# CB Crew Banter — Scope Contract

**Status**: locked (CB-1 output)
**Authors**: CB-1 implement phase
**Date**: 2026-04-29
**Consumed by**: CB-2 (implementation), SA-X6 (anchor-specific content), SA-X6 planner (touch-zone reconciliation)

---

## 1. Current Coverage

**Source file**: `data/crew/ambient_dialogue.json`
**Top-level key**: `ambient_lines`
**Total entries**: 249 lines across 24 distinct `crew_id`s and 5 context types.

### Context distribution

| Context | Count | Description |
|---|---|---|
| idle | 93 | General ambient, no trigger condition |
| player_action | 60 | Reaction to a specific player action |
| inter_crew | 52 | Single speaker, requires a specific crewmate aboard |
| home_system | 24 | Speaker arrives in their home/origin system |
| faction_territory | 20 | Speaker arrives in their faction's territory |

### Primary crew lines

| crew_id | Lines |
|---|---|
| marcus_jin | 36 |
| elena_reeves | 32 |
| dr_priya_osei | 30 |
| tomas_drifter | 29 |
| **Total primary** | **127** |

### Secondary specialists

20 additional `crew_id`s with 5-9 lines each (122 lines total).
Examples: `kai_torren` (9), `bram_okeke` (9), `sgt_harkov` (8), `zero` (8), `cpl_ines_rask` (8), and 15 others.

### Engine: AmbientDialogueManager

**File**: `spacegame/models/ambient_dialogue.py`
**Class**: `AmbientDialogueManager`

Key methods:
- `get_line(context, crew_id, ...)` — returns one matching line, marks it shown
- `get_random_idle(recruited_ids, loyalty_map)` — picks from any recruited crew member
- `get_player_action_line(action_type, ...)` — picks a reaction to a player action

**Cooldown mechanism**: `_shown: set[int]` of indices. Shown lines are never re-fired in the same session. This is index-based, not time-based. No days-since-last-fire tracking.

**Save state**: `to_dict()` / `load_state()` serialize and restore the `_shown` set via `"shown_indices"`.

Integration points in `spacegame/engine/game.py`:
- Manager constructed at lines 405-407 (init) and 618-621 (post-load)
- Warp/arrival triggers at lines 1167-1191 (home_system, faction_territory)
- Player-action triggers at lines 4129-4138
- Idle counter at lines 5406-5413
- Save binding at line 4685; load restore at lines 4871-4872

Note: `data/crew/banter.json` does not exist. All existing crew banter lives in `ambient_dialogue.json` and is managed by `AmbientDialogueManager`. The Phase 5 design doc's references to `banter.json` describe a not-yet-created file; this contract uses `ambient_dialogue.json` as the authoritative home.

---

## 2. Gap Analysis

Phase 5 trigger types from `requirements/living_universe_arc.md` lines 831-840 mapped against existing coverage:

| Trigger type | Coverage | Justification |
|---|---|---|
| `idle` | **Covered** | 93 idle lines, random selection from any recruited crew |
| `destination` | **Partial** | `home_system` (24) + `faction_territory` (20) cover origin systems and faction zones. Missing: per-destination weighting, non-home-system destinations, anchor-arrival variants |
| `crew_pair` | **Partial** | `inter_crew` (52) covers single-speaker lines that require a crewmate. Missing: multi-speaker exchange format (speakers/lines alternation per Phase 5 design) |
| `flag` | **Missing** | No `required_flags` or `excluded_flags` fields on `AmbientLine`. No flag-conditional selection exists. |
| `combat_after` | **Missing** | `player_action` has `combat_victory` (7) and `combat_retreat` (6) sub-types, but these fire immediately on the action. No time-delayed "recency" trigger (combat in last N game days). |
| `rival_seen` | **Missing** | No rival/RC system integration. `AmbientLine` has no `rival_id` field. This requires RC infrastructure CB-2 will not own. |

---

## 3. Architecture Decision

**Decision: Option A — extend `AmbientDialogueManager`.**

Rationale:
- Zero save-migration cost. Existing `_shown` set is additive.
- Preserves all 249 voice-checked lines. No format change for existing entries.
- Existing manager already serializes state and integrates at warp/idle/player_action. New context types are additive.
- Scanner integration is already live (`test_writing_bible_compliance.py` reads `dl.ambient_lines` via `_extract_ambient_strings()`).

**Concrete extensions for CB-2:**

`AmbientLine` gains two optional fields (backward-compatible, default `[]`):
- `required_flags: list[str]` — all named flags must be set in `player.dialogue_flags`
- `excluded_flags: list[str]` — any named flag being set disqualifies the line

