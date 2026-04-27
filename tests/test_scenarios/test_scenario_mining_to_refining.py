"""Scenario: mining → refining chain — full subsystem handoff.

SI-2 Stream 1. Existing ``test_scenario_mining_session`` covers the
session yield in isolation; this scenario picks up where that one stops
and walks the rest of the gameplay loop:

  1. MiningSession yields ore into ``session.total_mined``
  2. Mining view writes the yield into ``OreSilo`` (per-system buffer)
  3. Player transfers silo → ship cargo (capacity-bounded)
  4. Refining view reads from ship cargo to source recipe inputs
  5. ``RefiningSession.start_job`` consumes inputs and queues the job
  6. ``RefiningSession.update(dt)`` ticks until completion
  7. Refining view routes ``RefiningResult.outputs`` into ``ForgeBuffer``
  8. Player transfers buffer → ship cargo

Each hop is a distinct surface that can break in production. The scenario
mirrors the real view-layer transfer code (mining_view:1172 silo handoff
and refining_view:752/882 buffer handoff) inline so a regression in any
primitive surfaces here. **If those view-layer transfers are ever
extracted into model methods (``Player.commit_silo_to_cargo()`` or
similar — comparable to ``Player.apply_combat_defeat``), update the
inlined helpers below to delegate.**

This scenario would have caught: a silo-capacity off-by-one that ate
ore, a recipe that consumed inputs but didn't queue a job, a buffer
that accepted output but never released it, and the cargo-cap clipping
on transfer.
"""

from __future__ import annotations

from spacegame.data_loader import get_data_loader
from spacegame.models.refining import Recipe, RefiningSession
from tests.test_scenarios._helpers import fresh_player


def _commodity_volumes() -> dict[str, int]:
    """Same volumes the views use for cargo math."""
    dl = get_data_loader()
    dl.load_all()
    return {c.id: c.volume_per_unit for c in dl.commodities.values()}


# ---------------------------------------------------------------------------
# Test harness — mirrors view-layer transfers in helper functions so the
# scenario reads like the gameplay it's exercising.
# ---------------------------------------------------------------------------


def _smelt_iron_recipe() -> Recipe:
    """The simplest real recipe: 10 raw_ore → 2 common_metals (data/economy/recipes.json:4)."""
    return Recipe(
        id="smelt_iron",
        name="Smelt Iron",
        description="Melt down raw ore into usable common metals.",
        inputs={"raw_ore": 10},
        outputs={"common_metals": 2},
        processing_time=1.0,  # short for test speed; production value is 5.0
        location_ids=["nexus_prime"],
    )


def _commit_silo_to_cargo(player, system_id: str) -> dict[str, int]:
    """Mirror mining_view's exit-silo transfer (mining_view.py:685, capacity-bounded).

    Returns the dict of {commodity_id: qty_moved} for assertions.
    """
    silo = player.ore_silo_manager.get_silo(system_id)
    volumes = _commodity_volumes()
    moved: dict[str, int] = {}
    for cid, stored in list(silo.contents.items()):
        volume = volumes.get(cid, 1)
        available = player.ship.get_available_cargo(volumes)
        can_fit = available // volume if volume > 0 else stored
        qty = min(stored, can_fit)
        if qty <= 0:
            continue
        player.ship.add_cargo(cid, qty)
        silo.remove_ore(cid, qty)
        moved[cid] = qty
    return moved


def _commit_buffer_to_cargo(player, system_id: str) -> dict[str, int]:
    """Mirror refining_view's _transfer_buffer_to_cargo (refining_view.py:752)."""
    buffer = player.forge_buffer_manager.get_buffer(system_id)
    volumes = _commodity_volumes()
    moved: dict[str, int] = {}
    for cid, stored in list(buffer.contents.items()):
        volume = volumes.get(cid, 1)
        available = player.ship.get_available_cargo(volumes)
        can_fit = available // volume if volume > 0 else stored
        qty = min(stored, can_fit)
        if qty <= 0:
            continue
        player.ship.add_cargo(cid, qty)
        buffer.remove_output(cid, qty)
        moved[cid] = qty
    return moved


# ---------------------------------------------------------------------------
# Step-by-step coverage of each hop
# ---------------------------------------------------------------------------


class TestSiloToCargoHandoff:
    """Step 2 → 3: ore lands in the silo, transfers to cargo respecting capacity."""

    def test_silo_to_cargo_full_transfer_when_space_available(self) -> None:
        player = fresh_player()
        sys = player.current_system_id

        # Mining session writes 30 raw_ore into the per-system silo
        # (this is what mining_view does at line 1172 after each yield).
        silo = player.ore_silo_manager.get_silo(sys)
        added = silo.add_ore("raw_ore", 30)
        assert added == 30  # well under the BASE_SILO_CAPACITY of 100

        # Player exits mining → silo flushes into cargo
        moved = _commit_silo_to_cargo(player, sys)

        assert moved == {"raw_ore": 30}
        assert silo.contents == {}, "silo should be empty after full transfer"
        assert player.ship.current_cargo.get("raw_ore", 0) == 30

    def test_silo_to_cargo_clipped_by_cargo_capacity(self) -> None:
        """Cargo cap is the binding constraint — leftover stays in silo."""
        player = fresh_player()
        sys = player.current_system_id

        # Pre-fill cargo with raw_ore (volume 1) up to leave a small gap.
        # The silo holds extra; transfer should move only what fits.
        gap = 5
        player.ship.current_cargo["raw_ore"] = player.ship.max_cargo - gap

        silo = player.ore_silo_manager.get_silo(sys)
        silo.add_ore("raw_ore", 80)

        moved = _commit_silo_to_cargo(player, sys)

        assert moved.get("raw_ore", 0) == gap
        assert silo.contents.get("raw_ore", 0) == 80 - gap, (
            "remainder must persist in silo for next visit"
        )


