"""Skills load from data/progression/skills.json (SP3 spec 6.4)."""

from __future__ import annotations

import dataclasses

from spacegame.models.progression import SkillNode, create_default_skills, load_skill_definitions


def _typed(node: SkillNode) -> list[tuple[str, object, type]]:
    return [
        (f.name, getattr(node, f.name), type(getattr(node, f.name)))
        for f in dataclasses.fields(node)
    ]


def _from_rows() -> dict[str, SkillNode]:
    from spacegame.models.progression import _node_from_row

    return {str(row["id"]): _node_from_row(row) for row in load_skill_definitions()}


class TestSkillsJson:
    def test_json_matches_the_coded_skills_exactly(self) -> None:
        coded = create_default_skills()
        loaded = _from_rows()
        assert list(loaded) == list(coded), "same ids in the same order"
        for skill_id, node in coded.items():
            assert _typed(loaded[skill_id]) == _typed(node), skill_id
