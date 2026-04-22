"""Module-targeted combat damage system.

Tracks per-module HP during combat, resolves hits probabilistically
based on pixel coverage, applies category-specific disable effects
when modules are destroyed, and handles structural severing.

Part of the Shipbuilder Upgrade — Phase 9 (Combat Integration).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from spacegame.models.ship_build import ShipBuild
from spacegame.models.ship_module import ShipModule

# Module HP scales linearly with pixel count
HP_PER_MODULE_PIXEL = 5


@dataclass
class ModuleCombatState:
    """Tracks a single module's combat state."""

    module_id: str
    placed_index: int  # Index into ShipBuild.placed_slots
    max_hp: int
    current_hp: int
    disabled: bool = False
    category: str = ""

    @property
    def hp_ratio(self) -> float:
        """Current HP as a fraction of max (0.0 to 1.0)."""
        return self.current_hp / self.max_hp if self.max_hp > 0 else 0.0


# HP per grid cell for slot-based builds (slots use footprint area instead of pixel count)
HP_PER_SLOT_CELL = 8


def init_slot_combat_states(
    build: ShipBuild,
    slot_definitions: dict,
) -> list[ModuleCombatState]:
    """Initialize combat states for all placed slots in a build.

    Produces the same ModuleCombatState objects as init_module_combat_states(),
    allowing the downstream combat engine to work identically.

    Each slot's max HP = footprint_area * HP_PER_SLOT_CELL.
    The slot_def's slot_type maps to ModuleCombatState.category for
    disable effects (weapon → weapon offline, defense → shield penalty, etc).

    Args:
        build: The ship build containing placed slots.
        slot_definitions: SlotDefinition catalog keyed by ID.

    Returns:
        List of ModuleCombatState, one per placed slot.
    """
    states: list[ModuleCombatState] = []
    for i, placed_slot in enumerate(build.placed_slots):
        slot_def = slot_definitions.get(placed_slot.slot_def_id)
        if not slot_def:
            continue
        area = slot_def.footprint_w * slot_def.footprint_h
        max_hp = area * HP_PER_SLOT_CELL
        # Map slot_type to combat category for disable effects
        # "defense" → "shield" for backward compat with existing disable logic
        category = slot_def.slot_type
        if category == "defense":
            category = "shield"
        states.append(
            ModuleCombatState(
                module_id=placed_slot.slot_def_id,
                placed_index=i,
                max_hp=max_hp,
                current_hp=max_hp,
                disabled=False,
                category=category,
            )
        )
    return states


def get_slot_equipment_moves(
    build: ShipBuild,
    slot_definitions: dict,
    parts_catalog: dict,
) -> list[dict]:
    """Extract equipment slot info from placed slots for combat initialization.

    Produces the same format as get_module_equipment_slots() from ship_module.py,
    allowing build_player_combat_state() to use either path.

    Args:
        build: Ship build with placed_slots.
        slot_definitions: SlotDefinition catalog.
        parts_catalog: ShipPart catalog.

    Returns:
        List of dicts with keys: slot_idx, slot_type, equipped_part_id,
        combat_move (raw dict), mark.
    """
    result: list[dict] = []
    for i, placed_slot in enumerate(build.placed_slots):
        if not placed_slot.equipped_part_id:
            continue
        slot_def = slot_definitions.get(placed_slot.slot_def_id)
        part = parts_catalog.get(placed_slot.equipped_part_id)
        if not slot_def or not part:
            continue
        if not part.combat_move:
            continue
        result.append(
            {
                "slot_idx": i,
                "slot_type": slot_def.slot_type,
                "equipped_part_id": placed_slot.equipped_part_id,
                "combat_move": part.combat_move,
                "mark": part.mark,
            }
        )
    return result


def resolve_module_hit(
    build: ShipBuild,
    module_catalog: dict[str, ShipModule],
    states: list[ModuleCombatState],
) -> Optional[int]:
    """Determine which slot (or hull) a hit lands on.

    Uses probabilistic targeting based on combat state HP pools.
    Each slot's hit probability is proportional to its max HP.
    Hull pixels get the remaining probability.

    Args:
        build: The ship build.
        module_catalog: Module/slot catalog (kept for API compat).
        states: Current module combat states.

    Returns:
        Module state index (into states list) if a slot is hit,
        or None if hull pixels are hit.
    """
    hull_pixel_count = len(build.pixels)

    # Build weighted choices from combat states
    choices: list[Optional[int]] = []
    weights: list[int] = []
    for i, state in enumerate(states):
        if state.max_hp > 0 and not state.disabled:
            choices.append(i)
            weights.append(state.max_hp)
    if hull_pixel_count > 0:
        choices.append(None)
        weights.append(hull_pixel_count)

    if not choices:
        return None

    result = random.choices(choices, weights=weights, k=1)[0]
    return result


