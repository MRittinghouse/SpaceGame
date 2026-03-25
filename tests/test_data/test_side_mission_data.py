"""Tests for side mission data loading and validation."""

from pathlib import Path

from spacegame.data_loader import DataLoader


VALID_SYSTEM_IDS = {
    "nexus_prime",
    "stellaris_port",
    "verdant",
    "havens_rest",
    "forgeworks",
    "axiom_labs",
    "nova_research",
    "breakstone",
    "iron_depths",
    "crimson_reach",
    "the_fulcrum",
}

VALID_FACTION_IDS = {
    "commerce_guild",
    "miners_union",
    "science_collective",
    "frontier_alliance",
}

VALID_OBJECTIVE_TYPES = {
    "reach_system",
    "talk_to_npc",
    "have_credits",
    "collect_cargo",
    "has_flag",
    "complete_trade",
    "win_combat",
}

VALID_REWARD_TYPES = {
    "credits",
    "xp",
    "set_flag",
    "modify_reputation",
    "remove_cargo",
    "deduct_credits",
    "trade_permit",
    "crew",
    "black_market_access",
    "reputation",
}

VALID_DISCOVERY_METHODS = {"npc", "station_board", "encounter", "automatic", ""}

VALID_MISSION_TYPES = {"campaign", "side", "crew"}

# Campaign mission IDs (for available_after validation)
CAMPAIGN_MISSION_IDS = {
    "bill_of_landing",
    "iron_delivery",
    "footing_the_bill",
    "union_territory",
    "the_foremans_son",
    "the_scholars_errand",
    "the_drifters_deal",
    "drifters_delivery",
    "recruit_navigator",
    "recruit_engineer",
    "recruit_scientist",
    "recruit_trader",
    "cargo_lost",
    "whispers_at_the_bar",
    "the_crimson_run",
    "embassy_visit",
    "under_fire",
    "the_favor_returned",
    "iron_depths_investigation",
    "the_ledger",
    "point_of_no_return",
    "the_collapse",
}


def _load():
    """Load all missions via DataLoader."""
    project_root = Path(__file__).parent.parent.parent
    loader = DataLoader(data_dir=project_root / "data")
    loader.load_missions()
    return loader.missions


def _load_side():
    """Load only side missions."""
    return [m for m in _load() if m.mission_type == "side"]


def _load_campaign():
    """Load only campaign missions."""
    return [m for m in _load() if m.mission_type == "campaign"]


class TestSideMissionDataLoading:
    """Tests that side missions load correctly from JSON."""

    def test_side_missions_load_without_error(self) -> None:
        """Side missions JSON loads successfully."""
        side = _load_side()
        assert side is not None

    def test_minimum_side_mission_count(self) -> None:
        """At least 20 side missions are loaded."""
        side = _load_side()
        assert len(side) >= 20, f"Expected >= 20 side missions, got {len(side)}"

    def test_campaign_missions_still_load(self) -> None:
        """Campaign missions still load alongside side missions."""
        campaign = _load_campaign()
        assert len(campaign) >= 22, f"Expected >= 22 campaign missions, got {len(campaign)}"

    def test_total_mission_count(self) -> None:
        """Total missions include both campaign and side."""
        all_missions = _load()
        assert len(all_missions) >= 42, f"Expected >= 42 total missions, got {len(all_missions)}"


class TestSideMissionIds:
    """Tests for mission ID uniqueness and validity."""

    def test_no_duplicate_ids(self) -> None:
        """All mission IDs are unique across campaign and side missions."""
        all_missions = _load()
        ids = [m.id for m in all_missions]
        duplicates = [mid for mid in ids if ids.count(mid) > 1]
        assert len(duplicates) == 0, f"Duplicate mission IDs: {set(duplicates)}"

    def test_all_ids_are_snake_case(self) -> None:
        """All side mission IDs use snake_case."""
        for m in _load_side():
            assert m.id == m.id.lower(), f"Mission ID '{m.id}' is not lowercase"
            assert " " not in m.id, f"Mission ID '{m.id}' contains spaces"

    def test_all_have_mission_type_side(self) -> None:
        """All side missions have mission_type='side'."""
        for m in _load_side():
            assert m.mission_type == "side", f"Side mission {m.id} has type '{m.mission_type}'"


