# Station Legibility — Aurelia: A Ledger of Stars

**Status**: scoping draft, 2026-04-26. Not a polished spec — this is the pass *before* the sprints.

**Context**: playtester reports (post-AR-PK) describe the station hub view as "overwhelming" for new players. Six cards on a typical dock, little visible direction. `onboarding_design.md` covered the **first** station under Arna's supervision, where guidance is character-driven. This doc covers everything after that: every subsequent dock at every other station for the rest of the game, where Arna is not present and the layout itself has to do the work.

**Sister doc**: `onboarding_design.md` (2026-04-22) — first-station orientation, Arna roster, soft break. Read it first. Principles inherit.

---

## What this doc inherits

The six principles from `onboarding_design.md` apply unchanged. Briefly:

1. **Prefer character over UI overlays, but player experience wins.**
2. **One NPC owns one cluster.**
3. **Progressive disclosure.**
4. **Transparency where the world can't narrate.**
5. **Soft break into autonomy.**
6. **Voice-check everything.**

What this doc adds: **station legibility is principle 4 in disguise.** When the player docks at a station and Arna isn't there, the world cannot narrate which card matters. The layout itself must surface relevance, or the player drowns. We solve this by reshaping the visual hierarchy and by computing a "next step" suggestion from player state — not by removing options.

---

## The problem

### What's on the cards

Each major station presents 5–7 cards drawn from this set:

| Type | Coverage | Mechanic depth | Early-game usefulness |
|---|---|---|---|
| `market` | 11/11 | Deep (trading loop) | High — core verb |
| `cantina` | 11/11 | Deep (NPCs, missions) | High — but "social" reads as optional |
| `repair_bay` | 11/11 | Shallow (one-button cost) | Conditional (after damage) |
| `shipyard` | 8/11 | Deepest (modules, builder) | Intimidating early |
| `mining` | 2/11 (breakstone, iron_depths) | Mini-game | High where present |
| `salvaging` | 2/11 (forgeworks, crimson_reach) | Mini-game | High where present |
| `refining` | 3/11 (forgeworks, axiom, nova) | Recipe loop | Niche until mid-game |
| `investment` | 10/11 | Passive capital deployment | **Zero** until 5-figure credits |
| `unique` | 11/11 | None — lore popup only | **Zero** mechanically |

### Where this lands for a new player

A typical first-dock at Nexus Prime presents six cards. Two of those (`unique`, `investment`) have no early-game utility. One (`shipyard`) is intimidating. Three (`market`, `repair_bay`, `cantina`) are core. The cards do not visually distinguish those tiers. Three of six cards earn their slot for the player's current state. The other three are noise.

### Why "Guild Halls" feel flat

Playtester language: "Guild Halls don't have any active uses." These are `unique`-typed locations. Every station has one. They take a card slot, look identical to actionable cards, and reward a click with a flavor blurb. Examples: Meridian Financial Exchange (Nexus Prime), The Deep Shafts (Breakstone), Mayors' Council Chamber (Verdant), Wreckers' Guild Hall (Crimson Reach).

The complaint reflects two distinct issues:

1. **Visual parity**: `unique` cards look as important as `market` cards but aren't.
2. **Content thinness**: even on the cards' own terms, a tooltip-sized lore blurb isn't satisfying.

(1) is a layout problem. (2) is a content problem. They can be addressed separately.

### Why investment feels niche

Investment locations exist on 10 of 11 stations and require capital the player will not have for the first several hours. The card's existence is a credit-sink advertisement for a system the player cannot meaningfully engage with. It is also visually identical to action cards, so a new player learns "this card is for nothing right now" the hard way.

### Why faction layout variance compounds the load

Five layout classes:

- **Guild deck-by-deck** (`GuildDeckLayout`): semantic decks (upper / service / industrial). Good information design. Scannable.
- **Union grid** (`UnionBlueprintLayout`): even grid. Scannable.
- **Collective radial** (`CollectiveRadialLayout`): pretty, harder to scan, requires learning.
- **Frontier scattered** (`FrontierScatteredLayout`): organic, deliberately disordered. Worst for scannability.
- **Reach hidden-until-hovered** (`ReachDarkLayout`): intentionally hostile. Cards barely visible until hovered.

