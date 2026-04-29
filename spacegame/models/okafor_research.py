"""SA-R1 Okafor Institute: research-patronage projects, state, and resolution.

Models the funded-research lifecycle: a project template is a frozen
dataclass at module scope (Scanner B clean per the SI-2 cookbook); the
mutable :class:`OkaforResearchState` lives on
:class:`spacegame.models.player.Player` and tracks active projects,
patent holdings, and the player's relationship-value with Dr. Kweon.

Risk resolution is deterministic per CLAUDE.md "Gameplay Philosophy":
the seeded RNG ``random.Random(f"{template_id}_{accept_day}_{player_seed}")``
fixes the outcome the moment the player funds. Reload-and-retry never
changes the result.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Tunables (decisions locked in the SA-R1 plan; risks/open-questions section)
# ---------------------------------------------------------------------------

# Window length for visit-triggered offer rerolls. Per the plan: 30 days
# is long enough for an active mid-tier project to finish inside one
# window without forcing the player to revisit just to keep the board
# fresh.
SLOT_REFRESH_WINDOW_DAYS: int = 30

# Minimum / maximum offers presented per visit (acceptance #3).
SLOT_OFFER_MIN: int = 5
SLOT_OFFER_MAX: int = 7

# Risk-tier failure odds (acceptance #5; locked in the risks table).
FAILURE_ODDS: dict[str, float] = {
    "low": 0.05,
    "mid": 0.18,
    "high": 0.35,
}

# Failure path refunds 30% of paid capital.
FAILURE_REFUND_RATE: float = 0.30

# Patent / IP economy (acceptance #8).
ROYALTY_INTERVAL_DAYS: int = 10
ROYALTY_RATE: float = 0.05  # 5% of success payout per interval, while licensed
SELL_LUMP_SUM_RATE: float = 0.60  # 60% of success payout, one-time, removes holding

# Team-fund collaborator math (acceptance #6).
TEAM_FUND_COST_PER_COLLABORATOR: float = 0.5  # +50% per slot
TEAM_FUND_DURATION_PER_COLLABORATOR: float = 0.7  # 70% remaining per slot
TEAM_FUND_DURATION_FLOOR: float = 0.5  # capped at 50% of base regardless of slots
TEAM_FUND_MAX_COLLABORATORS: int = 2

# Kweon relationship arc range (locked decision: not a sub-rep tier).
RELATIONSHIP_VALUE_MIN: int = 0
RELATIONSHIP_VALUE_MAX: int = 10


# ---------------------------------------------------------------------------
# Project template (frozen — module-level content table)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OkaforProjectTemplate:
    """An Okafor Institute funded-research project offer.

    Templates are immutable definitions. Active runs are
    :class:`ActiveProject` instances created from a template via
    :func:`fund_project`.

    Attributes:
        id: Stable snake_case identifier.
        name: Display name for the board entry.
        faction: Faction id whose flavor the project carries
            (``"science_collective"``, ``"frontier_alliance"``,
            ``"miners_union"``).
        risk_tier: One of ``"low"``, ``"mid"``, ``"high"``. Drives
            failure odds via :data:`FAILURE_ODDS`.
        base_cost_credits: Solo-fund cost in credits.
        base_duration_days: Solo-fund duration in game days.
        base_failure_odds: Locked to ``FAILURE_ODDS[risk_tier]``.
        base_success_payout: Solo-fund success payout in credits before
            ``research_yield_bonus`` is applied.
        briefing: Kweon's voice; what the project investigates and why.
        success_debrief: Kweon's voice; one block on success.
        failure_debrief: Kweon's voice; one block on failure.
        outcome_unlock_type: ``""`` or ``"module"`` / ``"upgrade"`` /
            ``"commodity"``. Mid- and high-risk projects name a specific
            unlock from existing data; low-risk projects pay credits only.
        outcome_unlock_id: Snake_case id from the matching data file
            when ``outcome_unlock_type`` is non-empty.
    """

    id: str
    name: str
    faction: str
    risk_tier: str
    base_cost_credits: int
    base_duration_days: int
    base_failure_odds: float
    base_success_payout: int
    briefing: str
    success_debrief: str
    failure_debrief: str
    outcome_unlock_type: str = ""
    outcome_unlock_id: str = ""


# ---------------------------------------------------------------------------
# 10 project templates (4 low / 4 mid / 2 high) — Kweon's voice throughout.
# ---------------------------------------------------------------------------


OKAFOR_PROJECT_TEMPLATES: tuple[OkaforProjectTemplate, ...] = (
    # === Low risk (4) ===
    OkaforProjectTemplate(
        id="low_protein_folding_replication",
        name="Protein-Folding Replication Run",
        faction="science_collective",
        risk_tier="low",
        base_cost_credits=8_000,
        base_duration_days=6,
        base_failure_odds=0.05,
        base_success_payout=14_000,
        briefing=(
            "A replication run on the protein-folding work the founding "
            "generation published. The methodology is well-established. "
            "What we need is the bench time and the consumables. Six days, "
            "competent technicians, and the variance data fills out a "
            "decade-old footnote that the field still cites without "
            "the underlying numbers."
        ),
        success_debrief=(
            "Replicated within tolerance. The footnote is now a citation "
            "with substance behind it. Modest, but the field will use it."
        ),
        failure_debrief=(
            "The reagents were not what the supplier listed. Resources "
            "were not allocated for a second batch. The work stands as "
            "incomplete in the file. Not the outcome any of us wanted."
        ),
    ),
    OkaforProjectTemplate(
        id="low_archive_recovery",
        name="Founder-Era Archive Recovery",
        faction="science_collective",
        risk_tier="low",
        base_cost_credits=10_000,
        base_duration_days=8,
        base_failure_odds=0.05,
        base_success_payout=18_000,
        briefing=(
            "Twenty boxes of pre-Convergence research notes that have "
            "lived in offsite storage for fifteen years. Cataloging, "
            "digitizing, cross-referencing. Tedious. Low-stakes on the "
            "outside. What is in those notes is the founding generation "
            "showing its work. We have lost too much of that already."
        ),
        success_debrief=(
            "The catalog is in the system. Two of the notebooks contain "
            "data we did not know we still had. The Institute archives "
            "are richer than they were at the start of the month."
        ),
        failure_debrief=(
            "Water damage on the inner stacks. The catalog covers what "
            "was salvaged. The gaps are now documented gaps rather than "
            "unknown ones. Worth recording, even at this cost."
        ),
    ),
    OkaforProjectTemplate(
        id="low_meta_analysis_pediatric",
        name="Pediatric Care Meta-Analysis",
        faction="frontier_alliance",
        risk_tier="low",
        base_cost_credits=12_000,
        base_duration_days=7,
        base_failure_odds=0.05,
        base_success_payout=20_000,
        briefing=(
            "The Frontier Alliance medical-aid corps wants a meta-analysis "
            "of the last decade of pediatric outcomes in mid-belt outposts. "
            "It is desk work. Comparative methodology, standard tools. "
            "What it produces is what the field workers carry into the "
            "next funding round when they argue for a clinic that should "
            "have been built five years ago."
        ),
        success_debrief=(
            "The meta-analysis is published. The field corps has the "
            "numbers they were missing. Whether anyone funds the clinic "
            "this round is not our concern. The argument now has weight."
        ),
        failure_debrief=(
            "The dataset had gaps the corps had not flagged. The methodology "
            "could not bridge them honestly. Our finding is that the data "
            "the field corps wants does not yet exist. That is also useful, "
            "if it is read carefully."
        ),
    ),
    OkaforProjectTemplate(
        id="low_industrial_dust_filtration",
        name="Industrial Dust Filtration Trial",
        faction="miners_union",
        risk_tier="low",
        base_cost_credits=9_000,
        base_duration_days=6,
        base_failure_odds=0.05,
        base_success_payout=16_000,
        briefing=(
            "The Miners' Union health committee is funding a trial of an "
            "improved filtration cartridge for low-rotation belt operations. "
            "The chemistry is straightforward. The variable is whether the "
            "cartridge holds tolerance over a six-day shift. Six days of "
            "controlled-atmosphere benchwork. Practical, applied, the kind "
            "of work the Institute used to do without thinking twice."
        ),
        success_debrief=(
            "The cartridge holds tolerance through the full shift cycle. "
            "The Union committee has what they need to negotiate the spec "
            "with their suppliers. Useful work."
        ),
        failure_debrief=(
            "The cartridge degrades at the four-day mark in the controlled "
            "atmosphere. The Union committee has the variance data and "
            "will go back to the suppliers. We did not produce the answer "
            "they wanted. We produced the answer the data supports."
        ),
    ),
    # === Mid risk (4) ===
    OkaforProjectTemplate(
        id="mid_neural_synthesis_protocol",
        name="Neural-Synthesis Protocol Refinement",
        faction="science_collective",
        risk_tier="mid",
        base_cost_credits=28_000,
        base_duration_days=12,
        base_failure_odds=0.18,
        base_success_payout=70_000,
        briefing=(
            "The neural-synthesis protocol the Institute has been refining "
            "for two years is at the stage where the variance data on the "
            "third-step yield is the question. Twelve-day trial. The "
            "literature suggests the third step is solvable. The literature "
            "is also two years old. What we know now is that the third "
            "step is solvable for some classes of substrate and not others. "
            "Funding closes that gap."
        ),
        success_debrief=(
            "The third-step yield is consistent across the tested substrate "
            "classes. The protocol is now publishable in its current form. "
            "The Collective journal is the obvious venue."
        ),
        failure_debrief=(
            "The third step held for two of three substrate classes. The "
            "third class shows the variance our hypothesis predicted at "
            "the lower bound. The protocol is not yet publishable. The "
            "data points where the next iteration has to start."
        ),
        outcome_unlock_type="module",
        outcome_unlock_id="advanced_sensor_array",
    ),
    OkaforProjectTemplate(
        id="mid_orbital_propulsion_efficiency",
        name="Low-Thrust Propulsion Efficiency Study",
        faction="science_collective",
        risk_tier="mid",
        base_cost_credits=32_000,
        base_duration_days=14,
        base_failure_odds=0.18,
        base_success_payout=80_000,
        briefing=(
            "An efficiency study on low-thrust orbital propulsion that the "
            "Collective passed on twice. The methodology is sound. What "
            "the Collective declined to fund was the bench time on the "
            "rare-isotope catalyst run. Two weeks. If the catalyst behaves "
            "as the modeling predicts, the efficiency floor for this class "
            "of drive moves up by a full digit."
        ),
        success_debrief=(
            "The catalyst behaves. The efficiency floor moves. The paper "
            "writes itself from here. The Collective will fund the next "
            "stage now that the hard part is documented."
        ),
        failure_debrief=(
            "The catalyst behaves at the lower modeled bound. Efficiency "
            "improves, but not at the threshold the field considers "
            "interesting. The paper still publishes; the conclusions "
            "are narrower than we hoped. Honest result."
        ),
        outcome_unlock_type="upgrade",
        outcome_unlock_id="efficient_thrusters",
    ),
    OkaforProjectTemplate(
        id="mid_field_clinic_supply_chain",
        name="Field-Clinic Cold-Chain Resilience",
        faction="frontier_alliance",
        risk_tier="mid",
        base_cost_credits=24_000,
        base_duration_days=10,
        base_failure_odds=0.18,
        base_success_payout=60_000,
        briefing=(
            "The Frontier Alliance medical-aid corps is funding work on "
            "cold-chain resilience for field clinics in the outer belts. "
            "Two weeks of failure-mode analysis on the standard transport "
            "chassis. The aim is identifying which links break first under "
            "the actual conditions the corps operates in, rather than the "
            "conditions the chassis specification was written for."
        ),
        success_debrief=(
            "The failure-mode analysis is complete. The corps has a ranked "
            "list of which links to harden first. The Alliance will fund "
            "the hardware iteration on the strength of this work."
        ),
        failure_debrief=(
            "The analysis identified the first two failure modes cleanly. "
            "The third resists characterization with the test rig we have. "
            "The corps will work with the partial result. That is what "
            "they have to do, and what we deliver."
        ),
        outcome_unlock_type="commodity",
        outcome_unlock_id="medical_supplies",
    ),
    OkaforProjectTemplate(
        id="mid_alloy_corrosion_mining_belt",
        name="Mining-Belt Alloy Corrosion Study",
        faction="miners_union",
        risk_tier="mid",
        base_cost_credits=26_000,
        base_duration_days=11,
        base_failure_odds=0.18,
        base_success_payout=65_000,
        briefing=(
            "A corrosion study on the alloys used in mid-belt mining "
            "habitat construction. The Union health committee is the "
            "primary patron. The methodology requires controlled exposure "
            "trials over eleven days. What it produces is the spec the "
            "Union takes to the construction firms when the next habitat "
            "contract goes out for bid."
        ),
        success_debrief=(
            "The corrosion data is in. Three of the four alloys show "
            "predictable degradation curves; the fourth is an outlier "
            "that the Union will flag in its construction specs. Solid "
            "work, the kind that quietly prevents an incident."
        ),
        failure_debrief=(
            "The exposure trials produced data on three alloys. The "
            "fourth's exposure rig failed at day eight. The Union has "
            "the partial data and a documented gap. Not a complete result; "
            "an honest one."
        ),
        outcome_unlock_type="commodity",
        outcome_unlock_id="alloy_composite",
    ),
    # === High risk (2) ===
    OkaforProjectTemplate(
        id="high_quantum_sensor_capstone",
        name="Quantum Sensor Capstone Trial",
        faction="science_collective",
        risk_tier="high",
        base_cost_credits=85_000,
        base_duration_days=22,
        base_failure_odds=0.35,
        base_success_payout=240_000,
        briefing=(
            "The quantum sensor capstone the founder's last cohort "
            "designed. Twenty-two-day fabrication-and-trial cycle. The "
            "modeling is at the edge of what current theory supports. "
            "If the sensor calibrates to spec, the next decade of "
            "deep-field detection work has a tool it does not currently "
            "have. The risk is real. So is the prize."
        ),
        success_debrief=(
            "The sensor calibrates. The detection threshold sits where "
            "the modeling said it should, and the noise floor is below "
            "what the field can currently resolve. This is the work. "
            "The Collective will fund the second unit on its own ledger."
        ),
        failure_debrief=(
            "The sensor calibrates to a lower threshold than the modeling "
            "predicted. The result is publishable as a negative. The "
            "field will adjust its expectations. The next iteration "
            "starts from a more honest baseline."
        ),
        outcome_unlock_type="module",
        outcome_unlock_id="advanced_sensor_array",
    ),
    OkaforProjectTemplate(
        id="high_post_outbreak_vaccine_synthesis",
        name="Post-Outbreak Vaccine Synthesis",
        faction="frontier_alliance",
        risk_tier="high",
        base_cost_credits=120_000,
        base_duration_days=28,
        base_failure_odds=0.35,
        base_success_payout=320_000,
        briefing=(
            "A vaccine synthesis project the Frontier Alliance medical-aid "
            "corps has been trying to fund for three years. Four-week "
            "synthesis-and-trial cycle. The pathogen is the one the corps "
            "has watched circulate in the outer belt clinics since the "
            "second-wave outbreak. If the synthesis holds, the Alliance "
            "has a treatment to deploy. If it does not, we have produced "
            "the data that lets the next attempt start closer to the answer."
        ),
        success_debrief=(
            "The synthesis holds at the trial scale. The Alliance corps "
            "has what they have been waiting on. The deployment timeline "
            "is theirs to manage. The work is done."
        ),
        failure_debrief=(
            "The synthesis held at bench scale and degraded under trial "
            "conditions. The corps has the variance data and the outline "
            "of what the next iteration has to address. We did not deliver "
            "a vaccine. We delivered the work the next team will build on."
        ),
        outcome_unlock_type="commodity",
        outcome_unlock_id="medical_supplies",
    ),
)


# ---------------------------------------------------------------------------
# SA-R2 — project ethics map (locked: Decision 2)
# ---------------------------------------------------------------------------
#
# Module-level lookup, NOT a new field on the frozen OkaforProjectTemplate
# (see SA-R2 plan Decision 1 rationale — keeps categorization separate from
# SA-R1's content schema). Keyset must equal the keyset of
# OKAFOR_PROJECT_TEMPLATES; values are one of "heal" | "profit" | "neutral".
#
# Heal: directly serves clinical / public-health outcomes per Dr. Okafor's
# founding principle ("knowledge that does not heal is knowledge wasted").
# Profit: serves industrial / commercial / sensor-network outcomes.
# Neutral: basic-science work that doesn't cleanly belong to either side.

OKAFOR_PROJECT_ETHICS: dict[str, str] = {
    # Low risk (4)
    "low_protein_folding_replication": "neutral",
    "low_archive_recovery": "neutral",
    "low_meta_analysis_pediatric": "heal",
    "low_industrial_dust_filtration": "profit",
    # Mid risk (4)
    "mid_neural_synthesis_protocol": "neutral",
    "mid_orbital_propulsion_efficiency": "profit",
    "mid_field_clinic_supply_chain": "heal",
    "mid_alloy_corrosion_mining_belt": "profit",
    # High risk (2)
    "high_quantum_sensor_capstone": "profit",
    "high_post_outbreak_vaccine_synthesis": "heal",
}


# ---------------------------------------------------------------------------
# Helpers (pure)
# ---------------------------------------------------------------------------


def get_template(template_id: str) -> Optional[OkaforProjectTemplate]:
    """Return the template with this id, or None."""
    for tpl in OKAFOR_PROJECT_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    return None


def seed_for_window(game_day: int) -> int:
    """Return the offer-refresh window index for a given game day.

    Windows are :data:`SLOT_REFRESH_WINDOW_DAYS` long, starting at day 0.
    """
    return game_day // SLOT_REFRESH_WINDOW_DAYS


def roll_offers(
    player_seed_token: str,
    game_day: int,
    *,
    templates: tuple[OkaforProjectTemplate, ...] = OKAFOR_PROJECT_TEMPLATES,
) -> list[str]:
    """Deterministically roll the offer list for a visit.

    The seed is ``f"{window}_{player_seed_token}_okafor"`` so two visits
    inside the same 30-day window produce the same offers and a window
    rollover produces a fresh roll. The slot count is itself
    deterministic per seed (in [SLOT_OFFER_MIN, SLOT_OFFER_MAX]).

    Args:
        player_seed_token: Caller-supplied player identity token (a
            stable string per save — the player name is fine).
        game_day: Current in-game day.
        templates: Override hook for tests.

    Returns:
        List of template ids in deterministic order.
    """
    if not templates:
        return []
    window = seed_for_window(game_day)
    rng = random.Random(f"{window}_{player_seed_token}_okafor")
    upper = min(SLOT_OFFER_MAX, len(templates))
    lower = min(SLOT_OFFER_MIN, upper)
    count = rng.randint(lower, upper) if upper > lower else upper
    sampled = rng.sample(list(templates), count)
    return [t.id for t in sampled]


def compute_team_fund_cost(base_cost: int, n_collaborators: int) -> int:
    """Cost with ``n_collaborators`` slots applied (capped at the max).

    Per acceptance #6: cost ×1.5 per collaborator, capped at 2.0× with
    both slots filled.
    """
    n = max(0, min(n_collaborators, TEAM_FUND_MAX_COLLABORATORS))
    factor = 1.0 + TEAM_FUND_COST_PER_COLLABORATOR * n
    return round(base_cost * factor)


def compute_team_fund_duration(base_days: int, n_collaborators: int) -> int:
    """Duration with ``n_collaborators`` slots applied (capped at the floor).

    Per acceptance #6: duration ×0.7 per collaborator, capped at 0.5×
    with both slots filled. Always at least 1 day.
    """
    n = max(0, min(n_collaborators, TEAM_FUND_MAX_COLLABORATORS))
    factor = TEAM_FUND_DURATION_PER_COLLABORATOR**n
    factor = max(factor, TEAM_FUND_DURATION_FLOOR if n > 0 else 1.0)
    return max(1, math.ceil(base_days * factor))


# ---------------------------------------------------------------------------
# Active project (mutable runtime instance)
# ---------------------------------------------------------------------------


@dataclass
class ActiveProject:
    """A project the player has funded but not yet completed.

    Attributes:
        template_id: Id of the source :class:`OkaforProjectTemplate`.
        accept_day: Game day the project was funded; pinned for the
            seeded RNG so save-and-reload cannot change the outcome.
        duration_days: Resolution day - accept_day. Reduced from
            ``template.base_duration_days`` when team-funded.
        cost_paid: Credits debited at fund time. Drives the failure
            refund (acceptance #9).
        collaborators: Researcher speaker_ids in the team-fund slots.
            Empty list = solo fund.
    """

    template_id: str
    accept_day: int
    duration_days: int
    cost_paid: int
    collaborators: list[str] = field(default_factory=list)

    @property
    def completion_day(self) -> int:
        """Game day on which this project resolves."""
        return self.accept_day + self.duration_days

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "template_id": self.template_id,
            "accept_day": self.accept_day,
            "duration_days": self.duration_days,
            "cost_paid": self.cost_paid,
            "collaborators": list(self.collaborators),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActiveProject":
        """Restore from save data with safe defaults for missing keys."""
        return cls(
            template_id=str(data.get("template_id", "")),
            accept_day=int(data.get("accept_day", 0)),
            duration_days=int(data.get("duration_days", 0)),
            cost_paid=int(data.get("cost_paid", 0)),
            collaborators=list(data.get("collaborators", [])),
        )


# ---------------------------------------------------------------------------
# Patent holding (mutable; outcome of a successful project)
# ---------------------------------------------------------------------------


@dataclass
class PatentHolding:
    """A successful project's patent / IP holding.

    Three player-controllable states (acceptance #8):
      - ``"held"``: default; preserves the option, no income.
      - ``"licensed"``: pays :data:`ROYALTY_RATE` of ``success_payout``
        every :data:`ROYALTY_INTERVAL_DAYS` game days.
      - ``"sold"``: one-time payout at :data:`SELL_LUMP_SUM_RATE`
        of ``success_payout``; the holding is removed after the sale.

    Attributes:
        holding_id: Unique within the player's holdings list, stable
            across saves; constructed from template_id + accept_day.
        template_id: Source project template id (for UI display).
        state: One of ``"held"`` / ``"licensed"`` / ``"sold"``.
        success_payout: Credits the project paid out — drives both
            royalty and lump-sum amounts.
        license_start_day: Game day the patent was first licensed.
            ``0`` while the holding has never been licensed.
        next_royalty_day: Next game day a royalty payment is owed.
            ``0`` while the holding is not in the ``"licensed"`` state.
    """

    holding_id: str
    template_id: str
    state: str
    success_payout: int
    license_start_day: int = 0
    next_royalty_day: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "holding_id": self.holding_id,
            "template_id": self.template_id,
            "state": self.state,
            "success_payout": self.success_payout,
            "license_start_day": self.license_start_day,
            "next_royalty_day": self.next_royalty_day,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatentHolding":
        """Restore from save data with safe defaults for missing keys."""
        return cls(
            holding_id=str(data.get("holding_id", "")),
            template_id=str(data.get("template_id", "")),
            state=str(data.get("state", "held")),
            success_payout=int(data.get("success_payout", 0)),
            license_start_day=int(data.get("license_start_day", 0)),
            next_royalty_day=int(data.get("next_royalty_day", 0)),
        )


# ---------------------------------------------------------------------------
# Resolution + royalty math
# ---------------------------------------------------------------------------


def resolve_completion(
    template: OkaforProjectTemplate,
    active: ActiveProject,
    player_seed_token: str,
    yield_bonus_total: float,
    risk_reduction_total: float,
) -> tuple[bool, int]:
    """Resolve a completed project deterministically.

    Per CLAUDE.md "Gameplay Philosophy" — the seeded RNG fixes the
    outcome at fund time; reload-and-retry cannot change it.

    Effective failure odds clamp to ``[0, base_failure_odds]`` so a very
    high ``risk_reduction_total`` cannot drive odds negative; the success
    payout is multiplied by ``(1 + yield_bonus_total)``; failure refunds
    :data:`FAILURE_REFUND_RATE` of ``active.cost_paid``.

    Args:
        template: The source template.
        active: The funded active project.
        player_seed_token: Stable per-save player token (the player
            name is fine).
        yield_bonus_total: Sum of crew + skill yield bonuses
            (e.g. ``crew_roster.get_bonus("research_yield_bonus") +
            progression.get_bonus("research_yield_bonus")``).
        risk_reduction_total: Sum of crew + skill risk reductions.

    Returns:
        ``(success, payout_in_credits)``. On success ``payout`` is the
        success payout with bonus applied; on failure ``payout`` is the
        30% refund of ``active.cost_paid``.
    """
    rng = random.Random(f"{template.id}_{active.accept_day}_{player_seed_token}")
    roll = rng.random()
    base_odds = template.base_failure_odds
    effective_odds = max(0.0, min(base_odds, base_odds - risk_reduction_total))
    is_success = roll >= effective_odds
    if is_success:
        payout = round(template.base_success_payout * (1.0 + yield_bonus_total))
        return True, payout
    refund = round(active.cost_paid * FAILURE_REFUND_RATE)
    return False, refund


def transition_patent_to_licensed(holding: PatentHolding, current_day: int) -> None:
    """Move a held patent to the ``"licensed"`` state.

    Sets ``license_start_day`` and seeds ``next_royalty_day`` so the
    first royalty pays out :data:`ROYALTY_INTERVAL_DAYS` after the
    transition. Idempotent on already-licensed holdings.
    """
    if holding.state == "licensed":
        return
    holding.state = "licensed"
    holding.license_start_day = current_day
    holding.next_royalty_day = current_day + ROYALTY_INTERVAL_DAYS


def transition_patent_to_sold(holding: PatentHolding) -> int:
    """Move a held / licensed patent to ``"sold"`` and return the lump sum.

    The lump sum is :data:`SELL_LUMP_SUM_RATE` of the success payout.
    Caller is responsible for crediting the player and removing the
    holding from the state's list.
    """
    holding.state = "sold"
    holding.next_royalty_day = 0
    return round(holding.success_payout * SELL_LUMP_SUM_RATE)


def tick_royalties(state: "OkaforResearchState", current_day: int) -> int:
    """Advance every licensed patent's royalty schedule and total payout.

    For every ``"licensed"`` holding, while ``next_royalty_day <=
    current_day``, accrue one :data:`ROYALTY_RATE` payout and advance
    the schedule by :data:`ROYALTY_INTERVAL_DAYS`. Returns the total
    credits owed to the player on this tick.
    """
    total = 0
    for holding in state.holdings:
        if holding.state != "licensed":
            continue
        per_payout = round(holding.success_payout * ROYALTY_RATE)
        while holding.next_royalty_day != 0 and holding.next_royalty_day <= current_day:
            total += per_payout
            holding.next_royalty_day += ROYALTY_INTERVAL_DAYS
    return total


# ---------------------------------------------------------------------------
# Mutable state (per-save)
# ---------------------------------------------------------------------------


@dataclass
class OkaforResearchState:
    """Per-save Okafor Institute runtime state.

    Stored on :class:`spacegame.models.player.Player` as
    ``okafor_research_state``. Kweon's relationship arc lives here as
    a flat int (locked decision: not a sub-rep tier).

    Attributes:
        active_projects: Currently-funded projects, keyed by template
            id. The dict-by-template keying enforces acceptance #4
            (the same template cannot be funded twice in one window).
        holdings: Successful projects' patent / IP records, including
            their license / royalty / sold state.
        kweon_relationship_value: 0-10 trust counter; increments on
            success-debrief, decrements on failure-debrief, used by
            dialogue gates instead of a numbered tier.
        slot_seed_window: Window index :func:`seed_for_window` used for
            the cached ``slot_offers``. View rerolls when current
            window > this value.
        slot_offers: Cached template ids for the current window.
        completed_count: Lifetime successful completions.
        failed_count: Lifetime failures.
        legacy_heal_completed: SA-R2 — count of successfully completed
            heal-tagged projects (per :data:`OKAFOR_PROJECT_ETHICS`).
            Gates Kweon's ethics arc beats. 0 on legacy saves.
        legacy_profit_completed: SA-R2 — count of successfully completed
            profit-tagged projects. 0 on legacy saves.
        legacy_ending: SA-R2 — ``"heal"`` or ``"profit"`` once the
            spread-based ending beat fires; ``""`` until then. Terminal
            arc state: once set, :func:`pending_legacy_beat` returns None.
    """

    active_projects: dict[str, ActiveProject] = field(default_factory=dict)
    holdings: list[PatentHolding] = field(default_factory=list)
    kweon_relationship_value: int = 0
    slot_seed_window: int = -1
    slot_offers: list[str] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    # SA-R2 legacy-arc tracking
    legacy_heal_completed: int = 0
    legacy_profit_completed: int = 0
    legacy_ending: str = ""

    # ---- Relationship arc ----

    def bump_relationship(self, delta: int) -> None:
        """Increment / decrement Kweon's relationship value, clamped.

        Per the locked decision the range is
        ``[RELATIONSHIP_VALUE_MIN, RELATIONSHIP_VALUE_MAX]`` (0-10).
        """
        self.kweon_relationship_value = max(
            RELATIONSHIP_VALUE_MIN,
            min(RELATIONSHIP_VALUE_MAX, self.kweon_relationship_value + delta),
        )

    # ---- Holdings ----

    def find_holding(self, holding_id: str) -> Optional[PatentHolding]:
        """Return the holding with this id, or None."""
        for h in self.holdings:
            if h.holding_id == holding_id:
                return h
        return None

    def remove_holding(self, holding_id: str) -> None:
        """Drop the holding with this id from the list (no-op if absent)."""
        self.holdings = [h for h in self.holdings if h.holding_id != holding_id]

    # ---- Serialization ----

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict."""
        return {
            "active_projects": {k: v.to_dict() for k, v in self.active_projects.items()},
            "holdings": [h.to_dict() for h in self.holdings],
            "kweon_relationship_value": self.kweon_relationship_value,
            "slot_seed_window": self.slot_seed_window,
            "slot_offers": list(self.slot_offers),
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            # SA-R2 fields
            "legacy_heal_completed": self.legacy_heal_completed,
            "legacy_profit_completed": self.legacy_profit_completed,
            "legacy_ending": self.legacy_ending,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OkaforResearchState":
        """Restore from save data with safe defaults for missing keys."""
        active_data = data.get("active_projects", {}) or {}
        active_projects = {str(k): ActiveProject.from_dict(v) for k, v in active_data.items()}
        holdings_data = data.get("holdings", []) or []
        holdings = [PatentHolding.from_dict(h) for h in holdings_data]
        return cls(
            active_projects=active_projects,
            holdings=holdings,
            kweon_relationship_value=int(data.get("kweon_relationship_value", 0)),
            slot_seed_window=int(data.get("slot_seed_window", -1)),
            slot_offers=list(data.get("slot_offers", [])),
            completed_count=int(data.get("completed_count", 0)),
            failed_count=int(data.get("failed_count", 0)),
            # SA-R2 fields — default to 0 / "" on legacy saves
            legacy_heal_completed=int(data.get("legacy_heal_completed", 0)),
            legacy_profit_completed=int(data.get("legacy_profit_completed", 0)),
            legacy_ending=str(data.get("legacy_ending", "")),
        )


# ---------------------------------------------------------------------------
# SA-R2 — arc-beat routing helper
# ---------------------------------------------------------------------------


def pending_legacy_beat(
    state: OkaforResearchState, dialogue_flags: dict[str, bool]
) -> Optional[str]:
    """Return the dialogue tree id of the next due Kweon legacy-arc beat, or None.

    Priority (Decision 4 — locked): endings beat patterns beat firsts; within
    each tier, heal side checked first (heal-ties-default-to-heal rule reflects
    the founder's principle as the institution's stated north star).

    The arc is terminal once ``state.legacy_ending`` is non-empty; all
    subsequent calls return ``None``.

    Args:
        state: The player's current ``OkaforResearchState``.
        dialogue_flags: The player's flat flag dict (``player.dialogue_flags``).

    Returns:
        A dialogue tree id string, or ``None`` if no beat is due.
    """
    # Terminal: ending already fired
    if state.legacy_ending:
        return None

    heal = state.legacy_heal_completed
    profit = state.legacy_profit_completed

    def flag(name: str) -> bool:
        return bool(dialogue_flags.get(name))

    # --- Endings (spread >= 5 AND dominant side >= 6) ---
    if heal - profit >= 5 and heal >= 6 and not flag("okafor_legacy_heal_ending_seen"):
        return "kweon_legacy_heal_ending"
    if profit - heal >= 5 and profit >= 6 and not flag("okafor_legacy_profit_ending_seen"):
        return "kweon_legacy_profit_ending"

    # --- Patterns (3+ on the dominant side, pattern not yet seen) ---
    if heal >= 3 and not flag("okafor_legacy_heal_pattern_seen"):
        return "kweon_legacy_heal_pattern"
    if profit >= 3 and not flag("okafor_legacy_profit_pattern_seen"):
        return "kweon_legacy_profit_pattern"

    # --- Firsts (1+ on the dominant side, first not yet seen) ---
    if heal >= 1 and not flag("okafor_legacy_first_heal_seen"):
        return "kweon_legacy_first_heal"
    if profit >= 1 and not flag("okafor_legacy_first_profit_seen"):
        return "kweon_legacy_first_profit"

    return None


# ---------------------------------------------------------------------------
# Funding entry point
# ---------------------------------------------------------------------------


def fund_project(
    state: OkaforResearchState,
    template: OkaforProjectTemplate,
    accept_day: int,
    collaborators: list[str],
) -> ActiveProject:
    """Insert a funded project into ``state.active_projects``.

    Computes the team-fund cost / duration from ``collaborators`` and
    builds the :class:`ActiveProject`. Caller is responsible for
    deducting the credits from the player.

    Args:
        state: The state to mutate.
        template: The source template.
        accept_day: Player's current ``game_day`` at fund time.
        collaborators: Researcher speaker_ids filling the team-fund
            slots; capped at :data:`TEAM_FUND_MAX_COLLABORATORS` upstream.

    Returns:
        The newly-inserted :class:`ActiveProject` (also stored in
        ``state.active_projects[template.id]``).
    """
    n = len(collaborators)
    cost = compute_team_fund_cost(template.base_cost_credits, n)
    duration = compute_team_fund_duration(template.base_duration_days, n)
    active = ActiveProject(
        template_id=template.id,
        accept_day=accept_day,
        duration_days=duration,
        cost_paid=cost,
        collaborators=list(collaborators),
    )
    state.active_projects[template.id] = active
    return active


def make_holding_id(template_id: str, accept_day: int) -> str:
    """Stable holding id constructor — used by the view at success time."""
    return f"{template_id}_{accept_day}"


# ---------------------------------------------------------------------------
# Project-resolution sweep (game-day tick entry point)
# ---------------------------------------------------------------------------


@dataclass
class ProjectOutcome:
    """Side-effect record from resolving a completed project.

    Returned by :func:`resolve_completed_projects` so the caller can
    apply credits, set journal flags, and surface notifications without
    re-deriving any of the math.

    Attributes:
        template_id: The source template's id.
        accept_day: The active project's ``accept_day`` (preserved for
            holding-id construction and display).
        success: Whether the project succeeded.
        payout: Credits to award to the player. On success, the
            yield-bonus-adjusted success payout. On failure, the 30%
            refund of cost_paid.
        holding_id: Non-empty on success; empty on failure.
    """

    template_id: str
    accept_day: int
    success: bool
    payout: int
    holding_id: str = ""


def resolve_completed_projects(
    state: OkaforResearchState,
    current_day: int,
    player_seed_token: str,
    yield_bonus_total: float,
    risk_reduction_total: float,
) -> list[ProjectOutcome]:
    """Resolve every active project whose completion day has arrived.

    Mutates ``state``: removes resolved projects from
    ``active_projects``, appends a :class:`PatentHolding` (state =
    ``"held"``) for each success, increments ``completed_count`` or
    ``failed_count`` accordingly, and bumps Kweon's relationship value
    (+1 on success, -1 on failure).

    Args:
        state: The research state to advance.
        current_day: The player's current ``game_day``.
        player_seed_token: Stable per-save player token (the player
            name is fine).
        yield_bonus_total: Sum of crew + skill yield bonuses.
        risk_reduction_total: Sum of crew + skill risk reductions.

    Returns:
        A list of :class:`ProjectOutcome` describing each resolved
        project. The list is in deterministic order (sorted by
        template id) so the caller's notification feed is stable.
    """
    completed_ids: list[str] = []
    for template_id, active in state.active_projects.items():
        if active.completion_day <= current_day:
            completed_ids.append(template_id)
    completed_ids.sort()

    outcomes: list[ProjectOutcome] = []
    for template_id in completed_ids:
        active = state.active_projects[template_id]
        template = get_template(template_id)
        if template is None:
            # Stale active project pointing at a removed template — drop
            # it without payout. Defensive against a content rename.
            del state.active_projects[template_id]
            continue
        success, payout = resolve_completion(
            template, active, player_seed_token, yield_bonus_total, risk_reduction_total
        )
        if success:
            holding_id = make_holding_id(template_id, active.accept_day)
            state.holdings.append(
                PatentHolding(
                    holding_id=holding_id,
                    template_id=template_id,
                    state="held",
                    success_payout=payout,
                )
            )
            state.completed_count += 1
            state.bump_relationship(1)
            outcomes.append(
                ProjectOutcome(
                    template_id=template_id,
                    accept_day=active.accept_day,
                    success=True,
                    payout=payout,
                    holding_id=holding_id,
                )
            )
        else:
            state.failed_count += 1
            state.bump_relationship(-1)
            outcomes.append(
                ProjectOutcome(
                    template_id=template_id,
                    accept_day=active.accept_day,
                    success=False,
                    payout=payout,
                    holding_id="",
                )
            )
        del state.active_projects[template_id]
    return outcomes
