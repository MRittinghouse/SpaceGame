# Refinement Roadmap — Breathing Life into the Aurelia Expanse

> **Goal**: Transform Act I from a linear narrative demo into a living, replayable universe. Add strategic depth to trading, variety to encounters, personality to planets, meaningful player builds through expanded skill trees, and organic side content that makes the Expanse feel inhabited.

**Last Updated**: 2026-03-16

---

## Cycle Status Tracker

| Cycle | Name | Status | % | Notes |
|-------|------|--------|---|-------|
| **R1** | Regional Markets | **DONE** | 100% | Market profiles, filtering, specialty pricing all working. Trend visibility gated behind Market Eye skill. Remote prices on galaxy map info panel (gated behind Market Insider skill). 9 tests. |
| **R2** | Ship & Upgrade Overhaul | **DONE** | 100% | 24 ships, 43 upgrades with tier (1-3) + system-locking. 3 new upgrades added (diplomatic_transponder, trade_manifest_scanner, overclocked_engines). |
| **R3** | Encounter Variety | **DONE** | 100% | 131 encounters across 11 types. Exceeds target of ~37. |
| **R4** | Side Missions | **DONE** | 100% | 21 narrative side missions + 12 crew quests + 5 procedural templates (bounty, delivery, smuggling, survey, salvage). ProceduralMissionGenerator model with station board UI. Contracts rotate daily per-system. 24 tests. |
| **R5** | Skill Tree Expansion | **DONE** | 100% | 89 skills across 9 trees (175 total skill points). 26 new skills + 5 multi-rank upgrades. Every tree has capstone skill. Ground Combat overhauled (6→11 skills). 3 orphan positions fixed. Respec system: model + UI button in skill tree view. |
| **R6** | Faction Reputation | **DONE** | 100% | Tiers, spillover, consequences, faction perks (12 perks across 4 factions at friendly/allied). Buy/sell bonuses, free fuel/repairs, mining/salvage yield bonuses, safe passage. Active perks displayed in character view with tier colors. |
| **R7** | Crew Depth | **DONE** | 100% | 12 crew quests (3-stage arcs), loyalty system, ambient dialogue, party management. 15 lightweight crew added (specialist hirelings at all 11 systems). Companion/crew distinction: companions have loyalty/XP/quests, crew provide flat passive bonuses. 19 total crew templates (4 companions + 15 crew). 69 ambient dialogue lines. Crew hire UI in station hub cantina with slot tracking. 12 tests. |
| **R8** | Mini-Game Expansion | **DONE** | 100% | Mining: 5/5 systems. Salvage: 5/5. Refining: Nexus Prime added. Danger-based yield scaling (safe/moderate/dangerous multipliers). Faction perk yield bonuses stack with danger. Yield bonus indicators in mining/salvage session summaries. Fixed refining bonus type mismatch (refine_speed→refining_speed, refine_yield→gathering_yield_bonus). |
| **R9** | Living Universe Polish | **DONE** | 100% | Galaxy events (5 types, 18 templates), event chains (strike cascade), station chatter (148 lines across 11 systems), news ticker (44 templates), travel log (4 trigger types). Market integration: embargo blocks trade, festival/breakthrough modify prices, strike raises production costs. 126 new tests. Station chatter wired into station hub flavor text. News ticker rendered at bottom of galaxy map. Travel log first-visit entries auto-generated on arrival. |
| **R10** | Combat Encounter Depth | **DONE** | 100% | Faction enemies, pre-combat negotiation/bribe, combat in travel pool. Tier-based loot scaling: credit_reward on all 28 enemies, loot tables normalized by danger_tier, invalid commodity refs fixed. Ground loot bonus skill (combat_scavenger) now applied to ground mission loot + crew bonus stacking. Rare loot drops on all 10 dangerous-tier enemies with "RARE!" visual callout. 18 tests. |
| **R11** | Achievements & Polish | **DONE** | 100% | 62 achievements (+19 new: combat, side quest, exploration, smuggling, progression). 5 new player stat fields wired. Category filter tabs in achievements view (12 categories, click to filter). Badge colors for combat and side_quest categories added. |
| **NP** | Narrative Polish | **DONE** | 100% | Full writing pass across all narrative content. 55 mission descriptions rewritten with texture and personality. ~216 em-dashes purged across 5 content files. 6 "no X, no Y, just Z" GenAI patterns removed. 8 location descriptions polished. ~25 NPC dialogue lines rewritten (physical intros, character voice, removing clichés). Station chatter expanded to 148 lines. All dialogue trees reviewed for natural tone. |

> **All refinement cycles complete.** R1-R11 + Narrative Polish pass are done. The Aurelia Expanse has regional identity, crew depth, side content, skill variety, faction consequences, living-world events, and polished narrative voice throughout.

### Current Counts (as of 2026-03-16)

| System | Count |
|--------|-------|
| Tests | 4,242 |
| Views | 34 |
| Missions | 55+ (22 campaign + 21 side + 12 crew quests + procedural) |
| Encounters | 131 (11 types) |
| Enemy Templates | 28 |
| Ship Types | 24 |
| Upgrades | 43 (tiered 1-3, system-locked) |
| Commodities | 27 |
| Skill Trees | 9 (89 skills, 175 total points) |
| Crew Members | 19 (4 companions + 15 crew specialists) |
| Achievements | 62 |
| Mining Configs | 5 (Breakstone, Iron Depths, Forgeworks, Verdant, The Fulcrum) |
| Salvage Configs | 5 (Forgeworks, Crimson Reach, Breakstone, The Fulcrum, Iron Depths) |
| Factions | 4 + Crimson Reach (with rivalry + spillover + consequences) |

---

## Pre-Refinement State Audit

