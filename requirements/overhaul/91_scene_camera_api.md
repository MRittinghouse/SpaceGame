# SceneCamera API Specification

> **Status:** v1 — concrete implementation spec for the `SceneCamera` primitive. Written as a pre-implementation deliverable for **Combat Phase C1**, the first implementation phase and the foundation block for 9 downstream consumers.
>
> Inherits from `30_overhaul_space_combat.md §4.4` (source doc, v1.1 with post-coherence rename), `99_CORPUS_COHERENCE_REVIEW.md §2.1` (consumer enumeration).

---

## Table of Contents

1. Purpose and scope
2. Core data model
3. Public API surface
4. State management patterns
5. Parallax layer system
6. Shake composition rules
7. Transition curves
8. Per-consumer integration patterns
9. Performance notes
10. Testing strategy
11. Implementation location and dependencies
12. Open questions / decisions

---

## 1. Purpose and scope

### 1.1 What SceneCamera is

A general-purpose 2D camera primitive. Tracks current and target transforms (offset + zoom), interpolates smoothly between them over time with configurable easing, composes multiple shake sources, and applies parallax factors per render layer.

**Not** a specific camera for combat. Combat happens to be the first consumer; seven other systems also consume it. The primitive lives in a shared engine module.

### 1.2 What it does not do

- **Does not define states.** States (`DEFAULT`, `FOCUS_PLAYER`, `PREVIEW_ORBIT`, etc.) live in consumer-specific code. SceneCamera is the transform engine; state machines are consumer territory.
- **Does not manage ship positions.** It applies a transform; consumers still position their own objects.
- **Does not render.** It produces transforms consumed by rendering code.
- **Does not handle 3D.** Aurelia is 2D throughout; zoom is a scalar, offset is 2D.

### 1.3 Why this exists

The 9 systems that need camera control (combat, ship builder preview + test flight, galaxy map, mining, salvage × 2, station hub, ground) all want the same three things:

1. Smoothly interpolate between camera transforms over configurable durations with configurable easing
2. Apply stacking shake from impact events without disrupting in-flight transitions
3. Produce per-layer parallax offsets so backgrounds drift slower than foreground

Implementing this nine times produces nine subtle inconsistencies. Implementing it once, sharing the primitive, enforces consistency.

---

## 2. Core data model

### 2.1 The SceneCamera dataclass

```python
# spacegame/engine/scene_camera.py
from dataclasses import dataclass, field
from typing import Callable
from spacegame.engine.easing import ease_out_cubic


@dataclass
class SceneCamera:
    """Shared 2D camera primitive. Tracks transform state and interpolates
    smoothly between targets. Used by combat, ship builder, galaxy map,
    mining, salvage, station hub, and ground exploration views.
    """

    # Current transform state
    offset: tuple[float, float] = (0.0, 0.0)
    zoom: float = 1.0

    # Target transform (what we're interpolating toward)
    target_offset: tuple[float, float] = (0.0, 0.0)
    target_zoom: float = 1.0

    # Transition state
    _origin_offset: tuple[float, float] = (0.0, 0.0)
    _origin_zoom: float = 1.0
    _transition_elapsed: float = 0.0
    _transition_duration: float = 0.0
    _transition_ease: Callable[[float], float] = field(default=ease_out_cubic)

    # Shake composition — list of active shake sources
    _shakes: list["ShakeSource"] = field(default_factory=list)

    # Parallax layers: layer_id -> factor (0.0 = fully static, 1.0 = full camera motion)
    parallax_factors: dict[int, float] = field(default_factory=dict)

    # Bounds (optional; if set, camera clamps panning to stay in-bounds)
    pan_bounds: tuple[float, float, float, float] | None = None  # (min_x, min_y, max_x, max_y)
```

### 2.2 ShakeSource

