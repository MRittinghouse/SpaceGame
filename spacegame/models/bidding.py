"""SA-B2: Auction lifecycle state machine.

``AuctionState`` lives as a field on ``Player`` and runs the venue-
agnostic auction loop: schedule -> preview -> session open -> per-lot
ascending-bid rounds -> session close. The view layer drives ``tick``
and ``submit_bid`` directly; AI counter-bidding fires inside ``tick``.

All randomness is seeded from the active session id so saves and tests
both reproduce the same outcomes deterministically.

See ``requirements/sa_bidding_design.md`` §2 (lifecycle), §3 (lot pool),
§4 (AI), §6 (captain memory), §7 (crew/skill bonuses), §8 (save schema),
§9 (hooks).
"""

from __future__ import annotations

import hashlib
import random
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional

from spacegame.models.bidding_lot import (
    REP_TIER_REGULAR,
    VENUE_STELLARIS,
    AuctionLot,
)
from spacegame.models.bidding_persona import (
    NAMED_RIVAL_IDS,
    SALKO_ESCALATION_WINDOW,
    AIBidderPersona,
)
from spacegame.models.bidding_round import (
    DEFAULT_SPEED_SETTING,
    SPEED_AI_MULTIPLIER,
    SPEED_SETTINGS,
    RoundPhase,
    RoundState,
    min_increment_for_appraisal,
    opening_bid_for_lot,
)

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only.
    from spacegame.models.captain_memory import CaptainMemory


class AuctionLifecycle(str, Enum):
    """Top-level auction lifecycle per design doc §2.6."""

    SCHEDULED = "scheduled"
    PREVIEW = "preview"
    SESSION_OPEN = "session_open"
    LOT_OPEN = "lot_open"
    BID_WINDOW = "bid_window"
    ROUND_CLOSE = "round_close"
    LOT_RESOLUTION = "lot_resolution"
    SESSION_CLOSE = "session_close"


# Lifecycle states where the player can leave the venue without
# forfeiting any in-progress lot. Outside these the player drops their
# position on the live lot per §2.5.
SAFE_EXIT_STATES: frozenset[AuctionLifecycle] = frozenset(
    {
        AuctionLifecycle.SCHEDULED,
        AuctionLifecycle.PREVIEW,
        AuctionLifecycle.SESSION_CLOSE,
    }
)


# Session sizing. Stellaris standard 6, headliner 8; Reach 4. SA-B3 / B4
# may override these via venue config; SA-B2 ships with the defaults so
# the synthetic fixture works out of the box.
STELLARIS_STANDARD_SESSION_SIZE = 6
STELLARIS_HEADLINER_SESSION_SIZE = 8
REACH_SESSION_SIZE = 4

# Cadence for next-session scheduling (Stellaris). Reach is demand-driven
# so SA-B4 will override this. Fixed range here; AuctionState picks
# deterministically from the seed.
STELLARIS_CADENCE_MIN_DAYS = 5
STELLARIS_CADENCE_MAX_DAYS = 7

# Lot-pool exclusion: lots seen in 5 consecutive sessions without a sale
# are excluded from the next draw (resets to 0 when sold).
RECENTLY_SEEN_EXCLUSION = 5

# Headliner cap per session: at most one headliner.
HEADLINER_CAP_PER_SESSION = 1

# Sable's ceiling-jitter multiplier (§7.1, decision §11.12). Sable's
# *displayed* estimate is wider than the actual ceiling variance.
SABLE_CEILING_JITTER_FACTOR = 0.15

# Sable post-session "ceiling correct" trigger threshold (§9.4 banter
# flag). 5% averaged across rivals seen this session.
SABLE_CEILING_CORRECT_THRESHOLD = 0.05

# Achievement: perfect read = win lot within 2% of Sable's estimate.
PERFECT_READ_THRESHOLD = 0.02

# Achievement: champion = 5 wins at Stellaris.
CHAMPION_WINS_AT_STELLARIS = 5


# SA-B4: Reach demand-driven cadence (locked decision §B4.4). The pending-
# arrivals counter stamps a per-game-day chance of advancing; a session
# fires once the counter reaches REACH_SESSION_SIZE OR the gap-cap days
# elapse since the last Reach close. Counter resets on session close.
REACH_DEMAND_PROBABILITY = 0.35
REACH_DEMAND_MAX_GAP_DAYS = 8

# SA-B4: faction-rep penalty magnitudes for Reach legality consequences
# (locked decision §B4.8). Applied against ``stellaris_commerce_guild``
# rep when the player wins a contraband or restricted_weapon lot at the
# Reach. Engine wires these in via ``_ensure_auction_view``'s on_lot_won
# callback (see ``spacegame/engine/game.py``).
REACH_CONTRABAND_REP_PENALTY = -2
REACH_RESTRICTED_WEAPON_REP_PENALTY = -1

# SA-B4: achievement stub id (decision §B4.14). Metadata + display copy
# land in SA-X7; this constant is the canonical id consumers reference.
ACHIEVEMENT_AUCTION_REACH_DEBUT = "auction_reach_debut"


# SA-B5: Stellaris-only player-listing acceptance contract (locked
# decision §B5.2). Player listings consign at the Stellaris Auction
# House; Crimson Reach is buyer-side only in SA-B5.
PLAYER_LISTING_VENUE = "stellaris"
PLAYER_SELLER_ID = "player"


def compute_listing_fee(declared_appraisal: int) -> int:
    """Return the listing fee for a declared appraisal in credits.

    Locked decision §B5.4: ``fee = max(LISTING_FEE_FLOOR, int(declared *
    LISTING_FEE_RATE))``. Negative or zero appraisals collapse to the
    floor — the validator on ``create_listing`` handles the eligibility
    check separately, so this helper stays a pure formula.
    """
    from spacegame.config import LISTING_FEE_FLOOR, LISTING_FEE_RATE

    raw = int(max(0, declared_appraisal) * LISTING_FEE_RATE)
    return max(LISTING_FEE_FLOOR, raw)


# SA-B3: Stellaris Port standing -> tier ladder thresholds (decision §B3.2).
# Faction id is ``stellaris_commerce_guild``; rep clamps to -100..100.
STELLARIS_TIER_APPRENTICE_MAX = -1
STELLARIS_TIER_REGULAR_MAX = 25
STELLARIS_TIER_CERTIFIED_MAX = 75
# Anything above STELLARIS_TIER_CERTIFIED_MAX is patron.

# SA-B3: Season rotation (decision §B3.6). Three locked tags rotate on a
# 30-game-day cycle. SA-B6 may layer "no season" gaps; SA-B3 ships
# unconditional rotation.
STELLARIS_SEASON_TAGS: tuple[str, str, str] = (
    "provenance_week",
    "axiom_export_window",
    "salvage_circuit",
)
STELLARIS_SEASON_CYCLE_DAYS = 30

# SA-B3: Per-rival attendance frequencies (decision §B3.3). Prentiss is
# stochastic-deterministic at 70%; Kade conditional on a faction
# commodity gated to a Stellaris-aligned faction; Salko unconditional.
STELLARIS_PRENTISS_ATTENDANCE_RATE = 0.70
STELLARIS_KADE_TARGET_FACTIONS: frozenset[str] = frozenset(
    {"commerce_guild", "axiom_research", "stellaris_commerce_guild"}
)


# Appraisal-bonus stacking thresholds (§7.2). Sum of crew + skill
# auction_lot_appraisal_bonus values determines the post-win message.
APPRAISAL_BONUS_LEVEL_1 = 0.05  # lot_appraiser L1 only.
APPRAISAL_BONUS_LEVEL_2 = 0.10  # Sable only OR lot_appraiser L2.
APPRAISAL_BONUS_LEVEL_3 = 0.15  # Sable + lot_appraiser L1.
APPRAISAL_BONUS_LEVEL_4 = 0.20  # Sable + lot_appraiser L2.


