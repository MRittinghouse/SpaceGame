# Visual Overhaul — 16-Bit Pixel Art System

## Implementation Status: PHASES A-B COMPLETE (Infrastructure + Static Sprites Wired)
**Cycle**: 6.1-6.2 (promoted to Phase 6 — priority before Act Two content)
**Priority**: P1 — visual identity
**Prerequisites**: None (all views exist and render; this enhances them)

---

## Vision

SpaceGame's visuals currently rely on procedural drawing (pygame.draw polygons, circles, rects) and text. There are no character sprites, no ship variety, no commodity icons, and no ground tile textures. The game feels functional but visually flat.

This overhaul transforms SpaceGame into a visually cohesive 16-bit pixel art game inspired by SNES/GBA-era sci-fi RPGs. Every visual element — ships, characters, worlds, items, UI chrome — shares a unified pixel art aesthetic with constrained palettes, crisp scaling, and moderate animation.

### Core Aesthetic Principles

1. **Consistent pixel density**: All assets share the same "pixel size" at their display scale. No mixing hi-res text with lo-res sprites or vice versa.
2. **Constrained palettes**: Each visual domain (faction, system, UI) has a defined palette of 8-16 colors. This forces cohesion and gives the game a curated feel.
3. **Readable at a glance**: Silhouettes and color language must communicate identity instantly. The player should know "that's a Commerce Guild ship" or "that's stolen data" from the icon alone without reading text.
4. **Animation serves gameplay**: Animation draws attention to what matters — engine glow when moving, shield shimmer when active, damage flash when hit. No animation for decoration's sake.
5. **Pixel art, not retro pastiche**: We're using pixel art because it's beautiful and achievable, not because we're imitating a specific old game. Clean, modern pixel art with smart use of color and form.

---

## Art Direction

### Color Language

#### Ship & Player UI
- **Primary**: Deep blue tones (hull plating, cockpit glass, UI panels)
- **Accent**: Orange/amber for energy, heat, engine glow, warning states
- **Health**: Green → yellow → red gradient for hull/shield bars
- **Shields**: Cyan/electric blue shimmer

#### Factions
Each faction has a signature palette (4-6 primary colors + 2-3 accent colors):

| Faction | Primary Colors | Accent | Feel |
|---------|---------------|--------|------|
| Commerce Guild | Gold, cream, dark navy | Red trim | Wealth, authority, corporate |
| Science Collective | White, steel blue, teal | Green data glow | Clean, clinical, advanced |
| Miners Union | Rust orange, brown, dark gray | Yellow sparks | Industrial, rough, warm |
| Frontier Alliance | Forest green, tan, earth brown | Sky blue | Frontier, resourceful, organic |
| Crimson Reach | Deep red, charcoal, black | Purple, sickly green | Dangerous, lawless, neon-lit |

#### Systems
Each of the 10 systems has a dominant color mood derived from its controlling faction + unique environmental identity:

| System | Mood Palette | Environmental Character |
|--------|-------------|------------------------|
| Nexus Prime | Gold/navy (Guild hub) | Gleaming station spires, trade traffic |
| Stellaris Port | Gold/cream (Guild outpost) | Busy docks, cargo containers |
| Forgeworks | Rust/orange glow (Union industrial) | Molten metal, foundry chimneys |
| Iron Depths | Dark gray/brown (Union mining) | Asteroid tunnels, drill rigs |
| Breakstone | Brown/amber (Union settlement) | Rough-hewn rock, warm lights |
| Axiom Labs | White/teal (Collective research) | Sleek labs, holographic displays |
| Nova Research | Steel blue/green (Collective outpost) | Orbital arrays, sensor dishes |
| Haven's Rest | Green/tan (Alliance refuge) | Vegetation, wooden structures |
| Verdant | Earth green/sky blue (Alliance garden) | Lush canopy, water features |
| Crimson Reach | Red/charcoal/neon (Lawless) | Rusted hulls, flickering signs, danger |

### Sprite Specifications

#### Portraits (NPCs + Crew)
- **Native size**: 50×60 pixels
- **Display size**: 100×120 pixels (2x scale)
- **Style**: Head-and-shoulders bust, 3/4 view facing right (mirrored for left-facing if needed)
- **Background**: Transparent (composited onto dialogue panel background)
- **Palette**: Character-specific (skin tones + outfit colors from faction palette)
- **Animation**: 2-frame idle (subtle breathing/blink cycle, ~2s period)
- **Expression variants**: Neutral, happy/confident, angry/stern, surprised (4 per character)
- **Count**: 7 NPCs + 4 crew + 1 narrator silhouette = 12 portrait sets

