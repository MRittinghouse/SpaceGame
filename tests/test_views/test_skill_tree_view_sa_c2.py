"""SA-C2 layout regression tests for the skill tree view.

Verifies that after adding 7 new SA-arc skill nodes, the detail-view
layout algorithm (_compute_detail_positions) produces valid positions
for Commerce (14), Social (15), Leadership (13), and Industry (13)
trees at the base 720p resolution.

Checks per tree (per AC 8):
  (a) Every skill in the tree has a computed position.
  (b) Every position falls inside (DETAIL_LEFT, DETAIL_TOP,
      DETAIL_RIGHT, DETAIL_BOTTOM).
  (c) Within each depth column, sorted node centers are at least
      2 * NODE_RADIUS apart vertically (no overlap).

The algorithm is reproduced here rather than running the full view
lifecycle — same surgical approach as test_targeted_overlap.py.
If any assertion fails, the sprint files PHASE_BLOCKED rather than
patching the layout algorithm.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest

from spacegame.models.progression import PlayerProgression, SkillTreeType


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """Initialize pygame once for this module at base 720p resolution."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT

        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


def _compute_positions(
    skills: list,
) -> dict[str, tuple[int, int]]:
    """Replicate _compute_detail_positions from SkillTreeView.

    Returns mapping skill_id -> (x, y).
    """
    from spacegame.views.skill_tree_view import DETAIL_BOTTOM, DETAIL_LEFT, DETAIL_RIGHT, DETAIL_TOP

    skill_map = {s.id: s for s in skills}
    depths: dict[str, int] = {}

    def get_depth(sid: str) -> int:
        if sid in depths:
            return depths[sid]
        skill = skill_map.get(sid)
        if not skill or not skill.prerequisite_id or skill.prerequisite_id not in skill_map:
            depths[sid] = 0
            return 0
        d = get_depth(skill.prerequisite_id) + 1
        depths[sid] = d
        return d

    for s in skills:
        get_depth(s.id)

    by_depth: dict[int, list[str]] = {}
    for sid, d in depths.items():
        by_depth.setdefault(d, []).append(sid)

    max_depth = max(by_depth.keys()) if by_depth else 0

    available_w = DETAIL_RIGHT - DETAIL_LEFT
    available_h = DETAIL_BOTTOM - DETAIL_TOP
    col_spacing = available_w / max(1, max_depth) if max_depth > 0 else available_w

    positions: dict[str, tuple[int, int]] = {}
    for depth, sids in by_depth.items():
        x = DETAIL_LEFT + int(depth * col_spacing)
        count = len(sids)
        row_spacing = available_h / (count + 1)
        for j, sid in enumerate(sids):
            y = DETAIL_TOP + int((j + 1) * row_spacing)
            positions[sid] = (x, y)

    return positions


@pytest.mark.parametrize(
    "tree, expected_count",
    [
        (SkillTreeType.COMMERCE, 14),
        (SkillTreeType.SOCIAL, 15),
        (SkillTreeType.LEADERSHIP, 13),
        (SkillTreeType.INDUSTRY, 13),
    ],
)
class TestSAC2LayoutRegression:
    """Layout regression for the four SA-C2 affected trees at 720p."""

    def test_all_skills_have_positions(
        self, tree: SkillTreeType, expected_count: int
    ) -> None:
        """Every skill in the tree must receive a position."""
        prog = PlayerProgression()
        skills = prog.get_skill_tree(tree)
        assert len(skills) == expected_count, (
            f"{tree.value}: expected {expected_count} skills, got {len(skills)}"
        )
        positions = _compute_positions(skills)
        missing = [s.id for s in skills if s.id not in positions]
        assert not missing, f"{tree.value}: skills without positions: {missing}"

    def test_all_positions_inside_bounds(
        self, tree: SkillTreeType, expected_count: int
    ) -> None:
        """Every position must be inside the layout rectangle."""
        from spacegame.views.skill_tree_view import (
            DETAIL_BOTTOM,
            DETAIL_LEFT,
            DETAIL_RIGHT,
            DETAIL_TOP,
        )

        prog = PlayerProgression()
        skills = prog.get_skill_tree(tree)
        positions = _compute_positions(skills)

        violations = []
        for sid, (x, y) in positions.items():
            if not (DETAIL_LEFT <= x <= DETAIL_RIGHT and DETAIL_TOP <= y <= DETAIL_BOTTOM):
                violations.append(f"{sid}=({x},{y})")
        assert not violations, f"{tree.value}: out-of-bounds positions: {violations}"

    def test_no_column_overlap(
        self, tree: SkillTreeType, expected_count: int
    ) -> None:
        """Within each depth column, node centers must be >= 2*NODE_RADIUS apart."""
        from spacegame.views.skill_tree_view import NODE_RADIUS

        prog = PlayerProgression()
        skills = prog.get_skill_tree(tree)
        positions = _compute_positions(skills)

        # Group positions by x-column
        by_x: dict[int, list[int]] = {}
        for _sid, (x, y) in positions.items():
            by_x.setdefault(x, []).append(y)

        min_gap = 2 * NODE_RADIUS
        violations = []
        for x_col, ys in by_x.items():
            sorted_ys = sorted(ys)
            for i in range(len(sorted_ys) - 1):
                gap = sorted_ys[i + 1] - sorted_ys[i]
                if gap < min_gap:
                    violations.append(
                        f"column x={x_col}: gap {gap}px < {min_gap}px "
                        f"between y={sorted_ys[i]} and y={sorted_ys[i+1]}"
                    )
        assert not violations, f"{tree.value}: node overlap in columns: {violations}"
