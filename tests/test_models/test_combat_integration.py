"""Tests for combat extensions to existing models (ShipType, Ship, ShipUpgrade, CrewTemplate)."""

from spacegame.models.ship import ShipType, Ship
from spacegame.models.upgrades import ShipUpgrade, ShipUpgradeManager
from spacegame.models.crew import CrewTemplate, CrewRoster
from spacegame.models.combat import (
    CombatMove,
    CombatEffect,
    EffectType,
    EffectTarget,
    build_player_combat_state,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_ship_type(**overrides: object) -> ShipType:
    defaults: dict = {
        "id": "light_freighter",
        "name": "Light Freighter",
        "ship_class": "early_game",
        "description": "A workhorse ship.",
        "cargo_capacity": 150,
        "fuel_capacity": 150,
        "fuel_efficiency": 15,
        "speed_multiplier": 1.0,
        "purchase_price": 25000,
        "resale_value": 17500,
        "crew_slots": 2,
        "special_abilities": [],
        "availability": "common",
    }
    defaults.update(overrides)
    return ShipType(**defaults)


def _make_weapon_upgrade(
    uid: str = "laser_cannon",
    damage: float = 18.0,
    energy_cost: int = 3,
) -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name="Laser Cannon",
        description="A focused laser beam.",
        price=10000,
        slot_type="weapon",
        bonus_type="",
        bonus_value=0.0,
        combat_move={
            "id": uid,
            "name": "Laser Cannon",
            "description": "Fires a focused laser.",
            "effects": [{"type": "damage", "value": damage}],
            "energy_cost": energy_cost,
            "accuracy_modifier": 10,
        },
    )


def _make_defense_upgrade(uid: str = "basic_shield_gen") -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name="Basic Shield Generator",
        description="Restores shields.",
        price=5000,
        slot_type="defense",
        bonus_type="",
        bonus_value=0.0,
        combat_move={
            "id": uid,
            "name": "Shield Restore",
            "description": "Restores 20 shields.",
            "effects": [{"type": "shield_restore", "value": 20.0, "target": "self"}],
            "energy_cost": 2,
        },
    )


def _make_utility_upgrade(uid: str = "cargo_ext") -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name="Cargo Bay Extension",
        description="+20 cargo",
        price=5000,
        slot_type="cargo",
        bonus_type="cargo_bonus",
        bonus_value=20.0,
    )


def _make_crew_template_with_combat(
    template_id: str = "elena_reeves",
) -> CrewTemplate:
    return CrewTemplate(
        id=template_id,
        name="Elena Reeves",
        role="Navigator",
        description="Expert navigator.",
        portrait_color=[100, 150, 200],
        combat_move={
            "id": "evasive_maneuvers",
            "name": "Evasive Maneuvers",
            "description": "+20 evasion for 2 turns.",
            "effects": [{"type": "evasion_mod", "value": 20.0, "duration": 2, "target": "self"}],
            "energy_cost": 0,
        },
    )


# ============================================================================
# ShipType Combat Fields
# ============================================================================


class TestShipTypeCombatFields:
    """Tests for combat stat fields on ShipType."""

    def test_defaults_are_zero(self) -> None:
        st = _make_ship_type()
        assert st.combat_hull == 0
        assert st.combat_shields == 0
        assert st.combat_energy == 0
        assert st.combat_energy_regen == 0
        assert st.combat_speed == 0
        assert st.combat_evasion == 0
        assert st.combat_accuracy == 0

    def test_slot_defaults(self) -> None:
        st = _make_ship_type()
        assert st.weapon_slots == 0
        assert st.defense_slots == 0
        assert st.utility_slots == 3

    def test_custom_combat_stats(self) -> None:
        st = _make_ship_type(
            combat_hull=100,
            combat_shields=40,
            combat_energy=10,
            combat_energy_regen=3,
            combat_speed=8,
            combat_evasion=15,
            combat_accuracy=70,
            weapon_slots=1,
            defense_slots=1,
            utility_slots=3,
        )
        assert st.combat_hull == 100
        assert st.combat_shields == 40
        assert st.combat_energy == 10
        assert st.combat_energy_regen == 3
        assert st.combat_speed == 8
        assert st.combat_evasion == 15
        assert st.combat_accuracy == 70
        assert st.weapon_slots == 1
        assert st.defense_slots == 1

    def test_backward_compat_existing_fields_unchanged(self) -> None:
        st = _make_ship_type()
        assert st.cargo_capacity == 150
        assert st.fuel_capacity == 150
        assert st.fuel_efficiency == 15
        assert st.speed_multiplier == 1.0
        assert st.crew_slots == 2


