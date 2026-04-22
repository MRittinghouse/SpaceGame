"""
Tier-distribution and turn-pacing tests for Phase B4 weapon revamp.

These tests encode the design-doc §2.3 tier structure and §2.5 turn-pacing
targets. They catch drift if anyone edits a weapon to values that no
longer fit its tier band, and they guard the overall 40/40/20 catalog
distribution.

Tier bands:
  T1 Sidearm: cooldown 0,     energy 2,   damage 10-18
  T2 Tech:    cooldown 1-2,   energy 3-5, damage 20-35
  T3 Burst:   cooldown 3-4,   energy 5-8, damage 40-60

Each weapon's combat_move lives in data/ships/parts.json (active path)
and a mirror in data/ships/upgrades.json (legacy fallback). Both must
agree per-weapon on tier-relevant numbers.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PARTS_PATH = PROJECT_ROOT / "data" / "ships" / "parts.json"
UPGRADES_PATH = PROJECT_ROOT / "data" / "ships" / "upgrades.json"


# ============================================================================
# Tier roster — single source of truth for test assertions.
# Keep in sync with requirements/combat_balance_design.md §2.3.
# ============================================================================

T1_SIDEARM_IDS = {
    "salvaged_pulse_emitter",
    "mining_laser_retrofit",
    "autocannon",
    "slug_thrower",
    "plasma_caster",
    "emp_pulse_emitter",
    "ion_disruptor_weapon",
    "frost_projector",
    "voltaic_pulse",
    "capacitor_dump_array",
    "flak_battery",
    "laser_cannon",
}

T2_TECH_IDS = {
    "ion_disruptor",
    "dual_laser",
    "railgun_accelerator",
    "arc_emitter_weapon",
    "glacial_beam",
    "storm_emitter",
    "inferno_lance",
    "missile_launcher",
    "absolute_zero_array",
    "tempest_cannon",
    "rail_gun",
    "mass_driver_mk3",
    "solar_flare_cannon",
    "cascade_ionizer",
}

T3_BURST_IDS = {
    "arc_emitter",
    "broadside_battery",
    "plasma_conduit",
    "plasma_torpedo",
    "nova_core",
    "nova_burst_cannon",
}

ALL_TIERED_IDS = T1_SIDEARM_IDS | T2_TECH_IDS | T3_BURST_IDS


# ============================================================================
# Helpers
# ============================================================================


def _load_weapons(path: Path) -> dict[str, dict]:
    with open(path) as f:
        data = json.load(f)
    arr = data.get("parts") or data.get("upgrades") or data
    return {
        p["id"]: p
        for p in arr
        if p.get("slot_type") == "weapon" and p.get("combat_move")
    }


def _move_stats(weapon: dict) -> tuple[float, int, int]:
    cm = weapon["combat_move"]
    dmg = float(cm["effects"][0].get("value", 0)) if cm.get("effects") else 0.0
    return dmg, int(cm.get("energy_cost", 0)), int(cm.get("cooldown", 0))


@pytest.fixture(scope="module")
def parts_weapons() -> dict:
    return _load_weapons(PARTS_PATH)


@pytest.fixture(scope="module")
def upgrades_weapons() -> dict:
    return _load_weapons(UPGRADES_PATH)


# ============================================================================
# Bucket 1: Roster integrity
# ============================================================================


class TestRosterIntegrity:
    def test_exactly_32_weapons(self, parts_weapons: dict) -> None:
        assert len(parts_weapons) == 32

    def test_every_weapon_is_tiered(self, parts_weapons: dict) -> None:
        untiered = set(parts_weapons.keys()) - ALL_TIERED_IDS
        assert not untiered, (
            f"Weapons without tier assignment: {untiered}. "
            f"Update ALL_TIERED_IDS in this test file AND its tier band."
        )

    def test_tier_rosters_disjoint(self) -> None:
        assert not (T1_SIDEARM_IDS & T2_TECH_IDS)
        assert not (T2_TECH_IDS & T3_BURST_IDS)
        assert not (T1_SIDEARM_IDS & T3_BURST_IDS)

    def test_no_unknown_tiered_ids(self, parts_weapons: dict) -> None:
        """Every ID in the tier rosters must exist in the data."""
        missing = ALL_TIERED_IDS - set(parts_weapons.keys())
        assert not missing, f"Tier rosters reference missing weapons: {missing}"


# ============================================================================
# Bucket 2: Tier distribution (40/40/20)
# ============================================================================


class TestTierDistribution:
    """Catalog distribution should approximate 40% sidearm / 40% tech /
    20% burst. Rigid percentages cause brittleness; aim for design intent."""

    def test_t1_at_least_one_third(self) -> None:
        ratio = len(T1_SIDEARM_IDS) / 32
        assert ratio >= 0.30, f"T1 Sidearm ratio {ratio:.2f} too low (target ~0.40)"

    def test_t2_at_least_one_third(self) -> None:
        ratio = len(T2_TECH_IDS) / 32
        assert ratio >= 0.30, f"T2 Tech ratio {ratio:.2f} too low (target ~0.40)"

    def test_t3_at_most_one_fourth(self) -> None:
        ratio = len(T3_BURST_IDS) / 32
        assert ratio <= 0.25, f"T3 Burst ratio {ratio:.2f} too high (target ~0.20)"

    def test_t3_at_least_one_tenth(self) -> None:
        ratio = len(T3_BURST_IDS) / 32
        assert ratio >= 0.10, f"T3 Burst ratio {ratio:.2f} too low — burst fantasy matters"


# ============================================================================
# Bucket 3: Tier band enforcement
# ============================================================================


class TestT1SidearmBand:
    """T1 Sidearm: 0 cd, 2 E, 10-18 dmg."""

    def test_all_t1_weapons_match_band(self, parts_weapons: dict) -> None:
        for wid in T1_SIDEARM_IDS:
            dmg, eng, cd = _move_stats(parts_weapons[wid])
            assert cd == 0, f"{wid} T1 cooldown {cd} != 0"
            assert eng == 2, f"{wid} T1 energy {eng} != 2"
            assert 10 <= dmg <= 18, f"{wid} T1 damage {dmg} outside 10-18"


class TestT2TechBand:
    """T2 Tech: 1-2 cd, 3-5 E, 20-35 dmg."""

    def test_all_t2_weapons_match_band(self, parts_weapons: dict) -> None:
        for wid in T2_TECH_IDS:
            dmg, eng, cd = _move_stats(parts_weapons[wid])
            assert 1 <= cd <= 2, f"{wid} T2 cooldown {cd} outside 1-2"
            assert 3 <= eng <= 5, f"{wid} T2 energy {eng} outside 3-5"
            assert 20 <= dmg <= 35, f"{wid} T2 damage {dmg} outside 20-35"


class TestT3BurstBand:
    """T3 Burst: 3-4 cd, 5-8 E, 40-60 dmg."""

    def test_all_t3_weapons_match_band(self, parts_weapons: dict) -> None:
        for wid in T3_BURST_IDS:
            dmg, eng, cd = _move_stats(parts_weapons[wid])
            assert 3 <= cd <= 4, f"{wid} T3 cooldown {cd} outside 3-4"
            assert 5 <= eng <= 8, f"{wid} T3 energy {eng} outside 5-8"
            assert 40 <= dmg <= 60, f"{wid} T3 damage {dmg} outside 40-60"


# ============================================================================
# Bucket 4: Monotonicity — tier damage progression
# ============================================================================


class TestTierMonotonicity:
    """Average damage must rise strictly across tiers."""

    def test_tier_damage_averages_rise(self, parts_weapons: dict) -> None:
        def avg_dmg(ids: set[str]) -> float:
            total = sum(_move_stats(parts_weapons[wid])[0] for wid in ids)
            return total / len(ids)

        t1_avg = avg_dmg(T1_SIDEARM_IDS)
        t2_avg = avg_dmg(T2_TECH_IDS)
        t3_avg = avg_dmg(T3_BURST_IDS)

        assert t1_avg < t2_avg < t3_avg, (
            f"Tier damage averages must rise: T1={t1_avg:.1f}, "
            f"T2={t2_avg:.1f}, T3={t3_avg:.1f}"
        )

    def test_tier_damage_per_energy_rises_with_tier(self, parts_weapons: dict) -> None:
        """Burst weapons have better damage-per-energy at the cost of
        cooldown. Investment in cooldown management pays back."""
        def avg_dpe(ids: set[str]) -> float:
            total = 0.0
            for wid in ids:
                dmg, eng, _ = _move_stats(parts_weapons[wid])
                total += dmg / max(eng, 1)
            return total / len(ids)

        t1_dpe = avg_dpe(T1_SIDEARM_IDS)
        t3_dpe = avg_dpe(T3_BURST_IDS)
        assert t3_dpe > t1_dpe, (
            f"T3 damage-per-energy {t3_dpe:.1f} should exceed T1 {t1_dpe:.1f}"
        )


# ============================================================================
# Bucket 5: Elemental diversity
# ============================================================================


class TestElementalDiversity:
    """Each of the 5 elements (kinetic, plasma, ion, cryo, voltaic) has at
    least one representative across the catalog. Generic / no-element
    weapons still exist but element variety must not collapse."""

    def test_each_element_has_at_least_one_weapon(self, parts_weapons: dict) -> None:
        elements_seen = set()
        for w in parts_weapons.values():
            elem = w["combat_move"].get("element")
            if elem:
                elements_seen.add(elem)
        expected = {"kinetic", "plasma", "ion", "cryo", "voltaic"}
        missing = expected - elements_seen
        assert not missing, f"Elements missing from catalog: {missing}"


# ============================================================================
# Bucket 6: Parts / upgrades parity
# ============================================================================


class TestPartsUpgradesParity:
    """parts.json (active combat path) and upgrades.json (legacy fallback)
    must carry matching weapon numbers — no drift between them."""

    def test_same_weapon_ids_in_both_files(
        self, parts_weapons: dict, upgrades_weapons: dict
    ) -> None:
        assert set(parts_weapons.keys()) == set(upgrades_weapons.keys()), (
            "parts.json and upgrades.json diverge on which weapons exist"
        )

    def test_damage_energy_cooldown_match(
        self, parts_weapons: dict, upgrades_weapons: dict
    ) -> None:
        for wid in parts_weapons:
            p_dmg, p_eng, p_cd = _move_stats(parts_weapons[wid])
            u_dmg, u_eng, u_cd = _move_stats(upgrades_weapons[wid])
            assert p_dmg == u_dmg, f"{wid}: parts dmg {p_dmg} != upgrades dmg {u_dmg}"
            assert p_eng == u_eng, f"{wid}: parts eng {p_eng} != upgrades eng {u_eng}"
            assert p_cd == u_cd, f"{wid}: parts cd {p_cd} != upgrades cd {u_cd}"


# ============================================================================
# Bucket 7: Turn pacing — design doc §2.5 integration check
# ============================================================================


class TestTurnPacingAgainstDesignDoc:
    """§2.5 example: Standard reactor (18 pool, 5 regen), mixed loadout of
    one sidearm + one tech + one burst. 5-turn total ~280 damage."""

    def test_representative_loadout_matches_turn1_target(
        self, parts_weapons: dict
    ) -> None:
        """Turn 1 alpha strike: Burst + Tech + Sidearm all fire.
        Expected ~90 damage per §2.5."""
        # Pick representative medians of each tier.
        sidearm = parts_weapons["laser_cannon"]       # T1 ceiling
        tech = parts_weapons["missile_launcher"]       # T2 mid
        burst = parts_weapons["plasma_torpedo"]        # T3 mid

        s_dmg, s_eng, _ = _move_stats(sidearm)
        t_dmg, t_eng, _ = _move_stats(tech)
        b_dmg, b_eng, _ = _move_stats(burst)

        total_eng = s_eng + t_eng + b_eng
        total_dmg = s_dmg + t_dmg + b_dmg

        assert total_eng <= 18, (
            f"Turn 1 alpha strike energy {total_eng} exceeds Standard reactor pool 18"
        )
        assert 75 <= total_dmg <= 110, (
            f"Turn 1 total damage {total_dmg} outside design-doc §2.5 target ~90"
        )

    def test_sidearm_sustainable_with_standard_regen(
        self, parts_weapons: dict
    ) -> None:
        """Every T1 sidearm costs at most 2E. With regen 5, two sidearms
        (4E) sustain forever. If a sidearm creeps above 2E, sustain breaks."""
        for wid in T1_SIDEARM_IDS:
            _, eng, _ = _move_stats(parts_weapons[wid])
            assert eng <= 2, (
                f"{wid} sidearm energy {eng} > 2 — breaks sustain math in §2.5"
            )

    def test_no_weapon_costs_more_than_standard_pool(
        self, parts_weapons: dict
    ) -> None:
        """No single weapon should exceed Standard reactor pool (18E).
        Otherwise players with Standard reactor can't alpha-strike at all."""
        for wid, w in parts_weapons.items():
            _, eng, _ = _move_stats(w)
            assert eng <= 18, f"{wid} energy {eng} exceeds Standard pool 18"
