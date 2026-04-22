# Risk Register

> **Status:** v1 — honest enumeration of implementation risks across the overhaul corpus. Written pre-implementation; expected to evolve as real implementation surfaces empirical risks not visible from design alone.
>
> Each risk has: category, probability, impact, description, mitigation, escalation trigger. Probability × Impact × Effort-to-Mitigate informs where to invest attention first.

---

## Table of Contents

1. How to use this document
2. Risk scoring rubric
3. Technical risks
4. Content risks
5. Process risks
6. UX risks
7. Top-5 concentration watch
8. Escalation protocol
9. Update process

---

## 1. How to use this document

### 1.1 Before starting a phase

1. Scan §3-§6 for risks tagged to this phase
2. Confirm mitigations are in place or planned
3. If a risk's escalation trigger activates during the phase, pause and apply the mitigation before continuing

### 1.2 When risk materializes

1. Note which risk triggered (update §7 watchlist)
2. Apply the documented mitigation
3. If mitigation proves inadequate, update the register with lessons learned

### 1.3 Periodic review

Weekly during active implementation. Add new risks as observed; close risks that haven't materialized after their phases ship.

---

## 2. Risk scoring rubric

**Probability:**
- **Low** — <25% chance of occurring during the relevant phase
- **Medium** — 25-60% chance
- **High** — >60% chance

**Impact:**
- **Low** — costs hours to recover; does not derail phase
- **Medium** — costs days to recover; may delay phase but not cascade
- **High** — costs weeks to recover; cascades into downstream phases or corpus revision

**Priority = Probability × Impact.** High/High risks get proactive mitigation; Low/Low risks get monitored.

---

## 3. Technical risks

### RT-1 — ShipComposite rebuild performance regression

**Category:** Technical
**Probability:** Medium
**Impact:** High
**Phases affected:** Framework §2 foundation → Combat C4, Builder B1/B5, Salvage S5, Station Hub H5

**Description:** The rebuilt `ship_composite.py` is a fundamentally different algorithm (unified-object rendering per Framework §6) vs. the current tile-stitch. The rebuild could be slower than the current implementation if caching, pooling, or shader discipline is inadequate. Combat with 4-6 ships + active VFX + 60 FPS target could miss frame time.

**Mitigation:**
1. **Benchmark current implementation before rebuild.** Establish baseline frame time for combat with 1, 3, 6 ships. Document in `tests/performance/baseline.md`.
2. **Cache aggressively.** Per Framework §9.3, ship composites cache by build-hash; rebuild only on changes. Production must hit cache in steady-state combat.
3. **Profile continuously during rebuild.** Run combat benchmark after each significant change; flag regressions immediately.
4. **Per Tier 2 doc §12 Success Criteria**, each system declares frame budget. Combat: 8ms. Builder: 10ms. These are contracts.
5. **Reserve fallback**: if rebuild blows budget, cache pre-rendered composites at higher resolution and downsample rather than rebuild per frame.

**Escalation trigger:** combat scene drops below 60 FPS with standard load during rebuild integration. Halt rebuild; profile; optimize.

### RT-2 — SceneCamera feel drift across consumers

**Category:** Technical / UX
**Probability:** Medium
**Impact:** Medium
**Phases affected:** Combat C1 (first integration) → all 8 downstream consumers

**Description:** SceneCamera's transitions might feel mechanically identical across 9 systems, producing a "same-camera-everywhere" sensation. Different scenes want different camera feels — combat wants punchy + recoveries; galaxy jumps want weight; builder orbit wants serene.

**Mitigation:**
1. **First integration (Combat C1) gets an explicit "feel pass"** — tune easing curves, durations, shake intensities against subjective feel before any other consumer adopts.
2. **Each subsequent consumer's first use gets its own feel pass.** Builder orbit may want `ease_in_out_cubic` with 1.2s; combat focus wants `ease_out_cubic` with 0.3s; galaxy jump wants scripted segments with distinct curves per phase.
3. **Document per-consumer curves in the consumer's code** — don't bury in config.
4. **Playtest each consumer integration in isolation** before moving to next.

