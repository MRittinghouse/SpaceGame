# Overhaul Master Plan

> **Status:** PLANNING — this is the roadmap of roadmaps.
>
> This document indexes every overhaul doc that will be written, scopes what each contains, flags research that must happen before implementation, and sequences the work. Read this first when approaching the visual/experiential overhaul.

---

## 1. Purpose & Philosophy

The combat balance pass (U2.5d) closed. The next work is different in kind: not a mechanical tuning pass, but a **look-and-feel overhaul** of the entire game. This plan exists because overhaul work has a failure mode — writing an inspiring vision doc that the production methodology can't actually deliver — and we want to sidestep it.

The governing principles for this overhaul are:

1. **A Cyberpunk-flavored JRPG set in a grounded Armored Core universe, with No Man's Sky's reverence for scale.** This is the North Star sentence. Every aesthetic and gameplay decision in the overhaul defers to it.
2. **Programmatic generation as a first-class creative discipline.** Not a fallback — a primary medium with its own maturity model, tooling, and standards.
3. **No AI image/audio generation.** Gaming audiences reject generated assets, and our output should be defensibly human-or-programmatic.
4. **Agentic resources at maximum leverage.** AI coding agents (this one) iterate on procedural generation, shader code, Blender scripts, SVG output, and visual test harnesses. This is where AI amplifies without triggering audience rejection.
5. **VFX/UI polish and lighting are higher-leverage than sprite detail.** Budget goes to the multiplicative layer (post-processing, particles, animation, chrome) that improves every existing system.
6. **Decisions deferred to evidence.** We prototype small questions before committing to big decisions. Research cycles are built into the plan.

---

## 2. Document Hierarchy

```
requirements/overhaul/
├── 00_master_plan.md                        ← this file
│
├── Tier 1 — Production Framework
│   ├── 10_programmatic_generation_framework.md
│   ├── 11_pygame_capability_audit.md
│   └── 12_agentic_graphics_workflow.md
│
├── Tier 0 — Aesthetic Umbrella (written AFTER Tier 1)
│   └── 20_aesthetic_bible.md
│
├── Tier 2 — System Overhauls (one per system)
│   ├── 30_overhaul_space_combat.md
│   ├── 31_overhaul_ship_builder.md
│   ├── 32_overhaul_mining.md
│   ├── 33_overhaul_galaxy_map.md
│   ├── 34_overhaul_trading_markets.md
│   ├── 35_overhaul_station_hub.md
│   ├── 36_overhaul_salvage.md
│   ├── 37_overhaul_refining.md
│   └── 38_overhaul_ground_exploration.md
│
└── Tier 3 — Parallel Tracks (non-blocking support)
    ├── 40_audio_synthesis_framework.md
    ├── 41_vfx_particle_vocabulary.md
    └── 42_ui_chrome_components.md
```

**Why Tier 1 comes before Tier 0:** the aesthetic bible specifies *what* the game looks like. The framework docs specify *what we can produce*. Writing the bible first risks specifying a visual language the production methodology can't deliver. Inverting the order forces the bible to be honest about the toolchain's capability.

---

## 3. Tier 1 — Production Framework Docs

These three docs define *how we produce visual output*. They are research-heavy and deserve prototype spikes before being written. Each doc below names its scope, the research questions it must answer, and the prototypes that inform it.

### 3.1 Programmatic Generation Framework (`10_programmatic_generation_framework.md`)

**Purpose:** Define the creative discipline of generating visual assets from code. Establish the primitive vocabulary, material system, lighting model, composition rules, and variation strategies that let a finite amount of code produce a rich visual world.

**Scope — what the doc will cover:**

- **Primitive vocabulary.** The base shapes every asset is composed of. Candidates: lines, circles, polygons, Bézier curves, signed distance fields (SDFs), Voronoi cells. Decision: which to commit to as foundational, which as optional.
- **Material system.** How we express "brushed steel," "crimson-painted iron," "energy plasma," "glass viewport," "ceramic heat tile" as parametric functions. Per-manufacturer material dictionaries.
- **Lighting model.** The one global directional light that every module honors. Ambient contribution. Emissive contributions (engines, windows, indicators).
- **Procedural detail.** How rivets, panel seams, wear, battle damage, and grime emerge from code. Noise function library (Perlin, Simplex, FBM, Voronoi-based patterns).
- **Composition rules.** How modules connect at interface points (welds, seams, glowing couplings). How an entire ship reads as *one thing* rather than modules-next-to-each-other.
- **Variation strategies.** Seeded randomness, parametric families, template-plus-fills. How we avoid sameness without producing chaos.
- **Color system.** Palette-constrained rendering. How palette entries map to roles ("hull cold-metal," "Reach warning red," "console glow"). HSV manipulation for dynamic recoloring.
- **Post-processing hooks.** Where in the render pipeline the global filter (bloom/vignette/grain) inserts and how per-asset rendering prepares for it.

