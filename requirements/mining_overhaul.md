# Mining Mini-Game Overhaul

## Vision
Transform mining from a simple click-and-dump loop into a strategic resource engine
that feeds the broader game economy. The player should make meaningful decisions
about what to mine, how deep to push, and what to keep.

## Status Key
- [ ] Not started
- [~] In progress
- [x] Complete

---

## Phase 1: Player Agency (Selective Transfer)

### 1A: Selective Transfer Screen (COMPLETE)
- [x] When ending a mining session, show a transfer overlay instead of auto-dumping
- [x] Display silo contents with commodity icons, names, quantities
- [x] Show cargo space available (current / max)
- [x] Player adjusts quantities per commodity (+/- buttons)
- [x] "Transfer All" button (fills cargo greedily, most valuable first)
- [x] "Take Nothing" button (leave everything in silo)
- [x] "Confirm" button (moves chosen amounts)
- [x] Remaining ore stays in silo for next visit
- [x] Show estimated sale value per commodity for decision-making
- [x] Session summary appears after transfer (XP, strata earned, ore kept)
- [x] ENTER confirms, ESC leaves everything in silo
- [x] Tests: transfer flow, take nothing, partial selection

### 1B: Regen Gate (COMPLETE)
- [x] Regenerate Field requires >= 50% field cleared
- [x] Shows current clear percentage in rejection message
- [x] Tests updated for new requirement

### 1C: Transfer During Session (COMPLETE)
- [x] "Transfer to Cargo" button available during mining
- [x] Moves silo contents to cargo without ending session
- [x] Feedback messages for success/failure/empty

---

## Phase 2: Upgrade Redesign (Gameplay-Changing Deep Core)

### 2A: Ore Scanner (COMPLETE)
- [x] 3 levels, new upgrade in mining_upgrades.json
- [x] L1: Rock border color shows commodity type (colored glow)
- [x] L2: Hovering a rock shows exact commodity name
- [x] L3: Hovering shows estimated yield range
- [x] Immediately applied when purchased during session

### 2B: Auto-Drill (COMPLETE)
- [x] 3 levels, new upgrade in mining_upgrades.json
- [x] Passively mines the weakest undepleted rock on a timer
- [x] L1: every 8 seconds, L2: every 5s, L3: every 3s
- [x] Does not consume energy
- [x] Triggers chain/volatile/hazard mechanics like normal breaks
- [x] Immediately applied when purchased during session

### 2C: Chain Mastery (REWORK of Seismic Pulse)
- [ ] 3 levels, enhances volatile rock chain reactions
- [ ] L1: 60% splash damage (up from 50%)
- [ ] L2: 75% splash damage
- [ ] L3: Volatile breaks can trigger non-volatile adjacent rocks (25% chance)

### 2D: Keep Existing Basics
- [ ] Silo Expansion (5 levels, +50 capacity) — keep as-is
- [ ] Core Resonance (5 levels, +8% click) — keep but rename to "Drill Power"
- [ ] Energy Conduit (5 levels, +3 energy) — keep as-is

### 2E: Late-Game Unlocks
- [ ] Deep Vein Sense (1 level): Monoliths every 3 depths instead of 5
- [ ] Drone Specialization (3 levels): Drones target specific ore types
- [ ] Resonance Well (1 level, capstone): 10% ore duplication chance

---

## Phase 3: Depth as Risk/Reward

### 3A: Depth-Gated Ore Types (COMPLETE)
- [x] Common ore: all depths
- [x] Iron ore: depth 3+
- [x] Crystal ore: depth 6+
- [x] Rare ore: depth 9+
- [x] Dense: depth 5+ (existing)
- [x] Volatile: depth 12+ (existing)
- [x] "Next unlock" hint shown in stats panel (e.g., "Depth 6: Crystal")

### 3B: Depth Persistence (COMPLETE)
- [x] Save max depth per system in player.mining_depth_per_system
- [x] Resume from saved depth on next visit (or base + scanner, whichever is higher)
- [x] Persists through save/load
- [x] Each system tracks independently

### 3C: Regen Button Clear % (COMPLETE)
- [x] Button text updates dynamically: "Regen (67%)"
- [x] Updates every frame during gameplay
- [x] Player always knows how close they are to 50% threshold

### 3D: Depth Difficulty Scaling (existing, already works)
- [x] Rocks get harder at deeper depths (dense at 5+, volatile at 12+)
- [x] Hazards spawn more frequently (unstable at 10+, vents at 15+)
- [x] Energy cost for empowered clicks increases (2x at depth 7+)
- [x] Strata rewards scale with depth (depth × 1.5 base)

---

## Phase 4: Game System Integration

### 4A: Refining Connection
- [ ] Refining view can read silo contents as ingredient source
- [ ] Show recipe ingredient availability including silo quantities
- [ ] "Mine for Recipe" hints: when viewing a recipe, show which system to mine at

### 4B: Station Hub Silo Indicator (COMPLETE)
- [x] Show silo fill status on the mining card at station hub
- [x] Format: "Silo: N/capacity" in top-right of mining card
- [x] Color: green (<70%), yellow (70-90%), red (>90%)
- [x] Only shown when silo has ore (clean when empty)

### 4C: Per-System Mining Identity (COMPLETE)
- [x] Mining card shows dominant ore type (e.g., "Iron-rich")
- [x] Derived from mining config's rock_distribution (highest non-common weight)
- [x] Displayed in mining accent color on bottom-right of card

---

## Design Principles

1. **Every session should have a decision.** What to mine, how deep to push, what to keep.
2. **Upgrades change how you play, not just how fast.** Ore Scanner gives information.
   Auto-Drill gives idle progression. Chain Mastery gives spectacle.
3. **Mining feeds the economy.** Ore is needed for refining recipes, not just selling.
   The player should mine with purpose.
4. **Depth creates tension.** Deeper = better rewards but harder work. The player
   should feel the pull of "one more depth."
5. **The silo is your bank.** Persistent, selective, strategic. Not a dumb buffer.

---

## Implementation Order
1. Phase 1A (Selective Transfer Screen) — immediate, highest player impact
2. Phase 2A-2B (Ore Scanner + Auto-Drill) — gameplay-changing upgrades
3. Phase 3A (Depth-Gated Ore) — gives purpose to depth progression
4. Phase 4A-4B (Refining hook + Silo indicator) — connects mining to the economy
5. Remaining phases as polish
