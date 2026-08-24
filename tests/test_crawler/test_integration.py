"""End-to-end integration + determinism test (QF-6, Task 14; upgraded QF-6B Task 7).

Runs the crawler with a real ``Game`` object at 2000 actions and asserts:

- The crawler itself does not raise (game crashes are recorded, not
  propagated).
- Two runs with the same seed produce structurally-identical action traces
  (same action kinds + same element types and screen positions).
- Two runs with the same seed produce identical final ``GameState``.
- Two runs with the same seed produce identical trailing samples of
  both stdlib random and numpy random.

Determinism note (QF-6B Task 7): save-slot buttons include real-world
timestamps baked into their text (e.g. "Autosave: Save 2026-08-23T19:30").
These change between runs that span a minute boundary. The trace comparison
therefore normalises action descriptions to ``ElementType@(x, y)`` so that
volatile text content (timestamps, dynamic labels) does not cause false
failures while the meaningful signal (same element at same position) is
preserved.

Per the QF-6 plan (Task 14 Gotcha) the project has no ``slow`` marker
convention, so this test is unmarked and runs as part of the suite.
Real-Game construction is heavier than a mock; the run currently
completes in ~5 seconds.
"""

from __future__ import annotations

import os
import random
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np

from tools.crawler.crawler import Crawler

# Matches the position suffix emitted by _describe_element: "@(x, y)"
_POS_RE = re.compile(r"@\((\d+), (\d+)\)$")
# Matches the element type prefix: "TypeName["
_TYPE_RE = re.compile(r"^(\w+)\[")


def _trailing_random_samples() -> tuple[float, float]:
    """Snapshot one random.random() and one np.random.random() sample."""
    return (random.random(), float(np.random.random()))


def _normalise_trace(trace: list[tuple]) -> list[tuple]:
    """Strip volatile text from click descriptions; keep kind + type + pos.

    Save-slot buttons include real-world timestamps that change between
    runs spanning a clock-minute boundary.  The normalised form is
    ``("click", "UIButton@(225, 150)")`` — type and position only.
    Keypresses and advance_time actions are returned unchanged.
    """
    result: list[tuple] = []
    for action in trace:
        if action[0] != "click":
            result.append(action)
            continue
        desc = action[1]
        pos_m = _POS_RE.search(desc)
        type_m = _TYPE_RE.match(desc)
        if pos_m and type_m:
            result.append(("click", f"{type_m.group(1)}@({pos_m.group(1)}, {pos_m.group(2)})"))
        else:
            result.append(action)
    return result


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
        """Two seeded runs produce structurally identical action traces.

        Uses checkpoint='late' (GALAXY_MAP start) so the crawler visits
        interesting states beyond MAIN_MENU.  Traces are normalised to
        element-type+position to tolerate save-slot timestamp changes
        that occur when two runs span a clock-minute boundary.
        """
        # Run A
        crawler_a = Crawler(seed=99, actions=500, checkpoint="late")
        crawler_a.run()
        trailing_a = _trailing_random_samples()

        # Run B
        crawler_b = Crawler(seed=99, actions=500, checkpoint="late")
        crawler_b.run()
        trailing_b = _trailing_random_samples()

        # Structurally identical action trace (kind + element type + position).
        norm_a = _normalise_trace(crawler_a.action_trace)
        norm_b = _normalise_trace(crawler_b.action_trace)
        assert norm_a == norm_b, (
            "action traces diverged across identically-seeded runs "
            f"(first diff at index "
            f"{next((i for i, (a, b) in enumerate(zip(norm_a, norm_b, strict=False)) if a != b), '?')})"
        )
        # Identical final state.
        state_a = crawler_a.game.state_manager.current_state
        state_b = crawler_b.game.state_manager.current_state
        assert state_a == state_b, f"final states differ: {state_a} vs {state_b}"
        # Identical trailing RNG samples for both PRNGs.
        assert trailing_a == trailing_b, (
            f"trailing RNG samples differ: {trailing_a} vs {trailing_b}"
        )
