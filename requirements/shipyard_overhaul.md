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

### Phase A: Data Model & Core Logic (HIGH effort)

**Goal:** The foundational data structures and computation engine. No UI yet.

1. Create `HullShape` dataclass + `data/ships/shapes.json` (~40 shapes with pixel masks)
2. Create `HullMaterial` dataclass + `data/ships/materials.json` (14 materials)
3. Create `ShipBuild`, `PlacedPixel`, `DesignatedSlot` dataclasses
4. Create `ShipGridManager` — placement validation, collision detection, weight calculation
5. Create `ShipStatsComputer` — derive all stats from build (hull, shields, evasion, armor, speed, etc.)
6. Create `ShipComposite` — render build into a pygame Surface with auto-detailing pipeline
7. Implement weight class system with modifier tables
8. Implement power budget computation
9. Implement identity detection (Juggernaut/Sentinel/Ghost threshold)
10. Create preset system + `data/ships/presets.json` (24 legacy ship presets)
11. Save/load serialization for ShipBuild (new format + old format migration)
12. Update `Ship` model to derive stats from `ShipBuild` instead of `ShipType`
13. Update `build_player_combat_state()` to use build-derived stats
14. **Tests**: Grid placement, stat computation, weight limits, identity detection, serialization, migration

### Phase B: Builder View — Core Interaction (HIGH effort)

**Goal:** The interactive ship builder screen. The heart of the feature.

1. Create `ShipBuilderView` (BaseView subclass) with grid rendering
2. Implement shape palette panel (left side) with category tabs and scrolling
3. Implement material selector panel (right side)
4. Implement Shape Stamp tool (select shape → ghost preview → click to place)
5. Implement Pencil tool (single pixel placement)
6. Implement Eraser tool (click to remove)
7. Implement Material Brush tool (repaint existing pixels)
8. Implement Mirror Mode toggle (symmetrical placement)
9. Implement Slot Designator tool (place equipment slots on filled areas)
10. Implement real-time stats panel with weight/power bars
11. Implement build validation (required core slot, weight limit, etc.)
12. Implement CONFIRM BUILD flow
13. Implement equipment install modal (click slot → browse equipment)
14. Implement Undo/Redo stack
15. Wire into game state (Shipyard → Builder transition)

### Phase C: Visual System — Ship Composite Rendering (MEDIUM effort)

**Goal:** Player-built ships render beautifully everywhere.

1. Implement full auto-detailing pipeline (panel lines, edge highlight, outline, material texture)
2. Implement engine glow animation (2-frame pulse at engine slot locations)
3. Implement tier visual variations for materials
4. Cache composite surfaces with invalidation on build change
5. Replace player ship sprite calls in `combat_view.py`
6. Replace player ship sprite calls in `galaxy_map_view.py`
7. Replace player ship sprite in `cockpit_hud.py`
8. Update `station_hub_view.py` docked ship display
9. Update save/load slot thumbnails
10. Verify all existing VFX work with composite (shields, damage sparks, destruction)
11. Size-appropriate rendering for each weight class (tiny→XL visual scaling)

### Phase D: Content Catalog & System Distribution (HIGH effort)

**Goal:** Full shape/material/equipment catalog, distributed across systems per the Acquisition Atlas.

**Shapes & Materials:**
1. Create all ~55 shapes with pixel masks in `data/ships/shapes.json`
2. Balance all 16 materials in `data/ships/materials.json`
3. Create all 24 legacy presets in `data/ships/presets.json`
4. Assign drydock-specific shape/material catalogs per system (Acquisition Atlas mapping)
5. Assign weight class availability per system drydock

**Equipment Distribution:**
6. Redistribute all ~85 equipment modules across faction systems (per Equipment Distribution tables)
7. Mark system-exclusive equipment (e.g., Trade Beam = Nexus only, Cryo Cannon = Axiom only)
8. Mark black-market-only equipment for Crimson Reach
9. Update shipyard view to filter equipment by current system's catalog

**Discovery Wiring:**
10. Wire salvage discovery: deck-type-specific shape/material drops with skill scaling
11. Wire mining discovery: system-specific deep-layer discoveries
12. Wire refining mastery: Bronze/Silver/Gold tier unlocks per recipe category
13. Wire combat trophy drops: boss-guaranteed + elite/regular chance drops
14. Wire ground exploration: map-specific blueprint finds
15. Wire trading milestones: cumulative profit → economic unlocks
16. Wire faction reputation: 5-tier unlock paths per faction (Neutral→Allied)
17. Wire crew bonuses: passive builder discounts + discovery chance boosts
18. Wire crew quest rewards: unique shapes from companion quest chains

