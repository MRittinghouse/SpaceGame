"""SA-1 Wreckers' Guild Hall: organization config, contracts, runtime state.

Layered on top of :mod:`spacegame.models.sub_reputation` (SA-B-EXT-1). The
contract registry is a tuple of frozen dataclasses so module-level content
stays Scanner B-clean (CLAUDE.md cross-cutting table; SI-2 cookbook).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from spacegame.models.sub_reputation import (
    OrganizationConfig,
    OrganizationTier,
    get_tier_for_rep,
)

# ---------------------------------------------------------------------------
# Tunables (decisions locked in the SA-1 plan; risks/open-questions section)
# ---------------------------------------------------------------------------

# Window length for visit-triggered slot rerolls. Per the plan:
#   "24 days is long enough that an active contract will resolve within a
#    single window for nearly every player but short enough that re-visits
#    feel productive."
SLOT_REFRESH_WINDOW_DAYS = 24

# Minimum / maximum contract slots presented per visit (acceptance #3).
SLOT_OFFER_MIN = 3
SLOT_OFFER_MAX = 5

# Failure consequence shape (acceptance #5; locked in the risks table).
LOCKOUT_DAYS = 3
SUB_REP_FAILURE_PENALTY = 5

# Soft-deadline tier multipliers reused across all contracts. The Wrecker's
# Guild registers its lateness as a sub-rep penalty rather than a payout
# decay — keeping payout flat above the late-multiplier prevents a lockout +
# half-pay double-hit. Drift, not fail (TW invariant).
APPRENTICE_PARTIAL_MULTIPLIER = 0.85
APPRENTICE_LATE_MULTIPLIER = 0.7

# Tier payout multipliers (acceptance #7).
_TIER_PAYOUT_MULTIPLIER: dict[str, float] = {
    "unjoined": 1.0,
    "apprentice": 1.0,
    "journeyman": 1.10,
    "master": 1.25,
}


WRECKERS_GUILD_CONFIG = OrganizationConfig(
    id="wreckers_guild",
    name="Wreckers' Guild",
    tiers=(
        OrganizationTier(id="unjoined", name="Unjoined", rank=0, min_rep=0),
        OrganizationTier(id="apprentice", name="Apprentice", rank=1, min_rep=1),
        OrganizationTier(id="journeyman", name="Journeyman", rank=2, min_rep=30),
        OrganizationTier(id="master", name="Master", rank=3, min_rep=70),
    ),
    min_rep=0,
    max_rep=100,
)


# ---------------------------------------------------------------------------
# Contract template (frozen — module-level content table)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WreckersContractTemplate:
    """A Wreckers' Guild contract offer.

    Templates are immutable definitions. Active contracts are runtime
    Mission instances created from a template via the view's accept flow.

    Attributes:
        id: Stable snake_case identifier.
        name: Display name for the board entry.
        category: One of "cleanup" / "recovery" / "escort_salvage" /
            "deep_derelict". Used for tier gating + presentation.
        tier_required: Minimum tier ID to see this template.
        target_commodity_id: Commodity the player must deliver.
        target_quantity: Units required.
        base_payout_credits: Credits granted at apprentice-tier turn-in
            before tier multiplier.
        soft_deadline_days: Game days from accept to soft deadline.
            Past the deadline the contract auto-fails on next view entry.
        sub_rep_reward: Sub-rep granted on turn-in (before any clamps).
        briefing: Malia's voice; what the contract is and why.
        turn_in_line: Malia's voice; one line on completion.
        forced_encounter_id: Optional EncounterDefinition.id; non-empty
            for escort_salvage templates that thread combat into travel.
    """

    id: str
    name: str
    category: str
    tier_required: str
    target_commodity_id: str
    target_quantity: int
    base_payout_credits: int
    soft_deadline_days: int
    sub_rep_reward: int
    briefing: str
    turn_in_line: str
    forced_encounter_id: str = ""


WRECKERS_CONTRACT_TEMPLATES: tuple[WreckersContractTemplate, ...] = (
    # === Cleanup (apprentice-tier) ===
    WreckersContractTemplate(
        id="cleanup_scrap_haul",
        name="Scrap Haul: Outer Lanes",
        category="cleanup",
        tier_required="apprentice",
        target_commodity_id="scrap_metal",
        target_quantity=8,
        base_payout_credits=320,
        soft_deadline_days=18,
        sub_rep_reward=2,
        briefing=(
            "Outer-lane debris is fouling approach vectors. Eight crates of "
            "scrap metal off the books, no manifest, brought back here. "
            "Easy work for steady hands. Pays the rent."
        ),
        turn_in_line=(
            "Eight crates, weighed in. You did the work. Take the credits."
        ),
    ),
    WreckersContractTemplate(
        id="cleanup_salvaged_electronics",
        name="Drift Pickings: Salvaged Boards",
        category="cleanup",
        tier_required="apprentice",
        target_commodity_id="salvaged_electronics",
        target_quantity=5,
        base_payout_credits=380,
        soft_deadline_days=20,
        sub_rep_reward=2,
        briefing=(
            "Five units of salvaged electronics from the drift pickings. "
            "Older boards mostly. We test them before we sell them. The "
            "Reach buyer doesn't ask where they came from. We don't ask "
            "where they go."
        ),
        turn_in_line=(
            "Boards check out. Some of these might even still boot. "
            "Credits in your account."
        ),
    ),
    # === Recovery (journeyman-gated) ===
    WreckersContractTemplate(
        id="recovery_rare_parts",
        name="Recovery Job: Inner-Hull Components",
        category="recovery",
        tier_required="journeyman",
        target_commodity_id="rare_parts",
        target_quantity=4,
        base_payout_credits=720,
        soft_deadline_days=22,
        sub_rep_reward=3,
        briefing=(
            "Four rare parts off the inner-hull recovery list. Clean pull, "
            "documented chain of custody. The Guild covers your overhead "
            "if the wreck shifts on you. Bring them back here intact."
        ),
        turn_in_line=(
            "Four parts, all on the list. Paz and Daro can use these. "
            "Solid work."
        ),
    ),
    WreckersContractTemplate(
        id="recovery_alloy_composite",
        name="Recovery Job: Composite Plating",
        category="recovery",
        tier_required="journeyman",
        target_commodity_id="alloy_composite",
        target_quantity=6,
        base_payout_credits=820,
        soft_deadline_days=24,
        sub_rep_reward=3,
        briefing=(
            "Six units of alloy composite off a Forgeworks-class hull, "
            "main-belt scatter. Heavy haul, watch your cargo balance on "
            "the run home. Daro's been waiting on plating for the West "
            "Bay refit."
        ),
        turn_in_line=(
            "Six crates, weighed and logged. Daro's patching a hauler "
            "with this tonight. Credits are yours."
        ),
    ),
    # === Escort-salvage (journeyman-gated; forced_encounter on travel) ===
    WreckersContractTemplate(
        id="escort_salvage_weapons_components",
        name="Escort Salvage: Contested Drift",
        category="escort_salvage",
        tier_required="journeyman",
        target_commodity_id="weapons_components",
        target_quantity=3,
        base_payout_credits=950,
        soft_deadline_days=20,
        sub_rep_reward=4,
        briefing=(
            "Three crates of weapons components off a contested drift. "
            "Pirate scouts have been working that lane. Bring backup or "
            "bring speed. Either way, bring the crates back."
        ),
        turn_in_line=(
            "Three crates, no questions. The Guild appreciates a clean "
            "delivery on a dirty run."
        ),
        forced_encounter_id="pirate_scout_intercept",
    ),
    # === Deep-derelict (master-gated) ===
    WreckersContractTemplate(
        id="deep_derelict_purified_crystal",
        name="Deep Derelict: Crystal Recovery",
        category="deep_derelict",
        tier_required="master",
        target_commodity_id="purified_crystal",
        target_quantity=4,
        base_payout_credits=1600,
        soft_deadline_days=28,
        sub_rep_reward=5,
        briefing=(
            "Four units of purified crystal from a deep derelict. "
            "Old hull, bad orientation, partial atmosphere. Ife has the "
            "approach chart drafted. You know the work. We split the "
            "risk on a job like this."
        ),
        turn_in_line=(
            "Four crates of crystal. That wreck's been refusing visitors "
            "for a year. Good run."
        ),
    ),
)


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def payout_multiplier_for_tier(tier_id: str) -> float:
    """Return the payout multiplier for a given tier id.

    Returns 1.0 for unknown tier ids — this is a defensive default for
    pre-enrollment turn-ins that should never happen in production but
    should not crash if they do.
    """
    return _TIER_PAYOUT_MULTIPLIER.get(tier_id, 1.0)


def templates_for_tier(
    templates: tuple[WreckersContractTemplate, ...],
    tier_id: str,
) -> list[WreckersContractTemplate]:
    """Return templates the given tier is eligible to roll on the board.

    Lower tiers see only their own tier's pool; higher tiers see all
    lower-tier pools too. Unjoined sees nothing — the player has to
    enroll with Malia at the Hall first.
    """
    tier_rank = _rank_for_tier_id(tier_id)
    if tier_rank <= 0:
        return []
    eligible: list[WreckersContractTemplate] = []
    for tpl in templates:
        if _rank_for_tier_id(tpl.tier_required) <= tier_rank:
            eligible.append(tpl)
    return eligible


def _rank_for_tier_id(tier_id: str) -> int:
    """Map a tier id to its rank using :data:`WRECKERS_GUILD_CONFIG`.

    Returns -1 for unknown ids so callers can treat them as below-floor.
    """
    for tier in WRECKERS_GUILD_CONFIG.tiers:
        if tier.id == tier_id:
            return tier.rank
    return -1


def seed_for_window(game_day: int) -> int:
    """Return the slot-refresh window index for a given game day.

    Windows are :data:`SLOT_REFRESH_WINDOW_DAYS` long, starting at day 0.
    """
    return game_day // SLOT_REFRESH_WINDOW_DAYS


def roll_offers(
    player_seed_token: str,
    game_day: int,
    tier_id: str,
    *,
    templates: tuple[WreckersContractTemplate, ...] = WRECKERS_CONTRACT_TEMPLATES,
) -> list[str]:
    """Deterministically roll the contract slot list for a visit.

    The seed is ``f"{window}_{player_seed_token}_wreckers"`` so two
    visits inside the same window produce the same offers and a window
    rollover produces a fresh roll. The slot count is itself
    deterministic per seed (in [SLOT_OFFER_MIN, SLOT_OFFER_MAX]).

    Args:
        player_seed_token: Caller-supplied player identity token (a
            stable string per save — the player name is fine).
        game_day: Current in-game day.
        tier_id: Player's current Wreckers' Guild tier id.
        templates: Override hook for tests.

    Returns:
        List of template ids in deterministic order.
    """
    eligible = templates_for_tier(templates, tier_id)
    if not eligible:
        return []
    window = seed_for_window(game_day)
    rng = random.Random(f"{window}_{player_seed_token}_wreckers")
    # Slot count is bounded by both the design clamp and the eligible pool —
    # apprentice may have fewer templates than SLOT_OFFER_MIN, in which case
    # we show every eligible template rather than padding with placeholders.
    upper = min(SLOT_OFFER_MAX, len(eligible))
    lower = min(SLOT_OFFER_MIN, upper)
    count = rng.randint(lower, upper) if upper > lower else upper
    sampled = rng.sample(eligible, count)
    return [t.id for t in sampled]


def get_template(template_id: str) -> WreckersContractTemplate | None:
    """Return the template with this id, or None."""
    for tpl in WRECKERS_CONTRACT_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    return None


# ---------------------------------------------------------------------------
# Mutable runtime state
# ---------------------------------------------------------------------------


@dataclass
class WreckersGuildState:
    """Per-save Wreckers' Guild runtime state.

    Stored on :class:`spacegame.models.player.Player` as
    ``wreckers_guild_state``. Sub-rep value lives separately on
    ``Player.sub_reputation["wreckers_guild"]`` per the SA-B-EXT-1
    contract — *enrolled* and *standing* are intentionally orthogonal.

    Attributes:
        enrolled: True once Malia has formally inducted the player.
        lockout_until_day: Game day past which contract accepts unlock
            again. ``0`` means never locked out.
        active_contract_ids: Mission ids currently ACTIVE through the
            Guild — used to filter the board so the same template does
            not double-show. Cleared on turn-in or fail.
        slot_seed_window: The window index :data:`seed_for_window` used
            for the current ``slot_offers``. When the player's current
            window > this value, the view rerolls.
        slot_offers: Cached template ids for the current window's slots.
        promoted_tiers: Tier ids the player has already crossed into.
            Used to suppress repeat promotion banners across saves.
        completed_contract_count: Lifetime number of Wreckers' contracts
            successfully turned in. Powers stat readouts.
    """

    enrolled: bool = False
    lockout_until_day: int = 0
    active_contract_ids: list[str] = field(default_factory=list)
    slot_seed_window: int = -1
    slot_offers: list[str] = field(default_factory=list)
    promoted_tiers: set[str] = field(default_factory=set)
    completed_contract_count: int = 0

    # ---- Lockout ----

    def is_locked_out(self, game_day: int) -> bool:
        """True if the player cannot accept contracts at ``game_day``.

        Lockout includes the lockout day itself; the player regains the
        ability to accept on the following day.
        """
        return game_day <= self.lockout_until_day and self.lockout_until_day > 0

    def apply_lockout(self, game_day: int) -> None:
        """Set ``lockout_until_day`` to ``game_day + LOCKOUT_DAYS``."""
        self.lockout_until_day = game_day + LOCKOUT_DAYS

    def clear_lockout(self) -> None:
        """Reset lockout — invoked after the make-up beat resolves."""
        self.lockout_until_day = 0

    # ---- Contract bookkeeping ----

    def register_active_contract(self, mission_id: str) -> None:
        """Track that a Mission was created for a Wreckers' contract."""
        if mission_id not in self.active_contract_ids:
            self.active_contract_ids.append(mission_id)

    def clear_active_contract(self, mission_id: str) -> None:
        """Remove a mission id from the active list, if present."""
        if mission_id in self.active_contract_ids:
            self.active_contract_ids.remove(mission_id)

    # ---- Promotion bookkeeping ----

    def record_promotion(self, tier_id: str) -> bool:
        """Mark a tier promotion as fired. Returns True on first fire."""
        if tier_id in self.promoted_tiers:
            return False
        self.promoted_tiers.add(tier_id)
        return True

    # ---- Serialization ----

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "enrolled": self.enrolled,
            "lockout_until_day": self.lockout_until_day,
            "active_contract_ids": list(self.active_contract_ids),
            "slot_seed_window": self.slot_seed_window,
            "slot_offers": list(self.slot_offers),
            "promoted_tiers": sorted(self.promoted_tiers),
            "completed_contract_count": self.completed_contract_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WreckersGuildState":
        """Restore a :class:`WreckersGuildState` from save data.

        Missing keys default to safe values so legacy saves and partial
        fixtures load without crashing.
        """
        return cls(
            enrolled=bool(data.get("enrolled", False)),
            lockout_until_day=int(data.get("lockout_until_day", 0)),
            active_contract_ids=list(data.get("active_contract_ids", [])),
            slot_seed_window=int(data.get("slot_seed_window", -1)),
            slot_offers=list(data.get("slot_offers", [])),
            promoted_tiers=set(data.get("promoted_tiers", [])),
            completed_contract_count=int(data.get("completed_contract_count", 0)),
        )


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------


