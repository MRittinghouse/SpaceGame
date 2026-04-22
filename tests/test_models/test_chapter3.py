"""Tests for Chapters 3-7: Undercurrents, Escalation & The Collapse (M08-M17)."""

from spacegame.data_loader import get_data_loader
from spacegame.models.dialogue import (
    NPC,
    DialogueManager,
    DialogueTree,
    SkillCheck,
)
from spacegame.models.mission import (
    MissionManager,
    MissionStatus,
    MissionObjective,
    MissionReward,
    Mission,
    AcceptCargo,
    ObjectiveType,
)
from spacegame.models.player import Player
from spacegame.models.ship import Ship, ShipType


# ============================================================================
# Helpers
# ============================================================================


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player(**overrides: object) -> Player:
    defaults: dict = {
        "name": "TestCaptain",
        "credits": 2000,
        "current_system_id": "nexus_prime",
        "ship": Ship(ship_type=_make_ship_type(), current_fuel=50),
    }
    defaults.update(overrides)
    return Player(**defaults)


def _load_data() -> None:
    """Ensure data loader is initialized."""
    dl = get_data_loader()
    dl.load_all()


# ============================================================================
# Phase A.1: Three New NPCs
# ============================================================================


class TestChapter3NPCs:
    """Three new NPCs should exist in the data files with correct fields."""

    def test_reva_sato_exists(self) -> None:
        """Reva Sato NPC should exist in loaded data."""
        _load_data()
        dl = get_data_loader()
        assert "reva_sato" in dl.npcs, "reva_sato NPC should exist"

    def test_reva_sato_fields(self) -> None:
        """Reva Sato should have correct character data."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["reva_sato"]
        assert npc.name == "Captain Reva Sato"
        assert npc.title == "Guild Convoy Escort"
        assert npc.home_system_id == "nova_research"
        assert npc.portrait_color == (220, 80, 80)
        assert npc.faction_id == "commerce_guild"
        assert npc.dialogue_id == "reva_distress"

    def test_reva_sato_no_auto_trigger(self) -> None:
        """Reva has no auto-trigger — encountered via distress signal + manual dialogue."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["reva_sato"]
        assert npc.auto_trigger_gate_flag == ""
        assert npc.auto_trigger_prerequisites == []

    def test_dex_halloran_exists(self) -> None:
        """Dex Halloran NPC should exist in loaded data."""
        _load_data()
        dl = get_data_loader()
        assert "dex_halloran" in dl.npcs, "dex_halloran NPC should exist"

    def test_dex_halloran_fields(self) -> None:
        """Dex Halloran should have correct character data."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_halloran"]
        assert npc.name == "Dex Halloran"
        assert npc.title == "Information Broker"
        assert npc.home_system_id == "nexus_prime"
        assert npc.portrait_color == (180, 160, 100)
        assert npc.faction_id == ""

    def test_dex_halloran_auto_trigger(self) -> None:
        """Dex auto-triggers at Nexus Prime after cargo_lost is resolved."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_halloran"]
        assert npc.auto_trigger_gate_flag == "met_dex_halloran"
        assert npc.auto_trigger_prerequisites == ["cargo_lost_resolved"]

    def test_malia_torres_exists(self) -> None:
        """Malia Torres NPC should exist in loaded data."""
        _load_data()
        dl = get_data_loader()
        assert "malia_torres" in dl.npcs, "malia_torres NPC should exist"

    def test_malia_torres_fields(self) -> None:
        """Malia Torres should have correct character data."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["malia_torres"]
        assert npc.name == "Malia Torres"
        assert npc.title == "Salvage Boss"
        assert npc.home_system_id == "crimson_reach"
        assert npc.portrait_color == (160, 100, 60)
        assert npc.faction_id == "frontier_alliance"

    def test_malia_torres_auto_trigger(self) -> None:
        """Torres auto-triggers at Crimson Reach after ground mission."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["malia_torres"]
        assert npc.auto_trigger_gate_flag == "met_malia_torres"
        assert npc.auto_trigger_prerequisites == ["crimson_run_ground_complete"]

    def test_total_npc_count(self) -> None:
        _load_data()
        dl = get_data_loader()
        assert len(dl.npcs) >= 17, f"Expected >= 17 NPCs, got {len(dl.npcs)}"


# ============================================================================
# Phase A.2: Three Dialogue Trees
# ============================================================================


class TestRevaDistressDialogue:
    """reva_distress dialogue tree structure and flag logic."""

    def test_dialogue_tree_exists(self) -> None:
        """reva_distress dialogue tree should load from data."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees.get("reva_distress")
        assert tree is not None, "reva_distress dialogue tree should exist"

    def test_start_node_exists(self) -> None:
        """Start node should be reachable."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["reva_distress"]
        start = tree.get_start_node()
        assert start is not None
        assert start.speaker_id == "reva_sato"

    def test_helped_branch_exists(self) -> None:
        """Should have a branch when player helped Reva (helped_reva_sato flag)."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["reva_distress"]
        # The start node should have responses that lead to grateful path
        # Walk the tree to verify flag-gated content exists
        all_node_ids = set(tree.nodes.keys())
        assert (
            "grateful" in all_node_ids
            or "helped_path" in all_node_ids
            or any("grateful" in nid or "helped" in nid for nid in all_node_ids)
        ), f"Should have a helped/grateful branch. Nodes: {all_node_ids}"

    def test_ignored_branch_exists(self) -> None:
        """Should have a branch when player ignored distress signal."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["reva_distress"]
        all_node_ids = set(tree.nodes.keys())
        assert any("cold" in nid or "ignored" in nid or "bitter" in nid for nid in all_node_ids), (
            f"Should have an ignored/cold branch. Nodes: {all_node_ids}"
        )

    def test_persuasion_check_exists(self) -> None:
        """Should contain a persuasion skill check with difficulty 2."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["reva_distress"]
        # Find any response with a skill check
        found_check = False
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "persuasion":
                    assert resp.skill_check.difficulty == 2
                    found_check = True
        assert found_check, "reva_distress should have a persuasion difficulty 2 check"

    def test_sets_cargo_lost_resolved(self) -> None:
        """Dialogue should set cargo_lost_resolved flag somewhere."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["reva_distress"]
        flags_set: set[str] = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    flags_set.add(resp.set_flag)
                if resp.skill_check:
                    if resp.skill_check.set_flag_on_success:
                        flags_set.add(resp.skill_check.set_flag_on_success)
                    if resp.skill_check.set_flag_on_failure:
                        flags_set.add(resp.skill_check.set_flag_on_failure)
        assert "cargo_lost_resolved" in flags_set, (
            f"Should set cargo_lost_resolved. Flags found: {flags_set}"
        )


class TestDexCantinaDialogue:
    """dex_cantina dialogue tree structure and flag logic."""

    def test_dialogue_tree_exists(self) -> None:
        """dex_cantina dialogue tree should load from data."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees.get("dex_cantina")
        assert tree is not None, "dex_cantina dialogue tree should exist"

    def test_start_node_exists(self) -> None:
        """Start node should be reachable."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_cantina"]
        start = tree.get_start_node()
        assert start is not None
        assert start.speaker_id == "dex_halloran"

    def test_persuasion_check_exists(self) -> None:
        """Should contain a persuasion skill check with difficulty 3."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_cantina"]
        found_check = False
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "persuasion":
                    assert resp.skill_check.difficulty == 3
                    found_check = True
        assert found_check, "dex_cantina should have a persuasion difficulty 3 check"

    def test_sets_dex_favor_accepted(self) -> None:
        """Dialogue should set dex_favor_accepted flag on accept path."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_cantina"]
        flags_set: set[str] = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    flags_set.add(resp.set_flag)
                if resp.skill_check:
                    if resp.skill_check.set_flag_on_success:
                        flags_set.add(resp.skill_check.set_flag_on_success)
        assert "dex_favor_accepted" in flags_set, (
            f"Should set dex_favor_accepted. Flags found: {flags_set}"
        )

    def test_has_accept_and_decline_paths(self) -> None:
        """Dialogue should have both accept and decline paths."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_cantina"]
        all_node_ids = set(tree.nodes.keys())
        assert any("accept" in nid for nid in all_node_ids), (
            f"Should have accept path. Nodes: {all_node_ids}"
        )
        assert any("decline" in nid for nid in all_node_ids), (
            f"Should have decline path. Nodes: {all_node_ids}"
        )


class TestTorresUndergroundDialogue:
    """torres_underground dialogue tree structure and flag logic."""

    def test_dialogue_tree_exists(self) -> None:
        """torres_underground dialogue tree should load from data."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees.get("torres_underground")
        assert tree is not None, "torres_underground dialogue tree should exist"

    def test_start_node_exists(self) -> None:
        """Start node should be reachable."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["torres_underground"]
        start = tree.get_start_node()
        assert start is not None
        assert start.speaker_id == "malia_torres"

    def test_sets_met_malia_torres(self) -> None:
        """Dialogue should set met_malia_torres flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["torres_underground"]
        flags_set: set[str] = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    flags_set.add(resp.set_flag)
        assert "met_malia_torres" in flags_set, (
            f"Should set met_malia_torres. Flags found: {flags_set}"
        )

    def test_sets_crimson_underground_access(self) -> None:
        """Dialogue should set crimson_underground_access flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["torres_underground"]
        flags_set: set[str] = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    flags_set.add(resp.set_flag)
        assert "crimson_underground_access" in flags_set, (
            f"Should set crimson_underground_access. Flags found: {flags_set}"
        )

    def test_conspiracy_hint_text(self) -> None:
        """Torres dialogue should contain conspiracy hints about the piracy."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["torres_underground"]
        all_text = " ".join(node.text for node in tree.nodes.values())
        # Should mention someone with resources or organized piracy
        assert any(
            phrase in all_text.lower() for phrase in ["resources", "organized", "someone", "behind"]
        ), "Torres should hint at organized piracy conspiracy"


class TestDialogueTreeTotalCount:
    """Verify total dialogue tree count after additions."""

    def test_total_dialogue_count(self) -> None:
        _load_data()
        dl = get_data_loader()
        assert len(dl.dialogue_trees) >= 18, (
            f"Expected >= 18 dialogue trees, got {len(dl.dialogue_trees)}"
        )


# ============================================================================
# Phase A.3: Auto-Trigger Logic for New NPCs
# ============================================================================


