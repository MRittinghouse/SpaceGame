"""End-to-end integration + determinism test (QF-6, Task 14).

Runs the crawler with a real ``Game`` object at 2000 actions and asserts:

- The crawler itself does not raise (game crashes are recorded, not
  propagated).
- Two runs with the same seed produce byte-identical action traces.
- Two runs with the same seed produce identical final ``GameState``.
- Two runs with the same seed produce identical trailing samples of
  both stdlib random and numpy random.

Per the QF-6 plan (Task 14 Gotcha) the project has no ``slow`` marker
convention, so this test is unmarked and runs as part of the suite.
Real-Game construction is heavier than a mock; the run currently
completes in ~5 seconds.
"""

from __future__ import annotations

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from tools.crawler.crawler import Crawler


def _trailing_random_samples() -> tuple[float, float]:
    """Snapshot one random.random() and one np.random.random() sample."""
    return (random.random(), float(np.random.random()))


class TestCrawlerIntegration:
    def test_crawler_completes_2000_action_session_headless(self) -> None:
        crawler = Crawler(seed=42, actions=2000)
        crawler.run()
        assert len(crawler.action_trace) == 2000
        # The crawler itself should not have raised; game-side crashes go
        # into ``crawler.crashes``. We do not assert 0 crashes because a
        # real Game may legitimately surface crawler-discovered bugs; the
        # test guarantees the CRAWLER doesn't crash.

    def test_crawler_determinism_across_two_runs(self) -> None:
        # Run A
        crawler_a = Crawler(seed=99, actions=500)
        crawler_a.run()
        trailing_a = _trailing_random_samples()

        # Run B
        crawler_b = Crawler(seed=99, actions=500)
        crawler_b.run()
        trailing_b = _trailing_random_samples()

        # Byte-identical action trace.
        assert crawler_a.action_trace == crawler_b.action_trace, (
            "action traces diverged across identically-seeded runs"
        )
        # Identical final state.
        state_a = crawler_a.game.state_manager.current_state
        state_b = crawler_b.game.state_manager.current_state
        assert state_a == state_b, f"final states differ: {state_a} vs {state_b}"
        # Identical trailing RNG samples for both PRNGs.
        assert trailing_a == trailing_b, (
            f"trailing RNG samples differ: {trailing_a} vs {trailing_b}"
        )
