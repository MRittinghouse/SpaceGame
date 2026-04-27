"""Arna mini-campaign AR-1 + AR-2 regression tests.

Covers the post-Mission-1 pitch, The Ore Tip (M2), Refinement (M3), and
the dialogue state machine that routes Arna to the right conversation
at each step of her arc.
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")


def _dialogues() -> dict:
    with open("data/dialogue/dialogues.json", encoding="utf-8") as f:
        return json.load(f)


def _npcs() -> dict:
    with open("data/characters/npcs.json", encoding="utf-8") as f:
        return json.load(f)


def _missions() -> list[dict]:
    with open("data/missions/side_missions.json", encoding="utf-8") as f:
        return json.load(f)["missions"]


def _tree(tree_id: str) -> dict:
    return next(d for d in _dialogues()["dialogues"] if d["id"] == tree_id)


def _node(tree: dict, node_id: str) -> dict:
    return next(n for n in tree["nodes"] if n["id"] == node_id)


# ---------------------------------------------------------------------------
# Pitch rewrite — arna_post_completion now offers the Ore Tip, not retirement
# ---------------------------------------------------------------------------


class TestPitchRewrite:
    def test_pitch_branches_accept_or_retire(self) -> None:
        tree = _tree("arna_post_completion")
        start = _node(tree, "start")
        response_texts = [r["text"].lower() for r in start["responses"]]
        assert any("tell me" in t for t in response_texts)
        assert any("out" in t for t in response_texts)

    def test_accept_path_sets_accepted_flag(self) -> None:
        """Accepted node must set arna_accepted_ore_tip, not arna_retired."""
        tree = _tree("arna_post_completion")
        accepted = _node(tree, "accepted")
        set_flags = [r.get("set_flag") for r in accepted["responses"]]
        assert "arna_accepted_ore_tip" in set_flags

    def test_retire_early_path_sets_retired(self) -> None:
        """Declining the pitch retires Arna without progressing."""
        tree = _tree("arna_post_completion")
        retire = _node(tree, "retire_early")
        set_flags = [r.get("set_flag") for r in retire["responses"]]
        assert "arna_retired" in set_flags

    def test_catch_node_loops_to_pitch(self) -> None:
        """Asking about the catch should route back to accept/think options."""
        tree = _tree("arna_post_completion")
        catch = _node(tree, "catch")
        next_ids = [r["next_node_id"] for r in catch["responses"]]
        assert "accepted" in next_ids or "think" in next_ids


# ---------------------------------------------------------------------------
# M2 mission: The Ore Tip
# ---------------------------------------------------------------------------


class TestOreTipMission:
    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_02_ore_tip"), None)
        assert m is not None

    def test_gate_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_02_ore_tip")
        assert "arna_accepted_ore_tip" in m["required_flags"]
        assert m["auto_accept"] is True

    def test_objectives_structure(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_02_ore_tip")
        obj_types = [o["type"] for o in m["objectives"]]
        assert "reach_system" in obj_types
        assert "collect_cargo" in obj_types
        assert "talk_to_npc" in obj_types
        # Collect cargo targets rare_metals
        collect = next(o for o in m["objectives"] if o["type"] == "collect_cargo")
        assert collect["target_id"] == "rare_metals"
        assert collect["target_quantity"] == 5

    def test_rewards_set_ore_delivered_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_02_ore_tip")
        flag_rewards = [r for r in m["rewards"] if r["reward_type"] == "set_flag"]
        flags = [r["target_id"] for r in flag_rewards]
        assert "arna_ore_delivered" in flags
        assert "taught_mining" in flags


# ---------------------------------------------------------------------------
# Arna ore-tip interim + return dialogues
# ---------------------------------------------------------------------------


class TestOreTipDialogues:
    def test_pending_dialogue_exists(self) -> None:
        _tree("arna_ore_tip_pending")

    def test_post_ore_tip_dialogue_exists(self) -> None:
        _tree("arna_post_ore_tip")

    def test_post_ore_tip_sends_to_tev(self) -> None:
        """The return conversation must set arna_sent_to_tev, kicking off M3."""
        tree = _tree("arna_post_ore_tip")
        nexts = []
        for node in tree["nodes"]:
            for r in node["responses"]:
                if r.get("set_flag") == "arna_sent_to_tev":
                    nexts.append(node["id"])
        assert nexts  # At least one response sets arna_sent_to_tev


# ---------------------------------------------------------------------------
# Tev NPC + dialogue (AR-2)
# ---------------------------------------------------------------------------


class TestTevNpc:
    def test_npc_defined(self) -> None:
        tev = next((n for n in _npcs()["npcs"] if n["id"] == "tev"), None)
        assert tev is not None
        assert tev["home_system_id"] == "forgeworks"
        assert tev["dialogue_id"] == "tev_refining_intro"

    def test_gated_on_arna_referral(self) -> None:
        """Tev only appears after Arna has sent the player."""
        tev = next(n for n in _npcs()["npcs"] if n["id"] == "tev")
        assert "arna_sent_to_tev" in tev["auto_trigger_prerequisites"]

    def test_hides_after_refining_done(self) -> None:
        tev = next(n for n in _npcs()["npcs"] if n["id"] == "tev")
        assert tev["hide_after_flag"] == "tev_refining_complete"


class TestTevDialogue:
    def test_tree_exists(self) -> None:
        _tree("tev_refining_intro")

    def test_skim_math_beats_present(self) -> None:
        """The dialogue must walk through fee structure — this is the
        dark-humor teaching beat that surfaces Tev's skim without telling
        the player directly."""
        tree = _tree("tev_refining_intro")
        fee_node = _node(tree, "fee_breakdown")
        text = fee_node["text"].lower()
        assert "calibration" in text
        assert "tolerance" in text
        assert "processing" in text

    def test_perception_path_sets_knows_skims(self) -> None:
        """NV-2/3 upgrade: catching the skim now requires passing an
        Observation skill check. The flag moves from direct ``set_flag``
        to ``skill_check.set_flag_on_success``."""
        tree = _tree("tev_refining_intro")
        weigh = _node(tree, "weigh_output")
        flags_set: list[str] = []
        for r in weigh["responses"]:
            if r.get("set_flag"):
                flags_set.append(r["set_flag"])
            sc = r.get("skill_check") or {}
            if sc.get("set_flag_on_success"):
                flags_set.append(sc["set_flag_on_success"])
        assert "knows_tev_skims" in flags_set

    def test_weigh_output_has_observation_check(self) -> None:
        """NV-2/3: knowing Tev skims is gated behind an Observation 2 check,
        not automatically granted to anyone who picks 'weigh the output'."""
        tree = _tree("tev_refining_intro")
        weigh = _node(tree, "weigh_output")
        obs_checks = [
            r
            for r in weigh["responses"]
            if (r.get("skill_check") or {}).get("skill") == "observation"
        ]
        assert len(obs_checks) == 1, "expected one Observation check on weigh_output"
        check = obs_checks[0]["skill_check"]
        assert check["difficulty"] == 2
        assert check["set_flag_on_success"] == "knows_tev_skims"

    def test_weigh_output_subtext_is_ambiguous(self) -> None:
        """NV-2/3: ambiguous subtext — the specific 'second tap' detail is
        reserved for the Observation-check response, not the narrator."""
        tree = _tree("tev_refining_intro")
        weigh = _node(tree, "weigh_output")
        subtext = weigh.get("subtext", "").lower()
        assert "second tap" not in subtext
        assert "calibration" not in subtext

    def test_completion_sets_refining_flag(self) -> None:
        tree = _tree("tev_refining_intro")
        finished = _node(tree, "finished")
        set_flags = [r.get("set_flag") for r in finished["responses"]]
        assert "tev_refining_complete" in set_flags


# ---------------------------------------------------------------------------
# M3 mission: Refinement
# ---------------------------------------------------------------------------


class TestRefinementMission:
    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_03_refinement"), None)
        assert m is not None

    def test_gated_on_sent_to_tev(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_03_refinement")
        assert "arna_sent_to_tev" in m["required_flags"]

    def test_objectives_chain_correctly(self) -> None:
        """M3 objectives: reach Forgeworks, talk to Tev, complete refining,
        return to Arna. All four must be present in the right targets."""
        m = next(x for x in _missions() if x["id"] == "arna_03_refinement")
        targets = [o["target_id"] for o in m["objectives"]]
        assert "forgeworks" in targets
        assert "tev" in targets
        assert "tev_refining_complete" in targets
        assert "arna" in targets

    def test_reward_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_03_refinement")
        flags = [r["target_id"] for r in m["rewards"] if r["reward_type"] == "set_flag"]
        assert "taught_refining" in flags


# ---------------------------------------------------------------------------
# Arna's dialogue_states route correctly across the arc
# ---------------------------------------------------------------------------


class TestArnaStateMachine:
    def _arna(self) -> dict:
        return next(n for n in _npcs()["npcs"] if n["id"] == "arna")

    def test_all_states_present(self) -> None:
        states = {s["state_id"] for s in self._arna()["dialogue_states"]}
        assert "arna_pre_completion" in states
        assert "arna_post_completion" in states
        assert "arna_ore_tip_pending" in states
        assert "arna_post_ore_tip" in states
        assert "arna_post_refining" in states
        assert "arna_retired" in states

    def test_state_exclusions_chain(self) -> None:
        """As the player progresses, later states must exclude earlier
        ones so the first matching state is always the right one."""
        states = self._arna()["dialogue_states"]
        # post_completion excludes arna_accepted_ore_tip (so it doesn't fire
        # after the player accepted M2)
        post_comp = next(s for s in states if s["state_id"] == "arna_post_completion")
        assert "arna_accepted_ore_tip" in post_comp["excluded_flags"]
        # ore_tip_pending excludes ore_delivered (so it doesn't fire post-M2)
        pending = next(s for s in states if s["state_id"] == "arna_ore_tip_pending")
        assert "arna_ore_delivered" in pending["excluded_flags"]
        # post_ore_tip excludes sent_to_tev (fires once, before M3 starts)
        post_ore = next(s for s in states if s["state_id"] == "arna_post_ore_tip")
        assert "arna_sent_to_tev" in post_ore["excluded_flags"]
        # post_refining excludes arranging_buyer (so it fires between M3
        # and M4, but steps aside when M4 kicks off)
        post_ref = next(s for s in states if s["state_id"] == "arna_post_refining")
        assert "arna_arranging_buyer" in post_ref["excluded_flags"]


# ---------------------------------------------------------------------------
# Arna post-refining dialogue: arranges M4 buyer meeting
# ---------------------------------------------------------------------------


class TestPostRefiningDialogue:
    def test_tree_exists(self) -> None:
        _tree("arna_post_refining")

    def test_accusation_path_requires_perception(self) -> None:
        """The 'Tev skimmed you' accusation should be gated on the player
        having actually observed Tev's skim (the knows_tev_skims flag)."""
        tree = _tree("arna_post_refining")
        start = _node(tree, "start")
        accusation = next((r for r in start["responses"] if "skimmed" in r["text"].lower()), None)
        assert accusation is not None
        assert "knows_tev_skims" in accusation.get("required_flags", [])

    def test_sets_arranging_buyer(self) -> None:
        """End of dialogue must transition to M4 by setting arna_arranging_buyer."""
        tree = _tree("arna_post_refining")
        whats_next = _node(tree, "whats_next")
        set_flags = [r.get("set_flag") for r in whats_next["responses"]]
        assert "arna_arranging_buyer" in set_flags


