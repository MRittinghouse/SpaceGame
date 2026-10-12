"""Crew scenes: the record, the parse, the gate's six rules and their refusals (polish design 3.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spacegame.data_loader import DataLoader
from spacegame.models.crew_scene import (
    NEXT_PORT,
    NOT_ABOARD,
    NOTHING_NOW,
    WRONG_PLACE,
    CrewScene,
    CrewTalkRow,
    SceneContext,
    parse_scenes,
    place_hooks,
    refusal,
    talk_rows,
)

NAMES = {"elena_reeves": "Elena Reeves", "marcus_jin": "Marcus Jin"}
SYSTEMS = {"nexus_prime": "Nexus Prime", "stellaris_port": "Stellaris Port"}


def _opener(**overrides: Any) -> CrewScene:
    fields: dict[str, Any] = {
        "id": "elena_old_charts_opener",
        "quest_id": "elena_old_charts",
        "crew_id": "elena_reeves",
        "beat": "opener",
        "initiative": "crew",
        "dialogue_id": "elena_old_charts_dialogue",
        "entry_node": "start",
        "min_loyalty": 50,
        "excluded_flags": ("elena_old_charts_agreed", "elena_old_charts_declined"),
        "hook": "Captain, when you have a minute, I'd like to talk about Koren.",
    }
    fields.update(overrides)
    return CrewScene(**fields)


def _resolution(**overrides: Any) -> CrewScene:
    fields: dict[str, Any] = {
        "id": "elena_old_charts_resolution",
        "quest_id": "elena_old_charts",
        "crew_id": "elena_reeves",
        "beat": "resolution",
        "initiative": "crew",
        "dialogue_id": "elena_archives_dialogue",
        "entry_node": "start",
        "system_id": "stellaris_port",
        "excluded_flags": ("elena_archives_accessed",),
        "hook": "The archive terminal is in the Guild Quarter. My codes should still work.",
    }
    fields.update(overrides)
    return CrewScene(**fields)


def _raise(**overrides: Any) -> CrewScene:
    fields: dict[str, Any] = {
        "id": "elena_old_charts_raise",
        "quest_id": "elena_old_charts",
        "crew_id": "elena_reeves",
        "beat": "opener",
        "initiative": "captain",
        "dialogue_id": "elena_old_charts_dialogue",
        "entry_node": "ask_again",
        "min_loyalty": 50,
        "required_flags": ("elena_old_charts_declined",),
        "excluded_flags": ("elena_old_charts_agreed",),
    }
    fields.update(overrides)
    return CrewScene(**fields)


def _ctx(**overrides: Any) -> SceneContext:
    fields: dict[str, Any] = {
        "crew_names": NAMES,
        "loyalty": {"elena_reeves": 50},
        "loyalty_offset": 0,
        "statuses": {},
        "flags": {},
        "system_id": "nexus_prime",
        "system_names": SYSTEMS,
        "spoken": (),
    }
    fields.update(overrides)
    return SceneContext(**fields)


class TestTheRecord:
    def test_a_scene_reads_its_record(self) -> None:
        scene = CrewScene.from_dict(
            {
                "id": "s",
                "beat": "resolution",
                "initiative": "crew",
                "dialogue_id": "t",
                "entry_node": "start",
                "system_id": "forgeworks",
                "with_npc_id": "lira_feng",
                "required_flags": ["a"],
                "excluded_flags": ["b"],
                "hook": "h",
            },
            "q",
            "marcus_jin",
        )
        assert scene == CrewScene(
            id="s",
            quest_id="q",
            crew_id="marcus_jin",
            beat="resolution",
            initiative="crew",
            dialogue_id="t",
            entry_node="start",
            system_id="forgeworks",
            with_npc_id="lira_feng",
            min_loyalty=0,
            required_flags=("a",),
            excluded_flags=("b",),
            hook="h",
        )

    def test_parse_scenes_names_each_scenes_quest_and_companion(self) -> None:
        records = [
            {"id": "plain_mission"},
            {
                "id": "elena_old_charts",
                "crew_member_id": "elena_reeves",
                "scenes": [
                    {
                        "id": "a",
                        "beat": "opener",
                        "initiative": "crew",
                        "dialogue_id": "t",
                        "entry_node": "start",
                    },
                    {
                        "id": "b",
                        "beat": "resolution",
                        "initiative": "crew",
                        "dialogue_id": "u",
                        "entry_node": "start",
                    },
                ],
            },
        ]
        scenes = parse_scenes(records)
        assert list(scenes) == ["a", "b"]
        assert {(s.quest_id, s.crew_id) for s in scenes.values()} == {
            ("elena_old_charts", "elena_reeves")
        }

    def test_the_loader_keeps_scenes_beside_the_missions(self, tmp_path: Path) -> None:
        missions_dir = tmp_path / "missions"
        missions_dir.mkdir()
        (missions_dir / "missions.json").write_text('{"missions": []}', encoding="utf-8")
        record = {
            "id": "q",
            "name": "Q",
            "description": "",
            "mission_type": "crew",
            "crew_member_id": "elena_reeves",
            "scenes": [
                {
                    "id": "q_opener",
                    "beat": "opener",
                    "initiative": "crew",
                    "dialogue_id": "t",
                    "entry_node": "start",
                    "hook": "h",
                }
            ],
        }
        (missions_dir / "crew_quests.json").write_text(
            json.dumps({"missions": [record]}), encoding="utf-8"
        )
        loader = DataLoader(data_dir=tmp_path)
        loader.load_missions()
        assert [m.id for m in loader.missions] == ["q"]
        assert list(loader.crew_scenes) == ["q_opener"]
        assert loader.crew_scenes["q_opener"].quest_id == "q"


class TestTheGate:
    def test_an_opener_is_due_at_the_loyalty_mark_and_not_below_it(self) -> None:
        assert refusal(_opener(), _ctx()) == ""
        assert refusal(_opener(), _ctx(loyalty={"elena_reeves": 49})) == NOTHING_NOW.format(
            name="Elena Reeves"
        )

    def test_legend_lowers_the_mark_by_ten(self) -> None:
        ctx = _ctx(loyalty={"elena_reeves": 40}, loyalty_offset=10)
        assert refusal(_opener(), ctx) == ""
        ctx = _ctx(loyalty={"elena_reeves": 39}, loyalty_offset=10)
        assert refusal(_opener(), ctx) != ""

    def test_a_companion_not_aboard_is_refused_first(self) -> None:
        ctx = _ctx(loyalty={}, system_id="nexus_prime")
        assert refusal(_resolution(), ctx) == NOT_ABOARD.format(name="Elena Reeves")

    def test_an_opener_waits_for_the_accept_and_a_resolution_for_the_active_quest(self) -> None:
        active = _ctx(statuses={"elena_old_charts": "active"}, system_id="stellaris_port")
        assert refusal(_opener(), active) == NOTHING_NOW.format(name="Elena Reeves")
        assert refusal(_resolution(), active) == ""
        before = _ctx(system_id="stellaris_port")
        assert refusal(_resolution(), before) == NOTHING_NOW.format(name="Elena Reeves")
        done = _ctx(statuses={"elena_old_charts": "completed"}, system_id="stellaris_port")
        assert refusal(_resolution(), done) == NOTHING_NOW.format(name="Elena Reeves")
        assert refusal(_opener(), done) == NOTHING_NOW.format(name="Elena Reeves")

    def test_the_flags_allow_or_refuse(self) -> None:
        assert refusal(_opener(), _ctx(flags={"elena_old_charts_declined": True})) != ""
        assert refusal(_raise(), _ctx()) != ""
        assert refusal(_raise(), _ctx(flags={"elena_old_charts_declined": True})) == ""
        both = {"elena_old_charts_declined": True, "elena_old_charts_agreed": True}
        assert refusal(_raise(), _ctx(flags=both)) != ""

    def test_a_scene_at_a_place_names_it(self) -> None:
        ctx = _ctx(statuses={"elena_old_charts": "active"})
        assert refusal(_resolution(), ctx) == WRONG_PLACE.format(
            name="Elena Reeves", system="Stellaris Port"
        )

    def test_one_new_matter_a_landing(self) -> None:
        ctx = _ctx(spoken=("elena_reeves",))
        assert refusal(_opener(), ctx) == NEXT_PORT.format(name="Elena Reeves")

    def test_a_resolution_ignores_the_pace(self) -> None:
        ctx = _ctx(
            statuses={"elena_old_charts": "active"},
            system_id="stellaris_port",
            spoken=("elena_reeves",),
        )
        assert refusal(_resolution(), ctx) == ""

    def test_a_captain_topic_ignores_the_pace(self) -> None:
        ctx = _ctx(flags={"elena_old_charts_declined": True}, spoken=("elena_reeves",))
        assert refusal(_raise(), ctx) == ""

    def test_a_dismissed_companion_has_nothing_to_say_and_the_quest_resumes_when_rehired(
        self,
    ) -> None:
        statuses = {"elena_old_charts": "active"}
        gone = _ctx(loyalty={}, statuses=statuses, system_id="stellaris_port")
        assert refusal(_resolution(), gone) == NOT_ABOARD.format(name="Elena Reeves")
        back = _ctx(loyalty={"elena_reeves": 30}, statuses=statuses, system_id="stellaris_port")
        assert refusal(_resolution(), back) == ""

    def test_every_refusal_says_why(self) -> None:
        assert NOT_ABOARD.format(name="Elena Reeves") == "Elena Reeves is not aboard."
        assert NOTHING_NOW.format(name="Elena Reeves") == (
            "Elena Reeves has nothing to say about that now."
        )
        assert WRONG_PLACE.format(name="Elena Reeves", system="Stellaris Port") == (
            "Elena Reeves wants to talk about that at Stellaris Port."
        )
        assert NEXT_PORT.format(name="Elena Reeves") == (
            "Elena Reeves will bring it up at the next port."
        )


class TestTheRows:
    def test_each_companion_raises_one_matter_then_the_captains_topics_follow(self) -> None:
        marcus = _opener(
            id="marcus_old_debts_opener",
            quest_id="marcus_old_debts",
            crew_id="marcus_jin",
            dialogue_id="marcus_old_debts_dialogue",
            hook="There's something about Hargan Yards you should hear.",
        )
        second = _opener(id="elena_second_opener", quest_id="elena_second", hook="Another.")
        raised = _raise(
            id="marcus_raise",
            quest_id="marcus_other",
            crew_id="marcus_jin",
            required_flags=("marcus_other_declined",),
        )
        ctx = _ctx(
            loyalty={"elena_reeves": 50, "marcus_jin": 50},
            flags={"marcus_other_declined": True},
        )
        rows = talk_rows([raised, marcus, _opener(), second], ctx, ["marcus_jin", "elena_reeves"])
        assert rows == [
            CrewTalkRow("marcus_jin", "marcus_old_debts_opener", marcus.hook, "crew"),
            CrewTalkRow("elena_reeves", "elena_old_charts_opener", _opener().hook, "crew"),
            CrewTalkRow("marcus_jin", "marcus_raise", "", "captain"),
        ]

    def test_a_place_scene_announces_its_hook_there_and_an_opener_does_not(self) -> None:
        here = _ctx(statuses={"elena_old_charts": "active"}, system_id="stellaris_port")
        assert place_hooks([_opener(), _resolution()], here) == [
            ("Elena Reeves", _resolution().hook)
        ]
        away = _ctx(statuses={"elena_old_charts": "active"})
        assert place_hooks([_resolution()], away) == []
