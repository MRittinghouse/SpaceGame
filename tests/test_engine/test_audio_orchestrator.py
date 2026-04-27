"""Tests for AudioOrchestrator.

Covers scene mapping, faction overrides, dialogue/critical ducking,
category ceilings, priority-based SFX culling, and the AudioManager
duck multipliers the orchestrator depends on.

Uses a StubAudioManager to observe calls deterministically — no pygame
mixer required.

See ``requirements/overhaul/40_audio_synthesis_framework.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pytest

from spacegame.engine.audio_manager import AudioConfig
from spacegame.engine.audio_orchestrator import (
    CATEGORY_CEILINGS,
    FACTION_STATION_MUSIC_OVERRIDES,
    MAX_SFX_CHANNELS,
    SCENE_MAP,
    AudioCategory,
    AudioOrchestrator,
    AudioScene,
    SFXPriority,
)

# ---------------------------------------------------------------------------
# Stub audio plumbing
# ---------------------------------------------------------------------------


@dataclass
class StubChannel:
    """Minimal Channel stand-in for priority-culling tests."""

    is_busy: bool = True

    def get_busy(self) -> bool:
        return self.is_busy

    def stop(self) -> None:
        self.is_busy = False


@dataclass
class MusicCall:
    music_id: str
    fade_in: float
    loop: bool


@dataclass
class AmbientCall:
    ambient_id: str
    fade_in: float


@dataclass
class SFXCall:
    sfx_id: str
    volume: float


@dataclass
class StubAudioManager:
    """AudioManager-compatible double. Records every call."""

    music_calls: list[MusicCall] = field(default_factory=list)
    music_stop_calls: list[float] = field(default_factory=list)
    ambient_calls: list[AmbientCall] = field(default_factory=list)
    sfx_calls: list[SFXCall] = field(default_factory=list)
    music_duck_history: list[float] = field(default_factory=list)
    ambient_duck_history: list[float] = field(default_factory=list)
    # Channel factory — each play_sfx returns a new channel so the
    # orchestrator tracks priorities separately.
    _next_channel: Optional[StubChannel] = None

    def set_next_channel(self, channel: Optional[StubChannel]) -> None:
        """Override what the next play_sfx call returns."""
        self._next_channel = channel

    def play_music(self, music_id: str, fade_in: float = 0.5, loop: bool = True) -> None:
        self.music_calls.append(MusicCall(music_id=music_id, fade_in=fade_in, loop=loop))

    def stop_music(self, fade_out: float = 1.0) -> None:
        self.music_stop_calls.append(fade_out)

    def play_ambient(self, ambient_id: str, fade_in: float = 1.0) -> None:
        self.ambient_calls.append(AmbientCall(ambient_id=ambient_id, fade_in=fade_in))

    def stop_ambient(self, fade_out: float = 1.0) -> None:
        pass

    def play_sfx(self, sfx_id: str, volume: float = 1.0) -> Optional[StubChannel]:
        self.sfx_calls.append(SFXCall(sfx_id=sfx_id, volume=volume))
        if self._next_channel is not None:
            ch = self._next_channel
            self._next_channel = None
            return ch
        return StubChannel()

    def set_music_duck(self, factor: float) -> None:
        self.music_duck_history.append(factor)

    def set_ambient_duck(self, factor: float) -> None:
        self.ambient_duck_history.append(factor)

    def get_music_duck(self) -> float:
        return self.music_duck_history[-1] if self.music_duck_history else 1.0

    def get_ambient_duck(self) -> float:
        return self.ambient_duck_history[-1] if self.ambient_duck_history else 1.0


def _orchestrator() -> tuple[AudioOrchestrator, StubAudioManager]:
    stub = StubAudioManager()
    return AudioOrchestrator(audio=stub), stub  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Category ceilings + taxonomy
# ---------------------------------------------------------------------------


class TestAudioCategoryCeilings:
    def test_every_category_has_ceiling(self) -> None:
        for cat in AudioCategory:
            assert cat in CATEGORY_CEILINGS, f"{cat.name} missing a ceiling"

    def test_ceilings_in_valid_range(self) -> None:
        for cat, ceiling in CATEGORY_CEILINGS.items():
            assert 0.0 < ceiling <= 1.0, f"{cat.name} ceiling {ceiling} out of range"

    def test_combat_ceiling_is_1(self) -> None:
        assert CATEGORY_CEILINGS[AudioCategory.COMBAT] == 1.0

    def test_ui_ceiling_quieter_than_combat(self) -> None:
        assert CATEGORY_CEILINGS[AudioCategory.UI] < CATEGORY_CEILINGS[AudioCategory.COMBAT]


class TestSFXPriorityTiers:
    def test_priorities_ordered(self) -> None:
        assert SFXPriority.CRITICAL > SFXPriority.HIGH
        assert SFXPriority.HIGH > SFXPriority.NORMAL
        assert SFXPriority.NORMAL > SFXPriority.LOW


# ---------------------------------------------------------------------------
# Scene map
# ---------------------------------------------------------------------------


class TestSceneMap:
    def test_every_scene_has_mapping(self) -> None:
        for scene in AudioScene:
            assert scene in SCENE_MAP, f"{scene.name} missing scene mapping"

    def test_combat_pre_engagement_uses_fast_fade(self) -> None:
        """Spec §5.3: combat music entry on engagement = 0.5s fade-in."""
        cfg = SCENE_MAP[AudioScene.COMBAT_PRE_ENGAGEMENT]
        assert cfg.music_fade_in == 0.5

    def test_victory_and_defeat_do_not_loop(self) -> None:
        """Spec §3.2: resolution tier (victory/defeat) is one-shot."""
        assert SCENE_MAP[AudioScene.COMBAT_VICTORY].music_loops is False
        assert SCENE_MAP[AudioScene.COMBAT_DEFEAT].music_loops is False

    def test_cockpit_scenes_have_no_music(self) -> None:
        """Spec §5.1: cockpit idle is intentionally silent."""
        assert SCENE_MAP[AudioScene.COCKPIT_SPACE].music_id is None
        assert SCENE_MAP[AudioScene.COCKPIT_STATION].music_id is None

    def test_silence_scenes(self) -> None:
        """Spec §5.5: salvage + refining use silence as signal."""
        assert SCENE_MAP[AudioScene.SALVAGE].music_id is None
        assert SCENE_MAP[AudioScene.REFINING].music_id is None


# ---------------------------------------------------------------------------
# enter_scene
# ---------------------------------------------------------------------------


class TestEnterScene:
    def test_enter_scene_with_music_plays_track(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP)
        assert len(stub.music_calls) == 1
        assert stub.music_calls[0].music_id == "galaxy_exploration"

    def test_enter_scene_plays_ambient(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP)
        assert len(stub.ambient_calls) == 1
        assert stub.ambient_calls[0].ambient_id == "ambient_space"

    def test_enter_silent_scene_stops_music(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.COCKPIT_SPACE)
        assert stub.music_calls == []
        assert len(stub.music_stop_calls) == 1

    def test_enter_scene_is_idempotent(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP)
        orch.enter_scene(AudioScene.GALAXY_MAP)
        assert len(stub.music_calls) == 1
        assert len(stub.ambient_calls) == 1

    def test_re_enter_same_scene_different_faction_not_idempotent(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.STATION_HUB)
        orch.enter_scene(AudioScene.STATION_HUB, faction="crimson_reach")
        assert len(stub.music_calls) == 2

    def test_current_scene_tracked(self) -> None:
        orch, _ = _orchestrator()
        orch.enter_scene(AudioScene.MINING)
        assert orch.current_scene == AudioScene.MINING

    def test_current_faction_tracked(self) -> None:
        orch, _ = _orchestrator()
        orch.enter_scene(AudioScene.STATION_HUB, faction="commerce_guild")
        assert orch.current_faction == "commerce_guild"

    def test_enter_scene_ducks_ambient_under_music(self) -> None:
        """Spec §4.3: when music plays, ambient → 70%."""
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP)
        assert stub.ambient_duck_history[-1] == pytest.approx(0.70)

    def test_enter_silent_scene_releases_ambient_duck(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP)  # music plays → ambient ducks
        orch.enter_scene(AudioScene.COCKPIT_SPACE)  # silent → ambient restored
        assert stub.ambient_duck_history[-1] == pytest.approx(1.0)

    def test_victory_scene_uses_one_shot(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.COMBAT_VICTORY)
        assert stub.music_calls[0].loop is False


# ---------------------------------------------------------------------------
# Faction overrides
# ---------------------------------------------------------------------------


class TestFactionOverrides:
    def test_crimson_reach_overrides_station_hub_music(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.STATION_HUB, faction="crimson_reach")
        assert stub.music_calls[0].music_id == "frontier_danger"

    def test_other_factions_use_station_default(self) -> None:
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.STATION_HUB, faction="commerce_guild")
        assert stub.music_calls[0].music_id == "station_hub"

    def test_faction_override_only_applies_to_station(self) -> None:
        """A faction tag on non-station scenes doesn't swap music."""
        orch, stub = _orchestrator()
        orch.enter_scene(AudioScene.GALAXY_MAP, faction="crimson_reach")
        assert stub.music_calls[0].music_id == "galaxy_exploration"

    def test_crimson_reach_override_is_canonical(self) -> None:
        """Ensures the override table matches spec §5.1."""
        assert FACTION_STATION_MUSIC_OVERRIDES.get("crimson_reach") == "frontier_danger"


