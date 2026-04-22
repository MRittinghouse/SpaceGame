# Systems Unification — Modules, Upgrades & Combat

> **Status**: DESIGN PHASE
>
> The current game has three disconnected systems that all claim to handle ship equipment: drydock modules, shipyard upgrades, and frame slot pools. This creates confusion — the player places 4 weapon modules in the drydock but the frame says 2 weapon slots, and the actual weapons that fire in combat come from the upgrades tab. This document proposes a unification that makes the relationship clear, intuitive, and satisfying.

---

## The Problem

A player's journey today:

1. **Buys a Large frame** — told it has "Weapon: 4, Defense: 3, Utility: 4"
2. **Enters the Drydock** — places 4 Weapon Mount modules, 3 Shield Generators, etc.
3. **Exits to Shipyard** — goes to "Upgrades" tab, buys a Laser Cannon, hits "Buy & Install"
4. **Enters combat** — the Laser Cannon fires

**What's confusing:**
- The 4 weapon *modules* from step 2 don't directly relate to the weapon *upgrades* from step 3
- The frame's "Weapon: 4" from step 1 uses the old SLOT_POOLS system, not the module count
- Weapon modules provide stat bonuses (accuracy, etc.) but don't fire — upgrades do
- There's no visual connection between "I placed a weapon mount here" and "this is where my Laser Cannon lives"
- The player can install upgrades without even entering the drydock — the two systems are independent

**The core confusion**: Modules feel decorative. Upgrades feel disconnected from the ship you built. The drydock and the upgrades tab feel like two separate games.

---

## The Vision

**One system, one truth: Modules ARE slots. Upgrades install INTO modules.**

When you place a Weapon Mount module in the drydock, that IS a weapon slot. When you buy a Laser Cannon from the upgrades shop, you install it INTO that specific weapon mount. The module is the hardpoint; the upgrade is the equipment. You can see your Laser Cannon sitting in the weapon mount on your ship grid. In combat, it fires from where you placed it.

This is how Armored Core, Starfield, and FTL all work: the physical structure and the equipment are unified. You don't buy an arm and then separately buy the ability to use it.

### The Player Journey (Unified)

1. **Enter the Drydock** — place modules to build your ship structure
2. **Place a Weapon Mount** — the checklist shows "Weapon: 1" and the module has an empty equipment slot
3. **Click the weapon mount** (or switch to Equipment mode) — a panel shows available weapons you own
4. **Install Laser Cannon** into the weapon mount — the module's pixel art subtly changes to show it's armed, the stats panel updates with the weapon's combat stats
5. **Confirm build** — your ship has the Laser Cannon installed in the weapon mount you placed
6. **Enter combat** — the Laser Cannon fires. If that weapon mount module is destroyed, the Laser Cannon goes offline

**Everything connects. Everything makes sense.**

---

## Design Principles

1. **Modules define capacity.** The number and type of modules you place determines how many weapons, shields, engines, and utilities your ship can support. No more frame SLOT_POOLS.

2. **Upgrades define capability.** Weapons, shield generators, engine boosters, and utility equipment are installed into their matching module type. They provide the actual combat moves, stat bonuses, and special effects.

3. **The drydock is the single source of truth.** Everything about your ship — structure AND equipment — is visible and editable in the drydock. The shipyard's "Upgrades" tab becomes a shop for buying equipment, and "Installed" shows what's in your modules.

4. **Visual connection.** When a weapon is installed in a module, the module's appearance should subtly reflect it. The player can SEE their loadout on their ship.

5. **Spatial consequences.** Module placement matters for combat. A weapon mount on the bow fires forward. A shield generator in the center protects evenly. If a module is destroyed, its installed equipment goes offline. This is already partially implemented (Phase 9 module combat) but the equipment connection makes it meaningful.

---

## Unified Data Model

### Module Slots (Replace DesignatedSlot + SLOT_POOLS)

Each module with a `slot_type` in its `provides` dict IS an equipment slot:

| Module Category | Slot Type | What Installs Here |
|----------------|-----------|-------------------|
| Cockpit | `core` | Core systems (navigation computer, life support) |
| Engine | `engine` | Engine boosters, fuel injectors |
| Weapon | `weapon` | Weapons (Laser Cannon, Plasma Repeater, Ion Blaster) |
| Shield | `defense` | Shield generators, armor plating, ECM |
| Cargo | — | No equipment slot (cargo capacity is intrinsic) |
| Crew | — | No equipment slot (crew capacity is intrinsic) |
| Reactor | — | No equipment slot (power output is intrinsic) |
| Utility | `utility` | Scanners, mining drills, smuggling gear, misc equipment |
| Structural | — | No equipment slot (pure structure) |

