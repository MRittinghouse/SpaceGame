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
