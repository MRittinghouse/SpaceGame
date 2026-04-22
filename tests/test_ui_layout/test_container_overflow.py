"""Sprint 3c — container overflow probes.

Data-driven tests: for each content type the game renders in a
fixed-width container, iterate every real entry through the view's
layout math and assert the rendered text fits. When content gets
added or renamed, these tests surface overflows automatically.

Tests run at **720p** because that is the tightest horizontal
constraint in the supported matrix. Fonts are fixed pixel size (see
Sprint 3a notes on ``get_font``) while containers scale proportionally,
so text that fits at 720p fits at every higher resolution.

See ``requirements/ui_sprint_3c_findings.md`` for the catalog of
findings. Findings classified as:

  - FIT: all current content fits; test is a regression guard
  - CATALOGUED: real overflow exists with current content; test uses
    xfail to document without breaking the suite; fix is scheduled
    in findings doc
  - FIXED: view-level truncation added; test asserts clean fit
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


# ---------------------------------------------------------------------------
# Helper — measure overflow
# ---------------------------------------------------------------------------


def _measure_overflow(
    texts: list[tuple[str, str]],
    font: pygame.font.Font,
    available_width: int,
) -> list[tuple[str, str, int]]:
    """Return (id, text, rendered_width) for every entry that overflows."""
    offenders = []
    for entry_id, text in texts:
        width = font.size(text)[0]
        if width > available_width:
            offenders.append((entry_id, text, width))
    return offenders


# ---------------------------------------------------------------------------
# Mission log list items — name left + badge right, no truncation (FIXED)
# ---------------------------------------------------------------------------


class TestMissionLogListOverflow:
    """Mission name in the mission log list must not overflow into the
    status/type badge on the right.

    Pattern: `_MissionItem.render` blits ``mission.name`` at
    ``midleft=(rect.x + 14, centery)`` and the badge at
    ``midright=(rect.right - 10, centery)``. Same Y, no truncation.
    Drydock-class drift risk.
    """

    def test_all_missions_fit_list_item_width(self) -> None:
        """Every mission name fits the list item with badge reserved."""
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_SM, get_font
        from spacegame.views.layout import LIST_ITEM_HEIGHT, LIST_WIDTH

        dl = get_data_loader()
        dl.load_all()

        # Mission log uses role "dialogue" at FONT_SM for list text.
        font = get_font("dialogue", FONT_SM)
        badge_font = get_font("label", FONT_SM)

        # Worst-case badge is "ABANDONED" (longest status).
        worst_badge_w = badge_font.size("ABANDONED")[0]

        # Available for name text:
        #   list row width = LIST_WIDTH
        #   - 14px left padding
        #   - 10px right margin
        #   - badge width
        #   - 10px gap between name and badge (post-fix)
        available = LIST_WIDTH - 14 - 10 - worst_badge_w - 10

        # Assume list item height is at least LIST_ITEM_HEIGHT for context.
        assert LIST_ITEM_HEIGHT > 0

        # dl.missions is a list of Mission objects.
        texts = [(m.id, m.name) for m in dl.missions]
        offenders = _measure_overflow(texts, font, available)

        if offenders:
            report = "\n".join(
                f"  {mid}: {name!r} rendered={width}px > available={available}px"
                for mid, name, width in offenders[:20]
            )
            pytest.fail(
                f"Mission names overflow list item at 720p "
                f"(available={available}px). Fix: truncate name in "
                f"_MissionItem.render the same way we fixed ground_briefing:\n"
                + report
            )


# ---------------------------------------------------------------------------
# Crew roster list items — name left + badge right, no truncation (FIXED)
# ---------------------------------------------------------------------------


class TestCrewRosterListOverflow:
    """Crew member name in the roster list must not overflow the
    right-side level/role badge."""

    def test_all_crew_fit_list_item_width(self) -> None:
        """Every crew template name fits the list item with badge reserved."""
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_SM, get_font
        from spacegame.views.layout import LIST_WIDTH

        dl = get_data_loader()
        dl.load_all()

        font = get_font("dialogue", FONT_SM)

        # Worst-case badge for companions: "Lv 99" (5 chars + space).
        worst_badge_text = "Lv 99"
        worst_badge_w = font.size(worst_badge_text)[0]

        # Available = LIST_WIDTH - 14 (left pad) - 14 (right pad) - badge - 10 (gap)
        available = LIST_WIDTH - 14 - 14 - worst_badge_w - 10

        texts = [(t.id, t.name) for t in dl.crew_templates.values()]
        offenders = _measure_overflow(texts, font, available)

        if offenders:
            report = "\n".join(
                f"  {cid}: {name!r} rendered={width}px > available={available}px"
                for cid, name, width in offenders[:20]
            )
            pytest.fail(
                f"Crew names overflow list item at 720p "
                f"(available={available}px):\n" + report
            )


# ---------------------------------------------------------------------------
# Trading view commodity rows — name column must fit
# ---------------------------------------------------------------------------


class TestTradingCommodityNameOverflow:
    """Commodity names in trading view rows fit the name column.

    Post-Sprint 5b refactor: legality no longer renders as a text suffix
    on the name. It lives in a dedicated ``LEG`` column (35px at 720p).
    This decouples name-column budget from legality display — long names
    can still truncate via the table widget's ellipsis, but the legality
    indicator is always visible in its own column regardless of name
    length.
    """

    def test_commodity_names_fit_column_without_suffix(self) -> None:
        """Plain commodity names fit the COMMODITY column at 720p.

        The column is 240px wide; after the table widget's CELL_PAD (8px
        each side), effective budget is ~224px. Two commodity names exceed
        that and rely on the table's ellipsis truncation — acceptable
        because the legality indicator (the Sprint 5b fix target) is in a
        separate column and unaffected.
        """
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_SM, get_font

        dl = get_data_loader()
        dl.load_all()

        font = get_font("dialogue", FONT_SM)
        col_width = 240 - 16  # scale_x(240) - CELL_PAD * 2 at 720p

        # Names without ANY legality suffix — the post-refactor reality.
        texts = [(cid, c.name) for cid, c in dl.commodities.items()]
        offenders = _measure_overflow(texts, font, col_width)

        # Two commodity names are longer than the column but truncate
        # cleanly via the table widget; legality column is unaffected.
        # The budget after truncation cost is still positive for all
        # known content.
        assert len(offenders) <= 2, (
            f"More commodity names overflow than the accepted baseline of "
            f"two (table widget truncates cleanly up to that threshold). "
            f"Current offenders: {offenders}"
        )

    def test_legality_column_width_fits_markers(self) -> None:
        """The LEG column is wide enough for the marker variants.

        Variants: "", "R", "!", "R*", "!*" (the asterisk denotes the
        smugglers_eye-active rendering). All must fit the column budget.
        """
        from spacegame.engine.fonts import FONT_SM, get_font

        font = get_font("dialogue", FONT_SM)
        col_width = 35 - 16  # scale_x(35) - CELL_PAD * 2 at 720p; ~19px

        for marker in ("R", "!", "R*", "!*"):
            width = font.size(marker)[0]
            assert width <= col_width, (
                f"Legality marker {marker!r} ({width}px) exceeds LEG column "
                f"budget ({col_width}px)."
            )


# ---------------------------------------------------------------------------
# Achievement cards — achievement names fit the card
# ---------------------------------------------------------------------------


class TestAchievementNameOverflow:
    """Achievement names in the achievements view card must fit the card
    width with reward badge reserved."""

    def test_all_achievement_names_fit_card(self) -> None:
        """Every achievement name fits the card's name area at 720p."""
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_SUBTITLE, get_font

        dl = get_data_loader()
        dl.load_all()

        # Achievement card width = scale_x(550) at 720p.
        # Name renders at (x + 30, y + 8) per _render_achievement_card.
        # Reward text renders at (x + width - 100, y + 10).
        # Available for name = width - 30 (left after badge) - 100 (reward reserve) - 10 gap.
        card_w = 550
        available = card_w - 30 - 100 - 10

        font = get_font("dialogue", FONT_SUBTITLE)

        texts = [(a.id, a.name) for a in dl.achievements]
        offenders = _measure_overflow(texts, font, available)

        if offenders:
            report = "\n".join(
                f"  {aid}: {name!r} rendered={width}px > available={available}px"
                for aid, name, width in offenders[:20]
            )
            pytest.fail(
                f"Achievement names overflow the card name area at 720p "
                f"(available={available}px):\n" + report
            )