**Key change**: The module's `provides.slot_type` replaces both `SLOT_POOLS` and `DesignatedSlot`. No more manually designating 2x2 slot areas on hull pixels.

### PlacedModule Extension

```python
@dataclass
class PlacedModule:
    module_id: str
    x: int
    y: int
    rotation: int = 0
    flipped: bool = False
    color_overrides: dict[tuple[int, int], str] = field(default_factory=dict)
    # NEW: Equipment installed in this module's slot
    installed_upgrade_id: Optional[str] = None
    upgrade_mark: int = 1
    upgrade_tuning: Optional[str] = None
```

Each PlacedModule that provides a slot_type can hold ONE installed upgrade. The upgrade ID, mark, and tuning are stored directly on the module — no separate DesignatedSlot needed.

### Equipment Installation Flow

```
Player places Weapon Mount module at (5, 3)
    → module.provides = {"slot_type": "weapon", ...}
    → module.installed_upgrade_id = None  (empty slot)

Player installs Laser Cannon into this module
    → module.installed_upgrade_id = "laser_cannon"
    → module.upgrade_mark = 1
    → module.upgrade_tuning = None

Player enhances to Mk2 with Overcharged tuning
    → module.upgrade_mark = 2
    → module.upgrade_tuning = "overcharged"
```

### Combat Move Resolution (Unified)

```python
# In build_player_combat_state():
equipment_moves = []
for placed_module in ship.build.modules:
    module = module_catalog[placed_module.module_id]
    if placed_module.installed_upgrade_id:
        upgrade = upgrades[placed_module.installed_upgrade_id]
        if upgrade.combat_move:
            move = CombatMove.from_dict(upgrade.combat_move)
            # Apply mark multiplier to damage
            if placed_module.upgrade_mark > 1:
                for effect in move.effects:
                    if effect.type == EffectType.DAMAGE:
                        effect.value *= MARK_MULTIPLIERS[placed_module.upgrade_mark]
            equipment_moves.append(move)
```

No more dual paths. No more legacy UpgradeManager combat move extraction. One path: modules → installed upgrades → combat moves.

---

## Drydock UI Changes

### Equipment Mode (New)

The drydock gains a third mode alongside MODULES and HULL:

**[MODULES]  [HULL]  [EQUIP]**

- **MODULES mode**: Place/remove/rotate ship modules (existing)
- **HULL mode**: Paint structural hull pixels (existing)
- **EQUIP mode**: Install/remove equipment into module slots

In EQUIP mode:
- Module slots with `slot_type` are highlighted with a colored border (weapon=red, defense=blue, etc.)
- Empty slots pulse gently to draw attention
- Clicking a slot opens an equipment panel showing available upgrades of that type
- The player selects an upgrade → it's installed into that specific module
- The module's pixel art gets a subtle overlay or icon indicating what's installed
- Stats panel updates immediately

### Visual Feedback

When a weapon is installed in a weapon mount:
- A small weapon icon or colored pip appears on the module in the grid
- The module's tooltip shows: "Talon Standard Hardpoint — Laser Cannon Mk2 (Overcharged)"
- The stats panel shows the weapon's damage, energy cost, element, and cooldown

When a slot is empty:
- The module shows a dim, pulsing outline in the slot's color
- The tooltip shows: "Talon Standard Hardpoint — EMPTY (install a weapon)"
- The requirements checklist could optionally note "2 of 4 weapon slots equipped"

### Equipment Panel (Contextual)

When the player clicks a module slot in EQUIP mode, a panel appears showing:
- **Available equipment** of the matching slot type that the player owns
- Each entry: name, tier, mark level, element (for weapons), key stats
- **Currently installed** equipment highlighted with a green border
- **"Uninstall"** button to remove equipment from the slot
- **"Install"** button to place selected equipment

Equipment ownership could work two ways:
- **Blueprint model** (consistent with module blueprints): player unlocks equipment blueprints, instantiates as needed
- **Inventory model** (current system): player buys equipment items, each one exists once

**Recommendation**: Keep the current inventory model for equipment. You buy a Laser Cannon, you have one. You install it in one weapon mount. If you want two, you buy two. This is the Armored Core model and it works.

