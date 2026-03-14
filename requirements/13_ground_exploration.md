# Ground Exploration System

## Document Overview

Ground exploration is a **turn-based, stealth-first, grid-based roguelike exploration system** that gives the player on-foot gameplay in station interiors, mining tunnels, planetary surfaces, and hostile facilities. It is mechanically distinct from space combat — where combat rewards aggression and resource management, ground exploration rewards **patience, observation, and preparation.**

The core fantasy: **you are vulnerable here.** In space, you have a ship — weapons, shields, engines. On the ground, you're a person in a place that isn't yours. The primary mechanic is navigating without being caught, not fighting your way through.

Ground exploration serves two roles:
1. **Campaign missions**: Hand-authored maps tightly integrated with the story (Breakstone tunnels, Crimson Reach interior, pirate base infiltration)
2. **Repeatable content**: Procedurally generated maps providing a sustainable gameplay loop with unique rewards, contracts, and progression

> **Implementation Status** (Updated 2026-03-10): PHASES A-E COMPLETE, PHASE F REMAINING
>
> - **Phase A (Grid Foundation)**: COMPLETE — GroundMap model, 13 tile types, fog of war, scrolling viewport, GroundExplorationView
> - **Phase B (Stealth Core)**: COMPLETE — Enemy patrols, facing/vision cones, 4 detection states, noise system, alert decay
> - **Phase C (Ground Combat)**: COMPLETE — 1d6+modifier exchanges, fight/retreat/talk, social skill integration, 8 enemy templates
> - **Phase D (Crew & Attributes)**: COMPLETE — GroundCrewBonuses, 4 crew abilities, attribute modifiers (ACU/RES/COM/SYN), loot system
> - **Phase E (Procedural Generation)**: COMPLETE — 8 chunk templates with interior features, room-placement + corridor-carving, 4 difficulty tiers, 5 mission types, faction enemy pools, deterministic seeding, 62 mapgen tests
> - **Phase F (Content & Polish)**: NOT STARTED — Briefing/result views, campaign maps, repeatable contracts, ground loot/equipment, minimap polish, achievements
> - Prerequisite for Campaign Act One Chapters 3-5 (Missions 08-17)
> - See `11_implementation_roadmap.md` for phasing

---

## 1. Grid System & Map Structure

### 1.1 Map Dimensions

- **Baseline map size**: 20x25 tiles (width x height)
- **Large maps**: Up to 30x30 tiles for complex campaign missions or high-difficulty repeatable content
- **Multi-phase maps**: Campaign missions may chain 2-3 separate maps in sequence (e.g., "Enter station → Navigate tunnels → Reach contact"). Each phase is its own grid with a transition between them
- Maps are **scrollable** — the viewport shows a portion of the map, centered on the player, and scrolls as the player moves

### 1.2 Viewport

- The viewport displays a region of the map that fits the game window (exact tile count depends on tile size and screen resolution — target ~15x12 visible tiles at a time)
- The camera follows the player with smooth scrolling (lerp toward player position, not snapping)
- A **minimap** in the corner shows the full map with fog of war state — explored areas visible, unexplored areas dark, player position marked, detected enemies shown as dots

### 1.3 Tile Types

Each tile has a **type** that determines movement, visibility, and interaction:

