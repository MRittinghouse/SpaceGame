# Refining System Redesign

> **Status:** DESIGN — Tier 2 doc with **lighter mini-game identity treatment** (see `project_overhaul_minigame_identity.md` in memory for the pattern variants). Refining receives identity + lite narrative (seasonal rhythms and rediscovery arcs) without the full chaptered campaign of mining (`32_overhaul_mining.md`) or salvage (`36_overhaul_salvage.md`).
>
> Refining is the third and final mini-game in Aurelia's identity set. Where the Prospector is union-coded solidarity and the Salvager is Frontier-coded haunted, the **Fabricator** is Collective-coded precision — quiet craft, patient mastery, institutional knowledge. Together, the three identities deliberately map to Aurelia's three primary cultural registers. A player who inhabits all three has walked through Aurelia's cultural geography by work.
>
> Inherits from `20_aesthetic_bible.md`, `10_programmatic_generation_framework.md`, `32_overhaul_mining.md`, `36_overhaul_salvage.md` (pattern). Coordinates with `requirements/dialogue_writing_guide.md` for narrative voice.

---

## Table of Contents

1. Current state — honest assessment
2. Target feel — influences and reference moments
3. Player-experience goals — emotions per moment
4. Loop design and balance discipline
5. Narrative identity — The Fabricator
6. Mastery progression arc (no chaptered campaign)
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

Factual snapshot per survey of `refining_view.py`, `refining_vfx.py`, `models/refining.py`, `data/economy/recipes.json`.

### 1.1 What's already strong

- **Recipe system is substantive.** 38 recipes (22 base + 16 discoverable) across 3 tiers and 4 categories (commodity / upgrade / equipment / trade_good). Real progression surface.
- **Dual discovery paths** — reach mastery level 3 on a prerequisite recipe OR pay schematic_data cost. Respects different player temperaments (grinder vs. focused learner).
- **Forge atmosphere with heat scaling** (cold → warm → hot → blazing) is already a signature feel-element. Queue intensity + recipe tier drive the visual. Polished idle-game aesthetic.
- **Mastery tier system** (bronze / silver / gold via 3 / 8 / 15 craft thresholds) with particle-burst celebration at each tier-up. Visible progression.
- **Forge tokens as meta-progression currency** — used to purchase forge upgrades (thermal_efficiency, catalyst_resonance, queue_expansion, forge_buffer, material_insight). Closed-loop internal economy already exists.
- **Batch queuing (1-5 jobs)** respects player time. Idle-friendly without being mindless.
- **Buffer system decouples refining from cargo.** 50-unit base capacity (upgradeable). Sessions don't get cut short by cargo-full states.
- **Integration with mining/salvage/ship builder** is already real — raw materials flow through refining into crafted components. The economic chain works.

### 1.2 What's weak — the central gap

