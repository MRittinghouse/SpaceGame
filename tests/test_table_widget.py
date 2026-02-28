"""
Tests for the TableWidget reusable table component.
"""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for TableWidget tests")

from spacegame.views.table_widget import ColumnDef, TableWidget  # noqa: E402


@pytest.fixture(autouse=True)
def _init_pygame():
    """Ensure pygame is initialized for font rendering."""
    pygame.init()
    yield
    pygame.quit()


# === ColumnDef Tests ===


def test_column_def_defaults() -> None:
    """ColumnDef defaults align to 'left'."""
    col = ColumnDef("Name", 100)
    assert col.header == "Name"
    assert col.width == 100
    assert col.align == "left"


def test_column_def_custom_align() -> None:
    """ColumnDef accepts custom alignment."""
    col = ColumnDef("Price", 80, "right")
    assert col.align == "right"


# === TableWidget Construction ===


def _make_table(**kwargs) -> TableWidget:
    """Helper to create a table with sensible defaults."""
    defaults = {
        "rect": pygame.Rect(0, 0, 400, 300),
        "columns": [
            ColumnDef("A", 200, "left"),
            ColumnDef("B", 200, "right"),
        ],
    }
    defaults.update(kwargs)
    return TableWidget(**defaults)


def test_table_initial_state() -> None:
    """New table has no data and no selection."""
    table = _make_table()
    assert table.get_selected_index() is None
    assert table._rows == []


def test_table_set_data() -> None:
    """set_data stores rows for rendering."""
    table = _make_table()
    rows = [["Hello", "World"], ["Foo", "Bar"]]
    table.set_data(rows)
    assert len(table._rows) == 2


def test_table_set_data_clears_selection_when_out_of_range() -> None:
    """Selection is cleared if it exceeds the new data length."""
    table = _make_table()
    table.set_data([["a", "b"], ["c", "d"]])
    table.set_selected_index(1)
    assert table.get_selected_index() == 1

    # Shrink data — selection index 1 is now out of range
    table.set_data([["x", "y"]])
    assert table.get_selected_index() is None


def test_table_set_data_preserves_valid_selection() -> None:
    """Selection is preserved when new data still has that index."""
    table = _make_table()
    table.set_data([["a", "b"], ["c", "d"], ["e", "f"]])
    table.set_selected_index(1)
    table.set_data([["x", "y"], ["z", "w"]])
    assert table.get_selected_index() == 1


# === Selection ===


def test_set_selected_index() -> None:
    """Programmatic selection works within bounds."""
    table = _make_table()
    table.set_data([["a", "b"], ["c", "d"]])
    table.set_selected_index(0)
    assert table.get_selected_index() == 0
    table.set_selected_index(1)
    assert table.get_selected_index() == 1


def test_set_selected_index_out_of_range() -> None:
    """Out-of-range index is ignored (set to None)."""
    table = _make_table()
    table.set_data([["a", "b"]])
    table.set_selected_index(5)
    assert table.get_selected_index() is None


def test_set_selected_index_none() -> None:
    """Passing None clears the selection."""
    table = _make_table()
    table.set_data([["a", "b"]])
    table.set_selected_index(0)
    table.set_selected_index(None)
    assert table.get_selected_index() is None


# === Click Selection ===


def test_click_selects_row() -> None:
    """Clicking inside the content area selects the appropriate row."""
    table = _make_table(rect=pygame.Rect(0, 0, 400, 300), row_height=26)
    table.set_data([["a", "b"], ["c", "d"], ["e", "f"]])

    # The header takes _header_height pixels. Click inside row 0.
    header_h = table._header_height
    click_y = header_h + 5  # inside first row
    consumed = table._handle_click((10, click_y))
    assert consumed is True
    assert table.get_selected_index() == 0


