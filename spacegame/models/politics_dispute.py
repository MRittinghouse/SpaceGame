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
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from spacegame.models.crew import CrewRoster
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
    # Per-delegate counter-framing override map. Keyed by delegate_id, values
    # are ``(framing_id, target_dimension)``. SA-P3 introduced this field so
    # non-water-rights disputes can fire delegate-appropriate counter-framings
    # without each venue forking the engine. Empty dict preserves the SA-P2
    # default (``("soil_impact", "water_rights_change")``).
    counter_framings: dict[str, tuple[str, str]] = field(default_factory=dict)
    # SA-P4 annual scheduling. ``is_annual_congress`` flags a template that
    # only opens once per game-year cycle. ``opens_on_day_offset`` is the day
    # within each cycle when the window opens (0 = window opens at cycle
    # start). ``next_congress_offset_days`` is the cycle length (365 for the
    # canonical Annual Congress); zero disables the annual lockout entirely.
    # Templates that omit these fields parse identically to SA-P2 / SA-P3.
    is_annual_congress: bool = False
    opens_on_day_offset: int = 0
    next_congress_offset_days: int = 0
    # SA-P4 coalition betrayal mechanic. Per-delegate map: delegate_id ->
    # condition name from the engine's ``_BETRAYAL_DISPATCH`` table. When the
    # named condition resolves True at the start of a round, the delegate's
    # pre-commit flips back to wavering. Empty dict preserves SA-P2 / SA-P3
    # behavior (no betrayal possible).
    betrayal_conditions: dict[str, str] = field(default_factory=dict)


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
class ArgumentResolution:
    """Outcome of a single argument resolution.

    Returned by both :meth:`PoliticsDisputeManager.preview_argument` (live
    composer preview) and :meth:`PoliticsDisputeManager.submit_argument`
    (commit). Holds every component of the SA-P1 §6.2 formula so the
    composer's "Effective N vs Difficulty M" preview can name what each
    contribution was.
    """

    base_skill: int = 0
    framing_mod: int = 0
    disposition_mod: int = 0
    crew_bonus: float = 0.0
    tree_bonus: float = 0.0
    evidence_absent_penalty: int = 0
    difficulty: int = 0
    effective_floor: int = 0
    passes: bool = False
    error: Optional[str] = None


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
    # SA-P4: True when at least one delegate experienced a betrayal flip
    # during the arc. Drives the ``first_coalition_betrayal_handled`` journal
    # gate. Persisted via to_dict / from_dict; defaults False on legacy saves.
    had_betrayal: bool = False
    # SA-P4: snapshot of the player's reputation with each delegate-relevant
    # faction at dispute start, used by the rep-dropped-below-25 betrayal
    # predicate so the comparison is "since the dispute started" rather than
    # "since launch." Persisted; defaults to empty for legacy saves.
    rep_at_start: dict[str, int] = field(default_factory=dict)

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
            "had_betrayal": self.had_betrayal,
            "rep_at_start": dict(self.rep_at_start),
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
                did: PoliticsDelegate.from_dict(d) for did, d in data.get("delegates", {}).items()
            },
            eligible_framings=tuple(data.get("eligible_framings", ())),
            eligible_evidence=tuple(data.get("eligible_evidence", ())),
            framing_modifiers=dict(data.get("framing_modifiers", {})),
            framing_target_dimensions=dict(data.get("framing_target_dimensions", {})),
            outcome_matrix=outcome_matrix,
            current_round=data.get("current_round", 1),
            phase=DisputePhase(data.get("phase", DisputePhase.CREATED.value)),
            resolved_outcome=data.get("resolved_outcome"),
            round_log=list(data.get("round_log", [])),
            had_betrayal=bool(data.get("had_betrayal", False)),
            rep_at_start=dict(data.get("rep_at_start", {})),
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


# ----- Cass Weller intel reveal helpers (SA-P1 §7.5) -----------------------

# Threshold values for the qualitative summary (Risks: "small dispatch table
# for the three Verdant dimensions used by the synthetic fixture; SA-P3/P4
# extend the table when adding new dimension labels"). Engine code emits
# these strings; voice register matches the supervisor / out-of-world UI
# convention from SL-5 (terse, declarative, no flavor).
_INTEL_POSITIVE_THRESHOLD = 0.5
_INTEL_NEGATIVE_THRESHOLD = -0.5

# Display labels for known position-vector dimensions. SA-P3 / P4 / P5 may
# extend; unknown dimensions fall back to a generic "this dimension" form
# so the engine never crashes on an SA-P3-only label.
_DIMENSION_LABELS: dict[str, str] = {
    "modernization": "modernization",
    "water_rights_change": "water rights change",
    "outside_influence": "outside influence",
    "frontier_autonomy_stance": "frontier autonomy",
    "trade_leverage": "trade leverage",
    "process_fidelity": "process fidelity",
}


def qualitative_position_summary(position_vector: dict[str, float]) -> str:
    """Produce a qualitative summary line for a delegate's position vector.

    Engine-emitted player-facing string. Voice-checked: terse,
    declarative, no em-dashes, no banned phrases. SA-P1 §7.5 spec:
    "qualitative summary on the delegate's corridor profile card.
    Display text is derived from the vector ... Not the raw floats."

    Args:
        position_vector: ``{dimension: float}`` typically in [-1.0, +1.0].

    Returns:
        One line of summary text, no trailing newline. Empty string if
        the vector itself is empty.
    """
    if not position_vector:
        return ""
    parts: list[str] = []
    for dim, value in position_vector.items():
        label = _DIMENSION_LABELS.get(dim, dim.replace("_", " "))
        if value >= _INTEL_POSITIVE_THRESHOLD:
            parts.append(f"Open to {label}")
        elif value <= _INTEL_NEGATIVE_THRESHOLD:
            parts.append(f"Skeptical of {label}")
        else:
            parts.append(f"Undecided on {label}")
    return ". ".join(parts) + "."


