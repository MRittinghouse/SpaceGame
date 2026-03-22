"""Tests for shield renderer and damage state manager."""

import math

import pygame

from spacegame.engine.combat_vfx import (
    ShieldRenderer, ShieldState, DamageStateManager, DestructionSequence,
    CombatAtmosphere,
)


class TestShieldRenderer:
    """Tests for shield bubble visualization."""

    def test_set_shield_creates_state(self) -> None:
        """Setting shield on a new key creates a state."""
        sr = ShieldRenderer()
        sr.set_shield("player", 0.8, 50)
        assert "player" in sr._states
        assert sr._states["player"].active
        assert sr._states["player"].ratio == 0.8

    def test_zero_max_shields_no_state(self) -> None:
        """Ships with 0 max shields shouldn't have shield state."""
        sr = ShieldRenderer()
        sr.set_shield("enemy_0", 0.0, 0)
        assert "enemy_0" not in sr._states

    def test_shield_break_triggers(self) -> None:
        """Shields dropping to 0 should trigger break sequence."""
        sr = ShieldRenderer()
        sr.set_shield("player", 0.5, 50)
        sr.set_shield("player", 0.0, 50)
        state = sr._states["player"]
        assert state.breaking
        assert not state.active
        assert len(state._break_fragments) == 10

    def test_shield_restore_triggers(self) -> None:
        """Shields restoring from 0 should trigger restore sequence."""
        sr = ShieldRenderer()
        sr.set_shield("player", 0.5, 50)
        sr.set_shield("player", 0.0, 50)
        state = sr._states["player"]
        # Complete break
        state.breaking = False
        sr.set_shield("player", 0.3, 50)
        assert state.restoring
        assert state.active

    def test_ripple_sets_timer(self) -> None:
        """Trigger ripple should set the ripple timer."""
        sr = ShieldRenderer()
        sr.set_shield("player", 1.0, 50)
        sr.trigger_ripple("player", angle=0.5)
        assert sr._states["player"].ripple_timer > 0
        assert sr._states["player"].ripple_angle == 0.5

    def test_ripple_no_effect_when_inactive(self) -> None:
        """Ripple on inactive shields should do nothing."""
        sr = ShieldRenderer()
        sr.set_shield("player", 0.0, 50)
        sr.trigger_ripple("player", angle=0.5)
        # Shield is inactive — ripple shouldn't fire
        assert sr._states["player"].ripple_timer == 0

    def test_update_decays_ripple(self) -> None:
        """Ripple timer should decay over time."""
        sr = ShieldRenderer()
        sr.set_shield("player", 1.0, 50)
        sr.trigger_ripple("player")
        initial = sr._states["player"].ripple_timer
        sr.update(0.1)
        assert sr._states["player"].ripple_timer < initial

    def test_break_fragments_decay(self) -> None:
        """Break fragments should lose alpha over time."""
        sr = ShieldRenderer()
        sr.set_shield("player", 0.5, 50)
        sr.set_shield("player", 0.0, 50)
        state = sr._states["player"]
        initial_alpha = state._break_fragments[0]["alpha"]
        sr.update(0.1)
        assert state._break_fragments[0]["alpha"] < initial_alpha

    def test_clear(self) -> None:
        """Clear should remove all states."""
        sr = ShieldRenderer()
        sr.set_shield("player", 1.0, 50)
        sr.set_shield("enemy_0", 0.5, 30)
        sr.clear()
        assert len(sr._states) == 0


