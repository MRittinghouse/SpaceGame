"""Tests for Phase 9 — Crew Combo Abilities.

Tests combo definitions, availability checking, discovery tracking,
and combat engine execution.
"""

from spacegame.models.crew_combos import (
    CrewCombo,
    CREW_COMBOS,
    get_available_combos,
    get_combo_by_id,
)
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
)
from spacegame.models.combat_engine import CombatEngine


# ============================================================================
# Helpers
# ============================================================================


def _move(id: str = "blaster", damage: float = 10.0, energy: int = 2) -> CombatMove:
    return CombatMove(
        id=id, name=id.title(), description=f"{id}",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy,
    )


def _enemy(hull: int = 80) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id="test_enemy", name="Test Enemy", description="Test",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull, shields=20, energy=10, energy_regen=3,
        speed=8, evasion=0, accuracy=70,
        moves=[_move("enemy_shot", 5.0)],
        loot_table=[], bribe_cost=0,
    )


def _player(energy: int = 10, momentum_pct: float = 0.0) -> PlayerCombatState:
    p = PlayerCombatState(
        hull=80, max_hull=100, shields=30, max_shields=40,
        energy=energy, max_energy=10, energy_regen=3,
        speed=8, evasion=15, accuracy=70,
        equipment_moves=[_move("laser", 20.0, 3)], crew_moves=[],
        active_effects=[], cooldowns={},
    )
    if momentum_pct > 0:
        p.momentum.add(momentum_pct)
    return p


def _state(
    player: PlayerCombatState | None = None,
    enemies: list[EnemyShipTemplate] | None = None,
    seed: int = 42,
) -> CombatState:
    if player is None:
        player = _player(momentum_pct=0.30)
    if enemies is None:
        enemies = [_enemy()]
    encounter = CombatEncounter(enemy_templates=enemies, encounter_seed=seed)
    enemy_ships = [EnemyShip.from_template(t) for t in enemies]
    return CombatState(
        player=player, enemies=enemy_ships, encounter=encounter, combat_log=[],
    )


# ============================================================================
# Combo Definition Tests
# ============================================================================


class TestComboDefinitions:
    """Verify all 6 combos are properly defined."""

    def test_six_combos_exist(self) -> None:
        assert len(CREW_COMBOS) == 6

    def test_all_combos_have_two_crew(self) -> None:
        for combo in CREW_COMBOS:
            assert len(combo.crew_pair) == 2, f"{combo.id} needs exactly 2 crew"
            assert combo.crew_pair[0] != combo.crew_pair[1], f"{combo.id} has duplicate crew"

    def test_all_combos_have_energy_cost(self) -> None:
        for combo in CREW_COMBOS:
            assert combo.energy_cost > 0, f"{combo.id} needs energy cost > 0"

    def test_combo_ids_unique(self) -> None:
        ids = [c.id for c in CREW_COMBOS]
        assert len(ids) == len(set(ids)), "Combo IDs must be unique"

    def test_get_combo_by_id(self) -> None:
        combo = get_combo_by_id("emergency_overhaul")
        assert combo is not None
        assert combo.name == "Emergency Overhaul"
        assert set(combo.crew_pair) == {"elena", "marcus"}

    def test_get_combo_by_id_unknown(self) -> None:
        assert get_combo_by_id("nonexistent") is None

    def test_all_crew_pairs_covered(self) -> None:
        """All 6 possible pairs from 4 companions are represented."""
        pairs = set()
        for combo in CREW_COMBOS:
            pair = frozenset(combo.crew_pair)
            pairs.add(pair)
        expected = {
            frozenset({"elena", "marcus"}),
            frozenset({"elena", "priya"}),
            frozenset({"elena", "tomas"}),
            frozenset({"marcus", "priya"}),
            frozenset({"marcus", "tomas"}),
            frozenset({"priya", "tomas"}),
        }
        assert pairs == expected

    def test_combo_serialization(self) -> None:
        combo = get_combo_by_id("emergency_overhaul")
        data = combo.to_dict()
        restored = CrewCombo.from_dict(data)
        assert restored.id == combo.id
        assert restored.crew_pair == combo.crew_pair
        assert restored.energy_cost == combo.energy_cost


# ============================================================================
# Availability Tests
# ============================================================================


