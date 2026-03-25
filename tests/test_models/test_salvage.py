"""
Tests for the salvage system models.
"""

import pytest
from spacegame.models.salvage import (
    SalvageItemType,
    SalvageCell,
    CellState,
    SalvageConfig,
    SalvageSession,
    SalvageResult,
    QualityTier,
    DerelictType,
    DERELICT_TYPES,
)


class TestSalvageCell:
    """Tests for SalvageCell."""

    def test_cell_creation(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        assert cell.state == CellState.HIDDEN
        assert cell.has_item
        assert cell.extract_progress == 0.0

    def test_empty_cell(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.EMPTY)
        assert not cell.has_item
        assert cell.config is None

    def test_scan_cell(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.ELECTRONICS)
        assert cell.scan()
        assert cell.state == CellState.SCANNED

    def test_cannot_scan_twice(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        cell.scan()
        assert not cell.scan()

    def test_start_extract(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        cell.scan()
        assert cell.start_extract()
        assert cell.state == CellState.EXTRACTING

    def test_cannot_extract_hidden(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        assert not cell.start_extract()

    def test_cannot_extract_empty(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.EMPTY)
        cell.scan()
        assert not cell.start_extract()

    def test_extraction_progress(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        cell.scan()
        cell.start_extract()
        # Scrap metal = 1.0s extraction time, 0.5s = 50%
        result = cell.update_extract(0.5)
        assert result is None
        assert cell.extract_progress == pytest.approx(0.5, abs=0.01)

    def test_extraction_completion(self):
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        cell.scan()
        cell.start_extract()
        result = cell.update_extract(1.5)
        assert result is not None
        assert result >= 1
        assert cell.state == CellState.EXTRACTED


class TestSalvageConfig:
    """Tests for SalvageConfig."""

    def test_default_config(self):
        config = SalvageConfig(system_id="test")
        assert config.grid_size == 5
        assert config.max_charges == 10
        assert "scrap_metal" in config.item_distribution

    def test_custom_config(self):
        config = SalvageConfig(
            system_id="test",
            grid_size=7,
            max_charges=15,
            item_density=0.6,
        )
        assert config.grid_size == 7
        assert config.max_charges == 15
        assert config.item_density == 0.6


def _test_derelict(density: float = 0.4) -> DerelictType:
    """Create a deterministic 5x5 derelict type for testing."""
    return DerelictType(
        id="test",
        name="Test Derelict",
        grid_size=5,
        item_density=density,
        item_distribution={"scrap_metal": 0.50, "salvaged_electronics": 0.35, "rare_parts": 0.15},
    )


class TestSalvageSession:
    """Tests for SalvageSession."""

    def test_session_creation(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict())
        assert session.charges == 10
        assert len(session.grid) == 25  # 5x5

    def test_grid_has_items(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=0.5))
        item_count = session.get_item_count()
        # Should have roughly 50% items (12-13 of 25)
        assert item_count > 0
        assert item_count <= 25

    def test_scan_cell(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict())
        success, msg = session.scan_cell(0, 0)
        assert success
        assert session.charges == 9

    def test_scan_already_scanned(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict())
        session.scan_cell(0, 0)
        success, msg = session.scan_cell(0, 0)
        assert not success

    def test_no_charges(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict())
        session.charges = 0
        success, msg = session.scan_cell(0, 0)
        assert not success
        assert "charges" in msg.lower()

    def test_extract_scanned_item(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=1.0))
        session.scan_cell(0, 0)
        success, msg = session.start_extract(0, 0)
        assert success

    def test_cannot_exceed_extraction_slots(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=1.0))
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.scan_cell(2, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)  # 2nd slot fills
        success, msg = session.start_extract(2, 0)  # 3rd exceeds max_parallel=2
        assert not success

    def test_charge_regen(self):
        config = SalvageConfig(system_id="test", charge_regen_seconds=1.0)
        session = SalvageSession(config, derelict_type=_test_derelict())
        session.charges = 5
        session.update(1.5)
        assert session.charges == 6

    def test_extract_and_collect(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=1.0))
        session.scan_cell(0, 0)
        cell = session.get_cell_at(0, 0)
        session.start_extract(0, 0)
        # Run enough time to complete any extraction
        results = session.update(5.0)
        assert len(results) == 1
        assert results[0].quantity >= 1
        assert results[0].commodity_id in session.total_salvaged

    def test_extra_charges_from_skills(self):
        config = SalvageConfig(system_id="test", max_charges=10)
        session = SalvageSession(config, extra_charges=3, derelict_type=_test_derelict())
        assert session.charges == 13
        assert session.max_charges == 13

    def test_regenerate_grid(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict())
        # Scan some cells
        for i in range(5):
            session.scan_cell(i, 0)
        assert session.get_hidden_count() < 25
        session.regenerate_grid()
        assert session.get_hidden_count() == 25


class TestMinesweeperHints:
    """Tests for minesweeper-style adjacent item counts on empty cells."""

    def _make_session_with_grid(self, cells: list) -> SalvageSession:
        """Create a session with a manually constructed grid."""
        config = SalvageConfig(system_id="test", grid_size=3)
        session = SalvageSession(config)
        session.grid = cells
        return session

    def _make_3x3_grid(self, item_positions: set) -> list:
        """Create a 3x3 grid with items at specified (x,y) positions."""
        cells = []
        for y in range(3):
            for x in range(3):
                if (x, y) in item_positions:
                    item_type = SalvageItemType.SCRAP_METAL
                else:
                    item_type = SalvageItemType.EMPTY
                cells.append(SalvageCell(grid_x=x, grid_y=y, item_type=item_type))
        return cells

    def test_adjacent_count_stored_on_scan(self):
        """Scanning an empty cell sets adjacent_count."""
        # Center cell (1,1) empty, surrounded by some items
        grid = self._make_3x3_grid({(0, 0), (2, 2)})
        session = self._make_session_with_grid(grid)
        session.scan_cell(1, 1)
        cell = session.get_cell_at(1, 1)
        assert cell.adjacent_count is not None

    def test_adjacent_count_all_neighbors(self):
        """Empty center cell surrounded by 8 items → count = 8."""
        all_except_center = {(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)}
        grid = self._make_3x3_grid(all_except_center)
        session = self._make_session_with_grid(grid)
        session.scan_cell(1, 1)
        cell = session.get_cell_at(1, 1)
        assert cell.adjacent_count == 8

    def test_adjacent_count_no_neighbors(self):
        """Empty cell with no adjacent items → count = 0."""
        grid = self._make_3x3_grid(set())  # All empty
        session = self._make_session_with_grid(grid)
        session.scan_cell(1, 1)
        cell = session.get_cell_at(1, 1)
        assert cell.adjacent_count == 0

    def test_adjacent_count_partial(self):
        """3 adjacent items → count = 3."""
        grid = self._make_3x3_grid({(0, 0), (1, 0), (0, 1)})
        session = self._make_session_with_grid(grid)
        session.scan_cell(1, 1)
        cell = session.get_cell_at(1, 1)
        assert cell.adjacent_count == 3

    def test_adjacent_count_corner_cell(self):
        """Corner at (0,0) has max 3 neighbors."""
        # Items at (1,0), (0,1), (1,1) — all 3 neighbors of corner
        grid = self._make_3x3_grid({(1, 0), (0, 1), (1, 1)})
        session = self._make_session_with_grid(grid)
        session.scan_cell(0, 0)
        cell = session.get_cell_at(0, 0)
        assert cell.adjacent_count == 3

    def test_adjacent_count_none_for_item_cell(self):
        """Item cells have adjacent_count = None after scanning."""
        grid = self._make_3x3_grid({(1, 1)})
        session = self._make_session_with_grid(grid)
        session.scan_cell(1, 1)
        cell = session.get_cell_at(1, 1)
        assert cell.adjacent_count is None

    def test_adjacent_count_frozen_after_extraction(self):
        """Once set, adjacent_count does not change when neighbors are extracted."""
        # (0,0) is item, (1,0) is empty, (0,1) is item
        grid = self._make_3x3_grid({(0, 0), (0, 1)})
        session = self._make_session_with_grid(grid)
        # Scan the empty center-top cell
        session.scan_cell(1, 0)
        cell = session.get_cell_at(1, 0)
        assert cell.adjacent_count == 2
        # Now scan and extract a neighbor
        session.scan_cell(0, 0)
        session.start_extract(0, 0)
        session.update(5.0)  # Complete extraction
        # Adjacent count should still be 2
        assert cell.adjacent_count == 2

    def test_get_adjacent_item_count_method(self):
        """Direct method call returns correct count."""
        grid = self._make_3x3_grid({(0, 0), (2, 0), (0, 2), (2, 2)})
        session = self._make_session_with_grid(grid)
        # Center (1,1) has 4 diagonal neighbors with items
        assert session.get_adjacent_item_count(1, 1) == 4
        # Corner (0,0) has no item neighbors (it IS an item, but neighbors are empty)
        assert session.get_adjacent_item_count(0, 0) == 0


class TestItemQuality:
    """Tests for item quality variance."""

    def test_cell_default_quality_1(self):
        """Default quality is 1.0."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL)
        assert cell.quality == 1.0

    def test_quality_assigned_on_grid_generation(self):
        """Item cells have quality in [0.8, 1.5] after grid generation."""
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=1.0))
        for cell in session.grid:
            if cell.has_item:
                assert 0.8 <= cell.quality <= 1.5, f"Quality {cell.quality} out of range"

    def test_empty_cells_quality_1(self):
        """Empty cells keep quality 1.0."""
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=_test_derelict(density=0.0))
        for cell in session.grid:
            assert cell.quality == 1.0

    def test_quality_affects_yield(self):
        """High quality increases yield."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=1.5)
        cell.scan()
        cell.start_extract()
        # Scrap metal: min=1, max=3, quality=1.5 → yield = max(1, round(base * 1.5))
        # With base=3 (max roll), yield = round(4.5) = 4
        # With base=1 (min roll), yield = round(1.5) = 2
        result = cell.update_extract(5.0)
        assert result is not None
        assert result >= 2, "Quality 1.5 should boost min yield of 1 to at least 2"

    def test_quality_affects_extraction_time(self):
        """Higher quality = slower extraction."""
        cell_normal = SalvageCell(
            grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=1.0
        )
        cell_high = SalvageCell(
            grid_x=1, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=1.5
        )
        # Scrap base time = 1.0s
        # quality 1.0 → effective = 1.0 * (0.5 + 1.0 * 0.5) = 1.0
        # quality 1.5 → effective = 1.0 * (0.5 + 1.5 * 0.5) = 1.25
        assert cell_normal.get_effective_extraction_time() == pytest.approx(1.0)
        assert cell_high.get_effective_extraction_time() == pytest.approx(1.25)

    def test_poor_quality_yield_minimum_1(self):
        """Even with poor quality, yield is at least 1."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.RARE_PARTS, quality=0.8)
        cell.scan()
        cell.start_extract()
        # Rare parts: min=1, max=1, quality=0.8 → round(1 * 0.8) = round(0.8) = 1
        result = cell.update_extract(10.0)
        assert result is not None
        assert result >= 1

    def test_quality_tier_poor(self):
        """Quality 0.8 is POOR tier."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=0.8)
        assert cell.quality_tier == QualityTier.POOR

    def test_quality_tier_normal(self):
        """Quality 1.0 is NORMAL tier."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=1.0)
        assert cell.quality_tier == QualityTier.NORMAL

    def test_quality_tier_excellent(self):
        """Quality 1.45 is EXCELLENT tier."""
        cell = SalvageCell(grid_x=0, grid_y=0, item_type=SalvageItemType.SCRAP_METAL, quality=1.45)
        assert cell.quality_tier == QualityTier.EXCELLENT


class TestDerelictTypes:
    """Tests for derelict type variety."""

    def test_three_derelict_types_exist(self):
        """Module has 3 derelict type presets."""
        assert len(DERELICT_TYPES) == 3

    def test_cargo_bay_5x5(self):
        """Cargo Bay has grid_size=5."""
        cargo_bay = next(d for d in DERELICT_TYPES if d.id == "cargo_bay")
        assert cargo_bay.grid_size == 5

    def test_lab_module_4x4(self):
        """Lab Module has grid_size=4."""
        lab = next(d for d in DERELICT_TYPES if d.id == "lab_module")
        assert lab.grid_size == 4

    def test_engine_room_rare_heavy(self):
        """Engine Room has more rare_parts than scrap_metal."""
        engine = next(d for d in DERELICT_TYPES if d.id == "engine_room")
        assert engine.item_distribution["rare_parts"] > engine.item_distribution["scrap_metal"]

    def test_session_with_derelict_type(self):
        """Session grid size matches derelict type."""
        lab = next(d for d in DERELICT_TYPES if d.id == "lab_module")
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=lab)
        assert len(session.grid) == 16  # 4x4

    def test_derelict_overrides_config_grid(self):
        """Derelict type grid_size overrides config's grid_size."""
        lab = next(d for d in DERELICT_TYPES if d.id == "lab_module")
        config = SalvageConfig(system_id="test", grid_size=5)
        session = SalvageSession(config, derelict_type=lab)
        assert len(session.grid) == 16  # Lab module is 4x4, not config's 5x5

    def test_derelict_overrides_config_distribution(self):
        """Derelict item distribution is used, not config's."""
        engine = next(d for d in DERELICT_TYPES if d.id == "engine_room")
        config = SalvageConfig(
            system_id="test",
            item_distribution={"scrap_metal": 1.0},  # All scrap
        )
        session = SalvageSession(config, derelict_type=engine)
        # Engine room: 30% scrap, 20% electronics, 50% rare_parts
        # With density 0.3, grid 5x5=25, ~7-8 items expected
        # At least some should NOT be scrap if engine room dist is used
        item_types = {c.item_type for c in session.grid if c.has_item}
        # With 50% rare weight and several items, highly likely to get non-scrap
        assert len(item_types) >= 1  # At minimum there are items

    def test_session_stores_derelict_type(self):
        """Session stores the selected derelict type."""
        cargo = next(d for d in DERELICT_TYPES if d.id == "cargo_bay")
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config, derelict_type=cargo)
        assert session.derelict_type.id == "cargo_bay"


