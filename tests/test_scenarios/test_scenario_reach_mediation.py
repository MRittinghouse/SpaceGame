"""SA-P5 — full Crimson Reach mediation scenario test.

Walks the Wreckers' Guild arbitration venue end-to-end against the
shipped data files: load reach templates, start a dispute, resolve via
abstain / forced vote / forced-win paths, and verify the three SA-P5
first-time journal flags fire correctly.

SA-P5 flags under test:
  * ``first_reach_arbitration`` — any dispute resolution at Reach.
  * ``first_salvage_rights_concession`` — first partial_win_off_record outcome.
  * ``first_master_mediation_won`` — win outcome, master tier, resolved_via mediate.

Also: campaign-arc template (debris_field_territory_claim) round-count + save/load.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from spacegame.data_loader import DataLoader
from spacegame.models.politics_dispute import (
    DisputePhase,
    PoliticsDisputeManager,
    PoliticsMarketShift,
)
from spacegame.models.wreckers_guild import WRECKERS_GUILD_CONFIG

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Stubs (minimal surfaces the manager mutates during scenario runs)
# ---------------------------------------------------------------------------


class _StubPlayer:
    def __init__(self) -> None:
        self.faction_reputation: dict[str, int] = {}
        self.dialogue_flags: dict[str, bool] = {}
        self.sub_reputation: dict[str, int] = {}

    def modify_reputation(self, faction_id: str, amount: int) -> tuple[bool, str]:
        self.faction_reputation[faction_id] = self.faction_reputation.get(faction_id, 0) + amount
        return True, ""

    def get_reputation(self, faction_id: str) -> int:
        return self.faction_reputation.get(faction_id, 0)

    def modify_sub_reputation(self, org_id: str, amount: int, _config: object) -> None:
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
    def __init__(self) -> None:
        self.recruited_ids: set[str] = set()

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


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def _load_all_templates() -> dict:
    loader = DataLoader(data_dir=PROJECT_ROOT / "data")
    return loader.load_politics_disputes()


def _load_reach_templates() -> dict:
    """Return only templates whose delegates are all wreckers_guild sub-faction."""
    all_tpls = _load_all_templates()
    reach: dict = {}
    for tpl_id, tpl in all_tpls.items():
        if any(getattr(dt, "sub_faction_id", "") == "wreckers_guild" for dt in tpl.delegates):
            reach[tpl_id] = tpl
    return reach


def _load_journal_templates() -> dict[str, dict]:
    import json

    path = PROJECT_ROOT / "data" / "journal" / "entries.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict] = {}
    for entry in data["journal_entries"]:
        if entry.get("trigger_flag"):
            out[entry["trigger_flag"]] = entry
    return out


# ---------------------------------------------------------------------------
# Manager builder
# ---------------------------------------------------------------------------


def _build_manager(
    *,
    persuasion: int = 5,
    leadership: int = 4,
    coalition_sway_bonus: float = 0.30,
    master_tier: bool = False,
):
    """Wire a manager with the SA-P5 reach template registry."""
    templates = _load_reach_templates()
    journal_templates = _load_journal_templates()
    player = _StubPlayer()
    if master_tier:
        player.sub_reputation["wreckers_guild"] = 70
    politics = _StubPoliticsManager()
    news = _StubNewsTicker()
    market = _StubMarket("crimson_reach", game_day=10)
    journal = _StubJournal(journal_templates)

    def _market_lookup(sid: str) -> Optional[_StubMarket]:
        return market if sid == "crimson_reach" else None

    mgr = PoliticsDisputeManager(
        templates=templates,
        politics_manager=politics,
        news_ticker=news,
        crew_roster=_StubCrewRoster(),
        progression=_StubBonus(
            {
                "coalition_sway_bonus": coalition_sway_bonus,
                "coalition_size_bonus": 0.0,
                "arbitration_neutrality_bonus": 0.0,
            }
        ),
        social_manager=_StubSocial({"persuasion": persuasion, "leadership": leadership}),
        market_lookup=_market_lookup,
    )
    mgr.set_player(player)
    mgr.register_sub_rep_config(WRECKERS_GUILD_CONFIG.id, WRECKERS_GUILD_CONFIG)

    # Recreate the SA-P5-extended Game._on_dispute_outcome flag-bump logic so
    # the scenario test exercises the same path as the engine.
    def _on_dispute_outcome(dispute, category: str) -> None:
        from spacegame.models.wreckers_guild import current_tier_id

        flags = player.dialogue_flags
        # SA-P3 flags (any venue).
        if "first_dispute_attended" not in flags:
            flags["first_dispute_attended"] = True
            journal.trigger_auto_entry("first_dispute_attended", 10, "crimson_reach")
        # SA-P5 Reach flags.
        is_reach_dispute = any(
            d.sub_faction_id == "wreckers_guild" for d in dispute.delegates.values()
        )
        if is_reach_dispute:
            if "first_reach_arbitration" not in flags:
                flags["first_reach_arbitration"] = True
                journal.trigger_auto_entry("first_reach_arbitration", 10, "crimson_reach")
            if category == "partial_win_off_record":
                if "first_salvage_rights_concession" not in flags:
                    flags["first_salvage_rights_concession"] = True
                    journal.trigger_auto_entry(
                        "first_salvage_rights_concession", 10, "crimson_reach"
                    )
            if category == "win":
                player_tier = current_tier_id(player.sub_reputation)
                resolved_via_mediate = getattr(dispute, "resolved_via", None) == "mediate"
                if player_tier == "master" and resolved_via_mediate:
                    if "first_master_mediation_won" not in flags:
                        flags["first_master_mediation_won"] = True
                        journal.trigger_auto_entry(
                            "first_master_mediation_won", 10, "crimson_reach"
                        )

    mgr.set_outcome_callback(_on_dispute_outcome)
    return mgr, player, politics, news, market, journal


# ---------------------------------------------------------------------------
# SA-P5 first-time flags
# ---------------------------------------------------------------------------


class TestReachDisputeFlags:
    """SA-P5: first_reach_arbitration + first_salvage_rights_concession + first_master."""

    def test_any_resolution_fires_first_reach_arbitration(self) -> None:
        """Loss outcome fires first_reach_arbitration on first resolution."""
        mgr, player, _, _, _, journal = _build_manager()
        tpl_id = "salvage_rights_phasing"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        # Force a loss: all delegates in wavering (0 yes > 4 no is false), no conceded.
        for d in dispute.delegates.values():
            d.visible_state = "wavering"
            d.conceded = False
        mgr.cast_vote(dispute)

        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome == "loss"
        assert player.dialogue_flags.get("first_reach_arbitration") is True
        assert player.dialogue_flags.get("first_dispute_attended") is True
        # Journal entry fired for first_reach_arbitration.
        assert any(e["trigger_flag"] == "first_reach_arbitration" for e in journal.entries)

    def test_partial_win_off_record_fires_first_salvage_rights_concession(self) -> None:
        """partial_win_off_record emits first_salvage_rights_concession."""
        mgr, player, _, _, _, journal = _build_manager()
        tpl_id = "salvage_rights_phasing"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        # Force partial_win_off_record: vote fails (all wavering) + one conceded.
        delegates = list(dispute.delegates.values())
        for d in delegates:
            d.visible_state = "wavering"
            d.conceded = False
        delegates[0].conceded = True  # triggers partial_win_off_record
        mgr.cast_vote(dispute)

        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome == "partial_win_off_record"
        assert player.dialogue_flags.get("first_salvage_rights_concession") is True
        assert any(e["trigger_flag"] == "first_salvage_rights_concession" for e in journal.entries)

    def test_win_with_master_and_mediate_fires_first_master_mediation_won(self) -> None:
        """win outcome, master tier, resolved_via=mediate fires first_master_mediation_won."""
        mgr, player, _, _, _, journal = _build_manager(master_tier=True)
        tpl_id = "salvage_rights_phasing"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        # Force a win: all delegates committed_yes + pre_committed (ratio 1.0 ≥ 0.60).
        for d in dispute.delegates.values():
            d.visible_state = "committed_yes"
            d.pre_committed = True
        # Signal that mediation was the decisive move (duck-typed field, checked via getattr).
        dispute.resolved_via = "mediate"  # type: ignore[attr-defined]
        mgr.cast_vote(dispute)

        assert dispute.phase == DisputePhase.RESOLVED
        assert dispute.resolved_outcome == "win"
        assert player.dialogue_flags.get("first_master_mediation_won") is True
        assert any(e["trigger_flag"] == "first_master_mediation_won" for e in journal.entries)

    def test_win_without_master_tier_does_not_fire_first_master_mediation_won(self) -> None:
        """Master flag not emitted when player is below master tier."""
        mgr, player, _, _, _, _ = _build_manager(master_tier=False)
        # journeyman tier
        player.sub_reputation["wreckers_guild"] = 30
        tpl_id = "salvage_rights_phasing"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        for d in dispute.delegates.values():
            d.visible_state = "committed_yes"
            d.pre_committed = True
        dispute.resolved_via = "mediate"  # type: ignore[attr-defined]
        mgr.cast_vote(dispute)

        assert dispute.resolved_outcome == "win"
        assert "first_master_mediation_won" not in player.dialogue_flags

    def test_win_without_resolved_via_mediate_does_not_fire_master_flag(self) -> None:
        """Master flag not emitted when resolved_via is not 'mediate'."""
        mgr, player, _, _, _, _ = _build_manager(master_tier=True)
        tpl_id = "salvage_rights_phasing"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        for d in dispute.delegates.values():
            d.visible_state = "committed_yes"
            d.pre_committed = True
        # resolved_via NOT set → getattr returns None → flag must not fire
        mgr.cast_vote(dispute)

        assert dispute.resolved_outcome == "win"
        assert "first_master_mediation_won" not in player.dialogue_flags

    def test_first_reach_arbitration_is_idempotent(self) -> None:
        """Second resolution does not re-append the first_reach_arbitration journal entry."""
        mgr, player, _, _, _, journal = _build_manager()

        for i in range(2):
            tpl_id = "salvage_rights_phasing"
            dispute = mgr.start_dispute(tpl_id, current_game_day=10 + i)
            mgr.register_pending_dispute(dispute)
            for d in dispute.delegates.values():
                d.visible_state = "wavering"
                d.conceded = False
            mgr.cast_vote(dispute)

        assert player.dialogue_flags.get("first_reach_arbitration") is True
        entries = [e for e in journal.entries if e["trigger_flag"] == "first_reach_arbitration"]
        assert len(entries) == 1, "Journal entry must fire exactly once"


# ---------------------------------------------------------------------------
# Campaign-arc template
# ---------------------------------------------------------------------------


class TestCampaignArcTemplate:
    """SA-P5: debris_field_territory_claim is the campaign arc with 5 rounds."""

    def test_campaign_arc_template_exists_and_is_flagged(self) -> None:
        templates = _load_reach_templates()
        assert "debris_field_territory_claim" in templates, (
            "Campaign arc template must be in reach templates"
        )
        arc = templates["debris_field_territory_claim"]
        assert getattr(arc, "is_campaign_arc", False) is True
        assert arc.round_count == 5

    def test_campaign_arc_round_state_survives_save_load(self) -> None:
        """Round state serialises/deserialises so cross-session arcs persist."""
        mgr, _, _, _, _, _ = _build_manager()
        tpl_id = "debris_field_territory_claim"
        dispute = mgr.start_dispute(tpl_id, current_game_day=10)
        mgr.register_pending_dispute(dispute)

        # Advance two rounds via abstain.
        mgr.abstain_round(dispute)
        mgr.abstain_round(dispute)
        assert dispute.current_round == 3

        # Serialise manager state.
        saved = mgr.to_dict()

        # Reconstruct a fresh manager and restore.
        mgr2, _, _, _, _, _ = _build_manager()
        mgr2.from_dict(saved)

        # Pending dispute must survive and carry round 3.
        restored = mgr2.get_pending_dispute(tpl_id)
        assert restored is not None, "Pending dispute must survive save/load"
        assert restored.current_round == 3
