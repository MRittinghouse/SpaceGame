# Lens Authoring Guide

A working reference for content authors. Read this before authoring a per-lens reading, a
lens-aware NPC, or a location entry that sixteen lenses will filter through.

**Cross-references (do not duplicate these):**
- `dialogue_writing_guide.md` SS6 -- AI anti-patterns to avoid
- `dialogue_writing_guide.md` SS7 -- expression set (20 approved expressions)
- `dialogue_writing_guide.md` SS8 -- skill-check grading ladder (target grade B or A)
- `dialogue_writing_guide.md` SS11 -- naming rules
- `aurelia_voice_examples.md` -- 30 paired wrong/right examples; 16-item diagnostic checklist

---

## 1. What this guide is for

You are about to author a lens reading, a lens-aware NPC, or both. A lens is a motivational
reading of the shared world: the same derelict hauler, the same station, the same political
crisis is a different object depending on which of the sixteen frames the player is using to
see it. The architecture that makes sixteen ambitions affordable is that one authored location
plus one short paragraph per lens equals sixteen readings, not sixteen questlines.

**The promise:** author a place once, filtered through sixteen lenses without authoring sixteen
separate storylines.

**The failure mode this guide exists to prevent:** sixteen shallow reskins. Each of sixteen
NPCs who sounds the same but wears different vocabulary. Each of sixteen location paragraphs
that differ in flavor but share the same mechanical hook. Section 5 covers this in detail and
gives a self-audit checklist you run before submitting any new lens or per-lens reading.

**The Lens fields you are filling in** (from `spacegame/models/lens.py`):

| Field | What it is |
|---|---|
| `lens_id` | Stable snake_case id. Do not change once shipped. |
| `name` | Player-facing display name. |
| `core_fantasy` | One line: what this ambition gives the player. |
| `question` | What the arc asks the player to answer through play. |
| `sees` | What someone with this lens notices in a place, wreck, rumour, or person. |
| `wants` | What a character embodying this lens is trying to obtain. |
| `trades` | What they will give up to get it. |
| `investment_from` | Action tags that raise this lens's investment. Vocabulary in Section 5. |
| `minigame_shape` | The mechanical form that reinforces the ambition's feel. |
| `voice` | How a character embodying this lens speaks. One focused sentence. |
| `tier_unlocks` | What deepens when a dilemma resolves in this lens's favour. |

---

## 2. Per-lens voice notes and NPC construction patterns

Each entry below covers: register, verbal habits, one NPC pattern (role, premise, one sample
line), and the distinction between a scar NPC and a hostile NPC for that lens.

**Scar NPC**: refused the player at a dilemma; still exists; will not deal. Their presence
makes the choice permanent. Voice is quiet, not bitter. They go about their work.

**Hostile NPC**: opposed to the lens on principle and acts against the player. Not the same as
cold or unhelpful; hostile NPCs actively work against the player's interest, usually through
structural or procedural means rather than violence.

---

### vengeance

**Register.** Precise, patient, controlled. Every word serves a purpose. Does not explain
motivation unprompted. Catalogs, lists, tracks. Speaks in specific facts rather than
emotional language.

**Verbal habits.** Counts things. Names names and marks dates. Refers to the target as "they"
until a name is confirmed. Corrects imprecision -- "not soon, Wednesday, third shift." Silences
are deliberate. Does not speculate about motive; states what the record shows.

**NPC pattern.** The Shipping Registrar: a dock administrator who has access to manifests from
the night of the destruction and is weighing whether to share them against the personal risk
of doing so.

