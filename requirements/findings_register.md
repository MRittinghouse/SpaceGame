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
| F-005 | balance | "A ton of ways to softlock if you spend poorly." Economy permits unrecoverable states. The Godot port detects the dead end and ends the game (bug bash BB-3, aurelia plan B2); this build keeps the soft-lock. Since bug bash plan B1 a board contract's sealed cargo is one more way in: a broke captain whose only cargo belongs to a running board contract cannot sell it. | Playtest 2026-05-05 (designer's own assessment) | Balance track |
| F-006 | infra | Crawler cannot pass the onboarding gauntlet, so cold-boot coverage stops at 3 of 41 states. Needs hit-rect registry entries per screen. | Crawler, 2026-08-23 | QF-6D |
| F-007 | infra | xdist worker death at high worker counts; bounded but not understood. | SUITE-1, 2026-08-26 | SUITE-2 |
| F-008 | infra | `tests/test_ralph/` is not isolated from the real project-root `STOP` file; 3 tests fail spuriously when one exists. | Observed 2026-08-26 during a graceful stop | SUITE-2 |
| F-009 | hygiene | `CONVENTIONS.md` states sprints are `<h3>`, but the entire SA arc uses `####`. A scan written from the docs finds zero SA sprints. | 2026-08-24 | wontfix-for-now — documented in `scripts/sync_roadmap_index.py`; fix if a third heading level ever appears |
| F-010 | hygiene | `ruff check tests/` reports 874 findings. Lint is scoped to `spacegame/` for this reason. | QF-1, 2026-08-23 | wontfix-for-now — mechanical, low value, would bury real work |
| F-011 | hygiene | Legacy `tools/` scripts carry ~198 mypy errors and are ungated. `tools/crawler/` is gated at zero. | QF-2, 2026-08-23 | wontfix-for-now — build-time utilities, not shipped code |
| F-012 | hygiene | `ralph/agents.py:181` RUF005 (list concatenation). `ralph/` is not in the lint gate. | 2026-08-26 | wontfix-for-now — pre-existing, harmless |
| F-013 | content | `SA-F2 — Futures Core` is genuinely `blocked`, gating six Phase V sprints (SA-F3..SA-F7). Not a data defect; awaiting a human decision. | 2026-08-24 | needs decision — Matt |
| F-014 | content | The reference build ships content only the Godot port reads (bug bash BB-27, BB-3): `data/economy/balance.json`'s `economy.new_market_premium` block and `data/economy/first_sale_lines.json`, which Python ignores (it keeps its first-sale 1.5x bonus), and Emergency Reserves' description, which names the port's sealed reserve cell while Python keeps its 1-fuel floor. `tests/test_data/test_port_only_content.py` pins all three. | Bug bash plan B1, 2026-09-30 | wontfix: Python is the goldens' reference build; the port's deviations D-23 and D-25 record the difference |
| F-015 | softlock | A crew loyalty change made inside a conversation never sets its threshold flag. `DialogueManager`'s response handler passes a reply's `crew_loyalty_changes` to `CrewRoster.adjust_loyalty` and discards the `crew_loyalty_<id>_<threshold>` flags it returns, and a threshold is crossed only once, so a crew quest reply that carries a companion past 70 or 85 (some give +25) leaves that flag unset for good and the companion's next crew quest never opens. The Godot port drops the same flags on purpose to match this build (aurelia F-45, open since 2026-09-28; `core/dialogue/dialogue_manager.gd`, `_crew_loyalty`). | Bug bash plan B1 Task 3 review, 2026-10-01 | needs decision: Matt, with the crew quests (polish design section 3) and aurelia F-45; the fix sets each returned flag on the dialogue copy, in both builds |

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
| F-C09 | softlock | A save dropped every flag written outside a conversation. `Game._save_game` replaced the player's flag store with the dialogue manager's copy, which loads only when a conversation opens or a game loads, so a mission's accept flag, a reward's `set_flag`, the iron clock's flag at a rest and the sale sensor's flag were lost at the next dock's auto-save unless a conversation opened first; Reva's and Dex's gates (`cargo_lost_accepted`, `cargo_lost_complete`) and plan A1's Mossa gate (`the_dead_ledger_accepted`) would strand, and the first sale's 1.5x re-armed after every save. The mirror image held too: `check_crew_xp` and `check_missions` wrote a crossed crew loyalty threshold flag (`crew_loyalty_<id>_50`, `_70`, `_85`) to the copy alone, so a conversation opened before the next save reloaded the copy and dropped it for good, and the crew quests and NPC states it gates never opened. Found planning bug bash B1 (the loyalty half while landing it). | Bug bash plan B1, 2026-09-30: a save lays the player's store over the copy, in place, so a running combat's reference to the store stays live (`DialogueManager.merged_flags`); a new game reloads the copy (`initialize_new_game`); the crew loyalty threshold flags (`check_crew_xp`, `check_missions`) write the player's store too; `tests/test_engine/test_save_flag_stores.py`, `test_check_crew_xp.py`, `test_check_missions_payout.py` |