# ---------------------------------------------------------------------------
# Writing Bible compliance
# ---------------------------------------------------------------------------


class TestHeronsMarkSystem:
    """AR-3 authored herons_mark as a new derelict system for the buyer meet."""

    def test_system_exists(self) -> None:
        with open("data/galaxy/systems.json", encoding="utf-8") as f:
            systems = json.load(f)["systems"]
        herons = next((s for s in systems if s["id"] == "herons_mark"), None)
        assert herons is not None
        assert herons["type"] == "derelict"
        # Far from Nexus; on the edge
        assert herons["coordinates"]["y"] < -100

    def test_system_has_minimal_station(self) -> None:
        """Derelict has one station for the player to dock at. No services."""
        with open("data/galaxy/systems.json", encoding="utf-8") as f:
            systems = json.load(f)["systems"]
        herons = next(s for s in systems if s["id"] == "herons_mark")
        assert len(herons["stations"]) == 1
        assert herons["stations"][0]["market_variety"] == "none"


class TestKerenNpc:
    def test_npc_defined(self) -> None:
        keren = next((n for n in _npcs()["npcs"] if n["id"] == "keren"), None)
        assert keren is not None
        assert keren["home_system_id"] == "herons_mark"
        assert keren["dialogue_id"] == "keren_meet"

    def test_gated_on_arna_buyer_arrangement(self) -> None:
        keren = next(n for n in _npcs()["npcs"] if n["id"] == "keren")
        assert "arna_arranging_buyer" in keren["auto_trigger_prerequisites"]

    def test_vanishes_after_ambush(self) -> None:
        """Keren's mission is one-shot; hide_after_flag removes him once combat fires."""
        keren = next(n for n in _npcs()["npcs"] if n["id"] == "keren")
        assert keren["hide_after_flag"] == "keren_escaped"