The variance is on-character (Reach is lawless, Frontier is improvised) and that's worth preserving. But the variance pushes scannability in five different directions, and the new player who has just learned Guild's deck arrangement at Nexus Prime now has to relearn the layout when they arrive at Breakstone, and again at Axiom Labs, and again at Haven's Rest. This is cognitive cost that the world's narrative thematics do not justify per-station.

---

## Critical assessment: hiding cards is the wrong primary lever

User suggested gating early-game station cards (e.g., open with only `market` and `cantina`). This is one tool. It's not the right primary tool, for four reasons:

1. **Hides world from the player.** A station that says "you'll come back here for X later" is more evocative than two buttons. Discovery is part of the game-feel. Aurelia's working-galaxy register depends on the player feeling that places exist independent of them.
2. **Loses agency.** A player who wants to wander into the shipyard at hour one and look at ships they can't afford is doing something legitimate. The user's stated constraint — "don't restrict from running to Iron Depths" — is the same principle generalized.
3. **Inverts the discovery problem.** Player won't know features exist until they unlock. Many will never realize they're locked, especially for niche systems (refining, investment).
4. **Generalizes badly across factions.** The right "early-game subset" at a Guild station is not the same as at a Union station, where mining is the whole point.

Reframe: **the problem is salience, not visibility.** The eye should be drawn to what's relevant *now* without the rest disappearing. Salience preserves discovery, agency, and faction differentiation while reducing decision load.

This reframe does not exclude targeted hiding. `investment` is genuinely unusable at hour one and can hide without information loss. `unique` is genuinely flat as currently authored and can demote without information loss. Those are local, justified hides — not a blanket policy.

---

## Levers

Five levers, in decreasing order of impact-per-effort.

### Lever 1 — Demote `unique` to a Points of Interest strip

`unique` cards do not transition to a state. They show a flavor tooltip. Putting them at the same visual weight as a market or shipyard misrepresents their importance.

**Move them to a "Points of Interest" strip below the main action grid.** Narrow, secondary visual treatment. Small icon plus name. Hovering still surfaces the lore text. The Aurelia's Rest stays as a `cantina` card (it's mechanically deep). Meridian Financial Exchange moves to the strip.

Effect: every station drops one card from the main grid. New player's eye goes to the action layer first. Worldbuilding is preserved, properly framed.

Cost: layout work in `station_layouts.py`. Each of the five layout classes needs a "POI strip" region. The Frontier scattered layout will need design care — the strip can't sit in the same chaos. The Reach hidden layout already groups things tightly; the strip can be even dimmer.

### Lever 2 — Gate `investment` behind capital threshold and/or quest

Two paths, not mutually exclusive:

**(a) Hard credit gate.** `investment` cards do not render until the player's lifetime-earned-credits crosses a threshold (proposed: 25,000 CR). One state check. Simple. The player encounters investment naturally at the moment they could plausibly use it.

**(b) Quest gate.** A short act-1 mission introduces the concept ("the broker says you've got enough capital to put some of it to work"), sets a `dialogue_flags["investment_introduced"]` flag, and reveals all investment cards. Matches principle 1 (NPCs own clusters) and the doc's existing direction that paying work originates from people.

