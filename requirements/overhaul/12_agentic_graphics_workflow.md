# Agentic Graphics Workflow

> **Status:** DESIGN — novel territory with limited precedent. First-principles design, to be revised as we live inside the methodology.
>
> Defines how a human and AI coding agent (Claude) collaborate to produce visual assets at a pace that justifies the no-AI-image-gen constraint. Focuses on the iteration loop, the feedback mechanisms, the tooling stack, and the honest boundaries of what the agent can and can't do.

---

## 1. Why This Doc Exists

The overhaul commits to two constraints that pull in opposite directions:

1. **No AI-generated visual assets** (audience rejection risk).
2. **Pace compatible with solo-dev-plus-agent production** (the whole game must ship).

These constraints are only reconcilable if the agent's work is concentrated on **code that generates assets** rather than assets themselves. That is: the agent writes procedural rendering code, iterates it against visual criteria, and produces the visual output *as a deterministic function of that code*. No neural-network pixel synthesis at any stage.

This is genuinely new territory. There's no strong precedent for "AI coding agent iterates visual-procedural code against aesthetic targets." This doc is first-principles — we'll revise as we live inside the methodology.

---

## 2. What Makes Agentic Visual Work Different

### 2.1 From regular agentic coding

Normal coding work has a fast feedback loop: write code, run tests, fix failures, done. The loop is tight because the spec is a test file — mechanical, objective.

Visual work has a slow feedback loop because **the spec is aesthetic intent**, which the agent can't directly perceive. The agent writes rendering code, but can't *see* what it produces. A human in the loop is required.

### 2.2 From traditional visual design

Traditional visual design happens in a canvas tool (Aseprite, Inkscape, Photoshop) where the artist directly manipulates pixels/vectors. Feedback is instant and continuous.

The agentic workflow replaces the canvas with **code that produces pixels/vectors**. Feedback is discrete and mediated — a render cycle must complete, a human must observe, critique must be verbalized.

### 2.3 The design problem

How do we minimize the per-iteration cycle time without sacrificing quality? How do we automate critique where possible and efficient-handle where it can't be?

---

## 3. The Iteration Loop

### 3.1 The naive loop (baseline)

```
1. Human: write a task description ("render module X with manufacturer Y profile")
2. Agent:  write rendering code
3. Human:  run the code
4. Human:  capture the output (screenshot, PNG)
5. Human:  describe what's wrong to agent (free-form)
6. Agent:  revise code
7. GOTO 3
```

**Bottlenecks in the naive loop:**
- Step 4: capturing output is a context-switch (run script → navigate to output → screenshot)
- Step 5: describing visual problems in prose is lossy and slow
- Step 7: agent lacks persistent memory of what was tried — may re-suggest previously-failed approaches

**Expected naive cycle time: 2–5 minutes per iteration.** For a visual task requiring 10 iterations, that's 20-50 minutes. Acceptable for hero assets; too slow for 40 modules + 8 ships + UI chrome.

### 3.2 The tightened loop (target)

```
1. Human: specify task + style anchor (references aesthetic bible section, provides 1-2 reference screenshots if available)
2. Agent:  write rendering code AND visual-critique tests (palette compliance, silhouette, contrast)
3. Agent:  run critique tests automatically, report results to human
4. Human:  if tests pass → run code, glance at output, approve OR provide targeted critique (structured)
5. Agent:  revise code based on both automated test failures AND human structured critique
6. GOTO 3
```

**Target cycle time: 30-90 seconds per iteration.** Achieved through:
- Automated critique tests that catch ~60% of issues without human observation
- Structured critique templates that are faster to fill than free-form prose
- Style anchor that reduces the agent's "what does this world look like?" re-derivation each session
- Persistent memory via the aesthetic bible + per-task reference files

### 3.3 What makes the loop fast

Four disciplines, each essential:

