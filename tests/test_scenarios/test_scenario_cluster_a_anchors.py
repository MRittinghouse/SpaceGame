"""SA-0: Cluster A confirmation pass — scenario tests.

Verifies that Restricted Sector 7 (iron_depths_restricted_zone),
Restricted Research Wing (nova_restricted_labs), and Assembly Core
(fulcrum_core) surface correctly under the SL-1 conditional-demotion
rule.

Also validates the two new depth-tier intelligence beats:
  - Naveen Prakash (iron_depths): DCMC intelligence, gated by
    heard_dcmc_intelligence and iron_depths_investigation_accepted.
  - Yuki Tanaka (nova_research): NAS intelligence, gated by
    heard_nas_intelligence and cargo_lost_accepted.

The Fulcrum's scope is CONFIRMATION-ONLY. The Fulcrum is a one-time
narrative endpoint: before `point_of_no_return` the player cannot dock
there; after `the_collapse` the Expanse has collapsed. There is no
recurring between-beat visit state, so no depth-tier beat is authored
for the Fulcrum. Future SA-X cohesion sprints should not add a
recurring depth tier there without revisiting this constraint.
"""

from __future__ import annotations

import pygame
import pygame_gui
import pytest

from spacegame.constants.flags import heard_dcmc_intelligence, heard_nas_intelligence
from spacegame.data_loader import get_data_loader
from spacegame.models.dialogue import DialogueManager
from spacegame.models.journal import Journal
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.station_salience import is_system_mission_relevant
from spacegame.views.station_hub_view import StationHubView
from tests.test_scenarios._helpers import fresh_player, round_trip_save

# ---------------------------------------------------------------------------
# Module-level pygame init (StationHubView requires fonts + a UIManager)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """station_hub_view requires pygame fonts and a UIManager."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _real_locations(system_id: str) -> list:
    dl = get_data_loader()
    dl.load_all()
    return list(dl.locations.get(system_id, []))


def _real_system(system_id: str):
    dl = get_data_loader()
    dl.load_all()
    return dl.systems[system_id]


def _make_hub_view(player, system_id: str, mission_manager=None) -> StationHubView:
    """Construct a StationHubView with real data for the given system."""
    ui_mgr = pygame_gui.UIManager((1280, 800))
    locations = _real_locations(system_id)
    return StationHubView(
        ui_manager=ui_mgr,
        player=player,
        system=_real_system(system_id),
        locations=locations,
        activity_registry=None,
        data_loader=get_data_loader(),
        mission_manager=mission_manager,
    )


def _make_active_mission_manager(mission_id: str, system_id: str) -> MissionManager:
    """Return a MissionManager with one ACTIVE REACH_SYSTEM mission."""
    m = Mission(
        id=mission_id,
        name=mission_id,
        description="test mission",
        objectives=[
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id=system_id,
            )
        ],
    )
    mm = MissionManager([m])
    mm._status[mission_id] = MissionStatus.ACTIVE
    return mm


def _start_dialogue(tree_id: str, flags: dict[str, bool]) -> DialogueManager:
    """Return a DialogueManager with the given tree started and flags loaded."""
    dl = get_data_loader()
    dl.load_all()
    dm = DialogueManager()
    dm.load_flags(flags)
    dm.start_dialogue(dl.dialogue_trees[tree_id])
    return dm


def _unique_loc_ids(system_id: str) -> set[str]:
    """Return the IDs of all unique-typed locations in a system."""
    return {loc.id for loc in _real_locations(system_id) if loc.location_type == "unique"}


# ---------------------------------------------------------------------------
# SL-1 elevation: is_system_mission_relevant
# ---------------------------------------------------------------------------


_CLUSTER_A_TUPLES = [
    ("iron_depths", "iron_depths_restricted_zone", "iron_depths_investigation"),
    ("nova_research", "nova_restricted_labs", "cargo_lost"),
    ("the_fulcrum", "fulcrum_core", "point_of_no_return"),
]


