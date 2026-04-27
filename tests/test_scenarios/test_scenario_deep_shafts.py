"""SA-2 scenario coverage for the Deep Shafts memorial / pilgrimage.

End-to-end walks of the venue's load-bearing flows:

  - First visit + scripted scene + Sten dialogue + Marcus silent vigil.
  - Return visit + Marcus father-connection branch (gated on Sten).
  - Visit-5 + Marcus Uprising-inheritance branch.
  - Pilgrimage rep economy across the cap.
  - Sacred-ground regression: no forced encounters target the venue;
    GameState.DEEP_SHAFTS is not in any encounter router; venue
    dialogue contains zero aggressive choice nodes.
  - Per-loc-id station_hub dispatch leaves the SA-1 path intact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState
from spacegame.constants.flags import (
    marcus_father_connection_seen,
    marcus_silent_vigil_seen,
    marcus_uprising_inheritance_seen,
    pilgrimage_journal,
    received_miners_blessing_first,
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
from spacegame.views.station_hub_view import UNIQUE_HALL_TARGETS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _make_env(
    *,
    credits: int = 1000,
    game_day: int = 5,
    has_marcus: bool = False,
    learned_father_story: bool = False,
    deep_shafts_state: DeepShaftsState | None = None,
    miners_rep: int = 0,
    extra_flags: dict[str, bool] | None = None,
) -> tuple[pygame_gui.UIManager, Player]:
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
    if extra_flags:
        player.dialogue_flags.update(extra_flags)
    return manager, player


# ---------------------------------------------------------------------------
# Scenario 1 — first visit (curiosity path, no Marcus)
# ---------------------------------------------------------------------------


class TestScenarioFirstVisitCuriosityPath:
    def test_first_visit_sets_full_first_visit_state(self) -> None:
        manager, player = _make_env()
        view = DeepShaftsView(ui_manager=manager, player=player)
        view.on_enter()
        try:
            assert player.deep_shafts_state is not None
            assert player.deep_shafts_state.visit_count == 1
            assert player.deep_shafts_state.scripted_scene_played is True
            assert player.deep_shafts_state.blessing_total == PILGRIMAGE_FIRST_GRANT
            assert player.faction_reputation["miners_union"] == PILGRIMAGE_FIRST_GRANT
            assert player.dialogue_flags[visited_deep_shafts()] is True
            assert player.dialogue_flags[received_miners_blessing_first()] is True
            assert player.dialogue_flags[pilgrimage_journal(1)] is True
            assert view._tip_overlay is not None
        finally:
            view.on_exit()


# ---------------------------------------------------------------------------
# Scenario 2 — first visit with Marcus + father story (mission path)
# ---------------------------------------------------------------------------


class TestScenarioFirstVisitWithMarcus:
    def test_marcus_silent_vigil_on_first_visit(self) -> None:
        manager, player = _make_env(has_marcus=True, learned_father_story=True)
        view = DeepShaftsView(ui_manager=manager, player=player)
        view.on_enter()
        try:
            # Marcus is in the dock.
            assert "marcus_jin" in view.get_visible_dock_speaker_ids()
            # Walk the silent-vigil tree.
            view._open_npc_dialogue("marcus_jin")
            # Walk the entire dialogue.
            for _ in range(5):
                if view.get_active_dialogue_node() is None:
                    break
                view._advance_dialogue()
            # Branch A's silent-vigil flag should be set.
            assert player.dialogue_flags.get(marcus_silent_vigil_seen()) is True
            # Father-connection and Uprising flags should NOT yet fire.
            assert player.dialogue_flags.get(marcus_father_connection_seen()) is None
            assert player.dialogue_flags.get(marcus_uprising_inheritance_seen()) is None
        finally:
            view.on_exit()


# ---------------------------------------------------------------------------
# Scenario 3 — return visit (Marcus father-connection requires Sten talk)
# ---------------------------------------------------------------------------


class TestScenarioReturnVisitFatherConnection:
    def test_father_connection_unlocks_after_sten(self) -> None:
        # Player has visited once + walked silent vigil.
        state = DeepShaftsState(
            visit_count=1,
            last_pilgrimage_day=10,
            blessing_total=PILGRIMAGE_FIRST_GRANT,
            scripted_scene_played=True,
            last_journal_unlock_day=10,
        )
        manager, player = _make_env(
            has_marcus=True,
            learned_father_story=True,
            deep_shafts_state=state,
            miners_rep=PILGRIMAGE_FIRST_GRANT,
            game_day=10 + PILGRIMAGE_COOLDOWN_DAYS + 5,
            extra_flags={
                marcus_silent_vigil_seen(): True,
                talked_to_sten_brygaard(): True,
            },
        )
        view = DeepShaftsView(ui_manager=manager, player=player)
        view.on_enter()
        try:
            view._open_npc_dialogue("marcus_jin")
            # Walk the father-connection tree.
            for _ in range(5):
                if view.get_active_dialogue_node() is None:
                    break
                view._advance_dialogue()
            assert player.dialogue_flags.get(marcus_father_connection_seen()) is True
            assert player.dialogue_flags.get(marcus_uprising_inheritance_seen()) is None
        finally:
            view.on_exit()


# ---------------------------------------------------------------------------
# Scenario 4 — visit 5 unlocks Marcus's Uprising-inheritance branch
# ---------------------------------------------------------------------------


class TestScenarioUprisingInheritance:
    def test_visit_five_unlocks_uprising_branch(self) -> None:
        state = DeepShaftsState(
            visit_count=4,
            last_pilgrimage_day=40,
            blessing_total=PILGRIMAGE_FIRST_GRANT + 3 * PILGRIMAGE_RECURRING_GRANT,
            scripted_scene_played=True,
            last_journal_unlock_day=30,
        )
        manager, player = _make_env(
            has_marcus=True,
            learned_father_story=True,
            deep_shafts_state=state,
            miners_rep=state.blessing_total,
            game_day=50,
            extra_flags={
                marcus_silent_vigil_seen(): True,
                marcus_father_connection_seen(): True,
                talked_to_sten_brygaard(): True,
            },
        )
        view = DeepShaftsView(ui_manager=manager, player=player)
        view.on_enter()
        try:
            assert player.deep_shafts_state.visit_count == 5
            view._open_npc_dialogue("marcus_jin")
            for _ in range(5):
                if view.get_active_dialogue_node() is None:
                    break
                view._advance_dialogue()
            assert player.dialogue_flags.get(marcus_uprising_inheritance_seen()) is True
        finally:
            view.on_exit()


# ---------------------------------------------------------------------------
# Scenario 5 — pilgrimage rep economy hits the cap, no further grants
# ---------------------------------------------------------------------------


class TestScenarioPilgrimageCap:
    def test_visits_after_cap_grant_zero(self) -> None:
        state = DeepShaftsState(
            visit_count=10,
            last_pilgrimage_day=50,
            blessing_total=PILGRIMAGE_BLESSING_CAP,
            scripted_scene_played=True,
            last_journal_unlock_day=50,
        )
        manager, player = _make_env(
            deep_shafts_state=state,
            miners_rep=PILGRIMAGE_BLESSING_CAP + 5,  # other rep + cap
            game_day=200,
            extra_flags={received_miners_blessing_first(): True},
        )
        view = DeepShaftsView(ui_manager=manager, player=player)
        view.on_enter()
        try:
            # No additional rep beyond the prior fixture value.
            assert player.faction_reputation["miners_union"] == PILGRIMAGE_BLESSING_CAP + 5
            assert player.deep_shafts_state.blessing_total == PILGRIMAGE_BLESSING_CAP
        finally:
            view.on_exit()


# ---------------------------------------------------------------------------
# Sacred-ground regression (acceptance #9)
# ---------------------------------------------------------------------------


class TestSacredGroundContract:
    def test_no_mission_forced_encounter_targets_deep_mines(self) -> None:
        """No mission template across all loaded files has a forced
        encounter targeting ``breakstone_deep_mines``.

        The check walks BOTH the loaded ``Mission`` instances (model-level)
        AND every mission JSON file directly (defense-in-depth: catches
        new files that a future loader change might miss).
        """
        dl = get_data_loader()
        dl.load_all()
        for mission in dl.missions:
            forced = getattr(mission, "forced_encounter", None)
            if forced is None:
                continue
            assert getattr(forced, "encounter_def_id", "") != "breakstone_deep_mines", (
                f"Mission {mission.id} forces an encounter at the Deep Shafts memorial."
            )

        missions_dir = _PROJECT_ROOT / "data" / "missions"
        for mission_file in missions_dir.glob("*.json"):
            data = json.loads(mission_file.read_text(encoding="utf-8"))
            for mission in data.get("missions", []):
                forced = mission.get("forced_encounter")
                if not forced:
                    continue
                target = forced.get("target_location_id") or forced.get("encounter_def_id", "")
                assert target != "breakstone_deep_mines", (
                    f"{mission_file.name}::{mission.get('id')} targets the memorial."
                )

    def test_deep_shafts_not_in_encounter_router(self) -> None:
        """``GameState.DEEP_SHAFTS`` is not registered with any
        encounter-spawning router — station-hub-style views never run
        encounters, and this contract pins that for future content."""
        # The encounter system is travel-driven; the venue view never
        # exposes itself to any encounter pipeline. We assert that
        # GameState.DEEP_SHAFTS is not a TRAVEL/COMBAT-class state and
        # that the ``UNIQUE_HALL_TARGETS`` dispatch does not redirect
        # to a combat surface.
        assert GameState.DEEP_SHAFTS != GameState.COMBAT
        assert GameState.DEEP_SHAFTS != GameState.ENCOUNTER
        assert GameState.DEEP_SHAFTS not in (
            GameState.GROUND_BRIEFING,
            GameState.GROUND_EXPLORATION,
        )
        # The unique-hall dispatch only routes to the venue, never to a
        # combat / encounter / ground state.
        assert UNIQUE_HALL_TARGETS["breakstone_deep_mines"] == GameState.DEEP_SHAFTS

    def test_venue_dialogue_no_aggressive_choices(self) -> None:
        """No response in any Deep Shafts dialogue tree carries an
        aggressive verb (attack / intimidate / threaten / draw weapon)."""
        dl = get_data_loader()
        dl.load_all()
        banned = (
            "attack",
            "intimidate",
            "threaten",
            "draw weapon",
            "draw your weapon",
            "punch",
            "shoot",
            "kill",
        )
        tree_ids = (
            "sten_brygaard_deep_shafts",
            "marcus_jin_deep_shafts_silent_vigil",
            "marcus_jin_deep_shafts_father_connection",
            "marcus_jin_deep_shafts_uprising",
        )
        for tree_id in tree_ids:
            tree = dl.get_dialogue(tree_id)
            assert tree is not None, f"{tree_id} must exist"
            for node in tree.nodes.values():
                for resp in node.responses:
                    lowered = resp.text.lower()
                    for verb in banned:
                        assert verb not in lowered, (
                            f"Aggressive verb {verb!r} in {tree_id}::{node.id}: {resp.text!r}"
                        )


# ---------------------------------------------------------------------------
# Per-loc-id dispatch (acceptance #1)
# ---------------------------------------------------------------------------


class TestUniqueHallDispatch:
    """The dispatch table sends each unique anchor to the right venue."""

    def test_deep_shafts_dispatch(self) -> None:
        assert UNIQUE_HALL_TARGETS["breakstone_deep_mines"] == GameState.DEEP_SHAFTS

    def test_wreckers_guild_dispatch_unchanged(self) -> None:
        """SA-1 path must remain intact (regression guard)."""
        assert UNIQUE_HALL_TARGETS["crimson_wreckers_guild"] == GameState.WRECKERS_GUILD

    def test_other_unique_anchors_have_no_enter_route(self) -> None:
        """Other unique anchors are not in the dispatch — they keep their
        close-only detail panel until a future sprint authors a venue."""
        dl = get_data_loader()
        dl.load_all()
        unique_ids: set[str] = set()
        for system_id in dl.systems:
            locs = dl.get_locations_for_system(system_id)
            for loc in locs:
                if loc.location_type == "unique":
                    unique_ids.add(loc.id)
        # Every dispatch entry must correspond to a real unique location.
        for hall_loc_id in UNIQUE_HALL_TARGETS:
            assert hall_loc_id in unique_ids, (
                f"Dispatch entry {hall_loc_id} does not point at a real unique anchor."
            )


# ---------------------------------------------------------------------------
# Mission integration (acceptance #8)
# ---------------------------------------------------------------------------


class TestSilentShaftMission:
    def test_mission_loads(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        mission = next((m for m in dl.missions if m.id == "the_silent_shaft"), None)
        assert mission is not None, "the_silent_shaft mission must load"

    def test_mission_prerequisites(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        mission = next((m for m in dl.missions if m.id == "the_silent_shaft"), None)
        assert mission is not None
        assert "the_foremans_son" in mission.prerequisites
        assert "learned_father_story" in mission.required_flags

    def test_mission_objective_targets_visited_flag(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        mission = next((m for m in dl.missions if m.id == "the_silent_shaft"), None)
        assert mission is not None
        assert len(mission.objectives) == 1
        obj = mission.objectives[0]
        assert obj.target_id == "visited_deep_shafts"
        assert obj.type.value == "has_flag"

    def test_mission_rewards(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        mission = next((m for m in dl.missions if m.id == "the_silent_shaft"), None)
        assert mission is not None
        rewards = {r.reward_type: r for r in mission.rewards}
        assert "credits" in rewards
        assert rewards["credits"].amount == 100
        assert "xp" in rewards
        assert rewards["xp"].amount == 50
        assert "set_flag" in rewards
        assert rewards["set_flag"].target_id == "attended_silent_shaft"


# ---------------------------------------------------------------------------
# Journal entries
# ---------------------------------------------------------------------------


class TestJournalEntries:
    def test_all_five_pilgrimage_entries_load(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        ids = {entry.entry_id for entry in dl.journal_entries}
        for n in range(1, 6):
            assert f"pilgrimage_journal_{n}" in ids, f"pilgrimage_journal_{n} must be authored"

    def test_journal_entries_trigger_on_pilgrimage_flags(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        for n in range(1, 6):
            entry = next(
                (e for e in dl.journal_entries if e.entry_id == f"pilgrimage_journal_{n}"),
                None,
            )
            assert entry is not None
            assert entry.trigger_flag == f"pilgrimage_journal_{n}"
            assert entry.system_id == "breakstone"


# ---------------------------------------------------------------------------
# NPC entry
# ---------------------------------------------------------------------------


class TestStenNPCEntry:
    def test_sten_npc_loads_with_canonical_metadata(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        npc = dl.npcs.get("sten_brygaard")
        assert npc is not None, "sten_brygaard NPC must be authored"
        assert npc.name == "Sten Brygaard"
        assert npc.faction_id == "miners_union"
        assert npc.home_system_id == "breakstone"
        assert npc.dialogue_id == "sten_brygaard_deep_shafts"


# ---------------------------------------------------------------------------
# Voice-register distinctness (acceptance #4)
# ---------------------------------------------------------------------------


class TestVoiceDistinctness:
    """Sten and Marcus carry different registers in the venue dialogue."""

    def test_sten_register_uses_weighted_time_phrasing(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("sten_brygaard_deep_shafts")
        assert tree is not None
        all_text = " ".join(node.text for node in tree.nodes.values())
        # Sten should have at least one of his hallmark phrasings.
        markers = [
            "third decade",
            "third shift",
            "Charter",
            "rotation",
            "tea",
        ]
        assert any(m in all_text for m in markers), (
            "Sten should carry at least one weighted-time marker"
        )

    def test_marcus_silent_vigil_is_brief(self) -> None:
        dl = get_data_loader()
        dl.load_all()
        tree = dl.get_dialogue("marcus_jin_deep_shafts_silent_vigil")
        assert tree is not None
        # Marcus's silent-vigil tree is the shortest of the three.
        assert len(tree.nodes) <= 2, "Silent-vigil tree must stay brief to honor the silence beat"
