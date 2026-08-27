# Spec F — Act II Ambition: Lenses and Dilemmas

**Date**: 2026-08-27
**Status**: draft, pending review
**Arc**: AM (Ambition)
**Sibling of**: `2026-08-27-universe-discovery-design.md` (Spec D) — this is the
"ambition paths" corpus document Spec D named and deferred.

---

## Why this spec exists

Act I asks one question: **how do I survive?**

The player is an orphan from a run-down station whose father died of conditions
poverty inflicted on him. They spend the last of a meagre inheritance on a
home-built ship and leave, dedicating a life to the freedom their father never
had. They learn to trade, to fight off pirates, to keep a ship alive in hard
places. They find allies. Some become friends.

Then they uncover a plot that ends with their galaxy destroyed. A supernova.
Everyone they grew up among, gone in an instant. They survive only by warping out
at the exact moment, and arrive on the far side with nothing but a ship and a
crew.

Act II asks a different question, and it is the question the rest of the game is
built to answer:

> **Now that everything I knew is gone, what am I going to do with the life I
> still have?**

"Trader", "pirate", "miner" remain **how you play**. This spec is about **who you
become**, which is a different axis entirely, and the one that has to carry an
open-ended game.

## The design problem this solves

Sixteen ambitions, each with characters, worlds, rumours and reinforcing
systems, is not authorable as sixteen questlines. Act I is one galaxy with one
through-line and it took years. Sixteen arcs at that fidelity is a decade, and
the realistic failure is not running out of time — it is shipping sixteen thin
things instead of five deep ones. A shallow Vengeance arc actively cheapens the
supernova.

So this spec does not build sixteen questlines. It builds **one world that reads
sixteen ways.**

---

## The core architecture: a lens is a reading, not a track

A derelict hauler drifting in a dead system is one authored asset. Through
different lenses it is a different object:

| Lens | What it sees in that same wreck |
|---|---|
| Preservation | A cultural archive nobody else will save |
| Crime | A score, and a hull nobody will report missing |
| Truth | A transponder log placing a ship where it should not have been |
| Community | Forty survivors in cryo who need somewhere to go |
| Transcendence | An experimental neural rig in the medbay |
| Wealth | Salvage tonnage and a supply gap to exploit |

Same object. Six meanings. Authored once, with a paragraph per lens rather than
six questlines.

**This is the multiplier that makes sixteen ambitions affordable**, and it is the
same mechanism Spec D uses for discovery fragments, generalised. Author places,
people and events once; author what each lens sees in them.

Bespoke authoring then concentrates where it must: the handful of moments where
an ambition genuinely resolves. Those are the dilemmas, and there are eight.

### What a lens is, concretely

A lens is **data**, not code. Each is a record answering the same questions, so
that handing an author a new location plus the lens registry generates content
mechanically rather than requiring invention each time.

```
Lens
  id                  stable identifier
  name                player-facing
  core_fantasy        one line
  question            what its arc asks the player
  sees                what it notices in a place, wreck, rumour, person
  wants               what someone living it is trying to obtain
  trades              what they will give up to get it
  investment_from     actions that raise this lens's meter
  minigame_shape      the mechanical form that reinforces it
  voice               how a character embodying it speaks
  tier_unlocks        what deepens when a dilemma resolves in its favour
```

`minigame_shape` matters more than it looks. An ambition is only satisfying if
the *mechanics* of pursuing it feel like the thing itself. Truth wants deduction.
Wealth wants optimisation under scarcity. Community wants logistics and triage.
Transcendence wants irreversible upgrades with real costs. Getting this wrong
produces sixteen reskins of the same fetch loop, which is the specific failure
this section exists to prevent.

### Investment

Each lens carries a per-player investment value, raised by actions listed in
`investment_from`. Investment is what makes a dilemma land: a choice between two
ambitions the player never pursued is a menu, not a decision. **Dilemmas fire
only when both poles are above threshold**, which is also why they are rare
without needing a schedule.

A player who never touched Justice never receives its dilemma. That is correct.
You cannot lose something you never wanted.

---

## The sixteen lenses

Every lens participates in at least one dilemma, so none is decorative.

