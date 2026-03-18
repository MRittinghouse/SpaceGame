"""Tests for salvage ingredient drops (charged_filament, signal_fragment)."""

import pytest
import random

from spacegame.models.salvage import (
    SalvageSession,
    SalvageConfig,
    SalvageResult,
    SalvageCell,
    SalvageItemType,
    CellState,
    QualityTier,
    DerelictType,
)


def _make_config() -> SalvageConfig:
    return SalvageConfig(
        system_id="forgeworks",
        grid_size=4,
        max_charges=10,
        charge_regen_seconds=5.0,
    )


def _make_derelict() -> DerelictType:
    return DerelictType(
        id="cargo_bay",
        name="Cargo Bay",
        grid_size=4,
        item_density=0.50,
        item_distribution={"scrap_metal": 0.60, "salvaged_electronics": 0.30, "rare_parts": 0.10},
        corruption_seconds=90.0,
        max_decks=5,
    )


class TestSalvageResultIngredients:
    """SalvageResult should carry optional ingredient drops."""

    def test_default_no_ingredients(self) -> None:
        result = SalvageResult(
            commodity_id="scrap_metal", quantity=3,
            item_type=SalvageItemType.SCRAP_METAL,
        )
        assert result.ingredient_drops == {}

    def test_with_ingredients(self) -> None:
        result = SalvageResult(
            commodity_id="scrap_metal", quantity=3,
            item_type=SalvageItemType.SCRAP_METAL,
            ingredient_drops={"charged_filament": 1},
        )
        assert result.ingredient_drops == {"charged_filament": 1}


class TestIngredientDropRolling:
    """SalvageSession._roll_salvage_ingredient_drops() quality/deck logic."""

    def test_no_drops_on_poor_quality_deck_1(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        # Deck 1, poor quality — no drops expected
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.POOR)
            assert not drops, "No drops on poor quality deck 1"

    def test_charged_filament_on_excellent(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        found = False
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.EXCELLENT)
            if "charged_filament" in drops:
                found = True
                break
        assert found, "charged_filament should drop on EXCELLENT quality"

    def test_no_charged_filament_on_normal(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.NORMAL)
            assert "charged_filament" not in drops, "charged_filament needs EXCELLENT"

    def test_signal_fragment_on_deck_4(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.current_deck = 4
        found = False
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.NORMAL)
            if "signal_fragment" in drops:
                found = True
                break
        assert found, "signal_fragment should drop on deck 4+"

    def test_no_signal_fragment_on_deck_3(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.current_deck = 3
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.NORMAL)
            assert "signal_fragment" not in drops, "signal_fragment needs deck 4+"

    def test_both_can_drop_on_excellent_deck_4(self) -> None:
        """At deck 4+ with EXCELLENT quality, both ingredients can drop."""
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.current_deck = 4
        found_filament = False
        found_fragment = False
        for _ in range(500):
            drops = session._roll_salvage_ingredient_drops(QualityTier.EXCELLENT)
            if "charged_filament" in drops:
                found_filament = True
            if "signal_fragment" in drops:
                found_fragment = True
            if found_filament and found_fragment:
                break
        assert found_filament, "charged_filament should drop on EXCELLENT at deck 4+"
        assert found_fragment, "signal_fragment should drop at deck 4+"

    def test_drops_are_quantity_1(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.current_deck = 4
        for _ in range(200):
            drops = session._roll_salvage_ingredient_drops(QualityTier.EXCELLENT)
            for qty in drops.values():
                assert qty == 1, "Ingredient drops should be 1 unit each"


class TestExtractionIngredientDrop:
    """Extraction results should include ingredient drops when conditions met."""

    def test_extraction_result_has_ingredients_field(self) -> None:
        """Results from session.update() should include ingredient_drops."""
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        # Find an item cell and start extracting
        item_cells = [c for c in session.grid if c.has_item]
        assert len(item_cells) > 0
        cell = item_cells[0]
        cell.state = CellState.EXTRACTING
        cell.extract_progress = 0.99  # Nearly done
        session.active_extractions.append(cell)

        results = session.update(10.0)  # Large dt to finish
        for result in results:
            assert hasattr(result, "ingredient_drops")
