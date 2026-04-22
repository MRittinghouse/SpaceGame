"""SkillVoiceOverlay — shared inner-voice overlay primitive (spec §5.7).

Disco Elysium-inspired UI element. Each Tier 2 mini-game (Mining, Salvage,
Refining) registers a small roster of skill voices, then triggers them in
response to gameplay events. The overlay paints a single voice line at a
time, holds it briefly, fades it out, and forgets it. Lines never queue —
the spec is explicit: most-relevant-to-event wins. Callers encode relevance
as a priority integer.

Color per voice is a palette-role reference (``PALETTE_ROLES`` key), so the
overlay stays colorblind-remappable and palette-compliant during the full-
opacity hold. The fade window produces intermediate alpha and is excluded
from strict role compliance — a documented, intentional exception.

See ``requirements/overhaul/42_ui_chrome_components.md §5.7``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from spacegame.engine.fonts import FONT_MD, FONT_SM
from spacegame.engine.material_palette import get_role

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillVoice:
    """Registration payload for one skill voice.

    Every Tier 2 system registers a fixed roster at view construction; the
    roster doesn't change at runtime. ``display_name`` is the small-caps
    label shown above the voice line (e.g. ``"ORE SENSE"``).
    ``color_role`` must be a ``PALETTE_ROLES`` key.
    """

    skill_id: str
    display_name: str
    color_role: str


@dataclass(frozen=True)
class VoiceEvent:
    """Read-only snapshot of the currently-displayed voice line.

    Exposed via :attr:`SkillVoiceOverlay.current` for tests and for views
    that want to inspect overlay state (e.g. for contextual audio cues).
    """

    skill_id: str
    line: str
    priority: int
    elapsed: float


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------


# Timing constants per spec §5.7
_HOLD_SECONDS = 0.8
_FADE_SECONDS = 0.6
_TOTAL_SECONDS = _HOLD_SECONDS + _FADE_SECONDS

# Layout constants (pixel values at 1080p — overlay scales with resolution
# by virtue of the caller passing a resolution-scaled rect).
_PADDING = 6
_LABEL_GAP = 2
_STROKE_OFFSET = 1


class SkillVoiceOverlay:
    """Shared skill-voice overlay (spec §5.7).

    Lifecycle:
      - Construct once per consuming view.
      - Register every skill voice via :meth:`register_voice`.
      - Call :meth:`trigger` in gameplay event handlers.
      - Call :meth:`update(dt)` each frame.
      - Call :meth:`render(surface, rect)` each frame.
    """

    # Exposed as class attributes so callers can reference timing without
    # monkey-patching private state.
    HOLD_SECONDS = _HOLD_SECONDS
    FADE_SECONDS = _FADE_SECONDS
    TOTAL_SECONDS = _TOTAL_SECONDS

    def __init__(self) -> None:
        self._voices: dict[str, SkillVoice] = {}
        # Current: (voice, line, elapsed_seconds, priority) or None.
        self._current: Optional[tuple[SkillVoice, str, float, int]] = None
        # Fonts lazy-initialized so the overlay can be constructed pre-
        # pygame.init() without exploding. First render triggers creation.
        self._label_font: Optional[pygame.font.Font] = None
        self._body_font: Optional[pygame.font.Font] = None

    # ---- registration ------------------------------------------------------

    def register_voice(self, voice: SkillVoice) -> None:
        """Register a skill voice. Re-registration overwrites the prior entry."""
        self._voices[voice.skill_id] = voice

    def voice_ids(self) -> tuple[str, ...]:
        return tuple(self._voices.keys())

    def get_voice(self, skill_id: str) -> Optional[SkillVoice]:
        return self._voices.get(skill_id)

    # ---- state -------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._current is not None

    @property
    def current(self) -> Optional[VoiceEvent]:
        if self._current is None:
            return None
        voice, line, elapsed, priority = self._current
        return VoiceEvent(
            skill_id=voice.skill_id,
            line=line,
            priority=priority,
            elapsed=elapsed,
        )

    def current_alpha(self) -> int:
        """Opacity of the current voice, 0-255.

        Full 255 during the hold phase; linear ramp to 0 across the fade
        phase; 0 when no voice is active.
        """
        if self._current is None:
            return 0
        _, _, elapsed, _ = self._current
        if elapsed < _HOLD_SECONDS:
            return 255
        fade_progress = (elapsed - _HOLD_SECONDS) / _FADE_SECONDS
        return max(0, min(255, round(255 * (1.0 - fade_progress))))

    # ---- interaction -------------------------------------------------------

    def trigger(self, skill_id: str, line: str, priority: int = 0) -> bool:
        """Attempt to display a voice line. Returns True when accepted.

        Priority rules (spec §5.7 "lines don't queue"):
          - Unknown ``skill_id`` → rejected (False).
          - If a voice is already active and the incoming ``priority`` is
            strictly lower than the active priority → rejected.
          - Otherwise the incoming line replaces whatever is showing,
            resetting its hold+fade timer. Equal priority = most recent wins.
        """
        voice = self._voices.get(skill_id)
        if voice is None:
            return False
        if self._current is not None:
            _, _, _, current_priority = self._current
            if priority < current_priority:
                return False
        self._current = (voice, line, 0.0, priority)
        return True

    def clear(self) -> None:
        """Stop displaying the current voice immediately."""
        self._current = None

    def update(self, dt: float) -> None:
        """Advance the display by ``dt`` seconds. Auto-clears when fade completes."""
        if self._current is None or dt <= 0:
            return
        voice, line, elapsed, priority = self._current
        elapsed += dt
        if elapsed >= _TOTAL_SECONDS:
            self._current = None
            return
        self._current = (voice, line, elapsed, priority)

    # ---- rendering ---------------------------------------------------------

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Paint the overlay inside ``rect``.

        Layout inside the rect: skill-name label on top line (dim color),
        italic body line below in the skill's palette role. A 1px stroke
        in ``void_deep`` is drawn beneath the body for legibility.
        """
        if self._current is None:
            return
        alpha = self.current_alpha()
        if alpha == 0:
            return

        voice, line, _, _ = self._current
        self._ensure_fonts()
        assert self._label_font is not None and self._body_font is not None

        label_color = get_role("hud_text_dim")
        body_color = get_role(voice.color_role)
        stroke_color = get_role("void_deep")

        # No antialiasing: the stroke technique + alpha blend with a flat
        # background preserves palette-coloring during the hold phase.
        label_surf = self._label_font.render(voice.display_name, False, label_color)
        body_surf = self._body_font.render(line, False, body_color)
        stroke_surf = self._body_font.render(line, False, stroke_color)

        label_surf.set_alpha(alpha)
        body_surf.set_alpha(alpha)
        stroke_surf.set_alpha(alpha)

        # Anchored at the rect's top-left with padding. Spec says bottom-left
        # corner of the view — callers position the rect; we fill it.
        label_x = rect.left + _PADDING
        label_y = rect.top + _PADDING
        body_x = rect.left + _PADDING
        body_y = label_y + label_surf.get_height() + _LABEL_GAP

        surface.blit(label_surf, (label_x, label_y))

        # 4-direction stroke for subtle outline.
        for dx, dy in (
            (-_STROKE_OFFSET, 0),
            (_STROKE_OFFSET, 0),
            (0, -_STROKE_OFFSET),
            (0, _STROKE_OFFSET),
        ):
            surface.blit(stroke_surf, (body_x + dx, body_y + dy))
        surface.blit(body_surf, (body_x, body_y))

    # ---- internals ---------------------------------------------------------

    def _ensure_fonts(self) -> None:
        """Lazy-create private font instances so italic doesn't leak through
        the shared cache in ``engine.fonts.get_font``."""
        if self._body_font is None:
            body = pygame.font.Font(None, FONT_MD)
            body.set_italic(True)
            self._body_font = body
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, FONT_SM)
