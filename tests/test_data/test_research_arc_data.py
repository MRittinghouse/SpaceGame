"""Data validation tests for SA-R2 Kweon legacy-arc content.

Checks that:
  - The okafor_legacy_clinic_run mission loads cleanly and its fields
    are consistent (valid system, valid flag gate, correct objective type).
  - All 6 Kweon legacy-arc dialogue trees are present in dialogues.json
    and each has at least one terminal node (next_node_id null).
  - The 4 SA-R2 journal entries are present in entries.json with correct
    system_id and trigger_flag values.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_DATA_ROOT = Path(__file__).parent.parent.parent / "data"

_ARC_DIALOGUE_TREE_IDS = [
    "kweon_legacy_first_heal",
    "kweon_legacy_first_profit",
    "kweon_legacy_heal_pattern",
    "kweon_legacy_profit_pattern",
    "kweon_legacy_heal_ending",
    "kweon_legacy_profit_ending",
]

_ARC_JOURNAL_ENTRIES = {
    "auto_okafor_legacy_first_heal": "okafor_legacy_first_heal_seen",
    "auto_okafor_legacy_first_profit": "okafor_legacy_first_profit_seen",
    "auto_okafor_legacy_heal_ending": "okafor_legacy_heal_ending_seen",
    "auto_okafor_legacy_profit_ending": "okafor_legacy_profit_ending_seen",
}


def _load_missions() -> list[dict]:
    from spacegame.data_loader import DataLoader

    loader = DataLoader(data_dir=_DATA_ROOT)
    loader.load_missions()
    return [m.__dict__ if hasattr(m, "__dict__") else m for m in loader.missions]


def _load_missions_raw() -> list[dict]:
    """Return all mission dicts directly from the data loader's Mission objects."""
    from spacegame.data_loader import DataLoader

    loader = DataLoader(data_dir=_DATA_ROOT)
    loader.load_missions()
    return loader.missions


def _load_dialogues_raw() -> dict[str, dict]:
    with open(_DATA_ROOT / "dialogue" / "dialogues.json", encoding="utf-8") as f:
        data = json.load(f)
    return {d["id"]: d for d in data["dialogues"]}


def _load_journal_raw() -> dict[str, dict]:
    with open(_DATA_ROOT / "journal" / "entries.json", encoding="utf-8") as f:
        data = json.load(f)
    return {e["entry_id"]: e for e in data["journal_entries"]}


# ---------------------------------------------------------------------------
# Mission: okafor_legacy_clinic_run
# ---------------------------------------------------------------------------


class TestClinicRunMission:
    """okafor_legacy_clinic_run loads correctly and is internally consistent."""

    def _get_mission(self):
        missions = _load_missions_raw()
        matches = [m for m in missions if m.id == "okafor_legacy_clinic_run"]
        assert matches, "okafor_legacy_clinic_run mission not found in loaded data"
        return matches[0]

    def test_mission_loads(self) -> None:
        self._get_mission()

    def test_mission_type_is_side(self) -> None:
        m = self._get_mission()
        assert m.mission_type == "side", f"expected mission_type=side, got {m.mission_type!r}"

    def test_available_at_is_axiom_labs(self) -> None:
        m = self._get_mission()
        assert "axiom_labs" in m.available_at, (
            f"mission not available at axiom_labs, got {m.available_at}"
        )

    def test_required_flag_is_heal_pattern(self) -> None:
        m = self._get_mission()
        assert "okafor_legacy_heal_pattern_seen" in m.required_flags, (
            f"mission should require okafor_legacy_heal_pattern_seen, got {m.required_flags}"
        )

    def test_objective_is_reach_system(self) -> None:
        m = self._get_mission()
        assert m.objectives, "mission has no objectives"
        obj = m.objectives[0]
        assert obj.type.value == "reach_system", (
            f"expected reach_system objective, got {obj.type.value!r}"
        )

    def test_objective_targets_havens_rest(self) -> None:
        m = self._get_mission()
        obj = m.objectives[0]
        assert obj.target_id == "havens_rest", f"expected havens_rest target, got {obj.target_id!r}"

    def test_rewards_include_credits_and_xp(self) -> None:
        m = self._get_mission()
        reward_types = {r.reward_type for r in m.rewards}
        assert "credits" in reward_types, "mission should reward credits"
        assert "xp" in reward_types, "mission should reward XP"

    def test_reward_sets_completion_flag(self) -> None:
        m = self._get_mission()
        flag_rewards = [r for r in m.rewards if r.reward_type == "set_flag"]
        flag_ids = [r.target_id for r in flag_rewards]
        assert "okafor_legacy_mission_completed" in flag_ids, (
            f"mission should set okafor_legacy_mission_completed, got {flag_ids}"
        )

    def test_auto_accept_is_true(self) -> None:
        m = self._get_mission()
        assert m.auto_accept is True, "clinic run mission should be auto-accept"

    def test_not_repeatable(self) -> None:
        m = self._get_mission()
        assert m.repeatable is False, "clinic run mission should not be repeatable"

    def test_credit_reward_amount(self) -> None:
        m = self._get_mission()
        credit_rewards = [r for r in m.rewards if r.reward_type == "credits"]
        assert credit_rewards, "no credit reward found"
        assert credit_rewards[0].amount == 8000, (
            f"expected 8000 credits, got {credit_rewards[0].amount}"
        )


# ---------------------------------------------------------------------------
# Dialogue trees: 6 Kweon arc beats
# ---------------------------------------------------------------------------


