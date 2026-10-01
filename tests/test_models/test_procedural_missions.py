"""Tests for R4.3 procedural mission generation.

Verifies the ProceduralMissionGenerator creates valid missions of each
template type, and that MissionManager.add_mission() correctly integrates
generated missions into the lifecycle.
"""

import random

from spacegame.data_loader import get_data_loader
from spacegame.models.commodity import Legality
from spacegame.models.market import Market
from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
    ObjectiveType,
)
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from spacegame.models.player import Player
from spacegame.models.ship import Ship


def _make_player(system_id: str = "nexus_prime") -> Player:
    """Create a test player at the given system."""
    dl = get_data_loader()
    ship_type = dl.ship_types["shuttle"]
    ship = Ship(ship_type=ship_type, current_fuel=ship_type.fuel_capacity)
    return Player("TestPilot", 5000, system_id, ship)


class TestMissionManagerAddMission:
    """Test the add_mission() method on MissionManager."""

    def test_add_mission_registers_it(self) -> None:
        """Added mission appears in the manager."""
        mgr = MissionManager([])
        mission = Mission(
            id="test_proc_1",
            name="Test Mission",
            description="A test",
            objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="nexus_prime")],
            rewards=[MissionReward(reward_type="credits", amount=100)],
        )
        mgr.add_mission(mission)
        assert mgr.get_mission("test_proc_1") is not None

    def test_add_mission_starts_available(self) -> None:
        """Added mission defaults to AVAILABLE status."""
        mgr = MissionManager([])
        mission = Mission(
            id="test_proc_2",
            name="Test",
            description="Test",
            objectives=[],
            rewards=[],
        )
        mgr.add_mission(mission)
        available = mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        assert any(m.id == "test_proc_2" for m in available)

    def test_add_mission_with_custom_status(self) -> None:
        """Added mission can be set to a custom initial status."""
        mgr = MissionManager([])
        mission = Mission(id="test_proc_3", name="T", description="T", objectives=[], rewards=[])
        mgr.add_mission(mission, initial_status=MissionStatus.UNAVAILABLE)
        assert mgr.get_mission("test_proc_3") is not None
        available = mgr.get_missions_by_status(MissionStatus.AVAILABLE)
        assert not any(m.id == "test_proc_3" for m in available)

    def test_add_duplicate_mission_fails(self) -> None:
        """Cannot add a mission with an ID that already exists."""
        mgr = MissionManager([])
        m1 = Mission(id="dup", name="A", description="A", objectives=[], rewards=[])
        m2 = Mission(id="dup", name="B", description="B", objectives=[], rewards=[])
        mgr.add_mission(m1)
        success, msg = mgr.add_mission(m2)
        assert not success
        assert "already exists" in msg.lower()

    def test_added_mission_can_be_accepted(self) -> None:
        """A dynamically added mission can be accepted normally."""
        mgr = MissionManager([])
        mission = Mission(
            id="proc_accept",
            name="Proc",
            description="Proc",
            objectives=[MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="verdant")],
            rewards=[MissionReward(reward_type="credits", amount=200)],
        )
        mgr.add_mission(mission)
        success, msg = mgr.accept_mission("proc_accept")
        assert success, msg

    def test_added_mission_objectives_track(self) -> None:
        """Objectives on a dynamically added mission are tracked."""
        mgr = MissionManager([])
        mission = Mission(
            id="proc_track",
            name="Track",
            description="Track",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="nexus_prime",
                    description="Go to Nexus",
                )
            ],
            rewards=[MissionReward(reward_type="credits", amount=100)],
        )
        mgr.add_mission(mission)
        mgr.accept_mission("proc_track")
        player = _make_player("nexus_prime")
        completed = mgr.check_objectives(player)
        assert "proc_track" in completed

    def test_added_mission_persists_in_state(self) -> None:
        """get_state() includes dynamically added missions."""
        mgr = MissionManager([])
        mission = Mission(id="proc_save", name="S", description="S", objectives=[], rewards=[])
        mgr.add_mission(mission)
        state = mgr.get_state()
        assert "proc_save" in state["status"]


