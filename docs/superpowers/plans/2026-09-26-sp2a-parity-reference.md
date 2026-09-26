# SP2-a Parity Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Python build a deterministic, portable reference for the Godot port: one portable random generator (`SimRng`) behind every simulation draw in `models/`, Act II v1 switched off, the procedural-mission save bug fixed, and golden traces plus a type schema recorded for the market tracer bullet.

**Architecture:** A new pygame-free module `spacegame/sim_rng.py` implements xoshiro128** seeded from the md5 of a key string; models receive it by construction (keyed streams) or injection (a constructor or function parameter that falls back to `SimRng.from_entropy()`). A new package `tools/parity/` drives model APIs with seeded inputs and writes golden JSON plus `parity/schema.json`; a determinism check proves two processes with different `PYTHONHASHSEED` values produce identical files.

**Tech Stack:** Python 3.13, pytest (with xdist), ruff, mypy with the `mypy-baseline` ratchet, `hashlib.md5`.

**Spec:** `docs/superpowers/specs/2026-09-26-sp2-foundation-design.md` (parent: `docs/superpowers/specs/2026-09-25-aurelia-overhaul-master-design.md`). Read Sections 3 to 7 and 9 of the SP2 spec before starting any task.

## Global Constraints

- Work on branch `sp2a-parity-reference` cut from `master`. Merge back with `git merge --no-ff` at the end (Task 9). Never push; pushing to `origin` is the author's call.
- Python 3.13 builtins in annotations (`dict[str, int]`, `list[str]`); every function fully typed; Google-style docstrings; ruff format at 100 columns (`CLAUDE.md`).
- Do not regenerate `mypy-baseline.txt` in any task. New code must add zero mypy errors: `python -m mypy spacegame/ | grep -v ": note:" | python -m mypy_baseline filter` must exit 0 after every task.
- `tools/parity/` is born clean: `python -m mypy tools/parity/ --follow-imports=silent` must report zero errors (same bar as `tools/crawler/`).
- SimRng key parts are `str` or `int` only; `bool`, `float`, `None` raise `TypeError` (spec 3.2).
- Every simulation draw in `spacegame/models/` goes through `SimRng`. Presentation randomness in `spacegame/views/` and `spacegame/engine/` is out of scope and stays as is, except the salted `hash()` seeds listed in Task 3.
- `ACT_TWO_V1_ENABLED` defaults to `False` and is always read through the module object (`sg_config.ACT_TWO_V1_ENABLED`), never imported by name, so the test fixture's monkeypatch is seen.
- Re-baselining rule (spec 4.4): a test may get new expected values only if it asserts a specific random outcome of a converted site; the commit message lists each such test with the site that changed it. Any other failing test is a regression and is fixed.
- Prose in docs and commit messages: no em-dashes, no "no X, no Y" constructions.
- Full gate after every task: `python -m pytest -n auto -q`, `ruff check spacegame/`, `ruff format --check spacegame/ tests/`, the mypy baseline filter above. The pre-commit hook runs the lint, format, and mypy parts on commit; it must be installed (`pre-commit install`).

## Review Focus

- **Degenerate inputs to SimRng:** `choice([])`, `sample(seq, k)` with `k > len(seq)` or `k < 0`, `weighted_index` with an empty list or all-zero weights, `randint(lo, hi)` with `hi < lo` or a span above 2^32 must raise a clear error, never return a silent default. Tests in Task 2.
- **Invalid key parts:** `bool`, `float`, and `None` in a key must raise `TypeError` naming the part; negative ints and the empty string are valid and render as `-5` and ``. Tests in Task 2.
- **An empty market and zero-price goods:** `herons_mark` stocks no commodities and quest items have `base_price` 0; the market driver must record them rather than crash or skip. Test in Task 7.
- **Non-ASCII keys:** a player named with non-ASCII characters seeds through UTF-8 md5; the vectors include a unicode key so the Godot twin is held to the same bytes. Test in Task 6.
- **Regenerating goldens from a dirty tree:** `regen` must refuse when files outside `parity/` are modified, so a golden's `source_commit` never lies. Test in Task 6.

---

## File Structure

| File | Responsibility |
|---|---|
| `spacegame/sim_rng.py` (create) | `SimRng` (xoshiro128**), `build_key`, `stable_seed`, `seed_entropy` |
| `tests/sim_rng_helpers.py` (create) | `ScriptedRng`, a test double whose `random()` returns scripted values |
| `tests/test_sim_rng.py` (create) | Known-answer and edge-case tests for `sim_rng.py` |
| `spacegame/config.py` (modify) | `ACT_TWO_V1_ENABLED = False` |
| `spacegame/data_loader.py` (modify) | Gate the five Act II loads; `load_act_two_v1()` |
| `spacegame/models/player.py` (modify) | `record_lens_action` inert when the flag is off |
| `spacegame/engine/game.py` (modify) | Gate the Act II ticks and generator; `stable_seed` replaces salted `hash()`; `seed_rngs` seeds SimRng entropy |
| `spacegame/views/galaxy_map_view.py`, `spacegame/views/combat_view.py` (modify) | `stable_seed` replaces salted `hash()` simulation seeds |
| `tests/conftest.py`, `pyproject.toml` (modify) | The `act_two_v1` marker and its autouse fixture |
| `tests/test_compliance/test_act_two_v1_switch.py` (create) | The flag's behavior |
| 24 files in `spacegame/models/` (modify) | Seeded and injected `SimRng` conversions (Tasks 3, 4) |
| `tests/test_models/test_sim_rng_sites.py` (create) | Keyed-site formulas and cross-process determinism |
| `tests/test_models/test_sim_rng_injection.py` (create) | Injected-site reproducibility |
| `tests/test_compliance/test_no_global_random_in_models.py` (create) | The scanner |
| `spacegame/models/mission.py` (modify) | Runtime missions persist through save and load |
| `tests/test_models/test_mission_runtime_persistence.py` (create) | The round trip |
| `tools/parity/__init__.py`, `driver.py`, `regen.py`, `rng_vectors.py` (create) | Golden framework, CLI, SimRng vectors |
| `tools/parity/drivers/__init__.py`, `drivers/market.py` (create) | Market and PriceHistory cases |
| `tools/parity/export_schema.py` (create) | `parity/schema.json` |
| `tools/parity/check_determinism.py` (create) | Two-process byte comparison |
| `tests/test_parity/*.py` (create) | Tests for everything under `tools/parity/` |
| `parity/golden/**`, `parity/schema.json`, `parity/port_notes.md` (create) | The committed reference |
| `.pre-commit-config.yaml` (modify) | Format and mypy coverage for `tools/parity/` |

---

### Task 1: Archive tag, the Act II v1 switch, and the test marker

**Files:**
- Modify: `spacegame/config.py` (append a section at the end of the file)
- Modify: `spacegame/data_loader.py:247-251` and add a method
- Modify: `spacegame/models/player.py:466` (`record_lens_action`)
- Modify: `spacegame/engine/game.py:704-715`, `:4471-4472`, `:5350-5361`
- Modify: `tests/conftest.py`, `pyproject.toml` (`[tool.pytest.ini_options]`)
- Create: `tests/test_compliance/test_act_two_v1_switch.py`
- Modify: every test module whose tests need Act II content (found in Step 7)

**Interfaces:**
- Produces: `spacegame.config.ACT_TWO_V1_ENABLED: bool` (default `False`); `DataLoader.load_act_two_v1() -> None`; pytest marker `act_two_v1`.

- [ ] **Step 1: Create the branch and the archive tag**

```bash
git switch master
git switch -c sp2a-parity-reference
git tag -a act2-v1-archive master -m "Act II v1 (A2 lens arc) as written into the Act I galaxy; archived, not ported"
git tag --list act2-v1-archive
```
Expected: `act2-v1-archive` listed.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_compliance/test_act_two_v1_switch.py`:

```python
"""Act II v1 is archived and off by default (SP2 spec Section 5).

Act II v1 was written into the Act I galaxy and is not ported. The flag keeps
the Python reference behaving as Act I only; archived tests opt back in with
the ``act_two_v1`` marker.
"""

from __future__ import annotations

import pytest

import spacegame.config as sg_config
from spacegame.data_loader import DataLoader, get_data_loader
from tests.test_scenarios._helpers import fresh_player


class TestActTwoV1Switch:
    def test_flag_defaults_off(self) -> None:
        assert sg_config.ACT_TWO_V1_ENABLED is False, "Act II v1 must be off by default"

    def test_load_all_skips_act_two_registries(self) -> None:
        loader = DataLoader()
        loader.load_all()
        assert not loader.lenses, "lenses must not load with the flag off"
        assert not loader.capstones, "capstones must not load with the flag off"
        assert not loader.lens_reactions, "lens reactions must not load with the flag off"
        assert not loader.dilemmas, "dilemmas must not load with the flag off"
        assert not loader.post_capstone_templates, "post-capstone templates must not load"

    def test_load_act_two_v1_loads_registries(self) -> None:
        loader = DataLoader()
        loader.load_all()
        loader.load_act_two_v1()
        assert loader.lenses, "load_act_two_v1 must load the lens registry"
        assert loader.dilemmas, "load_act_two_v1 must load the dilemma registry"

    def test_record_lens_action_is_inert(self) -> None:
        player = fresh_player()
        assert player.record_lens_action("sold_cargo", 1) == [], (
            "record_lens_action must accrue nothing while Act II v1 is off"
        )


@pytest.mark.act_two_v1
class TestActTwoV1Marker:
    def test_marker_turns_the_flag_and_registries_on(self) -> None:
        assert sg_config.ACT_TWO_V1_ENABLED is True, "the marker must turn the flag on"
        assert get_data_loader().lenses, "the marker must make the lens registry available"
```

If `DataLoader()` needs a constructor argument, read `DataLoader.__init__` and pass the repo's `data/` directory the same way `get_data_loader()` does. If `fresh_player` lives elsewhere, `grep -n "def fresh_player" tests/test_scenarios/_helpers.py` gives the import.

- [ ] **Step 3: Run them to verify they fail**

Run: `python -m pytest tests/test_compliance/test_act_two_v1_switch.py -v`
Expected: FAIL with `AttributeError: module 'spacegame.config' has no attribute 'ACT_TWO_V1_ENABLED'`.

- [ ] **Step 4: Add the flag**

Append to `spacegame/config.py`:

```python
# ============================================================================
# ACT II V1 ARCHIVE
# ============================================================================

# Act II v1 (the A2 lens arc) was written into the Act I galaxy and is not
# ported to Godot (overhaul master spec, Appendix B). Off by default so the
# Python reference behaves as Act I only. Archived tests turn it on with the
# ``act_two_v1`` pytest marker. Read it as ``sg_config.ACT_TWO_V1_ENABLED``.
ACT_TWO_V1_ENABLED = False
```

- [ ] **Step 5: Gate the loads and the hooks**

In `spacegame/data_loader.py`, add `import spacegame.config as sg_config` to the imports if the module does not already import it under that name. Replace lines 247-251 (the five `_safe_load` calls for `lenses`, `capstones`, `lens_reactions`, `dilemmas`, `post_capstone_templates`) with:

```python
        if sg_config.ACT_TWO_V1_ENABLED:
            self.load_act_two_v1()
```

and add this method to `DataLoader` directly after `load_all`:

```python
    def load_act_two_v1(self) -> None:
        """Load the archived Act II v1 registries.

        Called by ``load_all`` only while ``ACT_TWO_V1_ENABLED`` is on, and by
        the ``act_two_v1`` test fixture.
        """
        self._safe_load("lenses", self.load_lenses)
        self._safe_load("capstones", self.load_capstones)
        self._safe_load("lens_reactions", self.load_lens_reactions)
        self._safe_load("dilemmas", self.load_dilemmas)
        self._safe_load("post_capstone_templates", self.load_post_capstone_templates)