# ---------------------------------------------------------------------------
# Dialogue ducking
# ---------------------------------------------------------------------------


class TestDialogueDucking:
    def test_begin_dialogue_sets_duck(self) -> None:
        orch, stub = _orchestrator()
        orch.begin_dialogue()
        assert stub.music_duck_history[-1] == pytest.approx(0.40)
        assert orch.dialogue_active

    def test_end_dialogue_restores_music(self) -> None:
        orch, stub = _orchestrator()
        orch.begin_dialogue()
        orch.end_dialogue()
        assert stub.music_duck_history[-1] == pytest.approx(1.0)
        assert not orch.dialogue_active

    def test_double_begin_is_noop(self) -> None:
        orch, stub = _orchestrator()
        orch.begin_dialogue()
        before = len(stub.music_duck_history)
        orch.begin_dialogue()
        assert len(stub.music_duck_history) == before

    def test_end_without_begin_is_noop(self) -> None:
        orch, stub = _orchestrator()
        orch.end_dialogue()
        assert stub.music_duck_history == []

    def test_end_dialogue_preserves_critical_duck_if_active(self) -> None:
        """If a critical-SFX duck is still running, dialogue-end drops to
        the critical duck level (0.60), not full volume."""
        orch, stub = _orchestrator()
        orch.trigger_critical_sfx("combat_explosion", category=AudioCategory.COMBAT)
        orch.begin_dialogue()  # dialogue duck overrides
        orch.end_dialogue()
        assert stub.music_duck_history[-1] == pytest.approx(0.60)