class TestProceduralMissionGenerator:
    """Test the ProceduralMissionGenerator model."""

    def _make_generator(self, seed: int = 42) -> ProceduralMissionGenerator:
        dl = get_data_loader()
        return ProceduralMissionGenerator(
            systems=dl.systems,
            commodities=dl.commodities,
            enemy_templates=dl.enemy_templates,
            seed=seed,
        )

    def test_generate_bounty(self) -> None:
        """Bounty mission has WIN_COMBAT + REACH_SYSTEM objectives."""
        gen = self._make_generator()
        mission = gen.generate_bounty("crimson_reach", game_day=10)
        assert mission.mission_type == "side"
        assert mission.discovery_method == "station_board"
        obj_types = {o.type for o in mission.objectives}
        assert ObjectiveType.WIN_COMBAT in obj_types
        assert ObjectiveType.REACH_SYSTEM in obj_types
        assert any(r.reward_type == "credits" for r in mission.rewards)

    def test_generate_delivery(self) -> None:
        """Delivery mission has COLLECT_CARGO + REACH_SYSTEM objectives."""
        gen = self._make_generator()
        mission = gen.generate_delivery("nexus_prime", game_day=10)
        obj_types = {o.type for o in mission.objectives}
        assert ObjectiveType.COLLECT_CARGO in obj_types
        assert ObjectiveType.REACH_SYSTEM in obj_types
        assert mission.discovery_method == "station_board"

    def test_generate_smuggling(self) -> None:
        """Smuggling holds its cargo, then reaches the destination, in that order (BB-7)."""
        gen = self._make_generator()
        mission = gen.generate_smuggling("crimson_reach", game_day=10)
        assert len(mission.on_accept_cargo) == 1, "Smuggling mission should grant cargo"
        cargo = mission.on_accept_cargo[0]
        collect, reach = mission.objectives
        assert collect.type == ObjectiveType.COLLECT_CARGO
        assert (collect.target_id, collect.target_quantity) == (cargo.commodity_id, cargo.quantity)
        assert reach.type == ObjectiveType.REACH_SYSTEM
        assert mission.ordered_final
        assert "\u2014" not in mission.description

    def test_return_legs_wait_for_departure(self) -> None:
        gen = self._make_generator()
        for mission in (
            gen.generate_bounty("nexus_prime", game_day=3),
            gen.generate_survey("nexus_prime", game_day=3),
            gen.generate_salvage("nexus_prime", game_day=3),
        ):
            *earlier, back = mission.objectives
            assert back.after_departure, mission.id
            assert not any(o.after_departure for o in earlier), mission.id
            assert not mission.ordered_final, mission.id

    def test_a_delivery_orders_its_destination_after_the_goods(self) -> None:
        mission = self._make_generator().generate_delivery("nexus_prime", game_day=3)
        assert mission is not None
        assert mission.ordered_final
        assert not any(o.after_departure for o in mission.objectives)

    def test_a_one_kill_bounty_reads_singular(self) -> None:
        gen = self._make_generator()
        names = {}
        for day in range(1, 60):
            bounty = gen.generate_bounty("nexus_prime", game_day=day)
            names[bounty.objectives[0].target_quantity] = bounty.name
        assert names[1] == "Bounty: Clear 1 Hostile"
        assert names[2] == "Bounty: Clear 2 Hostiles"

    def _deliveries(self):
        gen = self._make_generator()
        for system_id in get_data_loader().systems:
            for day in range(1, 31):
                mission = gen.generate_delivery(system_id, game_day=day)
                if mission is not None:
                    yield system_id, day, mission

    def test_a_delivery_carries_a_legal_export_of_its_origin(self) -> None:
        dl = get_data_loader()
        for system_id, _day, mission in self._deliveries():
            good = mission.objectives[0].target_id
            assert good in (dl.systems[system_id].economy.specialty_exports or []), mission.id
            assert dl.commodities[good].legality == Legality.LEGAL, mission.id

    def test_an_origin_without_a_legal_export_posts_no_delivery(self) -> None:
        gen = self._make_generator()
        for system_id in ("the_fulcrum", "herons_mark"):
            for day in range(1, 61):
                assert gen.generate_delivery(system_id, game_day=day) is None
                board = gen.generate_for_system(system_id, game_day=day)
                assert not [m for m in board if m.id.startswith("proc_delivery_")]

    def test_a_delivery_fits_a_starting_hold_and_pays_the_goods_base_value(self) -> None:
        dl = get_data_loader()
        mults = {"safe": 1.0, "moderate": 1.5, "dangerous": 2.0}
        for system_id, _day, mission in self._deliveries():
            good = dl.commodities[mission.objectives[0].target_id]
            qty = mission.objectives[0].target_quantity
            assert qty * good.volume_per_unit <= 50, mission.id
            pay = int(int(good.base_price * qty * 1.0) * mults[dl.systems[system_id].danger_level])
            credits = next(r.amount for r in mission.rewards if r.reward_type == "credits")
            assert credits == max(pay, 150), mission.id
            hand_over = next(r for r in mission.rewards if r.reward_type == "deliver_cargo")
            assert (hand_over.target_id, hand_over.amount) == (good.id, qty)

    def test_no_delivery_pays_less_than_its_goods_cost_at_the_origin(self) -> None:
        dl = get_data_loader()
        commodities = list(dl.commodities.values())
        for system_id, day, mission in self._deliveries():
            market = Market(dl.systems[system_id], commodities, game_day=day)
            good, qty = mission.objectives[0].target_id, mission.objectives[0].target_quantity
            credits = next(r.amount for r in mission.rewards if r.reward_type == "credits")
            assert credits >= market.get_price(good) * qty, mission.id

    def test_nexus_primes_first_contract_keeps_its_good_and_quantity(self) -> None:
        """Unchanged draw order: the old contract now pays 120 x 3 (polish design 5.5)."""
        from spacegame.sim_rng import stable_seed

        dl = get_data_loader()
        gen = ProceduralMissionGenerator(
            dl.systems,
            dl.commodities,
            dl.enemy_templates,
            seed=stable_seed("player", "Tavi Okonkwo"),
        )
        delivery = gen.generate_delivery("nexus_prime", game_day=1)
        assert delivery is not None
        assert (delivery.objectives[0].target_id, delivery.objectives[0].target_quantity) == (
            "manufactured_goods",
            3,
        )
        assert next(r.amount for r in delivery.rewards if r.reward_type == "credits") == 360

    def test_surveys_and_salvage_pay_their_route_fuel(self) -> None:
        gen = self._make_generator()
        assert gen._route_fuel("nexus_prime", ["axiom_labs"]) == 540
        # The shortest order: Verdant, Forgeworks, Crimson Reach is 145 units; Forgeworks
        # first would be 178.
        assert gen._route_fuel("nexus_prime", ["forgeworks", "verdant", "crimson_reach"]) == 1450
        survey = gen.generate_survey("nexus_prime", game_day=10)
        stops = [o.target_id for o in survey.objectives[:-1]]
        fuel = [r for r in survey.rewards if r.reward_type == "route_fuel"]
        assert [r.amount for r in fuel] == [gen._route_fuel("nexus_prime", stops)]
        salvage = gen.generate_salvage("nexus_prime", game_day=10)
        target = salvage.objectives[0].target_id
        fuel = [r for r in salvage.rewards if r.reward_type == "route_fuel"]
        assert [r.amount for r in fuel] == [gen._route_fuel("nexus_prime", [target])]

    def test_route_fuel_pays_once_a_landing(self) -> None:
        def contract(mission_id: str) -> Mission:
            return Mission(
                id=mission_id,
                name=mission_id,
                description="A test salvage.",
                objectives=[
                    MissionObjective(type=ObjectiveType.REACH_SYSTEM, target_id="nexus_prime")
                ],
                rewards=[
                    MissionReward(reward_type="credits", amount=400),
                    MissionReward(reward_type="route_fuel", amount=540),
                ],
            )

        manager = MissionManager([])
        for mission_id in ("proc_salvage_a", "proc_salvage_b", "proc_salvage_c"):
            manager.add_mission(contract(mission_id), MissionStatus.ACTIVE)
        player = Player(
            "TestPilot",
            0,
            "nexus_prime",
            Ship(ship_type=get_data_loader().ship_types["shuttle"], current_fuel=40),
        )
        player.game_day = 9
        assert "+540 Credits (route fuel)" in manager.apply_rewards("proc_salvage_a", player)
        assert manager.apply_rewards("proc_salvage_b", player) == ["+400 Credits"]
        assert player.credits == 400 + 540 + 400
        state = manager.get_state()
        assert state["route_fuel_landing"] == [9, "nexus_prime"]
        restored = MissionManager([])
        restored.load_state(state)
        assert restored.get_state()["route_fuel_landing"] == [9, "nexus_prime"]
        player.game_day = 11
        manager.apply_rewards("proc_salvage_c", player)
        assert player.credits == 400 + 540 + 400 + 400 + 540

    def test_the_new_fields_survive_a_save(self) -> None:
        gen = self._make_generator()
        for mission in (
            gen.generate_bounty("nexus_prime", game_day=4),
            gen.generate_smuggling("nexus_prime", game_day=4),
        ):
            restored = Mission.from_dict(mission.to_dict())
            assert restored.ordered_final == mission.ordered_final
            assert [o.after_departure for o in restored.objectives] == [
                o.after_departure for o in mission.objectives
            ]

    def test_generate_survey(self) -> None:
        """Survey mission has multiple REACH_SYSTEM objectives."""
        gen = self._make_generator()
        mission = gen.generate_survey("nexus_prime", game_day=10)
        reach_objs = [o for o in mission.objectives if o.type == ObjectiveType.REACH_SYSTEM]
        assert len(reach_objs) >= 2, "Survey should visit multiple systems"

    def test_generate_salvage(self) -> None:
        """Salvage mission has REACH_SYSTEM objective."""
        gen = self._make_generator()
        mission = gen.generate_salvage("forgeworks", game_day=10)
        obj_types = {o.type for o in mission.objectives}
        assert ObjectiveType.REACH_SYSTEM in obj_types
        assert any(r.reward_type == "credits" for r in mission.rewards)

    def test_all_generated_missions_are_side_type(self) -> None:
        """All procedural missions have mission_type='side'."""
        gen = self._make_generator()
        for method in [
            gen.generate_bounty,
            gen.generate_delivery,
            gen.generate_smuggling,
            gen.generate_survey,
            gen.generate_salvage,
        ]:
            mission = method("nexus_prime", game_day=10)
            assert mission.mission_type == "side", f"{mission.id} should be side type"

    def test_all_generated_missions_have_station_board_discovery(self) -> None:
        """All procedural missions use station_board discovery method."""
        gen = self._make_generator()
        for method in [
            gen.generate_bounty,
            gen.generate_delivery,
            gen.generate_smuggling,
            gen.generate_survey,
            gen.generate_salvage,
        ]:
            mission = method("nexus_prime", game_day=10)
            assert mission.discovery_method == "station_board"

    def test_generated_ids_are_unique(self) -> None:
        """Each generated mission gets a unique ID."""
        gen = self._make_generator()
        ids = set()
        for day in range(1, 20):
            mission = gen.generate_delivery("nexus_prime", game_day=day)
            assert mission.id not in ids, f"Duplicate ID: {mission.id}"
            ids.add(mission.id)

    def test_id_names_type_system_day_and_seed(self) -> None:
        """The ID is keyed like the content: type, system, day, and base seed."""
        gen = self._make_generator(seed=42)
        mission = gen.generate_delivery("nexus_prime", game_day=10)
        assert mission.id == "proc_delivery_nexus_prime_10_42"

    def test_ids_do_not_depend_on_generator_history(self) -> None:
        """A generator rebuilt on load names a regenerated board exactly as before.

        Otherwise a same-day reload offers a copy of an accepted contract under a new ID.
        """
        used = self._make_generator()
        for day in range(1, 6):
            used.generate_for_system("nexus_prime", game_day=day)
        fresh = self._make_generator()
        used_ids = [m.id for m in used.generate_for_system("forgeworks", game_day=9)]
        fresh_ids = [m.id for m in fresh.generate_for_system("forgeworks", game_day=9)]
        assert used_ids == fresh_ids

    def test_board_ids_are_unique_on_every_board(self) -> None:
        """No board holds two missions of one type, so type-keyed IDs never collide."""
        gen = self._make_generator()
        for system_id in get_data_loader().systems:
            for day in range(1, 61):
                ids = [m.id for m in gen.generate_for_system(system_id, game_day=day)]
                assert len(ids) == len(set(ids)), f"{system_id} day {day} repeats an ID: {ids}"

    def test_available_at_matches_origin_system(self) -> None:
        """Generated missions are available at the system they were generated for."""
        gen = self._make_generator()
        mission = gen.generate_delivery("stellaris_port", game_day=5)
        assert "stellaris_port" in mission.available_at

    def test_generate_for_system_produces_mixed_types(self) -> None:
        """generate_for_system() produces 2-3 missions of varying types."""
        gen = self._make_generator()
        missions = gen.generate_for_system("nexus_prime", game_day=10)
        assert 2 <= len(missions) <= 3, f"Expected 2-3 missions, got {len(missions)}"
        # Should have at least 2 different mission name prefixes
        names = {m.name.split(":")[0].strip() for m in missions}
        assert len(names) >= 2, "Should have variety in mission types"

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed + system + day produces same missions."""
        gen1 = self._make_generator(seed=99)
        gen2 = self._make_generator(seed=99)
        m1 = gen1.generate_delivery("nexus_prime", game_day=10)
        m2 = gen2.generate_delivery("nexus_prime", game_day=10)
        assert m1.id == m2.id
        assert m1.name == m2.name

    def test_different_seeds_produce_different_missions(self) -> None:
        """Different seeds produce different missions."""
        gen1 = self._make_generator(seed=1)
        gen2 = self._make_generator(seed=999)
        m1 = gen1.generate_delivery("nexus_prime", game_day=10)
        m2 = gen2.generate_delivery("nexus_prime", game_day=10)
        # At minimum IDs should differ due to seed
        assert m1.id != m2.id

    def test_rewards_scale_with_difficulty(self) -> None:
        """Bounties at dangerous systems pay more per-kill than safe ones."""
        gen = self._make_generator()
        safe = gen.generate_bounty("nexus_prime", game_day=10)
        gen2 = self._make_generator()
        dangerous = gen2.generate_bounty("crimson_reach", game_day=10)
        safe_credits = sum(r.amount for r in safe.rewards if r.reward_type == "credits")
        danger_credits = sum(r.amount for r in dangerous.rewards if r.reward_type == "credits")
        # Normalize by kills to remove RNG variance in kill count.
        # Bounty reward = base_reward * danger_mult * kills, so per-kill
        # reward reflects base * danger_mult.
        safe_kills = next(
            o.target_quantity for o in safe.objectives if o.type == ObjectiveType.WIN_COMBAT
        )
        danger_kills = next(
            o.target_quantity for o in dangerous.objectives if o.type == ObjectiveType.WIN_COMBAT
        )
        safe_per_kill = safe_credits / max(safe_kills, 1)
        danger_per_kill = danger_credits / max(danger_kills, 1)
        # Dangerous (2.0x) should always pay more per-kill than safe (1.0x)
        assert danger_per_kill >= safe_per_kill, (
            f"Dangerous per-kill should be >= safe: {danger_per_kill} vs {safe_per_kill}"
        )

    def test_delivery_uses_valid_commodities(self) -> None:
        """Delivery mission references real commodity IDs."""
        dl = get_data_loader()
        gen = self._make_generator()
        mission = gen.generate_delivery("nexus_prime", game_day=10)
        for obj in mission.objectives:
            if obj.type == ObjectiveType.COLLECT_CARGO:
                assert obj.target_id in dl.commodities, f"Unknown commodity: {obj.target_id}"

    def test_survey_targets_are_valid_systems(self) -> None:
        """Survey objectives reference real system IDs."""
        dl = get_data_loader()
        gen = self._make_generator()
        mission = gen.generate_survey("nexus_prime", game_day=10)
        for obj in mission.objectives:
            if obj.type == ObjectiveType.REACH_SYSTEM:
                assert obj.target_id in dl.systems, f"Unknown system: {obj.target_id}"

    def test_smuggling_grants_contraband_cargo(self) -> None:
        """Smuggling on_accept_cargo references valid commodities."""
        dl = get_data_loader()
        gen = self._make_generator()
        mission = gen.generate_smuggling("crimson_reach", game_day=10)
        for cargo in mission.on_accept_cargo:
            assert cargo.commodity_id in dl.commodities, (
                f"Unknown commodity in accept cargo: {cargo.commodity_id}"
            )

    def test_all_rewards_have_xp(self) -> None:
        """All procedural missions reward XP."""
        gen = self._make_generator()
        for method in [
            gen.generate_bounty,
            gen.generate_delivery,
            gen.generate_smuggling,
            gen.generate_survey,
            gen.generate_salvage,
        ]:
            mission = method("nexus_prime", game_day=10)
            assert any(r.reward_type == "xp" for r in mission.rewards), (
                f"{mission.id} should reward XP"
            )
