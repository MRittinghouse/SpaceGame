# SP2-b Godot Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the `aurelia` Godot 4.7 repo with Everember's gates, a synced copy of the Python reference's content and goldens, the GDScript twins of `SimRng` and Python's arithmetic, a golden-replay parity harness, and market pricing ported at parity as the tracer bullet.

**Architecture:** Simulation code lives in `core/` as RefCounted classes with no nodes; two autoloads (`DataRegistry`, `Game`) load synced data and own a `SimRoot`. The parity harness lives in `test/parity/`: `GoldenCodec` restores exact floats from the tagged goldens, `ParityRunner` replays each golden through a subsystem `ParityAdapter`, and `ParityComparator` reports the first divergent step by path. Python tooling (`tools/gate.py`, `tools/sync_data.py`) runs under uv.

**Tech Stack:** Godot 4.7.2 (typed GDScript, console exe), gdUnit4 6.2.1, gdtoolkit 4.5 (gdformat, gdlint), Python 3.13 via uv (pytest, mypy strict, black 100).

**Spec:** `docs/superpowers/specs/2026-09-26-sp2-foundation-design.md` in `C:\Users\matth\PycharmProjects\SpaceGame` (Sections 8, 9, 10). Read it, and the "Amendments" section at its end, before any task.

**Precondition:** SP2-a is merged to SpaceGame `master`: `parity/golden/` (with `sim_rng/`, `market/`, `price_history/`) and `parity/schema.json` exist and the SpaceGame working tree is clean.

## Global Constraints

- Repo: `C:\Users\matth\PycharmProjects\aurelia`, created in Task 1 with a root commit on `main`; all other work on branch `sp2b-scaffold`, merged with `git merge --no-ff` in Task 9. No remote; the first push is paired with the author.
- Godot: `C:/Users/matth/Tools/Godot/Godot_v4.7.2-stable_win64_console.exe` (the console exe; never the GUI exe for headless runs). Every headless script run passes `--remote-debug tcp://127.0.0.1:0` and closes stdin; `tools/gate.py` does both.
- Typed GDScript everywhere: annotate every var, param, and return; untyped declarations are errors. `core/` holds RefCounted classes only: never Node, never `get_tree()`.
- Files under about 300 lines; at most 25 public methods per class (gdlint enforces, including test suites); at most 8 returns per function (gdlint). Tabs, gdformat style.
- Porting rules (spec 8.4, verbatim): (1) every Python `/` becomes `PyMath.true_div` or an explicit float division; (2) every Python `//` and `%` becomes `PyMath.floor_div_int`/`floor_div_float` and `PyMath.floor_mod_int`/`floor_mod_float`; (3) every Python `round(x)` becomes `PyMath.round_half_even(x)`, and `int(x)` stays `int(x)`; (4) float expressions keep Python's operand order and grouping; (5) dictionaries are built in Python's insertion order wherever order feeds a draw or an output list; (6) loaders cast by `data/schema.json`; (7) all simulation randomness goes through `SimRng`; (8) a ported subsystem is not redesigned until its parity suite passes.
- Inside `SimRng`, call its own methods as `self.randf()`: a bare `randf()` resolves to Godot's global `randf` (probed on 4.7.2).
- Synced files (`data/**`, `test/parity/golden/**`) are never edited in this repo; `tools/sync_data.py --check` fails the gate if they are.
- Python tooling: black at 100 columns, mypy strict on `tools/`, pytest under `tools/tests/`.
- Prose: no em-dashes; no "no X, no Y" constructions. Banned NPC names: Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose.
- Before every gate run, format: `gdformat core autoload scenes test` and `uv run black tools`. The code in this plan is close to formatter output but not byte-exact; formatter changes are expected, logic changes are not.
- Full gate after every task: `python tools/gate.py` exits 0 with every step PASS.

## Rulings made while planning (spec deviations; the spec's Amendments section records them)

- **P1** Two autoloads (`DataRegistry`, `Game`). `DebugConsole`, `GameConfig`, and `SaveIO` are deferred to the sub-project that first calls them (master spec 11: wire it or delete it). Cost if wrong: one small copy later.
- **P2** `KernelSystem` uses `save_state()` and `load_state(data)` so no subclass shadows Godot's global `load()`. Cost: none.
- **P3** `schema.json` syncs to `data/schema.json`, because runtime loaders read it and `test/` is excluded from exports. Goldens still sync to `test/parity/golden/`.
- **P4** The event, politics, and galaxy-event branches of `Market._calculate_price` are not ported in SP2: without goldens they would be untested code. SP3 ports them with their types and cases. The snapshot keeps `"politics_shifts": []`.
- **P5** One gdUnit4 test per golden subsystem replays every file in it, names each failing case, and asserts the case count (spec R6 said one test per file): gdUnit4 cannot generate tests from a directory listing, and suites are capped at 25 public methods.
- **P6** Goldens carry floats as `"f:<repr>:<int64 bits>"` (SP2-a ruling R5): Godot's JSON parser misrounds 501 of 2,000 long decimals by one bit (probe 2026-09-26). `GoldenCodec` rebuilds each double from its bits.
- **P7** GDScript has no varargs, so `SimRng.from_key` and `stable_seed` take an Array of parts (`SimRng.from_key(["market", day, cid, sid])`); the key string and algorithm are identical.
- **P8** Python's `Optional[List[str]]` for `Economy.available_commodities` becomes `restricts_availability: bool` plus the list.
- **P9** `Market.initialize_stock` drops Python's unused `commodities` parameter.
- **P10** `sync_data.py` normalizes `.json` and `.md` files to LF and hashes the normalized bytes: SpaceGame's Windows checkout is CRLF and this repo is `eol=lf`.

## Review Focus

- **Golden ints arrive as floats:** Godot parses every JSON number as a float, so adapters must cast args (`int(args[0])`) and key parts before use; `SimRng.from_key` rejects floats. Tests in Task 5 (the `neg`, `-5` key) and Task 8.
- **The `randf` shadow:** a future edit that writes `randf()` inside `SimRng` silently uses Godot's global generator. Test in Task 3 (`random()` must equal a clone's `randf()`).
- **Signed zero and INT64_MIN bits:** `"f:-0.0:-9223372036854775808"` must decode to -0.0 without `to_int` overflow. Test in Task 5.
- **A system that stocks nothing:** `herons_mark` has an empty availability list; loading must give `restricts_availability == true` with an empty list, not "unrestricted". Test in Task 6.
- **An edited synced file:** changing one byte under `data/` must fail `sync_data.py --check`, and a stray extra file must too. Tests in Task 2.

---

## File Structure

| Path | Responsibility |
|---|---|
| `project.godot`, `.gitignore`, `.gitattributes`, `.gdlintrc`, `.mcp.json`, `pyproject.toml`, `.python-version` | Project and tooling config |
| `CLAUDE.md` | Rules for every agent working here |
| `addons/gdUnit4/` | Vendored test framework (copied from Everember) |
| `tools/gate.py`, `tools/install_hooks.py`, `tools/goal_run.py`, `tools/mcp_headless.json`, `tools/goal_slices.json` | Gate, hook, unattended runs |
| `tools/sync_data.py`, `tools/tests/test_sync_data.py` | Sync from the Python reference, and its tests |
| `autoload/game.gd` (`GameAutoload`) | Command-line helpers, test-run guard, owns the SimRoot |
| `autoload/data_registry.gd` (`DataRegistryAutoload`) | Loads `SimData` at startup |
| `scenes/main.tscn`, `scenes/main.gd` | Boot scene and the `stub` sandbox |
| `core/rng/sim_rng.gd` (`SimRng`) | The portable generator |
| `core/math/py_math.gd` (`PyMath`) | Python arithmetic semantics |
| `core/data/schema_cast.gd` (`SchemaCast`), `core/data/sim_data.gd` (`SimData`) | Schema casts and typed content |
| `core/galaxy/coordinates.gd`, `station.gd`, `economy.gd`, `star_system.gd` | Galaxy types |
| `core/economy/commodity.gd`, `market.gd`, `price_history.gd` | Economy types and the market port |
| `core/sim/sim_root.gd` (`SimRoot`), `core/sim/kernel_system.gd` (`KernelSystem`), `core/save/save_document.gd` (`SaveDocument`) | Simulation skeleton |
| `test/parity/golden_codec.gd`, `comparator.gd`, `parity_runner.gd`, `parity_adapter.gd`, `adapters/*.gd` | The parity harness |
| `test/unit/*_test.gd`, `test/parity/*_test.gd` | gdUnit4 suites |
| `data/**`, `test/parity/golden/**` | Synced, read-only |
| `docs/specs/`, `docs/plans/`, `docs/roadmap.md`, `docs/autonomous_runs.md`, `docs/dev_setup.md`, `docs/parity/deviations.md`, `docs/findings_register.md` | Docs |

---

### Task 1: The repo, its gate, and the boot scene

**Files:**
- Create: everything under "Project and tooling config", `CLAUDE.md`, `addons/gdUnit4/`, `tools/gate.py`, `tools/install_hooks.py`, `autoload/game.gd`, `scenes/main.tscn`, `scenes/main.gd`, `test/unit/boot_test.gd`, `docs/specs/*`, `docs/plans/*`

**Interfaces:**
- Produces: `GameAutoload.is_test_run() -> bool`, `GameAutoload.has_arg(flag: String) -> bool`, `GameAutoload.arg_value(flag: String) -> String` (static); the `[boot] main` and `[boot] sandbox stub` heartbeat lines; `tools/gate.py` with `HEARTBEATS: tuple[str, ...] = ("[boot]",)`.

- [ ] **Step 1: Create the repo with a root commit on main**

```bash
mkdir -p /c/Users/matth/PycharmProjects/aurelia && cd /c/Users/matth/PycharmProjects/aurelia
git init -b main
```

Create `.gitattributes`:

```
* text=auto eol=lf
*.json text eol=lf
*.png binary
*.jpg binary
*.ttf binary
*.wav binary
*.ogg binary
```

Create `.gitignore`:

```
# Godot
.godot/
*.import
export/
*.tmp

# Local config and secrets
tools/.env
tools/config.local.json
.mcp.json.local

# Python
__pycache__/
*.pyc
.venv/
.uv/

# Unattended run logs
tools/goal_runs/

# OS / IDE
.DS_Store
Thumbs.db
.idea/
.vscode/

# Godot MCP Pro is a paid, non-redistributable addon. Restore from C:\Users\matth\Tools\godot-mcp-pro\addons\
addons/godot_mcp/
.claude/settings.local.json

# gdUnit4 report output
reports/

# Superpowers SDD scratch (ledger, briefs, review packages)
.superpowers/
```

```bash
git add .gitattributes .gitignore
git commit -m "chore: root commit

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
git switch -c sp2b-scaffold
```

- [ ] **Step 2: Copy the seed files from Everember**

```bash
E=/c/Users/matth/PycharmProjects/fantasy-idler
A=/c/Users/matth/PycharmProjects/aurelia
cp -r $E/addons/gdUnit4 $A/addons/
mkdir -p $A/addons/godot_mcp && cp -r /c/Users/matth/Tools/godot-mcp-pro/addons/godot_mcp/. $A/addons/godot_mcp/
cp $E/.gdlintrc $E/.mcp.json $E/.python-version $A/
mkdir -p $A/tools && cp $E/tools/goal_run.py $E/tools/mcp_headless.json $A/tools/
cp $E/tools/config.local.json $A/tools/config.local.json
mkdir -p $A/docs/specs $A/docs/plans
cp /c/Users/matth/PycharmProjects/SpaceGame/docs/superpowers/specs/2026-09-25-aurelia-overhaul-master-design.md $A/docs/specs/
cp /c/Users/matth/PycharmProjects/SpaceGame/docs/superpowers/specs/2026-09-26-sp2-foundation-design.md $A/docs/specs/
cp /c/Users/matth/PycharmProjects/SpaceGame/docs/superpowers/plans/2026-09-26-sp2b-godot-scaffold.md $A/docs/plans/
```

`tools/config.local.json` is git-ignored; it keeps the `godot` path. In `tools/goal_run.py`, nothing changes: it reads `tools/goal_slices.json` (Task 9) and the runbook templates.

- [ ] **Step 3: Write the project and Python config**

`project.godot`:

```ini
; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.
;
; Format:
;   [section] ; section goes between []
;   param=value ; assign values to parameters

config_version=5

[application]

config/name="Aurelia"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.7", "Forward Plus")

[autoload]

Game="*res://autoload/game.gd"

[debug]

gdscript/warnings/untyped_declaration=2
gdscript/warnings/unsafe_property_access=1
gdscript/warnings/unsafe_method_access=1

[display]

window/size/viewport_width=1920
window/size/viewport_height=1080
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[editor_plugins]

enabled=PackedStringArray("res://addons/gdUnit4/plugin.cfg", "res://addons/godot_mcp/plugin.cfg")

[rendering]

renderer/rendering_method="forward_plus"
```

Display settings are provisional until SP1 confirms the pixel pipeline.

`pyproject.toml`:

```toml
[project]
name = "aurelia-tools"
version = "0.0.0"
description = "Aurelia gate and sync tooling. Not a distributable package."
requires-python = ">=3.13,<3.14"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8.3",
    "mypy>=1.14",
    "black>=25.1",
]

[tool.uv]
package = false

[tool.black]
line-length = 100
target-version = ["py313"]

[tool.mypy]
python_version = "3.13"
strict = true
files = ["tools"]
explicit_package_bases = true
mypy_path = "."

[tool.pytest.ini_options]
testpaths = ["tools/tests"]
pythonpath = ["."]
```

Create empty `tools/__init__.py` and `tools/tests/__init__.py`. Run `uv sync` once.

- [ ] **Step 4: Write the gate and the hook installer**

`tools/gate.py`:

```python
"""Aurelia quality gate: format, lint, Python tools, import, unit tests, smoke boot. Exit 1 on
any failure.

Usage:
  python tools/gate.py               full gate
  python tools/gate.py --tests-only  import + gdUnit4 + tools pytest
  python tools/gate.py --fast        gdformat check + gdlint + black check (pre-commit subset)

Uses the Godot *console* binary (Godot_v4.x_win64_console.exe) so stdout reaches the terminal.
Guards that keep headless runs from hanging or lying (learned in Everember):
  * `--remote-debug tcp://127.0.0.1:0` stops Godot from opening its local interactive `debug>`
    prompt on script parse errors. stdin is also closed as a second guard.
  * gdUnit4's exit code is not trusted alone: the newest reports/report_N/results.xml is parsed
    and the run fails if zero tests executed or any failed or errored.
  * Smoke boots run with `-d` so analyzer warnings reach the output; every ERROR or WARNING line
    fails the boot, and each boot must print every heartbeat in HEARTBEATS.
