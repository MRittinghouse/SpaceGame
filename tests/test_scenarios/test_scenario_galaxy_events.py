"""Scenario I: Galaxy event generation + chain progression.

Galaxy events are a recently-added layer: templates produce events that expire
after N days. Some events have chain follow-ups — when one expires, another
gets queued to fire after a delay.

This scenario verifies:
  - Events are built correctly from templates
  - Expiry uses ``is_active(current_day)`` correctly
  - Chain triggers enqueue the follow-up on expiry
  - The follow-up fires when the delay has elapsed
  - Max-active-event cap is respected
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.galaxy_event import (
    GALAXY_EVENT_MAX_ACTIVE,
    GalaxyEvent,
    GalaxyEventGenerator,
    GalaxyEventType,
)


def _generator() -> GalaxyEventGenerator:
    dl = get_data_loader()
    dl.load_all()
    return GalaxyEventGenerator(
        templates=dl.galaxy_event_templates,
        chains=dl.galaxy_event_chains,
    )


class TestEventBuilding:
    def test_build_from_template_produces_valid_event(self) -> None:
        gen = _generator()
        dl = get_data_loader()
        template = dl.galaxy_event_templates[0]

        event = gen._build_event_from_template(template, current_day=10)

        assert isinstance(event, GalaxyEvent)
        assert event.day_started == 10
        assert event.duration_days > 0
        assert event.event_type == GalaxyEventType(template["event_type"])
        # Event ID format: template_id + day
        assert event.id.startswith(template["id"])

    def test_event_active_while_within_duration(self) -> None:
        gen = _generator()
        dl = get_data_loader()
        template = dl.galaxy_event_templates[0]

        event = gen._build_event_from_template(template, current_day=100)

        # Active on start day and mid-duration
        assert event.is_active(100) is True
        assert event.is_active(100 + event.duration_days - 1) is True

        # Inactive once duration elapses
        assert event.is_active(100 + event.duration_days) is False
        assert event.is_active(100 + event.duration_days + 5) is False

    def test_days_remaining_counts_down(self) -> None:
        gen = _generator()
        dl = get_data_loader()
        template = dl.galaxy_event_templates[0]
        event = gen._build_event_from_template(template, current_day=50)

        # Mid-duration
        assert event.days_remaining(50) == event.duration_days
        assert event.days_remaining(50 + 1) == event.duration_days - 1

        # Expired — clamps at 0, does not go negative
        assert event.days_remaining(100 + event.duration_days) == 0


class TestChainTriggering:
    """The strike_cascade chain has step 0 (breakstone_strike) → step 1
    (forgeworks_shortage) after 2 days. Verify the enqueue + fire contract."""

    def test_expired_chain_event_enqueues_followup(self) -> None:
        gen = _generator()
        dl = get_data_loader()

        # Build a step-0 event manually (not via roll)
        step0_template = next(
            t for t in dl.galaxy_event_templates if t["id"] == "breakstone_strike"
        )
        event = gen._build_event_from_template(step0_template, current_day=10)
        # Attach chain metadata as the live system would
        event.chain_id = "strike_cascade"
        event.chain_step = 0

        # Pending queue starts empty
        assert gen._pending_chain_events == []

        # Expire the event — chain follow-up should enqueue
        gen.check_chain_triggers(event, current_day=15)

        assert len(gen._pending_chain_events) == 1
        fire_day, event_id = gen._pending_chain_events[0]
        assert event_id == "forgeworks_shortage", "Chain step 1 must enqueue"
        assert fire_day == 15 + 2, "delay_days=2 per chain spec"

    def test_followup_fires_when_delay_elapses(self) -> None:
        gen = _generator()
        dl = get_data_loader()
        step0_template = next(
            t for t in dl.galaxy_event_templates if t["id"] == "breakstone_strike"
        )
        event = gen._build_event_from_template(step0_template, current_day=10)
        event.chain_id = "strike_cascade"
        event.chain_step = 0
        gen.check_chain_triggers(event, current_day=15)

        # Before the delay elapses: no event fires
        assert gen._try_fire_chain_event(current_day=15) is None
        assert gen._try_fire_chain_event(current_day=16) is None

        # On fire_day: event fires and is removed from pending
        fired = gen._try_fire_chain_event(current_day=17)
        assert fired is not None
        assert fired.id.startswith("forgeworks_shortage")
        assert gen._pending_chain_events == []

    def test_non_chained_event_expiry_is_noop(self) -> None:
        """An expired event without a chain_id must not affect the queue."""
        gen = _generator()
        event = GalaxyEvent(
            id="standalone_1",
            event_type=GalaxyEventType.EMBARGO,
            system_id="nexus_prime",
            faction_id="commerce_guild",
            description="",
            flavor_text="",
            day_started=10,
            duration_days=5,
        )
        assert event.chain_id == ""
        gen.check_chain_triggers(event, current_day=15)
        assert gen._pending_chain_events == []


class TestGenerationCap:
    """The max-active cap prevents event explosion."""

    def test_try_generate_respects_max_active_cap(self) -> None:
        gen = _generator()

        # Fill active events to the cap
        full_active = {
            "nexus_prime": [
                GalaxyEvent(
                    id=f"fill_{i}",
                    event_type=GalaxyEventType.EMBARGO,
                    system_id="nexus_prime",
                    faction_id="commerce_guild",
                    description="",
                    flavor_text="",
                    day_started=1,
                    duration_days=10,
                )
                for i in range(GALAXY_EVENT_MAX_ACTIVE)
            ]
        }

        event = gen.try_generate_event(current_day=100, active_events=full_active)
        assert event is None, (
            "Cap exceeded — no new event should generate when the cap is full"
        )

    def test_chain_event_bypasses_cap(self) -> None:
        """Chain events fire regardless of cap — otherwise chain continuity
        breaks when the global is busy."""
        gen = _generator()
        # Enqueue a chain event directly (skip the _expire step)
        gen._pending_chain_events.append((50, "forgeworks_shortage"))

        # Even with active map "at cap," chain should fire
        full_active = {
            "nexus_prime": [
                GalaxyEvent(
                    id=f"fill_{i}",
                    event_type=GalaxyEventType.EMBARGO,
                    system_id="nexus_prime",
                    faction_id="commerce_guild",
                    description="",
                    flavor_text="",
                    day_started=1,
                    duration_days=10,
                )
                for i in range(GALAXY_EVENT_MAX_ACTIVE)
            ]
        }
        fired = gen.try_generate_event(current_day=50, active_events=full_active)
        assert fired is not None, "Chain events should fire even at cap"
        assert fired.id.startswith("forgeworks_shortage")


class TestDeterministicGeneration:
    """Event generation must be deterministic per game-day seed — critical
    for reproducible saves."""

    def test_same_day_produces_same_event_decision(self) -> None:
        gen_a = _generator()
        gen_b = _generator()
        empty_active: dict[str, list[GalaxyEvent]] = {}

        event_a = gen_a.try_generate_event(current_day=42, active_events=empty_active)
        event_b = gen_b.try_generate_event(current_day=42, active_events=empty_active)

        # Either both None or both the same event
        if event_a is None:
            assert event_b is None, "Determinism — same day must produce same result"
        else:
            assert event_b is not None
            # ID will include the day — stable
            assert event_a.id == event_b.id


class TestDataIntegrity:
    """Template + chain references must be consistent."""

    def test_all_chain_step_event_ids_exist_in_templates(self) -> None:
        dl = get_data_loader()
        template_ids = {t["id"] for t in dl.galaxy_event_templates}
        errors = []
        for chain in dl.galaxy_event_chains:
            for step in chain.get("steps", []):
                eid = step.get("event_id")
                if eid and eid not in template_ids:
                    errors.append(
                        f"Chain '{chain.get('chain_id')}' step {step.get('step')} "
                        f"references unknown event_id '{eid}'"
                    )
        assert not errors, "\n".join(errors)
