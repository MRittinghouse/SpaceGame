"""Tests for Phase 14 — Damage overkill propagation.

Covers excess damage tracking, hull propagation, adjacency map
construction, chain damage mechanics, and cascade limits.
"""

import random

from spacegame.models.module_combat import (
    ModuleCombatState,
    apply_module_damage,
    build_adjacency_map,
    process_overkill_chain,
    CHAIN_DAMAGE_CHANCE,
    CHAIN_DAMAGE_RATIO,
    MIN_EXCESS_FOR_CHAIN,
)
from spacegame.models.ship_build import PlacedSlot, ShipBuild
from spacegame.models.slot_definition import SlotDefinition


# ============================================================================
# Helpers
# ============================================================================


def _slot_def_2x2(sid: str) -> SlotDefinition:
    return SlotDefinition(
        id=sid,
        slot_type="weapon",
        size="small",
        footprint_w=2,
        footprint_h=2,
        weight=2.0,
        placement_cost=0,
        color=(200, 60, 60),
    )


# ============================================================================
# Excess Damage Tracking
# ============================================================================


class TestExcessDamage:
    def test_no_excess_when_damage_less_than_hp(self) -> None:
        state = ModuleCombatState("a", 0, 30, 30, False, "weapon")
        msg, excess = apply_module_damage(state, 10)
        assert excess == 0
        assert state.current_hp == 20

    def test_no_excess_at_exact_hp(self) -> None:
        state = ModuleCombatState("a", 0, 30, 10, False, "weapon")
        msg, excess = apply_module_damage(state, 10)
        assert excess == 0
        assert state.current_hp == 0
        assert state.disabled

    def test_excess_on_overkill(self) -> None:
        state = ModuleCombatState("a", 0, 30, 10, False, "weapon")
        msg, excess = apply_module_damage(state, 25)
        assert excess == 15
        assert state.current_hp == 0
        assert state.disabled

    def test_large_overkill(self) -> None:
        state = ModuleCombatState("a", 0, 20, 5, False, "engine")
        msg, excess = apply_module_damage(state, 100)
        assert excess == 95

    def test_already_disabled_returns_full_as_excess(self) -> None:
        state = ModuleCombatState("a", 0, 20, 0, True, "engine")
        msg, excess = apply_module_damage(state, 30)
        assert excess == 30

    def test_message_includes_disabled(self) -> None:
        state = ModuleCombatState("a", 0, 20, 5, False, "engine")
        msg, _ = apply_module_damage(state, 20)
        assert "disabled" in msg.lower()


# ============================================================================
# Adjacency Map
# ============================================================================


class TestAdjacencyMap:
    def test_adjacent_slots(self) -> None:
        """Two slots placed side by side should be adjacent."""
        catalog = {"mod": _slot_def_2x2("mod")}
        build = ShipBuild(
            weight_class="tiny",
            placed_slots=[
                PlacedSlot(slot_def_id="mod", x=0, y=0),
                PlacedSlot(slot_def_id="mod", x=2, y=0),
            ],
        )
        adj = build_adjacency_map(build, catalog)
        assert 1 in adj.get(0, []), "Slot 0 should be adjacent to slot 1"
        assert 0 in adj.get(1, []), "Slot 1 should be adjacent to slot 0"

    def test_non_adjacent_slots(self) -> None:
        """Slots far apart should not be adjacent."""
        catalog = {"mod": _slot_def_2x2("mod")}
        build = ShipBuild(
            weight_class="tiny",
            placed_slots=[
                PlacedSlot(slot_def_id="mod", x=0, y=0),
                PlacedSlot(slot_def_id="mod", x=10, y=10),
            ],
        )
        adj = build_adjacency_map(build, catalog)
        assert 1 not in adj.get(0, [])
        assert 0 not in adj.get(1, [])

    def test_diagonal_not_adjacent(self) -> None:
        """Diagonally touching slots should NOT be adjacent (4-connected only)."""
        catalog = {"mod": _slot_def_2x2("mod")}
        build = ShipBuild(
            weight_class="tiny",
            placed_slots=[
                PlacedSlot(slot_def_id="mod", x=0, y=0),
                PlacedSlot(slot_def_id="mod", x=2, y=2),
            ],
        )
        adj = build_adjacency_map(build, catalog)
        assert 1 not in adj.get(0, [])

    def test_three_slots_in_chain(self) -> None:
        """A-B-C chain: A adjacent to B, B adjacent to C, A not adjacent to C."""
        catalog = {"mod": _slot_def_2x2("mod")}
        build = ShipBuild(
            weight_class="tiny",
            placed_slots=[
                PlacedSlot(slot_def_id="mod", x=0, y=0),  # A
                PlacedSlot(slot_def_id="mod", x=2, y=0),  # B (adjacent to A)
                PlacedSlot(slot_def_id="mod", x=4, y=0),  # C (adjacent to B, not A)
            ],
        )
        adj = build_adjacency_map(build, catalog)
        assert 1 in adj[0]
        assert 0 in adj[1]
        assert 2 in adj[1]
        assert 1 in adj[2]
        assert 2 not in adj.get(0, [])  # A and C not adjacent

    def test_empty_build(self) -> None:
        adj = build_adjacency_map(ShipBuild(weight_class="tiny"), {})
        assert adj == {}