class TestChapter3AutoTriggers:
    """Auto-trigger conditions for Dex and Torres NPCs."""

    def test_dex_triggers_at_nexus_after_cargo_lost(self) -> None:
        """Dex auto-triggers at Nexus Prime after cargo_lost_resolved."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_halloran"]
        player = _make_player(current_system_id="nexus_prime")
        player.dialogue_flags["cargo_lost_resolved"] = True

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(player.dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites)
        )
        assert should_trigger, "Dex should auto-trigger at nexus_prime after cargo_lost_resolved"

    def test_dex_blocked_without_cargo_lost(self) -> None:
        """Dex should not trigger without cargo_lost_resolved."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_halloran"]
        player = _make_player(current_system_id="nexus_prime")

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(player.dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites)
        )
        assert not should_trigger, "Dex should not trigger without cargo_lost_resolved"

    def test_torres_triggers_at_crimson_after_ground(self) -> None:
        """Torres auto-triggers at Crimson Reach after ground mission complete."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["malia_torres"]
        player = _make_player(current_system_id="crimson_reach")
        player.dialogue_flags["crimson_run_ground_complete"] = True

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(player.dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites)
        )
        assert should_trigger, "Torres should auto-trigger at crimson_reach after ground mission"

    def test_torres_blocked_without_ground_mission(self) -> None:
        """Torres should not trigger without crimson_run_ground_complete."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["malia_torres"]
        player = _make_player(current_system_id="crimson_reach")

        should_trigger = (
            npc.auto_trigger_gate_flag
            and not player.dialogue_flags.get(npc.auto_trigger_gate_flag, False)
            and player.current_system_id == npc.home_system_id
            and all(player.dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites)
        )
        assert not should_trigger, "Torres should not trigger without ground mission complete"


# ============================================================================
# Phase B: Mission Definitions & Rewards
# ============================================================================