class TestSideMissionFields:
    """Tests for side mission framework fields."""

    def test_all_have_available_after(self) -> None:
        """Every side mission has a valid available_after campaign gate."""
        for m in _load_side():
            if m.available_after:
                assert m.available_after in CAMPAIGN_MISSION_IDS, (
                    f"Side mission {m.id} has invalid available_after '{m.available_after}'"
                )

    def test_available_at_references_valid_systems(self) -> None:
        """All available_at values are valid system IDs."""
        for m in _load_side():
            for sys_id in m.available_at:
                assert sys_id in VALID_SYSTEM_IDS, (
                    f"Side mission {m.id} has invalid available_at system '{sys_id}'"
                )

    def test_discovery_method_valid(self) -> None:
        """All discovery methods are from the known set."""
        for m in _load_side():
            assert m.discovery_method in VALID_DISCOVERY_METHODS, (
                f"Side mission {m.id} has invalid discovery_method '{m.discovery_method}'"
            )

    def test_mission_type_valid(self) -> None:
        """All missions have a valid mission_type."""
        for m in _load():
            assert m.mission_type in VALID_MISSION_TYPES, (
                f"Mission {m.id} has invalid mission_type '{m.mission_type}'"
            )


class TestSideMissionObjectives:
    """Tests for side mission objectives."""

    def test_all_have_objectives(self) -> None:
        """Every side mission has at least one objective."""
        for m in _load_side():
            assert len(m.objectives) >= 1, f"Side mission {m.id} has no objectives"

    def test_objective_types_valid(self) -> None:
        """All objective types are from the known set."""
        for m in _load_side():
            for obj in m.objectives:
                assert obj.type.value in VALID_OBJECTIVE_TYPES, (
                    f"Side mission {m.id} has invalid objective type '{obj.type.value}'"
                )

    def test_reach_system_targets_valid(self) -> None:
        """All reach_system objectives reference valid system IDs."""
        for m in _load_side():
            for obj in m.objectives:
                if obj.type.value == "reach_system":
                    assert obj.target_id in VALID_SYSTEM_IDS, (
                        f"Side mission {m.id} objective targets invalid system '{obj.target_id}'"
                    )

    def test_objectives_have_descriptions(self) -> None:
        """All objectives have non-empty descriptions."""
        for m in _load_side():
            for obj in m.objectives:
                assert obj.description, f"Side mission {m.id} has objective without description"


class TestSideMissionRewards:
    """Tests for side mission rewards."""

    def test_all_have_rewards(self) -> None:
        """Every side mission has at least one reward."""
        for m in _load_side():
            assert len(m.rewards) >= 1, f"Side mission {m.id} has no rewards"

    def test_reward_types_valid(self) -> None:
        """All reward types are from the known set."""
        for m in _load_side():
            for r in m.rewards:
                assert r.reward_type in VALID_REWARD_TYPES, (
                    f"Side mission {m.id} has invalid reward type '{r.reward_type}'"
                )

    def test_modify_reputation_has_valid_faction(self) -> None:
        """All modify_reputation rewards reference valid factions."""
        for m in _load_side():
            for r in m.rewards:
                if r.reward_type == "modify_reputation":
                    assert r.target_id in VALID_FACTION_IDS, (
                        f"Side mission {m.id} reputation reward targets "
                        f"invalid faction '{r.target_id}'"
                    )

    def test_credit_rewards_reasonable(self) -> None:
        """Credit rewards are in a reasonable range for side missions."""
        for m in _load_side():
            for r in m.rewards:
                if r.reward_type == "credits":
                    assert 50 <= r.amount <= 1000, (
                        f"Side mission {m.id} has unusual credit reward of {r.amount}"
                    )

    def test_xp_rewards_reasonable(self) -> None:
        """XP rewards are in a reasonable range."""
        for m in _load_side():
            for r in m.rewards:
                if r.reward_type == "xp":
                    assert 20 <= r.amount <= 200, (
                        f"Side mission {m.id} has unusual XP reward of {r.amount}"
                    )


