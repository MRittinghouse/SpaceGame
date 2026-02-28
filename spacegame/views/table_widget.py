"""
Reusable fixed-column table widget for pixel-precise rendering.

Renders a table with configurable columns, text alignment, row selection,
hover highlighting, scrolling, and a scrollbar. Not a pygame_gui element —
draws directly to the screen surface.
"""

import pygame
from dataclasses import dataclass, field
from typing import Optional

from spacegame.config import Colors

# Horizontal padding inside each cell
CELL_PAD = 6


@dataclass
class ColumnDef:
    """Definition for a single table column.

    Args:
        header: Column header text.
        width: Pixel width of the column.
        align: Text alignment — "left", "right", or "center".
    """

    header: str
    width: int
    align: str = "left"


class TableWidget:
    """Fixed-column table with selection, hover, and scrolling.

    Args:
        rect: Bounding rectangle for the entire widget.
        columns: Column definitions controlling layout.
        row_height: Pixel height of each row.
        font: Font for data rows.
        header_font: Font for the header row.
        empty_message: Text shown when there are no data rows.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        columns: list[ColumnDef],
        row_height: int = 26,
        font: Optional[pygame.font.Font] = None,
        header_font: Optional[pygame.font.Font] = None,
        empty_message: str = "",
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.columns = columns
        self.row_height = row_height
        self.font = font or pygame.font.Font(None, 20)
        self.header_font = header_font or pygame.font.Font(None, 22)
        self.empty_message = empty_message

        # Row data: each row is list[str | tuple[str, tuple]] for per-cell color
        self._rows: list[list[str | tuple[str, tuple]]] = []
        self._selected_index: Optional[int] = None
        self._hovered_index: Optional[int] = None
        self._scroll_offset: int = 0

        # Computed layout values
        self._header_height = self.row_height + 2  # header + separator line
        self._content_rect = pygame.Rect(
            self.rect.x,
            self.rect.y + self._header_height,
            self.rect.width,
            self.rect.height - self._header_height,
        )

        # Colors
        self._bg_color = (15, 18, 35, 180)
        self._header_color = Colors.TEXT_HIGHLIGHT
        self._separator_color = Colors.UI_BORDER
        self._selected_color = (40, 60, 100, 180)
        self._hovered_color = (30, 40, 60, 120)
        self._alt_row_color = (20, 24, 42, 80)
        self._default_text_color = Colors.TEXT_PRIMARY

        # Scrollbar
        self._scrollbar_width = 6
        self._scrollbar_track_color = (30, 35, 55)
        self._scrollbar_thumb_color = (80, 90, 120)

    def set_data(self, rows: list[list[str | tuple[str, tuple]]]) -> None:
        """Replace all row data.

        Args:
            rows: List of rows. Each row is a list of cells where each cell
                  is either a plain string or a (string, color) tuple.
        """
        self._rows = rows
        # Clamp selection
        if self._selected_index is not None and self._selected_index >= len(rows):
            self._selected_index = None
        # Clamp scroll
        self._clamp_scroll()

    def get_selected_index(self) -> Optional[int]:
        """Return the currently selected row index, or None."""
        return self._selected_index

    def set_selected_index(self, index: Optional[int]) -> None:
        """Programmatically set the selected row index."""
        if index is not None and 0 <= index < len(self._rows):
            self._selected_index = index
        else:
            self._selected_index = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Process mouse events for selection, hover, and scrolling.

        Args:
            event: A pygame event.

        Returns:
            True if the event was consumed by this widget.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._handle_click(event.pos)
        if event.type == pygame.MOUSEWHEEL:
            if self._content_rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll_offset -= event.y * self.row_height
                self._clamp_scroll()
                return True
        if event.type == pygame.MOUSEMOTION:
            return self._handle_motion(event.pos)
        return False

    def render(self, screen: pygame.Surface) -> None:
        """Draw the complete table widget to the screen."""
        self._draw_background(screen)
        self._draw_header(screen)
        self._draw_rows(screen)
        self._draw_scrollbar(screen)
        self._draw_border(screen)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _visible_row_count(self) -> int:
        """Number of rows that fit in the content area."""
        return max(1, self._content_rect.height // self.row_height)

    def _total_content_height(self) -> int:
        """Total pixel height of all data rows."""
        return len(self._rows) * self.row_height

    def _max_scroll(self) -> int:
        """Maximum valid scroll offset."""
        overflow = self._total_content_height() - self._content_rect.height
        return max(0, overflow)

    def _clamp_scroll(self) -> None:
        """Ensure scroll offset is within valid bounds."""
        self._scroll_offset = max(0, min(self._scroll_offset, self._max_scroll()))

    def _row_index_at(self, pos: tuple[int, int]) -> Optional[int]:
        """Return the data-row index under *pos*, or None."""
        if not self._content_rect.collidepoint(pos):
            return None
        local_y = pos[1] - self._content_rect.y + self._scroll_offset
        idx = local_y // self.row_height
        if 0 <= idx < len(self._rows):
            return idx
        return None

    def _handle_click(self, pos: tuple[int, int]) -> bool:
        idx = self._row_index_at(pos)
        if idx is not None:
            self._selected_index = idx
            return True
        return False

    def _handle_motion(self, pos: tuple[int, int]) -> bool:
        idx = self._row_index_at(pos)
        if idx != self._hovered_index:
            self._hovered_index = idx
            return True
        return False

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_background(self, screen: pygame.Surface) -> None:
        bg = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        bg.fill(self._bg_color)
        screen.blit(bg, self.rect.topleft)

    def _draw_border(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, self._separator_color, self.rect, 1)

    def _draw_header(self, screen: pygame.Surface) -> None:
        x = self.rect.x
        y = self.rect.y
        for col in self.columns:
            text_surf = self.header_font.render(col.header, True, self._header_color)
            tx = self._align_x(text_surf, x, col.width, col.align)
            screen.blit(text_surf, (tx, y + 4))
            x += col.width
        # Separator line below header
        sep_y = self.rect.y + self._header_height - 1
        pygame.draw.line(
            screen,
            self._separator_color,
            (self.rect.x, sep_y),
            (self.rect.right, sep_y),
        )

    def _draw_rows(self, screen: pygame.Surface) -> None:
        if not self._rows:
            if self.empty_message:
                msg = self.font.render(self.empty_message, True, Colors.TEXT_SECONDARY)
                mx = self.rect.x + (self.rect.width - msg.get_width()) // 2
                my = self._content_rect.y + (self._content_rect.height - msg.get_height()) // 2
                screen.blit(msg, (mx, my))
            return

        # Clip to content area
        old_clip = screen.get_clip()
        screen.set_clip(self._content_rect)

        first_visible = self._scroll_offset // self.row_height
        last_visible = first_visible + self._visible_row_count() + 1
        last_visible = min(last_visible, len(self._rows))

        for i in range(first_visible, last_visible):
            row_y = self._content_rect.y + i * self.row_height - self._scroll_offset
            self._draw_row_bg(screen, i, row_y)
            self._draw_row_cells(screen, i, row_y)

        screen.set_clip(old_clip)

    def _draw_row_bg(self, screen: pygame.Surface, index: int, y: int) -> None:
        row_rect = pygame.Rect(self.rect.x, y, self.rect.width, self.row_height)
        if index == self._selected_index:
            bg = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            bg.fill(self._selected_color)
            screen.blit(bg, row_rect.topleft)
        elif index == self._hovered_index:
            bg = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            bg.fill(self._hovered_color)
            screen.blit(bg, row_rect.topleft)
        elif index % 2 == 1:
            bg = pygame.Surface((row_rect.width, row_rect.height), pygame.SRCALPHA)
            bg.fill(self._alt_row_color)
            screen.blit(bg, row_rect.topleft)

    def _draw_row_cells(self, screen: pygame.Surface, index: int, y: int) -> None:
        row = self._rows[index]
        x = self.rect.x
        for col_idx, col in enumerate(self.columns):
            if col_idx < len(row):
                cell = row[col_idx]
                if isinstance(cell, tuple):
                    text, color = cell
                else:
                    text = cell
                    color = self._default_text_color
            else:
                text = ""
                color = self._default_text_color

            text_surf = self.font.render(text, True, color)

            # Truncate with ellipsis if text is wider than column
            max_width = col.width - CELL_PAD * 2
            if text_surf.get_width() > max_width:
                text_surf = self._truncate_text(text, color, max_width)

            tx = self._align_x(text_surf, x, col.width, col.align)
            # Vertically center text in the row
            ty = y + (self.row_height - text_surf.get_height()) // 2
            screen.blit(text_surf, (tx, ty))
            x += col.width

    def _truncate_text(self, text: str, color: tuple, max_width: int) -> pygame.Surface:
        """Render text truncated with '...' to fit within max_width."""
        ellipsis = "..."
        ellipsis_w = self.font.size(ellipsis)[0]
        if max_width <= ellipsis_w:
            return self.font.render(ellipsis, True, color)
        target = max_width - ellipsis_w
        for end in range(len(text), 0, -1):
            if self.font.size(text[:end])[0] <= target:
                return self.font.render(text[:end] + ellipsis, True, color)
        return self.font.render(ellipsis, True, color)

    def _align_x(self, surf: pygame.Surface, col_x: int, col_width: int, align: str) -> int:
        """Compute x position for a text surface within a column."""
        if align == "right":
            return col_x + col_width - surf.get_width() - CELL_PAD
        elif align == "center":
            return col_x + (col_width - surf.get_width()) // 2
        else:  # left
            return col_x + CELL_PAD

    def _draw_scrollbar(self, screen: pygame.Surface) -> None:
        """Draw a thin scrollbar when content overflows."""
        if self._total_content_height() <= self._content_rect.height:
            return

        track_x = self.rect.right - self._scrollbar_width - 2
        track_y = self._content_rect.y + 2
        track_h = self._content_rect.height - 4

        # Track
        pygame.draw.rect(
            screen,
            self._scrollbar_track_color,
            (track_x, track_y, self._scrollbar_width, track_h),
        )

        # Thumb
        visible_ratio = self._content_rect.height / self._total_content_height()
        thumb_h = max(16, int(track_h * visible_ratio))
        max_scroll = self._max_scroll()
        if max_scroll > 0:
            scroll_ratio = self._scroll_offset / max_scroll
        else:
            scroll_ratio = 0.0
        thumb_y = track_y + int((track_h - thumb_h) * scroll_ratio)

        pygame.draw.rect(
            screen,
            self._scrollbar_thumb_color,
            (track_x, thumb_y, self._scrollbar_width, thumb_h),
            border_radius=3,
        )
