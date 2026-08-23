# Spec A — Quality Foundation

**Date**: 2026-08-23
**Status**: approved (sections 1-4 walked through and approved in design conversation)
**Arc**: QF (Quality Foundation)
**Precedes**: Spec B (Shell Architecture), Spec C (Asset & Vision Pipeline)

---

## Why this spec exists

Aurelia has 10,370 passing tests, zero failures, a 70-second parallel suite, and a clean `ruff check`.
It also crashes when a playtester enters combat, crashes when they click Sell All, and lets them
strand themselves with no way out.

Both sentences are true. The gap between them is what this spec closes.

### Evidence gathered 2026-08-23

`mypy spacegame/` reports **768 errors across 64 of 201 source files**. Nothing runs it. There is no
`.github/workflows`, no `.pre-commit-config.yaml`, no git hooks. `git log --merges` is empty: all work
lands directly on `master`. CLAUDE.md line 54 documents "MyPy strict" as project convention, and
`mypy spacegame/` is listed under Quick Commands. The convention is written down and unenforced.

The playtester-reported crashes map onto the error distribution:

| File | crash-class errors | playtest report (2026-05-05) |
|---|---|---|
| `spacegame/engine/game.py` | 106 | (state / view lifecycle) |
| `spacegame/views/combat_view.py` | 44 | "went into combat, and the game crashed" |
| `spacegame/views/trading_view.py` | 31 | "click sell all ... the game just closes" |

The Sell All crash is recorded in `tests/test_views/test_trading_actions.py` as
`sell_commodity() takes 4 positional arguments but 5 were given`. `self.player` is correctly typed as
`Player` at `trading_view.py:71`. **MyPy would have caught it at author time.**

### Root diagnosis

This is not a codebase-quality problem and not an architecture problem. It is a **quality-gate
problem**. A 112,000-line project was built with the checkers switched off, and playtesters have been
serving as the type checker.

A secondary architectural problem exists: `game.py` is 6,549 lines with a 1,198-line
`_handle_state_transitions` method containing 185 branches, a 57-attribute constructor, and 106
`_ensure_*_view` call sites. **That is Spec B's scope, not this spec's.**

### Explicitly rejected alternative

Rewriting Aurelia from scratch was considered and rejected. The 5,622-to-34 ratio of model tests to
integration tests reflects a testing instinct, not an accident of this codebase; a fresh start with
the same instinct reproduces the same crash profile while discarding 39,815 LOC of pygame-free
models, 2.27MB of authored JSON content, and the tests that guard them. Every issue in the 2026-05-05
playtest transcript is a finishing problem, not a foundation problem.

---

## Section 1 — The Gate

Four gates. Three go to zero tolerance immediately; MyPy is ratcheted.

| Gate | Policy | State on 2026-08-23 |
|---|---|---|
| `ruff check spacegame/` | zero tolerance, immediate | already clean |
| `ruff format --check` | zero tolerance, immediate | 4 files drift (all in `tests/`) |
| `pytest -n auto` | zero tolerance, immediate | 10,370 pass / 98 skip / 70.5s |
| `mypy` | **ratcheted against baseline** | 768 errors |

> **Correction (found by the QF-1 planning agent, 2026-08-23).** An earlier draft of this spec said
> "`ruff check` already passes clean" without qualification. That is true for `spacegame/` only.
> `ruff check tests/` reports **874 pre-existing findings** (512 auto-fixable). Lint is therefore
> scoped to `spacegame/` in both the hook and CI. Cleaning `tests/` is deliberately **out of scope**
> for the QF arc; it is a separate, mechanical, low-risk sweep that should not be bundled with
> crash-risk work.

### Ratchet mechanics

- A checked-in `mypy-baseline.txt` generated from the 2026-08-23 output.
- CI and the pre-commit hook fail on any error **not** present in the baseline.
- Errors are fingerprinted on `(file, error-code, message-text)`, **never line number**, so unrelated
  edits do not churn the baseline or create merge conflicts.
- Use the `mypy-baseline` package from PyPI. Hand-rolling is roughly 50 lines but adds a maintenance
  surface for no benefit.
- The baseline may only be regenerated in a commit that changes nothing but type annotations and
  None-guards. This prevents it becoming a silent escape hatch during feature work.

### Metrics (revised during Section 4 analysis)

A single "crash-class" number conflates two unrelated populations and produces a misleading
dashboard. Track **two** numbers, both printed by CI on every run:

- **Population A — unguarded None access: 196.** Real crash risk. Must fall monotonically.
- **Population B — type blindness: 234.** Holes where type checking silently does nothing. Must fall,
  but **fixing them raises the total error count**, because MyPy starts seeing code it was blind to.

> **768 is a floor, not a ceiling.** Any gate whose rule is "the total must never increase" blocks the
> exact work this spec commissions. Stated here so a rising total in week three reads as progress.

### Deliberately out of scope

Per-module `[[tool.mypy.overrides]]` strictness tiers. The correct end state once modules begin
hitting zero, but building it now is machinery for a state we are not in.

### Decision: Python 3.13