---

## Shipyard Tab Restructure

### Current Tabs
Drydock | Frames | Parts | Upgrades | Installed

### Proposed Tabs
**Drydock** | **Frames** | **Parts** | **Equipment**

- **Drydock**: Opens the ship builder (unchanged)
- **Frames**: Buy weight class upgrades (unchanged)
- **Parts**: Buy module blueprints (unchanged)
- **Equipment**: Buy weapons, shields, engine mods, utilities — the current "Upgrades" tab, renamed for clarity

The "Installed" tab merges into the Drydock's EQUIP mode. You manage your loadout IN the builder, not in a separate tab. This eliminates the disconnect.

### Equipment Tab

The Equipment tab remains a shop for buying upgrade items. But it now shows:
- Which equipment you own (inventory)
- Which equipment is currently installed (and in which module)
- Available equipment for purchase

When you buy a piece of equipment, it goes into your inventory. You install it into a module slot in the Drydock's EQUIP mode.

---

## What Gets Retired

| Old System | Replacement |
|-----------|-------------|
| `SLOT_POOLS` (weapon/defense/utility/engine counts per weight class) | Module placement determines slot count |
| `DesignatedSlot` (manual 2x2 slot placement on hull) | `PlacedModule.installed_upgrade_id` |
| `ShipUpgradeManager._weapon_slots/_defense_slots/_utility_slots` | Count of modules with matching slot_type |
| `ShipUpgradeManager.installed` list | Equipment tracked per-module on `PlacedModule` |
| Separate "Installed" tab in shipyard | EQUIP mode in drydock builder |
| `[D] Slot` tool in hull mode | Removed (modules handle slots now) |
| Frame "Weapon: 2 Defense: 1 Utility: 3" display | Removed (module count replaces this) |

### What Stays

| System | Why |
|--------|-----|
| `ShipUpgrade` dataclass | Still defines equipment stats, combat moves, pricing, faction gating |
| Mark/Tuning enhancement | Still works, now stored on PlacedModule |
| `CombatMove` from upgrades | Still provides combat abilities |
| Equipment shop (renamed from "Upgrades") | Still where you buy weapons/shields/etc. |
| Module blueprints + Parts tab | Unchanged — how you acquire module types |
| Hull pixel painting | Unchanged — creative expression layer |

---

## Compatibility & Migration

### Save Compatibility

**Old saves** (pixel-only builds with DesignatedSlots):
- DesignatedSlots with `equipment_id` can be mapped to modules during migration
- Or: grandfather as "legacy build" that still uses the old system until rebuilt

**Module-based builds** (new system):
- `PlacedModule` gains `installed_upgrade_id`, `upgrade_mark`, `upgrade_tuning` fields
- Default: None/1/None (empty slot)
- Serialized in `to_dict()` / `from_dict()` with backward compat (.get() defaults)

### UpgradeManager Transition

The `ShipUpgradeManager` doesn't disappear immediately. Instead:
- For module-based builds: equipment is read from `PlacedModule.installed_upgrade_id`
- For legacy builds: equipment still comes from `UpgradeManager`
- The combat state builder checks which path to use
- Over time, all saves migrate to module-based builds

### Frame Slot Display

Frame descriptions in the Frames tab should stop showing "Weapon: 2 Defense: 1" since that's now determined by which modules you place. Instead, frames show:
- Canvas size
- Weight budget
- Suggested module count (for guidance, not enforcement)

---

## Balance: Preventing Degenerate Builds

### The Problem: 20 Weapon Mounts

Without SLOT_POOLS enforcing "Large ships get max 4 weapons," what stops a player from building a ship that's nothing but weapon mounts? A Light Hardpoint weighs only 1.5 — a Large ship (330 weight budget) could theoretically fit dozens.

This would be a glass cannon with no shields, no cargo, no crew quarters, minimal hull — but it would fire 20 weapons per combat round. That's not a ship. That's a turret array.

### The Solution: Layered Constraints

We use **multiple reinforcing constraints** rather than one hard cap. This creates natural trade-offs that feel like design decisions, not arbitrary limits.

#### 1. Energy Economy (Primary Lever)

Every weapon costs energy to fire. Energy comes from:
- **Base energy pool** (from cockpit/core module)
- **Reactor modules** (each adds power_output)
- **Energy regeneration** (per turn)

