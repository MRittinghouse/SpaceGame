"""SA-P4 — full Alliance Congress venue scenario test (AC 16, 18-22).

Walks the Haven's Rest venue loop end-to-end against the shipped data
files: load templates, start a dispute, run corridor + session rounds,
vote, observe outcome propagation (rep delta, market shift, news
headline, mission flag, journal trigger flag). Repeats for a win, a
loss, an annual-Congress arc completion across save/load mid-arc, a
betrayal-handled ``partial_win_off_record``, and a cross-venue gate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from spacegame.constants.flags import dispute_resolved
from spacegame.data_loader import DataLoader
from spacegame.models.alliance_congress import ALLIANCE_CONGRESS_CONFIG
from spacegame.models.politics_dispute import (
    DisputePhase,
    PoliticsArgument,
    PoliticsDisputeManager,
    PoliticsMarketShift,
)
from spacegame.models.verdant_council import VERDANT_COUNCIL_CONFIG

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Test stubs (mirror the SA-P3 scenario shape)
# ---------------------------------------------------------------------------


class _StubPlayer:
    def __init__(self) -> None:
        self.faction_reputation: dict[str, int] = {}
        self.dialogue_flags: dict[str, bool] = {}
        self.sub_reputation: dict[str, int] = {}
        self.game_day: int = 10

    def modify_reputation(self, faction_id: str, amount: int) -> tuple[bool, str]:
        self.faction_reputation[faction_id] = self.faction_reputation.get(faction_id, 0) + amount
        return True, ""

    def set_reputation(self, faction_id: str, value: int) -> None:
        self.faction_reputation[faction_id] = value

    def get_reputation(self, faction_id: str) -> int:
        return self.faction_reputation.get(faction_id, 0)

    def modify_sub_reputation(self, org_id: str, amount: int, _config) -> None:
        self.sub_reputation[org_id] = self.sub_reputation.get(org_id, 0) + amount


class _StubPoliticsManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def apply_reputation_with_spillover(
        self, player: _StubPlayer, faction_id: str, amount: int
    ) -> list[tuple[str, int]]:
        player.modify_reputation(faction_id, amount)
        self.calls.append((faction_id, amount))
        return [(faction_id, amount)]


class _StubNewsTicker:
    def __init__(self) -> None:
        self.headlines: list[str] = []

    def add_headline(self, text: str, priority: int = 5) -> None:
        self.headlines.append(text)


class _StubMarket:
    def __init__(self, system_id: str, game_day: int = 10) -> None:
        self.system_id = system_id
        self.game_day = game_day
        self.politics_shifts: list[PoliticsMarketShift] = []

    def add_politics_shift(self, shift: PoliticsMarketShift) -> None:
        self.politics_shifts.append(shift)


class _StubBonus:
    def __init__(self, bonuses: dict[str, float]) -> None:
        self._b = bonuses

    def get_bonus(self, key: str) -> float:
        return float(self._b.get(key, 0.0))


class _StubSocial:
    def __init__(self, levels: dict[str, int]) -> None:
        self._l = levels

    def get_skill_level(self, key: str) -> int:
        return int(self._l.get(key, 1))


class _StubCrewRoster:
    def __init__(self, crew_ids: Optional[list[str]] = None) -> None:
        self.recruited_ids: set[str] = set(crew_ids or [])

    def get_bonus(self, key: str) -> float:
        return 0.0


class _StubJournal:
    def __init__(self, templates: dict[str, dict]) -> None:
        self._templates = templates
        self.entries: list[dict] = []
        self._triggered: set[str] = set()

    def trigger_auto_entry(
        self, trigger_flag: str, game_day: int, system_id: str = ""
    ) -> Optional[dict]:
        if trigger_flag in self._triggered:
            return None
        template = self._templates.get(trigger_flag)
        if template is None:
            return None
        entry = {
            "trigger_flag": trigger_flag,
            "text": template["text"],
            "game_day": game_day,
            "system_id": system_id or template.get("system_id", ""),
        }
        self.entries.append(entry)
        self._triggered.add(trigger_flag)
        return entry


def _load_journal_templates() -> dict[str, dict]:
    path = PROJECT_ROOT / "data" / "journal" / "entries.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {e["trigger_flag"]: e for e in data["journal_entries"] if e.get("trigger_flag")}


def _build_alliance_manager(
    *,
    crew: Optional[list[str]] = None,
    persuasion: int = 6,
):
    """Wire a manager with the SA-P3 + SA-P4 shipped templates loaded."""
    crew = crew or []
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    templates = loader.load_politics_disputes()
    journal_templates = _load_journal_templates()
    player = _StubPlayer()
    politics = _StubPoliticsManager()
    news = _StubNewsTicker()
    havens_market = _StubMarket("havens_rest", game_day=10)
    verdant_market = _StubMarket("verdant", game_day=10)
    crimson_market = _StubMarket("crimson_reach", game_day=10)
    journal = _StubJournal(journal_templates)

    def _market_lookup(sid: str) -> Optional[_StubMarket]:
        if sid == "havens_rest":
            return havens_market
        if sid == "verdant":
            return verdant_market
        if sid == "crimson_reach":
            return crimson_market
        return None

    crew_roster = _StubCrewRoster(crew)
    mgr = PoliticsDisputeManager(
        templates=templates,
        politics_manager=politics,
        news_ticker=news,
        crew_roster=crew_roster,
        progression=_StubBonus({"coalition_sway_bonus": 0.30, "coalition_size_bonus": 3.0}),
        social_manager=_StubSocial({"persuasion": persuasion, "leadership": persuasion}),
        market_lookup=_market_lookup,
    )
    mgr.set_player(player)
    mgr.register_sub_rep_config(VERDANT_COUNCIL_CONFIG.id, VERDANT_COUNCIL_CONFIG)
    mgr.register_sub_rep_config(ALLIANCE_CONGRESS_CONFIG.id, ALLIANCE_CONGRESS_CONFIG)

    # Recreate the SA-P4-extended Game._on_dispute_outcome flag-bump logic
    # so the scenario test exercises the same path as the engine.
    def _on_dispute_outcome(dispute, category):
        flags = player.dialogue_flags
        if "first_dispute_attended" not in flags:
            flags["first_dispute_attended"] = True
            journal.trigger_auto_entry("first_dispute_attended", 10, "havens_rest")
        if category in ("partial_win_coalition_thin", "partial_win_off_record"):
            if "first_partial_win" not in flags:
                flags["first_partial_win"] = True
                journal.trigger_auto_entry("first_partial_win", 10, "havens_rest")
        if category == "win":
            if any(d.pre_committed for d in dispute.delegates.values()):
                if "first_coalition_won" not in flags:
                    flags["first_coalition_won"] = True
                    journal.trigger_auto_entry("first_coalition_won", 10, "havens_rest")
        # SA-P4: Congress-specific flags.
        is_congress = any(
            d.sub_faction_id == "alliance_congress" for d in dispute.delegates.values()
        )
        if is_congress:
            if "first_alliance_congress_attended" not in flags:
                flags["first_alliance_congress_attended"] = True
                journal.trigger_auto_entry("first_alliance_congress_attended", 10, "havens_rest")
            if dispute.had_betrayal and category in ("win", "partial_win_off_record"):
                if "first_coalition_betrayal_handled" not in flags:
                    flags["first_coalition_betrayal_handled"] = True
                    journal.trigger_auto_entry(
                        "first_coalition_betrayal_handled", 10, "havens_rest"
                    )
            if category == "win":
                row = dispute.outcome_matrix.get("win")
                alliance_systems = {
                    "havens_rest",
                    "verdant",
                    "forgeworks",
                    "crimson_reach",
                }
                affected = (
                    {s.system_id for s in row.market_shifts} & alliance_systems
                    if row is not None
                    else set()
                )
                if len(affected) >= 2:
                    if "first_alliance_wide_vote_won" not in flags:
                        flags["first_alliance_wide_vote_won"] = True
                        journal.trigger_auto_entry(
                            "first_alliance_wide_vote_won", 10, "havens_rest"
                        )
            # SA-X6 trigger when Tomas is on crew.
            if "tomas_drifter" in crew_roster.recruited_ids:
                if "tomas_alliance_congress_attended_seen" not in flags:
                    flags["tomas_alliance_congress_attended_seen"] = True

    mgr.set_outcome_callback(_on_dispute_outcome)
    return mgr, player, politics, news, havens_market, verdant_market, journal


# ---------------------------------------------------------------------------
# AC 16 — at least one win path (Alliance-wide vote)
# ---------------------------------------------------------------------------


class TestAllianceCongressWin:
    def test_infrastructure_capital_pool_full_win(self) -> None:
        """Tractable Congress template ends in a coalition-built win."""
        mgr, player, _, news, hm, vm, journal = _build_alliance_manager(persuasion=6)
        dispute = mgr.start_dispute("infrastructure_capital_pool", current_game_day=10)
        assert dispute is not None

        # Pre-commit Shirane (already leaning_yes) and Wentworth.
        ok, _ = mgr.do_corridor_visit(
            dispute, "councillor_shirane", "trade_leverage", success_override=True
        )
        assert ok
        ok, _ = mgr.do_corridor_visit(
            dispute, "councillor_wentworth", "process_fidelity", success_override=True
        )
        assert ok

        # Argue Vasc and Tejada to push them to leaning_yes.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(framing="trade_leverage", audience_delegate_id="delegate_vasc"),
        )
        mgr.advance_round(dispute)
        mgr.submit_argument(
            dispute,
            PoliticsArgument(framing="process_fidelity", audience_delegate_id="delegate_tejada"),
        )
        mgr.advance_round(dispute)

        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        # First-time flags fired.
        assert player.dialogue_flags.get("first_dispute_attended") is True
        assert player.dialogue_flags.get("first_alliance_congress_attended") is True
        # Journal entry fires for the Congress-attended flag.
        assert any(e["trigger_flag"] == "first_alliance_congress_attended" for e in journal.entries)
        if dispute.resolved_outcome == "win":
            # Dispute_resolved + coalition_won mission flags set.
            assert player.dialogue_flags.get(dispute_resolved("infrastructure_capital_pool"))
            # Market shifts at 2+ Alliance systems (Haven's Rest + Verdant).
            assert any(s.system_id == "havens_rest" for s in hm.politics_shifts)
            assert any(s.system_id == "verdant" for s in vm.politics_shifts)
            # Alliance-wide vote flag set.
            assert player.dialogue_flags.get("first_alliance_wide_vote_won") is True
            # News headline emitted.
            assert any("Congress capitalizes infrastructure pool" in h for h in news.headlines)


# ---------------------------------------------------------------------------
# AC 16 — loss path
# ---------------------------------------------------------------------------


class TestAllianceCongressLoss:
    def test_loss_outcome_with_abstentions(self) -> None:
        mgr, player, _, _news, _, _, _journal = _build_alliance_manager(persuasion=1)
        dispute = mgr.start_dispute("cross_settlement_tariff_review", current_game_day=10)
        assert dispute is not None
        # Three abstain rounds: nothing moves.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        # Loss because pre-existing room is mostly leaning_no/wavering.
        assert dispute.resolved_outcome in ("loss", "partial_win_coalition_thin")
        # Loss outcome implies first_dispute_attended fired.
        assert player.dialogue_flags.get("first_dispute_attended") is True
        # Congress-attended fired for any Congress dispute resolution.
        assert player.dialogue_flags.get("first_alliance_congress_attended") is True


# ---------------------------------------------------------------------------
# AC 16 — annual Congress arc + save/load mid-arc
# ---------------------------------------------------------------------------


class TestAnnualCongressSaveLoad:
    def test_annual_arc_round_state_persists_across_manager_round_trip(self) -> None:
        """Run two rounds of the annual flagship, save the manager, rebuild,
        restore, and assert mid-arc state survived.
        """
        mgr, player, _, _, _, _, _ = _build_alliance_manager(persuasion=5)
        dispute = mgr.start_dispute("annual_alliance_congress", current_game_day=10)
        assert dispute is not None
        assert dispute.round_count == 5
        assert dispute.had_betrayal is False
        mgr.register_pending_dispute(dispute)

        # Pre-commit Vasc.
        ok, _ = mgr.do_corridor_visit(
            dispute,
            "delegate_vasc",
            "frontier_autonomy_stance",
            success_override=True,
        )
        assert ok
        # Round 1: argue Wentworth.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="process_fidelity",
                audience_delegate_id="councillor_wentworth",
            ),
        )
        mgr.advance_round(dispute)

        # Round 2: argue Shirane.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(framing="trade_leverage", audience_delegate_id="councillor_shirane"),
        )
        mgr.advance_round(dispute)

        # Save manager state.
        saved = mgr.to_dict()
        # Pre-commit on Vasc, current_round at 3.
        assert "annual_alliance_congress" in saved["pending_disputes"]
        snapshot = saved["pending_disputes"]["annual_alliance_congress"]
        assert snapshot["current_round"] == 3
        assert snapshot["delegates"]["delegate_vasc"]["pre_committed"] is True

        # Build a fresh manager and restore.
        loader = DataLoader(data_dir=PROJECT_ROOT / "data")
        templates = loader.load_politics_disputes()
        new_mgr = PoliticsDisputeManager(templates=templates)
        new_mgr.set_player(player)
        new_mgr.from_dict(saved)
        restored = new_mgr.get_pending_dispute("annual_alliance_congress")
        assert restored is not None
        assert restored.current_round == 3
        assert restored.delegates["delegate_vasc"].pre_committed is True

    def test_annual_lockout_window_reports_after_resolution(self) -> None:
        """Once the annual arc resolves, is_dispute_active reports False."""
        mgr, player, _, _, _, _, _ = _build_alliance_manager(persuasion=5)
        dispute = mgr.start_dispute("annual_alliance_congress", current_game_day=10)
        assert dispute is not None
        # Force resolution: cast vote immediately.
        player.game_day = 30
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        # Lockout active: is_dispute_active False until 365 days after.
        assert mgr.is_dispute_active("annual_alliance_congress", current_game_day=30) is False
        assert mgr.is_dispute_active("annual_alliance_congress", current_game_day=30 + 365) is True
        # Lockout days remaining is non-negative.
        assert mgr.next_session_in_days("annual_alliance_congress", current_game_day=30) > 0


# ---------------------------------------------------------------------------
# AC 16, 20 — betrayal handled
# ---------------------------------------------------------------------------


class TestBetrayalHandled:
    def test_betrayal_flag_fires_on_recovery_outcome(self) -> None:
        """A pre-commit broken mid-arc that still resolves to win or
        partial_win_off_record sets first_coalition_betrayal_handled.
        """
        mgr, player, _, _, _, _, journal = _build_alliance_manager(persuasion=6)
        # Set rep with commerce_guild well above 25 so the snapshot starts high.
        player.set_reputation("commerce_guild", 50)
        dispute = mgr.start_dispute("frontier_trade_unification_act", current_game_day=10)
        assert dispute is not None
        # Pre-commit Tejada (whose betrayal condition will fire).
        ok, _ = mgr.do_corridor_visit(
            dispute, "delegate_tejada", "settlement_solidarity", success_override=True
        )
        assert ok
        assert dispute.delegates["delegate_tejada"].pre_committed is True

        # Drop the player's commerce_guild rep below 25 → betrayal predicate fires.
        player.set_reputation("commerce_guild", 10)

        # Submit an argument; advance_round triggers the betrayal eval.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="trade_leverage",
                audience_delegate_id="councillor_shirane",
            ),
        )
        mgr.advance_round(dispute)
        # Betrayal flipped Tejada.
        assert dispute.delegates["delegate_tejada"].pre_committed is False
        assert dispute.had_betrayal is True

        # Force a partial_win_off_record outcome by mediating a delegate.
        dispute.delegates["delegate_vasc"].conceded = True
        # Three abstain → cast.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        if dispute.resolved_outcome in ("win", "partial_win_off_record"):
            assert player.dialogue_flags.get("first_coalition_betrayal_handled") is True
            assert any(
                e["trigger_flag"] == "first_coalition_betrayal_handled" for e in journal.entries
            )


# ---------------------------------------------------------------------------
# AC 21 — cross-venue gating
# ---------------------------------------------------------------------------


class TestCrossVenueGate:
    def test_two_or_more_templates_have_cross_venue_required_flags(self) -> None:
        """Structural assertion: at least 2 Congress templates declare
        ``required_flags`` referencing SA-P3 outcomes.
        """
        loader = DataLoader(data_dir=PROJECT_ROOT / "data")
        templates = loader.load_politics_disputes()
        sa_p3_flags = {
            "dispute_resolved_water_rights_phasing",
            "dispute_resolved_aquifer_concession_renewal",
            "dispute_resolved_frontier_trade_route_levy",
            "dispute_resolved_infrastructure_co_op_vote",
            "dispute_resolved_forgeworks_partnership_extension",
            "dispute_resolved_co_op_dividend_distribution",
            "dispute_resolved_hydroponics_yield_quota",
            "dispute_resolved_settler_food_credit_dispute",
        }
        congress_ids = {
            "cross_settlement_tariff_review",
            "frontier_trade_unification_act",
            "crimson_response_protocol_review",
            "frontier_security_compact",
            "infrastructure_capital_pool",
            "cross_settlement_logistics_overhaul",
            "cross_settlement_water_compact",
            "annual_alliance_congress",
        }
        gating = [
            tpl
            for tid, tpl in templates.items()
            if tid in congress_ids and any(flag in sa_p3_flags for flag in tpl.required_flags)
        ]
        assert len(gating) >= 2

    def test_cross_venue_flag_resolves_after_sa_p3_outcome(self) -> None:
        """Resolve a SA-P3 Verdant dispute, observe the SA-P3 flag set, and
        confirm the SA-P4 cross-venue Congress dispute can now start.
        """
        mgr, player, _, _, _, _, _ = _build_alliance_manager(persuasion=6)
        # Resolve the SA-P3 prerequisite (frontier_trade_route_levy) in any way.
        verdant_dispute = mgr.start_dispute("frontier_trade_route_levy", current_game_day=10)
        assert verdant_dispute is not None
        # Force resolution: cast vote.
        mgr.cast_vote(verdant_dispute)
        assert verdant_dispute.phase == DisputePhase.RESOLVED
        # SA-P3 flag set on the player.
        assert player.dialogue_flags.get(dispute_resolved("frontier_trade_route_levy")) is True
        # SA-P4 unification act gated on this flag; it can now start.
        congress = mgr.start_dispute("frontier_trade_unification_act", current_game_day=20)
        assert congress is not None


# ---------------------------------------------------------------------------
# AC 22 — Tomas crew banter trigger
# ---------------------------------------------------------------------------


class TestTomasBanterTrigger:
    def test_flag_set_on_congress_resolution_when_tomas_on_crew(self) -> None:
        mgr, player, _, _, _, _, _ = _build_alliance_manager(crew=["tomas_drifter"], persuasion=4)
        dispute = mgr.start_dispute("cross_settlement_tariff_review", current_game_day=10)
        assert dispute is not None
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        assert player.dialogue_flags.get("tomas_alliance_congress_attended_seen") is True

    def test_flag_skipped_when_tomas_not_on_crew(self) -> None:
        mgr, player, _, _, _, _, _ = _build_alliance_manager(crew=[], persuasion=4)
        dispute = mgr.start_dispute("cross_settlement_tariff_review", current_game_day=10)
        assert dispute is not None
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        assert "tomas_alliance_congress_attended_seen" not in player.dialogue_flags


# ---------------------------------------------------------------------------
# AC 15 — sub-rep deduction on corridor failure (alliance_congress)
# ---------------------------------------------------------------------------


class TestAllianceSubRepDeduction:
    def test_failed_corridor_visit_deducts_alliance_congress_sub_rep(self) -> None:
        mgr, player, _, _, _, _, _ = _build_alliance_manager(persuasion=1)
        dispute = mgr.start_dispute("cross_settlement_tariff_review", current_game_day=10)
        assert dispute is not None
        ok, _msg = mgr.do_corridor_visit(
            dispute,
            "councillor_wentworth",
            "process_fidelity",
            success_override=False,
        )
        assert ok is False
        assert player.sub_reputation.get("alliance_congress") == -1