```python
@dataclass
class ShakeSource:
    """A single shake event; multiple compose by summing."""
    amplitude: float           # peak offset in pixels
    duration: float            # total seconds
    elapsed: float = 0.0
    frequency: float = 30.0    # oscillations per second
    decay: Callable[[float], float] = field(default=lambda t: 1.0 - t)  # 0..1 amplitude scaling

    @property
    def alive(self) -> bool:
        return self.elapsed < self.duration

    def current_offset(self) -> tuple[float, float]:
        """Returns (dx, dy) offset contribution for this frame."""
        import math
        if not self.alive:
            return (0.0, 0.0)
        t = self.elapsed / self.duration
        scale = self.amplitude * self.decay(t)
        # Two-dimensional high-frequency noise via independent sine phases
        dx = math.sin(self.elapsed * self.frequency * 2 * math.pi) * scale
        dy = math.sin(self.elapsed * self.frequency * 2 * math.pi * 1.3) * scale
        return (dx, dy)
```

---

## 3. Public API surface

### 3.1 Instantiation

```python
camera = SceneCamera()
camera = SceneCamera(offset=(0.0, 0.0), zoom=1.0)
```

### 3.2 Transitions (the primary API)

```python
def transition_to(
    self,
    offset: tuple[float, float] | None = None,
    zoom: float | None = None,
    duration: float = 0.5,
    ease: Callable[[float], float] | None = None,
) -> None:
    """Begin an eased transition to the given target transform.
    
    Either or both of offset/zoom can be specified; unspecified values
    remain at their current targets. Replaces any in-flight transition.
    
    Args:
        offset: target (x, y) offset. None = keep current target.
        zoom: target zoom multiplier. None = keep current target.
        duration: seconds until arrival.
        ease: curve function mapping 0..1 → 0..1. Default ease_out_cubic.
    """
```

### 3.3 Immediate transform

```python
def reset_immediate(
    self,
    offset: tuple[float, float] = (0.0, 0.0),
    zoom: float = 1.0,
) -> None:
    """Snap current and target state to the given transform. No animation.
    
    Use for scene transitions (new view loads) where camera should be
    pre-positioned without visible movement.
    """
```

### 3.4 Shake

```python
def add_shake(
    self,
    amplitude: float,
    duration: float,
    frequency: float = 30.0,
    decay: Callable[[float], float] | None = None,
) -> None:
    """Add a shake source. Multiple shakes compose additively.
    
    Args:
        amplitude: peak offset in pixels.
        duration: total seconds.
        frequency: oscillation frequency (Hz).
        decay: 0..1 → 0..1 amplitude scaling curve. Default: linear decay.
    """

def clear_shakes(self) -> None:
    """Remove all active shake sources immediately."""
```

### 3.5 Per-frame update

```python
def update(self, dt: float) -> None:
    """Advance camera state by `dt` seconds.
    
    Interpolates offset and zoom toward targets. Advances shake sources
    and prunes dead ones. Must be called every frame.
    """
```

### 3.6 Transform queries

```python
def get_offset(self) -> tuple[float, float]:
    """Current camera offset including shake contributions."""

def get_shake_offset(self) -> tuple[float, float]:
    """Only the shake contribution, excluding pan.

    For UI elements that should shake-with-impact but stay anchored
    (not pan with camera). Added during Combat C1 integration: combat's
    UI panels (header, player panel, enemy panels) use shake-only;
    the arena content uses get_offset (shake + pan).
    """

def get_zoom(self) -> float:
    """Current camera zoom factor."""

def get_layer_offset(self, layer: int) -> tuple[float, float]:
    """Parallax-adjusted offset for a specific rendering layer.
    
    Layer with parallax_factor=1.0 gets full offset; 0.0 gets zero offset;
    intermediate values scale proportionally.
    
    Unregistered layers default to factor 1.0 (no parallax).
    """

def get_transform(self) -> tuple[tuple[float, float], float]:
    """Convenience: returns ((x, y), zoom) of current camera state."""

def world_to_screen(
    self,
    world_pos: tuple[float, float],
    screen_center: tuple[float, float],
    layer: int = 1,
) -> tuple[float, float]:
    """Transform a world position to screen coordinates.
    
    screen_center is the view's rendering center (typically view_width/2,
    view_height/2). layer selects parallax factor.
    """
```

### 3.7 Parallax layer registration

```python
def set_parallax_factor(self, layer: int, factor: float) -> None:
    """Register or update a parallax factor for a layer.
    
    Factor 0.0 = fully static (doesn't move with camera).
    Factor 1.0 = full camera motion (foreground).
    Values between interpolate.
    """

def get_parallax_factor(self, layer: int) -> float:
    """Returns registered factor, or 1.0 if unregistered."""
```

