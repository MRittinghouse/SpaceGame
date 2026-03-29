"""Ship physics computations for shape-based constraints.

Computes structural integrity (articulation points), center of mass,
hull efficiency (interior vs perimeter), and frontal profile. These
metrics create meaningful consequences for ship shape choices.

Part of the Shipbuilder Upgrade — Phase 6 (Physics Constraints).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from spacegame.models.ship_build import HullMaterial, ShipBuild
from spacegame.models.ship_module import ShipModule


class BalanceRating(Enum):
    """Ship center-of-mass balance categories."""

    BALANCED = "balanced"  # <15% offset — no penalty
    OFF_BALANCE = "off_balance"  # 15-30% — mild penalty
    SEVERELY_OFF = "severely_off"  # >30% — significant penalty


# ============================================================================
# Structural Integrity — Articulation Point Detection
# ============================================================================


def compute_structural_integrity(
    coords: list[tuple[int, int]],
) -> dict[tuple[int, int], float]:
    """Compute structural integrity scores for each pixel.

    Uses articulation point detection (Tarjan's algorithm variant) to
    find pixels whose removal would disconnect the ship. These are
    structural weak points (bottlenecks).

    Args:
        coords: List of (x, y) filled pixel positions.

    Returns:
        Dict mapping (x, y) to a score from 0.0 (safe) to 1.0 (critical).
        A score of 1.0 means removing that pixel disconnects the graph.
    """
    if len(coords) <= 2:
        return dict.fromkeys(coords, 0.0)

    coord_set = set(coords)
    # Find articulation points via iterative DFS
    art_points = _find_articulation_points(coord_set)

    # Score articulation points based on local redundancy.
    # A lone articulation point (no adjacent art points) is a true
    # single-point-of-failure: score 1.0. Articulation points that
    # are adjacent to other articulation points form a "bridge cluster"
    # — wider connections that are less critical: score 0.5.
    scores: dict[tuple[int, int], float] = {}
    for c in coords:
        if c not in art_points:
            scores[c] = 0.0
            continue
        # Count adjacent articulation points
        x, y = c
        adj_art = sum(
            1 for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)) if (x + dx, y + dy) in art_points
        )
        if adj_art == 0:
            scores[c] = 1.0  # Lone bottleneck — most critical
        else:
            scores[c] = 0.5  # Part of wider bridge — less critical
    return scores


def _find_articulation_points(
    coords: set[tuple[int, int]],
) -> set[tuple[int, int]]:
    """Find articulation points in a 4-connected pixel graph.

    An articulation point (cut vertex) is a pixel whose removal would
    disconnect the graph into two or more components.

    Uses iterative Tarjan's algorithm to avoid recursion depth issues.
    """
    if len(coords) <= 2:
        return set()

    # Build adjacency for the 4-connected graph
    neighbors: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for x, y in coords:
        adj = []
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n = (x + dx, y + dy)
            if n in coords:
                adj.append(n)
        neighbors[(x, y)] = adj

    # Iterative Tarjan's algorithm for articulation points
    disc: dict[tuple[int, int], int] = {}
    low: dict[tuple[int, int], int] = {}
    parent: dict[tuple[int, int], Optional[tuple[int, int]]] = {}
    art_points: set[tuple[int, int]] = set()
    timer = [0]

    for start in coords:
        if start in disc:
            continue
        # Iterative DFS
        stack: list[tuple[tuple[int, int], int]] = [(start, 0)]
        parent[start] = None
        disc[start] = low[start] = timer[0]
        timer[0] += 1
        child_count: dict[tuple[int, int], int] = {start: 0}

        while stack:
            node, idx = stack[-1]
            adj = neighbors[node]

            if idx < len(adj):
                stack[-1] = (node, idx + 1)
                neighbor = adj[idx]

                if neighbor not in disc:
                    parent[neighbor] = node
                    disc[neighbor] = low[neighbor] = timer[0]
                    timer[0] += 1
                    child_count[neighbor] = 0
                    stack.append((neighbor, 0))
                elif neighbor != parent.get(node):
                    low[node] = min(low[node], disc[neighbor])
            else:
                # Backtrack
                stack.pop()
                if stack:
                    par = stack[-1][0]
                    low[par] = min(low[par], low[node])
                    child_count[par] = child_count.get(par, 0) + 1

                    # Check if par is an articulation point
                    if parent[par] is None:
                        # Root: articulation point if it has 2+ children in DFS tree
                        if child_count[par] >= 2:
                            art_points.add(par)
                    else:
                        # Non-root: articulation point if low[node] >= disc[par]
                        if low[node] >= disc[par]:
                            art_points.add(par)

    return art_points


# ============================================================================
# Center of Mass
# ============================================================================


def compute_center_of_mass(
    build: ShipBuild,
    materials: dict[str, HullMaterial],
    module_catalog: dict[str, ShipModule],
) -> tuple[float, float, float, BalanceRating]:
    """Compute the weighted center of mass and balance rating.

    Each pixel is weighted by its material's weight_per_pixel. Module
    pixels are weighted by the module's total weight distributed evenly.

    Args:
        build: The ship build.
        materials: Material definitions.
        module_catalog: Module blueprints.

    Returns:
        (com_x, com_y, offset_percent, balance_rating) tuple.
        offset_percent is 0-100, representing how far CoM is from
        the geometric center as a percentage of the half-diagonal.
    """
    total_weight = 0.0
    weighted_x = 0.0
    weighted_y = 0.0

    # Hull pixel contributions
    for p in build.pixels:
        mat = materials.get(p.material_id)
        w = mat.weight_per_pixel if mat else 0.25
        total_weight += w
        weighted_x += p.x * w
        weighted_y += p.y * w

    if total_weight == 0:
        return 0.0, 0.0, 0.0, BalanceRating.BALANCED

    com_x = weighted_x / total_weight
    com_y = weighted_y / total_weight

    # Compute offset from geometric center of bounding box
    all_xs: list[int] = [p.x for p in build.pixels]
    all_ys: list[int] = [p.y for p in build.pixels]

    if not all_xs:
        return com_x, com_y, 0.0, BalanceRating.BALANCED

    min_x, max_x = min(all_xs), max(all_xs)
    min_y, max_y = min(all_ys), max(all_ys)
    geo_cx = (min_x + max_x) / 2.0
    geo_cy = (min_y + max_y) / 2.0

    # Offset as percentage of half-diagonal
    half_w = max(1.0, (max_x - min_x) / 2.0)
    half_h = max(1.0, (max_y - min_y) / 2.0)
    half_diag = (half_w**2 + half_h**2) ** 0.5

    dx = com_x - geo_cx
    dy = com_y - geo_cy
    distance = (dx**2 + dy**2) ** 0.5
    offset_pct = min(100.0, (distance / half_diag) * 100.0)

    # Rating
    if offset_pct < 15.0:
        rating = BalanceRating.BALANCED
    elif offset_pct < 30.0:
        rating = BalanceRating.OFF_BALANCE
    else:
        rating = BalanceRating.SEVERELY_OFF

    return com_x, com_y, offset_pct, rating


# ============================================================================
# Hull Efficiency
# ============================================================================


def compute_hull_efficiency(
    coords: list[tuple[int, int]],
) -> tuple[int, int, float]:
    """Compute hull efficiency: interior vs perimeter pixel ratio.

    Interior pixels have all 4 orthogonal neighbors filled. Perimeter
    pixels have at least one empty neighbor.

    Args:
        coords: List of (x, y) filled pixel positions.

    Returns:
        (interior_count, perimeter_count, efficiency_ratio) tuple.
        Ratio is 0.0 (all perimeter) to <1.0 (mostly interior).
    """
    if not coords:
        return 0, 0, 0.0

    coord_set = set(coords)
    interior = 0
    perimeter = 0

    for x, y in coords:
        all_neighbors = all(
            (x + dx, y + dy) in coord_set for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
        )
        if all_neighbors:
            interior += 1
        else:
            perimeter += 1

    total = interior + perimeter
    ratio = interior / total if total > 0 else 0.0
    return interior, perimeter, ratio


# ============================================================================
# Frontal Profile
# ============================================================================


def compute_frontal_profile(
    coords: list[tuple[int, int]],
    canvas_w: int,
) -> tuple[int, int, float]:
    """Compute the ship's frontal cross-section profile.

    Ships face right. The frontal profile is the ship's height (vertical
    extent) relative to the canvas. Narrower ships are harder to hit.

    Note: We use HEIGHT as frontal profile because the ship faces right.
    The "width" from the enemy's perspective is the ship's vertical extent.

    Args:
        coords: List of (x, y) filled pixel positions.
        canvas_w: Canvas width for reference scaling.

    Returns:
        (filled_width, filled_height, profile_ratio) tuple.
        profile_ratio is filled_height / canvas_w (how much of the
        canvas the ship's vertical extent covers).
    """
    if not coords:
        return 0, 0, 0.0

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    filled_w = max(xs) - min(xs) + 1
    filled_h = max(ys) - min(ys) + 1

    # Profile ratio: vertical extent relative to canvas width
    # (canvas_w used as the reference dimension for consistency)
    profile_ratio = filled_h / canvas_w if canvas_w > 0 else 0.0
    return filled_w, filled_h, profile_ratio


# ============================================================================
# Stat Modifiers from Physics
# ============================================================================


def compute_physics_modifiers(
    build: ShipBuild,
    materials: dict[str, HullMaterial],
    module_catalog: dict[str, ShipModule],
) -> dict[str, float]:
    """Compute all physics-based stat modifiers.

    Returns a dict of modifier names to multiplier values (1.0 = no change).

    Applied modifiers:
    - evasion_mult: from CoM balance + frontal profile
    - hull_efficiency: ratio of interior to total pixels
    """
    from spacegame.models.ship_module import resolve_all_pixels

    all_pixels = resolve_all_pixels(build, module_catalog)
    coords = [(p.x, p.y) for p in all_pixels]

    modifiers: dict[str, float] = {
        "evasion_mult": 1.0,
        "hull_efficiency": 0.0,
        "com_offset_pct": 0.0,
        "balance_rating": 0,  # 0=balanced, 1=off, 2=severe
        "frontal_profile": 0.0,
    }

    if not coords:
        return modifiers

    # Center of mass balance
    _, _, offset_pct, rating = compute_center_of_mass(build, materials, module_catalog)
    modifiers["com_offset_pct"] = offset_pct
    if rating == BalanceRating.OFF_BALANCE:
        modifiers["evasion_mult"] *= 0.90  # -10%
        modifiers["balance_rating"] = 1
    elif rating == BalanceRating.SEVERELY_OFF:
        modifiers["evasion_mult"] *= 0.75  # -25%
        modifiers["balance_rating"] = 2

    # Hull efficiency
    _, _, efficiency = compute_hull_efficiency(coords)
    modifiers["hull_efficiency"] = efficiency

    # Frontal profile
    _, _, profile_ratio = compute_frontal_profile(coords, build.canvas_w)
    modifiers["frontal_profile"] = profile_ratio
    # Narrow ships (<0.3 profile) get evasion bonus; wide (>0.6) get penalty
    if profile_ratio < 0.3:
        modifiers["evasion_mult"] *= 1.10  # +10% evasion for narrow
    elif profile_ratio > 0.6:
        modifiers["evasion_mult"] *= 0.90  # -10% evasion for wide

    return modifiers
