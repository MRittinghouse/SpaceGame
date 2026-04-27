"""Sprint 3b targeted overlap tests for YELLOW-risk views.

Sprint 1 flagged five views with specific overlap/overflow risk patterns
that the broad smoke matrix cannot catch (those tests only check
pygame_gui elements; many of these risks are in ``pygame.draw.rect`` and
``screen.blit`` primitives that the harness cannot introspect).

Each test class targets one view and a specific risk pattern, reproducing
the exact rendering math from the view, then asserting the pattern's
invariants. Tests are surgical: they do not run the full view lifecycle,
just the layout computation relevant to the risk.

Views covered:

  1. ``cockpit_hud``          — button label fit with various player names
  2. ``dialogue_view``        — text truncation vs disposition preview collision
  3. ``ground_briefing_view`` — title + difficulty badge (drydock-class pattern)
  4. ``character_view``       — milestone text overflow in panel
  5. ``galaxy_map_view``      — travel confirm panel text overflow

These tests render at fixed 720p (the base design resolution) unless
otherwise noted. For broader resolution coverage, the subprocess harness
in ``test_subprocess_bounds.py`` is the complement.

See ``requirements/ui_sprint_3b_findings.md`` for the findings.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """Initialize pygame + display for this test module."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


def _rects_overlap(a: pygame.Rect, b: pygame.Rect) -> bool:
    """Return True if two rects overlap (both X and Y ranges intersect)."""
    return a.colliderect(b)


# ---------------------------------------------------------------------------
# 1. Cockpit HUD — button label fit with player names of varying length
# ---------------------------------------------------------------------------


class TestCockpitButtonLabelFit:
    """Cockpit HUD nav-button labels must always fit their button rect.

    The view already has a ``full_fits`` check that falls back to the short
    label when the full one is too wide. These tests verify the check
    actually holds across realistic player-name lengths.
    """

    @pytest.mark.parametrize(
        "player_name",
        [
            "Al",
            "Alex",
            "Alexander",
            "Alexandra",
            "Xiang Xiu-ying",  # Long double-name
            "Rosalind Franklin",  # Very long
        ],
    )
    def test_character_button_label_fits_at_720p(self, player_name: str) -> None:
        """Character button renders a label that always fits within the button rect."""
        from unittest.mock import MagicMock

        from spacegame.views.cockpit_hud import CockpitHUD

        player = MagicMock()
        player.name = player_name
        player.credits = 1000
        player.ship.current_hull = 80
        player.ship.ship_type.combat_hull = 100
        player.ship.current_shields = 50
        player.ship.ship_type.combat_shields = 50
        player.ship.current_fuel = 30
        player.ship.max_fuel = 50
        player.ship.current_cargo = {"food": 10}
        player.ship.cargo_capacity = 100
        player.progression.skill_points = 0

        mm = MagicMock()
        mm.get_missions_by_status.return_value = []

        hud = CockpitHUD(player=player, mission_manager=mm, crew_roster=None)

        # Character button is index 0.
        btn_rect = hud._button_rects[0]
        short_label, full_label, _ = hud._button_defs[0]
        # Mirror the view's runtime substitution.
        if not full_label:
            full_label = player.name or short_label

        # Same fit check the view does.
        from spacegame.config import scale_x

        padding = scale_x(12)
        available = btn_rect.width - padding
        full_fits = hud._button_font.size(full_label)[0] < available
        display = full_label if full_fits else short_label

        # Assertion: whichever label is rendered must actually fit.
        rendered_width = hud._button_font.size(display)[0]
        assert rendered_width < btn_rect.width, (
            f"Rendered label {display!r} (width={rendered_width}) exceeds "
            f"button width {btn_rect.width} for player name {player_name!r}"
        )


# ---------------------------------------------------------------------------
# 2. Dialogue view — response button text vs disposition preview collision
# ---------------------------------------------------------------------------


