# Agent Principles — How to Work on Aurelia

Meta-preferences for any agent (or human) working on this project. Read this in full before any phase. These principles are distilled from accumulated decisions and corrections; they exist because following them avoids the most common failure modes on this codebase.

`CLAUDE.md` covers project conventions (style, layout, architecture). `requirements/roadmap/AGENT_GUIDE.md` covers the harness loop mechanics. **This doc is about judgment** — how to decide what to do when the spec doesn't decide for you.

---

## Honesty over politeness

The single most common failure mode in autonomous agent work is rubber-stamping. **The reviewer's job is to find issues the implementer missed, not to confirm the implementer's confidence.** Three concrete findings beat ten vague ones. If you accept work, accept it because it's actually good — not because the implementer's commits look thorough.

This applies to plan and implement phases too. If the sprint's premise feels off, say so. Set `PHASE_BLOCKED` with a clear reason rather than planning around a flawed brief.

## Block early when scope is ambiguous

`PHASE_BLOCKED` is the right call when the premise is unclear, when a context doc is missing, when a spec contradicts itself, or when the work would require a decision you can't make alone. **Do not guess your way through ambiguity** — guesses produce sprints that look done but break in unexpected places.

The harness has a rework cycle for "implementation needs more work." It does not have a recovery for "the plan was based on a guess." Block early, surface the question, let a human (or a later agent with more context) make the call.

## Scope discipline

Don't add features beyond the sprint's acceptance criteria. **A bug fix doesn't need surrounding cleanup. A one-shot operation doesn't need a helper. Three similar lines is better than a premature abstraction.** If you notice an unrelated issue while working, log it in the sprint's Activity log as a follow-up suggestion. Do not expand scope.

The reviewer should call this out: an implementer who shipped the spec plus three unrelated improvements has not shipped the spec. They've shipped four things, and the three extras weren't reviewed against acceptance criteria.

## Real engineering depth, not surface fixes

If a test fails, find the root cause. Don't add a try/except to make the symptom go away. Don't widen a type to suppress a MyPy error. Don't add a guard that papers over an invariant violation.

Aurelia code is built on the assumption that if the test passes, the underlying behavior is correct. That assumption is only true if the implementer fixed the actual bug, not the test's complaint about it.

## Don't add error handling for impossible cases

Trust internal code. Trust framework guarantees. Validate at boundaries (user input, JSON loads, external APIs). **Do not add try/except blocks for cases that can't happen** — they obscure real failure modes by making every failure look like a recoverable error.

If you find yourself thinking "but what if this returns None?" and the answer is "it can't, the upstream code guarantees it," don't add the None check. Add a comment if the invariant is non-obvious. That's it.

## Comments only for WHY, not WHAT

Well-named code already explains what. **Only add a comment when the WHY is non-obvious**: a hidden constraint, a subtle invariant, a workaround for a specific bug, behavior that would surprise a reader. If removing the comment wouldn't confuse a future reader, don't write it.

Never write multi-paragraph docstrings or multi-line comment blocks. One short line max. Don't reference the current task, fix, or callers ("used by X," "added for the Y flow," "handles the case from issue #123") — those belong in the commit message and rot as the codebase evolves.

## No backwards-compatibility hacks unless required

Don't keep dead code "just in case." Don't rename unused vars to `_var`. Don't leave `# removed` comments where deleted code used to be. **If something is unused, delete it.** If a public API needs to change, change it and update the callers.

Save migration is the one exception: `from_dict` must handle missing keys with sensible defaults so old saves don't crash. That's not a backwards-compat hack; that's the save system contract.

## TDD discipline

Failing test first. Always. **The test should fail in the way you expect** (the right assertion message, the right line). If a test passes the moment you write it, you wrote a test for behavior that already exists, not for the new behavior.

Test both success and failure paths for any operation that returns `tuple[bool, str]`. Test edge cases: zero values, max capacity, empty collections, missing dependencies.

## Voice-check player-facing content

Anything the player will read — dialogue, missions, journals, UI strings, ambient lines, tutorial copy — must pass the Writing Bible scanner AND the voice-check in `requirements/aurelia_voice_examples.md`. **The scanner is the floor; the examples doc is the standard.**

If you write a line that sounds slightly off but you can't name why, copy a paired example from `aurelia_voice_examples.md` and rewrite in that register. Do not ship "passable" voice on player-facing content. Voice is the most visible quality dimension of this game.

## Variety across a cast