Sample line (player Persuasion, grade B -- reads the NPC's actual fear):
> "You're not protecting them. You're protecting yourself from what happens when I confirm
> you knew."

**Scar NPC.** Cordial. Closed. "You made your choice. I respect it." Does not engage further.
Occasionally seen pulling manifests without the player's help.

**Hostile NPC.** Has operational reasons to stop the investigation. Works to muddy trails and
discredit sources. Does not threaten the player personally -- removes access.

---

### wealth

**Register.** Optimized, additive. Converts everything to margin and window. Speaks in ratios
and numbers, not in relative terms. Recalculates mid-sentence when conditions shift.

**Verbal habits.** Cites specific numbers -- eight percent, not eight-ish. Names the gap before
naming the opportunity. Does not celebrate trades after the fact; moves to the next one.
Dismisses sentiment as a variable that doesn't close.

**NPC pattern.** The Route Analyst: a Guild logistics officer with access to regional supply
data, willing to share first-look information on supply gaps in exchange for a finder's cut on
transactions that exploit them.

Sample line (player Observation, grade A -- the observation is the entire insight):
> "Seventeen shipments in, zero out. That's not a distribution hub. That's a stockpile.
> Someone's waiting for a price event."

**Scar NPC.** Polite. Will not broker deals. "You walked away from a profitable arrangement.
Some doors close." Continues to close deals without the player.

**Hostile NPC.** Undercuts routes, buys out suppliers before the player arrives, competes
structurally. Does not perform the hostility; just executes it.

---

### political_power

**Register.** Measured, indirect. Everything said implies something unsaid. Speaks in
hypotheticals and "one could argue." Credits positions to third parties.

**Verbal habits.** Names rooms rather than actions -- "the session that year," "the floor vote."
Never claims credit for the thing that happened. Uses "arrangements" as the default noun for
deals. Comfortable with long pauses.

**NPC pattern.** The Faction Clerk: a low-level legislative aide with access to committee
schedules and real-time knowledge of which three votes are persuadable on a current motion.

Sample line (NPC pointing to an opening):
> "The delegate from Halcyon keeps two appointments for constituents on rotation day.
> One slot opened up this morning."

**Scar NPC.** Formal. Routes procedural notes correctly through official channels. Offers
no private access. "That channel closed." Continues to manage committee logistics without the
player's involvement.

**Hostile NPC.** Moves procedurally. Missing hearings, expired permits, motions tabled.
Never confrontational; uses the machinery of process as the weapon.

---

### exploration

**Register.** Terse, spatial, risk-calibrated. Describes distance in fuel and time. Does not
romanticize. States range before describing the destination.

**Verbal habits.** Uses cardinal directions relative to the core, not poetic descriptors.
Calibrates risk against fuel and return window -- "three days out, four back at minimum."
Treats the unknown as a logistical fact, not a mystery.

**NPC pattern.** The Fuel Depot Manager: operates the last resupply before the outer edge;
trades passage credits for accurate fuel-burn data from beyond the depot's measurement range.

Sample line (NPC, grounded):
> "Last three ships filed they were going beyond K-9. Two came back. They didn't see each
> other out there."

**Scar NPC.** Still runs the depot. Fuel available at standard rates. "You have your reasons."
Does not ask what they are.

**Hostile NPC.** Withholds resupply data. Sells position information to parties who don't want
the player at the edge. The refusal is commercial, not personal.

---

### discovery

**Register.** Precise, methodical, slightly impatient when interrupted. Builds hypotheses
incrementally. Never leaps.

**Verbal habits.** Distinguishes "suggest" from "confirm." Corrects the word "proof" to
"evidence" or "indication." Asks what the source is before accepting a claim. Comfortable with
an open question -- does not need to resolve it to proceed.

**NPC pattern.** The Archive Specialist: works salvage licensing at a recovery depot; knows
which wrecks have filed cultural-preservation flags and which have not -- a distinction that
matters before the player touches anything.

Sample line (player Observation, grade A -- expertise-specific reading of an anomaly):
> "The hull registry has a skip between 2298 and 2302. That's not a file gap -- they used a
> different classification system that year. Something changed how they catalogued things."

**Scar NPC.** Continues cataloguing. Answers factual questions. "Collaborations depend on
mutual investment." Does not elaborate.

**Hostile NPC.** Publishes findings first. Claims discovery credit before the player can
establish priority. The competition is academic and procedural.

---

### justice

**Register.** Formal but not cold. Methodical. Distinguishes "allegation" from "charge" from
"finding." Uncomfortable with shortcuts and says so.

**Verbal habits.** Names the applicable regulation or precedent before acting. Reluctant to
speculate; when speculating, names it as speculation. Does not move without the record.

**NPC pattern.** The Station Mediator: handles disputes between cargo operators and dock
authorities; holds case records going back fifteen years that bear on a current investigation.

Sample line (player Persuasion, grade B -- reads the procedural situation):
> "The precedent from 2318 already answers this. You don't need to file for a new ruling.
> You need someone to look at what was filed then."

**Scar NPC.** Continues mediation work. Treats the player as any other petitioner. "Rules
apply to everyone." No exception is offered and none is implied.

**Hostile NPC.** Moves to have the player's license reviewed. Files counter-complaints.
Weaponizes process. Does not need to win; needs the player to spend time responding.

---

### crime

**Register.** Oblique, transactional, unhurried. Never explains more than necessary. Questions
are measured. Silences are information.

**Verbal habits.** Uses passive constructions to maintain deniability. "Arrangements can be
made." "Cargo sometimes finds its way." Gives the player time to show what they know before
committing to anything.

**NPC pattern.** The Freight Broker: moves cargo that does not appear on the manifests;
connects operators who need discretion with suppliers who do not ask. Seventeen years in
business by being careful about which questions get answered.

Sample line (NPC, broker's read of an Intimidation approach -- shows how the lens's register holds under pressure):
> "I've been in business seventeen years. I know what questions the Guild doesn't ask.
> You're not one of them."

**Scar NPC.** Still in business. Available for legitimate work. "Professional discretion
goes both ways." The arrangement that ended stays ended.

**Hostile NPC.** Warns the right people. Reroutes supply chains away from the player. Does not
threaten; removes access and lets the player discover it after the fact.

---

### revolution

**Register.** Urgent but controlled. Specific about grievances. Names the structural condition,
not the personal grievance. Inclusive "we" when others are present; shifts to hard facts when
alone with someone.

**Verbal habits.** Distinguishes workers from management without making it a speech. Counts
things: shifts missed, fines levied, injuries filed and unfiled. Precise about which grievance
belongs to which faction.

**NPC pattern.** The Union Coordinator: organizes three docks; holds attendance data from two
unauthorized work stoppages and knows who gave the order to clear the docks that night.

Sample line (player Persuasion, grade A -- the labour data is the leverage, named precisely):
> "The dock manager's filing shows zero injuries for Q3. The Union's records show four.
> Those numbers belong to different universes. Whose version holds up at arbitration?"

**Scar NPC.** Organizes without the player's help. "We're still here." Means it, without
sentiment. The work continues.

**Hostile NPC.** Considers the player management-adjacent and acts accordingly. Cold, not
violent. Does not share information, contacts, or access.

---

### empire

**Register.** Strategic, patient. Frames current moves in terms of five years out. Does not
perform certainty -- calculates. Speaks in leverage and cost-of-holding, not valor.

**Verbal habits.** Names the leverage before the ask. Distinguishes territory by what it costs
to hold, not what it was worth to take. Treats commitments as contracts, not gestures.

**NPC pattern.** The Colonial Administrator: manages a contested system and is evaluating
which flag to fly based on who can guarantee shipping lanes through the next political cycle.

Sample line (NPC, grounded in stakes):
> "You're not asking for my loyalty. You're offering a trade. What happens to my fuel
> access when the lanes shift?"

**Scar NPC.** Manages the system under a different arrangement. "The deal landed elsewhere.
No hard feelings. Business." The system is now off-limits.

**Hostile NPC.** Secures alternate guarantees. Shuts the player's ships out of fueling
contracts in controlled territory. The exclusion is procedural and complete.

---

### community

**Register.** Specific about whose needs. Plain-spoken, averse to abstraction.
Logistics-focused. Asks about the person before the problem.

**Verbal habits.** Names individuals, not categories -- "Sefa's family" not "the refugees."
Counts resources in terms of people supported, not units held. Converts abstract offerings
into concrete questions: "That's enough for how many families for how long?"

**NPC pattern.** The Settlement Quartermaster: manages food and power allocation for a transit
camp; knows which forty-two families have nowhere to go when the camp's permit expires.

Sample line (NPC, naming the stakes in concrete terms):
> "Forty-two families. Eleven kids under ten. I can tell you exactly what the next three
> weeks look like. You want the number or the story?"

**Scar NPC.** Continues managing the camp on reduced resources. "We make do." No bitterness.
The families are still there. The player is not part of the plan anymore.

**Hostile NPC.** Directs community resources and trust away from the player. Tells the right
people what the player chose. The damage is reputational and permanent.

---

### legacy

**Register.** Long-horizon, measured. Invests time and resources in returns that will not come
for a decade. Does not mistake fame for legacy.

**Verbal habits.** Distinguishes the record from the impact. Asks what survives the person,
not what they are remembered for. Talks in decades and specific institutions, not in vague
futures.

**NPC pattern.** The Settlement Archivist: maintaining a historical index of labor actions
going back to the founding; knows whose names appear in the official record and whose do not.

Sample line (player Observation, grade A -- expertise reveals what the record hides):
> "The settlement record credits the founding to three names. The labor rolls from year one
> list forty-six. Whoever wrote the history knew what they were doing."

**Scar NPC.** Continues the project. References the player as a case study, not a partner.
The archive grows. The player's contribution, if any, is documented accurately.

**Hostile NPC.** Shapes the historical record to erase or discredit the player's
contributions. Does this through the legitimate process of who gets cited and how.

---

### faith

**Register.** Interpretive, attentive, unhurried. Comfortable with ambiguity. Names phenomena
before assigning meaning to them. Does not force resolution on open questions.

**Verbal habits.** Returns to physical images: weight, light in specific conditions, the
specific texture of a threshold. Uses analogies from direct experience, not doctrine. Does not
speak of the void as an entity.

**NPC pattern.** The Pilgrim Registrar: maintains records of those who have completed specific
routes; connects pilgrims with communities at destinations who are expecting them.

Sample line (NPC, grounded and specific):
> "Fourteen hundred people have completed the Silence Route since 2290. I've met three who
> said it answered their question. The rest said it asked a better one."

**Scar NPC.** The route stays open. The registrar keeps records. "What you sought wasn't
there. That tells you something too." Does not pursue the conversation further.

**Hostile NPC.** Controls access to specific phenomena the player wanted to reach. Redirects
pilgrims away from the relevant site or community. The blockage is administrative.

---

### transcendence

**Register.** Precise about limits and costs. Curious about thresholds. Distinguishes what the
baseline human can process from what has been modified. Not mystical -- technical.

**Verbal habits.** Names the modification by its cost and its functional change, not its
promise. Uses "integrated," "extended," "closed" rather than "augmented" or "enhanced."
States what a modification closes before stating what it opens.

**NPC pattern.** The Integration Technician: runs a licensed clinic with unreleased components;
can broker access to modifications that are not on the open registry, for operators who have
already done the research.

Sample line (player Intimidation, grade B -- reads that the decision is already made):
> "You know the recovery window. You know what it closes. You're here because you've already
> decided. So what are you waiting for me to say?"

**Scar NPC.** Clinic operates. Patient records are private. "Previous clients don't come
back for the same reason." Means both that they don't need to and that they can't.

**Hostile NPC.** Files regulatory complaints about unlicensed modifications. Blocks access to
modification networks through the official registry. Operates entirely inside the law.

---

### connection

**Register.** Specific about who, when. Remembers. Asks about people by name. Does not
generalize from the specific person to a type.

**Verbal habits.** Uses first names without asking permission. Notes how people change over
time. Returns to conversations that happened months earlier. Does not use "we" to describe
groups the character is not personally part of.

**NPC pattern.** The Long-Route Correspondent: maintains informal mail runs between isolated
settlements; knows who is expecting to hear from whom and hasn't.

Sample line (NPC, specific and carrying real weight):
> "She sent three letters in January. None came back. I've been holding a fourth since
> February that I don't know whether to deliver."

**Scar NPC.** Still runs the route. Delivers the player's mail alongside everyone else's.
"Your letters land. That's what matters." The warmth is real; the working relationship is
over.

**Hostile NPC.** Withholds correspondence. Manages who hears from whom and when. The harm is
felt slowly and in the absence of what should have arrived.

---

### truth

**Register.** Methodical, skeptical of first explanations. Distinguishes between what a source
claims and what it establishes. Uncomfortable with conclusions that arrived too easily.

**Verbal habits.** Attaches uncertainty explicitly -- "the report says" rather than "it is."
Uses "placed" and "logged" rather than "was." Distinguishes "suggest" from "confirm." Does not
close a lead until the source and the claim have been separated.

**NPC pattern.** The Signals Analyst: cross-indexes transponder logs against official shipping
records; has caught placement discrepancies that official channels never investigated.

Sample line (player Observation, grade A -- only expertise catches the specific discrepancy):
> "The manifest says she departed K-9 on the 14th. The beacon log puts her at Penumbra on
> the 12th. One of those is a clerical error. Neither one filed a correction."

**Scar NPC.** Analysis continues. Information shared at standard rates. "The record speaks for
itself, with or without your interest in it." The work does not stop.

**Hostile NPC.** Discredits sources. Generates conflicting data. Makes the investigation
harder to close by ensuring no single thread leads cleanly anywhere.

---

### preservation

**Register.** Specific about what exists and how long it has left. States replacement costs
and recovery windows. Does not romanticize loss; does not minimize it.

**Verbal habits.** Identifies objects by age and condition, not aesthetic value. States what is
unique and what has a copy. Distinguishes "recoverable" from "gone." Converts urgency to
specific timelines.

**NPC pattern.** The Recovery Coordinator: runs a cultural salvage operation; knows which
sites have active preservation claims and which are days away from an extraction permit.

Sample line (NPC, stating the timeline precisely):
> "The permit window closes in eleven days. After that, whatever's in the lower decks belongs
> to whoever files the extraction claim. We don't have eleven days of funding."

**Scar NPC.** Operation continues on reduced capacity. "The next site is already mapped.
Some things couldn't wait." The work is smaller. The coordinator does not say this with
resentment.

**Hostile NPC.** Files extraction claims ahead of the player. Makes every decision a race
against an opponent with more funding and faster paperwork.

---

## 3. The shared-world model: one place, sixteen readings

One authored location plus one short paragraph per lens equals sixteen readings. This is the
multiplier that makes sixteen ambitions affordable.

**What the location paragraph must name** (so each lens has a hook to pull on):
- One specific object, person, or structural fact that is genuinely present and unique to this place
- One state of the place that is unstable -- a pending decision, a resource running short, a
  relationship that has not resolved
- One gap in the official record that is not explained away

**What the location paragraph stays silent about** (so each lens can speak):
- The value of the object. Preservation and wealth read it differently; neither value belongs
  in the base entry.
- Who is responsible for the unstable state. Crime and Justice name different suspects; the
  base entry names the fact, not the cause.
- What the gap means. Truth, Vengeance, and Discovery each follow a different thread.

The location paragraph should be specific and grounded, not a deliberately bland container.
The trick is not thinning the content -- it is choosing what to leave unsaid, so each lens
can speak without contradicting the authored core.

**How `sees` drives per-lens reading.** The `sees` field on each Lens record states what
someone with that lens notices in a location. When authoring a per-lens paragraph for a
specific place:

1. Start with the `sees` statement as a filter.
2. Name the specific object, person, or fact in this location that the lens would focus on.
3. Write one paragraph from that focus. The paragraph names something specific to this place;
   it does not restate the `sees` field in different words.

Two paragraphs about the same derelict hauler under different lenses should not be swappable.
If they are, the per-lens paragraph has not done its job.

---

## 4. Worked example: the derelict hauler through three lenses

The hauler is a shared authored asset from Spec F. One ship, drifting in a dead system.
The base asset notes: the hull registration is three years out of date, the cryo systems
are still running on backup power, and the ship's log was partially overwritten.

**Under preservation:**

The cryo log shows thirty-eight individuals in the lower bays, none tagged to an active
population registry. The backup power cell will hold for nineteen more days. After that the
systems fail in a specific sequence: life-support heat last, which means the occupants will
have longer than they should. The manifest lists the vessel as a livestock transport. There
is no livestock on board. The log gap is not a technical fault -- the overwrite was manual,
entry by entry, and whoever did it stopped before finishing. Seventeen entries remain
intact. The question is not whether anyone survives. The question is what is in those
seventeen entries and whether there is a registry somewhere that is still looking for
these people.

**Under crime:**

The hull registration lapsed in 2330. The ship has been running outside registry for three
years, which means the cargo has been running outside manifest for three years. The cryo
systems are commercial units but the access codes are not commercial -- they require a
port authority override key to open without triggering an alert, and somebody aboard had
one. The log was partially wiped but the wipe was interrupted, which means someone left in
a hurry or was interrupted in turn. The salvage reporting window opened fourteen days ago
when the beacon went active. Nobody filed. A ship running outside registry for three years
with a valid port key and no salvage report has a reason for every one of those facts, and
those reasons point in the same direction.

**Under wealth:**

Thirty-eight cryo units, unknown contents. Backup power gives a nineteen-day window.
The livestock manifest means the holds are cleared to carry biological goods, which covers
a useful range of cargo types that standard manifest rules complicate. The dead system has
no traffic monitoring since the relay station burned out in 2328 and was not replaced. The
gap between the hull registration lapse and the current date is three years of transits
nobody logged. The question is who owns the salvage rights at day fifteen and whether that
person is currently reachable, because a ship carrying three years of unlogged biological
cargo and a partial manifest wipe is worth significantly more than its hull value if the
deal is structured correctly before the window closes.

**Self-check paragraph:**

Preservation names the intact log entries and the nineteen-day recovery window; neither
appears in the crime or wealth readings. Crime names the port authority override key and
the interrupted wipe, and reads the lack of a salvage filing as operational information
that points to who holds the key; neither reading applies to the other two. Wealth names
the livestock manifest clearance and the unmonitored system as market structure, and
converts the cryo units to a cargo-type question before anything else; the other two
readings do not treat the cryo units as goods. If a reader could move the Wealth paragraph
under Preservation without noticing the switch, the Wealth paragraph did not do its job.

---

## 5. The reskin failure mode: concrete tells and self-audit

### What sixteen shallow reskins look like

Two lenses collapse to the same reskin when:

- Their `minigame_shape` descriptions reduce to the same loop under examination (two lenses
  that both say "gather information and use it" without distinguishing what the information is
  for or how gathering it feels different)
- Two NPC patterns whose sample lines could be swapped without the reader noticing
- `wants` and `trades` fields that name only generic goods (credits, cargo, favours) without
  naming what specifically this lens values
- Per-lens location readings that differ only in vocabulary, not in what they name
- A Vengeance NPC and a Justice NPC whose voices are interchangeable (they are not: Vengeance
  is personal and patient; Justice is institutional and uncomfortable with shortcuts)
- A Wealth NPC and a Community NPC who both talk about resource allocation without the
  Wealth NPC converting everything to margin and the Community NPC naming specific people

The most common collapse is Exploration vs Discovery, Political Power vs Revolution vs Empire,
and Wealth vs Community. See Spec F for why these must remain distinct.

### Self-audit checklist

Run this before submitting any new lens definition or per-lens reading.

**Lens definition:**
- [ ] Does `sees` name what this specific lens notices, not what any curious person would?
- [ ] Does `minigame_shape` describe a loop that is mechanically distinct from the adjacent
      lenses that are easy to confuse with this one?
- [ ] Does `voice` contain at least one feature (a verbal habit, a register quality, a silence)
      that would not appear in any other lens's voice description?
- [ ] Does `investment_from` list actions that are specific to this ambition's pursuit, not
      generic player activity?

**Per-lens reading (location paragraph):**
- [ ] Does the paragraph name at least one specific object, number, or actor that only this
      lens would care about?
- [ ] Could this paragraph be moved under a different lens without the reader noticing? If yes,
      rewrite.
- [ ] Does the paragraph contradict or ignore the base location's authored core? If yes, revise
      the paragraph (do not revise the base).

**NPC pattern:**
- [ ] Does the sample line pass the Aurelia diagnostic checklist (16 items, `aurelia_voice_examples.md`)?
- [ ] If the sample line voices a social skill (Persuasion, Intimidation, Observation,
      Deception, Leadership), does it reach grade B or A on the ladder in
      `dialogue_writing_guide.md` SS8?
- [ ] Is the scar NPC distinct from the hostile NPC in behavior and in register, not just in
      plot state?

---

### `investment_from` vocabulary

Action tags follow the same snake_case verb_noun shape as `AmbientLine.action_type`
(e.g. `sold_cargo`, `combat_victory`). The five existing procedural mission types that lens
definitions may reference:

| Mission type | Relevant lenses |
|---|---|
| `bounty` | vengeance, justice, crime, truth |
| `delivery` | wealth, community, connection, preservation |
| `smuggling` | crime, revolution, wealth |
| `survey` | exploration, discovery, truth |
| `salvage` | preservation, crime, wealth, discovery |

Additional tags per lens (starting palette -- extend as content grows, not a closed set):

| Lens | Example `investment_from` tags |
|---|---|
| `vengeance` | `interrogated_contact`, `tracked_target`, `recovered_evidence`, `pursued_lead` |
| `wealth` | `exploited_gap`, `underbid_competitor`, `purchased_route_rights`, `sold_cargo` |
| `political_power` | `secured_vote`, `traded_favour`, `won_floor_session`, `placed_ally` |
| `exploration` | `surveyed_region`, `charted_system`, `reached_edge`, `survived_hostile_transit` |
| `discovery` | `assembled_fragment`, `confirmed_hypothesis`, `filed_artifact_claim` |
| `justice` | `filed_warrant`, `secured_testimony`, `presented_evidence`, `won_arbitration` |
| `crime` | `completed_smuggling`, `evaded_patrol`, `bribed_inspector`, `built_network_contact` |
| `revolution` | `organized_cell`, `backed_stoppage`, `distributed_materials`, `timed_action` |
| `empire` | `secured_territory`, `established_logistics`, `placed_administrator` |
| `community` | `housed_family`, `allocated_resource`, `settled_dispute`, `sourced_supply` |
| `legacy` | `funded_institution`, `placed_protege`, `commissioned_record` |
| `faith` | `completed_pilgrimage`, `interpreted_phenomenon`, `consulted_doctrine` |
| `transcendence` | `accepted_modification`, `integrated_upgrade`, `crossed_threshold` |
| `connection` | `maintained_bond`, `honored_commitment`, `shared_history` |
| `truth` | `contradicted_source`, `recovered_log`, `assembled_case`, `closed_lead` |
| `preservation` | `rescued_artifact`, `filed_preservation_claim`, `evacuated_population`, `archived_record` |

When a downstream sprint adds a new mission type, add it to the mission type table above. The
per-lens tag lists are a starting palette and will grow as A2-5, A2-6, and the dilemma sprints
land. Drift is expected and does not require a guide rewrite.
