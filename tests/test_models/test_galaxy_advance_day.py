"""The galaxy-event day step, lifted from game.py (ruling P2)."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.galaxy_event import GalaxyEvent, GalaxyEventGenerator


def _generator() -> GalaxyEventGenerator:
    dl = get_data_loader()
    dl.load_all()
    return GalaxyEventGenerator(dl.galaxy_event_templates, chains=dl.galaxy_event_chains)


class TestAdvanceDay:
    def test_events_appear_and_expire(self) -> None:
        gen = _generator()
        active: dict[str, list[GalaxyEvent]] = {}
        seen = []
        for day in range(1, 201):
            new = gen.advance_day(day, active)
            if new is not None:
                seen.append(new)
            for events in active.values():
                assert all(e.is_active(day) for e in events)
        assert seen, "200 days at 4% a day produce events"

    def test_an_expired_chain_head_queues_its_follow_up(self) -> None:
        gen = _generator()
        head = gen._build_event_from_template(gen._template_by_id["breakstone_strike"], 1)
        active = {head.system_id: [head]}
        day = head.day_started + head.duration_days
        gen.advance_day(day, active)
        assert gen.pending_chains(), "the strike_cascade follow-up is pending"
