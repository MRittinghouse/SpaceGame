"""Tests for galaxy event system — events that reshape gameplay dynamics."""

import pytest
from spacegame.models.galaxy_event import (
    GalaxyEvent,
    GalaxyEventType,
    GalaxyEventGenerator,
)
from spacegame.config import (
    GALAXY_EVENT_DAILY_CHANCE,
    GALAXY_EVENT_MAX_ACTIVE,
    GALAXY_EVENT_MIN_DURATION,
    GALAXY_EVENT_MAX_DURATION,
)


def _make_event(
    event_type: GalaxyEventType = GalaxyEventType.EMBARGO,
    system_id: str = "nexus_prime",
    day_started: int = 1,
    duration_days: int = 5,
    **kwargs: object,
) -> GalaxyEvent:
    defaults = dict(
        id="test_event",
        event_type=event_type,
        system_id=system_id,
        faction_id="commerce_guild",
        description="Test event",
        flavor_text="Test flavor",
        day_started=day_started,
        duration_days=duration_days,
        blocked_commodities=[],
        price_modifiers={},
        shutdown_tags=[],
        encounter_chance_modifier=1.0,
        danger_modifier=0,
        rep_bonus_faction="",
        rep_bonus_amount=0,
        skill_opportunity="",
    )
    defaults.update(kwargs)
    return GalaxyEvent(**defaults)


# === GalaxyEvent Dataclass ===


class TestGalaxyEventBasics:
    """GalaxyEvent should track active state and serialize correctly."""

    def test_is_active_within_duration(self) -> None:
        event = _make_event(day_started=1, duration_days=5)
        assert event.is_active(1) is True
        assert event.is_active(3) is True
        assert event.is_active(5) is True

    def test_is_active_expired(self) -> None:
        event = _make_event(day_started=1, duration_days=5)
        assert event.is_active(6) is False
        assert event.is_active(10) is False

    def test_days_remaining(self) -> None:
        event = _make_event(day_started=1, duration_days=5)
        assert event.days_remaining(1) == 5
        assert event.days_remaining(3) == 3
        assert event.days_remaining(6) == 0

    def test_to_dict_round_trip(self) -> None:
        event = _make_event(
            blocked_commodities=["raw_ore", "iron_ore"],
            price_modifiers={"food": 1.5},
            chain_id="test_chain",
            chain_step=1,
        )
        data = event.to_dict()
        restored = GalaxyEvent.from_dict(data)
        assert restored.id == event.id
        assert restored.event_type == event.event_type
        assert restored.blocked_commodities == ["raw_ore", "iron_ore"]
        assert restored.price_modifiers == {"food": 1.5}
        assert restored.chain_id == "test_chain"
        assert restored.chain_step == 1

    def test_event_type_values(self) -> None:
        assert GalaxyEventType.EMBARGO.value == "embargo"
        assert GalaxyEventType.FESTIVAL.value == "festival"
        assert GalaxyEventType.LABOR_STRIKE.value == "labor_strike"
        assert GalaxyEventType.RESEARCH_BREAKTHROUGH.value == "research_breakthrough"
        assert GalaxyEventType.PIRATE_SURGE.value == "pirate_surge"


# === Embargo Effects ===


class TestEmbargoEvent:
    """Embargo events should block specific commodities."""

    def test_embargo_has_blocked_commodities(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.EMBARGO,
            blocked_commodities=["raw_ore", "iron_ore", "common_metals"],
        )
        assert "raw_ore" in event.blocked_commodities
        assert "iron_ore" in event.blocked_commodities
        assert "food" not in event.blocked_commodities

    def test_embargo_skill_opportunity(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.EMBARGO,
            skill_opportunity="scan_evasion",
        )
        assert event.skill_opportunity == "scan_evasion"


# === Festival Effects ===


class TestFestivalEvent:
    """Festival events should grant rep bonuses and modify prices."""

    def test_festival_has_rep_bonus(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.FESTIVAL,
            rep_bonus_faction="miners_union",
            rep_bonus_amount=2,
        )
        assert event.rep_bonus_faction == "miners_union"
        assert event.rep_bonus_amount == 2

    def test_festival_price_modifiers(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.FESTIVAL,
            price_modifiers={"textiles": 1.8, "food": 1.4, "art": 2.0},
        )
        assert event.price_modifiers["textiles"] == 1.8
        assert event.price_modifiers["art"] == 2.0


# === Labor Strike Effects ===


class TestLaborStrikeEvent:
    """Labor strike events should shut down production tags."""

    def test_strike_has_shutdown_tags(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.LABOR_STRIKE,
            shutdown_tags=["raw_materials", "mining"],
        )
        assert "raw_materials" in event.shutdown_tags
        assert "mining" in event.shutdown_tags


# === Pirate Surge Effects ===


class TestPirateSurgeEvent:
    """Pirate surge events should increase encounter chance."""

    def test_pirate_surge_modifier(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.PIRATE_SURGE,
            encounter_chance_modifier=1.5,
            danger_modifier=1,
        )
        assert event.encounter_chance_modifier == 1.5
        assert event.danger_modifier == 1


# === GalaxyEventGenerator ===


