"""Tests for the journal view — filter tabs, entry display, CRUD, scrolling."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for JournalView tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required for JournalView tests")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT, GameState
from spacegame.models.journal import Journal, JournalEntry
from spacegame.views.journal_view import JournalView


# ============================================================================
# PYGAME INIT
# ============================================================================


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


# ============================================================================
# HELPERS
# ============================================================================


def _make_auto_templates() -> list[JournalEntry]:
    return [
        JournalEntry(
            entry_id="auto_m01",
            text="Acquired bill of landing.",
            game_day=0,
            system_id="nexus_prime",
            source="auto",
            trigger_flag="talked_to_officer_larsen",
            mission_id="m01",
        ),
        JournalEntry(
            entry_id="auto_m02",
            text="Delivered iron ore.",
            game_day=0,
            system_id="forgeworks",
            source="auto",
            trigger_flag="iron_ore_delivered",
            mission_id="m02",
        ),
    ]


def _make_journal_with_entries() -> Journal:
    """Create a journal with some auto and player entries."""
    journal = Journal(auto_templates=_make_auto_templates())
    journal.trigger_auto_entry("talked_to_officer_larsen", game_day=1, system_id="nexus_prime")
    journal.trigger_auto_entry("iron_ore_delivered", game_day=3, system_id="forgeworks")
    journal.add_player_entry(
        "Elena seems trustworthy.", game_day=2, system_id="nexus_prime", tag="people"
    )
    journal.add_player_entry(
        "Breakstone is rough.", game_day=4, system_id="breakstone", tag="places"
    )
    journal.add_player_entry(
        "Who runs the pirates?", game_day=5, system_id="nexus_prime", tag="suspicions"
    )
    return journal


def _make_view(
    journal: Journal | None = None,
    game_day: int = 5,
    system_id: str = "nexus_prime",
) -> JournalView:
    ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    j = journal or _make_journal_with_entries()
    return JournalView(ui_manager, j, game_day, system_id)


# ============================================================================
# CONSTRUCTION
# ============================================================================


class TestJournalViewConstruction:
    """Tests for JournalView initialization."""

    def test_construction(self) -> None:
        view = _make_view()
        assert view.journal is not None
        assert view.get_next_state() is None

    def test_initial_filter_is_all(self) -> None:
        view = _make_view()
        assert view._current_filter == "all"

    def test_construction_with_empty_journal(self) -> None:
        journal = Journal()
        view = _make_view(journal=journal)
        assert view.journal.get_entry_count() == 0


# ============================================================================
# FILTER TABS
# ============================================================================


class TestFilterSwitching:
    """Tests for tag filter tab behavior."""

    def test_all_filter_shows_all_entries(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view._current_filter == "all"
        # All 5 entries visible
        assert len(view._entry_items) == 5
        view.on_exit()

    def test_people_filter_shows_tagged_entries(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("people")
        # Only the "people" tagged player entry
        assert len(view._entry_items) == 1
        assert view._entry_items[0].entry.tag == "people"
        view.on_exit()

    def test_places_filter(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("places")
        assert len(view._entry_items) == 1
        assert view._entry_items[0].entry.tag == "places"
        view.on_exit()

    def test_suspicions_filter(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("suspicions")
        assert len(view._entry_items) == 1
        assert view._entry_items[0].entry.tag == "suspicions"
        view.on_exit()

    def test_goals_filter_empty(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("goals")
        assert len(view._entry_items) == 0
        view.on_exit()

    def test_switching_back_to_all(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("people")
        assert len(view._entry_items) == 1
        view._switch_filter("all")
        assert len(view._entry_items) == 5
        view.on_exit()


# ============================================================================
# ENTRY SELECTION
# ============================================================================


class TestEntrySelection:
    """Tests for selecting entries in the list."""

    def test_first_entry_selected_by_default(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view._selected_entry_id is not None
        view.on_exit()

    def test_select_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        entries = view.journal.get_entries()
        if len(entries) > 1:
            view._select_entry(entries[1].entry_id)
            assert view._selected_entry_id == entries[1].entry_id
        view.on_exit()

    def test_selection_cleared_on_filter_change(self) -> None:
        view = _make_view()
        view.on_enter()
        view._switch_filter("people")
        # Should auto-select first in filtered list
        if view._entry_items:
            assert view._selected_entry_id == view._entry_items[0].entry.entry_id
        view.on_exit()


# ============================================================================
# PLAYER ENTRY CRUD
# ============================================================================


class TestNewEntry:
    """Tests for creating new player entries."""

    def test_enter_compose_mode(self) -> None:
        view = _make_view()
        view.on_enter()
        view._start_compose()
        assert view._composing is True
        view.on_exit()

    def test_confirm_new_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        initial_count = view.journal.get_entry_count()
        view._start_compose()
        view._text_entry.set_text("Test note from player")
        view._compose_tag = "goals"
        view._confirm_compose()
        assert view.journal.get_entry_count() == initial_count + 1
        assert view._composing is False
        view.on_exit()

    def test_cancel_compose(self) -> None:
        view = _make_view()
        view.on_enter()
        initial_count = view.journal.get_entry_count()
        view._start_compose()
        view._text_entry.set_text("This will be discarded")
        view._cancel_compose()
        assert view.journal.get_entry_count() == initial_count
        assert view._composing is False
        view.on_exit()

    def test_new_entry_appears_in_list(self) -> None:
        view = _make_view()
        view.on_enter()
        view._start_compose()
        view._text_entry.set_text("A new observation")
        view._compose_tag = ""
        view._confirm_compose()
        # Check entry was added and list refreshed
        found = False
        for item in view._entry_items:
            if item.entry.text == "A new observation":
                found = True
                break
        assert found, "New entry should appear in list after confirm"
        view.on_exit()


class TestEditEntry:
    """Tests for editing player entries."""

    def test_start_edit_player_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        # Find a player entry
        player_entries = view.journal.get_entries(source_filter="player")
        assert len(player_entries) > 0
        entry = player_entries[0]
        view._select_entry(entry.entry_id)
        view._start_edit()
        assert view._editing is True
        assert view._compose_text == entry.text
        view.on_exit()

    def test_confirm_edit(self) -> None:
        view = _make_view()
        view.on_enter()
        player_entries = view.journal.get_entries(source_filter="player")
        entry = player_entries[0]
        view._select_entry(entry.entry_id)
        view._start_edit()
        view._text_entry.set_text("Updated text")
        view._compose_tag = "goals"
        view._confirm_compose()
        # Verify edit applied
        updated = view.journal._find_entry(entry.entry_id)
        assert updated.text == "Updated text"
        assert updated.tag == "goals"
        assert view._editing is False
        view.on_exit()

    def test_cannot_edit_auto_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        auto_entries = view.journal.get_entries(source_filter="auto")
        assert len(auto_entries) > 0
        view._select_entry(auto_entries[0].entry_id)
        view._start_edit()
        # Should not enter editing mode for auto entries
        assert view._editing is False
        view.on_exit()


class TestDeleteEntry:
    """Tests for deleting player entries."""

    def test_delete_player_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        player_entries = view.journal.get_entries(source_filter="player")
        initial_count = view.journal.get_entry_count()
        entry = player_entries[0]
        view._select_entry(entry.entry_id)
        view._delete_selected()
        assert view.journal.get_entry_count() == initial_count - 1
        view.on_exit()

    def test_cannot_delete_auto_entry(self) -> None:
        view = _make_view()
        view.on_enter()
        auto_entries = view.journal.get_entries(source_filter="auto")
        initial_count = view.journal.get_entry_count()
        view._select_entry(auto_entries[0].entry_id)
        view._delete_selected()
        assert view.journal.get_entry_count() == initial_count
        view.on_exit()


# ============================================================================
# NAVIGATION
# ============================================================================


class TestNavigation:
    """Tests for back navigation."""

    def test_back_sets_galaxy_map(self) -> None:
        view = _make_view()
        view.on_enter()
        assert view.get_next_state() is None
        # Simulate back button press
        view.next_state = GameState.GALAXY_MAP
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_escape_key_when_composing_cancels(self) -> None:
        view = _make_view()
        view.on_enter()
        view._start_compose()
        assert view._composing is True
        # Simulate escape key
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)
        assert view._composing is False
        assert view.get_next_state() is None  # Should not navigate away
        view.on_exit()

    def test_escape_key_when_not_composing_exits(self) -> None:
        view = _make_view()
        view.on_enter()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        view.handle_event(event)
        assert view.get_next_state() == GameState.GALAXY_MAP
        view.on_exit()

    def test_n_key_starts_compose(self) -> None:
        view = _make_view()
        view.on_enter()
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
        view.handle_event(event)
        assert view._composing is True
        view.on_exit()
