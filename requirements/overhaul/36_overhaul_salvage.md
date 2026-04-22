# Salvage System Redesign

> **Status:** DESIGN — Tier 2 doc with **full mini-game identity treatment** (see `project_overhaul_minigame_identity.md` in memory for the pattern established with `32_overhaul_mining.md`).
>
> Salvage is Aurelia's second full-identity mini-game. Where the Prospector is union-coded solidarity labor, the Salvager is something else entirely — Frontier-coded, morally-grey, haunted. The two identities are deliberate opposites in voice and cultural anchor, both valid ways to inhabit the Expanse.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `30_overhaul_space_combat.md` (camera/pipeline), `32_overhaul_mining.md` (mini-game identity template). Coordinates with `requirements/dialogue_writing_guide.md` for narrative voice.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Loop design and balance discipline
5. Narrative identity — The Salvager
6. The Wrecker's Log — main mini-campaign
7. Optional content tracks
8. Rendering changes — visual overhaul
9. Gameplay changes forced by rendering and narrative
10. Dependencies
11. Phasing
12. Success criteria
13. Open questions
14. Out of scope

---

## 1. Current state — honest assessment

Factual snapshot per survey of `salvage_view.py`, `models/salvage.py`, `engine/salvage_vfx.py`, `data/economy/salvage_configs.json`, `data/salvage/derelict_stories.json`.

### 1.1 What's already strong

- **Corruption pressure system** is the signature emotional hook. Timer countdown + red edge vignette creep + structural integrity bar + pulsing audio pulse create genuine tension. 50% yield loss on corrupted cells makes the pressure mechanical, not cosmetic. **This is the best feel-element in Aurelia's mini-game stack** and is preserved intact.
- **Dual-mode interface (Scan / Extract)** creates real strategic depth. Scan reveals; extract collects; mode-switching is Tab-fast. Decision tension between "scan more to find valuable cells" vs "extract what's revealed before corruption."
- **Charge economy** (10 max, 5s regen, +50% on deck advance) forces selective scanning. Not everything can be scanned. Players must choose.
- **Parallel extraction** (2 active slots default, expandable) adds throughput mastery axis.
- **Deck descent** with escalating corruption timer (~85% per deck) is a roguelike-adjacent progression within a session.
- **Three derelict types** — Cargo Bay, Lab Module, Engine Room — with distinct atmospheres and story fragment pools. Real environmental variety.
- **21 story fragments already exist** in `data/salvage/derelict_stories.json` (7 per derelict type). **These are the bones of the narrative identity.** The overhaul turns them from ambient flavor into load-bearing content.
- **Quality-graded yields** (poor → excellent) with ingredient drops (Charged Filament, Signal Fragment, Schematic Data) at quality/deck thresholds — real progression hooks.
- **5 system-specific salvage configs** with distinct grid sizes, densities, item distributions.
- **Salvage Hold decouples from ship cargo** (100 units base, +50 per Salvage Buffer level to 350) — smart design that enables long focused sessions.

### 1.2 What's weak — the central gap

**Orphaned narrative.** The derelict story fragments exist but have no connecting thread. No salvager character. No wreck-broker NPC. No named wrecks you return to. No quest arc. No reason you are salvaging beyond "credits are here." Stories tell you *about* the wreck, never *about* you, never *about* the trade.

**Compared to mining's "narrative void,"** salvage's problem is structurally better: the material exists. What's missing is connective tissue — the spine that says *these fragments are pages from the same book.*

### 1.3 Secondary gaps

**Gap 1: No named wrecks.** Every wreck is generic (Cargo Bay / Lab / Engine Room, randomly selected). There's no "the Meridian-class freighter off Breakstone that I've been working for three weeks" — no persistent wrecks with identity. Inscryption's trick (you return to the same table; it's different each time but it's *the same table*) isn't available.

**Gap 2: No module recovery.** Salvaging a broken ship cannot produce ship modules. You recover scrap metal, electronics, rare parts — commodities. But the *obvious* identity marker for a Salvager — pulling a working thruster out of a wreck and fitting it to your ship — doesn't exist. This is salvage's most natural signature capability and it's absent.

**Gap 3: No wreck-broker / fence NPCs.** Trading has merchants, mining will have Augustyn and Marta at the Union Hall, combat has faction captains. Salvage has a grid. There's nobody to sell to who *is* someone. Buyers are anonymous market rates.

**Gap 4: Crew comments are ship-crew, not salvager-specific.** Elena / Marcus / Priya / Tomas emit contextual one-liners during extraction — good feature, but they're the player's ship crew. There's no salvager-identity-voice — no Disco-Elysium-style skill voices representing the Salvager's inner instincts.

**Gap 5: Story fragments fade in 2 seconds.** Currently a story fragment pops briefly and vanishes. There's no persistent log. No way to re-read. The player is presented evidence and not given time to absorb it. Raw discoveries should become *entries* — readable, collectible, arrangeable.

**Gap 6: Derelict types are not bound to systems.** A randomly-selected derelict type at session start (Cargo Bay / Lab / Engine Room) means system identity is thin — the wreck could be any type regardless of where you are. Should be: Breakstone leans industrial cargo wrecks; Lab Modules appear disproportionately in Collective space; Crimson Reach has combat wrecks. System-type binding would reinforce worldbuilding.

**Gap 7: Legendary / unique recoveries absent.** Ingredient drops exist but there's no "I recovered the captain's log, signed by the captain of this specific named ship" tier. No artifacts. No lore objects with persistence.

### 1.4 What this doc addresses

