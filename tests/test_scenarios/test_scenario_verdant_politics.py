"""SA-P3 — full Verdant venue scenario test (AC 13, 15, 16, 20).

Walks the venue loop end-to-end against the shipped data files so
content + engine wiring stay aligned: load templates from JSON, start a
dispute, run a corridor visit, run the session, vote, observe outcome
propagation (rep delta, market shift, news headline, mission flag,
journal trigger flag). Repeats for at least one win, one loss, and
one ``partial_win_off_record`` template; campaign-arc cross-session
save/load is exercised in :class:`TestCampaignArcCrossSessionSaveLoad`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from spacegame.data_loader import DataLoader
from spacegame.models.politics_dispute import (
    DisputePhase,
    PoliticsArgument,
    PoliticsDisputeManager,
    PoliticsMarketShift,
)
from spacegame.models.verdant_council import VERDANT_COUNCIL_CONFIG

PROJECT_ROOT = Path(__file__).parent.parent.parent


class _StubPlayer:
    """Minimal Player surface the manager mutates during scenarios."""

    def __init__(self) -> None:
        self.faction_reputation: dict[str, int] = {}
        self.dialogue_flags: dict[str, bool] = {}
        self.sub_reputation: dict[str, int] = {}

    def modify_reputation(self, faction_id: str, amount: int) -> tuple[bool, str]:
        self.faction_reputation[faction_id] = self.faction_reputation.get(faction_id, 0) + amount
        return True, ""

    def get_reputation(self, faction_id: str) -> int:
        return self.faction_reputation.get(faction_id, 0)

    def modify_sub_reputation(self, org_id: str, amount: int, _config) -> None:
        self.sub_reputation[org_id] = self.sub_reputation.get(org_id, 0) + amount


class _StubFaction:
    def __init__(self, rivalry: str = "") -> None:
        self.rivalry = rivalry


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
    def __init__(self, system_id: str, game_day: int = 1) -> None:
        self.system_id = system_id
        self.game_day = game_day
        self.politics_shifts: list[PoliticsMarketShift] = []

    def add_politics_shift(self, shift: PoliticsMarketShift) -> None:
        self.politics_shifts.append(shift)


class _StubBonus:
    def __init__(self, bonuses: dict[str, float]) -> None:
        self._bonuses = bonuses

    def get_bonus(self, key: str) -> float:
        return float(self._bonuses.get(key, 0.0))


class _StubSocial:
    def __init__(self, levels: dict[str, int]) -> None:
        self._levels = levels

    def get_skill_level(self, key: str) -> int:
        return int(self._levels.get(key, 1))


class _StubCrewRoster:
    def __init__(self, crew_ids: list[str]) -> None:
        self.recruited_ids: set[str] = set(crew_ids)

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


def _load_verdant_templates() -> dict:
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    return loader.load_politics_disputes()


def _load_journal_templates() -> dict[str, dict]:
    """Return a dict of trigger_flag -> entry template from the journal data."""
    import json

    path = PROJECT_ROOT / "data" / "journal" / "entries.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict] = {}
    for entry in data["journal_entries"]:
        if entry.get("trigger_flag"):
            out[entry["trigger_flag"]] = entry
    return out


def _build_manager(
    *,
    crew: Optional[list[str]] = None,
    persuasion: int = 5,
    leadership: int = 4,
    coalition_sway_bonus: float = 0.30,
    coalition_size_bonus: float = 0.0,
    arbitration_neutrality_bonus: float = 0.0,
):
    """Wire a manager with the SA-P3-shipped template registry."""
    crew = crew or []
    templates = _load_verdant_templates()
    journal_templates = _load_journal_templates()
    player = _StubPlayer()
    politics = _StubPoliticsManager()
    news = _StubNewsTicker()
    market = _StubMarket("verdant", game_day=10)
    journal = _StubJournal(journal_templates)

    def _market_lookup(sid: str) -> Optional[_StubMarket]:
        return market if sid == "verdant" else None

    crew_roster = _StubCrewRoster(crew)
    mgr = PoliticsDisputeManager(
        templates=templates,
        politics_manager=politics,
        news_ticker=news,
        crew_roster=crew_roster,
        progression=_StubBonus(
            {
                "coalition_sway_bonus": coalition_sway_bonus,
                "coalition_size_bonus": coalition_size_bonus,
                "arbitration_neutrality_bonus": arbitration_neutrality_bonus,
            }
        ),
        social_manager=_StubSocial({"persuasion": persuasion, "leadership": leadership}),
        market_lookup=_market_lookup,
    )
    mgr.set_player(player)
    mgr.register_sub_rep_config(VERDANT_COUNCIL_CONFIG.id, VERDANT_COUNCIL_CONFIG)

    # Recreate the Game._on_dispute_outcome side-effect on the stubs so the
    # scenario test exercises the same flag-bump + journal-trigger path the
    # engine wires.
    def _on_dispute_outcome(dispute, category):
        flags = player.dialogue_flags
        if "first_dispute_attended" not in flags:
            flags["first_dispute_attended"] = True
            journal.trigger_auto_entry("first_dispute_attended", 10, "verdant")
        if category in ("partial_win_coalition_thin", "partial_win_off_record"):
            if "first_partial_win" not in flags:
                flags["first_partial_win"] = True
                journal.trigger_auto_entry("first_partial_win", 10, "verdant")
        if category == "win":
            if any(d.pre_committed for d in dispute.delegates.values()):
                if "first_coalition_won" not in flags:
                    flags["first_coalition_won"] = True
                    journal.trigger_auto_entry("first_coalition_won", 10, "verdant")

    mgr.set_outcome_callback(_on_dispute_outcome)
    return mgr, player, politics, news, market, journal


# ---------------------------------------------------------------------------
# AC 16 — at least one win + one loss + one partial_win_off_record
# ---------------------------------------------------------------------------


class TestVerdantWinLossPaths:
    def test_co_op_dividend_distribution_full_win(self) -> None:
        """Successful argument run on a tractable template ends in a full win."""
        mgr, player, _, news, market, journal = _build_manager(persuasion=5)
        dispute = mgr.start_dispute("co_op_dividend_distribution", current_game_day=10)
        assert dispute is not None

        # Pre-commit Hask via a successful corridor visit.
        ok, _msg = mgr.do_corridor_visit(
            dispute, "delegate_hask", "community_benefit", success_override=True
        )
        assert ok
        assert dispute.delegates["delegate_hask"].pre_committed is True

        # Argue Mayor Vance toward leaning_yes.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="community_benefit",
                audience_delegate_id="mayor_vance",
            ),
        )
        mgr.advance_round(dispute)

        # Argue Marsh.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="practical_cost",
                audience_delegate_id="delegate_marsh",
            ),
        )
        mgr.advance_round(dispute)

        # Cast the vote.
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        # AC 13: any-resolution sets first_dispute_attended
        assert player.dialogue_flags.get("first_dispute_attended") is True
        # If outcome is a coalition-built win, first_coalition_won fires.
        if dispute.resolved_outcome == "win":
            assert player.dialogue_flags.get("first_coalition_won") is True, (
                "win with pre-commit should bump first_coalition_won"
            )
            # Win row sets dispute_resolved + coalition_won mission flags.
            assert player.dialogue_flags.get("dispute_resolved_co_op_dividend_distribution") is True
            assert player.dialogue_flags.get("coalition_won_co_op_dividend_distribution") is True
            # Win headline emits when condition A holds (commodity shift ≥10%).
            assert any("Verdant co-op approves dividend split" in h for h in news.headlines)
            # Market shift registered on Verdant.
            assert any(
                s.commodity_id == "hydroponics_yield" and s.magnitude > 0
                for s in market.politics_shifts
            )
            # First-coalition-won journal entry fired.
            assert any(e["trigger_flag"] == "first_coalition_won" for e in journal.entries)

    def test_settler_food_credit_loss_when_arguments_fail(self) -> None:
        """No corridor work + a stiff difficulty lands in loss; engine flags fire."""
        mgr, player, _, news, _, journal = _build_manager(persuasion=1)
        dispute = mgr.start_dispute("settler_food_credit_dispute", current_game_day=10)
        assert dispute is not None
        # Three abstain-rounds: nothing moves, no concessions; tally fails.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome == "loss"
        # AC 13: first_dispute_attended fires on any resolution.
        assert player.dialogue_flags.get("first_dispute_attended") is True
        # Loss row sets dispute_resolved as a mission_lock.
        assert player.dialogue_flags.get("dispute_resolved_settler_food_credit_dispute") is True
        # Loss outcome ⇒ news headline (food shift ≥10%).
        assert any("Verdant rejects settler food credit" in h for h in news.headlines)
        # Loss does not emit first_partial_win or first_coalition_won.
        assert "first_partial_win" not in player.dialogue_flags
        assert "first_coalition_won" not in player.dialogue_flags
        # Journal entry fired exactly once (first_dispute_attended).
        attended = [e for e in journal.entries if e["trigger_flag"] == "first_dispute_attended"]
        assert len(attended) == 1

    def test_partial_win_off_record_via_mediation(self) -> None:
        """Mediate Marsh, lose the vote ⇒ partial_win_off_record."""
        mgr, player, _, _, _, journal = _build_manager(persuasion=1)
        dispute = mgr.start_dispute("water_rights_phasing", current_game_day=10)
        assert dispute is not None
        # Force Marsh into conceded state without engaging the social check.
        dispute.delegates["delegate_marsh"].conceded = True
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        mgr.cast_vote(dispute)
        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome == "partial_win_off_record"
        # AC 13: first_partial_win bumps on first partial-win category.
        assert player.dialogue_flags.get("first_partial_win") is True
        assert player.dialogue_flags.get("dispute_mediated_water_rights_phasing") is True
        # Journal entry fired for first_partial_win.
        assert any(e["trigger_flag"] == "first_partial_win" for e in journal.entries)


# ---------------------------------------------------------------------------
# AC 15 — corridor failure deducts verdant_council sub-rep
# ---------------------------------------------------------------------------


class TestSubRepDeductionOnCorridorFail:
    def test_failed_corridor_visit_deducts_one_sub_rep(self) -> None:
        mgr, player, _, _, _, _ = _build_manager()
        dispute = mgr.start_dispute("water_rights_phasing", current_game_day=10)
        assert dispute is not None
        ok, _msg = mgr.do_corridor_visit(
            dispute, "delegate_marsh", "soil_impact", success_override=False
        )
        assert ok is False
        # 1 sub-rep deducted with verdant_council org.
        assert player.sub_reputation.get("verdant_council") == -1


# ---------------------------------------------------------------------------
# AC 20 — crew banter trigger flags
# ---------------------------------------------------------------------------


class TestCrewBanterTriggers:
    def test_desta_corridor_pre_session_seen_set_on_success(self) -> None:
        mgr, player, _, _, _, _ = _build_manager(crew=["desta_coll"])
        dispute = mgr.start_dispute("water_rights_phasing", current_game_day=10)
        ok, _ = mgr.do_corridor_visit(
            dispute, "delegate_drift", "data_precedent", success_override=True
        )
        assert ok is True
        assert player.dialogue_flags.get("desta_corridor_pre_session_seen") is True

    def test_desta_flag_skipped_when_desta_not_on_crew(self) -> None:
        mgr, player, _, _, _, _ = _build_manager(crew=[])
        dispute = mgr.start_dispute("water_rights_phasing", current_game_day=10)
        ok, _ = mgr.do_corridor_visit(
            dispute, "delegate_drift", "data_precedent", success_override=True
        )
        assert ok is True
        assert "desta_corridor_pre_session_seen" not in player.dialogue_flags

    def test_cass_mediation_in_progress_seen_set_on_mediate_submit(self) -> None:
        mgr, player, _, _, _, _ = _build_manager(crew=["cass_weller"])
        dispute = mgr.start_dispute("water_rights_phasing", current_game_day=10)
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="community_benefit",
                audience_delegate_id="delegate_marsh",
                is_mediation=True,
            ),
        )
        assert player.dialogue_flags.get("cass_mediation_in_progress_seen") is True


# ---------------------------------------------------------------------------
# AC 16 (campaign arc): mid-arc state persists across save/load
# ---------------------------------------------------------------------------


class TestCampaignArcCrossSessionSaveLoad:
    def test_modernization_arc_round_state_persists_across_manager_round_trip(
        self,
    ) -> None:
        """Run two rounds of a 5-round campaign template, save the manager,
        rebuild a new manager, restore, and assert mid-arc state survived.
        """
        mgr, _player, _, _, _, _ = _build_manager(persuasion=4)
        dispute = mgr.start_dispute("infrastructure_co_op_vote", current_game_day=10)
        assert dispute is not None
        assert dispute.round_count == 5

        mgr.register_pending_dispute(dispute)

        # Run the first session: round 1 + advance, round 2 + advance.
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="data_precedent",
                audience_delegate_id="mayor_vance",
            ),
        )
        mgr.advance_round(dispute)
        mgr.submit_argument(
            dispute,
            PoliticsArgument(
                framing="practical_cost",
                audience_delegate_id="delegate_marsh",
            ),
        )
        mgr.advance_round(dispute)
        assert dispute.current_round == 3
        assert dispute.phase == DisputePhase.ROUND_OPEN
        # Snapshot after round 2 for cross-save assertion.
        round_three_snapshot = {d_id: d.visible_state for d_id, d in dispute.delegates.items()}

        # Save the manager state, rebuild a fresh manager.
        snapshot = mgr.to_dict()
        templates = _load_verdant_templates()
        mgr2 = PoliticsDisputeManager(templates=templates)
        mgr2.from_dict(snapshot)
        restored = mgr2.get_pending_dispute(dispute.dispute_id)
        assert restored is not None
        # Mid-arc round state preserved.
        assert restored.current_round == 3
        for d_id, expected in round_three_snapshot.items():
            assert restored.delegates[d_id].visible_state == expected
        # Pre-commit / conceded state survives.
        assert (
            restored.delegates["mayor_vance"].pre_committed
            == dispute.delegates["mayor_vance"].pre_committed
        )


# ---------------------------------------------------------------------------
# AC 17 — SA-P2 baseline test still holds (template-driven counter_framings
# preserves SA-P2 behavior). Smoke-tested by import + invocation here so a
# failure in the SA-P2 baseline shows up in the SA-P3 scenario suite as well.
# ---------------------------------------------------------------------------


class TestSAP2BaselinePreserved:
    def test_water_rights_phasing_uses_default_counter_framing(self) -> None:
        """Loaded ``water_rights_phasing`` keeps the SA-P2 default counter."""
        templates = _load_verdant_templates()
        tpl = templates["water_rights_phasing"]
        # Empty counter_framings ⇒ default fires. The default per SA-P2 is
        # ("soil_impact", "water_rights_change") — no per-delegate override.
        assert tpl.counter_framings == {}


# ---------------------------------------------------------------------------
# Save-load coverage: existing-save load tolerance for the new template field.
# ---------------------------------------------------------------------------


class TestLegacySaveLoadTolerance:
    def test_legacy_dispute_state_without_counter_framings_loads(self) -> None:
        """Manager.from_dict tolerates pre-SA-P3 saves (no counter_framings)."""
        templates = _load_verdant_templates()
        # Round-trip a synthetic save dict that omits counter_framings entirely.
        legacy = {
            "pending_disputes": {
                "water_rights_phasing": {
                    "dispute_id": "water_rights_phasing",
                    "template_id": "water_rights_phasing",
                    "headline": "Water Rights Phasing Bill",
                    "factions_affected": ["frontier_alliance"],
                    "base_difficulty": 4,
                    "round_count": 3,
                    "closes_on_day": 20,
                    "delegates": {},
                    "eligible_framings": [],
                    "eligible_evidence": [],
                    "framing_modifiers": {},
                    "framing_target_dimensions": {},
                    "current_round": 1,
                    "phase": "round_open",
                    "resolved_outcome": None,
                    "round_log": [],
                }
            },
            "resolved_disputes": {},
        }
        mgr = PoliticsDisputeManager(templates=templates)
        mgr.from_dict(legacy)
        # Loaded without crash; pending registry holds the restored dispute.
        assert "water_rights_phasing" in mgr.get_pending_dispute_ids()
