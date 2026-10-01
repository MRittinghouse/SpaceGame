"""BB-19: talk objectives after the first count only conversations after the accept."""

from __future__ import annotations

import pytest

from spacegame.constants.flags import talked_to_npc
from spacegame.models.flag_producers import content_flag_producers
from spacegame.models.mission import MissionManager, MissionStatus
from tests.test_models.test_mission_return_legs import _dl, _player


def _manager(**statuses: str) -> MissionManager:
    dl = _dl()
    manager = MissionManager(
        dl.missions,
        produced_flags=content_flag_producers(
            dl.dialogue_trees.values(), dl.encounter_definitions, dl.npcs.values()
        ),
    )
    manager.load_state({"status": dict(statuses)})
    return manager


class TestTalkAfterAccept:
    def test_a_clerk_chat_before_the_job_does_not_deliver_the_ore(self) -> None:
        manager, player = _manager(bill_of_landing="completed"), _player("nexus_prime")
        player.dialogue_flags[talked_to_npc("forgeworks_clerk")] = True
        player.dialogue_flags["talked_to_cargo_broker"] = True
        manager.update_availability(player.dialogue_flags, game_day=1, player=player)
        assert manager.get_status("iron_delivery") == MissionStatus.ACTIVE
        player.ship.add_cargo("iron_ore", 10, 0)
        # The availability pass may accept other missions, so check this one by name.
        assert "iron_delivery" not in manager.check_objectives(player)
        manager.record_conversation("forgeworks_clerk")
        assert "iron_delivery" in manager.check_objectives(player)

    def test_a_chat_with_arna_before_the_run_does_not_count(self) -> None:
        manager, player = _manager(arna_02_ore_tip="available"), _player("nexus_prime")
        player.dialogue_flags[talked_to_npc("arna")] = True
        manager.accept_mission("arna_02_ore_tip", game_day=1, player=player)
        manager.record_conversation("arna")
        assert manager.check_objectives(player) == []
        player.current_system_id = "breakstone"
        player.ship.add_cargo("rare_metals", 5, 0)
        assert manager.check_objectives(player) == []
        player.current_system_id = "nexus_prime"
        assert manager.check_objectives(player) == []
        manager.record_conversation("arna")
        assert manager.check_objectives(player) == ["arna_02_ore_tip"]

    def test_the_giver_of_a_first_talk_objective_still_counts_at_once(self) -> None:
        manager, player = _manager(the_forgery="available"), _player("stellaris_port")
        player.dialogue_flags[talked_to_npc("cassiel_maren")] = True
        manager.accept_mission("the_forgery", game_day=1, player=player)
        manager.check_objectives(player)
        assert manager.get_objective_progress("the_forgery")[0] is True

    def test_the_forgery_waits_for_its_confrontation(self) -> None:
        manager, player = _manager(the_forgery="available"), _player("stellaris_port")
        player.dialogue_flags[talked_to_npc("cassiel_maren")] = True
        manager.accept_mission("the_forgery", game_day=1, player=player)
        assert manager.check_objectives(player) == []
        player.dialogue_flags["forgery_appraised"] = True
        assert manager.check_objectives(player) == []
        player.dialogue_flags["forgery_resolved"] = True
        assert manager.check_objectives(player) == ["the_forgery"]

    def test_clean_paper_waits_for_the_followthrough_scene(self) -> None:
        manager, player = _manager(arna_05c_clean_paper="available"), _player("nexus_prime")
        player.dialogue_flags[talked_to_npc("arna")] = True  # the accepting conversation
        manager.accept_mission("arna_05c_clean_paper", game_day=1, player=player)
        assert manager.check_objectives(player) == []
        assert not player.dialogue_flags.get("arna_betrayal_resolved", False)
        manager.record_conversation("arna")
        player.dialogue_flags["arna_betrayal_resolved"] = True
        assert manager.check_objectives(player) == ["arna_05c_clean_paper"]

    def test_a_second_run_starts_with_no_departure(self) -> None:
        manager, player = _manager(miners_plight="available"), _player("breakstone")
        player.dialogue_flags[talked_to_npc("britt_vasara")] = True
        manager.accept_mission("miners_plight", game_day=1, player=player)
        player.current_system_id = "nexus_prime"
        manager.check_objectives(player)
        assert "miners_plight" in manager.get_state()["departed"]
        manager.abandon_mission("miners_plight")
        manager._status["miners_plight"] = MissionStatus.AVAILABLE
        player.current_system_id = "breakstone"
        manager.accept_mission("miners_plight", game_day=2, player=player)
        player.ship.add_cargo("medical", 5, 0)
        assert manager.check_objectives(player) == []
        assert "miners_plight" not in manager.get_state()["departed"]

    def test_a_second_run_starts_with_no_conversation(self) -> None:
        manager, player = _manager(arna_02_ore_tip="available"), _player("nexus_prime")
        manager.accept_mission("arna_02_ore_tip", game_day=1, player=player)
        manager.record_conversation("arna")
        assert manager.get_state()["talked_since_accept"] == {"arna_02_ore_tip": ["arna"]}
        manager.abandon_mission("arna_02_ore_tip")
        manager._status["arna_02_ore_tip"] = MissionStatus.AVAILABLE
        manager.accept_mission("arna_02_ore_tip", game_day=2, player=player)
        assert "arna_02_ore_tip" not in manager.get_state()["talked_since_accept"]

    def test_a_conversation_is_noted_only_for_a_mission_that_awaits_it(self) -> None:
        manager = _manager(miners_plight="available", arna_02_ore_tip="available")
        player = _player("breakstone")
        player.dialogue_flags[talked_to_npc("britt_vasara")] = True
        manager.accept_mission("miners_plight", game_day=1, player=player)
        manager.accept_mission("arna_02_ore_tip", game_day=1, player=player)
        # miners_plight's only talk objective is its first, which reads the sticky flag.
        manager.record_conversation("britt_vasara")
        manager.record_conversation("arna")
        assert manager.get_state()["talked_since_accept"] == {"arna_02_ore_tip": ["arna"]}

    def test_conversations_since_accept_survive_a_save(self) -> None:
        manager, player = _manager(arna_02_ore_tip="available"), _player("nexus_prime")
        manager.accept_mission("arna_02_ore_tip", game_day=1, player=player)
        player.current_system_id = "breakstone"
        player.ship.add_cargo("rare_metals", 5, 0)
        manager.check_objectives(player)
        manager.record_conversation("arna")
        state = manager.get_state()
        assert state["talked_since_accept"] == {"arna_02_ore_tip": ["arna"]}
        restored = _manager()
        restored.load_state(state)
        assert restored.get_state() == state