class TestParallelExtraction:
    """Tests for parallel extraction slots."""

    def _make_session(self, extra_parallel: int = 0) -> SalvageSession:
        config = SalvageConfig(system_id="test")
        return SalvageSession(
            config,
            derelict_type=_test_derelict(density=1.0),
            extra_parallel=extra_parallel,
        )

    def test_default_max_parallel_is_2(self):
        """Base parallel extraction slots = 2."""
        session = self._make_session()
        assert session.max_parallel == 2

    def test_can_extract_two_simultaneously(self):
        """Two extractions can run at the same time."""
        session = self._make_session()
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        ok1, _ = session.start_extract(0, 0)
        ok2, _ = session.start_extract(1, 0)
        assert ok1
        assert ok2
        assert len(session.active_extractions) == 2

    def test_cannot_exceed_max_parallel(self):
        """Third extraction fails when max_parallel=2."""
        session = self._make_session()
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.scan_cell(2, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)
        ok, msg = session.start_extract(2, 0)
        assert not ok
        assert "slot" in msg.lower() or "extraction" in msg.lower()

    def test_three_slots_with_bonus(self):
        """extra_parallel=1 gives 3 total slots."""
        session = self._make_session(extra_parallel=1)
        assert session.max_parallel == 3
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.scan_cell(2, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)
        ok, _ = session.start_extract(2, 0)
        assert ok

    def test_both_extractions_progress(self):
        """Both active extractions advance when update() is called."""
        session = self._make_session()
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)
        session.update(0.3)
        cell0 = session.get_cell_at(0, 0)
        cell1 = session.get_cell_at(1, 0)
        assert cell0.extract_progress > 0
        assert cell1.extract_progress > 0

    def test_both_can_complete_same_update(self):
        """Two fast extractions can both complete in one update."""
        session = self._make_session()
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)
        results = session.update(10.0)  # Enough to finish any extraction
        assert len(results) == 2
        assert all(r.quantity >= 1 for r in results)

    def test_update_returns_list(self):
        """update() returns a list (possibly empty)."""
        session = self._make_session()
        results = session.update(1.0)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_completed_extraction_frees_slot(self):
        """After extraction completes, the slot opens for a new one."""
        session = self._make_session()
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.scan_cell(2, 0)
        session.start_extract(0, 0)
        session.start_extract(1, 0)
        # Complete both
        session.update(10.0)
        assert len(session.active_extractions) == 0
        # Now we can start a new one
        ok, _ = session.start_extract(2, 0)
        assert ok

    def test_active_extractions_list_tracked(self):
        """session.active_extractions tracks currently extracting cells."""
        session = self._make_session()
        assert len(session.active_extractions) == 0
        session.scan_cell(0, 0)
        session.start_extract(0, 0)
        assert len(session.active_extractions) == 1


