# Shipyard Overhaul — Pixel Ship Designer

> The player doesn't pick a ship. They BUILD one. A grid of pixels IS the ship — every square, every triangle, every angled hull plate placed by the player's hand. The ship on the galaxy map, the ship in combat, the ship on the victory screen — that's YOUR creation, drawn from geometric shapes on a canvas bounded only by your weight class and your wallet. This is the core identity feature of Aurelia.

---

## Vision

### The Fantasy

You dock at Breakstone and walk into a cavernous shipyard bay. A holographic grid shimmers to life — 32 by 32 pixels of possibility. You drag a heavy triangle onto the bow, giving your ship a sharp armored prow. You stamp two long rectangles along the flanks — engine housings, light alloy to keep the weight down. A reinforced 4x4 block for the core, shield crystal panels along the dorsal spine. You designate weapon hardpoints at the wing tips, mark the engines at the stern. The weight bar hovers at 72%. The credit counter ticks down with each placement.

When you undock, that grid IS your ship. The pointed bow, the crystal spine, the engine blocks — rendered pixel for pixel on the galaxy map. In combat, it's there — YOUR ship, firing from the hardpoints YOU placed. Not a stock sprite. Not a template someone else designed. Yours.

Then you salvage a derelict in the Iron Depths and find something: a swept-wing hull fragment, a shape you've never seen before. Back at the shipyard, it's in your palette — a sleek curved wing piece that no amount of credits could buy. You tear off the old rectangular flanks and replace them with these swept wings. The ship transforms. It's still yours, but it's evolved.

That's the fantasy. Your ship is your signature.

### Design Pillars

1. **The grid IS the ship.** What you draw is what renders. No abstraction layer between "your build" and "your sprite." The 32x32 pixel canvas IS the 32x32 pixel sprite.

2. **Shapes are building blocks, not individual pixels.** You don't paint pixel by pixel (tedious). You stamp geometric shapes — triangles, rectangles, L-shapes, wings — onto the canvas. Like building with blocks, but the result is pixel art.

3. **Weight class defines your canvas.** Five tiers from Tiny (16x16) to Extra Large (64x64). Bigger canvas = more pixels = more stats = more slots = more cost. Weight class is your ship's "size," not its playstyle.

4. **Materials define your identity.** The same shape filled with Heavy Armor gives hull and armor. Filled with Shield Crystal, it gives shields. Filled with Stealth Composite, it gives evasion. Material choice IS defensive identity choice — and it shows in the ship's color.

5. **Slots are YOUR choice.** You designate where weapons, shields, engines, and utilities go. A pool of slots based on weight class, placed anywhere on filled pixels. Your slot layout defines your ship's capabilities.

6. **Discovery drives progression.** Basic shapes are free. Advanced shapes come from salvage runs, quest rewards, faction reputation, mining discoveries, and the black market. Finding a rare shape template is as exciting as finding a rare weapon.

7. **Cost creates meaning.** Building is expensive. Upgrading your weight class is a major purchase. Every pixel placed costs credits. This makes the ship feel EARNED — you scraped, traded, and fought for every hull plate.

8. **We build tools, not sprites.** This is a strategic shift in development philosophy. Hand-crafting 24+ unique ship sprites is expensive, slow, difficult to get right, and scales poorly. Instead, we create a library of simple geometric shapes and materials — triangles, rectangles, curves, hull plating types — and let players combine them into infinite ship designs. A single swept-wing triangle template creates more visual variety than a dozen hand-drawn sprites ever could. Every new shape we add multiplies the possibility space. Every new material changes the palette. We are no longer in the business of pixel art production — we are in the business of giving players parts and options. Simpler to create, vastly greater in effect, and the player gets something no pre-made sprite could ever give them: ownership.

### Inspirations

- **Armored Core**: Weight classes, stat trade-offs, the build IS your identity
- **Starfield Ship Builder**: Snap-together visual construction, seeing your creation take shape
- **LEGO / Tetris**: The satisfaction of fitting geometric pieces together on a grid
- **Pixel art editors**: The simple joy of placing colored squares to make something recognizable
- **FTL**: Your ship as a collection of functional parts, not a stat block

---

## Weight Classes

Weight class determines your canvas size, stat budgets, slot pools, and cost tier. Weight class is purely about SIZE — playstyle identity comes from materials and slot allocation.

| Class | Canvas | Filled Pixels (typical) | Max Slots | Max Weight | Unlock Cost | Ship Size Feel |
|-------|--------|------------------------|-----------|------------|-------------|---------------|
| **Tiny** | 16×16 | 80-120 | 4 | 40 | Free (starter) | Shuttle, escape pod |
| **Small** | 24×24 | 180-280 | 7 | 80 | 15,000 CR | Scout, courier, sloop |
| **Medium** | 32×32 | 350-500 | 10 | 140 | 60,000 CR | Freighter, fighter, corsair |
| **Large** | 48×48 | 700-1000 | 14 | 240 | 200,000 CR | War frigate, hauler, cruiser |
| **Extra Large** | 64×64 | 1200-1800 | 18 | 400 | 500,000 CR | Battlecruiser, capital ship, titan |

**Canvas Pixel Density Guidelines:**
- Ships don't fill every pixel — 40-70% fill rate looks best (silhouette with negative space)
- A 32×32 medium ship at ~50% fill = ~500 pixels = a recognizable ship shape
- Thinner shapes (fast ships) might be 35% fill; bulky shapes (haulers) might be 65%

**Weight Relationship:**
Each filled pixel contributes weight based on its material. Total weight must stay under the weight class maximum. Heavier materials (Heavy Armor) fill the budget faster, forcing fewer total pixels or lighter materials elsewhere.

### Slot Pools by Weight Class

| Class | Weapon | Defense | Utility | Engine | Total |
|-------|--------|---------|---------|--------|-------|
| **Tiny** | 1 | 1 | 1 | 1 | 4 |
| **Small** | 2 | 1 | 2 | 2 | 7 |
| **Medium** | 3 | 2 | 3 | 2 | 10 |
| **Large** | 4 | 3 | 4 | 3 | 14 |
| **Extra Large** | 6 | 4 | 5 | 3 | 18 |

Slots are placed on filled pixels during the build phase. Each slot occupies a 2×2 pixel area on the grid (it must overlay 4 filled pixels). This means slots need hull beneath them — you can't float a weapon in empty space.

### Weight Class Progression

Weight class upgrades are major milestones — comparable to buying a new ship in the current system:

- **Tiny → Small**: Equivalent of upgrading from Shuttle to Patrol Cutter/Light Freighter
- **Small → Medium**: The mid-game breakpoint. Most players reach this by mid-campaign
- **Medium → Large**: Late-game investment. War Frigate / Bulk Hauler territory
- **Large → Extra Large**: End-game aspiration. The ultimate build platform

When upgrading weight class:
- Old build is preserved (can be loaded as a preset)
- New canvas starts empty OR player can "import" their old build into the center of the new canvas
- Materials and shapes already purchased/unlocked carry over

---

## The Building Grid

### How It Works

The grid is a 2D pixel canvas. Empty cells are transparent. Filled cells contain a material. The player builds by stamping shapes onto the grid.

**Grid States (per pixel):**
```
EMPTY       — Nothing. Transparent in the final sprite.
FILLED      — Contains a material. Renders as that material's color.
SLOT        — Filled pixel that's also designated as an equipment slot.
                Renders with a subtle slot-type indicator overlay.
```

**Coordinate System:**
- Origin (0,0) at top-left
- X increases rightward, Y increases downward
- Center of grid is the ship's center of mass (for rotation in-game)

### Building Tools

The builder provides these tools (toolbar at bottom of screen):

| Tool | Icon | Behavior | Hotkey |
|------|------|----------|--------|
| **Shape Stamp** | Block icon | Select shape from palette, click to place | S |
| **Pencil** | Dot icon | Place individual pixels (1×1) | P |
| **Eraser** | X icon | Click to remove pixels/shapes | E |
| **Material Brush** | Paint bucket | Click filled pixels to change their material | M |
| **Slot Designator** | Crosshair | Click to place/remove equipment slots | D |
| **Fill** | Bucket icon | Fill enclosed area with current material | F |
| **Select** | Arrow icon | Click+drag to select region, move/copy/delete | V |
| **Mirror** | Symmetry icon | Toggle left-right mirror mode (auto-duplicate) | X |

**Mirror Mode** is critical for making ship-building accessible. When enabled, anything placed on the left half of the canvas is automatically mirrored to the right half. Most ships are symmetrical, so this cuts building time in half and produces cleaner results. Can be toggled off for asymmetrical designs.

### Grid Interaction Flow

1. **Select material** from material panel (right side)
2. **Select shape** from shape palette (left side)
3. **Rotate shape** with R key (90° increments) or Q for flip
4. **Hover over grid** — ghost preview shows shape placement in material color (valid = green tint, invalid = red tint)
5. **Click to place** — shape pixels are stamped onto grid in selected material
6. **Right-click to erase** — removes pixels under cursor
7. **Switch to Slot Designator** — click on filled 2×2 areas to designate slots
8. **Stats panel updates in real-time** as you build

---

## Shape System

Shapes are geometric building blocks — the LEGO bricks of ship construction. Each shape is a template that stamps a pattern of pixels onto the grid.

### Shape Properties

```python
@dataclass
class HullShape:
    id: str                         # e.g., "rect_4x2"
    name: str                       # "Hull Plank (4×2)"
    description: str                # Flavor text
    pixel_mask: list[list[bool]]    # 2D boolean array defining the shape
    category: str                   # "basic", "intermediate", "advanced", "exotic", "faction"
    unlock_method: str              # "free", "purchase", "salvage", "quest", "faction", "mining"
    unlock_cost: int                # Credits (if purchase); 0 if other method
    unlock_source: str              # Details: quest ID, faction ID, system ID, etc.
    discovery_flavor: str           # Text shown when unlocked: "Recovered from a derelict hull..."
```

**Shape Rotation:**
Every shape can be rotated in 90° increments and flipped horizontally. The builder stores the base mask and applies rotation/flip transforms at placement time. A 4×2 rectangle becomes a 2×4 rectangle when rotated 90°.

### Shape Catalog

#### Basic Shapes (Free — available from game start)

**Rectangles:**
| Shape | Size | Pixels | Visual |
|-------|------|--------|--------|
| Pixel | 1×1 | 1 | `#` |
| Small Bar | 2×1 | 2 | `##` |
| Bar | 3×1 | 3 | `###` |
| Long Bar | 4×1 | 4 | `####` |
| Small Square | 2×2 | 4 | `##`/`##` |
| Small Rect | 3×2 | 6 | `###`/`###` |

**Triangles:**
| Shape | Size | Pixels | Visual |
|-------|------|--------|--------|
| Small Triangle | 2×2 | 3 | `##`/`.#` |
| Medium Triangle | 3×3 | 6 | `###`/`.##`/`..#` |
| Nose Point | 3×2 | 4 | `.#.`/`###` |

These 9 basic shapes (plus their rotations = ~36 orientations) are enough to build a functional ship from the start. The starter tutorial walks the player through building a simple shuttle with just rectangles and triangles.

#### Intermediate Shapes (Purchased at shipyards — 500-2,000 CR each)

| Shape | Size | Pixels | Unlock | Cost | Visual |
|-------|------|--------|--------|------|--------|
| Medium Square | 3×3 | 9 | Purchase, any shipyard | 500 | `###`/`###`/`###` |
| Medium Rect | 4×2 | 8 | Purchase, any shipyard | 500 | `####`/`####` |
| Large Square | 4×4 | 16 | Purchase, mid+ shipyard | 1,000 | 4×4 block |
| L-Shape | 3×3 | 5 | Purchase, any shipyard | 800 | `#..`/`#..`/`###` |
| T-Shape | 3×3 | 5 | Purchase, any shipyard | 800 | `###`/`.#.`/`.#.` |
| Plus | 3×3 | 5 | Purchase | 800 | `.#.`/`###`/`.#.` |
| Large Triangle | 4×4 | 10 | Purchase, mid+ shipyard | 1,200 | `####`/`.###`/`..##`/`...#` |
| Diamond | 3×3 | 5 | Purchase | 1,000 | `.#.`/`###`/`.#.` |
| Arrow Point | 5×3 | 9 | Purchase | 1,500 | `..#..`/`.###.`/`#####` |
| Notch | 2×2 | 3 | Purchase | 500 | `##`/`#.` (corner removed) |
| Hull Plank | 6×2 | 12 | Purchase | 1,200 | `######`/`######` |
| Hull Section | 8×2 | 16 | Purchase, large+ shipyard | 2,000 | Long hull panel |

#### Advanced Shapes (Quest, Salvage, Faction unlocks)

| Shape | Size | Pixels | Unlock Method | Source | Discovery Text |
|-------|------|--------|--------------|--------|---------------|
| Swept Wing | 6×3 | ~12 | Salvage | Derelict in any dangerous system | *"A wing fragment from something fast. The alloy is still warm."* |
| Curved Bow | 5×4 | ~13 | Quest | "The Phantom's Wake" side quest | *"Schematics recovered from a ghost ship's nav computer."* |
| Reinforced Bulkhead | 4×4 | 16 (extra thick) | Mining | Deep mining at Iron Depths | *"Ore veins shaped like this don't occur naturally. Someone built down here."* |
| Stealth Wedge | 5×2 | ~7 | Quest | Crimson Reach faction quest | *"Angles designed to scatter sensor returns. Military-grade geometry."* |
| Organic Panel | 4×3 | ~9 | Quest | Science Collective research chain | *"Grown, not forged. The Collective's bio-hull prototype."* |
| Thruster Nacelle | 3×5 | ~10 | Salvage | Salvage from engine room decks | *"A thruster housing with pre-cut mounting channels. Efficient."* |
| Armored Prow | 5×5 | ~15 | Mining | Rare ore discovery (any deep vein) | *"Dense enough to take a railgun slug. Whoever designed this meant business."* |
| Cargo Rack | 6×3 | ~14 | Refining | Master a refining recipe | *"Modular container frame. Locks together like puzzle pieces."* |
| Sensor Dome | 3×3 | ~7 (circular) | Quest | Axiom Labs main quest reward | *"A hemispherical housing. Everything it sees, you see."* |
| Mega Block | 8×8 | 64 | Purchase | XL shipyards only | *"For when subtlety isn't the point."* |

#### Faction Shapes (Reputation rewards — unique visual style per faction)

| Shape | Faction | Size | Rep Required | Visual Style |
|-------|---------|------|-------------|-------------|
| Guild Prow | Commerce Guild | 4×3 | Friendly (25) | Clean, geometric, golden accent pixels |
| Union Girder | Miners' Union | 6×2 | Friendly (25) | Riveted, industrial, rust-toned highlights |
| Alliance Fin | Frontier Alliance | 3×4 | Friendly (25) | Organic curves, green-tinted edges |
| Collective Arc | Science Collective | 4×4 | Friendly (25) | Precise curves, blue energy channels |
| Guild Stern | Commerce Guild | 5×3 | Allied (50) | Elegant engine housing |
| Union Plating | Miners' Union | 4×4 | Allied (50) | Thick interlocking armor |
| Alliance Canopy | Frontier Alliance | 3×3 | Allied (50) | Bio-luminescent panel |
| Collective Ring | Science Collective | 5×5 | Allied (50) | Circular sensor array housing |

**Total Shape Count: ~40 unique shapes** (plus rotations/flips = 200+ orientations)

### Shape Discovery Integration with Mini-Games

This is where the shipyard connects to the rest of the game world:

