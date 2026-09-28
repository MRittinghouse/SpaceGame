"""Game._check_day_advance's galaxy-event step, lifted onto GalaxyEventGenerator.advance_day.

Task 9 moved the generate/expire/chain step out of the inline block that used to live
directly in ``_check_day_advance`` and onto ``GalaxyEventGenerator.advance_day``.
``_check_day_advance`` now just calls it and turns a new event into a notification and
a log line. This test drives the real ``_check_day_advance`` with real models and pins
the active-event dict, the chain follow-up queue, and the notifications each day
produces. It was written against the pre-move code and passes there too, so it proves
the rewire kept the behavior.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from spacegame.data_loader import get_data_loader
from spacegame.engine.game import Game
from spacegame.models.galaxy_event import GalaxyEvent, GalaxyEventGenerator
from tests.test_scenarios._helpers import fresh_player


def _game() -> tuple[Game, GalaxyEventGenerator, dict[str, list[GalaxyEvent]]]:
    """A ``Game`` with one active event (breakstone_strike_1, duration 5) and every
    other day-advance subsystem stubbed out so only the galaxy-event step runs.
    """
    dl = get_data_loader()
    dl.load_all()
    with patch.object(Game, "__init__", lambda self: None):
        game = Game()
    game._player = fresh_player()
    game.data_loader = dl
    game.price_history = None  # type: ignore[assignment]
    game.ground_contract_manager = None
    game.smuggling_contract_manager = None
    game.politics_manager = None
    game.news_ticker = None
    game.investment_manager = None
    game.crew_roster = None
    game.ambient_dialogue = None
    game.active_events = {}
    game._ambient_idle_day_counter = 0
    game._mission_notifications = []
    game.try_generate_market_event = MagicMock()  # type: ignore[method-assign]
    game._evaluate_timed_threads = MagicMock()  # type: ignore[method-assign]
    game._tick_okafor_projects = MagicMock()  # type: ignore[method-assign]

    gen = GalaxyEventGenerator(dl.galaxy_event_templates, chains=dl.galaxy_event_chains)
    game.galaxy_event_generator = gen
    head = gen._build_event_from_template(gen._template_by_id["breakstone_strike"], 1)
    assert head.duration_days == 5
    active: dict[str, list[GalaxyEvent]] = {head.system_id: [head]}
    game.active_galaxy_events = active
    game._last_known_day = 1
    return game, gen, active


class TestCheckDayAdvanceGalaxy:
    def test_events_advance_expire_and_chain(self) -> None:
        game, gen, active = _game()

        for day in range(2, 10):
            game.player.game_day = day
            game._check_day_advance()
            assert game.active_galaxy_events is active

            if day <= 5:
                assert list(active.keys()) == ["breakstone"]
                assert [e.id for e in active["breakstone"]] == ["breakstone_strike_1"]
                assert game._mission_notifications == []
            elif day in (6, 7):
                assert active == {}
                assert gen._pending_chain_events == [(8, "forgeworks_shortage")]
                assert game._mission_notifications == []
            elif day == 8:
                assert list(active.keys()) == ["forgeworks"]
                assert len(active["forgeworks"]) == 1
                event = active["forgeworks"][0]
                assert event.id == "forgeworks_shortage_8"
                assert gen._pending_chain_events == []
                assert game._mission_notifications == [f"Galaxy Event: {event.description}"]
