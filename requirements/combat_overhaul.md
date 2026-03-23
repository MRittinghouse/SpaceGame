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

### UPCOMING (JRPG Evolution)

| Phase | Description | Effort | Impact | Dependencies |
|-------|-------------|--------|--------|-------------|
| **8** | Momentum Gauge + Ship Ultimates | HIGH | CRITICAL | None |
| **9** | Crew Combo Abilities | MEDIUM | HIGH | Phase 8 (needs Momentum threshold) |
| **10** | Boss Encounter System | HIGH | HIGH | Phases 8-9 (bosses should test all systems) |
| **11** | Tutorial Integration | MEDIUM | HIGH | Phases 8-10 (tutorials explain new mechanics) |
| **7B-E** | Ship Sprite Generation | HIGH | MEDIUM | Art pipeline (API budget) |

### Recommended Implementation Order
1. **Phase 8 (Momentum)** first — it's the backbone. Ship Ultimates give every ship class identity.
2. **Phase 9 (Crew Combos)** next — layered on top of Momentum threshold 1. Rewards party composition.
3. **Phase 10 (Bosses)** third — uses all existing systems (momentum, combos, elements, telegraphing).
4. **Phase 11 (Tutorials)** last — explains everything that's been built.

### Future Expansion Opportunities (post-playtesting)
- Elemental visual pass: distinct projectile colors/sprites per element
- Enemy elemental resistances/weaknesses
- Skill tree integration: elemental mastery nodes + momentum mastery
- Blue Magic equivalent: salvage enemy technology after boss kills
- New Game+ mode: bosses appear as random encounters, momentum builds faster
- Boss Rush mode: fight all bosses in sequence for leaderboard score

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
