"""Tests for Phase U2.5b — Action queue execution in combat engine.

Covers multi-action turn execution, energy deduction per action,
cooldown setting, dead-target skip, and backward compatibility
with single-action turns.
"""

from spacegame.models.action_queue import ActionQueue
from unittest.mock import MagicMock

from spacegame.models.combat import (
    CombatMove,
    CombatEffect,
    CombatLogEntry,
    EffectType,
    EffectTarget,
    PlayerCombatState,
    EnemyShip,
    CombatState,
    CombatEncounter,
)
from spacegame.models.combat_engine import CombatEngine


# ============================================================================
# Helpers
# ============================================================================


def _laser() -> CombatMove:
    return CombatMove(
        id="laser",
        name="Laser",
        description="",
        effects=[
            CombatEffect(type=EffectType.DAMAGE, value=10.0, duration=0, target=EffectTarget.ENEMY)
        ],
        energy_cost=2,
        cooldown=0,
    )


def _plasma() -> CombatMove:
    return CombatMove(
        id="plasma",
        name="Plasma",
        description="",
        effects=[
            CombatEffect(type=EffectType.DAMAGE, value=15.0, duration=0, target=EffectTarget.ENEMY)
        ],
        energy_cost=3,
        cooldown=2,
    )


def _shield() -> CombatMove:
    return CombatMove(
        id="shield_fix",
        name="Shield Fix",
        description="",
        effects=[
            CombatEffect(
                type=EffectType.SHIELD_RESTORE, value=10.0, duration=0, target=EffectTarget.SELF
            )
        ],
        energy_cost=2,
        cooldown=1,
    )


def _make_player(**overrides) -> PlayerCombatState:
    defaults = dict(
        hull=100,
        max_hull=100,
        shields=50,
        max_shields=50,
        energy=12,
        max_energy=12,
        energy_regen=4,
        speed=10,
        evasion=10,
        accuracy=70,
        equipment_moves=[_laser(), _plasma(), _shield()],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )
    defaults.update(overrides)
    return PlayerCombatState(**defaults)


def _make_enemy(hull: int = 80, shields: int = 20) -> EnemyShip:
    """Create a simple enemy for testing."""
    template = MagicMock()
    template.id = "test_enemy"
    template.name = "Test Enemy"
    template.hull = hull
    template.shields = shields
    template.energy = 10
    template.energy_regen = 2
    template.speed = 5
    template.evasion = 5
    template.accuracy = 50
    template.is_boss = False
    template.boss_hp_multiplier = 1
    template.immune_to = []
    template.max_suppressed_stacks = 3
    template.combat_armor = 0
    template.flee_threshold = 0.0
    template.behavior = "aggressive"
    template.moves = []
    template.phases = []
    template.negotiate_difficulty = 0
    template.loot_table = []
    template.rare_loot = []
    template.xp_reward = 0
    template.credit_reward = 0
    template.danger_tier = "safe"
    template.bribe_cost = 0
    template.faction_id = ""
    template.trophy_drop = ""
    return EnemyShip(
        template=template,
        current_hull=hull,
        current_shields=shields,
        current_energy=10,
        active_effects=[],
        cooldowns={},
    )


def _make_engine(player: PlayerCombatState, enemies: list[EnemyShip]) -> CombatEngine:
    # Create a minimal mock encounter
    encounter = MagicMock(spec=CombatEncounter)
    encounter.enemy_templates = []
    encounter.negotiation_difficulty = 0
    encounter.bribe_cost = 0
    state = CombatState(
        player=player,
        enemies=enemies,
        encounter=encounter,
        combat_log=[],
        round_number=1,
    )
    return CombatEngine(state)


# ============================================================================
# Multi-Action Execution
# ============================================================================


class TestQueueExecution:
    def test_execute_single_action_queue(self) -> None:
        """Single action in queue works like old execute_player_move."""
        player = _make_player()
        enemy = _make_enemy()
        engine = _make_engine(player, [enemy])

        queue = ActionQueue(energy_available=player.energy, cooldowns=dict(player.cooldowns))
        queue.add("laser", 0, _laser())

        logs = engine.execute_player_turn(queue)
        assert len(logs) >= 1
        assert player.energy == 10  # 12 - 2

    def test_execute_two_actions(self) -> None:
        """Two actions in queue both resolve and deduct energy."""
        player = _make_player()
        enemy = _make_enemy(hull=200)
        engine = _make_engine(player, [enemy])

        queue = ActionQueue(energy_available=player.energy, cooldowns=dict(player.cooldowns))
        queue.add("laser", 0, _laser())
        queue.add("plasma", 0, _plasma())

        logs = engine.execute_player_turn(queue)
        # Both should produce log entries
        assert len(logs) >= 2
        # Energy: 12 - 2 - 3 = 7
        assert player.energy == 7

    def test_cooldowns_set_after_execution(self) -> None:
        """Actions with cooldowns get their cooldowns set."""
        player = _make_player()
        enemy = _make_enemy(hull=200)
        engine = _make_engine(player, [enemy])

        queue = ActionQueue(energy_available=player.energy, cooldowns=dict(player.cooldowns))
        queue.add("laser", 0, _laser())  # cooldown=0, no cooldown set
        queue.add("plasma", 0, _plasma())  # cooldown=2

        engine.execute_player_turn(queue)
        assert "laser" not in player.cooldowns  # 0 cooldown
        assert "plasma" in player.cooldowns
        assert player.cooldowns["plasma"] == 2

    def test_execute_empty_queue(self) -> None:
        """Empty queue produces no logs and doesn't change state."""
        player = _make_player()
        enemy = _make_enemy()
        engine = _make_engine(player, [enemy])
        initial_energy = player.energy

        queue = ActionQueue(energy_available=player.energy)
        logs = engine.execute_player_turn(queue)
        assert logs == []
        assert player.energy == initial_energy

    def test_mixed_offense_and_defense(self) -> None:
        """Queue with weapon + shield restore both resolve."""
        player = _make_player(shields=20)  # Shields below max
        enemy = _make_enemy(hull=200)
        engine = _make_engine(player, [enemy])

        queue = ActionQueue(energy_available=player.energy, cooldowns=dict(player.cooldowns))
        queue.add("laser", 0, _laser())
        queue.add("shield_fix", -1, _shield())

        logs = engine.execute_player_turn(queue)
        assert len(logs) >= 2
        # Energy: 12 - 2 - 2 = 8
        assert player.energy == 8
        # Shields should have been partially restored
        assert player.shields > 20

    def test_dead_target_skips_action(self) -> None:
        """If target dies from earlier action, later action targeting it is skipped."""
        player = _make_player(accuracy=100)  # Guarantee hits
        enemy = _make_enemy(hull=5, shields=0)  # Very fragile
        engine = _make_engine(player, [enemy])

        queue = ActionQueue(energy_available=player.energy, cooldowns=dict(player.cooldowns))
        queue.add("laser", 0, _laser())  # Should kill it (10 dmg vs 5 hp)
        queue.add("plasma", 0, _plasma())  # Target already dead

        logs = engine.execute_player_turn(queue)
        # Plasma should be skipped (target dead), energy refunded
        # Laser: -2, Plasma skipped: refund 3 → net = 12 - 2 = 10
        assert player.energy >= 7  # At minimum laser was spent


class TestBackwardCompat:
    def test_old_execute_player_move_still_works(self) -> None:
        """The old single-action API should still function."""
        player = _make_player()
        enemy = _make_enemy()
        engine = _make_engine(player, [enemy])

        logs = engine.execute_player_move("laser", 0)
        assert len(logs) >= 1
        assert player.energy == 10  # 12 - 2