# ---------------------------------------------------------------------------
# Galaxy map system labels — short abbreviated labels
# ---------------------------------------------------------------------------


class TestGalaxySystemLabelOverflow:
    """System labels drawn on the galaxy map must not be so long they
    cover adjacent systems."""

    def test_all_system_names_reasonable_label_width(self) -> None:
        """Every system name fits a reasonable label budget on the map.

        The galaxy map draws system labels near their map node. There is
        no strict container, but labels wider than ~160px at 720p push
        into adjacent map regions and become unreadable.
        """
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_SM, get_font

        dl = get_data_loader()
        dl.load_all()

        font = get_font("label", FONT_SM)

        # Soft budget: 160px at 720p. Beyond this, labels crowd the map.
        soft_budget = 160

        texts = [(sid, sys.name) for sid, sys in dl.systems.items()]
        offenders = _measure_overflow(texts, font, soft_budget)

        # Informational — no assertion. System name length is a content
        # decision; we just surface any egregious cases.
        if offenders:
            report = "\n".join(
                f"  {sid}: {name!r} rendered={width}px > budget={soft_budget}px"
                for sid, name, width in offenders
            )
            # Use a warning, not a failure. The map has pan/zoom so a
            # slightly wide label is tolerable.
            print("\nWARN (informational): system labels exceeding soft map budget:")
            print(report)


# ---------------------------------------------------------------------------
# Enemy template names — combat enemy header
# ---------------------------------------------------------------------------


class TestEnemyTemplateNameOverflow:
    """Enemy template names rendered in combat headers must fit the
    enemy card's name column."""

    def test_all_enemy_names_fit_header(self) -> None:
        """Every enemy template name fits a typical enemy-card header width."""
        from spacegame.data_loader import get_data_loader
        from spacegame.engine.fonts import FONT_MD, get_font

        dl = get_data_loader()
        dl.load_all()

        font = get_font("dialogue", FONT_MD)

        # Enemy card width at 720p is roughly scale_x(330).
        # Header has a tier stamp on the right taking ~60px.
        # Available for name ~ 330 - 20 (left pad) - 60 (tier) - 10 (gap).
        available = 330 - 20 - 60 - 10

        texts = [(eid, e.name) for eid, e in dl.enemy_templates.items()]
        offenders = _measure_overflow(texts, font, available)

        if offenders:
            report = "\n".join(
                f"  {eid}: {name!r} rendered={width}px > available={available}px"
                for eid, name, width in offenders[:20]
            )
            pytest.xfail(
                f"CATALOGUED: enemy template names can overflow combat card "
                f"header at 720p (available={available}px). Fix: truncate in "
                f"combat_view enemy-card renderer, or tighten template names. "
                f"{len(offenders)} overflow; first few:\n" + report
            )
