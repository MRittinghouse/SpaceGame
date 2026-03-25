"""Session rating system — S/A/B/C/D performance grades for mini-games."""

RATING_COLORS: dict[str, tuple[int, int, int]] = {
    "S": (255, 215, 0),  # Gold
    "A": (50, 200, 100),  # Green
    "B": (100, 200, 255),  # Blue
    "C": (255, 200, 50),  # Yellow
    "D": (150, 160, 180),  # Gray
}

# Thresholds are descending: (S, A, B, C) — below C = D
MINING_THRESHOLDS: tuple[float, float, float, float] = (15.0, 10.0, 6.0, 3.0)  # ore/min
SALVAGE_THRESHOLDS: tuple[float, float, float, float] = (0.80, 0.60, 0.40, 0.20)  # extraction ratio
REFINING_THRESHOLDS: tuple[float, float, float, float] = (10.0, 6.0, 4.0, 2.0)  # output/min


def calculate_rating(value: float, thresholds: tuple[float, float, float, float]) -> str:
    """Calculate a session rating based on a performance value.

    Args:
        value: The performance metric to evaluate.
        thresholds: Descending tuple of (S, A, B, C) minimum thresholds.

    Returns:
        Rating string: "S", "A", "B", "C", or "D".
    """
    s, a, b, c = thresholds
    if value >= s:
        return "S"
    if value >= a:
        return "A"
    if value >= b:
        return "B"
    if value >= c:
        return "C"
    return "D"
