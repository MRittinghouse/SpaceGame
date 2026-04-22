# Trading Visual Overhaul

> **Status:** DESIGN — Tier 2 doc, visual-overhaul scope per master plan §5. Trading is Aurelia's second-most-frequently-visited screen after the galaxy map. The pair form the player's primary economic-layer experience. Every visual investment here compounds across every session with a profit motive.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `33_overhaul_galaxy_map.md` (route planning + cross-system integration). Coordinates with `requirements/game_systems.md` for economy rules.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Rendering changes
5. Gameplay changes forced by rendering
6. Dependencies
7. Phasing
8. Success criteria
9. Open questions
10. Out of scope

---

## 1. Current state — honest assessment

Factual snapshot per survey of `trading_view.py` (~1,395 lines).

### 1.1 What's already strong

- **Regional specialty indicators** ("BUY HERE" green / "SELL HERE" yellow) on commodities — immediate local-opportunity signal without external reference. Tight, actionable.
- **Cargo P/L column** — real-time profit/loss vs. current system's sell price. Color-coded green/red/neutral. Players can see *right now* whether to sell what they're carrying.
- **Player impact modifier** (± X% inline) when the player's own trades have moved local prices ≥1%. The economy acknowledges the player as a participant, not just an observer.
- **Skill-gated detail unlocks** — `trade_instinct` adds margin % estimates; `smugglers_eye` reveals full "RESTRICTED/ILLEGAL" text vs [R]/[!] tags. Knowledge feels earned.
- **Active event banner** — current pattern is functional and readable. Shows commodity + multiplier + days remaining.
- **Hidden compartment integration** (for smuggling) — separate hidden-hold status line with HIDE / RETRIEVE transfer buttons. Gameplay complexity surfaced well.
- **Keyboard-first design** — B/M/S/X/R/T/A + TAB hotkeys; traders on long sessions flow fast. Preserved.
- **Route bonus % indicator** at top — returning to a visited system shows the bonus inline. Small but meaningful.

### 1.2 What's weak — the five gaps

**Gap 1: No data visualization.**

Zero charts. Zero sparklines. Zero market-depth bars. Trend communicated entirely as "▲ Rising / ▼ Falling / – Stable" + a color. For a trading game where price history is gameplay-significant, the absence of any visual time-series representation is the largest single gap. Players have no in-UI view of *how* a price got here — just where it is.

**Gap 2: No cross-system price comparison.**

The largest *gameplay* gap (per survey). A player in System A has zero visibility into whether the commodity they're considering buying is more valuable in System B — even if they've visited B. The `remote_prices` skill surfaces single-target prices on the galaxy map, but there's no dashboard showing "commodities you know about, by system, sorted by margin." Players currently maintain this information *externally*, in notebooks or memory. An entire metagame layer is locked behind player effort rather than surfaced.

**Gap 3: News ticker exists but isn't in trading view.**

`news_ticker` model exists and is passed to galaxy map. Trading view — the system most immediately affected by galactic news — doesn't display it. "Embargo lifted on fuel" is exactly the headline a trader wants to see while deciding what to load. Currently invisible.

**Gap 4: Commodity rows have no visual hierarchy.**

All 15-25 commodities render as equal table rows. Specialty indicators add color accents but the fundamental structure is unstyled rows. No differentiation by tier (luxury vs commodity vs bulk), by faction affiliation, by legality visual grade. Scanning the table for opportunity is a text-read task, not a pattern-recognition task.

**Gap 5: Faction-gating is invisible until failed transaction.**

Player attempts a buy; gets "You need a bill of landing" error. Until that attempt, there was nothing in the UI indicating the commodity required permit. In a brutalist-data-density aesthetic, permit-required goods should have a visual marker ("PERMIT" stamp, faction-color lock glyph) — preventing the failed-transaction feedback loop.

### 1.3 Secondary gaps

- **Quantity input is a text field.** Typing numbers works but doesn't feel brutalist-fast. Slider + increment buttons + shortcuts would feel more kinetic.
- **Market events are single-banner.** One event visible at a time. Multi-event systems (embargo + shortage + attack) reduce to one-at-a-time readout.
- **No commodity sprite variety.** 16×16 sprites exist but all render at same size; high-value cargo doesn't visually carry more weight.
- **Hidden compartment UI functional but muted.** Purple text isn't enough to communicate "smuggling layer active."

### 1.4 What this doc addresses

