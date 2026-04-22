# Mining System Redesign

> **Status:** DESIGN — Tier 2 doc with **expanded scope** beyond the master plan's original "visual overhaul" framing. This doc covers the full system redesign: visual presentation, click-loop design, balance discipline, narrative identity, main mini-campaign, and optional content tracks.
>
> Mining is the first of Aurelia's mini-game systems to receive **full mini-game identity treatment** (see also forthcoming docs for `36_overhaul_salvage.md`; `37_overhaul_refining.md` will receive a lighter treatment). These systems are not "features" — they are **self-contained playable identities the player can inhabit**, with their own narrative spines, characters, and reward loops. They feed back into the main-game economy at controlled rates; they do not obsolete other systems.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, and `30_overhaul_space_combat.md` (shared camera / unified pipeline). Coordinates with `requirements/dialogue_writing_guide.md` for the narrative voice.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Loop design and balance discipline
5. Narrative identity — The Prospector
6. The Prospector's Road — main mini-campaign
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

Factual snapshot per survey of `mining_view.py`, `mining_vfx.py`, `data/economy/mining_configs.json`, and related systems.

### 1.1 What's already strong

- **Hybrid clicker-idler loop is real and working.** Left-click mines freely; right-click/E applies empowered clicks with energy cost. Passive drones auto-mine. The core interaction pattern exists and feels right.
- **Depth progression is viscerally satisfying.** Vertical depth meter + 5 color-coded atmospheric layers (Surface → Shallow Rock → Mid Strata → Deep Core → Abyssal Vein) + 0.6s dramatic layer-transition sequence with dust flash, falling fragments, and depth banner. **This is the best feel-element in the system and stays.**
- **Prestige loop exists.** Reset depth + upgrades → gain +10% strata multiplier per prestige level → exponentially-scaling prestige costs force deeper runs. Meta-loop is real.
- **Deep Core upgrades (9 strata-token purchases)** provide meaningful progression axis: Silo Expansion, Ore Scanner, Auto-Drill, Drill Power, Energy Conduit, Seismic Pulse, Depth Scanner, Automaton Core, Deep Strata.
- **Dual-currency design already balances correctly.** Ore → credits (main-game conversion, moderate rate). Ore + depth → strata tokens (internal-loop currency, stays in mining). **This is exactly the "closed-loop with gated conversion" discipline the user's design intent requires — it's already implemented.**
- **5 mining configs** with distinct rock distributions and grid sizes per system. Real variation.
- **Danger-based yield scaling** integrates mining into the galaxy-risk-reward structure (safe=1.0×, moderate=1.15×, dangerous=1.3×).
- **Click VFX** — hit particles, empowered burst, rock-break flash, chain shockwave ring. Hit feedback is solid.

### 1.2 What's weak — the central gap

**Narrative void.** Mining has zero character, zero mission, zero identity. Flavor text in `FIELD_DESCRIPTIONS` (*"Verdant Crystal Caves: Crystal formations glitter in the dark"*) is the extent of narrative presence. No NPCs. No quests. No "prospector" arc. No rival miners. No Union organizers. No foremen. No old-timers. Mining is mechanically sound and narratively invisible.

This is the **single point of redesign**. The mechanical loop is a working clicker/idler; we bolt a narrative identity onto it. The narrative becomes the thing that gives the clicks *meaning*.

### 1.3 Secondary gaps

**Gap 1: Click feedback lacks weight tiering.** Every click produces the same particle burst regardless of what was struck. A small rock and a rare find both flash white. Feedback tiers (common / notable / rare / legendary) would amplify the clicker's dopamine rhythm.

**Gap 2: The mining view is isolated from the world.** Entering mining is a hard transition from trading view → full-screen mining. No context of *where* the player is (which asteroid, what the cockpit sees, what's outside the rig's window). The player is somewhere in space; the mining view forgets.

**Gap 3: Drones and automation are functional but visually absent.** Drones exist mechanically (passive auto-mining) but you don't see them. Same with auto-drill. Watching your drones work is a core clicker pleasure (Cookie Clicker's grandmas, Universal Paperclips' autoclippers) and it's missing.

**Gap 4: Prestige is a menu action, not a moment.** Prestige — the meta-loop's crown mechanic — resolves as a confirm dialog. Reference clicker games make prestige a *visible event*: ship bursts through a ceiling, a paperclip becomes a galaxy. Aurelia's prestige should *feel* like a transition.

**Gap 5: Depth layer names are evocative but underwritten.** "Abyssal Vein" is a great phrase; there's no story behind it. What IS an Abyssal Vein? Why does one layer have that name and another doesn't? Layer names imply worldbuilding that doesn't exist in the narrative. Mini-campaign fills this.

### 1.4 What this doc addresses

- The central narrative void — **The Prospector** identity + main mini-campaign + optional content
- Click weight tiering (§8.1)
- World-contextual entry to mining (§8.2)
- Visible automation (§8.3)
- Prestige as a cinematic event (§8.4)
- Layer worldbuilding integration (§5 + §6)

Mechanical systems — click rate, energy cost, strata pricing, Deep Core upgrades — remain largely unchanged. We are *not* redesigning the working loop.

---

## 2. Target feel — influences and reference moments

### 2.1 The five-influence synthesis

Mining is **a clicker/idler with narrative identity + parallel-track progression + worker solidarity voice**. Five references, each carrying specific cargo:

**Cookie Clicker — exponential satisfaction and visible escalation**

