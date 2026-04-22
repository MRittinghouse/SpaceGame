# QA Pass 6 — Narrative Tutorial Polish

Generated 2026-04-21. Pre-playtest content pass. Rewrote all tutorials to be narrative-integrated with the established backstory (orphaned child of a mining-rig foreman, scrapyard shuttle build, 4,000 credits, setting off from the Nexus Prime colony ship). Replaces 4th-wall-breaking "You are a trader in a galaxy of opportunity" framing with internal second-person voice that builds on the `intro_narration` dialogue.

**Bottom line:** All tutorials rewritten. +15 new regression tests (writing-bible compliance + narrative-thread presence). 1 existing test adjusted for new title. Test count 7,086 → 7,101. Playtesters will encounter a cohesive voice from the opening narration through every tutorial moment.

---

## What was broken

The opening narration (dialogue `intro_narration`, 5 nodes in `data/dialogue/dialogues.json`) establishes a specific protagonist: assistant foreman's child, 16 years old, orphaned six months ago by air-recycler failure in the colony ship's mining rig. Spent last credits on a broken shuttle. "Woefully unaware of the system, its politics, its people."

Then the player transitioned to tutorials that opened with:

> **"Welcome to Aurelia! You are a trader in a galaxy of opportunity. Your goal is to buy low, sell high, and build your fortune."**

Every hint continued in that voice — "Your Momentum gauge builds as you fight. Dealing damage, taking hits..." The tutorials taught systems competently but flattened the character's specificity into a generic player identity. The user's diagnosis: "I want tutorials to feel like they meaningfully weave into our campaign and universe."

## What shipped

### `TUTORIAL_STEPS` rewrite — 5 steps

Each step preserves its trigger (so the game-loop firing logic is unchanged) and its position in the learning arc, but speaks in the protagonist's internal voice and references the established backstory.

| Step | Old title | New title | Core narrative move |
|---|---|---|---|
| 0 | Welcome to Aurelia! | The Map | Father worked rigs in three systems on paper, saw only one in person. Two jumps of fuel. |
| 1 | Trading Basics | The Markets | Trading posts look like colony-ship posts. Math isn't hard; waiting is. |
| 2 | Traveling the Galaxy | The Fuel Bill | First profit went to fuel cells. Father's advice: "Plan twice, move once." "He didn't always follow his own advice." |
| 3 | Activities: Mining, Salvage & Refining | The Sidework | Father pulled mining shifts his whole adult life. Loud work. Dangerous. Honest. |
| 4 | Your Journey Ahead | The Long Haul | Some systems might tell you who buried your father's report. "First you need credits. Then you need friends. Then you need leverage." |

### `MINIGAME_HINTS` rewrite — 14 entries

Each hint now opens with a voice hook instead of a directive:

- **Mining: "The Drill Line"** — "Your father could read a rock face by the dust it threw. You don't have that yet. You will."
- **Salvage: "The Wreck"** — "Everything you see here was someone's bad day."
- **Refining: "The Crucible"** — "Raw metals pay less than finished parts. That's not philosophy, that's margin."
- **Combat (5 hints)** — momentum ("you feel the fight settle into rhythm"), crew combo ("your crew works better together than apart — not a metaphor, mechanics"), ultimate ("pick your moment"), boss ("fight them slow, fight them patient"), elemental ("pack for the fight you expect").
- **Defensive identity** — "Play the identity your ship actually has, not the one you wanted."
- **Builder (8 hints)** — the Drydock as a working shipyard voice: "The grid doesn't judge. That's what the stats panel is for." / "A bad center of mass in the builder is a worse one in combat."

All prior mechanical information preserved; only the framing changed. Key bindings, button labels, stat names, thresholds all still surface where needed.

### `TutorialShopView` mechanic dialogue polish

The scrapyard mechanic's voice was already strong (pre-existing: "Cockpit. Unless you plan to steer from outside." / "Reactor. Most of your budget. Power isn't cheap."). One addition: the closing line after the player completes the build now reinforces the father thread.

**Before:** "That'll do. Head to the build bay and bolt it all together."

**After:** "That'll do. Head to the build bay and bolt it all together. Your old man would have liked this build. Careful kid. Too careful, maybe. That's how he was when I knew him."

This anchors the mechanic as a person who knew the father — consistent with the intro narration's mention of "a neighbor in maintenance helps you source an engine." It's the last thing the player hears before leaving for the real game, and it lands with human weight rather than a rank-title sign-off.

Also killed a stray "Captain" fallback line that broke voice (the player isn't Captain-of-anything yet).

### Regression tests — 15 new

Grouped into 6 classes in `tests/test_models/test_tutorial_narrative_voice.py`:

1. **Writing Bible compliance** (2 tests) — no em-dashes, no "couldn't help but", no "a testament to", no "no X, no Y" constructions in any tutorial string we own.
2. **Tutorial step contract** (4 tests) — exactly 5 steps, required keys present, canonical trigger set intact, 40–120 words per step body.
3. **Narrative threads present** (3 tests) — father mentioned in both TUTORIAL_STEPS and MINIGAME_HINTS["mining"]; fuel-as-economic-constraint surfaces in trading/map flow. These guard against a future edit accidentally stripping the emotional framing back to generic text.
4. **No legacy trader identity** (2 tests) — Step 0's title isn't "Welcome to Aurelia!"; Step 0's body doesn't contain "you are a trader" or "galaxy of opportunity". Regression-proofs the rewrite.
5. **Minigame hint inventory** (3 tests) — all 18 expected hint keys still present; each has title+description; 30–150 words per body.
6. **TutorialShop mechanic voice** (1 test) — reads the view module source and confirms the new closing-line phrasing is present. Guards against accidental revert during future edits.

## Voice design decisions (for reference)

**POV**: Second-person internal. "You feel the fight settle." "Your first profit." Lets the mechanical facts land as realizations rather than instructions.

**Register**: Working-class. Short sentences. Dry humor ("Loud work. Dangerous. Honest.") instead of whimsical or academic voice. Matches the Nexus Prime station atmosphere and the Miners Union faction voice sheet in `character_voices.md`.

**Character anchoring**: Every reference to the father keeps him present but doesn't glorify him. "He didn't always follow his own advice." "Your father would have liked this build. Careful kid. Too careful, maybe." Real grief, not sainted grief.

**Mechanical facts in-place**: Every tutorial still lists the actual mechanics — key bindings, thresholds, slot requirements, stack math. The narrative voice wraps the facts rather than replacing them. Players who want to skim still get what they need.

**What's intentionally NOT in these rewrites**:
- New mechanics
- New NPCs
- New dialogue trees
- New game states

The scope discipline was: reframe the words we already show, keep everything else identical. Mechanism changes would belong in a separate session where playtest-informed decisions can shape them.

## Pre-playtest readiness

Combined with the prior QA wrap-up:

- 7,101 tests passing (was 7,086 — +15 from this pass)
- 2 intentionally skipped (placeholder scenarios awaiting combat-balance authoring)
- Zero flakes (parallel + sequential both green on first run)
- Zero TODO markers in source
- All lint clean on touched files
- Narrative tutorial voice locked with compliance tests

Ready for playtest.
