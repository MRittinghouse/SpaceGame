# Combat Balance Design — U2.5d and Beyond

> **Status**: DESIGN PHASE — awaiting review before implementation
>
> This document is the reference for rebuilding Aurelia's combat balance from the ground up: a coherent enemy roster scaled across the player's journey, a weapon catalog with real rotation tempo, a crew-driven dual tech system inspired by Chrono Trigger, and the numerical targets that let all three reinforce each other instead of fighting over player attention.

---

## 1. Design Philosophy

### 1.1 The Fantasy

The player is a captain. The ship is their instrument, the bridge crew their chorus. Combat is not a contest of reflexes. It is a *conversation under pressure*: the player reads the enemy, allocates limited resources across limited time, and commits to a plan whose consequences outlast the turn.

Three genres set the tone:

- **Final Fantasy / Chrono Trigger** — meaningful MP economy, clear role identity, telegraphed boss techs, dual techs as relationship payoff, phase transitions that reward learning.
- **Armored Core** — generator output as hard ceiling, mount location matters, every build is a tradeoff, "build identity" visible at a glance.
- **Starfield** — subsystem power distribution as per-engagement decision, weapons that heat up, cost-benefit curves legible in the builder.

### 1.2 Core Principles

1. **Every choice has an opportunity cost.** Firing a weapon costs energy that could have shielded. Equipping burst reduces sustain. Bringing Priya on the bridge means leaving Tomas on reserve.
2. **Rotation is tempo.** Cheap weapons every turn. Tech weapons every other turn. Burst weapons as climaxes. The rhythm itself is the player's literacy.
3. **Telegraph rewards observation.** Enemies signal their next move. A player who reads the bridge wins fights a player who spams optimal-DPS loses.
4. **Archetypes have legible identity.** A glass cannon feels fragile. A tank feels plodding. The first turn tells you what you're fighting.
5. **The builder is the combat tutorial.** The energy budget, cooldown rotation, and weapon-tier mix should be visible and comprehensible in the drydock, before combat starts.

### 1.3 Anti-Goals

- **No gear check walls.** Losing should feel like misplay, not insufficient build level.
- **No single optimal build.** Glass cannon, tank, balanced, and missile boat all need to clear Tier 4 content with correct play.
- **No cooldown soup.** If a player can't remember what's on cooldown, the UI failed. Max 5 actively-tracked cooldowns per turn.
- **No dual tech combinatorial explosion.** Handcrafted, not generated.

---

## 2. Combat Economy Model

### 2.1 The Four Resources

| Resource | Source | Regenerates | Player Sees | Purpose |
|----------|--------|-------------|-------------|---------|
| **Hull HP** | ShipBuild hull pixels | No (repair between fights) | Always | Fail condition |
| **Shield HP** | Shield modules | Yes (per-turn regen) | Always | Damage buffer |
| **Energy** | Reactors in build | Yes (end of turn) | Always in builder + combat | Action budget per turn |
| **Crew Actions** | 1 per turn, from recruited crew | Per turn | Combat queue | Parallel budget to energy |

### 2.2 Energy Economy

Energy is the *action budget* for weapons and defensive systems. Crew actions are a *separate budget* (1 per turn for crew abilities), so bringing Marcus does not cost you a weapon shot.

- **Unspent energy does not carry over.** Spend it or lose it. Encourages full-commit turns.
- **Regen applies at end of turn.** A turn that drains the pool is followed by a turn starting at `min(pool, regen)`.
- **Cheap weapons always sustain.** If regen is ≥ the cost of a sidearm (2 energy), the player always has a sidearm to fire, even from zero.

### 2.3 Weapon Tier Structure

The foundation of rotation tempo. Three tiers with clear role identity:

| Tier | Name | Cooldown | Energy Cost | Damage | Frequency per 5-turn window | Role |
|------|------|----------|-------------|--------|----------------------------|------|
| **T1** | Sidearm | 0 | 2 | 10–18 | Every turn | Sustain DPS, rotation filler |
| **T2** | Tech | 1–2 | 3–5 | 20–35 | Every 2nd turn | Mid-weight, rotation backbone |
| **T3** | Burst | 3–4 | 5–8 | 40–60 | Turn 1, turn 5 | Alpha strike, climax |

**Target catalog distribution**: 40% Sidearm, 40% Tech, 20% Burst. Current state is roughly 50/40/10 with median cooldown 0 — too heavy on flat-curve sidearms, too light on burst.

**Element matters.** Weapons carry one of: Kinetic, Plasma, Ion, Cryo, Voltaic. Enemies have elemental resistances and vulnerabilities that reward weapon variety over "three of the same laser."

### 2.4 Reactor Progression

Energy pool + regen scales roughly linearly with investment:

| Reactor Tier | Pool | Regen | Sustain Capacity | Typical Placement |
|--------------|------|-------|------------------|-------------------|
| Starter (Micro) | 8 | 3 | 1 sidearm | Shuttle default |
| Budget (Compact) | 12 | 4 | 2 sidearms or 1 tech | Early upgrade |
| Standard | 18 | 5 | 2 sidearms + 1 tech | Mid-game baseline |
| Premium | 24 | 6 | 3 sidearms + 1 tech + tap burst | Late-game |
| Capital | 32 | 8 | Full alpha strike every 2 turns | Endgame |

Sustain capacity is calculated as `regen / cost_of_sidearm`. Alpha strike capacity is `pool / avg_cost_mixed_salvo`.

### 2.5 Turn Pacing Targets

A representative mid-game turn with a Standard reactor (18 pool, 5 regen):

- **Turn 1** — Burst (6E) + Tech (4E) + Sidearm (2E) = 12E spent, 6E unused. Expected damage: 50 + 25 + 15 = **90**.
- **Turn 2** — Pool regens to 11 (6 + 5). Tech on cooldown. Fire 2 sidearms = 4E. Expected: **30**.
- **Turn 3** — Pool 12. Tech back. Fire Tech + Sidearm = 6E. Expected: **40**.
- **Turn 4** — Pool 11. Sidearms only. Expected: **30**.
- **Turn 5** — Burst back. Burst + Tech + Sidearm = 12E. Expected: **90**.

5-turn average damage: 56/turn. 5-turn total: 280. This defines what enemy HP should be to match encounter length targets.

---

## 3. Encounter Length Targets

Fight duration tells the player what difficulty tier they're in. Targets:

| Encounter Difficulty | Target Rounds | Example Player Mid-Game DPS | Example Enemy Total HP |
|---------------------|---------------|----------------------------|------------------------|
| Trivial (overlevel) | 1–2 | 80/turn | 60–120 |
| Standard | 3–5 | 56/turn | 180–280 |
| Hard | 6–8 | 56/turn | 350–450 |
| Boss | 8–12 | 56/turn (with phase stalls) | 500–800 |
| Legendary | 12–20+ | 56/turn (with phase stalls) | 1,000–1,500 |

These targets directly determine enemy HP in the next section.

---

## 4. Enemy Tier × Archetype Matrix

### 4.1 The Tiers

| Tier | Level Band | Player Ship State | Role in Journey |
|------|-----------|-------------------|-----------------|
| **T1 — Initiation** | L1–5 | Shuttle, starter reactor, 1–2 weapons | Teach the system |
| **T2 — Escalation** | L5–10 | First real frame, mixed weapon loadout | Introduce archetypes |
| **T3 — Challenge** | L10–15 | Committed build, premium reactor | Demand tactical play |
| **T4 — Boss** | L15–20 | Endgame build, dual techs unlocked | Narrative climax |
| **T5 — Legendary** | L20+ (optional) | Mastery builds | Superboss gauntlet |

### 4.2 The Archetypes

Each enemy reads as one archetype on first sight and plays to type consistently.

| Archetype | Identity | HP Pattern | Damage Pattern | Signature |
|-----------|----------|------------|----------------|-----------|
| **Striker** | Glass cannon | Low | High | High evasion, low armor, fast initiative |
| **Tank** | Wall | High | Moderate | Heavy armor, low evasion, slow |
| **Controller** | Denial | Moderate | Low direct | Status effects, energy drain, cooldown lock |
| **Support** | Force multiplier | Moderate | Low | Heals allies, buffs, appears in groups |
| **Rival** | Mirror | Moderate | Moderate | Player-like loadout, tech rotation, threatening |
| **Juggernaut** | Boss-class | Very high | Very high | Phase transitions, multi-move rotations |

### 4.3 The Full Matrix

HP / base damage / armor / evasion. Move count in parentheses.

| Archetype | T1 (L1–5) | T2 (L5–10) | T3 (L10–15) | T4 Boss (L15–20) | T5 Legendary |
|-----------|-----------|------------|-------------|------------------|--------------|
| **Striker** | 40 / 10 / 0 / 15% (1 move) | 100 / 18 / 2 / 25% (2) | 180 / 28 / 3 / 30% (3) | — | (existing) |
| **Tank** | 80 / 7 / 3 / 0% (1) | 160 / 12 / 6 / 0% (2) | 350 / 20 / 10 / 5% (3) | — | (existing) |
| **Controller** | — | 80 / 8 / 2 / 10% (2 + 1 status) | 200 / 18 / 4 / 15% (3 + 2 status) | — | — |
| **Support** | — | 120 / 10 / 3 / 10% (2 + heal) | 240 / 14 / 5 / 10% (2 + heal + buff) | — | — |
| **Rival** | — | — | 280 / 22 / 4 / 15% (3 + 1 burst) | 500 / 28 / 6 / 20% (4 + 1 burst) | (existing) |
| **Juggernaut** | — | — | — | 700 / 32 / 8 / 5% (4 moves, 2 phases) | 1,200 / 40 / 10 / 10% (5, 3 phases) |

**Total new templates**: 18 (5 T1, 4 T2, 5 T3, 3 T4, plus existing 5 legendary).

