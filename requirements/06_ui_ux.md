# UI/UX Requirements

> **Implementation Status** (Updated 2026-02-27): CORE COMPLETE + PHASE 1
>
> - **Views implemented**: 15 total — main menu, galaxy map, trading, mining, salvage, refining, skill tree, shipyard, save/load, settings, pause menu, startup, statistics, achievements, event notification
> - **UI framework**: pygame_gui integrated with themed JSON (`spacegame/data/theme.json`)
> - **Visual systems**: Animated parallax backgrounds, particle effects (6 presets), screen transitions (fade, warp, slide), vignette overlay, screen shake
> - **Input**: Mouse + keyboard support via InputHandler
> - **Design principles**: Implemented as specified — clarity, minimal clicks, persistent status display
> - **Tutorial UI**: IMPLEMENTED — 5-step tutorial with auto-trigger on new game, skip option, replay from settings, tutorial overlay system
> - **Statistics view**: IMPLEMENTED — categorized player stats (Economic, Exploration, Activities, Progression)
> - **Achievements view**: IMPLEMENTED — scrollable achievement list with progress bars, locked/unlocked states, reward info
> - **Event notifications**: IMPLEMENTED — modal dialog for DISASTER events, timed banner for SHORTAGE/SURPLUS/BOOM, galaxy map indicators
> - **Dialogue UI**: NOT IMPLEMENTED — Phase 2+ (campaign)
> - **Mission log UI**: NOT IMPLEMENTED — Phase 2+ (campaign)

## 1. Overview

The UI/UX defines how players interact with the game. It must be intuitive, informative, and efficient for a trading simulation while maintaining visual appeal within PyGame's 2D constraints.

## 2. Design Principles

### 2.1 Core Principles

1. **Clarity Over Flash** - Information must be immediately readable
2. **Minimize Clicks** - Common actions should require few inputs
3. **Always Informed** - Player should always know their status (credits, cargo, fuel, location)
4. **Consistent Layout** - Similar actions work similarly everywhere
5. **Forgiveness** - Allow undo or confirmation for major decisions
6. **Keyboard + Mouse** - Support both input methods

### 2.2 Visual Style

- **Aesthetic**: Clean, utilitarian space UI (think NASA/SpaceX interfaces)
- **Color Palette**: Dark backgrounds, bright text, accent colors for highlights
- **Typography**: Monospace or sans-serif, high readability
- **Iconography**: Simple, clear icons for common actions
- **Theme**: Professional trader terminal, not military combat UI

### 2.3 Accessibility

- **Font Size**: Minimum 12-14px, scalable
- **Color Blindness**: Don't rely solely on color (use icons/text)
- **High Contrast**: Text readable on all backgrounds
- **Tooltips**: Hover explanations for all UI elements

## 3. Screen Layouts

### 3.1 Main Menu

**Components:**
- Game Title/Logo (top center)
- Menu Options (center):
  - New Game
  - Continue (if save exists)
  - Load Game
  - Options
  - Credits
  - Quit
- Background: Static starfield or subtle animation

**Layout:**
```
┌────────────────────────────────────┐
│                                    │
│         SPACE TRADER               │
│                                    │
│         [New Game]                 │
│         [Continue]                 │
│         [Load Game]                │
│         [Options]                  │
│         [Credits]                  │
│         [Quit]                     │
│                                    │
└────────────────────────────────────┘
```

### 3.2 Galaxy Map View (Primary Gameplay Screen)

**Layout Regions:**

```
┌──────────────────────────────────────────────────────┐
│ HEADER: Credits | Fuel | Cargo | Location     [Menu] │
├──────────────────────────────────────────────────────┤
│                                                      │
│                                                      │
│                  GALAXY MAP                          │
│            (Interactive star systems)                │
│                                                      │
│                                                      │
├────────────────────────┬─────────────────────────────┤
│  SYSTEM INFO PANEL     │   QUICK ACTIONS             │
│  - Name                │   [Travel]                  │
│  - Type                │   [Trade]                   │
│  - Stations            │   [Ship]                    │
│  - Distance            │   [Map]                     │
└────────────────────────┴─────────────────────────────┘
```

**Components:**