| # | Lens | Core fantasy | Its question | Mini-game shape |
|---|---|---|---|---|
| 1 | **Vengeance** | Hunt whoever caused or enabled the destruction | If you find them, what are you willing to become to punish them? | Pursuit: tracking, interrogation, closing distance on a fleeing target |
| 2 | **Wealth** | Build an interstellar commercial empire | After growing up with nothing, how much is finally enough? | Optimisation under scarcity: routes, margins, leverage |
| 3 | **Political Power** | Rise from nobody to governor, senator, kingmaker | Can power create the freedom you wanted, or only control over others? | Negotiation and vote-counting; favours as currency |
| 4 | **Exploration** | Go farther than anyone has gone | What is beyond the edge of known civilisation? | Survey and risk management at range; fuel, distance, the unknown |
| 5 | **Discovery** | Uncover ancient civilisations, lost technologies, cosmic phenomena | Understanding, not territory. What *is* this? | Analysis: assembling fragments into a coherent explanation |
| 6 | **Justice** | Become a marshal, investigator, protector | Can there be justice where the powerful write the laws? | Case-building: evidence, testimony, warrants that must hold |
| 7 | **Crime** | Become a pirate lord, cartel boss, legendary outlaw | Not "do crimes" — build a criminal identity and an organisation | Heist planning and heat management; risk against reputation |
| 8 | **Revolution** | Liberate exploited colonies, workers, stations | Destroy the systems that created people like your father | Organising: cells, sympathy, timing an uprising that can fail |
| 9 | **Empire** | Conquer territory and establish a sovereign state | Why influence governments when you can be one? | Territory, logistics of holding, and the cost of borders |
| 10 | **Community** | Build the home you never had | Nobody who depends on me will live like he did | Logistics and triage: housing, food, who gets in, who is turned away |
| 11 | **Legacy** | Make your existence matter after you are gone | How does history remember you? | Long-horizon investment: institutions, protégés, monuments that outlive you |
| 12 | **Faith** | Search for meaning in an incomprehensibly large universe | Is there anything out here that means anything? | Interpretation: doctrine, pilgrimage, phenomena that resist explanation |
| 13 | **Transcendence** | Push beyond ordinary humanity | Must humanity remain human? | Irreversible upgrades with real costs; each step closes a door |
| 14 | **Connection** | Build intimate relationships instead of institutions | Crew, friendship, romance, found family | Relationship maintenance under pressure; time as the scarce resource |
| 15 | **Truth** | Determine what really happened | The supernova may not have been what you were told | Deduction: sources, contradictions, assembling a case from fragments |
| 16 | **Preservation** | Protect what remains | You could not save your home. Perhaps you can stop the next one disappearing | Rescue and archival under time pressure; choosing what to save |

### Notes on lenses that are easy to collapse and must not be

**Exploration vs Discovery.** Exploration is distance: go where nobody has been.
Discovery is comprehension: understand what is there. A player can chart a
thousand systems and understand none of them, or spend a hundred hours on one
artefact. Different mini-games, different NPCs, different satisfactions.

**Political Power vs Revolution vs Empire.** Three answers to systemic power:
master the system, break the system, become the system. Collapsing them loses
the most interesting political space in the game.

**Wealth vs Community.** The same childhood produces both. *I will never be poor
again* and *nobody who depends on me will ever live like that* are the same
wound with opposite conclusions. This pairing is the emotional centre of the
whole design and should be authored with the most care.

**Vengeance vs Justice.** Personal against ideological. *They took my world* and
*nobody should ever be permitted to do this*. A player can hold both for a long
time, which is exactly what makes their eventual collision hurt.

---

## The eight dilemmas

Sixteen lenses have 120 possible pairings and most are inert. Mining against
Faith is not a dilemma. The drama lives in a small set where two ambitions the
player has genuinely invested in cannot both remain true.