class TestSideMissionDistribution:
    """Tests for side mission coverage across systems."""

    def test_multiple_systems_covered(self) -> None:
        """Side missions cover at least 8 different systems."""
        systems = set()
        for m in _load_side():
            systems.update(m.available_at)
        assert len(systems) >= 8, f"Side missions only cover {len(systems)} systems: {systems}"

    def test_discovery_method_variety(self) -> None:
        """Multiple discovery methods are used."""
        methods = {m.discovery_method for m in _load_side() if m.discovery_method}
        assert len(methods) >= 3, f"Only {len(methods)} discovery methods used: {methods}"

    def test_encounter_triggered_quests_exist(self) -> None:
        """At least 2 encounter-triggered side quests exist."""
        encounter = [m for m in _load_side() if m.discovery_method == "encounter"]
        assert len(encounter) >= 2, (
            f"Expected >= 2 encounter-triggered quests, got {len(encounter)}"
        )

    def test_station_board_quests_exist(self) -> None:
        """At least 3 station board side quests exist."""
        board = [m for m in _load_side() if m.discovery_method == "station_board"]
        assert len(board) >= 3, f"Expected >= 3 station board quests, got {len(board)}"

    def test_npc_quests_exist(self) -> None:
        """At least 10 NPC-discovered side quests exist."""
        npc = [m for m in _load_side() if m.discovery_method == "npc"]
        assert len(npc) >= 10, f"Expected >= 10 NPC quests, got {len(npc)}"


