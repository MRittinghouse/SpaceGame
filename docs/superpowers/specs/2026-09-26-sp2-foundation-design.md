# SP2 Foundation: Design

- **Date:** 2026-09-26
- **Status:** Approved in two parts in a paired brainstorm (2026-09-26). This written form awaits the
  author's review.
- **Parent:** `2026-09-25-aurelia-overhaul-master-design.md`, Sections 9, 10 (SP2), and 11.
- **Runs:** in parallel with SP1 (Art and sound direction). Precedes SP3 (Logic port).
- **Plans:** SP2-a (Python reference work, in `SpaceGame`) then SP2-b (the Godot repo, in `aurelia`).

---

## 1. Goal

Build the machinery that lets the Godot port be checked against the Python build, prove it end to end
on one subsystem, and stand up the new repo with Everember's gates.

**Done means:**

In `SpaceGame`:
1. The full suite passes after every simulation randomness site in `models/` moves to `SimRng`,
   re-baselined where outcomes changed.
2. A scanner test bans the global `random` module and `hash()` seeding in `models/`.
3. Act II v1 is off by default; its tests pass under a fixture that turns it on.
4. The trace drivers run in two separate processes with different `PYTHONHASHSEED` values and produce
   byte-identical golden files.
5. The `SimRng` test vectors, the market goldens, and the schema export are committed.
6. Accepted procedural missions survive a save and load.

In `aurelia`:
1. The gate passes: gdformat, gdlint, import, gdUnit4 (including `SimRng` vectors and market parity),
   and the smoke boots.
2. The pre-commit hook is installed.
3. `tools/sync_data.py --check` passes.

---

## 2. Decision: parity sits at the model level

Chosen by the author on 2026-09-26 over whole-game traces and over targeted tests only.

A survey of the Python build found that it is a weak whole-game reference:
- Simulation state leaks out of the models. The trading view rebuilds the `Market` with fresh stock on
  every visit (`trading_view.py:246-247`), so player pressure lasts one visit. Mining, salvage,
  refining, and ground sessions live in views. Encounter and ground-dice rolls happen in views. About a
  dozen fields on the `Game` object are never saved.
- One global `random` stream is shared by simulation and particles, so outcomes depend on frame rate.
- Market events, galaxy events, and politics shifts never reach trading prices: `Market.apply_event`
  has no callers and `Game.markets` is never populated (`game.py:352`).
- Latent bugs: dialogue flags stored twice (`dialogue.py:333,337` and `game.py:5202`); accepted
  procedural missions dropped on load (`mission.py:984-995`); `TradeContractManager` never built; the
  Act II wealth capstone can fire during Act I at 95 sales.

Recording whole-game traces would lock in the orchestration being redesigned and these bugs. The
models are the trustworthy layer, so each subsystem's model API is the unit of parity. `game.py` and
the views are rebuilt fresh in Godot with their own tests.

---

## 3. SimRng: the portable random generator

One algorithm, implemented identically in Python (`spacegame/sim_rng.py`) and GDScript
(`core/rng/sim_rng.gd`). A shared test-vector file is the contract between them.

### 3.1 Algorithm: xoshiro128**

All arithmetic is on unsigned 32-bit values, masked with `M = 0xFFFFFFFF` after every operation that
can exceed 32 bits. The largest intermediate is below 2^36, so GDScript's signed 64-bit integers never
overflow. (PCG32 would need 64-bit multiplication that wraps, which GDScript does not guarantee.)

```
rotl(x, k) = ((x << k) & M) | (x >> (32 - k))

next_u32():
    result = (rotl((s1 * 5) & M, 7) * 9) & M
    t  = (s1 << 9) & M
    s2 = s2 ^ s0
    s3 = s3 ^ s1
    s1 = s1 ^ s2
    s0 = s0 ^ s3
    s2 = s2 ^ t
    s3 = rotl(s3, 11)
    return result
```

