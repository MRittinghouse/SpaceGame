# SA Crew Specialization Design

**Sprint**: SA-A1
**Status**: final
**Implements for**: SA-A2 (crew template authoring), SA-B3, SA-B4, SA-P3, SA-P4, SA-P5, SA-R1, SA-R2, SA-F2, SA-F3

This document is the single source of truth for the five crew specializations introduced in Phase A of the Station Anchors arc. SA-A2 reads this document to implement JSON template entries, voice sheets, and banter. Downstream SA sprints read section 2 (bonus-naming convention table) when their views call `get_bonus(...)`.

---

## 1. Specialization Roster

One block per specialization. Each block names the bonus_type strings (locked for SA-A2 to implement), a home_system_id and faction_id candidate for the JSON template entry, a hireability gating note for SA-A2 to resolve, and a 3-5 sentence persona seed for voice-sheet authoring.

---

### 1.1 Auction Reader

**Name**: Sable Trent
**Role label** (for `data/crew/crew_members.json#role`): `auction reader`
**Target anchor system(s)**: Bidding (Stellaris Auction House)
**Consuming sprint(s)**: SA-A2 (authoring), SA-B3, SA-B4

**home_system_id candidate**: `stellaris_port`
**faction_id candidate**: `commerce_guild`

**Hireability gating note**: Available at Stellaris Port after the player first enters the Stellaris Auction House. No faction reputation gate in v1. SA-B3 may add a Commerce Guild standing requirement during implementation.

