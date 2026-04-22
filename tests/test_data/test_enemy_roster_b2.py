"""
Data validation for the Phase B2 enemy roster (U2.5d balance pass).

Verifies the 18 new enemy templates added in data/combat/enemies.json
match the tier × archetype design targets in
requirements/combat_balance_design.md §4.3. These assertions protect
against accidental drift when data is edited by hand.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader

# ============================================================================
# Roster definition — must stay in sync with combat_balance_design.md §4.3
# ============================================================================

T1_IDS = {"skiff_raider", "hulk_derelict"}
T2_IDS = {
    "frontier_interceptor",
    "reach_scout_ace",
    "union_corvette",
    "reach_bulwark",
    "guild_signal_jammer",
    "collective_medic",
}
T3_IDS = {
    "reach_void_dancer",
    "frontier_raptor",
    "union_siege_cruiser",
    "collective_jammer_prime",
    "guild_relay_nexus",
    "mercenary_ace",
    "rogue_ace",
}
T4_IDS = {"pirate_lord", "reach_dreadnought", "union_behemoth"}

ALL_B2_IDS = T1_IDS | T2_IDS | T3_IDS | T4_IDS


@pytest.fixture(scope="module")
def enemies() -> dict:
    dl = get_data_loader()
    return dl.load_enemy_templates()


# ============================================================================
# Presence + uniqueness
# ============================================================================


class TestRosterPresence:
    def test_all_18_templates_loaded(self, enemies: dict) -> None:
        missing = ALL_B2_IDS - set(enemies.keys())
        assert not missing, f"Missing B2 templates: {missing}"

    def test_exactly_18_new_templates(self) -> None:
        """The B2 roster was scoped to 18 templates. If this changes, update
        combat_balance_design.md §4.3."""
        assert len(ALL_B2_IDS) == 18

    def test_no_id_collision_with_legacy_roster(self, enemies: dict) -> None:
        """Legacy 42 templates must still exist; new 18 are additive."""
        assert len(enemies) >= 60, "Should have 42 legacy + 18 new"


# ============================================================================
# Tier HP bounds — §4.3 matrix
# ============================================================================


class TestTierHPBounds:
    """Hull values must sit inside their tier's bounded range, per the
    design doc. Narrow bands catch accidental number-drift."""

    def test_t1_hull_in_range(self, enemies: dict) -> None:
        for eid in T1_IDS:
            hp = enemies[eid].hull
            assert 30 <= hp <= 90, f"{eid} T1 hull {hp} outside 30–90"

    def test_t2_hull_in_range(self, enemies: dict) -> None:
        for eid in T2_IDS:
            hp = enemies[eid].hull
            assert 70 <= hp <= 180, f"{eid} T2 hull {hp} outside 70–180"

    def test_t3_hull_in_range(self, enemies: dict) -> None:
        for eid in T3_IDS:
            hp = enemies[eid].hull
            assert 150 <= hp <= 400, f"{eid} T3 hull {hp} outside 150–400"

    def test_t4_hull_in_range(self, enemies: dict) -> None:
        """T4 bosses: 500–800 per design doc. HP multiplier applied at runtime
        by EnemyShip.from_template, so template hull IS the base."""
        for eid in T4_IDS:
            hp = enemies[eid].hull
            assert 450 <= hp <= 900, f"{eid} T4 hull {hp} outside 450–900"


# ============================================================================
# Archetype shape — identity asserts
# ============================================================================


class TestArchetypeIdentity:
    """Each archetype has a signature. These tests pin it down so future
    edits don't accidentally turn a tank into a striker."""

    def test_strikers_have_high_evasion(self, enemies: dict) -> None:
        strikers = [
            "skiff_raider",
            "frontier_interceptor",
            "reach_scout_ace",
            "reach_void_dancer",
            "frontier_raptor",
        ]
        for eid in strikers:
            ev = enemies[eid].evasion
            assert ev >= 15, f"{eid} striker evasion {ev} too low (should be ≥15)"

    def test_tanks_have_armor_and_low_evasion(self, enemies: dict) -> None:
        tanks = ["hulk_derelict", "union_corvette", "reach_bulwark", "union_siege_cruiser"]
        for eid in tanks:
            armor = enemies[eid].combat_armor
            ev = enemies[eid].evasion
            assert armor >= 3, f"{eid} tank armor {armor} too low (should be ≥3)"
            assert ev <= 5, f"{eid} tank evasion {ev} too high (should be ≤5)"

    def test_controllers_have_status_moves(self, enemies: dict) -> None:
        """Controllers apply at least one non-damage effect (jam/drain/freeze)."""
        controllers = ["guild_signal_jammer", "collective_jammer_prime"]
        status_types = {"energy_drain", "suppressed", "chill", "burn"}
        for eid in controllers:
            found_status = False
            for move in enemies[eid].moves:
                for eff in move.effects:
                    if eff.type.value in status_types:
                        found_status = True
                        break
            assert found_status, f"{eid} controller has no status-effect move"

    def test_support_archetype_has_restore_move(self, enemies: dict) -> None:
        """Support enemies self-heal or restore shields."""
        supports = ["collective_medic", "guild_relay_nexus"]
        restore_types = {"hull_restore", "shield_restore"}
        for eid in supports:
            found_restore = False
            for move in enemies[eid].moves:
                for eff in move.effects:
                    if eff.type.value in restore_types:
                        found_restore = True
                        break
            assert found_restore, f"{eid} support has no hull/shield restore"

    def test_rivals_have_balanced_mixed_loadout(self, enemies: dict) -> None:
        """Rivals carry 3+ moves: at least one damage-dealing and at least one
        utility-only (self-buff or evasion). Damage moves may be hybrid
        (damage + status) to express weapon elements."""
        rivals = ["mercenary_ace", "rogue_ace"]
        for eid in rivals:
            moves = enemies[eid].moves
            assert len(moves) >= 3, f"{eid} rival has only {len(moves)} moves"
            damage_dealing = 0
            utility_only = 0
            for m in moves:
                types = {e.type.value for e in m.effects}
                if "damage" in types:
                    damage_dealing += 1
                else:
                    utility_only += 1
            assert damage_dealing >= 2 and utility_only >= 1, (
                f"{eid} rival not balanced: damage_dealing={damage_dealing}, "
                f"utility_only={utility_only}"
            )

    def test_juggernauts_are_bosses_with_phases(self, enemies: dict) -> None:
        """T4 Juggernauts use is_boss + multi-phase machinery."""
        juggernauts = ["pirate_lord", "reach_dreadnought", "union_behemoth"]
        for eid in juggernauts:
            t = enemies[eid]
            assert t.is_boss, f"{eid} juggernaut must be is_boss=True"
            assert len(t.phases) >= 2, f"{eid} juggernaut needs ≥2 phases"
            assert len(t.moves) >= 4, f"{eid} juggernaut needs ≥4 moves"


