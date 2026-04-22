# UI Chrome Components

> **Status:** DESIGN — Tier 3 parallel-track doc. Formalizes the UI component patterns already present in `draw_utils.py` (573 lines), `table_widget.py`, `scrollable_panel.py`, `fonts.py`, and `engine/palettes.py`. Cross-references every Tier 2 doc's UI additions (stamps, badges, cards, overlays) so that new UI work consumes shared discipline rather than reinventing per-view.
>
> Inherits from `20_aesthetic_bible.md §2` (palette), `20_aesthetic_bible.md §7` (anti-patterns). Coordinates with `41_vfx_particle_vocabulary.md` (UI particle feedback) and every Tier 2 doc that introduced new UI components.

---

## Table of Contents

1. Current state — honest assessment
2. Chrome philosophy — the discipline
3. Typography system
4. Color and palette usage in UI
5. Panel and card system
6. Button and input components
7. Badge, stamp, and glyph system
8. Overlay and modal system
9. Navigation and layout patterns
10. Accessibility and colorblind discipline
11. Anti-patterns
12. Governance
13. Out of scope

---

## 1. Current state — honest assessment

### 1.1 What's already in place — the foundation

Aurelia's UI is **significantly standardized.** Key infrastructure:

- **`draw_utils.py`** (573 lines) — 9-slice panel renderer with cache, bar rendering (`draw_bar`), decorated panels (`draw_panel`), summary overlays, word-wrap, truncation, color helpers (`brighten`, `dim`)
- **`table_widget.py`** — shared table implementation (used across mission log, crew roster, dialogue choices)
- **`scrollable_panel.py`** — scroll math shared across views
- **`fonts.py`** — canonical font instances (`FONT_SM`, `FONT_MD`, `FONT_LG`, `FONT_HEADING`)
- **`engine/palettes.py`** — color mappings (rarity tints, status states, faction colors), complementing the `Colors` class in `config.py`
- **pygame_gui integration** — used for button/panel inputs in some views

**The 9-slice panel system** is particularly strong — generates pixel-art borders with alpha caching, memoized via `_nine_slice_cache`, used by 60+ call sites.

**Shared rendering utilities** are consistent — no view reimplements health bars, word-wrap, or ellipsis overflow.

### 1.2 What's weak — the central gap

**No vocabulary document.** Components exist and are consistent; nothing codifies "when to use a 9-slice panel vs a draw_panel vs a pygame_gui panel." Choice is by developer inclination or legacy convention. New Tier 2 docs reference components (card, stamp, badge, overlay) without knowing the canonical variant to consume.

The engineering is **coherent**. The decision-record is **tacit**.

### 1.3 Secondary gaps

**Gap 1: No explicit card taxonomy.** Each view implements cards somewhat differently (commodity cards in trading, module cards in ship builder, NPC cards in cantina, location cards in station hub). Common shape is there — the patterns aren't documented.

**Gap 2: No badge/stamp system.** Tier 2 docs introduced new visual elements: permit stamps (trading §4.6), faction insignia (station hub §4.8), affliction badges (ground §4.3), mastery glyphs (refining §8.1), tier glyphs (trading §4.3), landmark icons (galaxy §4.6). Currently each would be implemented ad-hoc. No shared badge rendering primitive.

**Gap 3: pygame_gui styling is ad-hoc.** Buttons and panels from pygame_gui use default theming; there's no centralized Aurelia theme config. Some views feel "pygame_gui-styled" rather than "Aurelia-styled."

**Gap 4: Overlay / modal discipline informal.** Dialogue, confirmation, cinematic, loading overlays exist but aren't built on a shared system. Transitions between modals vary.

**Gap 5: No documented typography tiers.** Fonts exist (`FONT_SM` through `FONT_HEADING`) but no rule for which font per context. Some views use `FONT_MD` for body; others use `FONT_SM`. Inconsistency is subtle but real.

**Gap 6: No accessibility / colorblind discipline documented.** Color-coded UI (danger levels, reputation states, legality tags) doesn't have a documented colorblind strategy. AB §2.4 commits to band-remap + role-remap functions; those don't exist yet at implementation layer.

### 1.4 What this doc addresses

- Gap 1 (card taxonomy) via §5 panel and card system
- Gap 2 (badge system) via §7 badge/stamp/glyph vocabulary
- Gap 3 (pygame_gui theming) via §6 button and input components
- Gap 4 (overlay discipline) via §8 overlay and modal system
- Gap 5 (typography tiers) via §3 typography
- Gap 6 (accessibility) via §10 accessibility and colorblind

---

## 2. Chrome philosophy — the discipline

### 2.1 The four rules