**Narrative void** (same pattern as mining's — different specifics). Refining has zero NPCs, no master-fabricator mentor, no Collective laboratory identity, no seasonal events, no craft-pride voice beyond flavored recipe descriptions. The forge is a *mechanism* that happens to be located in stations; it isn't a *trade* inhabited by people.

Refining's gap is **shallower** than mining's or salvage's — because there's no narrative DNA to corrupt, authoring it fresh is cleaner. And because refining doesn't carry the genre ambition of salvage (archaeological horror) or mining (solidarity epic), the lighter-treatment approach fits: seasonal rhythms + identity voice + mastery milestones, not a 6-chapter story.

### 1.3 Secondary gaps

**Gap 1: No failure or quality variance.** Current refining is 100% success-guaranteed; outputs are always the calculated yield. Surveyor flagged this as a "risk-free" problem. Design response: **don't introduce failure** (that would feel punishing) but **introduce quality variance as a mastery reward** (§9.1). Higher-mastery crafts can produce S / A / B / C grade outputs with small beneficial bonuses at higher grades. Downside stays absent; upside stratifies. Mastery feels earned without making the system hostile.

**Gap 2: Recipe descriptions are flavor, not character.** Recipe flavor text exists ("*Fuse alloy composite with combat salvage to produce heavy-duty hull plating*") but reads as mechanical description. The Fabricator's voice should inflect recipe text — not everywhere, but at key recipe unlocks, with small character-coded commentary.

**Gap 3: Discovery is transactional.** Recipe unlocks via mastery threshold or schematic cost — both mechanical. No discovery scene, no "a Collective researcher shared this schematic after seeing your last commission," no sense of the larger fabricator community. Discovery could be textured without becoming a full chapter arc.

**Gap 4: Sessions don't connect to time or place.** Each refining session is independent. The forge doesn't care when you last used it or who last used it. Other systems (Expanse markets) have time-of-day / seasonal dynamics; refining doesn't. Adding light temporal rhythm (§6.1) gives refining a heartbeat.

**Gap 5: Mastery level-up feels punctual, not weighty.** Current mastery level-up triggers a particle burst + banner. Fine for moment-to-moment, but reaching *gold mastery* on a recipe should carry more weight — it's a genuine milestone (15 crafts of the same recipe). A longer celebration with a skill-voice line ("*That one will last*") would make it land.

**Gap 6: No craft-pride persistence.** Mining has the Claim Ledger; salvage has the Wrecker's Log + Collector's Wall. Refining has stats screens. No persistent record of what you've mastered, which Exposition pieces you've submitted, what your Fabricator reputation is. Adding a **Fabricator's Register** closes this gap (§8.7).

### 1.4 What this doc addresses

- The central narrative gap — Fabricator identity + seasonal events + Register UI
- Quality variance system (§9.1) — mastery as upside stratification
- Recipe discovery textured with light narrative framing (§6.3)
- Temporal rhythm via seasonal events (§6.1)
- Mastery milestone reinforcement via skill voices (§5.2)
- Fabricator's Register as persistent craft-pride artifact (§8.7)

Recipe mechanics, mastery levels, forge tokens, batch queuing, discovery paths — all preserved.

---

## 2. Target feel — influences and reference moments

### 2.1 The four-influence synthesis

Refining is **craft-pride precision idle + quiet seasonal rhythm + Collective-coded voice**. Four references, each carrying specific cargo:

**Stardew Valley — seasonal rhythm and craft satisfaction**

- Seasons mark time. Events recur. Your crops mature on schedule. Your artisan goods age in barrels.
- Satisfaction of *watching things become*. A keg full of pale ale, checked tomorrow, is wine. The game respects your patience.
- Community without exposition — NPCs live their lives; you participate or don't; the world moves regardless.

**Factorio — creation escalation and visible infrastructure**

- Input → process → output. The pleasure is *the line working*. A factory humming is its own reward.
- Scale matters. One smelter is a prototype; twelve smelters in parallel is a factory.
- Efficient design *looks* efficient. Neat rows of machinery carry pride.

**Dwarf Fortress (masterwork items) — craft mastery as identity anchor**

- A **masterwork** item is different from a normal item. Your dwarf, over hundreds of crafts, becomes *someone who makes masterworks*.
- Items have provenance. "Engraved on the hilt is an image of Urist McMiner, in stunning crystal glass." The history carries.
- Craft identity is earned, not assigned. "Legendary Weaponsmith" is a title your dwarf grew into.

**Citizen Sleeper — idle-work as identity, sparse prose, meditative**

- Pure action-economy gameplay that *accumulates* into identity. You chose what work mattered; you became defined by it.
- Sparse worldbuilding prose during idle moments. A line about your character observing the light, a line about the cold.
- Respect for slow progress. No escalating crisis; just the daily work of being someone.

### 2.2 Reference moments (specific, cited, imitable)

Five reference moments to design against:

1. **Stardew Valley, "Fall's Stardew Fair"** (2016). A recurring seasonal event. You submit items to the grange display; the whole town attends. Aurelia equivalent: **The Exposition** (§6.1) — quarterly Collective crafting showcase. Submit your masterwork pieces; receive evaluations; gain Fabricator reputation.

2. **Factorio, "first smelter line running on automation"** (2020). No drama. Just belts moving. Iron becomes plates without you watching. Aurelia equivalent: forge atmosphere already carries this feel well — preserve and strengthen with visible multi-job queue animation (§8.3).

3. **Dwarf Fortress, "first legendary craft"** (2006). "Urist McAnvil has created a masterwork!" A specific item your specific dwarf made. It enters legend. Aurelia equivalent: reaching **gold mastery** on a recipe triggers a longer celebration beat (§8.5) + a Fabricator's Register entry marking that item specifically. You are now *the Fabricator who makes those*.

4. **Citizen Sleeper, "idle morning observation"** (2022). Two paragraphs of prose about your character's morning — the light, the cold, what they remember — as a reward for no particular action. Aurelia equivalent: **skill-voice reflections** at session milestones. Rare, optional-to-read, flavor-heavy.

5. **Stardew Valley, "mail from a villager"** (2016). Periodic letters from NPCs thanking you for something or announcing an event. Lightweight, recurring, persistent. Aurelia equivalent: **Fabricator's correspondence** — occasional messages from Collective peers referencing your recent crafts ("Saw your plating on the Meridian. Nice flux handling."). Low authoring cost, high texture.

### 2.3 What this is not

- **Not a factory-builder.** No conveyor belts, no spatial layout puzzles. Refining stays queue-and-wait.
- **Not a cooking mini-game.** No real-time attention mechanics (stirring pots, watching timers). Batch queuing + mastery passives keep it idle-friendly.
- **Not a narrative RPG.** No chaptered campaign. Narrative texture comes from seasonal events, skill voices, and occasional flavor — never from story arcs demanding attention.
- **Not Mining-but-for-refining.** Deliberately lighter. Players who want deep narrative identity choose Prospector or Salvager. Players who want craft satisfaction and competence-growth choose Fabricator.

---

## 3. Player-experience goals — emotions per moment

### 3.1 The emotion ledger

| Moment | Target emotion | Signal doing the work |
|---|---|---|
| Enter refining | Focused work | Forge atmosphere ignites; heat scales appropriately; a skill voice may acknowledge first entry of the day |
| Select a familiar recipe | Practiced rhythm | Recipe card highlights cleanly; memorized-cost-and-time summary |
| Select a recipe you haven't mastered | Anticipation | Mastery progress bar visible; "X crafts to silver" implied reward |
| Queue a batch | Commitment | Particle rate increases; forge hum intensifies; buffer indicator updates |
| Mastery level-up (bronze / silver) | Small satisfaction | Existing celebration — good as-is |
| Mastery level-up (gold) | Genuine milestone | Extended celebration: skill voice line, Register entry, longer particle sequence |
| Recipe discovery via mastery | Earned knowledge | New recipe reveals with brief flavor — "You've seen enough iron to know where the alloy lives" (skill voice) |
| Recipe discovery via schematic | Transactional but clean | Current flow preserved; small flourish on unlock |
| Quality variance S-grade output | Quiet pride | S-grade outputs get a brief gold-shimmer particle + Register entry; skill voice may comment |
| Seasonal Exposition arrives | "Something is happening" | Notification on entry to any refining-capable station; submission panel accessible |
| Exposition submission | Focused judgment | Choose your best recent crafts; submit; wait for evaluation at end of event |
| Exposition results | Craftsmanly pride or reflection | Grade-by-grade evaluation; reputation change; flavor line per submission |
| Fabricator correspondence arrives | Connection to peers | Brief inbox marker; read a 2-4 paragraph note from a named Collective peer |
| Long session without break | Meditative focus | Skill voices surface slower, rarer, more reflective lines; forge atmosphere shifts slightly warmer |
| Session close | Earned rest | Buffer transfer + summary; a skill voice may acknowledge the work ("good batch — sleep on it") |

### 3.2 What each emotion serves gameplay

- **Focused work / practiced rhythm** (entry, familiar recipes) → the forge is a place you *return to*, not visit
- **Anticipation / earned knowledge** (unmastered recipes, discoveries) → progression has intrinsic interest
- **Small and genuine satisfaction** (mastery tiers) → the mastery curve has weight at its peaks
- **Quiet pride** (S-grade, Register) → craft-identity without grandeur
- **"Something is happening"** (Exposition) → refining has a heartbeat beyond individual sessions
- **Connection to peers** (correspondence) → the Fabricator isn't isolated; they're in a community
- **Meditative focus** (long sessions) → refining rewards attention without demanding it
- **Earned rest** (session close) → the loop respects the player's time

### 3.3 The non-goal: escalating stakes

Refining doesn't build toward climax. There is no boss fight, no final confrontation, no "becoming the ultimate Fabricator." The arc is *competence deepening over time* — the same recipe, made more precisely, year over year. The Dwarf Fortress legendary-craftsman move: you are someone who does this work. That is the aesthetic.

---

## 4. Loop design and balance discipline

Inherits the **three-tier currency discipline** from `32_overhaul_mining.md §4.1` and `36_overhaul_salvage.md §4.1`. Parallel structure.

### 4.1 Three-tier currency structure

| Tier | Currency | Source | Sink | Converts to |
|---|---|---|---|---|
| **Main-game** | Credits (CR) | Selling refined commodities and crafted components | Ships, modules, services | — (terminal) |
| **Refining internal** | Forge Tokens | Job completions (existing formula) | Forge upgrades (thermal_efficiency, catalyst_resonance, queue_expansion, forge_buffer, material_insight + new tiers) | Improves processing speed, yield, queue capacity |
| **Refining reputation** | Fabricator Standing | Gold-mastery achievements, Exposition submissions, quality S-grades | Fabricator's Register entries, Seasonal event participation, master-tier recipe unlocks | Unlocks seasonal-event access, master recipes, reputation-gated upgrades; **never direct CR** |

**Critical discipline preserved:** Forge Tokens and Fabricator Standing never convert to CR. Crafted outputs convert to CR at commodity/component market rates, unchanged.

### 4.2 Income comparison (target)

| Activity | Typical session | CR yield | Notes |
|---|---|---|---|
| Single trade route | 3-8 min | 2,000-5,000 | Direct |
| Mining (master tier) | 20-30 min | 4,000-7,000 | Per `32_overhaul_mining.md` |
| Salvage (master tier) | 20-35 min | 5,000-9,000 | Per `36_overhaul_salvage.md`, risk-adjusted |
| Refining (basic, selling outputs) | 10-20 min | 1,500-3,500 | Direct commodity sale |
| Refining (mastery-rich, selling crafted components) | 15-25 min | 3,000-6,000 | Crafted components have higher margin |
| Refining (master Fabricator, Exposition-winning crafts sold) | 20-30 min | 4,500-7,500 | Exposition S-grade bonuses + top-tier components |

**Refining at master tier falls between mining and salvage** in per-session yield. This is deliberate: refining is **lowest-risk** of the three (no corruption pressure; no salvage pit collapse). Lower yield ceiling reflects lower risk. Players who want maximum income pick salvage; players who want steady satisfaction pick refining.

### 4.3 Progression gating (non-chaptered)

Because refining has no chaptered campaign, capability gating uses **achievement-style milestones** instead:

- **Reach Fabricator Standing tier 2** → Seasonal events unlocked (Exposition, Commission, etc. per §6.1)
- **Reach Fabricator Standing tier 3** → Master-tier recipe discoveries trigger automatically (no schematic cost)
- **Reach Fabricator Standing tier 4** → Quality variance system unlocks (§9.1)
- **Reach Fabricator Standing tier 5** → Fabricator's Register advanced sections (Masterwork Registry, Exposition Archive) unlock

Standing accumulates through:
- Each mastery level reached: +1 per bronze, +2 per silver, +3 per gold
- Each recipe discovery: +2
- Each Exposition submission: +1 per item, +5 per S-grade, +10 per Exposition Win
- Each Commission completion: +5-20 per commission based on complexity

Tier thresholds: 20 / 50 / 120 / 250 / 500 Standing. Ignoring this progression caps the player at current-state refining (Standing tiers 0-1). Engaging unlocks the full identity.

### 4.4 Cyclical events (no prestige equivalent)

Refining does **not** have a prestige / cycle mechanic parallel to mining (§4.4 of mining doc) or salvage Wrecker Cycles. Prestige-style resets work for exponential-progression systems; refining's progression is **not exponential** — it's linear skill accumulation. Forcing a reset would violate the Dwarf Fortress legendary-craftsman aesthetic.

Instead, **seasonal events** (§6.1) provide the temporal rhythm that prestige provides for mining/salvage. Players don't reset; they *mark time* through Expositions, Commissions, and Rediscoveries.

### 4.5 Optional content reward rules

Inherits the discipline from mining/salvage. Cosmetics + small bonuses + collectibles, never mastery capability.

Refining-specific optional rewards:
- **Fabricator's Register entries** — the signature refining cosmetic track (masterworks, Exposition wins, Rediscovered recipes)
- **Named commission contracts** — unique one-time orders with specific clients, unique flavor text
- **Masterwork stamps** — crafted items can bear a visible mark indicating master-fabricator origin (cosmetic on ship modules)
- **Seasonal titles** — "Exposition Winner 2336.Q2", "Recipe Rediscoverer", "Blazing Forge" based on seasonal achievements
- **Collective correspondence archive** — accumulated mail from Fabricator peers, readable in Register

### 4.6 Anti-cheese discipline

- **No AFK mastery** — mastery levels require actual crafts; idle time doesn't accumulate mastery
- **Quality variance gated by mastery** — can't cheese S-grade outputs on recipes you haven't mastered
- **Exposition submissions rate-limited** — one submission per Exposition event, forcing selection discipline
- **Commissions have true deadlines** — accept a commission, deliver within the event window or lose the reward
- **No duplicate Exposition wins** — can't re-submit the same piece; wins are per-event

---

## 5. Narrative identity — The Fabricator

### 5.1 Who is the Fabricator?

You, when you inhabit refining. The third of Aurelia's deliberate identity triad.

**Core voice (reference `requirements/dialogue_writing_guide.md`):**

- Aurelia's refining work is Science-Collective-coded — precise, methodical, respects materials. Not mystical; not industrial-grim. Think *experienced materials scientist* or *master ceramicist* — someone whose respect for their medium is practical, not performative.
- Cultural resonance: postwar Japanese swordsmith + Bauhaus workshop master + Bell Labs engineer + Arts & Crafts woodworker. Craft pride without pretension.
- Speech patterns: precise, measured, occasionally dry. Uses technical vocabulary without making it armor. Appreciates elegance.
- The Fabricator is **quiet**. Not taciturn — economical. Speaks when it's worth speaking.

**Core beliefs:**

- Material has a voice. Listen first.
- A good craft is not the fastest one. It's the right one.
- Mastery is hours, not talent.
- An elegant solution is half the work already.
- The work teaches the worker.

**What the Fabricator is not:**

- Not a mystic (no "the materials speak to me" language — materials have physics, the Fabricator reads physics well)
- Not a guild-traditionalist (Fabricator is *learned*, not inherited — institutional knowledge, not family lineage)
- Not a factory worker (Fabricator is small-batch, precision-focused — not industrial scale)
- Not a perfectionist — a *pragmatist*. Knows when "good enough" is good enough.

### 5.2 Skill voices (5 voices, distinct from mining and salvage)

Five inner-voice skills that interject during refining. Parallel implementation to mining/salvage (§5.2 of each), deliberately different voices.

| Skill | Voice color | Personality | Triggers |
|---|---|---|---|
| **Material Sense** | `collective_composite` bright (cool blue-white) | Reads raw inputs; knows what's pure and what's adulterated | First use of an ingredient type in a session; low-quality input detected |
| **Heat Eye** | `plasma_core` (warm orange) | Reads forge conditions; knows when to intervene | Queue intensity transitions; atmosphere heat-level shifts; forge upgrades active |
| **Recipe Memory** | `solari_chrome_bright` (silvery) | Institutional knowledge; recalls prior sessions | Recipe revisits after long absence; mastery milestones; discovery moments |
| **Patient Hand** | `union_ceramic_bright` (warm gold) | The one who waits; doesn't rush | Long batches; session-length milestones; meditative moments |
| **Quality Ear** | `hud_cyan` (sharp teal) | Hears when something rings true or false | Quality variance rolls; S-grade moments; anomalous outputs |

**Example lines:**

- *Material Sense:* "The ore's clean. Good batch from the deep seam."
- *Heat Eye:* "Forge is running cool. Add a second job to keep the heat up."
- *Recipe Memory:* "Last time you ran this, the yields were off. Might be the flux ratio."
- *Patient Hand:* "Don't rush it. The alloy needs the full cycle to bind."
- *Quality Ear:* "That one rang true. Worth the Register entry."

Each skill has ~20-30 lines total. Rare "memorable" lines (5%) are flagged for the Register.

### 5.3 Thought cabinet (4 thoughts — fewer than mining/salvage's 6, reflecting lighter treatment)

1. **I Work in Margins** — Internalize: craft 100 items at silver-or-higher mastery. Grants: +3% yield on all recipes. Trait: "Small improvements compound. I work in margins."
2. **Patience Is A Tool** — Internalize: complete 50 sessions lasting 15+ minutes. Grants: +5% forge-token generation during long sessions. Trait: "The work sets its own pace."
3. **The Recipe Remembers** — Internalize: discover 10 recipes. Grants: -1 schematic data cost on all future discoveries. Trait: "Each recipe is a conversation. Some are continuations."
4. **Craft Pride** — Internalize: achieve gold mastery on 8 recipes. Grants: S-grade probability +3% when quality variance applies. Trait: "The name on the piece is the name on the Register."

Fewer thoughts reflect the lighter narrative scope. The Fabricator's identity consolidates through mastery work, not through internalizable philosophical journeys.

---

## 6. Mastery progression arc (no chaptered campaign)

The **lighter-treatment** replacement for mining's Prospector's Road / salvage's Wrecker's Log. No chapters. Instead: seasonal events + mastery milestones + occasional correspondence.

### 6.1 Seasonal events

Three recurring events that structure time for the Fabricator. Events happen on a quarterly cadence (~90 in-game days / ~every 8-12 real hours of play).

**The Exposition** (quarterly, Collective-hosted)

A Collective-sponsored crafting showcase. Announcement notification appears ~5 in-game days before event. Active window: 3 in-game days.

- Player submits up to 3 recent crafts (crafted within prior 30 in-game days)
- At event end, judges evaluate: base grade determined by craft tier + quality variance (§9.1), modified by Exposition criteria
- Results: Standing reward per submission (1-10 based on grade), Exposition Win for top-grade submission, cosmetic Exposition Winner title
- Each Exposition has a **theme** (e.g., "Structural Elegance," "Energy Efficiency," "Material Economy") that modifies judging slightly — rewards players for matching theme with submissions

v1: 4 rotating Exposition themes. Annual cycle.

**The Commission** (offered quarterly, not all at once — commissions appear throughout the year)

A named client commissions a specific complex craft — recipe + quality + quantity with a deadline (~10 in-game days).

- Clients are named NPCs from Collective-adjacent organizations (engineering firms, ship outfitters, medical research) — 4-6 named commission clients v1
- Completion reward: CR + Fabricator Standing + flavor correspondence from the client
- Failure (missed deadline): small Standing penalty + flavor correspondence of apology / rescheduling
- Commissions have **difficulty tiers** (1-5) based on recipe complexity + quality requirement + quantity. Only offered for recipes the Fabricator has at least bronze-mastered.

v1: ~6 named clients × ~8 commission scenarios each = ~48 commissions, rotating across years.

**The Rediscovery** (seasonal, tied to specific recipes)

Once per in-game year, a Rediscovery event fires: a specific old recipe becomes available for "rediscovery work" — a multi-session mini-investigation where the player executes varied crafts to reconstruct a lost technique.

- Announced in correspondence from a Collective archaeologist-peer NPC
- Requires ~5-8 sessions of varied-recipe crafting (not grinding one recipe)
- Completion unlocks the Rediscovered recipe (v1: ~6 Rediscoverable recipes across multiple years)
- Skill voice commentary amplifies during Rediscovery sessions — Recipe Memory and Material Sense particularly active

### 6.2 Milestones (non-seasonal)

Individual mastery moments that carry weight:

- **First gold mastery on any recipe** — extended celebration, first Register masterwork entry, Material Sense skill voice comments at length
- **5 gold masteries** — Fabricator Standing tier threshold crossed; Register expands with Masterwork Registry section
- **15 gold masteries** — "Legendary Fabricator" honorific on ship; rare and earned
- **All 38 recipes at least bronze-mastered** — "Complete Fabricator" title; full Register access
- **First S-grade output** — once quality variance unlocks, the first S-grade is a milestone moment; Quality Ear skill voice comments

Milestones are **timeless** — players hit them when they hit them, no window, no expiry.

### 6.3 Correspondence system

A **lightweight mail system** providing texture without authoring burden.

Named Fabricator peers (5 v1: Collective researchers, craft-firm owners, former mentor figures) send occasional correspondence:

- Triggered by specific events: completing a commission from that peer, reaching a specific mastery milestone, Exposition submissions in a theme they specialize in
- 2-4 paragraphs, written in-character
- Read in the Fabricator's Register (§8.7)
- Accumulate as a persistent archive — players can re-read older correspondence anytime

v1: ~40 correspondence scenarios across 5 peers. Extensible.

Example: after the player completes a commission from **Adisa Lark** (a medical-research fabrication firm), correspondence arrives 3 in-game days later:

> *"The plating held up better than the specs required. Dr. Vetrin wanted me to pass that along — apparently it survived a centrifuge test they hadn't planned on running until the next quarter. She asked if you'd consider a follow-on piece for the Mendem Labs grant. Let me know. — Adisa"*

Small, specific, in-voice. The Fabricator has peers; those peers notice the work.

### 6.4 No chapter endings

Unlike mining's Prospector's Road or salvage's Wrecker's Log, refining has no "Chapter 5 complete" moment. The arc is **competence deepening without closure**. A Fabricator at year 5 is more skilled than one at year 1, but there's no final chapter that says "you are now THE Fabricator."

This is the Dwarf Fortress legendary-craftsman move made explicit: there is always another craft, another year, another mastery. The work doesn't end. That's the point.

---

## 7. Optional content tracks

Three tracks (fewer than mining's 4 or salvage's 4, reflecting lighter scope).

### 7.1 The Masterwork Registry (unlocked at Fabricator Standing tier 3)

The signature refining cosmetic track. Parallels the Collector's Wall from salvage.

When the player reaches gold mastery on a recipe **and** produces an S-grade output of that recipe, the specific output becomes a **Masterwork** — entered into the Fabricator's Register permanently.

Masterworks have:
- Specific identity (recipe + date + session + ingredients-used)
- Persistent record in the Register
- Optional **Masterwork Stamp** application: visible mark on the produced module if installed on the ship (cosmetic — doesn't alter stats, just marks provenance)
- Collective peers may reference your Masterworks in correspondence

v1: Masterwork capacity scales with Fabricator Standing (20 slots at tier 3, 50 at tier 4, 100 at tier 5). If a player exceeds capacity, they can "archive" older Masterworks — moved to read-only Register entries without cosmetic stamp slots.

### 7.2 Seasonal Archive (unlocked with Exposition access)

Persistent archive of all Exposition submissions, Commission completions, and Rediscovery events. Entries include:

- Exposition submissions: item + grade + judges' flavor comment (1-2 lines of Collective-voice feedback)
- Commission completions: client name + item + client correspondence
- Rediscovery completions: recipe + flavor-text summary of the investigation

Accessible from the Register. No mechanical function beyond reference; pure craft-pride record.

### 7.3 Collective Correspondence (unlocked Chapter... er, Fabricator Standing tier 2)

The accumulated mail archive from §6.3. Sorted by peer, searchable, re-readable.

Some correspondence triggers **quiet optional content**:
- A peer mentions a specific recipe-type they'd pay well for → spawns an extended commission
- A peer asks after a Rediscovered recipe → unlocks a dialogue option that grants bonus Fabricator Standing
- A peer's correspondence contradicts another peer's → small branching choice about which relationship to deepen

These are not quests — they're texture. Players who engage get light narrative depth; players who don't still see the correspondence.

---

## 8. Rendering changes — visual overhaul

### 8.1 Extended mastery-level-up (gold tier)

Current mastery-up is a particle burst + banner. Extend gold-tier only:

- 0.0–0.4s: existing particle burst (preserved)
- 0.4–1.2s: forge atmosphere briefly intensifies (heat escalation one tier); glow from workstation visible
- 1.2–2.0s: banner holds longer ("GOLD MASTERY — [Recipe Name]"); skill voice line surfaces in corner
- 2.0–2.5s: Fabricator's Register entry flash indicator ("Masterwork registry entry added" / "Available for Masterwork attempt")

Bronze and silver level-ups keep existing behavior.

**Cost:** ~4 days. Extension to existing `MasteryLevelUp` VFX.

### 8.2 Quality variance visualization (unlocked Fabricator Standing tier 4)

When a craft output rolls S-grade (§9.1), apply distinct VFX:

- Output icon shimmers gold for ~1s in the buffer slot
- Brief "S" letter-stamp particle (~0.8s hold)
- Quality Ear skill voice has elevated trigger rate (~15% on S-grade)
- Register entry updates if applicable

A / B / C grades get subtle distinctions (bronze, silver, default tints on output icons) without ceremony.

**Cost:** ~1 week. New VFX + quality-tier integration.

### 8.3 Visible queue animation

Current: queue exists mechanically; not heavily visualized. Upgrade:

- Queue slots render as small "workstation" icons on the forge display
- Active job icon animates (hammer, flame, or process-specific animation based on recipe type)
- Queue slots fill left-to-right as jobs are added
- Completed jobs "lift" off the queue toward the buffer with brief ore/component visual
- Empty queue slots show "waiting" state (dim)

**Cost:** ~1.5 weeks. Reuses existing forge atmosphere; adds per-slot workstation rendering.

**Benefit:** Factorio's "line is working" feel. Visible infrastructure makes automation present.

### 8.4 Seasonal event UI

Seasonal events (Exposition, Commission, Rediscovery) need UI presence:

- **Exposition:** during active window, a banner appears at top of refining view ("EXPOSITION ACTIVE — 2d 6h remaining"). Clickable → submission panel (select up to 3 recent crafts from the Register; submit)
- **Commission:** when a commission is active, banner shows client + deadline + required item. Recipe list highlights matching recipes
- **Rediscovery:** during Rediscovery event, affected recipes get special card treatment (subtle animated border); Rediscovery progress bar visible

**Cost:** ~2 weeks. Three distinct event UIs + event scheduling integration.

### 8.5 Correspondence notification

Correspondence arrives via notification: small icon appears at edge of refining view (and other relevant views — station hub, cockpit). Clicking opens the Register's Correspondence section with the new entry highlighted.

**Cost:** ~3 days. New notification element.

### 8.6 Fabricator dockside (optional — low priority)

Similar to mining's Union Hall and salvage's broker docksides. A small interactive space in Collective-system stations where:

- Visiting peer NPCs are rendered (even if silent)
- Commission board shows currently-available commissions
- Exposition status visible if event active
- Register kiosk for reviewing your craft history

Rendered in AB §8.1's `hangar_military` environment variant.

**Cost:** ~1.5 weeks. **Optional** — Fabricator identity works without a physical hall. Deferred to Phase F6 polish if bandwidth allows.

### 8.7 Fabricator's Register UI

The signature refining UI — parallels Claim Ledger and Wrecker's Log.

Sections:
- **Mastery Board** — all 38 recipes shown as cards; mastery level indicated (blank/bronze/silver/gold); progress bar for next threshold
- **Masterwork Registry** — S-grade crafts with provenance metadata, Masterwork Stamp equip option (up to 3 slots based on Fabricator Standing tier)
- **Seasonal Archive** — Exposition entries, Commission log, Rediscovery summaries
- **Correspondence** — letters from Collective peers, sortable by peer and date
- **Thought Cabinet** — 4 thoughts with progress indicators (unified implementation with mining/salvage)
- **Statistics** — total crafts, Fabricator Standing, forge-token lifetime, etc.

Styled as a **workshop notebook** — cleaner than mining's Claim Ledger (which is aged paper) and salvage's Wrecker's Log (which is battered leather). Fabricator's Register is well-kept — institutional-clean, small precise margin notes, grid lines, careful handwriting-style typography. The visible organization is itself identity.

**Cost:** ~2 weeks. New view + significant UI work.

### 8.8 Skill voice corner region

Shared implementation with mining and salvage. Same corner element, different content. Cost absorbed if built concurrently with mining §8.5 or salvage §8.9.

---

## 9. Gameplay changes forced by rendering and narrative

### 9.1 Quality variance system (unlocked Fabricator Standing tier 4)

**New mechanic.** At tier 4, craft outputs can roll quality grades: C / B / A / S. Default grade is C for tier-1 recipes, B for tier-2, A for tier-3 (baseline matches current output). Higher grades roll probabilistically, modified by mastery level and applicable skill/upgrade bonuses.

**Grade effects:**
- C-grade: standard output yield, standard market value
- B-grade: +10% yield, +5% market value, small quality bonus flavor text
- A-grade: +15% yield, +10% market value, skill voice may comment
- S-grade: +20% yield, +15% market value, Masterwork eligibility (if recipe is gold-mastered), Quality Ear skill voice triggers

**Probability ranges** (at Fabricator Standing tier 4+, gold mastery on recipe):
- C-grade: 40%
- B-grade: 35%
- A-grade: 20%
- S-grade: 5%

Below gold mastery or below tier 4, no variance applies — all crafts produce standard (C for tier 1, etc.) as today.

**Important:** quality variance is **upside-only.** Grade C is the current output — no change. B / A / S are new possibilities. Refining never penalizes the player.

### 9.2 Seasonal event progression

New scheduler system. Events trigger quarterly, with announcement + active-window + results phases.

- Quarterly cadence: ~90 in-game days (tunable)
- Announcement: 5 in-game days before active window
- Active window: 3 in-game days
- Results: immediate at end of active window; correspondence arrives 1-3 in-game days after

Events do not pause for player inaction — miss an Exposition, the next Exposition is 90 days away.

### 9.3 Commission acceptance and deadlines

Active commissions are gameplay commitments: accept one, and if the player fails to complete it within the deadline, they suffer a small Standing penalty + client-relationship damage.

Implementation: commission slots are limited (v1: max 2 active commissions at once) to prevent overcommitment. Players must triage.

### 9.4 Masterwork Stamp slot limits

Players can equip up to 3 Masterwork Stamps at once (Fabricator Standing tier 3), expandable to 5 at tier 4 and 7 at tier 5. Stamps apply visually to ship modules — they don't alter stats.

### 9.5 No other gameplay changes

Recipes, mastery, discovery, forge tokens, forge upgrades, batch queuing, buffer system — preserved.

---

## 10. Dependencies

### 10.1 On other overhaul docs

- **`20_aesthetic_bible.md`** — palette for skill voice colors (§5.2), environments (§8.6), Collective faction color overlay
- **`30_overhaul_space_combat.md` §4.4** — camera system (brief use in mastery-up extended celebration)
- **`31_overhaul_ship_builder.md` §4.1** — hangar environment system (Fabricator dockside uses this if implemented)
- **`32_overhaul_mining.md` §5.2 + §8.5** — skill voice corner region shared implementation
- **`32_overhaul_mining.md` §4** — balance discipline pattern
- **`36_overhaul_salvage.md` §8.4** — UI patterns (Register similar in structure to Wrecker's Log, different aesthetic)

### 10.2 On production systems

- **Dialogue system** — correspondence delivery, client commission offers, peer dialogue
- **Faction system** — Fabricator Standing separate from main-game faction rep; Collective-adjacent but not Collective-exclusive
- **Save system** — new state: Fabricator Standing, Exposition history, Commission log, Correspondence archive, Masterwork Registry, Rediscovery progress
- **Scheduler/event system** — quarterly event ticking; need reliable in-game-day passage tracking
- **NPC portrait pipeline** — hand-authored pixel art. ~6 portraits (5 peers + 1 mentor figure if needed)

### 10.3 On content authoring

- **Skill voices: 5 × 25 lines** = ~125 lines (~1,500 words)
- **Correspondence: 40 scenarios × ~150 words each** = ~6,000 words
- **Exposition judge flavor lines: 4 themes × ~15 lines per grade (4 grades)** = ~240 lines (~2,400 words)
- **Commission scenarios: 48 × ~200 words each** = ~9,600 words
- **Rediscovery events: 6 × ~600 words each** = ~3,600 words
- **Milestone / mastery-up flavor lines**: ~40 lines (~600 words)
- **Thought cabinet entries: 4 × ~200 words** = ~800 words

**Total: ~24,500 words.** Between mining (~17,700) and salvage (~26,600). Heavy on commission and correspondence content; lighter on chaptered narrative.

---

## 11. Phasing

Refining overhaul is moderate scope. Suggest 6 phases, parallelizable with mining and salvage overhauls.

### Phase F1 — Balance discipline + quality variance foundation (~1 week)

- Fabricator Standing system implemented
- Quality variance data model (grade storage on outputs)
- Tier progression rules

### Phase F2 — Visual overhaul baseline (~2 weeks)

- Extended gold mastery-up (§8.1)
- Visible queue animation (§8.3)
- Quality variance visualization (§8.2)
- Skill voice corner region (shared implementation)

**Parallelizable with** mining M2 and salvage S2.

### Phase F3 — Fabricator's Register + Correspondence system (~2 weeks)

- Full Register UI (§8.7)
- Correspondence delivery + archive
- Thought cabinet integration

### Phase F4 — Seasonal events (~3-4 weeks)

- Exposition event (§6.1) + submission UI (§8.4)
- Commission system + 6 named clients + initial ~24 commission scenarios
- Rediscovery system + first 3 rediscoverable recipes
- Event scheduler integration

### Phase F5 — Skill voices + Masterwork Registry (~2 weeks)

- 5 skill voices implemented (~125 lines authored)
- Masterwork Registry activation
- Masterwork Stamps on ship modules
- S-grade reward integration

### Phase F6 — Fabricator dockside (optional) + polish (~2 weeks)

- Fabricator dockside environment (§8.6) — *optional*
- Additional commissions (scale to ~48 total)
- Additional correspondence (scale to ~40 total)
- Additional Rediscovery recipes (scale to 6 total)
- Polish pass

### Total estimate: ~10-13 weeks for F1-F5 (F6 optional +2 weeks)

Significantly shorter than mining or salvage. Reflects the lighter scope deliberately.

---

## 12. Success criteria

Refining redesign is done when:

1. **Fabricator identity is real.** A player at Fabricator Standing tier 4+ has a distinct voice and a relationship with at least one Collective peer.
2. **Seasonal rhythm lands.** Players look forward to Expositions. Commission deadlines create micro-goals.
3. **Quality variance feels earned.** Reaching gold mastery + Standing tier 4 enables S-grades that players remember.
4. **Masterwork Registry is a point of pride.** Players screenshot their Register, share their best Masterworks.
5. **Craft satisfaction preserved and enhanced.** Current mastery-tier celebration feel is not diminished; gold extension adds weight without slowing the rhythm.
6. **Balance discipline holds.** Master Fabricator yields fall between mining and salvage, reflecting lower risk.
7. **Seasonal events drive return.** Players return to refining for Expositions even if main gameplay doesn't require it.
8. **Parallel identity complete.** Prospector, Salvager, Fabricator form a deliberate triad. A player who inhabits all three experiences Aurelia's three cultural registers through work.
9. **Lighter treatment respected.** Refining doesn't demand the time investment of mining or salvage. It rewards patient return without requiring campaign-scale engagement.
10. **Performance.** Refining view holds 60 FPS with forge atmosphere active + up to 5-job queue + active VFX.

---

## 13. Open questions

1. **Quarterly event cadence — is 90 in-game days right?** Might be too frequent (flooding players with events) or too rare (players forget Exposition exists). Calibrate in F4 playtesting.
2. **Quality variance probability curves.** v1 values are proposals. Test against "feels rewarding without being trivial."
3. **Masterwork Stamp visual treatment.** How does a stamp appear on a ship module? Small cornertuck icon? Full border treatment? Coordinate with ship builder Tier 2 doc (§8.9 material application).
4. **Fabricator dockside priority.** F6 is optional. If bandwidth tight, can refining ship without dedicated dockside? v1 proposal: yes — correspondence + Register carry identity without physical location.
5. **Cross-pollination with mining and salvage.** A Fabricator crafts from materials provided by a Prospector / Salvager. Correspondence could acknowledge where ingredients came from ("This batch of alloy has the deep-seam signature — nice work whoever sent it"). Low authoring cost, strong identity texture. Flagged for coordination.
6. **Recipe discovery events as Rediscovery fodder.** Currently rediscovery is one-off events. Could become regularly-scheduled events tied to specific recipe clusters. Defer to F6+.

---

## 14. Out of scope

- **Fabricator-ship specialization** — dedicated ship class deferred
- **Multiplayer craft cooperation** — not in scope
- **Full voice acting** — Tier 3 audio concern
- **Procedurally-generated commissions** — v1 commissions are authored
- **Factory-builder / spatial refining** — not the target aesthetic
- **Skill-tree rework for refining** — existing skills remain; no rebalancing as part of this overhaul
- **Cross-mini-game integration beyond correspondence flavor** — flagged, not scoped

---

*Mini-game identity set complete. The three docs (`32_overhaul_mining.md`, `36_overhaul_salvage.md`, `37_overhaul_refining.md`) form a deliberate identity triad mapping to Aurelia's three cultural registers:*

- *Prospector — Miners Union solidarity, hopeful labor, Appalachian / Wyoming resonance*
- *Salvager — Frontier Alliance haunted archaeology, moral-grey mercantile, Newfoundland shipwreck resonance*  
- *Fabricator — Science Collective precision craft, institutional mastery, postwar Japanese swordsmith / Bauhaus / Bell Labs resonance*

*Each identity is independently playable. A player who inhabits all three has walked Aurelia's cultural geography through work. Each identity contributes to the main economy at tuned rates; none obsoletes the others.*

*Remaining Tier 2 docs (`33_overhaul_galaxy_map.md`, `34_overhaul_trading.md`, `35_overhaul_station_hub.md`, `38_overhaul_ground_exploration.md`) return to visual-overhaul-only scope per master plan §5 — those systems already have narrative identity through existing game content.*
