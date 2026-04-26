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

### SL-1 — Points of Interest strip
- Add a POI footer strip region below the main card grid in `station_layouts.py`'s base class. Full-width, sits above the chatter band, narrow vertical extent.
- Render `unique` locations in the strip by default, **except** when a `unique` card is the current mission objective — those render in the main action grid for SL-3 to highlight. The "is this a mission objective?" check is shared with SL-3.
- Strip styling: smaller font, lower contrast, no flavor description visible (just name + small icon). Hover still surfaces the full lore tooltip via the existing `_render_zone_tooltip` path.
- Update each of the five layout subclasses to specify where their strip sits. Frontier scatter is the trickiest — the strip lives in a clean row at the bottom even if the action grid above is scattered.
- Acceptance: every station drops lore-only `unique` cards from the action grid. Mission-objective `unique` cards stay in the grid. Lore is still reachable from the strip. No layout regression at any of the six tested resolutions (per Sprint 3a's subprocess bounds harness).
- Tests: extend `test_subprocess_bounds.py` to cover the strip region. Scenario tests for both branches: a `unique` location with no active mission renders in the strip; the same location with an active mission objective pointing to it renders in the main grid.

### SL-2 — Investment gating
- Add credit-threshold logic: investment cards do not render until lifetime credits crossed (proposed: 25,000 CR).
- Author a small Cargo-Broker-led mission that introduces investment, sets `dialogue_flags["investment_introduced"]`, and unlocks the cards regardless of threshold.
- Both gates are OR'd: card visible if either threshold met or flag set.
- Per memory's flag registry rule: `investment_introduced` goes through `spacegame/constants/flags.py`.
- Acceptance: a fresh save shows zero investment cards across all 11 systems until threshold or flag. After either trigger, all 10 investment cards become available.
- Tests: scenario test in `tests/test_scenarios/` covering before-threshold, after-threshold, before-flag, after-flag, and combined states.

### SL-3 — Salience layer (highlight one card)
- Implement `get_recommended_card(player, system) -> Optional[tuple[location_id, source]]` in a new `spacegame/models/station_salience.py` module. Pure function reading existing state; no model changes. Source enum: `MISSION_OBJECTIVE` | `RECOMMENDATION`.
- Hierarchy as defined in Lever 3.
- Visual treatment: **reuse the cantina quest-receiver glow** (`_render_quest_receiver_glow` pattern from `cantina_view.py`, PT-016). Two-layer pulse: soft halo + crisp inner border, ~1Hz oscillation, alpha 100-240. Factor the pulse into a shared helper (proposed: `spacegame/views/_glow.py`) so cantina and station-hub both call into it.
- Color rule: cyan `(100, 220, 255)` when source is `MISSION_OBJECTIVE` (matches cantina semantic); the card's own `accent_color` when source is `RECOMMENDATION`.
- Acceptance: each player state in the hierarchy table produces the expected highlight on a fresh dock. Highlight does not cause performance regression (frame time unchanged within noise). Cantina's existing quest-receiver glow is identical in feel after the helper extraction.
- Tests: unit tests for `get_recommended_card` covering each hierarchy branch. Visual regression check on the shared glow helper. Integration test for the visual-treatment hook in one layout (others are mechanical reuse). Snapshot test confirming cantina's PT-016 behavior is preserved post-refactor.

### SL-4 — Action grid standardization
- Define the canonical grid: deck-by-deck (upper / service / industrial), as Guild's current arrangement.
- Migrate Union grid to deck-labeled grid (small change; mostly relabeling).
- Replace Frontier scattered with deck-by-deck wearing Frontier styling. Preserve atmosphere (background, particles, dashed connectors as decorative not navigational, taglines).
- Replace Reach hidden-until-hovered's asymmetric column with a deck-by-deck grid where cards are dim-by-default. Preserve the dim-until-hovered treatment.
- Fold Collective radial into the deck grid (per locked decision). Orbital data nodes preserved as ambient particles, central ring becomes a decorative element behind the deck labels, holographic card styling persists.
- Acceptance: a player who has docked at any one station can scan any other station's action grid in under 3 seconds (target for playtest).
- Tests: subprocess bounds harness on every layout × resolution. Visual smoke tests via `_view_harness.py`.

### SL-5 — Faction-first-dock orientation tip
- One-time first-time-tip on a player's first dock at *each* faction's territory. Single sentence, terse: "Guild stations group services by deck." / "Union stations are organized like a blueprint." / etc.
- Uses existing `first_time_tip` infrastructure (PT-M).
- Five tips, fires once per faction, never re-fires.
- Acceptance: first dock at each faction shows the tip; second dock at the same faction does not; first dock at a *different* faction shows that faction's tip.
- Tests: scenario tests for the five faction-first-dock paths.

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
- Crimson Reach has no investment card. The credit-gate logic should handle this gracefully (no card appears regardless of state). Worth confirming during SL-2.
- Do any existing missions assume the player has already noticed a `unique` card on some station? An audit of mission-objective text against `unique`-typed locations is a small task that should run before SL-1.
- Should the POI strip include any non-`unique` content? E.g., pinned faction-information or "system overview" panels? Recommendation: not in SL-1. Keep the strip narrow in purpose. Revisit later.

---

## What this doc is not

- Not a full spec. Each SL sprint will get its own short design note before implementation.
- Not a content authoring pass. The `unique`-location content arc (SL-6) is acknowledged but not designed here.
- Not a commitment to scope. If SL-4's standardization reveals bigger structural concerns (e.g., the radial doesn't fold cleanly into the canonical grid), we pause and re-scope.
- Not a critique of the existing five-layout design. Those layouts shipped good aesthetic identity; the legibility cost was the right tradeoff at the time. Playtester data is now telling us the balance has shifted.

The ambition is the same as `onboarding_design.md`: every dock teaches what it should teach without nagging the player. The world keeps its texture. The training wheels stop appearing because they were never visible to begin with.
