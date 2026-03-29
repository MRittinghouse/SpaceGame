"""Tests for TutorialOverlay safety — active without content auto-hides."""

import pygame
import pytest

from spacegame.tutorial_manager import TutorialManager


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    """Ensure pygame display and font subsystems are available."""
    pygame.init()
    pygame.display.set_mode((1280, 720))
    yield  # type: ignore[misc]
    pygame.quit()


class TestTutorialOverlaySafety:
    """Verify the overlay can't get stuck active with no visible content."""

    def _make_overlay(self) -> "TutorialOverlay":
        """Create a TutorialOverlay with a fresh manager."""
        from spacegame.views.tutorial_overlay import TutorialOverlay

        tm = TutorialManager()
        return TutorialOverlay(tm)

    def test_show_with_no_step_does_not_activate(self) -> None:
        """show() should refuse to activate if there's no valid step."""
        overlay = self._make_overlay()
        # Manager is not started, so get_current_step() returns None
        overlay.show()
        assert overlay.active is False, "Overlay should not activate with no step"

    def test_show_hint_with_invalid_id_does_not_activate(self) -> None:
        """show_hint() with a nonexistent hint ID should not activate."""
        overlay = self._make_overlay()
        overlay.show_hint("nonexistent_hint_id")
        assert overlay.active is False

    def test_show_hint_with_valid_id_activates(self) -> None:
        """show_hint() with a valid, undismissed hint should activate."""
        overlay = self._make_overlay()
        overlay.show_hint("combat_defensive_identity")
        assert overlay.active is True
        assert overlay._hint_mode is True
        assert overlay._hint_data is not None

    def test_show_hint_already_dismissed_does_not_activate(self) -> None:
        """show_hint() for an already-dismissed hint should not activate."""
        overlay = self._make_overlay()
        overlay.tutorial_manager.dismiss_hint("combat_defensive_identity")
        overlay.show_hint("combat_defensive_identity")
        assert overlay.active is False

    def test_hide_resets_state(self) -> None:
        """hide() should clear all active state."""
        overlay = self._make_overlay()
        overlay.show_hint("combat_defensive_identity")
        assert overlay.active is True
        overlay.hide()
        assert overlay.active is False
        assert overlay._hint_mode is False
        assert overlay._hint_data is None
        assert overlay._hint_id is None

    def test_render_auto_hides_when_hint_data_none(self) -> None:
        """render() should auto-hide if active but _hint_data is somehow None."""
        screen = pygame.Surface((1280, 720))

        overlay = self._make_overlay()
        # Force into broken state: active hint mode but no data
        overlay.active = True
        overlay._hint_mode = True
        overlay._hint_data = None

        overlay.render(screen)
        assert overlay.active is False, "Should auto-hide when no hint data"

    def test_render_auto_hides_when_tutorial_step_none(self) -> None:
        """render() should auto-hide if active tutorial mode but no step."""
        screen = pygame.Surface((1280, 720))

        overlay = self._make_overlay()
        # Force into broken state: active tutorial mode but no step
        overlay.active = True
        overlay._hint_mode = False
        # Manager has no active step (never started)

        overlay.render(screen)
        assert overlay.active is False, "Should auto-hide when no tutorial step"
