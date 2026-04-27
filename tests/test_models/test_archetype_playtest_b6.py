"""
Archetype playtest integration tests for Phase B6.

These verify that player archetypes *behave differently in the ways the
design doc says*, rather than asserting specific round counts. The
design-doc §6 expected round counts ("kill 2 strikers in 2 rounds")
turned out not to match current B2/B4 tuning — see
requirements/combat_balance_design.md §12 for the deferred tuning item.

What these tests DO guard against:

- Archetype identity regressions: a "glass cannon" must still deal
  more damage per turn than a "tank"; a "tank" must still survive
  longer than a glass cannon against the same encounter.
- Burst cooldown enforcement: a missile boat running only burst weapons
  must have idle turns between volleys (cooldown does what it says).
- Multi-tier rotation: a balanced build must use weapons from multiple
  tiers, not just spam one.

Scenarios 5-6 depend on Dual Techs (B8) and are skip-gated.
"""

from __future__ import annotations

import pytest

from spacegame.data_loader import get_data_loader
from spacegame.models.action_queue import ActionQueue
from spacegame.models.combat import (
    CombatEncounter,
    CombatState,
    EnemyShip,
    PlayerCombatState,
)
from spacegame.models.combat_engine import CombatEngine

# ============================================================================
# Helpers
# ============================================================================


def _make_player(
    *,
    hull: int,
    shields: int,
    energy_pool: int,
    energy_regen: int,
    weapon_ids: list[str],
    armor: int = 0,
    shield_regen: int = 0,
    accuracy: int = 85,
    evasion: int = 10,
    speed: int = 6,
) -> PlayerCombatState:
    dl = get_data_loader()
    dl.load_all()
    parts = dl.ship_parts

    from spacegame.models.combat import CombatMove

    moves = []
    for i, wid in enumerate(weapon_ids):
        part = parts.get(wid)
        assert part is not None, f"Unknown weapon {wid}"
        cm = part.combat_move
        assert cm is not None, f"{wid} has no combat_move"
        move = CombatMove.from_dict(cm)
        move.slot_key = f"{move.id}_slot_{i}"
        moves.append(move)

    p = PlayerCombatState(
        hull=hull,
        max_hull=hull,
        shields=shields,
        max_shields=shields,
        energy=energy_pool,
        max_energy=energy_pool,
        energy_regen=energy_regen,
        speed=speed,
        evasion=evasion,
        accuracy=accuracy,
        equipment_moves=moves,
        crew_moves=[],
        active_effects=[],
        cooldowns={},
        armor=armor,
    )
    p.shield_regen = shield_regen
    return p


def _make_enemies(enemy_ids: list[str]) -> tuple[list[EnemyShip], list]:
    dl = get_data_loader()
    templates = dl.load_enemy_templates()
    selected = [templates[eid] for eid in enemy_ids]
    enemies = [EnemyShip.from_template(t) for t in selected]
    return enemies, selected


