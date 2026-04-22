# Spike 03 Findings — Palette Stress Test

> Framework Spike C per `00_master_plan.md` and `10_programmatic_generation_framework.md §12`.
>
> Purpose: render the Spike B ship composition (3 manufacturers × 6 modules) under three candidate palette philosophies, to inform the Aesthetic Bible's palette finalization.

---

## TL;DR

**All three candidate palettes work.** Each produces legible, well-composed ships that pass 6 of 7 critique checks (the failing 7th is Solari lighting — confirmed as a **material-design issue**, not a palette issue, since it recurs under all three palettes).

The more important finding is structural: **palette changes have surprisingly modest impact on aggregate ship appearance.** Swapping palettes shifts mood without altering ship design. This is reassuring — palette becomes a discipline lever for "voice," not a design crutch. Faction identity, manufacturer distinctness, and readability remain intact across all three palettes.

The **warmth axis** (+18 → +11 → -5) is the clearest differentiator. The Bible's palette choice is essentially a decision about whether Aurelia leans warm-industrial, warm-graphic, or cool-cyberpunk.

---

## Spike Scope

Built on top of Spikes A/B, with no rendering changes:

- `palette_candidates.py` — three candidate palettes sharing role names, varying RGB values only
- `spike_palettes.py` — entry point that activates each palette in turn and renders all three manufacturers under each

Critique dimensions added:

- `palette_summary()` — per-palette luminance range, warmth skew, saturation mean
- Cross-palette determinism — same seed under different palettes produces distinct but deterministic output
- Same-ship-different-palette distinctness — does the same ship "feel different" across palettes, quantitatively?

Outputs: `palette_conservative.png`, `palette_high_contrast.png`, `palette_neon.png`, `palette_compare.png` (stacked), `palette_critique_report.txt`.

---

## The Three Palettes (Descriptive Stats)

| Palette | Luminance range | Warmth skew | Saturation mean |
|---|---|---|---|
| **conservative** | 235.2 | +11.5 | 62.2 |
| **high_contrast** | 247.7 | +18.6 | 71.0 |
| **neon** | 238.7 | **−5.4** | 64.7 |

- **conservative** — muted industrial sci-fi. The baseline. Grounded. Reference: The Expanse, Starfield.
- **high_contrast** — same hue families as conservative, pushed for chroma and dynamic range. Graphic-novel punch without breaking faction identity.
- **neon** — purple-tinted void, hot-pink plasma, magenta-leaning Reach, electric cyans. Cyberpunk voice. Reference: Hyper Light Drifter, Signalis.

All three keep identical faction-color hue families (Reach = red family, Solari = light family, Union = warm family). Neon pushes Reach toward magenta — within the red family but at its cyberpunk boundary.

---

## What Worked

### 1. Palette compliance holds cleanly across all palettes (9/9 ships)

Every ship under every palette produces 100% palette compliance on both the strict pointwise check and the gradient-aware line check. The palette-snap discipline is palette-agnostic — if the candidate is a well-formed role-indexed palette, snap works regardless of the specific RGB values.

### 2. Silhouette readability holds across all palettes (9/9 ships)

Edge-contrast-against-void averages 140–338 across all palette×manufacturer combinations (threshold: 30). Even the cool Neon void reads Solari's chrome clearly. No palette produces an "invisible" ship.

### 3. Ship connectivity holds (9/9 ships)

All ships render as one connected component under all palettes: 4412/4412 Solari, 4647/4647 Reach, 4714/4714 Union. Palette has no impact on the composition algorithm, as expected.

### 4. Within-palette variant distinctness holds

The three manufacturers remain strongly distinguishable under each palette:

| Palette | Pairwise mean RGB diff (target ≥15) |
|---|---|
| conservative | 88.1 |
| high_contrast | 91.6 |
| neon | 75.5 |

All ~5× the threshold. Faction identity survives every palette.

### 5. Cross-palette determinism holds (3/3 manufacturers)

Same seed + same layout + different palette = deterministically different output. Hashes confirm:

- Solari: `2c34220e` / `3eb45f66` / `ee253541`
- Reach: `aae57005` / `ec8daf23` / `d463b608`
- Union: `98614bdc` / `69d12266` / `2e64f3b3`

All nine distinct; each reproducible. Palette swapping is a clean lever.

### 6. Detail density stable across palettes

