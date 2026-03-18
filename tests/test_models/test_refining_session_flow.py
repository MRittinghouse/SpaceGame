"""Tests for the complete refining session flow: job completion → buffer → cargo.

Covers session summary, output delivery, forge tokens, recipe mastery updates,
buffer overflow, and batch edge cases.
"""

from spacegame.models.forge_buffer import ForgeBuffer
from spacegame.models.player import Player
from spacegame.models.recipe_mastery import RecipeMasteryTracker
from spacegame.models.refining import Recipe, RefiningSession
from spacegame.models.ship import Ship, ShipType


def _make_ship_type(cargo_capacity: int = 100) -> ShipType:
    return ShipType(
        id="shuttle", name="Shuttle", ship_class="light",
        description="Test", cargo_capacity=cargo_capacity, fuel_capacity=50,
        fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
        resale_value=0, crew_slots=1, special_abilities=[], availability="all",
    )


def _make_player(cargo_capacity: int = 100) -> Player:
    return Player(
        name="TestCaptain", credits=5000,
        current_system_id="forgeworks",
        ship=Ship(ship_type=_make_ship_type(cargo_capacity), current_fuel=50),
    )


def _make_recipe(
    recipe_id: str = "smelt_iron",
    inputs: dict | None = None,
    outputs: dict | None = None,
    processing_time: float = 1.0,
) -> Recipe:
    return Recipe(
        id=recipe_id,
        name=f"Recipe {recipe_id}",
        description="Test recipe",
        inputs=inputs or {"iron_ore": 3},
        outputs=outputs or {"common_metals": 2},
        processing_time=processing_time,
        location_ids=["forgeworks"],
    )


class TestJobCompletionOutputs:
    """Verify job completion produces correct outputs."""

    def test_single_job_produces_outputs(self) -> None:
        """A completed job returns outputs in RefiningResult."""
        recipe = _make_recipe(processing_time=1.0)
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 10}
        session.start_job(recipe, inventory)

        results = session.update(2.0)
        assert len(results) == 1
        assert results[0].outputs["common_metals"] >= 2

    def test_multiple_jobs_complete_independently(self) -> None:
        """Multiple queued jobs each produce their own result."""
        recipe = _make_recipe(processing_time=0.5)
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 20}
        session.start_job(recipe, inventory)
        session.start_job(recipe, inventory)

        results = session.update(1.0)
        assert len(results) == 2
        assert all(r.outputs["common_metals"] >= 2 for r in results)

    def test_job_consumes_ingredients_from_inventory(self) -> None:
        """Starting a job removes ingredients from inventory."""
        recipe = _make_recipe(inputs={"iron_ore": 5})
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 12}
        session.start_job(recipe, inventory)
        assert inventory["iron_ore"] == 7


class TestForgeBufferFlow:
    """Verify output flows correctly through the forge buffer."""

    def test_output_added_to_buffer(self) -> None:
        """Job outputs should be addable to ForgeBuffer."""
        buf = ForgeBuffer(system_id="forgeworks")
        added = buf.add_output("common_metals", 5)
        assert added == 5
        assert buf.contents["common_metals"] == 5

    def test_buffer_to_cargo_transfer(self) -> None:
        """Buffer contents can be transferred to ship cargo."""
        buf = ForgeBuffer(system_id="forgeworks")
        buf.add_output("common_metals", 10)

        player = _make_player()
        for cid, qty in list(buf.contents.items()):
            removed = buf.remove_output(cid, qty)
            player.ship.add_cargo(cid, removed, 0)

        assert player.ship.get_cargo_quantity("common_metals") == 10
        assert buf.get_total_stored() == 0

    def test_buffer_overflow_caps_at_capacity(self) -> None:
        """Buffer rejects output beyond capacity."""
        buf = ForgeBuffer(system_id="forgeworks", capacity=5)
        added1 = buf.add_output("common_metals", 3)
        added2 = buf.add_output("common_metals", 5)
        assert added1 == 3
        assert added2 == 2  # Only 2 more fit
        assert buf.get_total_stored() == 5

    def test_buffer_overflow_with_full_cargo(self) -> None:
        """When cargo is full, buffer contents remain in buffer."""
        buf = ForgeBuffer(system_id="forgeworks")
        buf.add_output("common_metals", 10)

        player = _make_player(cargo_capacity=3)
        # Try to transfer — only 3 fit in cargo
        transferred = 0
        for cid, qty in list(buf.contents.items()):
            space = player.ship.ship_type.cargo_capacity - sum(player.ship.current_cargo.values())
            can_transfer = min(qty, space)
            if can_transfer > 0:
                buf.remove_output(cid, can_transfer)
                player.ship.add_cargo(cid, can_transfer, 0)
                transferred += can_transfer

        assert transferred == 3
        assert buf.get_total_stored() == 7  # 7 remain in buffer
        assert player.ship.get_cargo_quantity("common_metals") == 3