A typical weapon costs 2-5 energy. A typical ship has 10-16 energy pool with 3-5 regen per turn. If you have 20 weapons but only 15 energy, you can fire at most 3-5 weapons per turn. The rest sit idle.

**This is the Armored Core approach**: your mech has a generator with finite output. You can mount 8 weapons, but you can only fire the ones your generator can power. The player learns to match weapon count to energy budget.

**Implementation**: Energy is already in the combat system. The constraint already exists — we just need to make it visible in the builder. Show "Energy Budget: 15 / 20 weapons = can fire 3-4 per turn" in the stats panel.

#### 2. Weight Trade-offs (Secondary Lever)

Weapon modules have weight. More weapons = less weight budget for:
- **Shields** (survival) — a 20-weapon ship has paper shields
- **Engines** (evasion/speed) — a 20-weapon ship can't dodge
- **Cargo** (trading/income) — a 20-weapon ship can't trade
- **Hull pixels** (structural integrity) — thin ships sever easily
- **Reactors** (energy to fire those weapons) — need reactors to power them

The weight budget naturally punishes over-specialization. A ship with 20 weapons has no shields, no evasion, no cargo. It kills fast or dies fast.

#### 3. Module Slot Soft Caps (Tertiary Lever — Optional)

If energy + weight aren't sufficient, we can add soft caps per weight class:

| Weight Class | Max Weapon Modules | Max Defense Modules | Max Utility Modules |
|-------------|-------------------|--------------------|--------------------|
| Tiny | 2 | 2 | 2 |
| Small | 3 | 2 | 3 |
| Medium | 4 | 3 | 4 |
| Large | 6 | 4 | 5 |
| XLarge | 8 | 6 | 7 |

These are **soft caps** — the builder allows placement but shows a warning: "Weapon overload: 7 of 6 max. Energy costs increased by 50% for excess weapons." This penalizes over-stacking without forbidding it. A player CAN build a 7-weapon Large ship, but those extra weapons cost 50% more energy to fire, making them inefficient.

**Why soft caps instead of hard caps**: Hard caps feel arbitrary and frustrating. Soft caps with trade-offs feel like informed design decisions. "I know the 7th weapon is less efficient, but I'm willing to pay for it because my build relies on burst damage."

#### 4. Physics Constraints (Already Implemented)

The physics system from Phase 6 already penalizes degenerate builds:
- **Frontal profile**: More modules = wider ship = easier to hit = less evasion
- **Center of mass**: Stacking weapons on one side = off-balance = handling penalty
- **Structural integrity**: Thin connections between weapon clusters = severing risk
- **Hull efficiency**: All-module-no-hull builds have terrible perimeter-to-interior ratios

These don't directly cap weapon count, but they make a 20-weapon ship physically fragile and easy to hit.

#### 5. Combat Cooldowns (Already Implemented)

Many weapons have cooldowns (1-3 turns between uses). Even with 20 weapons, if half are on cooldown each turn, effective firepower is 10. Combined with energy limits, the actual damage output plateaus well before 20.

### The Recommended Approach

**Phase 1**: Rely on energy economy + weight trade-offs. These already exist and create natural limits. Make the energy budget VISIBLE in the builder so players understand why mounting 20 weapons doesn't mean firing 20 weapons.

**Phase 2 (if needed after playtesting)**: Add soft caps with efficiency penalties. Only if pure energy + weight doesn't prevent degenerate builds from dominating.

**Never**: Hard caps that say "you can't place more than N weapons." This feels bad and removes player agency. The game should let you build a 20-weapon turret array — it just shouldn't be optimal.

### Builder UI: Making Trade-offs Visible

The stats panel in the builder should show:

```
COMBAT READINESS
  Weapons: 4 installed (can fire 3/turn at current energy)
  Energy: 12 pool, 4/turn regen
  Shields: 180 HP, 6/turn regen
  Armor: 12
  Evasion: 8 (off-balance penalty: -15%)
```

This tells the player: "You have 4 weapons but can only fire 3 per turn because of energy. Adding a 5th weapon won't help unless you add another reactor." The trade-off is transparent.

---

## Implementation Phases

### Phase U1: Data Model Extension
- [ ] Add `installed_upgrade_id`, `upgrade_mark`, `upgrade_tuning` to `PlacedModule`
- [ ] Update serialization (to_dict/from_dict) with backward compat
- [ ] Create `get_module_equipment_slots(build, catalog)` → list of (module_idx, slot_type, installed_upgrade_id)
- [ ] Tests for new fields and slot extraction

