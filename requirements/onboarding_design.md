# Onboarding Design — Aurelia: A Ledger of Stars

**Status**: scoping draft, 2026-04-22. Not a polished spec — this is the pass *before* the sprints.

**Context**: playtester feedback (PT-008, PT-010, PT-011, PT-013, PT-014, PT-015) revealed that the first two hours teach mechanics without teaching the game. The tutorial hand-holds through ship assembly, then the player is set free into a galaxy they've not been introduced to. Direction from user: significantly more guidance, verbally, preserving the feel of the world. This doc scopes how.

---

## Six principles

1. **Prefer character over UI overlays, but player experience wins.** Narrative vehicles are the default. When a narrative vehicle can't carry a teaching load — or would carry it so poorly that the player is left confused — we break the fourth wall deliberately. UI overlays, explicit tips, and quest markers are permitted; they are not first resorts. The discipline is: when we use an overlay, we use it *because we chose to*, not because we got lazy.
2. **One NPC owns one cluster.** The Mechanic owns ship assembly. A Dockmaster owns first-run guidance. Each teacher fades after they've taught. They're fixtures of the world, not permanent companions.
3. **Progressive disclosure.** A system is introduced when the player needs it, not before. Faction politics isn't explained at hour 0 because it doesn't matter at hour 0.
4. **Transparency where the world can't narrate.** Skill check thresholds, faction standing deltas, cargo mass — the world wouldn't narrate these in dialogue. For these, we surface the hidden state through cockpit HUD / floating feedback / journal. This is the explicit-teaching counterpart to the diegetic NPC work.
5. **Soft break into autonomy.** Teachers retire gradually. No "tutorial complete" banner. The training wheels just stop appearing.
6. **Voice-check everything.** Every new line passes through the Writing Bible. No em-dashes, no "couldn't help but," no AI tells, no corporate register. New NPCs get voice sheets. Out-of-world UI copy (overlay text, tip banners, objective prompts) also gets voice-checked — not for in-character voice, but for tone: terse, direct, no corporate register.

---

## When UI overlays are appropriate

To make principle 1 operational, four categories of UI overlay are on the table. Each has a justification and a style guideline.

### (a) First-time system tips
When the player encounters a system for the first time and no NPC is positioned to explain it — e.g., first time opening the skill tree, first time loading the mission log, first time entering a refining bay — a one-time modal or slide-in panel explains the system in 1-3 sentences. Dismissible. Never re-fires for that system.

**Style**: short, declarative, no flavor text. "This is where you track active contracts. Completed ones move to History." Not in-world voice, not corporate voice — just clean. Dismiss button reads "Got it."

### (b) Contextual hint banners
Inline, non-modal hints at the top or bottom of a view when the player is idle or appears stuck. "Tip: Press R to rotate a module before placing it." Fire on state conditions (player hovering the grid for >5s without placing anything) and suppress once the action happens.

**Style**: single sentence. No decoration. Fade after action or after ~6 seconds.

### (c) Objective / waypoint markers
Explicit markers on the galaxy map, cockpit HUD, and station maps pointing at the current objective. These exist to ensure "I don't know where to go" never happens in the first two hours. Always on during early game, retire by the soft-break logic.

**Style**: icon + single-line label. "Deliver to Concordia (2 jumps)."

### (d) Diegetic overlays (UI that looks in-world)
Where possible, we dress an overlay as a terminal readout, a comm message, or a station PA announcement. This is the fallback for places where a human-to-human dialogue would be awkward but the information is mission-critical. An arrival "Welcome to Port Kestrel — please proceed to the concourse" announcement is both an overlay AND an in-world sound. Use this pattern when it fits naturally; don't force it.

**Style**: fonts, frames, and colors already established in the aesthetic bible. Text reads as if the station wrote it.

---

## What we're NOT doing

Even with the overlay allowance, some patterns stay off the table because they damage the experience we're trying to build:

- **Popup quizzes** ("Which of these is a cargo module?"). Infantilizing.
- **Persistent tutorial sidebar**. Clutters the screen in every view forever.
- **Forced repeat tutorials** on return visits. Once the player dismisses a tip, it stays dismissed.
- **Corporate tutorial voice** in UI overlay copy ("Welcome to our game! Let's get you started!"). Even out-of-world, we keep the register terse.
- **Blocking modals** that the player can't proceed around without engaging. If a tip matters that much, put it in a character's mouth.

---

## What the player knows, and when

### After hour 0 (shop → builder → drydock → galaxy arrival)
Already shipped via tutorial + PT-007.
- Ship assembly, grid placement, rotation, confirm flow
- The galaxy is where you live now

