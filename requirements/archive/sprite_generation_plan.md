# Comprehensive Sprite Generation Plan

## Asset Audit Summary

| Category | Have | Need | Format | Player Impact |
|----------|------|------|--------|--------------|
| Enemy ships | 33/47 | **14** | 192x32 sheet (6x 32x32) | HIGH - every combat |
| Upgrade icons | 21/112 | **91** | 16x16 PNG | HIGH - shipyard browsing |
| Skill icons | 35/109 | **74** | 16x16 PNG | HIGH - progression screen |
| NPC portraits | 12/32 | **20** | 50x60 animated sheet | MEDIUM - dialogue |
| Ground tiles (faction) | 1/5 sets | **~32** | 16x16 PNG | MEDIUM - ground missions |
| Commodities | 60/61 | **1** | 16x16 PNG | LOW - single item |

**Total sprites needed: ~232**

---

## Generation System

### Recommended Tool: DALL-E 3 API via script

- Cost: ~$0.04-0.08 per image
- Budget: $200 = 2,500-5,000 generations (plenty of headroom for
  iterations and rejects)
- Approach: Generate at 1024x1024 with precise pixel art prompts, then
  downscale and crop via Python post-processing

### Pipeline Architecture

```
prompt_generator.py        -- Builds prompts from data/metadata
  |
  v
api_caller.py              -- Calls DALL-E API, saves raw 1024x1024
  |
  v
post_processor.py          -- Crop, resize, format, validate
  |
  v
sprite_assembler.py        -- Combine frames into sheets (ships, portraits)
  |
  v
sprites/ directory         -- Final assets placed in correct locations
```

### Batch Strategy

Process categories in order of impact. Each batch uses a consistent
style prompt prefix to maintain visual coherence within the category.

---

## Batch 1: Enemy Ship Sprite Sheets (14 sprites)

**See**: `requirements/enemy_sprite_generation.md` (already written)

**Generation approach**:
- Prompt for a single 1024x1024 image containing 6 ship frames in a row
- Post-process: crop to 192x32 region, scale down if needed
- OR: Generate 6 individual frames and stitch into sheet

**Style prefix**:
> 32x32 pixel art spaceship sprite, top-down view, transparent
> background, dark hull with colored engine glow, clean readable
> silhouette, retro sci-fi aesthetic.

**Estimated cost**: 14 ships x 2 attempts average = ~28 images = ~$2

---

## Batch 2: Upgrade Icons (91 sprites)

### Why high priority
The shipyard Parts shop and the Loadout tab display upgrade icons
constantly. Missing icons show as blank space, making the UI feel
unfinished. Players browse these frequently when building their ship.

### Format
- 16x16 pixels, RGBA PNG, transparent background
- Color-coded by category (weapon=red, defense=blue, engine=orange,
  utility=green, cargo=brown, reactor=yellow, fuel=gray)

### Sub-categories

**Weapon upgrades (~25 missing)**:
- Laser/beam weapons: horizontal beam line, red/orange glow
- Missile/torpedo: small projectile shape, smoke trail
- Cannon/kinetic: barrel with muzzle flash
- Elemental: colored energy (blue=ion, red=plasma, cyan=cryo, purple=voltaic)

**Defense upgrades (~20 missing)**:
- Shield generators: circular shield icon, blue glow
- Armor plates: layered plate squares, gray/brown
- ECM/countermeasures: radar dish, green pulse

**Engine upgrades (~10 missing)**:
- Thrusters: flame/exhaust shape, orange/cyan
- Navigation: compass or star chart icon

**Utility upgrades (~15 missing)**:
- Sensors: antenna or eye icon, green
- Cargo: container or crate, brown
- Crew: person silhouette or bunk, warm tones
- Mining/salvage: pickaxe or claw, metallic

**Reactor upgrades (~10 missing)**:
- Power core: glowing orb, yellow/white
- Fuel: canister or tank, gray/blue

**Faction-specific upgrades (~11 missing)**:
- Use faction color + generic icon overlay

### Generation approach
- Generate in grid sheets (e.g., 8x8 grid of 16x16 icons = 128x128)
- One grid per sub-category for style consistency
- Post-process: split grid into individual 16x16 PNGs

**Style prefix**:
> 16x16 pixel art icon, transparent background, single game item,
> clean silhouette, [CATEGORY COLOR] color scheme, dark outline,
> retro sci-fi RPG style. No text.

**Estimated cost**: ~15 grid sheets x 3 attempts = ~45 images = ~$4

---

## Batch 3: Skill Tree Icons (74 sprites)

