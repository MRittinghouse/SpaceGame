"""Plan W2-S's residue check (writing-discipline spec 9.4, 11.2): W2's fixes hold after the merge.

The gates prove the rows they read; this guards the rest. For each file in DONE_FILES, no audit
excerpt of a worklist entry is back in its string. Later chunks (W3 to W8, SP10) rewrite these
lines freely: a string need not equal W2's new line, so long as the offending clause stays out.
The worklist still holds every open audit row and every named line, and every file of the
worklist is here.
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
def test_no_audit_excerpt_comes_back(file: str) -> None:
    """After W2, W3 to W8 and SP10 may rewrite these lines; the audit's clauses stay out."""
    assert w2_audit.residue(w2_audit.load_worklist(), {file}) == []


def test_every_file_is_done() -> None:
    assert set(DONE_FILES) == {entry.file for entry in w2_audit.load_worklist()}