#### Header Bar (Always Visible)
- **Credits**: Current credits with color coding
- **Fuel**: Current/Max with visual gauge
- **Cargo**: Used/Max with visual fill indicator
- **Location**: Current system name
- **Menu Button**: Access to settings, save, quit

#### Galaxy Map (Center - Main Focus)
- Visual representation of star systems (nodes)
- Connection lines between systems
- Current location highlighted (pulsing or distinct color)
- Systems color-coded by faction or danger
- Clickable systems for details
- Zoom/pan controls (if large map)

#### System Info Panel (Bottom-Left)
- Selected system details
- Distance from current location (in jumps)
- Fuel cost estimate
- Stations available
- Faction control
- Reputation level

#### Quick Actions (Bottom-Right)
- **Travel**: Open travel planning/confirmation
- **Trade**: Open market (if at station)
- **Ship**: Open ship management
- **Map**: Toggle map overlays (faction, danger, etc.)

### 3.3 Trading Interface

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ TRADING POST: [Station Name]            [Back to Map]│
├──────────────────────────────────────────────────────┤
│                                                      │
│  MARKET COMMODITIES          │  YOUR CARGO           │
│  ┌─────────────────────────┐ │ ┌──────────────────┐ │
│  │ Food          50 CR  ↑  │ │ │ Food       20    │ │
│  │ [Buy] [Sell]            │ │ │ Electronics 15   │ │
│  │                         │ │ │                  │ │
│  │ Metals        120 CR ↓  │ │ │ Free: 45/200     │ │
│  │ [Buy] [Sell]            │ │ │                  │ │
│  │                         │ │ └──────────────────┘ │
│  │ Electronics   300 CR →  │ │                      │
│  │ [Buy] [Sell]            │ │                      │
│  └─────────────────────────┘ │                      │
│                                                      │
│  TRANSACTION SUMMARY                                 │
│  Credits: 12,500 CR                                  │
│  Pending: -2,000 CR (buying 40 Food)                 │
│  Result: 10,500 CR                                   │
│                               [Confirm] [Cancel]     │
└──────────────────────────────────────────────────────┘
```

**Components:**

#### Market List (Left)
- All commodities available at this station
- Display per item:
  - Commodity name
  - Price per unit
  - Trend indicator (↑↓→ or color)
  - Comparison to average ("+15% above avg")
  - Buy/Sell buttons
- Sortable by name, price, or profit potential

#### Your Cargo (Right)
- List of commodities in cargo hold
- Quantity of each
- Free space remaining
- Total cargo capacity
- Quick "Sell All" option per commodity

#### Transaction Summary (Bottom)
- Current credits
- Pending transaction value
- Resulting credits after transaction
- Cargo space impact
- Confirm/Cancel buttons

#### Buy/Sell Modal
```
┌─────────────────────────────┐
│ BUY: Food                   │
│ Price: 50 CR/unit           │
│ Available: 500 units        │
│                             │
│ Quantity: [___] [Max]       │
│                             │
│ Total Cost: 0 CR            │
│ Cargo Space: 0 units        │
│                             │
│     [Confirm]   [Cancel]    │
└─────────────────────────────┘
```

### 3.4 Ship Management Screen

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ SHIP MANAGEMENT                          [Back]      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  CURRENT SHIP: Light Freighter "Endeavor"           │
│  ┌────────────────────────────────────────────────┐ │
│  │ [Ship Image/Icon]                              │ │
│  │                                                │ │
│  │ Cargo:    150 units                            │ │
│  │ Fuel:     200 units                            │ │
│  │ Efficiency: 15 units/jump                      │ │
│  │ Value:    25,000 CR                            │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  UPGRADES:                                           │
│  ┌────────────────────────────────────────────────┐ │
│  │ □ Cargo Expansion (+20%)    Cost: 5,000 CR    │ │
│  │ ✓ Fuel Tank Upgrade         Installed         │ │
│  │ □ Engine Efficiency         Cost: 8,000 CR    │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  [Visit Shipyard]  [Repair Ship]  [Rename]          │
└──────────────────────────────────────────────────────┘
```

**Components:**
- Current ship display with stats
- Visual ship representation (icon or sprite)
- Installed upgrades list (checkmarks)
- Available upgrades with costs
- Actions: Shipyard (buy new), Repair, Rename

