"""Tests for SkillVoiceOverlay.

Covers registration, trigger/priority rules, fade timing, idle behavior,
rendering, and palette compliance during the full-opacity hold phase.

See ``requirements/overhaul/42_ui_chrome_components.md §5.7``.
"""

from __future__ import annotations

import pygame
import pytest

from spacegame.engine.skill_voice_overlay import (
    SkillVoice,
    SkillVoiceOverlay,
    VoiceEvent,
)


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _overlay_with_voices(*voices: SkillVoice) -> SkillVoiceOverlay:
    overlay = SkillVoiceOverlay()
    for v in voices:
        overlay.register_voice(v)
    return overlay


_ORE_SENSE = SkillVoice(
    skill_id="ore_sense",
    display_name="ORE SENSE",
    color_role="hud_accent_warm",
)
_SEISMIC = SkillVoice(
    skill_id="seismic_instinct",
    display_name="SEISMIC INSTINCT",
    color_role="hud_warning",
)
_FORENSIC = SkillVoice(
    skill_id="forensic_eye",
    display_name="FORENSIC EYE",
    color_role="hud_cyan",
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class TestSkillVoiceDataModel:
    def test_skill_voice_is_frozen(self) -> None:
        v = _ORE_SENSE
        with pytest.raises((AttributeError, TypeError)):
            v.display_name = "DIFFERENT"  # type: ignore[misc]

    def test_voice_event_is_hashable(self) -> None:
        e1 = VoiceEvent(skill_id="a", line="hi", priority=0, elapsed=0.1)
        e2 = VoiceEvent(skill_id="a", line="hi", priority=0, elapsed=0.1)
        assert e1 == e2
        assert hash(e1) == hash(e2)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_fresh_overlay_has_no_voices(self) -> None:
        overlay = SkillVoiceOverlay()
        assert overlay.voice_ids() == ()
        assert not overlay.is_active

    def test_register_single_voice(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        assert overlay.voice_ids() == ("ore_sense",)
        assert overlay.get_voice("ore_sense") == _ORE_SENSE

    def test_register_multiple_voices(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC, _FORENSIC)
        assert set(overlay.voice_ids()) == {
            "ore_sense",
            "seismic_instinct",
            "forensic_eye",
        }

    def test_reregistration_overwrites(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        variant = SkillVoice(
            skill_id="ore_sense", display_name="ORE SENSE 2", color_role="hud_cyan"
        )
        overlay.register_voice(variant)
        assert overlay.get_voice("ore_sense") == variant

    def test_registered_color_role_is_canonical(self) -> None:
        """All voices consumed here must name a real palette role."""
        from spacegame.engine.material_palette import is_valid_role

        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC, _FORENSIC)
        for vid in overlay.voice_ids():
            v = overlay.get_voice(vid)
            assert v is not None
            assert is_valid_role(v.color_role), (
                f"Voice '{vid}' has off-palette color_role '{v.color_role}'"
            )


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


class TestTrigger:
    def test_trigger_unknown_voice_rejected(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        assert overlay.trigger("unknown", "Line") is False
        assert not overlay.is_active

    def test_trigger_known_voice_accepted(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        assert overlay.trigger("ore_sense", "The vein runs deep.") is True
        assert overlay.is_active

    def test_current_snapshot_reflects_trigger(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "The vein runs deep.", priority=2)
        current = overlay.current
        assert current is not None
        assert current.skill_id == "ore_sense"
        assert current.line == "The vein runs deep."
        assert current.priority == 2
        assert current.elapsed == 0.0

    def test_clear_stops_current(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        overlay.clear()
        assert not overlay.is_active
        assert overlay.current is None


# ---------------------------------------------------------------------------
# Priority + queue discipline
# ---------------------------------------------------------------------------


class TestPriorityReplacement:
    def test_higher_priority_replaces_active(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC)
        overlay.trigger("ore_sense", "low line", priority=1)
        assert overlay.trigger("seismic_instinct", "high line", priority=5) is True
        assert overlay.current is not None
        assert overlay.current.skill_id == "seismic_instinct"
        assert overlay.current.line == "high line"

    def test_equal_priority_most_recent_wins(self) -> None:
        """Spec §5.7: lines don't queue — most recent at same priority replaces."""
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC)
        overlay.trigger("ore_sense", "first", priority=1)
        assert overlay.trigger("seismic_instinct", "second", priority=1) is True
        assert overlay.current is not None
        assert overlay.current.skill_id == "seismic_instinct"

    def test_lower_priority_rejected(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC)
        overlay.trigger("seismic_instinct", "boss line", priority=10)
        assert overlay.trigger("ore_sense", "flavor line", priority=2) is False
        # Active line unchanged.
        assert overlay.current is not None
        assert overlay.current.skill_id == "seismic_instinct"

    def test_trigger_after_fade_completes_accepted(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC)
        overlay.trigger("seismic_instinct", "old", priority=100)
        # Run out the clock completely.
        overlay.update(SkillVoiceOverlay.TOTAL_SECONDS + 0.1)
        assert not overlay.is_active
        # A fresh trigger at priority 0 is fine now.
        assert overlay.trigger("ore_sense", "fresh", priority=0) is True


# ---------------------------------------------------------------------------
# Timing / fade
# ---------------------------------------------------------------------------


class TestFadeTiming:
    def test_full_opacity_during_hold_phase(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        overlay.update(SkillVoiceOverlay.HOLD_SECONDS - 0.01)
        assert overlay.current_alpha() == 255

    def test_alpha_starts_decreasing_when_fade_begins(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        # Advance just past the hold boundary.
        overlay.update(SkillVoiceOverlay.HOLD_SECONDS + 0.01)
        alpha = overlay.current_alpha()
        assert alpha < 255

    def test_alpha_monotonically_non_increasing_across_fade(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        alphas: list[int] = []
        # Sample in 0.1s steps across hold+fade.
        steps = int((SkillVoiceOverlay.TOTAL_SECONDS + 0.2) / 0.1)
        for _ in range(steps):
            overlay.update(0.1)
            alphas.append(overlay.current_alpha())
        for i in range(len(alphas) - 1):
            assert alphas[i] >= alphas[i + 1], f"Alpha should not re-brighten: {alphas}"

    def test_voice_clears_after_total_duration(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        overlay.update(SkillVoiceOverlay.TOTAL_SECONDS + 0.01)
        assert not overlay.is_active
        assert overlay.current_alpha() == 0

    def test_idle_update_is_noop(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.update(0.5)
        assert not overlay.is_active

    def test_negative_or_zero_dt_ignored(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        overlay.update(-1.0)
        assert overlay.current is not None
        assert overlay.current.elapsed == 0.0
        overlay.update(0.0)
        assert overlay.current.elapsed == 0.0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_surface(overlay: SkillVoiceOverlay, w: int = 300, h: int = 60) -> pygame.Surface:
    target = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.render(target, pygame.Rect(0, 0, w, h))
    return target


class TestRender:
    def test_render_idle_is_noop(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        target = _render_surface(overlay)
        # Target should remain fully transparent — nothing was drawn.
        for y in (0, target.get_height() - 1):
            for x in (0, target.get_width() - 1):
                assert target.get_at((x, y)).a == 0

    def test_render_while_active_produces_opaque_pixels(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "The vein runs deep.")
        target = _render_surface(overlay)
        # Some pixel in the overlay region must be opaque.
        opaque = any(
            target.get_at((x, y)).a > 0
            for y in range(target.get_height())
            for x in range(target.get_width())
        )
        assert opaque

    def test_render_honors_skill_color_role(self) -> None:
        from spacegame.engine.material_palette import get_role

        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Warm accent line.")
        target = _render_surface(overlay)
        expected = get_role(_ORE_SENSE.color_role)
        # At least one fully-opaque pixel in the body region should match
        # the skill color exactly (no AA blending).
        found = False
        for y in range(target.get_height()):
            for x in range(target.get_width()):
                px = target.get_at((x, y))
                if px.a == 255 and (px.r, px.g, px.b) == expected:
                    found = True
                    break
            if found:
                break
        assert found, f"Expected at least one pixel in {expected}"

    def test_render_after_clear_is_noop(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Line")
        overlay.clear()
        target = _render_surface(overlay)
        any_opaque = any(
            target.get_at((x, y)).a > 0
            for y in range(target.get_height())
            for x in range(target.get_width())
        )
        assert not any_opaque


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------


class TestChromeCompliance:
    """Palette compliance during the full-opacity hold phase.

    The fade window is an intentional documented exception — alpha blend
    inevitably produces intermediate colors. Compliance matters when the
    player is actually reading the line, which is the hold.
    """

    def test_hold_phase_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Warm steady line.")
        # Advance to mid-hold — still full opacity.
        overlay.update(SkillVoiceOverlay.HOLD_SECONDS / 2)
        target = _render_surface(overlay)
        assert_role_compliance(target, tolerance=4.0)

    def test_multiple_skill_colors_all_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC, _FORENSIC)
        for voice in (_ORE_SENSE, _SEISMIC, _FORENSIC):
            overlay.trigger(voice.skill_id, f"{voice.display_name} speaking.", priority=1)
            target = _render_surface(overlay)
            assert_role_compliance(target, tolerance=4.0)
            overlay.clear()

    def test_stroke_uses_void_deep_role(self) -> None:
        """The 1-pixel legibility stroke must be the canonical void_deep role."""
        from spacegame.engine.material_palette import get_role

        overlay = _overlay_with_voices(_ORE_SENSE)
        overlay.trigger("ore_sense", "Stroke check.")
        target = _render_surface(overlay)
        void_deep = get_role("void_deep")
        # Somewhere in the body region there should be at least one pixel
        # exactly matching void_deep (the stroke beneath the body text).
        found_stroke = False
        for y in range(target.get_height()):
            for x in range(target.get_width()):
                px = target.get_at((x, y))
                if px.a == 255 and (px.r, px.g, px.b) == void_deep:
                    found_stroke = True
                    break
            if found_stroke:
                break
        assert found_stroke, "Expected at least one void_deep stroke pixel"


# ---------------------------------------------------------------------------
# Queue discipline (spec §5.7 guarantee)
# ---------------------------------------------------------------------------


class TestQueueDiscipline:
    def test_rapid_triggers_do_not_accumulate(self) -> None:
        """Spec: lines don't queue. Firing 10 triggers leaves exactly one active."""
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC, _FORENSIC)
        for i in range(10):
            overlay.trigger("ore_sense", f"line {i}", priority=1)
        assert overlay.is_active
        assert overlay.current is not None
        assert overlay.current.line == "line 9"

    def test_no_historical_replay_after_current_completes(self) -> None:
        overlay = _overlay_with_voices(_ORE_SENSE, _SEISMIC)
        overlay.trigger("ore_sense", "first", priority=1)
        overlay.trigger("seismic_instinct", "second (replaces)", priority=2)
        overlay.update(SkillVoiceOverlay.TOTAL_SECONDS + 0.1)
        # After fade completes, overlay is idle — no queued "first".
        assert not overlay.is_active