#### Ships (Player + Enemy)
- **Native size**: 32×32 pixels (fits all ship classes with padding)
- **Display size**: 64×64 pixels (2x scale in combat), 32×32 (galaxy map)
- **Orientation**: Top-down, nose pointing UP (rotated programmatically for travel)
- **Player ships** (6 types):
  - Shuttle: Compact, rounded, single engine
  - Light Freighter: Medium, visible cargo bay, two engines
  - Medium Freighter: Larger, boxy, cargo pods visible
  - Fast Courier: Sleek, swept wings, triple engine
  - Bulk Hauler: Massive, industrial, four engines, antenna arrays
  - Luxury Yacht: Elegant, curved lines, glowing trim
- **Enemy ships** (8-10 base sprites, palette-swapped for factions):
  - Pirate: Asymmetric, cobbled together, mismatched parts
  - Patrol: Symmetrical, clean lines, faction colors
  - Heavy: Bulky, armored plates, turret mounts
  - Scout: Tiny, fast-looking, minimal profile
  - Bounty Hunter: Distinctive, angular, predatory silhouette
- **Animation**: 2-frame engine glow cycle, hit flash (white overlay 2 frames), shield shimmer (3 frames), destruction sequence (4 frames)
- **Damage states**: Clean, light damage (scorch marks), heavy damage (sparks, missing panels) — 3 states per ship, can be overlays

#### Commodity Icons
- **Native size**: 16×16 pixels
- **Display size**: 32×32 pixels (2x scale) in market listings, 16×16 in compact views
- **Style**: Iconic, readable at small size, distinct silhouettes
- **Palette**: 4-6 colors per icon, drawn from commodity category colors:
  - Basic goods (food, water, textiles): Warm earth tones
  - Industrial (metals, ore, fuel): Gray/orange/amber
  - Luxury (electronics, luxury goods): Blue/gold/white
  - Contraband (stolen data, combat stims): Red/purple accent, skull or warning marker
- **Count**: 26 commodities
- **Animation**: None (static icons)

#### Faction Emblems
- **Native size**: 24×24 pixels
- **Display size**: 48×48 pixels (2x scale)
- **Style**: Geometric symbols, instantly recognizable
  - Commerce Guild: Stylized scale or coin
  - Science Collective: Atom or hexagonal lattice
  - Miners Union: Crossed pickaxes or gear
  - Frontier Alliance: Star or compass rose
- **Animation**: None
- **Count**: 4 emblems + 1 "lawless" icon for Crimson Reach

#### Ground Tiles
- **Native size**: 16×16 pixels
- **Display size**: 48×48 pixels (3x scale, matching current grid)
- **Tile types** (13 total): floor, wall, door, terminal, crate, hazard, extraction, entry, exit, vent, reinforced_wall, window, cover
- **Style**: Industrial sci-fi interior (metal flooring, wall panels, piping)
- **Palette**: Per-faction variant (4 faction tilesets + 1 neutral/derelict)
- **Animation**: Terminal (blinking screen, 2 frames), hazard (pulsing glow, 2 frames), vent (steam, 3 frames)
- **Count**: 13 base types × 5 palettes = 65 tiles (but many share geometry, just recolored)

#### Upgrade Icons
- **Native size**: 16×16 pixels
- **Display size**: 32×32 pixels (2x scale)
- **Style**: Recognizable equipment silhouettes
- **Count**: 20 upgrades (weapons, defenses, utility, smuggling)
- **Animation**: None

#### UI Elements
- **Button frames**: 9-slice scalable pixel art borders
- **Panel backgrounds**: Tiled dark metal texture
- **Health/shield/energy bar frames**: Pixel art end caps + tileable middle
- **Minimap frame**: Corner decorations, compass points
- **Status effect icons**: 12×12 native (buff/debuff indicators)
- **Cursor**: Custom pixel art cursor (16×16)

---

## Technical Architecture

### Directory Structure

