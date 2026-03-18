"""Tests for ground interactables and story triggers.

Tests GroundInteractable, GroundStoryTrigger models, their integration
with MapGenResult, GroundMissionState, GroundPlayerState, and
CampaignMapBuilder.
"""

import pytest

from spacegame.models.ground import (
    GroundInteractable,
    GroundMap,
    GroundPlayerState,
    GroundStoryTrigger,
    GroundTile,
    TileType,
)
from spacegame.models.ground_enemy import GroundMissionState
from spacegame.models.ground_mapgen import (
    DifficultyTier,
    MapGenConfig,
    MapGenResult,
    MissionType,
)


def _make_simple_map(width: int = 10, height: int = 8) -> GroundMap:
    """Create a simple map with floor tiles and wall border."""
    tiles = []
    for y in range(height):
        row = []
        for x in range(width):
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                row.append(GroundTile(tile_type=TileType.WALL))
            elif x == 1 and y == 1:
                row.append(GroundTile(tile_type=TileType.ENTRANCE))
            elif x == width - 2 and y == height - 2:
                row.append(GroundTile(tile_type=TileType.EXIT))
            else:
                row.append(GroundTile(tile_type=TileType.FLOOR))
        tiles.append(row)
    return GroundMap(
        width=width,
        height=height,
        tiles=tiles,
        entrance_pos=(1, 1),
        exit_pos=(width - 2, height - 2),
    )


def _make_config() -> MapGenConfig:
    return MapGenConfig(
        mission_type=MissionType.INFILTRATION,
        difficulty=DifficultyTier.LOW,
        seed=42,
    )


# === GroundInteractable model ===


class TestGroundInteractable:
    """GroundInteractable dataclass construction and state."""

    def test_construction(self):
        """Interactable stores position, type, credits, and description."""
        obj = GroundInteractable(
            x=5, y=3,
            interact_type="loot_container",
            loot_credits=50,
            description="A supply crate.",
        )
        assert obj.x == 5
        assert obj.y == 3
        assert obj.interact_type == "loot_container"
        assert obj.loot_credits == 50
        assert obj.description == "A supply crate."

    def test_not_looted_by_default(self):
        """Interactable starts as not looted."""
        obj = GroundInteractable(x=1, y=1, interact_type="loot_container")
        assert obj.looted is False

    def test_loot_marks_looted(self):
        """Collecting loot marks the interactable as looted."""
        obj = GroundInteractable(x=1, y=1, interact_type="loot_container", loot_credits=30)
        credits, _commodities = obj.loot()
        assert credits == 30
        assert obj.looted is True

    def test_loot_twice_returns_zero(self):
        """Looting a second time returns 0."""
        obj = GroundInteractable(x=1, y=1, interact_type="loot_container", loot_credits=30)
        obj.loot()
        assert obj.loot() == (0, {})

    def test_default_credits_zero(self):
        """Default loot credits is 0."""
        obj = GroundInteractable(x=1, y=1, interact_type="loot_container")
        assert obj.loot_credits == 0

    def test_default_description_empty(self):
        """Default description is empty string."""
        obj = GroundInteractable(x=1, y=1, interact_type="loot_container")
        assert obj.description == ""

    def test_to_dict(self):
        """Serializes to dict."""
        obj = GroundInteractable(x=5, y=3, interact_type="loot_container", loot_credits=50)
        d = obj.to_dict()
        assert d["x"] == 5
        assert d["y"] == 3
        assert d["interact_type"] == "loot_container"
        assert d["loot_credits"] == 50
        assert d["looted"] is False

    def test_from_dict(self):
        """Deserializes from dict."""
        d = {
            "x": 5, "y": 3, "interact_type": "loot_container",
            "loot_credits": 50, "description": "Crate", "looted": True,
        }
        obj = GroundInteractable.from_dict(d)
        assert obj.x == 5
        assert obj.looted is True
        assert obj.description == "Crate"


# === GroundStoryTrigger model ===