- Numbers go up, visibly and fast. Buildings accumulate on-screen (grandmas, farms, mines). You *see* your empire grow.
- Prestige ("Heavenly Chips") is a meta-layer with its own currency and its own progression tree. Prestige resets feel like ascension, not restart.
- Flavor text accumulates. Every building has a rotating description that deepens its absurdity over time. Voice is the texture.

**Universal Paperclips — narrative that emerges through the loop**

- You don't read a story then play a game. You play a game and the story *happens to you* as numbers grow. This is the move.
- Narrative beats are triggered by mechanical milestones — "trust rating reaches X → next research project unlocks." The system rewards mastery with story.
- Voice is sparse but load-bearing. A few words at the right moment reframes everything.

**A Dark Room — minimalism that grows**

- UI starts small. Options appear as you progress. Every new button is a revelation.
- "Stranger" NPCs with 2-3 lines of dialogue carry enormous worldbuilding weight because they're rare.
- Background tint shifts (literal color change as the room becomes less dark). Environmental storytelling at minimum cost.

**Disco Elysium — inner-voice characters and thought cabinet**

- The player's head is full of voices — skills as characters with opinions. "Drama" chimes in when you lie. "Inland Empire" senses things others don't.
- For the Prospector: skills like **Ore Sense**, **Seismic Instinct**, **Union Heart**, **Deep Ear** become *voices* that comment during mining. Short, rare, flavorful lines. Not chatty. Present.
- Thought cabinet: multi-hour internalizations that unlock permanent small bonuses + identity traits.

**Stardew Valley — parallel track with community and rhythm**

- You're not alone. There's a town. NPCs have lives that continue when you're not there. You *return* to the mining system and find things have moved.
- Seasonal/temporal rhythm — specific events happen at specific times (festivals, birthdays). Mining in Aurelia should have analogous beats: Union meetings quarterly, rival prospectors' seasonal rotations, occasional galactic events that affect all mining.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Cookie Clicker, "first grandma accumulates visible in the bakery panel"** (2013). Before: you click cookies alone. After: a pixel grandma stands in your bakery, baking passively. *You are no longer alone.* Aurelia equivalent: first drone becomes visible on the mining grid as a small sprite that moves between rocks, working on its own. Not a stat line — a creature.

2. **Universal Paperclips, "trust points unlock Strategic Modeling"** (2017). A menu that didn't exist before suddenly exists. You click it and the game has deepened. Aurelia equivalent: completing a Prospector's Road chapter unlocks a new UI panel (Union Hall, or Deep Log, or Rival Ledger) that didn't exist in your previous session. Structural reveal.

3. **A Dark Room, "the stranger arrives"** (2013). A new button appears on the side panel. Clicking it brings a sparse NPC with maybe two lines. The world has grown. Aurelia equivalent: old-timer Augustyn appears at your mining site after a certain depth milestone. One line of dialogue per session; permanent presence.

4. **Disco Elysium, "Ancient Reptilian Brain advises on a skill check"** (2019). A thought voice interjects at a specific moment with one line. Aurelia equivalent: during a deep-core dive, **Deep Ear** (skill voice) whispers "*it hums wrong here*" one second before a hazard. Narrative + mechanical integration.

5. **Stardew Valley, "Night Market on Winter 15-17"** (2016). A yearly event that changes the world for 3 days. Aurelia equivalent: quarterly **Union Convocation** — mining sessions during the event have different NPC dialogue, special offers from the Union organizer, maybe a limited-time quest. Seasonal texture.

### 2.3 What this is not

- **Not Minecraft.** No building-in-the-world layer. The grid is tight and schematic; mining happens in a focused interface, not an open 3D world.
- **Not Factorio.** No supply-chain automation webs. Auto-drill + drones are a few visible helpers, not a factory sim.
- **Not a traditional JRPG grinding loop.** The clicks are fun (Cookie Clicker); the story is real (Paperclips); the world breathes (Stardew). Grinding for XP is not the aesthetic.
- **Not a fully-separate standalone game.** Mining lives inside Aurelia and connects back to it. The Prospector identity is one identity the player might inhabit; crew/combat/trade identities remain equally valid parallel paths.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Signal doing the work |
|---|---|---|
| Enter mining from trading view | Transition to focused work | Brief scene transition through the cockpit window view (the rig is visible through external porthole); arrival at claim site |
| Strike a common ore | Light satisfaction | Tier-1 VFX (existing); subtle tick |
| Strike a rare ore | Escalating thrill | Tier-3 VFX — color flash in ore-specific palette role, larger particle burst, slower pop-up fade |
| First time striking a legendary vein | Memorable moment | Tier-4 VFX — screen-edge light, unique SFX, inner-voice line from a Prospector skill, bookmark-worthy |
| Drone completes an auto-mine cycle | Mini-pleasure | Visible drone sprite scurries to a rock, mining particles appear, drone carries ore to silo, returns |
| Depth layer transition | Achievement | Existing banner stays — it's already good |
| Meet an NPC on-site | Curiosity + recognition | NPC sprite appears at edge of mining view; single line of dialogue; persistent presence |
| Skill voice interjects (inner dialogue) | Self-understanding | Italicized text in a dedicated corner region (not floating damage text); 0.8s hold; palette-colored per skill |
| Complete a Prospector's Road chapter | Identity earned | Chapter-end scene — longer dialogue, journal entry, mastery tier unlock visible as new UI element |
| Unlock an optional content track | Discovery | Quiet announce — a new marker appears on the mining view map screen, no ceremony |
| Prestige event | Transition / rebirth | 3-4s cinematic — rig pulls up from the claim, the asteroid recedes, new depths open below, numbers reset with ceremony |
| Return to mining after long absence | "Life continued without me" | NPC dialogue acknowledges time; event-timer shows progress on background events; crew / Union state has moved |
| Reach master prospector tier | Earned identity | All skill voices available; mentor NPC shifts role to peer; your ship's cockpit gains a small visible prospector token (cosmetic) |

