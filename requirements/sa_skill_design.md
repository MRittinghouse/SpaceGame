# SA Skill Tree Extension Design

**Sprint**: SA-C1
**Status**: final
**Implements for**: SA-C2 (skill implementation), SA-B3, SA-B4, SA-P3, SA-P4, SA-P5, SA-F2, SA-F3, SA-R1, SA-R2

This document is the single source of truth for the seven new skill tree nodes introduced in Phase C of the Station Anchors arc. SA-C2 reads this document to implement the `SkillNode` entries in `create_default_skills()`. Downstream SA sprints read section 2 (bonus-naming convention table) when their views call `progression.get_bonus(...)`.

---

## 1. Skill Roster

One block per new skill. All seven are Tier 2 specialization nodes placed in existing trees per `station_anchors.md` Decision 3 (extend existing trees, no new trees). All seven have `max_level = 2` per the SA-C1 locked scope.

---

### 1.1 Lot Appraiser

**id**: `lot_appraiser`
**display name**: Lot Appraiser
**tree**: Commerce
**tier**: 2 (specialization)
**prerequisite_id**: `market_eye`
**max_level**: 2
**bonus_type**: `auction_lot_appraisal_bonus`
**bonus_per_level**: 0.05
**description** (player-facing): "+5% post-auction valuation accuracy per level"
**magnitude rationale**: SA-A1 range for this bonus type is 0.05-0.15. At `bonus_per_level = 0.05`, the skill contributes +0.05 at level 1 and +0.10 at max level 2. Combined with crew (Sable Trent, +0.10), the stacked maximum is +0.20. This slightly exceeds the SA-A1 crew-alone range upper bound of 0.15, which is intentional: the reward for pairing crew hire with skill investment is a stronger effect than either alone. Balance assumption: the consumer view caps display accuracy at a natural ceiling, so exceeding the crew-alone range does not create broken gameplay.
**narrative hook**: Knowing a lot's actual worth after winning it shapes whether you hold, flip, or factor the purchase into your next run.

---

### 1.2 Coalition Sway

**id**: `coalition_sway`
**display name**: Coalition Sway
**tree**: Social
**tier**: 2 (specialization)
**prerequisite_id**: `silver_tongue`
**max_level**: 2
**bonus_type**: `coalition_sway_bonus`
**bonus_per_level**: 0.10
**description** (player-facing): "+10% delegate persuasion modifier per level in Politics disputes"
**magnitude rationale**: SA-A1 range is 0.10-0.25. At `bonus_per_level = 0.10`, skill max is +0.20 at level 2. Combined with crew (Desta Coll, +0.15), stacked maximum is +0.35. The SA-A1 range reflects the crew value alone; combined investment yields a stronger modifier. SA-C2 implementers should verify the consuming view (politics_view.py) caps effective persuasion at a reasonable upper bound so a fully invested player still faces meaningful delegate resistance.
**narrative hook**: Moving a delegate from uncertain to committed takes patience and the right framing; practicing persuasion at scale makes both more consistent.

---

### 1.3 Delegate Reach

**id**: `delegate_reach`
**display name**: Delegate Reach
**tree**: Leadership
**tier**: 2 (specialization)
**prerequisite_id**: `give_the_word`
**max_level**: 2
**bonus_type**: `coalition_size_bonus`
**bonus_per_level**: 0.5
**description** (player-facing): "+0.5 to delegate pre-commitment cap per level before a Politics vote"
**magnitude rationale**: SA-A1 range is +1 to +2 (integer delegate count). With `bonus_per_level = 0.5`, the skill contributes +0.5 at level 1 and +1.0 at level 2. The consumer view floors the summed float to an integer after summing all sources, so level-1 skill alone contributes +0 and level-2 skill contributes +1. Combined with crew (Desta Coll, +1.0 floored to +1), the stacked maximum is +2, matching the SA-A1 range upper bound exactly. Level-1 investment provides no benefit without crew; this is intentional, creating a meaningful choice between partial investment (crew-dependent) and full investment (crew-plus-skill).
**narrative hook**: A captain who can hold more commitments together before the vote turns fragile coalitions into durable majorities.

---

### 1.4 Mediation Instinct