| Tile Type | Walkable | Blocks Vision | Notes |
|-----------|----------|---------------|-------|
| Floor | Yes | No | Standard traversable tile |
| Wall | No | Yes | Impassable, blocks line of sight |
| Door (unlocked) | Yes | Yes (when closed) | Can be opened. Closed doors block vision. Opening a door costs 1 turn and may generate noise |
| Door (locked) | No | Yes | Requires a key item, crew ability (Marcus), or ING attribute check to open |
| Cover (half-wall, crate) | Yes | Partially | Provides stealth bonus when adjacent. Enemies have reduced detection range toward tiles behind cover |
| Hazard | Yes | No | Environmental danger — steam vents, unstable ground, radiation, toxic atmosphere. Deals damage or applies debuff when stepped on unless mitigated (RES attribute, Priya's crew ability) |
| Interactable | Yes | No | Terminal, control panel, container, data node. Can be activated for effects (disable cameras, unlock doors, loot, intel) |
| Dark floor | Yes | No | Reduced visibility for player AND enemies. Player vision radius reduced by 1-2 tiles, but enemy detection range also reduced. Tradeoff: shadows are safe but blind |
| Noisy floor | Yes | No | Metal grating, gravel, debris. Moving onto this tile generates noise that can alert nearby enemies |
| Exit | Yes | No | Mission extraction point. Standing on this tile and choosing "Extract" ends the mission with current rewards |
| Entrance | Yes | No | Where the player starts. Also serves as an emergency extraction point (but may be blocked in some missions) |
| Hidden passage | No (until revealed) | Yes | Appears as a wall until discovered (ACU check, Tomas crew ability, or specific interactable). Once revealed, becomes a floor tile connecting to an alternate route |

### 1.4 Tile Rendering

- Each tile type has a distinct visual appearance that varies by **faction aesthetic** (see Section 11)
- Explored but not currently visible tiles are rendered at reduced brightness (fog of war dimming)
- Unexplored tiles are fully dark/hidden
- Interactable tiles have a subtle pulsing highlight when within the player's vision radius
- Hazard tiles have animated effects (steam particles, flickering radiation glow)

---

## 2. Turn System & Movement

### 2.1 Turn Structure

Ground exploration is **strictly turn-based**. Each turn:

1. **Player acts**: Move one tile in any cardinal direction (no diagonals), interact with an adjacent tile, use an ability, or wait (skip turn)
2. **Enemies act**: Each enemy takes their turn in sequence — move along patrol route, investigate suspicious activity, or pursue the player
3. **Environment updates**: Hazard timers tick, temporary effects expire, door states update

The player always acts first each turn. This gives the player agency to react to what they see before enemies move.

### 2.2 Player Actions (One Per Turn)

- **Move**: Step one tile in a cardinal direction (up/down/left/right). Moving onto noisy floor tiles generates noise.
- **Wait**: Skip your turn. Enemies still move. Useful for timing patrol gaps.
- **Interact**: Activate an adjacent interactable tile (terminal, container, control panel). Some interactions take 1 turn, some take multiple turns (e.g., hacking a terminal: 2-3 turns of standing still, vulnerable).
- **Open door**: Open an adjacent closed door. Costs 1 turn. May generate noise (faction-dependent — Guild doors are quiet, Alliance salvaged doors are loud).
- **Use crew ability**: Activate the ground ability of a crew member you brought (see Section 7). Some abilities are instant (don't cost a turn), some cost a turn.
- **Extract**: When standing on an exit tile, choose to leave the mission. Ends the ground exploration with current rewards.

### 2.3 Movement Rules

- No diagonal movement (cardinal only) — keeps pathfinding simple and patrol patterns readable
- The player cannot move through enemies or walls
- Moving into a tile occupied by an unaware enemy from behind could be a future mechanic (takedown), but for the initial implementation, enemies block movement
- Sprint: The player can optionally **sprint** (move 2 tiles in one turn in the same direction), but sprinting generates noise equivalent to stepping on a noisy tile. Useful for dashing across open areas.

### 2.4 Enemy Turn Frequency

Not all enemies act every turn. Each enemy has a **speed value**:

- **Speed 1 (Standard)**: Acts every turn. Most guards, patrol units.
- **Speed 2 (Slow)**: Acts every other turn. Heavy guards, automated turrets (rotate slowly), workers who aren't really guards.
- **Speed 0.5 (Fast)**: Acts every turn AND gets a second move on even-numbered turns. Elite guards, pursuit mode enemies. Rare, used for high-difficulty content.

This provides a natural difficulty gradient — easier maps have more Speed 2 enemies with readable, slow patterns. Harder maps have Speed 1 and Speed 0.5 enemies that demand tighter play.

---

## 3. Fog of War & Vision

### 3.1 Fog States

Each tile exists in one of three visibility states:

- **Unexplored**: Never seen. Rendered as fully dark. The player doesn't know what's there.
- **Explored**: Previously seen but not currently in vision range. Rendered dimmed. Shows tile type and last-known state (a guard was *here* last time you could see, but may have moved). Does NOT update enemy positions in real time.
- **Visible**: Currently within the player's vision radius and line of sight. Fully lit. Shows real-time enemy positions, item states, hazard effects.

### 3.2 Vision Radius

- **Base vision radius**: 5 tiles in all directions from the player
- **ACU (Acuity) bonus**: +1 tile radius per 2 ACU points (so ACU 4 = 7 tile radius)
- **Dark tiles**: Reduce effective vision radius by 2 tiles when looking *through* dark areas
- **Elena crew bonus**: +1 vision radius when Elena is in the party
- Vision is blocked by walls and closed doors — no seeing through solid objects

### 3.3 Line of Sight

Vision follows **line of sight** rules:

- Draw a line from the player tile to the target tile
- If the line passes through any wall or closed door tile, the target is not visible
- Cover tiles partially block line of sight — tiles directly behind cover (from the player's perspective) are not visible unless the player is adjacent to the cover
- This means corners are meaningful — you can't see around a corner until you step out, and neither can enemies

### 3.4 Enemy Vision

Enemies also have vision, used for detection (see Section 4):

- **Enemy vision range**: Defined per enemy type (typically 4-6 tiles)
- **Enemy vision cone**: Enemies face a direction and have a ~90-degree forward vision cone, not full 360-degree awareness
- Enemies rotate their facing as they patrol, creating predictable windows of opportunity
- Enemies cannot see through walls, closed doors, or around corners (same rules as player)
- Cover reduces enemy detection range by 2 tiles when the player is behind cover relative to the enemy

---

## 4. Stealth & Detection

### 4.1 Detection States

The mission has a global **alert level** that escalates:

| State | Description | Enemy Behavior |
|-------|-------------|----------------|
| **UNDETECTED** | Nobody knows you're here | Enemies follow patrol routes at normal speed |
| **SUSPICIOUS** | Something was noticed | Nearest enemy investigates the noise/sighting location. Other enemies continue patrol but face toward the disturbance. 5-turn timer to return to UNDETECTED if nothing else happens |
| **ALERT** | You've been spotted | All enemies in the area actively search. Patrol routes become wider. Reinforcement enemies may spawn at entry points. Does not decay — must break line of sight for 8 turns to drop to SUSPICIOUS |
| **COMBAT** | Direct engagement | Grid-native combat triggered (see Section 5). Other nearby enemies converge on combat location |

### 4.2 Detection Triggers

- **Sight**: An enemy's vision cone covers the player's tile while in UNDETECTED or SUSPICIOUS state → escalate to ALERT. If the player is behind cover, the enemy must be within half their normal vision range to detect.
- **Noise**: The player generates noise (opening a door, stepping on noisy tile, sprinting, failing an interaction check). Noise has a radius (typically 3-5 tiles). Any enemy within the noise radius enters SUSPICIOUS and moves toward the noise source.
- **Failed interaction**: Failing a skill check on a terminal or locked door generates noise and may trigger an alarm (faction-dependent — Guild terminals alert security, Alliance junk just makes a loud clang).
- **Body discovery**: (Future mechanic) If takedowns are added, enemies finding an unconscious guard would escalate to ALERT.

### 4.3 Noise System

Actions have a **noise value** (radius in tiles):

| Action | Noise Radius |
|--------|-------------|
| Normal movement on floor | 0 (silent) |
| Movement on noisy floor | 3 tiles |
| Sprint | 4 tiles |
| Open unlocked door | 2 tiles (faction-dependent: Guild 1, Alliance 3) |
| Force locked door | 5 tiles |
| Interact with terminal (success) | 1 tile |
| Interact with terminal (failure) | 4 tiles |
| Combat | 6 tiles (alerts everyone nearby) |

**Crew noise modifiers**:
- Tomas: -1 to all noise radii (minimum 0)
- Marcus: Door opening noise reduced to 0 (engineer knows how to work mechanisms quietly)

**Attribute noise modifiers**:
- ING (Ingenuity): -1 to interaction noise at ING 4+

### 4.4 Enemy Patrol Behavior

Enemies in UNDETECTED state follow **patrol routes** — predefined paths they walk along, repeating in a loop. Each patrol route is a sequence of tiles with optional **pause points** (the guard stops and faces a direction for 1-2 turns before continuing).

- Patrol routes are visible to the player once the enemy has been observed (shown as faded footprint dots on explored tiles, so the player can learn the pattern)
- Patrol routes are designed per-map (hand-authored) or per-template-chunk (procedural) to create navigable timing windows
- **ACU bonus**: At ACU 3+, patrol routes are revealed 2 turns ahead (you can see where the guard *will be*). At ACU 5, full patrol route is revealed on first sighting.
- **Elena bonus**: Patrol routes fully revealed on first sighting when Elena is in party

### 4.5 Breaking Detection

- **SUSPICIOUS → UNDETECTED**: If no new noise/sighting occurs for 5 turns, enemies return to patrol. Timer resets on any new trigger.
- **ALERT → SUSPICIOUS**: Player must break line of sight with ALL alert enemies for 8 consecutive turns. Enemies search the player's last known position and nearby rooms. After 8 turns without re-sighting, they drop to SUSPICIOUS and begin returning to patrol routes.
- **COMBAT → ALERT**: Combat ending (enemies defeated, player retreats to break line of sight, or player talks their way out) drops to ALERT. Remaining enemies stay on heightened alert for the rest of the mission.

---

## 5. Ground Combat — "Dice & Grit"

### 5.1 Design Philosophy

Ground combat is a **fast, high-stakes, dice-driven system** that resolves on the exploration grid. It is intentionally simplified compared to space combat — getting caught should feel like a tense, scrambled consequence, not a strategic set piece. The entire combat should resolve in 15-30 seconds.

Key identity differences from space combat:

| Space Combat | Ground Combat |
|---|---|
| Separate combat screen | Happens on the exploration grid |
| 5+ moves with cooldowns and energy costs | Attack or defend, modified by dice |
| Health bars, shield bars, energy bars | HP pips above sprites |
| Phase-driven state machine (7 phases) | Quick exchange rounds |
| Strategic, planned engagement | Frantic, consequential |
| Full visual effects suite | Compact dice animation + tile-local particles |

### 5.2 Combat Flow

When COMBAT state triggers:

1. **Engagement panel** overlays the bottom portion of the exploration view (the grid remains visible above)
2. All engaged enemies (within 2 tiles of the player when combat starts) are pulled into the encounter
3. Combat resolves as a series of **exchanges** — one exchange per round
4. After each exchange, the player chooses: **Continue Fighting**, **Attempt Retreat**, or **Try Talking**
5. Combat ends when:
   - All enemies are defeated (HP → 0)
   - Player successfully retreats (breaks engagement)
   - Player successfully talks their way out
   - Player HP → 0 (failure consequences apply, see Section 10)

### 5.3 The Exchange (Core Mechanic)

Each exchange resolves as simultaneous rolls:

- **Player rolls**: `1d6 + attack_modifier`
- **Enemy rolls**: `1d6 + defense_modifier`
- **Compare results**:
  - Player total > Enemy total: Player deals damage = difference (minimum 1)
  - Enemy total > Player total: Enemy deals damage = difference (minimum 1)
  - Tie: Glancing blow — 1 damage to both

If multiple enemies are engaged, the player rolls once against each enemy in sequence. The player can choose which enemy to target each exchange (focus fire or spread damage).

### 5.4 Stats

**Player ground combat stats:**
- **HP**: Base 8. Modified by RES (+1 per 2 RES points) and skills.
- **Attack modifier**: Base +0. Modified by ACU (+1 per 2 ACU points), skills, and crew.
- **Defense modifier**: Base +0. Modified by RES (+1 per 2 RES points), skills, and crew.
- **Shield**: Optional equipment. Absorbs the first N damage total (not per hit). Depletes over the mission, not per combat. Found as ground loot or purchased.

**Enemy ground combat stats (4 values):**

| Enemy Type | HP | Attack | Defense | Talk Difficulty |
|---|---|---|---|---|
| Guild Security | 4 | +2 | +2 | 6 |
| Union Worker | 3 | +1 | +0 | 4 |
| Pirate Thug | 5 | +3 | +0 | 8 |
| Collective Drone (automated) | 3 | +1 | +3 | ∞ (can't talk to robots) |
| Alliance Scrapper | 4 | +2 | +1 | 5 |
| Elite Guard | 6 | +3 | +3 | 9 |
| Station Sentry (automated) | 2 | +0 | +1 | ∞ |
| Crimson Enforcer | 5 | +3 | +1 | 7 |

### 5.5 Special Mechanics

**Critical Hits**: Natural 6 on the attack die = critical hit. Double damage. Enemy staggers and skips their next attack exchange. Occurs ~17% of the time — satisfying and impactful.

**Shields**: Flat damage absorption pool that depletes over the entire ground mission (not just one combat). Player can find or equip a personal shield module (e.g., "Light Shield Generator — absorbs 4 damage"). Some elite enemies also have shields.

**Re-rolls**: The Quick Reflexes skill and rare ground loot items grant re-rolls — reject a bad die result and roll again, keeping the new result. Limited uses per combat (typically 1-2). Strategic decision: burn it now or save it?

**Momentum Combo**: Win 2 consecutive exchanges → third exchange gets +2 attack bonus. Rewards sustained aggression without guaranteeing a snowball.

**Outnumbered Penalty**: -1 to player attack and defense per enemy beyond the first. Fighting 3 enemies at once is genuinely dangerous — incentivizes stealth or picking fights carefully.

**Ambush Bonus**: If the player detects an enemy before being detected and chooses to initiate combat (e.g., approaches from behind), the first exchange grants +3 attack and the enemy doesn't get a defense roll. Rewards tactical aggression.

**Disadvantaged Start**: If combat triggers because the player was caught in the open (no adjacent cover tiles), -2 to the first exchange. Being spotted in a corridor is worse than being spotted near crates.

### 5.6 Retreat

After any exchange, the player can attempt to retreat:

- **Retreat roll**: `1d6 + retreat_modifier` vs difficulty (base 4, +1 per engaged enemy)
- **Elena bonus**: +2 to retreat rolls (she knows the way out)
- **Sprint skill**: +1 to retreat rolls
- **Cornered**: If the player has no adjacent empty tiles (boxed in), retreat is impossible
- **Success**: Player disengages. Combat ends. Alert state drops to ALERT (not UNDETECTED). Player can continue exploring or extract.
- **Failure**: Costs one exchange — each enemy gets a free attack (the player tried to run and got hit). Can attempt retreat again next exchange.

### 5.7 Talk Your Way Out

After any exchange, the player can attempt to talk:

- **Talk roll**: `1d6 + social_skill_modifier + crew_talk_bonus` vs enemy's Talk Difficulty
- **Social skill used**: Player chooses which social skill to apply:
  - **Persuasion**: "This isn't worth your pay." Better against hired guards and workers.
  - **Intimidation**: "Walk away." +2 bonus if the player has already defeated at least one enemy this combat.
  - **Observation**: "Your boss doesn't pay you enough for this." Better with high ACU — you read the situation.
- **SYN (Synergy) bonus**: +1 per 2 SYN points
- **Tomas bonus**: +2 to all talk attempts
- **Success**: Enemies disengage. Player can continue exploring at ALERT state or extract.
- **Failure**: Costs one exchange (enemies attack while you're talking). Cannot attempt the *same* social skill again this combat (but can try a different one — up to 3 attempts total if all three skills are available).
- **Automated enemies** (drones, sentries): Talk difficulty ∞ — cannot be talked to. The button is grayed out with a tooltip explaining why.
- **Multiple enemies**: Talk difficulty is the *highest* among engaged enemies. Convince the toughest and the rest fall in line.

---

## 6. Ground Combat Skills

A small, focused set of skills that let the player invest in ground combat effectiveness. These can be added as nodes on an existing skill tree (Leadership or Social) or as a new mini-tree.

### 6.1 Skill Nodes

| Skill | Level Req | Prerequisite | Effect |
|---|---|---|---|
| **Scrapper** | 1 | None | +1 to ground attack rolls |
| **Tough Hide** | 1 | None | +2 max HP on ground missions |
| **Quick Reflexes** | 2 | Scrapper OR Tough Hide | Once per ground combat, re-roll any one of your dice |
| **Intimidating Presence** | 3 | Quick Reflexes | First exchange in any ground combat, enemy rolls at -2 |
| **Last Stand** | 3 | Tough Hide | When below 25% HP, +3 to all rolls (attack and defense) |
| **Veteran** | 4 | Intimidating Presence AND Last Stand | +1 re-roll per combat, +1 max HP |

Six skills total — small investment for meaningful returns. A fully specced ground combat player has +1 attack, +3 HP, 2 re-rolls per combat, enemy debuff on first exchange, and a clutch comeback mechanic.

### 6.2 Attribute Integration Summary

| Attribute | Ground Exploration Effect | Ground Combat Effect |
|---|---|---|
| **COM (Commerce)** | Find more/better loot in containers, identify valuable salvage | — |
| **ACU (Acuity)** | +1 vision radius per 2 pts, reveal patrol routes earlier, spot hidden passages | +1 attack per 2 pts |
| **RES (Resolve)** | Resist environmental hazards, more turns in toxic/hot areas | +1 defense per 2 pts, +1 HP per 2 pts |
| **ING (Ingenuity)** | Interact with machinery without crew, bypass simple locks, -1 interaction noise at 4+ | — |
| **SYN (Synergy)** | Better social checks at ground NPC encounters | +1 talk roll per 2 pts |

---

## 7. Crew Ground Abilities

The player selects **1-2 crew members** before entering a ground mission. Crew choice is a strategic pre-mission decision — who you bring fundamentally changes how you navigate.

### 7.1 Crew Ability Details

**Elena Reeves (Navigator)**
- **Pathfinder**: +1 vision radius. Patrol routes fully revealed on first enemy sighting.
- **Quick Exit**: +2 to retreat rolls during ground combat.
- **Ground identity**: She sees the map. Brings awareness and escape options.

**Marcus Jin (Engineer)**
- **Bypass**: Can hack locked doors and terminals without a skill check. Interaction takes 1 turn instead of 2-3.
- **Silent Entry**: Door opening noise reduced to 0.
- **Ground identity**: He opens paths. Locked doors and secured terminals aren't obstacles.

**Priya Osei (Scientist)**
- **Hazard Scan**: Environmental hazards are revealed 3 tiles before you reach them (even through fog of war). Stepping on revealed hazards deals half damage.
- **Analyze Weakness**: Once per ground combat, identify an enemy's weakness — +3 to one attack roll.
- **Ground identity**: She protects you from the environment and gives you an edge in combat.

**Tomas Drifter (Trader/Drifter)**
- **Light Feet**: -1 to all noise radii (minimum 0). Noisy floor tiles only generate noise radius 2 instead of 3.
- **Street Smarts**: +2 to all talk attempts during ground combat. Can sometimes reveal hidden passages (chance on entering a new room).
- **Ground identity**: He's quiet and connected. The stealth crew pick.

### 7.2 Crew Selection Constraints

- Minimum 0 crew, maximum 2 crew per ground mission
- Going solo has no inherent bonus — it's just harder. Some missions may require or suggest specific crew.
- Crew members brought on ground missions earn **crew XP** (same as existing crew XP system)
- Campaign missions may have crew-specific dialogue or alternate paths (e.g., Marcus vouches for you at Union security in Mission 13)

---

## 8. Reward Structure & Voluntary Extraction

### 8.1 Loot

Ground missions contain **lootable containers** scattered through the map. Containers hold:

- **Credits**: Direct currency reward
- **Commodities**: Ground-exclusive items or standard trade goods. Some are high-value and can only be obtained on the ground.
- **Intel data**: Faction intelligence that can be sold for reputation or credits
- **Equipment**: Personal shield modules, noise dampeners, vision enhancers — ground-specific gear that modifies exploration stats
- **Key items**: Campaign-specific items needed for mission objectives

Loot is revealed when the player interacts with a container (1 turn). Higher COM attribute = better quality rolls on loot tables.

### 8.2 Voluntary Extraction (Retreat)

At any time during exploration (not during combat), the player can move to an **exit tile** and choose to extract. This ends the mission immediately.

- The player **keeps all loot collected so far**
- If the mission has objectives, incomplete objectives are failed — but loot is retained
- This creates a **push-your-luck tension**: "I have good loot, but the objective is deeper in. Do I risk it?"
- Campaign missions with mandatory objectives cannot be extracted from early (the exit tile doesn't appear until the objective is complete, or extraction counts as mission abandonment)

### 8.3 Repeatable Mission Rewards

For procedurally generated ground missions (non-campaign), rewards scale with depth/difficulty:

- **Contracts**: Time-limited missions posted at stations. "Retrieve data core from Guild warehouse on Nexus Prime. Reward: 800 CR + Guild rep." Generated procedurally with faction, location, difficulty, and reward.
- **Rare ground-exclusive loot**: Items, commodities, and equipment that cannot be obtained through trading, mining, or salvage. Incentivizes ground play as its own loop.
- **Crew XP**: Ground missions award XP to crew members brought along.
- **Achievements/milestones**: Discover X rooms, complete Y ground missions, extract without detection Z times, defeat N enemies on the ground.

---

## 9. Procedural Map Generation

### 9.1 Template-Chunk System

Rather than pure random generation (which produces bland, samey layouts), ground maps are assembled from a library of **hand-authored chunks** stitched together with controlled variation.

**Chunk size**: 8x8 or 10x10 tiles — large enough to be a meaningful room or corridor section, small enough to combine in many configurations.

**Chunk categories**:
- **Room templates**: Security checkpoint, storage bay, mess hall, lab, office, cargo hold, docking bay, living quarters, server room, workshop, cantina, med bay
- **Connector templates**: Straight corridor, L-bend, T-junction, crossroads, elevator shaft (vertical connector between phases), airlock
- **Special templates**: Vault (high-reward room behind locked door), NPC encounter room, environmental hazard zone, hidden passage connector, dead end with loot

### 9.2 Generation Algorithm

A procedural map is built by:

1. **Select mission parameters**: Mission type (infiltration, retrieval, sabotage, exploration), faction, difficulty tier, map size
2. **Place anchor points**: Entry tile and objective room(s) at appropriate distance
3. **Generate critical path**: Connect entry to objective using connector and room chunks, ensuring a navigable route exists
4. **Branch alternate routes**: Add side paths, shortcuts (behind locked doors or hidden passages), and optional rooms with loot
5. **Place hazards and obstacles**: Environmental hazards, locked doors, noisy floor sections along both critical and alternate paths
6. **Populate enemies**: Place patrol routes based on difficulty tier. Higher difficulty = more enemies, faster patrol speed, tighter patrol patterns
7. **Place loot**: Distribute containers with rewards scaled to difficulty and distance from entry (deeper = better loot)
8. **Apply faction skin**: Swap tile art, enemy types, door noise values, hazard types, and ambient details to match the faction aesthetic (see Section 11)

### 9.3 Mission Types

| Type | Objective | Design Focus |
|---|---|---|
| **Infiltration** | Reach a specific room and interact with a target (terminal, NPC, object) | Navigation, stealth, patrol timing |
| **Retrieval** | Find and extract a specific item from a container deep in the map | Exploration, loot identification, extraction tension |
| **Sabotage** | Interact with 2-3 targets spread across the map (disable generators, plant devices) | Multi-objective routing, time pressure |
| **Exploration** | Reveal X% of the map and extract | Coverage, risk management, push-your-luck |
| **Extraction** | Escort an NPC from deep in the map to the exit | Pathfinding for two, NPC moves with you (slower), protection |

### 9.4 Difficulty Tiers

| Tier | Enemy Count | Enemy Speed | Patrol Density | Loot Quality | Map Size |
|---|---|---|---|---|---|
| **Low** | 3-5 | Mostly Speed 2 | Wide gaps between patrols | Standard | 15x20 |
| **Moderate** | 5-8 | Mix of Speed 1 and 2 | Moderate gaps, some overlap | Good | 20x25 |
| **High** | 8-12 | Mostly Speed 1, one Speed 0.5 | Tight gaps, overlapping routes | Excellent | 25x30 |
| **Extreme** | 10-15 | Speed 1 with multiple Speed 0.5 | Minimal gaps, requires crew abilities | Rare/exclusive | 30x30 |

---

## 10. Failure Consequences

### 10.1 The Consequence Curve

Failure severity follows a **bell curve** based on mission progress — not a flat penalty. This prevents punishing new players too harshly while still making mid-mission failure meaningful.

**Progress** is measured as the percentage of distance from entry to the primary objective (or percentage of objectives completed for multi-objective missions).

```
Penalty Severity
     ▲
     │        ╱‾‾‾╲
     │       ╱      ╲
     │      ╱        ╲
     │     ╱          ╲
     │────╱            ╲────
     └───────────────────────► Progress
     0%   15%  40%  65%  85% 100%
```

| Progress | Zone | Penalty |
|---|---|---|
| 0-15% | **Grace** | Minimal. Lose 5% of carried credits. Ejected from the mission. "You barely got in before getting chased out." |
| 15-40% | **Escalating** | Moderate. Lose 10-15% of credits + drop most loot collected so far. |
| 40-65% | **Commitment** | Full penalty. Lose 15-20% of credits + drop ALL loot collected + small XP penalty. "You were deep in and it cost you." |
| 65-85% | **Easing** | Moderate. Lose 10% of credits, keep half of collected loot. You earned some of that. |
| 85-100% | **So close** | Light. Lose 5% of credits, keep most loot. The failure stings but you almost had it. |

### 10.2 Stealth-Mandatory Missions

Some campaign missions require the player to remain undetected. In these missions:

- Detection state reaching ALERT = **mission failure**
- Player is returned to the start of the current **phase** (not the entire multi-phase mission)
- No credit or loot penalty — the consequence is the retry itself
- After 3 failures on the same phase, the game may offer a hint or reduce patrol density slightly (accessibility)

### 10.3 Player HP Depletion

If the player's HP reaches 0 during ground combat:

- Combat ends immediately
- The consequence curve penalties apply based on current progress
- The player is ejected from the mission (narratively: you're dragged out, escape wounded, get thrown out by guards)
- Player HP resets after leaving the ground mission (ground HP is separate from any ship-level state)
- No permanent death — ground missions are repeatable content, not save-ending events

---

## 11. Faction Aesthetics & Map Flavor

### 11.1 Faction-Specific Environments

Each faction provides a distinct visual and mechanical feel for ground maps:

**Merchants Guild**
- **Visual**: Clean corridors, polished floors, holographic signage, color-coded departments. Uniform lighting.
- **Security style**: Cameras, locked doors, professional patrol routes. High-tech but rigid — exploitable patterns.
- **Unique tile**: Security camera (interactable — can be disabled by Marcus or high ING). Has a vision cone that detects the player like an enemy but doesn't move.
- **Door noise**: Low (1). Guild doors are well-maintained.
- **Hazards**: Rare. Guild stations are safe environments. Occasional laser grid that cycles on/off.
- **Feel**: Orderly and predictable. Learn the pattern, exploit the pattern.

**Miners Union**
- **Visual**: Exposed conduit, rough-cut stone (in mines), hand-painted murals, heavy structural supports. Dim in tunnels, bright in communal areas.
- **Security style**: Fewer formal guards, more workers who might notice you. Dense NPC presence in communal areas.
- **Unique tile**: Machinery (creates ambient noise that masks player noise within 2 tiles — can use machinery as noise cover).
- **Door noise**: Medium (2). Functional, not fancy.
- **Hazards**: Common. Steam vents, unstable ground in mines, heavy equipment zones. RES checks to push through.
- **Feel**: Lived-in and unpredictable. Lots of NPCs but fewer formal patrols. Social skills help.

**Science Collective**
- **Visual**: Sterile hallways, smooth surfaces, color-coded safety zones, optimized lighting. Clinical beauty.
- **Security style**: Fewer guards but more automated systems — drones, sensors, sealed containment zones. Automated enemies can't be talked to.
- **Unique tile**: Sensor array (detects movement within 3 tiles, triggers SUSPICIOUS if tripped. Can be disabled at a terminal).
- **Door noise**: Low (1). Precision engineering.
- **Hazards**: Frequent and dangerous. Radiation zones, chemical spills, containment breaches. Priya's hazard scan is extremely valuable here.
- **Feel**: Sterile and hostile to the unprepared. Environmental mastery matters more than social skills.

**Frontier Alliance**
- **Visual**: Eclectic materials, welded hull plates, hand-carved panels, salvaged equipment painted in bright colors. No two rooms look alike.
- **Security style**: Informal, unpredictable. Guards don't follow rigid patrols — they wander. But there are many hiding spots and alternate routes.
- **Unique tile**: Salvage pile (can be searched for improvised items — noise dampener, lockpick, etc. One-time use).
- **Door noise**: High (3). Salvaged doors are loud.
- **Hazards**: Moderate. Jury-rigged electrical systems, unstable flooring. Unpredictable but not as dangerous as Collective hazards.
- **Feel**: Chaotic but exploitable. Lots of cover, lots of hidden passages, but guards are erratic.

### 11.2 Planetary Surface Maps

In addition to station interiors, some missions take place on **planetary surfaces**:

- **Visual**: Open terrain, sky backdrop, weather effects (dust storms, rain, fog)
- **Security style**: Perimeter patrols, watchtowers (elevated enemies with larger vision radius)
- **Unique considerations**: Larger open spaces with less cover. Weather can affect visibility (fog reduces everyone's vision, dust storms create noise cover). Day/night cycle within the mission (some maps start in darkness and dawn approaches — adding time pressure).
- **Hazards**: Environmental. Extreme heat, cold, toxic atmosphere. RES checks, limited exposure time.

### 11.3 Flavor Text (Briefing)

Before entering any ground mission, the player sees a **briefing panel**:

- **Title**: Mission name or ground site name
- **Atmospheric text**: 2-4 sentences setting the scene. For campaign missions, this is hand-written narrative prose. For procedural missions, assembled from faction + location type + mission type sentence fragments.
- **Objectives**: Clear bullet list of what needs to be done
- **Intel**: Optional hints based on player's ACU or Observation skill ("Guards rotate on a 6-turn cycle", "The east wing has a maintenance shaft", "Automated defenses detected — social resolution will be limited")
- **Crew selection**: Choose which crew to bring (with a summary of each crew member's ground abilities)

---

## 12. Campaign Integration

### 12.1 Campaign Ground Missions

The following campaign missions (from `campaign_act_one.md` and `act_one_narrative.md`) require ground exploration:

**Mission 10 — The Crimson Run** (Crimson Reach station interior)
- Type: Infiltration (reach Malia Torres in her workshop)
- Hand-authored map of Wrecker's Outpost: docking bay → market corridor → workshop bay
- Light security, more about atmosphere and world-building
- Difficulty: Low. Introduction to ground exploration mechanics.

**Mission 13 — The Favor Returned** (Breakstone mining tunnels)
- Type: Infiltration (navigate tunnels, find Oren Tak)
- Hand-authored map: Union security checkpoint → mining tunnels → deep tunnels
- Union workers as primary NPCs, speech checks at checkpoints
- Marcus companion path: vouches for you, skips security checks
- Difficulty: Moderate. First real stealth challenge with patrol timing.

**Mission 16 — The Operation (Alliance path)** (Pirate base infiltration)
- Type: Infiltration + sabotage (navigate base interior, reach command center)
- Hand-authored multi-phase map: maintenance port → corridors → guard stations → command center
- Stealth-focused with option for combat. Tomas companion provides stealth bonuses.
- Difficulty: High. Culmination of ground exploration skills.

### 12.2 Ground Exploration as Story Vehicle

Ground maps can embed **story moments** at specific tiles:

- **NPC encounter tiles**: Stepping on or interacting with these tiles triggers a dialogue sequence (using existing DialogueView infrastructure) before returning to the grid
- **Discovery tiles**: Finding something interesting triggers a journal entry or a short descriptive text overlay
- **Scripted events**: Campaign maps can trigger scripted sequences at specific progress points (e.g., lights go out, a door locks behind you, an alarm triggers)

These moments are placed in hand-authored campaign maps. Procedural maps use a simplified version — random NPC encounters with generic faction-appropriate dialogue.

---

## 13. Technical Architecture Notes

### 13.1 New Models

- **`GroundMap`**: Tile grid, dimensions, tile data, entry/exit positions, enemy patrol routes, loot container positions, interactable definitions. `to_dict()`/`from_dict()` for save/load mid-mission.
- **`GroundTile`**: Type enum, faction skin, contents (loot, interactable data), fog state, noise value.
- **`GroundEnemy`**: Position, facing direction, patrol route, speed, combat stats (HP, attack, defense, talk difficulty), current AI state (patrol/investigate/search/pursue).
- **`GroundPlayerState`**: Position, HP, shield, collected loot, noise modifiers, vision radius, ground combat stats (compiled from attributes + skills + crew + equipment).
- **`GroundMission`**: Mission type, objectives, completion state, progress percentage, difficulty tier, faction, rewards. Links to campaign mission ID if applicable.
- **`GroundCombatState`**: Engaged enemies, exchange history, current modifiers, available re-rolls, social skills already attempted.
- **`GroundEquipment`**: Personal shield module, noise dampener, vision enhancer, lockpick. Slot-based (1-2 equipment slots).

### 13.2 New Views

- **`GroundExplorationView`**: The primary view. Renders the tile grid with scrolling viewport, fog of war, player sprite, enemy sprites with facing indicators, patrol route overlays, minimap. Handles turn processing, input (arrow keys for movement, hotkeys for actions), and state transitions.
- **`GroundBriefingView`**: Pre-mission briefing panel. Shows atmospheric text, objectives, intel, and crew selection. Transitions to GroundExplorationView.
- **`GroundCombatPanel`**: Not a separate view — a UI panel that overlays the bottom of GroundExplorationView when combat triggers. Shows dice rolls, HP pips, action buttons (Fight/Retreat/Talk), exchange results.
- **`GroundResultView`**: Post-mission results screen. Shows objectives completed/failed, loot collected, XP earned, credits gained/lost. Similar in structure to combat outcome screen.

### 13.3 New Data Files

- **`data/ground/tile_types.json`**: Tile type definitions with per-faction visual variants
- **`data/ground/enemy_types.json`**: Ground enemy stat blocks and AI behavior parameters
- **`data/ground/chunks/`**: Directory of chunk template files (JSON), organized by category (rooms, connectors, special) and faction
- **`data/ground/missions.json`**: Procedural mission type definitions (objective templates, reward scales, difficulty parameters)
- **`data/ground/equipment.json`**: Ground-specific equipment definitions
- **`data/ground/campaign/`**: Hand-authored campaign map files (one per campaign ground mission)

### 13.4 Integration Points

- **GameState.GROUND_BRIEFING, GameState.GROUND_EXPLORATION, GameState.GROUND_RESULT**: New game states
- **Game engine**: Trigger ground missions from dialogue choices, mission objectives, or station UI (for repeatable content)
- **Save system**: Ground mission state must be saveable mid-mission (player position, fog state, enemy positions, collected loot, alert level)
- **Crew system**: Crew selection UI before ground missions, crew XP awards on completion
- **Skill tree**: New ground combat skill nodes (see Section 6)
- **Achievement system**: New ground-specific achievements
- **Mission system**: Ground mission objectives integrate with existing MissionManager

### 13.5 Rendering Considerations

- Tile rendering should use pre-rendered tile sprites loaded at startup (`.convert_alpha()`)
- Fog of war can be implemented as a dark overlay surface with per-tile alpha
- Enemy vision cones rendered as semi-transparent colored overlays (only shown when enemy is visible to player)
- Smooth scrolling uses the same lerp approach as other animated UI elements
- Minimap renders at reduced resolution — one pixel per tile, color-coded by tile type and fog state
- Dice roll animations: pre-rendered dice face sprites, tumble animation (rotate + bounce), land on result. Keep it snappy — 0.5-0.8 seconds total.

---

## 14. Implementation Phasing

Ground exploration is a large system. The recommended build order prioritizes getting a playable loop working early, then layering depth:

### Phase A: Grid Foundation
- Tile grid model and rendering (floor, wall, door, exit, entrance)
- Player movement (cardinal, turn-based)
- Scrolling viewport with camera follow
- Basic fog of war (unexplored/explored/visible)
- Placeholder tile art (colored rectangles per type)

### Phase B: Stealth Core
- Enemy model with patrol routes and facing
- Enemy vision cones and detection states (UNDETECTED → SUSPICIOUS → ALERT)
- Noise system (noisy tiles, door opening, sprint)
- Alert state transitions and decay timers
- Patrol route visualization (observed enemy paths)

### Phase C: Ground Combat (Dice & Grit)
- Combat trigger on ALERT → player contact
- Exchange system (1d6 + modifiers)
- Fight/Retreat/Talk action choices
- Dice roll visualization
- HP pips and damage display
- Basic enemy stat blocks
- Social skill integration for Talk action

### Phase D: Crew & Attributes
- Crew selection UI (briefing view)
- Crew ground abilities (Elena vision, Marcus bypass, Priya hazard scan, Tomas stealth)
- Attribute modifiers applied to vision, combat rolls, noise, interactions
- Ground combat skill nodes on skill tree

### Phase E: Procedural Generation
- Chunk template library (rooms, connectors, special)
- Map assembly algorithm (anchor points, critical path, branching)
- Faction aesthetic application (tile skins, enemy types, hazard types)
- Mission type templates (infiltration, retrieval, sabotage, exploration, extraction)
- Difficulty tier scaling

### Phase F: Content & Polish
- Hand-authored campaign maps (Missions 10, 13, 16)
- Repeatable mission contract system
- Ground-exclusive loot and equipment
- Briefing view with atmospheric text
- Result view with consequence curve
- Minimap
- Achievements and progression tracking
- Visual polish: tile art, enemy sprites, particle effects, screen effects
- Interactable tiles: terminals, containers, hidden passages
- Cover mechanics, dark tiles, hazard tiles

---

## 15. Playstyle Support

The ground exploration system is designed to support multiple viable playstyles:

| Playstyle | Key Investments | Crew Picks | How It Plays |
|---|---|---|---|
| **Ghost** | High ACU, stealth skills, noise reduction | Tomas + Elena | Never detected. Full rewards. Patient, methodical. Sees patrol routes early, moves through gaps. |
| **Scrapper** | High RES + ACU, ground combat skills, shield equipment | Marcus + Priya | Gets detected, fights through. Ambushes enemies deliberately. Tanky with re-rolls and Last Stand. |
| **Silver Tongue** | High SYN, social skills, observation | Tomas + any | Gets detected sometimes, talks past every encounter. Social checks at checkpoints avoid entire sections. |
| **Opportunist** | Balanced build | Situational | Sneaks when possible, fights when caught, extracts when risk gets high. Push-your-luck specialist. |
| **Explorer** | High COM + ACU, loot skills | Elena + any | Focused on map coverage and loot extraction. Voluntary extraction expert. Knows when to push and when to leave. |

---

## Document Status

**Version**: 1.0
**Created**: 2026-03-10
**Status**: Design specification — not yet implemented
**Dependencies**: Existing systems (crew, social skills, attributes, skill trees, dialogue, mission manager)
**Blocks**: Campaign Act One Chapters 3-5 (Missions 08-17)