### Phase U2: Combat Integration
- [ ] Update `build_player_combat_state()` to read equipment from modules (not UpgradeManager)
- [ ] Apply mark multipliers to combat moves from module-installed equipment
- [ ] Module disable in combat now also disables the installed weapon/shield
- [ ] Tests for combat move extraction from modules

### Phase U2.5: Combat Action Queue (Multi-Action Turns)

> **Milestone**: Players can fire multiple weapons per turn, gated by energy budget and cooldowns. Combat shifts from "pick one action" to "spend your energy wisely across your loadout." This makes module placement and weapon variety tactically meaningful.

#### The Problem: One Action Per Turn

The current combat system allows exactly one action per turn: fire one weapon OR activate one shield ability OR use one crew ability. This means:

- Having 4 weapons gives you OPTIONS (variety) but not THROUGHPUT (more damage per turn)
- A ship with 1 weapon and a ship with 4 weapons deal the same damage per turn
- Energy and cooldowns exist but don't create interesting per-turn decisions because you only spend energy once
- The player has no reason to manage their energy budget since one action rarely drains it

This undermines the module system. Why place 4 weapon mounts if you can only fire one? Why build reactors for more energy if you never spend it?

#### The Vision: Energy-Gated Multi-Action Turns

Each turn, the player has an **action phase** where they can queue multiple actions until they:
- Run out of energy
- Run out of off-cooldown weapons
- Choose to end their turn (saving energy for defense abilities or next turn)

**Example turn with 12 energy:**
1. Fire Small Laser (2 energy, 0 cooldown) → 10 energy remaining
2. Fire Plasma Repeater (3 energy, 2-turn cooldown) → 7 energy remaining
3. Activate Shield Restore (2 energy, 1-turn cooldown) → 5 energy remaining
4. Fire Small Laser again? No — each weapon fires max once per turn
5. End Turn → 5 energy saved, regenerates next turn

**Example turn with a missile boat:**
1. Fire Torpedo (5 energy, 3-turn cooldown) → 7 energy remaining
2. Fire Missile Rack (4 energy, 2-turn cooldown) → 3 energy remaining
3. Can't afford Ion Cannon (4 energy) → End Turn

**Key rules:**
- Each weapon/ability can fire **at most once per turn** (no spamming the same laser 6 times)
- Energy is the shared resource across all actions
- Cooldowns prevent high-power weapons from firing every turn
- Unspent energy does NOT carry over (regenerates to pool each turn) — encouraging the player to use it
- Crew abilities and defensive abilities also cost actions and energy, competing with weapons

#### Why This Works

**1. Module count becomes throughput.**
4 weapon mounts = 4 potential shots per turn. But only if you have the energy. This directly rewards building reactors and balancing your loadout.

**2. Energy creates per-turn decisions.**
"I have 12 energy. Do I fire 3 cheap weapons for sustained damage, or save energy for my shield restore in case the boss attacks? Do I fire the expensive torpedo now or hold it for when the boss enters its vulnerable phase?"

**3. Weapon variety creates rotation.**
A mix of cheap/fast and expensive/slow weapons creates interesting turn-by-turn patterns. Turn 1: fire everything. Turn 2: torpedo is on cooldown, fire the lasers and restore shields. Turn 3: torpedo ready again, alpha strike.

**4. Build diversity deepens.**
- **Glass cannon**: 5 weapons, big reactor, minimal shields. Dumps all energy into damage.
- **Balanced fighter**: 3 weapons, 1 shield ability, moderate reactor. Mixes offense and defense each turn.
- **Tank**: 2 weapons, 2 shield abilities, heavy shields. Fires less but survives everything.
- **Burst striker**: 2 expensive weapons with long cooldowns, small laser filler. Massive damage every 3 turns, sustain between.

#### Combat UI: Action Queue

The combat view needs a new interaction model:

```
┌─────────────────────────────────────────────────┐
│  YOUR TURN                     Energy: 7/12     │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Laser Cannon]  2E  Ready     ← click to queue │
│  [Plasma Repeater]  3E  Ready  ← click to queue │
│  [Ion Blaster]  4E  Cooldown 1 ← grayed out     │
│  [Shield Restore]  2E  Ready   ← click to queue │
│                                                 │
│  ─── QUEUED ACTIONS ───                         │
│  1. Laser Cannon → Enemy 1        (-2E)         │
│  2. Plasma Repeater → Enemy 1     (-3E)         │
│                                    ────          │
│                         Energy after: 2/12       │
│                                                 │
│  [EXECUTE TURN]              [UNDO LAST]        │
└─────────────────────────────────────────────────┘
```