**id**: `mediation_instinct`
**display name**: Mediation Instinct
**tree**: Social
**tier**: 2 (specialization)
**prerequisite_id**: `empathic_read`
**max_level**: 2
**bonus_type**: `arbitration_neutrality_bonus`
**bonus_per_level**: 0.10
**description** (player-facing): "+10% partial-win odds in mediation resolutions per level"
**magnitude rationale**: SA-A1 range is 0.10-0.20. At `bonus_per_level = 0.10`, skill max is +0.20 at level 2. Combined with crew (Cass Weller, +0.15), stacked maximum is +0.35. As with coalition_sway_bonus, the consumer view (mediation_view.py) should cap partial-win probability shifts so combined investment yields stronger outcomes without making every dispute a guaranteed partial win.
**narrative hook**: Seeing a dispute clearly is the first step; recognizing the partial win that holds is what ends disputes rather than postponing them.

---

### 1.5 Spread Trader

**id**: `spread_trader`
**display name**: Spread Trader
**tree**: Commerce
**tier**: 2 (specialization)
**prerequisite_id**: `tariff_negotiation`
**max_level**: 2
**bonus_type**: `speculator_premium_reduction`
**bonus_per_level**: 0.05
**description** (player-facing): "+5% futures contract spread reduction per level on entry"
**magnitude rationale**: SA-A1 range is 0.05-0.15. At `bonus_per_level = 0.05`, skill max is +0.10 at level 2. Combined with crew (Brix Tano, +0.10), stacked maximum is +0.20. Same dual-investment pattern as lot_appraiser; combined max slightly above the crew-alone range upper bound, acceptable as a reward for pairing crew hire with skill investment.
**narrative hook**: Shaving the spread at entry is the difference between a contract that has to work out perfectly and one that works on a good average.

---

### 1.6 Research Yield

**id**: `research_yield`
**display name**: Research Yield
**tree**: Industry
**tier**: 2 (specialization)
**prerequisite_id**: `efficient_refining`
**max_level**: 2
**bonus_type**: `research_yield_bonus`
**bonus_per_level**: 0.05
**description** (player-facing): "+5% project return at the Okafor Institute per level"
**magnitude rationale**: SA-A1 range is 0.05-0.15. At `bonus_per_level = 0.05`, skill max is +0.10 at level 2. Combined with crew (Nuri Solberg, +0.10), stacked maximum is +0.20. The Industry tree placement grounds the skill in applied technical competence: a captain who knows how to process raw materials efficiently can recognize when a research output is undervalued.
**narrative hook**: Understanding how yield-per-process works in industrial contexts translates directly to reading whether a funded project is extracting full value from its resources.

---

### 1.7 Research Oversight

**id**: `research_oversight`
**display name**: Research Oversight
**tree**: Leadership
**tier**: 2 (specialization)
**prerequisite_id**: `diplomatic_relations`
**max_level**: 2
**bonus_type**: `research_risk_reduction`
**bonus_per_level**: 0.05
**description** (player-facing): "+5% project failure odds reduction per level at the Okafor Institute"
**magnitude rationale**: SA-A1 range is 0.05-0.15. At `bonus_per_level = 0.05`, skill max is +0.10 at level 2. Combined with crew (Nuri Solberg, +0.10), stacked maximum is +0.20. The Leadership tree placement reflects institutional navigation skill: a captain with strong diplomatic relationships knows how to manage research institutions and reduce the odds of scope failure.
**narrative hook**: Failure in funded research is usually an institutional problem, not a science problem. Knowing how to apply the right pressure at the right point keeps projects on track.

---

## 2. Bonus-Naming Convention Table

Columns: bonus_type, description, skill level-1 magnitude, range (from SA-A1 section 1), consuming view file(s), consuming SA sprint(s), source read pattern.

Consumer read pattern for all "both" rows: `crew_roster.get_bonus("bonus_type") + progression.get_bonus("bonus_type")` per SA-A1 Decision 4, matching the established `cargo_bonus` / `fuel_efficiency_bonus` stacking convention (e.g., `views/mining_view.py:417`, `models/ship.py:259-265`). Each "both" row notes the crew name and skill ID that contribute.