**1. Chrome serves content.** UI chrome (borders, backgrounds, icons, stamps) is framing. Content (text, data, gameplay state) is primary. Chrome that pulls focus from content is wrong.

**2. Palette compliance is sacrosanct.** Every pixel in UI chrome uses a `PALETTE_ROLES` entry (AB §2.3). No hand-tuned hex values. Colorblind remapping works because chrome is palette-indexed.

**3. Consistency beats cleverness.** A commodity card and a module card are *both cards*. They share layout primitives even when their content varies. Divergence without justification is drift.

**4. Density respects clarity.** Information-dense UI (trading, builder, galaxy map) requires strict typography discipline; density without hierarchy is noise.

### 2.2 Voice

The UI carries Aurelia's voice per AB §1. Specific implications:

- **Brutalist-industrial** (per AB §1.1) — angular, honest, functional. No glass-skeuomorphic / iOS / glossy effects. Panel borders are pixel-precise, not smoothly-beveled.
- **Data-legible** — numbers and labels prioritized. Decoration is minimal and earned.
- **Faction-reactive** — UI picks up faction color accents where context warrants (station hub faction chrome, mission cards for faction missions). Base chrome stays palette-neutral; accents layer.
- **Warm-industrial in defaults** — base UI uses warm-neutral palette (warmth +14 per AB §2). Cool accents reserved for tech / information contexts (HUD cyan, sensor data).

### 2.3 Tonal rules

- **Panels are containers, not decorations.** A panel's job is to group content; its border + background serve that job, not the other way around.
- **Cards signal "this is a discrete item."** Card borders + accents communicate boundaries between items in a list.
- **Modals interrupt with purpose.** An overlay means "something needs your attention now." Non-critical notifications don't overlay.
- **Buttons are actions.** Buttons *do something*. Text labels are descriptions. A button should be obvious; a label should be readable.
- **Badges are small signals.** Badges are 8-16px glyphs carrying one piece of meaning. Many small badges on one element is noise; one or two is signal.

---

## 3. Typography system

### 3.1 Font tiers

Canonical instances in `fonts.py`:

| Tier | Size | Usage | Example |
|---|---|---|---|
| **FONT_HEADING** | 32pt | View titles, chapter headers, cinematic names | "GALAXY MAP", "DOCKED — NEXUS PRIME", dual-tech name |
| **FONT_LG** | 22pt | Subsection headers, notable stats, damage-number tier 4 | "YOUR CARGO", damage number for cinematic hits |
| **FONT_MD** | 16pt | Primary body text, labels, standard damage numbers | Commodity name, stat values, chatter lines |
| **FONT_SM** | 12pt | Secondary context, tooltips, minor labels | Faction name on card, timestamp, tier 1 damage numbers |
| **FONT_TINY** | 9pt | Ticker crawls, small metadata, debug | News ticker text, version string |

### 3.2 Pairing rules

Each UI context pairs tiers:

| Context | Primary | Secondary | Hierarchy |
|---|---|---|---|
| Standard card | FONT_MD (content) | FONT_SM (metadata) | 16pt + 12pt |
| Information panel | FONT_LG (heading) | FONT_MD (body) | 22pt + 16pt |
| View header | FONT_HEADING + FONT_MD (subtitle) | — | 32pt + 16pt |
| Tooltip | FONT_MD | FONT_SM | Compact pair |
| Ticker | FONT_TINY | — | Minimal footprint |
| Dialogue | FONT_MD | FONT_SM (speaker name) | Hierarchy via weight |

### 3.3 Weight and style

pygame `Font.set_bold(True)` / `set_italic(True)` used sparingly:

- **Bold** — emphasis only; numerical stand-outs; heading subtype; damage tier 4
- **Italic** — skill voice lines (per mini-game identity docs); flavor text; NPC internal thoughts

Default is regular weight. Bold/italic for specific purposes, not decoration.

### 3.4 Typography compliance

Every view's text rendering must go through canonical font instances. Hardcoded font construction (`pygame.font.Font(None, 18)`) is banned post-migration. Audit task: grep for `pygame.font.Font(` in views; migrate to `fonts.FONT_*` imports.

---

## 4. Color and palette usage in UI

### 4.1 Role-to-UI mapping

UI elements map to `PALETTE_ROLES` entries (AB §2.3):

