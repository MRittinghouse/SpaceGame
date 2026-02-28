"""
Salvaging system models.

Grid-based scanning and extraction puzzle at industrial systems.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple


class SalvageItemType(Enum):
    """Types of salvageable items."""

    EMPTY = "empty"
    SCRAP_METAL = "scrap_metal"
    ELECTRONICS = "salvaged_electronics"
    RARE_PARTS = "rare_parts"


@dataclass
class SalvageItemConfig:
    """Configuration for a salvage item type."""

    item_type: SalvageItemType
    commodity_id: str
    extraction_time: float  # Seconds to extract
    min_yield: int
    max_yield: int
    color: tuple  # RGB for rendering


SALVAGE_ITEM_CONFIGS = {
    SalvageItemType.SCRAP_METAL: SalvageItemConfig(
        item_type=SalvageItemType.SCRAP_METAL,
        commodity_id="scrap_metal",
        extraction_time=1.0,
        min_yield=1,
        max_yield=3,
        color=(140, 140, 140),
    ),
    SalvageItemType.ELECTRONICS: SalvageItemConfig(
        item_type=SalvageItemType.ELECTRONICS,
        commodity_id="salvaged_electronics",
        extraction_time=2.0,
        min_yield=1,
        max_yield=2,
        color=(50, 200, 50),
    ),
    SalvageItemType.RARE_PARTS: SalvageItemConfig(
        item_type=SalvageItemType.RARE_PARTS,
        commodity_id="rare_parts",
        extraction_time=3.0,
        min_yield=1,
        max_yield=1,
        color=(220, 180, 50),
    ),
}


class CellState(Enum):
    """State of a salvage grid cell."""

    HIDDEN = "hidden"
    SCANNED = "scanned"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"


@dataclass
class SalvageCell:
    """A single cell in the salvage grid."""

    grid_x: int
    grid_y: int
    item_type: SalvageItemType
    state: CellState = CellState.HIDDEN
    extract_progress: float = 0.0  # 0.0 to 1.0

    @property
    def has_item(self) -> bool:
        return self.item_type != SalvageItemType.EMPTY

    @property
    def config(self) -> Optional[SalvageItemConfig]:
        if self.item_type == SalvageItemType.EMPTY:
            return None
        return SALVAGE_ITEM_CONFIGS[self.item_type]

    def scan(self) -> bool:
        """Reveal this cell's contents. Returns True if state changed."""
        if self.state != CellState.HIDDEN:
            return False
        self.state = CellState.SCANNED
        return True

    def start_extract(self) -> bool:
        """Start extracting item from this cell."""
        if self.state != CellState.SCANNED or not self.has_item:
            return False
        self.state = CellState.EXTRACTING
        self.extract_progress = 0.0
        return True

    def update_extract(self, dt: float, speed_bonus: float = 1.0) -> Optional[int]:
        """
        Update extraction progress.

        Returns yield amount if extraction completes, None otherwise.
        """
        if self.state != CellState.EXTRACTING or not self.config:
            return None

        extract_rate = (1.0 / self.config.extraction_time) * speed_bonus
        self.extract_progress += extract_rate * dt

        if self.extract_progress >= 1.0:
            self.extract_progress = 1.0
            self.state = CellState.EXTRACTED
            return random.randint(self.config.min_yield, self.config.max_yield)

        return None


@dataclass
class SalvageConfig:
    """Configuration for salvaging at a specific system."""

    system_id: str
    grid_size: int = 5
    max_charges: int = 10
    charge_regen_seconds: float = 5.0
    item_density: float = 0.4  # Fraction of cells with items
    item_distribution: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.item_distribution:
            self.item_distribution = {
                "scrap_metal": 0.50,
                "salvaged_electronics": 0.35,
                "rare_parts": 0.15,
            }


@dataclass
class SalvageResult:
    """Result of a salvage extraction."""

    commodity_id: str
    quantity: int
    item_type: SalvageItemType


