"""Tests for Sprint 3 view fixes — AchievementsView scroll clamping and NameInputView validation."""

import re
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from spacegame.views.name_input_view import MAX_NAME_LENGTH, _VALID_NAME_PATTERN


# ============================================================================
# NameInputView — Name Validation Constants (no pygame needed)
# ============================================================================


class TestNameValidationConstants:
    """Tests for module-level name validation constants."""

    def test_max_name_length_is_20(self) -> None:
        assert MAX_NAME_LENGTH == 20, "MAX_NAME_LENGTH should be 20"

    def test_valid_name_pattern_accepts_alpha(self) -> None:
        assert _VALID_NAME_PATTERN.match("Captain"), "Alphabetic name should be valid"

    def test_valid_name_pattern_accepts_alphanumeric(self) -> None:
        assert _VALID_NAME_PATTERN.match("Player1"), "Alphanumeric name should be valid"

    def test_valid_name_pattern_accepts_spaces(self) -> None:
        assert _VALID_NAME_PATTERN.match("John Doe"), "Name with spaces should be valid"

    def test_valid_name_pattern_accepts_mixed(self) -> None:
        assert _VALID_NAME_PATTERN.match("Ace 42 Bravo"), "Mixed alphanumeric with spaces should be valid"

    def test_valid_name_pattern_rejects_empty(self) -> None:
        assert not _VALID_NAME_PATTERN.match(""), "Empty string should not match"

    def test_valid_name_pattern_rejects_special_characters(self) -> None:
        for char in ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_", "=", "+"]:
            name = f"Name{char}"
            assert not _VALID_NAME_PATTERN.match(name), f"Name with '{char}' should be rejected"

    def test_valid_name_pattern_rejects_unicode(self) -> None:
        assert not _VALID_NAME_PATTERN.match("Ren\u00e9"), "Name with accented characters should be rejected"

    def test_valid_name_pattern_rejects_tabs_and_newlines(self) -> None:
        assert not _VALID_NAME_PATTERN.match("Name\tTab"), "Name with tab should be rejected"
        assert not _VALID_NAME_PATTERN.match("Name\nLine"), "Name with newline should be rejected"


# ============================================================================
# Tests requiring pygame initialization
# ============================================================================

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for view tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState  # noqa: E402
from spacegame.views.achievements_view import AchievementsView  # noqa: E402
from spacegame.views.name_input_view import NameInputView  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


# ============================================================================
# Helpers
# ============================================================================


@dataclass
class _FakeAchievement:
    """Minimal achievement stub for scroll tests."""

    id: str
    category: str = "general"