```
spacegame/data/assets/
  palettes/                    # JSON palette definitions
    master_palette.json        # All colors used across the game
    faction_commerce_guild.json
    faction_science_collective.json
    faction_miners_union.json
    faction_frontier_alliance.json
    faction_crimson_reach.json
    ui_palette.json            # Ship UI (blue/orange) colors
  sprites/
    portraits/                 # 50x60 native PNGs
      officer_larsen.png       # Static or sprite sheet (if animated)
      officer_larsen_sheet.png # 4 expressions × 2 anim frames = 8 frames
      malia_torres.png
      ...
    ships/
      player/                  # 32x32 native, one per ship type
        shuttle.png
        shuttle_sheet.png      # Idle + damage states + destruction
        light_freighter.png
        ...
      enemies/                 # 32x32 native, base sprites
        pirate_base.png
        patrol_base.png
        bounty_hunter_base.png
        ...
    commodities/               # 16x16 native PNGs
      food_rations.png
      iron_ore.png
      stolen_data.png
      ...
    factions/                  # 24x24 native PNGs
      commerce_guild.png
      science_collective.png
      ...
    ground_tiles/              # 16x16 native PNGs
      neutral/                 # Default tileset
        floor.png
        wall.png
        ...
      commerce_guild/          # Faction-tinted tileset
        floor.png
        ...
    upgrades/                  # 16x16 native PNGs
      cargo_bay_ext.png
      hidden_compartment.png
      ...
    ui/                        # Various sizes
      panel_9slice.png         # 9-slice border texture
      bar_frame.png            # Health/shield bar frame
      cursor.png               # 16x16 cursor
      status_icons.png         # 12x12 sheet of buff/debuff icons
  animations/                  # Animation metadata
    portrait_anims.json        # Frame timing for portrait idle cycles
    ship_anims.json            # Frame timing for ship animations
    ground_tile_anims.json     # Animated tile frame data
```

### Palette System

Palettes are defined as JSON for tooling and enforcement:

```json
{
  "id": "ui_palette",
  "name": "Ship Interface",
  "colors": {
    "bg_dark": [12, 18, 32],
    "bg_mid": [24, 36, 64],
    "bg_light": [40, 58, 96],
    "accent_primary": [60, 120, 200],
    "accent_bright": [100, 180, 255],
    "energy_dim": [180, 100, 20],
    "energy_bright": [255, 160, 40],
    "energy_hot": [255, 80, 20],
    "text_primary": [220, 230, 245],
    "text_dim": [140, 155, 180],
    "health_full": [40, 200, 80],
    "health_mid": [220, 200, 40],
    "health_low": [220, 60, 40],
    "shield_color": [60, 200, 255]
  }
}
```

At runtime, `PaletteManager` loads all palettes and provides:
- `get_palette(palette_id) -> dict[str, tuple[int, int, int]]`
- `get_faction_palette(faction_id) -> dict`
- `get_nearest_color(rgb, palette_id) -> tuple` (for quantization)

### Sprite Loading & Rendering

#### SpriteSheet Class

```python
@dataclass
class SpriteSheet:
    """A horizontal strip of animation frames."""
    surface: pygame.Surface
    frame_width: int
    frame_height: int
    frame_count: int
    scale: int = 2  # Display scale multiplier

    def get_frame(self, index: int) -> pygame.Surface:
        """Extract and scale a single frame."""
        ...

    def get_scaled_frame(self, index: int) -> pygame.Surface:
        """Get frame at display scale (nearest-neighbor)."""
        ...
```

#### AnimatedSprite Class

```python
@dataclass
class AnimatedSprite:
    """A sprite with frame-based animation."""
    sheet: SpriteSheet
    frame_duration: float  # Seconds per frame
    loop: bool = True
    current_frame: int = 0
    timer: float = 0.0

    def update(self, dt: float) -> None:
        """Advance animation timer."""
        ...

    def get_current_surface(self) -> pygame.Surface:
        """Get the current display-scaled frame."""
        ...
```

#### Extended ImageLoader

The existing `ImageLoader` gains new methods with **graceful fallback**:

```python
def load_sprite(self, category: str, sprite_id: str,
                scale: int = 2) -> Optional[pygame.Surface]:
    """Load a sprite with nearest-neighbor scaling.

    Falls back to None if missing (caller renders procedurally).
    """
    ...

def load_sprite_sheet(self, category: str, sprite_id: str,
                      frame_size: tuple[int, int],
                      scale: int = 2) -> Optional[SpriteSheet]:
    """Load a sprite sheet (horizontal strip of frames)."""
    ...
```

