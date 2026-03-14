# Flag Architecture — Act One

## Document Purpose

This is the **technical reference** for every dialogue flag in Act One. It maps when each flag is set, what it gates, and how flags depend on each other. Use this when implementing missions, dialogue trees, and conditional content.

**Ref**: `act_one_narrative.md` for story beats, `campaign_act_one.md` for mission structure

---

## Flag Naming Conventions

- All flags use `snake_case`
- Prefix patterns:
  - `met_<npc>` — first meeting with an NPC
  - `chose_<path>` — mutually exclusive player choice
  - `<npc>_recruited` / `<npc>_declined` / `<npc>_dismissed` — crew state
  - Verb-based: `helped_`, `delivered_`, `attended_`, `completed_`, `survived_`
- Boolean only — flags are True or absent (no integer or string flag values)
- Flags are permanent once set (no unsetting within a playthrough)

---

## Chapter 1: Arrival (Missions 01–03)

### Mission 01: Bill of Landing
No new flags. This mission uses the existing `trade_permits` system (not dialogue flags).

### Mission 02: Iron Ore Delivery
No new flags. Completion tracked by mission status, not flags.

### Mission 03: The Navigator

| Flag | Set When | Used By |
|------|----------|---------|
| `talked_to_elena_cantina` | Player initiates conversation with Elena | M03 dialogue branching, `elena_offered` prereq |
| `elena_gave_trading_tips` | Elena shares trading advice | Optional — flavor tracking |

**Crew recruitment flags** (see Crew section below):
`elena_offered`, `elena_recruited`, `elena_declined`

---

## Chapter 2: Making Connections (Missions 04–07)

### Mission 04: Union Territory

| Flag | Set When | Used By |
|------|----------|---------|
| `breakstone_permit_earned` | Player delivers food to commissary | Enables Breakstone trading |
| `met_hanna_voss` | First dialogue with Hanna Voss | M05+ dialogue availability, M13 optional reference |
| `talked_to_voss` | Optional extended dialogue with Voss | Flavor — richer M11/M13 dialogue if set |

### Mission 05: The Foreman's Son

| Flag | Set When | Used By |
|------|----------|---------|
| `met_marcus_jin` | First dialogue with Marcus | M12 optional beat, M13 `marcus_vouched`, crew recruitment prereq |
| `learned_father_story` | Marcus tells you about the air recycler report | M17 crew reflection, journal flavor |
| `completed_mining_tutorial` | Complete mining run with Marcus | Gameplay tracking — no narrative gate |

**Crew recruitment flags** (see Crew section below):
`marcus_fetch_accepted`, `marcus_fetch_completed`, `marcus_offered_position`, `marcus_recruited`, `marcus_declined`

### Mission 06: The Scholar's Errand

| Flag | Set When | Used By |
|------|----------|---------|
| `met_priya_osei` | First dialogue with Priya | M11 summit dialogue, M14 scanner upgrade, crew recruitment prereq |
| `escorted_priya_axiom` | Complete transport to Axiom Labs | M06 completion |
| `priya_apologized` | Player pushes back on clinical framing, Priya apologizes | Flavor — adjusts later Priya dialogue tone |
| `visited_axiom_labs` | Player explores Axiom Labs station | Optional — unlocks Okafor plaque discovery |

**Crew recruitment flags** (see Crew section below):
`priya_data_requested`, `priya_data_delivered`, `priya_discovery`, `priya_offered_position`, `priya_recruited`, `priya_declined`

### Mission 07: The Drifter's Deal

| Flag | Set When | Used By |
|------|----------|---------|
| `met_tomas_drifter` | First dialogue with Tomas | M10 optional reference, crew recruitment prereq |
| `accepted_drifter_deal` | Player agrees to gray-market trade | M07 completion path, `tomas_friendship` |
| `declined_drifter_deal` | Player refuses trade | Mutually exclusive with `accepted_drifter_deal` |
| `tomas_friendship` | Complete deal + positive outcome | Tomas recruitment prereq, richer M10+ dialogue |

