"""Scenario: new-game happy path — the critical fresh-run sequence.

SI-1c (see ``requirements/stability_initiative.md``).

Exercises the exact journey every playtester hits on a fresh launch:

  1. Fresh Player (nothing bought, no dialogue flags set)
  2. TutorialShopView renders without crash
  3. Player purchases every mandatory tutorial part + a choice part
     (dialogue flags accumulate via the registry-backed helper)
  4. Parts land in the inventory via ``Player.add_part`` (same path
     the real shipyard shop uses)
  5. Control transitions to the ship builder in tutorial mode
  6. ShipBuilderView renders without crash at the current state
  7. ``_get_slot_definitions_grouped`` surfaces the slot types the
     purchased parts actually fit into
  8. ``_pick_tutorial_narration`` returns a non-empty string for every
     meaningful state (welcome, per-part, completion)
  9. Build confirmation path doesn't raise

Both game-breaking crashes that motivated the Stability Initiative would
have been caught here on day zero — the first would trip step (7), the
second would trip step (8). Keeping this test green is non-negotiable.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui
import pytest

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH, GameState


@pytest.fixture(autouse=True, scope="module")
def _pygame_session():
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield


def _fresh_tutorial_player():
    """Brand-new player as they come out of character creation."""
    from spacegame.data_loader import get_data_loader
    from spacegame.models.player import Player
    from spacegame.models.ship import Ship

    dl = get_data_loader()
    dl.load_all()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    return Player(
        name="Happy Path",
        credits=10_000,  # enough to buy every tutorial part
        current_system_id="nexus_prime",
        ship=ship,
    )


def _ui():
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def _screen():
    return pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))


class TestNewGameHappyPath:
    def test_full_journey_does_not_crash(self) -> None:
        """End-to-end: fresh player → shop → builder → narration. One test
        so it aborts at the first broken link rather than skipping steps
        on a cascade of prior failures."""
        from spacegame.constants.flags import tutorial_bought_part
        from spacegame.data_loader import get_data_loader
        from spacegame.views.ship_builder_view import ShipBuilderView
        from spacegame.views.tutorial_shop_view import (
            TUTORIAL_MANDATORY,
            TUTORIAL_PARTS,
            TutorialShopView,
        )

        dl = get_data_loader()
        dl.load_all()
        player = _fresh_tutorial_player()

        # --- 2. Shop renders without crash ---
        shop_ui = _ui()
        shop = TutorialShopView(ui_manager=shop_ui, player=player, data_loader=dl)
        shop.on_enter()
        shop.update(0.016)
        shop.render(_screen())

        # --- 3. Purchase mandatory parts + one choice via the real handler ---
        # Index 0-2 are mandatory; 3 is the cargo hold (choice).
        for i in range(len(TUTORIAL_MANDATORY)):
            shop._buy_part(i)
        # Choice: cargo hold (index 3 in TUTORIAL_PARTS = index 0 in TUTORIAL_CHOICES)
        shop._buy_part(len(TUTORIAL_MANDATORY))

        # Shop declares the transition by setting next_state
        assert shop.get_next_state() == GameState.TUTORIAL_BUILDER

        # --- 4. Flags are set via the registry (no string drift possible) ---
        for p in TUTORIAL_MANDATORY:
            assert player.dialogue_flags.get(tutorial_bought_part(p.part_id)), (
                f"Expected tutorial flag for {p.part_id} after purchase"
            )
        assert player.dialogue_flags.get(tutorial_bought_part("scrapyard_hold")), (
            "Expected cargo hold flag after choice purchase"
        )

        # --- 4b. Parts live in inventory (same path as real shipyard shop) ---
        inventory = getattr(player, "parts_inventory", {}) or {}
        for p in TUTORIAL_MANDATORY:
            assert p.part_id in inventory, (
                f"Expected {p.part_id} in parts_inventory after purchase; inventory={inventory}"
            )

        shop.on_exit()

        # --- 5/6. Ship builder renders in tutorial mode ---
        builder_ui = _ui()
        builder = ShipBuilderView(ui_manager=builder_ui, player=player, data_loader=dl)
        builder._tutorial_mode = True
        builder.on_enter()
        builder.update(0.016)
        builder.render(_screen())

        # --- 7. Slot palette must surface slot types matching purchases ---
        groups = builder._get_slot_definitions_grouped()
        slot_types_shown = {st for st, _defs in groups}
        # Every purchased part's slot_type should appear (plus always-available cockpit)
        expected = {"cockpit", "engine", "reactor", "fuel", "cargo"}
        missing = expected - slot_types_shown
        assert not missing, f"palette missing slot types: {missing}"

        # --- 8. Narration returns a non-empty string for each meaningful state ---
        # 8a. Welcome — nothing placed, nothing selected
        builder._selected_slot_def_id = None
        builder._shown_rotation_tip = False
        part_narration = {
            "cockpit_scout_pod": "Cockpit narration",
            "engine_small": "Engine narration",
            "reactor_small": "Reactor narration",
            "fuel_small": "Fuel narration",
            "cargo_small": "Cargo narration",
        }
        welcome = builder._pick_tutorial_narration(set(), part_narration, TUTORIAL_PARTS)
        assert welcome and isinstance(welcome, str)

        # 8b. Per-part: cockpit placed, engine pending → engine narration
        per_part = builder._pick_tutorial_narration(
            {"cockpit_scout_pod"}, part_narration, TUTORIAL_PARTS
        )
        assert per_part == "Engine narration", (
            f"Expected engine narration after placing cockpit; got {per_part!r}"
        )

        # 8c. Completion: every purchased slot_type has a slot placed
        fully_placed = {
            "cockpit_scout_pod",
            "engine_small",
            "reactor_small",
            "fuel_small",
            "cargo_small",
        }
        completion = builder._pick_tutorial_narration(fully_placed, part_narration, TUTORIAL_PARTS)
        assert "confirm build" in completion.lower()

        # --- 9. Lifecycle teardown clean ---
        builder.on_exit()