class TestComboAvailability:
    """Test when combos become available."""

    def test_available_with_both_crew_and_momentum(self) -> None:
        recruited = {"elena", "marcus"}
        discovered = {"emergency_overhaul"}
        available = get_available_combos(recruited, discovered, momentum_pct=0.30, energy=10)
        assert len(available) == 1
        assert available[0].id == "emergency_overhaul"

    def test_not_available_without_momentum(self) -> None:
        recruited = {"elena", "marcus"}
        discovered = {"emergency_overhaul"}
        available = get_available_combos(recruited, discovered, momentum_pct=0.20, energy=10)
        assert len(available) == 0, "Combo requires 25% momentum"

    def test_not_available_without_both_crew(self) -> None:
        recruited = {"elena"}  # Missing marcus
        discovered = {"emergency_overhaul"}
        available = get_available_combos(recruited, discovered, momentum_pct=0.30, energy=10)
        assert len(available) == 0, "Need both crew members"

    def test_not_available_without_discovery(self) -> None:
        recruited = {"elena", "marcus"}
        discovered: set[str] = set()  # Not yet discovered
        available = get_available_combos(recruited, discovered, momentum_pct=0.30, energy=10)
        assert len(available) == 0, "Combo must be discovered first"

    def test_not_available_without_energy(self) -> None:
        recruited = {"elena", "marcus"}
        discovered = {"emergency_overhaul"}
        available = get_available_combos(recruited, discovered, momentum_pct=0.30, energy=2)
        assert len(available) == 0, "Not enough energy (costs 5)"

    def test_multiple_combos_available(self) -> None:
        recruited = {"elena", "marcus", "priya"}
        discovered = {"emergency_overhaul", "precision_strike_protocol", "system_purge"}
        available = get_available_combos(recruited, discovered, momentum_pct=0.30, energy=10)
        ids = {c.id for c in available}
        # Elena+Marcus, Elena+Priya, Marcus+Priya — all 3 should be available
        assert "emergency_overhaul" in ids
        assert "precision_strike_protocol" in ids
        assert "system_purge" in ids

    def test_discovery_check_both_crew_and_momentum(self) -> None:
        """Discovery happens when both crew are recruited and 25% momentum is first reached."""
        from spacegame.models.crew_combos import check_combo_discoveries
        recruited = {"elena", "marcus", "tomas"}
        already_discovered: set[str] = set()
        newly_discovered = check_combo_discoveries(recruited, already_discovered)
        # Should discover combos for all pairs involving recruited members
        ids = {c.id for c in newly_discovered}
        assert "emergency_overhaul" in ids    # elena + marcus
        assert "smugglers_escape" in ids      # elena + tomas
        assert "jury_rigged_countermeasures" in ids  # marcus + tomas

    def test_no_rediscovery(self) -> None:
        from spacegame.models.crew_combos import check_combo_discoveries
        recruited = {"elena", "marcus"}
        already_discovered = {"emergency_overhaul"}
        newly_discovered = check_combo_discoveries(recruited, already_discovered)
        assert len(newly_discovered) == 0, "Should not rediscover"


# ============================================================================
# Engine Execution Tests
# ============================================================================


class TestComboExecution:
    """Test combo resolution in the combat engine."""

    def test_emergency_overhaul_heals_and_restores_energy(self) -> None:
        s = _state(player=_player(energy=8, momentum_pct=0.30))
        s.player.hull = 50
        engine = CombatEngine(s, seed=42)
        logs = engine.execute_crew_combo("emergency_overhaul")
        assert len(logs) > 0
        assert logs[0].hit
        # Should restore 40 hull (capped at max) and 5 energy
        assert s.player.hull == 90, f"Expected 90 (50 + 40), got {s.player.hull}"
        # Energy: 8 - 5 (cost) + 5 (effect) = 8
        assert s.player.energy == 8, f"Expected 8, got {s.player.energy}"

    def test_combo_deducts_energy(self) -> None:
        """Smuggler's Escape costs 3 energy, then restores 3 → net 0 change."""
        s = _state(player=_player(energy=6, momentum_pct=0.30))
        engine = CombatEngine(s, seed=42)
        engine.execute_crew_combo("smugglers_escape")  # Costs 3, restores 3
        # Net: 6 - 3 (cost) + 3 (restore) = 6
        assert s.player.energy == 6, f"Expected 6 (6-3+3), got {s.player.energy}"

    def test_combo_fails_without_energy(self) -> None:
        s = _state(player=_player(energy=2, momentum_pct=0.30))
        engine = CombatEngine(s, seed=42)
        logs = engine.execute_crew_combo("emergency_overhaul")  # Costs 5
        assert not logs[0].hit, "Should fail with insufficient energy"

    def test_combo_fails_without_momentum(self) -> None:
        s = _state(player=_player(energy=10, momentum_pct=0.10))
        engine = CombatEngine(s, seed=42)
        logs = engine.execute_crew_combo("emergency_overhaul")
        assert not logs[0].hit, "Should fail below 25% momentum"

    def test_combo_adds_momentum(self) -> None:
        s = _state(player=_player(energy=10, momentum_pct=0.30))
        engine = CombatEngine(s, seed=42)
        momentum_before = s.player.momentum.current
        engine.execute_crew_combo("emergency_overhaul")
        assert s.player.momentum.current > momentum_before, "Combo should add crew momentum"

    def test_precision_strike_protocol(self) -> None:
        """Next attack: 100% accuracy + 50% bonus damage."""
        s = _state(player=_player(energy=10, momentum_pct=0.30))
        engine = CombatEngine(s, seed=42)
        engine.execute_crew_combo("precision_strike_protocol")
        # Should have accuracy and damage boost effects
        has_acc = any(e.type == EffectType.ACCURACY_MOD for e, _ in s.player.active_effects)
        has_dmg = any(e.type == EffectType.DAMAGE_BOOST for e, _ in s.player.active_effects)
        assert has_acc, "Should add accuracy modifier"
        assert has_dmg, "Should add damage boost"

    def test_system_purge_cleanses(self) -> None:
        """Cleanse all debuffs + restore 20 shields."""
        s = _state(player=_player(energy=10, momentum_pct=0.30))
        # Add some debuffs
        debuff = CombatEffect(type=EffectType.BURN, value=5.0, duration=3)
        s.player.active_effects.append((debuff, 3))
        s.player.shields = 10
        engine = CombatEngine(s, seed=42)
        engine.execute_crew_combo("system_purge")
        burns = [e for e, _ in s.player.active_effects if e.type == EffectType.BURN]
        assert len(burns) == 0, "Burn should be cleansed"
        assert s.player.shields >= 25, f"Expected shields restored, got {s.player.shields}"
