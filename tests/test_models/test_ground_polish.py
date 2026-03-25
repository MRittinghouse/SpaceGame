"""Tests for ground system polish: attributes/progression passthrough,
patrol route reveal, COM loot bonus, and view-level crew wiring."""

import pytest

from spacegame.models.attributes import AttributeSheet
from spacegame.models.ground import GroundMap, GroundPlayerState, GroundTile, TileType
from spacegame.models.ground_combat import (
    CombatOutcome,
    GroundCombatState,
    GroundCombatantStats,
    build_player_ground_combat_stats,
    make_enemy_from_template,
)
from spacegame.models.ground_crew import GroundCrewBonuses
from spacegame.models.ground_enemy import (
    AlertLevel,
    Direction,
    GroundEnemy,
    GroundMissionState,
)
from spacegame.models.progression import PlayerProgression


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_attrs(**overrides: int) -> AttributeSheet:
    """Create an attribute sheet with specified values."""
    defaults = {"com": 1, "acu": 1, "res": 1, "ing": 1, "syn": 1}
    defaults.update(overrides)
    return AttributeSheet(values=defaults)


def _make_mission(
    player_x: int = 5,
    player_y: int = 5,
    enemies: list[GroundEnemy] | None = None,
    bonuses: GroundCrewBonuses | None = None,
    attributes: AttributeSheet | None = None,
    progression: PlayerProgression | None = None,
) -> tuple[GroundMissionState, GroundPlayerState]:
    """Create a mission state with optional crew bonuses + attributes."""
    gm = GroundMap.create_test_map(20, 20)
    player = GroundPlayerState(x=player_x, y=player_y)
    mission = GroundMissionState(
        ground_map=gm,
        player=player,
        enemies=enemies or [],
        crew_bonuses=bonuses or GroundCrewBonuses(),
        attributes=attributes,
        progression=progression,
    )
    return mission, player


# ============================================================================
# Gap 1: Attributes + Progression on GroundMissionState
# ============================================================================


class TestMissionStateAttributesProgression:
    """GroundMissionState carries attributes and progression for combat."""

    def test_mission_state_stores_attributes(self) -> None:
        attrs = _make_attrs(acu=4, res=4)
        mission, _ = _make_mission(attributes=attrs)
        assert mission.attributes is attrs

    def test_mission_state_stores_progression(self) -> None:
        prog = PlayerProgression()
        mission, _ = _make_mission(progression=prog)
        assert mission.progression is prog

    def test_mission_state_defaults_none(self) -> None:
        mission, _ = _make_mission()
        assert mission.attributes is None
        assert mission.progression is None

    def test_serialization_without_attrs_prog(self) -> None:
        """Attributes and progression are NOT serialized (computed at start)."""
        mission, _ = _make_mission()
        data = mission.to_dict()
        restored = GroundMissionState.from_dict(data)
        assert restored.attributes is None
        assert restored.progression is None

    def test_build_stats_with_attrs_and_prog(self) -> None:
        """build_player_ground_combat_stats uses attrs and progression."""
        attrs = _make_attrs(acu=4, res=4)
        prog = PlayerProgression()
        prog.add_xp(5200)
        prog.level_up_skill("scrapper")
        prog.level_up_skill("tough_hide")
        bonuses = GroundCrewBonuses()
        stats = build_player_ground_combat_stats(
            attributes=attrs, progression=prog, crew_bonuses=bonuses
        )
        # ACU 4 // 2 = 2 attack, scrapper +1 = 3
        assert stats.attack_mod == 3
        # Base 10 + RES 4//2=2 + tough_hide +2 = 14
        assert stats.hp == 14
        # RES 4//2 = 2 defense
        assert stats.defense_mod == 2


# ============================================================================
# Gap 2: Patrol Route Reveal
# ============================================================================


