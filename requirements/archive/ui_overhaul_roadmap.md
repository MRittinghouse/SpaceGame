# UI Overhaul: Refined Pixel Art Polish Pass

## Context

The game's UI is functional but has significant visual weaknesses that undermine the quality of the content beneath it. The station hub screenshot reveals the core issues: massive dead space between card grid and chatter area, text overflow on card titles, no visual hierarchy (everything is the same weight), inconsistent spacing, and no station-specific personality. These problems repeat across most views.

The direction is **Refined Pixel Art**: keep the pixel fonts, sprite assets, and 9-slice panels, but make everything cleaner, better-spaced, and more professional. Reference games: FTL, Starsector, Into The Breach. Evolutionary improvement, not a redesign.

## Universal Problems (Affect All Views)

### 1. Layout Constants Are Scattered
Every view defines its own padding, card sizes, margins. No shared vocabulary. Result: inconsistent spacing across screens.

**Fix**: Create `spacegame/views/layout.py` with shared constants: standard margins, card sizes, button heights, padding scales. Views import from this instead of defining locally.

### 2. Color Values Duplicated and Inconsistent
Faction colors defined separately in station_hub_view, cockpit_hud, and config.py with different RGB values. Some views use hardcoded RGB tuples instead of named constants.

**Fix**: Consolidate all color definitions into `Colors` class in config.py. Remove per-view color dicts. Add faction-accent colors that both HUD and station views reference.

### 3. Text Overflow Everywhere
Card titles truncate mid-word. Descriptions clip. Long NPC names overflow buttons. The width compensation system helps fonts fit, but containers don't adapt.

**Fix**: Add `truncate_text(text, font, max_width, suffix="...")` utility to draw_utils. Apply it consistently to all card titles, button labels, and description text. For descriptions, use word-wrap with explicit line limits.

### 4. Dead Space / Poor Vertical Distribution
The station hub has a 300px void between cards and chatter. Other views have similar gaps. Content clusters at the top, leaving the bottom empty.

**Fix**: Per-view layout restructuring. Each view should use available space proportionally. Cards should expand to fill, or supplementary content (station art, faction info, ambient details) should occupy the gap.

### 5. No Visual Hierarchy
Every element has the same visual weight. Headers, cards, buttons, chatter, and HUD all feel equally prominent.

**Fix**: Establish a 3-tier hierarchy:
- **Primary**: Screen title + main action area (largest, brightest)
- **Secondary**: Content panels and cards (medium, standard colors)
- **Tertiary**: Ambient text, status bars, contextual info (smallest, muted)

### 6. Hover/Selection States Inconsistent
Some buttons change color on hover, some don't. Some use pygame_gui hover, some use manual tracking. No consistent "selected" visual.

**Fix**: Standardize hover behavior: border brightens, subtle background shift. Standardize selection: thicker border or accent stripe. Apply to all interactive elements.

### 7. No Station-Specific Personality
Every station looks the same except for the header text. Iron Depths should feel different from Stellaris Port.

**Fix**: Faction-based accent color applied to panel borders, header underline, and card edges. Each faction gets a subtle tint: Guild (blue), Union (amber/gold), Collective (purple/teal), Alliance (green). Applied via the station's faction_id.

---

## Per-View Improvements

### Station Hub (Priority: HIGH — first impression when docking)

**Current problems** (from screenshot):
- 300px dead space between cards and chatter
- Card titles overflow ("Core Station Exchang...")
- Cards are too small for their content
- Rigid 4+2 grid leaves bottom row unbalanced
- Activity type labels (TRADE, REPAIR) compete with bay numbers
- No visual connection between header and content

**Fixes**:
- **Expand cards vertically**: Increase card height from 80px to ~110px. This gives room for full title + 2-line description without clipping.
- **Fill layout**: If fewer than 4 cards in bottom row, center them. Add station portrait or faction emblem in the freed space.
- **Simplify card header**: Remove "BAY XX" numbering. Players don't care about bay numbers. Show activity type as a colored badge (top-right), title as the primary element.
- **Add faction accent**: Thin colored line under the header matching the station's faction. Card borders tinted with faction color at reduced opacity.
- **Station description panel**: Move the atmospheric flavor text from the header into a mid-screen panel with more room. The header should just be station name + faction + danger.
- **Chatter card**: Increase height slightly, add subtle panel background matching faction accent.

### Galaxy Map (Priority: HIGH — primary navigation)

**Current problems**:
- System info cards appear on hover but feel disconnected
- Route lines are plain
- Mission target indicators are small
- Little sense of scale or distance

**Fixes**:
- **System hover cards**: Standardize card size, use faction-tinted border, show system name prominently with faction emblem.
- **Route preview**: When hovering a destination, show dotted route line with distance and travel time.
- **Mission markers**: Larger, pulsing indicators for active quest targets. Different icon for "NPC here" vs. "deliver cargo here."
- **System labels**: Always visible system names (not just on hover) at reduced opacity. Currently players must hover each dot to find where they want to go.

### Combat View (Priority: HIGH — most time-intensive view)

**Current problems**:
- 3,770 lines of code — the view is doing too much rendering work
- Player/enemy panels are dense with small text
- Move buttons are tightly packed
- Action queue display is small
- Momentum/energy bars compete for attention

