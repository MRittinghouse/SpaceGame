# Combat Balance & Integration Roadmap

> **Status**: PLANNING
> **Created**: 2026-03-26
> **Context**: Post-shipyard-revamp audit revealed combat is feature-complete but
> balance-incomplete. The new slot+part system creates the right structure; this
> roadmap tunes the numbers and fills gameplay gaps.

---

## Design Philosophy

**Early game**: Scrappy survival. Low-tier weapons, no shields, every encounter is risky.
Player learns to flee, negotiate, and pick fights carefully.

**Mid game**: Specialization. Player commits to a combat identity (Juggernaut/Sentinel/Ghost)
and an elemental preference. Trade-offs become meaningful. "My ion build melts shields
but struggles against hull-tankers."

**Late game**: Mastery. Legendary parts, optimized builds, multi-action turns demolishing
enemies. The reward for 20+ hours of play. Boss encounters test everything the player
has learned.

**The core loop**: Risk assessment → Engagement choice → Tactical execution → Reward

---

## Phase CB1: Weapon Balance Tuning (CRITICAL)

> **Impact**: HIGH — players feel punished for choosing interesting weapons
> **Effort**: LOW — data-only changes in parts.json

### Problem
Elemental weapons do 20-30% less upfront damage than kinetic at the same tier/cost.
Their secondary effects (burn DoT, chill CC, ion shield bypass, voltaic suppression)
don't compensate enough. A player who buys a Plasma Caster (12 dmg + burn) is
strictly worse than one who buys a Laser Cannon (18 dmg) in almost every fight.

### Fix
Increase elemental base damage by ~15-25% so total effective damage (base + secondary)
slightly EXCEEDS kinetic. The elemental premium justifies the complexity:

| Weapon | Current Dmg | New Dmg | Effective DPS | Rationale |
|--------|------------|---------|---------------|-----------|
| Plasma Caster | 12 | 15 | 15 + 5.9 burn/turn | Burn rewards sustained fights |
| Ion Disruptor (S) | 8 | 10 | 15 vs shields, 7.5 vs hull | Shield-killer niche |
| Frost Projector | 8 | 11 | 9.4 + freeze chance | CC value is high |
| Voltaic Pulse | 8 | 11 | 9.4 + suppression | Debuff reduces threat |

Scale proportionally for medium and large weapons.

### Cooldown Rebalance
Add cooldowns to the highest-damage weapons to create power-vs-flexibility trade-offs:

| Weapon | Damage | Current CD | New CD | Why |
|--------|--------|-----------|--------|-----|
| Rail Gun | 40 | 0 | 1 | Devastating but needs reload |
| Plasma Torpedo | 45 | 0 | 2 | Highest non-legendary, artillery pace |
| Nova Core | 60 | 0 | 2 | Was 0-cost, now premium + cooldown |
| Mass Driver Mk3 | 38 | 0 | 1 | Heavy kinetic needs reload |
| Nova Burst Cannon | 40 | 0 | 1 | Same tier as Rail Gun |

Weapons under 25 damage remain cooldown-free (quick skirmish weapons).

---

## Phase CB2: Enemy Armor & Scaling (CRITICAL)

> **Impact**: HIGH — creates difficulty ramp and makes defense meaningful
> **Effort**: LOW — data changes in enemies.json

### Problem
All 42 enemy templates have `combat_armor: 0`. The armor system exists in the engine
(flat damage reduction per hit) but is never used. Dangerous-tier enemies feel the
same as moderate-tier but with more HP — no qualitative difficulty change.

### Fix
Add armor to moderate and dangerous enemies:

| Danger Level | Armor Range | Effect |
|-------------|-------------|--------|
| Safe | 0 | Starter enemies, no armor |
| Moderate | 1-2 | Small reduction, teaches player about armor |
| Dangerous | 3-5 | Significant reduction, forces multi-hit or heavy weapons |
| Legendary (bosses) | 5-8 | Major reduction, requires optimized builds |

### Why This Matters
- Creates a natural difficulty ramp beyond just HP scaling
- Makes weapon choice meaningful (high per-hit vs multi-hit)
- Rewards the player's ship build quality
- Ion weapons bypass shields but not armor — creates a real choice
- Cryo freeze skips enemy turn regardless of armor — CC value rises

---

## Phase CB3: Defense Identity Rebalance (HIGH)

> **Impact**: HIGH — Ghost players feel punished; all three identities should be viable
> **Effort**: LOW — constant changes in combat code

### Current State
- **Juggernaut**: -5% damage (hull>75%) + Last Stand (+15% dmg, +2 armor at <25%) — STRONG
- **Sentinel**: Overcharge (shields to 150%) + Shield Break (+25% incoming) — HIGH RISK/REWARD
- **Ghost**: +15% incoming damage + Counterstrike (+10%/stack on miss, max 3) — WEAK

