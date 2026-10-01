"""BB-19: the flags content sets, which the side-mission auto-resolve must leave alone."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.flag_producers import content_flag_producers
from spacegame.models.mission import MissionManager, ObjectiveType


def _produced() -> frozenset[str]:
    dl = get_data_loader()
    dl.load_all()
    return content_flag_producers(
        dl.dialogue_trees.values(), dl.encounter_definitions, dl.npcs.values()
    )


class TestContentFlagProducers:
    def test_dialogue_encounter_and_npc_flags_are_produced(self) -> None:
        produced = _produced()
        for flag in (
            "forgery_appraised",  # a dialogue response
            "read_elena_navigator",  # a dialogue check's success flag
            "stowaway_discovered",  # an encounter outcome reward
            "met_dex_halloran",  # an NPC gate flag
        ):
            assert flag in produced, flag

    def test_flags_only_the_auto_resolve_sets_are_not(self) -> None:
        produced = _produced()
        for flag in ("blight_season_resolved", "pesticide_acquired", "fulcrum_ground_complete"):
            assert flag not in produced, flag


# The side missions whose has_flag objectives the auto-resolve stops setting, because some
# content produces them. Reviewed with plan A1; a change to this list is a design change.
NO_LONGER_AUTO_SET = {
    "the_scholars_dilemma": ["scholar_data_received"],
    "lab_rat": ["lab_rat_accepted"],
    "the_lost_registry": ["registry_search_started"],
    "the_forgery": ["forgery_appraised", "forgery_resolved"],
    "wrenchs_request": ["wrench_request_accepted"],
    "honor_among_thieves": ["thieves_job_accepted"],
    "signal_from_the_deep": ["signal_mission_accepted"],
    "coolant_run": ["arna_delivery_resolved"],
    "arna_05c_clean_paper": ["arna_betrayal_resolved"],
    "arna_03_refinement": ["tev_refining_complete"],
}


def test_the_auto_resolve_leaves_produced_flags_to_their_scenes() -> None:
    dl = get_data_loader()
    dl.load_all()
    manager = MissionManager(dl.missions, produced_flags=_produced())
    found: dict[str, list[str]] = {}
    for mission in dl.missions:
        if mission.mission_type != "side":
            continue
        if all(o.type == ObjectiveType.HAS_FLAG for o in mission.objectives):
            continue
        kept = [
            o.target_id
            for o in mission.objectives
            if o.type == ObjectiveType.HAS_FLAG
            and not manager._auto_resolvable(mission.id, o.target_id)
        ]
        if kept:
            found[mission.id] = kept
    assert found == NO_LONGER_AUTO_SET
