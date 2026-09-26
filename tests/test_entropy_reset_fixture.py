"""The suite-wide autouse fixture in ``tests/conftest.py`` resets SimRng entropy.

``Game.seed_rngs`` calls ``seed_entropy(seed)``. Without a reset, every later
``SimRng.from_entropy()`` in the same xdist worker replays a stream that depends
on which tests ran before it. The check runs two tests in order in an inner
pytest session that loads the real conftest: the first seeds entropy, the second
must see OS entropy restored.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest_plugins = ("pytester",)

CONFTEST = Path(__file__).resolve().parent / "conftest.py"


def test_seeded_entropy_does_not_reach_the_next_test(pytester: pytest.Pytester) -> None:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makepyfile(
        """
        from spacegame import sim_rng


        def test_a_seeds_entropy():
            sim_rng.seed_entropy(7)
            assert sim_rng._entropy_seed == 7


        def test_b_sees_os_entropy_restored():
            assert sim_rng._entropy_seed is None
            assert sim_rng._entropy_counter == 0
        """
    )
    result = pytester.runpytest_inprocess(
        "-p", "no:xdist", "-p", "no:cacheprovider", "-p", "no:asyncio"
    )
    result.assert_outcomes(passed=2)
