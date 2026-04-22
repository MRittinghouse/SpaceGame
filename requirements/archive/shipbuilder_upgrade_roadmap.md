# Shipbuilder Upgrade Roadmap — From Pixels to Parts

> **Status**: DESIGN PHASE (iterating on requirements)
>
> The current pixel builder gives players a canvas and materials. It works, but it feels like MS Paint with stat colors. This roadmap evolves the builder into a true ship engineering system: module-based construction with freeform hull shaping, meaningful physics-based constraints, and a parts progression that echoes Armored Core's garage, Starfield's snap-together builder, and FTL's functional rooms.

---

## Design Philosophy

### Core Influences

| Influence | What We Take |
|-----------|-------------|
| **Armored Core** | The garage feel. Named parts with identity. Unlocking through missions and shops. Weight/energy trade-offs. The build IS your identity. |
| **Starfield Ship Builder** | Snap-together modules on a grid. Clear viability rules. Manufacturer variety. Seeing your ship take shape from real parts. |
| **FTL** | Rooms as functional systems. Crew paths. Subsystem-targeted damage. Layout IS strategy. |
| **Minecraft** | Simple blocks, emergent complexity. Functional blocks + structural blocks. Creative expression within consistent rules. |

### The Shift

**Before**: The fundamental building unit is a pixel. Players paint colored pixels onto a canvas. Materials provide stats. Shapes are geometric stamps. The result is pixel art, not engineering.

**After**: The fundamental building unit is a **module** — a pre-designed, multi-pixel functional component with a name, stats, manufacturer, and pixel-art appearance. Players snap modules together, then paint hull pixels for creative expression. The result is a ship built from recognizable parts, shaped by the player's hand.

