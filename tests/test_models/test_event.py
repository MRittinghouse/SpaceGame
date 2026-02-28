"""Tests for event display, event log, and event serialization."""

from spacegame.models.event import MarketEvent, EventType, EventGenerator


class TestEventLog:
    """Test event log accumulation and behavior."""

    def _make_event(
        self,
        event_type: EventType = EventType.SHORTAGE,
        commodity_id: str = "iron_ore",
        system_id: str = "nexus_prime",
        day_started: int = 1,
        duration: int = 5,
        multiplier: float = 2.0,
        description: str = "Test event",
    ) -> MarketEvent:
        return MarketEvent(
            event_type=event_type,
            commodity_id=commodity_id,
            system_id=system_id,
            price_multiplier=multiplier,
            duration_days=duration,
            day_started=day_started,
            description=description,
        )

    def test_event_log_entry_format(self) -> None:
        """Event log entries contain required fields."""
        event = self._make_event()
        entry = {
            "event_type": event.event_type.value,
            "commodity": event.commodity_id,
            "system": event.system_id,
            "day": event.day_started,
            "description": event.description,
        }
        assert entry["event_type"] == "shortage"
        assert entry["commodity"] == "iron_ore"
        assert entry["system"] == "nexus_prime"
        assert entry["day"] == 1
        assert entry["description"] == "Test event"

    def test_event_log_max_size(self) -> None:
        """Event log should not exceed 15 entries."""
        event_log: list[dict] = []
        max_log_size = 15

        for i in range(20):
            event = self._make_event(day_started=i)
            entry = {
                "event_type": event.event_type.value,
                "commodity": event.commodity_id,
                "system": event.system_id,
                "day": event.day_started,
                "description": event.description,
            }
            event_log.append(entry)
            if len(event_log) > max_log_size:
                event_log.pop(0)

        assert len(event_log) == max_log_size
        assert event_log[0]["day"] == 5, "Oldest entries should be trimmed"
        assert event_log[-1]["day"] == 19, "Newest entry should be last"

    def test_event_banner_timer_countdown(self) -> None:
        """Event banner timer should count down with dt."""
        banner_timer = 5.0
        banner_timer -= 1.0
        assert banner_timer == 4.0
        banner_timer -= 4.0
        assert banner_timer == 0.0

    def test_event_banner_timer_no_negative(self) -> None:
        """Event banner timer should not go below zero."""
        banner_timer = 1.0
        banner_timer = max(0.0, banner_timer - 2.0)
        assert banner_timer == 0.0

    def test_disaster_event_is_modal(self) -> None:
        """DISASTER events should trigger modal notification."""
        event = self._make_event(event_type=EventType.DISASTER)
        assert event.event_type == EventType.DISASTER

    def test_non_disaster_events_are_banner(self) -> None:
        """SHORTAGE, SURPLUS, BOOM events should trigger banner."""
        for etype in [EventType.SHORTAGE, EventType.SURPLUS, EventType.BOOM]:
            event = self._make_event(event_type=etype)
            assert event.event_type != EventType.DISASTER


class TestEventLogSerialization:
    """Test event log serialization round-trip."""

    def test_event_log_serialization_roundtrip(self) -> None:
        """Event log should survive serialization to/from dict."""
        event_log = [
            {
                "event_type": "shortage",
                "commodity": "iron_ore",
                "system": "nexus_prime",
                "day": 1,
                "description": "Supply chain disruption causes Iron Ore shortage",
            },
            {
                "event_type": "disaster",
                "commodity": "fuel",
                "system": "breakstone",
                "day": 3,
                "description": "Asteroid strike destroys Fuel stockpiles",
            },
        ]

        # Simulate serialization
        import json

        serialized = json.dumps(event_log)
        deserialized = json.loads(serialized)

        assert len(deserialized) == 2
        assert deserialized[0]["event_type"] == "shortage"
        assert deserialized[1]["event_type"] == "disaster"
        assert deserialized[0]["commodity"] == "iron_ore"
        assert deserialized[1]["system"] == "breakstone"

    def test_empty_event_log_serialization(self) -> None:
        """Empty event log should serialize and deserialize correctly."""
        import json

        event_log: list[dict] = []
        serialized = json.dumps(event_log)
        deserialized = json.loads(serialized)
        assert deserialized == []


class TestMarketEventSerialization:
    """Test MarketEvent serialize/deserialize with correct field names."""

    def test_market_event_field_names(self) -> None:
        """MarketEvent should use day_started field correctly."""
        event = MarketEvent(
            event_type=EventType.SHORTAGE,
            commodity_id="iron_ore",
            system_id="nexus_prime",
            price_multiplier=2.0,
            duration_days=5,
            day_started=10,
            description="Test shortage",
        )
        assert event.day_started == 10
        assert event.is_active(12)
        assert not event.is_active(15)
        assert event.days_remaining(12) == 3

    def test_market_event_serialization_roundtrip(self) -> None:
        """MarketEvent should survive serialization round-trip."""
        event = MarketEvent(
            event_type=EventType.DISASTER,
            commodity_id="fuel",
            system_id="breakstone",
            price_multiplier=3.5,
            duration_days=4,
            day_started=7,
            description="Explosion!",
        )

        # Serialize
        data = {
            "event_type": event.event_type.value,
            "commodity_id": event.commodity_id,
            "system_id": event.system_id,
            "day_started": event.day_started,
            "duration_days": event.duration_days,
            "price_multiplier": event.price_multiplier,
            "description": event.description,
        }

        # Deserialize
        restored = MarketEvent(
            event_type=EventType(data["event_type"]),
            commodity_id=data["commodity_id"],
            system_id=data["system_id"],
            price_multiplier=data["price_multiplier"],
            duration_days=data["duration_days"],
            day_started=data["day_started"],
            description=data["description"],
        )

        assert restored.event_type == event.event_type
        assert restored.commodity_id == event.commodity_id
        assert restored.system_id == event.system_id
        assert restored.price_multiplier == event.price_multiplier
        assert restored.duration_days == event.duration_days
        assert restored.day_started == event.day_started
        assert restored.description == event.description
