"""SA-P2 venue-based politics dispute system.

Implements the engine for council-chamber-style deliberations: dispute
templates, named delegates with hidden position vectors, three-slot
argument construction, deterministic per-round resolution, coalition
pre-commit corridor, and outcome propagation through reputation,
market, mission flags, and news.

Coexists with the existing ``PoliticsManager`` (ambient inter-faction
events). See ``requirements/sa_politics_design.md`` section 1 for the
coexistence rationale and section 2 for the lifecycle state diagram.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from spacegame.constants.flags import (
    coalition_won,
    dispute_mediated,
    dispute_resolved,
)

if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster
    from spacegame.models.market import Market
    from spacegame.models.news_ticker import NewsTicker
    from spacegame.models.player import Player
    from spacegame.models.politics import PoliticsManager
    from spacegame.models.progression import PlayerProgression
    from spacegame.models.social import SocialManager


# ============================================================================
# Constants and lifecycle enums
# ============================================================================

# Visible-state chain (ordered worst -> best for the "yes" side, per design
# section 4.4). Index in this tuple defines the comparable rank used by the
# state-machine helpers below.
VISIBLE_STATES: tuple[str, ...] = (
    "committed_no",
    "leaning_no",
    "wavering",
    "leaning_yes",
    "committed_yes",
)

# Outcome categories (design section 5.1). Ordered for stable iteration.
OUTCOME_CATEGORIES: tuple[str, ...] = (
    "win",
    "partial_win_coalition_thin",
    "partial_win_off_record",
    "loss",
)

# Dispositional formula constants from social.py (see design section 4.3).
_DISPOSITION_DEFAULT = 50
_DISPOSITION_STEP = 10

# Per-argument position-vector deltas (design section 4.4).
_ARG_PASS_DELTA = 0.20
_COUNTER_DELTA = -0.15
_MEDIATE_DELTA = 0.10
_POSITION_CAP = 1.0

# Bias-init contribution per delegate (design section 4.5).
_FACTION_LOYALTY_PRIOR_BIAS_DISPOSITION = 5

# Coalition-thin threshold (design section 5.1 and §11 decision 5).
_COALITION_THIN_THRESHOLD = 0.60

# Skill routing (design section 6.4).
_LEADERSHIP_FRAMINGS: frozenset[str] = frozenset({"frontier_autonomy"})

# News-ticker thresholds (design section 7.6).
_TIER_BOUNDARIES: tuple[int, ...] = (-75, -25, 25, 75)
_NEWS_COMMODITY_MAGNITUDE = 0.10

# Market-shift duration (design section 7.2; locked).
DEFAULT_MARKET_SHIFT_DURATION = 30


class DisputePhase(Enum):
    """Lifecycle states for a single dispute (design section 2.5)."""

    CREATED = "created"
    ROUND_OPEN = "round_open"
    ROUND_PENDING = "round_pending"
    RESOLVING = "resolving"
    RESOLVED = "resolved"


# ============================================================================
# Frozen template dataclasses (loaded from JSON or built in tests)
# ============================================================================


@dataclass(frozen=True)
class PoliticsMarketShift:
    """Time-bounded commodity-price multiplier emitted by a dispute outcome.

    Magnitude is a fractional multiplier (e.g., +0.10 = +10% price for the
    duration window). Stack rule (design §11 decision 14): when two active
    shifts target the same (commodity_id, system_id), the larger absolute
    magnitude applies. Shifts decay independently after their own
    duration_days expire.
    """

    commodity_id: str
    system_id: str
    magnitude: float
    duration_days: int = DEFAULT_MARKET_SHIFT_DURATION
    start_day: int = 0


@dataclass(frozen=True)
class OutcomeRow:
    """Outcome propagation matrix entry for one outcome category.

    Each dispute template carries one OutcomeRow per category (`win`,
    `partial_win_coalition_thin`, `partial_win_off_record`, `loss`).
    """

    rep_deltas: dict[str, int] = field(default_factory=dict)
    market_shifts: tuple[PoliticsMarketShift, ...] = ()
    mission_unlocks: tuple[str, ...] = ()
    mission_locks: tuple[str, ...] = ()
    news_headline: Optional[str] = None


@dataclass(frozen=True)
class DelegateTemplate:
    """Per-dispute starting state for a named delegate.

    Carries the hidden position vector, starting visible state, faction
    loyalty / prior-memory biases, and the sub-tier faction id used when
    a corridor visit fails (design section 5.5 + Risks open question).
    """

    delegate_id: str
    name: str
    starting_visible_state: str
    position_vector: dict[str, float] = field(default_factory=dict)
    faction_loyalty: float = 0.0
    prior_dispute_memory: int = -1
    sub_faction_id: str = ""


@dataclass(frozen=True)
class PoliticsDisputeTemplate:
    """Frozen dispute template loaded from data/politics/*.json.

    Carries everything needed to instantiate a runtime
    :class:`PoliticsDispute`: schema fields from design section 3.1, the
    delegate roster (with starting positions), eligible framings /
    evidence, and the four-row outcome matrix.
    """

    id: str
    headline: str
    factions_affected: tuple[str, ...]
    base_difficulty: int
    round_count: int
    deadline_days: int
    delegates: tuple[DelegateTemplate, ...]
    eligible_framings: tuple[str, ...]
    eligible_evidence: tuple[str, ...]
    framing_modifiers: dict[str, int]
    framing_target_dimensions: dict[str, str]
    outcome_matrix: dict[str, OutcomeRow]
    is_campaign_arc: bool = False
    required_flags: tuple[str, ...] = ()


# ============================================================================
# Mutable runtime classes
# ============================================================================


@dataclass
class PoliticsDelegate:
    """Runtime mutable delegate state inside a dispute session.

    Instantiated by the manager when a dispute opens, mutated as the
    player argues / mediates / pre-commits. Position vector caps at
    +/-1.0 per design section 4.4.
    """

    delegate_id: str
    name: str
    visible_state: str
    position_vector: dict[str, float]
    disposition: int = _DISPOSITION_DEFAULT
    faction_loyalty: float = 0.0
    sub_faction_id: str = ""
    pre_committed: bool = False
    conceded: bool = False
    consecutive_corridor_fails: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the runtime delegate state for the save system."""
        return {
            "delegate_id": self.delegate_id,
            "name": self.name,
            "visible_state": self.visible_state,
            "position_vector": dict(self.position_vector),
            "disposition": self.disposition,
            "faction_loyalty": self.faction_loyalty,
            "sub_faction_id": self.sub_faction_id,
            "pre_committed": self.pre_committed,
            "conceded": self.conceded,
            "consecutive_corridor_fails": self.consecutive_corridor_fails,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PoliticsDelegate:
        """Restore from serialized data; missing keys default to safe values."""
        return cls(
            delegate_id=data["delegate_id"],
            name=data.get("name", data["delegate_id"]),
            visible_state=data.get("visible_state", "wavering"),
            position_vector=dict(data.get("position_vector", {})),
            disposition=data.get("disposition", _DISPOSITION_DEFAULT),
            faction_loyalty=data.get("faction_loyalty", 0.0),
            sub_faction_id=data.get("sub_faction_id", ""),
            pre_committed=data.get("pre_committed", False),
            conceded=data.get("conceded", False),
            consecutive_corridor_fails=data.get("consecutive_corridor_fails", 0),
        )


@dataclass
class PoliticsArgument:
    """Player-composed argument (design section 6.1).

    Composer state lives here while the player is selecting; the
    manager consumes it on submit and emits a deterministic resolution.
    Mid-composition state is not serialized (design section 11 decision
    4 -- round-boundary save granularity).
    """

    framing: str
    audience_delegate_id: str
    evidence: Optional[str] = None
    responds_to: Optional[str] = None
    is_mediation: bool = False


@dataclass
class PoliticsDispute:
    """Runtime mutable dispute instance.

    Persisted at round boundaries via :meth:`to_dict` / :meth:`from_dict`.
    Mid-round composer state is not saved (design section 2.6).
    """

    dispute_id: str
    template_id: str
    headline: str
    factions_affected: tuple[str, ...]
    base_difficulty: int
    round_count: int
    closes_on_day: int
    delegates: dict[str, PoliticsDelegate]
    eligible_framings: tuple[str, ...]
    eligible_evidence: tuple[str, ...]
    framing_modifiers: dict[str, int]
    framing_target_dimensions: dict[str, str]
    outcome_matrix: dict[str, OutcomeRow]
    current_round: int = 1
    phase: DisputePhase = DisputePhase.CREATED
    resolved_outcome: Optional[str] = None
    round_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the committed dispute state (round-boundary granularity)."""
        return {
            "dispute_id": self.dispute_id,
            "template_id": self.template_id,
            "headline": self.headline,
            "factions_affected": list(self.factions_affected),
            "base_difficulty": self.base_difficulty,
            "round_count": self.round_count,
            "closes_on_day": self.closes_on_day,
            "delegates": {did: d.to_dict() for did, d in self.delegates.items()},
            "eligible_framings": list(self.eligible_framings),
            "eligible_evidence": list(self.eligible_evidence),
            "framing_modifiers": dict(self.framing_modifiers),
            "framing_target_dimensions": dict(self.framing_target_dimensions),
            "current_round": self.current_round,
            "phase": self.phase.value,
            "resolved_outcome": self.resolved_outcome,
            "round_log": list(self.round_log),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        outcome_matrix: dict[str, OutcomeRow],
    ) -> PoliticsDispute:
        """Restore from save data (design §11 decision 15: every field defaulted).

        ``outcome_matrix`` is supplied separately from the live template
        registry rather than persisted, so post-SA-P2 template tweaks
        carry through to in-flight saved disputes without migration.
        """
        return cls(
            dispute_id=data["dispute_id"],
            template_id=data["template_id"],
            headline=data.get("headline", ""),
            factions_affected=tuple(data.get("factions_affected", ())),
            base_difficulty=data.get("base_difficulty", 4),
            round_count=data.get("round_count", 3),
            closes_on_day=data.get("closes_on_day", 0),
            delegates={
                did: PoliticsDelegate.from_dict(d)
                for did, d in data.get("delegates", {}).items()
            },
            eligible_framings=tuple(data.get("eligible_framings", ())),
            eligible_evidence=tuple(data.get("eligible_evidence", ())),
            framing_modifiers=dict(data.get("framing_modifiers", {})),
            framing_target_dimensions=dict(
                data.get("framing_target_dimensions", {})
            ),
            outcome_matrix=outcome_matrix,
            current_round=data.get("current_round", 1),
            phase=DisputePhase(data.get("phase", DisputePhase.CREATED.value)),
            resolved_outcome=data.get("resolved_outcome"),
            round_log=list(data.get("round_log", [])),
        )


# ============================================================================
# Helper functions
# ============================================================================


def _visible_index(state: str) -> int:
    """Rank index in the visible-state chain. Unknown states clamp to wavering."""
    try:
        return VISIBLE_STATES.index(state)
    except ValueError:
        return VISIBLE_STATES.index("wavering")


def _shift_visible(state: str, steps: int) -> str:
    """Move a visible state along the chain by ``steps`` (positive = toward yes)."""
    idx = _visible_index(state)
    new_idx = max(0, min(len(VISIBLE_STATES) - 1, idx + steps))
    return VISIBLE_STATES[new_idx]


def _disposition_modifier(disposition: int) -> int:
    """Mirror of :func:`SocialManager.get_effective_level`'s disposition mod.

    Integer-divides toward negative infinity, exactly as ``social.py``
    does at line 275.
    """
    return (disposition - _DISPOSITION_DEFAULT) // _DISPOSITION_STEP


def _floor(value: float) -> int:
    """Stable wrapper around :func:`math.floor` so callers read floor()."""
    return math.floor(value)


# ============================================================================
# Manager
# ============================================================================


class PoliticsDisputeManager:
    """Orchestrates dispute lifecycle, resolution, and outcome propagation.

    One manager instance per game. Holds references to the cross-cutting
    systems the resolver needs (politics_manager for spillover-aware rep
    deltas, news_ticker for headlines, market for shift registry,
    crew_roster + progression + social_manager for skill bonuses).
    Mutates the supplied :class:`Player` for outcome state.
    """

    def __init__(
        self,
        templates: Optional[dict[str, PoliticsDisputeTemplate]] = None,
        politics_manager: Optional["PoliticsManager"] = None,
        news_ticker: Optional["NewsTicker"] = None,
        crew_roster: Optional["CrewRoster"] = None,
        progression: Optional["PlayerProgression"] = None,
        social_manager: Optional["SocialManager"] = None,
        market_lookup: Optional[Any] = None,
    ) -> None:
        """Build the manager.

        Args:
            templates: ``{template_id: PoliticsDisputeTemplate}``. Empty dict
                or ``None`` is fine for tests / engine-only smoke runs.
            politics_manager: Source of ``apply_reputation_with_spillover``.
                Optional in tests that don't assert rep propagation.
            news_ticker: Sink for ``add_headline``. Optional.
            crew_roster: Source of ``get_bonus("coalition_sway_bonus")``,
                ``arbitration_neutrality_bonus``, ``coalition_size_bonus``,
                ``arbitration_dispute_intel``. Optional.
            progression: Source of ``get_bonus(...)`` for the same bonus
                types as crew_roster. Optional.
            social_manager: Source of ``get_effective_level`` /
                ``resolve_check`` for argue/mediate skill checks and
                corridor pre-commit checks. Optional in unit tests.
            market_lookup: Callable ``(system_id) -> Market`` so the
                manager can register politics market shifts on the
                affected system's market. Optional.
        """
        self._templates: dict[str, PoliticsDisputeTemplate] = dict(templates or {})
        self._politics_manager = politics_manager
        self._news_ticker = news_ticker
        self._crew_roster = crew_roster
        self._progression = progression
        self._social_manager = social_manager
        self._market_lookup = market_lookup

        # Per-session ephemeral state (reset on session leave).
        self._intel_revealed_this_session: bool = False
        self._active_session_venue: Optional[str] = None
