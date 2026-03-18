"""Tests for galaxy event integration — data loading, game loop, and save/load."""

import json
import pytest
from pathlib import Path
from typing import Any

from spacegame.models.galaxy_event import (
    GalaxyEvent,
    GalaxyEventType,
    GalaxyEventGenerator,
)
from spacegame.config import (
    GALAXY_EVENT_DAILY_CHANCE,
    GALAXY_EVENT_MAX_ACTIVE,
)


# === DataLoader: load_galaxy_events ===


class TestLoadGalaxyEvents:
    """DataLoader should parse galaxy_events.json into template list."""

    def test_load_galaxy_events_returns_templates(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        templates = dl.galaxy_event_templates
        assert isinstance(templates, list)
        assert len(templates) >= 15  # We have 17 templates

    def test_each_template_has_required_fields(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for t in dl.galaxy_event_templates:
            assert "id" in t, f"Template missing id"
            assert "event_type" in t, f"{t.get('id')} missing event_type"
            assert "target_systems" in t, f"{t.get('id')} missing target_systems"
            assert "descriptions" in t, f"{t.get('id')} missing descriptions"
            assert "weight" in t, f"{t.get('id')} missing weight"

    def test_template_event_types_are_valid(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        valid_types = {e.value for e in GalaxyEventType}
        for t in dl.galaxy_event_templates:
            assert t["event_type"] in valid_types, (
                f"{t['id']} has invalid event_type: {t['event_type']}"
            )

    def test_event_chains_loaded(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        assert isinstance(dl.galaxy_event_chains, list)
        assert len(dl.galaxy_event_chains) >= 1

    def test_chain_has_required_fields(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        for chain in dl.galaxy_event_chains:
            assert "chain_id" in chain
            assert "steps" in chain


# === Save/Load Round-Trip ===


class TestGalaxyEventSaveLoad:
    """Galaxy events should survive save/load cycle."""

    def _make_event(self, **kwargs: Any) -> GalaxyEvent:
        defaults = dict(
            id="test_event_42",
            event_type=GalaxyEventType.EMBARGO,
            system_id="nexus_prime",
            faction_id="commerce_guild",
            description="Guild embargo on ore",
            flavor_text="Empty cargo holds.",
            day_started=10,
            duration_days=5,
            blocked_commodities=["raw_ore", "iron_ore"],
            price_modifiers={},
            shutdown_tags=[],
            encounter_chance_modifier=1.0,
            danger_modifier=0,
            rep_bonus_faction="",
            rep_bonus_amount=0,
            skill_opportunity="scan_evasion",
            chain_id="strike_cascade",
            chain_step=0,
        )
        defaults.update(kwargs)
        return GalaxyEvent(**defaults)

    def test_serialize_galaxy_events(self) -> None:
        """Active galaxy events should serialize to list of dicts."""
        events: dict[str, list[GalaxyEvent]] = {
            "nexus_prime": [self._make_event()],
        }
        serialized = _serialize_galaxy_events(events)
        assert "nexus_prime" in serialized
        assert len(serialized["nexus_prime"]) == 1
        assert serialized["nexus_prime"][0]["id"] == "test_event_42"

    def test_deserialize_galaxy_events(self) -> None:
        """Serialized galaxy events should restore correctly."""
        events: dict[str, list[GalaxyEvent]] = {
            "nexus_prime": [self._make_event()],
            "breakstone": [
                self._make_event(
                    id="strike_1",
                    event_type=GalaxyEventType.LABOR_STRIKE,
                    system_id="breakstone",
                    shutdown_tags=["raw_materials"],
                    blocked_commodities=[],
                ),
            ],
        }
        serialized = _serialize_galaxy_events(events)
        restored = _deserialize_galaxy_events(serialized)
        assert len(restored) == 2
        assert len(restored["nexus_prime"]) == 1
        assert restored["nexus_prime"][0].id == "test_event_42"
        assert restored["nexus_prime"][0].event_type == GalaxyEventType.EMBARGO
        assert restored["nexus_prime"][0].blocked_commodities == ["raw_ore", "iron_ore"]
        assert restored["breakstone"][0].shutdown_tags == ["raw_materials"]

    def test_deserialize_empty(self) -> None:
        """Empty or missing galaxy events should return empty dict."""
        assert _deserialize_galaxy_events({}) == {}
        assert _deserialize_galaxy_events(None) == {}

    def test_round_trip_multiple_events_per_system(self) -> None:
        """Multiple events in a single system should round-trip."""
        events: dict[str, list[GalaxyEvent]] = {
            "nexus_prime": [
                self._make_event(id="evt_1"),
                self._make_event(id="evt_2", event_type=GalaxyEventType.FESTIVAL),
            ],
        }
        serialized = _serialize_galaxy_events(events)
        restored = _deserialize_galaxy_events(serialized)
        assert len(restored["nexus_prime"]) == 2
        ids = {e.id for e in restored["nexus_prime"]}
        assert ids == {"evt_1", "evt_2"}


# === Day Advance Integration ===


class TestGalaxyEventDayAdvance:
    """Galaxy events should be generated and cleaned up during day advance."""

    def test_expired_events_cleaned_up(self) -> None:
        """Events past their duration should be removed."""
        event = GalaxyEvent(
            id="expired_test",
            event_type=GalaxyEventType.EMBARGO,
            system_id="nexus_prime",
            faction_id="commerce_guild",
            description="Old embargo",
            flavor_text="Gone now.",
            day_started=1,
            duration_days=3,
            blocked_commodities=["raw_ore"],
        )
        active: dict[str, list[GalaxyEvent]] = {"nexus_prime": [event]}
        current_day = 10  # Well past expiry
        # Clean up expired
        for sid in list(active.keys()):
            active[sid] = [e for e in active[sid] if e.is_active(current_day)]
            if not active[sid]:
                del active[sid]
        assert "nexus_prime" not in active

    def test_active_events_kept(self) -> None:
        """Events within duration should not be removed."""
        event = GalaxyEvent(
            id="active_test",
            event_type=GalaxyEventType.FESTIVAL,
            system_id="breakstone",
            faction_id="miners_union",
            description="Festival ongoing",
            flavor_text="Party!",
            day_started=5,
            duration_days=10,
        )
        active: dict[str, list[GalaxyEvent]] = {"breakstone": [event]}
        current_day = 8
        for sid in list(active.keys()):
            active[sid] = [e for e in active[sid] if e.is_active(current_day)]
            if not active[sid]:
                del active[sid]
        assert "breakstone" in active
        assert len(active["breakstone"]) == 1

    def test_generator_integrated_with_active_count(self) -> None:
        """Generator should respect active event count from all systems."""
        templates = [
            {
                "id": "test_embargo",
                "event_type": "embargo",
                "faction_id": "commerce_guild",
                "target_systems": ["nexus_prime"],
                "blocked_commodities": ["raw_ore"],
                "descriptions": ["Test embargo"],
                "flavor_texts": ["Test flavor"],
                "duration_min": 3,
                "duration_max": 6,
                "skill_opportunity": "scan_evasion",
                "weight": 10,
            },
        ]
        gen = GalaxyEventGenerator(templates)
        # Fill up active events to max
        active: dict[str, list[GalaxyEvent]] = {}
        for i in range(GALAXY_EVENT_MAX_ACTIVE):
            sid = f"system_{i}"
            active[sid] = [
                GalaxyEvent(
                    id=f"fill_{i}",
                    event_type=GalaxyEventType.EMBARGO,
                    system_id=sid,
                    faction_id="test",
                    description="Filler",
                    flavor_text="",
                    day_started=1,
                    duration_days=100,
                )
            ]
        # Should not generate when at max
        for day in range(1, 500):
            result = gen.try_generate_event(day, active)
            assert result is None


# === Helper functions matching save_manager pattern ===


def _serialize_galaxy_events(
    events: dict[str, list[GalaxyEvent]],
) -> dict[str, list[dict[str, Any]]]:
    """Serialize active galaxy events for save system."""
    result: dict[str, list[dict[str, Any]]] = {}
    for system_id, event_list in events.items():
        result[system_id] = [e.to_dict() for e in event_list]
    return result


def _deserialize_galaxy_events(
    data: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[GalaxyEvent]]:
    """Deserialize active galaxy events from save system."""
    if not data:
        return {}
    result: dict[str, list[GalaxyEvent]] = {}
    for system_id, event_dicts in data.items():
        result[system_id] = [GalaxyEvent.from_dict(d) for d in event_dicts]
    return result
