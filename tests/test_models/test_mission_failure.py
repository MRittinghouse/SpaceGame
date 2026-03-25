"""Tests for mission failure mechanics."""

from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionReward,
    MissionStatus,
)


def _make_mission(
    mission_id: str = "test_mission",
    prerequisites: list[str] | None = None,
    auto_accept: bool = False,
) -> Mission:
    return Mission(
        id=mission_id,
        name="Test Mission",
        description="A test mission.",
        objectives=[
            MissionObjective(type="reach_system", target_id="breakstone", target_quantity=1)
        ],
        rewards=[MissionReward(reward_type="credits", amount=100)],
        prerequisites=prerequisites or [],
        auto_accept=auto_accept,
    )


class TestMissionFailure:
    """Tests for the FAILED mission status and fail_mission method."""

    def test_failed_status_exists(self) -> None:
        """MissionStatus should include FAILED."""
        assert MissionStatus.FAILED.value == "failed"

    def test_fail_active_mission(self) -> None:
        """Failing an active mission transitions to FAILED."""
        m = _make_mission("m1")
        manager = MissionManager([m])
        manager._status["m1"] = MissionStatus.ACTIVE

        success, msg = manager.fail_mission("m1")
        assert success, f"Should succeed: {msg}"
        assert manager.get_status("m1") == MissionStatus.FAILED

    def test_fail_non_active_mission_rejected(self) -> None:
        """Cannot fail a mission that isn't ACTIVE."""
        m = _make_mission("m1")
        manager = MissionManager([m])

        success, msg = manager.fail_mission("m1")
        assert not success, "Should fail for UNAVAILABLE mission"
        assert manager.get_status("m1") == MissionStatus.UNAVAILABLE

    def test_fail_completed_mission_rejected(self) -> None:
        """Cannot fail an already-completed mission."""
        m = _make_mission("m1")
        manager = MissionManager([m])
        manager._status["m1"] = MissionStatus.COMPLETED

        success, msg = manager.fail_mission("m1")
        assert not success, "Should fail for COMPLETED mission"

    def test_fail_unknown_mission_rejected(self) -> None:
        """Cannot fail a mission that doesn't exist."""
        manager = MissionManager([])
        success, msg = manager.fail_mission("nonexistent")
        assert not success

    def test_failed_mission_not_in_completed_ids(self) -> None:
        """Failed missions should not appear in completed IDs."""
        m = _make_mission("m1")
        manager = MissionManager([m])
        manager._status["m1"] = MissionStatus.FAILED

        assert "m1" not in manager.get_completed_ids()

    def test_failed_mission_does_not_unlock_dependents(self) -> None:
        """Failed prerequisite should not unlock dependent missions."""
        prereq = _make_mission("prereq")
        dependent = _make_mission("dep", prerequisites=["prereq"])
        manager = MissionManager([prereq, dependent])
        manager._status["prereq"] = MissionStatus.FAILED

        newly = manager.update_availability()
        assert "dep" not in newly
        assert manager.get_status("dep") == MissionStatus.UNAVAILABLE

    def test_get_status_returns_correct_status(self) -> None:
        """get_status returns the current status of a mission."""
        m = _make_mission("m1")
        manager = MissionManager([m])
        assert manager.get_status("m1") == MissionStatus.UNAVAILABLE

        manager._status["m1"] = MissionStatus.ACTIVE
        assert manager.get_status("m1") == MissionStatus.ACTIVE

    def test_get_status_returns_none_for_unknown(self) -> None:
        """get_status returns None for unknown mission IDs."""
        manager = MissionManager([])
        assert manager.get_status("nonexistent") is None

    def test_failed_status_serialization_roundtrip(self) -> None:
        """FAILED status survives save/load."""
        m = _make_mission("m1")
        manager = MissionManager([m])
        manager._status["m1"] = MissionStatus.FAILED

        state = manager.get_state()
        manager2 = MissionManager([m])
        manager2.load_state(state)
        assert manager2.get_status("m1") == MissionStatus.FAILED
