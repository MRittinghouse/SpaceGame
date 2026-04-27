"""SA-P2 — DisputeView tests (AC 10 + AC 11).

Covers substate transitions, empty / locked / loading / error renders,
and the live "Effective vs Difficulty" composer preview.
"""

from __future__ import annotations

import os

# Force pygame to use a dummy video driver so tests run headless.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from typing import Optional

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.politics_dispute import (
    PoliticsDisputeManager,
)
from spacegame.models.ship import Ship
from spacegame.views.dispute_view import (
    DisputeListState,
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


def _build_player(*, faction_id: str = "verdant", standing: int = 0) -> Player:
    dl = get_data_loader()
    if not dl.ship_types:
        dl.load_all()
    ship_type = next(iter(dl.ship_types.values()))
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Test",
        credits=1000,
        current_system_id="verdant",
        ship=ship,
    )
    player.faction_reputation[faction_id] = standing
    return player


def _build_view(
    player: Optional[Player] = None,
    *,
    register_dispute: bool = True,
) -> tuple[pygame_gui.UIManager, DisputeView, PoliticsDisputeManager]:
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    if player is None:
        player = _build_player()
    tpl = _make_water_rights_phasing_template()
    dispute_mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        crew_roster=_StubBonus({"coalition_sway_bonus": 0.15, "coalition_size_bonus": 1.0}),
        progression=_StubBonus({"coalition_sway_bonus": 0.20, "coalition_size_bonus": 1.0}),
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
        venue_id="verdant_mayors_council",
        venue_faction_id="verdant",
    )
    return manager, view, dispute_mgr


# ---------------------------------------------------------------------------
# Construction + lifecycle
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_construct_default(self) -> None:
        _manager, view, _ = _build_view()
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        assert view.active is True
        assert view.substate == DisputeSubstate.LIST
        view.on_exit()

    def test_on_exit_destroys_ui_and_resets_session(self) -> None:
        _manager, view, dispute_mgr = _build_view()
        view.on_enter()
        view.on_exit()
        assert view.back_button is None
        # End-of-session resets the intel reveal gate.
        assert dispute_mgr._intel_revealed_this_session is False


# ---------------------------------------------------------------------------
# LIST substate states (AC 10)
# ---------------------------------------------------------------------------


