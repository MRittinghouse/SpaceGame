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
                # Flags set via skill_check pass/fail branches are producers too.
                sc = getattr(response, "skill_check", None)
                if sc is not None:
                    if getattr(sc, "set_flag_on_success", None):
                        producers[sc.set_flag_on_success].add(
                            f"dialogue:{tree.id}:skill_check_success"
                        )
                    if getattr(sc, "set_flag_on_failure", None):
                        producers[sc.set_flag_on_failure].add(
                            f"dialogue:{tree.id}:skill_check_failure"
                        )
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

    # --- Consumers: ambient dialogue (CB-2) ---
    for i, line in enumerate(loader.ambient_lines):
        for flag in getattr(line, "required_flags", []) or []:
            consumers[flag].add(f"ambient:{i}:{line.crew_id}")
        for flag in getattr(line, "excluded_flags", []) or []:
            consumers[flag].add(f"ambient:{i}:{line.crew_id}:excluded")

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
    # Helper-routed accesses: SI-3 migrates flag strings behind helpers in
    # ``spacegame/constants/flags.py`` so producers/consumers share the
    # canonical prefix. Each helper looks like
    # ``def met_npc(npc_id): return f"met_{npc_id}"``. Discover the prefix
    # at runtime so the scanner stays in sync without per-migration edits.
    helper_patterns = _helper_access_patterns()

    for py_file in (project_root / "spacegame").rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        rel = str(py_file.relative_to(project_root))
        for m in set_flag_pat.finditer(text):
            producers[m.group(1)].add(f"code:{rel}")
        for m in consumed_pat.finditer(text):
            consumers[m.group(1)].add(f"code:{rel}")
        for prefix, suffix, producer_re, consumer_re, is_parameterized in helper_patterns:
            for m in producer_re.finditer(text):
                if is_parameterized:
                    arg = m.group(1) or m.group(2)
                    full_flag = f"{prefix}{arg}{suffix}"
                else:
                    full_flag = prefix
                producers[full_flag].add(f"code:{rel}")
            for m in consumer_re.finditer(text):
                if is_parameterized:
                    arg = m.group(1) or m.group(2)
                    full_flag = f"{prefix}{arg}{suffix}"
                else:
                    full_flag = prefix
                consumers[full_flag].add(f"code:{rel}")

    return producers, consumers