```

In `spacegame/models/player.py`, add `import spacegame.config as sg_config` at module top if absent, and make these the first statements of the body of `record_lens_action` (after its docstring):

```python
        if not sg_config.ACT_TWO_V1_ENABLED:
            return []
```

In `spacegame/engine/game.py`, add `import spacegame.config as sg_config` to the imports. Replace lines 4471-4472:

```python
        if sg_config.ACT_TWO_V1_ENABLED:
            self._tick_dilemma_engine()
            self._tick_capstone_engine()
```

Wrap both `PostCapstoneContentGenerator` constructions (the `from ... import` and the assignment at lines 707-715 and 5353-5361) in `if sg_config.ACT_TWO_V1_ENABLED:`. The board merge at line 6183 already checks `hasattr(self, "post_capstone_content_gen")`, so an unconstructed generator is skipped. The wreckers view needs no change: an empty `lens_reactions` registry makes `LensReactor.choose_variant` return the default line.

- [ ] **Step 6: Register the marker and the fixture**

In `pyproject.toml` under `[tool.pytest.ini_options]`, add:

```toml
markers = [
    "act_two_v1: archived Act II v1 test; runs with ACT_TWO_V1_ENABLED on and the registries loaded",
]
```

In `tests/conftest.py`, add `import pytest` directly under the existing `import os`, and append after the `os.environ.setdefault(...)` lines:

```python
@pytest.fixture(autouse=True)
def _act_two_v1_marker(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Turn archived Act II v1 content on for tests marked ``act_two_v1``.

    Imports are local so the SDL environment variables above are set before
    anything pulls in pygame.
    """
    if request.node.get_closest_marker("act_two_v1") is None:
        return
    import spacegame.config as sg_config
    from spacegame.data_loader import get_data_loader

    monkeypatch.setattr(sg_config, "ACT_TWO_V1_ENABLED", True)
    loader = get_data_loader()
    if not loader.lenses:
        loader.load_act_two_v1()
```

Run: `python -m pytest tests/test_compliance/test_act_two_v1_switch.py -v`
Expected: 5 PASS.

- [ ] **Step 7: Mark the archived test modules**

Run: `python -m pytest -n auto -q -p no:randomly 2>&1 | tail -60`
For every failing test, read its traceback. If it fails because an Act II registry is empty or `record_lens_action` returned `[]` (lens, dilemma, capstone, lens reaction, post-capstone content), add at module level, directly after the imports:

```python
pytestmark = pytest.mark.act_two_v1
```

(adding `import pytest` if missing). Candidate modules, from a grep for lens, dilemma, and capstone: the files under `tests/test_compliance/` named `test_capstone_registry.py`, `test_dilemma_integrity.py`, `test_lens_*.py`; `tests/test_data/test_lens_reactions_cross_references.py`; `tests/test_models/test_capstone.py`, `test_dilemma.py`, `test_lens*.py`, `test_post_capstone_content.py`; `tests/test_scenarios/test_scenario_dilemma_*.py`, `test_scenario_capstone_session_continues.py`, `test_scenario_investment_*.py`, `test_scenario_oblique_readout.py`, `test_scenario_post_capstone_generation.py`; `tests/test_ui_layout/test_dilemma_resolution_view.py`; `tests/test_views/test_capstone_view.py`. Mark only modules that actually fail. A failure not caused by Act II content is a regression: fix it.

Run again until: `python -m pytest -n auto -q` reports 0 failures.

- [ ] **Step 8: Commit**

```bash
git add spacegame/config.py spacegame/data_loader.py spacegame/models/player.py spacegame/engine/game.py tests/conftest.py pyproject.toml tests/test_compliance/test_act_two_v1_switch.py tests/
git commit -m "feat(sp2a): switch Act II v1 off behind ACT_TWO_V1_ENABLED

Tagged act2-v1-archive first. Archived tests opt in with the act_two_v1 marker.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: SimRng

**Files:**
- Create: `spacegame/sim_rng.py`
- Create: `tests/sim_rng_helpers.py`
- Test: `tests/test_sim_rng.py`

**Interfaces:**
- Produces (every later task and the GDScript twin rely on these exact names):
  - `build_key(*parts: str | int) -> str`
  - `stable_seed(*parts: str | int) -> int` (unsigned 32-bit)
  - `seed_entropy(seed: int | None) -> None`
  - `class SimRng` with `__init__(s0, s1, s2, s3)`, classmethods `from_key(*parts)`, `from_digest(digest: bytes)`, `from_entropy()`, `from_state(s0, s1, s2, s3)`, `deserialize(words: Sequence[str])`; methods `state() -> tuple[int, int, int, int]`, `serialize() -> list[str]`, `next_u32() -> int`, `randf() -> float`, `randint(lo, hi) -> int`, `uniform(a, b) -> float`, `chance(p) -> bool`, `choice(seq)`, `shuffle(items) -> None`, `sample(population, k) -> list`, `weighted_index(weights) -> int`, and the `random.Random`-compatible aliases `random() -> float` and `choices(population, weights=None, k=1) -> list`.
  - `tests.sim_rng_helpers.ScriptedRng(values: Sequence[float], key: str = "scripted")`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sim_rng.py`:

```python
"""Known-answer and edge-case tests for SimRng (SP2 spec Section 3)."""

from __future__ import annotations

import pytest

from spacegame.sim_rng import SimRng, build_key, seed_entropy, stable_seed
from tests.sim_rng_helpers import ScriptedRng


class _ScriptedU32(SimRng):
    """Feeds randint a fixed sequence of raw 32-bit draws."""

    def __init__(self, draws: list[int]) -> None:
        super().__init__(1, 2, 3, 4)
        self._draws = list(draws)

    def next_u32(self) -> int:
        return self._draws.pop(0)


class TestAlgorithm:
    def test_reference_sequence_from_state_1_2_3_4(self) -> None:
        rng = SimRng(1, 2, 3, 4)
        got = [rng.next_u32() for _ in range(4)]
        assert got == [11520, 0, 5927040, 70819200], f"xoshiro128** reference mismatch: {got}"

    def test_md5_seeding_of_key_a(self) -> None:
        # md5("a") = 0cc175b9 c0f1b6a8 31c399e2 69772661, read as little-endian words.
        assert SimRng.from_key("a").state() == (0xB975C10C, 0xA8B6F1C0, 0xE299C331, 0x61267769)

    def test_all_zero_state_uses_fallback_word(self) -> None:
        assert SimRng(0, 0, 0, 0).state() == (0x9E3779B9, 0, 0, 0)

    def test_randf_is_top_24_bits(self) -> None:
        a = SimRng.from_key("k")
        b = SimRng.from_key("k")
        assert a.randf() == (b.next_u32() >> 8) / 16777216.0


class TestKeys:
    def test_parts_join_with_pipe(self) -> None:
        assert build_key("market", 1, "iron_ore") == "market|1|iron_ore"

    def test_negative_int_and_empty_string_are_valid(self) -> None:
        assert build_key("neg", -5, "") == "neg|-5|"

    @pytest.mark.parametrize("bad", [True, 1.5, None])
    def test_bool_float_none_are_rejected(self, bad: object) -> None:
        with pytest.raises(TypeError, match="str or int"):
            build_key("x", bad)  # type: ignore[arg-type]

    def test_same_key_same_stream(self) -> None:
        a = SimRng.from_key("market", 3, "food", "verdant")
        b = SimRng.from_key("market", 3, "food", "verdant")
        assert [a.next_u32() for _ in range(8)] == [b.next_u32() for _ in range(8)]

    def test_stable_seed_is_first_state_word(self) -> None:
        assert stable_seed("player", "Ada") == SimRng.from_key("player", "Ada").state()[0]


class TestRandint:
    def test_bounds_inclusive(self) -> None:
        rng = SimRng.from_key("randint")
        values = {rng.randint(1, 6) for _ in range(500)}
        assert values == {1, 2, 3, 4, 5, 6}

    def test_rejection_skips_values_at_or_above_limit(self) -> None:
        # n = 3, limit = (2**32 // 3) * 3 = 4294967295: that draw is rejected.
        rng = _ScriptedU32([4294967295, 7])
        assert rng.randint(0, 2) == 1

    def test_full_32_bit_span_is_allowed(self) -> None:
        assert SimRng.from_key("span").randint(0, 2**32 - 1) >= 0

    @pytest.mark.parametrize(("lo", "hi"), [(5, 4), (0, 2**32)])
    def test_invalid_spans_raise(self, lo: int, hi: int) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("bad").randint(lo, hi)


class TestSequences:
    def test_choice_empty_raises(self) -> None:
        with pytest.raises(IndexError):
            SimRng.from_key("c").choice([])

    def test_sample_bounds(self) -> None:
        rng = SimRng.from_key("s")
        assert rng.sample([1, 2, 3], 0) == []
        with pytest.raises(ValueError):
            rng.sample([1, 2, 3], 4)
        with pytest.raises(ValueError):
            rng.sample([1, 2, 3], -1)

    def test_sample_returns_distinct_members(self) -> None:
        got = SimRng.from_key("s").sample(list(range(10)), 4)
        assert len(set(got)) == 4 and set(got) <= set(range(10))

    def test_shuffle_is_a_permutation(self) -> None:
        items = list(range(10))
        SimRng.from_key("sh").shuffle(items)
        assert sorted(items) == list(range(10))

    def test_weighted_index_never_picks_zero_weight(self) -> None:
        rng = SimRng.from_key("w")
        picks = {rng.weighted_index([1.0, 0.0, 3.5]) for _ in range(300)}
        assert picks == {0, 2}

    @pytest.mark.parametrize("weights", [[], [0.0, 0.0]])
    def test_weighted_index_degenerate_raises(self, weights: list[float]) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("w").weighted_index(weights)

    def test_choices_with_mismatched_weights_raises(self) -> None:
        with pytest.raises(ValueError):
            SimRng.from_key("c").choices(["a", "b"], weights=[1.0], k=1)

    def test_choices_matches_weighted_index(self) -> None:
        a = SimRng.from_key("cw")
        b = SimRng.from_key("cw")
        assert a.choices(["x", "y", "z"], weights=[1, 2, 3], k=1)[0] == ["x", "y", "z"][
            b.weighted_index([1, 2, 3])
        ]


class TestStateAndEntropy:
    def test_serialize_round_trip(self) -> None:
        rng = SimRng.from_key("state")
        rng.next_u32()
        clone = SimRng.deserialize(rng.serialize())
        assert clone.state() == rng.state()
        assert all(isinstance(w, str) for w in rng.serialize())

    def test_deserialize_needs_four_words(self) -> None:
        with pytest.raises(ValueError):
            SimRng.deserialize(["1", "2", "3"])

    def test_seeded_entropy_is_reproducible(self) -> None:
        seed_entropy(7)
        first = [SimRng.from_entropy().next_u32() for _ in range(3)]
        seed_entropy(7)
        second = [SimRng.from_entropy().next_u32() for _ in range(3)]
        seed_entropy(None)
        assert first == second

    def test_unseeded_entropy_differs(self) -> None:
        seed_entropy(None)
        assert SimRng.from_entropy().state() != SimRng.from_entropy().state()


class TestScriptedRng:
    def test_random_returns_scripted_values_then_fails(self) -> None:
        rng = ScriptedRng([0.25, 0.75])
        assert rng.random() == 0.25
        assert rng.random() == 0.75
        with pytest.raises(AssertionError, match="ran out"):
            rng.random()

    def test_other_draws_are_real(self) -> None:
        assert ScriptedRng([0.0]).randint(0, 9) == SimRng.from_key("scripted").randint(0, 9)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_sim_rng.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'spacegame.sim_rng'`.

- [ ] **Step 3: Implement `spacegame/sim_rng.py`**

```python
"""Portable deterministic random generator shared with the Godot port.

xoshiro128** seeded from the md5 of a key string (SP2 spec Section 3). Every
operation is specified so that the GDScript twin (``core/rng/sim_rng.gd`` in
the aurelia repo) produces bit-identical results: 32-bit arithmetic masked
after every step, no transcendental functions, and fixed algorithms for every
derived draw.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import MutableSequence, Sequence
from typing import TypeVar

T = TypeVar("T")

_MASK32 = 0xFFFFFFFF
_TWO_32 = 1 << 32
_FALLBACK_S0 = 0x9E3779B9
_INV_2_24 = 1.0 / 16777216.0

_entropy_seed: int | None = None
_entropy_counter = 0


def seed_entropy(seed: int | None) -> None:
    """Make ``SimRng.from_entropy()`` reproducible, or restore OS entropy.

    The crawler and ``Game.seed_rngs`` call this so seeded runs replay
    exactly. ``None`` restores ``os.urandom`` seeding.

    Args:
        seed: Integer seed, or None for OS entropy.
    """
    global _entropy_seed, _entropy_counter
    _entropy_seed = seed
    _entropy_counter = 0


def build_key(*parts: str | int) -> str:
    """Join key parts with ``|``.

    Args:
        *parts: Key parts. Only ``str`` and ``int`` render identically in
            Python and GDScript, so ``bool``, ``float``, and ``None`` are rejected.

    Returns:
        The key string.

    Raises:
        TypeError: If a part is not ``str`` or ``int``, or is a ``bool``.
    """
    rendered: list[str] = []
    for part in parts:
        if isinstance(part, bool) or not isinstance(part, (str, int)):
            raise TypeError(
                f"SimRng key parts must be str or int, got {type(part).__name__}: {part!r}"
            )
        rendered.append(str(part))
    return "|".join(rendered)


def stable_seed(*parts: str | int) -> int:
    """Return a process-stable unsigned 32-bit seed for the given key parts.

    Replaces ``hash(...) & 0xFFFFFFFF``, which Python salts per process.

    Args:
        *parts: Key parts, as for ``build_key``.

    Returns:
        The first state word of ``SimRng.from_key(*parts)``.
    """
    return SimRng.from_key(*parts).state()[0]


def _rotl(x: int, k: int) -> int:
    return ((x << k) & _MASK32) | (x >> (32 - k))


class SimRng:
    """xoshiro128** generator with a ``random.Random``-compatible subset.

    Construct with ``from_key`` for deterministic streams, ``from_entropy``
    where a caller does not care, and ``deserialize`` to resume a saved stream.
    """

    __slots__ = ("_s0", "_s1", "_s2", "_s3")

    def __init__(self, s0: int, s1: int, s2: int, s3: int) -> None:
        words = [w & _MASK32 for w in (s0, s1, s2, s3)]
        if not any(words):
            words[0] = _FALLBACK_S0
        self._s0, self._s1, self._s2, self._s3 = words

    # === CONSTRUCTION ===

    @classmethod
    def from_key(cls, *parts: str | int) -> SimRng:
        """Seed from the md5 of ``build_key(*parts)`` encoded as UTF-8."""
        return cls.from_digest(hashlib.md5(build_key(*parts).encode("utf-8")).digest())

    @classmethod
    def from_digest(cls, digest: bytes) -> SimRng:
        """Seed from 16 bytes read as four little-endian unsigned 32-bit words."""
        if len(digest) != 16:
            raise ValueError(f"SimRng needs a 16-byte digest, got {len(digest)} bytes")
        return cls(*(int.from_bytes(digest[i : i + 4], "little") for i in (0, 4, 8, 12)))

    @classmethod
    def from_entropy(cls) -> SimRng:
        """A stream for callers that do not need determinism (see ``seed_entropy``)."""
        global _entropy_counter
        if _entropy_seed is None:
            return cls.from_digest(os.urandom(16))
        _entropy_counter += 1
        return cls.from_key("entropy", _entropy_seed, _entropy_counter)

    @classmethod
    def from_state(cls, s0: int, s1: int, s2: int, s3: int) -> SimRng:
        """Resume from four state words."""
        return cls(s0, s1, s2, s3)

    @classmethod
    def deserialize(cls, words: Sequence[str]) -> SimRng:
        """Resume from ``serialize()`` output (four decimal strings)."""
        if len(words) != 4:
            raise ValueError(f"SimRng state needs 4 words, got {len(words)}")
        return cls(*(int(w) for w in words))

    def state(self) -> tuple[int, int, int, int]:
        """The four state words."""
        return (self._s0, self._s1, self._s2, self._s3)

    def serialize(self) -> list[str]:
        """State as four decimal strings (Godot parses JSON numbers as float64)."""
        return [str(w) for w in self.state()]

    # === CORE ===

    def next_u32(self) -> int:
        """Advance the generator and return an unsigned 32-bit value."""
        s0, s1, s2, s3 = self._s0, self._s1, self._s2, self._s3
        result = (_rotl((s1 * 5) & _MASK32, 7) * 9) & _MASK32
        t = (s1 << 9) & _MASK32
        s2 ^= s0
        s3 ^= s1
        s1 ^= s2
        s0 ^= s3
        s2 ^= t
        s3 = _rotl(s3, 11)
        self._s0, self._s1, self._s2, self._s3 = s0, s1, s2, s3
        return result

    def randf(self) -> float:
        """A float in [0, 1) built from the top 24 bits, exact in both engines."""
        return (self.next_u32() >> 8) * _INV_2_24

    def randint(self, lo: int, hi: int) -> int:
        """An int in [lo, hi], unbiased by rejection sampling."""
        n = hi - lo + 1
        if n < 1 or n > _TWO_32:
            raise ValueError(f"randint span must be 1..2**32, got lo={lo} hi={hi}")
        limit = (_TWO_32 // n) * n
        while True:
            x = self.next_u32()
            if x < limit:
                return lo + x % n

    def uniform(self, a: float, b: float) -> float:
        """A float in [a, b)."""
        return a + (b - a) * self.randf()

    def chance(self, p: float) -> bool:
        """True with probability ``p``."""
        return self.randf() < p

    def choice(self, seq: Sequence[T]) -> T:
        """One element of a non-empty sequence."""
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def shuffle(self, items: MutableSequence[T]) -> None:
        """Fisher-Yates shuffle in place, walking from the end."""
        for i in range(len(items) - 1, 0, -1):
            j = self.randint(0, i)
            items[i], items[j] = items[j], items[i]

    def sample(self, population: Sequence[T], k: int) -> list[T]:
        """``k`` distinct elements by partial Fisher-Yates on a copy."""
        pool = list(population)
        n = len(pool)
        if k < 0 or k > n:
            raise ValueError(f"sample size {k} outside 0..{n}")
        for i in range(k):
            j = self.randint(i, n - 1)
            pool[i], pool[j] = pool[j], pool[i]
        return pool[:k]

    def weighted_index(self, weights: Sequence[float]) -> int:
        """An index drawn in proportion to ``weights`` (cumulative, index order)."""
        if not weights:
            raise ValueError("weighted_index needs at least one weight")
        total = 0.0
        for w in weights:
            total += w
        if total <= 0.0:
            raise ValueError("weighted_index needs at least one positive weight")
        r = self.randf() * total
        cumulative = 0.0
        for i, w in enumerate(weights):
            cumulative += w
            if r < cumulative:
                return i
        for i in range(len(weights) - 1, -1, -1):
            if weights[i] > 0:
                return i
        raise ValueError("weighted_index needs at least one positive weight")

    # === random.Random-COMPATIBLE ALIASES ===

    def random(self) -> float:
        """Alias of ``randf`` so converted call sites keep their spelling."""
        return self.randf()

    def choices(
        self, population: Sequence[T], weights: Sequence[float] | None = None, k: int = 1
    ) -> list[T]:
        """``k`` draws with replacement, weighted like ``weighted_index``."""
        if weights is None:
            return [self.choice(population) for _ in range(k)]
        if len(weights) != len(population):
            raise ValueError("choices needs one weight per population member")
        return [population[self.weighted_index(weights)] for _ in range(k)]
```

Create `tests/sim_rng_helpers.py`:

```python
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
```

The spec's optional `approx_normal` is not implemented: the census found no Gaussian draw in any model (the only methods called are `choice`, `randint`, `random`, `uniform`, `shuffle`, `sample`, `choices`), and spec 3.3 adds it only if one exists.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_sim_rng.py -v`
Expected: all PASS. If `test_reference_sequence_from_state_1_2_3_4` fails, the algorithm is wrong; do not adjust the expected values (they are the published xoshiro128** reference, checked by hand in the plan).

- [ ] **Step 5: Gate and commit**

Run the full gate (Global Constraints). Then:

```bash
git add spacegame/sim_rng.py tests/sim_rng_helpers.py tests/test_sim_rng.py
git commit -m "feat(sp2a): SimRng, the portable xoshiro128** generator

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Convert the seeded sites and the salted `hash()` seeds

**Files:**
- Modify (models): `market.py`, `okafor_research.py`, `wreckers_guild.py`, `encounter.py`, `galaxy_event.py`, `ground_contracts.py`, `politics.py`, `post_capstone_content.py`, `procedural_missions.py`, `smuggling.py`, `trade_contract.py`, `bidding.py`, `lens_reactor.py`, `combat_engine.py`, `crew_interjection.py`, `ground_mapgen.py`, `ground_equipment.py`, `builder_discovery.py`
- Modify (orchestration): `spacegame/engine/game.py`, `spacegame/views/galaxy_map_view.py`, `spacegame/views/combat_view.py`
- Test: `tests/test_models/test_sim_rng_sites.py`

**Interfaces:**
- Consumes: `SimRng.from_key`, `SimRng.from_entropy`, `stable_seed` (Task 2).
- Produces: the stream keys below. SP3 ports these modules and must build byte-identical keys.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_models/test_sim_rng_sites.py`:

```python
"""Keyed SimRng sites and cross-process determinism (SP2 spec Section 4)."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.market import Market
from spacegame.sim_rng import SimRng

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_in_fresh_process(snippet: str, hash_seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    done = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(snippet)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return done.stdout


class TestMarketKey:
    def test_variance_uses_the_market_stream(self) -> None:
        loader = get_data_loader()
        system = loader.systems["nexus_prime"]
        market = Market(system, list(loader.commodities.values()), game_day=4)
        commodity = next(iter(market.commodities.values()))
        span = abs(commodity.variance_max - commodity.variance_min)
        max_random = min(0.10, span * 0.2)
        expected = SimRng.from_key("market", 4, commodity.id, "nexus_prime").uniform(
            -max_random, max_random
        )
        assert market._get_random_variance(commodity) == expected


class TestCrossProcess:
    def test_procedural_missions_identical_across_hash_seeds(self) -> None:
        snippet = """
            from spacegame.data_loader import get_data_loader
            from spacegame.models.procedural_missions import ProceduralMissionGenerator
            dl = get_data_loader()
            gen = ProceduralMissionGenerator(
                systems=dl.systems, commodities=dl.commodities,
                enemy_templates=dl.enemy_templates, seed=12345,
            )
            for m in gen.generate_for_system("nexus_prime", 7):
                print(m.id, m.name)
        """
        first = _run_in_fresh_process(snippet, "1")
        second = _run_in_fresh_process(snippet, "2")
        assert first, "the generator should produce missions for nexus_prime on day 7"
        assert first == second, "procedural missions must not depend on PYTHONHASHSEED"

    def test_stable_seed_identical_across_hash_seeds(self) -> None:
        snippet = """
            from spacegame.sim_rng import stable_seed
            print(stable_seed("player", "Ada"), stable_seed("enemy", "pirate_raider"))
        """
        assert _run_in_fresh_process(snippet, "1") == _run_in_fresh_process(snippet, "2")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_models/test_sim_rng_sites.py -v`
Expected: `test_variance_uses_the_market_stream` FAILS (values differ) and `test_procedural_missions_identical_across_hash_seeds` FAILS (outputs differ between the two processes). `test_stable_seed_identical_across_hash_seeds` passes already (it pins Task 2).

- [ ] **Step 3: Convert the model sites**

In each file: add `from spacegame.sim_rng import SimRng`; apply the replacement; then remove `import random`, `import random as _rng`, `import hashlib`, and `import struct` only where they became unused (ruff F401 reports them). Replace every `random.Random` type annotation in the file with `SimRng`.

| Site | Before | After |
|---|---|---|
| `market.py:298` | `local_rng = random.Random(f"{self.game_day}_{commodity.id}_{self.system.id}")` | `local_rng = SimRng.from_key("market", self.game_day, commodity.id, self.system.id)` |
| `okafor_research.py:510` | `rng = random.Random(f"{window}_{player_seed_token}_okafor")` | `rng = SimRng.from_key("okafor_offers", window, player_seed_token)` |
| `okafor_research.py:692` | `rng = random.Random(f"{template.id}_{active.accept_day}_{player_seed_token}")` | `rng = SimRng.from_key("okafor_outcome", template.id, active.accept_day, player_seed_token)` |
| `wreckers_guild.py:318` | `rng = random.Random(f"{window}_{player_seed_token}_wreckers")` | `rng = SimRng.from_key("wreckers_offers", window, player_seed_token)` |
| `encounter.py:220-223` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("encounter", game_day, system_id)` |
| `encounter.py:534` | `rng = _rng.Random(seed)` | `rng = SimRng.from_key("encounter_select", seed)` |
| `galaxy_event.py:188` | `rng = _rng.Random(current_day)` | `rng = SimRng.from_key("galaxy_event_build", current_day)` |
| `galaxy_event.py:261-263` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("galaxy_event", current_day)` |
| `ground_contracts.py:167-169` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("ground_contracts", system_id, game_day)` |
| `politics.py:454-456` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("political_event", current_day)` |
| `post_capstone_content.py:335-337` | the `seed_str`, `seed_int`, `return` lines | `return SimRng.from_key("post_capstone", lens_id, game_day, self._base_seed)` (and `-> SimRng` on `_make_rng`) |
| `procedural_missions.py:65-66` | the `seed` and `return` lines | `return SimRng.from_key("procedural", self._base_seed, system_id, game_day, salt)` |
| `smuggling.py:387-389` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("customs", game_day, system_id)` |
| `smuggling.py:1007-1009` | the `seed_str`, `seed`, `rng` lines (keep `day_window = game_day // 3`) | `rng = SimRng.from_key("smuggling_contracts", system_id, day_window)` |
| `smuggling.py:1643-1645` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("bounty_hunter", game_day, system_id)` |
| `smuggling.py:1660` | `rng = _rng.Random(seed)` | `rng = SimRng.from_key("bounty_enemies", seed)` |
| `trade_contract.py:99-101` | the `seed_str`, `seed`, `rng` lines | `rng = SimRng.from_key("trade_contracts", system_id, game_day)` |
| `bidding.py:347-351` | the body of `_seeded_rng` | `return SimRng.from_key("bidding", seed_token)` (return type `SimRng`, docstring "Return a ``SimRng`` keyed off ``seed_token``.") |
| `lens_reactor.py:104` | `rng = random.Random(hash((player.game_day, context, player.name)))` | `rng = SimRng.from_key("lens_reactor", player.game_day, context, player.name)` (also update the module docstring lines 17 and 64 that describe the old seeding) |
| `combat_engine.py:71` | `self._rng = random.Random(seed)` | `self._rng = SimRng.from_key("combat", seed)` |
| `crew_interjection.py:135` | `self._rng = random.Random(seed)` | `self._rng = SimRng.from_key("crew_interjection", seed)` |
| `ground_mapgen.py:566` | `rng = random.Random(config.seed)` | `rng = SimRng.from_key("ground_map", config.seed)` |
| `ground_equipment.py:101` | `rng: random.Random` in `roll_container_loot` | `rng: SimRng` |
| `builder_discovery.py:229` | `rng = random.Random(seed) if seed is not None else random` | `rng = SimRng.from_key("salvage_discovery", seed) if seed is not None else SimRng.from_entropy()` |
| `builder_discovery.py:270` | `rng = random.Random(seed) if seed is not None else random` | `rng = SimRng.from_key("mining_discovery", seed) if seed is not None else SimRng.from_entropy()` |

`bidding_persona.py` and `_seeded_unit_from_token` in `bidding.py` derive values from sha256 bytes without a generator; they are already portable and stay unchanged.

- [ ] **Step 4: Replace the salted `hash()` seeds in orchestration**

Add `from spacegame.sim_rng import seed_entropy, stable_seed` to `game.py` (`seed_entropy` is used in Task 4), and `from spacegame.sim_rng import stable_seed` to `galaxy_map_view.py` and `combat_view.py`.

| Site | After |
|---|---|
| `game.py:700`, `:714`, `:5346`, `:5360` | `seed=stable_seed("player", self.player.name),` |
| `game.py:3826` | `seed = stable_seed("bounty_combat", self.player.game_day)` |
| `game.py:3970` | `seed = stable_seed("bounty", self.player.game_day, system_id)` |
| `game.py:4115` | `encounter_seed=stable_seed("customs", self.player.game_day, system_id),` |
| `game.py:4335`, `:4379`, `combat_view.py:2870` | `seed=state.encounter.encounter_seed + stable_seed("enemy", enemy.template.id),` |
| `game.py:4344`, `combat_view.py:2878` | `seed=state.encounter.encounter_seed + stable_seed("enemy", enemy.template.id) + 7919,` |
| `game.py:4964` | `seed=config.seed or stable_seed("ground_config", config.id),` |
| `galaxy_map_view.py:521` | `encounter_seed=stable_seed("forced_encounter", fe.trigger_flag),` |

Leave `galaxy_map_view.py:198` and `combat_view.py:1669`: they seed presentation only. The loot mirror in `combat_view.py` must stay identical to `game.py:4335` and `:4344`; the table keeps them identical.

- [ ] **Step 5: Run the new tests**

Run: `python -m pytest tests/test_models/test_sim_rng_sites.py -v`
Expected: 3 PASS.

- [ ] **Step 6: Run the suite and re-baseline**

Run: `python -m pytest -n auto -q 2>&1 | tail -80`
For each failure, open the test. If it asserts a specific outcome of a site converted in Step 3 or 4 (a price, a picked template, a generated contract, a roll result), update its expected value to what the converted code now produces, and add the test to the re-baseline list in the commit message with the site that changed it. If a test computes its expectation with `random.Random(...)`, change it to the matching `SimRng.from_key(...)` call from the table instead of hard-coding a number. Any other failure is a regression: fix the conversion. Repeat until 0 failures.

- [ ] **Step 7: Gate and commit**

Run the full gate. Then:

```bash
git add spacegame/ tests/
git commit -m "feat(sp2a): keyed SimRng streams replace seeded Random and salted hash seeds

Re-baselined (test: site):
- <one line per re-baselined test>

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Inject SimRng into the global-stream sites, and the scanner

**Files:**
- Modify: `ambient_dialogue.py`, `event.py`, `faction.py`, `investment.py`, `legendary_effects.py`, `module_combat.py`, `refining.py`, `mining.py`, `salvage.py`, `news_ticker.py`, `station_chatter.py`, `travel_log.py` (all in `spacegame/models/`)
- Modify: `spacegame/models/combat_engine.py:1523`, `:2136`, `:2203`
- Modify: `spacegame/engine/game.py:7136` (`seed_rngs`)
- Create: `tests/test_compliance/test_no_global_random_in_models.py`
- Create: `tests/test_models/test_sim_rng_injection.py`
- Modify: `tests/test_engine/test_game.py`, and the tests that seed or patch the global stream: `tests/test_models/test_depth_rocks.py:31`, `test_event.py:219,229`, `test_legendary_combat.py:122,135`, `test_legendary_multi_action_b7.py:165`, `test_mining.py:1290`, `test_mining_deep_core_integration.py:192`, `test_mining_ingredients.py:139,160`, `test_monolith.py:21-70`, `test_overkill_propagation.py:165,182,252,274`

**Interfaces:**
- Consumes: `SimRng`, `seed_entropy` (Task 2); `tests.sim_rng_helpers.ScriptedRng`.
- Produces: an optional `rng: SimRng | None = None` parameter, always the last parameter, on: `AmbientDialogueManager.__init__`, `EventGenerator.__init__`, `InvestmentManager.__init__`, `RefiningSession.__init__`, `MiningSession.__init__`, `SalvageSession.__init__`, `NewsTicker.__init__`, `StationChatterManager.__init__`, `TravelLogGenerator.__init__`, `generate_faction_assignments`, `process_chain_fire`, `resolve_module_hit`, `process_overkill_chain`, `AsteroidRock.get_yield`, `AsteroidRock.update_drill`, `AsteroidRock.apply_click`, `SalvageCell.update_extract`. Classes store it as `self._rng`.

- [ ] **Step 1: Write the failing scanner**

Create `tests/test_compliance/test_no_global_random_in_models.py`:

```python
"""Compliance Scanner: simulation randomness in models goes through SimRng.

See ``docs/superpowers/specs/2026-09-26-sp2-foundation-design.md`` Section 4.3.

The Godot port replays model behavior against golden traces. That only works
if every draw comes from ``spacegame.sim_rng.SimRng``: the global ``random``
module is shared with particles (frame-rate dependent) and ``hash()`` is
salted per process. No allowlist.
"""

from __future__ import annotations

import ast
from pathlib import Path

MODELS_ROOT = Path(__file__).resolve().parent.parent.parent / "spacegame" / "models"


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[str] = []
    hash_methods: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__hash__":
            hash_methods.update(id(n) for n in ast.walk(node))
    for node in ast.walk(tree):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random" or alias.name.startswith("numpy.random"):
                    hits.append(f"{path.name}:{line}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module in ("random", "numpy.random"):
            hits.append(f"{path.name}:{line}: from {node.module} import ...")
        elif isinstance(node, ast.Attribute):
            base = node.value
            if isinstance(base, ast.Name) and base.id in ("random", "_rng"):
                hits.append(f"{path.name}:{line}: {base.id}.{node.attr}")
            if isinstance(base, ast.Attribute) and base.attr == "random":
                if isinstance(base.value, ast.Name) and base.value.id in ("np", "numpy"):
                    hits.append(f"{path.name}:{line}: numpy.random.{node.attr}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "hash" and id(node) not in hash_methods:
                hits.append(f"{path.name}:{line}: hash(...)")
    return hits


def test_models_use_only_sim_rng() -> None:
    hits: list[str] = []
    for path in sorted(MODELS_ROOT.glob("*.py")):
        hits.extend(_violations(path))
    assert not hits, "Global randomness in models (use spacegame.sim_rng.SimRng):\n" + "\n".join(
        hits
    )
```

Run: `python -m pytest tests/test_compliance/test_no_global_random_in_models.py -v`
Expected: FAIL listing the remaining sites in the files named in this task.

- [ ] **Step 2: Write the failing injection tests**

Create `tests/test_models/test_sim_rng_injection.py`:

```python
"""Injected SimRng makes each former global-stream site reproducible."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.event import EventGenerator
from spacegame.models.faction import generate_faction_assignments
from spacegame.models.legendary_effects import process_chain_fire
from spacegame.sim_rng import SimRng, seed_entropy
from tests.sim_rng_helpers import ScriptedRng


class TestEventGenerator:
    def test_roll_below_chance_generates(self) -> None:
        gen = EventGenerator(["food", "fuel"], ["nexus_prime"], rng=ScriptedRng([0.0]))
        assert gen.try_generate_event(5, {"food": "Food", "fuel": "Fuel"}) is not None

    def test_roll_above_chance_skips(self) -> None:
        gen = EventGenerator(["food"], ["nexus_prime"], rng=ScriptedRng([1.0]))
        assert gen.try_generate_event(5, {"food": "Food"}) is None


class TestFactionAssignments:
    def test_same_stream_same_assignment(self) -> None:
        systems = [f"s{i}" for i in range(12)]
        factions = ["guild", "union", "collective"]
        a = generate_faction_assignments(systems, factions, rng=SimRng.from_key("factions", 1))
        b = generate_faction_assignments(systems, factions, rng=SimRng.from_key("factions", 1))
        assert a == b


class TestChainFire:
    def test_scripted_roll_triggers(self) -> None:
        from spacegame.models.legendary_effects import LegendaryState

        state = LegendaryState()
        state.chain_fire_chance = 0.5
        state.chain_fire_damage_mult = 0.4
        assert process_chain_fire(state, 10.0, rng=ScriptedRng([0.1])) == (True, 0.4)
        assert process_chain_fire(state, 10.0, rng=ScriptedRng([0.9])) == (False, 0.0)


class TestMiningField:
    def test_same_stream_same_field(self) -> None:
        from spacegame.models.mining import MiningSession

        config = next(iter(get_data_loader().mining_configs.values()))
        a = MiningSession(config, rng=SimRng.from_key("mine", 1))
        b = MiningSession(config, rng=SimRng.from_key("mine", 1))
        assert [(r.grid_x, r.grid_y, r.rock_type) for r in a.rocks] == [
            (r.grid_x, r.grid_y, r.rock_type) for r in b.rocks
        ]


class TestEntropyDefault:
    def test_seeded_entropy_reproduces_default_streams(self) -> None:
        seed_entropy(3)
        first = SimRng.from_entropy().next_u32()
        seed_entropy(3)
        second = SimRng.from_entropy().next_u32()
        seed_entropy(None)
        assert first == second
```

`LegendaryState`, `MiningSession.rocks`, and the rock attribute names are read from `legendary_effects.py` and `mining.py`; if a name differs (for example the rock list is `self.field`), use the real name. The assertion's intent is fixed: the same key gives the same field.

Run: `python -m pytest tests/test_models/test_sim_rng_injection.py -v`
Expected: FAIL with `TypeError: ... got an unexpected keyword argument 'rng'`.

- [ ] **Step 3: Inject into the classes**

For each class below, add `rng: SimRng | None = None` as the last `__init__` parameter, document it in the docstring's `Args:` as "Random stream; defaults to ``SimRng.from_entropy()``.", and make this the **first** statement of the `__init__` body (before anything that can draw, such as field generation):

```python
        self._rng = rng if rng is not None else SimRng.from_entropy()
```

Then replace the draws:

| Class (file) | Replace |
|---|---|
| `AmbientDialogueManager` (`ambient_dialogue.py`) | `random.choice(` at lines 80, 170, 208, 262, 302 with `self._rng.choice(` |
| `EventGenerator` (`event.py`) | `random.random()`, `random.choice(`, `random.randint(`, `random.uniform(` at lines 137-152 with `self._rng.` equivalents |
| `InvestmentManager` (`investment.py`) | `random.random()` at line 255 with `self._rng.random()` |
| `RefiningSession` (`refining.py`) | `random.random()` at line 298 with `self._rng.random()` |
| `MiningSession` (`mining.py`) | every `random.` call at lines 574, 575, 592, 623, 679, 682, 938, 941, 950, 951, 1020 with `self._rng.`; every `.get_yield()` call on a rock inside the session (lines 809, 883, 1026, 1057, 1119, 1148, 1190) with `.get_yield(self._rng)`; `rock.apply_click(effective_power)` at line 728 with `rock.apply_click(effective_power, rng=self._rng)` |
| `SalvageSession` (`salvage.py`) | `random.choice(DERELICT_TYPES)` at line 280, and the draws at lines 313, 333, 335, 462, 465, 471, with `self._rng.`; `cell.update_extract(dt, self.extract_speed_bonus)` at line 492 with `cell.update_extract(dt, self.extract_speed_bonus, rng=self._rng)` |
| `NewsTicker` (`news_ticker.py`) | `_rng.choice(` at lines 240, 261 with `self._rng.choice(` |
| `StationChatterManager` (`station_chatter.py`) | `_rng.sample(` at line 104 with `self._rng.sample(` |
| `TravelLogGenerator` (`travel_log.py`) | `_rng.choice(` at lines 73, 96, 127 with `self._rng.choice(` |

In `news_ticker.py`, `station_chatter.py`, and `travel_log.py` the module-level alias `_rng` is removed with `import random as _rng`; after the edit no bare `_rng.` may remain (the scanner checks).

- [ ] **Step 4: Inject into the functions and the per-object helpers**

Each gains a final parameter `rng: SimRng | None = None` and draws from `roll = rng if rng is not None else SimRng.from_entropy()`:

```python
# faction.py, generate_faction_assignments: replace `random.shuffle(shuffled)`
    (rng if rng is not None else SimRng.from_entropy()).shuffle(shuffled)

# legendary_effects.py, process_chain_fire: replace the roll
    roll = rng if rng is not None else SimRng.from_entropy()
    if roll.random() < state.chain_fire_chance:
        return True, state.chain_fire_damage_mult

# module_combat.py, resolve_module_hit: replace the choices line
    roll = rng if rng is not None else SimRng.from_entropy()
    result = roll.choices(choices, weights=weights, k=1)[0]

# module_combat.py, process_overkill_chain (after force_chain): replace both draws
    roll = rng if rng is not None else SimRng.from_entropy()
    if not force_chain and roll.random() >= CHAIN_DAMAGE_CHANCE:
        return None
    target_idx = roll.choice(valid_targets)

# mining.py, AsteroidRock.get_yield
    def get_yield(self, rng: SimRng | None = None) -> int:
        ...
        roll = rng if rng is not None else SimRng.from_entropy()
        return roll.randint(cfg.min_yield, cfg.max_yield)

# mining.py, AsteroidRock.update_drill(dt, speed_bonus=1.0, rng=None) and
# apply_click(click_power, rng=None): pass `rng` through to `self.get_yield(rng)`
# at lines 221 and 247.

# salvage.py, SalvageCell.update_extract(dt, speed_bonus=1.0, rng=None): at lines 153-155
            roll = rng if rng is not None else SimRng.from_entropy()
            if self.corrupted and roll.random() < 0.5:
                return 0
            base_yield = roll.randint(self.config.min_yield, self.config.max_yield)
```

In `combat_engine.py`, pass the engine's seeded stream so a fight reproduces from its seed: line 1523 `process_chain_fire(attacker_state._legendary, base_dmg, rng=self._rng)`; line 2136 add `rng=self._rng,` as the last argument of `resolve_module_hit(...)`; line 2203 add `rng=self._rng,` as the last argument of `process_overkill_chain(...)`.

Add `from spacegame.sim_rng import SimRng` to each modified model file and remove the now-unused `import random` lines.

- [ ] **Step 5: Seed SimRng entropy from `Game.seed_rngs`**

In `spacegame/engine/game.py`, `seed_rngs` becomes:

```python
    def seed_rngs(self, seed: int) -> None:
        """Seed global random sources for deterministic replay.

        Args:
            seed: Integer seed applied to stdlib random, numpy.random, and the
                SimRng entropy fallback used by models constructed without a stream.
        """
        random.seed(seed)
        np.random.seed(seed)
        seed_entropy(seed)
```

Add to `tests/test_engine/test_game.py`, after `test_seed_rngs_reproduces_random`:

```python
def test_seed_rngs_seeds_sim_rng_entropy() -> None:
    """Models constructed without a stream replay under the crawler's seed."""
    from spacegame.sim_rng import SimRng, seed_entropy

    game1 = Game()
    game1.seed_rngs(42)
    first = SimRng.from_entropy().next_u32()
    pygame.quit()

    game2 = Game()
    game2.seed_rngs(42)
    second = SimRng.from_entropy().next_u32()
    pygame.quit()
    seed_entropy(None)

    assert first == second, "seed_rngs must make SimRng.from_entropy reproducible"
```

- [ ] **Step 6: Move the global-seeding tests to injected streams**

For each test site listed under **Files**, replace `random.seed(N)` (or the `patch("spacegame.models.event.random.random", ...)` context) with a stream passed to the object under test:
- If the test only needs a repeatable outcome, pass `rng=SimRng.from_key("test", N)` to the constructor or function it exercises (for example `MiningSession(config, ..., rng=SimRng.from_key("test", 42))`).
- If the test needs a probability roll to go one way, pass `rng=ScriptedRng([value])`: `0.0` forces "rolled under the chance", `1.0` forces "rolled over". `test_event.py:219` becomes `ScriptedRng([0.0])` and `:229` becomes `ScriptedRng([1.0])`, passed as `EventGenerator(..., rng=...)`. The `test_overkill_propagation.py:182` search for "a seed that triggers at 30%" becomes `rng=ScriptedRng([0.0])`.
- `tests/test_models/test_market.py:324-349` asserts the market never touches the global stream; it stays unchanged and must pass.

Where a test's asserted values change because the stream changed, apply the re-baselining rule and list it in the commit message.

- [ ] **Step 7: Run everything**

Run: `python -m pytest tests/test_compliance/test_no_global_random_in_models.py tests/test_models/test_sim_rng_injection.py -v`
Expected: all PASS.
Run: `python -m pytest -n auto -q`
Expected: 0 failures (re-baseline or fix as in Task 3 Step 6).

- [ ] **Step 8: Gate and commit**

Run the full gate. Then:

```bash
git add spacegame/ tests/
git commit -m "feat(sp2a): inject SimRng into global-stream model sites; scanner

Combat now reproduces from its seed: module hits, overkill chains, and chain
fire draw from the engine's stream. seed_rngs seeds the SimRng entropy fallback.

Re-baselined (test: site):
- <one line per re-baselined test>

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Accepted procedural missions survive save and load

**Files:**
- Modify: `spacegame/models/mission.py` (`MissionManager.__init__`, `add_mission`, `remove_mission`, `get_state`, `load_state`)
- Test: `tests/test_models/test_mission_runtime_persistence.py`

**Interfaces:**
- Produces: `MissionManager.get_state()` gains the key `"runtime_missions": list[dict]` (each a `Mission.to_dict()`); `load_state` re-adds them before restoring status and progress.

- [ ] **Step 1: Write the failing test**

Create `tests/test_models/test_mission_runtime_persistence.py`:

```python
"""Runtime-added (procedural) missions persist through save and load (SP2 spec Section 6)."""

from __future__ import annotations

import json

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import MissionManager, MissionStatus
from spacegame.models.procedural_missions import ProceduralMissionGenerator
from tests.test_scenarios._helpers import fresh_player


def _board() -> tuple[MissionManager, list[str]]:
    dl = get_data_loader()
    manager = MissionManager(list(dl.missions.values()))
    gen = ProceduralMissionGenerator(
        systems=dl.systems,
        commodities=dl.commodities,
        enemy_templates=dl.enemy_templates,
        seed=2024,
    )
    ids: list[str] = []
    for mission in gen.generate_for_system("nexus_prime", 3):
        ok, msg = manager.add_mission(mission)
        assert ok, msg
        ids.append(mission.id)
    assert len(ids) >= 2, "need at least two procedural missions for this test"
    return manager, ids


class TestRuntimeMissionPersistence:
    def test_accepted_and_offered_runtime_missions_survive(self) -> None:
        manager, ids = _board()
        player = fresh_player()
        ok, msg = manager.accept_mission(ids[0], player)
        assert ok, msg

        saved = json.loads(json.dumps(manager.get_state()))
        restored = MissionManager(list(get_data_loader().missions.values()))
        restored.load_state(saved)

        assert restored.get_status(ids[0]) == MissionStatus.ACTIVE
        assert restored.get_status(ids[1]) == MissionStatus.AVAILABLE
        original = manager.get_mission(ids[0])
        copy = restored.get_mission(ids[0])
        assert original is not None and copy is not None
        assert copy.to_dict() == original.to_dict()

    def test_removed_runtime_missions_are_not_saved(self) -> None:
        manager, ids = _board()
        assert manager.remove_mission(ids[1])
        saved_ids = [m["id"] for m in manager.get_state()["runtime_missions"]]
        assert ids[1] not in saved_ids

    def test_legacy_state_without_runtime_missions_loads(self) -> None:
        restored = MissionManager(list(get_data_loader().missions.values()))
        restored.load_state({"status": {}, "progress": {}})
        assert restored.get_state()["runtime_missions"] == []
```

Check the real signatures before running: `accept_mission` at `mission.py:465` (its arguments), and the loader attribute holding static missions (`grep -n "self.missions" spacegame/data_loader.py`). Adjust the calls, not the assertions.

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_models/test_mission_runtime_persistence.py -v`
Expected: FAIL with `KeyError: 'runtime_missions'` or an assertion that the restored status is `None`.

- [ ] **Step 3: Implement**

In `MissionManager.__init__`, after `self._accepted_day`:

```python
        # Missions added at runtime (procedural contracts). Their definitions
        # are not in the data files, so get_state saves them in full.
        self._runtime_ids: list[str] = []
```

In `add_mission`, after the three assignments and before the return: `self._runtime_ids.append(mission.id)`.
In `remove_mission`, after the three `del` lines: `if mission_id in self._runtime_ids: self._runtime_ids.remove(mission_id)` (as two lines).
In `get_state`, add the entry:

```python
            "runtime_missions": [self._missions[mid].to_dict() for mid in self._runtime_ids],
```

At the top of `load_state`'s body (before `status_data = ...`):

```python
        for mission_data in data.get("runtime_missions", []):
            mission = Mission.from_dict(mission_data)
            if mission.id in self._missions:
                continue
            self._missions[mission.id] = mission
            self._status[mission.id] = MissionStatus.UNAVAILABLE
            self._progress[mission.id] = [False] * len(mission.objectives)
            self._runtime_ids.append(mission.id)
```

The existing loop then restores status and progress for every mission, runtime ones included.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_models/test_mission_runtime_persistence.py -v`
Expected: 3 PASS. If `copy.to_dict() == original.to_dict()` fails, `Mission.to_dict`/`from_dict` drop a field that procedural missions set: fix the round trip in `Mission` (both methods), not the test.

- [ ] **Step 5: Gate and commit**

Run the full gate (the scenario save/load tests must still pass). Then:

```bash
git add spacegame/models/mission.py tests/test_models/test_mission_runtime_persistence.py
git commit -m "fix(sp2a): accepted procedural missions survive save and load

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: The parity framework, the regen command, and the SimRng vectors

**Files:**
- Create: `tools/parity/__init__.py`, `tools/parity/driver.py`, `tools/parity/regen.py`, `tools/parity/rng_vectors.py`
- Create: `tests/test_parity/__init__.py`, `tests/test_parity/test_driver.py`, `tests/test_parity/test_rng_vectors.py`
- Modify: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: `SimRng` (Task 2).
- Produces:
  - `tools.parity.driver`: `REPO_ROOT: Path`, `FORMAT_VERSION = 1`, `normalize(value: object) -> object`, `float_tag(value: float) -> str`, `tag_floats(value: object) -> object`, `@dataclass Case(subsystem: str, name: str, setup: dict[str, object], steps: list[dict[str, object]])` with `record(call: str, args: list[object], result: object, state: dict[str, object]) -> None` and `to_json(source_commit: str) -> str`, `source_commit() -> str`, `dirty_paths_outside(prefix: str) -> list[str]`, `write_cases(cases: list[Case], golden_root: Path, commit: str) -> list[Path]`.
  - Float encoding (controller ruling R5, spec Amendments A1): `Case.steps` keep raw Python floats, and `to_json` writes every float as the string `f:<repr>:<int64 bits>`. Godot 4.7.2's JSON parser misrounds about a quarter of long decimals by one bit (probe: 501 of 2,000), so the Godot harness rebuilds each double from its bits; the repr keeps goldens readable.
  - `tools.parity.regen`: `DRIVERS: list[Callable[[], list[Case]]]`, `main(argv: list[str] | None = None) -> int`, CLI `python -m tools.parity.regen [--out DIR] [--allow-dirty]`.
  - `tools.parity.rng_vectors.build_cases() -> list[Case]` (subsystem `sim_rng`).
  - Golden layout: `<out>/golden/<subsystem>/<case>.json`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_parity/__init__.py` (empty) and `tests/test_parity/test_driver.py`:

```python
"""The golden writer's rules (SP2 spec Section 7.3)."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

import pytest

from tools.parity import driver
from tools.parity.driver import Case, normalize


class _Color(Enum):
    RED = "red"


class TestNormalize:
    def test_scalars_pass_through(self) -> None:
        assert normalize({"a": 1, "b": 2.5, "c": "x", "d": None, "e": True}) == {
            "a": 1,
            "b": 2.5,
            "c": "x",
            "d": None,
            "e": True,
        }

    def test_tuples_become_lists_and_enums_values(self) -> None:
        assert normalize((1, _Color.RED, (2, 3))) == [1, "red", [2, 3]]

    def test_sets_are_rejected(self) -> None:
        with pytest.raises(TypeError, match="sort"):
            normalize({1, 2})

    def test_non_string_keys_are_rejected(self) -> None:
        with pytest.raises(TypeError, match="keys"):
            normalize({1: "x"})

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_nan_and_infinity_are_rejected(self, bad: float) -> None:
        with pytest.raises(ValueError):
            normalize(bad)


class TestFloatTags:
    def test_float_tag_carries_repr_and_int64_bits(self) -> None:
        assert driver.float_tag(0.1) == "f:0.1:4591870180066957722"
        assert driver.float_tag(1.5) == "f:1.5:4609434218613702656"
        assert driver.float_tag(-0.0) == "f:-0.0:-9223372036854775808"

    def test_tag_floats_walks_containers_and_leaves_other_scalars(self) -> None:
        assert driver.tag_floats({"x": [1.5, 2, True, None, "s"]}) == {
            "x": ["f:1.5:4609434218613702656", 2, True, None, "s"]
        }


class TestCaseJson:
    def test_sorted_keys_two_space_indent_trailing_newline(self) -> None:
        case = Case("demo", "one", {"z": 1, "a": 2})
        case.record("call", [1, (2, 3)], None, {"b": 0.1, "a": 1})
        text = case.to_json("abc123")
        doc = json.loads(text)
        assert doc["format"] == 1
        assert doc["source_commit"] == "abc123"
        assert doc["steps"] == [
            {
                "call": "call",
                "args": [1, [2, 3]],
                "result": None,
                "state": {"a": 1, "b": "f:0.1:4591870180066957722"},
            }
        ]
        assert case.steps[0]["state"] == {"a": 1, "b": 0.1}, "steps keep raw floats"
        assert text.endswith("\n")
        assert text.index('"a"') < text.index('"z"'), "keys must be sorted"

    def test_write_cases_layout(self, tmp_path: Path) -> None:
        paths = driver.write_cases([Case("demo", "one", {})], tmp_path, "abc123")
        assert paths == [tmp_path / "demo" / "one.json"]
        assert paths[0].read_bytes().endswith(b"\n")
        assert b"\r\n" not in paths[0].read_bytes()


class TestRegenRefusesDirtyTree:
    def test_refuses_when_files_outside_parity_are_modified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        from tools.parity import regen

        monkeypatch.setattr(regen, "dirty_paths_outside", lambda prefix: ["spacegame/x.py"])
        assert regen.main(["--out", str(tmp_path)]) == 2

    def test_allow_dirty_writes(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from tools.parity import regen

        monkeypatch.setattr(regen, "dirty_paths_outside", lambda prefix: ["spacegame/x.py"])
        assert regen.main(["--out", str(tmp_path), "--allow-dirty"]) == 0
        assert (tmp_path / "golden" / "sim_rng").is_dir()
```

Create `tests/test_parity/test_rng_vectors.py`:

```python
"""The SimRng vectors are the contract with the GDScript twin (SP2 spec 3.4)."""

from __future__ import annotations

from spacegame.sim_rng import SimRng
from tools.parity.rng_vectors import build_cases


class TestRngVectors:
    def test_one_case_per_key_including_unicode_and_empty(self) -> None:
        keys = [case.setup["key"] for case in build_cases()]
        assert ["a"] in keys
        assert ["Ωmega", "naïve", "星"] in keys, "a non-ASCII key must be pinned"
        assert [""] in keys
        assert ["neg", -5] in keys

    def test_first_step_is_the_seeded_state(self) -> None:
        case = next(c for c in build_cases() if c.setup["key"] == ["a"])
        first = case.steps[0]
        assert first["call"] == "state"
        assert first["result"] == list(SimRng.from_key("a").state())

    def test_every_step_records_the_state_after_it(self) -> None:
        for case in build_cases():
            for step in case.steps:
                words = step["state"]["s"]
                assert isinstance(words, list) and len(words) == 4

    def test_vectors_are_stable(self) -> None:
        assert [c.to_json("x") for c in build_cases()] == [c.to_json("x") for c in build_cases()]
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_parity -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.parity'`.

- [ ] **Step 3: Implement `tools/parity/driver.py`**

Create `tools/parity/__init__.py` with the docstring `"""Golden traces for the Godot parity harness (SP2 spec Section 7)."""`.

```python
"""Golden trace recording for the Godot parity harness (SP2 spec Section 7)."""

from __future__ import annotations

import json
import math
import struct
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAT_VERSION = 1


def float_tag(value: float) -> str:
    """Encode a float as ``f:<repr>:<int64 bits>``.

    Godot's JSON parser misrounds about a quarter of long decimals by one bit, so the
    Godot harness rebuilds each double from its bits; the repr keeps goldens readable.
    """
    bits: int = struct.unpack("<q", struct.pack("<d", value))[0]
    return f"f:{value!r}:{bits}"


def tag_floats(value: object) -> object:
    """Replace every float inside an already-normalized value with its ``float_tag``."""
    if isinstance(value, float):
        return float_tag(value)
    if isinstance(value, dict):
        return {key: tag_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [tag_floats(item) for item in value]
    return value


def normalize(value: object) -> object:
    """Convert a Python value into the JSON shape the Godot comparator expects.

    Args:
        value: A result, argument, or state value.

    Returns:
        JSON-ready value: tuples become lists, enums their value.

    Raises:
        TypeError: For sets (unordered; sort them in the driver), non-string
            dict keys, and unsupported types.
        ValueError: For NaN and infinity.
    """
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"goldens cannot hold {value!r}")
        return value
    if isinstance(value, Enum):
        return normalize(value.value)
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"golden dict keys must be str, got {key!r}")
            out[key] = normalize(item)
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("sets are unordered; sort them into a list in the driver")
    raise TypeError(f"cannot write {type(value).__name__} to a golden: {value!r}")


@dataclass
class Case:
    """One golden file: a setup and the recorded calls."""

    subsystem: str
    name: str
    setup: dict[str, object]
    steps: list[dict[str, object]] = field(default_factory=list)

    def record(self, call: str, args: list[object], result: object, state: dict[str, object]) -> None:
        """Append one step: the call, its arguments, its result, and the state after it."""
        self.steps.append(
            {
                "call": call,
                "args": normalize(args),
                "result": normalize(result),
                "state": normalize(state),
            }
        )

    def to_json(self, source_commit: str) -> str:
        """Serialize with tagged floats, sorted keys, two-space indent, and a trailing newline."""
        document = {
            "format": FORMAT_VERSION,
            "subsystem": self.subsystem,
            "case": self.name,
            "source_commit": source_commit,
            "setup": tag_floats(normalize(self.setup)),
            "steps": tag_floats(self.steps),
        }
        return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"


def source_commit() -> str:
    """The commit the goldens are generated from."""
    done = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def dirty_paths_outside(prefix: str) -> list[str]:
    """Modified or untracked paths that do not start with ``prefix``."""
    done = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    paths = [line[3:].strip() for line in done.stdout.splitlines() if line.strip()]
    return [p for p in paths if not p.startswith(prefix)]


def write_cases(cases: list[Case], golden_root: Path, commit: str) -> list[Path]:
    """Write each case to ``golden_root/<subsystem>/<name>.json`` with LF endings."""
    written: list[Path] = []
    for case in cases:
        path = golden_root / case.subsystem / f"{case.name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(case.to_json(commit))
        written.append(path)
    return written
```

- [ ] **Step 4: Implement `tools/parity/rng_vectors.py`**

```python
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
            "choices", [["x", "y", "z"], [1, 2, 3], 3], rng.choices(["x", "y", "z"], [1, 2, 3], 3), _state(rng)
        )
        cases.append(case)
    return cases
```

- [ ] **Step 5: Implement `tools/parity/regen.py`**

```python
"""Regenerate every parity golden file (SP2 spec Section 7.7).

Usage:
    python -m tools.parity.regen [--out DIR] [--allow-dirty]

Refuses to run when files outside ``parity/`` are modified, so a golden's
``source_commit`` always names the code that produced it. Review the git diff
of ``parity/`` before committing a regen; a regen commit holds only goldens.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from tools.parity import rng_vectors
from tools.parity.driver import REPO_ROOT, Case, dirty_paths_outside, source_commit, write_cases

DRIVERS: list[Callable[[], list[Case]]] = [rng_vectors.build_cases]


def main(argv: list[str] | None = None) -> int:
    """Run every driver and write the goldens.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 2 when the tree is dirty.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "parity"))
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    dirty = dirty_paths_outside("parity/")
    if dirty and not args.allow_dirty:
        print("Refusing to regenerate goldens with uncommitted changes outside parity/:")
        for path in dirty:
            print(f"  {path}")
        return 2

    out = Path(args.out)
    commit = source_commit()
    cases = [case for build in DRIVERS for case in build()]
    written = write_cases(cases, out / "golden", commit)
    print(f"Wrote {len(written)} golden files under {out / 'golden'} from {commit[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Cover `tools/parity` in the pre-commit gate**

In `.pre-commit-config.yaml`, change the `ruff-format` hook's args to `[--check, spacegame/, tests/, tools/parity/]`, and add this hook after `mypy-crawler-strict`:

```yaml
      - id: mypy-parity-strict
        name: mypy tools/parity (zero tolerance, no baseline)
        # tools/parity/ is born clean under SP2, same bar as tools/crawler/.
        language: system
        entry: "python -m mypy tools/parity/ --follow-imports=silent"
        pass_filenames: false
        types_or: [python]
```

- [ ] **Step 7: Run to verify**

Run: `python -m pytest tests/test_parity -v`
Expected: all PASS.
Run: `python -m mypy tools/parity/ --follow-imports=silent`
Expected: `Success: no issues found`.

- [ ] **Step 8: Gate and commit**

```bash
git add tools/parity tests/test_parity .pre-commit-config.yaml
git commit -m "feat(sp2a): parity golden framework, regen command, SimRng vectors

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Market and PriceHistory cases

**Files:**
- Create: `tools/parity/drivers/__init__.py`, `tools/parity/drivers/market.py`
- Modify: `tools/parity/regen.py` (`DRIVERS`)
- Test: `tests/test_parity/test_market_driver.py`

**Interfaces:**
- Consumes: `Case`, `normalize` (Task 6); `Market`, `PriceHistory` (`spacegame/models/market.py`); `get_data_loader()`.
- Produces: `tools.parity.drivers.market.build_cases() -> list[Case]` with subsystems `market` and `price_history`. This is the call vocabulary the SP2-b adapters implement:
  - `market` setup `{"system_id": str, "day": int}`; calls `snapshot []`, `update_day [day]`, `initialize_stock []`, `record_buy [cid, qty]`, `record_sell [cid, qty]`, `deplete_stock [cid, qty]` (result `[bool, str]`), `regenerate_stock []`, `get_price [cid]`, `get_sell_price [cid]`; state `{"game_day", "prices", "player_supply_demand", "stock", "base_stock", "politics_shifts"}`.
  - `price_history` setup `{"max_days": int}`; calls `record [system_id, cid, day, price]`, `get_history [system_id, cid]` (result list of `[day, price]`), `get_trend [system_id, cid]`; state is `PriceHistory.to_dict()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_parity/test_market_driver.py`:

```python
"""Market goldens cover every system, pressure, stock, and the empty market."""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from tools.parity.drivers.market import build_cases


def _cases() -> dict[str, object]:
    return {case.name: case for case in build_cases()}


class TestMarketCases:
    def test_a_price_table_per_system(self) -> None:
        names = set(_cases())
        for system_id in get_data_loader().systems:
            assert f"price_table_{system_id}" in names

    def test_empty_market_is_recorded(self) -> None:
        case = _cases()["off_market_herons_mark"]
        first = case.steps[0]  # type: ignore[attr-defined]
        assert first["call"] == "snapshot"
        assert first["state"]["prices"] == {}

    def test_pressure_hits_both_caps_then_decays_away(self) -> None:
        case = _cases()["player_pressure_nexus_prime"]
        mods = [step["state"]["player_supply_demand"] for step in case.steps]  # type: ignore[attr-defined]
        values = [v for m in mods for v in m.values()]
        assert 0.3 in values and -0.3 in values, "both caps must be reached"
        assert mods[-1] == {}, "decay must expire every modifier"

    def test_stock_case_records_a_failed_depletion(self) -> None:
        case = _cases()["stock_nexus_prime"]
        results = [s["result"] for s in case.steps if s["call"] == "deplete_stock"]  # type: ignore[attr-defined]
        assert any(r[0] is False for r in results)
        assert any(r[0] is True for r in results)

    def test_price_history_covers_every_trend(self) -> None:
        trends = {
            s["result"]
            for c in build_cases()
            if c.subsystem == "price_history"
            for s in c.steps
            if s["call"] == "get_trend"
        }
        assert trends == {"rising", "falling", "stable"}

    def test_cases_are_stable(self) -> None:
        assert [c.to_json("x") for c in build_cases()] == [c.to_json("x") for c in build_cases()]
```

Run: `python -m pytest tests/test_parity/test_market_driver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.parity.drivers'`.

- [ ] **Step 2: Implement `tools/parity/drivers/market.py`**

Create `tools/parity/drivers/__init__.py` with the docstring `"""Per-subsystem golden drivers."""`.

```python
"""Market pricing golden cases, the SP2 tracer bullet (SP2 spec Section 7.4).

Market events, politics shifts, and galaxy-event multipliers are SP3 cases.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.commodity import Commodity
from spacegame.models.market import Market, PriceHistory
from tools.parity.driver import Case

PRICE_TABLE_DAYS = range(2, 31)  # spec 7.4: days 1 to 30
DECAY_DAYS = range(2, 21)


def _all_commodities() -> list[Commodity]:
    return list(get_data_loader().commodities.values())


def _snapshot(market: Market) -> dict[str, object]:
    return {"game_day": market.game_day, "prices": market.get_all_prices(), **market.to_dict()}


class _Recorder:
    """Applies calls to one Market and records each with the state after it."""

    def __init__(self, case: Case, system_id: str, day: int) -> None:
        self.case = case
        self.system = get_data_loader().systems[system_id]
        self.market = Market(self.system, _all_commodities(), game_day=day)

    def call(self, name: str, *args: object) -> object:
        if name == "snapshot":
            result: object = None
        elif name == "initialize_stock":
            result = self.market.initialize_stock(self.system, _all_commodities())
        else:
            result = getattr(self.market, name)(*args)
        self.case.record(name, list(args), result, _snapshot(self.market))
        return result


def _priced_ids(market: Market) -> list[str]:
    return sorted(cid for cid, c in market.commodities.items() if c.base_price > 0)


def _price_tables() -> list[Case]:
    cases: list[Case] = []
    for system_id in get_data_loader().systems:
        case = Case("market", f"price_table_{system_id}", {"system_id": system_id, "day": 1})
        rec = _Recorder(case, system_id, 1)
        rec.call("snapshot")
        for day in PRICE_TABLE_DAYS:
            rec.call("update_day", day)
        cases.append(case)
    return cases


def _pressure(system_id: str) -> Case:
    case = Case("market", f"player_pressure_{system_id}", {"system_id": system_id, "day": 1})
    rec = _Recorder(case, system_id, 1)
    first, second = _priced_ids(rec.market)[:2]
    rec.call("snapshot")
    rec.call("initialize_stock")
    rec.call("record_buy", first, 5)
    rec.call("record_buy", first, 20)
    rec.call("record_sell", second, 3)
    rec.call("record_sell", second, 30)
    rec.call("record_buy", second, 7)
    for day in DECAY_DAYS:
        rec.call("update_day", day)
    return case


def _stock() -> Case:
    case = Case("market", "stock_nexus_prime", {"system_id": "nexus_prime", "day": 1})
    rec = _Recorder(case, "nexus_prime", 1)
    first, second = _priced_ids(rec.market)[:2]
    rec.call("snapshot")
    rec.call("initialize_stock")
    rec.call("deplete_stock", first, 10)
    rec.call("deplete_stock", first, 100_000)
    rec.call("deplete_stock", second, rec.market.get_stock(second))
    for _ in range(4):
        rec.call("regenerate_stock")
    rec.call("deplete_stock", "not_a_commodity", 1)
    return case


def _off_market() -> Case:
    case = Case("market", "off_market_herons_mark", {"system_id": "herons_mark", "day": 1})
    rec = _Recorder(case, "herons_mark", 1)
    rec.call("snapshot")
    rec.call("get_price", "food")
    rec.call("get_sell_price", "food")
    rec.call("get_sell_price", "data_chip")
    rec.call("get_sell_price", "not_a_commodity")
    rec.call("initialize_stock")
    return case


def _history(name: str, steps: list[tuple[str, list[object]]]) -> Case:
    case = Case("price_history", name, {"max_days": 7})
    history = PriceHistory(max_days=7)
    for call, args in steps:
        result = getattr(history, call)(*args)
        case.record(call, args, result, history.to_dict())
    return case


def _histories() -> list[Case]:
    rising: list[tuple[str, list[object]]] = [
        ("record", ["nexus_prime", "food", day, 20 + day * 3]) for day in range(1, 11)
    ]
    rising += [("get_history", ["nexus_prime", "food"]), ("get_trend", ["nexus_prime", "food"])]
    falling: list[tuple[str, list[object]]] = [
        ("record", ["verdant", "fuel", day, 100 - day * 4]) for day in range(1, 6)
    ]
    falling += [("get_trend", ["verdant", "fuel"])]
    edges: list[tuple[str, list[object]]] = [
        ("get_trend", ["nowhere", "food"]),
        ("get_history", ["nowhere", "food"]),
        ("record", ["axiom_labs", "medical", 1, 50]),
        ("get_trend", ["axiom_labs", "medical"]),
        ("record", ["axiom_labs", "medical", 2, 51]),
        ("get_trend", ["axiom_labs", "medical"]),
        ("record", ["axiom_labs", "art", 1, 0]),
        ("record", ["axiom_labs", "art", 2, 3]),
        ("get_trend", ["axiom_labs", "art"]),
    ]
    return [_history("rising_trims", rising), _history("falling", falling), _history("edges", edges)]


def build_cases() -> list[Case]:
    """Every market and price-history case."""
    return [
        *_price_tables(),
        _pressure("nexus_prime"),
        _pressure("forgeworks"),
        _stock(),
        _off_market(),
        *_histories(),
    ]
```

In `tools/parity/regen.py`, import `from tools.parity.drivers import market as market_driver` and set `DRIVERS = [rng_vectors.build_cases, market_driver.build_cases]`.

- [ ] **Step 3: Run to verify it passes**

Run: `python -m pytest tests/test_parity -v`
Expected: all PASS. If `test_pressure_hits_both_caps_then_decays_away` fails on the caps, check that the two commodities are distinct and priced; the recorded args, not the test, decide what a Godot adapter replays.

- [ ] **Step 4: Gate and commit**

```bash
git add tools/parity tests/test_parity
git commit -m "feat(sp2a): market and price-history golden cases

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: The schema export

**Files:**
- Create: `tools/parity/export_schema.py`
- Modify: `tools/parity/regen.py` (writes `<out>/schema.json`)
- Test: `tests/test_parity/test_export_schema.py`

**Interfaces:**
- Produces: `build_schema() -> dict[str, object]` of shape `{"format": 1, "types": {TypeName: {field: type_string}}}`; `type_name(tp: object) -> str`; `TYPES: dict[str, type]` (the registry, extended by SP3). Type strings: `int`, `float`, `str`, `bool`, `enum`, `list<T>`, `optional<T>`, `dict<K,V>`, or a registered dataclass name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_parity/test_export_schema.py`:

```python
"""The schema tells Godot loaders which JSON numbers are ints (SP2 spec 7.5)."""

from __future__ import annotations

from typing import Optional

import pytest

from tools.parity.export_schema import build_schema, type_name


class TestSchema:
    def test_commodity_fields(self) -> None:
        commodity = build_schema()["types"]["Commodity"]  # type: ignore[index]
        assert commodity["base_price"] == "int"
        assert commodity["variance_min"] == "float"
        assert commodity["volume_per_unit"] == "int"
        assert commodity["category"] == "enum"
        assert commodity["production_tags"] == "list<str>"

    def test_nested_types(self) -> None:
        types = build_schema()["types"]  # type: ignore[index]
        assert types["StarSystem"]["economy"] == "Economy"
        assert types["StarSystem"]["stations"] == "list<Station>"
        assert types["StarSystem"]["rest_cost"] == "int"
        assert types["Economy"]["available_commodities"] == "optional<list<str>>"
        assert types["Coordinates"]["x"] == "float"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError):
            type_name(complex)

    def test_optional_form(self) -> None:
        assert type_name(Optional[int]) == "optional<int>"
```

Run: `python -m pytest tests/test_parity/test_export_schema.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 2: Implement `tools/parity/export_schema.py`**

```python
"""Field types for the model types Godot loaders build (SP2 spec Section 7.5).

Godot parses every JSON number as a float; loaders cast by this schema.
SP3 extends ``TYPES`` as it ports more models.
"""

from __future__ import annotations

import dataclasses
import json
import types
from enum import Enum
from pathlib import Path
from typing import Union, get_args, get_origin, get_type_hints

from spacegame.models.commodity import Commodity
from spacegame.models.system import Coordinates, Economy, StarSystem, Station

TYPES: dict[str, type] = {
    "Commodity": Commodity,
    "Coordinates": Coordinates,
    "Economy": Economy,
    "StarSystem": StarSystem,
    "Station": Station,
}

_SCALARS: dict[object, str] = {int: "int", float: "float", str: "str", bool: "bool"}


def type_name(tp: object) -> str:
    """Render one annotation as a schema type string.

    Raises:
        TypeError: For annotations the schema cannot express.
    """
    if tp in _SCALARS:
        return _SCALARS[tp]
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is list:
        return f"list<{type_name(args[0])}>"
    if origin is dict:
        return f"dict<{type_name(args[0])},{type_name(args[1])}>"
    if origin in (Union, types.UnionType):
        members = [a for a in args if a is not type(None)]
        if len(members) == 1 and len(args) == 2:
            return f"optional<{type_name(members[0])}>"
    if isinstance(tp, type) and issubclass(tp, Enum):
        return "enum"
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        return tp.__name__
    raise TypeError(f"schema cannot express {tp!r}")


def build_schema() -> dict[str, object]:
    """The schema document for every registered type."""
    out: dict[str, dict[str, str]] = {}
    for name, cls in TYPES.items():
        hints = get_type_hints(cls)
        out[name] = {f.name: type_name(hints[f.name]) for f in dataclasses.fields(cls)}
    return {"format": 1, "types": out}


def write_schema(path: Path) -> None:
    """Write the schema as sorted, two-space JSON with an LF ending."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(build_schema(), indent=2, sort_keys=True) + "\n")
```

In `tools/parity/regen.py`, import `from tools.parity.export_schema import write_schema` and, after `write_cases(...)`, add `write_schema(out / "schema.json")`.

- [ ] **Step 3: Run to verify it passes**

Run: `python -m pytest tests/test_parity -v`
Expected: all PASS.

- [ ] **Step 4: Gate and commit**

```bash
git add tools/parity tests/test_parity
git commit -m "feat(sp2a): schema export for Godot loader casts

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Determinism check, port notes, the committed reference, and the merge

**Files:**
- Create: `tools/parity/check_determinism.py`
- Test: `tests/test_parity/test_determinism.py`
- Create: `parity/port_notes.md`, `parity/golden/**`, `parity/schema.json` (generated)

**Interfaces:**
- Consumes: `tools.parity.regen.main` (Tasks 6-8).
- Produces: `check_determinism.main(argv: list[str] | None = None) -> int` (0 identical, 1 differ); the committed reference that SP2-b syncs.

- [ ] **Step 1: Write the failing test**

Create `tests/test_parity/test_determinism.py`:

```python
"""Two processes with different hash seeds write byte-identical goldens (SP2 spec 7.6)."""

from __future__ import annotations

import pytest

from tools.parity import check_determinism


@pytest.mark.timeout(300)
def test_regen_is_byte_identical_across_hash_seeds() -> None:
    assert check_determinism.main([]) == 0
```

Run: `python -m pytest tests/test_parity/test_determinism.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 2: Implement `tools/parity/check_determinism.py`**

```python
"""Prove the goldens do not depend on PYTHONHASHSEED (SP2 spec Section 7.6).

Runs ``tools.parity.regen`` twice in fresh processes with PYTHONHASHSEED=1
and =2 into temporary directories, then compares every file byte for byte.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.parity.driver import REPO_ROOT


def _regen(out: Path, hash_seed: str) -> None:
    env = dict(os.environ, PYTHONHASHSEED=hash_seed)
    subprocess.run(
        [sys.executable, "-m", "tools.parity.regen", "--out", str(out), "--allow-dirty"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def main(argv: list[str] | None = None) -> int:
    """Return 0 when both runs match, 1 otherwise (printing the differing files)."""
    with tempfile.TemporaryDirectory() as tmp:
        first, second = Path(tmp) / "one", Path(tmp) / "two"
        _regen(first, "1")
        _regen(second, "2")
        a, b = _files(first), _files(second)
        differing = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
    if differing:
        print("Goldens differ between hash seeds:")
        for name in differing:
            print(f"  {name}")
        return 1
    print(f"Byte-identical across hash seeds: {len(a)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `python -m pytest tests/test_parity/test_determinism.py -v`
Expected: PASS.

Commit it (the regen in Step 4 refuses to run while these files are uncommitted):

```bash
git add tools/parity/check_determinism.py tests/test_parity/test_determinism.py
git commit -m "feat(sp2a): determinism check across hash seeds

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Write `parity/port_notes.md`**

```markdown
# Port notes for SP3

Facts about the Python reference that a GDScript port must honor. Each entry
names the site so the porting task can find it.

## Rounding with ndigits

Python rounds a binary float's decimal representation, which `PyMath` does not
reproduce. None of these touch credits, prices, or quantities. Port them by
switching to integer math first, or record a deviation.

- `spacegame/models/build_rating.py:152, 187, 224, 257`: `round(score, 3)` (ship
  builder rating, retired scope per master spec Appendix A).
- `spacegame/models/salvage.py:335`: `round(rng.uniform(quality_min, 1.5), 2)`
  (salvage quality; the career sub-spec decides port or rebuild).

## Floor division and modulo on negative operands

Python floors; GDScript truncates. Use `PyMath.floor_div` and `PyMath.floor_mod`.

- `spacegame/models/social.py:275`
- `spacegame/models/politics_dispute.py:411`

## JSON number types

27 data keys mix ints and floats across files (`weight`, `variance_min`,
`variance_max`, `value`, `bonus_value`, and others). Cast by `parity/schema.json`.
These sites branch on `isinstance(x, int)` and need the cast before the check:
`capstone.py:128`, `lens_investment.py:174`, `bidding.py:724`, `build_sharing.py:253`.

## Derived seeds

Seeds computed from stream keys that later feed other streams. A port must build them the same way.

- Travel encounters: `EncounterRef.encounter_seed = stable_seed("encounter", game_day, system_id)`
  (`encounter.py`, `check_travel_encounter`). It feeds the combat, crew interjection,
  encounter selection, and loot seeds.
- The name `"customs"` is both a stream (`smuggling.py`, the inspection roll) and a
  `stable_seed` namespace (`game.py`, the customs `encounter_seed`). Consumers re-hash the seed,
  so the overlap is harmless, but the port's key registry must keep both uses.

## Act II v1

Off behind `ACT_TWO_V1_ENABLED` (tag `act2-v1-archive`). Not ported.

## Orchestration findings

Bugs in `game.py` and the views are design inputs, not parity deviations. They
are listed for the owning sub-projects in the aurelia repo's
`docs/findings_register.md` (SP2 spec Section 6).
```

- [ ] **Step 4: Generate and commit the reference**

`git status --short` must show only `?? parity/port_notes.md`. Commit the notes, then regenerate from the clean tree:

```bash
git add parity/port_notes.md
git commit -m "docs(sp2a): port notes for SP3

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
python -m tools.parity.regen
git status --short
```

Expected: `Wrote N golden files ...`, and `git status` shows only new files under `parity/golden/` and `parity/schema.json`. Read a sample (`parity/golden/market/player_pressure_nexus_prime.json`) to confirm the shape matches spec 7.2. Then:

```bash
git add parity/golden parity/schema.json
git commit -m "feat(sp2a): committed goldens and schema

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

This commit holds only goldens and the schema (spec 7.7).

- [ ] **Step 5: Final gate on the branch**

Run: `python -m pytest -n auto -q`, `ruff check spacegame/`, `ruff format --check spacegame/ tests/ tools/parity/`, the mypy baseline filter, `python -m mypy tools/parity/ --follow-imports=silent`, and `python -m tools.parity.check_determinism`.
Expected: every command succeeds.

- [ ] **Step 6: Merge locally**

```bash
git switch master
git merge --no-ff sp2a-parity-reference -m "Merge branch 'sp2a-parity-reference': SimRng, Act II off, parity goldens

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
python -m pytest -n auto -q
git branch -d sp2a-parity-reference
```

Expected: the suite passes on `master`. Do not push.
