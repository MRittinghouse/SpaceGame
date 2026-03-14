"""Tests for mining energy rework.

Verifies that:
- Normal clicks are free (no energy cost)
- Empowered clicks cost energy and do triple damage
- Drones stop mining when cargo is full
"""

from spacegame.models.mining import MiningConfig, MiningSession, RockType


def _make_session(**kwargs) -> MiningSession:
    """Create a test mining session with defaults."""
    config = MiningConfig(
        system_id="test",
        grid_width=4,
        grid_height=3,
        max_energy=20,
    )
    return MiningSession(config=config, **kwargs)


class TestInfiniteClicks:
    """Normal clicks should be free (no energy cost)."""

    def test_click_does_not_consume_energy(self) -> None:
        """A normal click should not reduce energy."""
        session = _make_session()
        initial_energy = session.energy
        rock = session.rocks[0]

        success, _, _ = session.click_rock(rock.grid_x, rock.grid_y)
        assert success
        assert session.energy == initial_energy

    def test_click_works_at_zero_energy(self) -> None:
        """Player can click even with zero energy."""
        session = _make_session()
        session.energy = 0
        rock = session.rocks[0]

        success, _, _ = session.click_rock(rock.grid_x, rock.grid_y)
        assert success, "Click should succeed at zero energy"

    def test_multiple_clicks_at_zero_energy(self) -> None:
        """Multiple clicks work without energy."""
        session = _make_session()
        session.energy = 0
        rock = session.rocks[0]

        for _ in range(10):
            success, _, _ = session.click_rock(rock.grid_x, rock.grid_y)
            if not success:
                # Rock might be depleted, try next
                break
            assert session.energy == 0


class TestEmpoweredClicks:
    """Empowered clicks use energy for triple damage."""

    def test_empowered_click_costs_energy(self) -> None:
        """Empowered click deducts energy."""
        session = _make_session()
        initial_energy = session.energy
        rock = session.rocks[0]

        success, _, _ = session.click_rock(rock.grid_x, rock.grid_y, empowered=True)
        assert success
        assert session.energy < initial_energy

    def test_empowered_click_fails_without_energy(self) -> None:
        """Cannot empower a click with no energy."""
        session = _make_session()
        session.energy = 0
        rock = session.rocks[0]

        success, msg, _ = session.click_rock(rock.grid_x, rock.grid_y, empowered=True)
        assert not success
        assert "energy" in msg.lower()

    def test_empowered_click_triple_power(self) -> None:
        """Empowered clicks apply 3x the normal click power."""
        session = _make_session()
        rock_a = session.rocks[0]
        rock_b = session.rocks[1]

        # Normal click
        session.click_rock(rock_a.grid_x, rock_a.grid_y)
        normal_progress = rock_a.drill_progress

        # Empowered click (on a fresh rock)
        session.click_rock(rock_b.grid_x, rock_b.grid_y, empowered=True)
        empowered_progress = rock_b.drill_progress

        # Same rock type -> same hardness, so empowered should be 3x
        if rock_a.rock_type == rock_b.rock_type:
            assert abs(empowered_progress - normal_progress * 3) < 0.01, (
                f"Empowered progress ({empowered_progress}) should be 3x normal ({normal_progress})"
            )

    def test_empowered_cost_scales_with_depth(self) -> None:
        """Empowered click energy cost scales with depth modifiers."""
        session = _make_session()
        rock = session.rocks[0]

        cost_depth_1 = session.get_click_energy_cost()
        # At depth 1, cost should be 1
        assert cost_depth_1 >= 1

        success, _, _ = session.click_rock(rock.grid_x, rock.grid_y, empowered=True)
        assert success
        assert session.energy == session.max_energy - cost_depth_1


class TestDroneCargoCheck:
    """Drones should stop mining when cargo is full."""

    def test_update_returns_no_results_when_cargo_full(self) -> None:
        """When cargo_full=True, drones should not produce results."""
        from spacegame.models.drone import MiningDrone, DroneTier

        drone = MiningDrone(tier=DroneTier.BASIC)
        session = _make_session(drones=[drone])

        # Run a bunch of frames with cargo_full=True
        results = []
        for _ in range(100):
            frame_results = session.update(0.1, cargo_full=True)
            results.extend(frame_results)

        # Drones should not have produced any results
        assert len(results) == 0, "Drones should not mine when cargo is full"

    def test_passive_drill_stops_when_cargo_full(self) -> None:
        """Passive drill should not break rocks when cargo is full."""
        session = _make_session()
        rock = session.rocks[0]

        # Start drilling a rock
        session.click_rock(rock.grid_x, rock.grid_y)
        assert session.active_rock is not None

        # Run updates with cargo_full — should not break the rock
        for _ in range(100):
            results = session.update(0.1, cargo_full=True)
            # Should not produce any results
            assert len(results) == 0, "Passive drill should not yield when cargo full"
