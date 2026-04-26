# Investment Rewards Design — Aurelia: A Ledger of Stars

**Status**: stub, 2026-04-26. Not scoped, not sprinted. Placeholder so the design thread doesn't fall off.

**Origin**: `requirements/station_legibility.md` Lever 4.5. Playtester feedback flagged that the investment system "feels niche, flat" — and the Station Legibility roadmap (SL-1 through SL-5) addresses *when* the player encounters investment, not whether the encounter itself is satisfying. This doc is where the satisfaction work eventually lives.

---

## Problem

Investment cards exist on 10 of 11 stations. Each lets the player commit capital to a station-themed venture (mining rig, hydroponics co-op, salvage crew, research grant, etc.) for passive returns over time. The system is functional but sits in a dead zone: returns are slow enough to disengage attention, outcomes don't intersect with other systems, and there's no narrative texture around outcomes.

A player who unlocks investment per the SL-2 gate (25,000 CR threshold + Cargo Broker mission) can engage with it. Whether they *want* to is the question this doc will answer.

---

## Open threads (raw, not yet scoped)

These are placeholder hooks from the SL doc's Lever 4.5. Each needs design work.

- **Pacing**: returns are too slow to register as exciting. Faster initial dividend? "Your X earned Y while you were away" notification on next dock?
- **Cross-system intersection**: today's investments yield credits. What if a Breakstone Mining Rig investment yielded raw ore directly to cargo, converting investment into an alternate income channel that intersects with trading?
- **Narrative beats**: a successful Verdant Co-op investment could trigger a small NPC moment next visit ("the harvest paid out — here's your share, try the cider"). Aurelia's "people not menus" principle. Each station's investment could carry a per-station NPC tied to outcomes.
- **Risk dimension**: all current investments yield positive returns. Adding occasional setbacks (a salvage crew gets jumped, a mining rig fails) makes the system feel alive. Skill-tree investments in social/leadership get a place to matter (pre-empting setbacks via reputation, mediating disputes via Charisma checks).
- **Tier visibility**: are investments worth comparing against each other? A player should be able to see "this station's investment is best for me right now" via some visible heuristic (faction reputation, ship build, current cargo, current credits).

---

## What this doc is not

- Not committed work. SL-1 through SL-5 ship before this gets scoped.
- Not a critique of the existing investment implementation. The current system is functional infrastructure; what's missing is satisfaction. Different problem.
- Not a promise this happens at all. If playtesters tell us, after SL-1 through SL-5 land, that investment now feels fine in context, this stays a stub forever.

---

## Sister docs

- `requirements/station_legibility.md` — gating and salience for investment cards (SL-2). The "when does the player see it?" half of the problem.
- `requirements/onboarding_design.md` — six principles. Whatever this doc proposes inherits them.
