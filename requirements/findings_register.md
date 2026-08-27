# Findings Register

Every observation that is worth acting on but is not yet a sprint, classified so
it can be routed by kind rather than triaged one at a time.

## Why this exists

Findings arrive from everywhere: playtest transcripts, crawler runs, code review,
things noticed in passing while fixing something else. Most are not sprint-sized
at the moment they surface, and a flat "bug list" loses them, because the list
gets sorted by whoever writes it rather than by what kind of problem it is.

The specific failure this prevents: **"technically a bug, but really a
player-experience issue."** Refuel buying one unit at a time is a defect by any
strict reading, but filing it next to a crash guarantees it never gets fixed,
because crashes always win. Classified as an `affordance` finding routed to Spec
C, it competes only with its peers.

## Classes

| Class | Meaning | Typically routed to |
|---|---|---|
| `crash` | The game throws or the process dies. | Quality arc; fix immediately |
| `softlock` | The player cannot proceed. Not a crash; worse. | Quality arc / balance |
| `affordance` | The UI misleads, hides, or fails to teach. The player does the wrong thing and it is not their fault. | Spec C (legibility) |
| `balance` | Numbers, pacing, economy. Play is possible but unsatisfying or exploitable. | Balance track |
| `content` | Missing or thin authored material. | Spec D corpus |
| `hygiene` | Code or doc debt with no player-visible effect. | Opportunistic |
| `infra` | Harness, CI, or test-suite defects. Blocks work rather than players. | SUITE arc |

## Disposition

Every finding carries one of:

- a **sprint ID** (`QF-6D`, `SUITE-2`) — scheduled
- a **spec name** (`Spec C`) — accepted, not yet scheduled
- `wontfix` with a reason — a decision, recorded

Nothing sits without a disposition. `tests/test_compliance/test_findings_register.py`
fails the suite if any row lacks a class or a disposition, so a finding cannot
quietly rot here instead of quietly rotting somewhere else.

---

## Open findings

| ID | Class | Finding | Source | Disposition |
|---|---|---|---|---|
| F-001 | affordance | Refuel buys 1 unit because the quantity box defaults to `"1"`, and the `except ValueError` path fills the tank. Being precise strands the player; being sloppy fills up. Inverted affordance. | Playtest 2026-05-05 (Ish1da stranded) | Spec C |
| F-002 | affordance | The hull screen is effectively unfindable. The designer had to explain its location ("top center, on the right ish") with a screenshot. | Playtest 2026-05-05 | Spec C |
| F-003 | affordance | The tutorial exists but does not land — the player did not know it was there. | Playtest 2026-05-05 | Spec C |
| F-004 | affordance | New-game onboarding is three-plus consecutive hand-drawn screens (confirm dialog → intro narration → name entry) with no pygame_gui affordances. A player's first five minutes are bespoke one-offs. | Crawler, 2026-08-23 | Spec C |
| F-005 | balance | "A ton of ways to softlock if you spend poorly." Economy permits unrecoverable states. | Playtest 2026-05-05 (designer's own assessment) | Balance track |
| F-006 | infra | Crawler cannot pass the onboarding gauntlet, so cold-boot coverage stops at 3 of 41 states. Needs hit-rect registry entries per screen. | Crawler, 2026-08-23 | QF-6D |
| F-007 | infra | xdist worker death at high worker counts; bounded but not understood. | SUITE-1, 2026-08-26 | SUITE-2 |
| F-008 | infra | `tests/test_ralph/` is not isolated from the real project-root `STOP` file; 3 tests fail spuriously when one exists. | Observed 2026-08-26 during a graceful stop | SUITE-2 |
| F-009 | hygiene | `CONVENTIONS.md` states sprints are `<h3>`, but the entire SA arc uses `####`. A scan written from the docs finds zero SA sprints. | 2026-08-24 | wontfix-for-now — documented in `scripts/sync_roadmap_index.py`; fix if a third heading level ever appears |
| F-010 | hygiene | `ruff check tests/` reports 874 findings. Lint is scoped to `spacegame/` for this reason. | QF-1, 2026-08-23 | wontfix-for-now — mechanical, low value, would bury real work |
| F-011 | hygiene | Legacy `tools/` scripts carry ~198 mypy errors and are ungated. `tools/crawler/` is gated at zero. | QF-2, 2026-08-23 | wontfix-for-now — build-time utilities, not shipped code |
| F-012 | hygiene | `ralph/agents.py:181` RUF005 (list concatenation). `ralph/` is not in the lint gate. | 2026-08-26 | wontfix-for-now — pre-existing, harmless |
| F-013 | content | `SA-F2 — Futures Core` is genuinely `blocked`, gating six Phase V sprints (SA-F3..SA-F7). Not a data defect; awaiting a human decision. | 2026-08-24 | needs decision — Matt |

## Closed findings

| ID | Class | Finding | Closed by |
|---|---|---|---|
| F-C01 | crash | Sell All threw `TypeError` — view passed the buy signature to `sell_commodity`. | Fixed pre-QF; regression test in `test_trading_actions.py` |
| F-C02 | crash | Entering combat crashed. | QF-8 / SH-1 / SH-3 — crash-class errors driven to zero codebase-wide |
| F-C03 | infra | Pre-commit config committed but hook never installed; gate was inert. | 2026-08-24, enforced by `test_precommit_hook_installed.py` |
| F-C04 | infra | ROADMAP index tables drifted from sprint sections. | 2026-08-24, enforced by `test_roadmap_index_sync.py` |
| F-C05 | infra | `market.py` reseeded the global RNG from entropy, breaking crawler determinism. | QF-6B — local `random.Random` instance |
| F-C06 | infra | Crawler clicked the main menu's Exit button and quit its own session. | QF-6C — identity-based terminator registry |
| F-C07 | infra | Crawl runs mutated committed save fixtures. | QF-6C — fixtures copied to a temp dir |
| F-C08 | infra | Baseline capture returned `(0, 0)` silently on timeout; agents then ran with no regression baseline. | SUITE-1 — raises `BaselineCaptureError` |
