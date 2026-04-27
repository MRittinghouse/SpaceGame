"""JournalSurface — shared journal UI primitive (spec §5.6).

Canonical four-region journal surface consumed by each Tier 2 system's
realization (Claim Ledger, Wrecker's Log, Fabricator's Register, Expedition
Log). Aesthetic differentiation lives in :class:`JournalTheme` — each system
picks different palette-role combinations without breaking palette discipline.

Layout::

    +---------------------------------------------+
    | [TAB1] [TAB2] [TAB3]                        |  Tab bar
    +----------------+----------------------------+
    | Entry 1        | SELECTED ENTRY TITLE       |
    | Entry 2  <sel> | ---                        |
    | Entry 3        | body text ...              |
    |                | metadata ...               |
    |                | see also: [cross-ref]      |
    +----------------+----------------------------+
    | 3 in section · 12 total                     |  Metadata strip
    +---------------------------------------------+

All color resolution routes through ``engine/material_palette.get_role`` so
the component stays palette-compliant and colorblind-remappable. The
surface never mutates its entry list — systems keep their own data models
and hand in :class:`JournalEntryView` snapshots for rendering.

See ``requirements/overhaul/42_ui_chrome_components.md §5.6``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pygame

from spacegame.engine.draw_utils import word_wrap
from spacegame.engine.fonts import FONT_HEADING, FONT_MD, FONT_SM, get_font
from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class JournalEntryView:
    """Presentation payload for one journal entry (UI-layer only).

    Systems keep their own persistence models and convert to this struct at
    render time. The surface treats entries as read-only.
    """

    entry_id: str
    title: str
    body: str
    category: str = ""
    metadata: dict[str, str] = field(default_factory=dict)
    cross_references: list[str] = field(default_factory=list)
    timestamp: int = 0


@dataclass
class JournalTab:
    """A top-level tab filtering the entry list by ``category``."""

    tab_id: str
    label: str


@dataclass
class JournalTheme:
    """Aesthetic overrides. Every field names a ``PALETTE_ROLES`` entry.

    Realizations pick role combinations that express their mood without
    breaking palette discipline. Example realizations (per spec §5.6):
      - **Claim Ledger** — ``accent_role='hud_accent_warm'`` for the field
        journal mood
      - **Wrecker's Log** — dim contrast; ``border_role='weld'``
      - **Fabricator's Register** — ``accent_role='hud_cyan'`` for the
        clinical workshop mood
      - **Expedition Log** — neutral field-book defaults
    """

    surface_bg_role: str = "void_mid"
    panel_bg_role: str = "void_deep"
    border_role: str = "rivet"
    accent_role: str = "hud_cyan"
    text_role: str = "hud_text"
    text_dim_role: str = "hud_text_dim"
    divider_role: str = "seam"
    empty_state_role: str = "hud_muted"
    selected_bg_role: str = "void_light"


@dataclass(frozen=True)
class JournalEvent:
    """Returned by :meth:`JournalSurface.handle_click` on an interactive hit.

    ``kind`` is one of:
      - ``"tab_changed"`` — payload is the new ``tab_id``
      - ``"entry_selected"`` — payload is the selected ``entry_id``
      - ``"cross_reference_clicked"`` — payload is the target ``entry_id``
    """

    kind: str
    payload: str


# ---------------------------------------------------------------------------
# Layout constants (pixels at 1080p-equivalent scale)
# ---------------------------------------------------------------------------

_TAB_BAR_HEIGHT = 36
_METADATA_STRIP_HEIGHT = 22
_ENTRY_ROW_HEIGHT = 22
_ENTRY_LIST_RATIO = 0.30
_PADDING = 8
_TAB_PADDING_X = 12


# ---------------------------------------------------------------------------
# Surface
# ---------------------------------------------------------------------------


class JournalSurface:
    """Shared journal UI primitive (spec §5.6).

    Instantiated once per system with a fixed tab set + theme, then fed
    :class:`JournalEntryView` lists as the system's entries change.
    """

    def __init__(
        self,
        tabs: list[JournalTab],
        theme: Optional[JournalTheme] = None,
    ) -> None:
        if not tabs:
            raise ValueError("JournalSurface requires at least one tab")
        self._tabs: list[JournalTab] = list(tabs)
        self._theme: JournalTheme = theme or JournalTheme()
        self._entries: list[JournalEntryView] = []
        self._selected_tab_id: str = self._tabs[0].tab_id
        self._selected_entry_id: Optional[str] = None
        self._scroll_offset: int = 0
        self._hit_regions: list[tuple[pygame.Rect, JournalEvent]] = []

    # ---- state accessors ---------------------------------------------------

    @property
    def tabs(self) -> tuple[JournalTab, ...]:
        return tuple(self._tabs)

    @property
    def theme(self) -> JournalTheme:
        return self._theme

    @property
    def entries(self) -> tuple[JournalEntryView, ...]:
        return tuple(self._entries)

    @property
    def selected_tab_id(self) -> str:
        return self._selected_tab_id

    @property
    def selected_entry_id(self) -> Optional[str]:
        return self._selected_entry_id

    @property
    def scroll_offset(self) -> int:
        return self._scroll_offset

    # ---- mutation ----------------------------------------------------------

    def set_entries(self, entries: list[JournalEntryView]) -> None:
        """Replace the entry list. Selection is cleared if the selected
        entry no longer exists."""
        self._entries = list(entries)
        if self._selected_entry_id and not any(
            e.entry_id == self._selected_entry_id for e in self._entries
        ):
            self._selected_entry_id = None

    def set_theme(self, theme: JournalTheme) -> None:
        self._theme = theme

    def select_tab(self, tab_id: str) -> bool:
        """Return True if the tab selection changed."""
        if not any(t.tab_id == tab_id for t in self._tabs):
            return False
        if self._selected_tab_id == tab_id:
            return False
        self._selected_tab_id = tab_id
        self._scroll_offset = 0
        # Clear entry selection if it falls outside the new tab.
        if self._selected_entry_id:
            selected = self._get_entry(self._selected_entry_id)
            if selected and selected.category != tab_id:
                self._selected_entry_id = None
        return True

    def select_entry(self, entry_id: str) -> bool:
        """Return True if the entry selection changed."""
        entry = self._get_entry(entry_id)
        if entry is None:
            return False
        if self._selected_entry_id == entry_id:
            return False
        self._selected_entry_id = entry_id
        # Selecting an entry in another tab also switches the tab.
        if entry.category and entry.category != self._selected_tab_id:
            if any(t.tab_id == entry.category for t in self._tabs):
                self._selected_tab_id = entry.category
                self._scroll_offset = 0
        return True

    def scroll(self, delta: int) -> None:
        """Scroll the entry list by ``delta`` pixels (positive scrolls down).

        Upper bound is clamped during the next :meth:`render` call — the
        surface needs the current rect height before it can compute the
        real maximum.
        """
        self._scroll_offset = max(0, self._scroll_offset + delta)

    # ---- interaction -------------------------------------------------------

    def handle_click(self, pos: tuple[int, int]) -> Optional[JournalEvent]:
        """Return the :class:`JournalEvent` emitted by a click at ``pos``.

        Applies the resulting state change (tab switch / entry select /
        cross-reference jump) before returning. Returns ``None`` if the
        position hit nothing or the click did not change state.
        """
        x, y = pos
        for region_rect, event in self._hit_regions:
            if not region_rect.collidepoint(x, y):
                continue
            if event.kind == "tab_changed":
                if self.select_tab(event.payload):
                    return event
                return None
            if event.kind == "entry_selected":
                if self.select_entry(event.payload):
                    return event
                return None
            if event.kind == "cross_reference_clicked":
                if self.select_entry(event.payload):
                    return event
                return None
            return None
        return None

    # ---- rendering ---------------------------------------------------------

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Paint the journal into ``rect`` on ``surface``."""
        theme = self._theme
        self._hit_regions.clear()

        tab_rect = pygame.Rect(rect.left, rect.top, rect.width, _TAB_BAR_HEIGHT)
        metadata_rect = pygame.Rect(
            rect.left,
            rect.bottom - _METADATA_STRIP_HEIGHT,
            rect.width,
            _METADATA_STRIP_HEIGHT,
        )
        content_rect = pygame.Rect(
            rect.left,
            tab_rect.bottom,
            rect.width,
            rect.height - _TAB_BAR_HEIGHT - _METADATA_STRIP_HEIGHT,
        )
        list_w = int(content_rect.width * _ENTRY_LIST_RATIO)
        entry_list_rect = pygame.Rect(
            content_rect.left, content_rect.top, list_w, content_rect.height
        )
        entry_detail_rect = pygame.Rect(
            content_rect.left + list_w,
            content_rect.top,
            content_rect.width - list_w,
            content_rect.height,
        )

        pygame.draw.rect(surface, get_role(theme.surface_bg_role), rect)
        self._render_tab_bar(surface, tab_rect)
        self._render_entry_list(surface, entry_list_rect)
        self._render_entry_detail(surface, entry_detail_rect)
        self._render_metadata_strip(surface, metadata_rect)
        pygame.draw.rect(surface, get_role(theme.border_role), rect, width=1)

    # ---- internals ---------------------------------------------------------

    def _entries_for_current_tab(self) -> list[JournalEntryView]:
        return [e for e in self._entries if e.category == self._selected_tab_id]

    def _get_entry(self, entry_id: str) -> Optional[JournalEntryView]:
        return next((e for e in self._entries if e.entry_id == entry_id), None)

    def _render_tab_bar(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self._theme
        pygame.draw.rect(surface, get_role(theme.panel_bg_role), rect)
        font = get_font("label", FONT_MD)
        x = rect.left + _PADDING
        for tab in self._tabs:
            selected = tab.tab_id == self._selected_tab_id
            text_color = get_role(theme.accent_role if selected else theme.text_dim_role)
            label_surf = font.render(tab.label, False, text_color)
            tab_width = label_surf.get_width() + _TAB_PADDING_X * 2
            tab_rect = pygame.Rect(x, rect.top, tab_width, rect.height)
            if selected:
                pygame.draw.rect(
                    surface,
                    get_role(theme.selected_bg_role),
                    tab_rect.inflate(-4, -4),
                )
                pygame.draw.rect(
                    surface,
                    get_role(theme.accent_role),
                    pygame.Rect(tab_rect.left + 4, tab_rect.bottom - 2, tab_rect.width - 8, 2),
                )
            text_y = tab_rect.top + (tab_rect.height - label_surf.get_height()) // 2
            surface.blit(label_surf, (tab_rect.left + _TAB_PADDING_X, text_y))
            self._hit_regions.append((tab_rect, JournalEvent("tab_changed", tab.tab_id)))
            x += tab_width
        # Tab bar bottom divider
        pygame.draw.rect(
            surface,
            get_role(theme.divider_role),
            pygame.Rect(rect.left, rect.bottom - 1, rect.width, 1),
        )

    def _render_entry_list(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self._theme
        pygame.draw.rect(surface, get_role(theme.panel_bg_role), rect)
        pygame.draw.rect(
            surface,
            get_role(theme.divider_role),
            pygame.Rect(rect.right - 1, rect.top, 1, rect.height),
        )
        entries = self._entries_for_current_tab()
        if not entries:
            self._render_empty_state(surface, rect, "No entries.")
            return

        # Clamp scroll against the newly-known panel height.
        content_h = len(entries) * _ENTRY_ROW_HEIGHT
        max_scroll = max(0, content_h - rect.height + _PADDING)
        self._scroll_offset = min(self._scroll_offset, max_scroll)

        font = get_font("label", FONT_SM)
        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        y = rect.top + _PADDING - self._scroll_offset
        for entry in entries:
            row_rect = pygame.Rect(rect.left, y, rect.width, _ENTRY_ROW_HEIGHT)
            if row_rect.bottom < rect.top or row_rect.top > rect.bottom:
                y += _ENTRY_ROW_HEIGHT
                continue
            selected = entry.entry_id == self._selected_entry_id
            if selected:
                pygame.draw.rect(surface, get_role(theme.selected_bg_role), row_rect)
                pygame.draw.rect(
                    surface,
                    get_role(theme.accent_role),
                    pygame.Rect(row_rect.left, row_rect.top, 2, row_rect.height),
                )
            title_color = get_role(theme.accent_role if selected else theme.text_role)
            text_surf = font.render(entry.title, False, title_color)
            text_y = row_rect.top + (row_rect.height - text_surf.get_height()) // 2
            surface.blit(text_surf, (row_rect.left + _PADDING, text_y))
            self._hit_regions.append((row_rect, JournalEvent("entry_selected", entry.entry_id)))
            y += _ENTRY_ROW_HEIGHT
        surface.set_clip(prev_clip)

    def _render_entry_detail(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self._theme
        pygame.draw.rect(surface, get_role(theme.panel_bg_role), rect)

        entries = self._entries_for_current_tab()
        if self._selected_entry_id is None:
            msg = "Select an entry." if entries else "No entries yet."
            self._render_empty_state(surface, rect, msg)
            return
        entry = self._get_entry(self._selected_entry_id)
        if entry is None:
            return

        inner = rect.inflate(-_PADDING * 2, -_PADDING * 2)
        heading_font = get_font("label", FONT_HEADING)
        body_font = get_font("dialogue", FONT_MD)
        meta_font = get_font("label", FONT_SM)

        prev_clip = surface.get_clip()
        surface.set_clip(rect)
        y = inner.top

        title_surf = heading_font.render(entry.title, False, get_role(theme.accent_role))
        surface.blit(title_surf, (inner.left, y))
        y += title_surf.get_height() + 6

        pygame.draw.rect(
            surface,
            get_role(theme.divider_role),
            pygame.Rect(inner.left, y, inner.width, 1),
        )
        y += 8

        body_color = get_role(theme.text_role)
        for line in word_wrap(entry.body, body_font, inner.width):
            line_surf = body_font.render(line, False, body_color)
            surface.blit(line_surf, (inner.left, y))
            y += line_surf.get_height() + 2

        y += 10

        if entry.metadata:
            for key, value in entry.metadata.items():
                meta_surf = meta_font.render(
                    f"{key}: {value}", False, get_role(theme.text_dim_role)
                )
                surface.blit(meta_surf, (inner.left, y))
                y += meta_surf.get_height() + 2
            y += 8

        if entry.cross_references:
            see_label = meta_font.render("See also:", False, get_role(theme.text_dim_role))
            surface.blit(see_label, (inner.left, y))
            y += see_label.get_height() + 4
            for ref_id in entry.cross_references:
                ref_entry = self._get_entry(ref_id)
                ref_label = ref_entry.title if ref_entry else ref_id
                ref_surf = meta_font.render(ref_label, False, get_role(theme.accent_role))
                ref_rect = pygame.Rect(inner.left, y, ref_surf.get_width(), ref_surf.get_height())
                surface.blit(ref_surf, (inner.left, y))
                self._hit_regions.append(
                    (ref_rect, JournalEvent("cross_reference_clicked", ref_id))
                )
                y += ref_surf.get_height() + 2

        surface.set_clip(prev_clip)

    def _render_metadata_strip(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        theme = self._theme
        pygame.draw.rect(surface, get_role(theme.panel_bg_role), rect)
        pygame.draw.rect(
            surface,
            get_role(theme.divider_role),
            pygame.Rect(rect.left, rect.top, rect.width, 1),
        )
        total = len(self._entries)
        tab_count = len(self._entries_for_current_tab())
        text = f"{tab_count} in this section · {total} total"
        font = get_font("label", FONT_SM)
        text_surf = font.render(text, False, get_role(theme.text_dim_role))
        text_y = rect.top + (rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (rect.left + _PADDING, text_y))

    def _render_empty_state(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        message: str,
    ) -> None:
        font = get_font("label", FONT_SM)
        text_surf = font.render(message, False, get_role(self._theme.empty_state_role))
        x = rect.left + (rect.width - text_surf.get_width()) // 2
        y = rect.top + (rect.height - text_surf.get_height()) // 2
        surface.blit(text_surf, (x, y))