**Escalation trigger:** any consumer's transitions feel "off" on first playtest. Pause adoption, tune curves, resume.

### RT-3 — Palette compliance regression during implementation

**Category:** Technical
**Probability:** Medium
**Impact:** Medium
**Phases affected:** All rendering phases

**Description:** Implementation choices — developer convenience, quick-fix RGB hardcodes, temporary debug colors — drift from the canonical palette (Bible §2). Drift compounds silently until a visual audit catches it.

**Mitigation:**
1. **Palette compliance tests run in CI** — `assert_band_compliance` and `assert_role_compliance` per Bible §2.5. Tests fail merge if hand-tuned RGB appears in rendered output.
2. **VFX audit pass** (VFX §6.2) migrates existing hand-tuned RGB to palette lookups before consumers adopt.
3. **Grep discipline**: periodic grep for RGB tuple literals (`\(\d+,\s*\d+,\s*\d+\)`) in rendering code; migrate any hits.
4. **Developer shortcut**: provide `rgb(role_name)` helper in `draw_utils` so the path of least resistance is palette-compliant.

**Escalation trigger:** CI palette test fails on 3+ consecutive commits. Focused migration pass required.

### RT-4 — Save data model changes cause playtest disruption mid-episode

**Category:** Technical / Process
**Probability:** Low (per alpha "be bold" stance)
**Impact:** Medium
**Phases affected:** Any phase adding persistent state

**Description:** Per `feedback_alpha_no_backcompat.md`, save wipes between version bumps are acceptable in alpha. However, **within a single playtest episode**, changing the save model would invalidate testers' in-progress saves — disrupting the test they're conducting.

**Mitigation:**
1. **Version bumps coincide with playtester release** — never mid-episode. A tagged test-episode build freezes save model; subsequent development may break the model; next test-episode release starts fresh.
2. **Communicate save wipes clearly to playtesters** — "version X → Y includes save changes; start fresh."
3. **No defensive backward-compat scaffolding** — just document the break.

**Escalation trigger:** unplanned save-model change during an active playtest episode. Communicate to playtesters; offer save-wipe or version-rollback guidance.

### RT-5 — Cross-system primitive API mismatches surface late

**Category:** Technical
**Probability:** Medium
**Impact:** High
**Phases affected:** Phases consuming shared primitives after foundation

**Description:** SceneCamera spec is documented (`91_scene_camera_api.md`), but ShipComposite rebuild API is not yet spec'd to the same depth. When Builder B1 or Salvage S5 tries to consume the rebuild, they may find API gaps.

**Mitigation:**
1. **Spec ShipComposite rebuild API before Framework §2 implementation begins.** Follow the `91_scene_camera_api.md` pattern. Create `92_ship_composite_api.md` (future).
2. **Foundation phases coordinate via API specs, not implementation.** Downstream consumers read the spec; implementation follows the spec contract.
3. **Integration tests per consumer** — Combat C4, Builder B1, Salvage S5, Station Hub H5 each get integration tests against the rebuilt ship_composite as part of their phase.

**Escalation trigger:** a consumer's phase is blocked on a missing API capability. Pause consumer phase; update foundation spec; coordinate rebuild extension; resume.

### RT-6 — VFX pool overflow during cinematic moments

**Category:** Technical / UX
**Probability:** Low
**Impact:** Medium
**Phases affected:** Combat C5 (dual tech), Combat destruction, Galaxy G2 (jump)

**Description:** Particle pool capped at 500 (VFX §7.1). Cinematic moments can burst: dual tech cinematic + enemy destruction + player ship atmosphere + remaining effects could theoretically exceed cap. Priority system culls low-priority emissions, but cinematic beats might drop their own particles if not carefully budgeted.