def apply_module_damage(
    state: ModuleCombatState,
    damage: int,
) -> tuple[str, int]:
    """Apply damage to a module's HP pool, tracking excess.

    If HP reaches 0, the module is disabled. Excess damage beyond
    the module's remaining HP is returned for propagation.

    Args:
        state: The module's combat state.
        damage: Amount of damage to apply.

    Returns:
        (message, excess_damage) tuple. excess_damage is 0 if no overkill.
    """
    if state.current_hp <= 0:
        return f"{state.module_id} already disabled", damage

    remaining_before = state.current_hp
    state.current_hp = max(0, state.current_hp - damage)
    excess = max(0, damage - remaining_before)

    if state.current_hp <= 0:
        state.disabled = True
        cat_name = state.category.replace("_", " ").title()
        return f"{cat_name} module disabled! ({state.module_id})", excess

    return f"{state.module_id} hit ({state.current_hp}/{state.max_hp} HP)", 0


def get_disable_effects(category: str) -> dict[str, int | float | bool]:
    """Get the stat penalty effects for disabling a module of the given category.

    Returns a dict of modifier keys to values. Multipliers are < 1.0
    (applied multiplicatively). Boolean flags indicate binary state.

    Args:
        category: Module category string.

    Returns:
        Dict of effect modifiers. Empty dict for categories with no effect.
    """
    effects: dict[str, float | bool] = {
        "cockpit": {
            "accuracy_mult": 0.60,  # -40% accuracy
            "evasion_mult": 0.75,  # -25% evasion
        },
        "engine": {
            "speed_mult": 0.20,  # Speed drops to 20%
            "evasion_mult": 0.70,  # -30% evasion
        },
        "weapon": {
            "weapon_offline": True,  # Mounted weapon stops firing
        },
        "shield": {
            "shield_mult": 0.50,  # -50% shield capacity
        },
        "cargo": {
            "cargo_damage_chance": 0.15,  # 15% chance to lose cargo per hit
        },
        "reactor": {
            "all_stats_mult": 0.75,  # -25% to all other module stats
        },
        "crew": {
            "crew_capacity_loss": 1,  # -1 crew slot
        },
        "utility": {},
        "structural": {},
    }.get(category, {})
    return effects


def check_severing(
    build: ShipBuild,
    module_catalog: dict[str, ShipModule],
    states: list[ModuleCombatState],
) -> list[int]:
    """Check if any disabled slots have caused structural severing.

    When a slot is destroyed, its footprint pixels are removed from the
    ship's connectivity graph. If this disconnects the graph, all slots
    on the smaller disconnected section are also disabled.

    Args:
        build: The ship build.
        module_catalog: Catalog reference (slot_definitions for slot builds).
        states: Current module combat states.

    Returns:
        List of state indices that were newly disabled by severing.
    """
    # Only check severing if at least one slot is disabled
    has_disabled = any(s.disabled for s in states)
    if not has_disabled:
        return []

    # Build the full pixel set from hull pixels
    all_pixel_coords = {(p.x, p.y) for p in build.pixels}
    if len(all_pixel_coords) <= 1:
        return []

    # For slot-based builds, we approximate severing by connectivity
    # of hull pixels (slots don't own pixels, they overlay them)
    # Simplified: no severing for pixel-only builds
    if not build.placed_slots:
        return []

    # Remaining connected pixels (hull pixels are the connectivity substrate)
    remaining = set(all_pixel_coords)
    if len(remaining) <= 1:
        return []

    # BFS to find connected components
    visited: set[tuple[int, int]] = set()
    components: list[set[tuple[int, int]]] = []
    for start in remaining:
        if start in visited:
            continue
        component: set[tuple[int, int]] = set()
        queue = [start]
        while queue:
            cx, cy = queue.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            component.add((cx, cy))
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in remaining and (nx, ny) not in visited:
                    queue.append((nx, ny))
        components.append(component)

    if len(components) <= 1:
        return []  # Still connected, no severing

    # Find the largest component (main body)
    largest = max(components, key=len)
    severed_pixels = set()
    for comp in components:
        if comp is not largest:
            severed_pixels |= comp

    # Disable all non-disabled slots whose footprint falls in severed sections
    newly_severed: list[int] = []
    for i, state in enumerate(states):
        if state.disabled:
            continue
        if state.placed_index >= len(build.placed_slots):
            continue
        placed_slot = build.placed_slots[state.placed_index]
        # Get slot footprint from catalog
        slot_def = module_catalog.get(placed_slot.slot_def_id)
        if not slot_def:
            continue
        fw = getattr(slot_def, "footprint_w", 1)
        fh = getattr(slot_def, "footprint_h", 1)
        slot_pixels = {
            (placed_slot.x + dx, placed_slot.y + dy) for dx in range(fw) for dy in range(fh)
        }
        # Slot is severed if ALL its pixels are in severed sections
        active_pixels = slot_pixels & all_pixel_coords
        if active_pixels and active_pixels.issubset(severed_pixels):
            state.disabled = True
            state.current_hp = 0
            newly_severed.append(i)

    return newly_severed


