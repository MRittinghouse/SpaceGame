# Station Anchors — Aurelia: A Ledger of Stars

**Status**: scoping draft, 2026-04-26. Not a polished spec — this is the pass *before* the sprints.

**Sister docs**:
- `requirements/station_legibility.md` (2026-04-26) — addressed the LAYOUT problem with `unique` cards (POI demotion, salience glow, canonical grid). Closed SL-1 through SL-5.
- `requirements/onboarding_design.md` (2026-04-22) — six teaching principles. All inherit here.
- `requirements/investment_rewards_design.md` (stub, 2026-04-26) — sister concern. Likely folds into SA-F (Financial Exchange) phase.

**Origin**: SL-6 was acknowledged in `station_legibility.md` as deferred content work behind the `unique`-card demotion. This doc upgrades it from "content arc" to a system-development roadmap. The reframe is deliberate: each `unique` location becomes a **venue** for a broader system, not a one-off content blob. The Wreckers' Guild Hall is the first venue of a Salvage Contracts system. The Mayors' Council and Alliance Congress are two venues of one Politics system. The Stellaris Auction House is the first venue of a Bidding system. Treating them this way forces shared infrastructure, prevents five disposable mini-systems, and gives the game cohesion that one-off content can't.

**Includes**: SL-2b (Cargo-Broker investment introduction mission) folds in as **SA-V**.

---

## What this doc inherits

The six principles from `onboarding_design.md` apply unchanged. The reframe-specific additions:

7. **Systems before venues.** Every anchor location surfaces a system. Design the system first; the location is a place where it manifests, not where it's defined.
8. **Each anchor must integrate with at least three existing systems.** Reputation, missions, skill tree, market, crew, faction perks. No anchor is allowed to be a satellite — if we can't name three integration points before we start, we don't start.
9. **Narrative is the connective tissue, not the destination.** Missions thread anchors together; NPCs reference each other across systems; outcomes ripple. The goal is cohesion, not isolated narrative beats.

---

## Vision — what an anchor location feels like

Pick any anchor at random. A new player arrives, looks at it, and within thirty seconds understands:

- What this place *is* (Wreckers' Guild for salvage contracts; Auction House for rare bidding; Mayors' Council for trade disputes).
- What the system loop is (browse contracts → accept → execute → return).
- How it connects to what they already know (reputation, missions, market, skills).
- Whether they want to engage now or come back later.