| bonus_type | Description | Skill level-1 magnitude | SA-A1 range | Consuming view file(s) | Consuming sprint(s) | Source |
|---|---|---|---|---|---|---|
| `auction_lot_appraisal_bonus` | Post-auction valuation accuracy improvement | 0.05 | 0.05-0.15 | `spacegame/views/auction_view.py` (SA-B3) | SA-B3, SA-B4 | both (Sable Trent + lot_appraiser) |
| `coalition_sway_bonus` | Delegate persuasion modifier in Politics disputes | 0.10 | 0.10-0.25 | `spacegame/views/politics_view.py` (SA-P3), `spacegame/views/congress_view.py` (SA-P4) | SA-P3, SA-P4 | both (Desta Coll + coalition_sway) |
| `coalition_size_bonus` | Max delegates pre-committable per dispute (floored to integer) | 0.5 | +1 to +2 | `spacegame/views/politics_view.py` (SA-P3), `spacegame/views/congress_view.py` (SA-P4) | SA-P3, SA-P4 | both (Desta Coll + delegate_reach) |
| `arbitration_neutrality_bonus` | Partial-win odds shift in mediation resolution | 0.10 | 0.10-0.20 | `spacegame/views/mediation_view.py` (SA-P5) | SA-P5 | both (Cass Weller + mediation_instinct) |
| `speculator_premium_reduction` | Spread reduction on futures contract entry | 0.05 | 0.05-0.15 | `spacegame/views/financial_exchange_view.py` (SA-F2) | SA-F2, SA-F3 | both (Brix Tano + spread_trader) |
| `research_yield_bonus` | Increased project return at Okafor Institute | 0.05 | 0.05-0.15 | `spacegame/views/okafor_view.py` (SA-R1) | SA-R1, SA-R2 | both (Nuri Solberg + research_yield) |
| `research_risk_reduction` | Reduced project failure odds at Okafor Institute | 0.05 | 0.05-0.15 | `spacegame/views/okafor_view.py` (SA-R1) | SA-R1, SA-R2 | both (Nuri Solberg + research_oversight) |

These seven bonus_type strings map 1-to-1 with the seven "both"-source rows in `sa_crew_design.md` section 2. The three crew-only binary bonus_type strings from SA-A1 (`auction_bid_visibility`, `arbitration_dispute_intel`, `futures_intel`) are NOT in this table; they have no skill node in v1 per section 9 Decision 1 and AC 3 of this sprint.

---

## 3. Collision Check

Each new skill ID and bonus_type string is listed below with explicit pass/intentional-share status. Every ID in `create_default_skills()` (lines 384-1265, `spacegame/models/progression.py`) and every `bonus_type` in `data/crew/crew_members.json` was checked. No IDs in `_SKILL_MIGRATION_MAP` (lines 71-156 of `progression.py`) collide with the new IDs.

### 3.1 Skill IDs

| New ID | Status | Closest near-miss | Notes |
|---|---|---|---|
| `lot_appraiser` | PASS (new, no collision) | none | No existing skill ID contains "appraiser" |
| `coalition_sway` | PASS (new, no collision) | none | No existing skill ID starts with "coalition" |
| `delegate_reach` | PASS (new, no collision) | none | No existing skill ID contains "delegate" |
| `mediation_instinct` | PASS (new, no collision) | none | No existing skill ID starts with "mediation" |
| `spread_trader` | PASS (new, no collision) | none | No existing skill ID contains "spread" or "trader" |
| `research_yield` | PASS (new, no collision) | `refining_yield_bonus` (bonus_type on existing skill `forge_mastery`) | Skill ID `research_yield` and bonus_type `refining_yield_bonus` are distinct strings in distinct fields. Note: `research_yield` (new skill ID) and `research_yield_bonus` (new bonus_type) are different strings in different fields; no functional conflict. |
| `research_oversight` | PASS (new, no collision) | none | No existing skill ID starts with "research" |

Prefix substring check for `research_*` IDs: `research_yield` and `research_oversight` share the `research_` prefix with each other (both new; no functional conflict). No existing skill IDs share this prefix.

### 3.2 Bonus Type Strings

| New bonus_type | Status | Closest near-miss | Notes |
|---|---|---|---|
| `auction_lot_appraisal_bonus` | INTENTIONAL SHARED (crew + skill) | `auction_bid_visibility` (crew-only; distinct string) | Present in `data/crew/crew_members.json` (Sable Trent). Shared by design per SA-A1 Decision 4. Not in `progression.py` today; SA-C2 adds it. |
| `coalition_sway_bonus` | INTENTIONAL SHARED (crew + skill) | `coalition_size_bonus` (also new; distinct string) | Present in `data/crew/crew_members.json` (Desta Coll). Shared by design. Not in `progression.py` today. |
| `coalition_size_bonus` | INTENTIONAL SHARED (crew + skill) | `coalition_sway_bonus` (also new; distinct string) | Present in `data/crew/crew_members.json` (Desta Coll). Shared by design. Not in `progression.py` today. |
| `arbitration_neutrality_bonus` | INTENTIONAL SHARED (crew + skill) | `arbitration_dispute_intel` (crew-only; distinct string) | Present in `data/crew/crew_members.json` (Cass Weller). Shared by design. Not in `progression.py` today. |
| `speculator_premium_reduction` | INTENTIONAL SHARED (crew + skill) | `futures_intel` (crew-only; distinct string) | Present in `data/crew/crew_members.json` (Brix Tano). Shared by design. Not in `progression.py` today. |
| `research_yield_bonus` | INTENTIONAL SHARED (crew + skill) | `refining_yield_bonus` (existing skill bonus_type on `forge_mastery`; prefix is `refining_`, not `research_`) | Present in `data/crew/crew_members.json` (Nuri Solberg). Shared by design. `refining_yield_bonus` and `research_yield_bonus` are distinct strings; no collision. Not in `progression.py` today. |
| `research_risk_reduction` | INTENTIONAL SHARED (crew + skill) | none | Present in `data/crew/crew_members.json` (Nuri Solberg). Shared by design. Not in `progression.py` today. |

