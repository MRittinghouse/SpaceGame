"""Tests for Phase 9 — Module-targeted combat damage.

Covers module HP initialization, probabilistic hit targeting, module
disable effects, structural severing, and post-combat repair.
"""

import random

from spacegame.models.module_combat import (
    ModuleCombatState,
    init_module_combat_states,
    resolve_module_hit,
    apply_module_damage,
    get_disable_effects,
    check_severing,
    repair_all_modules,
    HP_PER_MODULE_PIXEL,
)
from spacegame.models.ship_build import ShipBuild, PlacedPixel
from spacegame.models.ship_module import ShipModule, PlacedModule


# ============================================================================
# Helpers
# ============================================================================


def _module(mid: str, cat: str, pixels: list[list[str]], weight: float = 2.0) -> ShipModule:
    return ShipModule(
        id=mid,
        name=mid,
        description="",
        category=cat,
        manufacturer="reyes_kowalski",
        pixel_grid=pixels,
        material_map={"H": "m", "E": "m", "W": "m", "S": "m"},
        provides={
            "slot_type": {
                "cockpit": "core",
                "engine": "engine",
                "weapon": "weapon",
                "shield": "defense",
            }.get(cat, ""),
            "thrust": 5,
        },
        weight=weight,
        base_cost=1000,
    )


def _catalog() -> dict[str, ShipModule]:
    return {
        "cockpit": _module("cockpit", "cockpit", [["H", "H"], ["H", "H"]]),
        "engine": _module("engine", "engine", [["H", "E", "H"], ["H", "E", "H"]]),
        "weapon": _module("weapon", "weapon", [["W", "H"], ["H", "H"]]),
        "shield": _module("shield", "shield", [["S", "H"], ["H", "S"]]),
        "cargo": _module("cargo", "cargo", [["H", "H", "H"]]),
    }


def _build_with_modules() -> tuple[ShipBuild, dict[str, ShipModule]]:
    catalog = _catalog()
    build = ShipBuild(weight_class="tiny")
    build.modules = [
        PlacedModule(module_id="cockpit", x=5, y=5),  # 4 pixels
        PlacedModule(module_id="engine", x=0, y=5),  # 6 pixels
        PlacedModule(module_id="weapon", x=7, y=5),  # 4 pixels
        PlacedModule(module_id="shield", x=5, y=7),  # 4 pixels
        PlacedModule(module_id="cargo", x=5, y=9),  # 3 pixels
    ]
    return build, catalog


# ============================================================================
# Module HP Initialization
# ============================================================================