# ============================================================================
# Ship Hull/Shields
# ============================================================================


class TestShipCombatState:
    """Tests for hull and shield tracking on Ship."""

    def test_current_hull_auto_init(self) -> None:
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=150)
        assert ship.current_hull == 100, "Should auto-init from ship_type.combat_hull"

    def test_current_shields_auto_init(self) -> None:
        st = _make_ship_type(combat_shields=40)
        ship = Ship(ship_type=st, current_fuel=150)
        assert ship.current_shields == 40

    def test_hull_zero_when_ship_type_has_no_combat(self) -> None:
        st = _make_ship_type()  # combat_hull defaults to 0
        ship = Ship(ship_type=st, current_fuel=150)
        assert ship.current_hull == 0

    def test_repair_hull(self) -> None:
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=150)
        ship.current_hull = 50
        repaired = ship.repair_hull(30)
        assert repaired == 30
        assert ship.current_hull == 80

    def test_repair_hull_capped(self) -> None:
        st = _make_ship_type(combat_hull=100)
        ship = Ship(ship_type=st, current_fuel=150)
        ship.current_hull = 90
        repaired = ship.repair_hull(50)
        assert repaired == 10, "Should only repair up to max"
        assert ship.current_hull == 100

    def test_restore_shields(self) -> None:
        st = _make_ship_type(combat_shields=40)
        ship = Ship(ship_type=st, current_fuel=150)
        ship.current_shields = 10
        ship.restore_shields()
        assert ship.current_shields == 40


# ============================================================================
# ShipUpgrade Combat Move
# ============================================================================


class TestShipUpgradeCombatMove:
    """Tests for combat_move field on ShipUpgrade."""

    def test_combat_move_none_by_default(self) -> None:
        u = _make_utility_upgrade()
        assert u.combat_move is None

    def test_weapon_has_combat_move(self) -> None:
        u = _make_weapon_upgrade()
        assert u.combat_move is not None
        assert u.combat_move["id"] == "laser_cannon"

    def test_defense_has_combat_move(self) -> None:
        u = _make_defense_upgrade()
        assert u.combat_move is not None


# ============================================================================
# ShipUpgradeManager Per-Category Slots
# ============================================================================


class TestShipUpgradeManagerCombatIntegration:
    """Tests the surface of ShipUpgradeManager that combat depends on.

    Per-category slot caps were retired in U5; module placement on the
    ShipBuild governs capacity. What remains here is combat-move
    extraction and the category-mapping helper used for UI grouping.
    """

    def test_category_mapping(self) -> None:
        mgr = ShipUpgradeManager()
        assert mgr.get_category("cargo") == "utility"
        assert mgr.get_category("fuel") == "utility"
        assert mgr.get_category("engine") == "utility"
        assert mgr.get_category("mining") == "utility"
        assert mgr.get_category("scanner") == "utility"
        assert mgr.get_category("weapon") == "weapon"
        assert mgr.get_category("defense") == "defense"
        assert mgr.get_category("unknown") == "utility"  # fallback

    def test_get_combat_moves_only_from_weapons_and_defenses(self) -> None:
        """Only upgrades with combat_move contribute moves; utility upgrades do not."""
        mgr = ShipUpgradeManager()
        mgr.install(_make_weapon_upgrade("laser"))
        mgr.install(_make_defense_upgrade("shield"))
        mgr.install(_make_utility_upgrade("cargo"))
        moves = mgr.get_combat_moves()
        assert len(moves) == 2, "Only weapon + defense have combat moves"
        move_ids = {m.id for m in moves}
        assert "laser" in move_ids
        assert "shield" in move_ids

    def test_mixed_install_no_longer_gated_by_category(self) -> None:
        """Without slot caps, weapons/defenses/utilities all install freely."""
        mgr = ShipUpgradeManager()
        assert mgr.install(_make_weapon_upgrade("w1"))[0]
        assert mgr.install(_make_weapon_upgrade("w2"))[0]
        assert mgr.install(_make_defense_upgrade("d1"))[0]
        assert mgr.install(_make_utility_upgrade("u1"))[0]
        assert len(mgr.installed) == 4