New `context` values added to the existing string enum:
- `combat_after` — fires after a combat event within a configurable recency window (default 3 game days). `AmbientDialogueManager` needs a `mark_combat(game_day: int)` method and a `get_combat_after_line(recruited_ids, loyalty_map, current_day)` method. State (`last_combat_day: Optional[int]`) serializes via `to_dict()` / `load_state()`.
- `flag_triggered` — fires when the manager's `check_flag_lines(player_flags, recruited_ids, loyalty_map)` is called. Lines matching context `flag_triggered` whose `required_flags` are all set (and no `excluded_flags` set) are eligible.

`get_all_matching()` gains a `player_flags: Optional[dict[str, bool]]` parameter for flag evaluation. Default `None` preserves backward compatibility.

**Option A constraint on crew_pair:** The existing single-speaker model means "crew pair" banter is one speaker addressing another (with `required_crew` constraint). There are no alternating multi-line exchanges. CB-2's crew_pair quota is filled by single-speaker lines that reference or address the required crewmate directly — the "conversation feel" lives in the text, not the structure.

**If this constraint is unacceptable:** Option C (sister-system, shared data file) introduces a `BanterEntry` model (`id`, `speakers: list[str]`, `lines: list[str]`, `trigger_conditions: BanterTrigger`) alongside `AmbientDialogueManager`. It supports multi-speaker exchanges but requires a new model, new engine methods, and a new display layer that can render alternating lines. This adds ~2 days to CB-2 and introduces a parallel data schema. The trip wire: if CB-2's author writes crew_pair samples that feel broken as single-speaker lines, escalate to Option C.

**`rival_seen` is deferred to SA-X6.** It requires RC infrastructure that CB-2 does not own. SA-X6 should include a `rival_seen` context wire-up once the RC system is complete.

---

## 4. SA-X6 Boundary

**Decision: SA-X6 is a sibling sprint.** CB-2 ships engine infrastructure and ~60 general banter lines. SA-X6 then authors 25-40 anchor-specific lines using CB-2's extended infrastructure.

Specifically:
- CB-2 delivers: the `flag_triggered` and `combat_after` context extensions, the `required_flags` / `excluded_flags` fields, and banter covering general travel triggers (destination, idle, combat_after, flag, crew_pair where the flag context is general story events).
- SA-X6 delivers: anchor-specific banter entries (lines triggered by anchor-outcome flags like `desta_corridor_pre_session_seen`, `cass_mediation_in_progress_seen`, `tomas_alliance_congress_attended_seen` already wired by SA-P3/P4) plus the `rival_seen` context type wire-up.

**Touch-zone reconciliation for SA-X6's planner:** SA-X6's declared touch zone lists `data/crew/banter.json`. That file does not exist and will not be created by CB-2 (Option A keeps all content in `ambient_dialogue.json`). SA-X6's planner must update its touch zone to `data/crew/ambient_dialogue.json` before implementation begins. CB-1 does NOT modify SA-X6's section; this note is for SA-X6's planner.

---

## 5. CB-2 Authoring Quota

Minimum entry counts per trigger type. These are the acceptance floor; CB-2 cannot ship a content drop that concentrates all entries in one type.

| Trigger type | Minimum entries | Notes |
|---|---|---|
| destination | >= 20 | Expand home_system + faction_territory with new destinations (anchor systems); add required_flags variants |
| crew_pair | >= 15 | Single-speaker lines referencing/addressing a required crewmate; min 2 per primary-crew pair (6 pairs) |
| flag_triggered | >= 10 | Flag-gated lines; at least 5 distinct flags from story progression |
| combat_after | >= 5 | New context type; at least one per primary crew member |
| idle | >= 10 | New general-purpose idle lines to supplement the existing 93 |
| **Total** | **>= 60** | Matches Phase 5's "40-60 entries at launch" target |

Secondary crew (non-primary specialists) are exempt from the per-type floor but should receive at least 10 new lines total distributed across types.

---

## 6. Sample Entries

Five entries demonstrating the locked schema. Each is voice-checked against `requirements/character_voices.md` and the Writing Bible (no em-dashes, no banned phrases, no parallel-negation). Flag names in these samples are **illustrative** — CB-2 must use actual production flag values registered in `spacegame/constants/flags.py`.

**Entry 1 — Elena Reeves, flag_triggered**
```json
{
  "crew_id": "elena_reeves",
  "context": "flag_triggered",
  "required_flags": ["guild_removed_equipment"],
  "excluded_flags": [],
  "text": "Stellaris confiscated my navigation certifications when I left. Technically I have three months to appeal. Technically."
}
```
Voice check: Precise timeframe ("three months"). "Technically" repeated is her overcorrection tell — formal word used twice to signal she knows it's hollow. No em-dashes. ✓

**Entry 2 — Marcus Jin, combat_after**
```json
{
  "crew_id": "marcus_jin",
  "context": "combat_after",
  "text": "Drive seals took a hit. Six hours, minimum. Combat isn't free."
}
```
Voice check: Short declarative sentences. Equipment focus. "Combat isn't free" is Marcus's dark-practical register, not dramatic. No em-dashes. ✓