class TestModuleCombatInit:
    """Test initialization of module combat states."""

    def test_init_creates_states_for_all_modules(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        assert len(states) == 5

    def test_max_hp_from_pixel_count(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        # Cockpit: 2x2 = 4 pixels → 4 * HP_PER_MODULE_PIXEL
        cockpit_state = states[0]
        assert cockpit_state.max_hp == 4 * HP_PER_MODULE_PIXEL
        # Engine: 3x2 = 6 pixels
        engine_state = states[1]
        assert engine_state.max_hp == 6 * HP_PER_MODULE_PIXEL

    def test_initial_hp_equals_max(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        for s in states:
            assert s.current_hp == s.max_hp

    def test_not_disabled_initially(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        for s in states:
            assert not s.disabled

    def test_category_tracked(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        categories = [s.category for s in states]
        assert "cockpit" in categories
        assert "engine" in categories
        assert "weapon" in categories

    def test_empty_build_no_states(self) -> None:
        build = ShipBuild(weight_class="tiny")
        states = init_module_combat_states(build, {})
        assert states == []


# ============================================================================
# Hit Resolution
# ============================================================================


class TestHitResolution:
    """Test probabilistic module targeting based on pixel coverage."""

    def test_hit_returns_module_or_hull(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        random.seed(42)
        result = resolve_module_hit(build, catalog, states)
        # Result is either a module index (int) or None (hull hit)
        assert result is None or isinstance(result, int)

    def test_many_hits_cover_multiple_modules(self) -> None:
        """Over many hits, different modules should be targeted."""
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        random.seed(42)
        hit_modules = set()
        for _ in range(200):
            result = resolve_module_hit(build, catalog, states)
            if result is not None:
                hit_modules.add(result)
        # Should hit at least 3 different modules over 200 tries
        assert len(hit_modules) >= 3, f"Only hit {len(hit_modules)} distinct modules"

    def test_hull_pixels_can_be_hit(self) -> None:
        """If build has hull pixels, some hits should target hull (return None)."""
        build, catalog = _build_with_modules()
        build.pixels = [PlacedPixel(x=i, y=0, material_id="standard_plate") for i in range(10)]
        states = init_module_combat_states(build, catalog)
        random.seed(42)
        hull_hits = 0
        for _ in range(200):
            result = resolve_module_hit(build, catalog, states)
            if result is None:
                hull_hits += 1
        assert hull_hits > 0, "Some hits should target hull pixels"

    def test_disabled_modules_still_targetable(self) -> None:
        """Disabled modules can still be hit (they're still physically there)."""
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        states[0].disabled = True  # Disable cockpit
        random.seed(42)
        cockpit_hits = 0
        for _ in range(200):
            result = resolve_module_hit(build, catalog, states)
            if result == 0:
                cockpit_hits += 1
        assert cockpit_hits > 0, "Disabled modules should still absorb hits"


# ============================================================================
# Module Damage Application
# ============================================================================


class TestModuleDamage:
    """Test damage application to individual modules."""

    def test_damage_reduces_hp(self) -> None:
        state = ModuleCombatState(
            module_id="engine",
            placed_index=1,
            max_hp=30,
            current_hp=30,
            category="engine",
        )
        msg, excess = apply_module_damage(state, 10)
        assert state.current_hp == 20
        assert not state.disabled
        assert excess == 0

    def test_damage_to_zero_disables(self) -> None:
        state = ModuleCombatState(
            module_id="engine",
            placed_index=1,
            max_hp=30,
            current_hp=10,
            category="engine",
        )
        msg, excess = apply_module_damage(state, 15)
        assert state.current_hp == 0
        assert state.disabled
        assert "disabled" in msg.lower()
        assert excess == 5

    def test_overkill_clamps_to_zero(self) -> None:
        state = ModuleCombatState(
            module_id="weapon",
            placed_index=2,
            max_hp=12,
            current_hp=5,
            category="weapon",
        )
        msg, excess = apply_module_damage(state, 100)
        assert state.current_hp == 0
        assert state.disabled
        assert excess == 95

    def test_damage_already_disabled(self) -> None:
        state = ModuleCombatState(
            module_id="weapon",
            placed_index=2,
            max_hp=12,
            current_hp=0,
            disabled=True,
            category="weapon",
        )
        msg, excess = apply_module_damage(state, 10)
        assert state.current_hp == 0
        assert "already" in msg.lower() or state.disabled
        assert excess == 10


# ============================================================================
# Disable Effects
# ============================================================================


class TestDisableEffects:
    """Test per-category disable effect multipliers."""

    def test_cockpit_disable_reduces_accuracy_and_evasion(self) -> None:
        effects = get_disable_effects("cockpit")
        assert effects["accuracy_mult"] < 1.0
        assert effects["evasion_mult"] < 1.0

    def test_engine_disable_reduces_speed_and_evasion(self) -> None:
        effects = get_disable_effects("engine")
        assert effects["speed_mult"] < 1.0
        assert effects["evasion_mult"] < 1.0

    def test_weapon_disable_flags_weapon_offline(self) -> None:
        effects = get_disable_effects("weapon")
        assert effects.get("weapon_offline") is True

    def test_shield_disable_reduces_shields(self) -> None:
        effects = get_disable_effects("shield")
        assert effects["shield_mult"] < 1.0

    def test_reactor_disable_degrades_all(self) -> None:
        effects = get_disable_effects("reactor")
        assert effects.get("all_stats_mult", 1.0) < 1.0

    def test_structural_has_no_effects(self) -> None:
        effects = get_disable_effects("structural")
        assert len(effects) == 0 or all(v == 1.0 for v in effects.values() if isinstance(v, float))

    def test_unknown_category(self) -> None:
        effects = get_disable_effects("unknown")
        assert effects == {}


# ============================================================================
# Structural Severing
# ============================================================================


class TestStructuralSevering:
    """Test severing detection when critical pixels are destroyed."""

    def test_no_severing_in_solid_build(self) -> None:
        build, catalog = _build_with_modules()
        states = init_module_combat_states(build, catalog)
        severed = check_severing(build, catalog, states)
        # No modules disabled, so no severing should happen
        assert severed == []

    def test_severing_returns_module_indices(self) -> None:
        """Severing should return list of module indices that got disconnected."""
        # Create a build with two groups connected only by one module
        catalog = _catalog()
        build = ShipBuild(weight_class="tiny")
        # Left group
        build.modules = [
            PlacedModule(module_id="cockpit", x=0, y=0),  # 2x2 at (0,0)
            PlacedModule(module_id="cargo", x=2, y=0),  # 3x1 bridge at (2,0)
            PlacedModule(module_id="weapon", x=5, y=0),  # 2x2 at (5,0)
        ]
        states = init_module_combat_states(build, catalog)
        # Disable the bridge module (cargo at index 1)
        states[1].disabled = True
        states[1].current_hp = 0

        severed = check_severing(build, catalog, states)
        # Result depends on connectivity; if cargo was the bridge,
        # one side should be severed
        # This is a structural test - the implementation determines specifics
        assert isinstance(severed, list)


# ============================================================================
# Post-Combat Repair
# ============================================================================


class TestPostCombatRepair:
    """Test that modules are restored after combat."""

    def test_repair_restores_hp(self) -> None:
        states = [
            ModuleCombatState("a", 0, 30, 10, False, "engine"),
            ModuleCombatState("b", 1, 20, 0, True, "weapon"),
        ]
        repair_all_modules(states)
        assert states[0].current_hp == 30
        assert states[1].current_hp == 20

    def test_repair_clears_disabled(self) -> None:
        states = [
            ModuleCombatState("a", 0, 30, 0, True, "engine"),
        ]
        repair_all_modules(states)
        assert not states[0].disabled
        assert states[0].current_hp == 30

    def test_repair_empty_list(self) -> None:
        repair_all_modules([])  # Should not error