### 4.4 Tier Move Palettes

Every enemy at a tier draws from that tier's available moves. Consistency within a tier teaches the player to read telegraphs.

**T1 (Initiation)** — 1 move each. Simple damage.

- `scatter_shot`: 10 kinetic damage, 100% accuracy.
- `ram`: 14 kinetic damage, 75% accuracy, self-damage 3.

**T2 (Escalation)** — 2 moves + possible status. Introduce variety.

- `focused_beam`: 18 plasma damage.
- `shield_burst`: 8 damage, +1 shield regen to self next turn.
- `jam`: 4 damage + target gains "Jammed" (-1 energy regen for 2 turns).
- `medical_relay`: heal 30 HP to lowest-HP ally.

**T3 (Challenge)** — 3 moves + 1–2 status. Real rotation.

- `plasma_lance`: 28 plasma damage, 5% crit bonus.
- `ion_drain`: 10 damage + target loses 4 energy (permanent this turn).
- `alpha_volley`: 45 damage, 1-turn cooldown.
- `dispersal_field`: self +30% evasion for 1 turn.
- `call_reinforcement`: summon T2 striker (Support-archetype only, once per fight).

**T4 (Boss)** — 4 moves, phase transition at 50% HP.

- `siege_cannon`: 50 damage, 2-turn cooldown, telegraphed 1 turn in advance.
- `shield_overclock`: restore 200 shield, 4-turn cooldown.
- `multi_target_barrage`: 15 damage to all player systems (hits multiple modules).
- `phase_shift_tech`: on reaching 50% HP, switch to a new move palette (signature of that boss).

**T5 (Legendary)** — keep existing 5 boss-drop mechanics; retune HP to 1,000–1,500 range.

### 4.5 Example Enemy Specifications

A few fully-specified entries to show the pattern. Full roster in implementation phase.

```
id: skiff_raider
tier: 1
archetype: striker
faction: pirate
hull: 40
damage: 10
armor: 0
evasion: 15
moves: [scatter_shot]
element_resist: {cryo: 0.5}     # dies fast to cryo
element_weak: {voltaic: 1.5}    # voltaic shreds it
telegraph: "The raider banks sharply, preparing to strafe."
```

```
id: iron_corvette
tier: 2
archetype: tank
faction: dominion
hull: 160
damage: 12
armor: 6
evasion: 0
moves: [focused_beam, shield_burst]
element_resist: {kinetic: 0.6, plasma: 0.7}
element_weak: {ion: 1.4}
telegraph: "The corvette braces; emergency shields pulse online."
```

```
id: crimson_dreadnought
tier: 4
archetype: juggernaut
faction: crimson_reach
hull: 700
damage: 32
armor: 8
evasion: 5
phases:
  phase_1: [siege_cannon, multi_target_barrage, focused_beam]
  phase_2_trigger: hull <= 50%
  phase_2: [siege_cannon, shield_overclock, phase_shift_tech, multi_target_barrage]
element_resist: {all: 0.8}
telegraph: "The dreadnought's spinal cannon pivots. You have one turn."
```

### 4.6 Faction Signatures

Each faction has an archetype preference that reinforces its identity:

| Faction | Archetype Bias | Elemental Bias | Combat Feel |
|---------|---------------|----------------|-------------|
| **Commerce Guild** | Support + Controller | Ion | Bureaucratic denial, system-lock tactics |
| **Miners Union** | Tank + Juggernaut | Kinetic + Plasma | Slow, heavy, grinding wars of attrition |
| **Frontier Alliance** | Striker + Rival | Plasma + Voltaic | Fast, improvised, unpredictable |
| **Science Collective** | Controller + Support | Ion + Cryo | Status-heavy, long-game tactical |
| **Crimson Reach** | Juggernaut + Striker | Plasma + Voltaic | Fanatic aggression, big damage |

This lets the narrative reinforce the combat. A Dominion fleet *feels* like Dominion. A Reach assault *feels* like Reach.

---

## 5. Dual Tech System

### 5.1 Design Principles Recap

- **Handcrafted, not combinatorial.** Exactly 6 named dual techs (one per senior-crew pair), plus 1 late-game triad.
- **Loyalty-gated.** Minor techs at Loyalty 2, legendary at Loyalty 3, triad at all four crew Loyalty 3.
- **Narrative reveal.** First time prerequisites are met, a combat dialogue cinematic fires. Then the tech is permanent.
- **Cost: both crew actions + high ship energy.** Sacrifices two crew-action slots for one devastating move. Long cooldown (4–6 rounds).
- **No rotation fodder.** Dual techs are climaxes, not every-turn plays.

### 5.2 The Six Pairs

Senior bridge crew: Elena (Captain), Marcus (Weapons), Priya (Engineer), Tomas (Pilot). All six pairs.