class TestCargoLostMission:
    """Mission 08 — cargo_lost definition and data."""

    def test_mission_exists(self) -> None:
        """cargo_lost mission should exist in loaded data."""
        _load_data()
        dl = get_data_loader()
        missions = {m.id: m for m in dl.missions}
        assert "cargo_lost" in missions, "cargo_lost mission should exist"

    def test_prerequisites(self) -> None:
        """cargo_lost requires the_scholars_errand."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        assert "the_scholars_errand" in m.prerequisites

    def test_on_accept_cargo(self) -> None:
        """cargo_lost grants electronics x5 on accept."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        assert len(m.on_accept_cargo) == 1
        assert m.on_accept_cargo[0].commodity_id == "electronics"
        assert m.on_accept_cargo[0].quantity == 5

    def test_forced_encounter(self) -> None:
        """cargo_lost has a forced distress_signal encounter."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        assert m.forced_encounter is not None
        assert m.forced_encounter.encounter_type == "distress_signal"

    def test_objectives(self) -> None:
        """cargo_lost has collect_cargo, reach_system, and has_flag objectives."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        types = [obj.type for obj in m.objectives]
        assert ObjectiveType.COLLECT_CARGO in types
        assert ObjectiveType.REACH_SYSTEM in types
        assert ObjectiveType.HAS_FLAG in types

    def test_reach_nova_research(self) -> None:
        """cargo_lost destination is nova_research."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        reach_objs = [o for o in m.objectives if o.type == ObjectiveType.REACH_SYSTEM]
        assert any(o.target_id == "nova_research" for o in reach_objs)

    def test_rewards(self) -> None:
        """cargo_lost rewards include credits, XP, set_flag."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        reward_types = {r.reward_type for r in m.rewards}
        assert "credits" in reward_types
        assert "xp" in reward_types
        assert "remove_cargo" in reward_types
        assert "set_flag" in reward_types

    def test_sets_cargo_lost_complete(self) -> None:
        """cargo_lost rewards set cargo_lost_complete flag."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        flag_rewards = [r for r in m.rewards if r.reward_type == "set_flag"]
        flag_ids = {r.target_id for r in flag_rewards}
        assert "cargo_lost_complete" in flag_ids


class TestWhispersAtTheBarMission:
    """Mission 09 — whispers_at_the_bar definition."""

    def test_mission_exists(self) -> None:
        """whispers_at_the_bar mission should exist."""
        _load_data()
        dl = get_data_loader()
        missions = {m.id: m for m in dl.missions}
        assert "whispers_at_the_bar" in missions

    def test_prerequisites(self) -> None:
        """whispers requires cargo_lost."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "whispers_at_the_bar")
        assert "cargo_lost" in m.prerequisites

    def test_required_flags(self) -> None:
        """whispers requires met_dex_halloran flag."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "whispers_at_the_bar")
        assert "met_dex_halloran" in m.required_flags

    def test_auto_accept(self) -> None:
        """whispers auto-accepts (it's a dialogue mission)."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "whispers_at_the_bar")
        assert m.auto_accept is True

    def test_objective_has_flag(self) -> None:
        """whispers objective is dex_favor_accepted flag."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "whispers_at_the_bar")
        assert len(m.objectives) == 1
        assert m.objectives[0].type == ObjectiveType.HAS_FLAG
        assert m.objectives[0].target_id == "dex_favor_accepted"

    def test_rewards(self) -> None:
        """whispers rewards XP and sets whispers_complete flag."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "whispers_at_the_bar")
        reward_types = {r.reward_type for r in m.rewards}
        assert "xp" in reward_types
        assert "set_flag" in reward_types


class TestTheCrimsonRunMission:
    """Mission 10 — the_crimson_run definition."""

    def test_mission_exists(self) -> None:
        """the_crimson_run mission should exist."""
        _load_data()
        dl = get_data_loader()
        missions = {m.id: m for m in dl.missions}
        assert "the_crimson_run" in missions

    def test_prerequisites(self) -> None:
        """crimson_run requires whispers_at_the_bar."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        assert "whispers_at_the_bar" in m.prerequisites

    def test_required_flags(self) -> None:
        """crimson_run requires dex_favor_accepted."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        assert "dex_favor_accepted" in m.required_flags

    def test_on_accept_cargo(self) -> None:
        """crimson_run grants data_chip x1 on accept."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        assert len(m.on_accept_cargo) == 1
        assert m.on_accept_cargo[0].commodity_id == "data_chip"
        assert m.on_accept_cargo[0].quantity == 1

    def test_reach_crimson_reach(self) -> None:
        """crimson_run destination is crimson_reach."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        reach_objs = [o for o in m.objectives if o.type == ObjectiveType.REACH_SYSTEM]
        assert any(o.target_id == "crimson_reach" for o in reach_objs)

    def test_has_flag_objectives(self) -> None:
        """crimson_run needs ground complete and Torres met flags."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        flag_objs = [o for o in m.objectives if o.type == ObjectiveType.HAS_FLAG]
        flag_targets = {o.target_id for o in flag_objs}
        assert "crimson_run_ground_complete" in flag_targets
        assert "met_malia_torres" in flag_targets

    def test_rewards_include_black_market(self) -> None:
        """crimson_run rewards include black_market_access for crimson_reach."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        bm_rewards = [r for r in m.rewards if r.reward_type == "black_market_access"]
        assert len(bm_rewards) == 1
        assert bm_rewards[0].target_id == "crimson_reach"

    def test_removes_data_chip(self) -> None:
        """crimson_run removes data_chip on completion."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        remove_rewards = [r for r in m.rewards if r.reward_type == "remove_cargo"]
        assert any(r.target_id == "data_chip" for r in remove_rewards)


class TestDataChipCommodity:
    """data_chip quest commodity."""

    def test_data_chip_exists(self) -> None:
        """data_chip commodity should exist."""
        _load_data()
        dl = get_data_loader()
        assert "data_chip" in dl.commodities, "data_chip commodity should exist"

    def test_data_chip_base_price_zero(self) -> None:
        """Quest items have base_price of 0."""
        _load_data()
        dl = get_data_loader()
        chip = dl.commodities["data_chip"]
        assert chip.base_price == 0

    def test_data_chip_no_production_tags(self) -> None:
        """Quest items should not appear in market supply/demand."""
        _load_data()
        dl = get_data_loader()
        chip = dl.commodities["data_chip"]
        assert chip.production_tags == []
        assert chip.consumption_tags == []


class TestCargoLostDistressEncounter:
    """Scripted encounter for the cargo_lost distress signal."""

    def test_encounter_definition_exists(self) -> None:
        """cargo_lost_distress encounter definition should exist."""
        _load_data()
        dl = get_data_loader()
        enc = next(
            (e for e in dl.encounter_definitions if e.id == "cargo_lost_distress"),
            None,
        )
        assert enc is not None, "cargo_lost_distress encounter should exist"

    def test_encounter_type_distress(self) -> None:
        """Should be a distress_signal type encounter."""
        _load_data()
        dl = get_data_loader()
        enc = next(e for e in dl.encounter_definitions if e.id == "cargo_lost_distress")
        assert enc.encounter_type == "distress_signal"

    def test_has_help_choice(self) -> None:
        """Should have a choice to answer the signal."""
        _load_data()
        dl = get_data_loader()
        enc = next(e for e in dl.encounter_definitions if e.id == "cargo_lost_distress")
        choice_ids = {c.id for c in enc.choices}
        assert "answer_signal" in choice_ids

    def test_has_ignore_choice(self) -> None:
        """Should have a choice to press on."""
        _load_data()
        dl = get_data_loader()
        enc = next(e for e in dl.encounter_definitions if e.id == "cargo_lost_distress")
        choice_ids = {c.id for c in enc.choices}
        assert "press_on" in choice_ids

    def test_help_choice_sets_flag(self) -> None:
        """Answering the signal should set helped_reva_sato flag."""
        _load_data()
        dl = get_data_loader()
        enc = next(e for e in dl.encounter_definitions if e.id == "cargo_lost_distress")
        help_choice = next(c for c in enc.choices if c.id == "answer_signal")
        flag_rewards = [r for r in help_choice.outcome.rewards if r.reward_type == "set_flag"]
        flag_ids = {r.target_id for r in flag_rewards}
        assert "helped_reva_sato" in flag_ids

    def test_ignore_choice_sets_flag(self) -> None:
        """Pressing on should set ignored_distress_signal flag."""
        _load_data()
        dl = get_data_loader()
        enc = next(e for e in dl.encounter_definitions if e.id == "cargo_lost_distress")
        ignore_choice = next(c for c in enc.choices if c.id == "press_on")
        flag_rewards = [r for r in ignore_choice.outcome.rewards if r.reward_type == "set_flag"]
        flag_ids = {r.target_id for r in flag_rewards}
        assert "ignored_distress_signal" in flag_ids


class TestMissionCounts:
    """Verify total mission and commodity counts."""

    def test_total_mission_count(self) -> None:
        _load_data()
        dl = get_data_loader()
        assert len(dl.missions) >= 22, f"Expected >= 22 missions, got {len(dl.missions)}"

    def test_total_commodity_count(self) -> None:
        """Total commodity count should be 61 (60 existing + 1 sealed_audit_chip)."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.commodities) == 61, f"Expected 61 commodities, got {len(dl.commodities)}"

    def test_total_encounter_count(self) -> None:
        """Total encounter definition count should be >= 120 after R3 expansion."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.encounter_definitions) >= 120, (
            f"Expected >= 120 encounter definitions, got {len(dl.encounter_definitions)}"
        )


# ============================================================================
# Phase B: Mission Chain Logic
# ============================================================================


class TestChapter3MissionChain:
    """Mission chain from Chapter 2 completion through Chapter 3."""

    def test_cargo_lost_unlocks_after_scholars_errand(self) -> None:
        """M08 unlocks when the_scholars_errand is completed."""
        m_prereq = Mission(
            id="the_scholars_errand",
            name="Scholar",
            description="",
            objectives=[],
            rewards=[],
            prerequisites=[],
        )
        m_cargo = Mission(
            id="cargo_lost",
            name="Cargo Lost",
            description="",
            prerequisites=["the_scholars_errand"],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="nova_research",
                    description="Reach Nova Research",
                ),
            ],
            rewards=[MissionReward(reward_type="xp", amount=100)],
        )
        mgr = MissionManager([m_prereq, m_cargo])

        # Before prereq completed
        mgr.update_availability()
        assert mgr._status["cargo_lost"] == MissionStatus.UNAVAILABLE

        # Complete prereq
        mgr._status["the_scholars_errand"] = MissionStatus.COMPLETED
        newly = mgr.update_availability()
        assert "cargo_lost" in newly

    def test_whispers_needs_cargo_lost_and_dex_flag(self) -> None:
        """M09 needs cargo_lost + met_dex_halloran flag."""
        m_cargo = Mission(
            id="cargo_lost",
            name="Cargo",
            description="",
            objectives=[],
            rewards=[],
            prerequisites=[],
        )
        m_whispers = Mission(
            id="whispers_at_the_bar",
            name="Whispers",
            description="",
            prerequisites=["cargo_lost"],
            required_flags=["met_dex_halloran"],
            auto_accept=True,
            objectives=[
                MissionObjective(
                    type=ObjectiveType.HAS_FLAG,
                    target_id="dex_favor_accepted",
                    description="Accept or decline Dex's favor",
                ),
            ],
            rewards=[MissionReward(reward_type="xp", amount=50)],
        )
        mgr = MissionManager([m_cargo, m_whispers])

        # Complete cargo_lost but no flag
        mgr._status["cargo_lost"] = MissionStatus.COMPLETED
        mgr.update_availability()
        assert mgr._status["whispers_at_the_bar"] == MissionStatus.UNAVAILABLE

        # Set flag — auto_accept should make it ACTIVE
        flags = {"met_dex_halloran": True}
        mgr.update_availability(flags)
        assert mgr._status["whispers_at_the_bar"] == MissionStatus.ACTIVE

    def test_crimson_run_needs_whispers_and_favor(self) -> None:
        """M10 needs whispers + dex_favor_accepted flag."""
        m_whispers = Mission(
            id="whispers_at_the_bar",
            name="Whispers",
            description="",
            objectives=[],
            rewards=[],
            prerequisites=[],
        )
        m_crimson = Mission(
            id="the_crimson_run",
            name="Crimson",
            description="",
            prerequisites=["whispers_at_the_bar"],
            required_flags=["dex_favor_accepted"],
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="crimson_reach",
                    description="Reach Crimson Reach",
                ),
            ],
            rewards=[MissionReward(reward_type="xp", amount=120)],
        )
        mgr = MissionManager([m_whispers, m_crimson])

        mgr._status["whispers_at_the_bar"] = MissionStatus.COMPLETED
        mgr.update_availability()
        assert mgr._status["the_crimson_run"] == MissionStatus.UNAVAILABLE

        flags = {"dex_favor_accepted": True}
        newly = mgr.update_availability(flags)
        assert "the_crimson_run" in newly


# ============================================================================
# Phase C: Engine Wiring
# ============================================================================


class TestForcedEncounterDefId:
    """ForcedEncounter encounter_def_id field and serialization."""

    def test_encounter_def_id_field(self) -> None:
        """ForcedEncounter should support encounter_def_id."""
        from spacegame.models.mission import ForcedEncounter

        fe = ForcedEncounter(
            encounter_type="distress_signal",
            trigger_flag="cargo_lost_distress_triggered",
            encounter_def_id="cargo_lost_distress",
        )
        assert fe.encounter_def_id == "cargo_lost_distress"

    def test_encounter_def_id_default_empty(self) -> None:
        """encounter_def_id defaults to empty string."""
        from spacegame.models.mission import ForcedEncounter

        fe = ForcedEncounter(encounter_type="hostile")
        assert fe.encounter_def_id == ""

    def test_serialization_roundtrip(self) -> None:
        """encounter_def_id survives to_dict/from_dict."""
        from spacegame.models.mission import ForcedEncounter

        fe = ForcedEncounter(
            encounter_type="distress_signal",
            trigger_flag="test_flag",
            encounter_def_id="cargo_lost_distress",
        )
        d = fe.to_dict()
        assert d["encounter_def_id"] == "cargo_lost_distress"

        fe2 = ForcedEncounter.from_dict(d)
        assert fe2.encounter_def_id == "cargo_lost_distress"
        assert fe2.trigger_flag == "test_flag"

    def test_backward_compat_no_def_id(self) -> None:
        """Old data without encounter_def_id loads with empty default."""
        from spacegame.models.mission import ForcedEncounter

        data = {"encounter_type": "hostile", "enemy_template_ids": ["raider_scout"]}
        fe = ForcedEncounter.from_dict(data)
        assert fe.encounter_def_id == ""

    def test_cargo_lost_mission_has_encounter_def_id(self) -> None:
        """Loaded cargo_lost mission's forced_encounter has encounter_def_id."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "cargo_lost")
        assert m.forced_encounter is not None
        assert m.forced_encounter.encounter_def_id == "cargo_lost_distress"


class TestGroundMissionFields:
    """Mission ground_mission fields for auto-launching ground exploration."""

    def test_ground_mission_id_field(self) -> None:
        """Mission should support ground_mission_id."""
        m = Mission(
            id="test",
            name="Test",
            description="",
            ground_mission_id="mission_10_crimson_reach",
            ground_mission_system_id="crimson_reach",
            ground_mission_complete_flag="crimson_run_ground_complete",
        )
        assert m.ground_mission_id == "mission_10_crimson_reach"
        assert m.ground_mission_system_id == "crimson_reach"
        assert m.ground_mission_complete_flag == "crimson_run_ground_complete"

    def test_ground_mission_fields_default_empty(self) -> None:
        """Ground mission fields default to empty."""
        m = Mission(id="test", name="Test", description="")
        assert m.ground_mission_id == ""
        assert m.ground_mission_system_id == ""
        assert m.ground_mission_complete_flag == ""

    def test_crimson_run_has_ground_mission(self) -> None:
        """the_crimson_run mission should have ground mission fields set."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        assert m.ground_mission_id == "mission_10_crimson_reach"
        assert m.ground_mission_system_id == "crimson_reach"
        assert m.ground_mission_complete_flag == "crimson_run_ground_complete"

    def test_ground_mission_serialization(self) -> None:
        """Ground mission fields survive to_dict round-trip."""
        m = Mission(
            id="test",
            name="Test",
            description="",
            ground_mission_id="test_ground",
            ground_mission_system_id="test_system",
            ground_mission_complete_flag="test_complete",
        )
        d = m.to_dict()
        assert d.get("ground_mission_id") == "test_ground"
        assert d.get("ground_mission_system_id") == "test_system"
        assert d.get("ground_mission_complete_flag") == "test_complete"


class TestBlackMarketAccessReward:
    """black_market_access reward type in MissionManager."""

    def test_reward_type_in_mission_data(self) -> None:
        """the_crimson_run should have black_market_access reward."""
        _load_data()
        dl = get_data_loader()
        m = next(m for m in dl.missions if m.id == "the_crimson_run")
        bm = [r for r in m.rewards if r.reward_type == "black_market_access"]
        assert len(bm) == 1
        assert bm[0].target_id == "crimson_reach"

    def test_apply_rewards_grants_access(self) -> None:
        """black_market_access reward should grant player access."""
        m = Mission(
            id="test_bm",
            name="Test",
            description="",
            rewards=[
                MissionReward(
                    reward_type="black_market_access", amount=0, target_id="crimson_reach"
                ),
            ],
        )
        mgr = MissionManager([m])
        player = _make_player()

        assert not player.has_black_market_access("crimson_reach")
        mgr.apply_rewards("test_bm", player)
        assert player.has_black_market_access("crimson_reach")


# ============================================================================
# Phase D: Integration Tests
# ============================================================================


class TestChapter3FullChain:
    """Integration: full flag chain from M07 → M08 → M09 → M10."""

    def _make_chapter3_missions(self) -> list[Mission]:
        """Build the Chapter 3 mission set for chain testing."""
        return [
            Mission(
                id="the_scholars_errand",
                name="The Scholar's Errand",
                description="",
                objectives=[
                    MissionObjective(
                        type=ObjectiveType.REACH_SYSTEM,
                        target_id="axiom_labs",
                        description="Transport to Axiom Labs",
                    ),
                ],
                rewards=[
                    MissionReward(
                        reward_type="set_flag", amount=0, target_id="escorted_priya_axiom"
                    ),
                    MissionReward(reward_type="xp", amount=80),
                ],
            ),
            Mission(
                id="cargo_lost",
                name="Cargo Lost",
                description="",
                prerequisites=["the_scholars_errand"],
                on_accept_cargo=[AcceptCargo(commodity_id="electronics", quantity=5)],
                objectives=[
                    MissionObjective(
                        type=ObjectiveType.COLLECT_CARGO,
                        target_id="electronics",
                        target_quantity=5,
                        description="Have electronics",
                    ),
                    MissionObjective(
                        type=ObjectiveType.REACH_SYSTEM,
                        target_id="nova_research",
                        description="Reach Nova Research",
                    ),
                    MissionObjective(
                        type=ObjectiveType.HAS_FLAG,
                        target_id="cargo_lost_resolved",
                        description="Speak with Reva",
                    ),
                ],
                rewards=[
                    MissionReward(reward_type="credits", amount=600),
                    MissionReward(reward_type="remove_cargo", amount=5, target_id="electronics"),
                    MissionReward(reward_type="xp", amount=100),
                    MissionReward(
                        reward_type="set_flag", amount=0, target_id="cargo_lost_complete"
                    ),
                ],
            ),
            Mission(
                id="whispers_at_the_bar",
                name="Whispers",
                description="",
                prerequisites=["cargo_lost"],
                required_flags=["met_dex_halloran"],
                auto_accept=True,
                objectives=[
                    MissionObjective(
                        type=ObjectiveType.HAS_FLAG,
                        target_id="dex_favor_accepted",
                        description="Dex's favor",
                    ),
                ],
                rewards=[
                    MissionReward(reward_type="xp", amount=50),
                    MissionReward(reward_type="set_flag", amount=0, target_id="whispers_complete"),
                ],
            ),
            Mission(
                id="the_crimson_run",
                name="The Crimson Run",
                description="",
                prerequisites=["whispers_at_the_bar"],
                required_flags=["dex_favor_accepted"],
                on_accept_cargo=[AcceptCargo(commodity_id="data_chip", quantity=1)],
                objectives=[
                    MissionObjective(
                        type=ObjectiveType.REACH_SYSTEM,
                        target_id="crimson_reach",
                        description="Reach Crimson Reach",
                    ),
                    MissionObjective(
                        type=ObjectiveType.HAS_FLAG,
                        target_id="crimson_run_ground_complete",
                        description="Ground mission",
                    ),
                    MissionObjective(
                        type=ObjectiveType.HAS_FLAG,
                        target_id="met_malia_torres",
                        description="Meet Torres",
                    ),
                ],
                rewards=[
                    MissionReward(reward_type="credits", amount=400),
                    MissionReward(reward_type="remove_cargo", amount=1, target_id="data_chip"),
                    MissionReward(reward_type="xp", amount=120),
                    MissionReward(
                        reward_type="black_market_access",
                        amount=0,
                        target_id="crimson_reach",
                    ),
                ],
            ),
        ]

    def test_full_chain_happy_path(self) -> None:
        """Complete M07 → M08 → M09 → M10 with all flags."""
        missions = self._make_chapter3_missions()
        mgr = MissionManager(missions)
        player = _make_player(current_system_id="nexus_prime")

        # M07 (the_scholars_errand) — force to available and complete
        mgr.update_availability()
        mgr._status["the_scholars_errand"] = MissionStatus.AVAILABLE
        mgr.accept_mission("the_scholars_errand")
        player.current_system_id = "axiom_labs"
        completed = mgr.check_objectives(player)
        assert "the_scholars_errand" in completed
        mgr.apply_rewards("the_scholars_errand", player)

        # M08 (cargo_lost) should unlock
        newly = mgr.update_availability(player.dialogue_flags)
        assert "cargo_lost" in newly

        # Accept M08 — cargo loaded
        mgr.accept_mission("cargo_lost")
        player.ship.add_cargo("electronics", 5)

        # Travel to nova_research and talk to Reva
        player.current_system_id = "nova_research"
        player.dialogue_flags["cargo_lost_resolved"] = True
        completed = mgr.check_objectives(player)
        assert "cargo_lost" in completed
        mgr.apply_rewards("cargo_lost", player)

        # Dex auto-trigger sets met_dex_halloran
        player.dialogue_flags["met_dex_halloran"] = True
        player.current_system_id = "nexus_prime"

        # M09 (whispers) should auto-accept
        mgr.update_availability(player.dialogue_flags)
        assert mgr._status["whispers_at_the_bar"] == MissionStatus.ACTIVE

        # Player accepts Dex's favor
        player.dialogue_flags["dex_favor_accepted"] = True
        completed = mgr.check_objectives(player)
        assert "whispers_at_the_bar" in completed
        mgr.apply_rewards("whispers_at_the_bar", player)

        # M10 (crimson_run) should unlock
        newly = mgr.update_availability(player.dialogue_flags)
        assert "the_crimson_run" in newly

        # Accept M10 — data_chip loaded
        mgr.accept_mission("the_crimson_run")
        player.ship.add_cargo("data_chip", 1)

        # Travel to Crimson Reach, ground mission, meet Torres
        player.current_system_id = "crimson_reach"
        player.dialogue_flags["crimson_run_ground_complete"] = True
        player.dialogue_flags["met_malia_torres"] = True
        completed = mgr.check_objectives(player)
        assert "the_crimson_run" in completed

        # Apply rewards — black market access granted
        mgr.apply_rewards("the_crimson_run", player)
        assert player.has_black_market_access("crimson_reach")
        assert player.credits == 2000 + 600 + 400  # Initial + M08 + M10

    def test_helped_reva_vs_ignored(self) -> None:
        """Choice at distress signal affects Reva dialogue branches."""
        # This tests the flag gating in the dialogue, not the mission chain
        _load_data()
        dl = get_data_loader()

        # Helped path — grateful response visible, cold path hidden
        dm = DialogueManager()
        dm.set_flag("helped_reva_sato")
        tree = dl.dialogue_trees["reva_distress"]
        dm.start_dialogue(tree, npc_id="reva_sato")
        responses = dm.get_available_responses()
        texts = [r.text for r in responses]
        assert any("distress signal" in t.lower() or "sato" in t.lower() for t in texts)

        # Ignored path
        dm2 = DialogueManager()
        dm2.set_flag("ignored_distress_signal")
        dm2.start_dialogue(tree, npc_id="reva_sato")
        responses2 = dm2.get_available_responses()
        texts2 = [r.text for r in responses2]
        # Should have the cold/ignored response, not the grateful one
        assert any("know you" in t.lower() for t in texts2) or any(
            "cold" in r.next_node_id or "ignored" in r.next_node_id
            for r in responses2
            if r.next_node_id
        )

    def test_dex_persuasion_branching(self) -> None:
        """Dex dialogue persuasion check success/failure leads to different nodes."""
        from spacegame.models.social import SocialManager

        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_cantina"]

        # With high persuasion (mock level 5) — should succeed difficulty 3
        dm = DialogueManager()
        social = SocialManager()
        # Level up persuasion to 5 to guarantee success
        for _ in range(50):
            social.resolve_check("persuasion", 0, "")
        dm.set_social_manager(social)
        dm.start_dialogue(tree, npc_id="dex_halloran")

        # Navigate to the node with the persuasion check
        # Start → intro or why_me → tension (has the check)
        dm.select_response(0)  # → intro
        dm.select_response(0)  # → tension
        node = dm.get_current_node()
        assert node is not None
        assert node.id == "tension"

        # Find the persuasion check response
        responses = dm.get_available_responses()
        check_idx = next(i for i, r in enumerate(responses) if r.skill_check is not None)
        next_node = dm.select_response(check_idx)
        assert next_node is not None
        assert next_node.id == "chip_truth"  # Success path

    def test_save_load_mid_chapter(self) -> None:
        """Flags and mission state should survive save/load mid-chapter."""
        from spacegame.save_manager import SaveManager
        import tempfile
        from pathlib import Path

        _load_data()

        player = _make_player()
        player.dialogue_flags["cargo_lost_resolved"] = True
        player.dialogue_flags["helped_reva_sato"] = True
        player.dialogue_flags["met_dex_halloran"] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.dialogue_flags.get("cargo_lost_resolved") is True
            assert p2.dialogue_flags.get("helped_reva_sato") is True
            assert p2.dialogue_flags.get("met_dex_halloran") is True


# ============================================================================
# Phase C.1: Encounter Def ID Routing
# ============================================================================


class TestEncounterDefIdRouting:
    """ForcedEncounter should pass encounter_def_id through to EncounterRef."""

    def test_forced_encounter_creates_ref_with_def_id(self) -> None:
        """_check_forced_encounters should include encounter_def_id on the ref."""
        from spacegame.models.mission import ForcedEncounter
        from spacegame.models.encounter import EncounterRef

        fe = ForcedEncounter(
            encounter_type="distress_signal",
            trigger_flag="cargo_lost_distress_triggered",
            encounter_def_id="cargo_lost_distress",
        )
        # Simulate what _check_forced_encounters should do
        ref = EncounterRef(
            enemy_template_ids=list(fe.enemy_template_ids),
            encounter_seed=hash(fe.trigger_flag) & 0xFFFFFFFF,
            encounter_type=fe.encounter_type,
            encounter_def_id=fe.encounter_def_id,
        )
        assert ref.encounter_def_id == "cargo_lost_distress"

    def test_resolve_by_direct_id(self) -> None:
        """select_encounter_definition should find by ID when encounter_def_id is set."""
        from spacegame.models.encounter import EncounterDefinition, EncounterChoice

        definitions = [
            EncounterDefinition(
                id="distress_medical_01",
                encounter_type="distress_signal",
                name="Medical Emergency",
                description="Test",
                choices=[],
                weight=10,
            ),
            EncounterDefinition(
                id="cargo_lost_distress",
                encounter_type="distress_signal",
                name="Disabled Convoy",
                description="Test",
                choices=[],
                weight=0,  # Zero weight — should NOT be randomly selected
            ),
        ]
        # lookup_encounter_definition should find by ID regardless of weight
        from spacegame.models.encounter import lookup_encounter_definition

        result = lookup_encounter_definition(definitions, "cargo_lost_distress")
        assert result is not None
        assert result.id == "cargo_lost_distress"

    def test_lookup_nonexistent_returns_none(self) -> None:
        """lookup_encounter_definition returns None for unknown IDs."""
        from spacegame.models.encounter import lookup_encounter_definition

        result = lookup_encounter_definition([], "nonexistent")
        assert result is None


# ============================================================================
# Phase C.2: Ground Mission Auto-Launch
# ============================================================================


class TestGroundMissionTrigger:
    """Ground mission trigger logic for active missions on system arrival."""

    def test_get_ground_trigger_at_system(self) -> None:
        """MissionManager should report ground mission triggers for current system."""
        m = Mission(
            id="the_crimson_run",
            name="Crimson",
            description="",
            ground_mission_id="mission_10_crimson_reach",
            ground_mission_system_id="crimson_reach",
            ground_mission_complete_flag="crimson_run_ground_complete",
            objectives=[
                MissionObjective(
                    type=ObjectiveType.REACH_SYSTEM,
                    target_id="crimson_reach",
                    description="",
                ),
            ],
            rewards=[],
        )
        mgr = MissionManager([m])
        mgr._status["the_crimson_run"] = MissionStatus.ACTIVE

        player = _make_player(current_system_id="crimson_reach")

        trigger = mgr.get_ground_mission_trigger(player.current_system_id, player.dialogue_flags)
        assert trigger is not None
        assert trigger[0] == "mission_10_crimson_reach"  # ground_mission_id
        assert trigger[1] == "crimson_run_ground_complete"  # complete_flag

    def test_no_trigger_at_wrong_system(self) -> None:
        """No ground trigger when player is at the wrong system."""
        m = Mission(
            id="the_crimson_run",
            name="Crimson",
            description="",
            ground_mission_id="mission_10_crimson_reach",
            ground_mission_system_id="crimson_reach",
            ground_mission_complete_flag="crimson_run_ground_complete",
            objectives=[],
            rewards=[],
        )
        mgr = MissionManager([m])
        mgr._status["the_crimson_run"] = MissionStatus.ACTIVE

        player = _make_player(current_system_id="nexus_prime")
        trigger = mgr.get_ground_mission_trigger(player.current_system_id, player.dialogue_flags)
        assert trigger is None

    def test_no_trigger_if_already_complete(self) -> None:
        """No ground trigger when complete flag is already set."""
        m = Mission(
            id="the_crimson_run",
            name="Crimson",
            description="",
            ground_mission_id="mission_10_crimson_reach",
            ground_mission_system_id="crimson_reach",
            ground_mission_complete_flag="crimson_run_ground_complete",
            objectives=[],
            rewards=[],
        )
        mgr = MissionManager([m])
        mgr._status["the_crimson_run"] = MissionStatus.ACTIVE

        player = _make_player(current_system_id="crimson_reach")
        player.dialogue_flags["crimson_run_ground_complete"] = True
        trigger = mgr.get_ground_mission_trigger(player.current_system_id, player.dialogue_flags)
        assert trigger is None

    def test_no_trigger_if_mission_not_active(self) -> None:
        """No ground trigger for unavailable missions."""
        m = Mission(
            id="the_crimson_run",
            name="Crimson",
            description="",
            ground_mission_id="mission_10_crimson_reach",
            ground_mission_system_id="crimson_reach",
            ground_mission_complete_flag="crimson_run_ground_complete",
            objectives=[],
            rewards=[],
        )
        mgr = MissionManager([m])
        # Mission stays UNAVAILABLE

        player = _make_player(current_system_id="crimson_reach")
        trigger = mgr.get_ground_mission_trigger(player.current_system_id, player.dialogue_flags)
        assert trigger is None


# ============================================================================
# Phase C.3: Crimson Reach Access Earned
# ============================================================================


class TestCrimsonReachAccess:
    """Crimson Reach black market access should be earned via mission, not free."""

    def test_backward_compat_existing_saves(self) -> None:
        """Old saves with crimson_reach in black_market_access still work."""
        from spacegame.save_manager import SaveManager
        import tempfile
        from pathlib import Path

        _load_data()

        player = _make_player()
        player.grant_black_market_access("crimson_reach")

        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(save_directory=Path(tmpdir))
            sm.save_game(0, player, {}, {}, 100)
            loaded = sm.load_game(0)
            assert loaded is not None

            p2 = loaded["player"]
            assert p2.has_black_market_access("crimson_reach")

    def test_new_player_no_crimson_access(self) -> None:
        """New players should NOT have Crimson Reach access by default."""
        player = _make_player()
        assert not player.has_black_market_access("crimson_reach")


# ============================================================================
# Mission 11: Embassy Visit — Summit NPC, Dialogue, Mission
# ============================================================================


class TestEmbassySummitNPC:
    """Summit trigger NPC entry for auto-triggering at Axiom Labs."""

    def test_summit_npc_exists(self) -> None:
        """Summit host NPC entry exists in loaded data."""
        _load_data()
        dl = get_data_loader()
        assert "embassy_summit_host" in dl.npcs

    def test_summit_npc_fields(self) -> None:
        """Summit host reuses Priya's identity, stationed at Axiom Labs."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["embassy_summit_host"]
        assert npc.name == "Dr. Priya Osei"
        assert npc.title == "Summit Chairperson"
        assert npc.home_system_id == "axiom_labs"
        assert npc.faction_id == "science_collective"
        assert npc.dialogue_id == "embassy_summit"

    def test_summit_auto_trigger(self) -> None:
        """Summit auto-triggers at Axiom Labs after Crimson Run storyline."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["embassy_summit_host"]
        assert npc.auto_trigger_gate_flag == "attended_embassy_summit"
        assert "crimson_underground_access" in npc.auto_trigger_prerequisites


class TestEmbassySummitDialogue:
    """Tests for the embassy_summit dialogue tree."""

    def test_dialogue_tree_exists(self) -> None:
        """embassy_summit dialogue tree loads from data."""
        _load_data()
        dl = get_data_loader()
        assert "embassy_summit" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Start node is arrival."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        assert tree.start_node_id == "arrival"

    def test_node_count(self) -> None:
        """Dialogue has at least 12 nodes for a full summit scene."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        assert len(tree.nodes) >= 12, f"Expected 12+ nodes, got {len(tree.nodes)}"

    def test_multiple_speakers(self) -> None:
        """Summit uses speakers from multiple factions."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        speakers = {node.speaker_id for node in tree.nodes.values()}
        # Must include Priya (chair), Reva (Guild), Hanna (Union), Tomas (Alliance)
        assert "dr_priya_osei" in speakers
        assert "reva_sato" in speakers
        assert "hanna_voss" in speakers
        assert "tomas_drifter" in speakers

    def test_persuasion_check_exists(self) -> None:
        """Summit deadlock offers a persuasion skill check."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        # Find a response with a persuasion skill check
        found = False
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "persuasion":
                    found = True
                    break
        assert found, "Summit should have a persuasion skill check"

    def test_observation_check_exists(self) -> None:
        """Summit offers an observation skill check."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        found = False
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "observation":
                    found = True
                    break
        assert found, "Summit should have an observation skill check"

    def test_observation_success_sets_flag(self) -> None:
        """Passing the observation check sets noticed_guild_signal."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "observation":
                    success_node = tree.nodes.get(resp.skill_check.success_node_id)
                    assert success_node is not None
                    # Flag should be on one of the success node's responses
                    flag_set = any(
                        r.set_flag == "noticed_guild_signal" for r in success_node.responses
                    )
                    assert flag_set, "Observation success should set noticed_guild_signal"
                    return
        assert False, "No observation check found"

    def test_persuasion_success_sets_flag(self) -> None:
        """Successful persuasion sets spoke_at_summit."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check and resp.skill_check.skill == "persuasion":
                    success_node = tree.nodes.get(resp.skill_check.success_node_id)
                    assert success_node is not None
                    flag_set = any(r.set_flag == "spoke_at_summit" for r in success_node.responses)
                    assert flag_set, "Persuasion success should set spoke_at_summit"
                    return
        assert False, "No persuasion check found"

    def test_terminal_node_sets_attended_flag(self) -> None:
        """Summit farewell sets attended_embassy_summit via response."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["embassy_summit"]
        farewell = tree.nodes.get("summit_farewell")
        assert farewell is not None, "summit_farewell node should exist"
        flag_set = any(r.set_flag == "attended_embassy_summit" for r in farewell.responses)
        assert flag_set, "Farewell response should set attended_embassy_summit"


class TestEmbassyVisitMission:
    """Tests for the embassy_visit mission definition."""

    def test_mission_exists(self) -> None:
        """embassy_visit mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "embassy_visit" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires the_crimson_run."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "embassy_visit")
        assert "the_crimson_run" in mission.prerequisites

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "embassy_visit")
        assert mission.auto_accept is True

    def test_objectives(self) -> None:
        """Mission has reach_system axiom_labs + has_flag attended_embassy_summit."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "embassy_visit")
        obj_types = [(o.type, o.target_id) for o in mission.objectives]
        assert (ObjectiveType.REACH_SYSTEM, "axiom_labs") in obj_types
        assert (ObjectiveType.HAS_FLAG, "attended_embassy_summit") in obj_types

    def test_rewards(self) -> None:
        """Mission rewards XP and sets embassy_complete flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "embassy_visit")
        reward_types = [(r.reward_type, r.target_id) for r in mission.rewards]
        assert any(r.reward_type == "xp" for r in mission.rewards)
        assert ("set_flag", "embassy_complete") in reward_types

    def test_mission_completion_flow(self) -> None:
        """Mission completes when at axiom_labs with summit attended flag."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)

        player = _make_player(current_system_id="axiom_labs")

        # Complete prerequisite chain through the_crimson_run
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Embassy visit should become available and auto-accept
        newly = mgr.update_availability(player.dialogue_flags)
        assert "embassy_visit" in newly
        assert mgr._status["embassy_visit"] == MissionStatus.ACTIVE

        # Not complete yet — missing attended flag
        completed = mgr.check_objectives(player)
        assert "embassy_visit" not in completed

        # Set the summit attended flag
        player.dialogue_flags["attended_embassy_summit"] = True
        completed = mgr.check_objectives(player)
        assert "embassy_visit" in completed


# ============================================================================
# Mission 12: Under Fire — Elite Pirate Combat Encounter
# ============================================================================


class TestLedgerEnemyTemplates:
    """New enemy templates for the well-equipped pirate ambush."""

    def test_ledger_raider_exists(self) -> None:
        """Unmarked Raider template exists."""
        _load_data()
        dl = get_data_loader()
        assert "ledger_raider" in dl.enemy_templates

    def test_ledger_raider_stats(self) -> None:
        """Unmarked Raider is tougher than a standard pirate_raider."""
        _load_data()
        dl = get_data_loader()
        raider = dl.enemy_templates["ledger_raider"]
        standard = dl.enemy_templates["pirate_raider"]
        assert raider.hull > standard.hull, "Ledger raider should be tougher"
        assert raider.danger_tier == "moderate"
        assert raider.faction_id == ""  # Unmarked — no faction
        assert len(raider.moves) >= 2

    def test_ledger_raider_behavior(self) -> None:
        """Unmarked Raider uses aggressive tactics."""
        _load_data()
        dl = get_data_loader()
        raider = dl.enemy_templates["ledger_raider"]
        from spacegame.models.combat import EnemyBehavior

        assert raider.behavior == EnemyBehavior.AGGRESSIVE

    def test_ledger_striker_exists(self) -> None:
        """Unmarked Striker template exists."""
        _load_data()
        dl = get_data_loader()
        assert "ledger_striker" in dl.enemy_templates

    def test_ledger_striker_stats(self) -> None:
        """Unmarked Striker is fast and evasive."""
        _load_data()
        dl = get_data_loader()
        striker = dl.enemy_templates["ledger_striker"]
        assert striker.danger_tier == "moderate"
        assert striker.faction_id == ""
        assert striker.evasion >= 40, "Striker should be highly evasive"
        assert striker.speed >= 55, "Striker should be fast"
        assert len(striker.moves) >= 2

    def test_ledger_striker_behavior(self) -> None:
        """Unmarked Striker uses evasive tactics."""
        _load_data()
        dl = get_data_loader()
        striker = dl.enemy_templates["ledger_striker"]
        from spacegame.models.combat import EnemyBehavior

        assert striker.behavior == EnemyBehavior.EVASIVE

    def test_enemy_descriptions_hint_guild_hardware(self) -> None:
        """Enemy descriptions should reference military-grade equipment."""
        _load_data()
        dl = get_data_loader()
        raider = dl.enemy_templates["ledger_raider"]
        striker = dl.enemy_templates["ledger_striker"]
        combined = (raider.description + striker.description).lower()
        assert "military" in combined or "guild" in combined or "unmarked" in combined


class TestUnderFireMission:
    """Tests for the under_fire mission definition."""

    def test_mission_exists(self) -> None:
        """under_fire mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "under_fire" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires embassy_visit."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "under_fire")
        assert "embassy_visit" in mission.prerequisites

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "under_fire")
        assert mission.auto_accept is True

    def test_forced_encounter(self) -> None:
        """Mission has a hostile forced encounter with Ledger enemies."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "under_fire")
        fe = mission.forced_encounter
        assert fe is not None, "Mission should have a forced encounter"
        assert fe.encounter_type == "hostile"
        assert "ledger_raider" in fe.enemy_template_ids
        assert "ledger_striker" in fe.enemy_template_ids
        assert fe.trigger_flag, "Forced encounter needs a trigger flag"

    def test_objective_is_encounter_flag(self) -> None:
        """Mission objective uses the forced encounter trigger flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "under_fire")
        fe = mission.forced_encounter
        obj_flags = [o.target_id for o in mission.objectives if o.type == ObjectiveType.HAS_FLAG]
        assert fe.trigger_flag in obj_flags

    def test_rewards_include_discovery_flag(self) -> None:
        """Mission rewards set guild_hardware_discovered flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "under_fire")
        reward_flags = [(r.reward_type, r.target_id) for r in mission.rewards]
        assert ("set_flag", "guild_hardware_discovered") in reward_flags
        assert any(r.reward_type == "xp" for r in mission.rewards)

    def test_mission_completion_flow(self) -> None:
        """Mission completes when forced encounter trigger flag is set."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete prerequisite chain through embassy_visit
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # under_fire should auto-accept
        newly = mgr.update_availability(player.dialogue_flags)
        assert "under_fire" in newly
        assert mgr._status["under_fire"] == MissionStatus.ACTIVE

        # Not complete yet
        completed = mgr.check_objectives(player)
        assert "under_fire" not in completed

        # Simulate forced encounter triggering (sets the flag)
        mission = next(m for m in dl.missions if m.id == "under_fire")
        player.dialogue_flags[mission.forced_encounter.trigger_flag] = True
        completed = mgr.check_objectives(player)
        assert "under_fire" in completed


# ============================================================================
# Chapter 5: Mission 13 — The Favor Returned
# ============================================================================


class TestDexTunnelContactNPC:
    """Tests for Dex Halloran's second appearance as tunnel contact."""

    def test_npc_exists(self) -> None:
        """dex_tunnel_contact NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "dex_tunnel_contact" in dl.npcs

    def test_npc_fields(self) -> None:
        """Dex tunnel contact should reuse Dex's identity at Nexus Prime."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_tunnel_contact"]
        assert npc.name == "Dex Halloran"
        assert npc.home_system_id == "nexus_prime"
        assert npc.dialogue_id == "dex_tunnel_briefing"
        assert npc.portrait_color == (180, 160, 100)

    def test_auto_trigger_config(self) -> None:
        """Should auto-trigger after guild_hardware_discovered flag."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_tunnel_contact"]
        assert npc.auto_trigger_gate_flag == "dex_tunnel_briefing_heard"
        assert "guild_hardware_discovered" in npc.auto_trigger_prerequisites


class TestOrenTakNPC:
    """Tests for Oren Tak, retired miner at Breakstone."""

    def test_npc_exists(self) -> None:
        """oren_tak NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "oren_tak" in dl.npcs

    def test_npc_fields(self) -> None:
        """Oren Tak should be at Breakstone with correct identity."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["oren_tak"]
        assert npc.name == "Oren Tak"
        assert npc.title == "Retired Miner"
        assert npc.home_system_id == "breakstone"
        assert npc.faction_id == "miners_union"
        assert npc.dialogue_id == "oren_tak_meeting"

    def test_auto_trigger_config(self) -> None:
        """Should auto-trigger after ground mission completes."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["oren_tak"]
        assert npc.auto_trigger_gate_flag == "met_oren_tak"
        assert "favor_ground_complete" in npc.auto_trigger_prerequisites