| System | Count | Gap |
|--------|-------|-----|
| Commodities | 27 (8 basic, 11 industrial, 7 luxury, 1 quest) | All available everywhere — no regional identity |
| Systems | 11 | No production/consumption tags populated; no market filtering |
| Ships | 9 | No hull/shield/speed stats populated; price=0 on all |
| Upgrades | 21 (no slot categories) | Flat list, no tier progression, no slot field used |
| Skill Trees | 4 (Trading, Gathering, Mining, Leadership) | 26 total skills — no combat, social, exploration, or smuggling trees |
| Factions | 4 + Crimson Reach | No reputation thresholds, no perks, no tangible consequences |
| Crew Members | 4 (navigator, engineer, scientist, trader) | No personal quests, no depth beyond stat bonuses |
| Enemy Templates | 28 | Good count, but only 13 encounter wrappers |
| Encounters | 13 | Thin — 5 types × 2-3 variants; no combat encounters in random pool |
| Mining Configs | 2 (Breakstone, Iron Depths) | 18% system coverage |
| Salvage Configs | 2 (Forgeworks, Crimson Reach) | 18% system coverage |
| Refining Recipes | 9 | Decent, but refining only available where mini-games are |
| Campaign Missions | 22 | Entirely linear, no branching |
| Side Missions | 0 | Zero — only procedural trade/ground contracts |
| Achievements | 43 | Decent, but no side-quest or social achievements |

---

## Cycle R1: Regional Markets — Per-Planet Trade Identity

**Priority**: HIGH — This is the single highest-impact change for making systems feel distinct.

### The Problem
Every system sells every commodity. There's no reason to plan trade routes, no regional flavor, and no discovery. The player has no reason to prefer one system over another for buying/selling.

### The Fix

**R1.1 — System Market Profiles** (data + model)
Add `market_profile` to each system in `systems.json`:

```json
{
  "id": "forgeworks",
  "market_profile": {
    "available": ["common_metals", "rare_metals", "machinery", "fuel", "food", "alloy_composite"],
    "specialty_buy": ["common_metals", "rare_metals"],
    "specialty_sell": ["machinery", "alloy_composite"],
    "excluded": ["art", "exotic_goods", "medical"]
  }
}
```

- `available`: Commodities that appear in this system's market
- `specialty_buy`: Commodities this system produces — lower buy prices (−15% to −30%)
- `specialty_sell`: Commodities this system consumes — higher sell prices (+15% to +30%)
- `excluded`: Never appears here (cultural/economic reasons)

**Proposed Market Identities**:

| System | Identity | Specialty Buy (Cheap) | Specialty Sell (Expensive) | Excluded |
|--------|----------|----------------------|---------------------------|----------|
| Nexus Prime | Trade hub capital | fuel, textiles | — (fair prices on everything) | contraband |
| Verdant | Agricultural world | food, textiles | electronics, machinery | weapons_components, combat_stims |
| Forgeworks | Industrial forge | common_metals, machinery | food, textiles, medical | art, exotic_goods |
| Breakstone | Rough mining frontier | raw_ore, iron_ore, scrap_metal | food, medical, electronics | luxury goods, art |
| Axiom Labs | Research station | electronics, medical | rare_metals, crystal_ore | contraband, weapons |
| Haven's Rest | Refugee sanctuary | food, textiles | — (poor economy, low stock) | weapons, combat_stims |
| Crimson Reach | Pirate territory | weapons_components, combat_stims | stolen_data, restricted_tech | — (anything goes) |
| Stellaris Port | Luxury trade post | art, exotic_goods, precious_metals | machinery, common_metals | contraband_medicine |
| Iron Depths | Deep mining colony | rare_metals, crystal_ore, rare_ore | food, medical, electronics | luxury goods |
| Nova Research | Science outpost | electronics, medical | rare_ore, crystal_ore | contraband, weapons |
| The Fulcrum | Lawless crossroads | fuel, scrap_metal | weapons_components, restricted_tech | — |

**R1.2 — Market Filtering** (code)
Modify `Market.generate_listings()` (or wherever listings are built) to filter commodities against the system's `available` list. Apply specialty price modifiers.

**R1.3 — Trade Route Discovery Skill**
Add a "Market Intel" skill node to the Trading skill tree that progressively reveals specialty buy/sell info for visited systems on the galaxy map tooltip.

### Design Notes
- Nexus Prime stays as a "safe harbor" where most things are available at fair-but-unremarkable prices
- Dangerous systems should have the most profitable specialty margins (risk/reward)
- Haven's Rest should be a poor market overall — it's a refugee station, not a trade hub
- Crimson Reach sells everything including contraband, but at a premium for legal goods

---

## Cycle R2: Ship & Upgrade Overhaul

**Priority**: HIGH — Ships currently have no stats populated; upgrades have no slot system.

### R2.1 — Ship Stats Population
Fill in actual stats for all 9 ships in `ship_types.json`:

| Ship | Price | Cargo | Hull | Shield | Speed | Weapon Slots | Utility Slots | Notes |
|------|-------|-------|------|--------|-------|-------------|---------------|-------|
| Shuttle | 0 (starter) | 50 | 40 | 10 | 8 | 1 | 1 | Tutorial ship |
| Light Freighter | 8,000 | 150 | 60 | 20 | 6 | 1 | 2 | First upgrade |
| Fast Courier | 12,000 | 100 | 50 | 25 | 10 | 1 | 2 | Speed build |
| Scout Vessel | 15,000 | 60 | 45 | 30 | 9 | 2 | 2 | Exploration |
| Armed Trader | 20,000 | 120 | 80 | 35 | 5 | 2 | 1 | Combat-trade hybrid |
| Medium Freighter | 25,000 | 300 | 70 | 25 | 4 | 1 | 3 | Pure trade |
| Clipper | 30,000 | 150 | 65 | 40 | 8 | 2 | 2 | Balanced |
| Luxury Yacht | 40,000 | 200 | 55 | 45 | 7 | 1 | 3 | Social/diplomatic bonuses |
| Bulk Hauler | 50,000 | 600 | 90 | 20 | 3 | 1 | 4 | Endgame trade |

### R2.2 — Upgrade Slot System
Add `slot` field to upgrades and enforce slot limits per ship:

- **Weapon**: laser_cannon, dual_laser, missile_launcher, ion_disruptor, plasma_torpedo, salvaged_pulse_emitter, mining_laser_retrofit
- **Defense**: basic_shield_gen, armor_plating, point_defense, emergency_repair, advanced_shield
- **Utility**: cargo_bay_ext, fuel_tank_upgrade, efficient_engines, emergency_thrusters, mining_drill_mk2, advanced_scanner
- **Smuggling**: hidden_compartment, signal_jammer, false_transponder

### R2.3 — Upgrade Tiers
Add `tier` field (1-3) so shipyard can show progression:

| Tier | Weapon Example | Defense Example | Price Range |
|------|---------------|-----------------|-------------|
| 1 | Salvaged Pulse Emitter | Basic Shield Gen | 500–5,000 |
| 2 | Laser Cannon, Dual Laser | Armor Plating, Point Defense | 8,000–18,000 |
| 3 | Plasma Torpedo | Advanced Shield | 25,000–30,000 |

### R2.4 — System-Locked Upgrades
Not every upgrade should be available everywhere:

- Smuggling upgrades: Crimson Reach, The Fulcrum only
- Tier 3 weapons: Crimson Reach, Breakstone, The Fulcrum
- Mining upgrades: Breakstone, Iron Depths, Forgeworks
- Advanced shields: Axiom Labs, Nova Research, Stellaris Port
- Basic tier 1: Available everywhere

### R2.5 — New Upgrades (6-8 additions)
Fill gaps in the upgrade roster:

- **Navigation Computer** (Utility, Tier 2): −10% fuel consumption per jump
- **Trade Manifest Scanner** (Utility, Tier 2): See exact cargo contents of merchant encounters
- **Reinforced Hull Plating** (Defense, Tier 2): +15% hull HP, −5% speed
- **ECM Suite** (Defense, Tier 3): 20% chance to avoid ambush encounters entirely
- **Overclocked Engines** (Utility, Tier 3): +2 speed, +15% fuel consumption
- **Crew Quarters Expansion** (Utility, Tier 2): +1 crew slot
- **Tractor Beam** (Utility, Tier 2): +25% salvage yields
- **Diplomatic Transponder** (Utility, Tier 1): +5% faction reputation gains

---

## Cycle R3: Encounter Variety & Random Events

**Priority**: HIGH — 13 encounters is far too few for a game with frequent travel.

### R3.1 — Expand Encounter Pool (Target: 35-40 encounters)

**New Distress Encounters** (5):
- `distress_pirates_01`: Ship under pirate attack — help fight or flee (combat optional)
- `distress_plague_01`: Station quarantine — deliver medical supplies for reputation + credits
- `distress_refugee_01`: Overcrowded transport begging for food — give supplies or ignore
- `distress_smuggler_01`: Smuggler claims they're being chased by authorities — help or turn in
- `distress_mechanical_02`: Ship with engine failure near a nebula — tow them or salvage

**New Merchant Encounters** (4):
- `merchant_rare_01`: Traveling merchant with 1-2 rare commodities at slight discount
- `merchant_info_01`: Trader offers market tip (reveals a specialty price at nearby system) for small fee
- `merchant_barter_01`: Merchant wants to trade cargo directly — commodity swap, no credits
- `merchant_collector_01`: Collector seeking a specific commodity — pays 2× if you have it

**New Anomaly/Discovery Encounters** (5):
- `anomaly_cache_01`: Hidden supply cache in asteroid field — free loot if you have scanner
- `anomaly_signal_01`: Encrypted signal — decoding (skill check) reveals hidden location or credits
- `anomaly_wreck_field_01`: Old battlefield debris — mini-salvage opportunity
- `anomaly_solar_storm_01`: Solar storm approaching — take hull damage or burn fuel to reroute
- `anomaly_probe_01`: Ancient probe with data chip — sell to Axiom Labs or Nova Research

**New Hostile Encounters** (5):
- `ambush_pirate_duo_01`: Two pirate ships attack simultaneously
- `ambush_customs_01`: Faction patrol demands cargo inspection — dangerous if carrying contraband
- `ambush_bounty_01`: Bounty hunter targeting player (triggers at low faction rep)
- `blockade_01`: System blockade — pay toll, fight, or find alternate route
- `raider_convoy_01`: Raider convoy spotted — avoid or engage for high reward

**New Dialogue Encounters** (5):
- `hail_old_friend_01`: Former crewmate hails you — short dialogue, small gift or intel
- `hail_warning_01`: Anonymous transmission warns about danger ahead — foreshadowing
- `hail_merchant_guild_01`: Guild rep offers a lucrative but time-sensitive contract
- `hail_scientist_01`: Researcher asks you to carry a delicate instrument — delivery side quest
- `hail_drifter_01`: Wandering philosopher shares cryptic lore about the Expanse

### R3.2 — Danger-Level Gating
Tag each encounter with `danger_min` / `danger_max` so encounters match system danger:
- Safe systems: distress, merchant, peaceful anomaly encounters
- Moderate systems: above + customs inspections, minor hostiles
- Dangerous systems: above + ambushes, blockades, raider convoys

### R3.3 — Encounter Dialogue Trees
Create short dialogue trees (2-4 nodes each) for the 5 dialogue encounters and the choice-based distress encounters. These should feel like real moments, not just loot drops.

---

## Cycle R4: Side Missions (18-20 Narrative Quests)

**Priority**: HIGH — Currently zero side missions. This is the biggest content gap.

### Design Philosophy
Side missions should:
- Be **discoverable** (found at stations, from NPCs, from encounters)
- Be **completable in 1-3 jumps** (not sprawling multi-system arcs)
- **Reward** credits, reputation, XP, or unique items
- **Not block** campaign progression
- Feel **organic** — like the universe has things happening independent of the player
- **Reinforce system identity** — each side quest should make the system it lives in feel more real
- Some should present **moral choices** that have faction reputation consequences

### R4.1 — Side Mission Framework
Add `type: "side"` support to the mission system. Side missions need:
- `available_at`: List of systems where this mission can be picked up
- `available_after`: Campaign mission ID prerequisite (for pacing)
- `available_before`: Campaign mission ID after which this expires (optional)
- `repeatable`: Boolean (most should be false)
- `discovery_method`: How the player finds it — "npc" (talk to someone), "station_board" (bulletin board), "encounter" (triggered during travel), "automatic" (triggers on arrival)

### R4.2 — Narrative Side Missions

#### Nexus Prime (Trade Hub — 2 quests)

**"The Price of Information"** — Available after `bill_of_landing`
A data broker in the freight depot offers to sell you a market intelligence package — but first she needs you to deliver a sealed data chip to a contact at Stellaris Port. Simple courier job, but the chip contains more than market data. Choosing to open it (breaking trust) vs. delivering blind introduces a moral fork. *Rewards: credits + market intel skill unlock OR reputation hit + secret intel about Forgeworks.*

**"Dock Rat's Favor"** — Available after `iron_delivery`
A dock worker asks you to smuggle a personal package to Haven's Rest — nothing illegal, just sentimental items for a refugee family member. The catch: Haven's Rest customs is tight, and you'll need to talk your way through. *Rewards: small credits, Haven's Rest reputation, unlocks ambient dialogue.*