**Key principle**: We build tools, not sprites. Modules are defined as compact text masks in JSON — the existing rendering pipeline (ShipComposite's 7-step auto-detail) turns them into polished pixel art. No hand-drawn sprites required. Content scales by writing a few lines of JSON, not by commissioning art.

---

## The Two-Layer Builder

### Layer 1: Functional Modules (The Engineering)

Modules are pre-designed, multi-pixel components that represent functional ship systems. Each module:

- Has a **pixel footprint** defined as a compact multi-character mask (e.g., `"HGGH"` where each character maps to a visual material)
- Has a **fixed function** (cockpit, engine, weapon mount, shield generator, cargo bay, etc.)
- Has **fixed stats** determined by the module, not by per-pixel material accumulation
- Has a **name and manufacturer** giving it identity ("Foundry Heavy Drive", not "orange pixels")
- Is **unlockable** through gameplay (purchase, salvage, faction rep, quests, boss drops)
- Can be **rotated** (0/90/180/270) and **flipped** horizontally
- Snaps to the pixel grid with no sub-pixel positioning

### Layer 2: Hull Pixels (The Artistry)

After placing modules, players freely paint structural pixels to:

- **Connect modules** that aren't directly adjacent
- **Shape the exterior silhouette** (pointed nose, swept wings, flared tail)
- **Add aesthetic detail** (panel lines, racing stripes, hull markings)
- **Reinforce structural weak points** (thicken narrow connections)

Hull pixels use a simplified material set (3-4 types) focused on weight/durability trade-offs. The meaningful design decisions happen in module selection; hull pixels are creative expression and structural glue.

### How It Feels

> Open the builder. Browse the parts catalog. Drag a **Reyes-Kowalski Standard Bridge** onto the grid. Snap a **Foundry Heavy Drive** to the rear. Mount two **Talon Light Hardpoints** on the flanks. Slot in a **Compact Shield Generator** and a **Trader's Cargo Bay**. Switch to hull mode. Paint standard plate to connect the modules, sculpt a pointed nose, extend wing shapes off the weapon mounts, flare the tail around the engines. Mirror mode keeps it symmetric. Name it "The Kestrel." Fly.

---

## Module Art: How We Build Parts Without Sprite Work

### The Critical Insight

**The existing ShipComposite rendering pipeline IS our module art generator.**

The 7-step pipeline (material color fill, panel lines, edge highlights, material texture, outline, slot indicators, engine glow) already transforms raw pixel data into polished-looking ships. Modules are defined as compact text masks in JSON with material character mappings. The renderer turns them into visually rich pixel art automatically.

### Module Definition Format

Extension of the existing compact mask format with multi-character material mapping:

```json
{
  "id": "standard_bridge",
  "name": "Standard Bridge",
  "manufacturer": "reyes_kowalski",
  "category": "cockpit",
  "description": "Reliable command center with solid visibility and balanced crew space.",
  "pixel_mask_compact": [
    ".HHH.",
    "HGCGH",
    "HGCGH",
    "HHHHH"
  ],
  "material_map": {
    "H": "module_hull",
    "G": "cockpit_glass",
    "C": "console_panel"
  },
  "provides": {
    "slot_type": "core",
    "crew_capacity": 2,
    "sensor_bonus": 0.1
  },
  "weight": 8,
  "cost": 5000,
  "unlock_method": "purchase",
  "unlock_cost": 5000
}
```

Five lines of pixel mask. A material map. Stats. The renderer handles the rest.

### Module-Specific Visual Materials

New materials purely for module visual identity (no per-pixel combat stats — modules have fixed stats):

| Material ID | Visual Purpose | Renderer Treatment |
|------------|---------------|-------------------|
| `module_hull` | Generic module casing | Slightly tinted vs hull pixels so modules are subtly distinct |
| `cockpit_glass` | Windows, canopy | Blue-tinted, semi-transparent, subtle reflection highlight |
| `console_panel` | Bridge instruments | Dim glow dots (green/amber), suggests screens |
| `exhaust_port` | Engine nozzles | Dark interior, ties into engine glow animation |
| `weapon_barrel` | Gun barrels, missile tubes | Dark gunmetal, slightly reflective |
| `shield_emitter` | Shield projection hardware | Bright cyan, subtle pulse texture |
| `sensor_dish` | Detection equipment | Light metallic, bright center pixel |
| `cargo_interior` | Visible hold space | Dark interior, subtle crate/container pattern |

Each gets a texture rule in ShipComposite step 4, just like `heavy_armor` has rivets and `shield_crystal` has shimmer. The infrastructure already exists.

### Manufacturer Differentiation Without New Art

Same pixel mask + different material map = different visual identity:

| Manufacturer | Hull Color | Texture Style | Philosophy |
|-------------|-----------|---------------|------------|
| **Reyes-Kowalski** | Clean white-blue (#B0C4DE) | Smooth, professional | Balanced, reliable |
| **Foundry Collective** | Industrial brown-orange (#8B6914) | Riveted, heavy | Durable, tanky |
| **Talon Systems** | Sharp red-black (#8B1A1A) | Angular highlights | Aggressive, weapon-focused |
| **Sable Dynamics** | Dark slate-blue (#2F3640) | Matte, minimal | Stealth, evasion |
| **Meridian Works** | Elegant gold-white (#D4AF37) | Shimmer accents | Efficient, expensive |
| **Salvage Rat** | Mismatched patchwork | Random tint variation | Cheap, character |

~120 unique pixel masks x 4-6 manufacturer variants = **500-700+ visually distinct modules** from purely data-driven definitions. No sprite files. No artist pipeline. Just JSON.

### Rendering Integration

The renderer doesn't need fundamental changes. Module pixels are flattened into the same `list[PlacedPixel]` the pipeline already consumes:

```
PlacedModule (position, rotation, module_data)
  -> resolve to PlacedPixel list (apply rotation, offset, material_map)
  -> merge with hull PlacedPixels
  -> feed to existing ShipComposite pipeline
  -> 7-step auto-detail renders everything
```

Modules are a builder/model abstraction. The renderer sees pixels.

### Module Boundary Visualization (Builder Only)

In the builder view, each placed module gets a subtle dashed border and a small label (icon or abbreviation) so the player can see module boundaries. This is purely a builder overlay — the in-game rendered ship shows no module boundaries.

---

## Mandatory Module Categories

### Required on Every Ship

**1. Cockpit** (exactly 1)
- Contains the core equipment slot
- Determines base crew capacity and sensor range
- Should be positioned interior (protected by surrounding hull/modules)
- If destroyed in combat: severe accuracy and evasion penalties

**2. Engine** (at least 1)
- Contains engine equipment slots
- Must be in the rear 30% of the ship's filled bounding box
- Determines thrust and fuel efficiency
- If destroyed in combat: speed and evasion drop to near-zero

**3. Weapon Mount** (at least 1)
- Contains weapon equipment slots
- Should have exterior exposure (edge pixels touching empty space) for firing lines
- Position relative to ship silhouette determines firing arc
- If destroyed in combat: mounted weapon disabled

**4. Shield Generator** (at least 1)
- Contains defense equipment slots
- Position affects shield coverage direction (centered = even, offset = directional)
- If destroyed in combat: shields drop

**5. Cargo Bay** (at least 1)
- No equipment slots — this is pure storage
- Pixel count in module directly determines cargo capacity
- This is a trading game; every ship carries cargo
- If hit in combat: chance to destroy carried commodities

### Required at Higher Weight Classes

**6. Crew Quarters** (required at Medium+)
- Determines crew specialist capacity (pixels / 4 = crew slots)
- No equipment slots

**7. Reactor Core** (required at Large+)
- Must be interior (surrounded by other modules/hull — a surface reactor is suicidal)
- Powers equipment; larger reactor = more power budget
- If damaged: all systems degrade proportionally

### Optional (Unlock Gameplay Advantages)

| Module Type | Benefit | Unlocked By |
|------------|---------|-------------|
| Armor Plating | Directional damage reduction | Purchase |
| Sensor Array | Detection range, targeting accuracy | Purchase |
| Medical Bay | Crew healing during travel | Purchase |
| Workshop | Field repairs, reduced station repair costs | Purchase |
| Fuel Tank | Extended jump range | Purchase |
| Refinery Pod | Process raw ores in flight | Mining questline |
| Smuggling Compartment | Hidden cargo, scan-resistant | Black market / quest |
| Brig | Hold prisoners for bounties | Faction (Guild) |

---

## Hull Pixel Materials (Simplified)

Hull pixels are the creative/structural layer. Keep it simple — 3-4 materials:

| Material | Color | Weight | HP | Feel |
|----------|-------|--------|-----|------|
| **Light Alloy** | Silver | Low | Low | Fast, agile ships |
| **Standard Plate** | Gray | Medium | Medium | Default, workmanlike |
| **Heavy Armor** | Dark Steel | High | High | Tanks, warships |
| **Stealth Composite** | Dark Blue-Black | Medium | Low | Covert builds |

---

## Physics-Based Shape Constraints

These systems make ship shape mechanically meaningful without prescriptive rules. Players discover "good design" through feedback, not error messages.

### Connectivity (Hard Rule)

All filled pixels (module + hull) must form a single 4-connected component. This is the one binary gate — disconnected pieces are not a ship.

- On placement: prevent placing disconnected islands
- On erasure: prevent deletions that would split the ship (articulation point detection)
- UX: ghost preview turns red when placement would disconnect

### Structural Integrity (Soft Consequence)

Thin connections (1-2 pixel wide bridges) between larger masses are **structural weak points**:

- Builder shows a structural heat map overlay (green = solid, yellow = narrow, red = critical)
- In combat, hits near a bottleneck have a chance to **sever** that section, temporarily disabling any modules/slots on the severed piece
- Severed sections are restored after combat with a repair cost
- This rewards solid, well-connected designs while allowing fragile extremities as a calculated risk

**Detection**: Find articulation points via DFS. Chains of articulation points connecting larger masses = bottleneck zones.

### Center of Mass (Soft Consequence)

Computed from weighted pixel positions (each pixel weighted by its material/module weight):

| Balance | CoM Offset | Effect |
|---------|-----------|--------|
| Balanced | <15% from center | No penalty |
| Off-balance | 15-30% | -5 to -15% evasion, slight turn rate reduction |
| Severely off-balance | >30% | Significant evasion penalty, ship pulls to one side |

Rewards thoughtful, balanced designs without requiring symmetry. Asymmetric ships are valid — they just handle differently.

### Hull Efficiency (Soft Consequence)

- **Interior pixels**: all 4 orthogonal neighbors are filled
- **Perimeter pixels**: at least one neighbor is empty/edge

Interior pixels contribute full stats. Perimeter pixels contribute reduced stats (~75%). This naturally:
- Punishes paper-thin designs (all perimeter)
- Rewards compact shapes (more interior volume)
- Creates a visible tradeoff for wings/protrusions (low-efficiency perimeter pixels traded for positional advantage)

### Frontal Profile (Soft Consequence)

Ship's filled bounding box width determines frontal cross-section (how easy to target):
- Narrower ships get evasion bonuses (smaller target)
- Wider ships are easier to hit
- Creates a genuine shape-based evasion vs. durability tradeoff

---

## Module Connectivity Rules

```
Every section connects through Hull Frame / hull pixels:

    ┌──────────┐     ┌──────────┐
    │ Weapon   ├──┐  │  Sensor  │
    └──────────┘  │  └────┬─────┘
                  │       │
              ┌───┴───────┴───┐
              │   HULL / FRAME │
              ├───┬───────┬───┤
              │   │       │   │
         ┌────┤ ┌─┴──┐ ┌──┴─┐├────┐
         │Shld│ │Brdg │ │Crgo││Crew│
         └────┘ └────┘ └────┘└────┘
                    │
              ┌─────┴─────┐
              │  Engine    │
              └────────────┘
```

1. Every module must be adjacent (share a pixel edge) to either another module or hull pixels that connect back to the ship body
2. The entire ship (modules + hull pixels) must be one connected component
3. Modules cannot overlap each other
4. Modules can touch directly (no hull pixel gap required) or be bridged by hull pixels

---

## Builder UX Flow

### Design Note: Tool Prominence & Visual Clarity

> **IMPORTANT**: The existing builder shrinks tools (mirror, flip, rotate, erase) into a minimal corner. This must change. Building tools are the player's primary interaction — they deserve prominent, clearly labeled UI real estate. Think Photoshop's tool sidebar, not a collapsed hamburger menu.
>
> Principles:
> - **Large, labeled buttons** for core actions (Rotate, Flip, Mirror, Erase, Undo/Redo)
> - **Visual icons with text labels** — icons alone are ambiguous; text alone is slow to scan. Both.
> - **Dedicated toolbar row** across the top or a wide sidebar — not tucked into a corner
> - **Hotkey hints visible** on each button (R for Rotate, Q for Flip, X for Mirror, etc.)
> - **Active tool highlighting** — always obvious which tool/mode is currently active
> - **Mode switching must be obvious** — Module Placement vs. Hull Pixel mode should be a prominent toggle, not a subtle tab
> - **Undo/Redo always visible** — Ctrl+Z/Ctrl+Y with prominent buttons, not hidden shortcuts only

### Step 1: Choose Weight Class & Frame
Select weight class (Tiny through XLarge). For Medium+, choose frame variant (Square, Wide, or Tall) — shows canvas dimensions and a visual preview of the aspect ratio. Shows requirements checklist for that class. Frame choice is final for this build.

### Step 2: Module Placement Mode (Primary)
- **Left panel**: Parts catalog organized by tabs (Cockpits, Engines, Weapons, Shields, Cargo, Utility, Structural)
- **Filters**: manufacturer dropdown, "unlocked only" toggle, weight range slider
- **Module preview**: hover a module in catalog to see its pixel art at scale, stats summary, weight cost, manufacturer
- **Placement**: click module in catalog to select, move cursor over grid to see ghost preview, click to place
- **Manipulation**: R to rotate, Q to flip — ghost preview updates in real-time before placement
- **Removal**: right-click a placed module to select it, then Delete/Backspace to remove, or drag to reposition
- **Comparison**: select a placed module and hover a catalog module to see stat diff (green/red delta numbers)
- **Requirements checklist** on right panel updates live (Cockpit ✓, Engine ✓, Weapons ✗...)

### Step 3: Hull Pixel Mode (Secondary)
- Switch via prominent toggle button or Tab hotkey
- Select hull material from simplified palette (4 types) — large color swatches, not tiny squares
- **Tools toolbar**: Pencil (P), Fill (F), Eraser (E), Mirror (X), Shape Stamp (S) — each a large labeled button
- Shape stamps available for hull pixels (existing geometric shape library)
- Paint to connect modules, shape exterior, add flair
- **Connectivity feedback**: pixels that would create disconnected islands show red preview; valid placements show green

### Step 4: Review & Checkout
- **Stats panel** shows all computed values: hull HP, shields, armor, evasion, speed, cargo capacity, fuel range, crew capacity, power budget
- **Overlay toggles**: structural integrity heat map, center of mass crosshair, module boundaries, firing arcs
- **Weight budget bar** — always visible during building, not just in review
- **Requirements checklist** — all mandatory modules present, minimum counts met, connectivity valid
- **Warnings panel** — non-blocking advisories ("Cockpit is on the hull exterior — consider protecting it", "Center of mass is 22% off-center — handling penalty applies")
- **Running build cost** — always visible, updates live (informational only, no credits deducted during design)
- All requirements must be met (green checklist) for the Finished button to be enabled
- **Finished button → Checkout screen**:
  - Itemized receipt: each module with name, manufacturer, instantiation cost
  - Hull pixel costs by material type
  - If rebuilding: credit for old build (80% of removed modules), net cost
  - Player's credits balance, afford/shortfall indicator
  - **Name the ship** text field
  - **Confirm Purchase** (pays, saves build, exits builder) / **Back to Builder** (return to editing)
  - If can't afford: shortfall shown in red, Confirm disabled, "Back to Builder" to adjust

### Builder Layout (Screen Organization)

```
┌─────────────────────────────────────────────────────────────────┐
│  [MODULE MODE ●]  [HULL MODE ○]     [UNDO] [REDO]   Weight: ██████░░ 72%  │
├──────────┬──────────────────────────────────┬───────────────────┤
│          │  ← STERN          BOW →          │  REQUIREMENTS     │
│  PARTS   │  ┌╌╌╌╌╌╌┬────────────────────┐  │  ✓ Cockpit        │
│  CATALOG │  ┊engine ┊                    │  │  ✓ Engine         │
│          │  ┊ zone  ┊   SHIP CANVAS      │  │  ✗ Weapon Mount   │
│ [Cockpit]│  ┊(tinted┊   (grid + modules  │  │  ✓ Shield Gen     │
│ [Engine] │  ┊ hint) ┊    + hull pixels)  →  │  ✓ Cargo Bay      │
│ [Weapon] │  ┊       ┊                    │  │                   │
│ [Shield] │  └╌╌╌╌╌╌┴────────────────────┘  │  STATS            │
│ [Cargo]  │                                  │  Hull: 245        │
│ [Utility]│                                  │  Shield: 180      │
│ [Struct] │                                  │  Evasion: 12%     │
│          │                                  │  Speed: 8         │
│ ──filter──│                                  │  Cargo: 45        │
│ [mfg: ▼] │                                  │                   │
│          │                                  │  OVERLAYS         │
│  module  │                                  │  [Integrity]      │
│  preview │                                  │  [CoM]            │
│  + stats │                                  │  [Firing Arcs]    │
├──────────┴──────────────────────────────────┴───────────────────┤
│  TOOLBAR: [Rotate R] [Flip Q] [Mirror X] [Erase E] [Fill F]    │
│           [Pencil P] [Stamp S] [Select V]   Material: [■■■■]   │
└─────────────────────────────────────────────────────────────────┘
```

Key layout principles:
- **Top bar**: Mode toggle is the most prominent element. Weight bar always visible.
- **Left panel**: Parts catalog with category tabs, scrollable, filterable. ~200px wide.
- **Center**: Ship canvas dominates the screen. Zoom/pan with scroll wheel and middle-click.
- **Right panel**: Requirements checklist + live stats + overlay toggles. ~180px wide.
- **Bottom toolbar**: All building tools, large and labeled with hotkey hints. Material selector when in hull mode.

---

## Progression & Unlocks

### Blueprint + Instantiation Cost Model

Modules use a **blueprint** system: unlock once, pay to instantiate each time.

**Two distinct costs:**

| Cost Type | When Paid | What It Represents | Example |
|-----------|-----------|-------------------|---------|
| **Blueprint unlock** | Once, ever | Learning the design / acquiring the schematic | Buy "Standard Bridge" blueprint at shop for 5,000 CR. Now it's in your catalog permanently. |
| **Instantiation cost** | Each time placed in a build | Manufacturing and installing that part | Each Standard Bridge you place in a build costs 2,000 CR to fabricate. Three Light Hardpoints = 3 × 1,500 CR. |

**How the builder handles costs:**

1. **The builder is a sandbox — no money changes hands until checkout.** Freely place, remove, rearrange, experiment. Zero cost, zero commitment. The builder is a design tool, not a cash register. This is the Starfield model: build your dream ship first, worry about the bill after.
2. **Running cost display**: a live-updating cost ticker shows what the build *would* cost, so the player can make informed decisions while designing. But it's informational only — not deducted.
3. **Checkout on "Finished"**: when the player hits the Finished/Confirm button, a **checkout summary** appears — an itemized receipt showing:
   - Each module placed, its instantiation cost, and manufacturer
   - Hull pixel material costs (total per material type)
   - Subtotal
   - If rebuilding: credit for existing build (80% of removed modules' value), net cost shown
   - Player's current credits and whether they can afford it
   - **Confirm Purchase** / **Back to Builder** buttons
4. **Refund rate: 80%**: when rebuilding an existing ship, removed modules are credited at 80% of their original instantiation cost. The 20% loss represents installation labor you don't get back. New additions are charged at full price. The checkout shows the net delta clearly.
5. **Can't afford it?** If the player designs a ship they can't pay for, the checkout screen shows the shortfall in red. They can go back to the builder and downgrade modules, use cheaper manufacturers, or reduce hull pixels until it fits their budget. The builder never prevents you from *designing* an expensive ship — it just won't let you *build* one you can't afford.
6. **Hull pixels**: each hull pixel has a per-pixel material cost (existing system). Included in the checkout total.

**Manufacturer cost scaling:** Same base mask, different instantiation cost per manufacturer. A Meridian Works module costs more to instantiate than the same shape from Salvage Rat. This makes manufacturer choice economic as well as aesthetic.

| Manufacturer | Cost Modifier | Rationale |
|-------------|--------------|-----------|
| **Salvage Rat** | 0.6x | Cheap, scrappy, variable quality |
| **Reyes-Kowalski** | 1.0x (baseline) | Standard pricing, reliable |
| **Foundry Collective** | 1.1x | Heavy industrial, durable materials |
| **Talon Systems** | 1.2x | Precision weapons engineering |
| **Sable Dynamics** | 1.3x | Stealth tech premium |
| **Meridian Works** | 1.5x | Luxury, cutting-edge, expensive |

**Example build cost breakdown:**
```
Reyes-Kowalski Standard Bridge:    2,000 CR
Foundry Heavy Drive (×1):          3,300 CR  (3,000 × 1.1)
Talon Light Hardpoint (×2):        3,600 CR  (1,500 × 1.2 × 2)
Sable Compact Shield Node (×2):    2,600 CR  (1,000 × 1.3 × 2)
Reyes-Kowalski Standard Cargo:     1,500 CR
Hull pixels (142 × standard plate): 1,136 CR
─────────────────────────────────────────────
Total build cost:                 14,136 CR
```

**Blueprint unlock sources:**

| Source | Unlock Cost | Pacing |
|--------|------------|--------|
| **Starter kit** | Free (given at game start) | Game start — basic cockpit, light engine, light hardpoint, basic shield, small cargo, basic structural pieces |
| **Station shops** | Credits (varies by module tier) | Early-mid game — browse and buy blueprints at shipyard stations |
| **Faction reputation** | Free at rep threshold | Mid game — manufacturer modules unlock at Friendly/Trusted/Allied tiers |
| **Salvage missions** | Free (discovery) | Ongoing — random blueprint drops from derelicts |
| **Quest rewards** | Free (quest completion) | Mid-late game — unique named modules |
| **Boss drops** | Free (trophy) | Late game — rare, powerful, flavorful |
| **Black market** | Credits (premium) | Mid game — smuggling compartments, illegal mods |
| **Mining/Refining** | Free (discovery) | Mid game — specialized modules from deep mining |

### Module Count Targets

| Category | Base Masks | Example Variety | x Mfg Variants | Visual Total |
|----------|-----------|----------------|-----------------|-------------|
| Cockpits | 12 | Compact pod, wide bridge, armored command, tall tower, observation dome, stealth helm, war bridge, racing cockpit, luxury suite, exploration bridge, split canopy, sensor bridge | x4 | 48 |
| Engines | 16 | Single thruster, twin nacelle, wide array, tapered nozzle, racing afterburner, split engine, micro thruster, wraparound, ion array, vectored thrust, heavy drive, efficient drive, afterburner pod, foundry powerplant, standard drive, light thruster | x4 | 64 |
| Weapon Mounts | 18 | Light/standard/heavy hardpoint, turret platform, missile rack, broadside battery, twin-link, spinal cannon, wing-tip pod, quad mount, concealed bay, point defense, dorsal turret, forward battery, torpedo tube, siege platform, rapid-fire mount, asymmetric mount | x4 | 72 |
| Shield Generators | 12 | Basic emitter, standard gen, compact node, fortress projector, directional barrier, shield dome, phase barrier, heavy projector, ring emitter, layered barrier, distributed array, bubble generator | x4 | 48 |
| Cargo Bays | 10 | Small hold, standard bay, wide hold, bulk freighter bay, tall hold, mega container, refrigerated hold, smuggling compartment, pressurized hold, modular rack | x4 | 40 |
| Crew Quarters | 8 | Bunk room, standard quarters, barracks, officer cabin, luxury suite, compact quarters, extended hab, medical quarters | x3 | 24 |
| Reactor Cores | 8 | Compact reactor, standard core, heavy reactor, overcharged core, efficient cell, capital reactor, shielded core, micro reactor | x3 | 24 |
| Utility | 17 | Sensor array, medical bay, workshop, fuel tanks (small/large/extended), refinery pod, brig, science lab, comms array, drone bay, nav computer, EW suite, tractor beam, life support, escape pod, crew lounge | x3 | 51 |
| Structural | 22 | Square/rectangle connectors (various sizes), L/T/plus shapes, long beams, wing spars, nose points, swept pieces, reinforced bulkheads, armored plates, lightweight frames, wing panels, tail fins, angled connectors, wide plates | x2 | 44 |
| **Total** | **~123** | | | **~415** |

123 unique pixel masks to author. Each is 3-6 lines of text in JSON with a material map. This is a focused content sprint, not a sprite pipeline. With manufacturer variants, the player sees 400+ distinct parts in the catalog.

---

## Canvas Frames & Weight Classes

### Frame Variants

Each weight class from Medium upward offers **frame variants** — different canvas aspect ratios for different ship archetypes. This lets players choose a canvas shape that matches their design intention before they start building. Tiny and Small are fixed (ships that small don't benefit from aspect ratio choice).

| Class | Default Frame | Variant Frame(s) | Rationale |
|-------|--------------|-------------------|-----------|
| **Tiny** | 16×16 (square) | — | Too small for variants to matter |
| **Small** | 24×24 (square) | — | Ditto |
| **Medium** | 32×32 (square) | 40×24 (wide), 24×40 (tall) | Wide = fighter/gunship profile. Tall = shuttle/corvette. Square = balanced. |
| **Large** | 48×48 (square) | 60×36 (wide), 36×60 (tall) | Wide = frigate/cruiser silhouette. Tall = destroyer/escort. |
| **XLarge** | 64×64 (square) | 80×48 (wide), 48×80 (tall) | Wide = battlecruiser/carrier. Tall = dreadnought/heavy hauler. |

**Rules:**
- All frame variants within a weight class have the **same total pixel area** (±5%) — choosing wide vs. square doesn't give you more pixels, it changes the *shape* of your design space
- Weight budgets, module count limits, and slot pools are tied to **weight class**, not frame shape — no mechanical advantage from frame choice, purely a design/silhouette decision
- Frame variant is chosen at the start of a build and cannot be changed mid-build (would invalidate placed modules/pixels). Starting a new build allows a different frame.
- The builder "canvas size" display updates to show the selected frame dimensions

**Why this matters:** A 60×36 wide frame naturally produces ships with broader silhouettes — fighters, cruisers, carriers with wide wingspans. A 36×60 tall frame produces ships with elongated vertical profiles — destroyers, escorts, deep-space haulers. The frame choice is the first design decision the player makes, and it shapes everything that follows.

### Ship Orientation Convention

> **IMPORTANT DESIGN RULE**: Ships face **RIGHT** in the builder canvas. The nose/bow of the ship points toward the right edge of the canvas. The engines/stern point toward the left edge.

This is a hard convention that the entire game depends on:

**Why right-facing:**
- Consistent with the game's side-scrolling combat orientation
- Allows the engine placement rule ("rear 30%") to map to "left 30% of canvas"
- Weapon firing arcs compute from known orientation (front = right, broadside = top/bottom)
- Ship rendering in combat, galaxy map, and HUD can use the build orientation directly without rotation
- Animations (engine glow, weapon fire, shield impacts) are authored relative to a known facing direction

**Builder orientation cues:**
- **Arrow indicator**: a subtle right-pointing arrow or "BOW →" label on the right edge of the canvas, "← STERN" on the left
- **Engine zone shading**: the rear 30% of the canvas (left side) has a very subtle tinted background (e.g., faint warm tone) indicating "engines go here"
- **Nose zone hint**: the front 20% of the canvas (right side) has a faint directional indicator suggesting "this is where you face the enemy"
- **Grid guidelines**: optional toggleable guide lines showing the bow/stern zones
- **First-build tutorial**: explicitly tells the player "your ship faces right — place engines on the left, weapons pointing right"

**How this propagates:**
- Combat view: player ship faces right (toward enemy), enemy ship faces left
- Galaxy map: ship icon faces direction of travel, rotated from the right-facing base
- Cockpit HUD: ship silhouette shown right-facing
- Ship preview in shops/inventory: always right-facing
- Enemy ships in combat: mirrored (left-facing) from their own right-facing builds

### Module Count by Weight Class

| Section | Tiny | Small | Medium | Large | XLarge |
|---------|------|-------|--------|-------|--------|
| Cockpit | 1 (small) | 1 | 1 (std+) | 1 (large) | 1 (large) |
| Engine | 1 | 1-2 | 2 | 2-3 | 3-4 |
| Weapon Mount | 1 | 1-2 | 2-3 | 3-4 | 4-6 |
| Shield Gen | 1 | 1 | 1-2 | 2-3 | 3-4 |
| Cargo Bay | 1 (small) | 1 | 1-2 | 2-3 | 2-4 |
| Crew Quarters | - | - | 1 | 1-2 | 2-3 |
| Reactor | - | - | - | 1 | 1-2 |
| Typical module count | 4-5 | 5-8 | 8-12 | 12-18 | 16-24 |

---

## Combat Integration: Module-Targeted Damage

Modules enable FTL-style subsystem damage:

- Hits are resolved against the pixel they strike
- If the hit pixel belongs to a module, that module takes damage
- Module HP is separate from hull HP
- When a module's HP reaches 0, it is **disabled** (not destroyed):
  - Disabled cockpit: accuracy and evasion penalties
  - Disabled engine: speed drops to near-zero
  - Disabled weapon mount: weapon stops firing
  - Disabled shield gen: shields drop
  - Disabled cargo bay: chance to lose cargo
  - Disabled reactor: all systems degrade
- Modules are repaired after combat (automatic) or at stations (if damaged enough)
- **Severing**: If structural bottleneck is broken, all modules on the severed section are disabled simultaneously

This makes ship layout a tactical decision: where you place your cockpit determines how protected it is. Where you put engines determines if they're vulnerable. Layout IS strategy.

---

## Module Detail: What Makes Each Category Deep

> The goal is 123 base masks. For that to work, each category needs genuine internal variety — not just "same rectangle in three sizes." Here's what makes each category interesting enough to sustain its mask count.

### Cockpits (12 masks)

Cockpits vary on three axes: **profile** (how much space they take), **glass-to-hull ratio** (visibility vs. protection), and **shape** (wide vs. tall vs. compact). A racing cockpit is a flat 4x2 sliver that's mostly glass — minimal weight, maximum vulnerability. An armored command is a thick 4x4 block with a tiny glass slit — heavy, protected, limited sensor range. An observation dome has glass on three sides for explorer builds. Each cockpit shape reads differently on the ship silhouette.

### Engines (16 masks)

Engine variety comes from **nozzle configuration** and **footprint shape**. A single thruster (3x2) is a compact rectangle. A twin nacelle (4x4) has two exhaust columns with hull between them — wider but splits thrust visually. A wide array (6x2) is a flat row of exhaust ports across the stern. A tapered nozzle (3x4) narrows toward the back. A split engine (5x3) has a gap in the center — distinctive silhouette, creates a concavity. These aren't just size variants; they create genuinely different ship stern profiles.

### Weapon Mounts (18 masks)

The largest category because weapons are the most expressive combat choice. Key differentiators: **shape** (protruding barrels vs. recessed bays vs. flat platforms), **aspect ratio** (a 2x6 spinal cannon runs along the ship's centerline; a 5x2 broadside battery extends laterally), and **intended placement** (wing-tip pods are small and meant for extremities; dorsal turrets are tall and meant for the ship's spine). A torpedo tube is long and narrow. A quad mount is a chunky square. A concealed bay is flush with the hull. Each creates different silhouette possibilities and implies different combat roles.

### Shield Generators (12 masks)

Shield variety comes from **coverage pattern** and **size**. Distributed nodes (2x2) are small — you place 3-4 around the ship for even coverage. A fortress projector (4x4) is one big block — concentrated but easier to protect. A directional barrier (4x2) is flat and projects primarily in one direction — place it facing where you expect fire. A ring emitter has a hollow center pixel — distinctive look, omnidirectional projection. Shield layout directly shapes defensive strategy.

### Cargo Bays (10 masks)

Cargo is the trading game's core loop made spatial. A small hold (3x2) barely changes your silhouette. A mega container (6x4) dominates the ship's interior — you're clearly a trader. A tall hold (3x4) fits narrow hull designs. A modular rack (4x2) is external-mount style — cheap cargo at the cost of hull exposure. The smuggling compartment (2x2) is deliberately tiny because its value is concealment, not volume. Refrigerated and pressurized holds have unique visual materials (frost pixels, sealed panels) that make them identifiable.

### Structural (22 masks)

This is the LEGO collection, and it needs the most variety because structural pieces are the most-placed modules. They need to cover every spatial situation:
- **Connectors** (2x2, 2x3, 3x2, 3x3): small linking pieces for tight spaces
- **Beams** (6x2, 8x2): long pieces for spines and wing spars
- **Shapes** (L, T, plus, angled): for corners, junctions, and non-rectangular layouts
- **Specialized**: reinforced bulkhead (high HP, heavy), lightweight frame (low HP, light), armored plate (directional protection), wing panel (thin, wide, meant for extremities)

Structural modules are functionally simple (just hull HP and weight) but their shape variety is what enables creative ship silhouettes. A player building swept wings uses wing panels and angled connectors. A player building a brick uses squares and rectangles. The structural catalog IS the creative toolkit.

### Utility (17 masks)

Each utility module is functionally unique, which drives the variety naturally. A sensor array looks different from a medical bay which looks different from a fuel tank. Visual identity per function:
- **Sensor array**: antenna/dish pixels (bright, protruding)
- **Medical bay**: cross-shaped highlight pattern
- **Workshop**: tool/workbench-toned interior
- **Fuel tanks**: cylindrical shape (rounded top/bottom rows), ice-blue interior
- **Science lab**: multi-colored instrument pixels
- **Communications array**: antenna + screen pixels
- **Drone bay**: open bay (concavity), launch pad pixels
- **Electronic warfare suite**: dark, angular, threatening

---

## The Module Shop Experience

> How players browse, compare, and acquire modules is as important as the modules themselves. This should feel like Armored Core's shop — browsing a catalog of parts with stats, prices, and manufacturer identity.

### Station Module Shops

Each station offers a selection of modules based on:
- **System location**: frontier stations have basic + salvage parts; core systems have full catalogs
- **Faction alignment**: Guild-aligned stations stock Talon and Foundry modules; Alliance stations stock Meridian and Sable
- **Station type**: shipyards have full catalogs; trading posts have cargo/utility; military stations have weapons/shields

### Shop UI

- Browse by category (same tabs as builder)
- Each module shows: pixel art preview (rendered at scale), name, manufacturer, stats, weight, cost
- **Compare to equipped**: if you have a cockpit, hovering a new cockpit shows stat deltas (green arrows up, red arrows down)
- **"Try before you buy"**: preview button opens a mini-builder view showing the module placed on your current ship (but not committed)
- **Locked modules visible**: modules you can't buy yet (faction rep too low, quest not done) are shown grayed out with unlock condition — this drives player goals ("I need Trusted with the Guild to get that Talon Quad Mount")

### Module Inventory

Players own modules in an **inventory**, not just a "currently installed" set. You buy a Foundry Heavy Drive at one station and keep it in your parts locker even if you're not using it. When you enter the builder, your inventory is your available parts list, supplemented by the station's shop if you're docked.

This creates the Armored Core "garage" feel: you accumulate parts over time, swapping them in and out as your strategy evolves. Selling old parts back at a discount recovers some credits.

---

## Enemy Ships & NPCs in the Module System

> Players shouldn't be the only ones with module-based ships. Enemy ships need to feel like they were built from the same system — this reinforces that modules are "real" in the game world.

### Enemy Ship Templates

Each EnemyTemplate (existing system) gets a module-based build definition:
- **Template approach**: define a module layout + hull pixels for each enemy archetype
- **Variation**: randomize manufacturer variants, hull material, and minor module swaps within the archetype
- **Faction identity**: Crimson Reach pirates use Salvage Rat parts (patchwork, mismatched). Guild enforcers use Talon weapons + Reyes-Kowalski hulls. Each faction's ships look cohesive.

### Combat Readability

When fighting an enemy, their module layout is partially visible:
- Module types are **not** labeled on enemy ships (you don't see "cockpit" floating over their bridge)
- But module visual materials are distinct enough that experienced players learn to read them: "those cyan pixels are their shield generator, I should focus fire there"
- Targeting system (if player has sensor modules) can highlight enemy module positions — a reward for building sensor-heavy ships

---

## Starter Ships & New Player Experience

### First Ship (Tutorial Build)

New players don't start with a blank canvas. They start with a **guided first-build tutorial**:

1. "Welcome to the Breakstone shipyard. Let's build your first ship."
2. "Start by placing your cockpit. Drag the Scout Pod to the center of the grid." (Only cockpits available, everything else grayed out)
3. "Now your ship needs an engine. Place the Light Thruster at the rear." (Only engines available)
4. "Every ship needs weapons. Place a Light Hardpoint near the front." (Weapons available)
5. "Shields will keep you alive. Place the Basic Emitter." (Shields available)
6. "You're a trader — you need cargo space. Place the Small Hold." (Cargo available)
7. "Now connect your modules with hull plating. Use the paint tool to shape your ship." (Hull mode unlocked, shape stamps available)
8. "Your ship is ready. Give it a name." → Player names their ship → Undock

This teaches the builder in 2-3 minutes, results in a flyable ship, and establishes the module-then-hull workflow. The tutorial ship is deliberately basic — motivation to upgrade comes immediately.

### Preset Ships (Skip the Build)

For players who want to fly NOW, offer 3-4 **preset ships** per weight class:
- "Courier" — balanced starter (small cockpit, light engine, 1 weapon, 1 shield, standard cargo)
- "Fighter" — combat-focused (armored cockpit, standard engine, 2 weapons, 1 shield, small cargo)
- "Trader" — cargo-focused (standard cockpit, efficient engine, 1 weapon, 1 shield, bulk cargo)

Presets are pre-built module layouts with hull pixels already shaped. Players can modify them in the builder at any time. Presets serve as "here's what a good ship looks like" examples.

---

## Drafts, Sharing & Community

### Draft Saves

Players can save unfinished builds as **drafts** — full build layouts stored locally without paying credits.

- **Save draft**: from the builder, hit "Save Draft" → name the draft → layout saved (modules, hull pixels, frame variant, weight class)
- **Load draft**: from the builder entry screen, choose "Load Draft" alongside "New Build" and "Load Preset"
- **Draft limit**: 20 drafts per player (generous, prevents unbounded save bloat)
- **Dream builds**: players can design ships they can't afford yet. Save as draft, go earn credits, come back and build it. The draft is a goal to work toward.
- **Iteration**: save multiple versions of the same design ("Kestrel v1", "Kestrel v2") while experimenting

### Build Sharing (Import/Export)

Players can share ship designs as **compact text codes** — no server infrastructure needed, works through Discord, Reddit, forums, or any text channel.

**Export flow:**
1. From the builder (or viewing a completed ship), hit **"Share Build"**
2. Game serializes the build: modules (IDs, positions, rotations), hull pixels (positions, materials), frame variant, weight class
3. Compress (zlib) → Base64 encode → prefix with version tag
4. Result: a shareable string like `AURELIA:1:eJzLSM3JyVcIzy9KSQEADiQDSA==`
5. Auto-copied to clipboard with confirmation toast: "Build code copied!"
6. Player pastes it in Discord, Reddit, a forum post, texts it to a friend

**Import flow:**
1. From the builder entry screen, hit **"Import Build"**
2. Paste a build code into the text field
3. Game decodes → validates format and version → loads the build into the builder
4. **Blueprint check**: if the imported build uses modules the player hasn't unlocked:
   - Build still loads and displays (you can SEE the design)
   - Missing modules are highlighted with a red border and lock icon
   - A **"Missing Blueprints"** panel lists exactly what you need to unlock:
     ```
     Missing Blueprints (3):
     ✗ Talon Quad Mount — Purchase at Guild-aligned shipyard (8,000 CR)
     ✗ Sable Phase Barrier — Requires Trusted with Collective
     ✗ Foundry Capital Reactor — Quest: "The Iron Heart"
     ```
   - Confirm button disabled until all blueprints owned
   - This turns an imported build into a **shopping list / goal list** — the player now knows exactly what to chase
5. If all blueprints owned: build loads normally, player can modify it, and pays instantiation costs at checkout

**Code format details:**
- Versioned: `AURELIA:<version>:<payload>` — allows future format changes without breaking old codes
- Compact: a typical Medium ship encodes to ~100-200 characters (easily fits in a Discord message)
- Deterministic: same build always produces the same code
- Validated on import: corrupt/tampered codes rejected gracefully with "Invalid build code" message
- Does NOT include: player name, credits, unlock state, equipment installed in slots — just the structural layout

### Security Hardening (Import Validation)

> **IMPORTANT**: Build codes are untrusted external input. A malicious actor could craft a code designed to crash the game, exploit memory, or inject unexpected data. All import processing must be defensive.

**Deserialization safety:**
- **Never use `pickle`, `eval`, `exec`, or any code execution** during import. Decode is strictly: base64 decode → zlib decompress → `json.loads()` with a strict schema validator. Nothing else.
- **JSON-only deserialization**: the payload is always JSON. No Python object serialization. `json.loads()` is safe against code execution (unlike pickle).
- **Schema validation before use**: after JSON parse, validate every field against an explicit allow-list schema before constructing any game objects:
  - `weight_class` must be one of the 5 known weight class strings
  - `frame_variant` must be one of: `"square"`, `"wide"`, `"tall"`
  - `modules` must be a list; each entry must have: `module_id` (string, must exist in loaded module catalog), `x` (int), `y` (int), `rotation` (int, 0-3), `flipped` (bool)
  - `hull_pixels` must be a list; each entry must have: `x` (int), `y` (int), `material_id` (string, must exist in loaded hull materials)
  - **Any field that fails validation → reject the entire code** with a generic "Invalid build code" message (don't leak specifics about why it failed to potential attackers)

**Size limits:**
- **Maximum payload size**: reject base64 strings longer than 50KB (an XLarge ship with maximum pixels is well under this; anything larger is suspicious or corrupted)
- **Maximum decompressed size**: after zlib decompress, reject if decompressed data exceeds 200KB (prevents zip bomb attacks)
- **Maximum module count**: reject builds with more than 50 modules (well above the XLarge max of ~24)
- **Maximum hull pixel count**: reject builds with more than 5,000 hull pixels (well above any valid build)
- **Coordinate bounds**: all x/y values must be within canvas bounds for the declared weight class. Reject any out-of-bounds coordinates.

**ID validation (critical):**
- Module IDs in the imported build must **exactly match** IDs in the loaded module catalog (`get_data_loader().ship_modules`). If a module_id doesn't exist, reject. This prevents injection of arbitrary strings into the game's data structures.
- Hull material IDs must exactly match loaded hull material IDs. Same principle.
- **No dynamic ID construction**: never concatenate or interpolate imported strings into file paths, database queries, or any system call. IDs are lookup keys only.

**Resource exhaustion protection:**
- Wrap the entire import pipeline in a try/except with a timeout or operation limit
- If `zlib.decompress()` fails → "Invalid build code"
- If `json.loads()` fails → "Invalid build code"
- If schema validation fails → "Invalid build code"
- Log import attempts at DEBUG level (not the payload content, just success/failure and code length) for diagnostics

**What we explicitly do NOT do:**
- No file I/O based on imported data (no loading files by imported paths)
- No network calls based on imported data
- No eval/exec of any imported strings
- No HTML/rich text rendering of imported strings (prevents XSS if we ever add web features)
- No storing raw imported payloads in save files (only store the validated, reconstructed build data)

**Why text codes instead of file export:**
- Zero friction: copy, paste, done. No "find the file, email it, put it in the right folder" workflow
- Works everywhere: Discord, Reddit, Twitter, text messages, forum posts, in-game chat (future)
- Compact: a single line of text, not a file attachment
- Discoverable: players see codes in community spaces and think "I want to try that"

### Community Dynamics This Enables

- **Build guides**: "Here's my 20K budget trader that can handle Act One — AURELIA:1:..."
- **Challenge builds**: "Beat the Corsair King with this tiny fighter — AURELIA:1:..."
- **Fashion builds**: "Check out this symmetric dreadnought I spent an hour on — AURELIA:1:..."
- **Theory-crafting**: community debates optimal layouts for different playstyles
- **Goal-setting**: importing a build you can't afford yet gives you a concrete progression target
- **Content creation**: streamers and YouTubers share builds with audiences

---

## Sound & Feel

> The builder should feel tactile and satisfying. Every action gets audio feedback.

| Action | Sound | Visual |
|--------|-------|--------|
| Place module | Solid metallic *clunk* — heavy, satisfying | Module snaps into position, brief white flash on edges |
| Rotate/Flip module (preview) | Light mechanical *click* | Ghost preview rotates smoothly (not instant snap) |
| Remove module | Hydraulic *release* hiss | Module lifts off grid, fades out |
| Paint hull pixel | Soft *tap* | Pixel fills with color, subtle ripple from placement point |
| Erase hull pixel | Light *scrape* | Pixel fades out |
| Fill hull area | Rapid *tap-tap-tap* cascade | Pixels fill outward from click point in a wave |
| Mirror toggle | Distinct *activation* chime | Mirror line appears/disappears with a subtle glow |
| Requirement met | Positive *ding* | Checklist item turns green with a brief shine |
| All requirements met | Satisfying *completion chord* | Confirm button pulses, "Ready to fly" text appears |
| Invalid placement | Soft *buzz* | Ghost preview flashes red briefly |
| Confirm build | Industrial *assembly sequence* (2-3 seconds) | Ship assembles piece by piece with sparks — then zooms out to show the full ship |

---

## Undo/Redo System

- **Action stack**: every module place, module remove, hull pixel change, fill operation is a discrete undo-able action
- **Stack depth**: 30 actions (increased from current 20 — module operations are bigger steps)
- **Undo**: Ctrl+Z or prominent UNDO button
- **Redo**: Ctrl+Y or prominent REDO button
- **Clear all**: separate action with confirmation dialog ("Clear all modules and hull pixels?")
- **Module undo granularity**: placing a module is one action; removing is one action; moving (remove + place) is two actions (both undo-able)

---

## Implementation Phases

> Each phase ends with a **testable milestone** — something we can run, see, and verify before moving on. Phases are designed to be completable in 1-3 focused sessions each. Total scope: 9 phases.

### Design Decisions to Resolve Before Implementation

These open questions from the design section must be locked down before Phase 1:

| Decision | Recommendation | Status |
|----------|---------------|--------|
| Module stats model | Fixed stats per module (not per-pixel accumulation) | **Decided** |
| Hull material count | 4 types (Light Alloy, Standard Plate, Heavy Armor, Stealth Composite) | **Decided** |
| Canvas frame variants | Square default + Wide/Tall for Medium+ | **Decided** |
| Ship orientation | Right-facing (bow right, stern left) | **Decided** |
| Module pixel customization | Recolor only (tint hull pixels, not functional pixels) — Phase 13 | **Decided** |
| Equipment slots | Slots come with modules (no manual slot designation) | **Decided** |
| Module economics | Blueprints (unlock once) + instantiation cost (pay per use, 80% refund on removal) | **Decided** |
| Build sharing | Base64-encoded build codes with security hardening — Phase 11 | **Decided** |
| Station module shops | Per-station module catalogs with faction/location variety — Phase 12 | **Decided** |
| Damage overkill | Excess propagates to hull + 30% chain to adjacent modules — Phase 14 | **Decided** |
| Power budget | Defer further (reactor provides stat but not consumed yet) | **Deferred** |

---

### Phase 1: Data Foundation
> **Milestone**: `ShipModule` loads from JSON, rotates, flips, and serializes correctly. All tests pass.

**New files:**
- `spacegame/models/ship_module.py` — `ShipModule` and `PlacedModule` dataclasses
- `data/ships/modules.json` — initial module catalog
- `data/ships/module_materials.json` — visual materials for module internals
- `tests/test_models/test_ship_module.py`

**Work:**
- [ ] `ShipModule` dataclass: id, name, category, manufacturer, pixel_mask_compact (multi-char), material_map, provides (slot_type, stats), weight, cost, unlock metadata
- [ ] `PlacedModule` dataclass: module_id, x, y, rotation (0/1/2/3), flipped (bool)
- [ ] Multi-character mask parsing: `"HGGH"` → list of (local_x, local_y, material_id) tuples
- [ ] Rotation logic: 0°/90°/180°/270° — rotate the mask grid, remap coordinates
- [ ] Flip logic: horizontal mirror of mask
- [ ] `resolved_pixels(placed_module, module_data)` → list of PlacedPixel at world coordinates
- [ ] Module-specific visual materials: cockpit_glass, console_panel, exhaust_port, weapon_barrel, shield_emitter, sensor_dish, cargo_interior, module_hull
- [ ] Manufacturer hull color definitions (6 manufacturers × color_primary/accent/highlight)
- [ ] DataLoader integration: `_parse_ship_modules()`, `_parse_module_materials()`
- [ ] Initial module catalog: **~20 modules** covering every mandatory category (2-3 per category). Enough to build one valid ship per weight class.
- [ ] Serialization: `ShipModule.to_dict()` / `from_dict()`, `PlacedModule.to_dict()` / `from_dict()`

**Tests (TDD — write these first):**
- [ ] Module loading from JSON (all fields parse correctly)
- [ ] Mask parsing: multi-char mask → correct pixel list with material assignments
- [ ] Rotation: 90° CW produces correct coordinate transform; 4 rotations = identity
- [ ] Flip: horizontal mirror produces correct coordinates; double flip = identity
- [ ] Rotation + flip composition: all 8 orientations produce distinct, correct results
- [ ] resolved_pixels: placed at (5, 3) with rotation → correct world coordinates and materials
- [ ] Serialization round-trip: to_dict → from_dict preserves all fields
- [ ] DataLoader loads modules and module_materials without errors
- [ ] Manufacturer color definitions load for all 6 manufacturers

**Not in this phase:** No ShipBuild changes, no validation, no rendering, no view changes.

---

### Phase 2: Build Model + Validation + Stats
> **Milestone**: Can programmatically construct a `ShipBuild` from modules + hull pixels, validate it, compute stats, serialize/deserialize it. All tests pass.

**Modified files:**
- `spacegame/models/ship_build.py` — updated ShipBuild, new validation, new stats
- `tests/test_models/test_ship_build.py` — extended

**Work:**
- [ ] Updated `ShipBuild`: add `modules: list[PlacedModule]` alongside existing `pixels: list[PlacedPixel]` (hull pixels)
- [ ] `resolve_all_pixels()` → flattens module pixels + hull pixels into unified pixel list
- [ ] Canvas frame variants: weight class now includes frame options (square/wide/tall for Medium+)
- [ ] **Placement validation** (`can_place_module()`):
  - Bounds check (module footprint within canvas after rotation/flip)
  - Overlap check (no module-module pixel overlap, no module-hull pixel overlap)
  - Weight budget check (sum of module weights + hull pixel weights ≤ max)
- [ ] **Connectivity validation** (`validate_connectivity()`):
  - All filled pixels (module + hull) form one 4-connected component
  - Flood fill from any pixel, verify all pixels reached
- [ ] **Requirements validation** (`validate_requirements()`):
  - Has exactly 1 cockpit module
  - Has at least 1 engine module
  - Has at least 1 weapon mount module
  - Has at least 1 shield generator module
  - Has at least 1 cargo bay module
  - Has crew quarters if Medium+ (conditional)
  - Has reactor core if Large+ (conditional)
  - At least 1 engine in rear 30% of ship bounding box
- [ ] **Stats computation** (updated `ShipStatsComputer`):
  - Module stats: sum fixed stats from all placed modules (hull HP, shields, armor, evasion, speed, cargo, crew capacity)
  - Hull pixel stats: sum material contributions from hull pixels (simplified 4-material set)
  - Combined stats with weight ratio modifiers (existing system)
  - Defensive identity detection updated for module-based builds
- [ ] **Serialization**: updated `to_dict()` / `from_dict()` includes modules list
  - Backward compatible: old saves without modules still load (modules list defaults to empty)
- [ ] Equipment slot derivation: slots come from modules, not manual placement. `ShipBuild.get_slots()` aggregates slot info from all placed modules.

**Tests (TDD):**
- [ ] Build with modules + hull pixels resolves to correct unified pixel list
- [ ] Placement: valid module placement succeeds
- [ ] Placement: out-of-bounds fails with message
- [ ] Placement: overlapping modules fails with message
- [ ] Placement: weight exceeded fails with message
- [ ] Connectivity: connected build passes
- [ ] Connectivity: disconnected build fails
- [ ] Requirements: all mandatory modules present → passes
- [ ] Requirements: missing cockpit → fails with "Ship requires a cockpit"
- [ ] Requirements: engine not in rear 30% → fails
- [ ] Requirements: Medium build without crew quarters → fails
- [ ] Stats: module stats + hull pixel stats sum correctly
- [ ] Stats: weight ratio modifiers apply
- [ ] Serialization round-trip with modules
- [ ] Backward compatibility: old save format loads (empty modules list)
- [ ] Frame variants: Medium wide (40×24) has correct canvas dimensions
- [ ] Slot derivation: weapon mount module provides weapon slot at correct position

**Not in this phase:** No rendering, no view changes. Pure model + validation logic.

---

### Phase 3: Rendering Pipeline
> **Milestone**: A module-based ShipBuild renders correctly through ShipComposite. Module pixels are visually distinct from hull pixels. Can see a rendered ship in-game.

**Modified files:**
- `spacegame/engine/ship_composite.py`
- `data/ships/module_materials.json` (texture rules)
- `tests/test_engine/test_ship_composite.py`

**Work:**
- [ ] `ShipComposite` updated to call `resolve_all_pixels()` on the build before rendering
- [ ] New material texture rules in pipeline step 4 for module visual materials:
  - `cockpit_glass`: blue tint, subtle reflection band on top row
  - `console_panel`: dim green/amber dot pattern (every other pixel)
  - `exhaust_port`: dark base, warm glow tint (ties into engine glow step 7)
  - `weapon_barrel`: dark gunmetal, single bright highlight pixel
  - `shield_emitter`: bright cyan base, shimmer on alternate rows
  - `sensor_dish`: light metallic, bright center pixel
  - `cargo_interior`: dark base, subtle grid pattern (crates)
  - `module_hull`: per-manufacturer color (lookup from manufacturer ID)
- [ ] Manufacturer hull color rendering: `module_hull` material reads manufacturer from module data to select color_primary/accent/highlight
- [ ] Verify: existing 7-step pipeline produces correct output with mixed module + hull pixels
  - Panel lines between module and hull pixels
  - Edge highlights on ship silhouette
  - Outline around entire ship (not per-module)
  - Engine glow on engine module exhaust_port pixels
- [ ] Module boundary overlay (builder-only): optional dashed outline around each module's bounding box + small category icon
- [ ] Cache invalidation: composite invalidates when modules change

**Tests:**
- [ ] Composite renders a module-based build without errors
- [ ] Module pixels use correct material colors
- [ ] Manufacturer color variants produce different visual output
- [ ] Mixed module + hull pixel build renders with proper panel lines at boundaries
- [ ] Engine glow activates on exhaust_port pixels in engine modules
- [ ] Boundary overlay generates correct rectangles for placed modules

**Visual verification**: After this phase, create a test script that builds a simple ship (cockpit + engine + weapon + shield + cargo + hull pixels) and renders it to screen. First time we SEE the new system working.

---

### Phase 4: Builder View — Module Placement
> **Milestone**: Player can open the builder, browse a module catalog, and place/rotate/flip/remove modules on the grid. Ship renders live as they build.

**Modified files:**
- `spacegame/views/ship_builder_view.py` — major overhaul
- New: `spacegame/views/components/module_catalog.py` (reusable catalog widget)

**Work:**
- [ ] **Screen layout overhaul**: left catalog panel (~200px), center canvas, right info panel (~180px), bottom toolbar
- [ ] **Canvas orientation cues**:
  - "← STERN" label on left edge, "BOW →" on right edge
  - Engine zone tinting: subtle warm overlay on left 30% of canvas
  - Optional grid guidelines (toggleable)
- [ ] **Frame variant selection**: weight class screen now shows frame options (Square/Wide/Tall) for Medium+ with visual aspect ratio preview
- [ ] **Module catalog panel**:
  - Category tabs (Cockpits, Engines, Weapons, Shields, Cargo, Utility, Structural)
  - Scrollable module list per category
  - Each entry: pixel art preview (rendered at 2-3x), name, weight, cost
  - Manufacturer filter dropdown
  - "Unlocked only" toggle (show locked modules grayed out with unlock hint)
- [ ] **Module placement mode**:
  - Click module in catalog to select → cursor becomes ghost preview on grid
  - Ghost preview: semi-transparent module at cursor position, snapped to grid
  - **R** to rotate preview 90° CW, **Q** to flip horizontally — preview updates in real time
  - Click to place (if valid) — solid placement with brief visual feedback
  - Invalid placement: ghost turns red, click does nothing
  - Right-click placed module to select it → highlight border appears
  - **Delete/Backspace** to remove selected module
  - Drag to reposition selected module (pick up → ghost → place)
- [ ] **Requirements checklist** (right panel): live-updating checkmarks for each mandatory module category
- [ ] **Weight budget bar**: always visible in top bar, updates with each placement
- [ ] **Live ship rendering**: canvas shows the ship as it's being built (ShipComposite re-renders on each change)
- [ ] **Zoom/Pan**: mouse wheel zooms canvas, middle-click drags to pan (carry over from existing builder)

**Tests:**
- [ ] Module catalog loads and displays correct modules per category
- [ ] Module placement at valid position succeeds and updates build
- [ ] Module placement at invalid position (overlap, OOB, overweight) is rejected
- [ ] Rotation and flip update ghost preview correctly
- [ ] Module removal updates build and frees weight budget
- [ ] Requirements checklist updates when modules are added/removed
- [ ] Frame variant selection produces correct canvas dimensions

---

### Phase 5: Builder View — Hull Pixels + Tools + Polish
> **Milestone**: Full builder experience. Player can place modules, paint hull pixels, use all tools, undo/redo, and confirm a build. A complete ship can be built and flown.

**Modified files:**
- `spacegame/views/ship_builder_view.py` — hull mode, tools, polish

**Work:**
- [ ] **Mode toggle**: prominent [MODULE MODE] / [HULL MODE] toggle button in top bar + **Tab** hotkey
  - Mode switch clearly changes left panel content and available tools
  - Active mode visually highlighted
- [ ] **Hull pixel mode**:
  - Left panel switches from module catalog to material palette (4 large color swatches)
  - Material selection: click swatch to select active material
- [ ] **Tools toolbar** (bottom bar, prominent labeled buttons with hotkey hints):
  - **Pencil** (P): single pixel placement
  - **Eraser** (E): single pixel removal
  - **Fill** (F): flood fill empty area with active material
  - **Shape Stamp** (S): opens shape sub-palette (existing geometric shapes library), stamp onto grid
  - **Mirror** (X): toggle left-right symmetry mode — mirror line visible on canvas
  - All buttons show icon + text label + hotkey
  - Active tool highlighted
- [ ] **Connectivity feedback**: hull pixels that would create disconnection show red preview; valid placements show green
- [ ] **Undo/Redo system**:
  - Action stack (depth 30): each module place/remove, hull pixel paint, fill, stamp is one action
  - **Ctrl+Z** / Undo button, **Ctrl+Y** / Redo button
  - Prominent buttons in top bar, always visible
- [ ] **Stats panel** (right panel, below checklist):
  - Live-updating: Hull HP, Shields, Armor, Evasion, Speed, Cargo, Fuel Range, Crew Capacity
  - Computed from modules + hull pixels via ShipStatsComputer
  - Updates on every build change
- [ ] **Confirm build flow**:
  - All requirements met → Confirm button enabled (pulses or glows)
  - Requirements not met → Confirm button disabled, unmet items highlighted red
  - Click Confirm → name dialog → ship build saved to player
  - Clear All button with confirmation dialog
  - **Save Draft** button: save current layout without paying (exits builder, layout preserved)
- [ ] **Module info on hover**: hover a placed module to see tooltip (name, manufacturer, stats, weight)
- [ ] **Overlay toggles** (right panel):
  - Module boundaries (dashed outlines)
  - Structural integrity heat map (if implemented in Phase 6)
  - Center of mass crosshair (if implemented in Phase 6)

**Tests:**
- [ ] Mode toggle switches between module and hull panels
- [ ] Hull pixel placement with each material works
- [ ] Fill tool fills connected empty area correctly
- [ ] Mirror mode places symmetric pixels
- [ ] Undo reverses last action; redo re-applies it
- [ ] Stats update correctly after hull pixel changes
- [ ] Confirm button disabled when requirements unmet
- [ ] Confirm button enabled when all requirements met
- [ ] Full build → confirm → ship saved to player with correct stats

**Integration test**: Build a complete ship from scratch (modules + hull pixels), confirm, verify it appears correctly in cockpit HUD, galaxy map, and combat view.

---

### Phase 6: Physics Constraints + Overlays
> **Milestone**: Builder shows structural integrity heat map, center of mass, hull efficiency, and frontal profile. These metrics feed into stat computation, creating meaningful shape consequences.

**New files:**
- `spacegame/models/ship_physics.py` — constraint computations
- `tests/test_models/test_ship_physics.py`

**Work:**
- [ ] **Structural integrity analysis**:
  - Find articulation points via iterative DFS on the pixel adjacency graph
  - Identify bottleneck zones (clusters of articulation points between larger masses)
  - Score each pixel: 0 (interior, safe) to 1.0 (critical single-point-of-failure)
  - Heat map overlay: green (0) → yellow (0.3-0.6) → red (0.7+)
- [ ] **Center of mass computation**:
  - Weighted average of all pixel positions (weight = material weight or module weight / pixel count)
  - Compare to geometric center of ship's bounding box
  - Express as percentage offset (0% = perfect center, 50% = extreme edge)
  - Crosshair overlay on canvas showing CoM position
  - Balance rating: Balanced (<15%), Off-balance (15-30%), Severely off-balance (>30%)
- [ ] **Hull efficiency computation**:
  - Count interior pixels (all 4 neighbors filled) vs. perimeter pixels
  - Ratio = interior / total
  - Perimeter pixels contribute ~75% of normal stats; interior contribute 100%
- [ ] **Frontal profile computation**:
  - Ship's filled bounding box width = frontal cross-section
  - Narrower → evasion bonus; wider → evasion penalty
  - Scale: compare to canvas width as reference
- [ ] **Wire into stats**: ShipStatsComputer applies CoM balance modifier, hull efficiency modifier, and frontal profile modifier to final stats
- [ ] **Builder overlays**:
  - Toggle buttons in right panel for each overlay
  - Heat map renders as semi-transparent color overlay on ship pixels
  - CoM renders as crosshair with offset percentage label
  - Overlays update live as build changes
- [ ] **Warnings panel**: non-blocking advisory text below stats
  - "Center of mass is 23% off-center — handling penalty applies"
  - "Structural bottleneck detected at (12, 8) — risk of severing in combat"
  - "Cockpit is on the hull exterior — consider protecting it with surrounding modules"

**Tests:**
- [ ] Solid rectangle has 0 articulation points
- [ ] H-shape (two blocks connected by 1-pixel bridge) correctly identifies the bridge as bottleneck
- [ ] Symmetric ship has CoM at geometric center (0% offset)
- [ ] Ship with heavy modules on one side has measurable CoM offset
- [ ] Interior pixel count correct for known shapes (e.g., 3×3 solid = 1 interior, 8 perimeter)
- [ ] Hull efficiency modifier applies correctly to stats
- [ ] Frontal profile modifier applies correctly to evasion
- [ ] CoM balance modifier applies correctly to evasion
- [ ] Overlays render without errors on various ship configurations

---

### Phase 7: Content Sprint — Full Module Catalog
> **Milestone**: All ~123 base module masks authored. Manufacturer variants defined. Balance pass complete. A rich parts catalog for the player.

**Modified files:**
- `data/ships/modules.json` — expanded from ~20 to ~123 modules
- `data/ships/module_manufacturers.json` (new) — manufacturer definitions and variant rules

**Work:**
- [ ] **Cockpits** (12 masks): compact pod, standard bridge, wide bridge, armored command, tall command tower, observation dome, stealth helm, war bridge, racing cockpit, luxury suite, split canopy, exploration bridge
- [ ] **Engines** (16 masks): single/light/standard/heavy/racing/wide array/twin nacelle/split/tapered/wraparound/micro/afterburner/foundry powerplant/efficient/vectored/ion array
- [ ] **Weapon Mounts** (18 masks): light/standard/heavy hardpoints, turret platform, missile rack, broadside battery, twin-link, spinal cannon, wing-tip pod, quad mount, concealed bay, point defense, dorsal turret, forward battery, torpedo tube, siege platform, rapid-fire, asymmetric
- [ ] **Shield Generators** (12 masks): basic emitter, standard gen, compact node, fortress projector, directional barrier, shield dome, phase barrier, heavy projector, ring emitter, layered barrier, distributed array, bubble generator
- [ ] **Cargo Bays** (10 masks): small hold, standard bay, wide hold, bulk freighter, tall hold, mega container, refrigerated, smuggling compartment, pressurized, modular rack
- [ ] **Crew Quarters** (8 masks): bunk room, standard quarters, barracks, officer cabin, luxury suite, compact quarters, extended hab, medical quarters
- [ ] **Reactor Cores** (8 masks): compact, standard, heavy, overcharged, efficient cell, capital, shielded core, micro reactor
- [ ] **Utility** (17 masks): sensor array, medical bay, workshop, fuel tanks (×3 sizes), refinery pod, brig, science lab, comms array, drone bay, nav computer, EW suite, tractor beam, life support, escape pod, crew lounge
- [ ] **Structural** (22 masks): connectors (×4 sizes), rectangles (×3), squares (×3), L/T/plus shapes, long beams (×2), wing spar, nose point, swept piece, reinforced bulkhead, armored plate, lightweight frame, wing panel, tail fin, angled connector, wide plate
- [ ] **Manufacturer variant definitions**: for each manufacturer, define hull color set + texture style. Each base mask generates variants for applicable manufacturers (not all modules available from all manufacturers).
- [ ] **Balance pass**: review module stats across tiers. Ensure meaningful trade-offs within each category. No module should be strictly better than another — side-grades, not upgrades (lighter but less HP, more shields but heavier, etc.)
- [ ] **Names and descriptions**: every module gets a proper name and 1-line description with flavor. Follow writing style guide (no em-dashes, no GenAI tropes).
- [ ] **Unlock assignments**: distribute modules across unlock sources (starter, purchase, faction, salvage, quest, boss, black market, mining). Ensure each source has meaningful rewards. Pacing: ~20 modules at game start, ~60 by mid-game, ~100+ by late-game.

**Tests:**
- [ ] All 123 modules load without errors
- [ ] Every module has valid pixel_mask_compact (no unknown characters, no empty masks)
- [ ] Every material_map character in every mask has a valid material reference
- [ ] No two modules share the same ID
- [ ] Every mandatory category has at least 2 modules available at game start (starter unlock)
- [ ] Balance: no module in a category is strictly dominant on all stat axes
- [ ] Every manufacturer has at least 5 modules
- [ ] Rotation/flip works correctly for all 123 masks (spot check + property tests)

---

### Phase 8: Progression Integration
> **Milestone**: Modules are bought at shops, unlocked through faction/quests/salvage, and stored in player inventory. Starter presets work. Old saves migrate gracefully.

**Modified files:**
- `spacegame/models/builder_discovery.py` — reworked for modules
- `spacegame/models/player.py` — module inventory
- `spacegame/models/ship_presets.py` — module-based presets
- `spacegame/save_manager.py` — save format update
- Various views (shop, shipyard)

**Work:**
- [ ] **Blueprint catalog**: Player unlocks module blueprints (by ID). Blueprints are permanent — unlock once, instantiate unlimited times. Catalog stored in Player/Progression data.
- [ ] **Instantiation cost tracking**: builder computes total build cost from module instantiation costs (with manufacturer multipliers) + hull pixel costs. Pay-on-confirm model. Rebuild pays net delta with 80% refund on removed modules.
- [ ] **Station shop integration**: Each station's shop screen includes a "Ship Parts" tab. Available blueprints based on system location, faction alignment, station type. Purchase unlocks the blueprint permanently.
- [ ] **Faction reputation gating**: manufacturer modules locked behind faction rep thresholds (Friendly/Trusted/Allied). Locked modules visible in shop with "Requires Trusted with Merchant Guild" text.
- [ ] **Salvage/quest/boss drop hooks**: existing discovery event system fires module unlock notifications. Map current discovery sources to module unlocks.
- [ ] **Starter ship presets**: 3-4 preset ships per weight class built from modules + hull pixels. "Courier", "Fighter", "Trader" archetypes. Player can choose a preset or build from scratch.
- [ ] **New game flow**: tutorial build (Phase 9) or preset selection → player starts with a flyable ship
- [ ] **Save format migration**:
  - Version bump for save format
  - Old saves (pixel-only builds): load as-is, modules list empty. Ship functions normally with old stats.
  - Flag: "Legacy build — visit a shipyard to upgrade to module-based construction" hint in cockpit HUD
  - Player can keep legacy ship or rebuild with modules at any shipyard
- [ ] **Module discovery notifications**: "New part available: Talon Twin-Link Mount!" with preview
- [ ] **Draft save system**: save/load up to 20 named drafts. Stored in save data. No credit cost.
- [ ] **Build sharing — Export**: serialize build → zlib compress → base64 encode → `AURELIA:1:...` string → copy to clipboard
- [ ] **Build sharing — Import**: paste code → decode → validate → load into builder. Blueprint check: highlight missing modules with lock icons, show "Missing Blueprints" list with unlock hints. Confirm disabled until all owned.

**Tests:**
- [ ] Module purchase adds to player blueprint catalog
- [ ] Faction-locked module not purchasable below threshold
- [ ] Salvage event grants module correctly
- [ ] Starter presets build valid ships (pass all validation)
- [ ] Old save loads without errors, ship renders correctly
- [ ] New save includes module data, round-trips correctly
- [ ] Shop displays correct modules for station/faction
- [ ] Draft save/load round-trip preserves full build layout
- [ ] Export produces deterministic code (same build → same string)
- [ ] Import of valid code loads correct build
- [ ] Import of code with missing blueprints shows correct missing list
- [ ] Import of corrupt/invalid code shows graceful error
- [ ] Draft limit (20) enforced

---

### Phase 9: Combat Integration
> **Milestone**: Module layout matters in combat. Hits target specific modules. Disabled modules degrade ship performance. Structural severing works.

**Modified files:**
- `spacegame/models/combat.py`
- `spacegame/views/combat_view.py`
- `spacegame/models/ship.py`

**Work:**
- [ ] **Module HP tracking**: each PlacedModule has current_hp (max_hp derived from module size × hull material factor). Tracked during combat, reset after.
- [ ] **Damage resolution**: when a hit lands at pixel (x, y), determine if that pixel belongs to a module. If yes, damage that module's HP. If hull pixel, damage overall hull HP.
- [ ] **Module disable effects**: when a module's HP reaches 0, it is disabled for the remainder of combat:
  - Cockpit disabled: -40% accuracy, -25% evasion
  - Engine disabled: speed drops to 20% of normal, -30% evasion
  - Weapon mount disabled: mounted weapon stops firing
  - Shield generator disabled: shield capacity reduced proportionally (if 1 of 2 gens disabled, shields drop by ~50%)
  - Cargo bay disabled: 15% chance per cargo bay to lose 1-3 random cargo items
  - Reactor disabled: all other module stats degraded by 25%
- [ ] **Structural severing**: if damage destroys a pixel that is an articulation point, check if the ship graph splits. All modules on the smaller severed section are simultaneously disabled. Visual: severed section dims/fades.
- [ ] **Post-combat repair**: disabled modules auto-repair after combat (free for minor damage; credit cost for severe damage at next station visit)
- [ ] **Combat view updates**:
  - Damaged modules show visual degradation (darkened, flickering pixels)
  - Disabled modules show clear visual indicator (grayed out, crossed out, sparking)
  - "Engine disabled!" / "Shields down!" combat log messages
  - Severed section visual (dimmed, disconnected feel)
- [ ] **Enemy ships**: apply module system to enemy ship templates. Enemy modules can be targeted and disabled (gives player tactical depth — "take out their engines so they can't flee")

**Tests:**
- [ ] Hit on module pixel damages that module
- [ ] Hit on hull pixel damages hull HP, not modules
- [ ] Module at 0 HP triggers correct disable effect
- [ ] Cockpit disable reduces accuracy and evasion
- [ ] Engine disable reduces speed
- [ ] Weapon mount disable stops weapon from firing
- [ ] Articulation point destruction triggers severing check
- [ ] Severed section disables all modules on smaller piece
- [ ] Post-combat repair restores modules
- [ ] Enemy module targeting works

---

### Phase 10: Polish, Tutorial & Sound
> **Milestone**: First-time player experience is guided and clear. Builder feels tactile and satisfying. Enemy ships use the module system. Complete feature.

**Work:**
- [ ] **Guided first-build tutorial**:
  - Step-by-step walkthrough (7 steps from requirements)
  - Progressive unlock: only current step's category available, rest grayed out
  - Hint arrows pointing to placement zones
  - Celebratory moment when ship is complete
  - Skippable for returning players
- [ ] **Sound effects**:
  - Module place: metallic clunk
  - Module rotate/flip preview: light click
  - Module remove: hydraulic hiss
  - Hull pixel paint: soft tap
  - Hull pixel erase: light scrape
  - Fill: rapid tap cascade
  - Mirror toggle: activation chime
  - Requirement met: positive ding
  - All requirements met: completion chord
  - Invalid placement: soft buzz
  - Confirm build: industrial assembly sequence (2-3s)
- [ ] **Visual feedback**:
  - Module placement: brief white edge flash
  - Fill: wave-fill animation outward from click point
  - Confirm: ship assembles piece-by-piece with spark particles, then zooms out
- [ ] **Enemy ship auto-generation**: convert existing EnemyTemplate stats into module-based builds for visual rendering. Faction-appropriate manufacturer choices.
- [ ] **Module comparison tooltips**: in catalog, hover module while one of same type is placed → shows stat delta (green up / red down)
- [ ] **Builder warnings**: advisory text for suboptimal layouts (exposed cockpit, extreme CoM offset, severe bottlenecks)
- [ ] **Preset save/load**: save current build as named preset, load presets from list
- [ ] **Final UX pass**: button sizing, label clarity, tooltip consistency, color coding review, keyboard shortcut cheat sheet (? key)

---

### Phase 11: Build Sharing (Import/Export Codes)
> **Milestone**: Players can export their ship designs as compact text codes and share them through Discord, Reddit, or any text channel. Importing a code loads the build into the builder with blueprint availability checks.

**New files:**
- `spacegame/models/build_sharing.py` — encode/decode logic
- `tests/test_models/test_build_sharing.py`

**Work:**
- [ ] **Export function**: `export_build_code(build: ShipBuild) -> str`
  - Serialize build to minimal JSON (weight_class, frame_variant, modules list, hull pixels)
  - Strip unnecessary fields (descriptions, names — only IDs and positions)
  - Compress with `zlib.compress()`
  - Base64 encode with `base64.urlsafe_b64encode()`
  - Prefix with version tag: `AURELIA:1:<payload>`
  - Result: compact string (~100-200 chars for a typical Medium ship)
  - Deterministic: same build always produces the same code
- [ ] **Import function**: `import_build_code(code: str, module_catalog: dict, hull_materials: dict) -> tuple[Optional[ShipBuild], str]`
  - Validate prefix format (`AURELIA:<version>:<payload>`)
  - Base64 decode → zlib decompress → JSON parse
  - Apply ALL security validation (see Security Hardening section):
    - Maximum payload size: reject base64 strings > 50KB
    - Maximum decompressed size: reject if > 200KB (zip bomb protection)
    - JSON-only deserialization (never pickle/eval/exec)
    - Schema validation: weight_class must be one of 5 known strings, frame_variant must be valid
    - Module IDs must exist in loaded module catalog
    - Hull material IDs must exist in loaded materials
    - Coordinate bounds: all x/y within canvas for declared weight class
    - Maximum module count: reject > 50 modules
    - Maximum hull pixel count: reject > 5000 pixels
  - Return (build, "") on success, (None, error_message) on failure
  - Generic error messages: "Invalid build code" (don't leak validation specifics)
- [ ] **Blueprint availability check**: `check_blueprint_availability(build: ShipBuild, unlocked: set[str]) -> list[dict]`
  - Compare build's module IDs against player's unlocked_modules
  - Return list of missing modules with unlock hints (method, source, cost)
  - Used by the import UI to show the "shopping list"
- [ ] **Builder UI — Export button**: "Share Build" button in the builder (near Save Draft)
  - Generates code, copies to clipboard (via `pygame.scrap` or fallback)
  - Toast message: "Build code copied to clipboard!"
  - Also accessible from the ship info panel outside the builder
- [ ] **Builder UI — Import flow**: "Import Build" button on builder entry screen
  - Text input field for pasting the code
  - Decode → validate → load into builder
  - If missing blueprints: show the build (viewable but not confirmable), display missing blueprint panel with lock icons and unlock hints per module
  - If all blueprints owned: load normally, player can modify and confirm
  - "Invalid build code" message for corrupt/tampered input
- [ ] **Version migration**: code format includes version number for future-proofing
  - Version 1: current format
  - If a future version adds fields, old codes still parse (missing fields get defaults)

**Tests:**
- [ ] Export produces deterministic output (same build → same code)
- [ ] Import of valid code reconstructs correct build (round-trip)
- [ ] Import of corrupted code returns graceful error
- [ ] Import of oversized payload is rejected
- [ ] Import with unknown module IDs returns missing blueprint list
- [ ] Import with all blueprints owned loads successfully
- [ ] Import with out-of-bounds coordinates is rejected
- [ ] Import with invalid weight class is rejected
- [ ] Version prefix validation (wrong prefix rejected, correct parsed)
- [ ] Security: no code execution during import (JSON-only path)

---

### Phase 12: Station Module Shops (Drydock Catalog Integration)
> **Milestone**: Players can browse and purchase module blueprints at station shops. Each station offers different modules based on system location, faction alignment, and station type. Module progression feels earned and location-driven.

**Modified files:**
- `data/ships/drydock_catalogs.json` — add `modules_sold` per station
- `spacegame/views/shipyard_view.py` — add "Parts" tab to shipyard
- `spacegame/models/builder_discovery.py` — wire module purchase into unlock flow
- `spacegame/data_loader.py` — parse modules_sold from catalogs

**Work:**
- [ ] **Extend drydock_catalogs.json** with `modules_sold` field per station:
  ```json
  {
    "nexus_prime": {
      "shapes_sold": [...],
      "materials_sold": [...],
      "modules_sold": ["standard_bridge_rk", "standard_drive_rk", "turret_platform_rk", ...],
      "weight_classes": ["tiny", "small", "medium"],
      "price_modifier": 1.1
    }
  }
  ```
  - Each station stocks 15-25 modules based on faction and system character
  - Guild stations: more Talon (weapon) and Foundry (heavy) modules
  - Collective stations: more Sable (stealth) modules
  - Alliance stations: more Meridian (luxury/efficiency) modules
  - Union stations: more Foundry (industrial/heavy) modules
  - Frontier stations: basic RK modules + Salvage Rat
  - Core systems: larger catalogs; frontier systems: smaller, specialized
- [ ] **Shipyard "Parts" tab**: new tab alongside Drydock/Frames/Shop/Installed
  - Scrollable list of modules available at current station
  - Each entry shows: pixel art preview, name, manufacturer, category, weight, cost
  - Locked modules (faction rep too low, quest not done): grayed out with unlock hint
  - Already-owned modules: green checkmark, "Owned" label
  - Click to purchase: deduct `unlock_cost` credits, add to `player.unlocked_modules`
  - Purchase confirmation toast: "Blueprint acquired: Talon Standard Hardpoint"
  - Filter tabs by category (same as builder catalog)
  - Manufacturer filter dropdown
- [ ] **Blueprint purchase function**: `purchase_module_blueprint(player, module_id, module_catalog) -> tuple[bool, str]`
  - Check if already owned (return "Already owned")
  - Check if unlock method is "purchase" (return "Not for sale" if quest/faction only)
  - Check if player has enough credits
  - Deduct credits, add to unlocked_modules
  - Return success message
- [ ] **Faction-gated modules in shop**: show in list but locked
  - Display: "Requires Trusted with Merchant Guild (rep 40)" with current rep shown
  - Grayed out, cannot purchase until rep threshold met
  - Motivates faction progression: "I need 15 more rep to unlock that engine"
- [ ] **Price modifier from drydock catalog**: station's `price_modifier` affects blueprint unlock costs
  - Frontier stations (0.9x): cheaper blueprints
  - Core stations (1.1x): more expensive
  - Black market stations: unique modules at premium
- [ ] **Module availability on DataLoader**: parse `modules_sold` list from catalog, expose as method
  - `get_station_modules(system_id) -> list[str]` returns module IDs sold at that station

**Tests:**
- [ ] Blueprint purchase deducts credits and adds to unlocked_modules
- [ ] Purchase of already-owned module returns "Already owned"
- [ ] Purchase with insufficient credits fails
- [ ] Faction-locked module cannot be purchased below rep threshold
- [ ] Station catalog correctly lists available modules per system
- [ ] Price modifier applies to blueprint costs
- [ ] All modules have at least one station that sells them (or alternative unlock path)

---

### Phase 13: Module Pixel Customization
> **Milestone**: Players can recolor pixels within placed modules to personalize their appearance without changing the module's shape or stats. Modules retain their functional identity while gaining visual individuality.

**Decision**: Option (b) from the design questions — **recolor only**. Players can change the tint/color of module pixels but cannot reshape the module. This preserves the "parts catalog" identity (you can still recognize a Talon Standard Hardpoint by its shape) while allowing personal expression (paint it blue, add racing stripes).

**Modified files:**
- `spacegame/models/ship_module.py` — add color override data structure
- `spacegame/models/ship_build.py` — extend PlacedModule with color overrides
- `spacegame/engine/ship_composite.py` — apply color overrides during rendering
- `spacegame/views/ship_builder_view.py` — add recolor mode to builder

**Work:**
- [ ] **Color override data structure**: `PlacedModule` gains optional `color_overrides: dict[tuple[int, int], str]`
  - Maps (local_x, local_y) → hull_material_id for recolored pixels
  - Default: empty dict (module renders with its original materials)
  - Only hull-type pixels can be recolored (cockpit_glass, exhaust_port, etc. stay fixed)
  - Override material determines color but NOT stats (module stats are fixed)
- [ ] **Resolve with overrides**: `resolve_placed_module()` checks color_overrides when building pixel list
  - If a pixel has an override, use the override material_id for rendering
  - Non-overridden pixels use the module's original material_map
- [ ] **Builder recolor mode**: new tool in module mode
  - Select a module pixel on the canvas → shows available hull material colors
  - Click a color swatch to apply it to that pixel
  - [C] hotkey to enter recolor mode (Color)
  - Ghost preview shows the new color before confirming
  - Can recolor individual pixels or flood-fill a region within a module
  - Only `H`-mapped pixels (hull pixels within the module) can be recolored
  - Functional material pixels (glass, exhaust, barrels, emitters) are locked
- [ ] **Serialization**: color_overrides serialize in PlacedModule.to_dict()
  - Format: `"color_overrides": {"2,1": "heavy_armor", "3,1": "stealth_composite"}`
  - Compact key format (comma-separated coords) to minimize save size
  - Backward compat: old saves without color_overrides load with empty dict
- [ ] **Rendering**: ShipComposite resolves overrides during pixel map construction
  - Override pixels use the override material's color_primary for fill
  - Panel lines, edge highlights, and material textures apply to the override material
  - Module boundary overlay still shows the original module shape
- [ ] **Undo/redo**: recolor operations are undo-able (included in composite snapshots)

**Design constraints:**
- Shape is FIXED. You cannot add or remove pixels from a module.
- Functional material pixels are NOT recolorable. You can't paint over cockpit glass or exhaust ports. Only hull-frame pixels (mapped to `H` or similar hull characters) can be recolored.
- Stats don't change. Recoloring a hull pixel from RK blue to Foundry brown is purely cosmetic.
- Recolored modules are still recognizable by shape in combat and on the map.

**Tests:**
- [ ] PlacedModule with color_overrides serializes/deserializes correctly
- [ ] resolve_placed_module applies color overrides to pixel material IDs
- [ ] Non-overridden pixels retain original material
- [ ] Functional pixels (glass, exhaust) cannot be overridden
- [ ] ShipComposite renders overridden pixels with correct colors
- [ ] Recolor in builder mode updates the override and triggers re-render

---

### Phase 14: Damage Overkill Propagation
> **Milestone**: When a module absorbs a hit that exceeds its remaining HP, excess damage propagates to hull HP or adjacent modules, creating more realistic and dramatic combat damage cascading.

**Design**: When a module takes overkill damage, the excess doesn't vanish. It propagates based on proximity — first to hull HP (global pool), with a chance to chain-damage adjacent modules. This means a devastating hit on a nearly-destroyed module can cascade into neighboring systems, creating dramatic combat moments ("The engine explosion took out the shield generator next to it!").

**Modified files:**
- `spacegame/models/module_combat.py` — extend `apply_module_damage` with propagation
- `spacegame/models/combat_engine.py` — updated damage flow for propagation results
- `tests/test_models/test_module_combat.py` — propagation tests

**Work:**
- [ ] **Overkill tracking**: `apply_module_damage()` returns excess damage amount
  - Current: `state.current_hp = max(0, state.current_hp - damage)` discards excess
  - New: return `(message, excess_damage)` tuple where `excess_damage = max(0, damage - state.current_hp)`
  - Callers can then route excess damage to hull or adjacent modules
- [ ] **Hull propagation**: excess damage from a module hit applies to global hull HP
  - 100% of excess flows through to hull (armor still applies)
  - Combat log: "Engine destroyed! 15 excess damage to hull"
- [ ] **Adjacent module chain damage**: 30% chance that excess damage chains to an adjacent module
  - "Adjacent" = modules whose pixel footprints share an edge (4-connected)
  - Build an adjacency map during combat init: `dict[int, list[int]]` (module index → neighbor indices)
  - Chain damage = 50% of excess (reduced, not full propagation)
  - Chain can only trigger once per hit (no infinite cascades)
  - Combat log: "Engine explosion damages adjacent Shield Generator! (8 chain damage)"
- [ ] **Chain damage visual feedback**: when chain damage occurs
  - Brief orange flash on the chain-damaged module
  - Particle trail between the destroyed and chain-damaged module positions
  - Combat log entry with clear causal description
- [ ] **Balance tuning**:
  - Chain chance (30%) and chain damage ratio (50%) as constants, easy to tune
  - Maximum one chain per hit (prevents cascade loops)
  - Minimum excess threshold: only propagate if excess >= 5 (small overkill absorbed)
  - Module placement now matters even MORE: don't put your reactor next to a fragile weapon pod

**Tests:**
- [ ] Module hit with exact remaining HP: 0 excess, no propagation
- [ ] Module hit with overkill: correct excess amount returned
- [ ] Excess damage propagates to hull HP
- [ ] Adjacent module chain: 30% chance triggered (seeded random for determinism)
- [ ] Chain damage is 50% of excess (not full amount)
- [ ] No infinite chain cascading (max 1 chain per hit)
- [ ] Small overkill below threshold doesn't propagate to adjacent modules
- [ ] Adjacency map correctly identifies neighboring modules
- [ ] Non-adjacent modules never receive chain damage

---

## Open Design Questions

> These need resolution through continued iteration and playtesting.

1. **Module customization**: ~~Can players edit pixels within a placed module?~~ **RESOLVED (Phase 13)**: Recolor only. Players can change hull pixel tints within a module but cannot reshape it. Functional pixels (glass, exhaust, etc.) are locked. Shape identity preserved, personal expression enabled.

2. **Material interaction**: Do hull pixel materials affect adjacent modules? **Current answer**: No. The two layers are independent. Hull pixels provide structural stats; modules provide functional stats. This may be revisited post-playtesting.

3. **Power budget**: Should reactor modules feed a power system that constrains equipment? **Deferred**. Adds depth but significant complexity. Reactor modules currently provide `power_output` stat but it's not consumed by other modules. Wire this when combat balance needs another lever.

4. **Firing arcs from position**: ~~How detailed should weapon arc computation be?~~ **Current answer**: Not implemented yet. Start with simple (front-facing = forward arc). Can deepen later based on playtesting.

5. **Module damage granularity**: ~~Individual HP pools or disable chance?~~ **RESOLVED (Phase 9)**: Individual HP pools per module. HP = pixel_count * 5. Probabilistic targeting based on pixel coverage. Richer, more tactical.

6. **Severing consequences**: ~~Temporary vs permanent?~~ **RESOLVED (Phase 9)**: Temporary. Disabled modules auto-repair after combat. Keeps the system fun, not punishing.

7. **Legacy migration**: ~~How do existing pixel-painted ships transition?~~ **RESOLVED (Phase 2)**: Grandfathered in. Old saves load with empty modules list and existing pixel/slot data intact. Ship functions normally with old stats. Builder defaults to module mode for new builds.

8. **Scaling weapon mounts to weight class**: Should larger weight classes simply allow more weapon mounts, or should they unlock larger mount sizes? **Current answer**: Larger modules (heavy weapons bay, siege platform) are available for larger ships by weight budget. No explicit size-gating beyond weight — heavier weapons are naturally restricted to larger ships that can afford the weight.

9. **Damage overkill propagation**: ~~Should excess damage vanish or propagate?~~ **RESOLVED (Phase 14)**: Excess propagates to hull HP, with 30% chance to chain-damage adjacent modules at 50% of excess. Creates dramatic cascading combat moments.

---

## What This Replaces

| Old System | New System |
|-----------|------------|
| Shapes (geometric stamps) | Modules (functional parts) + shape stamps for hull pixels only |
| Materials (17 types, per-pixel stats) | Module stats (fixed) + hull materials (4 types, simplified) |
| Material identity (Juggernaut/Sentinel/Ghost at 35%) | Manufacturer identity + module composition |
| Slot designation (place 2x2 anywhere on hull) | Slots come with modules (weapon mount includes weapon slot) |
| Discovery (shapes + materials) | Discovery (modules from all existing sources) |
| Freeform pixel painting (primary) | Module placement (primary) + hull pixel painting (secondary) |

---

## Metrics for Success

- **"Is this a ship?"** — A first-time player's build should look recognizably ship-like because modules provide visual structure
- **Decision depth** — Players should face meaningful trade-offs (weight, module choice, layout, manufacturer) not just "fill with best material"
- **Build variety** — No dominant strategy. Evasion builds, tank builds, trader builds, stealth builds should all be viable and visually distinct
- **Progression excitement** — Finding a new module should feel like finding a new weapon in Armored Core
- **Build time** — Quick rebuild: 3-5 minutes. Full from-scratch: 10-15 minutes
- **Creative pride** — Players should want to show off their ships. The hull pixel layer enables personal expression on top of functional engineering