def _helper_access_patterns() -> list[tuple[str, str, "re.Pattern[str]", "re.Pattern[str]", bool]]:
    """Build (prefix, suffix, producer_re, consumer_re, is_parameterized) for each
    helper in ``spacegame.constants.flags``.

    Discovery is runtime-introspective using ``inspect.signature``:

    - **No-arg helpers** (zero parameters): call ``obj()`` to get the flag string.
      Entry is ``(flag_string, "", producer_re, consumer_re, False)``.
    - **Parameterized helpers**: call with a sentinel value; if it returns a
      string containing the sentinel, the prefix is text before the substitution
      and the suffix is text after. Entry is
      ``(prefix, suffix, producer_re, consumer_re, True)``.

    The ``is_parameterized`` bool tells the consumer loop whether to extract a
    capture group (True) or use the prefix directly (False).

    Both producer and consumer regexes match the local-alias rebinding pattern
    ``flags = self.player.dialogue_flags`` that views use for legibility:
      - producer: ``(?:dialogue_)?flags[helper(...)] = ...``
      - consumer: ``(?:has_flag|(?:dialogue_)?flags.get|(?:dialogue_)?flags.pop)(helper(...))``
    """
    import inspect
    import re as _re

    from spacegame.constants import flags

    patterns: list[tuple[str, str, _re.Pattern[str], _re.Pattern[str], bool]] = []
    string_sentinel = "__SI3_FLAG_SENTINEL__"
    int_sentinel = 123456789
    arg_pat = r'["\']([a-z_][a-z0-9_]*)["\']|(\d+)'

    for name, obj in inspect.getmembers(flags):
        if name.startswith(("_", "extract_")):
            continue
        if not callable(obj):
            continue
        params = inspect.signature(obj).parameters
        if len(params) == 0:
            # No-arg helper: flag string is a constant; call once to retrieve it.
            try:
                result = obj()
            except Exception:
                continue
            if not isinstance(result, str):
                continue
            helper_call = rf"{_re.escape(name)}\(\s*\)"
            producer_re = _re.compile(rf"(?:dialogue_)?flags\[\s*{helper_call}\s*\]\s*=")
            consumer_re = _re.compile(
                rf"(?:has_flag|(?:dialogue_)?flags\.get|(?:dialogue_)?flags\.pop)"
                rf"\(\s*{helper_call}"
            )
            patterns.append((result, "", producer_re, consumer_re, False))
        else:
            # Parameterized helper: discover prefix/suffix via sentinel substitution.
            prefix: str | None = None
            suffix: str = ""
            for sentinel in (string_sentinel, int_sentinel):
                try:
                    result = obj(sentinel)
                except Exception:
                    continue
                if isinstance(result, str) and str(sentinel) in result:
                    idx = result.index(str(sentinel))
                    prefix = result[:idx]
                    suffix = result[idx + len(str(sentinel)) :]
                    break
            if prefix is None:
                continue
            helper_call = rf"{_re.escape(name)}\(\s*(?:{arg_pat})\s*\)"
            producer_re = _re.compile(rf"(?:dialogue_)?flags\[\s*{helper_call}\s*\]\s*=")
            consumer_re = _re.compile(
                rf"(?:has_flag|(?:dialogue_)?flags\.get|(?:dialogue_)?flags\.pop)"
                rf"\(\s*{helper_call}"
            )
            patterns.append((prefix, suffix, producer_re, consumer_re, True))
    return patterns


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
    # === SA-R2 DETECTOR MISS — set via _LEGACY_ARC_TREE_TO_FLAG dispatch ===
    # ``okafor_legacy_heal_pattern_seen`` is SET by the OkaforView
    # ``_close_active_dialogue`` close-handler, which looks up the flag name
    # from the ``_LEGACY_ARC_TREE_TO_FLAG`` module-level dict and writes it via
    # ``player.dialogue_flags[flag] = True``. The scanner only detects
    # string-literal assignments and misses variable-mediated ones.
    # Real consumer: ``mission:okafor_legacy_clinic_run:required``.
    "okafor_legacy_heal_pattern_seen",
    # === SA-R3 DETECTOR MISS — set via _LEGACY_ARC_TREE_TO_FLAG variable dispatch ===
    # ``okafor_legacy_clinic_callback_seen`` is SET by OkaforView._close_active_dialogue
    # through the same _LEGACY_ARC_TREE_TO_FLAG mechanism as okafor_legacy_heal_pattern_seen
    # above (variable-mediated ``player.dialogue_flags[seen_flag] = True``).
    # Consumer: OkaforView._kweon_dialogue_id() routing guard — now detected by the
    # SI3-FOLLOW-1 no-arg consumer regex. Producer remains a scanner blind spot.
    "okafor_legacy_clinic_callback_seen",
}

# Net producer-only set, regenerated 2026-04-21 from current data state.