class TestDexTunnelBriefingDialogue:
    """Tests for Dex's tunnel briefing dialogue tree."""

    def test_tree_exists(self) -> None:
        """dex_tunnel_briefing dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "dex_tunnel_briefing" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Tree should start with Dex speaking."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_tunnel_briefing"]
        start = tree.nodes[tree.start_node_id]
        assert start.speaker_id == "dex_halloran"

    def test_sets_briefing_flag(self) -> None:
        """Dialogue should set dex_tunnel_briefing_heard flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_tunnel_briefing"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "dex_tunnel_briefing_heard" in all_flags

    def test_mentions_oren(self) -> None:
        """Dialogue should reference Oren Tak by name."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_tunnel_briefing"]
        all_text = " ".join(n.text for n in tree.nodes.values())
        assert "Oren" in all_text


class TestOrenTakMeetingDialogue:
    """Tests for Oren Tak's meeting dialogue tree."""

    def test_tree_exists(self) -> None:
        """oren_tak_meeting dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "oren_tak_meeting" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Tree should start with Oren speaking."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["oren_tak_meeting"]
        start = tree.nodes[tree.start_node_id]
        assert start.speaker_id == "oren_tak"

    def test_persuasion_check(self) -> None:
        """Should have a Persuasion skill check to gain trust."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["oren_tak_meeting"]
        checks = []
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check:
                    checks.append(resp.skill_check)
        persuasion_checks = [c for c in checks if c.skill == "persuasion"]
        assert len(persuasion_checks) >= 1
        assert persuasion_checks[0].difficulty == 2

    def test_sets_intel_flag_on_success(self) -> None:
        """Successful persuasion path should set oren_intel_received."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["oren_tak_meeting"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "oren_intel_received" in all_flags

    def test_sets_met_flag(self) -> None:
        """Should set met_oren_tak flag (already gate flag, but also in dialogue)."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["oren_tak_meeting"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "met_oren_tak" in all_flags

    def test_mentions_hidden_facility(self) -> None:
        """Oren should reveal information about a hidden facility."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["oren_tak_meeting"]
        all_text = " ".join(n.text for n in tree.nodes.values()).lower()
        assert "facility" in all_text or "iron depths" in all_text


class TestFavorReturnedMission:
    """Tests for the_favor_returned mission definition."""

    def test_mission_exists(self) -> None:
        """the_favor_returned mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "the_favor_returned" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires under_fire."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert "under_fire" in mission.prerequisites

    def test_required_flags(self) -> None:
        """Mission requires dex_tunnel_briefing_heard flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert "dex_tunnel_briefing_heard" in mission.required_flags

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert mission.auto_accept is True

    def test_ground_mission_fields(self) -> None:
        """Mission should have ground mission config for Breakstone."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert mission.ground_mission_id == "mission_13_breakstone_tunnels"
        assert mission.ground_mission_system_id == "breakstone"
        assert mission.ground_mission_complete_flag == "favor_ground_complete"

    def test_objectives(self) -> None:
        """Mission has reach_system + two has_flag objectives."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert len(mission.objectives) == 3
        obj_types = [(o.type, o.target_id) for o in mission.objectives]
        assert (ObjectiveType.REACH_SYSTEM, "breakstone") in obj_types
        assert (ObjectiveType.HAS_FLAG, "favor_ground_complete") in obj_types
        assert (ObjectiveType.HAS_FLAG, "oren_intel_received") in obj_types

    def test_rewards(self) -> None:
        """Mission rewards include XP and discovery flags."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_favor_returned")
        assert any(r.reward_type == "xp" for r in mission.rewards)
        reward_flags = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "favor_returned_complete" in reward_flags
        assert "hidden_facility_discovered" in reward_flags

    def test_mission_completion_flow(self) -> None:
        """Mission completes when ground mission + oren intel both done."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete prerequisite chain
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
            "under_fire",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Need the briefing flag to unlock
        player.dialogue_flags["dex_tunnel_briefing_heard"] = True
        newly = mgr.update_availability(player.dialogue_flags)
        assert "the_favor_returned" in newly
        assert mgr._status["the_favor_returned"] == MissionStatus.ACTIVE

        # Not complete yet — need both flags
        completed = mgr.check_objectives(player)
        assert "the_favor_returned" not in completed

        # Ground mission done but no intel yet
        player.current_system_id = "breakstone"
        player.dialogue_flags["favor_ground_complete"] = True
        completed = mgr.check_objectives(player)
        assert "the_favor_returned" not in completed

        # Intel received — now complete
        player.dialogue_flags["oren_intel_received"] = True
        completed = mgr.check_objectives(player)
        assert "the_favor_returned" in completed


# ============================================================================
# Chapter 5 continued: Mission 14 — Iron Depths
# ============================================================================


class TestSiennaVekNPC:
    """Tests for Sienna Vek, Guild systems engineer at Iron Depths."""

    def test_npc_exists(self) -> None:
        """sienna_vek NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "sienna_vek" in dl.npcs

    def test_npc_fields(self) -> None:
        """Sienna Vek should be at Iron Depths with correct identity."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["sienna_vek"]
        assert npc.name == "Sienna Vek"
        assert npc.title == "Systems Engineer"
        assert npc.home_system_id == "iron_depths"
        assert npc.faction_id == "commerce_guild"
        assert npc.dialogue_id == "sienna_vek_warning"

    def test_auto_trigger_config(self) -> None:
        """Should auto-trigger after Iron Depths ground mission completes."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["sienna_vek"]
        assert npc.auto_trigger_gate_flag == "met_sienna_vek"
        assert "iron_depths_ground_complete" in npc.auto_trigger_prerequisites


