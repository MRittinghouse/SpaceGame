"""
Refining system models.

Process raw materials into valuable goods through recipes and job queues.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Recipe:
    """A refining recipe that converts inputs to outputs."""

    id: str
    name: str
    description: str
    inputs: Dict[str, int]  # commodity_id -> quantity required
    outputs: Dict[str, int]  # commodity_id -> quantity produced
    processing_time: float  # Seconds to complete
    location_ids: List[str]  # Systems where this recipe is available
    requires_skill: Optional[str] = None  # Skill ID required (or None)

    def can_craft(self, inventory: Dict[str, int]) -> bool:
        """Check if inventory has required inputs."""
        for commodity_id, required in self.inputs.items():
            if inventory.get(commodity_id, 0) < required:
                return False
        return True

    def get_missing_inputs(self, inventory: Dict[str, int]) -> Dict[str, int]:
        """Get dict of missing inputs and quantities needed."""
        missing = {}
        for commodity_id, required in self.inputs.items():
            have = inventory.get(commodity_id, 0)
            if have < required:
                missing[commodity_id] = required - have
        return missing


@dataclass
class ActiveJob:
    """A refining job in progress."""

    recipe: Recipe
    effective_time: float  # processing_time * speed factor
    elapsed_time: float = 0.0

    def advance(self, dt: float) -> None:
        """Advance job progress by delta time."""
        self.elapsed_time += dt

    @property
    def progress(self) -> float:
        """Get completion fraction (0.0 to 1.0)."""
        if self.effective_time <= 0:
            return 1.0
        return min(1.0, self.elapsed_time / self.effective_time)

    @property
    def remaining_time(self) -> float:
        """Get remaining time in seconds."""
        return max(0.0, self.effective_time - self.elapsed_time)

    @property
    def is_complete(self) -> bool:
        """Check if job is finished."""
        return self.elapsed_time >= self.effective_time


@dataclass
class RefiningResult:
    """Result of a completed refining job."""

    recipe_id: str
    outputs: Dict[str, int]


class RefiningSession:
    """
    Manages the refining queue and job processing.

    Jobs process in real-time with progress bars.
    Multiple jobs can queue (idle mechanic).
    """

    MAX_QUEUE_SIZE = 5

    def __init__(
        self,
        recipes: List[Recipe],
        system_id: str,
        speed_bonus: float = 0.0,
        yield_bonus: float = 0.0,
    ):
        """
        Initialize refining session.

        Args:
            recipes: Available recipes at this location
            system_id: Current system ID
            speed_bonus: Skill-based speed multiplier (0.0 = no bonus)
            yield_bonus: Chance per output unit to produce +1 extra (0.0 to 1.0)
        """
        self.available_recipes = [r for r in recipes if system_id in r.location_ids]
        self.job_queue: List[ActiveJob] = []
        self.total_refined: Dict[str, int] = {}
        self.speed_bonus = speed_bonus
        self.yield_bonus = yield_bonus

    def start_job(self, recipe: Recipe, inventory: Dict[str, int]) -> Tuple[bool, str]:
        """
        Start a refining job, consuming inputs from inventory.

        Args:
            recipe: Recipe to process
            inventory: Player's cargo (will be modified on success)

        Returns:
            Tuple of (success, message)
        """
        if len(self.job_queue) >= self.MAX_QUEUE_SIZE:
            return (False, "Refining queue is full (max 5 jobs)")

        if not recipe.can_craft(inventory):
            missing = recipe.get_missing_inputs(inventory)
            missing_str = ", ".join(f"{qty} {cid}" for cid, qty in missing.items())
            return (False, f"Missing: {missing_str}")

        # Consume inputs
        for commodity_id, qty in recipe.inputs.items():
            inventory[commodity_id] = inventory.get(commodity_id, 0) - qty
            if inventory[commodity_id] <= 0:
                del inventory[commodity_id]

        # Add job to queue
        effective_time = recipe.processing_time * max(0.1, 1.0 - self.speed_bonus)
        job = ActiveJob(recipe=recipe, effective_time=effective_time)
        self.job_queue.append(job)
        return (True, f"Started: {recipe.name}")

    def start_batch(
        self, recipe: Recipe, inventory: Dict[str, int], count: int
    ) -> Tuple[bool, str]:
        """
        Queue multiple copies of a recipe atomically.

        Args:
            recipe: Recipe to process
            inventory: Player's cargo (modified on success)
            count: Number of jobs to queue

        Returns:
            Tuple of (success, message)
        """
        if count <= 0:
            return (False, "Count must be at least 1")

        available_slots = self.MAX_QUEUE_SIZE - len(self.job_queue)
        if count > available_slots:
            return (False, f"Only {available_slots} queue slots available")

        # Check materials for full batch
        for cid, qty in recipe.inputs.items():
            if inventory.get(cid, 0) < qty * count:
                return (False, f"Need {qty * count} {cid}, have {inventory.get(cid, 0)}")

        # Consume all inputs atomically
        for cid, qty in recipe.inputs.items():
            inventory[cid] = inventory.get(cid, 0) - qty * count
            if inventory[cid] <= 0:
                del inventory[cid]

        # Queue individual jobs
        effective_time = recipe.processing_time * max(0.1, 1.0 - self.speed_bonus)
        for _ in range(count):
            self.job_queue.append(ActiveJob(recipe=recipe, effective_time=effective_time))

        return (True, f"Queued {count}x {recipe.name}")

    def update(self, dt: float) -> List[RefiningResult]:
        """
        Update all jobs in the queue.

        Args:
            dt: Delta time in seconds

        Returns:
            List of completed job results
        """
        results = []
        completed_indices = []

        for i, job in enumerate(self.job_queue):
            job.advance(dt)

            if job.is_complete:
                outputs = dict(job.recipe.outputs)
                if self.yield_bonus > 0:
                    outputs = self._apply_yield_bonus(outputs)
                result = RefiningResult(
                    recipe_id=job.recipe.id,
                    outputs=outputs,
                )
                results.append(result)
                completed_indices.append(i)

                # Track totals
                for cid, qty in outputs.items():
                    self.total_refined[cid] = self.total_refined.get(cid, 0) + qty

        # Remove completed jobs (reverse order to preserve indices)
        for i in reversed(completed_indices):
            self.job_queue.pop(i)

        return results

    def _apply_yield_bonus(self, outputs: Dict[str, int]) -> Dict[str, int]:
        """Roll per-unit bonus yield chance."""
        boosted: Dict[str, int] = {}
        for cid, qty in outputs.items():
            bonus = sum(1 for _ in range(qty) if random.random() < self.yield_bonus)
            boosted[cid] = qty + bonus
        return boosted

    def get_queue_size(self) -> int:
        """Get number of jobs in queue."""
        return len(self.job_queue)

    def get_available_recipes(
        self, inventory: Dict[str, int], unlocked_skills: Optional[Dict[str, bool]] = None
    ) -> List[Recipe]:
        """
        Get recipes that can currently be crafted.

        Args:
            inventory: Player's current cargo
            unlocked_skills: Dict of skill_id -> True for unlocked skills

        Returns:
            List of craftable recipes
        """
        craftable = []
        for recipe in self.available_recipes:
            if recipe.requires_skill:
                if not unlocked_skills or not unlocked_skills.get(recipe.requires_skill):
                    continue
            if recipe.can_craft(inventory):
                craftable.append(recipe)
        return craftable