def enroll_player_state(
    state: WreckersGuildState,
    sub_reputation: dict[str, int],
) -> tuple[WreckersGuildState, bool]:
    """Enroll the player at apprentice tier (idempotent).

    The plan locks unjoined as the default state; first conversation with
    Malia at the Hall flips both the ``enrolled`` flag and seeds
    ``sub_reputation["wreckers_guild"] = 1``.

    Args:
        state: Current state. Mutated in place AND returned for caller
            convenience (callers may have shadow copies).
        sub_reputation: The player's ``sub_reputation`` dict — mutated
            so the apprentice rep seeds in one call.

    Returns:
        ``(state, granted)``: ``granted`` is True if this call performed
        the enrollment; False if the player was already enrolled.
    """
    if state.enrolled:
        return state, False
    state.enrolled = True
    if sub_reputation.get(WRECKERS_GUILD_CONFIG.id, 0) < 1:
        sub_reputation[WRECKERS_GUILD_CONFIG.id] = 1
    return state, True


def current_tier_id(sub_reputation: dict[str, int]) -> str:
    """Convenience: resolve the player's Wreckers' Guild tier id."""
    value = sub_reputation.get(WRECKERS_GUILD_CONFIG.id, 0)
    return get_tier_for_rep(WRECKERS_GUILD_CONFIG, value).id
