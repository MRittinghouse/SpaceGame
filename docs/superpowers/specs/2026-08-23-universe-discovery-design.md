# Spec D — Universe Structure and Discovery

**Date**: 2026-08-23
**Status**: draft, pending review
**Arc**: UN (Universe)
**Position**: first document of the Act II corpus. Everything else in that corpus depends on the
structure defined here.

---

## Why this spec exists

Aurelia's content currently stops at the end of Act I. Act I is a single galaxy: the player learns
the systems, meets the factions, builds ships, and the arc ends with that galaxy destroyed and the
player's ship escaping into open space.

Everything after that is unwritten, and deliberately so. The intent is not "Act II." It is:

> The rest of the acts are unwritten, until you, the player, live them.

At the moment of escape the universe opens. Multiple galaxies, explorable in **any order**, each
with its own identity. The player has lost everything and rebuilds as whoever they choose to be:
hunting the faction that destroyed their home, running freight, running spies, running guns, or
building something else entirely.

The target feeling is the Bethesda threshold: stepping out of Vault 101, or through the prison door
in Oblivion. A vast expanse, visible landmarks, and no rails.

## Scope

**In scope for this spec:**
- Universe structure: how many galaxies, of what kinds, and how they relate.
- The galaxy trait model: what makes a galaxy feel like itself.
- The discovery model: how a player learns a galaxy exists and how they resolve it into a
  destination.
- The content rule that keeps discovery from becoming a checklist.

**Deferred to sibling specs in the Act II corpus:**
- **The Threshold** — the Act I ending, the escape sequence, and the reveal as a set-piece.
- **Ambition paths** — revenge, empire, shipping, espionage, piracy as divergent long-form goals.
- **New mechanical systems** — inter-galactic travel, new mini-games.
- **Rebuild-from-nothing** — losing everything and re-accumulating meaningfully.
- **Authored galaxy content** — the actual writing: factions, characters, dialogue, set-pieces.

This spec is the skeleton. The others hang on it, so it goes first.

---

## Decisions locked

1. **Roughly 5-6 authored galaxies, plus a few dozen procedural ones.** Not 100. Vastness is a
   feeling produced by variance and discovery, not by a count. Elite has 400 billion systems and
   feels empty. A few dozen galaxies with high trait variance will feel larger than a thousand
   samey ones, and a player can plausibly see a meaningful fraction of them.
2. **One galaxy system, varying authorship density.** There are not "procedural galaxies" and
   "authored galaxies" as separate constructs. Every galaxy is generated from composable traits.
   Authored galaxies are the ones that additionally carry hand-written layers. This means one system
   to build and tune, the ability to promote a procedural galaxy to authored later, and no visible
   seam for the player to find.
3. **Discovery is evidence-based, not marker-based.** Galaxies are not pins on a map waiting to be
   visited. They are inferred from fragments the player finds while doing other things.
4. **Resolution is a threshold, not a set.** A rumor resolves on **any 3 of 7** fragments. Never on
   three specific ones.
5. **Every authored galaxy has a trail per playstyle**, spanning at least four.
6. **Depth substitutes for breadth.** Deep specialization yields higher-value fragments, so a
   single-system expert resolves rumors on roughly the same curve as a generalist.
7. **A passive floor exists.** Some fragments arrive from things every player does regardless of
   build, so the universe never closes on anyone.
8. **Discovery itself is optional.** A player who wants to haul freight in charted space forever is
   allowed to. Rumors accumulate quietly and wait.
9. **The reveal shows scale and withholds specifics.** The player sees that the universe is
   enormous, and almost none of it is resolved.
10. **All of this is gated behind Act I completion.** None of it exists in the Act I experience.
11. **Procedural galaxies generate rumors too.** Discovery is not a tell. If only authored galaxies
    produced leads, players would learn within hours that a rumor always means hand-made content,
    and the seam this design exists to hide would be visible from the first trail. Authored galaxies
    are distinguished by the **density, specificity, and corroboration** of their evidence, never by
    whether evidence exists at all. See "Signal and noise" below, because this decision carries a
    real cost that has to be managed rather than wished away.

