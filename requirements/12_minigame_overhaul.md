# Mini-Game Depth & Polish Overhaul

> **Implementation Status** (Updated 2026-03-12): ALL CYCLES COMPLETE (A-E)
>
> - **Mining energy system**: IMPLEMENTED — clicks consume energy, regen over time, passive/drones free
> - **Mining rare ore chance**: IMPLEMENTED — `rich_veins` + `deep_scan` bonuses wired into rock distribution
> - **Mining depth scaling**: IMPLEMENTED — 4 tiers with rare/energy/yield modifiers, energy refills on regen
> - **Mining chain detonation**: IMPLEMENTED — recursive 8-directional chains, `chain_reaction` skill node added
> - **Mining session milestones**: IMPLEMENTED — 3 random milestones per session from 9-entry pool
> - **Salvage minesweeper hints**: IMPLEMENTED — empty scanned cells show adjacent item count (0-8)
> - **Salvage item quality**: IMPLEMENTED — quality 0.8-1.5 per item, affects yield + extraction time, 4 tiers
> - **Salvage derelict types**: IMPLEMENTED — 3 presets (Cargo Bay, Lab Module, Engine Room) with varying grid/density/distribution
> - **Salvage parallel extraction**: IMPLEMENTED — 2 base slots (+1 from master_extractor lv3), update() returns list
> - **Salvage corruption timer**: IMPLEMENTED — starts on first scan, CORRUPTED state, 2-charge scan cost, 50% zero yield
> - **Refining delta time**: IMPLEMENTED — replaced time.time() with dt accumulation, effective_time on ActiveJob
> - **Refining speed/yield bonuses**: IMPLEMENTED — 2 new Gathering skills (efficient_refining, yield_mastery), session-level bonuses
> - **Refining batch queuing**: IMPLEMENTED — atomic start_batch() method, +/- buttons in view
> - **Refining new recipes**: IMPLEMENTED — 3 recipes (forge_alloy, purify_crystal, advanced_electronics), 2 commodities (alloy_composite, purified_crystal)
> - **Session summaries**: IMPLEMENTED — overlay panels on mining/salvage/refining exit showing session stats + XP earned
> - **New player stats**: IMPLEMENTED — 8 new fields (max_mining_depth, total_chains_triggered, rare_ores_mined, salvage_sessions_completed, corrupted_items_extracted, refining_jobs_completed, batch_jobs_queued, recipes_crafted)
> - **New achievements**: IMPLEMENTED — 10 new minigame achievements (deep_delver, chain_master, master_prospector, rare_collector, salvage_expert, derelict_hunter, corruption_survivor, refining_mogul, alchemist, batch_crafter)
> - **Investment system**: IMPLEMENTED — InvestmentManager, InvestmentView, 10 system configs, save/load, day-advance returns, disaster/pirate risk
> - **Session ratings**: IMPLEMENTED — S/A/B/C/D rating system (rating.py), all 3 mini-game views display ratings with color coding
> - **Visual polish**: IMPLEMENTED — 5 particle configs (MINING_CHAIN, ENERGY_REGEN, SALVAGE_SCAN, SALVAGE_CORRUPT, REFINE_COMPLETE)

## 1. Overview & Philosophy

### 1.1 Purpose

The three resource mini-games (mining, salvaging, refining) are the primary non-trading gameplay activities. They currently function but lack strategic depth — mining is pure clicking with no resource management, salvaging is random scanning with no deduction, and refining is a passive queue with no skill integration. This overhaul adds meaningful decision-making, risk/reward tension, and progression hooks to each mini-game.

### 1.2 Design Principles

- **Depth through mechanics, not complexity**: Each improvement should create interesting decisions without adding cognitive overhead
- **Skill investment pays off**: Progression bonuses should feel impactful — players who invest in gathering/mining trees should see noticeably different gameplay
- **Risk vs. reward**: New mechanics (depth scaling, corruption timer, chain detonation) should reward aggressive play while punishing recklessness
- **Session variety**: No two mining/salvage sessions should feel identical
- **Wire what exists**: Several skill bonuses are already defined but unimplemented — activating these is the highest priority

### 1.3 Scope

This overhaul covers 5 implementation cycles:
- **Cycle A**: Mining depth (energy, rare chance, depth scaling, chain detonation, milestones)
- **Cycle B**: Salvage depth (minesweeper hints, parallel extraction, quality, corruption, derelict types)
- **Cycle C**: Refining depth (delta time, skill bonuses, batch queuing, new recipes)
- **Cycle D**: Skill trees + achievements (4 new nodes, wire 2 unused bonuses, 10 new achievements)
- **Cycle E**: Investment system + polish (passive income, session summaries, visual effects)

---

## 2. Mining Overhaul

### 2.1 Current State

The mining system (`spacegame/models/mining.py`, `spacegame/views/mining_view.py`) provides a 6x4 asteroid grid with 4 rock types (Common/Iron/Crystal/Rare). Players click to mine, a passive drill adds background progress, and up to 3 drones automate extraction. `MiningConfig` defines per-system settings loaded from `data/economy/mining_configs.json`.