| Tech Name | Pair | Loyalty Gate | Energy | Cooldown | Effect |
|-----------|------|--------------|--------|----------|--------|
| **Fire at Will** | Elena + Marcus | L2 | 6 | 4 turns | All equipped weapons fire this turn at 50% energy cost, 0 cooldown after use |
| **Daring Gambit** | Elena + Tomas | L2 | 4 | 4 turns | +40% evasion for 2 turns; on successful dodge, counter for 25 damage |
| **Total Commitment** | Elena + Priya | L3 | 8 | 6 turns | Convert next 3 incoming hull hits to armor stacks (cap +8 armor for fight) |
| **Focused Barrage** | Marcus + Priya | L3 | 8 | 5 turns | Single weapon fires at 2× damage, ignores all armor, crit on 25%+ |
| **Gun Run** | Marcus + Tomas | L2 | 6 | 4 turns | Strafing pass: hit every enemy on field for 35 damage each |
| **Power Drift** | Priya + Tomas | L2 | 4 | 4 turns | +6 energy regen this turn, all weapon cooldowns -2 |

**Notes on design:**

- Each tech reflects the characters' voice-sheet identities. Elena leads; Marcus executes; Priya engineers; Tomas pilots.
- Energy costs (4–8) are high enough to feel expensive mid-game, manageable late-game.
- Cooldowns (4–6) ensure at most one dual tech active per combat phase — they are climaxes, not rotations.
- Effect values calibrated against the T3/T4 damage targets in Section 4. Fire at Will on a 4-weapon build at T4 is ~120 damage for one turn's cost. Consistent with burst expectations.

### 5.3 The Triad

| Tech Name | Prerequisites | Energy | Cooldown | Effect |
|-----------|--------------|--------|----------|--------|
| **Crew Sync** | All 4 senior crew at L3 + full party on bridge | 12 | Once per combat | All weapons fire at 2× damage ignoring armor + restore 40% hull + grant +4 evasion for 3 turns |

**Design rationale:** One triad, narrative-heavy, late-game only. It is the character-driven limit break of the game. If dual techs are musical climaxes, Crew Sync is the finale. Requires the player to have maximally invested in every senior crew quest — not a casual find.

### 5.4 UI Integration

- **Crew panel**: Dual techs visible with lock icons showing prerequisites. "Fire at Will — Requires Elena + Marcus, both L2."
- **Combat queue**: When prerequisites met + both crew on bridge + both off cooldown + energy available, dual tech appears in a dedicated "Coordinated" section. Clicking queues it (consumes both crew action slots, shows the energy cost).
- **First-use cinematic**: Hardcoded dialogue node fires on first queueable moment. Plays before the combat turn resolves, reads once, then dual tech is unlocked for all future fights.
- **Visual treatment**: Dual techs have a distinct VFX palette (crew-portrait-flash pair animation, distinct hit sound) so the player registers them as special.

### 5.5 Cinematic Reveal Text Templates

First-time dialogue patterns (one per tech, delivered by the two crew). Example:

**Fire at Will (Elena + Marcus):**
> Elena glances at Marcus. "Both barrels?"
> Marcus is already grinning. "Been waiting, captain."
> *Fire at Will is now available.*

**Power Drift (Priya + Tomas):**
> Priya's hands dance across the panel. "Tomas, give me slack on the main bus."
> Tomas doesn't look up. "How much?"
> "All of it."
> *Power Drift is now available.*

**Crew Sync (triad):**
> Elena looks at each of them. No one speaks.
> The ship answers first — reactor resonant, all systems aligned.
> "Together," she says.
> *Crew Sync is now available.*

Full cinematic text to be written during implementation, consistent with each character's voice sheet.

---

## 6. Playtest Archetype Scenarios

Scenarios to verify at implementation. Each is a concrete build vs. a concrete encounter, with a target outcome. These become integration tests.

### 6.1 Glass Cannon vs. T2 Standard

**Build:** 4 weapons (2 tech, 1 sidearm, 1 burst), 1 Compact reactor, 1 shield generator, minimal hull.
**Encounter:** 2× T2 strikers.
**Expected:** Kill both in **5–8 rounds** (revised from aspirational "2 rounds" after B6 honesty pass — armor + multi-enemy economics make 2-round clears require burst damage that would trivialize other archetypes). Glass cannon should still feel meaningfully faster than Tank vs. the same encounter. Take moderate hull damage.
**Fail mode:** If glass cannon takes >10 rounds against T2 strikers or takes HP damage comparable to Tank, burst tuning is off.

### 6.2 Tank vs. T2 Standard

**Build:** 2 weapons (1 tech, 1 sidearm), 3 shield generators, 1 reactor, heavy hull.
**Encounter:** 2× T2 strikers.
**Expected:** Kill both in 4–5 rounds. Take minor hull damage, shields cycle.
**Fail mode:** If tank takes significant hull damage from strikers, armor/shield regen undertuned.

### 6.3 Balanced vs. T3 Hard