class TestSL1MissionRelevance:
    """is_system_mission_relevant returns the correct value for all 3 anchors."""

    @pytest.mark.parametrize("system_id, anchor_id, mission_id", _CLUSTER_A_TUPLES)
    def test_relevant_when_mission_active(
        self, system_id: str, anchor_id: str, mission_id: str
    ) -> None:
        mm = _make_active_mission_manager(mission_id, system_id)
        result = is_system_mission_relevant(mm, system_id)
        assert result is True, (
            f"is_system_mission_relevant should be True for {system_id} when {mission_id} is active"
        )

    @pytest.mark.parametrize("system_id, anchor_id, mission_id", _CLUSTER_A_TUPLES)
    def test_not_relevant_when_no_missions(
        self, system_id: str, anchor_id: str, mission_id: str
    ) -> None:
        result = is_system_mission_relevant(None, system_id)
        assert result is False, (
            f"is_system_mission_relevant should be False for {system_id} "
            "when mission_manager is None"
        )


class TestSL1ElevationViaView:
    """Unique anchor cards elevate/demote correctly based on mission state."""

    @pytest.mark.parametrize("system_id, anchor_id, mission_id", _CLUSTER_A_TUPLES)
    def test_anchor_elevated_when_mission_active(
        self, system_id: str, anchor_id: str, mission_id: str
    ) -> None:
        """Anchor is in the elevated set (NOT in POI strip) when mission active."""
        player = fresh_player(system_id=system_id)
        mm = _make_active_mission_manager(mission_id, system_id)
        view = _make_hub_view(player, system_id, mission_manager=mm)
        elevated = view._compute_elevated_unique_ids()
        assert anchor_id in elevated, (
            f"{anchor_id} should be elevated at {system_id} when {mission_id} is active"
        )

    @pytest.mark.parametrize("system_id, anchor_id, mission_id", _CLUSTER_A_TUPLES)
    def test_anchor_demotes_when_no_mission(
        self, system_id: str, anchor_id: str, mission_id: str
    ) -> None:
        """Anchor demotes to the POI strip (not elevated) when no mission active."""
        player = fresh_player(system_id=system_id)
        view = _make_hub_view(player, system_id, mission_manager=None)
        elevated = view._compute_elevated_unique_ids()
        assert anchor_id not in elevated, (
            f"{anchor_id} should NOT be elevated at {system_id} when no mission is active"
        )


# ---------------------------------------------------------------------------
# DCMC depth-tier beat: Naveen Prakash at iron_depths
# ---------------------------------------------------------------------------


class TestDCMCDepthBeat:
    """Naveen Prakash's DCMC intelligence branch at iron_depths.

    Branch ID: dcmc_intelligence (entry point) + dcmc_intelligence_reveal (final node).
    Gate: excluded_flags = [heard_dcmc_intelligence, iron_depths_investigation_accepted].
    Flag set: heard_dcmc_intelligence on the final [Leave] response.
    """

    def test_dcmc_branch_offered_when_conditions_met(self) -> None:
        """Branch appears in greet responses when both gate flags are absent."""
        dm = _start_dialogue("naveen_prakash_dialogue", {})
        responses = dm.get_available_responses()
        leads_to_dcmc = [r for r in responses if r.next_node_id == "dcmc_intelligence"]
        assert leads_to_dcmc, (
            "A response leading to dcmc_intelligence should be offered "
            "when heard_dcmc_intelligence and iron_depths_investigation_accepted are absent"
        )

    def test_dcmc_branch_suppressed_when_already_heard(self) -> None:
        """Branch is hidden once heard_dcmc_intelligence is set."""
        dm = _start_dialogue(
            "naveen_prakash_dialogue",
            {heard_dcmc_intelligence(): True},
        )
        responses = dm.get_available_responses()
        leads_to_dcmc = [r for r in responses if r.next_node_id == "dcmc_intelligence"]
        assert not leads_to_dcmc, (
            "DCMC branch should be suppressed when heard_dcmc_intelligence is set"
        )

    def test_dcmc_branch_suppressed_when_mission_active(self) -> None:
        """Branch is hidden when iron_depths_investigation is active."""
        dm = _start_dialogue(
            "naveen_prakash_dialogue",
            {"iron_depths_investigation_accepted": True},
        )
        responses = dm.get_available_responses()
        leads_to_dcmc = [r for r in responses if r.next_node_id == "dcmc_intelligence"]
        assert not leads_to_dcmc, (
            "DCMC branch should be suppressed when iron_depths_investigation_accepted is set"
        )

    def test_dcmc_branch_sets_flag_on_completion(self) -> None:
        """Completing the DCMC branch sets heard_dcmc_intelligence exactly once."""
        dl = get_data_loader()
        dl.load_all()
        dm = DialogueManager()
        dm.load_flags({})
        dm.start_dialogue(dl.dialogue_trees["naveen_prakash_dialogue"])

        # Navigate: greet → dcmc_intelligence
        responses = dm.get_available_responses()
        dcmc_entry_idx = next(
            i for i, r in enumerate(responses) if r.next_node_id == "dcmc_intelligence"
        )
        dm.select_response(dcmc_entry_idx)

        # Now at dcmc_intelligence node — pick any response to advance
        dm.select_response(0)

        # Now at dcmc_intelligence_reveal — select [Leave] which sets the flag
        responses = dm.get_available_responses()
        leave_idx = next(i for i, r in enumerate(responses) if r.next_node_id is None)
        dm.select_response(leave_idx)

        assert dm.get_flag(heard_dcmc_intelligence()), (
            "heard_dcmc_intelligence should be set after completing the DCMC depth-tier beat"
        )

    def test_dcmc_branch_not_offered_after_flag_set(self) -> None:
        """After flag is set, starting a new session hides the branch."""
        dm = _start_dialogue(
            "naveen_prakash_dialogue",
            {heard_dcmc_intelligence(): True},
        )
        responses = dm.get_available_responses()
        leads_to_dcmc = [r for r in responses if r.next_node_id == "dcmc_intelligence"]
        assert not leads_to_dcmc, "Branch should not re-appear after heard_dcmc_intelligence is set"