def test_click_second_row() -> None:
    """Clicking below the first row selects the second row."""
    table = _make_table(rect=pygame.Rect(0, 0, 400, 300), row_height=26)
    table.set_data([["a", "b"], ["c", "d"], ["e", "f"]])

    header_h = table._header_height
    click_y = header_h + 26 + 5  # inside second row
    consumed = table._handle_click((10, click_y))
    assert consumed is True
    assert table.get_selected_index() == 1


def test_click_outside_returns_false() -> None:
    """Click outside the content area does not select."""
    table = _make_table(rect=pygame.Rect(100, 100, 400, 300))
    table.set_data([["a", "b"]])

    consumed = table._handle_click((50, 50))  # outside rect
    assert consumed is False
    assert table.get_selected_index() is None


# === Scroll ===


def test_scroll_clamps_to_zero() -> None:
    """Scroll offset cannot go below zero."""
    table = _make_table()
    table.set_data([["a", "b"]])
    table._scroll_offset = -100
    table._clamp_scroll()
    assert table._scroll_offset == 0


def test_scroll_clamps_to_max() -> None:
    """Scroll offset is clamped to the maximum overflow."""
    table = _make_table(rect=pygame.Rect(0, 0, 400, 100), row_height=26)
    # 10 rows × 26px = 260px total, content area ~72px → overflow ~188px
    rows = [[str(i), str(i)] for i in range(10)]
    table.set_data(rows)

    table._scroll_offset = 9999
    table._clamp_scroll()
    assert table._scroll_offset == table._max_scroll()
    assert table._scroll_offset > 0


def test_no_scroll_when_content_fits() -> None:
    """When all rows fit, max_scroll is 0."""
    table = _make_table(rect=pygame.Rect(0, 0, 400, 500), row_height=26)
    table.set_data([["a", "b"], ["c", "d"]])
    assert table._max_scroll() == 0


# === Hover ===


def test_hover_updates_on_motion() -> None:
    """Mouse motion updates the hovered index."""
    table = _make_table(rect=pygame.Rect(0, 0, 400, 300), row_height=26)
    table.set_data([["a", "b"], ["c", "d"]])

    header_h = table._header_height
    consumed = table._handle_motion((10, header_h + 5))
    assert consumed is True
    assert table._hovered_index == 0


def test_hover_none_outside() -> None:
    """Moving outside the content area clears hover."""
    table = _make_table(rect=pygame.Rect(100, 100, 400, 300))
    table.set_data([["a", "b"]])
    table._hovered_index = 0

    consumed = table._handle_motion((50, 50))
    assert consumed is True
    assert table._hovered_index is None


# === Per-cell Color ===


def test_cell_color_tuple() -> None:
    """Rows can mix plain strings and (text, color) tuples."""
    table = _make_table()
    rows = [["Normal", ("Colored", (255, 0, 0))]]
    table.set_data(rows)
    assert table._rows[0][0] == "Normal"
    assert table._rows[0][1] == ("Colored", (255, 0, 0))


# === Empty Message ===


def test_empty_message_stored() -> None:
    """Empty message is stored and available for rendering."""
    table = _make_table(empty_message="No data")
    assert table.empty_message == "No data"


# === Render Smoke Test ===


def test_render_no_crash_empty() -> None:
    """Rendering an empty table does not crash."""
    screen = pygame.Surface((800, 600))
    table = _make_table(empty_message="Nothing here")
    table.render(screen)


def test_render_no_crash_with_data() -> None:
    """Rendering a table with data does not crash."""
    screen = pygame.Surface((800, 600))
    table = _make_table()
    table.set_data([["Hello", "World"], ["Foo", ("Bar", (255, 0, 0))]])
    table.set_selected_index(0)
    table._hovered_index = 1
    table.render(screen)


def test_render_no_crash_scrolled() -> None:
    """Rendering a scrolled table with many rows does not crash."""
    screen = pygame.Surface((800, 600))
    table = _make_table(rect=pygame.Rect(0, 0, 400, 100), row_height=26)
    rows = [[str(i), str(i)] for i in range(20)]
    table.set_data(rows)
    table._scroll_offset = 100
    table._clamp_scroll()
    table.render(screen)