class TestSiennaVekDialogue:
    """Tests for Sienna Vek's warning dialogue tree."""

    def test_tree_exists(self) -> None:
        """sienna_vek_warning dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "sienna_vek_warning" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Tree should start with Sienna speaking."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        start = tree.nodes[tree.start_node_id]
        assert start.speaker_id == "sienna_vek"

    def test_has_persuasion_check(self) -> None:
        """Should have a Persuasion check for Sienna to share data."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        checks = []
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.skill_check:
                    checks.append(resp.skill_check)
        persuasion_checks = [c for c in checks if c.skill == "persuasion"]
        assert len(persuasion_checks) >= 1
        assert persuasion_checks[0].difficulty == 3

    def test_sets_intel_flag(self) -> None:
        """Should set facility_intel_gathered flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "facility_intel_gathered" in all_flags

    def test_mentions_singularity(self) -> None:
        """Dialogue should reference singularity or gravitational weapon."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        all_text = " ".join(n.text for n in tree.nodes.values()).lower()
        assert "singularity" in all_text or "gravitational" in all_text

    def test_mentions_guild_leadership(self) -> None:
        """Dialogue should implicate Commerce Guild leadership."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        all_text = " ".join(n.text for n in tree.nodes.values()).lower()
        assert "guild" in all_text

    def test_sets_met_flag(self) -> None:
        """Should set met_sienna_vek flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["sienna_vek_warning"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "met_sienna_vek" in all_flags


class TestIronDepthsMission:
    """Tests for the iron_depths_investigation mission definition."""

    def test_mission_exists(self) -> None:
        """iron_depths_investigation mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "iron_depths_investigation" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires the_favor_returned."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert "the_favor_returned" in mission.prerequisites

    def test_required_flags(self) -> None:
        """Mission requires hidden_facility_discovered flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert "hidden_facility_discovered" in mission.required_flags

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert mission.auto_accept is True

    def test_ground_mission_fields(self) -> None:
        """Mission should have ground mission config for Iron Depths."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert mission.ground_mission_id == "mission_14_iron_depths_facility"
        assert mission.ground_mission_system_id == "iron_depths"
        assert mission.ground_mission_complete_flag == "iron_depths_ground_complete"

    def test_objectives(self) -> None:
        """Mission has reach_system + two has_flag objectives."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert len(mission.objectives) == 3
        obj_types = [(o.type, o.target_id) for o in mission.objectives]
        assert (ObjectiveType.REACH_SYSTEM, "iron_depths") in obj_types
        assert (ObjectiveType.HAS_FLAG, "iron_depths_ground_complete") in obj_types
        assert (ObjectiveType.HAS_FLAG, "facility_intel_gathered") in obj_types

    def test_rewards(self) -> None:
        """Mission rewards include XP and singularity discovery flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "iron_depths_investigation")
        assert any(r.reward_type == "xp" for r in mission.rewards)
        reward_flags = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "iron_depths_complete" in reward_flags
        assert "singularity_weapon_discovered" in reward_flags

    def test_mission_completion_flow(self) -> None:
        """Mission completes when ground mission + facility intel both done."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete prerequisite chain
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
            "under_fire",
            "the_favor_returned",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Need the hidden_facility_discovered flag
        player.dialogue_flags["hidden_facility_discovered"] = True
        newly = mgr.update_availability(player.dialogue_flags)
        assert "iron_depths_investigation" in newly
        assert mgr._status["iron_depths_investigation"] == MissionStatus.ACTIVE

        # Not complete yet
        completed = mgr.check_objectives(player)
        assert "iron_depths_investigation" not in completed

        # Ground mission done but no intel yet
        player.current_system_id = "iron_depths"
        player.dialogue_flags["iron_depths_ground_complete"] = True
        completed = mgr.check_objectives(player)
        assert "iron_depths_investigation" not in completed

        # Intel gathered — now complete
        player.dialogue_flags["facility_intel_gathered"] = True
        completed = mgr.check_objectives(player)
        assert "iron_depths_investigation" in completed


class TestIronDepthsGroundMap:
    """Tests for the Iron Depths facility ground map."""

    def test_campaign_map_loads(self) -> None:
        """mission_14_iron_depths_facility should be in campaign maps."""
        _load_data()
        dl = get_data_loader()
        assert "mission_14_iron_depths_facility" in dl.campaign_ground_maps

    def test_map_dimensions(self) -> None:
        """Map should be 30x25."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_14_iron_depths_facility"]
        assert map_data["width"] == 30
        assert map_data["height"] == 25

    def test_map_difficulty(self) -> None:
        """Map should be moderate difficulty."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_14_iron_depths_facility"]
        assert map_data["difficulty"] == "moderate"

    def test_map_has_enemies(self) -> None:
        """Map should have enemies including guild_security."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_14_iron_depths_facility"]
        enemies = map_data["enemies"]
        assert len(enemies) >= 5
        template_ids = [e["template_id"] for e in enemies]
        assert "guild_security" in template_ids

    def test_map_has_story_triggers(self) -> None:
        """Map should have story triggers describing the facility."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_14_iron_depths_facility"]
        triggers = map_data["story_triggers"]
        assert len(triggers) >= 4

    def test_map_faction(self) -> None:
        """Map faction should be commerce_guild."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_14_iron_depths_facility"]
        assert map_data["faction_id"] == "commerce_guild"


# ============================================================================
# Chapter 5 continued: Mission 15 — The Ledger
# ============================================================================


class TestPriyaAnalystNPC:
    """Tests for Priya's third appearance as data analyst."""

    def test_npc_exists(self) -> None:
        """priya_analyst NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "priya_analyst" in dl.npcs

    def test_npc_fields(self) -> None:
        """Priya analyst should be at Axiom Labs."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["priya_analyst"]
        assert npc.name == "Dr. Priya Osei"
        assert npc.home_system_id == "axiom_labs"
        assert npc.dialogue_id == "priya_convergence_analysis"
        assert npc.faction_id == "science_collective"

    def test_auto_trigger_config(self) -> None:
        """Should auto-trigger after singularity weapon discovered."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["priya_analyst"]
        assert npc.auto_trigger_gate_flag == "convergence_data_verified"
        assert "singularity_weapon_discovered" in npc.auto_trigger_prerequisites


class TestDexFinalLeadNPC:
    """Tests for Dex's third appearance with assembly location."""

    def test_npc_exists(self) -> None:
        """dex_final_lead NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "dex_final_lead" in dl.npcs

    def test_npc_fields(self) -> None:
        """Dex final lead should be at Nexus Prime."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_final_lead"]
        assert npc.name == "Dex Halloran"
        assert npc.home_system_id == "nexus_prime"
        assert npc.dialogue_id == "dex_assembly_intel"
        assert npc.portrait_color == (180, 160, 100)

    def test_auto_trigger_config(self) -> None:
        """Should auto-trigger after convergence data verified."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["dex_final_lead"]
        assert npc.auto_trigger_gate_flag == "assembly_location_known"
        assert "convergence_data_verified" in npc.auto_trigger_prerequisites


class TestPriyaConvergenceDialogue:
    """Tests for Priya's data analysis dialogue tree."""

    def test_tree_exists(self) -> None:
        """priya_convergence_analysis dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "priya_convergence_analysis" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Tree should start with Priya speaking."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["priya_convergence_analysis"]
        start = tree.nodes[tree.start_node_id]
        assert start.speaker_id == "dr_priya_osei"

    def test_sets_verified_flag(self) -> None:
        """Should set convergence_data_verified flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["priya_convergence_analysis"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "convergence_data_verified" in all_flags

    def test_references_political_failure(self) -> None:
        """Dialogue should reference failed attempts to rally factions."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["priya_convergence_analysis"]
        all_text = " ".join(n.text for n in tree.nodes.values()).lower()
        assert "veto" in all_text or "blocked" in all_text or "refused" in all_text

    def test_node_count(self) -> None:
        """Tree should have substantial content."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["priya_convergence_analysis"]
        assert len(tree.nodes) >= 6


class TestDexAssemblyDialogue:
    """Tests for Dex's assembly intel dialogue tree."""

    def test_tree_exists(self) -> None:
        """dex_assembly_intel dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "dex_assembly_intel" in dl.dialogue_trees

    def test_start_node(self) -> None:
        """Tree should start with Dex speaking."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_assembly_intel"]
        start = tree.nodes[tree.start_node_id]
        assert start.speaker_id == "dex_halloran"

    def test_sets_location_flag(self) -> None:
        """Should set assembly_location_known flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_assembly_intel"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "assembly_location_known" in all_flags

    def test_mentions_fulcrum(self) -> None:
        """Dialogue should reference The Fulcrum station."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["dex_assembly_intel"]
        all_text = " ".join(n.text for n in tree.nodes.values())
        assert "Fulcrum" in all_text


