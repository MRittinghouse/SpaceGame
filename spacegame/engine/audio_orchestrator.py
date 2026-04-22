"""AudioOrchestrator — scene-aware audio policy on top of AudioManager.

Implements spec §4 (mix discipline: category ceilings, priority culling,
ducking) and spec §5 (music + ambient orchestration rules). Views call
``enter_scene`` when game state changes; the orchestrator handles the
music/ambient transitions per the canonical scene map. It also owns:

  - **Category ceilings** — every SFX category has a hard volume cap
    (spec §3.1), applied on top of the user's SFX volume setting.
  - **Priority-based SFX culling** — at most 4 SFX channels active at once
    (spec §4.2); lower-priority sounds lose to higher-priority ones.
  - **Ducking** — music ducks under dialogue (0.40) and critical SFX
    (0.60), recovers on dialogue end or critical timer expiry (spec §4.3).
  - **Faction overrides** — station hub music follows the docked faction
    where called out (spec §5.1 Crimson Reach override).

The orchestrator drives the low-level :class:`AudioManager` singleton.
Views that previously called ``get_audio_manager().play_music(...)``
should migrate to ``get_audio_orchestrator().enter_scene(...)`` so policy
lives in one place.

See ``requirements/overhaul/40_audio_synthesis_framework.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from spacegame.engine.audio_manager import AudioManager, get_audio_manager

# ---------------------------------------------------------------------------
# Taxonomies
# ---------------------------------------------------------------------------


class AudioScene(Enum):
    """Canonical scene identifiers (spec §5.1 / §5.2)."""

    MAIN_MENU = "main_menu"
    GALAXY_MAP = "galaxy_map"
    STATION_HUB = "station_hub"
    COCKPIT_STATION = "cockpit_station"
    COCKPIT_SPACE = "cockpit_space"
    COMBAT = "combat"
    COMBAT_PRE_ENGAGEMENT = "combat_pre_engagement"
    COMBAT_VICTORY = "combat_victory"
    COMBAT_DEFEAT = "combat_defeat"
    GROUND_STEALTH = "ground_stealth"
    MINING = "mining"
    SALVAGE = "salvage"
    REFINING = "refining"
    DIALOGUE_INTIMATE = "dialogue_intimate"
    DIALOGUE_NEUTRAL = "dialogue_neutral"


class AudioCategory(Enum):
    """SFX categories (spec §3.1). Each has a canonical volume ceiling."""

    COMBAT = "combat"
    MINING = "mining"
    SALVAGE = "salvage"
    TRADING = "trading"
    NAVIGATION = "navigation"
    UI = "ui"
    BUILDER = "builder"
    ACTIVITY = "activity"
    GROUND = "ground"


# Category volume ceilings — spec §3.1.
CATEGORY_CEILINGS: dict[AudioCategory, float] = {
    AudioCategory.COMBAT: 1.0,
    AudioCategory.MINING: 0.75,
    AudioCategory.SALVAGE: 0.70,
    AudioCategory.TRADING: 0.55,
    AudioCategory.NAVIGATION: 0.80,
    AudioCategory.UI: 0.45,
    AudioCategory.BUILDER: 0.60,
    AudioCategory.ACTIVITY: 0.70,
    AudioCategory.GROUND: 0.85,
}


class SFXPriority:
    """Canonical SFX priority tiers (spec §4.2).

    Float values let callers interpolate if they need to. Critical/High
    priorities are "never culled" in practice because 1.0 beats everything.
    """

    CRITICAL = 1.0
    HIGH = 0.8
    NORMAL = 0.6
    LOW = 0.4


# Spec §4.2: 4 channels reserved for SFX (2 for music, 2 for ambient).
MAX_SFX_CHANNELS = 4


# ---------------------------------------------------------------------------
# Scene → music + ambient map
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SceneAudio:
    """Music + ambient configuration for one scene.

    A ``music_id`` of ``None`` means "scene is intentionally silent" — the
    orchestrator stops music on entry. An ``ambient_id`` of ``None`` means
    "this scene does not drive ambient" — the orchestrator leaves the
    existing ambient in place (scene inherits the caller's ambient).
    """

    music_id: Optional[str]
    ambient_id: Optional[str]
    music_fade_in: float = 2.0
    music_fade_out: float = 1.2
    ambient_fade: float = 0.8
    music_loops: bool = True


# Scene-to-music + scene-to-ambient mapping (spec §5.1 + §5.2).
SCENE_MAP: dict[AudioScene, SceneAudio] = {
    AudioScene.MAIN_MENU: SceneAudio(music_id="main_theme", ambient_id=None),
    AudioScene.GALAXY_MAP: SceneAudio(
        music_id="galaxy_exploration", ambient_id="ambient_space"
    ),
    AudioScene.STATION_HUB: SceneAudio(
        music_id="station_hub", ambient_id="ambient_station"
    ),
    AudioScene.COCKPIT_STATION: SceneAudio(
        music_id=None, ambient_id="ambient_station"
    ),
    AudioScene.COCKPIT_SPACE: SceneAudio(music_id=None, ambient_id="ambient_space"),
    AudioScene.COMBAT: SceneAudio(
        music_id="combat_intense",
        ambient_id="ambient_combat",
        music_fade_in=0.5,
    ),
    AudioScene.COMBAT_PRE_ENGAGEMENT: SceneAudio(
        music_id="combat_intense",
        ambient_id="ambient_combat",
        music_fade_in=0.5,
    ),
    AudioScene.COMBAT_VICTORY: SceneAudio(
        music_id="victory_fanfare", ambient_id=None, music_loops=False
    ),
    AudioScene.COMBAT_DEFEAT: SceneAudio(
        music_id="defeat_somber", ambient_id=None, music_loops=False
    ),
    AudioScene.GROUND_STEALTH: SceneAudio(
        music_id="ground_stealth", ambient_id="ambient_ground"
    ),
    AudioScene.MINING: SceneAudio(music_id="mining_rhythm", ambient_id="ambient_space"),
    AudioScene.SALVAGE: SceneAudio(music_id=None, ambient_id="ambient_combat"),
    AudioScene.REFINING: SceneAudio(music_id=None, ambient_id="ambient_station"),
    AudioScene.DIALOGUE_INTIMATE: SceneAudio(
        music_id="dialogue_intimate", ambient_id=None
    ),
    AudioScene.DIALOGUE_NEUTRAL: SceneAudio(
        music_id="dialogue_neutral", ambient_id=None
    ),
}


# Faction overrides for station hub music (spec §5.1). Any faction not in
# this table falls back to the station hub default.
FACTION_STATION_MUSIC_OVERRIDES: dict[str, str] = {
    "crimson_reach": "frontier_danger",
}


# ---------------------------------------------------------------------------
# Ducking constants (spec §4.3)
# ---------------------------------------------------------------------------


_DIALOGUE_MUSIC_DUCK = 0.40
_CRITICAL_MUSIC_DUCK = 0.60
_AMBIENT_UNDER_MUSIC_DUCK = 0.70
_AMBIENT_NORMAL = 1.0
_CRITICAL_DUCK_DURATION = 0.5  # seconds — spec "critical SFX duck + 0.5s fade-back"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class AudioOrchestrator:
    """High-level audio policy driver.

    Wraps an :class:`AudioManager` (inject-testable). Owns scene state,
    ducking state, and priority-based SFX tracking. Views should call
    ``enter_scene``, ``begin_dialogue`` / ``end_dialogue``,
    ``trigger_critical_sfx``, and ``play_sfx`` rather than poking the
    AudioManager directly so policy stays in one place.
    """

    def __init__(self, audio: Optional[AudioManager] = None) -> None:
        self._audio: AudioManager = audio if audio is not None else get_audio_manager()
        self._current_scene: Optional[AudioScene] = None
        self._current_faction: Optional[str] = None
        self._dialogue_active: bool = False
        self._critical_duck_remaining: float = 0.0
        # (channel, priority, category) for active SFX. Channels with
        # get_busy()==False are pruned lazily at next play_sfx call.
        self._active_sfx: list[tuple[Any, float, AudioCategory]] = []

    # ---- state ------------------------------------------------------------

    @property
    def current_scene(self) -> Optional[AudioScene]:
        return self._current_scene

    @property
    def current_faction(self) -> Optional[str]:
        return self._current_faction

    @property
    def dialogue_active(self) -> bool:
        return self._dialogue_active

    @property
    def critical_duck_remaining(self) -> float:
        return self._critical_duck_remaining

    def active_sfx_count(self) -> int:
        """Return the current number of active SFX channels (pruned)."""
        self._prune_finished_sfx()
        return len(self._active_sfx)

    # ---- scene transitions ------------------------------------------------

    def enter_scene(
        self,
        scene: AudioScene,
        faction: Optional[str] = None,
    ) -> None:
        """Transition to the given scene.

        Applies the scene's music + ambient per :data:`SCENE_MAP`. Faction
        overrides (currently only ``crimson_reach`` in :data:`FACTION_
        STATION_MUSIC_OVERRIDES`) swap the music track for the scene when
        applicable.

        Re-entering the same scene with the same faction is a no-op.
        """
        if scene == self._current_scene and faction == self._current_faction:
            return

        config = SCENE_MAP.get(scene)
        if config is None:
            return

        music_id = self._resolve_music_id(scene, faction, config.music_id)

        if music_id is not None:
            self._audio.play_music(
                music_id,
                fade_in=config.music_fade_in,
                loop=config.music_loops,
            )
            # Ambient ducks under music (spec §4.3).
            self._audio.set_ambient_duck(_AMBIENT_UNDER_MUSIC_DUCK)
        else:
            self._audio.stop_music(fade_out=config.music_fade_out)
            self._audio.set_ambient_duck(_AMBIENT_NORMAL)

        if config.ambient_id is not None:
            self._audio.play_ambient(config.ambient_id, fade_in=config.ambient_fade)

        self._current_scene = scene
        self._current_faction = faction

    def _resolve_music_id(
        self,
        scene: AudioScene,
        faction: Optional[str],
        default_music: Optional[str],
    ) -> Optional[str]:
        """Apply faction overrides to the scene's default music id."""
        if scene == AudioScene.STATION_HUB and faction:
            override = FACTION_STATION_MUSIC_OVERRIDES.get(faction)
            if override is not None:
                return override
        return default_music

    # ---- dialogue ducking -------------------------------------------------

    def begin_dialogue(self) -> None:
        """Duck music to the dialogue level. Idempotent."""
        if self._dialogue_active:
            return
        self._dialogue_active = True
        self._audio.set_music_duck(_DIALOGUE_MUSIC_DUCK)

    def end_dialogue(self) -> None:
        """Release dialogue duck. Restores music unless a critical duck
        is still running — the critical duck is less aggressive (0.60 vs
        0.40), so we defer to its timer to fully release."""
        if not self._dialogue_active:
            return
        self._dialogue_active = False
        if self._critical_duck_remaining > 0:
            # Keep the critical-tier duck in place until its timer expires.
            self._audio.set_music_duck(_CRITICAL_MUSIC_DUCK)
        else:
            self._audio.set_music_duck(1.0)

    # ---- critical SFX + ducking -------------------------------------------

    def trigger_critical_sfx(
        self,
        sfx_id: str,
        category: AudioCategory = AudioCategory.COMBAT,
        duck_duration: float = _CRITICAL_DUCK_DURATION,
    ) -> Any:
        """Play a critical-priority SFX and duck music briefly.

        Dialogue duck overrides the critical duck (0.40 < 0.60 — dialogue
        is more aggressive) so if dialogue is active, music stays at the
        dialogue level; the critical timer still advances and the ducking
        state is tracked for when dialogue ends.
        """
        channel = self.play_sfx(sfx_id, category=category, priority=SFXPriority.CRITICAL)
        self._critical_duck_remaining = max(
            self._critical_duck_remaining, duck_duration
        )
        if not self._dialogue_active:
            self._audio.set_music_duck(_CRITICAL_MUSIC_DUCK)
        return channel

    # ---- SFX with category ceilings + priority culling --------------------

    def play_sfx(
        self,
        sfx_id: str,
        category: AudioCategory,
        priority: float = SFXPriority.NORMAL,
    ) -> Any:
        """Play an SFX respecting its category ceiling and the priority queue.

        Returns the :class:`pygame.mixer.Channel` the sound is playing on,
        or ``None`` if the sound was dropped (either audio disabled or
        culled by priority).
        """
        self._prune_finished_sfx()

        if len(self._active_sfx) >= MAX_SFX_CHANNELS:
            # All 4 channels busy — find the lowest-priority slot.
            lowest_idx = min(
                range(len(self._active_sfx)),
                key=lambda i: self._active_sfx[i][1],
            )
            lowest_priority = self._active_sfx[lowest_idx][1]
            if priority <= lowest_priority:
                # Incoming SFX loses — dropped.
                return None
            # Stop the lowest-priority channel to make room.
            victim_channel = self._active_sfx[lowest_idx][0]
            if victim_channel is not None:
                try:
                    victim_channel.stop()
                except Exception:
                    pass
            del self._active_sfx[lowest_idx]

        ceiling = CATEGORY_CEILINGS.get(category, 1.0)
        channel = self._audio.play_sfx(sfx_id, volume=ceiling)
        if channel is not None:
            self._active_sfx.append((channel, priority, category))
        return channel

    def _prune_finished_sfx(self) -> None:
        """Drop channels that are no longer playing."""
        self._active_sfx = [
            (ch, p, cat)
            for ch, p, cat in self._active_sfx
            if ch is not None and self._channel_is_busy(ch)
        ]

    @staticmethod
    def _channel_is_busy(channel: Any) -> bool:
        """Tolerate stub channels that don't implement get_busy()."""
        try:
            return bool(channel.get_busy())
        except Exception:
            return False

    # ---- lifecycle --------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance ducking timers. Call once per frame from the game loop."""
        if dt <= 0:
            return
        if self._critical_duck_remaining > 0:
            self._critical_duck_remaining = max(
                0.0, self._critical_duck_remaining - dt
            )
            if self._critical_duck_remaining == 0 and not self._dialogue_active:
                self._audio.set_music_duck(1.0)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------


_orchestrator: Optional[AudioOrchestrator] = None


def get_audio_orchestrator() -> AudioOrchestrator:
    """Return the process-wide orchestrator singleton.

    The singleton wraps :func:`get_audio_manager`. Tests that need
    isolation should instantiate :class:`AudioOrchestrator` directly with
    an injected AudioManager stub rather than reach for this accessor.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AudioOrchestrator()
    return _orchestrator


def reset_audio_orchestrator() -> None:
    """Drop the cached singleton (tests only)."""
    global _orchestrator
    _orchestrator = None
