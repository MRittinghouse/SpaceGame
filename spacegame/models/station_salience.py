"""Station salience — which cards deserve highlighting at a station.

Per `requirements/station_legibility.md`:

- SL-1 introduces `is_system_mission_relevant` for `unique`-card demotion.
  When a system has any active mission objective, all `unique`-typed
  locations at that system stay in the main action grid; otherwise they
  demote to the POI footer strip.

- SL-2 introduces `is_investment_unlocked` for `investment`-card gating.
  Investment cards do not render until the player crosses a credit
  threshold OR has been introduced to investment via the Cargo-Broker
  mission (sets the `investment_introduced` flag).

- SL-3 introduces `get_recommended_card` for the cyan-glow highlight
  (reusing the cantina PT-016 pattern). Pure function over a hierarchy:
  mission objective > damaged hull > empty cargo > faction-first-visit
  > resource opportunity > investment unlocked. First match wins.

Mission objectives target *systems* (REACH_SYSTEM) or NPCs
(TALK_TO_NPC, which resolves to the NPC's home system). No objective
type targets a sub-station location ID, per data audit 2026-04-26. So
mission relevance is evaluated at the system level, and ALL `unique`
locations at a mission-relevant system are elevated together. This
matches the design intent of station_legibility.md (Fulcrum case: when
the player docks at the_fulcrum due to a campaign mission, fulcrum_core
is contextually elevated alongside any other unique cards there).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from spacegame.constants.flags import investment_introduced

if TYPE_CHECKING:
    from spacegame.models.location import Location
    from spacegame.models.mission import MissionManager
    from spacegame.models.player import Player


# SL-2 lifetime-credits floor for investment-card visibility.
# Locked at 25,000 CR per requirements/station_legibility.md (2026-04-26).
# Tunable in playtest if needed.
INVESTMENT_UNLOCK_CREDIT_THRESHOLD: int = 25_000

# SL-3 hull-damage threshold below which the repair_bay card is
# recommended. Strict less-than: hull exactly at 70% is healthy enough.
DAMAGED_HULL_THRESHOLD: float = 0.7


class RecommendationSource(Enum):
    """Why `get_recommended_card` chose a card.

    Drives the highlight color in the view layer per SL-3:
      - MISSION_OBJECTIVE: cyan glow (matches cantina PT-016 semantic —
        "the campaign points here")
      - RECOMMENDATION: the card's own accent color (the card itself is
        calling to the player based on heuristic state)
    """

    MISSION_OBJECTIVE = "mission_objective"
    RECOMMENDATION = "recommendation"


def is_system_mission_relevant(
    mission_manager: Optional["MissionManager"],
    system_id: str,
    npc_home_systems: Optional[dict[str, str]] = None,
) -> bool:
    """Return True if any active mission has an objective at this system.

    Used by `station_layouts.py` to decide whether `unique`-typed location
    cards stay in the main action grid (mission-relevant) or demote to
    the POI footer strip (lore-only).

    Args:
        mission_manager: The active MissionManager, or None when missions
            haven't been wired (tutorial states, dev launches, tests).
        system_id: The system to check.
        npc_home_systems: Optional mapping of NPC ID to home system ID,
            used to resolve TALK_TO_NPC objectives. When omitted,
            TALK_TO_NPC objectives are ignored.

    Returns:
        True if the system has at least one active mission objective.
    """
    if mission_manager is None:
        return False
    return system_id in mission_manager.get_active_target_systems(npc_home_systems)


def is_investment_unlocked(
    player: "Player",
    threshold: int = INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
) -> bool:
    """Return True if `investment`-typed location cards should render.

    SL-2 (station_legibility.md): two OR'd gates. Either suffices.

    1. Lifetime credits earned (``player.credits_earned_lifetime``) crosses
       ``threshold`` — the player has demonstrably moved enough capital to
       have surplus to invest. Default 25,000 CR.
    2. The ``investment_introduced`` dialogue flag (see
       :func:`spacegame.constants.flags.investment_introduced`) is set —
       the Cargo-Broker mission has fired and explicitly introduced the
       system, regardless of credit balance.

    The threshold is the floor; the flag is the introduction. A player
    who crosses the threshold without the mission firing still sees the
    cards (silent unlock). A player who completes the introductory
    mission with low credits still sees the cards (mission-driven unlock).

    Args:
        player: Current player. Reads ``credits_earned_lifetime`` and
            ``dialogue_flags`` only.
        threshold: Lifetime-credits floor. Defaults to the locked SL-2
            value; pass an override for tests or playtest tuning.

    Returns:
        True if either gate is met. Investment cards render in the
        station hub view's action grid. False means the cards are
        filtered out of the layout entirely.
    """
    if player.credits_earned_lifetime >= threshold:
        return True
    return bool(player.dialogue_flags.get(investment_introduced(), False))


def _max_hull(ship: object) -> int:
    """Return the ship's effective max hull. Mirrors Ship's own logic."""
    cs = getattr(ship, "computed_stats", None)
    if cs is not None and getattr(cs, "hull", 0) > 0:
        return cs.hull
    return ship.ship_type.combat_hull


def _first_loc_of_type(locations: list, location_type: str) -> Optional[str]:
    """Return the first location ID of a given type, or None."""
    for loc in locations:
        if loc.location_type == location_type:
            return loc.id
    return None


def get_recommended_card(
    player: "Player",
    system_id: str,
    faction_id: str,
    locations: list["Location"],
    mission_manager: Optional["MissionManager"],
    npc_home_systems: Optional[dict[str, str]] = None,
    faction_systems: Optional[dict[str, set[str]]] = None,
    hull_damage_threshold: float = DAMAGED_HULL_THRESHOLD,
    investment_threshold: int = INVESTMENT_UNLOCK_CREDIT_THRESHOLD,
) -> Optional[tuple[str, RecommendationSource]]:
    """Return the location ID to highlight at this station, or None.

    SL-3 hierarchy (first match wins):

    1. **Mission objective** (MISSION_OBJECTIVE source). An active
       TALK_TO_NPC objective whose NPC's home system is here. Highlights
       the cantina (NPCs live in cantinas). REACH_SYSTEM objectives are
       not highlighted because the player has already arrived; the
       objective auto-completes on dock.
    2. **Damaged hull** (RECOMMENDATION). Hull below
       ``hull_damage_threshold`` (default 0.7) and station has a
       repair_bay. Strict less-than: hull at exactly the threshold is
       healthy enough.
    3. **Empty cargo** (RECOMMENDATION). Player carries no commodities
       and station has a market. Suggests the player should buy
       something to start trading.
    4. **First-faction visit** (RECOMMENDATION). The player has visited
       no other system in this faction's territory and the station has
       a cantina — an NPC there can introduce the faction. Requires
       ``faction_systems`` to map faction_id to its system IDs.
    5. **Resource opportunity** (RECOMMENDATION). Station has mining or
       salvaging — direct gameplay loop available. Mining is preferred
       over salvaging when both are present (rare; today only Forgeworks
       has both, and it doesn't have mining).
    6. **Investment** (RECOMMENDATION). Investment is unlocked
       (threshold or flag) and station has an investment card.
    7. **None**. No conditions match.

    The function is pure and reads existing state only — no model
    mutation, no side effects.

    Args:
        player: Current player. Reads ship hull, cargo, lifetime credits,
            systems_visited, and dialogue_flags.
        system_id: The station's system ID.
        faction_id: The faction controlling this system.
        locations: Locations available at this station (already filtered
            by SL-2's investment gate where applicable).
        mission_manager: Active MissionManager, or None when missions
            haven't been wired (tutorial states, dev launches).
        npc_home_systems: Optional NPC ID → home system ID mapping.
            Required for the mission-objective branch (TALK_TO_NPC).
        faction_systems: Optional faction ID → set of its system IDs
            mapping. Required for the faction-first-visit branch.
        hull_damage_threshold: Strict hull-fraction floor for the
            repair-recommendation branch. Default 0.7.
        investment_threshold: Lifetime-credits floor for the investment
            branch. Default 25,000 CR.

    Returns:
        ``(location_id, RecommendationSource)`` tuple, or None if no
        branch matches.
    """
    # 1. Mission objective — TALK_TO_NPC at an NPC living here
    if mission_manager is not None and npc_home_systems:
        cantina_id = _first_loc_of_type(locations, "cantina")
        if cantina_id is not None:
            target_systems = mission_manager.get_active_target_systems(npc_home_systems)
            # Specifically check that the system match comes from a
            # TALK_TO_NPC objective (REACH_SYSTEM matches don't suggest
            # a card to highlight).
            if system_id in target_systems and _has_talk_to_npc_objective_at(
                mission_manager, system_id, npc_home_systems
            ):
                return (cantina_id, RecommendationSource.MISSION_OBJECTIVE)

    # 2. Damaged hull
    max_hp = _max_hull(player.ship)
    if max_hp > 0 and (player.ship.current_hull / max_hp) < hull_damage_threshold:
        repair_id = _first_loc_of_type(locations, "repair_bay")
        if repair_id is not None:
            return (repair_id, RecommendationSource.RECOMMENDATION)

    # 3. Empty cargo + market
    if not player.ship.current_cargo:
        market_id = _first_loc_of_type(locations, "market")
        if market_id is not None:
            return (market_id, RecommendationSource.RECOMMENDATION)

    # 4. First-faction visit
    if faction_systems is not None:
        same_faction = faction_systems.get(faction_id, set())
        # Subtract this system from visited; if any others in the faction
        # are visited, this isn't a first-visit.
        prior_in_faction = (player.systems_visited & same_faction) - {system_id}
        if not prior_in_faction:
            cantina_id = _first_loc_of_type(locations, "cantina")
            if cantina_id is not None:
                return (cantina_id, RecommendationSource.RECOMMENDATION)

    # 5. Resource opportunity (mining or salvaging)
    for resource_type in ("mining", "salvaging"):
        resource_id = _first_loc_of_type(locations, resource_type)
        if resource_id is not None:
            return (resource_id, RecommendationSource.RECOMMENDATION)

    # 6. Investment
    if is_investment_unlocked(player, threshold=investment_threshold):
        invest_id = _first_loc_of_type(locations, "investment")
        if invest_id is not None:
            return (invest_id, RecommendationSource.RECOMMENDATION)

    return None


def _has_talk_to_npc_objective_at(
    mission_manager: "MissionManager",
    system_id: str,
    npc_home_systems: dict[str, str],
) -> bool:
    """Return True if any active mission has a TALK_TO_NPC objective whose
    NPC is at ``system_id``.

    Distinct from the broader ``get_active_target_systems`` check —
    that one includes REACH_SYSTEM matches, which don't suggest a card.
    """
    from spacegame.models.mission import MissionStatus, ObjectiveType

    for mid, mission in mission_manager._missions.items():
        if mission_manager._status[mid] != MissionStatus.ACTIVE:
            continue
        progress = mission_manager._progress.get(mid, [])
        for i, obj in enumerate(mission.objectives):
            if i < len(progress) and progress[i]:
                continue  # already complete
            if obj.type != ObjectiveType.TALK_TO_NPC:
                continue
            if npc_home_systems.get(obj.target_id) == system_id:
                return True
    return False