### 3.5 Shipyard (Purchase) Screen

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ SHIPYARD: Available Ships                [Back]      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  YOUR SHIP: Light Freighter    │  AVAILABLE SHIPS   │
│  Trade-In Value: 17,500 CR      │                    │
│                                 │  Medium Freighter  │
│  ┌───────────────────────────┐  │  Price: 100,000 CR │
│  │ Cargo:     150            │  │  Cargo:    300     │
│  │ Fuel:      200            │  │  Fuel:     250     │
│  │ Efficiency: 15/jump       │  │  Efficiency: 20/j  │
│  └───────────────────────────┘  │                    │
│                                 │  [View Details]    │
│                                 │  [Purchase]        │
│                                 │                    │
│                                 │  Heavy Hauler      │
│                                 │  Price: 500,000 CR │
│                                 │  ...               │
└──────────────────────────────────────────────────────┘
```

**Components:**
- Current ship summary + trade-in value
- List of available ships at this shipyard
- Side-by-side stat comparison
- Purchase options (trade-in or direct buy)

### 3.6 Travel Planning Screen

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ TRAVEL: From [Alpha] to [Beta]          [Cancel]     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ROUTE:                                              │
│  Alpha → Beta (1 jump)                               │
│                                                      │
│  Fuel Required: 15 units                             │
│  Current Fuel: 85/200 units                          │
│  Remaining: 70 units                                 │
│                                                      │
│  Estimated Time: Instant (or 1 day, 5 seconds, etc.) │
│  Danger Level: Safe                                  │
│                                                      │
│  [Confirm Travel]  [Cancel]                          │
└──────────────────────────────────────────────────────┘
```

### 3.7 Pause/Options Menu

**Components:**
- Resume Game
- Save Game
- Load Game
- Settings:
  - Volume controls
  - Screen resolution
  - Key bindings
  - UI scale
- Help/Tutorial
- Quit to Main Menu
- Quit to Desktop

### 3.8 Player Statistics Screen

**Layout:**
```
┌──────────────────────────────────────────────────────┐
│ PLAYER STATISTICS                        [Back]      │
├──────────────────────────────────────────────────────┤
│  WEALTH:                                             │
│  Current Credits: 125,450 CR                         │
│  Lifetime Earned: 387,230 CR                         │
│  Total Profit: 62,780 CR                             │
│                                                      │
│  TRADING:                                            │
│  Trades Completed: 156                               │
│  Largest Single Profit: 12,450 CR                    │
│                                                      │
│  EXPLORATION:                                        │
│  Systems Discovered: 18/25 (72%)                     │
│  Total Jumps: 243                                    │
│                                                      │
│  REPUTATION:                                         │
│  Trade Federation: 67 (Respected)                    │
│  Industrial Consortium: 42 (Friendly)                │
│  Colonial Union: 12 (Neutral)                        │
│                                                      │
│  ACHIEVEMENTS: 12/35 Unlocked                        │
│  [View Achievements]                                 │
└──────────────────────────────────────────────────────┘
```

## 4. UI Components and Widgets

### 4.1 Standard Buttons

- **Dimensions**: 120x40px minimum
- **Hover State**: Highlight border or color shift
- **Click State**: Slight depression or flash
- **Disabled State**: Grayed out with reduced opacity
- **Text**: Centered, clear, action-oriented

### 4.2 Lists and Tables

- **Rows**: Alternating colors for readability
- **Hover**: Highlight row on mouseover
- **Selection**: Distinct color/border for selected item
- **Scrollbar**: Visible when content exceeds viewport
- **Headers**: Bold, sortable (click to sort)

### 4.3 Input Fields

- **Text Input**: Clear border, placeholder text
- **Number Input**: +/- buttons, numeric validation
- **Max Button**: Auto-fill maximum affordable/available
- **Enter to Confirm**: Keyboard shortcut support

### 4.4 Progress Bars and Gauges

- **Fuel Gauge**: Horizontal bar, color-coded (green > yellow > red)
- **Cargo Fill**: Visual representation (e.g., "145/200")
- **Reputation Bar**: Progress toward next level
- **Health/Ship Condition**: If applicable

### 4.5 Tooltips