| Role | Primary use |
|---|---|
| `void_deep` | View backgrounds (when space is the backdrop) |
| `void_mid` | Panel backgrounds (when content panels need contrast against void_deep) |
| `void_light` | Subtle dividers, scrollbar tracks |
| `hud_text` | Primary text on dark backgrounds |
| `hud_text_dim` | Secondary text, metadata, inactive labels |
| `hud_muted` | Disabled elements, unavailable state |
| `hud_cyan` | Primary interactive accent (button hover, focused input, primary CTA) |
| `hud_warning` | Warnings (amber), restricted items, timer approaching limits |
| `hud_critical` | Critical alerts (red), failed actions, hostile state |
| `hud_accent_warm` | Secondary warm accent (faction cross-refs, cooperative chrome) |
| `rivet` | Seam details, pixel-art borders (darker) |
| `rivet_gloss` | Highlight pixels on borders, subtle reflections |
| `seam` | Panel seams, card divisions |
| `weld` | Decorative accents (station hub, industrial UI) |
| Emissive roles (`plasma_core`, `cryo_fractal`, `ion_arc`, `voltaic_strike`, `glow_warm`, `glow_cool`) | UI elements that represent elemental/tech content (dual-tech glyphs, shield indicators, element-specific feedback) |

### 4.2 Faction color overlays

Per AB §4.8, faction colors are applied as **accent layers** on base UI:

| Faction | Accent role / tint |
|---|---|
| Commerce Guild | `hud_cyan` variant (brighter cyan) |
| Miners Union | `union_ceramic_bright` (warm gold) |
| Frontier Alliance | `frontier_canvas` band mid (warm earth) |
| Science Collective | `collective_composite` base (cool blue-white) |
| Crimson Reach | `reach_crimson` band base (deep crimson) |

Faction-themed UI elements (mission cards for faction quests, reputation indicators, station hub faction chrome) use these accents as border stripes, badge background, or tint overlays — never as primary text color (legibility).

### 4.3 State color discipline

UI state colors are palette-mapped, consistent across views:

| State | Role | Example |
|---|---|---|
| Normal / neutral | `hud_text` | Default text |
| Hover | `brighten(hud_text, 15%)` | Mouse-over |
| Selected / focused | `hud_cyan` border + `void_light` background | Active selection |
| Disabled | `hud_muted` | Non-interactive |
| Success / positive | `hud_cyan` or `cryo_fractal` (context-specific) | Completed, profitable, safe |
| Warning | `hud_warning` | Caution, restricted, time-pressured |
| Critical / negative | `hud_critical` | Failed, hostile, illegal |

### 4.4 The `brighten()` / `dim()` helpers

`draw_utils.brighten(color, amount)` and `dim(color, amount)` exist for state transitions. They:

- Operate on any RGB tuple
- Preserve palette-family membership (a brightened `hud_cyan` is still cyan-family)
- Are used for hover states, subtle highlights, momentary emphasis

**Don't** use them to produce off-palette colors — the helpers are for *transient* states, not permanent UI elements. Permanent UI colors come from `PALETTE_ROLES` directly.

---

## 5. Panel and card system

### 5.1 Panel taxonomy

Three canonical panel types:

**Type A: 9-slice panel (`draw_nine_slice_panel`)**
- Pixel-precise border with 4px corner + 1px highlight/shadow
- Used for: info panels, modals, content frames within views
- Best when: panel should feel like a physical UI element with depth
- Memoized via `_nine_slice_cache`

**Type B: Decorated panel (`draw_panel`)**
- Single-color background with border and optional corner-radius
- Used for: sub-panels within 9-slice containers, standalone info zones
- Best when: lighter visual weight needed; nested inside another panel

**Type C: Pygame_gui panel**
- Framework-provided panel
- Used for: interactive containers needing pygame_gui button/panel children
- Best when: input-heavy forms (ship builder dialogs, contract acceptance)

**Rule of thumb:** default to Type A (9-slice). Use Type B for nested sub-panels. Use Type C only when pygame_gui's interactive behaviors are required.

### 5.2 Card anatomy

A **card** is a bounded rectangle representing a discrete item. Canonical anatomy:

```
┌─────────────────────────────────────────────────────┐
│ [icon/sprite] TITLE TEXT       [tier-glyph] [badge] │   ← Header row
│ ──────────────────────────────────────────────────  │   ← Divider (seam role)
│ Primary body content                                │   ← Content area
│ - Stat chips  [+4 CR] [−2 WT]                       │   ← Stats row
│ - Secondary metadata                                │   ← Metadata (FONT_SM)
│ Accent stripe (left edge, faction color if applicable) ← Persistent accent
└─────────────────────────────────────────────────────┘
```

**Components:**
- **Border:** 9-slice, 2px typical
- **Header:** title (FONT_MD) + up to 2 right-aligned glyphs/badges
- **Divider:** 1px line in `seam` role (only if card is tall enough to warrant)
- **Content:** main body (FONT_MD / FONT_SM as appropriate)
- **Stat chips:** small rounded-rect pills with icon + number (see §5.3)
- **Accent stripe:** optional 2-3px left edge stripe in faction or contextual color