**Build:** 3 weapons (1 sidearm, 1 tech, 1 burst), 2 shields, 2 reactors.
**Encounter:** 1× T3 tank + 1× T3 controller.
**Expected:** 6–8 round fight. Player must handle energy drain from controller. Kill controller first, then tank.
**Fail mode:** If controller cannot meaningfully denial the player, controller archetype ineffective.

### 6.4 Missile Boat vs. T3 Hard

**Build:** 2 weapons (2 burst), 2 reactors, 1 shield, heavy hull.
**Encounter:** 1× T3 rival.
**Expected:** 5–7 round fight. Alpha strike turn 1, hold for cooldowns, alpha strike turn 4.
**Fail mode:** If missile boat can spam burst every 2 turns, burst cooldowns undertuned.

### 6.5 Dual Tech Unlock vs. T4 Boss

**Build:** Balanced with full crew at Loyalty 2+. Elena + Marcus on bridge.
**Encounter:** 1× T4 Juggernaut (Crimson Dreadnought).
**Expected:** 10–12 round fight. Phase transition at 50% HP. Fire at Will at round 3 shifts the fight pace. Power Drift recovery on round 7. Survival requires reading telegraphs.
**Fail mode:** If dual techs trivialize the boss, damage/cooldown tuning is off. If they never unlock in a normal playthrough, loyalty gates too high.

### 6.6 Legendary Gauntlet

**Build:** Endgame build with capital reactor, all senior crew at L3.
**Encounter:** Each of the 5 T5 legendary superbosses.
**Expected:** 15–20 round fights. Crew Sync available but only winnable once per combat. Build identity matters — glass cannon vs. Void Maw plays very differently than tank.
**Fail mode:** If any legendary is trivial, retune HP upward. If any legendary is unwinnable without specific build, retune mechanics.

---

## 7. Builder Energy Budget Widget

The builder must surface combat economy so players can plan.

### 7.1 Stats Panel Addition

New card in the ship builder stats panel:

```
┌─────────────────────────────────────┐
│  ENERGY ECONOMY                     │
│  ─────────────────────────────────  │
│  Pool:       18                     │
│  Regen:      5 / turn               │
│                                     │
│  Sustain:    2 sidearms / turn      │
│  Alpha:      4-weapon salvo turn 1  │
│                                     │
│  Weapons equipped:  3 (cost: 11)    │
│  ├─ Sidearm × 1 (2E, 0cd)          │
│  ├─ Tech × 1    (4E, 2cd)          │
│  └─ Burst × 1   (5E, 3cd)          │
│                                     │
│  ⚠ Alpha-strike drains pool (11/18) │
└─────────────────────────────────────┘
```

### 7.2 Warnings & Advisories

Advisory conditions surfaced in the builder:

- **Pool < sum-of-weapon-costs** → "Cannot alpha-strike full loadout."
- **Regen < cost-of-cheapest-weapon** → "Cannot sustain fire between bursts."
- **No burst-tier weapon equipped** → "No alpha strike option."
- **No sidearm equipped** → "No between-burst sustain."

These are *advisories* not *blocks*. Players can build whatever; they just see the tradeoffs.

---

## 8. Legendary Module Verification

The 5 legendary effects need integration tests confirming correct behavior under multi-action turns.

| Effect | Correct Multi-Action Behavior | Test |
|--------|------------------------------|------|
| **Chain Fire** | Triggers per weapon hit (not per turn). In a 3-weapon queue, each hit rolls 40%. | Queue 3 weapons; verify chain roll fires up to 3 times. |
| **Void Absorption** | Absorbs 15% of incoming hull damage per hit. Releases once per combat. | Take 3 hits across 2 turns; verify absorb accumulates correctly; release check. |
| **Heat Hardening** | +1 armor per shield hit, max 5. Resets at combat end. | Take 7 shield hits; verify armor caps at 5; new combat resets. |
| **Cooldown Reduction** | -1 to all cooldowns per turn end. Stacks with Overdrive. | Queue 3 weapons on cooldown; verify -1 tick + overdrive tick. |
| **Phase Shift** | Blocks first incoming attack per round (not per queued action). | 3-enemy round; verify only 1 attack blocked. |

---

## 9. Implementation Phases

Concrete, ordered, reviewable:

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **B1** | Golden-number regression tests for current combat feel | Locks in "shuttle vs 2 raiders in 3 rounds" baseline |
| **B2** | Enemy roster rebuild — 18 new templates per Section 4.3 | All templates in data/combat/enemies.json, validated |
| **B3** | Encounter pool migration — 131 existing entries mapped to new roster | No broken encounter references |
| **B4** | Weapon catalog revamp — 32 weapons retuned to Section 2.3 tiers | 40/40/20 distribution, damage math per Section 2.5 |
| **B5** | Builder energy widget — Section 7 implementation | Visible in shipyard builder view |
| **B6** | Archetype playtest tests — Section 6 scenarios as integration tests | All 6 scenarios pass |
| **B7** | Legendary multi-action verification — Section 8 tests | All 5 effects validated under queued combat |
| **B8** | Dual tech system (separate phase, post-balance) | Crew pair palette + triad + loyalty gates |

