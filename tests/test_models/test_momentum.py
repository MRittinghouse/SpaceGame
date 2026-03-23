"""Tests for MomentumGauge — Phase 8 combat momentum system."""

from spacegame.models.momentum import (
    MomentumGauge,
    ShipUltimate,
    SHIP_CLASS_CATEGORIES,
    get_ship_class_category,
)


class TestMomentumGauge:
    """Core momentum gauge behavior."""

    def test_initial_state(self) -> None:
        gauge = MomentumGauge()
        assert gauge.current == 0.0
        assert not gauge.overdriven_available
        assert not gauge.overclock_triggered
        assert gauge.ultimate_available is False

    def test_add_momentum(self) -> None:
        gauge = MomentumGauge()
        crossed = gauge.add(0.05)
        assert gauge.current == 0.05
        assert crossed == []

    def test_add_multiple(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.10)
        gauge.add(0.10)
        assert gauge.current == 0.20
        assert not gauge.overdriven_available

    def test_caps_at_one(self) -> None:
        gauge = MomentumGauge()
        gauge.add(1.5)
        assert gauge.current == 1.0

    def test_negative_add_ignored(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.5)
        gauge.add(-0.3)
        assert gauge.current == 0.5, "Negative momentum should be ignored"

    # === Threshold Detection ===

    def test_crossing_25_returns_charged(self) -> None:
        gauge = MomentumGauge()
        crossed = gauge.add(0.30)
        assert "charged" in crossed

    def test_crossing_50_returns_surging(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.30)
        crossed = gauge.add(0.25)
        assert "surging" in crossed
        assert gauge.overdriven_available

    def test_crossing_75_returns_overload(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.50)
        crossed = gauge.add(0.30)
        assert "overload" in crossed
        assert gauge.overclock_triggered

    def test_crossing_100_returns_ultimate(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.50)
        gauge.add(0.30)
        crossed = gauge.add(0.25)
        assert "ultimate" in crossed

    def test_crossing_multiple_thresholds_at_once(self) -> None:
        gauge = MomentumGauge()
        crossed = gauge.add(0.80)
        assert "charged" in crossed
        assert "surging" in crossed
        assert "overload" in crossed
        assert "ultimate" not in crossed

    def test_threshold_not_reported_twice(self) -> None:
        gauge = MomentumGauge()
        crossed1 = gauge.add(0.30)
        assert "charged" in crossed1
        crossed2 = gauge.add(0.05)
        assert "charged" not in crossed2, "Should not re-report already crossed threshold"

    # === Overdriven Weapon (50% threshold) ===

    def test_overdriven_available_at_50(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.55)
        assert gauge.overdriven_available

    def test_consume_overdriven(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.55)
        assert gauge.overdriven_available
        gauge.consume_overdriven()
        assert not gauge.overdriven_available
        assert gauge.current == 0.55, "Consuming overdriven should not change momentum"

    def test_overdriven_recharges_on_recross(self) -> None:
        """Overdriven recharges when momentum drops below 50% and re-crosses."""
        gauge = MomentumGauge()
        gauge.add(0.55)
        gauge.consume_overdriven()
        assert not gauge.overdriven_available
        # Simulate momentum dropping (e.g., after ultimate resets to 0, then rebuilds)
        gauge.current = 0.45
        gauge._thresholds_crossed.discard("surging")
        crossed = gauge.add(0.10)
        assert "surging" in crossed
        assert gauge.overdriven_available

    # === System Overclock (75% threshold) ===

    def test_overclock_triggered_at_75(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.80)
        assert gauge.overclock_triggered

    def test_overclock_only_fires_once(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.80)
        assert gauge.overclock_triggered
        gauge.overclock_triggered = False  # Simulating engine consuming it
        gauge.add(0.05)
        assert not gauge.overclock_triggered, "Should not re-trigger without re-crossing"

    # === Ultimate (100% threshold) ===

    def test_ultimate_available_at_100(self) -> None:
        gauge = MomentumGauge()
        gauge.add(1.0)
        assert gauge.ultimate_available

    def test_ultimate_not_available_below_100(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.99)
        assert not gauge.ultimate_available

    def test_consume_ultimate_resets_to_zero(self) -> None:
        gauge = MomentumGauge()
        gauge.add(1.0)
        gauge.consume_ultimate()
        assert gauge.current == 0.0
        assert not gauge.overdriven_available
        assert not gauge.overclock_triggered
        assert not gauge.ultimate_available

    def test_consume_ultimate_clears_all_thresholds(self) -> None:
        """After ultimate, all thresholds can be re-crossed on rebuild."""
        gauge = MomentumGauge()
        gauge.add(1.0)
        gauge.consume_ultimate()
        crossed = gauge.add(0.30)
        assert "charged" in crossed

    # === Serialization ===

    def test_to_dict_from_dict_round_trip(self) -> None:
        gauge = MomentumGauge()
        gauge.add(0.65)
        gauge.consume_overdriven()
        data = gauge.to_dict()
        restored = MomentumGauge.from_dict(data)
        assert restored.current == gauge.current
        assert restored.overdriven_available == gauge.overdriven_available
        assert restored.overclock_triggered == gauge.overclock_triggered


