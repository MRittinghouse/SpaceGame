# Skill Tree Overhaul — Vision & Review

## What Should Skills DO?

The protagonist goes from desperate 16-year-old orphan to capable captain. Skills should mark that journey. Every point invested should create one of three feelings:

1. **"I can feel the difference"** — The change is immediately noticeable in gameplay
2. **"I can do something new"** — A new option, ability, or information source unlocks
3. **"This is who I am"** — The skill defines the player's identity as a captain

What skills should NOT be: invisible +2% increments that the player can't feel. If investing a skill point doesn't change how the next 10 minutes of gameplay feel, the skill isn't worth having.

## Design Principles

**Fewer, bolder skills.** 60-80 meaningful skills beat 109 decorative ones. Every skill should pass the "would I notice if this disappeared?" test.

**Gateway skills over stat bumps.** "You can now see NPC disposition" (Empathic Read) is better than "+5% Persuasion." One changes the experience; the other changes a number.

**Specialization through identity, not restriction.** The player should feel like a Trader-Captain or a Combat-Captain or an Explorer-Captain based on their choices. Not because they're locked out of content, but because they're exceptionally GOOD at their thing.

**Integration with narrative.** Skills should connect to who the NPCs see when they look at the player. A player with high Social skills should get different dialogue. A player with high Combat skills should have enemies that react differently. Skills are character, not stats.

## Current State: The Honest Audit

### What Works
- **Empathic Read** (Social): Unlocks subtext hints in dialogue. FEELS different. Keep.
- **Master Negotiator** (Social): Unlocks unique dialogue options. New capability. Keep.
- **Remote Prices** (Trading): See prices at other systems. New information. Keep.
- **Trend Visibility** (Trading): See market trends. New information. Keep.
- **Crew Manager** (Leadership): +1 crew slot. Tangible, immediate. Keep.
- **Combat Capstones** (Juggernaut/Sentinel/Ghost): Identity-defining IF wired. Keep and wire.
- **Armor/Shield/Evasion skills** (Combat): Directly affect survivability. Keep.

### What Doesn't Work
- **+5% drill speed** (Mining): Imperceptible. Player can't feel this.
- **+2% sell price** (Trading): Lost in market variance noise.
- **9 smuggling skills** for a minor system: Overbuilt for the gameplay time spent.
- **11 mining skills** for a click mini-game: Too many skills for too little gameplay.
- **30 combat skills** (28% of all skills): Bloated. Many are tiny increments.
- **Ground combat tree** (11 skills): Secondary system, full tree. Overweight.
- **Drone Efficiency +5%** (Mining): The player has no frame of reference.

### The Root Problem
Most orphaned skills are **stat bumps that should be gameplay changers**. "+5% damage" becomes interesting when it's "Your first attack each combat deals double damage." The magnitude matters less than the moment.

## Proposed Structure: 6 Trees, ~90 Skills

### Why 6 instead of 9?
- **Merge Trading + Smuggling** → Commerce (trading is the core; smuggling is a variant)
- **Merge Mining + Gathering** → Industry (resource extraction and processing are one career)
- **Merge Ground Combat into Combat** → One combat identity (ground skills become sub-branch)
- **Keep**: Social, Leadership, Exploration, Commerce, Combat, Industry

### Skill Math
- ~15 skills per tree, average 2 levels each = ~90 skills, ~135 total levels
- At 1 point/level (uncapped):
  - Level 20: 20/135 = 15% (early specialization, 1 tree deep)
  - Level 40: 40/135 = 30% (2 trees deep or 3-4 moderate)
  - Level 60: 60/135 = 44% (broad competence, deep in 2-3)
  - Level 100: 100/135 = 74% (master of most, but not everything)
- Meaningful choice preserved at ALL levels

---

## Tree-by-Tree Review & Redesign

### 1. COMMERCE (merge Trading + Smuggling)

**Identity**: The shrewd merchant who always finds the angle.

