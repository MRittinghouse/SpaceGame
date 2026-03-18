"""Tests for particle system — blend mode support and new configs."""

import pygame
import pytest

from spacegame.engine.particles import (
    Particle,
    ParticleConfig,
    ParticlePool,
    # New C0 configs
    ROCK_BREAK,
    SCAN_RIPPLE,
    FORGE_FLAME,
    CORRUPTION_CRACKLE,
    EXTRACTION_SPARK,
    CHAIN_SHOCKWAVE,
    EMPOWERED_BURST,
    FORGE_COMPLETE_FLASH,
    DEPTH_TRANSITION,
)


@pytest.fixture(autouse=True, scope="module")
def _init_pygame() -> None:
    pygame.init()


@pytest.fixture()
def screen() -> pygame.Surface:
    return pygame.Surface((800, 600))


@pytest.fixture()
def pool() -> ParticlePool:
    return ParticlePool(max_particles=100)


# ============================================================================
# Blend mode support
# ============================================================================


class TestBlendAddSupport:
    """ParticleConfig.blend_add enables BLEND_ADD rendering for glow effects."""

    def test_particle_config_has_blend_add_field(self) -> None:
        config = ParticleConfig()
        assert hasattr(config, "blend_add")
        assert config.blend_add is False

    def test_blend_add_propagates_to_particle(self) -> None:
        config = ParticleConfig(blend_add=True, count=1, life_min=1.0, life_max=1.0)
        pool = ParticlePool(max_particles=10)
        pool.emit(100, 100, config)
        alive = [p for p in pool.particles if p.alive]
        assert len(alive) == 1
        assert alive[0].blend_add is True

    def test_blend_add_false_by_default_on_particle(self) -> None:
        p = Particle()
        assert p.blend_add is False

    def test_blend_add_renders_without_error(self, screen: pygame.Surface) -> None:
        """Additive blend particles should render without crashing."""
        config = ParticleConfig(
            blend_add=True,
            glow=True,
            count=5,
            life_min=0.5,
            life_max=0.5,
        )
        pool = ParticlePool(max_particles=10)
        pool.emit(400, 300, config)
        pool.update(0.1)
        pool.render(screen)  # Should not raise

    def test_non_blend_add_still_works(self, screen: pygame.Surface) -> None:
        """Normal (non-additive) particles should still render correctly."""
        config = ParticleConfig(count=5, life_min=0.5, life_max=0.5)
        pool = ParticlePool(max_particles=10)
        pool.emit(400, 300, config)
        pool.update(0.1)
        pool.render(screen)  # Should not raise


# ============================================================================
# Existing behavior regression
# ============================================================================


class TestParticlePoolBasics:
    """Core particle pool behavior still works after blend_add addition."""

    def test_emit_spawns_particles(self, pool: ParticlePool) -> None:
        config = ParticleConfig(count=10, life_min=1.0, life_max=1.0)
        pool.emit(100, 100, config)
        assert pool.alive_count == 10

    def test_particles_die_after_lifetime(self, pool: ParticlePool) -> None:
        config = ParticleConfig(count=5, life_min=0.5, life_max=0.5)
        pool.emit(100, 100, config)
        pool.update(0.6)
        assert pool.alive_count == 0

    def test_clear_kills_all(self, pool: ParticlePool) -> None:
        config = ParticleConfig(count=10, life_min=1.0, life_max=1.0)
        pool.emit(100, 100, config)
        pool.clear()
        assert pool.alive_count == 0

    def test_particles_respect_gravity(self, pool: ParticlePool) -> None:
        config = ParticleConfig(
            count=1, speed_min=0, speed_max=0,
            life_min=1.0, life_max=1.0, gravity=100.0,
        )
        pool.emit(100, 100, config)
        alive = [p for p in pool.particles if p.alive]
        initial_y = alive[0].y
        pool.update(0.5)
        assert alive[0].y > initial_y, "Gravity should pull particle downward"

    def test_render_all_paths(self, screen: pygame.Surface, pool: ParticlePool) -> None:
        """Render opaque, alpha, and glow particles without errors."""
        # Fully opaque, no glow
        pool.emit(100, 100, ParticleConfig(
            count=2, alpha_start=255, alpha_end=255, glow=False,
            life_min=1.0, life_max=1.0,
        ))
        # Alpha blended
        pool.emit(200, 200, ParticleConfig(
            count=2, alpha_start=128, alpha_end=0, glow=False,
            life_min=1.0, life_max=1.0,
        ))
        # Glow
        pool.emit(300, 300, ParticleConfig(
            count=2, glow=True, life_min=1.0, life_max=1.0,
        ))
        pool.update(0.1)
        pool.render(screen)


# ============================================================================
# New particle config presets
# ============================================================================


class TestNewParticleConfigs:
    """C0 particle presets exist and have reasonable parameters."""

    @pytest.mark.parametrize(
        "config",
        [
            ROCK_BREAK,
            SCAN_RIPPLE,
            FORGE_FLAME,
            CORRUPTION_CRACKLE,
            EXTRACTION_SPARK,
            CHAIN_SHOCKWAVE,
            EMPOWERED_BURST,
            FORGE_COMPLETE_FLASH,
            DEPTH_TRANSITION,
        ],
    )
    def test_config_has_valid_particle_count(self, config: ParticleConfig) -> None:
        assert config.count > 0

    @pytest.mark.parametrize(
        "config",
        [
            ROCK_BREAK,
            SCAN_RIPPLE,
            FORGE_FLAME,
            CORRUPTION_CRACKLE,
            EXTRACTION_SPARK,
            CHAIN_SHOCKWAVE,
            EMPOWERED_BURST,
            FORGE_COMPLETE_FLASH,
            DEPTH_TRANSITION,
        ],
    )
    def test_config_lifetime_positive(self, config: ParticleConfig) -> None:
        assert config.life_min > 0
        assert config.life_max >= config.life_min

    @pytest.mark.parametrize(
        "config",
        [
            ROCK_BREAK,
            SCAN_RIPPLE,
            FORGE_FLAME,
            CORRUPTION_CRACKLE,
            EXTRACTION_SPARK,
            CHAIN_SHOCKWAVE,
            EMPOWERED_BURST,
            FORGE_COMPLETE_FLASH,
            DEPTH_TRANSITION,
        ],
    )
    def test_config_renders_without_error(
        self, config: ParticleConfig, screen: pygame.Surface
    ) -> None:
        pool = ParticlePool(max_particles=50)
        pool.emit(400, 300, config)
        pool.update(0.05)
        pool.render(screen)

    def test_forge_flame_uses_blend_add(self) -> None:
        """Forge flame should use additive blending for fire glow."""
        assert FORGE_FLAME.blend_add is True

    def test_empowered_burst_uses_blend_add(self) -> None:
        assert EMPOWERED_BURST.blend_add is True

    def test_forge_complete_flash_uses_blend_add(self) -> None:
        assert FORGE_COMPLETE_FLASH.blend_add is True

    def test_rock_break_has_gravity(self) -> None:
        """Rock debris should fall."""
        assert ROCK_BREAK.gravity > 0

    def test_scan_ripple_no_gravity(self) -> None:
        """Scan effects should be zero-gravity."""
        assert SCAN_RIPPLE.gravity == 0.0

    def test_corruption_crackle_limited_spread(self) -> None:
        """Corruption particles should not be a full circle."""
        assert CORRUPTION_CRACKLE.spread < 360.0