- The central orphaned-narrative gap — **The Salvager** identity + "The Wrecker's Log" campaign + named wrecks + wreck-brokers
- Module recovery as Salvager's signature capability (§9.1)
- Story fragments promoted from ambient flavor to collectible Wrecker's Log entries (§8.5)
- System-wreck-type binding (§9.2)
- Legendary/unique recoveries via The Collector's Wall (§7.3)
- Skill voices (Forensic Eye, Wreck Logic, Ghost Channel, Trained Hand, Buyer's Memory) representing Salvager's inner instincts (§5.2)

The corruption pressure system, charge economy, dual-mode interface, deck descent — preserved intact.

---

## 2. Target feel — influences and reference moments

### 2.1 The four-influence synthesis

Salvage is **gothic forensic archaeology with mercantile edge + roguelike session arc + haunted voice**. Four references, each carrying specific cargo:

**Inscryption — discovery through slow reveal**

- You don't know what things *are* when you first encounter them. Understanding accumulates through play.
- Objects have *histories*. A card you pick up has been through other hands, other games. Past players left marks.
- The table / wreck is itself a character. You come back; it remembers. Or seems to.
- Voice is sparse, ominous, specific. Act 1's Leshy speaks the way a salvager's inner ear should — rare, load-bearing lines.

**Balatro — combinatorial mastery and risk management**

- Individual items aren't the point. *Combinations* are. A lone scrap-metal yield is noise; a full officer's quarters' worth of items is a story.
- Risk-reward pressure per session (ante scaling) maps to corruption-timer escalation per deck.
- Post-session summary feels weighty — "what I built this run."
- Visual language: understated cards, numbers that escalate, a table that feels real.

**Citizen Sleeper / Disco Elysium — prose discovery + skill voices**

- Prose is load-bearing. A well-written paragraph of found text carries more weight than three more mechanics.
- Skill voices: inner characters speaking when relevant. Terse, pointed, interjecting.
- Character identity built through accumulated choices + internalized experiences.

**Dishonored / BioShock environmental storytelling — the room tells you what happened**

- Every scene is a crime scene. The arrangement of objects *is* the story. You piece together narratives from physical evidence.
- Nobody narrates. You read the scene.
- The wreck isn't just a container — it's a record.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Inscryption, "you realize the cards remember"** (2021). A card you thought was disposable turns out to be from another run. The game has been watching. Aurelia equivalent: returning to a named wreck (e.g., the Signal Ship), finding that a cell you left unopened last session has shifted contents. The wreck isn't static.

2. **Balatro, "the end-of-round summary" (2024).** Chips, multipliers, your specific deck's choices tallied. You built this run; here's what it did. Aurelia equivalent: post-session Wrecker's Log entry — what you recovered, which story fragments, which named items, a single flavor line selected from the session's events.

3. **Citizen Sleeper, "reading found text in a run-down room"** (2022). A single found document, 3-4 paragraphs, reshapes your understanding of where you are. Aurelia equivalent: Wrecker's Log entries are longer than current 2s fade. They persist. Players re-read. They accumulate as evidence.

4. **Disco Elysium, "Shivers describes the city's pulse"** (2019). A skill voice speaks for 2-3 lines, revealing something the player couldn't have known. Aurelia equivalent: during deep salvage, **Ghost Channel** skill voice whispers "*someone's still broadcasting on 2.4 — the signal's old but the oscillator is warm*" — mechanically foreshadows a hidden cell with higher quality.

5. **Dishonored, "the Golden Cat brothel upstairs rooms"** (2012). No dialogue. You walk through, and the evidence tells you everything about who worked there, who died, what they wanted. Aurelia equivalent: a Lab Module wreck where scan-revealed item positions + story fragments + cell contents combine to imply a specific tragedy without ever narrating it.

### 2.3 What this is not

- **Not horror.** Aurelia's salvage is unsettling, not frightening. Haunted, not possessed. Weight, not shock.
- **Not a deckbuilder.** Balatro's combinatorics inspire the "combinations matter" pressure, but salvage is not a card game. Items don't synergize into builds; they assemble into stories.
- **Not a mystery game with puzzles.** There is no puzzle solution to "what happened on this wreck." The fragments accumulate; the player synthesizes. No one reveals the answer.
- **Not Prospector-with-wrecks.** The voice, cadence, and emotion are different. Cross-contamination of mining identity into salvage would flatten both.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Signal doing the work |
|---|---|---|
| Enter salvage from trading view | Uneasy commitment | Cockpit window view of wreck at distance; approach sequence; airlock-equivalent transition into grid |
| First scan of a new wreck | Forensic attention | Scan pulse (existing) + subtle "accessing" text in bottom-left (similar to Signal Intercept overlay) |
| Reveal a rare cell | Adrenaline | Tier-3 VFX (quality burst exists; weight); skill voice may interject; Wrecker's Log entry flagged |
| Story fragment appears | Pause the game (in spirit) | Persistent notification (not 2s fade); player clicks to read full entry; logged permanently |
| Corruption timer reaches red | Rising dread | Existing system works; preserved; strengthened visual cue slightly |
| Successfully extract under pressure | Tense satisfaction | Quality burst (existing) + brief camera focus on cell; skill voice acknowledges |
| Deck advancement | Descent | Existing deck transition — good; strengthened via layer-specific ambient tint |
| Recover a named artifact | Historical weight | Tier-4 VFX; permanent Collector's Wall entry; skill voice comments; artifact can be examined in Wrecker's Log |
| Recover a ship module (new capability) | Hands-on discovery | Brief cinematic: module highlighted at its cell, extraction animation focuses, "module recovered" state — goes to module inventory |
| Return to a named wreck | Recognition | On entry: "Re-entering [Wreck Name]" — skill voice notes what changed since last visit |
| Meet a wreck-broker NPC | Mercantile wariness | Broker dialogue interface — terser than Union Hall warmth; transactional with character |
| Complete a Wrecker's Log chapter | Archaeologist satisfaction | Longer scene — assembled fragments presented as a coherent narrative; chapter closes with reflection |
| Sell a sensitive find | Moral weight | Some findings can be sold or kept; selling to different brokers yields different outcomes (rep, currency, story consequence) |
| Prestige-equivalent (see §4.4) | Departure | Extended wreck departure cinematic — pull out, recede, star-field, the wreck remains behind forever |

### 3.2 What each emotion serves gameplay

- **Uneasy commitment** (entry) → salvage is weighted; players don't enter casually
- **Forensic attention** (first scan) → the Salvager reads scenes; mechanics reward slow attention
- **Adrenaline / tense satisfaction** → the clicker rhythm is preserved but flavored darker than mining
- **Pause the game** (story fragments) → narrative *interrupts* mechanics, not the reverse; this is the key difference from mining
- **Rising dread** (corruption) → preserve the signature feel
- **Descent** (deck advance) → already good; lean into it
- **Historical weight** (artifacts) → the Salvager carries what they find; not everything is for sale
- **Hands-on discovery** (modules) → the Salvager's signature capability, worth a cinematic beat
- **Recognition** (named wrecks) → persistent world state; the wreck remembers
- **Mercantile wariness** (brokers) → moral grey zone explicitly present
- **Archaeologist satisfaction** (chapter complete) → assembled knowledge feels earned
- **Moral weight** (sensitive sales) → choices have consequences in this mini-game, not just in main campaign
- **Departure** (prestige equivalent) → the loop has weight at its boundaries

### 3.3 The non-goal: moral lecture

Salvage is morally grey. That greyness is inherent to the trade — wrecks contain things people lost; you profit from loss. The game does not judge the player for this. It acknowledges the weight and lets the player sit with it. NPCs have opinions; the game itself does not preach.

---

## 4. Loop design and balance discipline

Inherits the **three-tier currency discipline** from `32_overhaul_mining.md §4.1`. Parallel structure, different specifics.

### 4.1 Three-tier currency structure

| Tier | Currency | Source | Sink | Converts to |
|---|---|---|---|---|
| **Main-game** | Credits (CR) | Selling commodities to broker, selling wreck salvage, Collector's Wall market sales | Ships, modules, services | — (terminal) |
| **Salvage internal** | Reputation Fragments | Quality extractions, ingredient drops, successful corruption survival, deck-clear bonuses | Salvage upgrades (Quick Extract, Signal Amplifier, Salvage Buffer, plus new tiers), broker-specific rep | Improves conversion rates and unlocks new broker relationships |
| **Salvage campaign** | Wrecker Standing + Collector's Wall entries | Wrecker's Log entries, named wreck completions, artifact recoveries | Chapter progression, master-tier capabilities, unique broker access | Unlocks master-tier capabilities within salvage; **never direct CR** |

**Critical discipline preserved:** Reputation Fragments and Wrecker Standing never convert to CR. The only salvage → CR pathway is commodity sales at broker rates, gated by broker rep (+5% to +20% per broker tier).

### 4.2 Income comparison (target)

| Activity | Typical session | CR yield | Notes |
|---|---|---|---|
| Single trade route | 3-8 min | 2,000-5,000 | Direct, low-skill, low-risk |
| Standard combat | 5-15 min | 1,500-4,500 | Includes salvage, module drops |
| Mining (master tier) | 20-30 min | 4,000-7,000 | Per `32_overhaul_mining.md` |
| Salvage session (basic) | 8-15 min | 1,500-3,500 | Commodity sales at default broker rate |
| Salvage (Wrecker's Log chapter 3+) | 15-25 min | 3,000-6,000 | Broker rep + quality extractions + named wrecks |
| Salvage (master tier) | 20-35 min | 5,000-9,000 | Includes module recovery (§9.1), legendary artifacts, top broker rates |

**At master tier, salvage slightly exceeds mining master-tier yield** — this is deliberate. Salvage is **riskier** (corruption can zero you out; mining never zeros you out). Risk-adjusted, mining and salvage are near-equivalent endpoints. The Expanse rewards both paths.

### 4.3 Campaign gating rules

Wrecker's Log chapter completion unlocks capability:

- **Chapter 1 complete** → Wrecker's Log UI + first broker (Mattsen Holt) available.
- **Chapter 2 complete** → Signal Tracker capability (reveals adjacent scan zones — passive signal-triangulation ability). Second broker unlocks.
- **Chapter 3 complete** → Master-tier salvage upgrades (levels beyond current caps on Quick Extract, Signal Amplifier, Salvage Buffer). Named Wrecks track opens (§7.1).
- **Chapter 4 complete** → **Module Recovery capability (the Salvager's signature)** unlocks (§9.1). Can now pull ship modules directly from specific cells. Third broker unlocks.
- **Chapter 5 complete** → Prestige-equivalent unlocks: **Wrecker Cycles** (§4.4). Fourth/fifth brokers unlock.
- **Chapter 6 (optional lore)** complete → Thought cabinet entry for "What the Long Dark Remembers." No capability gating — pure lore.

Ignoring the campaign caps the player at current-state salvage content (no module recovery, basic broker access only). Engaging earns the full identity.

### 4.4 Wrecker Cycles (prestige-equivalent)

Mining has prestige (reset depth, gain multiplier). Salvage's equivalent is **Wrecker Cycles**: a Salvager can commit to "moving on" — leaving their current broker network and starting fresh in a new region of the Expanse.

- Cycle cost: Wrecker Standing threshold (grows per cycle)
- Cycle effect: Broker rep resets; Reputation Fragments retain 25%; **Wrecker Standing compounds** (+5% permanent bonus to discovery rates per cycle)
- Cycle ceremony: 3-4s cinematic — your ship departs the current region, stars streak past, arrival at a new broker's dock
- Max cycles: 5 in v1 (expandable via optional content)

Cycles are earned through Chapter 5 completion + accumulated Wrecker Standing, not purchasable. Unlike mining's prestige (purely numerical), cycles carry narrative — each cycle, your Salvager has moved on. The cumulative identity is "someone who's seen several regions." Named wrecks in prior regions persist in the Wrecker's Log even after cycling.

### 4.5 Optional content reward rules

Inherits mining's discipline: cosmetics + small bonuses + collectibles, never mastery capability.

Salvage-specific optional rewards:
- **Collector's Wall entries** — the signature salvage cosmetic track
- **Named broker relationships** — alternate buyers with distinct personalities and niche markets
- **Artifact collection** — rare items with lore and small passive bonuses (e.g., "Captain's Pocketwatch" — +5% crew loyalty during salvage sessions; passive, permanent)
- **Salvage-skin cosmetics** for ship modules (a "salvaged" aesthetic variant of purchasable modules — same stats, visible history)
- **Titles** (on ship: "Wrecker," "Archaeologist," "The Quiet Buyer" based on playstyle)

### 4.6 Anti-cheese discipline

- **No AFK salvage** — corruption timer guarantees engagement. Preserved.
- **Module recovery rate-gated** — §9.1 enforces 1 module per named-wreck-session maximum + module level-cap tied to current ship tier. Can't recover end-game modules from early wrecks.
- **Artifact sell-or-keep choice is meaningful** — some artifacts yield large CR on sale but lock the player out of their Wrecker's Log entry completion. Players must choose.
- **Broker betrayal economics** — selling a find to one broker damages rep with a rival broker if the find was "supposed" to go to them. Cannot game all brokers simultaneously.

---

## 5. Narrative identity — The Salvager

### 5.1 Who is the Salvager?

You, when you inhabit salvage. Deliberately opposite register from the Prospector.

**Core voice (reference `requirements/dialogue_writing_guide.md`):**

- Aurelia's wrecking trade lives Frontier-coded — outlaw-adjacent but not criminal. Closer to an offshore oil-platform divemaster who also happens to do private recovery work than to a space pirate.
- Cultural resonance: Newfoundland shipwreck hunter + post-war battlefield archaeologist + deep-sea commercial salvor.
- Speech patterns: terse, dry, specific. A Salvager explains little and notices much.
- The Salvager is *haunted in a working way*. Not tortured. Carries weight without dramatizing it.

**Core beliefs:**

- The dead don't care. The living owe them what they owe.
- Everything in a wreck was someone's. You take it because it's owed.
- A good broker pays honest. A bad one never pays enough.
- The Expanse has a lot of pasts. You're in the business of them.
- Some things are worth more than credits. Most things aren't.

**What the Salvager is not:**

- Not a pirate (no predation on living ships)
- Not a crime-scene detective (salvage-for-profit is the frame, not justice)
- Not a collector in the obsessive sense (the Collector's Wall is a record, not a shrine)
- Not a mourner. The Salvager acknowledges; doesn't grieve.

### 5.2 Skill voices (Disco Elysium-inspired, 5 voices)

Five inner-voice skills that interject during salvage, each with distinct personality. Lines are sparse — average 1-3 per session, triggered by specific mechanical events. Style identical to mining's (§5.2 of mining doc): italicized corner-region text with palette-colored stroke. Deliberately different voices than mining.

| Skill | Voice color | Personality | Triggers |
|---|---|---|---|
| **Forensic Eye** | `cryo_fractal` (cool cyan) | Observational, precise, attends to detail | First scan of a wreck; cell adjacencies reveal a pattern; anomalous evidence |
| **Wreck Logic** | `plasma_core` (warm orange) | Structural, practical, experienced | Corruption timer pressure; deck collapse risk; extraction-order optimization |
| **Ghost Channel** | `hud_muted` (muted grey-blue) | Haunted, patient, rare | Signal-bearing cells; broadcasting wreckage; deep-corruption moments |
| **Trained Hand** | `frontier_canvas` (warm earth) | Practiced, deadpan, workmanlike | Extraction tool decisions; module-recovery prep; fatigue/session-end |
| **Buyer's Memory** | `hud_cyan` (sharp teal) | Mercantile, knowing, wry | Artifact discovery; broker-specific finds; value calculations during triage |

**Example lines (one per skill):**

- *Forensic Eye:* "Three cells stacked like that wasn't loading order. Someone was hiding something."
- *Wreck Logic:* "Hull's not going to hold the extraction pulse. Pull the shallow cells first."
- *Ghost Channel:* "Someone's still broadcasting on 2.4. The signal's old but the oscillator is warm."
- *Trained Hand:* "Cut the bolts, don't torque them. The seal's the only thing holding it."
- *Buyer's Memory:* "Mattsen won't touch that. Erika will, but she'll lowball."

Each skill has ~20-30 lines total across its content library. Rare "memorable" lines (~5%) are flagged for the Wrecker's Log.

### 5.3 Thought cabinet (6 thoughts v1)

Parallel structure to mining's thought cabinet. Salvager-specific identity internalizations:

1. **I Don't Ask Where** — Internalize: sell 30 artifacts without keeping any. Grants: +8% broker rate; trait: "I don't ask where it came from. They don't ask where it went."
2. **The Dead Don't Pay Rent** — Internalize: complete 15 sessions with full-clear. Grants: +5% extraction speed; trait: "They're done with it. Someone has to be."
3. **Some Things Aren't For Sale** — Internalize: keep 10 artifacts (refuse broker offers). Grants: +3 Wrecker Standing per named wreck; trait: "The Collector's Wall is a record. Not everything's inventory."
4. **I Know a Buyer** — Internalize: establish rep-tier-3 with 3 brokers. Grants: +10% CR on commodity sales; trait: "There's always a buyer. You just have to know who."
5. **The Long Dark Remembers** — Internalize: complete Chapter 6. Grants: skill voices trigger +20% rate; trait: "Some wrecks listen back."
6. **The Trade Is Old** — Internalize: complete 5 Wrecker Cycles. Grants: +5% discovery rate permanently; trait: "Every region has its wrecks. I'm not the first to work them, and I won't be the last."

Thoughts are permanent once internalized. Visible in Wrecker's Log.

---

## 6. The Wrecker's Log — main mini-campaign

Structurally different from Prospector's Road. Where the Prospector arc was linear (chapter 1 → 2 → 3 → 4 → 5), the Wrecker's Log is **episodic with a meta-spine**. Each chapter is a named wreck whose story unfolds across 3-6 sessions. Chapters can overlap — a player might work on Chapter 3's Signal Ship while also advancing Chapter 1 finding Mattsen the broker.

### 6.1 Pacing and structure

- **Each chapter:** a specific named wreck (or cluster), 3-6 sessions of engagement. Narrative beats trigger via *specific cell discoveries*, not generic milestones. Reading story fragments in the right order accumulates understanding.
- **Total campaign:** ~20-30 sessions for M1-M5 core chapters, ~5-8 hours real-time dedicated salvage. Shorter than Prospector's Road because sessions are denser per unit time (corruption pressure + real discovery pacing).
- **Delivery:** story fragments on-site, broker dialogue at broker docks, Wrecker's Log journal entries (persistent, re-readable), chapter-closing reflections.
- **Voice:** terse, haunted, workmanlike per §5.1.

### 6.2 The six chapters

**Chapter 1 — "First Wake"**

A recent wreck near your starting system. First paid contract: a small cargo hauler lost during a storm. Meet **Mattsen Holt**, a wreck-broker who operates out of a docking bay rented off a larger station. Mattsen is honest about the trade — he's a fence who doesn't pretend otherwise. Introduces Wrecker's Log UI + basic broker interaction.

*Narrative content:* ~5 story fragments specific to this wreck (original content, not from existing 21-fragment pool). Final scene: Mattsen pays you, looks at what you brought, says one specific thing that establishes his voice.

*Reward:* Wrecker's Log unlocked. Mattsen established as default broker. Broker rep system activated.

**Chapter 2 — "The Signal Ship"**

A derelict freighter that broadcasts a distress signal on 2.4 MHz. The signal has been broadcasting for 40 years. Players visit the wreck across 4-5 sessions, each session unlocking different decks and fragments. Over time, the story becomes clear: the signal is automated; the crew is long dead; but the signal was never supposed to be a distress call — it was a coordinate beacon for a rendezvous that never happened.

The Signal Ship becomes a **persistent named wreck** that stays available permanently after chapter completion. Players can return to it whenever they want — it has additional content (optional fragments, legendary artifact) that unlocks with broker progression.

*Reward:* Signal Tracker capability — future wrecks reveal adjacent-cell signals (passive discovery aid). Named Wrecks optional track unlocks. Second broker introduced: **Erika Sennen**, an older broker with specialization in historical finds; tenser relationship with Mattsen.

**Chapter 3 — "What Was Taken"**

You find a cargo bay wreck containing evidence of what the existing story fragment pool already hints at: a child's personal effects, paired with a blacklisted invoice, paired with a sealed compartment that was never supposed to be found. The wreck is not mysterious — it's specifically a trafficking incident that was covered up.

Another party is looking for what you took. A third broker appears: **"The Third Shift"** — anonymous, encrypted, buys everything without questions at rates below Mattsen or Erika. Works out of a different region. Meeting The Third Shift is your choice.

This is the **moral-weight chapter.** Narrative choices branch: sell sensitive evidence to Third Shift (fast CR, no rep), deliver to an authority via Erika (slow rep gain, Union-adjacent), keep it (Collector's Wall, Wrecker Standing, no CR).

*Reward:* Master-tier salvage upgrades. Named Wrecks track expanded. Player's choice recorded (affects Chapter 5's reception).

**Chapter 4 — "The Butcher's Bill"**

A large combat wreck. Specifically: a Crimson Reach raider + a Collective patrol craft locked in final embrace, mutual destruction. Both crews are aboard. Salvaging this wreck confronts the player with what "clean up" after battle means.

Across 4-5 sessions, the player recovers modules, personal effects, logs from both sides. The Crimson Reach raiders were smuggling medical supplies to an under-served Frontier colony. The Collective patrol was enforcing a blockade that was later ruled illegal. Neither side was simply villainous. Neither entirely innocent.

This is the chapter where **module recovery unlocks**. Pulling a working thruster from the wreckage of another person's ship is specifically the trade's signature move. The mechanical capability lands at the narrative moment that asks whether it's right to do.

*Reward:* **Module Recovery capability** (§9.1). Master-tier upgrades fully unlocked. Fourth broker introduced: **Cesarine "Ces" Marrot** — specializes in military-grade finds; Navy-adjacent, will only buy to certain specs.

**Chapter 5 — "The Long Wake"**

Your reputation is set. Multiple brokers know your work. You've accumulated enough Wrecker Standing to make a choice: commit to a Wrecker Cycle — leave your current region and start fresh with new brokers in a new part of the Expanse.

This is the identity consolidation chapter. The choice is how you close out this region: settle accounts with brokers, complete any named wrecks you've left unfinished, pick which broker gets the final sale. The chapter is ~3-4 sessions of deliberate closure.

*Reward:* Wrecker Cycle capability unlocks (§4.4). Fifth broker introduced: **Pell Bray**, only accessible in the next region after cycling. Cosmetic: Wrecker callsign on ship + Wrecker's Log "veteran" title.

**Chapter 6 (optional lore) — "The Long Dark"**

Triggered only if the player has completed all five main chapters plus salvaged at least 3 named wrecks fully. The Long Dark is a wreck — or not-quite-a-wreck — far off established routes. Pre-Expansion hull design. Impossible metallurgy. Should not still be intact.

A longer narrative investigation (5-7 sessions). No broker will buy from this wreck — what you find here isn't for sale anywhere. The chapter ends without a commercial conclusion; the narrative conclusion is whatever the player chooses to do with what they've learned.

*Reward:* Thought cabinet entry "The Long Dark Remembers" unlocked. Final optional-content expansion (anomaly-class discoveries in future sessions). No mechanical capability gating — lore.

### 6.3 Chapter-end scenes

Structurally identical to mining's (~300-500 word scenes + Wrecker's Log journal page). Rendered with the active wreck at reduced opacity behind the dialogue panel. Each chapter's journal page becomes re-readable in the Wrecker's Log.

---

## 7. Optional content tracks

Four tracks. Each independent, each revisitable, none gating campaign progression.

### 7.1 Named Wrecks (unlocked Chapter 2)

Beyond the chapter-specific named wrecks (Signal Ship, What Was Taken's cargo hauler, Butcher's Bill's combat wreck, The Long Dark), there are additional named wrecks scattered through the Expanse. Each has a story unfolding across 3-4 sessions. Unlike chapter wrecks, Named Wrecks are entirely optional and don't gate campaign progression.

v1: 6 named wrecks in addition to chapter-embedded ones. Each with distinct character.

Example:
- **The Drift** — a habitat module that broke free decades ago, drifting alone. Interior preserved. Personal logs of a woman who lived there for two years after everyone else evacuated.
- **The Negotiator** — a diplomatic courier ship. All files encrypted. Decrypting requires artifacts from multiple sessions.
- **The Museum Ship** — a wreck that was itself a museum; contains already-salvaged-and-curated items from even older wrecks. Meta-archaeology.

Each Named Wreck has one **legendary artifact** — a Collector's Wall entry with substantial lore and a small passive bonus if kept.

### 7.2 Broker Relationships (unlocked across campaign)

Five brokers, each with distinct voice, market niche, and attitude:

| Broker | Specialty | Voice | Buying priorities |
|---|---|---|---|
| **Mattsen Holt** | Generalist | Honest-fence, dry | Standard rates; reliable |
| **Erika Sennen** | Historical / pre-Expansion | Tense, scholarly | Premium on artifacts with provenance |
| **The Third Shift** | No-questions | Encrypted, anonymous | Below market; takes anything; no rep |
| **Cesarine "Ces" Marrot** | Military-grade | Former military, tight | Modules and weapons components only |
| **Pell Bray** (post-cycle) | Expeditionary | Quiet, long-sighted | Pays well for deep-space recovery |

Each broker has ~8-12 dialogue scenes across their interaction arc. Some scenes are one-time (introduction, a specific sale); some cycle (standard transactions with rotating flavor).

Broker rep affects rates, unlocks specialty items they'll buy, and occasionally gates them against each other — selling an artifact to The Third Shift damages rep with Erika if Erika was looking for it.

### 7.3 The Collector's Wall (unlocked Chapter 1)

The signature optional content. A museum-wall UI within the Wrecker's Log where the Salvager's kept artifacts are displayed. Each artifact has:

- Visual (hand-authored pixel art)
- Lore entry (2-4 paragraphs of provenance)
- Source wreck (linked to Wrecker's Log entry)
- Small passive bonus if equipped (e.g., +5% crew loyalty during salvage, +3% scan speed in cold strata)

The player can equip up to **3 artifacts simultaneously** — small mechanical bonuses stack modestly; gameplay impact deliberately small.

v1: ~24 artifact slots (one per named wreck + chapter-embedded artifacts + legendary seam items from mining cross-pollination). Expandable.

### 7.4 Hostile Recoveries (unlocked Chapter 4)

Salvage during or immediately after combat encounters. Higher risk, unique rewards. When the player defeats an enemy in combat, a "Hostile Recovery" prompt can appear offering a short (5-10 min) high-pressure salvage session on the wreckage. Corruption timer is steeper; yields include weapon-grade components that aren't available in standard salvage.

Integration with combat Tier 2 doc (§9.3 below) — combat's destruction sequence leaves persistent debris; hostile recoveries let the player interact with it.

v1: 4 Hostile Recovery scenarios (one per major combat encounter type). Expandable.

---

## 8. Rendering changes — visual overhaul

### 8.1 Tier-weighted extraction feedback

Parallels mining's click tiering (§8.1 of mining doc). Four tiers:

| Tier | Trigger | Visual |
|---|---|---|
| 1 (common) | Scrap metal, common electronics extraction | Existing quality burst (blue sparkles) |
| 2 (notable) | Rare Parts, good-quality extraction | Larger burst in commodity-specific palette |
| 3 (rare) | Ingredient drop, excellent-quality extraction | Tier-2 + palette glow, slower fade, skill voice interjection chance |
| 4 (legendary) | Named artifact, module recovery, campaign milestone | Brief camera focus on cell, unique animation 0.8s, Wrecker's Log flagged, potential Collector's Wall notification |

### 8.2 Cockpit-window salvage entry

Parallel to mining's world-contextual entry (§8.2 of mining doc). ~1.2s transition from trading view through cockpit window to wreck approach:

- 0.0–0.3s: Trading view fades; cockpit window view interior
- 0.3–0.8s: External view — the derelict wreck fills the frame; scale communicated via cockpit-glass reflection
- 0.8–1.2s: Camera push through viewport into salvage grid

The wreck visible during entry is **specific to the wreck-type / named-wreck** — Cargo Bay wrecks look like broken freighters; named Signal Ship has a distinct silhouette. Reinforces identity before grid loads.

### 8.3 Persistent story fragment log

Current: fragments fade after 2s. Replace with:

- **Persistent notification** on fragment discovery ("Wrecker's Log entry added") — small icon bottom-right
- Player can click to open Wrecker's Log mid-session (game pauses briefly)
- Fragments accumulate as **readable entries** in the Wrecker's Log Chapter they belong to
- Re-readable anytime, permanent record

Fragments are no longer interruptive flashes — they're **collected evidence.**

### 8.4 Wrecker's Log UI

New view, accessed from salvage interface or any station hub. Contents:

- Campaign chapter progress (episodic cards for each chapter, each with readable journal pages)
- Named Wrecks register (visited wrecks, completion state, re-entry availability)
- Broker cards (5 brokers with rep tiers, current specialty, dialogue history)
- Collector's Wall (artifacts with lore, equipped state indicator)
- Thought cabinet (6 thoughts with progress bars)
- Session statistics

Styled as a battered notebook / logbook — worn leather border, hand-written-style typography on selected sections, occasional pressed-flower / token visual details (a pressed metal shaving from a deep extraction, a photo of a broker's dockside).

**Cost:** ~2 weeks. New view, substantial UI work.

### 8.5 Wreck-specific ambiance

Current atmosphere system has dust / vapor / sparks per derelict type. Extend:

- Per-named-wreck visual variation (Signal Ship has signal-static overlay; The Drift has drifting personal-effect particles; The Butcher's Bill has subtle warning-amber tint)
- Deck-specific atmosphere scaling (deeper decks have sparser light; more silent; less debris motion)
- Audio hooks for future Tier 3 (radio static for Signal Ship; silence for The Long Dark; mechanical creak for combat wrecks)

**Cost:** ~1.5 weeks. Extension to existing atmosphere system.

### 8.6 Broker dockside environments

Each of 5 brokers has their own docking environment — a small scene rendered for broker dialogue. Uses `hangar_*` environment variants from ship builder doc (§4.1) as base:

| Broker | Environment | Details |
|---|---|---|
| Mattsen Holt | `hangar_standard` with commerce-coded tint | Crowded small office, paper stacks, crooked clock |
| Erika Sennen | `hangar_military` with scholarly details | Books, artifact-case, muted lighting |
| The Third Shift | Unspecified anonymous dock | Dim, featureless, one monitor that never shows who you're talking to |
| Cesarine Marrot | `hangar_military` | Clean, regulation, military flag |
| Pell Bray | `hangar_industrial` variant | Remote, practical, worn |

**Cost:** ~1.5 weeks. Reuses ship builder's hangar environment system.

### 8.7 Module recovery cinematic

When the player successfully recovers a ship module (Chapter 4+ capability), a brief 2-2.5s cinematic:

- 0.0–0.3s: target cell highlighted with tier-4 VFX
- 0.3–1.0s: camera focus on cell; module silhouette resolves from wreckage (uses the new unified composite pipeline)
- 1.0–1.8s: module "lifts" out of the cell visually; brief particle trail
- 1.8–2.5s: module added to inventory; "Module Recovered: [Module Name]" notification

**Cost:** ~1 week. Reuses combat's camera system + unified ship-composite pipeline.

### 8.8 Wrecker Cycle cinematic

Parallel to mining's prestige cinematic (§8.4 of mining doc). ~3-4s:

- 0.0–0.8s: current region broker dock shown; sun glinting off wreckage
- 0.8–2.0s: ship departs dock; region recedes (camera pulls back, passes through stars)
- 2.0–3.0s: arrival at new region; new broker dock resolves
- 3.0–3.5s: Wrecker Standing bonus tally + new region state applied

**Cost:** ~1 week.

### 8.9 Skill voice corner region

Shared implementation with mining — same UI element, same rendering approach. Different voice content, same visual language. Corner region at bottom-left, italic serif text, palette-colored per skill. Cost absorbed into mining's §8.5 if built concurrently.

---

## 9. Gameplay changes forced by rendering and narrative

### 9.1 Module recovery (Salvager's signature capability)

**New mechanic.** At Chapter 4+ mastery, specific cells in salvage grids can contain recoverable ship modules. When scanned, these cells reveal as "Module: [type]" instead of commodity types. Extraction produces the module directly into the player's module inventory (bypasses commodity/refining conversion).

**Rate limits:**
- Maximum 1 module per session
- Maximum 1 module per named wreck visit
- Module tier caps at player's current ship tier (can't salvage Tier-5 modules on a Tier-2 ship)
- Certain rare modules only appear in specific named wrecks (e.g., the Butcher's Bill might yield a specific Crimson Reach raider variant of a weapon mount)

**Visual:** cells that contain modules display a distinct "schematic outline" on scan — the module's silhouette traced in cryo_fractal blue overlay. Players can prioritize (or not, since modules take the longest extraction time — 5s base).

**Balance:** a recovered module is free (no purchase cost) but has 60% of current hull/durability (damaged from the wreck). Must be refit at a shipyard for full functionality — small CR cost proportional to module tier. This prevents salvage from entirely obsoleting module purchases; it provides a parallel path with trade-offs.

### 9.2 System-bound derelict types

Currently derelict types are randomly selected. Change: weight derelict type selection by system:

| System | Dominant derelict type |
|---|---|
| Breakstone | Cargo Bay (industrial freight lanes) |
| Forgeworks | Engine Room (manufacturing loss) |
| Crimson Reach | Cargo Bay or combat wrecks (raider activity) |
| Collective space (multiple systems) | Lab Module (research ship losses) |
| Frontier Alliance systems | Mixed; slight Cargo Bay lean |

System-type binding strengthens worldbuilding — players learn where certain wreck types cluster.

### 9.3 Combat-salvage bridge

Per Hostile Recovery track (§7.4), the combat Tier 2 doc's destruction sequence (`30_overhaul_space_combat.md` §1.1) gains a "recovery prompt" hook — after combat resolves, if destroyed enemies left wreckage, the player can accept a short Hostile Recovery session (5-10 min) on-scene before leaving.

This is **cross-system integration** — flagged for coordinated implementation between combat and salvage phases.

### 9.4 Broker-rep-gated wholesale rates

Broker-specific rates: 5 brokers × rep tiers 1-5 = 25 possible rate modifiers. Implementation is additive on existing commodity sales: broker rep modifies the sale rate, not the underlying commodity value.

### 9.5 Sell-or-keep choices for artifacts

Named artifacts (Collector's Wall entries) present a **one-time choice** at recovery: sell to a broker (yields large CR + broker rep) or keep (Collector's Wall entry + Wrecker Standing + small passive bonus). Once sold, the artifact is gone; the Collector's Wall entry is marked "Sold to [Broker]" with a lore-only note.

This is gameplay-significant: players who exclusively sell accumulate CR; players who exclusively keep build their museum; most players will mix. Chapter 3's moral-weight beat is the first introduction to this choice.

### 9.6 No other gameplay changes

Corruption pressure, charge economy, parallel extraction limits, dual-mode interface — unchanged. Existing salvage configs unchanged except for derelict-type binding (§9.2).

---

## 10. Dependencies

### 10.1 On other overhaul docs

- **`20_aesthetic_bible.md`** — palette for skill voice colors (§5.2), environments (§8.6), faction overlay for broker affiliations
- **`30_overhaul_space_combat.md` §4.1** — unified ship pipeline (required for module recovery visualization)
- **`30_overhaul_space_combat.md` §4.4** — camera system (module recovery cinematic, cycle cinematic, cockpit entry)
- **`30_overhaul_space_combat.md` §4.8** — arena entry animation (module recovery and cycle cinematics adapt this)
- **`31_overhaul_ship_builder.md` §4.1** — hangar environment system (broker dockside reuses this)
- **`31_overhaul_ship_builder.md` §4.7** — module preview pipeline (module recovery visualization)
- **`32_overhaul_mining.md` §5.2** — skill voice corner region (shared implementation)
- **`32_overhaul_mining.md` §4** — balance discipline pattern

### 10.2 On production systems

- **Dialogue system** — broker interactions, chapter-end scenes, skill voices
- **Faction system** — Salvager is Frontier-coded but not faction-exclusive; broker rep separate from main-game faction rep (dedicated rep tracking)
- **Save system** — persistent state: Wrecker Standing, broker reps, named wreck visit history, Collector's Wall contents, Wrecker Cycles completed, thought cabinet state
- **Module inventory** — must accept "salvaged" variant modules (60% durability, requires refit)
- **NPC portrait pipeline** — hand-authored pixel art. ~5 portraits (Mattsen, Erika, The Third Shift represented abstractly, Cesarine, Pell)

### 10.3 On content authoring

- **~6 chapter-end scenes × 500 words** = ~3,000 words
- **5 skill voices × 25 lines** = ~125 lines (~1,500 words)
- **6 named wrecks × ~8 story fragments each** = ~48 fragments (~7,200 words). This includes new content AND repurposing the existing 21 fragments as chapter-bound content.
- **5 brokers × ~10 dialogue scenes each** = ~50 scenes (~7,500 words)
- **Collector's Wall artifact lore: 24 entries × ~200 words each** = ~4,800 words
- **Anomaly/hostile recovery content** = ~2,000 words
- **Thought cabinet entries** = ~600 words

**Total: ~26,600 words.** Larger than mining (~17,700) because brokers and artifact lore add significant content. Content-heavy doc, but per-piece short enough to distribute across Phase M3-M5.

---

## 11. Phasing

Salvage overhaul is large. Suggest 7 phases, several parallelizable with mining and combat overhauls.

### Phase S1 — Balance discipline formalization (~1 week)

- Codify three-tier currency structure
- Derelict-type system binding (§9.2)
- Broker rep system scaffolding
- Module recovery rate-limiting rules

### Phase S2 — Visual overhaul baseline (~3 weeks)

- Tier-weighted extraction feedback (§8.1)
- Cockpit-window salvage entry (§8.2)
- Persistent story fragment log (§8.3)
- Wreck-specific ambiance (§8.5)

**Parallelizable with** mining M2 phase.

### Phase S3 — Wrecker's Log UI + Mattsen + Chapter 1 (~3-4 weeks)

- Wrecker's Log full UI (§8.4)
- First broker (Mattsen) + first dockside environment (§8.6)
- Chapter 1 narrative content + first 5 story fragments authored
- Broker rep integration

### Phase S4 — Chapters 2-3 + Signal Ship + broker expansion (~4-5 weeks)

- Chapter 2 (Signal Ship, persistent named wreck)
- Chapter 3 (What Was Taken, moral choice)
- Brokers: Erika + The Third Shift
- Named Wrecks track unlocked (3 named wrecks v1 authored)
- Signal Tracker capability
- Skill voices implemented (~75 lines across 5 voices)

### Phase S5 — Chapter 4 + module recovery + Cesarine (~3-4 weeks)

- Chapter 4 (Butcher's Bill)
- Module recovery capability (§9.1) — the signature feature
- Module recovery cinematic (§8.7)
- Broker: Cesarine Marrot
- 2-3 more named wrecks
- Hostile Recovery track (§7.4) foundation

### Phase S6 — Chapter 5 + Wrecker Cycles + Chapter 6 (~3-4 weeks)

- Chapter 5 (The Long Wake)
- Wrecker Cycle capability (§4.4)
- Cycle cinematic (§8.8)
- Broker: Pell Bray
- Chapter 6 (The Long Dark, optional lore)
- Thought cabinet fully integrated
- Collector's Wall full implementation

### Phase S7 — Content expansion reservoir (~ongoing)

- Additional named wrecks (beyond initial 6)
- Additional artifacts
- Expanded broker content
- Quarterly events (a Salvager-specific event: e.g., "the Grey Market Exchange" — limited-time broker who buys banned goods at high rates)

### Total estimate: ~17-22 weeks for S1-S6. S7 is open-ended.

Parallelizable with mining and combat overhauls significantly — skill voice implementation, UI patterns, cinematic systems all shared.

---

## 12. Success criteria

Salvage redesign is done when:

1. **The Salvager identity is real.** A player at Chapter 5 has a distinct character voice and relationships with brokers that feel specific — not "salvage-NPC-1."
2. **Corruption pressure preserved.** The signature tension remains. New content doesn't dilute the session's forward momentum.
3. **Module recovery feels signature.** Pulling a thruster out of a wreck feels specifically Salvager-coded; the cinematic is memorable; players anticipate the moment.
4. **Named wrecks persist.** Players return to the Signal Ship, The Drift, etc., and the wrecks remember them.
5. **Broker relationships matter.** Selling to Mattsen vs. Erika vs. Third Shift feels different — both mechanically (rates) and narratively (what they say, what they remember).
6. **The Collector's Wall becomes a personal artifact.** Players take pride in their wall; first-time players screenshot and share it.
7. **Moral weight lands.** Chapter 3's choice is remembered. Players hold on to or sell specific artifacts for reasons they can articulate.
8. **Balance discipline holds.** Master-tier salvage slightly exceeds per-session yield of alternatives, accounting for risk. Module recovery doesn't obsolete module purchasing.
9. **Parallel identity works.** Player who ignores salvage still has a full Aurelia experience. Player who inhabits the Salvager gains a distinct second identity that differs *qualitatively* from the Prospector.
10. **Performance.** Salvage view holds 60 FPS with atmosphere particles + up to 4 active extractions + corruption overlay + story fragment notifications.

---

## 13. Open questions

1. **Module recovery durability penalty — is 60% right?** Too lenient and it obsoletes shopping; too harsh and it's not worth the session time. Calibrate during Phase S5.
2. **Broker exclusivity — should some brokers refuse to buy from Salvagers who've sold to specific rivals?** Mechanical answer: yes, but softly — rep damage rather than outright lockout. Narrative answer: yes, more dramatically (Erika won't speak to you if you've worked extensively with The Third Shift). Balance TBD.
3. **The Third Shift representation.** Encrypted / anonymous broker with no visible character — intentional choice or a content-authoring bandwidth dodge? v1 proposal: intentional. Third Shift is always a text-only interface, no portrait, no dockside environment. Reinforces identity.
4. **Hostile Recoveries depth.** v1 as "short sessions after combat" may be lightweight. Could expand to be a full sub-system with unique mechanics. Defer to Phase S7+.
5. **Cross-pollination with mining.** Some wrecks could be abandoned mining operations. A Prospector might have notes about such wrecks. Bi-directional narrative references between mining and salvage — possible but adds coordination cost. Flagged for coordination during M4 + S4 timing.
6. **Chapter 6 (The Long Dark) ending commitment.** Because it's lore-only with no broker/commercial resolution, the ending is open. Does the game acknowledge The Long Dark in other systems (combat NPCs mentioning rumors, etc.)? v1 proposal: a few scattered dialogue references, but nothing that resolves what the Long Dark is. Mystery preserved.

---

## 14. Out of scope

- **Salvage-ship specialization** — a dedicated "salvager ship" class is deferred
- **Multiplayer salvage cooperation** — not in current project scope
- **Procedural narrative generation** — chapters and named wrecks are authored
- **Full voice acting** — Tier 3 audio
- **Salvage in ground combat** — in-space only
- **Combat mechanical overhaul beyond Hostile Recovery hook** — covered in combat doc
- **New salvage mechanic overhaul** — corruption pressure / charge economy / dual-mode kept as-is; overhaul is additive content, not mechanical restructure

---

*Next Tier 2 doc candidate: `37_overhaul_refining.md` — lighter treatment per scope decision. Refining gets identity + lite narrative without the full dual-structure campaign of mining/salvage. Could also return to visual-only Tier 2 docs (galaxy map, trading, station hub) before closing out the mini-game identity set. User's call on order.*
