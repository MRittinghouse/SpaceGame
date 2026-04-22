# UI Review Sprint 5 — Writing Bible Compliance

Generated 2026-04-22. Generalizes the existing narrative-voice tests (tutorials, cockpit HUD) to every UI-surface text source in the game.

**Bottom line:** 13 new tests scan **thousands of UI strings** across view source, mission content, journal entries, dialogue nodes, NPC ambient lines, and station chatter. **Five real Writing Bible violations found and fixed** (1 view-source em-dash, 4 ambient `--` double-hyphens, 4 journal `--` double-hyphens, 1 dialogue em-dash). After cleanup, every UI text surface is Writing Bible strict — zero xfails, zero catalogued exceptions.

Test count: **7,288 → 7,301 (+13).** Full suite green on first run, lint clean.

---

## What the scanner covers

The new `tests/test_writing_bible_compliance.py` walks six text surfaces and validates each against the Writing Bible ban list. All tests assert hard — no xfail tolerance. Any new em-dash, banned phrase, or parallel-negation rhetoric introduced later will fail the suite.

| Surface | Extraction method | Volume scanned |
|---|---|---|
| View source literals | Regex scan of `.render()`, `.set_text()`, `text=` calls in `spacegame/views/*.py` | 70+ strings |
| Mission content | `DataLoader.missions` iteration (name, description, objectives) | 55 missions |
| Journal entries | `DataLoader.journal_entries` iteration | 20 entries |
| Dialogue nodes | `DataLoader.dialogue_trees` walk (node text + all response text) | 1,085 nodes |
| NPC ambient lines | `DataLoader.ambient_lines` | 224 lines |
| Station chatter | `DataLoader.station_chatter_lines` | 201 lines |

### Rules enforced (per `requirements/dialogue_writing_guide.md`)

- **No em-dashes** (`—`, `–`, or double-hyphen `--`)
- **No "couldn't help but"**
- **No "a testament to"**
- **No parallel-negation rhetoric** (`no X, no Y`)

Future Writing Bible additions slot into the scanner trivially — add an entry to `_BANNED_PHRASES` or `_EM_DASHES` and the existing test machinery picks them up across every surface.

---

## What was found and fixed

### View source (1 finding)

- `spacegame/views/ship_builder_view.py:3638` — `"Ship Builder — Controls"` header used an em-dash. Fixed to `"Ship Builder Controls"`.

### Dialogue (1 finding)

- `dialogue:cassiel_maren_forgery:in_progress:response_0` — `"[Leave — complete the appraisal off-screen]"`. Fixed to `"[Leave and complete the appraisal off-screen]"`.

### Journal (4 findings — all `  -- ` double-hyphen)

- `auto_m06_priya` — `"clinical and precise -- nothing like Breakstone"` → `"clinical and precise. Nothing like Breakstone"`
- `auto_m07_tomas_accepted` — `"gray-market trade -- rerouting supplies"` → `"gray-market trade. Rerouting supplies"`
- `auto_m10_crimson` — `"serious resources -- real money, real ships"` → `"serious resources. Real money, real ships"`
- `auto_m12_attack` — `"well-equipped -- better than any frontier raiders"` → `"well-equipped. Better than any frontier raiders"`

### NPC ambient (4 findings — all `-- ` double-hyphen)

- `"bureaucracy -- their docking procedures are impeccable"` → sentence break
- `"welds -- clean, even, no shortcuts"` → sentence break
- `"calculations you sent -- good work"` → sentence break
- `"exceptional -- if they'd only share"` → sentence break

All ten findings converted the dash construction into sentence breaks. The repaired prose reads equivalently in voice and keeps the Writing Bible rule simple.

### Everything else passed strictly

- **Mission content** — 55 missions, 188 strings scanned. Zero violations.
- **Station chatter** — 201 lines. Zero violations.
- **Dialogue node bodies** (excluding the one fixed response) — 1,084 nodes. Zero violations.
- **No "couldn't help but" or "a testament to"** anywhere in the scanned corpus.
- **No parallel-negation rhetoric** anywhere.

This is a strong signal: the writing team's voice discipline held up well. The ten offenders were genuinely isolated, not systemic.

---

## Scanner design decisions

### View-source regex heuristics

The regex captures string arguments to `font.render()`, `.set_text()`, and `text=` keyword arguments. It skips:

- Format-string templates (anything with `{` placeholder)
- Strings under 3 characters
- Path-like strings (`/` or `\` in them)
- snake_case identifiers (underscore-heavy, no spaces)
- pygame_gui object-ID strings (`#_` or `$` prefix)

This prevents false positives on code rather than trying to identify "UI copy" semantically. The scanner produces ~70 likely-user-facing strings per view layer.

### JSON content via DataLoader

Rather than parsing JSON directly, the scanner uses `DataLoader` and iterates parsed model objects. Benefits:

- Matches what the game actually exposes
- Handles schema variations (journal entries, dialogue trees, ambient lines have different shapes)
- Free with the existing loading infrastructure

Downside: if new content types are added, the scanner needs a new extraction function. Acceptable cost.

### No more xfails

The initial scanner caught 10 offenders and used `xfail` to let the suite pass while cataloguing. After fixing all ten, the tests now assert strictly. Any future content that introduces a violation fails the build with a precise per-offender report.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,301 passed, 98 skipped, 1 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| New writing-bible tests | 13 (all strict, zero tolerance) |
| Writing Bible violations in any UI-surface text | **0** |
| Text surfaces with strict compliance coverage | 6 (views, missions, journal, dialogue, ambient, chatter) |

---

## What's explicitly not covered

Sprint 5 scope was "extend voice tests to every UI string." What that did NOT include:

- **Button action-name clarity** (per the standards doc: "Buttons name the action, not the abstraction"). Hard to test automatically. A human-review pass could audit button labels for "Confirm", "Apply", "OK" patterns that are vaguer than action verbs. Candidate for Sprint 5b.
- **Error messages and empty states** — voice and actionability. "Not enough credits. Ledger's short." vs "Insufficient funds." Subjective; needs human judgment.
- **Per-faction voice consistency** against `character_voices.md`. The faction voice sheets exist but weren't comparison-scanned against actual dialogue.
- **Tone drift by region** (a Consortium station should sound clinical; a Reach encounter should sound menacing). Structural but hard to test without classifier models.

These are all follow-up candidates for content-focused review sessions rather than automated testing.

---

## What's next

**Sprint 5b** (natural continuation): button action-name clarity audit + error/empty-state voice audit. Human-review pass with catalog of findings. A few hours of manual review, not code work.

**Sprint 6** — state and motion polish. Five-state interactive coverage, four-state content-panel coverage, motion discipline.

**Trading legality badge refactor** (Sprint 3c xfail follow-up) — the last remaining Sprint 3 xfail. Remove the `" RESTRICTED"` / `" ILLEGAL"` text suffix, replace with a badge component.

**Controller support conversation** — still flagged for a dedicated session.

**Colorblind calibration content pass** — with the Sprint 4/4b infrastructure live, find colorblind playtesters and refine the remap tables empirically.

Recommending **Sprint 6** next for process continuity, or **trading legality refactor** to clear the last xfail cleanly. Both are well-scoped. The content-focused items (5b, colorblind calibration) don't require code work and could be queued whenever human review cycles are available.