When a single sprint authors multiple NPCs, the work that survives isn't just "are the individual voices good" — it's "does the set have range." A previous sprint shipped five new specialists who were each internally well-written but shared a single register (professional, methodological, cataloguer's eye). Internally coherent; as a set, monotone.

The aim is **variety, not archetypes.** Resist both the failure mode where every character in a sprint speaks with the same tonal default AND the opposite failure of mechanical archetype-checking ("did we cover the warm one, the anxious one, the reckless one?"). Aurelia's universe is rewarded by characters who are specifically, irreducibly themselves — not characters who fill slots. A cast of five people from broadly similar backgrounds can feel varied if each carries something the others don't, and a cast that mechanically distributes "temperaments" can still feel canned.

The dimensions of variety are wider than temperament. Some that work:
- A relationship that shapes their speech (someone who lost a partner two years ago talks differently than someone who didn't)
- A craft register from outside their current role (a former teacher who became a broker still teaches when they explain)
- A learned silence (someone who knows when not to speak, in contrast to characters who narrate)
- A regional cadence (Verdant rhythm vs. Reach rhythm vs. Forgeworks clip)
- A contradiction the character has learned to carry (the gentlest voice in the cast is also the most uncompromising)
- A specific obsession or unfinished business that surfaces in unexpected moments
- A way of handling silence, or of refusing to fill it
- An unfashionable belief held with conviction
- Humor of a particular shape — wry, self-deprecating, sharp at others' expense, dry under pressure

Think of it as a **standard curve with deliberate outliers.** Most working-class NPCs will use grounded specific speech; most professionals will speak more precisely. That curve exists and it's fine. The point is to reach past it sometimes, where a character's history or role earns it. A cast where every voice is on the curve reads as monotonous. A cast where every voice tries hard to break the curve reads as forced. The right shape is most-on-curve with a few real outliers, and the outliers feel earned by who the character is, not by a quota.

When you finish drafting a multi-NPC sprint, read the cast aloud as a set. If two or three voices feel interchangeable once you cover the names, that's the alarm. The fix is rarely "swap one for a different archetype"; it's "give one of them something specific that nobody else in the cast has." Document a one-line note in the sprint's Activity log on what makes each voice non-substitutable. If you can't write that note, the voices are too close.

Be brave about depth. The fear of "too quirky" produces flatter casts than the fear of "too generic." Lean toward the specific.

## Don't over-defend the design in review

When reviewing, avoid the failure mode of "this looks fine because I can rationalize each pattern as intentional." The reviewer's job is to push, not to defend. If a foundational module has zero findings across hundreds of lines, the reviewer didn't read carefully enough.

A useful framing: **identify the single thing you would tighten if you were going to tighten one thing.** Even if you accept the work as-is, naming that thing keeps the review from rubber-stamping. If you genuinely cannot identify one, say so explicitly with a one-line diagnostic of why ("module is small and the pattern matches established X").

## Pre-existing failures aren't yours

If the test baseline shows pre-existing failures or skips, they're not your problem to fix unless your work made them worse. **Don't try to fix the world; just don't regress it.** Your acceptance bar is "pass count ≥ baseline."

If you discover a pre-existing bug while working, log it in the sprint's Activity log as a follow-up. The harness has a `Followups` section in the Last phase report block exactly for this.

## One thing at a time

If you're refactoring, refactor. If you're fixing a bug, fix the bug. **Don't bundle a refactor into a bug fix commit** — it makes the bug fix unreviewable and harder to revert if the refactor broke something subtle.

Smaller commits over larger ones, when convenient for recovery. If the harness crashes mid-sprint, smaller commits make it easier to see what landed.

## Composition over inheritance

Aurelia models follow the pattern: Player has Ship, Ship has ShipType, Player has Progression. If you're tempted to subclass, ask whether composition would do the same job with less coupling. Almost always, yes.

## Models contain logic, not just data

Models are `@dataclass` — but they're not data containers. **Operations that can fail return `tuple[bool, str]`** (success, message). Computed values are `@property`, not stored. Models never import from `views/` or `engine/` — dependency flows inward.

If a method on a model crosses into rendering, particle effects, or sound, it belongs in a view, not the model.

## DataLoader is a singleton

Always `get_data_loader()`, never `DataLoader()`. The singleton holds all the JSON content; constructing a fresh one re-parses everything and breaks identity assumptions in tests.

## Use the harness contract

- **Sentinel + structured report** at the end of every phase. The harness reads them.
- **Don't push** — the harness pushes after a sprint completes.
- **Touch zones limit your edit scope** — the harness will revert out-of-scope edits and mark the sprint blocked.
- **Use rework over half-shipping.** If implement is partial, set `PHASE_NEEDS_REWORK` rather than calling it done. The next implement pass picks up where you left off.
- **Reference the sprint ID in every commit message.** The harness uses commit messages to verify work happened.

---

## When in doubt

Default to: less code, less commentary, more honesty in reviews, more specific in voice. **The Aurelia codebase rewards restraint and punishes over-engineering.** If a phase feels like it should produce a thousand lines of new code, it probably shouldn't. If a review feels like it should rubber-stamp, it definitely shouldn't.

The user (Matt) prefers pragmatic engineering with real depth over thorough engineering with surface polish. Match that disposition.
