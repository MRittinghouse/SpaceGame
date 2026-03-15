"""
Tests for the upgrade enhancement system (Mk1 → Mk2 → Mk3).

Covers: InstalledUpgrade, mark multipliers, tuning system, enhancement costs,
backward compatibility, and bonus integration.
"""

import pytest
from spacegame.models.upgrades import (
    ShipUpgrade,
    ShipUpgradeManager,
    InstalledUpgrade,
    MARK_MULTIPLIERS,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_upgrade(
    uid: str = "test_upgrade",
    bonus_type: str = "cargo_bonus",
    bonus_value: float = 20.0,
    slot_type: str = "cargo",
    price: int = 5000,
    tuning_options: list | None = None,
    max_mark: int = 3,
    faction_required: str | None = None,
    faction_rep_required: int = 0,
    unlock_condition: str | None = None,
) -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name=f"Upgrade {uid}",
        description="Test upgrade",
        price=price,
        slot_type=slot_type,
        bonus_type=bonus_type,
        bonus_value=bonus_value,
        max_mark=max_mark,
        tuning_options=tuning_options or [],
        faction_required=faction_required,
        faction_rep_required=faction_rep_required,
        unlock_condition=unlock_condition,
    )


def _make_weapon(uid: str = "test_weapon", price: int = 10000) -> ShipUpgrade:
    return ShipUpgrade(
        id=uid,
        name=f"Weapon {uid}",
        description="Test weapon",
        price=price,
        slot_type="weapon",
        bonus_type="",
        bonus_value=0.0,
        combat_move={
            "id": uid,
            "name": f"Fire {uid}",
            "description": "Test",
            "effects": [{"type": "damage", "value": 20.0}],
            "energy_cost": 3,
            "accuracy_modifier": 10,
        },
        tuning_options=[
            {
                "id": "overcharged",
                "name": "Overcharged",
                "description": "+4 damage",
                "bonus_type": "damage_bonus",
                "bonus_value": 4.0,
            },
            {
                "id": "precision",
                "name": "Precision",
                "description": "+15 accuracy",
                "bonus_type": "accuracy_bonus",
                "bonus_value": 15.0,
            },
        ],
    )


SAMPLE_TUNINGS = [
    {
        "id": "reinforced",
        "name": "Reinforced",
        "description": "+10 hull HP",
        "bonus_type": "hull_bonus",
        "bonus_value": 10.0,
    },
    {
        "id": "optimized",
        "name": "Optimized",
        "description": "+5 cargo",
        "bonus_type": "cargo_bonus",
        "bonus_value": 5.0,
    },
]


# ============================================================================
# InstalledUpgrade
# ============================================================================


class TestInstalledUpgrade:
    """Tests for the InstalledUpgrade dataclass."""

    def test_default_state(self) -> None:
        inst = InstalledUpgrade(upgrade_id="cargo_bay")
        assert inst.upgrade_id == "cargo_bay"
        assert inst.mark == 1
        assert inst.tuning is None

    def test_mk2_with_tuning(self) -> None:
        inst = InstalledUpgrade(upgrade_id="cargo_bay", mark=2, tuning="reinforced")
        assert inst.mark == 2
        assert inst.tuning == "reinforced"

    def test_mk3_with_tuning(self) -> None:
        inst = InstalledUpgrade(upgrade_id="cargo_bay", mark=3, tuning="reinforced")
        assert inst.mark == 3
        assert inst.tuning == "reinforced"


# ============================================================================
# Mark Multipliers
# ============================================================================


