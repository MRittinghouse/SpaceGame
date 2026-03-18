"""Tests for recipe discovery system (Phase B2)."""

import pytest

from spacegame.models.refining import Recipe, RefiningSession


class TestRecipeDiscoveryFields:
    """Recipe model should support discovery fields."""

    def test_default_not_discoverable(self) -> None:
        recipe = Recipe(
            id="smelt_iron", name="Smelt Iron", description="test",
            inputs={"raw_ore": 10}, outputs={"common_metals": 2},
            processing_time=5.0, location_ids=["forgeworks"],
        )
        assert recipe.discoverable is False
        assert recipe.discovery_hint == ""
        assert recipe.discovery_prerequisite == ""

    def test_discoverable_recipe(self) -> None:
        recipe = Recipe(
            id="craft_reinforced_plating", name="Forge Reinforced Plating",
            description="test",
            inputs={"alloy_composite": 4}, outputs={"crafted_reinforced_plating": 1},
            processing_time=20.0, location_ids=["forgeworks"],
            discoverable=True,
            discovery_hint="Master alloy forging to unlock this blueprint.",
            discovery_prerequisite="forge_alloy",
        )
        assert recipe.discoverable is True
        assert recipe.discovery_hint == "Master alloy forging to unlock this blueprint."
        assert recipe.discovery_prerequisite == "forge_alloy"


class TestPlayerDiscoveredRecipes:
    """Player should track discovered recipes."""

    def _make_player(self) -> "Player":
        from spacegame.models.player import Player
        from spacegame.models.ship import Ship, ShipType
        ship_type = ShipType(
            id="shuttle", name="Shuttle", ship_class="light",
            description="Basic ship", cargo_capacity=50, fuel_capacity=100,
            fuel_efficiency=1.0, speed_multiplier=1.0, purchase_price=0,
            resale_value=0, crew_slots=1, special_abilities=[], availability="all",
        )
        ship = Ship(ship_type=ship_type, current_fuel=100)
        return Player(name="Tester", credits=1000, current_system_id="nexus_prime", ship=ship)

    def test_default_discovered_recipes_empty(self) -> None:
        player = self._make_player()
        assert player.discovered_recipes == set()

    def test_initialize_default_discoveries(self) -> None:
        """Non-discoverable recipes should auto-populate on init."""
        player = self._make_player()
        recipes = [
            Recipe(id="smelt_iron", name="Smelt Iron", description="test",
                   inputs={"raw_ore": 10}, outputs={"common_metals": 2},
                   processing_time=5.0, location_ids=["forgeworks"]),
            Recipe(id="craft_plating", name="Plating", description="test",
                   inputs={"alloy": 4}, outputs={"plating": 1},
                   processing_time=20.0, location_ids=["forgeworks"],
                   discoverable=True, discovery_prerequisite="smelt_iron"),
        ]
        player.initialize_discovered_recipes(recipes)
        assert "smelt_iron" in player.discovered_recipes
        assert "craft_plating" not in player.discovered_recipes

    def test_discover_recipe(self) -> None:
        player = self._make_player()
        player.discover_recipe("craft_reinforced_plating")
        assert "craft_reinforced_plating" in player.discovered_recipes

    def test_discover_already_discovered(self) -> None:
        player = self._make_player()
        player.discover_recipe("craft_reinforced_plating")
        player.discover_recipe("craft_reinforced_plating")
        assert "craft_reinforced_plating" in player.discovered_recipes

    def test_is_recipe_discovered(self) -> None:
        player = self._make_player()
        assert not player.is_recipe_discovered("craft_plating")
        player.discover_recipe("craft_plating")
        assert player.is_recipe_discovered("craft_plating")

    def test_serialization_round_trip(self) -> None:
        """discovered_recipes survives save/load cycle via SaveManager."""
        player = self._make_player()
        player.discover_recipe("craft_reinforced_plating")
        player.discover_recipe("craft_plasma_conduit")
        assert "craft_reinforced_plating" in player.discovered_recipes
        assert "craft_plasma_conduit" in player.discovered_recipes

    def test_discovered_set_is_mutable(self) -> None:
        player = self._make_player()
        player.discovered_recipes.add("test_recipe")
        assert "test_recipe" in player.discovered_recipes