Local environment runs 3.14.0; `pyproject.toml` pins `python_version = "3.13"` (MyPy) and
`target-version = "py313"` (ruff). CI standardizes on **3.13**, matching the config and the shipped
build. Changing runtime versions during a quality pass adds an uncontrolled variable.

---

## Section 2 — CI Topology

`git log --merges` is empty; all work lands directly on `master`. **Therefore CI on push cannot
prevent anything.** It reports that master is already broken. Prevention must be local; CI is the
backstop.

Measured timings that make local prevention viable:

```
ruff check spacegame/        0.1s
mypy  cold (no cache)       13.8s
mypy  warm, 1 file touched   0.4s
pytest -n auto              70.5s
```

### Pre-commit hook (prevention)

`ruff check`, `ruff format --check`, and `mypy` against baseline. **Sub-second warm.** Uses the
`pre-commit` framework with a checked-in `.pre-commit-config.yaml`, not a raw `.git/hooks` script and
not a Claude Code hook, because it must fire for every author: human, Claude, and ralph.

**pytest is deliberately NOT in the hook.** 70 seconds per commit is how hooks get bypassed.

### Ralph gets the same gate

`ralph/harness.py:360` runs `pytest -n auto -q --no-header` to capture a pass/skip baseline. That is
the only gate in the autonomous loop: no mypy, no ruff.

Ralph is executing a 50-sprint roadmap. Gating the human and not the loop misses most of the commit
volume. A type regression must mark a sprint `blocked` exactly the way a test failure does, using the
existing `Outcome` enum and `_mark_terminal_outcome` path.

### CI jobs

| Job | Runner | Runs | Trigger |
|---|---|---|---|
| `lint` | ubuntu-latest | `ruff check` + `ruff format --check` | push, PR |
| `types` | ubuntu-latest | `mypy` vs baseline; prints Population A and B counts | push, PR |
| `test` | ubuntu-latest **and** windows-latest | `pytest -n auto` | push, PR |
| `build` | windows-latest | PyInstaller via `spacegame.spec` | tag only |

Tests run on both platforms because Windows is the ship target and playtesters are on it; at 70
seconds the 2x Windows cost multiplier is irrelevant. Lint and types are platform-independent.

The tagged `build` job means **playtest builds become artifacts of a green pipeline** rather than
something produced by hand and discovered broken minutes later.

---

## Section 3 — The Play Harness

A deterministic, headless crawler driving the **real `Game` object** through **real event dispatch**.

### Verified mechanism

Probed 2026-08-23 against pygame-ce 2.5.6 / pygame_gui, headless (`SDL_VIDEODRIVER=dummy`):

```
mgr.get_sprite_group().sprites()  -> enumerates live UIButtons
button.is_enabled                 -> readable per element
synthetic MOUSEBUTTONDOWN/UP      -> produces a real UI_BUTTON_PRESSED event
pygame.image.save(screen, path)   -> 20.6ms
```

All three required capabilities work. Note that `LayeredGUIGroup` is **not** directly iterable; use
`.sprites()`.

### Required refactor (the only place Spec A touches `game.py`)

`Game.run()` (line 6243) is `while self.running: dt = self.clock.tick(FPS_TARGET)/1000.0`. Wall-clock
`dt` is non-reproducible. Extract the loop body into `Game.step(dt, events)` and have `run()` call it.
Small, well covered by the existing suite, and a seam Spec B wants regardless.

### Crawl step

Enumerate enabled elements from the live `ui_manager`; select an action from a seeded RNG (click a
button, press a bound key, or advance time); synthesize the pygame events; call `step()`; run oracles.

### Four oracles

1. **Unhandled exception.** The combat crash and the Sell All crash.
2. **UI element leak** on state exit. Reuse the check already in `tests/test_scenarios/_view_harness.py`.
3. **Softlock.** Zero enabled interactive elements and no keybind escape. The playtester's exact words
   were "I ended up stranded." Nothing in 10,370 tests can detect that; the crawler can.
4. **Invariant violation.** Negative credits, `fuel > max_fuel`, cargo exceeding hold capacity. Cheap,
   and targets "a ton of ways to softlock if you spend poorly."

### Outputs

- **Reproducible crashes.** Every failure reports `(seed, action_index)` plus the action trace. Replay
  is rerunning the seed. Each distinct crash generates a pytest regression stub, converting the crash
  corpus into permanent coverage.
- **Coverage.** Which of the 41 `GameState` values were reached and which transitions fired. Tells us
  where to hand-write scenario tests for what random exploration cannot reach.
- **A screenshot per state**, captured on first visit (~0.85s for the whole game). This is the piece
  folded forward from Spec C: a gallery of every screen in Aurelia as a build artifact. **Capture is
  in scope here; review and redesign are Spec C.**
- **Burndown triage input.** Cross-referencing visited code against Population A tells us which errors
  players actually reach.

### Two acknowledged risks

**Random clicking will not reach the late game.** Aurelia is an economy RPG; a uniform-random crawler
bounces around the station hub and never reaches a built ship in combat, because getting there needs a
coherent purchase sequence. Mitigations, all in scope: seed sessions from checkpoint saves via
`save_manager.py` (early / mid / late), weight action selection toward unvisited states, and provide a
debug hook to grant credits.