**Research questions to answer before writing:**

1. **Which noise library?** `noise`, `opensimplex`, `fastnoise`, or roll our own? Benchmark on pygame surfaces.
2. **SDFs or bust?** Is the investment in signed-distance-field rendering worth it for 2D sprites? (Pro: smooth shape blending, clean silhouettes. Con: complexity.)
3. **How do we manage per-manufacturer style guides?** A `manufacturer_profile.py` dict per manufacturer with color/detail/shape parameters?
4. **Lighting direction: global or per-scene?** Combat view has one light; ship builder preview another? Or one sacrosanct direction everywhere?
5. **What's the failure mode of procedural generation and how do we guard against it?** (Grey-goo sameness; unreadable silhouettes; palette drift.) Test harnesses needed.
6. **Reference games to study closely:** Caves of Qud (procedural tile rendering), Dwarf Fortress (tileset authoring discipline), Factorio (sprite asset production pipeline), Brogue (minimalist color composition), Hyper Light Drifter (palette discipline), Thomas Was Alone (geometric minimalism with great lighting).

**Prototypes to build before writing (disposable, 2–3 days total):**

1. **Module render spike.** Pick one module (say, a small weapon mount). Write a `render_module(manufacturer, wear_level, seed)` function. Produce three manufacturer variants. Criterion: the three read as distinctly different without any hand-drawn pixels.
2. **Ship composition spike.** Compose 4–6 modules into a ship with consistent lighting and visible connection seams. Criterion: it reads as one vehicle, not six sprites touching.
3. **Palette stress test.** Render the same ship with three candidate palettes. Observe which palette gives the best visual identity. Informs the aesthetic bible.

### 3.2 PyGame Capability Audit (`11_pygame_capability_audit.md`)

**Purpose:** Map the real surface of what pygame-ce (the version we use) offers, with concrete decisions about which features we commit to integrating. Avoids reinventing features the platform provides.

**Scope — what the doc will cover:**

- **Feature inventory.** Every pygame-ce module, class, and key function, tagged: {currently-used, available-but-unused, requires-integration-work, experimental}.
- **Blending capability.** All `BLEND_*` modes with use-case mapping (where each produces the best output).
- **Surface manipulation.** `surfarray` + numpy integration patterns. `PixelArray`. `mask`. `subsurface`. Direct pixel access speed benchmarks.
- **Shader support.** pygame-ce's experimental shader module. What it does, what it doesn't. Fallback: moderngl integration.
- **`_sdl2.video` hardware acceleration.** Texture renderer vs. traditional surface blitting. When to use which.
- **Advanced drawing.** `gfxdraw` antialiased primitives. Polygon rendering. Gradient fills.
- **Text rendering.** `freetype` for advanced typography. Outline, shadow, and layer effects.
- **Color manipulation.** HSV, HSLA, colorspace conversions. Dynamic recoloring patterns.
- **Audio surface.** `sndarray` for programmatic sound synthesis (parallels the visual story).
- **Event loop integration.** Where rendering inserts relative to input, logic, and state updates.
- **Integration candidates.** moderngl + pygame, Pillow for complex image ops, pymunk (physics, tangential), shapely (geometry).

**Research questions to answer before writing:**

1. **pygame-ce version capabilities.** Which version are we pinned to? What shader support does it expose? Test with a real shader, measure frame time.
2. **Speed of `surfarray` vs direct surface ops** on representative workloads (full-screen post-processing at 60 FPS).
3. **`_sdl2.video.Renderer` integration.** Does our current render loop prevent adoption, or can we migrate incrementally?
4. **Offscreen render targets.** How do we cache expensive procedural generation so it's not redone per frame?
5. **Threading.** Can asset generation run in background threads without stalling the main loop?

**Prototype spikes:**

1. **Shader post-processing spike.** Take an existing scene. Apply bloom + chromatic aberration via pygame-ce shaders (if supported) or moderngl. Measure frame time delta.
2. **Surfarray performance benchmark.** Full-screen per-pixel manipulation (e.g., apply a lookup-table palette remap) via surfarray. Confirm 60 FPS headroom.
3. **Hardware-accelerated renderer spike.** Migrate a simple scene to `_sdl2.video.Renderer`. Document the integration cost vs the performance gain.