**Crew recruitment flags** (see Crew section below):
`tomas_trade_completed`, `tomas_delivery_accepted`, `tomas_delivery_completed`, `tomas_offered_position`, `tomas_recruited`, `tomas_declined`

---

## Chapter 3: Undercurrents (Missions 08–11)

### Mission 08: Cargo Lost

| Flag | Set When | Used By |
|------|----------|---------|
| `encountered_distress_signal` | Forced encounter triggers during travel | M08 progression |
| `helped_freighter` | Player engages distress signal | `met_reva_sato` — Reva arrives after player helps |
| `ignored_distress` | Player bypasses distress signal | Mutually exclusive with `helped_freighter`; Reva met differently |
| `met_reva_sato` | First dialogue with Captain Reva Sato | M11 summit, M15 Guild path, M16 Guild path |
| `pirate_conspiracy_awareness` | Reva reveals coordinated attack pattern | M09 dialogue with Dex, general awareness gate |

### Mission 09: Whispers at the Bar

| Flag | Set When | Used By |
|------|----------|---------|
| `met_dex_halloran` | First dialogue with Dex at cantina | M10 prereq, M13+ references |
| `overheard_faction_argument` | Player witnesses Guild/Union debate | Flavor — M11 summit context |
| `accepted_dex_favor` | Player agrees to deliver data chip | M10 prereq |
| `declined_dex_favor` | Player refuses Dex's task | Mutually exclusive; alternate M10 path needed |
| `elena_pirate_insight` | Elena present + offers Guild perspective | Optional — requires `elena_recruited` |

### Mission 10: Crimson Run

| Flag | Set When | Used By |
|------|----------|---------|
| `delivered_dex_chip` | Data chip delivered to Malia | M10 completion |
| `met_malia_torres` | First dialogue with Malia Torres | M15+ Alliance path reference |
| `malia_pirate_intel` | Malia reveals scope of pirate operation | M11 summit knowledge, M13+ investigation |
| `visited_crimson_reach` | Player docks at Crimson Reach | Travel/exploration tracking |

### Mission 11: The Summit

| Flag | Set When | Used By |
|------|----------|---------|
| `attended_summit` | Player arrives at Axiom Labs for summit | M11 progression |
| `observed_guild_signal` | Social/Observation check — spot suspicious Guild behavior | M14+ conspiracy evidence, richer M15 briefing |
| `summit_deadlock` | Summit fails to reach agreement | M12+ — raises stakes, pirate attacks escalate |
| `faction_positions_known` | Player hears all four faction positions | M15 branching — informs faction choice |

---

## Chapter 4: Escalation (Missions 12–15)

### Mission 12: Under Fire

| Flag | Set When | Used By |
|------|----------|---------|
| `survived_pirate_attack` | Win forced combat encounter | M12 completion |
| `marcus_recognized_guild_hardware` | Marcus present + identifies Guild tech on pirate ship | Optional — requires `marcus_recruited`; adds conspiracy evidence |
| `combat_tutorial_complete` | Complete combat encounter | Gameplay tracking |

### Mission 13: The Favor Returned

| Flag | Set When | Used By |
|------|----------|---------|
| `met_oren_tak` | Find and talk to Oren in mining tunnels | M13 progression |
| `oren_revealed_base` | Oren trusts player + reveals base location | M14 prereq — provides coordinates |
| `explored_breakstone_tunnels` | Player navigates tunnels to find Oren | Gameplay tracking |
| `marcus_vouched` | Marcus vouches for player to Union contacts | Optional — requires `marcus_recruited` + `met_marcus_jin`; makes Oren easier to convince |

### Mission 14: The Ghost Signal

| Flag | Set When | Used By |
|------|----------|---------|
| `scanned_pirate_base` | Player locates base via scanning | M14 progression |
| `priya_modified_scanner` | Priya upgrades scanner for long-range scan | Optional — requires `priya_recruited`; enables easier/better scan |
| `pirate_base_confirmed` | Hard evidence of command center obtained | M15 prereq — essential evidence |
| `has_scan_data` | Player holds scan data | M15 briefing — data presented to factions |

### Mission 15: The Briefing