### 3.2 Seeding from a key

- A key is built from parts: `key = "|".join(parts)`. Parts must be `str` or `int`; ints render in
  decimal. Floats and bools are rejected with an error, because their string forms differ between the
  two engines.
- `digest = md5(key.encode("utf-8"))` gives 16 bytes. `s0..s3` are the little-endian unsigned 32-bit
  words of bytes 0-3, 4-7, 8-11, 12-15.
- If all four words are zero, `s0 = 0x9E3779B9`.
- Python uses `hashlib.md5`. GDScript uses `String.md5_buffer()` on the UTF-8 key.

### 3.3 API

Identical names, arguments, and algorithms on both sides:

| Method | Definition |
|---|---|
| `from_key(*parts)` | Seeded as in 3.2 |
| `from_state(s0, s1, s2, s3)` / `state()` | State as four ints; serialized as four decimal strings |
| `next_u32()` | 3.1 |
| `randf()` | `(next_u32() >> 8) * (1.0 / 16777216.0)`, in [0, 1), exact in both engines |
| `randint(lo, hi)` | Inclusive. `n = hi - lo + 1`, `1 <= n <= 2^32`. `limit = (2^32 // n) * n`. Draw `x = next_u32()` until `x < limit`, return `lo + x % n` |
| `uniform(a, b)` | `a + (b - a) * randf()` |
| `chance(p)` | `randf() < p` |
| `choice(seq)` | `seq[randint(0, len(seq) - 1)]`; empty raises |
| `shuffle(list)` | In place. For `i` from `len - 1` down to `1`: `j = randint(0, i)`, swap `i` and `j` |
| `sample(seq, k)` | Copy, then for `i` in `0..k-1`: `j = randint(i, n - 1)`, swap, return the first `k` |
| `weighted_index(weights)` | `total` summed in index order. `r = randf() * total`. Walk cumulative sums in index order and return the first `i` with `r < cum`. If none, the last index with a positive weight |
| `approx_normal(mu, sigma)` | `mu + sigma * (randf() + randf() + randf() + randf() - 2.0) * 1.7320508075688772` |

No transcendental functions are used, because `log` and `cos` can differ between math libraries.
`approx_normal` exists only if the conversion (Section 4) finds a Gaussian draw in a model.

### 3.4 Test vectors

`tools/parity/rng_vectors.py` writes `parity/golden/sim_rng/vectors.json`: for a fixed list of keys
(including `"a"`, a unicode key, and `"market|1|iron_ore|nexus_prime"`), the seeded state, the first
32 `next_u32` values, 16 `randf` values, and `randint`, `choice`, `shuffle`, `sample`, and
`weighted_index` results for fixed inputs. A Python test asserts the file is stable. A gdUnit4 test
asserts the GDScript implementation reproduces it exactly.

---

## 4. Converting the Python models (SP2-a)

### 4.1 Scope

Every simulation randomness site inside `spacegame/models/` and `data_loader.py`. The package-wide
census counts 82 simulation sites across patterns A to F, many of them in `game.py` and the views; the
plan enumerates the subset inside this scope. Sites in `game.py` and the views are left alone: they are
orchestration being rebuilt, and the trace drivers inject their own seeds. Presentation sites
(particles, station layouts) are left alone.

### 4.2 Conversion rules by pattern

| Pattern | Rule |
|---|---|
| A: `random.Random(str)` | `SimRng.from_key(...)` with the same logical parts. `market.py:298` becomes `SimRng.from_key("market", day, commodity_id, system_id)` |
| B: md5 or sha to int | `SimRng.from_key(...)` with the parts that were hashed |
| C: salted `hash()` | `SimRng.from_key(...)` with explicit parts. This fixes the per-launch variation |
| D: global `random.*` | An injected `SimRng`: a constructor or method parameter. Where the call site has a natural context key (day, system, entity id), a keyed stream instead |
| E: numpy | None in simulation scope |
| F: other (`Random(int)`, time) | Case by case; the plan lists each site |

