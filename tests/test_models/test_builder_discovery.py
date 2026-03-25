"""Tests for Phase D2 — Builder discovery system.

Tests salvage, mining, combat, trading, and faction discovery paths.
"""

from spacegame.models.builder_discovery import (
    check_salvage_discovery,
    check_mining_discovery,
    check_combat_trophy,
    check_trade_milestones,
    check_faction_unlocks,
    TRADE_MILESTONES,
    FACTION_BUILDER_UNLOCKS,
    BOSS_TROPHY_SHAPES,
    SALVAGE_DISCOVERIES,
    MINING_DISCOVERIES,
)


class TestSalvageDiscovery:
    """Salvage runs can discover shape blueprints."""

    def test_discovery_possible_on_cargo_deck(self) -> None:
        """Should be able to discover cargo-related shapes."""
        found = False
        for seed in range(200):
            result = check_salvage_discovery("cargo", 5, set(), seed=seed)
            if result:
                assert result in SALVAGE_DISCOVERIES["cargo"]
                found = True
                break
        assert found, "Should find a cargo shape in 200 attempts with max skill"

    def test_no_discovery_without_luck(self) -> None:
        """Most runs don't produce discoveries (only ~5-15% chance)."""
        discoveries = 0
        for seed in range(100):
            result = check_salvage_discovery("cargo", 0, set(), seed=seed)
            if result:
                discoveries += 1
        # 5% chance = ~5 discoveries in 100 runs (with variance)
        assert discoveries < 30, f"Too many discoveries: {discoveries}/100"

    def test_no_rediscovery(self) -> None:
        """Already unlocked shapes are not re-discovered."""
        all_cargo = set(SALVAGE_DISCOVERIES["cargo"])
        result = check_salvage_discovery("cargo", 5, all_cargo, seed=1)
        assert result is None, "Should not rediscover already-unlocked shapes"

    def test_skill_increases_chance(self) -> None:
        """Higher salvage skill = more discoveries."""
        low_skill_finds = sum(
            1 for s in range(500) if check_salvage_discovery("engine", 0, set(), seed=s)
        )
        high_skill_finds = sum(
            1 for s in range(500) if check_salvage_discovery("engine", 5, set(), seed=s)
        )
        assert high_skill_finds > low_skill_finds, "Higher skill should find more"


class TestMiningDiscovery:
    """Deep mining can reveal shapes and materials."""

    def test_no_discovery_at_shallow_depth(self) -> None:
        result = check_mining_discovery("iron_depths", 2, 0, set(), set(), seed=1)
        assert result is None, "Depth < 3 should never discover"

    def test_discovery_possible_at_deep_layers(self) -> None:
        found = False
        for seed in range(300):
            result = check_mining_discovery("iron_depths", 5, 3, set(), set(), seed=seed)
            if result:
                assert result["type"] in ("shape", "material")
                found = True
                break
        assert found, "Should find something at Iron Depths depth 5 with skill 3"

    def test_system_specific_discoveries(self) -> None:
        """Iron Depths has different discoveries than Breakstone."""
        iron_ids = {d["id"] for d in MINING_DISCOVERIES.get("iron_depths", [])}
        break_ids = {d["id"] for d in MINING_DISCOVERIES.get("breakstone", [])}
        assert iron_ids != break_ids, "Different systems should have different discoveries"

    def test_no_discovery_at_unknown_system(self) -> None:
        result = check_mining_discovery("nexus_prime", 5, 5, set(), set(), seed=1)
        assert result is None, "No mining discoveries at non-mining systems"


class TestCombatTrophy:
    """Boss kills award trophy shapes."""

    def test_boss_drops_trophy(self) -> None:
        trophy = check_combat_trophy("corsair_king", True, set())
        assert trophy == "pirate_cutlass_fin"

    def test_each_boss_has_unique_trophy(self) -> None:
        trophies = set()
        for boss_id, trophy_id in BOSS_TROPHY_SHAPES.items():
            assert trophy_id not in trophies, f"Duplicate trophy: {trophy_id}"
            trophies.add(trophy_id)

    def test_no_trophy_from_non_boss(self) -> None:
        trophy = check_combat_trophy("pirate_raider", False, set())
        assert trophy is None

    def test_no_redrop(self) -> None:
        trophy = check_combat_trophy("corsair_king", True, {"pirate_cutlass_fin"})
        assert trophy is None, "Should not re-drop already-unlocked trophy"

    def test_all_7_bosses_have_trophies(self) -> None:
        assert len(BOSS_TROPHY_SHAPES) == 7


