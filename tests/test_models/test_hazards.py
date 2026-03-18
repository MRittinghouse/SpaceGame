"""Tests for environmental hazards (Unstable Cells, Pressure Vents)."""

import pytest

from spacegame.models.mining import (
    MiningSession,
    MiningConfig,
    RockType,
    AsteroidRock,
    HazardType,
    HazardCell,
)


class TestHazardType:
    """Tests for HazardType enum."""

    def test_unstable_cell_value(self) -> None:
        assert HazardType.UNSTABLE_CELL.value == "unstable_cell"

    def test_pressure_vent_value(self) -> None:
        assert HazardType.PRESSURE_VENT.value == "pressure_vent"


class TestHazardCell:
    """Tests for HazardCell dataclass."""

    def test_create_unstable_cell(self) -> None:
        cell = HazardCell(hazard_type=HazardType.UNSTABLE_CELL, grid_x=2, grid_y=3)
        assert cell.hazard_type == HazardType.UNSTABLE_CELL
        assert cell.grid_x == 2
        assert cell.grid_y == 3

    def test_create_pressure_vent(self) -> None:
        cell = HazardCell(hazard_type=HazardType.PRESSURE_VENT, grid_x=1, grid_y=1)
        assert cell.hazard_type == HazardType.PRESSURE_VENT
        assert cell.pulse_timer == 0.0


class TestUnstableCellSpawning:
    """Tests for Unstable Cell spawning at depth 10+."""

    def test_no_hazards_at_shallow_depth(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        assert session.depth == 1
        assert len(session.hazards) == 0

    def test_no_hazards_at_depth_9(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 8
        session.regenerate_field()
        assert session.depth == 9
        unstable = [h for h in session.hazards if h.hazard_type == HazardType.UNSTABLE_CELL]
        assert len(unstable) == 0

    def test_unstable_cells_at_depth_10(self) -> None:
        """Unstable cells should appear at depth 10+."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 9
        session.regenerate_field()
        assert session.depth == 10
        unstable = [h for h in session.hazards if h.hazard_type == HazardType.UNSTABLE_CELL]
        assert len(unstable) >= 1

    def test_unstable_cells_dont_overlap_rocks(self) -> None:
        """Unstable cells should not occupy the same position as a rock."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 9
        session.regenerate_field()
        rock_positions = {(r.grid_x, r.grid_y) for r in session.rocks}
        for h in session.hazards:
            assert (h.grid_x, h.grid_y) not in rock_positions


class TestUnstableCellDetonation:
    """Tests for Unstable Cell detonation when adjacent rock breaks."""

    def test_unstable_cell_detonates_on_adjacent_break(self) -> None:
        """Breaking a rock adjacent to an unstable cell triggers detonation."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.energy = 20
        session.hazards = [
            HazardCell(hazard_type=HazardType.UNSTABLE_CELL, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
        ]
        # Break the first rock
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_unstable_detonation(session.rocks[0])
        # Rock at (2,0) is neighbor of unstable at (1,0) — should get 30% progress
        assert session.rocks[1].drill_progress == pytest.approx(0.30, abs=0.01)

    def test_unstable_cell_costs_energy(self) -> None:
        """Unstable cell detonation costs 3 energy."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.energy = 10
        session.hazards = [
            HazardCell(hazard_type=HazardType.UNSTABLE_CELL, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
        ]
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_unstable_detonation(session.rocks[0])
        assert session.energy == 7  # 10 - 3

    def test_unstable_cell_no_energy_no_detonation(self) -> None:
        """Unstable cell should not detonate if energy < 3."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.energy = 2  # Not enough
        session.hazards = [
            HazardCell(hazard_type=HazardType.UNSTABLE_CELL, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
        ]
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_unstable_detonation(session.rocks[0])
        # No detonation — neighbor should have no progress
        assert session.rocks[1].drill_progress == 0.0
        assert session.energy == 2

    def test_unstable_cell_consumed_after_detonation(self) -> None:
        """Unstable cell should be removed after detonating."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.energy = 20
        session.hazards = [
            HazardCell(hazard_type=HazardType.UNSTABLE_CELL, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
        ]
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_unstable_detonation(session.rocks[0])
        unstable = [h for h in session.hazards if h.hazard_type == HazardType.UNSTABLE_CELL]
        assert len(unstable) == 0


class TestPressureVentSpawning:
    """Tests for Pressure Vent spawning at depth 15+."""

    def test_no_vents_at_depth_14(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 13
        session.regenerate_field()
        assert session.depth == 14
        vents = [h for h in session.hazards if h.hazard_type == HazardType.PRESSURE_VENT]
        assert len(vents) == 0

    def test_vents_at_depth_15(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 14
        session.regenerate_field()
        assert session.depth == 15
        vents = [h for h in session.hazards if h.hazard_type == HazardType.PRESSURE_VENT]
        assert len(vents) >= 1


class TestPressureVentPulse:
    """Tests for Pressure Vent pulsing behavior."""

    def test_pressure_vent_pulses_at_interval(self) -> None:
        """Pressure vent applies 10% progress to adjacent rocks every 8 seconds."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.hazards = [
            HazardCell(hazard_type=HazardType.PRESSURE_VENT, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
            AsteroidRock(rock_type=RockType.COMMON, grid_x=2, grid_y=0),
        ]
        # Simulate 8 seconds of time
        session._update_pressure_vents(8.0)
        for rock in session.rocks:
            assert rock.drill_progress == pytest.approx(0.10, abs=0.01)

    def test_pressure_vent_timer_accumulates(self) -> None:
        """Timer should accumulate until reaching 8 seconds."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.hazards = [
            HazardCell(hazard_type=HazardType.PRESSURE_VENT, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
        ]
        # 4 seconds — not enough
        session._update_pressure_vents(4.0)
        assert session.rocks[0].drill_progress == 0.0
        # 4 more seconds — now fires
        session._update_pressure_vents(4.0)
        assert session.rocks[0].drill_progress == pytest.approx(0.10, abs=0.01)

    def test_pressure_vent_skips_depleted_rocks(self) -> None:
        """Pressure vents should not affect depleted rocks."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.hazards = [
            HazardCell(hazard_type=HazardType.PRESSURE_VENT, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
        ]
        session.rocks[0].depleted = True
        session._update_pressure_vents(8.0)
        assert session.rocks[0].drill_progress == 0.0

    def test_pressure_vent_can_break_rocks(self) -> None:
        """If pressure vent pushes progress >= 1.0, rock should break."""
        config = MiningConfig(system_id="breakstone", grid_width=3, grid_height=1)
        session = MiningSession(config)
        session.hazards = [
            HazardCell(hazard_type=HazardType.PRESSURE_VENT, grid_x=1, grid_y=0),
        ]
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=0, grid_y=0),
        ]
        session.rocks[0].drill_progress = 0.95
        session._update_pressure_vents(8.0)
        assert session.rocks[0].depleted