Long-lived streams that must survive a save store `state()` as four decimal strings.

### 4.3 The scanner

`tests/test_compliance/test_no_global_random_in_models.py` walks the AST of every file in
`spacegame/models/` and fails on `import random`, `from random import`, any `random.` attribute
access, `numpy.random`, and any `hash(` call outside a `__hash__` method. It lists offending
`file:line` pairs.

### 4.4 Re-baselining

Tests that assert a specific random outcome get new expected values. Each re-baseline commit contains
only expected-value updates plus a one-line note per test naming the site that changed. Tests that
assert distributions or invariants must pass unchanged. A test that fails for any other reason is a
regression and is fixed, not re-baselined.

### 4.5 Arithmetic

- Godot preserves Python's semantics with `PyMath` helpers (Section 8.3). Python is not normalized.
- Before recording, any `round(x, ndigits)` in a model that touches credits, prices, or quantities
  becomes explicit integer math, because Python's decimal rounding of binary floats is hard to
  reproduce. The plan lists each site. Sites outside SP2's tracer bullet may instead be listed in
  `parity/port_notes.md` for SP3.

---

## 5. Act II v1 off

- `ACT_TWO_V1_ENABLED = False` in `spacegame/config.py`.
- The flag gates the five Act II loads in `data_loader.py:247-251`. With empty registries, every Act II
  path goes inert.
- Hygiene gates on the hook sites: `record_lens_action` (`player.py:466`), the dilemma and capstone
  ticks (`game.py:4471-4472`), the post-capstone generator construction (`game.py:707`, `:5353`), and
  the LensReactor in `wreckers_guild_view.py:164`.
- A pytest fixture turns the flag on for the 38 test files that exercise Act II, so they keep passing
  as a record of the archived code.
- Before the flag lands, the current `master` HEAD is tagged `act2-v1-archive`.

---

## 6. Bugs: fix first or register

- **Fix in Python first** when the fix is cheap, clearly right, and inside a model. SP2 fixes one:
  `MissionManager.load_state` must restore accepted procedural missions, with a round-trip test.
- **Register everything else** in `docs/parity/deviations.md` in the `aurelia` repo. Each entry has an
  id, the subsystem, the Python behavior, the Godot behavior, the reason, and the Godot test that covers
  it.
- **Orchestration bugs are design inputs, not deviations.** They go to `docs/findings_register.md` in
  `aurelia`, addressed to the sub-project that owns them:
  - dialogue flags stored twice (SP6)
  - markets never populated, and events and politics never reaching prices (SP5)
  - `TradeContractManager` never built (SP8, Merchant)
  - Act II firing during Act I (closed by Section 5)

---

## 7. Trace drivers and golden files (SP2-a)

### 7.1 Layout in `SpaceGame`

```
tools/parity/
  driver.py          base class: case setup, call recording, the writer
  drivers/market.py  the SP2 driver
  regen.py           runs every driver, writes parity/golden/
  rng_vectors.py     writes the SimRng vectors (3.4)
  export_schema.py   writes parity/schema.json (7.5)
  check_determinism.py
parity/
  golden/<subsystem>/<case>.json
  schema.json
  port_notes.md
```

### 7.2 Golden file format

```json
{
  "format": 1,
  "subsystem": "market",
  "case": "player_pressure_nexus_prime",
  "source_commit": "<SpaceGame commit sha>",
  "setup": {"system_id": "nexus_prime", "day": 1},
  "steps": [
    {"call": "record_buy", "args": ["iron_ore", 12], "result": null,
     "state": {"player_supply_demand": {"iron_ore": 0.24}, "prices": {"iron_ore": 41}}},
    {"call": "update_day", "args": [2], "result": null,
     "state": {"player_supply_demand": {"iron_ore": 0.168}, "prices": {"iron_ore": 39}}}
  ]
}
```