### 3.3 Agentic Graphics Workflow (`12_agentic_graphics_workflow.md`)

**Purpose:** Design the collaboration model between the human and the AI coding agent for visual work. This is novel territory with no strong precedent — worth deliberate design.

**Scope — what the doc will cover:**

- **The iteration loop.** Agent writes rendering code → human runs it → human reports observations (text + screenshot) → agent refines → loop. Characterize the loop's per-cycle time and what makes it fast vs slow.
- **Visual critique harness.** Assertions the agent can make about its own output without needing a screenshot: silhouette readability (bounding-box ratio analysis), palette compliance (% of rendered pixels inside the canonical palette), contrast ratios for UI text, edge sharpness scores. Runs in CI / test suite.
- **Screenshot-in-the-loop.** When human observation is required, what's the fast feedback mechanism? Agent-proposed verbal critique on a rendered image? Structured observation prompts?
- **Reference inputs.** Where does the agent store "style references" it consults each session? A `visual_references/` folder of linked external inspirations? A written style guide the agent reads at task start?
- **Blender scripting via agent.** Agent writes `.py` scripts that Blender executes to produce 2D sprites from 3D models. Iteration loop: agent writes script → human runs Blender → image output → agent refines.
- **SVG generation via agent.** For UI chrome, agent writes SVG code that renders deterministically. Iteration loop: agent writes SVG → human views → agent refines.
- **Shader authoring via agent.** Agent writes GLSL code. Iteration loop: agent writes shader → human compiles/runs → agent refines.
- **Tooling stack.** What's installed, what's needed, what's optional.

**Research questions:**

1. **Can we automate the screenshot feedback?** If the human can paste a rendered image to the chat and the agent can parse/critique it, the loop tightens considerably.
2. **What visual properties can be tested programmatically?** Pixel-level: palette compliance, alpha coverage, edge sharpness via derivative. Composition-level: silhouette readability, negative space distribution. Harder: "does this feel space-like?" (ultimately subjective).
3. **How do we prevent agent drift?** A style reference doc loaded at task start keeps the agent anchored to the aesthetic bible.
4. **What's the right prompt structure for visual iteration?** (This doc formalizes patterns the human can copy/paste.)
5. **Where does hand-crafted pixel art fit?** When is "agent writes procedural code" wrong and "human makes a 16×16 sprite in Aseprite" right?

**Prototype spikes:**

1. **End-to-end iteration spike.** Pick a small asset (e.g., a HUD icon). Run a deliberate 10-iteration loop: agent code → human screenshot → agent critique → refine. Time each cycle. Document bottlenecks.
2. **Visual test harness spike.** Write `tests/visual/test_palette_compliance.py` that loads a rendered asset and asserts >95% of pixels fall inside the canonical palette. Automates one form of visual critique.
3. **Blender script spike.** Agent writes a Blender Python script that models + renders a simple ship part. Human runs. Iterate to acceptable output. Prove the pipeline works.

---

## 4. Tier 0 — Aesthetic Bible (`20_aesthetic_bible.md`)

**Purpose:** The umbrella reference. Every Tier-2 doc defers to this. Written AFTER Tier 1 so it's grounded in producible reality.

**Scope — what the doc will cover:**

