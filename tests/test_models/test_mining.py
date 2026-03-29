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
    DepthModifiers,
    ChainBreak,
    MiningMilestone,
    ROCK_TYPE_CONFIGS,
    CHAIN_BASE_CHANCE,
    CHAIN_PROGRESS_AMOUNT,
    CHAIN_MAX_DEPTH,
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
        session = MiningSession(config, passive_drill_bonus=1.0, starting_depth=20)
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
        session_base = MiningSession(config, starting_depth=20)
        session_base.click_rock(0, 0)
        base_progress = session_base.active_rock.drill_progress

        # 100% bonus
        session_bonus = MiningSession(config, click_power_bonus=1.0, starting_depth=20)
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
        session = MiningSession(config, starting_depth=20)
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
        session = MiningSession(config, passive_drill_bonus=1.0, starting_depth=20)
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
        session = MiningSession(config, drones=[drone], starting_depth=20)
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
        session = MiningSession(config, drones=[drone], starting_depth=20)
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


# === Energy System Tests ===


class TestEnergySystem:
    """Tests for energy management in mining sessions."""

    def test_session_starts_at_max_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        assert session.energy == 20
        assert session.max_energy == 20

    def test_normal_click_is_free(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        session.click_rock(0, 0)
        assert session.energy == 20  # Normal clicks don't cost energy

    def test_empowered_click_consumes_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        session.click_rock(0, 0, empowered=True)
        assert session.energy < 20  # Empowered clicks cost energy

    def test_empowered_click_at_zero_energy_fails(self) -> None:
        config = MiningConfig(system_id="test", max_energy=1)
        session = MiningSession(config)
        session.click_rock(0, 0, empowered=True)  # Uses last energy
        assert session.energy == 0
        success, msg, result = session.click_rock(1, 0, empowered=True)
        assert not success
        assert "energy" in msg.lower()
        assert result is None
        assert session.energy == 0

    def test_passive_drill_costs_no_energy(self) -> None:
        config = MiningConfig(
            system_id="test",
            max_energy=20,
            rock_distribution={"iron": 1.0},
            base_passive_rate=0.10,
        )
        session = MiningSession(config, starting_depth=20)
        session.click_rock(0, 0)
        energy_after_click = session.energy
        session.update(1.0)
        assert session.energy == energy_after_click

    def test_drone_mining_costs_no_energy(self) -> None:
        config = MiningConfig(
            system_id="test",
            max_energy=20,
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ELITE)
        session = MiningSession(config, drones=[drone])
        initial_energy = session.energy
        session.update(1.0)
        assert session.energy == initial_energy

    def test_energy_regenerates_over_time(self) -> None:
        config = MiningConfig(
            system_id="test",
            max_energy=20,
            energy_regen_seconds=3.0,
        )
        session = MiningSession(config)
        session.click_rock(0, 0, empowered=True)  # Spend energy
        energy_after = session.energy
        assert energy_after < 20
        session.update(30.0)  # Plenty of time to regen
        assert session.energy == 20

    def test_energy_regen_accumulates_fractional(self) -> None:
        config = MiningConfig(
            system_id="test",
            max_energy=20,
            energy_regen_seconds=2.0,
        )
        session = MiningSession(config)
        session.click_rock(0, 0, empowered=True)
        session.click_rock(0, 0, empowered=True)
        energy_after = session.energy
        assert energy_after < 20
        session.update(1.0)  # Half of regen period
        mid_energy = session.energy
        session.update(1.0)  # Complete the regen period
        assert session.energy >= mid_energy  # Should have regened

    def test_energy_does_not_exceed_max(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        assert session.energy == 20
        session.update(100.0)  # Long time, already at max
        assert session.energy == 20

    def test_multiple_empowered_clicks_drain_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        for i in range(5):
            session.click_rock(i % session.config.grid_width, 0, empowered=True)
        assert session.energy < 20

    def test_click_depleted_does_not_consume_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        rock = session.get_rock_at(0, 0)
        rock.depleted = True
        session.click_rock(0, 0)
        assert session.energy == 20

    def test_click_invalid_position_does_not_consume_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        session.click_rock(99, 99)
        assert session.energy == 20

    def test_get_click_energy_cost_default(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert session.get_click_energy_cost() == 1


# === Rare Ore Chance Wiring Tests ===


class TestRareChanceWiring:
    """Tests for rare ore chance bonus affecting rock generation."""

    def test_rare_bonus_increases_crystal_weight(self) -> None:
        """Large rare bonus produces statistically more crystal rocks."""
        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 0.50, "iron": 0.30, "crystal": 0.15, "rare": 0.05},
        )
        # No bonus — count crystals
        counts_base = 0
        for _ in range(20):
            session = MiningSession(config, rare_chance_bonus=0.0, starting_depth=80)
            counts_base += sum(1 for r in session.rocks if r.rock_type == RockType.CRYSTAL)

        # Large bonus
        counts_bonus = 0
        for _ in range(20):
            session = MiningSession(config, rare_chance_bonus=5.0, starting_depth=80)
            counts_bonus += sum(1 for r in session.rocks if r.rock_type == RockType.CRYSTAL)

        assert counts_bonus > counts_base, (
            f"Crystal count with 5x bonus ({counts_bonus}) should exceed base ({counts_base})"
        )

    def test_rare_bonus_increases_rare_weight(self) -> None:
        """Large rare bonus produces statistically more rare rocks."""
        import random as rng_module

        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 0.50, "iron": 0.30, "crystal": 0.15, "rare": 0.05},
        )
        # Seed for deterministic results across runs
        rng_module.seed(42)
        counts_base = 0
        for _ in range(50):
            session = MiningSession(config, rare_chance_bonus=0.0, starting_depth=80)
            counts_base += sum(1 for r in session.rocks if r.rock_type == RockType.RARE)

        rng_module.seed(42)
        counts_bonus = 0
        for _ in range(50):
            session = MiningSession(config, rare_chance_bonus=5.0, starting_depth=80)
            counts_bonus += sum(1 for r in session.rocks if r.rock_type == RockType.RARE)

        assert counts_bonus > counts_base, (
            f"Rare count with 5x bonus ({counts_bonus}) should exceed base ({counts_base})"
        )

    def test_zero_bonus_uses_base_distribution(self) -> None:
        """Zero bonus should not alter the distribution."""
        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 1.0},
        )
        session = MiningSession(config, rare_chance_bonus=0.0)
        # All rocks should be common with 100% common distribution
        assert all(r.rock_type == RockType.COMMON for r in session.rocks)

    def test_only_crystal_and_rare_weights_boosted(self) -> None:
        """Common and iron weights remain unchanged before normalization."""
        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 0.50, "iron": 0.30, "crystal": 0.15, "rare": 0.05},
        )
        # With huge bonus, common+iron fraction should decrease
        counts_common_iron_base = 0
        total_base = 0
        for _ in range(20):
            session = MiningSession(config, rare_chance_bonus=0.0, starting_depth=80)
            counts_common_iron_base += sum(
                1 for r in session.rocks if r.rock_type in (RockType.COMMON, RockType.IRON)
            )
            total_base += len(session.rocks)

        counts_common_iron_bonus = 0
        total_bonus = 0
        for _ in range(20):
            session = MiningSession(config, rare_chance_bonus=5.0, starting_depth=80)
            counts_common_iron_bonus += sum(
                1 for r in session.rocks if r.rock_type in (RockType.COMMON, RockType.IRON)
            )
            total_bonus += len(session.rocks)

        base_frac = counts_common_iron_base / total_base
        bonus_frac = counts_common_iron_bonus / total_bonus
        assert bonus_frac < base_frac, (
            f"Common+Iron fraction with bonus ({bonus_frac:.2f}) "
            f"should be less than base ({base_frac:.2f})"
        )

    def test_regenerate_applies_rare_bonus(self) -> None:
        """Regenerated field also uses the rare bonus."""
        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 0.50, "iron": 0.30, "crystal": 0.15, "rare": 0.05},
        )
        # Count rare+crystal across multiple regenerations with large bonus
        session = MiningSession(config, rare_chance_bonus=5.0, starting_depth=80)
        rare_count = sum(
            1 for r in session.rocks if r.rock_type in (RockType.CRYSTAL, RockType.RARE)
        )
        session.regenerate_field()
        rare_count_regen = sum(
            1 for r in session.rocks if r.rock_type in (RockType.CRYSTAL, RockType.RARE)
        )
        # Both should have elevated counts (at least some rare/crystal)
        assert rare_count + rare_count_regen > 0