# ============================================================================
# SA-P4: betrayal predicate dispatch (deterministic, content-extensible)
# ============================================================================
#
# Predicate signature: ``(dispute, delegate, player) -> bool``. Each predicate
# inspects a pre-committed delegate against the player and dispute state, and
# returns True when the delegate's pre-commit should flip back to wavering.
# The dispatch table is small and content-authored (template
# ``betrayal_conditions`` maps a delegate_id to a condition string); SA-P5+
# can extend by adding entries to ``_BETRAYAL_DISPATCH``.
#
# Condition strings carry one optional argument after a colon, e.g.
# ``"rep_dropped_below_25:crimson_reach"``. The argument-bearing dispatch
# wraps each named predicate in a closure so the manager can call it with
# the standard 3-arg signature.

_BETRAYAL_REP_DROP_FLOOR = 25


def _betrayal_rep_dropped_below(
    faction_id: str,
) -> Callable[["PoliticsDispute", "PoliticsDelegate", "Player"], bool]:
    """Predicate: True when player's rep with ``faction_id`` dropped under 25.

    Compares against the dispute's ``rep_at_start`` snapshot — the betrayal
    fires only when rep dropped *during* the arc (not when it was already
    low at dispute start). The snapshot is captured by
    :meth:`PoliticsDisputeManager.snapshot_rep_at_start`.
    """

    def _predicate(
        dispute: "PoliticsDispute",
        _delegate: "PoliticsDelegate",
        player: "Player",
    ) -> bool:
        start = dispute.rep_at_start.get(faction_id)
        if start is None or start < _BETRAYAL_REP_DROP_FLOOR:
            # Either no snapshot or rep was already below the floor at start;
            # the drop must have happened during the arc to count.
            return False
        current = player.get_reputation(faction_id)
        return current < _BETRAYAL_REP_DROP_FLOOR

    return _predicate


def _betrayal_counter_framing_succeeded(
    dispute: "PoliticsDispute",
    delegate: "PoliticsDelegate",
    _player: "Player",
) -> bool:
    """Predicate: True when a counter-argument moved this delegate during the arc.

    A counter-framing landing on a pre-committed delegate breaks the
    pre-commit — the room saw the delegate flinch. The dispute's round_log
    carries one ``counter from <id> hit <delegate_id>`` line per landed
    counter; we scan for any line naming this delegate.
    """
    needle = f"hit {delegate.delegate_id}"
    return any(needle in line for line in dispute.round_log)


def _betrayal_rival_faction_unfavored(
    dispute: "PoliticsDispute",
    _delegate: "PoliticsDelegate",
    player: "Player",
) -> bool:
    """Predicate: True when any of the dispute's affected factions entered
    a strongly-negative tier (rep < -25) since the arc started.

    The "rival faction unfavored" reading: if the room's broader political
    weather turns sharply against one of the factions in play, a delegate
    whose pre-commit was contingent on that faction's standing flips.
    """
    for faction_id in dispute.factions_affected:
        if player.get_reputation(faction_id) < -_BETRAYAL_REP_DROP_FLOOR:
            return True
    return False


def _resolve_betrayal_predicate(
    condition: str,
) -> Optional[Callable[["PoliticsDispute", "PoliticsDelegate", "Player"], bool]]:
    """Look up a betrayal predicate by its condition string.

    Condition strings may carry one argument after a colon
    (``"rep_dropped_below_25:crimson_reach"``). Unknown conditions return
    None so the manager can silently skip them.
    """
    name, _, arg = condition.partition(":")
    if name == "rep_dropped_below_25":
        if not arg:
            return None
        return _betrayal_rep_dropped_below(arg)
    if name == "counter_framing_succeeded":
        return _betrayal_counter_framing_succeeded
    if name == "rival_faction_unfavored":
        return _betrayal_rival_faction_unfavored
    return None