**Keep & Wire:**
- `Negotiator` (buy price -5%/-10%) — tangible, affects every purchase
- `Trade Network` (sell price +5%/+10%) — tangible, affects every sale
- `Market Insider` (remote prices visible) — gateway skill, new information
- `Market Eye` (trend visibility) — gateway skill, new information
- `Tariff Negotiation` (reduced faction tariffs) — meaningful at faction borders

**Redesign:**
- `Bulk Trader` → **Cargo Mastery** (max 3): +10% cargo capacity per level. Tangible — you can haul more.
- `Commodity Specialist` → **Trade Instinct** (max 1): Specialty indicators (BUY HERE/SELL HERE) glow brighter and show estimated profit. Information upgrade.
- `Market Manipulation` → **Price Memory** (max 1): Galaxy map shows last-known prices for visited systems. Huge QoL, feels like growing expertise.

**Add:**
- **Insurance** (max 1): On combat defeat, keep 50% of cargo instead of losing all. Identity-defining safety net for trade-focused players.
- **Smuggler's Eye** (max 1): See legality status of all goods at a glance. Restricted/illegal items highlighted in market.
- **Black Market Connections** (max 2): +15%/+30% black market sell prices. For players who choose the shadow economy.

**Remove:**
- All 9 granular smuggling skills (contraband_slots through phantom). Replace with 2-3 meaningful smuggling skills folded into Commerce.
- `Supply Chain Mastery`, `Trade Magnate` — capstone stat bumps nobody feels.

### 2. COMBAT (streamline 30 → ~18, absorb Ground Combat)

**Identity**: The feared captain who dominates every engagement.

**Keep & Wire (Critical):**
- **Juggernaut Capstone**: Hull > 75% = crit immunity. Hull < 25% = +25% damage. WIRE THIS.
- **Sentinel Capstone**: Shields > 50% = double regen. Shield break = 20% restore. WIRE THIS.
- **Ghost Capstone**: First turn +30 evasion. Consecutive unhit = guaranteed crit. WIRE THIS.
- `Armor Expertise` (max 3) — already wired, keep
- `Shield Mastery` (max 3) — already wired, keep
- `Shield Regeneration` (max 2) — already wired, keep
- `Tactical Retreat` (flee bonus) — already wired, keep

**Redesign:**
- 15 separate weapon/elemental damage skills → **Weapon Specialization** (max 3): +10% damage with ALL weapons per level. Simple, felt immediately.
- 5 elemental bonus skills → **Elemental Affinity** (max 1): Elemental status effects last 1 additional turn. Meaningful in multi-round fights.
- `Attack Speed` → **Volley Commander** (max 1): Queue ONE extra action per combat turn. Game-changing. Identity-defining.
- `Crit Chance` → **Precision Strike** (max 2): +10% crit chance per level. Felt every fight.

**Add:**
- **Momentum Surge** (max 2): Start combat with 10/20 momentum. Faster access to crew abilities.
- **Battle Awareness** (max 1): See enemy intended action before choosing yours. Information advantage.

**Absorb from Ground Combat (select best):**
- **Ground Veteran** (max 2): +1 ground combat reroll per level. Already wired.
- **Battle Hardened** (max 1): +20% ground HP. Simple, effective.
- **Combat Scavenger** (max 2): +15% ground loot per level. Already wired.

**Remove:**
- All individual weapon-type skills (heavy_weapon_damage, ion_drain_bonus, etc.) — merge into Weapon Specialization
- All individual elemental skills (burn_damage_bonus per element) — merge into Elemental Affinity
- Ground-specific skills that duplicate space combat (ground momentum, ground last stand)
- `Endurance`, `Fortitude`, individual hull/damage reduction skills — fold into capstone paths

### 3. EXPLORATION (merge Exploration + some Gathering)

**Identity**: The navigator who knows every corridor and hidden route.

**Keep & Wire:**
- `Fuel Efficiency` (max 3): -10% fuel cost per level. Wire into `_calculate_fuel_cost()`.
- `Salvage Instinct` (max 2): +15% salvage yield per level. Wire into salvage results.