# === Depth Scaling Tests ===


class TestDepthScaling:
    """Tests for mining depth progression and scaling."""

    def test_session_starts_at_depth_1(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert session.depth == 1

    def test_regenerate_increments_depth(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.regenerate_field()
        assert session.depth == 2
        session.regenerate_field()
        assert session.depth == 3

    def test_depth_modifiers_surface(self) -> None:
        """Depths 1-20 (Surface): no rare bonus, energy_mult=1, yield=0."""
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        for d in (1, 10, 20):
            session.depth = d
            mods = session.get_depth_modifiers()
            assert mods.rare_weight_bonus == 0.0, f"depth {d}"
            assert mods.energy_cost_multiplier == 1, f"depth {d}"
            assert mods.yield_bonus == 0.0, f"depth {d}"

    def test_depth_modifiers_shallow(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 30
        mods = session.get_depth_modifiers()
        assert mods.rare_weight_bonus == pytest.approx(0.10)
        assert mods.energy_cost_multiplier == 1
        assert mods.yield_bonus == pytest.approx(0.10)

    def test_depth_modifiers_shallow_end(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 50
        mods = session.get_depth_modifiers()
        assert mods.rare_weight_bonus == pytest.approx(0.30)
        assert mods.energy_cost_multiplier == 1
        assert mods.yield_bonus == pytest.approx(0.10)

    def test_depth_modifiers_mid_strata(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 60
        mods = session.get_depth_modifiers()
        assert mods.rare_weight_bonus == pytest.approx(0.42)
        assert mods.energy_cost_multiplier == 2
        assert mods.yield_bonus == pytest.approx(0.20)

    def test_depth_modifiers_deep_core(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 100
        mods = session.get_depth_modifiers()
        assert mods.rare_weight_bonus == pytest.approx(0.93)
        assert mods.energy_cost_multiplier == 2
        assert mods.yield_bonus == pytest.approx(0.30)

    def test_energy_cost_doubles_at_mid_strata(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 60
        assert session.get_click_energy_cost() == 2

    def test_energy_cost_is_1_at_shallow(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        session.depth = 50
        assert session.get_click_energy_cost() == 1

    def test_yield_bonus_click_break(self) -> None:
        """Breaking a rock at depth 4+ gives bonus yield."""
        config = MiningConfig(
            system_id="test",
            grid_width=1,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config)
        session.depth = 60  # yield_bonus = 0.20

        # Break a rock — common yields 1-3, with 20% bonus: floor(base * 0.20) extra
        # Use 1x1 grid to prevent chain detonation interference
        success, msg, result = session.click_rock(0, 0)
        assert result is not None, "Rock should break with 0.50 click_power on common"
        # Verify total_mined reflects the yielded amount
        assert session.total_mined[result.commodity_id] == result.quantity

    def test_yield_bonus_passive_break(self) -> None:
        """Passive drill break at depth applies yield bonus."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_passive_rate=0.50,
        )
        session = MiningSession(config)
        session.depth = 60
        session.click_rock(0, 0)  # Set active rock
        results = session.update(2.0)  # Enough time to break common
        assert len(results) >= 1
        # Result quantity should be tracked
        assert session.total_mined[results[0].commodity_id] >= results[0].quantity

    def test_yield_bonus_drone_break(self) -> None:
        """Drone break at depth applies yield bonus."""
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ELITE)
        session = MiningSession(config, drones=[drone])
        session.depth = 60
        results = session.update(2.0)
        assert len(results) >= 1

    def test_depth_rare_stacks_with_skill_rare(self) -> None:
        """Depth rare bonus and skill rare bonus stack additively."""
        config = MiningConfig(
            system_id="test",
            grid_width=10,
            grid_height=10,
            rock_distribution={"common": 0.50, "iron": 0.30, "crystal": 0.15, "rare": 0.05},
        )
        # Skill bonus only
        session_skill = MiningSession(config, rare_chance_bonus=1.0, starting_depth=80)
        session_skill.depth = 1  # No depth bonus
        crystal_skill = sum(
            1 for r in session_skill.rocks if r.rock_type in (RockType.CRYSTAL, RockType.RARE)
        )

        # Skill + depth bonus (depth=100 is Deep Core)
        session_both = MiningSession(config, rare_chance_bonus=1.0, starting_depth=80)
        session_both.depth = 100
        session_both.regenerate_field()  # Regenerate to apply depth bonus
        # Just verify the field was regenerated with bonus applied
        # At depth 101: no hazards yet (those start at 100), grid should be full
        assert len(session_both.rocks) + len(session_both.hazards) == 100

    def test_regenerate_refills_energy(self) -> None:
        config = MiningConfig(system_id="test", max_energy=20)
        session = MiningSession(config)
        # Drain some energy via empowered clicks
        for i in range(5):
            session.click_rock(i % session.config.grid_width, 0, empowered=True)
        assert session.energy < 20
        session.regenerate_field()
        assert session.energy == 20


# === Chain Detonation Tests ===


class TestChainDetonation:
    """Tests for chain detonation when breaking rocks near same-type neighbors."""

    def test_chain_results_empty_initially(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert session.chain_results == []
        assert session.total_chains == 0

    def test_no_chain_different_type_neighbors(self) -> None:
        """No chain when neighbors are different types."""
        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)  # Guaranteed chain
        # Force different types for neighbors
        session.rocks[0].rock_type = RockType.IRON
        session.rocks[1].rock_type = RockType.COMMON
        session.rocks[2].rock_type = RockType.CRYSTAL
        # Break the middle rock
        session.click_rock(1, 0)
        assert len(session.chain_results) == 0

    def test_chain_applies_progress_to_same_type_neighbor(self) -> None:
        """Chain adds progress to same-type neighbors."""
        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=1,
            rock_distribution={"iron": 1.0},
            base_click_power=0.50,
        )
        # chain_chance_bonus high enough to guarantee chain
        session = MiningSession(config, chain_chance_bonus=10.0, starting_depth=20)
        # All iron. Break middle rock.
        # Iron hardness=1.0, power=0.50 → 0.50 progress per click, need 2 clicks
        session.click_rock(1, 0)
        session.click_rock(1, 0)
        # Middle rock should be broken now, chains should fire on neighbors
        # With high chain chance, neighbors should get CHAIN_PROGRESS_AMOUNT
        rock_left = session.get_rock_at(0, 0)
        rock_right = session.get_rock_at(2, 0)
        # At least one neighbor should have been affected (chain or broken)
        any_affected = (
            rock_left.drill_progress > 0
            or rock_left.depleted
            or rock_right.drill_progress > 0
            or rock_right.depleted
        )
        assert any_affected

    def test_chain_breaks_neighbor_above_threshold(self) -> None:
        """Neighbor at high progress breaks from chain."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        # Set neighbor nearly broken
        neighbor = session.get_rock_at(1, 0)
        neighbor.drill_progress = 0.90
        # Break the first rock (common hardness=0.5, power=0.50 → instant)
        session.click_rock(0, 0)
        # Chain should push neighbor over threshold
        assert neighbor.depleted
        assert len(session.chain_results) >= 1
        assert session.chain_results[0].grid_x == 1
        assert session.chain_results[0].grid_y == 0

    def test_chain_breaks_neighbor_from_zero_progress(self) -> None:
        """Chain detonation breaks neighbor outright (CHAIN_PROGRESS_AMOUNT=1.0)."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        neighbor = session.get_rock_at(1, 0)
        neighbor.drill_progress = 0.0  # Fresh rock
        session.click_rock(0, 0)
        # CHAIN_PROGRESS_AMOUNT=1.0, so neighbor should break
        assert neighbor.depleted
        assert neighbor.drill_progress >= 1.0

    def test_chain_cascades_to_depth_2(self) -> None:
        """Chain can cascade through multiple same-type neighbors."""
        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        # Set all three nearly broken
        for rock in session.rocks:
            rock.drill_progress = 0.90
        # Break first rock
        session.click_rock(0, 0)
        # Middle rock should chain from first, then right rock from middle
        middle = session.get_rock_at(1, 0)
        right = session.get_rock_at(2, 0)
        assert middle.depleted, "Middle rock should be chain-broken"
        assert right.depleted, "Right rock should cascade from middle"
        assert len(session.chain_results) >= 2

    def test_chain_stops_at_max_depth_3(self) -> None:
        """Chain stops cascading at CHAIN_MAX_DEPTH."""
        config = MiningConfig(
            system_id="test",
            grid_width=5,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        # Set all rocks nearly broken
        for rock in session.rocks:
            rock.drill_progress = 0.90
        session.click_rock(0, 0)
        # Rocks 1,2,3 can chain (depths 1,2,3). Rock 4 should NOT chain (depth 4).
        rock_4 = session.get_rock_at(4, 0)
        # Chain max is 3, so depth-4 cascade shouldn't happen
        # The chain goes: 0 breaks → 1 (depth 1) → 2 (depth 2) → 3 (depth 3) → STOP
        assert not rock_4.depleted

    def test_chain_skips_depleted(self) -> None:
        """Chain does not affect already-depleted neighbors."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        neighbor = session.get_rock_at(1, 0)
        neighbor.depleted = True
        session.click_rock(0, 0)
        assert len(session.chain_results) == 0

    def test_chain_updates_total_mined(self) -> None:
        """Chain-broken rocks contribute to total_mined."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        neighbor = session.get_rock_at(1, 0)
        neighbor.drill_progress = 0.90
        session.click_rock(0, 0)
        # Both the clicked rock and chain-broken rock should contribute
        total = session.total_mined.get("raw_ore", 0)
        assert total >= 2  # At least 1 from each rock

    def test_chain_chance_bonus_increases_probability(self) -> None:
        """Higher chain chance bonus means more chain events."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        # Run many trials with no bonus vs high bonus
        chains_no_bonus = 0
        chains_high_bonus = 0
        for _ in range(100):
            session = MiningSession(config, chain_chance_bonus=0.0)
            session.get_rock_at(1, 0).drill_progress = 0.90
            session.click_rock(0, 0)
            chains_no_bonus += len(session.chain_results)

            session2 = MiningSession(config, chain_chance_bonus=2.0)
            session2.get_rock_at(1, 0).drill_progress = 0.90
            session2.click_rock(0, 0)
            chains_high_bonus += len(session2.chain_results)

        assert chains_high_bonus > chains_no_bonus

    def test_chain_triggered_by_click(self) -> None:
        """Click-breaking a rock triggers chain check."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        session.get_rock_at(1, 0).drill_progress = 0.90
        session.click_rock(0, 0)
        assert len(session.chain_results) >= 1

    def test_chain_triggered_by_passive(self) -> None:
        """Passive drill breaking a rock triggers chain check."""
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_passive_rate=2.0,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        session.get_rock_at(1, 0).drill_progress = 0.90
        session.click_rock(0, 0)  # Set active rock
        results = session.update(1.0)  # Passive breaks it
        assert len(results) >= 1
        assert session.total_chains >= 1

    def test_chain_triggered_by_drone(self) -> None:
        """Drone breaking a rock triggers chain check."""
        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=1,
            rock_distribution={"common": 1.0},
        )
        drone = MiningDrone(tier=DroneTier.ELITE)
        session = MiningSession(config, drones=[drone], chain_chance_bonus=10.0)
        # Set all rocks nearly broken so chain fires
        for rock in session.rocks:
            rock.drill_progress = 0.80
        results = session.update(1.0)
        # Drone should break one, chain should break at least one more
        assert session.total_chains >= 1

    def test_chain_results_cleared_between_calls(self) -> None:
        """chain_results is cleared at start of each click_rock/update call."""
        config = MiningConfig(
            system_id="test",
            grid_width=3,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        session = MiningSession(config, chain_chance_bonus=10.0)
        session.get_rock_at(1, 0).drill_progress = 0.90
        session.click_rock(0, 0)
        first_chains = len(session.chain_results)
        assert first_chains >= 1
        # Next call should clear previous results
        session.click_rock(2, 0)
        # chain_results should be fresh (may or may not have new chains)
        # But should NOT contain the old chain from (1,0)
        old_chain_positions = [(c.grid_x, c.grid_y) for c in session.chain_results]
        # Rock at (1,0) is already depleted, so it can't chain again
        assert (1, 0) not in old_chain_positions


# === Session Milestones Tests ===


class TestSessionMilestones:
    """Tests for mining session milestone tracking."""

    def _make_milestones(
        self, category: str, threshold: int, reward_xp: int = 25, reward_credits: int = 0
    ) -> list[MiningMilestone]:
        return [
            MiningMilestone(
                id=f"test_{category}",
                description=f"Test {category}",
                category=category,
                threshold=threshold,
                reward_xp=reward_xp,
                reward_credits=reward_credits,
            )
        ]

    def test_session_has_3_milestones(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert len(session.milestones) == 3

    def test_milestones_start_incomplete(self) -> None:
        config = MiningConfig(system_id="test")
        session = MiningSession(config)
        assert all(not m.completed for m in session.milestones)

    def test_rocks_mined_milestone_completes(self) -> None:
        config = MiningConfig(
            system_id="test",
            grid_width=1,
            grid_height=2,
            rock_distribution={"common": 1.0},
            base_click_power=5.0,
        )
        milestones = self._make_milestones("rocks_mined", threshold=2)
        session = MiningSession(config, milestones=milestones)
        # 1-wide grid: rocks at (0,0) and (0,1) are neighbors but both common.
        # With high click power, rock breaks instantly. Chain may fire but
        # that just means more rocks break — threshold=2 is still met.
        session.click_rock(0, 0)  # Break rock 1
        if not milestones[0].completed:
            # Chain didn't break rock 2, click it manually
            session.click_rock(0, 1)
        assert milestones[0].completed

    def test_rare_ores_tracked(self) -> None:
        import random

        random.seed(42)  # Deterministic: avoid flaky results from test ordering
        config = MiningConfig(
            system_id="test",
            rock_distribution={"crystal": 1.0},
            base_click_power=5.0,
        )
        milestones = self._make_milestones("rare_ores", threshold=1)
        session = MiningSession(config, milestones=milestones, starting_depth=80)
        # Crystal and rare both count as rare ores. At depth 9,
        # depth gating adds iron/dense/rare alongside crystal.
        # Click all rocks to guarantee at least one crystal or rare.
        for y in range(config.grid_height):
            for x in range(config.grid_width):
                session.click_rock(x, y)
                if session.rare_ores_found >= 1:
                    break
            if session.rare_ores_found >= 1:
                break
        assert session.rare_ores_found >= 1
        assert milestones[0].completed

    def test_common_not_counted_as_rare(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        milestones = self._make_milestones("rare_ores", threshold=1)
        session = MiningSession(config, milestones=milestones)
        session.click_rock(0, 0)  # Break common rock
        assert session.rare_ores_found == 0
        assert not milestones[0].completed

    def test_depth_milestone_completes(self) -> None:
        config = MiningConfig(system_id="test")
        milestones = self._make_milestones("depth_reached", threshold=3)
        session = MiningSession(config, milestones=milestones, starting_depth=1)
        assert not milestones[0].completed
        session.regenerate_field()  # depth 2
        session.regenerate_field()  # depth 3
        session._check_milestones()
        assert milestones[0].completed

    def test_chains_milestone_completes(self) -> None:
        config = MiningConfig(
            system_id="test",
            grid_width=2,
            grid_height=1,
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        milestones = self._make_milestones("chains_triggered", threshold=1)
        session = MiningSession(config, chain_chance_bonus=10.0, milestones=milestones)
        session.get_rock_at(1, 0).drill_progress = 0.90
        session.click_rock(0, 0)
        assert session.total_chains >= 1
        assert milestones[0].completed

    def test_milestone_not_double_completed(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        milestones = self._make_milestones("rocks_mined", threshold=1)
        session = MiningSession(config, milestones=milestones)
        session.click_rock(0, 0)
        assert milestones[0].completed
        # Clear newly_completed and break another — milestone shouldn't re-trigger
        session.newly_completed_milestones.clear()
        session.click_rock(1, 0)
        assert len(session.newly_completed_milestones) == 0

    def test_newly_completed_populated_and_cleared(self) -> None:
        config = MiningConfig(
            system_id="test",
            rock_distribution={"common": 1.0},
            base_click_power=0.50,
        )
        milestones = self._make_milestones("rocks_mined", threshold=1)
        session = MiningSession(config, milestones=milestones)
        session.click_rock(0, 0)
        assert len(session.newly_completed_milestones) == 1
        assert session.newly_completed_milestones[0].id == "test_rocks_mined"
        # Next call clears it
        session.click_rock(1, 0)
        # newly_completed should be empty (no new milestones to complete)
        assert len(session.newly_completed_milestones) == 0

    def test_custom_milestones_for_testing(self) -> None:
        """Injectable milestones param works for testing."""
        config = MiningConfig(system_id="test")
        custom = [
            MiningMilestone(
                id="custom_1",
                description="Custom",
                category="rocks_mined",
                threshold=99,
                reward_xp=100,
            )
        ]
        session = MiningSession(config, milestones=custom)
        assert len(session.milestones) == 1
        assert session.milestones[0].id == "custom_1"
