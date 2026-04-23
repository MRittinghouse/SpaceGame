# Arna — Early-Game Mini-Campaign Roadmap

**Status**: Design locked, implementation not yet scoped into sprints.
**Last updated**: 2026-04-23.
**Companion docs**: `onboarding_design.md`, `playtest_roadmap.md`.

---

## Vision

Arna is a **temporary bridge character** — a street-rat Dockmaster on Nexus Prime who takes the post-tutorial player under her wing for a multi-mission scheme that introduces every major non-ground gameplay system in the game while telling a grounded, darkly funny story about the Aurelia Expanse.

She is not a companion. She does not become crew. Her arc has a firm beginning and a firm end. She either walks away smaller than she started, dies in a way the universe barely registers, or gets sold out by the player she trusted. In every ending, she exits the stage. The player carries her lessons — mechanical and narrative — forward into the main campaign.

**Dual purpose:**
- **Mechanical**: teach trading, mining, refining, combat, salvage, and smuggling via mission-embedded tutorials. Player finishes the arc with hands-on experience in every early-game loop.
- **Narrative**: anchor the tone of the world. The Expanse grinds people like Arna under without noticing. Small-time schemes are the default. Information is asymmetric and usually wrong. Family is a reason to take risks that don't pay. Dark humor throughout, because that's how people survive here.

**Player slant**: the player is also an orphan, also scrapyard-grade, also starting with nothing. Arna is a mirror one step ahead — further into a pattern that does not work long-term. The player can choose to follow her down, walk away, or cash her in.

---

## Character

**Arna, Dockmaster of Nexus Central Exchange.**

Late 20s. Small, wiry, quick. Dark hair shaved on the sides. Utility vest covered in patch repairs. Fingerless gloves with old cargo scars. Permanent UV squint. Voice raw from recycled air. Silver pendant she never explains consistently.

**Origin**: Orphan of the Nexus port district. Never left the Expanse. Has seen every station via the manifest terminal, has never docked at one.

**Day job**: manifest clerk. Keeps her off the dock collector's list.

**Real income**: small-time schemes, favors, off-books courier runs, fenced parts.

**Core trait**: tactically clever, strategically blind. Reads a room in seconds, reads a trend in years and gets it wrong. When she's bluffing, she gets more specific and more confident, not less. The player's tell on her is that the details get thicker when the ground gets thinner. They'll notice it twice across her arc: once as a joke, once as a warning they wish they'd taken.

**Voice register**:
- Fast, clipped, observational.
- Station slang: "dock-rate" (bad deal), "clean paper" (legal manifest), "ghost ledger" (off-books account), "salt-out" (walk away broke), "manifest-blind" (doesn't know what they're loading).
- Creative station swears.
- Addresses the player as "kid" for Missions 1-2. Drops it starting Mission 3 once she's decided they're a peer.
- Dark humor as default register. "Half the Expanse is running schemes. The other half is running from them. We're splitting the difference."

