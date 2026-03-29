# Enemy Ship Sprite Generation Guide

Reference document for generating the 14 missing enemy sprite sheets.

## Technical Specifications

### Format
- **File**: PNG, RGBA (transparent background)
- **Sheet size**: 192x32 pixels (6 frames laid out horizontally)
- **Frame size**: 32x32 pixels each
- **Frame count**: 6 frames, looping idle animation at 0.5s/frame
- **Background**: Fully transparent (alpha = 0)

### Orientation
- Ships face **LEFT** (nose/prow points left, engines/exhaust on the right)
- This is the native enemy orientation in combat (enemies appear on the
  right side of the screen, facing left toward the player)
- Player ships face RIGHT, but are stored as separate sprites

### Animation Sequence (6 frames)
The 6 frames represent a subtle idle loop. Existing sprites vary by:
- **Engine glow pulse**: Exhaust/thruster glow brightens and dims across
  frames (frames 1-3 dim, frames 4-6 bright, or vice versa)
- **Running lights blink**: Small navigation lights toggle on/off
- **Shield shimmer**: Subtle color shift on hull edges
- Keep the ship body consistent across all frames; only small details
  should change (lights, glow, energy effects)

### Art Style
- **Pixel art**, 32x32, consistent with existing game sprites
- Ships should fill most of the 32x32 frame (use 24-30px of width)
- Dark hull colors with colored accent lighting (engines, weapons, faction markings)
- Top-down or 3/4 top-down perspective (slight angle, not pure side view)
- Clean silhouette that reads well at small size
- No background elements (stars, debris) -- just the ship on transparent

### Color Palette Conventions
- Hull: Dark grays, browns, dark blues (base metal)
- Engines: Cyan/blue (standard), orange/red (military), green (stealth)
- Weapons: Red/orange barrel tips or glow
- Shields: Light blue aura (only on shielded ships)
- Faction accents: see faction colors below

---

## Faction Color Reference

| Faction | Primary Accent | Secondary | Notes |
|---------|---------------|-----------|-------|
| Nexus Trade Consortium | Gold (200, 180, 60) | White | Trade/commerce vessels, clean lines |
| Forgeworks Industrial | Orange (200, 120, 40) | Dark gray | Heavy armor, industrial plating |
| Free Salvagers Union | Teal (60, 180, 160) | Rust brown | Jury-rigged, mismatched parts |
| Axiom Research | Blue-white (100, 160, 240) | Silver | Sleek, scientific, sensor arrays |
| Crimson Reach (pirates) | Red (200, 60, 40) | Dark red | Aggressive, spiky, intimidating |
| Neutral/Generic | Blue-gray (100, 120, 150) | — | Standard military/patrol look |

---

## Ships to Generate (14 total)

### Batch 1: Regular Enemies (9 ships)

**1. armored_transport**
- Role: Heavily armored cargo hauler (non-combat focused)
- Size: Large silhouette (28-30px wide), bulky rectangular body
- Color: Dark gray hull, reinforced plate textures, small orange engine glow
- Details: Cargo container shapes visible on hull, minimal weapons
- Animation: Slow engine pulse, running lights

**2. cryo_interceptor**
- Role: Fast attack craft, ice/cryo weapons
- Size: Narrow sleek profile (24-26px wide), angular wedge shape
- Color: White-blue hull, ice-crystal blue weapon tips, cyan engine trail
- Details: Crystalline weapon pods on wings, frost effect on hull edges
- Animation: Cyan engine glow pulse, weapon tips shimmer blue-white

**3. ghost_raider**
- Role: Stealth raider, hit-and-run
- Size: Medium (22-24px), low-profile angular shape
- Color: Very dark gray/near-black hull, faint cyan edge lighting
- Details: Minimal silhouette, stealth panels, dim engine signature
- Animation: Edge lights fade in/out subtly, near-invisible in dim frames

**4. guild_arbiter**
- Role: Nexus Trade Consortium authority/enforcement vessel
- Size: Medium-large (26-28px), authoritative wedge with command bridge
- Color: White hull with gold trim, official-looking stripes
- Details: Gold faction emblem area, sensor dish, weapon turrets
- Animation: Gold running lights pulse, engine glow steady cyan

**5. ion_striker**
- Role: Fast attack, ion/electric weapons
- Size: Small-medium (20-24px), dart-like profile
- Color: Dark blue hull, bright electric yellow/blue weapon glow
- Details: Twin ion emitters on nose, lightning-arc effect between frames
- Animation: Ion weapon tips crackle (yellow-blue alternation), fast engine

**6. plasma_bomber**
- Role: Heavy bomber, plasma weapons, wide profile
- Size: Wide and bulky (28-30px wide, 20px tall), bomber silhouette
- Color: Dark red-brown hull, orange-red plasma glow from weapon bays
- Details: Underslung bomb bays or plasma chambers, wide wing profile
- Animation: Plasma chambers glow and pulse red-orange, heavy engine trail

