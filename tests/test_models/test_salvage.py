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


class TestSalvageSession:
    """Tests for SalvageSession."""

    def test_session_creation(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        assert session.charges == 10
        assert len(session.grid) == 25  # 5x5

    def test_grid_has_items(self):
        config = SalvageConfig(system_id="test", item_density=0.5)
        session = SalvageSession(config)
        item_count = session.get_item_count()
        # Should have roughly 50% items (12-13 of 25)
        assert item_count > 0
        assert item_count <= 25

    def test_scan_cell(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        success, msg = session.scan_cell(0, 0)
        assert success
        assert session.charges == 9

    def test_scan_already_scanned(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.scan_cell(0, 0)
        success, msg = session.scan_cell(0, 0)
        assert not success

    def test_no_charges(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        session.charges = 0
        success, msg = session.scan_cell(0, 0)
        assert not success
        assert "charges" in msg.lower()

    def test_extract_scanned_item(self):
        config = SalvageConfig(
            system_id="test",
            item_density=1.0,  # All cells have items
        )
        session = SalvageSession(config)
        session.scan_cell(0, 0)
        success, msg = session.start_extract(0, 0)
        assert success

    def test_cannot_extract_two(self):
        config = SalvageConfig(system_id="test", item_density=1.0)
        session = SalvageSession(config)
        session.scan_cell(0, 0)
        session.scan_cell(1, 0)
        session.start_extract(0, 0)
        success, msg = session.start_extract(1, 0)
        assert not success

    def test_charge_regen(self):
        config = SalvageConfig(system_id="test", charge_regen_seconds=1.0)
        session = SalvageSession(config)
        session.charges = 5
        session.update(1.5)
        assert session.charges == 6

    def test_extract_and_collect(self):
        config = SalvageConfig(system_id="test", item_density=1.0)
        session = SalvageSession(config)
        session.scan_cell(0, 0)
        cell = session.get_cell_at(0, 0)
        session.start_extract(0, 0)
        # Run enough time to complete any extraction
        result = session.update(5.0)
        assert result is not None
        assert result.quantity >= 1
        assert result.commodity_id in session.total_salvaged

    def test_extra_charges_from_skills(self):
        config = SalvageConfig(system_id="test", max_charges=10)
        session = SalvageSession(config, extra_charges=3)
        assert session.charges == 13
        assert session.max_charges == 13

    def test_regenerate_grid(self):
        config = SalvageConfig(system_id="test")
        session = SalvageSession(config)
        # Scan some cells
        for i in range(5):
            session.scan_cell(i, 0)
        assert session.get_hidden_count() < 25
        session.regenerate_grid()
        assert session.get_hidden_count() == 25