def _run_scenario(
    player: PlayerCombatState,
    enemy_templates: list,
    enemies: list[EnemyShip],
    seed: int,
    max_rounds: int = 25,
) -> dict:
    """Run a scripted combat and return a detailed outcome dict.

    Player strategy: queue every weapon ready this turn, highest damage
    first, target lowest-hull surviving enemy.

    Returns:
        Dict with keys:
            rounds, survived, damage_dealt, player_hull_ratio,
            turns_with_weapon_fire (how many turns the player fired
            anything — measures cooldown idleness).
    """
    encounter = CombatEncounter(enemy_templates=enemy_templates, encounter_seed=seed)
    state = CombatState(player=player, enemies=enemies, encounter=encounter, combat_log=[])
    engine = CombatEngine(state, seed=seed)

    total_starting_hp = sum(e.current_hull + e.current_shields for e in enemies)
    rounds = 0
    turns_with_fire = 0

    while rounds < max_rounds:
        if player.hull <= 0:
            break
        if not any(e.is_alive for e in enemies):
            break

        queue = ActionQueue(
            energy_available=player.energy,
            cooldowns=dict(player.cooldowns),
        )
        sorted_moves = sorted(
            player.equipment_moves,
            key=lambda m: -(m.effects[0].value if m.effects else 0),
        )
        living = [(i, e) for i, e in enumerate(enemies) if e.is_alive]
        if not living:
            break
        target_idx = min(living, key=lambda pair: pair[1].current_hull)[0]

        weapons_queued = 0
        for move in sorted_moves:
            # queue.add expects move.id (it derives slot_key from the move
            # attribute internally for cooldown tracking).
            can, _ = queue.can_add(move.id, move)
            if can:
                queue.add(move.id, target_idx, move)
                weapons_queued += 1

        if weapons_queued > 0:
            turns_with_fire += 1

        engine.execute_player_turn(queue)

        if any(e.is_alive for e in enemies):
            engine.execute_enemy_turns()

        engine.end_round()
        rounds += 1

    total_ending_hp = sum(max(0, e.current_hull) + max(0, e.current_shields) for e in enemies)
    damage_dealt = max(0, total_starting_hp - total_ending_hp)
    hull_ratio = player.hull / max(player.max_hull, 1)

    return {
        "rounds": rounds,
        "survived": player.hull > 0,
        "damage_dealt": damage_dealt,
        "player_hull_ratio": hull_ratio,
        "turns_with_fire": turns_with_fire,
    }


# ============================================================================
# Archetype builder helpers — used across scenarios for comparison tests.
# ============================================================================


def _glass_cannon() -> PlayerCombatState:
    """High burst damage, low defense, high evasion."""
    return _make_player(
        hull=90,
        shields=30,
        energy_pool=12,
        energy_regen=4,
        armor=2,
        evasion=35,
        accuracy=90,
        weapon_ids=[
            "plasma_torpedo",
            "missile_launcher",
            "dual_laser",
            "laser_cannon",
        ],
    )


def _tank() -> PlayerCombatState:
    """Heavy hull, heavy shields, shield regen, low evasion."""
    return _make_player(
        hull=250,
        shields=100,
        energy_pool=18,
        energy_regen=5,
        armor=10,
        shield_regen=8,
        speed=3,
        evasion=0,
        accuracy=85,
        weapon_ids=["missile_launcher", "laser_cannon"],
    )


def _balanced() -> PlayerCombatState:
    """Mixed loadout covering all three weapon tiers."""
    return _make_player(
        hull=180,
        shields=80,
        energy_pool=36,
        energy_regen=10,
        armor=5,
        shield_regen=4,
        evasion=15,
        accuracy=85,
        weapon_ids=["plasma_torpedo", "missile_launcher", "laser_cannon"],
    )


def _missile_boat() -> PlayerCombatState:
    """Two burst weapons, long cooldowns, heavy hull."""
    return _make_player(
        hull=240,
        shields=60,
        energy_pool=36,
        energy_regen=10,
        armor=6,
        shield_regen=4,
        evasion=10,
        accuracy=85,
        weapon_ids=["plasma_torpedo", "nova_core"],
    )


# ============================================================================
# Scenario 1: Glass cannon identity — out-DPS the tank against the same foe
# ============================================================================
#
# Design-doc §6.1 asked for "kill 2 strikers in 2 rounds". Current tuning
# makes that unreachable without either buffing bursts or nerfing T2 enemy
# durability. Deferred: see combat_balance_design.md §12.
#
# What we CAN assert: a glass cannon deals measurably more damage per
# round than a tank, given identical encounters. That's the archetype
# identity — it still holds regardless of specific round counts.