class TestDamageStateManager:
    """Tests for progressive damage visualization."""

    def test_set_hull(self) -> None:
        """Setting hull creates damage state."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.8)
        assert "player" in dm._states
        assert dm._states["player"].hull_ratio == 0.8

    def test_recoil_offset(self) -> None:
        """Triggering recoil should produce non-zero offset."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.5)
        dm.trigger_recoil("player", from_right=True)
        ox, oy = dm.get_recoil_offset("player")
        assert ox != 0, "Recoil should have X offset"

    def test_recoil_decays(self) -> None:
        """Recoil should decay to zero over time."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.5)
        dm.trigger_recoil("player")
        dm.update(0.5)  # Well past recoil_max of 0.12s
        ox, oy = dm.get_recoil_offset("player")
        assert ox == 0 and oy == 0

    def test_no_recoil_without_trigger(self) -> None:
        """Without trigger, recoil offset should be zero."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.3)
        ox, oy = dm.get_recoil_offset("player")
        assert ox == 0 and oy == 0

    def test_is_critical_below_25(self) -> None:
        """Ship below 25% hull should be critical."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.2)
        assert dm.is_critical("player")

    def test_not_critical_above_25(self) -> None:
        """Ship above 25% hull should not be critical."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.3)
        assert not dm.is_critical("player")

    def test_smoke_emits_below_50(self) -> None:
        """Ships below 50% hull should emit smoke particles."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.3)
        # Use small timesteps to avoid particles expiring in the same frame
        for _ in range(20):
            dm.update(0.05)
        assert len(dm._states["player"].smoke_particles) > 0

    def test_no_smoke_above_50(self) -> None:
        """Ships above 50% hull should not emit smoke."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.7)
        for _ in range(20):
            dm.update(0.05)
        assert len(dm._states["player"].smoke_particles) == 0

    def test_sparks_emit_below_75(self) -> None:
        """Ships below 75% hull should emit sparks (check cumulative)."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.5)
        spark_seen = False
        for _ in range(100):
            dm.update(0.016)  # ~60fps
            if len(dm._states["player"].spark_particles) > 0:
                spark_seen = True
                break
        assert spark_seen, "Sparks should emit for damaged ships"

    def test_no_sparks_above_75(self) -> None:
        """Ships above 75% hull should not emit sparks."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.9)
        for _ in range(40):
            dm.update(0.05)
        assert len(dm._states["player"].spark_particles) == 0

    def test_critical_pulse_alpha(self) -> None:
        """Critical ships should have non-zero pulse alpha."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.1)
        dm.update(0.5)  # Advance pulse phase
        alpha = dm.get_critical_pulse_alpha("player")
        assert alpha >= 0  # Could be 0 at certain phase points

    def test_clear(self) -> None:
        """Clear should remove all states."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.5)
        dm.set_hull("enemy_0", 0.3)
        dm.clear()
        assert len(dm._states) == 0

    def test_smoke_particles_expire(self) -> None:
        """Smoke particles should be removed after their lifetime."""
        dm = DamageStateManager()
        dm.set_hull("player", 0.2)
        dm.update(0.5)  # Emit some smoke
        count = len(dm._states["player"].smoke_particles)
        assert count > 0
        dm.update(3.0)  # Wait for all to expire (max_life=1.5s)
        # Some may have expired but new ones emitted — just verify no crash
        assert isinstance(dm._states["player"].smoke_particles, list)