**Critical design principle**: Every view that renders a sprite MUST have a fallback to the current procedural rendering. This means:
- We can add sprites incrementally (one NPC at a time, one ship at a time)
- The game is always playable, even with zero sprite assets
- We never block gameplay progress on art completion

### Scaling Rules

| Asset Type | Native Size | Scale | Display Size | Method |
|-----------|-------------|-------|-------------|--------|
| Portraits | 50×60 | 2x | 100×120 | `pygame.transform.scale()` |
| Ships (combat) | 32×32 | 2x | 64×64 | `pygame.transform.scale()` |
| Ships (galaxy map) | 32×32 | 1x | 32×32 | Direct blit |
| Commodities (market) | 16×16 | 2x | 32×32 | `pygame.transform.scale()` |
| Commodities (compact) | 16×16 | 1x | 16×16 | Direct blit |
| Faction emblems | 24×24 | 2x | 48×48 | `pygame.transform.scale()` |
| Ground tiles | 16×16 | 3x | 48×48 | `pygame.transform.scale()` |
| Upgrade icons | 16×16 | 2x | 32×32 | `pygame.transform.scale()` |
| UI elements | Various | 2x | Various | 9-slice or direct |

**NEVER use `smoothscale()`** for pixel art — it introduces anti-aliasing that destroys the pixel aesthetic. Always `scale()` (nearest-neighbor).

### Animation System

#### Frame Timing Configuration

```json
{
  "portrait_idle": {
    "frames": [0, 1],
    "frame_duration": 1.0,
    "loop": true
  },
  "portrait_blink": {
    "frames": [0, 2, 0],
    "frame_duration": 0.1,
    "loop": false,
    "trigger": "random",
    "trigger_interval_range": [3.0, 7.0]
  },
  "ship_idle": {
    "frames": [0, 1],
    "frame_duration": 0.3,
    "loop": true
  },
  "ship_hit": {
    "frames": [2, 3, 2],
    "frame_duration": 0.08,
    "loop": false
  },
  "ship_destroy": {
    "frames": [4, 5, 6, 7],
    "frame_duration": 0.15,
    "loop": false
  }
}
```

#### Animation in Views

Views request animations through a simple API:

```python
# In combat_view.py
ship_sprite = self.sprite_manager.get_ship_sprite("shuttle")
ship_sprite.play("idle")  # Loops engine glow

# On hit:
ship_sprite.play("hit", on_complete=lambda: ship_sprite.play("idle"))

# On destroy:
ship_sprite.play("destroy")
```

The `SpriteManager` class owns all loaded sprites and animations for the current view, handles frame updates in `update(dt)`, and provides the current display surface on demand.

---

## Asset Pipeline

### Overview

The asset pipeline converts AI-generated or hand-drawn source art into game-ready pixel art sprites that conform to our palette and resolution standards.

```
[AI Generation] → [High-res concept] → [Pipeline Script] → [Game-ready sprite]
     ↓                                       ↓
  Prompt from              Python tool: downscale, quantize,
  world docs               outline, sheet pack
                                             ↓
                                    [Manual review & touch-up]
                                             ↓
                                    [Final sprite committed]
```

### Step 1: AI Generation (Concept Phase)

Use AI image generation to produce concept art at 2-4x target resolution:
- **Portraits**: Generate at 200×240 (4x native 50×60)
- **Ships**: Generate at 128×128 (4x native 32×32)
- **Icons**: Generate at 64×64 (4x native 16×16)

#### Prompt Strategy

Prompts are built from our existing worldbuilding documents:
- `requirements/cultural_guide.md` — faction aesthetics, cultural identity
- `requirements/14_smuggling_contraband.md` — NPC descriptions
- Character/NPC descriptions from dialogue JSON data

**Example prompt template for NPC portrait:**
```
Pixel art portrait, head and shoulders, 3/4 view facing right,
[NPC description from cultural guide],
[faction] color palette: [colors],
dark space station background, sci-fi uniform,
16-bit SNES style, clean pixel art, no anti-aliasing,
limited color palette, sharp outlines
```

**Example prompt template for ship:**
```
Top-down pixel art spaceship, [ship class description],
[faction] design language: [adjectives from cultural guide],
32x32 pixel grid, dark background,
16-bit style, clean outlines, visible engine glow,
limited palette: [faction colors]
```

### Step 2: Automated Processing (pixel_pipeline.py)