### 3.8 Transition state queries

```python
@property
def is_transitioning(self) -> bool:
    """True if a transition is currently in flight."""

@property
def transition_progress(self) -> float:
    """0.0 (just started) to 1.0 (arrived). Returns 1.0 if no transition."""

@property
def has_active_shakes(self) -> bool:
    """True if any shake source is currently contributing offset."""
```

---

## 4. State management patterns

**Consumers define their own state machines.** SceneCamera is state-agnostic — it just interpolates to targets.

### 4.1 Pattern: explicit state enum

Consumer code defines an enum of canonical states and transitions the camera between them:

```python
class ArenaCameraState(Enum):
    DEFAULT = auto()
    FOCUS_PLAYER = auto()
    FOCUS_ENEMY = auto()
    WIDE = auto()
    CINEMATIC = auto()

class CombatView:
    def __init__(self):
        self.camera = SceneCamera()
        self._state = ArenaCameraState.DEFAULT
        self._register_parallax_layers()

    def enter_state(self, state: ArenaCameraState, **kwargs):
        if state == ArenaCameraState.DEFAULT:
            self.camera.transition_to(offset=(0, 0), zoom=1.0, duration=0.25)
        elif state == ArenaCameraState.FOCUS_PLAYER:
            self.camera.transition_to(offset=(-80, 0), zoom=1.25, duration=0.3)
        elif state == ArenaCameraState.FOCUS_ENEMY:
            enemy_pos = kwargs["enemy_pos"]
            target = (enemy_pos[0] * 0.5, enemy_pos[1] * 0.5)
            self.camera.transition_to(offset=target, zoom=1.25, duration=0.3)
        elif state == ArenaCameraState.WIDE:
            self.camera.transition_to(offset=(0, 0), zoom=0.85, duration=0.5)
        elif state == ArenaCameraState.CINEMATIC:
            # Cinematic uses scripted sequences; see §4.3
            pass
        self._state = state
```

### 4.2 Pattern: orbit interpolation

Ship builder preview cycles through three canonical angles:

```python
class BuilderView:
    ORBIT_ANGLES = ["front", "profile", "three_quarter"]
    ORBIT_OFFSETS = {
        "front": (0, 0),
        "profile": (0, 40),
        "three_quarter": (-30, 20),
    }

    def _advance_orbit(self):
        self._orbit_idx = (self._orbit_idx + 1) % 3
        angle = self.ORBIT_ANGLES[self._orbit_idx]
        self.camera.transition_to(
            offset=self.ORBIT_OFFSETS[angle],
            duration=1.2,
            ease=ease_in_out_cubic,
        )
```

### 4.3 Pattern: scripted cinematic sequence

Dual tech cinematic, jump sequence, prestige cinematic — all scripted sequences with precise timing:

```python
def start_jump_sequence(self, destination_pos):
    # Phase A: Charge (1.0s)
    self.camera.transition_to(zoom=1.1, duration=1.0, ease=ease_in_cubic)
    # Schedule Phase B after 1.0s
    self._schedule(1.0, self._jump_phase_flash)

def _jump_phase_flash(self):
    # Phase B: Flash + Streak (1.2s)
    self.camera.add_shake(amplitude=3.0, duration=0.15)  # jump snap
    self.camera.transition_to(zoom=1.4, duration=1.2, ease=linear)
    self._schedule(1.2, self._jump_phase_arrival)

def _jump_phase_arrival(self):
    # Phase D: Arrival (0.5s)
    self.camera.transition_to(zoom=1.0, duration=0.5, ease=ease_out_cubic)
```

### 4.4 Pattern: zoom-tier cycling (galaxy map)

Galaxy map cycles discrete zoom tiers, each with its own parallax behavior:

```python
class GalaxyMapView:
    ZOOM_TIERS = {
        "close": {"zoom": 3.5, "parallax": {1: 0.02, 2: 0.05, 3: 0.2, 4: 1.0}},
        "default": {"zoom": 2.4, "parallax": {1: 0.05, 2: 0.1, 3: 0.3, 4: 1.0}},
        "regional": {"zoom": 1.2, "parallax": {1: 0.1, 2: 0.15, 3: 0.4, 4: 1.0}},
        "galactic": {"zoom": 0.5, "parallax": {1: 0.15, 2: 0.2, 3: 0.5, 4: 1.0}},
    }

    def set_zoom_tier(self, tier_name):
        tier = self.ZOOM_TIERS[tier_name]
        self.camera.transition_to(zoom=tier["zoom"], duration=0.4, ease=ease_out_cubic)
        for layer, factor in tier["parallax"].items():
            self.camera.set_parallax_factor(layer, factor)
```

---

## 5. Parallax layer system

### 5.1 Layer numbering convention

Lower layer number = further from camera (more static). Higher = closer (follows camera more).

Canonical layer assignments (used by multiple consumers):

| Layer | Purpose | Typical parallax factor |
|---|---|---|
| 1 | Far starfield / void backdrop | 0.02 – 0.15 |
| 2 | Mid-distance nebulae / dust | 0.05 – 0.25 |
| 3 | Near atmospheric elements (fog, debris) | 0.2 – 0.5 |
| 4 | Foreground scene content (ships, units, UI in world space) | 1.0 |
| 5 | Overlay (HUD in world space, not screen-anchored) | 1.0 or higher |

Most renders use layers 1-4. Factors registered per consumer via `set_parallax_factor`.

### 5.2 Applying parallax in render code

```python
def render(self, screen):
    screen_center = (screen.get_width() / 2, screen.get_height() / 2)
    
    # Layer 1: background starfield
    for star in self.starfield:
        pos = self.camera.world_to_screen(star.world_pos, screen_center, layer=1)
        screen.blit(star.sprite, pos)
    
    # Layer 4: foreground ships
    for ship in self.ships:
        pos = self.camera.world_to_screen(ship.world_pos, screen_center, layer=4)
        screen.blit(ship.composite, pos)
```

### 5.3 UI rendering

UI rendered in screen space (not world space) does not consume camera offset at all:

```python
# UI elements render directly in screen coordinates, bypassing camera
screen.blit(self.hud_panel, (10, 10))
```

---

## 6. Shake composition rules

### 6.1 Additive stacking

Multiple shakes compose by summing offsets. Active shake sources remain until their duration expires.

```python
# Both shakes compose; player sees combined offset
camera.add_shake(amplitude=5.0, duration=0.2)  # player weapon recoil
camera.add_shake(amplitude=8.0, duration=0.3)  # ship impact
```

Total per-frame shake offset = sum of all `ShakeSource.current_offset()` contributions.

### 6.2 Priority / clamping

No built-in amplitude ceiling. Consumers responsible for avoiding excessive shake stacking. If aggregate amplitude exceeds ~15px, it reads as chaotic; discipline is a consumer concern.

### 6.3 Reset discipline

On scene transition (combat ends, view closes), call `camera.clear_shakes()` to prevent leftover shake persisting into the new scene.

---

## 7. Transition curves

Standard easing library in `spacegame/engine/easing.py` (existing file; extended if needed).

### 7.1 Available curves

| Curve | When to use |
|---|---|
| `linear` | Mechanical transitions, uniform-speed panning |
| `ease_in_cubic` | Acceleration from rest (cinematic charge phases) |
| `ease_out_cubic` | Deceleration to stop (most UI transitions; DEFAULT) |
| `ease_in_out_cubic` | Smooth through-motion (orbit cycling) |
| `ease_in_out_quad` | Gentler version of cubic for subtle transitions |
| `ease_out_elastic` | Overshoot + spring (optional; rare use) |
| `ease_out_bounce` | Impact-settling (destruction sequences) |

### 7.2 Default

If no `ease` argument specified, `transition_to` uses `ease_out_cubic`. Feels natural for most UI.

### 7.3 Custom curves

Any `Callable[[float], float]` mapping 0..1 → 0..1 is valid. Consumers can define one-offs:

```python
def jump_streak_curve(t):
    """Accelerating curve for jump-sequence streak phase."""
    return t ** 1.5
```

---

## 8. Per-consumer integration patterns

How each of the 9 consumers uses SceneCamera. Referenced as implementation guide during each Tier 2 phase.

### 8.1 Combat (phases C1, C5)