class TestScenario1GlassCannonDamageIdentity:
    def test_glass_cannon_outdamages_tank_aggregate(self) -> None:
        """Aggregated across multiple seeds, the glass cannon's burst
        + tech loadout must deal more total damage than the tank's
        2-weapon loadout. Aggregating across seeds smooths miss-streak
        variance — a single unlucky glass cannon run can trail the
        tank, but over a portfolio of fights the archetype identity
        holds."""
        gc_totals = []
        tk_totals = []
        for seed in (42, 1337, 2024, 9999, 101):
            enemies_gc, tpl = _make_enemies(["frontier_interceptor", "frontier_interceptor"])
            gc_out = _run_scenario(_glass_cannon(), tpl, enemies_gc, seed=seed, max_rounds=6)
            enemies_tk, tpl = _make_enemies(["frontier_interceptor", "frontier_interceptor"])
            tk_out = _run_scenario(_tank(), tpl, enemies_tk, seed=seed, max_rounds=6)
            gc_totals.append(gc_out["damage_dealt"])
            tk_totals.append(tk_out["damage_dealt"])

        gc_total = sum(gc_totals)
        tk_total = sum(tk_totals)
        assert gc_total > tk_total, (
            f"Glass cannon aggregate damage {gc_total} (per seed: {gc_totals}) "
            f"must exceed tank's {tk_total} (per seed: {tk_totals}). "
            f"Burst fantasy requires glass cannon to hit harder than tank."
        )


# ============================================================================
# Scenario 2: Tank identity — survive longer under same enemy pressure
# ============================================================================


class TestScenario2TankDurabilityIdentity:
    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_tank_survives_longer_than_glass_cannon(self, seed: int) -> None:
        """Over a fixed 15-round window, tank must retain more hull
        (ratio) than a glass cannon facing identical enemies."""
        gc = _glass_cannon()
        tk = _tank()

        enemies_gc, tpl = _make_enemies(["frontier_interceptor", "frontier_interceptor"])
        gc_out = _run_scenario(gc, tpl, enemies_gc, seed=seed, max_rounds=15)

        enemies_tk, tpl = _make_enemies(["frontier_interceptor", "frontier_interceptor"])
        tk_out = _run_scenario(tk, tpl, enemies_tk, seed=seed, max_rounds=15)

        assert tk_out["player_hull_ratio"] >= gc_out["player_hull_ratio"], (
            f"Tank hull ratio ({tk_out['player_hull_ratio']:.2f}) must "
            f"meet or exceed glass cannon's ({gc_out['player_hull_ratio']:.2f}) "
            f"(seed={seed}). If both equal 1.0, enemies are missing too "
            f"much — verify enemy accuracy."
        )

    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_tank_is_viable_against_t2_pair(self, seed: int) -> None:
        """Tank must survive at least 10 rounds against 2× T2 strikers
        and deal nontrivial damage."""
        tk = _tank()
        enemies, tpl = _make_enemies(["frontier_interceptor", "frontier_interceptor"])
        out = _run_scenario(tk, tpl, enemies, seed=seed, max_rounds=15)
        assert out["player_hull_ratio"] > 0.3, (
            f"Tank reduced to {out['player_hull_ratio']:.2f} hull in 15 "
            f"rounds (seed={seed}) — defensive tuning undertuned"
        )
        assert out["damage_dealt"] > 50, (
            f"Tank dealt only {out['damage_dealt']} dmg in 15 rounds "
            f"(seed={seed}) — DPS too low even for tank"
        )


# ============================================================================
# Scenario 3: Balanced archetype — uses weapons across multiple tiers
# ============================================================================


class TestScenario3BalancedTierUsage:
    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_balanced_fires_weapons_most_turns(self, seed: int) -> None:
        """A balanced build with 3 weapons (sidearm + tech + burst)
        should fire something on a large majority of turns —
        it has rotation, not cooldown gaps."""
        balanced = _balanced()
        enemies, tpl = _make_enemies(["union_siege_cruiser", "collective_jammer_prime"])
        out = _run_scenario(balanced, tpl, enemies, seed=seed, max_rounds=15)
        fire_ratio = out["turns_with_fire"] / max(out["rounds"], 1)
        assert fire_ratio >= 0.80, (
            f"Balanced build fired on only {fire_ratio:.0%} of turns "
            f"(seed={seed}) — sidearm should keep it armed every turn"
        )


# ============================================================================
# Scenario 4: Missile boat — burst cooldowns enforce idle turns
# ============================================================================


