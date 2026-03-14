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


class QualityTier(Enum):
    """Visual quality tier for salvage items."""

    POOR = "poor"  # 0.80 - 0.99
    NORMAL = "normal"  # 1.00 - 1.19
    GOOD = "good"  # 1.20 - 1.39
    EXCELLENT = "excellent"  # 1.40 - 1.50


class CellState(Enum):
    """State of a salvage grid cell."""

    HIDDEN = "hidden"
    SCANNED = "scanned"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    CORRUPTED = "corrupted"


@dataclass
class SalvageCell:
    """A single cell in the salvage grid."""

    grid_x: int
    grid_y: int
    item_type: SalvageItemType
    state: CellState = CellState.HIDDEN
    extract_progress: float = 0.0  # 0.0 to 1.0
    adjacent_count: Optional[int] = None  # Set on scan for empty cells
    quality: float = 1.0  # Quality modifier [0.8, 1.5]
    corrupted: bool = False  # True if cell was corrupted before scanning

    @property
    def has_item(self) -> bool:
        return self.item_type != SalvageItemType.EMPTY

    @property
    def config(self) -> Optional[SalvageItemConfig]:
        if self.item_type == SalvageItemType.EMPTY:
            return None
        return SALVAGE_ITEM_CONFIGS[self.item_type]

    @property
    def quality_tier(self) -> QualityTier:
        """Get the display quality tier."""
        if self.quality < 1.0:
            return QualityTier.POOR
        if self.quality < 1.2:
            return QualityTier.NORMAL
        if self.quality < 1.4:
            return QualityTier.GOOD
        return QualityTier.EXCELLENT

    def get_effective_extraction_time(self) -> float:
        """Extraction time scaled by quality (higher quality = slower)."""
        if not self.config:
            return 0.0
        return self.config.extraction_time * (0.5 + self.quality * 0.5)

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

        effective_time = self.get_effective_extraction_time()
        extract_rate = (1.0 / effective_time) * speed_bonus
        self.extract_progress += extract_rate * dt

        if self.extract_progress >= 1.0:
            self.extract_progress = 1.0
            self.state = CellState.EXTRACTED
            if self.corrupted and random.random() < 0.5:
                return 0
            base_yield = random.randint(self.config.min_yield, self.config.max_yield)
            return max(1, round(base_yield * self.quality))

        return None


@dataclass
class DerelictType:
    """A type of derelict hull to salvage."""

    id: str
    name: str
    grid_size: int
    item_density: float
    item_distribution: Dict[str, float]
    corruption_seconds: float = 90.0


DERELICT_TYPES: List[DerelictType] = [
    DerelictType(
        id="cargo_bay",
        name="Cargo Bay",
        grid_size=5,
        item_density=0.50,
        item_distribution={"scrap_metal": 0.60, "salvaged_electronics": 0.30, "rare_parts": 0.10},
        corruption_seconds=90.0,
    ),
    DerelictType(
        id="lab_module",
        name="Lab Module",
        grid_size=4,
        item_density=0.45,
        item_distribution={"scrap_metal": 0.20, "salvaged_electronics": 0.50, "rare_parts": 0.30},
        corruption_seconds=75.0,
    ),
    DerelictType(
        id="engine_room",
        name="Engine Room",
        grid_size=5,
        item_density=0.30,
        item_distribution={"scrap_metal": 0.30, "salvaged_electronics": 0.20, "rare_parts": 0.50},
        corruption_seconds=100.0,
    ),
]


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
    corrupted: bool = False


