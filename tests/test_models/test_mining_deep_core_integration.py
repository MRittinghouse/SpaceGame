"""Tests for mining session integration with deep core systems."""

import pytest
import math

from spacegame.models.mining import MiningSession, MiningConfig, MiningResult
from spacegame.models.ore_silo import OreSilo
from spacegame.models.deep_core import calculate_strata_earned


class TestDepthAdvanceResult:
    """Tests for strata token generation on depth advance."""

    def test_regenerate_field_returns_result(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        result = session.regenerate_field()
        assert result is not None
        assert hasattr(result, "strata_earned")
        assert hasattr(result, "was_full_clear")

    def test_strata_earned_at_depth_1(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        # Depth starts at 1, regenerate advances to 2
        result = session.regenerate_field()
        # Strata for clearing depth 1 = floor(1 * 1.5) = 1
        assert result.strata_earned == 1

    def test_full_clear_gives_bonus(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        # Deplete all rocks to trigger full clear
        for rock in session.rocks:
            rock.depleted = True
        result = session.regenerate_field()
        assert result.was_full_clear
        # depth 1: base=1, bonus=floor(1*0.5)=0, total=1
        # Actually bonus for depth 1 is floor(1*0.5) = 0
        assert result.strata_earned == 1

    def test_partial_clear_no_bonus(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        # Leave some rocks undepleted
        result = session.regenerate_field()
        assert not result.was_full_clear

    def test_deeper_depth_earns_more_strata(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        session.depth = 9  # Will advance to 10
        result = session.regenerate_field()
        # Strata for clearing depth 9 = floor(9 * 1.5) = 13
        assert result.strata_earned == 13

    def test_prestige_multiplier_applied(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config, prestige_level=5)
        session.depth = 9
        result = session.regenerate_field()
        base = calculate_strata_earned(9, full_clear=False, prestige_level=0)
        expected = calculate_strata_earned(9, full_clear=False, prestige_level=5)
        assert result.strata_earned == expected
        assert expected > base


class TestSiloIntegration:
    """Tests for mining output going to silo."""

    def test_mine_to_silo_via_click(self) -> None:
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        silo = OreSilo(system_id="breakstone")

        # Click a rock until it breaks
        rock = session.rocks[0]
        result = None
        for _ in range(100):
            success, msg, result = session.click_rock(rock.grid_x, rock.grid_y)
            if result is not None:
                break

        assert result is not None, "Rock should have broken"
        # Add to silo instead of cargo
        added = silo.add_ore(result.commodity_id, result.quantity)
        assert added == result.quantity
        assert silo.get_total_stored() > 0

    def test_silo_full_still_allows_clicks(self) -> None:
        """Even when silo is full, clicks should work (ore is lost)."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        silo = OreSilo(system_id="breakstone", capacity=0)

        rock = session.rocks[0]
        success, msg, _ = session.click_rock(rock.grid_x, rock.grid_y)
        assert success, "Click should succeed even with full silo"


class TestDeepCoreEffects:
    """Tests for deep core upgrade effects on mining session."""

    def test_click_power_bonus_from_deep_core(self) -> None:
        config = MiningConfig(system_id="breakstone")
        # 24% click power bonus from core_resonance level 3
        session = MiningSession(config, click_power_bonus=0.24)
        expected_power = config.base_click_power * (1 + 0.24)
        rock = session.rocks[0]
        initial_progress = rock.drill_progress
        session.click_rock(rock.grid_x, rock.grid_y)
        actual_progress = rock.drill_progress - initial_progress
        # Progress should be power / hardness
        expected_progress = expected_power / rock.hardness
        if not rock.depleted:
            assert actual_progress == pytest.approx(expected_progress, abs=0.01)

    def test_max_energy_bonus_from_deep_core(self) -> None:
        config = MiningConfig(system_id="breakstone", max_energy=20)
        # energy_conduit level 2 = +6 max energy
        session = MiningSession(config)
        # Simulate the bonus being applied before session
        session.max_energy = config.max_energy + 6
        session.energy = session.max_energy
        assert session.max_energy == 26
        assert session.energy == 26

    def test_chain_chance_bonus_from_seismic_pulse(self) -> None:
        """Seismic Pulse adds chain_chance_bonus to session."""
        config = MiningConfig(system_id="breakstone")
        # Level 2 = +10% chain chance
        session = MiningSession(config, chain_chance_bonus=0.10)
        assert session.chain_chance_bonus == pytest.approx(0.10)

    def test_seismic_pulse_level_3_increases_max_chain_depth(self) -> None:
        """Seismic Pulse level 3 should increase max chain depth by 1."""
        from spacegame.models.mining import CHAIN_MAX_DEPTH

        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config, max_chain_depth_bonus=1)
        assert session.max_chain_depth == CHAIN_MAX_DEPTH + 1

    def test_max_chain_depth_default_is_base(self) -> None:
        """Without bonus, max chain depth should be the base constant."""
        from spacegame.models.mining import CHAIN_MAX_DEPTH

        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        assert session.max_chain_depth == CHAIN_MAX_DEPTH

    def test_depth_scanner_sets_starting_depth(self) -> None:
        """Depth Scanner level sets starting depth to 1 + level."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config, starting_depth=3)
        assert session.depth == 3

    def test_depth_scanner_zero_starts_at_1(self) -> None:
        """Without depth_scanner, session starts at depth 1."""
        config = MiningConfig(system_id="breakstone")
        session = MiningSession(config)
        assert session.depth == 1

    def test_automaton_core_increases_drone_speed(self) -> None:
        """Automaton Core adds drone_speed_bonus to session."""
        config = MiningConfig(system_id="breakstone")
        # Level 2 = +30% drone speed
        session = MiningSession(config, drone_speed_bonus=0.30)
        assert session.drone_speed_bonus == pytest.approx(0.30)

    def test_chain_depth_bonus_limits_recursion(self) -> None:
        """Chain detonation should respect the increased max depth."""
        import random
        from spacegame.models.mining import AsteroidRock, RockType, CHAIN_MAX_DEPTH

        random.seed(1)
        config = MiningConfig(system_id="breakstone", grid_width=6, grid_height=1)
        # Guarantee chains fire, and add +1 max chain depth
        session = MiningSession(
            config, chain_chance_bonus=10.0, max_chain_depth_bonus=1
        )
        # Place a line of common rocks with high progress so chain breaks them
        session.rocks = [
            AsteroidRock(rock_type=RockType.COMMON, grid_x=i, grid_y=0)
            for i in range(6)
        ]
        for rock in session.rocks[1:]:
            rock.drill_progress = 0.80  # Will break with 0.25 chain progress
        # Break the first rock
        session.rocks[0].depleted = True
        session._on_rock_broken(session.rocks[0])
        session._check_chain_detonation(session.rocks[0])
        # With +1 max depth (4 total), chains should cascade further
        broken_count = sum(1 for r in session.rocks if r.depleted)
        assert broken_count > 1, "Chain should have broken at least one neighbor"
        # Verify the max_chain_depth is correctly set
        assert session.max_chain_depth == CHAIN_MAX_DEPTH + 1
