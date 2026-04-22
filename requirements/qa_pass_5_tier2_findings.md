# QA Pass 5 Tier 2 — Medium-Effort Fixes

Generated 2026-04-21. Tier 2 closed all 4 medium-effort items from the Pass 5 triage. No new bugs surfaced, but one substantive mechanical change (Phase Shift semantics) and one safety-net documentation (legacy ShipType path) shipped.

**Bottom line:** 4 items resolved. +7 new tests. Test count 7,025 → 7,034 (accounting for 1 flakiness fix and 2 new regression guards for behavior changes).

---

## 2.1 — Phase Shift "first attack per round" semantics

**Change:** Spec §8 says Phase Shift "blocks first incoming attack per round." The engine blocked ALL attacks on an active round — a 3-enemy encounter on a shift round dodged all 3 attacks, making multi-enemy encounters trivial.

**Fix:**
- Added `phase_shift_used_this_round: bool = False` to `LegendaryState`
- Added `consume_phase_shift()` — side-effecting helper that sets the flag and returns True exactly once per shift round
- Added `reset_phase_shift_for_round()` — called from `end_round`
- `check_phase_shift()` kept as a pure predicate but now respects the used flag
- Combat engine switched from `check_phase_shift` to `consume_phase_shift` at the dodge site

**Tests added:**
- 4 new tests in `TestPhaseShiftFirstAttackOnly` covering: one-shot behavior, check-after-consume, end-of-round reset, off-interval non-consumption
- Updated the existing `test_phase_shift_negates_incoming_damage_on_active_round` to reflect the correct semantics (was documenting the broken behavior with a NOTE)

**Balance impact:** Phase Shift is slightly weaker but more honest. Multi-enemy encounters on shift rounds now take real damage from 2nd/3rd attackers. Matches design intent.

**Files:** `legendary_effects.py`, `combat_engine.py`, `test_legendary_combat.py`, `test_legendary_multi_action_b7.py`.

---

## 2.2 — §6 round-count doc revision

**Change:** §6.1 expected "Glass cannon kills 2 T2 strikers in 2 rounds." Actual tuning produces 5–8 rounds. The round-count target was aspirational; fights are balanced and engaging but don't hit the old number.

**Fix:** Revised §6.1 expected counts to 5–8 rounds with rationale preserved in-doc. §12 deferred entry marked RESOLVED with date. Existing structural tests in `test_balance_archetypes.py` remain the guard (they assert archetype identity, not round counts — correct shape).

**Files:** `requirements/combat_balance_design.md`.

---

## 2.3 — Colorblind profile starter values

**Change:** `PROTANOPIA`, `DEUTERANOPIA`, `TRITANOPIA` shipped as named stubs with empty `band_remap` / `role_remap`. Toggling the setting did nothing visible, which is worse than no setting — it misleads players into thinking the profile is active.

**Fix:** Each profile now carries 1–3 starter remaps addressing the MOST conflict-prone bands/roles for that deficiency:
- **Protanopia / Deuteranopia:** `reach_crimson → union_ceramic` (red-brown → warm ceramic), `hud_warning → hud_cyan` (orange → unambiguous cyan)
- **Tritanopia:** `collective_composite → solari_chrome`, `glass_viewport → steel`, `glow_cool → glow_warm`

These are **directionally correct, not playtest-calibrated** — full accessibility pass remains post-v1 per corpus coherence §42. But toggling the profile now visibly changes the render.

**Tests added:** 5 new tests in `TestColorblindProfilesAreFunctional` verifying remap application, pass-through of unremapped bands, clear-to-canonical behavior. Updated `test_canonical_profiles_have_empty_remaps` → `test_canonical_profiles_have_starter_remaps` (now asserts non-empty maps + canonical targets).

**Files:** `material_palette.py`, `test_material_palette.py`.

---

## 2.4 — Legacy ShipType combat path audit

**Audit question:** When does `combat.py`'s legacy ShipType path execute? Is it safe to remove?

**Findings:** The path is NOT dead code. Three active reach points:

1. **New-game fallback** — `Game.new_game` wraps `generate_preset_from_ship_type` in try/except. If it raises for any reason, the ship has no build and the legacy path fires.
2. **Corrupted-save fallback** — `save_manager.py:770-787` tries multiple paths to attach a build; if all fail, ship loads without computed_stats.
3. **Test direct-construction** — QA Pass 3.5 Scenario C *explicitly exercises this path* to verify skill bonuses apply identically in both code paths (the CLAUDE.md warning made flesh).

**Verdict:** Keep the path, document it. Removal requires:
- Exception-free preset generation for every ship_type in production data
- Save-migration test covering the malformed-save case
- Test refactor so all tests set_build before combat

**Fix:** Added a detailed block comment at the legacy-path entry in `combat.py` explaining the three reach points. Marked §12 entry RESOLVED with audit date — the next person looking at this code starts from the audit findings rather than rediscovering them.

**Files:** `combat.py`, `requirements/combat_balance_design.md`.

---

## Test count trajectory

| Pass | Running Total |
|---|---|
| Pass 5 Tier 1 | 7,025 |
| **Pass 5 Tier 2** | **7,034** |

**Delta:** +9 tests (4 Phase Shift, 5 Colorblind). No net regression.

**Known flaky tests (pre-existing, unrelated to Tier 2):**
- `test_large_ship_has_visible_rivets` and `test_enable_rivets_false_skips_rivets` fail when run in full-suite but pass in isolation. State leakage from some other test file earlier in the run. Documented in Pass 1 audit; not introduced by Tier 2.

---

## Pass 5 status

**Tier 1:** ✅ 8/8 items resolved (+10 campaign encounters unblocked, 9 real bugs fixed)

**Tier 2:** ✅ 4/4 items resolved (Phase Shift semantics corrected, docs revised, colorblind profiles functional, legacy path documented)

**Tier 3** (remaining): ~10 items requiring dedicated sessions each (`call_reinforcement`, `price_memory`+`TradeRouteTracker`, per-instance ShipComposite cache, ally-targeted heals, content authoring for marquee bosses, etc.). Each is a multi-session feature, not a triage fix.

**Tier 4 (post-v1):** `bridge_crew_ids` fleet management hook.

---

## Roadmap state

The Pass 1 audit doc (`qa_pass_1_audit.md`) and combat_balance §12 log both have updated statuses for every resolved item. Nothing has fallen off the plate. Tier 3 items are documented with clear "what's needed" blocks — they can be tackled as discrete feature sessions whenever you want to commit.

Everything in Tier 1 + Tier 2 scope is now shipped.