class TestForgeTokenAward:
    """Verify forge tokens are awarded on job completion."""

    def test_job_completion_earns_tokens(self) -> None:
        """Completed jobs should produce forge_tokens_earned > 0."""
        recipe = _make_recipe(processing_time=5.0, inputs={"iron_ore": 3, "raw_ore": 2})
        tracker = RecipeMasteryTracker()
        session = RefiningSession([recipe], "forgeworks", mastery_tracker=tracker)
        inventory = {"iron_ore": 10, "raw_ore": 10}
        session.start_job(recipe, inventory)

        results = session.update(6.0)
        assert len(results) == 1
        assert results[0].forge_tokens_earned > 0

    def test_tokens_scale_with_processing_time(self) -> None:
        """Longer recipes should earn more tokens."""
        short_recipe = _make_recipe("short", processing_time=2.0)
        long_recipe = _make_recipe("long", processing_time=10.0)
        tracker = RecipeMasteryTracker()
        session = RefiningSession([short_recipe, long_recipe], "forgeworks", mastery_tracker=tracker)
        inventory = {"iron_ore": 20}

        session.start_job(short_recipe, inventory)
        short_results = session.update(3.0)

        session.start_job(long_recipe, inventory)
        long_results = session.update(11.0)

        assert long_results[0].forge_tokens_earned > short_results[0].forge_tokens_earned

    def test_player_token_balance_increases(self) -> None:
        """Applying tokens to player increases their balance."""
        player = _make_player()
        initial = player.forge_tokens
        player.add_forge_tokens(15)
        assert player.forge_tokens == initial + 15


class TestRecipeMasteryTracking:
    """Verify mastery is tracked and leveled up during crafting."""

    def test_mastery_increments_on_completion(self) -> None:
        """Each completed job increments the recipe's craft count."""
        recipe = _make_recipe(processing_time=0.5)
        tracker = RecipeMasteryTracker()
        session = RefiningSession([recipe], "forgeworks", mastery_tracker=tracker)
        inventory = {"iron_ore": 30}

        for _ in range(3):
            session.start_job(recipe, inventory)
        session.update(1.0)

        mastery = tracker.get_mastery("smelt_iron")
        assert mastery.times_crafted == 3

    def test_mastery_level_1_at_3_crafts(self) -> None:
        """Mastery level 1 is reached at 3 crafts."""
        recipe = _make_recipe(processing_time=0.1)
        tracker = RecipeMasteryTracker()
        session = RefiningSession([recipe], "forgeworks", mastery_tracker=tracker)
        inventory = {"iron_ore": 50}

        for _ in range(3):
            session.start_job(recipe, inventory)
        session.update(1.0)

        mastery = tracker.get_mastery("smelt_iron")
        assert mastery.mastery_level >= 1

    def test_mastery_level_2_at_8_crafts(self) -> None:
        """Mastery level 2 is reached at 8 crafts."""
        recipe = _make_recipe(processing_time=0.1)
        tracker = RecipeMasteryTracker()
        session = RefiningSession(
            [recipe], "forgeworks", mastery_tracker=tracker, queue_size_bonus=3
        )
        inventory = {"iron_ore": 100}

        for _ in range(8):
            session.start_job(recipe, inventory)
        session.update(1.0)

        mastery = tracker.get_mastery("smelt_iron")
        assert mastery.mastery_level >= 2


