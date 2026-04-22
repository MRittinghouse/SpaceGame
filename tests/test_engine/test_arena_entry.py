"""Tests for the arena_entry timeline primitive (Combat C3 §4.8).

Validates phase boundaries, factor envelopes, enemy stagger, completion,
and reset behavior. No pygame dependency — this is a pure timeline.

See ``requirements/overhaul/30_overhaul_space_combat.md §4.8``.
"""

from __future__ import annotations

import pytest

from spacegame.engine.arena_entry import (
    TOTAL_DURATION,
    ArenaEntry,
    ArenaEntryPhase,
)

# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------


class TestArenaEntryPhases:
    def test_starts_in_intro(self) -> None:
        entry = ArenaEntry(enemy_count=2)
        assert entry.phase == ArenaEntryPhase.INTRO

    def test_intro_transitions_to_tint_fade_at_0_3(self) -> None:
        entry = ArenaEntry()
        entry.update(0.3)
        assert entry.phase == ArenaEntryPhase.TINT_FADE

    def test_camera_push_starts_at_0_5(self) -> None:
        entry = ArenaEntry()
        entry.update(0.5)
        assert entry.phase == ArenaEntryPhase.CAMERA_PUSH

    def test_enemy_entry_starts_at_1_1(self) -> None:
        entry = ArenaEntry()
        entry.update(1.1)
        assert entry.phase == ArenaEntryPhase.ENEMY_ENTRY

    def test_completes_at_1_5(self) -> None:
        entry = ArenaEntry()
        entry.update(1.5)
        assert entry.phase == ArenaEntryPhase.COMPLETE
        assert entry.is_complete

    def test_total_duration_constant_matches_spec(self) -> None:
        """Spec §4.8 calls out the total as 1.5s."""
        assert TOTAL_DURATION == 1.5


# ---------------------------------------------------------------------------
# Factor envelopes
# ---------------------------------------------------------------------------


class TestArenaEntryTintFactor:
    def test_tint_is_zero_before_fade_begins(self) -> None:
        entry = ArenaEntry()
        assert entry.tint_alpha_factor == 0.0
        entry.update(0.25)
        assert entry.tint_alpha_factor == 0.0

    def test_tint_mid_fade_is_half(self) -> None:
        entry = ArenaEntry()
        entry.update(0.3 + 0.25)  # halfway through the 500ms fade
        assert entry.tint_alpha_factor == pytest.approx(0.5, abs=0.02)

    def test_tint_reaches_full_after_fade(self) -> None:
        entry = ArenaEntry()
        entry.update(0.8)
        assert entry.tint_alpha_factor == 1.0

    def test_dust_and_tint_share_schedule(self) -> None:
        entry = ArenaEntry()
        entry.update(0.45)
        assert entry.dust_alpha_factor == entry.tint_alpha_factor


class TestArenaEntryEngineIgnite:
    def test_engine_is_dim_during_intro(self) -> None:
        entry = ArenaEntry()
        entry.update(0.2)
        assert entry.player_engine_ignite_factor == pytest.approx(0.35)

    def test_engine_at_full_after_push(self) -> None:
        entry = ArenaEntry()
        entry.update(1.2)
        assert entry.player_engine_ignite_factor == 1.0

    def test_engine_ramps_during_push(self) -> None:
        entry = ArenaEntry()
        entry.update(0.8)  # mid-push (0.3s into 0.6s push phase)
        factor = entry.player_engine_ignite_factor
        assert 0.35 < factor < 1.0


class TestArenaEntryCameraPush:
    def test_camera_at_wide_before_push(self) -> None:
        entry = ArenaEntry()
        entry.update(0.2)
        assert entry.camera_push_factor == 0.0

    def test_camera_at_default_after_push(self) -> None:
        entry = ArenaEntry()
        entry.update(1.15)
        assert entry.camera_push_factor == 1.0

    def test_camera_factor_monotonic(self) -> None:
        entry = ArenaEntry()
        prev = -0.1
        for _ in range(40):
            entry.update(0.05)
            assert entry.camera_push_factor >= prev
            prev = entry.camera_push_factor


# ---------------------------------------------------------------------------
# Enemy slide + stagger
# ---------------------------------------------------------------------------


class TestEnemySlideBehavior:
    def test_enemy_starts_offset_right(self) -> None:
        entry = ArenaEntry(enemy_count=3, slide_offset_px=80.0)
        assert entry.enemy_slide_offset(0) == 80.0
        assert entry.enemy_slide_offset(2) == 80.0

    def test_enemy_settles_at_zero_after_full_slide(self) -> None:
        entry = ArenaEntry(enemy_count=1)
        entry.update(1.5)
        assert entry.enemy_slide_offset(0) == 0.0

    def test_enemies_stagger_by_100ms(self) -> None:
        """Enemy 0 starts at 1.1, enemy 1 at 1.2, etc."""
        entry = ArenaEntry(enemy_count=2)
        entry.update(1.15)  # Past enemy 0 start, before enemy 1 start
        # Enemy 0: already moving; offset < slide_offset_px
        assert entry.enemy_slide_offset(0) < 80.0
        # Enemy 1: still at full offset (hasn't started sliding)
        assert entry.enemy_slide_offset(1) == 80.0

    def test_enemy_alpha_starts_zero(self) -> None:
        entry = ArenaEntry()
        assert entry.enemy_alpha_factor(0) == 0.0

    def test_enemy_alpha_reaches_one_partway_through_slide(self) -> None:
        """Fade-in finishes halfway through the slide; stays at 1.0 after."""
        entry = ArenaEntry()
        entry.update(1.5)  # well past enemy 0 fade-in window
        assert entry.enemy_alpha_factor(0) == 1.0


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestArenaEntryLifecycle:
    def test_negative_dt_ignored(self) -> None:
        entry = ArenaEntry()
        entry.update(-0.5)
        assert entry.elapsed == 0.0

    def test_zero_dt_is_noop(self) -> None:
        entry = ArenaEntry()
        entry.update(0.0)
        assert entry.elapsed == 0.0

    def test_update_clamps_at_total_duration(self) -> None:
        entry = ArenaEntry()
        entry.update(5.0)
        assert entry.elapsed == TOTAL_DURATION
        assert entry.is_complete

    def test_reset_rewinds_timeline(self) -> None:
        entry = ArenaEntry()
        entry.update(1.0)
        entry.reset()
        assert entry.elapsed == 0.0
        assert entry.phase == ArenaEntryPhase.INTRO

    def test_zero_enemies_still_completes(self) -> None:
        entry = ArenaEntry(enemy_count=0)
        entry.update(1.6)
        assert entry.is_complete