class TestGroundStoryTrigger:
    """GroundStoryTrigger dataclass construction and state."""

    def test_construction(self):
        """Story trigger stores position, type, and text."""
        trigger = GroundStoryTrigger(
            x=5, y=3,
            trigger_type="atmosphere",
            text="The corridor smells of rust.",
        )
        assert trigger.x == 5
        assert trigger.y == 3
        assert trigger.trigger_type == "atmosphere"
        assert trigger.text == "The corridor smells of rust."

    def test_not_triggered_by_default(self):
        """Story trigger starts as not triggered."""
        trigger = GroundStoryTrigger(x=1, y=1, trigger_type="atmosphere", text="Hello")
        assert trigger.triggered is False

    def test_fire_marks_triggered(self):
        """Firing a trigger marks it as triggered and returns text."""
        trigger = GroundStoryTrigger(x=1, y=1, trigger_type="atmosphere", text="The room echoes.")
        text = trigger.fire()
        assert text == "The room echoes."
        assert trigger.triggered is True

    def test_fire_twice_returns_none(self):
        """Firing a second time returns None (one-shot)."""
        trigger = GroundStoryTrigger(x=1, y=1, trigger_type="atmosphere", text="Echo.")
        trigger.fire()
        assert trigger.fire() is None

    def test_to_dict(self):
        """Serializes to dict."""
        trigger = GroundStoryTrigger(x=5, y=3, trigger_type="atmosphere", text="Dust.")
        d = trigger.to_dict()
        assert d["x"] == 5
        assert d["trigger_type"] == "atmosphere"
        assert d["triggered"] is False

    def test_from_dict(self):
        """Deserializes from dict."""
        d = {"x": 5, "y": 3, "trigger_type": "atmosphere", "text": "Dust.", "triggered": True}
        trigger = GroundStoryTrigger.from_dict(d)
        assert trigger.triggered is True
        assert trigger.text == "Dust."


# === MapGenResult integration ===


class TestMapGenResultInteractables:
    """MapGenResult carries interactables and story triggers."""

    def test_default_empty_interactables(self):
        """MapGenResult defaults to empty interactables list."""
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config()
        )
        assert result.interactables == []

    def test_default_empty_story_triggers(self):
        """MapGenResult defaults to empty story triggers list."""
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config()
        )
        assert result.story_triggers == []

    def test_carries_interactables(self):
        """MapGenResult stores interactables."""
        obj = GroundInteractable(x=3, y=3, interact_type="loot_container", loot_credits=50)
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config(),
            interactables=[obj],
        )
        assert len(result.interactables) == 1
        assert result.interactables[0].loot_credits == 50

    def test_carries_story_triggers(self):
        """MapGenResult stores story triggers."""
        trigger = GroundStoryTrigger(x=3, y=3, trigger_type="atmosphere", text="Dark.")
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config(),
            story_triggers=[trigger],
        )
        assert len(result.story_triggers) == 1


# === GroundMissionState integration ===


class TestMissionStateInteractables:
    """GroundMissionState tracks interactables and story triggers."""

    def test_has_interactables(self):
        """Mission state carries interactable list."""
        gmap = _make_simple_map()
        obj = GroundInteractable(x=3, y=3, interact_type="loot_container", loot_credits=50)
        state = GroundMissionState(
            ground_map=gmap,
            player=GroundPlayerState(x=1, y=1),
            interactables=[obj],
        )
        assert len(state.interactables) == 1

    def test_has_story_triggers(self):
        """Mission state carries story triggers list."""
        gmap = _make_simple_map()
        trigger = GroundStoryTrigger(x=3, y=3, trigger_type="atmosphere", text="Wind.")
        state = GroundMissionState(
            ground_map=gmap,
            player=GroundPlayerState(x=1, y=1),
            story_triggers=[trigger],
        )
        assert len(state.story_triggers) == 1

    def test_get_interactable_at(self):
        """Gets un-looted interactable at a position."""
        obj = GroundInteractable(x=3, y=3, interact_type="loot_container", loot_credits=50)
        state = GroundMissionState(
            ground_map=_make_simple_map(),
            player=GroundPlayerState(x=1, y=1),
            interactables=[obj],
        )
        found = state.get_interactable_at(3, 3)
        assert found is obj

    def test_get_interactable_at_returns_none_when_looted(self):
        """Returns None for looted interactable."""
        obj = GroundInteractable(x=3, y=3, interact_type="loot_container", loot_credits=50)
        obj.loot()
        state = GroundMissionState(
            ground_map=_make_simple_map(),
            player=GroundPlayerState(x=1, y=1),
            interactables=[obj],
        )
        assert state.get_interactable_at(3, 3) is None

    def test_get_interactable_at_returns_none_for_empty(self):
        """Returns None when no interactable at position."""
        state = GroundMissionState(
            ground_map=_make_simple_map(),
            player=GroundPlayerState(x=1, y=1),
        )
        assert state.get_interactable_at(3, 3) is None

    def test_get_story_trigger_at(self):
        """Gets un-triggered story trigger at a position."""
        trigger = GroundStoryTrigger(x=4, y=4, trigger_type="atmosphere", text="Dust.")
        state = GroundMissionState(
            ground_map=_make_simple_map(),
            player=GroundPlayerState(x=1, y=1),
            story_triggers=[trigger],
        )
        found = state.get_story_trigger_at(4, 4)
        assert found is trigger

    def test_get_story_trigger_at_returns_none_when_fired(self):
        """Returns None for already-triggered story trigger."""
        trigger = GroundStoryTrigger(x=4, y=4, trigger_type="atmosphere", text="Dust.")
        trigger.fire()
        state = GroundMissionState(
            ground_map=_make_simple_map(),
            player=GroundPlayerState(x=1, y=1),
            story_triggers=[trigger],
        )
        assert state.get_story_trigger_at(4, 4) is None