A Python command-line tool that processes raw concept art into pixel art:

```bash
# Process a single image
python tools/pixel_pipeline.py process \
  --input raw/officer_larsen_concept.png \
  --output sprites/portraits/officer_larsen.png \
  --target-size 50x60 \
  --palette palettes/faction_commerce_guild.json \
  --outline-color 20,22,30

# Batch process a folder
python tools/pixel_pipeline.py batch \
  --input-dir raw/commodities/ \
  --output-dir sprites/commodities/ \
  --target-size 16x16 \
  --palette palettes/master_palette.json

# Pack frames into a sprite sheet
python tools/pixel_pipeline.py sheet \
  --inputs frame_0.png frame_1.png frame_2.png \
  --output sprites/ships/shuttle_sheet.png

# Palette swap an existing sprite
python tools/pixel_pipeline.py recolor \
  --input sprites/enemies/patrol_base.png \
  --output sprites/enemies/guild_enforcer.png \
  --source-palette palettes/faction_neutral.json \
  --target-palette palettes/faction_commerce_guild.json
```

#### Processing Steps (per image):

1. **Resize**: Downscale to target size using `PIL.Image.resize(NEAREST)`
2. **Palette quantize**: Map each pixel to the nearest color in the target palette using Euclidean distance in RGB space
3. **Outline enforce**: Detect edges (alpha boundary), ensure 1px dark outline
4. **Alpha clean**: Any pixel with alpha < 128 → fully transparent; else → fully opaque (no semi-transparency in pixel art)
5. **Grid snap**: Ensure dimensions match target exactly, pad/crop as needed
6. **Validate**: Check total unique colors ≤ palette size, report violations

#### Palette Swap Algorithm:

For faction-variant enemies and tiles:
1. Load source sprite + source palette
2. For each non-transparent pixel, find its index in source palette
3. Map to same index in target palette
4. Output recolored sprite

This lets us create all faction variants of patrol ships, ground tiles, etc. from a single base sprite.

### Step 3: Manual Review & Touch-Up

After automated processing, review each sprite for:
- **Readability**: Is the silhouette clear at display scale?
- **Palette violations**: Any colors that feel "off" in context?
- **Detail loss**: Did downscaling lose important features?
- **Animation continuity**: Do frames flow smoothly?

Touch-up tools: Aseprite (recommended) or GIMP with pencil tool at 1x zoom. Fix individual pixels as needed. This should be minimal work per asset if the pipeline is tuned well — typically 1-5 minutes per sprite.

### Step 4: Integration

Processed sprites go into `spacegame/data/assets/sprites/` and are loaded by the extended `ImageLoader`. Views detect sprite availability and render them instead of procedural fallbacks.

---

## Implementation Phases

### Phase A: Infrastructure (Foundation)

**Goal**: Build the technical systems that all sprites depend on. No visual assets yet — just the plumbing.

**Deliverables**:
1. **Palette system**: `PaletteManager` class, JSON palette definitions for all factions + UI + master
2. **SpriteSheet class**: Load horizontal strip PNGs, extract frames, scale with nearest-neighbor
3. **AnimatedSprite class**: Frame-based animation with timing, looping, callbacks
4. **SpriteManager class**: Per-view sprite lifecycle (load on enter, release on exit), update all animations
5. **Extended ImageLoader**: `load_sprite()`, `load_sprite_sheet()` with category/id pattern, fallback to None
6. **Asset pipeline tool**: `tools/pixel_pipeline.py` with process, batch, sheet, recolor commands
7. **Scaling utilities**: Centralized `scale_pixel_art(surface, factor)` that enforces nearest-neighbor
8. **Test suite**: Pipeline unit tests (quantization accuracy, resize correctness, sheet packing)

**Files created/modified**:
- NEW: `spacegame/engine/sprites.py` (SpriteSheet, AnimatedSprite, SpriteManager)
- NEW: `spacegame/engine/palettes.py` (PaletteManager)
- NEW: `tools/pixel_pipeline.py` (asset processing CLI)
- NEW: `spacegame/data/assets/palettes/*.json` (6+ palette files)
- MODIFIED: `spacegame/utils/image_loader.py` (extend with sprite methods)
- NEW: `tests/test_engine/test_sprites.py`
- NEW: `tests/test_engine/test_palettes.py`
- NEW: `tests/test_tools/test_pixel_pipeline.py`

