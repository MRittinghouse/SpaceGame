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

- SL-3 will extend this module with `get_recommended_card` for the
  cyan-glow highlight (reusing the cantina PT-016 pattern).

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

from typing import TYPE_CHECKING, Optional

from spacegame.constants.flags import investment_introduced

if TYPE_CHECKING:
    from spacegame.models.mission import MissionManager
    from spacegame.models.player import Player


# SL-2 lifetime-credits floor for investment-card visibility.
# Locked at 25,000 CR per requirements/station_legibility.md (2026-04-26).
# Tunable in playtest if needed.
INVESTMENT_UNLOCK_CREDIT_THRESHOLD: int = 25_000


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