### Why high priority
The skill tree screen has 9 trees with 89 total skills. Players
reference this often when leveling. Missing icons make the tree feel
incomplete and harder to scan visually.

### Format
- 16x16 pixels, RGBA PNG, transparent background
- Color-coded by skill tree:
  - Trading: Gold (200, 180, 60)
  - Mining: Orange-brown (180, 120, 60)
  - Salvaging: Teal (60, 160, 140)
  - Refining: Red-orange (200, 100, 40)
  - Combat: Red (200, 60, 60)
  - Leadership: Purple (140, 80, 200)
  - Social: Blue (80, 140, 220)
  - Navigation: Cyan (60, 180, 200)
  - Survival: Green (80, 180, 80)

### Sub-categories by tree

**Combat skills (~15 missing)**:
- Damage bonuses: crossed swords, fist, explosion
- Accuracy: crosshair, eye
- Defensive: shield, dodge arrow
- Critical: star burst, lightning

**Social skills (~9 missing)**:
- Persuasion: speech bubble, handshake
- Intimidation: skull, fist
- Diplomacy: scroll, flag
- Reputation: star, badge

**Leadership skills (~7 missing)**:
- Crew bonuses: group silhouette, crown
- Morale: heart, flag
- Fleet: multiple ship silhouettes

**Trading skills (~5 missing)**:
- Price knowledge: coins, chart arrow
- Negotiation: scales, handshake
- Market: shopping bag, tag

**Gathering skills (~8 missing)**:
- Mining efficiency: pickaxe with sparkle
- Yield bonuses: gem, ore chunk
- Deep core: drill, depth gauge

**Special/passive skills (~30 missing)**:
- Various themed icons matching bonus type

### Generation approach
- Same grid approach as upgrades
- Group by tree for color consistency

**Style prefix**:
> 16x16 pixel art skill icon, transparent background, [TREE COLOR]
> color palette, symbolic representation of [SKILL CONCEPT], clean
> dark outline, retro RPG style. No text, no letters.

**Estimated cost**: ~12 grid sheets x 3 attempts = ~36 images = ~$3

---

## Batch 4: NPC Portraits (20 sprites)

### Why medium-high priority
NPCs appear in dialogue, cantina, crew roster, and station hub. Missing
portraits break immersion during story moments. The existing portraits
are 50x60 animated sheets with blinking/talking frames.

### Format
- Static: 50x60 PNG, RGBA
- Animated: 200x60 sprite sheet (4 frames of 50x60)
  - Frame 1: Neutral/idle
  - Frame 2: Eyes closed (blink)
  - Frame 3: Mouth open (talking)
  - Frame 4: Expression variant (smile/frown/concern)
- Pixel art style matching existing portraits

### Character descriptions
Each NPC needs a brief visual description:
- Species: All human (2335 setting, blended Earth cultures)
- Distinguishing features: clothing, accessories, faction colors
- Expression: Matches personality (gruff, cheerful, cunning, etc.)

### Existing portrait style reference
- Head and shoulders composition, 3/4 view facing slightly right
- Dark background gradient (not transparent -- portraits have bg)
- Consistent lighting from upper-left
- Visible faction-colored clothing accents

### Generation approach
- Generate each NPC as a single high-res portrait
- Downscale to 50x60
- Create blink/talk variants by editing the base frame
  (close eyes, open mouth -- can be done programmatically for pixel art)

**Style prefix**:
> 50x60 pixel art character portrait, head and shoulders, 3/4 view
> facing slightly right, dark gradient background, [CHARACTER
> DESCRIPTION], [FACTION COLORS] clothing accents, retro sci-fi RPG
> style, warm skin tones, expressive face.

**Estimated cost**: 20 portraits x 4 attempts = ~80 images = ~$6

---

## Batch 5: Faction Ground Tiles (32 sprites)

### Why medium priority
Ground exploration missions use tile-based maps. Currently only the
"neutral" tileset exists. 4 faction-specific tilesets would give each
faction's territory a distinct visual identity.

### Format
- 16x16 pixels, RGBA PNG
- Tileset per faction: floor, wall, door, decoration, hazard, terminal,
  crate, vent (~8 tiles per faction)

### Faction tile themes

**Commerce Guild (Nexus Trade)**:
- Clean, polished metal floors, gold accents
- Glass partitions, luxury materials
- Trade terminal screens, crate stacks

**Frontier Alliance (Free Salvagers)**:
- Rusted metal, jury-rigged panels, teal accents
- Exposed wiring, welded patches
- Salvage piles, makeshift barriers

**Miners Union (Forgeworks)**:
- Heavy industrial grating, orange warning stripes
- Furnace glow, soot-stained surfaces
- Ore carts, drilling equipment