#### Verdant (Agricultural — 2 quests)

**"Blight Season"** — Available after `footing_the_bill`
Verdant's crops are failing in one sector. A farmer needs you to pick up a specialized pesticide from Axiom Labs, but the Science Collective has restricted its export. Convince them (social check), buy it at premium (expensive), or smuggle it out. *Rewards: Verdant reputation, credits, faction consequences based on method.*

**"The Heirloom Seeds"** — Available after `the_scholars_errand`
An elderly botanist has cultivated a unique strain of Verdant wheat and wants samples delivered to three different systems for safekeeping before she dies. Multi-stop delivery with short, poignant dialogue at each stop. *Rewards: modest credits per stop, XP, unique ambient dialogue at all three destinations acknowledging the delivery.*

#### Forgeworks (Industrial — 2 quests)

**"Whistle-Blower"** — Available after `union_territory`
A factory supervisor has evidence of unsafe working conditions that the Syndicate is covering up. She wants it delivered to a journalist at Nexus Prime — but Forgeworks security is watching her. Agreeing puts you on a Forgeworks watchlist (temporary rep penalty), refusing means nothing changes. *Rewards: large Nexus Prime/Frontier Alliance reputation, Forgeworks rep penalty, credits from the journalist.*

**"Old Debts"** — Available after `the_foremans_son`
A retired foreman wants to send a package to his estranged son at Breakstone. Simple delivery, but the dialogue at both ends reveals deep worldbuilding about the Forgeworks-Breakstone labor tensions — why the son left, what the father regrets. *Rewards: small credits, XP, unique dialogue unlocked at both stations.*

#### Breakstone (Mining Frontier — 2 quests)

**"Miners' Plight"** — Available after `union_territory`
Breakstone miners need medicine smuggled past a Forgeworks embargo. Tests player morality — help the miners (reputation with Miners Union, lose Forgeworks rep) or report it (Forgeworks rep, miners remember). *Rewards: faction-dependent, medicine delivery grants access to discounted mining upgrades at Breakstone.*

**"Claim Jumper"** — Available after `the_foremans_son`
A miner's claim is being muscled out by a corporate-backed operation. Help the miner (ground exploration mission to recover their claim beacon), negotiate a buyout (social check), or side with the corporation (Forgeworks rep). Three distinct resolutions. *Rewards: credits, faction rep, possible unique ore deposit access.*

#### Axiom Labs (Research — 2 quests)

**"The Scholar's Dilemma"** — Available after `the_scholars_errand`
A junior researcher has discovered something anomalous in the data but publishing it would contradict her mentor's life work. She asks you to quietly deliver the raw data to Nova Research for independent verification. *Rewards: Science Collective reputation, XP, unlocks a follow-up ambient dialogue about the discovery.*

**"Lab Rat"** — Available after `recruit_scientist`
Axiom needs a live test of a new shield modulator — on your ship. Agree to install an experimental upgrade and fly through a moderate-danger system to collect field data. Risk: the modulator might malfunction mid-flight (encounter). *Rewards: keep the prototype upgrade (Tier 2 shield variant) or return it for credits + Science Collective rep.*

#### Haven's Rest (Refugee Station — 2 quests)

**"Supply Run"** — Available after `cargo_lost`
Haven's Rest desperately needs food and medical supplies. Deliver X units of food + medical for large reputation boost but modest credits. The station administrator's dialogue reveals the human cost of the political tensions driving the main campaign. *Rewards: large Haven's Rest/Frontier Alliance reputation, modest credits, ambient dialogue changes.*

**"The Lost Registry"** — Available after `whispers_at_the_bar`
A refugee is searching for a family member who was on a transport that never arrived. The last known coordinates point toward Crimson Reach. Investigate: travel to Crimson Reach, find a data log (ground exploration or salvage), return with news — good or bad. *Rewards: Haven's Rest reputation, XP, emotional dialogue payoff. The answer is bittersweet — the family member survived but chose not to come to Haven's Rest.*

#### Crimson Reach (Pirate Territory — 2 quests)

**"The Ghost Ship"** — Available after `the_crimson_run`
Rumors of a derelict in the Crimson Reach debris field. Short ground exploration mission on the derelict. Reveals lore about a pre-Expanse colony ship — the first settlers who came before the factions formed. *Rewards: rare salvage, XP, lore journal entry.*

**"Honor Among Thieves"** — Available after `the_crimson_run`
A pirate captain offers you a job: retrieve a stolen item from a rival gang's hideout at The Fulcrum. No questions asked. Simple fetch quest, but completing it earns you a "neutral" status with Crimson Reach pirates — they won't attack you on sight anymore. Declining means nothing changes. *Rewards: Crimson Reach reputation, reduced random pirate encounters in dangerous systems.*

#### Stellaris Port (Luxury Trade — 2 quests)

**"The Collector"** — Available after `footing_the_bill`
A wealthy collector wants you to acquire a specific rare commodity from a dangerous system. Good pay, simple fetch quest, but the destination is the most dangerous system you've unlocked so far. *Rewards: large credits, Stellaris Port reputation.*

**"Counterfeit Concerns"** — Available after `the_drifters_deal`
A Stellaris merchant suspects counterfeit luxury goods are being sold at The Fulcrum, undercutting legitimate trade. Investigate: travel to The Fulcrum, examine the goods (skill check or buy a sample), report back. Twist: the counterfeits are actually being produced at Forgeworks as a side operation. *Rewards: credits, Commerce Guild reputation, intel that connects to campaign themes.*

#### Iron Depths (Deep Mining — 1 quest)

**"Salvage Rights"** — Available after `iron_depths_investigation`
Competing salvage claim on a valuable wreck in the deep tunnels. Negotiate with the other claimant (social), race them to the site (ground exploration), or split the take (less reward, no conflict). *Rewards: rare materials, credits, XP.*

#### Nova Research (Science Outpost — 1 quest)

**"Signal from the Deep"** — Available after `embassy_visit`
Nova Research has detected a repeating signal from beyond charted space. They need someone to deploy a signal amplifier at the edge of the system — but the coordinates are in a debris-heavy zone. Short navigation challenge. *Rewards: Science Collective reputation, credits, lore about what lies beyond the Expanse. Seeds curiosity for Act Two.*