# ---------------------------------------------------------------------------
# NAS depth-tier beat: Yuki Tanaka at nova_research
# ---------------------------------------------------------------------------


class TestNASDepthBeat:
    """Yuki Tanaka's NAS intelligence branch at nova_research.

    Branch ID: nas_intelligence (entry point) + nas_intelligence_reveal (final node).
    Gate: excluded_flags = [heard_nas_intelligence, cargo_lost_accepted, signal_mission_accepted].
    Flag set: heard_nas_intelligence on the final [Leave] response.
    """

    def test_nas_branch_offered_when_conditions_met(self) -> None:
        """Branch appears in start responses when all gate flags are absent."""
        dm = _start_dialogue("yuki_signal_deep", {})
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert leads_to_nas, (
            "A response leading to nas_intelligence should be offered "
            "when heard_nas_intelligence, cargo_lost_accepted, and signal_mission_accepted "
            "are all absent"
        )

    def test_nas_branch_suppressed_when_already_heard(self) -> None:
        """Branch is hidden once heard_nas_intelligence is set."""
        dm = _start_dialogue(
            "yuki_signal_deep",
            {heard_nas_intelligence(): True},
        )
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert not leads_to_nas, (
            "NAS branch should be suppressed when heard_nas_intelligence is set"
        )

    def test_nas_branch_suppressed_when_cargo_lost_active(self) -> None:
        """Branch is hidden when cargo_lost is active."""
        dm = _start_dialogue(
            "yuki_signal_deep",
            {"cargo_lost_accepted": True},
        )
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert not leads_to_nas, "NAS branch should be suppressed when cargo_lost_accepted is set"

    def test_nas_branch_suppressed_when_signal_mission_active(self) -> None:
        """Branch is hidden when the signal mission is already accepted."""
        dm = _start_dialogue(
            "yuki_signal_deep",
            {"signal_mission_accepted": True},
        )
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert not leads_to_nas, (
            "NAS branch should be suppressed when signal_mission_accepted is set"
        )

    def test_nas_branch_sets_flag_on_completion(self) -> None:
        """Completing the NAS branch sets heard_nas_intelligence exactly once."""
        dl = get_data_loader()
        dl.load_all()
        dm = DialogueManager()
        dm.load_flags({})
        dm.start_dialogue(dl.dialogue_trees["yuki_signal_deep"])

        # Navigate: start → nas_intelligence
        responses = dm.get_available_responses()
        nas_entry_idx = next(
            i for i, r in enumerate(responses) if r.next_node_id == "nas_intelligence"
        )
        dm.select_response(nas_entry_idx)

        # At nas_intelligence node — pick any response to advance
        dm.select_response(0)

        # At nas_intelligence_reveal — select [Leave] which sets the flag
        responses = dm.get_available_responses()
        leave_idx = next(i for i, r in enumerate(responses) if r.next_node_id is None)
        dm.select_response(leave_idx)

        assert dm.get_flag(heard_nas_intelligence()), (
            "heard_nas_intelligence should be set after completing the NAS depth-tier beat"
        )

    def test_nas_branch_not_offered_after_flag_set(self) -> None:
        """After flag is set, starting a new session hides the branch."""
        dm = _start_dialogue(
            "yuki_signal_deep",
            {heard_nas_intelligence(): True},
        )
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert not leads_to_nas, "Branch should not re-appear after heard_nas_intelligence is set"


