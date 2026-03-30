"""Audio system for music, SFX, and ambient sound playback.

Provides a singleton AudioManager accessed via get_audio_manager().
Gracefully degrades to no-op if pygame.mixer fails to initialize.
"""

import json
from dataclasses import dataclass
from typing import Optional

import pygame

from spacegame.config import (
    AUDIO_DIR,
    DEFAULT_AMBIENT_VOLUME,
    DEFAULT_MASTER_VOLUME,
    DEFAULT_MUSIC_VOLUME,
    DEFAULT_SFX_VOLUME,
    MUSIC_FADE_MS,
)
from spacegame.utils.logger import logger


@dataclass
class AudioConfig:
    """Persistent audio volume settings."""

    master_volume: float = DEFAULT_MASTER_VOLUME
    music_volume: float = DEFAULT_MUSIC_VOLUME
    sfx_volume: float = DEFAULT_SFX_VOLUME
    ambient_volume: float = DEFAULT_AMBIENT_VOLUME

    def to_dict(self) -> dict[str, float]:
        """Serialize to dict for save system."""
        return {
            "master_volume": self.master_volume,
            "music_volume": self.music_volume,
            "sfx_volume": self.sfx_volume,
            "ambient_volume": self.ambient_volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "AudioConfig":
        """Restore from saved dict."""
        return cls(
            master_volume=data.get("master_volume", DEFAULT_MASTER_VOLUME),
            music_volume=data.get("music_volume", DEFAULT_MUSIC_VOLUME),
            sfx_volume=data.get("sfx_volume", DEFAULT_SFX_VOLUME),
            ambient_volume=data.get("ambient_volume", DEFAULT_AMBIENT_VOLUME),
        )


class AudioManager:
    """Singleton audio system for music, SFX, and ambient sounds.

    Access via get_audio_manager(). All methods are safe to call even when
    audio is disabled — they become no-ops.
    """

    def __init__(self) -> None:
        self._config = AudioConfig()
        self._sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self._current_music_id: Optional[str] = None
        self._current_ambient_id: Optional[str] = None
        self._ambient_channel: Optional[pygame.mixer.Channel] = None
        self._manifest: dict[str, dict] = {"sfx": {}, "music": {}, "ambient": {}}
        self._audio_dir = AUDIO_DIR
        self._fade_target_volume: Optional[float] = None
        self._fade_speed: float = 0.0

        # Check if mixer is initialized
        self._enabled = pygame.mixer.get_init() is not None
        if not self._enabled:
            logger.warning("Audio mixer not initialized; audio disabled")
            return

        logger.info("Audio system initialized")
        self._load_manifest()

    def _load_manifest(self) -> None:
        """Load audio manifest mapping IDs to file paths."""
        manifest_path = self._audio_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning("No audio manifest found at %s", manifest_path)
            self._manifest = {"sfx": {}, "music": {}, "ambient": {}}
            return

        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
            self._manifest = {
                "sfx": data.get("sfx", {}),
                "music": data.get("music", {}),
                "ambient": data.get("ambient", {}),
            }
            sfx_count = len(self._manifest["sfx"])
            music_count = len(self._manifest["music"])
            ambient_count = len(self._manifest["ambient"])
            logger.info(
                "Audio manifest loaded: %d SFX, %d music, %d ambient",
                sfx_count,
                music_count,
                ambient_count,
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load audio manifest: %s", e)
            self._manifest = {"sfx": {}, "music": {}, "ambient": {}}

    # === Volume control ===

    def _clamp(self, value: float) -> float:
        """Clamp volume to 0.0–1.0."""
        return max(0.0, min(1.0, value))

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0–1.0)."""
        self._config.master_volume = self._clamp(volume)
        self._apply_volumes()

    def set_music_volume(self, volume: float) -> None:
        """Set music volume (0.0–1.0)."""
        self._config.music_volume = self._clamp(volume)
        self._apply_volumes()

    def set_sfx_volume(self, volume: float) -> None:
        """Set SFX volume (0.0–1.0)."""
        self._config.sfx_volume = self._clamp(volume)

    def set_ambient_volume(self, volume: float) -> None:
        """Set ambient volume (0.0–1.0)."""
        self._config.ambient_volume = self._clamp(volume)
        self._apply_volumes()

    def _effective_sfx_volume(self) -> float:
        """Compute effective SFX volume (master * sfx)."""
        return self._config.master_volume * self._config.sfx_volume

    def _effective_music_volume(self) -> float:
        """Compute effective music volume (master * music)."""
        return self._config.master_volume * self._config.music_volume

    def _effective_ambient_volume(self) -> float:
        """Compute effective ambient volume (master * ambient)."""
        return self._config.master_volume * self._config.ambient_volume

    def _apply_volumes(self) -> None:
        """Apply current volume levels to active playback."""
        if not self._enabled:
            return
        pygame.mixer.music.set_volume(self._effective_music_volume())
        if self._ambient_channel and self._ambient_channel.get_busy():
            self._ambient_channel.set_volume(self._effective_ambient_volume())

    def get_config(self) -> AudioConfig:
        """Get a copy of the current audio config."""
        return AudioConfig(
            master_volume=self._config.master_volume,
            music_volume=self._config.music_volume,
            sfx_volume=self._config.sfx_volume,
            ambient_volume=self._config.ambient_volume,
        )

    def set_config(self, config: AudioConfig) -> None:
        """Apply a full audio config (e.g., from save data)."""
        self._config = AudioConfig(
            master_volume=self._clamp(config.master_volume),
            music_volume=self._clamp(config.music_volume),
            sfx_volume=self._clamp(config.sfx_volume),
            ambient_volume=self._clamp(config.ambient_volume),
        )
        self._apply_volumes()

    # === SFX ===

    def play_sfx(self, sfx_id: str, volume: float = 1.0) -> Optional[pygame.mixer.Channel]:
        """Play a sound effect by ID.

        Args:
            sfx_id: Sound effect ID from manifest.
            volume: Per-sound volume multiplier (0.0–1.0).

        Returns:
            Channel the sound is playing on, or None.
        """
        if not self._enabled:
            return None

        sound = self._get_sfx(sfx_id)
        if sound is None:
            return None

        # Get manifest default volume
        entry = self._manifest["sfx"].get(sfx_id, {})
        default_vol = entry.get("volume", 1.0)
        effective = self._effective_sfx_volume() * default_vol * self._clamp(volume)
        sound.set_volume(effective)

        channel = sound.play()
        return channel

    def _get_sfx(self, sfx_id: str) -> Optional[pygame.mixer.Sound]:
        """Load and cache a sound effect."""
        if sfx_id in self._sfx_cache:
            return self._sfx_cache[sfx_id]

        entry = self._manifest["sfx"].get(sfx_id)
        if entry is None:
            logger.debug("SFX '%s' not in manifest", sfx_id)
            return None

        file_path = self._audio_dir / entry["file"]
        if not file_path.exists():
            logger.warning("SFX file missing: %s", file_path)
            return None

        try:
            sound = pygame.mixer.Sound(str(file_path))
            self._sfx_cache[sfx_id] = sound
            return sound
        except pygame.error as e:
            logger.error("Failed to load SFX '%s': %s", sfx_id, e)
            return None

    # === Music ===

    def play_music(self, music_id: str, fade_in: float = 0.5, loop: bool = True) -> None:
        """Start playing a music track.

        Args:
            music_id: Music ID from manifest.
            fade_in: Fade-in duration in seconds.
            loop: Whether to loop the track.
        """
        if not self._enabled:
            return

        if music_id == self._current_music_id:
            return  # Already playing

        entry = self._manifest["music"].get(music_id)
        if entry is None:
            logger.debug("Music '%s' not in manifest", music_id)
            return

        file_path = self._audio_dir / entry["file"]
        if not file_path.exists():
            logger.warning("Music file missing: %s", file_path)
            return

        try:
            loops = -1 if loop else 0
            fade_ms = int(fade_in * 1000)

            # Fade out current, then start new
            if self._current_music_id is not None:
                pygame.mixer.music.fadeout(min(fade_ms, MUSIC_FADE_MS))

            pygame.mixer.music.load(str(file_path))
            pygame.mixer.music.set_volume(self._effective_music_volume())
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self._current_music_id = music_id
            logger.info("Playing music: %s", music_id)
        except pygame.error as e:
            logger.error("Failed to play music '%s': %s", music_id, e)

    def stop_music(self, fade_out: float = 1.0) -> None:
        """Stop music with optional fade-out.

        Args:
            fade_out: Fade-out duration in seconds.
        """
        if not self._enabled:
            return
        pygame.mixer.music.fadeout(int(fade_out * 1000))
        self._current_music_id = None

    def pause_music(self) -> None:
        """Pause music playback."""
        if not self._enabled:
            return
        pygame.mixer.music.pause()

    def resume_music(self) -> None:
        """Resume paused music."""
        if not self._enabled:
            return
        pygame.mixer.music.unpause()

    # === Ambient ===

    def play_ambient(self, ambient_id: str, fade_in: float = 1.0) -> None:
        """Start an ambient sound loop.

        Args:
            ambient_id: Ambient sound ID from manifest.
            fade_in: Fade-in duration in seconds (applied as volume ramp).
        """
        if not self._enabled:
            return

        if ambient_id == self._current_ambient_id:
            return

        entry = self._manifest["ambient"].get(ambient_id)
        if entry is None:
            logger.debug("Ambient '%s' not in manifest", ambient_id)
            return

        file_path = self._audio_dir / entry["file"]
        if not file_path.exists():
            logger.warning("Ambient file missing: %s", file_path)
            return

        # Stop current ambient
        self.stop_ambient(fade_out=0.3)

        try:
            sound = pygame.mixer.Sound(str(file_path))
            default_vol = entry.get("volume", 1.0)
            effective = self._effective_ambient_volume() * default_vol

            # Set the Sound object's volume BEFORE playing so the fade-in
            # ramps toward the correct target instead of the default 1.0
            sound.set_volume(effective)
            self._ambient_channel = sound.play(loops=-1, fade_ms=int(fade_in * 1000))
            if self._ambient_channel:
                self._ambient_channel.set_volume(effective)
            self._current_ambient_id = ambient_id
            logger.info("Playing ambient: %s (vol=%.2f)", ambient_id, effective)
        except pygame.error as e:
            logger.error("Failed to play ambient '%s': %s", ambient_id, e)

    def stop_ambient(self, fade_out: float = 1.0) -> None:
        """Stop ambient sound with fade-out.

        Args:
            fade_out: Fade-out duration in seconds.
        """
        if not self._enabled:
            return
        if self._ambient_channel and self._ambient_channel.get_busy():
            self._ambient_channel.fadeout(int(fade_out * 1000))
        self._current_ambient_id = None
        self._ambient_channel = None

    # === Lifecycle ===

    def update(self, dt: float) -> None:
        """Update audio state each frame.

        Args:
            dt: Delta time in seconds.
        """
        if not self._enabled:
            return
        # Future: fade management, dynamic music layering

    def shutdown(self) -> None:
        """Clean up audio resources."""
        if not self._enabled:
            return
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        self._sfx_cache.clear()
        self._current_music_id = None
        self._current_ambient_id = None
        self._ambient_channel = None
        logger.info("Audio system shut down")


# Singleton
_audio_manager: Optional[AudioManager] = None


def get_audio_manager() -> AudioManager:
    """Get the global AudioManager instance.

    Creates the instance on first call. Safe to call before mixer init —
    will create a disabled manager.

    Returns:
        The AudioManager singleton.
    """
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioManager()
    return _audio_manager
