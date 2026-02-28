"""
Tests for the activity registry.
"""

from spacegame.engine.activity_registry import (
    ActivityDefinition,
    ActivityRegistry,
    create_default_registry,
)
from spacegame.config import GameState


class TestActivityDefinition:
    """Tests for ActivityDefinition."""

    def test_available_by_system_id(self):
        activity = ActivityDefinition(
            id="mining",
            name="Mining",
            description="Mine stuff",
            game_state=GameState.MINING,
            button_text="MINE",
            system_ids=["breakstone"],
        )
        assert activity.is_available_at("breakstone", "mining")
        assert not activity.is_available_at("nexus_prime", "trade_hub")

    def test_available_by_system_type(self):
        activity = ActivityDefinition(
            id="mining",
            name="Mining",
            description="Mine stuff",
            game_state=GameState.MINING,
            button_text="MINE",
            system_types=["mining"],
        )
        assert activity.is_available_at("any_system", "mining")
        assert not activity.is_available_at("any_system", "trade_hub")


class TestActivityRegistry:
    """Tests for ActivityRegistry."""

    def test_register_and_get(self):
        registry = ActivityRegistry()
        activity = ActivityDefinition(
            id="mining",
            name="Mining",
            description="Mine stuff",
            game_state=GameState.MINING,
            button_text="MINE",
            system_ids=["breakstone"],
        )
        registry.register(activity)
        assert registry.get_activity("mining") is not None

    def test_get_activities_for_system(self):
        registry = ActivityRegistry()
        mining = ActivityDefinition(
            id="mining",
            name="Mining",
            description="Mine stuff",
            game_state=GameState.MINING,
            button_text="MINE",
            system_ids=["breakstone"],
        )
        salvage = ActivityDefinition(
            id="salvaging",
            name="Salvaging",
            description="Salvage stuff",
            game_state=GameState.SALVAGING,
            button_text="SALVAGE",
            system_ids=["forgeworks"],
        )
        registry.register(mining)
        registry.register(salvage)

        breakstone_activities = registry.get_activities_for_system("breakstone", "mining")
        assert len(breakstone_activities) == 1
        assert breakstone_activities[0].id == "mining"

        forgeworks_activities = registry.get_activities_for_system("forgeworks", "industrial")
        assert len(forgeworks_activities) == 1
        assert forgeworks_activities[0].id == "salvaging"

    def test_no_activities(self):
        registry = ActivityRegistry()
        assert registry.get_activities_for_system("nexus_prime", "trade_hub") == []

    def test_default_registry(self):
        registry = create_default_registry()
        all_activities = registry.get_all_activities()
        assert len(all_activities) >= 3  # mining, salvaging, refining

        # Mining at breakstone
        breakstone = registry.get_activities_for_system("breakstone", "mining")
        assert any(a.id == "mining" for a in breakstone)

        # Salvaging at forgeworks
        forgeworks = registry.get_activities_for_system("forgeworks", "industrial")
        assert any(a.id == "salvaging" for a in forgeworks)

    def test_unregister(self):
        registry = ActivityRegistry()
        activity = ActivityDefinition(
            id="test",
            name="Test",
            description="Test",
            game_state=GameState.MINING,
            button_text="TEST",
        )
        registry.register(activity)
        registry.unregister("test")
        assert registry.get_activity("test") is None