# ---------------------------------------------------------------------------
# Critical-SFX ducking
# ---------------------------------------------------------------------------


class TestCriticalSFXDuck:
    def test_triggers_plays_sfx_at_combat_ceiling(self) -> None:
        orch, stub = _orchestrator()
        orch.trigger_critical_sfx("combat_explosion")
        # Volume passed to play_sfx is the combat category ceiling (1.0).
        assert stub.sfx_calls[-1].volume == pytest.approx(1.0)

    def test_applies_music_duck(self) -> None:
        orch, stub = _orchestrator()
        orch.trigger_critical_sfx("combat_explosion")
        assert stub.music_duck_history[-1] == pytest.approx(0.60)

    def test_critical_duck_expires_via_update(self) -> None:
        orch, stub = _orchestrator()
        orch.trigger_critical_sfx("combat_explosion", duck_duration=0.5)
        orch.update(0.6)  # past fade window
        assert stub.music_duck_history[-1] == pytest.approx(1.0)

    def test_critical_duck_does_not_override_dialogue_duck(self) -> None:
        """Dialogue duck (0.40) is more aggressive than critical (0.60);
        dialogue should stay in effect even during a critical trigger."""
        orch, stub = _orchestrator()
        orch.begin_dialogue()
        assert stub.music_duck_history[-1] == pytest.approx(0.40)
        orch.trigger_critical_sfx("combat_explosion")
        assert stub.music_duck_history[-1] == pytest.approx(0.40)

    def test_critical_duck_does_not_restore_if_dialogue_still_active(self) -> None:
        orch, stub = _orchestrator()
        orch.begin_dialogue()
        orch.trigger_critical_sfx("combat_explosion", duck_duration=0.5)
        orch.update(1.0)  # past fade window, but dialogue still active
        assert stub.music_duck_history[-1] == pytest.approx(0.40)