class SalvageSession:
    """
    Active salvage session with scanning and extraction.

    Manages the derelict hull grid, scan charges, and extraction.
    """

    def __init__(
        self,
        config: SalvageConfig,
        extract_speed_bonus: float = 1.0,
        extra_charges: int = 0,
        derelict_type: Optional[DerelictType] = None,
        extra_parallel: int = 0,
    ):
        """
        Initialize salvage session.

        Args:
            config: Salvage configuration for current system
            extract_speed_bonus: Skill-based extraction speed multiplier
            extra_charges: Additional scan charges from skills
            derelict_type: Type of derelict hull (random if None)
            extra_parallel: Additional parallel extraction slots from skills
        """
        self.config = config
        self.derelict_type = derelict_type or random.choice(DERELICT_TYPES)
        self.extract_speed_bonus = extract_speed_bonus
        self.charges = config.max_charges + extra_charges
        self.max_charges = config.max_charges + extra_charges
        self.charge_regen_timer: float = 0.0
        self.charge_regen_rate: float = config.charge_regen_seconds
        self.max_parallel: int = 2 + extra_parallel
        self.corruption_seconds: float = self.derelict_type.corruption_seconds
        self.corruption_timer: float = self.corruption_seconds
        self.corruption_started: bool = False
        self.is_corrupted: bool = False
        self.grid: List[SalvageCell] = []
        self.active_extractions: List[SalvageCell] = []
        self.total_salvaged: Dict[str, int] = {}
        self._generate_grid()

    def _generate_grid(self) -> None:
        """Generate the salvage grid with hidden items."""
        self.grid.clear()
        dt = self.derelict_type
        size = dt.grid_size
        total_cells = size * size
        item_count = int(total_cells * dt.item_density)

        # Determine which cells have items
        all_positions = [(x, y) for x in range(size) for y in range(size)]
        item_positions = set()
        if item_count > 0:
            chosen = random.sample(all_positions, min(item_count, total_cells))
            item_positions = set(chosen)

        # Build weighted item type list from derelict type distribution
        item_types = []
        weights = []
        for type_name, weight in dt.item_distribution.items():
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
                    quality = round(random.uniform(0.8, 1.5), 2)
                else:
                    item_type = SalvageItemType.EMPTY
                    quality = 1.0
                self.grid.append(
                    SalvageCell(
                        grid_x=x,
                        grid_y=y,
                        item_type=item_type,
                        quality=quality,
                    )
                )

    def get_cell_at(self, grid_x: int, grid_y: int) -> Optional[SalvageCell]:
        """Get cell at grid position."""
        for cell in self.grid:
            if cell.grid_x == grid_x and cell.grid_y == grid_y:
                return cell
        return None

    def get_adjacent_item_count(self, grid_x: int, grid_y: int) -> int:
        """Count items in 8 neighbors of the given cell."""
        count = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbor = self.get_cell_at(grid_x + dx, grid_y + dy)
                if neighbor and neighbor.has_item:
                    count += 1
        return count

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

        if cell.state == CellState.CORRUPTED:
            # Corrupted cells cost 2 charges to scan
            if self.charges < 2:
                return (False, "Need 2 charges for corrupted cell")
            self.charges -= 2
            cell.state = CellState.SCANNED
            if cell.has_item:
                return (True, f"Found: {cell.item_type.value.replace('_', ' ').title()}")
            else:
                cell.adjacent_count = self.get_adjacent_item_count(grid_x, grid_y)
                return (True, "Empty - nothing here")

        if cell.state != CellState.HIDDEN:
            return (False, "Cell already scanned")

        if self.charges <= 0:
            return (False, "No scan charges remaining")

        self.charges -= 1
        cell.scan()

        if not self.corruption_started:
            self.corruption_started = True

        if cell.has_item:
            return (True, f"Found: {cell.item_type.value.replace('_', ' ').title()}")
        else:
            cell.adjacent_count = self.get_adjacent_item_count(grid_x, grid_y)
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

        if len(self.active_extractions) >= self.max_parallel:
            return (False, f"All {self.max_parallel} extraction slots in use")

        if cell.state != CellState.SCANNED:
            return (False, "Cell must be scanned first")

        if not cell.has_item:
            return (False, "No item to extract")

        cell.start_extract()
        self.active_extractions.append(cell)
        return (True, f"Extracting {cell.item_type.value.replace('_', ' ')}...")

    def update(self, dt: float) -> List[SalvageResult]:
        """
        Update salvage session (charge regen, extraction progress).

        Args:
            dt: Delta time in seconds

        Returns:
            List of completed SalvageResults (may be empty).
        """
        results: List[SalvageResult] = []
        completed: List[SalvageCell] = []

        # Update all active extractions
        for cell in self.active_extractions:
            if cell.state == CellState.EXTRACTING:
                yield_amount = cell.update_extract(dt, self.extract_speed_bonus)
                if yield_amount is not None:
                    commodity_id = cell.config.commodity_id
                    results.append(
                        SalvageResult(
                            commodity_id=commodity_id,
                            quantity=yield_amount,
                            item_type=cell.item_type,
                            corrupted=cell.corrupted,
                        )
                    )
                    self.total_salvaged[commodity_id] = (
                        self.total_salvaged.get(commodity_id, 0) + yield_amount
                    )
                    completed.append(cell)

        for cell in completed:
            self.active_extractions.remove(cell)

        # Corruption countdown
        if self.corruption_started and not self.is_corrupted:
            self.corruption_timer -= dt
            if self.corruption_timer <= 0:
                self.corruption_timer = 0
                self.is_corrupted = True
                self._apply_corruption()

        # Regenerate charges
        if self.charges < self.max_charges:
            self.charge_regen_timer += dt
            if self.charge_regen_timer >= self.charge_regen_rate:
                self.charge_regen_timer -= self.charge_regen_rate
                self.charges = min(self.charges + 1, self.max_charges)

        return results

    def _apply_corruption(self) -> None:
        """Mark all remaining HIDDEN cells as CORRUPTED."""
        for cell in self.grid:
            if cell.state == CellState.HIDDEN:
                cell.state = CellState.CORRUPTED
                cell.corrupted = True

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
        self.active_extractions.clear()