**Science Collective (Axiom Research)**:
- Clean white/blue laboratory surfaces
- Holographic displays, specimen containers
- Data terminals, sensor arrays

### Generation approach
- Generate as 4x2 grid sheets (8 tiles per sheet = 128x32)
- One grid per faction for style consistency

**Style prefix**:
> 16x16 pixel art tileset, top-down view, [FACTION] themed space
> station interior, [FACTION COLORS], seamless edges where applicable,
> dark sci-fi aesthetic, clean readable at small size.

**Estimated cost**: 4 factions x 3 attempts = ~12 images = ~$1

---

## Batch 6: Combat Visual Effects (optional, low priority)

### What exists
- `combat/` directory has 6 VFX sprites
- Particle effects are mostly procedural (code-generated)

### What could be added
- **Elemental hit effects** (4 sprites): plasma burst (red), ion
  crackle (blue-white), cryo shatter (ice blue), voltaic arc (purple)
- **Shield impact** (1 sprite sheet): circular ripple, 4 frames
- **Explosion variants** (3 sprites): small, medium, large debris burst
- **Status effect icons** (5 sprites): burn, chill, frozen, suppressed,
  counterstrike stack indicators

### Format
- 32x32 or 16x16 depending on use
- Sprite sheets for animated effects (4-6 frames)

**Estimated cost**: ~10 images = ~$1

---

## Budget Summary

| Batch | Sprites | Images to Generate | Est. Cost |
|-------|---------|-------------------|-----------|
| 1. Enemy ships | 14 | ~28 | $2 |
| 2. Upgrade icons | 91 | ~45 | $4 |
| 3. Skill icons | 74 | ~36 | $3 |
| 4. NPC portraits | 20 | ~80 | $6 |
| 5. Ground tiles | 32 | ~12 | $1 |
| 6. Combat VFX | 13 | ~10 | $1 |
| **Total** | **244** | **~211** | **~$17** |
| Iteration budget (3x) | | ~633 | ~$51 |
| **With generous margin** | | | **~$75** |

Well under the $200 budget. The extra headroom allows for:
- Re-generating any sprites that don't match the style
- Experimenting with different prompt approaches
- Adding more sprites if new needs are discovered during review

---

## Post-Processing Pipeline

### Step 1: Raw generation
- Save 1024x1024 PNGs from API to `_raw/` directory
- Name convention: `{category}_{id}_raw.png`

### Step 2: Crop and resize
- Extract the relevant region from the generated image
- Downscale using nearest-neighbor (preserves pixel art crispness)
- Target sizes: 16x16, 32x32, 50x60 depending on category

### Step 3: Transparency cleanup
- Remove background (AI often generates non-transparent bg)
- Clean up stray pixels
- Ensure alpha channel is correct

### Step 4: Sheet assembly (for animated sprites)
- Stitch individual frames into horizontal sprite sheets
- Ships: 6 frames → 192x32
- Portraits: 4 frames → 200x60
- VFX: 4-6 frames → width varies

### Step 5: Validation
- Check dimensions match expected format
- Verify transparency
- Visual spot-check for style consistency
- Test in-game rendering

### Step 6: Placement
- Copy to correct `sprites/` subdirectory
- Update any manifest files if needed
- Run game to verify loading

---

## Implementation Script Outline

```python
# generate_sprites.py
# Run from project root

import openai
from PIL import Image
from pathlib import Path

CATEGORIES = {
    "enemy_ships": {
        "output_dir": "spacegame/data/assets/sprites/ships/enemies",
        "target_size": (192, 32),  # sheet
        "frame_size": (32, 32),
        "frame_count": 6,
    },
    "upgrades": {
        "output_dir": "spacegame/data/assets/sprites/upgrades",
        "target_size": (16, 16),
        "frame_count": 1,
    },
    # ... etc
}

def generate_sprite(prompt: str, category: str, sprite_id: str):
    """Generate a sprite via DALL-E API and post-process."""
    # 1. Call API
    # 2. Save raw
    # 3. Crop/resize
    # 4. Clean transparency
    # 5. Assemble sheet if needed
    # 6. Save to output_dir
    pass
```

---

## Execution Order

1. **Start with enemy ships** (Batch 1) -- most visible, already documented
2. **Upgrade icons** (Batch 2) -- highest count, immediate UI improvement
3. **Skill icons** (Batch 3) -- same workflow as upgrades
4. **NPC portraits** (Batch 4) -- requires more per-sprite customization
5. **Ground tiles** (Batch 5) -- grouped by faction, efficient batching
6. **Combat VFX** (Batch 6) -- optional polish layer
