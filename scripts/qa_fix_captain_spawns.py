"""QA-3: Add enemy_template_ids spawn overrides on captain-attributed encounters
so the spawned enemy ship matches the captain's signature ship.

Idempotent: if enemy_template_ids is already set on an outcome, it's left alone.
"""

from __future__ import annotations

import json
from pathlib import Path

# Mapping: encounter_id -> captain's signature ship template
# Excludes the 2 already-overridden encounters (ransom_guild_audit_01,
# shakedown_ore_holdup_01) — those are the magic compositions.
SPAWN_FIXES = {
    "ransom_pirate_corvette_01": "pirate_raider",
    "ransom_reach_collector_01": "mercenary_ace",
    "ransom_frontier_brigand_01": "frontier_gunship",
    "shakedown_food_blockade_01": "reach_bulwark",
    "shakedown_contraband_intercept_01": "smuggler",
    "shakedown_medical_strongarm_01": "mercenary_ace",
}

PRESSURE_FILE = (
    Path(__file__).parent.parent / "data" / "encounters" / "ce4_pressure.json"
)


def _patch_outcome(outcome: dict, ship: str) -> bool:
    """Add ship to outcome.enemy_template_ids if it leads to combat
    and doesn't already have one. Returns True if changed."""
    if not outcome.get("leads_to_combat"):
        return False
    existing = outcome.get("enemy_template_ids", [])
    if existing:
        return False
    outcome["enemy_template_ids"] = [ship]
    return True


def main() -> int:
    data = json.loads(PRESSURE_FILE.read_text(encoding="utf-8"))
    fixed = 0
    for enc in data["encounters"]:
        if enc["id"] not in SPAWN_FIXES:
            continue
        ship = SPAWN_FIXES[enc["id"]]
        for choice in enc.get("choices", []):
            if "outcome" in choice and _patch_outcome(choice["outcome"], ship):
                fixed += 1
            if "failure_outcome" in choice and _patch_outcome(
                choice["failure_outcome"], ship
            ):
                fixed += 1
    PRESSURE_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Patched {fixed} combat outcomes with captain-aligned enemy spawns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