class TestMarkMultipliers:
    """Tests for mark-based bonus scaling."""

    def test_mk1_multiplier(self) -> None:
        assert MARK_MULTIPLIERS[1] == 1.0

    def test_mk2_multiplier(self) -> None:
        assert MARK_MULTIPLIERS[2] == 1.25

    def test_mk3_multiplier(self) -> None:
        assert MARK_MULTIPLIERS[3] == 1.50

    def test_mk1_bonus_unchanged(self) -> None:
        """Mk1 upgrade bonus should be the base value."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(bonus_value=20.0)
        mgr.install(upgrade)
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(20.0)

    def test_mk2_bonus_scaled(self) -> None:
        """Mk2 upgrade bonus should be base × 1.25."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(bonus_value=20.0)
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2)
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(25.0)

    def test_mk3_bonus_scaled(self) -> None:
        """Mk3 upgrade bonus should be base × 1.50."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(bonus_value=20.0)
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2)
        mgr.enhance("test_upgrade", mark=3)
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(30.0)

    def test_multiple_upgrades_independent_marks(self) -> None:
        """Different upgrades can have different mark levels."""
        mgr = ShipUpgradeManager(utility_slots=3)
        u1 = _make_upgrade("u1", bonus_type="cargo_bonus", bonus_value=20.0)
        u2 = _make_upgrade("u2", bonus_type="cargo_bonus", bonus_value=10.0)
        mgr.install(u1)
        mgr.install(u2)
        mgr.enhance("u1", mark=2)
        # u1 at Mk2 (25.0) + u2 at Mk1 (10.0) = 35.0
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(35.0)


# ============================================================================
# Enhancement Method
# ============================================================================


class TestEnhanceMethod:
    """Tests for ShipUpgradeManager.enhance()."""

    def test_enhance_mk1_to_mk2(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade())
        success, msg = mgr.enhance("test_upgrade", mark=2)
        assert success
        assert "Mk2" in msg or "mk2" in msg.lower() or "enhanced" in msg.lower()

    def test_enhance_mk2_to_mk3(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade())
        mgr.enhance("test_upgrade", mark=2)
        success, msg = mgr.enhance("test_upgrade", mark=3)
        assert success

    def test_cannot_skip_marks(self) -> None:
        """Cannot jump from Mk1 directly to Mk3."""
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade())
        success, msg = mgr.enhance("test_upgrade", mark=3)
        assert not success

    def test_cannot_enhance_past_max(self) -> None:
        """Cannot enhance beyond max_mark."""
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade(max_mark=2))
        mgr.enhance("test_upgrade", mark=2)
        success, msg = mgr.enhance("test_upgrade", mark=3)
        assert not success

    def test_cannot_enhance_uninstalled(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        success, msg = mgr.enhance("nonexistent", mark=2)
        assert not success

    def test_enhance_already_at_mark(self) -> None:
        """Cannot enhance to the current mark level."""
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade())
        mgr.enhance("test_upgrade", mark=2)
        success, msg = mgr.enhance("test_upgrade", mark=2)
        assert not success


# ============================================================================
# Tuning System
# ============================================================================


class TestTuningSystem:
    """Tests for tuning specialization at Mk2."""

    def test_set_tuning_at_mk2(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        mgr.install(upgrade)
        success, msg = mgr.enhance("test_upgrade", mark=2, tuning="reinforced")
        assert success

    def test_tuning_adds_secondary_bonus(self) -> None:
        """Tuning should add a bonus of the tuning's type."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(
            bonus_type="cargo_bonus", bonus_value=20.0, tuning_options=SAMPLE_TUNINGS
        )
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="reinforced")
        # Base cargo bonus at Mk2: 20 * 1.25 = 25
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(25.0)
        # Tuning adds hull_bonus: 10.0 at Mk2
        assert mgr.get_bonus("hull_bonus") == pytest.approx(10.0)

    def test_tuning_doubles_at_mk3(self) -> None:
        """Tuning bonus should double when going from Mk2 to Mk3."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(
            bonus_type="cargo_bonus", bonus_value=20.0, tuning_options=SAMPLE_TUNINGS
        )
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="reinforced")
        mgr.enhance("test_upgrade", mark=3)
        # Base cargo at Mk3: 20 * 1.5 = 30
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(30.0)
        # Tuning hull_bonus doubles: 10.0 * 2 = 20.0
        assert mgr.get_bonus("hull_bonus") == pytest.approx(20.0)

    def test_different_tuning_choice(self) -> None:
        """Choosing 'optimized' adds cargo_bonus (stacks with base)."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(
            bonus_type="cargo_bonus", bonus_value=20.0, tuning_options=SAMPLE_TUNINGS
        )
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="optimized")
        # Base Mk2: 25 + tuning cargo_bonus: 5 = 30
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(30.0)

    def test_invalid_tuning_rejected(self) -> None:
        """Cannot set a tuning ID that isn't in the upgrade's options."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        mgr.install(upgrade)
        success, msg = mgr.enhance("test_upgrade", mark=2, tuning="nonexistent")
        assert not success

    def test_tuning_optional_if_no_options(self) -> None:
        """Upgrade with no tuning_options can enhance without tuning."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(tuning_options=[])
        mgr.install(upgrade)
        success, msg = mgr.enhance("test_upgrade", mark=2)
        assert success

    def test_mk3_preserves_mk2_tuning(self) -> None:
        """Mk3 enhancement doesn't need tuning param — it keeps Mk2 choice."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="reinforced")
        success, msg = mgr.enhance("test_upgrade", mark=3)
        assert success
        # Tuning is still reinforced
        inst = mgr.get_installed("test_upgrade")
        assert inst is not None
        assert inst.tuning == "reinforced"


# ============================================================================
# ShipUpgrade New Fields
# ============================================================================


class TestShipUpgradeNewFields:
    """Tests for faction/quest gate fields on ShipUpgrade."""

    def test_default_no_gates(self) -> None:
        upgrade = _make_upgrade()
        assert upgrade.faction_required is None
        assert upgrade.faction_rep_required == 0
        assert upgrade.unlock_condition is None
        assert upgrade.max_mark == 3

    def test_faction_gated_upgrade(self) -> None:
        upgrade = _make_upgrade(
            faction_required="nexus_trade", faction_rep_required=20
        )
        assert upgrade.faction_required == "nexus_trade"
        assert upgrade.faction_rep_required == 20

    def test_quest_gated_upgrade(self) -> None:
        upgrade = _make_upgrade(unlock_condition="quest_axiom_defense")
        assert upgrade.unlock_condition == "quest_axiom_defense"

    def test_max_mark_override(self) -> None:
        upgrade = _make_upgrade(max_mark=2)
        assert upgrade.max_mark == 2


# ============================================================================
# Serialization with Enhancement State
# ============================================================================


class TestEnhancementSerialization:
    """Tests for save/load with mark and tuning data."""

    def test_to_dict_includes_enhancement(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="reinforced")

        data = mgr.to_dict()
        assert "installed" in data
        entry = data["installed"][0]
        assert entry["upgrade_id"] == "test_upgrade"
        assert entry["mark"] == 2
        assert entry["tuning"] == "reinforced"

    def test_from_dict_restores_enhancement(self) -> None:
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        all_upgrades = {"test_upgrade": upgrade}

        data = {
            "weapon_slots": 0,
            "defense_slots": 0,
            "utility_slots": 3,
            "installed": [
                {"upgrade_id": "test_upgrade", "mark": 2, "tuning": "reinforced"}
            ],
        }
        mgr = ShipUpgradeManager.from_dict(data, all_upgrades)
        assert mgr.slots_used == 1
        # Mk2 bonus: 20 * 1.25 = 25
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(25.0)
        # Tuning bonus
        assert mgr.get_bonus("hull_bonus") == pytest.approx(10.0)

    def test_backward_compat_old_format(self) -> None:
        """Old save format with installed_ids (no mark/tuning) should load as Mk1."""
        upgrade = _make_upgrade()
        all_upgrades = {"test_upgrade": upgrade}

        data = {
            "max_slots": 3,
            "installed_ids": ["test_upgrade"],
        }
        mgr = ShipUpgradeManager.from_dict(data, all_upgrades)
        assert mgr.slots_used == 1
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(20.0)
        inst = mgr.get_installed("test_upgrade")
        assert inst is not None
        assert inst.mark == 1
        assert inst.tuning is None

    def test_roundtrip(self) -> None:
        upgrade = _make_upgrade(tuning_options=SAMPLE_TUNINGS)
        all_upgrades = {"test_upgrade": upgrade}

        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2, tuning="optimized")

        data = mgr.to_dict()
        restored = ShipUpgradeManager.from_dict(data, all_upgrades)

        assert restored.get_bonus("cargo_bonus") == mgr.get_bonus("cargo_bonus")
        inst = restored.get_installed("test_upgrade")
        assert inst is not None
        assert inst.mark == 2
        assert inst.tuning == "optimized"


# ============================================================================
# Uninstall resets enhancement
# ============================================================================


class TestUninstallEnhanced:
    """Uninstalling an enhanced upgrade loses enhancement state."""

    def test_uninstall_enhanced_upgrade(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade()
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2)
        success, msg = mgr.uninstall("test_upgrade")
        assert success
        assert mgr.slots_used == 0
        assert mgr.get_bonus("cargo_bonus") == 0.0

    def test_reinstall_starts_at_mk1(self) -> None:
        """Reinstalling after uninstall resets to Mk1."""
        mgr = ShipUpgradeManager(utility_slots=3)
        upgrade = _make_upgrade()
        mgr.install(upgrade)
        mgr.enhance("test_upgrade", mark=2)
        mgr.uninstall("test_upgrade")
        mgr.install(upgrade)
        assert mgr.get_bonus("cargo_bonus") == pytest.approx(20.0)  # Mk1


# ============================================================================
# get_installed helper
# ============================================================================


class TestGetInstalled:
    """Tests for the get_installed() convenience method."""

    def test_get_installed_exists(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        mgr.install(_make_upgrade())
        inst = mgr.get_installed("test_upgrade")
        assert inst is not None
        assert inst.upgrade_id == "test_upgrade"

    def test_get_installed_missing(self) -> None:
        mgr = ShipUpgradeManager(utility_slots=3)
        assert mgr.get_installed("nonexistent") is None