---

## The galaxy model

A galaxy is generated from **composable traits**. A trait is data, and it drives:

- market behaviour and commodity availability
- faction presence and inter-faction relations
- encounter tables
- palette and visual identity
- ambient chatter and dialogue tone

Example traits: `civil_war`, `dead_economy`, `corporate_monoculture`, `quarantine`,
`pilgrimage_route`, `post_collapse_salvage_field`.

Traits combine. A quarantined pilgrimage route is a different place from a quarantined corporate
monoculture, and neither needed bespoke work.

This is the mechanism that makes the civil-war galaxy affordable. Treated as a hand-scripted place
it costs a galaxy. Treated as a **trait**, it costs a trait, and it yields that hook plus every
other combination it participates in.

### Authorship density

| Density | What it carries |
|---|---|
| Procedural | Traits only. Generated names, generated content, systemic flavour. |
| Authored | Traits, plus named characters with voice sheets, a set-piece, a bespoke questline, custom art, and a full evidence pool. |

Authored galaxies must be **sharper, not smaller**. Act I is one galaxy and it cost 112,000 lines
and 2.27MB of authored JSON. Five more at that fidelity is a decade, not a plan. An authored galaxy
is one strong idea, three to five characters with real voice, one set-piece the player will describe
to someone else, and one systemic twist that changes how they play while they are there. A galaxy
built around a single strong idea is more memorable than one carrying six diffuse ones. Act I can be
the sprawling homeland precisely because it is the only one that has to be.

---

## The discovery model

The map is a **knowledge map**, not a spatial one. Every galaxy is in one of three states:

| State | What the player sees |
|---|---|
| **Unknown** | Nothing. It is not on the map. |
| **Rumored** | An unresolved marker. A bearing, a fragment of a name, a description with no location: *"somewhere coreward, a system where the war never ended."* |
| **Charted** | A real destination the player can plot a course to. |

Two layers are visible at all times: the places the player knows, and the **implications** pointing
outward into the dark. The second layer is the game.

### Fragments

A fragment is a short piece of evidence. Fragments carry different *kinds* of information: a
bearing, a distance, a trait, a name, a faction affiliation. Two fragments narrow a rumor; three
resolve it.

The intended peak experience is the player realising that a derelict log found in one corner of
space and a trader's rumor heard somewhere unrelated describe **the same place**. Nobody told them.
They worked it out. That is a categorically different feeling from clearing a checklist, and it is
why this design uses evidence rather than keys.

### Fragment sources

Discovery requires **no new mini-game**. It reuses every system already built, giving each one a
second currency:

| Source | Existing system | Skill tree |
|---|---|---|
| Derelict logs | salvage | Industry / Exploration |
| Dockside gossip | trading | Commerce / Social |
| Faction intel | politics, reputation | Leadership / Social |
| Captured manifests | piracy, combat | Combat |
| Archival research | Okafor Institute | Exploration |
| Star charts as lots | auction house | Commerce |
| Ambient leads | news ticker, travel, time | none (passive floor) |

This is the answer to "the old systems should stay relevant." They stop being only an economy and
become an intelligence network. Salvaging a wreck is no longer only credits; it is a lead.

The six skill trees are the natural lens. The character build the player already chose determines
how the universe reveals itself to them, which is a large amount of expressive power for very little
new machinery.

### Why threshold-not-set matters

If a galaxy required a derelict log **and** a trader rumor **and** a faction manifest, a pure trader
would be forced to salvage and a pirate forced to make friends. The game would be about freedom
while quietly demanding a checklist.

Any-3-of-7 removes every lockout and keeps the deduction intact. The player still assembles a place
out of pieces; they are simply never required to assemble it from *those* pieces.

A useful side effect: **how the player found a place colours what it means to them.** The pirate and
the diplomat arrive at the same system carrying different framing.

---

### Signal and noise

