"""
Tests for the B5 energy-economy helper.

Covers the pure-logic computation the builder widget relies on:
- Weapon tier classification
- EnergyEconomy fields (pool, regen, tier counts, alpha cost, sustain)
- Advisory triggers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spacegame.models.energy_economy import (
    EnergyEconomy,
    WeaponTier,
    classify_weapon,
    compute_energy_economy,
)

# ============================================================================
# Lightweight fakes for build / parts / slot_defs
# ============================================================================


@dataclass
class _FakeSlotDef:
    slot_type: str = "weapon"


@dataclass
class _FakePart:
    id: str
    slot_type: str = "weapon"
    combat_move: dict | None = None


@dataclass
class _FakePlacedSlot:
    slot_def_id: str = "weapon_slot"
    equipped_part_id: str | None = None


@dataclass
class _FakeComputedStats:
    energy_pool: int = 0
    energy_regen: int = 0


@dataclass
class _FakeBuild:
    placed_slots: list[_FakePlacedSlot] = field(default_factory=list)
    modules: list[Any] = field(default_factory=list)
    computed_stats: _FakeComputedStats | None = None


@dataclass
class _FakeDataLoader:
    ship_parts: dict[str, _FakePart] = field(default_factory=dict)
    slot_definitions: dict[str, _FakeSlotDef] = field(default_factory=dict)


def _weapon(
    part_id: str, damage: float, energy: int, cooldown: int
) -> _FakePart:
    return _FakePart(
        id=part_id,
        slot_type="weapon",
        combat_move={
            "id": part_id,
            "name": part_id,
            "effects": [{"type": "damage", "value": damage}],
            "energy_cost": energy,
            "cooldown": cooldown,
        },
    )


def _build(
    weapons: list[_FakePart],
    pool: int,
    regen: int,
) -> tuple[_FakeBuild, _FakeDataLoader]:
    parts_catalog = {w.id: w for w in weapons}
    slot_defs = {"weapon_slot": _FakeSlotDef(slot_type="weapon")}
    dl = _FakeDataLoader(ship_parts=parts_catalog, slot_definitions=slot_defs)

    placed = [
        _FakePlacedSlot(slot_def_id="weapon_slot", equipped_part_id=w.id)
        for w in weapons
    ]
    build = _FakeBuild(
        placed_slots=placed,
        modules=[],
        computed_stats=_FakeComputedStats(energy_pool=pool, energy_regen=regen),
    )
    return build, dl


# ============================================================================
# Tier classification
# ============================================================================


class TestClassifyWeapon:
    def test_classifies_sidearm(self) -> None:
        move = {"energy_cost": 2, "cooldown": 0}
        assert classify_weapon(move) is WeaponTier.SIDEARM

    def test_classifies_tech_cd1(self) -> None:
        assert classify_weapon({"energy_cost": 3, "cooldown": 1}) is WeaponTier.TECH

    def test_classifies_tech_cd2_eng5(self) -> None:
        assert classify_weapon({"energy_cost": 5, "cooldown": 2}) is WeaponTier.TECH

    def test_classifies_burst_low_end(self) -> None:
        assert classify_weapon({"energy_cost": 5, "cooldown": 3}) is WeaponTier.BURST

    def test_classifies_burst_high_end(self) -> None:
        assert classify_weapon({"energy_cost": 8, "cooldown": 4}) is WeaponTier.BURST

    def test_off_band_returns_unknown(self) -> None:
        # cd 0 but eng 3 — doesn't fit any tier
        assert classify_weapon({"energy_cost": 3, "cooldown": 0}) is WeaponTier.UNKNOWN
        # cd 5 — beyond burst
        assert classify_weapon({"energy_cost": 8, "cooldown": 5}) is WeaponTier.UNKNOWN
        # no-cost/no-cd free move
        assert classify_weapon({"energy_cost": 0, "cooldown": 0}) is WeaponTier.UNKNOWN


# ============================================================================
# compute_energy_economy — pool/regen wiring
# ============================================================================


class TestEnergyEconomyBasics:
    def test_empty_build_has_zero_everything(self) -> None:
        build, dl = _build([], pool=0, regen=0)
        eco = compute_energy_economy(build, dl)
        assert eco.pool == 0
        assert eco.regen == 0
        assert eco.total_weapons == 0
        assert eco.total_alpha_cost == 0

    def test_reads_pool_and_regen_from_computed_stats(self) -> None:
        build, dl = _build([], pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.pool == 18
        assert eco.regen == 5


# ============================================================================
# Tier counting from equipped weapons
# ============================================================================


class TestTierCounting:
    def test_counts_sidearms(self) -> None:
        weapons = [
            _weapon("s1", 12, 2, 0),
            _weapon("s2", 15, 2, 0),
        ]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.sidearm_count == 2
        assert eco.tech_count == 0
        assert eco.burst_count == 0
        assert eco.total_weapons == 2

    def test_counts_mixed_loadout(self) -> None:
        weapons = [
            _weapon("laser", 18, 2, 0),
            _weapon("missile", 30, 4, 2),
            _weapon("nova", 60, 8, 3),
        ]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.sidearm_count == 1
        assert eco.tech_count == 1
        assert eco.burst_count == 1
        assert eco.total_alpha_cost == 14  # 2 + 4 + 8
        assert eco.min_weapon_cost == 2

    def test_counts_unknown_weapons(self) -> None:
        # Weapon with cd=0 but eng=3 doesn't fit T1 or T2.
        weapons = [_weapon("weird", 15, 3, 0)]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.unknown_count == 1

    def test_skips_empty_slots(self) -> None:
        dl = _FakeDataLoader(
            ship_parts={},
            slot_definitions={"weapon_slot": _FakeSlotDef("weapon")},
        )
        build = _FakeBuild(
            placed_slots=[_FakePlacedSlot(equipped_part_id=None)],
            computed_stats=_FakeComputedStats(energy_pool=10, energy_regen=3),
        )
        eco = compute_energy_economy(build, dl)
        assert eco.total_weapons == 0


# ============================================================================
# Derived capacity math
# ============================================================================


class TestDerivedCapacities:
    def test_sustain_capacity_is_regen_div_two(self) -> None:
        _, _ = _build([], pool=0, regen=0)
        for regen, expected in [(0, 0), (2, 1), (4, 2), (5, 2), (8, 4)]:
            build, dl = _build([_weapon("s", 10, 2, 0)], pool=18, regen=regen)
            eco = compute_energy_economy(build, dl)
            assert eco.sustain_capacity == expected, f"regen={regen}"

    def test_can_alpha_strike_true_when_pool_covers_cost(self) -> None:
        weapons = [_weapon("s", 10, 2, 0), _weapon("t", 25, 4, 2)]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.can_alpha_strike is True

    def test_can_alpha_strike_false_when_pool_too_small(self) -> None:
        weapons = [
            _weapon("b1", 50, 8, 3),
            _weapon("b2", 50, 8, 3),
            _weapon("b3", 50, 8, 3),
        ]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert eco.total_alpha_cost == 24
        assert eco.can_alpha_strike is False

    def test_can_sustain_sidearm_threshold(self) -> None:
        # regen 2 = one sidearm/turn exactly
        build, dl = _build([_weapon("s", 10, 2, 0)], pool=18, regen=2)
        assert compute_energy_economy(build, dl).can_sustain_sidearm is True
        # regen 1 = can't
        build, dl = _build([_weapon("s", 10, 2, 0)], pool=18, regen=1)
        assert compute_energy_economy(build, dl).can_sustain_sidearm is False


# ============================================================================
# Advisory triggers
# ============================================================================


class TestAdvisories:
    def test_no_weapons_advisory(self) -> None:
        build, dl = _build([], pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert any("No weapons equipped" in a for a in eco.advisories)

    def test_no_sidearm_advisory(self) -> None:
        weapons = [_weapon("t", 25, 4, 2), _weapon("b", 50, 8, 3)]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert any("No sidearm" in a for a in eco.advisories)

    def test_no_burst_advisory(self) -> None:
        weapons = [_weapon("s", 10, 2, 0), _weapon("t", 25, 4, 2)]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert any("No burst" in a for a in eco.advisories)

    def test_alpha_strike_blocked_advisory(self) -> None:
        # Three bursts cost 24, pool only 18 → cannot alpha strike.
        weapons = [
            _weapon("b1", 50, 8, 3),
            _weapon("b2", 50, 8, 3),
            _weapon("b3", 50, 8, 3),
        ]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert any("full alpha strike" in a.lower() for a in eco.advisories)

    def test_regen_below_cheapest_weapon_advisory(self) -> None:
        # Cheapest weapon costs 2, regen is 1 — sustain will drain.
        weapons = [_weapon("s", 10, 2, 0)]
        build, dl = _build(weapons, pool=18, regen=1)
        eco = compute_energy_economy(build, dl)
        assert any("below cheapest" in a.lower() for a in eco.advisories)

    def test_unknown_weapon_advisory(self) -> None:
        weapons = [_weapon("weird", 15, 3, 0)]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        assert any("outside tier bands" in a for a in eco.advisories)

    def test_balanced_loadout_has_minimal_advisories(self) -> None:
        """A standard sidearm + tech + burst loadout with standard reactor
        should trigger no advisories."""
        weapons = [
            _weapon("s", 15, 2, 0),
            _weapon("t", 28, 4, 2),
            _weapon("b", 50, 6, 3),
        ]
        build, dl = _build(weapons, pool=18, regen=5)
        eco = compute_energy_economy(build, dl)
        # Allow zero advisories for a balanced standard loadout.
        assert eco.advisories == [], (
            f"Balanced loadout should not trigger advisories, got: {eco.advisories}"
        )


# ============================================================================
# Public EnergyEconomy dataclass shape
# ============================================================================


class TestEnergyEconomyDataclass:
    def test_defaults_are_zero(self) -> None:
        eco = EnergyEconomy()
        assert eco.pool == 0
        assert eco.total_weapons == 0
        assert eco.advisories == []

    def test_total_weapons_sums_all_tiers(self) -> None:
        eco = EnergyEconomy(
            sidearm_count=2,
            tech_count=1,
            burst_count=1,
            unknown_count=1,
        )
        assert eco.total_weapons == 5
