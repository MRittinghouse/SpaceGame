"""Tests for the audio manager system."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pygame
import pytest

from spacegame.engine.audio_manager import AudioConfig, AudioManager, get_audio_manager


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    pygame.init()


@pytest.fixture()
def config() -> AudioConfig:
    return AudioConfig()


@pytest.fixture()
def manifest_dir(tmp_path: Path) -> Path:
    """Create a temporary audio directory with a manifest."""
    sfx_dir = tmp_path / "sfx" / "ui"
    sfx_dir.mkdir(parents=True)
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    ambient_dir = tmp_path / "ambient"
    ambient_dir.mkdir()

    manifest = {
        "sfx": {
            "ui_click": {"file": "sfx/ui/ui_click.wav", "volume": 0.7},
            "combat_laser": {"file": "sfx/combat/combat_laser.wav", "volume": 0.9},
        },
        "music": {
            "main_theme": {"file": "music/main_theme.ogg"},
        },
        "ambient": {
            "ambient_station": {"file": "ambient/ambient_station.wav", "volume": 0.5},
        },
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return tmp_path


@pytest.fixture()
def manager() -> AudioManager:
    """Create an AudioManager with mixer disabled for testing."""
    mgr = AudioManager.__new__(AudioManager)
    mgr._enabled = False
    mgr._config = AudioConfig()
    mgr._sfx_cache = {}
    mgr._current_music_id = None
    mgr._current_ambient_id = None
    mgr._ambient_channel = None
    mgr._manifest = {"sfx": {}, "music": {}, "ambient": {}}
    mgr._audio_dir = Path(".")
    mgr._fade_target_volume = None
    mgr._fade_speed = 0.0
    return mgr


class TestAudioConfig:
    """AudioConfig dataclass defaults and behavior."""

    def test_default_volumes(self, config: AudioConfig) -> None:
        assert config.master_volume == 1.0
        assert config.music_volume == 0.7
        assert config.sfx_volume == 0.9
        assert config.ambient_volume == 0.6

    def test_custom_volumes(self) -> None:
        cfg = AudioConfig(master_volume=0.5, music_volume=0.3)
        assert cfg.master_volume == 0.5
        assert cfg.music_volume == 0.3

    def test_to_dict(self, config: AudioConfig) -> None:
        d = config.to_dict()
        assert d["master_volume"] == 1.0
        assert d["music_volume"] == 0.7
        assert d["sfx_volume"] == 0.9
        assert d["ambient_volume"] == 0.6

    def test_from_dict_roundtrip(self) -> None:
        original = AudioConfig(master_volume=0.8, sfx_volume=0.5)
        restored = AudioConfig.from_dict(original.to_dict())
        assert restored.master_volume == original.master_volume
        assert restored.sfx_volume == original.sfx_volume

    def test_from_dict_missing_keys_uses_defaults(self) -> None:
        cfg = AudioConfig.from_dict({})
        assert cfg.master_volume == 1.0
        assert cfg.music_volume == 0.7


class TestAudioManagerDisabled:
    """AudioManager graceful degradation when mixer is unavailable."""

    def test_disabled_manager_play_sfx_noop(self, manager: AudioManager) -> None:
        result = manager.play_sfx("ui_click")
        assert result is None

    def test_disabled_manager_play_music_noop(self, manager: AudioManager) -> None:
        manager.play_music("main_theme")
        assert manager._current_music_id is None

    def test_disabled_manager_play_ambient_noop(self, manager: AudioManager) -> None:
        manager.play_ambient("ambient_station")
        assert manager._current_ambient_id is None

    def test_disabled_manager_stop_music_noop(self, manager: AudioManager) -> None:
        manager.stop_music()  # Should not raise

    def test_disabled_manager_stop_ambient_noop(self, manager: AudioManager) -> None:
        manager.stop_ambient()  # Should not raise

    def test_disabled_manager_update_noop(self, manager: AudioManager) -> None:
        manager.update(0.016)  # Should not raise

    def test_disabled_manager_shutdown_noop(self, manager: AudioManager) -> None:
        manager.shutdown()  # Should not raise


class TestVolumeControl:
    """Volume getters, setters, and clamping."""

    def test_set_master_volume(self, manager: AudioManager) -> None:
        manager.set_master_volume(0.5)
        assert manager._config.master_volume == 0.5

    def test_set_music_volume(self, manager: AudioManager) -> None:
        manager.set_music_volume(0.3)
        assert manager._config.music_volume == 0.3

    def test_set_sfx_volume(self, manager: AudioManager) -> None:
        manager.set_sfx_volume(0.4)
        assert manager._config.sfx_volume == 0.4

    def test_set_ambient_volume(self, manager: AudioManager) -> None:
        manager.set_ambient_volume(0.2)
        assert manager._config.ambient_volume == 0.2

    def test_volume_clamped_high(self, manager: AudioManager) -> None:
        manager.set_master_volume(1.5)
        assert manager._config.master_volume == 1.0

    def test_volume_clamped_low(self, manager: AudioManager) -> None:
        manager.set_master_volume(-0.5)
        assert manager._config.master_volume == 0.0

    def test_effective_sfx_volume(self, manager: AudioManager) -> None:
        manager.set_master_volume(0.5)
        manager.set_sfx_volume(0.8)
        assert manager._effective_sfx_volume() == pytest.approx(0.4)

    def test_effective_music_volume(self, manager: AudioManager) -> None:
        manager.set_master_volume(0.5)
        manager.set_music_volume(0.6)
        assert manager._effective_music_volume() == pytest.approx(0.3)

    def test_effective_ambient_volume(self, manager: AudioManager) -> None:
        manager.set_master_volume(1.0)
        manager.set_ambient_volume(0.5)
        assert manager._effective_ambient_volume() == pytest.approx(0.5)

    def test_get_config_returns_copy(self, manager: AudioManager) -> None:
        cfg = manager.get_config()
        cfg.master_volume = 0.0
        assert manager._config.master_volume != 0.0


class TestManifestLoading:
    """Manifest JSON loading and path resolution."""

    def test_load_manifest(self, manifest_dir: Path) -> None:
        mgr = AudioManager.__new__(AudioManager)
        mgr._enabled = False
        mgr._config = AudioConfig()
        mgr._sfx_cache = {}
        mgr._current_music_id = None
        mgr._current_ambient_id = None
        mgr._ambient_channel = None
        mgr._audio_dir = manifest_dir
        mgr._fade_target_volume = None
        mgr._fade_speed = 0.0
        mgr._load_manifest()

        assert "ui_click" in mgr._manifest["sfx"]
        assert mgr._manifest["sfx"]["ui_click"]["volume"] == 0.7
        assert "main_theme" in mgr._manifest["music"]
        assert "ambient_station" in mgr._manifest["ambient"]

    def test_missing_manifest_uses_empty(self, tmp_path: Path) -> None:
        mgr = AudioManager.__new__(AudioManager)
        mgr._enabled = False
        mgr._config = AudioConfig()
        mgr._sfx_cache = {}
        mgr._current_music_id = None
        mgr._current_ambient_id = None
        mgr._ambient_channel = None
        mgr._audio_dir = tmp_path
        mgr._fade_target_volume = None
        mgr._fade_speed = 0.0
        mgr._load_manifest()

        assert mgr._manifest == {"sfx": {}, "music": {}, "ambient": {}}


class TestSingleton:
    """get_audio_manager() singleton behavior."""

    def test_returns_same_instance(self) -> None:
        import spacegame.engine.audio_manager as mod

        # Reset singleton
        old = mod._audio_manager
        mod._audio_manager = None
        try:
            a = get_audio_manager()
            b = get_audio_manager()
            assert a is b
        finally:
            mod._audio_manager = old


class TestAudioConfigPersistence:
    """AudioConfig serialization round-trip."""

    def test_to_dict_default_values(self) -> None:
        config = AudioConfig()
        d = config.to_dict()
        assert d["master_volume"] == 1.0
        assert d["music_volume"] == 0.7
        assert d["sfx_volume"] == 0.9
        assert d["ambient_volume"] == 0.6

    def test_round_trip(self) -> None:
        config = AudioConfig(
            master_volume=0.5, music_volume=0.3, sfx_volume=1.0, ambient_volume=0.0
        )
        d = config.to_dict()
        restored = AudioConfig.from_dict(d)
        assert restored.master_volume == 0.5
        assert restored.music_volume == 0.3
        assert restored.sfx_volume == 1.0
        assert restored.ambient_volume == 0.0

    def test_from_dict_missing_keys_uses_defaults(self) -> None:
        restored = AudioConfig.from_dict({"master_volume": 0.8})
        assert restored.master_volume == 0.8
        assert restored.music_volume == 0.7  # default
        assert restored.sfx_volume == 0.9  # default

    def test_from_dict_empty_uses_all_defaults(self) -> None:
        restored = AudioConfig.from_dict({})
        assert restored.master_volume == 1.0


class TestSettingsPersistence:
    """SaveManager settings.json persistence."""

    def test_save_and_load_settings(self, tmp_path: Path) -> None:
        from spacegame.save_manager import SaveManager

        mgr = SaveManager(tmp_path / "saves")
        mgr.save_settings({"audio": {"master_volume": 0.5, "music_volume": 0.3}})

        loaded = mgr.load_settings()
        assert loaded["audio"]["master_volume"] == 0.5
        assert loaded["audio"]["music_volume"] == 0.3

    def test_load_settings_no_file(self, tmp_path: Path) -> None:
        from spacegame.save_manager import SaveManager

        mgr = SaveManager(tmp_path / "saves")
        loaded = mgr.load_settings()
        assert loaded == {}

    def test_audio_config_through_settings(self, tmp_path: Path) -> None:
        from spacegame.save_manager import SaveManager

        mgr = SaveManager(tmp_path / "saves")
        config = AudioConfig(
            master_volume=0.4, music_volume=0.6, sfx_volume=0.8, ambient_volume=0.2
        )
        mgr.save_settings({"audio": config.to_dict()})

        loaded = mgr.load_settings()
        restored = AudioConfig.from_dict(loaded["audio"])
        assert restored.master_volume == 0.4
        assert restored.music_volume == 0.6
        assert restored.sfx_volume == 0.8
        assert restored.ambient_volume == 0.2

    def test_instance_is_audio_manager(self) -> None:
        import spacegame.engine.audio_manager as mod

        old = mod._audio_manager
        mod._audio_manager = None
        try:
            mgr = get_audio_manager()
            assert isinstance(mgr, AudioManager)
        finally:
            mod._audio_manager = old