class TestGalaxyEventGenerator:
    """Generator should produce events from templates with deterministic seeding."""

    def _make_generator(self) -> GalaxyEventGenerator:
        templates = [
            {
                "id": "test_embargo",
                "event_type": "embargo",
                "faction_id": "commerce_guild",
                "target_systems": ["nexus_prime", "stellaris_port"],
                "blocked_commodities": ["raw_ore", "iron_ore"],
                "descriptions": ["Guild embargoes Union ore"],
                "flavor_texts": ["Empty cargo holds everywhere."],
                "duration_min": 3,
                "duration_max": 6,
                "skill_opportunity": "scan_evasion",
                "weight": 10,
            },
            {
                "id": "test_festival",
                "event_type": "festival",
                "faction_id": "miners_union",
                "target_systems": ["breakstone"],
                "price_modifiers": {"food": 1.4},
                "rep_bonus_faction": "miners_union",
                "rep_bonus_amount": 2,
                "descriptions": ["Founders' Day at Breakstone"],
                "flavor_texts": ["Mining shanties echo."],
                "duration_min": 2,
                "duration_max": 4,
                "skill_opportunity": "persuasion_bonus",
                "weight": 8,
            },
        ]
        return GalaxyEventGenerator(templates)

    def test_generator_respects_max_active(self) -> None:
        gen = self._make_generator()
        # Force-inject 2 active events
        active: dict[str, list[GalaxyEvent]] = {
            "nexus_prime": [_make_event(day_started=1, duration_days=10)],
            "breakstone": [_make_event(day_started=1, duration_days=10)],
        }
        result = gen.try_generate_event(5, active)
        assert result is None

    def test_generator_deterministic(self) -> None:
        gen = self._make_generator()
        active: dict[str, list[GalaxyEvent]] = {}
        # Force chance to succeed by calling many days
        results = []
        for day in range(1, 200):
            event = gen.try_generate_event(day, active)
            if event:
                results.append((day, event.id, event.system_id))
                break
        # Same generator, same seed should produce same result
        gen2 = self._make_generator()
        results2 = []
        for day in range(1, 200):
            event = gen2.try_generate_event(day, {})
            if event:
                results2.append((day, event.id, event.system_id))
                break
        assert results == results2

    def test_generator_produces_valid_event(self) -> None:
        gen = self._make_generator()
        # Try many days until we get an event
        for day in range(1, 500):
            event = gen.try_generate_event(day, {})
            if event:
                assert isinstance(event, GalaxyEvent)
                assert event.event_type in GalaxyEventType
                assert event.duration_days >= 2  # Template min can be below global
                assert event.duration_days <= GALAXY_EVENT_MAX_DURATION
                assert event.day_started == day
                assert len(event.description) > 0
                return
        pytest.fail("No event generated in 500 days")

    def test_generator_embargo_has_blocked_commodities(self) -> None:
        gen = self._make_generator()
        for day in range(1, 500):
            event = gen.try_generate_event(day, {})
            if event and event.event_type == GalaxyEventType.EMBARGO:
                assert len(event.blocked_commodities) > 0
                return
        # Okay if no embargo fires — probabilistic

    def test_generator_empty_templates_returns_none(self) -> None:
        gen = GalaxyEventGenerator([])
        result = gen.try_generate_event(1, {})
        assert result is None

    def test_generator_festival_has_rep_bonus(self) -> None:
        gen = self._make_generator()
        for day in range(1, 500):
            event = gen.try_generate_event(day, {})
            if event and event.event_type == GalaxyEventType.FESTIVAL:
                assert event.rep_bonus_amount > 0
                assert len(event.rep_bonus_faction) > 0
                return


# === Serialization ===


class TestGalaxyEventSerialization:
    """Full round-trip serialization for all event types."""

    def test_embargo_round_trip(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.EMBARGO,
            blocked_commodities=["raw_ore", "iron_ore"],
            skill_opportunity="scan_evasion",
        )
        restored = GalaxyEvent.from_dict(event.to_dict())
        assert restored.event_type == GalaxyEventType.EMBARGO
        assert restored.blocked_commodities == ["raw_ore", "iron_ore"]

    def test_festival_round_trip(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.FESTIVAL,
            price_modifiers={"food": 1.4, "art": 2.0},
            rep_bonus_faction="miners_union",
            rep_bonus_amount=2,
        )
        restored = GalaxyEvent.from_dict(event.to_dict())
        assert restored.price_modifiers == {"food": 1.4, "art": 2.0}
        assert restored.rep_bonus_faction == "miners_union"

    def test_labor_strike_round_trip(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.LABOR_STRIKE,
            shutdown_tags=["raw_materials", "mining"],
        )
        restored = GalaxyEvent.from_dict(event.to_dict())
        assert restored.shutdown_tags == ["raw_materials", "mining"]

    def test_pirate_surge_round_trip(self) -> None:
        event = _make_event(
            event_type=GalaxyEventType.PIRATE_SURGE,
            encounter_chance_modifier=1.5,
            danger_modifier=1,
        )
        restored = GalaxyEvent.from_dict(event.to_dict())
        assert restored.encounter_chance_modifier == 1.5
        assert restored.danger_modifier == 1

    def test_chain_fields_round_trip(self) -> None:
        event = _make_event(chain_id="strike_cascade", chain_step=2)
        restored = GalaxyEvent.from_dict(event.to_dict())
        assert restored.chain_id == "strike_cascade"
        assert restored.chain_step == 2
