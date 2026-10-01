"""Story content fixes from the post-SP3 bug bash (plan A1, Task 7)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from spacegame.constants.flags import talked_to_npc
from spacegame.models.mission import MissionStatus
from spacegame.views.station_hub_view import StationHubView
from tests.test_models.test_mission_return_legs import _dl, _player
from tests.test_models.test_mission_talk_rules import _manager

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _listed(npc_id: str, flags: dict[str, bool]) -> bool:
    view = StationHubView.__new__(StationHubView)
    view.player = SimpleNamespace(dialogue_flags=flags)
    return view._is_npc_available(_dl().npcs[npc_id])


def _texts(tree_id: str) -> list[str]:
    tree = _dl().dialogue_trees[tree_id]
    out: list[str] = []
    for node in tree.nodes.values():
        out.append(node.text)
        out += [r.text for r in node.responses]
    return out


class TestContractCargoStaysAboard:
    """BB-7: an authored delivery pays only with its cargo aboard."""

    def test_the_crimson_run_waits_for_the_chip(self) -> None:
        manager, player = _manager(the_crimson_run="available"), _player("nexus_prime")
        manager.accept_mission("the_crimson_run", game_day=1, player=player)
        player.current_system_id = "crimson_reach"
        player.dialogue_flags.update(
            {"crimson_run_ground_complete": True, "met_malia_torres": True}
        )
        assert manager.check_objectives(player) == []
        player.ship.add_cargo("data_chip", 1, 0)
        assert manager.check_objectives(player) == ["the_crimson_run"]

    def test_the_price_of_information_waits_for_the_chip(self) -> None:
        manager, player = _manager(the_price_of_information="available"), _player("nexus_prime")
        player.dialogue_flags[talked_to_npc("neve_osei")] = True
        manager.accept_mission("the_price_of_information", game_day=1, player=player)
        player.current_system_id = "stellaris_port"
        assert manager.check_objectives(player) == []
        player.ship.add_cargo("sealed_audit_chip", 1, 0)
        assert manager.check_objectives(player) == ["the_price_of_information"]

    def test_a_lost_fight_does_not_strand_the_crimson_run(self) -> None:
        manager, player = _manager(the_crimson_run="available"), _player("nexus_prime")
        manager.accept_mission("the_crimson_run", game_day=1, player=player)
        player.ship.add_cargo("data_chip", 1, 0)
        player.apply_combat_defeat("crimson_reach")
        player.dialogue_flags.update(
            {"crimson_run_ground_complete": True, "met_malia_torres": True}
        )
        assert player.ship.get_cargo_quantity("data_chip") == 1
        assert manager.check_objectives(player) == ["the_crimson_run"]

    def test_a_lost_fight_does_not_strand_the_price_of_information(self) -> None:
        manager, player = _manager(the_price_of_information="available"), _player("nexus_prime")
        player.dialogue_flags[talked_to_npc("neve_osei")] = True
        manager.accept_mission("the_price_of_information", game_day=1, player=player)
        player.ship.add_cargo("sealed_audit_chip", 1, 0)
        player.apply_combat_defeat("stellaris_port")
        assert player.ship.get_cargo_quantity("sealed_audit_chip") == 1
        assert manager.check_objectives(player) == ["the_price_of_information"]


class TestCoolantRun:
    """BB-15: the pallet fits the shuttle, and Rhea signs only for a pallet that is aboard."""

    def test_a_sold_pallet_and_a_chat_with_rhea_do_not_complete_the_run(self) -> None:
        manager, player = _manager(coolant_run="available"), _player("nexus_prime")
        manager.accept_mission("coolant_run", game_day=1, player=player)
        player.current_system_id = "verdant"
        manager.record_conversation("rhea")
        player.dialogue_flags["arna_delivery_resolved"] = True
        assert manager.check_objectives(player) == []
        player.ship.add_cargo("machinery", 4, 0)
        assert manager.check_objectives(player) == []
        manager.record_conversation("rhea")
        assert manager.check_objectives(player) == ["coolant_run"]

    def test_the_lines_name_four_units_of_machinery(self) -> None:
        dl = _dl()
        texts = " ".join(_texts("rhea_receives_coolant"))
        assert "coolant" not in texts
        subtexts = [n.subtext for n in dl.dialogue_trees["arna_first_encounter"].nodes.values()]
        assert any("Four units" in s for s in subtexts)
        assert "coolant" not in dl.dialogue_trees["arna_post_completion"].nodes["ore_pitch"].text
        # Read the raw file: DataLoader._parse_mission does not load discovery_text.
        raw = json.loads((DATA_DIR / "missions" / "side_missions.json").read_text(encoding="utf-8"))
        ore_tip = next(m for m in raw["missions"] if m["id"] == "arna_02_ore_tip")
        assert "coolant" not in ore_tip["discovery_text"]


class TestHeldBack:
    """BB-17: Two Calls and The Silent Shaft wait for SP10."""

    def test_two_calls_is_not_offered_after_cargo_lost(self) -> None:
        manager = _manager(cargo_lost="completed")
        manager.update_availability({})
        assert manager.get_status("two_calls") == MissionStatus.UNAVAILABLE

    def test_the_silent_shaft_is_not_offered(self) -> None:
        manager = _manager(the_foremans_son="completed")
        manager.update_availability({"learned_father_story": True})
        assert manager.get_status("the_silent_shaft") == MissionStatus.UNAVAILABLE


class TestDeliveredGoodsLeaveTheHold:
    """BB-31."""

    def test_miners_plight_takes_the_medicine(self) -> None:
        player = _player("breakstone")
        player.ship.add_cargo("medical", 5, 0)
        _manager().apply_rewards("miners_plight", player)
        assert player.ship.get_cargo_quantity("medical") == 0

    def test_wrenchs_request_takes_the_parts(self) -> None:
        player = _player("crimson_reach")
        player.ship.add_cargo("rare_parts", 3, 0)
        _manager().apply_rewards("wrenchs_request", player)
        assert player.ship.get_cargo_quantity("rare_parts") == 0


class TestEncounterMissionsFollowTheirEncounter:
    """BB-83: The Stowaway and Adrift appear with their encounter."""

    def test_adrift_waits_for_the_pod(self) -> None:
        manager = _manager(cargo_lost="completed")
        manager.update_availability({})
        assert manager.get_status("adrift") == MissionStatus.UNAVAILABLE

    def test_a_rescue_completes_adrift_at_once(self) -> None:
        manager, player = _manager(cargo_lost="completed"), _player("nova_research")
        player.dialogue_flags.update({"adrift_survivor_found": True, "adrift_resolved": True})
        manager.update_availability(player.dialogue_flags, game_day=5, player=player)
        # The availability pass may accept other missions, so check this one by name.
        assert "adrift" in manager.check_objectives(player)
        manager.complete_mission("adrift", player)
        assert player.credits == 5000 + 250

    # Logging the pod's coordinates sets no flag, so test_adrift_waits_for_the_pod covers
    # it: that choice never offers Adrift.

    def test_the_stowaway_waits_for_the_stowaway(self) -> None:
        manager = _manager(recruit_navigator="completed")
        manager.update_availability({})
        assert manager.get_status("the_stowaway") == MissionStatus.UNAVAILABLE


class TestTalkListGates:
    """BB-84 and BB-32: givers wait for their jobs; Torres goes when her request is done."""

    def test_mossa_waits_for_the_board_accept(self) -> None:
        assert not _listed("dock_investigator", {})
        manager, player = _manager(the_dead_ledger="available"), _player("nexus_prime")
        manager.accept_mission("the_dead_ledger", game_day=1, player=player)
        assert _listed("dock_investigator", player.dialogue_flags)

    def test_the_other_givers_wait_for_their_missions(self) -> None:
        assert not _listed("callum_rhee", {})
        assert _listed("callum_rhee", {"drifters_deal_complete": True})
        assert not _listed("pirate_captain", {})
        assert _listed("pirate_captain", {"crimson_run_complete": True})
        assert not _listed("nova_researcher", {})
        assert _listed("nova_researcher", {"embassy_complete": True})

    def test_the_two_campaign_rewards_set_the_gates(self) -> None:
        dl = _dl()
        rewards = {
            m.id: {r.target_id for r in m.rewards if r.reward_type == "set_flag"}
            for m in dl.missions
        }
        assert "crimson_run_complete" in rewards["the_crimson_run"]
        assert "drifters_deal_complete" in rewards["the_drifters_deal"]

    def test_torres_hides_after_her_request(self) -> None:
        flags = {"met_malia_torres": True, "wrench_request_complete": True}
        assert not _listed("torres_memorial", flags)


class TestNamesAndPlaces:
    """BB-60."""

    def test_one_amara_okonkwo(self) -> None:
        names = [npc.name for npc in _dl().npcs.values()]
        assert names.count("Dr. Amara Okonkwo") == 1
        assert "Dr. Teodora Rautio-Mensah" in names

    def test_havens_rest_is_spelled_right_everywhere(self) -> None:
        for path in DATA_DIR.rglob("*.json"):
            assert "Havens Rest" not in path.read_text(encoding="utf-8"), path


class TestLinesMatchTheGame:
    """BB-36, BB-101, BB-92: lines promise only what the game does."""

    def test_the_forgery_promises_no_money_it_does_not_move(self) -> None:
        texts = " ".join(_texts("cassiel_maren_forgery"))
        assert "Double the fee" not in texts
        assert "pay me double" not in texts
        assert "Keep your credits" not in texts
        caught = _dl().dialogue_trees["cassiel_maren_forgery"].nodes["caught"]
        assert caught.responses[0].faction_reputation_changes == [{"commerce_guild": 3}]

    def test_the_inspector_names_no_sum(self) -> None:
        texts = " ".join(_texts("marcus_inspector_dialogue"))
        assert "2000" not in texts and "Two thousand" not in texts

    def test_quoted_fares_match_the_pay(self) -> None:
        assert "350 credits" in " ".join(_texts("priya_stranded"))
        callum = " ".join(_texts("callum_rhee_informant"))
        assert "350 credits" in callum and "200 credits" not in callum

    def test_odom_names_real_places_and_goods(self) -> None:
        # Only the route tip: "the coolant run I fronted her" elsewhere names Arna's job.
        # Weapons components are restricted, not illegal. The papers clause stays: Task 14
        # makes the Union's permit Hanna's alone to give (BB-74).
        tip = _dl().dialogue_trees["merchant_delivery"].nodes["teach_routes"].text
        for word in ("Concord", "Fringe", "coolant", "grain", "never legally"):
            assert word not in tip, word
        assert "Don't ask about Union until you have papers." in tip

    def test_priya_points_at_the_job_not_at_herself(self) -> None:
        decline = _dl().dialogue_trees["priya_stranded"].nodes["decline"].text
        for promise in ("hours", "I will be here", "find me here"):
            assert promise not in decline, promise
        assert "board" in decline

    def test_larsen_names_safe_lanes(self) -> None:
        advice = _dl().dialogue_trees["larsen_customs"].nodes["advice"].text
        assert "Forgeworks" not in advice and "Verdant" in advice

    def test_recruit_navigator_says_where_elena_waits(self) -> None:
        mission = next(m for m in _dl().missions if m.id == "recruit_navigator")
        assert "Stellaris Port" in mission.description and "Stellaris Port" in mission.hint

    def test_miners_plight_offers_what_its_giver_offers(self) -> None:
        mission = next(m for m in _dl().missions if m.id == "miners_plight")
        assert "report the request" not in mission.description