Recommended: both. The credit threshold is the floor (so the card does not appear ever before usability). The quest is the introduction (so the card's first appearance is character-mediated, not a silent unlock). If the player crosses the credit threshold and the quest hasn't fired, the quest fires; if the quest fires before the threshold, the cards still wait.

Effect: removes one card from 10 of 11 stations until the player is positioned to use it. Cumulative effect with Lever 1: a typical Nexus Prime first-dock drops from 6 cards to 4.

Cost: state read + flag plumbing + a small mission. Mission authoring is the gating work; the credit threshold is an afternoon.

### Lever 3 — Highlight one card based on player state

A pulsing accent, "next" indicator, or both, applied to **at most one card** per dock. The highlight is computed from a `get_recommended_card(player, system) -> Optional[location_id]` function reading existing state. Examples:

| Player state | Highlight |
|---|---|
| Active mission objective is at this station | The card the objective points to |
| Damaged hull (below ~70% threshold) | `repair_bay` |
| Empty cargo + system has `market` + system has buyable goods | `market` |
| Cargo full + market accepts what player is carrying | `market` |
| First time at this faction's territory (`faction_first_visit_<id>` flag unset) | `cantina` (an NPC who can introduce the faction) |
| At a `mining` system + cargo space + appropriate ship | `mining` |
| Investment-introduced flag set + surplus capital + no active investment at this system | `investment` |
| None of the above | None — every card at neutral weight |

Hierarchy: mission objective > damage > cargo state > faction-introduction > resource opportunity > investment > nothing. First match wins.

Effect: teaches by drawing the eye, not by hiding. New player follows the highlight. Experienced player ignores it. Player who *wants* to rush to mining at Iron Depths sees `mining` highlighted and is rewarded for following the obvious path; player who wants to skip it just does.

Cost: pure state-read. No new content, no new flags beyond what mission/cargo/faction already track. Visual treatment lives in `_render_default_zone` in each layout class.

### Lever 4 — Standardize the action grid across factions

Pick the Guild deck-by-deck arrangement (semantic decks: upper / service / industrial) as the canonical layout. Apply it everywhere. Faction visual identity (background tint, accent colors, particles, taglines, icon styling) sits *on top* of the canonical grid, not in place of it.

Specifically retire:

- **Frontier scattered**: replace with deck-by-deck wearing Frontier accents (warm green, organic dust particles, hand-painted feel). The "improvised" frontier feel can come from rougher edges, varied border styles, and the dashed connector lines — not from random placement.
- **Reach hidden-until-hovered**: keep the "barely visible" treatment, but apply it to a deck-by-deck grid instead of the asymmetric column. The lawless feel reads through dimness, not through unpredictable layout.

Keep, with modification:

- **Guild deck-by-deck**: already canonical. Becomes the template.
- **Union grid**: already scannable. Map onto the deck framework with labels — Union's "Industrial Deck" is the most populated, which fits Union character.
- **Collective radial**: locked to fold in. The deck-by-deck grid carries Collective styling (orbital data nodes preserved as ambient particles, central ring becomes a decorative element behind the deck labels, holographic node card styling persists). Atmosphere reads Collective; layout reads canonical.

Effect: a player who learns one station layout has 80%+ of the legibility load handled at every other station. Faction identity is preserved through atmosphere, not through layout chaos.

Cost: largest of the levers. Touches all five layout classes. Risk: aesthetic pushback from the team that wrote the original "five distinct identities" design. Mitigation: keep the visual atmosphere, only normalize the underlying card grid.

### Lever 4.5 — Investment system rewards (related concern, scope-flagged)

The user flagged during decision review: even after gating investment to a usable point in the player's progression, the system itself "feels niche, flat." Layout and gating address *when* the player encounters investment. They don't address *whether the encounter is satisfying.*

Out of scope for the SL-1 through SL-5 sprints, but worth holding the thread:

- Returns are too slow to register as exciting. A faster initial dividend or a visible "this earned X while you were away" notification on next dock would help.
- Investment outcomes don't intersect with other systems. An investment in Breakstone's Mining Rig could yield raw ore directly to the player's cargo hold instead of pure credits — converts a passive system into an alternate income channel that intersects with trading.
- No narrative beats around investments. A successful Verdant Co-op investment could trigger a small NPC interaction next visit ("the harvest paid out — here's your share, try the cider"). Aurelia's "people not menus" principle applies.
- Risk dimension is missing. All current investments yield positive returns. Adding occasional setbacks (a salvage crew gets jumped, a mining rig fails) makes the system feel alive and gives skill-tree investments in social/leadership a place to matter.

**Track separately**: a future `investment_rewards_design.md` doc is the right home for this. Acknowledged here so the connection isn't lost. The legibility work and the rewards work can ship independently.

### Lever 5 — Make `unique` locations meaningful (content arc, not layout)

Lever 1 demotes `unique` cards visually. This lever addresses the content problem behind the visual problem. Some `unique` cards have natural mechanical hooks waiting:

- **Wreckers' Guild Hall** (Crimson Reach) — salvage job board, Malia Torres-mediated contracts.
- **Mayors' Council Chamber** (Verdant) — politics minigame or trade-dispute mediation.
- **Stellaris Auction House** (Stellaris Port) — rare-item bidding, faction-restricted goods.
- **Meridian Financial Exchange** (Nexus Prime) — futures contracts on commodity prices, advanced investment.
- **The Deep Shafts** (Breakstone) — Sora Takahashi history beat, pilgrimage that grants reputation, possibly a tier of mining.
- **Restricted Sector 7 / Restricted Research Wing** (Iron Depths / Nova) — campaign hooks already, content-gated.
- **Alliance Congress Hall** / **Faculty Lounge** / **Okafor Institute** — NPC-density hubs for narrative beats.

This is a content arc, not a layout sprint. It should run in parallel to or after the layout work, scoped per location, and tied to faction reputation systems. Out of scope for the SL-1 through SL-4 sprints. **Acknowledged here so it doesn't fall off.**

---

## What we are explicitly not doing

- **Not hiding `market` or `cantina` ever.** They're the core verbs.
- **Not hiding `mining` / `salvaging` / `refining` at the systems where they're the point.** The Iron Depths rush stays. Forgeworks salvage stays open.
- **Not building a new tutorial overlay system.** The `first_time_tip` infrastructure (PT-M) and Arna already cover first-station orientation. New tips, if needed, plug into what exists.
- **Not removing `unique` locations.** They are worldbuilding worth seeing. We change their visual weight, not their existence.
- **Not adding a "tutorial complete" banner or unlock notification.** Per principle 5, the soft break stays soft. Investment's first appearance is mediated by a quest beat or a quiet threshold cross — not a popup.
- **Not blocking faction-specific layouts entirely.** Atmosphere stays. The grid underneath standardizes.

---

## Roadmap

Six sprints. Sequenced so each builds on the prior without forward-dependency hazards.

### SL-1 — Points of Interest strip — SHIPPED 2026-04-26
- POI footer strip added to `station_layouts.py` base class. Full-width, sits above the HUD/chatter band, ~40px vertical extent.
- `unique` locations demote to the strip by default. **Mission-relevance is evaluated at the system level**, not per-location: per data audit (no mission targets sub-station location IDs as objectives), when a system has any active mission objective (REACH_SYSTEM or TALK_TO_NPC at an NPC whose home is here), ALL `unique` cards at that system stay in the main grid. The Fulcrum case is handled this way: campaign mission to `the_fulcrum` → all unique cards at the Fulcrum, including `fulcrum_core`, stay in the action grid.
- Strip styling: smaller font, lower contrast, no description text in the card body. Hover surfaces the full lore tooltip via the existing `_render_zone_tooltip` path.
- All five layout subclasses share base-class strip rendering. Strip is uniform across factions per design (the whole point: worldbuilding reads consistently as worldbuilding).
- Frontier scatter handled — the random scatter is now bounded to the action-grid area, so the strip below stays clean.
- API: `StationLayout.__init__` accepts `elevated_location_ids: set[str] | None`. Factory `create_station_layout()` accepts the same. View computes the set as either `{all unique IDs at this system}` (when relevant) or `set()` (when not).
- New module: `spacegame/models/station_salience.py` with `is_system_mission_relevant`. SL-3 will extend this module with `get_recommended_card`.
- Tests: 8 unit tests for `is_system_mission_relevant` + 30 layout demotion tests (parametrized over all 5 layout subclasses × 6 behaviors). Total +38 tests, full suite 8,186 passing.
- Acceptance met: every station drops lore-only `unique` cards from the action grid; mission-relevant unique cards stay; lore reachable from the strip via hover.

**Acceptance gap deferred**: extending `test_subprocess_bounds.py` to cover the strip region requires first folding `station_hub_view` into the bounds harness — which isn't currently one of the 16 views it exercises. Tracked as a follow-up; the parametrized layout tests cover the strip's geometry across all five faction layouts at default resolution and the full test suite catches structural regressions. Bounds-harness extension lands when station_hub gets harness coverage in a future UI sprint.

### SL-2 — Investment gating — SHIPPED 2026-04-26 (gating mechanism, mission TBD)
- Credit-threshold logic shipped: `is_investment_unlocked(player, threshold=25_000)` in `spacegame/models/station_salience.py`. Reads `player.credits_earned_lifetime` (existing field) and the `investment_introduced` dialogue flag.
- `INVESTMENT_UNLOCK_CREDIT_THRESHOLD = 25_000` constant locked at 25k CR per the 2026-04-26 decision.
- Flag helper `investment_introduced()` added to `spacegame/constants/flags.py` per the registry rule. Flag-string is the canonical `"investment_introduced"`.
- Both gates OR'd: a player who crosses the credit threshold OR has the flag set sees investment cards.
- View-level filter: `station_hub_view.__init__` filters `investment`-typed locations from the locations list before constructing the layout. Filter at `__init__` time so flavor-text rotation, layout zones, and any other downstream consumer all respect the gate.
- Source data fact (corrected during SL-2): of the 11 systems, **10 have an investment card** (nexus_prime, stellaris_port, breakstone, iron_depths, forgeworks, axiom_labs, nova_research, havens_rest, verdant, crimson_reach). The one without is **the_fulcrum** (campaign-only military location). The earlier doc note saying "Crimson Reach has no investment card" was wrong. Both Crimson Reach and Verdant ship investment locations.
- 19-case scenario test covers fresh-save lock across all 10 investment-bearing systems, threshold-boundary unlock (24,999 vs 25,000), flag-set unlock, the_fulcrum graceful no-op (locked + unlocked), and the falsy-flag-doesn't-unlock edge case.
- Total tests: 8,186 → **8,205 passing** (+19) post-SL-2.

**Mission deferred to SL-2b**: the Cargo-Broker introduction beat. The flag plumbing is in place to receive whatever sets it; no mission currently writes the flag, so unlock occurs only via the threshold gate today. A player crossing the threshold gets a silent unlock — no introduction. Authoring the mission is a content sprint and lands separately. The credit-gate mechanism alone is shippable and meets the immediate cognitive-load goal: a new player at hour one sees no investment cards.

**Scanner gap surfaced during SL-2** (track separately): the SI-3 flag-integrity scanner in `tests/test_data/test_dialogue_integrity.py` introspects parameterized helpers in `spacegame/constants/flags.py` (e.g., `met_npc(npc_id)`) by calling them with sentinel values to discover prefix/suffix patterns. **No-arg helpers like `investment_introduced()` aren't introspectable by this method** — the call fails with TypeError when the scanner passes a sentinel arg. Result: the helper-routed consumer in `is_investment_unlocked` (which calls `dialogue_flags.get(investment_introduced(), False)`) is invisible to the scanner. Today this is fine because no producer exists either. **When SL-2b lands and the mission's `set_flag` action writes the flag, the flag will appear as a producer-only orphan** — the producer is detected (mission JSON) but the consumer isn't (helper not introspectable). At that point either (a) extend the scanner to handle no-arg helpers, or (b) add `investment_introduced` to `KNOWN_PRODUCER_ONLY_ORPHANS` with a comment. Tracked as a small follow-up alongside `writing_bible_scanner_gaps.md`.

### SL-3 — Salience layer (highlight one card) — SHIPPED 2026-04-26
- `get_recommended_card(player, system_id, faction_id, locations, mission_manager, ...)` shipped in `spacegame/models/station_salience.py`. Pure function over the locked hierarchy. Returns `Optional[tuple[location_id, RecommendationSource]]`.
- `RecommendationSource` enum: `MISSION_OBJECTIVE` | `RECOMMENDATION`.
- Hierarchy implemented (first match wins):
  1. **Mission objective** — TALK_TO_NPC objective whose NPC's home system is here → cantina, MISSION_OBJECTIVE source. (REACH_SYSTEM objectives don't suggest a card; player has already arrived and the objective auto-completes on dock.)
  2. **Damaged hull** — strict less-than 70% (default `DAMAGED_HULL_THRESHOLD`) → repair_bay, RECOMMENDATION.
  3. **Empty cargo** — no commodities held + station has market → market, RECOMMENDATION.
  4. **First-faction visit** — no other system in this faction visited + station has cantina → cantina, RECOMMENDATION.
  5. **Resource opportunity** — station has mining or salvaging → mining/salvaging, RECOMMENDATION.
  6. **Investment** — `is_investment_unlocked` AND station has investment → investment, RECOMMENDATION.
  7. None.
