# Graphics & Interface Overhaul

> Design document for the comprehensive visual and interaction overhaul of SpaceGame.
> Originated from playtester feedback (March 2026): resolution issues, text cutoff, discoverability of progression systems.
> Expanded into a full vision for maximizing player engagement through visual identity, spatial design, and interaction depth.

---

## Design Principles

1. **Every screen should feel like a place.** Screens evoke being somewhere, not looking at data. Spatial metaphors replace abstract menus wherever possible.
2. **Distinct identity for every system.** Mining, salvage, refining, and both combat systems each have their own visual language, sound palette, and interaction feel.
3. **Progression is visible.** The player should see their growth reflected in the world: upgraded consoles, better ships, trophies, faction recognition.
4. **Information without overwhelm.** Context-sensitive tooltips, smart quest hints, and layered disclosure replace front-loaded data dumps.
5. **Immersion through contextual identity.** The persistent HUD adapts to where the player is: cockpit instruments when flying, station chrome when docked, tactical overlay on the ground. The frame tells you where you are before you read a word.

---

## Wave 1: Foundation (Immediate Impact)

### 1A. Cockpit HUD Bar

**The single highest-impact change.** A persistent bottom bar visible on the galaxy map and station hub, designed to look like the cockpit instrument panel of the player's ship.

#### Visual Design

The HUD is not a generic UI bar. It is the bottom edge of the player's cockpit viewport:

```
+------------------------------------------------------------------+
|                                                                  |
|                    GALAXY MAP / STATION HUB                      |
|                      (main game content)                         |
|                                                                  |
+==================================================================+
|  [HULL ====----]  [SHIELD ========]  [FUEL =======--]   1,245 CR |
|  [Capt] [Skills] [Crew] [Missions] [Journal]    "Deliver chip.." |
+------------------------------------------------------------------+
```

**Left section (Ship Status):**
- Hull integrity bar (green/yellow/red gradient, animated)
- Shield bar (cyan, animated pulse when full)
- Fuel bar (amber, shows remaining fuel visually)
- All bars have subtle glow/scanline effects to feel like instruments

**Center section (Quick Access):**
- 5 icon buttons styled as cockpit console buttons (backlit, tactile feel):
  - Captain (character sheet) -- silhouette icon
  - Skills (skill tree) -- circuit/node icon
  - Crew (roster) -- people icon
  - Missions (log) -- clipboard icon
  - Journal -- book icon
- Each button glows when the corresponding system has new content (new skill points, new mission available, unread journal entry)
- Hover shows tooltip: "Skills (3 points available)"

**Right section (Status & Quest):**
- Credits display with subtle credit chip icon
- Cargo capacity: "42/100" with fill indicator
- Active quest hint: single line, truncated with "..." if long
  - e.g., "Deliver the audit chip to Stellaris Port"
  - Click to open mission log
  - Subtle directional arrow or system name highlight

#### Visual Style

- **Material**: Dark metal with brushed steel texture, riveted edges
- **Lighting**: Subtle blue-white backlight behind gauges, warm amber for fuel
- **Accents**: Thin cyan border line along top edge (separating cockpit from viewport)
- **Animation**: Bars pulse gently when at full. Shield bar has faint shimmer. Low fuel triggers amber warning pulse. Critical hull triggers red flash.
- **Resolution**: Rendered at native resolution. Height scales with `scale_y()`. Approximately 80-100px at 720p, 120-150px at 1080p.

#### Technical Implementation

