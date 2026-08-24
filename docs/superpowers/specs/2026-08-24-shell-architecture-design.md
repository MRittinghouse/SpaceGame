# Spec B — Shell Architecture (rescoped)

**Date**: 2026-08-24
**Status**: draft, pending review
**Arc**: SH (Shell)
**Follows**: Spec A (Quality Foundation) — complete, all 10 QF sprints done
**Supersedes**: the original "decompose `game.py` into a scene stack" framing

---

## Why this spec exists, and why it is much smaller than first proposed

`spacegame/engine/game.py` is 6,564 lines. It contains a 1,197-line
`_handle_state_transitions` method with 185 branches, a 57-attribute
constructor, and 30 `_ensure_*_view` methods managing 40 view classes across 41
`GameState` values.

I have argued two different positions about this file and both were wrong.

**First position: decompose it, because it taxes every new feature.** Measured,
that is not true. One new view costs roughly **45 lines inside `game.py`** (a
median-16-line `_ensure_*_view`, plus ~29 lines of dispatcher branches at 1,197
lines / 41 states) against ~1,130 LOC for the view file itself. About **4%
overhead**. The Act II vision adds perhaps 5-6 new views, so decomposition buys
around 270 lines across the entire second half of the game. The earlier claim
that it would make the remaining game "dramatically cheaper" was asserted, not
measured.

**Second position: drop it, since remaining work is mostly JSON content.** Also
wrong, because the case never rested on velocity.

**The measured case, after Spec A completed:**

| | |
|---|---|
| `game.py` share of `spacegame/` LOC | **5.9%** |
| `game.py` share of all remaining mypy errors (338 of 427) | **79%** |
| `game.py` share of remaining **crash-class** errors (103 of 103) | **100%** |

Spec A drove Population A to zero everywhere else in the codebase. **Every
remaining way this game can crash from a null-access defect now lives in this
one file.** Both crashes the 2026-05-05 playtest reported routed through it.

There is a second argument worth weighting given how this project is built: a
6,564-line file containing a 1,197-line method is hard for an *agent* to edit
safely. Every QF sprint deliberately routed around it. That constraint gets
more expensive the longer it stands.

So Spec B is justified as **stability and agent-effectiveness**, not velocity,
and its scope shrinks accordingly.

## What this spec is NOT

**Not a scene-stack rewrite.** A declarative scene system with automatic view
lifecycle is what you build when adding twenty activity types. Aurelia is adding
five or six. Buying that architecture now means funding a months-long refactor
whose main justification does not hold.

**Not a `_ensure_*_view` cleanup.** Thirty methods averaging 22 lines (673 LOC
total) is unglamorous and harmless. Leave them.

---

## Scope

### SH-1 — `Game.player` accessor (64 of 103 crash-class errors, one pattern)

`Game.player` is `Optional[Player]` because no player exists until
`initialize_new_game()`. Every downstream access is therefore an unguarded
`union-attr`, and there are **64 of them** — 62% of everything left.

QF-8 already solved this exact shape and documented it in
`docs/qf/accessor_pattern.md`, which explicitly names itself *"the model for
Spec B's `Game.player`"*. The recipe is proven on five view classes:

```python
self._player: Optional[Player] = None

@property
def player(self) -> Player:
    if self._player is None:
        raise RuntimeError(
            "Game.player accessed before initialize_new_game(); "
            "the player is created there and cleared on return to main menu."
        )
    return self._player
```

Critically, this does **not** introduce new crashes. `self.player.credits` with
`player` as `None` already raises `AttributeError`. The accessor replaces a
cryptic failure with a diagnostic one that names the lifecycle violation. QF-8
verified this empirically: after rewriting five view classes, a 2,400-action
crawl across the trading, salvage, mining and refining paths fired zero
accessors.

Remaining after SH-1: 39 crash-class errors across `MissionManager | None` (3),
`MiningConfig | None` (3), `SalvageConfig | None` (2), and a long tail.

### SH-2 — Split `_handle_state_transitions`

1,197 lines, 185 branches, 66 nested function definitions, one method. This is
where combinatorial state bugs are born and it is the single hardest thing in
the codebase for a human or an agent to reason about.

Split by arc or by state group into focused handlers with a thin dispatcher.
This is mechanical, bounded, and fully covered by the existing suite — the same
shape as QF-5's `Game.step()` extraction, which landed clean.

**Move code. Change nothing else.** No behaviour changes, no drive-by fixes, no
restructuring of the event cascade. If the split cannot be done without
behaviour change, stop and report rather than improvising.

### SH-3 — Remaining `game.py` crash-class errors

Whatever survives SH-1, by root-cause cluster rather than error by error, using
the same accessor pattern where lifetime is bounded and local guards where it
genuinely is not.

---

## Success criteria

1. `scripts/mypy_populations.py` reports **Population A = 0 including
   `game.py`**, and the game.py exclusion is removed from the metric with its
   justification comment deleted rather than left misleading.
2. `_handle_state_transitions` is under 200 lines; no resulting handler exceeds
   250.
3. No behaviour change: full suite green throughout, at or above 10,559 passing.
4. The crawler runs a 2,000-action session from the `late` checkpoint with zero
   new crashes and zero raising-accessor failures — the same independent check
   that verified QF-8, exercising live state paths rather than pytest.
5. No `# type: ignore` added without a one-line justification.
6. `game.py` total error count falls materially from 338; the arc is not
   considered done while it holds 79% of the project's remaining errors.

## Risks

- **`Game.player` has a genuinely nullable window.** Unlike a view's
  `on_enter`/`on_exit` pair, the player is absent at main menu and during
  character creation. Any code path legitimately running there needs a local
  guard, not the accessor. SH-1 must identify those paths first rather than
  applying the property blindly.
- **The dispatcher split will surface latent bugs.** 185 branches accumulated
  over years almost certainly contain unreachable and duplicated cases.
  Discovering them is a benefit, but it will make SH-2 feel larger than "move
  code" suggests. Record what is found; do not fix it inside SH-2.
- **Sequencing.** SH-1 before SH-2. Fixing types in a file mid-restructure means
  resolving conflicts against yourself, and SH-1 is where most of the value is.

## Open question

Whether `game.py` should end up smaller in absolute terms, or merely
comprehensible. This spec targets the second. If the file is still ~6,000 lines
afterwards but no method exceeds 250 and the crash-class count is zero, that is
success. Shrinking it further is a different project and needs its own
justification, measured rather than asserted.