The three crew-only binary bonus_type strings (`auction_bid_visibility`, `arbitration_dispute_intel`, `futures_intel`) are present in `data/crew/crew_members.json` and are NOT shared with any new skill. They retain their crew-only status per SA-A1 Decision 4 exception and AC 3 of this sprint.

---

## 4. Tree-Population Analysis

Per-tree skill counts confirmed from `tree=SkillTreeType.<NAME>` occurrences in `spacegame/models/progression.py` (`create_default_skills()`, lines 384-1265). The SA-C1 plan estimated Commerce 12, Combat 17, Exploration ~10, Leadership 11, Social 13, Industry 12. Actual confirmed counts differ for Combat (22, not 17) and Exploration (12, not ~10). The discrepancy for Combat is pre-existing; SA-C1 adds no Combat skills.

| Tree | Pre-SA-C2 count | SA-C1 additions | Post-SA-C2 count | New skills |
|---|---|---|---|---|
| Commerce | 12 | 2 | 14 | `lot_appraiser`, `spread_trader` |
| Combat | 22 | 0 | 22 | none |
| Exploration | 12 | 0 | 12 | none |
| Leadership | 11 | 2 | 13 | `delegate_reach`, `research_oversight` |
| Social | 13 | 2 | 15 | `coalition_sway`, `mediation_instinct` |
| Industry | 12 | 1 | 13 | `research_yield` |
| **Total** | **82** | **7** | **89** | |

No new tree is introduced. Authority: `station_anchors.md` Decision 3.

Combat pre-SA-C2 flag: Combat already has 22 nodes, above the 18-node rendering guidance threshold in the SA-C1 plan. This is a pre-existing condition; SA-C1 adds no Combat skills. SA-C2 implementers should verify `_compute_detail_positions` in `skill_tree_view.py` renders Combat at 22 nodes without crowding at the standard six resolutions. No post-SA-C2 tree count exceeds 22.

Post-SA-C2 crowding analysis: Social reaches 15 and Commerce reaches 14. Neither approaches the 18-node threshold. No mitigation required.

---

## 5. Capstone Analysis

All seven new skills are Tier 2 specialization nodes. None is Tier 3.

**No new capstones in v1.**

Rationale: An S-sized design sprint is not the place for identity-defining capstones. Capstones earn their place by the depth of a system; Phase II Politics may justify a future "Coalition Builder" capstone during the SA-X cohesion pass, not here. Keeping all seven at Tier 2 also keeps `_CAPSTONE_IDS` in `spacegame/views/skill_tree_view.py` (lines 83-95) unchanged for SA-C2.

Current `_CAPSTONE_IDS` (unchanged by SA-C2):
`insurance`, `juggernaut_capstone`, `sentinel_capstone`, `ghost_capstone`, `volley_commander`, `emergency_reserves`, `anomaly_sense`, `legend_of_the_expanse`, `peacemaker`, `ore_sense`, `material_science`

SA-C2 does NOT add any entry to `_CAPSTONE_IDS`.

Future-arc note: if SA-X cohesion identifies "Coalition Builder" (Politics advocate identity), "Market Theorist" (Bidding/Futures identity), or "Institute Patron" (Research identity) as warranted by system depth, those are Phase VI considerations, out of scope for SA-C1 and SA-C2.

---

## 6. Save-Migration Analysis

No migration entries required.

`from_dict()` in `spacegame/models/progression.py` (lines 351-368) iterates over `skills_data.items()` from the saved dict. If a skill ID is absent from the saved dict, it is not iterated; the `SkillNode` for that ID was already re-instantiated by `create_default_skills()` via `__post_init__` with `current_level = 0`. The result: pre-SA-C2 saves load without crashing; new skills default to level 0 as expected.

