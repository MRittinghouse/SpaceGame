"""Tests for crew personal quest data and gating."""

from spacegame.data_loader import DataLoader
from spacegame.models.crew import CrewRoster, LoyaltyTier


def _load_all() -> DataLoader:
    """Load all game data for testing."""
    loader = DataLoader()
    loader.load_all()
    return loader


class TestCrewQuestDataLoading:
    """Tests that crew quest data files parse correctly."""

    def test_crew_quests_loaded(self) -> None:
        """All 12 crew quest missions should load."""
        loader = _load_all()
        crew_missions = [m for m in loader.missions if m.mission_type == "crew"]
        assert len(crew_missions) == 12, f"Expected 12 crew quests, got {len(crew_missions)}"

    def test_each_crew_member_has_3_quests(self) -> None:
        """Each of the 4 crew members should have exactly 3 quest stages."""
        loader = _load_all()
        crew_missions = [m for m in loader.missions if m.mission_type == "crew"]
        prefixes = ["elena_", "marcus_", "priya_", "tomas_"]
        for prefix in prefixes:
            quests = [m for m in crew_missions if m.id.startswith(prefix)]
            assert len(quests) == 3, (
                f"Expected 3 quests for {prefix}, got {len(quests)}: {[m.id for m in quests]}"
            )

    def test_stage1_quests_require_loyalty_50_flag(self) -> None:
        """Stage 1 quests should require the loyalty 50 threshold flag."""
        loader = _load_all()
        stage1_ids = [
            "elena_old_charts",
            "marcus_old_debts",
            "priya_retracted_paper",
            "tomas_name_from_past",
        ]
        for mission_id in stage1_ids:
            mission = next(m for m in loader.missions if m.id == mission_id)
            loyalty_flags = [f for f in mission.required_flags if "loyalty" in f]
            assert len(loyalty_flags) >= 1, f"{mission_id} should require a loyalty flag"
            assert any("_50" in f for f in loyalty_flags), (
                f"{mission_id} should require loyalty 50 flag"
            )

    def test_stage2_quests_require_stage1_complete(self) -> None:
        """Stage 2 quests should require the stage 1 completion flag."""
        loader = _load_all()
        stage2_pairs = [
            ("elena_wreck_meridian", "elena_quest_stage1_complete"),
            ("marcus_the_inspector", "marcus_quest_stage1_complete"),
            ("priya_peer_review", "priya_quest_stage1_complete"),
            ("tomas_fulcrum_job", "tomas_quest_stage1_complete"),
        ]
        for mission_id, required_flag in stage2_pairs:
            mission = next(m for m in loader.missions if m.id == mission_id)
            assert required_flag in mission.required_flags, (
                f"{mission_id} should require {required_flag}"
            )

    def test_stage3_quests_require_stage2_complete_and_loyalty_85(self) -> None:
        """Stage 3 quests should require stage 2 complete and loyalty 85 flag."""
        loader = _load_all()
        stage3_pairs = [
            ("elena_charting_stars", "elena_quest_stage2_complete", "_85"),
            ("marcus_steel_holds", "marcus_quest_stage2_complete", "_85"),
            ("priya_the_theorem", "priya_quest_stage2_complete", "_85"),
            ("tomas_new_ledger", "tomas_quest_stage2_complete", "_85"),
        ]
        for mission_id, stage2_flag, loyalty_suffix in stage3_pairs:
            mission = next(m for m in loader.missions if m.id == mission_id)
            assert stage2_flag in mission.required_flags, (
                f"{mission_id} should require {stage2_flag}"
            )
            loyalty_flags = [f for f in mission.required_flags if loyalty_suffix in f]
            assert len(loyalty_flags) >= 1, f"{mission_id} should require loyalty 85 flag"

    def test_quest_completion_sets_stage_flags(self) -> None:
        """Each quest stage should set a completion flag as reward."""
        loader = _load_all()
        expected_flags = [
            ("elena_old_charts", "elena_quest_stage1_complete"),
            ("elena_wreck_meridian", "elena_quest_stage2_complete"),
            ("elena_charting_stars", "elena_quest_stage3_complete"),
            ("marcus_old_debts", "marcus_quest_stage1_complete"),
            ("marcus_the_inspector", "marcus_quest_stage2_complete"),
            ("marcus_steel_holds", "marcus_quest_stage3_complete"),
            ("priya_retracted_paper", "priya_quest_stage1_complete"),
            ("priya_peer_review", "priya_quest_stage2_complete"),
            ("priya_the_theorem", "priya_quest_stage3_complete"),
            ("tomas_name_from_past", "tomas_quest_stage1_complete"),
            ("tomas_fulcrum_job", "tomas_quest_stage2_complete"),
            ("tomas_new_ledger", "tomas_quest_stage3_complete"),
        ]
        for mission_id, flag in expected_flags:
            mission = next(m for m in loader.missions if m.id == mission_id)
            flag_rewards = [
                r for r in mission.rewards if r.reward_type == "set_flag" and r.target_id == flag
            ]
            assert len(flag_rewards) == 1, f"{mission_id} should set flag {flag}"


