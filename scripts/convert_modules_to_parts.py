"""Convert modules.json entries to the new parts.json format.

Filters out cockpit and structural categories, maps remaining modules
to ShipPart schema with appropriate slot_type and min_size inference.
"""

import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MODULES_PATH = BASE / "data" / "ships" / "modules.json"
PARTS_PATH = BASE / "data" / "ships" / "parts.json"

# Categories to skip
SKIP_CATEGORIES = {"cockpit", "structural"}

# category -> slot_type mapping
CATEGORY_TO_SLOT = {
    "weapon": "weapon",
    "shield": "defense",
    "engine": "engine",
    "cargo": "cargo",
    "crew": "crew_quarters",
    "reactor": "reactor",
    "utility": "utility",
}

# weapon_size values that map directly
WEAPON_SIZE_MAP = {"small", "medium", "large"}


def count_pixels(pixel_mask_compact: list[str]) -> int:
    """Count non-dot characters in a pixel mask."""
    total = 0
    for row in pixel_mask_compact:
        for ch in row:
            if ch != ".":
                total += 1
    return total


def infer_min_size(module: dict) -> str:
    """Infer min_size from pixel mask or weapon_size."""
    # For weapons, prefer weapon_size from provides if available
    if module.get("category") == "weapon":
        weapon_size = module.get("provides", {}).get("weapon_size", "")
        if weapon_size in WEAPON_SIZE_MAP:
            return weapon_size

    pixels = count_pixels(module.get("pixel_mask_compact", []))
    if pixels <= 6:
        return "small"
    elif pixels <= 12:
        return "medium"
    else:
        return "large"


def is_legendary(module: dict) -> bool:
    """Check if a module is legendary."""
    return "legendary" in module.get("id", "")


def convert_module(module: dict) -> dict:
    """Convert a single module dict to a part dict."""
    category = module["category"]
    slot_type = CATEGORY_TO_SLOT[category]

    description = module.get("description", "")
    if not description:
        description = module.get("discovery_flavor", "")

    return {
        "id": module["id"],
        "name": module["name"],
        "description": description,
        "slot_type": slot_type,
        "min_size": infer_min_size(module),
        "manufacturer": module.get("manufacturer", ""),
        "provides": module.get("provides", {}),
        "base_cost": module.get("base_cost", 0),
        "mark": 1,
        "weight": module.get("weight", 0.0),
        "legendary": is_legendary(module),
    }


def main() -> None:
    with open(MODULES_PATH, encoding="utf-8") as f:
        data = json.load(f)

    modules = data["modules"]
    print(f"Total modules in source: {len(modules)}")

    parts: list[dict] = []
    skip_counts: Counter[str] = Counter()
    slot_counts: Counter[str] = Counter()

    for mod in modules:
        category = mod["category"]
        if category in SKIP_CATEGORIES:
            skip_counts[category] += 1
            continue

        if category not in CATEGORY_TO_SLOT:
            skip_counts[f"unknown:{category}"] += 1
            continue

        part = convert_module(mod)
        parts.append(part)
        slot_counts[part["slot_type"]] += 1

    output = {"parts": parts}
    with open(PARTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Verify
    with open(PARTS_PATH, encoding="utf-8") as f:
        verify = json.load(f)
    print(f"\nWrote {len(verify['parts'])} parts to {PARTS_PATH}")

    # Summary
    print(f"\n=== CONVERSION SUMMARY ===")
    print(f"Converted: {len(parts)}")
    total_skipped = sum(skip_counts.values())
    print(f"Skipped:   {total_skipped}")
    for reason, count in sorted(skip_counts.items()):
        print(f"  - {reason}: {count}")

    print(f"\nBreakdown by slot_type:")
    for slot, count in sorted(slot_counts.items()):
        print(f"  {slot}: {count}")

    legendary_count = sum(1 for p in parts if p["legendary"])
    print(f"\nLegendary parts: {legendary_count}")


if __name__ == "__main__":
    main()