**Mitigation:**
1. **Cinematic budget enforced** (VFX §7.3) — single cinematic at a time; ceiling 400 particles during burst.
2. **Priority-based culling** — cinematic emissions are priority 1.0; ambient drops first.
3. **Profile cinematic moments** — combat destruction + dual tech + multiple enemies should stay within budget.
4. **Pool cap can grow to 750+** if empirically needed; 500 was a first pass.

**Escalation trigger:** a cinematic visually drops particles (gaps in fragment spray, thin shield burst) during playtest. Profile; raise cap or tune budget.

### RT-7 — Framework §2 rebuild scope creep

**Category:** Technical
**Probability:** Medium
**Impact:** High
**Phases affected:** Framework §2 foundation (blocking 5 consumers)

**Description:** The ship_composite rebuild is estimated 600-800 lines (Framework §2). "While we're rebuilding anyway" temptations — adding extra features, refactoring surrounding code, improving un-related areas — could balloon scope and delay foundation completion.

**Mitigation:**
1. **Rebuild scope is frozen by the Framework §2 specification.** Features outside the spec are explicitly out-of-scope.
2. **"While we're here" improvements get logged for future passes** — not included in the rebuild.
3. **Time-box the rebuild** (2-3 weeks per coherence review §4.1). If overrun threatens, re-scope to minimum viable surface and defer extensions.

**Escalation trigger:** rebuild estimate doubles during implementation. Re-scope to MVP; defer non-essential features to phase 2 of rebuild.

---

## 4. Content risks

### RC-1 — Voice drift across 107k words of authoring

**Category:** Content
**Probability:** High
**Impact:** Medium
**Phases affected:** Mining M3-M5, Salvage S3-S6, Refining F3-F5, Ground GR4-GR5

**Description:** Multi-agent content authoring is the biggest content-phase risk. Different agents produce different voices even with the same style guide. The Prospector's union-coded voice, Salvager's haunted terse voice, Fabricator's precise measured voice, plus cross-identity consistency — this is genuinely hard.

**Mitigation:**
1. **Glossary (`90_glossary.md`)** — canonical term reference. Reduces surface-level drift.
2. **Voice-sheets per identity** — refer to `requirements/character_voices.md` + Bible §10.4 pivot constraints. Consider extending voice-sheets to include Prospector / Salvager / Fabricator voices explicitly.
3. **Writing Bible** (`requirements/dialogue_writing_guide.md`) — existing authored-voice discipline.
4. **Pilot chapter first** — author Mining Chapter 1 in isolation; user reviews voice; establishes calibration before scaling.
5. **Voice review pass per chapter** — dedicated review agent or user review before chapter commit.
6. **Chapter-by-chapter review cadence** — do NOT author entire campaigns in one pass; break into chapter units with review gates between.
7. **Banned-trope scan** — grep each chapter for em-dashes, "no X, no Y" constructions, "testament to", "couldn't help but" before accepting.

**Escalation trigger:** a chapter's voice review surfaces 10+ drift issues. Calibrate agent + re-author before continuing.

### RC-2 — Content authoring fatigue / timeline slip

**Category:** Content / Process
**Probability:** Medium
**Impact:** High
**Phases affected:** Mining M3-M5, Salvage S3-S6, Refining F3-F5, Ground GR4-GR5

**Description:** 107k words is sustained marathon work. At 2-4k words per week sustained pace, that's 6-14 months. Burnout, quality degradation, deprioritization against more tangible engineering tasks all threaten the content phases.

**Mitigation:**
1. **Content priority cuts documented** (coherence review §5.4) — provide a deferrable stack if schedule compresses.
2. **Parallelize across agents** — one agent per identity reduces single-stream fatigue.
3. **Phase gating** — ship foundation + core chapters before optional content. Core content (Mining Ch1-5, Salvage Ch1-5, Ground named encounters + expedition voice) is ~55% of total budget and highest priority.
4. **User review cadence is a gate** — don't over-author ahead of review. Matches review pace.
5. **Accept incremental release** — Mining Chapter 1 can ship before Chapter 6 is written; players engage progressively.