class TestCrewQuestDialogueLoading:
    """Tests that crew quest dialogue trees parse correctly."""

    def test_crew_quest_dialogues_loaded(self) -> None:
        """All crew quest dialogue trees should load."""
        loader = _load_all()
        crew_dialogue_ids = [
            "elena_old_charts_dialogue",
            "elena_archives_dialogue",
            "elena_wreck_dialogue",
            "elena_charting_dialogue",
            "marcus_old_debts_dialogue",
            "marcus_evidence_dialogue",
            "marcus_inspector_dialogue",
            "marcus_confrontation_dialogue",
            "priya_retracted_paper_dialogue",
            "priya_paper_dialogue",
            "priya_peer_review_dialogue",
            "priya_theorem_dialogue",
            "tomas_name_past_dialogue",
            "tomas_lead_dialogue",
            "tomas_fulcrum_dialogue",
            "tomas_new_ledger_dialogue",
        ]
        for dialogue_id in crew_dialogue_ids:
            assert dialogue_id in loader.dialogue_trees, f"Dialogue tree {dialogue_id} not loaded"

    def test_dialogue_trees_have_valid_start_nodes(self) -> None:
        """Each crew quest dialogue tree should have a reachable start node."""
        loader = _load_all()
        crew_prefixes = ["elena_", "marcus_", "priya_", "tomas_"]
        for tree_id, tree in loader.dialogue_trees.items():
            if any(tree_id.startswith(p) for p in crew_prefixes):
                start = tree.get_start_node()
                assert start is not None, f"Dialogue {tree_id} has no valid start node"

    def test_wreck_dialogue_has_moral_choice(self) -> None:
        """Elena's wreck dialogue should have a cargo vs logs choice."""
        loader = _load_all()
        tree = loader.dialogue_trees["elena_wreck_dialogue"]
        start = tree.get_start_node()
        assert start is not None
        # Should have at least 2 responses (cargo vs logs, possibly 'both')
        assert len(start.responses) >= 2

    def test_dialogue_crew_loyalty_changes_parsed(self) -> None:
        """Dialogue responses with crew_loyalty_changes should parse."""
        loader = _load_all()
        tree = loader.dialogue_trees["elena_wreck_dialogue"]
        # Find the logs choice response
        logs_node = tree.get_node("logs_choice")
        assert logs_node is not None
        # The response should have crew_loyalty_changes
        assert len(logs_node.responses) > 0
        response = logs_node.responses[0]
        assert "elena_reeves" in response.crew_loyalty_changes
        assert response.crew_loyalty_changes["elena_reeves"] == 10


class TestCrewQuestNPCs:
    """Tests that quest-related NPCs are loaded."""

    def test_quest_npcs_loaded(self) -> None:
        """Quest NPCs should be in the NPC registry."""
        loader = _load_all()
        quest_npc_ids = ["lira_feng", "amara_okonkwo", "ren_castillo"]
        for npc_id in quest_npc_ids:
            assert npc_id in loader.npcs, f"NPC {npc_id} not loaded"

    def test_lira_feng_at_forgeworks(self) -> None:
        """Lira Feng should be located at Forgeworks."""
        loader = _load_all()
        npc = loader.npcs["lira_feng"]
        assert npc.home_system_id == "forgeworks"

    def test_ren_castillo_at_fulcrum(self) -> None:
        """Ren Castillo should be located at The Fulcrum."""
        loader = _load_all()
        npc = loader.npcs["ren_castillo"]
        assert npc.home_system_id == "the_fulcrum"


class TestCrewTemplateNewFields:
    """Tests that crew templates load with faction_id and home_system_id."""

    def test_elena_faction_and_home(self) -> None:
        loader = _load_all()
        template = loader.crew_templates["elena_reeves"]
        assert template.faction_id == "commerce_guild"
        assert template.home_system_id == "stellaris_port"

    def test_marcus_faction_and_home(self) -> None:
        loader = _load_all()
        template = loader.crew_templates["marcus_jin"]
        assert template.faction_id == "industrial_union"
        assert template.home_system_id == "breakstone"

    def test_priya_faction_and_home(self) -> None:
        loader = _load_all()
        template = loader.crew_templates["dr_priya_osei"]
        assert template.faction_id == "science_collective"
        assert template.home_system_id == "axiom_labs"

    def test_tomas_faction_and_home(self) -> None:
        loader = _load_all()
        template = loader.crew_templates["tomas_drifter"]
        assert template.faction_id == "frontier_alliance"
        assert template.home_system_id == "havens_rest"
