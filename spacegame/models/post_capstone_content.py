"""A2-21: Post-capstone content generator keyed to resolved identity.

The resolved identity is the content generator (per the Act II design spec's
"After the capstone" section). Empire resolved begins the *problems of
empire*: succession, borders, a governor overreaching. Community resolved
begins scarcity and outside interest. Vengeance resolved means meeting
people who know what the player did.

This module ships the framework plus three worked-example lens templates
(``empire``, ``community``, ``vengeance``). Any lens without a template
returns ``[]`` gracefully. Determinism follows the ``galaxy_event.py``
hashlib-md5 pattern so the same day / lens / seed / state always produces
the same missions, satisfying the "no save scumming" contract from
CLAUDE.md.

The generator reads only ``player.dialogue_flags``,
``player.dilemma_state.resolved``, and ``player.capstones_reached`` -- never
``player.lens_investment``. The wiring in ``spacegame/engine/game.py``
respects the A2-4 AC4 compliance guard for the same reason.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

from spacegame.models.commodity import Commodity
from spacegame.models.mission import (
    Mission,
    MissionObjective,
    MissionReward,
    ObjectiveType,
)
from spacegame.models.system import StarSystem
from spacegame.utils.logger import logger

# Per-lens dilemma -> outcome_flag mapping. Lists (not sets) so iteration
# order is stable across runs -- essential for determinism.
_EMPIRE_GATES: list[tuple[str, str]] = [
    ("d6_preservation_empire", "d6_empire_won"),
    ("d3_power_revolution_empire", "d3_empire_won"),
]
_COMMUNITY_GATES: list[tuple[str, str]] = [
    ("d2_wealth_community", "d2_community_won"),
    ("d8_crime_community", "d8_community_won"),
]
_VENGEANCE_GATES: list[tuple[str, str]] = [
    ("d1_vengeance_justice", "d1_vengeance_won"),
    ("d4_truth_vengeance", "d4_vengeance_won"),
]


class PostCapstoneContentGenerator:
    """Generate station-board missions keyed to a player's resolved identity.

    Constructed with the same shape as
    :class:`~spacegame.models.procedural_missions.ProceduralMissionGenerator`
    plus a ``templates`` payload loaded from
    ``data/narrative/post_capstone_templates.json``. Construction closes over
    no player state; ``generate_for_lens`` reads player state per call.

    See :func:`generate_for_lens` for the per-lens dispatch contract.
    """

    def __init__(
        self,
        systems: dict[str, StarSystem],
        commodities: dict[str, Commodity],
        enemy_templates: dict[str, Any],
        templates: dict[str, list[dict[str, Any]]],
        seed: int = 0,
    ) -> None:
        """Initialize the generator.

        Args:
            systems: All star systems by id.
            commodities: All commodities by id.
            enemy_templates: Enemy templates by id (unused this sprint;
                reserved for a future encounter-shaped template).
            templates: Map of ``lens_id`` -> list of raw template dicts.
                A lens without an entry (or an empty list) yields ``[]``.
            seed: Base RNG seed used together with ``lens_id`` and
                ``game_day`` in the hashlib-md5 seeding formula.
        """
        self._systems = systems
        self._commodities = commodities
        self._enemy_templates = enemy_templates
        self._templates = templates
        self._base_seed = seed

    def generate_for_lens(
        self,
        lens_id: str,
        game_day: int,
        player: Any,
    ) -> list[Mission]:
        """Dispatch to a per-lens builder and return generated missions.

        Empty result (``[]``) is returned when any of the following holds:

        - ``player.dialogue_flags[f"{lens_id}_capstone_reached"]`` is absent
          or false (capstone not yet acknowledged).
        - ``lens_id`` is not one of the three implemented lenses.
        - No dilemma resolution in ``player.dilemma_state.resolved`` matches
          the lens's gate list (nothing to write about yet).

        Args:
            lens_id: The lens whose post-capstone content to generate.
            game_day: The current game day, seeds the RNG.
            player: Any object exposing ``dialogue_flags`` and
                ``dilemma_state`` with a ``resolved: dict[str, str]``.

        Returns:
            List of :class:`Mission` records. Never raises for unknown
            or unimplemented lens ids.
        """
        flag = f"{lens_id}_capstone_reached"
        if not player.dialogue_flags.get(flag, False):
            return []

        if lens_id == "empire":
            return self._build_for_empire(game_day, player)
        if lens_id == "community":
            return self._build_for_community(game_day, player)
        if lens_id == "vengeance":
            return self._build_for_vengeance(game_day, player)

        logger.debug(
            "PostCapstoneContentGenerator: no template implemented for lens '%s'",
            lens_id,
        )
        return []

    # ------------------------------------------------------------------
    # Per-lens builders
    # ------------------------------------------------------------------

    def _build_for_empire(self, game_day: int, player: Any) -> list[Mission]:
        outcome_flag = self._match_gate(_EMPIRE_GATES, player)
        if outcome_flag is None:
            logger.debug(
                "PostCapstoneContentGenerator: empire capstone but no empire outcome_flag resolved"
            )
            return []

        templates = self._templates.get("empire", [])
        if not templates:
            return []

        rng = self._make_rng("empire", game_day)
        target_system_id = self._pick_system(rng)
        if not target_system_id:
            return []
        system_name = self._systems[target_system_id].name
        outcome_label = self._outcome_label(outcome_flag)

        missions: list[Mission] = []
        for counter, template in enumerate(templates, start=1):
            mid = self._mission_id("empire", target_system_id, game_day, counter)
            fmt = {
                "system_name": system_name,
                "outcome_label": outcome_label,
                "outcome_flag": outcome_flag,
            }
            name = template["name_template"].format(**fmt)
            description = template["description_template"].format(**fmt)
            objectives = self._build_objectives(
                template.get("objectives", []),
                target_system_id=target_system_id,
                outcome_flag=outcome_flag,
                fmt=fmt,
            )
            missions.append(
                Mission(
                    id=mid,
                    name=name,
                    description=description,
                    mission_type="side",
                    discovery_method="station_board",
                    objectives=objectives,
                    rewards=[
                        MissionReward(reward_type="credits", amount=800),
                        MissionReward(reward_type="xp", amount=120),
                    ],
                )
            )
        return missions

    def _build_for_community(self, game_day: int, player: Any) -> list[Mission]:
        outcome_flag = self._match_gate(_COMMUNITY_GATES, player)
        if outcome_flag is None:
            logger.debug(
                "PostCapstoneContentGenerator: community capstone but no community "
                "outcome_flag resolved"
            )
            return []

        templates = self._templates.get("community", [])
        if not templates:
            return []

        rng = self._make_rng("community", game_day)
        # Community missions still use a stable target system id for id-suffix
        # variety; the settlement name is baked into the template text.
        target_system_id = self._pick_system(rng)
        if not target_system_id:
            return []
        outcome_label = self._outcome_label(outcome_flag)

        missions: list[Mission] = []
        for counter, template in enumerate(templates, start=1):
            mid = self._mission_id("community", target_system_id, game_day, counter)
            commodity_id = template.get("commodity", "food")
            quantity = int(template.get("quantity", 5))
            commodity_name = (
                self._commodities[commodity_id].name
                if commodity_id in self._commodities
                else commodity_id.replace("_", " ").title()
            )
            fmt = {
                "commodity_name": commodity_name,
                "quantity": quantity,
                "outcome_label": outcome_label,
                "outcome_flag": outcome_flag,
            }
            name = template["name_template"].format(**fmt)
            description = template["description_template"].format(**fmt)
            objectives = self._build_objectives(
                template.get("objectives", []),
                target_system_id=target_system_id,
                outcome_flag=outcome_flag,
                fmt=fmt,
                commodity_id=commodity_id,
                quantity=quantity,
            )
            missions.append(
                Mission(
                    id=mid,
                    name=name,
                    description=description,
                    mission_type="side",
                    discovery_method="station_board",
                    objectives=objectives,
                    rewards=[
                        MissionReward(reward_type="credits", amount=500),
                        MissionReward(reward_type="xp", amount=90),
                        MissionReward(
                            reward_type="remove_cargo",
                            amount=quantity,
                            target_id=commodity_id,
                        ),
                    ],
                )
            )
        return missions

    def _build_for_vengeance(self, game_day: int, player: Any) -> list[Mission]:
        outcome_flag = self._match_gate(_VENGEANCE_GATES, player)
        if outcome_flag is None:
            logger.debug(
                "PostCapstoneContentGenerator: vengeance capstone but no vengeance "
                "outcome_flag resolved"
            )
            return []

        all_templates = self._templates.get("vengeance", [])
        if not all_templates:
            return []

        # Filter to templates matching the resolved gate. Templates carry a
        # ``gate_dilemma`` field so a d1 resolution surfaces d1-specific
        # descriptions (Foss / Vert) and a d4 resolution surfaces d4-specific
        # descriptions (Senn / Ledger). Templates without ``gate_dilemma``
        # match any resolved gate.
        gate_dilemma_id = self._dilemma_for_outcome(outcome_flag, _VENGEANCE_GATES)
        templates = [
            t for t in all_templates if t.get("gate_dilemma", gate_dilemma_id) == gate_dilemma_id
        ]
        if not templates:
            return []

        rng = self._make_rng("vengeance", game_day)
        target_system_id = self._pick_system(rng)
        if not target_system_id:
            return []
        system_name = self._systems[target_system_id].name
        outcome_label = self._outcome_label(outcome_flag)

        missions: list[Mission] = []
        for counter, template in enumerate(templates, start=1):
            mid = self._mission_id("vengeance", target_system_id, game_day, counter)
            fmt = {
                "system_name": system_name,
                "outcome_label": outcome_label,
                "outcome_flag": outcome_flag,
            }
            name = template["name_template"].format(**fmt)
            description = template["description_template"].format(**fmt)
            objectives = self._build_objectives(
                template.get("objectives", []),
                target_system_id=target_system_id,
                outcome_flag=outcome_flag,
                fmt=fmt,
            )
            missions.append(
                Mission(
                    id=mid,
                    name=name,
                    description=description,
                    mission_type="side",
                    discovery_method="station_board",
                    objectives=objectives,
                    rewards=[
                        MissionReward(reward_type="credits", amount=700),
                        MissionReward(reward_type="xp", amount=110),
                    ],
                )
            )
        return missions

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_rng(self, lens_id: str, game_day: int) -> random.Random:
        """Seed an RNG deterministically across process starts.

        Follows the ``galaxy_event.py`` md5 pattern rather than ``hash()``:
        Python's ``hash()`` on strings is salted by PYTHONHASHSEED so
        ``random.Random(hash(str))`` produces different sequences across
        process invocations, which would silently break the "no save
        scumming" determinism guarantee in CLAUDE.md.
        """
        seed_str = f"{lens_id}_{game_day}_{self._base_seed}"
        seed_int = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
        return random.Random(seed_int)

    def _mission_id(
        self,
        lens_id: str,
        system_id: str,
        game_day: int,
        counter: int,
    ) -> str:
        """Compose a stable, refresh-strippable mission id.

        The prefix ``post_capstone_{lens_id}_`` mirrors ``proc_*`` so the
        engine's per-day refresh can strip stale post-capstone missions
        the same way it strips procedural ones.
        """
        return f"post_capstone_{lens_id}_{system_id}_{game_day}_{counter}"

    def _pick_system(self, rng: random.Random) -> str:
        """Pick a system id from the systems registry, sorted for determinism.

        ``rng.choice`` on the sorted list guarantees the same lens/day/seed
        picks the same system across process starts.
        """
        candidates = sorted(self._systems.keys())
        if not candidates:
            return ""
        return rng.choice(candidates)

    def _match_gate(
        self,
        gates: list[tuple[str, str]],
        player: Any,
    ) -> str | None:
        """Return the first matching outcome_flag from ``gates``.

        A gate matches when the dilemma id is in
        ``player.dilemma_state.resolved`` AND
        ``player.dialogue_flags[outcome_flag]`` is true. Both checks are
        conservative: dilemma resolve writes the outcome_flag, so the
        second check catches saves that were manually rewound.
        """
        resolved = getattr(player.dilemma_state, "resolved", {}) or {}
        flags = player.dialogue_flags
        for dilemma_id, outcome_flag in gates:
            if dilemma_id in resolved and flags.get(outcome_flag, False):
                return outcome_flag
        return None

    def _dilemma_for_outcome(
        self,
        outcome_flag: str,
        gates: list[tuple[str, str]],
    ) -> str:
        """Return the dilemma id that produced ``outcome_flag``.

        The reverse lookup is a small list scan; kept explicit rather than
        building a dict so ``_EMPIRE_GATES`` / ``_COMMUNITY_GATES`` /
        ``_VENGEANCE_GATES`` remain the one source of truth.
        """
        for dilemma_id, flag in gates:
            if flag == outcome_flag:
                return dilemma_id
        return ""

    def _outcome_label(self, outcome_flag: str) -> str:
        """Return a human-readable label for an outcome_flag.

        Used inside description templates so text can refer to "the empire
        record" or "the community standing" without hardcoding the lens id
        into every template string.
        """
        # d3_empire_won -> "empire"
        parts = outcome_flag.split("_")
        if len(parts) >= 3:
            return parts[1]
        return outcome_flag

    def _build_objectives(
        self,
        template_objectives: list[dict[str, Any]],
        *,
        target_system_id: str,
        outcome_flag: str,
        fmt: dict[str, Any],
        commodity_id: str = "",
        quantity: int = 0,
    ) -> list[MissionObjective]:
        """Convert template objective dicts into concrete MissionObjectives.

        Each template objective has a ``type`` and a ``target`` selector
        naming which piece of runtime data to plug into ``target_id``:

        - ``target_system`` -> ``target_system_id``
        - ``outcome_flag`` -> the resolved outcome_flag
        - ``commodity`` -> the template's ``commodity`` field
        """
        objectives: list[MissionObjective] = []
        for obj in template_objectives:
            obj_type = ObjectiveType(obj["type"])
            selector = obj.get("target", "")
            if selector == "target_system":
                target_id = target_system_id
            elif selector == "outcome_flag":
                target_id = outcome_flag
            elif selector == "commodity":
                target_id = commodity_id
            else:
                target_id = selector
            description = obj.get("description_template", "").format(**fmt)
            qty = quantity if obj.get("quantity_field") else 1
            objectives.append(
                MissionObjective(
                    type=obj_type,
                    target_id=target_id,
                    target_quantity=qty,
                    description=description,
                )
            )
        return objectives