class TestLedgerMission:
    """Tests for the_ledger mission definition."""

    def test_mission_exists(self) -> None:
        """the_ledger mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "the_ledger" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires iron_depths_investigation."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        assert "iron_depths_investigation" in mission.prerequisites

    def test_required_flags(self) -> None:
        """Mission requires singularity_weapon_discovered flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        assert "singularity_weapon_discovered" in mission.required_flags

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        assert mission.auto_accept is True

    def test_no_ground_mission(self) -> None:
        """This is a narrative/travel mission with no ground component."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        assert mission.ground_mission_id == ""

    def test_objectives(self) -> None:
        """Mission has two reach_system + two has_flag objectives."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        obj_types = [(o.type, o.target_id) for o in mission.objectives]
        assert (ObjectiveType.REACH_SYSTEM, "axiom_labs") in obj_types
        assert (ObjectiveType.HAS_FLAG, "convergence_data_verified") in obj_types
        assert (ObjectiveType.HAS_FLAG, "assembly_location_known") in obj_types

    def test_rewards(self) -> None:
        """Mission rewards include XP and ledger flags."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_ledger")
        assert any(r.reward_type == "xp" for r in mission.rewards)
        reward_flags = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "ledger_complete" in reward_flags

    def test_mission_completion_flow(self) -> None:
        """Mission completes when data verified + assembly location known."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete prerequisite chain
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
            "under_fire",
            "the_favor_returned",
            "iron_depths_investigation",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Need the singularity flag
        player.dialogue_flags["singularity_weapon_discovered"] = True
        newly = mgr.update_availability(player.dialogue_flags)
        assert "the_ledger" in newly

        # Not complete without both flags
        player.current_system_id = "axiom_labs"
        player.dialogue_flags["convergence_data_verified"] = True
        completed = mgr.check_objectives(player)
        assert "the_ledger" not in completed

        # Assembly location known — complete
        player.dialogue_flags["assembly_location_known"] = True
        completed = mgr.check_objectives(player)
        assert "the_ledger" in completed


