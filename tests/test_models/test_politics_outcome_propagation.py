"""SA-P2 — outcome propagation tests (AC 4 + AC 5).

Asserts that all four outcome categories (win, partial_win_coalition_thin,
partial_win_off_record, loss) propagate end-to-end:
- (a) rep deltas via apply_reputation_with_spillover
- (b) market shifts registered with correct magnitude/duration/system
- (c) mission flags via dispute_resolved / coalition_won / dispute_mediated
- (d) news headline gating per SA-P1 §7.6 (both branches asserted)

Uses the synthetic water_rights_phasing fixture from
``tests/test_models/test_politics_dispute._make_water_rights_phasing_template``.
"""

from __future__ import annotations

from typing import Any, Optional

import pytest

from tests.test_models.test_politics_dispute import _make_water_rights_phasing_template

from spacegame.constants.flags import (
    coalition_won,
    dispute_mediated,
    dispute_resolved,
)
from spacegame.models.politics_dispute import (
    PoliticsDisputeManager,
    PoliticsMarketShift,
)


# ---------------------------------------------------------------------------
# Stubs for politics_manager / player / market / news_ticker
# ---------------------------------------------------------------------------


class _StubPlayer:
    def __init__(self, reputation: Optional[dict[str, int]] = None) -> None:
        self.reputation: dict[str, int] = dict(reputation or {})
        self.dialogue_flags: dict[str, bool] = {}

    def modify_reputation(self, faction_id: str, amount: int) -> tuple[bool, str]:
        self.reputation[faction_id] = self.reputation.get(faction_id, 0) + amount
        return True, ""

    def get_reputation(self, faction_id: str) -> int:
        return self.reputation.get(faction_id, 0)


class _StubFaction:
    def __init__(self, rivalry: str = "") -> None:
        self.rivalry = rivalry


class _StubPoliticsManager:
    """Mirrors `apply_reputation_with_spillover` and tracks calls for assert."""

    def __init__(self, factions: Optional[dict[str, _StubFaction]] = None) -> None:
        self._factions = dict(factions or {})
        self.calls: list[tuple[str, int]] = []

    def apply_reputation_with_spillover(
        self, player: _StubPlayer, faction_id: str, amount: int
    ) -> list[tuple[str, int]]:
        changes = []
        player.modify_reputation(faction_id, amount)
        self.calls.append((faction_id, amount))
        changes.append((faction_id, amount))
        faction = self._factions.get(faction_id)
        if faction and faction.rivalry:
            spillover = -int(amount * 0.5)
            if spillover != 0:
                player.modify_reputation(faction.rivalry, spillover)
                self.calls.append((faction.rivalry, spillover))
                changes.append((faction.rivalry, spillover))
        return changes


class _StubNewsTicker:
    def __init__(self) -> None:
        self.headlines: list[str] = []

    def add_headline(self, text: str, priority: int = 5) -> None:
        self.headlines.append(text)


class _StubMarket:
    def __init__(self, system_id: str, game_day: int = 1) -> None:
        self.system_id = system_id
        self.game_day = game_day
        self.politics_shifts: list[PoliticsMarketShift] = []

    def add_politics_shift(self, shift: PoliticsMarketShift) -> None:
        self.politics_shifts.append(shift)


class _StubBonus:
    def __init__(self, bonuses: Optional[dict[str, float]] = None) -> None:
        self._b = dict(bonuses or {})

    def get_bonus(self, key: str) -> float:
        return float(self._b.get(key, 0.0))


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------