**Estimated scope**: ~800-1000 lines of new code, 0 visual assets

---

### Phase B: Ship Sprites & Combat View

**Goal**: Replace procedural wedge silhouettes with pixel art ships. Transform the combat view from "functional wireframe" to "visually engaging space battle."

**Deliverables**:
1. **6 player ship sprites** (32×32 native): shuttle, light_freighter, medium_freighter, fast_courier, bulk_hauler, luxury_yacht
   - Each with: idle (2 frames), hit flash (2 frames), heavy damage overlay, destruction (4 frames)
   - Ship sprite sheets: 32×32 × 10 frames = 320×32 per ship
2. **8-10 enemy base sprites** (32×32 native): pirate, patrol, heavy, scout, smuggler, bounty_tracker, bounty_enforcer, bounty_vanguard, bounty_ace, faction_enforcer
   - Palette-swapped variants for each faction (automated via pipeline)
   - Same animation frames as player ships
3. **Combat view integration**:
   - Replace `_draw_ship_silhouette()` with sprite rendering
   - Add damage state rendering (sprite overlay based on hull %)
   - Add hit flash animation trigger on damage events
   - Add destruction animation on enemy defeat
   - Ship rotation for galaxy map travel (programmatic rotation of top-down sprite)
4. **Galaxy map ship icon**: Use player's current ship sprite (scaled down to 1x)
5. **Shipyard view**: Show ship sprites in purchase/comparison UI

**Files modified**:
- `spacegame/views/combat_view.py` (sprite rendering replaces procedural)
- `spacegame/views/galaxy_map_view.py` (player ship sprite)
- `spacegame/views/shipyard_view.py` (ship preview sprites)
- NEW: `spacegame/data/assets/sprites/ships/player/*.png`
- NEW: `spacegame/data/assets/sprites/ships/enemies/*.png`
- NEW: `spacegame/data/assets/animations/ship_anims.json`

**Estimated scope**: ~200 lines code changes, 16-20 sprite assets (before palette swaps), ~40 total with faction variants

---

### Phase C: NPC Portraits & Dialogue View

**Goal**: Give every NPC and crew member a visual identity. Transform dialogue from "text on a dark background" to "character-driven conversation."

**Deliverables**:
1. **12 portrait sprite sets**:
   - 7 NPCs: Officer Larsen, Cargo Broker, Elena Vasquez, Marcus Jin, Priya Osei, Tomas Drifter, Malia Torres
   - 4 crew (same characters, but these are the in-crew versions — could share portraits)
   - 1 narrator (silhouette/abstract, used for intro narration)
   - Each with: neutral, confident, stern, surprised expressions
   - 2-frame idle animation (subtle breathing/shift)
   - Sprite sheets: 50×60 × 8 frames (4 expressions × 2 idle) = 400×60 per character
2. **Dialogue view integration**:
   - Render portrait in the existing 100×120 reserved area
   - Expression changes driven by dialogue node metadata (new optional field)
   - Idle animation runs continuously
   - Smooth cross-fade between expression changes
3. **Crew roster view**: Show crew portraits in the detail panel
4. **Character creation view**: Simple player avatar or silhouette

**New dialogue JSON field** (optional, backward compatible):
```json
{
  "id": "node_01",
  "speaker": "officer_larsen",
  "expression": "stern",
  "text": "Your cargo manifest doesn't match our records."
}
```

**Files modified**:
- `spacegame/views/dialogue_view.py` (portrait rendering)
- `spacegame/views/crew_roster_view.py` (crew portraits)
- `spacegame/data_loader.py` (parse expression field)
- `spacegame/models/dialogue.py` (add optional expression field to DialogueNode)
- NEW: `spacegame/data/assets/sprites/portraits/*.png`
- NEW: `spacegame/data/assets/animations/portrait_anims.json`

**Estimated scope**: ~150 lines code changes, 12 portrait sprite sets

---

### Phase D: Commodity Icons & Market UI

**Goal**: Give every tradeable commodity a visual icon. Make the market UI feel like a real trading interface.

**Deliverables**:
1. **26 commodity icons** (16×16 native):
   - Basic: food_rations, water, textiles, medical_supplies, contraband_medicine
   - Industrial: iron_ore, metals, fuel, manufactured_goods, weapons_components, combat_stims
   - Luxury: electronics, luxury_goods, spice, exotic_goods, restricted_tech, stolen_data
   - Raw: raw_ore, common_metals, rare_metals, salvaged_electronics, rare_parts, scrap_metal
   - Refined: refined_alloy, composite_material, advanced_components, precision_parts