class TestBatchCrafting:
    """Verify batch crafting mechanics."""

    def test_batch_consumes_all_ingredients(self) -> None:
        """A batch of 3 consumes 3x the recipe inputs."""
        recipe = _make_recipe(inputs={"iron_ore": 2})
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 10}

        success, msg = session.start_batch(recipe, inventory, count=3)
        assert success, f"Batch should succeed: {msg}"
        assert inventory["iron_ore"] == 4  # 10 - (2 * 3)
        assert session.get_queue_size() == 3

    def test_batch_fails_if_insufficient_materials(self) -> None:
        """Batch fails atomically if not enough for all jobs."""
        recipe = _make_recipe(inputs={"iron_ore": 5})
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 8}

        success, msg = session.start_batch(recipe, inventory, count=2)
        assert not success
        assert inventory["iron_ore"] == 8  # Nothing consumed

    def test_batch_fails_if_exceeds_queue(self) -> None:
        """Batch fails if count exceeds available queue slots."""
        recipe = _make_recipe(inputs={"iron_ore": 1})
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 100}

        # Fill queue to 4 of 5
        for _ in range(4):
            session.start_job(recipe, inventory)

        success, msg = session.start_batch(recipe, inventory, count=2)
        assert not success, "Should fail — only 1 slot available"
        assert session.get_queue_size() == 4

    def test_batch_zero_count_fails(self) -> None:
        """Batch with count=0 should fail."""
        recipe = _make_recipe()
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 10}

        success, msg = session.start_batch(recipe, inventory, count=0)
        assert not success

    def test_batch_all_jobs_complete(self) -> None:
        """All jobs from a batch eventually complete."""
        recipe = _make_recipe(processing_time=0.5)
        session = RefiningSession([recipe], "forgeworks")
        inventory = {"iron_ore": 30}

        session.start_batch(recipe, inventory, count=3)
        results = session.update(1.0)

        assert len(results) == 3
        assert session.get_queue_size() == 0


class TestSessionPlayerStats:
    """Verify player stat tracking during refining sessions."""

    def test_items_refined_incremented(self) -> None:
        """Player.items_refined increases when buffer receives output."""
        player = _make_player()
        initial = player.items_refined

        buf = ForgeBuffer(system_id="forgeworks")
        added = buf.add_output("common_metals", 5)
        player.items_refined += added

        assert player.items_refined == initial + 5

    def test_refining_jobs_completed_incremented(self) -> None:
        """Player.refining_jobs_completed tracks total jobs."""
        player = _make_player()
        initial = player.refining_jobs_completed
        player.refining_jobs_completed += 1
        assert player.refining_jobs_completed == initial + 1

    def test_recipes_crafted_tracks_unique_recipes(self) -> None:
        """Player.recipes_crafted is a set of unique recipe IDs."""
        player = _make_player()
        player.recipes_crafted.add("smelt_iron")
        player.recipes_crafted.add("smelt_iron")
        player.recipes_crafted.add("forge_alloy")
        assert len(player.recipes_crafted) == 2


class TestQueueExpansion:
    """Verify queue size can be expanded via forge upgrades."""

    def test_default_queue_size_is_five(self) -> None:
        """Base queue size is 5."""
        recipe = _make_recipe()
        session = RefiningSession([recipe], "forgeworks")
        assert session.max_queue_size == 5

    def test_expanded_queue_accepts_more_jobs(self) -> None:
        """Queue with bonus slots accepts more than 5 jobs."""
        recipe = _make_recipe(inputs={"iron_ore": 1})
        session = RefiningSession([recipe], "forgeworks", queue_size_bonus=3)
        inventory = {"iron_ore": 100}

        for _ in range(8):
            success, _ = session.start_job(recipe, inventory)
            assert success
        assert session.get_queue_size() == 8

        success, _ = session.start_job(recipe, inventory)
        assert not success  # 9th should fail (5 + 3 = 8 max)
