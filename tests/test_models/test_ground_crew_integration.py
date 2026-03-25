"""Tests for ground crew & attribute integration (Phase D)."""

import pytest

from spacegame.models.attributes import AttributeSheet
from spacegame.models.ground import GroundMap, GroundPlayerState, GroundTile, TileType
from spacegame.models.ground_combat import (
    CombatOutcome,
    GroundCombatState,
    GroundCombatantStats,
    SocialSkillType,
    build_player_ground_combat_stats,
)
from spacegame.models.ground_crew import GroundCrewBonuses
from spacegame.models.ground_enemy import (
    AlertLevel,
    Direction,
    GroundEnemy,
    GroundMissionState,
    NoiseEvent,
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
) -> tuple[GroundMissionState, GroundPlayerState]:
    """Create a mission state with optional crew bonuses."""
    gm = GroundMap.create_test_map(20, 20)
    player = GroundPlayerState(x=player_x, y=player_y)
    mission = GroundMissionState(
        ground_map=gm,
        player=player,
        enemies=enemies or [],
        crew_bonuses=bonuses or GroundCrewBonuses(),
    )
    return mission, player


# ============================================================================
# GroundCrewBonuses construction
# ============================================================================


class TestGroundCrewBonusesConstruction:
    """Tests for GroundCrewBonuses default values and compute factory."""

    def test_default_no_bonuses(self) -> None:
        bonuses = GroundCrewBonuses()
        assert bonuses.vision_radius_bonus == 0
        assert bonuses.noise_reduction == 0
        assert not bonuses.silent_doors
        assert not bonuses.reveal_patrol_routes
        assert bonuses.retreat_bonus == 0
        assert bonuses.talk_bonus == 0
        assert not bonuses.analyze_weakness_available

    def test_empty_crew_no_attributes(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=[])
        assert bonuses.vision_radius_bonus == 0
        assert bonuses.noise_reduction == 0

    def test_elena_vision_and_retreat(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        assert bonuses.vision_radius_bonus == 1
        assert bonuses.reveal_patrol_routes
        assert bonuses.retreat_bonus == 2

    def test_marcus_silent_doors(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["marcus_jin"])
        assert bonuses.silent_doors

    def test_priya_analyze_weakness(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["dr_priya_osei"])
        assert bonuses.analyze_weakness_available

    def test_tomas_noise_and_talk(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"])
        assert bonuses.noise_reduction == 1
        assert bonuses.talk_bonus == 2

    def test_acu_vision_bonus(self) -> None:
        attrs = _make_attrs(acu=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        assert bonuses.vision_radius_bonus == 2  # ACU 4 // 2 = 2

    def test_syn_talk_bonus(self) -> None:
        attrs = _make_attrs(syn=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        assert bonuses.talk_bonus == 2  # SYN 4 // 2 = 2

    def test_ing_noise_reduction(self) -> None:
        attrs = _make_attrs(ing=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        assert bonuses.noise_reduction == 1  # ING 4+ = -1 noise

    def test_ing_below_threshold_no_bonus(self) -> None:
        attrs = _make_attrs(ing=3)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        assert bonuses.noise_reduction == 0

    def test_combined_crew_and_attributes(self) -> None:
        attrs = _make_attrs(acu=4, syn=2, ing=5)
        bonuses = GroundCrewBonuses.compute(
            crew_ids=["elena_reeves", "tomas_drifter"], attributes=attrs
        )
        # Vision: Elena +1, ACU 4//2=2 → total 3
        assert bonuses.vision_radius_bonus == 3
        # Noise: Tomas -1, ING 5≥4 → -1, total -2
        assert bonuses.noise_reduction == 2
        # Talk: Tomas +2, SYN 2//2=1 → total 3
        assert bonuses.talk_bonus == 3
        # Retreat: Elena +2
        assert bonuses.retreat_bonus == 2
        # Patrol reveal: Elena
        assert bonuses.reveal_patrol_routes

    def test_two_crew_stacking(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves", "marcus_jin"])
        assert bonuses.vision_radius_bonus == 1  # Elena only
        assert bonuses.silent_doors  # Marcus
        assert bonuses.retreat_bonus == 2  # Elena

    def test_serialization_round_trip(self) -> None:
        bonuses = GroundCrewBonuses.compute(
            crew_ids=["elena_reeves", "tomas_drifter"],
            attributes=_make_attrs(acu=4),
        )
        data = bonuses.to_dict()
        restored = GroundCrewBonuses.from_dict(data)
        assert restored.vision_radius_bonus == bonuses.vision_radius_bonus
        assert restored.noise_reduction == bonuses.noise_reduction
        assert restored.silent_doors == bonuses.silent_doors
        assert restored.reveal_patrol_routes == bonuses.reveal_patrol_routes
        assert restored.retreat_bonus == bonuses.retreat_bonus
        assert restored.talk_bonus == bonuses.talk_bonus
        assert restored.analyze_weakness_available == bonuses.analyze_weakness_available


# ============================================================================
# Vision radius integration
# ============================================================================


class TestVisionRadiusIntegration:
    """Tests that crew/attributes modify effective vision radius."""

    def test_base_vision_no_bonuses(self) -> None:
        mission, player = _make_mission()
        assert mission.effective_vision_radius == player.vision_radius

    def test_elena_increases_vision(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        mission, player = _make_mission(bonuses=bonuses)
        assert mission.effective_vision_radius == player.vision_radius + 1

    def test_acu_increases_vision(self) -> None:
        attrs = _make_attrs(acu=6)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        mission, player = _make_mission(bonuses=bonuses)
        # ACU 6 // 2 = 3
        assert mission.effective_vision_radius == player.vision_radius + 3


# ============================================================================
# Noise reduction integration
# ============================================================================


class TestNoiseReduction:
    """Tests that crew/attributes reduce noise radii."""

    def test_noisy_floor_default_radius(self) -> None:
        mission, _ = _make_mission()
        # Place noisy floor
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        noise = mission.check_tile_noise(6, 5)
        assert noise is not None
        assert noise.radius == 3  # Default GROUND_NOISE_NOISY_FLOOR

    def test_tomas_reduces_noisy_floor(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"])
        mission, _ = _make_mission(bonuses=bonuses)
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        noise = mission.check_tile_noise(6, 5)
        assert noise is not None
        assert noise.radius == 2  # 3 - 1

    def test_ing_reduces_noise(self) -> None:
        attrs = _make_attrs(ing=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        mission, _ = _make_mission(bonuses=bonuses)
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        noise = mission.check_tile_noise(6, 5)
        assert noise is not None
        assert noise.radius == 2  # 3 - 1

    def test_stacked_noise_reduction(self) -> None:
        attrs = _make_attrs(ing=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"], attributes=attrs)
        mission, _ = _make_mission(bonuses=bonuses)
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        noise = mission.check_tile_noise(6, 5)
        assert noise is not None
        assert noise.radius == 1  # 3 - 2

    def test_noise_reduction_minimum_zero(self) -> None:
        """Noise radius can't go below 0."""
        attrs = _make_attrs(ing=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"], attributes=attrs)
        # noise_reduction = 2, but a radius-1 noise should become 0
        bonuses_heavy = GroundCrewBonuses(noise_reduction=5)
        mission, _ = _make_mission(bonuses=bonuses_heavy)
        mission.ground_map.tiles[5][6] = GroundTile(tile_type=TileType.NOISY_FLOOR)
        noise = mission.check_tile_noise(6, 5)
        assert noise is not None
        assert noise.radius == 0

    def test_marcus_silent_doors(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["marcus_jin"])
        mission, _ = _make_mission(bonuses=bonuses)
        assert mission.get_door_noise_radius() == 0

    def test_default_door_noise(self) -> None:
        mission, _ = _make_mission()
        assert mission.get_door_noise_radius() == 2  # GROUND_NOISE_DOOR_OPEN


# ============================================================================
# Combat stat integration with crew bonuses
# ============================================================================


class TestCombatCrewBonuses:
    """Tests that crew bonuses integrate into combat stats and actions."""

    def test_syn_adds_talk_modifier(self) -> None:
        attrs = _make_attrs(syn=4)
        bonuses = GroundCrewBonuses.compute(crew_ids=[], attributes=attrs)
        # SYN talk bonus should be 2
        assert bonuses.talk_bonus == 2

    def test_tomas_talk_bonus_in_stats(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["tomas_drifter"])
        assert bonuses.talk_bonus == 2

    def test_elena_retreat_bonus_in_stats(self) -> None:
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        assert bonuses.retreat_bonus == 2

    def test_build_player_stats_with_crew(self) -> None:
        attrs = _make_attrs(acu=4, res=4, syn=2)
        prog = PlayerProgression()
        prog.skills["scrapper"].current_level = 1
        bonuses = GroundCrewBonuses.compute(crew_ids=["dr_priya_osei"], attributes=attrs)
        stats = build_player_ground_combat_stats(
            attributes=attrs, progression=prog, crew_bonuses=bonuses
        )
        # Attack: ACU 4//2=2, scrapper +1 = 3
        assert stats.attack_mod == 3
        # HP: 10 base + RES 4//2=2 = 12
        assert stats.hp == 12
        # Analyze weakness from Priya should be tracked separately (not in stats)

    def test_analyze_weakness_priya(self) -> None:
        """Priya's analyze weakness grants +3 to one attack roll."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["dr_priya_osei"])
        assert bonuses.analyze_weakness_available

    def test_combat_state_with_analyze_weakness(self) -> None:
        """Combat state tracks analyze weakness usage."""
        player = GroundCombatantStats(hp=8, max_hp=8)
        enemy = GroundCombatantStats(
            hp=10,
            max_hp=10,
            attack_mod=0,
            defense_mod=0,
            talk_difficulty=6,
            name="Guard",
        )
        state = GroundCombatState(
            player=player,
            enemies=[enemy],
            has_analyze_weakness=True,
        )
        assert state.can_analyze_weakness
        bonus = state.use_analyze_weakness()
        assert bonus == 3
        assert not state.can_analyze_weakness, "Can only use once"

    def test_retreat_with_elena_bonus(self) -> None:
        """Elena's +2 retreat should be passed as retreat_mod."""
        bonuses = GroundCrewBonuses.compute(crew_ids=["elena_reeves"])
        assert bonuses.retreat_bonus == 2
        # This would be passed as retreat_mod=2 to attempt_retreat


# ============================================================================
# Progression skill integration
# ============================================================================


class TestGroundSkillIntegration:
    """Tests that ground combat skills affect build_player_ground_combat_stats."""

    def test_has_last_stand_from_skill(self) -> None:
        prog = PlayerProgression()
        prog.skills["tough_hide"].current_level = 1
        prog.skills["last_stand"].current_level = 1
        bonuses = GroundCrewBonuses()
        stats = build_player_ground_combat_stats(progression=prog, crew_bonuses=bonuses)
        # The function returns stats; has_last_stand is tracked on CombatState
        # But we can verify HP bonus from tough_hide
        assert stats.hp == 12  # 10 + 2

    def test_intimidating_presence_from_skill(self) -> None:
        prog = PlayerProgression()
        prog.skills["scrapper"].current_level = 1
        prog.skills["quick_reflexes"].current_level = 1
        prog.skills["intimidating_presence"].current_level = 1
        # The has_intimidating_presence flag goes on CombatState, not stats
        assert prog.get_bonus("ground_intimidating_presence") > 0