class TestShipUltimate:
    """Ship class ultimate definitions."""

    def test_ship_ultimate_fields(self) -> None:
        ult = ShipUltimate(
            id="nova_barrage",
            name="Nova Barrage",
            ship_class_category="heavy_combat",
            description="60 damage to ALL enemies.",
            effects=[{"type": "damage", "value": 60.0, "target": "all_enemies"}],
            visual_type="damage_aoe",
        )
        assert ult.id == "nova_barrage"
        assert ult.ship_class_category == "heavy_combat"

    def test_to_dict_from_dict(self) -> None:
        ult = ShipUltimate(
            id="ghost_protocol",
            name="Ghost Protocol",
            ship_class_category="stealth",
            description="Immune to all damage for 2 turns.",
            effects=[{"type": "damage_reduction", "value": 100.0, "duration": 2}],
            visual_type="buff_self",
        )
        data = ult.to_dict()
        restored = ShipUltimate.from_dict(data)
        assert restored.id == ult.id
        assert restored.effects == ult.effects


class TestShipClassCategories:
    """Ship class category mapping."""

    def test_all_24_ships_have_category(self) -> None:
        all_ships: set[str] = set()
        for ships in SHIP_CLASS_CATEGORIES.values():
            all_ships.update(ships)
        expected_ships = {
            "shuttle", "light_freighter", "prospector", "patrol_cutter",
            "medium_freighter", "fast_courier", "armed_trader", "scout_vessel",
            "corsair", "mining_barge", "smugglers_sloop", "salvage_rig",
            "bulk_hauler", "luxury_yacht", "clipper", "war_frigate",
            "deep_explorer", "phantom", "industrial_titan", "diplomatic_cruiser",
            "consortium_merchantman", "syndicate_enforcer", "frontier_runner",
            "institute_vessel",
        }
        assert all_ships == expected_ships, f"Missing: {expected_ships - all_ships}, Extra: {all_ships - expected_ships}"

    def test_no_ship_in_multiple_categories(self) -> None:
        seen: dict[str, str] = {}
        for category, ships in SHIP_CLASS_CATEGORIES.items():
            for ship in ships:
                assert ship not in seen, f"{ship} in both {seen[ship]} and {category}"
                seen[ship] = category

    def test_14_categories_exist(self) -> None:
        assert len(SHIP_CLASS_CATEGORIES) == 14

    def test_get_ship_class_category(self) -> None:
        assert get_ship_class_category("shuttle") == "starter"
        assert get_ship_class_category("war_frigate") == "heavy_combat"
        assert get_ship_class_category("phantom") == "stealth"
        assert get_ship_class_category("institute_vessel") == "faction_science"

    def test_get_ship_class_category_unknown_returns_none(self) -> None:
        assert get_ship_class_category("nonexistent_ship") is None


