# Station Anchors — Aurelia: A Ledger of Stars

**Status**: scoping draft, 2026-04-26 (full-ambition revision). Not a polished spec — this is the pass *before* the sprints.

**Sister docs**:
- `requirements/station_legibility.md` (2026-04-26) — addressed the LAYOUT problem with `unique` cards (POI demotion, salience glow, canonical grid). Closed SL-1 through SL-5.
- `requirements/onboarding_design.md` (2026-04-22) — six teaching principles. All inherit here.
- `requirements/investment_rewards_design.md` (stub, 2026-04-26) — folds into Phase V (SA-F).

**Origin**: SL-6 was acknowledged in `station_legibility.md` as deferred content work behind the `unique`-card demotion. This doc upgrades it from "content arc" to a system-development roadmap. The reframe is deliberate: each `unique` location becomes a **venue** for a broader system. The Wreckers' Guild Hall is a venue of a Salvage Contracts system that will scale across multiple stations. The Mayors' Council, Alliance Congress, and Wreckers' Guild Hall (gray-market mediation) are three venues of one Politics system. The Stellaris Auction House and Crimson Reach black-market are two venues of one Bidding system. Treating them this way forces shared infrastructure, prevents disposable mini-systems, and gives the game cohesion that one-off content can't.

**Ambition statement**: This roadmap reflects what *good* looks like, not what fits inside a playtest cycle. We do not compress phases to ship faster. We do not strip features to hit a date. Playtest builds may ship in staggers alongside completed phases — that's fine — but the playtest cadence does not constrain phase scoping. This is the vision, full-ambition, with the timeline that honest depth requires.

**Includes**: SL-2b (Cargo-Broker investment introduction mission) folds in as **SA-V** with its full character-arc treatment.

---

## What this doc inherits

The six principles from `onboarding_design.md` apply unchanged. Three additions specific to this arc:

7. **Systems before venues.** Every anchor location surfaces a system. Design the system first; the location is a place where it manifests, not where it's defined.
8. **Each anchor must integrate with at least three existing systems.** Reputation, missions, skill tree, market, crew, faction perks, modules. No anchor is a satellite — if we can't name three integration points before we start, we don't start.
9. **Narrative is the connective tissue, not the destination.** Missions thread anchors together; NPCs reference each other across systems; outcomes ripple. The goal is cohesion, not isolated narrative beats.

---

## Vision — what an anchor location feels like at maturity

Pick any anchor at random. A new player arrives, looks at it, and within thirty seconds understands:
- What this place *is*.
- What the system loop is.
- How it connects to what they already know.
- Whether they want to engage now or come back later.