| # | Tension | The question it forces |
|---|---|---|
| D1 | Vengeance ↔ Justice | Punish them, or make sure it can never happen again? |
| D2 | Wealth ↔ Community | Never poor again, or nobody near me ever poor again? |
| D3 | Political Power ↔ Revolution ↔ Empire | Master the system, break it, or become it? |
| D4 | Truth ↔ Vengeance | If it was not who you were told, does your rage transfer or dissolve? |
| D5 | Legacy ↔ Connection | Remembered by history, or by the people who knew you? |
| D6 | Preservation ↔ Empire | Save what remains, or build over it? |
| D7 | Faith ↔ Transcendence | Find meaning, or manufacture it? |
| D8 | Crime ↔ Community | Your organisation, or the people it preys on? |

D3 is a triangle rather than a pair; it resolves to one of three, closing the
other two.

**D4 is the sharpest and should be authored first.** It reaches back into Act I:
if the supernova was not what the player was told, the person they spent forty
hours hunting may be the wrong person. One authored revelation retroactively
recolours everything that came before it, which is the highest narrative return
in the entire document.

### Anatomy of a dilemma

Each of the eight is a hand-built set-piece with four required parts:

1. **Telegraph.** Permanent consequences plus ambush equals resentment. A
   character tells the player plainly, in advance, that they cannot keep doing
   both. Not a UI warning. A person who has watched them and says so.
2. **Collision.** The moment both cannot be satisfied. Fires only when both poles
   exceed the investment threshold.
3. **Visible cost.** The closed path must be *seen* closing: the investigator who
   trusted you stops taking your calls; the sponsor withdraws the commission;
   a door you spent thirty hours opening shuts audibly. Absence is forgettable.
   Refusal is not.
4. **Tier unlock.** The surviving ambition gains depth it did not have — contacts
   who only deal with someone who has proven they will go that far, methods
   previously refused. See "closure is a trade" below.

### Permanent closure

Resolution is **permanent and universe-wide**, not per-galaxy. The player cannot
walk both paths later somewhere else.

This is consistent with an existing project principle. From CLAUDE.md:
*"Deterministic outcomes: social skill checks use threshold comparison, NOT
random rolls. No save scumming."* Aurelia already refuses to let players reroll
out of consequences; permanent closure is the same philosophy applied to
identity.

### Closure is a trade, not a subtraction

**This is the requirement that makes permanence survivable, and it is not
optional.**

If resolving D1 merely deletes the Justice content, every dilemma shrinks the
game, and a decisive player ends with less to play than a fence-sitter. That
punishes exactly the conviction the design is trying to reward.

So each resolution closes one path **and deepens the other**. Net content stays
roughly constant; the *shape* of the remaining game changes, not its size. Every
dilemma must specify its `tier_unlocks` for each possible outcome. A dilemma
authored without them is incomplete and must not ship.

### Scars, not gaps

A closed path stays visible. The investigator who walked away still exists, still
will not speak to you, and is occasionally seen doing the work you did not.
Removing the content entirely makes the choice forgettable; leaving it present
and refused makes it permanent in the player's memory as well as the save file.

---

## Endings are capstones, and the game does not stop

There is no Act III. Act I is the galaxy where the player learns the systems and
their ship. It ends when that galaxy is destroyed. Act II is the universe opening,
and it is where the game lives from then on.

**Aurelia has no hard ending.** Each lens can reach a capstone — an authored
cutscene marking that this ambition arrived somewhere — and the player sees the
capstones they earned rather than a single canonical ending. Then they keep
playing. The capstone is a punctuation mark, not a terminus.

Sixteen capstones cost a cutscene each, which is far cheaper than sixteen
endgames, and fits "write your own story" better than a single ending could.

## After the capstone: identity is the generator

This is the hardest requirement in the document and the one most likely to be
got wrong.

Games that end their narrative and keep the world running usually go hollow at
exactly that moment: the systemic engine keeps turning, the meaning engine stops,
and what remains is errands. Infinite play without a meaning source is filler
with better graphics.

Aurelia's answer: **the resolved identity becomes the content generator.**

- Empire resolved does not end the Empire story. It begins the *problems of
  empire*: succession, borders, a governor who overreaches, a colony that would
  rather not be yours.
- Community resolved begins scarcity, newcomers who do not fit, and the outside
  power that notices you have built something worth taking.
- Vengeance resolved means living as someone who did that, and meeting people
  who know it.

Post-capstone content is therefore procedurally generated **from the player's
resolved position**, not from a generic pool. It is unbounded because
consequences are unbounded, and meaningful for the same reason the original
choice was.

