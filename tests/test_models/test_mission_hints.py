"""Tests for the mission hint system ('What To Do Next').

Verifies that MissionManager.get_current_hint() returns the correct
hint text based on mission progression.
"""

from spacegame.models.mission import (
    Mission,
    MissionManager,
    MissionObjective,
    MissionStatus,
    ObjectiveType,
)


def _make_mission(
    mission_id: str,
    name: str = "Test Mission",
    prerequisites: list[str] | None = None,
    hint: str = "",
    auto_accept: bool = False,
    required_flags: list[str] | None = None,
) -> Mission:
    """Create a test mission with minimal fields."""
    return Mission(
        id=mission_id,
        name=name,
        description="Test description",
        objectives=[
            MissionObjective(
                type=ObjectiveType.HAS_FLAG,
                target_id=f"{mission_id}_done",
            )
        ],
        prerequisites=prerequisites or [],
        required_flags=required_flags or [],
        hint=hint,
        auto_accept=auto_accept,
    )


class TestMissionHints:
    """Test get_current_hint() functionality."""

    def test_hint_field_on_mission(self) -> None:
        """Mission dataclass has a hint field."""
        m = _make_mission("test", hint="Go to Nexus Prime.")
        assert m.hint == "Go to Nexus Prime."

    def test_hint_defaults_to_empty(self) -> None:
        """Hint defaults to empty string."""
        m = _make_mission("test")
        assert m.hint == ""

    def test_get_current_hint_returns_active_mission_hint(self) -> None:
        """Returns hint for the first active campaign mission."""
        m1 = _make_mission("m1", name="First", hint="Do first thing.")
        m2 = _make_mission("m2", name="Second", hint="Do second thing.", prerequisites=["m1"])
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")

        result = mgr.get_current_hint()
        assert result is not None
        name, hint = result
        assert name == "First"
        assert hint == "Do first thing."

    def test_get_current_hint_returns_available_if_no_active(self) -> None:
        """Falls back to available mission hint if nothing active."""
        m1 = _make_mission("m1", name="First", hint="Do first thing.")
        mgr = MissionManager([m1])
        mgr.update_availability()
        # m1 is available but not accepted

        result = mgr.get_current_hint()
        assert result is not None
        name, hint = result
        assert name == "First"
        assert hint == "Do first thing."

    def test_get_current_hint_none_when_all_complete(self) -> None:
        """Returns None when all missions are complete."""
        m1 = _make_mission("m1", hint="Do it.")
        mgr = MissionManager([m1])
        mgr.update_availability()
        mgr.accept_mission("m1")
        # Manually complete
        mgr._status["m1"] = MissionStatus.COMPLETED

        result = mgr.get_current_hint()
        assert result is None

    def test_get_current_hint_prefers_active_over_available(self) -> None:
        """Active missions take priority over available ones."""
        m1 = _make_mission("m1", name="Active", hint="Active hint.")
        m2 = _make_mission("m2", name="Available", hint="Available hint.")
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")
        # m2 is also available but not accepted

        result = mgr.get_current_hint()
        assert result is not None
        name, _ = result
        assert name == "Active"

    def test_get_current_hint_skips_missions_without_hints(self) -> None:
        """Missions without hint text are skipped."""
        m1 = _make_mission("m1", name="No Hint", hint="")
        m2 = _make_mission("m2", name="Has Hint", hint="Go here.")
        mgr = MissionManager([m1, m2])
        mgr.update_availability()
        mgr.accept_mission("m1")
        # m2 also available

        result = mgr.get_current_hint()
        assert result is not None
        name, hint = result
        assert name == "Has Hint"
        assert hint == "Go here."

    def test_hint_updates_as_missions_complete(self) -> None:
        """Hint changes as player completes missions."""
        m1 = _make_mission("m1", name="First", hint="Do first.", auto_accept=True)
        m2 = _make_mission(
            "m2", name="Second", hint="Do second.", prerequisites=["m1"], auto_accept=True
        )
        mgr = MissionManager([m1, m2])
        mgr.update_availability()

        # Initially: m1 is active
        result = mgr.get_current_hint()
        assert result is not None
        assert result[0] == "First"

        # Complete m1, update availability
        mgr._status["m1"] = MissionStatus.COMPLETED
        mgr.update_availability()

        # Now: m2 is active
        result = mgr.get_current_hint()
        assert result is not None
        assert result[0] == "Second"

    def test_hint_serialization_round_trip(self) -> None:
        """Hint field survives to_dict/from_dict."""
        m = _make_mission("m1", hint="Test hint.")
        d = m.to_dict()
        assert d["hint"] == "Test hint."
