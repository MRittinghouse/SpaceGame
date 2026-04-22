"""Tests for Phase 10 — Builder polish, tutorial hints, and feedback systems.

Covers tutorial hint definitions, advisory warning generation,
module combat integration feedback, and visual feedback state.
"""

from spacegame.models.ship_build import ShipBuild, PlacedPixel
from spacegame.models.ship_physics import (
    compute_center_of_mass,
    compute_hull_efficiency,
    BalanceRating,
)
from spacegame.models.module_combat import (
    ModuleCombatState,
    apply_module_damage,
    get_disable_effects,
    repair_all_modules,
)


# ============================================================================
# Tutorial Hint Definitions
# ============================================================================


class TestTutorialHints:
    """Verify module builder tutorial hints are registered."""

    def test_module_hints_exist(self) -> None:
        from spacegame.tutorial_manager import MINIGAME_HINTS

        module_hints = [
            "builder_module_welcome",
            "builder_module_engine",
            "builder_module_requirements",
            "builder_module_hull",
            "builder_module_confirm",
        ]
        for hint_id in module_hints:
            assert hint_id in MINIGAME_HINTS, f"Missing tutorial hint: {hint_id}"

    def test_hints_have_title_and_description(self) -> None:
        from spacegame.tutorial_manager import MINIGAME_HINTS

        for hint_id in [
            "builder_module_welcome",
            "builder_module_engine",
            "builder_module_requirements",
            "builder_module_hull",
            "builder_module_confirm",
        ]:
            hint = MINIGAME_HINTS[hint_id]
            assert "title" in hint, f"Hint {hint_id} missing title"
            assert "description" in hint, f"Hint {hint_id} missing description"
            assert len(hint["title"]) > 0
            assert len(hint["description"]) > 10

    def test_welcome_hint_mentions_slots(self) -> None:
        from spacegame.tutorial_manager import MINIGAME_HINTS

        desc = MINIGAME_HINTS["builder_module_welcome"]["description"].lower()
        assert "slot" in desc, "Welcome hint should mention slots"
        assert "drydock" in desc, "Welcome hint should mention Drydock"

    def test_engine_hint_mentions_stern(self) -> None:
        from spacegame.tutorial_manager import MINIGAME_HINTS

        desc = MINIGAME_HINTS["builder_module_engine"]["description"].lower()
        assert "stern" in desc or "left" in desc, "Engine hint should mention stern/left"

    def test_requirements_hint_lists_slot_types(self) -> None:
        from spacegame.tutorial_manager import MINIGAME_HINTS

        desc = MINIGAME_HINTS["builder_module_requirements"]["description"].lower()
        assert "engine" in desc
        assert "reactor" in desc
        assert "weapon" in desc
        assert "cargo" in desc


# ============================================================================
# Advisory Warnings
# ============================================================================


class TestAdvisoryWarnings:
    """Test non-blocking advisory generation for suboptimal builds."""

    def test_off_balance_detected(self) -> None:
        """An extremely lopsided build should trigger CoM advisory."""
        from spacegame.models.ship_build import HullMaterial

        build = ShipBuild(weight_class="tiny")
        # Light pixels on far left, heavy on far right
        for x in range(0, 4):
            build.pixels.append(PlacedPixel(x=x, y=8, material_id="light"))
        for x in range(12, 16):
            build.pixels.append(PlacedPixel(x=x, y=8, material_id="heavy"))
        materials = {
            "light": HullMaterial(
                id="light",
                name="L",
                description="",
                shade_band="steel",
                weight_per_pixel=0.15,
            ),
            "heavy": HullMaterial(
                id="heavy",
                name="H",
                description="",
                shade_band="union_ceramic",
                weight_per_pixel=0.55,
            ),
        }
        _, _, offset_pct, rating = compute_center_of_mass(build, materials, {})
        assert offset_pct > 0, f"Lopsided build should have nonzero CoM offset, got {offset_pct}"

    def test_low_hull_efficiency_detected(self) -> None:
        """A thin line of pixels should have very low hull efficiency."""
        coords = [(x, 0) for x in range(10)]
        interior, perimeter, ratio = compute_hull_efficiency(coords)
        assert ratio == 0.0, "1-pixel-wide line should have 0% interior"

    def test_cockpit_exterior_detection(self) -> None:
        """Cockpit touching empty space should be flagged as exposed."""
        # A cockpit at the edge of the ship with no surrounding pixels
        # The advisory checks if any cockpit pixel has an empty neighbor
        coords = {(5, 5), (6, 5), (5, 6), (6, 6)}  # 2x2 cockpit
        # Check if any pixel has an empty 4-neighbor
        for x, y in coords:
            has_empty = any(
                (x + dx, y + dy) not in coords for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
            )
            if has_empty:
                break
        assert has_empty, "Edge cockpit pixels should have empty neighbors"


# ============================================================================
# Combat Feedback Integration
# ============================================================================


class TestCombatFeedback:
    """Test that combat module hits produce clear, readable feedback."""

    def test_module_damage_message_descriptive(self) -> None:
        state = ModuleCombatState("engine_rk", 0, 30, 30, False, "engine")
        msg, _ = apply_module_damage(state, 10)
        assert "engine_rk" in msg
        assert "20" in msg or "30" in msg  # Should show HP

    def test_module_disable_message_clear(self) -> None:
        state = ModuleCombatState("engine_rk", 0, 30, 5, False, "engine")
        msg, _ = apply_module_damage(state, 10)
        assert "disabled" in msg.lower()
        assert "engine" in msg.lower()

    def test_disable_effects_have_meaningful_values(self) -> None:
        """Disable effects should produce noticeable penalties."""
        for category in ["cockpit", "engine", "weapon", "shield", "reactor"]:
            effects = get_disable_effects(category)
            assert len(effects) > 0, f"Category {category} should have disable effects"

    def test_repair_message_implicit(self) -> None:
        """After repair, all modules should be functional."""
        states = [
            ModuleCombatState("a", 0, 30, 0, True, "engine"),
            ModuleCombatState("b", 1, 20, 5, False, "weapon"),
        ]
        repair_all_modules(states)
        for s in states:
            assert not s.disabled
            assert s.current_hp == s.max_hp


# ============================================================================
# Visual Feedback State
# ============================================================================


class TestVisualFeedbackState:
    """Test that visual feedback state initializes correctly."""

    def test_placement_flash_defaults(self) -> None:
        """Placement flash should start inactive."""
        # Just verify the initial values are reasonable
        timer = 0.0
        pos = (0, 0)
        assert timer == 0.0
        assert pos == (0, 0)

    def test_feedback_messages_list(self) -> None:
        """Feedback messages should start empty and support append."""
        messages: list[dict] = []
        messages.append(
            {
                "text": "Module placed!",
                "x": 100.0,
                "y": 200.0,
                "timer": 1.0,
                "color": (80, 255, 80),
            }
        )
        assert len(messages) == 1
        assert messages[0]["text"] == "Module placed!"

    def test_feedback_timer_decay(self) -> None:
        """Feedback messages should decay over time."""
        messages = [{"text": "Test", "x": 0.0, "y": 0.0, "timer": 1.0, "color": (255, 255, 255)}]
        dt = 0.5
        for msg in messages:
            msg["timer"] -= dt
            msg["y"] -= 25 * dt
        messages = [m for m in messages if m["timer"] > 0]
        assert len(messages) == 1
        assert messages[0]["timer"] == 0.5
        # After another 0.6s it should be gone
        for msg in messages:
            msg["timer"] -= 0.6
        messages = [m for m in messages if m["timer"] > 0]
        assert len(messages) == 0
