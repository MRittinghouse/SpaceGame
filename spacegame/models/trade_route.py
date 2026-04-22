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


@dataclass
class PriceMemory:
    """Last-seen commodity prices per visited system.

    Unlocked by the ``price_memory`` skill (QA Pass 5 Tier 3.F, 2026-04-21).
    When the player arrives at a system with the skill active, the current
    market snapshot is recorded here. The galaxy map reads this data to
    display "as of day N" price memory for unvisited (but previously-
    visited) systems, helping players plan trade routes without needing
    to re-travel to check prices.

    Design notes:
      - Always the LATEST snapshot per system — no history, no decay.
        "Last known" price is the entire value proposition.
      - Per-commodity day stamps so the UI can show "days ago" freshness
        and players can tell if their memory is stale.
      - Snapshots overwrite wholesale on re-visit — prices are independent
        per commodity but the visit event updates all of them together.
    """

    # system_id → {commodity_id: (price, game_day_seen)}
    _snapshots: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)

    def record(
        self,
        system_id: str,
        prices: dict[str, int],
        game_day: int,
    ) -> None:
        """Record a visit snapshot.

        Args:
            system_id: System the player just visited.
            prices: All commodity prices at that system as of the visit.
            game_day: Current in-game day for freshness tracking.
        """
        if not system_id or not prices:
            return
        snapshot: dict[str, tuple[int, int]] = {}
        for commodity_id, price in prices.items():
            if price <= 0:
                continue  # Skip unavailable/quest commodities
            snapshot[commodity_id] = (int(price), int(game_day))
        self._snapshots[system_id] = snapshot

    def get_last_known(
        self,
        system_id: str,
        commodity_id: str,
    ) -> tuple[int, int] | None:
        """Return the last-known ``(price, day_seen)`` or None if unknown."""
        return self._snapshots.get(system_id, {}).get(commodity_id)

    def get_snapshot(self, system_id: str) -> dict[str, tuple[int, int]]:
        """Return the full commodity snapshot for a system (empty dict if unknown)."""
        return dict(self._snapshots.get(system_id, {}))

    def known_systems(self) -> set[str]:
        """Set of all system IDs with any recorded snapshot."""
        return set(self._snapshots.keys())

    def has_memory(self, system_id: str) -> bool:
        """True if at least one price is remembered for ``system_id``."""
        return bool(self._snapshots.get(system_id))

    def clear(self) -> None:
        """Wipe all snapshots (e.g., on new game)."""
        self._snapshots.clear()

    def to_dict(self) -> dict:
        """Serialize to a save-friendly dict.

        Tuple is flattened to list because JSON can't carry tuples directly.
        """
        return {
            "snapshots": {
                sys_id: {cid: list(entry) for cid, entry in snap.items()}
                for sys_id, snap in self._snapshots.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceMemory":
        """Deserialize from dict. Tolerant of missing/partial data."""
        memory = cls()
        raw = data.get("snapshots", {})
        for sys_id, snap in raw.items():
            restored: dict[str, tuple[int, int]] = {}
            for cid, entry in snap.items():
                # Entry is [price, day] — tolerate both list and tuple.
                if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    try:
                        restored[cid] = (int(entry[0]), int(entry[1]))
                    except (TypeError, ValueError):
                        continue
            if restored:
                memory._snapshots[sys_id] = restored
        return memory
