"""Dialogue tree structural integrity tests.

Validates that all dialogue trees have valid node references, no orphan nodes,
reachable terminal paths, and no node-level set_flag (which is silently ignored
by the data loader).
"""

import json
from collections import defaultdict, deque
from pathlib import Path

from spacegame.data_loader import DataLoader

# ---------------------------------------------------------------------------
# Shared loader
# ---------------------------------------------------------------------------

_loader_cache: DataLoader | None = None


def _get_loader() -> DataLoader:
    """Load all game data once and cache."""
    global _loader_cache
    if _loader_cache is None:
        project_root = Path(__file__).parent.parent.parent
        loader = DataLoader(data_dir=project_root / "data")
        loader.load_all()
        _loader_cache = loader
    return _loader_cache


def _get_raw_dialogue_data() -> list[dict]:
    """Load raw dialogue JSON (before parsing) to check for node-level fields
    that the parser silently ignores.
    """
    project_root = Path(__file__).parent.parent.parent
    raw_trees: list[dict] = []
    for filename in ["dialogues.json", "crew_quest_dialogues.json"]:
        filepath = project_root / "data" / "dialogue" / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_trees.extend(data.get("dialogues", []))
    return raw_trees


# ---------------------------------------------------------------------------
# Node reference validation
# ---------------------------------------------------------------------------