class TestTradeMilestones:
    """Trading profit milestones unlock builder content."""

    def test_first_milestone(self) -> None:
        crossed = check_trade_milestones(12000, 5000)
        assert len(crossed) == 1
        assert crossed[0]["name"] == "Merchant"

    def test_multiple_milestones_at_once(self) -> None:
        """Large profit jump can cross multiple milestones."""
        crossed = check_trade_milestones(300000, 0)
        names = {m["name"] for m in crossed}
        assert "Merchant" in names
        assert "Trader" in names
        assert "Magnate" in names
        assert "Tycoon" in names

    def test_no_milestone_below_threshold(self) -> None:
        crossed = check_trade_milestones(5000, 3000)
        assert len(crossed) == 0

    def test_milestone_not_recrossed(self) -> None:
        """Previous profit already past threshold = not crossed again."""
        crossed = check_trade_milestones(15000, 12000)
        assert len(crossed) == 0, "10K milestone already passed"

    def test_six_milestones_defined(self) -> None:
        assert len(TRADE_MILESTONES) == 6


class TestFactionUnlocks:
    """Faction reputation thresholds unlock builder content."""

    def test_guild_friendly_unlocks_shape(self) -> None:
        unlocks = check_faction_unlocks("commerce_guild", 25, set(), set())
        shape_ids = []
        for u in unlocks:
            shape_ids.extend(u["shapes"])
        assert "guild_prow" in shape_ids

    def test_guild_allied_unlocks_stern(self) -> None:
        unlocks = check_faction_unlocks("commerce_guild", 50, set(), set())
        shape_ids = []
        for u in unlocks:
            shape_ids.extend(u["shapes"])
        assert "guild_stern" in shape_ids

    def test_no_unlock_below_threshold(self) -> None:
        unlocks = check_faction_unlocks("commerce_guild", 10, set(), set())
        assert len(unlocks) == 0

    def test_no_rediscovery(self) -> None:
        """Already-unlocked shapes are not re-reported."""
        unlocks = check_faction_unlocks(
            "commerce_guild",
            50,
            {"guild_prow", "guild_stern"},
            {"ablative_plating"},
        )
        assert len(unlocks) == 0

    def test_all_four_factions_have_unlocks(self) -> None:
        assert len(FACTION_BUILDER_UNLOCKS) == 4
        for faction_id in [
            "commerce_guild",
            "miners_union",
            "science_collective",
            "frontier_alliance",
        ]:
            assert faction_id in FACTION_BUILDER_UNLOCKS
            assert len(FACTION_BUILDER_UNLOCKS[faction_id]) >= 3


class TestDrydockCatalogs:
    """Per-system content catalogs load correctly."""

    def test_catalogs_load(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_drydock_catalogs()
        assert len(dl.drydock_catalogs) >= 10

    def test_forgeworks_has_heavy_armor(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_drydock_catalogs()
        forge = dl.drydock_catalogs.get("forgeworks", {})
        assert "heavy_armor" in forge.get("materials_sold", [])

    def test_axiom_has_shield_crystal(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_drydock_catalogs()
        axiom = dl.drydock_catalogs.get("axiom_labs", {})
        assert "shield_crystal" in axiom.get("materials_sold", [])

    def test_crimson_has_stealth(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_drydock_catalogs()
        crimson = dl.drydock_catalogs.get("crimson_reach", {})
        assert "stealth_composite" in crimson.get("materials_sold", [])

    def test_no_system_sells_everything(self) -> None:
        """Each system should have a limited selection."""
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_drydock_catalogs()
        for sys_id, catalog in dl.drydock_catalogs.items():
            shapes = catalog.get("shapes_sold", [])
            materials = catalog.get("materials_sold", [])
            assert len(shapes) <= 8, f"{sys_id} sells too many shapes: {len(shapes)}"
            assert len(materials) <= 4, f"{sys_id} sells too many materials: {len(materials)}"