class TestSideMissionNPCIntegration:
    """Tests that side mission NPCs and dialogues exist."""

    def test_npc_missions_reference_valid_npcs(self) -> None:
        """Side missions using talk_to_npc reference NPCs that exist."""
        project_root = Path(__file__).parent.parent.parent
        loader = DataLoader(data_dir=project_root / "data")
        loader.load_missions()
        loader.load_npcs()

        for m in loader.missions:
            if m.mission_type != "side":
                continue
            for obj in m.objectives:
                if obj.type.value == "talk_to_npc":
                    npc = loader.get_npc(obj.target_id)
                    assert npc is not None, (
                        f"Side mission {m.id} references missing NPC '{obj.target_id}'"
                    )

    def test_price_of_info_uses_sealed_audit_chip(self) -> None:
        """The Price of Information uses sealed_audit_chip, not data_chip."""
        all_missions = _load()
        poi = [m for m in all_missions if m.id == "the_price_of_information"]
        assert len(poi) == 1, "the_price_of_information mission not found"
        mission = poi[0]
        cargo_ids = [c.commodity_id for c in mission.on_accept_cargo]
        assert "sealed_audit_chip" in cargo_ids, (
            f"Expected sealed_audit_chip in on_accept_cargo, got {cargo_ids}"
        )
        assert "data_chip" not in cargo_ids, "the_price_of_information should not use data_chip"
        # Verify matching remove_cargo reward
        remove_rewards = [
            r
            for r in mission.rewards
            if r.reward_type == "remove_cargo" and r.target_id == "sealed_audit_chip"
        ]
        assert len(remove_rewards) == 1, (
            "the_price_of_information should have remove_cargo for sealed_audit_chip"
        )

    def test_side_quest_npcs_have_dialogues(self) -> None:
        """All new side quest NPCs have corresponding dialogue trees."""
        project_root = Path(__file__).parent.parent.parent
        loader = DataLoader(data_dir=project_root / "data")
        loader.load_npcs()
        loader.load_dialogues()

        # NPC IDs used by side missions
        side_npc_ids = {
            "neve_osei",
            "petra_vance",
            "tomasz_brennan",
            "britt_vasara",
            "cassiel_maren",
            "callum_rhee",
            "verdant_farmer",
            "verdant_botanist",
            "haven_refugee",
            "pirate_captain",
            "nova_researcher",
        }
        for npc_id in side_npc_ids:
            npc = loader.get_npc(npc_id)
            assert npc is not None, f"NPC '{npc_id}' not found"
            dlg = loader.get_dialogue(npc.dialogue_id)
            assert dlg is not None, (
                f"NPC '{npc_id}' references missing dialogue '{npc.dialogue_id}'"
            )

    def test_side_quest_npcs_have_hide_after_flag(self) -> None:
        """All side quest NPCs have hide_after_flag set."""
        import json

        project_root = Path(__file__).parent.parent.parent
        with open(project_root / "data" / "characters" / "npcs.json") as f:
            npcs_data = json.load(f)
        npc_map = {n["id"]: n for n in npcs_data["npcs"]}

        expected = {
            "neve_osei": "price_of_info_complete",
            "petra_vance": "whistleblower_complete",
            "tomasz_brennan": "old_debts_complete",
            "britt_vasara": "miners_plight_complete",
            "cassiel_maren": "forgery_complete",
            "callum_rhee": "informant_complete",
            "verdant_farmer": "blight_season_complete",
            "verdant_botanist": "heirloom_seeds_complete",
            "haven_refugee": "lost_registry_complete",
            "pirate_captain": "honor_thieves_complete",
            "nova_researcher": "signal_from_deep_complete",
        }
        for npc_id, flag in expected.items():
            npc = npc_map.get(npc_id)
            assert npc is not None, f"NPC '{npc_id}' not found"
            assert npc.get("hide_after_flag") == flag, (
                f"NPC '{npc_id}' should have hide_after_flag='{flag}', "
                f"got '{npc.get('hide_after_flag')}'"
            )

    def test_side_quest_dialogues_have_in_progress_branch(self) -> None:
        """All side quest dialogues have excluded_flags and in_progress nodes."""
        import json

        project_root = Path(__file__).parent.parent.parent
        with open(project_root / "data" / "dialogue" / "dialogues.json") as f:
            dlg_data = json.load(f)
        dlg_map = {d["id"]: d for d in dlg_data["dialogues"]}

        targets = {
            "neve_osei_price_of_info": "price_of_info_accepted",
            "petra_vance_whistleblower": "whistleblower_accepted",
            "tomasz_brennan_old_debts": "old_debts_accepted",
            "britt_vasara_miners_plight": "miners_plight_accepted",
            "cassiel_maren_forgery": "forgery_job_accepted",
            "callum_rhee_informant": "informant_passenger_accepted",
            "orin_blight_season": "blight_season_accepted",
            "amara_heirloom_seeds": "heirloom_seeds_accepted",
            "soren_lost_registry": "registry_search_started",
            "rook_honor_thieves": "thieves_job_accepted",
            "yuki_signal_deep": "signal_mission_accepted",
        }
        for dlg_id, flag in targets.items():
            dlg = dlg_map[dlg_id]
            nodes = {n["id"]: n for n in dlg["nodes"]}
            start = nodes["start"]

            # Verify in_progress node exists
            assert "in_progress" in nodes, f"Dialogue '{dlg_id}' missing in_progress node"

            # Verify start node has excluded_flags on quest-pitch responses
            excluded = [r for r in start["responses"] if flag in r.get("excluded_flags", [])]
            assert len(excluded) >= 1, f"Dialogue '{dlg_id}' has no excluded_flags for '{flag}'"

            # Verify start node has required_flags response for in_progress
            required = [
                r
                for r in start["responses"]
                if flag in r.get("required_flags", []) and r.get("next_node_id") == "in_progress"
            ]
            assert len(required) == 1, (
                f"Dialogue '{dlg_id}' should have exactly one in_progress route "
                f"with required_flags '{flag}'"
            )
