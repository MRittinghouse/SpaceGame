"""The prose gates' engine on synthetic strings, and its walkers (writing discipline spec 5.1).

The gates themselves run over the shipped data and code in tests/test_writing_bible_compliance.py;
this module pins what each rule catches and what it lets through, so a regex edit cannot widen or
narrow a gate unseen, and pins the walkers that find the strings.
"""

from __future__ import annotations

import pytest

from tests.writing_gates import rules, surfaces
from tests.writing_gates.registry import tokens_for


class TestPaths:
    def test_unique_ids_name_list_elements(self) -> None:
        document = {"items": [{"id": "a", "t": "x"}, {"id": "b", "t": "y"}, {"t": "z"}]}
        paths = dict(surfaces.walk(document))
        assert paths[".items[id=a].t"] == "x"
        assert paths[".items[id=b].t"] == "y"
        assert paths[".items[2].t"] == "z"

    def test_a_shared_id_falls_back_to_the_index(self) -> None:
        document = {"items": [{"id": "a", "t": "x"}, {"id": "a", "t": "y"}]}
        paths = dict(surfaces.walk(document))
        assert paths[".items[0].t"] == "x"
        assert paths[".items[1].t"] == "y"

    def test_keys_starting_with_an_underscore_are_skipped(self) -> None:
        assert dict(surfaces.walk({"_comment": "note", "t": "x"})) == {".t": "x"}

    def test_resolve_follows_ids_and_indexes(self) -> None:
        document = {"items": [{"id": "a", "lines": ["one", "two"]}]}
        assert surfaces.resolve(document, ".items[id=a].lines[1]") == "two"
        assert surfaces.resolve(document, ".items[id=b].lines[1]") is None
        assert surfaces.resolve(document, ".items[id=a].lines[5]") is None

    def test_parent_path_drops_the_last_segment(self) -> None:
        assert surfaces.parent_path(".a[id=x].nodes[id=y].text") == ".a[id=x].nodes[id=y]"
        assert surfaces.parent_path(".a[id=x].lines[2]") == ".a[id=x].lines"


class TestTheRegistry:
    def test_the_registry_allows_a_surfaces_own_tokens_only(self) -> None:
        assert "shakedown_demand" in tokens_for("data/encounters/generic.json")
        assert "system" not in tokens_for("data/missions/missions.json")


class TestStringsBuiltInCode:
    """Spec 5.1 scopes G1 to G3, G5 and G10 to every player-facing string, code-built included."""

    SOURCE = (
        '"""A module docstring \N{EM DASH} skipped."""\n'
        "\n"
        "\n"
        "class Panel:\n"
        '    """A class docstring."""\n'
        "\n"
        "    def render(self, count: int) -> list[str]:\n"
        '        logger.info("a log line \N{EM DASH} skipped")\n'
        '        header = f"DOCKED \N{EM DASH} {count}"\n'
        '        return [header, "Empty - nothing here", "Empty - nothing here", "credits"]\n'
        "\n"
        "\n"
        'TITLE = "Dock fees apply."\n'
    )

    def test_scopes_repeats_docstrings_logs_and_identifiers(self) -> None:
        """Docstrings, logger arguments and identifiers are skipped; a repeat gets its #n."""
        assert surfaces.strings_in_source(self.SOURCE) == [
            ("Panel.render|DOCKED \N{EM DASH} ", "DOCKED \N{EM DASH} "),
            ("Panel.render|Empty - nothing here", "Empty - nothing here"),
            ("Panel.render|Empty - nothing here#2", "Empty - nothing here"),
            ("<module>|Dock fees apply.", "Dock fees apply."),
        ]


class TestTheChangeAndRomanceFields:
    """Spec 9.2 row 0 lands the fields: change on a node, romance on a tree, both booleans."""

    def test_change_sits_only_on_nodes_and_romance_only_on_trees(self) -> None:
        for file, _path, tree in surfaces.trees():
            assert "change" not in tree, (file, tree["id"])
            assert isinstance(tree.get("romance", False), bool), (file, tree["id"])
            for node in tree["nodes"]:  # type: ignore[attr-defined]
                assert "romance" not in node, (file, tree["id"], node["id"])
                assert isinstance(node.get("change", False), bool), (file, tree["id"], node["id"])


