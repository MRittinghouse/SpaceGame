# Ship Builder Polish Roadmap

> **Status**: PLANNING
> **Created**: 2026-03-26
> **Context**: After completing the Shipyard Revamp (S1-S6), this roadmap addresses
> builder experience improvements identified during playtesting. Focus: making the
> builder feel like constructing a starship, not editing a spreadsheet.

---

## Phase BP1: Live Ship Preview

> **Impact**: HIGH — closes the imagination gap between grid and ship
> **Effort**: LOW — composite renderer already exists

### What It Does
A real-time ship composite thumbnail in the builder corner that updates as slots
and hull pixels are placed. The player sees their ship taking shape visually as
they build, not just colored rectangles on a grid.

### Implementation
- [ ] Add a preview panel area (top-right or bottom-right of the builder, ~120x120px)
- [ ] On every slot placement/removal and hull pixel change, re-render the composite
- [ ] Use `ShipComposite.get_surface(scale=res_scale(2))` for the thumbnail
- [ ] Slots render as their type color within the composite (not pixel-art modules)
- [ ] Hull pixels render with their material colors (already works)
- [ ] Add a subtle panel background and "PREVIEW" label
- [ ] Fade-in when first content is placed, empty state shows ship outline silhouette
- [ ] Performance: throttle composite rebuild to max once per 0.5s (not every frame)

### Acceptance Criteria
- [ ] Preview updates within 0.5s of any grid change
- [ ] Preview correctly shows slot positions as colored regions
- [ ] Preview shows hull pixel materials
- [ ] Empty build shows a faint grid outline (not blank)
- [ ] No FPS impact (composite cached, not rebuilt per-frame)

---

## Phase BP2: Ship Naming

> **Impact**: HIGH — emotional attachment, cheapest feature with biggest payoff
> **Effort**: LOW — text input + save field already exists (player.ship_name)

### What It Does
Let the player name their ship at build confirmation time. The name persists in
the HUD, save files, and galaxy map. "The Midnight Runner" is a ship with a story.

### Implementation
- [ ] On CONFIRM BUILD, show a naming dialog before finalizing
- [ ] Text input field with placeholder: "Name your ship..."
- [ ] Default: frame name (e.g., "Light Freighter") if player skips
- [ ] Store in `player.ship_name` (field already exists, currently unused)
- [ ] Display ship name in:
  - Cockpit HUD (replace or supplement ship type display)
  - Galaxy map info card (below system info)
  - Save/load slot display
  - Build sharing codes (include name in export)
- [ ] Allow renaming later via the Drydock (without rebuilding)
- [ ] Character limit: 24 characters
- [ ] Filter: no empty names, trim whitespace

### Acceptance Criteria
- [ ] Name dialog appears on confirm
- [ ] Name persists across save/load
- [ ] Name appears in HUD and galaxy map
- [ ] Skipping the dialog uses the frame name as default
- [ ] Name survives frame upgrades (kept when buying new frame)

---

## Phase BP3: Build Rating

> **Impact**: MEDIUM-HIGH — engagement loop, "can I get an A?"
> **Effort**: MEDIUM — requires defining rating criteria and computing scores

### What It Does
A real-time rating displayed in the builder that evaluates the ship's design
quality across multiple axes. Not a gate (any valid build can be confirmed),
but a quality signal that encourages optimization.

### Rating Axes
- **Combat**: weapon slots, defense slots, reactor capacity, weapon coverage
- **Trade**: cargo slots, fuel capacity, cargo-to-weight ratio
- **Mobility**: engine count, weight ratio, evasion potential
- **Durability**: hull pixel count, armor material %, shield slots, structural integrity

### Rating Scale
S > A > B > C > D > F

Each axis is rated independently. Overall rating is the average, weighted by
the ship's apparent focus (a ship with 4 weapon slots is judged more on Combat).

