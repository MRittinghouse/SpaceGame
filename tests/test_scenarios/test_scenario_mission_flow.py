"""Scenario D: Mission accept → progress → complete → reward.

Walks a mission through UNAVAILABLE → AVAILABLE → ACTIVE → COMPLETED,
verifying side effects at each stage. Uses real mission definitions from
``data/missions/*.json`` so the test catches authoring bugs as well as
engine bugs.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager, MissionStatus, ObjectiveType
from tests.test_scenarios._helpers import fresh_player


def _manager_for_test() -> MissionManager:
    dl = get_data_loader()
    dl.load_all()
    return MissionManager(dl.missions)


class TestFlagGatedMissionBecomesAvailable:
    """A mission with a ``required_flags`` prereq must remain UNAVAILABLE
    until the flag is set, then become AVAILABLE."""

    def test_unavailable_until_flag_set(self) -> None:
        player = fresh_player()
        mgr = _manager_for_test()

        # Find any mission with a required_flags prereq AND no other gates
        target = None
        for _mid, mission in mgr._missions.items():
            if (
                mission.required_flags
                and not mission.prerequisites
                and not mission.available_after
                and not mission.required_reputation
                and mission.mission_type != "campaign"
            ):
                target = mission
                break
        assert target is not None, "Need a flag-gated mission in data to run this test"

        # Without flag: should remain unavailable
        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        assert mgr.get_status(target.id) == MissionStatus.UNAVAILABLE

        # Set required flags; should become available
        for flag in target.required_flags:
            player.dialogue_flags[flag] = True
        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        status = mgr.get_status(target.id)
        # auto_accept missions skip to ACTIVE; others stop at AVAILABLE.
        assert status in (MissionStatus.AVAILABLE, MissionStatus.ACTIVE)


class TestMissionAcceptActivates:
    def test_accept_transitions_to_active(self) -> None:
        player = fresh_player()
        mgr = _manager_for_test()

        # Pick a side mission without required_flags (simplest case)
        target = None
        for _mid, mission in mgr._missions.items():
            if (
                not mission.required_flags
                and not mission.prerequisites
                and not mission.available_after
                and not mission.required_reputation
                and not mission.auto_accept
            ):
                target = mission
                break
        assert target is not None

        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        assert mgr.get_status(target.id) == MissionStatus.AVAILABLE

        ok, msg = mgr.accept_mission(target.id)
        assert ok, f"Accept should succeed: {msg}"
        assert mgr.get_status(target.id) == MissionStatus.ACTIVE


class TestObjectiveProgressAndCompletion:
    """Drive a mission with a simple objective (HAS_FLAG or HAVE_CREDITS) and
    verify completion."""

    def test_has_flag_objective_completes_when_flag_set(self) -> None:
        player = fresh_player()
        mgr = _manager_for_test()

        # Find a mission whose first objective is HAS_FLAG on a flag we control.
        target = None
        for _mid, mission in mgr._missions.items():
            if not mission.objectives:
                continue
            obj0 = mission.objectives[0]
            if (
                obj0.type == ObjectiveType.HAS_FLAG
                and not mission.required_flags
                and not mission.prerequisites
                and not mission.available_after
                and not mission.required_reputation
            ):
                target = mission
                break
        if target is None:
            # No matching mission — skip, not a failure.
            return

        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        mgr.accept_mission(target.id)
        assert mgr.get_status(target.id) == MissionStatus.ACTIVE

        # Set the flag the objective reads
        player.dialogue_flags[target.objectives[0].target_id] = True

        newly_completed = mgr.check_objectives(player)
        # If mission has ONLY this objective, it should complete now
        if len(target.objectives) == 1:
            assert target.id in newly_completed
            assert mgr.get_status(target.id) == MissionStatus.COMPLETED

    def test_have_credits_objective_completes_when_credits_sufficient(self) -> None:
        player = fresh_player(credits=100)  # Start low
        mgr = _manager_for_test()

        # Find a mission with ONLY HAVE_CREDITS objective.
        target = None
        for _mid, mission in mgr._missions.items():
            if (
                len(mission.objectives) == 1
                and mission.objectives[0].type == ObjectiveType.HAVE_CREDITS
                and not mission.required_flags
                and not mission.prerequisites
            ):
                target = mission
                break
        if target is None:
            return  # No matching mission in data

        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        mgr.accept_mission(target.id)

        # Below threshold — doesn't complete
        target_credits = target.objectives[0].target_quantity
        player.credits = max(0, target_credits - 1)
        newly = mgr.check_objectives(player)
        assert target.id not in newly

        # Meet threshold — completes
        player.credits = target_credits
        newly = mgr.check_objectives(player)
        assert target.id in newly
        assert mgr.get_status(target.id) == MissionStatus.COMPLETED


class TestRewardApplication:
    """Verify rewards actually mutate player state (credits, XP, flags)."""

    def test_apply_rewards_grants_credits_and_xp(self) -> None:
        player = fresh_player(credits=1000)
        mgr = _manager_for_test()

        # Pick any mission whose first reward is credits; don't care about flow.
        target = None
        for _mid, mission in mgr._missions.items():
            has_credits_reward = any(r.reward_type == "credits" and r.amount > 0 for r in mission.rewards)
            if has_credits_reward:
                target = mission
                break
        assert target is not None

        before_credits = player.credits
        before_xp = player.progression.xp

        credit_rewards = sum(
            r.amount for r in target.rewards if r.reward_type == "credits"
        )
        xp_rewards = sum(
            r.amount for r in target.rewards if r.reward_type == "xp"
        )

        messages = mgr.apply_rewards(target.id, player)

        assert player.credits == before_credits + credit_rewards, (
            f"Credits must be granted. before={before_credits}, "
            f"after={player.credits}, expected_delta={credit_rewards}"
        )
        if xp_rewards > 0:
            assert player.progression.xp >= before_xp + xp_rewards
        assert len(messages) >= 1

    def test_apply_rewards_sets_flags(self) -> None:
        mgr = _manager_for_test()
        player = fresh_player()

        # Pick a mission whose rewards include set_flag
        target = None
        for _mid, mission in mgr._missions.items():
            if any(r.reward_type == "set_flag" for r in mission.rewards):
                target = mission
                break
        assert target is not None

        set_flag_rewards = [
            r.target_id for r in target.rewards if r.reward_type == "set_flag" and r.target_id
        ]
        assert set_flag_rewards, "Sanity — should have at least one flag to set"

        mgr.apply_rewards(target.id, player)

        for flag in set_flag_rewards:
            assert player.dialogue_flags.get(flag) is True, (
                f"set_flag reward must actually set the flag: {flag}"
            )


class TestCannotAcceptNonAvailableMission:
    def test_accept_unavailable_returns_false(self) -> None:
        mgr = _manager_for_test()

        # Pick a mission we know is UNAVAILABLE (has flag prereqs)
        target = None
        for _mid, mission in mgr._missions.items():
            if mission.required_flags:
                target = mission
                break
        assert target is not None
        assert mgr.get_status(target.id) == MissionStatus.UNAVAILABLE

        ok, msg = mgr.accept_mission(target.id)
        assert not ok
        assert "not available" in msg.lower() or "unavailable" in msg.lower()

    def test_cannot_double_accept(self) -> None:
        mgr = _manager_for_test()
        player = fresh_player()

        # Pick any mission that can be accepted
        target = None
        for _mid, mission in mgr._missions.items():
            if (
                not mission.required_flags
                and not mission.prerequisites
                and not mission.available_after
                and not mission.required_reputation
                and not mission.auto_accept
            ):
                target = mission
                break
        assert target is not None

        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        mgr.accept_mission(target.id)  # First accept
        ok, _msg = mgr.accept_mission(target.id)  # Second attempt
        assert not ok, "Cannot accept a mission that's already ACTIVE"


class TestMissionFullLifecycle:
    """The full loop — find → accept → complete → reward — on a real mission."""

    def test_end_to_end_for_realistic_mission(self) -> None:
        mgr = _manager_for_test()
        player = fresh_player(credits=1000)

        # Prefer a mission with HAS_FLAG objectives only so we can drive completion.
        target = None
        for _mid, mission in mgr._missions.items():
            if (
                mission.objectives
                and all(obj.type == ObjectiveType.HAS_FLAG for obj in mission.objectives)
                and not mission.required_flags
                and not mission.prerequisites
                and not mission.available_after
                and not mission.required_reputation
                and not mission.auto_accept
            ):
                target = mission
                break
        if target is None:
            return  # No mission matches in data

        # 1. Mission starts unavailable → becomes available
        mgr.update_availability(player.dialogue_flags, player.faction_reputation)
        assert mgr.get_status(target.id) == MissionStatus.AVAILABLE

        # 2. Accept → active
        mgr.accept_mission(target.id)
        assert mgr.get_status(target.id) == MissionStatus.ACTIVE

        # 3. Set each HAS_FLAG objective's flag → completes
        for obj in target.objectives:
            player.dialogue_flags[obj.target_id] = True
        newly_completed = mgr.check_objectives(player)
        assert target.id in newly_completed
        assert mgr.get_status(target.id) == MissionStatus.COMPLETED

        # 4. Apply rewards
        before_credits = player.credits
        mgr.apply_rewards(target.id, player)
        # At minimum, credits reward should have fired if present.
        credit_rewards = sum(r.amount for r in target.rewards if r.reward_type == "credits")
        if credit_rewards > 0:
            assert player.credits == before_credits + credit_rewards