**Fixes**:
- **Panel clarity**: Increase bar heights from 14px to 18px. Add labels ABOVE bars instead of inline (avoids overlap when bars are short).
- **Move button sizing**: Slightly larger buttons with clearer category tabs. Current 3-tab system (Attack/Defend/Utility) is good but tabs are small.
- **Enemy cards**: More vertical spacing between stacked enemy cards. Add faction emblem or ship class icon.
- **Action queue**: Enlarge the queue display panel. Show queued actions with move icons, not just text.
- **Floating damage numbers**: Ensure font size is readable at all resolutions. Current FONT_HEADING (32) may be too large at 720p, too small at 1080p.

### Ship Builder (Priority: MEDIUM — complex but less frequent)

**Current problems**:
- Very dense layout with 3 side panels + grid + stats
- Module catalog scrolling can feel cramped
- Stats panel at bottom competes with HUD

**Fixes**:
- **Catalog panel**: Slightly wider with clearer category headers. Show module preview on hover.
- **Grid**: Cleaner grid lines with subtle faction-tinted background.
- **Stats panel**: Move above HUD with clear separation. Use paired layout (stat name: value) with aligned columns.

### Trading View (Priority: MEDIUM)

**Current problems**:
- Two tables (market + cargo) leave little room for prices
- Buy/Sell buttons are small
- Transaction feedback is easy to miss

**Fixes**:
- **Table readability**: Slightly larger row heights. Alternating row backgrounds for scan-ability.
- **Price highlighting**: Color-code prices relative to base (green = below average, red = above).
- **Transaction feedback**: Larger, centered confirmation with brief animation.

### Cockpit HUD (Priority: HIGH — always visible)

**Current problems**:
- Navigation buttons use cryptic abbreviations (CPT, SKL, CRW, MSN, JRN)
- Bar labels (HULL, SHLD, FUEL) are tiny
- Notification badges are small red dots

**Fixes**:
- **Button labels**: Expand to full words if space allows at higher resolutions: "Captain", "Skills", "Crew", "Missions", "Journal". At 720p, keep abbreviations but add tooltip on hover.
- **Bar labels**: Slightly larger font. Use color-coding: hull (green), shield (blue), fuel (orange/yellow).
- **Notification badges**: Larger, with count number. Pulse animation for new notifications.
- **Credits display**: Slightly larger, with comma formatting already in place.

### Mission Log (Priority: MEDIUM)

**Current problems**:
- Objective details (from Q7) need visual testing at all resolutions
- Reward display could be clearer

**Fixes**:
- **Objective indent hierarchy**: Checkmark + description + location detail should have clear indent levels.
- **Reward icons**: Small colored dots or icons for credit/XP/rep rewards instead of text-only.

### Dialogue View (Priority: LOW — recently improved in SP4)

**Recent SP4 additions** (disposition bar, floating feedback, subtext) need visual QA at all resolutions. Otherwise the dialogue view is relatively clean.

### Crew Roster, Skill Tree, Character Sheet (Priority: LOW)

These views work but would benefit from the universal improvements (consistent spacing, hover states, faction accents).

---

## Implementation Phases

### Phase U1: Foundation — Shared Layout System + Color Consolidation
- Create `spacegame/views/layout.py` with shared constants
- Consolidate all faction colors into config.py Colors class
- Add `truncate_text()` utility to draw_utils
- Add standard hover/selection color computation functions
- No visual changes yet — just infrastructure

### Phase U2: Station Hub Overhaul
- Restructure card layout (larger cards, centered rows, no bay numbers)
- Fill dead space (station personality area or expanded cards)
- Apply faction accent colors to borders and header
- Fix text overflow on all card elements
- QA at all 3 resolutions

### Phase U3: Cockpit HUD Polish
- Expand navigation button labels at higher resolutions
- Larger bar labels with color coding
- Enhanced notification badges (count + pulse)
- Faction-specific accent tint on HUD border

### Phase U4: Galaxy Map Improvements
- Always-visible system labels (dimmed)
- Standardized hover cards with faction tint
- Route preview with distance/time
- Larger mission target markers

### Phase U5: Combat View Clarity
- Larger bars with external labels
- More spacing in enemy card stack
- Enlarged action queue display
- Move button sizing improvements

### Phase U6: Trading + Minor View Polish
- Table row alternation
- Price color-coding
- Larger transaction feedback
- Apply universal improvements to remaining views

### Phase U7: Visual QA Pass
- Test all views at 720p, 900p, 1080p
- Text overflow audit at all resolutions
- Hover state audit (every interactive element)
- Screenshot comparison before/after

---

## Key Files

**New**:
- `spacegame/views/layout.py` — shared layout constants

**Modified heavily**:
- `spacegame/config.py` — consolidated Colors, faction accents
- `spacegame/engine/draw_utils.py` — truncate_text, hover helpers
- `spacegame/views/station_hub_view.py` — layout restructure
- `spacegame/views/cockpit_hud.py` — label expansion, badge enhancement
- `spacegame/views/galaxy_map_view.py` — labels, hover cards, route preview
- `spacegame/views/combat_view.py` — bar sizing, spacing, queue display

**Modified lightly** (universal improvements):
- `spacegame/views/trading_view.py`
- `spacegame/views/mission_log_view.py`
- `spacegame/views/crew_roster_view.py`
- `spacegame/views/skill_tree_view.py`
- `spacegame/views/ship_builder_view.py`

## Verification
- Visual QA at all 3 resolutions after each phase
- Existing tests must pass (UI changes are rendering-only, no model changes)
- Screenshot comparison (before/after per view)
