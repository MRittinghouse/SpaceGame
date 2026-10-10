"""Writing plan W1's data rows (writing discipline spec section 7; 9.2 rows 1 to 3).

Each class pins one group of the rows the spec rules: the address fixes and M05's title, the
intro cards repaired in place, Marcus's timeline and the Log, and the renames.
"""

from __future__ import annotations

import re
from pathlib import Path

from spacegame.data_loader import get_data_loader
from spacegame.models.mission import Mission
from tests.writing_gates.surfaces import player_facing

REPO_ROOT = Path(__file__).resolve().parents[2]


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


CARD_1 = (
    "You spend a week cleaning out your father's bunk. Coveralls, a few tools, a wedding ring."
    " The trading post buys the rest. What's left of his savings goes in the same pocket."
)
CARD_2 = (
    "The scrapyard drydock smells like ozone and bad coolant. The mechanic from maintenance has"
    ' a salvaged shuttle frame waiting under a tarp. He pulls it back and looks at you. "You'
    " count what you've got. I'll show you what fits. We don't waste a credit if we can help"
    ' it."'
)
REPORT_DEFERRED = (
    "Nothing. Got filed. Came back stamped deferred. Every year, same stamp. Then the recyclers"
    " quit on your father's shift. He didn't come off it. Three others are still in medical"
    " with lung damage."
)
AUTO_M05 = (
    "Met Marcus Jin at Breakstone. Mining foreman, twenty years on station. He said his team"
    " flagged the air recyclers on the Nexus Prime orbital, and the report came back deferred."
)


class TestTheIntro:
    """Section 7: the cards repaired in place to the narrator contract until SP7's opening."""

    def test_two_cards_of_acts_and_objects(self) -> None:
        tree = get_data_loader().dialogue_trees["intro_narration"]
        assert tree.start_node_id == "intro_1"
        assert list(tree.nodes) == ["intro_1", "intro_2"]
        assert tree.nodes["intro_1"].text == CARD_1
        assert [r.next_node_id for r in tree.nodes["intro_1"].responses] == ["intro_2"]
        assert tree.nodes["intro_2"].text == CARD_2
        assert tree.nodes["intro_2"].responses == []

    def test_no_biography_memory_or_purse(self) -> None:
        tree = get_data_loader().dialogue_trees["intro_narration"]
        text = " ".join(node.text for node in tree.nodes.values()).lower()
        cuts = (
            "16th",
            "colony ship",
            "school",
            "grew up",
            "passed away",
            "remember",
            "hoped",
            "thousand",
            "hull and a promise",
            "used to look",
        )
        for cut in cuts:
            assert cut not in text, cut


class TestMarcusAndTheLog:
    """Impact 1b.7 and 1b.8: the timeline against a twenty-year-old."""

    def test_the_recognition_drops_the_date(self) -> None:
        assert (
            _node_text("marcus_recognition", "recognition")
            == "You related to someone who worked the Nexus Prime orbital? Mining crew?"
        )

    def test_marcus_says_the_death(self) -> None:
        assert _node_text("marcus_recognition", "report_buried") == REPORT_DEFERRED

    def test_his_age_at_the_flag_still_holds(self) -> None:
        """Twenty-four, about twenty years back: before the captain was born (spec 4.3)."""
        assert "twenty-four" in _node_text("marcus_recognition", "why_didnt_push")

    def test_the_log_records_what_marcus_said_and_never_the_death(self) -> None:
        entry = next(
            e for e in get_data_loader().journal_entries if e.entry_id == "auto_m05_marcus"
        )
        assert entry.text == AUTO_M05
        for cut in ("dead", "died", "buried", "my father"):
            assert cut not in entry.text.lower(), cut


class TestRenames:
    """Spec 10: Glyn Quintela for Dex Halloran, Mouthfeel for The Spacer's Palate; ids stay."""

    def test_the_fixer_is_glyn_quintela(self) -> None:
        npcs = get_data_loader().npcs
        ids = ("dex_halloran", "dex_tunnel_contact", "dex_final_lead")
        assert [npcs[npc_id].name for npc_id in ids] == ["Glyn Quintela"] * 3

    def test_no_player_facing_string_keeps_an_old_name(self) -> None:
        old = re.compile(r"Dex|Halloran|Spacer's Palate")
        assert not [(row.file, row.path) for row in player_facing() if old.search(row.text)]

    def test_orens_line_keeps_its_one_beat(self) -> None:
        line = _node_text("oren_tak_meeting", "suspicious")
        assert line.startswith("Glyn. That name buys you thirty seconds.")

    def test_the_show_is_mouthfeel(self) -> None:
        show = next(
            e for e in get_data_loader().encounter_definitions if e.id == "humor_cooking_show_01"
        )
        assert show.name == "Mouthfeel"
        assert "'Welcome back to Mouthfeel, the only culinary review show" in show.description

    def test_the_smuggling_code_names_glyn(self) -> None:
        source = (REPO_ROOT / "spacegame" / "models" / "smuggling.py").read_text(encoding="utf-8")
        assert "Dex Halloran" not in source
        assert source.count("Glyn Quintela") == 3
