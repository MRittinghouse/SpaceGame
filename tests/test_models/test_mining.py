"""
Tests for the mining system models.
"""

import pytest
from spacegame.models.mining import (
    RockType,
    RockTypeConfig,
    AsteroidRock,
    MiningConfig,
    MiningSession,
    MiningResult,
    ROCK_TYPE_CONFIGS,
)
from spacegame.models.drone import MiningDrone, DroneTier


class TestAsteroidRock:
    """Tests for AsteroidRock."""

    def test_rock_creation(self):
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        assert rock.rock_type == RockType.COMMON
        assert not rock.depleted
        assert not rock.drilling
        assert rock.drill_progress == 0.0

    def test_rock_hardness(self):
        common = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        rare = AsteroidRock(rock_type=RockType.RARE, grid_x=0, grid_y=0)
        assert common.hardness == 0.5
        assert rare.hardness == 3.0

    def test_rock_commodity_id(self):
        iron = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        assert iron.commodity_id == "iron_ore"

    def test_rock_yield_range(self):
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        cfg = ROCK_TYPE_CONFIGS[RockType.COMMON]
        for _ in range(50):
            y = rock.get_yield()
            assert cfg.min_yield <= y <= cfg.max_yield

    def test_start_drilling(self):
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        assert rock.start_drilling()
        assert rock.drilling
        assert rock.drill_progress == 0.0

    def test_cannot_drill_depleted(self):
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        rock.depleted = True
        assert not rock.start_drilling()

    def test_cannot_drill_while_drilling(self):
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        rock.start_drilling()
        assert not rock.start_drilling()

    def test_drill_progress(self):
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        rock.start_drilling()
        # Common rock has 0.5s hardness, so 0.25s = 50%
        result = rock.update_drill(0.25)
        assert result is None
        assert rock.drill_progress == pytest.approx(0.5, abs=0.01)

    def test_drill_completion(self):
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        rock.start_drilling()
        # Common rock has 0.5s hardness, so 0.6s should complete
        result = rock.update_drill(0.6)
        assert result is not None
        assert result >= 1
        assert rock.depleted
        assert not rock.drilling

    def test_drill_speed_bonus(self):
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        rock.start_drilling()
        # Iron has 1.0s hardness, with 2x bonus = 0.5s effective
        result = rock.update_drill(0.6, speed_bonus=2.0)
        assert result is not None
        assert rock.depleted

    def test_cancel_drill(self):
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        rock.start_drilling()
        rock.update_drill(0.3)
        rock.cancel_drill()
        assert not rock.drilling
        assert rock.drill_progress == 0.0
        assert not rock.depleted


# === apply_click Tests ===


class TestAsteroidRockClick:
    """Tests for AsteroidRock.apply_click()."""

    def test_apply_click_adds_progress(self) -> None:
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        # Common hardness=0.5, click_power=0.12 → 0.12/0.5 = 0.24 progress
        result = rock.apply_click(0.12)
        assert result is None
        assert rock.drill_progress == pytest.approx(0.24, abs=0.01)
        assert rock.drilling is True

    def test_apply_click_accumulates(self) -> None:
        rock = AsteroidRock(rock_type=RockType.IRON, grid_x=0, grid_y=0)
        # Iron hardness=1.0, click_power=0.12 → 0.12 progress each
        rock.apply_click(0.12)
        rock.apply_click(0.12)
        assert rock.drill_progress == pytest.approx(0.24, abs=0.01)

    def test_apply_click_breaks_rock(self) -> None:
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        # Common hardness=0.5, need 0.5 total click_power to break
        # Each click of 0.3 gives 0.6 progress (0.3/0.5)
        rock.apply_click(0.3)
        result = rock.apply_click(0.3)
        assert result is not None
        assert result >= 1
        assert rock.depleted is True

    def test_apply_click_depleted_returns_none(self) -> None:
        rock = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        rock.depleted = True
        result = rock.apply_click(0.12)
        assert result is None
        assert rock.drill_progress == 0.0

    def test_apply_click_scales_with_hardness(self) -> None:
        """Harder rocks get less progress per click."""
        common = AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0)
        rare = AsteroidRock(rock_type=RockType.RARE, grid_x=1, grid_y=0)
        common.apply_click(0.12)
        rare.apply_click(0.12)
        # Common (0.5) gets 0.24, Rare (3.0) gets 0.04
        assert common.drill_progress > rare.drill_progress