**Bonus types** (level 1, flat, non-companion):
- `auction_bid_visibility`: 1.0 (binary: reveals one rival's bid ceiling per auction round when value >= 1.0)
- `auction_lot_appraisal_bonus`: 0.10 (post-win valuation accuracy improvement; range 0.05-0.15)

**Persona seed**: Sable spent six years logging bids for a Commerce Guild auction desk before she decided the better money was in reading the room from the floor. She has a cataloguer's eye for tells: the pause before a counter, the too-quick raise, the bluff that costs two rounds too early. She does not explain her reads. She shows you the number she thinks the ceiling is, and she is right often enough that you stop questioning it.

---

### 1.2 Coalition Builder

**Name**: Desta Coll
**Role label**: `coalition builder`
**Target anchor system(s)**: Politics, advocate role (Mayors' Council Chamber, Alliance Congress Hall)
**Consuming sprint(s)**: SA-A2 (authoring), SA-P3, SA-P4

**home_system_id candidate**: `havens_rest`
**faction_id candidate**: `frontier_alliance`

**Hireability gating note**: Available at Haven's Rest after the player first visits the Alliance Congress Hall. Requires Frontier Alliance standing of at least Neutral. SA-P4 may tighten the gate during implementation.

**Bonus types** (level 1, flat, non-companion):
- `coalition_sway_bonus`: 0.15 (delegate persuasion modifier; range 0.10-0.25)
- `coalition_size_bonus`: 1.0 (adds to maximum delegates pre-committable per dispute; +1 to +2 range)

**Persona seed**: Desta spent fifteen years coordinating between frontier settlements that had every reason not to trust each other and very little time to argue. She does not persuade with speeches. She counts commitments, maps pressure points, and tells you exactly how many delegates you can move before the room starts pushing back. She is useful before the vote, not during it.

---

### 1.3 Arbiter

**Name**: Cass Weller
**Role label**: `arbiter`
**Target anchor system(s)**: Politics, neutral role / gray-market mediation (SA-P5 Wreckers' Guild arbitration venue)
**Consuming sprint(s)**: SA-A2 (authoring), SA-P5

**home_system_id candidate**: `crimson_reach`
**faction_id candidate**: `""` (independent, no faction affiliation)

**Hireability gating note**: Available at Crimson Reach without a faction gate. SA-P5 may add a sub-reputation requirement (Wreckers' Guild standing) during implementation.

**Bonus types** (level 1, flat, non-companion):
- `arbitration_neutrality_bonus`: 0.15 (partial-win odds shift in mediation resolution; range 0.10-0.20)
- `arbitration_dispute_intel`: 1.0 (binary: reveals one hidden delegate position per dispute when value >= 1.0)

**Persona seed**: Cass arbitrated gray-market disputes on the Reach for eight years before the Guild gave her a semi-official role no one bothered to name. She has no interest in who wins. She has interest in whether the outcome holds. Her value is in the partial-win: she knows how to structure a deal that leaves both parties with enough that neither wants to restart the fight in three months.

---

### 1.4 Speculator

**Name**: Brix Tano
**Role label**: `speculator`
**Target anchor system(s)**: Financial Exchange (Meridian, Nexus Prime)
**Consuming sprint(s)**: SA-A2 (authoring), SA-F2, SA-F3

**home_system_id candidate**: `nexus_prime`
**faction_id candidate**: `commerce_guild`

**Hireability gating note**: Available at Nexus Prime. SA-F2 may add a gate tied to initial financial exchange engagement during implementation.

**Bonus types** (level 1, flat, non-companion):
- `futures_intel`: 1.0 (binary: reveals one futures contract probability band per session when value >= 1.0)
- `speculator_premium_reduction`: 0.10 (spread reduction on futures contract entry; range 0.05-0.15)

**Persona seed**: Brix ran contract desks at Nexus Prime for eleven years and left when the numbers stopped surprising him. He does not predict the market. He narrows the range of what is possible and tells you which band the contract is most likely to land in. He is comfortable being wrong inside the band. He is not comfortable being wrong outside it.

---

### 1.5 Patron

**Name**: Nuri Solberg
**Role label**: `research patron`
**Target anchor system(s)**: Research Patronage (Okafor Institute, Axiom Labs)
**Consuming sprint(s)**: SA-A2 (authoring), SA-R1, SA-R2

**home_system_id candidate**: `axiom_labs`
**faction_id candidate**: `science_collective`

**Hireability gating note**: Available at Axiom Labs after first contact with the Okafor Institute. The specific flag name is authored by SA-R1.

**Bonus types** (level 1, flat, non-companion):
- `research_yield_bonus`: 0.10 (project return increase at Okafor Institute; range 0.05-0.15)
- `research_risk_reduction`: 0.10 (project failure odds reduction at Okafor Institute; range 0.05-0.15)

**Persona seed**: Nuri spent two decades as a research administrator at the Collective before moving to independent patronage. She knows how to read a project proposal: which methodology is under-resourced, which risk estimate is padded to make the sponsor comfortable, and which researcher is the one the team is actually built around. She does not care about prestige. She cares about whether the project produces something that holds up.

---

## 2. Bonus-Naming Convention Table

All new `bonus_type` strings introduced by this design. Collision check against `spacegame/models/progression.py` and `data/crew/crew_members.json` is documented inline.

| bonus_type | Description | Magnitude (level 1) | Range | Consuming view file(s) | Source read from |
|---|---|---|---|---|---|
| `auction_bid_visibility` | Reveals one rival's bid ceiling per auction round | 1.0 (binary) | 0 or 1 | `spacegame/views/auction_view.py` (SA-B3, does not exist yet) | crew only (binary gate; not a skill-tree additive modifier in SA-C1/C2 v1) |
| `auction_lot_appraisal_bonus` | Post-win valuation accuracy improvement | 0.10 | 0.05-0.15 | `spacegame/views/auction_view.py` (SA-B3, does not exist yet) | both (crew + skill; SA-C1 may introduce a matching Commerce skill node) |
| `coalition_sway_bonus` | Delegate persuasion modifier in Politics disputes | 0.15 | 0.10-0.25 | `spacegame/views/politics_view.py` (SA-P3, does not exist yet), `spacegame/views/congress_view.py` (SA-P4, does not exist yet) | both |
| `coalition_size_bonus` | Adds to max delegates pre-committable per dispute | 1.0 (+1) | +1 to +2 | `spacegame/views/politics_view.py` (SA-P3), `spacegame/views/congress_view.py` (SA-P4) | both |
| `arbitration_neutrality_bonus` | Partial-win odds shift in mediation resolution | 0.15 | 0.10-0.20 | `spacegame/views/mediation_view.py` (SA-P5, does not exist yet) | both |
| `arbitration_dispute_intel` | Reveals one hidden delegate position per dispute | 1.0 (binary) | 0 or 1 | `spacegame/views/mediation_view.py` (SA-P5, does not exist yet) | crew only (binary gate) |
| `futures_intel` | Reveals one futures contract probability band per session | 1.0 (binary) | 0 or 1 | `spacegame/views/financial_exchange_view.py` (SA-F2, does not exist yet) | crew only (binary gate) |
| `speculator_premium_reduction` | Spread reduction on futures contract entry | 0.10 | 0.05-0.15 | `spacegame/views/financial_exchange_view.py` (SA-F2, does not exist yet) | both |
| `research_yield_bonus` | Increased project return at Okafor Institute | 0.10 | 0.05-0.15 | `spacegame/views/okafor_view.py` (SA-R1, does not exist yet) | both |
| `research_risk_reduction` | Reduced project failure odds at Okafor Institute | 0.10 | 0.05-0.15 | `spacegame/views/okafor_view.py` (SA-R1, does not exist yet) | both |

### Collision Check

All existing `bonus_type` strings in `spacegame/models/progression.py` and `data/crew/crew_members.json` were reviewed. No collisions found. Specific strings checked for prefix ambiguity:

- `salvage_yield` exists in both sources. None of the new strings share this prefix. `research_yield_bonus` and `salvage_yield` are distinct; `research_yield_bonus` and `refining_yield_bonus` are distinct.
- `research_yield_bonus`: no existing match.
- `research_risk_reduction`: no existing match.
- `coalition_sway_bonus`, `coalition_size_bonus`: no existing match.
- `arbitration_neutrality_bonus`, `arbitration_dispute_intel`: no existing match.
- `futures_intel`, `speculator_premium_reduction`: no existing match.
- `auction_bid_visibility`, `auction_lot_appraisal_bonus`: no existing match.

---

## 3. Cross-Reference Matrix

One row per specialization. Consuming view file paths are forward-looking; none of the listed views exist yet.

| Specialization | Consuming SA sprint(s) | Consuming view file(s) | Integration mechanism |
|---|---|---|---|
| Auction Reader (Sable Trent) | SA-B3, SA-B4 | `spacegame/views/auction_view.py` (authored in SA-B3) | `auction_bid_visibility` check (>= 1.0) gates the "reveal rival ceiling" button per auction round; `auction_lot_appraisal_bonus` adjusts the post-win valuation accuracy displayed to the player. |
| Coalition Builder (Desta Coll) | SA-P3, SA-P4 | `spacegame/views/politics_view.py` (SA-P3), `spacegame/views/congress_view.py` (SA-P4) | `coalition_sway_bonus` is summed from crew and skill when computing delegate persuasion success threshold; `coalition_size_bonus` adds to the maximum pre-committable delegates before a vote. |
| Arbiter (Cass Weller) | SA-P5 | `spacegame/views/mediation_view.py` (SA-P5) | `arbitration_neutrality_bonus` shifts partial-win probability in the mediation resolution calculation; `arbitration_dispute_intel` check (>= 1.0) gates the "reveal hidden position" UI element per dispute. |
| Speculator (Brix Tano) | SA-F2, SA-F3 | `spacegame/views/financial_exchange_view.py` (SA-F2) | `futures_intel` check (>= 1.0) gates the "reveal probability band" display on a futures contract listing; `speculator_premium_reduction` reduces the spread applied at contract entry, visible in the entry cost summary. |
| Patron (Nuri Solberg) | SA-R1, SA-R2 | `spacegame/views/okafor_view.py` (SA-R1) | `research_yield_bonus` is summed when computing project completion payout; `research_risk_reduction` is subtracted from project failure probability shown on the funding confirmation screen. |

---

## 4. Decisions Locked

### Decision 1: Specialization set scope

Five specializations, covering all four Phase A-named anchor systems plus the Politics arbitration variant. Set: Auction Reader (Bidding), Coalition Builder (Politics advocate), Arbiter (Politics neutral / SA-P5 gray-market mediation), Speculator (Financial), Patron (Research).

Rationale: The strategic vision (`requirements/station_anchors.md` Phase A header and Phase II through V integration commitments) names exactly these four anchor systems and distinguishes neutral Politics crew from advocate crew. Phase A names "Politics crew can sway delegates" as the advocate function; Phase II names the arbitration venue (SA-P5) as a separate mechanic requiring neutral crew. Five is the minimum that lets every Phase II-V system find a crew slot without forcing a single crew NPC to double-role across incompatible mechanics. Six would push SA-A2 outside its M-size budget without a locked consumer.

### Decision 2: Naming scheme to avoid collisions

Use Auction Reader, Coalition Builder, Arbiter, Speculator, Patron as the five specialization labels. The label "Negotiator" is not used for any specialization.

Rationale: `spacegame/models/progression.py` defines a `negotiator` Commerce skill node (line 385) and a `master_negotiator` capstone (line 1049). `data/crew/crew_members.json` gives Leah Chen the role label `negotiator` with `buy_price_reduction` and `sell_price_bonus` bonuses unrelated to bidding. Reusing "Negotiator" for a Bidding-specialist crew would create three distinct systems sharing one label with three different bonus_type sets. "Auction Reader" makes the bidding-specific function clear at the hire screen without overloading existing terminology. "Arbiter" is distinct from the SA-P5 venue label ("gray-market mediation") while remaining readable.

### Decision 3: Extend existing templates vs. author net-new

Net-new templates for all five specializations.

Rationale: The closest existing matches are Leah Chen (negotiator role; bonuses `buy_price_reduction` and `sell_price_bonus`, neither of which maps to bidding mechanics) and Adisa Nyong'o (diplomatic aide; bonuses `reputation_gain_bonus` and `diplomatic_rep_bonus`, neither of which maps to a Politics dispute UI). Extending either would require rewriting their identities and destabilizing the assumption that a recruited crew member's bonuses are stable across saves. Net-new templates give SA-A2 freedom on faction, home system, and voice without touching existing companion or non-companion semantics.

### Decision 4: Bonus integration pattern

Both. Each new `bonus_type` string is readable via both `crew_roster.get_bonus(...)` and `progression.get_bonus(...)` in the consuming view; values sum. SA-C1/SA-C2 will introduce matching skill nodes that emit the same strings where noted in section 2.

Exception: the three binary intel strings (`auction_bid_visibility`, `arbitration_dispute_intel`, `futures_intel`) are crew-only for v1. These function as gate booleans (value >= 1.0 triggers UI element), not additive modifiers. SA-C1 may introduce matching skill nodes if a skill-tree path to these reveals is warranted. If that happens, summing from both sources is still correct because any nonzero value satisfies the gate.

Rationale: This is the project's established pattern. `cargo_bonus`, `fuel_efficiency_bonus`, `salvage_yield`, and `extra_scan_charges` are all read from both sources and summed in their consuming views (e.g., `views/mining_view.py:417`, `models/ship.py:259-265`). Using crew-only for all SA specializations would fork anchor bonus aggregation off the standard pattern and produce surprises during SA-C1/C2 skill implementation.

### Decision 5: Companion vs. non-companion semantics

All five new specialist crew are non-companions: `is_companion: false`, `max_level: 1`, single-tier flat abilities. XP gain and loyalty multiplier scaling do not apply to non-companions.

Rationale: `spacegame/models/crew.py` lines 286-288 apply loyalty-multiplier scaling (1.25 times at Loyal, 1.5 times at Devoted) only to companions. Companions are story-bound (Elena, Marcus, Priya, Tomas) with full crew-quest arcs. The SA arc specialists are journeyman-tier hires keyed to anchor systems. Non-companion status keeps companion identity intact and constrains SA-A2 to a clean implementation envelope: quest authoring, loyalty curve tuning, and per-level scaling tables are all out of scope.

---

## 5. Save-Migration Note

No save migration required.

The `CrewRoster.get_state()` and `load_state()` chain (lines 637-679 in `spacegame/models/crew.py`) serializes the recruited crew list, per-member state, and `bonus_abilities`. New `bonus_type` strings (`auction_bid_visibility`, `auction_lot_appraisal_bonus`, etc.) are values inside the existing `abilities` list on each crew template entry. They flow through the serialization chain unchanged because they occupy the existing `bonus_type` field within the existing `abilities` list structure.

No new top-level fields are added to `CrewRoster` or to individual crew member state. No migration logic is required in `load_state()`. Old saves (which contain none of the five new crew) load without change. Saves that include a recruited specialist carry the specialist's bonus_type values in the standard abilities structure; loading those saves requires no version check.

SA-A2 should confirm this assumption holds after writing the JSON template entries. If SA-A2 introduces any new top-level field on individual crew member state, it must add `data.get("new_field", default)` handling in `load_state()` per the project's save-migration convention.

---

## 6. Hand-off Checklist for SA-A2

SA-A2 produces the following artifacts, referencing this document as specification:

- Five JSON template entries in `data/crew/crew_members.json`, one per specialization. Each entry requires: `id` (snake_case), `name`, `role` (matching section 1 role labels), `faction_id`, `home_system_id`, `description`, `portrait_color`, `base_attributes`, `max_level: 1`, `xp_thresholds: [0]`, `is_companion: false`, `abilities` list with the bonus_type strings and magnitudes from section 1.
- Voice sheets for each of the five new specialist NPCs in `requirements/character_voices.md`, following the format established by the SA-PREP-1 voice sheets. Each sheet should be consistent with the persona seed in section 1 of this document.
- 3-5 ambient banter lines per specialist, suitable for use in the cockpit crew panel. Lines must pass Writing Bible compliance (no em-dashes, no banned phrases, voice consistent with persona seed).
- Integration tests in `tests/test_models/test_crew.py` covering: each bonus_type string resolves correctly via `crew_roster.get_bonus(...)` when the specialist is recruited; save/load round-trip preserves specialist crew state; `get_bonus` returns 0 when specialist is not recruited.
- Hireability gating implementation: confirm which flags or reputation thresholds gate each specialist's appearance in the hire screen, implementing the notes in section 1 or adjusting with documented rationale.
