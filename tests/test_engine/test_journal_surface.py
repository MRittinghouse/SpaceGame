"""Tests for the shared JournalSurface UI primitive.

Covers the data model, state machine (tab/entry selection, scroll),
rendering behavior, click-to-event mapping, and palette compliance.

See ``requirements/overhaul/42_ui_chrome_components.md §5.6``.
"""

from __future__ import annotations

from typing import Optional

import pygame
import pytest

from spacegame.engine.journal_surface import (
    JournalEntryView,
    JournalEvent,
    JournalSurface,
    JournalTab,
    JournalTheme,
)


@pytest.fixture(autouse=True)
def _pygame_init() -> None:
    pygame.init()


def _tabs(*ids: str) -> list[JournalTab]:
    return [JournalTab(tab_id=tid, label=tid.upper()) for tid in ids]


def _entry(entry_id: str, category: str, title: Optional[str] = None) -> JournalEntryView:
    return JournalEntryView(
        entry_id=entry_id,
        title=title or f"Entry {entry_id}",
        body=f"Body of entry {entry_id}.",
        category=category,
    )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class TestJournalEntryView:
    def test_defaults(self) -> None:
        e = JournalEntryView(entry_id="e1", title="T", body="B")
        assert e.category == ""
        assert e.metadata == {}
        assert e.cross_references == []
        assert e.timestamp == 0

    def test_full_payload(self) -> None:
        e = JournalEntryView(
            entry_id="e1",
            title="T",
            body="B",
            category="campaign",
            metadata={"Date": "Day 42"},
            cross_references=["e2"],
            timestamp=42,
        )
        assert e.metadata == {"Date": "Day 42"}
        assert e.cross_references == ["e2"]
        assert e.timestamp == 42


class TestJournalTheme:
    def test_defaults_are_valid_palette_roles(self) -> None:
        from spacegame.engine.material_palette import is_valid_role

        theme = JournalTheme()
        for field_name, role in vars(theme).items():
            assert is_valid_role(role), (
                f"Theme default {field_name}='{role}' is not a canonical palette role"
            )

    def test_customization_rewrites_single_roles(self) -> None:
        theme = JournalTheme(accent_role="hud_accent_warm", border_role="weld")
        assert theme.accent_role == "hud_accent_warm"
        assert theme.border_role == "weld"
        # Unset fields keep default
        assert theme.text_role == "hud_text"


