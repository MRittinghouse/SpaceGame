"""Palette management system for pixel art assets.

Provides color distance calculations, nearest-color lookup,
palette loading from JSON, and a manager for faction/domain palettes.
"""

import json
import os
from dataclasses import dataclass, field


def color_distance_sq(
    c1: tuple[int, int, int], c2: tuple[int, int, int]
) -> int:
    """Euclidean distance squared between two RGB colors.

    Args:
        c1: First color as (R, G, B).
        c2: Second color as (R, G, B).

    Returns:
        Sum of squared channel differences.
    """
    return (c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2


def nearest_palette_color(
    color: tuple[int, int, int],
    palette: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """Find the closest palette color to the given input color.

    Uses Euclidean distance in RGB space. When equidistant,
    returns the first match in palette order.

    Args:
        color: Input color as (R, G, B).
        palette: List of palette colors to match against.

    Returns:
        The nearest palette color.

    Raises:
        ValueError: If palette is empty.
    """
    if not palette:
        raise ValueError("Palette must not be empty.")

    best = palette[0]
    best_dist = color_distance_sq(color, best)
    for entry in palette[1:]:
        dist = color_distance_sq(color, entry)
        if dist < best_dist:
            best = entry
            best_dist = dist
    return best


@dataclass
class Palette:
    """A named collection of colors with string keys.

    Attributes:
        id: Unique identifier for this palette.
        name: Human-readable display name.
        colors: Mapping of color name to (R, G, B) tuple.
    """

    id: str
    name: str
    colors: dict[str, tuple[int, int, int]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Palette":
        """Create a Palette from a JSON-like dictionary.

        Args:
            data: Dict with 'id', 'name', and 'colors' keys.
                  Colors are name -> [R, G, B] lists.

        Returns:
            New Palette instance.
        """
        colors: dict[str, tuple[int, int, int]] = {}
        for name, rgb in data.get("colors", {}).items():
            colors[name] = (rgb[0], rgb[1], rgb[2])
        return cls(id=data["id"], name=data["name"], colors=colors)

    def get_color(self, name: str) -> tuple[int, int, int] | None:
        """Get a color by name.

        Args:
            name: Color name key.

        Returns:
            (R, G, B) tuple, or None if not found.
        """
        return self.colors.get(name)

    def get_all_colors(self) -> list[tuple[int, int, int]]:
        """Get all color values in this palette.

        Returns:
            List of (R, G, B) tuples.
        """
        return list(self.colors.values())

    def color_names(self) -> list[str]:
        """Get all color names in this palette.

        Returns:
            List of color name strings.
        """
        return list(self.colors.keys())


class PaletteManager:
    """Loads and provides access to palette definitions.

    Palettes are loaded from JSON files in a directory.
    Each JSON file defines one palette with id, name, and colors.
    """

    def __init__(self) -> None:
        self._palettes: dict[str, Palette] = {}

    def load_directory(self, dir_path: str) -> None:
        """Load all palette JSON files from a directory.

        Invalid or non-JSON files are skipped gracefully.

        Args:
            dir_path: Path to directory containing palette JSON files.
        """
        for filename in os.listdir(dir_path):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(dir_path, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                palette = Palette.from_dict(data)
                self._palettes[palette.id] = palette
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    def get_palette(self, palette_id: str) -> Palette | None:
        """Get a palette by ID.

        Args:
            palette_id: Palette identifier.

        Returns:
            Palette instance, or None if not found.
        """
        return self._palettes.get(palette_id)

    def get_color(
        self, palette_id: str, color_name: str
    ) -> tuple[int, int, int] | None:
        """Shorthand to get a specific color from a specific palette.

        Args:
            palette_id: Palette identifier.
            color_name: Color name within the palette.

        Returns:
            (R, G, B) tuple, or None if palette or color not found.
        """
        palette = self._palettes.get(palette_id)
        if palette is None:
            return None
        return palette.get_color(color_name)

    def get_palette_ids(self) -> list[str]:
        """Get all loaded palette IDs.

        Returns:
            List of palette ID strings.
        """
        return list(self._palettes.keys())

    def get_master_palette(self) -> list[tuple[int, int, int]]:
        """Collect all unique colors across all loaded palettes.

        Returns:
            List of unique (R, G, B) tuples.
        """
        seen: set[tuple[int, int, int]] = set()
        result: list[tuple[int, int, int]] = []
        for palette in self._palettes.values():
            for color in palette.get_all_colors():
                if color not in seen:
                    seen.add(color)
                    result.append(color)
        return result