# ---------------------------------------------------------------------------
# Journal trigger tests
# ---------------------------------------------------------------------------


class TestJournalTriggers:
    """New flags trigger the correct auto journal entries."""

    def _make_journal_with_templates(self) -> Journal:
        dl = get_data_loader()
        dl.load_all()
        return Journal(auto_templates=dl.journal_entries)

    def test_dcmc_flag_triggers_auto_dcmc_intelligence_entry(self) -> None:
        """Setting heard_dcmc_intelligence triggers auto_dcmc_intelligence in journal."""
        journal = self._make_journal_with_templates()
        entry = journal.trigger_auto_entry(
            heard_dcmc_intelligence(), game_day=5, system_id="iron_depths"
        )
        assert entry is not None, (
            "trigger_auto_entry should return a JournalEntry for heard_dcmc_intelligence"
        )
        assert entry.entry_id == "auto_dcmc_intelligence", (
            f"Expected entry_id 'auto_dcmc_intelligence', got '{entry.entry_id}'"
        )
        assert entry.system_id == "iron_depths"

    def test_nas_flag_triggers_auto_nas_intelligence_entry(self) -> None:
        """Setting heard_nas_intelligence triggers auto_nas_intelligence in journal."""
        journal = self._make_journal_with_templates()
        entry = journal.trigger_auto_entry(
            heard_nas_intelligence(), game_day=7, system_id="nova_research"
        )
        assert entry is not None, (
            "trigger_auto_entry should return a JournalEntry for heard_nas_intelligence"
        )
        assert entry.entry_id == "auto_nas_intelligence", (
            f"Expected entry_id 'auto_nas_intelligence', got '{entry.entry_id}'"
        )
        assert entry.system_id == "nova_research"

    def test_dcmc_journal_entry_fires_once_only(self) -> None:
        """Journal entry for heard_dcmc_intelligence fires only the first time."""
        journal = self._make_journal_with_templates()
        first = journal.trigger_auto_entry(
            heard_dcmc_intelligence(), game_day=5, system_id="iron_depths"
        )
        second = journal.trigger_auto_entry(
            heard_dcmc_intelligence(), game_day=6, system_id="iron_depths"
        )
        assert first is not None, "First trigger should return an entry"
        assert second is None, "Second trigger should return None (already triggered)"

    def test_nas_journal_entry_fires_once_only(self) -> None:
        """Journal entry for heard_nas_intelligence fires only the first time."""
        journal = self._make_journal_with_templates()
        first = journal.trigger_auto_entry(
            heard_nas_intelligence(), game_day=7, system_id="nova_research"
        )
        second = journal.trigger_auto_entry(
            heard_nas_intelligence(), game_day=8, system_id="nova_research"
        )
        assert first is not None
        assert second is None


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundTrip:
    """New flags and journal entries persist through the save/load cycle."""

    def test_dcmc_flag_persists_through_save_load(self) -> None:
        """heard_dcmc_intelligence survives serialization round-trip."""
        player = fresh_player()
        player.dialogue_flags[heard_dcmc_intelligence()] = True
        restored = round_trip_save(player)
        assert restored.dialogue_flags.get(heard_dcmc_intelligence()) is True, (
            "heard_dcmc_intelligence flag should persist through save/load"
        )

    def test_nas_flag_persists_through_save_load(self) -> None:
        """heard_nas_intelligence survives serialization round-trip."""
        player = fresh_player()
        player.dialogue_flags[heard_nas_intelligence()] = True
        restored = round_trip_save(player)
        assert restored.dialogue_flags.get(heard_nas_intelligence()) is True, (
            "heard_nas_intelligence flag should persist through save/load"
        )

    def test_journal_state_persists_through_save_load(self) -> None:
        """Journal entries triggered by the new flags survive serialization."""
        dl = get_data_loader()
        dl.load_all()
        player = fresh_player()
        journal = Journal(auto_templates=dl.journal_entries)

        # Trigger both entries
        player.dialogue_flags[heard_dcmc_intelligence()] = True
        player.dialogue_flags[heard_nas_intelligence()] = True
        journal.trigger_auto_entry(heard_dcmc_intelligence(), game_day=5, system_id="iron_depths")
        journal.trigger_auto_entry(heard_nas_intelligence(), game_day=7, system_id="nova_research")

        # Sync journal state into player before saving
        player.journal_state = journal.get_state()

        restored = round_trip_save(player)

        # Verify journal state contains the entries
        triggered = set(restored.journal_state.get("triggered_flags", []))
        assert heard_dcmc_intelligence() in triggered, (
            "heard_dcmc_intelligence should remain in journal triggered_flags after load"
        )
        assert heard_nas_intelligence() in triggered, (
            "heard_nas_intelligence should remain in journal triggered_flags after load"
        )

    def test_dcmc_branch_not_re_offered_after_load(self) -> None:
        """After save/load with flag set, DCMC branch is not offered."""
        player = fresh_player()
        player.dialogue_flags[heard_dcmc_intelligence()] = True
        restored = round_trip_save(player)

        # Simulate starting a new dialogue session with the restored flags
        dm = _start_dialogue(
            "naveen_prakash_dialogue",
            dict(restored.dialogue_flags),
        )
        responses = dm.get_available_responses()
        leads_to_dcmc = [r for r in responses if r.next_node_id == "dcmc_intelligence"]
        assert not leads_to_dcmc, (
            "DCMC branch should not re-appear after loading a save with the flag set"
        )

    def test_nas_branch_not_re_offered_after_load(self) -> None:
        """After save/load with flag set, NAS branch is not offered."""
        player = fresh_player()
        player.dialogue_flags[heard_nas_intelligence()] = True
        restored = round_trip_save(player)

        dm = _start_dialogue(
            "yuki_signal_deep",
            dict(restored.dialogue_flags),
        )
        responses = dm.get_available_responses()
        leads_to_nas = [r for r in responses if r.next_node_id == "nas_intelligence"]
        assert not leads_to_nas, (
            "NAS branch should not re-appear after loading a save with the flag set"
        )