### Implementation
- [ ] Create `spacegame/models/build_rating.py` with `compute_build_rating()` function
- [ ] Inputs: ShipBuild, slot_definitions, frame slot limits
- [ ] Outputs: dict of axis -> (letter_grade, numeric_score, feedback_text)
- [ ] Display in the stats panel or requirements panel as: `Combat: B+ | Trade: A-`
- [ ] Color-coded: S=gold, A=green, B=cyan, C=yellow, D=orange, F=red
- [ ] Feedback text explains low ratings: "Combat: C — only 1 weapon slot on a Large frame"
- [ ] Recalculate on every build change (cheap computation)

### Acceptance Criteria
- [ ] Rating updates live as slots are placed/removed
- [ ] Empty build shows "F" across all axes (or "--")
- [ ] Well-designed ships achieve A or S ratings
- [ ] Rating visible but not intrusive (doesn't block building)
- [ ] Feedback text helps new players understand what's suboptimal
- [ ] All tests pass — rating is informational, never blocks confirmation

---

## Phase BP4: Exposure Overlay

> **Impact**: MEDIUM-HIGH — makes spatial strategy visible and tangible
> **Effort**: MEDIUM — requires hit probability computation per grid cell

### What It Does
A toggleable overlay (like structural integrity) showing a heat map of combat
exposure across the ship. Front-facing areas glow red (high hit probability),
center areas are yellow, rear areas are green. Helps players understand WHY
slot placement matters for combat survivability.

### Combat Exposure Model
- **Frontal profile**: columns at the bow have higher hit weight
- **Pixel coverage**: areas with more pixels are larger targets
- **Slot vulnerability**: slots that are exposed (near edges, front-facing)
  are more likely to take direct hits
- **Protection depth**: slots buried behind hull pixels have natural armor

### Implementation
- [ ] Add "Exposure" toggle button next to existing Structural Integrity and CoM overlays
- [ ] Compute per-cell exposure score: 0.0 (protected) to 1.0 (maximally exposed)
- [ ] Exposure factors:
  - Column position (front = higher exposure, bow-weighted)
  - Edge proximity (outer cells more exposed than interior)
  - Pixel density around the cell (isolated cells = more exposed)
- [ ] Render as color gradient overlay: green (safe) -> yellow -> red (exposed)
- [ ] Highlight slots on the overlay with a brighter version of their exposure color
- [ ] Tooltip on hover: "This weapon slot has 72% exposure — enemies will target it often"
- [ ] Cache overlay computation (only recalculate when build changes)

### Acceptance Criteria
- [ ] Overlay toggled by checkbox in the OVERLAYS section
- [ ] Heat map visually communicates front-vs-rear exposure gradient
- [ ] Slots in exposed positions show high values
- [ ] Slots buried in the center show low values
- [ ] Overlay doesn't impact FPS (cached, computed once per change)
- [ ] Helps players make informed placement decisions

---

## Phase BP5: Audio Variety

> **Impact**: MEDIUM — builds atmosphere and feedback quality
> **Effort**: LOW — sound files + conditional SFX selection

### What It Does
Different placement sounds for different slot types. The builder should sound
like assembly — mounting weapons should clank differently than pressurizing
crew quarters.

### Sound Design
| Slot Type | Sound Character | Description |
|-----------|----------------|-------------|
| Cockpit | Electronic chirp | Control systems initializing |
| Weapon | Heavy metallic clank | Turret mounting, bolt locking |
| Defense | Resonant hum | Shield emitter charging |
| Engine | Deep mechanical thrum | Drive system connecting |
| Utility | Soft electronic beep | Sensor/computer activation |
| Fuel | Pressurization hiss | Tank sealing |
| Cargo | Hollow metallic thud | Bay locking into place |
| Crew Quarters | Airlock seal | Pressurization cycle |
| Reactor | Low power-up whine | Core ignition sequence |

### Implementation
- [ ] Create/source 9 short SFX clips (~0.3-0.5s each)
- [ ] Map slot_type to SFX ID in a constant dict
- [ ] Update `_place_slot_at()` to select SFX by slot type instead of generic "ui_build"
- [ ] Also update removal sound — single "disconnect" SFX for all types
- [ ] Hull pixel placement keeps existing sound
- [ ] Confirm build keeps existing celebration sound
- [ ] Volume: slot SFX at ~70% of UI volume (not jarring)

### Acceptance Criteria
- [ ] Each slot type has a distinct placement sound
- [ ] Sounds are short and satisfying, not annoying on repetition
- [ ] Removal has a single consistent sound
- [ ] Audio can be toggled off via settings (existing audio system)

---

## Stretch Goals (Require Additional Design)

### SG1: Template Ships

> **Effort**: MEDIUM — data creation + template loading UI
> **Prerequisite**: Core builder polish (BP1-BP5)

Pre-built slot layouts that new players can load as starting points. Reduces
blank-canvas intimidation and teaches good ship design by example.

**Templates needed** (one per archetype):
- "Combat Frigate" — weapon-heavy, 2 engines, minimal cargo
- "Trade Hauler" — cargo-heavy, 1 weapon for self-defense, large fuel
- "Fast Scout" — 2 engines, lots of utility (sensors), small and light
- "Balanced Explorer" — even distribution, medium everything
- "Mining Rig" — utility-heavy, extra fuel, minimal weapons
- "Armored Transport" — defense-heavy cargo ship

**Open questions**:
- Are templates per-frame-size? (Small Combat Frigate vs Large Combat Frigate)
- Can players save their own builds as templates?
- Should templates be discovered/unlocked, or always available?
- How does the UI present template selection? (overlay? separate tab?)

**Implementation sketch**:
- Templates stored as JSON (list of PlacedSlot with slot_def_ids and positions)
- "LOAD TEMPLATE" button in builder opens template browser
- Loading a template clears current slots and loads the template's layout
- Player can then modify freely before confirming
- Templates are read-only references, not editable themselves

---

### SG2: Color Themes & Decals

> **Effort**: HIGH — decal system, theme data, UI for placement
> **Prerequisite**: Core builder polish + live preview (BP1)

Quick-apply color themes and decorative decals for hull personalization.

**Color Themes**:
- Pre-defined palettes that recolor all hull pixels: "Military Green", "Corporate Blue",
  "Pirate Red", "Stealth Black", "Civilian White", "Racing Yellow"
- One-click apply from a theme picker in Hull mode
- Theme maps current materials to palette-appropriate colors
- Player can still manually override individual pixels after applying

**Decals/Markings**:
- Small pixel-art stamps placed on the hull: faction emblems, racing stripes,
  nose art, kill marks, custom patterns
- Decal library with ~20 designs (8x8 or 12x12 pixel art)
- Place by clicking on hull after selecting a decal
- Some decals unlocked via achievements or faction reputation
- Decals are cosmetic-only, no stat impact

**Open questions**:
- Do decals take up pixel grid space or overlay on top?
- Can decals overlap slots or only hull pixels?
- How are decals stored in ShipBuild? (separate layer? special pixel type?)
- Should decals be visible on the galaxy map ship sprite?
- Build sharing: do codes include decals?

---

## Implementation Order

| Phase | What | Priority | Effort |
|-------|------|----------|--------|
| **BP1** | Live Ship Preview | URGENT | Low |
| **BP2** | Ship Naming | URGENT | Low |
| **BP3** | Build Rating | HIGH | Medium |
| **BP4** | Exposure Overlay | HIGH | Medium |
| **BP5** | Audio Variety | HIGH | Low |
| **SG1** | Template Ships | STRETCH | Medium |
| **SG2** | Color Themes & Decals | STRETCH | High |

Recommended order: BP1 -> BP2 -> BP5 -> BP3 -> BP4 -> SG1 -> SG2

BP1 and BP2 are the cheapest, highest-impact changes. BP5 is quick audio work.
BP3 and BP4 are the meatier features that add strategic depth.
SG1 and SG2 are stretch goals that benefit from the core polish being in place.
