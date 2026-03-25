# Shipyard Revamp: Slot-Based Ship Building

> **Status**: REQUIREMENTS DRAFT
> **Created**: 2026-03-25
> **Context**: The current shipyard has overlapping systems (modules + equipment) that confuse
> the player. This revamp separates ship design (structure/slots), part acquisition (shopping),
> and loadout configuration (equipping) into three clear activities with dedicated UI tabs.

---

## Design Philosophy

**The builder should be about spatial strategy, not shopping.** The player designs where
slots go on the grid, making structural tradeoffs (more weapons = less cargo, exposed
slots are vulnerable in combat, weight distribution affects physics). The complexity and
variety live in the parts catalog, not the builder.

**Three clear activities, three clear tabs:**
1. **Drydock** -- Design the ship. Place slots, paint hull pixels. No currency involved.
2. **Shop** -- Buy frames and parts. Browse catalogs, manage inventory.
3. **Loadout** -- Assign owned parts to slots. Configure the combat/trade loadout.

**"Design it, buy for it, equip it."**

---

## Tab 1: Drydock (Ship Designer)

### Purpose
Design the ship's physical layout. Place typed/sized slot placeholders on the pixel grid
and paint hull pixels for structural stats and cosmetic expression.

### What the Player Does
- Select a slot type and size from a simple palette (not a shopping catalog)
- Click on the grid to place the slot (occupies a rectangular footprint)
- Paint hull pixels around and between slots (material choice affects HP, armor, evasion)
- Rotate and flip slots for layout flexibility
- Review physics constraints (weight, structural integrity, center of mass)

### Slot Types

| Type | Purpose | Required? | Notes |
|------|---------|-----------|-------|
| **Weapon** | Mounts offensive weapons | No | More = more actions per combat turn |
| **Defense** | Mounts shields, armor plating, point defense | No | Determines defensive capability |
| **Engine** | Mounts thrusters, drives | Yes (min 1) | Determines speed; must be placed at rear |
| **Utility** | Mounts sensors, nav computers, fuel tanks, misc | No | Flexible catch-all for non-combat gear |
| **Cargo** | Mounts cargo bays, specialized containers | No | Determines trade capacity |
| **Crew Quarters** | Houses crew members | No | Each slot houses 1-2 crew depending on size |
| **Reactor** | Provides power/energy for combat | Yes (min 1) | Powers weapons, shields, abilities |

### Slot Sizes

Each slot type comes in three sizes with different grid footprints:

| Size | Typical Footprint | Weight | Accepts |
|------|-------------------|--------|---------|
| **Small (S)** | 2x2 or 2x3 | Light | Basic/starter parts |
| **Medium (M)** | 3x3 or 3x4 | Moderate | Mid-tier parts |
| **Large (L)** | 4x4 to 4x6 | Heavy | Advanced/heavy parts |

Exact footprint varies by slot type (e.g., a Large Cargo bay might be 4x6 while a Large
Weapon slot is 4x4). Each slot type+size combination has a defined pixel mask.

### Frame Constraints

Each frame defines:
- Canvas dimensions (width x height in pixels)
- Maximum weight budget
- Maximum slot counts per type (e.g., "Weapon: 3, Defense: 2, Engine: 2, ...")
- Cockpit (built-in, not placeable -- see Cockpit section)

Example frame slot limits:
```
Light Freighter (Small Frame):
  Weapon: 2, Defense: 1, Engine: 1, Utility: 2, Cargo: 3, Crew: 1, Reactor: 1

Armed Trader (Medium Frame):
  Weapon: 3, Defense: 2, Engine: 2, Utility: 3, Cargo: 4, Crew: 2, Reactor: 1

Heavy Cruiser (Large Frame):
  Weapon: 5, Defense: 3, Engine: 3, Utility: 4, Cargo: 2, Crew: 3, Reactor: 2
```

### Cockpit

The cockpit is **mandatory and built into the frame**. It is NOT a placeable slot.
- Each frame has a unique cockpit design (pixel art) that renders at a fixed position
- The cockpit always supports 1 crew (the captain/protagonist)
- The cockpit contributes to the ship's visual identity
- The cockpit cannot be removed, moved, or destroyed in combat

