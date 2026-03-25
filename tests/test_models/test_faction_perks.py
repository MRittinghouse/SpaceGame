"""Tests for faction perk system — data loading, model logic, and applied effects."""

from spacegame.models.faction import ReputationTier
from spacegame.models.faction_perks import (
    FactionPerk,
    get_active_perks,
    get_perk_bonus,
    has_perk,
)


def _make_perk(
    perk_id: str = "test_perk",
    perk_type: str = "buy_price_bonus",
    value: float | bool = 0.05,
    faction_id: str = "commerce_guild",
    required_tier: str = "friendly",
) -> FactionPerk:
    return FactionPerk(
        id=perk_id,
        perk_type=perk_type,
        value=value,
        name="Test Perk",
        description="A test perk",
        faction_id=faction_id,
        required_tier=required_tier,
    )


def _sample_perks() -> dict[str, dict[str, list[FactionPerk]]]:
    """Build a minimal perk structure for testing."""
    return {
        "commerce_guild": {
            "friendly": [
                _make_perk("cg_buy", "buy_price_bonus", 0.05, "commerce_guild", "friendly"),
            ],
            "allied": [
                _make_perk("cg_sell", "sell_price_bonus", 0.05, "commerce_guild", "allied"),
                _make_perk("cg_repair", "free_repairs", True, "commerce_guild", "allied"),
            ],
        },
        "miners_union": {
            "friendly": [
                _make_perk("mu_mining", "mining_yield_bonus", 0.10, "miners_union", "friendly"),
            ],
            "allied": [
                _make_perk("mu_mining2", "mining_yield_bonus", 0.05, "miners_union", "allied"),
            ],
        },
    }


# === Data Loading ===


