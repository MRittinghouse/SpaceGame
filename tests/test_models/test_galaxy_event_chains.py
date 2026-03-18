"""Tests for galaxy event chain system."""

from spacegame.models.galaxy_event import (
    GalaxyEvent,
    GalaxyEventType,
    GalaxyEventGenerator,
)


CHAIN_TEMPLATES = [
    {
        "id": "strike_start",
        "event_type": "labor_strike",
        "faction_id": "miners_union",
        "target_systems": ["breakstone"],
        "shutdown_tags": ["raw_materials"],
        "descriptions": ["Workers strike at Breakstone"],
        "flavor_texts": ["Silence."],
        "duration_min": 3,
        "duration_max": 3,
        "chain_id": "test_cascade",
        "chain_step": 0,
        "skill_opportunity": "",
        "weight": 0,
    },
    {
        "id": "shortage_follow",
        "event_type": "labor_strike",
        "faction_id": "miners_union",
        "target_systems": ["forgeworks"],
        "shutdown_tags": ["manufacturing"],
        "descriptions": ["Shortage hits Forgeworks"],
        "flavor_texts": ["Empty bays."],
        "duration_min": 3,
        "duration_max": 3,
        "chain_id": "test_cascade",
        "chain_step": 1,
        "skill_opportunity": "",
        "weight": 0,
    },
]

CHAIN_DEFS = [
    {
        "chain_id": "test_cascade",
        "description": "Strike cascades to shortage",
        "steps": [
            {"step": 0, "event_id": "strike_start"},
            {"step": 1, "event_id": "shortage_follow", "delay_days": 2},
        ],
    }
]


def _make_strike_event(day_started: int = 1, duration: int = 3) -> GalaxyEvent:
    return GalaxyEvent(
        id="strike_start_1",
        event_type=GalaxyEventType.LABOR_STRIKE,
        system_id="breakstone",
        faction_id="miners_union",
        description="Workers strike at Breakstone",
        flavor_text="Silence.",
        day_started=day_started,
        duration_days=duration,
        shutdown_tags=["raw_materials"],
        chain_id="test_cascade",
        chain_step=0,
    )


class TestChainTriggers:
    """Expired events should queue chain follow-ups."""

    def test_expired_chain_event_queues_follow_up(self) -> None:
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        expired = _make_strike_event(day_started=1, duration=3)
        gen.check_chain_triggers(expired, current_day=4)
        assert len(gen._pending_chain_events) == 1
        fire_day, template_id = gen._pending_chain_events[0]
        assert template_id == "shortage_follow"
        assert fire_day == 6  # day 4 + delay 2

    def test_non_chain_event_does_not_queue(self) -> None:
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        event = GalaxyEvent(
            id="random_event",
            event_type=GalaxyEventType.EMBARGO,
            system_id="nexus_prime",
            faction_id="commerce_guild",
            description="Random",
            flavor_text="",
            day_started=1,
            duration_days=3,
        )
        gen.check_chain_triggers(event, current_day=4)
        assert len(gen._pending_chain_events) == 0

    def test_chain_event_fires_on_correct_day(self) -> None:
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        expired = _make_strike_event()
        gen.check_chain_triggers(expired, current_day=4)

        # Day 5: too early
        result = gen.try_generate_event(5, {})
        assert result is None or result.chain_id != "test_cascade" or result.chain_step != 1

        # Day 6: should fire
        result = gen.try_generate_event(6, {})
        assert result is not None
        assert result.id.startswith("shortage_follow")
        assert result.chain_step == 1

    def test_chain_event_removed_after_firing(self) -> None:
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        expired = _make_strike_event()
        gen.check_chain_triggers(expired, current_day=4)
        assert len(gen._pending_chain_events) == 1

        gen.try_generate_event(6, {})
        assert len(gen._pending_chain_events) == 0

    def test_chain_bypasses_max_active_check(self) -> None:
        """Chain events should fire even when at max active events."""
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        expired = _make_strike_event()
        gen.check_chain_triggers(expired, current_day=4)

        # Fill up active events
        active = {
            "sys_a": [_make_strike_event()],
            "sys_b": [_make_strike_event()],
        }
        result = gen.try_generate_event(6, active)
        assert result is not None
        assert result.id.startswith("shortage_follow")

    def test_unknown_chain_id_is_ignored(self) -> None:
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        event = GalaxyEvent(
            id="orphan",
            event_type=GalaxyEventType.LABOR_STRIKE,
            system_id="breakstone",
            faction_id="miners_union",
            description="Orphan chain",
            flavor_text="",
            day_started=1,
            duration_days=3,
            chain_id="nonexistent_chain",
            chain_step=0,
        )
        gen.check_chain_triggers(event, current_day=4)
        assert len(gen._pending_chain_events) == 0

    def test_last_step_does_not_queue_more(self) -> None:
        """The last step in a chain should not queue anything."""
        gen = GalaxyEventGenerator(CHAIN_TEMPLATES, chains=CHAIN_DEFS)
        # Simulate the follow-up (step 1) expiring
        event = GalaxyEvent(
            id="shortage_follow_6",
            event_type=GalaxyEventType.LABOR_STRIKE,
            system_id="forgeworks",
            faction_id="miners_union",
            description="Shortage",
            flavor_text="",
            day_started=6,
            duration_days=3,
            chain_id="test_cascade",
            chain_step=1,
        )
        gen.check_chain_triggers(event, current_day=9)
        assert len(gen._pending_chain_events) == 0