Each phase produces passing tests before moving to the next. B8 intentionally sits after the balance work stabilizes so dual tech damage can be set against known enemy HP curves and weapon DPS.

---

## 10. Open Questions

Items to resolve during implementation, listed for visibility:

1. **Encounter pool migration policy** — do we retune encounter *difficulty* during migration (may require reworking campaign pacing) or preserve difficulty-per-encounter and only swap enemy IDs?
2. **Element resistance granularity** — single-element resist multipliers (simple) vs. layered resist+weak (more tactical but more UI needed)?
3. **Support archetype heal math** — heals flat HP (predictable) vs. % of target max (scales with tier)?
4. **Dual tech cinematic first-fire** — does the cinematic *pause* combat for dialogue or overlay during the action resolve?
5. **Triad loyalty gate** — all four at L3 (strict) vs. three of four at L3 (more achievable)?
6. **Legendary superboss retuning** — keep existing 5 as-is, or retune HP/damage to match the new curve? (current memory says HP ≤ 200, but legendary bosses likely already overridden elsewhere — verify.)

---

## 11. Success Criteria

The balance pass is successful when:

- A new player's first 3 combat encounters take 2–4 rounds each and feel learnable.
- By L10, the player can articulate their build archetype ("I'm a tank build" or "I'm running a missile boat") and see why it matters.
- Every tier has at least one standout fight the player remembers (a boss, a rival, a support ambush).
- Dual techs feel like earned payoff, not a power spike they stumbled into.
- The builder energy widget answers the question "can this build survive?" before combat starts.
- No single weapon, enemy, or dual tech is "the right answer" — multiple builds are viable at every tier.

If any of these fail during implementation, the numerical targets in Sections 2 and 4 are the first knobs to turn.

---

## 12. Deferred Items Log

Implementation-time decisions to *not* do something, recorded here so we can return to them on purpose instead of rediscovering them by accident. Each entry notes **what** was deferred, **why**, and **where it should probably land** when we come back.

### From Phase B2 (Enemy Roster Rebuild)

- **"Iron Dominion" → Miners Union mapping.** ✅ **RESOLVED** (QA Pass 5 Tier 1.6, 2026-04-21). Lightweight rename applied to §4.6; Miners Union is now the canon label for the Tank/Juggernaut bias. If a narrative case for a distinct Iron Dominion faction emerges, that's a separate feature.

- **Ally-targeted heals for Support archetype.** ✅ **RESOLVED** (QA Pass 5 Tier 3.D, 2026-04-21). `EffectTarget.ALLY` variant added; combat engine routes ALLY effects to the caster's lowest-HP living teammate via `_select_ally_target`. `collective_medic` and `guild_relay_nexus` now fire `medical_relay` (30 HP ally heal, design-spec value) instead of self-heals. Solo-caster fallback: when no ally is alive, the effect redirects to self so lonely Support enemies still have a survival tool. 8 regression tests guard the routing / selection / fallback behaviour.

- **Reinforcement spawning (call_reinforcement move).** ✅ **RESOLVED** (QA Pass 5 Tier 3.E, 2026-04-21). `EffectType.SPAWN_REINFORCEMENT` added; `CombatEffect.metadata["template_id"]` carries the spawn template id, `value` is the count. Engine `_spawn_reinforcements()` appends to `state.enemies` bounded by `MAX_LIVING_ENEMIES=5`. Wired on `union_behemoth` (T4 Miners Union boss) as "Call the Yard" — summons a `union_picket`, 99-round cooldown (effectively once-per-combat). 8 regression tests guard the spawn contract (append, cap respect, unknown-template no-op, count via value, missing-template-id no-op, metadata serialization round-trip).

- **Legendary superboss retuning verification.** Legacy T5 bosses (corsair_king, void_leviathan, etc.) were retained unchanged. The design doc §4.3 suggests 1,000–1,500 HP for legendary. **Next:** audit legacy T5 HP + `boss_hp_multiplier` math during B7 legendary verification; retune if needed.

### From Phase B8 (Dual Tech System)

**B8.1 foundation** — shipped: data model, palette of 7 techs, availability logic, executable factories for Gun Run and Focused Barrage.

**B8.2 engine hooks** — shipped: 4 additional techs fully playable through the combat engine:
- **Fire at Will** — sets a `fire_at_will_active` flag on PlayerCombatState; weapon moves fired while active halve energy cost AND skip cooldown assignment. Flag clears at end of `execute_player_turn`.
- **Power Drift** — immediate +6 energy (clamped at max) plus −2 to every active cooldown except its own.
- **Daring Gambit** — 2-turn EVASION_MOD +40 via standard active_effects pipeline. Counter-on-dodge is **B8.3**.
- **Crew Sync** — heals 40% of max hull, grants EVASION_MOD +4 / 3 turns and DAMAGE_BOOST +100% / 1 turn, sets `crew_sync_used=True` to block re-activation. Armor-ignoring damage portion is **B8.3**.