# ============================================================================
# Chapter 6: Mission 16 — Point of No Return
# ============================================================================


class TestFulcrumSystem:
    """Tests for The Fulcrum star system."""

    def test_system_exists(self) -> None:
        """the_fulcrum system should exist."""
        _load_data()
        dl = get_data_loader()
        assert "the_fulcrum" in dl.systems

    def test_system_properties(self) -> None:
        """The Fulcrum should be dangerous, deep space."""
        _load_data()
        dl = get_data_loader()
        system = dl.systems["the_fulcrum"]
        assert system.name == "The Fulcrum"
        assert system.danger_level == "dangerous"

    def test_system_has_locations(self) -> None:
        """The Fulcrum should have locations."""
        _load_data()
        dl = get_data_loader()
        assert "the_fulcrum" in dl.locations
        assert len(dl.locations["the_fulcrum"]) >= 2


class TestFulcrumGroundMap:
    """Tests for The Fulcrum ground map."""

    def test_campaign_map_loads(self) -> None:
        """mission_16_the_fulcrum should be in campaign maps."""
        _load_data()
        dl = get_data_loader()
        assert "mission_16_the_fulcrum" in dl.campaign_ground_maps

    def test_map_difficulty(self) -> None:
        """Map should be high difficulty."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_16_the_fulcrum"]
        assert map_data["difficulty"] == "high"

    def test_map_faction(self) -> None:
        """Map faction should be commerce_guild."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_16_the_fulcrum"]
        assert map_data["faction_id"] == "commerce_guild"

    def test_map_has_enemies(self) -> None:
        """Map should have at least 6 enemies including elite guards."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_16_the_fulcrum"]
        enemies = map_data["enemies"]
        assert len(enemies) >= 6
        template_ids = [e["template_id"] for e in enemies]
        assert "elite_guard" in template_ids

    def test_story_triggers_reference_warp_gate(self) -> None:
        """Story triggers should mention the warp gate."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_16_the_fulcrum"]
        all_trigger_text = " ".join(t["text"] for t in map_data["story_triggers"]).lower()
        assert "warp" in all_trigger_text or "gate" in all_trigger_text

    def test_story_triggers_reference_arrays(self) -> None:
        """Story triggers should mention gravitational arrays or convergence."""
        _load_data()
        dl = get_data_loader()
        map_data = dl.campaign_ground_maps["mission_16_the_fulcrum"]
        all_trigger_text = " ".join(t["text"] for t in map_data["story_triggers"]).lower()
        assert "array" in all_trigger_text or "convergence" in all_trigger_text