#### The Fulcrum (Lawless Crossroads — 1 quest)

**"The Gambler's Debt"** — Available after `the_drifters_deal`
A gambler at The Fulcrum owes money to a dangerous figure. Pay off the debt (expensive), negotiate (social skill check), or deal with the collector (combat). Short dialogue tree with 3 endings. *Rewards: credits (if negotiated), The Fulcrum reputation, the gambler becomes an informant who tips you off about future encounters.*

#### Encounter-Triggered (not tied to a system — 2 quests)

**"The Stowaway"** — Random encounter after `recruit_navigator`
Discover a stowaway in your cargo hold. Dialogue tree: turn them in at the next port (bounty credits), drop them at Haven's Rest (reputation), or let them work passage (temporary crew bonus for 5 jumps). *Rewards: varies by choice.*

**"Adrift"** — Random encounter after `cargo_lost`
You find a damaged escape pod with a barely conscious pilot. They were fleeing something — but won't say what. Rescue them and deliver to any station, or leave them. If rescued, they show up later at Haven's Rest with a small thank-you gift and a cryptic warning. *Rewards: small credits, Haven's Rest reputation, foreshadowing dialogue.*

### R4.3 — Procedural Side Quests (templates, infinite variety)
Expand the existing contract system with more templates:
- **Bounty Contracts**: Hunt specific enemy type in specific system
- **Escort Missions**: Protect NPC ship through dangerous space (2-3 jumps)
- **Smuggling Runs**: Move contraband between specific systems (risk/reward)
- **Survey Missions**: Visit 2-3 systems and report market data (scout skill)
- **Salvage Claims**: Go to specific system, complete salvage mini-game, return

---

## Cycle R5: Skill Tree Expansion

**Priority**: HIGH — Currently 4 trees with 26 skills. No combat, social, exploration, or smuggling trees. Players have very limited build identity.

### The Problem
A player who focuses on combat has zero skill nodes to invest in. A player who talks their way through encounters has no social skills to develop. The current trees only serve traders and miners — roughly half the gameplay has no progression support.

### R5.1 — New Skill Tree: Combat & Tactics (8 skills)

```
[Steady Aim] ──→ [Rapid Fire] ──→ [Overcharge]
      │                               │
      ▼                               ▼
[Hull Breaker]              [Shield Piercer]
      │
      ▼
[Tactical Retreat] ──→ [Ambush Sense]
                            │
                            ▼
                     [Battle Hardened]
```

| Skill | Max Level | Effect |
|-------|-----------|--------|
| Steady Aim | 3 | +10% weapon accuracy per level |
| Rapid Fire | 2 | −15% weapon cooldown per level |
| Overcharge | 1 | Unlocks overcharge ability: double damage, burns weapon for 2 turns |
| Hull Breaker | 2 | +15% damage to hull per level (ignores shields) |
| Shield Piercer | 2 | +20% damage to shields per level |
| Tactical Retreat | 1 | Flee from combat without hull damage (once per encounter) |
| Ambush Sense | 2 | +15% chance to detect ambush encounters before they trigger per level |
| Battle Hardened | 3 | +5% max hull HP per level |

### R5.2 — New Skill Tree: Social & Diplomacy (7 skills)

```
[Silver Tongue] ──→ [Faction Diplomat] ──→ [Peacemaker]
      │                                        │
      ▼                                        ▼
[Read the Room]                        [Double Agent]
      │
      ▼
[Negotiation Pressure] ──→ [Black Market Contact]
                                    │
                                    ▼
                              [Information Broker]
```