# === build_mission_state passes through ===


class TestBuildMissionStateWithInteractables:
    """build_mission_state() forwards interactables and triggers."""

    def test_passes_interactables(self):
        """Interactables appear in the built mission state."""
        obj = GroundInteractable(x=3, y=3, interact_type="loot_container", loot_credits=40)
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config(),
            interactables=[obj],
        )
        state = result.build_mission_state()
        assert len(state.interactables) == 1
        assert state.interactables[0].loot_credits == 40

    def test_passes_story_triggers(self):
        """Story triggers appear in the built mission state."""
        trigger = GroundStoryTrigger(x=4, y=4, trigger_type="atmosphere", text="Hum.")
        result = MapGenResult(
            ground_map=_make_simple_map(), enemies=[], config=_make_config(),
            story_triggers=[trigger],
        )
        state = result.build_mission_state()
        assert len(state.story_triggers) == 1
        assert state.story_triggers[0].text == "Hum."


# === CampaignMapBuilder builds interactables and triggers ===


class TestCampaignMapBuilderInteractables:
    """CampaignMapBuilder creates interactable and trigger instances."""

    def _make_campaign_data(self) -> dict:
        return {
            "id": "test_map",
            "name": "Test Map",
            "width": 10,
            "height": 8,
            "mission_type": "infiltration",
            "difficulty": "low",
            "faction_id": "commerce_guild",
            "tiles": [
                ["W"] * 10,
                ["W", "E", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "F", "W"],
                ["W", "F", "F", "F", "F", "F", "F", "F", "X", "W"],
                ["W"] * 10,
            ],
            "entrance": [1, 1],
            "exit": [8, 6],
            "enemies": [],
            "interactables": [
                {
                    "x": 3, "y": 3,
                    "type": "loot_container",
                    "loot_credits": 55,
                    "description": "A crate of spare parts.",
                },
                {
                    "x": 6, "y": 5,
                    "type": "loot_container",
                    "loot_credits": 30,
                    "description": "Salvage bin.",
                },
            ],
            "story_triggers": [
                {
                    "x": 4, "y": 2,
                    "type": "atmosphere",
                    "text": "The air smells of machine oil.",
                },
            ],
        }

    def test_builds_interactables(self):
        """Campaign builder creates GroundInteractable instances."""
        from spacegame.models.campaign_map import CampaignMapBuilder, CampaignMapData

        data = CampaignMapData.from_dict(self._make_campaign_data())
        result = CampaignMapBuilder.build(data)
        assert len(result.interactables) == 2
        assert result.interactables[0].x == 3
        assert result.interactables[0].y == 3
        assert result.interactables[0].loot_credits == 55
        assert result.interactables[0].interact_type == "loot_container"
        assert result.interactables[0].description == "A crate of spare parts."

    def test_builds_story_triggers(self):
        """Campaign builder creates GroundStoryTrigger instances."""
        from spacegame.models.campaign_map import CampaignMapBuilder, CampaignMapData

        data = CampaignMapData.from_dict(self._make_campaign_data())
        result = CampaignMapBuilder.build(data)
        assert len(result.story_triggers) == 1
        assert result.story_triggers[0].x == 4
        assert result.story_triggers[0].y == 2
        assert result.story_triggers[0].trigger_type == "atmosphere"
        assert result.story_triggers[0].text == "The air smells of machine oil."

    def test_no_interactables_defaults_empty(self):
        """Campaign map with no interactables gets empty list."""
        from spacegame.models.campaign_map import CampaignMapBuilder, CampaignMapData

        raw = self._make_campaign_data()
        del raw["interactables"]
        del raw["story_triggers"]
        data = CampaignMapData.from_dict(raw)
        result = CampaignMapBuilder.build(data)
        assert result.interactables == []
        assert result.story_triggers == []

    def test_interactables_survive_mission_state(self):
        """Interactables flow through build → build_mission_state."""
        from spacegame.models.campaign_map import CampaignMapBuilder, CampaignMapData

        data = CampaignMapData.from_dict(self._make_campaign_data())
        result = CampaignMapBuilder.build(data)
        state = result.build_mission_state()
        assert len(state.interactables) == 2
        assert len(state.story_triggers) == 1