class TestKweonArcDialogueTrees:
    """All 6 arc-beat trees are present in dialogues.json."""

    @pytest.mark.parametrize("tree_id", _ARC_DIALOGUE_TREE_IDS)
    def test_tree_is_present(self, tree_id: str) -> None:
        dialogues = _load_dialogues_raw()
        assert tree_id in dialogues, f"dialogue tree {tree_id!r} not found in dialogues.json"

    @pytest.mark.parametrize("tree_id", _ARC_DIALOGUE_TREE_IDS)
    def test_tree_has_at_least_one_node(self, tree_id: str) -> None:
        dialogues = _load_dialogues_raw()
        tree = dialogues[tree_id]
        assert tree["nodes"], f"{tree_id!r} has no nodes"

    @pytest.mark.parametrize("tree_id", _ARC_DIALOGUE_TREE_IDS)
    def test_tree_has_terminal_node(self, tree_id: str) -> None:
        """Every tree must have at least one node that terminates the dialogue."""
        dialogues = _load_dialogues_raw()
        tree = dialogues[tree_id]
        nodes = tree["nodes"]

        # A terminal node is one where every response has next_node_id null
        # OR the node itself has no responses (leaf node).
        def is_terminal(node: dict) -> bool:
            responses = node.get("responses", [])
            if not responses:
                return True
            return all(r.get("next_node_id") is None for r in responses)

        terminal_nodes = [n for n in nodes if is_terminal(n)]
        assert terminal_nodes, (
            f"Dialogue tree {tree_id!r} has no terminal node — "
            "add a leaf node or a node where all responses have next_node_id=null"
        )

    @pytest.mark.parametrize("tree_id", _ARC_DIALOGUE_TREE_IDS)
    def test_tree_nodes_have_text(self, tree_id: str) -> None:
        dialogues = _load_dialogues_raw()
        tree = dialogues[tree_id]
        for node in tree["nodes"]:
            text = node.get("text", "").strip()
            assert text, f"Node {node['id']!r} in {tree_id!r} has empty text"

    def test_heal_pattern_tree_sets_mission_flag(self) -> None:
        """kweon_legacy_heal_pattern must set okafor_legacy_mission_offered."""
        dialogues = _load_dialogues_raw()
        tree = dialogues["kweon_legacy_heal_pattern"]
        flag_found = False
        for node in tree["nodes"]:
            if node.get("set_flag") == "okafor_legacy_mission_offered":
                flag_found = True
                break
            for resp in node.get("responses", []):
                if resp.get("set_flag") == "okafor_legacy_mission_offered":
                    flag_found = True
                    break
        assert flag_found, (
            "kweon_legacy_heal_pattern must set okafor_legacy_mission_offered "
            "on at least one node or response"
        )

    def test_profit_pattern_tree_does_not_set_mission_flag(self) -> None:
        """kweon_legacy_profit_pattern must NOT set okafor_legacy_mission_offered."""
        dialogues = _load_dialogues_raw()
        tree = dialogues["kweon_legacy_profit_pattern"]
        for node in tree["nodes"]:
            assert node.get("set_flag") != "okafor_legacy_mission_offered", (
                f"Node {node['id']!r} in kweon_legacy_profit_pattern incorrectly sets "
                "okafor_legacy_mission_offered"
            )
            for resp in node.get("responses", []):
                assert resp.get("set_flag") != "okafor_legacy_mission_offered", (
                    "kweon_legacy_profit_pattern response incorrectly sets "
                    "okafor_legacy_mission_offered"
                )


# ---------------------------------------------------------------------------
# Journal entries: 4 SA-R2 arc beats
# ---------------------------------------------------------------------------


class TestArcJournalEntries:
    """SA-R2 journal entries are present with correct trigger_flag values."""

    @pytest.mark.parametrize("entry_id,trigger_flag", _ARC_JOURNAL_ENTRIES.items())
    def test_entry_is_present(self, entry_id: str, trigger_flag: str) -> None:
        entries = _load_journal_raw()
        assert entry_id in entries, f"journal entry {entry_id!r} not found in entries.json"

    @pytest.mark.parametrize("entry_id,trigger_flag", _ARC_JOURNAL_ENTRIES.items())
    def test_entry_trigger_flag(self, entry_id: str, trigger_flag: str) -> None:
        entries = _load_journal_raw()
        entry = entries[entry_id]
        assert entry.get("trigger_flag") == trigger_flag, (
            f"journal entry {entry_id!r} has trigger_flag "
            f"{entry.get('trigger_flag')!r}, expected {trigger_flag!r}"
        )

    @pytest.mark.parametrize("entry_id,trigger_flag", _ARC_JOURNAL_ENTRIES.items())
    def test_entry_system_is_axiom_labs(self, entry_id: str, trigger_flag: str) -> None:
        entries = _load_journal_raw()
        entry = entries[entry_id]
        assert entry.get("system_id") == "axiom_labs", (
            f"journal entry {entry_id!r} should have system_id=axiom_labs, "
            f"got {entry.get('system_id')!r}"
        )

    @pytest.mark.parametrize("entry_id,trigger_flag", _ARC_JOURNAL_ENTRIES.items())
    def test_entry_has_body_text(self, entry_id: str, trigger_flag: str) -> None:
        entries = _load_journal_raw()
        entry = entries[entry_id]
        body = entry.get("text", "").strip()
        assert body, f"journal entry {entry_id!r} has empty text field"
