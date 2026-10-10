"""Writing plan W1's data rows (writing discipline spec section 7; 9.2 rows 1 to 3).

Each class pins one group of the rows the spec rules: the address fixes and M05's title, the
intro cards repaired in place, Marcus's timeline and the Log, and the renames.
"""

from __future__ import annotations

import re

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import Mission


def _node_text(tree_id: str, node_id: str) -> str:
    return get_data_loader().dialogue_trees[tree_id].nodes[node_id].text


def _mission(mission_id: str) -> Mission:
    return next(m for m in get_data_loader().missions if m.id == mission_id)


class TestAddress:
    """Spec 2.6: Larsen and Szabo address the captain through the table; Elena's slip has none."""

    def test_larsen_greets_through_the_table(self) -> None:
        assert (
            _node_text("larsen_customs", "greeting")
            == "I need your bill of landing, and your registration, {sir}."
        )

    def test_larsens_age_line_is_retired(self) -> None:
        assert _node_text("larsen_customs", "farewell") == "Good luck out there, {sir}. Fly smart."

    def test_elenas_slip_is_chief_for_every_captain(self) -> None:
        bank = next(
            b
            for b in get_data_loader().crew_interjections
            if b.crew_id == "elena_reeves" and b.trigger == "first_turn"
        )
        line = "Engagement window opens. Standard rules of evasion apply, Chief. Sorry. Captain."
        assert line in bank.lines

    def test_szabo_calls_the_captain_through_the_table(self) -> None:
        encounter = next(
            e for e in get_data_loader().encounter_definitions if e.id == "alliance_moonshine_01"
        )
        report = next(c for c in encounter.choices if c.id == "report")
        assert report.outcome.description.startswith(
            "Szabo scratches his chin. '{Son}, I been running"
        )

    def test_the_two_endearments_stay_as_written(self) -> None:
        """The author's ruling, 2026-10-02: a habit the speaker uses with anyone (spec 2.6)."""
        assert "sweetheart" in get_data_loader().captains["odalys_kindling"].surrender_line
        tariq = next(
            e
            for e in get_data_loader().encounter_definitions
            if e.id == "sys_stellaris_art_dealer_01"
        )
        sell_story = next(c for c in tariq.choices if c.id == "sell_story")
        assert "darling" in tariq.description
        assert "darling" in sell_story.outcome.description


class TestMissionTitles:
    def test_m05_is_deferred_and_keeps_its_id(self) -> None:
        mission = _mission("the_foremans_son")
        assert mission.name == "Deferred"
        assert "The one that came back deferred." in mission.description
        assert "buried" not in mission.description

    def test_larsen_is_he(self) -> None:
        description = _mission("bill_of_landing").description
        assert "the way he looks at your ship" in description
        assert not re.search(r"\bshe\b", description)
