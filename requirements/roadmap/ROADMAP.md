# Aurelia Master Roadmap

**Updated**: 2026-04-26
**Format**: single file, per-sprint anchors. Each sprint is an `<h3>` section identified by stable ID. The dispatcher and agents reference sprints by anchor. See `CONVENTIONS.md` for sprint format and `AGENT_GUIDE.md` for agent workflow.

This is the active execution backlog for the multi-agent ralph loop. Sprints listed here are real, scopable work units. Strategic vision docs live elsewhere (`requirements/station_anchors.md`, `requirements/onboarding_design.md`, etc.) and are referenced in each sprint's `Context to read`.

---

## How to use this doc

- **Loop dispatcher**: parse the index table below to find sprints with `Status: todo`. Filter for those whose dependencies are all `done` and whose touch zones don't conflict with `in-progress` sprints. Hand a selected sprint to an agent by anchor (e.g., "execute the sprint at `ROADMAP.md#sa-1`").
- **Agent**: read your sprint's `<h3>` section and every doc/file in `Context to read`. Plan, implement TDD-style, validate, commit. Update your sprint's `Status` and `Activity log`. Do not touch any other sprint's section.
- **Human**: scan the index for arc-level progress. Move sprints from `review` to `done` after acceptance verification.

---

## Index

Status flow: `todo` → `in-progress` → `review` → `done`. Also: `blocked` (recoverable), `aborted` (terminal).

### SA Arc — Station Anchors (Phase 0 through Phase VI)

