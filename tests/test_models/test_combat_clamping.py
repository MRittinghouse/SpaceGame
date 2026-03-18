"""Tests for combat hull/shield clamping after damage."""

from spacegame.models.combat import (
    PlayerCombatState,
    EnemyShip,
    EnemyShipTemplate,
    EnemyBehavior,
    CombatEffect,
    CombatEncounter,
    CombatState,
    CombatLogEntry,
    EffectType,
)
from spacegame.models.combat_engine import CombatEngine


def _make_player(hull: int = 100, shields: int = 50, energy: int = 30) -> PlayerCombatState:
    return PlayerCombatState(
        hull=hull,
        max_hull=hull,
        shields=shields,
        max_shields=shields,
        energy=energy,
        max_energy=energy,
        energy_regen=5,
        speed=5,
        evasion=0,
        accuracy=100,
        equipment_moves=[],
        crew_moves=[],
        active_effects=[],
        cooldowns={},
    )


def _make_enemy_template(hull: int = 80, shields: int = 30) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id="test_enemy",
        name="Test Enemy",
        description="",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull,
        shields=shields,
        energy=20,
        energy_regen=0,
        speed=5,
        evasion=0,
        accuracy=100,
        moves=[],
        loot_table=[],
    )


def _make_engine(
    player: PlayerCombatState,
    enemy_template: EnemyShipTemplate | None = None,
) -> tuple[CombatEngine, EnemyShip]:
    """Create a CombatEngine with a single enemy."""
    if enemy_template is None:
        enemy_template = _make_enemy_template()
    encounter = CombatEncounter(
        enemy_templates=[enemy_template],
        encounter_seed=42,
    )
    enemy = EnemyShip.from_template(enemy_template)
    state = CombatState(
        player=player,
        enemies=[enemy],
        encounter=encounter,
        combat_log=[],
    )
    return CombatEngine(state), enemy


class TestHullNeverGoesNegative:
    """Hull must be clamped to 0 after damage, never negative."""

    def test_player_hull_clamped_to_zero(self) -> None:
        """Massive damage should leave hull at 0, not negative."""
        player = _make_player(hull=50, shields=0)
        engine, _ = _make_engine(player)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=999)]
        engine._apply_effects(effects, player, "test")
        assert player.hull >= 0, f"Player hull went negative: {player.hull}"
        assert player.hull == 0

    def test_enemy_hull_clamped_to_zero(self) -> None:
        """Massive damage should leave enemy hull at 0, not negative."""
        player = _make_player()
        tmpl = _make_enemy_template(hull=50, shields=0)
        engine, enemy = _make_engine(player, tmpl)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=999)]
        engine._apply_effects(effects, enemy, "test")
        assert enemy.current_hull >= 0, f"Enemy hull went negative: {enemy.current_hull}"
        assert enemy.current_hull == 0

    def test_player_hull_exact_kill(self) -> None:
        """Damage exactly equal to hull should leave 0."""
        player = _make_player(hull=50, shields=0)
        engine, _ = _make_engine(player)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=50)]
        engine._apply_effects(effects, player, "test")
        assert player.hull == 0

    def test_damage_overflow_from_shields(self) -> None:
        """Damage that breaks through shields shouldn't leave hull negative."""
        player = _make_player(hull=20, shields=10)
        engine, _ = _make_engine(player)
        # 100 damage: 10 absorbed by shields, 90 to hull (hull is only 20)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=100)]
        engine._apply_effects(effects, player, "test")
        assert player.hull >= 0, f"Hull went negative after shield overflow: {player.hull}"
        assert player.shields >= 0


class TestShieldsNeverGoNegative:
    """Shields must be clamped to 0 after damage/drain."""

    def test_player_shields_after_damage(self) -> None:
        player = _make_player(hull=100, shields=10)
        engine, _ = _make_engine(player)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=50)]
        engine._apply_effects(effects, player, "test")
        assert player.shields >= 0

    def test_enemy_shields_after_damage(self) -> None:
        player = _make_player()
        tmpl = _make_enemy_template(hull=100, shields=10)
        engine, enemy = _make_engine(player, tmpl)
        effects = [CombatEffect(type=EffectType.DAMAGE, value=50)]
        engine._apply_effects(effects, enemy, "test")
        assert enemy.current_shields >= 0

    def test_shield_drain_clamped(self) -> None:
        player = _make_player(hull=100, shields=15)
        engine, _ = _make_engine(player)
        effects = [CombatEffect(type=EffectType.SHIELD_DRAIN, value=999)]
        engine._apply_effects(effects, player, "test")
        assert player.shields >= 0

    def test_enemy_shield_drain_clamped(self) -> None:
        player = _make_player()
        tmpl = _make_enemy_template(hull=100, shields=15)
        engine, enemy = _make_engine(player, tmpl)
        effects = [CombatEffect(type=EffectType.SHIELD_DRAIN, value=999)]
        engine._apply_effects(effects, enemy, "test")
        assert enemy.current_shields >= 0


class TestEnergyNeverGoesNegative:
    """Energy drain should be clamped to 0."""

    def test_player_energy_clamped(self) -> None:
        player = _make_player(hull=100, shields=50, energy=10)
        engine, _ = _make_engine(player)
        effects = [CombatEffect(type=EffectType.ENERGY_DRAIN, value=999)]
        engine._apply_effects(effects, player, "test")
        assert player.energy >= 0

    def test_enemy_energy_clamped(self) -> None:
        player = _make_player()
        engine, enemy = _make_engine(player)
        effects = [CombatEffect(type=EffectType.ENERGY_DRAIN, value=999)]
        engine._apply_effects(effects, enemy, "test")
        assert enemy.current_energy >= 0
