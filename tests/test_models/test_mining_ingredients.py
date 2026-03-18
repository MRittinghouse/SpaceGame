"""Tests for mining ingredient drops (flux_catalyst, resonance_core)."""

import pytest
import random

from spacegame.models.mining import MiningResult, MiningSession, MiningConfig, ChainBreak


def _make_config() -> MiningConfig:
    return MiningConfig(
        system_id="iron_depths",
        grid_width=4,
        grid_height=4,
        base_click_power=1.0,
        base_passive_rate=0.5,
        energy_regen_seconds=3.0,
        max_energy=10,
    )


class TestMiningResultIngredients:
    """MiningResult should carry optional ingredient drops."""

    def test_default_no_ingredients(self) -> None:
        from spacegame.models.mining import RockType

        result = MiningResult(commodity_id="common_metals", quantity=3, rock_type=RockType.COMMON)
        assert result.ingredient_drops == {}

    def test_with_ingredients(self) -> None:
        from spacegame.models.mining import RockType

        result = MiningResult(
            commodity_id="common_metals",
            quantity=3,
            rock_type=RockType.COMMON,
            ingredient_drops={"flux_catalyst": 1},
        )
        assert result.ingredient_drops == {"flux_catalyst": 1}


class TestChainBreakIngredients:
    """ChainBreak should carry optional ingredient drops."""

    def test_default_no_ingredients(self) -> None:
        from spacegame.models.mining import RockType

        cb = ChainBreak(
            grid_x=0, grid_y=0, rock_type=RockType.COMMON,
            commodity_id="common_metals", quantity=3, chain_depth=1,
        )
        assert cb.ingredient_drops == {}


class TestIngredientDropRolling:
    """MiningSession._roll_ingredient_drops() depth-gated logic."""

    def test_no_drops_below_depth_8(self) -> None:
        session = MiningSession(_make_config())
        session.depth = 7
        # Run 100 rolls — should never drop anything
        drops_found = False
        for _ in range(100):
            drops = session._roll_ingredient_drops()
            if drops:
                drops_found = True
        assert not drops_found, "No ingredient drops should occur below depth 8"

    def test_flux_catalyst_at_depth_8(self) -> None:
        session = MiningSession(_make_config())
        session.depth = 8
        # Run many rolls to verify flux_catalyst can drop
        found = False
        for _ in range(500):
            drops = session._roll_ingredient_drops()
            if "flux_catalyst" in drops:
                found = True
                break
        assert found, "flux_catalyst should drop at depth 8+"

    def test_no_resonance_core_at_depth_8(self) -> None:
        session = MiningSession(_make_config())
        session.depth = 8
        # Resonance core requires depth 15+
        for _ in range(500):
            drops = session._roll_ingredient_drops()
            assert "resonance_core" not in drops, "resonance_core needs depth 15+"

    def test_resonance_core_at_depth_15(self) -> None:
        session = MiningSession(_make_config())
        session.depth = 15
        found = False
        for _ in range(500):
            drops = session._roll_ingredient_drops()
            if "resonance_core" in drops:
                found = True
                break
        assert found, "resonance_core should drop at depth 15+"

    def test_both_can_drop_at_depth_15(self) -> None:
        """At depth 15+, both resonance_core and flux_catalyst are possible."""
        session = MiningSession(_make_config())
        session.depth = 15
        found_flux = False
        found_resonance = False
        for _ in range(1000):
            drops = session._roll_ingredient_drops()
            if "flux_catalyst" in drops:
                found_flux = True
            if "resonance_core" in drops:
                found_resonance = True
            if found_flux and found_resonance:
                break
        assert found_flux, "flux_catalyst should still drop at depth 15+"
        assert found_resonance, "resonance_core should drop at depth 15+"

    def test_drops_are_quantity_1(self) -> None:
        session = MiningSession(_make_config())
        session.depth = 15
        for _ in range(500):
            drops = session._roll_ingredient_drops()
            for qty in drops.values():
                assert qty == 1, "Ingredient drops should be 1 unit each"


class TestClickRockIngredientDrop:
    """click_rock should include ingredient drops in result."""

    def test_click_rock_at_depth_includes_ingredients(self) -> None:
        """At sufficient depth, some click results should have ingredient drops."""
        config = _make_config()
        config.base_click_power = 100.0  # Ensure one-shot breaks
        found_ingredient = False
        for seed in range(50):
            random.seed(seed)
            session = MiningSession(config)
            session.depth = 10
            for rock in session.rocks:
                if not rock.depleted:
                    success, msg, result = session.click_rock(rock.grid_x, rock.grid_y)
                    if result and result.ingredient_drops:
                        found_ingredient = True
                        break
            if found_ingredient:
                break
        assert found_ingredient, "Should find at least one ingredient drop across many attempts"


class TestPassiveDrillIngredientDrop:
    """Passive/drone results should include ingredient drops."""

    def test_passive_result_can_have_ingredients(self) -> None:
        config = _make_config()
        found_ingredient = False
        for seed in range(50):
            random.seed(seed)
            session = MiningSession(config)
            session.depth = 10
            # Pick an active rock and set it nearly done
            for rock in session.rocks:
                if not rock.depleted:
                    session.active_rock = rock
                    rock.drill_progress = 0.999
                    break
            results = session.update(50.0)  # Large dt to push past 1.0
            for result in results:
                if result.ingredient_drops:
                    found_ingredient = True
                    break
            if found_ingredient:
                break
        assert found_ingredient, "Passive drill should produce ingredient drops at depth"
