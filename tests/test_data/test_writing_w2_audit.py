"""Plan W2-S's done-test (writing-discipline spec 9.4): the narrator audit's lines landed.

The gates prove the rows they read; this proves the rest. For each file in DONE_FILES, every
worklist entry's string is its new line, every audit excerpt is gone, every brace is kept, and
every skipped line (W3's, SP10's, the archive's) is exactly as shipped. Each rewrite task adds its
files; Task 11 requires every file of the worklist to be here.
"""

from __future__ import annotations

import pytest

from tools.writing import w2_audit

DONE_FILES: tuple[str, ...] = (
    "data/auctions/stellaris_voices.json",
    "data/combat/complications.json",
    "data/combat/enemies.json",
    "data/crew/crew_members.json",
    "data/crew/station_chatter.json",
    "data/dialogue/dialogues.json",
    "data/economy/news_templates.json",
    "data/encounters/campaign.json",
    "data/encounters/ce4_pressure.json",
    "data/encounters/ce4_variety.json",
    "data/encounters/commerce_guild.json",
    "data/encounters/frontier_alliance.json",
    "data/encounters/generic.json",
    "data/encounters/humor.json",
    "data/encounters/lore.json",
    "data/encounters/miners_union.json",
    "data/encounters/science_collective.json",
    "data/encounters/system_specific.json",
    "data/galaxy/locations.json",
    "data/ground/campaign/mission_10_crimson_reach.json",
    "data/ground/campaign/mission_13_breakstone_tunnels.json",
    "data/ground/campaign/mission_14_iron_depths_facility.json",
    "data/ground/campaign/mission_16_pirate_base.json",
    "data/ground/campaign/mission_16_the_fulcrum.json",
    "data/journal/entries.json",
    "data/journal/travel_log_templates.json",
    "data/missions/crew_quests.json",
    "data/missions/missions.json",
    "data/missions/side_missions.json",
    "data/narrative/dilemmas/d1_vengeance_justice.json",
    "data/narrative/dilemmas/d2_wealth_community.json",
    "data/narrative/dilemmas/d3_power_revolution_empire.json",
    "data/narrative/dilemmas/d5_legacy_connection.json",
    "data/narrative/dilemmas/d6_preservation_empire.json",
    "data/narrative/lenses.json",
    "data/ships/modules.json",
)


def test_the_worklist_holds_every_open_audit_row() -> None:
    entries = w2_audit.load_worklist()
    assert sum(len(entry.rows) for entry in entries) == 567
    assert len({entry.id for entry in entries}) == len(entries)


def test_the_worklist_holds_every_named_line() -> None:
    entries = w2_audit.load_worklist()
    for named in w2_audit.NAMED:
        held = [
            entry.why
            for entry in entries
            if all(part in entry.gate_path for part in named.parts)
            and entry.gate_path.endswith(named.suffix)
            and (not named.text or entry.old == named.text)
        ]
        assert held == [named.why], named


@pytest.mark.parametrize("file", DONE_FILES)
def test_every_entry_of_a_done_file_landed(file: str) -> None:
    assert w2_audit.check(w2_audit.load_worklist(), {file}) == []


def test_every_file_is_done() -> None:
    assert set(DONE_FILES) == {entry.file for entry in w2_audit.load_worklist()}