class TestSurfaceVolumes:
    """The walkers find the shipped corpus; a broken path must not read as a clean bill."""

    def test_volumes(self) -> None:
        assert len(surfaces.player_facing()) > 14_000
        assert len(surfaces.code_strings()) > 4_000
        assert len(surfaces.narration()) > 1_700
        assert len(surfaces.speech()) > 2_600
        assert len(surfaces.option_texts()) > 1_600
        assert len(surfaces.trees()) > 150
        assert len(surfaces.people()) > 190

    def test_the_code_frame_is_read(self) -> None:
        frames = [row for row in surfaces.narration() if row.file.endswith("capstone_view.py")]
        assert len(frames) == 1
        assert "This is who you have chosen" in frames[0].text


class TestG1Dashes:
    @pytest.mark.parametrize(
        "text",
        [
            "A \N{EM DASH} B",
            "word\N{EN DASH}word",
            "The dock -- the stamp",
            "Stop - now",
            "the dock . the stamp",
        ],
    )
    def test_each_dash_form_is_caught(self, text: str) -> None:
        assert any(pattern.search(text) for _rule, pattern in rules.G1_FORMS), text

    @pytest.mark.parametrize("text", ["pages 3\N{EN DASH}5", "a well-filed form", "Sector 7-G."])
    def test_digit_ranges_and_compound_words_pass(self, text: str) -> None:
        assert not any(pattern.search(text) for _rule, pattern in rules.G1_FORMS), text


class TestG3Tells:
    def test_whole_words_with_inflections(self) -> None:
        hits = [
            rule
            for rule, word in rules.G3_WORDS
            if rules.re.search(rf"(?i)\b{word}\b", "remarkably delving")
        ]
        assert hits == ["remarkable", "delve"]

    def test_a_word_inside_another_passes(self) -> None:
        text = "an unremarkable pipe"
        assert not any(rules.re.search(rf"(?i)\b{word}\b", text) for _rule, word in rules.G3_WORDS)


class TestG4Names:
    def test_banned_names_are_whole_words(self) -> None:
        name = rules.BANNED_NAMES[3].title()
        assert rules.G4_BANNED.search(f"Ask {name} at the desk.")
        assert not rules.G4_BANNED.search(f"A {name.lower()}thon shift.")

    def test_titles_are_dropped_before_the_first_name(self) -> None:
        assert rules.first_name("Customs Officer Larsen") == "larsen"
        assert rules.first_name("Sgt. Dima Harkov") == "dima"
        assert rules.first_name('"Wrench" Malia Torres') == "malia"

    def test_edit_distance(self) -> None:
        assert rules.edit_distance("oren", "orin") == 1
        assert rules.edit_distance("glyn", "glyn") == 0
        assert rules.edit_distance("tomas", "tomasz") == 1
        assert rules.edit_distance("glyn", "dex") == 4


class TestG5Address:
    @pytest.mark.parametrize(
        "text", ["Sorry, sir.", "Son, I been running", "All right, sweetheart, go."]
    )
    def test_vocative_address_is_caught(self, text: str) -> None:
        assert rules.G5_VOCATIVE.search(text), text

    @pytest.mark.parametrize("text", ["Sir Reginald signs.", "Her son works the dock.", "{sir}."])
    def test_non_vocative_uses_and_tokens_pass(self, text: str) -> None:
        assert not rules.G5_VOCATIVE.search(text), text

    def test_token_names_name_a_verb_token_v(self) -> None:
        text = "{They}{v:'s|'re} at {system}."
        assert rules.token_names(text) == ["They", "v", "system"]


class TestG6ToG8Narration:
    def test_filter_verbs_fail_and_direct_perception_passes(self) -> None:
        assert rules.G6_FILTER_VERBS.search("You notice the clerk's stamp.")
        assert rules.G6_FILTER_VERBS.search("You suddenly realize the hold is empty.")
        assert not rules.G6_FILTER_VERBS.search("You hear the clerk sigh.")

    def test_body_tells_fail(self) -> None:
        assert any(p.search("Your heart rate climbs.") for _r, p in rules.G7_BODY_TELLS)
        assert any(p.search("your hands are shaking") for _r, p in rules.G7_BODY_TELLS)
        assert not any(
            p.search("The panel's edge opens your palm.") for _r, p in rules.G7_BODY_TELLS
        )

    def test_feelings_and_motives_fail(self) -> None:
        for text in ("You feel uneasy.", "Not your problem.", "You can't afford to stop."):
            assert any(p.search(text) for _r, p in rules.G8_FEELINGS), text
        assert not any(p.search("You hit the throttle.") for _r, p in rules.G8_FEELINGS)