def _build_propagation_setup(
    *,
    starting_rep: Optional[dict[str, int]] = None,
    spillover: bool = False,
):
    tpl = _make_water_rights_phasing_template()
    player = _StubPlayer(reputation=starting_rep or {})
    if spillover:
        factions = {
            "verdant": _StubFaction(rivalry="frontier_alliance"),
            "frontier_alliance": _StubFaction(rivalry="verdant"),
            "crimson_reach": _StubFaction(rivalry=""),
        }
    else:
        factions = {
            "verdant": _StubFaction(rivalry=""),
            "frontier_alliance": _StubFaction(rivalry=""),
            "crimson_reach": _StubFaction(rivalry=""),
        }
    politics = _StubPoliticsManager(factions=factions)
    news = _StubNewsTicker()
    market = _StubMarket("verdant", game_day=10)

    def _market_lookup(system_id: str) -> Optional[_StubMarket]:
        return market if system_id == "verdant" else None

    mgr = PoliticsDisputeManager(
        templates={tpl.id: tpl},
        politics_manager=politics,
        news_ticker=news,
        crew_roster=_StubBonus({"coalition_size_bonus": 1.0}),  # cap = 2
        progression=_StubBonus({"coalition_size_bonus": 1.0}),  # cap = 3
        market_lookup=_market_lookup,
    )
    mgr.set_player(player)
    dispute = mgr.start_dispute(tpl.id, current_game_day=10)
    return mgr, dispute, player, politics, news, market


# ---------------------------------------------------------------------------
# Outcome category tests
# ---------------------------------------------------------------------------