| Flag | Set When | Used By |
|------|----------|---------|
| `chose_guild_path` | Player allies with Commerce Guild | M16 path — military assault |
| `chose_union_path` | Player allies with Miners' Union | M16 path — blockade operation |
| `chose_collective_path` | Player allies with Science Collective | M16 path — data infiltration |
| `chose_alliance_path` | Player allies with Frontier Alliance | M16 path — stealth infiltration |
| `briefed_all_factions` | Player consults all faction leaders before choosing | Flavor — M16 richer dialogue |
| `m15_decision_made` | Any path chosen | M16 prereq |

**Mutually exclusive**: exactly ONE of `chose_guild_path`, `chose_union_path`, `chose_collective_path`, `chose_alliance_path` will be set.

---

## Chapter 5: The Revelation (Missions 16–17)

### Mission 16: The Operation

| Flag | Set When | Used By |
|------|----------|---------|
| `completed_operation` | Base operation succeeds | M17 prereq |
| `ledger_discovered` | Player discovers The Ledger conspiracy | M17 narrative, Act Two setup |
| `base_neutralized` | Pirate base destroyed/neutralized | M17 aftermath |

### Mission 17: New Horizons

| Flag | Set When | Used By |
|------|----------|---------|
| `act_one_complete` | Act One narrative concluded | Act Two gating, save state |
| `ledger_known` | Conspiracy knowledge established | Act Two persistent state |
| `new_horizons_unlocked` | Uncharted space markers revealed | Galaxy map expansion |

---

## Crew Recruitment Flags

All crew recruitment is optional. Each crew member follows the same flag pattern:

```
met_<npc>          → Required before any recruitment path
<npc>_<task>       → Side quest progression (varies per crew)
<npc>_recruited    → Player accepted crew member
<npc>_declined     → Player refused crew member
<npc>_dismissed    → Player dismissed crew member after recruiting
```

### Elena Reeves (Navigator)

```
talked_to_elena_cantina     ← M03
  └→ elena_offered          ← M03 dialogue
       ├→ elena_recruited   ← Player accepts
       └→ elena_declined    ← Player declines
            └→ (re-recruitable at Nexus Prime)

elena_recruited
  └→ elena_dismissed        ← Player dismisses later
       └→ (re-recruitable at Nexus Prime)
```

**Prerequisite chain**: `talked_to_elena_cantina` → `elena_offered` → `elena_recruited`
**Earliest available**: Mission 03
**Effort**: Low (single conversation)

### Marcus Jin (Engineer)

```
met_marcus_jin                  ← M05
  └→ marcus_fetch_accepted      ← Post-M05, return to Breakstone
       └→ marcus_fetch_completed ← Deliver salvage part
            └→ marcus_offered_position ← Marcus offers to join
                 ├→ marcus_recruited    ← Player accepts
                 └→ marcus_declined     ← Player declines
                      └→ (re-recruitable at Breakstone)
```

**Prerequisite chain**: `met_marcus_jin` → `marcus_fetch_accepted` → `marcus_fetch_completed` → `marcus_offered_position` → `marcus_recruited`
**Earliest available**: Post-Mission 05 (requires return trip to Breakstone)
**Effort**: Medium (fetch quest + two trips to Breakstone)

### Dr. Priya Osei (Scientist)

```
met_priya_osei                 ← M06
  └→ priya_data_requested      ← Post-M06, Priya contacts player
       └→ priya_data_delivered  ← Deliver scan data from Breakstone belt
            └→ priya_discovery  ← Priya discovers falsified safety data
                 └→ priya_offered_position ← Priya offers field research arrangement
                      ├→ priya_recruited    ← Player accepts
                      └→ priya_declined     ← Player declines
                           └→ (re-recruitable at Axiom Labs)
```

**Prerequisite chain**: `met_priya_osei` → `priya_data_requested` → `priya_data_delivered` → `priya_discovery` → `priya_offered_position` → `priya_recruited`
**Earliest available**: Post-Mission 06 (requires trip to Breakstone belt + return to Axiom Labs)
**Effort**: High (transport mission + data collection + return delivery)

### Tomas Drifter (Trader)