**Escalation trigger:** authored content falls behind engineering phases by 2+ weeks sustained. Cut optional content per §5.4 or extend parallelization.

### RC-3 — Cross-identity acknowledgment gets dropped

**Category:** Content
**Probability:** Medium
**Impact:** Low
**Phases affected:** All content phases

**Description:** Bible §10.3 commits to ~30-40 lines of cross-identity acknowledgment (Augustyn mentions salvage wrecks; Mattsen notes Fabricator buyers). This is easy to skip under scope pressure; the explicit lines go un-authored, and the cultural-geography-by-work payoff is weaker.

**Mitigation:**
1. **Named in content priority list** (coherence review §5.4) — cross-identity lines are Priority 7, explicitly documented so they don't silently vanish.
2. **Bake into character content at author-time** — when writing Augustyn's content, include his salvage cross-reference line as part of the initial draft. Don't treat as separate pass.
3. **Cross-reference tracker** — lightweight list of committed cross-references; mark off during authoring.

**Escalation trigger:** content ships without cross-references. Small follow-up pass to add them; not a blocker.

### RC-4 — Named NPC name drift (GenAI tells, banned names)

**Category:** Content
**Probability:** Medium
**Impact:** Medium
**Phases affected:** All content phases; particularly Mining M3-M4, Salvage S3-S4, Refining F4

**Description:** Agent-authored names frequently default to AI-generic (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose per MEMORY.md). Aurelia's named characters need grounded naming — real ethno-cultural blends reflecting the cultural guide's Earth-cultures composition. Naming drift breaks worldbuilding.

**Mitigation:**
1. **Banned names list** — documented in Bible §13 / glossary §14. Part of agent onboarding.
2. **Pre-authored named character roster** — NPCs are named in the Tier 2 docs already (Augustyn Voss, Marta Beleń, Itzal Remé, Cesarine Vega, Mattsen Holt, Erika Sennen, Cesarine "Ces" Marrot, Pell Bray, Adisa Lark, etc.). These are committed; agents author dialogue, not invent names.
3. **New-name review** — when a Tier 2 phase needs a new NPC beyond those already named, user reviews before authoring commits.
4. **Banned-name grep** — CI or pre-commit scan for banned names.

**Escalation trigger:** agent authors content with banned name in it. Immediate rename + agent recalibration.

### RC-5 — Scope creep in content ("wouldn't it be cool if...")

**Category:** Content
**Probability:** Medium
**Impact:** High
**Phases affected:** All content phases

**Description:** Mining rival NPCs could each have 8-12 scenes or 20+. Legendary Seams could be 6 or 15. Commission clients could have 48 scenarios or 120. Mid-authoring, the desire to expand is strong.

**Mitigation:**
1. **Tier 2 doc scope is frozen per phase** — v1 counts are commitments; increases are post-launch expansion scope.
2. **"Content expansion reservoir" phase** (M7, S7, etc.) — deferrable perpetual-content phase. Ideas go here, not into current phase.
3. **Backlog file** — maintain a `CONTENT_BACKLOG.md` for future ideas during authoring.
4. **Per-phase scope freeze** — before authoring a phase begins, re-confirm scope against the Tier 2 doc; deviations require user approval.

**Escalation trigger:** phase authoring produces >20% more content than scoped. Pause; scope review; either absorb into current phase (if low cost) or defer to expansion reservoir.

---

## 5. Process risks

### RP-1 — Phase dependency ambiguity causes wasted work

**Category:** Process
**Probability:** Low (mitigated by §92 code-touch map)
**Impact:** Medium
**Phases affected:** Any phase that starts before dependencies are clear

**Description:** A Tier 2 phase starts implementation, discovers mid-phase that it actually blocks on a foundation item that hasn't landed. Work is paused or reverted.