class TestOutcomePropagationLoss:
    """Loss path: vote fails, no concessions."""

    def test_loss_applies_negative_rep(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        # No arguments, no pre-commits — three rounds of abstention.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.resolved_outcome == "loss"
        assert player.reputation["verdant"] == -2
        assert player.reputation["frontier_alliance"] == -1
        assert player.reputation["crimson_reach"] == 2

    def test_loss_registers_market_shift(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert len(market.politics_shifts) == 1
        shift = market.politics_shifts[0]
        assert shift.commodity_id == "fresh_water"
        assert shift.system_id == "verdant"
        assert shift.magnitude == pytest.approx(-0.10)
        assert shift.duration_days == 30

    def test_loss_sets_mission_lock_flag(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        # Loss row uses mission_locks (not mission_unlocks).
        assert player.dialogue_flags.get(
            dispute_resolved("water_rights_phasing")
        ) is True

    def test_loss_emits_news_headline_via_magnitude_qualifier(self) -> None:
        """Loss with -10% commodity shift satisfies §7.6 (>=10% AND loss)."""
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert len(news.headlines) == 1
        assert "rejects water rights phasing" in news.headlines[0]


class TestOutcomePropagationWin:
    """Win path: full coalition pre-committed (>=60%) and vote passes."""

    def test_win_with_full_coalition(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        # Pre-commit two of three delegates (>=60% threshold).
        mgr.do_corridor_visit(
            dispute, "samela_drift", "practical_cost", success_override=True
        )
        mgr.do_corridor_visit(
            dispute, "ferron_hask", "practical_cost", success_override=True
        )
        # Both pre-committed delegates start at leaning_yes -> they vote yes.
        # That's 2 yes vs 1 no (Marsh leaning_no). Vote immediately to skip
        # the counter phase.
        mgr.cast_vote(dispute)
        assert dispute.resolved_outcome == "win"
        assert player.reputation["verdant"] == 5
        assert player.dialogue_flags.get(coalition_won("water_rights_phasing")) is True

    def test_win_emits_news_headline(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        mgr.do_corridor_visit(
            dispute, "samela_drift", "practical_cost", success_override=True
        )
        mgr.do_corridor_visit(
            dispute, "ferron_hask", "practical_cost", success_override=True
        )
        mgr.cast_vote(dispute)
        assert len(news.headlines) == 1
        assert "phases water rights" in news.headlines[0]

    def test_win_registers_two_market_shifts(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        mgr.do_corridor_visit(
            dispute, "samela_drift", "practical_cost", success_override=True
        )
        mgr.do_corridor_visit(
            dispute, "ferron_hask", "practical_cost", success_override=True
        )
        mgr.cast_vote(dispute)
        # Win row has TWO shifts (fresh_water +10%, hydroponics_yield -8%).
        # The hydroponics shift targets system "verdant" — both go to the
        # verdant market.
        assert len(market.politics_shifts) == 2
        commodities = {s.commodity_id for s in market.politics_shifts}
        assert commodities == {"fresh_water", "hydroponics_yield"}


class TestOutcomePropagationPartialWinCoalitionThin:
    """Vote passes with <60% pre-committed (just won by argument push)."""

    def test_thin_win_no_news_no_tier_crossing(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup(
            starting_rep={"verdant": 0}
        )
        # Construct a thin win directly: set 2 of 3 delegates to
        # leaning_yes (vote passes 2-1) but no pre-commits set
        # (coalition ratio = 0/3 < 60%).
        dispute.delegates["samela_drift"].visible_state = "leaning_yes"
        dispute.delegates["ferron_hask"].visible_state = "leaning_yes"
        mgr.cast_vote(dispute)
        assert dispute.resolved_outcome == "partial_win_coalition_thin"
        assert player.reputation["verdant"] == 2
        assert (
            player.dialogue_flags.get(dispute_resolved("water_rights_phasing"))
            is True
        )

    def test_thin_win_news_suppressed_unless_tier_crossing(self) -> None:
        from spacegame.models.politics_dispute import PoliticsArgument

        mgr, dispute, player, politics, news, market = _build_propagation_setup(
            starting_rep={"verdant": 0}
        )
        dispute.delegates["samela_drift"].visible_state = "leaning_yes"
        dispute.delegates["ferron_hask"].visible_state = "leaning_yes"
        mgr.cast_vote(dispute)
        # Outcome is partial_win_coalition_thin; news_headline = None in
        # the row, AND no tier crossed -> no news emitted.
        assert news.headlines == []


class TestOutcomePropagationPartialWinOffRecord:
    """Vote fails, but at least one delegate has the conceded flag."""

    def test_off_record_with_conceded_delegate(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        # Mark one delegate conceded directly (mediation success would set this).
        dispute.delegates["ollo_marsh"].conceded = True
        mgr.cast_vote(dispute)
        # Vote fails (all leaning_no/wavering) BUT conceded delegate
        # rescues -> partial_win_off_record.
        assert dispute.resolved_outcome == "partial_win_off_record"
        assert player.reputation["verdant"] == 3
        assert (
            player.dialogue_flags.get(dispute_mediated("water_rights_phasing"))
            is True
        )

    def test_off_record_news_suppressed_when_no_tier_crossing(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup()
        dispute.delegates["ollo_marsh"].conceded = True
        mgr.cast_vote(dispute)
        # news_headline is None in the row -> nothing emitted.
        assert news.headlines == []


class TestNewsGatingPositiveAndNegative:
    """AC 5(d): news headline fires when §7.6 conditions hold and is
    suppressed when they don't (both branches asserted)."""

    def test_partial_win_with_tier_crossing_emits_news(self) -> None:
        """If a partial-win row's rep delta crosses a tier boundary, news fires."""
        from spacegame.models.politics_dispute import (
            OutcomeRow,
            PoliticsDisputeTemplate,
            DelegateTemplate,
            PoliticsMarketShift,
        )

        # Build a custom template whose partial_win_off_record row has a
        # news_headline AND deltas large enough to cross a boundary.
        tpl = _make_water_rights_phasing_template()
        # Mutate row in a fresh template instance.
        new_row = OutcomeRow(
            rep_deltas={"verdant": 30},  # 0 -> 30 crosses +25 boundary
            news_headline="Verdant council brokers compromise; tier rises.",
        )
        new_matrix = dict(tpl.outcome_matrix)
        new_matrix["partial_win_off_record"] = new_row
        custom = PoliticsDisputeTemplate(
            id="custom_test",
            headline=tpl.headline,
            factions_affected=tpl.factions_affected,
            base_difficulty=tpl.base_difficulty,
            round_count=tpl.round_count,
            deadline_days=tpl.deadline_days,
            delegates=tpl.delegates,
            eligible_framings=tpl.eligible_framings,
            eligible_evidence=tpl.eligible_evidence,
            framing_modifiers=tpl.framing_modifiers,
            framing_target_dimensions=tpl.framing_target_dimensions,
            outcome_matrix=new_matrix,
        )

        player = _StubPlayer(reputation={"verdant": 0})
        politics = _StubPoliticsManager(
            factions={"verdant": _StubFaction(rivalry="")}
        )
        news = _StubNewsTicker()
        mgr = PoliticsDisputeManager(
            templates={custom.id: custom},
            politics_manager=politics,
            news_ticker=news,
        )
        mgr.set_player(player)
        dispute = mgr.start_dispute("custom_test", current_game_day=1)
        dispute.delegates["ollo_marsh"].conceded = True
        mgr.cast_vote(dispute)
        assert dispute.resolved_outcome == "partial_win_off_record"
        # Tier boundary 25 crossed (rep went 0 -> 30) -> news fires.
        assert len(news.headlines) == 1

    def test_loss_without_magnitude_or_tier_crossing_suppresses_news(self) -> None:
        """Loss with sub-10% shift and no tier crossing does not emit news."""
        from spacegame.models.politics_dispute import (
            OutcomeRow,
            PoliticsDisputeTemplate,
            PoliticsMarketShift,
        )

        tpl = _make_water_rights_phasing_template()
        new_matrix = dict(tpl.outcome_matrix)
        new_matrix["loss"] = OutcomeRow(
            rep_deltas={"verdant": -1},  # tiny, no boundary
            market_shifts=(
                PoliticsMarketShift("fresh_water", "verdant", 0.04),
            ),  # under 10%
            news_headline="Verdant council declines small adjustment; minor effect.",
        )
        custom = PoliticsDisputeTemplate(
            id="custom_loss",
            headline=tpl.headline,
            factions_affected=tpl.factions_affected,
            base_difficulty=tpl.base_difficulty,
            round_count=tpl.round_count,
            deadline_days=tpl.deadline_days,
            delegates=tpl.delegates,
            eligible_framings=tpl.eligible_framings,
            eligible_evidence=tpl.eligible_evidence,
            framing_modifiers=tpl.framing_modifiers,
            framing_target_dimensions=tpl.framing_target_dimensions,
            outcome_matrix=new_matrix,
        )

        player = _StubPlayer(reputation={"verdant": 0})
        politics = _StubPoliticsManager(
            factions={"verdant": _StubFaction(rivalry="")}
        )
        news = _StubNewsTicker()
        mgr = PoliticsDisputeManager(
            templates={custom.id: custom},
            politics_manager=politics,
            news_ticker=news,
        )
        mgr.set_player(player)
        dispute = mgr.start_dispute("custom_loss", current_game_day=1)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.resolved_outcome == "loss"
        # Neither magnitude nor tier crossing — news suppressed even with
        # a configured headline.
        assert news.headlines == []


class TestSpilloverPipelineUsed:
    """AC 5(a): rep deltas flow through apply_reputation_with_spillover."""

    def test_spillover_call_recorded(self) -> None:
        mgr, dispute, player, politics, news, market = _build_propagation_setup(
            spillover=True
        )
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        # Loss row applies -2 to verdant, -1 to frontier_alliance, +2 to
        # crimson_reach. Spillover entries also recorded by the stub.
        primary = [c for c in politics.calls]
        assert ("verdant", -2) in primary
        assert ("frontier_alliance", -1) in primary
        assert ("crimson_reach", 2) in primary
        # Verdant rep dropped 2 -> spillover should produce a positive
        # +1 entry for frontier_alliance (verdant's rivalry).
        assert any(c == ("frontier_alliance", 1) for c in primary)
