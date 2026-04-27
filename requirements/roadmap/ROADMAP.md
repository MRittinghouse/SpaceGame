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

The SA-arc table below is **auto-regenerated** by the ralph harness from the sprint sections. Don't hand-edit between the markers; edits get overwritten on the next harness run.

<!-- AUTO_GENERATED_SA_INDEX_START -->
| ID | Title | Phase | Size | Status | Depends on |
|---|---|---|---|---|---|
| [SA-PREP-1](#sa-prep-1--npc-voice-sheet-audit) | NPC voice-sheet audit | 0 | M | done | none |
| [SA-PREP-2](#sa-prep-2--existing-data-audit) | Existing-data audit | 0 | S | done | none |
| [SA-PREP-3](#sa-prep-3--playtest-baseline-telemetry) | Playtest baseline telemetry | 0 | S | todo | none |
| [SA-A1](#sa-a1--crew-specialization-design) | Crew specialization design | A | S | todo | SA-PREP-2 |
| [SA-A2](#sa-a2--crew-template-implementation) | Crew template implementation | A | M | todo | SA-A1 |
| [SA-B-EXT-1](#sa-b-ext-1--sub-reputation-system) | Sub-reputation system | B | M | todo | none |
| [SA-C1](#sa-c1--skill-tree-extension-design) | Skill tree extension design | C | S | todo | SA-PREP-2 |
| [SA-C2](#sa-c2--skill-tree-extension-implementation) | Skill tree extension implementation | C | M | todo | SA-C1 |
| [SA-0](#sa-0--cluster-a-confirmation-pass) | Cluster A confirmation pass | I | S | todo | SA-PREP-2 |
| [SA-1](#sa-1--wreckers-guild-hall-salvage-contracts) | Wreckers' Guild Hall (Salvage Contracts) | I | L | todo | SA-PREP-1, SA-A2, SA-B-EXT-1 |
| [SA-2](#sa-2--deep-shafts-memorial--pilgrimage) | Deep Shafts memorial / pilgrimage | I | L | todo | SA-PREP-1 |
| [SA-V](#sa-v--cargo-broker-arc--investment-introduction) | Cargo Broker arc + Investment Introduction | I | M | todo | SA-PREP-1 |
| [SA-P1](#sa-p1--politics-system-design) | Politics System Design | II | M | todo | SA-PREP-1, SA-C2 |
| [SA-P2](#sa-p2--politics-core) | Politics Core | II | XL | todo | SA-P1, SA-A2, SA-C2, SA-B-EXT-1 |
| [SA-P3](#sa-p3--mayors-council-chamber-verdant-venue) | Mayors' Council Chamber (Verdant Venue) | II | L | todo | SA-P2 |
| [SA-P4](#sa-p4--alliance-congress-hall-havens-rest-venue) | Alliance Congress Hall (Haven's Rest Venue) | II | L | todo | SA-P2, SA-P3 |
| [SA-P5](#sa-p5--wreckers-guild-gray-market-mediation-venue) | Wreckers' Guild gray-market mediation venue | II | M | todo | SA-P2, SA-1 |
| [SA-P6](#sa-p6--politics-polish--tuning) | Politics polish + tuning | II | M | todo | SA-P3, SA-P4, SA-P5 |
| [SA-B1](#sa-b1--bidding-system-design) | Bidding System Design | III | M | todo | SA-PREP-1 |
| [SA-B2](#sa-b2--bidding-core) | Bidding Core | III | XL | todo | SA-B1, SA-A2, SA-C2 |
| [SA-B3](#sa-b3--stellaris-auction-house-primary-venue) | Stellaris Auction House (primary venue) | III | L | todo | SA-B2 |
| [SA-B4](#sa-b4--crimson-reach-black-market-auctions) | Crimson Reach Black Market auctions | III | L | todo | SA-B2, SA-1 |
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
| [SA-X1](#sa-x1--cross-anchor-narrative-threading) | Cross-anchor narrative threading | VI | M | todo | SA-1, SA-2, SA-V, SA-P6, SA-B6, SA-R3, SA-F3, SA-F7 |
| [SA-X2](#sa-x2--reputation-consistency-audit--rebalance) | Reputation consistency audit + rebalance | VI | M | todo | SA-1, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X3](#sa-x3--tutorial-integration) | Tutorial integration | VI | M | todo | SA-1, SA-2, SA-V, SA-P3, SA-B3, SA-R1, SA-F3 |
| [SA-X4](#sa-x4--journal-pass) | Journal pass | VI | S | todo | SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X5](#sa-x5--news-ticker-integration) | News ticker integration | VI | M | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X6](#sa-x6--crew-reactions--anchor-banter) | Crew reactions / anchor banter | VI | M | todo | SA-A2, SA-1, SA-2, SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X7](#sa-x7--achievement-pass) | Achievement pass | VI | S | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X8](#sa-x8--cross-anchor-mega-arc) | Cross-anchor mega-arc | VI | XL | todo | SA-P6, SA-B6, SA-F3, SA-F7 |
| [SA-X9](#sa-x9--audio--music-pass) | Audio + music pass | VI | M | todo | SA-P6, SA-B6, SA-R3, SA-F3 |
| [SA-X10](#sa-x10--visual-identity-per-venue) | Visual identity per venue | VI | M | todo | SA-1, SA-P3, SA-B3, SA-R1, SA-F3 |
<!-- AUTO_GENERATED_SA_INDEX_END -->

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

**Status**: done
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

**Deliverables.**
- Inventory table at the top of the SA section in `character_voices.md`: every named NPC the SA arc touches, with status (existing / extend / net-new), existing speaker_id (if any), and the SA sprint(s) that consume the sheet.
- For each NPC: existing voice sheet (with consistency-pass edits) OR a new sheet at the Elena/Marcus/Priya/Tomas standard (six-section structure: Core voice, Verbal habits, What they say vs. mean, Emotional range, What they never say, Sample lines).
- A "tonal map" identifying at least one distinguishing register feature per character.
- A speaker_id registry table mapping every named SA NPC to its canonical snake_case `speaker_id`. Flags any deferred reconciliations (e.g., `delivery_merchant` to `odom_broker` belongs to SA-V; the `torres_memorial` duplicate of `malia_torres` is captured for SA-1).

**Acceptance criteria.**
1. Inventory covers Malia Torres, Marcus Jin, Dr. Okafor's successor (named, distinct from existing `jez_okafor`), Cargo Broker (canonical name **Odom** per locked decision), Verdant Mayor + 3 Verdant council delegates, 4 Alliance Congress delegates, Stellaris Auctioneer + 3 recurring rivals, Meridian primary broker, Deep Shafts miner caretaker, Wreckers' Guild secondary contacts (3 — wreck navigator, salvage engineer, debris-field cartographer).
2. Every character has a voice sheet at the Elena/Marcus/Priya/Tomas standard. Six sections, minimum 3 sample lines, named verbal-habits and emotional-range tags.
3. All new and edited sheets pass the Writing Bible scanner: no em-dashes (≤1 per long sheet by craft exception), no banned phrases ("a testament to", "couldn't help but", parallel-negation rhetoric), no banned names (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose).
4. Tonal map is concrete: each character has at least one named distinguishing register feature. Extends the existing Voice Interactions table with at least 3 new SA-relevant cross-character pairings.
5. Speaker_id registry table committed alongside the inventory. Each NPC has a canonical snake_case id; reconciliations needed in downstream sprints are listed with the consuming sprint ID.
6. Cargo Broker / Odom name reconciliation is captured: voice sheet upgraded from 3-line stub to full standard; explicit note that the `delivery_merchant` speaker_id and `talked_to_cargo_broker` flag should be reconciled in SA-V (not this sprint).

**Plan.**

| # | Task | Files touched | Verification | Risks |
|---|---|---|---|---|
| 1 | Inventory pass: walk `data/dialogue/dialogues.json` `speaker_id` set + cross-reference acceptance-criteria NPC list. Produce the inventory table at the top of a new `## Station Anchors arc — NPC inventory` section in `character_voices.md`. Tag each as existing / extend / net-new with the consuming SA sprint(s). | `requirements/character_voices.md` | Manual table check; numbers reconcile with criterion #1 (about 22 NPCs). | `delivery_merchant`, `torres_memorial`, `jez_okafor` are existing speaker_ids easy to mistake for SA characters. Spell out distinctions in the inventory. |
| 2 | Reconcile Cargo Broker to Odom. Replace the current 3-line stub with a full Elena-standard sheet. The Broker carries SA-V to SA-F3 (graduation to Meridian) so this is the most-consumed sheet in the arc. Note the deferred speaker_id rename (`delivery_merchant` to `odom_broker`) as SA-V scope. | `requirements/character_voices.md` | Sheet length parity with Elena/Marcus/Priya. Six sections present. Writing Bible scanner clean. | Voice must square with existing dialogue text (lines around 1003-1243) without forcing SA-V to rewrite. Confirm Odom's existing voice is consistent. |
| 3 | Consistency pass on existing sheets that SA-1 / SA-2 will consume: Malia Torres (SA-1 Wreckers' Guild membership-tier interactions, SA-P5 Reach-venue arbitration), Marcus Jin (SA-2 Deep Shafts pilgrimage). Add an "SA Notes" subsection to each. | `requirements/character_voices.md` | Diff review: only additive changes. | Marcus's father link to Sora Takahashi (Breakstone Uprising 2267) is implicit in cultural guide; SA-2 needs the elder caretaker as the primary teller. Don't conflate the historical figure with Marcus's actual father. |
| 4 | Author Cluster B sheets: Dr. Okafor's successor (named distinct from `jez_okafor`); Deep Shafts miner caretaker (elder Union miner who tells the Sora Takahashi stories); 3 Wreckers' Guild secondary contacts (wreck navigator, salvage engineer, debris-field cartographer). | `requirements/character_voices.md` | Five new sheets, each at full standard. Surnames diversified; no overlap with existing `*_okafor` speakers. | Dr. Okafor's successor easy trap: defaults to "another scientist who sounds like Priya." Make register distinct: founder-shadow + institutional fatigue, not academic curiosity. |
| 5 | Author Politics sheets: Verdant Mayor + 3 council delegates + 4 Alliance Congress delegates = 8 sheets. Verdant is Frontier-Alliance flavored; Alliance Congress speakers each represent a different settlement. | `requirements/character_voices.md` | Eight new sheets at full standard. Cross-faction contrast appears in tonal map. | Sheet fatigue → AI tells creep in. Author in two batches with Writing Bible re-read between. Include at least one obstinate, one self-interested, one grief-shaped voice in each set. |
| 6 | Author Bidding sheets: Stellaris Auctioneer + 3 recurring rivals. Pick three rival personas during this task (collector, faction agent, rival captain or equivalent) and lock them. Auctioneer needs a verbal-cadence feature distinctive enough to be recognized by sound alone. | `requirements/character_voices.md` | Four new sheets at full standard. Three rivals with locked persona tags SA-B3 can consume. | Rival captain risks duplicating Tomas's charm. Push toward cold rivalry or earned grudge instead. |
| 7 | Author Financial sheet: Meridian primary broker. Per SA-F3 the broker carries the Cargo Broker → Meridian graduation. Voice must contrast with Odom (Odom: working middleman; Meridian broker: institutional, polished, gatekeeper). | `requirements/character_voices.md` | One sheet at full standard. Voice contrast with Odom called out in SA Notes. | Easy to write Meridian broker as a Guild knock-off. Meridian is a financial exchange with its own register. |
| 8 | Compile tonal map: per-NPC one-line distinguishing register feature appended to each sheet's header. Extend the `## Voice Interactions` table with ≥3 new SA-relevant pairings. | `requirements/character_voices.md` | Voice Interactions table grows by ≥3 rows. | Repeating "terse"/"warm" defeats the cohesion goal. Force unique adjectives per character. |
| 9 | Compile speaker_id registry table: snake_case canonical id for each SA NPC. Flag deferred reconciliations. | `requirements/character_voices.md` | Diff between inventory table and registry: no NPC missing. | Missing registrations cause downstream drift. |
| 10 | Writing Bible scanner pass on the new content. Fix violations. Re-read all new sheets aloud per dialogue guide §6 self-check. | `requirements/character_voices.md` | Scanner clean. Pass count from baseline (8326) preserved. | If a scanner flags a legitimate craft em-dash, document the exception inline; don't delete the line. |

**Risks / open questions.**
- ~~Cargo Broker existing data~~ — RESOLVED: dialogue tree (lines around 1003-1243) names him **Odom**; voice sheet is the 3-line stub. Decision locked: canonical name = Odom. Speaker_id reconciliation deferred to SA-V.
- ~~Whether to split per-character into a subdirectory~~ — RESOLVED: keep all sheets in `character_voices.md`. Revisit if file exceeds ~2000 lines after SA-PREP-1.
- ~~Sheet standard~~ — RESOLVED: full Elena/Marcus/Priya/Tomas six-section structure, minimum 3 sample lines per sheet.
- ~~Dr. Okafor's successor naming~~ — RESOLVED: must be distinct from existing `jez_okafor` (Breakstone deep-shafts shift supervisor); the successor runs Axiom Labs' Okafor Institute Medical Wing. Lock the successor's full name during task 4.
- ~~Three personas for the Bidding rivals~~ — RESOLVED: (a) **Old-money collector** — heritage capital, condescending register, treats auctions as social ritual; (b) **Stellaris faction agent** — institutional buyer with internal procurement pressure, polite but inflexible, never personal; (c) **Cold-grudge rival captain** — independent, history with the player implied, no charm overlap with Tomas (this is the deliberate contrast: rivalry is earned and quiet, not theatrical). These three give SA-B3 distinct dramatic vectors (status, institution, history) without overlap. Lock the names during task 6.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 17:32 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)
- 2026-04-26 20:48 — harness: plan phase starting
- 2026-04-26 21:05 — planning confirmed; recovered plan verified against context docs; locked the last open question (Bidding rivals personas: old-money collector + Stellaris faction agent + cold-grudge rival captain); refreshed test-suite baseline (8304 → 8326) in task 10. PHASE_OK
- 2026-04-26 20:50 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 21:30 — implementation complete; 21 NPC voice sheets authored; inventory table, speaker_id registry, tonal map, Voice Interactions extension committed; tests 8326/8326 baseline preserved; Writing Bible scanner 17/17 clean. PHASE_OK
- 2026-04-26 21:15 — harness: review phase starting (rework cycle 0)
- 2026-04-26 21:45 — review complete; all 6 acceptance criteria verified; 21 NPCs inventoried (18 net-new sheets + 3 extended); tonal register added to all sheets; speaker_id registry and Voice Interactions table (5 new pairings) confirmed; Writing Bible scanner 17/17 passing; 8326/8326 tests preserved; zero Unicode em-dashes in new body prose; no banned phrases, names, or parallel negation in SA arc additions. No findings requiring rework. PHASE_OK
- 2026-04-26 21:21 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 21:15
- Completed: 2026-04-26 21:45
- Files_changed: none
- Commits: none
- Tests_passing: 8326
- Acceptance_criteria_verified: 6/6
- Polish_items_verified: n/a
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Followup_sprints_added: none
- Notes: All deliverables shipped. 18 net-new voice sheets at full Elena-standard; Odom upgraded from stub; SA Notes on Malia Torres and Marcus Jin; inventory table, speaker_id registry, and tonal map committed. Pre-existing Unicode em-dashes in original Elena/Marcus/Priya/Tomas body prose are out of scope; new SA arc body prose correctly uses ASCII double-hyphen convention. Writing Bible automated scanner (17/17) clean; manual scan of SA arc content confirmed zero banned phrases, banned names, or parallel negation in the 877 lines of new content.

#### SA-PREP-2 — Existing-data audit

**Status**: done
**Phase**: Phase 0 | **Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: SA-A1, SA-C1, SA-0

**Goal.** Walk every content surface (dialogue trees, missions, journal entries, ambient/station chatter, encounters, news templates, NPC home assignments) and produce a per-anchor inventory of what already references each Station Anchor location plus the Cargo Broker character. Surface the asymmetric content state (some anchors heavily seeded, others lore-only) so downstream SA sprints inherit a starting point. Capture a regression baseline so post-SA changes can be verified against the pre-SA state.

**Context to read.**
- `requirements/station_anchors.md` (anchor inventory + cluster definitions)
- `data/galaxy/locations.json` (`location_type: unique` cards)
- `data/dialogue/dialogues.json`
- `data/missions/missions.json`, `data/missions/side_missions.json`, `data/missions/crew_quests.json`
- `data/journal/entries.json`, `data/journal/travel_log_templates.json`
- `data/characters/npcs.json` (NPC `home_system_id` mapping; anchor linkage is mostly indirect via this field)
- `data/economy/news_templates.json`
- `data/encounters/*.json`
- `data/crew/station_chatter.json`, `data/crew/ambient_dialogue.json`
- `tests/test_writing_bible_compliance.py` (voice-check regex patterns)
- `requirements/character_voices.md` (cross-reference for named NPC presence)

**Touch zones.**
- `requirements/sa_audit_findings.md` (NEW)

**Deliverables.**
- A findings doc with: a cross-cutting summary table; one section per anchor subject (10 anchors + Cargo Broker = 11 subjects); per-section catalog of existing references by source path + identifier; per-section "Named NPCs operating here" list; per-section "Gaps for downstream sprints" subsection; a sub-faction / organization references section.
- A regression checklist of at least 5 distinct existing player-facing behaviors spanning at least 3 different anchor locations.
- A save-state baseline: a documented manual smoke-test recipe (not a binary save file) that a tester can run pre-SA-1 and post-SA-1 to verify no listed behavior regressed.

**Plan.**

1. **Anchor inventory + ID confirmation.** Read `data/galaxy/locations.json`. Cross-reference the 10 anchors named in `station_anchors.md` against actual `unique`-typed location IDs. Note any naming drift between the vision doc and live data. Output: anchor table at the top of `sa_audit_findings.md` with columns (Anchor name from vision, Live `id`, Host system, `location_type`).
   - Files: read `data/galaxy/locations.json`; create `requirements/sa_audit_findings.md` skeleton.
   - Tests: none (research artifact).
   - Risk: vision-doc names like "Restricted Sector 7" may differ from `iron_depths_restricted_zone`. Catalog both forms so later greps do not miss content.

2. **NPC home-mapping table.** Walk `data/characters/npcs.json` and tag each NPC by which anchor they operate at, joining on `home_system_id`. This is the linkage backbone since most anchor references are indirect via NPC speakers. Cross-reference with the SA arc NPC inventory + speaker_id registry that SA-PREP-1 just shipped to `requirements/character_voices.md` so the audit's NPC list aligns with the registry's canonical ids.
   - Files: `data/characters/npcs.json`, `requirements/character_voices.md` (read-only cross-reference) to audit doc.
   - Risk: NPCs with no `home_system_id` should be flagged as `unhomed` so SA-PREP-1's voice-sheet audit triage list (already produced) can be reconciled. Note the `delivery_merchant` to `odom_broker` reconciliation is owned by SA-V; flag it but do not act.

3. **Per-anchor reference walk: dialogue.** For each of the 11 subjects, enumerate dialogue trees that reference the anchor by direct name string OR by a `speaker_id` whose NPC homes at the anchor's system OR via `set_flag`/`requires_flag` patterns mentioning the anchor. Cite using `dialogues.json#tree_id:node_id`.
   - Files: `data/dialogue/dialogues.json`.
   - Gotcha: NPCs may speak from anywhere; mark indirect speaker-based linkage as "speaker home" versus "in-text reference."

4. **Per-anchor reference walk: missions.** Walk all three mission files. Tag references by mission objective `target_id` (NPC at anchor), `available_at` host-system match, or anchor-name strings in `description`/`hint`. Cite as `missions.json#mission_id`.
   - Files: `data/missions/missions.json`, `side_missions.json`, `crew_quests.json`.
   - Gotcha: mission objectives reach systems, not locations. A system match is not necessarily anchor-specific; flag the difference.

5. **Per-anchor reference walk: journal, news, encounters, chatter, ambient.** Walk `data/journal/*.json`, `data/economy/news_templates.json`, `data/encounters/*.json`, `data/crew/station_chatter.json`, `data/crew/ambient_dialogue.json` for anchor-name strings or `system_id` matches.
   - Files: as listed.
   - Gotcha: news templates use placeholders like `{system}`; record which systems can fill them rather than counting templates as direct references.

6. **Sub-faction / organization references audit.** Grep across `data/` and `spacegame/` for: Wreckers' Guild membership concepts, Stellaris Auctioneer relationship, Meridian broker relationships, any other sub-faction tier structures. Document what already exists in code/data so SA-B-EXT-1 knows what to extend versus build from zero.
   - Files: search-only across `data/` and `spacegame/`; output to audit doc's sub-faction section.
   - Gotcha: do NOT design the sub-reputation system here. Catalog only. Designing it is SA-B-EXT-1's scope.

7. **Gaps + expand-vs-preserve per anchor.** For each anchor section, write the "Gaps for downstream sprints" subsection, naming the specific SA sprint that owns the gap (SA-0, SA-1, SA-2, SA-V, SA-R1, SA-P3, SA-P4, SA-P5, SA-B3, SA-B4, SA-F3). Format: "What exists / What sprint X must add / What must be preserved."
   - Files: audit doc.
   - Risk: easy to overstate gaps. Stick to what the data shows. Avoid prescribing solutions; that is the downstream sprint's job.

8. **Regression checklist + save-state baseline.** Write at least 5 player-facing behaviors that must survive SA changes (e.g., "Loading an existing save with `dialogue_flags['met_okafor']=True` continues to show the post-meeting Okafor dialogue branch"). Span at least 3 anchors. Write the save-state baseline as a numbered procedural recipe a tester can run from a clean checkout.
   - Files: audit doc.
   - Gotcha: behaviors must be observable from normal play, not from internal log inspection. Keep them player-facing.

9. **Voice-check + final pass.** Run the three patterns from `tests/test_writing_bible_compliance.py` against the entire `sa_audit_findings.md` text: em-dashes (U+2014, U+2013, ` -- `), banned phrases (`couldn't help but` / `a testament to`), parallel-negation (`no X, no Y`). Zero violations required. Run `pytest -n auto -q` and confirm pass count is at least 8326 (pre-phase baseline). Move sprint to `review`.
   - Files: audit doc; pytest invocation.
   - Gotcha: pre-existing voice violations in the data being audited are OUT OF SCOPE for this sprint. Catalog them in the doc but do not fix; that is downstream content work.
   - Gotcha 2: the audit doc itself uses ASCII double-hyphen ` -- ` only between space-separated tokens (the regex requires surrounding spaces). Inline compound words like `multi-session` are unaffected. When in doubt, prefer a comma or sentence break.

**Acceptance criteria.**
1. `requirements/sa_audit_findings.md` exists and contains a cross-cutting summary table listing all 11 anchor subjects (10 `unique` locations + Cargo Broker character) with reference counts per content surface (dialogue, mission, journal, encounter, ambient/chatter, news).
2. Each anchor subject has its own section listing every existing reference by source path + identifier (e.g., `dialogues.json#okafor_intro:greeting`, `missions.json#deliver_to_torres`), with linkage type noted (in-text name match, speaker home, system_id match, flag chain).
3. Each anchor section includes a "Named NPCs operating here" list (cross-reference for SA-PREP-1).
4. Each anchor section includes a "Gaps for downstream sprints" subsection naming the specific SA sprint(s) that own the gap, in the form "What exists / What sprint X must add / What must be preserved."
5. The sub-faction / organization references section catalogs what exists today for Wreckers' Guild membership, Stellaris Auctioneer relationship, Meridian broker relationships, and any other tier/membership structures, with a note on whether the concept exists in current code/data.
6. The regression checklist enumerates at least 5 distinct player-facing behaviors that SA changes must not break, spanning at least 3 different anchor locations (no single-location concentration).
7. A save-state baseline is included as a documented manual smoke-test procedure (not a binary save file) that a tester can execute pre-SA-1 and post-SA-1 to verify no listed behavior regressed.
8. The audit doc passes the three voice-check patterns from `tests/test_writing_bible_compliance.py` (em-dashes, banned phrases, parallel-negation) with zero violations. Pre-existing violations found in scanned data are documented but out of scope to fix.
9. Full test suite passes at or above the pre-phase baseline of 8326 passing tests; no new failures.

**Risks / open questions.**
- **Locked: audit subject count = 11.** 10 unique-typed anchor locations plus the Cargo Broker character, since SA-V treats the Broker as an anchor-equivalent recurring NPC. Reason: leaving the Broker out would force a parallel mini-audit during SA-V planning.
- **Locked: doc structure = per-anchor sections + cross-cutting summary table at top.** Per-anchor sections give downstream sprint owners a single section to read; the summary table gives the human reviewer a one-screen overview.
- **Locked: voice-check method = run the three regex patterns from `tests/test_writing_bible_compliance.py` against the audit doc text.** Zero violations required. The doc itself does not need a pytest runner; the implementer runs the patterns manually or scripts a one-shot scan during step 9.
- **Locked: save-state baseline = procedural smoke-test recipe, not a binary save file.** Save formats change; binary baselines rot. A documented procedure stays valid across save migrations.
- **Locked: regression checklist = at least 5 behaviors spanning at least 3 anchors.** Prevents "all five behaviors are at Okafor because Okafor has the most existing content."
- **Locked: pre-existing voice violations in scanned data are catalog-only, not fixed in this sprint.** Voice cleanup of pre-SA content is downstream work (likely a future SA-X polish sprint or a WB followup).
- **Locked: per-anchor "Gaps for downstream sprints" subsection required.** Without this, the audit becomes inert reference material; with it, every downstream sprint inherits a concrete starting point.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 17:45 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)
- 2026-04-26 21:22 — harness: plan phase starting
- 2026-04-26 21:26 — planning confirmed; verified all 14 context-to-read paths exist (incl. 11 encounters files); refreshed test-suite baseline (8304 → 8326) in step 9 + acceptance criterion 9 to match SA-PREP-1 done state; added SA-PREP-1 speaker_id-registry cross-reference to step 2; added voice-check tokenization gotcha so the audit-doc author does not trip the ` -- ` regex on inline compound words. No scope expansion, no new sprints proposed. PHASE_OK
- 2026-04-26 21:27 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 — implement: audited all 11 subjects across 10 data surfaces; key finding: all unique anchor location_ids are absent from encounter, dialogue, chatter, ambient, and news data; all references are system-level or speaker-home linkages
- 2026-04-26 — implement: authored requirements/sa_audit_findings.md (640+ lines); 11 per-anchor sections, cross-cutting summary table, sub-faction catalog, 6-behavior regression checklist, 5-step save-state baseline procedure; voice-check clean (zero em-dashes, banned phrases, parallel negation)
- 2026-04-26 — implement: test suite 8326 passed, 98 skipped; no regressions; lint/format n/a (docs-only sprint, no Python files touched). PHASE_OK
- 2026-04-26 21:48 — harness: review phase starting (rework cycle 0)
- 2026-04-26 22:30 — review complete; 2 minor findings fixed directly: (1) lira_feng incorrectly listed at breakstone (homes at forgeworks per npcs.json) -- removed from Section 3 named NPCs list and corrected summary table count 5 to 4; (2) dr_priya_osei (home_system_id=nexus_prime) not mentioned in Section 1 -- added clarifying note. All 9 acceptance criteria verified. Test suite 8326/8326. PHASE_OK
- 2026-04-26 21:54 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 22:15
- Completed: 2026-04-26 22:30
- Files_changed: requirements/sa_audit_findings.md, requirements/roadmap/ROADMAP.md
- Commits: none
- Tests_passing: 8326
- Acceptance_criteria_verified: 9/9
- Polish_items_verified: n/a
- Findings_critical: 0
- Findings_minor_fixed_directly: 2
- Followup_sprints_added: none
- Notes: lira_feng NPC was listed at breakstone but homes at forgeworks; corrected. dr_priya_osei (nexus_prime NPC) was absent from Section 1; clarifying note added. All 9 ACs met; voice clean; test baseline held at 8326.

#### SA-PREP-3 — Playtest baseline telemetry

**Status**: in-progress (planning)
**Phase**: Phase 0 | **Size**: S | **Effort**: 2-3 days
**Depends on**: none | **Blocks**: (informational only — does not block subsequent sprints)

**Goal.** Stand up a minimal, off-by-default telemetry hook that captures pre-arc player behavior at every `unique`-typed anchor card, and write a baseline doc that catalogs what is measurable today (per anchor) vs. what is not. The deliverable is *enabling future comparison* — once the SA arc lands, we will be able to diff "what players do at anchors today" against "what players do at anchors after the arc." External-playtester data collection is a separate effort and out of scope here.

**Context to read.**
- `requirements/station_anchors.md` (per-anchor inventory; the arc-as-a-whole acceptance criteria define what the comparison is against)
- `requirements/onboarding_design.md` (six teaching principles — apply unchanged)
- `spacegame/utils/logger.py` (existing logging surface; the new telemetry module sits beside it, not on top of it)
- `spacegame/views/station_hub_view.py` (where `unique` cards render and accept clicks; the hook lands here, around the `location_type == "unique"` click branch and the detail-panel render path)
- `spacegame/models/player.py` (existing stat counters; `last_interaction_day` and `record_interaction()` are existing measurement surfaces we should *not* duplicate)
- `data/galaxy/locations.json` (the 10 `unique`-typed location IDs the baseline must cover)
- `.gitignore` (`logs/` is already ignored — telemetry output writes under `logs/telemetry/`)

**Touch zones.**
- `requirements/sa_baseline.md` (NEW)
- `spacegame/utils/telemetry.py` (NEW)
- `spacegame/views/station_hub_view.py` (small additions: emit on unique-card click + detail-panel-dwell)
- `tests/test_utils/__init__.py` (NEW, empty)
- `tests/test_utils/test_telemetry.py` (NEW)
- `tests/test_views/test_station_hub_view.py` (extend with telemetry hook coverage)

**Deliverables.**
- `requirements/sa_baseline.md` — per-anchor table covering the 10 `unique` locations plus SA-V's Cargo Broker. For each entry: `anchor_id`, system, current content state (lore-only / has-content / has-campaign-content), at least 3 measurable behaviors with derivation method (Player counter, dialogue flag, telemetry event, JSONL grep, etc.), at least 1 unmeasurable behavior with reason, regression-checklist seed line.
- `spacegame/utils/telemetry.py` — minimal opt-in telemetry module. Off by default; opt-in via `SPACEGAME_TELEMETRY=1`. Writes one JSON object per line to `logs/telemetry/<session_id>.jsonl`. Public API: `is_enabled()`, `record_event(event_type, **payload)`, `current_session_path()`. No-op when disabled (no file is created on import or on disabled `record_event`).
- Telemetry hooks in `station_hub_view.py`: emit `anchor_card_clicked` (payload: `anchor_id`, `system_id`, `game_day`) when a `unique` card is clicked; emit `anchor_detail_dwell` (payload: `anchor_id`, `duration_ms`) when the detail panel closes. Both no-op when telemetry is disabled.
- Test coverage in `tests/test_utils/test_telemetry.py` and an extension to `tests/test_views/test_station_hub_view.py`.

**Acceptance criteria.**
1. `requirements/sa_baseline.md` exists and lists every `unique`-typed location (`nexus_financial_exchange`, `stellaris_auction_house`, `breakstone_deep_mines`, `iron_depths_restricted_zone`, `axiom_research_wing`, `nova_restricted_labs`, `havens_congress_hall`, `verdant_mayors_council`, `crimson_wreckers_guild`, `fulcrum_core`) plus SA-V's Cargo Broker. Each entry names at least 3 measurable behaviors (with derivation method) or marks them unmeasurable with stated reason.
2. `spacegame/utils/telemetry.py` exposes `is_enabled() -> bool`, `record_event(event_type: str, **payload: object) -> None`, and `current_session_path() -> Path | None`. With `SPACEGAME_TELEMETRY` unset or set to `"0"`, all three are no-ops and no file is created.
3. With `SPACEGAME_TELEMETRY=1`, `record_event(...)` appends one JSON object per call to `logs/telemetry/<session_id>.jsonl`. Each line parses with `json.loads`. Each event includes `event_type`, `timestamp_iso`, `session_id`, plus the supplied payload fields.
4. `station_hub_view.py` emits an `anchor_card_clicked` event when a `unique`-typed location card is clicked, AND an `anchor_detail_dwell` event when the detail panel is dismissed by ANY of these paths: (a) detail close button pressed, (b) the player clicks a different `unique` card replacing the open one, (c) the player exits the station hub view (back button or any other navigation) while a detail is open. Both events carry `anchor_id`. Both no-op when telemetry is disabled. Existing click and navigation behavior is unchanged (telemetry is purely additive).
5. New tests in `tests/test_utils/test_telemetry.py` cover: disabled-by-default no-op (no file created), enabled `record_event` writes parseable JSONL, two events append two lines, event schema includes the required fields, non-JSON-serializable payload logs a warning and does not raise, AND a simulated I/O error on append (e.g., output dir is unwritable) logs a warning and does not raise. Tests use `monkeypatch.setenv` and `tmp_path` for isolation.
6. Telemetry-hook tests in `tests/test_views/test_station_hub_view.py` cover: click on `unique` card emits `anchor_card_clicked` with the documented payload; click on a non-`unique` card emits no event; closing the detail panel via the close button emits `anchor_detail_dwell`; clicking a second `unique` card while one detail is open emits `anchor_detail_dwell` for the first anchor; exiting the view (`on_exit`) while a detail is open emits `anchor_detail_dwell`; with telemetry disabled, no events are emitted from any path.
7. Full test suite passes with pass count >= 8326 (the pre-phase baseline as of 2026-04-26). New tests add to the count, not replace existing ones. `ruff format`, `ruff check`, `mypy spacegame/` all clean.

**Risks / open questions.**
- ~~Default state: telemetry on or off by default?~~ **LOCKED** — off by default, opt-in via `SPACEGAME_TELEMETRY=1`. We have no central collection backend, and players running the game from source should not be surprised by behavior tracking.
- ~~Output format: SQLite, JSON-per-event, JSONL, CSV?~~ **LOCKED** — JSONL (one JSON object per line). Append-friendly, parseable line-by-line, no schema migration, easy to grep.
- ~~Output location: where do telemetry files land?~~ **LOCKED** — `logs/telemetry/<session_id>.jsonl`. `logs/` is already gitignored, so no repo pollution. `session_id` format: `YYYYMMDD_HHMMSS_<pid>`.
- ~~Save-state changes: do we add per-anchor counters to `Player`?~~ **LOCKED** — no. Telemetry stays out of the save chain. Existing `last_interaction_day` and `dialogue_flags` already cover save-side measurement; new metrics flow through telemetry only.
- ~~Scope of metrics: which of "click count / time spent / mission acceptance patterns" do we instrument now?~~ **LOCKED** — click count (`anchor_card_clicked`) and detail-panel dwell time (`anchor_detail_dwell`). Both land entirely inside `station_hub_view.py`. Mission-acceptance-by-anchor is deferred — too cross-cutting for an S sprint, would touch the mission pipeline. Re-evaluate during Phase VI if a cohesion sprint needs it.
- ~~Snapshot collection in this sprint: do we ship a captured dataset alongside the doc?~~ **LOCKED** — yes, but only as a "shape demonstration" appendix in the baseline doc: a sample JSONL line captured by the implementer running through one anchor with telemetry on. Not a comprehensive playtester dataset.

**Plan.** (8 tasks, sequenced TDD-first per task)

1. **Anchor inventory + measurement audit (read-only, ~1-2 hours).** Walk `data/galaxy/locations.json` for the 10 `unique` IDs. For each, grep `data/dialogue/`, `data/missions/`, `data/journal/` for existing references (this is *not* SA-PREP-2's full audit — just enough to fill the per-anchor "measurable behaviors" column with what exists today). Identify which `met_npc(...)` or `record_interaction(...)` keys already touch each anchor. Output: outline notes for the `sa_baseline.md` table. *Risk*: SA-PREP-2 (currently blocked) does the deep version. Stay surface-level so we do not pre-empt that sprint's deliverable.

2. **Telemetry module — write failing tests first.** Create `tests/test_utils/__init__.py` (empty) and `tests/test_utils/test_telemetry.py`. Tests: (a) `is_enabled()` returns False with env unset; (b) disabled `record_event` is a no-op (no file created in `tmp_path`); (c) `is_enabled()` returns True with `SPACEGAME_TELEMETRY=1`; (d) enabled `record_event` writes one JSONL line with `event_type`, `timestamp_iso`, `session_id`, and the supplied payload; (e) two `record_event` calls append two parseable lines; (f) non-JSON-serializable payload logs a warning and does not raise. Use `monkeypatch.setenv` and `tmp_path` (override the output dir via a module constant or a constructor arg so tests do not write under repo `logs/`). *Gotcha*: env-var leakage between tests — `monkeypatch.setenv` scopes correctly; bare `os.environ[...]=` does not.

3. **Implement telemetry module.** `spacegame/utils/telemetry.py`. Public API: `is_enabled() -> bool`, `record_event(event_type: str, **payload: object) -> None`, `current_session_path() -> Path | None`. Internals: lazy session_id (`YYYYMMDD_HHMMSS_<pid>`) generated on first enabled write; output dir defaults to `logs/telemetry/`, overridable via env (`SPACEGAME_TELEMETRY_DIR`) or test fixture; JSONL writer opens-appends-closes per event (open-per-event is fine for an S sprint); both serialization errors AND I/O errors (unwritable dir, disk full, permission denied) caught and logged via `spacegame.utils.logger.logger.warning(...)`. MyPy strict; no new dependencies. *Risk*: importing the module must not trigger file I/O. The output directory is created lazily on first enabled write only. A telemetry failure must never crash the game loop or a click handler.

4. **Station hub click hook — write failing test first.** Extend `tests/test_views/test_station_hub_view.py` with a test that constructs the view, simulates a click on a `unique`-typed location card with telemetry enabled (via `monkeypatch.setenv` + `tmp_path` redirect of the output dir), and asserts `anchor_card_clicked` is recorded with `anchor_id`, `system_id`, `game_day`. Add a parallel test asserting no event is recorded when telemetry is disabled. *Gotcha*: existing station-hub tests do not import telemetry — keep imports lazy inside the test to avoid import-order surprises.

5. **Implement click hook in `station_hub_view.py`.** Find the click handler for `unique`-typed location cards (around line 748: `if zone.location.location_type == "unique":`). After the existing branch resolves (whichever branch — open detail panel, navigate, etc.), call `telemetry.record_event("anchor_card_clicked", anchor_id=zone.location.id, system_id=self.system.id, game_day=self.player.game_day)`. Import `telemetry` at module top (cheap import). *Risk*: do not change existing click behavior — telemetry is purely additive. The hook fires regardless of click outcome.

6. **Detail-panel dwell timer — failing tests, then implementation.** Tests cover three dismissal paths: (a) close button (handler at `station_hub_view.py:693`, sets `_detail_location = None` and kills `_detail_close_button`); (b) replacement click (handler at `_activate_zone`, line 748, where a new `unique` card overwrites `_detail_location`); (c) view exit (`on_exit` at line 394 — emit before `_destroy_ui()` so the event still fires when the player navigates away with a detail open). All three tests open a detail panel, advance time via a fake clock or `time.monotonic` patch, trigger the dismissal path, and assert `anchor_detail_dwell` was recorded with the originally-opened `anchor_id` and `duration_ms >= 0`. Implementation: add `_detail_panel_opened_at: Optional[float]` and `_detail_panel_anchor_id: Optional[str]` to the view; set on detail-panel open (line 749); add a private `_emit_detail_dwell_if_open()` helper that emits and clears both fields; call it from each dismissal site. *Gotcha*: replacement-click overwrites `_detail_location` before the new click hook fires — emit dwell for the OLD anchor *before* assigning the new one. Use `_detail_panel_anchor_id` (not the new `_detail_location`) as the source-of-truth so the emitted event names the closed anchor, not the freshly-opened one.

7. **Author `requirements/sa_baseline.md`.** Use the inventory from task 1. Per-anchor table with columns: `anchor_id`, system, content state, measurable-behaviors (with derivation source), unmeasurable-behaviors (with reason), regression seed. Plus a "How to enable telemetry" section (env var + log path + privacy posture). Plus a "Sample event shape" appendix with one captured JSONL line as a demonstration. *Risk*: do not duplicate SA-PREP-2's findings doc — this doc is about *measurement methods*, not *content references*.

8. **Run full validation suite.** `ruff format spacegame/ tests/`, `ruff check spacegame/`, `mypy spacegame/`, `pytest -n auto -q`. Confirm pass count >= 8326 (pre-phase baseline as of 2026-04-26) with new tests added to the count. Append validation lines to Activity log; commit; move Status to `review`.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 18:00 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)
- 2026-04-26 21:55 — harness: plan phase starting
- 2026-04-26 22:35 — plan reconfirmed; folded in 3 polish items (dwell-on-view-exit, dwell-on-replacement-click, telemetry I/O error robustness); split AC into 7 (added explicit hook-coverage AC for station_hub_view tests); refreshed test baseline reference 8304 → 8326. PHASE_OK

**Last phase report.**
- Phase: plan
- Outcome: PHASE_OK
- Started: 2026-04-26 22:30
- Completed: 2026-04-26 22:35
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: pending
- New_sprints_proposed: none
- Polish_items_folded_in: dwell-on-view-exit, dwell-on-replacement-click, telemetry-IO-error-robustness
- Decisions_locked: 6 (reconfirmed from prior recovery cache; no new locks needed)
- Notes: Verified all 7 context targets exist; verified the 10 unique-typed location IDs match locations.json; confirmed no existing tests/test_utils/ directory; confirmed station_hub_view dismissal sites at lines 693 (close button), 749 (replacement), 394 (on_exit). Plan now names each dismissal path with line refs. AC6 split into AC6+AC7 to separate hook-coverage tests from telemetry-module tests. Test baseline refreshed from stale 8304 to current 8326. Scope holds at S; mission-acceptance-by-anchor remains deferred.

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

**Goal.** Extend the reputation model to support per-organization standing layered under per-faction standing. Wreckers' Guild membership tier (apprentice/journeyman/master) is independent of Crimson Reach faction reputation. Stellaris Auctioneer relationship is independent of Stellaris Port faction reputation. Establishes the pattern for SA-1 and SA-B3/B4 to consume. SA-B-EXT-1 ships only the foundation: the `OrganizationConfig` / `OrganizationTier` shape, the `Player.sub_reputation` field, helper APIs, save round-trip, and a tier-promotion notification queue. Concrete organization configs (Wreckers' Guild, Stellaris Auctioneer, etc.) are declared by their owning consumer sprints.

**Context to read.**
- `spacegame/models/player.py` (`faction_reputation`, `_pending_faction_deltas` pattern, `modify_reputation`)
- `spacegame/models/faction.py` (`ReputationTier`, `_TIER_THRESHOLDS`, `get_reputation_tier` — the existing tier pattern this sprint mirrors)
- `spacegame/save_manager.py` (`_player_to_dict`, `_player_from_dict` — `faction_reputation` round-trip path)
- `spacegame/engine/game.py` (`_pending_faction_deltas` drain at line 5399 — model the sub-rep drain on this)
- `requirements/station_anchors.md` (Phase B, plus open question line 253 on save-chain reuse)
- `requirements/si2_dataclass_migration_cookbook.md` (frozen-dataclass requirement for module-level content tables)

**Touch zones.**
- `spacegame/models/sub_reputation.py` (NEW)
- `spacegame/models/player.py` (add `sub_reputation` field, helper methods, notification queue)
- `spacegame/save_manager.py` (round-trip)
- `requirements/sub_reputation_design.md` (NEW — short design doc for downstream consumers)
- `tests/test_models/test_sub_reputation.py` (NEW)

**Deliverables.**
- `requirements/sub_reputation_design.md`: short design doc covering model shape, organization-config registry pattern, notification queue, range/clamping rules, interaction with faction reputation, save chain reuse. Resolves the open question from `station_anchors.md` line 253. Cites the consumer organizations (Wreckers' Guild, Stellaris Auctioneer) as worked examples without authoring their final tier tables.
- `spacegame/models/sub_reputation.py`: `OrganizationTier` (frozen dataclass — `id`, `name`, `rank`, `min_rep`; ordering by `rank`); `OrganizationConfig` (frozen dataclass — `id`, `name`, `tiers: tuple[OrganizationTier, ...]`, `min_rep: int = 0`, `max_rep: int = 100`); `get_tier_for_rep(config, value)` returning the tier whose `min_rep` is the largest still <= `value`; `is_at_least(config, value, tier_id)` for gating; validation in `__post_init__` rejecting empty tier lists, duplicate IDs, non-ascending ranks, or non-ascending thresholds.
- `Player.sub_reputation: dict[str, int]` field with `default_factory=dict`. Helper methods: `modify_sub_reputation(org_id, amount, config) -> tuple[bool, str]` (clamps to `[config.min_rep, config.max_rep]`, queues a `SubReputationDelta(org_id, effective_amount, old_tier, new_tier)` on `_pending_sub_rep_deltas` whenever the tier changes); `get_sub_reputation(org_id) -> int` (defaults to 0); `get_sub_reputation_tier(org_id, config) -> OrganizationTier` (computes tier from current value); `is_at_least_tier(org_id, tier_id, config) -> bool`. Mirrors `_pending_faction_deltas` lifecycle — non-serialized list, drained per-frame by consumer views.
- Save round-trip in `save_manager.py`: `"sub_reputation": player.sub_reputation` written; `player.sub_reputation = data.get("sub_reputation", {})` read with default-empty for legacy saves.
- Tests in `tests/test_models/test_sub_reputation.py` covering: config validation, tier lookup at edges, tier promotion/demotion notification queueing, sub-rep faction-rep orthogonality, helper APIs, save round-trip, legacy-save loading. Three organization shapes exercised: a 3-tier Wreckers'-shape (apprentice / journeyman / master), a 4-tier Stellaris-shape, and a 1-tier minimal config.

**Acceptance criteria.**
1. `OrganizationConfig` rejects empty tiers, duplicate tier IDs, non-ascending ranks, and non-ascending `min_rep` thresholds in `__post_init__`. Tested with an explicit failure case for each.
2. `get_tier_for_rep(config, value)` returns the correct tier at every threshold edge (boundary above and at the threshold) and at `config.min_rep` / `config.max_rep`.
3. `OrganizationTier.__ge__` / `__lt__` compare by `rank` so "is at least journeyman" gates work without consumers reaching into internals.
4. `Player.modify_sub_reputation(org_id, amount, config)` clamps to `[config.min_rep, config.max_rep]` and returns `(success, message)` per project convention. Effective delta after clamping is what's reported in the message.
5. Crossing a tier threshold upward or downward appends a `SubReputationDelta(org_id, effective_amount, old_tier, new_tier)` entry to `Player._pending_sub_rep_deltas`. No-tier-change modifications do not queue.
6. Modifying `sub_reputation` for one organization does not modify `faction_reputation` for any faction, does not modify `sub_reputation` for any other organization, and `modify_reputation(faction_id, ...)` does not touch `sub_reputation`. Tested explicitly.
7. `get_sub_reputation(org_id)` returns 0 when the organization is absent from `sub_reputation`. `get_sub_reputation_tier(org_id, config)` returns the lowest tier when absent (consumers gate "engaged vs. unengaged" via their own state, not sub-rep). `is_at_least_tier(org_id, tier_id, config)` returns False when the tier is unknown to the config (does not raise).
8. Save/load round-trip preserves `sub_reputation` values across `_player_to_dict` -> `_player_from_dict`. A populated three-organization dict survives the round-trip with all values intact.
9. Saves missing the `sub_reputation` key load with `player.sub_reputation == {}`. No crash. No warning that breaks tests.
10. The notification queue (`_pending_sub_rep_deltas`) is NOT serialized — round-tripping a player drops the queue (matches `_pending_faction_deltas` precedent).
11. Tests cover at least 3 organizations with different tier structures (1-tier, 3-tier, 4-tier).
12. `ruff format`, `ruff check`, `mypy` clean. Full test suite green at >= 8304 passing (pre-phase baseline).

**Plan.**
1. **Author `requirements/sub_reputation_design.md`** (~30 minutes). Short design doc. Sections: (a) what sub-reputation is and isn't (per-organization standing; not a parallel faction system, not a lockout mechanism, not auto-tied to faction-rep gain), (b) the `OrganizationConfig` / `OrganizationTier` shape, (c) the registry pattern (consumer sprints declare their own configs in their own modules — SA-1 declares the Wreckers' Guild config in `spacegame/models/wreckers_guild.py`), (d) range and clamping rules (0-100 default; configurable), (e) notification queue contract for downstream views, (f) save chain (reuses Player serialization — single `sub_reputation` dict field, no separate save manager), (g) two worked examples shown as illustrative configurations (Wreckers' 3-tier, Stellaris 4-tier) explicitly marked "owned by SA-1 / SA-B3 — not implemented in this sprint." Resolves `station_anchors.md` line 253. Touches: `requirements/sub_reputation_design.md` (NEW). Tests: none (doc-only).

2. **Write failing tests for `sub_reputation` model surface** (TDD red). `tests/test_models/test_sub_reputation.py`. Assert: (a) `OrganizationTier` is a frozen dataclass and orderable by `rank`; (b) `OrganizationConfig.__post_init__` rejects empty tiers, duplicate tier IDs, non-ascending ranks, non-ascending `min_rep`; (c) `get_tier_for_rep` returns the correct tier across edges (including value below the lowest threshold returns the lowest tier, value at `max_rep` returns the highest tier, value at exactly each threshold returns that threshold's tier); (d) `is_at_least` returns False for unknown tier IDs and True/False correctly otherwise. Touches: tests only. Risk: getting the lowest-tier-when-below-threshold semantics right — document and assert explicitly.

3. **Implement `spacegame/models/sub_reputation.py`** (TDD green). Define `OrganizationTier`, `OrganizationConfig`, `SubReputationDelta` (the notification record — frozen dataclass with `org_id`, `effective_amount`, `old_tier`, `new_tier`), `get_tier_for_rep`, `is_at_least`. All three model dataclasses are `@dataclass(frozen=True)` per the SI-2 cookbook. Validation in `__post_init__` raises `ValueError` with descriptive messages. Touches: `spacegame/models/sub_reputation.py` (NEW). Tests: from step 2 turn green.

4. **Write failing tests for `Player.modify_sub_reputation` and helpers** (TDD red). Continue `test_sub_reputation.py`. Assert: (a) new player has `sub_reputation == {}`; (b) `modify_sub_reputation` clamps, returns `(True, message)`, sets the dict entry; (c) tier-up appends a `SubReputationDelta` to `_pending_sub_rep_deltas`; (d) tier-down appends; (e) no-tier-change modifications do not append; (f) modifying sub-rep does not touch `faction_reputation`; (g) calling `modify_reputation` does not touch `sub_reputation`; (h) `get_sub_reputation` defaults to 0; (i) `get_sub_reputation_tier` returns the lowest tier when absent; (j) `is_at_least_tier` returns False for unknown tier_id, correct bool otherwise. Touches: tests only. Risk: clamping at exactly `max_rep` should not queue a no-op delta — pin the behavior.

5. **Implement Player helpers** (TDD green). Add `sub_reputation: dict[str, int] = field(default_factory=dict)` next to `faction_reputation` in `spacegame/models/player.py`. Add `modify_sub_reputation`, `get_sub_reputation`, `get_sub_reputation_tier`, `is_at_least_tier`. Mirror `modify_reputation`'s shape exactly: clamp, compute effective delta, write back, conditionally append to `_pending_sub_rep_deltas` (lazily-initialized non-serialized list, same pattern as `_pending_faction_deltas`). Touches: `spacegame/models/player.py`. Tests: from step 4 turn green.

6. **Write failing tests for save round-trip** (TDD red). `test_sub_reputation.py`. Build a player, set sub-rep on three organizations using synthetic configs, run through `SaveManager._player_to_dict` -> `_player_from_dict`, assert all three preserved. Build a save dict missing the `sub_reputation` key, run through `_player_from_dict`, assert `player.sub_reputation == {}`. Build a player, queue notifications via `modify_sub_reputation`, run through round-trip, assert the queue is reset to empty (notification queue is ephemeral). Touches: tests only. Risk: the save-manager test path has many required fixture fields — use the existing helper convention from `test_save_roundtrip.py` if applicable, otherwise inline the minimal fixture.

7. **Implement save/load round-trip** (TDD green). In `spacegame/save_manager.py`: add `"sub_reputation": player.sub_reputation` to `_player_to_dict` next to `"faction_reputation"`. Add `player.sub_reputation = data.get("sub_reputation", {})` to `_player_from_dict` next to the corresponding faction-rep load. Touches: `spacegame/save_manager.py`. Tests: from step 6 turn green.

8. **Run lint, format, type-check, full test suite**. `ruff format spacegame/ tests/`, `ruff check spacegame/ --fix`, `mypy spacegame/`, `pytest -n auto -q`. Confirm pass count >= 8304 and skip count == 98. If any pre-existing failure surfaces unrelated to this sprint, note in Activity log but do not chase. Touches: none (validation step).

9. **Update Status to `review` and append phase report**. Move `Status` from `in-progress` to `review`. Append the `**Last phase report.**` block per agent convention. Commit with `SA-B-EXT-1: ...` prefix.

**Risks / open questions.**

The following decisions were locked during planning:

- ~~Save chain: separate save manager vs. reuse Player chain~~. **LOCKED**: reuse Player chain. Single `sub_reputation: dict[str, int]` field on `Player`, serialized inside `_player_to_dict` next to `faction_reputation`. Rationale: zero migration risk; matches `faction_reputation`'s precedent exactly; consumers don't need to learn a new save mechanism. Resolves `station_anchors.md` line 253.
- ~~Reputation range (negatives allowed for blacklist?)~~. **LOCKED**: 0-100 default with per-config `min_rep` / `max_rep`. No negatives in v1. Rationale: SA-1's failed-contract lockout already lives on a separate `wreckers_guild_state.lockout_until_day` field per the SA-1 risks list. Sub-rep is membership progression; lockouts are time-windowed bans. Conflating them muddies both. If a consumer sprint later wants negative ranges (such as "blacklisted Stellaris bidder"), they configure `min_rep = -50` on their own config — the foundation already supports it.
- ~~Configuration source (JSON vs. Python dataclasses)~~. **LOCKED**: Python frozen dataclasses (`@dataclass(frozen=True)`) per the SI-2 dataclass migration cookbook. Same precedent as the skill system (`create_default_skills()` in `progression.py`, no JSON). Rationale: organization tier tables are content tied to game-design constants, not user-editable data; Scanner B requires frozen dataclasses for module-level content; mirrors the established pattern.
- ~~Where do organization configs live~~. **LOCKED**: registry pattern. SA-B-EXT-1 ships zero concrete configs. Consumer sprints (SA-1 declares Wreckers' Guild in `spacegame/models/wreckers_guild.py`; SA-B3 declares Stellaris Auctioneer in `spacegame/models/bidding.py` or a sibling; SA-B4 reuses SA-1's config). Tests in this sprint use synthetic configs created inline. Rationale: keeps SA-B-EXT-1 truly foundational; avoids prematurely committing tier names that the narrative sprints should own.
- ~~Default tier for an organization not yet in `sub_reputation`~~. **LOCKED**: `get_sub_reputation` returns 0; `get_sub_reputation_tier` returns the lowest tier (whose `min_rep <= 0`). Consumers that need an "engaged vs. unengaged" distinction track that on their own state (e.g., SA-1's `wreckers_guild_state["enrolled"]`). Rationale: separating "is the player a member?" from "what's the player's standing?" lets each consumer decide its onboarding flow without sub-rep semantics dictating it.
- ~~Notification queue contract~~. **LOCKED**: `_pending_sub_rep_deltas: list[SubReputationDelta]` on Player, lazily initialized, NOT serialized. Drained by consumer views per frame, mirroring the `_pending_faction_deltas` pattern in `engine/game.py:5399`. Rationale: the existing pattern works; downstream venues (SA-1 wreckers view, SA-B3 auction view) can drain it the same way without learning a new mechanism.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 18:14 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)

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
**Source**: Living Universe Arc deferral; `requirements/living_universe_arc.md` Phase 5 design carries the as-imagined CB scope.
**Size**: S | **Effort**: 3-5 days
**Depends on**: none | **Blocks**: CB-2

**Goal.** Lock the scope of the CB Crew Banter sprint. CB has been deferred without architectural decisions; this sprint produces `requirements/cb_scope.md`, a design contract that tells CB-2 exactly what to build, how it relates to existing crew dialogue infrastructure, where it ends and SA-X6 begins, and what the authoring quota is. The doc is the planning artifact CB-2 plans against.

**Context to read.**
- `requirements/living_universe_arc.md` — Phase 5 (CB) section, lines ~793-940. The originally-designed CB architecture (BanterEntry, BanterTrigger, BanterEngine, Ship Log menu, sub-sprint breakdown CB-1 through CB-9). Treat as the maximalist starting point; CB-1 trims it to a shippable contract.
- `requirements/character_voices.md` — voice sheets for Elena, Marcus, Priya, Tomas. Sample entries authored in this sprint must pass these voice rules.
- `requirements/station_anchors.md` — SA-X6 description (line ~197) and the cohesion claim (line ~228, "Without crew reactions, the player navigates anchor systems alone"). Determines CB / SA-X6 boundary.
- `data/crew/ambient_dialogue.json` — 224 existing ambient lines (home_system / faction_territory / idle / inter_crew / player_action). Note: the original sprint listed `data/crew/banter.json`, which does not exist; the existing crew-banter content lives in `ambient_dialogue.json` and is managed by `AmbientDialogueManager`. The absence of `banter.json` is itself a finding for the scope doc.
- `spacegame/models/ambient_dialogue.py` — `AmbientLine` and `AmbientDialogueManager`. The existing engine. Decision: extend it, or replace it.
- `spacegame/engine/game.py` — points where ambient_dialogue fires (warp, idle counter, player_action). Lines ~328, ~536, ~1080-1110, ~3192-3201, ~4370-4380.
- `requirements/onboarding_design.md` — six-principle framing; banter must obey "voice-check everything" (principle 6).

**Touch zones.**
- `requirements/cb_scope.md` (NEW)

**Deliverables.**
- `requirements/cb_scope.md`, ~1000-1800 words, with the eight sections enumerated in the acceptance criteria.
- 3-5 sample banter entries (in the locked schema) embedded in the doc as voice-checked exemplars.

**Acceptance criteria.**
1. **Current Coverage section** enumerates crew banter that exists today: speaker by context tabulation derived from `data/crew/ambient_dialogue.json`, plus a one-line description of `AmbientDialogueManager`'s selection / cooldown / save-state semantics. Include line-of-evidence pointers (file path, key class, key methods).
2. **Gap Analysis section** maps each Living Universe Arc Phase 5 trigger type — `destination`, `crew_pair`, `flag`, `combat_after`, `rival_seen`, `idle` — to existing coverage as **covered / partial / missing**, with a one-sentence justification each.
3. **Architecture Decision section** locks one of: (A) extend `AmbientDialogueManager` with new context types and trigger fields; (B) introduce `BanterEntry` / `BanterEngine` per Phase 5 design, deprecating `AmbientDialogueManager`; or (C) sister-system that shares the data file. Rationale must address save-migration cost, the 224 existing entries, scanner integration, and CB-2 implementation complexity.
4. **SA-X6 Boundary section** explicitly states whether SA-X6 is (a) a subset of CB-2 (anchor-specific trigger category), (b) a sibling sprint that runs after CB-2 ships infrastructure, or (c) merged into CB-2 with SA-X6 retired. The `data/crew/banter.json` reference in SA-X6's touch zones must be reconciled (renamed or annotated).
5. **CB-2 Authoring Quota section** specifies minimum entry counts per trigger type (e.g., destination >= 20, crew_pair >= 15, flag >= 10, combat_after >= 5, idle >= 10). Quota becomes CB-2's acceptance bar.
6. **Sample Entries section** includes 3-5 banter entries written in the locked schema, voice-checked against `requirements/character_voices.md` and the Writing Bible (no em-dashes, no banned phrases, no parallel-negation rhetoric). These exemplars prove the locked schema is workable in practice.
7. **Test Surface section** specifies which test files CB-2 will add or extend, and what each asserts (eligibility evaluation, cooldown, voice consistency, scanner coverage of new content file, speaker_id resolution, save round-trip).
8. **Recommendation section** picks one of: fold-into-SA-X6, run-parallel-with-SA-X6, defer-indefinitely. Includes a one-paragraph justification grounded in the architecture decision and the SA-X6 boundary.

**Plan.**

1. **Catalog current banter coverage.** Read `data/crew/ambient_dialogue.json` end-to-end. Tabulate by `crew_id` x `context`. Note the 224 lines split across 5 contexts. Confirm `station_chatter.json` is non-crew (NPC overheard / announcement / atmosphere) and `crew_members.json` is metadata only. Output: Current Coverage section.
   - Touches: read-only on `data/crew/*.json` and `spacegame/models/ambient_dialogue.py`. No tests at this step.
   - Risk: tabulation must match the file exactly. Use a small Python one-liner or the data_loader rather than eyeballing.

2. **Gap-map against Phase 5.** For each Living Universe Arc Phase 5 trigger type, classify existing coverage. Expected mapping: `destination` (partial, since `home_system` and `faction_territory` overlap, but per-destination weighting is missing), `crew_pair` (partial, since `inter_crew` exists but lines are single-speaker, not multi-line dialogues), `flag` (missing, no dialogue_flag conditions), `combat_after` (missing, no combat-recency trigger), `rival_seen` (missing, no rival/RC integration), `idle` (covered).
   - Touches: read-only.
   - Risk: don't over-catalog. The point is CB-2's gap surface, not a complete audit of every line.

3. **Lock architecture decision (extend vs. new vs. sister).** Recommended posture: option **A (extend)**. Rationale: zero save-migration cost; preserves 224 voice-checked lines; the existing manager already serializes shown_indices and integrates at warp/idle/player_action; new contexts are additive (`destination_system`, `crew_pair_dialogue`, `flag_triggered`, `combat_after`, `rival_zone`); the doc commits to extending `AmbientLine` with optional fields rather than introducing a parallel data model. Document trade-offs.
   - Touches: drafts the Architecture Decision section. Reads `spacegame/models/ambient_dialogue.py` and `spacegame/engine/game.py` to confirm extension feasibility.
   - Risk: option A constrains CB-2 to a single-speaker line model. If multi-line crew_pair dialogues are non-negotiable, option C (sister-system, shared data file) is the fallback. The doc must document this fallback and the trigger that would force the switch.

4. **Resolve SA-X6 boundary.** Re-read SA-X6 (line ~1520 in this file). Recommend: SA-X6 stays as a sibling sprint, but its touch zone `data/crew/banter.json` must be reconciled. Either rename to `data/crew/ambient_dialogue.json` (if option A locks) or update to whatever data file the locked architecture produces. The scoping doc surfaces this as a follow-up note for SA-X6's planner; CB-1 does NOT modify SA-X6.
   - Touches: drafts the SA-X6 Boundary section. Reads ROADMAP.md SA-X6 section read-only.
   - Risk: agent must NOT edit SA-X6. That's another sprint's section. Surface the reconciliation as a note in cb_scope.md.

5. **Set CB-2 authoring quota.** Recommended starting numbers: destination >= 20, crew_pair >= 15, flag >= 10, combat_after >= 5, idle >= 10 (total >= 60, matches Phase 5's "40-60 entries at launch"). Lock the per-category floors so CB-2 cannot ship 50 idle lines and call it done.
   - Touches: drafts the CB-2 Authoring Quota section.

6. **Write 3-5 sample banter entries.** One per crew member with at least one crew_pair dialogue. Each must pass character_voices.md (read voice sheets for tonal alignment) and the Writing Bible (no em-dashes, no "couldn't help but," no "no X, no Y," no banned NPC names). Include the entries in the doc with the locked schema's field structure visible.
   - Touches: drafts the Sample Entries section.
   - Risk: voice fidelity. Re-read each character's voice sheet sample lines before drafting. If any sample line would fail the writing bible scanner, it does not belong in the scope doc.

7. **Specify CB-2's test surface.** List the test files: `tests/test_models/test_ambient_dialogue.py` (extend with new context evaluation tests), `tests/test_writing_bible_compliance.py` (confirm the existing or new file is in the scan list), `tests/test_data/test_dialogue_integrity.py` (speaker_id and flag-id resolution tests for new entries), `tests/test_models/test_player.py` (save round-trip for any new state). Note that no NEW test file is needed if option A locks.
   - Touches: drafts the Test Surface section.

8. **Lock the recommendation.** Pick run-parallel as the default if architecture option A locks (CB-2 ships engine extensions and ~60 lines of general banter; SA-X6 reduces to ~25-40 lines of anchor-specific banter using CB-2's extended infrastructure). Defer fold-into-SA-X6 unless there's a strong cohesion argument; defer-indefinitely is rejected as it leaves the Phase 5 vision unimplemented.
   - Touches: drafts the Recommendation section.

9. **Compose `requirements/cb_scope.md` end-to-end.** ~1000-1800 words. Run a self-check against all 8 acceptance criteria before the agent moves to review. Voice-check the sample entries one more time.
   - Touches: writes `requirements/cb_scope.md` (NEW).
   - Risk: doc length sprawl. Each section should be tight. Bullets and short paragraphs over prose.

**Risks / open questions.**

The following decisions were locked during this planning phase. The implementer follows them; the reviewer can challenge them.

- ~~Should the missing `data/crew/banter.json` reference block planning?~~ **LOCKED**: no. The file's absence is the current state. The scoping doc records it as a finding and the existing content lives in `ambient_dialogue.json`. The original Context-to-read entry has been corrected.
- ~~Is the scoping doc just enumeration, or does it pre-lock architecture for CB-2?~~ **LOCKED**: pre-locks architecture. The doc IS the design contract for CB-2. Without architectural commitment, CB-2 will defer again.
- ~~Should the doc include sample entries, or only describe them?~~ **LOCKED**: sample entries required (3-5, voice-checked). Paper designs hide voice-fidelity risk; sample entries surface it.
- ~~Should CB-2 quotas be set in CB-1 or by CB-2's own planner?~~ **LOCKED**: set in CB-1, per-category. Without floor numbers, CB-2 can ship a tiny content drop and claim acceptance.
- ~~Is SA-X6 a CB-2 subset, sibling, or merge target?~~ **LOCKED**: sibling, with the scope doc surfacing the touch-zone reconciliation as a follow-up for SA-X6's planner. CB-2 ships infrastructure plus general banter; SA-X6 authors anchor-specific lines using that infrastructure.

Open question (reviewer judgment, not blocking implementation):
- Architecture preference is option A (extend `AmbientDialogueManager`). Implementer may flip to option C (sister-system, shared data file) if the multi-line crew_pair dialogue requirement turns out non-negotiable while writing the sample entries. The doc must document whichever option locks and the trade-off the implementer evaluated.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 18:25 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)

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

**Goal.** Extend the Writing Bible compliance scanner to cover station tagline strings. Currently `faction_tagline = "..."` class attributes in `station_layouts.py` are invisible to the scanner because the regex only matches `.render("literal")` calls, not variable references. Five faction tagline strings — Guild, Union, Collective, Frontier, Reach — must enter the scanner's coverage so future authors can't introduce em-dashes, banned phrases, or comma-form parallel-negation rhetoric without a test failure.

**Context to read.**
- `requirements/writing_bible_scanner_gaps.md`
- `tests/test_writing_bible_compliance.py`
- `spacegame/views/station_layouts.py`

**Touch zones.**
- `tests/test_writing_bible_compliance.py` (add `_extract_tagline_strings` + tests)

**Deliverables.**
- New extractor `_extract_tagline_strings()` pulling `faction_tagline` from every `StationLayout` subclass via `__subclasses__()`. Empty taglines (the base-class default `""`) are skipped.
- New `TestStationTaglineWritingBible` class with 4 tests: em-dashes, banned phrases, parallel-negation (using `_find_violations()` so the existing allowlist is honored), and a coverage-sanity test that asserts >= 5 taglines are extracted (so silent drift to zero fails the suite).
- The 5 currently-defined taglines remain clean under the existing rules; no production strings change.

**Acceptance criteria.**
1. `_extract_tagline_strings()` returns one `(loc, text)` entry per non-empty `faction_tagline` declared on a `StationLayout` subclass; the extractor ignores the base-class `""` default and any future subclass that omits an override.
2. `TestStationTaglineWritingBible.test_no_em_dashes_in_taglines` would fail if any tagline contained an em-dash, en-dash, or `" -- "`. (Verify by temporarily injecting an em-dash into a subclass and confirming the test fails; revert.)
3. `TestStationTaglineWritingBible.test_no_banned_phrases_in_taglines` would fail if any tagline contained `"couldn't help but"` or `"a testament to"`.
4. `TestStationTaglineWritingBible.test_no_parallel_negation_in_taglines` flags comma-form parallel-negation taglines, but the existing `_PARALLEL_NEGATION_ALLOWLIST` (containing the Reach tagline) still suppresses any allowlisted entry — confirmed by a small unit test that asserts `_find_violations("No laws. No mercy. No refunds.")` returns no parallel-negation entry, and that `_find_violations("No laws, no mercy.")` (a synthetic non-allowlisted string) does flag it.
5. `TestStationTaglineWritingBible.test_tagline_scanner_finds_content` asserts `len(_extract_tagline_strings()) >= 5` so removal of the extractor or accidental import failure surfaces immediately.
6. `python -m pytest -n auto -q tests/test_writing_bible_compliance.py` passes; full suite stays at >= 8304 passing.

**Risks / open questions.**
- ~~Discovery method: `__subclasses__()` introspection vs. hardcoded import list vs. AST parsing.~~ **Locked**: use `StationLayout.__subclasses__()` so future faction layouts are auto-discovered without touching the test file. The trade-off (subclasses must be imported before introspection runs) is satisfied by importing `spacegame.views.station_layouts` at extractor-call time.
- ~~Allowlist enforcement in the new parallel-negation test: call `_find_violations()` (which honors the allowlist) or call `_PARALLEL_NEGATION.search()` directly?~~ **Locked**: use `_find_violations()` for the violation tests, mirroring the function the rest of the scanner relies on. This keeps the allowlist honored consistently and makes the test forward-compatible with WB-2's regex broadening.
- ~~Empty-tagline handling: should the extractor emit the base-class `""` default?~~ **Locked**: skip empty/whitespace-only taglines so the scanner doesn't emit spurious zero-length entries. Subclass authors who *want* a blank-display layout can opt out by setting `faction_tagline = ""` (the current base-class default), and the scanner correctly skips them.
- Nothing genuinely open. Sprint is implementation-ready.

**Plan.**
1. **Add the failing coverage-sanity test** in `tests/test_writing_bible_compliance.py`. Create `TestStationTaglineWritingBible` class with `test_tagline_scanner_finds_content` that calls `_extract_tagline_strings()` and asserts `len(...) >= 5`. The function does not exist yet so the test fails on `NameError`. (Risk: the test file's other tests must remain importable — make sure the new class sits at the end of the file, after the existing `TestCoverageSanity` block.)
2. **Implement `_extract_tagline_strings()`**. Import `spacegame.views.station_layouts` (which transitively imports pygame + fonts; this matches the pattern used by other extractors). Walk `StationLayout.__subclasses__()`, for each subclass read `cls.faction_tagline`, skip if `not tagline.strip()`, append `(f"tagline:{cls.__name__}", tagline)` to the result list. Return the list. Coverage-sanity test now passes. (Gotcha: `__subclasses__()` returns only directly-imported subclasses; importing `spacegame.views.station_layouts` triggers all five class definitions to register, so this works in the test environment.)
3. **Add the three violation tests.** Mirror the pattern of `TestViewSourceWritingBible` but against `_extract_tagline_strings()`:
   - `test_no_em_dashes_in_taglines` — direct `if any(d in text for d in _EM_DASHES)` check.
   - `test_no_banned_phrases_in_taglines` — direct `if phrase in text.lower()` loop.
   - `test_no_parallel_negation_in_taglines` — call `_find_violations(text)` and inspect for the parallel-negation entry; this honors the allowlist.
   All three pass against current content (Guild/Union/Collective/Frontier/Reach taglines are clean under the existing comma-only regex; Reach tagline is also explicitly allowlisted). Test surface: `tests/test_writing_bible_compliance.py::TestStationTaglineWritingBible`.
4. **Add the allowlist-honored unit test.** Inside the same class, add `test_allowlist_suppresses_reach_tagline` that calls `_find_violations("No laws. No mercy. No refunds.")` and asserts the result contains no parallel-negation entry, then calls `_find_violations("No laws, no mercy.")` (a synthetic non-allowlisted string in comma form) and asserts the result *does* contain a parallel-negation entry. This pins both the allowlist behavior and the regex behavior in a single unit test, satisfying acceptance #4 today and forward-defending against WB-2's regex broadening.
5. **Manual injection check (verifies acceptance #2 + #3).** Temporarily edit `GuildDeckLayout.faction_tagline` to include an em-dash. Run `pytest tests/test_writing_bible_compliance.py::TestStationTaglineWritingBible -q`. Confirm `test_no_em_dashes_in_taglines` fails with a clear offender report. Revert. Repeat with a banned phrase. Note the result in the Activity log so the implementation phase has evidence the tests bite.
6. **Run full suite.** `python -m pytest -n auto -q`. Confirm pass count stays at >= 8304 and no new failures. Lint with `ruff check tests/test_writing_bible_compliance.py` and format with `ruff format tests/test_writing_bible_compliance.py`. Commit with sprint ID in the message.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 18:36 — plan phase ran in pilot but blocked by sandbox; planning content recovered from agent stdout and applied to this sprint section
- 2026-04-26 — plan content recovered; ready for re-pickup by harness (next plan phase will see substantive existing plan and confirm/refine)

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