**Mitigation:**
1. **Code-touch map (`92_code_touch_map.md`)** — documents §2 overlap hotspots and §3 per-phase file touches.
2. **Foundation-first discipline** — `99_CORPUS_COHERENCE_REVIEW.md §4.1` enumerates must-ship-first items. Foundation completes before any Tier 2 phase beyond C1.
3. **Pre-phase checklist** — before starting a phase, confirm its §6.3 production code dependencies are available.

**Escalation trigger:** a phase halts mid-implementation on a missing dependency. Re-sequence; complete dependency; resume.

### RP-2 — Balance tuning regresses during playtest iteration

**Category:** Process
**Probability:** High
**Impact:** Low (normal part of playtest)
**Phases affected:** All gameplay phases with tunable parameters

**Description:** Balance targets in Tier 2 docs are proposals. Playtest will show some are wrong. Iteration is expected.

**Mitigation:**
1. **Data-driven tuning** — balance values live in JSON (economy configs, combat stats, resolve thresholds, quality variance probabilities). Code changes not required to re-tune.
2. **Metrics tracking** — monitor session lengths, yields, session-completion rates. Playtest data drives tuning, not guesses.
3. **Per-phase tuning cycle** — after each phase ships, dedicated tuning pass informed by playtest.
4. **Accept that initial proposals are wrong** — Tier 2 doc numbers are starting points, not targets.

**Escalation trigger:** (this is normal operations, not escalation). Post-phase tuning pass is scheduled work, not reactive.

### RP-3 — Agent handoff context loss

**Category:** Process
**Probability:** Medium
**Impact:** Medium
**Phases affected:** Any phase spanning multiple agent sessions

**Description:** An agent session implementing a phase terminates; next session must pick up. Without careful context transfer, the next agent may re-invent approaches, deviate from established patterns, or miss nuance.

**Mitigation:**
1. **Memory system** — `MEMORY.md` + individual memory files capture project state.
2. **Coherence review + glossary + code-touch map** are entry points for new agent sessions.
3. **Per-phase handoff note** — when ending a session mid-phase, write a short handoff to memory capturing: what's done, what's next, open questions, tricky bits.
4. **Convention preservation** — established patterns (skill voice UI, journal surfaces, badge primitives) documented in UI Chrome §5.6/§5.7. New agents consume the canon.

**Escalation trigger:** new agent session produces code that deviates from established patterns. Review; correct; update memory with the mis-step + resolution.

### RP-4 — Design-reality divergence during implementation

**Category:** Process
**Probability:** High
**Impact:** Medium
**Phases affected:** All phases

**Description:** Implementation reveals design assumptions that don't match reality. A Tier 2 doc's claim may prove unworkable, over-scoped, or miscalibrated. The design must be revised; the question is how.

**Mitigation:**
1. **Design docs are living, not frozen** — per coherence review §9.5 (Governance), changes are welcome with revision-history tracking.
2. **Revision protocol** — when implementation needs a design change, update the Tier 2 doc first (adds revision-history entry), then proceed with the updated design.
3. **Don't implement past the doc** — if code deviates from doc, fix the doc or fix the code; no silent drift.

**Escalation trigger:** any phase ships with code differing from its doc without a documented revision. Either update doc or update code; resolve drift.

### RP-5 — Insufficient time for playtest-driven tuning

**Category:** Process
**Probability:** Medium
**Impact:** Medium
**Phases affected:** All gameplay phases

**Description:** Focus on shipping the next phase over tuning the previous one. Tunable systems (mining prestige curves, ground Resolve thresholds, quality variance probabilities) go un-tuned until release, then feel miscalibrated.

**Mitigation:**
1. **Tuning budget per phase** — each Tier 2 phase budgets ~20% overhead for post-implementation tuning.
2. **Playtester feedback loop** — episodes include explicit "tune this" questions for the just-shipped system.
3. **Gameplay metrics** — quantitative signals (session completion %, yield distributions) inform tuning even without explicit feedback.