# ============================================================================
# CrewTemplate Combat Move
# ============================================================================


class TestCrewTemplateCombatMove:
    """Tests for combat_move field on CrewTemplate."""

    def test_combat_move_none_by_default(self) -> None:
        ct = CrewTemplate(
            id="test",
            name="Test",
            role="Pilot",
            description="A pilot.",
            portrait_color=[100, 100, 100],
        )
        assert ct.combat_move is None

    def test_combat_move_set(self) -> None:
        ct = _make_crew_template_with_combat()
        assert ct.combat_move is not None
        assert ct.combat_move["id"] == "evasive_maneuvers"


# ============================================================================
# build_player_combat_state Factory
# ============================================================================


class TestBuildPlayerCombatState:
    """Tests for the factory that builds PlayerCombatState from game objects."""

    def test_basic_build(self) -> None:
        st = _make_ship_type(
            combat_hull=100,
            combat_shields=40,
            combat_energy=10,
            combat_energy_regen=3,
            combat_speed=8,
            combat_evasion=15,
            combat_accuracy=70,
            weapon_slots=1,
            defense_slots=1,
            utility_slots=3,
        )
        ship = Ship(ship_type=st, current_fuel=150)
        mgr = ShipUpgradeManager()
        mgr.install(_make_weapon_upgrade())

        state = build_player_combat_state(ship, mgr, None, {})
        assert state.max_hull == 100
        assert state.hull == ship.current_hull
        assert state.max_shields == 40
        assert state.shields == ship.current_shields
        assert state.max_energy == 10
        assert state.energy == 10
        assert state.energy_regen == 3
        assert state.speed == 8
        assert state.evasion == 15
        assert state.accuracy == 70
        assert len(state.equipment_moves) == 1

    def test_build_with_crew_moves(self) -> None:
        st = _make_ship_type(
            combat_hull=100,
            combat_shields=40,
            combat_energy=10,
            combat_energy_regen=3,
            combat_speed=8,
            combat_evasion=15,
            combat_accuracy=70,
        )
        ship = Ship(ship_type=st, current_fuel=150)
        mgr = ShipUpgradeManager()

        templates = {"elena": _make_crew_template_with_combat("elena")}
        roster = CrewRoster(templates)
        roster.recruit("elena", 2)

        crew_moves = {
            "elena": CombatMove(
                id="evasive_maneuvers",
                name="Evasive Maneuvers",
                description="+20 evasion",
                effects=[
                    CombatEffect(
                        type=EffectType.EVASION_MOD,
                        value=20.0,
                        duration=2,
                        target=EffectTarget.SELF,
                    )
                ],
            ),
        }
        state = build_player_combat_state(ship, mgr, roster, crew_moves)
        assert len(state.crew_moves) == 1
        assert state.crew_moves[0].id == "evasive_maneuvers"

    def test_build_no_combat_stats(self) -> None:
        st = _make_ship_type()  # all combat fields default to 0
        ship = Ship(ship_type=st, current_fuel=150)
        mgr = ShipUpgradeManager()
        state = build_player_combat_state(ship, mgr, None, {})
        assert state.max_hull == 0
        assert state.max_shields == 0
        assert state.equipment_moves == []
        assert state.crew_moves == []