class TestFactionPerkDataLoading:
    """Faction perks should load correctly from JSON."""

    def test_perks_load_from_json(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        assert len(loader.faction_perks) == 4  # 4 factions

    def test_each_faction_has_friendly_and_allied(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        for faction_id, tiers in loader.faction_perks.items():
            assert "friendly" in tiers, f"{faction_id} missing friendly perks"
            assert "allied" in tiers, f"{faction_id} missing allied perks"

    def test_perk_types_are_valid(self) -> None:
        valid_types = {
            "buy_price_bonus",
            "sell_price_bonus",
            "mining_yield_bonus",
            "salvage_yield_bonus",
            "free_repairs",
            "free_fuel",
            "safe_passage",
            "wholesale_ore_bonus",
        }
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        for faction_id, tiers in loader.faction_perks.items():
            for tier_name, perks in tiers.items():
                for perk in perks:
                    assert perk.perk_type in valid_types, (
                        f"{perk.id}: invalid type '{perk.perk_type}'"
                    )

    def test_no_duplicate_perk_ids(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        all_ids: list[str] = []
        for faction_id, tiers in loader.faction_perks.items():
            for tier_name, perks in tiers.items():
                for perk in perks:
                    all_ids.append(perk.id)
        assert len(all_ids) == len(set(all_ids)), f"Duplicate perk IDs found"

    def test_total_perk_count(self) -> None:
        from spacegame.data_loader import DataLoader

        loader = DataLoader()
        loader.load_all()
        count = sum(
            len(perks) for tiers in loader.faction_perks.values() for perks in tiers.values()
        )
        assert count == 13  # 3 per faction × 4 factions + 1 wholesale perk


# === Model Logic: get_active_perks ===


class TestGetActivePerks:
    """get_active_perks should return correct perks based on reputation tier."""

    def test_neutral_gets_no_perks(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "commerce_guild", ReputationTier.NEUTRAL)
        assert len(active) == 0

    def test_hostile_gets_no_perks(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "commerce_guild", ReputationTier.HOSTILE)
        assert len(active) == 0

    def test_friendly_gets_friendly_perks(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "commerce_guild", ReputationTier.FRIENDLY)
        assert len(active) == 1
        assert active[0].id == "cg_buy"

    def test_allied_gets_friendly_and_allied(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "commerce_guild", ReputationTier.ALLIED)
        assert len(active) == 3  # 1 friendly + 2 allied
        ids = {p.id for p in active}
        assert "cg_buy" in ids
        assert "cg_sell" in ids
        assert "cg_repair" in ids

    def test_wrong_faction_gets_no_perks(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "frontier_alliance", ReputationTier.ALLIED)
        assert len(active) == 0

    def test_unknown_faction_returns_empty(self) -> None:
        perks = _sample_perks()
        active = get_active_perks(perks, "nonexistent", ReputationTier.ALLIED)
        assert len(active) == 0


# === Model Logic: get_perk_bonus ===


class TestGetPerkBonus:
    """get_perk_bonus should sum numeric bonuses of a given type."""

    def test_single_bonus(self) -> None:
        active = [_make_perk("p1", "buy_price_bonus", 0.05)]
        assert get_perk_bonus(active, "buy_price_bonus") == 0.05

    def test_stacking_bonuses(self) -> None:
        active = [
            _make_perk("p1", "mining_yield_bonus", 0.10),
            _make_perk("p2", "mining_yield_bonus", 0.05),
        ]
        assert abs(get_perk_bonus(active, "mining_yield_bonus") - 0.15) < 0.001

    def test_no_matching_type(self) -> None:
        active = [_make_perk("p1", "buy_price_bonus", 0.05)]
        assert get_perk_bonus(active, "sell_price_bonus") == 0.0

    def test_boolean_perks_ignored(self) -> None:
        active = [_make_perk("p1", "free_repairs", True)]
        assert get_perk_bonus(active, "free_repairs") == 0.0

    def test_empty_list(self) -> None:
        assert get_perk_bonus([], "buy_price_bonus") == 0.0


# === Model Logic: has_perk ===


class TestHasPerk:
    """has_perk should check for boolean perk flags."""

    def test_has_boolean_perk(self) -> None:
        active = [_make_perk("p1", "free_repairs", True)]
        assert has_perk(active, "free_repairs") is True

    def test_missing_perk_type(self) -> None:
        active = [_make_perk("p1", "free_repairs", True)]
        assert has_perk(active, "free_fuel") is False

    def test_false_value_perk(self) -> None:
        active = [_make_perk("p1", "free_repairs", False)]
        assert has_perk(active, "free_repairs") is False

    def test_empty_list(self) -> None:
        assert has_perk([], "free_repairs") is False


# === PoliticsManager Integration ===


class TestPoliticsManagerPerks:
    """PoliticsManager should expose perk queries."""

    def _make_politics_manager(self) -> "PoliticsManager":
        from spacegame.models.politics import PoliticsManager
        from spacegame.models.faction import Faction

        factions = {
            "commerce_guild": Faction(
                id="commerce_guild",
                name="Commerce Guild",
                description="",
                color=(200, 180, 50),
                rivalry="miners_union",
            ),
            "miners_union": Faction(
                id="miners_union",
                name="Miners' Union",
                description="",
                color=(180, 120, 60),
                rivalry="commerce_guild",
            ),
        }
        mgr = PoliticsManager(relationships=[], factions=factions)
        mgr.set_faction_perks(_sample_perks())
        return mgr

    def _make_player(self, faction_systems: dict[str, str] | None = None) -> "Player":
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType

        ship_type = ShipType(
            id="shuttle",
            name="Shuttle",
            ship_class="light",
            description="",
            cargo_capacity=50,
            fuel_capacity=100,
            fuel_efficiency=1.0,
            speed_multiplier=1.0,
            purchase_price=0,
            resale_value=0,
            crew_slots=1,
            special_abilities=[],
            availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        player = Player(
            name="Test",
            credits=5000,
            current_system_id="nexus_prime",
            ship=ship,
        )
        # Wire faction system mapping
        if faction_systems:
            for system_id, faction_id in faction_systems.items():
                player.faction_assignments[system_id] = faction_id
        return player

    def test_get_perk_bonus_friendly(self) -> None:
        mgr = self._make_politics_manager()
        player = self._make_player({"nexus_prime": "commerce_guild"})
        player.modify_reputation("commerce_guild", 25)  # FRIENDLY tier
        bonus = mgr.get_perk_bonus(player, "nexus_prime", "buy_price_bonus")
        assert bonus == 0.05

    def test_get_perk_bonus_neutral(self) -> None:
        mgr = self._make_politics_manager()
        player = self._make_player({"nexus_prime": "commerce_guild"})
        bonus = mgr.get_perk_bonus(player, "nexus_prime", "buy_price_bonus")
        assert bonus == 0.0

    def test_has_perk_allied(self) -> None:
        mgr = self._make_politics_manager()
        player = self._make_player({"nexus_prime": "commerce_guild"})
        player.modify_reputation("commerce_guild", 55)  # ALLIED tier
        assert mgr.has_perk(player, "nexus_prime", "free_repairs") is True

    def test_has_perk_friendly_no_allied(self) -> None:
        mgr = self._make_politics_manager()
        player = self._make_player({"nexus_prime": "commerce_guild"})
        player.modify_reputation("commerce_guild", 25)  # FRIENDLY only
        assert mgr.has_perk(player, "nexus_prime", "free_repairs") is False

    def test_mining_yield_stacks(self) -> None:
        mgr = self._make_politics_manager()
        player = self._make_player({"forgeworks": "miners_union"})
        player.modify_reputation("miners_union", 55)  # ALLIED
        bonus = mgr.get_perk_bonus(player, "forgeworks", "mining_yield_bonus")
        assert abs(bonus - 0.15) < 0.001  # 0.10 friendly + 0.05 allied
