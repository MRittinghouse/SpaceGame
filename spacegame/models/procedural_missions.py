"""Procedural mission generator for station board contracts.

Creates 5 types of repeatable side missions: bounty, delivery, smuggling,
survey, and salvage. Missions are generated per-system on each station visit
and rotate with the game day.
"""

import itertools
from collections.abc import Callable
from typing import Any, Optional

from spacegame.models.commodity import Commodity, Legality
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.system import StarSystem
from spacegame.models.travel import jump_fuel_cost
from spacegame.sim_rng import SimRng

# Credit reward multipliers by system danger level
_DANGER_MULTIPLIER = {"safe": 1.0, "moderate": 1.5, "dangerous": 2.0}

# Smuggling commodities (restricted/illegal)
_SMUGGLING_COMMODITIES = [
    "weapons_components",
    "restricted_tech",
    "stolen_data",
    "combat_stims",
    "contraband_medicine",
]

# Bug bash BB-11: a delivery fits a starting shuttle's hold, and route fuel is priced for a
# shuttle's efficiency with no skill.
_CONTRACT_HOLD = 50
_ROUTE_FUEL_EFFICIENCY = 10


class ProceduralMissionGenerator:
    """Generates procedural station board missions.

    Creates bounty, delivery, smuggling, survey, and salvage contracts
    based on the origin system's economy and the current game day.
    Uses deterministic RNG seeded from (base_seed + system_id + game_day).
    """

    def __init__(
        self,
        systems: dict[str, StarSystem],
        commodities: dict[str, Commodity],
        enemy_templates: dict[str, Any],
        seed: int = 0,
    ) -> None:
        """Initialize generator with game data.

        Args:
            systems: All star systems by ID.
            commodities: All commodities by ID.
            enemy_templates: Enemy templates by ID.
            seed: Base RNG seed for deterministic generation.
        """
        self._systems = systems
        self._commodities = commodities
        self._enemy_templates = enemy_templates
        self._base_seed = seed

    def _make_rng(self, system_id: str, game_day: int, salt: str = "") -> SimRng:
        """Create a seeded RNG for deterministic generation."""
        return SimRng.from_key("procedural", self._base_seed, system_id, game_day, salt)

    def _mission_id(self, prefix: str, system_id: str, game_day: int) -> str:
        """Build a mission ID keyed like the mission's content.

        A board holds at most one mission of each type (``generate_for_system``
        samples distinct generators), so type, system, day, and base seed name a
        mission uniquely. A generator rebuilt on load gives a regenerated mission
        the ID it had before, so the copy collides with the restored mission in
        ``MissionManager.add_mission`` instead of being offered twice.
        """
        return f"proc_{prefix}_{system_id}_{game_day}_{self._base_seed}"

    def _danger_mult(self, system_id: str) -> float:
        """Get credit multiplier for system danger."""
        system = self._systems.get(system_id)
        if not system:
            return 1.0
        return _DANGER_MULTIPLIER.get(system.danger_level, 1.0)

    def _pick_other_system(self, rng: SimRng, exclude: str) -> str:
        """Pick a random system that isn't the excluded one."""
        candidates = [sid for sid in self._systems if sid != exclude]
        return rng.choice(candidates)

    def _pick_trade_commodity(self, rng: SimRng, system_id: str) -> Optional[str]:
        """One of the origin's legal specialty exports, or None when it has none (BB-11).

        A delivery is carriage of what the origin makes; contraband stays off the lawful
        board, and an origin that exports nothing legal (the Fulcrum, Heron's Mark) posts
        no delivery.
        """
        system = self._systems.get(system_id)
        exports = (system.economy.specialty_exports or []) if system and system.economy else []
        candidates = [
            c
            for c in exports
            if c in self._commodities and self._commodities[c].legality == Legality.LEGAL
        ]
        return rng.choice(candidates) if candidates else None

    def _route_fuel(self, origin_id: str, stops: list[str]) -> int:
        """Credits for the fuel of the shortest round trip from the origin through the stops.

        Fuel at its base price, for a shuttle's efficiency and no skill (bug bash BB-11).
        Surveys and salvage carry no goods, so their fuel is their whole cost.
        """
        best: Optional[int] = None
        for order in itertools.permutations(stops):
            legs = [origin_id, *order, origin_id]
            units = sum(
                jump_fuel_cost(self._systems[a], self._systems[b], _ROUTE_FUEL_EFFICIENCY, 0.0)
                for a, b in itertools.pairwise(legs)
            )
            if best is None or units < best:
                best = units
        return (best or 0) * self._commodities["fuel"].base_price

    def generate_bounty(self, system_id: str, game_day: int) -> Mission:
        """Generate a bounty hunting contract.

        Hunt a specific number of enemies, then return to the origin system.

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A bounty Mission.
        """
        rng = self._make_rng(system_id, game_day, "bounty")
        mid = self._mission_id("bounty", system_id, game_day)
        system = self._systems[system_id]
        kills = rng.randint(1, 3)
        base_reward = rng.randint(300, 600)
        reward = int(base_reward * self._danger_mult(system_id) * kills)
        xp = 40 * kills

        return Mission(
            id=mid,
            name=f"Bounty: Clear {kills} Hostile{'s' if kills > 1 else ''}",
            description=(
                f"Local authorities in {system.name} are offering a bounty for "
                f"eliminating {kills} hostile{'s' if kills > 1 else ''} in the region. "
                f"Return here after completing the contract."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.WIN_COMBAT,
                    target_id="",
                    target_quantity=kills,
                    description=f"Win {kills} combat encounter{'s' if kills > 1 else ''}",
                ),
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=system_id,
                    description=f"Return to {system.name} to collect bounty",
                    after_departure=True,
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=reward),
                MissionReward(reward_type="xp", amount=xp),
            ],
        )

    def generate_delivery(self, system_id: str, game_day: int) -> Optional[Mission]:
        """Generate a cargo delivery contract.

        Collect a legal specialty export of the origin and deliver it to another system. The
        quantity fits a starting hold, and the pay is the goods' base value (BB-11).

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A delivery Mission, or None when the origin exports nothing legal.
        """
        rng = self._make_rng(system_id, game_day, "delivery")
        mid = self._mission_id("delivery", system_id, game_day)
        dest_id = self._pick_other_system(rng, system_id)
        dest = self._systems[dest_id]
        commodity_id = self._pick_trade_commodity(rng, system_id)
        if commodity_id is None:
            return None
        commodity = self._commodities[commodity_id]
        qty = min(rng.randint(3, 10), _CONTRACT_HOLD // max(1, commodity.volume_per_unit))
        base_reward = int(commodity.base_price * qty * 1.0)
        reward = int(base_reward * self._danger_mult(system_id))
        xp = 30 + qty * 5

        return Mission(
            id=mid,
            name=f"Delivery: {commodity.name} to {dest.name}",
            description=(
                f"Transport {qty} units of {commodity.name} to {dest.name}. "
                f"Acquire the goods and deliver them to collect payment."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.COLLECT_CARGO,
                    target_id=commodity_id,
                    target_quantity=qty,
                    description=f"Acquire {qty} {commodity.name}",
                ),
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=dest_id,
                    description=f"Deliver to {dest.name}",
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=max(reward, 150)),
                MissionReward(reward_type="xp", amount=xp),
                MissionReward(
                    reward_type="deliver_cargo",
                    amount=qty,
                    target_id=commodity_id,
                ),
            ],
            ordered_final=True,
        )

    def generate_smuggling(self, system_id: str, game_day: int) -> Mission:
        """Generate a smuggling run contract.

        Player receives contraband and must deliver it to a destination.

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A smuggling Mission.
        """
        rng = self._make_rng(system_id, game_day, "smuggling")
        mid = self._mission_id("smuggling", system_id, game_day)
        system = self._systems[system_id]
        dest_id = self._pick_other_system(rng, system_id)
        dest = self._systems[dest_id]

        # Pick a smuggling commodity that exists in our commodities
        available_smuggling = [c for c in _SMUGGLING_COMMODITIES if c in self._commodities]
        commodity_id = rng.choice(available_smuggling) if available_smuggling else "electronics"
        commodity = self._commodities[commodity_id]
        qty = rng.randint(2, 5)
        reward = int(commodity.base_price * qty * 1.2 * self._danger_mult(system_id))
        xp = 50 + qty * 10

        return Mission(
            id=mid,
            name=f"Smuggling: {commodity.name} to {dest.name}",
            description=(
                f"A contact in {system.name} needs {qty} units of {commodity.name} "
                f"moved to {dest.name}, no questions asked. The cargo will be "
                f"loaded when you accept."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            on_accept_cargo=[AcceptCargo(commodity_id=commodity_id, quantity=qty)],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.COLLECT_CARGO,
                    target_id=commodity_id,
                    target_quantity=qty,
                    description=f"Keep the {qty} {commodity.name} aboard",
                ),
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=dest_id,
                    description=f"Deliver contraband to {dest.name}",
                ),
            ],
            ordered_final=True,
            rewards=[
                MissionReward(reward_type="credits", amount=max(reward, 300)),
                MissionReward(reward_type="xp", amount=xp),
                MissionReward(
                    reward_type="remove_cargo",
                    amount=qty,
                    target_id=commodity_id,
                ),
            ],
        )

    def generate_survey(self, system_id: str, game_day: int) -> Mission:
        """Generate a survey mission.

        Visit 2-3 systems and return to report.

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A survey Mission.
        """
        rng = self._make_rng(system_id, game_day, "survey")
        mid = self._mission_id("survey", system_id, game_day)
        system = self._systems[system_id]
        num_targets = rng.randint(2, 3)
        candidates = [sid for sid in self._systems if sid != system_id]
        targets = rng.sample(candidates, min(num_targets, len(candidates)))
        reward = int(200 * len(targets) * self._danger_mult(system_id))
        xp = 25 * len(targets)

        objectives = [
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id=tid,
                description=f"Survey {self._systems[tid].name}",
            )
            for tid in targets
        ]
        objectives.append(
            MissionObjective(
                type=ObjectiveType.REACH_SYSTEM,
                target_id=system_id,
                description=f"Return to {system.name} with survey data",
                after_departure=True,
            )
        )

        target_names = ", ".join(self._systems[t].name for t in targets)
        return Mission(
            id=mid,
            name=f"Survey: {len(targets)} Systems",
            description=(
                f"A research consortium in {system.name} needs market and "
                f"navigational data from {target_names}. Visit each system "
                f"and return with the data."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            objectives=objectives,
            rewards=[
                MissionReward(reward_type="credits", amount=max(reward, 250)),
                MissionReward(reward_type="xp", amount=xp),
                MissionReward(
                    reward_type="route_fuel", amount=self._route_fuel(system_id, targets)
                ),
            ],
        )

    def generate_salvage(self, system_id: str, game_day: int) -> Mission:
        """Generate a salvage claim contract.

        Travel to a system with salvage opportunities and return.

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A salvage Mission.
        """
        rng = self._make_rng(system_id, game_day, "salvage")
        mid = self._mission_id("salvage", system_id, game_day)
        system = self._systems[system_id]
        # Prefer dangerous systems for salvage
        danger_systems = [
            sid
            for sid, s in self._systems.items()
            if s.danger_level in ("moderate", "dangerous") and sid != system_id
        ]
        if not danger_systems:
            danger_systems = [sid for sid in self._systems if sid != system_id]
        dest_id = rng.choice(danger_systems)
        dest = self._systems[dest_id]
        reward = int(400 * self._danger_mult(system_id))
        xp = 60

        return Mission(
            id=mid,
            name=f"Salvage: Wreckage near {dest.name}",
            description=(
                f"Sensors have detected a derelict vessel near {dest.name}. "
                f"Travel there to claim salvage rights, then return to "
                f"{system.name} for your finder's fee."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=dest_id,
                    description=f"Investigate wreckage near {dest.name}",
                ),
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=system_id,
                    description=f"Return to {system.name}",
                    after_departure=True,
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=max(reward, 300)),
                MissionReward(reward_type="xp", amount=xp),
                MissionReward(
                    reward_type="route_fuel", amount=self._route_fuel(system_id, [dest_id])
                ),
            ],
        )

    def generate_for_system(self, system_id: str, game_day: int) -> list[Mission]:
        """Draw 2-3 varied mission types for a system's station board.

        Picks from all 5 template types, weighted by system characteristics.

        Args:
            system_id: System to generate missions for.
            game_day: Current game day.

        Returns:
            The generated missions, one fewer when a delivery is drawn at an origin that
            exports nothing legal (BB-11).
        """
        rng = self._make_rng(system_id, game_day, "board")
        system = self._systems.get(system_id)
        if not system:
            return []

        # Weight templates by system type
        generators: list[tuple[str, Callable[[str, int], Optional[Mission]]]] = [
            ("bounty", self.generate_bounty),
            ("delivery", self.generate_delivery),
            ("survey", self.generate_survey),
            ("salvage", self.generate_salvage),
            ("smuggling", self.generate_smuggling),
        ]

        # Pick 2-3 distinct types
        count = rng.randint(2, 3)
        selected = rng.sample(generators, min(count, len(generators)))

        missions: list[Mission] = []
        for _name, gen_func in selected:
            mission = gen_func(system_id, game_day)
            if mission is not None:
                missions.append(mission)
        return missions
