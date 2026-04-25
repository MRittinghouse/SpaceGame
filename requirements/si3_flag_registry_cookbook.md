# SI-3 Flag Registry Cookbook

Recipe for moving a cluster of `dialogue_flags` strings into
`spacegame/constants/flags.py`. One page, scannable. Every Stream 3
migration follows this. Commit messages reference this doc by filename.

Companion to `requirements/si2_dataclass_migration_cookbook.md`. Same
shape, different bug class.

## Why migrate

`Player.dialogue_flags` is a `dict[str, bool]` that crosses every
module boundary in the game — missions write, dialogue reads, news
ticker reads, journal entries write, encounters read, save system
serializes. A typo on either side fails silently.

The SI origin bugs were exactly this class of failure (shop wrote
`tutorial_bought_part_X`, builder read `tutorial_bought_X`). The
registry pattern made that drift impossible. Stream 3 expands the
defense to the next ~50 highest-risk flags.

## When to register (scope boundary)

**Register:** flags that cross module boundaries. The producer file
and at least one consumer file are different. Drift between them is a
silent bug waiting.

**Don't register:** flags with single-file producer + consumer (e.g.,
`builder_*` flags consumed only by `ship_builder_view`, `seen_tip_*`
flags consumed only by view tests). The registry adds overhead and
catches no bug class for these — they're really just module-private
state that happens to live on `dialogue_flags` for save/load
convenience.

**Rule of thumb:** if a `git grep` for the flag string finds
references in 2+ source files (excluding tests), migrate. Otherwise
skip.

## Helper conventions

Two shapes. Pick the one that matches the flag.

**1. Parameterized helper** — when the flag varies by an ID
(mission, NPC, encounter, etc.).

```python
def mission_completed(mission_id: str) -> str:
    """Flag set when a mission completes. Read by campaign/dialogue gates."""
    return f"mission_completed_{mission_id}"
```

Plus the inverse extractor when any consumer iterates
`dialogue_flags` looking for matches:

```python
def extract_completed_mission_id(flag_name: str) -> Optional[str]:
    """Inverse of mission_completed — extracts mission_id from a flag, or None."""
    prefix = "mission_completed_"
    if flag_name.startswith(prefix):
        return flag_name[len(prefix):]
    return None
```

Use a private module-level constant for the prefix (`_MISSION_COMPLETED_PREFIX = "mission_completed_"`)
so the setter and extractor reference the same string. See
`tutorial_bought_part` / `extract_tutorial_bought_part_id` for the
working template.

**2. Module constant** — when the flag is a singleton (one specific
story beat, one NPC introduction).

```python
MET_TORRES: str = "met_torres"
```

SCREAMING_SNAKE_CASE per Python convention. Use the value directly:
`player.dialogue_flags[flags.MET_TORRES] = True`.

## Naming rules

When a cluster has inconsistent prefixes in the wild
(`*_complete` vs `*_done` vs `*_completed`), **pick one canonical
form** and migrate both producer and consumer to it during the
migration. This often fixes a real drift bug as a side-effect — flag
the discovery in the commit message.

Canonical forms:
- Completion: `<thing>_completed_<id>` (past tense, parameterized)
- Met someone: `met_<npc_id>` (singleton)
- Talked to: `talked_to_<npc_id>` (singleton)
- Encounter seen: `encounter_seen_<encounter_id>` (parameterized)
- Reveal/discovery: `<system>_revealed_<id>` (parameterized)

## Recipe

1. **Audit the cluster.** Grep every read and write across `spacegame/`
   AND `data/` (JSON content references flags too in `requires_flags`,
   `set_flag`, `unlock_condition`, etc.). Note any inconsistent
   prefixes — they get unified during migration.

2. **Add the helper(s).** New section in `spacegame/constants/flags.py`
   under a `# --- <Cluster Name> ---` header. Include a docstring on
   each helper that names producer + consumer modules so future
   readers don't have to guess.

3. **Migrate producers.** Every `dialogue_flags["..."] = True` for the
   cluster becomes `dialogue_flags[helper(...)] = True`. Same for
   `dialogue_flags[constant_name] = True`.

4. **Migrate consumers.** Every `dialogue_flags.get("...")` becomes
   `dialogue_flags.get(helper(...))`. For iteration consumers
   (`for flag in dialogue_flags: if flag.startswith("...")`), use the
   `extract_*` helper.

5. **Migrate JSON content.** `data/missions/*.json`, `data/dialogues/*.json`,
   etc. reference flag strings. The data loader path needs to use the
   helper too. Often this means: keep the JSON string as-is, but add
   a runtime assertion in the data loader that the loaded string
   equals `helper(id)` for the corresponding ID. (Defer the actual
   JSON-side migration unless drift is happening — JSON-as-content is
   the schema's source of truth.)

6. **Update tests.** Test fixtures with raw flag strings get the
   helper too. Leaving raw strings in tests defeats the scanner.

7. **Drop the allowlist entry.** Scanner A's `KNOWN_ORPHANS` (in
   `tests/test_compliance/test_flag_string_discipline.py` once
   broadened in Pass 3.4) — remove the cluster's prefix entry.

8. **Verify.** `pytest tests/test_compliance/`, full suite, ruff.

9. **Commit.** Message:
   `SI-3: register <cluster> flag cluster (cookbook: requirements/si3_flag_registry_cookbook.md)`.

## Call the helper at the access site

**Inline the helper call at the `dialogue_flags` access, don't assign to a
local first.** Both of these do the same thing at runtime, but the first
is what the static-analysis scanners expect:

```python
# ✅ Preferred: helper call is right at the dialogue_flags boundary.
already_met = player.dialogue_flags.get(met_npc("arna"), False)
player.dialogue_flags[met_npc("arna")] = True

# ❌ Avoid: a local variable hides the helper from tracing.
arna_flag = met_npc("arna")
already_met = player.dialogue_flags.get(arna_flag, False)
player.dialogue_flags[arna_flag] = True
```

The integrity scanner (`tests/test_data/test_dialogue_integrity.py`)
regex-traces helper calls that appear directly inside `dialogue_flags[...]`
or `dialogue_flags.get(...)`. Assigning the result to a local variable
first breaks the trace and reports the flag as an orphan.

## What NOT to do

- Don't register single-file flags. Registry is for cross-module
  contracts; module-internal state stays put.
- Don't add validation logic (a `__post_init__`-style "is this a
  known mission_id?" check). The registry exists to prevent string
  drift, not to validate IDs at runtime.
- Don't split `flags.py` until it crosses ~300 lines. When that
  happens, split by domain (one module per cluster: `flags/mission.py`,
  `flags/npc.py`, etc.) — but not before.
- Don't migrate JSON content strings unless drift is actually
  happening. JSON is content-data; the canonical strings live there
  by design.
- Don't introduce a new flag without using the helper from day one.
  SI-3 enforces this via Scanner A.

## Verification checklist

Before marking a cluster migration done:

- [ ] `pytest tests/test_compliance/` — Scanner A passes, allowlist not stale
- [ ] `git grep "<prefix>" spacegame/` — every match is via the helper
- [ ] `git grep "<prefix>" tests/` — fixtures use the helper
- [ ] `pytest -q` — full suite green
- [ ] `ruff check spacegame/ tests/` — clean on touched files
- [ ] Commit message cites this cookbook by path