class TestArnaPendingStates:
    COMMON = {
        "arna_delivery_accepted": True,
        "arna_delivery_complete": True,
        "arna_accepted_ore_tip": True,
        "arna_ore_delivered": True,
        "arna_sent_to_tev": True,
    }

    @pytest.mark.parametrize(
        "extra,tree_id",
        [
            ({}, "arna_refining_pending"),
            (
                {"tev_refining_complete": True, "arna_arranging_buyer": True},
                "arna_buyer_pending",
            ),
            (
                {
                    "tev_refining_complete": True,
                    "arna_arranging_buyer": True,
                    "keren_ambush_triggered": True,
                    "arna_branch_payback": True,
                },
                "arna_payback_pending",
            ),
            (
                {
                    "tev_refining_complete": True,
                    "arna_arranging_buyer": True,
                    "keren_ambush_triggered": True,
                    "arna_branch_walkaway": True,
                },
                "arna_walkaway_pending",
            ),
        ],
    )
    def test_each_job_window_opens_its_own_tree(self, extra: dict, tree_id: str) -> None:
        dl = _dl()
        flags = {**self.COMMON, **extra}
        assert dl.npcs["arna"].get_active_dialogue_id(flags) == tree_id
        tree = dl.dialogue_trees[tree_id]
        responses = tree.get_start_node().responses
        assert [r.text for r in responses] == ["[Leave]"]

    def test_a_finished_payback_still_opens_the_post_payback_scene(self) -> None:
        flags = {
            **self.COMMON,
            "tev_refining_complete": True,
            "arna_arranging_buyer": True,
            "keren_ambush_triggered": True,
            "arna_branch_payback": True,
            "arna_branch_a_complete": True,
        }
        assert _dl().npcs["arna"].get_active_dialogue_id(flags) == "arna_post_payback"

    @pytest.mark.parametrize(
        "tree_id", ["arna_ore_tip_pending", "arna_payback_pending", "arna_walkaway_pending"]
    )
    def test_a_pending_line_reads_true_to_a_captain_back_from_the_job(self, tree_id: str) -> None:
        """The conversation that completes arna_02, 05a, or 05b opens this tree (ruling)."""
        text = _dl().dialogue_trees[tree_id].get_start_node().text
        assert "If not" in text, text
        for sending in ("get back", "come back", "Take what"):
            assert sending not in text, (tree_id, sending)