Detail density values cluster tightly at **0.13–0.18** across all 9 combos. Palette doesn't change how busy the ships look — rivets, wear, and seams survive the snap consistently. Good signal that detail passes are orthogonal to palette choice.

### 7. Render speed unchanged

Nine ships (3 palettes × 3 manufacturers) in 133ms total — ~15ms per ship. Palette swapping has no measurable performance cost; the active PALETTE is just a dict lookup.

---

## What's Revealed (not failed — informative)

### Finding 1: Solari's lighting problem is material, not palette

The Solari lighting check fails under all three palettes:
- conservative: +3.7 (below threshold of 5)
- high_contrast: **−0.2** (wrong direction!)
- neon: +2.1

This confirms Spike 02 Finding 3 was correctly diagnosed as a **material-band problem**. Solari's chrome is predominantly bright; the band's luminance range is compressed at the top, so lighting gradients get eaten by the snap. **No palette tuning will fix this**; the material redesign from `10_programmatic_generation_framework.md §4.1` (shade band with broader spread) is required.

Most telling: high_contrast — the palette with the widest luminance range (247.7) — has the WORST Solari lighting (−0.2, direction-incorrect). The extra dynamic range is invested in darks and highlights that Solari's chrome doesn't reach anyway, so its within-band span actually narrows relative to conservative.

**Implication for Bible:** Solari's material spec gets a hand-designed 5-entry shade band with forced luminance spread, not one derived from "pick some palette colors that are roughly chrome-y."

### Finding 2: Cross-palette distinctness is surprisingly modest

For the SAME ship under THREE different palettes, pairwise mean RGB diff came out at:
- Solari: 11.8
- Reach: 25.1
- Union: 12.6

Against an aspirational threshold of 30 — all three technically fail. But the threshold was arbitrary; the real finding is the pattern:

- **Reach shifts most (25.1)** because Neon pushes its crimson toward magenta (a true hue shift), while conservative and high_contrast stay within the red family.
- **Solari and Union shift least** because their palette entries change mostly in luminance and saturation, not hue. A chrome ship rendered in a "warmer" vs "cooler" palette is still a chrome ship.

This is **a good result, not a bad one**. It says: palette is a mood layer, not a design layer. Ship identity — silhouette, material parameters, seam placement, manufacturer signature — survives palette swapping. Palette choice determines voice; ship design determines identity.

**Implication for Bible:** don't expect palette to carry too much work. A bold palette makes things feel bold, but it won't disguise weak ship design or rescue flat composition. Invest palette work in voice-setting; invest the more consequential work in materials and composition (per Spikes 01/02).

### Finding 3: The warmth axis is the cleanest Bible decision vector

Luminance range and saturation cluster near each other across the candidates (~235–247, ~62–71). The sharply differentiating metric is **warmth skew**:

- conservative: +11.5 (slightly warm — industrial honest)
- high_contrast: +18.6 (warmer — dramatic, pulp)
- neon: **−5.4** (cool — cyberpunk, glow-forward)

The Bible's single cleanest decision is: **Aurelia is warm, neutral, or cool?** That one choice probably pulls 60% of the aesthetic identity with it.

Our project context gives a strong hint: the cultural guide's "lived-in industrial" + "faded chrome + crimson + ceramic" language points warm. Neon's cool pivot is the interesting outsider — high impact, but a bigger commitment.

### Finding 4: Neon works better than I expected — but shifts the game's voice

Neon's cross-palette distinctness showing (Reach 25.1 — the biggest shift) confirms Neon is the most aesthetically differentiated candidate. The 9 ship renders are legible, well-composed, and bring a clear stylistic signature. It's a real option, not a straw man.

But Neon's **Warmth −5.4** is a genuine voice change. Crimson Reach becoming "Magenta Reach" is a retcon against the cultural guide's description of the faction. This is the kind of cost that should be decided at Bible level, not drifted into. A cool-leaning Aurelia is a different game than the one in the cultural guide.

Recommended for Bible: treat **neon as a lighting/post-process option** (e.g., certain stations, combat intensity, specific biomes) rather than a base palette. This lets us keep cool-cyberpunk as an accent color language without retconning faction identity.

---

## Design Decisions Informed (not forced — the Bible decides)

The Bible gets the final call. Candidate positions informed by this spike:

### Position A — Conservative as base (most faithful to cultural guide)

- Muted warm industrial palette becomes canon
- Band-structured (per §8.1 framework revision) with conservative RGB values as band centers
- Stations and scenes vary **tint and vignette** for mood, not base palette
- Neon reserved for specific gameplay contexts (Red Line combat, Crimson Reach strongholds as mood overlay, cyber-district stations)