"""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "tools" / "config.local.json").read_text(encoding="utf-8"))
GODOT: str = CONFIG["godot"]
REPORTS = ROOT / "reports"
GD_DIRS = ["core", "autoload", "scenes", "test"]
NO_LOCAL_DEBUGGER = ["--remote-debug", "tcp://127.0.0.1:0"]
SMOKE_FRAMES = 120
SMOKE_TIMEOUT_S = 180
HEARTBEATS: tuple[str, ...] = ("[boot]",)
# Lines the remote-debug port-0 trick always prints; not real failures.
SMOKE_IGNORED = ("remote port number", "Remote Debugger: Unable to connect")
UV = ["uv", "run", "--frozen"]


def run(
    name: str, cmd: list[str], capture: bool = False, timeout: int | None = None
) -> tuple[bool, str]:
    """Run one gate step from the repo root with stdin closed."""
    print(f"\n=== {name} ===", flush=True)
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=capture,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"{name}: timed out after {timeout}s")
        return False, ""
    out = (proc.stdout or "") + (proc.stderr or "") if capture else ""
    if capture:
        print(out[-4000:])
    return proc.returncode == 0, out


def gd_format_check() -> bool:
    return run("gdformat --check", ["gdformat", "--check", *GD_DIRS])[0]


def gd_lint() -> bool:
    return run("gdlint", ["gdlint", *GD_DIRS])[0]


def tools_format() -> bool:
    return run("tools: black --check", [*UV, "black", "--check", "tools"])[0]


def tools_types() -> bool:
    return run("tools: mypy", [*UV, "mypy"])[0]


def tools_tests() -> bool:
    return run("tools: pytest", [*UV, "pytest", "-q"])[0]


def gd_import() -> bool:
    return run("godot import", [GODOT, "--headless", "--path", str(ROOT), "--import"])[0]


def _newest_results_xml() -> Path | None:
    if not REPORTS.exists():
        return None
    candidates = sorted(REPORTS.glob("report_*/results.xml"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def _verify_report() -> bool:
    xml_path = _newest_results_xml()
    if xml_path is None:
        print("gdUnit4: no results.xml produced")
        return False
    root = ET.parse(xml_path).getroot()
    tests = int(root.get("tests", "0"))
    failures = int(root.get("failures", "0"))
    errors = sum(int(s.get("errors", "0")) for s in root.iter("testsuite"))
    print(f"gdUnit4 report: {tests} tests, {failures} failures, {errors} errors ({xml_path.name})")
    return tests > 0 and failures == 0 and errors == 0


def unit_tests(path: str = "res://test") -> bool:
    ok, _ = run(
        "gdUnit4",
        [
            GODOT,
            "--headless",
            "--path",
            str(ROOT),
            "-s",
            "-d",
            *NO_LOCAL_DEBUGGER,
            "res://addons/gdUnit4/bin/GdUnitCmdTool.gd",
            "--ignoreHeadlessMode",
            "-a",
            path,
        ],
    )
    return ok and _verify_report()


def _boot(label: str, extra: list[str]) -> bool:
    ok, out = run(
        f"smoke boot ({label})",
        [GODOT, "--headless", "-d", "--path", str(ROOT), "--quit-after", str(SMOKE_FRAMES), *extra],
        capture=True,
        timeout=SMOKE_TIMEOUT_S,
    )
    bad = [
        line
        for line in out.splitlines()
        if ("ERROR" in line or "WARNING" in line)
        and not any(ignored in line for ignored in SMOKE_IGNORED)
    ]
    if bad:
        print(f"smoke ({label}): {len(bad)} error/warning lines in output (first 10):")
        for line in bad[:10]:
            print("  " + line)
    missing = [beat for beat in HEARTBEATS if beat not in out]
    if missing:
        print(f"smoke ({label}): heartbeat lines not found: {missing}")
        return False
    return ok and not bad


def smoke() -> bool:
    main_ok = _boot("main", [])
    sandbox_ok = _boot("sandbox stub", ["--", "--sandbox", "stub"])
    return main_ok and sandbox_ok


def main(argv: list[str]) -> int:
    results: dict[str, bool] = {}
    if "--fast" in argv:
        results["format"] = gd_format_check()
        results["lint"] = gd_lint()
        results["tools_format"] = tools_format()
    elif "--tests-only" in argv:
        results["import"] = gd_import()
        results["tests"] = unit_tests()
        results["tools_tests"] = tools_tests()
    else:
        results["format"] = gd_format_check()
        results["lint"] = gd_lint()
        results["tools_format"] = tools_format()
        results["tools_types"] = tools_types()
        results["import"] = gd_import()
        results["tests"] = unit_tests()
        results["tools_tests"] = tools_tests()
        results["smoke"] = smoke()
    print("\n=== GATE ===")
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL':5} {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

`tools/install_hooks.py`: copy Everember's file (`$E/tools/install_hooks.py`) and change the marker line to `MARKER = "# aurelia-fast-gate"` and the uninstall message to `"no aurelia hook installed"`. Add a module docstring line is unchanged.

`tools/tests/` has no tests until Task 2; pytest exits 5 on an empty run, so add `tools/tests/test_gate_smoke.py`:

```python
"""The gate imports and names its steps (keeps pytest non-empty before Task 2)."""

from __future__ import annotations

from tools import gate


def test_gate_dirs_cover_every_gdscript_root() -> None:
    assert gate.GD_DIRS == ["core", "autoload", "scenes", "test"]


def test_heartbeats_start_with_boot() -> None:
    assert gate.HEARTBEATS[0] == "[boot]"
```

- [ ] **Step 5: Write the Game autoload helpers, the boot scene, and the first gdUnit4 test**

`test/unit/boot_test.gd` (write it first):

```gdscript
extends GdUnitTestSuite


func test_project_is_named_aurelia() -> void:
	assert_str(str(ProjectSettings.get_setting("application/config/name"))).is_equal("Aurelia")


func test_gdunit_run_is_detected_as_a_test_run() -> void:
	assert_bool(GameAutoload.is_test_run()).is_true()


func test_missing_flag_has_no_value() -> void:
	assert_str(GameAutoload.arg_value("--no-such-flag")).is_empty()
	assert_bool(GameAutoload.has_arg("--no-such-flag")).is_false()
```

`autoload/game.gd`:

```gdscript
class_name GameAutoload
extends Node

## Autoload: command-line helpers and the test-run guard. Task 7 adds the SimRoot it owns.
## Thin by design; simulation rules live in core/.


static func is_test_run() -> bool:
	for arg: String in OS.get_cmdline_args():
		if arg.contains("GdUnit"):
			return true
	return false


static func has_arg(flag: String) -> bool:
	return OS.get_cmdline_args().has(flag) or OS.get_cmdline_user_args().has(flag)


static func arg_value(flag: String) -> String:
	var all_args: PackedStringArray = OS.get_cmdline_args()
	all_args.append_array(OS.get_cmdline_user_args())
	var index: int = all_args.find(flag)
	if index < 0 or index + 1 >= all_args.size():
		return ""
	return all_args[index + 1]
```

`scenes/main.gd`:

```gdscript
extends Control

## Boot scene (SP2 placeholder): names the build and hosts the stub sandbox.


func _ready() -> void:
	var sandbox: String = GameAutoload.arg_value("--sandbox")
	var label := Label.new()
	label.text = "Aurelia" if sandbox.is_empty() else "Aurelia sandbox: %s" % sandbox
	add_child(label)
	print("[boot] %s" % ("main" if sandbox.is_empty() else "sandbox " + sandbox))
```

`scenes/main.tscn`:

```
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scenes/main.gd" id="1"]

[node name="Main" type="Control"]
layout_mode = 3
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
script = ExtResource("1")
```

- [ ] **Step 6: Write `CLAUDE.md`**

```markdown
# Aurelia: A Ledger of Stars (Godot)

Godot 4.7 narrative space-trading RPG, ported from the Python build at
`C:\Users\matth\PycharmProjects\SpaceGame` (the reference implementation). Master spec:
`docs/specs/2026-09-25-aurelia-overhaul-master-design.md`; SP2 spec:
`docs/specs/2026-09-26-sp2-foundation-design.md`. Plans live in `docs/plans/`; the queue is
`docs/roadmap.md`; environment: `docs/dev_setup.md`.

## Non-negotiables
- Typed GDScript. Untyped declarations are errors. Annotate every var, param, return.
- `core/` is the simulation core: RefCounted only, never Node, never get_tree().
- Views (`scenes/`) hold no game logic. They read core state and call core methods.
- Two autoloads: Game (class GameAutoload) and DataRegistry (DataRegistryAutoload). Type
  references against those class names and call their statics on the class.
- Files under ~300 lines, one responsibility per class, at most 25 public methods.
- TDD: failing gdUnit4 test first, then the minimal implementation, then refactor.
- Run `python tools/gate.py` before calling anything done. Green gate or it is not done.
- Wire it or delete it: nothing merges without a call site and a test proving it is wired.

## Porting from the Python reference
- Parity first: a subsystem is ported against its goldens (`test/parity/golden/`) and is not
  redesigned until its parity suite passes.
- Python `/` becomes a float division (`PyMath.true_div`); GDScript `int / int` truncates.
- Python `//` and `%` become `PyMath.floor_div_*` and `PyMath.floor_mod_*`.
- Python `round(x)` becomes `PyMath.round_half_even(x)`; `int(x)` stays `int(x)`.
- Keep Python's operand order and grouping in float expressions.
- Build dictionaries in Python's insertion order wherever order feeds a draw or an output list.
- Loaders cast by `data/schema.json`; Godot parses every JSON number as a float.
- All simulation randomness goes through `SimRng`; Godot's random functions are for
  presentation only. Inside `SimRng`, call `self.randf()`: a bare `randf()` is Godot's global.
- `data/` and `test/parity/golden/` are synced from SpaceGame by `tools/sync_data.py` and are
  never edited here; edit in SpaceGame, regenerate, and re-sync.

## Writing and canon
- Writing bible, voices, and culture live in SpaceGame `requirements/` until cutover:
  `dialogue_writing_guide.md`, `character_voices.md`, `cultural_guide.md`.
- Prose: no em-dashes, no "no X, no Y" constructions. Banned NPC names: Yara, Elara, Kael,
  Mara, Lydia, Clive, Magnus, Ambrose.
- Act I content stays in Act I. Only the crew (Elena Reeves, Marcus Jin, Dr. Priya Osei,
  Tomas Drifter), the perpetrators (Aldric Senn and the Ledger leadership), and the keepsakes
  cross into Act II.

## Commands
- Full gate: `python tools/gate.py`; tests only: `--tests-only`; pre-commit subset: `--fast`.
- Godot binary path lives in `tools/config.local.json` (git-ignored); use the console exe.
- Install the pre-commit hook once per clone: `python tools/install_hooks.py`
- Sync from SpaceGame: `python tools/sync_data.py --from ../SpaceGame`; verify: `--check`.
- Sandbox boot: `<godot> --path . -- --sandbox stub`
- Unattended run: `python tools/goal_run.py --print <slice>` (see `docs/autonomous_runs.md`).

## Godot MCP Pro
- Start Claude Code FROM this directory so `.mcp.json` loads the `godot-mcp-pro` server.
- The addon under `addons/godot_mcp/` is git-ignored. Restore from `C:\Users\matth\Tools\godot-mcp-pro\addons\`.
- While the editor runs, the addon injects `MCP*` autoloads into project.godot; never commit that diff.

## Layout
`core/` sim core · `autoload/` Game, DataRegistry · `scenes/` views · `data/` synced JSON ·
`test/` gdUnit4 suites and the parity harness · `tools/` Python gate and sync · `docs/` specs,
plans, roadmap, runbook
```

- [ ] **Step 7: Import, format, and run the gate**

```bash
cd /c/Users/matth/PycharmProjects/aurelia
mkdir -p core && touch core/.gitkeep
python tools/install_hooks.py
"C:/Users/matth/Tools/Godot/Godot_v4.7.2-stable_win64_console.exe" --headless --path . --import
gdformat core autoload scenes test
uv run black tools
python tools/gate.py
```

Expected: the gate prints `PASS` for format, lint, tools_format, tools_types, import, tests (3 tests), tools_tests, smoke; exit 0. `core/.gitkeep` lets gdformat and gdlint accept the path before Task 3 adds the first core script; delete it in Task 3.

- [ ] **Step 8: Commit**

```bash
git add -A
git status --short | grep -v "^A" || true
git commit -m "feat(sp2b): repo scaffold, gate, hooks, boot scene

Seeded from Everember: gdUnit4 6.2.1, gate guards, hook installer, goal runner.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

Check `git status` before committing: `addons/godot_mcp/`, `tools/config.local.json`, `.godot/`, and `reports/` must not be staged. The `*.gd.uid` files Godot generates are committed.

---

### Task 2: Sync from the Python reference

**Files:**
- Create: `tools/sync_data.py`, `tools/tests/test_sync_data.py`
- Modify: `tools/gate.py` (add the `sync` step)
- Create (generated): `data/**`, `data/schema.json`, `data/SYNC.json`, `test/parity/golden/**`

**Interfaces:**
- Produces: `sync(source: Path, root: Path) -> int`, `check(root: Path) -> int`, `main(argv: list[str] | None = None) -> int`; CLI `python tools/sync_data.py --from <SpaceGame> [--root <repo>]` and `--check [--root <repo>]`. Manifest `data/SYNC.json`: `{"source_repo": str, "source_commit": str, "files": {relative_posix_path: sha256_hex}}`.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_sync_data.py`:

```python
"""sync_data copies the reference's content and goldens and guards them (SP2 spec 8.5)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tools import sync_data


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture()
def source(tmp_path: Path) -> Path:
    repo = tmp_path / "SpaceGame"
    (repo / "data" / "economy").mkdir(parents=True)
    (repo / "data" / "economy" / "commodities.json").write_bytes(b'{"commodities": []}\r\n')
    (repo / "parity" / "golden" / "market").mkdir(parents=True)
    (repo / "parity" / "golden" / "market" / "one.json").write_bytes(b'{"format": 1}\n')
    (repo / "parity" / "schema.json").write_bytes(b'{"format": 1, "types": {}}\n')
    _git(repo, "init", "-q")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed")
    return repo