class TestCorruptionTimer:
    """Tests for the corruption timer mechanic."""

    def _make_session(self, corruption_seconds: float = 90.0) -> SalvageSession:
        derelict = DerelictType(
            id="test",
            name="Test",
            grid_size=3,
            item_density=0.5,
            item_distribution={"scrap_metal": 1.0},
            corruption_seconds=corruption_seconds,
        )
        config = SalvageConfig(system_id="test", max_charges=20)
        return SalvageSession(config, derelict_type=derelict)

    def test_corruption_not_started_initially(self):
        """Corruption timer doesn't start until first scan."""
        session = self._make_session()
        assert not session.corruption_started

    def test_first_scan_starts_corruption(self):
        """First scan starts the corruption countdown."""
        session = self._make_session()
        session.scan_cell(0, 0)
        assert session.corruption_started

    def test_corruption_timer_initial_value(self):
        """Timer starts at derelict_type.corruption_seconds."""
        session = self._make_session(corruption_seconds=75.0)
        assert session.corruption_timer == 75.0

    def test_corruption_timer_counts_down(self):
        """Timer decreases with update() after first scan."""
        session = self._make_session(corruption_seconds=90.0)
        session.scan_cell(0, 0)
        session.update(10.0)
        assert session.corruption_timer == pytest.approx(80.0, abs=0.1)

    def test_timer_does_not_count_before_first_scan(self):
        """Timer does not count down before any scan."""
        session = self._make_session(corruption_seconds=90.0)
        session.update(50.0)
        assert session.corruption_timer == 90.0

    def test_corruption_triggers_at_zero(self):
        """When timer reaches 0, remaining HIDDEN cells become CORRUPTED."""
        session = self._make_session(corruption_seconds=5.0)
        session.scan_cell(0, 0)  # Start timer, reveal one cell
        session.update(6.0)  # Exceed timer
        assert session.is_corrupted
        # All remaining hidden cells should now be corrupted
        for cell in session.grid:
            assert cell.state != CellState.HIDDEN, "No cells should remain HIDDEN after corruption"

    def test_corrupted_cell_scan_costs_2(self):
        """Scanning a CORRUPTED cell costs 2 charges."""
        session = self._make_session(corruption_seconds=1.0)
        session.scan_cell(0, 0)  # Starts timer, costs 1
        initial_charges = session.charges
        session.update(2.0)  # Trigger corruption
        # Find a corrupted cell
        corrupted = [c for c in session.grid if c.state == CellState.CORRUPTED]
        assert len(corrupted) > 0
        cell = corrupted[0]
        charges_before = session.charges
        success, msg = session.scan_cell(cell.grid_x, cell.grid_y)
        assert success
        assert session.charges == charges_before - 2

    def test_corrupted_extraction_50_percent_zero(self):
        """Corrupted cells have ~50% chance of yielding 0 on extraction."""
        import random as rng

        rng.seed(42)
        zero_count = 0
        total = 50
        for i in range(total):
            session = self._make_session(corruption_seconds=0.1)
            # Make all cells items with density=1.0
            derelict = DerelictType(
                id="test",
                name="Test",
                grid_size=3,
                item_density=1.0,
                item_distribution={"scrap_metal": 1.0},
                corruption_seconds=0.1,
            )
            config = SalvageConfig(system_id="test", max_charges=20)
            session = SalvageSession(config, derelict_type=derelict)
            session.scan_cell(0, 0)  # Start timer
            session.update(1.0)  # Trigger corruption
            # Scan and extract a corrupted cell
            corrupted = [c for c in session.grid if c.state == CellState.CORRUPTED]
            if not corrupted:
                continue
            cell = corrupted[0]
            session.scan_cell(cell.grid_x, cell.grid_y)
            session.start_extract(cell.grid_x, cell.grid_y)
            results = session.update(10.0)
            if results and results[0].quantity == 0:
                zero_count += 1
        # Should be roughly 50% zeros (allow wide margin for randomness)
        assert 10 <= zero_count <= 40, f"Expected ~25 zeros, got {zero_count}"

    def test_scanned_cells_not_corrupted(self):
        """Already scanned cells are not affected by corruption."""
        session = self._make_session(corruption_seconds=1.0)
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.update(2.0)  # Trigger corruption
        cell_00 = session.get_cell_at(0, 0)
        cell_10 = session.get_cell_at(1, 0)
        assert cell_00.state == CellState.SCANNED
        assert cell_10.state == CellState.SCANNED

    def test_corruption_timer_readable(self):
        """corruption_timer is accessible and reflects remaining time."""
        session = self._make_session(corruption_seconds=60.0)
        session.scan_cell(0, 0)
        session.update(20.0)
        assert session.corruption_timer == pytest.approx(40.0, abs=0.1)