# ============================================================================
# Chain Damage Propagation
# ============================================================================


class TestOverkillChain:
    def test_no_chain_below_threshold(self) -> None:
        """Small excess damage should not trigger chain."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
        ]
        adj = {0: [1], 1: [0]}
        random.seed(42)
        result = process_overkill_chain(
            excess=MIN_EXCESS_FOR_CHAIN - 1,
            source_idx=0,
            states=states,
            adjacency=adj,
        )
        assert result is None

    def test_chain_triggers_on_high_roll(self) -> None:
        """With 100% chance override, chain should always trigger."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
        ]
        adj = {0: [1], 1: [0]}
        # Force trigger by seeding
        random.seed(0)  # Need to find a seed that triggers at 30%
        # Instead test with sufficient excess and verify the chain mechanic
        result = process_overkill_chain(
            excess=100,
            source_idx=0,
            states=states,
            adjacency=adj,
            force_chain=True,  # Test helper
        )
        assert result is not None
        assert result["target_idx"] == 1
        assert result["damage"] == int(100 * CHAIN_DAMAGE_RATIO)

    def test_chain_damage_ratio(self) -> None:
        """Chain damage should be excess * CHAIN_DAMAGE_RATIO."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
        ]
        adj = {0: [1], 1: [0]}
        result = process_overkill_chain(
            excess=40,
            source_idx=0,
            states=states,
            adjacency=adj,
            force_chain=True,
        )
        assert result is not None
        assert result["damage"] == int(40 * CHAIN_DAMAGE_RATIO)

    def test_no_chain_to_non_adjacent(self) -> None:
        """Chain should never hit non-adjacent modules."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
        ]
        adj = {0: [], 1: []}  # No adjacency
        result = process_overkill_chain(
            excess=100,
            source_idx=0,
            states=states,
            adjacency=adj,
            force_chain=True,
        )
        assert result is None

    def test_chain_skips_already_disabled(self) -> None:
        """Chain should not target already-disabled modules."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 0, True, "shield"),  # Already disabled
        ]
        adj = {0: [1], 1: [0]}
        result = process_overkill_chain(
            excess=100,
            source_idx=0,
            states=states,
            adjacency=adj,
            force_chain=True,
        )
        assert result is None  # No valid target

    def test_chain_picks_random_neighbor(self) -> None:
        """With multiple neighbors, chain picks one randomly."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
            ModuleCombatState("c", 2, 20, 20, False, "engine"),
        ]
        adj = {0: [1, 2], 1: [0], 2: [0]}
        random.seed(42)
        targets = set()
        for _ in range(50):
            result = process_overkill_chain(
                excess=20,
                source_idx=0,
                states=states,
                adjacency=adj,
                force_chain=True,
            )
            if result:
                targets.add(result["target_idx"])
        # Should hit both neighbors over 50 tries
        assert len(targets) >= 2

    def test_probability_respects_chance(self) -> None:
        """Over many rolls, chain should trigger ~30% of the time."""
        states = [
            ModuleCombatState("a", 0, 20, 0, True, "weapon"),
            ModuleCombatState("b", 1, 20, 20, False, "shield"),
        ]
        adj = {0: [1], 1: [0]}
        random.seed(42)
        triggers = sum(
            1
            for _ in range(1000)
            if process_overkill_chain(excess=20, source_idx=0, states=states, adjacency=adj)
            is not None
        )
        # Should be ~300 ± 50
        assert 200 < triggers < 400, f"Expected ~300 triggers, got {triggers}"