class TestListSubstateRenders:
    def test_list_state_ready_when_disputes_pending(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        assert view.list_state == DisputeListState.READY
        # A pending dispute generates one button.
        assert len(view._dispute_buttons) == 1
        view.on_exit()

    def test_list_state_empty_when_no_pending_disputes(self) -> None:
        _manager, view, _ = _build_view(register_dispute=False)
        view.on_enter()
        assert view.list_state == DisputeListState.EMPTY
        assert len(view._dispute_buttons) == 0
        view.on_exit()

    def test_list_state_locked_when_standing_below_threshold(self) -> None:
        player = _build_player(standing=-50)
        _manager, view, _ = _build_view(player)
        view.on_enter()
        assert view.list_state == DisputeListState.LOCKED
        assert len(view._dispute_buttons) == 0
        view.on_exit()

    def test_list_state_loading(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.set_loading(True)
        assert view.list_state == DisputeListState.LOADING
        view.on_exit()

    def test_list_state_error(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.set_error(True)
        assert view.list_state == DisputeListState.ERROR
        view.on_exit()


# ---------------------------------------------------------------------------
# Substate transitions
# ---------------------------------------------------------------------------


class TestSubstateTransitions:
    def test_open_dispute_switches_to_session(self) -> None:
        _manager, view, _dispute_mgr = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        assert view.substate == DisputeSubstate.SESSION
        assert view.active_dispute is not None
        view.on_exit()

    def test_open_corridor_switches_to_corridor(self) -> None:
        _manager, view, _dispute_mgr = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_corridor()
        assert view.substate == DisputeSubstate.CORRIDOR
        view.on_exit()

    def test_open_composer_clears_argument_state(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        assert view.substate == DisputeSubstate.COMPOSER
        assert view.composer_argument.framing == ""
        assert view.composer_argument.audience_delegate_id == ""
        view.on_exit()

    def test_back_to_list_clears_active_dispute(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.back_to_list()
        assert view.substate == DisputeSubstate.LIST
        assert view.active_dispute is None
        view.on_exit()

    def test_destroy_create_destroy_no_runtime_error(self) -> None:
        """Pygame_gui leak test: switching substates twice does not throw."""
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        view.back_to_list()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        view.back_to_list()
        view.on_exit()


# ---------------------------------------------------------------------------
# Composer live preview (AC 11)
# ---------------------------------------------------------------------------


class TestComposerLivePreview:
    def test_initial_preview_text_is_error_until_selections_made(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        text = view.preview_label.text  # type: ignore[union-attr]
        assert "framing" in text.lower() or "Argument incomplete" in text
        view.on_exit()

    def test_preview_updates_on_framing_change(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        view.update_composer_selection(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        # 3 + 1 + 0 + 0.15 + 0.20 = 4.35 -> floor 4 vs D4 -> PASSES
        text = view.preview_label.text  # type: ignore[union-attr]
        assert "Effective 4" in text
        assert "Difficulty 4" in text
        assert "PASSES" in text
        view.on_exit()

    def test_preview_updates_when_evidence_removed(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        view.update_composer_selection(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        # Now drop evidence — difficulty +1.
        view.update_composer_selection(evidence="")
        text = view.preview_label.text  # type: ignore[union-attr]
        assert "Effective 4" in text
        assert "Difficulty 5" in text
        assert "FAILS" in text
        view.on_exit()

    def test_preview_updates_when_audience_changes(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        # Set hask high disposition to verify preview reflects audience swap.
        view.active_dispute.delegates["ferron_hask"].disposition = 80  # type: ignore[union-attr]
        view.update_composer_selection(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        # Drift: disposition 50 -> mod 0. 3+1+0+0.15+0.20=4.35 -> 4 PASS
        text1 = view.preview_label.text  # type: ignore[union-attr]
        view.update_composer_selection(audience_delegate_id="ferron_hask")
        # Hask: disposition 80 -> mod 3. 3+1+3+0.15+0.20=7.35 -> 7 PASS easily.
        text2 = view.preview_label.text  # type: ignore[union-attr]
        assert text1 != text2
        assert "Effective 7" in text2

    def test_preview_updates_after_responds_to_change(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        view.update_composer_selection(
            framing="data_precedent",
            audience_delegate_id="samela_drift",
            evidence="forgeworks_2324_partnership",
        )
        text_before = view.preview_label.text  # type: ignore[union-attr]
        # Setting responds_to does not change the preview math itself
        # (it gates counter pre-emption later) but we still want the
        # preview to refresh.
        view.update_composer_selection(responds_to="soil_impact")
        text_after = view.preview_label.text  # type: ignore[union-attr]
        # Math unchanged, but the call path executed without error.
        assert text_after == text_before


# ---------------------------------------------------------------------------
# SA-P3 PT-M tutorial overlays (AC 9 + AC 10 + AC 11)
# ---------------------------------------------------------------------------


class TestTutorialOverlays:
    """The two PT-M tutorial overlays (venue + composer) fire once per save."""

    def test_venue_tip_fires_on_first_entry(self) -> None:
        from spacegame.constants.flags import seen_politics_venue_tip
        from spacegame.views.dispute_view import VENUE_TIP_BODY, VENUE_TIP_TITLE

        _manager, view, _ = _build_view()
        # New player: no flag yet.
        assert view.player.dialogue_flags.get(seen_politics_venue_tip(), False) is False
        view.on_enter()
        assert view._first_time_tip is not None
        assert view._first_time_tip.title == VENUE_TIP_TITLE
        assert view._first_time_tip.body == VENUE_TIP_BODY
        view.on_exit()

    def test_venue_tip_does_not_re_fire_after_dismiss(self) -> None:
        from spacegame.constants.flags import seen_politics_venue_tip

        _manager, view, _ = _build_view()
        view.on_enter()
        # Dismiss
        view._first_time_tip._dismiss()  # type: ignore[union-attr]
        assert view.player.dialogue_flags[seen_politics_venue_tip()] is True
        view.on_exit()

        # Re-enter: tip should not re-fire.
        view.on_enter()
        assert view._first_time_tip is None
        view.on_exit()

    def test_venue_tip_skipped_when_flag_already_set(self) -> None:
        from spacegame.constants.flags import seen_politics_venue_tip

        player = _build_player()
        player.dialogue_flags[seen_politics_venue_tip()] = True
        _manager, view, _ = _build_view(player)
        view.on_enter()
        assert view._first_time_tip is None
        view.on_exit()

    def test_composer_tip_fires_on_first_composer_open(self) -> None:
        # Pre-set the venue flag so the composer tip is the only one tested.
        from spacegame.constants.flags import seen_argument_composer_tip, seen_politics_venue_tip
        from spacegame.views.dispute_view import COMPOSER_TIP_BODY, COMPOSER_TIP_TITLE

        player = _build_player()
        player.dialogue_flags[seen_politics_venue_tip()] = True
        _manager, view, _ = _build_view(player)
        view.on_enter()
        assert view._first_time_tip is None  # venue tip suppressed
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        assert view._first_time_tip is not None
        assert view._first_time_tip.title == COMPOSER_TIP_TITLE
        assert view._first_time_tip.body == COMPOSER_TIP_BODY
        assert view.player.dialogue_flags.get(seen_argument_composer_tip(), False) is False
        view.on_exit()

    def test_composer_tip_does_not_re_fire_after_dismiss(self) -> None:
        from spacegame.constants.flags import (
            seen_argument_composer_tip,
            seen_politics_venue_tip,
        )

        player = _build_player()
        player.dialogue_flags[seen_politics_venue_tip()] = True
        _manager, view, _ = _build_view(player)
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        # Dismiss the composer tip.
        view._first_time_tip._dismiss()  # type: ignore[union-attr]
        assert player.dialogue_flags[seen_argument_composer_tip()] is True
        # Re-open the composer: the tip must not refire.
        view.back_to_list()
        view.open_dispute("water_rights_phasing")
        view.open_composer()
        assert view._first_time_tip is None
        view.on_exit()

    def test_overlay_consumes_keydown_event(self) -> None:
        _manager, view, _ = _build_view()
        view.on_enter()
        # While the venue tip is up, an Enter key should dismiss it and
        # the back-to-list path should NOT fire from event leakage.
        event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})
        view.handle_event(event)
        # Tip dismissed, back_button still in the LIST substate.
        assert view._first_time_tip is None or view._first_time_tip.dismissed
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-P4 — Annual Congress tutorial overlay (AC 12)
# ---------------------------------------------------------------------------


def _build_havens_view(
    player: Optional[Player] = None,
) -> tuple[pygame_gui.UIManager, DisputeView, PoliticsDisputeManager]:
    """Build a dispute view targeting the Haven's Rest Alliance Congress."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    if player is None:
        player = _build_player(faction_id="frontier_alliance", standing=0)
    tpl = _make_water_rights_phasing_template()
    dispute_mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        crew_roster=_StubBonus({"coalition_sway_bonus": 0.0}),
        progression=_StubBonus({"coalition_sway_bonus": 0.0}),
        social_manager=_StubSocial({"persuasion": 3, "leadership": 3}),
    )
    dispute_mgr.set_player(player)
    view = DisputeView(
        ui_manager=manager,
        player=player,
        dispute_manager=dispute_mgr,
        venue_id="havens_congress_hall",
        venue_faction_id="frontier_alliance",
    )
    return manager, view, dispute_mgr


class TestAnnualCongressTip:
    """SA-P4 — third PT-M overlay only fires at Haven's Rest."""

    def test_fires_on_first_havens_entry(self) -> None:
        # Skip the venue + composer tips so this one is the only candidate.
        from spacegame.constants.flags import (
            seen_annual_congress_tip,
            seen_argument_composer_tip,
            seen_politics_venue_tip,
        )
        from spacegame.views.dispute_view import (
            ANNUAL_CONGRESS_TIP_BODY,
            ANNUAL_CONGRESS_TIP_TITLE,
        )

        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_havens_view(player)
        assert view.player.dialogue_flags.get(seen_annual_congress_tip(), False) is False
        view.on_enter()
        assert view._first_time_tip is not None
        assert view._first_time_tip.title == ANNUAL_CONGRESS_TIP_TITLE
        assert view._first_time_tip.body == ANNUAL_CONGRESS_TIP_BODY
        view.on_exit()

    def test_does_not_re_fire_after_dismiss(self) -> None:
        from spacegame.constants.flags import (
            seen_annual_congress_tip,
            seen_argument_composer_tip,
            seen_politics_venue_tip,
        )

        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_havens_view(player)
        view.on_enter()
        assert view._first_time_tip is not None
        view._first_time_tip._dismiss()  # type: ignore[union-attr]
        assert player.dialogue_flags[seen_annual_congress_tip()] is True
        view.on_exit()
        view.on_enter()
        # Re-entry should not fire the annual congress tip again.
        assert view._first_time_tip is None
        view.on_exit()

    def test_not_fired_at_verdant_venue(self) -> None:
        """The Annual Congress tip must NOT fire at the Verdant venue."""
        from spacegame.constants.flags import (
            seen_annual_congress_tip,
            seen_argument_composer_tip,
            seen_politics_venue_tip,
        )

        # Build a Verdant view as usual; pre-set the SA-P3 tips so only the
        # SA-P4 tip would have a chance to fire.
        player = _build_player()
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_view(player)
        view.on_enter()
        # Tip not present.
        assert view._first_time_tip is None
        # Flag never gets set.
        assert player.dialogue_flags.get(seen_annual_congress_tip(), False) is False
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-P4 — LOCKED_OUT_ANNUAL list substate (AC 13)
# ---------------------------------------------------------------------------


class TestLockedOutAnnualSubstate:
    """The Haven's Rest list substate enters LOCKED_OUT_ANNUAL during recess."""

    def _attach_annual_template(
        self,
        dispute_mgr: PoliticsDisputeManager,
        *,
        last_resolved_day: Optional[int] = None,
    ) -> str:
        """Register an annual template and optionally seed the lockout."""
        from spacegame.models.politics_dispute import (
            DelegateTemplate,
            OutcomeRow,
            PoliticsDisputeTemplate,
        )

        delegates = (
            DelegateTemplate(
                delegate_id="councillor_wentworth",
                name="Councillor Wentworth",
                starting_visible_state="wavering",
                position_vector={"process_fidelity": 0.0},
            ),
        )
        outcome_matrix = {
            "win": OutcomeRow(rep_deltas={"frontier_alliance": 5}),
            "partial_win_coalition_thin": OutcomeRow(rep_deltas={}, news_headline=None),
            "partial_win_off_record": OutcomeRow(rep_deltas={}, news_headline=None),
            "loss": OutcomeRow(rep_deltas={"frontier_alliance": -2}),
        }
        tpl = PoliticsDisputeTemplate(
            id="annual_alliance_congress",
            headline="Annual Alliance Congress",
            factions_affected=("frontier_alliance",),
            base_difficulty=4,
            round_count=5,
            deadline_days=20,
            delegates=delegates,
            eligible_framings=("process_fidelity",),
            eligible_evidence=(),
            framing_modifiers={"process_fidelity": 0},
            framing_target_dimensions={"process_fidelity": "process_fidelity"},
            outcome_matrix=outcome_matrix,
            is_annual_congress=True,
            opens_on_day_offset=0,
            next_congress_offset_days=365,
        )
        dispute_mgr.register_template(tpl)
        if last_resolved_day is not None:
            dispute_mgr.record_annual_resolution(tpl.id, last_resolved_day)
        return tpl.id

    def test_substate_active_when_annual_locked_out(self) -> None:
        """When the only annual template is locked out, the list shows recess."""
        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.game_day = 100
        _manager, view, mgr = _build_havens_view(player)
        # Drop SA-P2's water_rights template so the only template is the annual.
        mgr._templates.pop("water_rights_phasing", None)
        self._attach_annual_template(mgr, last_resolved_day=50)
        view.on_enter()
        assert view.list_state == DisputeListState.LOCKED_OUT_ANNUAL
        # Days remaining: 50 + 365 - 100 = 315.
        assert view._annual_recess_days_remaining == 315
        view.on_exit()

    def test_substate_inactive_when_annual_open(self) -> None:
        """When the annual template is in its open window, normal EMPTY/READY."""
        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.game_day = 1
        _manager, view, mgr = _build_havens_view(player)
        mgr._templates.pop("water_rights_phasing", None)
        # No prior resolution -> active.
        self._attach_annual_template(mgr, last_resolved_day=None)
        view.on_enter()
        assert view.list_state == DisputeListState.EMPTY
        view.on_exit()

    def test_substate_does_not_fire_at_verdant(self) -> None:
        """The Verdant venue has no annual templates and never enters lockout."""
        player = _build_player()
        _manager, view, _ = _build_view(player, register_dispute=False)
        view.on_enter()
        # No annual templates, so the substate stays at EMPTY.
        assert view.list_state == DisputeListState.EMPTY
        assert view._annual_recess_days_remaining == 0
        view.on_exit()

    def test_no_dispute_buttons_during_recess(self) -> None:
        """Enter buttons are not built during the annual recess substate."""
        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.game_day = 100
        _manager, view, mgr = _build_havens_view(player)
        mgr._templates.pop("water_rights_phasing", None)
        self._attach_annual_template(mgr, last_resolved_day=50)
        view.on_enter()
        assert view.list_state == DisputeListState.LOCKED_OUT_ANNUAL
        assert len(view._dispute_buttons) == 0
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-P5 — helpers
# ---------------------------------------------------------------------------


def _build_reach_view(
    player: Optional[Player] = None,
    *,
    register_dispute: bool = True,
) -> tuple[pygame_gui.UIManager, DisputeView, PoliticsDisputeManager]:
    """Build a DisputeView targeting the Crimson Reach Wreckers' Guild venue."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    if player is None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 1  # apprentice
    tpl = _make_water_rights_phasing_template()
    dispute_mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        crew_roster=_StubBonus({"coalition_sway_bonus": 0.0}),
        progression=_StubBonus({"coalition_sway_bonus": 0.0}),
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
        venue_id="crimson_wreckers_guild",
        venue_faction_id="crimson_reach",
    )
    return manager, view, dispute_mgr


# ---------------------------------------------------------------------------
# SA-P5 — LOCKED_NO_MEMBERSHIP list substate (AC 10)
# ---------------------------------------------------------------------------


class TestLockedNoMembershipSubstate:
    """SA-P5: Reach venue shows LOCKED_NO_MEMBERSHIP for unjoined players."""

    def test_unjoined_player_at_reach_hits_locked_no_membership(self) -> None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        # sub_reputation empty → unjoined tier
        _manager, view, _ = _build_reach_view(player)
        view.on_enter()
        assert view.list_state == DisputeListState.LOCKED_NO_MEMBERSHIP
        assert len(view._dispute_buttons) == 0
        view.on_exit()

    def test_enrolled_player_at_reach_bypasses_locked_no_membership(self) -> None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 1  # apprentice
        _manager, view, _ = _build_reach_view(player)
        view.on_enter()
        assert view.list_state != DisputeListState.LOCKED_NO_MEMBERSHIP
        view.on_exit()

    def test_locked_no_membership_not_triggered_at_verdant(self) -> None:
        """Verdant venue never enters LOCKED_NO_MEMBERSHIP regardless of sub_rep."""
        player = _build_player()  # default verdant, no wreckers sub_rep
        _manager, view, _ = _build_view(player)
        view.on_enter()
        assert view.list_state != DisputeListState.LOCKED_NO_MEMBERSHIP
        view.on_exit()

    def test_locked_no_membership_text_constant_content(self) -> None:
        from spacegame.views.dispute_view import LOCKED_NO_MEMBERSHIP_TEXT

        player = _build_player(faction_id="crimson_reach", standing=0)
        _manager, view, _ = _build_reach_view(player)
        view.on_enter()
        assert view.list_state == DisputeListState.LOCKED_NO_MEMBERSHIP
        # Constant references the Guild floor and tier progression.
        assert "Guild floor" in LOCKED_NO_MEMBERSHIP_TEXT
        assert "journeymen" in LOCKED_NO_MEMBERSHIP_TEXT.lower()
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-P5 — per-tier action button gating (AC 11)
# ---------------------------------------------------------------------------


class TestTierGatedActionButtons:
    """SA-P5: Reach venue session buttons gated by Wreckers' Guild tier."""

    def _open_session(self, player: Player) -> DisputeView:
        _manager, view, dispute_mgr = _build_reach_view(player)
        view.on_enter()
        ids = dispute_mgr.get_pending_dispute_ids()
        assert ids, "No pending disputes to open"
        view.open_dispute(ids[0])
        return view

    def test_apprentice_all_buttons_disabled(self) -> None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 1  # apprentice
        view = self._open_session(player)
        assert view.substate == DisputeSubstate.SESSION
        for key, btn in view._action_buttons.items():
            assert not btn.is_enabled, f"Expected {key!r} disabled for apprentice"
        view.on_exit()

    def test_journeyman_argue_vote_abstain_enabled_mediate_disabled(self) -> None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 30  # journeyman
        view = self._open_session(player)
        assert view.substate == DisputeSubstate.SESSION
        assert view._action_buttons["argue"].is_enabled
        assert view._action_buttons["vote_now"].is_enabled
        assert view._action_buttons["abstain"].is_enabled
        assert not view._action_buttons["mediate"].is_enabled
        view.on_exit()

    def test_master_all_buttons_enabled(self) -> None:
        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 70  # master
        view = self._open_session(player)
        assert view.substate == DisputeSubstate.SESSION
        for key, btn in view._action_buttons.items():
            assert btn.is_enabled, f"Expected {key!r} enabled for master"
        view.on_exit()

    def test_verdant_venue_all_buttons_enabled_regardless_of_sub_rep(self) -> None:
        """Non-Reach venues must not apply tier gating."""
        player = _build_player()  # verdant, no wreckers sub_rep
        _manager, view, _ = _build_view(player)
        view.on_enter()
        view.open_dispute("water_rights_phasing")
        assert view.substate == DisputeSubstate.SESSION
        for key, btn in view._action_buttons.items():
            assert btn.is_enabled, f"Expected {key!r} enabled at Verdant venue"
        view.on_exit()


# ---------------------------------------------------------------------------
# SA-P5 — gray-market arbitration tip overlay (AC 9)
# ---------------------------------------------------------------------------


class TestGrayMarketArbitrationTip:
    """SA-P5: gray-market arbitration tip fires once on first Reach entry."""

    def test_fires_on_first_reach_entry(self) -> None:
        from spacegame.constants.flags import (
            seen_argument_composer_tip,
            seen_gray_market_arbitration_tip,
            seen_politics_venue_tip,
        )
        from spacegame.views.dispute_view import (
            GRAY_MARKET_ARBITRATION_TIP_BODY,
            GRAY_MARKET_ARBITRATION_TIP_TITLE,
        )

        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 1
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_reach_view(player)
        assert player.dialogue_flags.get(seen_gray_market_arbitration_tip(), False) is False
        view.on_enter()
        assert view._first_time_tip is not None
        assert view._first_time_tip.title == GRAY_MARKET_ARBITRATION_TIP_TITLE
        assert view._first_time_tip.body == GRAY_MARKET_ARBITRATION_TIP_BODY
        view.on_exit()

    def test_does_not_re_fire_after_dismiss(self) -> None:
        from spacegame.constants.flags import (
            seen_argument_composer_tip,
            seen_gray_market_arbitration_tip,
            seen_politics_venue_tip,
        )

        player = _build_player(faction_id="crimson_reach", standing=0)
        player.sub_reputation["wreckers_guild"] = 1
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_reach_view(player)
        view.on_enter()
        assert view._first_time_tip is not None
        view._first_time_tip._dismiss()  # type: ignore[union-attr]
        assert player.dialogue_flags[seen_gray_market_arbitration_tip()] is True
        view.on_exit()
        # Re-entry must not refire.
        view.on_enter()
        assert view._first_time_tip is None
        view.on_exit()

    def test_not_fired_at_verdant_venue(self) -> None:
        from spacegame.constants.flags import (
            seen_argument_composer_tip,
            seen_gray_market_arbitration_tip,
            seen_politics_venue_tip,
        )

        player = _build_player()
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        _manager, view, _ = _build_view(player)
        view.on_enter()
        assert view._first_time_tip is None
        assert player.dialogue_flags.get(seen_gray_market_arbitration_tip(), False) is False
        view.on_exit()

    def test_not_fired_at_havens_rest(self) -> None:
        from spacegame.constants.flags import (
            seen_annual_congress_tip,
            seen_argument_composer_tip,
            seen_gray_market_arbitration_tip,
            seen_politics_venue_tip,
        )

        player = _build_player(faction_id="frontier_alliance", standing=0)
        player.dialogue_flags[seen_politics_venue_tip()] = True
        player.dialogue_flags[seen_argument_composer_tip()] = True
        player.dialogue_flags[seen_annual_congress_tip()] = True
        _manager, view, _ = _build_havens_view(player)
        view.on_enter()
        assert view._first_time_tip is None
        assert player.dialogue_flags.get(seen_gray_market_arbitration_tip(), False) is False
        view.on_exit()