A player who has been playing for hours has:
- A relationship with at least one named NPC at each anchor they've visited.
- A history they can reference in dialogue ("the salvage run for Torres last month").
- Mechanical reasons to return regularly (rotating contracts, scheduled auctions, recurring votes).
- Reputation consequences from past anchor activity that show up in unrelated places (a bad call at the Mayors' Council changes which Verdant farmers will trade with you).

If those two paragraphs both work, an anchor is anchor-quality.

---

## The ten anchors plus SA-V

| Anchor | System cluster | Today's state |
|---|---|---|
| Wreckers' Guild Hall (Crimson Reach) | Salvage Contracts | Lore-only `unique` card |
| The Deep Shafts (Breakstone) | Memorial / pilgrimage | Lore-only |
| Alliance Congress Hall (Haven's Rest) | Politics | Lore-only |
| Mayors' Council Chamber (Verdant) | Politics | Lore-only |
| Okafor Institute Medical Wing (Axiom Labs) | Research Patronage | Lore-only |
| Stellaris Auction House (Stellaris Port) | Bidding | Lore-only |
| Meridian Financial Exchange (Nexus Prime) | Financial / Futures | Lore-only |
| Restricted Sector 7 (Iron Depths) | Campaign endpoint | Already has content |
| Restricted Research Wing (Nova Research) | Campaign endpoint | Already has content |
| Assembly Core (the Fulcrum) | Campaign endpoint | Already has content |

Plus **SA-V**: the Cargo-Broker mission that introduces investment (no anchor; runs at any cantina with a Cargo Broker NPC).

---

## Three system clusters

### Cluster A — Already done
Restricted Sector 7, Restricted Research Wing, Assembly Core. Campaign content already in flight. SA work here is a confirmation pass that SL-1's conditional demotion + SL-3's mission-objective elevation surface them correctly during their campaign beats. No new content.

### Cluster B — Single-anchor narrative + light system
- **Wreckers' Guild Hall** — Salvage Contracts (reuses existing salvage system; new contract board).
- **The Deep Shafts** — Memorial, pilgrimage, narrative tie-in to Marcus Jin's arc.
- **Okafor Institute Medical Wing** — Research Patronage (player funds projects; outcomes deliver mechanical unlocks).
- **SA-V** — Cargo-Broker investment introduction mission.

Each is one-to-three weeks of focused work. They reuse existing systems heavily; the new infrastructure is small.

### Cluster C — Multi-venue systems
- **Politics** — Mayors' Council Chamber + Alliance Congress Hall. Two venues, one system. Multi-sprint.
- **Bidding** — Stellaris Auction House (primary venue, possible future expansion). Multi-sprint.
- **Financial / Futures** — Meridian Financial Exchange. Big new layer on top of investment + market. Multi-sprint.

These are the major engineering efforts. Each cluster gets its own sub-roadmap.

---

## Phase plan

Six phases. Phase I is shippable for the next playtest cycle; Phases II-V are subsequent cycles.

### Phase I — Foundation + Quick Wins (2-3 weeks)
The cheapest, highest-narrative-yield work. Every anchor in Phase I either reuses an existing system or is dialogue-and-flag work. Ships first so playtest signal informs Phase II priorities.

- **SA-0** — Campaign-endpoint audit. Confirm Restricted Sector 7, Restricted Research Wing, Assembly Core surface correctly during their existing campaign beats post-SL-1 demotion. QA + minor adjustments only. Hours.
- **SA-1** — Wreckers' Guild Hall (Salvage Contracts). Contract board UI at the anchor, Malia Torres dialogue tree expansion, 3-5 initial contract templates that target existing derelict sites, faction-rep integration, mission-system wiring. ~1 week.
- **SA-2** — The Deep Shafts (Memorial). First-visit pilgrimage scene, Sora Takahashi historical journal entry, Marcus Jin dialogue gate (player's father connection), Union reputation grant on first visit, recurring-flavor NPC presence on later visits. ~1 week. Mostly content + narrative; little new code.
- **SA-V** — Cargo-Broker investment introduction mission. Mission JSON + Cargo-Broker dialogue beat that sets `investment_introduced`. ~3 days. Closes the SL-2 narrative loop.

### Phase II — Politics System (4-5 weeks)
Politics is one system that hosts at two venues. Design + core + content + polish.

- **SA-P1** — Politics System Design. Design doc covering: dispute/issue lifecycle, dispute templates (categories + variations), AI delegate behavior, player input model (vote, argue, mediate, stake reputation), integration points (reputation, market, missions, skill tree). Locks decisions before code. ~4 days.
- **SA-P2** — Politics Core. The mechanic: dispute representation, player choice flow, skill-check integration (Charisma, Leadership, Social), outcome resolution, reputation deltas. UI for the dispute view. Save/load support. Tests. ~1.5 weeks.
- **SA-P3** — Mayors' Council Chamber (Verdant). First venue. Local Verdant disputes — settler vs. farmer trade complaints, modernization-proposal recurring debate, water-rights flares. 5-8 dispute templates. NPC delegates with named voice sheets. ~1 week.
- **SA-P4** — Alliance Congress Hall (Haven's Rest). Second venue. Higher-stakes Alliance-wide issues — Verdant modernization vote at the inter-settlement level, frontier patrol funding, response to Crimson Reach raids. 4-6 issue templates, scheduled (once per game-month). Crosses with Verdant outcomes when the same issue surfaces at both venues. ~1 week.
- **SA-P5** — Politics polish + tuning. Playtest pass on dispute pacing, skill-check balance, narrative texture. Tutorial-overlay hint on first dispute. ~3 days.

**Politics integration commitments** (per principle 8):
- **Reputation**: Dispute outcomes change Verdant + Alliance + (sometimes) Crimson Reach standing.
- **Market**: Outcomes shift commodity prices at affected systems for N game-days.
- **Missions**: Outcomes can unlock or lock specific missions (e.g., a "Modernization Defender" mission unlocks if the player votes pro-modernization at the right Congress).
- **Skill tree**: Charisma + Leadership + Social drive dispute success rates and unlock options ("Mediator" capstone enables a neutral-arbiter path).
- **Crew**: Crew with Social or Leadership specialization grants bonuses during disputes (one crew may attend with the player).

### Phase III — Bidding System (4-5 weeks)
Bidding hosted at one anchor for now (Stellaris Auction House). Designed for multi-venue extension later (black-market auctions in Crimson Reach, Commerce Guild contract auctions, player-initiated sales of rare loot).

- **SA-B1** — Bidding System Design. Design doc covering: lot generation rules, AI bidder behavior model (multiple AI personas with different value functions), bid round structure, time pressure, faction-restricted lots, recurring rival design. ~4 days.
- **SA-B2** — Bidding Core. Bid submission, AI counter-bid logic, time-pressure UI, lot reveal/sale flow, win/loss outcomes. Tests. ~1.5 weeks.
- **SA-B3** — Stellaris Auction House (Primary Venue). Auctioneer NPC, scheduled auctions (every 5-7 game-days), 4-6 lot categories (legendary modules, art, faction-restricted commodities, rare upgrades), 2-3 recurring rival bidders integrated with the existing Captain Memory system so they remember encounters. ~1 week.
- **SA-B4** — Bidding polish + tuning. Playtest pass on lot value calibration, AI bidder difficulty, narrative texture (auctioneer voice). ~3 days.

**Bidding integration commitments**:
- **Modules**: Legendary modules become auction-only items, replacing or supplementing the boss-drop pipeline.
- **Reputation**: Stellaris Port reputation gates lot tiers (low rep = rough lots only; high rep = headliner items).
- **Captain Memory**: Recurring rivals carry over outcomes; winning a hard-fought lot creates a rival that remembers losing.
- **Crew**: Crew with Charisma or Social specialization can be brought to "read" the room (gives info on AI bidders' max prices).
- **Investment**: A futures contract from SA-F can pay out in auction-house credit.

### Phase IV — Research Patronage (2-3 weeks)
Smaller scope than Politics or Bidding. One anchor (Okafor Institute), one system, simpler mechanic.

- **SA-R1** — Okafor Institute Medical Wing. Research-project funding mechanic: 3-5 active projects at any time, each with credit cost + game-day duration + outcome list. Outcomes include: ship-module unlocks (Collective-themed), commodity unlocks (rare medical), reputation grants, dialogue-tree unlocks at Axiom. Tied to Dr. Okafor's "knowledge that does not heal is knowledge wasted" framing. ~2-3 weeks.

**Research Patronage integration commitments**:
- **Investment**: Adjacent system; capital + time deployment with non-credit returns.
- **Modules**: Funded research can unlock new module families (medical-tier, electronics-tier, exotic-materials-tier).
- **Skill tree**: Industry skills shorten research time.
- **Reputation**: Collective standing affects available projects.
- **Faction perks**: Funded research can grant faction-perk equivalent benefits.

### Phase V — Financial Exchange (3-4 weeks)
The most complex single anchor. Multiple sub-systems (futures, shipping contracts, insurance) live here. Folds in `investment_rewards_design.md`.

- **SA-F1** — Financial Exchange Design. Design doc covering: futures contract pricing model (must feel honest against the existing market simulation), shipping contract structure (delivery deadlines + payouts), insurance premium math, integration with `investment_rewards_design.md` open threads. Decisions to lock include: do contracts use real game-day market data, simulated market projections, or both? Skill-tree integration scope. ~5 days.
- **SA-F2** — Financial Exchange Core. Implement the three sub-systems. Tests against price simulation. ~1.5 weeks.
- **SA-F3** — Meridian Financial Exchange Venue. Broker NPCs, contract terminal UI, recurring market-specialist contacts, integration with the Cargo-Broker character (graduation: Cargo Broker for SA-V → Meridian for SA-F). ~1 week.

**Financial Exchange integration commitments**:
- **Market**: Real commodity prices drive futures outcomes.
- **Investment**: Existing investment system is the lower-tier; Meridian is the higher-tier.
- **Game-day cycle**: Contract deadlines tick with the existing turn counter.
- **Skill tree**: Commerce skills (Market Intelligence, Negotiator) grant edges.
- **Reputation**: Nexus Prime standing gates contract sizes.

### Phase VI — Cohesion + Polish (1-2 weeks)
The integration pass. Without this, we have six anchors that work in isolation. With it, the game feels like one place.

- **SA-X1** — Cross-anchor narrative threading. NPCs at one anchor reference events at another ("Heard you took the Vandermeer estate at the Stellaris auction. Smart play."). 10-15 small dialogue insertions across the existing crew + recurring NPCs.
- **SA-X2** — Reputation consistency audit. Confirm anchor activity affects faction standings consistently with the rest of the game; no double-dipping or dead-weight rep paths.
- **SA-X3** — Tutorial integration. First-time-tip overlay on each anchor (PT-M infrastructure, same pattern as SL-5). One sentence each, declarative, no flavor.
- **SA-X4** — Journal pass. Each first interaction with an anchor system grants a journal entry. Standardize the voice and format.

---

## Sequencing recommendation

1. **Phase I first.** Cheapest, ships fast, gives playtest signal on which Cluster C system to prioritize.
2. **Phase II OR III** based on playtest signal. If players gravitate to Verdant disputes in their feedback, Politics first. If they linger at Stellaris and ask about the auction house, Bidding first.
3. **Phase IV** parallelizable with II or III since Research Patronage is small and self-contained.
4. **Phase V** late. Financial Exchange has the most cross-system dependencies and benefits from Phase II/III/IV being stable.
5. **Phase VI last.** Cohesion pass requires the systems to exist before we can thread them.

Total scope: **16-22 weeks** for the full arc. Phase I alone is 2-3 weeks and is the right shippable target for the next playtest cycle.

---

## Decisions to lock (before SA-0 starts)

1. **Naming**: confirm **SA — Station Anchors** as the arc designation. Alternatives: "Living Stations" (LS, riffs on Living Universe Arc), "Anchor Stations" (also SA). Recommendation: **SA**.
2. **Politics reuse for Crimson Reach later?** The Wreckers' Guild Hall does dispute mediation per its lore. After Politics ships at Verdant + Alliance, do we add a Reach venue (gray-market dispute mediation) as a Phase II.5? Or hold for later. **Recommendation**: hold; lever 8 (integration commitment) makes adding a third venue cheap once the system exists.
3. **Bidding venue expansion scope**: are black-market auctions at Crimson Reach in scope for Phase III, or post-arc? **Recommendation**: post-arc. Ship Stellaris well before adding a second venue.
4. **Research Patronage outcome scope**: do we author 5 projects to start, or 10? **Recommendation**: 5 well-tuned outcomes over 10 thin ones. Add more in playtest.
5. **Financial Exchange complexity ceiling**: do we ship all three sub-systems (futures + shipping + insurance) in Phase V, or stage them? **Recommendation**: stage. Ship futures in SA-F2-F3; shipping contracts and insurance become SA-F4 and SA-F5 if/when warranted.
6. **Cargo-Broker → Meridian graduation**: should the same Broker character appear at both venues, with Meridian being a "promotion" of trust? **Recommendation**: yes. One named Cargo Broker who appears at any Cluster B+ cantina, then "graduates" the player to Meridian when they're ready. Strong narrative thread.
7. **SA-V scope**: just the introduction mission, or also a short follow-up at threshold cross? **Recommendation**: just the introduction. The threshold-cross follow-up is the natural lead-in to SA-F (Financial Exchange) and lives there.

---

## Open questions

- Does the politics system's "vote" mechanic conflict with any existing skill-check mechanic? Need to confirm interactions during SA-P1 design.
- Do we have crew with Social/Leadership specialization already, or do we need to extend the crew templates? Quick audit during Phase I.
- Auction-house "recurring rival" bidders — do they integrate with the existing Captain Memory system, or stand alone? Recommendation: integrate; the captain-memory pattern is exactly right for this.
- The Deep Shafts pilgrimage: does it tie into the existing campaign Act One Marcus arc, or is it a side beat? Need to read the campaign reference and decide during SA-2 design.
- Cargo Broker NPC: does this character already exist in the data, or do we need to create them? Per `requirements/onboarding_design.md`, the Cargo Broker was the recommended secondary teacher. Confirm authoring status.

---

## Acceptance criteria for the arc as a whole

A player who has done a full SA arc should:

1. Recognize the names of at least one anchor-specific NPC per faction without being told.
2. Be able to describe the salvage-contract loop, the dispute loop, and the auction loop in one sentence each.
3. Have at least one rivalry, alliance, or grudge that began at an anchor (a Stellaris auction loss, a Verdant dispute they took the wrong side of, a Wreckers' contract that went sideways).
4. See anchor activity reflected in market prices, reputation, and unlocked content elsewhere.
5. Have a journal that reads like a captain's log of decisions, not a list of completed tasks.

A new player at hour one should:
1. See no immediate cognitive overload from the anchors. Per SL-1 they're in the POI strip until earned.
2. Encounter SA-V naturally during the first investment unlock.
3. Have at least one anchor system introduced through narrative (not menus) by hour 3.

---

## What this doc is not

- Not a full design spec for any one system. Politics, Bidding, and Financial Exchange each get their own design docs at the start of their respective phases (SA-P1, SA-B1, SA-F1).
- Not a commitment to scope. If Phase II reveals that Politics is bigger than estimated, we re-scope. The 16-22 week total is honest, not pessimistic — but anything cluster-C-shaped tends to grow.
- Not the unique-content arc as originally framed in `station_legibility.md`. That framing was "ten content blobs." This is "three system clusters with content as the surfacing layer." If the docs ever conflict on SA-6 vs SL-6, this one supersedes.
- Not a playtest substitute. The phases are sequenced so playtest signal informs prioritization. We don't ship all of Phase II before we hear what Phase I felt like.

The ambition is structural: a galaxy where anchors aren't just lore cards, but venues where the player's choices ripple through markets, factions, and stories. The systems do the heavy lifting; the locations are where they meet the player.