# Producer-only orphans are typically narrative-state flags (player-choice
# memory) for save state + future content (Act Two), or transient UI flags.
KNOWN_PRODUCER_ONLY_ORPHANS: set[str] = {
    # === Player-choice memory + Act One ending state ===
    "alliance_followed",
    # Set on reva_distress Persuasion 2 success. Pre-existing narrative
    # reward flag exposed when NV-2/3 extended the scanner to walk
    # skill_check.set_flag_on_success. Not currently read by any consumer.
    "reva_shared_patrol_data",
    # === NV-7 skill-check success flags ===
    # Set by NV-7 skill checks to record that the player caught a specific
    # tell or took a specific action. These are "insight flags" — they
    # preserve narrative memory for potential future content to consume
    # (closeout variants, crew recognition lines, later-scene callbacks).
    # Flags stay in the allowlist until a consumer is authored.
    "read_arna_contact_hedge",
    "read_arna_weighing",
    "saw_keren_tell",
    "took_command_post_ambush",
    "read_elena_navigator",
    "read_elena_grounded",
    "read_marcus_recognition",
    "read_marcus_engineer",
    "read_priya_sample_urgency",
    "named_father_to_priya",
    "proposed_manifest_split",
    "bluffed_larsen",
    "offered_voss_real_load",
    "leaned_on_voss",
    "pressed_reva_cold",
    "spotted_auditor_cover",
    "flagged_forge_crucible",
    "warned_torres",
    "read_oren_holdout",
    "technical_named_convergence",
    "added_tev_fees",
    # === CE-4 encounter texture flags ===
    # Set on player choices in CE-4 encounters to remember mercy /
    # negotiation outcomes. Reserved for future TW (Time Weight) and
    # RC (Recurring Captains) phases that may surface callbacks.
    "ce4_fed_the_hungry",
    "ce4_frontier_friendly",
    "ce4_guild_assessed",
    "ce4_saved_a_kid",
    # NV-7 wave 2 insight flags — ground mission NPCs + factions
    "read_neve_setup",
    "pushed_petra_decision",
    "offered_tomasz_off_books",
    "took_command_britt",
    "read_cassiel_forger",
    "pressed_callum",
    "diagnosed_blight_vector",
    "pressed_amara_worried",
    "read_meridian_off_lane",
    "leaned_on_rook",
    "read_yuki_debris_math",
    "offered_to_lead_investigation",
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
    # Arna mini-campaign (AR-1 + AR-2) — taught_* flags are narrative state
    # markers that future content (NPC dialogue, achievements) may read but
    # don't yet.
    "taught_mining",
    "taught_refining",
    "taught_combat",
    "taught_salvage",
    "taught_smuggling",
    # Arna mini-campaign (AR-3) — narrative state flags.
    "arna_scheme_revealed",
    "keren_escaped",
    "smuggling_primer_received",
    # Arna mini-campaign (AR-5) — odom_spoke_of_arna is a pure producer
    # (dialogue flags for one-time gating, no further consumer expected).
    # arna_pendant_revealed triggers a journal entry but the scanner doesn't
    # detect journal trigger_flag as a consumer. arna_gone_from_nexus is
    # consumed by NPC hide_after_flag but the scanner doesn't pick that up.
    "odom_spoke_of_arna",
    "arna_pendant_revealed",
    "arna_gone_from_nexus",
    # Narrative state flag — post-branch-A, Reach watches the player. No
    # mechanical gating yet; future encounter / journal content may consume.
    "reach_hunts_player",
    # CB-2 (2026-04-29): heard_dcmc_intelligence, heard_nas_intelligence,
    # attended_silent_shaft, and marcus_uprising_inheritance_seen were removed
    # from this list. CB-2 authored ambient required_flags consumers for all four,
    # so the scanner now detects them via the ambient consumer block added to
    # _collect_all_flag_uses(). No longer orphaned.
    # === SA-B3 Velo first encounter — journal trigger consumer ===
    # ``seen_first_velo_encounter`` is set by Velo's dialogue tree
    # (``cassian_velo_main``) and consumed by the
    # ``auto_auction_first_velo_encounter`` journal entry's
    # ``trigger_flag``. The scanner does not crawl journal trigger_flag,
    # so the flag appears producer-only here despite a real consumer
    # existing in ``data/journal/entries.json``.
    "seen_first_velo_encounter",
    # === SA-B4 Floor Manager first encounter — journal trigger consumer ===
    # ``seen_first_floor_manager_encounter`` is set by Vex's dialogue tree
    # (``reach_floor_manager_main``) and consumed by the
    # ``auto_auction_first_floor_manager_encounter`` journal entry. Same
    # scanner-blind-spot as the Velo entry above.
    "seen_first_floor_manager_encounter",
    # === SA-R1 Okafor met_npc — SA-R2 reserved ===
    # ``met_kweon_director`` is SET by the OkaforView on first entry
    # (via ``met_npc("kweon_director")`` setdefault). No consumer yet;
    # SA-R2 will gate Kweon's returning-greeting branches on this flag.
    "met_kweon_director",
    # === SA-R1 Okafor team-fund collaborator share — SA-R2 reserved ===
    # ``okafor_collaborator_share_<researcher_id>`` is SET by the Okafor
    # view team-fund flow when the player adds a researcher to a project.
    # Consumers are explicitly deferred to SA-R2 (Dr. Okafor's Legacy
    # Narrative Arc), per the locked decision in the SA-R1 plan. They
    # preserve narrative state so future SA-R2 dialogue can reference
    # which Institute staff the player has worked with.
    "okafor_collaborator_share_dr_iris_navarro",
    "okafor_collaborator_share_theo_brandt",
    "okafor_collaborator_share_sana_dey",
    "okafor_collaborator_share_nuri_solberg",
    # === SA-R2 DETECTOR MISS — consumed via pending_legacy_beat variable dispatch ===
    # ``okafor_legacy_mission_offered`` is SET by the dialogue response's
    # set_flag field (detectable). The real consumer is ``pending_legacy_beat``
    # in ``okafor_research.py``, which calls ``dialogue_flags.get(name)`` with
    # ``name`` being a variable — not a string literal the scanner can match.
    # The OkaforView close-handler also reads it through the same helper.
    "okafor_legacy_mission_offered",
    # === SI3-FOLLOW-1: Net-new producer orphans surfaced by no-arg helper detection ===
    # Before SI3-FOLLOW-1, the scanner's producer regex matched only string-literal
    # ``dialogue_flags["flag"]`` assignments and missed helper-call forms like
    # ``dialogue_flags[enrolled_wreckers_guild()] = True``. The extended no-arg
    # producer regex now detects these, surfacing 4 previously invisible producers.
    #
    # Triage (2026-04-29):
    #   enrolled_wreckers_guild — SET on enroll in WreckersGuildView. No wired consumer
    #     yet; enrollment state is read via sub_reputation model attribute, not this flag.
    #     Narrative state marker for future dialogue gates (SA-X1 cross-anchor).
    "enrolled_wreckers_guild",
    #   received_miners_blessing_first — SET in DeepShaftsView._apply_rep_grant on first
    #     visit. Future consumer planned (SA-X1). First-visit gate logic reads
    #     DeepShaftsState.scripted_scene_played, not this flag, so no code consumer.
    "received_miners_blessing_first",
    #   wreckers_contract_completed — DETECTOR MISS: consumed by data/journal/entries.json
    #     trigger_flag (``auto_wreckers_contract_completed``). Scanner does not crawl
    #     journal trigger_flag entries.
    "wreckers_contract_completed",
    #   wreckers_made_up_journal — DETECTOR MISS: same pattern — consumed by
    #     data/journal/entries.json trigger_flag. Scanner blind spot.
    "wreckers_made_up_journal",
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
            f"REAL BUG / DETECTOR MISS classification:\n" + "\n".join(sorted(new_orphans))
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


# ---------------------------------------------------------------------------
# SI3-FOLLOW-1: No-arg helper introspection unit tests
# ---------------------------------------------------------------------------


class TestNoArgHelperIntrospection:
    """Unit tests verifying _helper_access_patterns() detects no-arg helpers.

    AC-3: patterns include no-arg entries with prefix == flag string, suffix == "".
    AC-4: parameterized helpers still round-trip correctly.
    AC-5: helpers with any parameters (required or default) are not misclassified as no-arg.
    """

    def test_no_arg_helper_returns_full_flag_as_prefix(self) -> None:
        """investment_introduced appears as a no-arg entry with flag string as prefix."""
        patterns = _helper_access_patterns()
        entry = next((p for p in patterns if p[0] == "investment_introduced"), None)
        assert entry is not None, (
            "'investment_introduced' no-arg helper not found in _helper_access_patterns() output"
        )
        assert entry[1] == "", "No-arg helper should have empty suffix"
        assert not entry[4], "investment_introduced should be is_parameterized=False"

    def test_no_arg_helper_consumer_regex_matches_dialogue_flags_get(self) -> None:
        """Consumer regex for investment_introduced matches dialogue_flags.get(...)."""
        patterns = _helper_access_patterns()
        entry = next((p for p in patterns if p[0] == "investment_introduced"), None)
        assert entry is not None, "'investment_introduced' not in patterns"
        consumer_re = entry[3]
        snippet = "dialogue_flags.get(investment_introduced(), False)"
        assert consumer_re.search(snippet), (
            f"Consumer regex {consumer_re.pattern!r} did not match: {snippet!r}"
        )

    def test_no_arg_helper_consumer_regex_matches_local_alias_flags_get(self) -> None:
        """Consumer regex matches local-alias flags.get(okafor_legacy_mission_completed())."""
        patterns = _helper_access_patterns()
        entry = next((p for p in patterns if p[0] == "okafor_legacy_mission_completed"), None)
        assert entry is not None, "'okafor_legacy_mission_completed' not in patterns"
        consumer_re = entry[3]
        snippet = "flags.get(okafor_legacy_mission_completed())"
        assert consumer_re.search(snippet), (
            f"Consumer regex {consumer_re.pattern!r} did not match local-alias: {snippet!r}"
        )

    def test_parameterized_helper_still_detected(self) -> None:
        """Parameterized helpers (met_npc, talked_to_npc, tutorial_bought_part,
        dual_tech_revealed) still produce correct producer regex matches."""
        patterns = _helper_access_patterns()
        cases = [
            ("met_", 'dialogue_flags[met_npc("marcus_jin")] = True', True),
            ("talked_to_", 'dialogue_flags[talked_to_npc("cargo_broker")] = True', True),
            (
                "tutorial_bought_part_",
                'dialogue_flags[tutorial_bought_part("engine")] = True',
                True,
            ),
            ("dual_tech_", 'dialogue_flags[dual_tech_revealed("ionic_burst")] = True', True),
        ]
        for prefix, snippet, expected_is_param in cases:
            entry = next((p for p in patterns if p[0] == prefix), None)
            assert entry is not None, f"Parameterized helper with prefix '{prefix}' not found"
            assert entry[4] == expected_is_param, (
                f"Helper with prefix '{prefix}' has wrong is_parameterized={entry[4]}"
            )
            producer_re = entry[2]
            assert producer_re.search(snippet), (
                f"Producer regex for prefix '{prefix}' did not match: {snippet!r}"
            )

    def test_default_arg_helper_guard_no_misclassification(self) -> None:
        """Every no-arg entry corresponds to a genuine zero-parameter helper (AC-5).

        Guards against a future helper like ``def f(x: str = "y")`` being
        misclassified as no-arg. Verified by confirming that for every
        is_parameterized=False entry, a zero-parameter helper in flags.py
        returns the same string.
        """
        import inspect

        from spacegame.constants import flags as flags_module

        patterns = _helper_access_patterns()
        no_arg_entries = [p for p in patterns if not p[4]]

        for prefix, _suffix, _prod, _cons, _is_param in no_arg_entries:
            found_zero_param_helper = False
            for name, obj in inspect.getmembers(flags_module):
                if name.startswith(("_", "extract_")) or not callable(obj):
                    continue
                sig = inspect.signature(obj)
                if len(sig.parameters) != 0:
                    continue
                try:
                    result = obj()
                    if result == prefix:
                        found_zero_param_helper = True
                        break
                except Exception:
                    pass
            assert found_zero_param_helper, (
                f"No-arg entry with prefix '{prefix}' has no matching zero-parameter "
                f"helper in flags.py — possible misclassification of a default-arg helper"
            )