### Procedural plus lens stops being generic

A procedurally generated derelict is filler. The same derelict read through the
player's lens is not.

Spec D already supplies the substrate: galaxy traits generate places, evidence
fragments generate leads. This spec supplies the meaning layer. **Procedural
content plus a lens is the multiplier that makes open-ended play survivable**,
and neither half works alone — traits without lenses produce texture without
purpose; lenses without traits produce purpose with nothing to point at.

### The world must move without the player

An open-ended game stays alive only if things happen while the player is
elsewhere. Factions should pursue their own ambitions whether or not the player
engages. A galaxy ignored for eighty hours should have changed when they return.
Somebody else should occasionally get there first.

This is expensive and it is the difference between a living universe and a large
static one. It is also the only durable answer to "why keep playing after the
capstone" that is not simply *more*.

Scoped here as a **requirement on the design**, with its implementation deferred
to a sibling spec — it is a simulation problem, not an ambition problem.

---

## Scope

**In scope:**
- The lens data model and registry
- Sixteen lens definitions
- Investment tracking per lens
- Eight dilemmas: telegraph, collision, visible cost, tier unlocks
- Permanent closure semantics and save/load
- Capstone cutscene hooks
- Post-capstone generation keyed to resolved identity

**Out of scope, deferred to siblings:**
- **The Threshold** — the Act I ending, the escape, the reveal
- **Inter-galactic travel** and the new mechanical systems
- **Rebuild-from-nothing** — losing everything and re-accumulating
- **World-moves-without-you** simulation
- Authored galaxy content (the writing itself)
- Anything in Act I

## Success criteria

1. A lens can be added as data with no code change.
2. A new authored location can be given per-lens readings without touching lens
   or dilemma code.
3. Investment is tracked per lens, persists across save/load, and is visible to
   the player in some form — a choice with hidden stakes is not a choice.
4. A dilemma fires only when both poles exceed threshold, verified by a scenario
   test that drives one pole high and confirms no collision.
5. Every dilemma specifies `tier_unlocks` for every outcome. A data-integrity
   test fails the build if any outcome lacks one, on the same pattern as the
   findings-register and evidence-pool guards.
6. Resolution is permanent: reloading a later save cannot reopen a closed path.
7. A closed path leaves an observable scar — the refusing NPC still exists.
8. Capstones fire without ending the session; play continues afterward, verified
   by a scenario test.
9. Post-capstone generation produces content keyed to the resolved identity, not
   from a generic pool.
10. Full suite green; no regression from the current baseline.

## Risks

- **Sixteen shallow lenses.** The named failure mode. Mitigation is the shared-
  world model plus concentrating bespoke effort on eight dilemmas — but the risk
  returns the moment someone authors a lens without a distinct `minigame_shape`,
  because that is what makes an ambition feel like itself rather than a reskin.
- **`tier_unlocks` treated as optional.** Without them permanent closure becomes
  pure subtraction and the game punishes conviction. Criterion 5 exists to make
  this fail loudly rather than degrade quietly.
- **The player not understanding the stakes.** Permanent plus unclear equals
  resentment. The telegraph is a hard requirement, not polish.
- **Post-capstone hollowness.** If identity-keyed generation is thin, the game
  goes quiet exactly when the player has most invested in it. This is the single
  most likely place for the design to fail in practice, and it will not show up
  in testing until someone plays a hundred hours.

## Open questions

- **How is investment surfaced?** A visible meter is legible but gamifies
  identity into a score to max. Something more oblique — how NPCs address you,
  what work you get offered — is truer but risks the player never seeing the
  dilemma coming. Criterion 3 requires *some* visibility; the form is unresolved.
- **Can a dilemma be declined?** Refusing to choose is itself a characterisation,
  but an indefinitely deferred collision undermines the whole mechanic.
- **How many capstones can one player reach?** Unbounded means a completionist
  collects all sixteen and the choices stop mattering; a hard cap needs a
  diegetic reason.
- **Does Act I need retrofitting** so investment can begin before the supernova?
  D4 (Truth ↔ Vengeance) reaches back into Act I, which implies at least some
  seeding there. Not answered here.