**Hidden backstory (revealed across arc)**:
- Cousin who "went straight" — actually a Crimson Reach informant. Revealed M4.
- Former engagement she won't discuss. Doesn't appear directly.
- Younger brother on a Union station, lungs failing from processed air. The REAL reason she needs the money. Revealed late M4.
- Silver pendant: three conflicting stories told across the arc. Real answer (was her mother's, nothing to do with the brother) surfaces only in Branch A's closeout journal entry.

**What makes her compelling to the player**:
- She sees them clearly: "Scrapyard kid. Your dad's gone. You built that rig from parts nobody else wanted." Doesn't pity, treats it as credentials.
- She has a plan. The player came in with none.
- She's funny, and the player hasn't had much reason to laugh.
- She offers something the player lacks: familiarity with this world.

---

## The Scheme

Arna has spent a year on the outline of a vertically-integrated small-score operation:

1. **Mine** rare-earth ore at a marginal site she "knows about" — low enforcement, minimal presence.
2. **Refine** it at her friend Tev's off-books facility for cheap processing.
3. **Sell** the refined product to a buyer she has lined up, who'll pay premium because the supply is untraceable.

The payout — in her projection — is enough to move her brother off-station to better air.

**Four fatal flaws she doesn't fully see:**

1. **The ore site is marginal because it's partially depleted.** Her "tip" is public knowledge among miners who tried it and left. She'll blame the yield on "edge seams."
2. **Tev has been skimming her for years.** She trusts him because he's personally kind to her. That's it.
3. **Her buyer is her cousin Keren.** Keren "went straight" by becoming a low-ranking Crimson Reach informant. The deal is a trap he set to buy back goodwill after a prior failure.
4. **Rare-earth trafficking is exactly what larger factions care about.** Stepping up from small-time courier to rare-earth smuggler moves her from "ignored" to "tracked." She doesn't understand that shift until it's on top of her.

The player, if attentive (and appropriately skill-checked), can see cracks starting in Mission 2 and widening through Mission 4.

---

## Mission Arc — Six Canonical Missions

| # | Title | Teaches | Narrative beat |
|---|---|---|---|
| 1 | Coolant Run | Trading, NPC-initiated missions, galaxy travel | Trust beat. Passes her test. |
| 2 | The Ore Tip | Mining, danger navigation, ore extraction | First crack. Yield underperforms. |
| 3 | Refinement | Refining mini-game, commodity chains | Second crack. Tev skims. |
| 4 | The Buyer | Combat, ambush mechanics, smuggling primer | Blown plan. Cousin reveal. Smuggling reveal. |
| 5 | Branching | Salvage (A/B), smuggling run (A), faction rep (C) | Player choice drives climax. |
| 6 | Last Freight Out | Journal consequences, reputation shift | Arna exits the stage. |

### Mission 1: Coolant Run (existing, shipped in PT-H)

Already built. After delivery to Verdant and return to Nexus, Arna now leans in for the pitch:

> "That was the test. I needed to know you don't chicken out on a clean run. Got something real next, if you're in. Meet me here tomorrow. Bring your ship. Leave your conscience at the door. I'm joking. Mostly."

Sets flag `arna_pitched_scheme`, which unlocks Mission 2 as available.

### Mission 2: The Ore Tip

**Setup**: Arna has coordinates to a "marginal" site in the outer belt of Breakstone. She claims the enforcement presence is minimal because the site is barely on the maps. She needs the player to haul out, run their mining rig, and return with raw ore.

**Mechanical beat**: Mining tutorial. First time the player engages with mining mechanic. Scoped to a single session, moderate danger system, yield tuned to the mission's expectations (not the over-optimistic projection).

**Narrative cracks**:
- The site is partially depleted. The yield is ~60% of what Arna projected.
- A Perception skill check (gated on any non-zero investment) reveals "this site was worked recently." Players who pass get a journal hint.
- A Persuasion check gets Arna to admit the tip came from a rival miner who abandoned the site. She plays it off: "They didn't have my refining angle."

**Completion**: player returns with raw ore. Arna is elated, doesn't dwell on yield shortfall. Sets flags `arna_ore_delivered`, `taught_mining`.

**Reward**: modest credits + XP. Raw ore kept for Mission 3.

### Mission 3: Refinement

**Setup**: Arna sends the player to Tev's off-books refining facility in Forgeworks' industrial district. "Tell him Arna sent you. He'll take care of us."

**Mechanical beat**: Refining mini-game tutorial. Player runs the crucible/process on Arna's behalf, watching Tev's interface deduct fees step by step.

**Narrative cracks**:
- Fee structure: calibration 3%, tolerance 7%, processing 12%, storage 4%, transfer 2%. Final refined volume is ~40% of what raw ore should yield.
- Arna does the math on return and never arrives at a final number. Just says: "Not ideal. But fixable."
- Skill check options: confront Tev (Intimidation/Persuasion), weigh independently before and after (Perception/Engineering), accept the numbers (no check).
- Branching dialogue: if the player raises the issue with Arna, she defends Tev vocally. Player can push or back off.

**Completion**: player returns with refined product. Sets flags `arna_refining_complete`, `taught_refining`. Persuasion-path players may also set `knows_tev_skims` (journal entry, matters in epilogue).

**Reward**: refined commodity held for Mission 4, no cash reward yet.

### Mission 4: The Buyer

**Setup**: Arna has the buyer meeting set. Remote derelict station in a marginal system (working title: **Heron's Mark**, a derelict orbital in a moderate-danger system adjacent to Breakstone). She insists on coming along in person. Transports herself + cargo on the player's ship.

**Mechanical beat**: The meet. Three Crimson Reach operators in the docking bay. They want the cargo without paying and Arna as a bounty for a prior issue. Combat encounter — tutorial-tier enemies tuned for a shakedown-grade ship. Teaches combat basics, ambush recovery, action economy.

**Narrative reveal**: the "buyer" is Keren, Arna's cousin. He's now Crimson Reach adjacent. He set the meeting up to buy goodwill after a prior failure. He mispronounces Arna's name — calls her "Ernie." Arna is briefly more furious about the name than the ambush. Combat starts.

**Post-combat beat** (cutscene or dialogue): Arna takes a non-fatal hit, survives. Keren escapes (important — he recurs if Branch A is chosen). Arna comes clean:

> "Everything we've been doing — it's not clean. The ore's restricted. The refining was off-books. The sale was black market. I told myself it was small enough not to matter. It wasn't. My brother's on a Union station, and his lungs are giving out, and I've been running this scheme for a year because it's the only shot at the kind of money that moves him somewhere that won't kill him. That's it. That's all of it."

**Smuggling primer** (in-dialogue): Arna teaches the player:
- Legality tiers: LEGAL, RESTRICTED, ILLEGAL
- Inspection mechanics per system (some factions enforce, others don't)
- Penalty escalation (WARN → FINE → CONFISCATE → BAN)
- Heat accumulation and decay
- Smuggling compartments (available at shipyard, conceals contraband from inspections)
- Black market access (gated per station)

This information is delivered via dialogue plus a companion journal entry titled "What Arna Told Me About Running Hot." The entry is the permanent reference the player can consult.

**Flags set**: `arna_scheme_revealed`, `taught_combat`, `smuggling_primer_received`. Sub-flag `keren_escaped` drives Branch A.

### Mission 5: Branching Climax

Player chooses path. Three branches, each a full mission, teaching a different capstone set.

#### Branch A — "Last Freight Out" (Payback + Smuggling)

**Setup**: Arna has Keren's home coordinates — a cached supply depot where he stores personal contraband. She wants payback and to recover value lost. The play: hit the depot, take what's there, route back through a customs system with a smuggling compartment installed.

**Mechanical beat (first half)**: install smuggling compartment at Nexus shipyard (tutorial for the install). Fly to the depot, engage Keren's remaining muscle in combat (second combat encounter, harder), clear the station.

**Mechanical beat (second half)**: salvage the depot (teaches salvage mini-game). Route back through a Commerce Guild customs system (they enforce restricted cargo). Smuggling compartment keeps the contraband hidden. Player learns:
- How to install the compartment
- What inspection looks like in practice (customs event triggers)
- How the compartment affects the inspection roll
- Black market sale at Nexus on return (first time accessing black market UI)

**Narrative beats**:
- Keren is present at the depot. Final combat confrontation. Player can spare him (he disappears off-map) or kill him (hunted flag sets).
- Arna is more reflective. Talks about her brother. Shows the pendant unprompted and tells the third wrong story.
- Post-salvage, she's quiet. The adrenaline has broken down to tiredness.

**Completion**: substantial credits + rare-earth contraband sold on black market. Flags `arna_branch_a_complete`, `taught_salvage`, `taught_smuggling`.

#### Branch B — "The Clean Pull" (Walk Away)

**Setup**: Arna concedes the loss. Proposes one last "clean" salvage job on a derelict she's had coordinates for, untouched, no faction involvement. Lower risk, lower payout, but no entanglement.

**Mechanical beat**: salvage mini-game tutorial with no combat. Player flies solo (Arna stays behind — "I'm not getting on another ship this week"). Salvages the derelict thoroughly, returns to Nexus.

**Narrative beats**:
- Quiet mission. Arna has time to reflect via comm messages.
- She admits over comms that she's never left the Expanse in her life, that she made the same scheme work three times smaller over the years.
- This was her shot at the big one. It didn't land. She's going back to the manifest desk.

**Completion**: modest credits + salvaged parts. Flags `arna_branch_b_complete`, `taught_salvage`.

#### Branch C — "Clean Paper" (Betrayal)

**Setup**: Player can, at M5 start, choose to turn Arna in. Two sub-options:
- Report her to Nexus Security (Officer Larsen — existing NPC). Legal bounty, Commerce Guild rep boost.
- Sell her to Crimson Reach (contact via Keren's channels). Black-market bounty, Crimson Reach rep boost.

**Mechanical beat**: no tutorial in the traditional sense, but player experiences:
- Faction reputation shift mechanics (visible via PT-K's faction delta notifications)
- Journal entries that encode moral consequence
- Changed dialogue states across multiple NPCs

**Narrative beats**:
- Arna is caught unprepared. She trusted the player.
- Security/Reach arrest scene is brief, mundane, dark.
- Rhea, if the player sees her later, will know and say something cold but not dramatic.
- Odom at the cantina will say one line: *"Heard about your friend. She owed me seventy credits."* Walks off.

**Completion**: lump bounty. Flags `arna_branch_c_complete`, `arna_betrayed`. No gameplay-system teaching in this branch — the lesson is moral.

### Mission 6: Last Freight Out (branch-dependent closeout)

Three variants, all short, delivered as final scene + journal entry.

**Branch A variant** — Arna is packed. Two blacklists now. She's taking a freighter out of Nexus tonight, heading to Port Kestrel, probably further. Player can give her credits, a part, or a terse goodbye. Her last line to the player:

> "Tell Rhea I still owe her for that coolant. Actually don't. She doesn't need to know I'm gone."

Journal entry reveals the silver pendant was her mother's. None of her three stories were true. The reveal is written matter-of-factly — no sentimentality.

**Branch B variant** — Scene at the cantina. She's quiet. Thanks the player in a way she hasn't before. Confirms she's not leaving the desk. If the player offers her a crew slot, she declines kindly: "Nexus is the only home I've got. Can't leave it. Can't tell you why. Don't ask."

Warm but final. Journal entry brief: "Arna stayed."

**Branch C variant** — No scene with Arna. Delayed journal entry:

> "Dockmaster Arna was taken into custody three days after I reported her. The docket said rare-earth trafficking and conspiracy. I saw the list of charges once. I don't need to see it again. Odom told me she owed him seventy credits. He wasn't joking. The docks kept running."

Faction rep shift fires from the report (not the arrest). PT-K's notification queue surfaces the delta.

---

## Smuggling Integration

**What the arc permanently unlocks** (regardless of branch, after M4 primer):
- `smuggling_primer_received` flag — gates access to:
  - Smuggling compartment installation option at any shipyard
  - Black market tab visibility at stations that have one
  - Ability to accept smuggling contracts at cantinas
  - Journal entry reference "What Arna Told Me About Running Hot"

**What Branch A adds**:
- `taught_smuggling` flag — the player has actually DONE a smuggling run
- A stash of recovered contraband sold on black market (first-time UI exposure)
- First-hand experience with customs inspection event

**What Branches B and C don't add** — the player has the knowledge but no practical experience. They can experiment on their own.

**Narrative justification for the unlock**: even players who walk away clean or turn Arna in have heard her primer. That information doesn't un-hear. The game gives the mechanics; the player decides whether to use them.

---

## Site Assignments (existing systems, not new content)

Every location in Arna's arc uses an existing galaxy system. Reinforces the player's mental map.

| Mission | Location | Why |
|---|---|---|
| M1 Coolant Run | Nexus Prime → Verdant | Existing, shipped |
| M2 Ore Tip | Breakstone (moderate danger, mining hub) | Real mining content, tuned difficulty |
| M3 Refinement | Forgeworks (industrial, refining-appropriate) | Real industrial setting |
| M4 The Buyer | Heron's Mark (working name — derelict in outer Breakstone space OR reuse Iron Depths) | Need to confirm a suitable remote-station location exists or assign one |
| M5A Payback | Keren's depot — system TBD, probably Iron Depths or Fringe-adjacent | Dangerous, faction-adjacent |
| M5B Clean Pull | Havens Rest or similar safe frontier system | Low-danger salvage |
| M5C Betrayal | Nexus Prime (report at security) or contact-via-signal (no travel) | Domestic |
| M6 Closeout | Nexus Prime | Final beat, home territory |

**Decision needed**: does the game currently have a derelict station location available, or do we author one for M4? Worst case: reuse an existing system and describe the meeting location in dialogue flavor.

---

## NPCs to Author

| NPC | Location | Role | Dialogue scope |
|---|---|---|---|
| Tev | Forgeworks refining facility | Arna's refining "friend" — sketchy, sympathetic, skimming her | 1 tree, 2-3 nodes, sub-branches on player suspicion level |
| Keren | Heron's Mark (M4), his depot (M5A) | Cousin, Crimson Reach informant, antagonist | 2 trees (M4 ambush / M5A confrontation), moderate scope |
| Reach operator ×2-3 | M4 ambush, M5A fight | Combat enemies | Enemy definitions, not dialogue |
| Security officer (Larsen — existing) | Nexus (M5C variant) | Arrest contact | 1 new branch on Larsen's dialogue |

**Arna** already authored. **Rhea** already authored. No new allies needed.

---

## Data Files Required

### New missions
- `arna_02_ore_tip` (new)
- `arna_03_refinement` (new)
- `arna_04_the_buyer` (new)
- `arna_05a_last_freight_out` (new)
- `arna_05b_clean_pull` (new)
- `arna_05c_clean_paper` (new — or handled as dialogue-driven without a mission entry)
- `arna_06_closeout_a`, `arna_06_closeout_b`, `arna_06_closeout_c` (3 closeout variants, can be journal entries rather than missions)

### New dialogues
- `arna_post_coolant_pitch` (after M1, pitches M2)
- `arna_ore_return`, `arna_refinement_discussion`, `arna_the_buyer_ambush`, `arna_primer_full`
- `tev_refining_intro`, `tev_refining_defensive`
- `keren_meet`, `keren_depot_confront`
- Extended arna_post_completion / arna_retired trees with branch-aware variants

### New commodities (if needed)
- Rare-earth ore (restricted): investigate `rare_metals` — may already fit
- Refined rare-earth: new commodity, restricted or illegal

### Reused parts
- `smuggling_compartment_sable` — already exists, triggered by tutorial hook

### Reused encounter templates
- Tutorial combat tuned for first-time players
- Customs inspection event (existing)

### Journal entries
- "The Ore Tip" — M2 discovery
- "Tev's Math" — M3 cracks
- "What Arna Told Me About Running Hot" — M4 primer
- "Last Freight Out" — M6A
- "Arna Stayed" — M6B
- "The Docket" — M6C

---

## Sprint Phases

The full arc is too big for one sprint. Proposed breakdown:

### Phase AR-1 — Foundation and Ore Tip
- M1 post-pitch dialogue (short extension to existing Arna dialogue)
- M2 mission + Tev NPC stub + mining-site configuration
- Journal entry authoring
- Tests

### Phase AR-2 — Refinement
- M3 mission
- Full Tev dialogue tree with branching
- Refining tutorial scoping
- Journal entries
- Tests

### Phase AR-3 — The Buyer and Smuggling Primer
- M4 mission with ambush encounter
- Keren NPC and dialogue
- Reach operator combat templates (tutorial-grade)
- Smuggling primer dialogue + journal entry
- Permanent smuggling-mechanic unlocks tied to `smuggling_primer_received` flag
- Tests

### Phase AR-4 — Branching Climax
- M5A, M5B, M5C mission authoring
- Smuggling compartment install tutorial flow (M5A)
- Black market first-time UI (M5A)
- Customs inspection tutorial event (M5A)
- Faction reputation shift wiring (M5C)
- Tests

### Phase AR-5 — Closeouts and Polish
- M6 closeout variants (dialogue / journal)
- Crimson Reach light introduction — ONE dialogue hook at Nexus post-arc if the player saw Reach elements
- Rhea post-arc one-liner
- Odom post-arc one-liner (light reference)
- Journal entries
- Comprehensive integration tests

Each phase is scoped to be a focused session's work (comparable to PT-H or PT-N). The full arc takes 4-5 sprints.

---

## Permanent Unlocks Summary

By the end of Arna's arc, regardless of branch, the player has:
- Completed: trading, mining, refining, combat tutorials
- Received: smuggling primer (knowledge only, unless Branch A)
- Unlocked: smuggling compartments, black market visibility, smuggling contracts
- Banked: some credits (amount varies by branch)
- Changed: Crimson Reach rep (minor, one of several possibilities)
- Journaled: permanent reference to every system Arna explained

Branch A players additionally have:
- Completed: salvage + smuggling practical tutorials
- Rep: Crimson Reach penalty (pursued Keren)

Branch B players additionally have:
- Completed: salvage tutorial (peaceful)
- Rep: none

Branch C players additionally have:
- Rep: Commerce Guild or Crimson Reach positive shift (depending on who they sold to)
- Morality: journal weight

---

## Crimson Reach Integration

Light touch only. The arc:
- Names the Reach once, in M4 reveal
- Uses them as antagonists in M4 and M5A (tutorial-grade)
- Does NOT open the full Reach faction gameplay
- Does NOT unlock Reach missions or rep tracking beyond the arc's shifts
- Leaves the Reach as "something the player has heard of" for the main campaign to develop properly

Keren is a low-level informant, not a made man. His depot is a petty cache, not a Reach outpost. The scale stays small to respect MEMORY's designation of Crimson Reach as late-game content.

---

## Open Questions

1. **M4 location** — does the galaxy have a suitable derelict station to host the ambush, or do we author one?
2. **Rare-earth commodity** — does `rare_metals` fit the restricted-trafficking role, or do we need a new commodity entry (`rare_earth_ore`, `rare_earth_refined`)?
3. **Mission ID naming convention** — start new IDs with `arna_` prefix or fold into the generic naming scheme?
4. **Keren's fate in Branch A** — kill-or-spare player choice: does he become a dialogue reference in the main campaign, or does he vanish? My lean: vanish; keep the arc self-contained per user direction.
5. **Arna's pendant** — three conflicting stories is my proposal. User tone check: does this land for Aurelia's register, or is it too quirky?
6. **Branch C bounty routing** — Nexus Security vs. Crimson Reach. Two sub-options, or one? My lean: offer both, both are thematically distinct (legal vs. black-market betrayal).
7. **Tutorial difficulty gating** — Arna's arc is front-loaded; the player may not have gear for M4 combat or M5A. Should we scale enemies to player level, or trust the narrative placement to deliver roughly-matched difficulty?
8. **Which sprint ships first** — AR-1 alone (expansion of existing), or AR-1 + AR-2 together (narrative thread needs Tev to pay off)?

---

## Non-goals

- Arna does NOT become permanent crew
- Arna does NOT recur in the main campaign (stand-alone per user direction)
- Crimson Reach is NOT fully introduced here (light touch only)
- No new gameplay systems invented for this arc — existing systems only
- No new galaxy locations invented (reuse existing systems)
- No ground combat (that's campaign Act 1 territory)
- No new ship frames or major parts (scrapyard tier is the baseline)

---

## Closing

Arna's arc is a mini-campaign designed to do two jobs at once: teach the player how the game works, and teach the player what kind of universe they're in. The mechanics are real tutorials wrapped in story beats; the story beats are real character study wrapped in a scheme. The ending is earned either way — grinding-down, walking-away, or being-sold-out are all honest Expanse endings. Dark humor carries the tone. Player agency picks the shape.

When this ships, the post-tutorial player will have a full mental model of the gameplay loop and a clear read on the world's tone. They will also have had, briefly, a friend who meant it when she offered them a scheme, and may or may not have chosen to take it.

---

## AR-PK: Deferred Polish (2026-04-23) — SHIPPED

Three mechanics referenced narratively in AR-4 that were deferred from the M4/M5A sprints. All three now wired to actual gameplay tutorials, applicable to any player who touches smuggling (not M5A-scripted).

**PK-1: Hidden compartment install flow.** Pre-existing bug: buying the `hidden_compartment` upgrade only registered it on `upgrade_manager` but never created the `HiddenCompartment` object on the player, so trading view's hide/retrieve buttons stayed dead. Fixed in `shipyard_view._buy_selected`: when the upgrade is `hidden_compartment`, also instantiate `HiddenCompartment(total_cargo_capacity=player.max_cargo)`, set its progression ref, and fire a `FirstTimeTipOverlay` (flag: `seen_tip_hidden_compartment`). Uninstall helper merges hidden cargo back to main (split capacities sum to the full pool, so the cargo always fits).

**PK-2: First-time customs inspection tutorial.** `EncounterView` now accepts an optional `player` parameter and, for `encounter_type == "customs_inspection"` with `seen_tip_customs_inspection` unset, shows a `TutorialNarrationModal` explaining the four choices (comply/persuade/bribe/intimidate) and the hidden-hold doubled-penalty rule. `_ensure_encounter_view` in `game.py` now passes `self.player` through. Legacy call sites without player fall through cleanly.

**PK-3: Black market denial surface + first-time tip.** At systems with a black market rule (`nexus_prime`, `breakstone`, etc.), the toggle button now renders disabled with a tooltip reason when the player lacks access — previously invisible, which made the market feel nonexistent until access was granted. Toggling INTO the black market for the first time fires a one-time tip (flag: `seen_tip_black_market`) explaining price modifiers, contraband trading, and heat implications.

**Side-effect bug fix**: while wiring PK-3, caught that `TradingView._create_ui` only ran inside the first-time-tip dismissal path, so the market/UI was never initialized on return visits once `seen_tip_trading` was set. Refactored into `_init_station_state` called unconditionally on `on_enter`.

**Tests**: +21 in `tests/test_views/test_smuggling_polish.py` covering install wiring (idempotency + cargo merge), customs tutorial gating (first fire, second skip, non-customs skip, no-player fallback), and black market surface (enabled/disabled/absent states + tip lifecycle). The return-visit regression is guarded by `TestTradingViewReturnVisit`. Test total: 7,606 → 7,627. Writing Bible compliance now covers 8 tip bodies (all scanned for em-dashes/AI tells/sentence count).
