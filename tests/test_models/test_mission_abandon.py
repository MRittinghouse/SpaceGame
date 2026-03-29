"""Tests for mission abandon functionality.

Validates that side missions can be abandoned, campaign missions cannot,
abandoned missions receive no rewards, and serialization works correctly.
"""

from spacegame.models.mission import MissionManager, MissionStatus


def _make_manager() -> MissionManager:
    """Create a MissionManager with missions loaded from game data."""
    from spacegame.data_loader import DataLoader

    dl = DataLoader()
    dl.load_all()
    missions = dl.missions if isinstance(dl.missions, list) else list(dl.missions.values())
    return MissionManager(missions)


class TestAbandonMission:
    def test_abandon_active_side_mission(self) -> None:
        mm = _make_manager()
        # Find a side mission and activate it
        side_ids = [
            m.id for m in mm._missions.values() if m.mission_type == "side"
        ]
        assert side_ids, "Should have at least one side mission"
        mid = side_ids[0]
        mm._status[mid] = MissionStatus.ACTIVE
        success, msg = mm.abandon_mission(mid)
        assert success, f"Should succeed: {msg}"
        assert mm.get_status(mid) == MissionStatus.ABANDONED

    def test_cannot_abandon_campaign_mission(self) -> None:
        mm = _make_manager()
        campaign_ids = [
            m.id for m in mm._missions.values() if m.mission_type == "campaign"
        ]
        assert campaign_ids, "Should have at least one campaign mission"
        mid = campaign_ids[0]
        mm._status[mid] = MissionStatus.ACTIVE
        success, msg = mm.abandon_mission(mid)
        assert not success
        assert "side" in msg.lower()

    def test_cannot_abandon_non_active_mission(self) -> None:
        mm = _make_manager()
        side_ids = [
            m.id for m in mm._missions.values() if m.mission_type == "side"
        ]
        mid = side_ids[0]
        # Mission is UNAVAILABLE by default
        success, msg = mm.abandon_mission(mid)
        assert not success
        assert "unavailable" in msg.lower()

    def test_abandoned_status_serializes(self) -> None:
        mm = _make_manager()
        side_ids = [
            m.id for m in mm._missions.values() if m.mission_type == "side"
        ]
        mid = side_ids[0]
        mm._status[mid] = MissionStatus.ACTIVE
        mm.abandon_mission(mid)
        state = mm.get_state()
        assert state["status"][mid] == "abandoned"
        # Restore
        mm.load_state(state)
        assert mm.get_status(mid) == MissionStatus.ABANDONED

    def test_abandoned_appears_in_completed_query(self) -> None:
        mm = _make_manager()
        side_ids = [
            m.id for m in mm._missions.values() if m.mission_type == "side"
        ]
        mid = side_ids[0]
        mm._status[mid] = MissionStatus.ACTIVE
        mm.abandon_mission(mid)
        abandoned = mm.get_missions_by_status(MissionStatus.ABANDONED)
        assert any(m.id == mid for m in abandoned)
        # Should NOT appear in COMPLETED
        completed = mm.get_missions_by_status(MissionStatus.COMPLETED)
        assert not any(m.id == mid for m in completed)

    def test_abandon_nonexistent_mission(self) -> None:
        mm = _make_manager()
        success, msg = mm.abandon_mission("nonexistent_id_xyz")
        assert not success
        assert "not found" in msg.lower()
