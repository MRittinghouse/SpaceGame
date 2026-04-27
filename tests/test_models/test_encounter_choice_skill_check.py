"""CE-4a: encounter choice skill_check + failure_outcome + requires_credits.

Schema test: data loader parses the new fields and the model exposes
them. View-side resolution lives in test_views/test_encounter_view_ce4.py.
"""

from __future__ import annotations

from spacegame.data_loader import DataLoader
from spacegame.models.encounter import (
    EncounterChoice,
    EncounterDefinition,
    EncounterOutcome,
    EncounterSkillCheck,
)
from spacegame.models.mission import MissionReward


class TestEncounterSkillCheckModel:
    def test_skill_check_dataclass_round_trip(self) -> None:
        sc = EncounterSkillCheck(
            skill="persuasion",
            difficulty=3,
            set_flag_on_success="my_flag_pass",
            set_flag_on_failure="my_flag_fail",
        )
        assert sc.skill == "persuasion"
        assert sc.difficulty == 3
        assert sc.set_flag_on_success == "my_flag_pass"
        assert sc.set_flag_on_failure == "my_flag_fail"

    def test_choice_with_skill_check_carries_failure_outcome(self) -> None:
        outcome = EncounterOutcome(description="ok", rewards=[])
        failure = EncounterOutcome(description="fight", rewards=[], leads_to_combat=True)
        choice = EncounterChoice(
            id="talk_down",
            label="Talk",
            description="d",
            outcome=outcome,
            skill_check=EncounterSkillCheck("persuasion", 3),
            failure_outcome=failure,
            requires_credits=0,
        )
        assert choice.skill_check is not None
        assert choice.failure_outcome is failure
        assert choice.failure_outcome.leads_to_combat

    def test_choice_defaults_remain_optional(self) -> None:
        """Existing encounters without new fields still construct cleanly."""
        choice = EncounterChoice(
            id="x",
            label="x",
            description="",
            outcome=EncounterOutcome(description="", rewards=[]),
        )
        assert choice.skill_check is None
        assert choice.failure_outcome is None
        assert choice.requires_credits == 0


class TestParseChoiceSkillCheck:
    def test_parser_threads_skill_check(self) -> None:
        dl = DataLoader()
        raw = {
            "id": "ce4_test",
            "encounter_type": "ransom_demand",
            "name": "T",
            "description": "d",
            "choices": [
                {
                    "id": "talk",
                    "label": "Talk",
                    "description": "",
                    "skill_check": {
                        "skill": "persuasion",
                        "difficulty": 3,
                        "set_flag_on_success": "ce4_pass_flag",
                    },
                    "outcome": {"description": "ok", "rewards": []},
                    "failure_outcome": {
                        "description": "fight",
                        "rewards": [],
                        "leads_to_combat": True,
                    },
                }
            ],
        }
        defn = dl._parse_encounter_definition(raw)
        choice = defn.choices[0]
        assert choice.skill_check is not None
        assert choice.skill_check.skill == "persuasion"
        assert choice.skill_check.difficulty == 3
        assert choice.skill_check.set_flag_on_success == "ce4_pass_flag"
        assert choice.failure_outcome is not None
        assert choice.failure_outcome.leads_to_combat

    def test_parser_threads_requires_credits(self) -> None:
        dl = DataLoader()
        raw = {
            "id": "ce4_pay",
            "encounter_type": "ransom_demand",
            "name": "T",
            "description": "d",
            "choices": [
                {
                    "id": "pay",
                    "label": "Pay",
                    "description": "",
                    "requires_credits": 200,
                    "outcome": {"description": "ok", "rewards": []},
                }
            ],
        }
        defn = dl._parse_encounter_definition(raw)
        assert defn.choices[0].requires_credits == 200

    def test_parser_handles_missing_optional_fields(self) -> None:
        """Schema is backward-compatible — old encounter JSON still loads."""
        dl = DataLoader()
        raw = {
            "id": "old_style",
            "encounter_type": "distress_signal",
            "name": "T",
            "description": "d",
            "choices": [
                {
                    "id": "help",
                    "label": "Help",
                    "description": "",
                    "outcome": {"description": "ok", "rewards": []},
                }
            ],
        }
        defn = dl._parse_encounter_definition(raw)
        choice = defn.choices[0]
        assert choice.skill_check is None
        assert choice.failure_outcome is None
        assert choice.requires_credits == 0


class TestCe4PressureFileLoads:
    """Sanity check: the CE-4a template encounter file parses end-to-end."""

    def test_ransom_pirate_corvette_loads(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        match = [d for d in dl.encounter_definitions if d.id == "ransom_pirate_corvette_01"]
        assert len(match) == 1, "CE-4a template encounter missing"
        defn = match[0]
        assert defn.encounter_type == "ransom_demand"
        # Pay (requires_credits 200), talk_down (skill_check + failure → combat),
        # threaten (skill_check + failure → combat), refuse (combat)
        assert len(defn.choices) == 4
        pay = defn.choices[0]
        talk = defn.choices[1]
        threaten = defn.choices[2]
        refuse = defn.choices[3]
        assert pay.requires_credits == 200
        assert talk.skill_check is not None and talk.skill_check.skill == "persuasion"
        assert talk.failure_outcome is not None
        assert talk.failure_outcome.leads_to_combat
        assert threaten.skill_check.skill == "intimidation"
        assert threaten.skill_check.difficulty == 4
        assert refuse.outcome.leads_to_combat
