"""SA-B2: Per-round bid validation, increment scale, and snipe-window logic.

A ``RoundState`` is mutable per-round bookkeeping that lives inside the
parent ``AuctionState`` for the active lot. It tracks the current high
bid, the round phase, the seconds remaining, and whether the
once-per-round snipe-window timer reset has been used.

See ``requirements/sa_bidding_design.md`` §5 for the player input model
and §2.3 for the per-round phase order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RoundPhase(str, Enum):
    """Per-round phase per design doc §2.3.

    Values are strings so they round-trip through JSON without a custom
    encoder. The state machine progresses ``OPEN_CALL -> BID_WINDOW ->
    ROUND_CLOSE -> LOT_RESOLUTION``; ``BID_WINDOW`` is the only phase
    where bids are accepted.
    """

    OPEN_CALL = "open_call"
    BID_WINDOW = "bid_window"
    ROUND_CLOSE = "round_close"
    LOT_RESOLUTION = "lot_resolution"


# Speed setting -> (round_duration_seconds, snipe_window_seconds) per
# design doc §2.4.
SPEED_SETTINGS: dict[str, tuple[float, float]] = {
    "slow": (45.0, 5.0),
    "normal": (30.0, 5.0),
    "fast": (15.0, 3.0),
    "asap": (8.0, 2.0),
}
DEFAULT_SPEED_SETTING = "normal"

# Speed setting -> AI-timing compression factor. ``asap`` mode squeezes
# the per-round bid window to 8 s so AI counter-bids must compress
# proportionally; the other settings run at full pace.
SPEED_AI_MULTIPLIER: dict[str, float] = {
    "slow": 1.0,
    "normal": 1.0,
    "fast": 0.5,
    "asap": 0.27,  # 8 / 30 ~ 0.27 vs normal-speed timing.
}


def min_increment_for_appraisal(base_appraisal: int) -> int:
    """Return the minimum bid increment for a lot at this appraisal.

    Four-tier scale per design doc §5.2.

    Args:
        base_appraisal: Lot ``base_appraisal`` in credits.

    Returns:
        Minimum increment in credits.
    """
    if base_appraisal <= 2000:
        return 50
    if base_appraisal <= 10000:
        return 200
    if base_appraisal <= 30000:
        return 500
    return 1000


def opening_bid_for_lot(base_appraisal: int, reserve_price: int) -> int:
    """Return the opening bid floor per locked decision §11.8.

    Opening bid = ``reserve_price + min_increment_for_appraisal(base_appraisal)``.
    AI personas with ``effective_value`` below this floor sit out the lot
    entirely (handled at the AuctionState layer; this function just
    surfaces the number).
    """
    return reserve_price + min_increment_for_appraisal(base_appraisal)


@dataclass
class RoundState:
    """Mutable per-round bookkeeping.

    Attributes:
        round_number: 1-indexed round counter for the active lot. Round 1
            is the first round; standard lots run rounds 1-2, headliner
            lots run rounds 1-3.
        phase: Current :class:`RoundPhase`.
        current_high_bid: Current winning bid in credits. Starts at the
            opening floor on round 1; carries forward into round 2.
        current_high_bidder_id: Persona id of the leader, ``"player"`` if
            the player is leading, or ``None`` if no bids have landed.
        time_remaining: Seconds left in the bid window. Decremented by
            :meth:`tick`; clamped at 0.
        round_duration_seconds: Total round duration; used to reset
            ``time_remaining`` when a new round opens.
        snipe_window_seconds: Length of the snipe window in seconds.
            A bid landing in the final ``snipe_window_seconds`` triggers
            a one-time timer reset.
        snipe_reset_used: True once the snipe window has reset the timer
            this round. Subsequent snipe bids do NOT chain-extend.
        bidders_active: Set of persona ids (and ``"player"``) still
            eligible to bid. Folding removes a bidder for the lot's
            remaining rounds.
        round_min_increment: Min increment for this round, captured at
            round-open from the lot's base_appraisal.
    """

    round_number: int = 1
    phase: RoundPhase = RoundPhase.OPEN_CALL
    current_high_bid: int = 0
    current_high_bidder_id: Optional[str] = None
    time_remaining: float = 0.0
    round_duration_seconds: float = 30.0
    snipe_window_seconds: float = 5.0
    snipe_reset_used: bool = False
    bidders_active: set[str] = field(default_factory=set)
    round_min_increment: int = 50

    # ------------------------------------------------------------------
    # Round lifecycle
    # ------------------------------------------------------------------

    def open_round(
        self,
        round_number: int,
        round_duration_seconds: float,
        snipe_window_seconds: float,
        round_min_increment: int,
    ) -> None:
        """Reset the round state for a new round."""
        self.round_number = round_number
        self.phase = RoundPhase.BID_WINDOW
        self.time_remaining = round_duration_seconds
        self.round_duration_seconds = round_duration_seconds
        self.snipe_window_seconds = snipe_window_seconds
        self.snipe_reset_used = False
        self.round_min_increment = round_min_increment

    def tick(self, dt: float) -> None:
        """Advance the round timer.

        Clamps to 0; transitions ``BID_WINDOW`` to ``ROUND_CLOSE`` when
        the timer expires. Caller is responsible for triggering lot
        resolution after the round closes.
        """
        if self.phase != RoundPhase.BID_WINDOW:
            return
        self.time_remaining = max(0.0, self.time_remaining - dt)
        if self.time_remaining <= 0.0:
            self.phase = RoundPhase.ROUND_CLOSE

    # ------------------------------------------------------------------
    # Bid validation
    # ------------------------------------------------------------------

    def submit_bid(self, bidder_id: str, amount: int) -> tuple[bool, str]:
        """Validate and apply a bid.

        Returns ``(True, message)`` on success or ``(False, message)`` on
        failure. The caller is expected to display the message in the
        feedback area.

        Args:
            bidder_id: ``"player"`` or a persona id.
            amount: Total bid in credits.
        """
        if self.phase != RoundPhase.BID_WINDOW:
            return (False, "Bidding is closed for this round.")
        if bidder_id == self.current_high_bidder_id:
            return (False, "You are already the high bidder.")
        if bidder_id not in self.bidders_active:
            return (False, "You have folded on this lot.")
        min_required = self.current_high_bid + self.round_min_increment
        if amount < min_required:
            return (
                False,
                f"Bid must be at least {min_required:,} credits.",
            )
        previous_bidder = self.current_high_bidder_id
        self.current_high_bid = amount
        self.current_high_bidder_id = bidder_id
        # Snipe-window check: if this bid lands inside the final
        # snipe_window_seconds and the reset has not been used, extend
        # the timer.
        snipe_triggered = False
        if not self.snipe_reset_used and self.time_remaining < self.snipe_window_seconds:
            self.time_remaining = self.snipe_window_seconds
            self.snipe_reset_used = True
            snipe_triggered = True
        msg = f"{bidder_id} now leads at {amount:,} credits."
        if snipe_triggered:
            msg += " Snipe window: timer reset."
        if previous_bidder is not None:
            msg += f" (Outbid: {previous_bidder}.)"
        return (True, msg)

    def fold(self, bidder_id: str) -> tuple[bool, str]:
        """Withdraw a bidder from the rest of the lot.

        Folding is a permanent action for the active lot. Returns
        ``(False, msg)`` if the bidder was not active.
        """
        if bidder_id not in self.bidders_active:
            return (False, "Bidder is not active on this lot.")
        self.bidders_active.discard(bidder_id)
        return (True, f"{bidder_id} has folded.")

    # ------------------------------------------------------------------
    # Snipe queries
    # ------------------------------------------------------------------

    def is_in_snipe_window(self) -> bool:
        """True if the current ``time_remaining`` is inside the snipe window."""
        return (
            self.phase == RoundPhase.BID_WINDOW and self.time_remaining < self.snipe_window_seconds
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "phase": self.phase.value,
            "current_high_bid": self.current_high_bid,
            "current_high_bidder_id": self.current_high_bidder_id,
            "time_remaining": self.time_remaining,
            "round_duration_seconds": self.round_duration_seconds,
            "snipe_window_seconds": self.snipe_window_seconds,
            "snipe_reset_used": self.snipe_reset_used,
            "bidders_active": sorted(self.bidders_active),
            "round_min_increment": self.round_min_increment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoundState":
        phase_value = data.get("phase", RoundPhase.OPEN_CALL.value)
        try:
            phase = RoundPhase(phase_value)
        except ValueError:
            phase = RoundPhase.OPEN_CALL
        return cls(
            round_number=int(data.get("round_number", 1)),
            phase=phase,
            current_high_bid=int(data.get("current_high_bid", 0)),
            current_high_bidder_id=data.get("current_high_bidder_id"),
            time_remaining=float(data.get("time_remaining", 0.0)),
            round_duration_seconds=float(data.get("round_duration_seconds", 30.0)),
            snipe_window_seconds=float(data.get("snipe_window_seconds", 5.0)),
            snipe_reset_used=bool(data.get("snipe_reset_used", False)),
            bidders_active=set(data.get("bidders_active", [])),
            round_min_increment=int(data.get("round_min_increment", 50)),
        )


__all__ = [
    "DEFAULT_SPEED_SETTING",
    "SPEED_AI_MULTIPLIER",
    "SPEED_SETTINGS",
    "RoundPhase",
    "RoundState",
    "min_increment_for_appraisal",
    "opening_bid_for_lot",
]