| ID | Title | Phase | Size | Status | Depends on |
|---|---|---|---|---|---|
| [SA-PREP-1](#sa-prep-1--npc-voice-sheet-audit) | NPC voice-sheet audit | 0 | M | todo | none |
| [SA-PREP-2](#sa-prep-2--existing-data-audit) | Existing-data audit | 0 | S | todo | none |
| [SA-PREP-3](#sa-prep-3--playtest-baseline-telemetry) | Playtest baseline telemetry | 0 | S | todo | none |
| [SA-A1](#sa-a1--crew-specialization-design) | Crew specialization design | A | S | todo | SA-PREP-2 |
| [SA-A2](#sa-a2--crew-template-implementation) | Crew template implementation | A | M | todo | SA-A1 |
| [SA-B-EXT-1](#sa-b-ext-1--sub-reputation-system) | Sub-reputation system | B | M | todo | none |
| [SA-C1](#sa-c1--skill-tree-extension-design) | Skill tree extension design | C | S | todo | SA-PREP-2 |
| [SA-C2](#sa-c2--skill-tree-extension-implementation) | Skill tree extension implementation | C | M | todo | SA-C1 |
| [SA-0](#sa-0--cluster-a-confirmation-pass) | Cluster A confirmation pass | I | S | todo | SA-PREP-2 |
| [SA-1](#sa-1--wreckers-guild-hall-salvage-contracts) | Wreckers' Guild Hall (Salvage Contracts) | I | L | todo | SA-PREP-1, SA-A2, SA-B-EXT-1 |
| [SA-2](#sa-2--deep-shafts-memorial--pilgrimage) | Deep Shafts memorial / pilgrimage | I | L | todo | SA-PREP-1 |
| [SA-V](#sa-v--cargo-broker-arc--investment-introduction) | Cargo Broker arc + investment introduction | I | M | todo | SA-PREP-1 |
| [SA-P1](#sa-p1--politics-system-design) | Politics System Design | II | M | todo | SA-PREP-1, SA-C2 |
| [SA-P2](#sa-p2--politics-core) | Politics Core | II | XL | todo | SA-P1, SA-A2, SA-C2, SA-B-EXT-1 |
| [SA-P3](#sa-p3--mayors-council-chamber-verdant-venue) | Mayors' Council Chamber (Verdant) | II | L | todo | SA-P2 |
| [SA-P4](#sa-p4--alliance-congress-hall-havens-rest-venue) | Alliance Congress Hall (Haven's Rest) | II | L | todo | SA-P2, SA-P3 |
| [SA-P5](#sa-p5--wreckers-guild-gray-market-mediation-venue) | Wreckers' Guild gray-market (Reach venue) | II | M | todo | SA-P2, SA-1 |
| [SA-P6](#sa-p6--politics-polish--tuning) | Politics polish + tuning | II | M | todo | SA-P3, SA-P4, SA-P5 |
| [SA-B1](#sa-b1--bidding-system-design) | Bidding System Design | III | M | todo | SA-PREP-1 |
| [SA-B2](#sa-b2--bidding-core) | Bidding Core | III | XL | todo | SA-B1, SA-A2, SA-C2 |
| [SA-B3](#sa-b3--stellaris-auction-house-primary-venue) | Stellaris Auction House (primary) | III | L | todo | SA-B2 |
| [SA-B4](#sa-b4--crimson-reach-black-market-auctions) | Crimson Reach Black Market | III | L | todo | SA-B2, SA-1 |
| [SA-B5](#sa-b5--player-initiated-auctions) | Player-Initiated Auctions | III | L | todo | SA-B2 |
| [SA-B6](#sa-b6--bidding-polish--tuning) | Bidding polish + tuning | III | M | todo | SA-B3, SA-B4, SA-B5 |
| [SA-R1](#sa-r1--okafor-institute-research-patronage) | Okafor Institute (Research Patronage) | IV | L | todo | SA-PREP-1, SA-C2 |
| [SA-R2](#sa-r2--dr-okafors-legacy-narrative-arc) | Dr. Okafor's Legacy Narrative Arc | IV | M | todo | SA-R1 |
| [SA-R3](#sa-r3--research-patronage-polish) | Research Patronage polish | IV | S | todo | SA-R1, SA-R2 |
| [SA-F1](#sa-f1--financial-exchange-design) | Financial Exchange Design | V | M | todo | SA-PREP-1, SA-C2, SA-V |
| [SA-F2](#sa-f2--futures-core) | Futures Core | V | XL | todo | SA-F1 |
| [SA-F3](#sa-f3--meridian-venue--cargo-broker-graduation) | Meridian Venue + Cargo Broker graduation | V | L | todo | SA-F2, SA-V |
| [SA-F4](#sa-f4--shipping-contracts-sub-system) | Shipping Contracts sub-system | V | L | todo | SA-F2 |
| [SA-F5](#sa-f5--insurance-sub-system) | Insurance sub-system | V | M | todo | SA-F2 |
| [SA-F6](#sa-f6--market-manipulation-threats) | Market Manipulation threats | V | M | todo | SA-F2, SA-F4 |
| [SA-F7](#sa-f7--financial-crisis-event-arc) | Financial Crisis Event Arc | V | L | todo | SA-F2, SA-F4, SA-F5, SA-F6 |
| [SA-X1](#sa-x1--cross-anchor-narrative-threading) | Cross-anchor narrative threading | VI | M | todo | (most Cluster B+C work done) |
| [SA-X2](#sa-x2--reputation-consistency-audit--rebalance) | Reputation consistency audit + rebalance | VI | M | todo | SA-1, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X3](#sa-x3--tutorial-integration) | Tutorial integration (per-anchor first-time tips) | VI | M | todo | SA-1, SA-2, SA-V, SA-P3, SA-B3, SA-R1, SA-F3 |
| [SA-X4](#sa-x4--journal-pass) | Journal pass | VI | S | todo | SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X5](#sa-x5--news-ticker-integration) | News ticker integration | VI | M | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X6](#sa-x6--crew-reactions--anchor-banter) | Crew reactions / anchor banter | VI | M | todo | SA-A2, SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X7](#sa-x7--achievement-pass) | Achievement pass | VI | S | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X8](#sa-x8--cross-anchor-mega-arc) | Cross-anchor mega-arc | VI | XL | todo | SA-P6, SA-B6, SA-F3 |
| [SA-X9](#sa-x9--audio--music-pass) | Audio + music pass | VI | M | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X10](#sa-x10--visual-identity-per-venue) | Visual identity per venue | VI | M | todo | SA-1, SA-P3, SA-B3, SA-R1, SA-F3 |

### Followups

| ID | Title | Source | Size | Status | Depends on |
|---|---|---|---|---|---|
| [CB-1](#cb-1--crew-banter-scope--scoping) | Crew Banter scope (scoping) | Living Universe Arc deferral | S | todo | none |
| [CB-2](#cb-2--crew-banter-implementation) | Crew Banter implementation | TBD via CB-1 | M | todo | CB-1 |
| [WB-1](#wb-1--station-tagline-scanner-coverage) | Station tagline scanner coverage | writing_bible_scanner_gaps.md | S | todo | none |
| [WB-2](#wb-2--parallel-negation-regex-broadening) | Parallel-negation regex broadening | writing_bible_scanner_gaps.md | S | todo | WB-1 |
| [SI3-FOLLOW-1](#si3-follow-1--no-arg-helper-introspection) | No-arg helper introspection (flag scanner) | SL-2 disclosure | S | todo | none |
| [UI-BOUNDS-1](#ui-bounds-1--station_hub_view-in-bounds-harness) | station_hub_view in subprocess bounds harness | SL-1 deferral | S | todo | none |

---

## SA Arc — Station Anchors

Strategic context: `requirements/station_anchors.md`. The arc upgrades the original SL-6 "unique content arc" placeholder into a 10-phase, ~38-52 week roadmap with full ambition intact (no playtest-cadence compression).

### Phase 0 — Pre-arc Preparation

#### SA-PREP-1 — NPC voice-sheet audit

**Status**: todo
**Phase**: Phase 0 — Pre-arc Preparation | **Size**: M | **Effort**: 1-2 weeks
**Depends on**: none | **Blocks**: SA-1, SA-2, SA-V, SA-P3, SA-P4, SA-P5, SA-B3, SA-B4, SA-R1, SA-F3

**Goal.** Catalog every named NPC the SA arc will touch. Confirm each has a 1-page voice sheet at the standards established by `requirements/character_voices.md`. Author missing sheets. Cross-reference for tonal consistency across the cast. The arc's cohesion ambition depends on every named character feeling like a real person — voice sheets are the foundation.

**Context to read.**
- `requirements/station_anchors.md`
- `requirements/character_voices.md`
- `requirements/cultural_guide.md`
- `requirements/dialogue_writing_guide.md` (Writing Bible)
- `data/dialogue/dialogues.json`
- `spacegame/constants/flags.py` (`met_npc(npc_id)` registry)

**Touch zones.**
- `requirements/character_voices.md`
- `requirements/character_voices/` (NEW if splitting per-character)

**Deliverables.**
- Inventory table: every named NPC the SA arc touches.
- For each: existing voice sheet (with consistency-pass edits) OR a new 1-page voice sheet.
- A "tonal map" identifying at least one distinguishing register feature per character.

**Acceptance criteria.**
1. Inventory covers Malia Torres, Marcus Jin, Dr. Okafor's successor, Cargo Broker, Verdant Mayor + 3 Verdant council delegates, 4 Alliance Congress delegates, Stellaris Auctioneer + 3 recurring rivals, Meridian primary broker, Deep Shafts miner caretaker, Wreckers' Guild secondary contacts (3).
2. Every character has a voice sheet at the Elena/Marcus/Priya/Tomas standard.
3. All sheets pass the Writing Bible scanner (no em-dashes, no banned phrases).
4. Tonal map is concrete: each character has at least one named distinguishing register feature.

**Risks / open questions.**
- Cargo Broker existing data: confirm whether the character is named in current dialogue trees.
- Whether to split per-character into a subdirectory or keep all sheets in one doc.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-PREP-2 — Existing-data audit

**Status**: todo
**Phase**: Phase 0 | **Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: SA-A1, SA-C1, SA-0

**Goal.** Walk current dialogue trees, ambient lines, news headlines, journal entries, missions to see what already references each anchor. Identify what we need to extend vs. preserve. Save state baseline for regression checks.

**Context to read.**
- `data/dialogue/dialogues.json`
- `data/missions/missions.json`, `side_missions.json`, `crew_quests.json`
- `data/galaxy/locations.json`
- `data/journal/*.json`
- `requirements/station_anchors.md`

**Touch zones.**
- `requirements/sa_audit_findings.md` (NEW)

**Deliverables.**
- A findings doc cataloging existing references per anchor.
- A regression checklist: behaviors that must continue to work after SA changes.

**Acceptance criteria.**
1. Every `unique`-typed location has a list of existing references (mission, dialogue, journal, ambient).
2. Regression checklist itemizes at least 5 distinct existing player-facing behaviors that SA must preserve.
3. Findings doc voice-checked.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-PREP-3 — Playtest baseline telemetry

**Status**: todo
**Phase**: Phase 0 | **Size**: S | **Effort**: 2-3 days
**Depends on**: none | **Blocks**: (informational only — does not block subsequent sprints)

**Goal.** Capture pre-arc telemetry for post-arc comparison. Measures of "what players do today" with `unique` cards: how often each is clicked, time spent, mission acceptance patterns at each station. Comparison data for evaluating whether the SA arc moved player behavior in intended directions.

**Context to read.**
- Existing analytics or logging infrastructure (audit during planning).
- `requirements/station_anchors.md` acceptance criteria.

**Touch zones.**
- `requirements/sa_baseline.md` (NEW — captured snapshot)
- `spacegame/utils/logger.py` (potential telemetry hooks)

**Deliverables.**
- A captured baseline of current behavior per anchor (where measurable).
- Documentation of what's measurable vs. what isn't.

**Acceptance criteria.**
1. Baseline document committed.
2. At least 3 measurable behaviors captured per anchor (or noted as unmeasurable with reason).

**Activity log.**
- 2026-04-26 — todo (created)

### Phase A — Crew Specialization Extension

#### SA-A1 — Crew specialization design

**Status**: todo
**Phase**: Phase A | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: SA-A2

**Goal.** Identify which crew templates need new specializations to support SA systems (Negotiator for Bidding, Mediator/Coalition Builder for Politics, Speculator for Financial, Patron for Research). Decide whether to add new templates or extend existing.

**Context to read.**
- `data/crew/*.json` (existing templates)
- `spacegame/models/crew.py`
- `requirements/station_anchors.md`
- `requirements/sa_audit_findings.md` (from SA-PREP-2)

**Touch zones.**
- `requirements/sa_crew_design.md` (NEW)

**Deliverables.**
- Design doc covering: which specializations to add, whether new templates or extensions to existing, bonus ranges, how the bonus integrates with anchor mechanics.

**Acceptance criteria.**
1. Each new specialization has a defined bonus type and bonus magnitude range.
2. Each specialization names at least one anchor system it integrates with.
3. Decision locked on extension vs. new templates.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-A2 — Crew template implementation

**Status**: todo
**Phase**: Phase A | **Size**: M | **Effort**: 5-7 days
**Depends on**: SA-A1 | **Blocks**: SA-1, SA-P2, SA-B2, SA-X6

**Goal.** Implement the crew specializations designed in SA-A1. Add new specialist crew template entries (or extend existing). Wire bonuses through `progression.get_bonus()`. Author voice sheets and ambient banter for new specialist crew members.

**Context to read.**
- `requirements/sa_crew_design.md`
- `spacegame/models/crew.py`
- `data/crew/*.json`
- `requirements/character_voices.md`

**Touch zones.**
- `data/crew/*.json` (modify or extend)
- `spacegame/models/crew.py`
- `tests/test_models/test_crew.py`
- `requirements/character_voices.md` (new specialist sheets)

**Deliverables.**
- Crew templates updated/added per SA-A1 design.
- Bonus integration tested.
- Voice sheets for any net-new specialist characters.
- Ambient banter samples (3-5 lines per specialist).

**Acceptance criteria.**
1. Each new specialization is selectable when hiring crew.
2. Bonuses apply correctly (verified via skill-bonus integration tests).
3. Save/load round-trips crew with new specializations.
4. Writing Bible scanner clear on all new banter lines.
5. Full test suite green.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase B — Sub-Reputation System Extension

#### SA-B-EXT-1 — Sub-reputation system

**Status**: todo
**Phase**: Phase B | **Size**: M | **Effort**: 5-7 days
**Depends on**: none | **Blocks**: SA-1, SA-B3, SA-B4

**Goal.** Extend the reputation model to support per-organization standing layered under per-faction standing. Wreckers' Guild membership tier (apprentice/journeyman/master) is independent of Crimson Reach faction reputation. Stellaris Auctioneer relationship is independent of Stellaris Port faction reputation. Establishes the pattern for SA-1 and SA-B3/B4 to consume.

**Context to read.**
- `spacegame/models/player.py` (`faction_reputation`)
- `spacegame/save_manager.py`
- `requirements/station_anchors.md`

**Touch zones.**
- `spacegame/models/sub_reputation.py` (NEW)
- `spacegame/models/player.py` (add `sub_reputation` field)
- `spacegame/save_manager.py` (round-trip)
- `tests/test_models/test_sub_reputation.py` (NEW)

**Deliverables.**
- New `SubReputation` model encoding per-organization standing with named tiers.
- Player gains `sub_reputation: dict[str, int]` field with `to_dict`/`from_dict`.
- Save migration: existing saves load with empty sub_reputation.
- Tests covering tier promotion, tier-based gates, save/load.

**Acceptance criteria.**
1. Player can have non-zero sub_reputation in one organization without affecting any other organization or any faction reputation.
2. Tier thresholds are configurable per organization.
3. Save/load round-trip clean across game sessions.
4. Existing saves load without crash; sub_reputation defaults to empty.
5. Tests cover at least 3 organizations with different tier structures.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase C — Skill Tree Extensions

#### SA-C1 — Skill tree extension design

**Status**: todo
**Phase**: Phase C | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: SA-C2

**Goal.** Identify which new skills the SA arc needs. Candidates: Negotiator (Bidding), Mediator (Politics neutral arbiter), Speculator (Financial), Patron (Research), Coalition Builder (Politics advocate). Decide whether to extend the Social and Commerce trees or add a new tree. Confirm bonus types and magnitude ranges.

**Context to read.**
- `spacegame/models/progression.py` (`create_default_skills`)
- Memory: 6 trees / 75 skills / no JSON / 1 point per level
- `requirements/station_anchors.md`

**Touch zones.**
- `requirements/sa_skill_design.md` (NEW)

**Deliverables.**
- Design doc covering: new skills, tree assignment (extension vs. new tree), bonus types, magnitude ranges, prerequisites, capstone implications.

**Acceptance criteria.**
1. Each new skill has named bonus_type and magnitude range.
2. Tree assignment locked.
3. Prerequisites and tier locked.
4. Recommendation: extend existing trees rather than add new.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-C2 — Skill tree extension implementation

**Status**: todo
**Phase**: Phase C | **Size**: M | **Effort**: 5-7 days
**Depends on**: SA-C1 | **Blocks**: SA-P1, SA-P2, SA-B2, SA-F1, SA-R1

**Goal.** Add the new SA skills per SA-C1's design. Wire bonuses through `progression.get_bonus()`. Update the skill tree view if the new skills require visual treatment.

**Context to read.**
- `requirements/sa_skill_design.md`
- `spacegame/models/progression.py`
- `spacegame/views/skill_tree_view.py`
- `tests/test_models/test_progression.py`

**Touch zones.**
- `spacegame/models/progression.py`
- `spacegame/views/skill_tree_view.py`
- `tests/test_models/test_progression.py`

**Deliverables.**
- New skills present in `create_default_skills()`.
- Bonus types accessible via `get_bonus(...)`.
- Skill tree view renders the new skills correctly at all 6 tested resolutions.
- Tests for bonus integration + skill tree rendering.

**Acceptance criteria.**
1. Each new skill is unlockable, leveled, and grants its bonus correctly.
2. Save/load round-trips ranks in new skills.
3. Skill tree view layout doesn't regress at any resolution.
4. Full test suite green.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase I — Cluster B Anchors

#### SA-0 — Cluster A confirmation pass

**Status**: todo
**Phase**: Phase I | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: none

**Goal.** Confirm Restricted Sector 7, Restricted Research Wing, Assembly Core surface correctly during their existing campaign beats post-SL-1 demotion. Author the optional depth tier for between-campaign-beat visits (intelligence opportunities at restricted sectors, espionage flavor).

**Context to read.**
- `requirements/station_legibility.md` (SL-1 conditional demotion rule)
- `data/galaxy/locations.json` (Cluster A entries)
- `data/missions/missions.json` (campaign endpoints)
- `requirements/sa_audit_findings.md`

**Touch zones.**
- `data/dialogue/dialogues.json` (depth-tier dialogues)
- `tests/test_scenarios/test_scenario_cluster_a_anchors.py` (NEW)

**Deliverables.**
- Confirmation that SL-1's mission-objective elevation works for the 3 Cluster A anchors during their campaign beats.
- Optional depth-tier content (intelligence-gathering dialogue) for between-campaign visits.
- Scenario tests covering the campaign-elevation path.

**Acceptance criteria.**
1. Each Cluster A anchor stays in the action grid during its campaign mission, demoted otherwise.
2. Between-campaign visits offer 1-2 depth-tier dialogue beats per anchor.
3. Scenario tests pass for both elevation states.
4. Writing Bible clear on new dialogue.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-1 — Wreckers' Guild Hall (Salvage Contracts)

**Status**: todo
**Phase**: Phase I | **Size**: L | **Effort**: 2-3 weeks
**Depends on**: SA-PREP-1, SA-A2, SA-B-EXT-1 | **Blocks**: SA-P5, SA-B4

**Goal.** Convert the Wreckers' Guild Hall `unique` location at Crimson Reach into a working Salvage Contracts hub. Players take contracts mediated by Malia Torres targeting derelict sites. Reuses existing salvage gameplay end-to-end. Adds Wreckers' Guild membership tier (apprentice / journeyman / master) separate from Crimson Reach faction reputation. Multiple recurring NPC contacts develop relationships with the player over time.

**Context to read.**
- `requirements/station_anchors.md` (Phase I, Cluster B)
- `requirements/character_voices.md` (Malia Torres + Wreckers secondary contacts, post-SA-PREP-1)
- `data/galaxy/locations.json` (`crimson_wreckers_guild`)
- `spacegame/views/station_hub_view.py`
- `spacegame/views/salvaging_view.py`
- `spacegame/models/mission.py`
- `spacegame/models/sub_reputation.py` (post-SA-B-EXT-1)
- `spacegame/constants/flags.py`

**Touch zones.**
- `spacegame/views/wreckers_guild_view.py` (NEW)
- `spacegame/models/wreckers_guild.py` (NEW)
- `spacegame/models/player.py` (wreckers_guild_state field)
- `spacegame/save_manager.py`
- `spacegame/constants/flags.py`
- `spacegame/engine/game.py`
- `spacegame/config.py` (GameState enum)
- `data/missions/wreckers_contracts.json` (NEW)
- `data/dialogue/dialogues.json` (Malia + secondary contacts)
- `tests/test_models/test_wreckers_guild.py` (NEW)
- `tests/test_views/test_wreckers_guild_view.py` (NEW)
- `tests/test_scenarios/test_scenario_wreckers_arc.py` (NEW)

**Deliverables.**
- Wreckers' Guild view with contract board (3-5 active offers, refreshes on cadence).
- Membership tier model (apprentice/journeyman/master) with promotion thresholds and lockout rules.
- 5-7 contract templates across tiers (cleanup, recovery, escort-salvage, deep-derelict).
- Malia Torres expanded dialogue tree + 2-3 secondary Wreckers (wreck navigator, salvage engineer, debris-field cartographer).
- Save/load support.
- Tests at model, view, and scenario layers.

**Acceptance criteria.**
1. Player docks at Crimson Reach, clicks the Wreckers' Guild Hall card, enters new view.
2. Contract board filters by membership tier.
3. Accepting → mission created. Completing returns to Wreckers' Guild Hall with payout + standing increase.
4. Failing applies lockout rule with make-up dialogue path.
5. Promotion auto-triggers at thresholds; new tiers unlock content.
6. Malia voice sheet satisfied across all dialogue beats.
7. Save/load clean. Existing saves load with default state (unjoined).
8. Full suite green; SI-3 + Writing Bible scanners clear.

**Risks / open questions.**
- Default state for existing saves: unjoined vs. apprentice. Recommendation: unjoined; first conversation enrolls.
- Contract refresh cadence: visit-triggered with cooldown. Lockable in planning.
- Existing salvage system: support for per-contract objectives? May require small extension.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-2 — Deep Shafts memorial / pilgrimage

**Status**: todo
**Phase**: Phase I | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-PREP-1 | **Blocks**: SA-X1, SA-X4, SA-X6

**Goal.** Convert The Deep Shafts at Breakstone into a memorial venue with a Sora Takahashi historical narrative arc, Marcus Jin tie-in (player's father connection), pilgrimage mechanics (reputation grant, ongoing miner's-blessing returns), and a sacred-ground rule.

**Context to read.**
- `requirements/station_anchors.md` (SA-2)
- `requirements/character_voices.md` (Marcus Jin, Old Sten miner caretaker)
- `requirements/cultural_guide.md` (Sora Takahashi historical context)
- `requirements/act_one_reference.md` (Marcus arc integration)
- `requirements/first_session_pacing.md` (Marcus revelation moment)
- `data/galaxy/locations.json` (`breakstone_deep_mines`)
- `data/journal/*.json`

**Touch zones.**
- `spacegame/views/deep_shafts_view.py` (NEW)
- `spacegame/views/station_hub_view.py` (route the unique-click)
- `spacegame/engine/game.py` (state transition)
- `spacegame/config.py` (GameState enum)
- `data/dialogue/dialogues.json` (Marcus expanded + Old Sten)
- `data/journal/*.json` (Sora Takahashi multi-entry arc)
- `data/missions/missions.json` (Act One/Act Two beats)
- `tests/test_views/test_deep_shafts_view.py` (NEW)
- `tests/test_scenarios/test_scenario_deep_shafts.py` (NEW)

**Deliverables.**
- Deep Shafts view with first-visit scripted scene (sound + atmospheric beat).
- Multi-entry Sora Takahashi historical journal arc.
- Marcus Jin dialogue tree extension (player's father connection, gated by progression).
- Old Sten miner caretaker NPC (named, voice-sheet, recurring).
- Sacred-ground rule (combat/violence forbidden, NPC reactions).
- Union reputation grant on first visit.
- Periodic miner's-blessing reputation tick.
- Mission tie-ins: Act One and Act Two beats.
- Long-running thread: Uprising-echoes references in NPC dialogue across the game.

**Acceptance criteria.**
1. First visit triggers scripted scene exactly once per save.
2. Sora Takahashi journal arc unlocks across multiple visits at game-day cadence.
3. Marcus Jin Act One beat triggers correctly.
4. Sacred-ground rule enforced (combat blocked at Deep Shafts; NPC reactions if attempted).
5. Voice sheet for Old Sten satisfied; Writing Bible clear.
6. Save/load preserves all progression.
7. Full suite green.

**Risks / open questions.**
- Existing campaign Act One Marcus arc: extend existing dialogue or branch new tree? Read campaign reference first.
- Sacred-ground enforcement mechanics: how does the system block combat? Integrate with existing politics_manager or create new?

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-V — Cargo Broker arc + Investment Introduction

**Status**: todo
**Phase**: Phase I | **Size**: M | **Effort**: 1.5 weeks
**Depends on**: SA-PREP-1 | **Blocks**: SA-F3 (Meridian + Cargo Broker graduation)

**Goal.** Author the Cargo Broker as a recurring named character with full voice sheet (per onboarding_design.md secondary-teacher slot). Player meets them at multiple cantinas. Mission introduces investment and sets `investment_introduced` flag. Sets up the SA-F3 graduation arc to Meridian.

**Context to read.**
- `requirements/onboarding_design.md` (Cargo Broker recommendation)
- `requirements/character_voices.md` (Cargo Broker voice sheet, post-SA-PREP-1)
- `requirements/station_legibility.md` (SL-2b context, investment gating)
- `spacegame/constants/flags.py` (`investment_introduced`)
- `data/missions/missions.json`, `side_missions.json`
- `data/dialogue/dialogues.json`

**Touch zones.**
- `data/missions/sa_v_investment_intro.json` (NEW or fold into side_missions.json)
- `data/dialogue/dialogues.json` (Cargo Broker dialogue trees: introduction, ongoing, graduation pointer)
- `data/galaxy/npcs.json` (NEW Cargo Broker entry if needed)
- `spacegame/data_loader.py` (if NPC structure changes)
- `tests/test_scenarios/test_scenario_sa_v_investment_intro.py` (NEW)

**Deliverables.**
- Cargo Broker NPC with voice sheet, character history, signature dialogue.
- Investment-introduction mission: Cargo Broker offers it, player completes, flag set.
- 3 dialogue trees (introduction, ongoing, graduation pointer to Meridian).
- The Cargo Broker appears at multiple cantinas (Nexus Prime + 2-3 others).
- Scenario test covering the introduction → flag-set → SA-2-style unlocked-cards flow.

**Acceptance criteria.**
1. Cargo Broker is encounterable at the designated cantinas.
2. The introduction mission can be accepted, completed, and sets `investment_introduced`.
3. Post-mission, investment cards appear at all 10 systems with investment per SL-2 acceptance.
4. Writing Bible clear; Cargo Broker voice consistent.
5. SI-3 flag scanner: `investment_introduced` is now producer-detected (was producer-only orphan via doc); update `KNOWN_PRODUCER_ONLY_ORPHANS` if needed.
6. Scenario test passes.

**Risks / open questions.**
- Cargo Broker existing data: does the character already exist named in current dialogue? SA-PREP-1 answers this.
- Mission acceptance flow: chained from existing missions, or fully standalone?

**Activity log.**
- 2026-04-26 — todo (created)

### Phase II — Politics System

#### SA-P1 — Politics System Design

**Status**: todo
**Phase**: Phase II | **Size**: M | **Effort**: 1 week
**Depends on**: SA-PREP-1, SA-C2 | **Blocks**: SA-P2

**Goal.** Design doc + paper prototyping for the Politics system. Locks the dispute lifecycle, AI delegate behavior model, player input model (vote/argue/mediate/abstain/coalition-build), argument-construction submechanic, integration points, all before code starts.

**Context to read.**
- `requirements/station_anchors.md` (Phase II)
- `requirements/character_voices.md` (delegate register)
- `requirements/sa_skill_design.md` (Mediator, Coalition Builder)
- `spacegame/models/social.py` (existing skill-check primitives)
- `spacegame/models/politics.py` (existing politics manager if any)

**Touch zones.**
- `requirements/sa_politics_design.md` (NEW)

**Deliverables.**
- Design doc covering: dispute lifecycle, dispute templates and variations, AI delegate behavior model with persuasion vectors, player input model, argument-construction submechanic specifics, integration points, UI flow sketch.
- Locked decisions on: round structure, partial-win mechanics, time pressure model, save/load granularity.

**Acceptance criteria.**
1. Doc covers all five player input modes with concrete mechanics.
2. Argument-construction submechanic fully specified (no "TBD" load-bearing pieces).
3. Integration commitments named for: reputation, market, missions, skill tree, crew, news.
4. Decisions list exhaustive — anything left ambiguous becomes a Risk in SA-P2.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-P2 — Politics Core

**Status**: todo
**Phase**: Phase II | **Size**: XL | **Effort**: 2 weeks
**Depends on**: SA-P1, SA-A2, SA-C2, SA-B-EXT-1 | **Blocks**: SA-P3, SA-P4, SA-P5

**Goal.** Implement the Politics system core mechanic: dispute representation, player choice flow, argument-construction submechanic, AI delegate behavior, multi-skill-check resolution, outcome propagation. Venue-agnostic engine.

**Context to read.**
- `requirements/sa_politics_design.md`
- `spacegame/models/social.py`
- `spacegame/models/progression.py`
- `spacegame/views/base_view.py`
- `spacegame/save_manager.py`

**Touch zones.**
- `spacegame/models/politics_dispute.py` (NEW)
- `spacegame/models/politics_delegate.py` (NEW)
- `spacegame/models/politics_argument.py` (NEW)
- `spacegame/models/politics.py` (extend or create)
- `spacegame/models/player.py` (politics_state field)
- `spacegame/save_manager.py`
- `spacegame/views/dispute_view.py` (NEW)
- `spacegame/engine/game.py`
- `spacegame/config.py` (GameState.DISPUTE)
- `spacegame/constants/flags.py` (politics outcome flags)
- `tests/test_models/test_politics_dispute.py` (NEW)
- `tests/test_models/test_politics_delegate.py` (NEW)
- `tests/test_models/test_politics_argument.py` (NEW)
- `tests/test_views/test_dispute_view.py` (NEW)
- `tests/test_scenarios/test_scenario_politics_loop.py` (NEW)

**Deliverables.**
- Dispute, Delegate, Argument data models.
- Argument-construction submechanic.
- Multi-round structure.
- Outcome resolution that emits faction-rep deltas, market shifts, mission unlocks, news events.
- Dispute view venue UI.
- Save/load support for in-progress disputes.
- Synthetic-fixture tests at model + view + scenario layers.

**Acceptance criteria.**
1. Synthetic test dispute can run through every input path (vote/argue/mediate/abstain/coalition-build).
2. Argument-construction applies skill weighting per SA-P1 design (verifiable).
3. Delegate updates deterministic given same inputs (no resolution-stage randomness).
4. Partial-win outcomes work.
5. Outcome propagation: faction-rep deltas, market shifts, news events all fire in tests.
6. Save/load round-trips an in-progress dispute at any round boundary.
7. Coalition-building measurably improves starting positions vs. control.
8. 30-50+ new tests.
9. Full suite green; lint + format clean.

**Risks / open questions.**
- Argument-construction load-bearing: if SA-P1 left this ambiguous, this sprint blocks back.
- Existing politics_manager scope: extend or replace? Audit during planning.
- Performance: argument resolution <100ms; UI 60 FPS.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-P3 — Mayors' Council Chamber (Verdant Venue)

**Status**: todo
**Phase**: Phase II | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-P2 | **Blocks**: SA-P4, SA-P6

**Goal.** First Politics venue. 8-12 dispute templates focused on Verdant local issues (settler-vs-farmer trade, modernization debate, water-rights, hydroponics-co-op). Multiple named delegates with developed voices. Multi-session arcs. Outcomes feed market and faction rep.

**Context to read.**
- `requirements/sa_politics_design.md`
- `requirements/character_voices.md` (Verdant Mayor + delegates, post-SA-PREP-1)
- `requirements/station_anchors.md` (SA-P3)
- `data/galaxy/locations.json` (`verdant_mayors_council`)

**Touch zones.**
- `data/politics/verdant_disputes.json` (NEW)
- `data/dialogue/dialogues.json` (Mayor + delegates)
- `data/galaxy/npcs.json` (delegate NPC entries)
- `spacegame/views/dispute_view.py` (Verdant-themed presentation)
- `tests/test_scenarios/test_scenario_verdant_politics.py` (NEW)

**Deliverables.**
- 8-12 dispute templates.
- Mayor character + 3-5 named delegates with voice sheets, dialogue trees.
- Verdant-themed venue rendering.
- Tutorial integration for first dispute (uses PT-M FirstTimeTipOverlay).
- Multi-session arcs for at least 2 disputes (campaign-style storyline).
- Scenario tests for full dispute loop in Verdant context.

**Acceptance criteria.**
1. Player docks at Verdant, clicks Mayors' Council card, enters dispute view.
2. Initial dispute populated from templates with rotation between visits.
3. All 8-12 templates pass dispute view rendering tests.
4. Multi-session disputes correctly persist between sessions.
5. Outcomes shift Verdant market for documented duration.
6. Delegate voices distinct per Writing Bible scanner.
7. Tutorial fires on first dispute, never re-fires.
8. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-P4 — Alliance Congress Hall (Haven's Rest Venue)

**Status**: todo
**Phase**: Phase II | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-P2, SA-P3 | **Blocks**: SA-P6

**Goal.** Second Politics venue. 6-10 inter-settlement issue templates. Annual Congress event (scheduled, multi-session arcs with campaigning sessions before the vote). Coalition-building gameplay. Major-vote outcomes ripple through Alliance-wide reputation, mission unlocks, economic conditions.

**Context to read.**
- `requirements/sa_politics_design.md`
- `requirements/character_voices.md` (Alliance delegates, post-SA-PREP-1)
- `requirements/station_anchors.md` (SA-P4)
- SA-P3 implementation (for venue patterns)

**Touch zones.**
- `data/politics/alliance_issues.json` (NEW)
- `data/dialogue/dialogues.json` (Alliance delegates)
- `data/galaxy/npcs.json`
- `spacegame/models/politics.py` (annual Congress scheduling)
- `spacegame/views/dispute_view.py` (Haven's-Rest-themed presentation)
- `tests/test_scenarios/test_scenario_alliance_congress.py` (NEW)

**Deliverables.**
- 6-10 issue templates spanning trade, defense, settlement modernization, Crimson Reach response.
- Named representatives from each Alliance settlement.
- Annual Congress event scheduling (once per game-month or game-quarter).
- Multi-session campaigning arc: pre-vote sessions visit delegates with favors and reputation.
- Coalition-building integration measurably improves outcomes.
- Possibility of betrayal/double-cross by coalition members.
- Scenario tests for Congress arc start-to-finish.

**Acceptance criteria.**
1. Annual Congress fires on schedule.
2. Player can pre-visit delegates and see effect on starting positions.
3. Delegate betrayal mechanic exercised in tests.
4. Major-vote outcomes ripple through Alliance reputation across multiple systems.
5. Cross-venue interaction with SA-P3: same-issue voting between venues considers prior outcomes.
6. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-P5 — Wreckers' Guild gray-market mediation venue

**Status**: todo
**Phase**: Phase II | **Size**: M | **Effort**: 1 week
**Depends on**: SA-P2, SA-1 | **Blocks**: SA-P6

**Goal.** Third Politics venue. Crimson Reach gray-market dispute mediation, salvage-rights conflicts, Malia Torres arbitrating. Demonstrates system reusability across factions. Reach-specific issue templates. Wreckers' Guild membership tier (from SA-1) gates delegate access.

**Context to read.**
- `requirements/sa_politics_design.md`
- SA-1 implementation (Wreckers' Guild membership)
- `requirements/character_voices.md` (Malia Torres)

**Touch zones.**
- `data/politics/reach_disputes.json` (NEW)
- `data/dialogue/dialogues.json` (Malia Torres dispute mediation tree)
- `spacegame/views/dispute_view.py` (Reach-themed presentation, dim-by-default consistent with `ReachDarkLayout`)
- `tests/test_scenarios/test_scenario_reach_mediation.py` (NEW)

**Deliverables.**
- 3-5 Reach-specific dispute templates (salvage-rights conflicts, Wreckers vs. unaffiliated salvagers, debris-field territory).
- Reach-themed dispute view styling.
- Membership-tier gating for participation.
- Malia Torres mediator dialogue tree.
- Scenario tests.

**Acceptance criteria.**
1. Apprentice-tier members can observe but not arbitrate; journeyman + can participate; master can lead mediation.
2. Reach disputes visually distinct (dim-by-default per ReachDarkLayout register).
3. Outcomes connect with Wreckers' Guild standing AND Crimson Reach reputation independently.
4. Writing Bible clear on Malia's mediator voice.
5. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-P6 — Politics polish + tuning

**Status**: todo
**Phase**: Phase II | **Size**: M | **Effort**: 1 week
**Depends on**: SA-P3, SA-P4, SA-P5 | **Blocks**: SA-X1, SA-X2, SA-X4, SA-X5, SA-X6, SA-X7, SA-X8, SA-X9

**Goal.** Polish pass on the full Politics system across all three venues. Pacing tuning, skill-check balance calibration, narrative texture review, accessibility, tutorial-flow refinement.

**Context to read.**
- All SA-P1 through SA-P5 deliverables.
- `requirements/ui_design_standards.md`
- Full politics-related test suite.

**Touch zones.**
- `data/politics/*.json` (rebalancing)
- `spacegame/models/politics_*.py` (tuning)
- `spacegame/views/dispute_view.py` (UX refinement)

**Deliverables.**
- Tuning report: changes made and why.
- Updated dispute templates with playtest-informed pacing.
- Accessibility audit results addressed.
- Tutorial fires correctly on first encounter at each venue.

**Acceptance criteria.**
1. Average dispute resolution time within target range (defined in SA-P1 design doc).
2. Skill-check pass rates balanced across venues for similarly-skilled players.
3. UI complies with `ui_design_standards.md`.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase III — Bidding System

#### SA-B1 — Bidding System Design

**Status**: todo
**Phase**: Phase III | **Size**: M | **Effort**: 1 week
**Depends on**: SA-PREP-1 | **Blocks**: SA-B2

**Goal.** Design doc + prototyping for the Bidding system. Locks lot generation rules, AI bidder behavior with multiple personas, bid round structure, time pressure, faction-restricted lots, recurring rival design.

**Context to read.**
- `requirements/station_anchors.md` (Phase III)
- `requirements/character_voices.md` (Auctioneer + rivals, post-SA-PREP-1)
- `spacegame/models/captain_memory.py` (recurring rival pattern)
- `data/galaxy/modules.json` (legendary modules — auction lot candidates)

**Touch zones.**
- `requirements/sa_bidding_design.md` (NEW)

**Deliverables.**
- Design doc covering: lot generation, AI bidder personas (collectors, speculators, faction agents, rival captains), value functions and hidden ceilings, round structure (decision: ascending/sealed/dutch), time pressure with adjustable speed, faction-restricted lot tiers.
- Locked decisions on: round format (recommendation: ascending), AI persona count (4-5), reserve-price mechanics.

**Acceptance criteria.**
1. AI bidder personas concretely specified with named value-function shapes.
2. Lot generation algorithm specified — what makes a lot for the auction tonight.
3. Decisions locked.
4. Doc voice-checked.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-B2 — Bidding Core

**Status**: todo
**Phase**: Phase III | **Size**: XL | **Effort**: 2 weeks
**Depends on**: SA-B1, SA-A2, SA-C2 | **Blocks**: SA-B3, SA-B4, SA-B5

**Goal.** Implement the Bidding system core: bid submission, AI counter-bid logic with multiple personas, round structure, live time-pressure UI, lot reveal/sale flow, win/loss outcomes. Venue-agnostic engine.

**Context to read.**
- `requirements/sa_bidding_design.md`
- `spacegame/models/captain_memory.py`
- `spacegame/views/base_view.py`

**Touch zones.**
- `spacegame/models/bidding_lot.py` (NEW)
- `spacegame/models/bidding_persona.py` (NEW)
- `spacegame/models/bidding_round.py` (NEW)
- `spacegame/models/bidding.py` (auction state)
- `spacegame/models/player.py` (bidding_history field)
- `spacegame/save_manager.py`
- `spacegame/views/auction_view.py` (NEW)
- `spacegame/engine/game.py`
- `spacegame/config.py` (GameState.AUCTION)
- `tests/test_models/test_bidding_*.py` (NEW)
- `tests/test_views/test_auction_view.py` (NEW)
- `tests/test_scenarios/test_scenario_auction_loop.py` (NEW)

**Deliverables.**
- Bidding data models (lot, persona, round, auction state).
- AI bidder personas with hidden value functions and ceilings.
- Round flow logic (ascending bid model per SA-B1 decision).
- Live time-pressure UI with adjustable speed.
- Lot reveal/sale flow with dramatic UI moments.
- Win/loss outcome propagation.
- 30+ tests across model, view, scenario layers.

**Acceptance criteria.**
1. Synthetic auction with 3+ AI personas runs from open to close cleanly.
2. Different player strategies (snipe, steady, aggressive) produce different outcomes.
3. AI ceilings hidden but consistent (a persona never bids past their value function).
4. Time pressure UI doesn't cause input lag.
5. Save/load preserves auction state mid-round.
6. Player loss propagates to Captain Memory if rival was involved.
7. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-B3 — Stellaris Auction House (primary venue)

**Status**: todo
**Phase**: Phase III | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-B2 | **Blocks**: SA-B6

**Goal.** Primary Bidding venue. Auctioneer NPC. Scheduled auctions every 5-7 game-days with seasonal headliner events. 6-8 lot categories. 3-5 recurring rival bidders integrated with Captain Memory. Pre-auction preview period. Post-auction social moments.

**Context to read.**
- `requirements/sa_bidding_design.md`
- SA-B2 implementation
- `requirements/character_voices.md` (Auctioneer + rivals)

**Touch zones.**
- `data/auctions/stellaris_lots.json` (NEW — lot pool)
- `data/dialogue/dialogues.json` (Auctioneer + rivals)
- `data/galaxy/npcs.json` (rival bidder NPCs)
- `spacegame/models/bidding.py` (Stellaris venue logic)
- `spacegame/views/auction_view.py` (Stellaris-themed)
- `tests/test_scenarios/test_scenario_stellaris_auction.py` (NEW)

**Deliverables.**
- 6-8 lot categories: legendary modules, art, faction-restricted commodities, rare upgrades, antiquities, derelict-recovery rights, smuggled goods, faction-perk-equivalent unlocks.
- Auctioneer NPC with full voice sheet.
- 3-5 recurring rival bidders with backstories, distinct value functions, Captain Memory integration.
- Auction scheduling (5-7 game-day cadence, seasonal headliners).
- Pre-auction preview UI; post-auction social UI.
- Reputation gating: Stellaris Port standing controls lot tier access.

**Acceptance criteria.**
1. Auctions fire on schedule with appropriate lots for player rep tier.
2. Lot pool refreshes between auctions.
3. Recurring rivals remember outcomes (Captain Memory).
4. Voice sheets satisfied; Writing Bible clear.
5. Headliner events differ measurably from regular auctions.
6. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-B4 — Crimson Reach Black Market auctions

**Status**: todo
**Phase**: Phase III | **Size**: L | **Effort**: 1.5 weeks
**Depends on**: SA-B2, SA-1 | **Blocks**: SA-B6

**Goal.** Second Bidding venue. Different rules from Stellaris: faction-restricted goods only, reputation/legality consequences, no-questions-asked culture. Wreckers' Guild membership gates access tiers.

**Context to read.**
- `requirements/sa_bidding_design.md`
- SA-1 (Wreckers' Guild membership system)
- `data/galaxy/locations.json` (`crimson_market` and Reach context)

**Touch zones.**
- `data/auctions/reach_lots.json` (NEW)
- `data/dialogue/dialogues.json` (Reach auctioneer)
- `spacegame/models/bidding.py` (Reach venue logic)
- `spacegame/views/auction_view.py` (Reach-themed dim styling)
- `tests/test_scenarios/test_scenario_reach_blackmarket.py` (NEW)

**Deliverables.**
- 4-6 black-market lot types (stolen goods, contraband, dangerous items, rebel-supplied tech).
- Reach auctioneer NPC with criminal-register voice sheet.
- Wreckers' Guild membership tier-gates access.
- Legality risk: bidding on stolen goods can incur faction-rep loss.
- Reach-themed dim-by-default UI consistent with ReachDarkLayout.

**Acceptance criteria.**
1. Tier-gates enforce correctly (apprentice locked from highest-risk lots).
2. Legality consequences fire when player wins illegal lots.
3. Black-market auctioneer voice distinct from Stellaris.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-B5 — Player-Initiated Auctions

**Status**: todo
**Phase**: Phase III | **Size**: L | **Effort**: 1.5 weeks
**Depends on**: SA-B2 | **Blocks**: SA-B6

**Goal.** Player can sell rare loot through the bidding system. Reverse-side mechanic. Listing fees, reserve prices, AI buyer pool. Makes the player a participant in the economy, not just a customer.

**Context to read.**
- SA-B2 implementation (core mechanic to reverse)
- `requirements/station_anchors.md` (SA-B5)

**Touch zones.**
- `spacegame/models/bidding.py` (player-listing flow)
- `spacegame/views/auction_view.py` (player-list UI)
- `spacegame/views/sell_lot_view.py` (NEW or fold into auction view)
- `data/auctions/buyer_personas.json` (NEW — AI buyer profiles)
- `tests/test_scenarios/test_scenario_player_listing.py` (NEW)

**Deliverables.**
- Player can list a held item with reserve price.
- Listing fee charged regardless of sale.
- AI buyer pool generates bids based on item desirability.
- Listing slots limited (configurable, e.g., 3 active at a time).
- Sale outcomes credit player.

**Acceptance criteria.**
1. Player lists an item, AI bids, sale resolves.
2. Reserve price respected (no sale below reserve).
3. Listing fee charged on listing creation.
4. Sale-failed outcome handled gracefully.
5. Player's bidding_history records sales.
6. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-B6 — Bidding polish + tuning

**Status**: todo
**Phase**: Phase III | **Size**: M | **Effort**: 1 week
**Depends on**: SA-B3, SA-B4, SA-B5 | **Blocks**: SA-X1, SA-X2, SA-X4, SA-X5, SA-X6, SA-X7, SA-X8, SA-X9

**Goal.** Polish pass on the full Bidding system. Lot value calibration, AI bidder difficulty tuning, narrative texture review, accessibility, time-pressure UX refinement.

**Context to read.**
- All SA-B1 through SA-B5 deliverables.

**Touch zones.**
- `data/auctions/*.json` (rebalancing)
- `spacegame/models/bidding_*.py` (tuning)
- `spacegame/views/auction_view.py` (UX refinement)

**Deliverables.**
- Tuning report.
- Updated lot pools and AI persona parameters.
- Accessibility audit addressed.

**Acceptance criteria.**
1. Player win rates balanced across rep tiers.
2. AI ceiling distributions feel honest (not clustered at extreme high or low).
3. UI complies with `ui_design_standards.md`.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase IV — Research Patronage

#### SA-R1 — Okafor Institute (Research Patronage)

**Status**: todo
**Phase**: Phase IV | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-PREP-1, SA-C2 | **Blocks**: SA-R2, SA-R3

**Goal.** Research-project funding mechanic at Okafor Institute Medical Wing (Axiom Labs). 8-12 active research project templates with rotating availability. Each project has design + outcomes + faction implications + risk profile. Dr. Okafor's successor as named NPC. 3-5 researcher NPCs as recurring sub-cast. Solo-fund vs. team-fund options. Risk dimension. Patent/IP system.

**Context to read.**
- `requirements/station_anchors.md` (Phase IV)
- `requirements/character_voices.md` (Dr. Okafor's successor + researchers)
- `requirements/investment_rewards_design.md` (sister concern)
- `data/galaxy/locations.json` (`axiom_research_wing`)
- `data/upgrades.json` (modules — research outcomes can unlock these)

**Touch zones.**
- `spacegame/views/research_view.py` (NEW)
- `spacegame/models/research.py` (NEW — project + funding state)
- `spacegame/models/player.py` (research_state field)
- `spacegame/save_manager.py`
- `data/research/projects.json` (NEW)
- `data/dialogue/dialogues.json` (Okafor successor + researchers)
- `data/galaxy/npcs.json`
- `spacegame/engine/game.py` / `spacegame/config.py` (GameState.RESEARCH)
- `tests/test_models/test_research.py` (NEW)
- `tests/test_views/test_research_view.py` (NEW)
- `tests/test_scenarios/test_scenario_research_arc.py` (NEW)

**Deliverables.**
- 8-12 research project templates with credit cost, game-day duration, outcome list, faction implications, risk profile.
- Project-funding mechanic: solo-fund (longer/cheaper) vs. team-fund (shorter/more expensive, shared returns).
- Risk dimension: some projects can fail (lost capital, bad outcomes).
- Patent/IP dimension: completed projects produce IP the player can license, sell, or hold.
- Dr. Okafor's successor as voiced NPC.
- 3-5 researcher recurring NPCs with voice sheets.
- Outcomes unlock unique modules, commodities, dialogue trees.

**Acceptance criteria.**
1. Player funds a project; game-day ticks advance progress; outcome resolves on completion.
2. Risk fires correctly (sometimes a project fails per its risk profile).
3. Solo vs. team measurably differ in cost/time.
4. Outcomes apply (modules unlocked, commodities available, etc.).
5. Patents can be held, licensed (passive returns), or sold (lump-sum).
6. Skill bonuses (Industry, Patron) apply.
7. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-R2 — Dr. Okafor's Legacy Narrative Arc

**Status**: todo
**Phase**: Phase IV | **Size**: M | **Effort**: 1 week
**Depends on**: SA-R1 | **Blocks**: SA-R3

**Goal.** Long-running narrative thread about ethics in research. Knowledge that heals vs. knowledge that profits. Multi-step storyline surfacing across many visits. Dialogue gates tied to which projects the player chooses to fund.

**Context to read.**
- SA-R1 implementation
- `requirements/character_voices.md`
- `requirements/cultural_guide.md` (Aurelia ethics register)

**Touch zones.**
- `data/dialogue/dialogues.json` (multi-step Okafor legacy arc)
- `data/journal/research.json` (NEW journal entries)
- `data/missions/research_arc.json` (NEW — gated mission triggers)
- `tests/test_scenarios/test_scenario_okafor_legacy.py` (NEW)

**Deliverables.**
- Multi-step dialogue arc revealed across 5-8 visits or specific project completions.
- Journal entries unlocked at narrative beats.
- Optional mission triggered by funding ethically-loaded research.

**Acceptance criteria.**
1. Arc unlocks correctly via funding choices (not random).
2. Two distinct ending paths based on funding pattern (heal-focused vs. profit-focused).
3. Voice sheet for Okafor successor satisfied throughout.
4. Writing Bible clear.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-R3 — Research Patronage polish

**Status**: todo
**Phase**: Phase IV | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-R1, SA-R2 | **Blocks**: SA-X1, SA-X2, SA-X4, SA-X5, SA-X6, SA-X7, SA-X9

**Goal.** Polish pass on Research Patronage. Project-cost calibration, outcome value tuning, patent-licensing rate balance.

**Touch zones.**
- `data/research/projects.json` (rebalancing)
- `spacegame/models/research.py` (tuning)

**Deliverables.**
- Tuning report.
- Updated project parameters.

**Acceptance criteria.**
1. Cost-to-outcome ratios feel fair across player progression stages.
2. Patent-licensing yields tuned to be a viable income stream without dominating.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase V — Financial Exchange

#### SA-F1 — Financial Exchange Design

**Status**: todo
**Phase**: Phase V | **Size**: M | **Effort**: 1 week
**Depends on**: SA-PREP-1, SA-C2, SA-V | **Blocks**: SA-F2

**Goal.** Design doc + prototyping for Financial Exchange. Futures contract pricing model (must feel honest against existing market simulation), shipping contract structure, insurance premium math, market manipulation surface, integration with `investment_rewards_design.md`.

**Context to read.**
- `requirements/station_anchors.md` (Phase V)
- `requirements/investment_rewards_design.md`
- `spacegame/models/market.py` (existing market simulation)
- SA-V (Cargo Broker introduction; Meridian graduation context)

**Touch zones.**
- `requirements/sa_financial_design.md` (NEW)

**Deliverables.**
- Design doc covering: futures pricing model, shipping contract structure, insurance math, market manipulation mechanics, sub-system integration with investment_rewards_design.md threads.
- Locked decisions on: real game-day market data vs. simulated projections, contract granularity, insurance premium calculation.

**Acceptance criteria.**
1. Each sub-system fully specified.
2. Pricing models specified concretely (not "TBD pricing").
3. Decisions locked.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F2 — Futures Core

**Status**: todo
**Phase**: Phase V | **Size**: XL | **Effort**: 2 weeks
**Depends on**: SA-F1 | **Blocks**: SA-F3, SA-F4, SA-F5, SA-F6, SA-F7

**Goal.** Implement futures contracts. Real market simulation work. Tests against price simulation.

**Context to read.**
- `requirements/sa_financial_design.md`
- `spacegame/models/market.py`
- `spacegame/models/player.py` (game_day cycle)

**Touch zones.**
- `spacegame/models/futures.py` (NEW)
- `spacegame/models/player.py` (futures_state field)
- `spacegame/save_manager.py`
- `tests/test_models/test_futures.py` (NEW)
- `tests/test_scenarios/test_scenario_futures_loop.py` (NEW)

**Deliverables.**
- Futures contract data model.
- Pricing engine integrated with market simulation.
- Contract lifecycle (offer → accept → mature → settle).
- Settlement against actual market prices on maturity.
- Save/load support.

**Acceptance criteria.**
1. Player accepts a futures contract; game-days advance; settlement resolves correctly.
2. Profitable contracts pay; losing contracts cost.
3. Pricing engine produces fair contract values across commodities.
4. Save/load preserves in-flight contracts.
5. 25+ new tests.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F3 — Meridian Venue + Cargo Broker graduation

**Status**: todo
**Phase**: Phase V | **Size**: L | **Effort**: 1.5 weeks
**Depends on**: SA-F2, SA-V | **Blocks**: SA-F4, SA-F7

**Goal.** Meridian Financial Exchange venue at Nexus Prime. Broker NPCs (named, voiced). Contract terminal UI. Cargo Broker graduation: the same Cargo Broker character from SA-V "graduates" the player to Meridian.

**Context to read.**
- SA-V implementation (Cargo Broker character)
- SA-F2 (futures core)
- `requirements/character_voices.md` (Meridian brokers + Cargo Broker)

**Touch zones.**
- `spacegame/views/meridian_view.py` (NEW)
- `spacegame/engine/game.py` / `spacegame/config.py` (GameState.MERIDIAN)
- `data/dialogue/dialogues.json` (Cargo Broker graduation tree, Meridian brokers)
- `data/galaxy/npcs.json` (Meridian broker NPCs)
- `spacegame/views/station_hub_view.py` (route Meridian unique-click)
- `tests/test_views/test_meridian_view.py` (NEW)
- `tests/test_scenarios/test_scenario_meridian_arc.py` (NEW)

**Deliverables.**
- Meridian venue view.
- Contract terminal UI for browsing/accepting futures.
- Cargo Broker graduation dialogue arc.
- 2-3 named Meridian brokers (junior, senior, headliner).
- Player's first Meridian visit triggers Cargo Broker graduation event.

**Acceptance criteria.**
1. Player at Nexus Prime clicks Meridian Financial Exchange unique card → enters venue.
2. First-visit graduation arc fires once per save.
3. Cargo Broker dialogue references prior Cargo Broker interactions (continuity).
4. Player can accept futures contracts from terminal.
5. Voice sheets satisfied for new brokers.
6. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F4 — Shipping Contracts sub-system

**Status**: todo
**Phase**: Phase V | **Size**: L | **Effort**: 1.5 weeks
**Depends on**: SA-F2 | **Blocks**: SA-F6, SA-F7

**Goal.** Agreed delivery for profit. Player accepts a contract to deliver A from System X to System Y by Day Z for payout. Faction implications. Route-quality bonuses.

**Context to read.**
- `requirements/sa_financial_design.md`
- SA-F2 implementation
- Existing cargo + travel system

**Touch zones.**
- `spacegame/models/shipping_contract.py` (NEW)
- `spacegame/models/player.py` (shipping_contracts field)
- `spacegame/save_manager.py`
- `data/missions/shipping_contracts.json` (NEW — initial contract pool)
- `tests/test_models/test_shipping_contract.py` (NEW)
- `tests/test_scenarios/test_scenario_shipping_contract.py` (NEW)

**Deliverables.**
- Shipping contract data model.
- Contract pool generation tied to market simulation.
- Deadline tracking per game-day cycle.
- Successful delivery → payout. Late/failed delivery → consequences.
- Route-quality bonus (some contracts pay more if delivered via specific waypoints).

**Acceptance criteria.**
1. Player accepts contract, ships cargo, delivers, receives payout.
2. Late delivery applies penalty per contract terms.
3. Contracts integrate with existing cargo/travel system without regression.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F5 — Insurance sub-system

**Status**: todo
**Phase**: Phase V | **Size**: M | **Effort**: 1 week
**Depends on**: SA-F2 | **Blocks**: SA-F7

**Goal.** Insurance — pay premiums against ship loss. Payout on destruction. Tied to ship value, combat record, faction standing.

**Context to read.**
- `requirements/sa_financial_design.md`
- `spacegame/models/ship.py` (ship value computation)
- `spacegame/models/combat.py` (combat outcomes)

**Touch zones.**
- `spacegame/models/insurance.py` (NEW)
- `spacegame/models/player.py` (insurance_policies field)
- `spacegame/save_manager.py`
- `spacegame/engine/game.py` (death/respawn integration)
- `tests/test_models/test_insurance.py` (NEW)
- `tests/test_scenarios/test_scenario_insurance.py` (NEW)

**Deliverables.**
- Insurance policy model with premium calculation, coverage tier, deductibles.
- Premium payment schedule (monthly game-time).
- Payout on ship destruction event.
- Premium adjusts with combat record.

**Acceptance criteria.**
1. Player buys policy, pays premiums, ship destroyed → payout received.
2. Combat record affects premium correctly.
3. Multiple coverage tiers selectable with appropriate trade-offs.
4. Save/load preserves active policies.
5. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F6 — Market Manipulation threats

**Status**: todo
**Phase**: Phase V | **Size**: M | **Effort**: 1 week
**Depends on**: SA-F2, SA-F4 | **Blocks**: SA-F7

**Goal.** Other actors can manipulate markets. News events affect futures. Player can sometimes counter or exploit. Adds depth and risk.

**Context to read.**
- `requirements/sa_financial_design.md`
- SA-F2, SA-F4 implementations
- Existing news ticker + galaxy events systems

**Touch zones.**
- `spacegame/models/market_manipulation.py` (NEW)
- `spacegame/models/galaxy_event.py` (extend with manipulation events)
- `data/galaxy/manipulation_events.json` (NEW)
- `tests/test_models/test_market_manipulation.py` (NEW)

**Deliverables.**
- 6-8 manipulation event templates (cartel pumps, supply-line sabotage, false-news pumps).
- Manipulation events affect commodity prices and futures contracts.
- Player can sometimes detect and counter (skill-check based).

**Acceptance criteria.**
1. Manipulation events fire correctly per their probabilities.
2. Effects on prices and futures verifiable in tests.
3. Player counters work at appropriate skill thresholds.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-F7 — Financial Crisis Event Arc

**Status**: todo
**Phase**: Phase V | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-F2, SA-F4, SA-F5, SA-F6 | **Blocks**: SA-X1, SA-X2, SA-X4, SA-X5, SA-X6, SA-X7, SA-X8, SA-X9

**Goal.** Major scripted event. Markets crash, futures contracts come due in chaos, player navigates. Big narrative moment. Multi-session arc requiring all financial sub-systems to be in place.

**Context to read.**
- All SA-F1 through SA-F6 deliverables.
- `requirements/character_voices.md` (Meridian brokers in crisis mode)

**Touch zones.**
- `data/galaxy/financial_crisis_event.json` (NEW — scripted event chain)
- `data/dialogue/dialogues.json` (crisis-mode broker dialogue)
- `data/missions/crisis_arc.json` (NEW — player-facing missions)
- `spacegame/models/galaxy_event.py` (special-case crisis trigger)
- `tests/test_scenarios/test_scenario_financial_crisis.py` (NEW)

**Deliverables.**
- Multi-session scripted financial crisis arc.
- Player choices during crisis affect outcome (run, profit-from-chaos, stabilize, etc.).
- Branching consequences across faction reputations and economic conditions.
- Crisis aftermath ripples for N game-days.

**Acceptance criteria.**
1. Crisis triggers under defined conditions (game-day + market state thresholds).
2. Multiple distinct player choice paths each produce different outcomes.
3. Crisis aftermath affects subsequent gameplay (verifiable in tests).
4. Voice sheets for crisis-mode brokers satisfied.
5. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)

### Phase VI — Cohesion + Polish

#### SA-X1 — Cross-anchor narrative threading

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1.5 weeks
**Depends on**: SA-1, SA-2, SA-V, SA-P6, SA-B6, SA-R3, SA-F3, SA-F7 | **Blocks**: none

**Goal.** 30-50+ dialogue insertions across crew, recurring NPCs, station chatter, existing NPCs. The player should hear references to their anchor activity literally everywhere. Includes Marcus Jin reactions to Deep Shafts visits, Malia Torres reactions to Wreckers' milestones, Cargo Broker reactions to Meridian success.

**Context to read.**
- All Cluster B + Cluster C completed work.
- `requirements/character_voices.md`
- `data/dialogue/dialogues.json`, `data/dialogue/ambient_lines.json`

**Touch zones.**
- `data/dialogue/dialogues.json` (extensive insertions)
- `data/dialogue/ambient_lines.json` (extensive insertions)
- `data/galaxy/station_chatter.json` (anchor-aware chatter)
- `tests/test_writing_bible_compliance.py` (regression coverage)

**Deliverables.**
- 30-50+ new conditional dialogue lines that fire based on player anchor history.
- Crew reactions to anchor outcomes (specialist crew with relevant skills react first).
- Station chatter that references recent player anchor activity.
- Existing NPCs across the game updated with anchor-aware lines where contextually appropriate.

**Acceptance criteria.**
1. After completing N anchor milestones, player hears at least M references in subsequent unrelated dialogue/chatter.
2. Conditional logic correctly gates each line.
3. Writing Bible scanner clear.
4. No dialogue regressions in existing trees.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X2 — Reputation consistency audit + rebalance

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week
**Depends on**: SA-1, SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** Audit anchor activity rep deltas across all phases. Rebalance so no anchor dominates rep gain or under-rewards engagement. Confirm rep changes flow consistently with rest of game.

**Touch zones.**
- All anchor JSON data files (rebalance numbers).
- `requirements/sa_rep_audit_findings.md` (NEW report)

**Deliverables.**
- Audit report.
- Rebalanced rep deltas across all anchor activity sources.

**Acceptance criteria.**
1. No anchor offers rep gain >2x another anchor for comparable effort.
2. Rep loss paths exist for each major faction (no rep-only-up exploits).
3. Sub-reputation interacts cleanly with faction reputation per SA-B-EXT-1.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X3 — Tutorial integration

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week
**Depends on**: SA-1, SA-2, SA-V, SA-P3, SA-B3, SA-R1, SA-F3 | **Blocks**: none

**Goal.** Per-anchor first-time tips using PT-M FirstTimeTipOverlay (same pattern as SL-5). One sentence each, declarative, no flavor. Plus introduction missions for any system without one.

**Context to read.**
- `requirements/onboarding_design.md`
- `spacegame/views/first_time_tip.py`
- SL-5 implementation pattern (faction-first-dock tip)

**Touch zones.**
- `spacegame/views/wreckers_guild_view.py`, `dispute_view.py`, `auction_view.py`, `research_view.py`, `meridian_view.py`, `deep_shafts_view.py` (each gets a `_maybe_show_*_tip` helper)
- `spacegame/constants/flags.py` (new `seen_*_tip` helpers)

**Deliverables.**
- 6 per-anchor first-time tips wired via PT-M.
- Tips fire once per save, suppressed by mission-objective conflicts (matches SL-5 pattern).
- Tests for each tip.

**Acceptance criteria.**
1. Each tip fires on first interaction with its anchor system.
2. Tips don't re-fire after dismissal.
3. Tips suppressed when mission-objective glow active.
4. Voice clean per onboarding_design.md register.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X4 — Journal pass

**Status**: todo
**Phase**: Phase VI | **Size**: S | **Effort**: 5 days
**Depends on**: SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** Standardize journal voice and format across all anchor entries. Each anchor has a signature journal voice that fits the location.

**Touch zones.**
- `data/journal/*.json`

**Deliverables.**
- Journal entries standardized per anchor signature voices.
- Each anchor has an introductory journal entry on first interaction.

**Acceptance criteria.**
1. 12-20+ new or revised journal entries.
2. Voice consistency across each anchor's entries.
3. Writing Bible clear.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X5 — News ticker integration

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week
**Depends on**: SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** Anchor activity produces news headlines. 30-40+ new news templates covering politics outcomes, auction results, research breakthroughs, futures movements, financial-crisis ripples.

**Context to read.**
- `data/galaxy/news_templates.json`
- All SA system implementations

**Touch zones.**
- `data/galaxy/news_templates.json`
- `spacegame/models/news.py` (event-sourcing extensions if needed)

**Deliverables.**
- 30-40+ new news templates spanning all SA systems.
- Trigger logic in each system to produce news on outcomes.

**Acceptance criteria.**
1. Major outcomes from each SA system produce news within reasonable game-day window.
2. News templates voice-clean.
3. No template-rotation regressions.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X6 — Crew reactions / anchor banter

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week
**Depends on**: SA-A2, SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** Crew comments on anchor activity. Specialist crew (Social, Commerce, Industry + new SA specialist roles) get anchor-specific banter.

**Context to read.**
- `data/crew/*.json` and crew banter system
- All SA implementations

**Touch zones.**
- `data/crew/banter.json` (anchor-aware lines)
- `spacegame/models/crew.py` (banter trigger conditions)

**Deliverables.**
- 25-40+ banter lines tied to anchor outcomes.
- Specialist crew react first when their specialty matches the activity.

**Acceptance criteria.**
1. Crew react to anchor outcomes within session.
2. Specialist match correctly triggers preferred crew.
3. Voice sheets and Writing Bible clear.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X7 — Achievement pass

**Status**: todo
**Phase**: Phase VI | **Size**: S | **Effort**: 3 days
**Depends on**: SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** New unique achievements per system: Salvage Master (Wreckers'), Council Mediator (Politics), Auction Champion (Bidding), Patron of Research (Okafor), Wall Street Captain (Meridian), Pilgrim of the Shafts (Deep Shafts), plus several hidden / cross-anchor achievements that reward unusual play.

**Touch zones.**
- `data/achievements.json`
- `spacegame/achievement_manager.py` (any wiring needed)

**Deliverables.**
- 8-12 new achievements across SA systems.
- Trigger logic verified.

**Acceptance criteria.**
1. Each achievement unlockable through documented player actions.
2. Hidden achievements stay hidden until unlock.
3. Save/load preserves achievement state.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X8 — Cross-anchor mega-arc

**Status**: todo
**Phase**: Phase VI | **Size**: XL | **Effort**: 2-3 weeks
**Depends on**: SA-P6, SA-B6, SA-F3, SA-F7 | **Blocks**: none

**Goal.** Long-running narrative spanning multiple anchors. A corruption scheme threading through Stellaris auctions, Meridian futures, and Verdant politics — three venues, one through-line. Multi-session, branching, with consequences across all three Cluster C systems.

**Context to read.**
- All Cluster C implementations
- `requirements/cultural_guide.md`
- `requirements/character_voices.md`

**Touch zones.**
- `data/missions/cross_anchor_arc.json` (NEW — multi-step mission chain)
- `data/dialogue/dialogues.json` (arc-specific dialogue)
- `data/journal/cross_anchor.json` (NEW)
- `spacegame/models/cross_anchor_arc.py` (state tracking — NEW or fold into existing campaign system)
- `tests/test_scenarios/test_scenario_mega_arc.py` (NEW)

**Deliverables.**
- Multi-step branching narrative spanning Stellaris + Meridian + Verdant.
- 3-5 distinct ending paths based on player decisions across all three venues.
- Arc state tracking with save/load support.
- Major reward outcomes (legendary item, faction perk, narrative resolution beats).

**Acceptance criteria.**
1. Arc triggerable after player has engaged with all three venues.
2. Distinct branches verifiable in tests.
3. Endings ripple into post-arc gameplay (faction reputations, news ticker, NPC reactions).
4. Voice sheets satisfied throughout.
5. Writing Bible clear on multi-thousand-word arc content.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X9 — Audio + music pass

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week (assuming existing audio pipeline)
**Depends on**: SA-P6, SA-B6, SA-R3, SA-F3 | **Blocks**: none

**Goal.** Each venue gets ambient audio identity. Politics: gavel, murmur. Auctions: room noise, auctioneer cadence. Meridian: trading-floor energy. Optional venue-specific music tracks for major beats.

**Touch zones.**
- `spacegame/engine/audio_manager.py`
- `data/audio/` directory (new audio assets)
- Each anchor view to wire ambient sound on enter.

**Deliverables.**
- Ambient audio loops per venue.
- Optional music tracks (if asset budget allows).

**Acceptance criteria.**
1. Each venue audio identity distinct on first listen.
2. Audio doesn't regress at any of 6 tested resolutions.
3. Mute/volume settings respected.

**Risks / open questions.**
- New audio asset creation: in-scope or out-of-scope? Recommendation: scope is "wire existing assets and identify gaps." Asset creation outside SA-X9 if needed.

**Activity log.**
- 2026-04-26 — todo (created)

#### SA-X10 — Visual identity per venue

**Status**: todo
**Phase**: Phase VI | **Size**: M | **Effort**: 1 week
**Depends on**: SA-1, SA-P3, SA-B3, SA-R1, SA-F3 | **Blocks**: none

**Goal.** SL-4 standardized layout. SA-X10 pushes per-venue visual identity within that standardization — distinctive backgrounds, lighting, signature props.

**Touch zones.**
- Each new venue view (`wreckers_guild_view.py`, `dispute_view.py`, `auction_view.py`, etc.).
- `spacegame/engine/sprites.py` (if new sprite assets needed).

**Deliverables.**
- Per-venue visual treatments distinct from other venues but consistent within their faction's identity.

**Acceptance criteria.**
1. Each venue visually distinct.
2. UI compliance maintained (`ui_design_standards.md`).
3. No layout regressions at 6 tested resolutions.

**Activity log.**
- 2026-04-26 — todo (created)

---

## Followups

Smaller deferred items pulled from prior sprint findings. Each is independently scopable; included here so the dispatcher has additional eligible work outside the SA arc.

### CB-1 — Crew Banter scope (scoping)

**Status**: todo
**Source**: Living Universe Arc deferral (see memory: "CB sprint (Crew Banter) remains deferred")
**Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: CB-2

**Goal.** Define the actual scope of the CB Crew Banter sprint. The sprint has been deferred multiple times without explicit scope-locking. Produce a small scoping doc identifying: which crew banter currently exists, what gaps remain, what the deferred sprint was supposed to address, and whether CB content should be folded into SA-X6 or remain its own track.

**Context to read.**
- Memory entries on Living Universe Arc
- `requirements/character_voices.md`
- `data/crew/banter.json` (current state)
- `requirements/station_anchors.md` (SA-X6 scope — overlap check)

**Touch zones.**
- `requirements/cb_scope.md` (NEW)

**Deliverables.**
- Scope doc.
- Recommendation: fold into SA-X6, run parallel, or keep deferred indefinitely.

**Acceptance criteria.**
1. Doc enumerates current crew banter coverage.
2. Identifies specific gaps the deferred sprint was meant to address.
3. Locks recommendation.

**Activity log.**
- 2026-04-26 — todo (created)

### CB-2 — Crew Banter implementation

**Status**: todo
**Source**: TBD via CB-1
**Size**: M | **Effort**: TBD
**Depends on**: CB-1 | **Blocks**: none

**Goal.** Per CB-1's recommendation, implement the gap-filling banter. Scope locks at CB-1 completion.

**Activity log.**
- 2026-04-26 — todo (created — scope pending CB-1)

### WB-1 — Station tagline scanner coverage

**Status**: todo
**Source**: `requirements/writing_bible_scanner_gaps.md` Gap 1
**Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: WB-2

**Goal.** Extend the Writing Bible compliance scanner to cover station tagline strings. Currently `faction_tagline = "..."` class attributes in `station_layouts.py` are invisible to the scanner because the regex only matches `.render("literal")` calls, not variable references.

**Context to read.**
- `requirements/writing_bible_scanner_gaps.md`
- `tests/test_writing_bible_compliance.py`
- `spacegame/views/station_layouts.py`

**Touch zones.**
- `tests/test_writing_bible_compliance.py` (add `_extract_tagline_strings` + tests)

**Deliverables.**
- New extractor pulling `faction_tagline` from each `StationLayout` subclass.
- 3 new tests (em-dashes, banned phrases, parallel-negation) following existing pattern.

**Acceptance criteria.**
1. Scanner now flags any future em-dash or banned-phrase introduction in faction taglines.
2. Reach tagline allowlist correctly suppresses parallel-negation flag.
3. Existing tests still pass.

**Activity log.**
- 2026-04-26 — todo (created)

### WB-2 — Parallel-negation regex broadening

**Status**: todo
**Source**: `requirements/writing_bible_scanner_gaps.md` Gap 2
**Size**: S | **Effort**: 3-5 days
**Depends on**: WB-1 | **Blocks**: none

**Goal.** Broaden the `_PARALLEL_NEGATION` regex to catch period-parallelism ("No X. No Y.") and dash-parallelism ("No X — no Y"), not just comma-parallelism. The Writing Bible's intent is broader than the current regex captures.

**Context to read.**
- `requirements/writing_bible_scanner_gaps.md`
- `tests/test_writing_bible_compliance.py`

**Touch zones.**
- `tests/test_writing_bible_compliance.py` (regex update)

**Deliverables.**
- Updated regex catches all three separator styles.
- Audit pass on existing scanned content for newly-detected violations.
- Reach tagline still suppressed via allowlist.

**Acceptance criteria.**
1. Test cases for each separator pattern.
2. Existing content audit identifies any new violations and addresses them (fix or allowlist with documented rationale).
3. Full suite green.

**Risks / open questions.**
- Risk: tightening the regex may catch existing content. Treat detection as a content audit, not a scanner regression.

**Activity log.**
- 2026-04-26 — todo (created)

### SI3-FOLLOW-1 — No-arg helper introspection (flag scanner)

**Status**: todo
**Source**: SL-2 disclosure (`requirements/station_legibility.md`)
**Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: none

**Goal.** Extend the SI-3 flag-integrity scanner in `tests/test_data/test_dialogue_integrity.py` to recognize no-arg helpers like `investment_introduced()`. Current `_helper_access_patterns` calls each helper with sentinel args; no-arg helpers raise TypeError and get silently skipped, leaving consumers invisible to the scanner.

**Context to read.**
- `tests/test_data/test_dialogue_integrity.py` (`_helper_access_patterns`)
- `spacegame/constants/flags.py` (current parameterized + no-arg helpers)
- `requirements/station_legibility.md` (SL-2 scanner gap section)

**Touch zones.**
- `tests/test_data/test_dialogue_integrity.py`

**Deliverables.**
- Updated `_helper_access_patterns` handles no-arg helpers (try `obj()` first; if it returns a literal string, treat as a fixed-flag helper without sentinel substitution).
- Producer/consumer regex variants for fixed-flag helpers.

**Acceptance criteria.**
1. `investment_introduced` flag now detected as both producer (when present in mission JSON) and consumer (in `is_investment_unlocked`).
2. No regression: existing parameterized helpers still detected correctly.
3. Full suite green; orphan reports remain accurate.

**Activity log.**
- 2026-04-26 — todo (created)

### UI-BOUNDS-1 — station_hub_view in subprocess bounds harness

**Status**: todo
**Source**: SL-1 deferral (`requirements/station_legibility.md`)
**Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: none

**Goal.** Fold `station_hub_view` into the subprocess bounds harness so the POI strip region is exercised at all 6 tested resolutions. The harness currently exercises 16 views; station_hub isn't one of them. Adding it closes the SL-1 acceptance-gap that was deferred.

**Context to read.**
- `tests/test_ui_layout/test_subprocess_bounds.py`
- `tests/test_ui_layout/_subprocess_bounds_inner.py`
- `spacegame/views/station_hub_view.py`
- `requirements/ui_sprint_3a_findings.md`

**Touch zones.**
- `tests/test_ui_layout/test_subprocess_bounds.py`
- `tests/test_ui_layout/_subprocess_bounds_inner.py`

**Deliverables.**
- View factory for `station_hub_view` in the harness.
- Bounds tests pass at all 6 resolutions.
- POI strip region explicitly verified to render within layout bounds.

**Acceptance criteria.**
1. Harness lists `station_hub_view` as a covered view.
2. All 6 resolutions pass bounds checks for station hub.
3. Strip region verified within `_LAYOUT_BOTTOM`/`_HUD_H` bounds.
4. Full suite green.

**Activity log.**
- 2026-04-26 — todo (created)