- New `CockpitHUD` class (not a full BaseView -- it's a persistent overlay)
- Rendered AFTER the active view but BEFORE transitions
- Receives references to Player, MissionManager for live data
- Only visible on GALAXY_MAP and STATION_HUB states (hidden during combat, mini-games, dialogue, etc.)
- Buttons trigger state changes the same way galaxy map buttons currently do
- Existing galaxy map buttons for Skills/Crew/Missions/Journal/Character are removed (moved to HUD)

#### Notification Badges

- Unspent skill points: red dot on Skills button
- New available missions: dot on Missions button
- Unread journal entries: dot on Journal button
- Crew loyalty warnings: dot on Crew button
- These replace the need for the player to "remember to check" systems they might not discover

#### Contextual HUD Skins

The HUD adapts its visual framing based on where the player is. The layout, buttons, and data are identical across skins — only the background panel, accent colors, and decorative elements change.

**Three contexts:**

| Context | Visual Frame | Accent Color | States |
|---------|-------------|--------------|--------|
| **Ship (cockpit)** | Dark brushed metal, rivets, cyan instruments | Cyan (#3CB4FF) | Galaxy map, skill tree, character, missions, journal, crew, statistics, achievements |
| **Station (docked)** | Clean composite panels, faction-colored trim, station signage | Faction primary color | Station hub, trading, cantina, repair bay, shipyard, investment |
| **Hidden** | No HUD | N/A | Combat, mining, salvage, refining, dialogue, ground exploration, encounters, menus |

**Ship skin (default):**
- Dark metal panel with brushed steel texture
- Riveted edges, panel seam line
- Cyan accent border along top edge
- Blue-white backlight behind gauges

**Station skin:**
- Lighter composite panel (station interior material)
- Faction-colored accent border (Guild blue, Union amber, Collective white, Frontier green)
- Subtle station logo/emblem watermark in corner
- Warmer lighting feel (you're indoors, not in a cockpit)

**Technical approach:** The `CockpitHUD` class tracks a `hud_context` enum (`SHIP`, `STATION`, `HIDDEN`) and swaps the pre-rendered background panel surface based on context. The context is derived from the current GameState. Button rendering, data binding, and event handling are shared across skins.

### 1B. Station Hub Visual Upgrade

**Replace the 3x3 card grid with an illustrated station cross-section.**

#### Visual Design

The player sees a side-view cross-section of the station interior. Different zones are visually distinct areas:

```
+------------------------------------------------------------------+
|  ____                    ____            ____                     |
| |DOCK|   ___  ___       |CANT|   ___   |MINE|                   |
| |    |  |MKT||REP|      |INA |  |SHIP| |DOCK|                   |
| |____|  |___||___|       |____|  |YARD| |____|                   |
|   ===========================    |____|   ============           |
|  |INVEST|  |REFINE|              |SALV|                          |
|  |______|  |______|              |____|                          |
+==================================================================+
|  [HULL ====----]  ...cockpit HUD...              "Quest hint..." |
+------------------------------------------------------------------+
```

- Each zone has distinct visual character:
  - **Market**: Cargo crates, holographic price boards, busy NPCs
  - **Repair Bay**: Sparks flying, robotic arms, hull plating
  - **Cantina**: Warm amber light, bar counter, seated figures
  - **Mining Dock**: Rock dust, conveyor belts, drill equipment
  - **Salvage Bay**: Derelict hull fragments, cutting torches
  - **Refinery**: Glowing forge, smoke stacks, molten metal channels
  - **Shipyard**: Ship silhouettes in dry dock, crane arms
  - **Investment Office**: Clean desk, holographic charts
  - **Unique POI**: Varies by system (purple accent, mysterious)

- Zones highlight on hover with a subtle glow outline
- Click zone to enter the corresponding location
- Station name and faction banner displayed at top
- Station chatter text scrolls along the bottom of the station area (above HUD)
- Faction-specific architectural style:
  - **Commerce Guild**: Clean lines, chrome, holographic displays
  - **Miners' Union**: Industrial, riveted steel, warm amber lights
  - **Science Collective**: Sleek, white/blue, floating displays
  - **Frontier Alliance**: Patched together, colorful, improvised

#### Technical Implementation

- Replace station_hub_view.py's card grid rendering with zone-based illustrated layout
- Pre-rendered station backgrounds per faction (or procedurally assembled from tile sets)
- Clickable zones defined as pygame.Rect regions with hover detection
- Zone availability checks (locked zones dimmed/barred)
- Ambient particle effects: sparks near repair, steam near refinery, dust near mining

### 1C. Combat Visual Overhaul

**Make space combat feel like watching a battle, not reading a log. Every action should have visual weight. The player should feel the impact of every shot, the tension of every decision, and the satisfaction of every victory.**

#### Design Pillars

1. **Ships are the stars.** They should be large, detailed, and dominate the arena. Ship class should be visually obvious.
2. **Weapons cross the gap.** When you fire, you SEE the projectile travel from your ship to the target. The empty space between ships is the stage.
3. **Damage is progressive and visible.** A damaged ship LOOKS damaged. A critical hit FEELS devastating. Destruction is spectacular.
4. **The visual tells the story.** The combat log becomes supplementary. Players should understand what happened by watching, not reading.

---

#### Ship Presentation

**Ship Scale by Class:**

| Ship Class | Native Sprite | Display Scale | Display Size (1080p) | Arena Presence |
|-----------|---------------|---------------|---------------------|----------------|
| Light (scouts, couriers) | 64x64 | 2x | 128x128 | Small, nimble |
| Medium (freighters, traders) | 64x64 | 3x | 192x192 | Standard |
| Heavy (cruisers, haulers) | 64x64 | 3x | 192x192 | Imposing |
| Boss (warships, flagships) | 64x64 | 4x | 256x256 | Massive |

- Player ship: left 1/3 of arena, facing right
- Primary enemy: right 1/3 of arena, facing left
- Additional enemies: stacked vertically, scaled down slightly

**Idle Animation:**
- Gentle vertical bob (2px amplitude, 2s period sine wave)
- Engine glow pulsing (subtle brightness oscillation on rear thruster area)
- Shield shimmer when shields active (faint translucent overlay cycles alpha 20-40)

**Ship State Visualization:**

| Hull % | Visual Effect |
|--------|--------------|
| 100-75% | Clean ship, full engine glow |
| 75-50% | Minor damage marks overlay, occasional spark particle (1 per 2s) |
| 50-25% | Heavy damage overlay, persistent smoke trail (3-4 particles/s rising slowly), engine glow flickers |
| Below 25% | Critical damage, red warning pulse on ship outline (0.5s cycle), heavy smoke, sparks flying |
| Shields active | Faint translucent shield bubble around ship |
| Shields depleted | Bubble shatters (one-time cyan particle burst outward) |
| Shields restored | Bubble rebuilds (particles converge inward over 0.3s) |

---

#### Weapon Projectile System

A new `ProjectileManager` handles weapon visualization. Each weapon type has a distinct visual identity:

**Laser / Energy Beams:**
```
Timeline: [0.0s charge] → [0.05s muzzle flash] → [0.15s beam extends] → [0.1s impact] → [0.1s fade]
```
1. Weapon mount on attacker brightens (muzzle flash sprite, 0.05s)
2. Bright beam sprite stretches from weapon mount to target (0.15s, progressive extension)
3. Impact flash at hit point + LASER_HIT particles
4. Beam fades out (0.1s alpha decay)
- **Color**: Hot white core with red/orange glow edges
- **Width**: 4-6px (scaled)

**Missiles / Torpedoes:**
```
Timeline: [0.05s launch] → [0.3s flight arc] → [0.15s explosion]
```
1. Launch flash at attacker
2. Missile sprite travels on parabolic arc (apex ~30px above straight line)
3. Trail particles emitted along flight path (orange/yellow, fast fade)
4. On hit: MISSILE_EXPLOSION particles + larger screen shake
5. On miss: missile streaks past target, smaller explosion off-screen edge
- **Color**: Silver/white body with orange exhaust trail
- **Speed**: ~400px/s (0.3s for typical arena crossing)

**Cannons / Kinetic Weapons:**
```
Timeline: [0.0s] → [0.15s burst of 3 rounds] → [0.1s impacts]
```
1. Three small bright projectiles fired in quick succession (0.05s apart)
2. Each travels in straight line at high speed (~600px/s)
3. Small impact flash on each hit
4. Slight ship recoil on firing (attacker shifts back 3px, returns 0.1s)
- **Color**: Bright yellow/white rounds
- **Feel**: Rapid, punchy, mechanical

**Repair / Shield Abilities:**
```
Timeline: [0.3s swirl effect around target]
```
1. Green (hull) or cyan (shield) particles spiral inward toward ship
2. Brief bright flash as healing applies
3. Health/shield bar ticks up smoothly
- No projectile — self-targeting visual effect

**Miss Visualization:**
- Projectile fires normally but trajectory offset 20-40px past the target
- Projectile continues past and fades at arena edge
- No impact effects, no screen shake
- "MISS" text floats from target position

---

#### Shield System Visualization

Shields deserve their own visual layer because they're a core combat mechanic:

- **Active shields**: Faint translucent circular bubble rendered around ship (alpha 25-35, cyan tint)
  - Subtle shimmer: alpha oscillates on a 2s sine cycle
  - Bubble drawn as filled circle with soft-edge gradient

- **Shield hit**: Bubble flares bright at impact point (alpha jumps to 150, fades over 0.2s)
  - Ripple effect: concentric circles expand outward from impact point (3 rings, fast fade)
  - SHIELD_IMPACT particles at contact point

- **Shield break** (shields reach 0):
  - Bubble surface fractures: 8-12 triangular fragments fly outward
  - Each fragment: small cyan polygon particle with gravity, 0.5s lifetime
  - Bright flash at center
  - Audio: distinct "shield down" SFX
  - Ship is now visually exposed (no bubble = vulnerability is VISIBLE)

- **Shield restore** (shields regenerated from 0):
  - Particles converge inward from a ring around the ship
  - Bubble reforms from translucent to solid over 0.3s
  - Subtle "shield up" audio cue

---

#### Impact Feedback Hierarchy

Different hit severities should FEEL different:

| Hit Type | Screen Shake | Flash | Particles | Sound |
|----------|-------------|-------|-----------|-------|
| Glancing (low damage) | None | Brief white, 0.05s | 8 small sparks | Soft impact |
| Standard | Light (2.0, 0.1s) | White, 0.1s | 15 sparks | combat_hit |
| Heavy (>30% of max hull) | Medium (4.0, 0.15s) | Bright white, 0.15s | 25 sparks + debris | Heavy impact |
| Critical hit | Heavy (6.0, 0.2s) | Yellow flash, 0.2s | 30 sparks + fire | Critical SFX + camera pulse |
| Shield-only | Gentle (1.5, 0.1s) | Cyan, 0.15s | SHIELD_IMPACT | combat_shield |
| Ship destruction | Max (8.0, 0.35s) | White → orange, 0.3s | 40+ explosion | combat_explosion |

---

#### Destruction Sequence (Enhanced)

Ship destruction should be the most dramatic moment in combat:

```
Timeline: [0.0s] → [0.05s freeze] → [0.15s flash] → [0.4s breakup] → [0.5s settle]
```

1. **Freeze frame** (0.05s): Brief pause on the killing blow. Everything stops. Impact registered.
2. **White flash** (0.15s): Bright white expanding circle from ship center (radius 0 → ship_size * 1.5)
3. **Ship breaks apart** (0.4s):
   - Ship sprite splits into 4-6 fragment sprites
   - Fragments fly outward with rotation and gravity
   - MISSILE_EXPLOSION particles (40+ count) burst from center
   - Fire/smoke particles persist at center for 0.5s
   - Secondary explosions (2-3 smaller bursts at 0.1s intervals)
4. **Settle** (0.5s):
   - Fragments fade and slow
   - Smoke dissipates
   - Debris particles drift with slow gravity
   - Arena returns to calm

**Fragment Generation (procedural):**
- Take the ship sprite, divide into 4-6 irregular regions
- Each fragment is a cropped portion of the original sprite
- Fragments assigned random velocity (outward from center) + angular rotation
- Tinted orange/red to simulate burning

---

#### Arena Atmosphere

The combat arena should feel alive:

- **Space dust**: 15-20 tiny particles drifting slowly left-to-right (speed: 5-15px/s, alpha: 30-60, size: 1-2px). Always present, creates sense of motion through space.
- **Distant stars**: Static point sprites in the background (part of AnimatedBackground). Subtle parallax if camera system is added.
- **Post-combat debris**: After an enemy is destroyed, 5-10 small debris particles remain floating in the arena for the rest of combat. Creates narrative — you're fighting among the wreckage.
- **Danger-level atmosphere**:
  - Safe systems: Clean starfield, minimal dust
  - Moderate: More dust, occasional distant asteroid silhouette
  - Dangerous: Dense dust, red-tinged nebula glow, more asteroids
  - Crimson Reach: Dark red ambient, heavy particle density

---

#### Combat Log Redesign

The combat log should supplement, not drive, the experience:

- **Relocate**: Move from bottom-right to a compact strip along the bottom of the arena (above action panel)
- **Format**: Single scrolling line of most recent action, with "expand" button for full log
- **Style**: Semi-transparent background, smaller font
- **Content**: Brief action summaries: "Laser Mk2 → Pirate Scout: 18 hull damage"
- **Scrollback**: Click or scroll to see previous entries in an expanding overlay

---

#### Damage Preview (Hover Feedback)

When hovering over a move button:
- **On enemy health bar**: Ghost fill showing projected damage range (translucent red overlay on the bar from current health down by expected damage)
- **On move button**: Enhanced tooltip showing:
  - Damage range: "12-18 hull damage"
  - Accuracy: "85% hit chance"
  - Energy cost: "3 energy"
  - Special effects: "+15% accuracy for 2 turns"
  - Cooldown: "2 turn cooldown after use"

---

#### Required Sprite Assets

**Ship sprites (regeneration at 64x64 native):**
All player ships (24) and enemy ships (20+) regenerated at 64x64 native. Displayed at class-appropriate scale (2x-4x). Update sprite_manifest.json ship section with new sizes and improved prompts emphasizing:
- Clear silhouette at small sizes
- Visible engine section (rear glow area)
- Faction-distinctive design language
- Damage-compatible design (areas that can show cracks/burns)

**New weapon VFX sprites:**

| Sprite ID | Size | Description | Backend |
|-----------|------|-------------|---------|
| `vfx_muzzle_flash` | 32x32 | Bright white/yellow weapon fire flash | Gemini |
| `vfx_laser_beam` | 128x8 | Horizontal energy beam, hot white core with colored glow | NanoBanano |
| `vfx_missile_body` | 32x32 | Missile/torpedo projectile with exhaust trail | Gemini |
| `vfx_cannon_round` | 16x16 | Small bright kinetic projectile | Gemini |
| `vfx_shield_bubble` | 128x128 | Translucent circular shield overlay | NanoBanano |
| `vfx_shield_ripple_01-04` | 128x128 | Shield impact ripple animation (4 frames) | NanoBanano |
| `vfx_shield_fragment` | 32x32 | Triangular shield shard for break effect (4 variants) | Gemini |
| `vfx_ship_fragment_01-04` | 32x32 | Hull debris pieces for destruction (4 variants) | NanoBanano |
| `vfx_smoke_puff` | 32x32 | Gray/dark smoke for damaged ships | Gemini |
| `vfx_explosion_flash` | 64x64 | Bright expanding explosion flash | NanoBanano |

**Updated explosion sequence:**
- `vfx_explosion_01-06` at 64x64 — Expand from 4 frames to 6 for smoother destruction (flash, fireball, secondary, smoke, embers, fade)

---

#### New Combat Engine Components

**ProjectileManager** (new class):
```
Manages active projectiles in flight. Each projectile:
- Interpolates from source to target position
- Renders sprite (rotated to face direction of travel)
- Emits trail particles along path
- Triggers impact effects on arrival
- Handles miss deflection (offset trajectory)
```

**ShieldRenderer** (new class):
```
Manages shield bubble visualization per ship:
- Renders translucent overlay when shields > 0
- Animates hit ripples on impact
- Plays break/restore sequences
- Tracks shimmer animation state
```

**DamageStateRenderer** (enhancement to existing):
```
Manages per-ship visual degradation:
- Selects damage overlay based on hull %
- Manages persistent smoke/spark emitters
- Applies red tint at critical damage levels
- Handles ship recoil on hit (brief position offset + return)
```

**New Particle Configs:**

| Config | Count | Speed | Life | Colors | Use |
|--------|-------|-------|------|--------|-----|
| SPACE_DUST | 20 | 5-15 | 3-6s | (100,110,130)→(60,65,80) | Always present |
| WEAPON_TRAIL | 5/frame | 10-30 | 0.1-0.3s | weapon_color→dark | Along projectile path |
| SHIELD_SHATTER | 12 | 80-200 | 0.3-0.6s | (100,200,255)→(20,60,120) | Shield break |
| SHIELD_REFORM | 10 | 60-120 | 0.2-0.4s | (20,60,120)→(100,200,255) | Shield restore (inward) |
| SHIP_SMOKE | 4/s | 8-20 | 1.0-2.0s | (80,80,90)→(40,40,50) | Damaged ship persistent |
| SHIP_SPARKS | 1/2s | 30-80 | 0.2-0.5s | (255,200,80)→(200,50,0) | Damaged ship intermittent |
| DEBRIS_FLOAT | 8 | 5-15 | 3-8s | (60,55,50)→(30,25,20) | Post-destruction debris |
| CRITICAL_FLASH | 20 | 100-250 | 0.1-0.3s | (255,255,200)→(255,150,0) | Critical hit burst |

---

#### Implementation Phases

**Phase 1: Ship Scale & Arena Layout** (foundation)
- Regenerate ship sprites at 64x64 native
- Add ship class → scale mapping
- Update arena layout for larger ships
- Implement idle bob animation
- Move combat log to compact strip

**Phase 2: Projectile System** (core visual upgrade)
- Build ProjectileManager class
- Implement laser beam rendering (stretch sprite from source to target)
- Implement missile flight (arc interpolation + trail particles)
- Implement cannon burst (rapid small projectiles)
- Wire into animation event system

**Phase 3: Shield Visualization** (defensive feedback)
- Build ShieldRenderer class
- Implement persistent shield bubble overlay
- Implement impact ripple effect
- Implement break/restore sequences
- Add shield-specific audio cues

**Phase 4: Damage Escalation** (progressive feedback)
- Enhance DamageStateRenderer with persistent emitters
- Implement smoke trail for damaged ships
- Implement spark particles for damaged ships
- Implement ship recoil on hit
- Implement critical hit flash

**Phase 5: Destruction Spectacular** (climactic moment)
- Implement freeze frame on killing blow
- Implement expanding flash effect
- Implement ship fragment generation and physics
- Implement secondary explosions
- Implement persistent debris

**Phase 6: Atmosphere & Polish** (immersion)
- Add space dust ambient particles
- Add danger-level atmosphere variations
- Implement damage preview on hover
- Polish timing, easing, and visual hierarchy
- Audio pass: ensure every visual has matching audio

---

## Wave 2: Mini-Game Identity

### 2A. Mining: Excavation Depth System

**Transform from flat click-grid to cross-section excavation.**

#### Core Mechanic Change
- The asteroid is shown as a vertical cross-section with **depth layers**:
  - Surface (0-3): Common ores, easy extraction, low energy cost
  - Mid-depth (4-7): Iron/crystal ores, moderate energy, occasional gas vents
  - Deep core (8-10): Rare ores, high energy cost, unstable sections, biggest payoff
- Player selects a **column** to drill into (horizontal choice)
- Drill advances downward one cell per action (vertical progression)
- Each cell reveals its contents as the drill reaches it

#### Decision Space
- **Column selection**: Geological scanner (skill-gated) shows hints about what's below
- **Depth commitment**: Deeper = better ore, but more energy spent and more hazards
- **Hazard management**: Gas vents require waiting (skip a turn) or risk explosion. Unstable sections can collapse (lose drill position)
- **Tool switching**: Standard drill (balanced), precision extractor (slow, preserves quality), blast charge (fast, damages ore quality)

#### Visual Identity
- **Color palette**: Deep browns, blacks, amber highlights, crystal blue/purple glows at depth
- **Perspective**: Side-view cross-section, drill enters from top
- **Effects**: Dust particles rise as drill descends, rock fragments fly on extraction, gas wisps from vents, crystal glow pulses at depth
- **Sound**: Drilling rumble, rock cracking, hissing gas, crystalline chime on rare finds

#### Retained Mechanics
- Energy system (regeneration timer)
- Drone automation (drones work surface layer automatically)
- Ore silo + transfer to cargo
- Session summary with rating
- Skill bonuses (damage, energy efficiency, scanner range)

### 2B. Salvage: Derelict Infiltration

**Reframe the grid as room-by-room exploration of a wrecked ship.**

#### Core Mechanic Change
- The 5x5 grid becomes a **derelict floor plan** with rooms and corridors
- Each cell is now a **room** with a door (sealed, breached, or open)
- Scanning a room reveals its contents through the door (uses scan charges)
- Extracting requires entering the room (costs structural integrity)

#### Decision Space
- **Structural integrity timer**: The derelict is collapsing. Each room entered reduces integrity by 5-15%. At 0%, auto-extraction with whatever you've grabbed
- **Room types**: Cargo hold (commodities), Lab (rare components), Bridge (data/intel), Engine room (ship parts), Crew quarters (personal effects)
- **Risk escalation**: Deeper rooms have better loot but cost more integrity
- **Intel mechanic**: Scanning adjacent rooms for free before committing charges

#### Visual Identity
- **Color palette**: Dark steel blue, emergency red lighting, flickering white
- **Perspective**: Top-down derelict floor plan with room layouts
- **Effects**: Flickering lights, vacuum hiss particles, sparking wires, hull groaning (screen shake on integrity drops)
- **Atmosphere**: Each derelict type (cargo, lab, engine) has distinct visual styling and ambient mood

#### Retained Mechanics
- Scan/extract charge economy
- Quality tiers (poor/normal/good/excellent)
- Derelict type selection
- Session summary with rating
- Skill bonuses (scan efficiency, extraction quality, structural resistance)

### 2C. Refining: Active Forge

**Replace queue-and-wait with hands-on forging.**

#### Core Mechanic Change
- Selecting a recipe begins a **forging sequence** (30-60 seconds of active play)
- The player manages two gauges: **Temperature** and **Pressure**
- Temperature must stay in the "optimal zone" (green band on gauge) during forging
- Pressure affects speed: higher pressure = faster forging but narrower optimal temp band
- The player adjusts heat (up/down controls) and pressure (valve control) in real time

#### Decision Space
- **Temperature management**: Fuel burns raise temp, vent cools it. Different recipes have different optimal ranges
- **Pressure trade-off**: Higher pressure means faster completion but tighter margins for error
- **Quality outcome**: Time spent in optimal zone determines output quality (affects sell price and recipe mastery)
- **Batch efficiency**: Successfully maintaining optimal conditions unlocks batch bonuses

#### Visual Identity
- **Color palette**: Deep orange, molten gold, forge red, dark iron
- **Perspective**: Front-facing forge with visible crucible, temperature gauge on left, pressure gauge on right
- **Effects**: Molten metal glow, rising sparks, steam vents, heat shimmer distortion
- **Feedback**: Gauge needles wobble realistically, forge color shifts with temperature, satisfying "clang" on successful forging completion

#### Retained Mechanics
- Recipe discovery and mastery progression
- Forge token upgrade system
- Ingredient consumption
- Session summary with rating
- Skill bonuses (temperature stability, pressure tolerance, batch size)

---

## Wave 3: Combat Depth

### 3A. Space Combat: Tactical Positioning

#### Core Mechanic Addition
- Ships occupy positions on a **3-column lane system**: Close, Mid, Far
- Each turn: choose to **Move** (change lane) AND/OR **Attack** (use a weapon)
- Weapon effectiveness varies by range:
  - Lasers: Best at Close range, reduced at Far
  - Missiles: Best at Mid/Far, can be evaded at Close
  - Cannons: Consistent damage but slow (cooldown)
  - Point defense: Only works at Close (intercepts missiles)

#### Decision Space
- **Positioning**: Close range = more damage dealt AND received. Far range = safer but less effective
- **Weapon selection**: Match weapon to current range for maximum effect
- **Crew abilities**: Crew members provide abilities based on assignment:
  - Bridge: accuracy bonus, initiative bonus
  - Weapons: damage bonus, crit chance
  - Engineering: shield regen, repair efficiency
  - Navigation: evasion bonus, repositioning speed
- **Multi-enemy tactics**: With 2+ enemies, positioning matters more (focus fire vs split attention)

#### Retained Mechanics
- Turn-based combat with phase system
- Energy management for special moves
- Flee/negotiate/bribe options
- Loot drops on victory
- Combat log for detailed information

### 3B. Ground Combat: Cover & Flanking

#### Core Mechanic Addition
- Existing grid tiles now provide **cover values**:
  - Terminals/desks: Half cover (-30% incoming damage)
  - Walls: Full cover (blocks line of sight)
  - Open ground: No cover
- **Flanking**: Attacking an enemy from the side ignores their cover bonus. Attacking from behind provides +25% damage
- Crew members (in party) position independently on the grid

#### Decision Space
- **Positioning for advantage**: Move to flank before attacking
- **Cover management**: Use cover to reduce damage taken, force enemies out of cover
- **Crew coordination**: Send crew to flank while captain draws fire
- **Social skills integration**: Talking from cover is safer (enemy can't close distance)

#### Retained Mechanics
- Turn-based movement on existing grid
- Stealth/detection system
- Social skill checks (persuasion, intimidation)
- Equipment and attribute bonuses
- Mission objective integration

---

## Wave 4: Immersion & Polish

### 4A. Captain's Quarters

- New GameState: CAPTAINS_QUARTERS
- Accessible from cockpit HUD (Captain button) or pause menu
- Visual: Ship interior showing collected trophies, faction plaques, star chart with visited systems marked
- Replaces or augments the current CHARACTER view with a more immersive presentation
- Progression is VISIBLE: empty shelves fill as the player completes achievements

### 4B. Enhanced Galaxy Map

- Trade route overlay: toggle to see profitable routes highlighted (commodity flow visualization)
- Danger indicators: pirate activity, faction conflict zones shown as visual overlays
- System info on hover: population, faction, available activities, visited/unvisited status
- Quest waypoint: active quest destination has a persistent marker/glow

### 4C. Screen Transitions

- **Warp travel**: Brief warp tunnel animation (0.5s) when traveling between systems
- **Station docking**: Approach + docking clamp animation (0.3s) when entering station
- **Combat entry**: Alert klaxon + ship systems powering up transition
- **Mini-game entry**: Appropriate transition (drill deploying, docking with derelict, forge igniting)

### 4D. Skill Tree as Ship Systems

- Reframe 9 skill trees as ship system consoles:
  - Navigation → Navigation Computer
  - Trading → Trade Analytics Terminal
  - Combat → Weapons Array
  - Mining → Drill Operations Console
  - Salvage → Salvage Bay Controls
  - Refining → Forge Interface
  - Crew → Crew Quarters Panel
  - Leadership → Command Bridge
  - Social/Black Market → Comms Array
- Each "console" is a visual panel that upgrades as skills are unlocked
- Skill nodes become hardware components that slot into the console

---

## Implementation Status & Priority

### WAVE 1: Foundation — ALL COMPLETE

| Item | Status | Notes |
|------|--------|-------|
| Resolution Infrastructure | DONE | Configurable 720p/900p/1080p, scale_x/scale_y, font auto-scaling |
| Font System Migration | DONE | 161 calls migrated to semantic constants, resolution-aware FontCache |
| View Layout Scaling | DONE | All 35 views use proportional positioning |
| Sprite Scale Defaults | DONE | Resolution-aware res_scale() on all SpriteManager methods |
| Sprite Manifest v4 | DONE | All 75 sprites doubled to HD sizes, improved prompts |
| 1A: Cockpit HUD Bar | DONE | Ship/station context skins, notification badges, quest hints, faction accents |
| Galaxy Map Cleanup | DONE | Buttons migrated to HUD, system info panel moved left, action card added |
| HUD Clearance Pass | DONE | All bottom-positioned buttons across 11 views adjusted for HUD height |
| 1B: Station Hub Visual | DONE | 5 faction-specific layouts + polish (tooltips, particles, taglines, entrance anim) |
| 1C: Combat Visual Overhaul | DONE | All 6 phases: ships, projectiles, shields, damage, destruction, atmosphere |

### WAVE 2: Mini-Game Identity — ALL COMPLETE

| Item | Status | Notes |
|------|--------|-------|
| 2A: Mining Depth Visuals | DONE | 5-layer atmosphere, depth meter sidebar, layer transition animation |
| 2B: Salvage Derelict Visuals | DONE | 3 derelict atmospheres, deck meter, corruption pressure, scan pulse, quality bursts, mode overlay |
| 2C: Refining Forge Visuals | DONE | Forge intensity (4 heat levels), mastery momentum bar (connected), buffer pressure, mastery celebration |

### UPCOMING (Waves 3-4)

| Wave | Item | Impact | Effort | Priority |
|------|------|--------|--------|----------|
| 3A | Space Combat Positioning | High | Very High | Next |
| 2B | Salvage Derelict Layout | High | High | After 2A |
| 2C | Refining Active Forge | Medium | High | After 2B |
| 3A | Space Combat Positioning | High | Very High | After 2C |
| 3B | Ground Combat Cover | Medium | High | After 3A |
| 4B | Enhanced Galaxy Map | Medium | Medium | After 3B |
| 4C | Screen Transitions | Medium | Low | After 4B |
| 4A | Captain's Quarters | Medium | Medium | After 4C |
| 4D | Skill Tree Ship Systems | Low | High | After 4A |

---

## Technical Notes

- All new UI elements use the existing `scale_x()`/`scale_y()` resolution system
- All fonts use semantic `FontCache` constants
- All sprites use `res_scale()` for resolution-aware display
- New views follow the BaseView lifecycle pattern (see views/CLAUDE.md)
- New particle effects use the existing ParticlePool system
- Wave 1A (Cockpit HUD) is a persistent overlay, not a full BaseView -- similar pattern to tutorial_overlay
- Each wave should be independently testable and shippable