class TestJournalEvent:
    def test_event_is_hashable(self) -> None:
        e1 = JournalEvent(kind="tab_changed", payload="campaign")
        e2 = JournalEvent(kind="tab_changed", payload="campaign")
        assert e1 == e2
        assert hash(e1) == hash(e2)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestJournalSurfaceConstruction:
    def test_requires_at_least_one_tab(self) -> None:
        with pytest.raises(ValueError):
            JournalSurface(tabs=[])

    def test_selects_first_tab_by_default(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        assert surf.selected_tab_id == "campaign"

    def test_default_theme_applied(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        assert isinstance(surf.theme, JournalTheme)

    def test_custom_theme_applied(self) -> None:
        theme = JournalTheme(accent_role="hud_warning")
        surf = JournalSurface(tabs=_tabs("a"), theme=theme)
        assert surf.theme.accent_role == "hud_warning"

    def test_no_entry_selected_on_construction(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        assert surf.selected_entry_id is None
        assert surf.scroll_offset == 0


# ---------------------------------------------------------------------------
# Tab navigation
# ---------------------------------------------------------------------------


class TestTabNavigation:
    def test_select_valid_tab(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        changed = surf.select_tab("archive")
        assert changed
        assert surf.selected_tab_id == "archive"

    def test_select_same_tab_is_noop(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        assert not surf.select_tab("campaign")

    def test_select_unknown_tab_returns_false(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign"))
        assert not surf.select_tab("does_not_exist")
        assert surf.selected_tab_id == "campaign"

    def test_tab_switch_clears_scroll(self) -> None:
        surf = JournalSurface(tabs=_tabs("a", "b"))
        surf.scroll(100)
        assert surf.scroll_offset == 100
        surf.select_tab("b")
        assert surf.scroll_offset == 0

    def test_tab_switch_clears_selection_if_different_category(self) -> None:
        surf = JournalSurface(tabs=_tabs("a", "b"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "b")])
        surf.select_entry("e1")
        assert surf.selected_entry_id == "e1"
        surf.select_tab("b")
        # e1 belongs to "a", no longer visible in "b" — cleared.
        assert surf.selected_entry_id is None

    def test_tab_switch_keeps_selection_if_category_matches(self) -> None:
        surf = JournalSurface(tabs=_tabs("a", "b"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "b")])
        surf.select_entry("e1")
        # Selecting "a" (same as current) is a no-op for selection.
        assert surf.select_tab("a") is False
        assert surf.selected_entry_id == "e1"


# ---------------------------------------------------------------------------
# Entry selection
# ---------------------------------------------------------------------------


class TestEntrySelection:
    def test_select_valid_entry(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        assert surf.select_entry("e1")
        assert surf.selected_entry_id == "e1"

    def test_select_unknown_entry_returns_false(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        assert not surf.select_entry("nope")
        assert surf.selected_entry_id is None

    def test_select_same_entry_is_noop(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        surf.select_entry("e1")
        assert not surf.select_entry("e1")

    def test_set_entries_clears_stale_selection(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        surf.select_entry("e1")
        surf.set_entries([_entry("e2", "a")])
        assert surf.selected_entry_id is None

    def test_set_entries_preserves_valid_selection(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "a")])
        surf.select_entry("e2")
        surf.set_entries([_entry("e2", "a"), _entry("e3", "a")])
        assert surf.selected_entry_id == "e2"

    def test_select_entry_in_other_tab_switches_tab(self) -> None:
        """Jumping to a cross-referenced entry should follow the entry's tab."""
        surf = JournalSurface(tabs=_tabs("a", "b"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "b")])
        surf.select_entry("e2")
        assert surf.selected_tab_id == "b"
        assert surf.selected_entry_id == "e2"


# ---------------------------------------------------------------------------
# Scroll
# ---------------------------------------------------------------------------


class TestScrollBehavior:
    def test_scroll_positive_increases_offset(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.scroll(40)
        assert surf.scroll_offset == 40

    def test_scroll_below_zero_clamps_to_zero(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.scroll(-500)
        assert surf.scroll_offset == 0

    def test_scroll_upper_bound_clamped_after_render(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry(f"e{i}", "a") for i in range(3)])
        surf.scroll(10_000)
        target = pygame.Surface((400, 300), pygame.SRCALPHA)
        surf.render(target, pygame.Rect(0, 0, 400, 300))
        # With only 3 short entries in a 300px-tall surface, scroll has no room.
        assert surf.scroll_offset == 0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render(surf: JournalSurface, w: int = 600, h: int = 400) -> pygame.Surface:
    target = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.render(target, pygame.Rect(0, 0, w, h))
    return target


class TestRendering:
    def test_render_produces_non_transparent_surface(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign"))
        out = _render(surf)
        # A ship of pixels inside the journal area should be opaque.
        px = out.get_at((100, 100))
        assert px.a == 255

    def test_render_empty_state_when_no_entries(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign"))
        out = _render(surf)
        # No crash; central pixels include the "No entries yet." message —
        # verify opacity only (text content is visual).
        assert out.get_at((300, 200)).a == 255

    def test_render_produces_same_output_with_no_state_change(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        surf.select_entry("e1")
        a = _render(surf)
        b = _render(surf)
        for y in range(a.get_height()):
            for x in range(a.get_width()):
                assert a.get_at((x, y)) == b.get_at((x, y))

    def test_theme_accent_change_shifts_rendered_colors(self) -> None:
        """Changing the accent role must visibly change output."""
        theme_warm = JournalTheme(accent_role="hud_accent_warm")
        theme_cool = JournalTheme(accent_role="hud_cyan")

        surf_warm = JournalSurface(tabs=_tabs("a"), theme=theme_warm)
        surf_cool = JournalSurface(tabs=_tabs("a"), theme=theme_cool)

        a = _render(surf_warm)
        b = _render(surf_cool)

        # Somewhere in the tab bar, accent-colored pixels must differ.
        differ = False
        for y in range(40):
            for x in range(200):
                if a.get_at((x, y)) != b.get_at((x, y)):
                    differ = True
                    break
            if differ:
                break
        assert differ, "Theme accent change should alter tab bar rendering"

    def test_selection_highlight_renders(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "a")])
        a = _render(surf)
        surf.select_entry("e2")
        b = _render(surf)
        # Selection must change the entry list region (leftmost panel).
        differ = False
        for y in range(50, 200):
            for x in range(150):
                if a.get_at((x, y)) != b.get_at((x, y)):
                    differ = True
                    break
            if differ:
                break
        assert differ

    def test_metadata_strip_count_reflects_entries(self) -> None:
        """Rendering 0 vs N entries produces different metadata-strip output."""
        surf0 = JournalSurface(tabs=_tabs("a"))
        surf3 = JournalSurface(tabs=_tabs("a"))
        surf3.set_entries([_entry(f"e{i}", "a") for i in range(3)])

        a = _render(surf0)
        b = _render(surf3)
        # Metadata strip is at the bottom ~22px
        differ = False
        for y in range(380, 400):
            for x in range(200):
                if a.get_at((x, y)) != b.get_at((x, y)):
                    differ = True
                    break
            if differ:
                break
        assert differ


# ---------------------------------------------------------------------------
# Click / interaction
# ---------------------------------------------------------------------------


class TestHitDetection:
    def test_click_on_tab_emits_tab_changed(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        _render(surf)
        # "campaign" is selected by default; click should land on "archive".
        # Tabs start at left padding (8) and flow right. Click in the second
        # tab region — roughly column 150.
        event = surf.handle_click((150, 18))
        assert event is not None
        assert event.kind == "tab_changed"
        assert event.payload == "archive"
        assert surf.selected_tab_id == "archive"

    def test_click_on_same_tab_returns_none(self) -> None:
        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        _render(surf)
        event = surf.handle_click((30, 18))  # inside "campaign"
        # Clicking the already-selected tab is a no-op.
        assert event is None

    def test_click_on_entry_emits_entry_selected(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a"), _entry("e2", "a")])
        _render(surf)
        # First entry lives at approximately y=36+8 (tab bar + padding).
        event = surf.handle_click((50, 50))
        assert event is not None
        assert event.kind == "entry_selected"
        assert event.payload == "e1"
        assert surf.selected_entry_id == "e1"

    def test_click_outside_hit_region_returns_none(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries([_entry("e1", "a")])
        _render(surf)
        # Click deep in the detail pane, far from any hit region.
        event = surf.handle_click((500, 200))
        assert event is None

    def test_cross_reference_click_jumps_to_entry(self) -> None:
        surf = JournalSurface(tabs=_tabs("a"))
        surf.set_entries(
            [
                JournalEntryView(
                    entry_id="src",
                    title="Source Entry",
                    body="Short.",
                    category="a",
                    cross_references=["tgt"],
                ),
                _entry("tgt", "a", title="Target Entry"),
            ]
        )
        surf.select_entry("src")
        _render(surf)
        # Scan the whole surface for a cross_reference_clicked hit region.
        xref_rects = [
            rect
            for rect, event in surf._hit_regions
            if event.kind == "cross_reference_clicked" and event.payload == "tgt"
        ]
        assert xref_rects, "Expected a cross-reference hit region"
        rect = xref_rects[0]
        event = surf.handle_click((rect.centerx, rect.centery))
        assert event is not None
        assert event.kind == "cross_reference_clicked"
        assert event.payload == "tgt"
        assert surf.selected_entry_id == "tgt"


# ---------------------------------------------------------------------------
# Palette compliance
# ---------------------------------------------------------------------------


class TestChromePaletteCompliance:
    """Every opaque pixel in the rendered journal maps to a palette role.

    The text tolerance is tight (4.0) — the surface uses no-AA fonts, so
    no intermediate channel blends should appear.
    """

    def test_empty_journal_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        surf = JournalSurface(tabs=_tabs("campaign", "archive"))
        out = _render(surf)
        assert_role_compliance(out, tolerance=4.0)

    def test_populated_journal_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        surf = JournalSurface(tabs=_tabs("a", "b"))
        surf.set_entries(
            [
                JournalEntryView(
                    entry_id="e1",
                    title="First Entry",
                    body="Some descriptive body text that should wrap across lines.",
                    category="a",
                    metadata={"Date": "Day 42"},
                ),
                _entry("e2", "b", title="Second Entry"),
            ]
        )
        surf.select_entry("e1")
        out = _render(surf)
        assert_role_compliance(out, tolerance=4.0)

    def test_custom_theme_is_role_compliant(self) -> None:
        from spacegame.engine.material_palette import assert_role_compliance

        theme = JournalTheme(
            accent_role="hud_accent_warm",
            border_role="weld",
            surface_bg_role="void_deep",
            panel_bg_role="void_mid",
        )
        surf = JournalSurface(tabs=_tabs("a"), theme=theme)
        surf.set_entries([_entry("e1", "a")])
        surf.select_entry("e1")
        out = _render(surf)
        assert_role_compliance(out, tolerance=4.0)