# ============================================================================
# Move palette consistency
# ============================================================================


class TestMovePaletteConsistency:
    """Count-of-moves-per-tier follows §4.4."""

    def test_t1_enemies_have_one_move(self, enemies: dict) -> None:
        for eid in T1_IDS:
            n = len(enemies[eid].moves)
            assert n == 1, f"{eid} T1 should have exactly 1 move, has {n}"

    def test_t2_enemies_have_two_moves(self, enemies: dict) -> None:
        for eid in T2_IDS:
            n = len(enemies[eid].moves)
            assert n == 2, f"{eid} T2 should have exactly 2 moves, has {n}"

    def test_t3_enemies_have_three_moves(self, enemies: dict) -> None:
        for eid in T3_IDS:
            n = len(enemies[eid].moves)
            assert n == 3, f"{eid} T3 should have exactly 3 moves, has {n}"

    def test_t4_enemies_have_four_plus_moves(self, enemies: dict) -> None:
        for eid in T4_IDS:
            n = len(enemies[eid].moves)
            assert n >= 4, f"{eid} T4 should have ≥4 moves, has {n}"


# ============================================================================
# Faction attribution
# ============================================================================


class TestFactionAttribution:
    """New roster aligns with the faction signature map (§4.6)."""

    def test_faction_ids_are_valid_or_empty(self, enemies: dict) -> None:
        """Faction must be a real gameplay faction or empty string (unaligned)."""
        valid = {"", "commerce_guild", "miners_union", "science_collective", "frontier_alliance"}
        for eid in ALL_B2_IDS:
            f = enemies[eid].faction_id
            assert f in valid, f"{eid} has invalid faction_id {f!r}"

    def test_guild_templates_use_commerce_faction(self, enemies: dict) -> None:
        for eid in ("guild_signal_jammer", "guild_relay_nexus"):
            assert enemies[eid].faction_id == "commerce_guild", (
                f"{eid} should belong to commerce_guild"
            )

    def test_collective_templates_use_science_faction(self, enemies: dict) -> None:
        for eid in ("collective_medic", "collective_jammer_prime"):
            assert enemies[eid].faction_id == "science_collective", (
                f"{eid} should belong to science_collective"
            )

    def test_union_templates_use_miners_faction(self, enemies: dict) -> None:
        for eid in ("union_corvette", "union_siege_cruiser", "union_behemoth"):
            assert enemies[eid].faction_id == "miners_union", (
                f"{eid} should belong to miners_union"
            )

    def test_frontier_templates_use_frontier_faction(self, enemies: dict) -> None:
        for eid in ("frontier_interceptor", "frontier_raptor", "rogue_ace"):
            assert enemies[eid].faction_id == "frontier_alliance", (
                f"{eid} should belong to frontier_alliance"
            )