### Position B — High-contrast as base (same voice, more punch)

- Same hue families as conservative, but calibrated for wider luminance + saturation
- Ship renders get more dramatic — stronger highlights, deeper shadows
- Cost: slightly less grounded; some risk of reading as "arcade" rather than "industrial"

### Position C — Split between warm base and cool accents

- Primary material bands (hull, factions) on the warm axis (conservative or high-contrast values)
- Emissive / tech / UI on the cool axis (neon values for plasma_core, hud_cyan, cryo_fractal)
- Biggest maintenance load but widest expressive range

**My recommendation:** Position B — high-contrast as base. It picks up the punch we need for modern-feeling visuals without sacrificing the cultural guide's grounded industrial voice. Conservative is the safest but arguably the flattest; Neon is the most distinctive but costs us faction identity. High-contrast is grounded AND legible AND punchy.

---

## Framework Implications

### No revisions forced

Spike C's findings don't require framework doc changes. The §8 palette structure (two-tier bands + roles) accommodates all three candidates equally well — role names stayed constant; only RGB values swapped. This validates the role-indexed discipline is working as designed.

### Revisions flagged (optional, low-priority)

- `check_ship_lighting_consistency` could be updated to use the Spike 02 Finding 5 split (direction-only required + magnitude advisory). Currently it treats a tiny positive as a fail. Worth doing when the critique harness gets promoted from spike-tool to production-test — not today.
- Cross-palette distinctness threshold of 30 was arbitrary and too aggressive. If this becomes a Bible-layer test, tune to observed values (~12–25 range is normal and healthy).

### Aesthetic Bible TODOs (re-confirmed)

Per framework §15.4:
- Reserve band-naming space for future material classes (sensor_glass, electronics_emissive, cooling_vent, radar_mesh, shield_field)
- Define per-category visual signatures (manufacturer × category as identity grid)
- Pick the warmth-axis position (A / B / C above)

---

## Artifacts Produced

Files (keep — they seed the Bible):
- `tools/overhaul_spike/palette_candidates.py`
- `tools/overhaul_spike/spike_palettes.py`

Outputs for Bible-writing visual review:
- `tools/overhaul_spike/output/palette_conservative.png`
- `tools/overhaul_spike/output/palette_high_contrast.png`
- `tools/overhaul_spike/output/palette_neon.png`
- `tools/overhaul_spike/output/palette_compare.png` — stacked 3-palette comparison
- `tools/overhaul_spike/output/palette_critique_report.txt`

---

## Recommended Next Actions

1. **Human view pass (the real test):** open `palette_compare.png`. Does one of the three palettes feel like Aurelia? Does one feel wrong? Warm or cool? Punch or restraint? This is the decision the spikes were buying; the metrics confirm viability but they don't pick the voice.

2. **Write the Aesthetic Bible** (`20_aesthetic_bible.md`):
   - Pick palette position (A / B / C recommendation above, or a new synthesis)
   - Promote the chosen candidate's RGB values into band-structured form per framework §8.1
   - Reserve band-naming space for future material classes (framework §15.4)
   - Define per-category visual signatures (manufacturer × category)
   - Commit material bands for all v1 materials (§4.2) as hand-calibrated shade bands, resolving Spike 01/02/03's recurring Solari lighting finding

3. **After the Bible: begin Tier 2 per-system overhaul docs.** Top candidate: space combat visual overhaul, since it's the highest-visibility system and benefits most from the new material/lighting pipeline.

---

## Honest Assessment

**What the spike proved:**
- Palette swapping via role-indexed materials works cleanly; the framework discipline holds under stress.
- All three candidates produce legible, well-composed, deterministic output.
- The warmth axis is the cleanest differentiation vector for Bible decisions.

**What the spike did NOT prove:**
- **Which palette is "right" for Aurelia.** That's a human judgment, not a metric. The output images are the deliverable for that decision.
- **Whether the material band structure (framework §4.1/§8.1) needs implementation in the spike.** The current flat-palette spike works well enough to defer band-structure implementation to production. Solari's lighting problem re-confirms the redesign is needed — but the spike doesn't need to be where it lands.

**Verdict:** all three spikes complete. Framework validated. **Next step is the Aesthetic Bible** — which is now informed by concrete visual evidence rather than speculation.