# ============================================================================
# Engine integration tests
# ============================================================================

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


def _make_test_move(
    id: str = "blaster",
    damage: float = 10.0,
    energy_cost: int = 2,
    element: WeaponElement = WeaponElement.KINETIC,
    aoe: bool = False,
) -> CombatMove:
    return CombatMove(
        id=id, name=id.title(), description=f"{id} attack",
        effects=[CombatEffect(type=EffectType.DAMAGE, value=damage)],
        energy_cost=energy_cost, element=element, aoe=aoe,
    )


def _make_test_enemy(
    hull: int = 80, shields: int = 0, evasion: int = 0,
) -> EnemyShipTemplate:
    return EnemyShipTemplate(
        id="test_enemy", name="Test Enemy", description="Test",
        behavior=EnemyBehavior.AGGRESSIVE,
        hull=hull, shields=shields, energy=10, energy_regen=3,
        speed=8, evasion=evasion, accuracy=70,
        moves=[_make_test_move("enemy_blaster", 5.0)],
        loot_table=[], negotiate_difficulty=3, flee_threshold=0.4,
        bribe_cost=0,
    )


def _make_test_state(
    player_moves: list[CombatMove] | None = None,
    enemy_templates: list[EnemyShipTemplate] | None = None,
    ship_class_category: str = "fast_scout",
    seed: int = 1,
) -> CombatState:
    if player_moves is None:
        player_moves = [_make_test_move("laser", 20.0, 3)]
    if enemy_templates is None:
        enemy_templates = [_make_test_enemy()]

    player = PlayerCombatState(
        hull=100, max_hull=100, shields=40, max_shields=40,
        energy=10, max_energy=10, energy_regen=3,
        speed=8, evasion=0, accuracy=95,  # High accuracy to ensure hits
        equipment_moves=player_moves, crew_moves=[],
        active_effects=[], cooldowns={},
        ship_class_category=ship_class_category,
    )
    encounter = CombatEncounter(enemy_templates=enemy_templates, encounter_seed=seed)
    enemies = [EnemyShip.from_template(t) for t in enemy_templates]
    return CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])


