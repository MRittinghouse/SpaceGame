"""Player identity system — ship naming, reputation titles, and playstyle recognition.

Computes player identity from tracked stats. Titles and playstyle are
derived (not stored), so they automatically update as the player progresses.
Ship name is stored and persisted.
"""

from typing import Optional

# ============================================================================
# REPUTATION TITLES
# ============================================================================

# Title tiers per activity domain. Each entry: (threshold, title)
# Thresholds checked against cumulative player stats.

MINING_TITLES: list[tuple[int, str]] = [
    (10, "Prospector"),
    (100, "Ore Hauler"),
    (500, "Vein Striker"),
    (2000, "Deep Core Pioneer"),
    (5000, "Iron Baron"),
]

TRADING_TITLES: list[tuple[int, str]] = [
    (5, "Peddler"),
    (50, "Merchant"),
    (200, "Market Shark"),
    (1000, "Trade Magnate"),
    (5000, "Tycoon"),
]

COMBAT_TITLES: list[tuple[int, str]] = [
    (3, "Scrapper"),
    (15, "Corsair"),
    (50, "Battle-Scarred"),
    (100, "Void Wolf"),
    (250, "Warlord"),
]

SALVAGE_TITLES: list[tuple[int, str]] = [
    (10, "Scavenger"),
    (50, "Hull Cracker"),
    (200, "Wreck Diver"),
    (500, "Derelict Hunter"),
    (1500, "Salvage King"),
]

REFINING_TITLES: list[tuple[int, str]] = [
    (5, "Smelter"),
    (30, "Forge Hand"),
    (100, "Master Smith"),
    (300, "Catalyst Sage"),
    (1000, "Grand Artificer"),
]

EXPLORATION_TITLES: list[tuple[int, str]] = [
    (3, "Drifter"),
    (5, "Wayfarer"),
    (8, "Star Mapper"),
    (10, "Trailblazer"),
    (11, "Galaxy Walker"),
]


def get_title(value: int, tiers: list[tuple[int, str]]) -> Optional[str]:
    """Get the highest title earned for a given stat value.

    Args:
        value: Current stat value.
        tiers: List of (threshold, title) in ascending order.

    Returns:
        Title string, or None if no threshold met.
    """
    earned = None
    for threshold, title in tiers:
        if value >= threshold:
            earned = title
    return earned


def get_all_titles(
    ore_mined: int = 0,
    trades_completed: int = 0,
    combats_won: int = 0,
    items_salvaged: int = 0,
    items_refined: int = 0,
    systems_visited: int = 0,
) -> dict[str, str]:
    """Compute all earned titles from player stats.

    Args:
        ore_mined: Lifetime ore mined.
        trades_completed: Lifetime trades.
        combats_won: Lifetime combat victories.
        items_salvaged: Lifetime salvage.
        items_refined: Lifetime refined items.
        systems_visited: Unique systems visited.

    Returns:
        Dict of domain -> title for each earned title.
    """
    titles: dict[str, str] = {}
    pairs = [
        ("mining", ore_mined, MINING_TITLES),
        ("trading", trades_completed, TRADING_TITLES),
        ("combat", combats_won, COMBAT_TITLES),
        ("salvage", items_salvaged, SALVAGE_TITLES),
        ("refining", items_refined, REFINING_TITLES),
        ("exploration", systems_visited, EXPLORATION_TITLES),
    ]
    for domain, value, tiers in pairs:
        title = get_title(value, tiers)
        if title:
            titles[domain] = title
    return titles


def get_primary_title(
    ore_mined: int = 0,
    trades_completed: int = 0,
    combats_won: int = 0,
    items_salvaged: int = 0,
    items_refined: int = 0,
    systems_visited: int = 0,
) -> str:
    """Get the player's highest-ranking single title.

    Picks the title from the domain where the player has progressed furthest
    (highest tier index). Ties broken by: trading > combat > mining > salvage > refining > exploration.

    Returns:
        Title string, or "Rookie" if no titles earned.
    """
    best_title = "Rookie"
    best_tier_idx = -1

    pairs = [
        (trades_completed, TRADING_TITLES),
        (combats_won, COMBAT_TITLES),
        (ore_mined, MINING_TITLES),
        (items_salvaged, SALVAGE_TITLES),
        (items_refined, REFINING_TITLES),
        (systems_visited, EXPLORATION_TITLES),
    ]
    for value, tiers in pairs:
        for idx, (threshold, title) in enumerate(tiers):
            if value >= threshold and idx > best_tier_idx:
                best_tier_idx = idx
                best_title = title
    return best_title


# ============================================================================
# PLAYSTYLE RECOGNITION
# ============================================================================

PLAYSTYLE_LABELS: dict[str, str] = {
    "trading": "Trader",
    "mining": "Miner",
    "combat": "Fighter",
    "salvage": "Salvager",
    "refining": "Artisan",
    "exploration": "Explorer",
    "balanced": "Freelancer",
}


def get_playstyle(
    ore_mined: int = 0,
    trades_completed: int = 0,
    combats_won: int = 0,
    items_salvaged: int = 0,
    items_refined: int = 0,
    systems_visited: int = 0,
) -> str:
    """Determine the player's dominant playstyle.

    Normalizes each activity against its tier thresholds to compute
    relative engagement. The activity with the highest normalized
    score determines playstyle. If no clear dominant, returns "balanced".

    Returns:
        Playstyle key (e.g., "trading", "mining", "balanced").
    """
    # Normalize each stat against its mid-tier threshold
    scores = {
        "trading": trades_completed / 50 if trades_completed > 0 else 0,
        "mining": ore_mined / 100 if ore_mined > 0 else 0,
        "combat": combats_won / 15 if combats_won > 0 else 0,
        "salvage": items_salvaged / 50 if items_salvaged > 0 else 0,
        "refining": items_refined / 30 if items_refined > 0 else 0,
        "exploration": systems_visited / 5 if systems_visited > 0 else 0,
    }

    if not any(v > 0 for v in scores.values()):
        return "balanced"

    top_activity = max(scores, key=lambda k: scores[k])
    top_score = scores[top_activity]

    # Need at least 20% more engagement than second-highest to be "dominant"
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0] > 0:
        ratio = sorted_scores[1] / sorted_scores[0] if sorted_scores[0] > 0 else 0
        if ratio > 0.8:
            return "balanced"

    if top_score < 0.2:
        return "balanced"

    return top_activity


def get_playstyle_label(
    ore_mined: int = 0,
    trades_completed: int = 0,
    combats_won: int = 0,
    items_salvaged: int = 0,
    items_refined: int = 0,
    systems_visited: int = 0,
) -> str:
    """Get the human-readable playstyle label.

    Returns:
        Label like "Trader", "Miner", "Freelancer", etc.
    """
    style = get_playstyle(
        ore_mined,
        trades_completed,
        combats_won,
        items_salvaged,
        items_refined,
        systems_visited,
    )
    return PLAYSTYLE_LABELS.get(style, "Freelancer")