### Hull Pixels

Hull pixels remain the cosmetic/structural layer:
- Material choice affects: hull HP, armor, evasion, weight
- Players are incentivized to design thoughtful silhouettes (frontal profile affects targeting)
- Hull efficiency (interior vs perimeter ratio) still matters
- Structural integrity (connectivity) still validated

### Drydock Costs

Hull pixels and slots cost credits to place. This represents fabrication and installation
costs -- you're physically building the ship structure.

- **Hull pixels**: cost per pixel based on material (already exists in material data)
- **Slots**: moderate cost per slot, scaling with size (S < M < L) and type
  - Weapon/Defense slots cost more than Utility/Cargo (military-grade mounting hardware)
  - Example costs: Weapon S = 500 CR, Weapon M = 1,500 CR, Weapon L = 4,000 CR

**No double-charging on modifications.** When the player enters the Drydock to edit an
existing build, the system tracks deltas:
- Adding new slots/pixels charges for the additions
- Removing slots/pixels refunds 80% of the original placement cost
- Moving a slot (remove + re-place) nets to a small repositioning fee
- This delta-cost system already exists from the Shipbuilder Upgrade (Phase 8)

### What's NOT in the Drydock
- No equipment assignment -- that's the Loadout tab
- No part browsing -- that's the Shop tab
- No frame selection -- that's the Shop tab

### Builder Palette

The slot palette should be simple and clear:
```
[Weapon S] [Weapon M] [Weapon L]
[Defense S] [Defense M] [Defense L]
[Engine S] [Engine M] [Engine L]
[Utility S] [Utility M] [Utility L]
[Cargo S] [Cargo M] [Cargo L]
[Crew S] [Crew M]
[Reactor S] [Reactor M] [Reactor L]
```

Each slot renders as a distinctly colored outline on the grid with a type icon.
The slot palette replaces the current 144-item module catalog.

---

## Tab 2: Shop (Parts Vendor)

### Purpose
Buy frames and ship parts. Everything purchased goes into the player's **inventory**.
Parts are physical items you own -- not abstract unlocks.

### Sub-tabs

#### Frames
- Browse available ship frames
- Shows: canvas size, slot limits, base stats, cockpit design, price
- Stat comparison vs current frame
- Buying a new frame keeps your inventory but resets the Drydock layout
- Trade-in value for current frame (80% of purchase price?)

#### Parts (with category sub-tabs)
Parts are organized by slot type, with sub-tabs for easy navigation:

| Sub-tab | Contains | Example Parts |
|---------|----------|---------------|
| **Weapons** | All weapon parts S/M/L | Light Laser, Plasma Cannon, Ion Beam, Heavy Railgun |
| **Defense** | Shield generators, armor | Light Shield Gen, Heavy Armor Plate, Point Defense |
| **Engines** | Thrusters, drives | Ion Thruster, Fusion Drive, Afterburner |
| **Utility** | Sensors, nav, fuel, misc | Fuel Tank, Sensor Array, Tractor Beam |
| **Cargo** | Cargo bays, containers | Standard Bay, Refrigerated Bay, Smuggling Compartment |
| **Crew** | Quarters, life support | Basic Quarters, Officer Cabin, Medical Bay |
| **Reactors** | Power plants, generators | Fission Reactor, Fusion Core, Antimatter Generator |

Each part listing shows:
- Name, size (S/M/L), price
- Stats it provides when equipped
- Whether the player already owns one (inventory count)
- Faction/station availability (some parts only sold at certain stations)

### Inventory System

Parts are **inventory items**:
- When you buy a Light Laser, it goes into your parts inventory
- Your inventory persists across station visits
- You can own multiple of the same part (e.g., 2x Light Laser for 2 weapon slots)
- Unequipping a part returns it to inventory (not destroyed)
- Parts can be sold back at any station (70-80% of purchase price)
- Inventory has no weight/space limit (parts are small, the ship's slots determine what's active)

### What the Existing 144 Modules Become