2. **Trading view integration**:
   - Commodity icon displayed next to name in market table
   - Legality indicator overlay (small colored dot: green/yellow/red)
   - Cargo hold shows icons in grid layout (optional enhancement)
3. **Mission log**: Show commodity icons next to delivery objectives
4. **Ground loot**: Show commodity icon on pickup notification

**Files modified**:
- `spacegame/views/trading_view.py` (icon rendering in market table)
- `spacegame/views/table_widget.py` (support for icon column type)
- NEW: `spacegame/data/assets/sprites/commodities/*.png`

**Estimated scope**: ~100 lines code changes, 26 icon assets

---

### Phase E: Faction Emblems & System Portraits

**Goal**: Give factions and star systems visual identity beyond color-coded text.

**Deliverables**:
1. **5 faction emblems** (24×24 native): Commerce Guild, Science Collective, Miners Union, Frontier Alliance, Crimson Reach
2. **10 system portraits** (80×60 native): One per star system, showing the station/environment character
3. **Galaxy map integration**:
   - Replace procedural 12px planets with larger system portraits (or use emblem + portrait on hover)
   - Faction emblem displayed on system tooltip/info panel
4. **Trading view header**: Show current system portrait + faction emblem
5. **Dialogue view**: Faction emblem next to NPC name for faction-affiliated characters

**Files modified**:
- `spacegame/views/galaxy_map_view.py` (system portraits)
- `spacegame/views/trading_view.py` (header with system portrait)
- `spacegame/views/dialogue_view.py` (faction emblem)
- NEW: `spacegame/data/assets/sprites/factions/*.png`
- NEW: `spacegame/data/assets/sprites/systems/*.png`

**Estimated scope**: ~150 lines code changes, 15 sprite assets

---

### Phase F: Ground Tiles & Exploration View

**Goal**: Replace solid-color rectangles with textured pixel art tiles. Make ground exploration feel like exploring a real environment.

**Deliverables**:
1. **13 base tile sprites** (16×16 native) in neutral palette
2. **4 faction palette variants** (automated via pipeline recolor)
3. **Animated tiles**: terminal (2 frames), hazard (2 frames), vent (3 frames)
4. **Ground exploration view integration**:
   - Replace `_TILE_COLORS` rect fills with sprite blits
   - Fog of war: darken/desaturate tile sprites (not just overlay)
   - Enemy sprites: Replace circle+triangle with small character sprites (16×16 native, same grid)
   - Player sprite: Replace yellow square with character sprite
5. **Ground enemy sprites** (8 templates, 16×16 native):
   - Factioned: guild_guard, union_worker, collective_drone, alliance_scout
   - Generic: pirate, raider, sentry, beast
   - Facing direction via rotation or 4-direction sprite (up/down/left/right)
6. **Minimap update**: Use tile sprite colors for more accurate representation

**Files modified**:
- `spacegame/views/ground_exploration_view.py` (tile + entity rendering)
- NEW: `spacegame/data/assets/sprites/ground_tiles/**/*.png`
- NEW: `spacegame/data/assets/sprites/ground_enemies/*.png`
- NEW: `spacegame/data/assets/animations/ground_tile_anims.json`

**Estimated scope**: ~200 lines code changes, 65+ tile assets, 8 enemy sprites

---

### Phase G: Upgrade Icons & UI Polish

**Goal**: Final polish pass. Upgrade icons, status effect indicators, UI chrome, and consistency sweep.

**Deliverables**:
1. **20 upgrade icons** (16×16 native): One per ship upgrade
2. **Status effect icons** (12×12 native): Buff/debuff indicators for combat
3. **UI panel texture**: Subtle pixel art panel background (tileable)
4. **Health/shield/energy bar frames**: Pixel art end caps replacing plain rects
5. **Custom cursor**: 16×16 pixel art cursor
6. **Skill tree node icons**: Replace text-only skill nodes with small icons
7. **Achievement icons**: Small badge graphics for achievement unlocks
8. **Loading/transition enhancements**: Pixel art warp effect, scan lines
9. **Consistency audit**: Review all views, ensure no remaining procedural-only elements that should have sprites

