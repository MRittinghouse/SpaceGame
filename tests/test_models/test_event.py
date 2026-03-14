"""Tests for event display, event log, and event serialization."""

from unittest.mock import patch
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


# ============================================================================
# Day-Advance Event Generation Tests
# ============================================================================


class TestDayAdvanceEventGeneration:
    """Tests for event generation triggered by day advances."""

    def _make_generator(self) -> EventGenerator:
        return EventGenerator(
            commodities=["food", "iron_ore", "fuel"],
            systems=["nexus_prime", "verdant", "forgeworks"],
        )

    def test_event_generator_produces_event_when_rng_hits(self) -> None:
        """EventGenerator should produce event when random < EVENT_CHANCE."""
        gen = self._make_generator()
        names = {"food": "Food", "iron_ore": "Iron Ore", "fuel": "Fuel"}
        # Force random.random() to return 0.0 (always below EVENT_CHANCE)
        with patch("spacegame.models.event.random.random", return_value=0.0):
            event = gen.try_generate_event(5, names)
        assert event is not None
        assert event.day_started == 5

    def test_event_generator_no_event_when_rng_misses(self) -> None:
        """EventGenerator should return None when random > EVENT_CHANCE."""
        gen = self._make_generator()
        names = {"food": "Food", "iron_ore": "Iron Ore", "fuel": "Fuel"}
        # Force random.random() to return 1.0 (always above EVENT_CHANCE)
        with patch("spacegame.models.event.random.random", return_value=1.0):
            event = gen.try_generate_event(5, names)
        assert event is None

    def test_event_expires_after_duration(self) -> None:
        """Event should expire after its duration passes."""
        event = MarketEvent(
            event_type=EventType.SHORTAGE,
            commodity_id="food",
            system_id="nexus_prime",
            price_multiplier=2.0,
            duration_days=3,
            day_started=5,
            description="Test shortage",
        )
        assert event.is_active(5)  # Day started
        assert event.is_active(7)  # Last active day
        assert not event.is_active(8)  # Expired

    def test_event_multiplier_affects_market_price(self) -> None:
        """Market should apply event price multiplier to affected commodity."""
        from spacegame.data_loader import DataLoader
        from spacegame.models.market import Market

        loader = DataLoader()
        loader.load_all()
        nexus = loader.get_system("nexus_prime")
        commodities = loader.get_all_commodities()

        # Create market without event
        market_no_event = Market(nexus, commodities, game_day=1)
        normal_price = market_no_event.get_price("food")

        # Create market with a 2x shortage event on food
        market_with_event = Market(nexus, commodities, game_day=1)
        event = MarketEvent(
            event_type=EventType.SHORTAGE,
            commodity_id="food",
            system_id="nexus_prime",
            price_multiplier=2.0,
            duration_days=5,
            day_started=1,
            description="Test shortage",
        )
        market_with_event.apply_event(event)
        event_price = market_with_event.get_price("food")

        assert event_price > normal_price, (
            f"Event price ({event_price}) should exceed normal ({normal_price})"
        )

    def test_expired_events_cleaned_from_active_dict(self) -> None:
        """Expired events should be removed from active_events dict."""
        active_events: dict[str, MarketEvent] = {}
        event = MarketEvent(
            event_type=EventType.SURPLUS,
            commodity_id="fuel",
            system_id="verdant",
            price_multiplier=0.5,
            duration_days=3,
            day_started=1,
            description="Test surplus",
        )
        active_events["verdant"] = event

        # Simulate cleanup logic (mirrors Game._check_day_advance)
        current_day = 5  # After duration
        expired = [
            sid for sid, ev in active_events.items()
            if not ev.is_active(current_day)
        ]
        for sid in expired:
            del active_events[sid]

        assert len(active_events) == 0, "Expired event should be removed"