- `setup` holds only what the adapter needs to construct the object from synced data.
- `state` is the subsystem's snapshot after the call: its `to_dict()` where one exists, plus any
  derived values the case asserts (for the market, `get_all_prices()`).

### 7.3 Writer rules

- Keys are sorted and output is indented with two spaces, so diffs are readable.
- Floats are written with Python's shortest round-trip repr. NaN and infinity are rejected.
- Tuples become lists. Enums become their value. Sets are rejected; the driver sorts them into lists.

### 7.4 The market driver's cases

| Case | Covers |
|---|---|
| `price_table` | Every system and every available commodity, days 1 to 30: `get_all_prices()` after each `update_day` |
| `player_pressure_<system>` | For Nexus Prime and Forgeworks: sequences of `record_buy` and `record_sell` crossing the cap in both directions, then `update_day` decay until entries expire |
| `stock` | `initialize_stock`, `deplete_stock` success and failure, `regenerate_stock` across days |
| `off_market_sell` | `get_sell_price` for commodities a system does not stock |
| `price_history` | `PriceHistory.record`, `get_history`, `get_trend` across all trend branches |

Market events, politics shifts, and galaxy-event multipliers are SP3 cases, since they depend on
`MarketEvent`, `PoliticsMarketShift`, and `GalaxyEvent`.

### 7.5 The schema export

`export_schema.py` reads the dataclass type hints of the model types the data loader builds and writes
`parity/schema.json`: for each type, each field's JSON type (`int`, `float`, `str`, `bool`, `list`,
`dict`, or a nested type name). SP2 covers the types the tracer bullet needs (`Commodity`, `StarSystem`,
and its economy); SP3 extends the registry. Godot loaders cast by this schema, since Godot parses every
JSON number as a float.

### 7.6 Determinism check

`check_determinism.py` runs `regen.py` twice in subprocesses, with `PYTHONHASHSEED=1` and
`PYTHONHASHSEED=2`, into two temporary directories, and fails on any byte difference. A pytest wrapper
runs it in the suite.

### 7.7 Regeneration and review

`python -m tools.parity.regen` refreshes every golden. As in Everember, the author or the reviewer
reads the git diff before a regen is committed. A regen commit contains only golden files.

---

## 8. The `aurelia` repo (SP2-b)

### 8.1 Layout

```
aurelia/
  project.godot  .gitignore  .gitattributes  .gdlintrc  .mcp.json
  pyproject.toml  .python-version  CLAUDE.md
  addons/gdUnit4/            vendored (6.2.1)
  addons/godot_mcp/          restored locally, git-ignored
  autoload/                  game.gd, data_registry.gd, debug_console.gd
  core/
    rng/sim_rng.gd
    math/py_math.gd
    config/game_config.gd
    save/save_io.gd, save/save_document.gd
    sim/sim_root.gd, sim/kernel_system.gd
    economy/commodity.gd, economy/star_system.gd, economy/market.gd, economy/price_history.gd
    data/loaders (typed, schema-cast)
  data/                      synced from SpaceGame, plus SYNC.json
  scenes/                    main, a minimal shell, sandbox/ (stub)
  test/
    parity/parity_runner.gd, parity/comparator.gd, parity/adapters/market_adapter.gd
    parity/golden/           synced from SpaceGame
    unit/
  tools/
    gate.py  install_hooks.py  goal_run.py  mcp_headless.json  goal_slices.json  sync_data.py
    config.local.json        git-ignored
  docs/
    specs/                   the master spec and this spec, moved here
    roadmap.md               SP1 to SP11 with status
    autonomous_runs.md  dev_setup.md
    parity/deviations.md  findings_register.md
```

The repo is created with `git init` on `main`. There is no remote until the author and Claude do the
first push together.

### 8.2 Seeded from Everember