**A. Automated visual critique.** Some aspects of "is this asset good?" can be tested programmatically. Palette compliance, silhouette readability, contrast ratios, alpha coverage — all can be asserted by code that the agent runs before asking the human to observe. When a critique test fails, the agent revises without human attention.

**B. Structured human critique.** When human observation is required, the critique template is fixed: *[dimension] → [observation] → [desired change]*. The human fills it out in 15 seconds; the agent receives unambiguous signal.

**C. Persistent reference.** The aesthetic bible is mandatory reading at session start. The agent sessions don't re-derive "what does this game look like?" — it's handed to them.

**D. Batch hypothesis testing.** When agent uncertain which of N approaches is right, produce all N in parallel. Human picks in one glance. Instead of 5 serial iterations testing hypotheses one at a time: 1 iteration producing 5 variants, human picks one.

### 3.4 Task archetypes

Not every visual task has the same loop shape. We identify three archetypes with tailored workflows:

**Archetype 1: Constrained parametric (fast iteration, automated critique dominates)**

Example: render module variants for a new manufacturer. The style is highly constrained (the manufacturer profile already exists), and success is mostly measurable (palette compliance, silhouette vs. other manufacturers, detail density).

Workflow: agent produces + critique-tests + human rubber-stamps. 5-15 iterations, 20-40 minutes.

**Archetype 2: Novel aesthetic (slow iteration, human critique dominates)**

Example: design the post-processing signature look. No established reference — we're deciding "what does Aurelia feel like?" via sampling. Success is subjective judgment.

Workflow: agent produces variants in batches of 3-4; human selects; agent refines in the chosen direction. 3-5 batches = 10-20 iterations.

**Archetype 3: Adaptive polish (mixed, fast when specific, slow when vibes)**

Example: tune weapon VFX after it's "working" — make it feel heavier, more satisfying. Spec is partly objective (particle count, screen shake amplitude) and partly aesthetic (does it *feel* heavy?).

Workflow: agent makes a specific adjustment based on human structured critique; human observes; repeat. 10-20 iterations spread over time (not one session).

---

## 4. The Visual Critique Harness

The automated critique layer. Built as a test suite in `tests/visual/`. Runs in CI and on-demand by the agent.

### 4.1 Critique dimensions (automated)

Each dimension has a test-suite function that returns pass/fail + diagnostic.

**Palette compliance**

```python
def test_palette_compliance(surface, palette, tolerance=8, min_pct=0.95):
    """≥95% of opaque pixels within `tolerance` units of a palette color."""
```

**Silhouette readability**

```python
def test_silhouette_readability(surface, background_color, min_edge_contrast=30):
    """Edge pixels have perceptual contrast ≥ threshold vs the declared background."""
```

**Alpha discipline**

```python
def test_alpha_discipline(surface):
    """No halfway-alpha pixels outside the expected antialiasing zones (no accidental transparency)."""
```

**Dimension bounds**

```python
def test_dimension_bounds(surface, expected_bbox):
    """Rendered content stays within declared bounding box; no overflow."""
```

**Contrast ratio (for UI)**

```python
def test_contrast_ratio(text_color, bg_color, min_ratio=4.5):
    """WCAG AA contrast ratio for accessibility."""
```

**Determinism**

```python
def test_determinism(render_fn, **kwargs):
    """Same inputs produce byte-identical output. Hash comparison."""
```

### 4.2 Critique dimensions (semi-automated, model-assisted)

These require a more sophisticated analysis but can still run without human attention. Each uses a lightweight heuristic or a vision model (if available):

**Composition balance**

A rendered image should have balanced visual weight. Compute center-of-mass of non-transparent pixels; assert it's near the image center. Catches "everything's off to one side" accidents.

**Color temperature consistency**

Compute mean color temperature across the image; flag if it's outside the expected range for the scene (combat = cool; station hub = warm).

**Detail density**

Compute edge density (Sobel edges per unit area); compare against a target range. Catches "too much detail — unreadable" and "too little detail — looks lazy."

