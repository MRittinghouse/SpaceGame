"""Trade route tracking for efficiency bonuses.

Tracks player travel between systems to reward established trade routes
with discount bonuses.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TradeRouteTracker:
    """Tracks trade route usage between system pairs.

    Routes are symmetric: A->B and B->A count as the same route.
    Efficiency bonuses increase with usage.
    """

    _routes: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def _route_key(system_a: str, system_b: str) -> str:
        """Create a canonical sorted key for a system pair."""
        a, b = sorted([system_a, system_b])
        return f"{a}|{b}"

    def record_trip(self, system_a: str, system_b: str) -> None:
        """Record a completed trade trip between two systems.

        Args:
            system_a: Origin system ID.
            system_b: Destination system ID.
        """
        key = self._route_key(system_a, system_b)
        self._routes[key] = self._routes.get(key, 0) + 1

    def get_route_count(self, system_a: str, system_b: str) -> int:
        """Get number of trips on a route.

        Args:
            system_a: First system ID.
            system_b: Second system ID.

        Returns:
            Trip count for this route.
        """
        key = self._route_key(system_a, system_b)
        return self._routes.get(key, 0)

    def get_efficiency_bonus(self, system_a: str, system_b: str) -> float:
        """Get trade efficiency bonus for a route.

        Args:
            system_a: First system ID.
            system_b: Second system ID.

        Returns:
            Bonus as a fraction: 0.0, 0.05, 0.10, or 0.15.
        """
        count = self.get_route_count(system_a, system_b)
        if count >= 10:
            return 0.15
        elif count >= 5:
            return 0.10
        elif count >= 3:
            return 0.05
        return 0.0

    def get_active_routes(self) -> list[tuple[str, str, int]]:
        """Get all routes with their trip counts.

        Returns:
            List of (system_a, system_b, count) tuples.
        """
        result = []
        for key, count in self._routes.items():
            a, b = key.split("|")
            result.append((a, b, count))
        return result

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {"routes": dict(self._routes)}

    @classmethod
    def from_dict(cls, data: dict) -> "TradeRouteTracker":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with routes mapping.

        Returns:
            TradeRouteTracker instance.
        """
        tracker = cls()
        tracker._routes = dict(data.get("routes", {}))
        return tracker
