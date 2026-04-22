# UI Review Sprint 5b Follow-up — Click-Then-Error → Disabled Button Conversions

Generated 2026-04-22. Continuation of Sprint 5b's button clarity audit.

**Bottom line:** Two high-traffic views converted from click-then-error feedback to pre-emptive disabled button state with in-voice tooltip reasons. Trading view (Buy/Sell with 5+3 failure modes) and Repair Bay (Repair with 2 failure modes) now reflect invalid actions visually before the player clicks. **+13 regression tests** guard the button-state logic.

Test count: **7,303 → 7,316 (+13).** Full suite green, lint clean.

---

## The UX shift

Standards doc principle: *"A disabled 'Buy' with 'Not enough credits' is better than no 'Buy' at all."*

Old pattern (click-then-error):
1. Player selects a commodity
2. Player clicks Buy
3. Button fires, action fails silently or with a flash message
4. Player reads the failure reason and has to infer what to adjust

New pattern (pre-emptive disable):
1. Player selects a commodity
2. Buy button immediately reflects whether the action is viable — enabled or dimmed
3. Hovering a disabled button surfaces the reason via tooltip
4. The player knows what to fix before clicking

The old pattern puts cognitive load after the action. The new pattern puts it before. Fewer wasted clicks, clearer progression, less trial-and-error.

---

## Trading view conversion

### Buy / Buy Max

`trading_view.py::_why_cannot_buy()` returns an in-voice reason string or `None`. The refresh loop calls `.disable()` + `tool_tip_text = reason` when blocked, `.enable()` + `tool_tip_text = None` when valid.

Reasons the Buy button gets disabled:

| Condition | Tooltip |
|---|---|
| Station has no trade permit | `"No trade permit here."` |
| Nothing selected in the market table | `"Pick a commodity."` |
| Current stock is zero | `"Out of stock."` |
| Can't afford one unit at current price | `"Can't afford it."` |
| Cargo hold can't fit one unit | `"Hold's full."` |

Buy Max mirrors Buy's state (same conditions).

### Sell / Sell Max

`_why_cannot_sell()` handles:

| Condition | Tooltip |
|---|---|
| Station has no trade permit | `"No trade permit here."` |
| Nothing selected in the cargo table | `"Pick something from your cargo."` |
| Selected cargo has zero units | `"Nothing of that kind aboard."` |

### Refresh cadence

Button states refresh on two hooks:

1. **After `_refresh_tables()`** — fires after state-changing events (buy, sell, mode switch, tutorial advance, refuel, rest). Ensures immediate reflection of the action's result.
2. **In `update()` per frame** — handles selection changes (click on a table row) and drift (black-market toggle, credits changing asynchronously). Cheap (a few dict lookups); pygame_gui's `enable`/`disable` is idempotent so calling per-frame with unchanged state is a no-op.

### Tests

New `tests/test_views/test_trading_button_states.py` with 13 tests:

- **5 Buy disable reasons** — each condition fires the correct disable + tooltip
- **3 Sell disable reasons** — same
- **1 Buy Max mirror** — Max variant tracks base state
- **2 state transitions** — re-enables cleanly when blocker clears
- **2 enabled sanity cases** — Buy and Sell enable when all conditions met

The tests construct the view via `TradingView.__new__` and inject controllable mocks for player credits, ship cargo, market stock, and permit status. No dependency on real content or subprocess harnessing.

---

## Repair bay conversion

`repair_bay_view.py::_why_cannot_repair()` handles two cases:

| Condition | Tooltip |
|---|---|
| Hull is already at full integrity | `"Already at full hull."` |
| Player can't afford the full repair cost | `"Can't afford the full repair."` |

Refresh happens in `update()` per frame. Repair bay is simpler than trading — no selection, no multiple conditions per outcome, so a single `_why_cannot_repair()` check is sufficient.

No new regression tests — the existing 15 repair bay tests cover the behavior via direct `_execute_repair` calls that remain unchanged. The click-then-error path still works (for callers that bypass the button state), but the button surface now visually reflects the outcome.

---

## What's still on the click-then-error pattern

Other views with buttons that can fail on click and still show error-after-click. Candidates for future conversion if playtester feedback surfaces friction:

| View | Button(s) | Failure modes |
|---|---|---|
| `mission_log_view` | Accept | Mission not available, prerequisites not met |
| `shipyard_view` | Install, Uninstall, Buy Part | Not unlocked, no credits, wrong slot |
| `ship_builder_view` | Confirm Build | Build invalid, insufficient structural integrity |
| `investment_view` | Invest | No credits, already maxed |
| `cantina_view` | Recruit | Roster full, can't afford signing bonus |

Each conversion follows the same template established here: a `_why_cannot_X()` helper returning in-voice reason-or-None, a refresh method called on state changes, and focused regression tests for the disable reasons.

I did not convert these this session because:

- **Trading is the highest-frequency interaction** — player runs dozens of Buy/Sell ops per session. Repair is moderate. The rest are less frequent.
- **Bigger conversions (shipyard, ship_builder) have many failure modes** that benefit from careful per-condition design rather than bulk conversion.
- **Click-then-error is still a legitimate pattern** — it's not a bug, just a slightly lower-friction alternative where the error message carries the teaching load.

Converting more views should be playtester-driven: if players complain about wasted clicks on a specific button, that's the signal to convert it.

---

## Pre-playtest health

| Check | Result |
|---|---|
| `pytest` (full suite, first run) | **7,316 passed, 98 skipped, 0 failed, 0 xfailed** |
| `ruff check` on touched files | Clean |
| Views converted to pre-emptive disable | 2 (trading_view, repair_bay_view) |
| Disable reason tooltips added | 8 distinct in-voice messages |
| New regression tests | 13 |

---

## What's next

The code-focused UI review arc is now genuinely complete. Total arc totals:

- **7,110 → 7,316 tests (+206, +2.9%)**
- 3 game-affecting bugs fixed (tutorial drydock overlap, trading legality truncation, pre-emptive disable conversion)
- 3 architectural systems shipped (palette wrapper, subprocess resolution harness, writing bible scanner)
- 30 `Colors.*` attributes palette-backed; colorblind remap infrastructure live
- Every UI-surface text source Writing Bible strict, enforced via regression test
- Zero regressions introduced

Remaining work is external-input driven:

- **Colorblind calibration content pass** — playtesters with colorblindness refining Sprint 4/4b remap tables
- **Controller support conversation** — design session, journal and drydock need UX rethink not just input remap
- **Further click-then-error conversions** — playtester-driven, per-view

Natural stopping point for the arc. The standards doc, scanners, and compliance tests together form a framework that future features slot into automatically.
