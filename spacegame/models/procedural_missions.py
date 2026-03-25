"""Procedural mission generator for station board contracts.

Creates 5 types of repeatable side missions: bounty, delivery, smuggling,
survey, and salvage. Missions are generated per-system on each station visit
and rotate with the game day.
"""

import random
from typing import Any

from spacegame.models.commodity import Commodity, Legality
from spacegame.models.mission import (
    AcceptCargo,
    Mission,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.system import StarSystem

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
        self._counter = 0

    def _make_rng(self, system_id: str, game_day: int, salt: str = "") -> random.Random:
        """Create a seeded RNG for deterministic generation."""
        seed = hash(f"{self._base_seed}_{system_id}_{game_day}_{salt}") & 0xFFFFFFFF
        return random.Random(seed)

    def _next_id(self, prefix: str, system_id: str, game_day: int) -> str:
        """Generate a unique mission ID."""
        self._counter += 1
        return f"proc_{prefix}_{system_id}_{game_day}_{self._base_seed}_{self._counter}"

    def _danger_mult(self, system_id: str) -> float:
        """Get credit multiplier for system danger."""
        system = self._systems.get(system_id)
        if not system:
            return 1.0
        return _DANGER_MULTIPLIER.get(system.danger_level, 1.0)

    def _pick_other_system(self, rng: random.Random, exclude: str) -> str:
        """Pick a random system that isn't the excluded one."""
        candidates = [sid for sid in self._systems if sid != exclude]
        return rng.choice(candidates)

    def _pick_trade_commodity(self, rng: random.Random, system_id: str) -> str:
        """Pick a commodity relevant to the system's economy."""
        system = self._systems.get(system_id)
        if system and system.economy:
            exports = system.economy.specialty_exports or []
            imports = system.economy.specialty_imports or []
            candidates = [c for c in exports + imports if c in self._commodities]
            if candidates:
                return rng.choice(candidates)
        # Fallback: any legal commodity
        legal = [cid for cid, c in self._commodities.items() if c.legality == Legality.LEGAL]
        return rng.choice(legal)

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
        mid = self._next_id("bounty", system_id, game_day)
        system = self._systems[system_id]
        kills = rng.randint(1, 3)
        base_reward = rng.randint(300, 600)
        reward = int(base_reward * self._danger_mult(system_id) * kills)
        xp = 40 * kills

        return Mission(
            id=mid,
            name=f"Bounty: Clear {kills} Hostiles",
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
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=reward),
                MissionReward(reward_type="xp", amount=xp),
            ],
        )

    def generate_delivery(self, system_id: str, game_day: int) -> Mission:
        """Generate a cargo delivery contract.

        Collect a commodity and deliver it to another system.

        Args:
            system_id: System offering the contract.
            game_day: Current game day for seeding.

        Returns:
            A delivery Mission.
        """
        rng = self._make_rng(system_id, game_day, "delivery")
        mid = self._next_id("delivery", system_id, game_day)
        dest_id = self._pick_other_system(rng, system_id)
        dest = self._systems[dest_id]
        commodity_id = self._pick_trade_commodity(rng, system_id)
        commodity = self._commodities[commodity_id]
        qty = rng.randint(3, 10)
        base_reward = int(commodity.base_price * qty * 0.5)
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
                    reward_type="remove_cargo",
                    amount=qty,
                    target_id=commodity_id,
                ),
            ],
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
        mid = self._next_id("smuggling", system_id, game_day)
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
                f"moved to {dest.name} — no questions asked. The cargo will be "
                f"loaded when you accept."
            ),
            mission_type="side",
            discovery_method="station_board",
            available_at=[system_id],
            on_accept_cargo=[AcceptCargo(commodity_id=commodity_id, quantity=qty)],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id=dest_id,
                    description=f"Deliver contraband to {dest.name}",
                ),
            ],
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
        mid = self._next_id("survey", system_id, game_day)
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
        mid = self._next_id("salvage", system_id, game_day)
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
                ),
            ],
            rewards=[
                MissionReward(reward_type="credits", amount=max(reward, 300)),
                MissionReward(reward_type="xp", amount=xp),
            ],
        )

    def generate_for_system(self, system_id: str, game_day: int) -> list[Mission]:
        """Generate 2-3 varied missions for a system's station board.

        Picks from all 5 template types, weighted by system characteristics.

        Args:
            system_id: System to generate missions for.
            game_day: Current game day.

        Returns:
            List of 2-3 generated missions.
        """
        rng = self._make_rng(system_id, game_day, "board")
        system = self._systems.get(system_id)
        if not system:
            return []

        # Weight templates by system type
        generators = [
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
            missions.append(gen_func(system_id, game_day))
        return missions