**Files modified**:
- `spacegame/views/shipyard_view.py` (upgrade icons)
- `spacegame/views/skill_tree_view.py` (node icons)
- `spacegame/views/combat_view.py` (status icons, bar frames)
- Various views (UI panel texture, cursor)
- NEW: `spacegame/data/assets/sprites/upgrades/*.png`
- NEW: `spacegame/data/assets/sprites/ui/*.png`

**Estimated scope**: ~200 lines code changes, 40+ icon/UI assets

---

## Asset Count Summary

| Category | Native Size | Count | Palette Variants | Total Assets |
|---------|-------------|-------|-----------------|-------------|
| Player ship sprites | 32×32 | 6 | 1 | 6 sheets |
| Enemy ship sprites | 32×32 | 10 | 4 factions + neutral | ~20 sheets |
| NPC portraits | 50×60 | 8 | 1 | 8 sheets |
| Crew portraits | 50×60 | 4 | 1 | 4 sheets |
| Commodity icons | 16×16 | 26 | 1 | 26 |
| Faction emblems | 24×24 | 5 | 1 | 5 |
| System portraits | 80×60 | 10 | 1 | 10 |
| Ground tiles | 16×16 | 13 | 5 | 65 |
| Ground enemies | 16×16 | 8 | 1 | 8 |
| Upgrade icons | 16×16 | 20 | 1 | 20 |
| UI elements | Various | ~15 | 1 | ~15 |
| **Total** | | **~125 unique** | | **~190 files** |

---

## Testing Strategy

### Pipeline Tests (tools/pixel_pipeline.py)
- Palette quantization: verify color mapping accuracy
- Resize: verify nearest-neighbor (no interpolation artifacts)
- Outline detection: verify 1px outline enforcement
- Alpha cleanup: verify binary alpha (0 or 255 only)
- Sheet packing: verify frame extraction round-trip
- Palette swap: verify color index mapping
- Batch processing: verify directory traversal and output

### Sprite System Tests (spacegame/engine/sprites.py)
- SpriteSheet frame extraction at correct dimensions
- AnimatedSprite frame timing and looping
- SpriteManager lifecycle (load, update, release)
- Fallback behavior when sprite file missing

### Integration Tests
- Views render without errors when sprites are missing (fallback path)
- Views render correctly when sprites are present
- Animation timing matches configuration
- Palette-swapped sprites have correct colors

### Visual Regression (Manual)
- Screenshot comparison before/after for each phase
- Verify consistent pixel density across all views
- Verify no smoothscale artifacts (crisp edges at all scales)
- Verify animation smoothness at 60 FPS

---

## Dependencies

| Dependency | Status | Notes |
|-----------|--------|-------|
| Pillow (PIL) | Available | Used by pixel_pipeline.py for image processing |
| pygame.transform.scale | Available | Nearest-neighbor scaling (NOT smoothscale) |
| ImageLoader | COMPLETE | Exists, needs extension for sprite categories |
| All game views | COMPLETE | Every view has working procedural rendering to fall back on |
| Aseprite | NOT ACQUIRED | $20 one-time, recommended for manual touch-up |

---

## Metrics & Quality Targets

| Metric | Target |
|--------|--------|
| Sprite load time (all assets) | < 500ms on startup |
| Memory usage (all sprites cached) | < 50MB |
| Animation frame rate | 60 FPS (no dropped frames from sprite rendering) |
| Palette compliance | 100% of sprites use only defined palette colors |
| Fallback coverage | 100% of views render correctly with zero sprite files |
| Unique color count per sprite | ≤ 16 (portraits), ≤ 8 (icons), ≤ 12 (ships) |
| Manual touch-up time per asset | < 5 minutes average after pipeline processing |

---

## What This Does NOT Include

- **3D rendering**: Everything remains 2D surface-based
- **Skeletal animation**: All animation is frame-based sprite sheets
- **Dynamic lighting**: No per-pixel lighting; mood is set by palette and particle effects
- **Procedural sprite generation at runtime**: All sprites are pre-made assets; the procedural generators remain as fallbacks only
- **Resolution independence**: Game targets 1280×720 fixed; sprites are designed for this resolution
- **Tilemap editor**: Ground maps use existing procedural generation; tiles are just visual skins
- **Character customization**: Player has no visual avatar to customize (portrait is narrator silhouette)
- **Cutscenes or FMV**: Narrative remains dialogue-driven with portraits, not animated sequences