**Escalation trigger:** phase ships without a tuning pass. Schedule tuning before next-phase work begins.

---

## 6. UX risks

### RU-1 — Tutorial / onboarding gaps for new mechanics

**Category:** UX
**Probability:** High
**Impact:** Medium
**Phases affected:** Mining M3 (Expedition Resolve... wait, this is Ground. Mining has prestige/Strata/thought cabinet), Salvage S3, Refining F3, Ground GR2

**Description:** Several Tier 2 docs introduce new mechanics without scoped tutorials: Expedition Resolve, party formation, thought cabinet internalizations, Quality Variance grades, module recovery cinematic, Wrecker Cycles. Players encounter these without contextual help.

**Mitigation:**
1. **Per-phase tutorial subsection** — each Tier 2 phase implementation includes a brief "first-time encountering this system" pass. Contextual hints, first-use tooltips, integrated dialogue.
2. **Reuse existing tutorial infrastructure** — `requirements/dialogue_flags`-based tutorial system from previous phases is already flexible. Hook new systems in.
3. **Pilot-test early** — new playtesters through the new system reveal onboarding gaps immediately.

**Escalation trigger:** playtest reveals players confused by a new mechanic. Author contextual hint; patch.

### RU-2 — UI chrome migration breaks view feel

**Category:** UX
**Probability:** Medium
**Impact:** Medium
**Phases affected:** All phases touching existing views

**Description:** Migrating existing views to canonical fonts, palette, badges, card primitives may subtly change how the view feels. "This used to look right" regression.

**Mitigation:**
1. **UI Chrome migration is incremental** — per-view, not all-at-once (UI Chrome §12.3).
2. **Playtest each migrated view** in isolation before proceeding to next.
3. **Before/after screenshot diff** — quick manual review identifies regressions.
4. **Revert window**: if a migration breaks feel, roll back; revisit after canonical primitives mature.

**Escalation trigger:** playtest feedback says a view "feels worse" after migration. Review what changed; tune or revert.

### RU-3 — Information density overwhelm (Trading, Galaxy)

**Category:** UX
**Probability:** Medium
**Impact:** Low
**Phases affected:** Trading T1-T3, Galaxy G4

**Description:** Trading's density boost (sparklines + depth bars + tier glyphs + volatility pips + faction affinity + permit stamps all on one row) could overwhelm casual players. Galaxy map's dominion overlay + landmarks + events + territory on regional zoom could obscure navigation.

**Mitigation:**
1. **Progressive disclosure** — novice players see core info (commodity name + price + trend); detail layers unlock with skill progression (remote_prices, trade_instinct, etc.).
2. **Hover-to-expand** — dense info requires hover for full detail; glance-level is simpler.
3. **Settings toggles** — option to hide event indicators, dominion overlay, trend arrows for players who want minimalism.
4. **Playtest with casuals** — information density testing separate from power-user testing.

**Escalation trigger:** playtest shows players unable to navigate / complete routine tasks. Reduce default density.

### RU-4 — Cinematic fatigue from unskippable sequences

**Category:** UX
**Probability:** Medium
**Impact:** Medium
**Phases affected:** Galaxy G2 (jump), Combat C5 (dual tech), Mining M2 (prestige), Salvage S5 (module recovery, cycle)

**Description:** First jump cinematic: cool. Fortieth: tedious. Same for dual tech, prestige, module recovery.

**Mitigation:**
1. **Skippable per-moment** — any key press abbreviates cinematic to ~0.3s fade.
2. **Configurable speed** — per Galaxy §4.1, player setting: Full / Fast / Minimal / Instant.
3. **Cinematic budget awareness** — don't over-trigger; dual-tech is a rare move, not every turn.
4. **Abbreviated repeat** — per-session, first cinematic is full; subsequent are abbreviated.

**Escalation trigger:** playtest feedback says cinematics are annoying. Audit trigger frequency; expose speed setting; default to Fast for repeats.

### RU-5 — Mini-game loop fatigue