### 4.3 Critique dimensions (human-only)

Some things only a human can assess:

- "Does this feel space-like?"
- "Does this manufacturer feel distinct from that one?"
- "Is the composition intentional or accidental?"
- "Does this portrait convey the character?"

For these, we use the structured critique template (§5).

### 4.4 Test harness output format

When the agent runs the critique suite against an asset, the output looks like:

```
Asset: module_weapon_small_solari.png
  [PASS] palette_compliance (98.2% within tolerance)
  [PASS] silhouette_readability (avg edge contrast 42)
  [PASS] alpha_discipline
  [PASS] dimension_bounds
  [FAIL] detail_density (edges/area = 0.08, target range 0.12-0.25)
        Diagnostic: likely too few panel seams or rivets
  [PASS] determinism

Verdict: 1 failure. Recommended adjustments:
  - Increase rivet_density on solari_chrome material
  - Add Voronoi paneling if currently disabled
```

The agent can read this and revise without a human observation step.

---

## 5. Structured Human Critique Template

When human observation is required, it is shaped by a fixed template. Avoids free-form prose ambiguity.

### 5.1 The template

```
TASK: <agent output being critiqued>

OVERALL: <accept | revise | reject>

DIMENSION CRITIQUE (only fill non-empty):
  silhouette:    <observation → desired change>
  palette:       <observation → desired change>
  lighting:      <observation → desired change>
  detail:        <observation → desired change>
  composition:   <observation → desired change>
  feel:          <observation → desired change>

PRIORITY: <single dimension to focus on if agent must pick one>
```

### 5.2 Example filled template

```
TASK: First render of small weapon mount, solari manufacturer

OVERALL: revise

DIMENSION CRITIQUE:
  silhouette:    barrel is too thin relative to the mount body → thicken barrel by ~30%
  detail:        no visible panel seams — feels flat → add 2-3 vertical seams on the mount body
  lighting:      inconsistent — highlight is on upper-left instead of upper-right → confirm light direction is (1, -1) normalized

PRIORITY: lighting
```

The agent can execute this with high fidelity; the human spends ~30 seconds writing it.

### 5.3 When to use (versus automated critique)

- Use automated critique by default
- Bring in human critique when the automated harness passes but the asset still doesn't feel right
- Bring in human critique for the first render of a new asset type (establishes taste)
- Skip human critique when the automated harness is already failing (fix the automated failures first)

---

## 6. Persistent Reference Management

Agent sessions don't carry context across conversations. We must make the aesthetic constants *mandatory reading* at the start of any visual-generation task.

### 6.1 Reference hierarchy

```
 ┌─ 20_aesthetic_bible.md (the canonical style guide)
 │
 ├─ 10_programmatic_generation_framework.md (the procedural vocabulary)
 │
 ├─ 11_pygame_capability_audit.md (the technical substrate)
 │
 └─ 30-38 per-system overhaul docs (system-specific rules)
```

Every agentic visual task starts with: *"Read these docs. Confirm you've internalized them. Proceed."*

### 6.2 Style anchor file

A smaller doc loaded on every visual task: `requirements/overhaul/STYLE_ANCHOR.md` — contains **only** the style-critical facts needed in session context:

- The North Star sentence
- The 24-color palette with RGB values
- The global light direction
- The material list
- The manufacturer profiles
- Anti-patterns (what we never do)

Compact enough to fit in working context. Referenced by path in every task prompt.

### 6.3 Per-task reference pack

For complex tasks, the human assembles a **task-specific reference pack**:

- 1-2 reference screenshots from other games (if available, linked not embedded to respect copyright)
- The specific system-overhaul doc section being implemented
- Any previously-accepted assets of the same type (for continuity)

Loaded into the agent's context at task start.

---

## 7. Tooling Stack

### 7.1 Core