**What works well**:
- Click-to-mine feel is responsive and satisfying
- Drone progression (3 tiers via skill tree) provides long-term motivation
- Rock type variety creates natural prioritization
- Per-system configs (Breakstone vs. Iron Depths) give systems identity

**What's missing**:
- `MiningConfig.max_energy` (default 20) and `energy_regen_seconds` (default 3.0) — fields exist but are completely unused
- `rich_veins` bonus (`rare_ore_chance`, Gathering tree, +0.25/level, max 2) — calculated but never applied to rock generation
- `deep_scan` bonus (`mining_rare_chance`, Mining tree, +0.50/level, max 2) — calculated but never applied
- No sense of progression within a single mining session
- No strategic resource management (infinite clicking)
- Grid regeneration is flat (same distribution every time)

### 2.2 Activate Energy System

Clicks consume energy, adding resource management to the mining loop. Passive drill and drones operate for free, creating meaningful tradeoffs between manual speed and automated patience.

**Mechanics**:
- Energy bar starts at `max_energy` (default 20, configurable per system)
- Each click costs 1 energy
- Energy regenerates at 1 charge per `energy_regen_seconds` (default 3.0s)
- When energy reaches 0, clicking is disabled (passive drill and drones continue)
- Energy does NOT persist between sessions — resets on entering mining view

**Skill integration**:
- New skill node `energy_reserves` in Gathering tree: +5 max energy per level, max 2 levels (see Section 6)

**View changes** (`mining_view.py`):
- Energy bar rendered below the asteroid grid (horizontal bar, same width as grid)
- Bar color: blue when >50%, yellow when 25-50%, red when <25%
- Pulsing glow effect when energy is regenerating
- "NO ENERGY" text overlay when bar is empty
- Particle effect (cyan sparks) on energy regen tick

**Model changes** (`mining.py`):
- `MiningSession.energy: int` — current energy level
- `MiningSession.energy_regen_timer: float` — tracks time since last regen
- `MiningSession.click_mine(rock)` — check energy before processing, deduct on success
- `MiningSession.update(dt)` — add energy regeneration logic

### 2.3 Implement Rare Ore Chance

Wire the two existing but unused skill bonuses into rock type distribution during grid generation.

**Mechanics**:
- `rich_veins` (Gathering tree): `rare_ore_chance` bonus, +0.25 per level (max 2 levels = +0.50)
- `deep_scan` (Mining tree): `mining_rare_chance` bonus, +0.50 per level (max 2 levels = +1.00)
- Both bonuses stack additively: `total_rare_bonus = rare_ore_chance + mining_rare_chance`
- On grid generation, CRYSTAL and RARE weights are multiplied by `(1 + total_rare_bonus)`
- Example: base weights [50% common, 30% iron, 15% crystal, 5% rare] with +0.50 total bonus becomes [50%, 30%, 22.5%, 7.5%] (then normalized)

**Model changes** (`mining.py`):
- Grid generation method accepts `rare_chance_bonus: float` parameter
- Weight adjustment applied before rock type selection

**View changes**: None — visual change is simply seeing more rare rocks in the grid.

### 2.4 Depth Scaling

Each time the player regenerates the asteroid field (completes all rocks), depth increases. Deeper levels offer better rewards but cost more energy, creating escalating risk/reward within a single session.

**Mechanics**:
- `depth` starts at 1, increments when all rocks are mined and the field regenerates
- Depth resets to 1 when leaving the mining view
- Depth modifiers:

| Depth | Rare Weight Bonus | Energy Cost | Yield Bonus |
|-------|-------------------|-------------|-------------|
| 1-3   | +0% (normal)      | 1/click     | +0%         |
| 4-6   | +10% per depth    | 1/click     | +10%        |
| 7-9   | +20% per depth    | 2/click     | +20%        |
| 10+   | +30% per depth    | 2/click     | +30%        |

- Rare weight bonus stacks with skill bonuses (additive)
- Yield bonus applies as extra quantity chance (e.g., +20% means 20% chance of +1 unit)

**Model changes** (`mining.py`):
- `MiningSession.depth: int` — current depth level
- `MiningSession.advance_depth()` — called on field regeneration, increments depth
- Depth modifiers applied in grid generation and yield calculation
- Energy cost multiplier applied in click handler

**View changes** (`mining_view.py`):
- Depth indicator in top-left corner: "DEPTH 1", "DEPTH 4", etc.
- Background darkens slightly per depth level (deeper = darker ambient)
- Rock glow intensity increases at higher depths
- Depth advance animation: screen flash + "DEPTH UP" text

### 2.5 Chain Detonation

Mining a rock has a chance to crack adjacent rocks of the same type, creating cascading breaks that reward spatial awareness and grid reading.