@dataclass
class _LotResultRecord:
    """Per-lot session-history record."""

    lot_id: str
    sold: bool
    winner_id: Optional[str] = None
    sale_price: int = 0
    player_bid: bool = False
    rivals_bid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "sold": self.sold,
            "winner_id": self.winner_id,
            "sale_price": self.sale_price,
            "player_bid": self.player_bid,
            "rivals_bid": list(self.rivals_bid),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "_LotResultRecord":
        return cls(
            lot_id=data["lot_id"],
            sold=bool(data.get("sold", False)),
            winner_id=data.get("winner_id"),
            sale_price=int(data.get("sale_price", 0)),
            player_bid=bool(data.get("player_bid", False)),
            rivals_bid=list(data.get("rivals_bid", [])),
        )


@dataclass
class _SessionHistoryEntry:
    """Per-session history record stored on AuctionState."""

    session_id: str
    venue_id: str
    closed_on_day: int
    lot_results: list[_LotResultRecord] = field(default_factory=list)
    rival_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "venue_id": self.venue_id,
            "closed_on_day": self.closed_on_day,
            "lot_results": [r.to_dict() for r in self.lot_results],
            "rival_ids": list(self.rival_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "_SessionHistoryEntry":
        return cls(
            session_id=data["session_id"],
            venue_id=data["venue_id"],
            closed_on_day=int(data.get("closed_on_day", 0)),
            lot_results=[_LotResultRecord.from_dict(r) for r in data.get("lot_results", [])],
            rival_ids=list(data.get("rival_ids", [])),
        )


# --------------------------------------------------------------------------
# Bonus stacking helpers
# --------------------------------------------------------------------------


def appraisal_band_for_bonus(total_bonus: float, base_appraisal: int) -> tuple[int, int]:
    """Return the (low, high) credit band for a post-win valuation message.

    Maps the design doc §7.2 stacking rows:

    - 0.20 (Sable + lot_appraiser L2) -> (exact, exact)
    - 0.15 (Sable + lot_appraiser L1) -> ±8% band
    - 0.10 (Sable only OR lot_appraiser L2) -> ±15% band (Sable wording)
                                              or ±12% (no Sable wording)
    - 0.05 (lot_appraiser L1 only) -> ±20% band
    - 0.00 -> (0, 0) sentinel (caller skips message)
    """
    if total_bonus >= APPRAISAL_BONUS_LEVEL_4 - 0.0001:
        return (base_appraisal, base_appraisal)
    if total_bonus >= APPRAISAL_BONUS_LEVEL_3 - 0.0001:
        spread = round(base_appraisal * 0.08)
        return (base_appraisal - spread, base_appraisal + spread)
    if total_bonus >= APPRAISAL_BONUS_LEVEL_2 - 0.0001:
        spread = round(base_appraisal * 0.15)
        return (base_appraisal - spread, base_appraisal + spread)
    if total_bonus >= APPRAISAL_BONUS_LEVEL_1 - 0.0001:
        spread = round(base_appraisal * 0.20)
        return (base_appraisal - spread, base_appraisal + spread)
    return (0, 0)


def post_win_valuation_message(
    total_bonus: float,
    base_appraisal: int,
    *,
    sable_active: bool,
) -> str:
    """Format the post-win valuation message per §7.2.

    Returns an empty string when the player has no appraisal bonus.
    """
    low, high = appraisal_band_for_bonus(total_bonus, base_appraisal)
    if low == 0 and high == 0:
        return ""
    if total_bonus >= APPRAISAL_BONUS_LEVEL_4 - 0.0001:
        return f"Fair market value: {base_appraisal:,} credits."
    if total_bonus >= APPRAISAL_BONUS_LEVEL_3 - 0.0001:
        return f"Fair market value: {low:,} to {high:,} credits."
    if total_bonus >= APPRAISAL_BONUS_LEVEL_2 - 0.0001:
        if sable_active:
            return f"Fair market value: approx. {base_appraisal:,} credits."
        return f"Estimate: {low:,} to {high:,} credits."
    return f"Estimate: {low:,} to {high:,} credits."


def reserve_band_for_preview(base_appraisal: int, reserve_pct: float) -> tuple[int, int]:
    """Reserve banded estimate shown in preview when ``lot_appraiser`` is present.

    ``X = base_appraisal * (reserve_pct - 0.10)``,
    ``Y = base_appraisal * (reserve_pct + 0.10)`` per §7.2 preview clause.
    """
    low_pct = max(0.0, reserve_pct - 0.10)
    high_pct = min(1.0, reserve_pct + 0.10)
    low = round(base_appraisal * low_pct)
    high = round(base_appraisal * high_pct)
    return (low, high)


def sable_displayed_ceiling(
    persona: AIBidderPersona,
    lot: AuctionLot,
    session_id: str,
    *,
    vs_player: bool = False,
    recent_player_categories: tuple[str, ...] = (),
) -> int:
    """Return Sable's displayed ceiling estimate per §7.1 step 2.

    ``displayed = round(persona.ceiling + persona.session_signal_drift *
    persona.ceiling * SABLE_CEILING_JITTER_FACTOR)`` (banker's rounding
    via Python's built-in ``round``).
    """
    actual = persona.compute_ceiling(
        lot,
        session_id,
        vs_player=vs_player,
        recent_player_categories=recent_player_categories,
    )
    if actual <= 0:
        return 0
    drift = persona.session_signal_drift(session_id)
    jitter = drift * actual * SABLE_CEILING_JITTER_FACTOR
    return round(actual + jitter)


# --------------------------------------------------------------------------
# Lot pool generation
# --------------------------------------------------------------------------


def _seeded_rng(seed_token: str) -> random.Random:
    """Return a ``random.Random`` instance keyed off ``seed_token``."""
    digest = hashlib.sha256(seed_token.encode("utf-8")).digest()
    seed_int = struct.unpack(">Q", digest[:8])[0]
    return random.Random(seed_int)


def _player_rep_tier_for_venue(
    *,
    venue_id: str,
    stellaris_tier: str = "patron",
    wreckers_tier: str = "veteran",
) -> str:
    """Map a venue id + caller-provided tier strings into the lot tier ladder.

    Stellaris uses Port standing (apprentice/regular/certified/patron).
    Reach uses Wreckers' Guild membership (apprentice/journeyman/master/
    veteran). The Reach lot-tier ladder is independent of Stellaris's;
    SA-B4 owns Reach content. SA-B2 falls through to ``"patron"`` as the
    most-permissive Stellaris tier so the synthetic fixture sees every
    lot regardless of standing — content sprints lock the actual mapping.
    """
    if venue_id == "stellaris":
        return stellaris_tier
    return wreckers_tier


# --------------------------------------------------------------------------
# SA-B3: Stellaris-specific helpers (additive only; no schema changes)
# --------------------------------------------------------------------------


def stellaris_tier_for_standing(rep: int) -> str:
    """Return the Stellaris Port tier string for ``rep`` faction standing.

    Decision §B3.2 thresholds:

    * ``rep < 0`` -> ``"apprentice"``
    * ``0 <= rep <= 25`` -> ``"regular"``
    * ``26 <= rep <= 75`` -> ``"certified"``
    * ``76 <= rep <= 100`` -> ``"patron"``

    Faction id is ``stellaris_commerce_guild``. Reputation clamps to
    -100..100 elsewhere; this function tolerates any int and never raises.
    """
    if rep <= STELLARIS_TIER_APPRENTICE_MAX:
        return "apprentice"
    if rep <= STELLARIS_TIER_REGULAR_MAX:
        return "regular"
    if rep <= STELLARIS_TIER_CERTIFIED_MAX:
        return "certified"
    return "patron"


def current_season_tag(game_day: int) -> Optional[str]:
    """Return the active Stellaris season tag for ``game_day``.

    Decision §B3.6: 3 tags rotate on a 30-day cycle. ``game_day``
    expected to be a non-negative game-day counter; negative inputs
    treat day 0 as the first day of the cycle (mirror modulo).
    """
    if game_day < 0:
        return STELLARIS_SEASON_TAGS[0]
    bucket = (game_day // STELLARIS_SEASON_CYCLE_DAYS) % len(STELLARIS_SEASON_TAGS)
    return STELLARIS_SEASON_TAGS[bucket]


def stellaris_initial_session_day(current_day: int) -> int:
    """Pick the first Stellaris session day for a fresh save.

    Deterministic per ``current_day`` so the schedule survives reload
    without drift. Returns a calendar day in the locked 5-7 day cadence
    band.
    """
    rng = _seeded_rng(f"{current_day}_stellaris_initial")
    gap = rng.randint(STELLARIS_CADENCE_MIN_DAYS, STELLARIS_CADENCE_MAX_DAYS)
    return current_day + gap


def _kade_targets_in_pool(lot_pool: Iterable[AuctionLot]) -> bool:
    """True if any lot in ``lot_pool`` matches Kade's mandate.

    Kade attends only when at least one ``faction_commodity`` lot is
    gated to a Stellaris-aligned faction (decision §B3.3). The author-
    side rule lives in code, not data, because it's persona behavior.
    """
    for lot in lot_pool:
        if lot.category != "faction_commodity":
            continue
        if lot.faction_gate is None:
            continue
        if lot.faction_gate in STELLARIS_KADE_TARGET_FACTIONS:
            return True
    return False


def pick_stellaris_rival_attendance(
    *,
    session_id: str,
    lot_pool: Iterable[AuctionLot],
) -> list[str]:
    """Return the list of named-rival ids attending the given session.

    Decision §B3.3 attendance rules:

    * Prentiss: 70% deterministic via seeded hash on ``session_id``.
    * Kade: present iff the pool contains a Stellaris-aligned
      ``faction_commodity`` lot.
    * Salko: always attends a Stellaris session the player walks into.

    Args:
        session_id: Stable identifier for the session; seeds the RNG.
        lot_pool: Lots already drawn for the session (for Kade gate).

    Returns:
        Persona ids of the named rivals attending, in stable order
        (Prentiss, Kade, Salko).
    """
    pool_list = list(lot_pool)
    attendees: list[str] = []
    prentiss_unit = _seeded_unit_from_token(f"{session_id}_prentiss_attendance")
    if prentiss_unit < STELLARIS_PRENTISS_ATTENDANCE_RATE:
        from spacegame.models.bidding_persona import PERSONA_PRENTISS

        attendees.append(PERSONA_PRENTISS)
    if _kade_targets_in_pool(pool_list):
        from spacegame.models.bidding_persona import PERSONA_KADE

        attendees.append(PERSONA_KADE)
    from spacegame.models.bidding_persona import PERSONA_SALKO

    attendees.append(PERSONA_SALKO)
    return attendees


def _seeded_unit_from_token(token: str) -> float:
    """Return a deterministic float in [0, 1) keyed by ``token``."""
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    raw: int = struct.unpack(">Q", digest[:8])[0]
    return raw / float(1 << 64)


def generate_lot_pool(
    candidates: Iterable[AuctionLot],
    *,
    venue_id: str,
    player_rep_tier: str,
    player_faction_standing: dict[str, int],
    season_tag: Optional[str],
    session_id: str,
    target_size: int,
) -> list[AuctionLot]:
    """Draw a deterministic lot pool for a session per design doc §3.3.

    Filters apply in order: venue, rep tier, faction gate (positive
    standing only), recently-seen exclusion. The remaining candidates
    are weighted (rep-tier multiplier, season multiplier, headliner cap)
    and drawn without replacement up to ``target_size``.

    Args:
        candidates: All lots known for this venue (already venue-tagged).
        venue_id: Venue identifier (filters by lot.venue).
        player_rep_tier: Player's standing tier string for the venue.
        player_faction_standing: Faction id -> int. Lots gated on a
            faction require positive standing (>= 0).
        season_tag: Active season tag, or ``None``. Lots with a matching
            ``season_tag`` get a 2x weight bonus.
        session_id: Stable session identifier; seeds the draw RNG.
        target_size: Number of lots to draw.

    Returns:
        Drawn lots, in selection order. May be shorter than
        ``target_size`` if the candidate pool runs out.
    """
    # Step 1: venue filter.
    pool = [lot for lot in candidates if lot.venue == venue_id]
    # Step 2: rep tier filter (venue-aware ladder per locked decision §B4.3).
    pool = [
        lot
        for lot in pool
        if _player_meets_tier_for_venue(player_rep_tier, lot.rep_tier_required, venue_id)
    ]

    # Step 3: faction gate filter.
    def _passes_faction_gate(lot: AuctionLot) -> bool:
        if lot.faction_gate is None:
            return True
        return player_faction_standing.get(lot.faction_gate, 0) >= 0

    pool = [lot for lot in pool if _passes_faction_gate(lot)]
    # Step 4: recently-seen exclusion.
    pool = [lot for lot in pool if lot.recently_seen_count < RECENTLY_SEEN_EXCLUSION]
    if not pool:
        return []

    rng = _seeded_rng(f"{session_id}_lot_pool")
    drawn: list[AuctionLot] = []
    headliner_drawn = 0

    # Helper: compute current weight for ``lot`` given which headliners
    # have already been picked.
    def _weight_for(lot: AuctionLot) -> float:
        base_weight = 1.0
        # Rep tier multiplier: +0.3 per tier above the lot's required
        # tier. ``"none"`` requirement = 0 distance.
        rep_distance = _tier_distance(player_rep_tier, lot.rep_tier_required, venue_id=venue_id)
        rep_mult = 1.0 + 0.3 * rep_distance
        season_mult = 2.0 if (season_tag and lot.season_tag == season_tag) else 1.0
        if lot.is_headliner and headliner_drawn >= HEADLINER_CAP_PER_SESSION:
            return 0.0
        return base_weight * rep_mult * season_mult

    remaining = list(pool)
    while remaining and len(drawn) < target_size:
        weights = [_weight_for(lot) for lot in remaining]
        total = sum(weights)
        if total <= 0:
            break
        r = rng.uniform(0, total)
        upto = 0.0
        chosen_idx = len(remaining) - 1
        for i, w in enumerate(weights):
            upto += w
            if upto >= r:
                chosen_idx = i
                break
        chosen = remaining.pop(chosen_idx)
        drawn.append(chosen)
        if chosen.is_headliner:
            headliner_drawn += 1
    return drawn


_STELLARIS_TIER_LADDER: tuple[str, ...] = (
    "none",
    "apprentice",
    "regular",
    "certified",
    "patron",
)
_REACH_TIER_LADDER: tuple[str, ...] = (
    "none",
    "apprentice",
    "journeyman",
    "master",
)


def tier_ladder_for_venue(venue_id: str) -> tuple[str, ...]:
    """Return the rep-tier ladder strings for ``venue_id``.

    Stellaris uses Port standing (apprentice / regular / certified /
    patron); Reach uses Wreckers' Guild membership (apprentice /
    journeyman / master). Unknown venue ids fall back to the Stellaris
    ladder so SA-B3 callers that never pass ``venue_id`` keep their
    behavior (locked decision §B4.3).
    """
    if venue_id == "crimson_reach":
        return _REACH_TIER_LADDER
    return _STELLARIS_TIER_LADDER


def _tier_distance(
    player_tier: str,
    required_tier: str,
    *,
    venue_id: str = "stellaris",
) -> int:
    """Return positions between ``player_tier`` and ``required_tier`` on the ladder.

    Returns 0 if the player is at or below the required tier (the rep-
    tier filter excludes the lot before this is called for "below"
    cases, so the weight multiplier never sees a negative value). Falls
    back to 0 for unknown tier strings to avoid runaway weights.

    SA-B4 (locked decision §B4.3): ``venue_id`` selects the ladder.
    Stellaris ladder is the legacy default so SA-B3 callers without the
    keyword keep their behavior.
    """
    ladder = tier_ladder_for_venue(venue_id)
    try:
        p = ladder.index(player_tier)
    except ValueError:
        p = 0
    try:
        r = ladder.index(required_tier)
    except ValueError:
        r = 0
    return max(0, p - r)


def _player_meets_tier_for_venue(player_tier: str, required_tier: str, venue_id: str) -> bool:
    """True if ``player_tier`` meets or exceeds ``required_tier`` on the venue ladder.

    SA-B4: venue-aware replacement for the lot-pool tier-gate filter.
    Reach's "journeyman" / "master" tiers and Stellaris's "regular" /
    "certified" / "patron" tiers live on disjoint ladders; this helper
    keeps the comparison correct regardless of which venue is drawing.
    """
    ladder = tier_ladder_for_venue(venue_id)
    try:
        player_idx = ladder.index(player_tier)
    except ValueError:
        # Unknown player tier: only "none" requirements pass.
        player_idx = 0
    try:
        required_idx = ladder.index(required_tier)
    except ValueError:
        # Unknown required tier on the venue ladder: gate fails closed.
        return False
    return player_idx >= required_idx


# --------------------------------------------------------------------------
# SA-B4: Reach-specific helpers (additive only; no schema changes)
# --------------------------------------------------------------------------


def wreckers_tier_for_membership(player: Any) -> str:
    """Return the player's Wreckers' Guild tier id.

    Delegates to ``Player.get_sub_reputation_tier("wreckers_guild",
    WRECKERS_GUILD_CONFIG)`` so SA-1 stays the canonical source for the
    Wreckers' tier ladder. Returns ``"unjoined"`` when the player has
    never engaged with the Guild (sub_reputation defaults to 0 -> the
    lowest tier, ``unjoined``).
    """
    from spacegame.models.wreckers_guild import WRECKERS_GUILD_CONFIG

    tier = player.get_sub_reputation_tier("wreckers_guild", WRECKERS_GUILD_CONFIG)
    return tier.id


def reach_advance_demand(state: "AuctionState", current_day: int) -> int:
    """Advance the Reach pending-arrivals counter up to ``current_day``.

    Locked decision §B4.4: per-game-day deterministic draw on
    ``f"{day}_reach_arrivals"`` against ``REACH_DEMAND_PROBABILITY``.
    Idempotent across reload because the seed is fixed by the game day
    and the helper rolls only for days strictly greater than
    ``next_auction_day["crimson_reach_last_advance_day"]``. Counter is
    stored on ``AuctionState.next_auction_day`` under
    ``"crimson_reach_pending"`` so the existing save schema is unchanged.

    Args:
        state: The player's auction state.
        current_day: Game day we are advancing the counter to. Multiple
            calls with non-decreasing days advance once per day total;
            calling at a non-advancing day is a no-op.

    Returns:
        New pending-arrivals counter value after any draws.
    """
    last_advance = state.next_auction_day.get("crimson_reach_last_advance_day", -1)
    counter = state.next_auction_day.get("crimson_reach_pending", 0)
    day = last_advance + 1
    while day <= current_day:
        unit = _seeded_unit_from_token(f"{day}_reach_arrivals")
        if unit < REACH_DEMAND_PROBABILITY:
            counter += 1
        day += 1
    state.next_auction_day["crimson_reach_pending"] = counter
    state.next_auction_day["crimson_reach_last_advance_day"] = current_day
    return counter


def reach_session_due(state: "AuctionState", current_day: int) -> bool:
    """Return True if a Reach session should fire on ``current_day``.

    Locked decision §B4.4: a session is due when (a) the pending-
    arrivals counter has reached ``REACH_SESSION_SIZE`` OR (b)
    ``REACH_DEMAND_MAX_GAP_DAYS`` game-days have elapsed since the last
    Reach session close. Fresh saves (no ``last_auction_day`` entry)
    treat day 0 as the reference, so the cap path still fires once the
    cap elapses on a fresh save.
    """
    counter = state.next_auction_day.get("crimson_reach_pending", 0)
    if isinstance(counter, int) and counter >= REACH_SESSION_SIZE:
        return True
    last_day = state.last_auction_day.get("crimson_reach", 0)
    return (current_day - last_day) >= REACH_DEMAND_MAX_GAP_DAYS


# --------------------------------------------------------------------------
# SA-B5: Player-initiated listings
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _PlayerListing:
    """A consignment the player has listed at the Stellaris Auction House.

    Frozen so the in-flight listing data can be safely shared between
    ``AuctionState.active_listings`` and the converted ``AuctionLot``
    handed to the session. The fields capture exactly the inputs the
    player chose plus the listing-time bookkeeping the engine needs to
    return the item to inventory if the lot withdraws.

    Attributes:
        listing_id: Unique listing identifier. Stable across save/load.
        item_kind: ``"commodity"`` (cargo) or ``"part"`` (parts inventory).
        item_id: Canonical id in the corresponding inventory keyspace.
        quantity: How many units the player is consigning.
        declared_appraisal: Player's declared fair-market value, in
            credits. The 5% listing fee is computed off this value.
        reserve_pct: Player-chosen reserve, in [0.50, 0.95]. Hidden from
            AI buyers (mirrors §5.4); the lot's ``reserve_price`` derives
            from ``declared_appraisal * reserve_pct``.
        listing_fee_paid: Credits already deducted at listing time. Not
            refunded under any outcome (locked decision §B5.4).
        listed_on_day: Game-day stamp. Used by
            ``eligible_listings_for_session`` to gate session inclusion.
        headline: Display name shown on the floor (anonymized).
        description: Short flavor text shown in preview.
        category: Lot category from the standard set; mirrors ``AuctionLot``.
    """

    listing_id: str
    item_kind: str
    item_id: str
    quantity: int
    declared_appraisal: int
    reserve_pct: float
    listing_fee_paid: int
    listed_on_day: int
    headline: str
    description: str
    category: str

    def to_auction_lot(self) -> AuctionLot:
        """Return the ``AuctionLot`` the session machinery sees.

        Decision §B5.2 / §B5.3: ``venue=stellaris``, ``seller_id="player"``,
        ``contraband=False`` (SA-B5 ships only non-contraband listings),
        ``rep_tier_required=REP_TIER_REGULAR`` (mirrors the listing
        tier-gate so the lot pool filter is consistent with eligibility).
        """
        return AuctionLot(
            id=f"player_listing_{self.listing_id}",
            headline=self.headline,
            description=self.description,
            category=self.category,
            venue=VENUE_STELLARIS,
            base_appraisal=self.declared_appraisal,
            reserve_pct=self.reserve_pct,
            faction_gate=None,
            rep_tier_required=REP_TIER_REGULAR,
            is_headliner=False,
            season_tag=None,
            contraband=False,
            source_module_id=None,
            recently_seen_count=0,
            seller_id=PLAYER_SELLER_ID,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "item_kind": self.item_kind,
            "item_id": self.item_id,
            "quantity": self.quantity,
            "declared_appraisal": self.declared_appraisal,
            "reserve_pct": self.reserve_pct,
            "listing_fee_paid": self.listing_fee_paid,
            "listed_on_day": self.listed_on_day,
            "headline": self.headline,
            "description": self.description,
            "category": self.category,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "_PlayerListing":
        return cls(
            listing_id=str(data["listing_id"]),
            item_kind=str(data["item_kind"]),
            item_id=str(data["item_id"]),
            quantity=int(data.get("quantity", 1)),
            declared_appraisal=int(data["declared_appraisal"]),
            reserve_pct=float(data["reserve_pct"]),
            listing_fee_paid=int(data.get("listing_fee_paid", 0)),
            listed_on_day=int(data.get("listed_on_day", 0)),
            headline=str(data.get("headline", "")),
            description=str(data.get("description", "")),
            category=str(data.get("category", "faction_commodity")),
        )


# --------------------------------------------------------------------------
# AuctionState
# --------------------------------------------------------------------------


@dataclass
class AuctionState:
    """Player's auction-system state, serialized as a Player field.

    Mutable. The view drives ``tick``/``submit_bid``; the lifecycle
    moves through :class:`AuctionLifecycle` states. AI counter-bidding
    happens inside ``tick`` so the same call advances both timers and
    AI activity.

    The 12 schema fields below match design doc §8.1.
    """

    pending_lot_pool: list[AuctionLot] = field(default_factory=list)
    active_auction_id: Optional[str] = None
    active_session_id: Optional[str] = None
    active_session_lots: list[AuctionLot] = field(default_factory=list)
    active_round: int = 0
    active_lot_index: int = 0
    session_history: list[_SessionHistoryEntry] = field(default_factory=list)
    last_auction_day: dict[str, int] = field(default_factory=dict)
    next_auction_day: dict[str, int] = field(default_factory=dict)
    recent_bid_categories: list[str] = field(default_factory=list)
    rival_session_attendance: dict[str, list[str]] = field(default_factory=dict)
    won_lots: list[str] = field(default_factory=list)
    speed_setting: str = DEFAULT_SPEED_SETTING

    # Runtime-only fields not part of the §8.1 schema but persisted to
    # keep mid-session save/load deterministic. Ignored by save migration
    # if absent.
    lifecycle: AuctionLifecycle = AuctionLifecycle.SCHEDULED
    round_state: Optional[RoundState] = None
    session_personas: list[str] = field(default_factory=list)
    session_lot_results: list[_LotResultRecord] = field(default_factory=list)
    seconds_since_last_bid: float = 0.0
    pending_ai_actions: dict[str, float] = field(default_factory=dict)

    # Achievement counters mirrored on Player for AchievementManager. We
    # keep them in sync on the Player object via ``apply_lot_resolution``.
    auction_lots_won_total: int = 0
    auction_lots_won_stellaris: int = 0
    # SA-B4: Reach win counter for the achievement_auction_reach_debut
    # stub (locked decision §B4.14). SA-X7 wires the achievement metadata
    # to this stat key.
    auction_lots_won_reach: int = 0
    auction_rivals_retired: int = 0
    auction_perfect_reads: int = 0

    # SA-B5: Player-initiated auctions. ``active_listings`` holds open
    # consignments awaiting a session; ``listing_history`` archives past
    # outcomes (one dict per resolved listing). The 3 counters mirror
    # SA-B2's lots-won pattern and are read by AchievementManager via the
    # Player property mirror.
    active_listings: list[_PlayerListing] = field(default_factory=list)
    listing_history: list[dict[str, Any]] = field(default_factory=list)
    auction_listings_sold: int = 0
    auction_listings_attempted: int = 0
    auction_listing_fees_paid: int = 0

    # ------------------------------------------------------------------
    # Lifecycle entry / scheduling
    # ------------------------------------------------------------------

    def schedule_session(self, venue_id: str, day: int) -> None:
        """Record the next-session day for ``venue_id``."""
        self.next_auction_day[venue_id] = day

    def is_session_due(self, venue_id: str, current_day: int) -> bool:
        """True if a session is scheduled and the current day has reached it."""
        scheduled = self.next_auction_day.get(venue_id)
        return scheduled is not None and current_day >= scheduled

    def enter_preview(
        self,
        venue_id: str,
        session_lots: list[AuctionLot],
        rival_ids: Iterable[str],
        session_id: str,
    ) -> None:
        """Move to PREVIEW with a session lot list ready for the player to inspect.

        Idempotent if already in PREVIEW for the same session_id; calling
        it again with a new session id replaces the lot list.
        """
        self.active_auction_id = venue_id
        self.active_session_id = session_id
        self.active_session_lots = list(session_lots)
        self.session_personas = list(rival_ids)
        self.lifecycle = AuctionLifecycle.PREVIEW
        self.active_lot_index = 0
        self.active_round = 0
        self.session_lot_results = []
        self.round_state = None
        self.seconds_since_last_bid = 0.0
        self.pending_ai_actions = {}
        self.rival_session_attendance[session_id] = [
            rid for rid in rival_ids if rid in NAMED_RIVAL_IDS
        ]

    def open_session(self) -> None:
        """Transition PREVIEW -> SESSION_OPEN -> first LOT_OPEN."""
        if self.lifecycle != AuctionLifecycle.PREVIEW:
            return
        self.lifecycle = AuctionLifecycle.SESSION_OPEN
        self._open_next_lot()

    # ------------------------------------------------------------------
    # Per-lot lifecycle
    # ------------------------------------------------------------------

    def _open_next_lot(self) -> None:
        if self.active_lot_index >= len(self.active_session_lots):
            self._close_session()
            return
        lot = self.active_session_lots[self.active_lot_index]
        rounds_for_lot = 3 if lot.is_headliner else 2
        round_dur, snipe_w = SPEED_SETTINGS.get(
            self.speed_setting, SPEED_SETTINGS[DEFAULT_SPEED_SETTING]
        )
        rs = RoundState(
            bidders_active={"player", *self.session_personas},
            round_min_increment=min_increment_for_appraisal(lot.base_appraisal),
        )
        # Drop personas whose effective_value is below the opening floor.
        # (We only know personas by id here; the caller wires the actual
        # AIBidderPersona objects in via ``set_session_personas``.)
        rs.current_high_bid = opening_bid_for_lot(lot.base_appraisal, lot.reserve_price)
        rs.open_round(
            round_number=1,
            round_duration_seconds=round_dur,
            snipe_window_seconds=snipe_w,
            round_min_increment=min_increment_for_appraisal(lot.base_appraisal),
        )
        # Opening price counts as the floor; nobody is yet "leading" --
        # we treat it as an unfilled floor by leaving current_high_bidder_id
        # as None so the first bid registers normally.
        rs.current_high_bidder_id = None
        self.round_state = rs
        self.active_round = 1
        self.lifecycle = AuctionLifecycle.BID_WINDOW
        self.seconds_since_last_bid = 0.0
        # Stash the round count for closure logic.
        self._rounds_for_active_lot = rounds_for_lot

    # The view supplies live AIBidderPersona objects; we keep them
    # mutable on the state machine so AI counter-bid logic can inspect
    # axes / ceilings without re-loading from data.
    def set_session_personas(self, personas: list[AIBidderPersona]) -> None:
        """Provide the live persona objects for the active session."""
        self._live_personas: dict[str, AIBidderPersona] = {p.persona_id: p for p in personas}

    def get_persona(self, persona_id: str) -> Optional[AIBidderPersona]:
        return getattr(self, "_live_personas", {}).get(persona_id)

    # ------------------------------------------------------------------
    # SA-B5: Player-initiated listings
    # ------------------------------------------------------------------

    def create_listing(
        self,
        *,
        player: Any,
        item_kind: str,
        item_id: str,
        quantity: int,
        declared_appraisal: int,
        reserve_pct: float,
        current_day: int,
        headline: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "faction_commodity",
    ) -> tuple[bool, str, Optional[_PlayerListing]]:
        """Validate and register a player consignment.

        Returns ``(ok, message, listing)``. On success the fee is
        deducted from credits, the item is removed from the player's
        cargo or parts inventory, the listing is appended to
        ``active_listings``, and the attempt counter is incremented.
        On failure no state mutates and ``listing`` is ``None``.
        """
        from spacegame.config import (
            LISTING_RESERVE_PCT_MAX,
            LISTING_RESERVE_PCT_MIN,
            MAX_ACTIVE_LISTINGS,
        )

        if item_kind not in ("commodity", "part"):
            return (False, "Item kind must be commodity or part.", None)
        if quantity <= 0:
            return (False, "Quantity must be at least 1.", None)
        if declared_appraisal <= 0:
            return (False, "Declared appraisal must be greater than zero.", None)
        if not (LISTING_RESERVE_PCT_MIN <= reserve_pct <= LISTING_RESERVE_PCT_MAX):
            return (
                False,
                (
                    f"Reserve must be between {LISTING_RESERVE_PCT_MIN:.0%} "
                    f"and {LISTING_RESERVE_PCT_MAX:.0%} of the appraisal."
                ),
                None,
            )
        if len(self.active_listings) >= MAX_ACTIVE_LISTINGS:
            return (
                False,
                f"You already have {MAX_ACTIVE_LISTINGS} active listings on the floor.",
                None,
            )
        # Tier check (defence in depth — view also gates the entry).
        rep = player.faction_reputation.get("stellaris_commerce_guild", 0)
        tier = stellaris_tier_for_standing(rep)
        if tier == "apprentice" or tier == "none":
            return (
                False,
                "Listing requires Stellaris regular standing or above.",
                None,
            )
        # Inventory check.
        if item_kind == "commodity":
            held = player.ship.get_cargo_quantity(item_id)
        else:
            held = player.parts_inventory.get(item_id, 0)
        if held < quantity:
            return (
                False,
                f"You do not have {quantity} of '{item_id}' in inventory.",
                None,
            )
        fee = compute_listing_fee(declared_appraisal)
        if player.credits < fee:
            return (
                False,
                f"Listing fee is {fee:,} credits; you have {player.credits:,}.",
                None,
            )
        listing_id = f"l_{current_day}_{len(self.active_listings)}_{item_id}"
        listing_headline = headline or self._default_listing_headline(item_kind, item_id, quantity)
        listing_description = description or self._default_listing_description(
            item_kind, item_id, quantity
        )
        listing = _PlayerListing(
            listing_id=listing_id,
            item_kind=item_kind,
            item_id=item_id,
            quantity=quantity,
            declared_appraisal=declared_appraisal,
            reserve_pct=reserve_pct,
            listing_fee_paid=fee,
            listed_on_day=current_day,
            headline=listing_headline,
            description=listing_description,
            category=category,
        )
        # Mutations only after every check passes.
        player.credits -= fee
        if item_kind == "commodity":
            player.ship.remove_cargo(item_id, quantity)
        else:
            player.parts_inventory[item_id] = held - quantity
            if player.parts_inventory[item_id] <= 0:
                del player.parts_inventory[item_id]
        self.active_listings.append(listing)
        self.auction_listings_attempted += 1
        self.auction_listing_fees_paid += fee
        return (True, "Listing accepted.", listing)

    def cancel_listing(self, listing_id: str, player: Any) -> tuple[bool, str]:
        """Pull an active listing back. Returns the item; the fee is forfeit.

        Cancellation is only allowed while the listing is still in
        ``active_listings`` (decision §B5.6). Once a listing is pulled
        into a live session it cannot be cancelled — the player must
        wait for the lot to resolve.
        """
        for i, listing in enumerate(self.active_listings):
            if listing.listing_id == listing_id:
                # Return the item to inventory.
                if listing.item_kind == "commodity":
                    player.ship.add_cargo(listing.item_id, listing.quantity, price_per_unit=0)
                else:
                    player.parts_inventory[listing.item_id] = (
                        player.parts_inventory.get(listing.item_id, 0) + listing.quantity
                    )
                del self.active_listings[i]
                return (True, "Listing cancelled. The item is back in your hold.")
        return (False, "Listing not found.")

    def eligible_listings_for_session(self, current_day: int) -> list[_PlayerListing]:
        """Return up to ``MAX_ACTIVE_LISTINGS`` listings ready for the next session.

        A listing is eligible when ``listed_on_day <= current_day``.
        Listings already on a live session lot are tracked in
        ``active_listings`` until resolution, so they're excluded only
        when ``_resolve_lot`` archives them. The cap mirrors the slot
        count so a session never carries more than 3 player lots.
        """
        from spacegame.config import MAX_ACTIVE_LISTINGS

        eligible = [l for l in self.active_listings if l.listed_on_day <= current_day]
        return eligible[:MAX_ACTIVE_LISTINGS]

    def _default_listing_headline(self, item_kind: str, item_id: str, quantity: int) -> str:
        """Anonymous headline when the caller didn't supply one."""
        nice = item_id.replace("_", " ").title()
        if quantity == 1:
            return f"Consigned: {nice}"
        return f"Consigned: {nice} ({quantity} units)"

    def _default_listing_description(self, item_kind: str, item_id: str, quantity: int) -> str:
        """Anonymous flavor when the caller didn't supply one."""
        if item_kind == "commodity":
            return "A consigned commodity. Provenance held by the seller."
        return "A consigned ship part. Listed by a private hand."

    def _find_active_listing_for_lot(self, lot: AuctionLot) -> Optional[_PlayerListing]:
        """Return the listing whose ``to_auction_lot()`` produced ``lot``.

        Lookup keys on the lot id (``"player_listing_<listing_id>"``) so
        the lookup survives session round-trips.
        """
        prefix = "player_listing_"
        if not lot.id.startswith(prefix):
            return None
        listing_id = lot.id[len(prefix) :]
        for l in self.active_listings:
            if l.listing_id == listing_id:
                return l
        return None

    def _archive_player_listing(
        self,
        listing: _PlayerListing,
        *,
        outcome: str,
        sale_price: int,
        closed_on_day: int,
    ) -> dict[str, Any]:
        """Move a player listing from active to history with the resolution data.

        Returns the archived entry dict so the engine callback can read
        it without scanning the history list.
        """
        archived = listing.to_dict()
        archived["outcome"] = outcome
        archived["sale_price"] = sale_price
        archived["closed_on_day"] = closed_on_day
        self.listing_history.append(archived)
        # Drop the matching listing from active.
        self.active_listings = [
            l for l in self.active_listings if l.listing_id != listing.listing_id
        ]
        if outcome == "sold":
            self.auction_listings_sold += 1
        return archived

    # ------------------------------------------------------------------
    # Player input
    # ------------------------------------------------------------------

    def submit_player_bid(self, amount: int) -> tuple[bool, str]:
        """Submit a bid as the player.

        Triggers a snipe-window reset where applicable, records the
        category for Salko escalation, and transitions to BID_WINDOW
        bookkeeping.
        """
        if self.round_state is None or self.lifecycle != AuctionLifecycle.BID_WINDOW:
            return (False, "No active round.")
        ok, msg = self.round_state.submit_bid("player", amount)
        if ok:
            lot = self.active_session_lots[self.active_lot_index]
            cat = lot.category
            # Track recent bid categories (last N sessions, capped — we
            # track per-session to keep the list bounded).
            if cat not in self.recent_bid_categories:
                self.recent_bid_categories.append(cat)
                # Keep the list to a reasonable length. SALKO_ESCALATION_WINDOW
                # is "sessions"; since each session may generate multiple
                # categories, we keep up to ``window * 4`` distinct entries.
                cap = SALKO_ESCALATION_WINDOW * 4
                if len(self.recent_bid_categories) > cap:
                    self.recent_bid_categories = self.recent_bid_categories[-cap:]
            self.seconds_since_last_bid = 0.0
            self._record_bidder("player")
        return (ok, msg)

    def player_fold(self) -> tuple[bool, str]:
        """Fold the player out of the current lot for its remaining rounds."""
        if self.round_state is None:
            return (False, "No active round.")
        return self.round_state.fold("player")

    def player_hold(self) -> tuple[bool, str]:
        """Player passes this round; no bid submitted."""
        if self.round_state is None:
            return (False, "No active round.")
        return (True, "Player holds this round.")

    def player_min_raise_amount(self) -> int:
        """Compute the next-min bid amount the player can submit, or 0."""
        if self.round_state is None:
            return 0
        return self.round_state.current_high_bid + self.round_state.round_min_increment

    # ------------------------------------------------------------------
    # AI counter-bid scheduling
    # ------------------------------------------------------------------

    def _record_bidder(self, bidder_id: str) -> None:
        """Track which bidders have placed bids on the active lot."""
        if not hasattr(self, "_active_lot_bidders"):
            self._active_lot_bidders: set[str] = set()
        self._active_lot_bidders.add(bidder_id)

    def _step_ai_bidders(self, dt: float) -> list[str]:
        """Drive AI counter-bidding for a single tick.

        Returns a list of human-readable feedback strings for any AI
        actions taken this tick. Pure determinism: persona timing comes
        from the seeded delay + the elapsed time since the last bid.
        """
        messages: list[str] = []
        rs = self.round_state
        if rs is None or rs.phase != RoundPhase.BID_WINDOW:
            return messages
        live = getattr(self, "_live_personas", {})
        if not live:
            return messages
        speed_mult = SPEED_AI_MULTIPLIER.get(self.speed_setting, 1.0)
        lot = self.active_session_lots[self.active_lot_index]
        recent_cats = tuple(self.recent_bid_categories[-SALKO_ESCALATION_WINDOW * 4 :])
        for persona_id, persona in live.items():
            if persona_id not in rs.bidders_active:
                continue
            if persona_id == rs.current_high_bidder_id:
                continue
            # Snipe gate: if currently inside the snipe window, only
            # high-snipe-resistance personas may counter.
            if rs.is_in_snipe_window() and not persona.will_counter_snipe():
                continue
            ceiling = persona.compute_ceiling(
                lot,
                self.active_session_id or "_",
                vs_player=(rs.current_high_bidder_id == "player"),
                recent_player_categories=recent_cats,
            )
            if ceiling <= 0:
                continue
            # Persona's planned counter-delay for this round.
            delay = persona.counter_bid_delay(
                self.active_session_id or "_",
                round_number=rs.round_number,
                round_duration_seconds=rs.round_duration_seconds,
                speed_multiplier=speed_mult,
            )
            # Once the elapsed time since the last bid exceeds the
            # persona's planned delay, the persona acts.
            if self.seconds_since_last_bid + dt < delay:
                continue
            next_bid = rs.current_high_bid + rs.round_min_increment
            if next_bid > ceiling:
                continue  # Persona never bids past ceiling.
            ok, msg = rs.submit_bid(persona_id, next_bid)
            if ok:
                self._record_bidder(persona_id)
                self.seconds_since_last_bid = 0.0
                messages.append(msg)
                # One AI action per tick keeps the simulation well-paced.
                return messages
        return messages

    # ------------------------------------------------------------------
    # Tick + round close + lot resolution
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> list[str]:
        """Advance the round timer + AI activity for ``dt`` seconds.

        Returns a list of feedback strings (AI bid landed, round closed,
        lot resolved) so the view can route them to its message queue.
        """
        messages: list[str] = []
        if self.lifecycle != AuctionLifecycle.BID_WINDOW or self.round_state is None:
            return messages
        # Step AI before the timer so the AI's last reaction can still
        # land in the same tick the timer would have expired.
        messages.extend(self._step_ai_bidders(dt))
        self.seconds_since_last_bid += dt
        self.round_state.tick(dt)
        if self.round_state.phase == RoundPhase.ROUND_CLOSE:
            messages.append(self._handle_round_close())
        return messages

    def _handle_round_close(self) -> str:
        """Resolve the just-closed round: open the next round, or close the lot."""
        if self.round_state is None:
            return ""
        rounds_left = max(
            0, getattr(self, "_rounds_for_active_lot", 2) - self.round_state.round_number
        )
        if rounds_left > 0 and self.round_state.current_high_bidder_id is not None:
            # Carry the high bid forward into the next round.
            old = self.round_state
            self.round_state = RoundState(
                bidders_active=set(old.bidders_active),
                round_min_increment=old.round_min_increment,
            )
            self.round_state.current_high_bid = old.current_high_bid
            self.round_state.current_high_bidder_id = old.current_high_bidder_id
            round_dur, snipe_w = SPEED_SETTINGS.get(
                self.speed_setting, SPEED_SETTINGS[DEFAULT_SPEED_SETTING]
            )
            self.round_state.open_round(
                round_number=old.round_number + 1,
                round_duration_seconds=round_dur,
                snipe_window_seconds=snipe_w,
                round_min_increment=old.round_min_increment,
            )
            self.active_round = self.round_state.round_number
            self.lifecycle = AuctionLifecycle.BID_WINDOW
            self.seconds_since_last_bid = 0.0
            return f"Round {old.round_number} closed; advancing to round {self.round_state.round_number}."
        return self._resolve_lot()

    def _resolve_lot(self) -> str:
        if self.round_state is None:
            return ""
        lot = self.active_session_lots[self.active_lot_index]
        winning_bid = self.round_state.current_high_bid
        winner = self.round_state.current_high_bidder_id
        bidders = sorted(getattr(self, "_active_lot_bidders", set()))
        rivals_bid = [b for b in bidders if b in NAMED_RIVAL_IDS]
        player_bid = "player" in bidders
        sold = winner is not None and winning_bid >= lot.reserve_price
        record = _LotResultRecord(
            lot_id=lot.id,
            sold=sold,
            winner_id=winner if sold else None,
            sale_price=winning_bid if sold else 0,
            player_bid=player_bid,
            rivals_bid=rivals_bid,
        )
        self.session_lot_results.append(record)
        # SA-B5: player-seller lots route through listing_history rather
        # than the lots-won counters. Catalog lots (seller_id is None)
        # keep the original behavior unchanged.
        if lot.seller_id == PLAYER_SELLER_ID:
            listing = self._find_active_listing_for_lot(lot)
            outcome = "sold" if sold else "withdrawn"
            archive_price = winning_bid if sold else 0
            if listing is not None:
                self._archive_player_listing(
                    listing,
                    outcome=outcome,
                    sale_price=archive_price,
                    closed_on_day=0,  # caller stamps via close_session_for_day
                )
            self.active_session_lots[self.active_lot_index] = lot.with_recently_seen(0)
            if sold:
                msg = f"Sold: {lot.headline} at {winning_bid:,} credits."
            else:
                msg = "Reserve not met. The lot returns to your hold."
        elif sold:
            if winner == "player":
                self.won_lots.append(lot.id)
                self.auction_lots_won_total += 1
                if lot.venue == "stellaris":
                    self.auction_lots_won_stellaris += 1
                elif lot.venue == "crimson_reach":
                    self.auction_lots_won_reach += 1
            # Reset recently_seen_count on sale; replace lot in pool.
            self.active_session_lots[self.active_lot_index] = lot.with_recently_seen(0)
            msg = f"Sold: {lot.headline} at {winning_bid:,} credits."
        else:
            # Withdraw: bump recently_seen_count, return to pool.
            new_seen = lot.recently_seen_count + 1
            self.active_session_lots[self.active_lot_index] = lot.with_recently_seen(new_seen)
            msg = "Reserve not met. The lot is withdrawn."
        # Advance to next lot.
        self.lifecycle = AuctionLifecycle.LOT_RESOLUTION
        self.active_lot_index += 1
        if hasattr(self, "_active_lot_bidders"):
            self._active_lot_bidders = set()
        return msg

    def advance_after_resolution(self) -> Optional[str]:
        """Move from LOT_RESOLUTION to the next LOT_OPEN or SESSION_CLOSE.

        Returns the next-lot announcement message, or ``None`` when the
        session has closed.
        """
        if self.lifecycle != AuctionLifecycle.LOT_RESOLUTION:
            return None
        if self.active_lot_index >= len(self.active_session_lots):
            self._close_session()
            return None
        self._open_next_lot()
        next_lot = self.active_session_lots[self.active_lot_index - 0]
        return f"Next lot: {next_lot.headline}."

    # ------------------------------------------------------------------
    # Session close
    # ------------------------------------------------------------------

    def _close_session(self) -> None:
        if self.active_auction_id is None or self.active_session_id is None:
            self.lifecycle = AuctionLifecycle.SESSION_CLOSE
            return
        history = _SessionHistoryEntry(
            session_id=self.active_session_id,
            venue_id=self.active_auction_id,
            closed_on_day=0,  # caller fills via close_session_for_day
            lot_results=list(self.session_lot_results),
            rival_ids=list(self.rival_session_attendance.get(self.active_session_id, [])),
        )
        self.session_history.append(history)
        self.lifecycle = AuctionLifecycle.SESSION_CLOSE

    def close_session_for_day(self, current_day: int) -> None:
        """Stamp ``current_day`` on the most recent session and schedule the next.

        Idempotent: calling twice does not re-stamp prior sessions.
        """
        if self.session_history:
            last = self.session_history[-1]
            if last.closed_on_day == 0:
                last.closed_on_day = current_day
        if self.active_auction_id is not None:
            self.last_auction_day[self.active_auction_id] = current_day
            # Stellaris cadence: 5-7 days; Reach is demand-driven (locked
            # decision §B4.4 — counter resets on close so the next session
            # accumulates from zero).
            if self.active_auction_id == "stellaris":
                seed = _seeded_rng(
                    f"{self.active_session_id}_next_cadence_{self.active_auction_id}"
                )
                gap = seed.randint(STELLARIS_CADENCE_MIN_DAYS, STELLARIS_CADENCE_MAX_DAYS)
                self.next_auction_day[self.active_auction_id] = current_day + gap
            elif self.active_auction_id == "crimson_reach":
                self.next_auction_day["crimson_reach_pending"] = 0
                # Roll forward last_advance_day so the next demand pass
                # accumulates from the just-closed day rather than re-
                # rolling history.
                self.next_auction_day["crimson_reach_last_advance_day"] = current_day

    # ------------------------------------------------------------------
    # Helpers consumed by the view
    # ------------------------------------------------------------------

    def current_lot(self) -> Optional[AuctionLot]:
        """Return the lot the round_state is bidding on, or ``None``."""
        if self.round_state is None:
            return None
        if 0 <= self.active_lot_index < len(self.active_session_lots):
            return self.active_session_lots[self.active_lot_index]
        return None

    def player_won(self, lot_id: str) -> bool:
        return lot_id in self.won_lots

    # ------------------------------------------------------------------
    # Captain memory hand-off
    # ------------------------------------------------------------------

    def collect_outbid_records(
        self, captain_memory: dict[str, "CaptainMemory"], game_day: int
    ) -> list[str]:
        """Iterate the just-closed session's lot results and apply OUTCOME_OUTBID.

        Records exactly one entry per (rival, lot) where:
        * the rival was in the session,
        * the rival won the lot,
        * the player also bid on the lot.

        Returns the ids of rivals whose status crossed to ``STATUS_WANDERER``
        on this call (achievement + flag wiring on the caller side).
        """
        from spacegame.models.captain_memory import (
            OUTCOME_OUTBID,
            STATUS_WANDERER,
            CaptainMemory,
        )

        retired_ids: list[str] = []
        if not self.session_history:
            return retired_ids
        last = self.session_history[-1]
        for record in last.lot_results:
            if not record.sold or not record.player_bid:
                continue
            if record.winner_id is None or record.winner_id not in NAMED_RIVAL_IDS:
                continue
            rival_id = record.winner_id
            mem = captain_memory.get(rival_id)
            if mem is None:
                mem = CaptainMemory(captain_id=rival_id)
                captain_memory[rival_id] = mem
            previous_status = mem.status
            mem.record_encounter(OUTCOME_OUTBID, game_day)
            if previous_status != STATUS_WANDERER and mem.status == STATUS_WANDERER:
                retired_ids.append(rival_id)
                self.auction_rivals_retired += 1
        return retired_ids

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "pending_lot_pool": [lot.to_dict() for lot in self.pending_lot_pool],
            "active_auction_id": self.active_auction_id,
            "active_session_id": self.active_session_id,
            "active_session_lots": [lot.to_dict() for lot in self.active_session_lots],
            "active_round": self.active_round,
            "active_lot_index": self.active_lot_index,
            "session_history": [s.to_dict() for s in self.session_history],
            "last_auction_day": dict(self.last_auction_day),
            "next_auction_day": dict(self.next_auction_day),
            "recent_bid_categories": list(self.recent_bid_categories),
            "rival_session_attendance": {
                k: list(v) for k, v in self.rival_session_attendance.items()
            },
            "won_lots": list(self.won_lots),
            "speed_setting": self.speed_setting,
            "lifecycle": self.lifecycle.value,
            "round_state": self.round_state.to_dict() if self.round_state else None,
            "session_personas": list(self.session_personas),
            "session_lot_results": [r.to_dict() for r in self.session_lot_results],
            "seconds_since_last_bid": self.seconds_since_last_bid,
            "auction_lots_won_total": self.auction_lots_won_total,
            "auction_lots_won_stellaris": self.auction_lots_won_stellaris,
            "auction_lots_won_reach": self.auction_lots_won_reach,
            "auction_rivals_retired": self.auction_rivals_retired,
            "auction_perfect_reads": self.auction_perfect_reads,
            # SA-B5: player-listing schema. Old saves (no SA-B5 fields)
            # round-trip cleanly via the from_dict defaults.
            "active_listings": [l.to_dict() for l in self.active_listings],
            "listing_history": [dict(entry) for entry in self.listing_history],
            "auction_listings_sold": self.auction_listings_sold,
            "auction_listings_attempted": self.auction_listings_attempted,
            "auction_listing_fees_paid": self.auction_listing_fees_paid,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuctionState":
        lifecycle_value = data.get("lifecycle", AuctionLifecycle.SCHEDULED.value)
        try:
            lifecycle = AuctionLifecycle(lifecycle_value)
        except ValueError:
            lifecycle = AuctionLifecycle.SCHEDULED
        rs_data = data.get("round_state")
        rs = RoundState.from_dict(rs_data) if rs_data else None
        return cls(
            pending_lot_pool=[AuctionLot.from_dict(d) for d in data.get("pending_lot_pool", [])],
            active_auction_id=data.get("active_auction_id"),
            active_session_id=data.get("active_session_id"),
            active_session_lots=[
                AuctionLot.from_dict(d) for d in data.get("active_session_lots", [])
            ],
            active_round=int(data.get("active_round", 0)),
            active_lot_index=int(data.get("active_lot_index", 0)),
            session_history=[
                _SessionHistoryEntry.from_dict(d) for d in data.get("session_history", [])
            ],
            last_auction_day=dict(data.get("last_auction_day", {})),
            next_auction_day=dict(data.get("next_auction_day", {})),
            recent_bid_categories=list(data.get("recent_bid_categories", [])),
            rival_session_attendance={
                k: list(v) for k, v in data.get("rival_session_attendance", {}).items()
            },
            won_lots=list(data.get("won_lots", [])),
            speed_setting=str(data.get("speed_setting", DEFAULT_SPEED_SETTING)),
            lifecycle=lifecycle,
            round_state=rs,
            session_personas=list(data.get("session_personas", [])),
            session_lot_results=[
                _LotResultRecord.from_dict(d) for d in data.get("session_lot_results", [])
            ],
            seconds_since_last_bid=float(data.get("seconds_since_last_bid", 0.0)),
            auction_lots_won_total=int(data.get("auction_lots_won_total", 0)),
            auction_lots_won_stellaris=int(data.get("auction_lots_won_stellaris", 0)),
            # SA-B4: defaults to 0 when loading saves authored before
            # SA-B4 lands (no migration needed).
            auction_lots_won_reach=int(data.get("auction_lots_won_reach", 0)),
            auction_rivals_retired=int(data.get("auction_rivals_retired", 0)),
            auction_perfect_reads=int(data.get("auction_perfect_reads", 0)),
            # SA-B5: defaults to empty / zero for saves authored before
            # SA-B5 (decision §B5 / design doc §8.3 migration discipline).
            active_listings=[_PlayerListing.from_dict(d) for d in data.get("active_listings", [])],
            listing_history=[dict(entry) for entry in data.get("listing_history", [])],
            auction_listings_sold=int(data.get("auction_listings_sold", 0)),
            auction_listings_attempted=int(data.get("auction_listings_attempted", 0)),
            auction_listing_fees_paid=int(data.get("auction_listing_fees_paid", 0)),
        )


# Type alias used by the game.py wiring for the journal/news/achievement
# hand-off callbacks. Callbacks are optional; the AuctionState defaults
# to no-ops when the engine isn't supplying them (e.g., in scenario tests).
LifecycleHook = Callable[[str, dict[str, Any]], None]


__all__ = [
    "APPRAISAL_BONUS_LEVEL_1",
    "APPRAISAL_BONUS_LEVEL_2",
    "APPRAISAL_BONUS_LEVEL_3",
    "APPRAISAL_BONUS_LEVEL_4",
    "CHAMPION_WINS_AT_STELLARIS",
    "HEADLINER_CAP_PER_SESSION",
    "PERFECT_READ_THRESHOLD",
    "REACH_SESSION_SIZE",
    "RECENTLY_SEEN_EXCLUSION",
    "SABLE_CEILING_CORRECT_THRESHOLD",
    "SABLE_CEILING_JITTER_FACTOR",
    "SAFE_EXIT_STATES",
    "STELLARIS_CADENCE_MAX_DAYS",
    "STELLARIS_CADENCE_MIN_DAYS",
    "STELLARIS_HEADLINER_SESSION_SIZE",
    "STELLARIS_KADE_TARGET_FACTIONS",
    "STELLARIS_PRENTISS_ATTENDANCE_RATE",
    "STELLARIS_SEASON_CYCLE_DAYS",
    "STELLARIS_SEASON_TAGS",
    "STELLARIS_STANDARD_SESSION_SIZE",
    "STELLARIS_TIER_APPRENTICE_MAX",
    "STELLARIS_TIER_CERTIFIED_MAX",
    "STELLARIS_TIER_REGULAR_MAX",
    "AuctionLifecycle",
    "AuctionState",
    "appraisal_band_for_bonus",
    "current_season_tag",
    "generate_lot_pool",
    "pick_stellaris_rival_attendance",
    "post_win_valuation_message",
    "reserve_band_for_preview",
    "sable_displayed_ceiling",
    "stellaris_initial_session_day",
    "stellaris_tier_for_standing",
]