**Salvaging → Shape Blueprints:**
When salvaging derelicts, there's a chance to discover hull fragment blueprints. The discovery chance scales with salvage skill and deck type:
- Cargo decks: Cargo-related shapes (racks, holds)
- Engine decks: Thruster shapes (nacelles, housings)
- Lab decks: Sensor shapes (domes, arrays)
- Any deck: General hull shapes (wings, panels)
- Discovery rate: ~5% per salvage run, +2% per Salvage skill level

**Mining → Material Blueprints & Rare Shapes:**
Deep mining can reveal unusual ore formations that inspire hull designs:
- Deeper layers have higher discovery chance
- Specific shapes tied to specific mining locations (Iron Depths → Reinforced Bulkhead)
- Discovery rate: ~3% per mining run in deep layers

**Refining → Efficiency Unlocks:**
Mastering refining recipes unlocks material efficiency:
- Bronze mastery: 10% discount on that material's cost per pixel
- Silver mastery: Unlock advanced material variant
- Gold mastery: Unlock a unique shape (Cargo Rack at Gold refining mastery)

**Crew Bonuses:**
- Marcus (Engineer): -10% construction cost, +5% discovery chance on salvage runs
- Priya (Navigator): Sensor shapes get +15% stat bonus when placed
- Tomas (Smuggler): Hidden compartment shapes available (concealed cargo areas)

---

## Material System

Materials determine what each pixel contributes to ship stats AND what color it renders as. Material choice is the primary way players express their defensive identity.

### Material Properties

```python
@dataclass
class HullMaterial:
    id: str                         # e.g., "standard_plate"
    name: str                       # "Standard Plate"
    description: str                # Flavor text
    color_primary: tuple[int,int,int]   # Main pixel color
    color_accent: tuple[int,int,int]    # Variation for panel lines / detail
    color_highlight: tuple[int,int,int] # Bright variation for edges
    hull_per_pixel: float           # Hull HP contributed per filled pixel
    armor_per_pixel: float          # Armor contributed (fractional; accumulates)
    shield_per_pixel: float         # Shield HP per pixel (shield materials)
    shield_regen_per_pixel: float   # Shield regen per pixel (fractional)
    evasion_per_pixel: float        # Evasion per pixel (fractional)
    weight_per_pixel: float         # Weight cost per pixel
    cost_per_pixel: int             # Credits per pixel
    special_property: str | None    # Optional special effect
    unlock_method: str              # "free", "purchase", "quest", etc.
    unlock_cost: int                # Credits if purchased
    unlock_source: str              # Quest ID, faction, system, etc.
```

### Material Catalog

#### Starter Materials (Free)

| Material | Color | Hull/px | Armor/px | Shield/px | Evasion/px | Weight/px | Cost/px | Identity |
|----------|-------|---------|----------|-----------|------------|-----------|---------|----------|
| **Light Alloy** | Silver `#B0B8C8` | 1.5 | 0 | 0 | 0.08 | 0.4 | 8 | Ghost lean |
| **Standard Plate** | Gray `#707888` | 2.5 | 0 | 0 | 0 | 0.7 | 15 | Balanced |
| **Salvage Scrap** | Rust `#886848` | 2.0 | 0.02 | 0 | 0 | 0.8 | 5 | Cheap, rough |

*Salvage Scrap is the "budget" material — cheap, functional, looks rough. Perfect for early game when credits are tight. The visual says "I built this from junk" and that's a valid aesthetic.*

#### Unlockable Materials (Purchased or earned)

| Material | Color | Hull/px | Armor/px | Shield/px | Evasion/px | Weight/px | Cost/px | Unlock | Identity |
|----------|-------|---------|----------|-----------|------------|-----------|---------|--------|----------|
| **Heavy Armor** | Bronze `#987040` | 3.0 | 0.06 | 0 | 0 | 1.2 | 25 | Purchase, 5,000 CR, industrial stations | Juggernaut |
| **Reinforced Plate** | Dark Steel `#505868` | 3.5 | 0.04 | 0 | 0 | 1.0 | 30 | Purchase, 8,000 CR, mid+ stations | Juggernaut |
| **Shield Crystal** | Cyan `#40A8D0` | 1.0 | 0 | 0.6 | 0.03 | 0.6 | 22 | Purchase, 6,000 CR, science stations | Sentinel |
| **Barrier Lattice** | Blue `#3868B0` | 0.5 | 0 | 0.8 | 0.02 | 0.7 | 28 | Purchase, 10,000 CR, diplomatic stations | Sentinel |
| **Stealth Composite** | Matte Black `#282838` | 1.0 | 0 | 0 | 0.15 | 0.3 | 20 | Crimson Reach, 8,000 CR | Ghost |
| **Phase Alloy** | Dark Violet `#383050` | 0.8 | 0 | 0 | 0.20 | 0.25 | 35 | Quest: "The Phantom's Wake" | Ghost |
| **Composite Weave** | Teal `#406068` | 2.0 | 0.02 | 0.2 | 0.05 | 0.5 | 18 | Purchase, 4,000 CR, frontier stations | Hybrid |

#### Advanced Materials (Late-game, quest/faction gated)

| Material | Color | Key Stats | Weight/px | Cost/px | Unlock |
|----------|-------|-----------|-----------|---------|--------|
| **Nano-Fiber Hull** | Silver-Blue `#90A0C0` | 3.0 hull, 0.05 armor, +auto-repair 0.5 hull/turn per 20px | 0.8 | 40 | Union Allied (50 rep) |
| **Quantum Lattice** | Bright Cyan `#50C0E0` | 0.5 hull, 1.0 shield, 0.05 regen | 0.6 | 45 | Collective Allied (50 rep) |
| **Ablative Plating** | Orange-Brown `#C08840` | 4.0 hull, 0.08 armor, reflects 5% damage | 1.5 | 50 | Guild Allied (50 rep) |
| **Bio-Hull** | Green `#408848` | 2.0 hull, regenerates 1 hull/turn per 30px | 0.5 | 35 | Alliance Allied (50 rep) |
| **Void Glass** | Deep Purple `#201830` | 0.3 hull, 0.25 evasion, transparent (semi-invisible in combat) | 0.15 | 55 | Quest: "The Collector's Debt" |
| **Crimson Steel** | Blood Red `#802020` | 3.5 hull, 0.05 armor, +5% weapon damage per 50px | 1.1 | 45 | Crimson Reach black market |

**Total: 14 materials** (3 starter + 7 mid-game + 4 late-game)

### How Materials Translate to Stats

Stats are summed across all filled pixels, then rounded:

```python
total_hull = sum(pixel.material.hull_per_pixel for pixel in filled_pixels)
total_armor = int(sum(pixel.material.armor_per_pixel for pixel in filled_pixels))
total_shields = sum(pixel.material.shield_per_pixel for pixel in filled_pixels)
total_shield_regen = int(sum(pixel.material.shield_regen_per_pixel for pixel in filled_pixels))
raw_evasion = sum(pixel.material.evasion_per_pixel for pixel in filled_pixels)
total_weight = sum(pixel.material.weight_per_pixel for pixel in filled_pixels)
```

**Example — Medium Ghost Build (32×32, ~400 filled pixels):**
- 300 pixels Stealth Composite: 300 hull, 45 evasion, 90 weight
- 60 pixels Light Alloy: 90 hull, 4.8 evasion, 24 weight
- 40 pixels Shield Crystal: 40 hull + 24 shields + 1.2 regen, 24 weight
- **Totals**: 430 hull, 24 shields, ~50 evasion, 138/140 weight (98% — tight!)
- Weight modifier at 98%: -20% evasion, -10% speed → effective evasion ~40
- This is a glass cannon Ghost build: high evasion, low HP, minimal shields

**Example — Medium Juggernaut Build (32×32, ~500 filled pixels):**
- 350 pixels Heavy Armor: 1050 hull, 21 armor, 420 weight... OVER LIMIT
- Can't fill 350 pixels with Heavy Armor on a Medium frame (weight 140 max)
- Realistic: 100 px Heavy Armor (300 hull, 6 armor, 120 weight) + 100 px Standard (250 hull, 70 weight) = 190 weight... still over
- Even more realistic: 80 px Reinforced Plate (280 hull, 3 armor, 80 weight) + 120 px Light Alloy (180 hull, 48 weight) = 128/140 weight
- **Totals**: 460 hull, 3 armor, ~10 evasion, 128/140 weight (91%)
- This is a tank: high hull, some armor, low evasion, heavily committed to durability

The weight system naturally prevents absurd stat stacking while allowing clear identity expression.

---

## Slot System

After building the hull shape, the player designates **equipment slots** — locations on the ship where modules (weapons, shields, engines, utilities) are installed. Slots are the bridge between the hull you DREW and the equipment you USE.

### Slot Types

| Slot Type | Color Marker | Size | Placement Rule | What Goes Here |
|-----------|-------------|------|---------------|---------------|
| **Weapon** | Red diamond `◆` | 2×2 | Any filled 2×2 area | Weapons (lasers, missiles, etc.) |
| **Defense** | Blue circle `●` | 2×2 | Any filled 2×2 area | Shields, repair systems, armor mods |
| **Engine** | Orange triangle `▲` | 2×2 | Must be on rear 25% of ship (high Y) | Thrusters, afterburners |
| **Utility** | Green square `■` | 2×2 | Any filled 2×2 area | Cargo, sensors, crew quarters, mining |

**Core Slot** (required, exactly one):
| **Core** | Yellow star `★` | 3×3 | Must be near center of mass | Power core (energy pool + regen) |

### Slot Placement Rules

- Each slot occupies a 2×2 area (Core: 3×3) of filled pixels
- Slots cannot overlap
- Engine slots must be in the rear quarter of the ship (Y > 75% of canvas height)
- Core slot should be near the center (within 30% of center in each axis)
- All other slots can go anywhere there are filled pixels
- Slot count is limited by weight class pool (see Weight Classes table)

### Slot Costs

Designating slots costs credits — this is part of the ship's total construction cost:

| Slot Type | Cost Per Slot |
|-----------|--------------|
| Weapon | 3,000 CR |
| Defense | 2,500 CR |
| Engine | 2,000 CR |
| Utility | 1,500 CR |
| Core | Free (required) |

### Equipment in Slots

Once slots are designated, the player installs equipment modules — this is essentially the existing upgrade system, remapped:

- **Weapon slots**: Accept weapon upgrades (Laser Cannon, Plasma Caster, etc.)
- **Defense slots**: Accept defense upgrades (Shield Generator, Armor Plating, ECM Suite, etc.)
- **Engine slots**: Accept engine upgrades (Afterburner, Emergency Thrusters, Phase Drive, etc.)
- **Utility slots**: Accept utility upgrades (Cargo Bay, Mining Drill, Sensor Array, Crew Quarters, etc.)
- **Core slot**: Accepts power core modules (Standard Reactor, Fusion Core, etc.)

Equipment modules retain their existing properties: combat moves, stat bonuses, mark levels, tuning options. The Mark 1→2→3 enhancement system carries over unchanged.

### Slot Placement Strategy

Where you place slots affects gameplay and visuals:

- **Wing-tip weapons**: Thematically satisfying, creates wide firing arc visual
- **Spine-mounted shields**: Central placement protects the core
- **Stern engines**: Required by placement rules, but left/right/center positioning varies the silhouette
- **Distributed utilities**: Spreading utility slots creates a "working ship" feel
- **Clustered weapons**: All weapons on one side = dramatic broadsides

The ship's slot layout is purely the player's expression — no mechanical bonus for placement position (keeping it simple). The 2×2 slot markers are visible as subtle colored overlays on the ship sprite, giving visual information about where weapons and systems are.

---

## Cost & Economy

### Construction Cost Breakdown

Building a ship has four cost components:

```
Total Cost = Weight Class Unlock + Hull Material Cost + Slot Designation + Equipment
```

| Component | When Paid | Refundable? | Notes |
|-----------|-----------|------------|-------|
| Weight Class Unlock | One-time when upgrading | No | Major milestone purchase |
| Hull Material | Per pixel placed | 50% on removal | Running cost during construction |
| Slot Designation | Per slot placed | 50% on removal | Credits per slot type |
| Equipment | Per module installed | 50% on uninstall | Existing upgrade prices |

### Example Builds — Full Cost

**Early Game: Small Scout (24×24)**
- Weight class: Small (15,000 CR unlock)
- Hull: 200 pixels × mix of Light Alloy (8 CR) and Salvage Scrap (5 CR) ≈ 1,300 CR
- Slots: 1 weapon (3K) + 1 defense (2.5K) + 2 utility (3K) + 2 engine (4K) = 12,500 CR
- Equipment: ~15,000 CR (Tier 1 modules)
- **Total: ~44,000 CR** (comparable to current early ships at 22-28K, plus you keep the slot/equipment investment across rebuilds)

**Mid-Game: Medium Fighter (32×32)**
- Weight class: Medium (60,000 CR unlock)
- Hull: 450 pixels × Standard Plate (15 CR) ≈ 6,750 CR
- Slots: 3 weapon (9K) + 2 defense (5K) + 3 utility (4.5K) + 2 engine (4K) = 22,500 CR
- Equipment: ~60,000 CR (Tier 2 modules)
- **Total: ~149,000 CR** (comparable to current mid-game ships 85-150K)

**Late-Game: Large Warship (48×48)**
- Weight class: Large (200,000 CR)
- Hull: 800 pixels × Reinforced Plate (30 CR) ≈ 24,000 CR
- Slots: 4 weapon (12K) + 3 defense (7.5K) + 4 utility (6K) + 3 engine (6K) = 31,500 CR
- Equipment: ~150,000 CR (Tier 2-3 modules)
- **Total: ~405,000 CR** (comparable to current War Frigate 200K + full upgrades)

### Rebuild Economics

The key insight: **you don't buy a new ship. You rebuild.** When you want to change your design:

- **Removing pixels**: Refund 50% of material cost
- **Removing slots**: Refund 50% of slot cost
- **Moving pixels**: Free (erase + replace at same material = net 50% loss, BUT if you use the Move tool, it's free repositioning)
- **Changing material**: Pay the difference (new material cost - 50% old material refund)
- **Weight class carries over**: You never pay the unlock cost again

This means players can experiment and iterate on their design without losing everything. A full teardown and rebuild of the hull costs roughly 50% of original construction — meaningful but not devastating.

### Economic Integration with Game Systems

**Repair Costs Scale with Hull Value:**
- Repair cost per hull point = 0.5 × (average material cost per pixel / hull per pixel)
- Heavy Armor ships cost more to repair than Light Alloy ships
- This maintains the hull-identity economic disadvantage (Wave 3 design)

**Selling Materials:**
- Players can sell unused material stock for 30% of purchase price
- Scrapping your ship entirely refunds 40% of total material + slot cost

**Faction Discounts:**
- Allied reputation with a faction gives 15% discount on their materials
- Commerce Guild: discount on all materials purchased at guild stations
- Miners' Union: discount on Heavy Armor and Reinforced Plate
- Science Collective: discount on Shield Crystal and Quantum Lattice
- Frontier Alliance: discount on Bio-Hull and Composite Weave

---

## Builder UI Design

### Layout (Full Screen)

```
┌────────────────────────────────────────────────────────────────────────────┐
│  DRYDOCK — [Weight Class: MEDIUM 32×32]              Credits: 145,230 CR  │
├──────────┬─────────────────────────────────────┬───────────────────────────┤
│          │                                     │                           │
│  SHAPES  │          BUILDING GRID              │     MATERIALS             │
│          │                                     │                           │
│ ┌──────┐ │   ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │  ● Light Alloy    8/px   │
│ │ ▪▪   │ │   │                             │   │  ○ Standard Plate 15/px  │
│ │ ▪▪▪  │ │   │    (32×32 interactive grid   │   │  ○ Heavy Armor    25/px  │
│ │      │ │   │     with placed shapes,      │   │  ○ Shield Crystal 22/px  │
│ │ ◣    │ │   │     material colors,         │   │  ○ Stealth Comp.  20/px  │
│ │ ◣◣   │ │   │     slot markers,            │   │  ○ [LOCKED] 🔒          │
│ │      │ │   │     ghost preview)           │   │  ○ [LOCKED] 🔒          │
│ │ ▪▪▪▪ │ │   │                             │   │                           │
│ │ ▪▪   │ │   │                             │   │  ─────────────────────── │
│ │      │ │   │                             │   │  SLOT DESIGNATOR         │
│ │[More]│ │   │                             │   │  ◆ Weapon  (1/3)  3000   │
│ └──────┘ │   │                             │   │  ● Defense (0/2)  2500   │
│          │   │                             │   │  ▲ Engine  (2/2)  2000   │
│  TOOLS   │   └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │  ■ Utility (1/3)  1500   │
│ [S][P]   │                                     │  ★ Core    (1/1)  free   │
│ [E][M]   │                                     │                           │
│ [F][V]   │                                     │                           │
│ [X]Mirror│                                     │                           │
├──────────┴─────────────────────────────────────┴───────────────────────────┤
│  SHIP STATS                                                                │
│  Hull: 460  Shields: 24  Armor: 3  Evasion: 18  Speed: 12  Accuracy: 68  │
│  Energy: 8/3  Cargo: 80  Fuel: 150  Crew: 2                              │
│                                                                            │
│  Weight: ████████████████░░░░ 128/140 (91%) HEAVY                         │
│  Power:  ████████████░░░░░░░░ 6/10 (60%)                                 │
│  Cost:   72,450 CR total  |  Budget remaining: 72,780 CR                  │
│                                                                            │
│  [PRESETS ▼]  [UNDO] [REDO]  [CLEAR]  [TEST VIEW]  [CONFIRM BUILD]       │
│  [← BACK TO STATION]                                                      │
└────────────────────────────────────────────────────────────────────────────┘
```

### Panel Descriptions

**Shape Palette (Left):**
- Scrollable grid of available shapes
- Shapes shown at 2× magnification with material color preview
- Category filter tabs: Basic / Intermediate / Advanced / Exotic / Faction
- Locked shapes show lock icon with unlock hint on hover
- Selected shape has bright border highlight

**Building Grid (Center):**
- The main canvas, displayed at maximum zoom that fits the screen area
- Grid lines: 1px subtle lines (toggleable with G key)
- Filled pixels render in their material color
- Slot markers overlay as colored icons (weapon=red ◆, defense=blue ●, etc.)
- Ghost preview: shape follows cursor with transparency, snaps to grid
- Invalid placement: ghost turns red with "NO FIT" or "OVER WEIGHT" label
- Zoom controls: scroll wheel or +/- keys (for Large/XL canvases)
- Pan: middle-click drag or arrow keys (when zoomed in)

**Material Panel (Right):**
- Vertical list of available materials
- Each shows: color swatch, name, cost/pixel, key stats
- Selected material has bright border
- Locked materials show lock icon with unlock requirement
- Material stats tooltip on hover: full breakdown of hull/armor/shield/evasion/weight per pixel

**Slot Designator (Right, below materials):**
- Shows each slot type with current count / maximum
- Click a slot type to enter placement mode
- Slot being placed follows cursor as colored overlay
- Shows cost per slot next to each type

**Stats Panel (Bottom):**
- Real-time ship stats computed from current build
- Weight bar with color coding: green (0-60%), yellow (60-80%), orange (80-95%), red (95-100%)
- Power bar with similar coding
- Running cost total
- Warning text if build is invalid ("Need a Core slot", "Over weight limit", etc.)

**Tool Bar (Bottom left or left panel):**
- Tool buttons with hotkeys
- Mirror mode toggle (highlighted when active)
- Undo/Redo (Ctrl+Z / Ctrl+Y)

### Builder Sub-Screens

**Frame Selection (accessed via BACK TO STATION → DRYDOCK → "Change Weight Class"):**
- Shows all 5 weight classes with canvas preview
- Current class highlighted
- Upgrade cost shown for next class
- Downgrade option (smaller canvas, but what about existing build? → warning dialog)

**Equipment Screen (accessed via clicking a placed slot):**
- Opens a modal overlay showing available equipment for that slot type
- Similar to existing shipyard upgrade shop, but filtered to the slot type
- Install, uninstall, enhance (Mk1-3) from this screen
- Close returns to builder grid

**Preset Browser (accessed via PRESETS button):**
- Shows saved builds (system presets + player presets)
- Preview: small render of the ship + stat summary
- "LOAD" replaces current build (with confirmation)
- "SAVE CURRENT" saves current build as named preset (max 10 player presets)
- System presets include all 24 legacy ship configurations

**Test View (accessed via TEST VIEW button):**
- Shows the ship sprite at combat scale against a space background
- Can rotate the ship, see it at different zoom levels
- Shows the sprite with slot overlays ON and OFF
- "Back to Builder" returns to grid
- Purely cosmetic preview — no stat simulation

---

## Auto-Detailing — Making Player Ships Look Good

Raw pixel placement by non-artists could look rough. The rendering pipeline adds automatic visual polish so that ANY build looks like a cohesive ship.

### Rendering Pipeline

```
Player's raw pixel grid
        ↓
1. Material Color Fill (base pixel colors from material type)
        ↓
2. Panel Line Generation (darker lines between adjacent different-material pixels)
        ↓
3. Edge Highlight (1px lighter border on top/left edges of the ship silhouette)
        ↓
4. Edge Outline (1px dark border around entire ship silhouette for readability)
        ↓
5. Slot Indicators (subtle colored overlay on slot locations — faint, not distracting)
        ↓
6. Material Texture (per-material pixel-level detail: rivets on Heavy Armor, smooth
   gradient on Shield Crystal, matte on Stealth, organic veins on Bio-Hull)
        ↓
7. Engine Glow (animated pixel at engine slot locations — 2-frame warm color pulse)
        ↓
Final composite surface (cached, regenerated only on build change)
```

### Auto-Detail Examples

**Panel Lines:**
Where two different materials meet, a 1px darker line is drawn. This creates natural "panel" boundaries that make the ship look assembled rather than painted. Same-material adjacent pixels don't get panel lines.

**Edge Highlight:**
The top and left edges of the silhouette get a 1px lighter pixel. This creates a subtle 3D-ish lighting effect that's standard in pixel art (light from top-left).

**Material Textures (applied at native resolution):**
- **Heavy Armor**: Every 3rd pixel in a row is 10% darker (rivet pattern)
- **Shield Crystal**: Subtle 2-pixel gradient from bright center to darker edge
- **Stealth Composite**: Flat matte (no texture — intentionally featureless)
- **Salvage Scrap**: Random 15% of pixels are slightly different hue (patchy, worn look)
- **Bio-Hull**: Faint organic vein lines (1px connecting paths through the material)
- **Standard Plate**: Clean, uniform (the "default" professional look)

**Engine Glow:**
Pixels at engine slot locations get a 2-frame animated glow:
- Frame 1: Warm orange center pixel + yellow-white surround
- Frame 2: Slightly dimmer, shifted by 1 pixel outward

This creates a subtle engine "throb" visible on the galaxy map and in combat idle.

### Why This Works

Even if a player just stamps three rectangles together, the auto-detailing pipeline turns it into something that reads as "a ship":
- Outline gives it a clear silhouette
- Panel lines give it structure
- Material colors give it identity (blue = shields, dark = stealth, bronze = armor)
- Engine glow gives it life

A skilled player who carefully designs their shape with triangles and swept wings gets an even better result — the system rewards care but doesn't punish simplicity.

---

## Ship Rendering Integration

### Where the Ship Appears

| Context | Scale | Animated? | Notes |
|---------|-------|-----------|-------|
| Builder Grid | Native × (600/canvas_size) | No | Full detail, interactive |
| Combat (player) | Native × res_scale(2) | Yes (idle bob, engine glow) | With VFX overlays (shields, damage) |
| Combat (shield bubble) | Based on sprite radius | Yes | Shield renderer uses sprite bounds |
| Galaxy Map | Native × res_scale(1) | Yes (engine glow) | Rotated to travel direction |
| Cockpit HUD | Native × 1 (thumbnail) | No | Small icon in HUD ship panel |
| Station Hub | Native × res_scale(1.5) | Yes (engine glow) | Docked ship display |
| Save/Load | Native × 1 (thumbnail) | No | Slot preview |
| Test View | Native × res_scale(3) | Yes | Large preview in builder |

### Composite Surface Caching

```python
class ShipComposite:
    """Cached rendered surface for a player's ship build."""

    def __init__(self, build: ShipBuild):
        self._build = build
        self._base_surface: pygame.Surface | None = None  # Native resolution
        self._scaled_cache: dict[int, pygame.Surface] = {}  # scale → surface
        self._engine_frame: int = 0  # Animation frame (0 or 1)
        self._dirty: bool = True  # Rebuild needed

    def invalidate(self) -> None:
        """Mark as needing rebuild (called when build changes)."""
        self._dirty = True
        self._scaled_cache.clear()

    def get_surface(self, scale: int = 1) -> pygame.Surface:
        """Get the rendered ship at the given scale."""
        if self._dirty:
            self._rebuild()
        if scale not in self._scaled_cache:
            self._scaled_cache[scale] = pygame.transform.scale(
                self._base_surface,
                (self._base_surface.get_width() * scale,
                 self._base_surface.get_height() * scale),
            )
        return self._scaled_cache[scale]

    def update(self, dt: float) -> None:
        """Advance engine glow animation."""
        ...
```

### Replacing Stock Sprites

The player's ship currently uses `SpriteManager.get_ship_sprite(ship_type_id)`. After the overhaul:

```python
# Before:
sprite = sprite_mgr.get_ship_sprite(player.ship.ship_type.id, scale=res_scale(2))

# After:
sprite = player.ship.composite.get_surface(scale=res_scale(2))
```

Enemy ships continue using stock sprites — this system is player-only. (Future: enemies could also be grid-built for visual variety.)

---

## Game System Integration

### Combat

**Stat source changes:**
```python
# Before: stats from ShipType + UpgradeManager bonuses
hull = ship.ship_type.combat_hull + upgrade_manager.get_bonus("hull_bonus")

# After: stats computed from build
hull = ship.build.computed_stats.hull  # Sum of all material hull + equipment bonuses
```

`build_player_combat_state()` reads from `ship.computed_stats` instead of `ship.ship_type`. The `PlayerCombatState` dataclass is unchanged — it still receives hull, shields, energy, evasion, accuracy, etc.

**Combat moves** come from equipment installed in weapon/defense slots (existing upgrade combat_move system).

**Ship size in combat:**
The weight class directly maps to visual size. Tiny ships are small targets (32px at combat scale). XL ships dominate the arena (128px). This creates dramatic visual contrast when a tiny shuttle faces a pirate heavy — and when the player upgrades to Large, they SEE the power difference.

### Galaxy Map

Ship renders at `res_scale(1)` with rotation. Larger weight classes show as larger sprites on the map — visible progression.

### Repair

Repair cost per hull point scales with the average material cost of the build:
```python
repair_cost_per_hp = max(1, int(total_material_cost / total_hull_hp * 0.4))
```
Expensive materials = expensive repairs. This naturally creates the hull-identity economic trade-off from Wave 3.

### Salvage Mini-Game → Shape Discovery

When completing a salvage run:
```python
if salvage_quality >= "good" and random.random() < discovery_chance:
    shape = pick_random_undiscovered_shape(deck_type)
    player.unlock_shape(shape.id)
    show_discovery_popup(shape)  # "Hull Fragment Recovered: Swept Wing"
```

Discovery chance: 5% base + 2% per Salvage skill level + 1% per deck quality level. On a maxed-out salvage build, that's ~15% per run — frequent enough to be exciting, rare enough to feel special.

### Mining Mini-Game → Material/Shape Discovery

Deep mining (layer 4-5) can reveal rare ore formations:
```python
if depth_layer >= 4 and random.random() < ore_discovery_chance:
    unlock = pick_mining_discovery(system_id)  # Material or shape
    player.unlock_material_or_shape(unlock.id)
    show_discovery_popup(unlock)
```

Specific discoveries are tied to specific systems:
- Iron Depths: Reinforced Bulkhead shape, Heavy Armor material
- Axiom Labs: Sensor Dome shape
- Breakstone: Union Girder shape

### Refining → Material Mastery

Reaching mastery tiers on refining recipes unlocks:
- Bronze: 10% cost reduction on a specific material
- Silver: Unlock an advanced material variant
- Gold: Unlock a unique shape (Cargo Rack, Refinery Module housing)

### Crew Integration

Crew members provide builder bonuses (passive, always-on when recruited):
- **Marcus (Engineer)**: -10% construction costs, +5% salvage shape discovery
- **Priya (Navigator)**: Sensor equipment in slots gets +15% stat bonus
- **Elena (Medic)**: Bio-Hull material heals 50% faster
- **Tomas (Smuggler)**: Unlocks "Hidden Compartment" shape (concealed cargo area — invisible to scans)

### Faction Reputation

Faction reputation gates materials and shapes:
- Friendly (25 rep): Unlock faction's basic shape + 10% material discount
- Allied (50 rep): Unlock faction's advanced shape + advanced material

### Quest Rewards

Key quest chains reward builder content:
- "The Phantom's Wake": Phase Alloy material + Curved Bow shape
- "The Collector's Debt": Void Glass material
- Campaign bosses: Each drops a unique shape on defeat
- Act One completion: Unlocks XL weight class regardless of credits

---

## Acquisition Atlas — Where Everything Comes From

The core principle: **every system, every activity, and every faction should contribute something unique to the builder.** The player who only trades at Nexus Prime has a different set of parts than the player who mines at Iron Depths. Your ship tells the story of where you've been.

### Drydock Capability by System

Not all shipyards are created equal. Each system's drydock has a **specialty** — a category of shapes and materials it stocks that others don't. Basic shapes and starter materials are available everywhere, but the interesting stuff requires visiting the right port.

| System | Drydock Specialty | Shapes Sold | Materials Sold | Equipment Focus | Weight Classes |
|--------|------------------|-------------|----------------|-----------------|---------------|
| **Nexus Prime** | Commerce & Luxury | Medium Rect, Arrow Point, Hull Section | Standard Plate, Composite Weave | Full catalog (all tiers, marked up 10%) | Up to Large |
| **Stellaris Port** | Premium Engineering | Large Square, Diamond, Hull Plank | Reinforced Plate, Barrier Lattice | Luxury equipment, diplomatic modules | Up to Large |
| **Verdant** | Agricultural & Civilian | Small shapes only (low-tech) | Light Alloy, Standard Plate | Cargo modules, fuel tanks, basic weapons | Up to Small |
| **Haven's Rest** | Frontier Improvisation | Notch, L-Shape, T-Shape | Salvage Scrap, Composite Weave | Budget equipment, emergency thrusters | Up to Medium |
| **Forgeworks** | Industrial & Heavy Armor | Large Triangle, Hull Section, Mega Block (L+) | Heavy Armor, Reinforced Plate | Heavy weapons, armor modules, mining drills | Up to XL |
| **Breakstone** | Mining & Rugged | Medium Square, Hull Plank | Heavy Armor, Salvage Scrap | Mining equipment, hull repair modules | Up to Medium |
| **Axiom Labs** | Science & Sensors | Diamond, Plus, Medium Rect | Shield Crystal, Barrier Lattice | Sensor arrays, shield generators, ECM | Up to Large |
| **Nova Research** | Experimental Tech | Arrow Point, Large Square | Shield Crystal, Quantum Lattice (Allied) | Advanced shields, experimental weapons | Up to Large |
| **Crimson Reach** | Stealth & Black Market | Notch, L-Shape | Stealth Composite, Crimson Steel (black market) | Evasion modules, smuggling rigs, ghost plating | Up to Medium |
| **Iron Depths** | Deep Industrial | Hull Plank, Large Triangle | Heavy Armor, Standard Plate | Mining drills, hull repair, heavy armor mods | Up to Medium |
| **The Fulcrum** | *No drydock* | — | — | Emergency repairs only (20 CR/HP) | — |

**Key design rule**: No single system sells everything. A Juggernaut pilot needs Forgeworks or Iron Depths for Heavy Armor. A Sentinel needs Axiom Labs or Nova Research for Shield Crystal. A Ghost needs Crimson Reach for Stealth Composite. This creates TRAVEL motivation — you go to specific places because they have what you need for YOUR build.

**No-reputation gate, location-gated content**: Simply docking at a system gives you access to its drydock catalog. You don't need faction reputation to buy standard shapes and materials at a system's shipyard. Reputation gates only apply to faction-exclusive content (see Faction Reputation section below). The player who scrapes together fuel money to reach Crimson Reach can immediately buy Stealth Composite — they earned it by getting there.

### Equipment Module Distribution by Faction

Equipment modules (weapons, defenses, utilities installed in slots) are distributed across factions. Each faction's systems stock equipment that supports certain playstyles.

#### Commerce Guild Systems (Nexus Prime, Stellaris Port)
*"Everything has a price, and we set it."*

| Category | Module | Tier | Price | System | Notes |
|----------|--------|------|-------|--------|-------|
| Weapon | Laser Cannon | 2 | 10,000 | Both | Reliable Kinetic mainstay |
| Weapon | Dual Laser Array | 2 | 14,000 | Both | Heavy Kinetic, high energy |
| Weapon | Railgun | 3 | 35,000 | Stellaris only | Ultimate single-target |
| Weapon | Trade Beam | 2 | 12,000 | Nexus only | Moderate damage, +10% credit loot on kill |
| Defense | Reinforced Shield Gen | 2 | 5,000 | Both | Standard shield module |
| Defense | Insurance Protocol | 2 | 9,000 | Nexus only | On death: retain 50% cargo value as credits |
| Defense | Luxury Shield Array | 3 | 25,000 | Stellaris only | +60 shields, +6 regen. Top-tier |
| Utility | Expanded Cargo Bay | 2 | 4,000 | Both | Guild space staple |
| Utility | Pressurized Hold | 3 | 10,000 | Both | Large cargo capacity |
| Utility | Trade Computer | 2 | 8,000 | Nexus only | Shows price differentials on galaxy map |
| Utility | Diplomatic Transponder | 3 | 18,000 | Stellaris only | Reduces faction rep loss from smuggling |

#### Miners' Union Systems (Forgeworks, Breakstone, Iron Depths)
*"Built to last, built to work."*

| Category | Module | Tier | Price | System | Notes |
|----------|--------|------|-------|--------|-------|
| Weapon | Mining Laser Retrofit | 1 | 3,000 | All Union | Starter dual-use weapon |
| Weapon | Missile Launcher | 2 | 18,000 | Forgeworks/Breakstone | Heavy Kinetic burst |
| Weapon | Plasma Caster | 2 | 12,000 | Forgeworks only | Burn DoT |
| Weapon | Plasma Torpedo | 3 | 30,000 | Iron Depths only | Devastating + Burn |
| Weapon | Flak Battery | 2 | 16,000 | Breakstone only | AoE Kinetic |
| Defense | Reactive Armor Module | 2 | 7,000 | All Union | Hull identity staple |
| Defense | Nano-Repair Module | 2 | 6,000 | Forgeworks only | In-combat hull restore |
| Defense | Hull Integrity Matrix | 3 | 20,000 | Iron Depths only | +100 hull, +3 armor, Fortify ability |
| Defense | Field Repair Rig | 2 | 10,000 | Breakstone only | -25% station repair costs |
| Utility | Mining Drill | 1 | 3,000 | All Union | Mining capability |
| Utility | Advanced Mining Laser | 2 | 10,000 | Breakstone/Iron Depths | Enhanced mining yield |
| Utility | Tractor Beam | 2 | 8,000 | Forgeworks only | +20% post-combat loot |
| Utility | Compact Refinery | 2 | 15,000 | Forgeworks only | On-board basic refining |

#### Science Collective Systems (Axiom Labs, Nova Research)
*"Knowledge is the ultimate armor."*

| Category | Module | Tier | Price | System | Notes |
|----------|--------|------|-------|--------|-------|
| Weapon | Ion Disruptor | 2 | 15,000 | Both | Anti-shield specialist |
| Weapon | Ion Lance | 3 | 28,000 | Nova only | Heavy shield drain |
| Weapon | Cryo Projector | 2 | 13,000 | Axiom only | Chill stacks → Freeze |
| Weapon | Cryo Cannon | 3 | 26,000 | Axiom only | Multi-Chill, devastating vs. evasion |
| Weapon | Voltaic Emitter | 2 | 14,000 | Both | Suppress enemy damage |
| Weapon | Voltaic Array | 3 | 27,000 | Nova only | AoE Suppress |
| Defense | Shield Harmonics Unit | 3 | 10,000 | Axiom only | +5 regen, +20 shields |
| Defense | Quantum Shield Matrix | 3 | 15,000 | Nova only | Phase Shields ability |
| Defense | Aegis Projector | 3 | 25,000 | Axiom only | Full shield restore ultimate |
| Defense | Ion-Hardened Coils | 2 | 5,500 | Both | Counter to Ion weapons |
| Defense | ECM Suite | 2 | 5,000 | Both | Evasion + Chaff ability |
| Utility | Advanced Sensors | 2 | 5,000 | Both | Accuracy + scan bonus |
| Utility | Quantum Sensor Suite | 3 | 12,000 | Nova only | +12 accuracy |
| Utility | Repair Drone Bay | 3 | 18,000 | Axiom only | Auto-repair 5 hull/turn |
| Utility | Shield Drone Bay | 3 | 18,000 | Nova only | Auto-restore 5 shields/turn |

#### Frontier Alliance Systems (Haven's Rest, Verdant)
*"Make do. Make it work. Make it yours."*

| Category | Module | Tier | Price | System | Notes |
|----------|--------|------|-------|--------|-------|
| Weapon | Pulse Emitter | 1 | 500 | Both | Starter weapon |
| Weapon | Point Defense Array | 2 | 8,000 | Haven's Rest | Auto-fire on incoming |
| Weapon | Salvaged Cannon | 1 | 2,500 | Haven's Rest | Cheap mid-range Kinetic |
| Defense | Basic Shield Gen | 1 | 1,500 | Both | Starter shield |
| Defense | Emergency Thrusters | 1 | 2,000 | Both | +15% flee |
| Defense | Lightweight Frame Mod | 1 | 1,500 | Haven's Rest | +3 evasion, -10 hull |
| Utility | Cargo Pod | 1 | 1,000 | Both | Starter cargo |
| Utility | Fuel Cell | 1 | 500 | Both | Starter fuel |
| Utility | Nav Computer | 2 | 4,000 | Verdant only | -3 fuel per jump |
| Utility | Salvage Arm | 1 | 3,000 | Haven's Rest | Salvage capability |
| Utility | Smuggling Rig | 2 | 6,000 | Haven's Rest | Contraband concealment |

*Frontier systems are where new players gear up. Low prices, Tier 1-2 range. The breadth isn't here — but neither is the cost.*

#### Crimson Reach (Independent / Black Market)
*"We don't ask where it came from."*

| Category | Module | Tier | Price | System | Notes |
|----------|--------|------|-------|--------|-------|
| Weapon | Voltaic Emitter | 2 | 14,000 | Standard | Suppress enemy output |
| Weapon | Cryo Projector | 2 | 13,000 | Standard | Freeze evasion targets |
| Weapon | Stolen Railgun | 3 | 28,000 | Black market | Cheaper than Stellaris |
| Weapon | Disruptor Mines | 2 | 11,000 | Black market | AoE damage + energy drain |
| Defense | Phase Shift Drive | 3 | 16,000 | Standard | 100% evasion for 1 turn |
| Defense | Ghost Plating | 3 | 14,000 | Black market | +10 evasion, Vanish ability |
| Defense | Quantum Blink Drive | 3 | 18,000 | Black market | Dodge all + guaranteed next hit |
| Utility | Hidden Compartment | 2 | 6,000 | Standard | Concealed cargo |
| Utility | Smuggling Rig | 2 | 6,000 | Standard | Contraband concealment |
| Utility | Threat Analyzer | 2 | 12,000 | Black market | Counterstrike bonus increased |
| Utility | Bounty Scanner | 2 | 9,000 | Black market | Shows enemy credit rewards |

*Crimson Reach is the Ghost identity's home base. Stealth materials, evasion equipment, black market specials. Coming here is a statement about your playstyle.*

### Mini-Game Discovery — Deep Integration

Every mini-game feeds the builder. This creates a virtuous loop: you build your ship to be better at activities that unlock more parts for your ship.

#### Salvaging → Shape Blueprints + Rare Material Variants

**Discovery Mechanics:**
- Base discovery chance: 5% per completed salvage run
- +2% per Salvage skill level (max +10% at level 5)
- +1% per deck quality tier (Good/Excellent)
- +3% at dangerous system salvage sites (Crimson Reach, Forgeworks)
- Marcus crew bonus: +5% additional

**Discovery Table by Deck Type:**

| Deck Type | Shape Discoveries | Material Discoveries |
|-----------|------------------|---------------------|
| **Cargo Deck** | Cargo Rack (6×3), Hull Plank (6×2) | Salvage Scrap (free restock) |
| **Engine Deck** | Thruster Nacelle (3×5), Swept Wing (6×3) | Composite Weave (if not yet unlocked) |
| **Lab Deck** | Sensor Dome (3×3), Organic Panel (4×3) | Shield Crystal (if not yet unlocked) |
| **Bridge Deck** | Curved Bow (5×4), Stealth Wedge (5×2) | Phase Alloy (rare, 2% within the discovery roll) |
| **Any Deck** | Basic shapes (duplicates give 200 CR scrap value) | Salvage Scrap (free restock) |

**Salvage-Exclusive Content (ONLY found by salvaging):**
- Swept Wing shape — sleek aerodynamic form, the salvager's signature
- Thruster Nacelle shape — efficient engine housing, pre-cut mounting channels
- Derelict Plating material variant — Salvage Scrap with +0.03 armor/px ("battle-tested junk")

#### Mining → Material Discovery + Rare Shapes

**Discovery Mechanics:**
- Only triggers at depth layer 3+ (Deep Veins and below)
- Base discovery chance: 3% per mining field
- +2% per Mining skill level
- +5% at Abyssal Vein depth (layer 5)
- System-specific discoveries

**Discovery Table by System:**

| System | Shape Discoveries | Material Discoveries |
|--------|------------------|---------------------|
| **Breakstone** | Union Girder (bypasses rep gate) | Heavy Armor (if not yet purchased) |
| **Iron Depths** | Reinforced Bulkhead (4×4), Armored Prow (5×5) | Nano-Fiber Hull (rare, bypasses rep gate) |

**Mining-Exclusive Content (ONLY found by mining):**
- Reinforced Bulkhead shape — dense, thick, the miner's signature hull piece
- Armored Prow shape — massive battering ram bow
- Crystal Vein material variant — Shield Crystal with +0.02 regen/px ("naturally resonant ore")

*Mining is the Juggernaut's discovery path. Heavy shapes, heavy materials, deep investment in the hull identity.*

#### Refining → Material Mastery + Unique Shapes

**Mastery rewards by recipe category:**

| Recipe Category | Bronze Mastery | Silver Mastery | Gold Mastery |
|----------------|---------------|----------------|-------------|
| **Metal Refining** | -10% Heavy Armor cost/px | Reinforced Plate unlock (if not purchased) | **Armored Hull Plank** shape (8×2, extra thick) |
| **Crystal Processing** | -10% Shield Crystal cost/px | Barrier Lattice unlock (if not purchased) | **Resonant Panel** shape (3×3, built-in +shield regen) |
| **Chemical Synthesis** | -10% Composite Weave cost/px | Stealth Composite unlock (if not purchased) | **Cargo Rack** shape (6×3) |
| **Advanced Recipes** | -10% on all Tier 3 materials | Unlock corresponding advanced material | **Prototype Module** shape (4×4, +5% to any installed module stat) |

**Refining-Exclusive Content:**
- Armored Hull Plank shape (Gold Metal mastery)
- Resonant Panel shape (Gold Crystal mastery)
- Prototype Module shape (Gold Advanced mastery)
- Permanent material cost discounts (Bronze mastery, stacking with faction discounts)

*Refining is the long game. Mastery takes time, but the rewards compound — cheaper builds and exclusive shapes that no shop sells.*

#### Combat → Trophy Salvage

**New mechanic: notable enemies drop usable ship parts.**

| Enemy Type | Drop Chance | Possible Drops |
|-----------|------------|---------------|
| Regular enemies | 3% | Basic shape (duplicate = 100-500 CR scrap) |
| Elite enemies | 8% | Intermediate shapes |
| Boss enemies | **100%** (first kill) | Unique trophy (see below) |

**Boss Trophy Drops:**

| Boss | Trophy | Type | Description |
|------|--------|------|-------------|
| The Corsair King | **Pirate Cutlass Fin** (5×2, angled) | Shape | *"Torn from the King's own hull. Still has scorch marks."* |
| Guild Arbiter | **Corporate Bulwark** (4×4, built-in +5% DR) | Shape | *"Guild-stamped armor. Legal ownership is... complicated."* |
| The Iron Maw | **Forgeborn Steel** (3.5 hull, 0.07 armor, 1.3 wt) | Material | *"Metal from the Maw's heart. It doesn't bend."* |
| Ledger Phantom | **Phantom Shroud** (5×3, built-in +8 evasion) | Shape | *"The Phantom's cloak. Still shimmers at the edges."* |
| The Collector | **Collector's Crest** (3×3, +10% credit loot) | Shape | *"They collected everything. Now you've collected them."* |
| Void Leviathan | **Void Chitin** (2.5 hull, 0.3 shield, 0.1 evasion) | Material | *"Peeled from something that shouldn't exist."* |
| Rogue AI Vessel | **AI Logic Core** (2×2, +8 accuracy, +3 energy) | Shape | *"It still hums. Don't think about it too hard."* |

*Boss trophies are the rarest and most powerful builder content in the game. Each one is a statement piece — visible on the ship, mechanically impactful, and earned through the hardest fights.*

#### Ground Exploration → Rare Finds

Ground exploration missions can uncover builder blueprints in the field:

| Ground Map | Discovery | Chance | Notes |
|-----------|-----------|--------|-------|
| Forgeworks Industrial Complex | Union Plating shape | 8% per run | Found in the restricted forge area |
| Axiom Labs Research Wing | Collective Ring shape | 8% per run | Found in sealed laboratory |
| Crimson Reach Underbelly | Stealth Wedge shape | 8% per run | Found in smuggler's cache |
| Iron Depths Caverns | Armored Prow shape | 8% per run | Found in ancient mining ruin |
| The Fulcrum Assembly | **Experimental Hull Fragment** (6×4, +3 energy) | 100% | Campaign Act One reward |

#### Trading → Economic Unlocks

Profitable trading unlocks builder content through **Trade Milestones**:

| Milestone | Requirement | Reward |
|-----------|------------|--------|
| First Profit | Any profitable sale | Basic shapes tutorial reminder |
| Merchant | 10,000 CR cumulative profit | Trade Computer available at Nexus |
| Trader | 50,000 CR cumulative profit | Medium weight class 20% discount |
| Magnate | 100,000 CR cumulative profit | Hull Section shape (8×2) free |
| Tycoon | 250,000 CR cumulative profit | Cargo Rack shape free |
| Baron | 500,000 CR cumulative profit | Large weight class 15% discount |
| Mogul | 1,000,000 CR cumulative profit | **Merchant's Keel** shape (6×4, +15 cargo when placed) |

*Trading doesn't give combat-focused rewards. It gives economic advantages — discounts, cargo shapes, efficiency. The trader's ship isn't the meanest; it's the most profitable.*

### Faction Reputation — Full Unlock Paths

Each faction has a tiered unlock path. Reputation gates the exclusive content; location access (just docking there) gates the standard catalog.

#### Commerce Guild (Nexus Prime, Stellaris Port)

| Rep Level | Threshold | Unlocks |
|-----------|-----------|---------|
| Neutral | 0 | Standard catalog at Guild drydocks |
| Acquainted | 10 | 5% drydock discount |
| Friendly | 25 | **Guild Prow** shape (4×3, golden accent) + Trade Computer equipment + 10% drydock discount |
| Trusted | 40 | **Ablative Plating** material available for purchase + Diplomatic Transponder + 15% discount |
| Allied | 50 | **Guild Stern** shape (5×3, elegant engine) + Ablative Plating at -20% + Luxury Shield Array + Guild Exclusive preset |

#### Miners' Union (Forgeworks, Breakstone, Iron Depths)

| Rep Level | Threshold | Unlocks |
|-----------|-----------|---------|
| Neutral | 0 | Standard catalog at Union drydocks |
| Acquainted | 10 | 5% repair discount at Union stations |
| Friendly | 25 | **Union Girder** shape (6×2, riveted) + Hull Integrity Matrix + 10% repair discount |
| Trusted | 40 | **Nano-Fiber Hull** material available + Compact Refinery + 15% repair discount |
| Allied | 50 | **Union Plating** shape (4×4, interlocking) + Nano-Fiber at -20% + XL weight class 25% discount at Forgeworks |

#### Science Collective (Axiom Labs, Nova Research)

| Rep Level | Threshold | Unlocks |
|-----------|-----------|---------|
| Neutral | 0 | Standard catalog at Collective drydocks |
| Acquainted | 10 | 5% discount on science equipment |
| Friendly | 25 | **Collective Arc** shape (4×4, precise curves) + Quantum Shield Matrix + 10% equipment discount |
| Trusted | 40 | **Quantum Lattice** material available + Shield Drone Bay + free Quantum Sensors upgrade |
| Allied | 50 | **Collective Ring** shape (5×5, sensor array) + Quantum Lattice at -20% + Aegis Projector + Sensor Dome shape free |

#### Frontier Alliance (Haven's Rest, Verdant)

| Rep Level | Threshold | Unlocks |
|-----------|-----------|---------|
| Neutral | 0 | Standard catalog at Alliance drydocks |
| Acquainted | 10 | 5% fuel discount at Alliance stations |
| Friendly | 25 | **Alliance Fin** shape (3×4, organic curves) + Salvage Suite + 10% fuel + construction discount |
| Trusted | 40 | **Bio-Hull** material available + Phase Shift Drive at Haven's Rest + 15% all discounts |
| Allied | 50 | **Alliance Canopy** shape (3×3, bioluminescent) + Bio-Hull at -20% + Ghost Plating at Haven's Rest (no black market needed) + Hidden Compartment shape free |

#### Crimson Reach (No formal faction — progression through activities)

| Unlock Tier | Requirement | Content |
|-------------|------------|---------|
| Docked | Arrive at Crimson Reach | Stealth Composite material, standard evasion equipment |
| Black Market | Criminal heat > 0 OR smuggling quest | Black market equipment catalog (Ghost Plating, Stolen Railgun, etc.) |
| Smuggler's Trust | Complete 3 smuggling runs | **Crimson Steel** material available |
| Wrecker's Guild | Complete "Wrecker's Initiation" quest | Disruptor Mines, Quantum Blink Drive, Threat Analyzer |
| Inner Circle | Complete "The Wrecker's Debt" chain | **Void Glass** material, unique Phantom Shroud preset |

### Crew Integration — Builder Bonuses

| Crew Member | Role | Passive Builder Bonus | Discovery Bonus | Recruitment Reward |
|-------------|------|----------------------|-----------------|-------------------|
| **Marcus** | Engineer | -10% construction cost at all drydocks | +5% salvage shape discovery | Repair Drone Bay 20% cheaper |
| **Priya** | Navigator | Sensor equipment: +15% stat bonus | +3% discovery chance in ANY activity | Nav Computer unlocked free |
| **Elena** | Medic | Bio-Hull regen +50% effectiveness | +2% ground exploration discovery | Crew Quarters 20% cheaper |
| **Tomas** | Smuggler | Hidden Compartment shape unlocked | +5% mining material discovery | Smuggling Rig free, Crimson Reach black market (no heat needed) |

**Crew Quest Rewards (personal quest chain completions):**

| Quest Chain | Reward Shape | Effect |
|------------|-------------|--------|
| Marcus's Engineering Legacy | **Marcus's Masterwork** (4×4) | +auto-repair 3 hull/turn when placed |
| Priya's Star Chart | **Astrogation Module** (2×2) | -2 fuel per jump when placed |
| Elena's Research | **Medical Bay Module** (3×2) | Crew abilities cost -1 energy in combat |
| Tomas's Past | **Tomas's Getaway Kit** (3×3) | +20% flee chance when placed, stealth design |

*Crew shapes are among the most powerful in the game — built-in stat bonuses that no other shape has. But they require completing personal quest chains, real investment in your crew relationships.*

### Quest & Event Rewards — Complete Map

| Source | Reward | Type |
|--------|--------|------|
| Tutorial completion | Basic shapes palette + Standard Cockpit + starter kit | Shapes + Equipment |
| "The Phantom's Wake" side quest | Phase Alloy material + Curved Bow shape | Material + Shape |
| "The Collector's Debt" side quest | Void Glass material + Collector's Crest trophy | Material + Shape |
| "Ghost Ship" side quest | Stealth Wedge shape + Ghost Plating equipment | Shape + Equipment |
| "The Bounty Board" side quest | Pirate Cutlass Fin trophy shape | Shape |
| "Wrecker's Initiation" (Crimson Reach) | Black market equipment access | Equipment |
| "The Wrecker's Debt" (Crimson Reach chain) | Void Glass material + Phantom preset | Material + Preset |
| Campaign: Corsair King defeated | Pirate Cutlass Fin + Forgeborn Steel | Shape + Material |
| Campaign: Guild Arbiter defeated | Corporate Bulwark trophy shape | Shape |
| Campaign: The Iron Maw defeated | Forgeborn Steel trophy material | Material |
| Campaign: Ledger Phantom defeated | Phantom Shroud trophy shape | Shape |
| Campaign: Act One complete | XL weight class unlock + Experimental Hull Fragment | Weight Class + Shape |
| Marcus crew quest complete | Marcus's Masterwork shape | Shape |
| Priya crew quest complete | Astrogation Module shape | Shape |
| Elena crew quest complete | Medical Bay Module shape | Shape |
| Tomas crew quest complete | Tomas's Getaway Kit shape | Shape |
| 62 achievements (completionist) | **Aurelia's Mark** (3×3, golden glow, +1 all stats) | Shape |

### Skill Tree Bonuses for the Builder

| Skill | Tree | Builder Effect |
|-------|------|---------------|
| Hull Reinforcement | Combat | +5% hull per level from hull materials |
| Shield Mastery | Combat | +10% shield effectiveness from shield materials |
| Evasive Maneuvers | Combat | +5% evasion per level from evasion materials |
| Armor Expertise (Wave 3) | Combat | +1 armor per level (added to material armor sum) |
| Shield Regen (Wave 3) | Combat | +2 shield regen/turn per level |
| Afterburner (Wave 3) | Combat | +5 evasion per level |
| Field Repairs (Wave 3) | Combat | -15% repair costs per level |
| Salvage Expert | Exploration | +3% salvage shape discovery per level |
| Deep Mining | Exploration | +2% mining material discovery per level |
| Refining Mastery | Exploration | Faster mastery progression |
| Negotiation | Social | -5% drydock construction cost per level |
| Black Market Access | Social | Crimson Reach black market (no heat required) |

### Content Totals (Final)

| Content Type | Count | Acquisition Breakdown |
|-------------|-------|----------------------|
| **Shapes** | **~55** | Free (9) + Purchase (12) + Salvage-exclusive (3) + Mining-exclusive (3) + Refining-exclusive (3) + Quest (9) + Faction rep (8) + Boss trophy (7) + Crew quest (4) + Trading milestone (1) + Ground exploration (4) + Completionist (1) |
| **Materials** | **16** | Free (3) + Location-gated purchase (7) + Faction Allied (4) + Boss trophy (2) + Quest (2) + Mini-game variant (3) |
| **Equipment Modules** | **~85** | Distributed across 10 systems by faction, some faction-rep gated, some quest-gated, some black-market only |
| **Weight Classes** | **5** | Free (Tiny) + Credits (Small/Medium/Large/XL) + Campaign alternate path (XL) |
| **Presets** | **24+ system + 10 player** | Legacy ships + faction exclusives + player-saved |

**Total unique builder content: ~160+ items**, each with a specific source that ties it to a place, an activity, a faction, or a story moment in the game world.

---

## Tutorial Design

The builder is the most complex UI in the game. It needs excellent onboarding.

### First Visit Tutorial (Guided Build)

When the player first enters the Drydock, a step-by-step tutorial walks them through building a simple ship:

**Step 1: "Welcome to the Drydock"**
> *"This is where you build your ship. Every pixel you place becomes part of your ship's hull. Let's build something."*
> Highlights: grid area

**Step 2: "Choose a Shape"**
> *"Shapes are your building blocks. Select the Small Square from the palette."*
> Highlights: shape palette, guides player to click Small Square

**Step 3: "Place It"**
> *"Click on the grid to place the shape. Try putting it near the center."*
> Highlights: grid center area

**Step 4: "Materials Matter"**
> *"Each material gives different stats. Standard Plate is balanced. Heavy Armor is tough but heavy. Try placing a triangle at the front — that's your ship's bow."*
> Highlights: material panel, guides through selecting material + placing triangle

**Step 5: "Mirror Mode"**
> *"Press X to enable Mirror Mode. Now whatever you place on the left appears on the right too. Most ships are symmetrical."*
> Guides player to toggle mirror mode and place wing shapes

**Step 6: "Add an Engine"**
> *"Place some shapes at the back of your ship for engines. Ships need propulsion!"*
> Highlights rear of grid

**Step 7: "Designate Slots"**
> *"Now designate where your equipment goes. Click the Weapon slot button, then click on your ship to place it."*
> Guides through placing 1 weapon, 1 engine, 1 utility, and core slot

**Step 8: "Install Equipment"**
> *"Click on your weapon slot to install a weapon. Pick the Pulse Emitter — it's free with your starter kit."*
> Opens equipment modal

**Step 9: "Check Your Stats"**
> *"The stats panel shows your ship's capabilities. Watch how adding or removing pieces changes the numbers."*
> Highlights stats panel

**Step 10: "Confirm Your Build"**
> *"When you're happy, hit Confirm Build. You can always come back and rebuild later."*
> Highlights confirm button

### Contextual Tooltips

Every UI element has a tooltip that appears on hover (after 0.5s):
- Shape: name, pixel count, unlock source
- Material: full stat breakdown per pixel
- Slot: type, cost, what equipment fits
- Stats: what contributes to this stat (e.g., hover Hull → "Hull Plates: 460, Equipment: +20")
- Weight bar: "X/Y weight. Current modifier: HEAVY (-10% evasion, -5% speed)"
- Power bar: "X/Y power. Surplus: Z (or Deficit: Z — warning!)"

### Quick Start Options

For players who don't want to build from scratch:
- **"Load Preset"** button prominent in the builder
- Presets include all 24 legacy ships + "Starter Shuttle" + themed templates
- "Auto-Fill" button: fills empty structural cells with the cheapest material (for players who designed the shape but don't want to material-pick every pixel)

---

## Defensive Identity Integration (Wave 3 Synergy)

The ship builder is the perfect vehicle for the defensive identity system. Instead of buying a "hull ship" or "shield ship," you BUILD your identity pixel by pixel.

### Identity Expression Through Materials

| Identity | Primary Material | Secondary Material | Visual Color Profile | Ship Looks Like |
|----------|-----------------|-------------------|--------------------|--------------------|
| Juggernaut (Hull) | Heavy Armor, Reinforced Plate | Standard Plate | Bronze/dark steel | Thick, angular, heavy |
| Sentinel (Shield) | Shield Crystal, Barrier Lattice | Standard Plate | Blue/cyan | Sleek, crystalline panels |
| Ghost (Evasion) | Stealth Composite, Phase Alloy | Light Alloy | Dark/matte/violet | Thin, angular, minimal |
| Hybrid | Composite Weave | Any | Teal mixed | Varied, balanced |

### Identity Passive Triggers

From the Wave 3 design, identity passives activate at material density thresholds:

```python
# Calculate material identity
hull_material_pixels = count_pixels_with_materials(["heavy_armor", "reinforced_plate", "ablative_plating", "nano_fiber", "crimson_steel"])
shield_material_pixels = count_pixels_with_materials(["shield_crystal", "barrier_lattice", "quantum_lattice"])
evasion_material_pixels = count_pixels_with_materials(["stealth_composite", "phase_alloy", "void_glass", "light_alloy"])
total_filled = count_all_filled_pixels()

hull_ratio = hull_material_pixels / total_filled
shield_ratio = shield_material_pixels / total_filled
evasion_ratio = evasion_material_pixels / total_filled

# Highest ratio above threshold wins
IDENTITY_THRESHOLD = 0.35  # 35% of pixels must be one identity's materials
if hull_ratio >= IDENTITY_THRESHOLD and hull_ratio > max(shield_ratio, evasion_ratio):
    active_identity = "juggernaut"  # Unlock: Last Stand, Structural Integrity, Armor passives
elif shield_ratio >= IDENTITY_THRESHOLD and shield_ratio > max(hull_ratio, evasion_ratio):
    active_identity = "sentinel"    # Unlock: Overcharge, Shield Break recovery, Regen passives
elif evasion_ratio >= IDENTITY_THRESHOLD and evasion_ratio > max(hull_ratio, shield_ratio):
    active_identity = "ghost"       # Unlock: Counterstrike, Slippery, Light Frame passives
else:
    active_identity = None          # Hybrid — no identity passives, but no weaknesses either
```

The builder UI shows which identity is active (if any) in the stats panel with the identity name and a brief description of the passive benefits. This gives immediate feedback as the player builds: "Oh, if I replace these Light Alloy pixels with Shield Crystal, I'll cross the Sentinel threshold."

### Weight System Naturally Creates Trade-Offs

- Heavy Armor: 1.2 weight/pixel → fills weight budget fast → heavy ship → low evasion
- Shield Crystal: 0.6 weight/pixel → moderate weight → moderate evasion
- Stealth Composite: 0.3 weight/pixel → light ship → high evasion from weight bonus

You literally cannot build a Juggernaut that's also a Ghost. The weight math forbids it. This is elegant because it's not an arbitrary rule — it emerges naturally from the system.

---

## Save & Migration

### New Save Format

```json
{
  "ship": {
    "build": {
      "frame_class": "medium",
      "pixels": [
        {"x": 10, "y": 5, "material": "standard_plate"},
        {"x": 11, "y": 5, "material": "standard_plate"},
        {"x": 10, "y": 6, "material": "shield_crystal"}
      ],
      "slots": [
        {"type": "weapon", "x": 14, "y": 8, "equipment_id": "laser_cannon", "mark": 2, "tuning": "overcharged"},
        {"type": "defense", "x": 10, "y": 12, "equipment_id": "shield_gen_t2", "mark": 1, "tuning": null},
        {"type": "engine", "x": 15, "y": 28, "equipment_id": "thruster_afterburner", "mark": 1, "tuning": null},
        {"type": "core", "x": 14, "y": 14, "equipment_id": "power_core_t2", "mark": 1, "tuning": null},
        {"type": "utility", "x": 8, "y": 15, "equipment_id": "cargo_pod_t2", "mark": 1, "tuning": null}
      ],
      "preset_name": "My Fighter v3"
    },
    "current_fuel": 120,
    "current_cargo": {"iron_ore": 5},
    "current_hull": 285,
    "current_shields": 45
  },
  "unlocked_shapes": ["swept_wing", "curved_bow", "reinforced_bulkhead"],
  "unlocked_materials": ["heavy_armor", "shield_crystal", "stealth_composite"],
  "player_presets": [
    {"name": "My Fighter v2", "build": { ... }},
    {"name": "Trade Config", "build": { ... }}
  ]
}
```

**Optimization**: The pixel array can be compressed using run-length encoding for save file size:
```json
"pixels_rle": [
  {"material": "standard_plate", "runs": [[5,10,15,10], [6,10,16,10]]},
  {"material": "shield_crystal", "runs": [[12,8,14,12]]}
]
```
This compresses a 500-pixel ship from 500 entries to ~20-30 entries.

### Old Save Migration

When loading a save with the old format (`ship_type_id` + `installed` upgrades):
1. Look up `ship_type_id` → find matching preset in `data/ships/presets.json`
2. Load preset as the ship build
3. Map old `installed` upgrades → equipment in corresponding slot types
4. Set unlocked shapes/materials to a reasonable mid-game default set
5. Save in new format on next save

Player sees their ship auto-converted to a preset build that matches their old ship's stats. They can then customize it at any shipyard.

---

## Implementation Roadmap

> This roadmap is broken into sub-phases that can be implemented independently and tested in isolation. Each sub-phase has a clear goal, specific files to create/modify, acceptance criteria, and a checkpoint before proceeding. Follow the project conventions in `CLAUDE.md` and `spacegame/views/CLAUDE.md` throughout.

### Dependency Graph

```
A1 (Data Models)
 ├── A2 (Ship Model Transition) ──── G (System Integration & Migration)
 │    └── A3 (Presets & Save Migration)
 ├── B1 (Builder View: Grid & Core Tools)
 │    ├── B2 (Builder View: Advanced Tools)
 │    └── B3 (Builder View: Slots & Equipment)
 └── C (Visual Composite Rendering) ── replaces stock sprites everywhere

D1 (Content Catalog: Shapes & Materials) ── feeds B1, C
D2 (Content Distribution & Discovery) ── depends on A3, B3, mini-game views

E (Builder Polish) ── depends on B1+B2+B3
F (Tutorial & Onboarding) ── depends on B3, E
```

**Recommended build order:** A1 → A2 → A3 → D1 → B1 → C → B2 → B3 → D2 → E → F → G

---

### Phase A1: Data Models & Core Logic

**Goal:** Pure data structures and computation engine. No UI, no rendering, no pygame imports. Everything in this phase is testable with `pytest` alone.

**Effort:** HIGH | **Dependencies:** None | **Estimated scope:** ~600-800 lines of model code + ~400 lines of tests

**New files to create:**

| File | Purpose |
|------|---------|
| `spacegame/models/ship_build.py` | All builder data models and computation logic |
| `data/ships/shapes.json` | Shape catalog (start with 9 basic shapes only — full catalog in D1) |
| `data/ships/materials.json` | Material catalog (start with 3 starter materials only — full catalog in D1) |
| `tests/test_models/test_ship_build.py` | Comprehensive tests |

**Implementation details for `spacegame/models/ship_build.py`:**

```python
# === Data Models (all @dataclass, following project conventions) ===

@dataclass
class HullShape:
    """A geometric building block template."""
    id: str
    name: str
    description: str
    pixel_mask: list[list[bool]]    # 2D array, True = filled pixel
    category: str                   # "basic", "intermediate", "advanced", "exotic", "faction"
    unlock_method: str              # "free", "purchase", "salvage", "quest", "faction", "mining"
    unlock_cost: int
    unlock_source: str
    discovery_flavor: str

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def pixel_count(self) -> int: ...
    def rotated(self, times: int = 1) -> "HullShape": ...  # Returns new shape with rotated mask
    def flipped(self) -> "HullShape": ...                   # Returns horizontally flipped shape
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "HullShape": ...


@dataclass
class HullMaterial:
    """A material type that determines pixel stats and color."""
    id: str
    name: str
    description: str
    color_primary: tuple[int, int, int]
    color_accent: tuple[int, int, int]
    color_highlight: tuple[int, int, int]
    hull_per_pixel: float
    armor_per_pixel: float
    shield_per_pixel: float
    shield_regen_per_pixel: float
    evasion_per_pixel: float
    weight_per_pixel: float
    cost_per_pixel: int
    special_property: str | None
    unlock_method: str
    unlock_cost: int
    unlock_source: str
    # NOTE: No pygame imports. Colors are plain tuples. Rendering uses them later.


@dataclass
class PlacedPixel:
    """A single filled pixel on the ship grid."""
    x: int
    y: int
    material_id: str

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "PlacedPixel": ...


@dataclass
class DesignatedSlot:
    """An equipment slot placed on the ship grid."""
    slot_type: str              # "weapon", "defense", "engine", "utility", "core"
    x: int                      # Top-left X of 2×2 area (3×3 for core)
    y: int                      # Top-left Y
    equipment_id: str | None    # Installed equipment module ID (None = empty slot)
    mark: int = 1               # Enhancement level (1-3)
    tuning: str | None = None   # Tuning specialization

    @property
    def size(self) -> int: ...  # 2 for standard slots, 3 for core
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "DesignatedSlot": ...


WEIGHT_CLASSES: dict[str, dict] = {
    "tiny":   {"canvas": 16, "max_weight": 40,  "max_slots": 4,  "unlock_cost": 0},
    "small":  {"canvas": 24, "max_weight": 80,  "max_slots": 7,  "unlock_cost": 15000},
    "medium": {"canvas": 32, "max_weight": 140, "max_slots": 10, "unlock_cost": 60000},
    "large":  {"canvas": 48, "max_weight": 240, "max_slots": 14, "unlock_cost": 200000},
    "xlarge": {"canvas": 64, "max_weight": 400, "max_slots": 18, "unlock_cost": 500000},
}

SLOT_POOLS: dict[str, dict[str, int]] = {
    "tiny":   {"weapon": 1, "defense": 1, "utility": 1, "engine": 1},
    "small":  {"weapon": 2, "defense": 1, "utility": 2, "engine": 2},
    # ... etc per Weight Classes table
}


@dataclass
class ShipBuild:
    """Complete ship configuration — the central data structure."""
    weight_class: str                   # "tiny", "small", "medium", "large", "xlarge"
    pixels: list[PlacedPixel]           # All filled pixels
    slots: list[DesignatedSlot]         # All designated equipment slots
    preset_name: str | None = None      # Custom name if saved

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> "ShipBuild": ...


# === Computation Engine ===

class ShipGridManager:
    """Handles placement validation and grid state queries."""

    def __init__(self, weight_class: str): ...

    def can_place_shape(self, shape: HullShape, x: int, y: int, material: HullMaterial,
                        existing_pixels: list[PlacedPixel]) -> tuple[bool, str]: ...
    def can_place_slot(self, slot_type: str, x: int, y: int,
                       pixels: list[PlacedPixel], slots: list[DesignatedSlot]) -> tuple[bool, str]: ...
    def get_pixels_at(self, x: int, y: int, width: int, height: int,
                      pixels: list[PlacedPixel]) -> list[PlacedPixel]: ...
    def is_area_filled(self, x: int, y: int, size: int, pixels: list[PlacedPixel]) -> bool: ...
    def get_canvas_size(self) -> int: ...


class ShipStatsComputer:
    """Derives all ship stats from a ShipBuild + material/equipment data."""

    @staticmethod
    def compute(build: ShipBuild, materials: dict[str, HullMaterial],
                equipment: dict[str, "ShipUpgrade"]) -> "ComputedShipStats": ...
    # Returns a ComputedShipStats dataclass with all combat/travel/economy stats


@dataclass
class ComputedShipStats:
    """All derived stats for a ship build. Replaces ShipType combat stats."""
    hull: int
    armor: int
    shields: int
    shield_regen: int
    evasion: int
    speed: int
    accuracy: int
    energy_pool: int
    energy_regen: int
    cargo_capacity: int
    fuel_capacity: int
    crew_slots: int
    weight_current: float
    weight_max: int
    weight_ratio: float
    power_current: int
    power_max: int
    defensive_identity: str | None  # "juggernaut", "sentinel", "ghost", or None
    combat_moves: list              # CombatMove objects from equipment
    flee_bonus: int
    special_abilities: list[str]
```

**Key implementation rules:**
- Follow `tuple[bool, str]` return convention for failable operations (can_place_shape, can_place_slot)
- All dataclasses have `to_dict()` / `from_dict()` serialization
- No pygame imports in this file — purely data and math
- Weight modifiers: use the table from the Weight System section (0-40% = ULTRALIGHT +15% evasion, etc.)
- Identity detection: 35% material pixel threshold, highest wins, see Defensive Identity Integration section
- Power budget: sum equipment power_draw vs frame base_power + power_core output

**Tests to write (`tests/test_models/test_ship_build.py`):**
1. Shape rotation produces correct pixel mask (90°, 180°, 270°)
2. Shape flip produces correct horizontal mirror
3. `can_place_shape` — succeeds on empty grid
4. `can_place_shape` — fails on overlap with existing pixels
5. `can_place_shape` — fails when shape extends beyond canvas
6. `can_place_shape` — fails when weight would exceed max
7. `can_place_slot` — succeeds on filled 2×2 area
8. `can_place_slot` — fails when underlying pixels not filled
9. `can_place_slot` — fails when overlapping existing slot
10. `can_place_slot` — fails when slot pool exhausted
11. `can_place_slot` — engine slot fails when not in rear 25% of canvas
12. Stat computation: hull = sum of material hull_per_pixel across all pixels
13. Stat computation: weight modifiers apply correctly at each threshold
14. Stat computation: identity detection triggers at 35% threshold
15. Stat computation: identity detection picks highest ratio when multiple cross threshold
16. Stat computation: power budget sums correctly
17. Serialization round-trip: `ShipBuild.to_dict()` → `ShipBuild.from_dict()` produces identical build
18. Edge case: empty build (no pixels) produces zero stats
19. Edge case: build at exactly 100% weight

**Checkpoint before proceeding:**
- [ ] `pytest tests/test_models/test_ship_build.py` — all pass
- [ ] Can create a ShipBuild programmatically, compute stats, serialize/deserialize
- [ ] Weight modifiers produce expected evasion/speed changes
- [ ] Identity detection correctly identifies Juggernaut/Sentinel/Ghost builds

---

### Phase A2: Ship Model Transition

**Goal:** Wire ShipBuild into the existing Ship model so the game can use build-derived stats alongside the old ShipType system. Both paths work simultaneously during transition.

**Effort:** MEDIUM | **Dependencies:** A1 | **Estimated scope:** ~200 lines modified across 3 files

**Files to modify:**

| File | Changes |
|------|---------|
| `spacegame/models/ship.py` | Add optional `ShipBuild` reference; stat properties check build first, fall back to ShipType |
| `spacegame/models/combat.py` | Update `build_player_combat_state()` to read from build when available |
| `spacegame/data_loader.py` | Add `load_shapes()`, `load_materials()` to DataLoader |

**Implementation approach for `ship.py`:**

```python
# Add to Ship dataclass:
_build: Optional[ShipBuild] = field(default=None, repr=False)
_computed_stats: Optional[ComputedShipStats] = field(default=None, repr=False)

def set_build(self, build: ShipBuild) -> None:
    """Attach a ShipBuild and recompute stats."""
    self._build = build
    self._recompute_stats()

def _recompute_stats(self) -> None:
    """Derive ComputedShipStats from the build. Called when build changes."""
    if self._build:
        materials = get_data_loader().materials  # dict[str, HullMaterial]
        equipment = get_data_loader().upgrades   # dict[str, ShipUpgrade]
        self._computed_stats = ShipStatsComputer.compute(self._build, materials, equipment)

@property
def computed_stats(self) -> Optional[ComputedShipStats]:
    return self._computed_stats

# Modify existing properties to check build first:
@property
def max_cargo(self) -> int:
    if self._computed_stats:
        return self._computed_stats.cargo_capacity + self._crew_bonus("cargo_bonus")
    # Fall back to old ShipType path (backward compat during transition)
    return self.ship_type.cargo_capacity + self._upgrade_bonus("cargo_bonus") + self._crew_bonus("cargo_bonus")
```

**Implementation approach for `combat.py` `build_player_combat_state()`:**

```python
# Add at top of function:
if ship.computed_stats:
    cs = ship.computed_stats
    return PlayerCombatState(
        hull=ship.current_hull, max_hull=cs.hull,
        shields=ship.current_shields, max_shields=cs.shields,
        energy=cs.energy_pool, max_energy=cs.energy_pool,
        energy_regen=cs.energy_regen,
        speed=cs.speed, evasion=cs.evasion, accuracy=cs.accuracy,
        equipment_moves=cs.combat_moves,
        crew_moves=crew_moves,  # unchanged
        active_effects=[], cooldowns={},
        flee_bonus=cs.flee_bonus,
    )
# ... existing ShipType path below (unchanged, used for old saves until migrated)
```

**Tests to write:**
1. Ship with ShipBuild returns computed stats from build, not ShipType
2. Ship without ShipBuild returns stats from ShipType (backward compat)
3. `build_player_combat_state()` with build produces correct PlayerCombatState
4. DataLoader loads shapes and materials from JSON

**Checkpoint:**
- [ ] Existing game still works (no build set → old path)
- [ ] Programmatically setting a build on a Ship produces correct combat stats
- [ ] `pytest` — ALL existing 5,076 tests still pass (no regressions)

---

### Phase A3: Presets & Save/Load Migration

**Goal:** Create preset builds for all 24 legacy ships and implement save format migration so old saves auto-convert.

**Effort:** MEDIUM | **Dependencies:** A1, A2 | **Estimated scope:** ~300 lines + preset JSON

**New files:**

| File | Purpose |
|------|---------|
| `data/ships/presets.json` | 24 preset builds (one per legacy ShipType) |
| `spacegame/models/ship_presets.py` | Preset loading, legacy ShipType → ShipBuild conversion |

**Files to modify:**

| File | Changes |
|------|---------|
| `spacegame/save_manager.py` | Detect old format, convert to new; serialize ShipBuild |
| `spacegame/data_loader.py` | Load presets |
| `spacegame/models/player.py` | Add `unlocked_shapes`, `unlocked_materials`, `weight_class`, `player_presets` |

**Preset creation strategy:**
Each legacy ship type must produce a preset build that matches its stats within 10%. Approach:
1. Map ship's hull → appropriate material mix (e.g., Patrol Cutter's 110 hull → ~44 Standard Plate pixels)
2. Map ship's shields → Shield Crystal pixels
3. Map ship's evasion → either Light Alloy pixels or weight ratio targeting
4. Place shapes to form a recognizable silhouette matching the ship's identity
5. Designate slots matching the ship's weapon/defense/utility slot counts
6. Verify: `ComputedShipStats` from preset ≈ old `ShipType` stats (within 10%)

Write a test that loads every preset and asserts stat parity with the legacy ShipType.

**Save migration in `save_manager.py`:**

```python
def _deserialize_ship(self, data: dict) -> Ship:
    if "build" in data:
        # New format — load ShipBuild directly
        build = ShipBuild.from_dict(data["build"])
        ship = Ship(ship_type=self._get_fallback_ship_type(build), ...)
        ship.set_build(build)
    else:
        # OLD FORMAT — migrate
        ship_type = data_loader.get_ship_type(data["ship_type_id"])
        ship = Ship(ship_type=ship_type, ...)
        # Convert to build using preset
        preset = data_loader.get_preset_for_ship_type(data["ship_type_id"])
        if preset:
            build = self._apply_upgrades_to_preset(preset, data.get("upgrades", {}))
            ship.set_build(build)
    return ship
```

**Player model additions:**
```python
# Add to Player dataclass:
unlocked_shapes: set[str] = field(default_factory=lambda: {"pixel", "small_bar", ...})  # 9 basic shapes
unlocked_materials: set[str] = field(default_factory=lambda: {"light_alloy", "standard_plate", "salvage_scrap"})
unlocked_weight_classes: set[str] = field(default_factory=lambda: {"tiny"})
player_presets: list[dict] = field(default_factory=list)  # Max 10 custom presets
trade_profit_total: int = 0  # For trading milestones
```

**Tests:**
1. Every preset produces stats within 10% of its legacy ShipType
2. Old save format loads and auto-converts to new format with build
3. New save format round-trips correctly
4. Player unlocked shapes/materials serialize correctly
5. Preset loading from JSON works

**Checkpoint:**
- [ ] All 24 presets created and verified for stat parity
- [ ] Loading an old save file → ship has a ShipBuild → stats match old system
- [ ] Saving and reloading produces identical state
- [ ] `pytest` — all tests pass including new migration tests

---

### Phase B1: Builder View — Grid & Core Tools

**Goal:** A minimal but functional ship builder. Player can open it, see the grid, place shapes, choose materials, see stats update, and confirm a build. This is the MVP builder.

**Effort:** HIGH | **Dependencies:** A1, D1 (needs shapes and materials in JSON) | **Estimated scope:** ~800-1000 lines

**New files:**

| File | Purpose |
|------|---------|
| `spacegame/views/ship_builder_view.py` | The builder view (BaseView subclass) |

**Files to modify:**

| File | Changes |
|------|---------|
| `spacegame/config.py` | Add `GameState.SHIP_BUILDER` |
| `spacegame/engine/game.py` | Register builder view, wire SHIPYARD → BUILDER transition |
| `spacegame/views/shipyard_view.py` | Add "DRYDOCK" button/tab that transitions to builder |

**View lifecycle (follow `spacegame/views/CLAUDE.md` patterns exactly):**

```python
class ShipBuilderView(BaseView):
    def __init__(self, ui_manager, player, system, data_loader): ...
    def on_enter(self) -> None: ...   # _create_ui(), load current build onto grid
    def on_exit(self) -> None: ...    # _destroy_ui()
    def _create_ui(self) -> None: ... # pygame_gui buttons: CONFIRM, CLEAR, UNDO, BACK
    def _destroy_ui(self) -> None: ...
    def handle_event(self, event) -> None: ...  # Grid clicks, tool switching, keyboard shortcuts
    def update(self, dt: float) -> None: ...    # Cursor preview, stat recomputation
    def render(self, screen) -> None: ...       # Grid, shapes, panels, stats
```

**B1 scope — tools to implement in this phase:**
- Shape Stamp tool (primary — select shape, click to place)
- Eraser tool (right-click or E key)
- Material selector panel (right side, clickable list)
- Shape palette panel (left side, scrollable, category filtered)

**B1 scope — panels to implement:**
- Grid rendering (center, scaled to fit screen area, with subtle grid lines)
- Stats panel (bottom, real-time: hull/shields/evasion/speed/weight/power)
- Weight bar (color-coded: green → yellow → orange → red)
- Power bar (similar)
- Current cost display

**B1 scope — controls:**
- CONFIRM BUILD button (grayed until build is valid)
- CLEAR ALL button (with confirmation dialog)
- BACK button (returns to station hub, with "unsaved changes" warning if modified)
- R key: rotate selected shape
- Q key: flip selected shape

**Rendering approach:**
The grid is drawn manually (not pygame_gui) using `pygame.draw.rect()` for cells and `screen.blit()` for shape previews. The stats panel uses `FontCache` with existing font constants. The shape palette and material list can use either manual rendering or pygame_gui elements — follow whichever approach the existing shipyard_view uses for consistency.

**Builder grid rendering pseudocode:**
```python
def _render_grid(self, screen):
    canvas_size = WEIGHT_CLASSES[self.build.weight_class]["canvas"]
    # Scale grid to fit the available screen area
    cell_size = min(grid_area_w, grid_area_h) // canvas_size
    grid_origin_x = grid_area_x + (grid_area_w - canvas_size * cell_size) // 2
    grid_origin_y = grid_area_y + (grid_area_h - canvas_size * cell_size) // 2

    # Draw background (dark)
    # Draw grid lines (subtle, 1px, toggleable)
    # Draw filled pixels (material color)
    # Draw slot indicators (colored overlay on designated slots)
    # Draw ghost preview (if holding a shape)
```

**Tests:**
View tests are limited (pygame dependency), but test:
1. Build validation logic (required core, weight limit, slot count)
2. Shape placement through ShipGridManager integration
3. Stats recompute correctly when pixels added/removed

**Checkpoint:**
- [ ] Player can open the builder from the shipyard
- [ ] Grid renders for each weight class (try Tiny and Medium)
- [ ] Player can select a shape, select a material, click to place
- [ ] Stats panel shows correct values and updates in real-time
- [ ] Player can erase pixels
- [ ] CONFIRM BUILD saves the build to the player's ship
- [ ] Player's ship uses build-derived stats in combat (verify with a test fight)
- [ ] BACK returns to station hub

---

### Phase B2: Builder View — Advanced Tools

**Goal:** Make the builder feel good to use. These are quality-of-life tools that aren't required for functionality but transform the experience.

**Effort:** MEDIUM | **Dependencies:** B1

**All changes in `spacegame/views/ship_builder_view.py`:**

1. **Mirror Mode** (X key toggle): Auto-duplicate placements across the vertical center line. This is the single most impactful UX feature — implement it first.
2. **Pencil tool** (P key): Place individual 1×1 pixels. For detail work.
3. **Material Brush** (M key): Click filled pixels to repaint them with current material. No shape needed.
4. **Fill tool** (F key): Flood-fill an enclosed area with current material. Use standard 4-connected flood fill, bounded by canvas edges and filled pixels.
5. **Ghost preview**: Translucent shape follows cursor before placement. Green tint = valid, red tint = invalid. This makes placement feel precise and predictable.
6. **Rotation preview**: Shape in ghost rotates when R is pressed, before placement.
7. **Undo/Redo** (Ctrl+Z / Ctrl+Y): Store up to 20 grid states. Each placement or erasure pushes state.
8. **Select tool** (V key): Click+drag to select a rectangular region. Then move (drag), delete (Delete key), or copy (Ctrl+C → click to paste).
9. **Zoom/Pan**: For Large (48×48) and XL (64×64) canvases, scroll wheel zooms, middle-click drags to pan. Small/Medium/Tiny fit on screen without zoom.
10. **"Auto-Fill" button**: Fill all empty cells within the ship's convex hull with the cheapest available material. For players who designed the silhouette but want quick stat filling.

**Checkpoint:**
- [ ] Mirror mode produces symmetrical ships efficiently
- [ ] Ghost preview makes placement feel predictable
- [ ] Undo/redo works across tool switches
- [ ] Large canvas is navigable with zoom/pan

---

### Phase B3: Builder View — Slots & Equipment

**Goal:** Slot designation and equipment installation. This connects the visual hull to the mechanical equipment system.

**Effort:** MEDIUM | **Dependencies:** B1

**Implementation in `ship_builder_view.py`:**

1. **Slot Designator tool** (D key): Enter slot mode. A sub-panel shows slot types with remaining counts (e.g., "Weapon: 1/3"). Click a slot type, then click on the grid to place it on a filled 2×2 area. The slot overlay (colored marker) appears immediately. Right-click an existing slot to remove it (50% cost refund).

2. **Equipment install modal**: Click an already-placed slot to open an equipment browser filtered to that slot type. This should reuse the card-list rendering pattern from the existing `shipyard_view.py` (scrollable list, card per item, stats, buy button). Install deducts credits; uninstall refunds 50%.

3. **Core slot requirement**: Build validation enforces exactly 1 core slot. Show warning text if missing.

4. **Engine slot placement rule**: Engine slots must be in the rear 25% of the canvas (y > 75% of canvas height). Show the valid zone with a subtle tint when engine slot is selected.

5. **Power budget display**: Show power bar in stats panel. If power demand > supply, the bar turns red and affected modules show a "DEPOWERED" label. Depowered weapon modules can't be used in combat.

6. **Slot cost display**: Each slot shows its designation cost (weapon: 3000 CR, etc.). Running total visible.

**Equipment modal pattern:**
```python
# When player clicks a placed slot:
self._equipment_modal_open = True
self._equipment_slot = clicked_slot
self._equipment_list = self._get_available_equipment(clicked_slot.slot_type, self.system)
# Render as overlay on top of grid, similar to existing detail panels
# Filter by current system's catalog (from Acquisition Atlas — implemented in D2)
```

**Checkpoint:**
- [ ] Player can designate slots of each type
- [ ] Slot placement validates (filled area, slot pool, engine zone)
- [ ] Player can install equipment into slots
- [ ] Equipment stats contribute to ship stats
- [ ] Combat uses equipment moves from slots
- [ ] Core slot requirement enforced

---

### Phase C: Visual Composite Rendering

**Goal:** The player's ship build renders as a polished composite sprite everywhere in the game. This is what makes the whole system VISIBLE.

**Effort:** MEDIUM | **Dependencies:** A1 (needs build data), B1 (needs builds to exist)

**New files:**

| File | Purpose |
|------|---------|
| `spacegame/engine/ship_composite.py` | ShipComposite renderer + auto-detailing pipeline |

**Files to modify:**

| File | Change | Search for |
|------|--------|-----------|
| `spacegame/views/combat_view.py` | Use composite for player ship | `get_ship_sprite`, `get_ship_animated`, `_ship_sprite_cache` |
| `spacegame/views/galaxy_map_view.py` | Use composite for player ship | `_player_ship_anim`, `get_ship_animated` |
| `spacegame/views/cockpit_hud.py` | Use composite thumbnail | Any ship sprite reference |
| `spacegame/views/station_hub_view.py` | Show composite in docked display | Ship sprite references |
| `spacegame/views/save_load_view.py` | Composite thumbnail in slot preview | Ship sprite references |

**Auto-detailing pipeline implementation (`ship_composite.py`):**

```python
class ShipComposite:
    """Renders a ShipBuild into a pygame Surface with automatic visual polish."""

    def __init__(self, build: ShipBuild, materials: dict[str, HullMaterial]):
        self._build = build
        self._materials = materials
        self._base_surface: pygame.Surface | None = None
        self._scaled_cache: dict[int, pygame.Surface] = {}
        self._dirty = True

    def invalidate(self) -> None:
        """Mark for rebuild (call when build changes)."""
        self._dirty = True
        self._scaled_cache.clear()

    def get_surface(self, scale: int = 1) -> pygame.Surface:
        """Get rendered composite at given scale factor."""
        if self._dirty:
            self._rebuild()
        if scale not in self._scaled_cache:
            scaled = pygame.transform.scale(
                self._base_surface,
                (self._base_surface.get_width() * scale,
                 self._base_surface.get_height() * scale),
            )
            self._scaled_cache[scale] = scaled
        return self._scaled_cache[scale]

    def _rebuild(self) -> None:
        """Execute the full rendering pipeline."""
        canvas = WEIGHT_CLASSES[self._build.weight_class]["canvas"]
        surf = pygame.Surface((canvas, canvas), pygame.SRCALPHA)

        # Step 1: Fill pixels with material base color
        for pixel in self._build.pixels:
            mat = self._materials[pixel.material_id]
            surf.set_at((pixel.x, pixel.y), mat.color_primary)

        # Step 2: Panel lines (1px darker between different materials)
        self._apply_panel_lines(surf)

        # Step 3: Edge highlight (1px lighter on top/left silhouette edges)
        self._apply_edge_highlight(surf)

        # Step 4: Material texture (per-material micro-detail)
        self._apply_material_texture(surf)

        # Step 5: Edge outline (1px dark border around entire silhouette)
        self._apply_outline(surf)

        # Step 6: Slot indicators (subtle colored dots)
        self._apply_slot_indicators(surf)

        self._base_surface = surf.convert_alpha()
        self._dirty = False
```

**How to replace sprite calls:**
In each view, search for calls to `SpriteManager.get_ship_sprite()` or `get_ship_animated()` for the player's ship. Replace with:

```python
# Before:
sprite = self._sprite_mgr.get_ship_sprite(self.player.ship.ship_type.id, scale=res_scale(2))

# After:
if self.player.ship.composite:
    sprite = self.player.ship.composite.get_surface(scale=res_scale(2))
else:
    sprite = self._sprite_mgr.get_ship_sprite(self.player.ship.ship_type.id, scale=res_scale(2))
```

Always keep the fallback for ships that haven't been converted yet (backward compat).

**Combat VFX compatibility:**
The existing `ShieldRenderer`, `DamageStateManager`, and `DestructionSequence` all work with any `pygame.Surface` — they use the sprite's bounding rect for positioning. The composite surface slots in identically. Verify by running a test combat after integration.

**Weight class → visual size:**
| Class | Native | Combat (res_scale 2) | Galaxy Map (res_scale 1) |
|-------|--------|---------------------|------------------------|
| Tiny | 16×16 | 32×32 | 16×16 |
| Small | 24×24 | 48×48 | 24×24 |
| Medium | 32×32 | 64×64 | 32×32 |
| Large | 48×48 | 96×96 | 48×48 |
| XL | 64×64 | 128×128 | 64×64 |

**Checkpoint:**
- [ ] Composite renders a recognizable ship from a preset build
- [ ] Auto-detailing makes even a simple rectangle build look like a ship
- [ ] Composite displays correctly in combat (correct position, scale, orientation)
- [ ] Shield bubble, damage sparks, destruction sequence all work on composite
- [ ] Composite displays on galaxy map with rotation
- [ ] Composite shows in HUD and station hub

---

### Phase D1: Content Catalog — Shapes & Materials

**Goal:** Create the full library of shapes and materials that players will use. This is content creation, not engineering.

**Effort:** MEDIUM | **Dependencies:** A1 (needs data model) | Can be done in parallel with B1

**Files to create/update:**

| File | Content |
|------|---------|
| `data/ships/shapes.json` | All ~55 shapes with pixel masks |
| `data/ships/materials.json` | All 16 materials with stat values and colors |
| `data/ships/presets.json` | All 24 legacy presets (update from A3 if needed) |

**Shape creation approach:**
Each shape needs a `pixel_mask` — a 2D boolean array. Define these as compact strings in JSON for readability:

```json
{
  "id": "medium_triangle",
  "name": "Medium Triangle",
  "pixel_mask_compact": [
    "###",
    ".##",
    "..#"
  ],
  "category": "basic",
  "unlock_method": "free"
}
```

The data loader converts `pixel_mask_compact` strings to `list[list[bool]]` during parsing.

**Material balance approach:**
Start with the values in the Material Catalog section of this document. Then run the preset parity test: do the 24 legacy presets produce stats within 10% of old ShipType values? Adjust material per-pixel values until they do. This is the primary balance lever.

**Content checklist:**
- [ ] 9 basic shapes (free) — rectangles + triangles per Shape Catalog
- [ ] 12 intermediate shapes (purchased) — per Shape Catalog
- [ ] 10+ advanced shapes (discovery-gated) — per Shape Catalog
- [ ] 8 faction shapes (rep-gated) — per Faction Shapes table
- [ ] 7 boss trophy shapes — per Boss Trophy Drops table
- [ ] 4 crew quest shapes — per Crew Quest Rewards table
- [ ] 3 starter materials — per Material Catalog
- [ ] 7 mid-game materials — per Material Catalog
- [ ] 4 late-game materials — per Material Catalog
- [ ] 2 boss trophy materials — per Boss Trophy Drops table
- [ ] All shapes have discovery_flavor text
- [ ] All materials have distinct, readable colors (test at native resolution)
- [ ] Preset parity test passes (all 24 within 10%)

---

### Phase D2: Content Distribution & Discovery Wiring

**Goal:** Every shape, material, and equipment module is tied to a specific source in the game world. The Acquisition Atlas becomes real.

**Effort:** HIGH | **Dependencies:** A3, B3, D1, plus access to mini-game views

**New files:**

| File | Purpose |
|------|---------|
| `data/ships/drydock_catalogs.json` | Per-system shape/material/equipment catalogs + weight class availability |
| `spacegame/models/builder_discovery.py` | Discovery logic: chance rolls, unlock tracking, milestone tracking |

**Files to modify:**

| File | Changes |
|------|---------|
| `spacegame/views/shipyard_view.py` | Filter equipment by current system's catalog (read from drydock_catalogs.json) |
| `spacegame/views/ship_builder_view.py` | Filter shapes/materials by unlocked + current system catalog |
| `spacegame/views/salvage_view.py` (or model) | Add shape discovery roll after salvage completion |
| `spacegame/views/mining_view.py` (or model) | Add material/shape discovery roll at deep layers |
| `spacegame/models/refining.py` (or similar) | Wire mastery tier rewards |
| `spacegame/models/combat_engine.py` | Add trophy drop roll after boss/elite kills |
| `spacegame/views/ground_exploration_view.py` (or model) | Add blueprint discovery roll |
| `spacegame/models/player.py` | Add `trade_profit_total` tracking, milestone checks on trade |
| `spacegame/models/faction_reputation.py` (or similar) | Wire reputation threshold → unlock notifications |
| `spacegame/models/crew.py` | Wire crew builder bonuses + quest rewards |

**Discovery popup pattern:**
Create a reusable discovery notification that shows:
- Shape/material name and visual preview (rendered at 4× for visibility)
- Discovery flavor text (italicized)
- "Added to your builder palette" confirmation
- Brief particle effect (COLLECT_SPARKLE preset)

This should use the existing floating message or tutorial overlay pattern.

**Drydock catalog JSON structure:**
```json
{
  "nexus_prime": {
    "shapes_sold": ["medium_rect", "arrow_point", "hull_section"],
    "materials_sold": ["standard_plate", "composite_weave"],
    "equipment_sold": ["laser_cannon", "dual_laser", "railgun", "trade_beam", ...],
    "weight_classes": ["tiny", "small", "medium", "large"],
    "price_modifier": 1.1
  },
  "forgeworks": {
    "shapes_sold": ["large_triangle", "hull_section", "mega_block"],
    "materials_sold": ["heavy_armor", "reinforced_plate"],
    "equipment_sold": ["mining_laser_retro", "missile_launcher", "plasma_caster", ...],
    "weight_classes": ["tiny", "small", "medium", "large", "xlarge"],
    "price_modifier": 1.0
  }
}
```

**Testing (critical — this phase touches many systems):**
1. Salvage at Crimson Reach → shape discovery fires with correct deck-type table
2. Mining at Iron Depths layer 5 → material discovery fires
3. Refining Gold mastery → shape unlock fires
4. Boss kill → trophy drops correctly (first kill only)
5. Trading milestone at 50K → weight class discount applies
6. Faction rep reaches Friendly → shape unlocks
7. Crew quest completion → crew shape unlocks
8. System-specific equipment: can't buy Axiom-only gear at Haven's Rest
9. Crimson Reach black market: requires heat or quest flag
10. Discovery popup displays correctly with flavor text

**Checkpoint:**
- [ ] Each of the 7 discovery sources (salvage, mining, refining, combat, ground, trading, faction) produces unlocks
- [ ] System-specific catalogs filter correctly in the builder
- [ ] All content from the Acquisition Atlas is wired and reachable
- [ ] Discovery popups display with flavor text
- [ ] Collection gallery shows locked items with unlock hints

---

### Phase E: Builder Polish & UX

**Goal:** Make the builder feel satisfying and professional. This is the difference between "functional tool" and "feature you want to spend time in."

**Effort:** MEDIUM | **Dependencies:** B1, B2, B3

**All changes in `ship_builder_view.py` + supporting engine files:**

1. **Stat comparison on hover**: When hovering a shape in the palette, show "+X hull, +Y weight" delta in the stats panel. Green for improvements, red for costs. This reduces cognitive load — the player sees the trade-off before committing.

2. **Builder ambient atmosphere**: Industrial background (reuse `AnimatedBackground("industrial")`), welding spark particles (reuse `ParticlePool` with `FORGE_FLAME` or new preset), subtle ambient audio. The shipyard should FEEL like a shipyard.

3. **Confirmation animation**: When player clicks CONFIRM BUILD, play a brief "assembly" flourish: spark particles converge on the ship, a bright flash, the composite sprite renders at large scale center-screen for 1 second, then fades. This makes confirming a build feel like a MOMENT.

4. **Shape search**: Text input at top of shape palette. Filters shapes by name as you type. Essential when the palette grows to 55+ shapes.

5. **Weight class upgrade flow**: Dedicated sub-screen or modal for purchasing weight class upgrades. Shows: canvas size comparison, stat budget comparison, cost, and an "import current build" option that centers the old build in the new canvas.

6. **Auto-Fill button**: Fills empty pixels inside the ship's convex hull with the cheapest unlocked material. For players who want to design the silhouette but not hand-fill every pixel.

7. **Stat breakdown tooltip**: Hover a stat (e.g., "Hull: 460") to see breakdown: "Standard Plate: 280, Heavy Armor: 120, Equipment: +60".

**Checkpoint:**
- [ ] Stat comparison makes trade-offs visible before placement
- [ ] Builder atmosphere feels immersive (background, particles, audio)
- [ ] Confirmation animation makes building feel rewarding
- [ ] A new player can build a functional ship in under 10 minutes
- [ ] A veteran can optimize a build in 3-5 minutes

---

### Phase F: Tutorial & Onboarding

**Goal:** A new player walks into the builder and knows what to do within 60 seconds.

**Effort:** LOW-MEDIUM | **Dependencies:** B3, E

**Implementation:**
Use the existing tutorial overlay system (`spacegame/views/tutorial_overlay.py` or similar pattern). The builder tutorial is a sequence of 10 contextual steps (detailed in the Tutorial Design section of this document).

**Key principles:**
- Tutorial fires ONCE on first builder visit (flag in `player.tutorial_flags`)
- Each step highlights a specific UI element and gives a short instruction
- Player must complete the highlighted action to advance (guided, not just informational)
- "Skip Tutorial" button always visible
- Tutorial can be replayed from Settings
- "Quick Start: Load Preset" button is ALWAYS visible, even during tutorial — escape hatch for players who don't want to build

**Also implement:**
- Contextual tooltips on every UI element (0.5s hover delay)
- Build validation warnings rendered in stats panel ("No weapons — you won't be able to fight")
- In-builder help panel (? button → overlay showing all controls and concepts)

**Checkpoint:**
- [ ] First-time player completes tutorial and has a functional ship
- [ ] Tutorial can be skipped without breaking anything
- [ ] "Load Preset" provides an instant working ship for non-builders
- [ ] All builder UI elements have informative tooltips

---

### Phase G: System Integration & Migration

**Goal:** Every game system works seamlessly with the new ship model. Old saves convert transparently. New games start with the builder.

**Effort:** MEDIUM | **Dependencies:** All previous phases

**System-by-system integration checklist:**

| System | File(s) | What to change | How to verify |
|--------|---------|---------------|--------------|
| **Combat** | `combat.py`, `combat_engine.py`, `combat_view.py` | Stats from build, moves from equipment, composite sprite | Fight an enemy → correct damage, hit chance, energy |
| **Repair** | Station repair logic | Cost = `f(total_material_cost, total_hull)` | Repair at station → cost scales with material quality |
| **Mining** | `mining_view.py` or model | Check `ship.has_module("mining_drill")` instead of `has_upgrade()` | Enter mining → works if mining drill in utility slot |
| **Salvaging** | `salvage_view.py` or model | Same pattern: check module in slot | Enter salvaging → works if salvage arm in slot |
| **Refining** | Refining model | Same pattern | Enter refining → works |
| **Trading** | Trading model | Cargo from build stats `computed_stats.cargo_capacity` | Buy/sell → cargo limits correct |
| **Travel** | Galaxy map, fuel logic | Fuel from build stats, speed from build stats | Jump → correct fuel cost, travel time |
| **Skill tree** | `progression.py`, stat computation | Bonuses apply to computed stats (hull_hp_bonus → +% hull) | Level skill → stats increase in builder |
| **Crew** | `crew.py`, stat computation | Crew bonuses apply (cargo_bonus, etc.) | Recruit crew → stats change |
| **Achievements** | Achievement checks | Update any that reference old upgrade/ship_type data | Check achievement triggers still fire |
| **Flee** | `combat_engine.py` | Flee bonus from build stats + equipment | Flee attempt → correct success rate |
| **New Game** | `game.py` | Start with Tiny weight class, Shuttle preset loaded, basic shapes/materials unlocked | New game → player has a functional ship |
| **Smuggling** | Smuggling logic | Check hidden_compartment module | Smuggling works with module in slot |

**Migration testing matrix:**
- [ ] Load save from before shipyard overhaul → auto-converts → game plays normally
- [ ] Load save with fully upgraded War Frigate → preset matches old stats
- [ ] Load save with installed upgrades → upgrades map to equipment in slots
- [ ] New game → tutorial → builder → first combat → all works

**Checkpoint:**
- [ ] ALL existing 5,076+ tests pass
- [ ] Every game activity (mine, salvage, refine, trade, fight, flee, repair) works with build-derived stats
- [ ] New game through first combat works end-to-end
- [ ] Old save load through combat works end-to-end

---

### Phase H: Expansion & Future (FUTURE — not part of initial implementation)

Ideas for post-launch iteration, documented here for reference:

1. **Ship painting**: Cosmetic color palette per material region. Material still determines stats, but player can tint the visual color. Purely cosmetic.
2. **Build code sharing**: Encode a ShipBuild as a Base64 string. Players share build codes. Import code → load build in builder.
3. **Enemy ship variety**: Auto-generate enemy builds from templates for visual diversity. Enemy stats still come from `EnemyTemplate` (no balance risk), but the rendered sprite is a composite.
4. **Fleet building**: Multiple ship builds for the Fleet Management feature (Campaign Act Two). Crew assigned to specific ships.
5. **Canvas expansion modules**: Rare modules that add rows/columns to your canvas without upgrading weight class. Found in late-game quests.
6. **Animated assembly**: On CONFIRM BUILD, watch modules assemble one by one with sparks and welds. Purely cinematic.
7. **Builder challenges**: "Build a ship under 40 weight that can defeat the Void Leviathan." Community challenges with leaderboard.

---

## Balance Guardrails

- **Weight cap is absolute**: Cannot exceed 100%. No exceptions, no overrides.
- **Stat floors**: Minimum 1 evasion, 1 speed (even heaviest build can dodge/move slightly).
- **Material stat caps**: No single pixel should contribute more than 4 hull, 1 shield, or 0.25 evasion.
- **Slot requirement**: Must have at least 1 weapon OR 1 engine slot (can fight or flee).
- **Core requirement**: Must have exactly 1 core slot (energy system).
- **Identity threshold (35%)**: Prevents "I have all three identity passives" builds.
- **Weight modifier ranges**: -20% to +15% evasion, -10% to +10% speed (bounded impact).
- **Repair cost scaling**: Prevents ultra-cheap hull tanking (expensive materials = expensive repairs).
- **Pixel economy**: At max, a build should cost comparable to current late-game ship + full upgrades (~300-500K for a Large, ~700K+ for XL). Not cheap, not impossible.
- **Discovery pacing**: Shapes should unlock steadily throughout the game. By mid-game, player has ~20 shapes. By end-game, ~35+. The last 5-10 are rare collectibles.
- **Preset parity**: Legacy presets must produce stats within 10% of old ShipType values. If not, adjust material values until they do. This is the first thing to verify.
- **Builder time expectation**: A quick rebuild (swap some materials, move a slot) should take 2-3 minutes. A full from-scratch design should be 10-15 minutes. If it takes longer, the UX needs improvement.
- **No "best build"**: Weight, power, grid space, and discovery gating should prevent convergence. If playtesting shows one dominant build, add counter-content (new enemy types, material weaknesses) rather than nerfing the build.

---

## Content Counts Summary (Final)

| Content Type | Count | Acquisition Breakdown |
|-------------|-------|----------------------|
| Weight Classes | 5 | Free (Tiny) + Purchase (Small/Medium/Large/XL) + Campaign alt path (XL) |
| Shapes | ~55 | Free (9) + Purchase (12) + Salvage (3) + Mining (3) + Refining (3) + Quest (9) + Faction (8) + Boss trophy (7) + Crew quest (4) + Trading (1) + Ground (4) + Completionist (1) |
| Materials | 16 | Free (3) + Location-purchase (7) + Faction Allied (4) + Boss trophy (2) + Quest (2) + Mini-game variant (3) |
| Equipment Modules | ~85 | Distributed across 10 systems by faction identity |
| Presets | 24+ system + 10 player | All legacy ships + player-saved custom builds |
| Discovery Sources | 7 | Salvage, Mining, Refining, Combat, Ground, Trading, Faction |
| Builder Tools | 8 | Stamp, Pencil, Eraser, Brush, Slot, Fill, Select, Mirror |
| Tutorial Steps | 10 | Guided first-build walkthrough |
| New Files | ~8 | ship_build.py, ship_composite.py, ship_builder_view.py, builder_discovery.py, shapes.json, materials.json, presets.json, drydock_catalogs.json |
| Modified Files | ~20 | ship.py, combat.py, game.py, save_manager.py, data_loader.py, player.py, shipyard_view.py, combat_view.py, galaxy_map_view.py, cockpit_hud.py, + mini-game views |
