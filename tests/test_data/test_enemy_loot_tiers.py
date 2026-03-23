"""Tests for enemy loot table normalization and credit rewards by danger tier."""

from spacegame.data_loader import DataLoader
from spacegame.models.combat import EnemyShipTemplate, CombatMove


VALID_DANGER_TIERS = {"low", "moderate", "dangerous"}

# Expected ranges per tier
TIER_XP_RANGES = {
    "low": (10, 20),
    "moderate": (20, 35),
    "dangerous": (35, 200),  # Upper bound loose for elite enemies
}

TIER_CREDIT_RANGES = {
    "low": (0, 25),
    "moderate": (25, 75),
    "dangerous": (75, 200),
}


def _load_enemies() -> list[EnemyShipTemplate]:
    loader = DataLoader()
    loader.load_all()
    return list(loader.enemy_templates.values())


def _load_commodity_ids() -> set[str]:
    loader = DataLoader()
    loader.load_all()
    return {c.id for c in loader.commodities.values()}


class TestEnemyDangerTiers:
    """All enemies should have a valid danger tier."""

    def test_all_enemies_have_valid_danger_tier(self) -> None:
        enemies = _load_enemies()
        for e in enemies:
            assert e.danger_tier in VALID_DANGER_TIERS, (
                f"{e.id} has invalid danger_tier '{e.danger_tier}'"
            )

    def test_enemy_count(self) -> None:
        """28 base + 7 bosses = 35 enemy templates."""
        enemies = _load_enemies()
        assert len(enemies) == 35

    def test_no_duplicate_enemy_ids(self) -> None:
        enemies = _load_enemies()
        ids = [e.id for e in enemies]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"


class TestEnemyXpRewards:
    """XP rewards should fall within expected range for tier."""

    def test_low_tier_xp_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_XP_RANGES["low"]
        for e in [e for e in enemies if e.danger_tier == "low"]:
            assert lo <= e.xp_reward <= hi, (
                f"{e.id}: xp_reward {e.xp_reward} outside [{lo}, {hi}]"
            )

    def test_moderate_tier_xp_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_XP_RANGES["moderate"]
        for e in [e for e in enemies if e.danger_tier == "moderate"]:
            assert lo <= e.xp_reward <= hi, (
                f"{e.id}: xp_reward {e.xp_reward} outside [{lo}, {hi}]"
            )

    def test_dangerous_tier_xp_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_XP_RANGES["dangerous"]
        for e in [e for e in enemies if e.danger_tier == "dangerous" and not e.is_boss]:
            assert lo <= e.xp_reward <= hi, (
                f"{e.id}: xp_reward {e.xp_reward} outside [{lo}, {hi}]"
            )


class TestEnemyCreditRewards:
    """Credit rewards should fall within expected range for tier."""

    def test_credit_reward_field_default(self) -> None:
        """EnemyShipTemplate should default credit_reward to 0."""
        template = EnemyShipTemplate(
            id="test",
            name="Test",
            description="Test",
            behavior="aggressive",
            hull=100,
            shields=50,
            energy=10,
            energy_regen=3,
            speed=8,
            evasion=15,
            accuracy=70,
            moves=[],
            loot_table=[],
        )
        assert template.credit_reward == 0

    def test_all_enemies_have_credit_reward(self) -> None:
        """Every enemy should have a positive credit_reward."""
        enemies = _load_enemies()
        for e in enemies:
            assert e.credit_reward > 0, f"{e.id} has credit_reward=0"

    def test_low_tier_credit_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_CREDIT_RANGES["low"]
        for e in [e for e in enemies if e.danger_tier == "low"]:
            assert lo <= e.credit_reward <= hi, (
                f"{e.id}: credit_reward {e.credit_reward} outside [{lo}, {hi}]"
            )

    def test_moderate_tier_credit_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_CREDIT_RANGES["moderate"]
        for e in [e for e in enemies if e.danger_tier == "moderate"]:
            assert lo <= e.credit_reward <= hi, (
                f"{e.id}: credit_reward {e.credit_reward} outside [{lo}, {hi}]"
            )

    def test_dangerous_tier_credit_in_range(self) -> None:
        enemies = _load_enemies()
        lo, hi = TIER_CREDIT_RANGES["dangerous"]
        for e in [e for e in enemies if e.danger_tier == "dangerous" and not e.is_boss]:
            assert lo <= e.credit_reward <= hi, (
                f"{e.id}: credit_reward {e.credit_reward} outside [{lo}, {hi}]"
            )


class TestEnemyLootTables:
    """Loot tables should reference valid commodities and scale with tier."""

    def test_all_loot_commodity_ids_valid(self) -> None:
        enemies = _load_enemies()
        valid_ids = _load_commodity_ids()
        for e in enemies:
            for loot in e.loot_table:
                assert loot["commodity_id"] in valid_ids, (
                    f"{e.id}: invalid commodity '{loot['commodity_id']}'"
                )

    def test_dangerous_tier_has_high_value_commodity(self) -> None:
        """Dangerous-tier enemies should drop at least one high-value item."""
        high_value = {
            "rare_metals", "rare_parts", "electronics", "weapons_components",
            "exotic_goods", "precious_metals", "rare_ore",
        }
        enemies = _load_enemies()
        for e in [e for e in enemies if e.danger_tier == "dangerous"]:
            loot_ids = {loot["commodity_id"] for loot in e.loot_table}
            assert loot_ids & high_value, (
                f"{e.id} (dangerous) has no high-value commodity in loot: {loot_ids}"
            )

    def test_loot_quantities_positive(self) -> None:
        """All loot min/max quantities should be positive."""
        enemies = _load_enemies()
        for e in enemies:
            for loot in e.loot_table:
                assert loot["min_qty"] >= 1, f"{e.id}: min_qty < 1"
                assert loot["max_qty"] >= loot["min_qty"], (
                    f"{e.id}: max_qty < min_qty"
                )

    def test_loot_chances_valid(self) -> None:
        """Loot drop chances should be between 0 and 1."""
        enemies = _load_enemies()
        for e in enemies:
            for loot in e.loot_table:
                assert 0 < loot["chance"] <= 1.0, (
                    f"{e.id}: chance {loot['chance']} not in (0, 1]"
                )
