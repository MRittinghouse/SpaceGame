# Writing Bible Scanner Coverage Gaps — Aurelia: A Ledger of Stars

**Status**: stub, 2026-04-26. Surfaced during station_legibility.md pre-tasks. Not yet scoped.

**Origin**: while adding a parallel-negation allowlist for the Reach faction tagline ("No laws. No mercy. No refunds.") in `tests/test_writing_bible_compliance.py`, two coverage gaps in the existing scanner became visible. The allowlist is forward-defensive — without these gaps closed, the Reach tagline isn't being caught today regardless of allowlist state.

**Sister doc**: `requirements/ui_sprint_5_findings.md` originated the scanner. This doc tracks extensions to it.

---

## Gap 1 — Station taglines are not scanned

`StationLayout` subclasses in `spacegame/views/station_layouts.py` declare `faction_tagline` as a class attribute (e.g., `faction_tagline = "Built by hands, not contracts."`). Rendering goes through `self._tagline_font.render(self.faction_tagline, ...)`. The scanner's `_RENDER_STRING` regex matches `.render("literal string")` calls only — it does not follow variable references back to attribute declarations. So the tagline content slips through every existing test.

**Coverage**:
- Guild: "Commerce. Order. Prosperity." — currently uncaught
- Union: "Built by hands, not contracts." — currently uncaught
- Collective: "Through knowledge, understanding." — currently uncaught
- Frontier: "The frontier takes care of its own." — currently uncaught
- Reach: "No laws. No mercy. No refunds." — currently uncaught (also period-parallelism, see Gap 2)

**Fix shape**: add a small `_extract_tagline_strings()` extractor to the scanner that walks `StationLayout`'s subclasses (or imports `station_layouts` and pulls the `faction_tagline` attribute from each). Add three tests mirroring the existing pattern (em-dashes, banned phrases, parallel-negation). Estimated 30-40 lines.

---

## Gap 2 — Parallel-negation regex is comma-separated only

The current `_PARALLEL_NEGATION = re.compile(r"\bno \w+,\s*no \w+", re.IGNORECASE)` requires literal `,` between the parallel terms. The Writing Bible's intent (per CLAUDE.md and `requirements/dialogue_writing_guide.md`) is broader: any "no X, no Y" rhetorical construction, regardless of separator. Period-parallelism ("No X. No Y.") slips through, as does dash-parallelism ("No X — no Y").

**Fix shape**: broaden the regex to match `\bno \w+[,.\s][\s\.]*\bno \w+` or similar, with care taken not to false-positive on innocent "no X" sentences that happen to be near other "no Y" sentences in unrelated contexts. Probably needs a sentence-window heuristic rather than a flat regex.

**Risk**: tightening the regex may catch existing content that was authored before the rule was tightened. Run on all existing scanned content first; if violations surface, treat as a content audit, not a scanner regression.

---

## Suggested sequencing

These gaps don't block any active sprint. They block enforcement of a Writing Bible rule that the Reach tagline allowlist *anticipates* but doesn't currently rely on.

Prioritization signal: low. The Writing Bible compliance scanner already covers the bulk of UI-surface text. These two extensions close edge cases. Pick up when the next Writing Bible sprint runs (likely a sister to UI Sprint 5b's deferred button-clarity audit) or as a small follow-up after SL-1 lands.

---

## What this doc is not

- Not a commitment. May stay a stub indefinitely if no other Writing Bible sprint is scoped.
- Not a critique of the existing scanner. The scanner already prevented 10+ violations in active content; these are gaps at the margin.
- Not the full list of possible scanner extensions. Other surfaces (cockpit_hud chatter, station chatter ambient lines, encounter narration) may have similar variable-reference-vs-literal issues. Audit those if scope expands.