# ---------------------------------------------------------------------------
# Fulcrum confirmation-only scope documentation
# ---------------------------------------------------------------------------


class TestFulcrumConfirmationOnly:
    """Documents and verifies The Fulcrum's confirmation-only scope.

    The Fulcrum is a one-time narrative endpoint. No depth-tier beat is
    authored there (SA-0 scope decision, locked). These tests confirm:
    1. The SL-1 elevation machinery works for the Fulcrum exactly as for
       the other two anchors.
    2. No new dialogue branches exist at The Fulcrum for SA-0 (the scope
       is intentionally limited to iron_depths and nova_research).
    """

    def test_fulcrum_elevation_works_with_point_of_no_return(self) -> None:
        """SL-1 elevates fulcrum_core when point_of_no_return is active."""
        mm = _make_active_mission_manager("point_of_no_return", "the_fulcrum")
        result = is_system_mission_relevant(mm, "the_fulcrum")
        assert result is True

    def test_fulcrum_demotes_without_mission(self) -> None:
        """fulcrum_core demotes to POI strip when no mission targets the Fulcrum."""
        result = is_system_mission_relevant(None, "the_fulcrum")
        assert result is False

    def test_fulcrum_has_no_depth_tier_dialogue_branch(self) -> None:
        """Confirms no dcmc_intelligence or nas_intelligence branches exist at the Fulcrum.

        The Fulcrum has no resident NPCs with depth-tier beats in SA-0.
        This is a deliberate scope decision: the Fulcrum is a narrative
        endpoint visited once, not a recurring anchorage.
        """
        dl = get_data_loader()
        dl.load_all()
        # The Fulcrum's NPCs do not have dcmc_intelligence or nas_intelligence
        # nodes in their dialogue trees. We confirm this by checking all
        # dialogue trees associated with Fulcrum NPCs.
        fulcrum_npcs = [npc for npc in dl.npcs.values() if npc.home_system_id == "the_fulcrum"]
        for npc in fulcrum_npcs:
            tree_id = npc.dialogue_id
            if tree_id not in dl.dialogue_trees:
                continue
            tree = dl.dialogue_trees[tree_id]
            assert "dcmc_intelligence" not in tree.nodes, (
                f"Fulcrum NPC {npc.id}'s tree '{tree_id}' should not have "
                "a dcmc_intelligence node (Fulcrum is confirmation-only in SA-0)"
            )
            assert "nas_intelligence" not in tree.nodes, (
                f"Fulcrum NPC {npc.id}'s tree '{tree_id}' should not have "
                "a nas_intelligence node (Fulcrum is confirmation-only in SA-0)"
            )