**Mechanics**:
- When a rock is fully mined, check all 4 cardinal + 4 diagonal neighbors (8-connected)
- For each neighbor of the **same RockType**: chance to apply 25% progress
- Base chain chance: 15%
- Chain chance applies per neighbor independently
- If a cracked rock reaches 100% progress, it breaks and triggers its own chain check (cascade)
- Maximum cascade depth: 3 (prevents infinite chains)

**Skill integration**:
- New skill node `chain_reaction` in Mining tree: +10% chain chance per level, max 3 levels (see Section 6)
- At max level: 15% + 30% = 45% chain chance per neighbor

**Model changes** (`mining.py`):
- `MiningSession._check_chain_detonation(rock, cascade_depth)` — recursive chain check
- Chain results returned as list of affected rocks for animation

**View changes** (`mining_view.py`):
- Shockwave particle effect emanating from the mined rock to cracked neighbors
- Cracked rocks show fracture lines (visual overlay) before breaking
- Screen shake on multi-rock chains (intensity scales with chain count)
- Chain counter text: "CHAIN x3!" floating above the grid

### 2.6 Session Milestones

Per-session goals that provide optional objectives and bonus rewards, adding variety and secondary motivation to each mining visit.

**Mechanics**:
- 3 milestones selected randomly from a pool when entering the mining view
- Milestone pool:

| Milestone | Threshold | Reward |
|-----------|-----------|--------|
| Mine N rocks | 10/15/20 | +5/+10/+15 XP |
| Find N rare ores | 2/3/5 | +50/+100/+200 credits |
| Reach depth N | 3/5/7 | +10/+15/+25 XP |
| Chain N total rocks | 5/10/15 | +50/+100/+200 credits |
| Mine without energy drain | 30s duration | +10 XP |

- 3 milestones drawn from different categories (no duplicates within category)
- Completing a milestone immediately awards the reward and shows a notification
- Milestones are tracked within `MiningSession`, not persisted

**View changes** (`mining_view.py`):
- Milestone tracker panel in top-right corner (3 rows, each with objective text + progress + checkmark)
- Green checkmark animation on completion
- Small floating text reward notification ("+15 XP") on milestone complete

---

## 3. Salvage Overhaul

### 3.1 Current State

The salvage system (`spacegame/models/salvage.py`, `spacegame/views/salvage_view.py`) provides a 5x5 grid representing a derelict hull. ~40% of cells contain items (3 types: Scrap Metal, Electronics, Rare Parts). Players spend scan charges to reveal cells, then extract items one at a time.

**What works well**:
- Grid-based exploration creates spatial gameplay
- Charge management adds resource pressure
- Item type variety with different extraction times
- Per-system configurations (Forgeworks vs. Crimson Reach)

**What's missing**:
- No strategic information — scanning is pure guesswork
- Sequential extraction (1 at a time) makes extraction a passive wait
- No time pressure or risk mechanic
- Every derelict looks and plays the same
- No item quality variance — all scrap metal is identical

### 3.2 Minesweeper-Style Proximity Hints

When an empty cell is scanned, display a number indicating how many adjacent cells contain items. Transforms salvage from random clicking into a deduction puzzle.

**Mechanics**:
- When a cell is revealed as EMPTY, count adjacent cells (8-connected) that contain items
- Display that count (0-8) on the empty cell
- 0 = no adjacent items (gray text), 1-2 = blue, 3-4 = green, 5+ = yellow
- This applies retroactively — if an adjacent item is extracted, hint numbers do NOT update (matches minesweeper convention)

**Model changes** (`salvage.py`):
- `SalvageSession.get_adjacent_item_count(x, y) -> int` — count items in 8 neighbors
- `SalvageCell.adjacent_count: Optional[int]` — cached hint number, set on scan

**View changes** (`salvage_view.py`):
- Empty scanned cells display their hint number centered in the cell
- Number font size and color based on count value
- Subtle cell background tint to distinguish scanned-empty from unscanned

### 3.3 Parallel Extraction

Allow multiple simultaneous extractions, reducing the passive waiting time and adding prioritization decisions.

**Mechanics**:
- Base parallel slots: 2 (up from 1)
- `master_extractor` at level 3 unlocks a 3rd parallel extraction slot
- Each extraction operates independently with its own progress bar
- Player chooses which scanned items to extract — order matters when slots are full

**Model changes** (`salvage.py`):
- `SalvageSession.max_parallel_extractions: int` — 2 base + skill bonus
- `SalvageSession.active_extractions: list[SalvageCell]` — currently extracting cells
- `SalvageSession.start_extraction(cell)` — validates slot availability
- `SalvageSession.update(dt)` — advance all active extractions

**View changes** (`salvage_view.py`):
- Multiple extraction progress bars shown below the grid
- Each bar labeled with item type name
- Extracting cells show pulsing border (one color per active extraction)

### 3.4 Item Rarity Variance

Each item instance has a quality modifier that affects yield and extraction time, adding variance and decision-making to extraction priority.