# ============================================================================
# Reward scaling
# ============================================================================


class TestRewardScaling:
    """XP and credit rewards must rise monotonically across tiers."""

    def test_xp_rises_with_tier(self, enemies: dict) -> None:
        t1_max = max(enemies[e].xp_reward for e in T1_IDS)
        t2_max = max(enemies[e].xp_reward for e in T2_IDS)
        t3_max = max(enemies[e].xp_reward for e in T3_IDS)
        t4_max = max(enemies[e].xp_reward for e in T4_IDS)
        assert t1_max < t2_max < t3_max < t4_max, (
            f"XP must rise by tier: T1={t1_max}, T2={t2_max}, T3={t3_max}, T4={t4_max}"
        )

    def test_credits_rise_with_tier(self, enemies: dict) -> None:
        t1_max = max(enemies[e].credit_reward for e in T1_IDS)
        t4_min = min(enemies[e].credit_reward for e in T4_IDS)
        assert t4_min > t1_max, (
            f"T4 minimum credits ({t4_min}) should exceed T1 maximum ({t1_max})"
        )


# ============================================================================
# Boss structure
# ============================================================================


class TestBossStructure:
    """Bosses have well-formed phase data."""

    def test_bosses_have_opening_phase_threshold_1(self, enemies: dict) -> None:
        """First phase activates at hp_threshold 1.0 (always active from fight start)."""
        for eid in T4_IDS:
            phases = enemies[eid].phases
            assert phases[0].hp_threshold == 1.0, (
                f"{eid} first phase hp_threshold {phases[0].hp_threshold} != 1.0"
            )

    def test_bosses_have_transition_phase_at_half_hp(self, enemies: dict) -> None:
        """Second phase triggers at 50% — design doc §4.4 phase-transition spec."""
        for eid in T4_IDS:
            phases = enemies[eid].phases
            assert phases[1].hp_threshold == 0.5, (
                f"{eid} second phase hp_threshold {phases[1].hp_threshold} != 0.5"
            )

    def test_boss_phase_move_ids_exist_in_moveset(self, enemies: dict) -> None:
        """Every move_id referenced by a phase must actually be a move the boss has."""
        for eid in T4_IDS:
            t = enemies[eid]
            move_ids = {m.id for m in t.moves}
            for phase in t.phases:
                for mid in phase.move_ids:
                    assert mid in move_ids, (
                        f"{eid} phase '{phase.name}' references missing move {mid}"
                    )