**Flow:**
1. Available actions shown with energy cost and cooldown status
2. Player clicks an action → selects target (if offensive) → action added to queue
3. Queue shows planned actions with running energy total
4. "Undo Last" removes the most recent queued action
5. "Execute Turn" resolves all queued actions in order, then enemies act
6. Actions that become invalid (target died from earlier action in queue) are skipped with a log note

**Keyboard shortcuts:**
- Number keys (1-6) to quick-select weapons
- Enter to execute turn
- Backspace to undo last queued action
- Space to end turn without queuing more

#### Balance Implications

**Energy regeneration becomes critical.** Currently energy regens each turn but is barely spent. With multi-action turns, energy regen determines sustained DPS:
- 4 regen = 4 energy per turn = ~2 cheap weapons sustained
- 6 regen = can sustain 3 weapons per turn
- Reactors that provide energy_regen become essential, not decorative

**Cooldowns become the burst limiter.** Without cooldowns, a 5-weapon ship with 15 energy could fire everything every turn. Cooldowns force weapon rotation and create tempo:
- Small Laser: 0 cooldown, 2 energy — fires every turn (sustained DPS filler)
- Plasma Repeater: 1 cooldown, 3 energy — fires every other turn (mid-range burst)
- Torpedo: 3 cooldown, 5 energy — fires every 4th turn (alpha strike)
- Shield Restore: 1 cooldown, 2 energy — defensive option on alternate turns

**First-turn alpha strike is intentional.** On turn 1, all weapons are off cooldown. A 4-weapon ship CAN fire all 4 on turn 1 if it has the energy. This is the "opening salvo" fantasy. Subsequent turns require managing cooldowns.

**Enemy balance needs adjustment.** If the player can deal 2-4x damage per turn, enemy HP needs to scale. This is a tuning pass, not a design problem. Boss HP already scales with `boss_hp_multiplier`.

#### Implementation Sub-Phases

##### Phase U2.5a: Action Queue Model
- [ ] New `ActionQueue` class: ordered list of `(move, target_idx)` tuples
- [ ] Queue validation: energy budget, cooldown check, once-per-turn-per-weapon rule
- [ ] Queue execution: resolve actions in order, skip invalid (dead target), accumulate logs
- [ ] Each-weapon-once-per-turn tracking: `set[str]` of move IDs used this turn
- [ ] Energy deduction happens as actions are queued (preview), confirmed on execute
- [ ] Tests for queue building, validation, execution, and edge cases

##### Phase U2.5b: Combat Engine Refactor
- [ ] Replace `execute_player_move(move_id, target_idx)` with `execute_player_turn(queue: ActionQueue)`
- [ ] All queued actions resolve before enemy turns
- [ ] Hit/miss/graze resolved independently per action
- [ ] Momentum accumulates across all actions in the turn
- [ ] Chain Fire legendary: triggers per-action (each hit can chain), not per-turn
- [ ] Phase Shift: blocks first incoming attack per round (not per action)
- [ ] End-of-turn processing unchanged (effects tick, cooldowns set, regen)
- [ ] Backward compat: if queue has exactly 1 action, behavior identical to current system
- [ ] Tests for multi-action resolution, momentum, legendary interactions

##### Phase U2.5c: Combat View Overhaul
- [ ] Action selection panel: list available moves with energy cost, cooldown, element
- [ ] Click-to-queue interaction: click move → click target → added to queue
- [ ] Queue display panel: ordered list of planned actions with running energy total
- [ ] Undo button: remove last queued action, refund energy
- [ ] Execute button: resolve queue, animate all actions, transition to enemy turn
- [ ] Keyboard shortcuts: 1-6 for weapons, Enter to execute, Backspace to undo
- [ ] Grayed-out moves: insufficient energy, on cooldown, already used this turn
- [ ] Energy bar updates in real-time as actions are queued
- [ ] Animation: each queued action resolves with its own hit/damage animation sequence
- [ ] "Turn Summary" log entry showing all actions taken