- **Python + pygame** — rendering substrate
- **numpy** — pixel manipulation
- **pytest** — visual critique test suite
- **PIL (Pillow)** — image I/O when pygame's is insufficient

### 7.2 For specific asset types

- **Blender + Python scripting** — for hero ships and characters that benefit from 3D → 2D render baking. Agent writes `.blend.py` scripts; human runs Blender; output feeds back.
- **Inkscape CLI** — rasterizing agent-generated SVG files. Agent writes SVG XML; Inkscape renders to PNG at specified size.
- **FFmpeg** — compositing frame sequences into animation GIFs if needed for promotional material.

### 7.3 For the iteration loop

- **Auto-reload rendering harness** — a small script (`tools/render_watch.py`) that watches a target Python file and re-renders on save. Reduces "did my change take?" friction.
- **Output gallery** — rendered assets dropped into `tools/output/` with timestamped filenames; a simple HTML gallery (auto-generated) lets human scan a batch visually at once.
- **Structured critique CLI** — a little tool that prompts the human with the template (§5.1) and captures it as a file the agent reads.

### 7.4 For automated critique

- **Contrast/WCAG libraries** — `wcag-contrast-ratio` or hand-roll
- **Sobel/edge detection** — via numpy or scipy.ndimage
- **Image diff** — PIL `ImageChops.difference` for regression testing

---

## 8. Prompt Patterns

The human-to-agent prompt structures that make visual work fast. These live in the style anchor or get copy-pasted per-task.

### 8.1 "Produce parametric variants"

```
Task: Render <asset> with manufacturer <X> in 3 variants (seeds 1, 2, 3).
Constraints:
  - Follow 10_programmatic_generation_framework.md §4.3 manufacturer profile
  - Respect 24-color palette; run test_palette_compliance before reporting
  - Save to tools/output/<asset>_<manufacturer>_seed<N>.png
Report:
  - Palette compliance % for each
  - Silhouette readability score for each
  - One-sentence diff between the three
```

### 8.2 "Tighten the spec on dimension X"

```
Task: Revise <asset> to improve <dimension>.
Current output: tools/output/<asset>_<version>.png
Observation: <structured critique>
Desired change: <specific>
Save revision to: tools/output/<asset>_<version+1>.png
Report:
  - What you changed in the code
  - Critique suite results
```

### 8.3 "Explore an aesthetic space"

```
Task: I'm unsure what <asset>'s aesthetic should be. Produce 4 wildly different approaches.
Constraints:
  - All four must pass palette compliance
  - Each must read as a coherent, intentional choice — not random
  - One-sentence description of the aesthetic each represents
Save to: tools/output/<asset>_exploration_A.png through _D.png
I'll pick one and we'll iterate.
```

### 8.4 "Translate a reference"

```
Task: Translate the feel of <game X scene Y> into Aurelia's aesthetic.
Reference: <link or screenshot>
Constraints:
  - Maintain palette compliance
  - Do not copy — translate. The reference's aesthetic language, not its pixels.
Save to: tools/output/<asset>_ref_translation.png
Report:
  - What you kept from the reference
  - What you translated
  - What you discarded as incompatible with Aurelia
```

### 8.5 "Produce and critique your own output"

```
Task: <produce an asset>
After producing, run the critique suite and ALSO give me your own 3-sentence critique of the output — what you would change, what works, what you're uncertain about.
```

This last one is the most powerful. The agent's self-critique catches issues before human observation.

---

## 9. Where Agentic Generation Does NOT Work

Honest boundaries. Not every visual task should be agent-driven.

### 9.1 One-off hero assets

Character portraits, boss designs, cover art, logo. These benefit from authored intent that's hard to encode procedurally. **Hand-craft these** (or commission a human artist; not our call today).

### 9.2 Subtle aesthetic moments

Narrative cutscene backgrounds, emotional composition, story-critical visuals. The agent can produce technically-correct output that lacks soul. **Hand-craft.**