@pytest.fixture()
def target(tmp_path: Path) -> Path:
    root = tmp_path / "aurelia"
    root.mkdir()
    return root


def test_sync_copies_data_goldens_and_schema(source: Path, target: Path) -> None:
    assert sync_data.sync(source, target) == 0
    assert (target / "data" / "economy" / "commodities.json").is_file()
    assert (target / "test" / "parity" / "golden" / "market" / "one.json").is_file()
    assert (target / "data" / "schema.json").is_file()


def test_sync_normalizes_line_endings(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    assert b"\r\n" not in (target / "data" / "economy" / "commodities.json").read_bytes()


def test_manifest_records_commit_and_hashes(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    manifest = json.loads((target / "data" / "SYNC.json").read_text(encoding="utf-8"))
    assert len(manifest["source_commit"]) == 40
    assert "data/economy/commodities.json" in manifest["files"]
    assert "test/parity/golden/market/one.json" in manifest["files"]
    assert "data/schema.json" in manifest["files"]


def test_check_passes_after_sync(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    assert sync_data.check(target) == 0


def test_check_fails_on_an_edited_file(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    path = target / "data" / "economy" / "commodities.json"
    path.write_bytes(path.read_bytes() + b" ")
    assert sync_data.check(target) == 1


def test_check_fails_on_an_extra_file(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    (target / "data" / "economy" / "stray.json").write_text("{}", encoding="utf-8")
    assert sync_data.check(target) == 1


def test_resync_removes_stale_files(source: Path, target: Path) -> None:
    sync_data.sync(source, target)
    stale = target / "test" / "parity" / "golden" / "market" / "gone.json"
    stale.write_text("{}", encoding="utf-8")
    sync_data.sync(source, target)
    assert not stale.exists()


def test_refuses_a_dirty_source(source: Path, target: Path) -> None:
    (source / "data" / "economy" / "commodities.json").write_text("{}", encoding="utf-8")
    assert sync_data.sync(source, target) == 2


def test_check_without_manifest_fails(target: Path) -> None:
    assert sync_data.check(target) == 1
```

Run: `uv run pytest tools/tests/test_sync_data.py -q`
Expected: FAIL with `ImportError: cannot import name 'sync_data'`.

- [ ] **Step 2: Implement `tools/sync_data.py`**

```python
"""Copy the Python reference's content and goldens into this repo (SP2 spec 8.5).

Usage:
    python tools/sync_data.py --from ../SpaceGame     sync, then record data/SYNC.json
    python tools/sync_data.py --check                 verify nothing synced was edited

Synced trees are owned by the sync: SpaceGame/data/ -> data/, SpaceGame/parity/golden/ ->
test/parity/golden/, SpaceGame/parity/schema.json -> data/schema.json. Text files are written
with LF endings (this repo is eol=lf; SpaceGame's Windows checkout is CRLF) and hashed after
normalization, so a fresh clone checks clean.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path("data") / "SYNC.json"
TEXT_SUFFIXES = {".json", ".md", ".txt", ".csv"}
# (source relative dir, target relative dir) pairs; each target dir is owned by the sync.
TREES = [(Path("data"), Path("data")), (Path("parity/golden"), Path("test/parity/golden"))]
SCHEMA = (Path("parity/schema.json"), Path("data/schema.json"))


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _payload(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix in TEXT_SUFFIXES:
        return raw.replace(b"\r\n", b"\n")
    return raw


def _write(path: Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _owned_files(root: Path) -> set[str]:
    owned: set[str] = set()
    for _, target_dir in TREES:
        base = root / target_dir
        if base.exists():
            owned.update(p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file())
    owned.discard(MANIFEST.as_posix())
    return owned


def sync(source: Path, root: Path) -> int:
    """Copy the synced trees from ``source`` into ``root``.

    Returns:
        0 on success, 2 when the source working tree has uncommitted changes.
    """
    if _git(source, "status", "--porcelain"):
        print(f"Refusing to sync: {source} has uncommitted changes")
        return 2
    for _, target_dir in TREES:
        if (root / target_dir).exists():
            shutil.rmtree(root / target_dir)
    files: dict[str, str] = {}
    for source_dir, target_dir in TREES:
        for path in sorted((source / source_dir).rglob("*")):
            if path.is_file():
                relative = target_dir / path.relative_to(source / source_dir)
                files[relative.as_posix()] = _write(root / relative, _payload(path))
    files[SCHEMA[1].as_posix()] = _write(root / SCHEMA[1], _payload(source / SCHEMA[0]))
    manifest = {
        "source_repo": str(source.resolve()),
        "source_commit": _git(source, "rev-parse", "HEAD"),
        "files": dict(sorted(files.items())),
    }
    _write(root / MANIFEST, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(f"Synced {len(files)} files from {manifest['source_commit'][:10]}")
    return 0


def check(root: Path) -> int:
    """Verify every synced file matches its recorded hash and no stray file exists.

    Returns:
        0 when clean, 1 otherwise.
    """
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        print(f"No {MANIFEST}; run sync first")
        return 1
    recorded: dict[str, str] = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    problems: list[str] = []
    for relative, digest in recorded.items():
        path = root / relative
        if not path.is_file():
            problems.append(f"missing: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"edited: {relative}")
    for relative in sorted(_owned_files(root) - set(recorded)):
        problems.append(f"not synced: {relative}")
    for line in problems:
        print(line)
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.check:
        return check(root)
    if not args.source:
        parser.error("--from is required unless --check is given")
    return sync(Path(args.source), root)


if __name__ == "__main__":
    sys.exit(main())
```

Note `_owned_files` includes `data/schema.json` (it lives under `data/`) and excludes `data/SYNC.json`; both are in the manifest, so neither is reported as stray.

- [ ] **Step 3: Run the tests**

Run: `uv run pytest tools/tests/test_sync_data.py -q`
Expected: 9 passed.

- [ ] **Step 4: Add the gate step and run the first real sync**

In `tools/gate.py`, add:

```python
def sync_check() -> bool:
    return run("sync --check", [*UV, "python", "tools/sync_data.py", "--check"])[0]
```

and call it in the full gate directly after `tools_tests` (`results["sync"] = sync_check()`).

```bash
uv run python tools/sync_data.py --from /c/Users/matth/PycharmProjects/SpaceGame
uv run python tools/sync_data.py --check
ls test/parity/golden
```

Expected: `Synced N files ...`; `--check` exits 0; `test/parity/golden` lists `market`, `price_history`, `sim_rng`. Run `python tools/gate.py`: every step PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/sync_data.py tools/tests/test_sync_data.py tools/gate.py data test/parity/golden
git commit -m "feat(sp2b): sync content and goldens from the Python reference

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: SimRng

**Files:**
- Create: `core/rng/sim_rng.gd`
- Test: `test/unit/sim_rng_test.gd`

**Interfaces:**
- Produces (`class_name SimRng extends RefCounted`), statics: `from_state(s0: int, s1: int, s2: int, s3: int) -> SimRng`, `is_valid_part(part: Variant) -> bool`, `build_key(parts: Array) -> String`, `from_key(parts: Array) -> SimRng`, `from_digest(digest: PackedByteArray) -> SimRng`, `deserialize(words: Array) -> SimRng`, `stable_seed(parts: Array) -> int`; methods: `state() -> Array[int]`, `serialize() -> Array[String]`, `next_u32() -> int`, `randf() -> float`, `randint(lo: int, hi: int) -> int`, `uniform(a: float, b: float) -> float`, `chance(p: float) -> bool`, `choice(seq: Array) -> Variant`, `shuffle(items: Array) -> void`, `sample(population: Array, k: int) -> Array`, `weighted_index(weights: Array) -> int`, `random() -> float`, `choices(population: Array, weights: Variant = null, k: int = 1) -> Array`.

- [ ] **Step 1: Write the failing tests**

`test/unit/sim_rng_test.gd`:

```gdscript
extends GdUnitTestSuite


class ScriptedU32:
	extends SimRng

	var draws: Array[int] = []

	func next_u32() -> int:
		return draws.pop_front()


func test_reference_sequence_from_state_1_2_3_4() -> void:
	var rng := SimRng.from_state(1, 2, 3, 4)
	var got: Array[int] = []
	for i: int in range(6):
		got.append(rng.next_u32())
	assert_array(got).is_equal([11520, 0, 5927040, 70819200, 2031721883, 1637235492])


func test_md5_seeding_of_key_a() -> void:
	assert_array(SimRng.from_key(["a"]).state()).is_equal(
		[0xB975C10C, 0xA8B6F1C0, 0xE299C331, 0x61267769]
	)


func test_unicode_key_matches_python_md5() -> void:
	# Python: int.from_bytes(md5("Ωmega|naïve|星".encode()).digest()[:4], "little")
	assert_int(SimRng.from_key(["Ωmega", "naïve", "星"]).state()[0]).is_equal(118567268)


func test_all_zero_state_uses_fallback_word() -> void:
	assert_array(SimRng.from_state(0, 0, 0, 0).state()).is_equal([0x9E3779B9, 0, 0, 0])


func test_randf_is_top_24_bits() -> void:
	var a := SimRng.from_key(["k"])
	var b := SimRng.from_key(["k"])
	assert_float(a.randf()).is_equal(float(b.next_u32() >> 8) / 16777216.0)


func test_random_uses_this_stream_not_the_global_randf() -> void:
	var a := SimRng.from_key(["shadow"])
	var b := SimRng.from_key(["shadow"])
	assert_float(a.random()).is_equal(b.randf())
	assert_float(a.uniform(-1.0, 1.0)).is_equal(-1.0 + 2.0 * b.randf())


func test_key_parts() -> void:
	assert_str(SimRng.build_key(["market", 1, "iron_ore"])).is_equal("market|1|iron_ore")
	assert_str(SimRng.build_key(["neg", -5, ""])).is_equal("neg|-5|")
	assert_bool(SimRng.is_valid_part(&"name")).is_true()
	assert_bool(SimRng.is_valid_part(1.5)).is_false()
	assert_bool(SimRng.is_valid_part(true)).is_false()
	assert_bool(SimRng.is_valid_part(null)).is_false()


func test_stable_seed_is_first_state_word() -> void:
	assert_int(SimRng.stable_seed(["player", "Ada"])).is_equal(
		SimRng.from_key(["player", "Ada"]).state()[0]
	)


func test_randint_bounds_inclusive() -> void:
	var rng := SimRng.from_key(["randint"])
	var seen: Dictionary = {}
	for i: int in range(500):
		seen[rng.randint(1, 6)] = true
	assert_array(seen.keys()).contains_exactly_in_any_order([1, 2, 3, 4, 5, 6])


func test_randint_rejects_draws_at_or_above_limit() -> void:
	var rng := ScriptedU32.new()
	rng.draws = [4294967295, 7]
	assert_int(rng.randint(0, 2)).is_equal(1)


func test_sequences() -> void:
	var rng := SimRng.from_key(["seq"])
	var items: Array = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
	rng.shuffle(items)
	var sorted_items: Array = items.duplicate()
	sorted_items.sort()
	assert_array(sorted_items).is_equal([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
	assert_int(rng.sample([1, 2, 3], 3).size()).is_equal(3)
	assert_array(rng.sample([1, 2, 3], 0)).is_empty()
	for i: int in range(200):
		assert_int(rng.weighted_index([1.0, 0.0, 3.5])).is_not_equal(1)


func test_choices_matches_weighted_index() -> void:
	var a := SimRng.from_key(["cw"])
	var b := SimRng.from_key(["cw"])
	var picked: Variant = a.choices(["x", "y", "z"], [1, 2, 3], 1)[0]
	assert_str(str(picked)).is_equal(["x", "y", "z"][b.weighted_index([1, 2, 3])])


func test_serialize_round_trip() -> void:
	var rng := SimRng.from_key(["state"])
	rng.next_u32()
	var words: Array[String] = rng.serialize()
	var clone := SimRng.deserialize(JSON.parse_string(JSON.stringify(words)) as Array)
	assert_array(clone.state()).is_equal(rng.state())
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (the parser reports `SimRng` is not declared).

- [ ] **Step 2: Implement `core/rng/sim_rng.gd`**

```gdscript
class_name SimRng
extends RefCounted

## Portable deterministic generator, the twin of spacegame/sim_rng.py (SP2 spec 3).
## xoshiro128** seeded from the md5 of a "|"-joined key. Every intermediate stays below 2^36, so
## GDScript's signed 64-bit ints never overflow. Inside this class always call self.randf(): a
## bare randf() resolves to Godot's global randf, not this method.

const MASK32: int = 0xFFFFFFFF
const TWO_32: int = 4294967296
const FALLBACK_S0: int = 0x9E3779B9
const INV_2_24: float = 1.0 / 16777216.0

var _s0: int = 0
var _s1: int = 0
var _s2: int = 0
var _s3: int = 0


static func from_state(s0: int, s1: int, s2: int, s3: int) -> SimRng:
	var rng := SimRng.new()
	rng._set_state(s0, s1, s2, s3)
	return rng


static func is_valid_part(part: Variant) -> bool:
	var kind: int = typeof(part)
	return kind == TYPE_INT or kind == TYPE_STRING or kind == TYPE_STRING_NAME


static func build_key(parts: Array) -> String:
	var rendered: PackedStringArray = []
	for part: Variant in parts:
		if not is_valid_part(part):
			push_error("SimRng key parts must be String or int, got %s" % type_string(typeof(part)))
			return ""
		rendered.append(str(part))
	return "|".join(rendered)


static func from_key(parts: Array) -> SimRng:
	return from_digest(build_key(parts).md5_buffer())


static func from_digest(digest: PackedByteArray) -> SimRng:
	return from_state(
		digest.decode_u32(0), digest.decode_u32(4), digest.decode_u32(8), digest.decode_u32(12)
	)


static func deserialize(words: Array) -> SimRng:
	if words.size() != 4:
		push_error("SimRng state needs 4 words, got %d" % words.size())
		return from_state(0, 0, 0, 0)
	return from_state(
		str(words[0]).to_int(), str(words[1]).to_int(), str(words[2]).to_int(), str(words[3]).to_int()
	)


static func stable_seed(parts: Array) -> int:
	return from_key(parts).state()[0]


static func _rotl(x: int, k: int) -> int:
	return ((x << k) & MASK32) | (x >> (32 - k))


func state() -> Array[int]:
	return [_s0, _s1, _s2, _s3]


func serialize() -> Array[String]:
	return [str(_s0), str(_s1), str(_s2), str(_s3)]


func next_u32() -> int:
	var result: int = (_rotl((_s1 * 5) & MASK32, 7) * 9) & MASK32
	var t: int = (_s1 << 9) & MASK32
	_s2 ^= _s0
	_s3 ^= _s1
	_s1 ^= _s2
	_s0 ^= _s3
	_s2 ^= t
	_s3 = _rotl(_s3, 11)
	return result


func randf() -> float:
	return float(next_u32() >> 8) * INV_2_24


@warning_ignore("integer_division")
func randint(lo: int, hi: int) -> int:
	var n: int = hi - lo + 1
	if n < 1 or n > TWO_32:
		push_error("SimRng.randint span must be 1..2^32, got lo=%d hi=%d" % [lo, hi])
		return lo
	var limit: int = (TWO_32 / n) * n
	var x: int = next_u32()
	while x >= limit:
		x = next_u32()
	return lo + x % n


func uniform(a: float, b: float) -> float:
	return a + (b - a) * self.randf()


func chance(p: float) -> bool:
	return self.randf() < p


func choice(seq: Array) -> Variant:
	if seq.is_empty():
		push_error("SimRng.choice from an empty sequence")
		return null
	return seq[randint(0, seq.size() - 1)]


func shuffle(items: Array) -> void:
	for i: int in range(items.size() - 1, 0, -1):
		var j: int = randint(0, i)
		var held: Variant = items[i]
		items[i] = items[j]
		items[j] = held


func sample(population: Array, k: int) -> Array:
	var pool: Array = population.duplicate()
	var n: int = pool.size()
	if k < 0 or k > n:
		push_error("SimRng.sample size %d outside 0..%d" % [k, n])
		return []
	for i: int in range(k):
		var j: int = randint(i, n - 1)
		var held: Variant = pool[i]
		pool[i] = pool[j]
		pool[j] = held
	return pool.slice(0, k)


func weighted_index(weights: Array) -> int:
	var total: float = 0.0
	for w: Variant in weights:
		total += float(w)
	if weights.is_empty() or total <= 0.0:
		push_error("SimRng.weighted_index needs a positive weight")
		return -1
	var r: float = self.randf() * total
	var cumulative: float = 0.0
	for i: int in range(weights.size()):
		cumulative += float(weights[i])
		if r < cumulative:
			return i
	for i: int in range(weights.size() - 1, -1, -1):
		if float(weights[i]) > 0.0:
			return i
	return -1


func random() -> float:
	return self.randf()


func choices(population: Array, weights: Variant = null, k: int = 1) -> Array:
	var out: Array = []
	for i: int in range(k):
		if weights == null:
			out.append(choice(population))
		else:
			out.append(population[weighted_index(weights as Array)])
	return out


func _set_state(s0: int, s1: int, s2: int, s3: int) -> void:
	_s0 = s0 & MASK32
	_s1 = s1 & MASK32
	_s2 = s2 & MASK32
	_s3 = s3 & MASK32
	if _s0 == 0 and _s1 == 0 and _s2 == 0 and _s3 == 0:
		_s0 = FALLBACK_S0
```

Python adds each weight to a float total (`0.0 + 1` is `1.0`); `float(w)` before adding gives the same double for int weights.

- [ ] **Step 3: Run, format, gate, commit**

Run: `gdformat core test` then `python tools/gate.py`
Expected: every step PASS (the new suite passes).

```bash
git rm -q core/.gitkeep
git add core/rng test/unit/sim_rng_test.gd
git commit -m "feat(sp2b): SimRng, the GDScript twin of the portable generator

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: PyMath

**Files:**
- Create: `core/math/py_math.gd`
- Test: `test/unit/py_math_test.gd`

**Interfaces:**
- Produces (`class_name PyMath extends RefCounted`), statics: `round_half_even(x: float) -> int`, `floor_div_int(a: int, b: int) -> int`, `floor_mod_int(a: int, b: int) -> int`, `floor_div_float(a: float, b: float) -> float`, `floor_mod_float(a: float, b: float) -> float`, `true_div(a: float, b: float) -> float`.

- [ ] **Step 1: Write the failing tests**

The expected values were computed with CPython 3.13 while planning.

`test/unit/py_math_test.gd`:

```gdscript
extends GdUnitTestSuite


## Long decimals go through the same GDScript literal parser that misrounds long JSON decimals,
## so they are built from the IEEE bits CPython prints for them.
func _f(bits: int) -> float:
	var bytes := PackedByteArray()
	bytes.resize(8)
	bytes.encode_s64(0, bits)
	return bytes.decode_double(0)


func test_round_half_even_matches_python() -> void:
	var cases: Array = [
		[0.5, 0], [1.5, 2], [2.5, 2], [-0.5, 0], [-1.5, -2], [-2.5, -2],
		[_f(4612811918334230527), 2], [2.6, 3], [-2.6, -3], [_f(4602678819172646911), 0],
		[_f(4831355200913801220), 1000000000000000], [3.0, 3], [-3.0, -3],
	]
	for case: Array in cases:
		assert_int(PyMath.round_half_even(float(case[0]))).is_equal(int(case[1]))


func test_floor_div_int_matches_python() -> void:
	var cases: Array = [
		[7, 2, 3], [-7, 2, -4], [7, -2, -4], [-7, -2, 3], [6, 3, 2], [-6, 3, -2], [0, 5, 0],
		[-1, 3, -1],
	]
	for case: Array in cases:
		assert_int(PyMath.floor_div_int(int(case[0]), int(case[1]))).is_equal(int(case[2]))


func test_floor_mod_int_matches_python() -> void:
	var cases: Array = [[7, 2, 1], [-7, 2, 1], [7, -2, -1], [-7, -2, -1], [6, 3, 0], [-1, 3, 2]]
	for case: Array in cases:
		assert_int(PyMath.floor_mod_int(int(case[0]), int(case[1]))).is_equal(int(case[2]))


func test_floor_div_float_matches_python() -> void:
	var cases: Array = [
		[7.5, 2.0, 3.0], [-7.5, 2.0, -4.0], [7.5, -2.0, -4.0], [1.0, 0.1, 9.0], [-1.0, 0.1, -10.0],
		[0.0, 3.0, 0.0],
	]
	for case: Array in cases:
		assert_float(PyMath.floor_div_float(float(case[0]), float(case[1]))).is_equal(
			float(case[2])
		)


func test_floor_mod_float_matches_python() -> void:
	var cases: Array = [
		[7.5, 2.0, 1.5], [-7.5, 2.0, 0.5], [7.5, -2.0, -0.5], [1.0, 0.1, _f(4591870180066957718)],
		[-1.0, 0.1, _f(4363988038922010624)],
	]
	for case: Array in cases:
		assert_float(PyMath.floor_mod_float(float(case[0]), float(case[1]))).is_equal(
			float(case[2])
		)


func test_true_div_is_float_division() -> void:
	assert_float(PyMath.true_div(7, 2)).is_equal(3.5)
	assert_float(PyMath.true_div(-7, 2)).is_equal(-3.5)
	assert_float(PyMath.true_div(1, 3)).is_equal(_f(4599676419421066581))
```

The bits were printed by CPython 3.13 while planning: `2.4999999999999996` is 4612811918334230527, `0.49999999999999994` is 4602678819172646911, `1000000000000000.5` is 4831355200913801220, `0.09999999999999995` is 4591870180066957718, `5.551115123125783e-17` is 4363988038922010624, `0.3333333333333333` is 4599676419421066581. Short literals (one or two significant digits) parse exactly; a probe of every float in SpaceGame's data files (at most four digits) found no misrounding.

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`PyMath` not declared).

- [ ] **Step 2: Implement `core/math/py_math.gd`**

```gdscript
class_name PyMath
extends RefCounted

## Python 3 arithmetic for ported simulation code (SP2 spec 8.3; CLAUDE.md porting rules).
## Float floor division and modulo follow CPython's float_floor_div and float_rem exactly.


static func round_half_even(x: float) -> int:
	var f: float = floorf(x)
	var diff: float = x - f
	var fi: int = int(f)
	if diff > 0.5:
		return fi + 1
	if diff < 0.5:
		return fi
	return fi if floor_mod_int(fi, 2) == 0 else fi + 1


@warning_ignore("integer_division")
static func floor_div_int(a: int, b: int) -> int:
	var q: int = a / b
	if a % b != 0 and (a < 0) != (b < 0):
		q -= 1
	return q


static func floor_mod_int(a: int, b: int) -> int:
	var m: int = a % b
	if m != 0 and (m < 0) != (b < 0):
		m += b
	return m


static func floor_div_float(a: float, b: float) -> float:
	var mod: float = fmod(a, b)
	var div: float = (a - mod) / b
	if mod != 0.0 and (b < 0.0) != (mod < 0.0):
		div -= 1.0
	if div == 0.0:
		var quotient: float = a / b
		return -0.0 if quotient < 0.0 or (quotient == 0.0 and 1.0 / quotient < 0.0) else 0.0
	var floordiv: float = floorf(div)
	if div - floordiv > 0.5:
		floordiv += 1.0
	return floordiv


static func floor_mod_float(a: float, b: float) -> float:
	var mod: float = fmod(a, b)
	if mod != 0.0:
		if (b < 0.0) != (mod < 0.0):
			mod += b
		return mod
	return -0.0 if b < 0.0 else 0.0


static func true_div(a: float, b: float) -> float:
	return a / b
```

- [ ] **Step 3: Run, format, gate, commit**

Run: `gdformat core test` then `python tools/gate.py`
Expected: every step PASS.

```bash
git add core/math test/unit/py_math_test.gd
git commit -m "feat(sp2b): PyMath, Python arithmetic semantics for ports

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: The parity harness, proven on the SimRng vectors

**Files:**
- Create: `test/parity/golden_codec.gd`, `test/parity/comparator.gd`, `test/parity/parity_adapter.gd`, `test/parity/parity_runner.gd`, `test/parity/adapters/sim_rng_adapter.gd`
- Test: `test/parity/golden_codec_test.gd`, `test/parity/comparator_test.gd`, `test/parity/parity_runner_test.gd`, `test/parity/sim_rng_parity_test.gd`

**Interfaces:**
- Consumes: `SimRng` (Task 3); synced `test/parity/golden/sim_rng/*.json` (Task 2).
- Produces:
  - `GoldenCodec.decode(value: Variant) -> Variant`, `GoldenCodec.bits_to_float(bits: int) -> float`
  - `ParityComparator.diff(expected: Variant, actual: Variant, path: String) -> Array[String]`
  - `ParityAdapter` with overridable `setup(setup_data: Dictionary) -> void`, `call_step(call_name: String, args: Array) -> Variant`, `snapshot() -> Dictionary`; static `key_parts(raw: Array) -> Array` (whole-number floats back to ints)
  - `ParityRunner.GOLDEN_ROOT`, `case_names(subsystem: String) -> PackedStringArray`, `load_case(subsystem: String, case_name: String) -> Dictionary`, `replay(document: Dictionary, adapter: ParityAdapter) -> Array[String]`, `replay_subsystem(subsystem: String, make_adapter: Callable) -> Array[String]`
  - `SimRngAdapter` (subsystem `sim_rng`)

- [ ] **Step 1: Write the failing codec and comparator tests**

`test/parity/golden_codec_test.gd`:

```gdscript
extends GdUnitTestSuite


func test_tagged_float_decodes_to_the_exact_double() -> void:
	assert_float(GoldenCodec.decode("f:0.1:4591870180066957722") as float).is_equal(0.1)
	assert_float(GoldenCodec.decode("f:0.16799999999999998:4595220858189721370") as float).is_equal(
		GoldenCodec.bits_to_float(4595220858189721370)
	)


func test_negative_zero_decodes_without_overflow() -> void:
	var value: float = GoldenCodec.decode("f:-0.0:-9223372036854775808") as float
	assert_float(value).is_equal(0.0)
	assert_float(1.0 / value).is_less(0.0)


func test_untagged_values_pass_through_recursively() -> void:
	var decoded: Variant = GoldenCodec.decode({"a": ["x", "f:1.5:4609434218613702656", 3.0]})
	assert_dict(decoded as Dictionary).is_equal({"a": ["x", 1.5, 3.0]})


func test_strings_that_only_look_tagged_are_left_alone() -> void:
	assert_str(GoldenCodec.decode("Stock depleted: 95 remaining") as String).is_equal(
		"Stock depleted: 95 remaining"
	)
	assert_str(GoldenCodec.decode("f:not:a-number") as String).is_equal("f:not:a-number")
```

`test/parity/comparator_test.gd`:

```gdscript
extends GdUnitTestSuite


func test_int_and_float_compare_numerically() -> void:
	assert_array(ParityComparator.diff(10.0, 10, "x")).is_empty()


func test_one_bit_float_difference_fails() -> void:
	var a: float = GoldenCodec.bits_to_float(4595220858189721370)
	var b: float = GoldenCodec.bits_to_float(4595220858189721371)
	assert_array(ParityComparator.diff(a, b, "x")).has_size(1)


func test_string_and_string_name_compare_as_text() -> void:
	assert_array(ParityComparator.diff("food", &"food", "x")).is_empty()


func test_type_mismatch_is_reported() -> void:
	var failures: Array[String] = ParityComparator.diff(true, 1, "flag")
	assert_int(failures.size()).is_equal(1)
	assert_str(failures[0]).starts_with("flag:")


func test_dictionary_key_sets_must_match_and_paths_nest() -> void:
	var failures: Array[String] = ParityComparator.diff(
		{"stock": {"iron_ore": 40.0}, "gone": 1}, {"stock": {"iron_ore": 39}, "new": 2}, "state"
	)
	assert_array(failures).contains(["state.stock.iron_ore: expected 40.0, got 39"])
	assert_int(failures.size()).is_equal(3)


func test_list_length_mismatch_is_reported() -> void:
	assert_array(ParityComparator.diff([1, 2], [1], "list")).has_size(1)


func test_null_matches_null() -> void:
	assert_array(ParityComparator.diff(null, null, "x")).is_empty()
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`GoldenCodec`, `ParityComparator` not declared).

- [ ] **Step 2: Implement `GoldenCodec` and `ParityComparator`**

`test/parity/golden_codec.gd`:

```gdscript
class_name GoldenCodec
extends RefCounted

## Decodes golden JSON. The Python writer stores every float as "f:<repr>:<int64 bits>" because
## Godot's JSON parser misrounds about a quarter of long decimals by one bit (probe, 2026-09-26);
## the bits give back the exact double. Everything else passes through unchanged.

const INT64_MIN_TEXT: String = "-9223372036854775808"

static var _tag: RegEx = RegEx.create_from_string("^f:[^:]+:-?[0-9]+$")


static func decode(value: Variant) -> Variant:
	var decoded: Variant = value
	match typeof(value):
		TYPE_STRING:
			var text: String = str(value)
			if _tag.search(text) != null:
				var bits_text: String = text.get_slice(":", 2)
				decoded = -0.0 if bits_text == INT64_MIN_TEXT else bits_to_float(bits_text.to_int())
		TYPE_DICTIONARY:
			var out_dict: Dictionary = {}
			var source: Dictionary = value as Dictionary
			for key: Variant in source:
				out_dict[key] = decode(source[key])
			decoded = out_dict
		TYPE_ARRAY:
			var out_array: Array = []
			for item: Variant in value as Array:
				out_array.append(decode(item))
			decoded = out_array
	return decoded


static func bits_to_float(bits: int) -> float:
	var bytes := PackedByteArray()
	bytes.resize(8)
	bytes.encode_s64(0, bits)
	return bytes.decode_double(0)
```

`test/parity/comparator.gd`:

```gdscript
class_name ParityComparator
extends RefCounted

## Exact comparison of decoded golden values against GDScript values (SP2 spec 8.7). Ints and
## floats compare numerically (JSON gives Godot every number as a float), String and StringName
## compare as text, key sets and list lengths must match, and every failure names its path.
## A tolerance needs a written ruling in docs/parity/deviations.md.


static func diff(expected: Variant, actual: Variant, path: String) -> Array[String]:
	var failures: Array[String] = []
	_diff(expected, actual, path, failures)
	return failures


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT


static func _is_text(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING or typeof(value) == TYPE_STRING_NAME


static func _show(value: Variant) -> String:
	if typeof(value) == TYPE_FLOAT:
		return var_to_str(value)
	if _is_text(value):
		return JSON.stringify(str(value))
	return str(value)


static func _diff(expected: Variant, actual: Variant, path: String, failures: Array[String]) -> void:
	if _is_number(expected) and _is_number(actual):
		if float(expected) != float(actual):
			failures.append("%s: expected %s, got %s" % [path, _show(expected), _show(actual)])
		return
	if _is_text(expected) and _is_text(actual):
		if str(expected) != str(actual):
			failures.append("%s: expected %s, got %s" % [path, _show(expected), _show(actual)])
		return
	if typeof(expected) != typeof(actual):
		failures.append(
			(
				"%s: expected %s %s, got %s %s"
				% [
					path,
					type_string(typeof(expected)),
					_show(expected),
					type_string(typeof(actual)),
					_show(actual),
				]
			)
		)
		return
	if typeof(expected) == TYPE_DICTIONARY:
		_diff_dict(expected as Dictionary, actual as Dictionary, path, failures)
	elif typeof(expected) == TYPE_ARRAY:
		_diff_array(expected as Array, actual as Array, path, failures)
	elif expected != actual:
		failures.append("%s: expected %s, got %s" % [path, _show(expected), _show(actual)])


static func _diff_dict(
	expected: Dictionary, actual: Dictionary, path: String, failures: Array[String]
) -> void:
	var keys: Array = expected.keys()
	keys.sort()
	for key: Variant in keys:
		if actual.has(key):
			_diff(expected[key], actual[key], "%s.%s" % [path, key], failures)
		else:
			failures.append("%s: missing key %s" % [path, key])
	var extra: Array = actual.keys()
	extra.sort()
	for key: Variant in extra:
		if not expected.has(key):
			failures.append("%s: unexpected key %s" % [path, key])


static func _diff_array(expected: Array, actual: Array, path: String, failures: Array[String]) -> void:
	if expected.size() != actual.size():
		failures.append("%s: expected %d items, got %d" % [path, expected.size(), actual.size()])
		return
	for i: int in range(expected.size()):
		_diff(expected[i], actual[i], "%s[%d]" % [path, i], failures)
```

Run: `gdformat test` then `python tools/gate.py --tests-only`
Expected: the codec and comparator suites PASS.

- [ ] **Step 3: Write the failing runner tests**

`test/parity/parity_runner_test.gd`:

```gdscript
extends GdUnitTestSuite


class CounterAdapter:
	extends ParityAdapter

	var count: int = 0

	func setup(setup_data: Dictionary) -> void:
		count = int(setup_data["start"])

	func call_step(call_name: String, args: Array) -> Variant:
		if call_name == "add":
			count += int(args[0])
			return count
		return super.call_step(call_name, args)

	func snapshot() -> Dictionary:
		return {"count": count}


func _document(steps: Array) -> Dictionary:
	return {"setup": {"start": 0.0}, "steps": steps}


func test_matching_trace_replays_clean() -> void:
	var doc: Dictionary = _document(
		[
			{"call": "add", "args": [2.0], "result": 2.0, "state": {"count": 2.0}},
			{"call": "add", "args": [3.0], "result": 5.0, "state": {"count": 5.0}},
		]
	)
	assert_array(ParityRunner.replay(doc, CounterAdapter.new())).is_empty()


func test_replay_stops_at_the_first_divergent_step() -> void:
	var doc: Dictionary = _document(
		[
			{"call": "add", "args": [2.0], "result": 2.0, "state": {"count": 2.0}},
			{"call": "add", "args": [3.0], "result": 6.0, "state": {"count": 6.0}},
			{"call": "add", "args": [1.0], "result": 99.0, "state": {"count": 99.0}},
		]
	)
	var failures: Array[String] = ParityRunner.replay(doc, CounterAdapter.new())
	assert_str(failures[0]).starts_with("steps[1] add")
	assert_array(failures).contains(["steps[1].result: expected 6.0, got 5"])
	for line: String in failures:
		assert_str(line).not_contains("steps[2]")


func test_unhandled_call_fails_the_step() -> void:
	var doc: Dictionary = _document(
		[{"call": "mystery", "args": [], "result": null, "state": {"count": 0.0}}]
	)
	assert_array(ParityRunner.replay(doc, CounterAdapter.new())).is_not_empty()


func test_key_parts_turn_whole_floats_back_into_ints() -> void:
	assert_array(ParityAdapter.key_parts(["neg", -5.0, "x"])).is_equal(["neg", -5, "x"])
```

`test/parity/sim_rng_parity_test.gd`:

```gdscript
extends GdUnitTestSuite

const EXPECTED_CASES: int = 6


func test_every_sim_rng_golden_replays_clean() -> void:
	assert_int(ParityRunner.case_names("sim_rng").size()).is_equal(EXPECTED_CASES)
	var failures: Array[String] = ParityRunner.replay_subsystem(
		"sim_rng", func() -> ParityAdapter: return SimRngAdapter.new()
	)
	assert_str("\n".join(failures)).is_empty()
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`ParityRunner`, `ParityAdapter`, `SimRngAdapter` not declared).

- [ ] **Step 4: Implement the adapter base, the runner, and the SimRng adapter**

`test/parity/parity_adapter.gd`:

```gdscript
class_name ParityAdapter
extends RefCounted

## Bridges one golden subsystem to its GDScript port (SP2 spec 8.7). Subclasses map golden call
## names to port methods, cast args (every golden number arrives as a float), and snapshot the
## state the Python driver recorded.


static func key_parts(raw: Array) -> Array:
	var parts: Array = []
	for part: Variant in raw:
		if typeof(part) == TYPE_FLOAT and float(part) == floorf(float(part)):
			parts.append(int(part))
		else:
			parts.append(part)
	return parts


func setup(_setup_data: Dictionary) -> void:
	pass


func call_step(call_name: String, _args: Array) -> Variant:
	return "unhandled golden call: %s" % call_name


func snapshot() -> Dictionary:
	return {}
```

`test/parity/parity_runner.gd`:

```gdscript
class_name ParityRunner
extends RefCounted

## Replays golden traces from the Python reference through a ParityAdapter (SP2 spec 8.7).
## Each case stops at its first divergent step, which is where a porting bug first shows.

const GOLDEN_ROOT: String = "res://test/parity/golden"


static func case_names(subsystem: String) -> PackedStringArray:
	var names: PackedStringArray = []
	for file: String in DirAccess.get_files_at(GOLDEN_ROOT.path_join(subsystem)):
		if file.ends_with(".json"):
			names.append(file.trim_suffix(".json"))
	names.sort()
	return names


static func load_case(subsystem: String, case_name: String) -> Dictionary:
	var path: String = GOLDEN_ROOT.path_join(subsystem).path_join(case_name + ".json")
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		push_error("ParityRunner: %s is not a JSON object" % path)
		return {}
	return GoldenCodec.decode(parsed) as Dictionary


static func replay(document: Dictionary, adapter: ParityAdapter) -> Array[String]:
	adapter.setup(document["setup"] as Dictionary)
	var steps: Array = document["steps"] as Array
	for i: int in range(steps.size()):
		var step: Dictionary = steps[i] as Dictionary
		var result: Variant = adapter.call_step(str(step["call"]), step["args"] as Array)
		var failures: Array[String] = ParityComparator.diff(
			step["result"], result, "steps[%d].result" % i
		)
		failures.append_array(
			ParityComparator.diff(step["state"], adapter.snapshot(), "steps[%d].state" % i)
		)
		if not failures.is_empty():
			failures.push_front("steps[%d] %s %s" % [i, step["call"], str(step["args"])])
			return failures
	return []


static func replay_subsystem(subsystem: String, make_adapter: Callable) -> Array[String]:
	var failures: Array[String] = []
	for case_name: String in case_names(subsystem):
		var adapter: ParityAdapter = make_adapter.call() as ParityAdapter
		for line: String in replay(load_case(subsystem, case_name), adapter):
			failures.append("%s/%s: %s" % [subsystem, case_name, line])
	return failures
```

`test/parity/adapters/sim_rng_adapter.gd`:

```gdscript
class_name SimRngAdapter
extends ParityAdapter

## Replays the sim_rng vectors (SP2 spec 3.4) against one SimRng stream.

var _rng: SimRng


func setup(setup_data: Dictionary) -> void:
	_rng = SimRng.from_key(ParityAdapter.key_parts(setup_data["key"] as Array))


func call_step(call_name: String, args: Array) -> Variant:
	var result: Variant = null
	match call_name:
		"state":
			result = _rng.state()
		"next_u32":
			result = _rng.next_u32()
		"randf":
			result = _rng.randf()
		"randint":
			result = _rng.randint(int(args[0]), int(args[1]))
		"uniform":
			result = _rng.uniform(float(args[0]), float(args[1]))
		"choice":
			result = _rng.choice(args[0] as Array)
		"shuffle":
			var items: Array = (args[0] as Array).duplicate()
			_rng.shuffle(items)
			result = items
		"sample":
			result = _rng.sample(args[0] as Array, int(args[1]))
		"weighted_index":
			result = _rng.weighted_index(args[0] as Array)
		"choices":
			result = _rng.choices(args[0] as Array, args[1] as Array, int(args[2]))
		_:
			result = super.call_step(call_name, args)
	return result


func snapshot() -> Dictionary:
	return {"s": _rng.state()}
```

- [ ] **Step 5: Run, format, gate, commit**

Run: `gdformat test` then `python tools/gate.py`
Expected: every step PASS; `sim_rng_parity_test` reports 6 cases clean. A failure names the case, the step, and the path: fix `SimRng` (Task 3's file), never the golden.

```bash
git add test/parity
git commit -m "feat(sp2b): parity harness, proven on the SimRng vectors

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Schema casts and typed content

**Files:**
- Create: `core/data/schema_cast.gd`, `core/data/sim_data.gd`, `core/galaxy/coordinates.gd`, `core/galaxy/station.gd`, `core/galaxy/economy.gd`, `core/galaxy/star_system.gd`, `core/economy/commodity.gd`
- Test: `test/unit/schema_cast_test.gd`, `test/unit/sim_data_test.gd`

**Interfaces:**
- Produces:
  - `SchemaCast.from_json(text: String) -> SchemaCast`, `cast_record(type_name: String, raw: Dictionary) -> Dictionary`, `cast_value(value: Variant, type_str: String) -> Variant`
  - `Commodity` fields `id, name, category, description: String`, `base_price: int`, `variance_min, variance_max: float`, `volume_per_unit: int`, `legality: String`, `production_tags, consumption_tags: Array[String]`; `static from_record(rec: Dictionary) -> Commodity`; `is_produced_by(system_tags: Array[String]) -> bool`; `is_consumed_by(system_tags: Array[String]) -> bool`
  - `Coordinates` (`x, y: float`), `Station` (`id, name, type, description: String`, `docking_fee: int`, `market_variety: String`), `Economy` (`production_tags, consumption_tags: Array[String]`, `tariff_rate: float`, `restricts_availability: bool`, `available_commodities, specialty_exports, specialty_imports: Array[String]`), `StarSystem` (`id, name, type, description, danger_level, faction: String`, `coordinates: Coordinates`, `stations: Array[Station]`, `economy: Economy`, `rest_cost: int`); each with `static from_record(rec: Dictionary)`
  - `SimData` fields `commodities: Array[Commodity]`, `commodity_by_id: Dictionary`, `systems: Array[StarSystem]`, `system_by_id: Dictionary`; `static load_from(root: String) -> SimData` (null on failure)

- [ ] **Step 1: Write the failing tests**

`test/unit/schema_cast_test.gd`:

```gdscript
extends GdUnitTestSuite

const SCHEMA: String = """{"format": 1, "types": {
	"Item": {"id": "str", "count": "int", "weight": "float", "kind": "enum",
		"tags": "list<str>", "extra": "optional<list<str>>", "child": "Child",
		"children": "list<Child>"},
	"Child": {"n": "int"}}}"""


func _item() -> Dictionary:
	return {
		"id": "a", "count": 10.0, "weight": 2.0, "kind": "basic", "tags": ["x"],
		"child": {"n": 3.0}, "children": [{"n": 1.0}], "ignored": true,
	}


func test_int_fields_become_ints() -> void:
	var rec: Dictionary = SchemaCast.from_json(SCHEMA).cast_record("Item", _item())
	assert_int(typeof(rec["count"])).is_equal(TYPE_INT)
	assert_int(typeof(rec["weight"])).is_equal(TYPE_FLOAT)
	assert_int(typeof((rec["child"] as Dictionary)["n"])).is_equal(TYPE_INT)
	assert_int(typeof(((rec["children"] as Array)[0] as Dictionary)["n"])).is_equal(TYPE_INT)


func test_missing_optional_is_null_and_unknown_keys_are_dropped() -> void:
	var rec: Dictionary = SchemaCast.from_json(SCHEMA).cast_record("Item", _item())
	assert_that(rec["extra"]).is_null()
	assert_bool(rec.has("ignored")).is_false()


func test_missing_list_defaults_to_empty() -> void:
	var raw: Dictionary = _item()
	raw.erase("tags")
	var rec: Dictionary = SchemaCast.from_json(SCHEMA).cast_record("Item", raw)
	assert_array(rec["tags"] as Array).is_empty()


func test_present_optional_list_is_cast() -> void:
	var raw: Dictionary = _item()
	raw["extra"] = []
	var rec: Dictionary = SchemaCast.from_json(SCHEMA).cast_record("Item", raw)
	assert_that(rec["extra"]).is_not_null()
	assert_array(rec["extra"] as Array).is_empty()
```

`test/unit/sim_data_test.gd`:

```gdscript
extends GdUnitTestSuite


func _raw_count(path: String, key: String) -> int:
	var parsed: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path)) as Dictionary
	return (parsed[key] as Array).size()


func test_loads_every_commodity_and_system() -> void:
	var data := SimData.load_from("res://data")
	assert_object(data).is_not_null()
	assert_int(data.commodities.size()).is_equal(
		_raw_count("res://data/economy/commodities.json", "commodities")
	)
	assert_int(data.systems.size()).is_equal(_raw_count("res://data/galaxy/systems.json", "systems"))


func test_commodity_numbers_are_typed() -> void:
	var food: Commodity = SimData.load_from("res://data").commodity_by_id["food"] as Commodity
	assert_int(typeof(food.base_price)).is_equal(TYPE_INT)
	assert_int(typeof(food.variance_min)).is_equal(TYPE_FLOAT)


func test_an_empty_availability_list_still_restricts() -> void:
	var heron: StarSystem = SimData.load_from("res://data").system_by_id["herons_mark"] as StarSystem
	assert_bool(heron.economy.restricts_availability).is_true()
	assert_array(heron.economy.available_commodities).is_empty()


func test_specialties_and_stations_load() -> void:
	var nexus: StarSystem = SimData.load_from("res://data").system_by_id["nexus_prime"] as StarSystem
	assert_array(nexus.economy.specialty_exports).contains(["electronics"])
	assert_int(nexus.stations.size()).is_greater(0)
	assert_int(typeof(nexus.stations[0].docking_fee)).is_equal(TYPE_INT)
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`SchemaCast`, `SimData` not declared).

- [ ] **Step 2: Implement `SchemaCast`**

`core/data/schema_cast.gd`:

```gdscript
class_name SchemaCast
extends RefCounted

## Casts parsed JSON (every number a float in Godot) to the field types in data/schema.json
## (SP2 spec 7.5). Only schema fields are kept. A missing optional field is null and a missing
## list is empty, matching the Python loader's defaults; any other missing field is an error.

var _types: Dictionary = {}


static func from_json(text: String) -> SchemaCast:
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary or not (parsed as Dictionary).has("types"):
		push_error("SchemaCast: malformed schema")
		return null
	var schema := SchemaCast.new()
	schema._types = (parsed as Dictionary)["types"] as Dictionary
	return schema


func cast_record(type_name: String, raw: Dictionary) -> Dictionary:
	if not _types.has(type_name):
		push_error("SchemaCast: unknown type %s" % type_name)
		return {}
	var fields: Dictionary = _types[type_name] as Dictionary
	var out: Dictionary = {}
	for field: Variant in fields:
		var type_str: String = str(fields[field])
		if raw.has(field):
			out[field] = cast_value(raw[field], type_str)
		elif type_str.begins_with("optional<"):
			out[field] = null
		elif type_str.begins_with("list<"):
			out[field] = []
		else:
			push_error("SchemaCast: %s is missing field %s" % [type_name, field])
			return {}
	return out


func cast_value(value: Variant, type_str: String) -> Variant:
	var result: Variant = null
	if type_str == "int":
		result = int(value)
	elif type_str == "float":
		result = float(value)
	elif type_str == "str" or type_str == "enum":
		result = str(value)
	elif type_str == "bool":
		result = bool(value)
	elif type_str.begins_with("optional<"):
		result = null if value == null else cast_value(value, _inner(type_str))
	elif type_str.begins_with("list<"):
		var items: Array = []
		for item: Variant in value as Array:
			items.append(cast_value(item, _inner(type_str)))
		result = items
	elif _types.has(type_str):
		result = cast_record(type_str, value as Dictionary)
	else:
		push_error("SchemaCast: unsupported type %s" % type_str)
	return result


static func _inner(type_str: String) -> String:
	return type_str.substr(type_str.find("<") + 1, type_str.length() - type_str.find("<") - 2)
```

- [ ] **Step 3: Implement the typed content**

`core/economy/commodity.gd`:

```gdscript
class_name Commodity
extends RefCounted

## A tradeable good; port of spacegame/models/commodity.py.

var id: String = ""
var name: String = ""
var category: String = ""
var description: String = ""
var base_price: int = 0
var variance_min: float = 0.0
var variance_max: float = 0.0
var volume_per_unit: int = 0
var legality: String = ""
var production_tags: Array[String] = []
var consumption_tags: Array[String] = []


static func from_record(rec: Dictionary) -> Commodity:
	var c := Commodity.new()
	c.id = str(rec["id"])
	c.name = str(rec["name"])
	c.category = str(rec["category"])
	c.description = str(rec["description"])
	c.base_price = int(rec["base_price"])
	c.variance_min = float(rec["variance_min"])
	c.variance_max = float(rec["variance_max"])
	c.volume_per_unit = int(rec["volume_per_unit"])
	c.legality = str(rec["legality"])
	c.production_tags.assign(rec["production_tags"] as Array)
	c.consumption_tags.assign(rec["consumption_tags"] as Array)
	return c


func is_produced_by(system_tags: Array[String]) -> bool:
	for tag: String in production_tags:
		if system_tags.has(tag):
			return true
	return false


func is_consumed_by(system_tags: Array[String]) -> bool:
	for tag: String in consumption_tags:
		if system_tags.has(tag):
			return true
	return false
```

`core/galaxy/coordinates.gd`:

```gdscript
class_name Coordinates
extends RefCounted

## 2D coordinates of a star system.

var x: float = 0.0
var y: float = 0.0


static func from_record(rec: Dictionary) -> Coordinates:
	var c := Coordinates.new()
	c.x = float(rec["x"])
	c.y = float(rec["y"])
	return c
```

`core/galaxy/station.gd`:

```gdscript
class_name Station
extends RefCounted

## A station within a star system.

var id: String = ""
var name: String = ""
var type: String = ""
var description: String = ""
var docking_fee: int = 0
var market_variety: String = ""


static func from_record(rec: Dictionary) -> Station:
	var s := Station.new()
	s.id = str(rec["id"])
	s.name = str(rec["name"])
	s.type = str(rec["type"])
	s.description = str(rec["description"])
	s.docking_fee = int(rec["docking_fee"])
	s.market_variety = str(rec["market_variety"])
	return s
```

`core/galaxy/economy.gd`:

```gdscript
class_name Economy
extends RefCounted

## A star system's economic profile. Python's Optional availability list becomes
## restricts_availability plus the list (an empty list still restricts: nothing is stocked).

var production_tags: Array[String] = []
var consumption_tags: Array[String] = []
var tariff_rate: float = 0.0
var restricts_availability: bool = false
var available_commodities: Array[String] = []
var specialty_exports: Array[String] = []
var specialty_imports: Array[String] = []


static func from_record(rec: Dictionary) -> Economy:
	var e := Economy.new()
	e.production_tags.assign(rec["production_tags"] as Array)
	e.consumption_tags.assign(rec["consumption_tags"] as Array)
	e.tariff_rate = float(rec["tariff_rate"])
	if rec["available_commodities"] != null:
		e.restricts_availability = true
		e.available_commodities.assign(rec["available_commodities"] as Array)
	e.specialty_exports.assign(rec["specialty_exports"] as Array)
	e.specialty_imports.assign(rec["specialty_imports"] as Array)
	return e
```

`core/galaxy/star_system.gd`:

```gdscript
class_name StarSystem
extends RefCounted

## A star system; port of the fields of spacegame/models/system.py that SP2 needs.

var id: String = ""
var name: String = ""
var type: String = ""
var description: String = ""
var coordinates: Coordinates
var danger_level: String = ""
var faction: String = ""
var stations: Array[Station] = []
var economy: Economy
var rest_cost: int = 0


static func from_record(rec: Dictionary) -> StarSystem:
	var s := StarSystem.new()
	s.id = str(rec["id"])
	s.name = str(rec["name"])
	s.type = str(rec["type"])
	s.description = str(rec["description"])
	s.coordinates = Coordinates.from_record(rec["coordinates"] as Dictionary)
	s.danger_level = str(rec["danger_level"])
	s.faction = str(rec["faction"])
	for station: Variant in rec["stations"] as Array:
		s.stations.append(Station.from_record(station as Dictionary))
	s.economy = Economy.from_record(rec["economy"] as Dictionary)
	s.rest_cost = int(rec["rest_cost"])
	return s
```

`core/data/sim_data.gd`:

```gdscript
class_name SimData
extends RefCounted

## Typed simulation content loaded from the synced data/ tree, in the files' order.

var commodities: Array[Commodity] = []
var commodity_by_id: Dictionary = {}
var systems: Array[StarSystem] = []
var system_by_id: Dictionary = {}


static func load_from(root: String) -> SimData:
	var schema := SchemaCast.from_json(FileAccess.get_file_as_string(root.path_join("schema.json")))
	if schema == null:
		return null
	var data := SimData.new()
	for raw: Variant in _records(root.path_join("economy/commodities.json"), "commodities"):
		var rec: Dictionary = schema.cast_record("Commodity", raw as Dictionary)
		if rec.is_empty():
			return null
		var commodity := Commodity.from_record(rec)
		data.commodities.append(commodity)
		data.commodity_by_id[commodity.id] = commodity
	for raw: Variant in _records(root.path_join("galaxy/systems.json"), "systems"):
		var rec: Dictionary = schema.cast_record("StarSystem", raw as Dictionary)
		if rec.is_empty():
			return null
		var system := StarSystem.from_record(rec)
		data.systems.append(system)
		data.system_by_id[system.id] = system
	return data


static func _records(path: String, key: String) -> Array:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		push_error("SimData: %s is not a JSON object" % path)
		return []
	return (parsed as Dictionary).get(key, []) as Array
```

- [ ] **Step 4: Run, format, gate, commit**

Run: `gdformat core test` then `python tools/gate.py`
Expected: every step PASS.

```bash
git add core/data core/galaxy core/economy/commodity.gd test/unit/schema_cast_test.gd test/unit/sim_data_test.gd
git commit -m "feat(sp2b): schema casts and typed commodities and systems

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: The simulation skeleton and the autoloads

**Files:**
- Create: `core/sim/kernel_system.gd`, `core/sim/sim_root.gd`, `core/save/save_document.gd`, `autoload/data_registry.gd`
- Modify: `autoload/game.gd`, `project.godot` (`[autoload]`), `tools/gate.py` (`HEARTBEATS`), `tools/tests/test_gate_smoke.py`
- Test: `test/unit/sim_root_test.gd`, `test/unit/save_document_test.gd`

**Interfaces:**
- Consumes: `SimData` (Task 6).
- Produces:
  - `KernelSystem`: `id: StringName`; `day_start(_sim: SimRoot, _day: int) -> void`, `save_state() -> Dictionary`, `load_state(_data: Dictionary) -> void`, `rederive(_sim: SimRoot) -> void`
  - `SimRoot`: `signal day_started(day: int)`; `data: SimData`, `day: int`; `static new_game(p_data: SimData) -> SimRoot`, `add_system(system: KernelSystem) -> void`, `systems() -> Array[KernelSystem]`, `advance_day() -> void`, `write_to(doc: SaveDocument) -> void`, `read_from(doc: SaveDocument) -> void`
  - `SaveDocument`: `SCHEMA_VERSION = 1`, `SECTIONS = ["sim", "systems"]`, `data: Dictionary`; `static new_game(now_unix: float) -> SaveDocument`, `static from_json(text: String) -> SaveDocument`, `to_json(saved_wall: float) -> String`, `schema_version() -> int`, `section(name: String) -> Dictionary`
  - `DataRegistryAutoload`: `data: SimData`, `is_loaded() -> bool`
  - `GameAutoload.sim: SimRoot`; the `[sim] ...` heartbeat

- [ ] **Step 1: Write the failing tests**

`test/unit/sim_root_test.gd`:

```gdscript
extends GdUnitTestSuite


class Recorder:
	extends KernelSystem

	var days: Array[int] = []
	var loaded: Dictionary = {}
	var rederived: int = 0

	func day_start(_sim: SimRoot, day: int) -> void:
		days.append(day)

	func save_state() -> Dictionary:
		return {"seen": days.size()}

	func load_state(data: Dictionary) -> void:
		loaded = data

	func rederive(_sim: SimRoot) -> void:
		rederived += 1


func _sim_with_recorder() -> Array:
	var sim := SimRoot.new_game(SimData.new())
	var recorder := Recorder.new()
	recorder.id = &"recorder"
	sim.add_system(recorder)
	return [sim, recorder]


func test_new_game_starts_on_day_one() -> void:
	assert_int(SimRoot.new_game(SimData.new()).day).is_equal(1)


func test_advance_day_ticks_every_system_and_signals() -> void:
	var pair: Array = _sim_with_recorder()
	var sim: SimRoot = pair[0]
	var recorder: Recorder = pair[1]
	var heard: Array[int] = []
	sim.day_started.connect(func(day: int) -> void: heard.append(day))
	sim.advance_day()
	sim.advance_day()
	assert_array(recorder.days).is_equal([2, 3])
	assert_array(heard).is_equal([2, 3])


func test_save_round_trip_restores_day_and_system_state() -> void:
	var pair: Array = _sim_with_recorder()
	var sim: SimRoot = pair[0]
	sim.advance_day()
	var doc := SaveDocument.new_game(0.0)
	sim.write_to(doc)
	var restored_doc := SaveDocument.from_json(doc.to_json(1.0))
	var fresh: Array = _sim_with_recorder()
	var sim2: SimRoot = fresh[0]
	var recorder2: Recorder = fresh[1]
	sim2.read_from(restored_doc)
	assert_int(sim2.day).is_equal(2)
	assert_int(int(recorder2.loaded["seen"])).is_equal(1)
	assert_int(recorder2.rederived).is_equal(1)
```

`test/unit/save_document_test.gd`:

```gdscript
extends GdUnitTestSuite


func test_new_game_has_version_and_sections() -> void:
	var doc := SaveDocument.new_game(100.0)
	assert_int(doc.schema_version()).is_equal(SaveDocument.SCHEMA_VERSION)
	for name: String in SaveDocument.SECTIONS:
		assert_bool(doc.data.has(name)).is_true()


func test_from_json_fills_defaults_and_keeps_unknown_keys() -> void:
	var doc := SaveDocument.from_json('{"future_key": 7}')
	assert_int(doc.schema_version()).is_equal(SaveDocument.SCHEMA_VERSION)
	assert_dict(doc.section("sim")).is_empty()
	assert_int(int(doc.data["future_key"])).is_equal(7)


func test_to_json_stamps_saved_wall() -> void:
	var doc := SaveDocument.new_game(1.0)
	var parsed: Dictionary = JSON.parse_string(doc.to_json(5.0)) as Dictionary
	assert_float(float(parsed["saved_wall"])).is_equal(5.0)
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`SimRoot`, `KernelSystem`, `SaveDocument` not declared).

- [ ] **Step 2: Implement the skeleton**

`core/sim/kernel_system.gd`:

```gdscript
class_name KernelSystem
extends RefCounted

## A day-ticked simulation system owned by SimRoot (markets, traffic, politics, news, and so on
## in later sub-projects). State methods are save_state/load_state so no subclass shadows
## Godot's global load().

var id: StringName = &""


func day_start(_sim: SimRoot, _day: int) -> void:
	pass


func save_state() -> Dictionary:
	return {}


func load_state(_data: Dictionary) -> void:
	pass


## Re-derive anything computed rather than saved, after a load.
func rederive(_sim: SimRoot) -> void:
	pass
```

`core/sim/sim_root.gd`:

```gdscript
class_name SimRoot
extends RefCounted

## The simulation root (SP2 skeleton): owns the content, the day clock, and the kernel systems.
## Holds no nodes; tests drive it directly.

signal day_started(day: int)

var data: SimData
var day: int = 1
var _systems: Array[KernelSystem] = []


static func new_game(p_data: SimData) -> SimRoot:
	var sim := SimRoot.new()
	sim.data = p_data
	return sim


func add_system(system: KernelSystem) -> void:
	_systems.append(system)


func systems() -> Array[KernelSystem]:
	return _systems.duplicate()


func advance_day() -> void:
	day += 1
	for system: KernelSystem in _systems:
		system.day_start(self, day)
	day_started.emit(day)


func write_to(doc: SaveDocument) -> void:
	doc.section("sim")["day"] = day
	var saved: Dictionary = doc.section("systems")
	for system: KernelSystem in _systems:
		saved[String(system.id)] = system.save_state()


func read_from(doc: SaveDocument) -> void:
	day = int(doc.section("sim").get("day", 1))
	var saved: Dictionary = doc.section("systems")
	for system: KernelSystem in _systems:
		system.load_state(saved.get(String(system.id), {}) as Dictionary)
		system.rederive(self)
```

`core/save/save_document.gd`:

```gdscript
class_name SaveDocument
extends RefCounted

## The versioned save document, v1 from day one (SP2 spec 8.6). Knows shape and defaults, not
## files: SaveIO arrives with the first sub-project that writes a save (ruling P1). Missing keys
## load as defaults; unknown keys are preserved.

const SCHEMA_VERSION: int = 1
const SECTIONS: Array[String] = ["sim", "systems"]

var data: Dictionary = {}


static func new_game(now_unix: float) -> SaveDocument:
	var doc := SaveDocument.new()
	doc.data = {
		"schema_version": SCHEMA_VERSION,
		"created_wall": now_unix,
		"saved_wall": now_unix,
	}
	doc._fill_defaults()
	return doc


static func from_json(text: String) -> SaveDocument:
	var parsed: Variant = JSON.parse_string(text)
	if not parsed is Dictionary:
		push_error("SaveDocument: expected a JSON object")
		return null
	var doc := SaveDocument.new()
	doc.data = parsed as Dictionary
	doc._fill_defaults()
	return doc


func to_json(saved_wall: float) -> String:
	data["saved_wall"] = saved_wall
	return JSON.stringify(data, "  ")


func schema_version() -> int:
	return int(data.get("schema_version", SCHEMA_VERSION))


func section(name: String) -> Dictionary:
	if not data.has(name) or not data[name] is Dictionary:
		data[name] = {}
	return data[name] as Dictionary


func _fill_defaults() -> void:
	if not data.has("schema_version"):
		data["schema_version"] = SCHEMA_VERSION
	for key: String in ["created_wall", "saved_wall"]:
		if not data.has(key):
			data[key] = 0.0
	for name: String in SECTIONS:
		section(name)
```

- [ ] **Step 3: Wire the autoloads**

`autoload/data_registry.gd`:

```gdscript
class_name DataRegistryAutoload
extends Node

## Autoload: loads the synced content once at startup.

var data: SimData


func _ready() -> void:
	data = SimData.load_from("res://data")
	if data == null:
		push_error("DataRegistry: data failed to load; see errors above")


func is_loaded() -> bool:
	return data != null
```

In `autoload/game.gd`, add after the class docstring (and update the docstring's second sentence to "Owns the SimRoot for a play session."):

```gdscript
var sim: SimRoot


func _ready() -> void:
	if is_test_run():
		return
	var registry := get_node("/root/DataRegistry") as DataRegistryAutoload
	if not registry.is_loaded():
		push_error("Game: data failed to load; simulation not started")
		return
	sim = SimRoot.new_game(registry.data)
	print(
		(
			"[sim] day %d: %d systems, %d commodities"
			% [sim.day, registry.data.systems.size(), registry.data.commodities.size()]
		)
	)
```

`project.godot` `[autoload]` becomes (DataRegistry first, so it is ready before Game):

```ini
[autoload]

DataRegistry="*res://autoload/data_registry.gd"
Game="*res://autoload/game.gd"
```

In `tools/gate.py`: `HEARTBEATS: tuple[str, ...] = ("[boot]", "[sim]")`. In `tools/tests/test_gate_smoke.py`, add:

```python
def test_heartbeats_include_the_simulation() -> None:
    assert "[sim]" in gate.HEARTBEATS
```

- [ ] **Step 4: Run, format, gate, commit**

Run: `gdformat core autoload test` then `python tools/gate.py`
Expected: every step PASS; both smoke boots print `[boot] ...` and `[sim] day 1: 12 systems, N commodities`.

```bash
git add core/sim core/save autoload project.godot tools/gate.py tools/tests/test_gate_smoke.py test/unit
git commit -m "feat(sp2b): SimRoot, KernelSystem, SaveDocument, and the autoloads

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Market pricing at parity

**Files:**
- Create: `core/economy/market.gd`, `core/economy/price_history.gd`, `test/parity/adapters/market_adapter.gd`, `test/parity/adapters/price_history_adapter.gd`
- Test: `test/parity/market_parity_test.gd`

**Interfaces:**
- Consumes: `SimRng.from_key` (Task 3), `SimData`, `Commodity`, `StarSystem` (Task 6), `ParityAdapter`, `ParityRunner` (Task 5); synced `market/` and `price_history/` goldens.
- Produces:
  - `Market`: `static create(p_system: StarSystem, all_commodities: Array[Commodity], day: int = 1) -> Market`; `system: StarSystem`, `game_day: int`, `commodities: Dictionary`; `get_price(cid: String) -> int`, `get_sell_price(cid: String) -> int`, `get_all_prices() -> Dictionary`, `record_buy(cid: String, quantity: int) -> void`, `record_sell(cid: String, quantity: int) -> void`, `initialize_stock(p_system: StarSystem) -> void`, `get_stock(cid: String) -> int`, `deplete_stock(cid: String, quantity: int) -> Array` (`[bool, String]`), `regenerate_stock() -> void`, `update_day(new_day: int) -> void`, `to_dict() -> Dictionary`
  - `PriceHistory`: `static create(p_max_days: int = 7) -> PriceHistory`; `record(system_id: String, cid: String, day: int, price: int) -> void`, `get_history(system_id: String, cid: String) -> Array`, `get_trend(system_id: String, cid: String) -> String`, `to_dict() -> Dictionary`

- [ ] **Step 1: Write the failing parity test**

`test/parity/market_parity_test.gd`:

```gdscript
extends GdUnitTestSuite

## 12 price tables (one per system) + 2 pressure + stock + off-market = 16 market cases.
const MARKET_CASES: int = 16
const PRICE_HISTORY_CASES: int = 3


func test_every_market_golden_replays_clean() -> void:
	assert_int(ParityRunner.case_names("market").size()).is_equal(MARKET_CASES)
	var failures: Array[String] = ParityRunner.replay_subsystem(
		"market", func() -> ParityAdapter: return MarketAdapter.new()
	)
	assert_str("\n".join(failures)).is_empty()


func test_every_price_history_golden_replays_clean() -> void:
	assert_int(ParityRunner.case_names("price_history").size()).is_equal(PRICE_HISTORY_CASES)
	var failures: Array[String] = ParityRunner.replay_subsystem(
		"price_history", func() -> ParityAdapter: return PriceHistoryAdapter.new()
	)
	assert_str("\n".join(failures)).is_empty()
```

Run: `python tools/gate.py --tests-only`
Expected: FAIL (`MarketAdapter` not declared).

- [ ] **Step 2: Port the market**

`core/economy/market.gd`:

```gdscript
class_name Market
extends RefCounted

## Commodity pricing for one star system; port of spacegame/models/market.py (SP2 scope: base
## pricing, supply and demand, SimRng variance, player pressure, stock). The event, politics, and
## galaxy-event price branches arrive in SP3 with their goldens (ruling P4). Float expressions
## keep Python's operand order.

const PLAYER_MODIFIER_PER_UNIT: float = 0.02
const PLAYER_MODIFIER_CAP: float = 0.30
const PLAYER_MODIFIER_DECAY: float = 0.70
const STOCK_PRODUCED: int = 100
const STOCK_CONSUMED: int = 30
const STOCK_NEUTRAL: int = 10
const STOCK_REGEN_RATE: float = 0.30
const SPECIALTY_EXPORT_MODIFIER: float = -0.15
const SPECIALTY_IMPORT_MODIFIER: float = 0.15
const OFF_MARKET_SELL_PENALTY: float = 0.50

var system: StarSystem
var game_day: int = 1
var commodities: Dictionary = {}
var _all_commodities: Dictionary = {}
var _price_cache: Dictionary = {}
var _player_supply_demand: Dictionary = {}
var _stock: Dictionary = {}
var _base_stock: Dictionary = {}


static func create(p_system: StarSystem, all_commodities: Array[Commodity], day: int = 1) -> Market:
	var market := Market.new()
	market.system = p_system
	for c: Commodity in all_commodities:
		market._all_commodities[c.id] = c
	var econ: Economy = p_system.economy
	for c: Commodity in all_commodities:
		if not econ.restricts_availability or econ.available_commodities.has(c.id):
			market.commodities[c.id] = c
	market.game_day = day
	market._generate_prices()
	return market


func get_price(cid: String) -> int:
	return int(_price_cache.get(cid, 0))


func get_sell_price(cid: String) -> int:
	var market_price: int = get_price(cid)
	if market_price > 0:
		return market_price
	var c: Commodity = _all_commodities.get(cid) as Commodity
	if c != null and c.base_price > 0:
		return maxi(1, int(c.base_price * OFF_MARKET_SELL_PENALTY))
	return 0


func get_all_prices() -> Dictionary:
	return _price_cache.duplicate()


func record_buy(cid: String, quantity: int) -> void:
	var current: float = float(_player_supply_demand.get(cid, 0.0))
	var new_mod: float = current + quantity * PLAYER_MODIFIER_PER_UNIT
	_player_supply_demand[cid] = minf(new_mod, PLAYER_MODIFIER_CAP)


func record_sell(cid: String, quantity: int) -> void:
	var current: float = float(_player_supply_demand.get(cid, 0.0))
	var new_mod: float = current - quantity * PLAYER_MODIFIER_PER_UNIT
	_player_supply_demand[cid] = maxf(new_mod, -PLAYER_MODIFIER_CAP)


func initialize_stock(p_system: StarSystem) -> void:
	_stock.clear()
	_base_stock.clear()
	for cid: String in commodities:
		var c: Commodity = commodities[cid] as Commodity
		if c.base_price <= 0:
			continue
		var base: int = STOCK_NEUTRAL
		if c.is_produced_by(p_system.economy.production_tags):
			base = STOCK_PRODUCED
		elif c.is_consumed_by(p_system.economy.consumption_tags):
			base = STOCK_CONSUMED
		_base_stock[cid] = base
		_stock[cid] = base


func get_stock(cid: String) -> int:
	return int(_stock.get(cid, 0))


func deplete_stock(cid: String, quantity: int) -> Array:
	var current: int = int(_stock.get(cid, 0))
	if quantity > current:
		return [false, "Only %d units in stock" % current]
	_stock[cid] = current - quantity
	return [true, "Stock depleted: %d remaining" % (current - quantity)]


func regenerate_stock() -> void:
	for cid: String in _base_stock:
		var base: int = int(_base_stock[cid])
		var regen: int = int(base * STOCK_REGEN_RATE)
		_stock[cid] = mini(base, int(_stock.get(cid, 0)) + regen)


func update_day(new_day: int) -> void:
	game_day = new_day
	var expired: Array[String] = []
	for cid: String in _player_supply_demand:
		_player_supply_demand[cid] = float(_player_supply_demand[cid]) * PLAYER_MODIFIER_DECAY
		if absf(float(_player_supply_demand[cid])) < 0.001:
			expired.append(cid)
	for cid: String in expired:
		_player_supply_demand.erase(cid)
	_generate_prices()


func to_dict() -> Dictionary:
	return {
		"player_supply_demand": _player_supply_demand.duplicate(),
		"stock": _stock.duplicate(),
		"base_stock": _base_stock.duplicate(),
		"politics_shifts": [],
	}


func _generate_prices() -> void:
	_price_cache.clear()
	for cid: String in commodities:
		_price_cache[cid] = _calculate_price(commodities[cid] as Commodity)


func _calculate_price(c: Commodity) -> int:
	var supply_demand_mod: float = _supply_demand_modifier(c)
	var random_mod: float = _random_variance(c)
	var player_mod: float = float(_player_supply_demand.get(c.id, 0.0))
	var total_modifier: float = 1.0 + supply_demand_mod + random_mod + player_mod
	var final_price: int = int(c.base_price * total_modifier)
	return maxi(1, final_price)


func _supply_demand_modifier(c: Commodity) -> float:
	var econ: Economy = system.economy
	var modifier: float = 0.0
	if c.is_produced_by(econ.production_tags):
		modifier -= 0.25
	if c.is_consumed_by(econ.consumption_tags):
		modifier += 0.25
	if econ.specialty_exports.has(c.id):
		modifier += SPECIALTY_EXPORT_MODIFIER
	if econ.specialty_imports.has(c.id):
		modifier += SPECIALTY_IMPORT_MODIFIER
	return modifier


func _random_variance(c: Commodity) -> float:
	var rng := SimRng.from_key(["market", game_day, c.id, system.id])
	var variance_range: float = absf(c.variance_max - c.variance_min)
	var max_random: float = minf(0.10, variance_range * 0.2)
	return rng.uniform(-max_random, max_random)
```

`initialize_stock`'s neutral default checks produced before consumed, exactly as Python's `if is_produced ... elif is_consumed ... else` does.

`core/economy/price_history.gd`:

```gdscript
class_name PriceHistory
extends RefCounted

## Per-system, per-commodity price history over recent days; port of PriceHistory in
## spacegame/models/market.py. get_trend uses true division (porting rule 1).

var max_days: int = 7
var _history: Dictionary = {}


static func create(p_max_days: int = 7) -> PriceHistory:
	var history := PriceHistory.new()
	history.max_days = p_max_days
	return history


func record(system_id: String, cid: String, day: int, price: int) -> void:
	if not _history.has(system_id):
		_history[system_id] = {}
	var per_system: Dictionary = _history[system_id] as Dictionary
	if not per_system.has(cid):
		per_system[cid] = []
	var entries: Array = per_system[cid] as Array
	entries.append([day, price])
	if entries.size() > max_days:
		per_system[cid] = entries.slice(entries.size() - max_days)


func get_history(system_id: String, cid: String) -> Array:
	var per_system: Dictionary = _history.get(system_id, {}) as Dictionary
	return (per_system.get(cid, []) as Array).duplicate(true)


func get_trend(system_id: String, cid: String) -> String:
	var entries: Array = get_history(system_id, cid)
	if entries.size() < 2:
		return "stable"
	var first_price: int = int((entries[0] as Array)[1])
	var last_price: int = int((entries[entries.size() - 1] as Array)[1])
	var diff_pct: float = float(last_price - first_price) / float(maxi(1, first_price))
	if diff_pct > 0.05:
		return "rising"
	if diff_pct < -0.05:
		return "falling"
	return "stable"


func to_dict() -> Dictionary:
	return {"max_days": max_days, "history": _history.duplicate(true)}
```

- [ ] **Step 3: Write the adapters**

`test/parity/adapters/market_adapter.gd`:

```gdscript
class_name MarketAdapter
extends ParityAdapter

## Replays market goldens (SP2 spec 7.4) against the Market port.

static var _data: SimData

var _market: Market
var _system: StarSystem


static func data() -> SimData:
	if _data == null:
		_data = SimData.load_from("res://data")
	return _data


func setup(setup_data: Dictionary) -> void:
	_system = MarketAdapter.data().system_by_id[str(setup_data["system_id"])] as StarSystem
	_market = Market.create(_system, MarketAdapter.data().commodities, int(setup_data["day"]))


func call_step(call_name: String, args: Array) -> Variant:
	var result: Variant = null
	match call_name:
		"snapshot":
			pass
		"update_day":
			_market.update_day(int(args[0]))
		"initialize_stock":
			_market.initialize_stock(_system)
		"record_buy":
			_market.record_buy(str(args[0]), int(args[1]))
		"record_sell":
			_market.record_sell(str(args[0]), int(args[1]))
		"deplete_stock":
			result = _market.deplete_stock(str(args[0]), int(args[1]))
		"regenerate_stock":
			_market.regenerate_stock()
		"get_price":
			result = _market.get_price(str(args[0]))
		"get_sell_price":
			result = _market.get_sell_price(str(args[0]))
		_:
			result = super.call_step(call_name, args)
	return result


func snapshot() -> Dictionary:
	var state: Dictionary = _market.to_dict()
	state["game_day"] = _market.game_day
	state["prices"] = _market.get_all_prices()
	return state
```

`test/parity/adapters/price_history_adapter.gd`:

```gdscript
class_name PriceHistoryAdapter
extends ParityAdapter

## Replays price_history goldens against the PriceHistory port.

var _history: PriceHistory


func setup(setup_data: Dictionary) -> void:
	_history = PriceHistory.create(int(setup_data["max_days"]))


func call_step(call_name: String, args: Array) -> Variant:
	var result: Variant = null
	match call_name:
		"record":
			_history.record(str(args[0]), str(args[1]), int(args[2]), int(args[3]))
		"get_history":
			result = _history.get_history(str(args[0]), str(args[1]))
		"get_trend":
			result = _history.get_trend(str(args[0]), str(args[1]))
		_:
			result = super.call_step(call_name, args)
	return result


func snapshot() -> Dictionary:
	return _history.to_dict()
```

- [ ] **Step 4: Run to green**

Run: `gdformat core test` then `python tools/gate.py --tests-only`
Expected: both parity tests PASS. If a case fails, the message names the case, the first divergent step, and the path (for example `market/player_pressure_nexus_prime: steps[4].state.prices.food: expected 41, got 40`). Compare that step against `spacegame/models/market.py` line by line (operand order, int truncation, insertion order), fix the port, and rerun. Never edit a golden; never add a tolerance without a ruling in `docs/parity/deviations.md`.

- [ ] **Step 5: Gate and commit**

Run: `python tools/gate.py`
Expected: every step PASS.

```bash
git add core/economy test/parity
git commit -m "feat(sp2b): market pricing and price history at parity with the Python reference

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Docs, the run queue, and the merge

**Files:**
- Create: `docs/roadmap.md`, `docs/autonomous_runs.md`, `docs/dev_setup.md`, `docs/parity/deviations.md`, `docs/findings_register.md`, `tools/goal_slices.json`

**Interfaces:**
- Produces: the run queue that `tools/goal_run.py` and later sub-projects read.

- [ ] **Step 1: Write the docs**

`docs/roadmap.md`:

```markdown
# Roadmap

The overhaul's sub-projects (master spec Section 10). Each runs: paired brainstorm, sub-spec,
plans, autonomous execution, paired playtest. Status values: todo, design, planned, running, done.

| Row | Sub-project | Status | Notes |
|---|---|---|---|
| SP1 | Art and sound direction | todo | Paired; opens with a model validation cycle |
| SP2 | Foundation | done | SP2-a in SpaceGame, SP2-b here; market pricing at parity |
| SP3 | Logic port | todo | Wave A: what the Nexus Prime slice needs |
| SP4 | The Ship | todo | |
| SP5 | Space | todo | |
| SP6 | Stations and UI | todo | |
| SP7 | Nexus Prime slice (M1) | todo | Paired playtest decides go or no-go |
| SP8 | Careers | todo | One sub-spec per career |
| SP9 | Breadth | todo | |
| SP10 | Act I (M2 demo, M3 complete) | todo | |
| SP11 | Act II (M4) | todo | |
```

`docs/parity/deviations.md`:

```markdown
# Parity deviations

Every intentional difference between a GDScript port and the Python reference (SP2 spec
Section 6). A deviation is backed by its own Godot test; a comparator tolerance is allowed only
by an entry here, cited by id in the adapter that applies it.

| Id | Subsystem | Python behavior | Godot behavior | Reason | Covering test |
|---|---|---|---|---|---|

None yet.
```

`docs/findings_register.md`:

```markdown
# Findings register

Bugs and gaps found in the Python reference's orchestration (`game.py`, the views). They are
design inputs for the sub-project that owns them, not parity deviations (SP2 spec Section 6).

| Id | Finding | Evidence | Owner | Status |
|---|---|---|---|---|
| F-1 | Dialogue flags are stored twice; a save can overwrite flags written directly to the player | `dialogue.py:333,337`, `game.py:5202` | SP6 | open |
| F-2 | Markets are never populated and market events, galaxy events, and politics shifts never reach trading prices | `game.py:352`, `Market.apply_event` has no callers | SP5 | open |
| F-3 | `TradeContractManager` is never built at runtime | survey 2026-09-26 | SP8 (Merchant) | open |
| F-4 | Act II v1 content can fire during Act I (the wealth capstone at 95 sales) | survey 2026-09-26 | SP2-a | closed: `ACT_TWO_V1_ENABLED` off |
| F-5 | The main loop consumes ESC before any view sees it | `game.py:6899` (read in code) | SP6 | open |
| F-6 | Refuel defaults to one unit | `trading_view.py:323,1262` (F-001 in SpaceGame) | SP6 | open |
| F-7 | About a dozen `Game` fields are never saved (news buffer, pending chain events, bounty immunity, and others) | survey 2026-09-26 | SP3 | open |
| F-8 | The ground map generator violates its own invariants (floor ratio, entrance-exit distance, chunk count) on about 58% of seeds, under either random generator | SP2-a Task 3 review survey (290 of 500 seeds) | SP8 (away team, planets) | open |
```

`docs/dev_setup.md`:

```markdown
# Development setup

## Tools
- Godot 4.7.2 standard build at `C:\Users\matth\Tools\Godot\`. Use the console exe for every
  headless run. Its path lives in `tools/config.local.json` (git-ignored):
  `{"godot": "C:/Users/matth/Tools/Godot/Godot_v4.7.2-stable_win64_console.exe"}`.
- gdtoolkit 4.5 (`gdformat`, `gdlint`) on PATH (installed as uv tools in `~/.local/bin`).
- uv with Python 3.13: run `uv sync` once per clone.
- gdUnit4 6.2.1 is vendored under `addons/gdUnit4/`.
- Godot MCP Pro: restore `addons/godot_mcp/` from `C:\Users\matth\Tools\godot-mcp-pro\addons\`;
  start Claude Code from this directory so `.mcp.json` loads.

## Once per clone
1. `uv sync`
2. `python tools/install_hooks.py`
3. `"<godot>" --headless --path . --import`
4. `python tools/gate.py`

## Syncing from the Python reference
Content and goldens are generated in `C:\Users\matth\PycharmProjects\SpaceGame`
(`python -m tools.parity.regen` there, reviewed and committed), then
`uv run python tools/sync_data.py --from ../SpaceGame` here. Never edit `data/` or
`test/parity/golden/` in this repo.
```

`docs/autonomous_runs.md`: copy `$E/docs/autonomous_runs.md` and edit it for Aurelia:
- Title paragraph: "How Aurelia runs a plan without the author in every turn. Policy from the master spec, Section 11. The queue lives in `docs/roadmap.md`."
- Replace the image-hold bullet under "What stays paired" with: "Art spend above the cap SP1 records, and any major image generation pass (new asset class, a batch above a handful of images) until SP1's validation cycle names the winning model."
- In the execute-row template, replace "Keep typed GDScript, core/ RefCounted-only, files under about 300 lines, TDD, no em-dashes in prose, and the banned-name list." with "Keep typed GDScript, core/ RefCounted-only, files under about 300 lines, TDD, parity first, the porting rules in CLAUDE.md, no em-dashes in prose, and the banned-name list."
- Replace the "The 1A instance" example with the SP2-b instance rendered by `python tools/goal_run.py --print SP2-b`.
- Replace slice ids in the command examples (`1A`, `1B-plan 1B`) with `SP2-b` and `SP3-plan SP3`.

`tools/goal_slices.json`:

```json
{
  "SP2-b": {
    "kind": "execute",
    "plan": "docs/plans/2026-09-26-sp2b-godot-scaffold.md",
    "branch": "sp2b-scaffold",
    "turns": 80
  }
}
```

Run: `python tools/goal_run.py --print SP2-b`
Expected: prints the `/goal` condition naming this plan and branch.

- [ ] **Step 2: Scan prose, gate, commit**

Run: `python -c "import pathlib,sys; hits=[str(p) for p in [*pathlib.Path('docs').rglob('*.md'), pathlib.Path('CLAUDE.md')] if '\u2014' in p.read_text(encoding='utf-8')]; print(hits or 'no em-dashes'); sys.exit(1 if hits else 0)"`
Expected: `no em-dashes` (the copied specs were written without them).
Run: `python tools/gate.py`
Expected: every step PASS.

```bash
git add docs tools/goal_slices.json
git commit -m "docs(sp2b): roadmap, runbook, setup, deviations, findings register

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Merge**

```bash
git switch main
git merge --no-ff sp2b-scaffold -m "Merge branch 'sp2b-scaffold': Godot scaffold with market pricing at parity

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
python tools/gate.py
git branch -d sp2b-scaffold
```

Expected: the gate passes on `main`. No remote exists; do not add one.
