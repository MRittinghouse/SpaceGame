# PyGame Capability Audit

> **Status:** DESIGN — speculative mapping. Prototype spikes will verify performance claims and integration costs.
>
> Maps the real surface of pygame-ce 2.5.0+ to the programmatic generation framework. Identifies what we use today, what we're leaving on the table, and what requires integration work. Drives concrete adoption decisions.

---

## 1. Purpose

A common failure mode when committing to programmatic generation: reinventing features the platform already provides, or dismissing the platform as "just for blitting" when it has much deeper capabilities.

pygame-ce (the community fork we're using) has substantially more surface area than stock pygame. Most of it is undocumented in beginner tutorials. This doc is the deliberate audit so we make informed choices, not defaulted ones.

---

## 2. Current Usage Audit

An honest accounting of what we actually use today, based on the engine module audit done in `10_programmatic_generation_framework.md §2`:

### 2.1 Heavily used

- `pygame.Surface` (everywhere) — the primary render target
- `pygame.Rect` (everywhere) — bounding boxes, collisions, positioning
- `Surface.blit` / `blits` — the primary compositing operation
- `pygame.draw.rect`, `draw.line`, `draw.circle`, `draw.polygon` — primitive rendering
- `pygame.font` (via `engine/fonts.py`) — text rendering
- `pygame.transform.scale`, `transform.rotate` — sprite scaling/rotation
- `pygame.mixer` — sound playback
- `pygame.event` — input handling

### 2.2 Used sparingly

- `Surface.convert_alpha()` — called on sprite loads, probably not consistently
- `pygame.Color` objects — most code uses raw tuples
- `pygame.BLEND_*` modes — some usage in particles, minimal elsewhere
- `Surface.set_alpha()` / `set_colorkey()` — sporadic

### 2.3 Not used at all (or barely)

This is where the biggest opportunity lives.

- `pygame.surfarray` — numpy-backed surface manipulation ← **major gap**
- `pygame.gfxdraw` — antialiased primitives ← **quick win**
- `pygame.freetype` — advanced text rendering ← **medium value**
- `pygame.sndarray` — numpy-backed audio generation ← **required for audio synthesis framework**
- `pygame.mask` — pixel-precise collision, shape manipulation ← **relevant for silhouette analysis**
- `Surface.subsurface` — view-slicing without copy ← **occasional value**
- `pygame.PixelArray` — direct pixel access ← **superseded by surfarray**

### 2.4 Advanced / experimental

- `pygame._sdl2.video.Renderer` / `Texture` — hardware-accelerated rendering (different model from Surface-based) ← **research required**
- `pygame.shader` (pygame-ce specific) — shader support, experimental ← **research required**
- OpenGL context via `pygame.display.set_mode(flags=pygame.OPENGL)` — unlocks moderngl integration ← **research required**

---

## 3. BLEND Modes — Full Reference

pygame-ce supports these blend modes via `Surface.blit(..., special_flags=...)`. Each has a specific use case; most are under-leveraged.

| Mode | Formula | Use Cases |
|------|---------|-----------|
| `BLEND_RGB_ADD` | `dst = dst + src` (clamped) | Additive glow, energy weapons, fire, bloom compositing |
| `BLEND_RGB_SUB` | `dst = dst - src` | Negative-light effects, darkness spreading |
| `BLEND_RGB_MULT` | `dst = dst * src / 255` | Shadow overlays, tinting, vignette (multiplied darkening) |
| `BLEND_RGB_MIN` | `dst = min(dst, src)` | "Darken-only" compositing |
| `BLEND_RGB_MAX` | `dst = max(dst, src)` | "Lighten-only" compositing, handy for bloom pass |
| `BLEND_RGBA_ADD` etc. | RGBA variants | Rarely needed over RGB variants |
| `BLEND_PREMULTIPLIED` | Premultiplied-alpha optimized path | Faster alpha blending when assets are pre-multiplied |

**Quick wins from better BLEND usage:**

- **Engine glow** (particles): additive blend with a warm core gradient → realistic thrust glow without hand-painted sprites
- **Vignette** (post-processing): multiply blend with a radial gradient mask → immediate screen-edge darkening
- **Scene tint** (per-system mood): multiply with a full-screen solid color → e.g., cold-blue tint during space combat
- **Critical hit flash** (combat): additive bright-white blit for 1 frame → no asset needed

### 3.1 `SRCALPHA` surface flag

For programmatic generation, creating surfaces with `pygame.SRCALPHA` (or via `Surface.convert_alpha()` after load) is mandatory. Without it, alpha is all-or-nothing, which breaks material shading. **Adopt as a standard practice** — every procedural surface in `procedural.py` starts with SRCALPHA.

---

## 4. surfarray + numpy — The Real Power Tool

`pygame.surfarray` wraps a pygame Surface as a numpy array, enabling vectorized per-pixel operations. This is the single largest capability we're not exploiting.

### 4.1 What it enables

- **Full-screen post-processing at 60 FPS** — palette remapping, lookup tables, chromatic aberration, pixelation, channel shifts
- **Procedural texture generation** — Perlin noise fields, gradients, composited effects, all at numpy speed
- **Pixel-art palette compliance** — snap rendered colors to a palette via numpy nearest-neighbor lookup
- **Material detail passes** — apply wear noise across a shape in one vectorized pass

### 4.2 Standard patterns

**Read/write pixel arrays:**

```python
import numpy as np
import pygame
from pygame import surfarray

surface = pygame.Surface((width, height), pygame.SRCALPHA)
# Modify R channel:
arr = surfarray.pixels3d(surface)   # H, W, 3 for RGB (or pixels_alpha for alpha)
arr[:, :, 0] = np.clip(arr[:, :, 0] + 20, 0, 255)  # brighten red
del arr  # release the pixel lock

# For RGBA including alpha as a 4-channel array:
arr = surfarray.pixels_alpha(surface)  # H, W for alpha only
```

**Palette remapping** (snap to canonical palette):

```python
def snap_to_palette(surface: pygame.Surface, palette: np.ndarray) -> pygame.Surface:
    """palette: (N, 3) array of RGB. Return surface with each pixel snapped to nearest palette color."""
    px = surfarray.pixels3d(surface).astype(np.int32)
    # pixels shape: (H, W, 3); palette: (N, 3)
    # compute distance: (H, W, N)
    dists = np.sum((px[:, :, None, :] - palette[None, None, :, :]) ** 2, axis=-1)
    idx = np.argmin(dists, axis=-1)  # (H, W)
    px[:, :, :] = palette[idx]
    del px
    return surface
```

This single function is how we enforce palette compliance across every procedural output.

**Procedural noise field:**

```python
def perlin_field(width: int, height: int, scale: float, seed: int) -> np.ndarray:
    """Generate a Perlin noise field as (H, W) array in [-1, 1]."""
    from opensimplex import OpenSimplex
    noise = OpenSimplex(seed=seed)
    xs = np.arange(width) * scale
    ys = np.arange(height) * scale
    # Vectorized evaluation — opensimplex returns scalar, so we loop, but fast enough
    field = np.array([[noise.noise2(x, y) for x in xs] for y in ys])
    return field
```

For maximum speed, we'd want a vectorized-native Perlin implementation. See §4.4.

### 4.3 Performance expectations

Rough numbers (will be verified in prototype):

- Full-screen palette remap (1920×1080, 24-entry palette): **~15ms** with `np.argmin` nearest-neighbor → fits comfortably in a 60 FPS frame budget
- Full-screen Perlin generation (1920×1080, opensimplex per-pixel): **~200ms** → too slow per-frame; MUST be cached
- Numpy gaussian blur 1920×1080: **~30ms** → tight but feasible; prefer downsample-blur-upsample for bloom
- `surfarray.pixels3d` unlock/lock overhead: negligible per call

**Rule:** never call a heavy numpy op per frame without caching. Cache keyed on (resolution, seed, parameters). The existing `procedural._cache` structure extends to this.

### 4.4 Native noise libraries

For Perlin/Simplex at speed, we want a native implementation:

- **`noise`** — oldest, C-backed, fast, Perlin + Simplex
- **`opensimplex`** — pure Python but good algorithm; slow for large grids
- **`pyfastnoiselite`** — bindings to FastNoiseLite, excellent performance, many algorithms (cellular/Voronoi included)

**Recommendation:** adopt `pyfastnoiselite` for the performance + feature set. Benchmark in prototype phase before committing.

---

## 5. gfxdraw — Antialiased Primitives

`pygame.gfxdraw` offers antialiased versions of the core `pygame.draw` primitives. Vastly better for smooth sci-fi chrome.

### 5.1 Functions we should use

- `gfxdraw.aacircle` — antialiased circle outline
- `gfxdraw.aapolygon` — antialiased polygon outline
- `gfxdraw.aatrigon` — antialiased triangle outline
- `gfxdraw.bezier` — cubic Bézier curves! Not in `pygame.draw`!

### 5.2 Why this matters

Current rendering uses `pygame.draw` primitives, which are aliased (hard-edged). Against a dark space background, aliased edges are jarring; antialiased edges blend smoothly and read more cleanly.

**Quick adoption pass:** audit `engine/draw_utils.py` and replace every `draw.circle`/`draw.polygon` with `gfxdraw.aacircle`/`aapolygon`. Pair with a filled version (one call aa-outline, one call filled) since `gfxdraw` separates these.

### 5.3 Caveat

`gfxdraw` is considered "experimental" in pygame docs, but pygame-ce has stabilized it. Safe for production.

---

## 6. freetype — Advanced Text

`pygame.freetype` is substantially richer than `pygame.font` (the standard `SysFont`/`Font` interface). We're using the old API.

### 6.1 What freetype adds

- **Outline rendering** — stroked text with adjustable outline width
- **Rotated text** — native rotation support without `transform.rotate`
- **Subpixel positioning** — smoother small-text rendering
- **Per-call style flags** — bold/italic/underline as render-time params
- **Metrics queries** — precise ascender/descender info for layout

### 6.2 Why we'd want it

For our HUD aesthetic (glowing text, outlined labels for readability against varied backgrounds), freetype's outline rendering is dramatically cleaner than blitting text twice (once dark-offset, once in foreground color) as an outline hack.

### 6.3 Migration cost

`engine/fonts.py` wraps pygame.font. A migration to freetype would touch that file primarily, with downstream call sites mostly unchanged if the wrapper preserves its API. **Medium migration effort — defer until the aesthetic bible demands outlined text specifically.**

---

## 7. sndarray — Programmatic Audio

Parallels `surfarray` for audio. Allows us to synthesize sound from numpy arrays — the foundation of the programmatic-audio discipline (see `40_audio_synthesis_framework.md`).

### 7.1 Capabilities

- Create a pygame Sound from a numpy int16 array
- Real-time parameter changes (pitch, duration, harmonics)
- Mix layers procedurally before playback
- No external audio files required for synthesized SFX

### 7.2 Example: weapon blip

```python
import numpy as np
from pygame import sndarray, mixer

def make_blip(frequency_hz: float, duration_s: float, sample_rate: int = 44100) -> mixer.Sound:
    samples = int(duration_s * sample_rate)
    t = np.arange(samples) / sample_rate
    # Square-wave with exponential decay
    wave = np.sign(np.sin(2 * np.pi * frequency_hz * t))
    envelope = np.exp(-3.0 * t)  # decay
    signal = (wave * envelope * 16000).astype(np.int16)
    # Stereo
    stereo = np.column_stack([signal, signal])
    return sndarray.make_sound(stereo)

# One function, thousands of sound variants by tweaking frequency_hz and duration_s.
```

This is exactly the audio parallel to procedural visual generation. The audio framework doc builds on this primitive.

---

## 8. Shader Support (pygame-ce experimental)

pygame-ce added experimental shader support in recent versions. Status as of the research cut: available but considered unstable, with limited examples in the wild.

### 8.1 What it would enable

- Full-screen post-processing at GPU speed
- Bloom, chromatic aberration, vignette, grain — all as GLSL shaders running on the graphics card
- Per-pixel effects that would be prohibitively slow in numpy (at framerate)

### 8.2 The open question

**Does pygame-ce's shader module deliver at production quality, or do we need moderngl integration?**

This is the single most important research question for the post-processing pipeline. If pygame-ce shaders work: the integration is clean, no extra dependencies. If not: we drop in `moderngl` (another Python GL binding) and run shaders there. moderngl is mature and well-documented but adds integration complexity.

### 8.3 Spike to run

In the prototype phase, pick one shader (bloom's extract-blur-composite), implement it both ways: pygame-ce shader and moderngl. Compare frame time, code complexity, integration cost. Decide.

---

## 9. `_sdl2.video` — Hardware-Accelerated Renderer

pygame-ce exposes the SDL2 renderer/texture API via `pygame._sdl2.video`. This is a fundamentally different rendering model from Surface-based rendering.

### 9.1 The model

- `Window` + `Renderer` + `Texture` hierarchy (more like SDL2 native)
- Textures live on the GPU; `Renderer.copy(texture, ...)` issues GPU draw calls
- Surface-based rendering is deprecated in this model (though still works)

### 9.2 Performance

Substantially faster for large numbers of sprites — tens of thousands of draws per frame feasible. Combat scenes, particle swarms, UI with lots of icons all benefit.

### 9.3 Migration cost

**High.** Every `blit` call becomes a `Renderer.copy` against a Texture. Every Surface becomes a Texture. Surface-based procedural generation still works but needs `Texture.from_surface()` conversion. Caches get more complex.

### 9.4 Recommendation

**Defer migration.** The current game does not have a frame-rate problem. Adopting `_sdl2.video` solves a problem we don't yet have. Revisit if profiling reveals CPU-bound rendering after the Programmatic Generation framework lands.

**Exception:** particle systems with 1000+ particles could benefit. Tier 3 `41_vfx_particle_vocabulary.md` may decide to experiment with `_sdl2.video` for the particle renderer specifically, isolated from the rest.

---

## 10. `pygame.mask` — Silhouette Analysis

Underused. `pygame.mask` treats a surface's alpha channel as a bitmask, enabling pixel-precise operations.

### 10.1 What it does

- `Mask.overlap()` — pixel-precise collision between two masks
- `Mask.outline()` — extract the silhouette outline as a point list
- `Mask.connected_component_bounding_rects()` — find connected regions
- Useful for: silhouette readability testing, ship outline extraction for rim lighting, pixel-perfect selection on modules in the builder

### 10.2 Relevance

Primary use in the overhaul: **silhouette extraction** for the ship composite renderer (§6 of the programmatic framework). After rendering modules into a shared target, `Mask.outline()` gives us the ship's outer edge as a point list, which we feed into:
- Rim-lighting pass
- Selection feedback
- Shadow casting
- Thumbnail generation

---

## 11. Integration Matrix: Recommended Stack

Given the capabilities mapped above, the recommended substrate for the overhaul:

| Capability | Implementation | Priority |
|------------|----------------|----------|
| Procedural Surface generation | `pygame.Surface` + `SRCALPHA` + numpy via `surfarray` | **Critical** |
| Per-pixel composition | `surfarray.pixels3d` with vectorized numpy | **Critical** |
| Antialiased primitives | `pygame.gfxdraw` | **High** (quick adoption) |
| Noise fields | `pyfastnoiselite` (pending benchmark) | **High** |
| Blend-mode compositing | `Surface.blit(..., special_flags=BLEND_*)` | **High** |
| Post-processing (bloom/CA/grain) | pygame-ce shader → moderngl fallback | **High** (pending spike) |
| Silhouette extraction | `pygame.mask` | **Medium** |
| Advanced text | `pygame.freetype` | **Medium** (defer until bible demands it) |
| Audio synthesis | `pygame.sndarray` + numpy | **Medium** (parallel track) |
| Hardware-accelerated render | `pygame._sdl2.video` | **Low** (defer; adopt only if needed) |
| Physics | `pymunk` | **Skip** (out of scope) |

---

## 12. External Dependencies We'll Adopt

Beyond pygame-ce, the recommended substrate adds:

- **`numpy`** — already used indirectly (confirm in pyproject). Core for surfarray/sndarray.
- **`pyfastnoiselite`** — noise field generation. ~1MB install, C-backed, fast.
- **`moderngl`** — shader integration IF pygame-ce shaders fall short. ~5MB install.
- **`Pillow` (PIL)** — image I/O, specific filters (e.g., gaussian blur at higher quality than numpy convolve). Optional — adopt only if numpy falls short.

**Total install weight added: ~10-15MB.** Acceptable.

---

## 13. Prototype Spikes

Three spikes will validate or revise this audit.

### Spike A — `surfarray` performance benchmark

- Write `tools/spike_surfarray_bench.py` — runs representative operations (palette remap, noise field, gaussian blur) on full-screen surfaces, reports timings.
- **Success:** palette remap < 20ms; noise generation cached-once acceptable; blur via downsample path fits in 16ms budget.
- **Failure path:** some operation is too slow → need moderngl for that operation OR rethink the pipeline.

### Spike B — Shader integration test

- Two implementations of bloom (extract-blur-additive composite):
  1. `tools/spike_bloom_pygame_ce.py` — uses `pygame.shader` if available
  2. `tools/spike_bloom_moderngl.py` — uses moderngl
- Measure: correctness, frame time, code complexity.
- **Decision:** which pipeline the post-processing framework adopts.

### Spike C — `_sdl2.video` viability

- `tools/spike_sdl2_renderer.py` — port a minimal scene (1 ship, particles, background) to the SDL2 Renderer model.
- Measure: frame time vs Surface-based equivalent.
- **Decision:** whether the migration cost is justified, either now or deferred to post-overhaul.

---

## 14. Decisions This Doc Defers

- **Exact noise library** — pending spike.
- **Shader substrate** (pygame.shader vs moderngl) — pending spike.
- **When (if ever) to migrate to `_sdl2.video`** — pending spike + profiling.
- **Whether to adopt freetype now** — pending bible's text requirements.

---

## 15. Dependencies

**This doc depends on:**
- `00_master_plan.md`
- `10_programmatic_generation_framework.md` (defines what the capabilities are for)

**Docs that depend on this one:**
- All Tier 2 per-system overhauls (use these capabilities)
- `41_vfx_particle_vocabulary.md` (heavy numpy + BLEND usage)
- `42_ui_chrome_components.md` (gfxdraw + freetype)

---

*Next: `12_agentic_graphics_workflow.md`, then run spikes A/B/C from this doc + module/ship/palette spikes from framework doc.*