**Sizing:**
- **Compact card:** 200-280px wide, 40-60px tall — for dense lists (trading commodities pre-overhaul, crew roster)
- **Standard card:** 400-600px wide, 80-100px tall — for detail lists (new trading rows per §34, module catalog)
- **Hero card:** 800-1000px wide, 150-200px tall — for feature items (selected module preview, mission briefing)

### 5.3 Stat chips

Small inline stat indicators. Anatomy:

```
[icon] +4 CR     ← Positive stat (green-shifted text or hud_cyan)
[icon] −2 WT     ← Negative stat (hud_warning or hud_critical)
[icon] 124 CR    ← Neutral value
```

- Rounded rectangle background with subtle fill (`void_light` tint)
- Icon on left (8-12px), value on right (FONT_SM)
- Color per value-direction: positive = hud_cyan / success-green; negative = hud_warning; neutral = hud_text

### 5.4 Per-Tier-2-doc card variants

Each Tier 2 doc introduced specific card variants. All inherit from §5.2 anatomy:

| Source | Variant | Key chrome elements |
|---|---|---|
| Trading §34 §4.1 | Commodity row | sprite + name + tier-glyph + faction-glyph + legality-stamp + price + sparkline + volatility pip bar + supply depth bar |
| Ship builder §31 §4.3 | Module catalog card | module preview (rendered large) + name + manufacturer glyph + stats + delta chips + manufacturer signature |
| Station hub §35 | Location card | icon + name + type-label + description + left accent stripe + hover-state transition |
| Mining §32 §8.7 | Recipe card (Claim Ledger mastery) | mastery stars + recipe name + progress bar + gold-mastery stamp if earned |
| Salvage §36 §8.4 | Broker card | broker portrait + name + specialty label + rep-tier indicator + buying-priorities text |
| Ground §38 | Mission briefing card | mission type glyph + location name + difficulty tier + objective list + crew-slot selectors |
| Cantina NPC card | NPC portrait + name + role + dialogue hook line | Used existing pattern |

### 5.5 Card hover / selection states

Unified across all card variants:

- **Normal:** base palette rendering
- **Hover:** background brightens 10-15%, border color shifts to `brighten(border, 20%)`, optional subtle accent (right-arrow or chevron indicating interactability)
- **Selected:** `hud_cyan` border accent + background tinted 8% toward cyan
- **Disabled / unavailable:** overall opacity drops to 40%, badge added indicating reason (e.g., "LOCKED", "NOT HERE")

### 5.6 Journal surface family (canonical)

*Added post-corpus-coherence-review.* Four Tier 2 docs introduced persistent "player's personal journal" UI surfaces, each with distinct aesthetic but shared anatomy:

| Surface | Source | Aesthetic treatment |
|---|---|---|
| **Claim Ledger** | Mining (32 §8.7) | Aged paper with hand-drawn border motifs — prospector's field journal |
| **Wrecker's Log** | Salvage (36 §8.4) | Battered leather notebook — wrecker's logbook |
| **Fabricator's Register** | Refining (37 §8.7) | Institutional-clean workshop notebook — grid lines, precise margin notes |
| **Expedition Log** | Ground (38 §5.5) | Field-book pragmatic — expedition record-keeping |

**Shared anatomy** (all four adopt this structure, different aesthetic treatments):

- Section tabs (top) — campaign / register / correspondence / archive / statistics / thought cabinet
- Entry-list panel (left or scrollable) — chronological or categorical
- Entry-detail panel (right or expanded) — readable content + metadata + cross-references
- Metadata strip (bottom) — total counts, last-updated, filter state

**Shared behaviors:**
- All entries persistent across save/load
- All entries re-readable indefinitely
- Accessible from system view AND from a station hub (or appropriate home)
- Cross-reference hyperlinks where narrative content connects to other tracks

**Implementation:** a base `JournalSurface` component in `ui_components/` consumed by each system's specific realization. Aesthetic differentiation via theme override per instance. Palette-compliant across all four.

### 5.7 Skill voice corner region (canonical)

*Added post-corpus-coherence-review.* Three Tier 2 docs introduced a shared inner-voice UI element (Disco Elysium-inspired).

**Specification:**
- Position: bottom-left corner of the relevant view; anchored, does not move
- Size: ~300×60px at 1080p, scales with resolution
- Typography: `FONT_MD` italic (serif variant for differentiation from UI sans-serif)
- Text color: skill-specific palette role (§4.1) with subtle stroke for legibility
- Animation: 0.8s hold + 0.6s fade per line
- Queue discipline: lines don't queue — if multiple skills trigger, priority goes to most-relevant-to-event
- Idle state: corner is empty / transparent

