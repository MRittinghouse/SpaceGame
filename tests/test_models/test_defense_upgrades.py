"""Tests for Phase 12B — Defense upgrade bonus wiring.

Verifies that armor_bonus, shield_regen_bonus, evasion_bonus, and
shield_bonus from upgrade_manager flow into PlayerCombatState.
"""

from unittest.mock import MagicMock
from spacegame.models.combat import build_player_combat_state, PlayerCombatState


def _mock_ship(
    hull: int = 100, shields: int = 40, energy: int = 10,
    energy_regen: int = 3, speed: int = 8, evasion: int = 15,
    accuracy: int = 70, armor: int = 0, shield_regen: int = 0,
    identity: str = "",
) -> MagicMock:
    """Create a mock Ship with ShipType attributes."""
    ship = MagicMock()
    ship.current_hull = hull
    ship.current_shields = shields
    st = MagicMock()
    st.combat_hull = hull
    st.combat_shields = shields
    st.combat_energy = energy
    st.combat_energy_regen = energy_regen
    st.combat_speed = speed
    st.combat_evasion = evasion
    st.combat_accuracy = accuracy
    st.combat_armor = armor
    st.combat_shield_regen = shield_regen
    st.defensive_identity = identity
    st.ship_class_category = "fast_scout"
    ship.ship_type = st
    return ship


def _mock_upgrade_manager(**bonuses: float) -> MagicMock:
    """Create a mock UpgradeManager that returns specified bonuses."""
    um = MagicMock()
    um.get_combat_moves.return_value = []

    def get_bonus(bonus_type: str) -> float:
        return bonuses.get(bonus_type, 0.0)

    um.get_bonus = get_bonus
    return um


class TestDefenseUpgradeBonusWiring:
    """Verify upgrade bonuses flow into PlayerCombatState."""

    def test_armor_bonus_from_upgrades(self) -> None:
        ship = _mock_ship(armor=1)
        um = _mock_upgrade_manager(armor_bonus=3.0)
        state = build_player_combat_state(ship, um, None, {})
        assert state.armor == 4, f"Expected 4 (1 base + 3 upgrade), got {state.armor}"

    def test_shield_regen_bonus_from_upgrades(self) -> None:
        ship = _mock_ship(shield_regen=2)
        um = _mock_upgrade_manager(shield_regen_bonus=4.0)
        state = build_player_combat_state(ship, um, None, {})
        assert state.shield_regen == 6, f"Expected 6 (2 base + 4 upgrade), got {state.shield_regen}"

    def test_evasion_bonus_from_upgrades(self) -> None:
        ship = _mock_ship(evasion=15)
        um = _mock_upgrade_manager(evasion_bonus=8.0)
        state = build_player_combat_state(ship, um, None, {})
        assert state.evasion == 23, f"Expected 23 (15 base + 8 upgrade), got {state.evasion}"

    def test_shield_max_bonus_from_upgrades(self) -> None:
        ship = _mock_ship(shields=40)
        um = _mock_upgrade_manager(shield_bonus=10.0)
        state = build_player_combat_state(ship, um, None, {})
        assert state.max_shields == 50, f"Expected 50 (40 base + 10 upgrade), got {state.max_shields}"

    def test_flee_bonus_from_upgrades(self) -> None:
        ship = _mock_ship()
        um = _mock_upgrade_manager(flee_bonus=15.0)
        # player_level=50 avoids the early-game flee bonus
        state = build_player_combat_state(ship, um, None, {}, player_level=50)
        assert state.flee_bonus == 15

    def test_no_bonuses_default_zero(self) -> None:
        ship = _mock_ship(armor=0, shield_regen=0, evasion=20)
        um = _mock_upgrade_manager()  # No bonuses
        state = build_player_combat_state(ship, um, None, {})
        assert state.armor == 0
        assert state.shield_regen == 0
        assert state.evasion == 20

    def test_combined_bonuses(self) -> None:
        ship = _mock_ship(armor=2, shield_regen=3, evasion=10)
        um = _mock_upgrade_manager(
            armor_bonus=2.0, shield_regen_bonus=3.0,
            evasion_bonus=5.0, shield_bonus=15.0,
        )
        state = build_player_combat_state(ship, um, None, {})
        assert state.armor == 4
        assert state.shield_regen == 6
        assert state.evasion == 15
        assert state.max_shields == 55  # 40 base + 15 upgrade
