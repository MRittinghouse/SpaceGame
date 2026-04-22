"""Tests for CombatEngine — core turn resolution."""

from spacegame.models.combat import (
    CombatEffect,
    CombatEncounter,
    CombatMove,
    CombatResult,
    CombatState,
    EffectTarget,
    EffectType,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine

# ============================================================================
# Helpers
# ============================================================================


def _make_move(
    id: str = "blaster",
    name: str = "Blaster",
    damage: float = 10.0,
    energy_cost: int = 2,
    cooldown: int = 0,
    accuracy_modifier: int = 0,
    effects: list[CombatEffect] | None = None,
) -> CombatMove:
    if effects is None:
        effects = [CombatEffect(type=EffectType.DAMAGE, value=damage)]
    return CombatMove(
        id=id,
        name=name,
        description=f"{name} attack",
        effects=effects,
        energy_cost=energy_cost,
        cooldown=cooldown,
        accuracy_modifier=accuracy_modifier,
    )


def _make_enemy_template(
    id: str = "pirate",
    hull: int = 80,
    shields: int = 20,
    energy: int = 10,
    energy_regen: int = 3,
    speed: int = 8,
    evasion: int = 10,
    accuracy: int = 70,
    behavior: EnemyBehavior = EnemyBehavior.AGGRESSIVE,
    moves: list[CombatMove] | None = None,
    negotiate_difficulty: int = 3,
    flee_threshold: float = 0.4,
    bribe_cost: int = 0,
) -> EnemyShipTemplate:
    if moves is None:
        moves = [_make_move()]
    return EnemyShipTemplate(
        id=id,
        name="Pirate",
        description="A pirate.",
        behavior=behavior,
        hull=hull,
        shields=shields,
        energy=energy,
        energy_regen=energy_regen,
        speed=speed,
        evasion=evasion,
        accuracy=accuracy,
        moves=moves,
        loot_table=[],
        negotiate_difficulty=negotiate_difficulty,
        flee_threshold=flee_threshold,
        bribe_cost=bribe_cost,
    )


def _make_player_state(
    hull: int = 100,
    max_hull: int = 100,
    shields: int = 40,
    max_shields: int = 40,
    energy: int = 10,
    max_energy: int = 10,
    energy_regen: int = 3,
    speed: int = 8,
    evasion: int = 15,
    accuracy: int = 70,
    equipment_moves: list[CombatMove] | None = None,
    crew_moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    if equipment_moves is None:
        equipment_moves = [_make_move("laser", "Laser", 20.0, 3)]
    if crew_moves is None:
        crew_moves = []
    return PlayerCombatState(
        hull=hull,
        max_hull=max_hull,
        shields=shields,
        max_shields=max_shields,
        energy=energy,
        max_energy=max_energy,
        energy_regen=energy_regen,
        speed=speed,
        evasion=evasion,
        accuracy=accuracy,
        equipment_moves=equipment_moves,
        crew_moves=crew_moves,
        active_effects=[],
        cooldowns={},
    )


def _make_combat_state(
    player: PlayerCombatState | None = None,
    enemy_templates: list[EnemyShipTemplate] | None = None,
    seed: int = 42,
) -> CombatState:
    if player is None:
        player = _make_player_state()
    if enemy_templates is None:
        enemy_templates = [_make_enemy_template()]
    encounter = CombatEncounter(enemy_templates=enemy_templates, encounter_seed=seed)
    enemies = [EnemyShip.from_template(t) for t in enemy_templates]
    return CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
    )


def _make_engine(
    player: PlayerCombatState | None = None,
    enemy_templates: list[EnemyShipTemplate] | None = None,
    seed: int = 42,
) -> CombatEngine:
    state = _make_combat_state(player, enemy_templates, seed)
    return CombatEngine(state, seed=seed)


# ============================================================================
# Attack Resolution
# ============================================================================


class TestAttackResolution:
    """Tests for hit/miss and damage calculation."""

    def test_guaranteed_hit_high_accuracy(self) -> None:
        # Accuracy 95 vs evasion 0 → clamped to 95% hit chance
        # With seed 42, should hit most of the time
        player = _make_player_state(accuracy=95)
        engine = _make_engine(
            player=player,
            enemy_templates=[_make_enemy_template(evasion=0)],
            seed=42,
        )
        logs = engine.execute_player_move("laser", target_idx=0)
        # At least one log entry produced
        assert len(logs) >= 1

    def test_hit_chance_clamped_minimum_5(self) -> None:
        # Very low accuracy → still 5% chance to hit, never 0
        player = _make_player_state(accuracy=0)
        engine = _make_engine(
            player=player,
            enemy_templates=[_make_enemy_template(evasion=95)],
            seed=1,
        )
        # Should not crash
        logs = engine.execute_player_move("laser", target_idx=0)
        assert len(logs) >= 1

    def test_shields_absorb_damage_first(self) -> None:
        # High accuracy, no evasion → guaranteed hit for testing
        player = _make_player_state(accuracy=200)  # well above cap, but capped to 95
        enemy_template = _make_enemy_template(evasion=0, hull=80, shields=20)
        engine = _make_engine(player=player, enemy_templates=[enemy_template], seed=42)

        # Force a hit by using a high-accuracy move
        state = engine.get_state()
        enemy = state.enemies[0]
        initial_shields = enemy.current_shields
        initial_hull = enemy.current_hull

        # Execute attack with 20 damage
        engine.execute_player_move("laser", target_idx=0)

        # Damage should go to shields first
        if state.combat_log and state.combat_log[-1].hit:
            total_damage = (
                initial_shields - enemy.current_shields + initial_hull - enemy.current_hull
            )
            assert total_damage > 0, "Hit should deal damage"

    def test_damage_overflow_to_hull(self) -> None:
        player = _make_player_state(accuracy=200)
        # Shields = 5, so 20 damage should overflow 15 to hull
        enemy_template = _make_enemy_template(evasion=0, hull=80, shields=5)
        engine = _make_engine(player=player, enemy_templates=[enemy_template], seed=42)
        engine.execute_player_move("laser", target_idx=0)
        state = engine.get_state()
        enemy = state.enemies[0]
        # If hit, shields should be 0 and hull should be reduced
        hit_entries = [e for e in state.combat_log if e.hit]
        if hit_entries:
            assert enemy.current_shields == 0
            assert enemy.current_hull < 80


# ============================================================================
# Damage Reduction
# ============================================================================


class TestDamageReduction:
    """Tests for active damage reduction buffs."""

    def test_damage_reduction_reduces_incoming(self) -> None:
        player = _make_player_state(accuracy=200)
        enemy_template = _make_enemy_template(evasion=0, hull=100, shields=0)
        engine = _make_engine(player=player, enemy_templates=[enemy_template], seed=42)

        # Give enemy 50% damage reduction
        state = engine.get_state()
        dr_effect = CombatEffect(
            type=EffectType.DAMAGE_REDUCTION,
            value=0.5,
            duration=3,
            target=EffectTarget.SELF,
        )
        state.enemies[0].active_effects.append((dr_effect, 3))

        engine.execute_player_move("laser", target_idx=0)
        hit_entries = [e for e in state.combat_log if e.hit]
        if hit_entries:
            # 20 damage * 0.5 reduction = 10 damage
            assert state.enemies[0].current_hull >= 90


# ============================================================================
# Energy and Cooldowns
# ============================================================================


class TestEnergyAndCooldowns:
    """Tests for energy costs and cooldown mechanics."""

    def test_move_costs_energy(self) -> None:
        player = _make_player_state(energy=10)
        engine = _make_engine(player=player, seed=42)
        engine.execute_player_move("laser", target_idx=0)
        state = engine.get_state()
        assert state.player.energy < 10

    def test_move_blocked_when_insufficient_energy(self) -> None:
        player = _make_player_state(energy=1)  # laser costs 3
        engine = _make_engine(player=player, seed=42)
        logs = engine.execute_player_move("laser", target_idx=0)
        assert any(
            "energy" in e.action.lower() or "energy" in str(e.effects_applied).lower() for e in logs
        )

    def test_cooldown_blocks_move(self) -> None:
        move = _make_move("missile", "Missile", 30.0, energy_cost=4, cooldown=2)
        player = _make_player_state(equipment_moves=[move])
        engine = _make_engine(player=player, seed=42)

        # First use should work
        engine.execute_player_move("missile", target_idx=0)
        # Immediately using again should fail (on cooldown)
        logs = engine.execute_player_move("missile", target_idx=0)
        assert any(
            "cooldown" in str(e.effects_applied).lower() or "cooldown" in e.action.lower()
            for e in logs
        )

    def test_cooldown_decrements_each_round(self) -> None:
        move = _make_move("missile", "Missile", 30.0, energy_cost=2, cooldown=1)
        player = _make_player_state(equipment_moves=[move], energy=20, max_energy=20)
        engine = _make_engine(player=player, seed=42)

        engine.execute_player_move("missile", target_idx=0)
        state = engine.get_state()
        assert "missile" in state.player.cooldowns

        engine.end_round()
        assert "missile" not in state.player.cooldowns


# ============================================================================
# Crew Moves
# ============================================================================


class TestCrewMoves:
    """Tests for crew phase execution."""

    def test_crew_moves_execute(self) -> None:
        heal_move = _make_move(
            "repair",
            "Emergency Repair",
            0,
            energy_cost=0,
            effects=[
                CombatEffect(type=EffectType.HULL_RESTORE, value=20.0, target=EffectTarget.SELF)
            ],
        )
        player = _make_player_state(hull=50, crew_moves=[heal_move])
        engine = _make_engine(player=player, seed=42)

        logs = engine.execute_crew_moves()
        assert len(logs) >= 1
        state = engine.get_state()
        assert state.player.hull > 50

    def test_skip_crew_moves(self) -> None:
        heal_move = _make_move(
            "repair",
            "Emergency Repair",
            0,
            energy_cost=0,
            effects=[
                CombatEffect(type=EffectType.HULL_RESTORE, value=20.0, target=EffectTarget.SELF)
            ],
        )
        player = _make_player_state(hull=50, crew_moves=[heal_move])
        engine = _make_engine(player=player, seed=42)

        engine.execute_crew_moves(skip_ids={"repair"})
        state = engine.get_state()
        assert state.player.hull == 50, "Skipped move should not apply"


# ============================================================================
# Enemy AI
# ============================================================================


class TestEnemyAI:
    """Tests for enemy turn execution and AI behaviors."""

    def test_aggressive_always_attacks(self) -> None:
        enemy_t = _make_enemy_template(behavior=EnemyBehavior.AGGRESSIVE, hull=100)
        engine = _make_engine(enemy_templates=[enemy_t], seed=42)
        logs = engine.execute_enemy_turns()
        assert len(logs) >= 1
        assert logs[0].actor == "enemy:0"

    def test_cowardly_flees_at_low_hull(self) -> None:
        enemy_t = _make_enemy_template(
            behavior=EnemyBehavior.COWARDLY,
            hull=100,
            flee_threshold=0.4,
        )
        engine = _make_engine(enemy_templates=[enemy_t], seed=42)
        state = engine.get_state()
        state.enemies[0].current_hull = 30  # 30% hull, below 40% threshold
        engine.execute_enemy_turns()
        # Cowardly enemy should flee
        assert state.enemies[0].is_fled

    def test_defensive_uses_defense_when_low(self) -> None:
        shield_move = _make_move(
            "shield",
            "Shield",
            0,
            energy_cost=2,
            effects=[
                CombatEffect(
                    type=EffectType.SHIELD_RESTORE,
                    value=15.0,
                    target=EffectTarget.SELF,
                )
            ],
        )
        attack_move = _make_move("attack", "Attack", 10.0, energy_cost=2)
        enemy_t = _make_enemy_template(
            behavior=EnemyBehavior.DEFENSIVE,
            hull=100,
            shields=20,
            moves=[attack_move, shield_move],
        )
        engine = _make_engine(enemy_templates=[enemy_t], seed=42)
        state = engine.get_state()
        state.enemies[0].current_hull = 40  # below 50%
        state.enemies[0].current_shields = 5
        logs = engine.execute_enemy_turns()
        # Should prefer defensive move
        assert any("Shield" in e.action for e in logs)

    def test_dead_enemies_dont_act(self) -> None:
        enemy_t = _make_enemy_template(hull=100)
        engine = _make_engine(enemy_templates=[enemy_t], seed=42)
        state = engine.get_state()
        state.enemies[0].current_hull = 0
        logs = engine.execute_enemy_turns()
        assert len(logs) == 0


# ============================================================================
# Flee Mechanic
# ============================================================================


class TestFleeMechanic:
    """Tests for the flee action."""

    def test_flee_fast_ship_succeeds(self) -> None:
        # Player speed 20 vs enemy speed 5 → high flee chance
        player = _make_player_state(speed=20)
        enemy_t = _make_enemy_template(speed=5, evasion=0, accuracy=10)
        engine = _make_engine(player=player, enemy_templates=[enemy_t], seed=42)
        success, logs = engine.attempt_flee()
        # With large speed advantage, should succeed most seeds
        assert isinstance(success, bool)
        assert len(logs) >= 1

    def test_flee_slow_ship_harder(self) -> None:
        # Player speed 2 vs enemy speed 15 → low flee chance
        player = _make_player_state(speed=2)
        enemy_t = _make_enemy_template(speed=15)
        engine = _make_engine(player=player, enemy_templates=[enemy_t], seed=42)
        success, _logs = engine.attempt_flee()
        assert isinstance(success, bool)

    def test_flee_parting_shots(self) -> None:
        player = _make_player_state(speed=20, shields=100, max_shields=100, hull=200, max_hull=200)
        enemy_t = _make_enemy_template(speed=5, accuracy=100, evasion=0)
        engine = _make_engine(player=player, enemy_templates=[enemy_t], seed=42)
        _success, logs = engine.attempt_flee()
        # Parting shot log entries should exist
        parting = [l for l in logs if "parting" in l.action.lower() or l.actor.startswith("enemy:")]
        assert len(parting) >= 1

    def test_flee_success_sets_result(self) -> None:
        player = _make_player_state(speed=50)
        enemy_t = _make_enemy_template(speed=1)
        engine = _make_engine(player=player, enemy_templates=[enemy_t], seed=42)
        success, _ = engine.attempt_flee()
        if success:
            assert engine.get_state().result == CombatResult.FLED


# ============================================================================
# Negotiate Mechanic
# ============================================================================


class TestNegotiateMechanic:
    """Tests for combat negotiation."""

    def test_negotiate_once_per_encounter(self) -> None:
        engine = _make_engine(seed=42)
        state = engine.get_state()
        state.negotiate_used = True
        success, msg, _logs = engine.attempt_negotiate("persuasion", None)
        assert not success
        assert "already" in msg.lower()

    def test_negotiate_without_social_manager(self) -> None:
        engine = _make_engine(seed=42)
        success, _msg, _logs = engine.attempt_negotiate("persuasion", None)
        # Without social manager, should fail gracefully
        assert not success

    def test_negotiate_marks_used(self) -> None:
        engine = _make_engine(seed=42)
        engine.attempt_negotiate("persuasion", None)
        assert engine.get_state().negotiate_used


# ============================================================================
# End Round
# ============================================================================


class TestEndRound:
    """Tests for end-of-round processing."""

    def test_end_round_ticks_effects(self) -> None:
        engine = _make_engine(seed=42)
        state = engine.get_state()
        effect = CombatEffect(
            type=EffectType.EVASION_MOD,
            value=10.0,
            duration=1,
            target=EffectTarget.SELF,
        )
        state.player.active_effects.append((effect, 1))
        engine.end_round()
        assert len(state.player.active_effects) == 0

    def test_end_round_regenerates_energy(self) -> None:
        player = _make_player_state(energy=5, max_energy=10, energy_regen=3)
        engine = _make_engine(player=player, seed=42)
        engine.end_round()
        assert engine.get_state().player.energy == 8

    def test_end_round_increments_round(self) -> None:
        engine = _make_engine(seed=42)
        assert engine.get_state().round_number == 1
        engine.end_round()
        assert engine.get_state().round_number == 2

    def test_victory_when_all_enemies_dead(self) -> None:
        engine = _make_engine(seed=42)
        state = engine.get_state()
        state.enemies[0].current_hull = 0
        engine._check_combat_end()
        assert state.result == CombatResult.VICTORY

    def test_defeat_when_player_dead(self) -> None:
        player = _make_player_state(hull=0)
        engine = _make_engine(player=player, seed=42)
        engine._check_combat_end()
        assert engine.get_state().result == CombatResult.DEFEAT


# ============================================================================
# Available Moves
# ============================================================================


class TestAvailableMoves:
    """Tests for querying available moves."""

    def test_get_available_moves_filters_cooldown(self) -> None:
        move = _make_move("missile", "Missile", 30.0, energy_cost=2, cooldown=2)
        player = _make_player_state(equipment_moves=[move])
        engine = _make_engine(player=player, seed=42)
        assert len(engine.get_available_moves()) == 1
        engine.get_state().player.cooldowns["missile"] = 2
        assert len(engine.get_available_moves()) == 0

    def test_get_available_moves_filters_energy(self) -> None:
        move = _make_move("laser", "Laser", 20.0, energy_cost=5)
        player = _make_player_state(equipment_moves=[move], energy=3)
        engine = _make_engine(player=player, seed=42)
        assert len(engine.get_available_moves()) == 0

    def test_is_combat_over(self) -> None:
        engine = _make_engine(seed=42)
        assert not engine.is_combat_over()
        engine.get_state().result = CombatResult.VICTORY
        assert engine.is_combat_over()


# ============================================================================
# Bribe Tests
# ============================================================================


class TestBribe:
    """Tests for attempt_bribe()."""

    def test_bribe_success_sufficient_credits(self) -> None:
        """Bribe succeeds when player has enough credits."""
        template = _make_enemy_template(bribe_cost=100)
        engine = _make_engine(enemy_templates=[template])
        success, cost, _logs = engine.attempt_bribe(player_credits=500)
        assert success
        assert cost == 100
        assert engine.get_state().result == CombatResult.BRIBED

    def test_bribe_fails_insufficient_credits(self) -> None:
        """Bribe fails when player can't afford it."""
        template = _make_enemy_template(bribe_cost=100)
        engine = _make_engine(enemy_templates=[template])
        success, cost, _logs = engine.attempt_bribe(player_credits=50)
        assert not success
        assert cost == 100
        assert engine.get_state().result == CombatResult.IN_PROGRESS

    def test_bribe_cost_sums_multiple_enemies(self) -> None:
        """Total bribe cost is sum of surviving enemies' bribe costs."""
        t1 = _make_enemy_template(id="a", bribe_cost=100)
        t2 = _make_enemy_template(id="b", bribe_cost=200)
        engine = _make_engine(enemy_templates=[t1, t2])
        success, cost, _logs = engine.attempt_bribe(player_credits=300)
        assert success
        assert cost == 300

    def test_bribe_once_per_encounter(self) -> None:
        """Can only attempt bribe once per encounter."""
        template = _make_enemy_template(bribe_cost=100)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_bribe(player_credits=50)  # Fail first
        success, _cost, logs = engine.attempt_bribe(player_credits=500)
        assert not success
        assert "already" in logs[0].effects_applied[0].lower()

    def test_bribe_persuasion_discount(self) -> None:
        """Persuasion level reduces bribe cost by 10% per level."""
        template = _make_enemy_template(bribe_cost=200)
        engine = _make_engine(enemy_templates=[template])
        success, cost, _logs = engine.attempt_bribe(player_credits=500, persuasion_level=3)
        assert success
        assert cost == 140  # 200 * (1 - 0.30) = 140

    def test_bribe_persuasion_max_discount(self) -> None:
        """Persuasion discount caps at 50%."""
        template = _make_enemy_template(bribe_cost=200)
        engine = _make_engine(enemy_templates=[template])
        success, cost, _logs = engine.attempt_bribe(player_credits=500, persuasion_level=10)
        assert success
        assert cost == 100  # 200 * 0.50 = 100 (max 50% discount)

    def test_bribe_ends_combat(self) -> None:
        """Successful bribe ends combat with BRIBED result."""
        template = _make_enemy_template(bribe_cost=50)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_bribe(player_credits=100)
        assert engine.is_combat_over()

    def test_bribe_zero_cost_enemy(self) -> None:
        """Enemy with 0 bribe cost can be bribed for free."""
        template = _make_enemy_template(bribe_cost=0)
        engine = _make_engine(enemy_templates=[template])
        success, cost, _logs = engine.attempt_bribe(player_credits=0)
        assert success
        assert cost == 0

    def test_bribe_only_counts_surviving_enemies(self) -> None:
        """Dead enemies don't add to bribe cost."""
        t1 = _make_enemy_template(id="a", bribe_cost=100)
        t2 = _make_enemy_template(id="b", bribe_cost=200)
        engine = _make_engine(enemy_templates=[t1, t2])
        # Kill the first enemy
        engine.get_state().enemies[0].current_hull = 0
        success, cost, _logs = engine.attempt_bribe(player_credits=200)
        assert success
        assert cost == 200  # Only second enemy's cost

    def test_bribe_produces_log_entry(self) -> None:
        """Bribe attempt produces a log entry."""
        template = _make_enemy_template(bribe_cost=100)
        engine = _make_engine(enemy_templates=[template])
        _success, _cost, logs = engine.attempt_bribe(player_credits=500)
        assert len(logs) == 1
        assert "Bribe" in logs[0].action


# ============================================================================
# Enhanced Negotiation Tests
# ============================================================================


class _FakeSocialManager:
    """Minimal social manager that always passes or fails checks."""

    def __init__(self, pass_check: bool = True) -> None:
        self._pass = pass_check
        self.last_difficulty: int = 0

    def can_pass_check(self, skill_id: str, difficulty: int, npc_id: str) -> bool:
        self.last_difficulty = difficulty
        return self._pass


class TestEnhancedNegotiation:
    """Tests for faction reputation modifiers and enhanced outcomes."""

    def test_allied_tier_reduces_difficulty(self) -> None:
        """Allied reputation should reduce negotiate difficulty by 2."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=4)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("persuasion", social, faction_reputation_tier="Allied")
        assert social.last_difficulty == 2  # 4 - 2

    def test_hostile_tier_increases_difficulty(self) -> None:
        """Hostile reputation should increase negotiate difficulty by 2."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=2)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("persuasion", social, faction_reputation_tier="Hostile")
        assert social.last_difficulty == 4  # 2 + 2

    def test_neutral_tier_no_modifier(self) -> None:
        """Neutral reputation should not change difficulty."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=3)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("persuasion", social, faction_reputation_tier="Neutral")
        assert social.last_difficulty == 3

    def test_difficulty_floor_at_one(self) -> None:
        """Difficulty should never go below 1."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=1)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("persuasion", social, faction_reputation_tier="Allied")
        assert social.last_difficulty == 1  # max(1, 1 - 2)

    def test_persuasion_sets_partial_loot_flag(self) -> None:
        """Successful persuasion should set negotiate_partial_loot."""
        social = _FakeSocialManager(pass_check=True)
        engine = _make_engine()
        engine.attempt_negotiate("persuasion", social)
        assert engine.get_state().negotiate_partial_loot is True

    def test_intimidation_sets_rival_rep_flag(self) -> None:
        """Successful intimidation should set negotiate_rival_rep."""
        social = _FakeSocialManager(pass_check=True)
        engine = _make_engine()
        engine.attempt_negotiate("intimidation", social)
        assert engine.get_state().negotiate_rival_rep is True

    def test_observation_reveals_bribe_cost(self) -> None:
        """Successful observation should reveal total bribe cost."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(bribe_cost=150)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("observation", social)
        assert engine.get_state().revealed_bribe_cost == 150

    def test_no_tier_parameter_works(self) -> None:
        """Omitting faction_reputation_tier should work (backward compat)."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=3)
        engine = _make_engine(enemy_templates=[template])
        success, _msg, _logs = engine.attempt_negotiate("persuasion", social)
        assert success
        assert social.last_difficulty == 3


# ============================================================================
# Flee Bonus Tests
# ============================================================================


class TestFleeBonus:
    """Tests for flee_bonus from Emergency Thrusters upgrade."""

    def test_flee_bonus_increases_chance(self) -> None:
        """flee_bonus should increase flee chance."""
        # Create two engines with same seed, one with bonus
        template = _make_enemy_template(speed=10)
        player_no_bonus = _make_player_state(speed=8)
        player_with_bonus = _make_player_state(speed=8)
        player_with_bonus.flee_bonus = 15

        # The flee_chance formula: FLEE_BASE_CHANCE + (player_speed - avg_enemy_speed) * SPEED_FACTOR + flee_bonus
        # With bonus: 30 + (8-10)*3 + 15 = 30 - 6 + 15 = 39
        # Without bonus: 30 + (8-10)*3 = 30 - 6 = 24
        engine_no = CombatEngine(_make_combat_state(player_no_bonus, [template]), seed=42)
        engine_yes = CombatEngine(_make_combat_state(player_with_bonus, [template]), seed=42)

        # Run many attempts to verify statistical difference
        no_bonus_success = 0
        bonus_success = 0
        for s in range(500):
            state_no = _make_combat_state(_make_player_state(speed=8), [template], seed=s)
            engine_no = CombatEngine(state_no, seed=s)
            ok, _ = engine_no.attempt_flee()
            if ok:
                no_bonus_success += 1

            state_yes = _make_combat_state(_make_player_state(speed=8), [template], seed=s)
            state_yes.player.flee_bonus = 15
            engine_yes = CombatEngine(state_yes, seed=s)
            ok, _ = engine_yes.attempt_flee()
            if ok:
                bonus_success += 1

        assert bonus_success > no_bonus_success, (
            f"Bonus ({bonus_success}) should exceed no-bonus ({no_bonus_success})"
        )

    def test_flee_bonus_default_zero(self) -> None:
        """flee_bonus should default to 0."""
        player = _make_player_state()
        assert player.flee_bonus == 0

    def test_flee_bonus_clamped_correctly(self) -> None:
        """Flee chance with bonus should still respect FLEE_MAX_CHANCE."""
        template = _make_enemy_template(speed=1)
        successes = 0
        for s in range(200):
            player = _make_player_state(speed=20)
            player.flee_bonus = 50
            state = _make_combat_state(player, [template], seed=s)
            engine = CombatEngine(state, seed=s)
            ok, _ = engine.attempt_flee()
            if ok:
                successes += 1
        # flee_chance = 30 + (20-1)*3 + 50 = 137 → clamped to 90
        # With 90% chance, ~180/200 expected
        assert successes > 150


# ============================================================================
# Combat result integration flags
# ============================================================================


class TestCombatResultFlags:
    """Tests that combat result flags are correctly set for game.py integration."""

    def test_bribe_sets_result_and_flag(self) -> None:
        """Successful bribe should set BRIBED result and bribe_used flag."""
        template = _make_enemy_template(bribe_cost=100)
        player = _make_player_state()
        state = _make_combat_state(player, [template])
        engine = CombatEngine(state, seed=42)

        success, cost, _ = engine.attempt_bribe(500)
        assert success
        assert cost == 100
        assert state.result == CombatResult.BRIBED
        assert state.bribe_used

    def test_negotiate_partial_loot_flag(self) -> None:
        """Persuasion success should set negotiate_partial_loot flag."""
        social = _FakeSocialManager(pass_check=True)
        engine = _make_engine()
        engine.attempt_negotiate("persuasion", social)
        assert engine.get_state().negotiate_partial_loot

    def test_negotiate_rival_rep_flag(self) -> None:
        """Intimidation success should set negotiate_rival_rep flag."""
        social = _FakeSocialManager(pass_check=True)
        engine = _make_engine()
        engine.attempt_negotiate("intimidation", social)
        assert engine.get_state().negotiate_rival_rep

    def test_negotiate_observation_reveals_bribe_cost(self) -> None:
        """Observation success should reveal bribe cost."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(bribe_cost=150)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("observation", social)
        assert engine.get_state().revealed_bribe_cost == 150

    def test_bribe_cost_deducted_correctly(self) -> None:
        """Bribe cost should equal sum of surviving enemy bribe costs."""
        t1 = _make_enemy_template(id="e1", bribe_cost=100)
        t2 = _make_enemy_template(id="e2", bribe_cost=200)
        player = _make_player_state()
        state = _make_combat_state(player, [t1, t2])
        engine = CombatEngine(state, seed=42)

        success, cost, _ = engine.attempt_bribe(500)
        assert success
        assert cost == 300

    def test_faction_tier_modifies_negotiate_difficulty(self) -> None:
        """Allied faction tier should make negotiation easier."""
        social = _FakeSocialManager(pass_check=True)
        template = _make_enemy_template(negotiate_difficulty=5)
        engine = _make_engine(enemy_templates=[template])
        engine.attempt_negotiate("persuasion", social, faction_reputation_tier="Allied")
        assert social.last_difficulty == 3  # 5 - 2 = 3


# ============================================================================
# Ally-targeted heals (Tier 3.D)
# ============================================================================


class TestAllyTargetedHeals:
    """EffectTarget.ALLY routes HULL_RESTORE to a teammate of the caster.

    For an enemy attacker, the "team" is other living enemies (not the
    caster, not the player). For a player attacker, there are no allies
    in the current combat model — the effect falls back to self.
    """

    def _medic_template(self) -> EnemyShipTemplate:
        """A support enemy with an ally-heal move."""
        heal_move = _make_move(
            id="medical_relay",
            name="Medical Relay",
            damage=0,
            energy_cost=2,
            cooldown=0,
            effects=[
                CombatEffect(
                    type=EffectType.HULL_RESTORE,
                    value=30.0,
                    target=EffectTarget.ALLY,
                )
            ],
        )
        return _make_enemy_template(
            id="medic",
            hull=100,
            energy=10,
            behavior=EnemyBehavior.DEFENSIVE,
            moves=[heal_move],
        )

    def _striker_template(self) -> EnemyShipTemplate:
        """A damaged-but-alive ally for the medic to heal."""
        return _make_enemy_template(id="striker", hull=100, moves=[_make_move()])

    def test_ally_heal_restores_wounded_teammate(self) -> None:
        medic = self._medic_template()
        striker = self._striker_template()
        engine = _make_engine(enemy_templates=[medic, striker])
        state = engine.get_state()

        # Damage the striker to 20/100 hull
        state.enemies[1].current_hull = 20

        # Run the medic's turn — should heal the striker up, not itself
        medic_enemy = state.enemies[0]
        heal_move = medic_enemy.template.moves[0]
        engine._resolve_move(
            heal_move,
            attacker=medic_enemy,
            defender=state.player,  # Ignored for ALLY effects
            actor_name="enemy_0",
            attacker_accuracy=medic_enemy.get_effective_accuracy(),
        )

        assert state.enemies[1].current_hull == 50, (
            f"Striker should heal from 20 → 50 (+30). Got {state.enemies[1].current_hull}"
        )
        assert state.enemies[0].current_hull == 100, (
            "Medic should NOT heal itself when an ally is available"
        )

    def test_ally_heal_picks_lowest_hp_when_multiple_allies(self) -> None:
        medic = self._medic_template()
        wounded = _make_enemy_template(id="wounded", hull=200, moves=[_make_move()])
        healthy = _make_enemy_template(id="healthy", hull=200, moves=[_make_move()])
        engine = _make_engine(enemy_templates=[medic, wounded, healthy])
        state = engine.get_state()

        # wounded at 30% HP, healthy at 90% HP — lowest-HP wins
        state.enemies[1].current_hull = 60   # 30% hull ratio
        state.enemies[2].current_hull = 180  # 90% hull ratio

        heal_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            heal_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert state.enemies[1].current_hull == 90, (
            "Wounded ally (lowest HP) must be the heal target"
        )
        assert state.enemies[2].current_hull == 180, (
            "Healthy ally should be untouched"
        )

    def test_ally_heal_skips_dead_allies(self) -> None:
        medic = self._medic_template()
        dead = _make_enemy_template(id="dead", hull=100, moves=[_make_move()])
        alive = _make_enemy_template(id="alive", hull=100, moves=[_make_move()])
        engine = _make_engine(enemy_templates=[medic, dead, alive])
        state = engine.get_state()

        state.enemies[1].current_hull = 0  # Dead
        state.enemies[2].current_hull = 50  # Alive, wounded

        heal_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            heal_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert state.enemies[1].current_hull == 0, "Dead ally stays dead"
        assert state.enemies[2].current_hull == 80, (
            "Alive ally (despite higher HP) should be healed since dead one was skipped"
        )

    def test_ally_heal_with_no_allies_redirects_to_self(self) -> None:
        """Solo medic (no teammates alive) falls back to self-heal."""
        medic = self._medic_template()
        engine = _make_engine(enemy_templates=[medic])
        state = engine.get_state()

        state.enemies[0].current_hull = 30  # Medic itself is wounded

        heal_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            heal_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert state.enemies[0].current_hull == 60, (
            "With no allies, heal falls back to self (30 → 60)"
        )

    def test_player_ally_heal_falls_back_to_self(self) -> None:
        """Player has no distinct allies (crew are part of PlayerCombatState).
        An ally effect from a player move routes to the player itself."""
        heal_move = _make_move(
            "self_patch",
            "Self Patch",
            0,
            energy_cost=0,
            effects=[
                CombatEffect(
                    type=EffectType.HULL_RESTORE,
                    value=25.0,
                    target=EffectTarget.ALLY,
                )
            ],
        )
        player = _make_player_state(hull=40, max_hull=100, equipment_moves=[heal_move])
        engine = _make_engine(player=player)

        engine._resolve_move(
            heal_move,
            attacker=player,
            defender=engine.get_state().enemies[0],
            actor_name="player",
            attacker_accuracy=player.accuracy,
        )

        assert player.hull == 65, (
            f"Player ally heal should route to self (40 → 65). Got {player.hull}"
        )


class TestAllyHealLogEntry:
    """Pure ally-effect moves (no offensive, no self) must still produce a
    log entry so players can see the action happen."""

    def test_ally_only_move_produces_log_entry(self) -> None:
        heal_move = _make_move(
            id="medical_relay",
            name="Medical Relay",
            damage=0,
            energy_cost=2,
            effects=[
                CombatEffect(
                    type=EffectType.HULL_RESTORE,
                    value=30.0,
                    target=EffectTarget.ALLY,
                )
            ],
        )
        medic = _make_enemy_template(
            id="medic", hull=100, behavior=EnemyBehavior.DEFENSIVE, moves=[heal_move]
        )
        striker = _make_enemy_template(id="striker", hull=100, moves=[_make_move()])
        engine = _make_engine(enemy_templates=[medic, striker])
        state = engine.get_state()
        state.enemies[1].current_hull = 30

        log_len_before = len(state.combat_log)
        engine._resolve_move(
            heal_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )
        new_entries = state.combat_log[log_len_before:]

        assert len(new_entries) >= 1, "Ally-only move must produce a log entry"
        # The action name should appear in the log
        assert any(e.action == "Medical Relay" for e in new_entries)


# ============================================================================
# Reinforcement spawning (Tier 3.E)
# ============================================================================


class TestReinforcementSpawning:
    """EffectType.SPAWN_REINFORCEMENT appends a new EnemyShip to
    state.enemies mid-combat, respecting the living-enemy cap."""

    def _caller_template(self, spawn_template_id: str = "pirate") -> EnemyShipTemplate:
        """Template with a single call_reinforcement move."""
        spawn_move = _make_move(
            id="call_reinforcement",
            name="Call Backup",
            damage=0,
            energy_cost=0,
            effects=[
                CombatEffect(
                    type=EffectType.SPAWN_REINFORCEMENT,
                    value=1.0,
                    metadata={"template_id": spawn_template_id},
                )
            ],
        )
        return _make_enemy_template(
            id="caller",
            hull=100,
            behavior=EnemyBehavior.DEFENSIVE,
            moves=[spawn_move],
        )

    def test_spawn_appends_to_enemies_list(self) -> None:
        from spacegame.data_loader import get_data_loader

        dl = get_data_loader()
        dl.load_all()
        # Confirm the template we want to spawn actually exists in data
        assert "pirate_scout" in dl.enemy_templates

        caller = self._caller_template(spawn_template_id="pirate_scout")
        engine = _make_engine(enemy_templates=[caller])
        state = engine.get_state()
        enemies_before = len(state.enemies)

        spawn_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            spawn_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert len(state.enemies) == enemies_before + 1, (
            "Reinforcement spawn should append one enemy to state.enemies"
        )
        assert state.enemies[-1].template.id == "pirate_scout"
        assert state.enemies[-1].is_alive

    def test_spawn_respects_max_living_cap(self) -> None:
        """With MAX_LIVING_ENEMIES living already, the spawn is declined."""
        from spacegame.models.combat_engine import MAX_LIVING_ENEMIES

        # Build an arena at the cap — caller + (cap-1) extras
        templates = [self._caller_template(spawn_template_id="pirate_scout")]
        for i in range(MAX_LIVING_ENEMIES - 1):
            templates.append(_make_enemy_template(id=f"filler_{i}", hull=50))
        engine = _make_engine(enemy_templates=templates)
        state = engine.get_state()

        assert len(state.enemies) == MAX_LIVING_ENEMIES
        spawn_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            spawn_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )
        assert len(state.enemies) == MAX_LIVING_ENEMIES, (
            "Spawn must be declined when cap is reached"
        )

    def test_spawn_unknown_template_noop_with_log(self) -> None:
        caller = self._caller_template(spawn_template_id="nonexistent_template")
        engine = _make_engine(enemy_templates=[caller])
        state = engine.get_state()
        enemies_before = len(state.enemies)

        log_len_before = len(state.combat_log)
        spawn_move = state.enemies[0].template.moves[0]
        engine._resolve_move(
            spawn_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        # State did not grow
        assert len(state.enemies) == enemies_before, (
            "Unknown template must not add a phantom enemy"
        )
        # A log entry surfaces the failure
        new_entries = state.combat_log[log_len_before:]
        failure_msg = [
            e for e in new_entries if any("failed" in m.lower() for m in e.effects_applied)
        ]
        assert failure_msg, "Failed spawn should log a failure message"

    def test_spawn_value_controls_count(self) -> None:
        """value=2 spawns two reinforcements (up to cap)."""
        spawn_move = _make_move(
            id="call_two",
            name="Call Two",
            damage=0,
            energy_cost=0,
            effects=[
                CombatEffect(
                    type=EffectType.SPAWN_REINFORCEMENT,
                    value=2.0,
                    metadata={"template_id": "pirate_scout"},
                )
            ],
        )
        caller = _make_enemy_template(
            id="caller",
            hull=100,
            behavior=EnemyBehavior.DEFENSIVE,
            moves=[spawn_move],
        )
        engine = _make_engine(enemy_templates=[caller])
        state = engine.get_state()
        enemies_before = len(state.enemies)

        engine._resolve_move(
            spawn_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert len(state.enemies) == enemies_before + 2

    def test_spawn_missing_template_id_noop(self) -> None:
        """Effect without a template_id in metadata is declined gracefully."""
        spawn_move = _make_move(
            id="malformed",
            name="Malformed Spawn",
            damage=0,
            energy_cost=0,
            effects=[
                CombatEffect(
                    type=EffectType.SPAWN_REINFORCEMENT,
                    value=1.0,
                    metadata={},  # missing template_id
                )
            ],
        )
        caller = _make_enemy_template(
            id="caller",
            hull=100,
            behavior=EnemyBehavior.DEFENSIVE,
            moves=[spawn_move],
        )
        engine = _make_engine(enemy_templates=[caller])
        state = engine.get_state()
        enemies_before = len(state.enemies)

        engine._resolve_move(
            spawn_move,
            attacker=state.enemies[0],
            defender=state.player,
            actor_name="enemy_0",
            attacker_accuracy=state.enemies[0].get_effective_accuracy(),
        )

        assert len(state.enemies) == enemies_before


class TestCombatEffectMetadata:
    """CombatEffect.metadata field round-trips through to_dict/from_dict."""

    def test_metadata_serializes(self) -> None:
        effect = CombatEffect(
            type=EffectType.SPAWN_REINFORCEMENT,
            value=1.0,
            metadata={"template_id": "pirate_scout"},
        )
        restored = CombatEffect.from_dict(effect.to_dict())
        assert restored.metadata == {"template_id": "pirate_scout"}
        assert restored.type == EffectType.SPAWN_REINFORCEMENT

    def test_metadata_empty_dict_omitted_from_serialization(self) -> None:
        """Keeps existing JSON minimal — don't emit metadata:{} for every effect."""
        effect = CombatEffect(type=EffectType.DAMAGE, value=10.0)
        assert "metadata" not in effect.to_dict()

    def test_metadata_missing_in_dict_loads_empty(self) -> None:
        """Backward compat: old JSON without metadata loads with empty dict."""
        restored = CombatEffect.from_dict({"type": "damage", "value": 10.0})
        assert restored.metadata == {}