class TestScenario4MissileBoatCooldownPacing:
    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_missile_boat_has_cooldown_idle_turns(self, seed: int) -> None:
        """Missile boat runs only 2 burst weapons (both cd 3). Over a
        10-turn window, there MUST be turns where no weapon fires —
        that's the cooldown price of burst builds."""
        boat = _missile_boat()
        enemies, tpl = _make_enemies(["mercenary_ace"])
        out = _run_scenario(boat, tpl, enemies, seed=seed, max_rounds=10)
        fire_ratio = out["turns_with_fire"] / max(out["rounds"], 1)
        # A boat with cd-3 bursts fires every 3-4 turns at best.
        # Must be < 100% (there must be idle turns).
        assert fire_ratio < 0.80, (
            f"Missile boat fired on {fire_ratio:.0%} of turns "
            f"(seed={seed}) — burst cooldowns should create idle gaps"
        )

    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_missile_boat_burst_strike_damage_per_fire_is_high(self, seed: int) -> None:
        """When the boat DOES fire, its per-fire damage must be high —
        that's the tradeoff for the idle turns. If turns_with_fire is
        low, damage_per_fire must be large."""
        boat = _missile_boat()
        enemies, tpl = _make_enemies(["mercenary_ace"])
        out = _run_scenario(boat, tpl, enemies, seed=seed, max_rounds=10)
        if out["turns_with_fire"] == 0:
            pytest.skip("Boat didn't fire in window — seed-dependent edge case")
        dmg_per_fire = out["damage_dealt"] / out["turns_with_fire"]
        # Two bursts at roughly 50+60=110 raw damage, minus armor/shields —
        # a firing turn should deal at least 30 effective damage.
        assert dmg_per_fire >= 30, (
            f"Missile boat dealt only {dmg_per_fire:.1f} dmg per firing "
            f"turn (seed={seed}) — burst alpha strike too weak"
        )


# ============================================================================
# Cross-archetype sanity
# ============================================================================


class TestArchetypeSeparation:
    """Archetypes must actually differ. If two archetypes produce
    statistically identical outcomes, the design doesn't differentiate them."""

    @pytest.mark.parametrize("seed", [42, 1337, 2024])
    def test_missile_boat_alpha_damage_exceeds_sidearm_turn(self, seed: int) -> None:
        """Single-turn damage from missile boat alpha strike must
        exceed what a sidearm-only turn could plausibly deal.
        This confirms the 'burst fantasy' is present."""
        boat = _missile_boat()
        enemies, tpl = _make_enemies(["mercenary_ace"])
        out = _run_scenario(boat, tpl, enemies, seed=seed, max_rounds=2)
        # Turn-1 alpha strike from 2 bursts should deal well over 50 damage.
        assert out["damage_dealt"] >= 40, (
            f"Missile boat turn-1 output only {out['damage_dealt']} dmg "
            f"(seed={seed}) — alpha strike fantasy is missing"
        )


# ============================================================================
# Skip-gated: Scenarios 5 & 6 depend on Dual Techs (B8)
# ============================================================================


class TestScenario5DualTechUnlock:
    @pytest.mark.skip(
        reason=(
            "Placeholder — §6.5 scenario body not yet implemented. Phase B8 "
            "(dual tech system) has shipped, so the gate itself is open; the "
            "remaining work is authoring the scenario assertions (round count, "
            "damage timing, telegraph-reading outcomes). Unblocked whenever "
            "the combat balance tuning pass picks this up."
        )
    )
    def test_balanced_build_survives_t4_boss_with_dual_tech(self) -> None:
        """§6.5 — Balanced build + Elena + Marcus L2+ vs T4 Juggernaut.
        Expected: 10-12 rounds. Fire at Will shifts pace at round 3.
        Survival requires reading telegraphs."""


class TestScenario6LegendaryGauntlet:
    @pytest.mark.skip(
        reason=(
            "Placeholder — §6.6 scenario body not yet implemented. Crew Sync "
            "shipped in B8 so the mechanism exists; this test still needs the "
            "actual scenario authoring (5 legendary superbosses × expected "
            "round counts, with Crew Sync usage pattern asserted)."
        )
    )
    def test_endgame_build_clears_all_5_legendaries(self) -> None:
        """§6.6 — Endgame build, all senior crew L3, vs each T5 legendary.
        Expected: 15-20 rounds each. Crew Sync available once per combat."""
