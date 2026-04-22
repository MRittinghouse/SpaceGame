"""
Phase B8 — Dual tech system tests.

Covers the B8.1 foundation layer:
- DualTech data model (palette integrity)
- Availability gating (recruitment + loyalty + bridge)
- Executable moves for Gun Run + Focused Barrage

Execution of the non-ready techs (fire_at_will, power_drift,
daring_gambit, total_commitment, crew_sync) is deferred to B8.2 and is
NOT covered here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from spacegame.models.combat import EffectType
from spacegame.models.dual_tech import (
    DUAL_TECH_PALETTE,
    PAIR_TECH_IDS,
    TRIAD_TECH_IDS,
    DualTech,
    build_dual_tech_move,
    build_focused_barrage_move,
    build_gun_run_move,
    compute_available_dual_techs,
    is_dual_tech_available,
)

# ============================================================================
# Fake crew roster for isolated tests (no DataLoader needed)
# ============================================================================


@dataclass
class _FakeRoster:
    """Minimal ``CrewRoster`` stand-in with just ``get_member_state``."""

    states: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_member_state(self, template_id: str) -> dict[str, Any] | None:
        return self.states.get(template_id)


def _roster(**crew_loyalties: int) -> _FakeRoster:
    """Build a roster where each kwarg pairs crew_id → loyalty."""
    return _FakeRoster(
        states={cid: {"loyalty": loy} for cid, loy in crew_loyalties.items()}
    )


# Companion IDs used across tests.
ELENA = "elena_reeves"
MARCUS = "marcus_jin"
PRIYA = "dr_priya_osei"
TOMAS = "tomas_drifter"


# ============================================================================
# Palette integrity
# ============================================================================


class TestPaletteIntegrity:
    def test_palette_has_6_pairs_plus_1_triad(self) -> None:
        assert len(PAIR_TECH_IDS) == 6
        assert len(TRIAD_TECH_IDS) == 1
        assert len(DUAL_TECH_PALETTE) == 7

    def test_every_palette_entry_has_its_id_key(self) -> None:
        """Dict key must match DualTech.id — prevents typo drift."""
        for key, tech in DUAL_TECH_PALETTE.items():
            assert key == tech.id, f"Palette key {key!r} != tech.id {tech.id!r}"

    def test_all_six_pairs_combine_distinct_crew(self) -> None:
        """The 6 pairs are exactly (4 choose 2) = 6 combinations of the
        senior crew. No duplicates, no same-person pairs."""
        pair_sets = [
            frozenset(DUAL_TECH_PALETTE[tid].crew_ids)
            for tid in PAIR_TECH_IDS
        ]
        assert len(set(pair_sets)) == 6, "Pairs must be distinct"
        for pair in pair_sets:
            assert len(pair) == 2, f"Pair has wrong size: {pair}"

    def test_triad_includes_all_four_senior_crew(self) -> None:
        triad = DUAL_TECH_PALETTE["crew_sync"]
        assert set(triad.crew_ids) == {ELENA, MARCUS, PRIYA, TOMAS}
        assert triad.once_per_combat is True

    def test_loyalty_thresholds_in_valid_range(self) -> None:
        for tech in DUAL_TECH_PALETTE.values():
            assert 0 < tech.loyalty_req <= 100, (
                f"{tech.id} loyalty_req {tech.loyalty_req} outside (0, 100]"
            )

    def test_energy_costs_are_meaningful(self) -> None:
        """Design doc §5 — energy 4-12. No free dual techs."""
        for tech in DUAL_TECH_PALETTE.values():
            assert 4 <= tech.energy_cost <= 12, (
                f"{tech.id} energy_cost {tech.energy_cost} outside 4-12"
            )

    def test_pair_cooldowns_in_design_band(self) -> None:
        """Design doc §5 — pairs have cooldown 4-6."""
        for tid in PAIR_TECH_IDS:
            cd = DUAL_TECH_PALETTE[tid].cooldown
            assert 4 <= cd <= 6, f"{tid} cooldown {cd} outside 4-6"


# ============================================================================
# Availability gating
# ============================================================================


class TestAvailabilityGating:
    def test_gun_run_unavailable_without_recruitment(self) -> None:
        tech = DUAL_TECH_PALETTE["gun_run"]
        roster = _roster()  # Nobody recruited.
        ok, reason = is_dual_tech_available(tech, roster)
        assert ok is False
        assert "not recruited" in reason

    def test_gun_run_unavailable_with_half_party(self) -> None:
        """Marcus recruited at high loyalty, but Tomas missing."""
        tech = DUAL_TECH_PALETTE["gun_run"]
        roster = _roster(**{MARCUS: 80})
        ok, reason = is_dual_tech_available(tech, roster)
        assert ok is False
        assert TOMAS in reason

    def test_gun_run_unavailable_at_insufficient_loyalty(self) -> None:
        tech = DUAL_TECH_PALETTE["gun_run"]  # Requires 50
        roster = _roster(**{MARCUS: 80, TOMAS: 40})
        ok, reason = is_dual_tech_available(tech, roster)
        assert ok is False
        assert "loyalty" in reason.lower()

    def test_gun_run_available_when_all_gates_met(self) -> None:
        tech = DUAL_TECH_PALETTE["gun_run"]
        roster = _roster(**{MARCUS: 60, TOMAS: 60})
        ok, reason = is_dual_tech_available(tech, roster)
        assert ok is True
        assert reason == "OK"

    def test_total_commitment_needs_higher_loyalty(self) -> None:
        """Requires 70 — 60 is not enough."""
        tech = DUAL_TECH_PALETTE["total_commitment"]
        roster = _roster(**{ELENA: 60, PRIYA: 60})
        ok, _ = is_dual_tech_available(tech, roster)
        assert ok is False
        roster = _roster(**{ELENA: 75, PRIYA: 75})
        ok, _ = is_dual_tech_available(tech, roster)
        assert ok is True

    def test_bridge_filter_locks_techs_when_crew_absent(self) -> None:
        """Even if recruited + loyal, a tech is locked if a participant
        isn't in the bridge set."""
        tech = DUAL_TECH_PALETTE["gun_run"]
        roster = _roster(**{MARCUS: 80, TOMAS: 80})
        # Marcus on bridge, Tomas off.
        ok, reason = is_dual_tech_available(tech, roster, bridge_crew_ids={MARCUS})
        assert ok is False
        assert TOMAS in reason

    def test_triad_requires_all_four(self) -> None:
        tech = DUAL_TECH_PALETTE["crew_sync"]
        roster = _roster(**{ELENA: 80, MARCUS: 80, PRIYA: 80})  # Missing Tomas.
        ok, reason = is_dual_tech_available(tech, roster)
        assert ok is False
        assert TOMAS in reason

        # All four at L3 → unlocked.
        roster = _roster(**{ELENA: 80, MARCUS: 80, PRIYA: 80, TOMAS: 80})
        ok, _ = is_dual_tech_available(tech, roster)
        assert ok is True