From `fantasy-idler`: copy verbatim `.gitattributes`, `.gdlintrc`, `.mcp.json`, `addons/gdUnit4/`,
`tools/install_hooks.py` (marker changed), `tools/goal_run.py`, `tools/mcp_headless.json`, and
`core/config/game_config.gd`. Take as a pattern only: `tools/balance/regen_baselines.py` and
`test/sim/baseline_test.gd` (the parity runner replaces them). Adapt:
- `project.godot`: desktop only (drop `handheld/orientation` and ETC2), the Forward+ renderer,
  untyped declarations as errors, three typed autoloads. Display settings are provisional until SP1
  confirms the pixel pipeline.
- `tools/gate.py`: drop the art and Blender stages (SP1 adds its own), add `sync_data.py --check`,
  smoke-boot `main` and `--sandbox stub` with a heartbeat line.
- `core/save/`, `core/sim/`, `autoload/game.gd` (the test-run guard), `autoload/data_registry.gd`,
  and the sandbox launcher.
- `docs/autonomous_runs.md` and `docs/dev_setup.md`.

Not copied in SP2: `tools/art/` (SP1 vendors it with a new `style.json`).

### 8.3 PyMath

`core/math/py_math.gd`, static functions matching Python exactly:
- `round_half_even(x: float) -> int`
- `floor_div(a, b)` for ints and floats (Python `//`)
- `floor_mod(a, b)` (Python `%`, sign of the divisor)
- `true_div(a, b) -> float` (Python `/`, always float)

Each has a unit test table generated from Python for edge cases: ties at .5 on both sides of zero,
negative operands, and exact multiples.

### 8.4 Porting rules (written into `CLAUDE.md`)

These rules exist because GDScript and Python differ in ways a parity test will catch only after the
fact:
1. Every Python `/` becomes `PyMath.true_div` or an explicit float division. GDScript's `int / int`
   truncates.
2. Every Python `//` and `%` becomes `PyMath.floor_div` and `PyMath.floor_mod`.
3. Every Python `round(x)` becomes `PyMath.round_half_even(x)`. `int(x)` stays `int(x)`; both truncate.
4. Float expressions keep Python's operand order and grouping, so rounding happens in the same places.
5. Dictionaries are built in the same insertion order as Python wherever iteration order feeds a
   random draw or an output list.
6. Loaders cast by `schema.json`. No model reads a JSON number without a cast.
7. All simulation randomness goes through `SimRng`. Godot's own random functions are allowed only in
   presentation code.
8. A ported subsystem is not redesigned until its parity suite passes (master spec Section 11).

### 8.5 Sync

`tools/sync_data.py --from <path to SpaceGame>`:
- refuses to run if the SpaceGame working tree is dirty
- copies `SpaceGame/data/` into `aurelia/data/`, and `SpaceGame/parity/golden/` and `schema.json`
  into `aurelia/test/parity/`
- writes `data/SYNC.json` with the source commit and a sha256 per file

`--check`, run by the gate, fails if any synced file differs from its recorded hash. Synced content is
edited in `SpaceGame` and re-synced, never edited in `aurelia`, until the cutover at M3.

### 8.6 Core skeleton

- `SimRoot` (RefCounted, no nodes): owns the config, the data registry handle, the day clock, and a
  list of `KernelSystem`s; emits `day_started`. SP2 builds only the skeleton and one test that steps
  days. SP3 fills it.
- `KernelSystem`: `id`, `day_start(ctx, day)`, `save()`, `load(data)`, `rederive()`.
- `SaveDocument` and `SaveIO`: a versioned v1 schema from day one, atomic writes with rotating backups.
  No import of Python saves.
- The three autoloads, typed by `class_name`, with the test-run guard so gdUnit4 never touches user
  saves.

### 8.7 The parity runner

- `ParityRunner` loads a golden file and hands `setup` to a subsystem adapter, which builds the Godot
  object from synced data. It then replays each step: calls the method through the adapter, then
  compares the result and the snapshot.
