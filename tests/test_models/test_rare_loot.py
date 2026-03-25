"""Tests for rare boss loot drops (R10).

Dangerous-tier enemies should have a rare_loot table with low-chance,
high-value commodity drops that are highlighted separately in combat results.
"""

from spacegame.models.combat import (
    CombatMove,
    EnemyBehavior,
    EnemyShipTemplate,
)
from spacegame.views.combat_view import _roll_loot


def _make_template(
    rare_loot: list[dict] | None = None,
    loot_table: list[dict] | None = None,
    danger_tier: str = "moderate",
) -> EnemyShipTemplate:
    """Create a minimal EnemyShipTemplate for testing."""
    return EnemyShipTemplate(
        id="test_enemy",
        name="Test Enemy",
        description="A test enemy.",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=100,
        shields=30,
        energy=10,
        energy_regen=3,
        speed=8,
        evasion=10,
        accuracy=70,
        moves=[
            CombatMove(
                id="test_shot",
                name="Test Shot",
                description="A test attack.",
                effects=[],
                energy_cost=2,
            )
        ],
        loot_table=loot_table or [],
        danger_tier=danger_tier,
        rare_loot=rare_loot or [],
    )


class TestRareLootField:
    """Tests for the rare_loot field on EnemyShipTemplate."""

    def test_rare_loot_defaults_to_empty_list(self) -> None:
        """rare_loot should default to empty list when not provided."""
        template = EnemyShipTemplate(
            id="test",
            name="Test",
            description="Test",
            behavior=EnemyBehavior.AGGRESSIVE,
            hull=100,
            shields=30,
            energy=10,
            energy_regen=3,
            speed=8,
            evasion=10,
            accuracy=70,
            moves=[],
            loot_table=[],
        )
        assert template.rare_loot == [], "rare_loot should default to empty list"

    def test_rare_loot_can_be_set(self) -> None:
        """rare_loot should accept a list of loot entries."""
        rare = [{"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 2, "chance": 0.1}]
        template = _make_template(rare_loot=rare)
        assert template.rare_loot == rare

    def test_rare_loot_independent_from_loot_table(self) -> None:
        """rare_loot and loot_table should be separate lists."""
        loot = [{"commodity_id": "common_metals", "min_qty": 1, "max_qty": 3, "chance": 0.8}]
        rare = [{"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 2, "chance": 0.1}]
        template = _make_template(loot_table=loot, rare_loot=rare)
        assert len(template.loot_table) == 1
        assert len(template.rare_loot) == 1
        assert template.loot_table[0]["commodity_id"] == "common_metals"
        assert template.rare_loot[0]["commodity_id"] == "exotic_goods"


class TestRareLootDataLoading:
    """Tests for rare_loot parsing from JSON data."""

    def test_data_loader_parses_rare_loot(self) -> None:
        """DataLoader should parse rare_loot from enemy JSON."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()

        # At least one dangerous enemy should have rare_loot
        dangerous_with_rare = [
            t for t in dl.enemy_templates.values() if t.danger_tier == "dangerous" and t.rare_loot
        ]
        assert len(dangerous_with_rare) > 0, "At least one dangerous enemy should have rare_loot"

    def test_all_dangerous_enemies_have_rare_loot(self) -> None:
        """Every dangerous-tier enemy should have at least one rare_loot entry."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()

        dangerous = [t for t in dl.enemy_templates.values() if t.danger_tier == "dangerous"]
        assert len(dangerous) >= 10, f"Expected at least 10 dangerous enemies, got {len(dangerous)}"

        for template in dangerous:
            assert template.rare_loot, (
                f"Dangerous enemy '{template.id}' should have rare_loot entries"
            )

    def test_low_tier_enemies_have_no_rare_loot(self) -> None:
        """Low-tier enemies should not have rare_loot in the data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()

        low = [t for t in dl.enemy_templates.values() if t.danger_tier == "low"]
        assert len(low) > 0, "Should have at least one low-tier enemy"
        for template in low:
            assert not template.rare_loot, (
                f"Low-tier enemy '{template.id}' should not have rare_loot"
            )

    def test_moderate_tier_enemies_have_no_rare_loot(self) -> None:
        """Moderate-tier enemies should not have rare_loot in the data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()

        moderate = [t for t in dl.enemy_templates.values() if t.danger_tier == "moderate"]
        assert len(moderate) > 0, "Should have at least one moderate-tier enemy"
        for template in moderate:
            assert not template.rare_loot, (
                f"Moderate-tier enemy '{template.id}' should not have rare_loot"
            )

    def test_rare_loot_commodity_ids_are_valid(self) -> None:
        """All commodity IDs in rare_loot should exist in commodities data."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()

        valid_ids = set(dl.commodities.keys())
        for template in dl.enemy_templates.values():
            for entry in template.rare_loot:
                assert entry["commodity_id"] in valid_ids, (
                    f"rare_loot commodity '{entry['commodity_id']}' on enemy "
                    f"'{template.id}' is not a valid commodity ID"
                )

    def test_rare_loot_entries_have_correct_structure(self) -> None:
        """Each rare_loot entry should have commodity_id, min_qty, max_qty, chance."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_enemy_templates()

        for template in dl.enemy_templates.values():
            for entry in template.rare_loot:
                assert "commodity_id" in entry, f"Missing commodity_id in {template.id} rare_loot"
                assert "min_qty" in entry, f"Missing min_qty in {template.id} rare_loot"
                assert "max_qty" in entry, f"Missing max_qty in {template.id} rare_loot"
                assert "chance" in entry, f"Missing chance in {template.id} rare_loot"
                assert 0.0 <= entry["chance"] <= 1.0, (
                    f"Chance should be in [0, 1] for {template.id}"
                )
                assert entry["min_qty"] >= 1, f"min_qty should be >= 1 for {template.id}"
                assert entry["max_qty"] >= entry["min_qty"], (
                    f"max_qty should be >= min_qty for {template.id}"
                )


class TestRareLootRolling:
    """Tests for rolling rare loot drops."""

    def test_roll_loot_includes_rare_items(self) -> None:
        """_roll_loot should work with rare_loot entries (same format)."""
        rare_table = [
            {"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 2, "chance": 1.0},
        ]
        result = _roll_loot(rare_table, seed=42)
        assert "exotic_goods" in result, "Chance 1.0 should always drop"

    def test_guaranteed_rare_drop_always_drops(self) -> None:
        """Rare loot with chance=1.0 should always drop."""
        rare_table = [
            {"commodity_id": "precious_metals", "min_qty": 1, "max_qty": 1, "chance": 1.0},
        ]
        # Test across multiple seeds
        for seed in range(100):
            result = _roll_loot(rare_table, seed=seed)
            assert "precious_metals" in result, f"Guaranteed drop missed at seed {seed}"
            assert result["precious_metals"] == 1

    def test_zero_chance_rare_drop_never_drops(self) -> None:
        """Rare loot with chance=0.0 should never drop."""
        rare_table = [
            {"commodity_id": "restricted_tech", "min_qty": 1, "max_qty": 3, "chance": 0.0},
        ]
        for seed in range(100):
            result = _roll_loot(rare_table, seed=seed)
            assert "restricted_tech" not in result, f"Zero-chance drop appeared at seed {seed}"

    def test_rare_loot_quantities_in_range(self) -> None:
        """Rolled quantities should be within min_qty and max_qty."""
        rare_table = [
            {"commodity_id": "crystal_ore", "min_qty": 1, "max_qty": 3, "chance": 1.0},
        ]
        for seed in range(200):
            result = _roll_loot(rare_table, seed=seed)
            qty = result["crystal_ore"]
            assert 1 <= qty <= 3, f"Quantity {qty} out of range [1, 3] at seed {seed}"

    def test_combined_loot_and_rare_loot_rolling(self) -> None:
        """Both regular and rare loot tables can be rolled and combined."""
        regular = [
            {"commodity_id": "common_metals", "min_qty": 2, "max_qty": 4, "chance": 1.0},
        ]
        rare = [
            {"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 1, "chance": 1.0},
        ]
        regular_result = _roll_loot(regular, seed=42)
        rare_result = _roll_loot(rare, seed=42)

        # Combine like the game does
        combined: dict[str, int] = {}
        for cid, qty in regular_result.items():
            combined[cid] = combined.get(cid, 0) + qty
        for cid, qty in rare_result.items():
            combined[cid] = combined.get(cid, 0) + qty

        assert "common_metals" in combined
        assert "exotic_goods" in combined

    def test_roll_loot_deterministic_for_same_seed(self) -> None:
        """_roll_loot should return identical results for the same seed."""
        table = [
            {"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 10, "chance": 0.5},
            {"commodity_id": "rare_ore", "min_qty": 1, "max_qty": 5, "chance": 0.5},
        ]
        result_a = _roll_loot(table, seed=12345)
        result_b = _roll_loot(table, seed=12345)
        assert result_a == result_b, "Same seed should produce identical loot results"

    def test_roll_loot_different_seeds_produce_different_results(self) -> None:
        """_roll_loot should produce variation across different seeds."""
        table = [
            {"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 10, "chance": 0.5},
            {"commodity_id": "rare_ore", "min_qty": 1, "max_qty": 10, "chance": 0.5},
            {"commodity_id": "restricted_tech", "min_qty": 1, "max_qty": 10, "chance": 0.5},
        ]
        results = set()
        for seed in range(50):
            result = _roll_loot(table, seed=seed)
            results.add(frozenset(result.items()))
        assert len(results) > 1, "Different seeds should produce at least some variation in loot"

    def test_empty_loot_table_returns_empty_dict(self) -> None:
        """_roll_loot with an empty table should return an empty dict."""
        result = _roll_loot([], seed=42)
        assert result == {}, "Empty loot table should return empty dict"

    def test_rare_loot_seed_offset_differs_from_normal_loot(self) -> None:
        """Rare loot uses encounter_seed + hash(id) + 7919, producing different results."""
        table = [
            {"commodity_id": "exotic_goods", "min_qty": 1, "max_qty": 10, "chance": 0.5},
            {"commodity_id": "rare_ore", "min_qty": 1, "max_qty": 10, "chance": 0.5},
        ]
        found_difference = False
        for trial_seed in range(100):
            base = trial_seed + hash("test_enemy")
            r1 = _roll_loot(table, seed=base)
            r2 = _roll_loot(table, seed=base + 7919)
            if r1 != r2:
                found_difference = True
                break
        assert found_difference, (
            "Rare loot seed offset (7919) should produce different results than normal loot seed"
        )
