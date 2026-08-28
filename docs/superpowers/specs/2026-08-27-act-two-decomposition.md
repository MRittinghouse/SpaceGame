# Spec F decomposition — Act II ambition framework (A2 sprints)

**Source spec:** `docs/superpowers/specs/2026-08-27-act-two-ambition-design.md`
**Purpose:** fill the seven-day unattended run with work the harness can actually reach.

## Graph shape is the design constraint, not an afterthought

The current backlog is 9 levels deep with **zero dependency-free roots**, which is how one
135-byte failure in `SA-F2` stranded fifteen sprints for four months. This decomposition is
shaped against that: **3 independent roots, max depth 5, and a tier that is 8 sprints wide.**

If any single A2 sprint blocks, the most it can strand is its own subtree. The eight
dilemmas in Tier 3 are siblings — none depends on another, so a bad night on D2 does not
touch D4.

---

## Tier 0 — roots (no dependencies; all three eligible immediately)

**A2-1 — Lens data model and registry**
`spacegame/models/lens.py`, data at `data/narrative/lenses.json`, `DataLoader._parse_lenses()`.
Satisfies criterion 1: a lens is addable as data with no code change. Includes the
data-integrity test that fails the build on a malformed lens, on the existing
findings-register / evidence-pool guard pattern.

**A2-2 — Lens authoring guide** (docs only, no code)
Extends the writing bible: per-lens voice, NPC construction patterns, how a location gets a
per-lens reading. This is what later content sprints read from, so it must exist before
them, but it depends on nothing.

**A2-3 — Capstone format and hook contract** (data format only, no authored content)
Defines what a capstone *is* as data and where it fires. No cutscenes written here.

## Tier 1 — depends on A2-1

- **A2-4 — Investment tracking** — per-lens, save/load round-trip. Criteria 3 and 6.
- **A2-5 — Lens definitions 1-8** (Vengeance, Wealth, Political Power, Exploration, Discovery, Justice, Crime, Revolution)
- **A2-6 — Lens definitions 9-16** (Empire, Community, Legacy, Faith, Transcendence, Connection, Truth, Preservation)
- **A2-7 — Per-lens readings on locations** — criterion 2: a new authored location takes per-lens readings without touching lens or dilemma code.

> `minigame_shape` is a **required data field** on every lens, guarded by A2-1's integrity
> test. The 16 mini-game *implementations* are explicitly NOT in this arc — they are the
> single largest downstream body of work and belong in their own spec. Declaring the shape
> now is what stops a lens shipping as a reskin later.

## Tier 2 — the dilemma engine

- **A2-8 — Dilemma model + threshold collision** (deps A2-4) — fires only when BOTH poles exceed threshold. Criterion 4.
- **A2-9 — `tier_unlocks` integrity guard** (deps A2-8) — criterion 5. Build fails if any dilemma outcome lacks one. This is what keeps closure a trade rather than a subtraction.
- **A2-10 — Permanent closure + save/load** (deps A2-8) — criterion 6: reloading a later save cannot reopen a closed path.
- **A2-11 — Scars** (deps A2-10) — criterion 7: the refusing NPC still exists and is occasionally seen doing the work you did not.

## Tier 3 — the eight dilemmas (deps A2-9 + A2-10; siblings, mutually independent)

Authored in the spec's own priority order:

| Sprint | Dilemma | Why this position |
|---|---|---|
| **A2-12** | D4 Truth ↔ Vengeance | Spec says author FIRST. Reaches back into Act I; one revelation recolours forty hours retroactively. Highest narrative return in the document. |
| **A2-13** | D2 Wealth ↔ Community | The emotional centre. Same childhood wound, opposite conclusions. |
| **A2-14** | D1 Vengeance ↔ Justice | Personal against ideological. |
| **A2-15** | D3 Power ↔ Revolution ↔ Empire | Triangle, resolves to one of three. |
| **A2-16** | D5 Legacy ↔ Connection | |
| **A2-17** | D6 Preservation ↔ Empire | |
| **A2-18** | D7 Faith ↔ Transcendence | |
| **A2-19** | D8 Crime ↔ Community | |

Each carries all four required parts: telegraph, collision, visible cost, tier unlock.

## Tier 4

- **A2-20 — Capstones fire without ending the session** (deps A2-10, A2-3) — criterion 8.
- **A2-21 — Post-capstone generation keyed to resolved identity** (deps A2-20) — criterion 9. The resolved identity becomes the content generator.

---

## Four open questions that will stall agents mid-week

The spec leaves these unresolved. Agents will hit them and cannot ask. Recommended defaults
below so the week proceeds either way.

**Q1 — How is investment surfaced? — DECIDED: fully oblique, no panel.**
The world's behaviour is the only signal. How NPCs address you and what work you are offered
*is* the readout. No meter, no bar, no worded summary panel.

Criterion 3 still holds but must be restated to stay testable: investment is tracked and
persists, and is observable **through NPC address and offered work**. The scenario test
asserts that driving one lens high measurably changes what NPCs say and what work appears —
not that a UI element exists.

**Q2 — Can a dilemma be declined? — DECIDED: no. The player chooses when it fires.**
No deferral path. A collision resolves at the moment it occurs.

### Consequence of Q1 + Q2 together — the telegraph is now the whole safety net

Individually each choice is fine. Together they remove *every* warning channel except one:
the player gets no numeric read on their investment, and no option to stall once the
collision lands. The telegraph — a character who tells them plainly, in advance, that they
cannot keep doing both — stops being "a hard requirement, not polish" and becomes **the
single point of failure for the entire mechanic**. If it misfires, permanent closure lands
as an ambush, which is the exact resentment the spec names as a top risk.

So the telegraph gets promoted from authored content to an enforced invariant:

1. **It must fire before the collision can.** Every dilemma declares a telegraph threshold
   strictly below its collision threshold. **A2-9's integrity guard is extended to fail the
   build on any dilemma where `telegraph_threshold >= collision_threshold`** — same pattern
   as `tier_unlocks`.
2. **It must be unmissable.** Delivery cannot depend on the player choosing to talk to
   someone or lingering in a location. A2-8 owns guaranteed delivery.
3. **It must persist.** Ignored once, the world keeps signalling — repeated approaches from
   the telegraphing character as investment climbs, rather than one line that can be walked
   past.

A2-8 and A2-9 carry these; no new sprint needed.

**Q3 — How many capstones? — DECIDED: no hard cap; the dilemma graph enforces it.**
Eight dilemmas each permanently close a lens, so at least eight of sixteen close over a full
run and a completionist mathematically cannot collect all sixteen. No arbitrary number, no
new mechanic, and a limit the player can feel the reason for.

**Q4 — Does Act I need retrofitting?**
*Recommend:* minimal seeding only. Act I sets the evidence flags D4 depends on and nothing
else. No investment tracking or lens UI in Act I. Keeps the retrofit to one dilemma's
prerequisites instead of reopening finished content.