# ---------------------------------------------------------------------------
# Category ceiling applied to play_sfx
# ---------------------------------------------------------------------------


class TestCategoryCeilingApplied:
    def test_ui_sfx_uses_ui_ceiling(self) -> None:
        orch, stub = _orchestrator()
        orch.play_sfx("ui_click", category=AudioCategory.UI)
        assert stub.sfx_calls[-1].volume == pytest.approx(CATEGORY_CEILINGS[AudioCategory.UI])

    def test_combat_sfx_uses_combat_ceiling(self) -> None:
        orch, stub = _orchestrator()
        orch.play_sfx("combat_hit", category=AudioCategory.COMBAT)
        assert stub.sfx_calls[-1].volume == pytest.approx(CATEGORY_CEILINGS[AudioCategory.COMBAT])


# ---------------------------------------------------------------------------
# Priority-based SFX culling
# ---------------------------------------------------------------------------


class TestPriorityCulling:
    def test_first_four_sfx_play_freely(self) -> None:
        orch, stub = _orchestrator()
        for i in range(MAX_SFX_CHANNELS):
            orch.play_sfx(f"sfx_{i}", category=AudioCategory.UI, priority=SFXPriority.NORMAL)
        assert len(stub.sfx_calls) == MAX_SFX_CHANNELS

    def test_fifth_lower_priority_is_dropped(self) -> None:
        orch, stub = _orchestrator()
        for i in range(MAX_SFX_CHANNELS):
            orch.play_sfx(f"sfx_{i}", category=AudioCategory.UI, priority=SFXPriority.NORMAL)
        # Fifth SFX at LOW priority — all channels are busy at NORMAL.
        result = orch.play_sfx("sfx_extra", category=AudioCategory.UI, priority=SFXPriority.LOW)
        assert result is None
        # Manager was not called for the 5th.
        assert len(stub.sfx_calls) == MAX_SFX_CHANNELS

    def test_fifth_higher_priority_culls_lowest(self) -> None:
        orch, stub = _orchestrator()
        # Fill 4 channels with LOW priority.
        for i in range(MAX_SFX_CHANNELS):
            orch.play_sfx(f"sfx_{i}", category=AudioCategory.UI, priority=SFXPriority.LOW)
        # Critical SFX arrives — should cull one of the LOW voices.
        result = orch.play_sfx(
            "sfx_critical",
            category=AudioCategory.COMBAT,
            priority=SFXPriority.CRITICAL,
        )
        assert result is not None
        assert len(stub.sfx_calls) == MAX_SFX_CHANNELS + 1
        # One LOW channel got .stop()ed (is_busy flipped to False).
        assert orch.active_sfx_count() == MAX_SFX_CHANNELS  # still at cap, but different mix

    def test_equal_priority_does_not_cull(self) -> None:
        orch, _ = _orchestrator()
        for i in range(MAX_SFX_CHANNELS):
            orch.play_sfx(f"sfx_{i}", category=AudioCategory.UI, priority=SFXPriority.NORMAL)
        # Equal priority incoming — spec §4.2: "if equal or lower, the
        # incoming is dropped".
        result = orch.play_sfx("sfx_tied", category=AudioCategory.UI, priority=SFXPriority.NORMAL)
        assert result is None

    def test_finished_channels_free_up_slots(self) -> None:
        orch, _ = _orchestrator()
        channels: list[Any] = []
        for i in range(MAX_SFX_CHANNELS):
            ch = orch.play_sfx(f"sfx_{i}", category=AudioCategory.UI, priority=SFXPriority.NORMAL)
            channels.append(ch)
        # Mark first channel as finished.
        channels[0].is_busy = False
        # A new LOW-priority SFX should now fit.
        result = orch.play_sfx("sfx_late", category=AudioCategory.UI, priority=SFXPriority.LOW)
        assert result is not None