- `Comparator` rules:
  - exact equality by default, with integer and float values compared numerically (10 equals 10.0)
  - dictionary key sets must match exactly; list lengths and order must match
  - a failure names the path, for example `steps[12].state.stock.iron_ore: expected 40, got 39`
  - a tolerance is allowed only by a written ruling in `docs/parity/deviations.md`, cited by id in the
    adapter
- One gdUnit4 test per golden file keeps runtime down and failures legible.

### 8.8 The tracer bullet: market pricing at parity

Port `Commodity`, `StarSystem` (with its economy), `Market` (base pricing, supply and demand,
`SimRng` variance, player pressure with cap and decay, stock), and `PriceHistory`. The adapter exposes
the calls in 7.4. SP2 is done when every market golden passes.

The event, politics, and galaxy-event branches of `Market._calculate_price` are ported as code in SP2
(they are part of the same method) but are covered by goldens only in SP3.

**Why the market:** it is small (about 660 lines of Python), central to the game, and hits every hazard at once: a keyed
stream, float-to-int truncation, player-pressure float accumulation with decay, loader casts on
`base_price` and the variance fields, dictionary iteration, and the comparator.

---

## 9. The plans

**SP2-a (Python, `SpaceGame`), branch `sp2a-parity-reference`:**
1. Tag `act2-v1-archive`; add `ACT_TWO_V1_ENABLED` and the fixture.
2. `SimRng` with its unit tests and the vector writer.
3. Convert the pattern A, B, and C sites; re-baseline.
4. Convert the pattern D and F sites; re-baseline.
5. The scanner test.
6. The `round(x, ndigits)` cleanup for money; `port_notes.md` for the rest.
7. The procedural-mission load fix.
8. The driver framework, the writer, and the market driver.
9. The schema export.
10. The determinism check.
11. Regen and commit the goldens.

**SP2-b (Godot, `aurelia`), branch `sp2b-scaffold` in the new repo:**
1. Create the repo; seed from Everember; adapt `project.godot`, `CLAUDE.md` (with 8.4), the docs.
2. The gate, hooks, and smoke sandbox.
3. `sync_data.py` with `--check`; first sync.
4. `SimRng` and the vector test.
5. `PyMath` and its table tests.
6. The core skeleton and autoloads.
7. Schema-cast loaders for the tracer bullet's types.
8. The parity runner and comparator, with self-tests on synthetic goldens.
9. The market port and adapter; the market parity suite green.
10. `docs/roadmap.md`, `docs/parity/deviations.md`, `docs/findings_register.md` seeded with the
    Section 6 entries.

Both plans run autonomously on the runbook: subagent-driven, a review per task, a final review, the
full gate, then a local merge. `SpaceGame` changes merge to its `master` locally; pushing to its
existing origin stays the author's call. `aurelia` gets no remote until the paired first push.

---

## 10. Rulings

| Id | Ruling | Cost if wrong |
|---|---|---|
| R1 | xoshiro128** instead of Godot's built-in PCG32, so the generator does not depend on engine internals | Low: the generator is one small file on each side |
| R2 | Python's arithmetic semantics are preserved in Godot through `PyMath`, not normalized in Python first | A later redesign can switch a subsystem to round-half-away once its parity is retired |
| R3 | The tracer bullet excludes market events, politics, and galaxy events from goldens | SP3 adds those cases |
| R4 | Goldens are generated only in `SpaceGame` and synced into `aurelia` | One extra sync step per regen |
| R5 | Only models and the data loader are converted to `SimRng`; `game.py` and views keep their randomness | The Python game's orchestration stays nondeterministic, which no longer matters |
| R6 | One gdUnit4 test per golden file | Coarser failure counts; the comparator's path messages compensate |
| R7 | Forward+ renderer | SP1 may switch to Compatibility if the pixel pipeline needs it |

---

## 11. Risks