- **Trigger**: Hover for 0.5 seconds
- **Content**: Brief explanation, shortcut keys
- **Position**: Near cursor, avoid blocking critical UI
- **Styling**: Semi-transparent background, border

### 4.6 Notifications and Alerts

#### Toast Notifications (Bottom-Right)
- Small pop-ups for non-critical events
- Examples: "Trade completed", "Achievement unlocked"
- Auto-dismiss after 3-5 seconds
- Stack if multiple occur

#### Modal Alerts (Center Screen)
- Critical information or confirmations
- Examples: "Not enough fuel", "Purchase ship?"
- Require user action to dismiss
- Dim background to focus attention

### 4.7 Icons

- **Commodity Icons**: Unique for each commodity type
- **System Icons**: Visual distinction for system types
- **Ship Icons**: Different for each ship class
- **Action Icons**: Trade, Travel, Ship, Map, Settings
- **Status Icons**: Trend arrows, danger warnings, faction logos

## 5. Interaction Patterns

### 5.1 Mouse Controls

- **Left Click**: Select, confirm, activate
- **Right Click**: Context menu, quick actions (optional)
- **Hover**: Tooltips, highlights
- **Scroll Wheel**: Zoom map, scroll lists
- **Drag**: Pan map (optional)

### 5.2 Keyboard Controls

**Global Hotkeys:**
- **ESC**: Pause menu / Back to previous screen
- **M**: Toggle galaxy map
- **T**: Open trading (if at station)
- **S**: Ship management
- **P**: Player stats
- **Space**: Confirm travel / Advance dialogue
- **F5**: Quicksave
- **F9**: Quickload

**Navigation:**
- **Arrow Keys**: Navigate lists, map (optional)
- **Tab**: Cycle through UI elements
- **Enter**: Confirm selection
- **Number Keys**: Quick-select commodities/actions

### 5.3 Confirmation Flows

**Major Actions Require Confirmation:**
- Ship purchase: Summary + "Are you sure?"
- Large trades: Show impact before confirming
- Travel to dangerous systems: Warning message
- Selling ship: "You'll lose installed upgrades"

**Minor Actions Are Instant:**
- Sorting lists
- Viewing details
- Opening screens
- Hovering tooltips

### 5.4 Undo/Cancel

- **Cancel**: Available before confirming transactions
- **Back Button**: Return to previous screen (non-destructive)
- **Undo**: Limited - can cancel during multi-step workflows

## 6. Visual Feedback

### 6.1 State Changes

- **Credits Change**: Flash green (gain) or red (loss)
- **Cargo Change**: Update fill percentage with animation
- **Fuel Consumption**: Visual depletion during travel
- **Reputation Change**: +/- indicator with sound

### 6.2 Animations (Subtle)

- **Screen Transitions**: Fade or slide (200-300ms)
- **Button Hover**: Smooth color transition (100ms)
- **Notification Appear**: Slide in from side (250ms)
- **Travel Effect**: Brief jump animation or screen flash

### 6.3 Sound Design (Optional)

- **UI Sounds**: Click, hover, confirm, error
- **Event Sounds**: Trade complete, credit gain, achievement
- **Ambient**: Subtle background hum, station noise
- **Music**: Low-key ambient tracks (pausable)

## 7. Responsive Design

### 7.1 Resolution Support

**Minimum Resolution**: 1280x720 (720p)
**Recommended Resolution**: 1920x1080 (1080p)
**Support for**: 1440p, 4K (UI scaling)

### 7.2 UI Scaling

- **Scale Factor**: 1.0x, 1.25x, 1.5x, 2.0x
- **Font Scaling**: Maintain readability across scales
- **Layout Flexibility**: Elements reposition/resize gracefully

### 7.3 Windowed vs. Fullscreen

- **Windowed Mode**: Resizable, minimum size enforced
- **Fullscreen Mode**: Native resolution, aspect ratio preserved
- **Borderless Window**: Optional mode

## 8. Onboarding and Tutorials

### 8.1 First-Time User Experience

**New Game Flow:**
1. Brief intro story or context (optional, skippable)
2. Name your ship (or use default)
3. Choose starting location (or default to starter system)
4. Tutorial begins

### 8.2 Tutorial System