**It will find a lot at once.** Possibly hundreds of distinct crashes on the first real run. Without
deduplication by traceback signature and a stated triage policy, that is demoralizing rather than
useful. Dedup by normalized traceback signature; triage by crawler reachability.

### CI integration

A short seeded run (roughly 2,000 actions, ~30s) as a push gate. Long runs and multi-seed sweeps run
nightly or as ralph sprints.

---

## Section 4 — Burndown Triage

### The three populations

```
POPULATION A — unguarded None access (real crash risk)          196
   union-attr (X | None)                        165
   "None" has no attribute                       31
   of which live in game.py (deferred to Spec B) 72
   >>> actionable under this spec               124

POPULATION B — type blindness (not bugs)                        234
   "object" has no attribute                    167
   name-defined (unresolvable forward refs)      67

POPULATION C — hygiene                                          338
   arg-type, assignment, no-untyped-def, no-any-return, operator, ...

                                                          TOTAL 768
```

### Where Population B came from

```python
self._tutorial_helper: Optional[object] = None    # combat_view.py:407
station_chatter: object = None,                    # station_hub_view.py:201
data_loader: object,                               # cantina_view.py:63
crew_roster: object = None,
mission_manager: object = None,
```

There are **41 bare-`object` annotations in `views/` alone**. The mechanism:
`disallow_untyped_defs = true` is the one strict flag enabled. Annotating a parameter as `object`
satisfies it while providing zero type safety. **The single enabled flag created an incentive to
annotate meaninglessly.** This is a config problem, not a discipline problem.

The code at these sites is frequently correct:

```python
hint = self._tutorial_helper.get_current_hint() if self._tutorial_helper else ""
```

Properly None-guarded. The *annotation* is useless, not the logic. Hence: not a crash population.

Population B is also **runtime-safe by construction**. The `name-defined` cases are quoted forward
references (`-> "Optional[ShipBuild]"`) in modules without `from __future__ import annotations`, so
they are never evaluated. Nothing in the codebase calls `get_type_hints()`.

### These are ~12 root causes, not 768 fixes

| Root cause | Errors |
|---|---|
| `Game.player: Optional[Player]` (one field) | 64 |
| 41 `object`-typed collaborators in `views/` | 167 |
| 67 forward refs to never-imported names | 67 |
| `Market \| None` | 26 |
| `SalvageSession \| None` | 25 |
| UI element Optionals (`UIButton`, `UITextEntryLine`, `UITextBox`) | 14 |
| `MiningSession \| None` | 11 |
| `RefiningSession \| None` | 5 |

`Game.player` is `Optional` because the player does not exist until `initialize_new_game()`. A
non-Optional accessor property that raises if unset erases 64 errors in one edit. Most of this work
has that shape.

### Order of operations

1. **Population A outside `game.py` (124).** Real crash risk in code Spec B will not touch.
   Prioritized by crawler reachability once Section 3 lands.
2. **Population B (234).** Mechanical and high leverage, but sequenced **after** the crawler exists so
   newly revealed errors are triaged by reachability rather than dumped in a pile.
3. **Population C (338).** Opportunistic; the ratchet handles it (touch a file, clean the file).
4. **`game.py`'s 106 — deferred to Spec B.** Fixing `Player | None` 72 times in a file scheduled for
   decomposition is throwaway work. These stay baselined and are **excluded from the Population A
   metric**, with an explanatory comment in the baseline file.

> Consequence, stated plainly: `game.py` remains knowingly broken for the duration of Spec A.

---

## Additional deliverable: import-boundary guard

`models/` (39,815 LOC) and `constants/` (1,052 LOC) contain **zero** pygame imports. That property is
the only reason a future engine port is conceivable, and nothing enforces it.
`tests/test_compliance/` holds only the flag-string and list-dict discipline scanners.

Add a compliance test asserting that nothing under `spacegame/models/` or `spacegame/constants/`
imports pygame. Roughly 20 lines; preserves a strategic option indefinitely at near-zero cost.

---

## Out of scope for Spec A

- `game.py` decomposition and its 106 errors (**Spec B**)
- MCP-driven asset generation, raster asset loading, screenshot *review* (**Spec C**)
- Economy and combat balance tuning (separate design track)
- Engine migration of any kind (rejected; see "Why this spec exists")

## Success criteria

1. Pre-commit hook blocks a commit introducing a new MyPy error, a lint error, or format drift.
2. GitHub Actions runs lint, types, and tests on push; tagged builds produce a Windows artifact.
3. Ralph marks a sprint `blocked` on type regression, as it does for test failure.
4. The crawler runs headless and deterministically, reports coverage over the 41 `GameState` values,
   and reproduces any crash it finds from `(seed, action_index)`.
5. The crawler detects a deliberately introduced softlock (verification of oracle 3).
6. Population A outside `game.py` reaches **0**, down from 124.
7. Population B reaches **0**, down from 234, with the total error count permitted to rise in between.
8. `models/` and `constants/` are enforced pygame-free.
9. Full suite remains green throughout; no regression in the 10,370 passing tests.
