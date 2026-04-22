"""One-shot tool: assign targetable_subsystems to each enemy template.

Rule set (Combat §11.2):

Tier by hull:
  - Regular  (hull < 150):  2 subsystems
  - Mid-boss (hull 150-299): 3 subsystems
  - Big boss (hull >= 300):  4 subsystems (cockpit added as risk target)

Archetype picks (ordered — first is the "signature" subsystem):
  - aggressive  : weapon_array, engine, reactor, cockpit
  - defensive   : shield_generator, reactor, weapon_array, cockpit
  - evasive     : engine, sensor_array, weapon_array, cockpit
  - cowardly    : engine, sensor_array, weapon_array, cockpit

Known legendary/named bosses get 4 regardless of hull if they fall under 300.
"""

from __future__ import annotations

import json
from pathlib import Path

ARCHETYPE_ORDER = {
    "aggressive": ["weapon_array", "engine", "reactor", "cockpit"],
    "defensive": ["shield_generator", "reactor", "weapon_array", "cockpit"],
    "evasive": ["engine", "sensor_array", "weapon_array", "cockpit"],
    "cowardly": ["engine", "sensor_array", "weapon_array", "cockpit"],
}

LEGENDARY_IDS = {
    "corsair_king",
    "iron_maw",
    "the_collector",
    "void_leviathan",
    "ledger_phantom",
    "pirate_lord",
    "reach_dreadnought",
    "union_behemoth",
}


def count_for(enemy: dict) -> int:
    hull = int(enemy.get("hull", 0))
    if enemy["id"] in LEGENDARY_IDS:
        return 4
    if hull >= 300:
        return 4
    if hull >= 150:
        return 3
    return 2


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "data" / "combat" / "enemies.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    templates = data["enemy_templates"]
    for e in templates:
        if "targetable_subsystems" in e:
            continue
        archetype = e.get("behavior", "aggressive")
        order = ARCHETYPE_ORDER.get(archetype, ARCHETYPE_ORDER["aggressive"])
        n = count_for(e)
        e["targetable_subsystems"] = order[:n]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(templates)} enemies")


if __name__ == "__main__":
    main()