**Category:** UX
**Probability:** Low (identity content mitigates)
**Impact:** Medium
**Phases affected:** Mining, Salvage, Refining as core loops

**Description:** Core clicker/idler loops (mining click cycles, refining recipe queues) might feel repetitive over long play. Narrative identity mitigates but doesn't eliminate.

**Mitigation:**
1. **Identity content provides pacing structure** — chapter arcs punctuate grind.
2. **Seasonal events** (Refining) provide temporal rhythm.
3. **Optional content tracks** offer variety within a system.
4. **Cross-identity play** — players who hit fatigue in one system can switch to another; all three are valid progression paths.
5. **Playtest session-length data** — monitor for fatigue indicators.

**Escalation trigger:** playtest session-length data shows declining play duration per system. Add variety content; evaluate identity arc pacing.

---

## 7. Top-5 concentration watch

The highest-priority risks concentrated here for sustained attention:

| Rank | Risk | P × I | Why top |
|---|---|---|---|
| 1 | **RC-1 — Voice drift across 107k words** | High × Medium | Content is the long pole; drift compounds |
| 2 | **RT-1 — ShipComposite performance regression** | Medium × High | Blocks 5 downstream consumers |
| 3 | **RT-5 — Cross-system API mismatches surface late** | Medium × High | Cascades into phase slips |
| 4 | **RT-7 — Framework §2 scope creep** | Medium × High | Blocks foundation completion |
| 5 | **RC-2 — Content authoring fatigue / timeline slip** | Medium × High | 107k words is marathon territory |

**Common theme:** the highest risks cluster around **foundation phases (engineering blockers)** and **content phases (authoring marathon)**. These are the two places implementation can slip most dramatically.

**Mitigation attention concentrates here:**
- Rigorous foundation API specs (SceneCamera done; ShipComposite next)
- Voice review discipline with pilot chapter calibration
- Time-boxed rebuild + content priority cuts

---

## 8. Escalation protocol

When a risk's escalation trigger activates:

### 8.1 Immediate (same day)

1. Note the risk identifier in §7 (bump its position / add annotation)
2. Apply the documented mitigation
3. Log the event with timestamp in a risk-log section (appended to §7 or separate file)

### 8.2 Reflection (within the phase)

1. Did the mitigation work?
2. Should the mitigation be refined?
3. Is the probability assessment still accurate?

### 8.3 Update (end of phase)

1. Update this register with lessons learned
2. If a risk's mitigation proved inadequate, refine
3. If a new risk surfaced, add it

### 8.4 Corpus-revision threshold

Some risks, if they materialize, may require a coherence review update or a Tier 2 doc revision. In that case:
- Update the relevant doc with a revision-history entry
- Note in `99_CORPUS_COHERENCE_REVIEW.md` under "Coherence edits applied"
- Update this risk register

---

## 9. Update process

This document is **living.** Update triggers:

- **New risk observed** during implementation → add entry
- **Risk materializes** → update §7 watchlist; apply escalation protocol
- **Risk mitigated / doesn't materialize after phase ships** → close entry or downgrade probability
- **Post-Combat C1** → comprehensive update based on first-phase experience

Next scheduled update: **after Combat Phase C1 completes.** Real implementation reveals which risks were real and which were speculative.

---

## 10. Risks explicitly NOT tracked

Out of scope for this register:

- **Launch-phase risks** (pricing, marketing, platform-specific) — not alpha concerns
- **External dependency risks** (pygame-ce library changes, Python version) — general project risks, not overhaul-specific
- **Team risks** (solo dev fatigue, project abandonment) — personal, not documented here
- **Scope decisions already made** (no multiplayer, no voice acting, no procedural narrative) — settled in Tier 2 docs

---

*Revision history:*
- *v1 — pre-implementation risk enumeration. 22 risks across 4 categories (7 technical, 5 content, 5 process, 5 UX). Top-5 watchlist identifies foundation + content as highest-risk concentration zones.*