Most current modules map directly to parts:
- Weapon modules (32) -> Weapon parts with appropriate S/M/L sizes
- Shield modules -> Defense parts
- Engine modules -> Engine parts
- Cargo modules -> Cargo parts
- Utility modules -> Utility parts
- Cockpit modules -> Absorbed into frame definitions (removed as purchasable items)
- Structural modules -> Removed (hull pixels handle structure)
- Station signature modules -> Become station-exclusive parts (faction flavor preserved)
- Legendary modules -> Become legendary parts (boss drops preserved)

Manufacturer variety is preserved -- Reyes Kowalski parts, Sung Dynamics parts, etc.
still exist as different parts with different stat profiles.

---

## Tab 3: Loadout (Equipment Assignment)

### Purpose
Assign parts from your inventory to the slots on your ship. This is where the ship
becomes combat/trade-ready.

### What the Player Does
- See their ship layout (from Drydock) with all slots visible
- Click a slot to see what parts in their inventory fit that slot (right type + right size)
- Assign a part to the slot (or swap it for a different one)
- See the live stat changes as parts are equipped/unequipped
- Review the complete ship stats summary

### UI Layout
- Left: ship grid visualization showing all slots (color-coded by type)
- Right: selected slot details + compatible parts from inventory
- Bottom: complete ship stat summary (hull, shields, cargo, fuel, speed, etc.)

### Rules
- A part can only be in one slot at a time
- Unequipping a part returns it to inventory immediately
- Empty slots provide no stats (the slot is just a placeholder)
- The ship can launch with empty slots (but the player is warned)
- Parts must match the slot's type AND fit within the slot's size (S part fits in S/M/L slot, M part fits in M/L slot, L part only fits in L slot)

### Part Size Compatibility

| Part Size | Fits in Slot S | Fits in Slot M | Fits in Slot L |
|-----------|---------------|---------------|---------------|
| Small | Yes | Yes | Yes |
| Medium | No | Yes | Yes |
| Large | No | No | Yes |

This means larger slots are strictly more flexible. A Large Weapon slot can mount
anything from a Light Pistol (S) to a Heavy Railgun (L). This creates a meaningful
tradeoff: Large slots take more grid space and weight, but accept any part.

---

## Stat Computation

### Ship Stats Come From:

| Stat | Source |
|------|--------|
| Hull HP | Hull pixels (material) |
| Armor | Hull pixels (material) + defense parts |
| Shields | Defense parts (shield generators) |
| Shield Regen | Defense parts |
| Speed | Frame base + engine parts |
| Evasion | Frame base + hull pixel bonuses + utility parts |
| Fuel Capacity | Utility parts (fuel tanks) -- minimum 10 guaranteed |
| Cargo Capacity | Cargo parts (cargo bays) |
| Power/Energy | Reactor parts |
| Crew Capacity | Crew parts + cockpit (1 always for captain) |
| Weapon Damage | Weapon parts (per-weapon, used in combat) |
| Accuracy | Frame base + utility parts |

### Frame Base Stats
Each frame provides base values for speed, evasion, and accuracy that are present
even without any parts equipped. This ensures a bare frame can at least move.

---

## Combat Integration

### Module-Targeted Damage
Slots replace modules as combat targets. When an enemy attacks:
- Hit location is determined by pixel coverage (same as current system)
- If the hit lands on a slot's footprint, that slot takes damage
- Slots have HP (based on the equipped part)
- When a slot's HP reaches 0, the part is disabled for the rest of combat
- Disabled weapons can't fire, disabled engines reduce speed, etc.

### Multi-Action Combat
The action queue system works identically:
- Each weapon slot = one available weapon action per turn
- Energy budget (from reactor parts) gates how many actions per turn
- More weapon slots + bigger reactor = more combat flexibility

### Overkill Propagation
Excess damage to a slot propagates to adjacent hull pixels (unchanged from current).

---

## Save Migration

### Backward Compatibility
- Old saves with module-based builds: modules are mapped to equivalent slot+part pairs
- Old saves with legacy DesignatedSlot: mapped to new slot system
- The migration uses the module's category and provides dict to determine slot type and size
- Parts that can't be mapped get converted to credits at 80% value