### 3.2 What each emotion serves gameplay

- **Transition to focused work** (entry) → mining is a *place you go to work*, not a menu
- **Light / escalating / memorable satisfaction** (strike tiers) → the click-dopamine loop has rhythm and peaks
- **Mini-pleasure** (drones) → watching your empire function is its own reward (Cookie Clicker's bakery)
- **Curiosity + recognition** (NPCs) → the world is populated; you are not alone
- **Self-understanding** (skill voices) → you *become* a prospector through the voices; Disco Elysium's identity construction applied
- **Identity earned** (chapter completion) → progression has meaning beyond stats
- **Discovery** (optional unlocks) → there is always more
- **Transition / rebirth** (prestige) → the meta-loop has weight
- **"Life continued without me"** (return) → Stardew parallel-world feel; your absence is acknowledged
- **Earned identity** (mastery) → the campaign has a conclusion; you become who you were becoming

### 3.3 The non-goal: narrative-replaces-mechanics

The clicker loop is still the game. Narrative is additive — it gives the clicks meaning, not replaces them. A player who ignores narrative entirely still has a working mining minigame. A player who engages gets a richer one.

---

## 4. Loop design and balance discipline

The **non-negotiable** section. The reason the user's expansion works is the balance discipline; without it, mini-game identity bleeds into main-game progression and breaks the economy.

### 4.1 Three-tier currency structure (preserved from current state)

| Tier | Currency | Source | Sink | Converts to |
|---|---|---|---|---|
| **Main-game** | Credits (CR) | All systems (trade, combat, quests, mining wholesale) | Ship purchases, module purchases, services | — (terminal currency) |
| **Mining internal** | Strata Tokens | Depth advancement, full-clears, prestige multiplier | Deep Core upgrades (9 slots, max 1-5 levels), prestige costs | Prestige increases ore → CR conversion rate (+5%/level, max 5 prestiges = +25% CR yield) |
| **Mining campaign** | Prospector Standing + Claim Ledger entries | Prospector's Road chapter progress, optional content | Identity unlocks, cosmetics, narrative progression | Unlocks new Deep Core upgrade tiers + new ore types + master-tier capabilities |

**Critical discipline:** Strata Tokens and Prospector Standing **never convert directly to credits**. They convert to *capability* within the mining system. The main-game economy's only feed from mining is ore → CR at the wholesale rate, modified only slightly by prestige level (caps at +25%).

### 4.2 Income comparison (target, preserved from measured current state)

| Activity | Typical session | CR yield | Notes |
|---|---|---|---|
| Single trade route | 3-8 min | 2,000-5,000 | Direct, low-skill, low-risk |
| Standard combat encounter | 5-15 min | 1,500-4,500 | Includes salvage, module drops |
| Mining session (depth 30) | 6-10 min | 1,000-2,500 | Wholesale rate |
| Mining session (depth 80, advanced upgrades) | 15-25 min | 2,500-5,000 | Requires significant invested time |
| Mining prestige level 5 session (endgame) | 20-30 min | 4,000-7,000 | Highest mining output, requires full campaign + optional content |

**Mining at master tier slightly exceeds trading/combat per-session yield, but requires 10-15 sessions of investment to reach.** This is the correct ratio — the activity rewards specialization without obsoleting alternatives.

### 4.3 Campaign gating rules

The Prospector's Road unlocks capability tiers. These tiers apply inside mining only:

- **Chapter 1 complete** → Unlocks **Claim Ledger** UI panel + Union reputation track. No direct power.
- **Chapter 2 complete** → Unlocks **Deep Core upgrades tier 2** (levels 6-10 on applicable upgrades).
- **Chapter 3 complete** → Unlocks **Rival Prospectors** content track + **Legendary Seams** content track.
- **Chapter 4 complete** → Unlocks **master-tier Deep Core upgrades** (levels 11-15 on 4 of the 9 upgrades) + first master-exclusive ore type (**glasswater ore**, highest value).
- **Chapter 5 complete** → Unlocks **prestige level 6-10** (the current max is 5). Unlocks identity cosmetic: "Prospector" callsign on ship.
- **Chapter 6 (optional lore)** complete → Unlocks **Abyssal Vein** deepest content + secret ore type + thought cabinet entry.

Ignoring the campaign entirely caps the player at current-state content (prestige 5, current upgrade caps). That's still a functional mining system. Engaging with the campaign *earns* the expanded ceiling.

### 4.4 Optional content reward rules

Optional content tracks (§7) grant:
- **Cosmetics** — hull pixel stamps ("prospector marks"), cockpit badges, named titles, unique emote
- **Flavor items** — collectible lore objects for the Claim Ledger
- **Small mechanical bonuses** — +5% chain chance at one specific depth, +1 free empowered click per session, Union rep discounts (+5% on wholesale within Union space)
- **Rare cosmetic modules** — e.g., "Prospector's Pickaxe" (a cosmetic hull-pixel stamp or a mining-skin weapon variant that does the same damage as normal but renders distinctly)

**No optional content unlocks capability tiers that the main campaign gates.** You can mine-master and skip optional content; you can't optional-content your way to mastery.

### 4.5 Anti-cheese discipline

Known exploit patterns to guard against:

- **AFK drone maxing** — drones run passively. Cap per-session passive yield so infinite AFK sessions have diminishing returns (existing energy regen + drone scaling already soft-caps this).
- **Prestige-farming for CR** — prestige increases CR rate by only +25% at max (already implemented). This is tuned; do not let it inflate.
- **Session-reset cheese** — quitting mid-session to reset. Strata tokens, Prospector Standing, and Claim Ledger entries persist on session exit. No incentive to reset.
- **Optional-to-main bleed** — if an optional content track ever grants direct CR or a capability that the campaign doesn't gate, that's a balance bug. Flag in code review.

---

## 5. Narrative identity — The Prospector

### 5.1 Who is the Prospector?

You. The Prospector is the identity the player inhabits during mining. It is one of several parallel identities (Captain in combat, Trader in markets, Diplomat in politics, Crew-leader in missions); engaging with mining is choosing to inhabit this one for a session.

**Core voice (reference `requirements/dialogue_writing_guide.md`):**

- Aurelia's Miners Union has a specific cultural register — working-class, solidarity-oriented, grounded, wry. A prospector's voice is closer to a Wyoming oilfield worker or an Appalachian coal miner than to a space-opera hero.
- Speech patterns: understatement, occupational slang, measured, earned authority.
- Dry humor. Dark humor at pressure. Solidarity present but not preached — shown, not told.

**Core beliefs:**

- The rock doesn't care about you. You respect it.
- The Union is family, even when you disagree with it.
- A good claim is earned. A lucky strike is blessed.
- Old-timers are to be listened to.
- The deep doesn't give without taking.

**What the Prospector is not:**

- Not a lone-wolf treasure hunter (Crimson Reach is raider-coded; prospectors are union-coded)
- Not a corporate employee (the Prospector is independent, sometimes Union-affiliated, always working for themselves)
- Not an adventurer. A worker.

### 5.2 Skill voices (Disco Elysium-inspired)

Five inner-voice skills that interject during mining, each with a distinct personality. Lines are sparse — average 1-3 per session, triggered by specific mechanical events. Styled as italicized corner-region text with palette-colored stroke.

| Skill | Voice color | Personality | Triggers |
|---|---|---|---|
| **Ore Sense** | `solari_chrome_bright` (silvery) | Intuitive, soft, observational | Proximity to rare/legendary ore; first strike of a session |
| **Seismic Instinct** | `plasma_core` (warm orange) | Technical, alert, precise | Hazard proximity; chain detonation opportunity |
| **Union Heart** | `union_ceramic_bright` (warm gold) | Solidarity, wry, elder | Other prospector encounters; Union events; long-session endurance moments |
| **Deep Ear** | `cryo_fractal` (cool cyan) | Eerie, patient, ancient | Deep-core depth thresholds; anomaly investigations; layer 5 (Abyssal Vein) |
| **Weathered Hands** | `frontier_canvas` band mid (warm earth) | Veteran-grizzled, deadpan | Session start/end; fatigue milestones; drone maintenance moments |

**Example lines (one per skill, for voice calibration — not authored content):**

- *Ore Sense:* "The light's wrong on that one. There's something underneath it."
- *Seismic Instinct:* "Three clicks from a cascade. Place the next one carefully."
- *Union Heart:* "Gertie's daughter works the same seam. Don't be a stranger."
- *Deep Ear:* "It hums wrong here. Go quiet for a minute."
- *Weathered Hands:* "Six hours in. You'll want water before the next pulse."

Each skill has ~20-30 lines total across its full content library. Lines are cycled; rare lines (5%) are flagged as "memorable" and marked in the Claim Ledger.

### 5.3 Thought cabinet (Disco Elysium mechanic, scoped)

A lightweight thought cabinet — internal identity reflections that the Prospector can "internalize" over time. Each thought is unlocked by specific play patterns or campaign progress; internalizing takes in-game time (real-time hours of mining, or session-count) and grants a small permanent bonus + an identity trait visible in the Claim Ledger.

v1 thought library (6 thoughts, expandable):

1. **The Good Strike is Enough** — Internalize: 20 sessions without prestige. Grants: +2 energy pool; trait: "I don't chase the deep."
2. **The Union Pays Its Dues** — Internalize: Complete 3 Union-aligned side events. Grants: +5% wholesale in Union systems; trait: "Solidarity, signed."
3. **I Work Alone** — Internalize: Complete 20 sessions without a drone active. Grants: +1 click power; trait: "No partners, no trouble."
4. **The Deep Calls** — Internalize: Reach depth 100 in 5 consecutive sessions. Grants: +10% strata token yield at depth 80+; trait: "I go where others don't."
5. **A Prospector's Superstitions** — Internalize: Encounter 5 anomalies. Grants: +5% rare ore chance; trait: "I hedge my bets against the rock."
6. **The Name on the Door** — Internalize: Complete Chapter 5. Grants: Prospector callsign; trait: "I'm known."

Thoughts are permanent once internalized. Cannot be un-internalized (identity is permanent).

---

## 6. The Prospector's Road — main mini-campaign

The **gated capability path**. Six chapters. Each concludes with a mastery tier unlock (§4.3).

### 6.1 Pacing and structure

- **Each chapter:** 3-5 narrative beats within ~3-5 mining sessions. Narrative beats trigger at specific mechanical milestones (depth reached, ore count, session count, NPC encounter) rather than time.
- **Total campaign duration:** ~25-40 sessions of focused engagement, or ~15-25 hours of real-time play. Comfortably completable; not a second full game.
- **Delivery:** NPC dialogue on-site, Claim Ledger journal entries, occasional longer scenes at Union Hall (visitable from any mining-capable system's station hub). Dialogue uses the dialogue system, not a custom UI.
- **Voice:** grounded union-coded per §5.1. No melodrama. Chapter endings carry weight through what's *earned*, not through escalating stakes.

### 6.2 The six chapters

**Chapter 1 — "First Claim"**

Arrive at a starter mining system (likely Breakstone or Forgeworks). Meet **Augustyn "Auggie" Voss**, an old-timer who works a neighboring claim. He shows you the ropes — not with tutorials, but with presence. Over 4-5 sessions, you learn via his asides. Chapter ends when you've mined 500 ore and depth-reached 20.

*Reward:* Claim Ledger unlocked. Union reputation track begins. Auggie becomes a permanent NPC who appears at starter mining sites.

**Chapter 2 — "The Union Question"**

The Miners Union organizer, **Marta Beleń**, finds you at a mining site. She has an offer: join the Union officially, gain collective bargaining benefits (+5% wholesale in Union systems), accept obligations (occasional Union tasks). Alternately, stay independent — keep full autonomy, lose Union perks, gain Frontier sympathy. Either choice is valid; both open content. Chapter requires completing one Union task or one Frontier-sympathy act (in either case, 2-3 sessions).

*Reward:* Deep Core upgrades tier 2 (levels 6-10) unlocked. Faction reputation locked in — Union or Frontier path.

**Chapter 3 — "The Seam Wars"**

Another prospector, **Itzal Remé**, is working the same seam as you. This is a gameplay-integrated rivalry — Itzal's yields compete with yours in the same system. Resolution options: cooperate (share the seam, both yield less but gain rival reputation → friendly), confront (run Itzal off, harder initial conflict, exclusive yields → dominant), or negotiate a deal (each takes different ore types). Play out over 3-5 sessions.

*Reward:* Rival Prospectors optional content track unlocks (§7.1). Legendary Seams content track unlocks (§7.2).

**Chapter 4 — "The Deep Vein"**

Auggie tells you about a legendary seam in the deep core — one nobody's mined in a decade. You make the attempt. This is a single **extended session** (the mechanical arc spans one long play session, not multiple): descend past depth 100, survive the hazards, strike the vein. The Deep Ear skill voice gets particularly active here.

*Reward:* Master-tier Deep Core upgrades (levels 11-15 on Drill Power, Energy Conduit, Seismic Pulse, Depth Scanner). **Glasswater ore** unlocked as ore type — highest value, appears only at depth 100+, Chapter 4 alumni only.

**Chapter 5 — "The Name on the Door"**

Your reputation is established. Auggie is retiring and wants you to mentor a new prospector (NPC named **Cesarine Vega**). Over 3-4 sessions, you appear alongside Cesarine at starter mining sites — you are now the old-timer. This is the identity-consolidation chapter.

*Reward:* Prestige levels 6-10 unlocked. Cosmetic: Prospector callsign on ship + Claim Ledger "master" title.

**Chapter 6 (optional lore) — "The Abyss"**

Triggered only if the player has reached depth 150+ at least once. A discovery in the Abyssal Vein — something that doesn't fit the Union's understanding of the deep. A longer investigation (5-6 sessions) that ends with a choice: report it (Union-aligned), study it alone (Collective-aligned), bury it (Frontier-aligned). Narrative-only chapter; no mastery tier behind this one. Unlocks the "Abyssal Secret" thought cabinet entry.

*Reward:* Thought cabinet entry unlocked. Optional anomaly content expanded. No mechanical capability gating — this is the lore chapter.

### 6.3 Chapter-end scenes

Each chapter ends with a longer scene (~300-500 words of dialogue + Claim Ledger journal page). Scenes use the existing dialogue system, framed in a **chapter-end screen** with:

- The mining environment rendered at reduced opacity behind the dialogue panel
- Chapter-title card at top
- A single "mastery tier unlocked" visual beat on-screen after dialogue
- A claim-ledger journal-page visible afterward (the player can read the summarized chapter at any time)

Chapter-end scenes are **optional to re-read** from the Claim Ledger. Core narrative is replayable in journal form, even though the first encounter is the one that matters most.

---

## 7. Optional content tracks

Four tracks. Each independent, each revisitable, none gating campaign progression.

### 7.1 Rival Prospectors (unlocked Chapter 3)

Five named NPC prospectors, each with a distinct voice and working style. Periodically appear at your mining systems. Interactions:

- **Work alongside** — shared session; small yield penalty to you, rep gain with the rival
- **Race** — compete on a single session; winner gets a small one-time bonus
- **Gossip** — dialogue-only; reveals flavor about other prospectors, the Union, the Abyss
- **Trade tips** — offers a mechanical tip the player may not have discovered (e.g., "chain explosions reflect off iron deposits — strike iron last for a bigger chain")

Rivals have persistent state — you can build deep rapport with one over time. Each rival has ~6-8 interaction scenes before exhausting content.

### 7.2 Legendary Seams (unlocked Chapter 3)

Unique asteroid configurations with puzzle-like mining challenges. Each is a one-time discovery; completion marks it in the Claim Ledger.

Example legendary seams:
- **The Echo Vein** — chain detonations form a musical rhythm; yields massively when played as a sequence
- **The Cold Heart** — one massive rare-ore deposit, frozen; requires 40 consecutive empowered clicks with no misses
- **The Old Mine** — abandoned claim with a backstory; mining reveals artifacts (readable lore items) alongside ore
- **The Singing Glass** — crystal formation that hums; produces bonus yields in rhythm to the hum (audio-synced if music available)

v1: 6 legendary seams. Expandable.

Legendary seam discovery appears as an optional event while mining (similar to galaxy events). Players can decline to engage; missed seams re-roll over long intervals (not lost permanently).

### 7.3 Anomaly Investigations (unlocked progressively, first at depth 80)

Weird discoveries in deep strata. Each is a short (2-3 session) investigation chain.

Example anomalies:
- **The Breathing Rock** — a deposit that slowly changes shape between sessions. Pattern-recognition puzzle to identify what it is.
- **The Silent Layer** — a depth stratum where skill voices fall silent. Mine through it. Something is listening.
- **Whispers from the Deep** — single-line messages appear on the Claim Ledger between sessions. They don't clearly come from anywhere.

Unlocks lore items for the Claim Ledger. One anomaly chain references the Chapter 6 Abyss discovery if that content has been completed — cross-pollination between optional and main tracks.

### 7.4 Deep-Core Dives (unlocked Chapter 4, requires master-tier upgrades)

Endgame high-risk/high-reward sessions. A deep-core dive is initiated explicitly (separate button from normal mining session) and takes the player immediately to depth 150+. Hazards are more aggressive; yields are massive; skill voices are constant.

Deep-core dives are **timed sessions** (~15-20 real-time minutes). Completion grants rare mastery cosmetics + one of the top-tier ore types (including glasswater).

v1: 3 distinct dive scenarios, revisitable. Expandable.

---

## 8. Rendering changes — visual overhaul

### 8.1 Click weight tiering

Current click VFX is uniform. Introduce four tiers:

| Tier | Trigger | Visual |
|---|---|---|
| 1 (common) | Common/iron ore strike | Existing white-spark particle (unchanged) |
| 2 (notable) | Crystal ore strike; full chain | Larger burst, colored in the ore's emissive role (cryo_fractal for crystal, plasma_core for iron-tier) |
| 3 (rare) | Rare ore strike; first strike of a session | Tier 2 + brief screen-edge highlight, ore-specific palette glow, slower floating-text fade, SFX gain |
| 4 (legendary) | Legendary ore; anomaly triggered; campaign milestone hit | Full cinematic beat: slight zoom on struck rock (camera §4.4 from combat), inner-voice line from appropriate skill, unique particle animation 0.8s, Claim Ledger entry flagged |

**Cost:** ~1 week. Existing VFX extended per tier.

### 8.2 World-contextual mining entry

Entering mining from trading view currently hard-cuts to a full-screen grid. Replace with a ~1.2s transition:

- 0.0–0.3s: Trading view fades to cockpit window interior
- 0.3–0.8s: External view through the cockpit window — the mining rig deploying / the asteroid filling the frame
- 0.8–1.2s: Camera push-in through the viewport into the mining grid

This establishes **where** the player is. Exit reverses the sequence.

**Cost:** ~1 week. Scripted transition using existing camera system + new cockpit-window render composite.

### 8.3 Visible automation (drones, auto-drill)

Current: drones are a stat line; auto-drill is a background process. Upgrade:

- **Drones:** each drone is a visible 12×12px sprite that moves between rocks on the grid. Idle animation, mining animation (vibrating at rock), carrying-ore animation (small glow trailing), return-to-silo animation. Sprites rotate per drone "model" unlocked (3 sprites: basic, advanced, master).
- **Auto-drill:** when active, the weakest rock on the grid has a small visible drill icon hovering at it, animated vibrating. Makes the passive system *present*.

**Cost:** ~1.5 weeks. Drone sprite work (hand-authored pixel art per framework §11.5 or procedural per framework §3). Animation system integration.

**Benefit:** Cookie Clicker's visible-empire effect. Big feel upgrade per unit effort.

### 8.4 Prestige cinematic

Current: prestige resolves as a confirm dialog. Replace with ~3.5s cinematic:

- 0.0–0.5s: Current grid renders with faint pulsing glow; depth meter sweeps rapidly to 0
- 0.5–1.5s: Camera pulls up out of the asteroid (reusing combat's camera zoom/pan); we see the mining rig detach from the asteroid and rise
- 1.5–2.5s: Wide shot of the asteroid against void; rig pulls back toward the cockpit window
- 2.5–3.0s: Numerical celebration — prestige level chimes up, new multiplier appears with flourish
- 3.0–3.5s: Return to mining grid at depth 0, new prestige state applied

**Cost:** ~1 week. Scripted sequence using existing camera + UI flourish.

**Benefit:** prestige is a *moment*, not a menu action. Serves §3.1 transition/rebirth emotion.

### 8.5 Skill voice corner region

Dedicated UI region (bottom-left of mining view, ~300×60px at 1080p) where skill voice lines appear. Styled:

- Italic serif font (differentiation from UI sans-serif)
- Text color = skill's palette role (§5.2)
- Subtle stroke for legibility
- 0.8s hold + 0.6s fade per line
- Lines don't queue — if multiple skills would trigger, priority goes to the most-relevant-to-event

Corner region stays otherwise dark/empty — voices appear only when triggered.

**Cost:** ~4 days. Custom UI element + skill-voice trigger integration.

### 8.6 Depth layer identity reinforcement

Layer transition sequence (already good) gains per-layer audio cue slot (deferred to audio Tier 3) and layer-specific Prospector voice lines for **first arrival at each layer** (e.g., Weathered Hands comments on arrival at Mid Strata for the first time). Replayable from Claim Ledger.

**Cost:** ~3 days. Voice-line wiring + first-arrival tracking.

### 8.7 Claim Ledger UI

A new view, accessed from the mining view's UI bar. Contents:

- Campaign progress (chapter cards with completion state)
- NPC register (Augustyn, Marta, Itzal, Cesarine, rivals, anomaly NPCs — each with an unlocked/locked state and their visible portrait)
- Thought cabinet (6 thoughts v1, showing locked/unlocked state + progress bar for unlocking)
- Discovery log (anomalies found, legendary seams completed, memorable skill-voice lines)
- Statistics (existing stats aggregated into a nice page)

The Ledger feels like a prospector's personal journal — styled as aged paper with hand-drawn border motifs (framework §3 primitives: line segments, polygons).

**Cost:** ~2 weeks. New view + significant UI work.

### 8.8 Union Hall (new location)

A station subsystem accessible from any system with Miners Union presence. The Union Hall is a small interactive space where:

- Augustyn holds court at a table (visit for flavor dialogue, campaign progression beats)
- Marta Beleń has an office for Union business
- A bulletin board lists current Union jobs (optional content)
- A memorial wall lists prospectors who died in the deep (lore)

Rendered in AB §8.1's `hangar_industrial` environment variant (warm-cool mix with visible gantries).

**Cost:** ~2 weeks. New view + NPC sprites + dialogue content integration.

---

## 9. Gameplay changes forced by rendering and narrative

### 9.1 Chapter-gated upgrades

§4.3 gates Deep Core upgrade tiers behind campaign chapters. This is a gameplay change — currently upgrades gate on strata cost only. Implementation: upgrades show a "chapter required" lock state alongside strata cost. Players who don't engage with the campaign are capped at tier 1 upgrades (current behavior).

### 9.2 Faction lock from Chapter 2

Chapter 2's Union/Frontier choice locks in a faction path for the Prospector. Union-aligned prospectors gain Union rep faster; Frontier-aligned gain Frontier rep faster. This is a **soft lock** — player can still rebuild rep in the other faction through main-game questing, but Prospector-track rep is locked.

### 9.3 Optional content participation is persistent

Rival Prospector relationship states, Legendary Seam completions, and Anomaly Investigation progress persist across saves. Dropping mid-investigation and returning months later: state is preserved.

### 9.4 Prestige cost adjustment

Prestige costs scale exponentially in the current system. With the added prestige levels 6-10 from Chapter 5, extend the scaling: levels 6-10 cost ~2× their level-5 equivalent. Prestige remains achievable but meaningful at top tier.

### 9.5 No other gameplay changes

Click rates, energy regen, chain mechanics, danger multipliers — unchanged. Existing mining configs unchanged. The mechanical clicker loop is preserved.

---

## 10. Dependencies

### 10.1 On other overhaul docs

- **`20_aesthetic_bible.md`** — palette for skill voice colors (§5.2), environments for Union Hall (§8.8), faction overlay for Union/Frontier locked path
- **`30_overhaul_space_combat.md` §4.4** — camera system reused for prestige cinematic and world-contextual entry
- **`30_overhaul_space_combat.md` §4.8** — arena-entry-style animation reused for prestige cinematic

### 10.2 On production systems

- **Dialogue system** — narrative delivery for campaign dialogue, rival conversations, skill voices. Reuses existing.
- **Faction system** — Chapter 2's Union/Frontier choice hooks into existing faction rep tracking.
- **Save system** — new persistent state: Prospector Standing, Claim Ledger entries, thought cabinet internalizations, rival relationship states, anomaly progress. All flagged for save migration.
- **NPC portrait pipeline** — hand-authored pixel art per framework §11.5. ~7 new portraits (Augustyn, Marta, Itzal, Cesarine, 3 additional rivals).

### 10.3 On content authoring

Significant new narrative content required:
- ~6 chapter-end scenes × 400 words each = ~2,400 words
- ~5 skill voices × 25 lines each = ~125 lines (~1,500 words)
- ~6 rival prospectors × 8 interaction scenes × ~200 words = ~9,600 words
- ~6 legendary seams × flavor text = ~1,200 words
- ~6 anomalies × 3 sessions of content = ~2,400 words
- ~6 thought cabinet entries × flavor = ~600 words

**Total:** ~17,700 words of mining-specific narrative content. Substantial but scoped.

---

## 11. Phasing

Mining is the largest Tier 2 doc to date. Suggest 7 phases. Significant parallel opportunities.

### Phase M1 — Balance discipline formalization (~1 week)

- Codify 3-tier currency structure in code (§4.1) — currently implicit, make explicit
- Document anti-cheese discipline (§4.5) in test harness
- Calibrate prestige and chapter-gated pricing

**Why first:** before any new content, the balance scaffolding must be explicit.

### Phase M2 — Visual overhaul (visible automation + click tiering + prestige cinematic) (~3 weeks)

- Click weight tiering (§8.1)
- Visible drones + auto-drill (§8.3)
- Prestige cinematic (§8.4)
- Skill voice corner region (§8.5) — UI only, no content yet

**Why early:** improves current state of mining without requiring narrative authoring. Can ship standalone.

### Phase M3 — The Prospector's Road Chapters 1-2 + core NPCs (~4-5 weeks)

- Chapter 1 (Augustyn) — narrative authoring + implementation
- Chapter 2 (Marta, Union/Frontier choice) — narrative authoring + faction integration
- Claim Ledger UI (§8.7)
- Union Hall subsystem (§8.8)
- ~3 skill voice libraries (~75 lines authored)

**Why together:** Chapters 1-2 establish the identity; cutting them apart loses narrative coherence.

### Phase M4 — Chapters 3-5 + rival content (~4-5 weeks)

- Chapters 3 (Itzal), 4 (Deep Vein), 5 (mentorship arc)
- Rival Prospectors content track (§7.1)
- Legendary Seams content track (§7.2, 3 of 6 seams)
- Remaining skill voice libraries
- Thought cabinet integration (first 4 thoughts)

### Phase M5 — Chapter 6 + Anomalies + remaining optional content (~3-4 weeks)

- Chapter 6 (Abyss) — optional lore chapter
- Anomaly Investigations (§7.3)
- Deep-Core Dives (§7.4)
- Remaining Legendary Seams (3 of 6)
- Remaining thought cabinet entries

### Phase M6 — World-contextual entry + polish (~1-2 weeks)

- World-contextual mining entry animation (§8.2)
- Depth layer identity reinforcement (§8.6)
- Polish pass on VFX, transitions, cinematic pacing

### Phase M7 — Content expansion reservoir (~ongoing)

- Additional rival prospectors (beyond initial 5)
- Additional legendary seams and anomalies
- Quarterly events (Union Convocation, etc.)

Content additions are cheap once infrastructure is in place. Phase M7 is a perpetual low-priority queue.

### Total estimate: ~16-22 weeks for M1-M6. M7 is open-ended.

Parallelizable with other Tier 2 overhauls where dependencies allow (camera work from combat, palette from Bible, save migration coordination).

---

## 12. Success criteria

Mining redesign is done when:

1. **The Prospector identity is real.** A player completing Chapter 5 feels they have *become* something, not just leveled up.
2. **Click-loop satisfaction preserved and enhanced.** Current loop feel (strong per survey) is not diminished; tier weighting amplifies dopamine rhythm.
3. **Balance discipline holds.** Mining at master tier slightly exceeds per-session yield of trading/combat, earned through 10-15 session investment. Optional content does not obsolete main campaign.
4. **Narrative content lands.** Player recognizes NPC names unprompted, remembers scenes, quotes skill voices spontaneously.
5. **Parallel identity works.** Player who ignores mining still has a full Aurelia experience. Player who inhabits the Prospector gains a second full experience inside the one game.
6. **Visible automation delivers the empire-grows feeling.** Cookie Clicker's grandma moment is achieved with drones.
7. **Prestige is an event.** Players pause to watch the cinematic the first time they prestige.
8. **Skill voices feel alive.** Players quote them. "The light's wrong on that one" becomes a phrase players use.
9. **Performance.** Mining view holds 60 FPS with all automation visible (up to 6 drones + auto-drill + chain cascade particles + tier-4 VFX).

---

## 13. Open questions

1. **Voice acting?** Skill voices and campaign dialogue are written; are they also voiced? Out of scope for v1 (audio framework is Tier 3); flag for future.
2. **Rival prospector number.** 5 named rivals in §7.1 is provisional. Playtesting may suggest 3 is enough; 8 is too many. Tune after Phase M4.
3. **Thought cabinet timer.** Disco Elysium's thoughts internalize in real-time hours. Aurelia's should probably scale to session count rather than wall time — less punishing for casual players. Calibrate in M4.
4. **Union Hall as single location or system-specific.** v1 proposal: one Union Hall visible in every Miners Union system, same NPCs (Augustyn, Marta) logically present in all. Simpler. Alternate: one canonical Union Hall (in a specific flagship system) — feels more grounded but increases travel friction.
5. **Chapter 6 as canonical or hidden.** v1 proposal: optional content, discovered by players who reach depth 150. Alternate: canonical but late-game. Discuss during M5.
6. **Cross-pollination with salvage identity.** Salvage (forthcoming doc) may have narrative threads that intersect with mining (prospectors who also salvage; abandoned mining wrecks). Design coordination needed with salvage doc.

---

## 14. Out of scope

- **Mining-ship specialization** — a "prospector ship" module class is deferred; current ship builder + upgrades handle the functional needs
- **Mining in ground combat** — mining is in-space only; ground mining is a different system if it ever ships
- **Multiplayer prospecting** — not in current project scope
- **Procedural campaign generation** — chapters are authored, not procedural
- **Full voice acting** — Tier 3 audio concern
- **Cross-mini-game integration** — mining narrative is standalone; intersections with salvage/refining flagged but not scoped here
- **New mining hazard types** — current hazard system is sufficient; balance pass, not redesign

---

*Next Tier 2 doc candidate: `36_overhaul_salvage.md` — applies the same full-identity treatment learned here. The Salvager identity + its own narrative track. Alternately: return to visual-overhaul-only Tier 2 docs (`33_overhaul_galaxy_map.md`, `34_overhaul_trading.md`, `35_overhaul_station_hub.md`) before coming back for salvage and refining. User's call on order.*
