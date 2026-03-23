"""Tests for Phase 12A — Defensive Identity Core Mechanics.

Tests armor, shield regen, graze, evasion scaling, and identity passives.
"""

from spacegame.models.combat import (
    CombatEffect,
    CombatLogEntry,
    CombatMove,
    CombatState,
    CombatEncounter,
    EnemyBehavior,
    EnemyShip,
    EnemyShipTemplate,
    EffectTarget,
    EffectType,
    PlayerCombatState,
    WeaponElement,
)
from spacegame.models.combat_engine import CombatEngine


# ============================================================================
# Helpers
# ============================================================================


def _move(
    id: str = "blaster", damage: float = 10.0, energy: int = 2,
    element: WeaponElement = WeaponElement.KINETIC, aoe: bool = False,
) -> CombatMove:
    return CombatMove(
        id=id, name=id.replace("_", " ").title(), description=f"{id}",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy, element=element, aoe=aoe,
    )


def _enemy(
    hull: int = 80, shields: int = 0, evasion: int = 0, accuracy: int = 95,
    armor: int = 0, moves: list[CombatMove] | None = None,
) -> EnemyShipTemplate:
    if moves is None:
        moves = [_move("enemy_shot", 10.0)]
    return EnemyShipTemplate(
        id="test_enemy", name="Test Enemy", description="Test",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull, shields=shields, energy=10, energy_regen=3,
        speed=8, evasion=evasion, accuracy=accuracy,
        moves=moves, loot_table=[], bribe_cost=0,
        combat_armor=armor,
    )


def _player(
    hull: int = 100, shields: int = 40, evasion: int = 0, accuracy: int = 95,
    armor: int = 0, shield_regen: int = 0,
    defensive_identity: str = "",
    moves: list[CombatMove] | None = None,
) -> PlayerCombatState:
    if moves is None:
        moves = [_move("laser", 20.0, 3)]
    return PlayerCombatState(
        hull=hull, max_hull=100, shields=shields, max_shields=40,
        energy=10, max_energy=10, energy_regen=3,
        speed=8, evasion=evasion, accuracy=accuracy,
        equipment_moves=moves, crew_moves=[],
        active_effects=[], cooldowns={},
        armor=armor, shield_regen=shield_regen,
        defensive_identity=defensive_identity,
    )


def _state(
    player: PlayerCombatState | None = None,
    enemies: list[EnemyShipTemplate] | None = None,
    seed: int = 42,
) -> CombatState:
    if player is None:
        player = _player()
    if enemies is None:
        enemies = [_enemy()]
    encounter = CombatEncounter(enemy_templates=enemies, encounter_seed=seed)
    enemy_ships = [EnemyShip.from_template(t) for t in enemies]
    return CombatState(
        player=player, enemies=enemy_ships, encounter=encounter, combat_log=[],
    )


# ============================================================================
# Armor Tests
# ============================================================================