### After hour 1 — *the scope of this doc*
- Paying work originates from **people**, not menus. Menus are ledgers; NPCs are sources.
- A safe first run exists, someone points at it explicitly ("Go to Concordia. You'll be fine.")
- Travel costs fuel / time / attention — not a free warp.
- You can come back to any station. Nothing is one-shot unless it says so.
- Skills and faction standing exist as visible state; their consequences come later.

### After hour 2 — out of scope here
Covered by mid-campaign beats and the campaign itself. Listed for completeness:
- Factions have reputations; reputations compound
- Skills benefit from direction; dabbling costs you
- Some choices are final; others aren't
- The Ledger campaign exists and you're inside it

---

## Teaching NPCs roster

### The Mechanic (existing)
- **Location**: tutorial shop + drydock
- **Teaches**: ship assembly, grid placement, rotation, confirm flow
- **Voice**: terse-impatient, working-class, no sentiment
- **Retires**: after the tutorial build confirm. Re-entering the drydock post-tutorial shows her at a distance; she's not re-teaching.

### Arna (new — Dockmaster, primary ask for this doc)
- **Name**: Arna. Single-name handle; no title-surname construction. Short, unadorned, fits the Expanse's working register.
- **Location**: starting station's main concourse. Intercepts the player on first galaxy arrival, not opt-in. Stands between the airlock and the rest of the station, working a manifest terminal.
- **Teaches**:
  - Jobs come from people. The Station Board is a ledger; the courier, the dispatcher, the scholar in the back booth — they're the sources. Go talk to them.
  - The safe first run: a specific delivery or haul, named destination, rough payoff. Not "go explore."
  - Coming back is expected. Stations let you dock free. Fuel is the only running cost that matters at this stage.
  - Where the cantina is, where the shipyard is, where the exit is. One sentence each.
- **Voice**: terse-observant. Low-affect. Seen thousands of greenhorns cycle through, not mean about it, not warm either. Doesn't repeat herself. "Kid. Listen once."
- **Retires**: after Mission 1 completes. On return, short neutral greeting; no path advice. By Mission 3, indistinguishable from a station NPC — the player notices she stopped teaching without being told.

### Secondary teacher slot — TBD
Bartender concept rejected. User asked for alternatives with stronger narrative feel. See **§Secondary teacher candidates** below. This slot is flagged as TBD; a decision locks before PT-H scopes.

---

## Secondary teacher candidates

Three proposals, ranked. Aurelia's narrative register favors grounded roles — people doing something when you arrive. Not lounging, not waiting. The bartender rejection reads as: too tropey, too passive, too "quest hub." Aurelia isn't a quest hub game; it's a working galaxy.

### (1) The Cargo Broker — **recommended**
- **Who**: runs freight manifests for the station's import/export flow. Sits at a terminal tracking shipments when the player approaches. Annoyed by anyone who isn't cargo.
- **Teaches**: commercial intel. Which routes pay, what's hot this week, what's grey vs. outright illegal. The market view becomes interpretable because someone who sees the flow daily tells you what's worth noticing.
- **Voice**: transactional. Short sentences. Treats the player as a potential hauler, not a friend. "You moving or asking? Moving, I care. Asking, make it quick."
- **Fit**: direct replacement for what the bartender was going to do — commercial teaching — but with a role that matches the game's working-galaxy tone instead of a tropey tavern keeper.
- **Location**: cargo office at the starting station, adjacent to the trade terminal. Natural waypoint if Arna points the player at "talk to the broker."

### (2) The Archivist
- **Who**: former spacer, now too old to fly, parked at a terminal in an administrative office. Paid by someone (station? faction? independent?) to track records, movements, rumors. Trades context for favors or credits.
- **Teaches**: narrative context. Faction shifts, who's connected to whom, what a name means when you hear it. Doesn't teach tactics or trade — teaches *why the world is the way it is*.
- **Voice**: measured, watchful, underplayed. Remembers everything. "That name? Means something in the Concord Belt. Not here. Yet."
- **Fit**: thematically resonant with "A Ledger of Stars" — an archivist who keeps ledgers is on-title. But this character's role overlaps with later-campaign information brokers, so introducing them at hour 1 risks showing too much of the narrative hand. Better as a mid-game gate than an onboarding teacher.
- **Location**: administrative wing, secondary station concourse.

### (3) The Station Medic
- **Who**: runs the dock clinic. Patches up spacers who came back worse than they left. Has a bad view of faction space and will say so.
- **Teaches**: combat reality. What hostile space looks like, which systems send people home in pieces, what a shield rating actually buys you.
- **Voice**: direct, unromantic, blood-on-the-gloves. "You going out past the Fringe? Fine. Just don't come back looking like my last three patients."
- **Fit**: fills a combat-intro slot that's currently empty in the onboarding roster. Strong register, very Aurelia-tone. But combat teaching may be premature at hour 1 if the player hasn't encountered combat yet.
- **Location**: dock clinic.