class TestDialogueNodeReferences:
    """Every node reference in dialogue trees points to a valid node."""

    def test_start_node_ids_exist(self) -> None:
        """Every dialogue tree's start_node_id exists in its nodes."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            if tree.start_node_id not in tree.nodes:
                errors.append(
                    f"Tree '{tree.id}' start_node_id '{tree.start_node_id}' does not exist in nodes"
                )
        assert not errors, "\n".join(errors)

    def test_response_next_node_ids_valid(self) -> None:
        """Every response next_node_id points to a valid node in the same tree."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            node_ids = set(tree.nodes.keys())
            for node in tree.nodes.values():
                for response in node.responses:
                    if response.next_node_id is not None:
                        if response.next_node_id not in node_ids:
                            errors.append(
                                f"Tree '{tree.id}' node '{node.id}' response "
                                f"'{response.text[:40]}...' references "
                                f"node '{response.next_node_id}' which does not exist"
                            )
        assert not errors, "\n".join(errors)

    def test_skill_check_node_ids_valid(self) -> None:
        """Every skill check success/failure node exists in the same tree."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            node_ids = set(tree.nodes.keys())
            for node in tree.nodes.values():
                for response in node.responses:
                    if response.skill_check:
                        sc = response.skill_check
                        if sc.success_node_id not in node_ids:
                            errors.append(
                                f"Tree '{tree.id}' node '{node.id}' skill check "
                                f"success_node_id '{sc.success_node_id}' "
                                f"does not exist"
                            )
                        if sc.failure_node_id not in node_ids:
                            errors.append(
                                f"Tree '{tree.id}' node '{node.id}' skill check "
                                f"failure_node_id '{sc.failure_node_id}' "
                                f"does not exist"
                            )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Reachability validation
# ---------------------------------------------------------------------------


class TestDialogueReachability:
    """All dialogue nodes are reachable and all paths terminate."""

    def _get_reachable_nodes(self, tree_id: str) -> set[str]:
        """BFS from start_node_id to find all reachable nodes."""
        loader = _get_loader()
        tree = loader.dialogue_trees[tree_id]
        visited: set[str] = set()
        queue: deque[str] = deque()
        if tree.start_node_id in tree.nodes:
            queue.append(tree.start_node_id)
        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            node = tree.nodes.get(node_id)
            if not node:
                continue
            for response in node.responses:
                if response.next_node_id and response.next_node_id not in visited:
                    queue.append(response.next_node_id)
                if response.skill_check:
                    for target in [
                        response.skill_check.success_node_id,
                        response.skill_check.failure_node_id,
                    ]:
                        if target and target not in visited:
                            queue.append(target)
        return visited

    def test_no_orphan_nodes(self) -> None:
        """Every node in a dialogue tree is reachable from start_node_id."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            reachable = self._get_reachable_nodes(tree.id)
            all_nodes = set(tree.nodes.keys())
            orphans = all_nodes - reachable
            if orphans:
                errors.append(f"Tree '{tree.id}' has unreachable nodes: {sorted(orphans)}")
        assert not errors, "\n".join(errors)

    def test_all_paths_terminate(self) -> None:
        """Every dialogue tree has at least one path to a terminal node
        (a node where a response has next_node_id=None).
        """
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            has_terminal = False
            for node in tree.nodes.values():
                if not node.responses:
                    has_terminal = True
                    break
                for response in node.responses:
                    if response.next_node_id is None and not response.skill_check:
                        has_terminal = True
                        break
                if has_terminal:
                    break
            if not has_terminal:
                errors.append(
                    f"Tree '{tree.id}' has no terminal node (no response with next_node_id=None)"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Node-level set_flag detection (silent bug)
# ---------------------------------------------------------------------------


class TestNoNodeLevelSetFlag:
    """Detect set_flag on dialogue nodes (silently ignored by the parser).

    The DialogueNode dataclass has no set_flag field — only DialogueResponse
    does. Any set_flag at the node level in the JSON is silently dropped,
    meaning the flag never gets set during gameplay. This test catches that
    authoring mistake.
    """

    def test_no_node_level_set_flag_in_raw_json(self) -> None:
        """No dialogue node in raw JSON has a set_flag field."""
        raw_trees = _get_raw_dialogue_data()
        errors = []
        for tree in raw_trees:
            for node in tree.get("nodes", []):
                if "set_flag" in node:
                    errors.append(
                        f"Tree '{tree['id']}' node '{node['id']}' has "
                        f"node-level set_flag='{node['set_flag']}' which is "
                        f"silently ignored — move to response level"
                    )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Flag naming consistency
# ---------------------------------------------------------------------------


class TestFlagNamingConsistency:
    """Dialogue flag names follow consistent conventions."""

    def test_flag_names_are_snake_case(self) -> None:
        """All set_flag values in dialogues use snake_case."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            for node in tree.nodes.values():
                for response in node.responses:
                    if response.set_flag:
                        flag = response.set_flag
                        if flag != flag.lower() or " " in flag:
                            errors.append(
                                f"Tree '{tree.id}' node '{node.id}' "
                                f"set_flag '{flag}' is not snake_case"
                            )
                    if response.skill_check:
                        sc = response.skill_check
                        for flag in [sc.set_flag_on_success, sc.set_flag_on_failure]:
                            if flag and (flag != flag.lower() or " " in flag):
                                errors.append(
                                    f"Tree '{tree.id}' node '{node.id}' "
                                    f"skill check flag '{flag}' is not snake_case"
                                )
        assert not errors, "\n".join(errors)

    def test_required_flags_are_snake_case(self) -> None:
        """All required_flags and excluded_flags in responses use snake_case."""
        loader = _get_loader()
        errors = []
        for tree in loader.dialogue_trees.values():
            for node in tree.nodes.values():
                for response in node.responses:
                    for flag in response.required_flags + response.excluded_flags:
                        if flag != flag.lower() or " " in flag:
                            errors.append(
                                f"Tree '{tree.id}' node '{node.id}' flag '{flag}' is not snake_case"
                            )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Writing Bible compliance (SP1 standards)
# ---------------------------------------------------------------------------


class TestWritingBibleCompliance:
    """Validate dialogue content against the Writing Bible standards from SP1."""

    # The 20-expression standard set
    STANDARD_EXPRESSIONS = {
        "neutral",
        "confident",
        "stern",
        "happy",
        "angry",
        "sad",
        "serious",
        "worried",
        "concerned",
        "hopeful",
        "surprised",
        "determined",
        "frustrated",
        "grateful",
        "vulnerable",
        "cautious",
        "relieved",
        "thoughtful",
        "bitter",
        "amused",
    }

    # Banned NPC names
    BANNED_NAMES = {
        "yara",
        "elara",
        "kael",
        "mara",
        "lydia",
        "clive",
        "magnus",
        "ambrose",
    }

    def test_no_banned_npc_names(self) -> None:
        """No NPC uses a banned name from the Writing Bible."""
        loader = _get_loader()
        errors = []
        for npc in loader.npcs.values():
            first_name = npc.name.split()[0].lower() if npc.name else ""
            if first_name in self.BANNED_NAMES:
                errors.append(f"NPC '{npc.id}' uses banned name '{npc.name}'")
        assert not errors, "\n".join(errors)

    def test_dialogue_trees_use_valid_expressions(self) -> None:
        """All expression values are from the standard set or crew quest extended set."""
        loader = _get_loader()
        # Allow crew quest extended expressions alongside standard set
        extended = self.STANDARD_EXPRESSIONS | {
            "bittersweet",
            "brave",
            "business",
            "conflicted",
            "disappointed",
            "emotional",
            "excited",
            "fierce",
            "focused",
            "frank",
            "grim",
            "grim_satisfied",
            "intense",
            "nervous",
            "overjoyed",
            "painful",
            "patient",
            "proud",
            "reflective",
            "resigned",
            "resolute",
            "resolved",
            "satisfied",
            "scheming",
            "shocked",
            "steeled",
            "tense",
            "tired",
            "triumphant",
            "uncertain",
            "urgent",
        }
        errors = []
        for tree in loader.dialogue_trees.values():
            for node in tree.nodes.values():
                if node.expression and node.expression not in extended:
                    errors.append(
                        f"Tree '{tree.id}' node '{node.id}' uses "
                        f"unknown expression '{node.expression}'"
                    )
        assert not errors, "\n".join(errors)

    def test_ai_anti_patterns_in_dialogue_text(self) -> None:
        """No dialogue text contains AI writing anti-patterns."""
        import re

        raw_trees = _get_raw_dialogue_data()
        errors = []
        for tree in raw_trees:
            for node in tree.get("nodes", []):
                text = node.get("text", "")
                tid = f"{tree['id']}/{node['id']}"

                # Em-dash (Unicode)
                if "\u2014" in text:
                    errors.append(f"{tid}: contains Unicode em-dash (U+2014)")

                # "No X, no Y" pattern
                if re.search(r"[Nn]o \w+,\s*no \w+", text):
                    errors.append(f'{tid}: contains "no X, no Y" pattern')

                # "A testament to" cliche
                if "testament to" in text.lower():
                    errors.append(f'{tid}: contains "a testament to"')

                # "Couldn't help but"
                if "couldn't help but" in text.lower():
                    errors.append(f'{tid}: contains "couldn\'t help but"')

                # Check subtext too
                subtext = node.get("subtext", "")
                if subtext:
                    if "\u2014" in subtext:
                        errors.append(f"{tid} subtext: em-dash")
                    if re.search(r"[Nn]o \w+,\s*no \w+", subtext):
                        errors.append(f'{tid} subtext: "no X, no Y"')

        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# QA Pass 2.3 — Bidirectional dialogue flag audit
# ---------------------------------------------------------------------------


def _collect_all_flag_uses() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Walk all data + source and collect (producers, consumers) for every flag.

    Returns a pair of dicts mapping flag_name → set of locations describing
    where it is set / read. A flag is well-formed iff it has at least one
    entry in BOTH dicts (with documented exceptions).

    Producers are detected from:
      - Mission completion (auto-sets ``<mission_id>_complete``)
      - Mission rewards with ``reward_type == "set_flag"``
      - Mission ``on_accept_flags``
      - DialogueResponse ``set_flag``
      - Dialogue node ``set_flags`` arrays in raw JSON
      - Code: any string literal preceded by ``set_flag(``,
        ``dialogue_flags[``, or assigned to ``dialogue_flags["..."] =``

    Consumers are detected from:
      - Mission ``required_flags``, ``forbidden_flags``
      - Dialogue node ``required_flags``, ``forbidden_flags`` (raw JSON)
      - NPC ``required_flags``
      - Encounter ``required_flags`` / dependent fields
      - Chatter ``required_flags``
      - Code: ``has_flag``, ``dialogue_flags.get``, ``not in dialogue_flags``
    """
    import re

    project_root = Path(__file__).parent.parent.parent
    producers: dict[str, set[str]] = defaultdict(set)
    consumers: dict[str, set[str]] = defaultdict(set)

    loader = _get_loader()

    # --- Producers: mission system ---
    for mission in loader.missions:
        producers[f"{mission.id}_complete"].add(f"mission:{mission.id}:auto")
        for flag in getattr(mission, "on_accept_flags", []) or []:
            producers[flag].add(f"mission:{mission.id}:on_accept")
        for reward in mission.rewards:
            if reward.reward_type == "set_flag" and reward.target_id:
                producers[reward.target_id].add(f"mission:{mission.id}:reward")

    # Some mission objectives carry a target_id flag they consume on completion
    # (type=has_flag) — that's a consumer pattern rather than producer.
    for mission in loader.missions:
        for obj in mission.objectives:
            if obj.type.value == "has_flag" and obj.target_id:
                consumers[obj.target_id].add(f"mission:{mission.id}:objective")

    # --- Producers + consumers: dialogue tree responses ---
    for tree in loader.dialogue_trees.values():
        for node in tree.nodes.values():
            for response in node.responses:
                if getattr(response, "set_flag", None):
                    producers[response.set_flag].add(f"dialogue:{tree.id}")
                for flag in getattr(response, "required_flags", []) or []:
                    consumers[flag].add(f"dialogue:{tree.id}:response_required")
                for flag in getattr(response, "forbidden_flags", []) or []:
                    consumers[flag].add(f"dialogue:{tree.id}:response_forbidden")

    # --- Producers: NPC auto_trigger_gate_flag (set on first interaction) ---
    for npc in loader.npcs.values():
        gate = getattr(npc, "auto_trigger_gate_flag", "")
        if gate:
            producers[gate].add(f"npc:{npc.id}:auto_trigger_gate")

    # --- Producers: dynamically-generated crew loyalty threshold flags ---
    # Format: crew_loyalty_<template_id>_{50,70,85}
    for template_id, template in loader.crew_templates.items():
        if getattr(template, "is_companion", False):
            for threshold in (50, 70, 85):
                producers[f"crew_loyalty_{template_id}_{threshold}"].add(
                    f"crew_roster:adjust_loyalty:{template_id}"
                )

    # --- Raw JSON sweep for node-level set_flags + required_flags + forbidden_flags ---
    raw_trees = _get_raw_dialogue_data()
    for tree in raw_trees:
        for node in tree.get("nodes", []):
            for flag in node.get("set_flags", []) or []:
                producers[flag].add(f"dialogue:{tree['id']}:node_set_flags")
            for flag in node.get("required_flags", []) or []:
                consumers[flag].add(f"dialogue:{tree['id']}:node_required")
            for flag in node.get("forbidden_flags", []) or []:
                consumers[flag].add(f"dialogue:{tree['id']}:node_forbidden")

    # --- Consumers: missions ---
    for mission in loader.missions:
        for flag in getattr(mission, "required_flags", []) or []:
            consumers[flag].add(f"mission:{mission.id}:required")
        for flag in getattr(mission, "forbidden_flags", []) or []:
            consumers[flag].add(f"mission:{mission.id}:forbidden")

    # --- Consumers: NPCs ---
    for npc in loader.npcs.values():
        for flag in getattr(npc, "required_flags", []) or []:
            consumers[flag].add(f"npc:{npc.id}")
        # NPC dialogue_states reference flags that gate which tree to use
        for state in getattr(npc, "dialogue_states", []) or []:
            for flag in getattr(state, "required_flags", []) or []:
                consumers[flag].add(f"npc:{npc.id}:state")
            for flag in getattr(state, "forbidden_flags", []) or []:
                consumers[flag].add(f"npc:{npc.id}:state_forbidden")

    # --- Consumers: chatter ---
    for line in loader.station_chatter_lines:
        for flag in getattr(line, "required_flags", []) or []:
            consumers[flag].add(f"chatter:{line.id}")
        for flag in getattr(line, "forbidden_flags", []) or []:
            consumers[flag].add(f"chatter:{line.id}:forbidden")

    # --- Consumers + producers: encounters (raw JSON since model may not preserve all) ---
    encounters_dir = project_root / "data" / "encounters"
    if encounters_dir.exists():
        for jf in encounters_dir.glob("*.json"):
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            for enc in data.get("encounters", []):
                eid = enc.get("id", "?")
                for flag in enc.get("required_flags", []) or []:
                    consumers[flag].add(f"encounter:{eid}")
                # Encounters use both spellings — required_flags AND requires_flags.
                for flag in enc.get("requires_flags", []) or []:
                    consumers[flag].add(f"encounter:{eid}:requires")
                for flag in enc.get("forbidden_flags", []) or []:
                    consumers[flag].add(f"encounter:{eid}:forbidden")
                for flag in enc.get("set_flags", []) or []:
                    producers[flag].add(f"encounter:{eid}")
                # Encounter choices can have outcome.rewards with
                # reward_type=set_flag and target_id pointing to the flag.
                for choice in enc.get("choices", []) or []:
                    outcome = choice.get("outcome", {})
                    for reward in outcome.get("rewards", []) or []:
                        if reward.get("reward_type") == "set_flag":
                            tid = reward.get("target_id")
                            if tid:
                                producers[tid].add(f"encounter:{eid}:reward")
                # Plural variant: outcomes[].actions[]
                for outcome in enc.get("outcomes", []) or []:
                    for action in outcome.get("actions", []) or []:
                        if action.get("type") == "set_flag":
                            tid = action.get("target_id")
                            if tid:
                                producers[tid].add(f"encounter:{eid}:action")

    # --- Code-side scan: any string literal as arg to set_flag / dialogue_flags / has_flag ---
    set_flag_pat = re.compile(r'(?:set_flag|dialogue_flags\[)\s*\(?\s*["\']([a-z_][a-z0-9_]*)["\']')
    consumed_pat = re.compile(
        r'(?:has_flag|dialogue_flags\.get|dialogue_flags\.pop)\s*\(\s*["\']([a-z_][a-z0-9_]*)["\']'
    )
    for py_file in (project_root / "spacegame").rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        rel = str(py_file.relative_to(project_root))
        for m in set_flag_pat.finditer(text):
            producers[m.group(1)].add(f"code:{rel}")
        for m in consumed_pat.finditer(text):
            consumers[m.group(1)].add(f"code:{rel}")

    return producers, consumers


# ---------------------------------------------------------------------------
# Known orphan flags — snapshot from QA Pass 2.3 audit (2026-04-21).
#
# The detector cannot trace every producer/consumer path because some flags
# are set/read through dynamic code (encounter ground-combat completions,
# location triggers, mission-internal flow not modeled in JSON). This list
# freezes the current orphan set so the audit becomes a regression guard:
# if a NEW flag becomes orphaned, the test fails and the author has to either
# wire it up or add it here with a justification.
#
# Each entry should be classified during Pass 5 triage:
#   - REAL BUG: flag is genuinely orphaned, gate never fires
#   - DETECTOR MISS: flag is set/read by a path the audit can't see
# ---------------------------------------------------------------------------

KNOWN_CONSUMER_ONLY_ORPHANS: set[str] = {
    # Note: completed_mission_* flags are set at runtime by game.py's
    # mission-completion handler (Tier 1.1 fix), not by static data. The
    # detector only sees static producers, so these stay listed. If someone
    # adds a reward_type mechanism that sets them declaratively, the
    # stay-meaningful test will catch it and we can clean up.
    "completed_mission_5",
    "completed_mission_10",
    "completed_mission_15",
    "completed_mission_20",
    # `met_torres` was a typo for met_malia_torres (fixed in Tier 1.4) but
    # the typo string itself remains a consumer-only orphan since no encounter
    # uses it anymore — left in case a future author restores the misspelled ref.
    "met_torres",
    # === DETECTOR MISS — set by ground-mission completion (not modeled in JSON) ===
    "crimson_run_ground_complete",
    "deep_core_ground_complete",
    "favor_ground_complete",
    "fulcrum_ground_complete",
    "iron_depths_ground_complete",
    "long_shift_ground_complete",
    # === DETECTOR MISS — set by mission-internal flow (objectives, choices) ===
    "blight_season_resolved",
    "counterfeit_investigated",
    "counterfeit_resolved",
    "deep_core_resolved",
    "escape_combat_survived",
    "informant_resolved",
    "lab_rat_resolved",
    "long_shift_resolved",
    "lost_registry_resolved",
    "miners_plight_resolved",
    "old_debts_delivered",
    "pesticide_acquired",
    "price_of_info_resolved",
    "registry_data_found",
    "scholars_dilemma_resolved",
    "seeds_delivered",
    "signal_amplifier_deployed",
    "signal_from_deep_resolved",
    "stolen_item_recovered",
    "thieves_resolved",
    "two_calls_choice_made",
    "two_calls_resolved",
    "under_fire_ambush",
    "whistleblower_resolved",
    "wrench_request_resolved",
}

# Net producer-only set, regenerated 2026-04-21 from current data state.

# Producer-only orphans are typically narrative-state flags (player-choice
# memory) for save state + future content (Act Two), or transient UI flags.
KNOWN_PRODUCER_ONLY_ORPHANS: set[str] = {
    # === Player-choice memory + Act One ending state ===
    "alliance_followed",
    "alliance_formed",
    "ancient_chamber_discovered",
    "anomaly_coordinates_found",
    "axiom_theta9_scanned",
    "breakstone_permit_earned",
    "completed_mining_tutorial",
    "courier_was_followed",
    "crimson_neutral_status",
    "declined_drifter_deal",
    "defied_ledger_shadow",
    "escaped_through_warp_gate",
    "escorted_priya_axiom",
    "evidence_distributed",
    "evidence_held_reserve",
    "evidence_public",
    "forgery_blackmailed",
    "forgery_exposed",
    "forgery_ignored",
    "fulcrum_relay_located",
    "fulcrum_threshold_intercepted",
    "fulcrum_weapons_scanned",
    "gravity_anomaly_studied",
    "guild_hardware_discovered",
    "has_patrol_data",
    "iron_depths_anomaly_recorded",
    "larsen_warning_heeded",
    "ledger_comm_backbone_found",
    "ledger_manifest_obtained",
    "ledger_routes_mapped",
    "marcus_alternate_inspector",
    "marcus_bribed_inspector",
    "marcus_went_public",
    "margrave_boarded",
    "met_oren_tak",
    "noticed_guild_signal",
    "nova_drone_scanned",
    "nova_kindling_tip",
    "pirate_weapons_evidence",
    "priya_apologized",
    "priya_calibrated_jump",
    "refugee_testimony_recorded",
    "sato_ghost_investigated",
    "sato_shared_intel",
    "section_nine_discovered",
    "shadow_ship_identified",
    "spoke_at_summit",
    "talked_to_voss",
    "tomas_chose_peace",
    "tomas_direct_confrontation",
    "torres_intel_forwarded",
    "visited_axiom_labs",
    "void_drifters_observed",
    "weapons_drop_witnessed",
    # === Lore / discovery flags (collectibles for save state) ===
    "lore_aurelia_found",
    "lore_charter_found",
    "lore_earth_broadcast_heard",
    "lore_earth_song_heard",
    "lore_first_miners_honored",
    "lore_generation_ship_found",
    "lore_pre_colony_probe_found",
    "lore_star_map_analyzed",
    "lore_station_zero_explored",
    "lore_time_capsule_opened",
    # === UI / tutorial transient state ===
    "builder_hint_shapes",
    "builder_hint_tools",
    "builder_module_confirm_seen",
    "builder_module_engine_seen",
    "builder_module_hull_seen",
    "builder_module_requirements_seen",
    "builder_module_welcome_seen",
    "trading_tutorial_sell_pending",
}


class TestDialogueFlagAudit:
    """Every flag should have both a producer and a consumer.

    Current orphans are snapshotted in KNOWN_*_ORPHANS sets. Test fails on
    NET-NEW orphans only — driving a Pass 5 review of each known orphan.
    """

    def test_no_new_consumer_only_flags(self) -> None:
        producers, consumers = _collect_all_flag_uses()
        new_orphans = []
        for flag, locs in consumers.items():
            if flag in producers or flag in KNOWN_CONSUMER_ONLY_ORPHANS:
                continue
            new_orphans.append(f"  {flag} — read at: {sorted(locs)[:3]}")
        assert not new_orphans, (
            f"NEW flags are READ but never SET ({len(new_orphans)}). Either "
            f"wire a producer or add to KNOWN_CONSUMER_ONLY_ORPHANS with a "
            f"REAL BUG / DETECTOR MISS classification:\n"
            + "\n".join(sorted(new_orphans))
        )

    def test_no_new_producer_only_flags(self) -> None:
        producers, consumers = _collect_all_flag_uses()
        new_orphans = []
        for flag, locs in producers.items():
            if flag in consumers or flag in KNOWN_PRODUCER_ONLY_ORPHANS:
                continue
            if flag.endswith("_complete"):
                continue  # Mission completion auto-flags don't need a reader
            new_orphans.append(f"  {flag} — set at: {sorted(locs)[:3]}")
        assert not new_orphans, (
            f"NEW flags are SET but never READ ({len(new_orphans)}). Either "
            f"wire a consumer or add to KNOWN_PRODUCER_ONLY_ORPHANS:\n"
            + "\n".join(sorted(new_orphans))
        )

    def test_known_orphan_lists_stay_meaningful(self) -> None:
        """Sanity check: if a known orphan acquires a producer/consumer,
        remove it from the list so we can spot when bugs get fixed."""
        producers, consumers = _collect_all_flag_uses()
        stale_consumer = [f for f in KNOWN_CONSUMER_ONLY_ORPHANS if f in producers]
        stale_producer = [f for f in KNOWN_PRODUCER_ONLY_ORPHANS if f in consumers]
        msgs = []
        if stale_consumer:
            msgs.append(
                f"These flags are in KNOWN_CONSUMER_ONLY_ORPHANS but now have a "
                f"producer — remove from the set: {sorted(stale_consumer)}"
            )
        if stale_producer:
            msgs.append(
                f"These flags are in KNOWN_PRODUCER_ONLY_ORPHANS but now have a "
                f"consumer — remove from the set: {sorted(stale_producer)}"
            )
        assert not msgs, "\n".join(msgs)
