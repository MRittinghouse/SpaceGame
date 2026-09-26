"""Test doubles for SimRng (SP2-a)."""

from __future__ import annotations

from collections.abc import Sequence

from spacegame.sim_rng import SimRng


class ScriptedRng(SimRng):
    """A SimRng whose ``random()`` returns scripted values in order.

    Every other draw (randint, choice, uniform, choices) uses the real
    generator seeded from ``key``, so a test controls exactly the probability
    rolls it cares about. Model code rolls chances as ``rng.random() < p``.
    """

    def __init__(self, values: Sequence[float], key: str = "scripted") -> None:
        super().__init__(*SimRng.from_key(key).state())
        self._scripted = list(values)

    def random(self) -> float:
        if not self._scripted:
            raise AssertionError("ScriptedRng ran out of scripted random() values")
        return self._scripted.pop(0)