A player at hour twenty has:
- A relationship with at least one named NPC at each anchor they've visited.
- A history they can reference in dialogue ("the salvage run for Torres last month").
- Mechanical reasons to return regularly (rotating contracts, scheduled auctions, recurring votes).
- Reputation consequences from past anchor activity that show up in unrelated places (a bad call at the Mayors' Council changes which Verdant farmers will trade with you).
- Crew banter that references their anchor history.
- News ticker entries that reflect their decisions.

A player at hour fifty has lived a story made out of decisions taken at these places.

If those three paragraphs all work, an anchor is anchor-quality.

---

## Inventory

The ten `unique` locations plus SA-V's mission target:

| Anchor | System cluster | Today's state |
|---|---|---|
| Wreckers' Guild Hall (Crimson Reach) | Salvage Contracts + Politics venue | Lore-only `unique` card |
| The Deep Shafts (Breakstone) | Memorial / pilgrimage | Lore-only |
| Alliance Congress Hall (Haven's Rest) | Politics | Lore-only |
| Mayors' Council Chamber (Verdant) | Politics | Lore-only |
| Okafor Institute Medical Wing (Axiom Labs) | Research Patronage | Lore-only |
| Stellaris Auction House (Stellaris Port) | Bidding | Lore-only |
| Meridian Financial Exchange (Nexus Prime) | Financial / Futures | Lore-only |
| Restricted Sector 7 (Iron Depths) | Campaign endpoint + DCMC intelligence | Already has campaign content |
| Restricted Research Wing (Nova Research) | Campaign endpoint + NAS intelligence | Already has campaign content |
| Assembly Core (the Fulcrum) | Campaign endpoint | Already has campaign content |

Plus **SA-V**: the Cargo-Broker Investment Introduction (a recurring named character whose arc connects to SA-F at Meridian).

---

## Three system clusters

### Cluster A — Already done, with optional depth tier
Restricted Sector 7, Restricted Research Wing, Assembly Core. Campaign content exists. SA work here is two-layered:
- A confirmation pass that SL-1's conditional demotion + SL-3's mission-objective elevation surface them correctly during their campaign beats.
- An optional depth tier: visiting these between-campaign-beats can unlock intelligence-gathering opportunities, faction-specific narrative beats, espionage potential.

### Cluster B — Single-anchor narrative + light system
- **Wreckers' Guild Hall** — Salvage Contracts (reuses existing salvage system, adds membership tier).
- **The Deep Shafts** — Memorial, pilgrimage, narrative tie-in to Marcus Jin's arc.
- **Okafor Institute Medical Wing** — Research Patronage (player funds projects; outcomes deliver mechanical unlocks + narrative).

Plus **SA-V** (Cargo-Broker introduction mission and ongoing character arc).

Each is two-to-four weeks of focused work. They reuse existing systems heavily; the new infrastructure is small. They each anchor a long-running NPC relationship.

### Cluster C — Multi-venue systems
- **Politics** — Mayors' Council Chamber + Alliance Congress Hall + Wreckers' Guild Hall (gray-market mediation). Three venues, one system. Multi-sprint.
- **Bidding** — Stellaris Auction House (primary) + Crimson Reach Black Market + Player-Initiated Sales. Two venues + one player-side. Multi-sprint.
- **Financial / Futures** — Meridian Financial Exchange. Three sub-systems (futures, shipping contracts, insurance) plus market manipulation threats and a major financial crisis event. Multi-sprint, multi-phase.

These are the major engineering efforts. Each cluster gets its own sub-roadmap.

---

## Phase plan — full ambition

Ten phases. Phase 0 + A + B + C are pre-arc preparation. Phases I through VI are the SA arc proper. Each phase ships when complete; playtest builds run in parallel.

### Phase 0 — Pre-arc Preparation (1-2 weeks)
- **SA-PREP-1** — NPC voice-sheet audit. Catalog every named character touched by this arc (Malia Torres, Marcus Jin, Dr. Okafor's successor, the Cargo Broker, Verdant Mayor, Alliance delegates, Stellaris Auctioneer, Meridian Brokers). Confirm each has a voice sheet per `requirements/character_voices.md` standards. Author missing sheets. Cross-reference for tonal consistency.
- **SA-PREP-2** — Existing-data audit. Walk current dialogue trees, ambient lines, news headlines, journal entries to see what already references each anchor. Identify what we need to expand vs. preserve. Save state baseline for regression checks.
- **SA-PREP-3** — Playtest baseline. Capture pre-arc telemetry: which `unique` cards do players currently click on, time-spent metrics, mission acceptance patterns. Comparison data for post-arc evaluation.

### Phase A — Crew Specialization Extension (1-2 weeks)
Some anchors need crew to feel right (Bidding crew can read other bidders, Politics crew can sway delegates).
- **SA-A1** — Crew specialization design. Identify which crew templates need new specializations (Negotiator, Speculator, Mediator, Patron). Decide whether to add new templates or extend existing ones.
- **SA-A2** — Crew template implementation. Add the new specializations, integrate with existing crew bonus system, write voice sheets for new specialist crew members.

### Phase B — Reputation System Extension (1 week)
Some anchors need fine-grained sub-faction reputation (Wreckers' Guild membership tier separate from Crimson Reach standing; Stellaris Auctioneer relationship separate from Stellaris Port faction rep).
- **SA-B-EXT-1** — Sub-reputation system. Extend the reputation model to support per-organization standing layered under per-faction standing. Tests, save support.

### Phase C — Skill Tree Extensions (1-2 weeks)
- **SA-C1** — Skill design. Identify which new skills the SA arc needs. Candidates: Negotiator (Bidding), Mediator (Politics neutral), Speculator (Financial), Patron (Research), Coalition Builder (Politics advocate). Decision: do we extend an existing tree or add a new one? Probably extend Social and Commerce.
- **SA-C2** — Skill implementation. Add the new skills, wire bonuses through `progression.get_bonus()`, update the skill tree view if needed, tests.

### Phase I — Foundation + Cluster B Anchors (5-7 weeks)
The four single-anchor + light-system pieces. Each gets full character-arc treatment.

- **SA-0** — Cluster A confirmation pass. QA that Restricted Sector 7, Restricted Research Wing, Assembly Core surface correctly post-SL-1. Author the optional depth tier for between-campaign-beat visits (intelligence opportunities at restricted sectors, espionage flavor). 1 week including the depth tier.
- **SA-1** — Wreckers' Guild Hall (Salvage Contracts). Contract board, contract tiers (cleanup, recovery, escort-salvage, deep-derelict), Wreckers' Guild membership system (apprentice / journeyman / master tiers, separate from Crimson Reach faction rep), Malia Torres relationship arc with multiple dialogue gates, 2-3 secondary Wreckers as recurring contacts (different specialties — wreck navigator, salvage engineer, debris-field cartographer), failed contract consequences, guild-member-only contracts unlocked at higher Wreckers' standing, Wreckers' Guild membership badge with mechanical implications. Integrates with salvage location at both Forgeworks and Crimson Reach. 2-3 weeks.
- **SA-2** — Deep Shafts (Memorial / Pilgrimage). First-visit scripted scene with sound design and atmospheric lingering. Sora Takahashi historical journal entries (multi-entry arc rolling out over time + game days). Marcus Jin's father connection — the player learns more here than anywhere else, multiple gated dialogue beats. Older miner caretaker NPC ("Old Sten" or similar — named character, voice-sheet) who tells stories. Faction reputation grant on first visit. Recurring "miner's blessing" — small reputation ticks for periodic returns with crew. Sacred-ground rule (combat/violence forbidden, NPC reactions if violated). Mission tie-ins: Act One beat (Marcus brings player here), Act Two beat (consequences cascade across the Union). Long-running thread: the Uprising's modern echoes in NPC dialogue across the game. 2 weeks.
- **SA-V** — Cargo Broker Character Arc + Investment Introduction Mission. The Broker is a named, voiced character (per onboarding_design.md secondary-teacher slot). They appear at multiple cantinas; the player meets them organically. The mission introduces investment, sets `investment_introduced`. The Broker is the precursor to Meridian — they "graduate" the player to Meridian later in SA-F. Includes the Broker's own voice sheet, personality, history, signature dialogue. 1.5 weeks.

### Phase II — Politics System (8-10 weeks)
Politics is one system that hosts at three venues. Design + core + three venues + polish.

- **SA-P1** — Politics System Design. Design doc + paper prototyping. Covers: dispute/issue lifecycle, dispute templates and variations, AI delegate behavior model (each delegate has positions, biases, persuasion vectors), player input model (vote / argue / mediate / abstain / coalition-build), argument-construction submechanic (present evidence, anticipate counter-arguments, choose framing), integration points (reputation, market, missions, skill tree, crew). Locks decisions before code. ~1 week.
- **SA-P2** — Politics Core. The mechanic at full depth: dispute representation (data model), player choice flow with argument-construction submechanic, multi-skill checks weighted by argument framing, partial-win outcomes, rivalries-formed/alliances-formed as side-effects, UI for the dispute view (this is real UI work — not a modal, a venue), AI delegate behavior with hidden positions and visible reactions, save/load support, tests. ~2 weeks.
- **SA-P3** — Mayors' Council Chamber (Verdant Venue). 8-12 dispute templates (settler vs. farmer trade complaints, modernization-proposal recurring debate, water-rights flares, hydroponics-co-op disputes, frontier-trade tensions). Multiple named delegates with developed voices (Mayor as council chair + 3-5 named delegates). Recurring disputants. Multi-session arcs (one session presents, next session resolves). Outcomes feed market and faction rep. Tutorial integration for first dispute. ~2 weeks.
- **SA-P4** — Alliance Congress Hall (Haven's Rest Venue). 6-10 inter-settlement issue templates. Annual Congress event (scheduled, big stakes, multi-session arcs with campaigning sessions before the vote). Named representatives from each Alliance settlement. Coalition-building gameplay (visit specific delegates ahead of time, build votes with favors and reputation). Major-vote outcomes ripple through Alliance-wide reputation, mission unlocks, economic conditions. Possibility of betrayal/double-cross mechanics on coalition members. ~2 weeks.
- **SA-P5** — Wreckers' Guild Hall (Crimson Reach Venue). Different flavor — gray-market disputes, salvage-rights conflicts, Malia Torres arbitrating. Demonstrates system reusability. Reach-specific issue templates (3-5). Connects with SA-1's Wreckers' Guild membership for delegate access. ~1 week.
- **SA-P6** — Politics polish + tuning. Playtest pass on dispute pacing, skill-check balance, narrative texture, accessibility, tutorial flow. ~1 week.

**Politics integration commitments** (per principle 8):
- **Reputation**: Dispute outcomes change Verdant + Alliance + Crimson Reach standing.
- **Market**: Outcomes shift commodity prices at affected systems for N game-days.
- **Missions**: Outcomes can unlock or lock specific missions.
- **Skill tree**: Charisma, Leadership, Social, plus the new Mediator and Coalition Builder skills.
- **Crew**: Crew with Social or Mediator specialization grants bonuses during disputes.
- **News**: Major outcomes hit the news ticker.

### Phase III — Bidding System (8-10 weeks)
Two venues + one player-side mechanic.

- **SA-B1** — Bidding System Design. Design doc + prototyping. Covers: lot generation rules, AI bidder behavior (multiple AI personas with hidden value functions), bid round structure (open call / sealed / ascending / dutch — pick which we ship), time pressure with adjustable speed, faction-restricted lots, recurring rival design. ~1 week.
- **SA-B2** — Bidding Core. Bid submission, AI counter-bid logic with multiple personas and hidden ceilings, multi-round structure, live time-pressure UI, lot reveal/sale flow with dramatic UI moments, win/loss outcomes. Tests. ~2 weeks.
- **SA-B3** — Stellaris Auction House (Primary Venue). Auctioneer NPC with full voice sheet (named, recurring, characterful). Scheduled auctions every 5-7 game-days, with seasonal "headliner" events. 6-8 lot categories: legendary modules, art, faction-restricted commodities, rare upgrades, antiquities, derelict ship recovery rights, smuggled goods, faction-perk-equivalent unlocks. 3-5 recurring rival bidders with distinct personalities and backstories (Captain Memory integration so they remember encounters). Pre-auction preview period. Post-auction social moments (winner's reception, condolences). ~2 weeks.
- **SA-B4** — Crimson Reach Black Market Auctions. Different flavor venue. Same system, different rules. Faction-restricted goods, reputation/legality consequences, no-questions-asked culture. Connects to Wreckers' Guild membership for access tiers. ~1.5 weeks.
- **SA-B5** — Player-Initiated Auctions. Player can sell rare loot through the bidding system. Reverse-side of the same mechanic. Listing fees, reserve prices, AI buyer pool. Makes the player feel like they're part of the economy rather than just a customer. ~1.5 weeks.
- **SA-B6** — Bidding polish + tuning. Lot value calibration, AI bidder difficulty, narrative texture, accessibility. ~1 week.

**Bidding integration commitments**:
- **Modules**: Legendary modules become primarily auction-acquired, supplementing the boss-drop pipeline.
- **Reputation**: Stellaris Port reputation gates lot tiers; Crimson Reach reputation gates black-market access.
- **Captain Memory**: Recurring rivals carry over outcomes; winning a hard-fought lot creates a rival.
- **Crew**: Negotiator-specialized crew can read AI bidder ceilings.
- **Investment**: Futures contracts from SA-F can pay out as auction-house credit.
- **News**: Major auction outcomes hit the news ticker.

### Phase IV — Research Patronage (3-4 weeks)
Single anchor, smaller surface than Politics or Bidding, but at full ambition this is more than 3-5 projects.

- **SA-R1** — Okafor Institute (Research Patronage). 8-12 active research project templates with rotating availability. Each project has design + outcomes + faction implications + risk profile. Dr. Okafor's successor as a named NPC with developing relationship. 3-5 researcher NPCs as recurring sub-cast. Collaboration system: solo-fund (longer/cheaper) or team-fund with NPCs (shorter/more expensive but shared returns). Risk dimension: some projects can fail (lost capital, bad outcomes). Patent/IP dimension: completed projects produce IP that the player can license, sell, or hold. Major projects unlock unique modules, commodities, tech-tree items. Integration with Industry skills (research time), Commerce skills (IP licensing), Patron skill (better outcomes). ~2 weeks for the system + venue.
- **SA-R2** — Dr. Okafor's Legacy Narrative Arc. Long-running thread about ethics in research. Knowledge that heals vs. knowledge that profits. Multi-step storyline that surfaces over many visits. Dialogue gates tied to which projects the player chooses to fund. ~1 week of authoring.
- **SA-R3** — Polish + tuning. ~3 days.

### Phase V — Financial Exchange (8-10 weeks)
The most complex anchor. Three sub-systems, plus market dynamics, plus a major scripted event arc.

- **SA-F1** — Financial Exchange Design. Real design pass with prototyping. Futures contract pricing model (must feel honest against the existing market simulation), shipping contract structure, insurance premium math, market manipulation surface, integration with `investment_rewards_design.md` open threads. Decisions to lock include: do contracts use real game-day market data, simulated projections, or both? ~1 week.
- **SA-F2** — Futures Core. Implement futures contracts. Real market simulation work. Tests against price simulation. ~2 weeks.
- **SA-F3** — Meridian Venue + Cargo Broker Graduation. Broker NPCs (named, voiced, with relationships back to the Cargo Broker from SA-V — same character, expanded role). Contract terminal UI. Recurring market-specialist contacts. The Cargo Broker introduces the player to Meridian as a graduation moment from basic investment. ~1.5 weeks.
- **SA-F4** — Shipping Contracts Sub-system. Agreed delivery for profit. Deadlines, payouts, faction implications, route-quality bonuses. Integrates with the existing travel and market system. ~1.5 weeks.
- **SA-F5** — Insurance Sub-system. Pay premiums against ship loss; payouts on destruction. Integrates with combat and encounter systems. Tied to ship value, combat record, and faction standing. ~1 week.
- **SA-F6** — Market Manipulation Threats. Other actors can manipulate markets. News events affect futures. The player can sometimes counter or exploit. Adds depth and risk. ~1 week.
- **SA-F7** — Financial Crisis Event Arc. Major scripted event where markets crash, futures contracts come due in chaos, the player navigates. Big narrative moment. Requires the rest of the system in place. Multi-session arc. ~2 weeks.

**Financial Exchange integration commitments**:
- **Market**: Real commodity prices drive futures outcomes.
- **Investment**: Existing investment is the lower tier; Meridian is the higher tier.
- **Game-day cycle**: Contract deadlines tick with the existing turn counter.
- **Skill tree**: Commerce skills + new Speculator skill.
- **Reputation**: Nexus Prime standing gates contract sizes.
- **Combat / Encounters**: Insurance ties to ship loss.
- **News**: Market events drive ticker entries.

### Phase VI — Cohesion + Polish (8-10 weeks)
The integration pass. Without this, six anchor systems work in isolation. With it, the game feels like one place.

- **SA-X1** — Cross-anchor narrative threading. 30-50+ dialogue insertions across crew, recurring NPCs, station chatter, and existing NPCs. The player should hear references to their anchor activity literally everywhere. Includes Marcus Jin reactions to Deep Shafts visits, Malia Torres reactions to Wreckers' Guild milestones, Cargo Broker reactions to Meridian success, etc. ~1.5 weeks.
- **SA-X2** — Reputation consistency audit + rebalance. Confirm anchor activity affects faction standings consistently with the rest of the game. Rebalance so no anchor dominates rep gain or under-rewards engagement. ~1 week.
- **SA-X3** — Tutorial integration. Per-anchor first-time tips (PT-M infrastructure, same pattern as SL-5). One sentence each, declarative, no flavor. Plus introduction missions for systems that don't have them yet. ~1 week.
- **SA-X4** — Journal pass. Each first interaction with an anchor system grants a journal entry. Each anchor has a signature journal voice that fits the location. Standardize voice and format. ~5 days.
- **SA-X5** — News Ticker Integration. Anchor activity produces news headlines. Politics outcomes, auction results, research breakthroughs, futures movements, financial-crisis ripples. The galaxy news ticker should reflect the world the anchors create. 30-40+ new news templates. ~1 week.
- **SA-X6** — Crew Reactions / Anchor Banter. Crew comments on anchor activity. Specialist crew (Social, Commerce, Industry, plus the new SA specializations) get anchor-specific banter. ~1 week.
- **SA-X7** — Achievement Pass. New unique achievements per system: Salvage Master (Wreckers'), Council Mediator (Politics), Auction Champion (Bidding), Patron of Research (Okafor), Wall Street Captain (Meridian), Pilgrim of the Shafts (Deep Shafts), and several hidden / cross-anchor achievements that reward unusual play. ~3 days.
- **SA-X8** — Cross-anchor Mega-Arc. A long-running narrative where multiple anchors connect. A corruption scheme that threads through Stellaris auctions, Meridian futures, and Verdant politics — three venues, one through-line. The kind of thing that makes the world feel alive. Multi-session, branching, with consequences across all three Cluster C systems. ~2-3 weeks of authoring.
- **SA-X9** — Audio + Music Pass. Each venue gets ambient audio identity. Politics gets gavel sounds. Auctions get ambient room noise + auctioneer cadence. Meridian gets trading-floor energy. Optional venue-specific music tracks for major beats. ~1 week (assumes existing audio pipeline; if new audio assets are needed, scope grows).
- **SA-X10** — Visual identity per venue. SL-4 standardized layout. SL-X10 pushes per-venue visual identity within that standardization — distinctive backgrounds, lighting, signature props. ~1 week.

---

## Sequencing recommendation

1. **Phase 0 (prep)** first. Always.
2. **Phases A, B, C** before Phase II/III/V. They're foundational.
3. **Phase I** is the natural first-content phase. Quick wins, high narrative yield.
4. **Phases II OR III** based on which Cluster C system feels most ready. Politics has more venues and more design surface; Bidding has more new-mechanic surface. Either is a valid first.
5. **Phase IV** parallelizable with II or III since Research Patronage is more contained.
6. **Phase V** late. Financial Exchange has the most cross-system dependencies and benefits from prior phases being stable. Folds in `investment_rewards_design.md`.
7. **Phase VI last.** Cohesion pass requires the systems to exist before we can thread them.

Total scope estimate at full ambition: **~38-52 weeks** (~9-12 months). Playtest builds ship in parallel as phases complete.

---

## What we cannot accelerate without compromising

Cataloged so future scope conversations stay honest:

- **NPC voice authoring.** Every named character per `requirements/character_voices.md` standards needs a real voice sheet. Skipping voice sheets produces NPC1 / NPC2 / NPC3 — the opposite of the cohesion goal.
- **Argument-construction submechanic in Politics.** A simple yes/no vote is not the Politics system. Argument construction is the system. Stripping it makes Politics a binary toggle.
- **AI bidder personas in Bidding.** Without distinct AI personas (collectors, speculators, faction agents, rival captains), the auction is just a price-pump-or-fold mechanic. Personas are what make it a system.
- **The Cargo Broker → Meridian graduation arc.** The Broker is the same character at SA-V and SA-F. Splitting them across two unrelated NPCs costs the cross-phase narrative thread.
- **Cross-anchor mega-arc (SA-X8).** Without a story that spans multiple anchors, the systems feel parallel. With it, they feel part of one world.
- **Crew anchor banter (SA-X6).** Without crew reactions, the player navigates anchor systems alone. With them, the crew is part of the story.

These can be reduced in scope but not eliminated without changing what good looks like.

---

## Decisions to lock (before SA-PREP-1 starts)

1. **Naming**: confirm **SA — Station Anchors** as the arc designation. Recommendation: **SA**.
2. **Voice-sheet baseline for NPCs**: do all named SA characters need a 1-page voice sheet, or just primary anchors? **Recommendation**: 1-page minimum for every named character. Cohesion depends on voice consistency.
3. **Skill tree extension scope**: extend Social + Commerce, or also add new tree(s)? **Recommendation**: extend existing trees. Adding a new tree is a structural change beyond SA scope.
4. **Politics venue order**: Mayors' Council first, or Alliance Congress first? **Recommendation**: Mayors' Council first. Smaller stakes for system shake-out; Congress amplifies on top of proven mechanics.
5. **Bidding round-format choice**: open call, sealed, ascending, or dutch? **Recommendation**: ascending (auctioneer-led, most game-feel-friendly). Decision lockable in SA-B1.
6. **Financial Exchange staging**: ship futures-only first (SA-F2-F3) and stage shipping/insurance/manipulation/crisis as future phases? **Recommendation**: ship the full Phase V. Stagger across multiple months but treat it as one phase.
7. **Cargo Broker character authoring scope**: voice sheet + 3 dialogue trees minimum (introduction, ongoing, graduation), or larger? **Recommendation**: 3 dialogue trees minimum, with room to expand based on playtest signal.
8. **Cross-anchor mega-arc scope** (SA-X8): which three anchors thread the central story? **Recommendation**: Stellaris Auction + Meridian Futures + Verdant Politics. The three economic-influence venues, one through-line about market manipulation that connects to legitimate-vs-corrupt power.

---

## Open questions

- Does the politics system's vote/argument mechanic conflict with any existing skill-check mechanic? Confirm during SA-P1.
- Crew templates — do we have crew with Social/Leadership specialization already, or do we need to extend? Phase A audit answers this.
- The Deep Shafts pilgrimage: does it tie into the existing campaign Act One Marcus arc, or is it a side beat? Read campaign reference and decide during SA-2 design.
- Cargo Broker NPC: per `requirements/onboarding_design.md`, the Cargo Broker was the recommended secondary teacher. Confirm authoring status during Phase 0.
- Sub-reputation system (Phase B): does it reuse the existing reputation save/load chain, or need its own? Decide during SA-B-EXT-1.
- Financial-crisis event (SA-F7) — is it scripted (single scripted event) or generated (the system can produce crises under conditions)? Recommendation lockable in SA-F1.

---

## Acceptance criteria for the arc as a whole

A player who has done a full SA arc should:
1. Recognize the names of at least one anchor-specific NPC per faction without being told.
2. Be able to describe the Salvage Contract loop, the Politics loop, the Bidding loop, the Research Patronage loop, and the Financial Exchange loop in one sentence each.
3. Have at least one rivalry, alliance, or grudge that began at an anchor.
4. See anchor activity reflected in market prices, reputation, news ticker, crew banter, and unlocked content elsewhere.
5. Have a journal that reads like a captain's log of decisions, not a list of completed tasks.
6. Have triggered at least one cross-anchor narrative beat (the SA-X8 mega-arc, or one of its branches).

A new player at hour one should:
1. See no immediate cognitive overload from the anchors. Per SL-1 they're in the POI strip until earned.
2. Encounter SA-V naturally during the first investment unlock.
3. Have at least one anchor system introduced through narrative (not menus) by hour 3.
4. Hear references to anchor-system activity from the world (chatter, news) by hour 5, even before they've engaged with anchor systems themselves.

---

## What this doc is not

- Not a full design spec for any one system. Politics, Bidding, and Financial Exchange each get their own design docs at the start of their respective phases (SA-P1, SA-B1, SA-F1).
- Not a commitment to a fixed timeline. The 38-52 week estimate is honest, not pessimistic. Cluster C work tends to grow during design.
- Not the unique-content arc as originally framed in `station_legibility.md`. That framing was "ten content blobs." This is "three system clusters with content as the surfacing layer, plus extensive integration and polish." If the docs ever conflict on SA-6 vs SL-6, this one supersedes.
- Not constrained by playtest cadence. Playtest builds ship in stagger as phases complete; the playtest schedule does not compress phase scoping.

The ambition is structural: a galaxy where anchors aren't just lore cards, but venues where the player's choices ripple through markets, factions, and stories. The systems do the heavy lifting; the locations are where they meet the player; the cohesion phase makes everything one world. We do this right or not at all.