def _make_achievements_view(
    achievement_count: int = 0, category: str = "general"
) -> AchievementsView:
    """Create an AchievementsView with a mocked achievement manager."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    player = MagicMock()
    achievement_manager = MagicMock()
    achievements = [
        _FakeAchievement(id=f"ach_{i}", category=category)
        for i in range(achievement_count)
    ]
    achievement_manager.get_all_achievements.return_value = achievements
    view = AchievementsView(ui_manager, player, achievement_manager)
    return view


def _make_name_input_view() -> NameInputView:
    """Create a NameInputView for testing."""
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    view = NameInputView(ui_manager)
    view.on_enter()
    return view


# ============================================================================
# AchievementsView — Scroll Offset Clamping (Issue 4.2)
# ============================================================================


class TestAchievementsViewScrollClamping:
    """Tests for AchievementsView._clamp_scroll() behavior."""

    def test_clamp_scroll_method_exists(self) -> None:
        view = _make_achievements_view()
        assert hasattr(view, "_clamp_scroll"), "AchievementsView should have _clamp_scroll method"
        assert callable(view._clamp_scroll), "_clamp_scroll should be callable"

    def test_scroll_clamped_to_zero_when_no_achievements(self) -> None:
        view = _make_achievements_view(achievement_count=0)
        view.scroll_offset = 100
        view._clamp_scroll()
        assert view.scroll_offset == 0, "Scroll offset should clamp to 0 with no achievements"

    def test_scroll_clamped_to_zero_when_content_fits(self) -> None:
        """When total content height fits in visible area, scroll should be 0."""
        # Visible area = WINDOW_HEIGHT - 70 - 108
        visible_height = WINDOW_HEIGHT - 70 - 108
        card_total = 70 + 8  # card_height + spacing
        # Use few enough achievements to fit within visible area
        count = visible_height // card_total
        view = _make_achievements_view(achievement_count=count)
        view.scroll_offset = 50
        view._clamp_scroll()
        assert view.scroll_offset == 0, (
            f"Scroll should clamp to 0 when {count} achievements fit in {visible_height}px"
        )

    def test_scroll_clamped_to_max_content_bounds(self) -> None:
        """Scroll should be clamped to max_scroll = content_height - visible_height."""
        count = 50  # Many achievements — definitely overflows
        view = _make_achievements_view(achievement_count=count)
        card_total = 70 + 8
        content_height = count * card_total
        visible_height = WINDOW_HEIGHT - 70 - 108
        expected_max = max(0, content_height - visible_height)

        view.scroll_offset = 99999
        view._clamp_scroll()
        assert view.scroll_offset == expected_max, (
            f"Scroll should clamp to {expected_max}, got {view.scroll_offset}"
        )

    def test_scroll_not_reduced_when_within_bounds(self) -> None:
        """Scroll offset already within bounds should remain unchanged."""
        count = 50
        view = _make_achievements_view(achievement_count=count)
        card_total = 70 + 8
        content_height = count * card_total
        visible_height = WINDOW_HEIGHT - 70 - 108
        max_scroll = max(0, content_height - visible_height)

        target = max_scroll // 2
        view.scroll_offset = target
        view._clamp_scroll()
        assert view.scroll_offset == target, (
            f"Scroll at {target} (within bounds) should remain unchanged"
        )

    def test_scroll_clamped_with_category_filter(self) -> None:
        """Scroll clamp should respect the active category filter."""
        view = _make_achievements_view(achievement_count=50, category="trading")
        # Set filter to a category that matches none of the achievements
        view._active_filter = "combat"
        view.scroll_offset = 100
        view._clamp_scroll()
        assert view.scroll_offset == 0, (
            "Scroll should clamp to 0 when filter matches no achievements"
        )


# ============================================================================
# NameInputView — Name Validation (Issue 6.1)
# ============================================================================


class TestNameInputViewValidation:
    """Tests for NameInputView name validation on begin button press."""

    def _simulate_begin_press(self, view: NameInputView, name: str) -> None:
        """Set the input text and simulate pressing the begin button."""
        view.name_input.set_text(name)
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": view.begin_button},
        )
        view.handle_event(event)

    def test_empty_name_rejected(self) -> None:
        view = _make_name_input_view()
        self._simulate_begin_press(view, "")
        assert view.next_state is None, "Empty name should be rejected — next_state stays None"
        view.on_exit()

    def test_whitespace_only_name_rejected(self) -> None:
        view = _make_name_input_view()
        self._simulate_begin_press(view, "   ")
        assert view.next_state is None, "Whitespace-only name should be rejected after strip()"
        view.on_exit()

    def test_special_characters_rejected(self) -> None:
        view = _make_name_input_view()
        self._simulate_begin_press(view, "H@cker!")
        assert view.next_state is None, "Name with special characters should be rejected"
        view.on_exit()

    def test_valid_alpha_name_accepted(self) -> None:
        view = _make_name_input_view()
        self._simulate_begin_press(view, "Captain")
        assert view.next_state == GameState.GALAXY_MAP, (
            "Valid alphabetic name should be accepted"
        )
        view.on_exit()

    def test_valid_alphanumeric_space_name_accepted(self) -> None:
        view = _make_name_input_view()
        self._simulate_begin_press(view, "Ace 42")
        assert view.next_state == GameState.GALAXY_MAP, (
            "Valid alphanumeric name with spaces should be accepted"
        )
        view.on_exit()

    def test_name_at_max_length_accepted(self) -> None:
        view = _make_name_input_view()
        name = "A" * MAX_NAME_LENGTH
        self._simulate_begin_press(view, name)
        assert view.next_state == GameState.GALAXY_MAP, (
            f"Name at exactly {MAX_NAME_LENGTH} chars should be accepted"
        )
        view.on_exit()

    def test_name_over_max_length_rejected(self) -> None:
        """Names over MAX_NAME_LENGTH should be rejected by the length check.

        Note: the UITextEntryLine enforces set_text_length_limit(MAX_NAME_LENGTH)
        at the UI level, but the handle_event code also checks len(name) > MAX_NAME_LENGTH
        as a server-side guard.
        """
        view = _make_name_input_view()
        # Bypass the UI length limit by patching get_text directly
        long_name = "A" * (MAX_NAME_LENGTH + 5)
        view.name_input.get_text = MagicMock(return_value=long_name)
        event = pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED,
            {"ui_element": view.begin_button},
        )
        view.handle_event(event)
        assert view.next_state is None, (
            f"Name over {MAX_NAME_LENGTH} chars should be rejected"
        )
        view.on_exit()
