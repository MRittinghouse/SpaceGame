# Combat Mechanics Overhaul

> Design document for deepening combat gameplay to match the visual spectacle.
> Originated from critical analysis: visual systems (projectiles, shields, destruction, atmosphere) are strong, but underlying mechanics are shallow. The decision space is too narrow — players spam their strongest move with no meaningful trade-offs.

---

## Design Principles

1. **Every turn should present a meaningful choice.** The player should weigh options, not autopilot.
2. **Energy is the strategic currency.** Managing energy across turns is the core tactical skill.
3. **Enemies are puzzles, not punching bags.** Each enemy type demands a different approach.
4. **Crew are tactical assets, not passive buffs.** Choosing which crew ability to deploy is a real decision.
5. **Weapons have identity.** Each weapon class rewards a different playstyle.
6. **Information creates strategy.** The player should be able to read the battlefield and plan ahead.

---

## Phase 1: Energy Tension

**The single highest-impact change. Make energy a real resource.**

### Current Problem
- Energy pools: 10-15. Regen: 3-4 per turn.
- Most moves cost 2-5 energy. Player can always afford their best move.
- No turn ever requires planning ahead. No "save now for a big play later."

### Changes

**Rebalance energy economy:**
- Reduce base energy pool to **8** (was 10-15)
- Reduce base energy regen to **2** per turn (was 3-4)
- Scale with ship class: light ships get +1 regen (nimble), heavy ships get +2 pool (endurance)
- Crew engineering bonus: Marcus provides +1 regen when in party (tangible benefit)

**Add energy-generating moves:**
- "Power Shunt" (new move, available on all ships): Deal 0 damage, restore 4 energy. Costs your turn but sets up a big play next round.
- "Capacitor Dump" (new move, mid-tier upgrade): Deal moderate damage AND restore 2 energy if the hit lands. Reward for accuracy.
- "Overcharge" (new move, late-tier upgrade): Next attack deals +50% damage but costs double energy. Setup → payoff pattern.

**Energy theft/drain becomes meaningful:**
- Energy drain moves now steal from the enemy AND give to the player
- Creates a "resource war" dynamic: drain the enemy's energy to prevent their strong moves

### Impact
Players now think: "I have 4 energy. Do I use Laser Cannon (3 energy, moderate damage) or save for Missile Barrage (6 energy, huge damage) next turn by using Power Shunt now?" Every turn is a resource allocation puzzle.

---

## Phase 2: Enemy Telegraphing & AI Depth

**Make enemies feel intelligent and distinct. Give the player information to react to.**

### Telegraphing System

Each enemy broadcasts their next move one turn in advance:

**Visual indicator**: Icon + text above the enemy card:
- Sword icon: "ATTACKING" — standard damage move incoming
- Double sword: "CHARGING" — powerful attack next turn (1-turn charge)
- Shield icon: "FORTIFYING" — defensive move, reduced damage taken
- Lightning: "DRAINING" — energy/shield drain incoming
- Arrow: "EVADING" — high evasion next turn, hard to hit
- Door icon: "FLEEING" — will attempt to flee next turn

**Player reads the field**: "The pirate is CHARGING — I should use my shield boost this turn" or "The enforcer is FORTIFYING — save my big hit for when their defense drops."

### Enemy AI Improvements

**Replace deterministic patterns with personality-driven decision trees:**

- **Aggressive**: Prefers high-damage moves. Telegraphs CHARGING when at >60% hull. Switches to desperation attacks below 30%.
- **Defensive**: Opens with FORTIFYING. Alternates between shield and attack. Telegraphs DRAINING when player has high energy.
- **Evasive**: High evasion base. Telegraphs EVADING before attacking. Vulnerable during attack turns (dropped evasion).
- **Tactical**: Reads player state. If player shields are down, goes all-in. If player has low energy, uses drain. The "smart" enemy.
- **Berserker**: Damage increases as hull decreases. Terrifying at low health. Never defends.
- **Support** (new): Buffs other enemies. Heals allies. Priority target — if you don't kill the support first, the fight drags on.

### Charge Attacks

New mechanic: some powerful moves take **2 turns** to execute.

Turn 1: Enemy telegraphs "CHARGING NOVA CANNON" — the player sees this and has one turn to prepare.
Turn 2: The attack fires. High damage, possibly AOE.

**Player counterplay options:**
- Use a disruption move (new) to cancel the charge
- Raise shields to absorb the hit
- Go all-in on damage to kill the enemy before they fire
- Flee if the charge is too threatening

This creates dramatic tension moments that the visual system (flash effects, charge particles) can amplify.

---

## Phase 3: Crew Tactical Choice

**Transform crew from passive buffs to active tactical decisions.**

### Current Problem
- Crew abilities fire automatically in the crew phase
- Player has zero input on crew actions
- Crew feels like a stat modifier, not a team member

### Changes

**Player chooses ONE crew ability per turn during the Player Input phase:**

UI: A crew ability bar appears above the move buttons (or as a second row). Each recruited crew member shows their ability with energy cost. Player clicks one (optional — can skip for free).

**Expanded crew combat abilities (2 per crew member):**

| Crew | Ability 1 | Ability 2 |
|------|-----------|-----------|
| Elena (Navigator) | *Evasive Maneuvers*: +25 evasion for 2 turns (3 energy) | *Intercept Course*: Next attack gains +20 accuracy (1 energy) |
| Marcus (Engineer) | *Emergency Repair*: Restore 25 hull (4 energy) | *Reroute Power*: Restore 3 energy, skip crew ability next turn (0 energy) |
| Priya (Scientist) | *Sensor Jam*: -20 enemy evasion for 2 turns (3 energy) | *Analyze Weakness*: Next attack deals +30% damage to target (2 energy) |
| Tomas (Trader) | *Smooth Talking*: +15 negotiate chance, permanent for this combat (2 energy) | *Distraction*: Target enemy skips their next turn (5 energy, 4-turn cooldown) |

**Design intent:**
- Each crew member offers a defensive/utility option AND an offensive option
- The choice is contextual: "Do I heal or set up a big hit?"
- Energy cost means crew abilities compete with weapon moves for the same pool
- Tomas's Distraction is expensive but powerful — a real tactical tool

### Crew Synergies

Certain combinations create bonus effects:
- Elena's Intercept Course + Priya's Analyze Weakness = "Precision Strike" (text callout, +50% damage total)
- Marcus's Reroute Power + any expensive weapon = "Overclocked" (the energy you saved pays for a big gun)
- These aren't hard-coded mechanics — they're emergent from the system. But we can add visual callouts when synergies occur.

---

## Phase 4: Damage Preview & Combat Information

**Give the player the information they need to make smart decisions.**

### Damage Preview on Move Hover

When hovering over a move button:
- **Enemy health bar**: Ghost fill shows projected damage range (translucent red/cyan overlay)
  - Shows RANGE (min-max) not exact value, since accuracy varies
  - Shield damage shown in cyan ghost, hull damage in red ghost
- **Move tooltip enhanced**:
  - Damage: "12-18 hull damage" (not just a number)
  - Accuracy: "85% hit chance" with color coding (green >70%, yellow 50-70%, red <50%)
  - Special effects: "Applies -15 evasion for 2 turns"
  - Energy: "3 energy (you have 6)"
  - Cooldown: "2 turn cooldown" or "READY"

### Enemy Info on Hover

