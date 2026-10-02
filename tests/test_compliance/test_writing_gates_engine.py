"""The prose gates' engine on synthetic strings, and its walkers (writing discipline spec 5.1).

The gates themselves run over the shipped data and code in tests/test_writing_bible_compliance.py;
this module pins what each rule catches and what it lets through, so a regex edit cannot widen or
narrow a gate unseen, and pins the walkers that find the strings.
"""

from __future__ import annotations

from tests.writing_gates import surfaces
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
            for node in tree["nodes"]:  # type: ignore[union-attr]
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
