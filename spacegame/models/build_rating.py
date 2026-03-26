"""Ship build rating system.

Evaluates a ship build across four axes (Combat, Trade, Mobility, Durability)
and assigns letter grades. Purely informational — never blocks confirmation.
Designed to encourage optimization and help players understand design quality.
"""

from spacegame.models.ship_build import FRAME_SLOT_LIMITS, ShipBuild

# Letter grade thresholds (score 0.0 to 1.0 → grade)
_GRADE_THRESHOLDS = [
    (0.90, "S"),
    (0.75, "A"),
    (0.55, "B"),
    (0.35, "C"),
    (0.15, "D"),
    (0.00, "F"),
]

GRADE_ORDER: dict[str, int] = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4, "S": 5}


def _score_to_grade(score: float) -> str:
    """Convert a 0.0-1.0 score to a letter grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def _infer_slot_type(slot_def_id: str) -> str:
    """Infer slot type from a slot_def_id like 'weapon_small' or 'cockpit_scout_pod'."""
    # Known type prefixes in order of specificity
    for prefix in (
        "cockpit",
        "weapon",
        "defense",
        "engine",
        "utility",
        "fuel",
        "cargo",
        "crew_quarters",
        "reactor",
    ):
        if slot_def_id.startswith(prefix):
            return prefix
    return "utility"


def _infer_slot_size(slot_def_id: str) -> str:
    """Infer slot size from a slot_def_id like 'weapon_medium_v2'."""
    if "_large" in slot_def_id:
        return "large"
    if "_medium" in slot_def_id:
        return "medium"
    return "small"


def _count_slot_types(build: ShipBuild, slot_defs: dict) -> dict[str, int]:
    """Count placed slots by type."""
    counts: dict[str, int] = {}
    for ps in build.placed_slots:
        sd = slot_defs.get(ps.slot_def_id)
        stype = sd.slot_type if sd else _infer_slot_type(ps.slot_def_id)
        counts[stype] = counts.get(stype, 0) + 1
    return counts


def _count_slot_sizes(build: ShipBuild, slot_defs: dict) -> dict[str, dict[str, int]]:
    """Count placed slots by type and size."""
    counts: dict[str, dict[str, int]] = {}
    for ps in build.placed_slots:
        sd = slot_defs.get(ps.slot_def_id)
        stype = sd.slot_type if sd else _infer_slot_type(ps.slot_def_id)
        ssize = sd.size if sd else _infer_slot_size(ps.slot_def_id)
        counts.setdefault(stype, {})
        counts[stype][ssize] = counts[stype].get(ssize, 0) + 1
    return counts


def _get_frame_limits(weight_class: str) -> dict[str, int]:
    """Get the frame slot limits for a weight class."""
    return FRAME_SLOT_LIMITS.get(weight_class, FRAME_SLOT_LIMITS.get("small", {}))


def compute_build_rating(
    build: ShipBuild,
    slot_definitions: dict,
    parts_catalog: dict,
) -> dict[str, tuple[str, float, str]]:
    """Compute build quality ratings across four axes.

    Args:
        build: The ship build to evaluate.
        slot_definitions: SlotDefinition catalog.
        parts_catalog: ShipPart catalog (for future equipment-aware rating).

    Returns:
        Dict mapping axis name to (letter_grade, numeric_score, feedback_text).
        Axes: "combat", "trade", "mobility", "durability".
    """
    counts = _count_slot_types(build, slot_definitions)
    sizes = _count_slot_sizes(build, slot_definitions)
    limits = _get_frame_limits(build.weight_class)
    n_pixels = len(build.pixels)

    # Total slot capacity for this frame
    total_capacity = sum(limits.values())
    total_placed = sum(counts.values())
    fill_ratio = total_placed / max(1, total_capacity)

    results: dict[str, tuple[str, float, str]] = {}

    # === COMBAT ===
    weapons = counts.get("weapon", 0)
    defense = counts.get("defense", 0)
    reactors = counts.get("reactor", 0)
    weapon_limit = limits.get("weapon", 1)
    defense_limit = limits.get("defense", 1)

    combat_score = 0.0
    combat_feedback = []

    # Weapon coverage (0-0.4)
    weapon_ratio = weapons / max(1, weapon_limit)
    combat_score += min(0.4, weapon_ratio * 0.4)
    if weapons == 0:
        combat_feedback.append("No weapons")
    elif weapon_ratio < 0.5:
        combat_feedback.append(f"Low weapons ({weapons}/{weapon_limit})")

    # Defense coverage (0-0.25)
    defense_ratio = defense / max(1, defense_limit)
    combat_score += min(0.25, defense_ratio * 0.25)
    if defense == 0:
        combat_feedback.append("No defenses")

    # Reactor (0-0.15)
    combat_score += 0.15 if reactors >= 1 else 0.0

    # Size bonus — larger weapons score higher (0-0.1)
    large_weapons = sizes.get("weapon", {}).get("large", 0)
    medium_weapons = sizes.get("weapon", {}).get("medium", 0)
    combat_score += min(0.1, (large_weapons * 0.05 + medium_weapons * 0.025))

    # Balance bonus — having both offense and defense (0-0.1)
    if weapons > 0 and defense > 0:
        combat_score += 0.1

    results["combat"] = (
        _score_to_grade(combat_score),
        round(combat_score, 3),
        " | ".join(combat_feedback) if combat_feedback else "Well armed",
    )

    # === TRADE ===
    cargo = counts.get("cargo", 0)
    fuel = counts.get("fuel", 0)
    cargo_limit = limits.get("cargo", 1)

    trade_score = 0.0
    trade_feedback = []

    # Cargo coverage (0-0.5)
    cargo_ratio = cargo / max(1, cargo_limit)
    trade_score += min(0.5, cargo_ratio * 0.5)
    if cargo == 0:
        trade_feedback.append("No cargo bays")
    elif cargo_ratio < 0.5:
        trade_feedback.append(f"Low cargo ({cargo}/{cargo_limit})")

    # Fuel (0-0.25)
    trade_score += min(0.25, fuel * 0.15)
    if fuel == 0:
        trade_feedback.append("No fuel tanks")

    # Hull pixels for weight efficiency (0-0.15)
    pixel_ratio = min(1.0, n_pixels / 80.0)
    trade_score += pixel_ratio * 0.15

    # Bonus for large cargo bays (0-0.1)
    large_cargo = sizes.get("cargo", {}).get("large", 0)
    trade_score += min(0.1, large_cargo * 0.05)

    results["trade"] = (
        _score_to_grade(trade_score),
        round(trade_score, 3),
        " | ".join(trade_feedback) if trade_feedback else "Ready to trade",
    )

    # === MOBILITY ===
    engines = counts.get("engine", 0)
    engine_limit = limits.get("engine", 1)

    mobility_score = 0.0
    mobility_feedback = []

    # Engine coverage (0-0.45) — scales with both ratio and absolute count
    engine_ratio = engines / max(1, engine_limit)
    mobility_score += min(0.3, engine_ratio * 0.3)
    # Bonus for extra engines beyond the first (0-0.15)
    mobility_score += min(0.15, max(0, engines - 1) * 0.08)
    if engines == 0:
        mobility_feedback.append("No engines")
    elif engine_ratio < 0.5:
        mobility_feedback.append(f"Low engines ({engines}/{engine_limit})")

    # Fuel range (0-0.2)
    mobility_score += min(0.2, fuel * 0.12)
    if fuel == 0:
        mobility_feedback.append("No fuel range")

    # Weight efficiency — lighter builds are more mobile (0-0.1)
    weight_penalty = min(1.0, total_placed / max(1, total_capacity))
    mobility_score += 0.1 * (1.0 - weight_penalty * 0.3)

    # Engine size bonus (0-0.15)
    large_engines = sizes.get("engine", {}).get("large", 0)
    medium_engines = sizes.get("engine", {}).get("medium", 0)
    mobility_score += min(0.15, large_engines * 0.08 + medium_engines * 0.04)

    results["mobility"] = (
        _score_to_grade(mobility_score),
        round(mobility_score, 3),
        " | ".join(mobility_feedback) if mobility_feedback else "Fast and agile",
    )

    # === DURABILITY ===
    durability_score = 0.0
    durability_feedback = []

    # Hull pixels (0-0.35)
    hull_score = min(1.0, n_pixels / 120.0)
    durability_score += hull_score * 0.35
    if n_pixels == 0:
        durability_feedback.append("No hull")
    elif n_pixels < 40:
        durability_feedback.append("Thin hull")

    # Defense slots (0-0.25)
    durability_score += min(0.25, defense_ratio * 0.25)
    if defense == 0:
        durability_feedback.append("No shields")

    # Crew quarters for damage control (0-0.1)
    crew = counts.get("crew_quarters", 0)
    durability_score += min(0.1, crew * 0.05)

    # Reactor for sustained combat (0-0.15)
    durability_score += min(0.15, reactors * 0.1)

    # Slot fill ratio — more complete builds are more durable (0-0.15)
    durability_score += fill_ratio * 0.15

    results["durability"] = (
        _score_to_grade(durability_score),
        round(durability_score, 3),
        " | ".join(durability_feedback) if durability_feedback else "Built to last",
    )

    return results
