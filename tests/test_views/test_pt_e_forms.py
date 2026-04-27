"""PT-E "Forms that behave" regression tests.

Covers:
  - PT-008: tutorial shop part descriptions render on multi-line word wrap
  - PT-012: confirm-build skips naming dialog when ship_name is set
  - PT-012: explicit RENAME button opens naming dialog; rename-only path
            saves name without finalizing the build
  - PT-012: numpad Enter (K_KP_ENTER) confirms naming dialog
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1280, 720))
    yield


# ---------------------------------------------------------------------------
# PT-008: Tutorial shop descriptions wrap instead of truncating
# ---------------------------------------------------------------------------


class TestTutorialShopDescriptions:
    def test_descriptions_use_word_wrap_not_truncate(self) -> None:
        """Verify _render_part_card uses word_wrap on the description so
        full text shows across two lines instead of single-line ellipsis.

        Truncation is allowed for the part NAME (which is single-line and
        was overflowing card width on long names like 'Salvaged Pulse
        Emitter' — fixed 2026-04-24). What's banned is truncating the
        DESCRIPTION text.
        """
        from pathlib import Path

        source = Path("spacegame/views/tutorial_shop_view.py").read_text(encoding="utf-8")
        render_start = source.index("def _render_part_card")
        render_end = source.index("def ", render_start + 1)
        body = source[render_start:render_end]
        assert "word_wrap" in body, "tutorial shop should call word_wrap on descriptions"
        # The description rendering block must use word_wrap, not truncate.
        # Locate the description section by its anchor comment + ensure
        # truncate_text is not invoked on `part["description"]`.
        assert 'truncate_text(part["description"]' not in body, (
            "tutorial shop should render full descriptions via word_wrap, not truncate"
        )
        assert "truncate_text(part.description" not in body, (
            "tutorial shop should render full descriptions via word_wrap, not truncate"
        )

    def test_descriptions_visible_for_all_tutorial_parts(self) -> None:
        """All TUTORIAL_PARTS and TUTORIAL_CHOICES have description text."""
        from spacegame.views.tutorial_shop_view import TUTORIAL_CHOICES, TUTORIAL_PARTS

        for part in TUTORIAL_PARTS + TUTORIAL_CHOICES:
            assert part.description, f"part missing description: {part.name}"
            assert len(part.description) > 10, f"part description too short: {part.name}"


# ---------------------------------------------------------------------------
# PT-012: Confirm-build skips naming dialog when ship_name is set
# ---------------------------------------------------------------------------


def _make_builder_for_confirm():
    """Minimal ShipBuilderView with stubs sufficient to test _confirm_build."""
    from spacegame.views.ship_builder_view import ShipBuilderView

    view = ShipBuilderView.__new__(ShipBuilderView)
    view._tutorial_mode = False
    view._can_confirm = True
    view._naming_active = False
    view._naming_text = ""
    view._naming_cursor_timer = 0.0
    view._rename_only = False
    view._modified = True
    view.player = MagicMock()
    view.player.ship_name = "Black Kite"
    view.player.credits = 10_000
    view.player.ship = MagicMock()
    view._computed_stats = MagicMock()
    view._computed_stats.total_cost = 0
    view._entry_cost = 0
    view._confirm_anim_timer = 0.0
    view._confirm_anim_surface = None
    # Stub _finalize_build so we can observe whether it was called.
    view._finalize_build = MagicMock()
    return view


class TestConfirmBuildNamingSkip:
    def test_skips_naming_when_ship_has_name(self) -> None:
        view = _make_builder_for_confirm()
        view.player.ship_name = "Black Kite"
        view._confirm_build()
        # Dialog never opens; _finalize_build runs directly.
        assert view._naming_active is False
        view._finalize_build.assert_called_once()

    def test_opens_naming_when_ship_unnamed(self) -> None:
        view = _make_builder_for_confirm()
        view.player.ship_name = ""
        view.player.ship.ship_type.name = "Shuttle"
        view._confirm_build()
        # No name yet — dialog opens, build not yet finalized.
        assert view._naming_active is True
        view._finalize_build.assert_not_called()


# ---------------------------------------------------------------------------
# PT-012: Rename-only path saves name without finalizing
# ---------------------------------------------------------------------------


class TestRenameOnlyPath:
    def _make_view(self):
        from spacegame.views.ship_builder_view import ShipBuilderView

        view = ShipBuilderView.__new__(ShipBuilderView)
        view._naming_active = True
        view._naming_text = "New Name"
        view._rename_only = True
        view.player = MagicMock()
        view.player.ship_name = "Old Name"
        view._finalize_build = MagicMock()
        return view

    def test_rename_only_sets_name_and_closes_dialog(self) -> None:
        view = self._make_view()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"})
        view._handle_naming_event(evt)
        assert view.player.ship_name == "New Name"
        assert view._naming_active is False
        assert view._rename_only is False
        view._finalize_build.assert_not_called()

    def test_rename_only_blank_keeps_current_name(self) -> None:
        view = self._make_view()
        view._naming_text = "   "  # whitespace only
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\r"})
        view._handle_naming_event(evt)
        assert view.player.ship_name == "Old Name"
        assert view._naming_active is False

    def test_escape_cancels_rename(self) -> None:
        view = self._make_view()
        view._naming_text = "New Name"
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""})
        view._handle_naming_event(evt)
        assert view.player.ship_name == "Old Name"  # unchanged
        assert view._naming_active is False
        assert view._rename_only is False


# ---------------------------------------------------------------------------
# PT-012: Numpad Enter also confirms the naming dialog
# ---------------------------------------------------------------------------


class TestNumpadEnter:
    def test_kp_enter_finalizes_build(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        view = ShipBuilderView.__new__(ShipBuilderView)
        view._naming_active = True
        view._naming_text = "Test Ship"
        view._rename_only = False
        view.player = MagicMock()
        view._finalize_build = MagicMock()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_KP_ENTER, "unicode": "\r"})
        view._handle_naming_event(evt)
        view._finalize_build.assert_called_once()

    def test_kp_enter_saves_rename(self) -> None:
        from spacegame.views.ship_builder_view import ShipBuilderView

        view = ShipBuilderView.__new__(ShipBuilderView)
        view._naming_active = True
        view._naming_text = "New"
        view._rename_only = True
        view.player = MagicMock()
        view.player.ship_name = "Old"
        view._finalize_build = MagicMock()
        evt = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_KP_ENTER, "unicode": "\r"})
        view._handle_naming_event(evt)
        assert view.player.ship_name == "New"
        view._finalize_build.assert_not_called()