class TestPatrolRouteReveal:
    """Elena's reveal_patrol_routes exposes enemy patrol paths."""

    def test_patrol_tiles_not_revealed_by_default(self) -> None:
        enemy = GroundEnemy(
            id="guard",
            x=10,
            y=10,
            facing=Direction.RIGHT,
            patrol_route=[(10, 10), (15, 10), (15, 15), (10, 15)],
        )
        mission, _ = _make_mission(enemies=[enemy])
        revealed = mission.get_revealed_patrol_tiles()
        assert len(revealed) == 0

    def test_elena_reveals_patrol_tiles(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        enemy = GroundEnemy(
            id="guard",
            x=10,
            y=10,
            facing=Direction.RIGHT,
            patrol_route=[(10, 10), (15, 10)],
        )
        mission, _ = _make_mission(enemies=[enemy], bonuses=bonuses)
        revealed = mission.get_revealed_patrol_tiles()
        assert (10, 10) in revealed
        assert (15, 10) in revealed

    def test_multiple_enemies_routes_merged(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        e1 = GroundEnemy(
            id="a",
            x=3,
            y=3,
            patrol_route=[(3, 3), (5, 3)],
        )
        e2 = GroundEnemy(
            id="b",
            x=8,
            y=8,
            patrol_route=[(8, 8), (8, 10)],
        )
        mission, _ = _make_mission(enemies=[e1, e2], bonuses=bonuses)
        revealed = mission.get_revealed_patrol_tiles()
        assert (3, 3) in revealed
        assert (5, 3) in revealed
        assert (8, 8) in revealed
        assert (8, 10) in revealed

    def test_empty_patrol_route_no_tiles(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        enemy = GroundEnemy(id="guard", x=5, y=5, patrol_route=[])
        mission, _ = _make_mission(enemies=[enemy], bonuses=bonuses)
        revealed = mission.get_revealed_patrol_tiles()
        assert len(revealed) == 0


# ============================================================================
# Gap 3: COM → Loot Bonus
# ============================================================================


class TestGroundLootSystem:
    """COM attribute gives a % bonus to credits looted from defeated enemies."""

    def test_enemy_has_loot_credits(self) -> None:
        enemy = GroundEnemy(id="guard", x=5, y=5, loot_credits=50)
        assert enemy.loot_credits == 50

    def test_enemy_default_loot_zero(self) -> None:
        enemy = GroundEnemy(id="guard", x=5, y=5)
        assert enemy.loot_credits == 0

    def test_loot_credits_serialization(self) -> None:
        enemy = GroundEnemy(id="guard", x=5, y=5, loot_credits=75)
        data = enemy.to_dict()
        assert data["loot_credits"] == 75
        restored = GroundEnemy.from_dict(data)
        assert restored.loot_credits == 75

    def test_mission_calculate_loot_no_com(self) -> None:
        """Base loot with no COM bonus."""
        mission, _ = _make_mission()
        base_credits = 100
        total = mission.calculate_loot_credits(base_credits)
        assert total == 100

    def test_mission_calculate_loot_with_com(self) -> None:
        """COM 4 gives 20% loot bonus (COM // 2 * 10%)."""
        attrs = _make_attrs(com=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        mission, _ = _make_mission(bonuses=bonuses, attributes=attrs)
        base_credits = 100
        total = mission.calculate_loot_credits(base_credits)
        # COM 4 // 2 = 2, bonus = 2 * 10% = 20%
        assert total == 120

    def test_mission_calculate_loot_com_6(self) -> None:
        """COM 6 gives 30% loot bonus."""
        attrs = _make_attrs(com=6)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        mission, _ = _make_mission(bonuses=bonuses, attributes=attrs)
        assert mission.calculate_loot_credits(100) == 130

    def test_mission_calculate_loot_com_1(self) -> None:
        """COM 1 gives 0% bonus (1 // 2 = 0)."""
        attrs = _make_attrs(com=1)
        mission, _ = _make_mission(attributes=attrs)
        assert mission.calculate_loot_credits(100) == 100

    def test_collect_enemy_loot(self) -> None:
        """Collect total loot from a list of enemies."""
        e1 = GroundEnemy(id="a", x=5, y=5, loot_credits=30)
        e2 = GroundEnemy(id="b", x=6, y=5, loot_credits=50)
        mission, _ = _make_mission(enemies=[e1, e2])
        total = mission.collect_enemy_loot([e1, e2])
        assert total == 80  # No COM bonus

    def test_collect_enemy_loot_with_com(self) -> None:
        """COM bonus applies to total loot."""
        attrs = _make_attrs(com=4)
        e1 = GroundEnemy(id="a", x=5, y=5, loot_credits=50)
        e2 = GroundEnemy(id="b", x=6, y=5, loot_credits=50)
        mission, _ = _make_mission(enemies=[e1, e2], attributes=attrs)
        total = mission.collect_enemy_loot([e1, e2])
        # Base 100, COM 4 → 20% bonus → 120
        assert total == 120

    def test_loot_templates_have_credits(self) -> None:
        """Enemy templates should define loot_credits."""
        from spacegame.models.ground_combat import GROUND_ENEMY_TEMPLATES

        for tid, template in GROUND_ENEMY_TEMPLATES.items():
            assert "loot_credits" in template, f"{tid} missing loot_credits"
            assert template["loot_credits"] >= 0