- The North Star sentence (copied verbatim for reference).
- **Canonical palette.** 16–32 colors with named roles. "Deep space" (#0a0e1a), "hull cold-metal" (#2a3444), etc. Each role defined once.
- **Typography.** One primary display font (sci-fi, free, licensable). One monospace for HUD readouts. Weight/size scale. When to use which.
- **Motion language.** Ease curves (cubic-bezier constants). Animation timings (how long is a "punch," a "drift," an "entry"?). Idle motion rules.
- **Rendering principles.** Global light direction. Bloom intensity ceiling. Vignette strength. Chromatic aberration use.
- **UI chrome vocabulary.** Panel borders, header treatments, button states, badge shapes. Specified enough that every screen uses the same lexicon.
- **Faction visual signatures.** Each faction's palette subset and detail vocabulary. Makes Commerce Guild UI distinguishable from Crimson Reach UI at a glance.
- **Anti-patterns.** Explicit "do not" list. (No CRT-scan filter without purpose. No cartoonish proportions. No AI-generated visual assets.)
- **Examples.** Mockups or rendered samples illustrating each principle.

**Inputs required before writing:**

- Framework docs complete (10/11/12 above).
- At least two prototype spikes executed (module render spike + post-processing spike) — we need to know what producible quality looks like.
- Palette exploration prototype (render candidate ships in 3 palette options, pick the winner).

---

## 5. Tier 2 — System Overhaul Docs

One doc per major system. Each inherits from Aesthetic Bible + Tier 1 framework. Each contains:

- Current state (honest assessment)
- Target feel (influences, specific reference scenes)
- Player-experience goals (which emotions during which moments)
- Rendering changes (lighting, VFX, UI chrome)
- Gameplay changes (only if rendering exposes gameplay problems)
- Dependencies on other overhaul docs
- Phasing

Per-system quick scope:

| # | System | Primary Influence | Notes |
|---|--------|-------------------|-------|
| 30 | Space Combat | FF7/Chrono Trigger + Armored Core weight | JRPG camera composition, VFX per element, dual tech portraits, damage-number juice |
| 31 | Ship Builder | Armored Core | Manufacturer identity, lighting consistency, live preview-in-flight |
| 32 | Mining | Cookie Clicker / Universal Paperclips | Click juice, idle-loop visibility, prestige as visible event |
| 33 | Galaxy Map | No Man's Sky / Starfield grav-jump | Parallax, scale reverence, jump animation |
| 34 | Trading | Cyberpunk 2077 market brutalism | Data density, ticker crawls, sparklines |
| 35 | Station Hub | Cyberpunk districts + Starfield stations | Painted panorama, neon-on-darkness, faction-specific chrome |
| 36 | Salvage | TBD (Balatro? Slay the Spire? Inscryption?) | Needs influence anchor before design |
| 37 | Refining | TBD (Stardew? Factorio? Project Zomboid?) | Needs influence anchor before design |
| 38 | Ground Exploration | TBD (Fallout 1/2 isometric? Invisible Inc?) | Needs influence anchor before design |

**Pre-doc research for Tier 2:** for each system, pick its anchor influence (the specific reference game/scene) BEFORE writing the overhaul doc. Without the anchor, the doc drifts.

---

## 6. Tier 3 — Parallel Tracks

Non-blocking support docs that apply across systems.

### 6.1 Audio Synthesis Framework (`40_audio_synthesis_framework.md`)

Parallels the programmatic-visual approach. No AI audio generation. Techniques:

- **Programmatic synthesis** via `numpy` + `pygame.sndarray`. Sine/square/saw waves composed into weapon sounds, UI clicks, ambient drones.
- **Procedural soundscapes** for mining depth, station ambience, combat tension layers.
- **Chiptune/FM synthesis** as a recognizable aesthetic (synthwave, not "retro," a considered modern chip sound).
- **Licensed royalty-free music** where programmatic doesn't fit (moments of character). Sourced from non-AI human composers (itch.io, OpenGameArt, paid marketplaces with attribution).

Research: FM synthesis libraries, soundfont support, MIDI-via-Python for flexible music layer.

### 6.2 VFX Particle Vocabulary (`41_vfx_particle_vocabulary.md`)

The game's particle system needs an opinionated vocabulary. This doc defines:

- Named presets (trail, burst, dust, smoke, spark, rising-text, directional-flow, pulse-ring).
- Per-preset parameters (count, lifetime, color ramp, size curve, velocity distribution).
- Composition rules (how presets layer — e.g., muzzle flash = burst + spark + flash + screen shake).
- Screen-space effects (vignette pulse, edge highlight, focus blur).

This depends on Programmatic Generation Framework (shares the palette) and Aesthetic Bible (color discipline).

### 6.3 UI Chrome Components (`42_ui_chrome_components.md`)

Reusable UI component library. Panel frames, button states, tabs, tooltips, progress bars, toggles, sliders — each specified and rendered programmatically with Aesthetic Bible palette compliance.

---

## 7. Sequencing & Dependencies

```
Week 1 — Prototype phase (no docs written yet)
  ├── Module render spike (programmatic-gen research input)
  ├── Post-processing pipeline spike (pygame research input)
  └── Agentic iteration loop spike (workflow research input)

Week 2 — Tier 1 framework docs
  ├── Write 10_programmatic_generation_framework.md
  ├── Write 11_pygame_capability_audit.md
  └── Write 12_agentic_graphics_workflow.md

Week 3 — Aesthetic umbrella
  └── Write 20_aesthetic_bible.md (informed by prototypes + framework)

Week 4+ — System overhauls (sequenced, one at a time)
  Order of operations:
  1. Space combat (highest player-time visibility)
  2. Ship builder (most visible visual offender today)
  3. Galaxy map (relatively contained, big perceptual win)
  4. Station hub (connective tissue)
  5. Trading + other mini-games
  6. Ground exploration (lowest priority until influence chosen)

Parallel tracks start whenever their dependencies resolve:
  - VFX vocabulary: begins after Tier 1 done, runs alongside combat overhaul
  - UI chrome: begins alongside trading/station overhauls
  - Audio synthesis: can start anytime; needed for combat overhaul
```

**Critical path:** Tier 1 framework docs → Aesthetic bible → Combat overhaul → everything else.

**Parallelization:** Once Tier 1 is done, VFX vocabulary and UI chrome work can start in parallel with the bible and combat overhaul.

---

## 8. Open Questions & Risks

| # | Question | Impact | Resolve when |
|---|----------|--------|--------------|
| 1 | Can pygame-ce's shader support deliver bloom/CA at 60 FPS, or do we need moderngl? | Medium — if moderngl, extra integration work | During pygame audit spike |
| 2 | Will programmatic module rendering match hand-made pixel art for perceived quality? | High — if not, pivot plan needed | During module render spike |
| 3 | Can the agent-iteration loop go <30 seconds/cycle? | Medium — slow cycles demotivate the overhaul | During iteration loop spike |
| 4 | Do we commit to Blender for hero assets, or go 100% code-rendered? | Medium — Blender adds a tool dependency | During Blender spike (in agentic workflow) |
| 5 | How do we preserve existing save compatibility through visual changes? | Low (visual only, not data) | N/A |
| 6 | Is the current `ParticlePool` sufficient or does it need a rebuild? | Medium — affects VFX vocabulary scope | During combat overhaul research |
| 7 | Does the "no AI audio" constraint apply to music too, or only SFX? | Low — drives audio framework scope | Before writing audio framework |
| 8 | Which sci-fi display font is the right one? | Low — easy to swap | During aesthetic bible writing |

---

## 9. Success Criteria

The overhaul is successful when:

- Any random screenshot of the game communicates "this is Aurelia" via visual identity alone.
- Ships visibly belong to their manufacturers; a player can identify a Solari ship vs. a Reach ship without reading the label.
- First-time players describe the game as "slick," "modern," "space-like" without prompting.
- Every particle effect, UI transition, and post-processing filter feels *intentional* rather than defaulted.
- The procedural generation code is understandable to a new contributor without archaeology.
- The agentic workflow produces new assets at a faster clip than hand-authoring would.
- No AI-generated visual or audio assets shipped, and we can confidently state that to an audience.

---

## 10. What This Document Is Not

- **Not the aesthetic bible.** That's Tier 0, written later.
- **Not an implementation plan for any specific system.** Those are Tier 2, written later.
- **Not a commitment to every prototype landing.** Prototypes are research; some will fail and inform us that a direction isn't viable.
- **Not a deadline.** Weeks are ordering indicators, not calendar commitments.

---

## Appendix A: Research Reading List

Curated references to study before and during each research phase. Not authoritative — add to this list as we discover more.

**Programmatic generation:**
- Inigo Quilez's articles on SDFs and procedural graphics (iquilezles.org)
- "Procedural Content Generation in Games" (Shaker, Togelius, Nelson — available free)
- Caves of Qud postmortems
- Factorio dev blog posts on asset pipeline

**PyGame deep dive:**
- pygame-ce official docs + changelog for features post-fork
- moderngl tutorials for shader integration
- Real-Python articles on pygame advanced techniques
- The pygame-ce discord / community forum for undocumented patterns

**Agentic visual workflows:**
- (Few precedents — document as we go)
- Research: existing visual-regression testing frameworks (Percy, Chromatic) for test-harness inspiration
- Research: Blender Python API documentation (scripted asset pipeline)

**Reference games for mood-boarding:**
- Hyper Light Drifter, Hades, Thomas Was Alone (visual discipline)
- Caves of Qud, Brogue (procedural tile art)
- Factorio, Rimworld (asset consistency at scale)
- No Man's Sky, Starfield (scale and atmosphere)
- Cyberpunk 2077 (UI brutalism, character voice)
- Armored Core 6 (part identity, manufacturer vocabulary)

---

*End of master plan. Next action: prototype-phase spikes (Week 1) before any Tier 1 docs are written.*
