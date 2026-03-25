"""Tests for schematic data system (Task 52).

Schematic data drops from salvage and provides an alternative path
to discover recipes (vs. mastery-3 prerequisite).
"""

import pytest
import random

from spacegame.models.refining import Recipe


class TestSchematicCostField:
    """Recipe model should support schematic_cost field."""

    def test_default_schematic_cost_is_zero(self) -> None:
        r = Recipe(
            id="test",
            name="Test",
            description="test",
            inputs={"a": 1},
            outputs={"b": 1},
            processing_time=5.0,
            location_ids=["nexus_prime"],
        )
        assert r.schematic_cost == 0

    def test_schematic_cost_set(self) -> None:
        r = Recipe(
            id="test",
            name="Test",
            description="test",
            inputs={"a": 1},
            outputs={"b": 1},
            processing_time=5.0,
            location_ids=["nexus_prime"],
            schematic_cost=3,
        )
        assert r.schematic_cost == 3


class TestSchematicDataCommodity:
    """schematic_data commodity should exist in data."""

    def test_schematic_data_exists(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        commodity_ids = {c.id for c in dl.get_all_commodities()}
        assert "schematic_data" in commodity_ids

    def test_schematic_data_has_zero_price(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        c = next(c for c in dl.get_all_commodities() if c.id == "schematic_data")
        assert c.base_price == 0


class TestDiscoverableRecipeSchematicCosts:
    """All discoverable recipes should have schematic_cost values."""

    def test_tier2_discoverable_cost_3(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for r in dl.recipes:
            if r.discoverable and r.tier == 2:
                assert r.schematic_cost == 3, f"{r.id} tier 2 should have schematic_cost=3"

    def test_tier3_discoverable_cost_5(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for r in dl.recipes:
            if r.discoverable and r.tier == 3:
                assert r.schematic_cost == 5, f"{r.id} tier 3 should have schematic_cost=5"

    def test_non_discoverable_cost_zero(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        for r in dl.recipes:
            if not r.discoverable:
                assert r.schematic_cost == 0, f"{r.id} non-discoverable should have cost=0"


class TestSchematicDiscoveryUI:
    """Refining view should support schematic-based recipe discovery."""

    def test_refining_view_has_schematic_click_handler(self) -> None:
        """refining_view.py must have _handle_schematic_click method."""
        import inspect
        from spacegame.views.refining_view import RefiningView

        assert hasattr(RefiningView, "_handle_schematic_click")
        source = inspect.getsource(RefiningView._handle_schematic_click)
        assert "schematic_data" in source
        assert "discover_recipe" in source

    def test_refining_view_renders_locked_recipes(self) -> None:
        """refining_view._render_recipes should render locked discoverable recipes."""
        import inspect
        from spacegame.views.refining_view import RefiningView

        source = inspect.getsource(RefiningView._render_recipes)
        assert "_locked_recipes" in source
        assert "Schematic Data" in source

    def test_refining_view_computes_locked_recipes(self) -> None:
        """refining_view.on_enter should compute _locked_recipes list."""
        import inspect
        from spacegame.views.refining_view import RefiningView

        source = inspect.getsource(RefiningView.on_enter)
        assert "_locked_recipes" in source

    def test_schematic_discovery_consumes_cargo(self) -> None:
        """_handle_schematic_click should consume schematic_data from cargo."""
        import inspect
        from spacegame.views.refining_view import RefiningView

        source = inspect.getsource(RefiningView._handle_schematic_click)
        assert "schematic_cost" in source
        assert "cargo" in source


class TestSchematicDataDrop:
    """Salvage should drop schematic_data at deck 3+ with GOOD/EXCELLENT quality."""

    def test_drop_at_deck3_good_quality(self) -> None:
        """schematic_data should drop at 12% on deck 3+ GOOD quality."""
        from spacegame.models.salvage import SalvageSession, SalvageConfig, QualityTier

        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.current_deck = 3

        # Seed for deterministic test
        drop_count = 0
        trials = 10000
        for _ in range(trials):
            drops = session._roll_salvage_ingredient_drops(QualityTier.GOOD)
            if "schematic_data" in drops:
                drop_count += 1

        # 12% rate, expect ~1200 drops in 10000 trials
        assert 900 < drop_count < 1500, f"Expected ~12% rate, got {drop_count}/{trials}"

    def test_no_drop_at_deck2(self) -> None:
        """schematic_data should NOT drop below deck 3."""
        from spacegame.models.salvage import SalvageSession, SalvageConfig, QualityTier

        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.current_deck = 2

        for _ in range(1000):
            drops = session._roll_salvage_ingredient_drops(QualityTier.GOOD)
            assert "schematic_data" not in drops

    def test_no_drop_at_poor_quality(self) -> None:
        """schematic_data should NOT drop at POOR quality even on high deck."""
        from spacegame.models.salvage import SalvageSession, SalvageConfig, QualityTier

        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.current_deck = 5

        for _ in range(1000):
            drops = session._roll_salvage_ingredient_drops(QualityTier.POOR)
            assert "schematic_data" not in drops

    def test_drop_at_excellent_quality(self) -> None:
        """schematic_data should also drop at EXCELLENT quality on deck 3+."""
        from spacegame.models.salvage import SalvageSession, SalvageConfig, QualityTier

        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.current_deck = 4

        found = False
        for _ in range(1000):
            drops = session._roll_salvage_ingredient_drops(QualityTier.EXCELLENT)
            if "schematic_data" in drops:
                found = True
                break
        assert found, "Expected schematic_data to drop at EXCELLENT quality deck 4+"