**Mechanics**:
- Quality roll on grid generation: uniform random in [0.8, 1.5]
- Quality affects yield: `final_yield = base_yield * quality` (rounded, minimum 1)
- Quality affects extraction time: `final_time = base_time * (0.5 + quality * 0.5)` (higher quality = slower extraction)
- Quality tiers for display purposes:

| Quality Range | Tier | Visual |
|--------------|------|--------|
| 0.80 - 0.99 | Poor | Dim border |
| 1.00 - 1.19 | Normal | Standard border |
| 1.20 - 1.39 | Good | Bright border |
| 1.40 - 1.50 | Excellent | Gleaming border + sparkle |

- Quality is visible after scanning (before extraction), enabling informed prioritization

**Crew integration**:
- Dr. Priya Osei's level 3 ability (`deep_analysis`) could reveal quality of HIDDEN cells adjacent to scanned cells — future enhancement, not required for this overhaul

**Model changes** (`salvage.py`):
- `SalvageCell.quality: float` — quality modifier, default 1.0
- Quality applied in yield calculation and extraction time

**View changes** (`salvage_view.py`):
- Scanned item cells show quality tier indicator (border color/thickness)
- Excellent quality cells have a subtle sparkle particle effect

### 3.5 Corruption Timer

A ticking clock that degrades unscanned cells over time, creating urgency and forcing strategic scanning order. Balances the power of minesweeper hints (which could otherwise make salvage trivially solvable).

**Mechanics**:
- Timer starts when the player performs their first scan action
- Duration: 90 seconds (configurable per system in `salvage_configs.json`)
- When timer expires, all remaining HIDDEN cells become CORRUPTED
- Corrupted cells can still be scanned and extracted, but:
  - Scanning costs 2 charges instead of 1
  - Extraction has a 50% chance of yielding nothing (quality zeroed)
- Timer is visible at all times after first scan

**Crew integration**:
- Marcus Jin's engineering abilities could add +15 seconds to the corruption timer — future enhancement

**Model changes** (`salvage.py`):
- `SalvageSession.corruption_timer: float` — seconds remaining, starts at configured duration
- `SalvageSession.corruption_started: bool` — True after first scan
- `SalvageSession.is_corrupted: bool` — True when timer reaches 0
- `SalvageCell.corrupted: bool` — per-cell corruption state

**View changes** (`salvage_view.py`):
- Corruption timer bar at top of grid area (full width, counts down)
- Bar changes color: green (>60s) → yellow (30-60s) → red (<30s)
- Remaining HIDDEN cells progressively darken as timer approaches 0
- When corruption triggers: visual "static" effect across remaining hidden cells
- Corrupted cells show a distinct visual treatment (cracks, red tint)

### 3.6 Derelict Types

Different salvage scenarios with distinct grid layouts and item distributions, adding variety to each salvage session.

**Mechanics**:
- 3 derelict types, selected randomly (weighted by system type) when entering salvage:

| Derelict Type | Grid Size | Item Density | Distribution | Special |
|--------------|-----------|-------------|--------------|---------|
| Cargo Bay | 5x5 | 50% | 60% scrap, 30% electronics, 10% rare | Standard layout |
| Lab Module | 4x4 | 45% | 20% scrap, 50% electronics, 30% rare | Smaller grid, higher value |
| Engine Room | 5x5 | 30% | 30% scrap, 20% electronics, 50% rare | Fewer items, high quality bias |

- Each derelict type has a distinct visual theme (background tint, grid frame style)
- Industrial systems (Forgeworks) favor Cargo Bay; Science systems (Axiom Labs) favor Lab Module; Frontier systems (Crimson Reach) favor Engine Room

**Data** (`data/salvage/derelict_types.json`):
```json
{
  "derelict_types": [
    {
      "id": "cargo_bay",
      "name": "Cargo Bay",
      "grid_width": 5,
      "grid_height": 5,
      "item_density": 0.50,
      "distribution": {"scrap_metal": 60, "electronics": 30, "rare_parts": 10},
      "corruption_seconds": 90,
      "theme_color": [140, 140, 160]
    }
  ]
}
```

**Model changes** (`salvage.py`):
- `DerelictType` dataclass loaded from JSON
- `SalvageSession.__init__` accepts a `DerelictType` parameter
- Grid dimensions and item distribution driven by derelict type config

---

## 4. Refining Overhaul

### 4.1 Current State

The refining system (`spacegame/models/refining.py`, `spacegame/views/refining_view.py`) processes raw materials through 6 recipes with a queue of up to 5 concurrent jobs. Jobs process in real-time using `time.time()` wall clock.

**What works well**:
- Recipe variety (6 recipes) with clear input/output chains
- Visual recipe cards with ingredient display
- Queue system allows batching
- `refining_knowledge` skill gate on advanced recipe

**What's missing**:
- Uses `time.time()` instead of game delta time — breaks on pause, inconsistent with rest of engine
- Zero skill bonuses for processing speed or output yield
- No way to queue multiples of the same recipe quickly
- Only 6 recipes — limited late-game variety
- No new commodities to refine into