Decision 11 means every galaxy in the universe can produce leads, which is what keeps the seam
invisible. It also creates the one genuine risk in this design: **authored content getting lost in
procedural noise.** If a player's log fills with forty rumors of equal apparent weight, the five
places we spent months writing are needles in a haystack, and the trail stops feeling like a trail.

Three levers manage it, and they should be tuned together rather than picked from:

- **Density.** Authored galaxies carry 7 fragments; procedural ones carry far fewer. A player
  encountering repeated, independent corroboration is being told, implicitly, that something is
  there.
- **Specificity.** Procedural fragments should skew vague ("a trader mentioned good salvage two
  jumps spinward"). Authored fragments name things: a person, a ship, an event, a date.
- **Corroboration.** Only authored galaxies should produce fragments that *cross-reference each
  other* from unrelated sources. That cross-referencing is the peak experience described above, and
  reserving it for authored content makes it a reliable signal without ever being an explicit one.

The player should never be told which galaxies are authored. They should simply find that some
rumors keep getting louder.

**This needs playtesting, not theory.** The failure mode is quiet: nobody reports "the signal-to-noise
ratio is off," they just report that exploring felt aimless. Watch for players who stop pursuing
rumors, and treat that as the symptom.

## The content rule

> **No galaxy ships without a full-spectrum evidence pool.**
>
> Every authored galaxy carries **7 fragments spanning at least 4 playstyles**, any **3** of which
> resolve it.

For 5-6 authored galaxies that is roughly 40 short pieces of writing. Achievable, but it is a hard
requirement on the content template rather than something to improvise per galaxy. A galaxy that
ships with a narrow pool silently re-introduces the lockout this spec exists to prevent.

Enforcement should be a data-integrity test in the same family as the existing
`test_dialogue_integrity.py` and `test_cross_references.py`: fail the build if any authored galaxy's
evidence pool has fewer than 7 fragments or covers fewer than 4 distinct playstyles. A rule that
cannot fail is a rule that will be forgotten.

---

## The reveal

At the end of Act I the camera pulls out. The player sees an enormous field of light, hundreds of
points, unmistakably vast.

**Almost none of it is resolved.** Two or three charted neighbours, bright and legible. Everything
else is glow with no name, no distance, and no promise.

That is the vault door. Stepping out of Vault 101 does not put a marker on Megaton. It shows a shape
on the horizon and lets the player think *what is that?* The scale arrives instantly and for free;
the specifics are the next hundred hours.

Mechanically this costs a camera transition, a zoom level, and a starfield with per-galaxy visual
variance. It does not cost a hundred authored destinations. The detailed staging of this moment
belongs to the Threshold spec.

---

## Open questions

- **How many traits, and how many are needed for a galaxy to feel distinct?** Suspect 2-3 per galaxy
  from a pool of 10-15, but this needs a spike.
- **Exact procedural galaxy count.** "A few dozen" needs to become a number, ideally chosen by
  playtesting how long the trail feels good.
- **Signal-to-noise tuning.** Decision 11 is locked (procedural galaxies do generate rumors), but
  the density, specificity, and corroboration ratios that keep authored content findable are a
  playtest question, not a design-time one. See "Signal and noise."
- **Fragment persistence across the Act I destruction.** Everything the player owned is lost. Is
  knowledge lost too? Losing it is thematically strong and mechanically punishing.
- **Does the player ever exhaust the universe?** A defined ending versus an open horizon is a
  different game. Not answered here.

---

## Success criteria

1. A galaxy can be authored entirely from trait data, with no code changes.
2. A new trait can be added without touching any galaxy definition.
3. Discovery is playable end to end: a fragment found in one galaxy contributes to resolving a rumor
   about another.
4. Any 3 of a galaxy's 7 fragments resolve it, verified across at least 4 single-playstyle runs
   (pure trader, pure pirate, pure salvager, pure diplomat), none of which stall.
5. A data-integrity test fails the build when an authored galaxy's evidence pool is narrower than
   7 fragments across 4 playstyles.
6. A player who ignores discovery entirely can still play indefinitely in charted space.
7. The reveal renders at the end of Act I and is gated so it cannot be reached earlier.