The `_SKILL_MIGRATION_MAP` (lines 71-156) maps old 9-tree skill IDs to new 6-tree equivalents. None of the seven new IDs (`lot_appraiser`, `coalition_sway`, `delegate_reach`, `mediation_instinct`, `spread_trader`, `research_yield`, `research_oversight`) appear in the migration map. No collision. No new entries are needed because these are net-new IDs, not renamed or split existing skills.

Post-SA-C2 round-trip behavior: saves created after SA-C2 that include leveled new skills serialize correctly via `to_dict()` (stores `current_level` by ID) and restore correctly via `from_dict()` (maps ID to the new `SkillNode` in `create_default_skills()`). No version field changes needed.

Reminder for SA-C2: if any of the seven IDs changes during implementation (e.g., renamed during review), a `_SKILL_MIGRATION_MAP` entry will be required at that time. Flag any such rename explicitly in the SA-C2 commit message and this document should be updated.

---

## 7. Cross-Reference Matrix

| New skill | Bonus type | Consuming SA sprint(s) | Consuming view file(s) | Integration note |
|---|---|---|---|---|
| `lot_appraiser` | `auction_lot_appraisal_bonus` | SA-B3, SA-B4 | `spacegame/views/auction_view.py` | Summed with Sable Trent crew value in post-win valuation accuracy display |
| `coalition_sway` | `coalition_sway_bonus` | SA-P3, SA-P4 | `spacegame/views/politics_view.py`, `spacegame/views/congress_view.py` | Summed with Desta Coll crew value when computing delegate persuasion success threshold |
| `delegate_reach` | `coalition_size_bonus` | SA-P3, SA-P4 | `spacegame/views/politics_view.py`, `spacegame/views/congress_view.py` | Summed with Desta Coll crew value; consumer floors total to integer for max pre-committable delegate count |
| `mediation_instinct` | `arbitration_neutrality_bonus` | SA-P5 | `spacegame/views/mediation_view.py` | Summed with Cass Weller crew value in partial-win probability calculation |
| `spread_trader` | `speculator_premium_reduction` | SA-F2, SA-F3 | `spacegame/views/financial_exchange_view.py` | Summed with Brix Tano crew value; applied as spread reduction on futures contract entry cost |
| `research_yield` | `research_yield_bonus` | SA-R1, SA-R2 | `spacegame/views/okafor_view.py` | Summed with Nuri Solberg crew value when computing project completion payout |
| `research_oversight` | `research_risk_reduction` | SA-R1, SA-R2 | `spacegame/views/okafor_view.py` | Summed with Nuri Solberg crew value; subtracted from project failure probability |

---

## 8. Handoff Checklist for SA-C2

SA-C2 produces the following artifacts, using this document as specification. Items are numbered for reference.

1. **Seven new `SkillNode` entries in `create_default_skills()`** in `spacegame/models/progression.py`. Each entry uses the `id`, `name`, `description`, `tree`, `max_level`, `prerequisite_id`, `bonus_type`, and `bonus_per_level` values from section 1 of this document, verbatim.

2. **Per-skill bonus-stack tests** in `tests/test_models/test_progression.py`. For each new skill:
   - Test that `progression.get_bonus("bonus_type")` returns 0.0 when the skill is at level 0.
   - Test that it returns `bonus_per_level * 1` when the skill is at level 1.
   - Test that it returns `bonus_per_level * 2` when the skill is at level 2.
   - Test that a `max_level = 2` skill cannot be raised to level 3.
   - Test the prerequisite gate: leveling the new skill fails when the prerequisite skill is at level 0.

3. **Save round-trip tests**: confirm pre-SA-C2 save fixtures (with new skill IDs absent) load via `from_dict()` and produce `current_level = 0` for all seven new skills. Confirm a post-SA-C2 save with leveled new skills round-trips correctly.

4. **No view code changes expected**: `_compute_detail_positions` in `skill_tree_view.py` auto-arranges by prerequisite depth; net-new mid-tier skills lay out without edits. No additions to `_CAPSTONE_IDS`. SA-C2 performs a layout regression check at the six standard resolutions; if crowding appears in Commerce, Social, or Leadership, report via `PHASE_BLOCKED` rather than silently adjusting the layout algorithm.