class TestPointOfNoReturnMission:
    """Tests for the point_of_no_return mission definition."""

    def test_mission_exists(self) -> None:
        """point_of_no_return mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "point_of_no_return" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires the_ledger."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        assert "the_ledger" in mission.prerequisites

    def test_required_flags(self) -> None:
        """Mission requires assembly_location_known flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        assert "assembly_location_known" in mission.required_flags

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        assert mission.auto_accept is True

    def test_ground_mission_fields(self) -> None:
        """Mission should have ground mission config for The Fulcrum."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        assert mission.ground_mission_id == "mission_16_the_fulcrum"
        assert mission.ground_mission_system_id == "the_fulcrum"
        assert mission.ground_mission_complete_flag == "fulcrum_ground_complete"

    def test_objectives(self) -> None:
        """Mission has reach + ground mission + warp gate discovery."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        obj_types = [(o.type, o.target_id) for o in mission.objectives]
        assert (ObjectiveType.REACH_SYSTEM, "the_fulcrum") in obj_types
        assert (ObjectiveType.HAS_FLAG, "fulcrum_ground_complete") in obj_types
        assert (ObjectiveType.HAS_FLAG, "warp_gate_discovered") in obj_types

    def test_rewards(self) -> None:
        """Mission rewards set convergence_active and warp_gate_discovered flags."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "point_of_no_return")
        assert any(r.reward_type == "xp" for r in mission.rewards)
        reward_flags = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "point_of_no_return_complete" in reward_flags
        assert "convergence_active" in reward_flags

    def test_mission_completion_flow(self) -> None:
        """Mission completes when ground mission done + warp gate found."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete prerequisite chain
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
            "under_fire",
            "the_favor_returned",
            "iron_depths_investigation",
            "the_ledger",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Need the assembly_location_known flag
        player.dialogue_flags["assembly_location_known"] = True
        newly = mgr.update_availability(player.dialogue_flags)
        assert "point_of_no_return" in newly

        # Ground mission done
        player.current_system_id = "the_fulcrum"
        player.dialogue_flags["fulcrum_ground_complete"] = True
        completed = mgr.check_objectives(player)
        assert "point_of_no_return" not in completed

        # Warp gate discovered — complete
        player.dialogue_flags["warp_gate_discovered"] = True
        completed = mgr.check_objectives(player)
        assert "point_of_no_return" in completed


# ============================================================================
# Chapter 7: Mission 17 — The Collapse
# ============================================================================


class TestLedgerVanguardEnemy:
    """Tests for the Ledger Vanguard elite enemy template."""

    def test_template_exists(self) -> None:
        """ledger_vanguard enemy template should exist."""
        _load_data()
        dl = get_data_loader()
        assert "ledger_vanguard" in dl.enemy_templates

    def test_vanguard_is_elite(self) -> None:
        """Vanguard should be strongest Ledger enemy."""
        _load_data()
        dl = get_data_loader()
        vanguard = dl.enemy_templates["ledger_vanguard"]
        raider = dl.enemy_templates["ledger_raider"]
        assert vanguard.hull > raider.hull
        assert vanguard.shields > raider.shields

    def test_vanguard_behavior(self) -> None:
        """Vanguard should be aggressive."""
        _load_data()
        dl = get_data_loader()
        from spacegame.models.combat import EnemyBehavior

        vanguard = dl.enemy_templates["ledger_vanguard"]
        assert vanguard.behavior == EnemyBehavior.AGGRESSIVE

    def test_vanguard_has_multiple_moves(self) -> None:
        """Vanguard should have at least 3 combat moves."""
        _load_data()
        dl = get_data_loader()
        vanguard = dl.enemy_templates["ledger_vanguard"]
        assert len(vanguard.moves) >= 3

    def test_vanguard_danger_tier(self) -> None:
        """Vanguard should be dangerous tier."""
        _load_data()
        dl = get_data_loader()
        vanguard = dl.enemy_templates["ledger_vanguard"]
        assert vanguard.danger_tier == "dangerous"


class TestCollapseNPC:
    """Tests for the collapse sequence narrator NPC."""

    def test_npc_exists(self) -> None:
        """collapse_witness NPC should exist."""
        _load_data()
        dl = get_data_loader()
        assert "collapse_witness" in dl.npcs

    def test_npc_at_fulcrum(self) -> None:
        """Collapse narrator should trigger at The Fulcrum."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["collapse_witness"]
        assert npc.home_system_id == "the_fulcrum"
        assert npc.dialogue_id == "the_collapse_sequence"

    def test_auto_trigger_after_combat(self) -> None:
        """Should auto-trigger after escape combat survived."""
        _load_data()
        dl = get_data_loader()
        npc = dl.npcs["collapse_witness"]
        assert npc.auto_trigger_gate_flag == "expanse_collapsed"
        assert "escape_combat_survived" in npc.auto_trigger_prerequisites


class TestCollapseDialogue:
    """Tests for the collapse sequence dialogue tree."""

    def test_tree_exists(self) -> None:
        """the_collapse_sequence dialogue should load."""
        _load_data()
        dl = get_data_loader()
        assert "the_collapse_sequence" in dl.dialogue_trees

    def test_node_count(self) -> None:
        """Tree should have substantial content for the Act 1 climax."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        assert len(tree.nodes) >= 10

    def test_multiple_speakers(self) -> None:
        """Tree should have multiple speakers (crew members)."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        speakers = set(n.speaker_id for n in tree.nodes.values())
        assert len(speakers) >= 3

    def test_sets_collapse_flag(self) -> None:
        """Should set expanse_collapsed flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "expanse_collapsed" in all_flags

    def test_sets_act_one_complete(self) -> None:
        """Should set act_one_complete flag."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        all_flags = set()
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.set_flag:
                    all_flags.add(resp.set_flag)
        assert "act_one_complete" in all_flags

    def test_priya_calibration_branch(self) -> None:
        """Dialogue should have a Priya calibration branch gated by flags."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        # Find responses gated by convergence_data_verified (Priya's analysis)
        priya_gated = []
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.required_flags and "convergence_data_verified" in resp.required_flags:
                    priya_gated.append(resp)
        assert len(priya_gated) >= 1

    def test_alliance_escort_branch(self) -> None:
        """Dialogue should have an Alliance escort branch gated by tomas_friendship."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        alliance_gated = []
        for node in tree.nodes.values():
            for resp in node.responses:
                if resp.required_flags and "tomas_friendship" in resp.required_flags:
                    alliance_gated.append(resp)
        assert len(alliance_gated) >= 1

    def test_references_new_space(self) -> None:
        """Dialogue should reference arriving somewhere new — a glimpse of Act 2."""
        _load_data()
        dl = get_data_loader()
        tree = dl.dialogue_trees["the_collapse_sequence"]
        all_text = " ".join(n.text for n in tree.nodes.values()).lower()
        assert "star" in all_text or "system" in all_text or "galaxy" in all_text


class TestCollapseMission:
    """Tests for the_collapse mission definition."""

    def test_mission_exists(self) -> None:
        """the_collapse mission loads from data."""
        _load_data()
        dl = get_data_loader()
        mission_ids = [m.id for m in dl.missions]
        assert "the_collapse" in mission_ids

    def test_prerequisites(self) -> None:
        """Mission requires point_of_no_return."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        assert "point_of_no_return" in mission.prerequisites

    def test_required_flags(self) -> None:
        """Mission requires convergence_active flag."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        assert "convergence_active" in mission.required_flags

    def test_auto_accept(self) -> None:
        """Mission auto-accepts when available."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        assert mission.auto_accept is True

    def test_forced_encounter(self) -> None:
        """Mission has hostile forced encounter with Ledger forces."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        fe = mission.forced_encounter
        assert fe is not None
        assert fe.encounter_type == "hostile"
        assert "ledger_vanguard" in fe.enemy_template_ids
        assert fe.trigger_flag == "escape_combat_survived"

    def test_objectives(self) -> None:
        """Mission has combat survival + collapse witness objectives."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        obj_flags = [o.target_id for o in mission.objectives if o.type == ObjectiveType.HAS_FLAG]
        assert "escape_combat_survived" in obj_flags
        assert "expanse_collapsed" in obj_flags

    def test_rewards_include_act_complete(self) -> None:
        """Mission rewards should set act_one_complete."""
        _load_data()
        dl = get_data_loader()
        mission = next(m for m in dl.missions if m.id == "the_collapse")
        reward_flags = [r.target_id for r in mission.rewards if r.reward_type == "set_flag"]
        assert "act_one_complete" in reward_flags
        assert "escaped_through_warp_gate" in reward_flags

    def test_mission_completion_flow(self) -> None:
        """Mission completes when combat survived + collapse witnessed."""
        _load_data()
        dl = get_data_loader()
        mgr = MissionManager(dl.missions)
        player = _make_player()

        # Complete full prerequisite chain
        for mid in [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
            "cargo_lost",
            "whispers_at_the_bar",
            "the_crimson_run",
            "embassy_visit",
            "under_fire",
            "the_favor_returned",
            "iron_depths_investigation",
            "the_ledger",
            "point_of_no_return",
        ]:
            mgr._status[mid] = MissionStatus.COMPLETED

        # Need convergence_active flag
        player.dialogue_flags["convergence_active"] = True
        newly = mgr.update_availability(player.dialogue_flags)
        assert "the_collapse" in newly

        # Not complete yet
        completed = mgr.check_objectives(player)
        assert "the_collapse" not in completed

        # Survive combat but haven't witnessed collapse
        player.dialogue_flags["escape_combat_survived"] = True
        completed = mgr.check_objectives(player)
        assert "the_collapse" not in completed

        # Witness the collapse — complete
        player.dialogue_flags["expanse_collapsed"] = True
        completed = mgr.check_objectives(player)
        assert "the_collapse" in completed


class TestActOneFinalCounts:
    """Verify final counts for Act One completion."""

    def test_total_missions(self) -> None:
        """Should have 22 missions (Act One complete)."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.missions) >= 22, (
            f"Expected >= 22 missions, got {len(dl.missions)}: {[m.id for m in dl.missions]}"
        )

    def test_total_npcs(self) -> None:
        """Should have at least 17 NPCs (campaign) + side quest NPCs."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.npcs) >= 17, (
            f"Expected >= 17 NPCs, got {len(dl.npcs)}: {sorted(dl.npcs.keys())}"
        )

    def test_total_dialogues(self) -> None:
        """Should have at least 18 dialogue trees (campaign) + side quest dialogues."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.dialogue_trees) >= 18, (
            f"Expected >= 18 dialogues, got {len(dl.dialogue_trees)}: "
            f"{sorted(dl.dialogue_trees.keys())}"
        )

    def test_total_enemy_templates(self) -> None:
        """42 legacy + 18 B2 balance-pass templates = 60."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.enemy_templates) == 60, (
            f"Expected 60 enemy templates, got {len(dl.enemy_templates)}: "
            f"{sorted(dl.enemy_templates.keys())}"
        )

    def test_total_systems(self) -> None:
        """Should have 11 star systems."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.systems) == 11, (
            f"Expected 11 systems, got {len(dl.systems)}: {sorted(dl.systems.keys())}"
        )

    def test_total_campaign_maps(self) -> None:
        """Should have 5 campaign ground maps."""
        _load_data()
        dl = get_data_loader()
        assert len(dl.campaign_ground_maps) == 5, (
            f"Expected 5 campaign maps, got {len(dl.campaign_ground_maps)}: "
            f"{sorted(dl.campaign_ground_maps.keys())}"
        )

    def test_main_story_mission_chain(self) -> None:
        """The full Act One main story chain should be traversable."""
        _load_data()
        dl = get_data_loader()
        main_chain = [
            "bill_of_landing",
            "iron_delivery",
            "footing_the_bill",
            "union_territory",
            "the_scholars_errand",
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
        ]
        mission_ids = {m.id for m in dl.missions}
        for mid in main_chain:
            assert mid in mission_ids, f"Main story mission {mid} should exist"
