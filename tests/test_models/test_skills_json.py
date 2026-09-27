"""Skills load from data/progression/skills.json (SP3 spec 6.4)."""

from __future__ import annotations

from spacegame.models.progression import create_default_skills


class TestSkillsJson:
    def test_counts(self) -> None:
        skills = create_default_skills()
        assert len(skills) == 89
        assert len({s.bonus_type for s in skills.values()}) == 88
        per_tree: dict[str, int] = {}
        for s in skills.values():
            per_tree[s.tree.value] = per_tree.get(s.tree.value, 0) + 1
        assert per_tree == {
            "commerce": 14,
            "combat": 22,
            "exploration": 12,
            "leadership": 13,
            "social": 15,
            "industry": 13,
        }

    def test_prerequisites_exist(self) -> None:
        skills = create_default_skills()
        for s in skills.values():
            assert s.prerequisite_id is None or s.prerequisite_id in skills, s.id

    def test_every_call_returns_fresh_nodes(self) -> None:
        first = create_default_skills()
        first["negotiator"].current_level = 2
        assert create_default_skills()["negotiator"].current_level == 0

    def test_bonus_values_are_numbers_and_levels_ints(self) -> None:
        for s in create_default_skills().values():
            assert type(s.max_level) is int and type(s.cost_per_level) is int, s.id
            assert type(s.bonus_per_level) in (int, float), s.id
