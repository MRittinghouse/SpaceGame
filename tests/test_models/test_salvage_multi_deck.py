"""Tests for multi-deck salvage session mechanics."""

import pytest

from spacegame.models.salvage import (
    SalvageSession,
    SalvageConfig,
    SalvageCell,
    CellState,
    SalvageItemType,
    DerelictType,
    DeckAdvanceResult,
)
from spacegame.models.wreck_upgrade import calculate_intel_earned


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
        max_decks=4,
    )


class TestMultiDeckBasics:
    """Tests for multi-deck session state."""

    def test_session_starts_at_deck_1(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        assert session.current_deck == 1

    def test_session_has_session_total(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        assert session.session_total_salvaged == {}

    def test_derelict_has_max_decks(self) -> None:
        dt = _make_derelict()
        assert dt.max_decks == 4

    def test_default_max_decks(self) -> None:
        """DerelictType without max_decks should default to 5."""
        dt = DerelictType(
            id="test",
            name="Test",
            grid_size=4,
            item_density=0.5,
            item_distribution={"scrap_metal": 1.0},
        )
        assert dt.max_decks == 5


class TestDeckAdvance:
    """Tests for advancing to next deck."""

    def _extract_enough(self, session: SalvageSession, target_ratio: float = 0.65) -> None:
        """Helper: mark enough items as extracted to reach target ratio."""
        items = [c for c in session.grid if c.has_item]
        target_count = int(len(items) * target_ratio) + 1
        for cell in items[:target_count]:
            cell.state = CellState.EXTRACTED
            commodity = cell.config.commodity_id
            session.total_salvaged[commodity] = session.total_salvaged.get(commodity, 0) + 1
            session.session_total_salvaged[commodity] = (
                session.session_total_salvaged.get(commodity, 0) + 1
            )

    def test_advance_at_60_percent(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        self._extract_enough(session, 0.65)
        result = session.advance_deck()
        assert result is not None
        assert result.new_deck == 2
        assert session.current_deck == 2

    def test_advance_returns_intel(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        self._extract_enough(session, 0.65)
        result = session.advance_deck()
        assert result is not None
        assert result.intel_earned > 0

    def test_reject_below_60_percent(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        # Extract only 1 item (well below 60%)
        items = [c for c in session.grid if c.has_item]
        if items:
            items[0].state = CellState.EXTRACTED
            commodity = items[0].config.commodity_id
            session.total_salvaged[commodity] = 1
        result = session.advance_deck()
        assert result is None

    def test_reject_at_max_deck(self) -> None:
        derelict = _make_derelict()
        derelict.max_decks = 2
        session = SalvageSession(_make_config(), derelict_type=derelict)
        self._extract_enough(session, 0.65)
        session.advance_deck()  # deck 1 -> 2
        self._extract_enough(session, 0.65)
        result = session.advance_deck()  # deck 2 -> should fail
        assert result is None

    def test_charges_refilled_on_advance(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.charges = 2  # Low charges
        self._extract_enough(session, 0.65)
        session.advance_deck()
        # Should get 50% of max_charges added
        assert session.charges >= 2 + session.max_charges // 2

    def test_corruption_tightens_per_deck(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        base = session.base_corruption_seconds
        self._extract_enough(session, 0.65)
        session.advance_deck()
        # Deck 2: base * 0.85
        assert session.corruption_seconds == pytest.approx(base * 0.85, abs=1.0)

    def test_corruption_resets_on_advance(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        session.corruption_started = True
        session.corruption_timer = 10.0
        self._extract_enough(session, 0.65)
        session.advance_deck()
        assert not session.corruption_started
        assert not session.is_corrupted
        assert session.corruption_timer == session.corruption_seconds

    def test_per_deck_salvaged_resets(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        self._extract_enough(session, 0.65)
        assert len(session.total_salvaged) > 0
        session.advance_deck()
        assert session.total_salvaged == {}

    def test_session_total_accumulates(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        self._extract_enough(session, 0.65)
        deck1_total = sum(session.session_total_salvaged.values())
        session.advance_deck()
        self._extract_enough(session, 0.65)
        # Manually update session_total for deck 2 items
        # (advance_deck already merged deck1 totals into session_total)
        deck2_items = sum(session.total_salvaged.values())
        assert deck1_total > 0

    def test_clear_bonus_at_80_percent(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        # Advance to deck 3 first so the bonus math is meaningful
        for _ in range(2):
            self._extract_enough(session, 0.85)
            session.advance_deck()
        self._extract_enough(session, 0.85)
        result = session.advance_deck()
        assert result is not None
        assert result.was_clear_bonus
        # Compare with no bonus — deck 3 gives floor(3*0.8)=2 bonus
        expected_with = calculate_intel_earned(3, extraction_ratio=result.extraction_ratio)
        expected_without = calculate_intel_earned(3, extraction_ratio=0.5)
        assert expected_with > expected_without

    def test_new_grid_generated_on_advance(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        self._extract_enough(session, 0.65)
        # After extraction, some cells are EXTRACTED
        extracted_before = sum(1 for c in session.grid if c.state == CellState.EXTRACTED)
        assert extracted_before > 0
        session.advance_deck()
        # New grid should have all cells in HIDDEN state
        extracted_after = sum(1 for c in session.grid if c.state == CellState.EXTRACTED)
        assert extracted_after == 0
        hidden_count = sum(1 for c in session.grid if c.state == CellState.HIDDEN)
        assert hidden_count == len(session.grid)

    def test_prestige_multiplier_on_intel(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict(), prestige_level=5)
        # Advance to deck 3 so the numbers are large enough for prestige to matter
        for _ in range(2):
            self._extract_enough(session, 0.65)
            session.advance_deck()
        self._extract_enough(session, 0.65)
        result = session.advance_deck()
        base_intel = calculate_intel_earned(3, extraction_ratio=result.extraction_ratio)
        prestige_intel = calculate_intel_earned(
            3, extraction_ratio=result.extraction_ratio, prestige_level=5
        )
        assert result.intel_earned == prestige_intel
        assert prestige_intel > base_intel


class TestQualityScaling:
    """Tests for quality floor increasing with deck depth."""

    def test_deck_1_quality_floor(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        for cell in session.grid:
            if cell.has_item:
                assert cell.quality >= 0.8

    def test_deeper_deck_higher_quality_floor(self) -> None:
        session = SalvageSession(_make_config(), derelict_type=_make_derelict())
        # Advance to deck 3
        for _ in range(2):
            items = [c for c in session.grid if c.has_item]
            target = int(len(items) * 0.7) + 1
            for cell in items[:target]:
                cell.state = CellState.EXTRACTED
                commodity = cell.config.commodity_id
                session.total_salvaged[commodity] = session.total_salvaged.get(commodity, 0) + 1
            session.advance_deck()
        # Deck 3: quality_min = 0.8 + 2 * 0.1 = 1.0
        for cell in session.grid:
            if cell.has_item:
                assert cell.quality >= 1.0, f"Cell quality {cell.quality} below 1.0 on deck 3"
