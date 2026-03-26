"""Convert upgrades with combat_move data into ShipPart entries in parts.json.

Reads all upgrades from upgrades.json that have a combat_move field,
creates corresponding ShipPart entries, removes redundant mounting-point
parts from parts.json, and writes the combined result back.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPGRADES_PATH = ROOT / "data" / "ships" / "upgrades.json"
PARTS_PATH = ROOT / "data" / "ships" / "parts.json"

TIER_TO_SIZE = {1: "small", 2: "medium", 3: "large"}


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def is_mounting_point(part: dict) -> bool:
    """Check if a part is a redundant mounting point.

    Mounting points only have slot_type and weapon_size in provides,
    with no actual stat contributions.
    """
    provides = part.get("provides", {})
    return set(provides.keys()) == {"slot_type", "weapon_size"}


def build_provides(upgrade: dict) -> dict:
    """Build provides dict from upgrade bonus info."""
    provides: dict = {}
    bonus_type = upgrade.get("bonus_type", "")
    bonus_value = upgrade.get("bonus_value", 0.0)
    if bonus_type and bonus_value:
        provides[bonus_type] = bonus_value
    return provides


def convert_upgrade_to_part(upgrade: dict) -> dict:
    """Convert a single upgrade with combat_move into a ShipPart entry."""
    tier = upgrade.get("tier", 1)
    min_size = TIER_TO_SIZE.get(tier, "small")

    return {
        "id": upgrade["id"],
        "name": upgrade["name"],
        "description": upgrade["description"],
        "slot_type": upgrade["slot_type"],
        "min_size": min_size,
        "manufacturer": "",
        "provides": build_provides(upgrade),
        "base_cost": upgrade.get("price", 0),
        "mark": 1,
        "weight": 0.0,
        "legendary": upgrade.get("legendary", False),
        "combat_move": upgrade["combat_move"],
    }


def main() -> None:
    # Load data
    upgrades_data = load_json(UPGRADES_PATH)
    parts_data = load_json(PARTS_PATH)

    upgrades = upgrades_data["upgrades"]
    existing_parts = parts_data["parts"]

    # Find upgrades with combat_move
    combat_upgrades = [u for u in upgrades if "combat_move" in u]
    print(f"Found {len(combat_upgrades)} upgrades with combat_move")

    # Convert to parts
    new_parts = [convert_upgrade_to_part(u) for u in combat_upgrades]
    new_part_ids = {p["id"] for p in new_parts}
    print(f"Created {len(new_parts)} new part entries")

    # Identify and remove mounting points
    mounting_points = [p for p in existing_parts if is_mounting_point(p)]
    print(f"Found {len(mounting_points)} mounting-point parts to remove:")
    for mp in mounting_points:
        print(f"  - {mp['id']}: {mp['provides']}")

    # Filter: keep parts that are NOT mounting points and NOT duplicates of new parts
    kept_parts = [
        p
        for p in existing_parts
        if not is_mounting_point(p) and p["id"] not in new_part_ids
    ]
    print(f"Kept {len(kept_parts)} existing parts")

    # Combine
    final_parts = kept_parts + new_parts
    print(f"Total parts: {len(final_parts)}")

    # Write back
    parts_data["parts"] = final_parts
    save_json(PARTS_PATH, parts_data)
    print(f"Wrote {len(final_parts)} parts to {PARTS_PATH}")

    # Verify: try loading with ShipPart.from_dict
    sys.path.insert(0, str(ROOT))
    from spacegame.models.ship_part import ShipPart

    reloaded = load_json(PARTS_PATH)
    loaded_parts = []
    for entry in reloaded["parts"]:
        part = ShipPart.from_dict(entry)
        loaded_parts.append(part)

    print(f"\nVerification: successfully loaded {len(loaded_parts)} ShipPart objects")

    # Count by category
    with_combat = sum(1 for p in loaded_parts if p.combat_move is not None)
    print(f"  Parts with combat_move: {with_combat}")
    print(f"  Parts without combat_move: {len(loaded_parts) - with_combat}")

    # Summary
    print("\n=== SUMMARY ===")
    print(f"Upgrade-derived parts added: {len(new_parts)}")
    print(f"Mounting-point parts removed: {len(mounting_points)}")
    print(f"Total parts count: {len(final_parts)}")


if __name__ == "__main__":
    main()
