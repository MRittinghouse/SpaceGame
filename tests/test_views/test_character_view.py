"""Tests for character view — faction emblem rendering."""

import pytest

pygame = pytest.importorskip("pygame", reason="pygame required for view tests")
pygame_gui = pytest.importorskip("pygame_gui", reason="pygame_gui required")

from spacegame.config import WINDOW_WIDTH, WINDOW_HEIGHT  # noqa: E402
from spacegame.models.player import Player  # noqa: E402
from spacegame.models.ship import Ship, ShipType  # noqa: E402
from spacegame.models.attributes import AttributeSheet  # noqa: E402
from spacegame.views.character_view import CharacterView  # noqa: E402


@pytest.fixture(autouse=True, scope="module")
def _init_pygame():
    """Initialize pygame once for all view tests in this module."""
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    yield
    pygame.quit()


def _make_ship_type() -> ShipType:
    return ShipType(
        id="shuttle",
        name="Shuttle",
        ship_class="light",
        description="Basic ship",
        cargo_capacity=100,
        fuel_capacity=50,
        fuel_efficiency=1.0,
        speed_multiplier=1.0,
        purchase_price=0,
        resale_value=0,
        crew_slots=1,
        special_abilities=[],
        availability="all",
    )


def _make_player() -> Player:
    return Player(
        name="TestCaptain",
        credits=5000,
        current_system_id="nexus_prime",
        ship=Ship(ship_type=_make_ship_type(), current_fuel=50),
    )


class TestFactionEmblems:
    """Tests for faction emblem rendering in character view."""

    def test_sprite_manager_initialized(self) -> None:
        """Character view should have a sprite manager after init."""
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        player = _make_player()
        attr_sheet = AttributeSheet()
        view = CharacterView(ui_manager, player, attr_sheet)
        assert hasattr(view, "_sprite_mgr")
        assert view._sprite_mgr is not None

    def test_render_faction_perks_with_reputation(self) -> None:
        """Rendering faction perks with reputation data should not crash."""
        ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
        player = _make_player()
        player.faction_reputation = {
            "commerce_guild": 25,
            "miners_union": -10,
        }
        attr_sheet = AttributeSheet()
        view = CharacterView(
            ui_manager, player, attr_sheet, politics_manager=None
        )
        view.on_enter()
        screen = pygame.display.get_surface()
        view.render(screen)
        view.on_exit()
