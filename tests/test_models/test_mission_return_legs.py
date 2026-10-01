"""BB-6: a return leg counts only on the return, and counters count only after the accept."""

from __future__ import annotations

from spacegame.constants.flags import talked_to_npc
from spacegame.data_loader import DataLoader, get_data_loader
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.models.ship import Ship, ShipType


def _dl() -> DataLoader:
    dl = get_data_loader()
    dl.load_all()
    return dl


def _roomy_ship() -> Ship:
    ship_type = ShipType(
        id="test_hauler",
        name="Test Hauler",
        ship_class="light",
        description="A hold big enough for any contract.",
        cargo_capacity=1000,
        fuel_capacity=100,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )
    return Ship(ship_type=ship_type, current_fuel=100)


def _player(system_id: str) -> Player:
    return Player(name="TestCaptain", credits=5000, current_system_id=system_id, ship=_roomy_ship())


def _authored(mission_id: str) -> MissionManager:
    manager = MissionManager(_dl().missions)
    manager.load_state({"status": {mission_id: "available"}})
    return manager


def _land(manager: MissionManager, player: Player, system_id: str) -> list[str]:
    player.current_system_id = system_id
    return manager.check_objectives(player)


class TestAuthoredReturnLegs:
    def test_blight_season_completes_back_at_verdant(self) -> None:
        manager, player = _authored("blight_season"), _player("verdant")
        manager.accept_mission("blight_season", game_day=1, player=player)
        assert _land(manager, player, "verdant") == []
        assert _land(manager, player, "axiom_labs") == []
        assert _land(manager, player, "verdant") == ["blight_season"]

    def test_passing_home_before_the_errand_does_not_count(self) -> None:
        manager, player = _authored("blight_season"), _player("verdant")
        manager.accept_mission("blight_season", game_day=1, player=player)
        for system_id in ("verdant", "nexus_prime", "verdant", "axiom_labs"):
            assert _land(manager, player, system_id) == [], system_id
        assert _land(manager, player, "verdant") == ["blight_season"]

    def test_miners_plight_does_not_pay_where_the_medicine_is_bought(self) -> None:
        manager, player = _authored("miners_plight"), _player("breakstone")
        manager.accept_mission("miners_plight", game_day=1, player=player)
        player.dialogue_flags[talked_to_npc("britt_vasara")] = True
        assert _land(manager, player, "breakstone") == []
        player.ship.add_cargo("medical", 5, 0)
        assert _land(manager, player, "nexus_prime") == []
        assert _land(manager, player, "breakstone") == ["miners_plight"]

    def test_a_return_leg_met_at_the_accept_waits_for_a_departure(self) -> None:
        manager, player = _authored("miners_plight"), _player("breakstone")
        player.dialogue_flags[talked_to_npc("britt_vasara")] = True
        player.ship.add_cargo("medical", 5, 0)
        manager.accept_mission("miners_plight", game_day=1, player=player)
        assert _land(manager, player, "breakstone") == []
        assert manager.get_objective_progress("miners_plight")[2] is False
        assert _land(manager, player, "nexus_prime") == []
        assert _land(manager, player, "breakstone") == ["miners_plight"]

    def test_the_ten_return_legs_are_marked(self) -> None:
        marked = {
            (m.id, i)
            for m in _dl().missions
            for i, o in enumerate(m.objectives)
            if o.after_departure
        }
        assert marked == {
            ("blight_season", 2),
            ("miners_plight", 2),
            ("lab_rat", 2),
            ("the_lost_registry", 3),
            ("counterfeit_concerns", 2),
            ("wrenchs_request", 2),
            ("honor_among_thieves", 3),
            ("arna_04_the_buyer", 2),
            ("arna_05a_last_freight_out", 1),
            ("arna_05b_clean_pull", 2),
        }


def _synthetic(objectives: list[MissionObjective], ordered_final: bool = False) -> Mission:
    return Mission(
        id="test_contract",
        name="Test Contract",
        description="A test contract.",
        objectives=objectives,
        rewards=[MissionReward(reward_type="credits", amount=100)],
        mission_type="side",
        ordered_final=ordered_final,
    )


class TestCountersSinceTheAccept:
    def test_lifetime_wins_before_the_accept_do_not_count(self) -> None:
        mission = _synthetic(
            [MissionObjective(type=ObjectiveType.WIN_COMBAT, target_id="", target_quantity=1)]
        )
        manager, player = MissionManager([mission]), _player("nexus_prime")
        manager.update_availability()
        player.combats_won = 3
        manager.accept_mission("test_contract", game_day=1, player=player)
        assert manager.check_objectives(player) == []
        player.combats_won += 1
        assert manager.check_objectives(player) == ["test_contract"]

    def test_lifetime_trades_before_the_accept_do_not_count(self) -> None:
        mission = _synthetic(
            [MissionObjective(type=ObjectiveType.COMPLETE_TRADE, target_id="", target_quantity=1)]
        )
        manager, player = MissionManager([mission]), _player("nexus_prime")
        manager.update_availability()
        player.trades_completed = 3
        manager.accept_mission("test_contract", game_day=1, player=player)
        assert manager.check_objectives(player) == []
        player.trades_completed += 1
        assert manager.check_objectives(player) == ["test_contract"]

    def test_an_accept_without_a_player_reads_lifetime_counts(self) -> None:
        mission = _synthetic(
            [MissionObjective(type=ObjectiveType.COMPLETE_TRADE, target_id="", target_quantity=2)]
        )
        manager, player = MissionManager([mission]), _player("nexus_prime")
        manager.update_availability()
        manager.accept_mission("test_contract")
        player.trades_completed = 2
        assert manager.check_objectives(player) == ["test_contract"]