class TestRefiningConsumesCargoAndProducesOutput:
    """Steps 4 → 7: refining session pulls inputs from cargo, ticks to
    completion, and routes outputs into the forge buffer."""

    def test_recipe_consumes_inputs_and_queues_job(self) -> None:
        player = fresh_player()
        sys = player.current_system_id
        recipe = _smelt_iron_recipe()
        session = RefiningSession([recipe], system_id=sys)

        # Cargo holds the inputs (acts as the inventory dict refining reads from)
        player.ship.add_cargo("raw_ore", 15)
        cargo = player.ship.current_cargo

        ok, msg = session.start_job(recipe, cargo)
        assert ok, f"expected job to start: {msg}"
        assert session.get_queue_size() == 1
        assert cargo.get("raw_ore", 0) == 5, "inputs deducted in-place"

    def test_update_ticks_to_completion_and_returns_outputs(self) -> None:
        player = fresh_player()
        sys = player.current_system_id
        recipe = _smelt_iron_recipe()
        session = RefiningSession([recipe], system_id=sys)

        player.ship.add_cargo("raw_ore", 10)
        cargo = player.ship.current_cargo
        session.start_job(recipe, cargo)

        # Tick under the duration → no completions yet
        early = session.update(0.5)
        assert early == [], "job should not be done at half time"
        assert session.get_queue_size() == 1

        # Tick past the duration → one completion fires
        results = session.update(1.0)
        assert len(results) == 1
        result = results[0]
        assert result.recipe_id == "smelt_iron"
        assert result.outputs == {"common_metals": 2}
        assert session.get_queue_size() == 0


class TestBufferToCargoHandoff:
    """Step 7 → 8: refining results go into the forge buffer, then transfer
    to cargo respecting capacity."""

    def test_buffer_to_cargo_round_trip(self) -> None:
        player = fresh_player()
        sys = player.current_system_id
        buffer = player.forge_buffer_manager.get_buffer(sys)

        # Refining view's _handle_result calls add_output for each commodity
        added = buffer.add_output("common_metals", 6)
        assert added == 6

        moved = _commit_buffer_to_cargo(player, sys)

        assert moved == {"common_metals": 6}
        assert buffer.contents == {}
        assert player.ship.current_cargo.get("common_metals", 0) == 6

    def test_buffer_clipped_by_cargo_when_full(self) -> None:
        """common_metals is volume 5/unit, so 'gap' units = gap*5 volume."""
        player = fresh_player()
        sys = player.current_system_id

        # Leave room for exactly 3 common_metals (15 volume).
        gap_units = 3
        gap_volume = gap_units * 5
        player.ship.current_cargo["raw_ore"] = player.ship.max_cargo - gap_volume

        buffer = player.forge_buffer_manager.get_buffer(sys)
        buffer.add_output("common_metals", 10)

        moved = _commit_buffer_to_cargo(player, sys)

        assert moved.get("common_metals", 0) == gap_units
        assert buffer.contents.get("common_metals", 0) == 10 - gap_units


# ---------------------------------------------------------------------------
# Full chain — the scenario this whole file exists for
# ---------------------------------------------------------------------------


class TestMiningToRefiningFullChain:
    def test_ore_yielded_in_mining_emerges_as_refined_in_cargo(self) -> None:
        """Full pipeline: mined raw_ore lands in silo → cargo → consumed by
        smelt_iron → produced as common_metals in buffer → transferred back
        to cargo. Asserts the final cargo state contains the refined product
        and zero raw_ore left over."""
        player = fresh_player()
        sys = player.current_system_id
        recipe = _smelt_iron_recipe()

        # Step 1+2: mining yielded 10 raw_ore → silo (mining_view:1172 path)
        player.ore_silo_manager.get_silo(sys).add_ore("raw_ore", 10)

        # Step 3: player exits mining, silo flushes to cargo
        moved_in = _commit_silo_to_cargo(player, sys)
        assert moved_in == {"raw_ore": 10}

        # Step 4+5: refining session consumes the raw_ore for smelt_iron
        session = RefiningSession([recipe], system_id=sys)
        ok, msg = session.start_job(recipe, player.ship.current_cargo)
        assert ok, msg
        assert player.ship.current_cargo.get("raw_ore", 0) == 0, "raw_ore consumed by refining"

        # Step 6: tick to completion
        results = session.update(recipe.processing_time + 0.1)
        assert len(results) == 1

        # Step 7: refining_view routes output into the forge buffer
        buffer = player.forge_buffer_manager.get_buffer(sys)
        for cid, qty in results[0].outputs.items():
            buffer.add_output(cid, qty)
        assert buffer.contents.get("common_metals", 0) == 2

        # Step 8: player exits refining, buffer flushes to cargo
        moved_out = _commit_buffer_to_cargo(player, sys)
        assert moved_out == {"common_metals": 2}

        # Final: cargo holds the refined product, no raw_ore residue, no
        # leftover in either buffer
        assert player.ship.current_cargo.get("common_metals", 0) == 2
        assert player.ship.current_cargo.get("raw_ore", 0) == 0
        assert player.ore_silo_manager.get_silo(sys).contents == {}
        assert player.forge_buffer_manager.get_buffer(sys).contents == {}