**Interactive Tutorial:**
- Highlights UI elements with arrows/boxes
- Step-by-step guidance:
  1. "This is your credits and cargo"
  2. "Click on a station to open the market"
  3. "Buy some goods at a low price"
  4. "Travel to another system"
  5. "Sell for a profit"
- Can skip or disable after first playthrough

**Tutorial Tips:**
- Non-intrusive tooltips
- Appear first time player encounters feature
- "Got it, don't show again" option

### 8.3 Help System

- **Help Button**: Access from pause menu
- **Contextual Help**: Explain current screen
- **Glossary**: Define terms (CR, Jump, Reputation, etc.)
- **Controls List**: Keyboard/mouse reference

## 9. Quality of Life Features

### 9.1 Auto-Save

- Save automatically every 5-10 minutes
- Save on major events (ship purchase, system arrival)
- Save on quit

### 9.2 Multiple Save Slots

- Support 3-5 manual save slots
- Show save metadata (timestamp, credits, location)
- Overwrite protection (confirm before overwriting)

### 9.3 Quick Actions

- "Sell All" button for cargo commodities
- "Fill Tank" for fuel (one-click max purchase)
- "Max" button in trade inputs
- "Optimal Route" suggestion (if autopilot implemented)

### 9.4 Filters and Sorting

- **Market View**: Filter by category, sort by price/profit
- **Ship List**: Sort by price, cargo, efficiency
- **System Map**: Filter by faction, danger, unvisited

### 9.5 Comparison Tools

- **Ship Comparison**: Side-by-side stats when shopping
- **Trade Comparison**: Show potential profit before buying
- **Route Comparison**: Compare fuel cost vs. distance

## 10. Error Handling and User Feedback

### 10.1 Error Messages

**Examples:**
- "Not enough credits to complete this purchase"
- "Not enough cargo space (need 20, have 15 free)"
- "Insufficient fuel to reach this system"
- "This station does not have a shipyard"

**Error Message Design:**
- Clear explanation of what went wrong
- Suggestion for how to fix (if applicable)
- Red text or warning icon
- Cannot proceed until error resolved

### 10.2 Validation

- Prevent invalid inputs (negative numbers, non-numeric)
- Disable unavailable actions (gray out buttons)
- Show requirements for locked features

### 10.3 Loading States

- Loading screen between major transitions (if needed)
- Progress bar or spinner
- "Loading..." message
- Quick loads (<1 second) may not show loader

## 11. Accessibility Features

### 11.1 Font and Color

- **High Contrast Mode**: Option for enhanced readability
- **Font Size Options**: Small, Medium, Large, Extra Large
- **Color Blind Support**: Don't rely on red/green alone
- **Text-to-Speech**: Screen reader support (post-MVP)

### 11.2 Input Alternatives

- **Mouse-Only**: All actions achievable with mouse
- **Keyboard-Only**: Full keyboard navigation
- **Remappable Keys**: Allow custom key bindings

### 11.3 Visual Clarity

- **No Flashing**: Avoid seizure-inducing effects
- **Motion Options**: Reduce/disable animations
- **Clear Focus**: Visible focus indicator for keyboard nav

## 12. Technical Constraints (PyGame)

### 12.1 Rendering

- 2D sprite/surface-based rendering
- Limited to raster graphics (PNG/JPG)
- No native vector graphics (render as bitmaps)

### 12.2 UI Framework

**Options:**
- **pygame-gui**: Pre-built UI components library
- **Custom**: Build UI from scratch using pygame.draw
- **Hybrid**: Mix custom and library components

**Recommendation**: Use pygame-gui for common elements (buttons, text inputs) and custom rendering for specialized displays (galaxy map).

### 12.3 Performance Considerations

- Limit simultaneous animations
- Cache rendered text surfaces
- Optimize redraw regions (dirty rect rendering)
- Target 60 FPS, minimum 30 FPS

## 13. Open Questions

- Should there be a mini-map or only main galaxy view?
- How much information shown via tooltips vs. dedicated screens?
- Real-time UI updates or turn-based snapshots?
- Voice acting or text-only?
- Customizable UI themes or single fixed design?
- Mobile/tablet support in future?

---

**Document Status**: Draft v1.0
**Last Updated**: 2025-10-18
**Dependencies**: All gameplay systems; critical for user experience