# ============================================================================
# compute_available_dual_techs
# ============================================================================


class TestComputeAvailable:
    def test_empty_roster_has_no_techs(self) -> None:
        available = compute_available_dual_techs(_roster())
        assert available == []

    def test_only_elena_and_marcus_at_l2_unlocks_fire_at_will(self) -> None:
        roster = _roster(**{ELENA: 60, MARCUS: 60})
        available = compute_available_dual_techs(roster)
        ids = {t.id for t in available}
        assert ids == {"fire_at_will"}

    def test_all_four_at_max_loyalty_unlocks_everything(self) -> None:
        roster = _roster(**{ELENA: 100, MARCUS: 100, PRIYA: 100, TOMAS: 100})
        available = compute_available_dual_techs(roster)
        ids = {t.id for t in available}
        # All 6 pairs + triad.
        assert ids == set(PAIR_TECH_IDS + TRIAD_TECH_IDS)

    def test_all_four_at_l2_only_unlocks_l2_techs(self) -> None:
        """At loyalty 60, L3 techs (req 70) stay locked."""
        roster = _roster(**{ELENA: 60, MARCUS: 60, PRIYA: 60, TOMAS: 60})
        available = compute_available_dual_techs(roster)
        ids = {t.id for t in available}
        # L2 pairs only: fire_at_will, daring_gambit, gun_run, power_drift
        assert ids == {"fire_at_will", "daring_gambit", "gun_run", "power_drift"}

    def test_order_is_stable(self) -> None:
        """Order of the return list follows PAIR_TECH_IDS + TRIAD_TECH_IDS."""
        roster = _roster(**{ELENA: 100, MARCUS: 100, PRIYA: 100, TOMAS: 100})
        available = compute_available_dual_techs(roster)
        got_order = [t.id for t in available]
        assert got_order == list(PAIR_TECH_IDS + TRIAD_TECH_IDS)


# ============================================================================
# Executable dual-tech move factories
# ============================================================================