# ============================================================================
# Overkill Propagation (Phase 14)
# ============================================================================

# Tuning constants
CHAIN_DAMAGE_CHANCE = 0.30  # 30% chance to chain to adjacent module
CHAIN_DAMAGE_RATIO = 0.50  # Chain deals 50% of excess damage
MIN_EXCESS_FOR_CHAIN = 5  # Minimum excess to trigger chain check


def build_adjacency_map(
    build: "ShipBuild",
    module_catalog: dict[str, ShipModule],
) -> dict[int, list[int]]:
    """Build a map of which slots are 4-connected adjacent.

    Two slots are adjacent if any of their footprint cells share a
    4-connected edge (orthogonal neighbors).

    Args:
        build: The ship build.
        module_catalog: Slot definition catalog.

    Returns:
        Dict mapping slot index -> list of adjacent slot indices.
    """
    if not build.placed_slots:
        return {}

    # Resolve footprint pixel sets per slot
    slot_pixel_sets: list[set[tuple[int, int]]] = []
    for ps in build.placed_slots:
        slot_def = module_catalog.get(ps.slot_def_id)
        if slot_def:
            fw = getattr(slot_def, "footprint_w", 1)
            fh = getattr(slot_def, "footprint_h", 1)
            slot_pixel_sets.append({(ps.x + dx, ps.y + dy) for dx in range(fw) for dy in range(fh)})
        else:
            slot_pixel_sets.append(set())

    # Build adjacency by checking if any cells are 4-adjacent between pairs
    adjacency: dict[int, list[int]] = {i: [] for i in range(len(build.placed_slots))}

    for i in range(len(slot_pixel_sets)):
        if not slot_pixel_sets[i]:
            continue
        neighbors_of_i: set[tuple[int, int]] = set()
        for x, y in slot_pixel_sets[i]:
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                neighbors_of_i.add((x + dx, y + dy))
        for j in range(i + 1, len(slot_pixel_sets)):
            if not slot_pixel_sets[j]:
                continue
            if neighbors_of_i & slot_pixel_sets[j]:
                adjacency[i].append(j)
                adjacency[j].append(i)

    return adjacency


def process_overkill_chain(
    excess: int,
    source_idx: int,
    states: list[ModuleCombatState],
    adjacency: dict[int, list[int]],
    force_chain: bool = False,
) -> Optional[dict]:
    """Process overkill chain damage to an adjacent module.

    When a module is destroyed with excess damage, there's a chance
    the explosion chains to an adjacent module. Maximum one chain
    per hit to prevent infinite cascades.

    Args:
        excess: Excess damage from the destroyed module.
        source_idx: Index of the destroyed module.
        states: All module combat states.
        adjacency: Module adjacency map.
        force_chain: If True, skip probability roll (for testing).

    Returns:
        Dict with 'target_idx', 'damage', 'message' if chain triggers,
        or None if no chain.
    """
    if excess < MIN_EXCESS_FOR_CHAIN:
        return None

    # Find valid adjacent targets (alive, not disabled)
    neighbors = adjacency.get(source_idx, [])
    valid_targets = [idx for idx in neighbors if idx < len(states) and not states[idx].disabled]

    if not valid_targets:
        return None

    # Probability check
    if not force_chain and random.random() >= CHAIN_DAMAGE_CHANCE:
        return None

    # Pick a random neighbor
    target_idx = random.choice(valid_targets)
    chain_dmg = int(excess * CHAIN_DAMAGE_RATIO)

    if chain_dmg <= 0:
        return None

    target = states[target_idx]
    source = states[source_idx]
    src_name = source.category.replace("_", " ").title()
    tgt_name = target.category.replace("_", " ").title()

    return {
        "target_idx": target_idx,
        "damage": chain_dmg,
        "message": (
            f"{src_name} explosion chains to adjacent {tgt_name}! ({chain_dmg} chain damage)"
        ),
    }


def repair_all_modules(states: list[ModuleCombatState]) -> None:
    """Restore all modules to full HP after combat.

    Args:
        states: Module combat states to repair.
    """
    for state in states:
        state.current_hp = state.max_hp
        state.disabled = False
