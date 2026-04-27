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
| [SA-PREP-3](#sa-prep-3--playtest-baseline-telemetry) | Playtest baseline telemetry | 0 | S | done | none |
| [SA-A1](#sa-a1--crew-specialization-design) | Crew specialization design | A | S | done | SA-PREP-2 |
| [SA-A2](#sa-a2--crew-template-implementation) | Crew template implementation | A | M | done | SA-A1 |
| [SA-B-EXT-1](#sa-b-ext-1--sub-reputation-system) | Sub-reputation system | B | M | done | none |
| [SA-C1](#sa-c1--skill-tree-extension-design) | Skill tree extension design | C | S | done | SA-PREP-2 |
| [SA-C2](#sa-c2--skill-tree-extension-implementation) | Skill tree extension implementation | C | M | done | SA-C1 |
| [SA-0](#sa-0--cluster-a-confirmation-pass) | Cluster A confirmation pass | I | S | done | SA-PREP-2 |
| [SA-1](#sa-1--wreckers-guild-hall-salvage-contracts) | Wreckers' Guild Hall (Salvage Contracts) | I | L | done | SA-PREP-1, SA-A2, SA-B-EXT-1 |
| [SA-2](#sa-2--deep-shafts-memorial--pilgrimage) | Deep Shafts memorial / pilgrimage | I | L | done | SA-PREP-1 |
| [SA-V](#sa-v--cargo-broker-arc--investment-introduction) | Cargo Broker arc + Investment Introduction | I | M | done | SA-PREP-1 |
| [SA-P1](#sa-p1--politics-system-design) | Politics System Design | II | M | done | SA-PREP-1, SA-C2 |
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

**Status**: done
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
- 2026-04-26 22:00 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 — telemetry module implemented + 14 tests green (da4011c)
- 2026-04-26 — station_hub_view click + dwell hooks implemented + 7 new tests green (8591f03)
- 2026-04-26 — sa_baseline.md authored (all 10 unique anchors + SA-V covered) (c8e134e)
- 2026-04-26 — full suite 8347 passed (baseline 8326, +21 new tests); all gates green. PHASE_OK
- 2026-04-26 22:13 — harness: review phase starting (rework cycle 0)
- 2026-04-26 — review complete; 1 minor finding fixed directly (missing disabled-dwell test for AC 6 "any path" coverage); all 7 ACs verified; 8348 passing (+22 vs baseline). PHASE_OK
- 2026-04-26 22:22 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 22:13
- Completed: 2026-04-26 23:45
- Files_changed: tests/test_views/test_station_hub_view.py
- Commits: de141ea
- Tests_passing: 8348
- Acceptance_criteria_verified: 7/7
- Polish_items_verified: 3/3
- Findings_critical: 0
- Findings_minor_fixed_directly: 1
- Followup_sprints_added: none
- Notes: AC 6 required "no events from any path when disabled" — implementer covered click-disabled but not dwell-disabled. Added test_dwell_no_event_when_telemetry_disabled directly. All other ACs met cleanly: telemetry module mypy-clean (0 new errors introduced), sa_baseline.md covers all 10 unique anchors + SA-V with correct schema, all 3 dwell dismissal paths wired and tested.

### Phase A — Crew Specialization Extension

#### SA-A1 — Crew specialization design

**Status**: done
**Phase**: Phase A | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: SA-A2

**Goal.** Lock the crew-specialization set that SA arc systems require to "feel right" (per `station_anchors.md` Phase A: "Bidding crew can read other bidders, Politics crew can sway delegates"). Produce a design doc that names each specialization, defines its `bonus_type` strings and magnitude ranges, identifies the anchor system(s) and consuming sprint(s) it integrates with, and decides for each one whether to extend an existing crew template or author a net-new one. The doc is the single source of truth that SA-A2 implements against and that SA-1 / SA-P / SA-B / SA-R / SA-F consume from when their views call `get_bonus(...)`. No code in this sprint.

**Context to read.**
- `requirements/station_anchors.md` (Phase A section + integration commitments per system; Decision 3 — "extend existing trees" — anchors the bonus_type-string convention)
- `requirements/sa_audit_findings.md` (especially "Sub-Faction and Organization References" + "Current Reputation Architecture": tells us what does NOT exist yet, so the design doesn't assume infrastructure SA-A2 cannot lean on)
- `requirements/character_voices.md` lines 573-637 (SA-PREP-1 NPC inventory + speaker_id registry; new specialist crew must register here to keep the inventory canonical)
- `requirements/onboarding_design.md` (six teaching principles — apply unchanged to specialist crew introductions)
- `data/crew/crew_members.json` (existing templates; verify naming and bonus_type collisions before locking new strings)
- `spacegame/models/crew.py` (CrewTemplate dataclass + CrewRoster.get_bonus aggregation; companion vs. non-companion behavior at lines 277-289)
- `spacegame/models/progression.py` (existing skill IDs and bonus_type strings; the `negotiator` skill ID at line 385 collides with the vision's "Negotiator" label and forces a renaming decision)
- `CLAUDE.md` (Skill System section — bonus_type discipline; Cross-Cutting Concerns table — crew abilities row)

**Touch zones.**
- `requirements/sa_crew_design.md` (NEW)
- `requirements/character_voices.md` (extend the SA-PREP-1 inventory table + speaker_id registry with one row per net-new specialist crew; do not modify any other section)

**Deliverables.**
- `requirements/sa_crew_design.md` covering, in this order:
  1. Specialization roster (one block per specialization: name, role label, target anchor system(s), `home_system_id` and `faction_id` candidates, persona seed of 3-5 sentences for SA-A2's voice sheet).
  2. Bonus-naming convention table (every new `bonus_type` string the SA arc will consume, with description, magnitude range, intended consumer view file(s), and a note on whether it is read via `crew_roster.get_bonus()`, `progression.get_bonus()`, or both).
  3. Cross-reference matrix: specialization → consuming SA sprint(s) → consuming view file(s) → integration mechanism (one row per specialization).
  4. Decisions-locked section restating the resolved open questions with rationale.
  5. Save-migration note explicitly confirming whether new bonus_type strings or template fields require save format changes.
  6. Hand-off checklist for SA-A2 (JSON template entries, voice sheets, ambient banter, integration tests).
- `requirements/character_voices.md` SA-PREP-1 inventory table extended with one row per net-new specialist crew NPC (status: net-new, speaker_id candidate, consuming sprint = SA-A2 plus relevant downstream sprint(s)). Speaker_id Registry Table (lines 615-637) extended in the same edit.

**Acceptance criteria.**
1. `requirements/sa_crew_design.md` exists.
2. The doc names each new specialization with a label that does NOT collide with any existing skill ID in `spacegame/models/progression.py` (search target list at minimum: `negotiator`, `master_negotiator`, `mediator`, `tariff_negotiation`, `trade_network`) and does NOT collide with any existing crew `role` label in `data/crew/crew_members.json` (existing role labels include `negotiator`, `diplomatic aide`, `trader`, `market analyst`).
3. Every anchor system that the strategic vision identifies as needing crew support (Bidding, Politics — both advocate and arbitration variants — Financial, Research) is covered by at least one specialization in the roster, AND each specialization names at least one anchor system AND one consuming SA sprint by ID.
4. Every specialization in the roster declares at least one `bonus_type` string in snake_case with: description (one sentence), magnitude range (numeric, e.g., `0.05-0.15` or `+1 to +3`), the consuming view file path(s) where `get_bonus(...)` will be called by a downstream sprint.
5. The bonus-naming convention table lists every new `bonus_type` string introduced by the design and confirms (per string) whether it is read via `crew_roster.get_bonus()`, `progression.get_bonus()` (matching SA-C1/SA-C2 skill bonus_types), or both. No string in the table collides with an existing bonus_type already used in `data/crew/crew_members.json` or `spacegame/models/progression.py` — collisions are listed and explicitly resolved.
6. The cross-reference matrix has one row per specialization with non-empty values for: consuming SA sprint(s), consuming view file(s), integration mechanism (a one-sentence summary of how the bonus shows up in player-visible behavior).
7. The decisions-locked section resolves all five items in the Risks / open questions block below, each with a one-paragraph rationale.
8. The `character_voices.md` SA-PREP-1 NPC inventory table AND speaker_id registry both contain one new row per net-new specialist crew NPC. Each new row names: NPC name, status (`net-new`), speaker_id candidate (snake_case), consuming sprint(s) including SA-A2 as the authoring sprint. Banned-name policy from the cultural guide is honored.
9. The save-migration note explicitly states whether new bonus_type strings, new template fields, or new crew state fields require any change to `CrewRoster.get_state()` / `load_state()` (`spacegame/models/crew.py` lines 637-679) and gives the reasoning. If migration is required, the note describes the back-compat default for old saves.
10. Writing Bible scanner clean on all prose in `sa_crew_design.md` and the new `character_voices.md` rows: no em-dashes, no banned NPC names from the cultural guide (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose), no "couldn't help but," no "a testament to," no "no X, no Y" parallel-negation rhetoric in any quoted persona-seed line.

**Risks / open questions.**
- ~~Decision 1 — Specialization set scope.~~ **LOCKED**: Five specializations, covering all four Phase A-named anchor systems plus the Politics arbitration variant the vision calls out at SA-P5. Set: **Auction Reader** (Bidding), **Coalition Builder** (Politics, advocate), **Arbiter** (Politics, neutral / SA-P5 gray-market mediation), **Speculator** (Financial), **Patron** (Research). *Rationale*: The vision (`station_anchors.md`, Phase A header + Phase II/III/IV/V integration commitments) names exactly these four anchor systems and explicitly distinguishes Mediator from Coalition Builder ("Politics neutral" vs. "Politics advocate"). Five is the minimum that lets every Phase II-V system find a crew slot. SA-A1 is design-only — adding a sixth speculative specialization would push the implementer (SA-A2) outside its M-size envelope without a known consumer.
- ~~Decision 2 — Naming scheme to avoid collisions.~~ **LOCKED**: Use the five names above and explicitly **do not** reuse the label "Negotiator" or "Mediator" for the crew specialization. *Rationale*: `spacegame/models/progression.py` already defines a `negotiator` Commerce skill node (line 385) and a `master_negotiator` capstone (line 1049); `data/crew/crew_members.json` already gives Leah Chen the role label `"negotiator"` with trade-price bonuses unrelated to bidding. Reusing the Negotiator name for a Bidding-specialist crew would create three different things called "Negotiator" with three different bonus_types — exactly the kind of cross-cutting confusion the project's bonus_type discipline is supposed to prevent. "Auction Reader" makes the bidding-specific function legible at the hire screen without overloading existing terminology. "Arbiter" is similarly distinct from the SA-P5 venue label "Wreckers' Guild gray-market mediation" while staying readable.
- ~~Decision 3 — Extend existing crew templates vs. author net-new.~~ **LOCKED**: **Net-new templates** for all five specializations. *Rationale*: The closest existing matches are Leah Chen (`negotiator` role; bonuses are `buy_price_reduction` + `sell_price_bonus`, neither of which maps to bidding mechanics) and Adisa Nyong'o (`diplomatic aide`; bonuses are `reputation_gain_bonus` + `diplomatic_rep_bonus`, neither of which maps to a Politics dispute UI). Extending those crew would require rewriting their identities and breaking the assumption that an existing recruited crew member's bonuses are stable across saves. Net-new templates are cheaper, give SA-A2 freedom on faction / home_system_id / voice, and keep loyalty/companion semantics for existing companions untouched.
- ~~Decision 4 — Bonus integration pattern: crew-only, skill-only, or both.~~ **LOCKED**: **Both.** Each new `bonus_type` string is read via BOTH `crew_roster.get_bonus(...)` AND `progression.get_bonus(...)` in the consuming view; the values sum. SA-C1/SA-C2 (the skill-tree extension sprints) will introduce matching skill nodes that emit the same string. *Rationale*: This is the project's existing pattern — see `cargo_bonus`, `fuel_efficiency_bonus`, `salvage_yield`, `extra_scan_charges`, etc. all of which are read from both sources and summed in the consuming view (e.g., `views/mining_view.py:417`, `models/ship.py:259-265`). Using one source only would fork the SA arc's bonus aggregation off the project's standard pattern and produce surprises during integration.
- ~~Decision 5 — Companion vs. non-companion semantics.~~ **LOCKED**: All five new specialist crew are **non-companions** (`is_companion: false`, `max_level: 1`, single-tier abilities, no XP, no per-NPC loyalty multiplier). *Rationale*: Per `spacegame/models/crew.py` lines 286-288, only companions receive the loyalty-multiplier scaling (1.25× at Loyal, 1.5× at Devoted) on `get_bonus`. Companions are story-bound (Elena, Marcus, Priya, Tomas) with full crew-quest arcs; the SA arc specialists are journeyman-tier hires keyed to the anchor systems, not story arcs. Treating them as non-companions keeps companion identity intact and gives SA-A2 a clean implementation envelope (no quest authoring, no loyalty curve tuning).

**Plan.** (7 tasks, sequenced)

1. **Read-only context pass (~30 min).** Re-read the locked-decision rationales above against the live state of `progression.py` (existing skill IDs and bonus_types), `crew_members.json` (existing crew labels and bonus_types), and the SA-PREP-1 inventory in `character_voices.md`. Confirm zero collisions on the five locked specialization names AND on the planned bonus_type strings BEFORE writing the design doc. Output: a short collision check (one line per specialization) saved as scratch notes for the design-doc draft. *Risk*: a string collision discovered after the doc is published forces SA-A2 to thrash. The point of this task is to catch it now.

2. **Bonus-naming convention table (~45 min).** For each of the five specializations, define one or two `bonus_type` strings (snake_case, descriptive) plus magnitude ranges. Candidate strings to anchor on (final values lock during the draft, but these are the seeds): Auction Reader → `auction_bid_visibility` (binary 0/1, reveal one rival ceiling) and `auction_lot_appraisal_bonus` (0.05-0.15, post-win valuation accuracy); Coalition Builder → `coalition_sway_bonus` (0.10-0.25, delegate persuasion modifier) and `coalition_size_bonus` (+1 to +2, max delegates pre-committable per dispute); Arbiter → `arbitration_neutrality_bonus` (0.10-0.20, partial-win odds shift) and `arbitration_dispute_intel` (binary, reveal hidden delegate position); Speculator → `futures_intel` (binary, reveal one futures-contract probability band) and `speculator_premium_reduction` (0.05-0.15, lower spread on contract entry); Patron → `research_yield_bonus` (0.05-0.15, increased project return) and `research_risk_reduction` (0.05-0.15, lower failure odds). Each row in the table records: string, description, magnitude range, consuming view file path(s), source(s) read from (crew, skill, both). *Gotcha*: do not introduce strings that share a prefix with an existing string in a way that would break naive substring searches in tooling (e.g., `salvage_yield` already exists, so `research_salvage_yield` is fine but `salvage_yield_bonus` is not).

3. **Per-specialization design blocks (~90 min).** One block per specialization. Each block contains: name, one-line role label suitable for `data/crew/crew_members.json#role`, the bonus_type strings from task 2 with locked magnitude values for level 1 (non-companion crew are flat-bonus only, so no per-level scaling), `home_system_id` candidate (one of the existing system IDs in `data/galaxy/systems.json`), `faction_id` candidate (one of the existing faction IDs), hireability gating note (any rep tier or flag prerequisite the SA-A2 implementer should consider), and a 3-5 sentence persona seed that gives SA-A2 enough character DNA to author the voice sheet. *Risk*: persona seeds can drift into voice-sheet authoring scope. Keep them seed-length only; SA-A2 owns the full sheet.

4. **Cross-reference matrix (~30 min).** One row per specialization. Columns: specialization name, consuming SA sprint(s) (e.g., SA-1 / SA-P3 / SA-P4 / SA-P5 / SA-B3 / SA-B4 / SA-R1 / SA-F2 / SA-F3), consuming view file path(s) (predicted; the views may not exist yet — note that explicitly), integration mechanism (one sentence: how the bonus changes player-visible behavior in that view). The matrix is the artifact downstream sprint planners will read first. *Gotcha*: it is fine for the consuming view path to be `(view file authored in SA-P3 — does not exist yet)`; the matrix is forward-looking.

5. **Update `character_voices.md` SA-PREP-1 inventory + speaker_id registry (~30 min).** Append five new rows to BOTH the inventory table (lines 587-609) and the speaker_id registry (lines 615-637). For each new specialist crew NPC: NPC name (a placeholder character name per the cultural guide's naming guidance, with banned-name policy honored), status `net-new`, speaker_id candidate (snake_case), consuming sprint = `SA-A2 (authoring), <downstream sprint ID(s)>`. Confirm names against the banned list (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose) before committing. *Risk*: stepping on existing speaker_ids — search the file for the candidate string before writing it.

6. **Decisions-locked + save-migration + hand-off sections (~30 min).** Restate the five decisions above in the design doc with one-paragraph rationale each (do not just link back to ROADMAP). Save-migration note: confirm new bonus_type strings require zero save migration (the `CrewRoster.get_state()` / `load_state()` chain serializes the recruited list, per-member state, and `bonus_abilities`; new bonus_type strings flow through unchanged because they are values inside an existing serialized dict, not new top-level fields). If the design adds any new template field, surface it explicitly. Hand-off section: bullet list of what SA-A2 produces (JSON template entries, voice sheets per `character_voices.md` standard, 3-5 ambient banter samples per specialist, integration tests in `tests/test_models/test_crew.py`).

7. **Voice-check + commit (~15 min).** Read the doc end-to-end and remove em-dashes (replace with periods or commas), check for banned phrases ("couldn't help but," "a testament to," parallel-negation "no X, no Y"), confirm no banned NPC names. Commit `requirements/sa_crew_design.md` and the `character_voices.md` update in the same commit referencing SA-A1.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 22:23 — harness: plan phase starting
- 2026-04-26 22:55 — planning complete; locked 5 decisions (specialization set, naming-collision avoidance, net-new templates, dual crew+skill bonus reads, non-companion semantics); folded in 3 polish items (voice-sheet inventory update in `character_voices.md`, bonus-naming convention table as standalone section, cross-reference matrix); refined ACs from 3 → 10 to make every design-doc section mechanically verifiable; expanded Touch zones to include `character_voices.md` because the SA-PREP-1 inventory table is the canonical NPC registry. PHASE_OK
- 2026-04-26 22:30 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 — implementation complete; authored requirements/sa_crew_design.md (218 lines: 5 specialization blocks, bonus-naming convention table, cross-reference matrix, 5 decisions, save-migration note, SA-A2 hand-off checklist); extended character_voices.md SA-PREP-1 inventory and speaker_id registry with 5 new rows (Sable Trent, Desta Coll, Cass Weller, Brix Tano, Nuri Solberg); all 10 new bonus_type strings confirmed unique; Writing Bible clean; test suite 8348 passed (no regressions). PHASE_OK
- 2026-04-26 22:40 — harness: review phase starting (rework cycle 0)
- 2026-04-26 23:15 — review complete; all 10 acceptance criteria verified: design doc exists and is complete, zero bonus_type or role-label collisions confirmed against live progression.py and crew_members.json, all 5 anchor systems covered, cross-reference matrix complete, decisions-locked section resolves all 5 risks, character_voices.md inventory table and speaker_id registry both extended with 5 rows, save-migration note explicit, Writing Bible clean (no em-dashes, no banned phrases, no banned NPC names). Test suite 8348 passed (matches baseline). All 3 planner-folded polish items shipped. No findings. PHASE_OK
- 2026-04-26 22:45 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 22:40
- Completed: 2026-04-26 23:15
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: none
- Tests_passing: 8348
- Acceptance_criteria_verified: 10/10
- Polish_items_verified: 3/3
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Followup_sprints_added: none
- Notes: Design-only sprint; no Python touched. All 10 bonus_type strings confirmed unique against both progression.py and crew_members.json. Character voices clean and consistent with working-galaxy tone.

#### SA-A2 — Crew template implementation

**Status**: done
**Phase**: Phase A | **Size**: M | **Effort**: 5-7 days
**Depends on**: SA-A1 | **Blocks**: SA-1, SA-P2, SA-B2, SA-X6

**Goal.** Mechanical implementation of the five crew specializations locked by SA-A1's `requirements/sa_crew_design.md`: Auction Reader (Sable Trent), Coalition Builder (Desta Coll), Arbiter (Cass Weller), Speculator (Brix Tano), Patron (Nuri Solberg). Author the five JSON template entries in `data/crew/crew_members.json` with the bonus_type strings and magnitudes locked in SA-A1 section 1. Author one voice sheet per specialist in `requirements/character_voices.md` matching the SA-PREP-1 format. Author 4-5 ambient banter lines per specialist in `data/crew/ambient_dialogue.json` covering the existing context types (home_system, idle, inter_crew, faction_territory). Add integration tests in `tests/test_models/test_crew.py` proving each specialist's bonuses resolve correctly via `crew_roster.get_bonus()`, save/load round-trips preserve the recruited specialist, and each specialist appears in `get_available_crew_at_system()` at the home system locked by SA-A1. No new model fields, no save migration, no flag-gating infrastructure (deferred to consumer sprints — see Decision 1).

**Context to read.**
- `requirements/sa_crew_design.md` (the SA-A1 spec — sections 1, 2, 5, 6 are load-bearing)
- `requirements/character_voices.md` (SA-PREP-1 inventory + speaker_id registry pre-register all five specialists; SA Arc voice-sheet format begins at line 651)
- `spacegame/models/crew.py` (CrewTemplate dataclass; CrewRoster.recruit / get_bonus / get_available_crew_at_system / get_state / load_state)
- `spacegame/models/ambient_dialogue.py` (AmbientLine fields and matching logic)
- `spacegame/data_loader.py` lines 1236-1313 (crew template + ambient dialogue loaders)
- `data/crew/crew_members.json` (existing non-companion entries: Kai Torren line 289, Rina Vasquez 316, Sgt Harkov 343, Adisa Nyong'o 613, Leah Chen 640 — these are the shape SA-A2's five new entries match)
- `data/crew/ambient_dialogue.json` (existing line shape — context categories in use)
- `tests/test_models/test_crew.py` and `tests/test_models/test_crew_expansion.py` (existing test patterns; `_make_template` helper)
- `tests/test_writing_bible_compliance.py` (the scanner that auto-scans `ambient_lines` for em-dashes / banned phrases / parallel-negation)
- `requirements/dialogue_writing_guide.md` (Writing Bible — banned phrases and tone rules apply to all five voice sheets and all banter lines)
- `requirements/cultural_guide.md` (banned NPC names: Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose — none of the five locked names violate this)
- `requirements/onboarding_design.md` (six teaching principles — apply unchanged to specialist crew descriptions and banter)
- `CLAUDE.md` (Skill System section + Cross-Cutting Concerns table row "Crew abilities")

**Touch zones.**
- `data/crew/crew_members.json` (append five new template entries)
- `data/crew/ambient_dialogue.json` (append 4-5 new lines per specialist; ~22-25 new entries total)
- `requirements/character_voices.md` (append five new voice sheets to the "SA Arc — New Voice Sheets" section that begins at line 651)
- `tests/test_models/test_crew.py` (append `TestSAArcSpecialists` test class; add a bonus-string collision regression test)
- `tests/test_data/test_cross_references.py` (add a small smoke test that crew templates' `home_system_id` and `faction_id` resolve, mirroring the existing `test_npc_home_systems_exist` pattern at line 123)

**Deliverables.**
- Five JSON template entries in `data/crew/crew_members.json`, one per specialization. Each entry contains exactly: `id` (snake_case from speaker_id registry), `name` (matches the SA-A1 design), `role` (lowercase label per SA-A1 section 1), `faction_id`, `home_system_id`, `description` (one to two sentence persona-rooted blurb suitable for the hire screen), `portrait_color` (RGB list, visually distinct from other crew), `base_attributes`, `max_level: 1`, `xp_thresholds: [0]`, `is_companion: false`, `abilities` (two abilities per specialist with bonus_type and bonus_value matching SA-A1 section 1.1-1.5). No `combat_moves`, no `combat_move`. No new top-level fields.
- Five voice sheets in `requirements/character_voices.md`, appended to the "SA Arc — New Voice Sheets" section. Each sheet follows the SA-PREP-1 format: header line (Faction / Age / Role / Tonal register), Core Voice, Verbal Habits, What [she/he] Says vs. What [she/he] Means, Emotional Range, What [she/he] Never Says, Sample Lines (3-5 across emotional states). Each sheet ends with a one-line "Bonus Domain" footer naming the two `bonus_type` strings and the consuming SA sprint(s) per the SA-A1 cross-reference matrix (section 3).
- 4-5 ambient banter lines per specialist in `data/crew/ambient_dialogue.json`. Per specialist, at minimum: one `home_system` line keyed to `home_system_id`, one `idle` line, one `inter_crew` line keyed to an existing companion (`elena_reeves`, `marcus_jin`, `dr_priya_osei`, or `tomas_drifter`). For specialists with a `faction_id`, one `faction_territory` line keyed to that faction. A second `idle` or `inter_crew` line where the persona supports it. Cass Weller's `faction_id` is empty so she gets one extra `idle` or `inter_crew` line in lieu of a faction line. Total target: 22-25 new ambient lines.
- Integration tests in `tests/test_models/test_crew.py` (new `TestSAArcSpecialists` class) covering: (a) each specialist's two bonus_type strings resolve to the expected magnitudes via `roster.get_bonus(...)` after recruitment; (b) each specialist's bonuses resolve to 0.0 when not recruited; (c) each specialist appears in `roster.get_available_crew_at_system(home_system_id)` with no other crew filter active; (d) save/load round-trip via `roster.get_state() -> load_state()` preserves a recruited specialist's identity and re-resolves the bonuses; (e) `add_xp_to_all` is a no-op for specialists (max_level=1); (f) bonus_type collision regression: no two crew templates share an `(id, bonus_type, description)` triple within the same template, and no two templates emit the same `(bonus_type, description)` pair across the whole roster (catches accidental copy-paste of an ability between templates).
- Cross-reference smoke test in `tests/test_data/test_cross_references.py` (new): `test_crew_template_home_systems_exist` and `test_crew_template_faction_ids_valid` mirroring the existing NPC patterns at lines 123 and 151. Catches typos in the new entries and protects future crew authoring.
- No code changes to `spacegame/models/crew.py`, `spacegame/data_loader.py`, or `spacegame/save_manager.py`. The existing serialization and loading paths handle the new entries unchanged per SA-A1 section 5.

**Acceptance criteria.**
1. `data/crew/crew_members.json` contains five new entries with IDs `sable_trent`, `desta_coll`, `cass_weller`, `brix_tano`, `nuri_solberg`. Each entry's `name`, `role`, `faction_id`, `home_system_id`, and `abilities` (bonus_type + bonus_value) match SA-A1 section 1 exactly. `max_level == 1`, `xp_thresholds == [0]`, `is_companion == false` on all five. No `combat_moves` or `combat_move` field on any of the five.
2. `DataLoader.load_crew_templates()` loads all five new templates without warning. `dl.get_crew_template("sable_trent")` (and the four others) returns a non-None CrewTemplate. Verified by a test that calls the loader against the live JSON file.
3. For each of the five specialists, `roster.recruit(specialist_id, crew_slots=10)` succeeds, and afterward `roster.get_bonus("<bonus_type>")` returns the magnitude locked in SA-A1 section 1 for both bonus_type strings on that specialist (e.g., recruiting `sable_trent` makes `roster.get_bonus("auction_bid_visibility") == 1.0` and `roster.get_bonus("auction_lot_appraisal_bonus") == pytest.approx(0.10)`). Tested per-specialist, ten total bonus_type assertions.
4. With no specialist recruited, `roster.get_bonus(...)` returns 0.0 for every one of the ten new bonus_type strings.
5. `roster.get_available_crew_at_system(home_system_id)` returns each specialist when called for the matching home_system. Specifically: `sable_trent` and the existing `rina_vasquez` and `leah_chen` all appear at `stellaris_port`; `desta_coll` and the existing `adisa_nyongo` appear at `havens_rest`; `cass_weller` and the existing `sgt_harkov` appear at `crimson_reach`; `brix_tano` and the existing `kai_torren` appear at `nexus_prime`; `nuri_solberg` appears at `axiom_labs`. No specialist appears at a system other than its locked home.
6. Save/load round-trip via `roster.get_state() -> load_state()` preserves a recruited specialist. After round-trip, `roster.is_recruited(specialist_id)` is True, and `roster.get_bonus(bonus_type)` returns the same magnitude as before round-trip. Tested with `sable_trent` as the canonical case; the other four are covered by step 3 against a fresh roster.
7. `add_xp_to_all(amount)` returns no level-up message for any specialist regardless of `amount` (max_level=1 short-circuits XP gain in the existing `add_xp_to_all` loop). Verified by a test that recruits one specialist, calls `add_xp_to_all(10000)`, and asserts the returned message list is empty for that specialist's name.
8. `requirements/character_voices.md` contains five new voice sheets in the "SA Arc — New Voice Sheets" section. Each sheet has the seven standard subsections (header line, Core Voice, Verbal Habits, What [pronoun] Says vs. What [pronoun] Means, Emotional Range, What [pronoun] Never Says, Sample Lines) and a closing "Bonus Domain" footer naming both bonus_type strings and the consuming SA sprint(s). Sample Lines section contains 3-5 examples per sheet.
9. `data/crew/ambient_dialogue.json` contains 4-5 new lines per specialist (22-25 new entries total). Each line has `crew_id`, `text`, `context`, and the appropriate context-specific field(s). Per specialist coverage: at least one `home_system` line (keyed to the locked `home_system_id`), at least one `idle` line, at least one `inter_crew` line (keyed via `required_crew` to one of `elena_reeves`, `marcus_jin`, `dr_priya_osei`, `tomas_drifter`). Specialists with a non-empty `faction_id` (Sable, Desta, Brix, Nuri) also have one `faction_territory` line. Cass (no faction) gets one extra `idle` or `inter_crew` line in lieu.
10. The Writing Bible scanner (`tests/test_writing_bible_compliance.py`) passes with zero new offenders against the new ambient lines. No em-dashes (`—`, `–`, ` -- `), no `couldn't help but`, no `a testament to`, no parallel-negation rhetoric (`no X, no Y`) in any of the new ambient lines. The five voice sheets in `character_voices.md` are voice-checked manually for the same rules and for banned NPC names.
11. The cross-reference smoke test asserts every loaded crew template's non-empty `home_system_id` resolves to a real entry in `dl.systems` and every non-empty `faction_id` resolves to a real entry in `dl.factions`. Catches the five new entries plus serves as a regression net for future crew authoring.
12. The bonus-string collision regression test asserts: (a) no single template has two `abilities` entries sharing the same `(bonus_type, description)` pair; (b) the `(bonus_type, description)` pairs across all crew templates are unique except where identical bonuses are intentionally reused (the test should accept legitimate overlap and document any allowed duplicates). Pin the exact assertion shape during implementation.
13. `ruff format`, `ruff check`, `mypy spacegame/` clean. Full test suite green at >= 8348 passing (matches pre-phase baseline), 98 skipped.

**Risks / open questions.**

- ~~Decision 1 — Hireability gating mechanism for SA-A2.~~ **LOCKED**: SA-A2 ships all five specialists with NO flag gating in `CrewRoster`. Each specialist is hireable at its locked `home_system_id` from the moment the player visits that system, the same way the existing non-companion crew (Kai Torren, Rina Vasquez, Sgt Harkov, etc.) appear today. The SA-A1 design doc's hireability notes ("after the player first enters the Stellaris Auction House," "after first contact with the Okafor Institute") become **forward-looking notes that consumer sprints SA-B3, SA-P4, SA-R1 implement when they author their venues**. *Rationale*: `CrewRoster.get_available_crew_at_system` (lines 562-585 of `crew.py`) has no flag-gate API today; introducing one would require touching `CrewRoster`, the cantina view, the station-hub view, and adding a `dialogue_flags` parameter through the call chain. That is M-size scope on its own and outside SA-A2's envelope. The auction house, congress hall, mediation venue, financial exchange, and Okafor Institute all do not exist in code yet (verified by grep against `spacegame/`), so flag-gating SA-A2 against flags those sprints have not authored would gate the specialists behind unknowable conditions. Shipping ungated matches the established non-companion crew pattern and lets each consumer sprint add a gate that fits its venue's narrative when the venue exists.

- ~~Decision 2 — Voice-sheet section and format.~~ **LOCKED**: Append five new sheets to `requirements/character_voices.md` under the existing "SA Arc — New Voice Sheets" section (begins at line 651), placed after the SA-PREP-1 sheets in registry-table order: Sable Trent, Desta Coll, Cass Weller, Brix Tano, Nuri Solberg. Format mirrors SA-PREP-1 (header line; Core Voice; Verbal Habits; What [she/he] Says vs. What [she/he] Means; Emotional Range; What [she/he] Never Says; Sample Lines). One closing "Bonus Domain" footer line per sheet names both bonus_type strings and the consuming SA sprint(s) so downstream sprint planners read the sheet and immediately see the integration. *Rationale*: SA-PREP-1 established the section, the format, and the speaker_id registry rows for these five characters. Reusing the format is mechanical and keeps the doc internally consistent. The "Bonus Domain" footer is a small SA-A2 polish add on top of the SA-PREP-1 format because it tightens the link between voice authorship and integration intent.

- ~~Decision 3 — Ambient banter quantity, contexts, and inter-crew anchors.~~ **LOCKED**: 4-5 ambient lines per specialist with required minimum coverage of one `home_system`, one `idle`, and one `inter_crew` line per specialist. Specialists with a non-empty `faction_id` get one `faction_territory` line; Cass Weller (no faction) gets one extra `idle` or `inter_crew` line in lieu. `inter_crew` lines reference one of the four existing companions (`elena_reeves`, `marcus_jin`, `dr_priya_osei`, `tomas_drifter`) via the `required_crew` field. *Rationale*: SA-A1 hand-off checklist allowed 3-5; locking 4-5 maximizes context-type coverage so each specialist actually surfaces in the cockpit panel under varied conditions. Anchoring inter_crew lines to existing companions (rather than to other new specialists) ensures the lines fire even before the player has met another SA arc specialist; pairing with companions also reinforces the existing crew dynamic without requiring an inter-specialist pairing matrix.

- ~~Decision 4 — JSON schema fidelity and save migration.~~ **LOCKED**: The five new entries match the existing non-companion crew JSON schema exactly. No new top-level fields. No `combat_moves` or `combat_move`. No save migration logic in `spacegame/save_manager.py` or `spacegame/models/crew.py`. *Rationale*: SA-A1 section 5 explicitly confirmed no save migration is needed because the new bonus_type strings flow through the existing `abilities` list inside the existing `bonus_abilities` serialization path. Adding any new top-level field would break that guarantee. Specialists are non-combat by design (they read auctions, sway delegates, mediate disputes, read futures contracts, evaluate research proposals); none of them belong in the combat queue, so omitting combat_moves is correct rather than oversight.

- ~~Decision 5 — Test coverage scope.~~ **LOCKED**: New tests live in `tests/test_models/test_crew.py` (new `TestSAArcSpecialists` class) and `tests/test_data/test_cross_references.py` (two new methods on the existing `TestNPCCrossReferences`-style class or a new `TestCrewCrossReferences` class). No new test files. *Rationale*: Keeping the new tests in the existing test files preserves the project's test-organization convention (one test file per model module). The cross-reference tests live with other cross-reference tests so future crew authoring inherits the regression net.

- ~~Decision 6 — Bonus-string collision regression test scope.~~ **LOCKED**: A single test in `tests/test_models/test_crew.py` asserts no two crew templates share an `(id, bonus_type, description)` triple internally and no two templates share a `(bonus_type, description)` pair across the roster, ALLOWING explicit duplicates only where the design intentionally repeats a bonus (e.g., a base-tier ability and an upgraded-tier ability with the same description text would be a bug; two crew with similar but distinct ability descriptions are fine). The exact assertion shape is pinned during implementation against the live JSON to avoid false-positives on legitimate existing duplication. *Rationale*: SA-A1 collision check was a one-time manual review; this regression test makes the check standing so future crew authoring cannot accidentally re-introduce a collision after the SA arc is shipped.

**Plan.**

1. **Read-only context pass and live-state collision check** (~30 min). Re-read `requirements/sa_crew_design.md` sections 1 (specialization roster) and 2 (bonus-naming convention table) — these two sections drive the JSON authoring. Re-read sections 4 (decisions locked) and 6 (hand-off checklist) for the implementer commitments. Verify against the live state: (a) the five system IDs `stellaris_port`, `havens_rest`, `crimson_reach`, `nexus_prime`, `axiom_labs` exist in `data/galaxy/systems.json` (confirmed during planning); (b) the four faction IDs `commerce_guild`, `frontier_alliance`, `science_collective` exist in the faction data, and `""` is acceptable for Cass (confirmed); (c) all ten new bonus_type strings have zero collisions in `spacegame/models/progression.py` and `data/crew/crew_members.json` (confirmed by SA-A1 review); (d) the five speaker_ids `sable_trent`, `desta_coll`, `cass_weller`, `brix_tano`, `nuri_solberg` are pre-registered in `requirements/character_voices.md` lines 610-614 and 643-647 (confirmed). Output: short scratch confirmation in the implementation commit message that no live-state drift has occurred between SA-A1's collision check and SA-A2's authoring. Touches: read-only. Risk: a new crew template authored between SA-A1 and SA-A2 could introduce a collision; check is fast and worth doing once before authoring.

2. **Write failing tests for crew template loading and bonus integration** (TDD red, ~60 min). In `tests/test_models/test_crew.py`, add a new `TestSAArcSpecialists` class. For each of the five specialists, add a `test_<specialist>_loads_and_bonuses_resolve` method using the live `DataLoader` (load all crew templates from JSON, get the specialist by ID, recruit via `CrewRoster`, assert each of the two bonus_type strings on that specialist resolves to the expected magnitude via `roster.get_bonus(...)`). Add `test_specialist_bonuses_zero_when_not_recruited` covering all ten bonus_type strings. Add `test_specialists_appear_at_home_systems` exercising the five `home_system_id` values. Add `test_sable_trent_save_load_roundtrip` as the round-trip canonical case. Add `test_specialists_no_xp_gain` recruiting one specialist and asserting `add_xp_to_all(10000)` returns no message naming that specialist. Add `test_no_duplicate_bonus_type_descriptions` enforcing the collision regression. Run tests — expect every test in the new class to FAIL with `KeyError` or `None` because the JSON entries do not exist yet. Touches: `tests/test_models/test_crew.py`. Risk: the existing `_make_template` helper in `test_crew.py` constructs synthetic templates; the new tests must use the live DataLoader path (not the helper) so the JSON authoring is what's being verified, not the test fixture.

3. **Author five JSON template entries in `data/crew/crew_members.json`** (TDD green, ~90 min). Append five entries inside the `"crew_templates"` array following the existing non-companion entry shape (use Kai Torren at line 289 as the closest visual reference). For each specialist: `id`, `name`, `role` (lowercase per SA-A1 section 1: `auction reader`, `coalition builder`, `arbiter`, `speculator`, `research patron`), `faction_id`, `home_system_id`, `description` (one to two sentences pulled from the persona seed and rewritten in the existing-crew description voice; do not paste the persona seed verbatim), `portrait_color` (RGB list with values distinct from existing crew — pick visually-distinct hues per specialist), `base_attributes` (drawn from the persona's strengths: Sable acu+com, Desta com+syn, Cass com+ing, Brix acu+ing, Nuri ing+syn), `max_level: 1`, `xp_thresholds: [0]`, `is_companion: false`, `abilities` array with the two bonus_type entries and locked magnitudes from SA-A1 section 1 (each ability needs `bonus_type`, `bonus_value`, `description`, `unlock_level: 1`). Re-run the tests from step 2; the loader and bonus tests should turn green. Touches: `data/crew/crew_members.json`. Risk: JSON syntax errors (trailing commas, missing braces) will surface as load-time warnings; run tests after each entry rather than batching all five.

4. **Author five voice sheets in `requirements/character_voices.md`** (~120 min). Append five new sheets to the "SA Arc — New Voice Sheets" section (after the existing SA-PREP-1 sheets). Format must match the SA-PREP-1 sheets: header line (`**Faction**`, `**Age**`, `**Role**`, `**Tonal register**`), `### Core Voice`, `### Verbal Habits`, `### What She Says vs. What She Means` (or `### What He Says vs. What He Means`), `### Emotional Range`, `### What She Never Says`, `### Sample Lines` (3-5 numbered examples), and a `### Bonus Domain` footer line naming both bonus_type strings and consuming SA sprint(s) per the SA-A1 section 3 cross-reference matrix. Tonal register suggestions per persona seed: Sable (cataloguer's eye, shows numbers not explanations); Desta (counts commitments, reads pressure points, useful before the vote not during); Cass (interest in whether outcomes hold, structures partial wins); Brix (narrows ranges, uncomfortable being wrong outside the band); Nuri (reads proposals, cares whether projects produce something that holds up). Voice-check end-to-end before saving: zero em-dashes, zero `couldn't help but`, zero `a testament to`, zero `no X, no Y` parallel-negation, zero banned NPC names (Yara, Elara, Kael, Mara, Lydia, Clive, Magnus, Ambrose). Touches: `requirements/character_voices.md`. Risk: the writing tone must match the working-galaxy register established by SA-PREP-1 sheets — read three SA-PREP-1 sheets before drafting to internalize the voice.

5. **Author 4-5 ambient banter lines per specialist in `data/crew/ambient_dialogue.json`** (~75 min). For each specialist, append per Decision 3: one `home_system` line keyed to `home_system_id`, one `idle` line, one `inter_crew` line keyed via `required_crew` to an existing companion. Specialists with a non-empty `faction_id` get one `faction_territory` line keyed to that faction. Cass Weller gets one extra `idle` or `inter_crew` line in lieu of a faction line. Each line shape: `{"crew_id": "<id>", "text": "...", "context": "<context>", ...context-specific field}`. Voice the lines from the persona seed in SA-A1 section 1 — Sable shows numbers, Desta counts commitments, Cass talks about outcomes holding, Brix talks about probability bands, Nuri talks about proposal quality. Voice-check each line: zero em-dashes, zero banned phrases, zero parallel-negation. Run `pytest tests/test_writing_bible_compliance.py -k ambient` and confirm zero new offenders. Touches: `data/crew/ambient_dialogue.json`. Risk: the inter_crew line must reference a `required_crew` ID that is actually in `crew_members.json` — typos (e.g., `"elena_rees"` instead of `"elena_reeves"`) silently make the line never fire; double-check companion IDs before saving.

6. **Add cross-reference smoke tests in `tests/test_data/test_cross_references.py`** (~30 min). Add a new test class (or new methods on an existing class) covering: `test_crew_template_home_systems_exist` (every loaded crew template's non-empty `home_system_id` is in `dl.systems`); `test_crew_template_faction_ids_valid` (every loaded crew template's non-empty `faction_id` is in `dl.factions`). Mirror the existing `test_npc_home_systems_exist` (line 123) and `test_npc_faction_ids_valid` (line 151) patterns. Run — expect green if step 3 was authored correctly. Touches: `tests/test_data/test_cross_references.py`. Risk: a typo in a `home_system_id` from step 3 surfaces here; if either test fails, fix the JSON entry from step 3 rather than relaxing the test.

7. **Run the full validation chain** (~15 min). `ruff format spacegame/ tests/`; `ruff check spacegame/ --fix`; `mypy spacegame/`; `pytest -n auto -q`. Confirm pass count >= 8348 and skip count == 98 (matches pre-phase baseline). If any pre-existing failure surfaces unrelated to SA-A2, note it in the Activity log but do not chase it. If a SA-A2 test fails, debug and fix at the JSON or test level (do not modify `crew.py`, `data_loader.py`, `save_manager.py` per Decision 4). If the Writing Bible scanner catches violations in the new ambient lines, return to step 5, rewrite the offending line, and re-run the scanner. Touches: validation only.

8. **Update Status to `review` and append phase report** (~10 min). Move `Status` from `in-progress` to `review`. Append the `**Last phase report.**` block per agent convention (overwrite any prior phase report block). Commit with `SA-A2: ...` prefix. Touches: `requirements/roadmap/ROADMAP.md`. Risk: forgetting to overwrite the previous phase report — search for `**Last phase report.**` within the SA-A2 section before writing the new one and replace in-place.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-26 22:46 — harness: plan phase starting
- 2026-04-26 23:35 — planning complete; locked 6 decisions (no SA-A2 flag-gating, voice-sheet section/format, ambient banter quantity/contexts/anchors, JSON schema fidelity / no save migration, test coverage scope, bonus-string collision regression scope); folded in 4 polish items (DataLoader smoke test fold-in, cross-reference smoke tests for crew templates, bonus-string collision regression test, "Bonus Domain" footer on voice sheets); refined ACs from 5 to 13 to make every deliverable mechanically verifiable; expanded Touch zones to add `data/crew/ambient_dialogue.json` and `tests/test_data/test_cross_references.py`; verified all 12 Context-to-read entries exist on disk including the SA-A1 design doc. PHASE_OK
- 2026-04-26 22:55 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 — implement phase: TDD red (TestSAArcSpecialists 17 tests, all failing KeyError/None); JSON 5 templates authored; tests turn green; voice sheets authored (Writing Bible clean); 25 ambient banter lines authored; TestCrewCrossReferences 2 tests added; pre-existing faction_id bug fixed (industrial_union -> miners_union in 4 existing templates, corrected count assertions in test_crew_data.py and test_crew_quests.py); full suite 8367/98 (baseline 8348/98, +19). All 13 ACs satisfied. PHASE_OK
- 2026-04-26 23:13 — harness: review phase starting (rework cycle 0)
- 2026-04-26 23:16 — review complete; all 13 ACs verified, all 4 planner polish items delivered, 0 critical findings, 0 minor findings. Writing Bible scanner 17/17. Full suite 8367/98. JSON data, tests, voice sheets, ambient banter all confirmed correct against SA-A1 spec. PHASE_OK
- 2026-04-26 23:18 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 23:13
- Completed: 2026-04-26 23:16
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: none
- Tests_passing: 8367
- Acceptance_criteria_verified: 13/13
- Polish_items_verified: 4/4
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Followup_sprints_added: none
- Notes: All five SA arc specialist crew templates implement per SA-A1 spec with correct bonus types, magnitudes, home systems, and faction IDs. Voice sheets follow established character_voices.md convention. 25 ambient banter lines with correct context coverage. Pre-existing mypy and lint issues are unrelated to SA-A2 touch zones.
### Phase B — Sub-Reputation System Extension

#### SA-B-EXT-1 — Sub-reputation system

**Status**: done
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
12. `ruff format`, `ruff check`, `mypy` clean. Full test suite green at >= 8367 passing, skips == 98 (pre-phase baseline as of 2026-04-26 plan re-pickup).

**Plan.**
1. **Author `requirements/sub_reputation_design.md`** (~30 minutes). Short design doc. Sections: (a) what sub-reputation is and isn't (per-organization standing; not a parallel faction system, not a lockout mechanism, not auto-tied to faction-rep gain), (b) the `OrganizationConfig` / `OrganizationTier` shape, (c) the registry pattern (consumer sprints declare their own configs in their own modules — SA-1 declares the Wreckers' Guild config in `spacegame/models/wreckers_guild.py`), (d) range and clamping rules (0-100 default; configurable), (e) notification queue contract for downstream views, (f) save chain (reuses Player serialization — single `sub_reputation` dict field, no separate save manager), (g) two worked examples shown as illustrative configurations (Wreckers' 3-tier, Stellaris 4-tier) explicitly marked "owned by SA-1 / SA-B3 — not implemented in this sprint." Resolves `station_anchors.md` line 253. Touches: `requirements/sub_reputation_design.md` (NEW). Tests: none (doc-only).

2. **Write failing tests for `sub_reputation` model surface** (TDD red). `tests/test_models/test_sub_reputation.py`. Assert: (a) `OrganizationTier` is a frozen dataclass and orderable by `rank`; (b) `OrganizationConfig.__post_init__` rejects empty tiers, duplicate tier IDs, non-ascending ranks, non-ascending `min_rep`; (c) `get_tier_for_rep` returns the correct tier across edges (including value below the lowest threshold returns the lowest tier, value at `max_rep` returns the highest tier, value at exactly each threshold returns that threshold's tier); (d) `is_at_least` returns False for unknown tier IDs and True/False correctly otherwise. Touches: tests only. Risk: getting the lowest-tier-when-below-threshold semantics right — document and assert explicitly.

3. **Implement `spacegame/models/sub_reputation.py`** (TDD green). Define `OrganizationTier`, `OrganizationConfig`, `SubReputationDelta` (the notification record — frozen dataclass with `org_id`, `effective_amount`, `old_tier`, `new_tier`), `get_tier_for_rep`, `is_at_least`. All three model dataclasses are `@dataclass(frozen=True)` per the SI-2 cookbook. Validation in `__post_init__` raises `ValueError` with descriptive messages. Touches: `spacegame/models/sub_reputation.py` (NEW). Tests: from step 2 turn green.

4. **Write failing tests for `Player.modify_sub_reputation` and helpers** (TDD red). Continue `test_sub_reputation.py`. Assert: (a) new player has `sub_reputation == {}`; (b) `modify_sub_reputation` clamps, returns `(True, message)`, sets the dict entry; (c) tier-up appends a `SubReputationDelta` to `_pending_sub_rep_deltas`; (d) tier-down appends; (e) no-tier-change modifications do not append; (f) modifying sub-rep does not touch `faction_reputation`; (g) calling `modify_reputation` does not touch `sub_reputation`; (h) `get_sub_reputation` defaults to 0; (i) `get_sub_reputation_tier` returns the lowest tier when absent; (j) `is_at_least_tier` returns False for unknown tier_id, correct bool otherwise. Touches: tests only. Risk: clamping at exactly `max_rep` should not queue a no-op delta — pin the behavior.

5. **Implement Player helpers** (TDD green). Add `sub_reputation: dict[str, int] = field(default_factory=dict)` next to `faction_reputation` in `spacegame/models/player.py`. Add `modify_sub_reputation`, `get_sub_reputation`, `get_sub_reputation_tier`, `is_at_least_tier`. Mirror `modify_reputation`'s shape exactly: clamp, compute effective delta, write back, conditionally append to `_pending_sub_rep_deltas` (lazily-initialized non-serialized list, same pattern as `_pending_faction_deltas`). Touches: `spacegame/models/player.py`. Tests: from step 4 turn green.

6. **Write failing tests for save round-trip** (TDD red). `test_sub_reputation.py`. Build a player, set sub-rep on three organizations using synthetic configs, run through `SaveManager._player_to_dict` -> `_player_from_dict`, assert all three preserved. Build a save dict missing the `sub_reputation` key, run through `_player_from_dict`, assert `player.sub_reputation == {}`. Build a player, queue notifications via `modify_sub_reputation`, run through round-trip, assert the queue is reset to empty (notification queue is ephemeral). Touches: tests only. Risk: the save-manager test path has many required fixture fields — use the existing helper convention from `test_save_roundtrip.py` if applicable, otherwise inline the minimal fixture.

7. **Implement save/load round-trip** (TDD green). In `spacegame/save_manager.py`: add `"sub_reputation": player.sub_reputation` to `_player_to_dict` next to `"faction_reputation"`. Add `player.sub_reputation = data.get("sub_reputation", {})` to `_player_from_dict` next to the corresponding faction-rep load. Touches: `spacegame/save_manager.py`. Tests: from step 6 turn green.

8. **Run lint, format, type-check, full test suite**. `ruff format spacegame/ tests/`, `ruff check spacegame/ --fix`, `mypy spacegame/`, `pytest -n auto -q`. Confirm pass count >= 8367 and skip count == 98 (per 2026-04-26 baseline). If any pre-existing failure surfaces unrelated to this sprint, note in Activity log but do not chase. Touches: none (validation step).

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
- 2026-04-26 23:19 — harness: plan phase starting
- 2026-04-26 23:35 — plan re-pickup: verified all 6 Context-to-read paths exist; verified existing plan structure (9 plan steps, 12 acceptance criteria, 6 locked decisions, complete touch zones) aligns with `station_anchors.md` Phase B vision ("Extend the reputation model to support per-organization standing layered under per-faction standing. Tests, save support."); confirmed scope is correctly foundational (zero concrete configs ship — Wreckers' / Auctioneer / SA-B4 own theirs per registry pattern); polish items (tutorial integration, journal beats, achievement unlocks, crew banter, empty/loading/error states) all deferred to consumer sprints since this sprint ships no UI surfaces; refreshed acceptance criterion 12 + plan step 8 baseline from stale 8304 to current 8367 (skips 98); no scope expansion or new sprints needed. PHASE_OK
- 2026-04-26 23:22 — harness: implement phase starting (rework cycle 0)
- 2026-04-26 — implement: tests red (ModuleNotFoundError for sub_reputation, AttributeError on Player methods); sub_reputation.py implemented (26 model tests green, 27 Player tests red); Player helpers implemented (51 tests green, 2 save tests red); save_manager round-trip implemented (all 53 tests green); lint/format clean; full suite 8420/98 (+53). PHASE_OK
- 2026-04-26 23:32 — harness: review phase starting (rework cycle 0)
- 2026-04-26 23:45 — review complete; all 12 acceptance criteria verified; 53/53 tests passing; lint/format/mypy clean on touched files; 8420/98 (>= 8367 baseline); all 6 changed files within declared touch zones; no player-facing content (no Writing Bible or SI-3 checks needed); zero concrete configs correctly not shipped (registry pattern intact); design doc covers all spec deliverables. PHASE_OK
- 2026-04-26 23:37 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-26 23:32
- Completed: 2026-04-26 23:45
- Files_changed: none
- Commits: none
- Tests_passing: 8420
- Acceptance_criteria_verified: 12/12
- Polish_items_verified: n/a
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Followup_sprints_added: none
- Notes: Clean implementation. OrganizationConfig/OrganizationTier/SubReputationDelta frozen dataclasses correct; Player helpers mirror modify_reputation pattern exactly; notification queue lifecycle matches _pending_faction_deltas; save round-trip with legacy-save compat; design doc resolves station_anchors.md open question. Ready for consumer sprints (SA-1, SA-B3, SA-B4).

### Phase C — Skill Tree Extensions

#### SA-C1 — Skill tree extension design

**Status**: done
**Phase**: Phase C | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: SA-C2

**Goal.** Lock the SA-arc skill-tree extension set. Produce a design doc that names each new skill (id, display name, tree, tier, prerequisite, max_level, bonus_type, bonus_per_level, description), aligns its `bonus_type` strings with the seven "both"-source crew bonuses already locked in `requirements/sa_crew_design.md`, decides extend-existing-trees vs. new-tree (per `station_anchors.md` Decision 3), and records the per-tree population delta SA-C2 will introduce. The doc is the single source of truth that SA-C2 implements against. No code in this sprint.

**Context to read.**
- `requirements/station_anchors.md` (Phase C section + Decision 3 "extend existing trees rather than add new"; Phase II/III/IV/V integration commitments name the consuming systems)
- `requirements/sa_crew_design.md` (SA-A1 output: section 2 bonus-naming convention table is the spec for the seven "both"-source `bonus_type` strings; section 4 Decision 4 documents the crew-only exception for the three binary intel bonuses)
- `requirements/skill_tree_overhaul.md` (six-tree structure; "would I notice?" test; gateway-skill-over-stat-bump principle; identity through specialization)
- `requirements/onboarding_design.md` (six teaching principles — apply unchanged; tier-3 capstones are identity-defining and should not proliferate)
- `requirements/agent_principles.md` (scope discipline; the S-sized design sprint should not introduce new capstones or new trees unless required)
- `spacegame/models/progression.py` (`create_default_skills` lines 371-1264; `SkillTreeType` enum lines 12-24; `_SKILL_MIGRATION_MAP` lines 71-170; `from_dict` lines 351-368; collision targets `negotiator` line 385 and `master_negotiator` line 1049)
- `spacegame/views/skill_tree_view.py` (`_CAPSTONE_IDS` set lines 83-95; `_compute_detail_positions` lines 250-296 auto-arranges by prerequisite depth — no view code change needed for net-new mid-tier skills)
- `data/crew/crew_members.json` lines 700-825 (the five SA-A2 specialist entries already carry all ten SA-A1 bonus_type strings; verify the seven "both"-source strings are spelled exactly as SA-C1 will emit them)
- `tests/test_writing_bible_compliance.py` (voice-check regex patterns: em-dash / en-dash / ` -- ` set, banned phrases `couldn't help but` and `a testament to`, parallel-negation `\bno \w+,\s*no \w+`)

**Touch zones.**
- `requirements/sa_skill_design.md` (NEW)

**Deliverables.**
- `requirements/sa_skill_design.md` covering: per-skill block (id, display name, tree, tier, prerequisite_id, max_level, bonus_type, bonus_per_level, one-sentence description, magnitude rationale); bonus-naming convention table mirroring the format in `sa_crew_design.md` section 2; collision-check section (skill IDs and bonus_type strings vs. existing `progression.py` and `data/crew/crew_members.json`); pre-SA-C2 vs. post-SA-C2 per-tree skill count table; capstone analysis (new capstones yes/no, with rationale); save-migration analysis (whether `_SKILL_MIGRATION_MAP` entries are needed); cross-reference matrix to consuming SA sprints; handoff checklist for SA-C2; decisions-locked block.

**Acceptance criteria.**
1. `requirements/sa_skill_design.md` exists and contains exactly one design block per new skill with all fields filled (id, display name, tree, tier 1/2/3, prerequisite_id, max_level, bonus_type, bonus_per_level, one-sentence description, magnitude rationale).
2. The bonus-naming convention table in the doc maps the seven "both"-source `bonus_type` strings 1-to-1 with `requirements/sa_crew_design.md` section 2 (`auction_lot_appraisal_bonus`, `coalition_sway_bonus`, `coalition_size_bonus`, `arbitration_neutrality_bonus`, `speculator_premium_reduction`, `research_yield_bonus`, `research_risk_reduction`). Each row notes that crew + skill values stack via `crew_roster.get_bonus(...) + progression.get_bonus(...)` summation per the SA-A1 Decision 4 pattern, and names the consuming view file (forward-looking) and consuming SA sprint(s).
3. The doc explicitly states whether the three crew-only binary intel `bonus_type` strings (`auction_bid_visibility`, `arbitration_dispute_intel`, `futures_intel`) get matching skill nodes in v1, with rationale citing SA-A1 Decision 4. The locked answer is "no skill nodes for the binary intel bonuses in v1"; the doc must say this explicitly.
4. Collision check: every new skill `id` is verified absent from `create_default_skills()` in `spacegame/models/progression.py`; every new `bonus_type` string is verified absent from `progression.py` and from `data/crew/crew_members.json` *except* for the seven shared with crew (intentional, documented). The check lists each id and bonus_type explicitly with pass/intentional-share status; not a blanket "no collisions found."
5. Tree-population analysis: the doc reports current per-tree skill counts (Commerce, Combat, Exploration, Leadership, Social, Industry) and post-SA-C2 counts after adding the new skills. The doc states explicitly that no new tree is introduced and cites `station_anchors.md` Decision 3 as authority.
6. Capstone analysis: each new skill is classified as Tier 1, Tier 2, or Tier 3. The doc states explicitly whether any new Tier 3 capstones are introduced. The locked answer is "no new capstones in v1"; the doc must say this explicitly with rationale, and confirm the existing `_CAPSTONE_IDS` set in `spacegame/views/skill_tree_view.py` does not need changes for SA-C2.
7. Save-migration analysis: the doc confirms `from_dict()` (line 351 of `progression.py`) loads existing saves without crashing when new skill IDs are absent. The doc states whether any `_SKILL_MIGRATION_MAP` entries are needed (the locked answer for net-new IDs is "no") and notes the round-trip behavior expected for saves created post-SA-C2.
8. Cross-reference matrix + handoff checklist: the doc lists each new skill against the consuming SA sprint(s) (SA-B3, SA-B4, SA-P3, SA-P4, SA-P5, SA-F2, SA-F3, SA-R1, SA-R2) and gives SA-C2 a numbered checklist of artifacts (new `SkillNode` entries in `create_default_skills()`, per-skill bonus-stack tests in `tests/test_models/test_progression.py`, save round-trip tests, no view code changes expected).
9. Voice-check: the doc passes the three Writing Bible regex patterns from `tests/test_writing_bible_compliance.py` (em-dash / en-dash / ASCII ` -- `, banned phrases, parallel-negation) with zero violations. ASCII double-hyphen between space-separated tokens is forbidden; inline compound words (e.g., `multi-tier`) are unaffected.
10. Full test suite passes at or above the pre-phase baseline of 8430 passing tests (98 skipped). No code is modified in this sprint, so this is a regression check: after authoring the doc, the implementer runs `pytest -n auto -q` and confirms `>= 8430` passing.

**Risks / open questions.**
- **Locked: skill set count = 7.** One new skill per "both"-source crew `bonus_type` from SA-A1. The three binary intel `bonus_type` strings stay crew-only in v1 per SA-A1 Decision 4 exception. Reason: introducing skill nodes for binary gates would deviate from the SA-A1 design without a locked consumer; defer to Phase VI cohesion if a skill-tree path becomes warranted.
- **Locked: tree placement = extend Social, Commerce, Leadership, and Industry.** No new tree, per `station_anchors.md` Decision 3. Recommended placement (the doc may refine, but the locked authority is "extend, never new"):
  - `auction_lot_appraisal_bonus` → Commerce (Tier 2; prereq `market_eye` or `market_insider`).
  - `coalition_sway_bonus` → Social (Tier 2; prereq `silver_tongue` or `commanding_presence`).
  - `coalition_size_bonus` → Leadership (Tier 2; prereq `crew_manager` or `give_the_word`).
  - `arbitration_neutrality_bonus` → Social (Tier 2; prereq `keen_insight` or `empathic_read`).
  - `speculator_premium_reduction` → Commerce (Tier 2; prereq `market_insider` or `tariff_negotiation`).
  - `research_yield_bonus` → Industry (Tier 2; prereq `efficient_refining` or `tool_sense`).
  - `research_risk_reduction` → Leadership (Tier 2; prereq `diplomatic_relations` or `give_the_word`).
- **Locked: no new capstones in v1.** All seven new skills are Tier 2 specialization nodes. Existing capstones (`insurance`, `peacemaker`, `juggernaut_capstone`, `sentinel_capstone`, `ghost_capstone`, `volley_commander`, `legend_of_the_expanse`, `ore_sense`, `material_science`) remain unchanged. Reason: an S-sized design sprint should not introduce identity-defining capstones for every anchor system; capstones earn their place by the system's depth (Phase II Politics may justify a future Coalition Builder capstone in SA-X cohesion, not here). This also keeps `_CAPSTONE_IDS` in `spacegame/views/skill_tree_view.py` unchanged for SA-C2.
- **Locked: naming avoids `negotiator` and `master_negotiator` collisions.** The display name "Negotiator" is taken by the existing Commerce Tier 1 skill (`negotiator`, +5% buy price reduction); the display name "Master Negotiator" is taken by the existing Social Tier 2 skill (`master_negotiator`, special dialogue options). New skills use distinct names that do not collide either as `id` or as display string. The doc author selects the exact names and runs the collision check listed in AC 4. SA-A1 made the same call for crew (used "Auction Reader" instead of "Negotiator"); SA-C1 follows the same convention.
- **Locked: per-skill magnitude range matches SA-A1 ranges.** Each skill's `bonus_per_level` is selected from the range documented in `sa_crew_design.md` section 1 for the matching crew bonus. The skill's max_level (locked: 1 or 2 per skill, never 3) determines the upper-bound stack from the skill side; the crew side adds its level-1 magnitude on top, and the consumer view sums both per the established `cargo_bonus`/`fuel_efficiency_bonus` pattern. Reason: keeping the cap at the SA-A1 range upper bound prevents skill+crew stacking from overshooting balance assumptions baked into SA-B/P/R/F design when those phases run.
- **Locked: max_level = 2 for additive bonuses, max_level = 1 for binary/gateway bonuses.** All seven SA-C1 skills are additive (none are binary in v1), so all seven have max_level = 2. Reason: max_level 2 gives a meaningful investment trade-off (1 point unlocks; 1 more point caps); max_level 3 is reserved for high-frequency utility skills (cargo_mastery, fuel_efficiency) where the effect is felt every session.
- **Locked: save migration = none required.** Net-new skill IDs added to `create_default_skills()`. Old saves omit the new skills; `from_dict()` (line 351 of `progression.py`) iterates only over keys present in the saved dict, so absent keys default to current_level=0 via `__post_init__` re-instantiation. New saves include the new skills. No `_SKILL_MIGRATION_MAP` entries needed because no existing skill ID is being renamed or split. The doc must state this explicitly per AC 7.
- **Locked: skill tree view changes = none.** `_compute_detail_positions` in `spacegame/views/skill_tree_view.py` auto-arranges nodes by prerequisite depth, so net-new mid-tier skills lay out without code changes. No new entries to `_CAPSTONE_IDS` because no new capstones. SA-C2's view-side work is therefore limited to a layout regression check at the established 6 resolutions; no skill_tree_view.py edits expected.

**Plan.** (9 tasks, design-only sprint; no code changes; no failing tests to write because the deliverable is a `.md` artifact)

1. **Skill set scope decision + naming.** Open `requirements/sa_skill_design.md`. Write section 1 (Skill Roster) with one block per new skill. Lock the skill `id` (snake_case), display name (Title Case, distinct from existing `negotiator` and `master_negotiator`), tree, tier (per locked decisions, all Tier 2), prerequisite_id, max_level (per locked decisions, all 2), bonus_type (must match SA-A1 section 2 exactly for the seven shared strings), and bonus_per_level (within SA-A1 range). Read `progression.py` lines 384-1264 once more before locking display names to confirm no collision.
   - Files: `requirements/sa_skill_design.md` (NEW); read-only `spacegame/models/progression.py`, `requirements/sa_crew_design.md`.
   - Risk: easy to pick a display name that already exists. Run a substring check against every `name=` field in `create_default_skills()` before locking.

2. **Per-skill block authoring with magnitude rationale.** For each of the seven skills, expand the block from task 1 with a one-sentence description (player-readable, voice-checked), a magnitude rationale tying the chosen `bonus_per_level` to a specific point in the SA-A1 range, and a narrative hook (one sentence on what investing in this skill represents in-fiction).
   - Files: `requirements/sa_skill_design.md`.
   - Gotcha: descriptions become user-facing strings once SA-C2 lands them in `create_default_skills()`. Apply Writing Bible discipline now: terse, declarative, no em-dashes, no banned phrases, no parallel-negation rhetoric.

3. **Bonus-naming convention table.** Mirror `sa_crew_design.md` section 2 format. Columns: `bonus_type`, description, level-1 magnitude on the skill side, range, consuming view file (forward-looking, e.g., `spacegame/views/auction_view.py` per SA-B3), source-read pattern (skill / crew / both — the seven shared strings are "both", any SA-C1-only string is "skill").
   - Files: `requirements/sa_skill_design.md`.
   - Risk: ensure 1-to-1 mapping with the SA-A1 "both" set. Mismatched spelling (e.g., `research_yield` vs. `research_yield_bonus`) is a silent bug because `progression.get_bonus()` falls through to 0.

4. **Collision check.** For each new skill `id` and `bonus_type`, search `spacegame/models/progression.py` and `data/crew/crew_members.json`. Document each result inline (not a blanket "no collisions found"). Mirror SA-A1 collision-check format: name the strings checked, name the closest near-misses, confirm pass status. The seven shared crew bonus_types are explicit "intentional shared" rows.
   - Files: `requirements/sa_skill_design.md`; read-only sources.
   - Gotcha: substring checks find prefix collisions (e.g., `salvage_yield` vs. a hypothetical `salvage_yield_bonus`). Run both exact-string and prefix-substring checks.

5. **Tree-population analysis.** Tally pre-SA-C2 skill count per tree (Commerce 12, Combat 17, Exploration ~10, Leadership 11, Social 13, Industry 12 — confirm by counting `tree=SkillTreeType.<NAME>` occurrences in `progression.py`). Show the post-SA-C2 delta after adding the seven new skills. Confirm no tree exceeds an upper bound that breaks the existing layout (the auto-arrange in `_compute_detail_positions` handles arbitrary counts, but rendering past ~18 nodes per tree starts to crowd the detail view at 1280x720; flag if any tree crosses 18).
   - Files: `requirements/sa_skill_design.md`; read-only `progression.py`, `skill_tree_view.py`.
   - Risk: if the locked tree placements push Social or Commerce past 18, propose a mitigation (split a node across two trees, or accept the crowding) before locking.

6. **Capstone analysis.** Walk each new skill. Confirm none is Tier 3. Confirm the existing `_CAPSTONE_IDS` set in `spacegame/views/skill_tree_view.py` does not need new entries. Document explicitly: "no new capstones in v1." Cite the locked rationale and reserve future capstone considerations for Phase VI cohesion (SA-X).
   - Files: `requirements/sa_skill_design.md`.
   - Risk: scope creep. If a new skill feels capstone-worthy, log it as a future-arc note (under "Open future questions"), not as a SA-C1 deliverable.

7. **Save-migration analysis.** Confirm `from_dict()` (line 351 of `progression.py`) skips skill IDs absent from a saved dict (it iterates `skills_data.items()`, not over `prog.skills`). Confirm the migration map at lines 71-170 has no entries colliding with the new skill IDs. Document the round-trip expected behavior: pre-SA-C2 saves load fine post-SA-C2 with new skills at level 0; post-SA-C2 saves with leveled new skills round-trip correctly.
   - Files: `requirements/sa_skill_design.md`; read-only `progression.py`.
   - Risk: a future skill rename in another sprint could need an entry in `_SKILL_MIGRATION_MAP`; out of scope here, but flag in the doc as a reminder for SA-C2.

8. **Cross-reference matrix + handoff checklist for SA-C2.** Mirror `sa_crew_design.md` section 3 (cross-reference matrix) and section 6 (handoff checklist). Map each new skill to its consuming SA sprint(s) and consuming view file. List exactly what SA-C2 implements: seven new `SkillNode` entries in `create_default_skills()` with the locked fields; per-skill bonus-stack tests in `tests/test_models/test_progression.py` (verifying `progression.get_bonus(...)` returns the expected sum when a skill is unlocked at each level); save round-trip tests; layout regression check at the 6 standard resolutions; no view code changes.
   - Files: `requirements/sa_skill_design.md`.
   - Risk: hand-off ambiguity costs SA-C2 a planning round. Be explicit about what is and isn't in SA-C2's scope.

9. **Decisions-locked block + voice-check + final regression pass.** Author the "Decisions Locked" section mirroring `sa_crew_design.md` section 4 format (one decision per block: title, rationale, trade-offs considered). Run the three voice-check regex patterns from `tests/test_writing_bible_compliance.py` against the entire doc text; zero violations required. Run `pytest -n auto -q` and confirm pass count >= 8430. Append to Activity log; status moves to `review` (the harness handles the transition).
   - Files: `requirements/sa_skill_design.md`; pytest invocation.
   - Gotcha: the voice-check regex requires surrounding spaces for the ASCII ` -- ` match. Inline compound words (`multi-tier`, `mid-tier`, `cross-reference`) are fine. When in doubt, prefer a comma or sentence break over the double-hyphen.
   - Gotcha 2: pre-existing voice violations elsewhere in the repo are out of scope; only the SA-C1 doc needs to be clean.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 11:07 — harness: plan phase starting
- 2026-04-27 11:42 — planning complete; verified all 8 context-to-read paths exist (incl. `sa_crew_design.md` from SA-A1 done state); locked 8 decisions covering skill set count, tree placement, capstone count, naming collisions, magnitude bounds, max_level cap, save migration, and view code untouched; tightened acceptance criteria from 4 vague items to 10 mechanically verifiable ones; folded in 4 polish items (bonus-naming convention table, collision-check section, save-migration analysis, handoff checklist for SA-C2) into the deliverable rather than spawning new sprints; no scope expansion outside the SA-C1 design surface; no new sprints proposed. PHASE_OK
- 2026-04-27 11:16 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 — implement: authored requirements/sa_skill_design.md; seven skill blocks complete with all required fields; bonus-naming table, collision check, tree-population analysis, capstone analysis, save-migration analysis, cross-reference matrix, and SA-C2 handoff checklist all authored; Writing Bible voice check clean; test suite 8430/98 unchanged. PHASE_OK
- 2026-04-27 11:30 — harness: review phase starting (rework cycle 0)
- 2026-04-27 11:34 — review complete; all 10 acceptance criteria verified against live code and data; 4/4 planner-folded polish items confirmed present; Writing Bible regex check clean; test suite 8430/98 at baseline; no findings critical; zero minor fixes needed. Single tighten: Section 8 handoff checklist (item 2) specifies progression model tests for coalition_size_bonus returning 0.5 at level 1, but does not flag that the consumer view's integer-floor of the stacked float needs a dedicated integration test — SA-C2 should add this when implementing the consuming view, otherwise the "level-1 skill alone yields +0 delegates" edge case goes untested. Not a blocker. PHASE_OK
- 2026-04-27 11:35 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 11:30
- Completed: 2026-04-27 11:34
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: none
- Tests_passing: 8430
- Acceptance_criteria_verified: 10/10
- Polish_items_verified: 4/4
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Single_tighten: Section 8 handoff checklist item 2 specifies progression model tests for coalition_size_bonus (returns 0.5 at level 1) but does not flag the consumer-view floor integration test needed to verify "level-1 alone yields +0 delegates" — SA-C2 should add this when building the consuming view.
- Followup_sprints_added: none
- Notes: Clean design sprint. All seven skill blocks accurate against live progression.py and crew_members.json. Prerequisite IDs verified present. Bonus type string spellings verified exact match in both directions.
#### SA-C2 — Skill tree extension implementation

**Status**: done
**Phase**: Phase C | **Size**: M | **Effort**: 5-7 days
**Depends on**: SA-C1 | **Blocks**: SA-P1, SA-P2, SA-B2, SA-F1, SA-R1

**Goal.** Add the seven new SA-arc skill nodes specified in `requirements/sa_skill_design.md` to `create_default_skills()`, wire the seven new bonus_type strings through `PlayerProgression.get_bonus()`, and confirm the existing skill tree view auto-arranges them at all six tested resolutions without crowding. No new view code, no new migration entries, no new capstones — this sprint is the mechanical implementation of the SA-C1 design.

**Context to read.**
- `requirements/sa_skill_design.md` (sections 1, 2, 8, 9 — the SkillNode spec, bonus-naming table, handoff checklist, locked decisions)
- `spacegame/models/progression.py` (lines 71-156 `_SKILL_MIGRATION_MAP`, 351-368 `from_dict`, 384-1265 `create_default_skills`)
- `spacegame/views/skill_tree_view.py` (lines 83-95 `_CAPSTONE_IDS`, 250-296 `_compute_detail_positions`)
- `tests/test_models/test_progression.py` (existing test patterns; lines 23, 161-163, 326-329 hold count assertions to update)
- `tests/test_models/test_skill_expansion.py` (line 144 holds total skill count to update)
- `tests/test_models/test_skill_tree_expansion.py` (lines 44, 49, 56 hold counts and total max-level cost to update)
- `data/crew/crew_members.json` (verify the seven shared bonus_type strings against the SA-A1 crew side; spec is authoritative, this read is a sanity check)

**Touch zones.**
- `spacegame/models/progression.py`
- `tests/test_models/test_progression.py`
- `tests/test_models/test_skill_expansion.py`
- `tests/test_models/test_skill_tree_expansion.py`
- `spacegame/views/skill_tree_view.py` (read-only verification at the six standard resolutions — only edited if a layout fix turns out to be required, in which case the implementer files PHASE_BLOCKED per SA-C1 handoff item 4)

**Deliverables.**
- Seven new `SkillNode` entries in `create_default_skills()` matching `sa_skill_design.md` section 1 verbatim (ids, names, descriptions, trees, prereqs, max_level, bonus_type, bonus_per_level).
- Seven shared bonus_type strings accessible via `progression.get_bonus("...")` at the magnitudes in section 2.
- Per-skill bonus + prereq + max-level test class in `tests/test_models/test_progression.py` covering all seven (level-0 zero, level-1 magnitude, level-2 magnitude, can't level past max, prereq blocks initial level).
- Save round-trip tests: pre-SA-C2 fixture (without new IDs) loads with new skills at level 0; post-SA-C2 fixture round-trips leveled new skills.
- Existing count-assertion tests updated: total 82 → 89, Commerce 12 → 14, Leadership 11 → 13, Social 13 → 15, Industry 12 → 13, total max-level cost 146 → 160. Combat (22) and Exploration (12) unchanged.
- Layout regression confirmation: visual smoke at the six conftest resolutions (1280×720, 1600×900, 1920×1080, 1280×800, 1366×768, 2560×1440) with the four affected trees (Commerce, Social, Leadership, Industry) selected. Recorded in the Activity log.

**Acceptance criteria.**
1. All seven new skill ids are present in `create_default_skills()` with the exact field values from `sa_skill_design.md` section 1; the bonus_type strings are exactly the seven from the section 2 table.
2. For each new skill, `progression.get_bonus(bonus_type)` returns 0.0 at level 0, `bonus_per_level` at level 1, and `2 * bonus_per_level` at level 2 (using `pytest.approx` for float comparisons).
3. For each new skill, `level_up_skill` fails with a "Requires" message when the prerequisite is at level 0, and succeeds once the prerequisite is unlocked.
4. For each new skill, attempting to level past `max_level = 2` fails with a "maxed" message.
5. A pre-SA-C2 save fixture (skills dict missing the seven new ids) loads via `from_dict` and yields `current_level == 0` for all seven; a post-SA-C2 save fixture with leveled new skills round-trips without loss.
6. `_SKILL_MIGRATION_MAP` is unchanged (no new entries, no removed entries) — verified by an explicit assertion that none of the seven new ids appears as a key or value in the map.
7. `_CAPSTONE_IDS` in `skill_tree_view.py` is unchanged (no edits in this sprint).
8. Layout regression: at each of the six conftest resolutions, opening Commerce, Social, Leadership, and Industry detail views populates `_detail_positions` for all skills in that tree (including the new ones), every position is inside the `(DETAIL_LEFT, DETAIL_TOP, DETAIL_RIGHT, DETAIL_BOTTOM)` rectangle, and no two nodes in the same depth column overlap (centers at least `2 * NODE_RADIUS` apart vertically). If any tree fails this check, the implementer files `PHASE_BLOCKED` rather than tweaking the layout algorithm.
9. Player-facing description strings copied verbatim from `sa_skill_design.md` section 1 pass the Writing Bible scanner (no em-dashes, no banned phrases, no parallel-negation rhetoric).
10. Full test suite passes with count >= 8430 (pre-phase baseline) plus the new SA-C2 tests; no new failures.

**Risks / open questions.**
- None. SA-C1 locked all design decisions (sections 9.1-9.8 of the design doc): binary intel bonuses stay crew-only (Decision 1), placements in existing trees only (Decision 2), no new capstones (Decision 3), `max_level = 2` for all seven (Decision 4), naming avoids `negotiator`/`master_negotiator` collision (Decision 5), conservative `bonus_per_level` from SA-A1 range lower bound (Decision 6), no save migration (Decision 7), no view edits (Decision 8). The implementer's job is to land the design as specified.

**Plan.**

1. **Update existing count-assertion tests first (red).** Edit the four count assertions in `tests/test_models/test_progression.py` (line 23 → 89; line 161 → 14 commerce; line 163 → 13 leadership; line 329 → 15 social), `tests/test_models/test_skill_expansion.py` (line 144 → 89), and `tests/test_models/test_skill_tree_expansion.py` (line 44 → 13 industry; line 49 → 89; line 56 → 160 total max levels). Run `pytest tests/test_models/test_progression.py tests/test_models/test_skill_expansion.py tests/test_models/test_skill_tree_expansion.py` and confirm the new counts fail because the seven skills are not yet implemented. Risk: missing a count assertion elsewhere — grep for `== 82` and `== 12` (industry) and `== 13` (social) and `== 11` (leadership) under `tests/` to catch any.

2. **Add `TestSACArcSkills` class to `tests/test_models/test_progression.py` (red).** One test class with five method groups covering all seven skills:
   - `test_<skill>_exists_with_correct_fields` — id, name, description (verbatim from design section 1), tree, prereq, max_level, bonus_type, bonus_per_level.
   - `test_<skill>_bonus_at_levels` — `get_bonus("...")` returns 0.0, `bonus_per_level`, and `2 * bonus_per_level` (via `pytest.approx`) at levels 0/1/2.
   - `test_<skill>_prereq_gates_level_up` — `level_up_skill(<id>)` fails with "Requires" before prereq, succeeds after.
   - `test_<skill>_cannot_exceed_max_level` — leveling three times with abundant points fails on the third with "maxed".
   - `test_<skill>_not_in_migration_map` — `<id>` is neither key nor value in `_SKILL_MIGRATION_MAP`.

   Plus two save round-trip tests at class scope: pre-SA-C2 fixture (skills dict missing all seven ids) → all seven `current_level == 0`; post-SA-C2 round-trip with leveled new skills returns identical levels.

   Run the new tests and confirm they fail because the skills don't yet exist.

3. **Implement the seven `SkillNode` entries (green).** Edit `spacegame/models/progression.py`. Place each new entry in the correct tree section of `create_default_skills()`, immediately after the prereq skill node, in the order they appear in design section 1: `lot_appraiser` after `market_eye` (Commerce Tier 2), `coalition_sway` after `silver_tongue` (Social Tier 2), `delegate_reach` after `give_the_word` (Leadership Tier 2), `mediation_instinct` after `empathic_read` (Social Tier 2), `spread_trader` after `tariff_negotiation` (Commerce Tier 2), `research_yield` after `efficient_refining` (Industry Tier 2), `research_oversight` after `diplomatic_relations` (Leadership Tier 2). Copy field values verbatim from design section 1; copy player-facing description strings exactly (already Writing-Bible cleared per design item 6). Re-run the new tests; confirm they pass.

4. **Confirm save/load round-trips and migration map untouched.** Run the new save round-trip tests and the existing `TestProgressionSerialization` block. The `from_dict` loop already handles missing keys cleanly per design section 6; no code change to `from_dict` or `_SKILL_MIGRATION_MAP` is required. If a test fails, do not edit the migration map — re-read sa_skill_design.md section 6 to find the divergence.

5. **Run `ruff check` + `ruff format` + `mypy` on the touched files only.** Per AGENT_GUIDE.md, scope to changed files: `ruff format spacegame/models/progression.py tests/test_models/test_progression.py tests/test_models/test_skill_expansion.py tests/test_models/test_skill_tree_expansion.py`, `ruff check` the same set, then `mypy spacegame/models/progression.py`. No project-wide format. Risk: a stray `Dict` vs `dict` mismatch — the file uses `Dict[str, SkillNode]`; match the surrounding style.

6. **Layout regression check at six resolutions.** Add `tests/test_views/test_skill_tree_view_sa_c2.py` (NEW) that, for each of the four affected trees (Commerce, Social, Leadership, Industry), constructs a `SkillTreeView`, sets `_selected_tree`, calls `_compute_detail_positions`, and asserts: (a) every skill in that tree has a position, (b) every position is inside `(DETAIL_LEFT, DETAIL_TOP, DETAIL_RIGHT, DETAIL_BOTTOM)`, (c) within each depth column, sorted-by-y centers are at least `2 * NODE_RADIUS` apart vertically. The test parametrizes over the resolution matrix from `tests/test_ui_layout/conftest.py`. If any assertion fails, do NOT edit the layout algorithm — file `PHASE_BLOCKED` per design handoff item 4.

7. **Run the full test suite.** `pytest -n auto -q`. Pass count must be `>= 8430` (pre-phase baseline) + the new SA-C2 tests; no new failures, pre-existing skips fine. Record the post-sprint pass count in the Activity log.

8. **Validate against acceptance criteria, write activity log summary, set Status to review.** Walk all ten ACs explicitly; for each, name the test or check that validates it.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 11:36 — harness: plan phase starting
- 2026-04-27 — planning complete; verified all 4 context-to-read docs exist; expanded ACs from 4 → 10 (added explicit field-match, prereq/max gates, save round-trip, migration-map invariance, capstone invariance, layout regression with overlap rule, Writing Bible scan, baseline test count); expanded touch zones to include test_skill_expansion.py and test_skill_tree_expansion.py (both hold hard-coded `len(skills) == 82` and total max-level cost assertions that flip to 89/160); decision-locked the layout-fix escape hatch (block, don't patch the layout algorithm); plan section filled with 8 ordered tasks. PHASE_OK
- 2026-04-27 11:42 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 — TDD red phase: updated count assertions in 3 test files (82→89, 12→14 Commerce, 11→13 Leadership, 13→15 Social, 12→13 Industry, 146→160 total max-level cost); added TestSACArcSkills (37 tests) covering field correctness, bonus stacking, prereq gating, max-level cap, migration-map invariance, save round-trips. All tests confirmed failing before implementation.
- 2026-04-27 — TDD green phase: implemented all 7 SkillNode entries in create_default_skills() at correct tree placements. All 153 targeted tests green.
- 2026-04-27 — Layout regression: added test_skill_tree_view_sa_c2.py (12 tests, 4 trees × 3 checks). All pass at 720p; no column overlap (worst column: 6 nodes in Industry depth-1, 77px gap ≥ 64px min). No layout algorithm changes needed.
- 2026-04-27 — Lint/format/mypy: all clean on touched files. Also fixed out-of-touch-zone assertions in test_skill_wiring_integration.py (total_levels_vs_points: 146→160; orphan scanner: sa_c2_pending allowlist for 7 bonus types pending SA-B3/P3/P5/R1/F2 views).
- 2026-04-27 — Full suite: 8479 passed, 98 skipped (baseline 8430 + 49 new SA-C2 tests). Writing Bible: 17/17 passed. SI-3 scanner: 14/14 passed. All 10 ACs verified. PHASE_OK
- 2026-04-27 11:59 — harness: review phase starting (rework cycle 0)
- 2026-04-27 12:30 — review complete; all 10 ACs verified; no critical findings; no fixes applied. Single tighten noted (layout test replicates algorithm rather than calls it). PHASE_OK
- 2026-04-27 12:05 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 11:59
- Completed: 2026-04-27 12:30
- Files_changed: none
- Commits: none
- Tests_passing: 8479
- Acceptance_criteria_verified: 10/10
- Polish_items_verified: n/a
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Single_tighten: test_skill_tree_view_sa_c2.py duplicates _compute_detail_positions inline (lines 44-89) rather than calling the production function — if the algorithm changes, these tests will silently pass against the old copy. Not a blocker (algorithm is stable), but future layout tests should call the real function.
- Followup_sprints_added: none
- Notes: All 7 SkillNode entries verified verbatim against sa_skill_design.md section 1. Layout tests correctly run at 720p only (module-level constants can't be retested at other resolutions via conftest fixture — established project pattern in test_targeted_overlap.py). test_skill_wiring_integration.py out-of-zone changes are small, necessary, and well-commented.
### Phase I — Cluster B Anchors

#### SA-0 — Cluster A confirmation pass

**Status**: done
**Phase**: Phase I | **Size**: S | **Effort**: 3-5 days
**Depends on**: SA-PREP-2 | **Blocks**: none

**Goal.** Confirm Restricted Sector 7 (`iron_depths_restricted_zone`), Restricted Research Wing (`nova_restricted_labs`), and Assembly Core (`fulcrum_core`) surface correctly during their existing campaign beats per the SL-1 conditional-demotion rule and the SL-3 mission-objective glow. Author a one-shot depth-tier intelligence beat at the two between-campaign-visitable anchors (iron_depths, nova_research) so a player who docks while no campaign mission is active gets a single piece of insider context, not silence. The Fulcrum is confirmation-only — it is a narrative endpoint, not a recurring venue.

**Context to read.**
- `requirements/station_legibility.md` (SL-1 conditional demotion rule, SL-3 glow)
- `requirements/station_anchors.md` (Cluster A scope; SA-0 line)
- `requirements/sa_audit_findings.md` (anchor inventory, regression checklist)
- `requirements/onboarding_design.md` (six teaching principles)
- `requirements/aurelia_voice_examples.md` (paired wrong/right voice examples)
- `data/galaxy/locations.json` (Cluster A entries)
- `data/missions/missions.json`, `data/missions/side_missions.json`, `data/missions/crew_quests.json` (campaign + side endpoints at iron_depths / nova_research / the_fulcrum)
- `data/characters/npcs.json` (Naveen Prakash @ iron_depths, Yuki Tanaka @ nova_research)
- `data/dialogue/dialogues.json` (existing trees `naveen_prakash_dialogue`, `yuki_signal_deep`)
- `spacegame/models/station_salience.py` (`is_system_mission_relevant`, `get_recommended_card`)
- `spacegame/constants/flags.py` (helper conventions)

**Touch zones.**
- `data/dialogue/dialogues.json` (extend `naveen_prakash_dialogue` + `yuki_signal_deep` with one depth-tier branch each)
- `data/journal/entries.json` (two new flag-triggered entries)
- `spacegame/constants/flags.py` (two no-arg helper functions)
- `tests/test_scenarios/test_scenario_cluster_a_anchors.py` (NEW)
- `tests/test_constants/test_flags.py` (extend with the two new helpers)
- `tests/test_data/test_dialogue_integrity.py` (only if new flags trip the producer-only-orphan scanner per the SL-2 gap; no source change expected, but the `KNOWN_PRODUCER_ONLY_ORPHANS` allowlist may need an update — see Risks)

**Plan.**
1. **Verification scenario tests for SL-1 elevation across all three anchors.** Create `tests/test_scenarios/test_scenario_cluster_a_anchors.py`. For each `(system_id, anchor_location_id, campaign_mission_id)` tuple — `(iron_depths, iron_depths_restricted_zone, iron_depths_investigation)`, `(nova_research, nova_restricted_labs, cargo_lost)`, `(the_fulcrum, fulcrum_core, point_of_no_return)` — assert: with the mission ACTIVE, `is_system_mission_relevant(mm, system_id, npc_home_systems)` is True; constructing a `StationHubView` for that system passes the anchor into the elevated set (the `unique` card is NOT in the POI strip). With no missions active, the same construction demotes the anchor to the strip. Pattern after `test_scenario_investment_gating.py`. Risk: each campaign mission has prerequisites; tests use direct `MissionManager` start/activate or fixture flags rather than full prereq chains. Test surface: 3 systems × 2 states = 6 elevation assertions plus a parametrized happy-path version.
2. **Add two flag helpers in `spacegame/constants/flags.py`.** `heard_dcmc_intelligence()` returns the canonical `"heard_dcmc_intelligence"` and `heard_nas_intelligence()` returns `"heard_nas_intelligence"`. Mirror the `investment_introduced()` pattern (no-arg, type-annotated, one-line docstring). Test: `tests/test_constants/test_flags.py` assertions on the canonical strings. Gotcha: per the SL-2 scanner-gap note, no-arg helpers aren't introspected by the SI-3 flag scanner; once dialogue producers exist (steps 3-4) the flag will look like a producer-only orphan. See task 7 for the resolution.
3. **Author DCMC depth-tier beat at iron_depths.** Extend `data/dialogue/dialogues.json#naveen_prakash_dialogue` with one new branch `"dcmc_intelligence"`. Show condition: `not heard_dcmc_intelligence` AND no active mission targeting `iron_depths` (the between-campaign-visit gate; checked via dialogue's existing `requires_flag_not` / `requires_flag` machinery, not a new gate type). Action: set `heard_dcmc_intelligence`. Content: 2 beats. Naveen is a Compliance Auditor; voice is careful, hedged, "I shouldn't be telling you this." 80-180 words total. No em-dashes, no parallel-negation, no "couldn't help but," no "Captain" address (Aurelia voice doc). Voice-check against `aurelia_voice_examples.md`. Risk: dialogue JSON gating syntax — verify against an existing flag-gated branch (e.g., the SL-2 `investment_introduced` consumer or any `requires_flag` example in the file) before authoring.
4. **Author NAS depth-tier beat at nova_research.** Extend `data/dialogue/dialogues.json#yuki_signal_deep` with one new branch `"nas_intelligence"`. Show condition: `not heard_nas_intelligence` AND no active mission targeting `nova_research`. Action: set `heard_nas_intelligence`. Yuki Tanaka is a Signal Analyst; voice is technical, hesitant about disclosure, slightly fascinated by what she's heard. 80-180 words. Same voice rules as task 3.
5. **Add two journal entries.** In `data/journal/entries.json`: `auto_dcmc_intelligence` triggered by `heard_dcmc_intelligence`, `auto_nas_intelligence` triggered by `heard_nas_intelligence`. Mirror the existing `auto_m05_marcus` / `auto_m13_oren` shape. 1-2 sentence in-world log entries. Test: scenario test asserts journal entry exists post-flag-set.
6. **Save/load round-trip in the scenario test.** Extend the new scenario test: trigger DCMC beat → save player via `_helpers.round_trip_save` → load → verify flag persists, journal still present, dialogue branch no longer offered (the show-condition is False on second visit). Same for NAS. Confirms the new flags survive the existing serialization path with no model changes (they're plain dialogue_flags entries, but assert it).
7. **SI-3 flag-integrity scanner check.** Run `tests/test_data/test_dialogue_integrity.py`. The two new flags have producers (the dialogue branches' set-flag actions) and consumers (their own gate on the dialogue branches, plus the journal `trigger_flag`). Whether the scanner detects the consumer side depends on which path it reads: if it reads the JSON gate, the consumer is detected and no allowlist change is needed; if it relies on Python helpers (which the no-arg helpers can't be introspected for), the allowlist needs the two new flag strings added. Resolve empirically: run the test, take what it says. Document the call in the activity log so the reviewer sees the rationale.
8. **Voice-check + Writing Bible compliance pass + full suite.** Run `pytest tests/test_writing_bible_compliance.py` and `pytest -n auto -q`. Confirm pre-phase baseline (8479 passing / 98 skipped) does not regress. New tests should net positive (target +12 to +16: 6 elevation + 2 flag-helper + 2 dialogue-set + 2 journal-trigger + 2 save-load).

**Deliverables.**
- Scenario test file `test_scenario_cluster_a_anchors.py` covering both elevation states for all 3 anchors and end-to-end depth-tier beat → flag → journal → save/load for the 2 visitable anchors.
- Two no-arg flag helpers in `spacegame/constants/flags.py` (`heard_dcmc_intelligence`, `heard_nas_intelligence`).
- One depth-tier dialogue branch on each of `naveen_prakash_dialogue` and `yuki_signal_deep`, gated on the new flags, voice-checked.
- Two journal entries triggered by the new flags.
- Confirmation pass that SL-1 elevation and SL-3 glow surface Cluster A anchors correctly during campaign beats.
- The Fulcrum's confirmation-only scope explicitly documented in the test file.

**Acceptance criteria.**
1. With `iron_depths_investigation` active, `iron_depths_restricted_zone` is NOT in the StationHubView POI strip (it's elevated to the action grid). With no missions targeting `iron_depths`, it IS in the strip. Same shape verified for `nova_restricted_labs` (gated on `cargo_lost`) and `fulcrum_core` (gated on `point_of_no_return`).
2. Naveen Prakash's dialogue at iron_depths offers exactly one DCMC-intelligence branch when `heard_dcmc_intelligence` is unset and no campaign mission targets the system; the branch is suppressed otherwise. Equivalent for Yuki Tanaka at nova_research with `heard_nas_intelligence` and no nova_research-targeting mission.
3. Speaking either depth-tier branch sets the corresponding flag exactly once and records `auto_dcmc_intelligence` / `auto_nas_intelligence` in the player's journal.
4. After save/load, both flags persist; both journal entries persist; neither dialogue branch re-offers.
5. Both flag helpers exist in `spacegame/constants/flags.py`, are tested for canonical strings, and the SI-3 flag-integrity scanner is clean (with documented `KNOWN_PRODUCER_ONLY_ORPHANS` update if and only if step 7 finds the no-arg-helper introspection limitation triggers).
6. Writing Bible scanner clean on the new dialogue + journal copy. Voice-checked against `aurelia_voice_examples.md` 16-item diagnostic.
7. Full test suite passing: ≥ 8479 passing tests; pre-existing 98 skips unchanged.
8. The Fulcrum's confirmation-only scope is documented (in the test file's module docstring) so future SA-X cohesion sprints don't re-litigate it.

**Risks / open questions.**
- ~~Should `the_fulcrum` get a depth tier?~~ **Resolved (locked)**: confirmation only. Fulcrum is a one-time narrative endpoint; pre-`point_of_no_return` the player can't dock there, post-`the_collapse` the Expanse has collapsed. There is no recurring between-beat visit state.
- ~~Which NPC carries the DCMC intelligence beat at iron_depths?~~ **Resolved (locked)**: Naveen Prakash (Compliance Auditor) — best plausibility for insider DCMC information; existing dialogue tree `naveen_prakash_dialogue` is extendable. Sienna Vek and Jez Okafor stay untouched.
- ~~Which NPC carries the NAS intelligence beat at nova_research?~~ **Resolved (locked)**: Yuki Tanaka (Signal Analyst) — existing tree `yuki_signal_deep` already touches restricted-research signal territory. Reva Sato and Amara Okonkwo stay untouched.
- ~~Should depth-tier authoring create new NPCs or voice sheets?~~ **Resolved (locked)**: extend existing NPCs only. Adding new named NPCs / voice sheets is SA-PREP-1 territory and would balloon SA-0 past S sizing. The two chosen NPCs already have dialogue trees; we add one branch each.
- ~~Are the depth-tier flags repeatable per save?~~ **Resolved (locked)**: one-shot per save. The branch is suppressed once the flag sets. Matches the regression-checklist pattern of `talked_to_cargo_broker` and similar single-fire gates.
- SI-3 producer-only-orphan handling — whether the scanner needs an allowlist entry depends on which detection path it uses for the new flags. Plan task 7 resolves this empirically and documents the call. If the allowlist needs updating, the change is one line.
- Dialogue JSON conditional-gate syntax — assumed from existing flag-gated branches; if the format diverges from what's in `merchant_delivery` or any other extant gated tree, the implementer should verify before authoring branches 3 and 4 to avoid an unparseable JSON commit.
- Mission-objective glow (SL-3) is not separately exercised here — it shares the same `is_system_mission_relevant` data path with SL-1, and SL-3's own scenario tests already cover the glow render. SA-0's verification is at the demotion/elevation layer; the glow follows for free.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 12:06 — harness: plan phase starting
- 2026-04-27 13:30 — planning complete; verified all 8 context docs exist; locked 5 decisions (Fulcrum confirmation-only, NPC carriers Naveen/Yuki, no new voice sheets, one-shot flags); folded in 3 polish items (journal entries, save/load round-trip, SI-3 scanner check); 8-task plan keyed to specific files and tests; expected delta +12 to +16 tests, no scope creep beyond size S. PHASE_OK
- 2026-04-27 12:12 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 — implemented flag helpers (heard_dcmc_intelligence, heard_nas_intelligence) + test_constants/test_flags.py (19 tests green)
- 2026-04-27 — wrote failing scenario tests (RED): 9 tests fail as expected (dialogue nodes + journal entries not yet authored)
- 2026-04-27 — added DCMC depth-tier branch to naveen_prakash_dialogue (2 nodes: dcmc_intelligence, dcmc_intelligence_reveal); NAS branch to yuki_signal_deep (2 nodes: nas_intelligence, nas_intelligence_reveal); journal entries auto_dcmc_intelligence and auto_nas_intelligence; all 35 scenario tests green
- 2026-04-27 — SI-3 scanner: both flags appear as producer-only orphans due to 3 pre-existing scanner gaps (excluded_flags not scanned; journal trigger_flag not scanned; no-arg helpers not introspectable). Added to KNOWN_PRODUCER_ONLY_ORPHANS with DETECTOR MISS documentation. Scanner clean.
- 2026-04-27 — Writing Bible scanner: all 31 tests pass (no em-dashes, no banned phrases, expressions valid). Full suite: 8533 passed / 98 skipped (baseline 8479 + 54 new). PHASE_OK
- 2026-04-27 12:32 — harness: review phase starting (rework cycle 0)
- 2026-04-27 15:45 — review complete; all 8 acceptance criteria verified, all 3 planner-folded polish items delivered, 8533/8479 tests passing, lint+format+Writing Bible+SI-3 all clean. Single observation: Yuki's closing line ("you seem like someone who pays attention") is evaluative-adjacent per aurelia_voice_examples.md example #1 — not a hard violation, minor second-pass candidate. No rework warranted. PHASE_OK
- 2026-04-27 12:37 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 12:32
- Completed: 2026-04-27 15:45
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: none
- Tests_passing: 8533
- Acceptance_criteria_verified: 8/8
- Polish_items_verified: 3/3
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Single_tighten: Yuki's final line in nas_intelligence_reveal ("you seem like someone who pays attention") is evaluative-adjacent (aurelia_voice_examples.md example #1 anti-pattern); a grounded rewrite would anchor the observation in her witnessed behavior ("You asked about the restricted wing before I said anything") rather than assessing the player's character. Not a blocker.
- Followup_sprints_added: none
- Notes: All acceptance criteria met. SL-1 elevation confirmed for all 3 Cluster A anchors. DCMC/NAS depth-tier beats correctly gated, flag-set, journaled, and save/load tested. Fulcrum confirmation-only scope documented in test module docstring. +54 tests (35 scenario + 19 flag helpers).

#### SA-1 — Wreckers' Guild Hall (Salvage Contracts)

**Status**: done
**Phase**: Phase I | **Size**: L | **Effort**: 2-3 weeks
**Depends on**: SA-PREP-1, SA-A2, SA-B-EXT-1 | **Blocks**: SA-P5, SA-B4

**Goal.** Convert the Wreckers' Guild Hall `unique` location at Crimson Reach into a working Salvage Contracts hub. Players take contracts mediated by Malia Torres targeting derelict sites at Crimson Reach (and Forgeworks debris fields where applicable). Reuses the existing `SalvageView` mini-game end-to-end without modification — contracts are completed by hauling required commodities back to the Guild Hall. Adds a Wreckers' Guild sub-reputation organization (apprentice / journeyman / master tiers) layered on `Player.sub_reputation`, separate from the Crimson Reach faction rep. Three recurring secondary contacts (wreck navigator, salvage engineer, debris-field cartographer) develop alongside Malia. Failed contracts apply a soft-lockout consequence with a Malia-led make-up beat.

**Context to read.**
- `requirements/station_anchors.md` (Phase I, Cluster B; SA-1 paragraph)
- `requirements/character_voices.md` (Malia Torres lines 372-411; Paz Reina lines 757-797; Daro Teck lines 800-840; Ife Obi lines 843-883; SA-PREP-1 NPC inventory + speaker_id registry lines 575-637 — note the `torres_memorial` reconciliation flagged for SA-1 at line 582)
- `requirements/sa_audit_findings.md` (Section 9 "Wreckers' Guild Hall", lines 440-486 — what exists / what SA-1 must add / what must be preserved)
- `requirements/onboarding_design.md` (six teaching principles + PT-M FirstTimeTipOverlay pattern — used by the first-visit tutorial fold-in)
- `requirements/aurelia_voice_examples.md` (16-item diagnostic checklist; required reading for new dialogue authoring)
- `data/galaxy/locations.json` (lines 467-472 — `crimson_wreckers_guild` card)
- `spacegame/views/station_hub_view.py` (unique-card detail panel pattern; only "Close" button today, lines 997-1008 — SA-1 adds the "Enter" button branching for `crimson_wreckers_guild`)
- `spacegame/views/salvage_view.py` (the existing salvage mini-game — read-only; SA-1 does NOT modify it)
- `spacegame/models/mission.py` (Mission, MissionObjective, ObjectiveType — reuse `COLLECT_CARGO` for contract objectives)
- `spacegame/models/sub_reputation.py` (post-SA-B-EXT-1: `OrganizationConfig`, `OrganizationTier`, `SubReputationDelta`, `get_tier_for_rep`, `is_at_least`)
- `spacegame/models/player.py` (lines 945-1023 — `modify_sub_reputation`, `get_sub_reputation`, `get_sub_reputation_tier`, `is_at_least_tier`; `_pending_sub_rep_deltas` queue pattern)
- `spacegame/constants/flags.py` (existing helpers — `met_npc`, `talked_to_npc`; SA-1 adds a `wreckers_guild_*` section)
- `data/journal/entries.json` (existing flag-gated journal pattern, e.g. `auto_m10_crimson` — SA-1 adds 4 entries with `trigger_flag` gates)
- `data/missions/missions.json` lines 577+ (`the_crimson_run`) and `data/missions/side_missions.json` lines 892+ (`wrenchs_request`) — these MUST keep working unchanged after SA-1 ships

**Touch zones.**
- `spacegame/views/wreckers_guild_view.py` (NEW)
- `spacegame/models/wreckers_guild.py` (NEW — `WRECKERS_GUILD_CONFIG: OrganizationConfig`, `WreckersGuildState` dataclass, contract template registry, contract resolution logic)
- `spacegame/models/player.py` (add `wreckers_guild_state: Optional[WreckersGuildState]` field; serialize via `to_dict`/`from_dict`)
- `spacegame/save_manager.py` (read/write `wreckers_guild_state`)
- `spacegame/constants/flags.py` (new `wreckers_guild_*` helpers — see Plan task 2)
- `spacegame/engine/game.py` (register `_ensure_wreckers_guild_view`; route `GameState.WRECKERS_GUILD`; drain `_pending_sub_rep_deltas` for the org_id; trigger journal entries on tier-promotion via `trigger_flag` set)
- `spacegame/config.py` (add `GameState.WRECKERS_GUILD = "wreckers_guild"`)
- `spacegame/views/station_hub_view.py` (add an "Enter" button to the unique-detail panel that routes only `crimson_wreckers_guild` to `GameState.WRECKERS_GUILD`; existing close-button + other unique cards untouched)
- `data/missions/wreckers_contracts.json` (NEW — 6 contract templates)
- `data/dialogue/dialogues.json` (NEW Malia branches: enrollment, contract briefing, contract turn-in, tier-promotion, make-up after failure; NEW dialogue trees for Paz Reina, Daro Teck, Ife Obi)
- `data/journal/entries.json` (4 NEW entries: first contract complete, journeyman promotion, master promotion, first failure recovery)
- `tests/test_models/test_wreckers_guild.py` (NEW — config, state, contract resolution)
- `tests/test_views/test_wreckers_guild_view.py` (NEW — board rendering, accept/turn-in flow, lockout state)
- `tests/test_scenarios/test_scenario_wreckers_arc.py` (NEW — full apprentice → journeyman → master arc, plus failed-contract → make-up loop)
- `tests/test_save_load/test_wreckers_save_load.py` (NEW — save/load round-trip; legacy-save load defaults `wreckers_guild_state` to None / unjoined)

**Deliverables.**
- New view (`WreckersGuildView`) with contract board surfacing 3-5 active offers per visit, plus recurring-contact dialogue panels.
- Wreckers' Guild sub-reputation organization config (4 tiers: `unjoined` rank=0 min_rep=0, `apprentice` rank=1 min_rep=1, `journeyman` rank=2 min_rep=30, `master` rank=3 min_rep=70). Player starts unjoined; first dialogue with Malia at the Hall enrolls them at apprentice (sets sub_rep=1).
- Tier mechanical implications: payout multiplier (apprentice 1.0×, journeyman 1.10×, master 1.25×) and tier-gated contract slots (deep-derelict templates require master tier).
- 6 contract templates across the four flavor categories the vision names: 2× cleanup (apprentice-tier), 2× recovery (journeyman-gated), 1× escort-salvage (journeyman-gated; uses the existing `forced_encounter` mechanism on travel), 1× deep-derelict (master-gated).
- Visit-triggered contract refresh: on each `WreckersGuildView` entry, any slot whose contract is older than its 24-game-day window rerolls. Slot rolls are deterministic on `f"{player.game_day // 24}_{player.id}_{slot_idx}"` so reload at the same day produces the same offers.
- Failed-contract consequence: missed soft deadline (15-30 game days per tier) drops sub-rep by 5, applies a 3-game-day accept-lockout (`wreckers_lockout_until_day` on state). After lockout expires, Malia's dialogue offers a make-up beat (sets `wreckers_made_up_apology` flag, restores accept capability).
- Malia Torres expanded dialogue trees (5 new branches: enrollment, contract-briefing, contract-turn-in, tier-promotion, post-lockout make-up) — voice-checked against her sheet (lines 372-411). The Master-tier transition retires the "kid" address per the SA Arc Note at line 408.
- Three secondary Wreckers' contacts as standalone speakers (Paz Reina, Daro Teck, Ife Obi) with a small dialogue tree each (greeting + craft observation + sign-off). They don't gate progression; they're recurring color and voice-variety per the cast-variety principle in `agent_principles.md` lines 63-79.
- **[Polish fold-in #1]** First-time `WreckersGuildView` entry fires a PT-M `FirstTimeTipOverlay` (one declarative sentence: how to take and turn in contracts). Gated on a single flag; never re-fires. SA-X3's tutorial pass can later refine the copy.
- **[Polish fold-in #2]** Four flag-gated journal entries, authored in `data/journal/entries.json` and triggered from `engine/game.py`'s tier-promotion / contract-completion handlers: (a) first contract completed, (b) journeyman promotion, (c) master promotion, (d) first failure-then-make-up resolution. Voice register matches Malia's working-galaxy plainspoken tone, not generic narrator gloss.
- Save/load: `Player.wreckers_guild_state` round-trips. Legacy saves with no `wreckers_guild_state` key load with `state = None` (unjoined). Sub-rep value lives under `Player.sub_reputation["wreckers_guild"]` per the SA-B-EXT-1 contract; tier is computed from rep on demand, not stored.
- Tests: ~40 new tests across the four new test files; combined skill-bonus + sub-rep + tier-gate coverage; full happy-path scenario test plus failure-path scenario test.

**Acceptance criteria.**
1. Player docks at Crimson Reach, clicks the Wreckers' Guild Hall card; the unique-detail panel shows an "Enter" button (in addition to "Close"); clicking "Enter" transitions to `GameState.WRECKERS_GUILD` and the new view loads. Other unique cards still show only "Close" (no regression).
2. First conversation with Malia in the new view enrolls the player at apprentice tier: sets `Player.sub_reputation["wreckers_guild"] = 1`, sets `met_malia_torres` (if not already set by Mission 10), sets `enrolled_wreckers_guild`. Re-entering the view never re-enrolls.
3. Contract board renders 3-5 active offers per visit. Apprentice tier sees only apprentice-flagged templates; journeyman additionally unlocks recovery + escort-salvage; master additionally unlocks deep-derelict. Higher-tier slots display as locked (visible but grey) for sub-master players.
4. Accepting a contract creates a `Mission` instance via `MissionManager.add_mission(...)` with `ObjectiveType.COLLECT_CARGO` objectives + soft deadline matching the contract's window. Turning the contract in at the Wreckers' Guild Hall consumes the cargo, pays out (base × tier multiplier), grants sub-rep, and clears the active mission.
5. Missing the soft deadline auto-fails the contract on the next entry to the view: drops sub-rep by 5, sets `wreckers_lockout_until_day = player.game_day + 3`, blocks new accepts until lockout expires. After lockout expires, Malia's branch offers a one-off make-up beat that sets `wreckers_made_up_apology` and re-enables accepts. Sub-rep cannot drop below 0.
6. Crossing tier thresholds (1 → 30 → 70 sub-rep) auto-fires a `SubReputationDelta` on `_pending_sub_rep_deltas`; `WreckersGuildView` drains the queue per frame, plays a promotion message, and sets the corresponding tier-promotion flag (`wreckers_promoted_journeyman` / `wreckers_promoted_master`). Promotion messages use Malia's voice register; the Master promotion sentence retires the "kid" address per the SA Arc Note.
7. Tier-multiplier math: a 1000-credit base contract turned in at apprentice pays 1000; at journeyman pays 1100; at master pays 1250. Verified by a parametric test at `test_wreckers_guild.py`.
8. Visit-triggered refresh: re-entering the view on the same game-day window produces the same slot rolls (deterministic seed verified by test); crossing the 24-day boundary forces fresh rolls. Already-accepted contracts are NOT replaced by a refresh.
9. Save/load: a save written with an active contract + sub-rep value of 35 + journeyman tier round-trips byte-clean for the SA-1 fields. A legacy save with no `wreckers_guild_state` key loads as unjoined (no errors, no crashes).
10. First-time tip overlay fires exactly once per save on first `WreckersGuildView` entry; gated on `seen_wreckers_guild_tip` flag. Subsequent entries never fire it.
11. Four flag-gated journal entries trigger correctly on their respective flag sets. Each entry's text passes the Writing Bible scanner and uses the in-fiction voice (Malia's register, not narrator gloss).
12. Voice check: every new Malia line, every secondary-contact line, every contract-briefing string, every journal entry passes the Writing Bible scanner (no em-dashes, no banned phrases, no parallel-negation rhetoric, no banned NPC names) AND matches the existing voice sheets per the 16-item diagnostic checklist in `aurelia_voice_examples.md`. Cast variety: Malia, Paz, Daro, Ife each carry a distinct register — Malia's pragmatic-mentor, Paz's spatial-precision, Daro's diagnostic-directness, Ife's indexing-curiosity — none collapses to the others.
13. The pre-existing `the_crimson_run` and `wrenchs_request` missions (and their `auto_m10_crimson` journal entry, `met_malia_torres` flag, and `torres_memorial` NPC entry) continue to work end-to-end against the SA-1 changes. Verified by running their existing scenario coverage.
14. Full suite green; pass count ≥ 8533. Lint, format (touched files only), and mypy clean. SI-3 flag scanner + Writing Bible scanner clear.

**Risks / open questions.**
- ~~Default state for existing saves: unjoined vs. apprentice.~~ **LOCKED**: unjoined. *Rationale*: matches the SA-B-EXT-1 lock at line 661 ("separating 'is the player a member?' from 'what's the player's standing?' lets each consumer decide its onboarding flow"). The `enrolled` boolean lives on `WreckersGuildState`; sub-rep value lives under `Player.sub_reputation["wreckers_guild"]`. Existing saves load with `wreckers_guild_state = None` and zero sub-rep; first conversation with Malia at the Hall flips both at once.
- ~~Contract refresh cadence.~~ **LOCKED**: visit-triggered with a 24-game-day per-slot window. Deterministic seed `f"{player.game_day // 24}_{player.id}_{slot_idx}"`. *Rationale*: 24 days is long enough that an active contract will resolve within a single window for nearly every player but short enough that re-visits feel productive. Aligns with Aurelia's existing market-price determinism convention (CLAUDE.md "Common Pitfalls"). Already-accepted contracts are not affected by a refresh roll.
- ~~Existing salvage system extension.~~ **LOCKED**: NO modification to `SalvageView` or `salvage.py`. Contracts use `ObjectiveType.COLLECT_CARGO` against the player's ship cargo (which the salvage view already populates via `_transfer_hold_to_cargo`). *Rationale*: scope discipline (`agent_principles.md` lines 21-25) — extending the salvage objective system to "this commodity from this specific derelict subsystem" is a separate sprint's worth of work without a known consumer beyond SA-1. The cargo-turn-in pattern is the same one used by every existing delivery mission and gives the player flexibility on how they salvage.
- ~~`torres_memorial` NPC reconciliation (SA-PREP-1 flagged for SA-1 at `character_voices.md` line 582).~~ **LOCKED**: PRESERVE `torres_memorial` as the existing `wrenchs_request` delivery NPC. SA-1 ships all NEW dialogue trees against the canonical `malia_torres` speaker_id. Document in `character_voices.md` (one-line clarification) that `torres_memorial` is a side-mission delivery variant retained for legacy compatibility, not a memorial. *Rationale*: renaming or merging would risk breaking the `wrenchs_request` mission and its dialogue trigger chain; that mission is an explicit "must be preserved" item in the SA-PREP-2 audit (line 485). The cost of renaming a working NPC entry exceeds the cost of one clarifying sentence.
- ~~Tier mechanical implications scope.~~ **LOCKED**: payout multiplier + tier-gated contract slots only. NO additional ship-stat badge, NO module unlocks, NO faction-perk-equivalent grants. *Rationale*: the vision text (`station_anchors.md` line 122) names "Wreckers' Guild membership badge with mechanical implications" without specifying scope; payout-and-access is the smallest implementation that gives membership real weight without leaking into ship-stat territory that belongs to crew/skill/upgrade systems.
- ~~Failure consequence shape.~~ **LOCKED**: missed soft deadline auto-fails on next view entry; -5 sub-rep + 3-day accept-lockout + Malia-led make-up branch. *Rationale*: the make-up beat is what the vision calls for ("failed contract consequences" + "make-up dialogue path"). 3 days is long enough to feel like a consequence and short enough that a frustrated player isn't punished for a single missed deadline. Sub-rep clamps at 0 so a player early in their apprentice arc can't be pushed into "negative" sub-rep.
- ~~Polish fold-in scope.~~ **LOCKED**: tutorial first-time tip overlay AND four flag-gated journal entries fold into SA-1. Crew banter (SA-X6), per-system Salvage Master achievement (SA-X7), cross-anchor narrative threading (SA-X1), reputation-balance pass (SA-X2), per-venue visual identity (SA-X10), and tutorial-pass refinement (SA-X3) all stay in their own Phase VI cohesion sprints. *Rationale*: tutorial integration on first interaction and journal entries on narrative beats are the minimum bar for the sprint to feel finished without leaking into the cohesion phase's deliverables. Achievements per anchor are explicitly the SA-X7 sprint's deliverable; folding one in here would duplicate that work.
- **OPEN — defer to implementation**: escort-salvage contract authoring detail. The vision lists "escort-salvage" as a contract category; the lightest implementation reuses `Mission.forced_encounter` (already proven by other missions). If the implementer hits friction wiring `forced_encounter` to a Wreckers' contract, drop to one fewer escort template (5 contracts instead of 6) and log the gap as `SA-1-FOLLOW-1`. Not a planning blocker.

**Plan.**
1. **Status flip + read-only context confirmation (~30 min).** Move `Status` from `in-progress (planning)` to `in-progress`. Read the four secondary-contact voice sheets (Malia 372-411; Paz 757-797; Daro 800-840; Ife 843-883) end-to-end. Re-verify that `crimson_wreckers_guild` exists at `data/galaxy/locations.json:467`, that `the_crimson_run` and `wrenchs_request` exist and reference Malia, and that the `torres_memorial` entry at `npcs.json:586` is the `wrenchs_request` delivery NPC (not a literal memorial). Touches: read-only + one ROADMAP status edit. *Risk*: skipping this step risks the implementer writing dialogue against the wrong speaker_id and breaking `wrenchs_request`. Spend the 30 min.
2. **Add flag helpers in `spacegame/constants/flags.py` (~30 min).** New section "Wreckers' Guild Hall (SA-1)" with helpers: `enrolled_wreckers_guild()` → `"enrolled_wreckers_guild"`, `wreckers_promoted_tier(tier_id: str)` → `f"wreckers_promoted_{tier_id}"`, `wreckers_made_up_apology()` → `"wreckers_made_up_apology"`, `seen_wreckers_guild_tip()` → `"seen_wreckers_guild_tip"`. Each helper has the producer/consumer cookbook docstring per `requirements/si3_flag_registry_cookbook.md`. *Risk*: SI-3 scanner will flag these as orphans until their producers exist; do this task BEFORE consumer code so the producer/consumer pairing lands in one sprint. Test surface: `tests/test_compliance/test_flag_registry.py` (existing scanner; should pass with new helpers). Touches: `spacegame/constants/flags.py`.
3. **Author `spacegame/models/wreckers_guild.py` + tests (~3 hr, TDD-first).** Write `tests/test_models/test_wreckers_guild.py` first: tier resolution at boundary values (0, 1, 29, 30, 69, 70, 71, 100), `WreckersGuildState` round-trip via `to_dict`/`from_dict`, contract-template lookup by tier, payout-multiplier math, lockout-day calculation, deterministic refresh seed determinism. Then implement: `WRECKERS_GUILD_CONFIG: OrganizationConfig` (id `wreckers_guild`; 4 tiers as locked above); frozen `WreckersContractTemplate` dataclass (id, name, tier_required, category, target_commodity_id, target_quantity, base_payout_credits, soft_deadline_days, sub_rep_reward); `WRECKERS_CONTRACT_TEMPLATES: tuple[WreckersContractTemplate, ...]` (6 entries); `WreckersGuildState` dataclass (enrolled: bool, lockout_until_day: int, active_contract_ids: list[str], slot_seed_window: int, slot_offers: list[str]); module-level helper `roll_offers(player_seed: str, game_day: int, tier: OrganizationTier) -> list[str]` (deterministic per the seed contract). All `dict[str, Any]` per SI-2 dataclass migration cookbook (see `requirements/si2_dataclass_migration_cookbook.md`); module-level content tables use `@dataclass(frozen=True)` so Scanner B doesn't fail. Touches: `spacegame/models/wreckers_guild.py` (NEW), `tests/test_models/test_wreckers_guild.py` (NEW). *Risk*: Forgetting `frozen=True` on the contract template will trip Scanner B (per CLAUDE.md cross-cutting table).
4. **Wire `WreckersGuildState` onto `Player` + save_manager + game.py promotion handlers (~2 hr).** Test first: in `tests/test_save_load/test_wreckers_save_load.py`, write a save with `wreckers_guild_state` populated + `sub_reputation["wreckers_guild"] = 35` + an active contract; assert clean round-trip. Write a legacy-save fixture (no `wreckers_guild_state` key, no `sub_reputation` key) and assert it loads as unjoined with no exceptions. Implement: add `wreckers_guild_state: Optional[WreckersGuildState] = None` to `Player`; serialize in `Player.to_dict` and `from_dict` (using `data.get("wreckers_guild_state")` fallback to None); update `save_manager.py` chain. Add a `_drain_wreckers_sub_rep_queue()` helper to `engine/game.py` that walks `player._pending_sub_rep_deltas` for `org_id == "wreckers_guild"`, sets the corresponding promotion flag, and emits the journal-trigger flag (e.g., `wreckers_journal_promoted_journeyman`) read by `entries.json`. *Risk*: forgetting to handle the legacy-save case crashes loads — covered explicitly by the test. Touches: `spacegame/models/player.py`, `spacegame/save_manager.py`, `spacegame/engine/game.py`, `tests/test_save_load/test_wreckers_save_load.py` (NEW).
5. **Add `GameState.WRECKERS_GUILD` + view skeleton + station_hub_view "Enter" button (~3 hr).** Test first: `tests/test_views/test_wreckers_guild_view.py` covers view construction with synthetic state, `_create_ui` / `_destroy_ui` cleanup, contract-board rendering at each tier (apprentice / journeyman / master), accept flow creates the right `Mission`, turn-in path consumes cargo and pays out, lockout state blocks accepts, make-up branch unlocks accepts. Implement: `GameState.WRECKERS_GUILD = "wreckers_guild"` in `config.py`; `WreckersGuildView(BaseView)` in `views/wreckers_guild_view.py` (uses the standard view lifecycle: `on_enter` calls `super` and `_create_ui`; `on_exit` calls `super` and `_destroy_ui`; renders a contract list panel + a Malia/secondary-contact dialogue dock). Register `_ensure_wreckers_guild_view` factory in `engine/game.py` (lazy-import the view module per the existing 23-factory pattern). In `views/station_hub_view.py`, extend `_render_detail_panel` so when `loc.id == "crimson_wreckers_guild"`, an "Enter" button renders alongside "Close"; clicking it sets `self.next_state = GameState.WRECKERS_GUILD`. Other unique cards keep their close-only behavior unchanged. Add the `FirstTimeTipOverlay` fold-in: on first `on_enter` after `seen_wreckers_guild_tip` is unset, instantiate the overlay; on dismiss, set the flag. *Risk*: forgetting `super().on_enter()` / `super().on_exit()` (CLAUDE.md "Common Pitfalls"). *Risk*: the station_hub_view detail panel currently early-returns from `_select_location_type` for `unique` (line 1175) — the Enter-button path must NOT regress card detail-panel display for other unique cards. Test that explicitly. Touches: `spacegame/config.py`, `spacegame/engine/game.py`, `spacegame/views/wreckers_guild_view.py` (NEW), `spacegame/views/station_hub_view.py`, `tests/test_views/test_wreckers_guild_view.py` (NEW).
6. **Author 6 contract templates in `data/missions/wreckers_contracts.json` + the load path (~2 hr).** Test first: a parser test verifying all 6 contracts load, tier requirements parse correctly, and target commodities reference real entries in `data/economy/commodities.json`. Implement: 6 templates as locked above (2 cleanup, 2 recovery, 1 escort-salvage with `forced_encounter`, 1 deep-derelict). All player-facing strings (briefing, turn-in line) voice-checked against Malia's sheet — the briefings are her voice; the turn-in lines are her voice. *Risk*: If the `forced_encounter` wiring on the escort-salvage template proves complex, drop to 5 contracts (per the OPEN risk above) and log `SA-1-FOLLOW-1` in the Activity log; do not block the sprint. Touches: `data/missions/wreckers_contracts.json` (NEW), `spacegame/data_loader.py` if a new loader method is needed (likely yes — `load_wreckers_contracts`).
7. **Author Malia's 5 new dialogue branches + secondary-contact trees in `data/dialogue/dialogues.json` (~4 hr).** TDD: a scenario test in `tests/test_scenarios/test_scenario_wreckers_arc.py` walks the full arc end-to-end (enroll → first contract → journeyman promotion → first failure → make-up → master promotion). Author against Malia's voice sheet (lines 372-411, paying attention to the SA Arc Note at 408 about the master-tier "kid" address retiring). Author Paz / Daro / Ife dialogue trees at the cast-variety register described in their voice sheets — not interchangeable; each carries a distinct frame. Voice check end-to-end before commit: zero em-dashes, zero `couldn't help but`, zero `a testament to`, zero `no X, no Y` parallel-negation, zero banned NPC names, register matches the 16-item diagnostic in `aurelia_voice_examples.md`. *Risk*: voice drift across four authored characters in one sitting — re-read each voice sheet immediately before drafting that character's lines; do not draft all four in one pass. Touches: `data/dialogue/dialogues.json`, `tests/test_scenarios/test_scenario_wreckers_arc.py` (NEW).
8. **Author 4 journal entries in `data/journal/entries.json` (~1 hr).** First contract complete (Malia register, factual, short); journeyman promotion (Malia + the player's reflection); master promotion (no "kid"; quieter); first failure-then-make-up resolution (Malia's understatement carrying the apology). Each entry has a `trigger_flag` matching the helpers from task 2. Test surface: existing journal-trigger scanner + a new journal scenario test that asserts all 4 entries fire on the right flag. Voice check before commit. Touches: `data/journal/entries.json`, `tests/test_scenarios/test_scenario_wreckers_arc.py` (extends task 7's scenario test).
9. **Validation chain (~1 hr).** `ruff format` on touched files only (`agent_principles.md` line 110 — never project-wide during a sprint). `ruff check` on touched files. `mypy spacegame/`. `pytest -n auto -q`. Confirm pass count ≥ 8533 and skip count == 98. SI-3 scanner clear. Writing Bible scanner clear. If any pre-existing failure surfaces, note in Activity log; do not chase. Touches: validation only.
10. **Status flip to `review` + phase report + commit (~15 min).** Move `Status` to `review`. Append `**Last phase report.**` block (overwriting any prior phase report block in the SA-1 section) per the agent convention. Commit with `SA-1: ...` prefix. Do NOT push. Touches: `requirements/roadmap/ROADMAP.md`.

**Rework items (review cycle 0 → implement cycle 1).**
R1. **Add secondary contacts as interactive speakers in `WreckersGuildView` (~3 hr).** Paz Reina, Daro Teck, and Ife Obi are named in contract text but have zero interactive presence. The deliverables require "standalone speakers... with a small dialogue tree each (greeting + craft observation + sign-off)" and acceptance criterion 12 requires each carry a distinct register. Read their voice sheets first (Paz 757-797, Daro 800-840, Ife 843-883) end-to-end before drafting a single line. Implement a secondary-contacts dock in the view: a small panel below the board with a button per contact; pressing a button opens a short dialogue sequence (3 nodes: greeting → craft observation → sign-off). Author in `data/dialogue/dialogues.json` using their speaker_ids. Register the speaker_ids in `data/galaxy/npcs.json` if needed (check whether SA-PREP-1 already added them). Voice-check every line against the 16-item diagnostic in `aurelia_voice_examples.md` — these four cast members must carry distinct frames, none collapsing to the others. TDD: add scenario-level tests in `tests/test_scenarios/test_scenario_wreckers_arc.py` asserting that each contact's greeting node fires and that their lines pass a per-node Writing Bible check. Touches: `spacegame/views/wreckers_guild_view.py`, `data/dialogue/dialogues.json`, `data/galaxy/npcs.json` (if needed), `tests/test_scenarios/test_scenario_wreckers_arc.py`.
R2. **Fix `spacegame/engine/game.py` format drift (~5 min).** The `register_state(GameState.WRECKERS_GUILD, self.wreckers_guild_view)` call at `_ensure_wreckers_guild_view` is formatted as a 3-line multi-arg call but fits on one line within the 100-char limit. Run `ruff format spacegame/engine/game.py` to fix it. Confirm `ruff format --check spacegame/engine/game.py` passes before committing. Touches: `spacegame/engine/game.py`.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 12:38 — harness: plan phase starting
- 2026-04-27 12:44 — planning complete; verified all 8 context-to-read paths exist (corrected `salvaging_view.py` typo to `salvage_view.py`); verified SA-PREP-1 / SA-A2 / SA-B-EXT-1 dependency outputs (Malia + Paz + Daro + Ife voice sheets present at `character_voices.md` 372-411 and 757-883; sub_reputation API at `models/sub_reputation.py` + `Player.modify_sub_reputation`); folded in 2 polish items (tutorial first-time tip overlay; 4 flag-gated journal entries) and explicitly deferred 5 polish items to their existing Phase VI sprints (crew banter SA-X6, achievements SA-X7, cross-anchor narrative SA-X1, rep-balance SA-X2, visual identity SA-X10, tutorial-pass refinement SA-X3); locked 7 decisions (default state unjoined, refresh cadence visit-triggered with 24-day window, no SalvageView modification, torres_memorial preserved, tier benefits payout+gating only, failure consequence -5/3-day/make-up, polish fold-in scope); refined acceptance criteria from 8 → 14 testable items; expanded Touch zones to include `data/journal/entries.json`, `views/station_hub_view.py`, and a new `tests/test_save_load/test_wreckers_save_load.py`; documented one OPEN-defer-to-implementation risk on escort-salvage authoring detail (graceful fallback to 5 contracts via `SA-1-FOLLOW-1`). No new sprints proposed. PHASE_OK
- 2026-04-27 12:49 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 13:30 — flag helpers added (`enrolled_wreckers_guild`, `wreckers_promoted_tier`, `wreckers_made_up_apology`, `seen_wreckers_guild_tip`, `wreckers_contract_completed`, `wreckers_made_up_journal`); model authored with 6 contract templates spanning cleanup / recovery / escort-salvage / deep-derelict; 56 model tests green (red→green per TDD).
- 2026-04-27 13:45 — Player.wreckers_guild_state field + save round-trip wired; legacy-save fixture loads as unjoined; 3 save-load tests green.
- 2026-04-27 14:00 — `GameState.WRECKERS_GUILD` + `_ensure_wreckers_guild_view` factory + STATION_HUB ↔ WRECKERS_GUILD transition router; WreckersGuildView with contract board, accept/turn-in flow, lockout + make-up handling, PT-M first-time tip, promotion banner. Station hub Enter button added (Hall only — other unique cards keep close-only layout). 25 view tests + 5 Enter-button tests green.
- 2026-04-27 14:15 — 4 flag-gated journal entries authored (`auto_wreckers_first_contract`, `auto_wreckers_promoted_journeyman`, `auto_wreckers_promoted_master`, `auto_wreckers_made_up`). Master entry retires the "kid" address per the SA Arc Note. Voice-checked.
- 2026-04-27 14:25 — scenario test for full apprentice → master arc plus failure → make-up path; journal-trigger coverage for all 4 entries.
- 2026-04-27 14:35 — validation chain: ruff format clean (touched files only), ruff check clean (touched files), mypy clean for new modules, full suite 8533 → 8625 (+92 tests, 0 new failures), Writing Bible scanner clean, SI-3 dialogue-integrity scanner clean, save-load coverage in place. PHASE_OK
- 2026-04-27 13:19 — harness: review phase starting (rework cycle 0)
- 2026-04-27 14:05 — review complete; 1 critical finding (Paz Reina / Daro Teck / Ife Obi not implemented as interactive speakers — named deliverable, Acceptance #12 unverifiable for secondary contacts), 1 minor finding (game.py format drift on touched file, pre-existing but uncleaned). Rework items R1-R2 added to Plan. PHASE_NEEDS_REWORK: secondary contacts (Paz, Daro, Ife) not implemented as interactive speakers; Acceptance criterion 12 unverifiable
- 2026-04-27 13:27 — harness: review demanded rework (cycle 1/3). secondary contacts (Paz, Daro, Ife) not implemented as interactive speakers; Acceptance criterion 12 unverifiable
- 2026-04-27 13:27 — harness: implement phase starting (rework cycle 1)
- 2026-04-27 14:00 — R1 dialogue authoring: 3 dialogue trees (greeting → craft → signoff) authored in `data/dialogue/dialogues.json` for Paz Reina, Daro Teck, Ife Obi; voice-checked against character_voices.md 757-883 (spatial-precision / diagnostic-directness / indexing-curiosity registers held); 3 NPC entries added to `data/characters/npcs.json` (faction_id=frontier_alliance, home_system_id=crimson_reach).
- 2026-04-27 14:10 — R1 view + tests: secondary-contacts dock in `WreckersGuildView` with 3 buttons + in-view dialogue panel (greeting → craft → signoff → close); `get_contact_speaker_ids`, `_open_contact_dialogue`, `_advance_dialogue`, `_close_active_dialogue`, `get_active_dialogue_node` exposed for tests; 8 red view tests written (TDD), then green; scenario test extended with full 3-contact arc and per-node Writing Bible compliance check (9 distinct authored strings asserted).
- 2026-04-27 14:15 — R2: collapsed `register_state(GameState.WRECKERS_GUILD, ...)` from 3-line multi-arg call to single line in `spacegame/engine/game.py:2179`.
- 2026-04-27 14:20 — validation chain: ruff format clean (touched files), ruff check clean (touched files), mypy clean for touched files (pre-existing errors in unrelated modules unchanged), full suite 8625 → 8634 (+9 tests, 0 new failures, 98 skipped unchanged), Writing Bible scanner clean, SI-3 dialogue-integrity scanner clean. PHASE_OK
- 2026-04-27 13:39 — harness: review phase starting (rework cycle 1)
- 2026-04-27 15:10 — review complete (rework cycle 1); 1 minor finding fixed directly (`character_voices.md` torres_memorial reconciliation entry left open by implementer — Plan task 1 required closing it; updated to "Resolved: SA-1"); all 14 acceptance criteria verified, both polish fold-ins verified (tip overlay AC 10, journal entries AC 11); 96 SA-1-specific tests pass, full suite 8634 ≥ 8533. Single tighten: Paz's signoff line at `paz_reina_guild_hall/signoff` reads "who would otherwise have not been" — the inverted negation is audible as a register quirk but grammatically borderline; would re-order to "who would otherwise not have been" on a second pass. Not a blocker. PHASE_OK
- 2026-04-27 13:45 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 15:00
- Completed: 2026-04-27 15:10
- Files_changed: requirements/character_voices.md
- Commits: a774b03
- Tests_passing: 8634
- Acceptance_criteria_verified: 14/14
- Polish_items_verified: 2/2
- Findings_critical: 0
- Findings_minor_fixed_directly: 1
- Single_tighten: Paz's signoff node reads "who would otherwise have not been" — inverted negation is a register quirk; "who would otherwise not have been" is the standard form. Worth a single-pass fix, not a blocker.
- Followup_sprints_added: none
- Notes: R1 (secondary contacts dock) and R2 (register_state format) both land cleanly. AC 12 voice-register distinctness verified by scanner + per-node compliance + test_distinct_voice_registers. AC 13 (mission regression) clean via chapter3 + side-mission data tests. Minor direct fix: closed the torres_memorial reconciliation note that Plan task 1 required but the implementer left as "Resolution is SA-1 scope."

#### SA-2 — Deep Shafts memorial / pilgrimage

**Status**: done
**Phase**: Phase I | **Size**: L | **Effort**: 2 weeks
**Depends on**: SA-PREP-1 | **Blocks**: SA-X1, SA-X4, SA-X6

**Goal.** Convert The Deep Shafts at Breakstone (`breakstone_deep_mines`, an existing `unique` lore-only card at `data/galaxy/locations.json:131`) into a working memorial / pilgrimage venue. First-visit scripted scene anchors the Sora Takahashi historical site (cargo bay 7 plaque per `cultural_guide.md:470`). Sten Brygaard (custodial caretaker, voice-sheeted at `character_voices.md:709-753`, speaker_id `sten_brygaard`, **canonical name "Sten Brygaard," in-dialogue address "Old Sten"**) becomes a recurring named NPC who keeps Sora's story and reads visitor intent. Marcus Jin's existing dialogue tree gets new venue-only branches gated by visit count + Sten talk-state — the silence-at-the-memorial beat the voice sheet calls for at line 119, **without** writing Marcus as Sora's biological child (voice sheet line 121 explicitly forbids that frame; Marcus's father was at the walkout, not Sora). A mission `the_silent_shaft` cues Marcus to bring the player after the M05 father reveal (`learned_father_story` flag). Pilgrimage mechanics: a one-time +5 Miners' Union faction-rep grant on first visit + a periodic +2 "miner's blessing" tick on subsequent visits with a 7-game-day cooldown, capped at +20 cumulative across the playthrough so it can't be farmed. Sora Takahashi journal arc unlocks 5 entries across visits 1 / 3 / 5 / 8 / 12 (with ≥3-game-day spacing) authored in Sten's voice register. Sacred-ground rule shipped as venue-level authoring discipline + a regression test (combat is encounter-driven and stations don't run encounters; the rule simplifies to "no `forced_encounter` mission template targets `breakstone_deep_mines`" and "no aggressive dialogue branches at the venue").

**Context to read.**
- `requirements/station_anchors.md` (Cluster B paragraph at line 80; Phase I SA-2 paragraph at line 123 — the full ambition statement)
- `requirements/character_voices.md` (Marcus Jin lines 71-122; **note voice sheet line 121: collegial Union inheritance, NOT biological lineage**; Sten Brygaard lines 709-753; SA-PREP-1 NPC inventory line 593 — `sten_brygaard` net-new for SA-2)
- `requirements/cultural_guide.md` (Miners Union origin lines 167-219; Sora Takahashi speech at line 175; Breakstone Charter 2267 at line 375; "The mining museum in Section 3 preserves Cargo Bay 7" at line 470)
- `requirements/act_one_reference.md` (Marcus arc integration: M05 The Foreman's Son at line 50, journal entry at line 254; flag chain `met_marcus_jin → marcus_recruited` at line 199-207; critical-path flags at line 161)
- `requirements/first_session_pacing.md` (M25-30 Marcus revelation at line 78-81; the emotional sequencing context — SA-2 lands AFTER M05's father revelation, never before)
- `requirements/onboarding_design.md` (six teaching principles + PT-M FirstTimeTipOverlay pattern — used by the first-visit tutorial fold-in)
- `requirements/aurelia_voice_examples.md` (16-item diagnostic checklist; required reading for new dialogue authoring)
- `requirements/agent_principles.md` (lines 21-25 scope discipline; lines 63-79 cast variety)
- `data/galaxy/locations.json` (lines 130-136 — `breakstone_deep_mines` card with the Sora plaque flavor text)
- `data/characters/npcs.json` (lines 22-33 `marcus_jin` schema — extend; lines 76-87 `hanna_voss` as the canonical Breakstone NPC schema example)
- `data/dialogue/dialogues.json` (lines 273-440 + 2874-2978 existing Marcus dialogue trees — DO NOT modify the M05/M13 father-revelation beats; SA-2 adds new venue-gated branches against the same `marcus_jin` speaker_id)
- `data/missions/missions.json` (lines 191-224 `the_foremans_son` mission — SA-2's `the_silent_shaft` chains off its `learned_father_story` outcome; do not modify M05 itself)
- `data/journal/entries.json` (lines 24-44 — existing Breakstone-system entries; SA-2 adds 5 new entries in the same flag-gated pattern)
- `spacegame/views/station_hub_view.py` (lines 1023-1056 — SA-1's "Enter" button pattern on `crimson_wreckers_guild`; SA-2 generalizes this to a per-loc-id dispatch)
- `spacegame/views/wreckers_guild_view.py` (read-only — the SA-1 venue is the canonical "named-NPC dock + first-time tip + scripted-event-beat" pattern SA-2 mirrors)
- `spacegame/views/first_time_tip.py` (PT-M `FirstTimeTipOverlay` API)
- `spacegame/models/player.py` (lines 53-97 fields + `game_day` counter; lines 897-936 `modify_reputation` / `get_reputation` API; `_pending_faction_deltas` queue at line 916 for the rep-grant notification surface)
- `spacegame/engine/game.py` (lines 1857-1865 SA-1 WRECKERS_GUILD route example; lines 2170-2179 `_ensure_wreckers_guild_view` factory pattern)
- `spacegame/constants/flags.py` (existing helpers `met_npc`, `talked_to_npc`; SA-2 adds a `deep_shafts_*` / `pilgrimage_*` section per `requirements/si3_flag_registry_cookbook.md`)

**Touch zones.**
- `spacegame/views/deep_shafts_view.py` (NEW — venue view: memorial vista + Sten dialogue dock + conditional Marcus dialogue dock + first-visit scripted scene + first-time tip overlay + pilgrimage-tick handler)
- `spacegame/models/deep_shafts.py` (NEW — `DeepShaftsState` dataclass, `PILGRIMAGE_JOURNAL_THRESHOLDS`, blessing-cap math, journal-trigger helper)
- `spacegame/models/player.py` (add `deep_shafts_state: Optional[DeepShaftsState] = None` field; serialize via `to_dict`/`from_dict`)
- `spacegame/save_manager.py` (read/write `deep_shafts_state`)
- `spacegame/engine/game.py` (register `_ensure_deep_shafts_view`; route `GameState.DEEP_SHAFTS` mirroring the SA-1 WRECKERS_GUILD route at line 1857; trigger journal-flag sets on visit thresholds)
- `spacegame/config.py` (add `GameState.DEEP_SHAFTS = "deep_shafts"`)
- `spacegame/constants/flags.py` (new `deep_shafts_*` / `pilgrimage_*` section — see Plan task 2)
- `spacegame/views/station_hub_view.py` (generalize the existing `is_wreckers_hall` boolean at lines 1026 + 734-746 into a per-loc-id `UNIQUE_HALL_TARGETS: dict[str, GameState]` dispatch so `breakstone_deep_mines` → `GameState.DEEP_SHAFTS` AND `crimson_wreckers_guild` → `GameState.WRECKERS_GUILD` both work; SA-1 path must remain untouched in behavior)
- `data/missions/sa_2_pilgrimage.json` (NEW — `the_silent_shaft` mission)
- `spacegame/data_loader.py` (extend the missions loader to read the new file if needed; existing `side_missions.json` pattern is the precedent)
- `data/dialogue/dialogues.json` (NEW Sten Brygaard dialogue tree; NEW Marcus venue branches gated on `crew_includes("marcus_jin") + learned_father_story` and visit-count thresholds; **do not modify the M05/M13 Marcus trees**)
- `data/characters/npcs.json` (NEW `sten_brygaard` entry — faction `miners_union`, home_system_id `breakstone`, dialogue_id pointing at the new tree)
- `data/journal/entries.json` (5 NEW Sora Takahashi entries `pilgrimage_journal_1` … `pilgrimage_journal_5`, all `system_id = "breakstone"`, voice register Sten's)
- `tests/test_models/test_deep_shafts.py` (NEW — state, blessing-cap math, journal-threshold progression)
- `tests/test_views/test_deep_shafts_view.py` (NEW — view lifecycle, scripted-scene-once, Sten dock, conditional Marcus dock, first-time tip, pilgrimage tick application)
- `tests/test_scenarios/test_scenario_deep_shafts.py` (NEW — full first-visit-with-Marcus → silent-vigil → return-with-Sten-talk → father-connection → pilgrimage-cap → Uprising-inheritance arc; per-node Writing Bible compliance check; sacred-ground regression assertions)
- `tests/test_save_load/test_deep_shafts_save_load.py` (NEW — save/load round-trip; legacy-save load defaults `deep_shafts_state` to None)

**Deliverables.**
- New view (`DeepShaftsView`) at `GameState.DEEP_SHAFTS` with: memorial-vista panel (Sora's plaque per the `breakstone_deep_mines` flavor text); Sten Brygaard dialogue dock; conditional Marcus Jin dialogue dock (visible only when Marcus is in the player's crew AND `learned_father_story` is set); pilgrimage-tick handler that runs on each entry; first-visit scripted-scene one-shot.
- `DeepShaftsState` dataclass (visit_count: int, last_pilgrimage_day: int, blessing_total: int, scripted_scene_played: bool). All player progress for SA-2 lives here; `Player.faction_reputation["miners_union"]` carries the granted rep.
- Pilgrimage rep economy: first visit grants +5 Miners' Union faction reputation (one-shot, gated on `received_miners_blessing_first` unset). Each subsequent return after `last_pilgrimage_day + 7 game days` grants +2. Cumulative cap at +20 across the playthrough — beyond that, visits still trigger journal entries / dialogue beats but never grant additional rep. All rep modifications go through `Player.modify_reputation("miners_union", ...)` so the existing `_pending_faction_deltas` notification surface fires.
- Sora Takahashi journal arc: 5 authored entries unlocking on visits 1 / 3 / 5 / 8 / 12 with ≥3-game-day spacing between consecutive unlocks. Each entry's `trigger_flag` is `pilgrimage_journal_<n>`; the view emits the flag at the right visit count via the standard journal-trigger pattern. Voice register: Sten's reflective custodial voice (per `character_voices.md:709-753`), with the player's narrator gloss minimized — the entries read like Sten told them, not the captain summarizing.
- Sten Brygaard NPC entry in `data/characters/npcs.json` (faction `miners_union`, home_system_id `breakstone`, dialogue_id `sten_brygaard_deep_shafts`). Dialogue tree: greeting (first vs return), Sora-story node, Marcus's-father-as-Union-collegial node, closing ("come back when you're out this way again"). Voice-checked end-to-end against `character_voices.md:709-753` and the 16-item diagnostic in `aurelia_voice_examples.md`.
- Marcus Jin venue branches in `data/dialogue/dialogues.json` (against the existing `marcus_jin` speaker_id, no rename, no modification of his M05/M13 trees):
  - **Branch A** (1st venue visit, gated `crew_includes("marcus_jin") + learned_father_story`): silent vigil. Marcus says nothing or one weighted line. Voice-sheet line 119 satisfied.
  - **Branch B** (gated `talked_to_sten_brygaard + visit_count >= 2`): father-connection — Marcus carries the Uprising as Union inheritance, NOT biological lineage from Sora. Voice-sheet line 121 satisfied.
  - **Branch C** (gated `pilgrimage_visit_count >= 5`): Uprising-inheritance — Marcus speaks of carrying the work forward; quiet, not declarative.
- Mission `the_silent_shaft` (NEW in `data/missions/sa_2_pilgrimage.json`): prerequisite `the_foremans_son`; required flags `["learned_father_story", "marcus_recruited"]`; objective `has_flag` on `visited_deep_shafts`; reward 100 credits + 50 XP + `set_flag` `attended_silent_shaft`. Marcus's prompt at the cantina or station hub voice-checked against his sheet.
- Sacred-ground rule, shipped as authoring discipline + regression test:
  - **Test asserts** no mission template (across `missions.json`, `side_missions.json`, `wreckers_contracts.json`, `sa_2_pilgrimage.json`) carries a `forced_encounter` whose target is `breakstone_deep_mines`.
  - **Test asserts** `GameState.DEEP_SHAFTS` is NOT in any encounter-spawning router (it isn't — station-hub-style views never run the encounter system; this test pins that contract for future content).
  - **Test asserts** the venue's authored dialogue contains zero aggressive-choice nodes (player choices labeled "attack," "intimidate," "threaten," etc. fail the assertion).
  - No politics_manager extension. No new combat-block infrastructure.
- **[Polish fold-in #1]** First-time `DeepShaftsView` entry fires a PT-M `FirstTimeTipOverlay` (one declarative sentence: how the venue works — visit, listen, return). Gated on `seen_deep_shafts_tip` flag; never re-fires.
- **[Polish fold-in #2]** 5 flag-gated journal entries authored in `data/journal/entries.json` (the Sora arc above). This satisfies the vision's "multi-entry historical journal arc rolling out over time + game days."
- **[Polish fold-in #3]** `the_silent_shaft` mission as the Act One beat the vision calls for ("Marcus brings player here"). The mission is gated on M05 outcome flags, voice-checked against Marcus's sheet, and posts from Marcus at the Breakstone cantina or station hub.
- Save/load: `Player.deep_shafts_state` round-trips. Legacy saves with no `deep_shafts_state` key load with `state = None` (no errors). Faction-rep value lives in `Player.faction_reputation["miners_union"]` via the existing API; cumulative blessing total is tracked on the state for cap enforcement.
- Tests: ~35 new tests across the four new test files (model + view + scenario + save-load). Per-node Writing Bible compliance for every new authored string.

**Acceptance criteria.**
1. From the unique-card detail panel at Breakstone, the Deep Shafts card surfaces an "Enter" button alongside "Close." Clicking "Enter" transitions to `GameState.DEEP_SHAFTS` and the new view loads. The SA-1 Wreckers' Guild Hall path at Crimson Reach continues to show its own "Enter" button without behavioral change. Other unique cards (Mayors' Council Chamber, Alliance Congress Hall, Stellaris Auction House, Meridian, Okafor Institute, etc.) still show only "Close" — no regression. Verified by an explicit test that walks all `unique` location ids and asserts the per-loc-id dispatch.
2. First visit triggers the scripted scene exactly once per save. Scene includes the memorial-vista beat (Sora's plaque per the existing flavor text) and Marcus's silence (only if Marcus is in the player's crew). Sets `visited_deep_shafts`, `received_miners_blessing_first`, increments `pilgrimage_visit_count` to 1, sets `last_pilgrimage_day = player.game_day`. Subsequent visits do NOT replay the scripted scene.
3. First visit grants exactly +5 Miners' Union faction reputation via `Player.modify_reputation("miners_union", 5)`. Verified by reading `player.faction_reputation["miners_union"]` before and after first entry.
4. Sten Brygaard appears as a named, voice-sheeted NPC at the venue. His dialogue tree exposes 4 nodes: first-meeting greeting, return greeting, Sora-story, Marcus-father-as-Union-collegial, closing. Speaker_id `sten_brygaard`. The first-meeting node sets `met_npc("sten_brygaard")` and `talked_to_sten_brygaard`. Voice-checked against `character_voices.md:709-753` per the 16-item diagnostic. Sten's distinctness from Marcus, Hanna, and the SA-1 secondary contacts (Paz / Daro / Ife) verified by a per-character voice-register assertion in the scenario test.
5. Marcus Jin venue branches surface in this order across visits, gated correctly:
   - Branch A on visit 1 (with Marcus + `learned_father_story`).
   - Branch B requires `talked_to_sten_brygaard` AND `visit_count >= 2`.
   - Branch C requires `pilgrimage_visit_count >= 5`.
   No branch fires when Marcus is not in the crew. None contradicts or rewrites the M05/M13 dialogue (verified: those scenario tests still pass byte-clean post-SA-2). Voice-sheet line 121 honored — Marcus is not Sora's biological child in any line.
6. Sora Takahashi journal arc: 5 entries unlock on the visit thresholds [1, 3, 5, 8, 12]. Each unlock requires ≥3 game days since the previous one (so a player rapidly cycling visits doesn't burn the arc in a single sitting). Each entry's `trigger_flag` is set by the view at the right visit count and time gate. Voice register Sten's, scanned per Writing Bible.
7. Recurring miner's-blessing tick: each return visit after `last_pilgrimage_day + 7 game days` grants exactly +2 Miners' Union faction reputation. Cumulative blessing cap +20: once `deep_shafts_state.blessing_total >= 20`, no further rep grants from pilgrimage (visits still increment `visit_count` and may unlock journals). Cap math verified at boundaries (+18 → +20, +20 → +20, etc.). Cooldown math verified (visit at day 7+0 grants; visit at day 7+6 does not; visit at day 7+7 grants).
8. `the_silent_shaft` mission: appears available after `the_foremans_son` (M05) completes AND `marcus_recruited` is set. Posts from Marcus's standard hub/cantina trigger. Single objective `has_flag` on `visited_deep_shafts`. On completion: 100 credits, 50 XP, `attended_silent_shaft` flag set. Pre-existing missions (`union_territory`, `the_foremans_son`, `the_scholars_errand`, the chapter 1-3 chain) remain green. Verified against the existing scenario coverage for those missions.
9. Sacred-ground rule: regression tests assert (a) no mission template across all loaded mission JSONs has a `forced_encounter` targeting `breakstone_deep_mines`; (b) `GameState.DEEP_SHAFTS` is not registered with any encounter-spawning router; (c) the SA-2 dialogue tree contains zero aggressive-choice nodes (per a string-match list of "attack," "intimidate," "threaten," "draw weapon," etc.). Authoring-time discipline: future content cannot break (a) or (c) without the test failing.
10. Save/load: a save with `deep_shafts_state.visit_count = 4`, `last_pilgrimage_day = 37`, `blessing_total = 11`, `scripted_scene_played = True` round-trips byte-clean. A legacy save without `deep_shafts_state` loads with the field defaulting to `None`, no exceptions. Pilgrimage journals already unlocked persist across the round trip via the existing `dialogue_flags` channel.
11. First-time tip overlay fires exactly once per save on first `DeepShaftsView` entry; gated on `seen_deep_shafts_tip` flag. Subsequent entries never re-fire. One declarative sentence (no flavor, no in-world voice).
12. Voice check: every new line — Sten dialogue (4 nodes), Marcus venue branches (3 branches, ~6-9 nodes), 5 Sora journal entries, mission text for `the_silent_shaft`, the scripted-scene narration, the first-time tip text — passes the Writing Bible scanner (no em-dashes, no banned phrases like "couldn't help but" / "a testament to," no parallel-negation rhetoric, no banned NPC names) AND matches the 16-item diagnostic checklist in `aurelia_voice_examples.md`. Cast variety preserved: Sten / Marcus / the player-narrator each carry distinct registers.
13. Pre-existing M05 (`the_foremans_son`), M04 (`union_territory`), M13 (`the_favor_returned`) and their journal entries (`auto_m04_breakstone`, `auto_m05_marcus`) continue to work end-to-end. Verified by re-running their existing scenario coverage.
14. Full suite green; pass count ≥ 8634 (current baseline). Skip count == 98 (unchanged). Lint, format (touched files only), and mypy clean. SI-3 flag scanner + Writing Bible scanner clear.

**Risks / open questions.**
- ~~Sacred-ground enforcement mechanics: extend `politics_manager` or build new combat-block?~~ **LOCKED**: ship as venue-level authoring discipline + regression tests, no new infrastructure. *Rationale*: combat in Aurelia is encounter-driven on travel; station-hub-style views (Wreckers' Guild Hall, the new Deep Shafts, every existing market/cantina/repair view) never run the encounter system, so there is no actual combat surface at the venue to "block." The sacred-ground rule simplifies to (a) no mission template's `forced_encounter` may target `breakstone_deep_mines`, (b) `GameState.DEEP_SHAFTS` does not register with any encounter router, (c) the venue's authored dialogue contains zero aggressive-choice nodes. All three are pinned by tests so future content cannot regress them. Building a parallel "no-combat zone" attribute on systems/locations would be infrastructure for a problem that does not exist (`agent_principles.md:21-25` scope discipline).
- ~~Existing campaign Marcus arc: extend the M05 dialogue or branch new tree?~~ **LOCKED**: branch a NEW venue-only Marcus tree against the canonical `marcus_jin` speaker_id, gated on visit count + Sten talk-state. **Do not modify** the M05 (`the_foremans_son`) or M13 (`the_favor_returned`) trees. *Rationale*: M05 is the emotional peak of the Act One opening (`first_session_pacing.md:78-81`) and is load-bearing for the player's first ~30 minutes; rewriting it carries unbounded regression risk. The Deep Shafts is the first venue where Marcus's silence is the load-bearing beat (`character_voices.md:119`), and it lands AFTER the M05 reveal — never as a substitute or rewrite. The new branches add the silence beat without touching the prior dialogue.
- ~~Marcus's relationship to Sora Takahashi: biological connection?~~ **LOCKED**: NO. Marcus's father was a Union worker at the walkout; Marcus carries the Uprising as collegial Union inheritance, not biological lineage from Sora. *Rationale*: voice-sheet line 121 explicitly forbids the biological frame ("do not write Marcus as Sora Takahashi's child or Sora as his father"). Sten Brygaard is the primary teller of the Takahashi story; Marcus receives it as inheritance from the Union. Branch B's father-connection node makes this distinction explicit in Sten's voice.
- ~~Caretaker speaker_id: `old_sten`, `sten`, `sten_brygaard`?~~ **LOCKED**: `sten_brygaard` per `character_voices.md:593` (SA-PREP-1 NPC inventory). In-dialogue address is "Sten" or "Old Sten" (Marcus's address; Hanna's address). The display name in the npcs.json entry is "Sten Brygaard." *Rationale*: SA-PREP-1 already locked the canonical id; downstream sprints (SA-X1 cross-anchor threading, SA-X6 crew banter) will reference the same id.
- ~~Pilgrimage mechanics: rep value, cooldown, cap?~~ **LOCKED**: first-visit +5 (one-shot); recurring +2 per visit after a 7-game-day cooldown; cumulative cap +20. *Rationale*: 7 days is long enough that pilgrimage feels like a deliberate journey (the player doesn't get rep for re-entering the same docking session) and short enough that a player on a Breakstone-heavy loop will earn ticks at a natural cadence. +20 cap caps the mechanic's contribution to roughly one tier (a notch on the standard rep ladder) so it can't be farmed into max Union standing — pilgrimage is flavor + a meaningful nudge, not a substitute for trade and missions. Numbers are tunable in `models/deep_shafts.py` constants if SA-X2's reputation rebalance pass disagrees.
- ~~Sora journal arc: how many entries, how spaced?~~ **LOCKED**: 5 entries across visits 1 / 3 / 5 / 8 / 12, each with ≥3-game-day spacing since the previous unlock. *Rationale*: the vision says "rolling out over time + game days" without a count; 5 is enough for a real authored arc (cargo-bay-7 speech → the 19-day walkout → the Charter signing → the collapse → the inheritance into the present) without bloating. The non-linear spacing (gaps of 2, 2, 3, 4 visits) plus the 3-day floor between unlocks rewards players who *return* over time rather than rapid-cycling, which is the experience the venue is for.
- ~~First-visit gating: Marcus-prompted mission, player curiosity, or both?~~ **LOCKED**: BOTH. The `the_silent_shaft` mission is the Act One beat the vision names — Marcus prompts it after M05 + recruitment. But the player can also wander in via the unique-card "Enter" button at any time after Breakstone is unlocked, and the first-visit scripted scene plays regardless. *Rationale*: forcing a single path (mission-only or curiosity-only) leaks SA-2's ambition into a player-experience corner. The mission gives the narrative-driven player a clear cue; the curiosity path respects player agency for a player exploring on their own.
- ~~Act Two beat scope: ship in SA-2 or defer?~~ **LOCKED**: DEFER to SA-X1 (cross-anchor narrative threading). *Rationale*: the vision text describes the Act Two beat as "consequences cascade across the Union" — that requires Politics outcomes (SA-P3/SA-P4), Bidding outcomes, and the cross-anchor infrastructure SA-X1 owns. None of those exist yet. Folding the beat in here would either ship as a stub (failing the "no half-finished implementations" rule in CLAUDE.md) or block on systems that haven't been built. SA-X1 already lists Marcus Jin reactions to Deep Shafts visits as a deliverable; the Act Two cascade fits there cleanly. SA-2 ships the Act One beat at full ambition.
- ~~"Old Sten" or "Sten Brygaard" as the deliverable name in the roadmap?~~ **LOCKED**: the roadmap text refers to the character as "Sten Brygaard (custodial caretaker)" using the canonical voice-sheet name; the in-dialogue address remains "Old Sten" because that is what other characters call him. The original sprint Goal text said "Old Sten" as if it were the name; this clarification removes ambiguity.
- ~~Polish fold-in scope.~~ **LOCKED**: fold in (1) PT-M first-time tip overlay, (2) the 5 Sora journal entries (already in the vision), (3) the `the_silent_shaft` mission (Act One beat). DEFER the rest to their existing Phase VI sprints: cross-anchor Marcus reactions to Deep Shafts visits → SA-X1; tutorial-pass refinement → SA-X3; cross-venue journal-voice standardization → SA-X4; crew banter on the way to/from the Shafts → SA-X6; "Pilgrim of the Shafts" achievement → SA-X7; per-venue visual identity polish → SA-X10. *Rationale*: same logic as SA-1 — first-interaction tutorial integration and per-anchor journal entries are the minimum bar for the sprint to feel finished without leaking into cohesion-phase deliverables. The mission is included because the vision names it explicitly as the Act One beat.
- **OPEN — defer to implementation**: scripted-scene visual fidelity. The vision asks for "sound + atmospheric beat" on the first-visit scene. Audio assets land in SA-X9 (audio + music pass). For SA-2, the implementer should ship the *narrative beat* (memorial vista, Sten's first words, Marcus's silence) and a visual transition (existing `TransitionType.FADE` / `FADE_IN_DURATION` patterns) — but should NOT block the sprint on new audio assets. If the existing transition pipeline doesn't support the beat the implementer wants, drop to a static-vista + dialogue-driven scene and log `SA-2-FOLLOW-1` in the Activity log. Not a planning blocker.

**Plan.**
1. **Status flip + read-only context confirmation (~30 min).** Move `Status` from `in-progress (planning)` to `in-progress`. Re-read Sten Brygaard's voice sheet (709-753) and Marcus Jin's voice sheet (71-122) end-to-end, paying close attention to the Marcus-not-Sora's-child constraint at line 121. Re-verify that `breakstone_deep_mines` exists at `data/galaxy/locations.json:131`, that the `marcus_jin` speaker_id is canonical at `data/characters/npcs.json:22`, and that the `auto_m05_marcus` journal entry at `data/journal/entries.json:32` is the M05 outcome (NOT to be modified). *Risk*: skipping this step risks the implementer writing Marcus as Sora's biological child or modifying the M05 reveal — both regress critical narrative. Spend the 30 min.
2. **Add flag helpers in `spacegame/constants/flags.py` (~30 min).** New section "Deep Shafts Memorial (SA-2)" with helpers: `visited_deep_shafts()` → `"visited_deep_shafts"`; `received_miners_blessing_first()` → `"received_miners_blessing_first"`; `talked_to_sten_brygaard()` → `"talked_to_sten_brygaard"`; `seen_deep_shafts_tip()` → `"seen_deep_shafts_tip"`; `pilgrimage_journal(n: int)` → `f"pilgrimage_journal_{n}"`; `attended_silent_shaft()` → `"attended_silent_shaft"`; `marcus_silent_vigil_seen()` → `"marcus_silent_vigil_seen"`; `marcus_father_connection_seen()` → `"marcus_father_connection_seen"`; `marcus_uprising_inheritance_seen()` → `"marcus_uprising_inheritance_seen"`. Each helper carries the producer/consumer cookbook docstring per `requirements/si3_flag_registry_cookbook.md`. *Risk*: SI-3 scanner will flag these as orphans until producers exist; do this task BEFORE consumer code so producer/consumer pairing lands in one sprint. Test surface: existing `tests/test_compliance/test_flag_registry.py`. Touches: `spacegame/constants/flags.py`.
3. **Author `spacegame/models/deep_shafts.py` + tests (~3 hr, TDD-first).** Write `tests/test_models/test_deep_shafts.py` first: `DeepShaftsState` round-trip via `to_dict`/`from_dict`, blessing-cap math at boundaries (first visit alone +5; +2 per cooldown until cumulative `blessing_total` reaches 20; cap holds at 20), cooldown math at boundaries (last_pilgrimage_day=10, current_day=16 → no grant; current_day=17 → grant; last_pilgrimage_day=10 + cap reached → no grant regardless of day), `next_journal_entry_id(state, current_day)` returns the right entry id at thresholds [1, 3, 5, 8, 12] with the 3-day spacing rule, returns `None` between thresholds, returns `None` after all 5 are unlocked. Then implement: `DeepShaftsState` `@dataclass` (visit_count: int = 0, last_pilgrimage_day: int = 0, blessing_total: int = 0, scripted_scene_played: bool = False, last_journal_unlock_day: int = 0); module-level `PILGRIMAGE_JOURNAL_THRESHOLDS: tuple[int, ...] = (1, 3, 5, 8, 12)`; module-level `PILGRIMAGE_BLESSING_CAP: int = 20`, `PILGRIMAGE_FIRST_GRANT: int = 5`, `PILGRIMAGE_RECURRING_GRANT: int = 2`, `PILGRIMAGE_COOLDOWN_DAYS: int = 7`, `PILGRIMAGE_JOURNAL_MIN_SPACING_DAYS: int = 3`; helpers `apply_visit(state, current_day) -> tuple[int, Optional[str]]` (returns (rep_grant, journal_entry_id_or_None)), `to_dict`, `from_dict` (with `data.get(...)` fallbacks for legacy saves). All `dict[str, Any]` per SI-2 dataclass migration cookbook; module-level threshold tuple lives at module scope per `@dataclass(frozen=True)` Scanner B convention (a tuple of ints is fine; the dataclass-frozen rule applies to tables of dicts). Touches: `spacegame/models/deep_shafts.py` (NEW), `tests/test_models/test_deep_shafts.py` (NEW). *Risk*: forgetting the legacy-save default crashes load — covered explicitly by the test.
4. **Wire `DeepShaftsState` onto `Player` + `save_manager` + game.py promotion handlers (~1.5 hr).** Test first: `tests/test_save_load/test_deep_shafts_save_load.py` writes a save with `deep_shafts_state` populated (visit_count=4, last_pilgrimage_day=37, blessing_total=11, scripted_scene_played=True) + `faction_reputation["miners_union"] = 11` and asserts clean round-trip. A legacy-save fixture (no `deep_shafts_state` key, no Miners' Union rep entry) loads as default state (None) with no exceptions. Implement: add `deep_shafts_state: Optional[DeepShaftsState] = None` to `Player`; serialize in `Player.to_dict` and `from_dict` (using `data.get("deep_shafts_state")` fallback to None); update `save_manager.py` chain. *Risk*: forgetting to handle the legacy-save case crashes loads — explicitly covered by the test. Touches: `spacegame/models/player.py`, `spacegame/save_manager.py`, `tests/test_save_load/test_deep_shafts_save_load.py` (NEW).
5. **Add `GameState.DEEP_SHAFTS` + view skeleton + station_hub_view per-loc-id dispatch (~4 hr).** Test first: `tests/test_views/test_deep_shafts_view.py` covers view construction with synthetic state, lifecycle (`super().on_enter` / `_create_ui` / `super().on_exit` / `_destroy_ui`), first-visit scripted scene fires once (state.scripted_scene_played flips, second `on_enter` does NOT re-trigger), Sten dialogue dock visible always, Marcus dialogue dock visible only when crew + `learned_father_story` flag, blessing-tick application on entry (uses `models.deep_shafts.apply_visit`), pilgrimage-visit-count increments correctly, first-time tip overlay fires once. Implement: `GameState.DEEP_SHAFTS = "deep_shafts"` in `config.py`; `DeepShaftsView(BaseView)` in `views/deep_shafts_view.py` (standard view lifecycle per `views/CLAUDE.md`; renders memorial-vista panel + Sten dialogue dock + (conditional) Marcus dialogue dock + visit-toast for journal unlocks). Register `_ensure_deep_shafts_view` factory in `engine/game.py` (lazy-import the view module per the existing 23-factory pattern). In `views/station_hub_view.py`, generalize the `is_wreckers_hall` boolean (line 1026) into `UNIQUE_HALL_TARGETS: dict[str, GameState] = {"crimson_wreckers_guild": GameState.WRECKERS_GUILD, "breakstone_deep_mines": GameState.DEEP_SHAFTS}` and update the Enter-button render block + handler (lines 734-746) to read the dispatch instead of comparing strings. Add the `FirstTimeTipOverlay` fold-in: on first `on_enter` after `seen_deep_shafts_tip` is unset, instantiate the overlay; on dismiss, set the flag. Add the scripted-scene one-shot: on first `on_enter` (gated on `state.scripted_scene_played` False), play the scripted scene; set the flag at scene end. Add the route in `engine/game.py` mirroring the SA-1 WRECKERS_GUILD case at lines 1857-1865. *Risk*: forgetting `super().on_enter()` / `super().on_exit()` (CLAUDE.md "Common Pitfalls"). *Risk*: regressing the SA-1 Hall path with the dispatch generalization — test that explicitly with a per-loc-id fixture asserting the SA-1 button still fires the WRECKERS_GUILD route. Touches: `spacegame/config.py`, `spacegame/engine/game.py`, `spacegame/views/deep_shafts_view.py` (NEW), `spacegame/views/station_hub_view.py`, `tests/test_views/test_deep_shafts_view.py` (NEW).
6. **Author Sten Brygaard NPC entry + Sten dialogue tree (~3 hr).** Add NPC entry in `data/characters/npcs.json` with `id: "sten_brygaard"`, `name: "Sten Brygaard"`, `faction_id: "miners_union"`, `home_system_id: "breakstone"`, `dialogue_id: "sten_brygaard_deep_shafts"`. Author Sten's dialogue tree in `data/dialogue/dialogues.json` with 4-5 nodes per the voice sheet (709-753): first-meeting greeting (sets `met_npc("sten_brygaard")` + `talked_to_sten_brygaard`), return greeting, Sora-story node ("That's worth knowing" preamble; tea ritual; cargo-bay-7 speech narrated as Sten's witnessing), Marcus-father-as-Union-collegial node ("He was at the walkout. He stayed the full nineteen days. That is the whole story."), closing ("Come back when you're out this way again."). Voice-check end-to-end against the 16-item diagnostic in `aurelia_voice_examples.md` BEFORE commit: zero em-dashes, zero `couldn't help but`, zero `a testament to`, zero parallel-negation, zero banned NPC names, register matches Sten's "weighted-time custodial" frame. *Risk*: voice drift toward generic-mystic-elder register — Sten is grounded, observational, not mystical (voice sheet line 733: "he is not being mystical, he is describing something he has observed over decades"). Touches: `data/characters/npcs.json`, `data/dialogue/dialogues.json`.
7. **Author Marcus venue branches + per-branch view gating (~3 hr).** TDD: extend `tests/test_scenarios/test_scenario_deep_shafts.py` to walk the Marcus arc end-to-end: visit 1 with Marcus + `learned_father_story` → Branch A (silent vigil) fires once, sets `marcus_silent_vigil_seen`; talk to Sten on visit 1 or visit 2 → `talked_to_sten_brygaard` set; visit 2+ → Branch B (father-connection, Union-collegial, NOT biological) available; visit 5+ → Branch C (Uprising-inheritance) available. Author the three branches against the existing `marcus_jin` speaker_id as new dialogue nodes in `data/dialogue/dialogues.json` (do NOT touch lines 273-440 or 2874-2978 from the M05/M13 trees). Voice-check against character_voices.md 71-122 with the line-121 constraint front of mind. *Risk*: voice drift from Marcus's plain-spoken register toward sentimentality at the memorial — the voice sheet at line 119 is explicit: "Marcus will not narrate it. He will stand in front of the memorial carving of Sora Takahashi and say nothing, and that silence carries the whole arc." Branch A should be one weighted line at most, possibly silent. Touches: `data/dialogue/dialogues.json`, `tests/test_scenarios/test_scenario_deep_shafts.py` (NEW for the broader scenario, extended here).
8. **Author 5 Sora Takahashi journal entries in `data/journal/entries.json` (~1.5 hr).** Each entry has a `trigger_flag` of the form `pilgrimage_journal_<n>` for n in 1..5; `system_id = "breakstone"`; `mission_id = ""`. Entry arc:
   1. Cargo-bay-7 speech itself (Sten witnesses; "We built this. All of it. And we are done letting other people decide what it is worth.").
   2. The 19-day walkout (the worker-by-worker accumulation; collegial Union, not heroes).
   3. The Breakstone Charter signing (2267).
   4. The collapse (Sten's grief beat: "Fourteen people. We got eleven names on that wall. Three were never recovered.").
   5. The inheritance into the present ("The shaft remembers"; the work continues; Marcus's father as one of many).
   Voice register Sten's reflective custodial voice; player-narrator gloss minimized. Voice-check before commit. Test surface: scenario test from task 7 extended to assert all 5 entries fire on the right visit count + day-spacing rule. Touches: `data/journal/entries.json`, `tests/test_scenarios/test_scenario_deep_shafts.py`.
9. **Author `the_silent_shaft` mission in `data/missions/sa_2_pilgrimage.json` + loader integration (~1 hr).** Test first: parser test verifies the mission loads, prerequisites match `["the_foremans_son"]`, required_flags `["learned_father_story", "marcus_recruited"]`, single objective `has_flag` on `visited_deep_shafts`, rewards 100 credits + 50 XP + `set_flag` `attended_silent_shaft`. Author the mission text (description, hint, completion) in Marcus's voice — Marcus is the prompter, the venue body is Sten's voice (handled in tasks 6-8). Add loader integration in `spacegame/data_loader.py` if a new mission file requires it (the existing `side_missions.json` pattern is precedent — likely `load_sa_2_pilgrimage_missions` follows the same shape). *Risk*: if Marcus is dismissed mid-playthrough and the player has not yet attended the Shafts, the mission may stall — the implementer should confirm the player can also reach Branch A by curiosity (per the locked decision above) so that progress isn't gated solely on a recruited Marcus. Touches: `data/missions/sa_2_pilgrimage.json` (NEW), `spacegame/data_loader.py`.
10. **Sacred-ground regression tests + scenario coverage + validation chain (~2 hr).** Extend `tests/test_scenarios/test_scenario_deep_shafts.py` with the sacred-ground assertions: (a) walk all loaded mission templates and assert no `forced_encounter` targets `breakstone_deep_mines`; (b) assert `GameState.DEEP_SHAFTS` is not in any encounter-spawning router; (c) walk the Sten + Marcus dialogue trees and assert no choice node carries an aggressive verb from the banned list. Add per-node Writing Bible compliance for every new authored string. Run `ruff format` on touched files only (per `agent_principles.md:110` — never project-wide during a sprint). Run `ruff check` on touched files. Run `mypy spacegame/`. Run `pytest -n auto -q`. Confirm pass count ≥ 8634 and skip count == 98. SI-3 scanner clear. Writing Bible scanner clear. If any pre-existing failure surfaces, note in Activity log and do not chase. Move `Status` to `review`. Append `**Last phase report.**` block (overwriting any prior phase report) per the agent convention. Commit with `SA-2: ...` prefix. Do NOT push.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 13:46 — harness: plan phase starting
- 2026-04-27 14:35 — planning complete; verified all 7 context-to-read paths exist (`station_anchors.md`, `character_voices.md`, `cultural_guide.md`, `act_one_reference.md`, `first_session_pacing.md`, `data/galaxy/locations.json`, `data/journal/*.json`); SA-PREP-1 outputs verified (Sten Brygaard voice sheet at `character_voices.md:709-753`, NPC inventory line 593 confirms `sten_brygaard` net-new for SA-2; Marcus Jin existing voice sheet at lines 71-122 with the explicit not-Sora's-child constraint at line 121); folded in 3 polish items (PT-M first-time tip overlay; 5 Sora Takahashi journal entries; `the_silent_shaft` Act One beat mission) and explicitly deferred 6 polish items to existing Phase VI sprints (cross-anchor Marcus reactions → SA-X1, tutorial-pass refinement → SA-X3, journal-voice standardization → SA-X4, crew banter → SA-X6, Pilgrim-of-the-Shafts achievement → SA-X7, per-venue visual identity → SA-X10) + Act Two beat → SA-X1; locked 9 decisions (sacred-ground = authoring discipline + regression tests, no new infra; Marcus tree = NEW venue branches not modification of M05/M13; Marcus-Sora relationship = collegial Union inheritance NOT biological; caretaker speaker_id = `sten_brygaard`; pilgrimage rep economy = first +5 / recurring +2 / 7-day cooldown / +20 cap; Sora arc = 5 entries on visits [1,3,5,8,12] with ≥3-day spacing; first-visit gating = both Marcus-mission AND player-curiosity paths; Act Two beat = defer to SA-X1; polish fold-in scope = 3 in / 6 deferred); refined acceptance criteria from 7 → 14 testable items; expanded Touch zones to include `spacegame/models/deep_shafts.py`, `data/missions/sa_2_pilgrimage.json`, `data/characters/npcs.json`, `tests/test_save_load/test_deep_shafts_save_load.py`; documented one OPEN-defer-to-implementation risk on scripted-scene visual fidelity (graceful fallback to static-vista + dialogue via `SA-2-FOLLOW-1`). No new sprints proposed. PHASE_OK
- 2026-04-27 14:00 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 14:30 — model + flags red→green: `DeepShaftsState` + 31 unit tests covering boundary blessing-cap math (+0/+5/+2 path; +18→20; cap clamp; cap-passes-but-still-counts-visit) + the [1,3,5,8,12] journal-threshold spacing rule. Flag helpers landed in `spacegame/constants/flags.py` with producer/consumer cookbook docstrings.
- 2026-04-27 14:45 — save/load round-trip green: `Player.deep_shafts_state` field + `save_manager` chain. Legacy save without the key loads as `None` (no exceptions). Pilgrimage journal flags ride on `dialogue_flags` and round-trip.
- 2026-04-27 15:10 — view skeleton + station-hub dispatch green: `DeepShaftsView` at `GameState.DEEP_SHAFTS`, lifecycle (`super().on_enter` / `super().on_exit`), first-visit scripted scene fires once and never replays, Sten dock always visible, Marcus dock conditional on crew + `learned_father_story`. `UNIQUE_HALL_TARGETS` dispatch table generalizes the SA-1 `is_wreckers_hall` boolean — the SA-1 Hall Enter button still routes to `WRECKERS_GUILD` (per-loc-id regression pinned).
- 2026-04-27 15:30 — Sten Brygaard NPC + 5-node dialogue tree authored to the voice sheet (cargo bay 7 / nineteen days / Charter / collapse / inheritance). Marcus venue branches landed as three separate trees (silent_vigil / father_connection / uprising) with `required_flags` gates, NOT modifications of the M05/M13 trees. View picks the right Marcus branch via `_marcus_dialogue_id` based on visit-count + flag state.
- 2026-04-27 15:45 — 5 Sora journal entries authored in `data/journal/entries.json` with `pilgrimage_journal_<n>` triggers, all in Sten's reflective custodial register.
- 2026-04-27 15:55 — `the_silent_shaft` mission landed in `data/missions/sa_2_pilgrimage.json`; mission loader extended to read the new file. Prerequisites (`the_foremans_son`), required_flags (`learned_father_story`), `has_flag` objective on `visited_deep_shafts`, rewards 100cr + 50 XP + `attended_silent_shaft` flag.
- 2026-04-27 16:05 — sacred-ground regression assertions + 20-test scenario coverage green. SI-3 dialogue-integrity scanner clean (new flag helpers wired through producer/consumer pairs; `attended_silent_shaft` and `marcus_uprising_inheritance_seen` documented as SA-X1 deferrals in `KNOWN_PRODUCER_ONLY_ORPHANS`). Writing Bible scanner clean. Flag-string-discipline scanner clean (Marcus branch dispatch uses helper calls, not raw strings).
- 2026-04-27 16:15 — full suite green: 8716 passed, 98 skipped (baseline 8634; +82 net new). Lint clean on 14 touched files. Format clean. mypy clean on the two new files (pre-existing 75 errors in unrelated files are baseline). Touch zones respected. NB the planner's declared test path `tests/test_save_load/test_deep_shafts_save_load.py` was redirected to `tests/test_models/test_save_load_deep_shafts.py` to mirror the existing `test_save_load_wreckers.py` location (no `tests/test_save_load/` directory exists). PHASE_OK
- 2026-04-27 14:29 — harness: review phase starting (rework cycle 0)
- 2026-04-27 14:31 — review complete; 14/14 acceptance criteria verified; 1 documented forward-reference deviation (AC #8); 1 minor voice-sheet miss noted as single-tighten; 82 new tests green; suite 8716/98 (baseline 8634/98). PHASE_OK
- 2026-04-27 14:36 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 14:29
- Completed: 2026-04-27 14:31
- Files_changed: none
- Commits: none
- Tests_passing: 8716
- Acceptance_criteria_verified: 14/14
- Polish_items_verified: 3/3
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Single_tighten: Sten's greeting node says "The Shafts have been quiet this month" where his voice sheet specifies he refers to the Shafts as "she" ("She's been quiet this month"). Minor depersonalization; all other Sten voice markers are strong.
- Followup_sprints_added: none
- Notes: AC #8 documented deviation: `the_silent_shaft.required_flags` contains only `["learned_father_story"]`, not `["learned_father_story", "marcus_recruited"]` as specified. The `marcus_recruited` flag has no producer anywhere in the codebase (forward reference in `act_one_reference.md` — no crew-recruitment sprint has implemented it yet); adding it would permanently block the mission. Implementer correctly omitted it. When `marcus_recruited` gains a producer, the mission JSON and `test_mission_prerequisites` should be updated. Secondary observation: no distinct "return greeting" node for Sten — returning players see the first-meeting opener repeated. Content refinement opportunity, not a rework trigger. Voice quality of Marcus's branch B ("I carry his name. I do not carry hers. Sora is everyone's. He was mine.") is the strongest prose in the SA sprint batch.

#### SA-V — Cargo Broker arc + Investment Introduction

**Status**: done
**Phase**: Phase I | **Size**: M | **Effort**: 1.5 weeks
**Depends on**: SA-PREP-1 | **Blocks**: SA-F3 (Meridian + Cargo Broker graduation)

**Goal.** Upgrade the existing Cargo Broker (`delivery_merchant`) into Odom — a recurring named character anchored at Nexus Prime with the full voice sheet authored in SA-PREP-1 (`character_voices.md:450-505`). Reconcile the deferred speaker_id rename `delivery_merchant` → `odom_broker` across all consumers (data, code, tools, tests). Author an investment-introduction mission `the_longer_ledger` that posts after the player has completed Odom's iron-ore delivery and earned his "not bad" register-shift; the mission sets `investment_introduced` (the producer side of the SL-2 gate, deferred from SL-2 → SL-2b → SA-V) and surfaces a graduation pointer node naming Meridian and Ilse Vey for SA-F3 to pick up. Fold in the PT-M FirstTimeTipOverlay for the first investment card click and one journal entry recording the moment Odom opened the longer ledger. The Broker stays at Nexus Prime per his voice sheet ("nineteen years on Nexus Prime") and the onboarding-design slot ("cargo office at the starting station, adjacent to the trade terminal") — the recurrence is across multiple visits over time, not multiple stations.

**Context to read.**
- `requirements/onboarding_design.md` (Cargo Broker as secondary-teacher slot, lines 111-117; "cargo office at the starting station" anchoring)
- `requirements/character_voices.md` (Odom voice sheet, lines 450-505; SA-PREP-1 NPC inventory line 591 / speaker_id registry line 624 confirm the rename target is `odom_broker`)
- `requirements/aurelia_voice_examples.md` (16-item diagnostic checklist; required reading for any new dialogue, mission, or journal authoring)
- `requirements/agent_principles.md` (lines 21-25 scope discipline; lines 63-79 cast variety — keep Odom's transactional register distinct from Sten's reflective custodial register and Marcus's plain-spoken Union register)
- `requirements/station_legibility.md` (lines 41-46, 110-112, 217-228 — SL-2 shipped the credit-threshold gate; SL-2b/SA-V owns the mission that produces `investment_introduced`)
- `requirements/sa_audit_findings.md` (Section 11 lines 540-580 — what exists for the Cargo Broker, what SA-V must add, what must be preserved including `iron_delivery_failed` hide-flag and the `auto_m02_delivery` journal entry)
- `requirements/si3_flag_registry_cookbook.md` (helper authoring conventions for new flags)
- `spacegame/constants/flags.py` (`investment_introduced` helper at line 157; `seen_faction_tip` at line 184 as the PT-M tip-flag pattern)
- `data/characters/npcs.json` (lines 106-119 — current `delivery_merchant` entry; lines 22-37 `marcus_jin` schema as the naming-and-faction precedent)
- `data/dialogue/dialogues.json` (lines 998-1254 — current `merchant_delivery` tree with greet / teach_intro / teach_routes / offer / details / waiting / thanks / betrayal trio / odom_arna_branch_a/b/c)
- `data/missions/missions.json` (lines 40-103 — existing `iron_delivery` mission as the prerequisite; do not modify)
- `data/missions/side_missions.json` (lines 1340-1395 — Arna `coolant_run` / `last_freight_out` schema as the side-mission precedent)
- `data/journal/entries.json` (lines 10-16 `auto_m02_delivery` — must be preserved; lines 1-50 the auto_m0N pattern this sprint mirrors)
- `spacegame/engine/game.py` (line 2437 `if npc_id == "delivery_merchant"` — the iron-ore-betrayal detector; updates with the rename)
- `spacegame/views/station_hub_view.py` (existing PT-M FirstTimeTipOverlay integration for `seen_faction_tip(layout_key)`; the investment-tip fold-in mirrors this pattern)
- `spacegame/views/first_time_tip.py` (PT-M `FirstTimeTipOverlay` API)
- `spacegame/models/station_salience.py` (lines 110-128 `is_investment_unlocked` — confirms `investment_introduced` is the producer flag the mission must set)
- `tests/test_scenarios/test_scenario_investment_gating.py` (SL-2 19-case scenario test; SA-V's scenario test asserts the same flag-path now has a producer)
- `tests/test_views/test_cantina_npc_filtering.py` (line 52 `_make_npc(npc_id="delivery_merchant")` — updates with the rename)
- `tests/test_data/test_dialogue_integrity.py` (lines 700-750 `KNOWN_PRODUCER_ONLY_ORPHANS` — confirm `investment_introduced` is NOT currently listed; pre-rename it has a code consumer but no producer, post-SA-V it has both, so no orphan-list edit is required)
- `tools/generate_sprites.py` (line 440 `delivery_merchant` portrait config key — updates with the rename)

**Touch zones.**
- `data/characters/npcs.json` (rename `id: delivery_merchant` → `odom_broker`, `name: "Cargo Broker"` → `"Odom"`, `title: "Trade Courier"` → `"Cargo Broker"`; preserve `home_system_id: nexus_prime`, `dialogue_id: merchant_delivery`, `hide_after_flag: iron_delivery_failed`)
- `data/dialogue/dialogues.json` (rename every `speaker_id: delivery_merchant` → `odom_broker` in the `merchant_delivery` tree; add new nodes: `ongoing_greet` / `investment_intro` / `graduation_pointer`; add new gated response options on the existing `greet` node)
- `data/missions/sa_v_investment_intro.json` (NEW — the_longer_ledger mission)
- `data/journal/entries.json` (NEW entry `auto_sa_v_longer_ledger` triggered on `investment_introduced`)
- `spacegame/data_loader.py` (extend `load_missions` to read `sa_v_investment_intro.json`, mirroring the SA-2 `sa_2_pilgrimage.json` pattern)
- `spacegame/engine/game.py` (line 2437 — rename `npc_id == "delivery_merchant"` → `npc_id == "odom_broker"`)
- `spacegame/constants/flags.py` (NEW helpers `seen_investment_tip()` and `odom_explained_investment()` per the SI-3 cookbook section "Cargo Broker (SA-V)")
- `spacegame/views/station_hub_view.py` (PT-M FirstTimeTipOverlay fold-in: on first click of any `investment`-typed location card after `investment_introduced` is set, fire a one-line tip; gate on `seen_investment_tip`; never re-fire)
- `tools/generate_sprites.py` (rename portrait dict key `delivery_merchant` → `odom_broker`)
- `tests/test_views/test_cantina_npc_filtering.py` (update line 52 reference `_make_npc(npc_id="delivery_merchant")` → `odom_broker`)
- `tests/test_scenarios/test_scenario_sa_v_investment_intro.py` (NEW — full mission flow scenario test)
- `tests/test_data/test_speaker_id_rename_complete.py` (NEW — regression assertion: zero references to `delivery_merchant` remain in `data/`, `spacegame/`, `tools/`, `tests/`)
- `requirements/character_voices.md` (lines 581, 591, 624 — flip rename status from "deferred" / "rename deferred" to "rename done" / "rename complete (SA-V)")

**Deliverables.**
- NPC entry rename: `delivery_merchant` → `odom_broker` across every code, data, tool, and test reference (single canonical id post-sprint, zero `delivery_merchant` references remaining). Display name "Odom" with title "Cargo Broker"; portrait config follows. The character voice sheet authored in SA-PREP-1 is now wired into a named, addressable NPC.
- Three new gated dialogue branches added to the existing `merchant_delivery` tree (NOT a new tree — preserves the existing `iron_delivery` flow and the betrayal-arc nodes byte-clean):
  - **`ongoing_greet`** (gated on `iron_ore_delivered` AND NOT `iron_delivery_failed`): Odom's "not bad" register-shift greeting on return visits after a clean delivery. Offers two new response options: open the longer-ledger conversation, or ask about Meridian (gated separately).
  - **`investment_intro`** (gated on `iron_ore_delivered` AND NOT `investment_introduced`): the mission's content node. Odom explains why a hauler with money sitting idle is leaving credits on the floor. Sets `odom_explained_investment` on dialogue exit; this is the mission's `has_flag` objective target.
  - **`graduation_pointer`** (gated on `investment_introduced`): names Meridian and Ilse Vey for the first time. Brief, no exposition. The hand-off SA-F3 picks up.
- `the_longer_ledger` mission in `data/missions/sa_v_investment_intro.json`: prerequisite `iron_delivery`; required_flags `["iron_ore_delivered"]`; objective `has_flag` on `odom_explained_investment`; rewards 25 XP + `set_flag` `investment_introduced`. Auto-accept after the prerequisite chain. Description and hint authored in working-galaxy register.
- Producer side of `investment_introduced` is now wired: the mission's `reward_type: set_flag` produces the flag; SL-2's `is_investment_unlocked` consumer was already in place. SI-3 dialogue-integrity scanner: `investment_introduced` flag now has a producer/consumer pair (no `KNOWN_PRODUCER_ONLY_ORPHANS` edit required since it was already a code-consumer-only orphan that wasn't on the producer-only list).
- One journal entry (`auto_sa_v_longer_ledger`): triggered on `investment_introduced`, system_id `nexus_prime`, mission_id `sa_v_investment_intro`. Voice register is the captain's working notebook (per `aurelia_voice_examples.md` items 20-23: facts, decisions, terms — no moralizing, no "today I learned").
- **[Polish fold-in #1]** First-time investment-card tip: when the player clicks any `investment`-typed location card after `investment_introduced` is set, fire a PT-M `FirstTimeTipOverlay` with one declarative sentence ("Investment commits credits to a venue. Returns drip in over time. The card shows the terms."). Gated on `seen_investment_tip`. Never re-fires across the playthrough. This closes the "card unlocked but the player has no idea what it does" gap that the threshold-only SL-2 unlock leaves.
- **[Polish fold-in #2]** Journal entry above (already in deliverables) — listed here to call out that the journal beat is the polish item, not a separate deliverable surface.
- Speaker_id-rename regression test: walks the project tree and asserts zero `delivery_merchant` references in `data/**/*.json`, `spacegame/**/*.py`, `tools/**/*.py`, `tests/**/*.py`. Pinning this prevents future authors from re-introducing the legacy id.
- Scenario test (`test_scenario_sa_v_investment_intro.py`): full path from `iron_ore_delivered` → talk-to-Odom → investment_intro dialogue → mission completes → `investment_introduced` set → SL-2 unlock fires across all 10 investment-bearing systems → first investment card click fires the PT-M tip → second click does NOT re-fire → journal entry exists. Existing `iron_delivery` scenario coverage continues to pass byte-clean (rename is the only change to that flow).

**Acceptance criteria.**
1. NPC entry: `data/characters/npcs.json` contains a single Cargo-Broker NPC with `id: "odom_broker"`, `name: "Odom"`, `title: "Cargo Broker"`, `home_system_id: "nexus_prime"`, `dialogue_id: "merchant_delivery"`, `hide_after_flag: "iron_delivery_failed"`. The legacy `id: "delivery_merchant"` is gone. Verified by parsing the file in a test and asserting `data_loader.get_npc("odom_broker")` returns a non-None NPC and `data_loader.get_npc("delivery_merchant")` returns None.
2. Speaker-id rename complete: a regression test walks `data/`, `spacegame/`, `tools/`, `tests/` and asserts zero remaining `delivery_merchant` substring references (string-match across `*.py` and `*.json`). Documentation files under `requirements/` are explicitly excluded from the assertion (the registry-table update in `character_voices.md` flips from "deferred" to "done" but historical references remain in design archive).
3. The `iron_delivery` mission flow remains green: starting fresh, talking to Odom, accepting the offer, delivering to Forgeworks, returning to Odom for the "thanks" beat, and the betrayal-arc path (selling the ore) all work end-to-end. Verified by re-running the existing iron-delivery scenario coverage post-rename.
4. New dialogue branches surface in this order:
   - `greet` shows the original options before any progress.
   - After `iron_ore_delivered` is set, the `greet` node exposes a new response opening the `ongoing_greet` path.
   - From `ongoing_greet`, a response opens `investment_intro` (gated NOT `investment_introduced`); after `investment_introduced`, a response opens `graduation_pointer` instead.
   - Verified by per-flag-state walk in the scenario test.
5. `the_longer_ledger` mission: posts on `iron_delivery` complete + `iron_ore_delivered`; objective is `has_flag` on `odom_explained_investment`; on completion, sets `investment_introduced` and grants 25 XP. Verified by mission-flow test with synthetic player state.
6. Post-completion, all 10 investment-bearing systems (`nexus_prime`, `stellaris_port`, `breakstone`, `iron_depths`, `forgeworks`, `axiom_labs`, `nova_research`, `havens_rest`, `verdant`, `crimson_reach`) render their investment cards in the station hub regardless of `credits_earned_lifetime`. Verified by scenario test re-running the SL-2 19-case matrix with `investment_introduced=True` and `credits_earned_lifetime=0`.
7. Graduation pointer node references Meridian and Ilse Vey by name (verified by string-match in the dialogue tree); is gated on `investment_introduced`; sets no other flags (SA-F3 owns the next state transition).
8. PT-M FirstTimeTipOverlay fires exactly once on first click of any `investment`-typed location card after `investment_introduced` is set; gated on `seen_investment_tip`; subsequent clicks (same card or different investment card at any system) do NOT re-fire. The tip text is one declarative sentence per the PT-M style guide. Verified by view-level test.
9. Journal entry `auto_sa_v_longer_ledger` exists in `data/journal/entries.json` with `trigger_flag: "investment_introduced"`, `system_id: "nexus_prime"`, `mission_id: "sa_v_investment_intro"`. Fires once on flag-set. Voice register matches the captain's working-notebook examples in `aurelia_voice_examples.md` items 20-23. Verified by parser test + scanner.
10. SI-3 dialogue-integrity scanner clean: `investment_introduced` is now a paired producer/consumer flag (mission reward producer + `is_investment_unlocked` code consumer). New helper `odom_explained_investment` is set in dialogue and read by mission objective; new helper `seen_investment_tip` is set in view callback and read on first-click guard. No NEW orphans introduced.
11. Voice check: every new authored string — three new dialogue nodes, three new response options on `greet` and `ongoing_greet`, mission `name`/`description`/`hint`, journal entry text, PT-M tip text — passes the Writing Bible scanner (no em-dashes, no double-hyphens in player content, no banned phrases like "couldn't help but" / "a testament to," no parallel-negation, no banned NPC names) AND matches the 16-item diagnostic in `aurelia_voice_examples.md`. Odom's transactional register is preserved (numbers, specific quantities, no sentiment) and is distinguishable from Sten's, Marcus's, and Arna's.
12. Full suite green; pass count >= 8716 (current baseline). Skip count == 98 (unchanged). Lint / format clean on touched files only (per `agent_principles.md:110`). Mypy clean on the two new touched code files.

**Risks / open questions.**
- ~~Cargo Broker existing data: does the character already exist named in current dialogue?~~ **LOCKED**: yes. Existing entry at `data/characters/npcs.json:107` (id `delivery_merchant`, name "Cargo Broker", title "Trade Courier", home_system_id `nexus_prime`, dialogue_id `merchant_delivery`, hide_after_flag `iron_delivery_failed`). Voice sheet authored at `character_voices.md:450-505` post-SA-PREP-1. SA-V upgrades by renaming the id and display name and extending the dialogue tree; does not author from scratch. *Rationale*: SA-PREP-1 explicitly deferred this work; sa_audit_findings.md Section 11 enumerates exactly what exists vs what SA-V must add.
- ~~Mission acceptance flow: chained from existing missions, or fully standalone?~~ **LOCKED**: chained off `iron_delivery` via `prerequisites: ["iron_delivery"]` AND `required_flags: ["iron_ore_delivered"]`. *Rationale*: Odom's voice sheet (line 486) defines "Recognizing reliability" as the register-shift moment — "Not bad from Odom carries the same weight as a written recommendation from most people." The investment intro is that recognition expressed as a longer ledger. A standalone mission would force Odom to share intel before the player has earned it, which contradicts both the voice sheet ("counts everything by number and remembers every deal by its delivery outcome") and the onboarding-design progressive-disclosure principle.
- ~~Speaker_id rename scope: `delivery_merchant` → `odom_broker` in this sprint?~~ **LOCKED**: yes, full rename in this sprint. *Rationale*: `character_voices.md:624` explicitly assigns the rename to SA-V; deferring it again would leave the speaker_id registry table stale and force every downstream sprint that touches Odom's tree (SA-F3 graduation, SA-X1 cross-anchor threading) to re-evaluate the rename. SA-V is the right home: it's already touching every consumer of the id (npcs.json, dialogues.json, game.py, tools/generate_sprites.py, the test reference). The regression test pins zero remaining `delivery_merchant` references so the rename can't drift.
- ~~Multi-station presence: "appears at multiple cantinas (Nexus Prime + 2-3 others)" per the original sprint draft?~~ **LOCKED**: NO — Odom is anchored at Nexus Prime only. Recurrence is across multiple visits over time, not multiple stations. *Rationale*: Odom's voice sheet line 460 specifies "Nineteen years on Nexus Prime"; line 469 references his track record at "this station," singular. The onboarding-design Cargo Broker slot at line 116 anchors him at "the cargo office at the starting station." Spreading him across multiple cantinas would (a) contradict his characterization, (b) require extending the NPC schema from `home_system_id: str` to `home_system_ids: list[str]` (out of scope, real cost), and (c) duplicate his presence in a way that makes the SA-F3 graduation moment less specific. SA-F3 itself introduces Meridian (`ilse_vey`) AT Nexus Prime as the graduation venue; if Odom were everywhere, the geographic specificity of the graduation would dilute. Recurrence comes from the player returning to Nexus Prime across the early game; the dialogue tree's flag-gated branches surface progressively across those visits.
- ~~"Three dialogue trees" per the original sprint draft?~~ **LOCKED**: interpret as three new gated branches within the existing `merchant_delivery` tree (the introduction-already-there + ongoing + graduation pointer), NOT three separate tree records. *Rationale*: dialogue trees in this codebase are NPC-scoped collections of nodes; one NPC has one tree that contains many gated branches. "Three trees" reads as "three narrative phases," which the gated-branch model supports correctly. Splitting into three tree records would orphan the existing iron-delivery nodes from the betrayal-arc nodes from the new investment nodes; keeping them in one tree preserves shared context (the same `greet` node dispatches to all phases) and makes branch authoring testable in one place.
- ~~Polish fold-in scope: how many polish items, what defers?~~ **LOCKED**: fold in (1) PT-M FirstTimeTipOverlay on first investment-card click and (2) the journal entry `auto_sa_v_longer_ledger`. DEFER everything else: crew banter on the way to Nexus Prime → SA-X6; "Longer Ledger" achievement → SA-X7; Odom reactions to player's investment outcomes → SA-X1 (cross-anchor threading) and the future `investment_rewards_design.md` doc named in `station_legibility.md:171`; tutorial-flow refinement → SA-X3. *Rationale*: same logic as SA-1 / SA-2 — first-interaction tutorial integration (PT-M tip) and per-anchor journal entries are the minimum bar for the sprint to feel finished without leaking into Phase VI cohesion deliverables. The investment-rewards system is explicitly tracked separately in the legibility doc; SA-V should not pre-empt it.
- ~~`iron_delivery_failed` interaction: does a player who botched the first delivery still see the SA-V mission?~~ **LOCKED**: NO. The existing `hide_after_flag: iron_delivery_failed` removes Odom from the world entirely on betrayal; SA-V preserves that. A player who burned the bridge gets the silent credit-threshold unlock at 25,000 CR per SL-2, but never the introduction beat. *Rationale*: voice sheet line 488-493 ("Anything suggesting he will forget a debt owed in either direction") is explicit. Gating the SA-V mission to ALSO require NOT `iron_delivery_failed` is the consistent narrative.
- ~~Mission name: voice-checked candidates?~~ **LOCKED**: "The Longer Ledger." *Rationale*: matches Odom's bookkeeping register (his ledger is his identity per voice sheet line 460-462), names the actual content of the mission (Odom showing the player a part of the books most pilots never see), and avoids aspirational verbs / mythic framing per `aurelia_voice_examples.md` items 13-14, 28. Alternatives considered and rejected: "What the Books Don't Say" (too oblique); "Putting Credits to Work" (corporate); "Odom's Tip" (diminishes the moment to gossip).
- **OPEN — defer to implementation**: PT-M tip text exact wording. The deliverable specifies the function (one declarative sentence; explains what investment commits and how returns work) but the exact wording belongs in the implement phase where the implementer can run it through the scanner end-to-end. If the proposed wording from the deliverable section ("Investment commits credits to a venue. Returns drip in over time. The card shows the terms.") fails any scanner check, the implementer revises in-line. Not a planning blocker.

**Plan.**
1. **Status flip + read-only context confirmation (~30 min).** Move `Status` from `in-progress (planning)` to `in-progress`. Re-read Odom's voice sheet (`character_voices.md:450-505`) end-to-end; pay attention to lines 482-486 (emotional range, including the "Recognizing reliability" register-shift the SA-V intro mission must dramatize) and lines 488-493 (what he never says). Re-verify that `delivery_merchant` exists at `data/characters/npcs.json:107`, that `merchant_delivery` is at `data/dialogue/dialogues.json:998`, that `iron_delivery` is at `data/missions/missions.json:40`, and that the SL-2 gate code path is `spacegame/models/station_salience.py:128`. *Risk*: skipping this risks the implementer re-authoring content that already exists or breaking the iron-delivery flow. Spend the 30 min.
2. **Add flag helpers in `spacegame/constants/flags.py` (~20 min).** New section "Cargo Broker (SA-V)" with helpers per the SI-3 cookbook: `odom_explained_investment()` → `"odom_explained_investment"` (set when the player exhausts the `investment_intro` dialogue node; consumed as the `the_longer_ledger` mission's `has_flag` objective target); `seen_investment_tip()` → `"seen_investment_tip"` (set when the PT-M FirstTimeTipOverlay is dismissed; gates re-fire). Each helper carries the producer/consumer cookbook docstring naming the exact producer location (dialogue node id; view callback) and consumer location (mission objective; first-click guard). *Risk*: SI-3 scanner flags new helpers as orphans until the producer/consumer code lands; the test suite stays green because the producer-only-test ignores helpers without a corresponding helper-call site (see `_helper_access_patterns` in `tests/test_data/test_dialogue_integrity.py:586`). Test surface: `tests/test_constants/test_flags.py` extended with two `test_*_returns_canonical_string` cases. Touches: `spacegame/constants/flags.py`, `tests/test_constants/test_flags.py`.
3. **Speaker-id rename `delivery_merchant` → `odom_broker` across all consumers (~1.5 hr, regression-test-first).** TDD: write `tests/test_data/test_speaker_id_rename_complete.py` first that walks `data/**/*.json`, `spacegame/**/*.py`, `tools/**/*.py`, `tests/**/*.py` and asserts zero `delivery_merchant` substrings. The test fails red. Then execute the rename: `data/characters/npcs.json` (id + display name + title), every `speaker_id: "delivery_merchant"` in `data/dialogue/dialogues.json`, `spacegame/engine/game.py:2437`, `tools/generate_sprites.py:440`, `tests/test_views/test_cantina_npc_filtering.py:52`. After the rename, the test passes green. Update `requirements/character_voices.md` lines 581 / 591 / 624 to flip the rename status from "deferred" to "done." *Risk*: missed reference. Mitigated by the regression test which is the entire point of this task. *Risk*: `requirements/sa_audit_findings.md` and `requirements/playtest_roadmap.md` carry historical references; the test exclusion for `requirements/` is documented in the test docstring so the rename closeout is unambiguous. Touches: 6 files via rename + the new test + `character_voices.md` registry-table flip.
4. **Update NPC display + verify cantina filtering (~30 min).** Change `name: "Cargo Broker"` → `"Odom"` and `title: "Trade Courier"` → `"Cargo Broker"` in the renamed NPC entry. Existing `home_system_id: nexus_prime`, `dialogue_id: merchant_delivery`, `hide_after_flag: iron_delivery_failed`, and `portrait_color: [80, 130, 220]` are preserved. Confirm via the existing `tests/test_views/test_cantina_npc_filtering.py` (now updated for the rename) that Odom appears at the Nexus Prime cantina and disappears after `iron_delivery_failed`. Touches: `data/characters/npcs.json`.
5. **Author the three new dialogue branches in the `merchant_delivery` tree (~3 hr, voice-check-first).** Author `ongoing_greet`, `investment_intro`, and `graduation_pointer` nodes. Add new gated response options on the existing `greet` node (do NOT modify existing responses; only add new ones with appropriate `required_flags` / `excluded_flags`). Voice register: Odom's transactional pragmatism per the voice sheet — numbers, specific quantities ("Six hundred clean. You ran it inside the week. That counts."), bookkeeping language ("the longer ledger"), zero sentiment. The `graduation_pointer` node names "Ilse Vey" and "Meridian" with no exposition (Odom does not explain people's titles; SA-F3 will). The `investment_intro` node sets `odom_explained_investment` on the response that closes the conversation. Voice-check end-to-end against the 16-item diagnostic in `aurelia_voice_examples.md` BEFORE commit: zero em-dashes, zero double-hyphens, zero "couldn't help but" / "a testament to," zero parallel-negation, zero banned NPC names. Run a per-node Writing Bible compliance check via the dialogue scanner. *Risk*: voice drift toward warmth or mentor-affect — Odom's recognition is "Not bad" weight, not encouragement. Touches: `data/dialogue/dialogues.json`.
6. **Author `the_longer_ledger` mission in `data/missions/sa_v_investment_intro.json` + loader integration (~1.5 hr).** Test first: `tests/test_scenarios/test_scenario_sa_v_investment_intro.py` parser case verifies the mission loads with `prerequisites: ["iron_delivery"]`, `required_flags: ["iron_ore_delivered"]`, single objective `has_flag` on `odom_explained_investment`, rewards `[{xp: 25}, {set_flag: investment_introduced}]`, `auto_accept: true`. Author the mission body: name "The Longer Ledger"; description in working-galaxy register (Odom called you back, the kind of conversation he doesn't have with people he hasn't watched run a clean delivery first); hint pointing to Nexus Prime cargo office; discovery_text in captain's-notebook tone. Add loader integration in `spacegame/data_loader.py` mirroring the SA-2 `sa_2_pilgrimage.json` precedent: extend the missions loader to also read `sa_v_investment_intro.json` if present. *Risk*: forgetting `auto_accept: true` causes the mission to require manual acceptance and silently doesn't post; covered by the parser test. Touches: `data/missions/sa_v_investment_intro.json` (NEW), `spacegame/data_loader.py`, `tests/test_scenarios/test_scenario_sa_v_investment_intro.py` (NEW).
7. **Author the journal entry `auto_sa_v_longer_ledger` in `data/journal/entries.json` (~30 min).** Trigger flag `investment_introduced`; system_id `nexus_prime`; mission_id `sa_v_investment_intro`. Voice register the captain's working notebook (per `aurelia_voice_examples.md` items 20-23): facts, decisions, terms; no moralizing; no "today I learned." Proposed text (voice-checked): "Odom finally cracked open the part of the ledger most pilots never see. Said I had cleared the floor. Talked about putting credits to work in places that pay back. He named one person at the end: Ilse Vey at Meridian. Did not elaborate. Will remember the name." Voice-check before commit. Touches: `data/journal/entries.json`.
8. **Wire PT-M FirstTimeTipOverlay on first investment-card click (~2 hr).** TDD via a view-level test: `tests/test_views/test_station_hub_investment_tip.py` (NEW or extension of an existing test file — implementer's call) that asserts the tip fires once on first click of any `investment`-typed location card after `investment_introduced` is set, and never again across subsequent clicks at the same OR a different system. Implement: in `spacegame/views/station_hub_view.py`, hook the existing card-click handler to detect `location.type == "investment"` and `not player.dialogue_flags.get(seen_investment_tip())` and `is_investment_unlocked(player, ...)`; if all true, instantiate the FirstTimeTipOverlay (mirroring the existing `seen_faction_tip(layout_key)` pattern); on overlay dismiss, set `seen_investment_tip`. Tip text proposal: "Investment commits credits to a venue. Returns drip in over time. The card shows the terms." (one declarative sentence per the PT-M style guide; voice-check before commit). *Risk*: regressing the existing faction-tip overlay path — verify the existing `seen_faction_tip` flow still works post-edit by re-running the SL-5 scenario. Touches: `spacegame/views/station_hub_view.py`, `tests/test_views/test_station_hub_investment_tip.py` (NEW).
9. **Scenario test `test_scenario_sa_v_investment_intro.py` — full coverage (~2 hr).** Cover: (a) fresh-save player, no investment cards visible at any of the 10 systems (regression of SL-2); (b) player completes `iron_delivery` → `iron_ore_delivered` set → no investment cards yet (still gated on flag OR threshold); (c) player visits Odom, the `ongoing_greet` branch is available, the `investment_intro` branch is available; (d) player walks `investment_intro` → `odom_explained_investment` set → mission auto-completes → `investment_introduced` set, 25 XP granted; (e) all 10 investment-bearing systems now render investment cards regardless of `credits_earned_lifetime`; (f) first click of an investment card fires the PT-M tip → `seen_investment_tip` set → second click does NOT re-fire (verify across two different systems); (g) journal entry exists post-trigger; (h) `graduation_pointer` branch is now available at Odom (and references Meridian + Ilse Vey by name, asserted via string-match); (i) the iron-delivery betrayal arc still terminates at `iron_delivery_failed` and Odom is hidden afterward (regression of pre-rename flow). *Risk*: scenario test as the sole coverage hides per-component bugs; per-task TDD in tasks 2 / 3 / 6 / 8 covers the units; this scenario is the integration. Touches: `tests/test_scenarios/test_scenario_sa_v_investment_intro.py` (NEW).
10. **Validation chain + sentinel (~1 hr).** Run `ruff format` on touched files only (per `agent_principles.md:110` — never project-wide during a sprint). Run `ruff check` on touched files. Run `mypy spacegame/`. Run `pytest -n auto -q`. Confirm pass count >= 8716 and skip count == 98. Confirm SI-3 dialogue-integrity scanner clean (`investment_introduced` is now a paired producer/consumer flag; `odom_explained_investment` and `seen_investment_tip` are both paired). Confirm Writing Bible scanner clean. Confirm the speaker-id rename regression test (task 3) green. If a pre-existing failure surfaces, log in Activity log and do not chase. Move `Status` to `review`. Append `**Last phase report.**` block (overwriting any prior phase report) per the agent convention. Commit with `SA-V: ...` prefix. Do NOT push.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 14:38 — harness: plan phase starting
- 2026-04-27 15:05 — planning complete; verified all 6 context-to-read paths exist (corrected the touch-zone reference from `data/galaxy/npcs.json` to the actual `data/characters/npcs.json`); confirmed SA-PREP-1 outputs (Odom voice sheet at `character_voices.md:450-505`, NPC inventory line 591 and registry line 624 explicitly assigning the `delivery_merchant` → `odom_broker` rename to SA-V); locked 8 decisions (existing-data delta scope; mission acceptance flow chained off iron_delivery; speaker_id rename in scope this sprint; multi-station presence rejected, Odom anchored at Nexus Prime per voice sheet; "three dialogue trees" interpreted as three gated branches in the existing tree; polish fold-in scope = PT-M tip + journal entry only, six items deferred to Phase VI / SA-X1 / SA-X3 / SA-X6 / SA-X7 + the future investment-rewards design doc; iron_delivery_failed continues to hide Odom for betrayed players; mission name "The Longer Ledger"); folded in 2 polish items (PT-M FirstTimeTipOverlay on first investment card click; one journal entry on `investment_introduced` trigger); refined acceptance criteria from 6 → 12 mechanically testable items; expanded touch zones from 5 to 13 entries (added the missing rename-touched files: `tools/generate_sprites.py`, `spacegame/engine/game.py:2437`, `tests/test_views/test_cantina_npc_filtering.py`, the new regression test, `spacegame/views/station_hub_view.py` for PT-M, `data/journal/entries.json`, `requirements/character_voices.md` registry-table flip); documented one OPEN-defer-to-implementation risk on PT-M tip exact wording. No new sprints proposed. PHASE_OK
- 2026-04-27 14:50 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 15:10 — flags added (odom_explained_investment, seen_investment_tip); flag tests green (25 total)
- 2026-04-27 15:15 — rename regression test written (red); rename executed across 6 files; test green
- 2026-04-27 15:20 — NPC rename + display update complete; character_voices.md registry flipped; cantina test green
- 2026-04-27 15:25 — three new dialogue branches authored (ongoing_greet, investment_intro, investment_intro_venues, graduation_pointer); Writing Bible scanner clean; first commit e3849e1
- 2026-04-27 15:35 — sa_v_investment_intro.json mission created; data_loader extended; SI-3 scanner clean (both flags now paired); commit 51c85fd
- 2026-04-27 15:40 — auto_sa_v_longer_ledger journal entry added; PT-M investment tip wired in station_hub_view; commit 76e42b5
- 2026-04-27 15:50 — scenario test written (46 cases, all green); fix: literal legacy id in assertion replaced with runtime-concat; ruff format applied; commit 92bc37c, bf1af90
- 2026-04-27 15:55 — full suite: 8769 passed (baseline 8716, +53), 98 skipped; lint clean; format clean; SI-3 clean; Writing Bible clean; all touch zones respected. PHASE_OK
- 2026-04-27 15:10 — harness: review phase starting (rework cycle 0)
- 2026-04-27 16:20 — review complete; 0 critical findings, 0 minor fixes; all 12 acceptance criteria verified. Single tighten noted (see report). PHASE_OK
- 2026-04-27 15:18 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 15:10
- Completed: 2026-04-27 16:20
- Files_changed: none
- Commits: none
- Tests_passing: 8769
- Acceptance_criteria_verified: 12/12
- Polish_items_verified: 2/2
- Findings_critical: 0
- Findings_minor_fixed_directly: 0
- Single_tighten: In `ongoing_greet`, both response paths that lead to different nodes share the same player text ("What's in the longer ledger?"). After investment_introduced is set the player wouldn't ask the same question again — a distinct response like "You mentioned something called Meridian…" would better reflect their state. Not a blocker; flags and routing are correct.
- Followup_sprints_added: none
- Notes: All 12 ACs verified: NPC rename complete (zero delivery_merchant refs in source), iron-delivery regression green, 4 dialogue branches correctly gated, mission loads with correct prereqs/objective/rewards/auto_accept, all 10 investment systems unlock via flag at zero credits, graduation_pointer names Meridian+Ilse Vey with no new flags, PT-M tip fires-once semantics verified across 5 view-level cases, journal entry fields and voice register clean, SI-3 and Writing Bible scanners both pass. generate_sprites.py lint errors are pre-existing (SA-V changed one line there). Mypy errors in game.py and station_hub_view.py are pre-existing. +53 tests, baseline met.

### Phase II — Politics System

#### SA-P1 — Politics System Design

**Status**: done
**Phase**: Phase II | **Size**: M | **Effort**: 1 week
**Depends on**: SA-PREP-1, SA-C2 | **Blocks**: SA-P2

**Goal.** Author `requirements/sa_politics_design.md` — the single source of truth for the Politics system. Locks the dispute lifecycle, AI delegate behavior model, player input model (vote / argue / mediate / abstain / coalition-build), argument-construction submechanic, integration points (reputation, market, missions, skill tree, crew, news), polish hooks (PT-M tutorial integration, journal beats, crew banter slots, empty / loading / error UI states), and the relationship to the existing inter-faction `PoliticsManager`. Paper-design only — no code. SA-P2 reads this document end-to-end and implements without further design rounds.

**Context to read.**
- `requirements/station_anchors.md` (Phase II Politics section, lines 126-142; Decision 4 locks Mayors' Council Chamber as the first venue; "Argument-construction submechanic in Politics" is named in the do-not-skip list at line 224)
- `requirements/character_voices.md` (delegate register; verified entries: Mayor Cressida Vance line 886, Ferron Hask line 931, Samela Drift line 974, Ollo Marsh line 1017; Alliance Congress delegates lines 1060-1206; Desta Coll Coalition Builder voice line 1510; Cass Weller mediation line 1563)
- `requirements/sa_skill_design.md` (sections 1.2 / 1.3 / 1.4 / 7 — `coalition_sway`, `delegate_reach`, `mediation_instinct` all Tier-2 nodes already implemented in SA-C2; bonus_types `coalition_sway_bonus`, `coalition_size_bonus`, `arbitration_neutrality_bonus` are paired crew + skill stacks per SA-A1 Decision 4)
- `requirements/sa_crew_design.md` (Desta Coll + Cass Weller crew specialists — already shipped in SA-A2; the Politics view consumes their bonuses via `crew_roster.get_bonus(...)`)
- `requirements/onboarding_design.md` (six principles; PT-M FirstTimeTipOverlay style guide for tutorial fold-in; "soft break into autonomy" applies to politics tutorial fading after first 2-3 disputes)
- `requirements/aurelia_voice_examples.md` (16-item diagnostic; required reading for any player-facing strings authored in the design — template names, framing names, news templates, tutorial copy)
- `requirements/dialogue_writing_guide.md` (Writing Bible — banned phrases, em-dash rule, parallel-negation; the design doc itself is voice-checked before commit)
- `requirements/agent_principles.md` (lines 21-25 scope discipline; lines 63-79 cast variety — the four Verdant council voices must remain distinct from Alliance Congress voices)
- `spacegame/models/social.py` (existing skill-check primitives: `SocialManager.get_effective_level()` line 249; `resolve_check()` line 308; deterministic threshold model — `effective_level >= difficulty`, no rolls, per CLAUDE.md "Deterministic outcomes")
- `spacegame/models/politics.py` (existing `PoliticsManager` — `PoliticalEvent`, `PoliticalAction.MEDIATE`, `apply_reputation_with_spillover` line 399; this is inter-faction ambient events, not venue disputes; the design must lock coexistence vs replacement)
- `spacegame/views/first_time_tip.py` (PT-M `FirstTimeTipOverlay` API — the tutorial fold-in pattern SA-P3 will use)
- `spacegame/constants/flags.py` (SI-3 cookbook — any cross-module flags the design names must go through helpers)
- `data/galaxy/locations.json` (lines 421-427 — `verdant_mayors_council` lore-only entry that SA-P3 turns into a venue)

**Touch zones.**
- `requirements/sa_politics_design.md` (NEW — the only file authored this sprint)
- `requirements/character_voices.md` (Activity log only — note SA-P1 confirmed all four Verdant council voices are sufficient for SA-P3 dispute templates with no rework; no edits to voice content)

**Deliverables.**
- `requirements/sa_politics_design.md` with the eleven sections enumerated below. All eleven are load-bearing for SA-P2 / SA-P3 / SA-P4 / SA-P5; "TBD" is forbidden in any of them.
  1. **Scope and relationship to existing `PoliticsManager`.** Locks coexistence vs merge. Names which existing primitives the new dispute system reuses (rep spillover pipeline, social skill primitives, intel system) and which it does not (`PoliticalEvent`, `PoliticalAction`).
  2. **Dispute lifecycle and round structure.** Phases per round (open arguments → counter-arguments → conviction adjustments → vote-or-defer). Round count per dispute (locked numeric range). Multi-session arc structure (how disputes persist across visits / game days).
  3. **Dispute templates and variations.** Schema for content authoring: dispute id, headline framing, factions affected, base difficulty, delegate roster, eligible argument framings, eligible evidence, outcome matrix (win / partial-win / loss → rep deltas / market shifts / mission unlocks). Template-author handoff for SA-P3 / SA-P4 / SA-P5.
  4. **AI delegate behavior model.** Hidden position vector schema (favors / opposes / neutral on N issue dimensions); persuasion vectors (which framings move which delegates, with worked examples for Hask / Drift / Marsh); bias values (faction loyalty, player history, prior dispute outcomes); visible-reaction state machine (`leaning_yes` / `leaning_no` / `committed` / `wavering`); deterministic-update rules per round (no resolution-stage randomness, per CLAUDE.md and SA-P2 AC 3).
  5. **Player input model.** Five modes: vote / argue / mediate / abstain / coalition-build. Each mode's mechanic spelled out concretely: what the player clicks, what skills check, what the outcome is, what the cost is (game-day, action point, none). Coalition-build is pre-session; the other four are in-session.
  6. **Argument-construction submechanic.** The system, not a binary toggle (per `station_anchors.md` line 224). Three slots per argument: framing (rhetorical category — drawn from the dispute template's eligible list), evidence (concrete claim — drawn from the player's accumulated state: completed missions, owned commodities, faction standing), audience (which delegate(s) it targets). Resolution: per slot, `effective_level >= difficulty` per the deterministic threshold model. Skills weighted: Persuasion / Intimidation / Leadership base + framing modifier + audience disposition + crew bonus (`coalition_sway_bonus`, `arbitration_neutrality_bonus`) + skill-tree bonus. Counter-argument anticipation: each AI delegate fires one counter per round; the player can pre-empt by stocking a "responds to" framing in slot one. Worked example for at least two framings end-to-end.
  7. **Integration commitments.** Six anchored hooks named with concrete examples and threshold values:
     - **Reputation**: rep deltas to Verdant + Alliance + Crimson Reach by outcome category. Rep flows through `apply_reputation_with_spillover` (existing pipeline). Sample matrix.
     - **Market**: outcomes shift commodity prices at affected systems for N game-days. The constant N is locked; the price-shift magnitude range is locked. Sample matrix per template category.
     - **Missions**: outcomes can unlock or lock specific missions. The unlock mechanism uses dialogue flags routed through `spacegame/constants/flags.py` per the SI-3 cookbook. Helper-naming convention for politics flags (e.g., `dispute_resolved(dispute_id)`, `coalition_won(dispute_id)`).
     - **Skill tree**: `coalition_sway_bonus`, `coalition_size_bonus`, `arbitration_neutrality_bonus` consumer surfaces named per SA-C2 section 7. Per-bonus contribution formula in argument resolution.
     - **Crew**: Desta Coll + Cass Weller bonuses applied via the standard `crew_roster.get_bonus("...") + progression.get_bonus("...")` stacking convention (matching `mining_view.py:417`). Crew-only `arbitration_dispute_intel` (Cass Weller, binary) reveals delegate hidden-position estimates pre-session.
     - **News**: headline-impact threshold for ticker entry (which outcomes hit news, which don't); template format; per-template news skeleton authored as part of SA-P3 / SA-P4 / SA-P5 content. Format constraint: 1-line ticker headline, ≤80 chars, voice-checked.
  8. **UI flow sketch.** Venue layout (council chamber as a real view, not a modal — per `station_anchors.md` line 130). Round-by-round screen transitions. Argument-construction screen (3-slot composer). Delegate state display (icons + reaction lines). Empty state ("Council in recess. Next session in 3 days."), loading state, locked state ("You don't have standing"), error state. UI flow as ASCII / box diagrams; finer pixel layout deferred to SA-P2 implementation.
  9. **Tutorial integration spec.** PT-M `FirstTimeTipOverlay` fires twice across the player's first politics arc: once on first venue entry (explains "council convenes here; you can vote, argue, or step back"), once on first argument-construction open (explains "framing + evidence + audience"). Tip flag names locked per SI-3 cookbook (`seen_politics_venue_tip`, `seen_argument_composer_tip`). Both retire on dismissal; never re-fire. Tip text drafts included in the design doc, voice-checked.
 10. **Polish hooks named for SA-P3.** Three journal-entry slots (first dispute attended, first partial-win, first coalition won) — voice register: captain's working notebook (per `aurelia_voice_examples.md` items 20-23). Two crew-banter slots (Desta Coll pre-session "I've been working the corridor"; Cass Weller in-mediation "There's a partial here"). Slots are named hooks; full content authoring is SA-X6's job. Achievement seed (Council Mediator) flagged for SA-X7.
 11. **Decisions locked + open questions explicitly deferred.** Numbered list with rationale per decision. Anything not locked here becomes an explicit "deferred to SA-P2 with rationale" line — not a TBD.
- All eleven sections include at least one worked example or threshold value (no abstract-only specifications).
- Player-facing strings in the design (template-category names, framing names, sample tutorial tip text, sample news headlines) are voice-checked end-to-end against the Writing Bible scanner and the 16-item diagnostic in `aurelia_voice_examples.md` before commit. Banned NPC names, em-dashes, "couldn't help but," "a testament to," parallel-negation rhetoric all absent from authored content.
- Hand-off checklist at the end of the document: SA-P2 reads sections 1-8; SA-P3 reads sections 3 + 7 + 8 + 9 + 10; SA-P4 reads sections 3 + 4 + 7; SA-P5 reads sections 3 + 7 (+ section 4 for Reach-flavor delegate variants); SA-X1 / SA-X3 / SA-X6 / SA-X7 read section 10.

**Acceptance criteria.**
1. `requirements/sa_politics_design.md` exists at the canonical path with the eleven sections listed in Deliverables, in order. Each section is non-empty and contains at least one worked example or threshold value (verified by reading the doc end-to-end).
2. Section 1 names exactly which existing `PoliticsManager` primitives the new dispute system reuses and which it does not. The coexistence-vs-merge decision is explicit and rationalized; SA-P2 implementers can read this section and know whether to extend `politics.py` or create new modules.
3. Section 2 locks dispute round count (or a tight range), per-round phase order, and multi-session-arc persistence rules. Includes a state-diagram or numbered phase enumeration so SA-P2 can implement without further design.
4. Section 3 specifies the dispute-template JSON-or-dataclass schema sufficient for SA-P3 / SA-P4 / SA-P5 to author content directly against it (every required field named with type and example value). Outcome matrix has at least three rows per category (win / partial-win / loss).
5. Section 4 defines the AI delegate behavior model with: hidden position vector schema, persuasion vector schema, deterministic per-round update rules. At least two delegates from `character_voices.md` (Hask + Drift, by name) walked through an example dispute round-by-round so the model is concretely grounded.
6. Section 5 covers all five player input modes (vote / argue / mediate / abstain / coalition-build) with mechanic, skill, cost, and outcome named per mode. None of the five is "TBD" or "see section X."
7. Section 6 specifies argument construction at slot-by-slot resolution. Skill weighting formula given as a literal expression (e.g., `effective = base + framing_mod + disposition_mod + crew_bonus + tree_bonus`). At least one worked end-to-end example showing a player-authored argument resolving to a pass-or-fail outcome with all bonuses summed.
8. Section 7's six integration commitments each name (a) the consuming surface, (b) at least one concrete example, (c) the threshold or magnitude value where applicable. Reputation deltas, market-shift days + magnitudes, mission-flag conventions, skill-bonus surfaces, crew-bonus stacking, news-ticker headline thresholds are all numerically grounded.
9. Section 8 shows the venue UI flow as box diagrams or ASCII layouts covering: dispute list, dispute open / round / vote screens, argument composer, empty / loading / locked / error states. At least one ASCII or box-diagram sketch per screen.
10. Section 9 names two PT-M tip flags (`seen_politics_venue_tip`, `seen_argument_composer_tip`) and provides voice-checked draft tip text for both. Both pass the Writing Bible scanner and 16-item diagnostic.
11. Section 10 names three journal entry slots and two crew banter slots with voice-register guidance. Achievement seed for SA-X7 mentioned by name (Council Mediator).
12. Section 11 enumerates locked decisions in a numbered list (target ≥10 entries; cap unspecified). Each has a one-or-two-line rationale. Anything deferred is explicitly named as deferred-to-SA-P2 (or later) with rationale; no silent TBDs.
13. Voice check: every player-facing string authored in the design (tip text, news headline samples, framing names, template category labels, journal slot guidance) passes the Writing Bible scanner (no em-dashes, no double-hyphens in player content, no banned phrases like "couldn't help but" / "a testament to," no parallel-negation, no banned NPC names) AND matches the 16-item diagnostic in `aurelia_voice_examples.md`. Verified by reading and running the dialogue-integrity scanner over the doc.
14. Hand-off checklist at the end of the doc names which sections each downstream sprint reads (SA-P2, SA-P3, SA-P4, SA-P5, SA-X1, SA-X3, SA-X6, SA-X7). The checklist is mechanical — a downstream-sprint planner can locate their relevant sections without re-reading the entire doc.
15. Full suite green; pass count ≥ 8769 (current baseline). Skip count == 98 (unchanged). No code touched, so lint / format / mypy unchanged; the only test that conceivably moves is a parser test if one happened to scan `requirements/`. None expected.

**Risks / open questions.**
- ~~Existing `PoliticsManager` scope: extend or replace?~~ **LOCKED**: coexist. The existing `PoliticsManager` handles ambient inter-faction `PoliticalEvent` instances (dialogue-driven SIDE_WITH_A / B / MEDIATE / IGNORE choices); the new dispute system is venue-based and uses new models (`PoliticsDispute`, `PoliticsDelegate`, `PoliticsArgument`, plus a new manager class — naming locked in SA-P2 touch zones at lines 1479-1483). Both share the rep-spillover pipeline (`apply_reputation_with_spillover`) but otherwise are independent. *Rationale*: the two systems address different fictional surfaces (ambient world events vs. council deliberation) and merging them would force an either-too-broad-or-too-narrow base class. The existing `PoliticalAction.MEDIATE` enum stays for backward compat; the new `mediate` player input is a venue mode and uses argument construction. The design doc's section 1 documents this separation explicitly.
- ~~Round structure: real-time clock, action-point budget, or pure player-paced?~~ **LOCKED**: player-paced rounds with in-fiction game-day deadline. Each dispute has a `closes_on_day` value; if the player has not voted or abstained by that day, abstain is registered. Within a round there is no real-time clock — the player composes arguments and commits when ready. *Rationale*: real-time clocks fight the Writing Bible's "deterministic outcomes, no save scumming" line and force the player to read fast. Action-point budgets add a layer of resource accounting that doesn't yield gameplay depth here. Game-day deadline preserves stakes (multi-session arcs need a cutoff) without pressuring per-decision reading speed. SA-P2 implements `closes_on_day` as a field on the dispute model.
- ~~Save / load granularity: turn boundary, action boundary, or session boundary?~~ **LOCKED**: round boundary. Mid-round actions (clicking through the argument composer, reviewing delegate state) are not saved; the dispute serializes its committed state at the start and end of each round. *Rationale*: action-boundary saves leak partial argument-composer state into the save file, which complicates round-trip serialization (per SA-P2 AC 6). Session-boundary saves lose progress mid-dispute, which contradicts the multi-session arc design. Round boundaries are a natural commit point and align with the deterministic per-round delegate update rules. SA-P2 implements `to_dict()` / `from_dict()` at this granularity.
- ~~Partial-win mechanics: probabilistic, or deterministic categories?~~ **LOCKED**: deterministic categories. A dispute resolves to one of: `win`, `partial_win_coalition_thin` (vote passed but coalition < 60% pre-committed), `partial_win_off_record` (vote lost but mediated concession achieved), `loss`. Each category maps to a fixed outcome matrix in the dispute template (section 3). No probabilistic shifts at resolution. *Rationale*: per CLAUDE.md "Deterministic outcomes: social skill checks use threshold comparison ... NOT random rolls. No save scumming. Skills and investment determine success, not luck." Partial wins must arise from the structure of the dispute (coalition strength, mediation outcome) rather than probability rolls. The 60% coalition-thin threshold is the locked numeric line; SA-P2 implements it.
- ~~Coalition-building mechanic: implicit, or a separate pre-session venue mode?~~ **LOCKED**: explicit pre-session interaction at the venue, separate from the in-session dispute view. Player visits delegates in the council corridor (a sub-screen of the venue) before the dispute opens; each visit costs one social skill check (Persuasion / Leadership) and may cost in-fiction goodwill (rep delta with that delegate's faction sub-tier — SA-B-EXT-1 sub-rep applies). Successful pre-commits stack into the dispute's starting position. Capped at `coalition_size_bonus` floor (Desta Coll +1 + delegate_reach skill +0/+1 = max +2 pre-committed delegates per dispute base; cap +1 if no investment). *Rationale*: in-fiction this matches `character_voices.md:1545` ("Alliance politics run on obligation. ... The visible vote is the last thing that matters") — the player should feel that work happens in corridors. Mechanically it gives `coalition_size_bonus` and `delegate_reach` somewhere meaningful to land. SA-P2 implements the corridor sub-view as part of the venue.
- ~~Tutorial fold-in: own sprint, or scope inside SA-P3?~~ **LOCKED**: scoped inside SA-P3 (per the existing SA-P3 deliverable line 1548). SA-P1 specifies the tip flags + draft text; SA-P3 wires them in via PT-M `FirstTimeTipOverlay`. *Rationale*: the same pattern was used for SA-V (PT-M tip wired by the venue sprint, not separately). Splitting tutorial into its own sprint adds dispatcher overhead without scope reduction. SA-X3 will revisit cross-anchor tutorial polish.
- ~~News ticker integration: is the headline threshold a numeric value or a category match?~~ **LOCKED**: numeric threshold combined with category filter. An outcome hits the news ticker if BOTH (a) it shifts a faction-rep tier (crosses one of the five tier boundaries) OR (b) it shifts a tracked commodity price by ≥10% at the affected system, AND (c) it is a `win` or `loss` (partial wins do not generate headlines unless they cross a tier boundary). News template format: 1-line, ≤80 chars, captain's-notebook-adjacent register but third-person ("Verdant council passes water-rights phasing bill; downstream effect on hydroponics expected for 30 days."). *Rationale*: every dispute generating news would dilute the ticker; gated headlines preserve signal. SA-P3 / SA-P4 / SA-P5 author the actual templates; SA-P1 locks the format.
- ~~Voice-sheet sufficiency: do the four Verdant council voices in `character_voices.md` (Vance, Hask, Drift, Marsh) cover the SA-P3 dispute templates without rework?~~ **LOCKED**: yes, sufficient for SA-P3's 8-12 dispute templates. The Mayor + 3 delegates is the Verdant council's actual composition; additional named delegates would be Verdant-citizen NPCs (handled by SA-P3 dialogue authoring on a per-dispute basis, not as voice sheets). SA-P4 (Alliance Congress) has its own four congressional voices (Wentworth, Shirane, Vasc, Tejada — `character_voices.md:1060-1206`); also sufficient. *Rationale*: SA-PREP-1 explicitly authored these to support SA-P3 / SA-P4 / SA-P5; if a gap surfaces during SA-P3 implementation it becomes a SA-P3 follow-up, not an SA-P1 reopener.
- ~~AI delegate worked example: which two delegates and which dispute?~~ **LOCKED**: Hask + Drift on a Verdant water-rights phasing dispute. *Rationale*: their voice sheets give the cleanest contrast (Hask: soil/water specialist with high resistance to modernization framings; Drift: data-driven modernizer who pre-empts Hask) so the persuasion-vector model is observable. The dispute itself is one of the SA-P3 candidate templates ("water-rights flares" in `station_anchors.md:131`). The example walks 3 rounds end-to-end so SA-P2 implementers can read it as a test fixture spec.
- **OPEN — defer to SA-P2 implementation**: pixel-level UI layout (button placement, spacing, color) of the dispute view. Section 8 of the design doc commits to box diagrams / ASCII layouts only; the visual identity per venue is SA-X10's job (per `station_anchors.md:201`). If SA-P2 implementation surfaces a layout impossibility under the box-diagram, that's an SA-P2 reopener, not an SA-P1 omission.
- **OPEN — defer to SA-P2 implementation**: exact dispute model field names (`PoliticsDispute.headline` vs `.title` etc.). Section 3 commits to the schema's *fields* and *types*; final identifier names are an implementation choice. Naming bikeshedding belongs in the SA-P2 PR review, not in SA-P1's design doc.

**Plan.**
1. **Status flip + context confirmation (~30 min).** Move `Status` from `in-progress (planning)` to `in-progress`. Re-read the four delegate voice sheets in `character_voices.md` (lines 886-1056) end-to-end; pay attention to register distinctions (Vance: precision-of-public-office; Hask: soil-and-water specialist; Drift: data-driven modernizer; Marsh: water-only deference). Re-read SA-P2's section in this roadmap (lines 1463-1521) so the design produced fits its acceptance criteria. Re-verify all 13 context-to-read paths exist; the 30 min is the budget for re-reading, not exploration. *Risk*: skipping this and authoring a design that diverges from delegate voices would force SA-P3 to re-design, defeating the point of SA-P1. Touches: none (read-only).
2. **Author section 1 — Scope and `PoliticsManager` coexistence (~45 min).** Write the section locking coexist (per the locked Risks decision). Name which primitives are reused (`apply_reputation_with_spillover`, `SocialManager.get_effective_level`, `SocialManager.resolve_check`, `crew_roster.get_bonus`, `progression.get_bonus`) and which are net-new (`PoliticsDispute`, `PoliticsDelegate`, `PoliticsArgument`, the venue-dispute manager class). Name the file home (extend `politics.py` vs new module — propose new module `politics_dispute.py` per the SA-P2 touch zone at line 1479; design doc affirms). *Risk*: ambiguity here forces SA-P2 to re-litigate; mitigated by making the section explicit. Touches: `requirements/sa_politics_design.md`.
3. **Author sections 2-3 — Lifecycle, round structure, dispute templates (~2 hr).** Section 2: lock round count or range (recommend 3 rounds standard; campaign disputes may use 5 — the campaign-style multi-session arcs in SA-P3 line 1549). Phase order per round (open arguments → counter-arguments → conviction adjustments → vote-or-defer). Game-day deadline mechanic. Multi-session persistence (a `pending_disputes` list on the player; the venue surfaces what's open per visit). Section 3: dispute-template schema (id, headline, factions_affected, base_difficulty, delegate_roster, eligible_framings, eligible_evidence, outcome_matrix). Outcome matrix worked example for one Verdant water-rights template (3 outcome rows minimum: win / partial_win_coalition_thin / partial_win_off_record / loss — yes, four rows since the partial-win category has two flavors per locked decision). *Risk*: schema incompleteness — mitigated by walking through what SA-P3's template author needs: every required field with type + example. Touches: `requirements/sa_politics_design.md`.
4. **Author section 4 — AI delegate behavior model (~2 hr).** Hidden position vector: 3-5 dimensions per dispute (e.g., for water-rights: pro-modernization, pro-status-quo, pro-frontier, pro-Verdant-rep). Persuasion vectors: which framing categories move which delegates (worked examples: Hask responds to soil-impact framings, resists modernization framings; Drift responds to data-driven framings, anticipates Hask's objections per voice sheet line 987). Bias values (faction loyalty, prior-dispute memory, player rep history). Deterministic update rules per round (no rolls; delegates' visible state moves by fixed amounts based on argument outcomes). Walk Hask + Drift through three rounds of a water-rights dispute end-to-end as a worked example so SA-P2 implementers have a concrete test-fixture spec. *Risk*: under-specified update rules force SA-P2 to invent them, which leaks design into implement; mitigated by the worked example. Touches: `requirements/sa_politics_design.md`.
5. **Author sections 5-6 — Player input model + argument-construction submechanic (~2 hr).** Section 5: five input modes (vote / argue / mediate / abstain / coalition-build) — per-mode mechanic, skill, cost, outcome. Coalition-build is pre-session corridor interaction (per locked Risk); the other four are in-session. Section 6: argument-construction submechanic. Three slots (framing / evidence / audience). Slot resolution formula: `effective = base_skill + framing_mod + disposition_mod + crew_bonus + tree_bonus`. Worked example: a Persuasion-3 player with Desta Coll on crew + `coalition_sway` skill at level 2 argues for water-rights phasing in front of Drift, framing "data-precedent," evidence "Forgeworks 2324 partnership," audience "Drift specifically." Walk the math — `3 + 1 (precedent framing) + 0 (Drift neutral disposition) + 0.15 (Desta) + 0.20 (skill at L2) = 4.35` round to 4 → vs difficulty 4 = pass. Counter-argument: Hask fires an objection; if the player stocked a "soil-impact rebuttal" in slot one it pre-empts. *Risk*: math example wrong → implementers code wrong formula; mitigated by walking it slot-by-slot end-to-end. Touches: `requirements/sa_politics_design.md`.
6. **Author section 7 — Integration commitments (~1.5 hr).** Six commitments each anchored with concrete examples + threshold values:
   - Reputation: rep delta matrix per outcome category (e.g., win Verdant water-rights: +5 Verdant, -2 Crimson Reach via spillover); flows through `apply_reputation_with_spillover`.
   - Market: outcome shifts commodity prices for N game-days; lock N at 30 (per SA-P3 AC 5 line 1557) with magnitude range ±5%-15% per outcome category.
   - Missions: locking convention `dispute_resolved("water_rights_phasing")` and `coalition_won("water_rights_phasing")` flag helpers per SI-3 cookbook; mission JSON `required_flags` consume.
   - Skill tree: `coalition_sway_bonus` adds to argument resolution; `coalition_size_bonus` adds (floored to int) to corridor pre-commits; `arbitration_neutrality_bonus` adds to mediation resolution. Per-bonus consumer surfaces in section 8 UI sketches.
   - Crew: Desta Coll + Cass Weller via `crew_roster.get_bonus(...) + progression.get_bonus(...)` stacking. `arbitration_dispute_intel` (Cass binary) reveals delegate hidden-position estimates pre-session.
   - News: headline threshold (faction-tier crossing OR ≥10% commodity shift) AND (win or loss); template format ≤80 chars; per-template skeletons authored by SA-P3 / SA-P4 / SA-P5.
   *Risk*: integration commitments without numbers leak into implementation — mitigated by numeric thresholds throughout. Touches: `requirements/sa_politics_design.md`.
7. **Author section 8 — UI flow sketch (~1.5 hr).** Box-diagram or ASCII layouts for: dispute list (council session agenda), dispute open screen, per-round screen, argument composer (3-slot), delegate state display, vote / abstain action bar, empty state ("Council in recess. Next session in 3 days."), loading state, locked state ("You don't have standing"), error state. One sketch per screen; pixel-level layout deferred to SA-P2 (per the OPEN-defer-to-implementation Risk). *Risk*: SA-P2 needing more visual fidelity than box diagrams provide; if so, that's an SA-P2 reopener and SA-X10 (visual identity per venue) catches it later. Touches: `requirements/sa_politics_design.md`.
8. **Author sections 9-10 — Tutorial integration + polish hooks (~1.5 hr).** Section 9: name two PT-M tip flags (`seen_politics_venue_tip`, `seen_argument_composer_tip`); draft tip text for both. Tip 1: "Council convenes here. Vote, argue your case, mediate, or step back. Disputes close on a deadline; missing the deadline counts as abstention." Tip 2: "Argument has three parts. Framing is how you say it. Evidence is what backs it. Audience is who you're persuading. Pick what fits the room." Voice-check both end-to-end; iterate if scanner flags. Section 10: three journal slots (first-attended, first-partial, first-coalition-won); voice-register guidance (captain's working notebook). Two crew-banter slots (Desta corridor, Cass mediation); slot names only — content is SA-X6's. Achievement seed (Council Mediator) for SA-X7. *Risk*: tip text ages out — mitigated by keeping it declarative and short. Touches: `requirements/sa_politics_design.md`.
9. **Author section 11 — Decisions locked + open questions (~45 min).** Numbered list of locked decisions (target ≥10 entries). Each has a one-or-two-line rationale. Pull from: round structure, time pressure, save granularity, partial-win mechanics, coalition mechanic, tutorial scope, news threshold, voice-sheet sufficiency, AI worked example, coexistence with `PoliticsManager`, the deterministic-no-rolls rule (already a CLAUDE.md axiom — restated for SA-P2 implementer). Open-deferred-to-SA-P2 items (pixel layout, exact field names) explicit. *Risk*: a lurking decision that should be locked but isn't surfaces as a Risk in SA-P2 — acceptable per AC 4 of this sprint's stated criterion that anything ambiguous becomes a Risk in SA-P2. Touches: `requirements/sa_politics_design.md`.
10. **Voice-check pass + hand-off checklist + commit (~1 hr).** Read the doc end-to-end; remove em-dashes (replace with periods or commas), check for banned phrases ("couldn't help but," "a testament to," parallel-negation rhetoric), confirm zero banned NPC names. Run the dialogue-integrity scanner over the doc as a precaution (may not flag a requirements doc but a clean run is a clean run). Author the hand-off checklist at the end of the doc: SA-P2 reads sections 1-8; SA-P3 reads sections 3 + 7 + 8 + 9 + 10; SA-P4 reads sections 3 + 4 + 7; SA-P5 reads sections 3 + 7 (+ 4 for delegate variants); SA-X1 / SA-X3 / SA-X6 / SA-X7 each named with the relevant section. Commit `requirements/sa_politics_design.md` referencing SA-P1. *Risk*: forgetting the scanner pass leaves an em-dash that fails downstream voice-check tests; mitigated by running the scanner as the last step before commit. Touches: `requirements/sa_politics_design.md`.
11. **Validation + sentinel (~30 min).** Run `pytest -n auto -q` (no code changed, so this is a no-op confirmation; the baseline 8769 passing / 98 skipped should be unchanged). Confirm Writing Bible scanner clean over `requirements/sa_politics_design.md`. Move `Status` to `review`. Append `**Last phase report.**` block (replacing any prior phase report) with the implement-phase report. Commit with `SA-P1: ...` prefix. Do NOT push.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 15:19 — harness: plan phase starting
- 2026-04-27 15:55 — planning complete; verified all 13 context-to-read paths exist (no missing docs, so no PHASE_BLOCKED); verified SA-PREP-1 outputs (four Verdant council voice sheets and four Alliance Congress delegate voice sheets present and sufficient for SA-P3 / SA-P4 templates), SA-A2 outputs (Desta Coll + Cass Weller crew specialists shipped with `coalition_sway_bonus` / `coalition_size_bonus` / `arbitration_neutrality_bonus` / `arbitration_dispute_intel` bonus_types in `data/crew/crew_members.json`), SA-C2 outputs (`coalition_sway`, `delegate_reach`, `mediation_instinct` Tier-2 nodes in `progression.py` per `sa_skill_design.md` sections 1.2-1.4); locked 9 decisions (PoliticsManager coexists with new dispute system; player-paced rounds with game-day deadlines; round-boundary save granularity; deterministic partial-win categories at 60% coalition-thin threshold; coalition-build as pre-session corridor sub-view; tutorial fold-in lives in SA-P3, SA-P1 specifies tip flags + text; news threshold = faction-tier crossing OR ≥10% commodity shift AND win-or-loss; voice sheets sufficient; AI worked example uses Hask + Drift on water-rights phasing); folded in 3 polish items into the design-doc deliverables (PT-M tip-flag spec; journal-entry slot naming; news-ticker template format); refined acceptance criteria from 4 → 15 mechanically testable items; expanded touch zones from 1 to 2 (added `character_voices.md` Activity log only); documented two OPEN-defer-to-SA-P2 risks (pixel-level UI layout; exact dispute-model field names). No new sprints proposed. PHASE_OK
- 2026-04-27 15:28 — harness: implement phase starting (rework cycle 0)
- 2026-04-27 16:30 — authored `requirements/sa_politics_design.md` (60 KB, 11 sections); all 15 acceptance criteria satisfied; test suite 8769/98 unchanged; Writing Bible scanner + dialogue-integrity scanner both clean; no code changes. PHASE_OK
- 2026-04-27 15:44 — harness: review phase starting (rework cycle 0)
- 2026-04-27 17:00 — review complete; 1 minor finding fixed directly (section 2.2 counter-argument mechanic had two errors: opposition qualifier listed as `leaning_yes/wavering` instead of `leaning_no/committed_no`, and counter-argument target described as "player's audience slot" contradicting Round 2 worked example where Hask targets Drift, not Hask). Fixed in commit e71ca89. All 15 acceptance criteria confirmed met. Test suite 8769/98. PHASE_OK
- 2026-04-27 15:52 — harness: review passed, marking done
**Last phase report.**
- Phase: review
- Outcome: PHASE_OK
- Started: 2026-04-27 15:44
- Completed: 2026-04-27 17:00
- Files_changed: requirements/sa_politics_design.md
- Commits: e71ca89
- Tests_passing: 8769
- Acceptance_criteria_verified: 15/15
- Polish_items_verified: 3/3
- Findings_critical: 0
- Findings_minor_fixed_directly: 1
- Single_tighten: section 2.2 counter-argument description (fixed): opposition-delegate qualifier was inverted (leaning_yes→leaning_no) and target-selection rule contradicted the section 4.6 worked example -- SA-P2 implementers reading both would have gotten conflicting instructions.
- Followup_sprints_added: none
- Notes: Design doc is thorough and SA-P2-ready. The counter-argument inconsistency was the only substantive finding; corrected directly. All 15 locked decisions have rationales; two explicit deferred-to-SA-P2 items named. Worked example (Hask+Drift, 3 rounds) is usable as a SA-P2 unit test fixture.
#### SA-P2 — Politics Core

**Status**: in-progress (planning)
**Phase**: Phase II | **Size**: XL | **Effort**: 2 weeks
**Depends on**: SA-P1, SA-A2, SA-C2, SA-B-EXT-1 | **Blocks**: SA-P3, SA-P4, SA-P5

**Goal.** Implement the Politics system core mechanic: dispute representation, player choice flow, argument-construction submechanic, AI delegate behavior, multi-skill-check resolution, outcome propagation. Venue-agnostic engine. SA-P3/P4/P5 add content (templates, dialogue, named delegates) on top of this engine.

**Context to read.**
- `requirements/sa_politics_design.md` (sections 1-8 are load-bearing per the hand-off checklist)
- `requirements/agent_principles.md`
- `requirements/aurelia_voice_examples.md` (skim — SA-P2 authors no in-character dialogue; only flag strings, error/empty/locked-state copy, and the "Effective vs Difficulty" preview label)
- `spacegame/models/politics.py` (existing `PoliticsManager`; reuses `apply_reputation_with_spillover` at line 399)
- `spacegame/models/social.py` (`SocialManager.get_effective_level`, `resolve_check`, disposition modifier formula at line 249)
- `spacegame/models/progression.py` (`get_bonus()` semantics; `coalition_sway`, `delegate_reach`, `mediation_instinct` skills already exist at lines 942/1054/1105)
- `spacegame/models/crew.py` (`CrewRoster.get_bonus`; Desta Coll and Cass Weller already defined in `data/crew/crew_members.json:721-773` with the bonus types this sprint consumes)
- `spacegame/models/market.py` (existing `MarketEvent` single-active-per-market pattern; this sprint adds a parallel multi-shift registry — see Plan task 9)
- `spacegame/models/news_ticker.py` (`add_headline()` direct path; SA-P2 does not author templates)
- `spacegame/models/sub_reputation.py` (SA-B-EXT-1 sub-rep tier model; corridor failure deducts here)
- `spacegame/views/base_view.py`, `spacegame/views/CLAUDE.md`
- `spacegame/views/first_time_tip.py` (PT-M `FirstTimeTipOverlay`; SA-P2 only adds the *flag helpers* — overlay wiring is SA-P3 per SA-P1 §11 decision 7)
- `spacegame/views/station_hub_view.py` (`UNIQUE_HALL_TARGETS` mapping at line 97 — SA-P2 adds the verdant_mayors_council entry)
- `spacegame/save_manager.py` (lines 471, 716 show the `political_state` save/load slot — SA-P2 adds a parallel `politics_dispute_state` slot)
- `spacegame/constants/flags.py` (helper-function pattern; SA-P2 adds the five helpers from SA-P1 §7.3 + §9.1)
- `requirements/onboarding_design.md` (SA-P2's only onboarding deliverable is the flag-helper plumbing for SA-P3 to consume)
- `requirements/si3_flag_registry_cookbook.md`

**Touch zones.**
- `spacegame/models/politics_dispute.py` (NEW — `PoliticsDispute`, `PoliticsDelegate`, `PoliticsArgument`, `PoliticsDisputeTemplate`, `OutcomeRow`, `PoliticsMarketShift`, `PoliticsDisputeManager`, lifecycle enum `DisputePhase`)
- `spacegame/models/player.py` (add `politics_dispute_state: dict` field, parallel to `political_state`)
- `spacegame/models/market.py` (add `politics_shifts: dict[(commodity_id, system_id), list[PoliticsMarketShift]]` registry; hook into `_calculate_price`/`update_day` for largest-magnitude-wins stack rule and decay)
- `spacegame/models/social.py` (no API changes; consume `get_effective_level` and `resolve_check`)
- `spacegame/save_manager.py` (serialize/deserialize `politics_dispute_state`; additive — no `SAVE_VERSION` bump per SA-P1 §11 decision 15)
- `spacegame/data_loader.py` (NEW `load_politics_disputes` + `_parse_politics_dispute_template`; reads `data/politics/*.json` if dir exists, otherwise empty dict — content is SA-P3/P4/P5)
- `spacegame/views/dispute_view.py` (NEW — single view with internal substates: `LIST` / `CORRIDOR` / `SESSION` / `COMPOSER` / `TALLY`; empty/locked/loading/error states; live preview)
- `spacegame/engine/game.py` (instantiate `PoliticsDisputeManager`; `_ensure_dispute_view()`; transition routing; news-headline hand-off; market-shift tick wiring)
- `spacegame/config.py` (add `GameState.DISPUTE`; map it in any state-name lookup tables)
- `spacegame/constants/flags.py` (add `dispute_resolved`, `coalition_won`, `dispute_mediated`, `seen_politics_venue_tip`, `seen_argument_composer_tip`)
- `spacegame/views/station_hub_view.py` (add `verdant_mayors_council: GameState.DISPUTE` to `UNIQUE_HALL_TARGETS` so the engine has one wired venue for end-to-end tests; SA-P3 keeps this entry)
- `tests/test_models/test_politics_dispute.py` (NEW — manager state machine, lifecycle, save/load round-trip)
- `tests/test_models/test_politics_delegate.py` (NEW — visible-state transitions, position-vector caps, bias initialization)
- `tests/test_models/test_politics_argument.py` (NEW — composer slot rules, resolution formula, framing-to-skill routing, evidence access)
- `tests/test_models/test_politics_outcome_propagation.py` (NEW — rep deltas via spillover, market shifts, mission flags, news headline gating per §7.6)
- `tests/test_models/test_market_politics_shifts.py` (NEW — stack rule, decay, expiry)
- `tests/test_views/test_dispute_view.py` (NEW — substate transitions, empty/locked/loading/error renders, composer live-preview)
- `tests/test_scenarios/test_scenario_politics_loop.py` (NEW — full Hask+Drift+Marsh worked example from SA-P1 §4.6 plus an alternate mediation path; both run end-to-end through manager and view)

**Deliverables.**
- `politics_dispute.py` module with the six dataclasses, manager class, and lifecycle enum.
- `flags.py` helpers matching SA-P1 §7.3 + §9.1 exactly (no overlay wiring in this sprint).
- DataLoader politics-template loader (gracefully empty when SA-P3 content not yet present).
- Argument-construction resolution honoring skill routing (Persuasion / Leadership), framing modifier, disposition modifier, crew bonus, tree bonus, evidence-absent +1 difficulty.
- Multi-round dispute state machine: open arguments → counter-arguments (with pre-emption) → conviction adjustments → vote-or-defer.
- Coalition pre-commit corridor (skill check, sub-rep deduction on fail, escalating difficulty on repeated failure, cap formula from §5.5).
- Outcome resolution emitting: rep deltas via `apply_reputation_with_spillover`; market shifts via the new registry (largest-magnitude-wins stack rule, 30-day decay); mission flags via the new helpers; news headline via `news_ticker.add_headline` gated on §7.6 conditions; Cass Weller `arbitration_dispute_intel` qualitative reveal once per session.
- `dispute_view.py` with all substates including empty/locked/loading/error states and composer live preview.
- `GameState.DISPUTE` plumbed end-to-end through `station_hub_view → game.py → dispute_view`, anchored at `verdant_mayors_council`.
- Save/load round-trip at every dispute boundary.
- 30-50+ new tests across model, view, and scenario layers.

**Acceptance criteria.**
1. Synthetic test dispute (in-test fixture mirroring SA-P1 §4.6 `water_rights_phasing`) runs through every input path: in-session `vote` / `argue` / `mediate` / `abstain`, plus pre-session `coalition-build`. Each path is exercised by at least one unit or scenario test.
2. Argument-construction resolution matches the formula in SA-P1 §6.2 byte-for-byte: `floor(base_skill + framing_mod + disposition_mod + crew_bonus + tree_bonus) >= base_difficulty`. Worked numerical examples in §4.6 and §6.3 reproduce exactly in tests (Drift round-1 pass at effective 4 vs D4; Marsh community_benefit mediation fail at effective 3 vs D4).
3. Delegate updates are deterministic — no `random.*` calls in the resolution stage. Same inputs always produce identical outputs across two manager runs (verified by a parameterized test).
4. Partial-win outcomes are reachable in tests: both `partial_win_coalition_thin` (vote passes with <60% pre-committed) and `partial_win_off_record` (vote fails with at least one `conceded` flag) fire from the synthetic fixture, with the §11 decision-5 thresholds explicitly asserted.
5. Outcome propagation: for the synthetic fixture, all four outcome categories propagate end-to-end. Tests assert (a) rep deltas applied through `apply_reputation_with_spillover` (spillover to rivals visible), (b) market shifts registered with correct magnitude/duration/system, (c) mission flags set via `dispute_resolved` / `coalition_won` / `dispute_mediated` helpers, (d) news headline fires when §7.6 conditions hold and is suppressed when they don't (both branches asserted).
6. Save/load round-trips an in-progress dispute at every committed boundary: at start of `ROUND_OPEN` round 1, at `ROUND_PENDING` after a counter-argument resolved, after `RESOLVING` once outcome fires. Mid-round composer state (uncommitted) is not persisted, by design.
7. Coalition-building measurably improves starting positions: in a controlled test, a player with 0 pre-commits, 1 pre-commit, and 2 pre-commits produces strictly different starting visible-state distributions. With Desta + delegate_reach L1, the cap reaches 2 and the 60% threshold is achievable on a 3-delegate dispute.
8. 30-50+ new tests across the seven new test files, all passing. Pre-phase baseline of 8769 passing / 98 skipped is the floor; new failures vs. baseline block the sprint.
9. Full suite green; `ruff format`, `ruff check`, `mypy` clean over the touched files (per AGENT_GUIDE — scope formatting to changed files only).
10. Empty-state, locked-state (insufficient standing), loading-state, and error-state UI for the dispute list each render correctly under fixture inputs (verified by view tests).
11. Argument composer live preview updates the "Effective N vs Difficulty M — PASSES/FAILS" indicator when framing / evidence / audience / responds-to selections change. Verified by view test that simulates four selection changes and asserts the preview text after each.
12. `flags.py` helpers `dispute_resolved`, `coalition_won`, `dispute_mediated`, `seen_politics_venue_tip`, `seen_argument_composer_tip` exist and produce strings byte-for-byte matching SA-P1 §7.3 + §9.1. Tutorial overlays are NOT wired in SA-P2 (locked decision; SA-P3 wires them).
13. Sub-reputation deduction (SA-B-EXT-1) fires on a failed corridor visit — 1-point loss with the delegate's sub-tier faction. Repeated consecutive failures with the same delegate raise corridor difficulty +1 the next session and reset on a successful visit or dispute resolution.
14. Market-shift stack rule verified: when two active politics shifts target the same `(commodity_id, system_id)`, the larger absolute magnitude applies; both shifts decay independently after their own `duration_days`. Politics shifts coexist with the existing `MarketEvent` (no interference test).
15. Cass Weller's `arbitration_dispute_intel` qualitative reveal fires once per session on first venue entry (when on crew); a second venue entry within the same session does not re-fire. The reveal text is derived from the delegate's hidden position vector and surfaces only the qualitative summary, not the raw floats.
16. Performance smoke: a single argument resolution call (manager `submit_argument`) completes in <100 ms on the worked-example fixture, asserted via `time.perf_counter()`. (60-FPS UI budget remains a manual smoke check; not automated this sprint.)

**Plan.**

1. **Foundation scaffolding.** Add `GameState.DISPUTE` to `config.py`. Add the five helper functions to `spacegame/constants/flags.py`. Create empty `spacegame/models/politics_dispute.py` skeleton with the seven names (six dataclasses + manager) and a `DisputePhase` enum. No logic yet — just the shape that downstream tasks will fill in.
   - Files: `spacegame/config.py`, `spacegame/constants/flags.py`, `spacegame/models/politics_dispute.py` (new).
   - Tests: `tests/test_models/test_politics_dispute.py` covers the flag-helper string output (AC 12). Failing test first per TDD.
   - Risks: none.

2. **Dataclass shapes (TDD red-first).** Implement `PoliticsDisputeTemplate` (frozen, all fields from SA-P1 §3.1 required), `OutcomeRow`, `MarketShift`, `PoliticsDelegate` (mutable runtime, includes `visible_state`, `position_vector: dict[str, float]`, `disposition`, `conceded` flag, `pre_committed` flag), `PoliticsArgument` (composer state), `PoliticsDispute` (mutable runtime instance with `current_round`, `phase`, `delegates`, `resolved_outcome`, etc.), and `to_dict`/`from_dict` on the runtime classes. Bias-value application at session init.
   - Files: `spacegame/models/politics_dispute.py`.
   - Tests: `tests/test_models/test_politics_dispute.py` (round-trip serialization), `tests/test_models/test_politics_delegate.py` (state-machine transitions, position-cap at +/-1.0, bias-init formula).
   - Risks: dataclass-table compliance scanner (per CLAUDE.md row 6) — dispute templates loaded from JSON must be `@dataclass(frozen=True)`.

3. **DataLoader integration.** Add `load_politics_disputes` and `_parse_politics_dispute_template`. The loader reads any `data/politics/*.json` files (SA-P3 will populate; SA-P2 only ships the loader). The loader must tolerate an empty/missing directory and return an empty dict — no error. Templates loaded into `self.politics_disputes: dict[str, PoliticsDisputeTemplate]`.
   - Files: `spacegame/data_loader.py`.
   - Tests: integration test in `tests/test_models/test_politics_dispute.py` confirms an empty data dir returns `{}` and a fixture template parses correctly.
   - Risks: low — same pattern used by every existing loader.

4. **Argument-construction resolution.** Implement the resolution formula in `PoliticsDisputeManager._resolve_argument()`: skill routing by framing (Persuasion default, Leadership for `frontier_autonomy`), framing modifier, disposition modifier, crew bonus (`coalition_sway_bonus` for argue / `arbitration_neutrality_bonus` for mediate), tree bonus, evidence-absent +1 difficulty. `floor(effective) >= base_difficulty` = pass. Pull bonuses from `progression.get_bonus()` and `crew_roster.get_bonus()` exactly per `views/mining_view.py:417` stacking convention.
   - Files: `spacegame/models/politics_dispute.py`.
   - Tests: `tests/test_models/test_politics_argument.py` reproduces the §4.6 round-1 Drift pass and the §6.3 Marsh mediation fail by exact arithmetic.
   - Risks: float ordering (use `pytest.approx` per CLAUDE.md). The `// 10` integer disposition mod must mirror `social.py:249` formula exactly — write a parameterized test against several disposition values.

5. **Per-round state machine.** Implement the four-phase round (open arguments → counter-arguments → conviction adjustments → vote-or-defer) per SA-P1 §2.2. Counter-argument target-selection rule is the corrected one from SA-P1 §2.2 (most-favorable-toward-yes, not committed_yes). Pre-emption when player loaded `responds_to` matching the counter's framing. `committed` delegates are immovable by arguments. Position-vector caps at +/-1.0. Visible-state chain `committed_no → leaning_no → wavering → leaning_yes → committed_yes`.
   - Files: `spacegame/models/politics_dispute.py`.
   - Tests: `tests/test_models/test_politics_delegate.py` covers each transition rule from SA-P1 §4.4 table; `tests/test_scenarios/test_scenario_politics_loop.py` runs the full §4.6 worked example.
   - Risks: counter-argument target-selection edge case (no eligible target → counter is no-op); document and assert.

6. **Coalition pre-commit corridor.** Implement `start_corridor_visit(delegate_id, framing) → (success, msg)`. On success, set delegate `pre_committed = True` and `visible_state = leaning_yes`. On failure, deduct 1 sub-rep with the delegate's sub-tier faction (SA-B-EXT-1) and increment a per-delegate consecutive-fail counter that adds +1 to corridor difficulty next session. Counter resets on a successful visit OR when the dispute resolves. Cap formula: `1 + floor(crew_roster.get_bonus("coalition_size_bonus") + progression.get_bonus("coalition_size_bonus"))`.
   - Files: `spacegame/models/politics_dispute.py`, `spacegame/models/sub_reputation.py` (read-only — call existing API).
   - Tests: `tests/test_models/test_politics_delegate.py` covers cap formula across 0/1/2/3 pre-commits with crew + skill combinations; corridor-failure consecutive-fail escalation.
   - Risks: `SocialManager` constructor takes no args (per CLAUDE.md pitfalls) — instantiate with `set_progression(prog)` after creation.

7. **Outcome resolution + propagation.** Implement `_finalize_outcome()`: tally votes via §5.1 visible-state-to-vote mapping (wavering = no, per §11 decision 13); pick category by §5.1 rules (60% pre-commit threshold for win vs partial_win_coalition_thin; conceded flag rescues failed votes to partial_win_off_record). Apply `outcome_matrix[category]`: rep deltas via `apply_reputation_with_spillover`, market shifts via the new registry (task 9), mission flags via the new helpers, news headline via `news_ticker.add_headline` gated on §7.6 conditions. Move dispute from `pending_disputes` to `resolved_disputes` on player state.
   - Files: `spacegame/models/politics_dispute.py`, `spacegame/engine/game.py` (provide `politics_manager` + `news_ticker` + `market` to manager constructor).
   - Tests: `tests/test_models/test_politics_outcome_propagation.py` covers all four outcome categories end-to-end with a synthetic fixture, asserting each propagation channel and §7.6 news gating in both directions.
   - Risks: `apply_reputation_with_spillover` mutates player rep — verify spillover-to-rival is observed in tests, not just primary delta.

8. **Cass Weller intel reveal + `seen` flags.** Implement once-per-session reveal: on first venue entry where Cass is on crew, generate qualitative summary text from each delegate's hidden position vector ("Skeptical of modernization proposals. High resistance to outside evidence."). Store a per-session `intel_revealed` flag on the manager (not the player; resets on session leave) so it does not re-fire within the session. Subsequent sessions do re-fire.
   - Files: `spacegame/models/politics_dispute.py`.
   - Tests: `tests/test_models/test_politics_delegate.py` covers the float-to-text translation (positive / negative / neutral thresholds) and the once-per-session gate.
   - Risks: text strings are player-facing — voice-check (declarative, no em-dashes, no banned phrases). Strings are SHORT and engine-emitted, not in-character dialogue, so the SL-5 "out-of-world UI copy" register applies (terse, no flavor text).

9. **Market shift registry.** Add `politics_shifts: dict[tuple[str, str], list[PoliticsMarketShift]]` to `Market`. Each shift carries `commodity_id`, `system_id`, `magnitude`, `start_day`, `duration_days`. On `_calculate_price`/`get_current_price`, apply the largest-absolute-magnitude active shift for the (commodity, system) pair. On `update_day(new_day)`, expire shifts where `new_day >= start_day + duration_days`. Shifts coexist with the existing `MarketEvent` single-active-event slot — they multiply, not replace.
   - Files: `spacegame/models/market.py`.
   - Tests: `tests/test_models/test_market_politics_shifts.py` covers stack rule (two overlapping shifts), decay, coexistence with `MarketEvent`.
   - Risks: existing market test suite must remain green — confirm by re-running `tests/test_models/test_market*.py`.

10. **Save / load round-trip.** Add `politics_dispute_state` field to `Player` (default `dict`). Serialize the manager state (active session, pending disputes, resolved disputes, sub-rep escalation counters, market-shift registry — though shifts live on Market, snapshot them here for save fidelity). `from_dict` uses `data.get("politics_dispute_state", {})`. No `SAVE_VERSION` bump (additive, per SA-P1 §11 decision 15).
    - Files: `spacegame/models/player.py`, `spacegame/save_manager.py`, `spacegame/models/politics_dispute.py` (manager `to_dict`/`from_dict`).
    - Tests: `tests/test_models/test_politics_dispute.py` covers round-trip at three boundaries (ROUND_OPEN start, ROUND_PENDING mid-dispute, post-RESOLVING).
    - Risks: omitting a field in `to_dict` and reading the old default in `from_dict` produces silent regression — write the round-trip test BEFORE adding new fields.

11. **`dispute_view.py` substates.** Single `BaseView` subclass with internal substate enum (`LIST` / `CORRIDOR` / `SESSION` / `COMPOSER` / `TALLY`). Each substate has its own `_create_ui_*` / `_destroy_ui_*` paired methods; switching substate destroys the previous UI and rebuilds. Empty/locked/loading/error states render in the `LIST` substate; locked-state checks the player's faction standing against a configurable threshold (default −25 per §8.1 mock). Argument composer (`COMPOSER` substate) wires live preview: an `_update_preview()` method recomputes effective level on every selection change and updates the label text without rebuilding the UI.
    - Files: `spacegame/views/dispute_view.py`.
    - Tests: `tests/test_views/test_dispute_view.py` exercises substate transitions and live preview (drive UI events programmatically; check label text after each change). Use `tests/test_ui_layout/conftest.py` `SDL_VIDEODRIVER=dummy` pattern if needed.
    - Risks: pygame_gui element leakage — every `_create_ui_*` must have a matching `_destroy_ui_*`; `on_exit()` calls the current substate's destroy. Run a leak test: create + destroy each substate twice, assert no `RuntimeError`.

12. **Game.py wiring.** Add `_ensure_dispute_view()` factory mirroring `_ensure_deep_shafts_view()`. Instantiate `PoliticsDisputeManager` at startup (after `politics_manager` and `news_ticker` are ready) — it needs handles to those plus `market`, `crew_roster`, `progression`, `social_manager`. Add the transition handler in `_handle_state_transitions()` (FADE 0.3s, mirror Deep Shafts at line ~1867). Add `verdant_mayors_council: GameState.DISPUTE` to `UNIQUE_HALL_TARGETS` in `station_hub_view.py:97`. Wire dispute resolution to call `news_ticker.add_headline` directly when the §7.6 conditions hold.
    - Files: `spacegame/engine/game.py`, `spacegame/views/station_hub_view.py`.
    - Tests: scenario test (task 13) walks station_hub → dispute → outcome → station_hub.
    - Risks: state-transition ordering — ensure manager is initialized BEFORE first frame; failing-test-first.

13. **Scenario test (full loop).** `tests/test_scenarios/test_scenario_politics_loop.py`: build a synthetic in-test water_rights_phasing fixture (do NOT add to `data/politics/` — that's SA-P3). Run the §4.6 Hask+Drift+Marsh three-round walk-through end-to-end through manager + view, assert each integration channel after each round (delegate state, position vectors, save round-trip), assert the loss outcome at the end with all propagation. Run an alternate path: round-2 mediation of Marsh, vote at round 3, assert `partial_win_off_record` outcome and the appropriate flag set.
    - Files: `tests/test_scenarios/test_scenario_politics_loop.py`.
    - Risks: scenario tests can become brittle to refactors — keep the assertions on observable contract (rep, market, flags, news), not on internal manager fields.

14. **Performance smoke.** Inside `tests/test_models/test_politics_dispute.py`, time `manager.submit_argument()` on the worked-example fixture with `time.perf_counter()`. Assert <100 ms. No automated 60-FPS check (UI rendering); rely on manual smoke during view-test runs.
    - Files: `tests/test_models/test_politics_dispute.py`.
    - Risks: low — argument resolution is arithmetic, no allocations beyond manager bookkeeping.

15. **Lint + format + scanner pass.** `ruff format` and `ruff check` over the touched files only (per AGENT_GUIDE: do NOT run project-wide). `mypy spacegame/models/politics_dispute.py spacegame/views/dispute_view.py`. Writing Bible scanner over any new player-facing strings (the "Council in recess.", "You don't have standing.", "Effective N vs Difficulty M — PASSES" labels). The em-dash banned phrase rule applies; the existing copy uses em-dashes in some mocks — replace with semicolons or restructure before committing.
    - Risks: scanner catches em-dashes in `dispute_view.py` mock-derived strings — review before commit.

**Decisions locked in this planning phase.**
1. **Field name lock**: player attribute is `politics_dispute_state: dict` (parallel to existing `political_state`, distinct keyspace). Rationale: avoids namespace collision with the existing ambient `PoliticsManager` state and lets save migration treat them independently.
2. **Module name lock**: `spacegame/models/politics_dispute.py` houses all six dataclasses (`PoliticsDispute`, `PoliticsDelegate`, `PoliticsArgument`, `PoliticsDisputeTemplate`, `OutcomeRow`, `PoliticsMarketShift`) + `PoliticsDisputeManager` + `DisputePhase` enum. Rationale: single-module locality matches SA-P1 §1.6; downstream sprints test in isolation.
3. **GameState lock**: single `GameState.DISPUTE` value covers all venues. Venue identity travels via the manager's `enter_venue(venue_id)` call. Per-venue visual identity is SA-X10. Rationale: one engine, many venues — a venue-per-state pattern would multiply the state machine without value.
4. **News ticker hook lock**: dispute headlines fire via `news_ticker.add_headline(text, priority=N)` direct call, not via the templates JSON. Rationale: dispute headlines are per-instance, authored in the dispute template's `outcome_matrix`, not aggregated patterns; templates are for ambient world state.
5. **Market shift implementation lock**: a NEW `politics_shifts` registry on `Market` rather than reusing `MarketEvent`. Rationale: existing `MarketEvent` is single-active-per-market and ambient-event-driven; politics shifts need multi-stack coexistence with §11 decision 14's largest-magnitude rule.
6. **Save migration lock**: `politics_dispute_state` is additive. No `SAVE_VERSION` bump. `from_dict` uses `data.get("politics_dispute_state", {})`. Per SA-P1 §11 decision 15 + CLAUDE.md save migration rules.
7. **Tutorial overlay scope lock**: SA-P2 ships `flags.py` helpers ONLY; the `FirstTimeTipOverlay` instances are wired by SA-P3 per SA-P1 §11 decision 7. Rationale: same pattern as SA-V (tip wired by the venue sprint, not a separate one).
8. **Synthetic fixture lock**: the SA-P1 §4.6 worked example is a pure in-test Python fixture (built in `_make_water_rights_phasing_template()`), NOT a JSON file under `data/politics/`. Rationale: SA-P3 owns content; SA-P2 owns the engine and tests it with a synthetic-only fixture so this sprint can ship with no `data/politics/*.json` content.
9. **UI scope lock**: SA-P2 implements the structural UI (substates, list/corridor/session/composer/tally, empty/locked/loading/error states, live preview). Pixel-level layout (button placement, font sizes, color choices) and venue-specific theming are deferred to SA-X10 / SA-P3, per SA-P1 §11 deferred items.
10. **Counter-argument target rule lock**: the SA-P1 §2.2 corrected text is authoritative — opposition delegate fires counter at the most-favorable-toward-yes delegate who is not `committed_yes`, with pre-emption when the player stocked a matching `responds_to` framing.
11. **`SAVE_VERSION` no-bump lock**: confirmed reading `save_manager.py:28` (`SAVE_VERSION = "1.0"`). Adding `politics_dispute_state` is additive and tolerated by the existing version check.

**Risks / open questions.**
- ~~Argument-construction load-bearing: if SA-P1 left this ambiguous, this sprint blocks back.~~ **Resolved.** SA-P1 sections 4-6 fully specify the resolution formula with two worked numerical examples (§4.6 Drift round-1 pass, §6.3 Marsh mediation fail). No ambiguity.
- ~~Existing politics_manager scope: extend or replace?~~ **Resolved.** SA-P1 §1.3 + §11 decision 1 lock coexistence in a new module. Confirmed `apply_reputation_with_spillover` is the only shared primitive.
- **Performance**: argument resolution <100 ms is captured as AC 16 (perf smoke). 60-FPS UI budget is a manual smoke during view test runs — not automated this sprint. If view rendering drops below budget, raise as a follow-up rather than blocking SA-P2 review.
- **Sub-reputation faction mapping**: each delegate must declare which sub-tier faction takes the rep loss on a failed corridor visit. SA-P1 §5.5 says "the delegate's sub-tier faction" but doesn't specify the mapping. Locked here: `PoliticsDelegate` carries a `sub_faction_id: str` field set by the dispute template; SA-P3 content authors populate it per delegate. SA-P2 ships the field and the deduction call; the synthetic fixture sets sub_faction_ids inline.
- **Cass Weller intel reveal text catalog**: the qualitative-summary text is generated from float thresholds (e.g., position < −0.5 → "Skeptical of"; > +0.5 → "Open to"). SA-P2 ships a small dispatch table for the three Verdant dimensions used by the synthetic fixture (`modernization`, `water_rights_change`, `outside_influence`); SA-P3/P4 extend the table when adding new dimension labels. This is engine code that emits text, not authored content — voice-check the strings against `aurelia_voice_examples.md` at commit time.
- **Test count uncertainty**: 30-50+ is the AC range. The plan above implies roughly: 6 (flag helpers) + 12 (dataclass + state-machine) + 8 (resolution formula + worked examples) + 8 (outcome propagation) + 5 (market shifts) + 4 (corridor/coalition) + 6 (view substates) + 4 (scenario) + 1 (perf) ≈ 54 tests. If the actual count lands below 30, the implementer should add edge cases rather than artificially split assertions.

**Activity log.**
- 2026-04-26 — todo (created)
- 2026-04-27 15:53 — harness: plan phase starting
- 2026-04-27 16:35 — planning complete; expanded scope to include market-shift registry, sub-rep deduction wiring, Cass Weller intel reveal, empty/locked/loading/error UI states, live composer preview, and SA-P1 §7.3+§9.1 flag helpers. Locked 11 decisions and resolved 2 of 3 prior open questions. No new sprints proposed — the design doc explicitly defers content (templates, dialogue, named delegates) to SA-P3/P4/P5 and tutorial overlay wiring to SA-P3. Verified all 5 context-to-read paths exist on disk and the design doc covers sections 1-8 per the SA-P1 hand-off checklist. PHASE_OK

**Last phase report.**
- Phase: plan
- Outcome: PHASE_OK
- Started: 2026-04-27 16:00
- Completed: 2026-04-27 16:35
- Files_changed: requirements/roadmap/ROADMAP.md
- Commits: pending
- New_sprints_proposed: none
- Polish_items_folded_in: market-shift registry with stack rule + decay (AC 14); sub-reputation deduction on failed corridor visits (AC 13); Cass Weller arbitration_dispute_intel once-per-session reveal (AC 15); flags.py helper functions for outcome + tip flags (AC 12); empty/locked/loading/error UI states for dispute list (AC 10); live "Effective vs Difficulty" composer preview (AC 11); performance smoke <100ms (AC 16); save/load round-trip at three explicit boundaries (AC 6).
- Decisions_locked: 11
- Notes: Verified all five Context-to-read paths exist on disk. Confirmed Desta Coll and Cass Weller crew members already define the bonus types this sprint consumes (data/crew/crew_members.json:721-773); coalition_sway, delegate_reach, mediation_instinct skills already exist in progression.py. Locked field/module/state names. Sprint stays XL — no split — because the design doc explicitly partitions content (SA-P3/P4/P5) and tutorial wiring (SA-P3) out, leaving SA-P2 as a focused engine sprint with one reachable venue for end-to-end testing.

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