**UI:**
19. Create discovery popup UI (shape/material/equipment found notification with flavor text)
20. Create collection gallery screen (shapes, materials, trophies — shows locked items with unlock hints)
21. Create trade milestone tracker (accessible from stats or shipyard)

**Testing:**
22. Test each discovery path fires correctly (salvage, mining, refining, combat, ground, trading)
23. Test faction unlock progression across all 4 factions + Crimson Reach
24. Test system-specific equipment availability (can't buy Axiom-only gear at Haven's Rest)
25. Verify all presets produce stats within 10% of original ShipType values

### Phase E: Builder Polish & UX (MEDIUM effort)

**Goal:** Make the builder feel satisfying and accessible.

1. Ghost preview (translucent shape follows cursor)
2. Invalid placement feedback (red ghost, tooltip explaining why)
3. Fill tool implementation (flood-fill enclosed area)
4. Select tool (region select, move, copy, delete)
5. Rotation preview (R key rotates ghost before placement)
6. Stat comparison (hover module in equipment → preview stat delta)
7. Builder ambient: industrial background, particle sparks, audio ambiance
8. Confirmation animation (sparks, "ship powered up" flourish)
9. Zoom/pan for Large and XL canvases
10. Shape search in palette
11. "Auto-Fill" button (fill empty cells with cheapest material)
12. Weight class upgrade flow (buy new class, import old build)

### Phase F: Tutorial & Onboarding (LOW-MEDIUM effort)

**Goal:** New players can use the builder without frustration.

1. Implement 10-step guided first-build tutorial
2. Contextual tooltips on all builder UI elements
3. Quick-start preset loading (prominent "LOAD PRESET" for non-builders)
4. In-builder help panel (? button showing controls and concepts)
5. Contextual warnings ("Your ship has no weapons — you won't be able to fight")
6. Tutorial flag: skip tutorial on repeat visits, replayable from Settings

### Phase G: System Integration & Migration (MEDIUM effort)

**Goal:** All game systems work seamlessly with the new ship model.

1. Combat: all stats from build, all moves from equipment
2. Repair: cost scaled by material value
3. Mining/Salvage/Refining: check module presence in slots
4. Trading: cargo from utility slot equipment
5. Travel: speed and fuel from build stats
6. Skill tree: bonuses apply to computed stats
7. Crew: bonuses apply to computed stats + builder bonuses
8. Achievements: update references to old ship/upgrade data
9. Old save migration: transparent conversion on load
10. New game flow: starts with Tiny weight class + Shuttle preset

### Phase H: Expansion & Future (LOW effort, FUTURE)

1. Ship painting (cosmetic color palette per material region)
2. Build code sharing (encode build as shareable text string)
3. Enemy ship variety (auto-generate enemy builds for visual diversity)
4. Fleet building (multiple ship builds for fleet management feature)
5. Frame modifications (add cells to an existing weight class — hull expansion module)
6. Animated assembly sequence on confirm (watch ship build piece by piece)

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
- **Discovery pacing**: Shapes should unlock steadily throughout the game. By mid-game, player has ~20 shapes. By end-game, ~35+. The last 5 are rare collectibles.
- **Preset parity**: Legacy presets must produce stats within 10% of old ShipType values. If not, adjust material values until they do.
- **Builder time expectation**: A quick rebuild (swap some materials, move a slot) should take 2-3 minutes. A full from-scratch design should be 10-15 minutes. If it takes longer, the UX needs improvement.

---

## Content Counts Summary

| Content Type | Count | Notes |
|-------------|-------|-------|
| Weight Classes | 5 | Tiny through Extra Large |
| Shapes | ~40 | 9 basic (free) + 12 intermediate (purchased) + 10 advanced (discovered) + 8 faction |
| Materials | 14 | 3 starter + 7 mid-game + 4 late-game |
| Equipment Modules | 75+ | Carried from existing upgrade system + new modules |
| Presets | 24+ | All legacy ships + player-created (max 10) |
| Discovery Sources | 4 | Salvage, Mining, Refining, Quests |
| Builder Tools | 8 | Stamp, Pencil, Eraser, Brush, Slot, Fill, Select, Mirror |
| Tutorial Steps | 10 | Guided first-build walkthrough |
