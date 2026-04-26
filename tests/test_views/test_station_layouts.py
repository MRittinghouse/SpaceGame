"""Tests for spacegame.views.station_layouts.

SL-1 (station_legibility.md): `unique`-typed locations demote to a POI
footer strip unless the system is mission-relevant, in which case they
stay in the main action grid alongside other locations.

These tests are layout-agnostic: they construct each of the five faction
layout subclasses and assert the same demotion behavior. Visual rendering
is covered by the subprocess bounds harness (test_subprocess_bounds.py).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pygame
import pytest

from spacegame.models.location import Location
from spacegame.views.station_layouts import (
    CollectiveRadialLayout,
    FrontierScatteredLayout,
    GuildDeckLayout,
    ReachDarkLayout,
    StationLayout,
    UnionBlueprintLayout,
)

# Each subclass paired with a system_id whose faction matches the layout
# (see SYSTEM_LAYOUT_MAP in station_layouts.py). Parametrized over the
# layout/system pair so every subclass exercises the same demotion rules.
_LAYOUTS_AND_SYSTEMS: list[tuple[type[StationLayout], str]] = [
    (GuildDeckLayout, "nexus_prime"),
    (UnionBlueprintLayout, "breakstone"),
    (CollectiveRadialLayout, "axiom_labs"),
    (FrontierScatteredLayout, "havens_rest"),
    (ReachDarkLayout, "crimson_reach"),
]


@pytest.fixture(autouse=True, scope="module")
def _pygame_init():
    """station_layouts uses pygame fonts and surfaces. Init once per module."""
    pygame.init()
    pygame.display.set_mode((1, 1), pygame.HIDDEN)
    yield
    pygame.quit()


def _make_location(loc_id: str, loc_type: str, system_id: str) -> Location:
    """Build a minimal Location for layout tests."""
    return Location(
        id=loc_id,
        name=f"Test {loc_id}",
        location_type=loc_type,
        description=f"Test {loc_type} description",
        flavor_text="",
        system_id=system_id,
    )


def _stub_sprite_mgr() -> MagicMock:
    """sprite_mgr stub that returns None for every icon request."""
    mgr = MagicMock()
    mgr.get_location_icon.return_value = None
    return mgr


def _location_ids_in(zones: list) -> set[str]:
    """Extract location IDs from a list of StationZone."""
    return {z.location.id for z in zones}


@pytest.mark.parametrize("layout_cls, system_id", _LAYOUTS_AND_SYSTEMS)
class TestUniqueDemotion:
    """When the system has no active mission, `unique` cards demote to the strip."""

    def test_unique_card_demotes_to_strip_when_no_mission(self, layout_cls, system_id) -> None:
        """A unique-typed location with no elevation lands in poi_zones, not zones."""
        market = _make_location("test_market", "market", system_id)
        unique = _make_location("test_lore", "unique", system_id)
        layout = layout_cls([market, unique], system_id, elevated_location_ids=set())
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        grid_ids = _location_ids_in(layout.zones)
        strip_ids = _location_ids_in(layout.poi_zones)

        assert "test_market" in grid_ids, "Non-unique cards should stay in the action grid"
        assert "test_lore" not in grid_ids, "Lore-only unique cards must not appear in the grid"
        assert "test_lore" in strip_ids, "Demoted unique cards must appear in the POI strip"

    def test_unique_card_stays_in_grid_when_elevated(self, layout_cls, system_id) -> None:
        """When the system is mission-relevant, unique cards stay in the action grid."""
        market = _make_location("test_market", "market", system_id)
        unique = _make_location("test_lore", "unique", system_id)
        layout = layout_cls([market, unique], system_id, elevated_location_ids={"test_lore"})
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        grid_ids = _location_ids_in(layout.zones)
        strip_ids = _location_ids_in(layout.poi_zones)

        assert "test_lore" in grid_ids, "Mission-relevant unique cards stay in the action grid"
        assert "test_lore" not in strip_ids, (
            "Elevated unique cards must not duplicate to the POI strip"
        )

    def test_non_unique_cards_never_demote(self, layout_cls, system_id) -> None:
        """market, repair, cantina, etc. always stay in the action grid."""
        locations = [
            _make_location("test_market", "market", system_id),
            _make_location("test_repair", "repair_bay", system_id),
            _make_location("test_cantina", "cantina", system_id),
        ]
        layout = layout_cls(locations, system_id, elevated_location_ids=set())
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        grid_ids = _location_ids_in(layout.zones)
        strip_ids = _location_ids_in(layout.poi_zones)

        assert grid_ids == {"test_market", "test_repair", "test_cantina"}
        assert strip_ids == set()


@pytest.mark.parametrize("layout_cls, system_id", _LAYOUTS_AND_SYSTEMS)
class TestStripInteraction:
    """POI strip zones participate in hover/click resolution alongside grid zones."""

    def test_get_clicked_zone_finds_strip_zones(self, layout_cls, system_id) -> None:
        """Clicking on a POI strip zone returns it from get_clicked_zone."""
        unique = _make_location("test_lore", "unique", system_id)
        layout = layout_cls([unique], system_id, elevated_location_ids=set())
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        assert layout.poi_zones, "Test setup: strip should have at least one zone"
        strip_zone = layout.poi_zones[0]
        click_pt = strip_zone.rect.center

        clicked = layout.get_clicked_zone(click_pt)
        assert clicked is strip_zone

    def test_handle_hover_marks_strip_zone_hovered(self, layout_cls, system_id) -> None:
        """Hovering over a POI strip zone sets its hovered flag."""
        unique = _make_location("test_lore", "unique", system_id)
        layout = layout_cls([unique], system_id, elevated_location_ids=set())
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        assert layout.poi_zones, "Test setup: strip should have at least one zone"
        strip_zone = layout.poi_zones[0]
        hover_pt = strip_zone.rect.center

        layout.handle_hover(hover_pt)
        assert strip_zone.hovered is True


@pytest.mark.parametrize("layout_cls, system_id", _LAYOUTS_AND_SYSTEMS)
class TestBackwardCompatibility:
    """Layouts must still work when elevated_location_ids is not provided."""

    def test_default_argument_treats_all_uniques_as_strip_bound(
        self, layout_cls, system_id
    ) -> None:
        """Omitting elevated_location_ids demotes all unique cards (default behavior)."""
        market = _make_location("test_market", "market", system_id)
        unique = _make_location("test_lore", "unique", system_id)
        # No elevated_location_ids passed at all.
        layout = layout_cls([market, unique], system_id)
        layout.build_zones(_stub_sprite_mgr())
        layout.build_strip_zones(_stub_sprite_mgr())

        assert "test_lore" not in _location_ids_in(layout.zones)
        assert "test_lore" in _location_ids_in(layout.poi_zones)