- Shared visual helper: new `spacegame/views/_glow.py` exports `render_pulsing_glow(screen, rect, color, elapsed)`. Two-layer pattern (soft halo + crisp inner border), 1 Hz pulse, alpha 100-240. Identical parameters to PT-016.
- `cantina_view._render_quest_receiver_glow` refactored to call the shared helper. PT-016 source-level tests still pass (12/12); behavior is visually identical to pre-extraction.
- `station_hub_view` wires up: `_compute_recommendation()` runs once per dock in `_create_ui`. `_glow_time` ticks in `update`. `_render_recommendation_glow` paints the cyan or accent-color pulse on the matching action zone, between `render_zones` and `render_atmosphere` (so the hover tooltip stays on top).
- Color rule: cyan `(100, 220, 255)` for `MISSION_OBJECTIVE`; the zone's `accent_color` for `RECOMMENDATION`.
- 11 new unit tests for `get_recommended_card` covering each hierarchy branch, the no-match fallthrough, and the hierarchy ordering (mission > damage > cargo). Boundary case for the damage threshold tested.
- Total tests: 8,215 → **8,228 passing** post-SL-3 (+13 net: +11 SL-3 unit + 2 tagging from existing-suite reordering).

### SL-4 — Action grid standardization — SHIPPED 2026-04-26
- Canonical grid extracted to `StationLayout._build_deck_grid` (base class). Upper / service / industrial decks stacked vertically, zones in horizontal rows within each deck. Empty decks consume no vertical space.
- Deck labels rendered via shared `_render_deck_labels(screen, color)` helper. Subclasses opt in from their `render_background` and pass the faction's accent color.
- All five subclass `build_zones` methods now delegate to `_build_deck_grid`. Faction visual identity preserved through:
  - **Guild**: deck labels (always shipped this way; baseline).
  - **Union**: blueprint grid lines under the canonical layout, riveted-panel `_render_default_zone`, amber industrial spark particles, deck labels in faction blue.
  - **Collective**: central ring + station dot retained as decorative atmosphere behind the deck labels (no longer connecting nodes — was navigational, now scenery). Orbital data-node particles still circle the (now decorative) center. Holographic-node card styling intact. Connector lines from center to zones removed (radial-specific).
  - **Frontier**: warm green pollen particles, colorful per-zone borders, hand-painted register, "the frontier takes care of its own" tagline. Dashed zone-to-zone connectors removed (they were the scatter metaphor).
  - **Reach**: dim-by-default `_render_default_zone` override preserved (zones barely visible until hovered). Red ember flicker still drives `render_atmosphere`. Deck labels NOT rendered at Reach (would conflict with the menacing-darkness aesthetic). Layout is canonical; visual treatment keeps the lawless feel.