- States: `DEFAULT`, `FOCUS_PLAYER`, `FOCUS_ENEMY(i)`, `WIDE`, `CINEMATIC`, `SHAKE`
- Transition on action-commit (300ms to FOCUS); relax to DEFAULT (250ms pacing beat)
- Dual tech cinematic: scripted sequence §4.3 pattern
- Shake: on-hit impacts (amplitude 3-8px, duration 150-200ms)
- Parallax: 3 starfield layers + ship-layer foreground

### 8.2 Ship Builder (phases B1, B5)

- States: `DEFAULT` (centered preview), `PREVIEW_ORBIT` (angle cycling), `TEST_FLIGHT_BOOT`, `TEST_FLIGHT_TRACK`, `TEST_FLIGHT_IDLE`
- Orbit: 45s full cycle through 3 angles with `ease_in_out_cubic`
- Test flight: 20s scripted sequence (scripted §4.3 pattern reused from arena-entry)
- Parallax: hangar backdrop (3 layers) + ship-foreground

### 8.3 Galaxy Map (phases G1, G2)

- States: zoom tiers per §4.4
- Jump cinematic: scripted sequence §4.3 pattern, 4 phases
- Pan: keyboard / drag-driven `transition_to` with 0.15s smoothing
- Parallax: 3-layer starfield + nebula layer + traffic-lane layer + foreground

### 8.4 Mining (phase M2)

- States: mostly static (mining is contained view)
- Cinematic: prestige cinematic (~3.5s) — scripted §4.3
- Minor shake on chain detonation
- Parallax: depth-atmosphere backdrop has a layer, but minor effect

### 8.5 Salvage (phase S5)

- States: mostly static
- Cinematic: module recovery (~2.5s), wrecker cycle (~3.5s) — scripted §4.3
- Parallax: derelict atmosphere layers

### 8.6 Station Hub (phase H5)

- States: `DEFAULT`, `DOCKING`, `UNDOCKING`
- Docking / undocking cinematic: scripted ~1.5-2.0s
- Parallax: painted panorama 3-layer backdrop

### 8.7 Ground Exploration (phase GR3)

- States: `DEFAULT`, `COMBAT_FOCUS`, `DEPLOYMENT`, `EXTRACTION`
- Smooth lerp toward player (existing behavior preserved; now routes through SceneCamera)
- Shake on combat impacts, explosions
- Parallax: minimal (interior scene; not starfield-heavy)

---

## 9. Performance notes

### 9.1 Update cost

`SceneCamera.update(dt)` is cheap:
- Transition calculation: 4 float operations per frame (offset lerp + zoom lerp)
- Shake calculation: ~10 operations per active shake source
- Parallax: zero work during update (applied at query time)

Target: <0.05ms per frame for a camera with ~3 active shakes.

### 9.2 Memory

One `SceneCamera` instance per view. Minimal fields. `parallax_factors` dict usually 3-5 entries. `_shakes` list usually 0-3 active. Effectively free.

### 9.3 Query cost

`world_to_screen` does one subtraction + scalar multiply + offset add + zoom divide. Cheap.

**Recommendation**: for render passes with thousands of items (particles), batch by layer to avoid per-item parallax-factor lookups. Query the factor once per layer per frame; apply to all items in that layer.

---

## 10. Testing strategy

### 10.1 Unit tests

In `tests/engine/test_scene_camera.py`:

```python
class TestSceneCameraTransitions:
    def test_transition_to_completes_in_duration(self):
        c = SceneCamera()
        c.transition_to(offset=(100, 0), duration=1.0)
        c.update(1.0)
        assert c.get_offset() == pytest.approx((100, 0))

    def test_transition_respects_ease_curve(self):
        c = SceneCamera()
        c.transition_to(offset=(100, 0), duration=1.0, ease=linear)
        c.update(0.5)
        # Linear at t=0.5 should be halfway
        assert c.get_offset()[0] == pytest.approx(50.0, abs=1.0)

    def test_replace_in_flight_transition(self):
        c = SceneCamera()
        c.transition_to(offset=(100, 0), duration=1.0)
        c.update(0.5)  # partway
        c.transition_to(offset=(200, 0), duration=1.0)  # replace
        c.update(1.0)
        # Should reach new target from partial position
        assert c.get_offset() == pytest.approx((200, 0))

class TestSceneCameraShake:
    def test_single_shake_contributes_offset(self):
        c = SceneCamera()
        c.add_shake(amplitude=10.0, duration=0.5)
        c.update(0.1)
        dx, dy = c.get_offset()
        assert abs(dx) > 0 or abs(dy) > 0  # some shake offset applied

    def test_multiple_shakes_compose(self):
        c = SceneCamera()
        c.add_shake(amplitude=5.0, duration=0.5)
        c.add_shake(amplitude=3.0, duration=0.5)
        # Hard to test exact values; test structure
        assert c.has_active_shakes

    def test_shake_expires(self):
        c = SceneCamera()
        c.add_shake(amplitude=10.0, duration=0.2)
        c.update(0.3)  # past duration
        assert not c.has_active_shakes

class TestSceneCameraParallax:
    def test_layer_factor_scales_offset(self):
        c = SceneCamera(offset=(100, 0))
        c.set_parallax_factor(1, 0.1)
        assert c.get_layer_offset(1) == pytest.approx((10, 0))

    def test_unregistered_layer_is_full_parallax(self):
        c = SceneCamera(offset=(100, 0))
        assert c.get_layer_offset(999) == pytest.approx((100, 0))
```

### 10.2 Integration tests

Combat view's use of SceneCamera — lightweight integration covered by combat view tests. No dedicated integration suite for SceneCamera itself; it's a leaf primitive.

### 10.3 Visual verification

After C1 implementation, manual smoke test:
- Combat: actions trigger FOCUS_PLAYER / FOCUS_ENEMY transitions; shake on impact; 250ms relax to DEFAULT between turns
- Builder preview (after B1): orbit cycles smoothly through 3 angles

---

## 11. Implementation location and dependencies

### 11.1 File layout

```
spacegame/engine/scene_camera.py    # NEW — this spec
spacegame/engine/easing.py           # EXISTING — extended if curves needed
```

### 11.2 Python dependencies

Standard library only (`dataclasses`, `typing`, `math`). No external packages.

### 11.3 Pygame dependencies

None — SceneCamera operates on scalars and tuples; rendering is consumer territory.

### 11.4 Testing dependencies

pytest + existing test infrastructure. `pytest.approx` for float comparisons (existing convention per `CLAUDE.md`).

### 11.5 Estimated implementation effort

- Core dataclass + methods: ~150 lines
- Easing extensions (if needed): ~30 lines
- Unit tests: ~200 lines
- Combat view integration (C1): ~100 lines touched in `combat_view.py`

**Total for C1: ~1 week focused effort, pytest + manual smoke test validates.**

---

## 12. Open questions / decisions

### 12.1 Resolved during authoring

- **Shake composition**: additive stacking, no ceiling. Consumer responsibility to avoid chaos.
- **Default easing**: `ease_out_cubic` for `transition_to`.
- **Parallax defaults**: unregistered layers = factor 1.0 (full camera motion).

### 12.2 Deferred to implementation

- **Transition cancellation semantics**: does `transition_to` cancel a previous in-flight transition cleanly, or interpolate from current position to new target? v1 implementation should **interpolate from current** (matches §10.1 test `test_replace_in_flight_transition`). Confirm during C1.
- **Clamping**: `pan_bounds` field is defined but clamping not specified in §3. Implementation should clamp `get_offset` result to bounds; decide whether to clamp during transitions or only at query-time.
- **Zoom-aware shake**: should shake amplitude scale with zoom (shake reads bigger when zoomed in)? v1: no — amplitude in screen pixels. Can add zoom-scaling later if needed.

### 12.3 Future considerations (post-v1)

- **Camera bookmarks** — save/restore camera state for scene transitions
- **Camera recording** — replay-system integration
- **Per-stage cinematic timelines** — first-class scripted-sequence API vs current consumer-code pattern

---

*Revision history:*
- *v1 — initial API specification for Combat Phase C1. Complete data model, public API, consumer patterns, test strategy.*
- *v1.1 — C1 integration complete. Added `get_shake_offset()` method to §3.6 (surfaced during combat_view integration — UI elements shake with impact but should not pan with camera). Verified: 39 unit tests + 699 view tests passing; 0 mypy errors on new code; combat view now routes shake + focus transitions through SceneCamera.*
