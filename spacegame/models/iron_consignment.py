"""Odom's iron ore job: the campaign's clock and the close (bug bash BB-1, BB-4).

The campaign never waits on the errand. ``iron_delivery_moved_on`` says it has moved on:
the delivery's reward sets it, ``close_on_exit`` sets it when the betrayal fails the job
at a dialogue's exit, and ``on_clock`` sets it at the first landing or rest on or after
the day the job's late tier begins (accept day + 19), or from day 20 for a captain who
holds the bill of landing and never took the job. The job itself stays open and payable;
the clock fails nothing (the "drift, not fail" pillar, polish design choice 2).

Python keeps counts, so Odom's ten units are the job's accept cargo reserved through
``MissionManager.reserved_units``. The Godot port mirrors these rules (plan B2).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import TYPE_CHECKING, Optional

from spacegame.constants.flags import iron_delivery_failed, iron_delivery_moved_on
from spacegame.models.mission import MissionStatus

if TYPE_CHECKING:
    from spacegame.models.mission import Mission, MissionManager

MISSION = "iron_delivery"
ORE = "iron_ore"
PERMIT_MISSION = "bill_of_landing"
# The earliest day a captain can take the job: Larsen issues the permit on day 1.
FIRST_DAY = 1


def late_tier_offset(mission: "Mission") -> Optional[int]:
    """Days from the accept to the first day of the mission's late tier.

    The late multiplier applies once more days than the partial window have passed, so
    the first late day is ``partial_reward_day_count + 1`` days after the accept (19 for
    the iron job, whose windows are 14 and 18 days).

    Args:
        mission: The mission.

    Returns:
        The offset in days, or None for a mission without a soft deadline.
    """
    if mission.soft_deadline is None:
        return None
    return mission.soft_deadline.partial_reward_day_count + 1


def moved_on_due(manager: "MissionManager", flags: Mapping[str, bool], game_day: int) -> bool:
    """Whether the campaign should stop waiting on the iron job now.

    True when the flag is unset and: the job is open and its late tier has begun, counted
    from day 1 when no accept day was recorded; or the captain holds the bill of landing,
    never took the job, and day 20 has come. A settled job is left to the flag its own
    ending set (the delivery's reward or ``close_on_exit``).

    Args:
        manager: The mission manager.
        flags: The player's dialogue flags.
        game_day: The current game day.

    Returns:
        Whether to set ``iron_delivery_moved_on``.
    """
    if flags.get(iron_delivery_moved_on(), False):
        return False
    mission = manager.get_mission(MISSION)
    status = manager.get_status(MISSION)
    if mission is None or status is None:
        return False
    offset = late_tier_offset(mission)
    if offset is None:
        return False
    if status == MissionStatus.ACTIVE:
        accepted = manager.get_accepted_day(MISSION)
        start = accepted if accepted is not None else FIRST_DAY
        return game_day >= start + offset
    if status not in (MissionStatus.UNAVAILABLE, MissionStatus.AVAILABLE):
        return False
    holds_permit = manager.get_status(PERMIT_MISSION) == MissionStatus.COMPLETED
    return holds_permit and game_day >= FIRST_DAY + offset


def on_clock(manager: "MissionManager", flags: MutableMapping[str, bool], game_day: int) -> bool:
    """Run the job's clock at a landing or a rest; set the flag when it is due.

    Args:
        manager: The mission manager.
        flags: The player's dialogue flags, written in place.
        game_day: The current game day.

    Returns:
        Whether the flag was set now.
    """
    if not moved_on_due(manager, flags, game_day):
        return False
    flags[iron_delivery_moved_on()] = True
    return True


def close_on_exit(manager: "MissionManager", flags: MutableMapping[str, bool]) -> bool:
    """At a dialogue's exit, the betrayal fails an open job and the campaign moves on.

    Args:
        manager: The mission manager.
        flags: The player's dialogue flags, written in place.

    Returns:
        True only when this call failed the job, so the caller posts its notice once.
    """
    if not flags.get(iron_delivery_failed(), False):
        return False
    if manager.get_status(MISSION) != MissionStatus.ACTIVE:
        return False
    manager.fail_mission(MISSION)
    flags[iron_delivery_moved_on()] = True
    return True