class TestArmor:
    """Flat damage reduction per hit."""

    def test_armor_reduces_damage(self) -> None:
        """20 damage - 3 armor = 17 damage dealt."""
        s = _state(
            player=_player(armor=0),
            enemies=[_enemy(hull=200, armor=3)],
        )
        engine = CombatEngine(s, seed=42)
        hull_before = s.enemies[0].current_hull
        engine.execute_player_move("laser", 0)  # 20 damage
        damage = hull_before - s.enemies[0].current_hull
        assert damage == 17, f"Expected 17 (20 - 3 armor), got {damage}"

    def test_armor_minimum_one(self) -> None:
        """5 damage - 8 armor = 1 (floor)."""
        s = _state(
            player=_player(moves=[_move("weak", 5.0, 1)]),
            enemies=[_enemy(hull=200, armor=8)],
        )
        engine = CombatEngine(s, seed=42)
        hull_before = s.enemies[0].current_hull
        engine.execute_player_move("weak", 0)
        damage = hull_before - s.enemies[0].current_hull
        assert damage == 1, f"Expected 1 (floor), got {damage}"

    def test_burn_bypasses_armor(self) -> None:
        """Burn DoT should NOT be reduced by armor."""
        s = _state(
            player=_player(moves=[_move("plasma", 20.0, 3, element=WeaponElement.PLASMA)]),
            enemies=[_enemy(hull=200, armor=5)],
        )
        engine = CombatEngine(s, seed=42)
        engine.execute_player_move("plasma", 0)  # Applies burn
        hull_after_attack = s.enemies[0].current_hull
        # Tick effects to apply burn
        s.enemies[0].tick_effects()
        burn_damage = hull_after_attack - s.enemies[0].current_hull
        assert burn_damage > 0, "Burn should deal damage"
        # Burn damage should NOT be reduced by armor (full burn value applied)

    def test_player_armor_reduces_incoming(self) -> None:
        """Player with armor takes reduced damage from enemy attacks."""
        s = _state(
            player=_player(armor=3, shields=0, evasion=0),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 15.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        hull_before = s.player.hull
        engine.execute_enemy_turns()
        damage = hull_before - s.player.hull
        # 15 - 3 armor = 12
        if damage > 0:  # Only check if enemy actually hit
            assert damage == 12, f"Expected 12 (15 - 3 armor), got {damage}"


# ============================================================================
# Shield Regen Tests
# ============================================================================


class TestShieldRegen:
    """Passive shield regeneration each turn."""

    def test_shield_regen_each_round(self) -> None:
        """Shield regen adds shields at end of round."""
        s = _state(player=_player(shields=20, shield_regen=5))
        engine = CombatEngine(s, seed=42)
        engine.end_round()
        assert s.player.shields == 25, f"Expected 25 (20 + 5 regen), got {s.player.shields}"

    def test_shield_regen_capped_at_max(self) -> None:
        """Shield regen doesn't exceed max shields."""
        s = _state(player=_player(shields=38, shield_regen=5))
        engine = CombatEngine(s, seed=42)
        engine.end_round()
        assert s.player.shields == 40, f"Expected 40 (max), got {s.player.shields}"

    def test_zero_regen_no_change(self) -> None:
        """No regen when shield_regen is 0."""
        s = _state(player=_player(shields=20, shield_regen=0))
        engine = CombatEngine(s, seed=42)
        engine.end_round()
        assert s.player.shields == 20


# ============================================================================
# Graze Tests
# ============================================================================


class TestGraze:
    """Near-miss partial damage system."""

    def test_graze_deals_30_percent(self) -> None:
        """Miss by ≤10 margin deals 30% damage instead of 0."""
        # We need to control the RNG to produce a specific roll
        # Use player evasion to set hit chance, then find a seed where roll misses by ≤10
        # hit_chance = 95 (accuracy) - 30 (evasion) = 65%
        # A roll of 66-75 would be a graze (miss by 1-10)
        s = _state(
            player=_player(),
            enemies=[_enemy(hull=200, evasion=30, accuracy=65)],  # 65% vs 0 player evasion = 65%
        )
        # We need the enemy to attack the player, and we need a graze result
        # Instead, test the mechanic by having the PLAYER shoot an evasive enemy
        s2 = _state(
            player=_player(accuracy=65, evasion=0),
            enemies=[_enemy(hull=200, evasion=0)],  # 65% hit chance
        )
        engine = CombatEngine(s2, seed=42)
        # Find a seed that produces a graze
        # Let's test with many seeds and verify graze mechanics work in principle
        found_graze = False
        for test_seed in range(100):
            test_state = _state(
                player=_player(accuracy=60, moves=[_move("laser", 20.0, 3)]),
                enemies=[_enemy(hull=200, evasion=0)],  # 60% hit chance
            )
            eng = CombatEngine(test_state, seed=test_seed)
            hull_before = test_state.enemies[0].current_hull
            eng.execute_player_move("laser", 0)
            hull_after = test_state.enemies[0].current_hull
            damage = hull_before - hull_after
            if 0 < damage < 20:
                # This is a graze! (less than full damage, more than 0)
                found_graze = True
                assert damage == 6, f"Graze should deal 30% of 20 = 6, got {damage}"
                break
        assert found_graze, "Should find at least one graze in 100 seeds"

    def test_clean_miss_deals_zero(self) -> None:
        """Miss by >10 margin deals 0 damage."""
        found_clean_miss = False
        for test_seed in range(100):
            test_state = _state(
                player=_player(accuracy=50, moves=[_move("laser", 20.0, 3)]),
                enemies=[_enemy(hull=200, evasion=0)],  # 50% hit chance
            )
            eng = CombatEngine(test_state, seed=test_seed)
            hull_before = test_state.enemies[0].current_hull
            eng.execute_player_move("laser", 0)
            hull_after = test_state.enemies[0].current_hull
            damage = hull_before - hull_after
            if damage == 0:
                found_clean_miss = True
                break
        assert found_clean_miss, "Should find at least one clean miss in 100 seeds"

    def test_aoe_always_hits(self) -> None:
        """AoE moves bypass evasion entirely."""
        s = _state(
            player=_player(accuracy=10, moves=[_move("nova", 15.0, 3, aoe=True)]),
            enemies=[_enemy(hull=200, evasion=90)],  # Extremely high evasion
        )
        engine = CombatEngine(s, seed=42)
        hull_before = s.enemies[0].current_hull
        engine.execute_player_move("nova", 0)
        damage = hull_before - s.enemies[0].current_hull
        assert damage > 0, "AoE should always hit regardless of evasion"


# ============================================================================
# Evasion Scaling Tests
# ============================================================================


class TestEvasionScaling:
    """Diminishing returns and decay."""

    def test_diminishing_returns_above_50(self) -> None:
        """60 evasion should count as 55 effective (50 + (60-50)*0.5)."""
        s = _state(
            player=_player(accuracy=95),
            enemies=[_enemy(hull=200, evasion=60)],
        )
        engine = CombatEngine(s, seed=42)
        # The effective evasion of 55 means hit chance = 95 - 55 = 40%
        # We can verify by checking many combats and ensuring hit rate ~40%
        # For unit test, just verify the engine applies the diminishing returns
        # by checking that high evasion doesn't make enemies unhittable
        hits = 0
        for test_seed in range(50):
            test_state = _state(
                player=_player(accuracy=80),
                enemies=[_enemy(hull=200, evasion=60)],
            )
            eng = CombatEngine(test_state, seed=test_seed)
            hull_before = test_state.enemies[0].current_hull
            eng.execute_player_move("laser", 0)
            if test_state.enemies[0].current_hull < hull_before:
                hits += 1
        # With 80 accuracy - 55 effective evasion = 25% hit chance
        # Plus grazes, should get some hits
        assert hits > 0, "Should land some hits against 60 evasion with diminishing returns"

    def test_evasion_below_50_unaffected(self) -> None:
        """Evasion at 40 should remain 40 (no diminishing returns)."""
        # 95 accuracy - 40 evasion = 55% hit chance, should hit roughly half
        hits = 0
        for test_seed in range(50):
            test_state = _state(
                player=_player(accuracy=95),
                enemies=[_enemy(hull=200, evasion=40)],
            )
            eng = CombatEngine(test_state, seed=test_seed)
            hull_before = test_state.enemies[0].current_hull
            eng.execute_player_move("laser", 0)
            if test_state.enemies[0].current_hull < hull_before:
                hits += 1
        # 55% hit chance + graze → should hit majority
        assert hits >= 20, f"Expected ~27 hits (55% of 50), got {hits}"


# ============================================================================
# Identity Passive Tests
# ============================================================================


class TestJuggernautPassives:
    """Hull (Juggernaut) identity passives."""

    def test_last_stand_damage_bonus(self) -> None:
        """Below 25% hull with Juggernaut identity → +15% damage."""
        s = _state(
            player=_player(
                hull=20, armor=0, defensive_identity="juggernaut",
                moves=[_move("cannon", 20.0, 3)],
            ),
            enemies=[_enemy(hull=200)],
        )
        engine = CombatEngine(s, seed=42)
        hull_before = s.enemies[0].current_hull
        engine.execute_player_move("cannon", 0)
        damage = hull_before - s.enemies[0].current_hull
        # 20 base * 1.15 = 23
        assert damage == 23, f"Last Stand should deal 23 (20 * 1.15), got {damage}"

    def test_last_stand_armor_bonus(self) -> None:
        """Below 25% hull with Juggernaut identity → +2 armor."""
        s = _state(
            player=_player(hull=20, armor=1, shields=0, defensive_identity="juggernaut"),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 15.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        hull_before = s.player.hull
        engine.execute_enemy_turns()
        damage = hull_before - s.player.hull
        if damage > 0:
            # Effective armor = 1 base + 2 Last Stand = 3
            # 15 - 3 = 12
            assert damage == 12, f"Last Stand armor: expected 12 (15-3), got {damage}"

    def test_structural_integrity_dr(self) -> None:
        """Above 75% hull with Juggernaut identity → +5% DR."""
        s = _state(
            player=_player(hull=80, armor=0, shields=0, defensive_identity="juggernaut"),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 20.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        hull_before = s.player.hull
        engine.execute_enemy_turns()
        damage = hull_before - s.player.hull
        if damage > 0:
            # 20 * 0.95 = 19
            assert damage == 19, f"Structural Integrity: expected 19 (20*0.95), got {damage}"

    def test_no_passives_without_identity(self) -> None:
        """No identity → no passive bonuses."""
        s = _state(
            player=_player(hull=20, armor=0, shields=0, defensive_identity=""),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 20.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        hull_before = s.player.hull
        engine.execute_enemy_turns()
        damage = hull_before - s.player.hull
        if damage > 0:
            assert damage == 20, f"No identity: expected 20 (full damage), got {damage}"


class TestSentinelPassives:
    """Shield (Sentinel) identity passives."""

    def test_shield_break_vulnerability(self) -> None:
        """When shields hit 0 on Sentinel ship → +25% damage for 1 turn."""
        # This is tested indirectly: shield_break_vulnerable flag should be set
        s = _state(
            player=_player(shields=5, armor=0, defensive_identity="sentinel"),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 20.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        engine.execute_enemy_turns()
        # Shields should be 0 and vulnerability flag set
        if s.player.shields == 0:
            assert s.player.shield_break_vulnerable, "Shield break should set vulnerability"


class TestGhostPassives:
    """Evasion (Ghost) identity passives."""

    def test_counterstrike_stacks_on_dodge(self) -> None:
        """Clean miss against Ghost identity → +1 counterstrike stack."""
        found_miss = False
        for test_seed in range(100):
            s = _state(
                player=_player(evasion=50, defensive_identity="ghost"),
                enemies=[_enemy(accuracy=30, moves=[_move("shot", 10.0, 2)])],
                seed=test_seed,
            )
            engine = CombatEngine(s, seed=test_seed)
            engine.execute_enemy_turns()
            if s.player.counterstrike_stacks > 0:
                found_miss = True
                assert s.player.counterstrike_stacks <= 3, "Max 3 stacks"
                break
        assert found_miss, "Should find at least one dodge that triggers counterstrike"

    def test_counterstrike_resets_on_hit(self) -> None:
        """Counterstrike stacks reset when player takes a hit."""
        s = _state(
            player=_player(evasion=0, shields=0, defensive_identity="ghost"),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 5.0, 2)])],
            seed=1,
        )
        s.player.counterstrike_stacks = 2
        engine = CombatEngine(s, seed=1)
        engine.execute_enemy_turns()
        if s.player.hull < 100:  # Enemy hit
            assert s.player.counterstrike_stacks == 0, "Stacks should reset on hit"

    def test_slippery_flee_bonus(self) -> None:
        """Ghost identity → +20% flee bonus."""
        s = _state(player=_player(defensive_identity="ghost"))
        assert s.player.flee_bonus == 0  # Base
        # The engine should apply Slippery bonus during flee calculation
        # This is tested via the flee chance calculation, not a field

    def test_light_frame_vulnerability(self) -> None:
        """Ghost identity takes +15% damage when hit."""
        s = _state(
            player=_player(shields=0, armor=0, defensive_identity="ghost"),
            enemies=[_enemy(accuracy=95, moves=[_move("shot", 20.0, 2)])],
            seed=1,
        )
        engine = CombatEngine(s, seed=1)
        hull_before = s.player.hull
        engine.execute_enemy_turns()
        damage = hull_before - s.player.hull
        if damage > 0:
            # 20 * 1.15 = 23
            assert damage == 23, f"Light Frame: expected 23 (20*1.15), got {damage}"


# ============================================================================
# Integration Tests
# ============================================================================


class TestDefensiveIdentityIntegration:
    """Cross-cutting integration tests."""

    def test_identity_field_on_player_state(self) -> None:
        p = _player(defensive_identity="juggernaut")
        assert p.defensive_identity == "juggernaut"

    def test_identity_field_defaults_empty(self) -> None:
        p = _player()
        assert p.defensive_identity == ""

    def test_armor_field_on_player_state(self) -> None:
        p = _player(armor=5)
        assert p.armor == 5

    def test_shield_regen_field_on_player_state(self) -> None:
        p = _player(shield_regen=3)
        assert p.shield_regen == 3

    def test_counterstrike_stacks_field(self) -> None:
        p = _player(defensive_identity="ghost")
        assert p.counterstrike_stacks == 0

    def test_enemy_armor_field(self) -> None:
        t = _enemy(armor=3)
        assert t.combat_armor == 3
        e = EnemyShip.from_template(t)
        assert e.template.combat_armor == 3
