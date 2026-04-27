"""CE-5c: crew interjection content integrity.

Asserts the authored crew interjections JSON loads cleanly and meets
narrative coverage / referential-integrity bars.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.crew_interjection import VALID_INTERJECTION_TRIGGERS

# Companions covered by CE-5 wave 1 (the 4 crew with full voice sheets).
COMPANION_CREW_IDS = {
    "elena_reeves",
    "marcus_jin",
    "dr_priya_osei",
    "tomas_drifter",
}


@pytest.fixture(scope="module")
def dl():
    loader = get_data_loader()
    loader.load_all()
    return loader


class TestInterjectionLoading:
    def test_bank_has_min_volume(self, dl) -> None:
        """CE-5 ships at least 30 lines across the bank."""
        line_count = sum(len(e.lines) for e in dl.crew_interjections)
        assert line_count >= 30, f"only {line_count} lines, expected >=30"

    def test_every_companion_has_entries(self, dl) -> None:
        per_crew: dict[str, int] = {cid: 0 for cid in COMPANION_CREW_IDS}
        for entry in dl.crew_interjections:
            if entry.crew_id in per_crew:
                per_crew[entry.crew_id] += 1
        for crew_id, count in per_crew.items():
            assert count >= 5, f"crew {crew_id} has {count} interjection entries, expected >=5"


class TestInterjectionStructure:
    def test_crew_ids_resolve(self, dl) -> None:
        """Every crew_id maps to a real crew template."""
        crew_template_ids = set(dl.crew_templates.keys())
        for entry in dl.crew_interjections:
            assert entry.crew_id in crew_template_ids, (
                f"unknown crew_id '{entry.crew_id}' in interjection bank"
            )

    def test_triggers_in_registry(self, dl) -> None:
        for entry in dl.crew_interjections:
            assert entry.trigger in VALID_INTERJECTION_TRIGGERS, (
                f"invalid trigger '{entry.trigger}' for crew {entry.crew_id}"
            )

    def test_lines_non_empty(self, dl) -> None:
        for entry in dl.crew_interjections:
            assert entry.lines, f"empty line bank for {entry.crew_id} / {entry.trigger}"
            for line in entry.lines:
                assert line.strip(), f"empty line for {entry.crew_id} / {entry.trigger}"

    def test_enemy_type_match_template_resolves(self, dl) -> None:
        for entry in dl.crew_interjections:
            if entry.trigger != "enemy_type_match":
                continue
            tid = entry.conditions.get("enemy_template_id", "")
            assert tid, f"{entry.crew_id} enemy_type_match missing template_id"
            assert tid in dl.enemy_templates, (
                f"{entry.crew_id} references unknown enemy template '{tid}'"
            )

    def test_combat_outcome_uses_valid_outcome(self, dl) -> None:
        valid_outcomes = {"", "victory", "defeat"}
        for entry in dl.crew_interjections:
            if entry.trigger != "combat_outcome":
                continue
            outcome = entry.conditions.get("outcome", "")
            assert outcome in valid_outcomes, (
                f"{entry.crew_id} has invalid combat_outcome '{outcome}'"
            )


class TestTriggerCoverage:
    def test_each_companion_covers_all_round_triggers(self, dl) -> None:
        """Every companion has lines for first_turn, player_low_hp,
        enemy_low_hp, and enemy_type_match — the round-tick palette."""
        round_triggers = {
            "first_turn",
            "player_low_hp",
            "enemy_low_hp",
            "enemy_type_match",
        }
        per_crew: dict[str, set[str]] = {cid: set() for cid in COMPANION_CREW_IDS}
        for entry in dl.crew_interjections:
            if entry.crew_id in per_crew:
                per_crew[entry.crew_id].add(entry.trigger)
        for crew_id, triggers in per_crew.items():
            missing = round_triggers - triggers
            assert not missing, f"crew {crew_id} missing round triggers: {missing}"

    def test_each_companion_covers_both_outcomes(self, dl) -> None:
        """Every companion has a victory line AND a defeat line."""
        per_crew: dict[str, set[str]] = {cid: set() for cid in COMPANION_CREW_IDS}
        for entry in dl.crew_interjections:
            if entry.trigger != "combat_outcome":
                continue
            if entry.crew_id in per_crew:
                outcome = entry.conditions.get("outcome", "")
                if outcome:
                    per_crew[entry.crew_id].add(outcome)
        for crew_id, outcomes in per_crew.items():
            assert outcomes == {"victory", "defeat"}, (
                f"crew {crew_id} outcome coverage = {outcomes}, expected both"
            )