##### Phase U2.5d: Balance Tuning
- [ ] Review all weapon energy costs for multi-action balance
- [ ] Review cooldowns: cheap weapons should be 0-1 cooldown, expensive 2-3
- [ ] Review energy pool/regen values from reactors and cockpits
- [ ] Review enemy HP scaling (may need +50% across the board)
- [ ] Playtest: verify glass cannon, tank, and balanced builds all feel viable
- [ ] Verify legendary mechanics work correctly with multi-action (chain fire, void absorption)
- [ ] Document the "energy budget" in builder stats panel

#### Design Questions to Resolve

1. **Can defensive abilities be queued alongside offensive?** Recommended: Yes. Shield Restore competes with weapons for your energy budget. This creates meaningful defense/offense trade-offs per turn.

2. **Can crew abilities be queued?** Recommended: Yes, one crew ability per turn (crew are a separate action slot, not from the weapon queue). This preserves the existing crew combo system.

3. **Does unspent energy carry over?** Recommended: No. Energy regenerates to `min(pool, current + regen)` each turn. This prevents hoarding and encourages spending.

4. **Can the player fire the same weapon twice per turn?** Recommended: No. Each weapon/ability fires at most once per turn. This prevents "6 small lasers = 12 damage for 12 energy" from being strictly optimal. It rewards weapon variety.

5. **What happens if a queued target dies mid-queue?** Recommended: Skip that action, refund energy, log "Target destroyed — [Weapon] held fire." The player doesn't lose the energy or the cooldown.

6. **Can the player change targets mid-queue?** Recommended: Yes. Each queued action has its own target. "Laser → Enemy 1, Plasma → Enemy 2" is valid. This adds tactical depth in multi-enemy encounters.

---

### Phase U3: Drydock EQUIP Mode
- [ ] Add EQUIP mode toggle (third mode alongside MODULES and HULL)
- [ ] Render slot highlights on modules with slot_type
- [ ] Click-to-open equipment panel for a slot
- [ ] Equipment panel: show owned equipment matching slot type
- [ ] Install/uninstall flow with immediate stat updates
- [ ] Visual feedback: installed equipment indicator on module

### Phase U4: Shipyard Restructure
- [ ] Rename "Upgrades" tab to "Equipment"
- [ ] Remove "Installed" tab (merged into EQUIP mode)
- [ ] Equipment tab shows inventory (owned items, installed location)
- [ ] Update frame display to remove slot pool numbers
- [ ] Remove `[D] Slot` tool from hull mode

### Phase U5: Legacy Retirement
- [ ] Remove SLOT_POOLS from frame validation
- [ ] Remove DesignatedSlot from new builds (keep for legacy load)
- [ ] Remove ShipUpgradeManager slot counting (weapon_slots, etc.)
- [ ] Update all slot pool references in UI and validation
- [ ] Save migration: convert DesignatedSlot builds to module-based

---

## Player Experience: Before and After

### Before (Current)
> "I placed weapon modules on my ship but I don't know what they do. I went to the upgrades tab and bought a Laser Cannon. I guess that's what fires in combat? Why did I place those weapon modules in the drydock? What's the connection?"

### After (Unified)
> "I placed a Weapon Mount on my ship's bow. It has an empty slot. I switched to EQUIP mode and installed my Laser Cannon into it. I can see it sitting right there on my ship."

> "In combat, I have 12 energy. I queue up my Laser Cannon (2E) against the fighter, my Plasma Repeater (3E) against the frigate, and activate Shield Restore (2E). 5 energy left — I hold it. All three actions resolve: the fighter takes laser damage, the frigate starts burning from plasma, and my shields top off. Then the enemies attack. My bow weapon mount takes a hit — the Laser Cannon goes offline. Next turn I'm down to two weapons. I should have protected it better."

> "I rebuilt with the weapon mounts deeper in the hull and added a second reactor for more energy per turn. Now I can sustain 3 weapons every turn instead of running dry by turn 2."

The unified experience tells a story across building, equipping, and fighting. Every decision connects.

---

## Metrics for Success

- **Zero confusion** about what fires in combat and why
- **Spatial meaning** — where you place equipment affects what happens when it's hit
- **One workflow** — the drydock is where you build AND equip your ship
- **Energy creates per-turn decisions** — "fire everything or save energy for defense?"
- **Module count = options per turn** — more weapons means more shots IF you have the energy budget
- **Progressive depth** — beginners place modules and fire one weapon; advanced players optimize energy rotation, cooldown cycling, and module placement for survivability
- **No orphaned systems** — every piece of the UI connects to the same underlying model