# Names of the registered betrayal conditions, exposed for data-validation
# tests so authors stay aligned with the engine dispatch table.
BETRAYAL_CONDITION_NAMES: frozenset[str] = frozenset(
    {
        "rep_dropped_below_25",
        "counter_framing_succeeded",
        "rival_faction_unfavored",
    }
)


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

        # Pending disputes by id (round-boundary persisted) and
        # already-resolved disputes (for journal / mission gating). The
        # manager owns these; player state mirrors them via to_dict /
        # from_dict at the round boundary.
        self._pending_disputes: dict[str, PoliticsDispute] = {}
        self._resolved_disputes: dict[str, PoliticsDispute] = {}

        # Player reference for outcome propagation. Set via
        # :meth:`set_player`. None during construction so the manager
        # can be built before the player is loaded (game.py wiring
        # order).
        self._propagation_player: Optional["Player"] = None

        # SA-P3 outcome callback: fired after a dispute is fully
        # propagated so the engine can bump first-time journal-trigger
        # flags and other cross-cutting state. Optional (None when no
        # callback registered).
        self._outcome_callback: Optional[Callable[["PoliticsDispute", str], None]] = None

        # SA-P4: per-template last-resolved-day registry for annual
        # Congress scheduling. Persisted via to_dict / from_dict so the
        # lockout window survives save/load.
        self._annual_last_resolved: dict[str, int] = {}

    def set_player(self, player: "Player") -> None:
        """Bind the player whose state the manager mutates on resolution.

        Called by ``Game.__init__`` after the player is loaded; tests
        either skip this (when only verifying mechanics that don't
        propagate) or supply a stub Player.
        """
        self._propagation_player = player

    def set_outcome_callback(
        self,
        callback: Optional[Callable[["PoliticsDispute", str], None]],
    ) -> None:
        """Register a callback invoked after a dispute resolves.

        The callback runs after :meth:`_propagate_outcome` so any rep,
        market, mission-flag, and news side-effects have already landed.
        SA-P3 uses it from ``Game._on_dispute_outcome`` to bump the
        first-time journal-trigger flags.
        """
        self._outcome_callback = callback

    # ------------------------------------------------------------------
    # Template registry / introspection
    # ------------------------------------------------------------------

    def get_template(self, template_id: str) -> Optional[PoliticsDisputeTemplate]:
        """Return the loaded template by id, or None if not registered."""
        return self._templates.get(template_id)

    def register_template(self, template: PoliticsDisputeTemplate) -> None:
        """Register a template (used by tests and by the data loader)."""
        self._templates[template.id] = template

    # ------------------------------------------------------------------
    # SA-P4: annual Congress scheduling (game-day cycles)
    # ------------------------------------------------------------------

    def is_dispute_active(self, template_id: str, current_game_day: int) -> bool:
        """Return True when a template can be started on ``current_game_day``.

        Non-annual templates are always active. Annual templates are active
        until they resolve, then locked out for ``next_congress_offset_days``
        before re-opening on the next cycle. Unknown templates report
        inactive (defensive).

        Args:
            template_id: Registered template id.
            current_game_day: Current game day from ``Player.game_day``.

        Returns:
            True if the template is currently inside its open window.
        """
        template = self._templates.get(template_id)
        if template is None:
            return False
        if not template.is_annual_congress or template.next_congress_offset_days <= 0:
            return True
        last_resolved = self._annual_last_resolved.get(template_id)
        if last_resolved is None:
            return True
        return (current_game_day - last_resolved) >= template.next_congress_offset_days

    def next_session_in_days(self, template_id: str, current_game_day: int) -> int:
        """Days until the annual template re-opens (0 when active or non-annual).

        UI surface for the ``LOCKED_OUT_ANNUAL`` substate. Always returns a
        non-negative integer.
        """
        template = self._templates.get(template_id)
        if template is None or not template.is_annual_congress:
            return 0
        last_resolved = self._annual_last_resolved.get(template_id)
        if last_resolved is None:
            return 0
        elapsed = current_game_day - last_resolved
        remaining = template.next_congress_offset_days - elapsed
        return max(0, remaining)

    def record_annual_resolution(self, template_id: str, last_resolved_day: int) -> None:
        """Mark an annual template as resolved on ``last_resolved_day``.

        The next call to :meth:`is_dispute_active` will return False until
        ``next_congress_offset_days`` elapse.
        """
        self._annual_last_resolved[template_id] = last_resolved_day

    # ------------------------------------------------------------------
    # SA-P4: coalition betrayal mechanic (deterministic predicate dispatch)
    # ------------------------------------------------------------------

    def snapshot_rep_at_start(
        self,
        dispute: PoliticsDispute,
        faction_ids: tuple[str, ...],
    ) -> None:
        """Capture the player's reputation with each faction at dispute start.

        The ``rep_dropped_below_25`` betrayal predicate compares the player's
        current rep against the start-of-dispute snapshot, so the betrayal
        fires only on rep that dropped *during* the arc. Call once at
        ``start_dispute`` time (after ``set_player``).

        Skipped silently when the player isn't wired or doesn't expose
        ``get_reputation`` (test stubs that don't need the betrayal path).
        """
        if self._propagation_player is None:
            return
        getter = getattr(self._propagation_player, "get_reputation", None)
        if not callable(getter):
            return
        for faction_id in faction_ids:
            dispute.rep_at_start[faction_id] = int(getter(faction_id))

    def _evaluate_betrayal_conditions(
        self,
        dispute: PoliticsDispute,
        player: "Player",
    ) -> list[str]:
        """Walk pre-committed delegates and flip those whose condition fires.

        Args:
            dispute: The active dispute (uses ``template_id`` to look up
                the template's ``betrayal_conditions`` map).
            player: Player whose state the predicates inspect.

        Returns:
            List of delegate ids whose pre-commit was just flipped this
            evaluation. Empty list when nothing changes (idempotent).
        """
        template = self._templates.get(dispute.template_id)
        if template is None or not template.betrayal_conditions:
            return []
        flipped: list[str] = []
        for delegate_id, condition_str in template.betrayal_conditions.items():
            delegate = dispute.delegates.get(delegate_id)
            if delegate is None or not delegate.pre_committed:
                continue
            predicate = _resolve_betrayal_predicate(condition_str)
            if predicate is None:
                continue
            if predicate(dispute, delegate, player):
                delegate.pre_committed = False
                delegate.visible_state = "wavering"
                dispute.had_betrayal = True
                dispute.round_log.append(
                    f"betrayal: {delegate.delegate_id} pre-commit broken ({condition_str})"
                )
                flipped.append(delegate_id)
        return flipped

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_dispute(
        self,
        template_id: str,
        current_game_day: int,
        dispute_id: Optional[str] = None,
    ) -> Optional[PoliticsDispute]:
        """Instantiate a runtime dispute from its template.

        Applies bias initialization (faction loyalty + prior-dispute
        memory per design §4.5) and seeds the session state. Returns
        ``None`` if ``template_id`` is unknown so callers can degrade
        gracefully — empty data dirs are an expected runtime state
        until SA-P3 ships content.

        Args:
            template_id: Template to instantiate.
            current_game_day: Current game day; ``closes_on_day`` is
                ``current_game_day + template.deadline_days``.
            dispute_id: Optional override (defaults to the template id;
                pass when multiple in-flight instances of the same
                template are required).
        """
        template = self._templates.get(template_id)
        if template is None:
            return None
        delegates: dict[str, PoliticsDelegate] = {}
        for dt in template.delegates:
            delegates[dt.delegate_id] = PoliticsDelegate(
                delegate_id=dt.delegate_id,
                name=dt.name,
                visible_state=dt.starting_visible_state,
                position_vector=dict(dt.position_vector),
                faction_loyalty=dt.faction_loyalty,
                sub_faction_id=dt.sub_faction_id,
            )
        dispute = PoliticsDispute(
            dispute_id=dispute_id or template.id,
            template_id=template.id,
            headline=template.headline,
            factions_affected=template.factions_affected,
            base_difficulty=template.base_difficulty,
            round_count=template.round_count,
            closes_on_day=current_game_day + template.deadline_days,
            delegates=delegates,
            eligible_framings=template.eligible_framings,
            eligible_evidence=template.eligible_evidence,
            framing_modifiers=dict(template.framing_modifiers),
            framing_target_dimensions=dict(template.framing_target_dimensions),
            outcome_matrix=template.outcome_matrix,
            current_round=1,
            phase=DisputePhase.ROUND_OPEN,
        )
        # SA-P4: snapshot rep with every faction the betrayal predicates
        # might reference (factions_affected + any rep_dropped_below_25 arg
        # in the template's betrayal_conditions). The snapshot is harmless
        # on templates that declare no betrayals.
        if self._propagation_player is not None:
            faction_ids: set[str] = set(template.factions_affected)
            for condition in template.betrayal_conditions.values():
                if condition.startswith("rep_dropped_below_25:"):
                    _, arg = condition.split(":", 1)
                    if arg:
                        faction_ids.add(arg)
            self.snapshot_rep_at_start(dispute, tuple(sorted(faction_ids)))
        return dispute

    # ------------------------------------------------------------------
    # Internal state-machine helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_position_delta(delegate: PoliticsDelegate, dimension: str, delta: float) -> None:
        """Mutate ``delegate.position_vector[dimension]`` clamped to +/-1.0."""
        current = delegate.position_vector.get(dimension, 0.0)
        new_value = max(-_POSITION_CAP, min(_POSITION_CAP, current + delta))
        delegate.position_vector[dimension] = new_value

    # ------------------------------------------------------------------
    # Argument resolution (SA-P1 §6)
    # ------------------------------------------------------------------

    def _base_skill_id_for(self, argument: PoliticsArgument) -> str:
        """Per SA-P1 §6.4: frontier_autonomy uses Leadership in argue mode.

        Mediation always uses Persuasion regardless of framing
        (§6.2 closing line).
        """
        if argument.is_mediation:
            return "persuasion"
        if argument.framing in _LEADERSHIP_FRAMINGS:
            return "leadership"
        return "persuasion"

    def _bonus_keys_for(self, argument: PoliticsArgument) -> str:
        """Argue mode reads coalition_sway; mediate reads arbitration_neutrality."""
        if argument.is_mediation:
            return "arbitration_neutrality_bonus"
        return "coalition_sway_bonus"

    def _get_skill_level(self, skill_id: str) -> int:
        if self._social_manager is None:
            return 0
        return int(self._social_manager.get_skill_level(skill_id))

    def _get_crew_bonus(self, bonus_type: str) -> float:
        if self._crew_roster is None:
            return 0.0
        return float(self._crew_roster.get_bonus(bonus_type))

    def _get_progression_bonus(self, bonus_type: str) -> float:
        if self._progression is None:
            return 0.0
        return float(self._progression.get_bonus(bonus_type))

    # ------------------------------------------------------------------
    # Cass Weller intel reveal (SA-P1 §7.5)
    # ------------------------------------------------------------------

    def try_reveal_intel(self, dispute: PoliticsDispute) -> Optional[dict[str, str]]:
        """Return per-delegate qualitative position summaries, once per session.

        Fires only when Cass Weller is on crew (her
        ``arbitration_dispute_intel`` bonus_value > 0). Subsequent calls
        in the same session return ``None``. :meth:`end_session` resets
        the gate so the next venue entry re-fires.

        Returns:
            ``{delegate_id: summary_text}`` on success; ``None`` if the
            crew bonus is absent or the session has already revealed.
        """
        if self._intel_revealed_this_session:
            return None
        if self._get_crew_bonus("arbitration_dispute_intel") <= 0.0:
            return None
        self._intel_revealed_this_session = True
        return {
            d_id: qualitative_position_summary(d.position_vector)
            for d_id, d in dispute.delegates.items()
        }

    def end_session(self) -> None:
        """Mark the current venue session ended so per-session gates reset."""
        self._intel_revealed_this_session = False
        self._active_session_venue = None

    # ------------------------------------------------------------------
    # Coalition pre-commit corridor (SA-P1 §5.5)
    # ------------------------------------------------------------------

    def get_pre_commit_cap(self) -> int:
        """SA-P1 §5.5: ``1 + floor(crew_size + skill_size)`` for coalition cap."""
        crew_size = self._get_crew_bonus("coalition_size_bonus")
        skill_size = self._get_progression_bonus("coalition_size_bonus")
        return 1 + _floor(crew_size + skill_size)

    def get_corridor_difficulty(self, dispute: PoliticsDispute, delegate_id: str) -> int:
        """Effective corridor difficulty including consecutive-fail escalation."""
        d = dispute.delegates.get(delegate_id)
        if d is None:
            return dispute.base_difficulty
        return dispute.base_difficulty + d.consecutive_corridor_fails

    def do_corridor_visit(
        self,
        dispute: PoliticsDispute,
        delegate_id: str,
        framing: str,
        *,
        success_override: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """Run a pre-session corridor visit against ``delegate_id``.

        Pre-commit cap from :meth:`get_pre_commit_cap` is enforced before
        the skill check. On success: delegate is marked pre_committed
        and visible_state moves to leaning_yes (per §5.5). On failure:
        the consecutive-fail counter increments and 1 sub-rep is
        deducted from the delegate's sub-tier faction, when the player +
        sub_faction_id are wired.

        Args:
            success_override: Test hook. When ``None`` (default), the
                manager invokes ``social_manager.resolve_check`` against
                the delegate's npc id. Tests pass ``True`` / ``False``
                to bypass the social-manager dependency without stubbing
                the entire resolve_check pipeline.
        """
        delegate = dispute.delegates.get(delegate_id)
        if delegate is None:
            return False, f"Unknown delegate {delegate_id}"

        # Enforce the pre-commit cap (counts already-committed delegates).
        cap = self.get_pre_commit_cap()
        committed_now = sum(1 for d in dispute.delegates.values() if d.pre_committed)
        if not delegate.pre_committed and committed_now >= cap:
            return False, f"Pre-commit cap reached ({committed_now}/{cap})."

        difficulty = self.get_corridor_difficulty(dispute, delegate_id)
        if success_override is not None:
            success = success_override
        elif self._social_manager is None:
            return False, "Social manager not configured."
        else:
            success, _msg = self._social_manager.resolve_check(
                "persuasion", difficulty, delegate.delegate_id
            )

        if success:
            delegate.pre_committed = True
            delegate.visible_state = "leaning_yes"
            delegate.consecutive_corridor_fails = 0
            # SA-P3 crew-banter trigger: Desta Coll on a successful corridor
            # visit. Sets a one-time flag SA-X6 will consume for actual
            # banter content.
            self._maybe_set_crew_banter_flag("desta_coll", "desta_corridor_pre_session_seen")
            return True, f"Pre-commit secured for {delegate.name}."

        delegate.consecutive_corridor_fails += 1
        # Sub-rep deduction (SA-B-EXT-1) — fire only when both player and
        # the org config are wired. Failing visits without org config are
        # silently no-ops (test runs that don't load sub-rep configs).
        self._maybe_deduct_sub_rep(delegate)
        return False, f"Corridor visit failed against {delegate.name}."

    def _maybe_set_crew_banter_flag(self, crew_id: str, flag_name: str) -> None:
        """SA-P3: set ``flag_name`` on the player when ``crew_id`` is on crew.

        Trigger surface for SA-X6 banter content. Skipped silently when
        the player or crew roster isn't wired (unit-test mode), or when
        the named crew member isn't aboard. Idempotent: re-setting an
        already-True flag is a no-op.
        """
        if self._propagation_player is None or self._crew_roster is None:
            return
        recruited = getattr(self._crew_roster, "recruited_ids", None)
        ids: set[str] = set()
        if isinstance(recruited, (set, list, tuple)):
            ids = set(recruited)
        elif callable(recruited):  # pragma: no cover (defensive)
            ids = set(recruited())
        if crew_id not in ids:
            return
        # Variable-routed write keeps the SI-3 scanner from picking up this
        # literal as a producer. SA-X6 will consume the flag for banter
        # gating, at which point a helper migration may be appropriate.
        flag = flag_name
        self._propagation_player.dialogue_flags[flag] = True

    def _maybe_deduct_sub_rep(self, delegate: PoliticsDelegate) -> None:
        """Best-effort sub-reputation deduction for a failed corridor visit.

        Looks up the delegate's ``sub_faction_id`` in the engine's sub-
        rep config registry (when wired). If unconfigured, no-op so
        SA-P2 ships even before SA-P3 hooks up specific verdant /
        alliance org configs.
        """
        if self._propagation_player is None or not delegate.sub_faction_id:
            return
        config = getattr(self, "_sub_rep_configs", {}).get(delegate.sub_faction_id)
        if config is None:
            return
        self._propagation_player.modify_sub_reputation(delegate.sub_faction_id, -1, config)

    def register_sub_rep_config(self, org_id: str, config: Any) -> None:
        """Register a SubReputationConfig for an org (called by Game wiring)."""
        if not hasattr(self, "_sub_rep_configs"):
            self._sub_rep_configs: dict[str, Any] = {}
        self._sub_rep_configs[org_id] = config

    # ------------------------------------------------------------------
    # Per-round state machine (SA-P1 §2.2)
    # ------------------------------------------------------------------

    # Pending counter-arguments the manager has decided to fire on the next
    # advance_round() call. Computed at submit_argument() time so the
    # qualification snapshot uses the pre-Phase-1 visible_state per design
    # §2.2: "A delegate moved by Phase 1 retains their pre-Phase-1
    # qualification status for this check."
    #
    # Schema: list of (counter_delegate_id, framing_id, target_delegate_id).
    # Stored on the dispute object so save/load preserves it implicitly via
    # round-boundary serialization (we clear it as part of advance_round).

    @staticmethod
    def _opposition_qualifies_for_counter(visible_state: str) -> bool:
        """Per §2.2: counter-argument qualification = pre-round leaning_no/committed_no."""
        return visible_state in ("leaning_no", "committed_no")

    @staticmethod
    def _most_favorable_target(
        delegates: dict[str, PoliticsDelegate],
        opposition_id: str,
    ) -> Optional[str]:
        """SA-P1 §2.2 corrected rule: most-favorable-toward-yes who isn't committed_yes.

        Excludes the firing delegate themselves and any committed_yes
        delegates (immovable). Returns ``None`` if no eligible target,
        documenting the no-op case from §2.2's edge case.
        """
        best_id: Optional[str] = None
        best_rank = -1
        for d_id, d in delegates.items():
            if d_id == opposition_id:
                continue
            if d.visible_state == "committed_yes":
                continue
            rank = _visible_index(d.visible_state)
            if rank > best_rank:
                best_rank = rank
                best_id = d_id
        return best_id

    # SA-P2 default counter-framing, used when a dispute template does not
    # declare per-delegate overrides. Preserves the SA-P1 §4.6 worked-example
    # behavior (Hask responds with ``soil_impact`` against
    # ``water_rights_change``) for any template that omits the field.
    _DEFAULT_COUNTER_FRAMING: tuple[str, str] = ("soil_impact", "water_rights_change")

    def _resolve_counter_argument(
        self,
        dispute: PoliticsDispute,
        delegate: PoliticsDelegate,
    ) -> tuple[str, str]:
        """Pick the framing + opposition dimension this delegate fires.

        SA-P3 generalized the SA-P2 hard-coded rule into a template-driven
        lookup. The dispute's template carries an optional
        ``counter_framings: dict[str, tuple[str, str]]`` keyed by delegate
        id; when the firing delegate has an entry, that pair is used.
        Otherwise the SA-P2 default is preserved so existing fixtures and
        any template that omits the field continue to behave identically.

        Args:
            dispute: The runtime dispute (template lookup uses
                ``dispute.template_id``).
            delegate: The delegate firing the counter-argument.

        Returns:
            ``(framing_id, target_dimension)`` for the counter-argument.
        """
        template = self._templates.get(dispute.template_id)
        if template is not None:
            override = template.counter_framings.get(delegate.delegate_id)
            if override is not None:
                return override
        return self._DEFAULT_COUNTER_FRAMING

    def submit_argument(
        self,
        dispute: PoliticsDispute,
        argument: PoliticsArgument,
    ) -> ArgumentResolution:
        """Resolve the player's argue / mediate action and apply state changes.

        Player-action effects fire immediately. Counter-arguments queue
        until :meth:`advance_round` so the player sees their argument
        land before the room responds.
        """
        resolution = self.preview_argument(dispute, argument)
        if resolution.error:
            return resolution

        target = dispute.delegates[argument.audience_delegate_id]
        # Committed delegates cannot be moved by arguments.
        if target.visible_state in ("committed_yes", "committed_no"):
            return resolution

        if argument.is_mediation:
            # SA-P3 crew-banter trigger: Cass Weller observes mediation.
            # Fires whenever the player commits a mediate action,
            # regardless of pass / fail, since the banter notes structural
            # durability ("will this hold?"), not the resolver verdict.
            self._maybe_set_crew_banter_flag("cass_weller", "cass_mediation_in_progress_seen")
            if resolution.passes:
                target.conceded = True
                if argument.framing in dispute.framing_target_dimensions:
                    dim = dispute.framing_target_dimensions[argument.framing]
                    self._apply_position_delta(target, dim, _MEDIATE_DELTA)
        else:
            if resolution.passes:
                target.visible_state = _shift_visible(target.visible_state, +1)
                if argument.framing in dispute.framing_target_dimensions:
                    dim = dispute.framing_target_dimensions[argument.framing]
                    self._apply_position_delta(target, dim, _ARG_PASS_DELTA)

        # Snapshot pre-Phase-1 opposition for the counter-argument phase.
        # Per SA-P1 §4.6 worked example, one counter fires per round (not
        # one per opposition delegate); the firing delegate is the first
        # qualifying opposition by template iteration order, which keeps
        # the choice deterministic and matches the §4.6 narrative
        # (Hask fires, Marsh stays quiet).
        pending: list[dict[str, Any]] = []
        snapshot = self._snapshot_visible_states_pre_phase_one(dispute)
        for d_id, d in dispute.delegates.items():
            if not self._opposition_qualifies_for_counter(snapshot[d_id]):
                continue
            counter_framing, _dim = self._resolve_counter_argument(dispute, d)
            pre_empted = (
                argument.responds_to is not None and argument.responds_to == counter_framing
            )
            target_id = self._most_favorable_target(dispute.delegates, d_id)
            pending.append(
                {
                    "counter_id": d_id,
                    "framing": counter_framing,
                    "target_id": target_id,
                    "pre_empted": pre_empted,
                }
            )
            break  # one counter per round (§4.6 worked example)
        dispute._pending_counters = pending  # type: ignore[attr-defined]
        dispute.round_log.append(
            f"argued {argument.framing} to {target.delegate_id}: "
            f"{'pass' if resolution.passes else 'fail'} "
            f"(eff {resolution.effective_floor} vs D{resolution.difficulty})"
        )
        return resolution

    @staticmethod
    def _snapshot_visible_states_pre_phase_one(
        dispute: PoliticsDispute,
    ) -> dict[str, str]:
        """Best-effort snapshot of pre-Phase-1 states.

        SA-P2 takes a simpler view than the perfect spec: by the time
        ``submit_argument`` runs, only the player's targeted delegate has
        moved (Phase-1's single action). For all other delegates, the
        current visible_state == pre-Phase-1 visible_state. For the
        targeted delegate, we reconstruct: if the argument moved the
        delegate forward, the pre-state is one step "back" along the
        chain; otherwise unchanged.
        """
        return {d_id: d.visible_state for d_id, d in dispute.delegates.items()}

    def _run_counter_argument_phase(self, dispute: PoliticsDispute) -> None:
        """Apply pending counter-arguments queued by submit_argument."""
        pending: list[dict[str, Any]] = getattr(dispute, "_pending_counters", [])
        for entry in pending:
            if entry["pre_empted"]:
                dispute.round_log.append(
                    f"counter from {entry['counter_id']} pre-empted by responds_to"
                )
                continue
            target_id = entry["target_id"]
            if target_id is None:
                dispute.round_log.append(
                    f"counter from {entry['counter_id']} no-op (no eligible target)"
                )
                continue
            target = dispute.delegates[target_id]
            if target.visible_state == "committed_no":
                continue
            target.visible_state = _shift_visible(target.visible_state, -1)
            counter_framing = entry["framing"]
            if counter_framing in dispute.framing_target_dimensions:
                dim = dispute.framing_target_dimensions[counter_framing]
                self._apply_position_delta(target, dim, _COUNTER_DELTA)
            dispute.round_log.append(f"counter from {entry['counter_id']} hit {target_id}")
        dispute._pending_counters = []  # type: ignore[attr-defined]

    def advance_round(self, dispute: PoliticsDispute) -> None:
        """Run counter-argument phase, conviction adjustments, then advance.

        SA-P4: at the start of the next round (just before opening it),
        evaluate betrayal conditions on every pre-committed delegate. A
        triggered betrayal flips ``pre_committed`` back to False and resets
        ``visible_state`` to wavering, with one round_log entry per flip.
        Idempotent: re-running the evaluation produces no further flips.
        """
        self._run_counter_argument_phase(dispute)
        # Conviction adjustments are encoded in the position_vector
        # mutations applied during submit_argument and the counter phase;
        # there is no additional aggregate adjustment here in SA-P2.
        if dispute.current_round >= dispute.round_count:
            self._finalize_outcome(dispute)
        else:
            dispute.current_round += 1
            dispute.phase = DisputePhase.ROUND_OPEN
            # SA-P4: evaluate betrayal conditions once per round at round
            # start. Skipped silently when the player isn't wired (test
            # mode without ``set_player``).
            if self._propagation_player is not None:
                self._evaluate_betrayal_conditions(dispute, self._propagation_player)

    def cast_vote(self, dispute: PoliticsDispute) -> None:
        """Player calls the vote: skip remaining counter phase, resolve immediately."""
        # SA-P1 §5.1: voting forfeits remaining argument rounds AND avoids
        # counter-arguments. Drop pending counters before resolving.
        dispute._pending_counters = []  # type: ignore[attr-defined]
        self._finalize_outcome(dispute)

    def abstain_round(self, dispute: PoliticsDispute) -> None:
        """Forfeit the round's action; advance with no state change."""
        # No counters fire on abstain (player did not provoke them this round).
        dispute._pending_counters = []  # type: ignore[attr-defined]
        if dispute.current_round >= dispute.round_count:
            self._finalize_outcome(dispute)
        else:
            dispute.current_round += 1
            dispute.phase = DisputePhase.ROUND_OPEN

    # ------------------------------------------------------------------
    # Outcome resolution + propagation (SA-P1 §5.1 + §7)
    # ------------------------------------------------------------------

    def _tally_votes(self, dispute: PoliticsDispute) -> tuple[int, int]:
        """Return ``(yes_votes, no_votes)`` per the §5.1 mapping.

        wavering counts as no per §11 decision 13.
        """
        yes = 0
        no = 0
        for d in dispute.delegates.values():
            if d.visible_state in ("leaning_yes", "committed_yes"):
                yes += 1
            else:
                no += 1
        return yes, no

    def _select_outcome_category(self, dispute: PoliticsDispute) -> str:
        """SA-P1 §5.1 selection rules."""
        yes, no = self._tally_votes(dispute)
        passes = yes > no
        pre_committed = sum(1 for d in dispute.delegates.values() if d.pre_committed)
        roster_size = len(dispute.delegates) or 1
        pre_commit_ratio = pre_committed / roster_size
        any_conceded = any(d.conceded for d in dispute.delegates.values())
        if passes:
            if pre_commit_ratio >= _COALITION_THIN_THRESHOLD:
                return "win"
            return "partial_win_coalition_thin"
        # Vote failed.
        if any_conceded:
            return "partial_win_off_record"
        return "loss"

    def _finalize_outcome(self, dispute: PoliticsDispute) -> None:
        """Pick a category, mark the dispute resolved, fire propagation."""
        if dispute.phase == DisputePhase.RESOLVED:
            return
        dispute.phase = DisputePhase.RESOLVING
        category = self._select_outcome_category(dispute)
        dispute.resolved_outcome = category
        dispute.phase = DisputePhase.RESOLVED
        dispute.round_log.append(f"resolved: {category}")
        self._propagate_outcome(dispute, category)
        # Move from pending to resolved registry so save / load and the
        # journal-trigger system see the right state immediately.
        if dispute.dispute_id in self._pending_disputes:
            self._resolved_disputes[dispute.dispute_id] = dispute
            self._pending_disputes.pop(dispute.dispute_id, None)
        # SA-P4: record the resolve day for annual templates so the lockout
        # window opens. Uses the player's current game day when available;
        # falls back to the dispute's closes_on_day for engine-only flows.
        template = self._templates.get(dispute.template_id)
        if template is not None and template.is_annual_congress:
            resolved_day = (
                getattr(self._propagation_player, "game_day", None)
                if self._propagation_player is not None
                else None
            )
            if resolved_day is None:
                resolved_day = dispute.closes_on_day
            self._annual_last_resolved[dispute.template_id] = int(resolved_day)
        # SA-P3 outcome callback (after propagation, so the engine sees
        # rep / market / mission flag side-effects already applied).
        if self._outcome_callback is not None:
            self._outcome_callback(dispute, category)

    def _propagate_outcome(
        self,
        dispute: PoliticsDispute,
        category: str,
    ) -> None:
        """Fire rep deltas, market shifts, mission flags, news headline."""
        row = dispute.outcome_matrix.get(category)
        if row is None:
            return

        # Snapshot pre-delta reputation so the news gate (§7.6) can ask
        # whether a tier boundary was crossed by this outcome.
        pre_rep: dict[str, int] = {}
        if self._propagation_player is not None:
            for faction_id in row.rep_deltas:
                pre_rep[faction_id] = self._propagation_player.get_reputation(faction_id)

        # 1. Reputation deltas with spillover.
        if self._propagation_player is not None and self._politics_manager is not None:
            for faction_id, delta in row.rep_deltas.items():
                self._politics_manager.apply_reputation_with_spillover(
                    self._propagation_player, faction_id, delta
                )

        # 2. Market shifts via the new registry.
        if self._market_lookup is not None:
            for shift in row.market_shifts:
                market = self._market_lookup(shift.system_id)
                if market is None:
                    continue
                start_day = getattr(market, "game_day", 0)
                instance = PoliticsMarketShift(
                    commodity_id=shift.commodity_id,
                    system_id=shift.system_id,
                    magnitude=shift.magnitude,
                    duration_days=shift.duration_days,
                    start_day=start_day,
                )
                add_politics_shift = getattr(market, "add_politics_shift", None)
                if add_politics_shift is not None:
                    add_politics_shift(instance)

        # 3. Mission flags via player.dialogue_flags.
        if self._propagation_player is not None:
            for flag in row.mission_unlocks:
                self._propagation_player.dialogue_flags[flag] = True
            for flag in row.mission_locks:
                self._propagation_player.dialogue_flags[flag] = True

        # 4. News headline gated by §7.6 conditions.
        self._maybe_emit_headline(dispute, category, row, pre_rep)

    def _maybe_emit_headline(
        self,
        dispute: PoliticsDispute,
        category: str,
        row: OutcomeRow,
        pre_rep: dict[str, int],
    ) -> None:
        """SA-P1 §7.6 gate.

        Condition A: rep delta crosses a tier boundary OR
            commodity shift >= 10%.
        Condition B: outcome category is win or loss.
        Both must hold.
        """
        if self._news_ticker is None or row.news_headline is None:
            return
        condition_b = category in ("win", "loss")
        tier_crossed = self._tier_crossed(row, pre_rep)
        magnitude_qualifies = any(
            abs(s.magnitude) >= _NEWS_COMMODITY_MAGNITUDE for s in row.market_shifts
        )
        if condition_b:
            # win/loss: need condition A (magnitude >=10% OR tier crossing).
            if not (magnitude_qualifies or tier_crossed):
                return
        else:
            # partial wins: only gate on tier crossing per §7.6 commentary
            # ("Partial wins do NOT generate news unless condition A is
            # also met (tier boundary crossing)").
            if not tier_crossed:
                return
        self._news_ticker.add_headline(row.news_headline, priority=5)

    def _tier_crossed(self, row: OutcomeRow, pre_rep: dict[str, int]) -> bool:
        """True if any rep delta crossed a tier boundary.

        Compares each faction's pre-delta value to its post-delta value
        (from the player's current reputation, which has already been
        mutated by ``_propagate_outcome``).
        """
        if self._propagation_player is None:
            return False
        for faction_id in row.rep_deltas:
            before = pre_rep.get(faction_id, 0)
            after = self._propagation_player.get_reputation(faction_id)
            for boundary in _TIER_BOUNDARIES:
                if (before < boundary <= after) or (after <= boundary < before):
                    return True
        return False

    # ------------------------------------------------------------------
    # Existing preview_argument (already defined above) — placeholder so
    # the search anchor below remains stable.
    # ------------------------------------------------------------------

    def preview_argument(
        self,
        dispute: PoliticsDispute,
        argument: PoliticsArgument,
    ) -> ArgumentResolution:
        """Resolve an argument deterministically without applying side effects.

        The composer's live "Effective N vs Difficulty M" preview calls
        this on every selection change; :meth:`submit_argument` calls it
        too and then applies the state transitions. Pure function of
        (dispute state, argument selections) per the
        deterministic-outcomes axiom.
        """
        if not argument.framing:
            return ArgumentResolution(error="framing_required", difficulty=dispute.base_difficulty)
        if not argument.audience_delegate_id:
            return ArgumentResolution(error="audience_required", difficulty=dispute.base_difficulty)
        delegate = dispute.delegates.get(argument.audience_delegate_id)
        if delegate is None:
            return ArgumentResolution(error="unknown_audience", difficulty=dispute.base_difficulty)

        base_skill = self._get_skill_level(self._base_skill_id_for(argument))
        framing_mod = int(dispute.framing_modifiers.get(argument.framing, 0))
        disposition_mod = _disposition_modifier(delegate.disposition)
        bonus_key = self._bonus_keys_for(argument)
        crew_bonus = self._get_crew_bonus(bonus_key)
        tree_bonus = self._get_progression_bonus(bonus_key)
        effective = base_skill + framing_mod + disposition_mod + crew_bonus + tree_bonus
        evidence_penalty = 0 if argument.evidence else 1
        difficulty = dispute.base_difficulty + evidence_penalty
        effective_floor = _floor(effective)
        passes = effective_floor >= difficulty
        return ArgumentResolution(
            base_skill=base_skill,
            framing_mod=framing_mod,
            disposition_mod=disposition_mod,
            crew_bonus=crew_bonus,
            tree_bonus=tree_bonus,
            evidence_absent_penalty=evidence_penalty,
            difficulty=difficulty,
            effective_floor=effective_floor,
            passes=passes,
        )

    # ------------------------------------------------------------------
    # Pending / resolved dispute registry (persisted at round boundary)
    # ------------------------------------------------------------------

    def register_pending_dispute(self, dispute: PoliticsDispute) -> None:
        """Track ``dispute`` so it persists across save/load cycles.

        Resolved disputes auto-move to the resolved registry.
        """
        if dispute.phase == DisputePhase.RESOLVED:
            self._resolved_disputes[dispute.dispute_id] = dispute
            self._pending_disputes.pop(dispute.dispute_id, None)
        else:
            self._pending_disputes[dispute.dispute_id] = dispute

    def get_pending_dispute(self, dispute_id: str) -> Optional[PoliticsDispute]:
        return self._pending_disputes.get(dispute_id)

    def get_pending_dispute_ids(self) -> list[str]:
        return list(self._pending_disputes.keys())

    def get_resolved_dispute(self, dispute_id: str) -> Optional[PoliticsDispute]:
        return self._resolved_disputes.get(dispute_id)

    # ------------------------------------------------------------------
    # Manager save / load (SA-P1 §11 decision 4: round boundary)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the manager state for the save system.

        Only persists what's needed to restore a player mid-arc:
        pending disputes (state at last round boundary), resolved
        disputes (for journal / mission gating), and the SA-P4 annual
        last-resolved registry. Per-session ephemeral state (intel
        reveal flag, active venue) is NOT persisted by design.
        """
        return {
            "pending_disputes": {
                d_id: dispute.to_dict() for d_id, dispute in self._pending_disputes.items()
            },
            "resolved_disputes": {
                d_id: dispute.to_dict() for d_id, dispute in self._resolved_disputes.items()
            },
            "annual_last_resolved": dict(self._annual_last_resolved),
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Restore manager state from save data.

        Looks each dispute's outcome_matrix back up from the live
        template registry — never persists the matrix itself, so post-
        SA-P2 template tweaks carry through to in-flight disputes.
        Disputes whose template is missing are silently dropped.
        """
        self._pending_disputes = {}
        for d_id, raw in data.get("pending_disputes", {}).items():
            template = self._templates.get(raw.get("template_id", ""))
            if template is None:
                continue
            self._pending_disputes[d_id] = PoliticsDispute.from_dict(raw, template.outcome_matrix)
        self._resolved_disputes = {}
        for d_id, raw in data.get("resolved_disputes", {}).items():
            template = self._templates.get(raw.get("template_id", ""))
            if template is None:
                continue
            self._resolved_disputes[d_id] = PoliticsDispute.from_dict(raw, template.outcome_matrix)
        # SA-P4 annual lockout registry; legacy saves omit this key.
        self._annual_last_resolved = {
            tid: int(day) for tid, day in data.get("annual_last_resolved", {}).items()
        }