**Redesign:**
- `Stellar Cartography` → **System Intel** (max 2): Level 1: see danger level for unvisited systems. Level 2: see faction and economy type. Gateway skill — new information on the galaxy map.
- `Hazard Scanner` → **Safe Passage** (max 2): -15% encounter chance per level. Felt on every trip through dangerous space.
- `Long Range Scanner` → **Route Planner** (max 1): See fuel cost for ALL systems on galaxy map, not just selected. Massive QoL.
- `Explorer Reputation` → **Frontier Reputation** (max 2): +5 starting reputation with Frontier Alliance per level. Identity — you're known as an explorer.

**Add:**
- **Field Repairs** (max 2): Restore 5%/10% hull on system arrival. Reduces repair dependency.
- **Emergency Reserves** (max 1): Can never be fully stranded. Minimum 1 fuel after any jump.
- **Anomaly Sense** (max 1): Non-hostile encounter rate increased by 15%. More discovery, less combat.

**Remove:**
- `Travel Speed` — cosmetic, doesn't affect gameplay decisions
- `Trailblazer` (first visit bonus) — too niche to be a capstone
- `Map Reveal` — all systems are already visible

### 4. LEADERSHIP (refine)

**Identity**: The captain who inspires loyalty and commands respect.

**Keep & Wire:**
- `Crew Manager` (max 2): +1 crew slot per level. Already wired. Tangible.
- `Inspiring Leader` (max 2): +1 crew loyalty per trade. Already wired.
- `Crew Mentor` (max 2): +2 crew XP per event. Already wired.
- `Diplomatic Relations` (max 2): +1 faction rep per trade. Already wired.

**Redesign:**
- `Fleet Coordinator` → **Battle Commander** (max 2): Crew combat abilities deal +15%/+30% damage. Wire into combat engine.
- `Morale Officer` → **Unbreakable Bonds** (max 1): Crew loyalty never drops below 30 (minimum "Neutral"). Prevents companion departure.
- `Legendary Captain` → **Legend of the Expanse** (max 1): +2 crew slots AND crew quest stages unlock 10 loyalty earlier. True capstone — changes the crew experience.

**Add:**
- **Shared Experience** (max 2): +10%/+20% XP for the player from crew quest completions. Rewards investing in crew relationships.
- **Captain's Presence** (max 1): When you dock at a station, faction rep improves by +1 (once per visit). You're becoming someone people recognize.

**Remove:**
- `Veteran Command` (+2% XP from all sources) — invisible, unfelt
- `xp_gain_bonus` — same issue

### 5. SOCIAL (refine, ensure wired)

**Identity**: The diplomat who reads people and shapes conversations.

**Keep & Wire (CRITICAL — these must actually work):**
- `Silver Tongue` (max 2): +1 Persuasion level per level. MUST be wired into SocialManager.
- `Commanding Presence` (max 2): +1 Intimidation per level. MUST be wired.
- `Keen Insight` (max 2): +1 Observation per level. MUST be wired.
- `Empathic Read` (max 1): See NPC disposition + subtext. Already wired. Keep.
- `Master Negotiator` (max 1): Unlock special dialogue options. Already wired. Keep.
- `Cultural Savant` (max 2): +1 social checks in faction systems. MUST be wired.

**Redesign:**
- `Streetwise` → **Underworld Contacts** (max 1): Black market prices visible without visiting. Also: black market access at ALL stations (not just Crimson Reach). Gateway — opens a gameplay path.
- `Faction Diplomat` → **Faction Ambassador** (max 2): ALL faction rep gains doubled. Powerful for players who invest in relationships.
- `Voice of the Expanse` → **Peacemaker** (max 1): Non-hostile encounter option always available. Can talk your way out of ANY fight (with a high-difficulty social check). Capstone — identity-defining.

**Add:**
- **Read the Room** (max 1): Before choosing a dialogue response, see the disposition change it would cause (+5 or -3 shown on the response). Removes guesswork for social players.
- **Crew Whisperer** (max 1): Crew loyalty changes from dialogue choices are +50%. For players who care about their companions.