5. **No new `_SKILL_MIGRATION_MAP` entries**: these are net-new IDs. If any ID changes during SA-C2 implementation, a migration entry is required and this document should be updated.

6. **Writing Bible compliance on descriptions**: the seven player-facing description strings from section 1 may be copied verbatim into `create_default_skills()`. They have been verified against em-dash, banned phrase, and parallel-negation patterns.

---

## 9. Decisions Locked

### Decision 1: Binary intel bonus_type strings remain crew-only in v1

The three binary intel bonus_type strings (`auction_bid_visibility`, `arbitration_dispute_intel`, `futures_intel`) have no skill node in v1. They remain crew-only per SA-A1 Decision 4.

Rationale: Introducing skill nodes for binary gates would deviate from the SA-A1 design without a locked consumer. The binary bonuses function as gate booleans (value >= 1.0 triggers UI element), not additive modifiers. A skill node that gives +0.5 per level would require level 2 to trigger the gate, which is a different investment calculus from the established additive pattern. If a skill-tree path to these reveals becomes warranted (Phase VI cohesion), it should be added at that time with a locked consumer view in scope.

### Decision 2: Tree placement in existing trees only

All seven skills placed in existing trees: Commerce (+2), Social (+2), Leadership (+2), Industry (+1). No new tree introduced. Authority: `station_anchors.md` Decision 3.

Specific placements per SA-C1 locked recommendations:
- `lot_appraiser`: Commerce Tier 2, prereq `market_eye`
- `coalition_sway`: Social Tier 2, prereq `silver_tongue`
- `delegate_reach`: Leadership Tier 2, prereq `give_the_word`
- `mediation_instinct`: Social Tier 2, prereq `empathic_read`
- `spread_trader`: Commerce Tier 2, prereq `tariff_negotiation`
- `research_yield`: Industry Tier 2, prereq `efficient_refining`
- `research_oversight`: Leadership Tier 2, prereq `diplomatic_relations`

Trade-off considered: Placing `research_yield` in Industry (via `efficient_refining`) rather than Leadership (via `diplomatic_relations`) separates the two research bonuses across trees, which encourages players to invest in both trees for full research depth rather than double-dipping in Leadership. The split is intentional.

### Decision 3: No new capstones in v1

All seven new skills are Tier 2. `_CAPSTONE_IDS` in `skill_tree_view.py` is unchanged for SA-C2. Future capstone considerations deferred to SA-X cohesion phase.

### Decision 4: max_level = 2 for all seven

`max_level = 2` for all seven new skills. `max_level = 1` would make the skill a single-point gateway; `max_level = 3` is reserved for high-frequency utility skills (`cargo_mastery`, `fuel_efficiency`) where the effect is felt every session. All seven SA-C1 skills gate on anchor-system venues, not general trading mechanics, so the two-point investment cap is correct.

### Decision 5: Naming avoids `negotiator` and `master_negotiator` collisions

None of the seven new skill IDs or display names conflicts with `negotiator` (Commerce Tier 1, line 385 of `progression.py`) or `master_negotiator` (Social Tier 2, line 1049). All seven names are distinct at both ID and display-string level: Lot Appraiser, Coalition Sway, Delegate Reach, Mediation Instinct, Spread Trader, Research Yield, Research Oversight.

Note: "Coalition" appears in the crew role label "coalition builder" (Desta Coll in `data/crew/crew_members.json`). Skill display names and crew role labels are in separate namespaces; no functional conflict exists.

### Decision 6: bonus_per_level values from SA-A1 range, conservative selection

Each skill's `bonus_per_level` is the lower end of the SA-A1 range for the matching bonus type. Values: 0.05 for `auction_lot_appraisal_bonus`, `speculator_premium_reduction`, `research_yield_bonus`, `research_risk_reduction`; 0.10 for `coalition_sway_bonus` and `arbitration_neutrality_bonus`; 0.5 for `coalition_size_bonus` (integer-floored type, structured to match range upper bound when combined with crew).

Conservative selection keeps the skill alone within the SA-A1 range, reserving stronger combined effect for players who invest in both crew hire and skill leveling.

### Decision 7: Save migration not required

Net-new IDs. No `_SKILL_MIGRATION_MAP` entries needed. Old saves load correctly with new skills defaulting to level 0. New saves round-trip correctly. Full analysis in section 6.

### Decision 8: View code unchanged for SA-C2

No edits to `skill_tree_view.py` expected beyond the layout regression check at six standard resolutions. `_compute_detail_positions` auto-arranges by prerequisite depth. `_CAPSTONE_IDS` unchanged.