class TestG9Tags:
    @pytest.mark.parametrize(
        "tag",
        ["Persuasion 3", "Say nothing", "Leave", "Hand him the form.", "Continue", "Observation 2"],
    )
    def test_checks_known_tags_and_acts_pass(self, tag: str) -> None:
        assert rules.tag_verdict(tag) == "", tag

    def test_a_mood_fails(self) -> None:
        assert rules.tag_verdict("That math feels heavy.") == "mood"

    @pytest.mark.parametrize("tag", ["Understood.", "Observation", "Silence", "Go on."])
    def test_speech_and_bare_skills_fail(self, tag: str) -> None:
        assert rules.tag_verdict(tag) == "not an act", tag

    def test_every_act_verb_is_one_lowercase_word(self) -> None:
        verbs = rules.act_verbs()
        assert len(verbs) >= 30
        assert all(verb.isalpha() and verb.islower() for verb in verbs)
        assert not verbs & {"go", "tell", "hold", "drop"}

    def test_the_skills_match_the_social_model(self) -> None:
        from spacegame.models.social import SOCIAL_SKILL_DEFINITIONS

        assert set(SOCIAL_SKILL_DEFINITIONS) == rules.SKILLS

    @pytest.mark.parametrize(
        "text",
        [
            '[Observation 2] "You stopped at the name."',
            "[Observation 2] Hand him the manifest.",
            "[Observation 2] [Hand him the manifest.]",
        ],
    )
    def test_an_observation_followed_by_quoted_words_or_an_act_passes(self, text: str) -> None:
        assert rules.option_verdict(text) == ("", ""), text

    def test_an_observation_followed_by_an_unspoken_insight_fails(self) -> None:
        """The shipped tev_refining_intro.weigh_output reply (impact 7.145)."""
        text = "[Observation 2] His second tap was for him, not the scale."
        assert rules.option_verdict(text) == ("observation unquoted", "[Observation 2]")


class TestG10AndG11:
    def test_the_player(self) -> None:
        assert rules.G10_THE_PLAYER.search("This text tells the player what to do.")

    def test_warp_is_a_whole_word(self) -> None:
        assert rules.G11_WARP.search("the warp gate")
        assert not rules.G11_WARP.search("the signal warps and dissolves")

    def test_a_price_in_speech(self) -> None:
        assert rules.G11_PRICE.search("I'll pay the 250 credits.")
        assert rules.G11_PRICE.search("Sixty a unit is 60 CR.")
        assert not rules.G11_PRICE.search("Shaft 7 is closed.")


def _tree(*nodes: dict[str, object]) -> dict[str, object]:
    return {"id": "t", "start_node_id": nodes[0]["id"], "nodes": list(nodes)}


def _node(node_id: str, *next_ids: str | None, **extra: object) -> dict[str, object]:
    return {
        "id": node_id,
        "responses": [{"text": "x", "next_node_id": n} for n in next_ids],
        **extra,
    }


class TestG13:
    def test_four_nodes_without_an_exit_pass_and_five_fail(self) -> None:
        four = _tree(_node("a", "b"), _node("b", "c"), _node("c", "d"), _node("d", "e"), _node("e"))
        five = _tree(
            _node("a", "b"),
            _node("b", "c"),
            _node("c", "d"),
            _node("d", "e"),
            _node("e", "f"),
            _node("f"),
        )
        assert rules.longest_run_without_exit(four) == 4
        assert rules.longest_run_without_exit(five) == 5

    def test_a_reply_that_ends_the_conversation_is_an_exit(self) -> None:
        tree = _tree(_node("a", "b", None), _node("b", "a"))
        assert rules.longest_run_without_exit(tree) == 1

    def test_a_skill_check_with_branches_is_not_an_exit(self) -> None:
        check = {
            "skill": "observation",
            "difficulty": 2,
            "success_node_id": "b",
            "failure_node_id": "b",
        }
        tree = _tree(
            {"id": "a", "responses": [{"text": "x", "next_node_id": None, "skill_check": check}]},
            _node("b"),
        )
        assert rules.longest_run_without_exit(tree) == 1

    def test_a_loop_without_an_exit_fails(self) -> None:
        assert rules.longest_run_without_exit(_tree(_node("a", "b"), _node("b", "a"))) == float(
            "inf"
        )

    def test_the_change_node_carries_the_disposition_change(self) -> None:
        nodes = [_node("a", "b"), _node("b", "c"), _node("c", "d"), _node("d")]
        assert rules.change_verdict(_tree(*nodes)) == ""
        nodes[1]["change"] = True
        assert rules.change_verdict(_tree(*nodes)) == "b carries no disposition change"
        nodes[1]["responses"][0]["disposition_change"] = 5  # type: ignore[index]
        assert rules.change_verdict(_tree(*nodes)) == ""
        nodes[2]["change"] = True
        assert rules.change_verdict(_tree(*nodes)) == "2 nodes marked change"
