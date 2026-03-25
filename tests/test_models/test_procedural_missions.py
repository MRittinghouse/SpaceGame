"""Tests for R4.3 procedural mission generation.

Verifies the ProceduralMissionGenerator creates valid missions of each
template type, and that MissionManager.add_mission() correctly integrates
generated missions into the lifecycle.
"""

import random

from spacegame.data_loader import get_data_loader
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
        """Smuggling mission has COLLECT_CARGO + REACH_SYSTEM, grants cargo on accept."""
        gen = self._make_generator()
        mission = gen.generate_smuggling("crimson_reach", game_day=10)
        assert len(mission.on_accept_cargo) > 0, "Smuggling mission should grant cargo"
        obj_types = {o.type for o in mission.objectives}
        assert ObjectiveType.REACH_SYSTEM in obj_types

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