### 4.2 Convert to Delta Time

Replace wall-clock timing with game delta time for consistency with the rest of the engine.

**Current implementation**:
```python
# ActiveJob uses time.time() for tracking
self.start_time: float = time.time()

@property
def elapsed(self) -> float:
    return time.time() - self.start_time
```

**New implementation**:
- `ActiveJob.elapsed_time: float` — accumulated delta time, starts at 0.0
- `RefiningSession.update(dt: float)` — advances all active jobs by `dt`
- `ActiveJob.progress` computed as `elapsed_time / recipe.processing_time`
- Remove `time.time()` import and all wall-clock references

**Benefits**:
- Pausing the game pauses refining (correct behavior)
- Speed bonuses can be applied by scaling `dt` or `processing_time`
- Testable without mocking `time.time()`
- Consistent with mining and salvage update patterns

**Files**: `spacegame/models/refining.py`, `spacegame/views/refining_view.py`, `spacegame/engine/game.py` (pass dt to refining update)

### 4.3 Speed & Yield Skill Bonuses

Add two new skill nodes in the Gathering tree that make refining faster and more productive.

**Efficient Refining** (new skill):
- Bonus type: `refining_speed`
- Effect: -15% processing time per level
- Max level: 2 (total: -30% processing time)
- Prerequisite: `refining_knowledge`
- Applied as: `effective_time = recipe.processing_time * (1 - refining_speed_bonus)`

**Yield Mastery** (new skill):
- Bonus type: `refining_yield`
- Effect: +10% output chance per level (chance of +1 per output item)
- Max level: 3 (total: +30% chance of bonus output)
- Prerequisite: `efficient_refining`
- Applied as: for each output unit, roll `random() < yield_bonus` — if true, add +1 to that output

**Model changes** (`refining.py`):
- `RefiningSession` accepts `speed_bonus: float` and `yield_bonus: float` parameters
- Speed bonus applied when calculating job progress
- Yield bonus applied when completing a job and generating outputs

### 4.4 Batch Queuing

Queue multiple copies of the same recipe in a single action, reducing repetitive clicking.

**Mechanics**:
- Recipe cards show a quantity selector (1-5) when the player has enough inputs for 2+
- "Queue" button queues N copies of the recipe, consuming N * inputs
- Each copy is a separate `ActiveJob` in the queue (respects `MAX_QUEUE_SIZE = 5`)
- If queue has 3 slots remaining, batch size is capped at 3
- Inputs consumed immediately on queue (consistent with current behavior)

**View changes** (`refining_view.py`):
- Quantity selector: left/right arrows or +/- buttons next to recipe card
- "Queue x3" button text showing batch count
- Queued jobs show a group indicator (e.g., "2/3" for second of three batched)

### 4.5 New Recipes

Expand the recipe catalog with 3 new recipes that create new late-game commodities and a fuel conversion.

| Recipe | Inputs | Outputs | Time | Requires | Location |
|--------|--------|---------|------|----------|----------|
| Alloy Composite | 5 common_metals + 2 rare_metals | 2 alloy_composite | 20s | `yield_mastery` lv2 | Forgeworks, Iron Depths |
| Synthetic Fuel | 3 raw_ore + 2 crystal_ore | 15 fuel | 10s | None | All refining systems |
| Purified Crystal | 3 crystal_ore | 1 purified_crystal | 25s | `refining_knowledge` | Axiom Labs, Nova Research |

**New commodities**:
- `alloy_composite`: base_price 800, luxury tier, consumed by advanced manufacturing
- `purified_crystal`: base_price 1200, luxury tier, rare high-value trade good

**Data changes**:
- `data/economy/recipes.json`: 3 new recipe entries
- `data/economy/commodities.json`: 2 new commodity entries with supply/demand tags
- `data/galaxy/systems.json`: add production/consumption tags for new commodities at appropriate systems

**Resource flow update**:
```
Raw Ore ────────→ Common Metals ────→ Electronics
Iron Ore ───────/                  |
Crystal Ore ──→ Rare Metals ──────/+──→ Medical Supplies
            \──→ Purified Crystal  |
Scrap Metal ──→ Common Metals     \+──→ Alloy Composite
Raw Ore + Crystal Ore → Fuel (Synthetic)
```

---

## 5. Cross-System Improvements

### 5.1 Investment System

Per-system investments that generate passive income over game days, rewarding return visits and long-term economic planning.

**Mechanics**:
- Each system supports one investment type aligned with its economy:

| System Category | Investment Type | Returns |
|----------------|----------------|---------|
| Mining (Breakstone, Iron Depths) | Automated Mining Rig | Ores per game day |
| Industrial (Forgeworks) | Refining Contract | Metals per game day |
| Science (Axiom Labs, Nova Research) | Research Grant | Credits per game day |
| Trade Hub (Nexus Prime, Stellaris Port) | Trade Office | Credits per game day |
| Frontier (Crimson Reach, Haven's Rest) | Salvage Operation | Parts per game day |

- 3 tiers per system:

| Tier | Cost | Daily Return | Upkeep |
|------|------|-------------|--------|
| Basic | 1,000 CR | ~10 CR equivalent | 0 |
| Advanced | 5,000 CR | ~50 CR equivalent | 0 |
| Premium | 15,000 CR | ~200 CR equivalent | 0 |

- Returns accumulate while the player is away (tracked per game day)
- Collect returns by visiting the system (auto-collected on arrival at trading view)
- Returns delivered as items (ores, metals, parts) or credits, depending on investment type
- Investments persist across saves

**Risk**:
- Market events (DISASTER) at a system temporarily halt investment returns (duration of event)
- Pirate encounters at dangerous systems have a 10% chance per game day of reducing returns by 50% for that day

**Model** (`spacegame/models/investment.py`):
```python
@dataclass
class Investment:
    system_id: str
    tier: int  # 1, 2, 3
    returns_type: str  # "credits", "commodity"
    returns_commodity: Optional[str]  # commodity_id if type is commodity
    daily_return_amount: int
    accumulated_returns: int  # uncollected returns
    last_collection_day: int  # game day of last collection
```

**Player integration**:
- `Player.investments: dict[str, Investment]` — keyed by system_id
- Serialized in save data (backward compatible — empty dict default)

**View integration**:
- Investment panel in trading view (or accessible via a button)
- Shows current tier, daily returns, accumulated uncollected returns
- "Invest" / "Upgrade" button with cost display
- "Collect" button when returns are available

### 5.2 Session Statistics & Summary

End-of-session summary when leaving a mini-game, providing feedback on performance and driving achievement tracking.

**Displayed stats by mini-game**:

**Mining**:
- Rocks mined (by type)
- Total ore collected
- Max depth reached
- Chains triggered
- Time spent
- Efficiency rating (ore per minute)

**Salvage**:
- Cells scanned / total
- Items extracted
- Quality average
- Scans remaining (unused)
- Corruption status (cleared before / after / during)
- Efficiency rating (value per scan charge)

**Refining**:
- Jobs completed
- Total inputs consumed
- Total outputs produced
- Yield bonus procs
- Time spent
- Efficiency rating (output value per minute)

**Rating system**:
- S/A/B/C/D rank based on efficiency thresholds per mini-game
- Rank thresholds tuned per system (harder systems have more lenient thresholds)
- Personal best rank stored per system per mini-game

**Model changes**: Each session class (`MiningSession`, `SalvageSession`, `RefiningSession`) tracks stats internally. New `SessionStats` dataclass returned from `get_session_stats()` method.

**View changes**: Summary overlay rendered before transitioning back to trading view. Shows stats, rank, and personal best comparison.

### 5.3 Visual Polish

Consistent visual upgrades across all three mini-games to improve game feel.

**Mining visuals**:
- Rock crack animations: progressive crack overlay as mining progress advances
- Ore collection particles: colored sparks (matching rock type color) fly toward cargo counter
- Depth atmosphere: background darkens and adds subtle fog at higher depths
- Drone beam effects: visible laser-style beam from drone to target rock

**Salvage visuals**:
- Scan sweep animation: circular "ping" effect emanating from scanned cell
- Extraction beam: energy beam connecting extraction progress to cell
- Corruption decay: cells progressively show static/noise as corruption approaches
- Derelict theme: grid frame and background tint match the derelict type

**Refining visuals**:
- Active job animation: bubbling/heating effect on the job progress bar
- Completion flash: bright pulse when a job finishes
- Recipe card hover: highlight with ingredient availability indicators
- Queue flow: subtle conveyor-belt animation between queued jobs

**Particle configs** (add to `ParticlePool`):
- `MINING_CHAIN`: orange shockwave burst for chain detonation
- `ENERGY_REGEN`: cyan sparkles for energy regeneration
- `SALVAGE_SCAN`: blue expanding ring for scan action
- `SALVAGE_CORRUPT`: red static particles for corruption event
- `REFINE_COMPLETE`: green flash burst for job completion

---

## 6. Skill Tree Extensions

### 6.1 New Skill Nodes

4 new skill nodes added to existing trees. No new tree required.

**Gathering Tree** (currently 5 skills → 8 skills):

| Skill | Name | Description | Max Lv | Bonus Type | Per Level | Prereq |
|-------|------|-------------|--------|------------|-----------|--------|
| `energy_reserves` | Energy Reserves | +5 max mining energy per level | 2 | `max_energy_bonus` | 5.0 | `efficient_drills` |
| `efficient_refining` | Efficient Refining | -15% refining time per level | 2 | `refining_speed` | 0.15 | `refining_knowledge` |
| `yield_mastery` | Yield Mastery | +10% bonus output chance per level | 3 | `refining_yield` | 0.10 | `efficient_refining` |

**Mining Tree** (currently 8 skills → 9 skills):

| Skill | Name | Description | Max Lv | Bonus Type | Per Level | Prereq |
|-------|------|-------------|--------|------------|-----------|--------|
| `chain_reaction` | Chain Reaction | +10% chain detonation chance per level | 3 | `chain_chance` | 0.10 | `ore_targeting` |

### 6.2 Wire Existing Unused Skills

Two existing skills have bonuses that are calculated but never consumed by gameplay code:

**`rich_veins`** (Gathering tree):
- Bonus type: `rare_ore_chance`, +0.25/level, max 2 levels
- Currently: bonus is computed via `get_bonus("rare_ore_chance")` but never passed to mining grid generation
- Fix: pass bonus into grid generation to boost CRYSTAL and RARE rock weights

**`deep_scan`** (Mining tree):
- Bonus type: `mining_rare_chance`, +0.50/level, max 2 levels
- Currently: bonus is computed via `get_bonus("mining_rare_chance")` but never consumed
- Fix: stack with `rich_veins` for rare ore chance, or wire into chain detonation range

### 6.3 Updated Tree Layouts

**Gathering tree** (8 skills):
```
efficient_drills (root)
├── keen_scanner → master_extractor → refining_knowledge → efficient_refining → yield_mastery
├── rich_veins
└── energy_reserves
```

**Mining tree** (9 skills):
```
click_power (root)
├── passive_drill → deep_scan
└── drone_bay_1 → drone_bay_2 → drone_bay_3
    └── drone_efficiency → ore_targeting → chain_reaction
```

**Skill tree view** (`skill_tree_view.py`): Node positions may need adjustment to accommodate new nodes without overlapping. The Gathering tree grows 2 nodes deeper (efficient_refining → yield_mastery chain).

---

## 7. New Achievements

10 new achievements across mini-game categories, extending the existing 21 to 31 total.

| ID | Name | Description | Stat Key | Threshold | Category | Reward |
|----|------|-------------|----------|-----------|----------|--------|
| `deep_delver` | Deep Delver | Reach mining depth 7 | `max_mining_depth` | 7 | mining | 50 XP |
| `chain_master` | Chain Master | Trigger a 4+ rock chain detonation | `max_chain_length` | 4 | mining | 75 XP |
| `master_prospector` | Master Prospector | Mine 500 total ores | `ore_mined` | 500 | mining | 500 credits |
| `puzzle_solver` | Puzzle Solver | Clear a salvage grid using 15 or fewer scans | `efficient_salvage` | 1 | salvage | 75 XP |
| `salvage_expert` | Salvage Expert | Extract 200 total salvage items | `items_salvaged` | 200 | salvage | 500 credits |
| `corruption_runner` | Corruption Runner | Clear a salvage grid before corruption triggers | `corruption_clears` | 1 | salvage | 100 XP |
| `refining_mogul` | Refining Mogul | Complete 100 refining jobs | `items_refined` | 100 | refining | 500 credits |
| `alchemist` | Alchemist | Craft every recipe at least once | `unique_recipes` | 9 | refining | 1 skill point |
| `investor` | Investor | Own investments in 5 systems | `investments_owned` | 5 | economic | 100 XP |
| `efficiency_expert` | Efficiency Expert | Achieve S-rank in any mini-game session | `s_ranks_earned` | 1 | progression | 100 XP |

**New player stats to track**:
- `max_mining_depth`: highest depth reached in a single mining session
- `max_chain_length`: longest chain detonation achieved
- `efficient_salvage`: number of grids cleared with ≤15 scans (boolean-counted)
- `corruption_clears`: number of grids cleared before corruption
- `unique_recipes`: count of distinct recipe IDs crafted
- `investments_owned`: count of active investments
- `s_ranks_earned`: count of S-rank session summaries achieved

Some stats already exist (`ore_mined`, `items_salvaged`, `items_refined`) and are used by existing achievements — the new achievements simply use higher thresholds or new stat keys.

---

## 8. Data & Configuration

### 8.1 New Data Files

| File | Content |
|------|---------|
| `data/salvage/derelict_types.json` | 3 derelict type definitions with grid size, density, distribution, corruption time |

### 8.2 Modified Data Files

| File | Changes |
|------|---------|
| `data/economy/recipes.json` | +3 new recipes (alloy_composite, synthetic_fuel, purified_crystal) |
| `data/economy/commodities.json` | +2 new commodities (alloy_composite, purified_crystal) |
| `data/economy/mining_configs.json` | Verify `max_energy` and `energy_regen_seconds` values per system |
| `data/economy/salvage_configs.json` | Add `corruption_seconds` per system, derelict type weights |
| `data/galaxy/systems.json` | Add production/consumption tags for new commodities |
| `data/progression/skill_trees.json` | +4 new skill nodes (energy_reserves, efficient_refining, yield_mastery, chain_reaction) |
| `data/progression/achievements.json` | +10 new achievements |

### 8.3 Modified Model Files

| File | Changes |
|------|---------|
| `spacegame/models/mining.py` | Energy system, depth scaling, chain detonation, session milestones, session stats |
| `spacegame/models/salvage.py` | Proximity hints, parallel extraction, quality, corruption timer, derelict types, session stats |
| `spacegame/models/refining.py` | Delta time conversion (remove `time.time()`), speed/yield bonuses, batch queuing, session stats |
| `spacegame/models/investment.py` | **New file** — Investment dataclass, tier system, return calculation |

### 8.4 Modified View Files

| File | Changes |
|------|---------|
| `spacegame/views/mining_view.py` | Energy bar, depth indicator, chain visuals, milestones, session summary |
| `spacegame/views/salvage_view.py` | Hint numbers, parallel extraction bars, quality indicators, corruption timer, derelict themes, session summary |
| `spacegame/views/refining_view.py` | Batch queuing UI, speed bonus display, new recipe cards, session summary |
| `spacegame/views/trading_view.py` | Investment panel (or button to investment overlay) |
| `spacegame/views/skill_tree_view.py` | Node layout adjustments for new Gathering/Mining nodes |

### 8.5 Modified Engine Files

| File | Changes |
|------|---------|
| `spacegame/engine/game.py` | Pass dt to refining update, investment return accumulation on day advance, investment collection on system arrival |
| `spacegame/models/player.py` | `investments` dict field, new stat tracking fields |
| `spacegame/save_manager.py` | Serialize/deserialize investments, new stats (backward compatible) |
| `spacegame/data_loader.py` | Load derelict types, new recipes, new commodities, new skill nodes |

---

## 9. Implementation Approach

### 9.1 Implementation Cycles

Each cycle is independently testable and deployable. TDD workflow: write failing tests first, then implement.

**Cycle A: Mining Depth** (~40 tests)
1. Energy system: model tests → model implementation → view integration
2. Rare ore chance: wire `rich_veins` + `deep_scan` bonuses into grid generation
3. Depth scaling: model tests → depth increment → modifier application
4. Chain detonation: model tests → recursive chain logic → view animation
5. Session milestones: milestone pool → selection → tracking → reward application

**Cycle B: Salvage Depth** (~35 tests)
1. Minesweeper hints: model adjacency counting → view number rendering
2. Parallel extraction: model slot management → view multi-progress bars
3. Item quality: model quality generation → yield/time modification → view indicators
4. Corruption timer: model timer → state transition → view countdown bar
5. Derelict types: data loading → model parameterization → view theming

**Cycle C: Refining Depth** (~25 tests)
1. Delta time conversion: replace `time.time()` → model update(dt) → view passes dt
2. Speed/yield bonuses: model bonus application → verify with skill data
3. Batch queuing: model queue-multiple → view quantity selector
4. New recipes + commodities: data files → data loading → recipe availability

**Cycle D: Skill Trees + Achievements** (~20 tests)
1. Add 4 new skill nodes to JSON → data loading verification
2. Wire `rich_veins` and `deep_scan` bonuses into mining model
3. Skill tree view layout adjustments
4. Add 10 new achievements → data loading → stat tracking → unlock conditions

**Cycle E: Investment System + Polish** (~20 tests)
1. Investment model: dataclass, tier system, return calculation
2. Player integration: investments field, save/load
3. Game engine: day-advance returns, collection on arrival
4. Trading view: investment panel
5. Session summary overlay for all 3 mini-games
6. Visual polish: particle configs, animations

### 9.2 Test Targets

| Cycle | New Tests | Running Total (from 1088) |
|-------|-----------|--------------------------|
| A: Mining | ~40 | ~1128 |
| B: Salvage | ~35 | ~1163 |
| C: Refining | ~25 | ~1188 |
| D: Skills + Achievements | ~20 | ~1208 |
| E: Investment + Polish | ~20 | ~1228 |

### 9.3 Verification

After each cycle:
- `pytest tests/ -v --tb=short` — all tests pass
- Manual playtest of the affected mini-game
- Verify save/load backward compatibility (load old saves, check no crashes)
- Check skill bonuses are consumed correctly (not just calculated)

After all cycles:
- Full playthrough: mine at Breakstone (depth 5+, chain detonations), salvage at Crimson Reach (minesweeper deduction, corruption pressure), refine at Forgeworks (batch queue, speed bonus), invest at 3+ systems, collect returns
- Verify all 10 new achievements are earnable
- Verify session summaries display correctly for each mini-game

---

**Document Status**: v1.0
**Last Updated**: 2026-03-09
**Dependencies**: Phase 3 (combat, encounters, social) must be complete (it is). Existing Gathering tree (5 skills) and Mining tree (8 skills) are extended, not replaced.
**Cross-references**: See `requirements/05_player_progression.md` (skill trees), `requirements/08_content_requirements.md` (commodities, achievements), `requirements/11_implementation_roadmap.md` (Cycle 4.2)
