"""Cross-reference validation for all game JSON data.

Validates that IDs referenced across missions, NPCs, dialogues, encounters,
commodities, and systems are consistent and point to real entities. These
tests run against real game data and would catch data integrity bugs before
they reach playtesters.
"""

from collections import defaultdict
from pathlib import Path

from spacegame.data_loader import DataLoader
from spacegame.models.mission import ObjectiveType

# ---------------------------------------------------------------------------
# Shared loader fixture
# ---------------------------------------------------------------------------

_loader_cache: DataLoader | None = None


def _get_loader() -> DataLoader:
    """Load all game data once and cache for reuse across tests."""
    global _loader_cache
    if _loader_cache is None:
        project_root = Path(__file__).parent.parent.parent
        loader = DataLoader(data_dir=project_root / "data")
        loader.load_all()
        _loader_cache = loader
    return _loader_cache


# ---------------------------------------------------------------------------
# Commodity validation
# ---------------------------------------------------------------------------


class TestCommodityReferences:
    """Every commodity ID referenced in missions must exist."""

    def test_collect_cargo_objectives_reference_valid_commodities(self) -> None:
        """Every collect_cargo objective target_id exists in commodities."""
        loader = _get_loader()
        commodity_ids = set(loader.commodities.keys())
        errors = []
        for mission in loader.missions:
            for obj in mission.objectives:
                if obj.type == ObjectiveType.COLLECT_CARGO:
                    if obj.target_id not in commodity_ids:
                        errors.append(
                            f"Mission '{mission.id}' objective references "
                            f"commodity '{obj.target_id}' which does not exist"
                        )
        assert not errors, "\n".join(errors)

    def test_on_accept_cargo_references_valid_commodities(self) -> None:
        """Every on_accept_cargo commodity_id exists in commodities."""
        loader = _get_loader()
        commodity_ids = set(loader.commodities.keys())
        errors = []
        for mission in loader.missions:
            for cargo in mission.on_accept_cargo:
                if cargo.commodity_id not in commodity_ids:
                    errors.append(
                        f"Mission '{mission.id}' on_accept_cargo references "
                        f"commodity '{cargo.commodity_id}' which does not exist"
                    )
        assert not errors, "\n".join(errors)

    def test_remove_cargo_rewards_reference_valid_commodities(self) -> None:
        """Every remove_cargo reward target_id exists in commodities."""
        loader = _get_loader()
        commodity_ids = set(loader.commodities.keys())
        errors = []
        for mission in loader.missions:
            for reward in mission.rewards:
                if reward.reward_type == "remove_cargo":
                    if reward.target_id not in commodity_ids:
                        errors.append(
                            f"Mission '{mission.id}' remove_cargo reward "
                            f"references commodity '{reward.target_id}' "
                            f"which does not exist"
                        )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# NPC validation
# ---------------------------------------------------------------------------