**7. rogue_ai_vessel**
- Role: Autonomous AI ship, geometric/alien design
- Size: Medium (24-26px), angular/hexagonal shape (unusual geometry)
- Color: White/light gray hull with red sensor eye/light, precise edges
- Details: Geometric panels, single red "eye" sensor, no organic curves
- Animation: Red sensor pulses, geometric panels shift subtly

**8. shield_drone**
- Role: Small support drone, shield generation
- Size: Small (14-18px), compact spherical or octagonal shape
- Color: Blue-white body, bright blue shield bubble effect around it
- Details: Central core with radiating shield emitter lines
- Animation: Shield bubble pulses brighter/dimmer, core light rotates

**9. support_frigate**
- Role: Medium support ship, repair/buff capabilities
- Size: Medium (24-26px), elongated medical/support profile
- Color: White hull with green cross or green accent stripe
- Details: Repair beam emitter (green glow), antenna array
- Animation: Green repair beam glow pulses, antenna lights blink

### Batch 2: Legendary Bosses (5 ships)

Boss sprites should feel LARGER and more imposing than regular enemies,
even within the 32x32 frame. Fill the entire frame, use bolder colors,
and make the animation more dramatic.

**10. corsair_king**
- Role: LEGENDARY pirate flagship, ultimate pirate boss
- Size: Fill frame (30-32px), massive warship profile
- Color: Dark crimson hull, gold trim, skull or crown motif
- Details: Bristling weapon batteries (many turret dots), armored prow,
  tattered flag/banner element, gold crown detail
- Animation: Weapons glow red in sequence, gold trim pulses, dramatic
  engine flare

**11. iron_maw**
- Role: LEGENDARY industrial fortress-ship, Forgeworks boss
- Size: Fill frame (30-32px), blocky industrial mass
- Color: Dark iron/rust hull, molten orange glow from furnace interior
- Details: Open "maw" (front opening with orange glow), industrial
  smokestacks, grinding teeth/plate shapes at the prow
- Animation: Furnace glow pulses orange-red, smoke particles (darker
  pixels shifting), grinding maw opens/closes slightly

**12. ledger_phantom**
- Role: LEGENDARY ghost ship, stealth boss
- Size: Medium-large (26-28px), ethereal/translucent feel
- Color: Dark hull that FADES to semi-transparent at edges, ghostly
  blue-white glow, spectral trail
- Details: Partially transparent hull sections, glowing blue data-stream
  lines along hull, phantom afterimage effect
- Animation: Ship flickers between solid and translucent across frames,
  data lines scroll, ghost trail shifts

**13. the_collector**
- Role: LEGENDARY trophy hunter, bizarre alien-hybrid ship
- Size: Fill frame (30-32px), asymmetric/unusual silhouette
- Color: Dark hull covered in different-colored trophy fragments (bits
  of other ship colors welded on), green tractor beam glow
- Details: Mismatched hull sections (different colors/textures suggesting
  salvaged ship parts), tractor beam emitter, trophy spikes
- Animation: Tractor beam pulses green, trophy fragments glint different
  colors across frames

**14. void_leviathan**
- Role: LEGENDARY organic/hybrid monster ship, cosmic horror
- Size: Fill frame (30-32px), organic flowing shape unlike any other ship
- Color: Deep purple-black hull, bioluminescent magenta/violet glow lines
- Details: Tentacle-like appendages, organic curves instead of angular
  hull, glowing void "eyes" or energy nodes, eldritch feel
- Animation: Bioluminescent lines pulse in wave pattern, tentacles shift
  position slightly, void glow intensifies and fades

---

## File Naming Convention

Output files should be named: `{enemy_id}_sheet.png`

Place in: `spacegame/data/assets/sprites/ships/enemies/`

Examples:
- `armored_transport_sheet.png`
- `corsair_king_sheet.png`
- `void_leviathan_sheet.png`

---

## Prompt Template for AI Image Generation

For each ship, adapt this template:

> Pixel art sprite sheet, 192x32 pixels, 6 frames of 32x32 each, laid
> out horizontally left to right. Transparent background. Top-down or
> slight 3/4 perspective spaceship facing LEFT. [SHIP DESCRIPTION].
> Frames show subtle idle animation: [ANIMATION DETAILS]. Pixel art
> style, dark space game aesthetic, clean readable silhouette at small
> size. No background, no text, no border.

---

## Validation Checklist

After generating each sprite:
- [ ] File is exactly 192x32 pixels, RGBA PNG
- [ ] Background is transparent (not black)
- [ ] Ship faces LEFT across all 6 frames
- [ ] Ship body is consistent across frames (only lights/glow change)
- [ ] Silhouette reads clearly at 32x32 (not too detailed/muddy)
- [ ] Colors match faction palette where applicable
- [ ] Boss sprites feel larger/more imposing than regular enemies