**Remove:**
- `Silver Lining` (+10% encounter outcomes) — too vague, unfelt
- Keep the tree focused on DIALOGUE and REPUTATION, not combat-adjacent bonuses

### 6. INDUSTRY (merge Mining + Refining from Gathering)

**Identity**: The industrialist who turns raw materials into wealth.

**Keep & Wire:**
- `Click Power` (max 3): +1 mining damage per click per level. Already wired. Tangible.
- `Passive Drill` (max 2): Mining speed bonus. Already wired.
- `Efficient Refining` (max 2): Refining speed bonus. Already wired.
- `Rich Veins` (max 2): Rare ore chance. Already wired.

**Redesign:**
- `Drone Efficiency` → **Drone Fleet** (max 3): Level 1: unlock basic drone. Level 2: drone mines faster. Level 3: two drones active. Each level is a visible change on screen.
- `Chain Reaction` → **Seismic Charge** (max 1): Breaking a rock has 20% chance to crack adjacent rocks. Visible, exciting.
- `Master Prospector` → **Ore Sense** (max 1): First rock each mining session is guaranteed rare quality. Removes frustration from bad RNG sessions.

**Add:**
- **Forge Mastery** (max 2): Refining yields +1 extra unit per batch per level. Tangible output increase.
- **Salvage Efficiency** (max 2): +1 extraction charge per level. More pulls per salvage session.
- **Material Science** (max 1): Unlock advanced refining recipes without finding schematics. Opens new crafting paths.

**Remove:**
- `Efficient Drills`, `Ore Targeting`, `Pressure Venting`, `Strip Miner` — tiny % bonuses nobody feels
- The 8 granular mining sub-skills that create an illusion of depth

---

## Summary: Before vs After

| Metric | Current | Proposed |
|--------|---------|----------|
| Trees | 9 | 6 |
| Total skills | 109 | ~85 |
| Total max levels | 215 | ~135 |
| Skills that DO something | 33 (31%) | ~85 (100%) |
| Orphaned skills | 73 (69%) | 0 |
| Points per level | 1 + milestones | 1 (clean) |
| Point cap | Level 40 | None |
| At level 40 | 48 pts, 22% completion | 40 pts, 30% completion |
| At level 100 | 48 pts, 22% completion | 100 pts, 74% completion |
| Identity defined by | Nothing (most skills invisible) | Every investment |

## Decision: 6 Trees Confirmed

User confirmed: merge to 6 trees. Cleaner design, every tree meaningful, real depth within each.

## Implementation Phases

### Phase S1: Define New Tree Structure
- Create the 6-tree skill definitions in progression.py
- Map each skill: id, name, description, tree, max_level, prerequisite, bonus_type, bonus_per_level
- Prerequisite chains within each tree (Tier 1 → Tier 2 → Tier 3/Capstone)
- Remove all deprecated skills from the old 9-tree structure
- Update SkillTreeType enum from 9 to 6 values
- Update save migration: convert old skill investments to nearest new equivalents

### Phase S2: Wire Every Skill
- Social: Silver Tongue/Commanding Presence/Keen Insight into SocialManager
- Social: Cultural Savant with system faction context
- Social: Peacemaker capstone (encounter peaceful resolution)
- Combat: Juggernaut/Sentinel/Ghost capstones into CombatEngine
- Combat: Weapon Specialization, Precision Strike, Elemental Affinity into damage calc
- Combat: Volley Commander (+1 queued action) into ActionQueue
- Commerce: Price Memory, Insurance, Black Market Connections
- Exploration: Fuel Efficiency, Safe Passage, System Intel, Emergency Reserves, Field Repairs
- Industry: Drone Fleet, Seismic Charge, Ore Sense, Forge Mastery, Material Science
- Leadership: Battle Commander, Unbreakable Bonds, Legend of the Expanse, Captain's Presence