class TestKerenDialogue:
    def test_tree_exists(self) -> None:
        _tree("keren_meet")

    def test_ernie_beat_present(self) -> None:
        """The 'Ernie' mispronunciation is the signal beat that triggers Arna's
        realization. Must be in the inspect node's text."""
        tree = _tree("keren_meet")
        inspect = _node(tree, "inspect")
        assert "Ernie" in inspect["text"]

    def test_triggers_ambush_flag(self) -> None:
        tree = _tree("keren_meet")
        inspect = _node(tree, "inspect")
        set_flags = [r.get("set_flag") for r in inspect["responses"]]
        assert "keren_ambush_triggered" in set_flags


# ---------------------------------------------------------------------------
# M4 mission: The Buyer
# ---------------------------------------------------------------------------


class TestBuyerMission:
    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_04_the_buyer"), None)
        assert m is not None

    def test_gated_on_arranging_buyer(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_04_the_buyer")
        assert "arna_arranging_buyer" in m["required_flags"]

    def test_has_forced_encounter(self) -> None:
        """M4's ambush fires via forced_encounter when the player travels."""
        m = next(x for x in _missions() if x["id"] == "arna_04_the_buyer")
        fe = m.get("forced_encounter")
        assert fe is not None
        assert fe["encounter_type"] == "hostile"
        assert len(fe["enemy_template_ids"]) == 3  # three Reach operators
        assert all(t == "pirate_scout" for t in fe["enemy_template_ids"])

    def test_objectives_include_travel_chain(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_04_the_buyer")
        targets = [o["target_id"] for o in m["objectives"]]
        assert "herons_mark" in targets
        assert "keren" in targets
        assert "nexus_prime" in targets
        assert "arna" in targets

    def test_rewards_unlock_smuggling(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_04_the_buyer")
        flags = [r["target_id"] for r in m["rewards"] if r["reward_type"] == "set_flag"]
        assert "smuggling_primer_received" in flags
        assert "taught_combat" in flags
        assert "arna_scheme_revealed" in flags
        assert "keren_escaped" in flags

    def test_grants_crimson_reach_black_market_access(self) -> None:
        """M4 rewards include Crimson Reach black market access. Keren was
        the Reach intro — completing the arc means the player now knows
        where Wrecker's Market is. Gives the M5A 'buy a hidden compartment'
        suggestion a concrete, reachable destination."""
        m = next(x for x in _missions() if x["id"] == "arna_04_the_buyer")
        bm_grants = [
            r["target_id"] for r in m["rewards"] if r["reward_type"] == "black_market_access"
        ]
        assert "crimson_reach" in bm_grants


# ---------------------------------------------------------------------------
# Smuggling primer dialogue — the big teaching beat
# ---------------------------------------------------------------------------


class TestSmugglingPrimer:
    def test_post_ambush_tree_exists(self) -> None:
        _tree("arna_post_ambush")

    def test_primer_covers_legality_tiers(self) -> None:
        """Primer must explicitly name the three legality tiers so the
        journal entry and in-game context match."""
        tree = _tree("arna_post_ambush")
        node = _node(tree, "primer_legality")
        text = node["text"].lower()
        assert "legal" in text
        assert "restricted" in text
        assert "illegal" in text

    def test_primer_covers_penalties(self) -> None:
        tree = _tree("arna_post_ambush")
        node = _node(tree, "primer_penalties")
        text = node["text"].lower()
        # All four penalty tiers named
        for penalty in ("warn", "fine", "confiscate", "ban"):
            assert penalty in text, f"penalty '{penalty}' missing from primer"

    def test_primer_covers_inspections_and_heat(self) -> None:
        tree = _tree("arna_post_ambush")
        node = _node(tree, "primer_inspections")
        text = node["text"].lower()
        assert "inspection" in text
        assert "heat" in text

    def test_primer_covers_compartments(self) -> None:
        tree = _tree("arna_post_ambush")
        node = _node(tree, "primer_compartments")
        text = node["text"].lower()
        assert "compartment" in text
        assert "shipyard" in text

    def test_primer_covers_black_market(self) -> None:
        tree = _tree("arna_post_ambush")
        node = _node(tree, "primer_black_market")
        text = node["text"].lower()
        assert "black market" in text


class TestBrotherReveal:
    def test_brother_node_exists(self) -> None:
        tree = _tree("arna_post_ambush")
        brother = _node(tree, "brother")
        text = brother["text"].lower()
        assert "brother" in text
        assert "union" in text or "lungs" in text  # personal stakes


class TestBranchChoice:
    def test_three_branches_offered(self) -> None:
        tree = _tree("arna_post_ambush")
        branches = _node(tree, "branches")
        responses = branches["responses"]
        # Three branches: payback, walkaway, betray
        assert len(responses) == 3

    def test_each_branch_sets_unique_flag(self) -> None:
        tree = _tree("arna_post_ambush")
        # Collect set_flag from the three choice-node responses
        branch_flags = set()
        for node_id in ("chose_payback", "chose_walkaway", "chose_betray"):
            node = _node(tree, node_id)
            for r in node["responses"]:
                sf = r.get("set_flag")
                if sf:
                    branch_flags.add(sf)
        assert "arna_branch_payback" in branch_flags
        assert "arna_branch_walkaway" in branch_flags
        assert "arna_branch_betray" in branch_flags


class TestJournalEntries:
    def _entries(self) -> list[dict]:
        with open("data/journal/entries.json", encoding="utf-8") as f:
            return json.load(f)["journal_entries"]

    def test_smuggling_primer_entry_exists(self) -> None:
        entries = self._entries()
        primer = next((e for e in entries if e["entry_id"] == "auto_arna_smuggling_primer"), None)
        assert primer is not None
        assert primer["trigger_flag"] == "smuggling_primer_received"

    def test_primer_entry_covers_teaching_content(self) -> None:
        """Journal primer must cover the same teaching ground as the dialogue
        so the player can re-read after the dialogue closes."""
        entries = self._entries()
        primer = next(e for e in entries if e["entry_id"] == "auto_arna_smuggling_primer")
        text = primer["text"].lower()
        # Same teaching surface as the dialogue
        assert "legal" in text and "restricted" in text and "illegal" in text
        assert "warn" in text and "fine" in text and "confiscate" in text
        assert "compartment" in text
        assert "black market" in text
        assert "heat" in text

    def test_brother_reveal_entry_exists(self) -> None:
        entries = self._entries()
        brother = next((e for e in entries if e["entry_id"] == "auto_arna_brother_reveal"), None)
        assert brother is not None
        assert brother["trigger_flag"] == "arna_scheme_revealed"


class TestArnaStateMachineAR3:
    """Arna's state machine now includes arna_post_ambush. Verify ordering
    and exclusions so the right state fires at each point in the arc."""

    def test_post_ambush_state_exists(self) -> None:
        arna = next(n for n in _npcs()["npcs"] if n["id"] == "arna")
        states = {s["state_id"] for s in arna["dialogue_states"]}
        assert "arna_post_ambush" in states

    def test_post_ambush_excludes_branch_flags(self) -> None:
        """Once a branch is chosen, post_ambush should not re-fire."""
        arna = next(n for n in _npcs()["npcs"] if n["id"] == "arna")
        post_ambush = next(
            s for s in arna["dialogue_states"] if s["state_id"] == "arna_post_ambush"
        )
        excluded = set(post_ambush["excluded_flags"])
        assert "arna_branch_payback" in excluded
        assert "arna_branch_walkaway" in excluded
        assert "arna_branch_betray" in excluded

    def test_post_refining_excludes_ambush(self) -> None:
        """Post_refining should step aside when the ambush has fired."""
        arna = next(n for n in _npcs()["npcs"] if n["id"] == "arna")
        post_refining = next(
            s for s in arna["dialogue_states"] if s["state_id"] == "arna_post_refining"
        )
        assert "keren_ambush_triggered" in post_refining["excluded_flags"]


class TestPaybackBranch:
    """M5A 'Last Freight Out' — payback + harder combat + salvage + contraband."""

    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_05a_last_freight_out"), None)
        assert m is not None

    def test_gated_on_payback_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_05a_last_freight_out")
        assert "arna_branch_payback" in m["required_flags"]

    def test_harder_combat_encounter(self) -> None:
        """M5A combat must be tougher than M4's. M4 was 3 pirate_scout;
        M5A adds a pirate_raider (harder template)."""
        m = next(x for x in _missions() if x["id"] == "arna_05a_last_freight_out")
        fe = m.get("forced_encounter")
        assert fe is not None
        assert "pirate_raider" in fe["enemy_template_ids"]

    def test_rewards_include_salvage_and_smuggling(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_05a_last_freight_out")
        flags = [r["target_id"] for r in m["rewards"] if r["reward_type"] == "set_flag"]
        assert "taught_salvage" in flags
        assert "taught_smuggling" in flags
        assert "arna_branch_a_complete" in flags
        assert "reach_hunts_player" in flags

    def test_payback_pays_more_than_walkaway(self) -> None:
        """Risk should be rewarded: payback credits > walkaway credits."""
        mp = next(x for x in _missions() if x["id"] == "arna_05a_last_freight_out")
        mw = next(x for x in _missions() if x["id"] == "arna_05b_clean_pull")
        p = next(r["amount"] for r in mp["rewards"] if r["reward_type"] == "credits")
        w = next(r["amount"] for r in mw["rewards"] if r["reward_type"] == "credits")
        assert p > w


class TestWalkawayBranch:
    """M5B 'The Clean Pull' — solo salvage, no combat, smaller reward."""

    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_05b_clean_pull"), None)
        assert m is not None

    def test_gated_on_walkaway_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_05b_clean_pull")
        assert "arna_branch_walkaway" in m["required_flags"]

    def test_no_forced_encounter(self) -> None:
        """Walkaway is meant to be quiet — no combat."""
        m = next(x for x in _missions() if x["id"] == "arna_05b_clean_pull")
        assert "forced_encounter" not in m

    def test_destination_havens_rest(self) -> None:
        """Arna's clean coordinates point to Havens Rest space (safe frontier)."""
        m = next(x for x in _missions() if x["id"] == "arna_05b_clean_pull")
        targets = [o["target_id"] for o in m["objectives"]]
        assert "havens_rest" in targets

    def test_salvage_collect_objective(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_05b_clean_pull")
        collect = next((o for o in m["objectives"] if o["type"] == "collect_cargo"), None)
        assert collect is not None
        assert collect["target_id"] == "scrap_metal"


class TestBetrayalBranch:
    """M5C 'Clean Paper' — betrayal, no combat, moral consequence."""

    def test_mission_exists(self) -> None:
        m = next((x for x in _missions() if x["id"] == "arna_05c_clean_paper"), None)
        assert m is not None

    def test_gated_on_betray_flag(self) -> None:
        m = next(x for x in _missions() if x["id"] == "arna_05c_clean_paper")
        assert "arna_branch_betray" in m["required_flags"]

    def test_no_travel_outside_nexus(self) -> None:
        """Betrayal is a Nexus-local mission. No outbound travel."""
        m = next(x for x in _missions() if x["id"] == "arna_05c_clean_paper")
        reach_targets = [o["target_id"] for o in m["objectives"] if o["type"] == "reach_system"]
        assert reach_targets == ["nexus_prime"]

    def test_bounty_payout(self) -> None:
        """M5C pays a bounty for turning Arna in. AR-5: moderate payout
        (800 CR) — less than Branch A's 3,500 score, more than Branch B's
        1,200 clean pull. Betrayal is transactional, not heroic."""
        m = next(x for x in _missions() if x["id"] == "arna_05c_clean_paper")
        credits = next((r["amount"] for r in m["rewards"] if r["reward_type"] == "credits"), 0)
        assert 500 <= credits <= 1200, f"M5C bounty should be 500-1200, got {credits}"


class TestBranchFollowThroughDialogues:
    def test_post_payback_tree(self) -> None:
        tree = _tree("arna_post_payback")
        # Two initial paths — killed vs spared
        start = _node(tree, "start")
        response_ids = [r["next_node_id"] for r in start["responses"]]
        assert "gone" in response_ids
        assert "spared" in response_ids

    def test_post_walkaway_tree(self) -> None:
        tree = _tree("arna_post_walkaway")
        # Confirms Arna's decision to stay at Nexus
        what_next = _node(tree, "what_next")
        text = what_next["text"].lower()
        assert "manifest desk" in text or "staying" in text

    def test_betray_followthrough_offers_two_sub_paths(self) -> None:
        """Player chooses security OR Reach inside the betrayal dialogue."""
        tree = _tree("arna_betray_followthrough")
        ask = _node(tree, "ask")
        response_ids = [r["next_node_id"] for r in ask["responses"]]
        assert "security" in response_ids
        assert "reach" in response_ids

    def test_betray_both_sub_paths_resolve(self) -> None:
        tree = _tree("arna_betray_followthrough")
        for node_id in ("security", "reach"):
            node = _node(tree, node_id)
            set_flags = [r.get("set_flag") for r in node["responses"]]
            assert "arna_betrayal_resolved" in set_flags

    def test_post_payback_sets_closeout_ready(self) -> None:
        tree = _tree("arna_post_payback")
        what_now = _node(tree, "what_now")
        set_flags = [r.get("set_flag") for r in what_now["responses"]]
        assert "arna_closeout_ready" in set_flags

    def test_post_walkaway_sets_closeout_ready(self) -> None:
        tree = _tree("arna_post_walkaway")
        what_next = _node(tree, "what_next")
        set_flags = [r.get("set_flag") for r in what_next["responses"]]
        assert "arna_closeout_ready" in set_flags


class TestArnaStateMachineAR4:
    """Arna's state machine now covers all three branches' follow-through."""

    def _arna(self) -> dict:
        return next(n for n in _npcs()["npcs"] if n["id"] == "arna")

    def test_all_branch_states_present(self) -> None:
        states = {s["state_id"] for s in self._arna()["dialogue_states"]}
        assert "arna_post_payback" in states
        assert "arna_post_walkaway" in states
        assert "arna_betray_followthrough" in states

    def test_post_payback_excludes_closeout(self) -> None:
        states = self._arna()["dialogue_states"]
        post = next(s for s in states if s["state_id"] == "arna_post_payback")
        assert "arna_closeout_ready" in post["excluded_flags"]

    def test_post_walkaway_excludes_closeout(self) -> None:
        states = self._arna()["dialogue_states"]
        post = next(s for s in states if s["state_id"] == "arna_post_walkaway")
        assert "arna_closeout_ready" in post["excluded_flags"]

    def test_betray_excludes_resolved(self) -> None:
        """Once the player closes the loop, betray dialogue stops firing."""
        states = self._arna()["dialogue_states"]
        bet = next(s for s in states if s["state_id"] == "arna_betray_followthrough")
        assert "arna_betrayal_resolved" in bet["excluded_flags"]


class TestAR4JournalEntries:
    def _entries(self) -> list[dict]:
        with open("data/journal/entries.json", encoding="utf-8") as f:
            return json.load(f)["journal_entries"]

    def test_branch_a_entry(self) -> None:
        e = next((x for x in self._entries() if x["entry_id"] == "auto_arna_branch_a"), None)
        assert e is not None
        assert e["trigger_flag"] == "arna_branch_a_complete"

    def test_branch_b_entry(self) -> None:
        e = next((x for x in self._entries() if x["entry_id"] == "auto_arna_branch_b"), None)
        assert e is not None
        assert e["trigger_flag"] == "arna_branch_b_complete"

    def test_branch_c_entry(self) -> None:
        e = next((x for x in self._entries() if x["entry_id"] == "auto_arna_branch_c"), None)
        assert e is not None
        assert e["trigger_flag"] == "arna_betrayal_resolved"


class TestAR5ClosingClosures:
    """AR-5: the three branches close cleanly with matching closeout dialogues
    (Branch A gets the pendant reveal + departure; Branch B gets the quiet
    'I'm staying' beat; Branch C has no dialogue, handled by journal)."""

    def test_last_freight_out_closeout_exists(self) -> None:
        _tree("arna_last_freight_out_closeout")

    def test_stays_closeout_exists(self) -> None:
        _tree("arna_stays_closeout")

    def test_last_freight_out_reveals_pendant_truth(self) -> None:
        """The three-wrong-stories pendant thread resolves with the real answer."""
        tree = _tree("arna_last_freight_out_closeout")
        reveal = _node(tree, "pendant_truth")
        text = reveal["text"].lower()
        assert "mother" in text
        # The truth — not brother, not lover, not market (the three prior lies)
        assert "not my brother" in text or "not a lover" in text

    def test_last_freight_out_sets_both_flags(self) -> None:
        """Pendant reveal path sets arna_pendant_revealed (drives journal).
        Departure response sets arna_gone_from_nexus (hides the NPC)."""
        tree = _tree("arna_last_freight_out_closeout")
        why_now = _node(tree, "why_now")
        farewell = _node(tree, "farewell")
        why_flags = [r.get("set_flag") for r in why_now["responses"]]
        farewell_flags = [r.get("set_flag") for r in farewell["responses"]]
        assert "arna_pendant_revealed" in why_flags
        assert "arna_gone_from_nexus" in farewell_flags

    def test_stays_closeout_offer_declined(self) -> None:
        """Player can offer Arna a crew slot; she declines narratively."""
        tree = _tree("arna_stays_closeout")
        offer_decline = _node(tree, "offer_decline")
        text = offer_decline["text"].lower()
        # Her decline must name the reason (Nexus is home, brother)
        assert "nexus" in text
        assert "brother" in text

    def test_stays_closeout_sets_retired(self) -> None:
        tree = _tree("arna_stays_closeout")
        farewell = _node(tree, "farewell")
        flags = [r.get("set_flag") for r in farewell["responses"]]
        assert "arna_retired" in flags


class TestArnaHideLogic:
    """Arna hides from the concourse once she has left (Branch A) or been
    arrested (Branch C). Branch B she stays but routes to the retired state."""

    def test_hide_after_flag_set(self) -> None:
        arna = next(n for n in _npcs()["npcs"] if n["id"] == "arna")
        assert arna.get("hide_after_flag") == "arna_gone_from_nexus"

    def test_m5c_sets_gone_flag(self) -> None:
        """Branch C's mission reward must set arna_gone_from_nexus so she
        actually disappears from the concourse after arrest."""
        m = next(x for x in _missions() if x["id"] == "arna_05c_clean_paper")
        flags = [r["target_id"] for r in m["rewards"] if r["reward_type"] == "set_flag"]
        assert "arna_gone_from_nexus" in flags

    def test_closeout_states_ordering(self) -> None:
        """Closeout states must fire BEFORE the branch follow-through states
        once arna_closeout_ready is set, so the player gets the final scene
        instead of re-seeing the post-branch dialogue."""
        arna = next(n for n in _npcs()["npcs"] if n["id"] == "arna")
        state_order = [s["state_id"] for s in arna["dialogue_states"]]
        # Closeouts must come before post-branch follow-throughs
        a_closeout_idx = state_order.index("arna_last_freight_out_closeout")
        a_post_idx = state_order.index("arna_post_payback")
        b_closeout_idx = state_order.index("arna_stays_closeout")
        b_post_idx = state_order.index("arna_post_walkaway")
        assert a_closeout_idx < a_post_idx
        assert b_closeout_idx < b_post_idx


class TestOdomPostArc:
    """Odom gets one cold line per Arna branch. The seventy-credit debt is
    the thread. Each branch variant fires exactly once."""

    def test_all_three_branches_have_odom_node(self) -> None:
        tree = _tree("merchant_delivery")
        node_ids = [n["id"] for n in tree["nodes"]]
        assert "odom_arna_branch_a" in node_ids
        assert "odom_arna_branch_b" in node_ids
        assert "odom_arna_branch_c" in node_ids

    def test_each_branch_references_seventy_credits(self) -> None:
        """The recurring debt beat — Odom is owed seventy credits regardless
        of Arna's fate. That's the joke and the epitaph."""
        tree = _tree("merchant_delivery")
        for node_id in ("odom_arna_branch_a", "odom_arna_branch_b", "odom_arna_branch_c"):
            node = _node(tree, node_id)
            text = node["text"].lower()
            assert "seventy credits" in text, f"missing debt reference in {node_id}"

    def test_odom_responses_are_branch_gated(self) -> None:
        """Only the branch-matching response shows in Odom's greet."""
        tree = _tree("merchant_delivery")
        greet = _node(tree, "greet")
        arna_responses = [r for r in greet["responses"] if "Arna" in r["text"]]
        assert len(arna_responses) == 3
        required_sets = [tuple(sorted(r.get("required_flags", []))) for r in arna_responses]
        # Each response requires exactly its branch's complete flag
        assert ("arna_branch_a_complete",) in required_sets
        assert ("arna_branch_b_complete",) in required_sets
        assert ("arna_branch_c_complete",) in required_sets

    def test_odom_response_one_shot(self) -> None:
        """Odom's Arna line only fires once per playthrough."""
        tree = _tree("merchant_delivery")
        for node_id in ("odom_arna_branch_a", "odom_arna_branch_b", "odom_arna_branch_c"):
            node = _node(tree, node_id)
            flags = [r.get("set_flag") for r in node["responses"]]
            assert "odom_spoke_of_arna" in flags


class TestAR5JournalEntries:
    def _entries(self) -> list[dict]:
        with open("data/journal/entries.json", encoding="utf-8") as f:
            return json.load(f)["journal_entries"]

    def test_departure_entry_exists(self) -> None:
        e = next((x for x in self._entries() if x["entry_id"] == "auto_arna_departure"), None)
        assert e is not None

    def test_departure_entry_gated_on_pendant_reveal(self) -> None:
        """Journal entry must only fire for Branch A (pendant revealed),
        not Branch C where the player never saw the pendant reveal."""
        e = next(x for x in self._entries() if x["entry_id"] == "auto_arna_departure")
        assert e["trigger_flag"] == "arna_pendant_revealed"

    def test_departure_entry_mentions_brother_still_waiting(self) -> None:
        """The gut-punch line: the brother Arna was trying to save is still
        waiting. She never wrote the letter. Journal captures it."""
        e = next(x for x in self._entries() if x["entry_id"] == "auto_arna_departure")
        text = e["text"].lower()
        assert "brother" in text
        assert "waiting" in text


class TestWritingBibleCompliance:
    """All new dialogue bodies must be Writing Bible clean."""

    def _all_new_dialogue_text(self) -> list[str]:
        texts = []
        new_trees = [
            "arna_post_completion",  # rewritten for AR-1
            "arna_ore_tip_pending",
            "arna_post_ore_tip",
            "tev_refining_intro",
            "arna_post_refining",
            "keren_meet",
            "arna_post_ambush",
            "arna_post_payback",
            "arna_post_walkaway",
            "arna_betray_followthrough",
            "arna_last_freight_out_closeout",
            "arna_stays_closeout",
        ]
        for tid in new_trees:
            tree = _tree(tid)
            for node in tree["nodes"]:
                texts.append(node.get("text", ""))
                texts.append(node.get("subtext", ""))
                for r in node["responses"]:
                    texts.append(r.get("text", ""))
        return texts

    def test_no_em_dashes(self) -> None:
        for t in self._all_new_dialogue_text():
            assert "\u2014" not in t, f"em-dash: {t!r}"

    def test_no_ai_tells(self) -> None:
        banned = ["couldn't help but", "a testament to"]
        for t in self._all_new_dialogue_text():
            low = t.lower()
            for phrase in banned:
                assert phrase not in low, f"banned phrase '{phrase}' in: {t!r}"