# ---------------------------------------------------------------------------
# AudioManager duck multipliers
# ---------------------------------------------------------------------------


class TestAudioManagerDuckMultipliers:
    def test_duck_defaults_to_one(self) -> None:
        """Baseline: effective volume matches master * music with no duck."""
        from spacegame.engine.audio_manager import AudioManager

        am = AudioManager.__new__(AudioManager)
        am._config = AudioConfig()
        am._enabled = False
        am._music_duck = 1.0
        am._ambient_duck = 1.0
        # Stored config values are LINEAR; perceptual quadratic curve
        # applied at output time inside ``_effective_*_volume``. Duck
        # multiplier is applied AFTER the curve (it's a separate
        # ducking layer, not part of perceptual scaling).
        linear = am._config.master_volume * am._config.music_volume
        assert am._effective_music_volume() == pytest.approx(linear * linear)

    def test_set_music_duck_affects_effective_volume(self) -> None:
        from spacegame.engine.audio_manager import AudioManager

        am = AudioManager.__new__(AudioManager)
        am._config = AudioConfig()
        am._enabled = False
        am._music_duck = 1.0
        am._ambient_duck = 1.0
        am.set_music_duck(0.40)
        linear = am._config.master_volume * am._config.music_volume
        assert am._effective_music_volume() == pytest.approx(linear * linear * 0.40)
        assert am.get_music_duck() == pytest.approx(0.40)

    def test_set_ambient_duck_affects_effective_volume(self) -> None:
        from spacegame.engine.audio_manager import AudioManager

        am = AudioManager.__new__(AudioManager)
        am._config = AudioConfig()
        am._enabled = False
        am._music_duck = 1.0
        am._ambient_duck = 1.0
        am.set_ambient_duck(0.70)
        linear = am._config.master_volume * am._config.ambient_volume
        assert am._effective_ambient_volume() == pytest.approx(linear * linear * 0.70)
        assert am.get_ambient_duck() == pytest.approx(0.70)

    def test_duck_clamps_to_unit_range(self) -> None:
        from spacegame.engine.audio_manager import AudioManager

        am = AudioManager.__new__(AudioManager)
        am._config = AudioConfig()
        am._enabled = False
        am._music_duck = 1.0
        am._ambient_duck = 1.0
        am.set_music_duck(1.7)
        assert am.get_music_duck() == pytest.approx(1.0)
        am.set_music_duck(-0.3)
        assert am.get_music_duck() == pytest.approx(0.0)

    def test_duck_does_not_mutate_user_config(self) -> None:
        """Ducking must leave the player's user-facing volume preference alone."""
        from spacegame.engine.audio_manager import AudioManager

        am = AudioManager.__new__(AudioManager)
        am._config = AudioConfig(music_volume=0.8, ambient_volume=0.6)
        am._enabled = False
        am._music_duck = 1.0
        am._ambient_duck = 1.0
        am.set_music_duck(0.40)
        am.set_ambient_duck(0.70)
        assert am._config.music_volume == pytest.approx(0.8)
        assert am._config.ambient_volume == pytest.approx(0.6)