- **Re-baselining hides a regression.** Mitigated by 4.4: re-baseline commits carry only expected-value
  changes with a note per test, and the reviewer checks each against its converted site.
- **A hidden float divergence.** Mitigated by porting rules 1 to 5 and by the market suite, which
  exercises accumulation and truncation; any divergence is found at the step it first appears.
- **gdUnit4 runtime.** Mitigated by R6 and by keeping simulation tests out of the scene tree.
- **md5 and UTF-8 differences between engines.** Covered by the unicode key in the test vectors.
- **SpaceGame drift during the port.** Covered by the sync hash check and the frozen-reference rule
  (master spec 9.1).

---

## Amendments (2026-09-26, made while planning and executing SP2-a and SP2-b)

Each amendment supersedes the section it names. The plans record the matching rulings.

| Id | Supersedes | Amendment | Why |
|---|---|---|---|
| A1 | 7.3 (floats in goldens) | Goldens write every float as the string `f:<repr>:<int64 bits>`; `Case.steps` keep raw floats in Python. The Godot harness rebuilds each double from its bits. | Godot 4.7.2's JSON parser and `String.to_float()` misround 501 of 2,000 long decimals by one bit (probe 2026-09-26), so plain JSON floats cannot support exact comparison. `var_to_str` matches Python's repr, and short literals (every float in `data/`, at most four digits) parse exactly. |
| A2 | 3.3 (`approx_normal`) | Not implemented. | The census found no Gaussian draw in any model; the methods in use are `choice`, `randint`, `random`, `uniform`, `shuffle`, `sample`, `choices`. |
| A3 | 3.3 (API) | `SimRng` also exposes the `random.Random`-compatible aliases `random()` and `choices(population, weights=None, k=1)`, and `stable_seed(*parts)`; `seed_entropy(seed)` makes `from_entropy()` reproducible for the crawler. | Conversions become constructor swaps; `stable_seed` replaces salted `hash()` seeds. |
| A4 | R5 (orchestration randomness) | The salted `hash()` seeds in `game.py`, `galaxy_map_view.py`, and `combat_view.py` move to `stable_seed`. Other orchestration randomness stays. | Those seeds are the actual source of per-launch variation in fights and missions. |
| A5 | 4.2 (pattern D) | Injected models take an optional `rng` parameter that defaults to `SimRng.from_entropy()`. | Keeps `game.py` and view call sites unchanged; the trace drivers always inject. |
| A6 | 4.5 (`round(x, ndigits)`) | No site touches money; the five sites are listed in `parity/port_notes.md`. | Census. |
| A7 | 8.5 (schema location) | `schema.json` syncs to `data/schema.json`. | Runtime loaders read it, and `test/` is excluded from exports. |
| A8 | 8.6 (autoloads, SaveIO, GameConfig) | SP2-b builds two autoloads (Game, DataRegistry); DebugConsole, GameConfig, and SaveIO wait for their first caller. | Master spec 11: wire it or delete it. |
| A9 | 8.6 (`KernelSystem`) | State methods are `save_state()` and `load_state(data)`. | A method named `load` shadows Godot's global `load()` inside subclasses. |
| A10 | 8.8 (market branches) | The event, politics, and galaxy-event branches of `Market._calculate_price` are ported in SP3 with their goldens, not in SP2. | Untested code violates wire it or delete it. |
| A11 | R6 (one test per golden) | One gdUnit4 test per golden subsystem replays every file, names each failing case, and asserts the case count. | gdUnit4 cannot generate tests from a directory listing, and suites are capped at 25 public methods. |
| A12 | 3.3 (GDScript signature) | GDScript `SimRng.from_key` and `stable_seed` take an Array of parts. | GDScript has no varargs; the key string is identical. |
| A13 | 5 (the fixture) | The dilemma scenario modules' module-scoped fixtures call `load_act_two_v1()` when the registries are empty. | Module-scoped fixtures run before the function-scoped marker fixture. |
