"""SA-B2: Auction lot dataclass and category constants.

A lot is a single item or bundle posted at an auction venue. Lots are
authored as content data and are largely immutable; the only field that
changes between sessions is ``recently_seen_count``, which is updated via
``dataclasses.replace`` so the rest of the lot remains frozen.

See ``requirements/sa_bidding_design.md`` §3 for the schema, the venue
conventions, and the worked examples that drive the unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any, Optional

# Lot category constants (design doc §3.2). These travel with a lot's
# serialized form, so the strings are stable across save versions.
LOT_CATEGORY_MODULE = "module"
LOT_CATEGORY_ANTIQUITY = "antiquity"
LOT_CATEGORY_FACTION_COMMODITY = "faction_commodity"
LOT_CATEGORY_RARE_UPGRADE = "rare_upgrade"
LOT_CATEGORY_DERELICT_RIGHTS = "derelict_rights"
LOT_CATEGORY_CONTRABAND = "contraband"
LOT_CATEGORY_RESTRICTED_WEAPON = "restricted_weapon"
LOT_CATEGORY_SALVAGE_LOT = "salvage_lot"

LOT_CATEGORIES: frozenset[str] = frozenset(
    {
        LOT_CATEGORY_MODULE,
        LOT_CATEGORY_ANTIQUITY,
        LOT_CATEGORY_FACTION_COMMODITY,
        LOT_CATEGORY_RARE_UPGRADE,
        LOT_CATEGORY_DERELICT_RIGHTS,
        LOT_CATEGORY_CONTRABAND,
        LOT_CATEGORY_RESTRICTED_WEAPON,
        LOT_CATEGORY_SALVAGE_LOT,
    }
)

# Venue identifiers. Stable strings; do not rename without a save migration.
VENUE_STELLARIS = "stellaris"
VENUE_CRIMSON_REACH = "crimson_reach"

# Standing tier strings (Stellaris ladder). Reach lots use the Wreckers'
# Guild membership tier strings instead — they share the same field for
# simplicity and the venue determines which ladder applies.
REP_TIER_NONE = "none"
REP_TIER_APPRENTICE = "apprentice"
REP_TIER_REGULAR = "regular"
REP_TIER_CERTIFIED = "certified"
REP_TIER_PATRON = "patron"


@dataclass(frozen=True)
class AuctionLot:
    """A single auctionable lot.

    Frozen so lot data is safe to share across sessions. To bump the
    recently-seen counter, use ``dataclasses.replace(lot,
    recently_seen_count=lot.recently_seen_count + 1)``.

    Attributes:
        id: Unique lot identifier (snake_case, e.g.
            ``"kings_repeater_reissue_lot_2332"``).
        headline: Display name shown in preview and during bidding.
        description: Flavor text paragraph (preview only; collapsed in
            live rounds to keep the live UI tight).
        category: One of ``LOT_CATEGORY_*`` constants.
        venue: ``"stellaris"`` or ``"crimson_reach"``.
        base_appraisal: Fair market value in credits. Used by AI personas
            and (with the right bonuses) revealed to the player after a
            win.
        reserve_pct: Reserve price as a fraction of ``base_appraisal``,
            in the range 0.60 to 0.90.
        faction_gate: Faction id required to see and bid on this lot,
            or ``None`` if unrestricted.
        rep_tier_required: Minimum standing-tier string. ``"none"`` means
            no tier gate.
        is_headliner: True if this lot runs three rounds instead of two.
        season_tag: Seasonal-event tag that doubles pool weight while
            active, or ``None``.
        contraband: True if winning this lot triggers legal-consequence
            checks (Stellaris only; Reach lots are already off the books).
        source_module_id: For module re-issues, the canonical module id
            in ``modules.json`` so the win delivers the right ship part.
        recently_seen_count: How many sessions this lot has spent in the
            pool unsold. ``>= 5`` excludes the lot from the next draw;
            resets to 0 when the lot sells.
        seller_id: ``None`` for catalog lots authored under SA-B3 / SA-B4;
            ``"player"`` for SA-B5 player consignments. The field is
            omitted from ``to_dict`` when ``None`` so prior catalogs
            round-trip byte-for-byte.
    """

    id: str
    headline: str
    description: str
    category: str
    venue: str
    base_appraisal: int
    reserve_pct: float
    faction_gate: Optional[str] = None
    rep_tier_required: str = REP_TIER_NONE
    is_headliner: bool = False
    season_tag: Optional[str] = None
    contraband: bool = False
    source_module_id: Optional[str] = None
    recently_seen_count: int = 0
    seller_id: Optional[str] = None

    @property
    def reserve_price(self) -> int:
        """Hidden reserve price in credits (rounded down).

        Per design doc §3.1 derived property: ``int(base_appraisal *
        reserve_pct)``. Truncation matches the worked example in §3.4
        (28000 * 0.75 = 21000).
        """
        return int(self.base_appraisal * self.reserve_pct)

    def to_dict(self) -> dict[str, Any]:
        """Serialize all fields, including ``recently_seen_count``.

        The dict round-trips losslessly through :meth:`from_dict`. We
        don't emit ``reserve_price`` because it's derived; the consumer
        can compute it on demand.
        """
        out: dict[str, Any] = {
            "id": self.id,
            "headline": self.headline,
            "description": self.description,
            "category": self.category,
            "venue": self.venue,
            "base_appraisal": self.base_appraisal,
            "reserve_pct": self.reserve_pct,
            "faction_gate": self.faction_gate,
            "rep_tier_required": self.rep_tier_required,
            "is_headliner": self.is_headliner,
            "season_tag": self.season_tag,
            "contraband": self.contraband,
            "source_module_id": self.source_module_id,
            "recently_seen_count": self.recently_seen_count,
        }
        # SA-B5: emit ``seller_id`` only when non-None so SA-B3/B4 lot
        # catalogs round-trip byte-for-byte through to_dict / from_dict.
        if self.seller_id is not None:
            out["seller_id"] = self.seller_id
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuctionLot":
        """Deserialize a lot dict using ``data.get`` defaults.

        Required: ``id``, ``headline``, ``description``, ``category``,
        ``venue``, ``base_appraisal``, ``reserve_pct``. Everything else
        defaults to the same values as the dataclass field defaults so
        save migrations are additive.
        """
        return cls(
            id=data["id"],
            headline=data["headline"],
            description=data["description"],
            category=data["category"],
            venue=data["venue"],
            base_appraisal=int(data["base_appraisal"]),
            reserve_pct=float(data["reserve_pct"]),
            faction_gate=data.get("faction_gate"),
            rep_tier_required=data.get("rep_tier_required", REP_TIER_NONE),
            is_headliner=bool(data.get("is_headliner", False)),
            season_tag=data.get("season_tag"),
            contraband=bool(data.get("contraband", False)),
            source_module_id=data.get("source_module_id"),
            recently_seen_count=int(data.get("recently_seen_count", 0)),
            seller_id=data.get("seller_id"),
        )

    def with_recently_seen(self, new_count: int) -> "AuctionLot":
        """Return a copy with ``recently_seen_count`` set to ``new_count``.

        Convenience over ``dataclasses.replace`` so callers don't have to
        import ``replace`` just to bump the counter.
        """
        return replace(self, recently_seen_count=new_count)


# Tier ordering for the lot-pool filter. Higher index = higher tier; a
# lot with ``rep_tier_required == "regular"`` is accessible to any player
# whose tier is at least "regular" (regular, certified, patron). The
# Wreckers' Guild ladder reuses the same comparison via overlap with the
# Stellaris strings (apprentice / journeyman / master / veteran are
# treated as their own ladder elsewhere; SA-B4 maps Reach standing into
# this enum at filter time).
_REP_TIER_ORDER: tuple[str, ...] = (
    REP_TIER_NONE,
    REP_TIER_APPRENTICE,
    REP_TIER_REGULAR,
    REP_TIER_CERTIFIED,
    REP_TIER_PATRON,
)


def rep_tier_at_least(player_tier: str, required_tier: str) -> bool:
    """True if ``player_tier`` meets or exceeds ``required_tier``.

    Unknown tier strings on either side fall back to ``REP_TIER_NONE``,
    which never satisfies a non-``none`` requirement. Keeps the lot pool
    filter resilient against typos in content data.
    """
    try:
        player_idx = _REP_TIER_ORDER.index(player_tier)
    except ValueError:
        player_idx = 0
    try:
        required_idx = _REP_TIER_ORDER.index(required_tier)
    except ValueError:
        return False
    return player_idx >= required_idx


__all__ = [
    "LOT_CATEGORIES",
    "LOT_CATEGORY_ANTIQUITY",
    "LOT_CATEGORY_CONTRABAND",
    "LOT_CATEGORY_DERELICT_RIGHTS",
    "LOT_CATEGORY_FACTION_COMMODITY",
    "LOT_CATEGORY_MODULE",
    "LOT_CATEGORY_RARE_UPGRADE",
    "LOT_CATEGORY_RESTRICTED_WEAPON",
    "LOT_CATEGORY_SALVAGE_LOT",
    "REP_TIER_APPRENTICE",
    "REP_TIER_CERTIFIED",
    "REP_TIER_NONE",
    "REP_TIER_PATRON",
    "REP_TIER_REGULAR",
    "VENUE_CRIMSON_REACH",
    "VENUE_STELLARIS",
    "AuctionLot",
    "rep_tier_at_least",
]


def _all_field_names() -> tuple[str, ...]:
    """Internal: returns dataclass field names (used for round-trip tests)."""
    return tuple(f.name for f in fields(AuctionLot))