### Fixes
1. **Ghost**: Reduce vulnerability from +15% to +10%. Increase counterstrike from +10%
   to +12% per stack. Add: "After 3 stacks, next attack is guaranteed crit (2x damage)."
   This makes Ghost the "if they can't hit me, I demolish them" identity.

2. **Sentinel**: Shield break penalty from +25% to +20%. Shield overcharge decay from
   10%/turn to 8%/turn. Slight quality of life, keeps the risk/reward feel.

3. **Juggernaut**: No changes — well balanced as the "steady tank" option.

---

## Phase CB4: Defeat Consequences (CRITICAL)

> **Impact**: HIGH — without risk, there's no tension
> **Effort**: MEDIUM — requires UI for the defeat screen

### Problem
Losing combat has ZERO mechanical consequence. The player respawns at their last
location with everything intact. There's no reason to flee, negotiate, or build
carefully — just throw yourself at encounters repeatedly.

### Fix: Graduated Consequences
- **Credit loss**: Lose 10% of current credits on defeat (represents repairs/salvage)
- **Cargo loss**: Lose 25% of cargo (scattered in the wreckage)
- **Fuel cost**: Return to nearest safe system with minimum fuel (5 units)
- **Reputation hit**: -5 reputation with the system's faction (you needed rescuing)
- **No permadeath**: Player keeps their ship, parts, and progression

### Why This Matters
- Creates genuine risk assessment before each encounter
- Flee/negotiate become real tactical options, not "skip" buttons
- Player builds defensively because dying COSTS something
- Cargo trading becomes risky in dangerous systems (the core trader fantasy)
- 10% credit loss + 25% cargo loss is painful but not save-scumming-level punishing

---

## Phase CB5: Momentum Tuning (MEDIUM)

> **Impact**: MEDIUM — pacing improvement
> **Effort**: LOW — constant changes

### Fixes
- Increase MOMENTUM_ON_HIT: 5% -> 7% (reward aggression)
- Decrease MOMENTUM_ON_HULL_DAMAGE: 8% -> 5% (reduce turtle incentive)
- Add MOMENTUM_ON_CRIT: +3% (reward lucky/skilled play)
- Add momentum decay: -2% per turn if no actions taken (penalize stalling)

---

## Phase CB6: Enemy AI Improvements (MEDIUM)

> **Impact**: MEDIUM — combat feels less predictable
> **Effort**: MEDIUM — behavior logic changes

### Adaptive Behaviors
- **Defensive enemies below 30% HP**: Always prefer heal/shield if available
- **Aggressive enemies**: Focus lowest-HP player module (target disabled modules)
- **Evasive enemies**: Use evasion move when >60% HP, switch to aggression below 40%
- **Pack tactics**: When 2+ enemies, one focuses damage, other uses debuffs

### Threat Assessment
- Enemies prioritize targets based on: weapon damage output > low HP > exposed modules
- Boss AI: phase-based behavior shifts (already exists, needs tuning)

---

## Phase CB7: Combat Tutorials (MEDIUM)

> **Impact**: MEDIUM — player understanding drives engagement
> **Effort**: LOW — text content, triggered by game state

### New Tutorial Steps
1. **"Your First Fight"** — Hit/miss basics, health bars, energy system
2. **"Action Queue"** — Multi-action turns, energy budget, weapon selection
3. **"Elements of War"** — 5 elemental types, their strengths and status effects
4. **"Defense Styles"** — Three identities explained with visual examples
5. **"Know When to Run"** — Flee/negotiate/bribe options and when to use them
6. **"Slot Combat"** — How module-targeted damage works, why placement matters
7. **"Momentum & Ultimates"** — Building momentum, threshold abilities, ultimates

Triggered on first relevant encounter (first combat, first elemental weapon used,
first identity chosen, first flee attempt, etc.)

---

## Implementation Order

| Phase | What | Priority | Effort |
|-------|------|----------|--------|
| **CB1** | Weapon balance (elemental buff + cooldowns) | CRITICAL | Low |
| **CB2** | Enemy armor scaling | CRITICAL | Low |
| **CB4** | Defeat consequences | CRITICAL | Medium |
| **CB3** | Defense identity rebalance | HIGH | Low |
| **CB5** | Momentum tuning | MEDIUM | Low |
| **CB7** | Combat tutorials | MEDIUM | Low |
| **CB6** | Enemy AI improvements | MEDIUM | Medium |

Recommended: CB1 + CB2 first (data-only, immediate impact), then CB4 (biggest
gameplay change), then CB3/CB5/CB7 (tuning), then CB6 (code changes).
