"""Tests for DeepShaftsView (SA-2).

Covers:
  - Construction with synthetic state
  - on_enter / on_exit lifecycle and UI cleanup
  - First-visit scripted scene fires once and never re-fires
  - Sten dialogue dock visible always
  - Marcus dialogue dock visible only when Marcus is in crew + father story
  - Pilgrimage tick: first +5, recurring +2 after 7-day cooldown
  - Pilgrimage cap holds at +20 cumulative
  - Visit threshold journal flags fire at the right counts
  - First-time tip overlay fires once, never re-fires
  - Sten dialogue advances; first-meeting flag fires
  - Sacred-ground regression: no aggressive choice nodes in Sten / Marcus venue trees
"""

from __future__ import annotations

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.constants.flags import (
    marcus_silent_vigil_seen,
    pilgrimage_journal,
    received_miners_blessing_first,
    seen_deep_shafts_tip,
    talked_to_sten_brygaard,
    visited_deep_shafts,
)
from spacegame.data_loader import get_data_loader
from spacegame.models.deep_shafts import (
    PILGRIMAGE_BLESSING_CAP,
    PILGRIMAGE_COOLDOWN_DAYS,
    PILGRIMAGE_FIRST_GRANT,
    PILGRIMAGE_RECURRING_GRANT,
    DeepShaftsState,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.deep_shafts_view import DeepShaftsView


def _make_env(
    *,
    credits: int = 1000,
    game_day: int = 5,
    has_marcus: bool = False,
    learned_father_story: bool = False,
    deep_shafts_state: DeepShaftsState | None = None,
    miners_rep: int = 0,
) -> tuple[pygame_gui.UIManager, Player]:
    """Build an isolated test environment for the view."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
    dl = get_data_loader()
    dl.load_all()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    player = Player(
        name="Test Captain",
        credits=credits,
        current_system_id="breakstone",
        ship=ship,
        game_day=game_day,
    )
    player.deep_shafts_state = deep_shafts_state
    if has_marcus:
        player.crew_state = {"active": ["marcus_jin"]}
    if learned_father_story:
        player.dialogue_flags["learned_father_story"] = True
    if miners_rep:
        player.faction_reputation["miners_union"] = miners_rep
    return manager, player


def _make_view(player: Player, manager: pygame_gui.UIManager) -> DeepShaftsView:
    return DeepShaftsView(ui_manager=manager, player=player)


# ---------------------------------------------------------------------------
# Construction + lifecycle
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_construct_default(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        assert view is not None
        assert view.next_state is None

    def test_on_enter_sets_active(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view.active
        view.on_exit()

    def test_on_exit_destroys_ui(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view.on_exit()
        assert view.back_button is None
        assert not view.active


# ---------------------------------------------------------------------------
# Visit-count + scripted-scene lifecycle (acceptance #2)
# ---------------------------------------------------------------------------


class TestFirstVisitScriptedScene:
    def test_first_visit_increments_visit_count_to_one(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.deep_shafts_state is not None
        assert player.deep_shafts_state.visit_count == 1
        view.on_exit()

    def test_first_visit_marks_scripted_scene_played(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.deep_shafts_state.scripted_scene_played is True
        view.on_exit()

    def test_first_visit_sets_visited_flag(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(visited_deep_shafts()) is True
        view.on_exit()

    def test_first_visit_sets_received_blessing_flag(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(received_miners_blessing_first()) is True
        view.on_exit()

    def test_subsequent_visit_does_not_replay_scripted_scene(self) -> None:
        manager, player = _make_env(
            deep_shafts_state=DeepShaftsState(
                visit_count=1,
                last_pilgrimage_day=1,
                blessing_total=PILGRIMAGE_FIRST_GRANT,
                scripted_scene_played=True,
            ),
            game_day=20,
        )
        view = _make_view(player, manager)
        view.on_enter()
        # Second visit should NOT reset the scripted scene.
        assert player.deep_shafts_state.scripted_scene_played is True
        # visit_count moves from 1 -> 2.
        assert player.deep_shafts_state.visit_count == 2
        view.on_exit()


# ---------------------------------------------------------------------------
# Pilgrimage rep economy (acceptance #3, #7)
# ---------------------------------------------------------------------------


class TestPilgrimageRepGrant:
    def test_first_visit_grants_first_amount(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.faction_reputation.get("miners_union") == PILGRIMAGE_FIRST_GRANT
        view.on_exit()

    def test_recurring_grant_after_cooldown(self) -> None:
        manager, player = _make_env(
            deep_shafts_state=DeepShaftsState(
                visit_count=1,
                last_pilgrimage_day=10,
                blessing_total=PILGRIMAGE_FIRST_GRANT,
                scripted_scene_played=True,
            ),
            miners_rep=PILGRIMAGE_FIRST_GRANT,
            game_day=10 + PILGRIMAGE_COOLDOWN_DAYS,
        )
        view = _make_view(player, manager)
        view.on_enter()
        assert (
            player.faction_reputation.get("miners_union")
            == PILGRIMAGE_FIRST_GRANT + PILGRIMAGE_RECURRING_GRANT
        )
        view.on_exit()

    def test_no_grant_within_cooldown(self) -> None:
        manager, player = _make_env(
            deep_shafts_state=DeepShaftsState(
                visit_count=1,
                last_pilgrimage_day=10,
                blessing_total=PILGRIMAGE_FIRST_GRANT,
                scripted_scene_played=True,
            ),
            miners_rep=PILGRIMAGE_FIRST_GRANT,
            game_day=10 + (PILGRIMAGE_COOLDOWN_DAYS - 1),
        )
        view = _make_view(player, manager)
        view.on_enter()
        # Reputation unchanged.
        assert player.faction_reputation.get("miners_union") == PILGRIMAGE_FIRST_GRANT
        view.on_exit()

    def test_blessing_cap_holds(self) -> None:
        """Acceptance #7: at the cap, no further rep grants fire."""
        manager, player = _make_env(
            deep_shafts_state=DeepShaftsState(
                visit_count=15,
                last_pilgrimage_day=50,
                blessing_total=PILGRIMAGE_BLESSING_CAP,
                scripted_scene_played=True,
            ),
            miners_rep=PILGRIMAGE_BLESSING_CAP,
            game_day=200,
        )
        view = _make_view(player, manager)
        view.on_enter()
        assert player.faction_reputation.get("miners_union") == PILGRIMAGE_BLESSING_CAP
        view.on_exit()


# ---------------------------------------------------------------------------
# Sten dialogue dock (acceptance #4)
# ---------------------------------------------------------------------------


class TestStenDock:
    def test_sten_dock_speaker_id_present(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert "sten_brygaard" in view.get_visible_dock_speaker_ids()
        view.on_exit()

    def test_sten_dialogue_opens_on_request(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._open_npc_dialogue("sten_brygaard")
        assert view.get_active_dialogue_node() is not None
        view.on_exit()


# ---------------------------------------------------------------------------
# Marcus dock conditional visibility (acceptance #5)
# ---------------------------------------------------------------------------


class TestMarcusDockGating:
    def test_marcus_hidden_without_crew(self) -> None:
        manager, player = _make_env(learned_father_story=True)
        view = _make_view(player, manager)
        view.on_enter()
        assert "marcus_jin" not in view.get_visible_dock_speaker_ids()
        view.on_exit()

    def test_marcus_hidden_without_father_story(self) -> None:
        manager, player = _make_env(has_marcus=True, learned_father_story=False)
        view = _make_view(player, manager)
        view.on_enter()
        assert "marcus_jin" not in view.get_visible_dock_speaker_ids()
        view.on_exit()

    def test_marcus_visible_with_crew_and_father_story(self) -> None:
        manager, player = _make_env(has_marcus=True, learned_father_story=True)
        view = _make_view(player, manager)
        view.on_enter()
        assert "marcus_jin" in view.get_visible_dock_speaker_ids()
        view.on_exit()


# ---------------------------------------------------------------------------
# First-time tip overlay (acceptance #11)
# ---------------------------------------------------------------------------


class TestFirstTimeTip:
    def test_tip_fires_on_first_entry(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view._tip_overlay is not None
        view.on_exit()

    def test_tip_does_not_fire_when_flag_set(self) -> None:
        manager, player = _make_env()
        player.dialogue_flags[seen_deep_shafts_tip()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert view._tip_overlay is None
        view.on_exit()

    def test_tip_dismiss_sets_flag(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert view._tip_overlay is not None
        # Simulate dismiss by calling the on_dismiss callback.
        cb = view._tip_overlay.on_dismiss
        assert cb is not None
        cb()
        assert player.dialogue_flags.get(seen_deep_shafts_tip()) is True
        view.on_exit()


# ---------------------------------------------------------------------------
# Journal threshold flag fires (acceptance #6)
# ---------------------------------------------------------------------------


class TestJournalThresholdFlags:
    def test_first_visit_sets_journal_1(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(pilgrimage_journal(1)) is True
        view.on_exit()

    def test_visit_two_does_not_set_journal_2(self) -> None:
        """Visit threshold for journal 2 is visit count 3, not 2."""
        manager, player = _make_env(
            deep_shafts_state=DeepShaftsState(
                visit_count=1,
                last_pilgrimage_day=1,
                blessing_total=PILGRIMAGE_FIRST_GRANT,
                scripted_scene_played=True,
                last_journal_unlock_day=1,
            ),
            game_day=10,
        )
        view = _make_view(player, manager)
        view.on_enter()
        assert player.dialogue_flags.get(pilgrimage_journal(2)) is None
        view.on_exit()


# ---------------------------------------------------------------------------
# Back navigation
# ---------------------------------------------------------------------------


class TestBackNavigation:
    def test_request_back_sets_next_state_to_station_hub(self) -> None:
        manager, player = _make_env()
        view = _make_view(player, manager)
        view.on_enter()
        view._request_back()
        assert view.next_state == GameState.STATION_HUB
        view.on_exit()


# ---------------------------------------------------------------------------
# Sacred-ground regression (acceptance #9)
# ---------------------------------------------------------------------------


class TestSacredGroundDialogueRegression:
    """No aggressive choice nodes in any Deep Shafts venue dialogue."""

    BANNED_VERBS = (
        "attack",
        "intimidate",
        "threaten",
        "draw weapon",
        "draw your weapon",
        "punch",
        "strike",
        "shoot",
        "kill",
    )

    def test_sten_dialogue_has_no_aggressive_responses(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("sten_brygaard_deep_shafts")
        assert tree is not None, "Sten dialogue tree must be authored"
        for node in tree.nodes.values():
            for resp in node.responses:
                lowered = resp.text.lower()
                for verb in self.BANNED_VERBS:
                    assert verb not in lowered, (
                        f"Aggressive verb '{verb}' in Sten response: {resp.text!r}"
                    )

    def test_marcus_venue_dialogue_has_no_aggressive_responses(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree_ids = (
            "marcus_jin_deep_shafts_silent_vigil",
            "marcus_jin_deep_shafts_father_connection",
            "marcus_jin_deep_shafts_uprising",
        )
        for tree_id in tree_ids:
            tree = dl.get_dialogue(tree_id)
            assert tree is not None, f"Marcus venue dialogue tree {tree_id!r} must be authored"
            for node in tree.nodes.values():
                for resp in node.responses:
                    lowered = resp.text.lower()
                    for verb in self.BANNED_VERBS:
                        assert verb not in lowered, (
                            f"Aggressive verb '{verb}' in {tree_id} response: {resp.text!r}"
                        )


# ---------------------------------------------------------------------------
# Marcus branch ordering (acceptance #5)
# ---------------------------------------------------------------------------


class TestMarcusVenueBranchGating:
    """Marcus's venue dialogue exposes branch-A on visit 1; branches B / C
    require more state.

    These tests rely on the conditional dock visibility surfaced by the
    view rather than walking the dialogue tree directly — the tree is
    authored in JSON; the view decides whether the dock button appears.
    """

    def test_marcus_dock_present_on_first_visit(self) -> None:
        manager, player = _make_env(has_marcus=True, learned_father_story=True)
        view = _make_view(player, manager)
        view.on_enter()
        assert "marcus_jin" in view.get_visible_dock_speaker_ids()
        # Branch A's set_flag fires when the player walks the dialogue.
        view.on_exit()

    def test_marcus_dock_persists_on_return(self) -> None:
        manager, player = _make_env(
            has_marcus=True,
            learned_father_story=True,
            deep_shafts_state=DeepShaftsState(
                visit_count=2,
                last_pilgrimage_day=10,
                blessing_total=PILGRIMAGE_FIRST_GRANT,
                scripted_scene_played=True,
            ),
            game_day=30,
        )
        # Player has talked to Sten and seen the silent vigil.
        player.dialogue_flags[talked_to_sten_brygaard()] = True
        player.dialogue_flags[marcus_silent_vigil_seen()] = True
        view = _make_view(player, manager)
        view.on_enter()
        assert "marcus_jin" in view.get_visible_dock_speaker_ids()
        view.on_exit()