**Entry 3 — Dr. Priya Osei, home_system with required_flags**
```json
{
  "crew_id": "dr_priya_osei",
  "context": "home_system",
  "system_id": "axiom_labs",
  "required_flags": ["sa_r1_research_patron_completed"],
  "excluded_flags": [],
  "text": "The Institute has been recategorized as an active research partner. The Collective will notice. I want to be on record as not caring."
}
```
Voice check: Precision ("recategorized"), institutional framing ("on record"), dry implication of political awareness. Does not declare emotion directly. ✓

**Entry 4 — Tomas Drifter, inter_crew (crew_pair to Elena)**
```json
{
  "crew_id": "tomas_drifter",
  "context": "inter_crew",
  "required_crew": "elena_reeves",
  "text": "Elena, that routing you ran saved us three hundred in fuel. You didn't mention it. Way I see it, unmentioned savings are still savings."
}
```
Voice check: First-name address. "Way I see it" opener. Trade metric framing (savings in credits). Oblique compliment — he won't just say "good job." ✓

**Entry 5 — Marcus Jin, idle**
```json
{
  "crew_id": "marcus_jin",
  "context": "idle",
  "text": "Read the maintenance contract. Section four, paragraph nine: preventative care. Nobody reads it. Then they're surprised when things break."
}
```
Voice check: Documentation reference. Short sentences. "Nobody reads it" is Union-cynicism, the category Marcus lives in. ✓

---

## 7. Test Surface

CB-2 adds or extends these test files. No new test file is needed if Option A locks (all extensions go in existing files).

**`tests/test_models/test_ambient_dialogue.py`** — extend with:
- `test_combat_after_context_eligibility` — `combat_after` lines returned only when `current_day - last_combat_day <= threshold`
- `test_flag_triggered_requires_all_flags` — line with two `required_flags` not returned unless both are set
- `test_flag_triggered_excluded_flag_blocks` — line with `excluded_flags` not returned when any excluded flag is set
- `test_required_flags_backward_compat` — existing lines (no `required_flags`) still returned when `player_flags=None`
- `test_combat_after_save_round_trip` — `last_combat_day` survives `to_dict()` / `load_state()`

**`tests/test_writing_bible_compliance.py`** — no new test class needed. `_extract_ambient_strings()` already reads `dl.ambient_lines`, which includes new entries added to `ambient_dialogue.json`. CB-2 should confirm the file is still scanned after adding entries (it will be, as long as entries load into `dl.ambient_lines`).

**`tests/test_data/test_dialogue_integrity.py`** — extend with:
- New entries' `crew_id` values resolve to known crew member IDs (existing speaker_id integrity check pattern)
- `required_flags` and `excluded_flags` values, if any reference cross-module flags, must exist in `spacegame/constants/flags.py` (extend the flag producer/consumer scan to cover `ambient_dialogue.json`'s new fields)

**`tests/test_models/test_player.py`** — save round-trip: if `Player` gains no new fields (Option A does not require Player changes beyond what's already in `AmbientDialogueManager`), no new player-level test is needed. `AmbientDialogueManager.to_dict()` / `load_state()` already covers the shown-index state; `last_combat_day` is added to that dict.

---

## 8. Recommendation

**Run parallel with SA-X6.**

CB-2 ships the engine extensions (Option A: `combat_after` context, `flag_triggered` context, `required_flags` / `excluded_flags` fields, `mark_combat()` method) and ~60 lines of general banter covering all non-anchor trigger types. SA-X6 then runs as a sibling sprint, authoring 25-40 anchor-specific lines using CB-2's infrastructure.

This boundary is correct because:
- The trigger flags SA-P3/P4 set (`desta_corridor_pre_session_seen`, `cass_mediation_in_progress_seen`, `tomas_alliance_congress_attended_seen`) are already in the codebase. SA-X6 only needs to author the lines and point them at these flags via `flag_triggered` context. It can do that as soon as CB-2 ships.
- SA-X6 also handles `rival_seen`, which requires RC infrastructure outside CB-2's scope. Running SA-X6 after CB-2 gives RC time to mature.
- Folding SA-X6 into CB-2 would make CB-2 an XL sprint blocked on all of SA-A2, SA-1, SA-2, SA-P6, SA-B6, SA-R3, and SA-F3 — SA-X6's full dependency chain. CB-2's general banter has no such dependencies.
- Deferring indefinitely leaves the Phase 5 crew-voice vision unimplemented and the trigger flags already wired by SA-P3/P4 permanently orphaned.

SA-X6's planner must reconcile the `data/crew/banter.json` touch zone (see section 4) before SA-X6 implementation begins.
