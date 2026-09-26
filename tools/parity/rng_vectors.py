"""SimRng vectors: the contract the GDScript twin must reproduce (SP2 spec 3.4)."""

from __future__ import annotations

from spacegame.sim_rng import SimRng
from tools.parity.driver import Case

KEYS: list[list[str | int]] = [
    ["a"],
    ["market", 1, "iron_ore", "nexus_prime"],
    ["entropy", 42, 1],
    ["Ωmega", "naïve", "星"],
    ["neg", -5],
    [""],
]

RANDINT_SPANS: list[tuple[int, int]] = [(0, 0), (1, 6), (-5, 5), (10, 1000), (0, 2**32 - 1)]


def _state(rng: SimRng) -> dict[str, object]:
    return {"s": list(rng.state())}


def build_cases() -> list[Case]:
    """One case per key, replayed in order against a single stream."""
    cases: list[Case] = []
    for index, key in enumerate(KEYS):
        rng = SimRng.from_key(*key)
        case = Case("sim_rng", f"key_{index}", {"key": list(key)})
        case.record("state", [], list(rng.state()), _state(rng))
        for _ in range(32):
            case.record("next_u32", [], rng.next_u32(), _state(rng))
        for _ in range(16):
            case.record("randf", [], rng.randf(), _state(rng))
        for lo, hi in RANDINT_SPANS:
            case.record("randint", [lo, hi], rng.randint(lo, hi), _state(rng))
        case.record("uniform", [-0.1, 0.1], rng.uniform(-0.1, 0.1), _state(rng))
        case.record("choice", [["a", "b", "c", "d"]], rng.choice(["a", "b", "c", "d"]), _state(rng))
        items = list(range(10))
        rng.shuffle(items)
        case.record("shuffle", [list(range(10))], items, _state(rng))
        case.record("sample", [list(range(10)), 4], rng.sample(list(range(10)), 4), _state(rng))
        weights = [1.0, 0.0, 3.5, 2.0]
        case.record("weighted_index", [weights], rng.weighted_index(weights), _state(rng))
        case.record(
            "choices",
            [["x", "y", "z"], [1, 2, 3], 3],
            rng.choices(["x", "y", "z"], [1, 2, 3], 3),
            _state(rng),
        )
        cases.append(case)
    return cases