- Gap 1 (no visualization) via sparklines + market-depth bars + volatility indicator (§4.1, §4.4)
- Gap 2 (no cross-system) via Market Intel Panel (§4.5)
- Gap 3 (no news) via ticker crawl + integrated headlines (§4.2)
- Gap 4 (no hierarchy) via commodity-tier visual language + faction affinity glyphs (§4.3)
- Gap 5 (invisible gating) via permit/legality visual stamps (§4.6)
- Secondary gaps via quantity input polish (§4.7), multi-event slot (§4.2), hidden-layer chrome (§4.8)

---

## 2. Target feel — influences and reference moments

### 2.1 The three-influence synthesis

Trading is **brutalist-industrial data-dense commercial UI**. Not cyberpunk-neon (that's a scene-overlay option per AB §8.2, not the base voice). Three references:

**Cyberpunk 2077 — brutalist density + chromatic discipline**

- Data-dense menus that assume the player is paying attention. Angular borders, terminal-screen aesthetic, subtle scanlines.
- Information layered — primary readout, secondary context, tertiary detail. Each layer is legible at its own glance.
- Ticker crawls at screen edges. News happens *around* the UI, not hidden in sub-menus.
- Specific iconography. A locked item has a specific lock icon; a threat has a specific threat icon; legibility is signed.

**Terminal / Bloomberg Terminal — the density archetype**

- Dense data grids. Sparklines per row. Multiple timeseries overlaid. Trends at a glance.
- Color coding is strict: green = up, red = down, neutral = gray. Nothing fancy.
- Keyboard-first, mouse-supplementary. Power users move *fast*.
- UI is spartan to the point of aggression — no wasted pixels, no decorative chrome.

**Papers, Please / Return of the Obra Dinn — consequence-weighted screens**

- Transactions have weight. The stamp matters. The choice of what to process matters.
- UI is period-appropriate brutalist (bureaucratic typewriter in Papers, Please; 18th-century logbook in Obra Dinn). Function is form.
- Small details carry large meaning. A single word changes a decision.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Cyberpunk 2077, "V's inventory weapon comparison"** (2020). Selecting a weapon shows current-vs-candidate stat comparison with delta chips. Aurelia equivalent: Market Intel Panel (§4.5) — selecting a commodity shows "Best price at" comparison with margin chips for each visited system.

2. **Bloomberg Terminal, "the commodities workspace"** (ongoing). Grid of commodity rows with current price + sparkline + multi-period delta + volatility bar + volume indicator. Density without clutter. Aurelia equivalent: commodity rows (§4.1) gain a sparkline column + volatility pip + supply/demand depth bar.

3. **Cyberpunk 2077, "ticker crawl on ripperdoc vendor screen"** (2020). News crawls at the bottom of vendor screens — Night City news unrelated to your immediate transaction. The world is talking while you shop. Aurelia equivalent: news ticker at top of trading view (§4.2), permanent, scrolling, Expanse-wide.

4. **Papers, Please, "approval stamp"** (2013). The act of stamping a document is the central input. Tactile, final, consequential. Aurelia equivalent: confirm-transaction polish (§4.9) — BUY / SELL buttons get a tactile confirmation animation (stamp-down feel) with palette-specific color flash.

5. **Return of the Obra Dinn, "the memory book"** (2018). A dedicated screen for reviewing what you've learned. Aurelia equivalent: Market Intel Panel (§4.5) functions as the trader's memory book — your aggregated knowledge of the Expanse's markets, visualized.

### 2.3 What this is not

- **Not neon cyberpunk.** Cyberpunk 2077 *informs* the density aesthetic; we don't copy its color palette. Trading stays on Aurelia's balanced palette (AB §2) with brutalist-industrial chrome.
- **Not a spreadsheet.** Density ≠ incomprehensibility. Every element earns its pixel.
- **Not a trading simulator.** No order books, no bid-ask spreads, no algorithmic trading. Aurelia's economy is at the weight of a competent-trader-reads-the-market game, not an Eve Online commodities exchange.
- **Not Starfield's "every transaction opens a new menu."** Transactions happen in-place. The trading view is the workspace; sub-menus are for exceptions.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Visual signal |
|---|---|---|
| Open trading view | Workspace focus | UI chrome resolves from fade; ticker starts scrolling; current system's market data populates |
| Scan commodity table | Pattern recognition | Specialty indicators, tier colors, sparklines allow opportunity-scanning in <5 seconds |
| Hover a commodity | Contextual insight | Sparkline expands to show longer history; volatility + supply detail populate info zone |
| Open Market Intel Panel | Strategic overview | Panel opens with cross-system comparison; player sees their whole knowledge at once |
| Identify a route | Mercantile satisfaction | Margin chip highlights best destination; route previews cost/risk |
| Commit to a trade | Tactile confirmation | Stamp-down animation on BUY/SELL; credit count ticks with weight |
| Stock gets depleted (player impact) | Economic presence | Price shifts visibly; impact modifier updates; supply bar shrinks |
| Active event affects a commodity | Strategic attention | Event banner highlights commodity; commodity row gets event-stripe accent |
| News headline crosses ticker | Ambient awareness | Headlines scroll without demanding attention; relevant ones can be expanded |
| Attempt restricted trade without permit | Clear refusal | Visual permit stamp on commodity becomes prominent; error message is specific, not generic |
| Smuggle cargo into hidden compartment | Illicit competence | Hidden-layer chrome activates (smuggling-context color shift); transfer animation carries weight |
| Leave trading view | Deliberate exit | Chrome fades; ticker pauses; return to station hub |

### 3.2 What each emotion serves gameplay

- **Workspace focus** → trading is a *place to work*, not a screen to click through
- **Pattern recognition** → experienced traders read the table fast; density rewards skill
- **Contextual insight** → hover = deeper read; no modal required for common info
- **Strategic overview** → Market Intel Panel is the trader's planning surface
- **Mercantile satisfaction** → finding good margins feels earned
- **Tactile confirmation** → transactions carry weight; the stamp animation says "committed"
- **Economic presence** → the market is alive and responds to the player
- **Strategic attention** → events draw the eye to affected commodities without hiding them
- **Ambient awareness** → the galaxy talks; news crawls at the edge of focus
- **Clear refusal** → failed transactions are informative, not frustrating
- **Illicit competence** → smuggling feels like a specialist move, not an error state

### 3.3 The non-goal: trading-as-puzzle

Trading should reward attention, not demand it. A casual trader should be able to buy-sell through the UI in under a minute; a specialist trader should be able to optimize complex routes across visited systems in under five. Density serves speed for experts; clarity serves approachability for casuals. Both are legitimate play styles.

---

## 4. Rendering changes

### 4.1 Commodity row redesign with sparklines + depth bars

Replace current 5-column table with richer rows. Each commodity row becomes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [sprite] COMMODITY NAME        [tier-glyph] [faction-glyph] [legality-stamp]│
│          Current: 124 CR (+4%) ▲    Vol: ████░ · Supply: ██████████░       │
│          Sparkline: ────────╱╲──╱╲──╲─── (7-day price history)             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Components:
- **Sprite (existing, larger)** — tier-scaled: bulk commodities smaller (14px), luxury larger (20px) — per-commodity size data
- **Tier glyph** — small icon indicating commodity tier (bulk / standard / premium / luxury / restricted / illegal)
- **Faction glyph** — small faction insignia if commodity has faction affinity (Collective scientific goods, Reach contraband, etc.)
- **Legality stamp** — PERMIT or RESTRICTED or ILLEGAL (see §4.6)
- **Current price + delta + trend symbol** — existing format, cleaner typography
- **Volatility pip bar** — 5-segment bar showing price volatility over recent days (calm = 1 segment, wild = 5 segments)
- **Supply depth bar** — 10-segment bar showing stock depth relative to base (visual form of current numeric stock)
- **Sparkline** — 30-40px wide micro-chart showing 7-day price history, rendered in commodity-appropriate palette color

Row height grows from current ~24px to ~52px. Fewer rows visible per screen (12-15 instead of 20-25). Information density per row nearly doubles.

**Cost:** ~2 weeks. New row-rendering component, sparkline drawing, volatility/supply bar primitives.

### 4.2 Ticker crawl + multi-event slot

A **news ticker** runs at the top of the trading view, scrolling Expanse-wide headlines from the existing `news_ticker` model:

- Single-line scrolling text, right-to-left, ~40 px/s
- Headlines styled per category (market events in `hud_warning`, political in `hud_cyan`, ambient in `hud_text_dim`)
- Click a headline → expands into an inline card with the full text + "dismiss" action
- Ticker pauses on hover (gives the player time to read)

**Multi-event slot:** below the ticker, a zone that shows up to 3 concurrent events affecting local market. Replaces the current single-banner approach:

```
┌──────────────────────────────────────────────┐
│ EMBARGO: Fuel +15%  · 3d     [expand]        │
│ SHORTAGE: Medicine +22% · 2d [expand]        │
│ ATTACK: Rare Metals unavailable · 5d         │
└──────────────────────────────────────────────┘
```

Affected commodities in the main table get an **event-stripe accent** on their row (left edge) matching the event's category color, making it visually obvious which commodities are currently affected.

**Cost:** ~1.5 weeks. Ticker rendering, event-zone UI, commodity-event cross-reference rendering.

### 4.3 Commodity tier + faction glyphs

Commodity tier and faction affinity surface as small glyphs in each row (integrated into §4.1):

**Tier glyphs** (all v1 commodities mapped):
- **Bulk** — single chevron (basic goods)
- **Standard** — double chevron
- **Premium** — solid diamond
- **Luxury** — filled star
- **Restricted** — padlock (amber)
- **Illegal** — skull (red)

**Faction glyphs** (displayed when commodity has strong faction affinity):
- **Collective** — small scientific cross (cyan)
- **Reach** — crossed-bolts (crimson)
- **Union** — ceramic-style hexagon (warm gold)
- **Alliance** — frontier-star (muted orange)
- **Guild** — commerce-tri (chrome)

Glyphs are ~10×10px, positioned after the commodity name. Two glyphs max per commodity (tier + faction). Unglyphed commodities are generic / faction-neutral.

**Cost:** ~1 week. Glyph rendering + data-mapping for all commodities.

### 4.4 Volatility indicator + market-depth visualization

Per §4.1, each commodity row gains:

- **Volatility pip bar** — 5-segment horizontal bar (8px tall, 40px wide). Segment count reflects rolling-window price volatility:
  - 1 segment: price has moved ≤3% over last 7 days (calm)
  - 2 segments: 3-8% range (steady)
  - 3 segments: 8-15% (active)
  - 4 segments: 15-25% (volatile)
  - 5 segments: >25% (wild — often indicates event-affected commodity)
- **Supply depth bar** — 10-segment horizontal bar showing `current_stock / base_stock` ratio. Color-coded:
  - Above 100% (oversupplied): cool cyan
  - 50-100% (normal): neutral
  - 20-50% (tight): amber
  - Below 20% (critical): red

Skill `trade_instinct` level 2 unlocks **hover-details** — hovering a commodity shows a larger expanded sparkline (last 30 days) + volume history + event history for that commodity.

**Cost:** ~1 week. Pip + depth bar rendering; hover-expansion UI.

### 4.5 Market Intel Panel — the headline feature

Gap 2 from §1.2. The largest gameplay gap gets the signature new UI: a **Market Intel Panel** accessible via `I` key or toolbar button.

Panel opens as an inline overlay (doesn't leave trading view). Contains:

**Grid layout:**
- Rows: commodities the player has encountered (ever bought or sold)
- Columns: visited systems, ordered by current-system proximity
- Cells: current price at that system, or "–" if unknown, or "[stale]" if data is >30 in-game days old
- Cell colors: green if sell-here margin >15%, red if buy-here margin >15%, neutral otherwise
- Row sort: by best available margin (highest profit route at top)
- Column sort: by system alphabetical or proximity (toggle)

**Quick-actions per row:**
- "Best Buy" and "Best Sell" chips with margin %
- "Route to seller" → calls galaxy map §4.9 multi-hop route planner
- "Show price history" → expands the row into a multi-system sparkline comparison

**Skill gating:** base panel requires `trade_instinct` level 1 (currently needed for profit margin). `remote_prices` level 1 unlocks cells for un-visited systems' common commodities. `remote_prices` level 2 adds luxury/restricted. Panel is always unlocked if skills are present.

**Data freshness:**
- Cell data ages 1 in-game day per day since last visit
- Stale data (>30 days) shows with "stale" indicator; player can still route based on it but knows the data is old
- Event-affected cells show a small event badge
- Refresh by visiting the system

**Cost:** ~3 weeks. Significant new UI + data aggregation across visited-market history.

**Benefit:** unlocks the hidden metagame layer. Players stop maintaining spreadsheets.

### 4.6 Permit / legality visual stamps

Gap 5. Commodities requiring permits get visual treatment before the player attempts the transaction:

- **PERMIT commodities** — amber "PERMIT" stamp glyph in the row; hover shows which permit is required + whether the player has it
- **RESTRICTED commodities** — red "RESTRICTED" stamp; hover shows what legal risk the trade carries
- **ILLEGAL commodities** — heavy red "ILLEGAL" stamp; hover shows faction penalty + smuggling mechanics hint
- **Player-has-permit state** — stamp changes to "APPROVED" (green) when player has the required permit

Stamps are visible inline in the row, integrated with §4.1 layout. The "skill reveals legality" mechanic (existing) applies — players without `smugglers_eye` see ambiguous [R] / [!] tags; players with the skill see full stamps.

**Cost:** ~4 days. Stamp rendering + permit-state integration.

### 4.7 Quantity input polish

Replace text field with **hybrid input**:
- Numeric field (existing; preserved for precision)
- Increment buttons (−1 / −10 / +10 / +1)
- Slider bar (drag to select 0 to max-affordable)
- Keyboard: `Q` / `W` for ±1, `A` / `S` for ±10, `SHIFT+A` / `SHIFT+S` for ±100

Max-buy / max-sell keys (`M` / `X`) unchanged.

**Cost:** ~3 days. UI widget refinement.

### 4.8 Smuggling layer visual chrome

When the player's ship has a hidden compartment installed, trading view gains a **smuggling-context visual layer**:

- Hidden-hold status line uses stronger purple-violet palette (not just text color — a subtle background tint on the status zone)
- HIDE / RETRIEVE buttons gain a distinct styling (chrome border with violet accents)
- When the player has cargo in the hidden hold, a persistent "HIDDEN: X units" indicator at the top-right of the trading view (discreet but always visible to the player)
- Transferring to/from hidden storage triggers a brief `hud_muted`-tinted animation

Hidden-layer visuals never appear for players without the upgrade — clean UX for non-smugglers.

**Cost:** ~1 week. UI styling + transfer animation.

### 4.9 Transaction confirmation polish

BUY / SELL actions get a **tactile confirmation beat**:

- On click: button briefly depresses (2px shift) with a "stamp-down" feel
- A small particle burst of credits (BUY: minus-colored outgoing; SELL: plus-colored incoming) flows to the credit counter
- Credit counter ticks the delta with a digit-rollover animation (~0.3s) rather than an instant number swap
- Cargo / market tables update with a brief row-highlight on the affected commodity

**Cost:** ~1 week. Button styling + particle + counter animation.

### 4.10 Commodity sprite variety integration

Currently all 16×16 sprites render at one size. Upgrade:

- Tier-scaled rendering per §4.1 (bulk 14px, standard 16px, premium 18px, luxury 20px, restricted 18px with stamp overlay, illegal 16px with stamp overlay)
- Sprites render through the palette-snap discipline (AB §2) for consistency with ship rendering
- Legendary / story-flagged commodities get an optional faint gold-shimmer animation

**Cost:** ~4 days. Sprite rendering variation.

---

## 5. Gameplay changes forced by rendering

### 5.1 Market Intel Panel adds a new UI surface

§4.5 introduces a panel that consumes visited-system market history. This isn't a gameplay change — the data is already tracked in `market.py` price history. The panel *surfaces* existing data. Zero balance impact.

### 5.2 Permit stamp pre-filters visible clutter

§4.6 shows PERMIT / RESTRICTED / ILLEGAL commodities visibly even when the player can't buy them. This is an **information change** — the player now sees what they can't buy. Slightly more clutter, dramatically more clarity. Option: add a "Hide unavailable" toggle for players who find the clutter distracting.

### 5.3 No other gameplay changes

Pricing mechanics, stock rules, event effects, faction permit requirements, smuggling mechanics — unchanged.

---

## 6. Dependencies

### 6.1 On other overhaul docs

- **`20_aesthetic_bible.md` §2** — palette roles for ticker colors, glyph colors, stamp colors
- **`20_aesthetic_bible.md` §4.8** — faction color overlay values for faction glyphs
- **`33_overhaul_galaxy_map.md` §4.9** — multi-hop route planner (Market Intel Panel calls into this for "Route to seller")
- **`10_programmatic_generation_framework.md` §3** — primitives for sparklines, pip bars, depth bars

### 6.2 On production systems

- `spacegame/views/trading_view.py` — heavily extended
- `spacegame/models/market.py` — price history already tracked (cost-free consumption)
- `spacegame/models/player.py` — visited-systems market knowledge already tracked
- `data/economy/commodities.json` — tier + faction-affinity metadata additions
- `spacegame/models/news_ticker.py` — ticker rendering integration

### 6.3 On Tier 3 parallel docs

- **`42_ui_chrome_components.md` (Tier 3, not written)** — row/card patterns + stamp styling coordinate here when it lands

---

## 7. Phasing

Trading overhaul is moderate scope. 5 phases, parallelizable with other Tier 2 visual work.

### Phase T1 — Commodity row redesign + sparklines + depth bars (~2-3 weeks)

- Richer commodity row rendering (§4.1)
- Tier / faction glyphs (§4.3)
- Volatility + supply depth bars (§4.4)
- Sprite variety integration (§4.10)

**Why first:** the commodity table is the view's core; upgrading it touches the most screen real estate per unit effort.

### Phase T2 — Ticker crawl + multi-event slot (~1.5 weeks)

- News ticker integration (§4.2)
- Multi-event display zone
- Event-affected commodity row accents

**Parallelizable** with T1.

### Phase T3 — Market Intel Panel (~3 weeks)

- Cross-system price grid (§4.5)
- Margin chips, sorting, route-to-seller integration
- Data-freshness / stale-data indicators
- Price-history expanded view

**Why later:** depends on T1 (row design for consistency) and galaxy map §4.9 (route planner for "Route to seller" action).

### Phase T4 — Permit stamps + quantity polish + transaction feedback (~1.5 weeks)

- Permit / RESTRICTED / ILLEGAL stamp system (§4.6)
- Quantity input hybrid widget (§4.7)
- Transaction confirmation polish (§4.9)

### Phase T5 — Smuggling layer chrome (~1 week)

- Hidden compartment visual upgrade (§4.8)
- Smuggling-context color shifts
- Persistent hidden-cargo indicator

### Total estimate: ~9-11 weeks

---

## 8. Success criteria

Trading overhaul is done when:

1. **Sparklines make price history legible at a glance.** Player can identify trending-up commodities without reading numbers.
2. **Market Intel Panel obsoletes external notebooks.** Players stop tracking prices in Google Docs / Discord channels — the panel is enough.
3. **Ticker integration brings the galaxy in.** News affects trading decisions even when not actively queried.
4. **Permit stamps prevent failed transactions.** Players see "can't buy" before clicking.
5. **Row redesign rewards pattern recognition.** Scanning 15 commodities for opportunity takes <5 seconds for an experienced player.
6. **Density doesn't sacrifice clarity.** Casual players still navigate the basic buy/sell flow in under a minute.
7. **Smuggling layer feels specialist.** Players with hidden compartments feel they're operating in a different mode; players without don't see the clutter.
8. **Palette compliance holds.** All new visualizations (sparklines, pip bars, stamps) use palette roles per AB §2.
9. **Performance.** Trading view holds 60 FPS with 20+ commodity rows visible, ticker scrolling, event banners, and Market Intel Panel open.

---

## 9. Open questions

1. **Sparkline window — 7 days right?** Shorter (3-5 days) shows more recent behavior; longer (14-30 days) shows patterns. v1 proposal: 7 days primary, 30-day available on hover. Calibrate during T1 playtesting.
2. **Market Intel Panel for unvisited systems.** Skill-gated per §4.5. Is the skill threshold (`remote_prices` level 1) too permissive or too restrictive? Playtest.
3. **Tier glyph count.** 6 tiers v1 (bulk / standard / premium / luxury / restricted / illegal). Could expand to include ultra-rare tiers (legendary, artifact). Defer.
4. **Sparkline data freshness.** Stale sparklines (systems visited >30 days ago) — should they visually indicate staleness? v1 proposal: yes, grey-out the sparkline to ~50% opacity.
5. **Multi-event slot overflow.** What if 4+ events affect local market? v1 proposal: show 3, with "+N more" text; click expands full list. Rare edge case.
6. **Ticker dismissibility.** Can players dismiss ticker entirely for focus mode? v1 proposal: yes, via settings toggle.

---

## 10. Out of scope

- **Commodity production mechanics** — economy / balance territory
- **Multi-player market effects** — single-player only
- **Stock / bond investment system** — there's a separate Investment mini-game per Phase 4; this doc is commodity trading only
- **Automated trading (trade routes as automation)** — scope for future fleet management
- **Per-commodity story content** — narrative layer, not trading view
- **New commodity content** — design territory, not rendering

---

*Next Tier 2 doc: `35_overhaul_station_hub.md` (Cyberpunk districts + Starfield stations — painted panorama, neon-on-darkness, faction-specific chrome). Station Hub is the connective tissue that makes trading, mining, salvage, refining, shipyard all feel like they live somewhere.*
