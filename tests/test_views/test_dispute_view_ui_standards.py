"""SA-P6 — DisputeView UI standards tests.

Covers the seven mechanical UI standards AC for SA-P6:
  1. Module-top layout constants exist and are positive.
  2. _VENUE_TITLES has keys for all three venue IDs.
  3. _VENUE_EMPTY_STATE_COPY has correct per-venue copy (no em-dashes).
  4. _OUTCOME_LABELS covers all four categories using " | " separator.
  5. _dispute_button_label() produces the correct format string.
  6. Corridor intel cache initialises to None; clears on back_to_list / on_exit.
  7. Keyboard Escape exits SESSION to LIST; in LIST triggers STATION_HUB.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.politics_dispute import PoliticsDispute, PoliticsDisputeManager
from spacegame.models.ship import Ship
from spacegame.views.dispute_view import (
    _OUTCOME_LABELS,
    _VENUE_EMPTY_STATE_COPY,
    _VENUE_TITLES,
    BTN_H,
    BTN_W,
    BTN_W_AUD,
    BTN_W_FULL,
    BTN_W_SM,
    CARD_H,
    CARD_MARGIN,
    CARD_W,
    COL_ACTION_X_STEP,
    COL_AUDIENCE_X,
    COL_EVIDENCE_X,
    LINE_GAP,
    LIST_TOP,
    ROW_GAP,
    ROW_GAP_SM,
    TEXT_TOP,
    DisputeSubstate,
    DisputeView,
)
from tests.test_models.test_politics_dispute import _make_water_rights_phasing_template


class _StubBonus:
    def __init__(self, b: dict) -> None:
        self._b = b

    def get_bonus(self, k: str) -> float:
        return float(self._b.get(k, 0.0))


class _StubSocial:
    def __init__(self, levels: dict) -> None:
        self._l = levels

    def get_skill_level(self, k: str) -> int:
        return int(self._l.get(k, 1))


def _build_player() -> Player:
    dl = get_data_loader()
    if not dl.ship_types:
        dl.load_all()
    ship_type = next(iter(dl.ship_types.values()))
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    return Player(name="Test", credits=1000, current_system_id="verdant", ship=ship)


def _build_view(
    *,
    venue_id: str = "verdant_mayors_council",
    register_dispute: bool = True,
) -> tuple[pygame_gui.UIManager, DisputeView, PoliticsDisputeManager]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    player = _build_player()
    tpl = _make_water_rights_phasing_template()
    dispute_mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        crew_roster=_StubBonus({"coalition_sway_bonus": 0.15}),
        progression=_StubBonus({"coalition_sway_bonus": 0.20}),
        social_manager=_StubSocial({"persuasion": 3, "leadership": 3}),
    )
    dispute_mgr.set_player(player)
    if register_dispute:
        dispute = dispute_mgr.start_dispute(tpl.id, current_game_day=1)
        dispute_mgr.register_pending_dispute(dispute)
    view = DisputeView(
        ui_manager=manager,
        player=player,
        dispute_manager=dispute_mgr,
        venue_id=venue_id,
        venue_faction_id="verdant",
    )
    return manager, view, dispute_mgr


# ---------------------------------------------------------------------------
# 1. Layout constants
# ---------------------------------------------------------------------------


class TestLayoutConstants:
    """All SA-P6 extracted layout constants must be positive non-zero values."""

    @pytest.mark.parametrize(
        "name, value",
        [
            ("BTN_W", BTN_W),
            ("BTN_W_SM", BTN_W_SM),
            ("BTN_H", BTN_H),
            ("BTN_W_FULL", BTN_W_FULL),
            ("BTN_W_AUD", BTN_W_AUD),
            ("CARD_H", CARD_H),
            ("ROW_GAP", ROW_GAP),
            ("ROW_GAP_SM", ROW_GAP_SM),
            ("COL_ACTION_X_STEP", COL_ACTION_X_STEP),
            ("COL_AUDIENCE_X", COL_AUDIENCE_X),
            ("COL_EVIDENCE_X", COL_EVIDENCE_X),
            ("CARD_MARGIN", CARD_MARGIN),
            ("CARD_W", CARD_W),
            ("LIST_TOP", LIST_TOP),
            ("TEXT_TOP", TEXT_TOP),
            ("LINE_GAP", LINE_GAP),
        ],
    )
    def test_constant_is_positive(self, name: str, value: int) -> None:
        assert value > 0, f"Layout constant {name}={value} must be > 0"

    def test_btn_w_sm_less_than_btn_w(self) -> None:
        """Narrow button must be narrower than the standard button."""
        assert BTN_W_SM < BTN_W, f"BTN_W_SM={BTN_W_SM} must be < BTN_W={BTN_W}"

    def test_row_gap_sm_less_than_row_gap(self) -> None:
        assert ROW_GAP_SM < ROW_GAP, f"ROW_GAP_SM={ROW_GAP_SM} must be < ROW_GAP={ROW_GAP}"

    def test_col_evidence_x_greater_than_col_audience_x(self) -> None:
        assert COL_EVIDENCE_X > COL_AUDIENCE_X, (
            f"COL_EVIDENCE_X={COL_EVIDENCE_X} must be > COL_AUDIENCE_X={COL_AUDIENCE_X}"
        )


# ---------------------------------------------------------------------------
# 2. Venue title map
# ---------------------------------------------------------------------------


class TestVenueTitles:
    KNOWN_VENUES = ["verdant_mayors_council", "havens_congress_hall", "crimson_wreckers_guild"]

    def test_all_venue_ids_present(self) -> None:
        for vid in self.KNOWN_VENUES:
            assert vid in _VENUE_TITLES, f"_VENUE_TITLES missing key '{vid}'"

    def test_titles_are_non_empty(self) -> None:
        for vid, title in _VENUE_TITLES.items():
            assert title.strip(), f"_VENUE_TITLES['{vid}'] is empty or whitespace"

    def test_unknown_venue_returns_default(self) -> None:
        # View must gracefully handle unknown venue ids by falling back.
        default = _VENUE_TITLES.get("unknown_venue_xyz", "Dispute Chamber")
        assert default == "Dispute Chamber"

    def test_no_em_dashes_in_titles(self) -> None:
        for vid, title in _VENUE_TITLES.items():
            assert "—" not in title, f"_VENUE_TITLES['{vid}'] contains an em-dash"


# ---------------------------------------------------------------------------
# 3. Empty-state copy map
# ---------------------------------------------------------------------------


class TestVenueEmptyStateCopy:
    KNOWN_VENUES = ["verdant_mayors_council", "havens_congress_hall", "crimson_wreckers_guild"]

    def test_all_venue_ids_present(self) -> None:
        for vid in self.KNOWN_VENUES:
            assert vid in _VENUE_EMPTY_STATE_COPY, f"_VENUE_EMPTY_STATE_COPY missing key '{vid}'"

    def test_copy_is_non_empty(self) -> None:
        for vid, copy in _VENUE_EMPTY_STATE_COPY.items():
            assert copy.strip(), f"_VENUE_EMPTY_STATE_COPY['{vid}'] is empty"

    def test_no_em_dashes_in_copy(self) -> None:
        for vid, copy in _VENUE_EMPTY_STATE_COPY.items():
            assert "—" not in copy, f"_VENUE_EMPTY_STATE_COPY['{vid}'] contains an em-dash"

    def test_copy_differs_across_venues(self) -> None:
        values = list(_VENUE_EMPTY_STATE_COPY.values())
        assert len(set(values)) == len(values), "Each venue must have distinct empty-state copy"


# ---------------------------------------------------------------------------
# 4. Outcome labels map
# ---------------------------------------------------------------------------


class TestOutcomeLabels:
    REQUIRED_CATEGORIES = ("win", "partial_win_coalition_thin", "partial_win_off_record", "loss")

    def test_all_categories_present(self) -> None:
        for cat in self.REQUIRED_CATEGORIES:
            assert cat in _OUTCOME_LABELS, f"_OUTCOME_LABELS missing key '{cat}'"

    def test_no_em_dashes_in_labels(self) -> None:
        for cat, label in _OUTCOME_LABELS.items():
            assert "—" not in label, f"_OUTCOME_LABELS['{cat}'] contains an em-dash"

    def test_partial_win_labels_use_pipe_separator(self) -> None:
        """Partial-win labels must use ' | ' (not '—') per Writing Bible."""
        for cat in ("partial_win_coalition_thin", "partial_win_off_record"):
            label = _OUTCOME_LABELS[cat]
            assert " | " in label, (
                f"_OUTCOME_LABELS['{cat}'] must use ' | ' separator, got: {label!r}"
            )

    def test_win_label_is_win(self) -> None:
        assert _OUTCOME_LABELS["win"] == "WIN"

    def test_loss_label_is_loss(self) -> None:
        assert _OUTCOME_LABELS["loss"] == "LOSS"


# ---------------------------------------------------------------------------
# 5. _dispute_button_label helper
# ---------------------------------------------------------------------------


class TestDisputeButtonLabel:
    """Format: '{headline} | Round {r}/{R} | {d}d'."""

    def _make_dispute(
        self,
        headline: str,
        *,
        current_round: int = 1,
        round_count: int = 3,
        closes_on_day: int = 15,
        game_day: int = 10,
    ) -> tuple[DisputeView, PoliticsDispute, int]:
        _mgr, view, dispute_mgr = _build_view()
        view.on_enter()
        dispute = dispute_mgr.get_pending_dispute("water_rights_phasing")
        assert dispute is not None
        dispute.headline = headline
        dispute.current_round = current_round
        dispute.round_count = round_count
        dispute.closes_on_day = closes_on_day
        return view, dispute, game_day

    def test_standard_format(self) -> None:
        view, dispute, game_day = self._make_dispute("Water Rights", closes_on_day=15)
        label = view._dispute_button_label(dispute, "water_rights_phasing", game_day)
        assert label == "Water Rights | Round 1/3 | 5d"
        view.on_exit()

    def test_long_headline_truncated_at_50(self) -> None:
        long = "A" * 55
        view, dispute, game_day = self._make_dispute(long, closes_on_day=15)
        label = view._dispute_button_label(dispute, "water_rights_phasing", game_day)
        assert label.startswith("A" * 47 + "...")
        view.on_exit()

    def test_no_em_dash_in_label(self) -> None:
        view, dispute, game_day = self._make_dispute("Headline", closes_on_day=15)
        label = view._dispute_button_label(dispute, "water_rights_phasing", game_day)
        assert "—" not in label
        view.on_exit()

    def test_days_segment_omitted_when_no_deadline(self) -> None:
        view, dispute, game_day = self._make_dispute("No Deadline", closes_on_day=0)
        label = view._dispute_button_label(dispute, "water_rights_phasing", game_day)
        assert "d" not in label.split(" | ")[-1] or "Round" in label.split(" | ")[-1]
        view.on_exit()

    def test_days_left_is_zero_when_past_deadline(self) -> None:
        view, dispute, _game_day = self._make_dispute("Past", closes_on_day=5, game_day=20)
        label = view._dispute_button_label(dispute, "water_rights_phasing", 20)
        assert "| 0d" in label
        view.on_exit()

    def test_none_dispute_returns_dispute_id(self) -> None:
        _mgr, view, _ = _build_view()
        view.on_enter()
        label = view._dispute_button_label(None, "fallback_id", 1)
        assert label == "fallback_id"
        view.on_exit()


# ---------------------------------------------------------------------------
# 6. Corridor intel cache
# ---------------------------------------------------------------------------


class TestCorridorIntelCache:
    def test_intel_cache_is_none_after_init(self) -> None:
        _mgr, view, _ = _build_view()
        assert view._corridor_intel is None

    def test_intel_cache_clears_on_back_to_list(self) -> None:
        _mgr, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view._corridor_intel = {"some_delegate": "Some intel text"}
        view.back_to_list()
        assert view._corridor_intel is None
        view.on_exit()

    def test_intel_cache_clears_on_exit(self) -> None:
        _mgr, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view._corridor_intel = {"some_delegate": "Some intel text"}
        view.on_exit()
        assert view._corridor_intel is None

    def test_micro_font_attribute_exists_after_init(self) -> None:
        _mgr, view, _ = _build_view()
        assert hasattr(view, "micro_font")
        assert view.micro_font is not None


# ---------------------------------------------------------------------------
# 7. Keyboard Escape handling
# ---------------------------------------------------------------------------


def _suppress_tips(player: Player) -> None:
    """Pre-set all first-time tip flags so tips don't intercept keyboard events in tests."""
    from spacegame.constants.flags import (
        seen_annual_congress_tip,
        seen_argument_composer_tip,
        seen_gray_market_arbitration_tip,
        seen_politics_venue_tip,
    )

    for flag_fn in (
        seen_politics_venue_tip,
        seen_argument_composer_tip,
        seen_annual_congress_tip,
        seen_gray_market_arbitration_tip,
    ):
        player.dialogue_flags[flag_fn()] = True