class TestExecutableDualTechMoves:
    def test_gun_run_is_aoe_damage(self) -> None:
        move = build_gun_run_move()
        assert move.id == "gun_run"
        assert move.aoe is True
        damage_effects = [e for e in move.effects if e.type is EffectType.DAMAGE]
        assert len(damage_effects) == 1
        assert damage_effects[0].value == 35.0
        assert move.energy_cost == DUAL_TECH_PALETTE["gun_run"].energy_cost
        assert move.cooldown == DUAL_TECH_PALETTE["gun_run"].cooldown

    def test_focused_barrage_is_single_target(self) -> None:
        move = build_focused_barrage_move()
        assert move.id == "focused_barrage"
        assert move.aoe is False
        damage_effects = [e for e in move.effects if e.type is EffectType.DAMAGE]
        assert len(damage_effects) == 1
        assert damage_effects[0].value == 55.0

    def test_all_palette_techs_are_executable_after_b83(self) -> None:
        """Post-B8.3 every palette tech has a factory. The factory may
        return a move whose full fidelity is still partial (e.g., Crew
        Sync's armor-pierce is a flag, not an effect field), but the
        move is buildable and the engine handles it."""
        for tid in DUAL_TECH_PALETTE:
            assert build_dual_tech_move(tid) is not None, (
                f"{tid} factory returned None — wire an executor"
            )

    def test_build_dual_tech_move_returns_none_for_unknown_id(self) -> None:
        assert build_dual_tech_move("not_a_tech") is None

    def test_executable_techs_match_implementation_ready_flag(self) -> None:
        """The B8.1 executable set must agree with the palette flag.
        If someone flips ``implementation_ready`` on a tech, they must
        also wire a factory (or the contract silently drifts)."""
        executable: set[str] = set()
        for tid in DUAL_TECH_PALETTE:
            if build_dual_tech_move(tid) is not None:
                executable.add(tid)

        flagged = {
            tid
            for tid, tech in DUAL_TECH_PALETTE.items()
            if tech.implementation_ready
        }
        assert executable == flagged, (
            f"implementation_ready={flagged} but executable={executable} — "
            f"factory map and flag must agree"
        )


# ============================================================================
# DualTech dataclass shape sanity
# ============================================================================


class TestDescribeAllDualTechs:
    """UI-facing helper for the crew-roster view's locked-tech discovery panel."""

    def test_empty_roster_all_techs_locked(self) -> None:
        from spacegame.models.dual_tech import describe_all_dual_techs

        statuses = describe_all_dual_techs(_roster())
        # One entry per palette tech, in canonical order.
        assert len(statuses) == len(DUAL_TECH_PALETTE)
        assert all(not s.is_available for s in statuses), (
            "Empty roster should lock every tech"
        )

    def test_order_follows_canonical_pair_then_triad(self) -> None:
        from spacegame.models.dual_tech import describe_all_dual_techs

        statuses = describe_all_dual_techs(_roster())
        ids = [s.tech.id for s in statuses]
        from spacegame.models.dual_tech import PAIR_TECH_IDS, TRIAD_TECH_IDS

        assert ids == list(PAIR_TECH_IDS + TRIAD_TECH_IDS)

    def test_partial_unlock_reports_mixed_state(self) -> None:
        from spacegame.models.dual_tech import describe_all_dual_techs

        # Elena + Marcus at L2 → only Fire at Will available.
        roster = _roster(**{ELENA: 60, MARCUS: 60})
        statuses = describe_all_dual_techs(roster)
        by_id = {s.tech.id: s for s in statuses}
        assert by_id["fire_at_will"].is_available is True
        assert by_id["fire_at_will"].lock_reason == "OK"
        # A tech requiring Priya (not recruited) or Marcus (low loyalty)
        # is locked. is_dual_tech_available returns the first blocking
        # crew; either is acceptable.
        assert by_id["focused_barrage"].is_available is False
        reason = by_id["focused_barrage"].lock_reason
        assert MARCUS in reason or PRIYA in reason, (
            f"Expected a blocking crew name in reason; got: {reason}"
        )

    def test_crew_loyalties_include_current_values(self) -> None:
        from spacegame.models.dual_tech import describe_all_dual_techs

        roster = _roster(**{ELENA: 75, MARCUS: 40})
        statuses = describe_all_dual_techs(roster)
        faw = next(s for s in statuses if s.tech.id == "fire_at_will")
        # Current loyalty values are surfaced for the UI.
        by_crew = dict(faw.crew_loyalties)
        assert by_crew[ELENA] == 75
        assert by_crew[MARCUS] == 40

    def test_unrecruited_crew_loyalty_is_none(self) -> None:
        from spacegame.models.dual_tech import describe_all_dual_techs

        # Only Elena — Marcus not recruited.
        roster = _roster(**{ELENA: 75})
        statuses = describe_all_dual_techs(roster)
        faw = next(s for s in statuses if s.tech.id == "fire_at_will")
        by_crew = dict(faw.crew_loyalties)
        assert by_crew[ELENA] == 75
        assert by_crew[MARCUS] is None


class TestDualTechDataclass:
    def test_dualtech_is_hashable(self) -> None:
        """Frozen dataclass — usable as dict keys / set members."""
        tech = DualTech(
            id="x", name="X", crew_ids=("a", "b"),
            loyalty_req=50, energy_cost=4, cooldown=4, description="",
        )
        d = {tech: 1}
        assert tech in d

    def test_crew_ids_is_a_tuple(self) -> None:
        """All palette entries store crew IDs as tuples (immutable)."""
        for tech in DUAL_TECH_PALETTE.values():
            assert isinstance(tech.crew_ids, tuple)