class TestMasteryDiscoveryTrigger:
    """Mastery level 3 should trigger recipe discovery."""

    def test_mastery_3_discovers_dependent_recipe(self) -> None:
        from spacegame.models.recipe_mastery import RecipeMasteryTracker
        tracker = RecipeMasteryTracker()
        recipes = [
            Recipe(id="forge_alloy", name="Forge Alloy", description="test",
                   inputs={"common_metals": 5}, outputs={"alloy_composite": 2},
                   processing_time=10.0, location_ids=["forgeworks"]),
            Recipe(id="craft_reinforced_plating", name="Plating", description="test",
                   inputs={"alloy": 4}, outputs={"plating": 1},
                   processing_time=20.0, location_ids=["forgeworks"],
                   discoverable=True, discovery_prerequisite="forge_alloy"),
        ]
        discovered: list[str] = []
        # Craft forge_alloy 15 times to reach mastery 3
        for i in range(15):
            new_level = tracker.record_craft("forge_alloy")
            if new_level == 3:
                # Check for recipes unlocked by this mastery
                for r in recipes:
                    if r.discoverable and r.discovery_prerequisite == "forge_alloy":
                        discovered.append(r.id)

        assert "craft_reinforced_plating" in discovered

    def test_mastery_below_3_no_discovery(self) -> None:
        from spacegame.models.recipe_mastery import RecipeMasteryTracker
        tracker = RecipeMasteryTracker()
        recipes = [
            Recipe(id="forge_alloy", name="Forge Alloy", description="test",
                   inputs={"common_metals": 5}, outputs={"alloy_composite": 2},
                   processing_time=10.0, location_ids=["forgeworks"]),
            Recipe(id="craft_reinforced_plating", name="Plating", description="test",
                   inputs={"alloy": 4}, outputs={"plating": 1},
                   processing_time=20.0, location_ids=["forgeworks"],
                   discoverable=True, discovery_prerequisite="forge_alloy"),
        ]
        # Craft 8 times -> mastery 2
        for _ in range(8):
            tracker.record_craft("forge_alloy")
        entry = tracker.get_mastery("forge_alloy")
        assert entry.mastery_level == 2
        # No discovery at level 2
        for r in recipes:
            if r.discoverable and r.discovery_prerequisite == "forge_alloy":
                assert entry.mastery_level < 3


class TestRefiningSessionDiscoveryFilter:
    """RefiningSession should filter undiscovered recipes from available list."""

    def _make_recipes(self) -> list[Recipe]:
        return [
            Recipe(id="smelt_iron", name="Smelt Iron", description="test",
                   inputs={"raw_ore": 10}, outputs={"common_metals": 2},
                   processing_time=5.0, location_ids=["forgeworks"]),
            Recipe(id="craft_plating", name="Plating", description="test",
                   inputs={"alloy": 4}, outputs={"plating": 1},
                   processing_time=20.0, location_ids=["forgeworks"],
                   discoverable=True, discovery_prerequisite="smelt_iron"),
        ]

    def test_no_discovered_set_shows_all_non_discoverable(self) -> None:
        """Without discovered_recipes param, discoverable recipes are hidden."""
        recipes = self._make_recipes()
        session = RefiningSession(recipes, "forgeworks")
        ids = [r.id for r in session.available_recipes]
        assert "smelt_iron" in ids
        assert "craft_plating" not in ids

    def test_discovered_set_includes_discovered(self) -> None:
        """With discovered_recipes, discoverable recipes that are discovered show up."""
        recipes = self._make_recipes()
        session = RefiningSession(
            recipes, "forgeworks",
            discovered_recipes={"smelt_iron", "craft_plating"},
        )
        ids = [r.id for r in session.available_recipes]
        assert "smelt_iron" in ids
        assert "craft_plating" in ids

    def test_discovered_set_excludes_undiscovered(self) -> None:
        """Discoverable recipes NOT in discovered set are filtered out."""
        recipes = self._make_recipes()
        session = RefiningSession(
            recipes, "forgeworks",
            discovered_recipes={"smelt_iron"},
        )
        ids = [r.id for r in session.available_recipes]
        assert "smelt_iron" in ids
        assert "craft_plating" not in ids
