"""Builder discovery system — unlocking shapes and materials through gameplay.

Handles discovery chance rolls, unlock tracking, trading milestones,
and faction reputation thresholds. Each discovery source (salvage,
mining, combat, trading, faction, crew quest) has its own logic.

Part of the Shipyard Overhaul — Phase D2.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

# ============================================================================
# Trading Milestones
# ============================================================================
#
# SI-2 migration (see requirements/si2_dataclass_migration_cookbook.md):
# converted from ``list[dict]`` to ``list[TradeMilestone]``. The reward
# schema was stable (threshold, reward_type, reward_id, name), so the
# dataclass version is a 1:1 attribute-access translation.


@dataclass(frozen=True)
class TradeMilestone:
    """Schema for a cumulative-trade-profit milestone.

    Crossed milestones unlock equipment, discounts, or builder shapes
    (see :func:`check_trade_milestones`).
    """

    threshold: int
    reward_type: str  # "equipment" | "discount" | "shape"
    reward_id: str
    name: str


TRADE_MILESTONES: list[TradeMilestone] = [
    TradeMilestone(threshold=10000, reward_type="equipment", reward_id="trade_computer", name="Merchant"),
    TradeMilestone(threshold=50000, reward_type="discount", reward_id="medium_weight_20", name="Trader"),
    TradeMilestone(threshold=100000, reward_type="shape", reward_id="hull_section", name="Magnate"),
    TradeMilestone(threshold=250000, reward_type="shape", reward_id="cargo_rack", name="Tycoon"),
    TradeMilestone(threshold=500000, reward_type="discount", reward_id="large_weight_15", name="Baron"),
    TradeMilestone(threshold=1000000, reward_type="shape", reward_id="merchants_keel", name="Mogul"),
]

# Faction rep → builder unlocks (threshold, unlocks)
FACTION_BUILDER_UNLOCKS: dict[str, list[dict]] = {
    "commerce_guild": [
        {"rep": 25, "shapes": ["guild_prow"], "materials": [], "label": "Friendly"},
        {"rep": 40, "shapes": [], "materials": ["ablative_plating"], "label": "Trusted"},
        {"rep": 50, "shapes": ["guild_stern"], "materials": [], "label": "Allied"},
    ],
    "miners_union": [
        {"rep": 25, "shapes": ["union_girder"], "materials": [], "label": "Friendly"},
        {"rep": 40, "shapes": [], "materials": ["nano_fiber"], "label": "Trusted"},
        {"rep": 50, "shapes": ["union_plating"], "materials": [], "label": "Allied"},
    ],
    "science_collective": [
        {"rep": 25, "shapes": ["collective_arc"], "materials": [], "label": "Friendly"},
        {"rep": 40, "shapes": [], "materials": ["quantum_lattice"], "label": "Trusted"},
        {"rep": 50, "shapes": ["collective_ring"], "materials": [], "label": "Allied"},
    ],
    "frontier_alliance": [
        {"rep": 25, "shapes": ["alliance_fin"], "materials": [], "label": "Friendly"},
        {"rep": 40, "shapes": [], "materials": ["bio_hull"], "label": "Trusted"},
        {"rep": 50, "shapes": ["alliance_canopy"], "materials": [], "label": "Allied"},
    ],
}

# Salvage deck type → discoverable shapes
SALVAGE_DISCOVERIES: dict[str, list[str]] = {
    "cargo": ["cargo_rack", "hull_plank"],
    "engine": ["thruster_nacelle", "swept_wing"],
    "lab": ["sensor_dome", "organic_panel"],
    "bridge": ["curved_bow", "stealth_wedge"],
}

# Mining system → discoverable shapes/materials
MINING_DISCOVERIES: dict[str, list[dict]] = {
    "breakstone": [
        {"type": "shape", "id": "union_girder"},
        {"type": "material", "id": "heavy_armor"},
    ],
    "iron_depths": [
        {"type": "shape", "id": "reinforced_bulkhead"},
        {"type": "shape", "id": "armored_prow"},
        {"type": "material", "id": "nano_fiber"},
    ],
}

# Boss → trophy drops
BOSS_TROPHY_SHAPES: dict[str, str] = {
    "corsair_king": "pirate_cutlass_fin",
    "guild_arbiter": "corporate_bulwark",
    "iron_maw": "forgeborn_plate",
    "ledger_phantom": "phantom_shroud",
    "the_collector": "collectors_crest",
    "void_leviathan": "void_chitin",
    "rogue_ai_vessel": "ai_logic_core",
}

BOSS_TROPHY_MATERIALS: dict[str, str] = {
    "iron_maw": "forgeborn_steel",  # Not in base materials yet — future
    "void_leviathan": "void_chitin_material",  # Not in base materials yet — future
}

# Legendary module drops from the 5 superbosses (Emerald/Ruby weapon tier)
BOSS_TROPHY_MODULES: dict[str, str] = {
    "corsair_king": "legendary_kings_repeater",
    "void_leviathan": "legendary_void_maw_reactor",
    "iron_maw": "legendary_forgeborn_bulwark",
    "the_collector": "legendary_collection_engine",
    "ledger_phantom": "legendary_phantom_shroud",
}

# ============================================================================
# Module Blueprint Unlock Tables (Shipbuilder Upgrade Phase 8)
# ============================================================================

# Faction → module blueprint unlocks at reputation thresholds
FACTION_MODULE_UNLOCKS: dict[str, list[dict]] = {
    "commerce_guild": [
        {"rep": 25, "modules": ["split_engine_talon", "twin_link_talon"], "label": "Friendly"},
        {"rep": 40, "modules": ["quad_mount_foundry"], "label": "Trusted"},
        {"rep": 50, "modules": ["brig_rk"], "label": "Allied"},
    ],
    "miners_union": [
        {
            "rep": 25,
            "modules": ["wide_array_foundry", "reinforced_bulkhead_4x2"],
            "label": "Friendly",
        },
        {"rep": 40, "modules": ["heavy_projector_foundry"], "label": "Trusted"},
        {"rep": 50, "modules": ["capital_engine_foundry"], "label": "Allied"},
    ],
    "science_collective": [
        {"rep": 25, "modules": ["whisper_drive_sable", "compact_node_sable"], "label": "Friendly"},
        {"rep": 40, "modules": ["phase_barrier_sable", "concealed_bay_sable"], "label": "Trusted"},
        {"rep": 50, "modules": ["ew_suite_sable", "micro_reactor_sable"], "label": "Allied"},
    ],
    "frontier_alliance": [
        {
            "rep": 25,
            "modules": ["efficient_drive_meridian", "shield_dome_meridian"],
            "label": "Friendly",
        },
        {
            "rep": 40,
            "modules": ["tall_tower_meridian", "officer_cabin_meridian"],
            "label": "Trusted",
        },
        {
            "rep": 50,
            "modules": ["luxury_cabin_meridian", "ion_array_meridian", "science_lab_meridian"],
            "label": "Allied",
        },
    ],
}


def check_faction_module_unlocks(
    faction_id: str,
    current_rep: int,
    already_unlocked: set[str],
) -> list[dict]:
    """Check if faction reputation has unlocked any new module blueprints.

    Args:
        faction_id: Faction to check.
        current_rep: Player's current reputation with that faction.
        already_unlocked: Set of already-unlocked module IDs.

    Returns:
        List of dicts with 'module_id' and 'label' for newly unlocked modules.
    """
    tiers = FACTION_MODULE_UNLOCKS.get(faction_id, [])
    newly_unlocked = []
    for tier in tiers:
        if current_rep >= tier["rep"]:
            for mod_id in tier["modules"]:
                if mod_id not in already_unlocked:
                    newly_unlocked.append(
                        {
                            "module_id": mod_id,
                            "label": tier["label"],
                            "faction": faction_id,
                        }
                    )
    return newly_unlocked


# ============================================================================
# Discovery Functions
# ============================================================================


def check_salvage_discovery(
    deck_type: str,
    salvage_skill_level: int,
    already_unlocked: set[str],
    seed: Optional[int] = None,
) -> Optional[str]:
    """Roll for shape discovery after a salvage run.

    Args:
        deck_type: Type of salvage deck ("cargo", "engine", "lab", "bridge").
        salvage_skill_level: Player's salvage skill level (0-5).
        already_unlocked: Set of already-unlocked shape IDs.
        seed: Optional RNG seed for deterministic testing.

    Returns:
        Shape ID discovered, or None.
    """
    base_chance = 0.05  # 5% base
    skill_bonus = salvage_skill_level * 0.02  # +2% per level
    total_chance = base_chance + skill_bonus

    rng = random.Random(seed) if seed is not None else random
    if rng.random() > total_chance:
        return None

    candidates = SALVAGE_DISCOVERIES.get(deck_type, [])
    undiscovered = [s for s in candidates if s not in already_unlocked]
    if not undiscovered:
        return None

    return rng.choice(undiscovered)


def check_mining_discovery(
    system_id: str,
    depth_layer: int,
    mining_skill_level: int,
    already_unlocked_shapes: set[str],
    already_unlocked_materials: set[str],
    seed: Optional[int] = None,
) -> Optional[dict]:
    """Roll for shape/material discovery during deep mining.

    Args:
        system_id: Current system ID.
        depth_layer: Mining depth (3+ triggers discovery chance).
        mining_skill_level: Player's mining skill level.
        already_unlocked_shapes: Unlocked shape IDs.
        already_unlocked_materials: Unlocked material IDs.
        seed: Optional RNG seed.

    Returns:
        Dict with "type" ("shape"/"material") and "id", or None.
    """
    if depth_layer < 3:
        return None

    base_chance = 0.03  # 3% base
    skill_bonus = mining_skill_level * 0.02
    depth_bonus = 0.05 if depth_layer >= 5 else 0.0
    total_chance = base_chance + skill_bonus + depth_bonus

    rng = random.Random(seed) if seed is not None else random
    if rng.random() > total_chance:
        return None

    candidates = MINING_DISCOVERIES.get(system_id, [])
    undiscovered = []
    for c in candidates:
        if c["type"] == "shape" and c["id"] not in already_unlocked_shapes:
            undiscovered.append(c)
        elif c["type"] == "material" and c["id"] not in already_unlocked_materials:
            undiscovered.append(c)

    if not undiscovered:
        return None

    return rng.choice(undiscovered)


def check_combat_trophy(
    enemy_id: str,
    is_boss: bool,
    already_unlocked: set[str],
) -> Optional[str]:
    """Check if defeating an enemy awards a trophy shape.

    Boss enemies have guaranteed trophy drops on first kill.

    Args:
        enemy_id: The defeated enemy template ID.
        is_boss: Whether the enemy is a boss.
        already_unlocked: Already-unlocked shape IDs.

    Returns:
        Shape ID awarded, or None.
    """
    if not is_boss:
        return None

    trophy = BOSS_TROPHY_SHAPES.get(enemy_id)
    if trophy and trophy not in already_unlocked:
        return trophy
    return None


def check_combat_trophy_module(
    enemy_id: str,
    is_boss: bool,
    already_unlocked: set[str],
) -> Optional[str]:
    """Check if defeating a boss awards a legendary module blueprint.

    Superboss enemies drop unique legendary modules on first kill.
    These modules have effects that don't exist anywhere else.

    Args:
        enemy_id: The defeated enemy template ID.
        is_boss: Whether the enemy is a boss.
        already_unlocked: Already-unlocked module IDs.

    Returns:
        Module ID awarded, or None.
    """
    if not is_boss:
        return None

    trophy = BOSS_TROPHY_MODULES.get(enemy_id)
    if trophy and trophy not in already_unlocked:
        return trophy
    return None


def check_trade_milestones(
    current_profit: int,
    previous_profit: int,
) -> list[TradeMilestone]:
    """Check if any trading milestones were crossed.

    Args:
        current_profit: Total cumulative trade profit after this trade.
        previous_profit: Total before this trade.

    Returns:
        List of newly crossed milestones.
    """
    crossed: list[TradeMilestone] = []
    for milestone in TRADE_MILESTONES:
        if previous_profit < milestone.threshold <= current_profit:
            crossed.append(milestone)
    return crossed


def check_faction_unlocks(
    faction_id: str,
    current_rep: int,
    already_unlocked_shapes: set[str],
    already_unlocked_materials: set[str],
) -> list[dict]:
    """Check if faction reputation has unlocked new builder content.

    Args:
        faction_id: Faction to check.
        current_rep: Current reputation with this faction.
        already_unlocked_shapes: Currently unlocked shape IDs.
        already_unlocked_materials: Currently unlocked material IDs.

    Returns:
        List of newly unlocked content dicts with "shapes" and "materials" lists.
    """
    unlocks = FACTION_BUILDER_UNLOCKS.get(faction_id, [])
    newly_unlocked: list[dict] = []

    for unlock in unlocks:
        if current_rep >= unlock["rep"]:
            new_shapes = [s for s in unlock["shapes"] if s not in already_unlocked_shapes]
            new_materials = [m for m in unlock["materials"] if m not in already_unlocked_materials]
            if new_shapes or new_materials:
                newly_unlocked.append(
                    {
                        "shapes": new_shapes,
                        "materials": new_materials,
                        "label": unlock["label"],
                        "faction": faction_id,
                    }
                )

    return newly_unlocked