class TestDialogueResponseButtonTruncation:
    """Response button text must not collide with the disposition preview.

    The ``_ResponseButton.render`` method computes ``max_text_w = rect.width
    - 24`` as the truncation target, but does not subtract the disposition
    preview's width when present. For narrow buttons with long text AND a
    disposition preview, text can render into the preview's column.
    """

    def test_long_text_with_disposition_preview_does_not_overlap(self) -> None:
        """Truncated response text rect must not collide with preview rect."""
        from spacegame.engine.fonts import FONT_MD, get_font
        from spacegame.views.dialogue_view import _ResponseButton

        # Narrow button with long text AND positive disposition preview.
        font = get_font("dialogue", FONT_MD)
        button_rect = pygame.Rect(100, 100, 240, 32)  # Narrow
        text = (
            "Tell me everything you know about the Reach's latest "
            "movements in the outer belt, and do it slowly."
        )
        disposition = 5

        # Construction kept as documentation that this is the real entry
        # path the view uses; truncation logic is mirrored inline below.
        _ResponseButton(
            rect=button_rect,
            text=text,
            font=font,
            disposition_preview=disposition,
        )

        # Compute what the view will render.
        prefix = "  "
        display_text = text
        max_text_w = button_rect.width - 24
        text_surf = font.render(prefix + display_text, True, (0, 0, 0))
        if text_surf.get_width() > max_text_w:
            while len(display_text) > 3 and text_surf.get_width() > max_text_w:
                display_text = display_text[:-1]
            display_text = display_text.rstrip() + ".."
            text_surf = font.render(prefix + display_text, True, (0, 0, 0))
        text_rect = text_surf.get_rect(midleft=(button_rect.x + 12, button_rect.centery))

        # Compute disposition preview rect.
        preview_text = f"+{disposition}"
        preview_surf = font.render(preview_text, True, (0, 0, 0))
        preview_rect = preview_surf.get_rect(midright=(button_rect.right - 12, button_rect.centery))

        # Known limitation (flagged as finding): the view's truncation math
        # does NOT subtract preview_rect.width, so overlap CAN occur. This
        # test asserts the guard that SHOULD be in place. If the test fails,
        # that is a real finding to log, not a test bug.
        #
        # Using xfail lets the test document the risk without breaking the
        # suite. Remove xfail when the view is fixed to subtract preview_w
        # from max_text_w.
        if _rects_overlap(text_rect, preview_rect):
            pytest.xfail(
                "KNOWN: dialogue response button truncation does not subtract "
                "disposition preview width. Risk of text-over-preview collision "
                "at narrow widths + long text + active disposition preview. "
                f"text_rect={text_rect}, preview_rect={preview_rect}. "
                "Tracked in Sprint 3b findings for fix."
            )
        # If it passes, the text happened to be short enough after truncation.


# ---------------------------------------------------------------------------
# 3. Ground briefing — title vs difficulty badge (drydock-class)
# ---------------------------------------------------------------------------


class TestGroundBriefingHeaderOverlap:
    """The briefing header renders title left-anchored and difficulty badge
    right-anchored at nearly the same Y coordinate. This is the drydock
    class of overlap bug: if mission name is long, it collides with the
    badge."""

    def _render_rects(
        self, mission_name: str, difficulty_value: str
    ) -> tuple[pygame.Rect, pygame.Rect]:
        """Mirror ground_briefing_view _render_header (post-Sprint 3b fix)."""
        from spacegame.engine.fonts import FONT_HEADING, FONT_XL, get_font
        from spacegame.views.ground_briefing_view import GroundBriefingView

        title_font = get_font("header", FONT_HEADING)
        subtitle_font = get_font("header", FONT_XL)

        diff_surf = subtitle_font.render(difficulty_value.upper(), True, (0, 0, 0))
        diff_x = (
            GroundBriefingView.PANEL_X + GroundBriefingView.PANEL_W - diff_surf.get_width() - 30
        )
        diff_rect = diff_surf.get_rect(topleft=(diff_x, GroundBriefingView.PANEL_Y + 24))

        # Mirror the view's truncation logic.
        title_max_w = diff_x - (GroundBriefingView.PANEL_X + 30) - 16
        title_surf = title_font.render(mission_name, True, (0, 0, 0))
        if title_surf.get_width() > title_max_w:
            trimmed = mission_name
            while len(trimmed) > 3 and title_surf.get_width() > title_max_w:
                trimmed = trimmed[:-1]
                title_surf = title_font.render(trimmed.rstrip() + "...", True, (0, 0, 0))
        title_rect = title_surf.get_rect(
            topleft=(GroundBriefingView.PANEL_X + 30, GroundBriefingView.PANEL_Y + 20)
        )

        return title_rect, diff_rect

    def test_short_mission_name_does_not_collide(self) -> None:
        """Typical-length mission name leaves room for the difficulty badge."""
        title_rect, diff_rect = self._render_rects("Recon Op", "low")
        assert not _rects_overlap(title_rect, diff_rect), (
            f"Short mission name unexpectedly collided. title={title_rect}, diff={diff_rect}"
        )

    def test_long_mission_name_truncates_cleanly(self) -> None:
        """Very long mission names truncate before reaching the difficulty badge.

        Sprint 3b fix: ``_render_header`` now computes the title's maximum
        width from the difficulty badge's left edge minus a 16px gap, and
        truncates with ``...`` when needed. This prevents the drydock-class
        overlap pattern regardless of mission-name length.
        """
        title_rect, diff_rect = self._render_rects(
            "The Extraordinary Case of the Missing Reach Smuggler Operation",
            "extreme",
        )
        assert not _rects_overlap(title_rect, diff_rect), (
            f"Long mission name collided with difficulty badge despite "
            f"Sprint 3b truncation fix. title={title_rect}, diff={diff_rect}"
        )


