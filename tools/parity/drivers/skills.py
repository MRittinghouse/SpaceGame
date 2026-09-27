"""Skill, attribute, and social-check golden cases (SP3 spec 6.2)."""

from __future__ import annotations

import dataclasses

from spacegame.models import attributes
from spacegame.models.attributes import AttributeSheet
from spacegame.models.progression import PlayerProgression, SkillTreeType, create_default_skills
from spacegame.models.social import SOCIAL_SKILL_DEFINITIONS, SocialManager
from tools.parity.driver import Case

SKILL_POINTS = 200
XP_STEPS = (5, 50, 100, 250, 500, 1000, 5000)


def _catalog() -> Case:
    case = Case("skills", "catalog", {})
    rows = [dataclasses.asdict(node) for node in create_default_skills().values()]
    case.record("create_default_skills", [], rows, {})
    return case


def _learn_tree(tree: SkillTreeType) -> Case:
    case = Case("skills", f"learn_{tree.value}", {"tree": tree.value, "skill_points": SKILL_POINTS})
    prog = PlayerProgression()
    prog.skill_points = SKILL_POINTS
    ids = [s.id for s in prog.skills.values() if s.tree == tree]
    bonus_types = sorted({prog.skills[i].bonus_type for i in ids})
    for _ in range(2):  # a second pass reaches skills whose prerequisite came later
        for skill_id in ids:
            while True:
                result = prog.level_up_skill(skill_id)
                bonuses = {bt: prog.get_bonus(bt) for bt in bonus_types}
                case.record(
                    "level_up_skill",
                    [skill_id],
                    result,
                    {"progression": prog.to_dict(), "bonuses": bonuses},
                )
                if not result[0]:
                    break
    return case


def _all_bonuses() -> Case:
    case = Case("skills", "all_bonuses_maxed", {"all_skills": "max_level"})
    prog = PlayerProgression()
    for node in prog.skills.values():
        node.current_level = node.max_level
    for bonus_type in sorted({n.bonus_type for n in prog.skills.values()}):
        case.record("get_bonus", [bonus_type], prog.get_bonus(bonus_type), {})
    return case


def _xp_curve() -> Case:
    case = Case("skills", "xp_curve", {})
    prog = PlayerProgression()
    for amount in XP_STEPS:
        messages = prog.add_xp(amount)
        state = {k: v for k, v in prog.to_dict().items() if k != "skills"}
        case.record("add_xp", [amount], messages, state)
    return case


def _attributes() -> Case:
    case = Case("skills", "attributes", {"points": 6})
    sheet = AttributeSheet()
    sheet.add_points(6)
    case.record("add_points", [6], None, sheet.to_dict())
    for attr_id in ("com", "acu", "res", "ing", "syn", "syn"):
        case.record("allocate_point", [attr_id], sheet.allocate_point(attr_id), sheet.to_dict())
    case.record("deallocate_point", ["com"], sheet.deallocate_point("com"), sheet.to_dict())
    for bonus_type in sorted(attributes._BONUS_RATES):
        case.record("get_bonus", [bonus_type], sheet.get_bonus(bonus_type), sheet.to_dict())
    for milestone_id in ("first_trade", "first_trade", "not_a_milestone"):
        result = sheet.award_milestone(milestone_id)  # the repeat and the unknown id fail
        case.record("award_milestone", [milestone_id], result, sheet.to_dict())
    return case


def _social(profile: str) -> Case:
    case = Case("skills", f"social_checks_{profile}", {"profile": profile})
    manager = SocialManager()
    if profile == "expert":
        prog = PlayerProgression()
        for node in prog.skills.values():
            node.current_level = node.max_level
        manager.set_progression(prog)
    for skill_id in SOCIAL_SKILL_DEFINITIONS:
        for difficulty in range(1, 7):
            result = manager.resolve_check(skill_id, difficulty, "npc_parity")
            case.record(
                "resolve_check", [skill_id, difficulty, "npc_parity"], result, manager.get_state()
            )
    return case


def build_cases() -> list[Case]:
    """Every skill, attribute, and social-check case."""
    return [
        _catalog(),
        *[_learn_tree(tree) for tree in SkillTreeType],
        _all_bonuses(),
        _xp_curve(),
        _attributes(),
        _social("novice"),
        _social("expert"),
    ]