**Consumers:**
- Mining (32 §5.2 + §8.5) — 5 skill voices (Ore Sense, Seismic Instinct, Union Heart, Deep Ear, Weathered Hands)
- Salvage (36 §5.2) — 5 skill voices (Forensic Eye, Wreck Logic, Ghost Channel, Trained Hand, Buyer's Memory)
- Refining (37 §5.2) — 5 skill voices (Material Sense, Heat Eye, Recipe Memory, Patient Hand, Quality Ear)

**Implementation:** a shared `SkillVoiceOverlay` component, instantiated per view with skill-voice content registered. Palette-colored per skill role. All three systems consume the same primitive.

---

## 6. Button and input components

### 6.1 Button taxonomy

Three canonical button types:

**Type A: Primary button (full chrome)**
- 9-slice border with chrome fill
- `FONT_MD` label
- Hover: border brightens + subtle highlight on inner fill
- Click: brief 2px depression animation
- Used for: primary actions (Buy, Confirm, Travel, Undock)

**Type B: Secondary button (outline)**
- Border-only (no fill)
- `FONT_MD` label
- Hover: fills with low-alpha color
- Used for: secondary actions (Cancel, Back, Skip)

**Type C: Icon button (glyph-only)**
- Icon in a small rect, no label
- Used for: toolbar actions (zoom, filter, sort)

### 6.2 Button styling

| Property | Value |
|---|---|
| Primary fill | `void_mid` base with `hud_cyan` hover tint |
| Secondary outline | `hud_text_dim` → `hud_text` on hover |
| Disabled | `hud_muted` across all button types |
| Label | `hud_text` (primary), `hud_text_dim` (secondary) |
| Hover feedback | Combined: background tint shift + label brighten + optional particle (`CLICK_HIT` on click) |

### 6.3 pygame_gui button theming

pygame_gui buttons use a centralized theme config — **Aurelia Theme JSON** (to be authored). Sets:

- Border style, corners, fill colors for default/hover/pressed/disabled
- Font references (pointing to `fonts.FONT_MD` etc.)
- Shadow/highlight pixel offsets

Theme config lives in `spacegame/data/ui_theme.json`, loaded at view init. All pygame_gui buttons get Aurelia look-and-feel automatically.

### 6.4 Input components

| Input type | Style | Notes |
|---|---|---|
| Text input | Rectangular input with 9-slice border; `hud_cyan` focus border | Used for quantity fields, naming, search |
| Numeric input (with increments) | Text input + increment buttons (Type C) | Per trading §34 §4.7; hybrid input |
| Slider | Horizontal track with handle; track in `void_mid`, handle in `hud_cyan` | Volume controls, quantity sliders |
| Dropdown | Rectangular display + dropdown arrow; opens panel overlay with selectable options | Faction filter, sort order |
| Toggle / checkbox | 16×16 box with check on toggle-on; `hud_cyan` when active | Settings toggles |
| Radio button | 14×14 circle with fill on select | Choice-between options |

### 6.5 Focus and keyboard navigation

All interactive elements support keyboard focus:

- Tab cycles forward through interactive elements
- Shift+Tab cycles backward
- Enter activates focused button / submits input
- Arrow keys navigate within lists and dropdowns
- Esc cancels modals / returns from menus

Focused element visible via `hud_cyan` outline at 2px thickness.

---

## 7. Badge, stamp, and glyph system

The Tier 2 docs introduced a proliferation of small visual markers. This section formalizes them.

### 7.1 Badge taxonomy

**Badges** are small (12-20px) visual markers that carry one piece of metadata. Three types:

**Type A: Status badge** — indicates state (locked / available / new / warning)
- Rounded rectangle background + icon or short text
- Color-coded per state

**Type B: Glyph** — indicates category or type (tier, faction, element)
- Flat icon, no background
- Typically single-color, palette-sourced

**Type C: Stamp** — heavier state indicator (PERMIT, RESTRICTED, ILLEGAL, APPROVED)
- Rectangular background with text + optional icon
- Higher visual weight than a glyph

### 7.2 Catalog of badges, glyphs, stamps from Tier 2 docs

| Source | Type | Element |
|---|---|---|
| Trading §34 §4.3 | Glyph | Commodity tier (bulk / standard / premium / luxury / restricted / illegal) |
| Trading §34 §4.3 | Glyph | Faction affinity (Collective cross, Reach crossed-bolts, Union hex, Alliance star, Guild tri) |
| Trading §34 §4.6 | Stamp | PERMIT (amber) / RESTRICTED (red) / ILLEGAL (heavy red) / APPROVED (green) |
| Galaxy §33 §4.6 | Glyph | Landmark type (wreck, legendary seam, anomaly, quest, home) |
| Station hub §35 §4.8 | Glyph | Faction insignia (5 hand-authored pixel artworks) |
| Station hub §35 §4.2 | Badge | Service availability (UNAVAILABLE / LOCKED / QUEST REQUIRED / TEMPORARY CLOSURE) |
| Mining §32 §8.1 | Badge | Mastery tier (bronze / silver / gold stars) |
| Mining §32 §5.3 | Badge | Thought cabinet progress |
| Salvage §36 §8.7 | Badge | Collector's Wall equip indicator |
| Refining §37 §9.1 | Badge | Quality grade (C / B / A / S) |
| Refining §37 §7.1 | Badge | Masterwork Stamp (for equipped masterworks on ship modules) |
| Ground §38 §4.3 | Badge | Affliction state (Shaken / Wounded / Fatigued / etc.) + Virtue state (Focused / Hardened / Bonded) |
| Combat §30 §4.2 | Badge | Module targeted state (pre-fire / committed / damaged / destroyed) |
| Combat §30 §4.7 | Badge | Damage number tier (1-4) — though this is typography-weight more than a badge per se |

Total: **~40 distinct badges / glyphs / stamps** introduced across Tier 2.

### 7.3 Badge rendering primitives

To prevent ad-hoc implementation, `draw_utils.py` gains canonical functions:

```python
def draw_badge(surface, rect, background_role, label_text=None, icon_surface=None,
               border_role=None, alpha=255) -> None: ...

def draw_glyph(surface, pos, glyph_id, color_role=None, size=12) -> None: ...

def draw_stamp(surface, rect, stamp_type, text=None) -> None: ...
```

**Glyph library** — all Tier 2 glyphs (§7.2) defined as pixel-art data in a shared glyph sheet (`spacegame/data/assets/ui/glyphs.png`). Each glyph has a canonical ID referenced by name.

### 7.4 Badge rendering discipline

- Maximum 2 badges + 1 stamp on a single card (beyond that, the card becomes noise)
- Badges stack right-to-left from the right edge
- Stamps positioned inline with text, not floating (anchored to context)
- Glyphs position per context; typically inline with related text

### 7.5 Badge color compliance

Badges draw colors from:
- Status badges: state palette (hud_critical, hud_warning, hud_cyan, hud_muted)
- Glyphs: context-relevant palette role (faction glyphs use faction colors, element glyphs use element emissive roles)
- Stamps: state palette + their label

All badge colors are role-indexed per §4.1.

---

## 8. Overlay and modal system

### 8.1 Overlay taxonomy

Four canonical overlay types:

**Type A: Dialogue overlay**
- Full-screen semi-transparent tint (`void_deep` at 40% alpha)
- Dialogue panel centered, 9-slice panel
- Used for: NPC dialogue, crew conversations, narrative beats

**Type B: Confirmation modal**
- Tight overlay centered on screen
- Dark-tinted backdrop (`void_deep` at 60%)
- Used for: confirm-travel, confirm-build, confirm-purchase, cancel-mission

**Type C: Cinematic overlay**
- Full-screen darken with cinematic bars (optional top/bottom dark bands)
- Used for: dual-tech cinematic, prestige cinematic, arena-entry, jump sequence

**Type D: Notification overlay**
- Edge-anchored small panel (typically top-right or bottom)
- Non-blocking — game continues
- Used for: event notifications, new-entry-added, achievement unlocked

### 8.2 Overlay timing

| Overlay | Transition in | Hold | Transition out |
|---|---|---|---|
| Dialogue | 0.3s fade | (dialogue duration) | 0.3s fade |
| Confirmation | 0.2s scale+fade | (indefinite, awaits input) | 0.2s fade |
| Cinematic | 0.5s darken | (sequence duration) | 0.5s restore |
| Notification | 0.2s slide-in | 3-5s visible | 0.4s slide-out |

### 8.3 Overlay priority

Only one blocking overlay active at a time. If a blocking overlay would trigger while another is active:

- Queue (low-priority): notification overlays queue and surface after current blocker resolves
- Replace (high-priority): critical events (combat-end, system-critical) interrupt dialogue

Non-blocking notifications can stack (up to 3 visible simultaneously at edge).

### 8.4 Backdrop discipline

All blocking overlays darken the backdrop to focus attention:

- **Dialogue:** 40% alpha — underlying scene faintly visible
- **Confirmation:** 60% alpha — more decisive backdrop
- **Cinematic:** 80% alpha or full blackout — maximum focus

Non-blocking notifications have no backdrop tint.

---

## 9. Navigation and layout patterns

### 9.1 View hierarchy

Aurelia's views organize into four layers:

1. **Primary views** (one at a time) — galaxy map, station hub, combat, trading, ship builder, mining, salvage, refining, ground exploration
2. **Sub-views within primary** — tabs within shipyard (Drydock / Frames / Parts / Equipment)
3. **Overlays on primary/sub** — dialogues, confirmations, modals (§8)
4. **Persistent chrome** — cockpit HUD (when not in specific views), notification zone

### 9.2 Tab patterns

When a primary view has multiple conceptual sections (shipyard, station hub locations, journal sections):

- Horizontal tab row at top of view
- Active tab: brightened background + `hud_cyan` bottom border (2px)
- Inactive tab: `void_mid` background + `hud_text_dim` label
- Hover tab: brightens toward active state

### 9.3 Toolbar patterns

Tool/action rows within a view (e.g., hull pixel mode tools in ship builder):

- Row of icon buttons (Type C from §6.1)
- Selected tool: `hud_cyan` border accent + active fill
- Tooltip on hover showing tool name + keyboard shortcut

### 9.4 Pagination and scrolling

- Long lists use scrollable panels (`scrollable_panel.py`)
- Scrollbar on right, 8px wide
- Scrollbar thumb: `hud_text_dim` base, `hud_cyan` on drag
- Mouse-wheel scrolls content; arrow keys move selection

### 9.5 Breadcrumbs and navigation back

Views that allow deep navigation (e.g., shop sub-tabs within station hub within system within galaxy):

- Back button (Esc key): always available, top-left
- Breadcrumb text in header: "Galaxy › Nexus Prime › Shipyard › Parts"
- Clicking a breadcrumb level jumps back to it

### 9.6 Layout grid

Views use a **soft 12-column grid** for alignment. Not strict — allows freedom — but provides cohesion. Standard breakpoints:

- **Left panel:** columns 1-3 (25%)
- **Center:** columns 4-9 (50%)
- **Right panel:** columns 10-12 (25%)

Mining / salvage / combat typically 3-column; ship builder 2-column; galaxy map center-dominant with edges thin.

---

## 10. Accessibility and colorblind discipline

### 10.1 Colorblind philosophy

Per AB §2.4, Aurelia commits to **band-remap + role-remap functions** for colorblind modes. UI chrome must respect this:

- Every color in UI is palette-indexed (§4.1) — not a raw RGB
- A colorblind-remap function can transform `hud_critical` → a high-contrast cyan for red-blind, `hud_warning` → high-contrast purple for yellow-blind, etc.
- All views consume the remap automatically because they use role names, not hex values

### 10.2 Colorblind modes (planned)

v1 planned:
- **Protanopia** — red-blind remapping
- **Deuteranopia** — green-blind remapping
- **Tritanopia** — blue-blind remapping

Not implemented yet; reserved scope. Implementation requires:
1. Remap function per colorblind mode (maps each `PALETTE_ROLES` entry to an alternate entry)
2. Settings toggle in player menu
3. Audit pass verifying no hand-tuned colors slipped through

### 10.3 Non-color accessibility

State communication does not rely on color alone:

- Success / warning / critical states have icons in addition to colors
- Reputation tiers have both color and label ("Hostile" text, not just red pip)
- Legality stamps have text ("PERMIT", "RESTRICTED") in addition to color
- Gameplay feedback has audio + visual + often text (damage numbers are text, color-coded)

**Rule:** any single state indicator should be understandable with color disabled. Shape, icon, label, or position must carry signal independent of color.

### 10.4 Text sizing

UI supports a **text size multiplier** (settings, deferred). Values: 100% (default), 115%, 130%. Applied to font sizes at render time. Layout gracefully handles — word-wrap + container reflow.

### 10.5 Keyboard navigation

All UI interactable via keyboard (§6.5). Mouse-dependent interactions (drag-and-drop) are avoided or have keyboard equivalents.

### 10.6 Motion reduction

Setting toggle (deferred): "Reduce motion" disables or attenuates:
- Cinematic overlays → skip to result
- Jump sequences → shortened
- Particle bursts → simpler
- Camera shake → off
- Tickets / scrolling text → static

---

## 11. Anti-patterns

### 11.1 Reimplementing the panel

**Don't:** a new view drawing its own rectangles + borders in `render()`.

**Do:** use `draw_nine_slice_panel()` or `draw_panel()` per §5.1. If the need doesn't fit existing panel types, extend `draw_utils` with a new canonical type (governance §12).

### 11.2 Hand-tuning colors

**Don't:** `color=(110, 130, 150)` in a view's render code. Might be close to some palette role, but palette drift.

**Do:** `color=PALETTE_ROLES["hud_text_dim"]` or `color=rgb("hud_muted")`. If no role matches, a new role gets added to the Bible.

### 11.3 Font construction in views

**Don't:** `font = pygame.font.Font(None, 18)` in a view. Drifts from the tier system.

**Do:** `from spacegame.engine.fonts import FONT_MD`. If a size is needed that isn't covered, add to `fonts.py` rather than constructing inline.

### 11.4 Ad-hoc badge drawing

**Don't:** each view drawing its own rounded-rect + icon + text for a "new" badge.

**Do:** `draw_badge(surface, rect, "warning", label_text="LOCKED")`. Badge styling is centralized per §7.3.

### 11.5 Mixed pygame_gui / custom rendering

**Don't:** using pygame_gui buttons for some actions and custom-rendered buttons for others on the same view.

**Do:** choose one approach per view. If pygame_gui is in use, all buttons in that view use pygame_gui. Theme JSON ensures consistency across views (§6.3).

### 11.6 Informative-by-color-only

**Don't:** reputation indicated solely by colored pip. Red-blind player has no signal.

**Do:** combined color + icon + optional label. Tooltip on hover provides full context.

### 11.7 Overlay stacking

**Don't:** dialogue overlay opens, and during dialogue a confirmation overlay also opens. Player UI is now 3-level-deep.

**Do:** confirm overlays only appear after dialogue closes. Priority system (§8.3) enforces.

### 11.8 Chrome that pulls focus

**Don't:** animated borders, glowing outlines on static panels, decorative flourishes that repeat every frame.

**Do:** chrome is still. Transitions happen on state change; ambient UI is motion-quiet.

---

## 12. Governance

### 12.1 Adding a new component

Triggers:
- A Tier 2 doc references a UI element not in the catalog
- Implementation phase encounters a gap

Process:
1. Propose component name, anatomy, intended use cases
2. Coordinate with at least one consumer (Tier 2 doc or view)
3. Add entry to this doc
4. Implement in `draw_utils.py` or new `ui_components/` file
5. Provide migration docs if replacing an older ad-hoc implementation

### 12.2 Theme evolution

The pygame_gui theme JSON (`data/ui_theme.json`) is the central visual config for pygame_gui elements. Updates:

1. Propose change (typography, color, spacing)
2. Test against at least 5 views using pygame_gui
3. Coordinate with audit — verify no regressions
4. Version the theme; migration path if breaking

### 12.3 Audit tasks

Periodic audits:
- Font usage — grep for `pygame.font.Font(` in views; migrate to canonical fonts
- Color usage — grep for raw RGB tuples; migrate to palette roles
- Badge implementations — review for ad-hoc rendering; migrate to canonical primitives
- Overlay usage — confirm no stacking violations

### 12.4 Versioning

This doc versions as chrome scope expands. Revision history at header.

---

## 13. Out of scope

- **3D UI elements** — strictly 2D
- **CSS-style cascading stylesheets** — not adopting DOM-style architecture
- **Procedurally-generated UI layouts** — layouts are authored per view
- **Animation-heavy UI (Lottie, complex motion)** — static UI with state-transition-only animation
- **Touch-gesture support** — desktop-only; mouse + keyboard
- **HTML/web renderer integration** — pure pygame-ce rendering
- **Accessibility beyond §10** — v1 scope; deeper accessibility pass is a future initiative

---

*Revision history:*
- *v1 — initial UI chrome vocabulary doc. Formalizes existing `draw_utils`, `TableWidget`, `scrollable_panel`, `fonts` infrastructure; catalogs 40+ badges/glyphs/stamps from Tier 2 docs; establishes typography and palette discipline at UI layer.*

*Tier 3 parallel-track docs complete. The three parallel-track Tier 3 docs (`40_audio_synthesis_framework.md`, `41_vfx_particle_vocabulary.md`, `42_ui_chrome_components.md`) establish cross-cutting standards that every Tier 2 implementation consumes. Together with Tier 0 master plan, Tier 1 framework docs (10-12, 20), and Tier 2 overhauls (30-38), the design corpus is complete.*

*Next phase: **implementation**. Pick a first phase to build (candidates: Combat C1 camera + pacing beats; Ship Builder B1 hangar environment + preview pipeline; Mining M1 balance formalization; Audio A1 music/ambient orchestration wiring). Infrastructure phases unblock the most downstream work.*
