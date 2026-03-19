"""Tests for depth-gated rock types (DENSE, VOLATILE) and Monolith boss rocks."""

import pytest
import random

from spacegame.models.mining import (
    MiningSession,
    MiningConfig,
    RockType,
    ROCK_TYPE_CONFIGS,
    AsteroidRock,
)


class TestDenseRock:
    """Tests for DENSE rock type (depth 5+)."""

    def test_dense_in_rock_type_enum(self) -> None:
        assert RockType.DENSE.value == "dense"

    def test_dense_config_exists(self) -> None:
        cfg = ROCK_TYPE_CONFIGS[RockType.DENSE]
        assert cfg.hardness == 4.0
        assert cfg.commodity_id == "iron_ore"
        assert cfg.min_yield == 3
        assert cfg.max_yield == 6

    def test_dense_not_in_shallow_depths(self) -> None:
        """DENSE rocks should not appear at depths 1-4."""
        config = MiningConfig(system_id="breakstone")
        random.seed(42)
        session = MiningSession(config)
        # At depth 1, no dense rocks
        for rock in session.rocks:
            assert rock.rock_type != RockType.DENSE

    def test_dense_appears_at_depth_5(self) -> None:
        """DENSE rocks should appear in the distribution at depth 5+."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 4  # Will become 5 after regen
        session.regenerate_field()
        assert session.depth == 5
        # Check that dense is possible (might not appear due to RNG,
        # but the distribution should include it)
        dist = session._get_depth_rock_distribution()
        assert "dense" in dist

    def test_dense_immune_to_chain(self) -> None:
        """DENSE rocks should not be affected by chain detonation."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config, chain_chance_bonus=10.0)  # Guarantee chains
        # Place a common rock and a dense rock adjacent
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.DENSE, grid_x=1, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
        ]
        # Break the first common rock — chain should skip the dense rock
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_chain_detonation(session.rocks[0])
        # Dense rock should not have been affected
        assert session.rocks[1].drill_progress == 0.0
        assert not session.rocks[1].depleted


class TestVolatileRock:
    """Tests for VOLATILE rock type (depth 12+)."""

    def test_volatile_in_rock_type_enum(self) -> None:
        assert RockType.VOLATILE.value == "volatile"

    def test_volatile_config_exists(self) -> None:
        cfg = ROCK_TYPE_CONFIGS[RockType.VOLATILE]
        assert cfg.hardness == 1.5
        assert cfg.commodity_id == "raw_ore"
        assert cfg.min_yield == 2
        assert cfg.max_yield == 4

    def test_volatile_not_in_shallow_depths(self) -> None:
        """VOLATILE rocks should not appear at depths below 12."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 10
        session.regenerate_field()
        dist = session._get_depth_rock_distribution()
        assert "volatile" not in dist

    def test_volatile_appears_at_depth_12(self) -> None:
        """VOLATILE rocks should appear at depth 12+."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 11
        session.regenerate_field()
        assert session.depth == 12
        dist = session._get_depth_rock_distribution()
        assert "volatile" in dist

    def test_volatile_splash_damage_on_break(self) -> None:
        """Breaking a VOLATILE rock should apply 50% progress to all adjacent."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=3)
        session = MiningSession(config)
        # Place a volatile rock in center with neighbors
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=1, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=1),
            AsteroidRock(rock_type=RockType.VOLATILE, grid_x=1, grid_y=1),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=1),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=2),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=1, grid_y=2),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=2),
        ]
        # Break the volatile rock
        volatile = session.rocks[4]
        volatile.depleted = True
        session._on_rock_broken(volatile)
        session._apply_volatile_splash(volatile)
        # All 8 neighbors should have 50% progress
        for rock in session.rocks:
            if rock is not volatile and not rock.depleted:
                assert rock.drill_progress == pytest.approx(0.5, abs=0.01), (
                    f"Rock at ({rock.grid_x},{rock.grid_y}) should have 0.5 progress"
                )


class TestDepthRockDistribution:
    """Tests for depth-gated rock distribution."""

    def test_base_distribution_at_depth_1(self) -> None:
        """Depth 1: only common ore, no iron/crystal/rare/dense/volatile."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        dist = session._get_depth_rock_distribution()
        assert "common" in dist
        assert "iron" not in dist, "Iron should be gated to depth 3+"
        assert "crystal" not in dist, "Crystal should be gated to depth 6+"
        assert "rare" not in dist, "Rare should be gated to depth 9+"
        assert "dense" not in dist
        assert "volatile" not in dist

    def test_iron_appears_at_depth_3(self) -> None:
        """Iron ore unlocks at depth 3."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 3
        dist = session._get_depth_rock_distribution()
        assert "iron" in dist

    def test_crystal_appears_at_depth_6(self) -> None:
        """Crystal ore unlocks at depth 6."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 6
        dist = session._get_depth_rock_distribution()
        assert "crystal" in dist

    def test_rare_appears_at_depth_9(self) -> None:
        """Rare ore unlocks at depth 9."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 9
        dist = session._get_depth_rock_distribution()
        assert "rare" in dist

    def test_distribution_at_depth_7(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 7
        dist = session._get_depth_rock_distribution()
        assert "dense" in dist
        assert "iron" in dist
        assert "crystal" in dist
        assert "volatile" not in dist

    def test_distribution_at_depth_15(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 15
        dist = session._get_depth_rock_distribution()
        assert "dense" in dist
        assert "volatile" in dist