### 9.3 Final polish at the end

When the game is nearly shipping and everything needs a 5% push across the board, that's surgical work informed by overall context. The agent can help with specific pieces but the orchestration is human.

### 9.4 Iteration past diminishing returns

After 10 iterations on the same asset with marginal improvements each time, **stop**. Accept the output. Move on. The agent won't sense this; the human must.

### 9.5 Clarity of intent

The agent executes specs; it doesn't invent intent. If the human doesn't know what they want, the agent can't deliver it. Before engaging agentic iteration: **what does this asset need to do?** Write that down first.

---

## 10. Prototype Spikes

Two spikes validate this workflow before we commit.

### Spike I — The end-to-end iteration loop

- Pick one asset (a HUD icon — low stakes)
- Run a deliberate 10-iteration loop with timing
- Capture: cycle time per iteration, % caught by automated critique, % requiring human critique, time spent on each
- **Success:** average cycle time < 2 minutes; ≥50% of cycles caught by automated critique alone
- **Failure path:** the loop is too slow; revise the tooling before committing

### Spike II — The critique harness

- Build a real `tests/visual/` test suite with 5 critique dimensions
- Run it against 5 sample assets (real or synthetic)
- Confirm: tests run fast (<1s each), produce actionable diagnostics, don't false-positive or false-negative
- **Success:** harness is trustworthy enough that the agent can rely on it
- **Failure path:** critique tests are flaky or uninformative; rethink what's automatable

---

## 11. Open Questions

1. **Can the agent paste images into the chat?** If the conversation UI allows it, the human captures a screenshot and pastes; agent reads it directly. This would dramatically tighten the human-in-the-loop cycle. Research: validate the agent's image-reading capability in this workflow.

2. **Should we build a thin "critique harness runner" in the repo?** A command like `python tools/critique.py <asset_path>` that runs all critique tests and produces the structured report. Tighter than importing pytest utilities manually.

3. **How much aesthetic-bible content fits in session context?** Bible will be ~500 lines by the time it's written. Loading it every session is context-heavy. May need a condensed `STYLE_ANCHOR.md` (150 lines) for context-efficient reference, with the full bible reserved for deep tasks.

4. **What's the right granularity for system-overhaul docs?** One per system? One per sub-system? Balance discoverability vs fragmentation.

5. **Do we use the agent for non-visual asset generation (e.g., sound synthesis code)?** Probably yes — the same workflow applies to `pygame.sndarray` synthesis. Covered in `40_audio_synthesis_framework.md` (Tier 3) but flagged here.

---

## 12. Dependencies

**This doc depends on:**
- `00_master_plan.md` — the umbrella methodology
- `10_programmatic_generation_framework.md` — what procedural code produces
- `11_pygame_capability_audit.md` — the technical substrate
- `20_aesthetic_bible.md` (not yet written) — style anchor content

**Docs that depend on this one:**
- Every per-system overhaul doc uses these workflows
- `40_audio_synthesis_framework.md` inherits the iteration loop
- `41_vfx_particle_vocabulary.md` uses the critique harness

---

## 13. Success Criteria

This workflow is successful when:

- **Cycle time target met:** agent-human iteration averages < 2 minutes per cycle for constrained parametric tasks; < 5 minutes for novel-aesthetic tasks.
- **Automated critique catches ≥50% of issues** before human observation.
- **Assets shipped** are indistinguishable in quality from assets produced via traditional hand-authoring, even though their production method differs.
- **Boundaries respected:** hero/character assets not force-fit into agentic generation when hand-crafting is appropriate.
- **No AI image/audio generation** anywhere in the pipeline, confidently documentable if the topic ever comes up with an audience.

---

*Next: run prototype spikes. Prototype A (module render) and Spike I (iteration loop) together are the first experiments — they validate both the programmatic generation framework AND this workflow simultaneously. Then write the Aesthetic Bible with evidence, not speculation.*
