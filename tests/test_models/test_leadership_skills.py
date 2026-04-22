"""Tests for leadership skill bonus wiring into gameplay systems."""

from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatState,
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine
from spacegame.models.crew import CrewAbility, CrewRoster, CrewTemplate
from spacegame.models.progression import PlayerProgression


# ============================================================================
# Helpers
# ============================================================================


def _make_move(
    id: str = "blaster",
    name: str = "Blaster",
    damage: float = 10.0,
    energy_cost: int = 0,
    accuracy_modifier: int = 0,
) -> CombatMove:
    return CombatMove(
        id=id,
        name=name,
        description=f"{name} attack",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy_cost,
        accuracy_modifier=accuracy_modifier,
    )


def _make_enemy_template(
    hull: int = 200,
    shields: int = 0,
    evasion: int = 0,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id="pirate",
        name="Pirate",
        description="A pirate.",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull,
        shields=shields,
        energy=10,
        energy_regen=3,
        speed=8,
        evasion=evasion,
        accuracy=70,
        moves=[_make_move()],
        loot_table=[],
        negotiate_difficulty=3,
        flee_threshold=0.4,
        bribe_cost=0,
    )


def _make_player_state(
    crew_moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    return PlayerCombatState(
        hull=100,
        max_hull=100,
        shields=40,
        max_shields=40,
        energy=20,
        max_energy=20,
        energy_regen=5,
        speed=8,
        evasion=0,
        accuracy=95,
        equipment_moves=[_make_move("laser", "Laser", 20.0, 3)],
        crew_moves=crew_moves or [],
        active_effects=[],
        cooldowns={},
    )


def _make_progression_with_bonus(bonus_type: str, level: int) -> PlayerProgression:
    """Create a progression with a specific leadership skill active."""
    prog = PlayerProgression()
    # Find the skill node with the matching bonus_type and set its level
    for skill_id, node in prog.skills.items():
        if node.bonus_type == bonus_type:
            node.current_level = level
            break
    return prog


def _make_combat_state(
    crew_moves: list[CombatMove] | None = None,
    progression: PlayerProgression | None = None,
    seed: int = 42,
) -> CombatState:
    player = _make_player_state(crew_moves=crew_moves)
    templates = [_make_enemy_template()]
    encounter = CombatEncounter(enemy_templates=templates, encounter_seed=seed)
    enemies = [EnemyShip.from_template(t) for t in templates]
    return CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
        progression=progression,
    )


def _make_crew_template(
    template_id: str = "elena_reeves",
    name: str = "Elena Reeves",
    is_companion: bool = True,
) -> CrewTemplate:
    return CrewTemplate(
        id=template_id,
        name=name,
        role="navigator",
        description=f"Test crew: {name}",
        portrait_color=[100, 180, 255],
        abilities=[
            CrewAbility(
                bonus_type="fuel_efficiency_bonus",
                bonus_value=2.0,
                description="Test",
                unlock_level=1,
            )
        ],
        max_level=5,
        xp_thresholds=[0, 50, 150, 350, 700],
        is_companion=is_companion,
    )


def _make_roster() -> CrewRoster:
    templates = {
        "elena_reeves": _make_crew_template(),
        "marcus_jin": _make_crew_template("marcus_jin", "Marcus Jin"),
    }
    return CrewRoster(templates)


# ============================================================================
# 1. crew_combat_damage — crew abilities deal +15%/30% more damage
# ============================================================================


class TestCrewCombatDamage:
    """Crew combat abilities deal bonus damage with Battle Commander skill."""

    def test_no_bonus_without_skill(self) -> None:
        """Crew move damage is unmodified without the skill."""
        crew_move = _make_move("heal_pulse", "Heal Pulse", damage=50.0)
        state = _make_combat_state(crew_moves=[crew_move], progression=None)
        engine = CombatEngine(state, seed=1)
        enemy_hull_before = state.enemies[0].current_hull
        engine.execute_crew_moves(chosen_move_id="heal_pulse")
        damage_dealt = enemy_hull_before - state.enemies[0].current_hull
        assert damage_dealt == 50, f"Expected 50 damage, got {damage_dealt}"

    def test_level_1_gives_15_percent_bonus(self) -> None:
        """Level 1 crew_combat_damage gives +15% damage."""
        crew_move = _make_move("heal_pulse", "Heal Pulse", damage=100.0)
        prog = _make_progression_with_bonus("crew_combat_damage", 1)
        state = _make_combat_state(crew_moves=[crew_move], progression=prog)
        engine = CombatEngine(state, seed=1)
        enemy_hull_before = state.enemies[0].current_hull
        engine.execute_crew_moves(chosen_move_id="heal_pulse")
        damage_dealt = enemy_hull_before - state.enemies[0].current_hull
        # Int truncation in damage pipeline: expect ~115 (within ±1)
        assert 114 <= damage_dealt <= 116, f"Expected ~115 damage, got {damage_dealt}"

    def test_level_2_gives_30_percent_bonus(self) -> None:
        """Level 2 crew_combat_damage gives +30% damage."""
        crew_move = _make_move("heal_pulse", "Heal Pulse", damage=100.0)
        prog = _make_progression_with_bonus("crew_combat_damage", 2)
        state = _make_combat_state(crew_moves=[crew_move], progression=prog)
        engine = CombatEngine(state, seed=1)
        enemy_hull_before = state.enemies[0].current_hull
        engine.execute_crew_moves(chosen_move_id="heal_pulse")
        damage_dealt = enemy_hull_before - state.enemies[0].current_hull
        assert 129 <= damage_dealt <= 131, f"Expected ~130 damage, got {damage_dealt}"

    def test_bonus_does_not_apply_to_player_weapon(self) -> None:
        """crew_combat_damage does NOT affect player equipment attacks."""
        prog = _make_progression_with_bonus("crew_combat_damage", 2)
        state = _make_combat_state(progression=prog)
        cannon = _make_move("cannon", "Cannon", 100.0, 3)
        state.player.equipment_moves = [cannon]
        engine = CombatEngine(state, seed=1)
        enemy_hull_before = state.enemies[0].current_hull
        # Execute via single-move API (player move, not crew)
        engine.execute_player_move("cannon", target_idx=0)
        damage_dealt = enemy_hull_before - state.enemies[0].current_hull
        # Should NOT have 130 (crew bonus) — should be ~100
        assert 99 <= damage_dealt <= 101, (
            f"Player weapon should not get crew_combat_damage bonus, got {damage_dealt}"
        )