### New Save Format
```python
ShipBuild:
  weight_class: str
  pixels: list[HullPixel]      # Unchanged
  slots: list[PlacedSlot]      # Replaces modules list
    - slot_type: str            # "weapon", "defense", "engine", etc.
    - size: str                 # "small", "medium", "large"
    - x, y: int                 # Grid position
    - rotation: int             # 0/90/180/270
    - equipped_part_id: Optional[str]  # ID of the part installed (or None)

Player:
  parts_inventory: dict[str, int]  # part_id -> count owned (not equipped)
```

---

## Implementation Phases

### Phase S1: Data Foundation
- Define slot type + size data schema
- Create slot definitions (footprints, weight, visual masks for each type+size)
- Reclassify existing 144 modules into parts with slot type + size requirements
- Add `parts_inventory` to Player model
- Add frame slot limits to ShipType data
- Update ComputedShipStats to read from slot+equipment pairs

### Phase S2: Drydock Overhaul
- Replace module catalog with slot type/size palette
- Slot placement with grid footprint, rotation, snap
- Update validation (frame slot limits, weight, connectivity)
- Remove module-specific logic from builder
- Cockpit rendered as part of frame (not placeable)

### Phase S3: Shop Tab
- Frame sub-tab (similar to current Frames tab)
- Parts sub-tab with category navigation
- Inventory display (what you own, what's equipped)
- Purchase flow (buy part -> goes to inventory)
- Sell flow (sell from inventory, can't sell equipped parts)
- Station-specific part catalogs (faction variety preserved)

### Phase S4: Loadout Tab
- Ship visualization with slot highlighting
- Slot selection -> compatible parts list from inventory
- Equip/unequip flow with live stat preview
- Ship stats summary panel
- Launch readiness warnings (empty required slots)

### Phase S5: Combat + Migration
- Update combat hit resolution to use new slot model
- Update stat computation chain
- Save migration for old module-based builds
- Preserve legendary parts and boss drops

### Phase S6: Polish
- Visual slot rendering on grid (type-colored outlines with icons)
- Part tooltips and comparison
- Inventory management improvements
- Tutorial updates

---

## What This Removes (Simplification)

| Current | After Revamp |
|---------|-------------|
| 144 module items in builder catalog | ~21 slot types (7 types x 3 sizes) |
| Parts tab (modules you buy) | Merged into Shop > Parts |
| Equipment tab (upgrades for modules) | Merged into Loadout |
| Module blueprint unlocks | Parts available at station shops |
| Module instantiation cost in builder | Slot placement cost (fabrication) + part purchase cost (separate) |
| Confusion between modules and equipment | Clear: slots (structure) vs parts (equipment) |

---

## What This Preserves

- Hull pixel system (materials, cosmetics, structural stats)
- Module-targeted combat (slots are the new targets)
- Physics constraints (weight, structural integrity, center of mass)
- Faction-specific catalogs (station shops sell different parts)
- Manufacturer variety (Reyes Kowalski, Sung Dynamics, etc.)
- Legendary parts (boss drops)
- Multi-action combat (weapon slot count = available actions)
- Build sharing codes (encode slots instead of modules)
- Ship composite rendering (slots render as colored regions on the pixel grid)

---

## Open Questions

1. **Engine placement constraint**: Should engines still be required at the rear 25% of the ship?
   Recommend: Yes, preserves spatial strategy.

2. **Reactor placement**: Any position constraint? Recommend: center-ish preferred but not enforced.

3. **Part durability/repair**: Should parts take permanent damage that needs repair at a station?
   Recommend: No for now -- parts are disabled in combat but auto-repair after. Future feature.

4. **Part quality tiers**: Should parts have Mk1/Mk2/Mk3 like current upgrades?
   Recommend: Yes, preserves progression depth. Higher marks cost more and have better stats.

5. **Maximum inventory size**: Should the parts inventory have a limit?
   Recommend: No hard limit. The cost of buying parts is the natural limiter.