Hovering over an enemy card shows:
- Current hull/shields with numbers (not just bars)
- Active status effects with remaining turns
- Telegraph indicator (what they're about to do)
- Damage range of their strongest available move
- Behavior type label (Aggressive, Tactical, etc.)

### Combat Momentum Bar

A horizontal bar at the top of the arena showing "who's winning":
- Shifts left (player advantage) as enemies take damage
- Shifts right (enemy advantage) as player takes damage
- Color gradient: green (player) → yellow (even) → red (enemy)
- Creates narrative tension without adding mechanical complexity
- Victory shifts the bar fully left with a satisfying animation

---

## Phase 5: Elemental Weapon System

**Five weapon damage types, each with distinct identity, stacking mechanics, and tactical role.**

### Design Philosophy

Weapons in the Aurelia Expanse aren't just "bigger numbers." Each technology has a distinct effect that rewards sustained tactical play. Kinetic weapons are straightforward raw damage. Every other element trades some upfront damage for a powerful secondary effect that stacks across turns, creating build identity and rewarding players who commit to a weapon doctrine.

### The Five Elements

#### 1. Kinetic (White/Silver)
**Identity**: Pure, reliable damage. No tricks, no gimmicks.

- 100% of damage dealt as direct hull/shield damage
- No secondary effect, no stacking
- Highest raw damage per energy spent of any element
- **Best for**: Players who want simplicity and consistent output
- **Projectile visual**: White/silver rounds, cannon-style impacts

#### 2. Plasma (Orange/Red)
**Identity**: Burn them down. Sustained damage over time that punishes enemies who can't heal.

- 66% of weapon damage dealt upfront
- 33% + 15% bonus converted to **Burn** DoT (damage over time per turn for 3 turns)
- Burn **stacks up to 3 times** — each new plasma hit adds a fresh 3-turn Burn stack
- Example: Plasma weapon deals 18 base damage
  - Upfront: 12 damage
  - Burn: ~7 damage per turn for 3 turns
  - If fired every turn: Turn 1 = 7 DoT, Turn 2 = 14 DoT, Turn 3 = 21 DoT (3 stacks, max)
  - Turn 4: oldest stack falls off, new one added = still 21 DoT (rolling 3-stack cap)
- **Best for**: Sustained pressure against high-hull enemies
- **Projectile visual**: Orange-red fireballs, impact leaves lingering flame particles

#### 3. Ion (Cyan/Electric Blue)
**Identity**: Shield killer. Melts shields fast but struggles against bare hull.

- Deals **150% damage to shields** (bonus multiplier)
- Deals **75% damage to hull** (reduced when shields are down)
- No stacking mechanic — the multiplier IS the identity
- Encourages pairing: open with Ion to strip shields, switch to Kinetic/Plasma for hull
- **Best for**: Heavy-shield enemies (Science Collective, bounty hunters)
- **Projectile visual**: Crackling electric-blue bolts, shield impact shows electrical arcs

#### 4. Cryo (Ice Blue/White)
**Identity**: Slow the enemy. Stack frost to freeze them solid.

- 85% of weapon damage dealt as direct damage (slightly reduced)
- Each hit applies 1 stack of **Chill** (lasts 4 turns per stack)
- At **3 Chill stacks**: target becomes **Frozen** — loses their next turn entirely
  - Frozen clears all Chill stacks after triggering (resets to 0)
  - Must re-stack 3 Chill to freeze again
- Chill also provides minor evasion penalty: -5 evasion per stack
- **Best for**: Dangerous enemies with powerful attacks — freeze them before they fire
- **Projectile visual**: Ice-blue crystalline shards, impact shows frost spreading on hull

#### 5. Voltaic (Purple/Violet)
**Identity**: Suppress enemy firepower. Weaken their damage output with each hit.

- 85% of weapon damage dealt as direct damage (slightly reduced)
- Each hit applies 1 stack of **Suppressed** (lasts 3 turns per stack)
- Each Suppressed stack reduces enemy damage by **12%** (max 3 stacks = 36% reduction)
- At max stacks, enemies become significantly less threatening — turns defensive fights into attrition wins
- **Best for**: Multi-enemy fights and boss encounters where survivability matters
- **Projectile visual**: Purple energy pulses, impact shows crackling disruption field

### Elemental Damage Resolution

When a weapon fires, the combat engine processes damage based on its element:

```
1. Calculate base damage (from weapon stats)
2. Apply damage_boost buffs (Overcharge etc.)
3. Apply element-specific split:
   - Kinetic: 100% direct
   - Plasma: 66% direct, remainder → Burn stack
   - Ion: 150% to shields, 75% to hull
   - Cryo: 85% direct, apply Chill stack
   - Voltaic: 85% direct, apply Suppressed stack
4. Apply target's damage reduction
5. Resolve shield absorption → hull damage
6. Apply DoT/status stacks
```

### Weapon Upgrade Tiers (15 new weapons: 5 elements x 3 tiers)

#### Kinetic Weapons
| Tier | Name | Damage | Energy | Cooldown | Notes |
|------|------|--------|--------|----------|-------|
| 1 | Slug Thrower | 10 | 2 | 0 | Reliable starter kinetic |
| 2 | Railgun Accelerator | 22 | 3 | 0 | Standard kinetic upgrade |
| 3 | Mass Driver Mk3 | 38 | 5 | 2 | Heavy kinetic, highest raw damage |

#### Plasma Weapons
| Tier | Name | Damage | Energy | Cooldown | Notes |
|------|------|--------|--------|----------|-------|
| 1 | Plasma Caster | 12 | 2 | 0 | 8 direct + ~5/turn Burn |
| 2 | Inferno Lance | 21 | 3 | 0 | 14 direct + ~9/turn Burn |
| 3 | Solar Flare Cannon | 33 | 5 | 2 | 22 direct + ~14/turn Burn. T3 bonus: Burn bypasses shields |

#### Ion Weapons
| Tier | Name | Damage | Energy | Cooldown | Notes |
|------|------|--------|--------|----------|-------|
| 1 | Ion Disruptor | 10 | 2 | 0 | 15 to shields, 7.5 to hull |
| 2 | Arc Emitter | 18 | 3 | 0 | 27 to shields, 13.5 to hull |
| 3 | Cascade Ionizer | 30 | 5 | 2 | 45 to shields, 22.5 to hull. T3 bonus: shield overkill carries to hull |

#### Cryo Weapons
| Tier | Name | Damage | Energy | Cooldown | Notes |
|------|------|--------|--------|----------|-------|
| 1 | Frost Projector | 8 | 2 | 0 | Low damage + 1 Chill stack |
| 2 | Glacial Beam | 16 | 3 | 0 | Moderate damage + 1 Chill stack |
| 3 | Absolute Zero Array | 24 | 4 | 2 | Good damage + 1 Chill stack. T3 bonus: Frozen at 2 stacks instead of 3 |

#### Voltaic Weapons
| Tier | Name | Damage | Energy | Cooldown | Notes |
|------|------|--------|--------|----------|-------|
| 1 | Voltaic Pulse | 8 | 2 | 0 | Low damage + 1 Suppressed stack |
| 2 | Storm Emitter | 16 | 3 | 0 | Moderate damage + 1 Suppressed stack |
| 3 | Tempest Cannon | 24 | 4 | 2 | Good damage + 1 Suppressed stack. T3 bonus: 15% reduction per stack (45% max) |

### Elemental Status Effects (New)

| Status | Applied By | Per Stack | Max Stacks | Duration/Stack | Trigger at Max |
|--------|-----------|-----------|------------|----------------|----------------|
| **Burn** | Plasma weapons | X damage/turn | 3 | 3 turns | Rolling DoT (21+/turn at max) |
| **Chill** | Cryo weapons | -5 evasion | 3 | 4 turns | **Frozen**: lose next turn, clear all stacks |
| **Suppressed** | Voltaic weapons | -12% damage dealt | 3 | 3 turns | -36% damage (significant survivability gain) |

Note: Ion has no stacking status — its identity is the shield/hull damage multiplier, not a debuff.

### Enemy Elemental Weaknesses (Future Expansion)

Potential extension: enemies could have elemental resistances or weaknesses. A Science Collective ship might resist Ion (hardened shields) but be weak to Plasma (flammable components). This is NOT in the initial implementation but is a natural upgrade path.

### Visual Identity per Element

Each element has distinct projectile visuals (already supported by the ProjectileManager weapon type system):

| Element | Projectile Style | Impact Particles | Status Visual |
|---------|-----------------|-----------------|---------------|
| Kinetic | White/silver rounds | Spark burst, metal debris | None |
| Plasma | Orange-red fireballs | Fire particles, lingering flames | Orange glow on ship hull |
| Ion | Electric-blue crackling bolts | Blue electrical arcs | Blue lightning on shields |
| Cryo | Ice-blue crystal shards | Frost particles spreading | White frost patches on hull |
| Voltaic | Purple energy pulses | Purple disruption ripples | Purple static field around ship |

### Visual Identity Graphics Pass

Each element needs a complete visual treatment — not just different colors, but distinct visual *language* so the player instantly recognizes what type of weapon fired.

#### Projectile Visuals (ProjectileManager integration)

| Element | Projectile Shape | Trail Effect | Muzzle Flash |
|---------|-----------------|-------------|--------------|
| **Kinetic** | Tight cluster of 2-3 small white rounds | Faint white streaks, fast fade | Sharp white flash, small radius |
| **Plasma** | Wobbling orange-red fireball, irregular edges | Thick orange trail with ember particles falling behind | Wide orange-yellow flare, lingering |
| **Ion** | Crackling bolt with forked tendrils | Electric blue sparks along path, random lateral offshoots | Blue-white electric burst, thin arcs |
| **Cryo** | Angular ice-blue crystalline shard | Faint frost mist trail, slow drift | Cool blue-white flash with ice particles |
| **Voltaic** | Pulsing purple energy orb, size oscillates | Purple afterglow trail, ripple distortion | Purple-white flash with static sparks |

#### Impact Visuals

| Element | Shield Impact | Hull Impact | Screen Shake |
|---------|-------------|------------|-------------|
| **Kinetic** | Standard spark burst | Metal debris + sparks | Standard (3.0) |
| **Plasma** | Orange flare on shield surface | Fire particles that linger 0.5s on hull | Medium (3.5) — explosive feel |
| **Ion** | Electric arcs crawl across shield bubble | Smaller sparks, electrical crackle | Light (2.5) — precision feel |
| **Cryo** | Frost crystals spread on shield surface | Frost patch appears on hull (persists while Chill active) | Light (2.0) — cold, sharp |
| **Voltaic** | Purple ripple across shield | Purple static field around ship (brief) | Medium (3.0) — disruption feel |

#### Status Effect Visuals (rendered on affected ships)

| Status | Visual on Ship | Duration Visual |
|--------|---------------|----------------|
| **Burn (Plasma)** | Orange ember particles rising from hull. Intensity scales with stack count (1=subtle, 3=heavy flames) | Small flame icon with stack count on enemy card |
| **Chill (Cryo)** | Frost overlay on ship sprite (translucent white-blue tint). At 3 stacks: ice crystal cage around ship before Frozen triggers | Snowflake icon with stack count on enemy card |
| **Frozen (Cryo)** | Ship encased in translucent ice block for 1 turn. Dramatic crystallization animation on trigger | "FROZEN" text banner + shatter effect when turn skipped |
| **Suppressed (Voltaic)** | Purple static field crackling around ship. Intensity scales with stacks | Lightning-bolt-with-X icon with stack count on enemy card |

#### Weapon Shop Visual Treatment

In the shipyard upgrade shop, elemental weapons should be visually categorized:
- Each element gets a colored accent bar on its upgrade card (matching the element color)
- Element icon displayed next to weapon name (flame for Plasma, snowflake for Cryo, etc.)
- Tooltip shows element type and explains the secondary effect clearly

#### Sprite Assets Required

New sprites for the element system (add to sprite_manifest.json):

| Sprite ID | Size | Description |
|-----------|------|-------------|
| `icon_element_kinetic` | 16x16 | White/silver crosshair icon |
| `icon_element_plasma` | 16x16 | Orange flame icon |
| `icon_element_ion` | 16x16 | Blue lightning bolt icon |
| `icon_element_cryo` | 16x16 | Blue-white snowflake icon |
| `icon_element_voltaic` | 16x16 | Purple static/pulse icon |
| `vfx_plasma_fireball` | 32x32 | Wobbling orange-red projectile |
| `vfx_ion_bolt` | 32x16 | Crackling electric-blue bolt |
| `vfx_cryo_shard` | 24x24 | Angular ice crystalline shard |
| `vfx_voltaic_orb` | 24x24 | Pulsing purple energy orb |
| `vfx_frost_overlay` | 64x64 | Translucent frost patch for Chill visual |
| `vfx_ice_cage` | 96x96 | Ice crystal cage for Frozen visual |
| `status_burn` | 12x12 | Flame icon for status bar |
| `status_chill` | 12x12 | Snowflake icon for status bar |
| `status_frozen` | 12x12 | Ice block icon for status bar |
| `status_suppressed` | 12x12 | Purple static icon for status bar |

### Skill Tree Integration

The existing Combat skill tree should include elemental mastery nodes:
- **Burn Specialist**: +20% Burn damage
- **Ion Overcharge**: Ion weapons drain 2 enemy energy on hit
- **Deep Freeze**: Chill stacks last 1 extra turn
- **Suppression Expert**: Suppressed stacks last 1 extra turn
- **Elemental Versatility**: Switching weapon elements mid-combat costs 0 energy (instead of a turn)

---

## Phase 6: Utility Moves & Tactical Depth

**Non-elemental moves that add strategic variety beyond damage.**

### Utility Moves (alongside the 15 elemental weapons)

**Starter tier:**
1. *Power Shunt*: 0 damage, restore 4 energy. (DONE — already implemented)
2. *Point Defense*: 0 damage, next incoming attack deals -50% damage. Reactive defense.

**Mid tier:**
3. *Capacitor Dump*: 14 damage + restore 2 energy on hit. (DONE — already implemented)
4. *EMP Pulse*: 5 damage + drain 3 enemy energy. Resource warfare.
5. *Targeting Lock*: 0 damage, next 3 attacks gain +25 accuracy. Precision setup.

**Late tier:**
6. *Overcharge*: +50% damage boost for 1 turn. (DONE — already implemented)
7. *Broadside*: 12 damage to ALL enemies. 6 energy, 4-turn cooldown. Crowd control.
8. *Emergency Vent*: Sacrifice 15 shields to restore 5 energy. Desperate resource conversion.
9. *Nova Burst*: 35 damage (Kinetic), 5-turn cooldown, 8 energy. The ultimate finisher.

---

## Implementation Status — ALL 6 PHASES COMPLETE

| Phase | Description | Status | Highlights |
|-------|-------------|--------|------------|
| **1** | Energy Tension | DONE | Pools 6-8, regen 2, 24 ships + 28 enemies rebalanced, 3 new energy moves |
| **2** | Enemy Telegraphing | DONE | Enemies broadcast intent (ATTACKING/CHARGING/FORTIFYING/EVADING/DRAINING) |
| **3** | Crew Tactical Choice | DONE | 4 abilities per companion (16 total), player picks one per turn, energy cost |
| **4** | Damage Preview | DONE | Ghost fill on enemy health bars, enhanced tooltips with accuracy/energy |
| **5** | Elemental Weapons | DONE | 5 elements (Kinetic/Plasma/Ion/Cryo/Voltaic), 15 weapons, stacking effects |
| **6** | Utility Moves | DONE | 9 tactical tools (AOE, Absorb, Cleanse, Nova Burst, etc.), 85 total upgrades |

### CRITICAL: Ship Sprite Generation Gap

**Current state**: 15 of 24 player ships and 25 of 28 enemy templates fall back to generic cyan polygon wedges because sprite files either don't exist or use mismatched naming conventions.

**Player ships missing sprites** (15):
prospector, patrol_cutter, corsair, mining_barge, smugglers_sloop, salvage_rig, war_frigate, deep_explorer, phantom, industrial_titan, diplomatic_cruiser, consortium_merchantman, syndicate_enforcer, frontier_runner, institute_vessel

**Enemy templates missing sprites** (25):
pirate_scout, pirate_raider, smuggler, patrol_vessel, guild_enforcer, guild_dreadnought, union_brawler, union_crusher, science_probe, science_sentinel, frontier_raider, frontier_gunship, guild_revenue_cutter, union_picket, science_surveyor, frontier_skirmisher, reach_dreadwreck, bounty_tracker, bounty_enforcer, bounty_vanguard, bounty_ace, faction_enforcer, ledger_raider, ledger_striker, ledger_vanguard

**Naming mismatches** (sprites exist but IDs don't match):
- `pirate_light.png` exists → template is `pirate_scout`
- `enforcer.png` exists → template is `guild_enforcer`
- `smuggler_runner.png` exists → template is `smuggler`
- `frontier_gunboat.png` exists → template is `frontier_gunship`
- `frontier_scout.png` exists → template is `frontier_skirmisher`

#### Phase 7: Ship Sprite Overhaul

**7A. Fix naming mismatches** (immediate, no generation needed):
- Rename or symlink existing sprites to match template IDs
- 5 enemy sprites can be fixed immediately

**7B. Generate missing player ship sprites** (15 ships):
Each ship needs a unique visual identity based on its class and role:

| Ship | Class | Visual Identity |
|------|-------|----------------|
| prospector | early_game | Rugged utility vessel, sensor arrays, drill mounts |
| patrol_cutter | early_game | Small military, angled armor, weapon turret |
| corsair | mid_game | Sleek raider, swept wings, fast and aggressive |
| mining_barge | mid_game | Bulky industrial, conveyor arms, ore containers |
| smugglers_sloop | mid_game | Low-profile, hidden compartments, dark hull |
| salvage_rig | mid_game | Mechanical arms, cutting tools, patchwork hull |
| war_frigate | late_game | Heavy warship, turrets, thick armor plating |
| deep_explorer | late_game | Long-range, sensor dish, fuel pods |
| phantom | late_game | Stealth, angular, radar-absorbing surfaces |
| industrial_titan | late_game | Massive hauler, modular containers, crane arms |
| diplomatic_cruiser | late_game | Elegant, diplomatic insignia, communication arrays |
| consortium_merchantman | faction | Guild colors (blue), trade insignia |
| syndicate_enforcer | faction | Dark, menacing, Union colors (amber) |
| frontier_runner | faction | Improvised, green accents, frontier patches |
| institute_vessel | faction | Clean white-blue, Collective design, lab modules |

**7C. Generate missing enemy ship sprites** (25 enemies):
Enemy ships need faction-specific visual language:

- **Pirates**: Patchwork hulls, scavenged parts, red/black markings
- **Guild**: Clean corporate blue, standardized military design
- **Union**: Heavy industrial, amber/rust, riveted plating
- **Science**: Sleek white-blue, sensor arrays, modular pods
- **Frontier**: Improvised green, mismatched parts, hand-painted markings
- **Crimson Reach**: Dark red/rust, salvaged, dangerous-looking
- **Bounty Hunters**: Specialized, dark, purpose-built
- **Ledger**: Unmarked military, ominous, no faction insignia

**7D. Improve procedural fallback** (before sprites are generated):
Make the polygon ships look better as a stopgap:
- Different shapes by ship class (dart, wedge, rectangle, diamond)
- Faction-colored hulls instead of generic cyan
- Engine exhaust particle trail
- Hull detail lines (panel seams, viewport dots)

**7E. Ship sprite manifest update**:
Add all 40 missing ships to sprite_manifest.json with generation prompts.
Include animated idle sheets (2-frame engine glow pulse) for each.

#### Priority
7A (naming fixes) and 7D (better fallback) are immediate — no sprite generation needed. 7B-C-E require the generation pipeline and API budget.

---

## Wave 2: JRPG-Inspired Combat Evolution

> Inspired by Final Fantasy 6-9: momentum-based special abilities, crew combo synergies, boss encounters with scripted patterns, and ship class ultimates. These mechanics deepen combat from "pick a move" into a system with buildup, payoff, team synergy, and memorable moments.

### Phase 8: Momentum Gauge & Ship Ultimates

**The Momentum Gauge** is a combat-long resource that builds through actions and damage, unlocking increasingly powerful abilities at thresholds. This is our version of FF's Limit Break system.

#### Momentum Buildup
- **Dealing damage**: +5% per hit
- **Taking hull damage**: +8% per hit received (comeback mechanic)
- **Killing an enemy**: +15%
- **Crew ability used**: +3%
- **Elemental status applied**: +2% per stack
- **Taking critical damage (below 25% hull)**: +20% one-time surge

#### Momentum Thresholds

| Level | Threshold | Unlock | Description |
|-------|-----------|--------|-------------|
| Charged | 25% | **Crew Synergy** | Unlock combo abilities for crew pairs |
| Surging | 50% | **Overdriven Weapon** | Next weapon attack deals 2x damage |
| Overload | 75% | **System Overclock** | +3 energy regen for 2 turns |
| ULTIMATE | 100% | **Ship Ultimate** | Unique ability per ship class (see below) |

Momentum resets to 0 after using the Ship Ultimate. Lower-tier thresholds remain available after use (they don't consume momentum, only unlock access).

#### Ship Class Ultimates

| Ship Class | Ships | Ultimate Name | Effect |
|-----------|-------|---------------|--------|
| Starter | Shuttle | **Mayday Burst** | Guaranteed flee + 30% hull heal |
| Early Combat | Patrol Cutter | **Intercept Salvo** | 25 damage to all + -20 evasion for 2 turns |
| Trade/Freighter | Light/Medium Freighter, Bulk Hauler | **Cargo Jettison** | Sacrifice 10 cargo for 60 AoE damage |
| Fast/Scout | Fast Courier, Scout, Corsair | **Afterburner Strike** | 50 damage + guaranteed hit + free action next turn |
| Mining/Salvage | Prospector, Mining Barge, Salvage Rig | **Drill Charge** | 45 damage, ignores shields entirely |
| Stealth | Phantom, Smuggler's Sloop | **Ghost Protocol** | Immune to all damage for 2 turns |
| Heavy Combat | War Frigate, Clipper | **Nova Barrage** | 60 damage to ALL enemies (Kinetic) |
| Luxury/Diplomat | Luxury Yacht, Diplomatic Cruiser | **Diplomatic Immunity** | All enemies skip next 2 turns |
| Explorer | Deep Explorer | **Sensor Overload** | Reveal all enemy stats + 30 accuracy for 3 turns + drain 5 energy from all enemies |
| Industrial | Industrial Titan | **Tractor Beam** | Immobilize strongest enemy for 3 turns |
| Faction: Guild | Consortium Merchantman | **Trade Embargo** | Enemies can't use abilities costing 3+ energy for 3 turns |
| Faction: Union | Syndicate Enforcer | **Forge Hammer** | 70 single-target damage + apply 3 Burn stacks |
| Faction: Frontier | Frontier Runner | **Rally Cry** | Full heal crew abilities cooldowns + 50% momentum refund |
| Faction: Science | Institute Vessel | **Quantum Analysis** | Copy the strongest enemy's best move for 1 use |

#### Visual Treatment
- Momentum bar renders below the player panel (left side), filling with a gradient glow
- At each threshold, a brief pulse flash and audio cue
- At ULTIMATE, the bar blazes with the ship class's accent color
- Ultimate activation: brief cinematic zoom on player ship, dramatic particle burst, screen darken

---

### Phase 9: Crew Combo Abilities

When specific crew members are both recruited AND the Momentum gauge is at 25%+, **Combo Abilities** become available. These are more powerful than individual crew abilities and reward thoughtful party composition.

#### Combo List

| Crew Pair | Combo Name | Effect | Energy Cost |
|-----------|-----------|--------|-------------|
| Elena + Marcus | **Emergency Overhaul** | Restore 40 hull AND 5 energy | 5 |
| Elena + Priya | **Precision Strike Protocol** | Next attack: 100% accuracy + 50% bonus damage | 4 |
| Elena + Tomas | **Smuggler's Escape** | +60% flee chance + restore 3 energy | 3 |
| Marcus + Priya | **System Purge** | Cleanse all debuffs + restore 20 shields | 5 |
| Marcus + Tomas | **Jury-Rigged Countermeasures** | Deploy absorb shield + restore 4 energy | 4 |
| Priya + Tomas | **Market Intelligence** | Reveal all enemy stats + drain 4 energy from target | 3 |

#### UI Treatment
- When a combo is available (both crew recruited, 25%+ momentum, enough energy), a special **COMBO** button appears in the crew ability row
- Combo button has a distinct gold border and both crew member names
- Using a combo counts as the crew action for that turn (replaces individual crew ability)
- Brief combo name banner appears on use: "PRECISION STRIKE PROTOCOL"

#### Discovery
- Combos are NOT visible until the player has both crew members AND triggers 25% momentum for the first time with that pair
- First discovery shows a tutorial popup: "Crew Combo Unlocked! Elena and Marcus can combine their abilities."
- Discovered combos are remembered and show immediately in future combats

---

### Phase 10: Boss Encounter System

Boss enemies are mechanically distinct from regular enemies. They have more health, scripted multi-phase behavior patterns, and unique abilities that create puzzle-like combat encounters.

#### Boss Designation
A new field on enemy templates: `"is_boss": true`

Bosses differ from regular enemies in:
- **3x health multiplier** (applied on top of base hull/shields)
- **Scripted phase patterns** (behavior changes at HP thresholds)
- **Unique abilities** (not available to regular enemies)
- **Immunity to certain effects** (can't be frozen, limited suppression)
- **Special loot tables** (guaranteed rare drops)
- **Dramatic intro** (name banner, unique music, screen effects)

#### Boss Roster (Initial)

**Campaign Bosses** (encountered during Act One story missions):

| Boss | Context | Phase 1 | Phase 2 | Phase 3 |
|------|---------|---------|---------|---------|
| **The Corsair King** | Pirate leader, early campaign | Aggressive (high damage) | Calls reinforcement (spawns pirate_scout) | Berserk (damage +50%, defense -30%) |
| **Guild Arbiter** | Corporate enforcer, mid campaign | Defensive (shields + DR) | Tactical (drains energy + accuracy debuffs) | Desperate (removes own shields, 2x damage) |
| **The Iron Maw** | Union heavy cruiser, Forgeworks | Heavy (slow, massive damage) | Fortified (DR + shield regen) | Overload (charges 2-turn devastating attack) |
| **Ledger Phantom** | Conspiracy agent, late campaign | Stealth (high evasion, disappears 1 turn) | Revealed (normal combat, vulnerable) | Data Purge (self-destructs for massive AoE) |

**Rare Random Encounter Bosses** (low chance during travel):

| Boss | Systems | Behavior |
|------|---------|----------|
| **The Collector** | Any dangerous system | Hoards player cargo — on defeat, drops massive loot |
| **Void Leviathan** | Deep space (Iron Depths, Crimson Reach) | Massive hull, weak shields. Charges devastating attacks. |
| **Rogue AI Vessel** | Axiom Labs, Nova Research | Copies player's last weapon used. Adapts each round. |

**Side Quest Boss Encounters** (new multi-part side quests):

| Quest Name | Stages | Boss | Reward |
|-----------|--------|------|--------|
| **The Bounty Board** | 3 systems, track the target | Bounty Ace (enhanced) | Rare weapon + credits |
| **Ghost Ship** | Investigate disappearances at 2 systems | Void Leviathan | Unique ship upgrade |
| **The Collector's Debt** | Trade at 3 systems to lure them out | The Collector | Massive cargo haul |

#### Boss Visual Treatment
- **Intro**: Screen darkens, boss name appears in large dramatic text with faction-colored accent
- **Health bar**: Boss gets a wide bar across the top of the arena (not side panel) showing phase thresholds
- **Phase transitions**: Brief animation pause, boss hull color shifts, new pattern announced
- **Death**: Extended destruction sequence (1.5x duration, more fragments, screen shake)

---

### Phase 11: Tutorial Integration

Every new mechanic needs clear communication. The tutorial system already supports contextual overlays.

#### New Tutorials

| Trigger | Tutorial | Content |
|---------|----------|---------|
| First combat with Momentum > 0 | "Momentum Gauge" | "Your Momentum gauge builds as you fight. At key thresholds, new abilities unlock. Watch the bar on the left!" |
| Momentum reaches 25% first time | "Momentum: Crew Synergy" | "At 25% Momentum, Crew Combo abilities unlock if you have the right pair. Check the COMBO button in your crew row." |
| Momentum reaches 100% first time | "Ship Ultimate!" | "ULTIMATE READY! Your ship's unique ability is available. Use it wisely — it resets your Momentum to zero." |
| First Crew Combo discovered | "Crew Combo: [Name]" | "[Crew A] and [Crew B] can combine their abilities! Combos are more powerful than individual crew moves." |
| First Boss encounter | "Boss Encounter!" | "This is a powerful boss enemy. Watch for phase changes as their health drops. Boss enemies have unique attack patterns — read the telegraphs!" |
| First elemental status applied | "Elemental Effects" | "Your [Element] weapon applied [Status]. Stacking these effects increases their power. Cryo can freeze, Plasma burns, Voltaic suppresses!" |

#### Tutorial Persistence
- Each tutorial fires ONCE per save file (flag stored in player.tutorial_flags)
- Can be replayed from Settings → Tutorial section
- Non-intrusive: appears as overlay at top of screen, doesn't pause combat

---

## Implementation Priority (Updated)

### COMPLETED (Phases 1-7)

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Energy Tension | DONE |
| 2 | Enemy Telegraphing | DONE |
| 3 | Crew Tactical Choice | DONE |
| 4 | Damage Preview | DONE |
| 5 | Elemental Weapons | DONE |
| 6 | Utility Moves | DONE |
| 7A | Ship Sprite Naming Fixes | DONE |

### UPCOMING (JRPG Evolution — Wave 2)

| Phase | Description | Effort | Impact | Dependencies |
|-------|-------------|--------|--------|-------------|
| **8** | Momentum Gauge + Ship Ultimates | HIGH | CRITICAL | None |
| **9** | Crew Combo Abilities | MEDIUM | HIGH | Phase 8 (needs Momentum threshold) |
| **10** | Boss Encounter System | HIGH | HIGH | Phases 8-9 (bosses should test all systems) |
| **11** | Tutorial Integration | MEDIUM | HIGH | Phases 8-10 (tutorials explain new mechanics) |
| **7B-E** | ~~Ship Sprite Generation~~ | ~~HIGH~~ | ~~MEDIUM~~ | **SUPERSEDED by Shipyard Overhaul** — player ships are now player-built pixel grids, eliminating the need for hand-crafted/generated sprites. Enemy sprites remain stock. See `requirements/shipyard_overhaul.md`. |

### UPCOMING (Defensive Identity — Wave 3)

| Phase | Description | Effort | Impact | Dependencies |
|-------|-------------|--------|--------|-------------|
| **12A** | Core Mechanics (armor, shield regen, graze, identity passives) | HIGH | CRITICAL | None (can be built alongside Wave 2) |
| **12B** | Upgrades & Equipment (18 defense + 9 utility) | MEDIUM | HIGH | Phase 12A |
| **12C** | Skill Tree Expansion (18 nodes + 3 capstones) | MEDIUM | HIGH | Phase 12A |
| **12D** | Enemy Templates (6 identity-counter enemies) | LOW | MEDIUM | Phase 12A |
| **12E** | Visual Pass (armor sparks, dodge anims, identity VFX) | MEDIUM | HIGH | Phases 12A-B |
| **12F** | Balance & Integration | LOW | HIGH | Phases 12A-E |

### Recommended Implementation Order
1. **Phase 8 (Momentum)** first — it's the backbone. Ship Ultimates give every ship class identity.
2. **Phase 12A (Defensive Core)** — can be built in parallel with or immediately after Phase 8. Armor, shield regen, and graze are foundational mechanics that improve every subsequent combat feature.
3. **Phase 9 (Crew Combos)** — layered on top of Momentum threshold 1. Rewards party composition.
4. **Phase 12B-C (Upgrades + Skills)** — flesh out the defensive identities with equipment and skill trees.
5. **Phase 10 (Bosses)** — uses all systems (momentum, combos, elements, defense identities, telegraphing). Boss design should exploit all three defensive identities.
6. **Phase 12D-E (Enemies + Visuals)** — counter-enemies and visual polish for defense identities.
7. **Phase 11 (Tutorials)** last — explains everything that's been built, including defense identity choices.
8. **Phase 12F (Balance)** — final tuning pass after all systems are in place.

### Future Expansion Opportunities (post-playtesting)
- Elemental visual pass: distinct projectile colors/sprites per element
- Enemy elemental resistances/weaknesses
- Skill tree integration: elemental mastery nodes + momentum mastery
- Blue Magic equivalent: salvage enemy technology after boss kills
- New Game+ mode: bosses appear as random encounters, momentum builds faster
- Boss Rush mode: fight all bosses in sequence for leaderboard score
- Defensive identity synergy with crew: crew members that amplify specific identities
- Hybrid identity builds: upgrades that bridge two identities (e.g., shield-to-armor conversion)

---

## Wave 3: Defensive Identity System — Hull, Shields, Evasion

> Every ship has three defensive stats: Hull, Shields, and Evasion. Currently these exist as raw numbers, but they don't create distinct playstyles. This wave turns them into three fully realized defensive identities — the RPG equivalent of Warrior, Paladin, and Thief — each with dedicated upgrades, skill paths, passive mechanics, and strategic trade-offs that make choosing your defense feel as meaningful as choosing your weapon.

### Design Philosophy

**The Core Triangle:**
- **Hull (Juggernaut)**: High total survivability. You take every hit, but you can take more of them. Costs credits to repair — but in exchange, you get raw combat prowess that shield and evasion builds can't match. The "I win fights by refusing to die" identity.
- **Shields (Sentinel)**: Self-sustaining defense. Shields regenerate, so you pay nothing between fights — but the pool is smaller, and once broken, you're exposed. The "I manage my energy and tempo" identity. Countered hard by Ion weapons.
- **Evasion (Ghost)**: Probabilistic defense. When it works, you take zero damage. When it doesn't, you fold. The "I never get hit, but one bad turn can end me" identity. Rewards risk-taking, punishes greed. Also grants the best flee chances, fastest travel, and smuggling synergy.

**Balance Anchor: The Repair Cost Problem**
Hull costs money. Shields don't. Evasion doesn't. This means hull MUST be the strongest defensive option in raw combat terms, or a rational player would never choose it. Our balance target:

| Identity | Effective HP (turns survived) | Repair Cost | Out-of-Combat Advantage |
|----------|------------------------------|-------------|------------------------|
| Hull | **120%** of baseline | High (credits/turn) | None — pure combat power |
| Shield | **100%** of baseline | Free (auto-regen) | Sustain — no repair bills |
| Evasion | **90%** of baseline (probabilistic) | Free (not hit) | Flee chance, speed, smuggling |

A hull-focused ship survives ~20% more punishment than a shield ship, compensating for repair costs. An evasion ship survives ~10% less on average (but with higher variance — sometimes untouchable, sometimes caught flat-footed), compensated by out-of-combat advantages.

### Three Defensive Identities — Detailed Design

---

#### Identity 1: Hull (Juggernaut)

**Fantasy**: You're an armored freight train. Enemies shoot you and it barely matters. Your hull shrugs off hits that would cripple lighter ships. You pay for repairs after the fight, but during it? You're the last one standing.

**Core Mechanic — Armor Rating**
A new stat: **Armor**. Flat damage reduction per hit. Before shields are checked, before percentage reduction, Armor subtracts a flat amount from each incoming damage instance.

```
final_damage = max(1, raw_damage - armor_rating)
```

This is powerful against rapid small attacks (a 5-damage hit against 3 armor becomes 2 damage — 60% reduction!) but less effective against single large hits (a 40-damage hit against 3 armor becomes 37 — only 7.5% reduction). This creates a natural counter: hull ships fear big slow weapons but laugh at chip damage.

**Armor Scaling:**
- Base armor: 0 for most ships (opt-in via upgrades)
- Hull-identity ships (Industrial Titan, War Frigate, Bulk Hauler): 2-4 base armor
- Armor upgrades: +1 to +5 from equipment
- Skill tree: +1 per level of Hull Reinforcement (existing skill, rebalanced)
- Practical range: 0 (no investment) to 8-10 (fully built)

**Hull Passive — Last Stand**
When below 25% hull, hull-identity ships gain:
- +15% damage dealt (adrenaline)
- +2 armor (desperate defense)
- Visual: red hull glow, sparks, warning klaxon tone

This creates dramatic comeback moments and rewards staying in fights longer — exactly the hull fantasy.

**Hull Passive — Structural Integrity**
Hull HP above 75% grants +5% damage reduction. This rewards keeping hull topped up and makes the opening of fights slightly easier for hull ships.

**Repair Cost Balance:**
Current repair costs are flat per HP. We keep this, but add:
- Skill discount: "Field Repairs" skill reduces repair costs by 15% per level (max 3, 45% discount)
- Emergency hull-repair move heals less than shield-restore (25 hull vs 30-40 shields) but hull is a bigger pool
- Crew bonus: Marcus's engineering reduces repair costs at stations by 20%

---

#### Identity 2: Shields (Sentinel)

**Fantasy**: Your shields are your lifeline. You manage them like a resource — regenerating, restoring, overcharging. When shields are up, you're nearly invulnerable. When they break, you're scrambling to get them back. Ion weapons are your nightmare.

**Core Mechanic — Shield Regeneration**
Shields already exist but have no passive regen in combat. We add:

- **Passive shield regen**: Shields regenerate a small amount each turn automatically
- Base regen: 0 (most ships)
- Shield-identity ships (Institute Vessel, Luxury Yacht, Diplomatic Cruiser): 3-5 base regen per turn
- Shield regen upgrades: +2 to +8 per turn from equipment
- Skill tree: Shield Mastery adds +2 regen per level (existing skill, rebalanced)
- Practical range: 0 (no investment) to 10-15 per turn (fully built)

This means a dedicated shield build can sustain ~10-15 shield per turn for free, which against moderate damage creates a "shield wall" that absorbs chip damage entirely. But burst damage overwhelms it — a 40-damage hit blows through 10 regen instantly.

**Shield Passive — Overcharge Capacity**
Shield-identity upgrades can push shields ABOVE their base max, up to 150% capacity. Overshield decays at 10% per turn (use it or lose it). This rewards proactive shield management — restore shields before the fight intensifies, build a buffer.

**Shield Passive — Shield Break Vulnerability**
When shields hit 0, the ship takes 25% bonus damage for 1 turn (exposed systems). This is the shield identity's explicit weakness — once breached, you're more vulnerable than a hull ship would be. It creates urgency to prevent shield break and punishes letting shields drop.

**Ion Weakness:**
Ion weapons already deal 150% to shields. This is the hard counter. A shield-focused build that encounters Ion enemies must adapt (switch to hull repair moves, use evasion buffs). This is intentional — every identity should have a counter that forces adaptation.

**Economic Advantage:**
Shield regen is free. A shield ship that wins fights with shields intact pays zero repair bills. This is a real economic advantage over hull builds, balanced by the 20% lower effective survivability in combat.

---

#### Identity 3: Evasion (Ghost)

**Fantasy**: They can't hit what they can't catch. You're fast, slippery, and dangerous. You dodge most attacks, and the ones that land hit a ship made of paper. But your flee chance is incredible, your speed lets you outrun anything, and your hidden compartments keep contraband safe. You're a smuggler, a raider, a thief in the night.

**Core Mechanic — Evasion Scaling Overhaul**
Current evasion subtracts linearly from accuracy. We enhance this:

- **Graze system**: Attacks that miss by 10 or less deal 30% damage as a "graze" instead of a clean miss. This means evasion is never truly binary — high evasion reduces average damage smoothly rather than creating coin-flip situations.
- **Evasion diminishing returns above 50**: Each point of evasion above 50 counts as 0.5 points. This prevents evasion stacking from creating unhittable ships while keeping the 25-40 range (most evasion ships) at full value.
- **Evasion decay under fire**: After being hit, evasion is reduced by 5 for 1 turn (shaken). This means sustained focus fire gradually chips through evasion, preventing the "untouchable forever" problem. Ghost ships want short fights.

**Evasion Passive — Counterstrike**
When an attack misses (clean miss, not graze), the evasion ship gets +10% damage on their next attack. Stacks up to 3 times (+30%). This rewards the dodge fantasy — you dance around the enemy and then strike when they're overextended. Resets on taking a hit.

**Evasion Passive — Slippery**
+20% base flee chance (on top of the speed-based formula). Ghost ships can almost always escape fights they're losing. This is a MAJOR out-of-combat advantage — hull and shield ships are committed to fights; ghost ships choose their battles.

**Evasion Passive — Light Frame Vulnerability**
Evasion-identity ships take 15% bonus damage when hit. The trade-off is explicit: you dodge most things, but what connects HURTS. Combined with typically low hull pools (70-90 HP), a few unlucky hits can be fatal.

**Out-of-Combat Advantages:**
- **Faster travel**: Ships with evasion > 25 gain a speed multiplier (already exists on some ships)
- **Better smuggling**: Evasion-identity ships have higher contraband concealment (existing hidden_compartment ability)
- **Better encounter avoidance**: High evasion = higher chance to avoid random encounters entirely (new mechanic, simple roll)
- **Cheaper fuel**: Light ships are fuel-efficient (existing via fuel_efficiency stat)

---

### Ship Archetype Mapping

Every ship already leans toward an identity based on existing stats. We formalize this:

#### Hull-Leaning Ships (Juggernaut)
| Ship | Hull | Shields | Evasion | Base Armor | Identity Bonus |
|------|------|---------|---------|------------|---------------|
| War Frigate | 280 | 120 | 10 | 4 | Last Stand, +3 defense slots |
| Industrial Titan | 300 | 60 | 3 | 5 | Structural Integrity |
| Bulk Hauler | 250 | 80 | 5 | 3 | Last Stand |
| Syndicate Enforcer | 250 | 100 | 12 | 3 | hull_regen ability |
| Medium Freighter | 150 | 60 | 10 | 2 | Structural Integrity |
| Mining Barge | 180 | 40 | 5 | 3 | — |
| Salvage Rig | 160 | 35 | 10 | 2 | — |

#### Shield-Leaning Ships (Sentinel)
| Ship | Hull | Shields | Evasion | Base Regen | Identity Bonus |
|------|------|---------|---------|------------|---------------|
| Institute Vessel | 110 | 130 | 18 | 5 | Overcharge Capacity |
| Luxury Yacht | 120 | 100 | 20 | 4 | Overcharge Capacity |
| Diplomatic Cruiser | 180 | 90 | 12 | 3 | Shield Break protection |
| Patrol Cutter | 110 | 45 | 22 | 2 | — |
| Armed Trader | 130 | 50 | 15 | 2 | — |

#### Evasion-Leaning Ships (Ghost)
| Ship | Hull | Shields | Evasion | Speed | Identity Bonus |
|------|------|---------|---------|-------|---------------|
| Phantom | 70 | 35 | 38 | 18 | Counterstrike, Slippery, ghost_mode |
| Smuggler's Sloop | 75 | 30 | 32 | 15 | Slippery, hidden_compartment |
| Clipper | 90 | 45 | 32 | 16 | Counterstrike, fast_travel |
| Fast Courier | 80 | 30 | 30 | 15 | Slippery |
| Scout Vessel | 70 | 35 | 28 | 14 | Counterstrike, advanced_sensors |
| Frontier Runner | 90 | 50 | 28 | 14 | Slippery, salvage_mastery |
| Corsair | 140 | 55 | 20 | 12 | Counterstrike (hybrid, leans offense) |

#### Balanced/Starter Ships
| Ship | Hull | Shields | Evasion | Notes |
|------|------|---------|---------|-------|
| Shuttle | 60 | 20 | 25 | No identity — early game, upgradeable |
| Light Freighter | 100 | 40 | 15 | Slight hull lean |
| Prospector | 80 | 25 | 18 | Slight evasion lean |
| Deep Explorer | 100 | 60 | 22 | Slight shield lean |
| Consortium Merchantman | 180 | 70 | 12 | Hull/shield hybrid |

---

### New Upgrades — Defense Slot Equipment

Each identity gets a full tier progression of upgrades. Defense slot equipment provides the primary defense-identity investment.

#### Hull Identity Upgrades

| ID | Name | Tier | Price | Slot | Passive Bonus | Combat Move | Tuning Options |
|----|------|------|-------|------|--------------|-------------|----------------|
| `reinforced_plating` | Reinforced Hull Plating | 1 | 4,000 | defense | +1 armor | Brace (2E): +3 armor for 2 turns | Hardened (+1 armor) / Layered (+15 hull) |
| `reactive_armor` | Reactive Armor System | 2 | 12,000 | defense | +2 armor, +20 hull | Ablative Shield (3E): Absorb next hit up to 30 damage | Dense (+1 armor) / Regenerative (+5 hull/turn when below 50%) |
| `nano_repair_suite` | Nano-Repair Suite | 2 | 14,000 | defense | +1 armor | Rapid Mend (3E, 3-turn CD): Restore 35 hull | Fast Cycle (-1 energy) / Deep Repair (+12 hull) |
| `hull_matrix` | Structural Integrity Matrix | 3 | 28,000 | defense | +3 armor, +40 hull | Fortify (4E, 4-turn CD): +5 armor + 20% DR for 3 turns | Adamantine (+2 armor) / Resilient (+25 hull, Last Stand threshold 30%) |
| `titan_bulkhead` | Titan-Class Bulkhead | 3 | 42,000 | defense | +4 armor, +60 hull | Unbreakable (5E, 5-turn CD): Reduce all damage to 1 for 2 turns | Fortress (+3 armor) / Retribution (reflect 20% damage when hit) |
| `field_repair_rig` | Field Repair Rig | 2 | 10,000 | defense | Repair cost -25% | Patch Up (2E): Restore 20 hull | Salvage Parts (-10% more repair cost) / Combat Welder (+8 hull restore) |

#### Shield Identity Upgrades

| ID | Name | Tier | Price | Slot | Passive Bonus | Combat Move | Tuning Options |
|----|------|------|-------|------|--------------|-------------|----------------|
| `shield_conduit` | Shield Power Conduit | 1 | 5,000 | defense | +2 shield regen/turn | Pulse Shield (2E): Restore 20 shields | Capacitor (+1 regen) / Burst (+8 restore) |
| `adaptive_barrier` | Adaptive Barrier Array | 2 | 13,000 | defense | +3 shield regen, +20 max shields | Adaptive Ward (3E): Restore 30 shields + 10% DR for 1 turn | Overcharge (+15 max shields, allows overshield) / Reflective (+5% DR) |
| `shield_harmonics` | Shield Harmonics Generator | 2 | 15,000 | defense | +4 shield regen | Resonance Pulse (3E, 3-turn CD): Restore 40 shields to full, +5 regen for 2 turns | Harmonic (+2 regen) / Feedback (on shield break: deal 15 damage to attacker) |
| `quantum_shield` | Quantum Shield Matrix | 3 | 30,000 | defense | +5 shield regen, +30 max shields | Phase Shields (4E, 4-turn CD): Shields absorb 200% damage for 2 turns | Quantum Lock (shield break immunity for 1 turn) / Overclock (+20 max shields, overshield) |
| `aegis_projector` | Aegis Shield Projector | 3 | 45,000 | defense | +6 shield regen, +50 max shields | Aegis Protocol (5E, 5-turn CD): Full shield restore + overshield to 150% + immune to shield drain for 3 turns | Fortress Mode (+3 regen, -10 evasion) / Phalanx (allies gain 10 shields — future fleet mechanic) |
| `ion_hardening` | Ion-Hardened Shield Coils | 2 | 11,000 | defense | Ion damage reduced to 120% (from 150%) | Discharge (2E): Remove all Ion debuffs + restore 15 shields | Full Hardening (Ion to 100%) / Capacitor Bleed (+2 regen) |

#### Evasion Identity Upgrades

| ID | Name | Tier | Price | Slot | Passive Bonus | Combat Move | Tuning Options |
|----|------|------|-------|------|--------------|-------------|----------------|
| `thruster_array` | Maneuvering Thruster Array | 1 | 4,500 | defense | +5 evasion | Jink (1E): +15 evasion for 1 turn | Quick Burn (+3 evasion) / Afterburner (+10 flee chance) |
| `ecm_suite` | ECM Countermeasure Suite | 2 | 12,000 | defense | +8 evasion | Chaff Cloud (2E, 2-turn CD): +20 evasion for 2 turns + enemies -10 accuracy for 1 turn | Broadband (+5 evasion) / Sensor Jam (-15 enemy accuracy for 1 turn) |
| `phase_drive` | Phase Shift Drive | 2 | 16,000 | defense | +10 evasion | Phase Shift (3E, 3-turn CD): 100% evasion for 1 turn (unhittable) | Lingering (+25 evasion for 1 turn after phase) / Aggressive (next attack after phase: +25% damage) |
| `ghost_plating` | Ghost Plating | 3 | 32,000 | defense | +12 evasion, +10% flee | Vanish (4E, 4-turn CD): Cannot be targeted for 2 turns | Cloak (+15 evasion) / Ambush (+40% damage on first attack from stealth) |
| `quantum_blink` | Quantum Blink Engine | 3 | 48,000 | defense | +15 evasion, +20% flee | Blink (5E, 5-turn CD): Teleport — dodge ALL attacks this turn + reposition (guaranteed next hit) | Emergency Jump (if hull < 25%: auto-flee, one use per combat) / Predator (Counterstrike stacks cap at 5 instead of 3) |
| `lightweight_frame` | Lightweight Frame | 1 | 3,000 | defense | +5 evasion, -15 hull | Nimble Dodge (1E): +10 evasion for 1 turn | Stripped Down (+3 evasion, -10 hull) / Balanced (+2 evasion, no hull penalty) |

---

### New Upgrades — Utility Slot Equipment (Identity-Supporting)

These go in utility slots and provide secondary support for each identity.

| ID | Name | Tier | Price | Slot | Identity | Effect |
|----|------|------|-------|------|----------|--------|
| `hull_sealant` | Emergency Hull Sealant | 1 | 3,000 | utility | Hull | Auto-restore 5 hull when dropping below 50% (once per combat) |
| `backup_plating` | Backup Armor Plating | 2 | 9,000 | utility | Hull | +1 armor when hull is below 50% |
| `damage_dampener` | Kinetic Damage Dampener | 2 | 11,000 | utility | Hull | Kinetic damage reduced by 10% |
| `shield_battery` | Auxiliary Shield Battery | 1 | 3,500 | utility | Shield | +10 max shields |
| `regen_coil` | Shield Regeneration Coil | 2 | 10,000 | utility | Shield | +2 shield regen/turn |
| `ion_filter` | Ion Interference Filter | 2 | 8,000 | utility | Shield | Ion bonus damage reduced by 15% |
| `agility_mod` | Agility Modification | 1 | 2,500 | utility | Evasion | +3 evasion |
| `smuggler_rig` | Smuggler's Rigging | 2 | 8,000 | utility | Evasion | +5 evasion + hidden compartment (if ship lacks one) |
| `threat_analyzer` | Threat Analysis Computer | 2 | 12,000 | utility | Evasion | Counterstrike bonus increased to +15% per dodge (from +10%) |

---

### Skill Tree Expansion — Defense Paths

The existing Combat skill tree has `evasive_maneuvers`, `shield_mastery`, and `hull_reinforcement`. We expand these into three full branches.

#### Hull Branch (Juggernaut Path)
```
hull_reinforcement (existing, 3 levels: +5% max hull per level)
    ├── armor_expertise (NEW, 3 levels: +1 armor per level)
    │       └── last_stand_mastery (NEW, 2 levels: Last Stand threshold +5% per level, bonus damage +5% per level)
    ├── field_repairs (NEW, 3 levels: repair costs -15% per level)
    └── endurance (NEW, 2 levels: +3% hull damage reduction per level)
            └── juggernaut (NEW, capstone, 1 level: When hull > 75%, immune to critical hits. When hull < 25%, +25% damage)
```

#### Shield Branch (Sentinel Path)
```
shield_mastery (existing, 2 levels: +10% shield effectiveness per level)
    ├── shield_regen (NEW, 3 levels: +2 shield regen per turn per level)
    │       └── overcharge (NEW, 2 levels: max shield overflow +25% per level, up to +50%)
    ├── shield_discipline (NEW, 2 levels: shield break vulnerability reduced by 10% per level)
    └── energy_shields (NEW, 2 levels: shield restore moves cost 1 less energy per level)
            └── sentinel (NEW, capstone, 1 level: Shields regenerate double when above 50%. Shield break triggers emergency restore of 20% shields)
```

#### Evasion Branch (Ghost Path)
```
evasive_maneuvers (existing, 3 levels: +5% dodge chance per level)
    ├── afterburner (NEW, 3 levels: +5 evasion per level, +5% flee chance per level)
    │       └── counterstrike_mastery (NEW, 2 levels: Counterstrike bonus +5% per level, max stacks +1 per level)
    ├── light_foot (NEW, 2 levels: no evasion decay after being hit at level 1; graze damage reduced to 20% at level 2)
    └── slippery (NEW, 2 levels: +10% flee chance per level, +5% encounter avoidance per level)
            └── ghost (NEW, capstone, 1 level: First turn of combat: +30 evasion. If not hit in a round, next attack is guaranteed crit)
```

---

### Enemy Design Implications

Enemies should also lean into identities, creating readable combat puzzles:

**Hull-Heavy Enemies** (Pirate Heavy, Patrol Vessel):
- High hull, low evasion. Weak to sustained DPS and Burn.
- Counter: Use Plasma for DoT, or Ion to strip shields then burst hull.
- Telegraphed behavior: FORTIFYING (damage reduction buff)

**Shield-Heavy Enemies** (Shield Drone — NEW, Elite Patrol):
- High shields with regen. Break the shield, then burst.
- Counter: Ion weapons (150% shield damage), or energy drain to prevent shield restore.
- Telegraphed behavior: CHARGING (shield restore incoming)

**Evasion-Heavy Enemies** (Pirate Scout, Smuggler):
- High evasion, paper hull. Hard to hit but fold when connected.
- Counter: AoE weapons (can't dodge area effects), Cryo (reduces evasion via Chill stacks), accuracy buffs.
- Telegraphed behavior: EVADING (evasion buff active)

**New Enemy Templates to Add:**

| Enemy | Hull | Shields | Evasion | Identity | Behavior |
|-------|------|---------|---------|----------|----------|
| Shield Drone | 20 | 60 | 5 | Shield | Pure shield wall; regenerates 8/turn, exists to waste your ammo |
| Armored Transport | 120 | 15 | 3 | Hull | High armor (4), slow. Hits hard but infrequently |
| Ghost Raider | 35 | 15 | 35 | Evasion | Appears, strikes hard, tries to flee. Counterstrike-style attacks |
| Ion Striker | 50 | 10 | 20 | Anti-shield | Uses Ion weapons exclusively. Shield builds' nightmare |
| Cryo Interceptor | 55 | 25 | 18 | Anti-evasion | Uses Cryo weapons. Evasion builds' nightmare (Chill reduces evasion) |
| Plasma Bomber | 45 | 20 | 12 | Anti-hull | Uses Plasma weapons. Hull builds' concern (Burn DoT bypasses armor) |

---

### Interaction with Existing Elemental Weapons

The defensive triangle creates natural interactions with the elemental system:

| Element | vs Hull (Juggernaut) | vs Shield (Sentinel) | vs Evasion (Ghost) |
|---------|---------------------|---------------------|-------------------|
| **Kinetic** | Neutral (armor reduces flat) | Neutral | Neutral |
| **Plasma** | **Strong** — Burn DoT bypasses armor | Neutral | Neutral |
| **Ion** | Weak — 75% hull damage | **Strong** — 150% shield damage | Neutral |
| **Cryo** | Neutral | Neutral | **Strong** — Chill reduces evasion (-5 per stack) |
| **Voltaic** | Neutral (suppressed reduces their damage) | Neutral | Weak — suppressed doesn't help vs dodge |

This creates a double layer of strategy: your DEFENSIVE identity determines which enemy WEAPONS threaten you, and your OFFENSIVE element determines which enemy DEFENSES you can break. A hull ship dreads Plasma enemies. A shield ship fears Ion. An evasion ship struggles against Cryo.

---

### Visual Design

#### Hull Identity Visuals
- **Ship tint**: Warm orange/rust glow on hull-heavy ships
- **Armor hit effect**: Metallic sparks + "DEFLECTED" text for damage reduced by armor
- **Last Stand**: Red pulsing hull outline, warning sirens, sparks flying
- **Repair move**: Welding sparks, orange particles converging on ship

#### Shield Identity Visuals
- **Shield bubble**: Existing system, but more prominent on shield ships (thicker, brighter)
- **Regen tick**: Small blue pulse each turn shields regenerate
- **Overcharge**: Shield bubble glows brighter, expands slightly when above 100%
- **Shield break**: Dramatic shatter effect (existing), plus the vulnerability flash (red flicker)
- **Ion hit on shields**: Crackling electricity, distinct from normal shield impact

#### Evasion Identity Visuals
- **Dodge animation**: Ship jinks sideways briefly (short lateral movement)
- **Graze**: Projectile visually clips past the ship (near-miss particle trail)
- **Counterstrike glow**: Ship glows brighter with each dodge (stacking intensity)
- **Phase Shift**: Ship becomes translucent/ghostly for the duration
- **Vanish**: Ship fades to near-invisible, afterimage effect

---

### Upgrade Counts Summary

| Category | Hull | Shield | Evasion | Total New |
|----------|------|--------|---------|-----------|
| Defense slot | 6 | 6 | 6 | **18** |
| Utility slot | 3 | 3 | 3 | **9** |
| Skill nodes | 5+capstone | 5+capstone | 5+capstone | **18** |
| Enemy templates | — | — | — | **6** |
| **Total new content** | | | | **51 items** |

Combined with existing 85 upgrades → **112 total upgrades** (18 defense + 9 utility new).
Combined with existing 28 enemy templates → **34 total enemy templates**.
Combined with existing 89 skill nodes → **107 total skill nodes**.

---

### Implementation Phases

#### Phase 12A: Core Mechanics (HIGH effort)
- Add `armor` field to ShipType and combat state
- Implement armor damage reduction in combat engine
- Implement passive shield regen per turn in combat engine
- Implement graze system (near-miss 30% damage)
- Implement evasion diminishing returns above 50
- Implement evasion decay after being hit (-5 for 1 turn)
- Add identity passive flags to ShipType (`hull_passives`, `shield_passives`, `evasion_passives`)
- Implement Last Stand, Structural Integrity, Overcharge Capacity, Shield Break Vulnerability, Counterstrike, Slippery, Light Frame Vulnerability passives
- Tests for all new mechanics

#### Phase 12B: Upgrades & Equipment (MEDIUM effort)
- Add 18 new defense slot upgrades to upgrades.json
- Add 9 new utility slot upgrades to upgrades.json
- Add combat moves for all new upgrades
- Add tuning options for all new upgrades
- Wire passive bonuses (armor, shield_regen, evasion) through upgrade_manager
- Tests for upgrade effects in combat

#### Phase 12C: Skill Tree Expansion (MEDIUM effort)
- Add 18 new skill nodes to skill_trees.json (6 per branch + 3 capstones)
- Wire new bonus types through combat state initialization
- Ensure capstone skills have meaningful prerequisites
- Tests for skill bonuses in combat

#### Phase 12D: Enemy Templates (LOW effort)
- Add 6 new enemy templates to enemies.json
- Assign identity-appropriate behaviors and moves
- Distribute across systems by difficulty
- Tests for new enemy combat resolution

#### Phase 12E: Visual Pass (MEDIUM effort)
- Armor deflection particles and text
- Shield regen pulse animation
- Dodge/graze animations
- Counterstrike glow intensity
- Last Stand visual effects
- Identity-colored health bar accents

#### Phase 12F: Balance & Integration (LOW effort)
- Rebalance existing ship base stats to formalize identity leans
- Update ship descriptions to reference defensive identity
- Ensure upgrade availability matches progression curve
- Playtest tuning pass

---

### Balance Guardrails

- **Armor cap**: Maximum 10 armor from all sources. Prevents chip damage from becoming completely irrelevant.
- **Shield regen cap**: Maximum 15 per turn from all sources. Prevents passive regen from exceeding typical damage output.
- **Evasion soft cap**: Diminishing returns above 50. Effective evasion of 70+ should require massive investment and still allow 15-20% hit chance.
- **Graze floor**: Graze damage minimum is 2 (prevents 0-damage grazes on high-armor ships).
- **No stacking identity passives across identities**: A ship can benefit from hull AND shield upgrades, but identity passives (Last Stand, Overcharge, Counterstrike) only activate on ships whose ShipType has that identity flag. You can't get Counterstrike on a War Frigate.
- **Upgrade slot tension**: Defense slots are limited (1-3 per ship). You can mix identities but you can't max all three. This is the core build constraint.
- **Enemy identity counters should be telegraphed**: "ION STRIKER — your shields won't help here" in the encounter flavor text. The player should know before combat starts.

---

## Balance Notes

- All numbers in this document are starting points. Playtesting will determine final values.
- The energy rebalance should be tested at multiple points: early game (weak weapons, low pool) through late game (powerful weapons, upgraded pool).
- Elemental weapons should be balanced against Kinetic: raw DPS of Kinetic should be ~15-20% higher than elemental weapons to compensate for the lack of secondary effects.
- Burn DoT should be high enough to matter (not ignorable) but not so high that Plasma dominates all other elements.
- Cryo Freeze at 3 stacks is very powerful (skip a turn). Energy cost and stack duration must be tuned so freezing every 3 turns requires sustained commitment.
- Ion shield multiplier (150%) should make it clearly the best choice against heavy-shield enemies, but 75% hull penalty should discourage using it once shields are down.
- Enemy telegraphing should be introduced gradually: early enemies telegraph every turn, late-game "tactical" enemies only telegraph charge attacks.
- New moves should be unlocked through the existing upgrade/skill tree progression, not given all at once.
- Elemental mastery skill nodes should be mid-to-late in the Combat skill tree, rewarding specialization.
- Ship class identity (energy pool/regen differences) should reinforce the existing ship progression, not create mandatory choices.
- **Defensive identity balance**: Hull should survive ~20% more damage than shields to compensate for repair costs. Evasion should survive ~10% less on average but with higher variance and out-of-combat advantages.
- **Armor vs Burn**: Burn DoT bypasses armor intentionally. This is the hard counter to hull builds and prevents armor stacking from creating invulnerable ships.
- **Shield regen vs burst damage**: Shield regen should sustain against 1-2 weak enemies but be overwhelmed by 3+ attackers or boss-level burst. If shield regen makes a build feel invulnerable in normal encounters, the regen cap is too high.
- **Evasion graze system**: The 30% graze damage ensures evasion is never all-or-nothing. High evasion reduces average damage taken smoothly. If evasion builds feel too "coin flippy," adjust graze threshold or damage percentage.
- **Identity locking**: Ships should lean toward an identity but not be locked. A War Frigate with shield upgrades should work — just not as well as a pure hull build. The identity passives (Last Stand, Counterstrike, etc.) are the specialization reward.
- **Upgrade availability**: Hull upgrades should be available at industrial stations (Forgeworks, Breakstone). Shield upgrades at science/diplomatic stations (Axiom Labs, Stellaris Port). Evasion upgrades at frontier/criminal stations (Haven's Rest, Crimson Reach). This ties identity to faction exploration.