- Frontier `_view_harness` smoke now exercises the canonical layout, not the random scatter.
- Tests: 15 new parametrized tests in `TestCanonicalDeckGrid` covering all five subclasses across three behaviors (deck ordering, intra-deck row sharing, empty-deck collapse). Total tests: 8,228 → **8,243 passing** (+15).
- Acceptance: a player who has docked at any one station encounters the same upper/service/industrial deck arrangement at every other station, modulo faction-specific atmosphere. Verified via the parametrized tests asserting deck-Y ordering and intra-deck row alignment for all five layouts.

### SL-5 — Faction-first-dock orientation tip — SHIPPED 2026-04-26
- Five tips shipped, one per layout key (guild / union / collective / frontier / reach). Stored in `_FACTION_TIPS: dict[str, tuple[str, str]]` in `station_hub_view.py` — title + 1-2 sentence body each. Voice-checked: declarative, no em-dashes, no flavor. Each one establishes the deck pattern in its own terms (so the player learns the universal abstraction regardless of which faction they encounter first) and names the faction's specific texture.
- Tips fire on `on_enter` after `_create_ui` and the recommendation computation, via the existing `FirstTimeTipOverlay` infrastructure (PT-M). Identical lifecycle to character_view.py's tip.
- Per-faction state: `seen_faction_tip(layout_key)` helper in `spacegame/constants/flags.py` returns the canonical flag string. Pattern: `seen_faction_tip_<layout_key>`. Producer: the overlay's on-dismiss callback. Consumer: the `_maybe_show_faction_tip` gate.
- **Suppression rule** (per locked decision 5): if a mission-objective glow is already active on this dock (`_recommendation[1] is RecommendationSource.MISSION_OBJECTIVE`), the tip is suppressed and the seen flag is NOT set — the tip will fire on the next dock at this faction. Avoids stacking two new pieces of information at the same moment.
- 16 scenario tests in `tests/test_scenarios/test_scenario_faction_first_dock_tip.py` covering: first-dock fires for each of the five factions, correct title and body per faction, already-seen flag suppresses the tip, dismiss callback persists the flag, seeing one faction's tip doesn't silence others, mission-objective suppression, sanity baseline (no mission → tip fires), and the flag-helper string contract.
- Total tests: 8,243 → **8,259 passing** (+16) post-SL-5.
- Acceptance met: first dock at each faction shows the tip exactly once; subsequent docks at the same faction don't re-fire; different factions show their own tips; mission-objective conflict defers cleanly.