class TestMomentumEngineIntegration:
    """Test momentum triggers in the combat engine."""

    def test_player_combat_state_has_momentum(self) -> None:
        state = _make_test_state()
        assert state.player.momentum is not None
        assert state.player.momentum.current == 0.0

    def test_momentum_builds_on_player_hit(self) -> None:
        state = _make_test_state(seed=42)
        engine = CombatEngine(state, seed=42)
        # Fire weapon — should hit (95 accuracy vs 0 evasion)
        engine.execute_player_move("laser", 0)
        assert state.player.momentum.current > 0, "Momentum should increase on hit"

    def test_momentum_builds_on_enemy_kill(self) -> None:
        # Enemy with very low hull — should die in one hit
        state = _make_test_state(
            player_moves=[_make_test_move("cannon", 100.0, 3)],
            enemy_templates=[_make_test_enemy(hull=10)],
        )
        engine = CombatEngine(state, seed=42)
        engine.execute_player_move("cannon", 0)
        # Should have hit momentum + kill momentum
        assert state.player.momentum.current >= 0.20, (
            f"Expected >=0.20 (hit + kill), got {state.player.momentum.current}"
        )

    def test_momentum_builds_on_taking_damage(self) -> None:
        # Use enemy with 95 accuracy and seed that guarantees a hit
        high_acc_enemy = EnemyShipTemplate(
            id="sniper", name="Sniper", description="Test",
            behavior=EnemyBehavior.AGGRESSIVE,
            hull=80, shields=0, energy=10, energy_regen=3,
            speed=8, evasion=0, accuracy=95,
            moves=[_make_test_move("sniper_shot", 15.0)],
            loot_table=[], negotiate_difficulty=3, flee_threshold=0.4,
            bribe_cost=0,
        )
        state = _make_test_state(enemy_templates=[high_acc_enemy], seed=1)
        engine = CombatEngine(state, seed=1)
        state.player.shields = 0  # Remove shields so hull takes damage
        engine.execute_enemy_turns()
        assert state.player.momentum.current > 0, (
            f"Momentum should increase when player takes hull damage. "
            f"Log: {[e.effects_applied for e in state.combat_log]}"
        )

    def test_momentum_builds_on_crew_ability(self) -> None:
        crew_move = CombatMove(
            id="repair", name="Repair", description="Heal",
            effects=[CombatEffect(type=EffectType.HULL_RESTORE, value=10, target=EffectTarget.SELF)],
            energy_cost=2,
        )
        state = _make_test_state()
        state.player.crew_moves = [crew_move]
        engine = CombatEngine(state, seed=42)
        engine.execute_crew_moves(chosen_move_id="repair")
        assert state.player.momentum.current >= 0.03, "Crew ability should add momentum"

    def test_momentum_builds_on_elemental_status(self) -> None:
        plasma_move = _make_test_move("plasma", 20.0, 3, element=WeaponElement.PLASMA)
        state = _make_test_state(player_moves=[plasma_move])
        engine = CombatEngine(state, seed=42)
        engine.execute_player_move("plasma", 0)
        # Should have hit momentum + status applied momentum
        expected_min = 0.05 + 0.02  # hit + burn applied
        assert state.player.momentum.current >= expected_min, (
            f"Expected >={expected_min}, got {state.player.momentum.current}"
        )

    def test_overdriven_doubles_damage(self) -> None:
        state = _make_test_state(
            player_moves=[_make_test_move("laser", 20.0, 3)],
            enemy_templates=[_make_test_enemy(hull=200)],
        )
        engine = CombatEngine(state, seed=42)

        # Manually set momentum to 55% with overdriven available
        state.player.momentum.add(0.55)
        assert state.player.momentum.overdriven_available

        enemy_hull_before = state.enemies[0].current_hull
        engine.execute_player_move("laser", 0)
        damage_dealt = enemy_hull_before - state.enemies[0].current_hull

        # With 2x damage boost, 20 base damage should become ~40
        assert damage_dealt >= 35, f"Overdriven should roughly double damage, got {damage_dealt}"
        assert not state.player.momentum.overdriven_available, "Overdriven should be consumed"

    def test_ultimate_requires_100_percent(self) -> None:
        state = _make_test_state()
        engine = CombatEngine(state, seed=42)
        state.player.momentum.add(0.50)
        logs = engine.execute_ultimate()
        assert not logs[0].hit, "Ultimate should fail below 100%"

    def test_ultimate_resets_momentum(self) -> None:
        state = _make_test_state(ship_class_category="heavy_combat")
        engine = CombatEngine(state, seed=42)
        state.player.momentum.add(1.0)
        assert state.player.momentum.ultimate_available
        # Need data loader to have ultimates loaded
        # This test verifies the momentum reset even if ultimate resolution is partial
        logs = engine.execute_ultimate()
        assert state.player.momentum.current == 0.0, "Ultimate should reset momentum to 0"

    def test_critical_hp_surge_fires_once(self) -> None:
        state = _make_test_state()
        state.player.hull = 100
        state.player.shields = 0

        engine = CombatEngine(state, seed=42)
        # Simulate taking heavy damage
        state.player.hull = 20  # Below 25%
        engine._check_critical_hp_surge()
        momentum_after_first = state.player.momentum.current

        assert momentum_after_first >= 0.20, "Critical HP surge should add 20%"
        assert state.player.critical_hp_surge_fired

        # Should not fire again
        engine._check_critical_hp_surge()
        assert state.player.momentum.current == momentum_after_first, "Surge should not fire twice"