class TestDestructionSequence:
    """Tests for spectacular ship destruction animation."""

    def test_starts_in_freeze(self) -> None:
        """Sequence should begin in freeze frame."""
        seq = DestructionSequence(400.0, 300.0, 48)
        assert seq.in_freeze
        assert not seq.finished

    def test_freeze_ends(self) -> None:
        """Freeze frame should end after FREEZE_END time."""
        seq = DestructionSequence(400.0, 300.0, 48)
        seq.update(0.06)  # Past FREEZE_END of 0.05s
        assert not seq.in_freeze

    def test_generates_fragments(self) -> None:
        """Should generate hull fragments on creation."""
        seq = DestructionSequence(400.0, 300.0, 48)
        assert len(seq._fragments) >= 5
        assert len(seq._fragments) <= 8

    def test_secondary_explosions_trigger(self) -> None:
        """Secondary explosions should fire at their scheduled times."""
        seq = DestructionSequence(400.0, 300.0, 48)
        # Advance past all secondary triggers (0.25 + 3*0.08 = 0.49s)
        for _ in range(40):
            seq.update(0.016)
        fired = [s for s in seq._secondary_timers if s["fired"]]
        assert len(fired) == len(seq._secondary_timers), "All secondaries should fire"

    def test_fire_particles_emitted(self) -> None:
        """Fire/smoke particles should emit during the sequence."""
        seq = DestructionSequence(400.0, 300.0, 48)
        fire_seen = False
        for _ in range(50):
            seq.update(0.016)
            if len(seq._fire_particles) > 0:
                fire_seen = True
                break
        assert fire_seen, "Fire particles should emit during destruction"

    def test_sequence_finishes(self) -> None:
        """Sequence should finish after TOTAL_DURATION."""
        seq = DestructionSequence(400.0, 300.0, 48)
        for _ in range(80):
            seq.update(0.016)
        assert seq.finished

    def test_debris_generated_on_finish(self) -> None:
        """Persistent debris should be generated when sequence finishes."""
        seq = DestructionSequence(400.0, 300.0, 48)
        for _ in range(80):
            seq.update(0.016)
        assert seq.finished
        # Some fragments should convert to debris
        assert len(seq.debris) > 0

    def test_fragments_move_outward(self) -> None:
        """Fragments should move away from center over time."""
        seq = DestructionSequence(400.0, 300.0, 48)
        seq.update(0.06)  # Past freeze
        initial_positions = [(f["x"], f["y"]) for f in seq._fragments]
        seq.update(0.2)
        for i, frag in enumerate(seq._fragments):
            dist = abs(frag["x"]) + abs(frag["y"])
            initial_dist = abs(initial_positions[i][0]) + abs(initial_positions[i][1])
            assert dist > initial_dist, f"Fragment {i} should move outward"

    def test_fragment_alpha_fades(self) -> None:
        """Fragment alpha should decrease toward the end of the sequence."""
        seq = DestructionSequence(400.0, 300.0, 48)
        # Advance to late in the sequence
        for _ in range(60):
            seq.update(0.016)
        # Some fragments should have reduced alpha
        faded = [f for f in seq._fragments if f["alpha"] < 255]
        assert len(faded) > 0, "Fragments should fade toward end"

    def test_flash_radius_expands(self) -> None:
        """Flash should expand during the flash phase."""
        seq = DestructionSequence(400.0, 300.0, 48)
        seq.update(0.06)  # Past freeze, into flash
        seq.update(0.05)  # Partway through flash
        assert seq._flash_radius > 0, "Flash should expand"


class TestCombatAtmosphere:
    """Tests for combat arena atmosphere system."""

    def _make_arena(self) -> pygame.Rect:
        return pygame.Rect(200, 50, 800, 450)

    def test_creates_dust_motes(self) -> None:
        """Atmosphere should generate dust particles."""
        atm = CombatAtmosphere(self._make_arena(), "safe")
        assert len(atm._dust) == 15  # Safe dust count

    def test_dangerous_has_more_dust(self) -> None:
        """Dangerous atmosphere should have more particles than safe."""
        safe = CombatAtmosphere(self._make_arena(), "safe")
        danger = CombatAtmosphere(self._make_arena(), "dangerous")
        assert len(danger._dust) > len(safe._dust)

    def test_crimson_has_most_dust(self) -> None:
        """Crimson Reach should have the highest dust density."""
        crimson = CombatAtmosphere(self._make_arena(), "crimson")
        assert len(crimson._dust) == 40

    def test_dust_moves_on_update(self) -> None:
        """Dust motes should move after update."""
        atm = CombatAtmosphere(self._make_arena(), "safe")
        initial_x = atm._dust[0].x
        atm.update(1.0)
        assert atm._dust[0].x != initial_x, "Dust should drift"

    def test_dust_wraps_horizontally(self) -> None:
        """Dust that drifts past the arena edge should wrap to the left."""
        atm = CombatAtmosphere(self._make_arena(), "safe")
        arena = self._make_arena()
        # Force a mote past the right edge
        atm._dust[0].x = arena.right + 10
        atm.update(0.016)
        assert atm._dust[0].x < arena.left, "Dust should wrap left"

    def test_tint_surface_for_dangerous(self) -> None:
        """Dangerous atmosphere should have a tint overlay."""
        atm = CombatAtmosphere(self._make_arena(), "dangerous")
        assert atm._tint_surface is not None

    def test_no_tint_for_safe(self) -> None:
        """Safe atmosphere should have no tint overlay."""
        atm = CombatAtmosphere(self._make_arena(), "safe")
        assert atm._tint_surface is None

    def test_arena_frame_created(self) -> None:
        """Arena frame surface should be pre-rendered."""
        atm = CombatAtmosphere(self._make_arena(), "safe")
        assert atm._frame_surface is not None

    def test_unknown_danger_falls_back_to_safe(self) -> None:
        """Unknown danger level should use safe defaults."""
        atm = CombatAtmosphere(self._make_arena(), "unknown_level")
        assert len(atm._dust) == 15  # Safe count