**Recommendation**: **Cargo Broker** for this arc. Fills the slot the bartender was meant to fill (commercial intel) with a role that matches the game's working-galaxy register. Archivist and Medic become candidates for later arcs — Archivist paired with campaign progression, Medic introduced before the first combat encounter.

---

## System transparency hooks

Things the game knows that the player doesn't see. Each is one line of HUD/feedback + the plumbing to source the data. None require model changes.

| System | Current | Proposed |
|---|---|---|
| Skill check threshold + result | Silent pass/fail | Brief on-screen readout: "CHARISMA 14 vs DIFF 12 — PASS" (fades in ~2s) |
| Faction standing delta | Silent | Floating feedback: "Union: -5" at the moment it shifts |
| Cargo mass % | Shown in shipyard only | Add to cockpit HUD. Green under threshold, red over. |
| Fuel cost per jump | Visible at jump time | Show estimate on galaxy map hover, before commit |
| Current objective | In journal | Promote to cockpit HUD as a one-line "current objective". Auto-retires after Mission 3. |

Shippable together as a single pass (PT-K). Staggering is possible but adds sprint overhead without reducing risk.

---

## Post-tutorial soft break

How the game signals "you're flying solo now" without saying it.

- After Mission 1: Dockmaster's dialogue shortens. No more path advice, just a neutral acknowledgement.
- After Mission 3: cockpit "current objective" line goes silent unless a mission explicitly sets one.
- No banner, no achievement, no visible state flip. The player just notices the training wheels stopped appearing.
- Journal entries remain as a reference but become less prescriptive.

---

## Sprints that fall out of this doc

- **PT-H — "Arrival"**: Dockmaster NPC + first-station arrival dialogue + journal entry + cockpit "current objective" line + galaxy-map objective marker (the HUD hooks only; retirement logic is PT-L). Subsumes PT-015.
- **PT-I — "Second conversation"**: PT-010/11 security desk flow. Come-back-later branch, decision-lock post-choice, narrative pre-weight.
- **PT-J — "Where missions start"**: PT-013 mission-initiator gating. Auxiliary menus hide missions until the initiating NPC has been encountered.
- **PT-K — "System transparency"**: the five hooks from the table above. Shippable as one pass.
- **PT-M — "Training wheels" (new)**: first-time system tip infrastructure (category a above), contextual hint banners (category b), dismissible and state-tracked. Likely touches every major view (skill tree, mission log, refining, trading, combat's first encounter).
- **PT-L — "Soft break"**: Dockmaster dialogue recede + cockpit objective line auto-retire. Small, isolated so retirement logic doesn't get rushed into PT-H.

**Hygiene sprints run in parallel, independent of the design arc:**
- **PT-E**: PT-008 part descriptions + PT-012 rename button + Enter-key repro
- **PT-F**: PT-009 RESIZABLE window

**Sequencing recommendation:**
1. PT-H first — it's the anchor. Dockmaster existing changes the texture of the starting station.
2. PT-J next — missions make sense in the new framing once PT-H has landed.
3. PT-I after — security desk flow depends on the decision-locking pattern, which PT-J's flag-gating work establishes groundwork for.
4. PT-K any time — independent of the narrative arc, hooks in cleanly.
5. PT-M next — first-time tip infrastructure can land before or after PT-K. Picks up any teaching beats we find aren't being carried by NPCs.
6. PT-L last — retirement logic only meaningful once there's something to retire.

Parallel: PT-E and PT-F can ship any time.

---

## Decisions locked (2026-04-22)

1. **Dockmaster name**: **Arna**. Single-name handle, no title-surname construction.
2. **Bartender**: out. Rejected as tropey and too passive for Aurelia's working-galaxy tone.
3. **Secondary teacher**: TBD — proposing Cargo Broker (recommended), Archivist, or Medic. User picks.
4. **Cockpit "current objective" line**: opt-in toggle in settings, **default on**. Player can switch it off once they don't need it.
5. **System transparency hooks**: all five together in PT-K. Can be broken into implementation sub-cycles if scope balloons.
6. **Mission 1 content**: author a new mission for this arc, tuned to Arna's introduction. Not repurposed from existing content.

---

## What this doc is not

- Not a full spec. Each sprint will get its own short design note before implementation.
- Not a content authoring pass. NPC dialogues, mission beats, and voice sheets are downstream.
- Not a commitment to scope. If the design of any one sprint reveals bigger structural problems, we pause and re-scope.

The ambition is coherence: a first two hours where every beat teaches something, every NPC has a reason to be there, and the player never feels the training wheels are hand-holding them because the hand-holding reads as the world doing what worlds do.
