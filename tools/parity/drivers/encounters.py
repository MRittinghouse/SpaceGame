"""Encounter roll, selection, outcome, and captain goldens (SP3 spec 6.2)."""

from __future__ import annotations

import dataclasses
from typing import Optional

from spacegame.data_loader import get_data_loader
from spacegame.models.captain_memory import (
    OUTCOME_BRIBED,
    OUTCOME_DEFEAT,
    OUTCOME_FLED,
    OUTCOME_NEGOTIATED,
    OUTCOME_VICTORY,
    CaptainMemory,
)
from spacegame.models.captain_variant import (
    get_effective_captain_dialogue,
    meeting_state_for_memory,
)
from spacegame.models.encounter import (
    EncounterContext,
    EncounterDefinition,
    apply_encounter_outcome,
    check_travel_encounter,
    filter_enemies_for_system,
    resolve_choice_outcome,
    resolve_encounter_skill_check,
    select_encounter_definition,
)
from spacegame.models.social import SocialManager
from tools.parity.driver import Case
from tools.parity.snapshots import fresh_player, player_snapshot

ROLL_DAYS = range(1, 31)
PROFILES: dict[str, dict[str, object]] = {
    "novice": {
        "player_level": 1,
        "defensive_identity": "",
        "encounter_reduction": 0.0,
        "anomaly_sense": 0.0,
        "anomaly_chance_bonus": 0.0,
    },
    "veteran": {
        "player_level": 5,
        "defensive_identity": "ghost",
        "encounter_reduction": 0.2,
        "anomaly_sense": 0.1,
        "anomaly_chance_bonus": 0.1,
    },
}
SHAKEDOWN_DEMAND = 150
OUTCOMES = (OUTCOME_VICTORY, OUTCOME_DEFEAT, OUTCOME_NEGOTIATED, OUTCOME_BRIBED, OUTCOME_FLED)


def _roll(system_id: str) -> Case:
    dl = get_data_loader()
    system = dl.systems[system_id]
    origin = dl.systems["nexus_prime"]
    distance = origin.distance_to(system) if system_id != "nexus_prime" else 80.0
    enemy_ids = filter_enemies_for_system(dl.enemy_templates, system.faction, system.danger_level)
    case = Case(
        "encounters",
        f"roll_{system_id}",
        {
            "danger": system.danger_level,
            "distance": distance,
            "enemy_ids": enemy_ids,
        },
    )
    for profile, knobs in PROFILES.items():
        for day in ROLL_DAYS:
            ref = check_travel_encounter(
                system.danger_level,
                enemy_ids,
                day,
                system_id,
                distance,
                **knobs,  # type: ignore[arg-type]
            )
            case.record(
                "check_travel_encounter",
                [profile, day],
                dataclasses.asdict(ref) if ref else None,
                {},
            )
    return case


def _select() -> Case:
    dl = get_data_loader()
    definitions = dl.encounter_definitions
    types = sorted({d.encounter_type for d in definitions})
    factions = ["", *sorted(dl.factions)]
    case = Case("encounters", "select", {"types": types, "factions": factions})
    for encounter_type in types:
        for danger in ("moderate", "dangerous"):
            for faction_id in factions:
                for seed in range(1, 6):
                    ctx = EncounterContext(
                        encounter_type=encounter_type,
                        danger_level=danger,
                        seed=seed,
                        system_id="",
                        faction_id=faction_id,
                        player_level=3,
                    )
                    chosen = select_encounter_definition(definitions, ctx)
                    case.record(
                        "select_encounter_definition",
                        [encounter_type, danger, faction_id, seed],
                        chosen.id if chosen else None,
                        {},
                    )
    return case


def _outcomes(encounter_type: str, definitions: list[EncounterDefinition]) -> Case:
    case = Case("encounters", f"outcomes_{encounter_type}", {"shakedown_demand": SHAKEDOWN_DEMAND})
    for definition in definitions:
        for choice in definition.choices:
            passes = (True, False) if choice.skill_check is not None else (True,)
            for passed in passes:
                player = fresh_player(credits=500)
                player.ship.add_cargo("food", 10, 20)
                outcome = resolve_choice_outcome(choice, SHAKEDOWN_DEMAND, passed)
                effects = apply_encounter_outcome(player, outcome)
                case.record(
                    "choose",
                    [definition.id, choice.id, passed],
                    {
                        "outcome": dataclasses.asdict(outcome),
                        "effects": dataclasses.asdict(effects),
                    },
                    player_snapshot(player),
                )
    return case


def _skill_checks() -> Case:
    dl = get_data_loader()
    checks = sorted(
        {
            (
                c.skill_check.skill,
                c.skill_check.difficulty,
                c.skill_check.set_flag_on_success or "",
                c.skill_check.set_flag_on_failure or "",
            )
            for d in dl.encounter_definitions
            for c in d.choices
            if c.skill_check is not None
        }
    )
    case = Case("encounters", "skill_checks", {})
    for profile in ("default", "boosted"):
        for skill, difficulty, on_pass, on_fail in checks:
            manager = SocialManager()
            if profile == "boosted":
                for social_skill in manager._skills.values():
                    social_skill.level = 10
            player = fresh_player()
            check = next(
                c.skill_check
                for d in dl.encounter_definitions
                for c in d.choices
                if c.skill_check is not None
                and (
                    c.skill_check.skill,
                    c.skill_check.difficulty,
                    c.skill_check.set_flag_on_success or "",
                    c.skill_check.set_flag_on_failure or "",
                )
                == (skill, difficulty, on_pass, on_fail)
            )
            passed = resolve_encounter_skill_check(check, manager, player)
            flags = sorted(k for k, v in player.dialogue_flags.items() if v)
            case.record(
                "skill_check",
                [profile, skill, difficulty, on_pass, on_fail],
                passed,
                {"flags": flags, "social": manager.get_state()},
            )
    return case


def _captains() -> Case:
    dl = get_data_loader()
    case = Case("encounters", "captains", {"outcomes": list(OUTCOMES)})
    for captain_id in sorted(dl.captains):
        captain = dl.captains[captain_id]
        for outcome in OUTCOMES:
            memory: Optional[CaptainMemory] = None
            for day in (3, 9, 15):
                memory = memory or CaptainMemory(captain_id=captain_id)
                memory.record_encounter(outcome, day)
                dialogue = get_effective_captain_dialogue(captain, memory, dl.captain_variants)
                case.record(
                    "record_encounter",
                    [captain_id, outcome, day],
                    {
                        "meeting_state": meeting_state_for_memory(memory),
                        "dialogue": dataclasses.asdict(dialogue),
                    },
                    memory.to_dict(),
                )
    return case


def build_cases() -> list[Case]:
    """Every encounter case."""
    dl = get_data_loader()
    dl.load_all()
    by_type: dict[str, list[EncounterDefinition]] = {}
    for definition in dl.encounter_definitions:
        by_type.setdefault(definition.encounter_type, []).append(definition)
    return [
        *[_roll(system_id) for system_id in dl.systems],
        _select(),
        *[_outcomes(t, defs) for t, defs in sorted(by_type.items())],
        _skill_checks(),
        _captains(),
    ]
