"""A2-4B compliance test: wired/gap partition covers every investment_from tag.

Enforces AC1: every tag in the union of investment_from across all lenses is
either wired (emitted from real production code) or explicitly gap-flagged with
a rationale line and a future-sprint pointer.

The grep-hit test catches "emitter site accidentally removed" drift without
requiring any mock or fake.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from spacegame.data_loader import get_data_loader

# ---------------------------------------------------------------------------
# Partition manifest
# ---------------------------------------------------------------------------

# Tags wired in A2-4B (real production emitters exist; see audit table in
# ROADMAP.md sprint A2-4B for exact file:line pointers).
WIRED_TAGS: set[str] = {
    "combat_victory_named_target",
    "mission_completed:bounty",
    "sold_cargo",
    "trade_profit_large",
    "auction_won",
    "politics_vote_won",
    "reach_system_first_visit",
    "wreckers_guild_contract_completed",
    "deep_shafts_pilgrimage_visited",
    "okafor_research_project_funded",
    "okafor_research_project_funded:high_risk",
    "mission_completed:smuggling",
    "black_market_sale",
    "crew_loyalty_gained",
}

# Tags gap-flagged: the gameplay system that would emit them does not yet exist.
# Each entry: {"rationale": str, "future_sprint": str}
GAP_TAGS: dict[str, dict[str, str]] = {
    "investment_tier_purchased": {
        "rationale": "No player-facing investment tier purchase system exists.",
        "future_sprint": "Financial-Systems / SA-F sprint",
    },
    "politics_favor_granted": {
        "rationale": "No favor-granting mechanic in the politics system.",
        "future_sprint": "Future SA-P sprint",
    },
    "council_seat_won": {
        "rationale": "No council seat mechanic.",
        "future_sprint": "Future SA-P scope",
    },
    "deep_scan_completed": {
        "rationale": "deep_scan is a skill bonus_type, not a completable event.",
        "future_sprint": "Future exploration-mini-game sprint",
    },
    "encounter_anomaly_resolved": {
        "rationale": "Anomaly encounters have no discrete resolved event.",
        "future_sprint": "Future encounter-authoring sprint",
    },
    "journal_entry:discovery": {
        "rationale": "JournalEntry.tag valid values are {people, places, suspicions, goals}; no discovery category.",
        "future_sprint": "Future journal-taxonomy sprint",
    },
    "mission_completed:bounty_lawful": {
        "rationale": "Missions have no lawful/unlawful discriminator.",
        "future_sprint": "Future mission-metadata sprint",
    },
    "politics_dispute_resolved_lawful": {
        "rationale": "Dispute categories do not include lawful/uprising/annex taxonomy.",
        "future_sprint": "Future dispute-taxonomy sprint",
    },
    "politics_dispute_resolved_uprising": {
        "rationale": "See politics_dispute_resolved_lawful.",
        "future_sprint": "Future dispute-taxonomy sprint",
    },
    "faction_reputation_up:frontier_alliance_labor": {
        "rationale": "No frontier_alliance_labor sub-faction exists.",
        "future_sprint": "Future faction-decomposition sprint",
    },
    "territory_investment_purchased": {
        "rationale": "No territory purchasing mechanic.",
        "future_sprint": "Future Empire arc sprint",
    },
    "politics_dispute_resolved_annex": {
        "rationale": "See politics_dispute_resolved_lawful.",
        "future_sprint": "Future dispute-taxonomy sprint",
    },
    "investment_tier_purchased:community": {
        "rationale": "See investment_tier_purchased.",
        "future_sprint": "Financial-Systems / SA-F sprint",
    },
    "wreckers_guild_contract_completed:preservation": {
        "rationale": "Wreckers contract templates lack a preservation flag.",
        "future_sprint": "Future contract-metadata sprint",
    },
    "institution_founded": {
        "rationale": "No institution-founding mechanic.",
        "future_sprint": "Future Legacy arc sprint",
    },
    "dialogue_completed:faith": {
        "rationale": "Dialogue system has no per-completion tag-emit.",
        "future_sprint": "Future dialogue-taxonomy sprint",
    },
    "ship_upgrade_installed:experimental": {
        "rationale": "No experimental upgrade class in models/upgrades.py.",
        "future_sprint": "Future Transcendence arc sprint",
    },
    "dialogue_completed:crew_personal": {
        "rationale": "See dialogue_completed:faith.",
        "future_sprint": "Future dialogue-taxonomy sprint",
    },
    "investigation_flag_set": {
        "rationale": "No unified investigation-flag concept; individual flags are set ad hoc.",
        "future_sprint": "Future Truth arc sprint",
    },
    "dialogue_completed:evidence": {
        "rationale": "See dialogue_completed:faith.",
        "future_sprint": "Future dialogue-taxonomy sprint",
    },
}

_REPO_ROOT = Path(__file__).parent.parent.parent
_SPACEGAME_SRC = _REPO_ROOT / "spacegame"


class TestGapManifest:
    def _all_tags(self) -> set[str]:
        dl = get_data_loader()
        dl.load_all()
        tags: set[str] = set()
        for lens in dl.lenses.values():
            tags.update(lens.investment_from)
        return tags

    def test_wired_and_gap_partition_covers_every_tag(self) -> None:
        """WIRED_TAGS ∪ GAP_TAGS == all investment_from tags, no tag missing."""
        all_tags = self._all_tags()
        manifest_tags = WIRED_TAGS | set(GAP_TAGS.keys())
        missing = all_tags - manifest_tags
        extra = manifest_tags - all_tags
        assert not missing, f"Tags in lenses.json not in manifest: {sorted(missing)}"
        assert not extra, f"Tags in manifest not in lenses.json: {sorted(extra)}"

    def test_no_wired_tag_is_also_in_gap_manifest(self) -> None:
        """WIRED_TAGS and GAP_TAGS are disjoint."""
        overlap = WIRED_TAGS & set(GAP_TAGS.keys())
        assert not overlap, f"Tags appear in both WIRED and GAP: {sorted(overlap)}"

    def test_every_gap_tag_has_a_rationale_and_pointer(self) -> None:
        """Each gap entry has non-empty rationale and future_sprint strings."""
        for tag, entry in GAP_TAGS.items():
            assert entry.get("rationale"), f"Gap tag '{tag}' missing rationale"
            assert entry.get("future_sprint"), f"Gap tag '{tag}' missing future_sprint"

    def test_every_wired_tag_has_a_grep_hit_in_production_code(self) -> None:
        """Each wired tag appears in a production emit call outside lens_investment.py."""
        for tag in WIRED_TAGS:
            result = subprocess.run(
                ["grep", "-r", "--include=*.py", tag, str(_SPACEGAME_SRC)],
                capture_output=True,
                text=True,
            )
            hits = [
                line
                for line in result.stdout.splitlines()
                if "lens_investment.py" not in line and "lens_investment" not in line
            ]
            assert hits, (
                f"Wired tag '{tag}' has no grep hit in spacegame/ outside lens_investment.py. "
                f"Either the emitter was removed or the tag was mistyped."
            )
