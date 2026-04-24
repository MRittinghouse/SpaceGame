"""CE-4 encounter content integrity.

Asserts the new pressure + variety encounters resolve cleanly:
- attached complication_ids exist in DataLoader.complications
- skill_check.skill names are real social skills
- failure_outcomes that lead_to_combat have either a baked enemy list or
  an encounter_type whose runtime spawn baker provides one
- enemy_template_ids on outcomes are real enemy templates
- type weight tables list the new encounter types
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.encounter import _NON_HOSTILE_WEIGHTS
from spacegame.models.social import SOCIAL_SKILL_DEFINITIONS

# CE-4 encounter types — every one of these should have authored content
# and every one should appear in the moderate / dangerous weight tables.
CE4_TYPES = {
    "ransom_demand",
    "cargo_shakedown",
    "distress_bait",
    "wandering_trader",
    "derelict_encounter",
}

# Encounter types that bake an enemy into the EncounterRef at travel time.
# Outcomes for these types may leave enemy_template_ids empty; the runtime
# fills it in. See models/encounter.py::check_travel_encounter.
TYPES_WITH_RUNTIME_ENEMY = {
    "ransom_demand",
    "cargo_shakedown",
    "distress_bait",
}


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


class TestCe4Coverage:
    def test_each_type_has_authored_content(self, dl) -> None:
        per_type: dict[str, int] = {t: 0 for t in CE4_TYPES}
        for defn in dl.encounter_definitions:
            if defn.encounter_type in per_type:
                per_type[defn.encounter_type] += 1
        for enc_type, count in per_type.items():
            assert count >= 4, (
                f"CE-4 type '{enc_type}' has {count} encounters, expected >=4"
            )

    def test_each_type_in_weight_tables(self) -> None:
        for enc_type in CE4_TYPES:
            assert enc_type in _NON_HOSTILE_WEIGHTS["dangerous"], (
                f"CE-4 type '{enc_type}' missing from dangerous weight table"
            )
            assert enc_type in _NON_HOSTILE_WEIGHTS["moderate"], (
                f"CE-4 type '{enc_type}' missing from moderate weight table"
            )


class TestCe4ComplicationsResolve:
    def test_distress_bait_uses_reinforcement_arrival(self, dl) -> None:
        """All distress_bait encounters should attach reinforcement_arrival —
        the trap-springs-shut feel is the whole point."""
        for defn in dl.encounter_definitions:
            if defn.encounter_type != "distress_bait":
                continue
            assert "reinforcement_arrival" in defn.complication_ids, (
                f"distress_bait encounter '{defn.id}' missing "
                f"reinforcement_arrival complication"
            )

    def test_derelict_encounter_uses_asteroid_closure(self, dl) -> None:
        """All derelict_encounter encounters should attach asteroid_closure
        for the tight-quarters board feel."""
        for defn in dl.encounter_definitions:
            if defn.encounter_type != "derelict_encounter":
                continue
            assert "asteroid_closure" in defn.complication_ids, (
                f"derelict_encounter '{defn.id}' missing asteroid_closure"
            )

    def test_all_ce4_complications_resolve(self, dl) -> None:
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for cid in defn.complication_ids:
                assert cid in dl.complications, (
                    f"CE-4 encounter '{defn.id}' references unknown "
                    f"complication '{cid}'"
                )


class TestCe4SkillChecks:
    def test_skill_names_resolve(self, dl) -> None:
        """Every CE-4 skill_check uses a real social skill id."""
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for choice in defn.choices:
                if choice.skill_check is None:
                    continue
                assert choice.skill_check.skill in SOCIAL_SKILL_DEFINITIONS, (
                    f"CE-4 encounter '{defn.id}' choice '{choice.id}' uses "
                    f"unknown skill '{choice.skill_check.skill}'"
                )

    def test_skill_check_difficulty_in_range(self, dl) -> None:
        """Difficulties stay in the 1-5 design range."""
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for choice in defn.choices:
                if choice.skill_check is None:
                    continue
                d = choice.skill_check.difficulty
                assert 1 <= d <= 5, (
                    f"CE-4 encounter '{defn.id}' choice '{choice.id}' has "
                    f"out-of-range difficulty {d}"
                )

    def test_skill_diversity_per_type(self, dl) -> None:
        """Each CE-4 type uses at least 2 different skills across its
        instances (encourages NV-7 spread)."""
        skills_by_type: dict[str, set[str]] = {t: set() for t in CE4_TYPES}
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for choice in defn.choices:
                if choice.skill_check is not None:
                    skills_by_type[defn.encounter_type].add(choice.skill_check.skill)
        for enc_type, skills in skills_by_type.items():
            assert len(skills) >= 2, (
                f"CE-4 type '{enc_type}' uses only {skills} — needs >=2 "
                f"different skills across its instances"
            )


class TestCe4CombatPaths:
    def test_combat_outcomes_have_resolvable_enemies(self, dl) -> None:
        """leads_to_combat outcomes either name templates that resolve OR
        belong to an encounter type whose runtime spawn fills enemies in."""
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for choice in defn.choices:
                outcomes = [choice.outcome]
                if choice.failure_outcome is not None:
                    outcomes.append(choice.failure_outcome)
                for o in outcomes:
                    if not o.leads_to_combat:
                        continue
                    if o.enemy_template_ids:
                        # Authored enemies — must resolve
                        for tid in o.enemy_template_ids:
                            assert tid in dl.enemy_templates, (
                                f"CE-4 encounter '{defn.id}' choice "
                                f"'{choice.id}' references unknown enemy "
                                f"template '{tid}'"
                            )
                    else:
                        # No authored enemies — runtime must bake one
                        assert defn.encounter_type in TYPES_WITH_RUNTIME_ENEMY, (
                            f"CE-4 encounter '{defn.id}' choice "
                            f"'{choice.id}' leads to combat without enemy "
                            f"templates and its type "
                            f"'{defn.encounter_type}' doesn't bake one"
                        )


class TestCe4OutcomeShape:
    def test_outcome_descriptions_non_empty(self, dl) -> None:
        for defn in dl.encounter_definitions:
            if defn.encounter_type not in CE4_TYPES:
                continue
            for choice in defn.choices:
                assert choice.outcome.description.strip(), (
                    f"CE-4 encounter '{defn.id}' choice '{choice.id}' has "
                    "empty outcome description"
                )
                if choice.failure_outcome is not None:
                    assert choice.failure_outcome.description.strip(), (
                        f"CE-4 encounter '{defn.id}' choice '{choice.id}' "
                        "has empty failure_outcome description"
                    )