# ============================================================================
# 2. loyalty_floor — crew loyalty never drops below 30
# ============================================================================


class TestLoyaltyFloor:
    """Unbreakable Bonds skill prevents crew loyalty from dropping below floor."""

    def test_loyalty_floor_prevents_drop_below_30(self) -> None:
        """With loyalty_floor=30, loyalty cannot drop below 30."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.loyalty_floor = 30
        # Start at 30, try to lower
        roster.adjust_loyalty("elena_reeves", -50)
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        assert state["loyalty"] == 30, (
            f"Loyalty should be clamped to floor 30, got {state['loyalty']}"
        )

    def test_no_floor_without_skill(self) -> None:
        """Without the skill, loyalty can drop to 0."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.loyalty_floor = 0
        roster.adjust_loyalty("elena_reeves", -50)
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        assert state["loyalty"] == 0, (
            f"Loyalty should drop to 0 without floor, got {state['loyalty']}"
        )

    def test_floor_applies_to_all_crew(self) -> None:
        """Loyalty floor applies to all crew via adjust_loyalty_all."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.recruit("marcus_jin", 3)
        roster.loyalty_floor = 30
        roster.adjust_loyalty_all(-100)
        for tid in ["elena_reeves", "marcus_jin"]:
            state = roster.get_member_state(tid)
            assert state is not None
            assert state["loyalty"] >= 30, f"{tid} loyalty should be >= 30, got {state['loyalty']}"


# ============================================================================
# 3. legendary_captain — crew quests unlock 10 loyalty earlier
# ============================================================================


class TestLegendaryCaptainEarlyUnlock:
    """Legend of the Expanse makes crew quest loyalty flags fire 10 earlier."""

    def test_flags_fire_10_earlier_with_offset(self) -> None:
        """With loyalty_flag_offset=10, the 50-threshold flag fires at 40."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.loyalty_flag_offset = 10
        # Set loyalty to 35 (below normal 50 threshold, but above 40 effective)
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["loyalty"] = 35
        # Adjust by +10 to reach 45 (which crosses effective threshold of 40)
        flags = roster.adjust_loyalty("elena_reeves", 10)
        assert "crew_loyalty_elena_reeves_50" in flags, (
            f"Expected 50-threshold flag at loyalty 45 with offset 10, got {flags}"
        )

    def test_no_early_flags_without_offset(self) -> None:
        """Without the offset, loyalty 45 does not trigger the 50-threshold flag."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.loyalty_flag_offset = 0
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["loyalty"] = 35
        flags = roster.adjust_loyalty("elena_reeves", 10)
        assert "crew_loyalty_elena_reeves_50" not in flags, (
            "50-threshold flag should NOT fire at loyalty 45 without offset"
        )

    def test_70_threshold_fires_at_60_with_offset(self) -> None:
        """The 70-threshold flag fires at effective 60 with offset 10."""
        roster = _make_roster()
        roster.recruit("elena_reeves", 3)
        roster.loyalty_flag_offset = 10
        state = roster.get_member_state("elena_reeves")
        assert state is not None
        state["loyalty"] = 55
        flags = roster.adjust_loyalty("elena_reeves", 10)
        assert "crew_loyalty_elena_reeves_70" in flags, (
            f"Expected 70-threshold flag at loyalty 65 with offset 10, got {flags}"
        )


# ============================================================================
# 5. crew_quest_xp_bonus — tested indirectly via progression bonus check
# ============================================================================


class TestCrewQuestXpBonus:
    """Verify crew_quest_xp_bonus progression value is correct."""

    def test_shared_experience_level_1(self) -> None:
        """Level 1 gives 0.10 (10% bonus)."""
        prog = _make_progression_with_bonus("crew_quest_xp_bonus", 1)
        bonus = prog.get_bonus("crew_quest_xp_bonus")
        assert abs(bonus - 0.10) < 0.001, f"Expected 0.10, got {bonus}"

    def test_shared_experience_level_2(self) -> None:
        """Level 2 gives 0.20 (20% bonus)."""
        prog = _make_progression_with_bonus("crew_quest_xp_bonus", 2)
        bonus = prog.get_bonus("crew_quest_xp_bonus")
        assert abs(bonus - 0.20) < 0.001, f"Expected 0.20, got {bonus}"


# ============================================================================
# 4. dock_rep_bonus — tested via progression value check
# ============================================================================


class TestDockRepBonus:
    """Verify dock_rep_bonus progression value."""

    def test_captains_presence_gives_1(self) -> None:
        """Captain's Presence level 1 gives bonus value of 1.0."""
        prog = _make_progression_with_bonus("dock_rep_bonus", 1)
        bonus = prog.get_bonus("dock_rep_bonus")
        assert abs(bonus - 1.0) < 0.001, f"Expected 1.0, got {bonus}"
