"""View smoke-test harness (QA Pass 4).

Provides:
  - pygame + display initialization (module-scoped so pytest fixtures reuse)
  - A fresh ``UIManager`` per test (isolates UI element counts)
  - Factory functions that construct every view with realistic minimal args
  - A generic ``run_lifecycle`` helper that drives the view through its full
    lifecycle (on_enter → update → render → on_exit) and asserts no leaked
    pygame_gui elements

Each view that can be instantiated headlessly gets a registered factory.
Factories that need extra managers (MissionManager, CrewRoster, etc.)
construct them from the real DataLoader.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

# Headless SDL before pygame imports.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pygame_gui

from spacegame.config import WINDOW_HEIGHT, WINDOW_WIDTH
from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.views.base_view import BaseView

# ---------------------------------------------------------------------------
# Pygame + display init (idempotent)
# ---------------------------------------------------------------------------


def ensure_pygame() -> None:
    """Initialize pygame + display, tolerant of upstream ``pygame.quit()`` calls.

    Some other test modules in the suite call ``pygame.quit()`` in their
    teardown. If that happens between our tests, pygame_gui's font
    dictionary starts throwing FileNotFoundError for its bundled NotoSans
    font when we next create a UIManager. The fix is to check pygame's
    actual init state every time rather than trusting a one-shot flag.
    """
    if not pygame.get_init():
        pygame.init()
    # Display surface may have been lost across a quit cycle.
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))


def fresh_ui_manager() -> pygame_gui.UIManager:
    """Return a fresh UIManager — each test gets its own to isolate element counts."""
    ensure_pygame()
    return pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))


def fresh_screen() -> pygame.Surface:
    """A pygame.Surface for render() calls. Not the display surface."""
    ensure_pygame()
    return pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))


# ---------------------------------------------------------------------------
# Shared fixtures: real Player, real managers
# ---------------------------------------------------------------------------


def smoke_player() -> Player:
    """A realistic mid-game player for smoke tests.

    Has some credits, a shuttle ship, progression unlocked, and dialogue
    flags set so view branches that gate on "has met X" don't bail early.
    """
    dl = get_data_loader()
    dl.load_all()
    ship = Ship(ship_type=dl.ship_types["shuttle"], current_fuel=40)
    player = Player(
        name="SmokeTester",
        credits=5000,
        current_system_id="nexus_prime",
        ship=ship,
    )
    player.faction_reputation = {
        "commerce_guild": 25,
        "miners_union": 10,
    }
    player.faction_assignments = {"nexus_prime": "commerce_guild"}
    return player


def smoke_mission_manager():
    from spacegame.models.mission import MissionManager

    dl = get_data_loader()
    dl.load_all()
    return MissionManager(dl.missions)


def smoke_crew_roster():
    from spacegame.models.crew import CrewRoster

    dl = get_data_loader()
    dl.load_all()
    return CrewRoster(templates=dl.crew_templates)


def smoke_achievement_manager():
    from spacegame.achievement_manager import AchievementManager

    dl = get_data_loader()
    dl.load_all()
    # dl.achievements is already a list, not a dict.
    return AchievementManager(achievements=list(dl.achievements))


def smoke_activity_registry():
    from spacegame.engine.activity_registry import ActivityRegistry

    return ActivityRegistry()


def smoke_politics_manager():
    from spacegame.models.politics import PoliticsManager

    dl = get_data_loader()
    dl.load_all()
    mgr = PoliticsManager(
        relationships=dl.faction_relationships,
        factions=dl.factions,
    )
    mgr.set_faction_perks(dl.faction_perks)
    return mgr


def smoke_save_manager():
    from spacegame.save_manager import SaveManager

    return SaveManager()


def smoke_dialogue_manager():
    from spacegame.models.dialogue import DialogueManager

    return DialogueManager()


# ---------------------------------------------------------------------------
# Lifecycle driver
# ---------------------------------------------------------------------------


@dataclass
class LifecycleResult:
    """Diagnostics from a full lifecycle walk."""

    ui_elements_before: int
    ui_elements_after_enter: int
    ui_elements_after_exit: int
    exception: Exception | None = None


def run_lifecycle(
    view: BaseView,
    ui_manager: pygame_gui.UIManager,
    *,
    update_seconds: float = 0.1,
    render_frames: int = 1,
) -> LifecycleResult:
    """Drive a view through its full lifecycle.

    1. count UI elements baseline
    2. on_enter()
    3. update(dt) × render_frames
    4. render(screen) × render_frames
    5. on_exit()
    6. assert no leaked UI elements

    Returns a LifecycleResult for richer assertions in the test.
    """
    screen = fresh_screen()
    before = len(ui_manager.get_root_container().elements)

    try:
        view.on_enter()
        after_enter = len(ui_manager.get_root_container().elements)
        for _ in range(render_frames):
            view.update(update_seconds)
            view.render(screen)
        view.on_exit()
        after_exit = len(ui_manager.get_root_container().elements)
        return LifecycleResult(
            ui_elements_before=before,
            ui_elements_after_enter=after_enter,
            ui_elements_after_exit=after_exit,
        )
    except Exception as exc:
        return LifecycleResult(
            ui_elements_before=before,
            ui_elements_after_enter=-1,
            ui_elements_after_exit=-1,
            exception=exc,
        )


# ---------------------------------------------------------------------------
# View factory registry
# ---------------------------------------------------------------------------


ViewFactory = Callable[[pygame_gui.UIManager], BaseView]


def _main_menu_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.main_menu_view import MainMenuView

    return MainMenuView(ui_manager=ui, save_manager=smoke_save_manager())


def _crew_roster_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.crew_roster_view import CrewRosterView

    return CrewRosterView(
        ui_manager=ui,
        crew_roster=smoke_crew_roster(),
        crew_slots=4,
    )


def _mission_log_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.mission_log_view import MissionLogView

    dl = get_data_loader()
    dl.load_all()
    return MissionLogView(
        ui_manager=ui,
        mission_manager=smoke_mission_manager(),
        data_loader=dl,
        player=smoke_player(),
    )


def _skill_tree_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.skill_tree_view import SkillTreeView

    player = smoke_player()
    return SkillTreeView(
        ui_manager=ui,
        progression=player.progression,
        player=player,
    )


def _achievements_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.achievements_view import AchievementsView

    return AchievementsView(
        ui_manager=ui,
        player=smoke_player(),
        achievement_manager=smoke_achievement_manager(),
    )


def _dialogue_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.dialogue_view import DialogueView

    dl = get_data_loader()
    dl.load_all()
    return DialogueView(
        ui_manager=ui,
        dialogue_manager=smoke_dialogue_manager(),
        data_loader=dl,
    )


def _ship_builder_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.ship_builder_view import ShipBuilderView

    dl = get_data_loader()
    dl.load_all()
    return ShipBuilderView(ui_manager=ui, player=smoke_player(), data_loader=dl)


def _shipyard_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.models.upgrades import ShipUpgradeManager
    from spacegame.views.shipyard_view import ShipyardView

    dl = get_data_loader()
    dl.load_all()
    return ShipyardView(
        ui_manager=ui,
        player=smoke_player(),
        all_upgrades=dl.upgrades,
        upgrade_manager=ShipUpgradeManager(),
        all_ship_types=dl.ship_types,
    )


def _character_creation_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.models.attributes import AttributeSheet
    from spacegame.views.character_creation_view import CharacterCreationView

    return CharacterCreationView(ui_manager=ui, attribute_sheet=AttributeSheet())


def _event_notification_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.models.event import EventType, MarketEvent
    from spacegame.views.event_notification_view import EventNotificationView

    event = MarketEvent(
        event_type=EventType.SHORTAGE,
        commodity_id="metals",
        system_id="nexus_prime",
        price_multiplier=2.0,
        duration_days=5,
        day_started=1,
        description="A smoke-test market event",
    )
    return EventNotificationView(ui_manager=ui, event=event)


def _tutorial_shop_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.tutorial_shop_view import TutorialShopView

    dl = get_data_loader()
    dl.load_all()
    return TutorialShopView(ui_manager=ui, player=smoke_player(), data_loader=dl)


def _cantina_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.cantina_view import CantinaView

    dl = get_data_loader()
    dl.load_all()
    system = dl.systems["nexus_prime"]
    locations = dl.locations.get("nexus_prime", [])
    location = next(
        (loc for loc in locations if loc.location_type == "cantina"),
        locations[0] if locations else None,
    )
    return CantinaView(
        ui_manager=ui,
        player=smoke_player(),
        system=system,
        location=location,
        data_loader=dl,
        crew_roster=smoke_crew_roster(),
        mission_manager=smoke_mission_manager(),
    )


def _station_hub_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.station_hub_view import StationHubView

    dl = get_data_loader()
    dl.load_all()
    system = dl.systems["nexus_prime"]
    locations = dl.locations.get("nexus_prime", [])
    return StationHubView(
        ui_manager=ui,
        player=smoke_player(),
        system=system,
        locations=locations,
        activity_registry=smoke_activity_registry(),
        data_loader=dl,
        politics_manager=smoke_politics_manager(),
        crew_roster=smoke_crew_roster(),
        mission_manager=smoke_mission_manager(),
    )


# Sprint 3a additions: factories for the three YELLOW-risk views that Sprint 1
# flagged for overlap and layout concerns at non-base resolutions.


def _character_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.models.attributes import AttributeSheet
    from spacegame.views.character_view import CharacterView

    return CharacterView(
        ui_manager=ui,
        player=smoke_player(),
        attribute_sheet=AttributeSheet(),
        politics_manager=smoke_politics_manager(),
    )


def _galaxy_map_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.views.galaxy_map_view import GalaxyMapView

    dl = get_data_loader()
    dl.load_all()
    return GalaxyMapView(
        ui_manager=ui,
        player=smoke_player(),
        systems=dl.systems,
        politics_manager=smoke_politics_manager(),
    )


def _ground_briefing_view(ui: pygame_gui.UIManager) -> BaseView:
    from spacegame.models.ground_mapgen import DifficultyTier, MissionType
    from spacegame.models.ground_mission import (
        GroundMissionConfig,
        GroundMissionRewards,
    )
    from spacegame.views.ground_briefing_view import GroundBriefingView

    config = GroundMissionConfig(
        id="smoke_ground_01",
        name="Smoke Test Run",
        description="Infiltrate the facility.",
        mission_type=MissionType.INFILTRATION,
        difficulty=DifficultyTier.LOW,
        faction_id="commerce_guild",
        objectives=["Reach the exit"],
        intel_hints=[],
        rewards=GroundMissionRewards(credits=500, xp=25, crew_xp=10),
        max_crew=2,
        seed=42,
    )
    return GroundBriefingView(
        ui_manager=ui,
        mission_config=config,
        crew_roster=smoke_crew_roster(),
        skill_levels={},
    )


VIEW_FACTORIES: dict[str, ViewFactory] = {
    # Tier D (0% coverage per Pass 1 audit)
    "main_menu": _main_menu_view,
    "crew_roster": _crew_roster_view,
    "mission_log": _mission_log_view,
    "skill_tree": _skill_tree_view,
    "achievements": _achievements_view,
    "dialogue": _dialogue_view,
    "ship_builder": _ship_builder_view,
    "shipyard": _shipyard_view,
    "character_creation": _character_creation_view,
    "event_notification": _event_notification_view,
    "tutorial_shop": _tutorial_shop_view,
    # Tier C (low but non-zero coverage)
    "cantina": _cantina_view,
    "station_hub": _station_hub_view,
    # Sprint 3a additions — YELLOW-risk views needing resolution-matrix coverage
    "character": _character_view,
    "galaxy_map": _galaxy_map_view,
    "ground_briefing": _ground_briefing_view,
}


def view_factory(name: str) -> ViewFactory:
    if name not in VIEW_FACTORIES:
        raise KeyError(f"View factory '{name}' not registered")
    return VIEW_FACTORIES[name]


def all_view_names() -> list[str]:
    return sorted(VIEW_FACTORIES)


__all__ = [
    "VIEW_FACTORIES",
    "LifecycleResult",
    "all_view_names",
    "ensure_pygame",
    "fresh_screen",
    "fresh_ui_manager",
    "run_lifecycle",
    "smoke_player",
    "view_factory",
]