```
met_tomas_drifter                  ← M07
  └→ tomas_trade_completed         ← M07 gray-market deal
       └→ tomas_delivery_accepted  ← Post-M07, Tomas asks a favor
            └→ tomas_delivery_completed ← Deliver crate to Dustwell
                 └→ tomas_offered_position ← Tomas offers to join
                      ├→ tomas_recruited    ← Player accepts
                      └→ tomas_declined     ← Player declines
                           └→ (re-recruitable at Haven's Rest)
```

**Prerequisite chain**: `met_tomas_drifter` → `tomas_trade_completed` → `tomas_delivery_accepted` → `tomas_delivery_completed` → `tomas_offered_position` → `tomas_recruited`
**Earliest available**: Post-Mission 07
**Effort**: Low-Medium (participate in trade + one delivery run)

---

## Mutually Exclusive Flag Groups

These flags are guaranteed to never both be True:

| Group | Flags | Context |
|-------|-------|---------|
| Drifter deal | `accepted_drifter_deal` / `declined_drifter_deal` | M07 player choice |
| Distress response | `helped_freighter` / `ignored_distress` | M08 player choice |
| Dex favor | `accepted_dex_favor` / `declined_dex_favor` | M09 player choice |
| Faction path | `chose_guild_path` / `chose_union_path` / `chose_collective_path` / `chose_alliance_path` | M15 major choice |
| Per-crew state | `<npc>_recruited` / `<npc>_declined` | At any given decision point (note: `declined` can be overridden by later `recruited` via re-recruitment) |

---

## Crew-Conditional Story Flags

These flags only exist if the relevant crew member is recruited:

| Flag | Requires | Mission |
|------|----------|---------|
| `elena_pirate_insight` | `elena_recruited` | M09 |
| `marcus_recognized_guild_hardware` | `marcus_recruited` | M12 |
| `marcus_vouched` | `marcus_recruited` + `met_marcus_jin` | M13 |
| `priya_modified_scanner` | `priya_recruited` | M14 |

These are **bonus content** — they enrich the narrative but never gate progression. A solo player can complete every mission without these flags.

---

## Critical Path Flags

These flags are **required** for Act One progression. A player must set all of these:

```
Mission 01: (trade_permits system, not flags)
Mission 02: (mission completion, not flags)
Mission 03: talked_to_elena_cantina
Mission 04: breakstone_permit_earned, met_hanna_voss
Mission 05: met_marcus_jin, completed_mining_tutorial
Mission 06: met_priya_osei, escorted_priya_axiom
Mission 07: met_tomas_drifter, (accepted or declined)_drifter_deal
Mission 08: encountered_distress_signal, met_reva_sato, pirate_conspiracy_awareness
Mission 09: met_dex_halloran, accepted_dex_favor
Mission 10: delivered_dex_chip, met_malia_torres, malia_pirate_intel
Mission 11: attended_summit, summit_deadlock, faction_positions_known
Mission 12: survived_pirate_attack, combat_tutorial_complete
Mission 13: met_oren_tak, oren_revealed_base
Mission 14: scanned_pirate_base, pirate_base_confirmed, has_scan_data
Mission 15: m15_decision_made, (one path chosen)
Mission 16: completed_operation, ledger_discovered, base_neutralized
Mission 17: act_one_complete, ledger_known, new_horizons_unlocked
```

---

## Flag Count Summary

| Category | Count |
|----------|-------|
| NPC meeting flags (`met_*`) | 9 |
| Story progression flags | 26 |
| Player choice flags | 8 |
| Optional/flavor flags | 12 |
| Crew recruitment flags | 24 |
| Act milestone flags | 3 |
| **Total** | **82** |

---

## Implementation Notes

1. All flags use `player.dialogue_flags` (dict[str, bool]) — already implemented
2. Mission prerequisites use `required_flags` field — already implemented (Step 3)
3. Dialogue conditions use `required_flags` / `excluded_flags` on responses — already implemented (Step 4)
4. Flag-setting rewards use `set_flag` reward type — already implemented (Step 2)
5. Forced encounters use `trigger_flag` for once-only gating — already implemented (Step 5)
6. No new framework code needed — all flag infrastructure is in place