class TestOrderedFinalLeg:
    def _delivery(self) -> Mission:
        return _synthetic(
            [
                MissionObjective(
                    type=ObjectiveType.COLLECT_CARGO, target_id="food", target_quantity=3
                ),
                MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant"),
            ],
            ordered_final=True,
        )

    def test_an_empty_visit_then_a_purchase_does_not_complete(self) -> None:
        manager, player = MissionManager([self._delivery()]), _player("nexus_prime")
        manager.update_availability()
        manager.accept_mission("test_contract", game_day=1, player=player)
        assert _land(manager, player, "verdant") == []
        assert manager.get_objective_progress("test_contract") == [False, False]
        player.ship.add_cargo("food", 3, 0)
        assert _land(manager, player, "nexus_prime") == []
        assert _land(manager, player, "verdant") == ["test_contract"]


class TestRunStateIsSaved:
    def test_a_round_trip_keeps_the_accept_system_departure_and_baselines(self) -> None:
        manager, player = _authored("blight_season"), _player("verdant")
        player.combats_won = 2
        manager.accept_mission("blight_season", game_day=1, player=player)
        _land(manager, player, "axiom_labs")
        state = manager.get_state()
        assert state["accept_system"] == {"blight_season": "verdant"}
        assert state["departed"] == ["blight_season"]
        assert state["baselines"] == {"blight_season": {"combats_won": 2, "trades_completed": 0}}
        restored = MissionManager(_dl().missions)
        restored.load_state(state)
        assert restored.get_state() == state
        player.current_system_id = "verdant"
        assert restored.check_objectives(player) == ["blight_season"]

    def test_a_save_from_before_the_run_state_still_completes(self) -> None:
        manager, player = MissionManager(_dl().missions), _player("nexus_prime")
        manager.load_state(
            {
                "status": {"blight_season": "active"},
                "progress": {"blight_season": [True, False, False, False]},
            }
        )
        assert manager.check_objectives(player) == []
        assert _land(manager, player, "verdant") == ["blight_season"]

    def test_completion_forgets_the_run(self) -> None:
        manager, player = _authored("blight_season"), _player("verdant")
        manager.accept_mission("blight_season", game_day=1, player=player)
        _land(manager, player, "axiom_labs")
        _land(manager, player, "verdant")
        assert manager.get_status("blight_season") == MissionStatus.COMPLETED
        state = manager.get_state()
        assert "blight_season" not in state["accept_system"]
        assert "blight_season" not in state["departed"]


def _generator() -> ProceduralMissionGenerator:
    dl = _dl()
    return ProceduralMissionGenerator(dl.systems, dl.commodities, dl.enemy_templates, seed=7)


def _accept_contract(mission: Mission, player: Player) -> MissionManager:
    manager = MissionManager([])
    manager.add_mission(mission)
    manager.accept_mission(mission.id, game_day=1, player=player)
    for cargo in mission.on_accept_cargo:
        player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
    return manager


class TestBoardContracts:
    def test_a_bounty_pays_only_for_wins_after_the_accept_and_on_the_return(self) -> None:
        bounty = _generator().generate_bounty("nexus_prime", game_day=1)
        kills = bounty.objectives[0].target_quantity
        player = _player("nexus_prime")
        player.combats_won = 3
        manager = _accept_contract(bounty, player)
        assert manager.check_objectives(player) == []
        player.combats_won += kills
        assert _land(manager, player, "forgeworks") == []
        assert _land(manager, player, "nexus_prime") == [bounty.id]

    def test_a_survey_return_counts_only_after_every_target(self) -> None:
        survey = _generator().generate_survey("nexus_prime", game_day=1)
        *targets, _back = survey.objectives
        player = _player("nexus_prime")
        manager = _accept_contract(survey, player)
        assert _land(manager, player, targets[0].target_id) == []
        assert _land(manager, player, "nexus_prime") == []
        for target in targets[1:]:
            assert _land(manager, player, target.target_id) == []
        assert _land(manager, player, "nexus_prime") == [survey.id]

    def test_sold_smuggling_cargo_pays_nothing_at_the_destination(self) -> None:
        run = _generator().generate_smuggling("nexus_prime", game_day=1)
        player = _player("nexus_prime")
        manager = _accept_contract(run, player)
        cargo = run.on_accept_cargo[0]
        player.ship.remove_cargo(cargo.commodity_id, cargo.quantity)
        destination = run.objectives[-1].target_id
        assert _land(manager, player, destination) == []
        assert manager.get_status(run.id) == MissionStatus.ACTIVE

    def test_smuggling_with_part_of_the_cargo_stays_active_at_the_destination(self) -> None:
        run = _generator().generate_smuggling("nexus_prime", game_day=1)
        player = _player("nexus_prime")
        manager = _accept_contract(run, player)
        cargo = run.on_accept_cargo[0]
        player.ship.remove_cargo(cargo.commodity_id, 1)
        destination = run.objectives[-1].target_id
        assert _land(manager, player, destination) == []
        player.ship.add_cargo(cargo.commodity_id, 1, 0)
        assert manager.check_objectives(player) == [run.id]
