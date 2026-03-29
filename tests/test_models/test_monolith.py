"""Tests for Monolith boss rocks."""

import pytest
import random

from spacegame.models.mining import (
    MiningSession,
    MiningConfig,
    RockType,
    AsteroidRock,
)


class TestMonolith:
    """Tests for Monolith boss rock behavior."""

    def test_monolith_spawns_at_depth_25(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 24
        random.seed(42)
        session.regenerate_field()
        assert session.depth == 25
        monoliths = [r for r in session.rocks if r.rock_type == RockType.MONOLITH]
        assert len(monoliths) == 1

    def test_monolith_spawns_at_depth_50(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 49
        random.seed(42)
        session.regenerate_field()
        monoliths = [r for r in session.rocks if r.rock_type == RockType.MONOLITH]
        assert len(monoliths) == 1

    def test_no_monolith_at_non_multiple_of_25(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 6
        random.seed(42)
        session.regenerate_field()
        assert session.depth == 7
        monoliths = [r for r in session.rocks if r.rock_type == RockType.MONOLITH]
        assert len(monoliths) == 0

    def test_monolith_hardness_scales_with_depth(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 49
        random.seed(42)
        session.regenerate_field()
        monolith = next(r for r in session.rocks if r.rock_type == RockType.MONOLITH)
        # At depth 50: 10.0 + 50 * 0.05 = 12.5
        assert monolith.hardness == pytest.approx(12.5)

    def test_monolith_yield_scales_with_depth(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 99
        random.seed(42)
        session.regenerate_field()
        monolith = next(r for r in session.rocks if r.rock_type == RockType.MONOLITH)
        # At depth 100: 5 + 100 // 10 = 15
        assert monolith.get_yield() == 15

    def test_monolith_strata_reward(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 99
        random.seed(42)
        session.regenerate_field()
        monolith = next(r for r in session.rocks if r.rock_type == RockType.MONOLITH)
        # depth // 5 = 100 // 5 = 20
        assert monolith.strata_reward == 20

    def test_monolith_chain_immune(self) -> None:
        monolith = AsteroidRock(rock_type=RockType.MONOLITH, grid_x=0, grid_y=0)
        assert monolith.config.chain_immune

    def test_monolith_drone_immune(self) -> None:
        monolith = AsteroidRock(rock_type=RockType.MONOLITH, grid_x=0, grid_y=0)
        assert monolith.config.drone_immune

    def test_drones_skip_monolith(self) -> None:
        """Drones should not target monolith rocks."""
        from spacegame.models.drone import MiningDrone, DroneTier

        config = MiningConfig(system_id="breakstone", grid_width=2, grid_height=1)
        drone = MiningDrone(tier=DroneTier.BASIC)
        session = MiningSession(config, drones=[drone])
        # Replace field with one monolith and one common
        session.rocks = [
            AsteroidRock(rock_type=RockType.MONOLITH, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=1, grid_y=0),
        ]
        # Force monolith to have drone_immune via config (it does)
        target = session._pick_drone_target(drone, 0)
        assert target is not None
        assert target.rock_type == RockType.COMMON
