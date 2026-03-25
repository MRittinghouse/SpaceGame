"""Tests for ground exploration ingredient drops (anomalous_sample)."""

import pytest

from spacegame.models.ground import GroundInteractable


class TestGroundInteractableCommodities:
    """GroundInteractable should support loot_commodities."""

    def test_default_no_commodities(self) -> None:
        obj = GroundInteractable(x=0, y=0, interact_type="loot_container")
        assert obj.loot_commodities == {}

    def test_with_commodities(self) -> None:
        obj = GroundInteractable(
            x=0,
            y=0,
            interact_type="loot_container",
            loot_commodities={"anomalous_sample": 2},
        )
        assert obj.loot_commodities == {"anomalous_sample": 2}

    def test_loot_returns_commodities(self) -> None:
        obj = GroundInteractable(
            x=1,
            y=2,
            interact_type="loot_container",
            loot_credits=50,
            loot_commodities={"anomalous_sample": 1},
        )
        credits, commodities = obj.loot()
        assert credits == 50
        assert commodities == {"anomalous_sample": 1}

    def test_loot_already_looted(self) -> None:
        obj = GroundInteractable(
            x=1,
            y=2,
            interact_type="loot_container",
            loot_credits=50,
            loot_commodities={"anomalous_sample": 1},
        )
        obj.loot()  # First loot
        credits, commodities = obj.loot()
        assert credits == 0
        assert commodities == {}

    def test_serialization_round_trip(self) -> None:
        obj = GroundInteractable(
            x=3,
            y=4,
            interact_type="loot_container",
            loot_credits=75,
            loot_commodities={"anomalous_sample": 2, "rare_metals": 1},
        )
        data = obj.to_dict()
        restored = GroundInteractable.from_dict(data)
        assert restored.loot_commodities == {"anomalous_sample": 2, "rare_metals": 1}

    def test_backward_compat_no_commodities(self) -> None:
        """Deserializing old data without loot_commodities should default to empty."""
        data = {
            "x": 1,
            "y": 2,
            "interact_type": "loot_container",
            "loot_credits": 30,
        }
        obj = GroundInteractable.from_dict(data)
        assert obj.loot_commodities == {}


def _make_mission_config() -> "GroundMissionConfig":
    from spacegame.models.ground_mission import (
        GroundMissionConfig,
        MissionType,
        DifficultyTier,
        GroundMissionRewards,
    )

    return GroundMissionConfig(
        id="test_mission",
        name="Test",
        description="test",
        mission_type=MissionType.INFILTRATION,
        difficulty=DifficultyTier.LOW,
        faction_id="nexus_trade",
        objectives=["Test"],
        intel_hints=[],
        rewards=GroundMissionRewards(),
    )


class TestGroundMissionResultCommodities:
    """GroundMissionResult should carry loot_commodities."""

    def test_default_no_commodities(self) -> None:
        from spacegame.models.ground_mission import GroundMissionResult, MissionOutcome

        result = GroundMissionResult(
            config=_make_mission_config(),
            outcome=MissionOutcome.SUCCESS,
            objectives_completed=1,
            objectives_total=1,
            turns_taken=10,
            enemies_defeated=0,
            enemies_talked=0,
            loot_credits=100,
            loot_items=[],
            progress_percent=1.0,
            crew_ids=[],
            detected=False,
        )
        assert result.loot_commodities == {}

    def test_with_commodities(self) -> None:
        from spacegame.models.ground_mission import GroundMissionResult, MissionOutcome

        result = GroundMissionResult(
            config=_make_mission_config(),
            outcome=MissionOutcome.SUCCESS,
            objectives_completed=1,
            objectives_total=1,
            turns_taken=10,
            enemies_defeated=0,
            enemies_talked=0,
            loot_credits=100,
            loot_items=[],
            progress_percent=1.0,
            crew_ids=[],
            detected=False,
            loot_commodities={"anomalous_sample": 3},
        )
        assert result.loot_commodities == {"anomalous_sample": 3}

    def test_serialization_round_trip(self) -> None:
        from spacegame.models.ground_mission import GroundMissionResult, MissionOutcome

        result = GroundMissionResult(
            config=_make_mission_config(),
            outcome=MissionOutcome.SUCCESS,
            objectives_completed=1,
            objectives_total=1,
            turns_taken=10,
            enemies_defeated=0,
            enemies_talked=0,
            loot_credits=100,
            loot_items=[],
            progress_percent=1.0,
            crew_ids=[],
            detected=False,
            loot_commodities={"anomalous_sample": 2},
        )
        data = result.to_dict()
        restored = GroundMissionResult.from_dict(data)
        assert restored.loot_commodities == {"anomalous_sample": 2}