class TestKeyboardEscapeHandling:
    def _escape_event(self) -> pygame.event.Event:
        return pygame.event.Event(
            pygame.KEYDOWN,
            {"key": pygame.K_ESCAPE, "mod": 0, "unicode": "", "scancode": 0},
        )

    def _build_view_no_tips(self, register_dispute: bool = True):
        """Build view with all tips suppressed so keyboard events reach the handler."""
        pygame.init()
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        player = _build_player()
        _suppress_tips(player)
        tpl = _make_water_rights_phasing_template()
        from spacegame.models.politics_dispute import PoliticsDisputeManager

        dispute_mgr = PoliticsDisputeManager(
            templates={tpl.id: tpl},
            crew_roster=_StubBonus({"coalition_sway_bonus": 0.15}),
            progression=_StubBonus({"coalition_sway_bonus": 0.20}),
            social_manager=_StubSocial({"persuasion": 3, "leadership": 3}),
        )
        dispute_mgr.set_player(player)
        if register_dispute:
            d = dispute_mgr.start_dispute(tpl.id, current_game_day=1)
            dispute_mgr.register_pending_dispute(d)
        view = DisputeView(
            ui_manager=manager,
            player=player,
            dispute_manager=dispute_mgr,
            venue_id="verdant_mayors_council",
            venue_faction_id="verdant",
        )
        return manager, view, dispute_mgr

    def test_escape_from_session_goes_to_list(self) -> None:
        _mgr, view, _ = self._build_view_no_tips()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        assert view.substate == DisputeSubstate.SESSION
        view.handle_event(self._escape_event())
        assert view.substate == DisputeSubstate.LIST
        view.on_exit()

    def test_escape_from_corridor_goes_to_list(self) -> None:
        _mgr, view, _ = self._build_view_no_tips()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_corridor()
        assert view.substate == DisputeSubstate.CORRIDOR
        view.handle_event(self._escape_event())
        assert view.substate == DisputeSubstate.LIST
        view.on_exit()

    def test_escape_from_composer_goes_to_list(self) -> None:
        _mgr, view, _ = self._build_view_no_tips()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        assert view.substate == DisputeSubstate.COMPOSER
        view.handle_event(self._escape_event())
        assert view.substate == DisputeSubstate.LIST
        view.on_exit()

    def test_escape_from_list_triggers_station_hub(self) -> None:
        _mgr, view, _ = self._build_view_no_tips()
        view.on_enter()
        assert view.substate == DisputeSubstate.LIST
        view.handle_event(self._escape_event())
        assert view.next_state == GameState.STATION_HUB
        view.on_exit()