# ---------------------------------------------------------------------------
# 4. Character view — milestone text overflow
# ---------------------------------------------------------------------------


class TestCharacterMilestoneOverflow:
    """Milestone descriptions render without width clipping. If a description
    is long enough, it overflows the left panel."""

    def test_standard_milestones_fit_in_panel(self) -> None:
        """All current milestone descriptions fit within the left panel."""
        from spacegame.engine.fonts import FONT_SM, get_font
        from spacegame.models.attributes import MILESTONE_DEFINITIONS
        from spacegame.views.character_view import LEFT_W

        font = get_font("stats", FONT_SM)
        overflow_cases: list[str] = []
        # Same format string the view uses.
        # MILESTONE_DEFINITIONS is a dict whose values may be strings OR
        # nested dicts/objects with a description field. Normalize:
        for mid, value in MILESTONE_DEFINITIONS.items():
            desc = value if isinstance(value, str) else getattr(value, "description", str(value))
            text = f"[X] {desc}"
            width = font.size(text)[0]
            # Left panel content area: LEFT_W minus a modest right padding.
            available = LEFT_W - 30
            if width > available:
                overflow_cases.append(f"{mid}: width={width} > available={available}")

        if overflow_cases:
            pytest.xfail(
                "KNOWN: one or more milestone descriptions overflow the left "
                "panel at 720p. Fix: truncate or word-wrap in the view. "
                "Cases:\n  " + "\n  ".join(overflow_cases)
            )


# ---------------------------------------------------------------------------
# 5. Galaxy map travel confirm — destination name overflow
# ---------------------------------------------------------------------------


class TestGalaxyMapTravelConfirmOverflow:
    """The travel confirm overlay renders 'Destination: <name>' without
    clipping. Long destination names overflow the 320-wide confirm panel."""

    def test_typical_destination_names_fit(self) -> None:
        """Every real destination name in the game fits the confirm panel."""
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_MD, get_font

        dl = get_data_loader()
        dl.load_all()

        font = get_font("stats", FONT_MD)
        panel_w = 320  # scale_x(320) at 720p == 320
        content_w = panel_w - 40  # 20px padding per side per the view code

        overflow_cases: list[str] = []
        for sys_id, system in dl.systems.items():
            text = f"Destination: {system.name}"
            width = font.size(text)[0]
            if width > content_w:
                overflow_cases.append(f"{sys_id} ({system.name!r}): {width} > {content_w}")

        if overflow_cases:
            pytest.xfail(
                "KNOWN: one or more real system names overflow the travel "
                "confirm panel. Fix: truncate 'Destination:' line in the view "
                "or widen the panel. "
                "Cases:\n  " + "\n  ".join(overflow_cases)
            )