# === Player interaction with loot containers ===


class TestPlayerInteractWithContainer:
    """GroundPlayerState can interact with adjacent loot containers."""

    def _make_state_with_container(
        self, player_x: int = 3, player_y: int = 3,
        container_x: int = 4, container_y: int = 3,
        loot_credits: int = 50,
    ) -> GroundMissionState:
        gmap = _make_simple_map()
        obj = GroundInteractable(
            x=container_x, y=container_y,
            interact_type="loot_container",
            loot_credits=loot_credits,
            description="Test crate.",
        )
        return GroundMissionState(
            ground_map=gmap,
            player=GroundPlayerState(x=player_x, y=player_y),
            interactables=[obj],
        )

    def test_interact_adjacent_container(self):
        """Player can loot an adjacent container."""
        state = self._make_state_with_container()
        success, msg = state.player.interact(
            state.ground_map, 4, 3, interactables=state.interactables
        )
        assert success
        assert "50" in msg
        assert state.interactables[0].looted is True

    def test_interact_increments_turn(self):
        """Interacting with a container costs a turn."""
        state = self._make_state_with_container()
        initial_turn = state.player.turn_number
        state.player.interact(state.ground_map, 4, 3, interactables=state.interactables)
        assert state.player.turn_number == initial_turn + 1

    def test_interact_looted_container_fails(self):
        """Cannot interact with already-looted container."""
        state = self._make_state_with_container()
        state.interactables[0].loot()  # Pre-loot
        success, msg = state.player.interact(
            state.ground_map, 4, 3, interactables=state.interactables
        )
        assert not success

    def test_interact_not_adjacent_fails(self):
        """Cannot interact with distant container."""
        state = self._make_state_with_container(
            player_x=1, player_y=1, container_x=5, container_y=5,
        )
        success, msg = state.player.interact(
            state.ground_map, 5, 5, interactables=state.interactables
        )
        assert not success
        assert "too far" in msg.lower()

    def test_door_still_works(self):
        """Door interaction still works with interactables parameter."""
        gmap = _make_simple_map()
        # Place a door at (3, 2)
        gmap.tiles[2][3] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        player = GroundPlayerState(x=3, y=1)
        success, msg = player.interact(gmap, 3, 2, interactables=[])
        assert success
        assert gmap.tiles[2][3].tile_type == TileType.DOOR_OPEN

    def test_backwards_compatible_no_interactables_param(self):
        """interact() still works without interactables parameter."""
        gmap = _make_simple_map()
        gmap.tiles[2][3] = GroundTile(tile_type=TileType.DOOR_CLOSED)
        player = GroundPlayerState(x=3, y=1)
        success, msg = player.interact(gmap, 3, 2)
        assert success
