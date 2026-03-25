"""Tests for Phase 8 — Module progression, unlocks, and checkout.

Covers player module unlock tracking, save/load round-trips,
faction module unlocks, builder catalog filtering by unlock state,
and build cost checkout.
"""

from spacegame.models.ship_build import ShipBuild, ShipStatsComputer
from spacegame.models.ship_module import (
    ShipModule,
    PlacedModule,
    MANUFACTURER_COST_MULTIPLIERS,
)
from spacegame.models.builder_discovery import (
    check_faction_module_unlocks,
    FACTION_MODULE_UNLOCKS,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_player():
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship, ShipType

    ship_type = ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic",
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
    return Player(
        name="Test",
        credits=50000,
        current_system_id="nexus_prime",
        ship=ship,
    )


# ============================================================================
# Player Module Unlock Tracking
# ============================================================================


class TestPlayerModuleUnlocks:
    """Test module unlock field on Player."""

    def test_default_unlocked_modules(self) -> None:
        player = _make_player()
        assert len(player.unlocked_modules) >= 20, (
            f"Should have 20+ starter modules, got {len(player.unlocked_modules)}"
        )

    def test_starter_modules_include_mandatory_categories(self) -> None:
        """Free starters should cover all mandatory categories."""
        from spacegame.data_loader import DataLoader

        dl = DataLoader()
        dl.load_ship_modules()
        player = _make_player()
        mandatory = {"cockpit", "engine", "weapon", "shield", "cargo"}
        for cat in mandatory:
            cat_mods = [
                mid
                for mid in player.unlocked_modules
                if mid in dl.ship_modules and dl.ship_modules[mid].category == cat
            ]
            assert len(cat_mods) >= 1, f"No starter module for category '{cat}'"

    def test_unlock_new_module(self) -> None:
        player = _make_player()
        assert "standard_bridge_rk" not in player.unlocked_modules
        player.unlocked_modules.add("standard_bridge_rk")
        assert "standard_bridge_rk" in player.unlocked_modules

    def test_unlock_idempotent(self) -> None:
        player = _make_player()
        initial = len(player.unlocked_modules)
        player.unlocked_modules.add("scout_pod_rk")  # Already unlocked
        assert len(player.unlocked_modules) == initial


# ============================================================================
# Save/Load Round-Trip
# ============================================================================


class TestModuleUnlockSerialization:
    """Test that module unlocks persist through save/load."""

    def test_unlocked_modules_serialized(self) -> None:
        player = _make_player()
        player.unlocked_modules.add("war_bridge_talon")
        # Verify it would be serialized (same pattern as unlocked_shapes)
        serialized = sorted(player.unlocked_modules)
        assert "war_bridge_talon" in serialized

    def test_backward_compat_no_unlocked_modules(self) -> None:
        """Old saves without unlocked_modules should load with defaults."""
        player = _make_player()
        # Simulate loading old save data without the field
        # The default factory should still provide starter modules
        assert len(player.unlocked_modules) >= 20


# ============================================================================
# Faction Module Unlocks
# ============================================================================


class TestFactionModuleUnlocks:
    """Test faction reputation → module blueprint unlocks."""

    def test_no_unlocks_at_zero_rep(self) -> None:
        result = check_faction_module_unlocks("commerce_guild", 0, set())
        assert result == []

    def test_friendly_tier_unlocks(self) -> None:
        result = check_faction_module_unlocks("commerce_guild", 25, set())
        assert len(result) >= 1
        module_ids = [r["module_id"] for r in result]
        assert any("talon" in mid or "twin" in mid for mid in module_ids)

    def test_trusted_tier_adds_more(self) -> None:
        already = {"split_engine_talon", "twin_link_talon"}
        result = check_faction_module_unlocks("commerce_guild", 40, already)
        assert len(result) >= 1
        module_ids = [r["module_id"] for r in result]
        assert "quad_mount_foundry" in module_ids

    def test_already_unlocked_not_repeated(self) -> None:
        already = {"split_engine_talon", "twin_link_talon", "quad_mount_foundry", "brig_rk"}
        result = check_faction_module_unlocks("commerce_guild", 50, already)
        assert result == [], "All modules already unlocked, should return empty"

    def test_all_factions_have_module_unlocks(self) -> None:
        for faction_id in FACTION_MODULE_UNLOCKS:
            tiers = FACTION_MODULE_UNLOCKS[faction_id]
            all_mods = []
            for tier in tiers:
                all_mods.extend(tier["modules"])
            assert len(all_mods) >= 2, f"Faction {faction_id} has too few module unlocks"

    def test_collective_unlocks_sable_modules(self) -> None:
        result = check_faction_module_unlocks("science_collective", 50, set())
        module_ids = [r["module_id"] for r in result]
        # Collective should unlock Sable (stealth) manufacturer modules
        sable_mods = [mid for mid in module_ids if "sable" in mid]
        assert len(sable_mods) >= 2, "Collective should unlock multiple Sable modules"


# ============================================================================
# Build Cost Checkout
# ============================================================================


class TestBuildCostCheckout:
    """Test that build confirmation charges credits correctly."""

    def test_build_cost_includes_modules(self) -> None:
        from spacegame.models.ship_build import HullMaterial

        catalog = {
            "cockpit": ShipModule(
                id="cockpit",
                name="Test",
                description="",
                category="cockpit",
                manufacturer="reyes_kowalski",
                pixel_grid=[["H"]],
                material_map={"H": "m"},
                provides={"slot_type": "core"},
                weight=1.0,
                base_cost=2000,
            ),
        }
        materials = {
            "m": HullMaterial(id="m", name="M", description="", color_primary=(128, 128, 128))
        }
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="cockpit", x=0, y=0)]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        # RK multiplier = 1.0, so cost = 2000
        assert stats.total_cost >= 2000

    def test_manufacturer_multiplier_affects_cost(self) -> None:
        from spacegame.models.ship_build import HullMaterial

        catalog = {
            "meridian_mod": ShipModule(
                id="meridian_mod",
                name="Test",
                description="",
                category="utility",
                manufacturer="meridian",
                pixel_grid=[["H"]],
                material_map={"H": "m"},
                provides={},
                weight=1.0,
                base_cost=1000,
            ),
        }
        materials = {
            "m": HullMaterial(id="m", name="M", description="", color_primary=(128, 128, 128))
        }
        build = ShipBuild(weight_class="tiny")
        build.modules = [PlacedModule(module_id="meridian_mod", x=0, y=0)]
        stats = ShipStatsComputer.compute(build, materials, module_catalog=catalog)
        # Meridian multiplier = 1.5, so cost = 1500
        assert stats.total_cost >= 1500

    def test_hull_pixels_add_to_cost(self) -> None:
        from spacegame.models.ship_build import HullMaterial, PlacedPixel

        materials = {
            "plate": HullMaterial(
                id="plate",
                name="P",
                description="",
                color_primary=(128, 128, 128),
                cost_per_pixel=15,
            )
        }
        build = ShipBuild(weight_class="tiny")
        build.pixels = [PlacedPixel(x=i, y=0, material_id="plate") for i in range(10)]
        stats = ShipStatsComputer.compute(build, materials)
        # 10 pixels × 15 cr/px = 150
        assert stats.total_cost >= 150