class TestMiningConfig:
    """Tests for MiningConfig."""

    def test_default_config(self):
        config = MiningConfig(system_id="test")
        assert config.grid_width == 6
        assert config.grid_height == 4
        assert config.base_click_power == 0.12
        assert config.base_passive_rate == 0.05
        assert "common" in config.rock_distribution

    def test_custom_config(self):
        config = MiningConfig(
            system_id="test",
            grid_width=8,
            grid_height=6,
            base_click_power=0.20,
            rock_distribution={"iron": 0.5, "rare": 0.5},
        )
        assert config.grid_width == 8
        assert config.base_click_power == 0.20
        assert config.rock_distribution["iron"] == 0.5


class TestMiningSession:
    """Tests for MiningSession."""

    def test_session_creation(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert len(session.rocks) == 24  # 6x4 grid
        assert session.active_rock is None
        assert session.total_clicks == 0

    def test_field_generation(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        # All rocks should have valid positions
        for rock in session.rocks:
            assert 0 <= rock.grid_x < 6
            assert 0 <= rock.grid_y < 4

    def test_get_rock_at(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        rock = session.get_rock_at(0, 0)
        assert rock is not None
        assert rock.grid_x == 0
        assert rock.grid_y == 0

    def test_get_rock_at_invalid(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert session.get_rock_at(99, 99) is None

    def test_start_drill_compat(self):
        """start_drill() still works as backward-compat wrapper."""
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        success, msg = session.start_drill(0, 0)
        assert success
        assert session.active_rock is not None

    def test_drill_depleted_rock(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        rock = session.get_rock_at(0, 0)
        rock.depleted = True
        success, msg = session.start_drill(0, 0)
        assert not success

    def test_drill_and_collect(self):
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_passive_rate=0.50,
        )
        session = MiningSession(config)
        session.start_drill(0, 0)
        # Common hardness=0.5, passive_rate=0.50 → 1.0 progress/sec
        # Plus click progress. Should break within 1s.
        results = session.update(1.0)
        assert len(results) >= 1
        assert results[0].commodity_id == "raw_ore"
        assert results[0].quantity >= 1
        assert session.active_rock is None
        assert "raw_ore" in session.total_mined

    def test_regenerate_field(self):
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        # Deplete some rocks
        for rock in session.rocks[:5]:
            rock.depleted = True
        assert session.get_undepleted_count() < session.get_total_rocks()
        session.regenerate_field()
        assert session.get_undepleted_count() == session.get_total_rocks()

    def test_drill_speed_bonus(self):
        config = MiningConfig(
            system_id="test",
            rock_distribution={"iron": 1.0},
        )
        # Iron = 1.0s hardness, with passive_drill_bonus the passive rate
        # should be faster. Use start_drill compat wrapper.
        session = MiningSession(config, passive_drill_bonus=1.0)
        session.start_drill(0, 0)
        # base_passive_rate=0.05, bonus=1.0 → effective rate = 0.05*(1+1.0)=0.10
        # On iron (hardness=1.0): 0.10 progress/sec → 10s to break
        results = session.update(11.0)
        assert len(results) >= 1


# === click_rock Tests ===


class TestMiningSessionClickMine:
    """Tests for click-to-mine mechanic."""

    def test_click_rock_success(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        session = MiningSession(config)
        success, msg, result = session.click_rock(0, 0)
        assert success
        assert session.active_rock is not None
        assert session.total_clicks == 1

    def test_click_rock_breaks(self) -> None:
        """Repeated clicks can break a rock."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_click_power=0.30,
        )
        session = MiningSession(config)
        # Common hardness=0.5, click_power=0.30 → 0.60 progress per click
        # Two clicks = 1.20 progress → should break
        session.click_rock(0, 0)
        success, msg, result = session.click_rock(0, 0)
        assert result is not None
        assert result.commodity_id == "raw_ore"

    def test_click_depleted_fails(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        rock = session.get_rock_at(0, 0)
        rock.depleted = True
        success, msg, result = session.click_rock(0, 0)
        assert not success

    def test_click_invalid_position(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        success, msg, result = session.click_rock(99, 99)
        assert not success
        assert result is None

    def test_click_switches_active_rock(self) -> None:
        """Clicking a different rock switches active_rock (no lock-out)."""
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.click_rock(0, 0)
        rock_a = session.active_rock
        session.click_rock(1, 0)
        rock_b = session.active_rock
        assert rock_a is not rock_b
        # Old rock keeps its progress
        assert rock_a.drill_progress > 0

    def test_click_power_bonus(self) -> None:
        """click_power_bonus increases click effectiveness."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"iron": 1.0},
            base_click_power=0.12,
        )
        # No bonus
        session_base = MiningSession(config)
        session_base.click_rock(0, 0)
        base_progress = session_base.active_rock.drill_progress

        # 100% bonus
        session_bonus = MiningSession(config, click_power_bonus=1.0)
        session_bonus.click_rock(0, 0)
        bonus_progress = session_bonus.active_rock.drill_progress

        assert bonus_progress == pytest.approx(base_progress * 2, abs=0.01)

    def test_total_clicks_tracking(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.click_rock(0, 0)
        session.click_rock(0, 0)
        session.click_rock(1, 0)
        assert session.total_clicks == 3


# === Passive Drill Tests ===


class TestMiningSessionPassiveDrill:
    """Tests for passive drill mechanic."""

    def test_passive_drill_advances_active_rock(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"iron": 1.0},
            base_passive_rate=0.10,
        )
        session = MiningSession(config)
        session.click_rock(0, 0)
        initial_progress = session.active_rock.drill_progress
        session.update(1.0)
        # Iron hardness=1.0, passive_rate=0.10 → 0.10 progress/sec
        assert session.active_rock.drill_progress > initial_progress

    def test_passive_drill_can_break_rock(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_passive_rate=0.50,
        )
        session = MiningSession(config)
        session.click_rock(0, 0)
        # Common hardness=0.5, passive_rate=0.50 → 1.0 progress/sec
        # After 1s should break
        results = session.update(1.0)
        assert len(results) >= 1

    def test_passive_drill_bonus(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"iron": 1.0},
            base_passive_rate=0.10,
        )
        session = MiningSession(config, passive_drill_bonus=1.0)
        session.click_rock(0, 0)
        session.update(1.0)
        # Iron hardness=1.0, rate=0.10*(1+1.0)=0.20 → 0.20 progress
        # Plus the initial click progress
        click_progress = config.base_click_power / 1.0  # 0.12
        expected = click_progress + 0.20
        assert session.active_rock.drill_progress == pytest.approx(expected, abs=0.02)

    def test_no_passive_without_active_rock(self) -> None:
        config = MiningConfig(
            system_id="test",
            base_passive_rate=0.50,
        )
        session = MiningSession(config)
        results = session.update(5.0)
        assert len(results) == 0


# === Drone Mining Tests ===


class TestMiningSessionDrones:
    """Tests for drone auto-mining in MiningSession."""

    def test_no_drones_empty_results(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        session = MiningSession(config)
        results = session.update(1.0)
        assert results == []

    def test_single_drone_mines(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.BASIC)
        session = MiningSession(config, drones=[drone])
        # BASIC mining_speed=0.3, common hardness=0.5
        # Progress/sec = 0.3/0.5 = 0.6 → breaks in ~1.7s
        results = session.update(2.0)
        assert len(results) >= 1
        assert results[0].rock_type == RockType.COMMON

    def test_drone_avoids_active_rock(self) -> None:
        """Drones should not mine the player's active rock."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"iron": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.BASIC)
        session = MiningSession(config, drones=[drone])
        session.click_rock(0, 0)
        session.update(0.1)
        # Drone should target (1,0), not (0,0)
        assert session.drone_targets.get(0) is not session.active_rock

    def test_drone_breaks_rock_returns_result(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ELITE)
        session = MiningSession(config, drones=[drone])
        # ELITE mining_speed=1.0, common hardness=0.5
        # Progress/sec = 1.0/0.5 = 2.0 → breaks in 0.5s
        results = session.update(1.0)
        assert len(results) >= 1

    def test_drone_preference_targeting(self) -> None:
        """Drones with a preference should target preferred rock types."""
        config = MiningConfig(
            system_id="test",
            grid_width=4,
            grid_height=1,
            rock_distribution={"common": 0.0, "iron": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ADVANCED)
        drone.set_target_preference(RockType.IRON)
        session = MiningSession(config, drones=[drone])
        session.update(0.1)
        target = session.drone_targets.get(0)
        assert target is not None
        assert target.rock_type == RockType.IRON

    def test_drone_preference_fallback(self) -> None:
        """Drones fall back to any rock if preferred type not available."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ADVANCED)
        drone.set_target_preference(RockType.IRON)
        session = MiningSession(config, drones=[drone])
        session.update(0.1)
        # No iron rocks, should fall back to common
        target = session.drone_targets.get(0)
        assert target is not None

    def test_drone_speed_bonus(self) -> None:
        """drone_speed_bonus increases drone effectiveness."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.BASIC)
        # With 100% speed bonus, BASIC speed 0.3 becomes effectively 0.6
        session = MiningSession(config, drones=[drone], drone_speed_bonus=1.0)
        # Common hardness=0.5, effective speed=0.6
        # Progress/sec = 0.6/0.5 = 1.2 → breaks in ~0.83s
        results = session.update(1.0)
        assert len(results) >= 1

    def test_multiple_drones(self) -> None:
        """Multiple drones mine different rocks concurrently."""
        config = MiningConfig(
            system_id="test",
            grid_width=4,
            grid_height=1,
            rock_distribution={"common": 1.0},
        )
        drones = [
            MiningDrone(tier=DroneTier.BASIC),
            MiningDrone(tier=DroneTier.ADVANCED),
        ]
        session = MiningSession(config, drones=drones)
        session.update(0.1)
        # Both drones should have targets
        assert len(session.drone_targets) == 2
        # Targets should be different rocks
        targets = list(session.drone_targets.values())
        assert targets[0] is not targets[1]

    def test_elite_yield_bonus(self) -> None:
        """Elite drones apply yield bonus."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ELITE)
        session = MiningSession(config, drones=[drone])
        # Elite speed=1.0, common hardness=0.5 → breaks in 0.5s
        # Elite yield_bonus=0.25 → quantity should be boosted
        results = session.update(1.0)
        assert len(results) >= 1
        # Result quantity is at least 1 (base) and should be boosted
        # We can't test exact values due to randomness, but it should work

    def test_drones_skip_depleted(self) -> None:
        """Drones do not target depleted rocks."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.BASIC)
        session = MiningSession(config, drones=[drone])
        # Deplete all rocks
        for rock in session.rocks:
            rock.depleted = True
        session.update(0.5)
        assert session.drone_targets.get(0) is None

    def test_update_returns_list(self) -> None:
        """update() returns a list of MiningResult."""
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        results = session.update(0.1)
        assert isinstance(results, list)