class TestNPCReferences:
    """NPC references across missions and data are consistent."""

    def test_talk_to_npc_objectives_reference_valid_npcs(self) -> None:
        """Every talk_to_npc objective target_id exists in NPCs."""
        loader = _get_loader()
        npc_ids = set(loader.npcs.keys())
        errors = []
        for mission in loader.missions:
            for obj in mission.objectives:
                if obj.type == ObjectiveType.TALK_TO_NPC:
                    if obj.target_id not in npc_ids:
                        errors.append(
                            f"Mission '{mission.id}' talk_to_npc objective "
                            f"references NPC '{obj.target_id}' which does not exist"
                        )
        assert not errors, "\n".join(errors)

    def test_npc_dialogue_ids_reference_valid_trees(self) -> None:
        """Every NPC's dialogue_id references a real dialogue tree."""
        loader = _get_loader()
        tree_ids = set(loader.dialogue_trees.keys())
        errors = []
        for npc in loader.npcs.values():
            if npc.dialogue_id and npc.dialogue_id not in tree_ids:
                errors.append(
                    f"NPC '{npc.id}' ({npc.name}) dialogue_id "
                    f"'{npc.dialogue_id}' does not exist in dialogue trees"
                )
        assert not errors, "\n".join(errors)

    def test_npc_home_systems_exist(self) -> None:
        """Every NPC's home_system_id references a real system."""
        loader = _get_loader()
        system_ids = set(loader.systems.keys())
        errors = []
        for npc in loader.npcs.values():
            if npc.home_system_id and npc.home_system_id not in system_ids:
                errors.append(
                    f"NPC '{npc.id}' ({npc.name}) home_system_id "
                    f"'{npc.home_system_id}' does not exist"
                )
        assert not errors, "\n".join(errors)

    def test_npc_dialogue_states_reference_valid_trees(self) -> None:
        """Every dialogue_states[].dialogue_id references a real dialogue tree."""
        loader = _get_loader()
        tree_ids = set(loader.dialogue_trees.keys())
        errors = []
        for npc in loader.npcs.values():
            for state in npc.dialogue_states:
                if state.dialogue_id not in tree_ids:
                    errors.append(
                        f"NPC '{npc.id}' ({npc.name}) dialogue_states "
                        f"state '{state.state_id}' references dialogue "
                        f"'{state.dialogue_id}' which does not exist"
                    )
        assert not errors, "\n".join(errors)

    def test_npc_faction_ids_valid(self) -> None:
        """Every NPC's faction_id (if set) references a real faction."""
        loader = _get_loader()
        faction_ids = set(loader.factions.keys())
        errors = []
        for npc in loader.npcs.values():
            if npc.faction_id and npc.faction_id not in faction_ids:
                errors.append(
                    f"NPC '{npc.id}' ({npc.name}) faction_id '{npc.faction_id}' does not exist"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# System validation
# ---------------------------------------------------------------------------


class TestSystemReferences:
    """System IDs referenced in missions and NPCs are valid."""

    def test_reach_system_objectives_reference_valid_systems(self) -> None:
        """Every reach_system objective target_id exists in systems."""
        loader = _get_loader()
        system_ids = set(loader.systems.keys())
        errors = []
        for mission in loader.missions:
            for obj in mission.objectives:
                if obj.type == ObjectiveType.REACH_SYSTEM:
                    if obj.target_id not in system_ids:
                        errors.append(
                            f"Mission '{mission.id}' reach_system objective "
                            f"references system '{obj.target_id}' which does not exist"
                        )
        assert not errors, "\n".join(errors)

    def test_available_at_systems_exist(self) -> None:
        """Every mission available_at system exists."""
        loader = _get_loader()
        system_ids = set(loader.systems.keys())
        errors = []
        for mission in loader.missions:
            for sys_id in mission.available_at:
                if sys_id not in system_ids:
                    errors.append(f"Mission '{mission.id}' available_at '{sys_id}' does not exist")
        assert not errors, "\n".join(errors)

    def test_ground_mission_system_ids_exist(self) -> None:
        """Every ground_mission_system_id references a real system."""
        loader = _get_loader()
        system_ids = set(loader.systems.keys())
        errors = []
        for mission in loader.missions:
            if mission.ground_mission_system_id:
                if mission.ground_mission_system_id not in system_ids:
                    errors.append(
                        f"Mission '{mission.id}' ground_mission_system_id "
                        f"'{mission.ground_mission_system_id}' does not exist"
                    )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Mission chain validation
# ---------------------------------------------------------------------------


class TestMissionChainIntegrity:
    """Mission prerequisite chains reference real missions with no cycles."""

    def _get_mission_ids(self) -> set[str]:
        """Get all loaded mission IDs."""
        loader = _get_loader()
        return {m.id for m in loader.missions}

    def test_prerequisite_mission_ids_exist(self) -> None:
        """Every prerequisites entry references a real mission."""
        loader = _get_loader()
        all_ids = self._get_mission_ids()
        errors = []
        for mission in loader.missions:
            for prereq in mission.prerequisites:
                if prereq not in all_ids:
                    errors.append(f"Mission '{mission.id}' prerequisite '{prereq}' does not exist")
        assert not errors, "\n".join(errors)

    def test_available_after_mission_ids_exist(self) -> None:
        """Every available_after references a real mission."""
        loader = _get_loader()
        all_ids = self._get_mission_ids()
        errors = []
        for mission in loader.missions:
            if mission.available_after and mission.available_after not in all_ids:
                errors.append(
                    f"Mission '{mission.id}' available_after "
                    f"'{mission.available_after}' does not exist"
                )
        assert not errors, "\n".join(errors)

    def test_available_before_mission_ids_exist(self) -> None:
        """Every available_before references a real mission."""
        loader = _get_loader()
        all_ids = self._get_mission_ids()
        errors = []
        for mission in loader.missions:
            if mission.available_before and mission.available_before not in all_ids:
                errors.append(
                    f"Mission '{mission.id}' available_before "
                    f"'{mission.available_before}' does not exist"
                )
        assert not errors, "\n".join(errors)

    def test_no_circular_prerequisite_chains(self) -> None:
        """No mission prerequisite chain forms a cycle."""
        loader = _get_loader()
        # Build adjacency: mission -> set of missions it depends on
        deps: dict[str, set[str]] = {}
        for mission in loader.missions:
            d: set[str] = set(mission.prerequisites)
            if mission.available_after:
                d.add(mission.available_after)
            deps[mission.id] = d

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(deps, WHITE)

        def _has_cycle(node: str, path: list[str]) -> str | None:
            color[node] = GRAY
            path.append(node)
            for dep in deps.get(node, set()):
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    cycle_start = path.index(dep)
                    cycle = " -> ".join([*path[cycle_start:], dep])
                    return f"Circular dependency: {cycle}"
                if color[dep] == WHITE:
                    result = _has_cycle(dep, path)
                    if result:
                        return result
            path.pop()
            color[node] = BLACK
            return None

        errors = []
        for mid in deps:
            if color[mid] == WHITE:
                result = _has_cycle(mid, [])
                if result:
                    errors.append(result)
        assert not errors, "\n".join(errors)

    def test_no_duplicate_mission_ids(self) -> None:
        """No two missions share the same ID."""
        loader = _get_loader()
        seen: dict[str, int] = defaultdict(int)
        for mission in loader.missions:
            seen[mission.id] += 1
        dupes = {mid: count for mid, count in seen.items() if count > 1}
        assert not dupes, f"Duplicate mission IDs: {dupes}"


# ---------------------------------------------------------------------------
# Flag reachability validation
# ---------------------------------------------------------------------------


class TestFlagReachability:
    """Every required flag on a mission can be set by something in the game."""

    def _collect_settable_flags(self) -> set[str]:
        """Collect all flags that can be set by dialogues, rewards, encounters,
        or the game engine automatically.
        """
        loader = _get_loader()
        flags: set[str] = set()

        # Flags set by dialogue responses
        for tree in loader.dialogue_trees.values():
            for node in tree.nodes.values():
                for response in node.responses:
                    if response.set_flag:
                        flags.add(response.set_flag)
                    if response.skill_check:
                        if response.skill_check.set_flag_on_success:
                            flags.add(response.skill_check.set_flag_on_success)
                        if response.skill_check.set_flag_on_failure:
                            flags.add(response.skill_check.set_flag_on_failure)

        # Flags set by mission rewards
        for mission in loader.missions:
            for reward in mission.rewards:
                if reward.reward_type == "set_flag" and reward.target_id:
                    flags.add(reward.target_id)

        # Flags set by encounter outcomes
        for defn in loader.encounter_definitions:
            for choice in defn.choices:
                for reward in choice.outcome.rewards:
                    if reward.reward_type == "set_flag" and reward.target_id:
                        flags.add(reward.target_id)

        # Flags set automatically by game engine (talked_to_{npc_id})
        for npc_id in loader.npcs:
            flags.add(f"talked_to_{npc_id}")

        # NPC auto_trigger_gate_flags are set by the engine when auto-trigger fires
        for npc in loader.npcs.values():
            gate = getattr(npc, "auto_trigger_gate_flag", None)
            if gate:
                flags.add(gate)

        # Ground mission completion flags are set by the engine
        for mission in loader.missions:
            if mission.ground_mission_complete_flag:
                flags.add(mission.ground_mission_complete_flag)

        return flags

    def _collect_engine_flags(self) -> set[str]:
        """Flags set directly by game.py code, not derivable from data."""
        return {
            "iron_ore_delivered",
            "iron_delivery_failed",
            "broker_ore_sold",
            "talked_to_officer_larsen",
            # Combat outcome flags set by encounter/combat resolution
            "escape_combat_survived",
        }

    def test_mission_required_flags_are_settable(self) -> None:
        """Every required_flags entry on a mission can be set by something."""
        settable = self._collect_settable_flags()
        engine_flags = self._collect_engine_flags()
        loader = _get_loader()
        loyalty_pattern = "crew_loyalty_"

        errors = []
        for mission in loader.missions:
            for flag in mission.required_flags:
                if flag in settable or flag in engine_flags:
                    continue
                if flag.startswith(loyalty_pattern):
                    continue
                errors.append(
                    f"Mission '{mission.id}' requires flag '{flag}' "
                    f"but nothing in dialogues, rewards, or encounters sets it"
                )
        assert not errors, "\n".join(errors)

    def test_npc_auto_trigger_prerequisites_are_settable(self) -> None:
        """Every NPC auto_trigger_prerequisites flag can be set by something."""
        settable = self._collect_settable_flags()
        engine_flags = self._collect_engine_flags()
        loader = _get_loader()
        loyalty_pattern = "crew_loyalty_"

        errors = []
        for npc in loader.npcs.values():
            for flag in getattr(npc, "auto_trigger_prerequisites", []) or []:
                if flag in settable or flag in engine_flags:
                    continue
                if flag.startswith(loyalty_pattern):
                    continue
                errors.append(
                    f"NPC '{npc.id}' ({npc.name}) auto_trigger_prerequisites "
                    f"requires flag '{flag}' but nothing sets it"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Encounter-quest validation
# ---------------------------------------------------------------------------


class TestEncounterQuestIntegrity:
    """Encounter-triggered quests have corresponding encounters."""

    def test_encounter_discovery_quests_have_encounters(self) -> None:
        """Every mission with discovery_method='encounter' has an encounter
        that can set the flags needed to trigger the quest.
        """
        loader = _get_loader()

        # Collect all flags set by encounter outcomes
        encounter_flags: set[str] = set()
        for defn in loader.encounter_definitions:
            for choice in defn.choices:
                for reward in choice.outcome.rewards:
                    if reward.reward_type == "set_flag" and reward.target_id:
                        encounter_flags.add(reward.target_id)

        errors = []
        for mission in loader.missions:
            if mission.discovery_method != "encounter":
                continue
            # Check that at least one objective flag can be set by an encounter
            flag_objectives = [
                obj for obj in mission.objectives if obj.type == ObjectiveType.HAS_FLAG
            ]
            if not flag_objectives:
                continue
            first_flag = flag_objectives[0].target_id
            if first_flag not in encounter_flags:
                errors.append(
                    f"Mission '{mission.id}' (discovery_method=encounter) "
                    f"needs flag '{first_flag}' but no encounter sets it"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Reputation reward validation
# ---------------------------------------------------------------------------


class TestReputationRewardReferences:
    """Reputation rewards reference valid factions."""

    def test_modify_reputation_targets_valid_factions(self) -> None:
        """Every modify_reputation reward targets a real faction."""
        loader = _get_loader()
        faction_ids = set(loader.factions.keys())
        errors = []
        for mission in loader.missions:
            for reward in mission.rewards:
                if reward.reward_type == "modify_reputation":
                    if reward.target_id not in faction_ids:
                        errors.append(
                            f"Mission '{mission.id}' modify_reputation "
                            f"targets faction '{reward.target_id}' "
                            f"which does not exist"
                        )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Reputation gate validation
# ---------------------------------------------------------------------------


class TestReputationGateReferences:
    """Reputation gates on missions reference valid factions."""

    def test_required_reputation_faction_ids_valid(self) -> None:
        """Every required_reputation faction_id exists."""
        loader = _get_loader()
        faction_ids = set(loader.factions.keys())
        errors = []
        for mission in loader.missions:
            for req in mission.required_reputation:
                fid = req.get("faction_id", "")
                if fid not in faction_ids:
                    errors.append(
                        f"Mission '{mission.id}' required_reputation "
                        f"references faction '{fid}' which does not exist"
                    )
        assert not errors, "\n".join(errors)

    def test_required_reputation_thresholds_in_range(self) -> None:
        """Reputation thresholds are within valid range (-100 to 100)."""
        loader = _get_loader()
        errors = []
        for mission in loader.missions:
            for req in mission.required_reputation:
                min_rep = req.get("min_reputation", 0)
                if not -100 <= min_rep <= 100:
                    errors.append(
                        f"Mission '{mission.id}' required_reputation "
                        f"min_reputation {min_rep} out of range [-100, 100]"
                    )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Dialogue states flag reachability
# ---------------------------------------------------------------------------


class TestDialogueStateFlagReachability:
    """Dialogue state required_flags can be set by something in the game."""

    def test_dialogue_state_required_flags_settable(self) -> None:
        """Every flag in dialogue_states.required_flags is settable."""
        loader = _get_loader()
        # Collect all settable flags (reuse pattern from TestFlagReachability)
        settable: set[str] = set()
        for tree in loader.dialogue_trees.values():
            for node in tree.nodes.values():
                for resp in node.responses:
                    if resp.set_flag:
                        settable.add(resp.set_flag)
                    if resp.skill_check:
                        if resp.skill_check.set_flag_on_success:
                            settable.add(resp.skill_check.set_flag_on_success)
                        if resp.skill_check.set_flag_on_failure:
                            settable.add(resp.skill_check.set_flag_on_failure)
        for mission in loader.missions:
            for reward in mission.rewards:
                if reward.reward_type == "set_flag" and reward.target_id:
                    settable.add(reward.target_id)
        for defn in loader.encounter_definitions:
            for choice in defn.choices:
                for reward in choice.outcome.rewards:
                    if reward.reward_type == "set_flag" and reward.target_id:
                        settable.add(reward.target_id)
        for npc in loader.npcs.values():
            gate = getattr(npc, "auto_trigger_gate_flag", None)
            if gate:
                settable.add(gate)
        for mission in loader.missions:
            if mission.ground_mission_complete_flag:
                settable.add(mission.ground_mission_complete_flag)
        for npc_id in loader.npcs:
            settable.add(f"talked_to_{npc_id}")

        engine_flags = {
            "iron_ore_delivered",
            "iron_delivery_failed",
            "broker_ore_sold",
            "talked_to_officer_larsen",
            "escape_combat_survived",
        }

        errors = []
        for npc in loader.npcs.values():
            for state in npc.dialogue_states:
                for flag in state.required_flags:
                    if flag in settable or flag in engine_flags:
                        continue
                    if flag.startswith("crew_loyalty_"):
                        continue
                    errors.append(
                        f"NPC '{npc.id}' dialogue_state '{state.state_id}' "
                        f"requires flag '{flag}' but nothing sets it"
                    )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# Chatter flag validation
# ---------------------------------------------------------------------------


class TestChatterFlagReferences:
    """Station chatter flag references point to settable flags."""

    def test_one_shot_lines_have_required_flags(self) -> None:
        """Every one_shot chatter line has required_flags (must be progression-gated)."""
        loader = _get_loader()
        errors = []
        for line in loader.station_chatter_lines:
            if getattr(line, "one_shot", False) and not line.required_flags:
                errors.append(
                    f"Chatter '{line.id}': one_shot=true but no required_flags "
                    f"(one-shot lines must be progression-gated)"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# QA Pass 2.1 — Enemy subsystem tag validation
# ---------------------------------------------------------------------------


class TestEnemySubsystemTags:
    """Every targetable_subsystems entry must be in the canonical 6-tag palette."""

    def test_all_subsystem_tags_are_canonical(self) -> None:
        from spacegame.models.enemy_subsystems import CANONICAL_TAGS

        loader = _get_loader()
        canonical = set(CANONICAL_TAGS)
        errors = []
        for template_id, template in loader.enemy_templates.items():
            for tag in getattr(template, "targetable_subsystems", []):
                if tag not in canonical:
                    errors.append(
                        f"Enemy '{template_id}' targetable_subsystems references "
                        f"unknown tag '{tag}' (canonical: {sorted(canonical)})"
                    )
        assert not errors, "\n".join(errors)

    def test_subsystem_count_within_spec_bounds(self) -> None:
        """Combat §11.2: regular enemies 1-2 subsystems, bosses 3-4. No more than 4."""
        loader = _get_loader()
        errors = []
        for template_id, template in loader.enemy_templates.items():
            tags = getattr(template, "targetable_subsystems", [])
            if len(tags) > 4:
                errors.append(
                    f"Enemy '{template_id}' has {len(tags)} subsystems "
                    f"(spec maxes out at 4)"
                )
        assert not errors, "\n".join(errors)

    def test_no_duplicate_subsystems_per_enemy(self) -> None:
        loader = _get_loader()
        errors = []
        for template_id, template in loader.enemy_templates.items():
            tags = getattr(template, "targetable_subsystems", [])
            if len(tags) != len(set(tags)):
                errors.append(
                    f"Enemy '{template_id}' has duplicate subsystem tags: {tags}"
                )
        assert not errors, "\n".join(errors)


# ---------------------------------------------------------------------------
# QA Pass 2.2 — Skill bonus_type producer/consumer audit
# ---------------------------------------------------------------------------


class TestSkillBonusConsumers:
    """Every bonus_type defined on a SkillNode must have at least one consumer.

    Catches dead skills — a skill that defines a bonus_type but no system reads
    it. Consumers go through ``progression.get_bonus("name")`` or, for crew
    bonuses, ``crew_roster.get_bonus("name")``. Dialogue-skill checks call
    ``has_skill`` instead of get_bonus, so those skill IDs (not bonus_types)
    are exempt.
    """

    def test_every_skill_bonus_type_has_a_consumer(self) -> None:
        from spacegame.models.progression import create_default_skills

        skills = create_default_skills()
        # bonus_type → set of skill_ids declaring it (for diagnostic clarity)
        declared: dict[str, set[str]] = defaultdict(set)
        for sid, skill in skills.items():
            bt = getattr(skill, "bonus_type", "") or ""
            if bt:
                declared[bt].add(sid)

        project_root = Path(__file__).parent.parent.parent
        all_source = ""
        for py_file in (project_root / "spacegame").rglob("*.py"):
            all_source += py_file.read_text(encoding="utf-8", errors="ignore")

        # A bonus_type counts as consumed if it appears as a literal
        # somewhere in source — this is intentionally permissive (avoids
        # false positives from wrappers and indirection layers).
        orphans: list[str] = []
        for bt, owners in declared.items():
            if f'"{bt}"' not in all_source and f"'{bt}'" not in all_source:
                orphans.append(f"{bt} (declared by: {sorted(owners)})")

        # Known-deferred bonuses with documented reasons live here so the
        # test stays green while we hold the line on net new orphans. Each
        # entry MUST have a justification — no quiet exemptions.
        #
        # QA Pass 5 Tier 3.F (2026-04-21): price_memory was the last entry
        # and is now wired — PriceMemory model + galaxy map reader shipped.
        # Set intentionally empty: net-new orphans fail the test loudly.
        ALLOWED_ORPHANS: set[str] = set()

        unjustified = sorted(o for o in orphans if o.split(" ")[0] not in ALLOWED_ORPHANS)
        assert not unjustified, (
            "These skill bonus_types are declared but not read anywhere in "
            "source. Either wire them, remove the skill, or add to "
            "ALLOWED_ORPHANS with a justification:\n  " + "\n  ".join(unjustified)
        )


class TestFactionPerks:
    """Faction perks reference real factions and use known perk_types.

    DataLoader stores perks as ``{faction_id: {tier_name: [FactionPerk, ...]}}``;
    these tests walk that structure to flatten before validating.
    """

    def _all_perks(self, loader: DataLoader) -> list:
        flat = []
        for tier_map in loader.faction_perks.values():
            for perk_list in tier_map.values():
                flat.extend(perk_list)
        return flat

    def test_perk_faction_ids_valid(self) -> None:
        loader = _get_loader()
        faction_ids = set(loader.factions.keys())
        errors = []
        for perk in self._all_perks(loader):
            if perk.faction_id not in faction_ids:
                errors.append(
                    f"Perk '{perk.id}' references faction '{perk.faction_id}' "
                    f"which does not exist"
                )
        assert not errors, "\n".join(errors)

    def test_perk_required_tier_is_valid(self) -> None:
        loader = _get_loader()
        valid_tiers = {"friendly", "allied"}
        errors = []
        for perk in self._all_perks(loader):
            if perk.required_tier not in valid_tiers:
                errors.append(
                    f"Perk '{perk.id}' has required_tier '{perk.required_tier}' "
                    f"not in {valid_tiers}"
                )
        assert not errors, "\n".join(errors)

    def test_perk_types_are_consumed_somewhere(self) -> None:
        """Every perk_type in JSON must appear as a string literal in source.

        Consumers may go through wrapper layers (politics.get_perk_bonus,
        politics.has_perk, engine/game.py call sites), so the test scans for
        any occurrence of the literal perk_type string in the source tree.
        """
        loader = _get_loader()
        project_root = Path(__file__).parent.parent.parent
        declared = {p.perk_type for p in self._all_perks(loader)}
        consumed: set[str] = set()
        for py_file in (project_root / "spacegame").rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            for perk_type in declared:
                if f'"{perk_type}"' in text or f"'{perk_type}'" in text:
                    consumed.add(perk_type)
        orphans = declared - consumed
        assert not orphans, (
            f"These faction perk_types are declared in faction_perks.json but "
            f"do not appear as string literals anywhere in the codebase: "
            f"{sorted(orphans)}. Either wire them or remove."
        )


# ---------------------------------------------------------------------------
# QA Pass 2.5 — Module ID cross-references
# ---------------------------------------------------------------------------


class TestModuleReferences:
    """Module IDs in shop catalogs must exist in either ship_parts or ship_modules.

    The codebase has two coexisting builder catalogs:
      - ``ship_parts`` (~166) — new builder system
      - ``ship_modules`` (~144) — legacy module catalog
    Drydock catalogs reference IDs from EITHER, so the validation union-checks.
    """

    def test_drydock_catalog_modules_sold_exist(self) -> None:
        loader = _get_loader()
        valid = set(loader.ship_parts.keys()) | set(loader.ship_modules.keys())
        errors = []
        for system_id, catalog in loader.drydock_catalogs.items():
            for module_id in catalog.get("modules_sold", []):
                if module_id not in valid:
                    errors.append(
                        f"Drydock catalog at system '{system_id}' references "
                        f"unknown module '{module_id}' (not in ship_parts or "
                        f"ship_modules)"
                    )
        assert not errors, "\n".join(errors)

    def test_drydock_catalog_shapes_sold_exist(self) -> None:
        loader = _get_loader()
        valid = set(loader.hull_shapes.keys())
        errors = []
        for system_id, catalog in loader.drydock_catalogs.items():
            for shape_id in catalog.get("shapes_sold", []):
                if shape_id not in valid:
                    errors.append(
                        f"Drydock catalog at system '{system_id}' references "
                        f"unknown hull shape '{shape_id}'"
                    )
        assert not errors, "\n".join(errors)

    def test_drydock_catalog_materials_sold_exist(self) -> None:
        loader = _get_loader()
        valid = set(loader.hull_materials.keys())
        errors = []
        for system_id, catalog in loader.drydock_catalogs.items():
            for mat_id in catalog.get("materials_sold", []):
                if mat_id not in valid:
                    errors.append(
                        f"Drydock catalog at system '{system_id}' references "
                        f"unknown hull material '{mat_id}'"
                    )
        assert not errors, "\n".join(errors)

    def test_enemy_composite_build_modules_exist(self) -> None:
        """Marquee bosses with hand-authored composite_build reference real parts."""
        loader = _get_loader()
        valid = set(loader.ship_parts.keys()) | set(loader.ship_modules.keys())
        errors = []
        for tid, template in loader.enemy_templates.items():
            cb = getattr(template, "composite_build", None)
            if not cb:
                continue
            for slot in cb.get("placed_slots", []):
                installed = slot.get("installed_part_id")
                if installed and installed not in valid:
                    errors.append(
                        f"Enemy '{tid}' composite_build slot references unknown "
                        f"part '{installed}'"
                    )
        assert not errors, "\n".join(errors)