### SL-6 — Unique-content arc (parallel / deferred)
- Per-location content authoring as described in Lever 5.
- Not blocked by SL-1 through SL-5. Can run in parallel as a content-team workstream or be picked up after the layout work has stabilized.
- Acknowledged so it doesn't fall off the roadmap.

---

## Sequencing recommendation

1. **SL-1** first. Demoting `unique` clarifies the visual hierarchy that everything else builds on. Lowest risk, highest immediate clarity gain.
2. **SL-2** next. Credit-threshold half is independent of mission authoring and can ship immediately; mission half lands when the dialogue is written. Cumulative card reduction with SL-1 brings new-player Nexus Prime to 4 cards.
3. **SL-3** next. The salience layer benefits from the hierarchy SL-1 established. Pure code change, no content authoring.
4. **SL-4** after SL-1/2/3 have informed the canonical grid (POI strip placement, investment slot behavior, highlight visual). Largest sprint of the arc.
5. **SL-5** after SL-4. The faction-orientation tips assume a known canonical grid that the tip can describe.
6. **SL-6** parallel, low-priority, content workstream.

Hygiene work runnable in parallel:
- The `unique` content audit (which `unique` locations have natural mechanical hooks vs. pure flavor) can begin during SL-1 to inform SL-6 scoping.
- Faction-tagline voice review (Reach's "No laws. No mercy. No refunds." reads slightly Marvel-ish) — small, parallel.

---

## Acceptance criteria for the arc as a whole

A new player on first dock at any non-starting station should:

1. See no more than four cards in the main action grid (with default state, no investment-introduced, no missions).
2. Have at most one card visually highlighted (or none if no recommendation applies).
3. Encounter no card that is mechanically unusable at their current state.
4. Be able to access every `unique` location's lore (just from a different visual region).
5. Recognize the layout pattern within ~3 seconds if they've docked at any prior station.

A returning experienced player should notice nothing has been taken from them. All cards still reachable. Highlights ignorable. No nags, no popups, no banners.

---

## Decisions locked (2026-04-26)

1. **Investment unlock**: **both gates** — credit threshold AND Cargo-Broker mission, OR'd. The cards do not appear before the threshold OR the mission flag, and become available the moment either is met.
2. **Collective radial layout**: **fold into the canonical deck grid** in SL-4. Atmosphere preserved (orbital data nodes, central ring, holographic node card styling) but the underlying grid normalizes. Cognitive load wins over aesthetic distinction.
3. **POI strip styling**: **footer strip** (full-width, bottom of layout area, above the chatter band).
4. **Highlight visual treatment**: **reuse the cantina quest-receiver glow pattern** (PT-016, `_render_quest_receiver_glow` in `cantina_view.py`). Two-layer pulse: soft halo + crisp inner border, ~1Hz oscillation, alpha 100-240. Cross-view consistency: a player who has learned the cantina's "this NPC has your next step" glow will read the same glow on a station card without retraining. **Color rule**:
   - Mission-objective-driven highlight: same cyan as cantina (`(100, 220, 255)`). Same color = same semantic = "the campaign points here."
   - Non-objective recommendation (damage / cargo state / faction-first / resource opportunity): same pulse pattern in the **card's existing `accent_color`**. Visual consistency, semantic differentiation. The card itself feels like it's calling to the player.
5. **Faction-orientation tip timing**: **on dock, after the entrance fade completes** (`_entrance_timer >= 1.0`). Use the existing `first_time_tip` infrastructure (PT-M). **Suppression rule**: tip does not fire if a mission-objective highlight is also being rendered on this dock — defer to next dock at this faction. Avoids stacking two pieces of new information at the same moment.
6. **Investment threshold value**: **25,000 CR**. Tune in playtest if needed.

---

## Refinement triggered by decision review

### Conditional demotion for `unique` cards (SL-1 ↔ SL-3 coupling)

The Fulcrum case forces a refinement to SL-1. `fulcrum_core` (Assembly Core) is `unique`-typed but is **narratively critical** — it's the campaign endpoint. Demoting it to a POI strip alongside lore-only `unique` cards would understate its importance for a player whose current mission objective is to be there.

**Rule**: SL-1's demotion is conditional, not blanket. A `unique` card renders in the main action grid (with the SL-3 mission-objective highlight) when it is the current mission objective. Otherwise it renders in the POI footer strip. The check is the same one SL-3 uses for "is this card a mission objective?" — the two sprints share that data path.

This handles The Fulcrum naturally: by the time the player docks at the Fulcrum at all, they're there because of an active campaign mission; `fulcrum_core` is by definition an objective; it stays in the main grid.

It also handles `iron_depths_restricted_zone` and `nova_restricted_labs` — both `unique`-typed and likely tied to specific campaign beats. When the campaign points there, they're prominent. Otherwise they're worldbuilding.

### Reach tagline exemption

`ReachDarkLayout`'s tagline "No laws. No mercy. No refunds." matches the Writing Bible's banned `no X, no Y, no Z` parallel-negation pattern. **Granted exemption**: the tagline is in-character for Crimson Reach's outlaw register and the parallelism reads as intentional bravado, not GenAI default-mode. Documented here so future content scans don't auto-flag it. No similar exemptions extend elsewhere — the parallel-negation ban applies everywhere except this one tagline.

Allowlist mechanism live in `tests/test_writing_bible_compliance.py` (`_PARALLEL_NEGATION_ALLOWLIST` constant, 2026-04-26).

### Scanner coverage gaps surfaced during pre-tasks

While implementing the Reach allowlist, two coverage gaps in `tests/test_writing_bible_compliance.py` became visible. Tracked separately in `requirements/writing_bible_scanner_gaps.md`:

1. **Station taglines aren't scanned.** Stored as class attributes, rendered via variable reference; current scanner only catches `.render("literal")` patterns.
2. **Parallel-negation regex is `,`-separated only.** Period-parallelism (`No X. No Y.` — the Reach tagline form) slips through.

These gaps don't block SL-1 through SL-5. Tracked here so the connection isn't lost. The allowlist is forward-defensive: when the gaps are closed, the Reach exemption already exists.

---

## Open questions

- ~~The Fulcrum (4 cards, campaign location) plays by different rules.~~ **Resolved**: handled by the SL-1 conditional-demotion rule (a `unique` card stays in the main grid when it's the current mission objective). The Fulcrum's `fulcrum_core` is a campaign objective every time the player docks there, so it stays prominent.
- ~~Crimson Reach has no investment card.~~ **Resolved during SL-2 — that was wrong.** The system without an investment card is `the_fulcrum`. Crimson Reach has `crimson_reach_investment` ("Crimson Reach Salvage Op"). The graceful-no-op test now exercises `the_fulcrum`.
- Do any existing missions assume the player has already noticed a `unique` card on some station? An audit of mission-objective text against `unique`-typed locations is a small task that should run before SL-1.
- Should the POI strip include any non-`unique` content? E.g., pinned faction-information or "system overview" panels? Recommendation: not in SL-1. Keep the strip narrow in purpose. Revisit later.

---

## What this doc is not

- Not a full spec. Each SL sprint will get its own short design note before implementation.
- Not a content authoring pass. The `unique`-location content arc (SL-6) is acknowledged but not designed here.
- Not a commitment to scope. If SL-4's standardization reveals bigger structural concerns (e.g., the radial doesn't fold cleanly into the canonical grid), we pause and re-scope.
- Not a critique of the existing five-layout design. Those layouts shipped good aesthetic identity; the legibility cost was the right tradeoff at the time. Playtester data is now telling us the balance has shifted.

The ambition is the same as `onboarding_design.md`: every dock teaches what it should teach without nagging the player. The world keeps its texture. The training wheels stop appearing because they were never visible to begin with.