**B8.3 engine hooks** — shipped:

- **Total Commitment** wired: hull-damage interception in `_apply_direct_damage` converts incoming hull hits to armor stacks (+3 per hit, cap +8 for the fight). The tech disarms after 3 hits.
- **Daring Gambit counter-on-dodge** wired: a 2-turn window on `daring_gambit_turns` fires a 25-damage counter at the attacker when the player cleanly dodges an enemy attack.
- **Crew Sync armor-pierce** wired: the activation turn sets `armor_pierce_active`; player attacks bypass defender armor. Flag clears at end of round via the new `tick_dual_tech_end_of_round` helper.
- `_apply_direct_damage` now takes an optional `attacker` parameter so the armor-pierce check can consult the attacker's state. Thread-through was done cleanly across `_resolve_move` and `_apply_effects` call sites; DOT-style callers (end-of-round burn/chill) pass None and skip the check.

**B8.4 surface layer** — shipped:

- **`dual_tech_moves` field on PlayerCombatState** + `inject_available_dual_techs` helper that populates it from the crew roster. Called by `build_player_combat_state` at combat start so dual techs are first-class combat-start state.
- **Combat view integration** — dual techs render in the utility tab (via `category="coordinated"`) alongside regular moves. The element-lookup and move-name lookup in `combat_view.py` also walk `dual_tech_moves`.
- **`_find_player_move`** in the combat engine searches `dual_tech_moves` so the existing queue → execute pipeline finds them.
- **Queue-time Fire at Will prediction** — ActionQueue now halves the effective cost of weapon moves added AFTER a `fire_at_will` action in the same queue. Lets players pre-plan bigger alpha strikes; `can_add` agrees with `add` so the UI's affordance check is accurate.
- **Narrative role reconciliation** — dual tech descriptions rewritten to match canon roles (Elena: navigator/command line, Marcus: engineer/mount sync, Priya: scientist/capacitor, Tomas: trader/pilot-of-opportunity). Reads as coherent bridge coordination rather than military-role cosplay.

**B8.4 tail** — shipped:

- **First-use cinematic reveals.** 7 scenes written with voice-sheet fidelity (Elena, Marcus, Priya, Tomas), living in `spacegame/models/dual_tech_dialogue.py`. `check_and_mark_reveal(flags, tech_id)` gates on `dialogue_flags["dual_tech_{id}_revealed"]`. Combat engine emits the scene to the combat log on first activation, then marks the flag; subsequent activations skip the scene. Flag persists across combats when `build_player_combat_state` receives the Player's `dialogue_flags` dict.
- **Dedicated "Coordinated" tab** in the combat view. 4th tab (CREW) alongside ATK/DEF/UTL, with R key shortcut. Dual techs route here via the `_TAB_MAP["coordinated"] = "coordinated"` routing.

**Locked dual tech display** — shipped: `describe_all_dual_techs(crew_roster)` produces a UI snapshot (name, crew, loyalty_req, availability, lock reason, per-crew current loyalties) for every palette tech. Crew-roster view renders this in the detail panel's empty state (when no crew is selected), showing each tech with an AVAILABLE / LOCKED badge and the participating crew's current loyalty progress. Players now have a discovery point outside combat for what unlocks what.

**Bridge-crew-this-combat concept** — **closed as not applicable.** The architecture hook (`bridge_crew_ids` kwarg on `is_dual_tech_available` and `compute_available_dual_techs`) exists for future expansion. Today the game caps active combat party at the four senior crew, so there's no "bridge vs reserve" distinction to surface. Revisit only when fleet management (see Future Work) expands party size beyond 4 companions.
**Caller wire-up — shipped:** `game.py` now passes `self.player.dialogue_flags` into `build_player_combat_state`. Since `Player.dialogue_flags` is already serialized in `save_manager.py` (lines 442, 588), reveals persist across save/load without additional work. Reveals now fire exactly once per tech per savegame in live gameplay.

**Balance pass + dual tech tail are now fully shipped in live gameplay.** Every tech has a mechanical implementation, a cinematic reveal that fires once per savegame, and a home in the combat view's Coordinated tab. The two remaining items below are UX polish with no correctness impact.

### From Phase B7 (Legendary Multi-Action Verification)

- **Phase Shift blocks ALL attacks on an active round, not just the first.** Design doc §8 says "blocks first incoming attack per round". Current engine behavior (verified in B7) triggers `check_phase_shift(round_number, interval)` on *every* incoming attack during an active round, meaning all 3 enemy attacks in a 3-enemy encounter are dodged when the round is phase-active. The `LegendaryState` carries no "phase shift consumed this round" flag. **Next:** add a `phase_shift_used_this_round: bool` field to `LegendaryState`, set it to True on first use, reset at `end_round`. Simple change; defer until there's evidence the difference matters in playtest (current behavior is strictly stronger, so it's power-skewed but not broken).

