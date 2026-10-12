"""Odom's iron ore job: its state, sensors, clock and close (BB-1, BB-4; polish design 2.2).

The campaign never waits on the errand. ``iron_delivery_moved_on`` says it has moved on: the
delivery's reward sets it, the close sets it, the exit after the offer's decline sets it, and
``on_clock`` sets it at the first landing or rest on or after the day the job's late tier
begins (accept day + 19), or from day 20 for a captain who holds the bill of landing and never
took the job. ``iron_delivery_resolved`` says the job itself is over.

Odom reads records, never motives. A sale that draws his consigned ore while the job is open
sets ``broker_ore_sold`` (``note_sale``); a defeat whose losses draw it sets
``broker_ore_lost`` (``note_defeat``). The engine names the job's state in one of ten flags
(``refresh_state``), which Odom's and the intake clerk's replies read: as a dialogue opens,
after the close at its exit, and at the clock. The close (``close_on_exit``) fails the job
after the betrayal or a no-fault close and takes back the consigned ore still aboard; the
clock files a sale on record from the late tier, without the captain present.

Python keeps counts, so Odom's ten units are the job's accept cargo reserved through
``MissionManager.reserved_units``, and a sale or a defeat draws them when it leaves fewer than
ten held (both holds). Hiding them is refused (``hidable``), so the state table's rule that an
open job holds fewer than ten only after a sale or a loss holds here too. The Godot port
mirrors these rules (plan W3a-A).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from spacegame.constants.flags import (
    broker_ore_lost,
    broker_ore_sold,
    iron_delivery_closed,
    iron_delivery_failed,
    iron_delivery_moved_on,
    iron_delivery_resolved,
    iron_job_done_clean,
    iron_job_done_made_good,
    iron_job_done_replaced,
    iron_job_done_short,
    iron_job_full,
    iron_job_gone_lost,
    iron_job_made_good,
    iron_job_moved,
    iron_job_replaced,
    iron_job_short_lost,
    iron_ore_signed_short,
)
from spacegame.models.mission import MissionStatus, held_units
from spacegame.utils.logger import logger

if TYPE_CHECKING:
    from spacegame.models.mission import Mission, MissionManager
    from spacegame.models.player import Player

MISSION = "iron_delivery"
ORE = "iron_ore"
PERMIT_MISSION = "bill_of_landing"
BROKER = "odom_broker"
CLERK = "forgeworks_clerk"
CONSIGNED = 10
GUILD = "commerce_guild"
FILING_STANDING = -10
# The earliest day a captain can take the job: Larsen issues the permit on day 1.
FIRST_DAY = 1

FAILED_LINE = "Mission Failed: Iron Ore Delivery"
CLOSED_LINE = "Job Closed: Iron Ore Delivery"
TAKEN_BACK_LINE = "Odom's crew took back {units} Iron Ore"
FILING_LINE = (
    "Nexus Prime cargo office, Odom's register: consigned iron ore, ten units, sold on a Guild "
    "trading floor under your permit. Freight violation filed."
)
HIDE_REFUSED = "Consigned ore stays in the main hold."

# The ten state flags, open states first, in the table's order (polish design 2.2 rule 3).
OPEN_STATES: tuple[str, ...] = (
    iron_job_full(),
    iron_job_made_good(),
    iron_job_replaced(),
    iron_job_short_lost(),
    iron_job_gone_lost(),
    iron_job_moved(),
)
DONE_STATES: tuple[str, ...] = (
    iron_job_done_replaced(),
    iron_job_done_short(),
    iron_job_done_made_good(),
    iron_job_done_clean(),
)
STATE_FLAGS: tuple[str, ...] = OPEN_STATES + DONE_STATES

# Flags this module writes (``iron_delivery``'s reward also sets ``iron_delivery_moved_on``);
# the content scanners read this list (polish design 2.7).
ENGINE_FLAGS: tuple[str, ...] = (
    broker_ore_sold(),
    broker_ore_lost(),
    iron_delivery_moved_on(),
    *STATE_FLAGS,
)

# Who can close the open job in each state (polish design 6.1): the clerk while the ore can
# be weighed, Odom while he can close it.
_CLOSERS: tuple[tuple[str, frozenset[str]], ...] = (
    (iron_job_full(), frozenset({CLERK})),
    (iron_job_made_good(), frozenset({CLERK})),
    (iron_job_replaced(), frozenset({CLERK})),
    (iron_job_short_lost(), frozenset({CLERK, BROKER})),
    (iron_job_gone_lost(), frozenset({BROKER})),
    (iron_job_moved(), frozenset({BROKER})),
)


@dataclass(frozen=True)
class IronNotice:
    """What a close or a clock tick did: the lines to post and the flags it set.

    Attributes:
        lines: Notices for the captain, in order.
        flags: The flags this call wrote, so the caller can mirror them into a second store.
    """

    lines: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.lines or self.flags)


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


def state_of(manager: "MissionManager", player: "Player", flags: Mapping[str, bool]) -> str:
    """The job's state flag (polish design 2.2 rule 3), or "" when the job is not open or done.

    H is the iron ore held (both holds, the captain's own included: the scale doesn't read
    names), S ``broker_ore_sold``, L ``broker_ore_lost``, Sh ``iron_ore_signed_short``. A sale
    dominates a loss. An open job holding fewer than ten with neither S nor L cannot arise;
    meeting it logs an error and names no state.

    Args:
        manager: The mission manager.
        player: The player, for the ore held.
        flags: The player's dialogue flags.

    Returns:
        One of ``STATE_FLAGS``, or "".
    """
    status = manager.get_status(MISSION)
    sold = flags.get(broker_ore_sold(), False)
    lost = flags.get(broker_ore_lost(), False)
    if status == MissionStatus.ACTIVE:
        held = held_units(player, ORE)
        if sold:
            return iron_job_replaced() if held >= CONSIGNED else iron_job_moved()
        if held >= CONSIGNED:
            return iron_job_made_good() if lost else iron_job_full()
        if lost:
            return iron_job_short_lost() if held > 0 else iron_job_gone_lost()
        logger.error(f"Iron job open with {held} ore and neither a sale nor a loss on record")
        return ""
    if status == MissionStatus.COMPLETED:
        if sold:
            return iron_job_done_replaced()
        if flags.get(iron_ore_signed_short(), False):
            return iron_job_done_short()
        return iron_job_done_made_good() if lost else iron_job_done_clean()
    return ""


def refresh_state(
    manager: "MissionManager", player: "Player", flags: MutableMapping[str, bool]
) -> tuple[str, ...]:
    """Write the job's state: exactly one state flag true, writing only values that change.

    Args:
        manager: The mission manager.
        player: The player.
        flags: The player's dialogue flags, written in place.

    Returns:
        The flags written, so the caller can mirror them into a second store.
    """
    state = state_of(manager, player, flags)
    written: list[str] = []
    for name in STATE_FLAGS:
        wanted = name == state
        if flags.get(name, False) != wanted:
            flags[name] = wanted
            written.append(name)
    return tuple(written)


def closers(flags: Mapping[str, bool]) -> frozenset[str]:
    """The NPCs who can close the open job in its stored state (polish design 6.1).

    Args:
        flags: The player's dialogue flags.

    Returns:
        NPC ids, or an empty set when no open state is stored.
    """
    for state, npcs in _CLOSERS:
        if flags.get(state, False):
            return npcs
    return frozenset()


def hidable(manager: Optional["MissionManager"], player: "Player", commodity_id: str) -> int:
    """How many units of a good in the main hold may move to the hidden compartment.

    Odom's consigned ore stays in the main hold while the job is open: of the iron ore, only
    the main hold's units above the reserved count may be hidden.

    Args:
        manager: The mission manager, or None.
        player: The player.
        commodity_id: The good to hide.

    Returns:
        The units that may be hidden.
    """
    main = player.ship.get_cargo_quantity(commodity_id)
    if commodity_id != ORE or manager is None:
        return main
    if manager.get_status(MISSION) != MissionStatus.ACTIVE:
        return main
    return max(0, main - manager.reserved_units(ORE))


def moved_on_due(manager: "MissionManager", flags: Mapping[str, bool], game_day: int) -> bool:
    """Whether the campaign should stop waiting on the iron job now.

    True when the flag is unset and: the job is open and its late tier has begun, counted
    from day 1 when no accept day was recorded; or the captain holds the bill of landing,
    never took the job, and day 20 has come. A settled job is left to the flag its own
    ending set (the delivery's reward or the close).

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
        return game_day >= _late_day(manager, offset)
    if status not in (MissionStatus.UNAVAILABLE, MissionStatus.AVAILABLE):
        return False
    holds_permit = manager.get_status(PERMIT_MISSION) == MissionStatus.COMPLETED
    return holds_permit and game_day >= FIRST_DAY + offset


def filing_due(
    manager: "MissionManager", player: "Player", flags: Mapping[str, bool], game_day: int
) -> bool:
    """Whether Odom files a sale on record now (polish design 2.2 rule 6, outcome O7b).

    True when the job is open in the moved state (a sale, fewer than ten held) and its late
    tier has begun. A sale covered back to ten is not filed: that captain can still deliver.

    Args:
        manager: The mission manager.
        player: The player.
        flags: The player's dialogue flags.
        game_day: The current game day.

    Returns:
        Whether to file.
    """
    mission = manager.get_mission(MISSION)
    if mission is None or manager.get_status(MISSION) != MissionStatus.ACTIVE:
        return False
    offset = late_tier_offset(mission)
    if offset is None or game_day < _late_day(manager, offset):
        return False
    return state_of(manager, player, flags) == iron_job_moved()


def on_clock(
    manager: "MissionManager", player: "Player", flags: MutableMapping[str, bool], game_day: int
) -> IronNotice:
    """Run the job's clock at a landing or a rest: file a sale on record, or move on.

    Filing fails the job (``iron_delivery_failed``), takes back the consigned ore still
    aboard, costs Commerce Guild standing and posts the register's notice; it also settles
    the job's two flags. Otherwise the clock sets ``iron_delivery_moved_on`` when it is due.

    Args:
        manager: The mission manager.
        player: The player, for the take-back and the standing.
        flags: The player's dialogue flags, written in place.
        game_day: The current game day.

    Returns:
        What the tick did.
    """
    if filing_due(manager, player, flags, game_day):
        manager.fail_mission(MISSION)
        flags[iron_delivery_failed()] = True
        taken = take_back(player)
        player.modify_reputation(GUILD, FILING_STANDING)
        lines = (FAILED_LINE, *_taken_lines(taken), FILING_LINE)
        return IronNotice(lines, (iron_delivery_failed(), *_settle(flags)))
    if moved_on_due(manager, flags, game_day):
        flags[iron_delivery_moved_on()] = True
        return IronNotice((), (iron_delivery_moved_on(),))
    return IronNotice()


def close_on_exit(
    manager: "MissionManager", player: "Player", flags: MutableMapping[str, bool]
) -> IronNotice:
    """At a dialogue's exit: close an open job, or let a declined offer move the campaign on.

    The betrayal (``iron_delivery_failed``) and a no-fault close (``iron_delivery_closed``,
    a hand-back or a write-off) fail the open job, take back up to ten ore still aboard and
    settle the job's two flags. A decline at the offer sets ``iron_delivery_resolved`` with
    no job open; the exit then moves the campaign on.

    Args:
        manager: The mission manager.
        player: The player, for the take-back.
        flags: The player's dialogue flags, written in place.

    Returns:
        What the exit did.
    """
    failed = flags.get(iron_delivery_failed(), False)
    closed = flags.get(iron_delivery_closed(), False)
    if manager.get_status(MISSION) == MissionStatus.ACTIVE and (failed or closed):
        manager.fail_mission(MISSION)
        taken = take_back(player)
        lines = (FAILED_LINE if failed else CLOSED_LINE, *_taken_lines(taken))
        return IronNotice(lines, _settle(flags))
    if flags.get(iron_delivery_resolved(), False) and not flags.get(
        iron_delivery_moved_on(), False
    ):
        flags[iron_delivery_moved_on()] = True
        return IronNotice((), (iron_delivery_moved_on(),))
    return IronNotice()


def take_back(player: "Player") -> int:
    """Odom's dock crew takes back up to ten iron ore from the main hold.

    Args:
        player: The player.

    Returns:
        The units taken.
    """
    units = min(player.ship.get_cargo_quantity(ORE), CONSIGNED)
    if units > 0:
        player.ship.remove_cargo(ORE, units)
    return units


def note_sale(
    manager: "MissionManager",
    flags: MutableMapping[str, bool],
    commodity_id: str,
    held_before: int,
    quantity: int,
) -> bool:
    """Record a sale that drew Odom's consigned ore while the job is open (BB-1).

    The captain's own ore goes first, so a sale draws the consignment only when it sells
    more than the units above the reserved count, which is a sale that leaves fewer than
    ten held. Units in the hidden compartment are held (``held_units``). A fight's loss is
    not a sale and records nothing here.

    Args:
        manager: The mission manager.
        flags: The player's dialogue flags, written in place.
        commodity_id: The good sold.
        held_before: The units held before the sale, the hidden compartment's included.
        quantity: The units sold.

    Returns:
        Whether this sale drew the consignment.
    """
    if commodity_id != ORE or manager.get_status(MISSION) != MissionStatus.ACTIVE:
        return False
    if quantity <= held_before - manager.reserved_units(ORE):
        return False
    if not flags.get(broker_ore_sold(), False):
        flags[broker_ore_sold()] = True
    return True


def note_defeat(
    manager: "MissionManager", flags: MutableMapping[str, bool], held_before: int, held_after: int
) -> bool:
    """Record a defeat whose losses drew Odom's consigned ore while the job is open.

    The captain's own ore goes first, so a defeat draws the consignment only when it leaves
    fewer than ten held: ten to seven is a loss of his; twenty to fourteen is not.

    Args:
        manager: The mission manager.
        flags: The player's dialogue flags, written in place.
        held_before: The iron ore held before the defeat (both holds).
        held_after: The iron ore held after it.

    Returns:
        Whether this defeat drew the consignment.
    """
    if manager.get_status(MISSION) != MissionStatus.ACTIVE or held_after >= held_before:
        return False
    if held_after >= manager.reserved_units(ORE):
        return False
    if not flags.get(broker_ore_lost(), False):
        flags[broker_ore_lost()] = True
    return True


def _late_day(manager: "MissionManager", offset: int) -> int:
    accepted = manager.get_accepted_day(MISSION)
    return (accepted if accepted is not None else FIRST_DAY) + offset


def _settle(flags: MutableMapping[str, bool]) -> tuple[str, ...]:
    """Set the job's two end flags (rule 4); return the ones written."""
    written: list[str] = []
    for name in (iron_delivery_resolved(), iron_delivery_moved_on()):
        if not flags.get(name, False):
            flags[name] = True
            written.append(name)
    return tuple(written)


def _taken_lines(units: int) -> tuple[str, ...]:
    return (TAKEN_BACK_LINE.format(units=units),) if units else ()