### Phase S3: Point Economy Rebalance
- Remove SKILL_POINT_CAP_LEVEL (set to 999 or remove check entirely)
- Remove milestone bonus logic (clean 1 point per level)
- Update add_xp() to award exactly 1 point per level, always
- Update balance.json with new progression constants
- Update balance tests

### Phase S4: Skill Tree View UI Overhaul
- Redesign skill_tree_view.py for 6 trees instead of 9
- Tab layout: 6 tabs (Commerce, Combat, Exploration, Leadership, Social, Industry)
- Each tab shows a vertical skill tree with clear Tier 1 → 2 → 3 progression
- Skill nodes show: name, current/max level, bonus description, prerequisite line
- Color coding: faction-themed per tree (Commerce=blue, Combat=red, Exploration=green, Leadership=purple, Social=gold, Industry=amber)
- Show total points invested per tree in tab header
- Hover tooltip: full description + effect at current and next level
- Clear "CAPSTONE" visual treatment for Tier 3 identity skills
- Respect the layout.py shared constants and draw_utils for consistency

### Phase S5: Integration Testing
- Test every skill bonus is actually checked by its target system
- Test capstone effects in combat (Juggernaut/Sentinel/Ghost)
- Test social skills boost dialogue checks
- Test exploration skills affect fuel/encounter calculations
- Test commerce skills affect prices
- Test industry skills affect mining/refining outputs
- Test point economy at level 20/40/60/100
- Test save/load with new tree structure
- Test respec functionality with new trees

### Phase S6: Polish & Balance
- Playtest skill investments at key milestones
- Tune bonus magnitudes (are they felt? too strong? too weak?)
- Verify no dead investments remain (automated test)
- Update any tutorial hints that reference old tree names
- Update the cockpit HUD skill notification badge for new tree count

## Skill Tree View UI Design Notes

The current skill tree view supports 9 trees with 3 per row. With 6 trees, the layout improves:
- **2 rows of 3** or **1 row of 6 tabs** (horizontal tabs at top)
- Each tree has more horizontal space for skill node layout
- Vertical tree layout: root skills at top, capstones at bottom
- Branching: where a Tier 1 skill leads to 2 different Tier 2 options, show fork visually
- Invested skills: filled/glowing nodes vs. available-but-uninvested (outlined) vs. locked (dimmed)
- Connection lines between prerequisites (like a tech tree)

**Tree color scheme** (matching faction/theme associations):
- Commerce: Blue (trade, Guild-adjacent)
- Combat: Red/Orange (danger, aggression)
- Exploration: Teal/Cyan (space, navigation)
- Leadership: Purple (authority, wisdom)
- Social: Gold/Amber (charisma, warmth)
- Industry: Brown/Amber (earth, ore, forge)

## Files Affected

**Core restructure:**
- `spacegame/models/progression.py` — Complete skill redefinition (~1,400 lines, major rewrite)
- `spacegame/config.py` — SkillTreeType enum, SKILL_POINT_CAP_LEVEL removal

**Wiring (each skill connects to its system):**
- `spacegame/models/social.py` — Social tree skills
- `spacegame/models/combat_engine.py` — Combat capstones + weapon skills
- `spacegame/models/encounter.py` — Exploration encounter reduction
- `spacegame/views/galaxy_map_view.py` — Fuel efficiency, system intel
- `spacegame/views/trading_view.py` — Commerce skills
- `spacegame/models/mining.py` — Industry mining skills
- `spacegame/models/crew.py` — Leadership crew skills
- `spacegame/models/action_queue.py` — Volley Commander extra action

**UI:**
- `spacegame/views/skill_tree_view.py` — Major UI redesign for 6 trees
- `spacegame/views/character_view.py` — Tree color associations

**Tests:**
- `tests/test_models/test_progression.py` — New tree structure tests
- `tests/test_models/test_social.py` — Social wiring tests
- `tests/test_models/test_combat_engine.py` — Combat capstone tests
- `tests/test_models/test_balance.py` — Point economy tests
