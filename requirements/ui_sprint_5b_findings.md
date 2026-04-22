# UI Review Sprint 5b — Button Clarity + Voice Audit

Generated 2026-04-22. Follow-up to Sprint 5. Button label action-clarity and error/empty-state voice audit across every view.

**Bottom line:** 9 concrete voice fixes across 3 view files. Sprint 5's writing bible scanner widened to catch `_show_message()` calls and multi-line `.render()` arguments — surfaced one additional em-dash Sprint 5 had missed. After cleanup, every UI surface remains Writing Bible strict with broader scanner coverage.

Test count: **7,301** (unchanged — this sprint fixed content, did not add tests). Full suite green, lint clean.

---

## Scanner infrastructure improvement

Sprint 5's `_RENDER_STRING` regex in `tests/test_writing_bible_compliance.py` only matched single-line `.render()`, `.set_text()`, and `text=` calls. It missed:

- Multi-line calls where the string literal sits on a new line after the opening paren
- View-internal message display via `_show_message(...)`
- View-internal feedback via `_show_feedback(...)`

Widened regex:

```python
_RENDER_STRING = re.compile(
    r"""(?:
        \.render\(
        | \.set_text\(
        | \btext\s*=\s*
        | _show_message\(
        | _show_feedback\(
    )
    \s*
    ["']([^"'\n]+)["']""",
    re.VERBOSE,
)
```

The `\s*` between the call and the quoted string allows whitespace (including newlines) so multi-line literals are caught. This fix surfaced one em-dash Sprint 5 had missed (`trading_view.py:791`), confirming the scanner was under-covering.

---

## Fixes applied

### `spacegame/views/trading_view.py` — 4 fixes

Two `_show_message()` calls used em-dashes; two used generic "insufficient" language.

**Line 791** (stock unavailable):
- Before: `"Out of stock — check back tomorrow"`
- After: `"Out of stock. Check back tomorrow."`

**Line 923** (same message, different code path):
- Before: `"Out of stock — check back tomorrow"`
- After: `"Out of stock. Check back tomorrow."`

**Line 925** (can't afford):
- Before: `"Not enough credits"`
- After: `"Can't afford it."`

**Line 927** (cargo full):
- Before: `"Not enough cargo space"`
- After: `"Hold's full."`

The trading messages now carry the working-class register called for by the standards doc ("Not enough credits. Ledger's short." beats "Insufficient funds."). `"Hold's full."` is more terse than `"Ledger's short."` but both fit the voice.

### `spacegame/views/shipyard_view.py` — 1 fix

Shipyard empty-slot message used a double-hyphen substitute for em-dash, which Sprint 5's scanner missed because the `.render()` call spanned two lines.

**Line 1637** (empty loadout slot):
- Before: `"Empty -- select a part below to equip"`
- After: `"Empty. Pick a part below to equip."`

### `spacegame/views/name_input_view.py` — 4 fixes

Character creation screen had multiple voice issues that together would have set the wrong tone for the player's first interaction with the game.

**Default name input text:**
- Before: `self.name_input.set_text("Captain")` — prefilled "Captain" as the default name
- After: `self.name_input.set_text("")` — empty, player types their own

The intro narration establishes the player as a scrapyard kid orphaned from a colony-ship mining rig. Pre-filling "Captain" contradicts that framing from the very first screen. Sprint 2's cockpit HUD fix avoided "Captain" as a persistent label; Sprint 5b extends the same discipline to character creation. An in-line comment in the source marks the intent so the default does not silently drift back.

**Launch button:**
- Before: `text="BEGIN JOURNEY"` — corporate marketing voice
- After: `text="LAUNCH"` — action-oriented, genre-native

"Begin your journey" is an AI-writing trope flagged by the Writing Bible. "LAUNCH" is a single action verb and fits space-game convention.

**Empty-name error:**
- Before: `"Please enter a name."` — generic politeness
- After: `"Type a name first."` — direct, voice-matching

**Overlong-name error:**
- Before: `"Name must be {MAX} characters or fewer."` — technical register
- After: `"Name too long. Keep it under {MAX} characters."` — direct

**Invalid-character error:**
- Before: `"Name can only contain letters, numbers, and spaces."` — technical register
- After: `"Letters, numbers, and spaces only."` — terser

---

## Button label audit results

The scanner flagged one button as "abstract" — `"Continue (Enter)"` in `encounter_view.py:175`. Kept as-is because "Continue" is the universal convention for acknowledging a narrative beat and moving past it; action-verb alternatives ("Acknowledge", "Proceed") read more formally than the working-class voice the game uses everywhere else. Not every button needs an action verb; some are procedural.

All other buttons extracted by the scanner either used valid action verbs (`Buy Part`) or were short single-word labels whose context made them clear.

---

## What the audit explicitly did NOT find

The audit scanned for:
- Abstract button labels (`Confirm`, `Apply`, `OK`, `Submit`) — **zero found**
- `error` / `failed` / `unable to` language — found 5 instances, all context-appropriate (combat/mission failure states, "Cannot talk (automated)")
- `please` / `kindly` / `you must` generic phrasing — 1 found (fixed above)
- `no results` / `none found` / `empty` boilerplate — found 9, mostly appropriate or already in-voice

This is a strong signal: the existing voice discipline is solid. Sprint 5b's fixes were isolated drift, not systemic patterns.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,301 passed, 98 skipped, 1 xfailed, 0 failed** |
| `ruff check` on touched files | Clean |
| Writing Bible scanner coverage | Widened to `_show_message`, `_show_feedback`, multi-line `.render()` |
| Concrete voice fixes this sprint | 9 (across 3 view files) |
| New Sprint 5b writing-bible violations found by widened scanner | 1 (trading_view:791, fixed) |
| Button labels flagged as abstract | 1 (kept — context-appropriate) |

---

## What's next

With Sprint 5b complete, the remaining Sprint arc items:

**Sprint 6** — state and motion polish (5 interactive states × 4 content states audit per view, motion-timing discipline)

**Trading legality badge refactor** — clears the last Sprint 3 xfail. The `" RESTRICTED"` / `" ILLEGAL"` text suffix should become a proper badge component.

**Colorblind calibration content pass** — find colorblind playtesters, refine Sprint 4/4b remap tables empirically. Needs external input.

**Controller support conversation** — still flagged for a dedicated session.

I'd recommend **trading legality badge refactor** next — it's the last remaining xfail in the whole suite, a bounded architectural change, and clears the Sprint 3c technical-debt item cleanly. Alternatively **Sprint 6** continues the systematic UI review. Your call.