class SalvageSession:
    """
    Active salvage session with scanning and extraction.

    Manages the derelict hull grid, scan charges, and extraction.
    """

    def __init__(
        self, config: SalvageConfig, extract_speed_bonus: float = 1.0, extra_charges: int = 0
    ):
        """
        Initialize salvage session.

        Args:
            config: Salvage configuration for current system
            extract_speed_bonus: Skill-based extraction speed multiplier
            extra_charges: Additional scan charges from skills
        """
        self.config = config
        self.extract_speed_bonus = extract_speed_bonus
        self.charges = config.max_charges + extra_charges
        self.max_charges = config.max_charges + extra_charges
        self.charge_regen_timer: float = 0.0
        self.charge_regen_rate: float = config.charge_regen_seconds
        self.grid: List[SalvageCell] = []
        self.active_cell: Optional[SalvageCell] = None
        self.total_salvaged: Dict[str, int] = {}
        self._generate_grid()

    def _generate_grid(self) -> None:
        """Generate the salvage grid with hidden items."""
        self.grid.clear()
        size = self.config.grid_size
        total_cells = size * size
        item_count = int(total_cells * self.config.item_density)

        # Determine which cells have items
        all_positions = [(x, y) for x in range(size) for y in range(size)]
        item_positions = set()
        if item_count > 0:
            chosen = random.sample(all_positions, min(item_count, total_cells))
            item_positions = set(chosen)

        # Build weighted item type list
        item_types = []
        weights = []
        for type_name, weight in self.config.item_distribution.items():
            for sit in SalvageItemType:
                if sit.value == type_name:
                    item_types.append(sit)
                    weights.append(weight)
                    break

        if not item_types:
            item_types = [SalvageItemType.SCRAP_METAL]
            weights = [1.0]

        for y in range(size):
            for x in range(size):
                if (x, y) in item_positions:
                    item_type = random.choices(item_types, weights=weights, k=1)[0]
                else:
                    item_type = SalvageItemType.EMPTY
                self.grid.append(
                    SalvageCell(
                        grid_x=x,
                        grid_y=y,
                        item_type=item_type,
                    )
                )

    def get_cell_at(self, grid_x: int, grid_y: int) -> Optional[SalvageCell]:
        """Get cell at grid position."""
        for cell in self.grid:
            if cell.grid_x == grid_x and cell.grid_y == grid_y:
                return cell
        return None

    def scan_cell(self, grid_x: int, grid_y: int) -> Tuple[bool, str]:
        """
        Scan a cell to reveal its contents.

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Tuple of (success, message)
        """
        cell = self.get_cell_at(grid_x, grid_y)
        if cell is None:
            return (False, "Invalid position")

        if cell.state != CellState.HIDDEN:
            return (False, "Cell already scanned")

        if self.charges <= 0:
            return (False, "No scan charges remaining")

        self.charges -= 1
        cell.scan()

        if cell.has_item:
            return (True, f"Found: {cell.item_type.value.replace('_', ' ').title()}")
        else:
            return (True, "Empty - nothing here")

    def start_extract(self, grid_x: int, grid_y: int) -> Tuple[bool, str]:
        """
        Start extracting an item from a scanned cell.

        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate

        Returns:
            Tuple of (success, message)
        """
        cell = self.get_cell_at(grid_x, grid_y)
        if cell is None:
            return (False, "Invalid position")

        if self.active_cell and self.active_cell.state == CellState.EXTRACTING:
            return (False, "Already extracting another item")

        if cell.state != CellState.SCANNED:
            return (False, "Cell must be scanned first")

        if not cell.has_item:
            return (False, "No item to extract")

        cell.start_extract()
        self.active_cell = cell
        return (True, f"Extracting {cell.item_type.value.replace('_', ' ')}...")

    def update(self, dt: float) -> Optional[SalvageResult]:
        """
        Update salvage session (charge regen, extraction progress).

        Args:
            dt: Delta time in seconds

        Returns:
            SalvageResult if extraction completed, None otherwise
        """
        result = None

        # Update active extraction
        if self.active_cell and self.active_cell.state == CellState.EXTRACTING:
            yield_amount = self.active_cell.update_extract(dt, self.extract_speed_bonus)
            if yield_amount is not None:
                commodity_id = self.active_cell.config.commodity_id
                result = SalvageResult(
                    commodity_id=commodity_id,
                    quantity=yield_amount,
                    item_type=self.active_cell.item_type,
                )
                self.total_salvaged[commodity_id] = (
                    self.total_salvaged.get(commodity_id, 0) + yield_amount
                )
                self.active_cell = None

        # Regenerate charges
        if self.charges < self.max_charges:
            self.charge_regen_timer += dt
            if self.charge_regen_timer >= self.charge_regen_rate:
                self.charge_regen_timer -= self.charge_regen_rate
                self.charges = min(self.charges + 1, self.max_charges)

        return result

    def get_hidden_count(self) -> int:
        """Get count of cells not yet scanned."""
        return sum(1 for c in self.grid if c.state == CellState.HIDDEN)

    def get_item_count(self) -> int:
        """Get count of cells that contain items (regardless of state)."""
        return sum(1 for c in self.grid if c.has_item)

    def get_extractable_count(self) -> int:
        """Get count of scanned cells with items ready to extract."""
        return sum(1 for c in self.grid if c.state == CellState.SCANNED and c.has_item)

    def regenerate_grid(self) -> None:
        """Regenerate the salvage grid (between sessions)."""
        self._generate_grid()
        self.active_cell = None