| Skill | Max Level | Effect |
|-------|-----------|--------|
| Silver Tongue | 3 | +10% success chance on social skill checks per level |
| Faction Diplomat | 2 | +15% faction reputation gains per level |
| Peacemaker | 1 | Unlock dialogue option to avoid combat in non-pirate encounters |
| Read the Room | 2 | See NPC disposition and hidden dialogue options per level |
| Double Agent | 1 | Reputation losses with rival factions reduced by 50% |
| Negotiation Pressure | 2 | +5% better prices on all trades per level (stacks with Trading tree) |
| Black Market Contact | 1 | Unlock contraband trading at non-criminal stations (higher risk, higher reward) |
| Information Broker | 2 | +1 random encounter intel per jump per level (preview what's ahead) |

### R5.3 — New Skill Tree: Exploration & Piloting (7 skills)

```
[Fuel Efficiency] ──→ [Jump Navigator] ──→ [Wormhole Sense]
      │                                         │
      ▼                                         ▼
[Cartographer]                           [Storm Rider]
      │
      ▼
[Salvage Eye] ──→ [Anomaly Detector]
                        │
                        ▼
                  [Uncharted Routes]
```

| Skill | Max Level | Effect |
|-------|-----------|--------|
| Fuel Efficiency | 3 | −10% fuel consumption per jump per level |
| Jump Navigator | 2 | −1 travel time (game days) per jump per level |
| Wormhole Sense | 1 | Reveal hidden shortcuts between non-adjacent systems |
| Cartographer | 2 | +20% XP for first visits to new systems per level |
| Storm Rider | 2 | −25% hull damage from environmental hazards per level |
| Salvage Eye | 2 | +15% chance to find extra loot in encounter rewards per level |
| Anomaly Detector | 2 | +20% chance for discovery/anomaly encounters per level |
| Uncharted Routes | 1 | Unlock 1-2 secret routes to restricted systems (late-game access) |

### R5.4 — New Skill Tree: Smuggling & Subterfuge (6 skills)

```
[Concealment] ──→ [False Manifest] ──→ [Ghost Runner]
      │                                     │
      ▼                                     ▼
[Heat Management]                    [Inside Man]
      │
      ▼
[Quick Dump]
```

| Skill | Max Level | Effect |
|-------|-----------|--------|
| Concealment | 3 | +15% hidden compartment capacity per level |
| False Manifest | 2 | −20% chance of contraband detection per level |
| Ghost Runner | 1 | Complete invisibility to scans for 1 jump (cooldown: 5 jumps) |
| Heat Management | 3 | −10% heat gain per smuggling action per level |
| Inside Man | 1 | Unlock a fence contact at one random safe-system station |
| Quick Dump | 1 | Instantly jettison contraband when scanned (lose goods, avoid penalty) |

### R5.5 — Expand Existing Trees

**Trading Mastery** (add 3 skills):
- **Supply Chain Analyst** (prereq: Market Insider): See which systems buy what you're carrying at best price — highlights optimal sell destinations on galaxy map
- **Commodity Futures**: Lock in a buy price for 3 game days — reserve stock at current price for later pickup
- **Trade Magnate** (capstone): +3% sell price on all transactions, permanent

**Leadership & Operations** (add 3 skills):
- **Crew Specialization** (prereq: Crew Mentor): Crew members gain a secondary role bonus at 50% effectiveness
- **Fleet Contacts**: Unlock 1 NPC cargo ship that sells discounted goods at a random station each week
- **Inspirational Presence** (capstone): All crew bonuses +25%

### R5.6 — Skill Point Economy
Currently unclear how skill points are earned. Ensure:
- 1 skill point per level-up
- Bonus skill points from select side missions (rewarding exploration builds)
- Total available points should allow investing deeply in 2 trees OR shallowly in 4 — forcing meaningful build choices
- Respec option available at Axiom Labs for a credit cost (forgiveness for experimentation)

### Target Totals After R5
| Tree | Current Skills | New Skills | Total |
|------|---------------|------------|-------|
| Trading | 5 | 3 | 8 |
| Gathering | 7 | 0 | 7 |
| Mining | 9 | 0 | 9 |
| Leadership | 5 | 3 | 8 |
| Combat & Tactics | 0 | 8 | 8 |
| Social & Diplomacy | 0 | 7 | 7 |
| Exploration & Piloting | 0 | 7 | 7 |
| Smuggling & Subterfuge | 0 | 6 | 6 |
| **Total** | **26** | **34** | **60** |

---

## Cycle R6: Faction Reputation System

**Priority**: HIGH — Factions exist in name only. Reputation has no mechanical teeth.

### The Problem
Four factions exist with colors and descriptions, but no reputation thresholds, no perks, and no consequences. The player can't build a meaningful relationship with any faction. Reputation is tracked but does nothing.

### R6.1 — Reputation Thresholds
Add tiered reputation levels to each faction:

| Level | Rep Range | Name |
|-------|-----------|------|
| -3 | −100 to −60 | Hostile |
| -2 | −59 to −30 | Unfriendly |
| -1 | −29 to −1 | Suspicious |
| 0 | 0 to 19 | Neutral |
| 1 | 20 to 49 | Friendly |
| 2 | 50 to 79 | Trusted |
| 3 | 80 to 100 | Allied |

### R6.2 — Faction Perks (unlock at reputation thresholds)

**Commerce Guild** (Nexus Prime, Stellaris Port):
- Friendly: −5% market prices at guild stations
- Trusted: Access to exclusive luxury commodity (Stellaris fine goods)
- Allied: Free docking, +10% sell prices, guild escort available for hire

**Miners Union** (Breakstone, Iron Depths):
- Friendly: −10% mining upgrade prices
- Trusted: Access to deep mining sites (richer yields)
- Allied: Free repairs at mining stations, rare ore tips (1/week)

**Science Collective** (Axiom Labs, Nova Research):
- Friendly: −10% on electronics and medical commodities
- Trusted: Access to experimental upgrades (Lab Rat quest line)
- Allied: Free fuel at research stations, anomaly encounter hints

**Frontier Alliance** (Verdant, Haven's Rest):
- Friendly: +5% sell price on food and textiles
- Trusted: Access to unique agricultural commodities
- Allied: Safe passage through Frontier-aligned space (no hostile encounters), crew recruitment discount

### R6.3 — Faction Consequences (negative reputation)

| Level | Consequence |
|-------|-------------|
| Suspicious | NPCs offer fewer dialogue options, some side quests unavailable |
| Unfriendly | 10% price markup at faction stations, hostile patrol encounters possible |
| Hostile | Denied docking at faction stations, faction ships attack on sight |

### R6.4 — Faction Rivalry Consequences
Each faction has a rival (Commerce Guild ↔ Miners Union, Science Collective ↔ Frontier Alliance). Actions that benefit one faction should mildly displease the rival (−25% of reputation gained). This creates meaningful tension — you can't be allied with everyone.

### R6.5 — Reputation Sources
Document clear sources of reputation gain/loss:
- Trading at faction stations: +1-3 rep per trade
- Completing faction-aligned side quests: +10-25 rep
- Campaign mission choices: variable
- Smuggling contraband at faction stations: −5-15 rep if caught
- Attacking faction-aligned ships: −20-50 rep
- Helping faction-aligned distress signals: +5-10 rep

---

## Cycle R7: Crew Depth & Personal Quests

**Priority**: MEDIUM-HIGH — 4 crew members with no personal stories feels like a missed opportunity.

### The Problem
Crew members are recruited via campaign missions and provide stat bonuses, but they have no personality in gameplay, no personal arcs, and no reason for the player to care about them beyond numbers.

### R7.1 — Crew Personal Quests (4 quests, one per existing crew member)

**Elena Reeves (Navigator)** — "Star Charts" — Available after 10 jumps with Elena aboard
Elena asks you to visit a system where her former ship disappeared years ago. Travel to the coordinates, find the wreck (salvage mini-game), recover her old captain's star charts. Elena's navigation bonuses permanently improve. Short dialogue about loss and moving forward. *Rewards: Elena loyalty bonus, permanent −5% fuel consumption with Elena aboard.*

**Marcus Jin (Engineer)** — "The Prototype" — Available after 5 repairs/upgrades with Marcus aboard
Marcus has been tinkering with a prototype engine modification. He needs specific parts from Forgeworks and a testing ground in open space. Fetch quest + a unique encounter where you test the mod. Risk of malfunction (small hull damage) but permanent upgrade if successful. *Rewards: Marcus loyalty bonus, unique engine upgrade (Tier 2.5 — not available in shops).*

**Dr. Priya Osei (Scientist)** — "Peer Review" — Available after visiting 3 systems with Priya aboard
Priya's research paper has been rejected by the Science Collective under suspicious circumstances. She suspects her rival at Nova Research plagiarized her work. Investigate at Nova Research (dialogue), confront the rival (social check or present evidence), resolve. *Rewards: Priya loyalty bonus, Science Collective reputation, unique scanner upgrade.*

**Tomas "Drifter" (Trader)** — "The Long Con" — Available after 10 trades with Tomas aboard
Tomas reveals he's been tracking a con artist who swindled his family out of their trading business. The con artist is operating at The Fulcrum under a new name. Confront them (dialogue tree with multiple outcomes), help Tomas get justice or convince him to let it go. *Rewards: Tomas loyalty bonus, large credits if successful, unique trade insight (permanent +3% sell prices with Tomas aboard).*

### R7.2 — Crew Loyalty System
Add a `loyalty` stat (0-100) to crew members:
- Starts at 30 (grateful for recruitment)
- Completing personal quest: +30
- Making choices aligned with their values: +5-10
- Making choices against their values: −5-10
- High loyalty (70+): crew bonus increased by 25%
- Max loyalty (90+): unique ambient dialogue, crew member occasionally offers helpful tips

### R7.3 — Crew Dialogue Lines
Add 3-5 context-sensitive lines per crew member that display as ambient text during gameplay:
- Arriving at a new system
- Before/after combat
- When trading at their specialty
- When visiting their "home" system
- Random idle chatter during travel

### R7.4 — Additional Crew Members (4 new recruitable crew)
Available through side missions rather than campaign missions:

**Ren Vasquez** (Gunner) — Recruited from Crimson Reach side quest
- Bonus: +15% weapon damage
- Personality: Reformed pirate, dry humor, distrusts authority

**Juno Park** (Quartermaster) — Recruited from Stellaris Port side quest
- Bonus: +10% cargo capacity, +5% sell prices
- Personality: Meticulous organizer, former luxury trade apprentice

**Koda Frost** (Pilot) — Recruited from random encounter after `under_fire`
- Bonus: +1 speed, +10% evasion in combat
- Personality: Quiet, intense, lives for the thrill of flight

**Zara Okonkwo** (Medic) — Recruited from Haven's Rest "Supply Run" quest
- Bonus: +20% hull repair efficiency, −10% medical commodity costs
- Personality: Compassionate, stubborn, former field surgeon

---

## Cycle R8: Mini-Game Expansion

**Priority**: MEDIUM — Mining and salvage at only 2 systems each feels restrictive.

### R8.1 — Expand Mining Availability

| System | Mining Config | Notes |
|--------|--------------|-------|
| Breakstone | Existing (common_metals, raw_ore focus) | Keep as-is |
| Iron Depths | Existing (rare_metals, crystal_ore focus) | Keep as-is |
| Forgeworks | NEW — industrial mining (common_metals, iron_ore) | Lower yields than Breakstone |
| Verdant | NEW — crystal farming (crystal_ore, rare trace) | Unique: organic crystal deposits |
| The Fulcrum | NEW — scrap mining (scrap_metal, salvaged_electronics) | Asteroid junkyard |

### R8.2 — Expand Salvage Availability

| System | Salvage Config | Notes |
|--------|---------------|-------|
| Forgeworks | Existing (industrial salvage) | Keep as-is |
| Crimson Reach | Existing (pirate wreckage) | Keep as-is |
| Breakstone | NEW — mining equipment salvage | Broken mining rigs |
| The Fulcrum | NEW — battlefield salvage | Old war debris, rare parts |
| Iron Depths | NEW — deep space salvage | Abandoned facilities |

### R8.3 — Refining Availability
Currently refining is only available where mining/salvage exists. Expand:
- Forgeworks (industrial theme — fits perfectly)
- Axiom Labs (advanced processing)
- Nexus Prime (trade hub — basic recipes only)

### R8.4 — Mini-Game Difficulty Scaling
Tie mini-game difficulty and rewards to system danger level:
- Safe systems: easier, lower yields
- Dangerous systems: harder, richer yields, rare drops

---

## Cycle R9: Living Universe Polish

**Priority**: MEDIUM — Flavor that makes the world feel inhabited.

### R9.1 — Station Ambient Dialogue
Add 3-5 ambient NPC lines per station that rotate on visit. Not interactive — just flavor text displayed in the station hub. Different lines based on campaign progress.

Examples for Nexus Prime:
- Early game: "Another day, another credit. Welcome to Nexus Prim, newcomer."
- After `cargo_lost`: "Did you hear? A cargo hauler went down near Forgeworks. Bad business."
- After `the_crimson_run`: "They say someone actually survived a run through Crimson Reach..."

### R9.2 — News Ticker
Add a scrolling news ticker to the galaxy map or station hub showing procedurally generated headlines:
- Price changes: "Crystal ore prices surge at Axiom Labs — shortage reported"
- Political events: "Forgeworks Syndicate tightens export controls on refined metals"
- Story echoes: Headlines that reflect completed campaign missions
- Random flavor: "Verdant wheat harvest breaks 10-year record"
- Side quest echoes: "Medicine shortage at Breakstone eases after anonymous delivery"

### R9.3 — Planet Descriptions on Galaxy Map
Add 2-3 sentence descriptions visible on the galaxy map when hovering over a system. Should convey personality and hint at what's available there.

### R9.4 — Travel Log Entries
Auto-generate brief log entries for notable events during travel:
- First visit to a system
- Completing a trade over X credits
- Surviving an encounter
- Discovering a new commodity
- Completing a side quest

### R9.5 — Dynamic Market Events
Temporary events that shift prices and create trading opportunities:
- **Shortage**: A system runs low on a commodity — prices spike 30-50% for 3-5 game days
- **Surplus**: Overproduction drives prices down 20-30% — good time to buy
- **Embargo**: Faction conflict blocks trade of specific commodities at specific stations
- **Festival**: Luxury goods prices spike at celebrating stations
- **Disaster**: Mining accident, crop failure, etc. — increased demand for specific goods

These should be signaled via the news ticker so attentive players can capitalize.

---

## Cycle R10: Combat Encounter Depth

**Priority**: MEDIUM — Combat exists but random combat encounters during travel are thin.

### R10.1 — Combat Encounters in Travel Pool
Currently the 13 encounter templates have no combat. Add combat as a possible outcome for hostile encounters (R3 adds the encounter wrappers, this cycle adds the combat integration).

### R10.2 — Faction-Specific Enemy Variants
Create enemy templates that match system factions:
- Crimson Reach / The Fulcrum: Pirate variants (existing)
- Forgeworks: Corporate security drones
- Breakstone: Desperate claim-jumpers
- Safe systems: Rare — only if player has very low reputation

### R10.3 — Retreat and Negotiation
Add pre-combat dialogue options for non-pirate encounters:
- Pay a bribe to avoid combat
- Use social skills to talk down aggressors (Social tree integration)
- Surrender cargo (lose goods, keep hull)
- Flee (requires speed check against enemy, Exploration tree bonus)

### R10.4 — Post-Combat Rewards Scaling
Better loot from harder fights:
- Tier 1 enemies: basic commodities, small credits
- Tier 2 enemies: industrial goods, moderate credits, chance of upgrade drop
- Tier 3 enemies: rare commodities, large credits, guaranteed upgrade or rare material

---

## Cycle R11: Achievements & New Game+ Polish

**Priority**: LOW — Polish layer after core content is in place.

### R11.1 — New Achievements (20-25 additions)
Fill gaps for new systems:

**Social**: First successful social skill check, Reach Allied with any faction, Reach Allied with rival factions simultaneously, Complete all crew personal quests
**Side Quests**: Complete 5 side quests, Complete 10 side quests, Complete all narrative side quests, Make every "moral" choice the same way (consistent ethics)
**Exploration**: Visit all 11 systems, Discover a hidden route, Complete 20 encounters
**Combat**: Win 10 combat encounters, Win a combat without taking damage, Use social skills to avoid 3 combats
**Trading**: Complete a trade route (buy specialty, sell at premium) worth 5000+, Trade at every system, Profit 50,000 total credits
**Smuggling**: Complete 5 smuggling runs, Get caught and talk your way out, Never get caught across entire playthrough

### R11.2 — Statistics Tracking Expansion
Track additional stats for the stats screen:
- Faction reputation history
- Side quests completed / available
- Crew loyalty levels
- Most profitable trade route
- Total encounters survived
- Moral choices made (left/right tendency)

---

## Implementation Order & Dependencies

```
R1 (Regional Markets)      ──┐
R2 (Ships & Upgrades)      ──┤
R3 (Encounter Variety)     ──┼── Foundation layer — can be done in parallel
R5 (Skill Trees)           ──┤
R6 (Faction Reputation)    ──┘
         │
         ▼
R4 (Side Missions)         ── Depends on R1, R3, R5, R6 (quests reference markets,
         │                     encounters, skill checks, faction consequences)
         ▼
R7 (Crew Depth)            ── Depends on R4 framework (personal quests are side missions)
         │
         ▼
R8 (Mini-Game Expansion)   ──┐
R9 (Living Universe)       ──┼── Independent polish — can be done in parallel
R10 (Combat Depth)         ──┘
         │
         ▼
R11 (Achievements & Polish) ── Final pass after all systems are in
```

### Estimated Scope Per Cycle

| Cycle | Primary Deliverables | New Tests | Content Volume |
|-------|---------------------|-----------|----------------|
| R1 | Market profiles, filtering code, galaxy map tooltips | ~30 | 11 market profiles |
| R2 | Ship stats, slot system, tier system, new upgrades | ~25 | 9 ship stat blocks, 27+ upgrade entries |
| R3 | 24 new encounter templates, 5+ dialogue trees | ~20 | 37 total encounters |
| R4 | Side mission framework, 20 narrative quests, 5 procedural templates | ~40 | 20 missions, 20+ dialogue trees, 4 new NPCs |
| R5 | 4 new skill trees, expand 2 existing, respec system | ~35 | 60 total skills across 8 trees |
| R6 | Reputation thresholds, perks, consequences, rivalry system | ~25 | 4 faction profiles with 3 tiers each |
| R7 | 4 crew personal quests, loyalty system, 4 new crew, ambient lines | ~30 | 8 total crew, 4 quest dialogue trees, 30+ ambient lines |
| R8 | 3 mining, 3 salvage, 3 refining configs, difficulty scaling | ~15 | 9 new mini-game configs |
| R9 | Ambient dialogue, news ticker, planet descriptions, market events | ~15 | 50+ ambient lines, 30+ news templates, 11 descriptions |
| R10 | Combat in encounters, faction enemies, negotiation, loot scaling | ~20 | 5 faction enemy sets, negotiation dialogues |
| R11 | 20-25 new achievements, expanded stats tracking | ~15 | 65+ total achievements |

### Totals After Full Roadmap

| System | Before | After |
|--------|--------|-------|
| Skill Trees | 9 (89 skills, 175 total points) | 8 (60 skills) |
| Side Missions | 0 | 20 narrative + 5 procedural templates |
| Encounters | 13 | ~37 |
| Faction Perks | 0 | 12 (3 tiers × 4 factions) |
| Crew Members | 4 | 8 (each with personal quest) |
| Mini-Game Locations | 4 | 13 |
| Achievements | 43 | ~65 |
| Upgrades | 21 | ~29 |
| Market Events | 0 | 5 event types |
| Ambient Dialogue Lines | 0 | 80+ |

---

## Guiding Principles

1. **Data-driven first**: Every new feature should be a JSON config consumed by existing systems, not new hardcoded logic. Extend models, don't duplicate them.

2. **Minimal code, maximum content**: The best cycles add 5 lines of code and 500 lines of JSON. If a feature requires a new system, question whether it can be achieved by extending an existing one.

3. **TDD remains non-negotiable**: Every model change gets a failing test first. Content JSON gets validation tests. No exceptions.

4. **Risk/reward gradient**: Safe systems should feel safe. Dangerous systems should feel dangerous. Every system should have a reason to visit and a reason to leave.

5. **Player discovery**: Don't tell the player everything upfront. Let them discover trade routes, side missions, and encounters through exploration. Skills should reveal more information, not gate access.

6. **Respect the narrative**: Side content should enrich the world established by the campaign, not contradict it. Side missions should feel like they exist in the same universe as the main story.

7. **Replayability over length**: A player replaying Act I should have a meaningfully different experience based on which side missions they find, which trade routes they discover, and which encounters they face.

8. **Build identity matters**: By endgame, a combat-focused smuggler should feel meaningfully different from a diplomatic trader. Skill trees and faction reputation should create distinct playstyles, not just number boosts.

9. **Every system should touch at least two others**: Market profiles affect trading AND side quests. Faction rep affects prices AND encounter outcomes. Crew loyalty affects bonuses AND available dialogue. The interconnections are what make a world feel alive.

10. **Bite-sized over bloated**: A 2-minute side quest that reveals one memorable detail about the world is worth more than a 20-minute fetch chain that says nothing. Keep side content tight and flavorful.