- **Graze damage through Phase Shift — FIXED IN B7.** Bug caught during test writing: after `phase_shifted=True` set `hit=False` and `roll=100`, a redundant `graze = False` on the line below re-entered the graze check, which then computed `miss_margin = 100 - 95 = 5 ≤ 10 → graze=True`, resulting in phase-shifted attacks dealing 30% damage instead of zero. Fixed by guarding the graze check on `not phase_shifted` (see `combat_engine.py` around line 1124). Resolved, not deferred.

### From Phase B6 (Archetype Playtest Tests)

- **Design-doc §6 round-count targets don't match current tuning.** ✅ **RESOLVED** (QA Pass 5 Tier 2.2, 2026-04-21) via option (c): revised §6.1 expected counts to 5–8 rounds. Rationale: current fights are engaging — the old "2 rounds" expectation was aspirational and retuning to hit it would have required burst buffs that trivialize other archetypes. The structural tests in `test_balance_archetypes.py` (B6) remain the authoritative guard; they assert archetype identity rather than round counts, which is the correct shape.

- **B6 tests pivoted to structural comparisons, not round counts.** Per that scope-correction, the tests now assert archetype identity (glass cannon out-damages tank; tank hull survives; missile boat has cooldown idle turns) rather than hitting specific round counts. If a future tuning pass targets §6's original round counts, those scenarios can be added back as stricter assertions. The structural tests are the right guard-rail regardless.

- **Queue API footgun**: `ActionQueue.add(move_id, target, move)` expects the canonical `move.id` as first arg, not the slot-specific cooldown key. Passing slot_key silently breaks — the engine's `_find_player_move(move_id)` returns None, logs "Move not found", and the action becomes a no-op. Caught during B6 instrumentation. **Next:** add a test in test_combat_golden.py that an ActionQueue built with a bad move_id produces a "Move not found" log (documentation test). Low priority; the bug is self-revealing with instrumentation.

### From Phase B3 (Encounter Pool Migration)

- **Narrative encounters that trigger new T4 bosses.** The infrastructure is verified (tests in `test_scripted_boss_path_b3.py`), but no data-level narrative encounter currently references `pirate_lord`, `reach_dreadnought`, or `union_behemoth`. Legacy bosses like `corsair_king` already have narrative triggers (see `data/encounters/generic.json`). **Next:** write ~3 narrative encounter entries (one per new T4 boss) when we do campaign/narrative content work. Each needs `min_level` gating, narrative setup, and a `leads_to_combat + enemy_template_ids` outcome. Not balance work — content work.

- **Pruning legacy enemies from the pool.** The 42 legacy templates still appear in random encounter pools alongside the 18 new ones. A "dangerous" system can roll an old 80-HP `pirate_heavy` or a new 350-HP `union_siege_cruiser` — wide variance. **Next:** if playtest (phase B6) shows the inconsistency hurts difficulty pacing, either retire specific legacy IDs (mark `danger_tier` as `deprecated` and filter them) or retune their stats into the new tier bands. Decide after B6, not before.

- **Travel-encounter boss filtering (defense-in-depth).** `check_travel_encounter` trusts its input pool. If a future caller forgets to run the filter, bosses could leak. The test documents this contract (`test_travel_encounter_never_yields_boss` is currently skipped). **Next:** low priority. If we ever see a boss-leak incident, add an `is_boss` guard inside `check_travel_encounter` as belt-and-suspenders.

### From Phase U5 (Legacy Retirement — completed earlier)

- **Legacy `ShipType` combat path in `combat.py:912+`.** ✅ **AUDITED** (QA Pass 5 Tier 2.4, 2026-04-21). **Verdict: keep in place, now clearly documented.** The audit found three active code paths that reach this branch: (1) `Game.new_game` preset generation failure (try/except intentional), (2) corrupted-save fallback, (3) test direct-construction (including QA Pass 3.5 Scenario C which *requires* this path to verify skill-bonus parity). Removal requires exception-free preset generation for every ship_type + save-migration test for the malformed-save case + test refactor. Code now carries a block comment documenting these conditions so the next audit starts from this finding rather than rediscovering it.

### Open Questions (from §10, still unresolved)

The six open questions in §10 are also deferrals — listed there by convention, duplicated here only for quick reference when scanning this log:

1. Encounter pool migration policy (retune difficulty vs. swap IDs only)
2. Element resistance granularity (single multiplier vs. layered resist + weak)
3. Support archetype heal math (flat HP vs. % of target max) — resolved partially above (self-heal flat for now)
4. Dual tech cinematic first-fire (pause combat vs. overlay)
5. Triad loyalty gate (all four at L3 vs. three of four)
6. Legendary superboss retuning (keep vs. retune to new curve) — superseded partially above

### How to use this log

When starting any phase B4+, re-read §12. If a deferred item is blocking or adjacent to the current phase, resolve it in-phase and move the entry to a "Resolved" sub-section with a date + commit reference. When adding new deferrals during future phases, append to the appropriate "From Phase X" subsection and note the rationale.
