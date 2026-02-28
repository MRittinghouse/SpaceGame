"""
Main game engine class.

Manages the core game loop, initialization, and high-level game control.
"""

import pygame
import pygame_gui
import sys
from typing import Optional
from spacegame.config import (
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS_TARGET,
    FULLSCREEN,
    VSYNC,
    Colors,
    GameState,
)
from spacegame.engine.state_manager import StateManager
from spacegame.engine.input_handler import InputHandler
from spacegame.engine.activity_registry import create_default_registry
from spacegame.engine.transitions import TransitionManager, TransitionType
from spacegame.engine.screen_effects import Vignette, ScreenShake
from spacegame.data_loader import get_data_loader
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.models.event import EventGenerator
from spacegame.models.market import Market
from spacegame.models.faction import generate_faction_assignments
from spacegame.achievement_manager import AchievementManager
from spacegame.tutorial_manager import TutorialManager
from spacegame.save_manager import SaveManager
from spacegame.utils.logger import logger
import time


class Game:
    """
    Main game class that manages the game loop and core systems.

    This is the entry point for the entire game, responsible for:
    - Initializing PyGame
    - Managing the main game loop
    - Coordinating state management and input handling
    - Rendering and updates
    """

    def __init__(self) -> None:
        """Initialize the game engine."""
        logger.info("Initializing Space Trader game...")

        # Initialize PyGame
        pygame.init()

        # Create window
        flags = pygame.SCALED
        if FULLSCREEN:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), flags=flags, vsync=1 if VSYNC else 0
        )
        pygame.display.set_caption(WINDOW_TITLE)

        # Core systems
        self.clock = pygame.time.Clock()
        self.running = False
        self.state_manager = StateManager()
        self.input_handler = InputHandler()

        # pygame_gui UI manager with custom theme
        from spacegame.config import DATA_DIR

        theme_path = DATA_DIR / "theme.json"
        if theme_path.exists():
            self.ui_manager = pygame_gui.UIManager(
                (WINDOW_WIDTH, WINDOW_HEIGHT), theme_path=str(theme_path)
            )
            logger.info(f"Loaded UI theme from {theme_path}")
        else:
            self.ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
            logger.info("No theme.json found, using default pygame_gui theme")

        # Game data
        self.data_loader = get_data_loader()
        self.player: Optional[Player] = None

        # Event generator (initialized after data is loaded)
        self.event_generator: Optional[EventGenerator] = None
        self.active_events: dict[str, "MarketEvent"] = {}  # system_id -> active event

        # Event display state
        self.pending_event_notification: Optional["MarketEvent"] = None
        self.event_log: list[dict] = []  # Last 15 events
        self.event_banner: str = ""
        self.event_banner_timer: float = 0.0
        self._event_notification_view = None

        # Banner font (created lazily to avoid pygame init order issues)
        self._banner_font: Optional[pygame.font.Font] = None

        # Save/Load system
        self.save_manager = SaveManager()
        self.playtime_start = time.time()
        self.total_playtime_seconds = 0

        # Markets (system_id -> Market)
        self.markets: dict[str, Market] = {}

        # Activity registry
        self.activity_registry = create_default_registry()

        # Achievement system
        self.achievement_manager = AchievementManager(self.data_loader.achievements)

        # Achievement notification queue
        self._achievement_notifications: list[str] = []
        self._achievement_notify_timer: float = 0.0
        self._current_achievement_msg: str = ""

        # Tutorial system
        self.tutorial_manager = TutorialManager()
        self._tutorial_overlay = None

        # Pause menu state
        self.paused = False
        self.pause_menu_view = None
        self.save_load_view = None
        self.settings_view = None

        # Visual effects
        self.transition_manager = TransitionManager()
        self.vignette = Vignette(WINDOW_WIDTH, WINDOW_HEIGHT, intensity=0.5)
        self.screen_shake = ScreenShake()

        # View references (for state transitions)
        self.main_menu_view = None
        self.galaxy_map_view = None
        self.trading_view = None
        self.mining_view = None
        self.salvage_view = None
        self.refining_view = None
        self.skill_tree_view = None
        self.shipyard_view = None
        self.statistics_view = None
        self.achievements_view = None
        self.dialogue_view = None
        self.name_input_view = None

        # Dialogue system
        from spacegame.models.dialogue import DialogueManager

        self.dialogue_manager = DialogueManager()
        self._last_dialogue_npc_id: Optional[str] = None

        # Mission system
        from spacegame.models.mission import MissionManager

        self.mission_manager: Optional[MissionManager] = None
        self.mission_log_view = None

        # Mission notification queue
        self._mission_notifications: list[str] = []
        self._mission_notify_timer: float = 0.0
        self._current_mission_msg: str = ""

        # Crew system
        from spacegame.models.crew import CrewRoster

        self.crew_roster: Optional[CrewRoster] = None
        self.crew_roster_view = None
        self._crew_last_trades: int = 0
        self._crew_last_jumps: int = 0

        logger.info(f"Window created: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        logger.info(f"Target FPS: {FPS_TARGET}")

    def initialize_new_game(self, player_name: str = "Captain") -> None:
        """Initialize a new game with starting conditions.

        Args:
            player_name: Name chosen by the player.
        """
        logger.info("Initializing new game...")

        # Create player with starting ship
        shuttle_type = self.data_loader.get_ship_type("shuttle")
        starting_ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)

        self.player = Player(
            name=player_name, credits=2000, current_system_id="nexus_prime", ship=starting_ship
        )

        logger.info(f"Player created: {self.player.name} at {self.player.current_system_id}")
        logger.info(f"Starting credits: {self.player.credits} CR")

        # Generate random faction assignments
        faction_ids = [f.id for f in self.data_loader.get_all_factions()]
        system_ids = [s.id for s in self.data_loader.get_all_systems()]
        if faction_ids:
            self.player.faction_assignments = generate_faction_assignments(system_ids, faction_ids)
            self.player.faction_reputation = {fid: 0 for fid in faction_ids}
            self._apply_faction_assignments()

        # Initialize event generator
        commodity_ids = [c.id for c in self.data_loader.get_all_commodities()]
        system_ids = [s.id for s in self.data_loader.get_all_systems()]
        self.event_generator = EventGenerator(commodity_ids, system_ids)

        # Start tutorial for new game
        self.tutorial_manager.reset_tutorial()

        # Initialize mission system
        from spacegame.models.mission import MissionManager

        self.mission_manager = MissionManager(self.data_loader.missions)
        self.mission_manager.update_availability()

        # Auto-start campaign mission: bill of landing
        self.mission_manager.accept_mission("bill_of_landing")

        # Initialize crew system
        from spacegame.models.crew import CrewRoster

        self.crew_roster = CrewRoster(self.data_loader.crew_templates)
        self.player.ship.set_crew_roster(self.crew_roster)
        self._crew_last_trades = 0
        self._crew_last_jumps = 0

    def _apply_faction_assignments(self) -> None:
        """Apply faction assignments to star system objects.

        Sets each system's faction field to the assigned faction's display name.
        Called after new game creation and game loading.
        """
        if not self.player or not self.player.faction_assignments:
            return
        for system_id, faction_id in self.player.faction_assignments.items():
            system = self.data_loader.systems.get(system_id)
            faction = self.data_loader.get_faction(faction_id)
            if system and faction:
                system.faction = faction.name

    def try_generate_market_event(self) -> None:
        """Try to generate a random market event for a system."""
        if not self.event_generator or not self.player:
            return

        # Get commodity names for event descriptions
        commodity_names = {c.id: c.name for c in self.data_loader.get_all_commodities()}

        # Try to generate event
        event = self.event_generator.try_generate_event(self.player.game_day, commodity_names)

        if event:
            logger.info(f"Market event generated: {event.description} at {event.system_id}")
            # Store event for this system
            self.active_events[event.system_id] = event

            # Add to event log (max 15 entries)
            self.event_log.append(
                {
                    "event_type": event.event_type.value,
                    "commodity": event.commodity_id,
                    "system": event.system_id,
                    "day": event.day_started,
                    "description": event.description,
                }
            )
            if len(self.event_log) > 15:
                self.event_log.pop(0)

            # Set notification based on event type
            from spacegame.models.event import EventType

            if event.event_type == EventType.DISASTER:
                self.pending_event_notification = event
            else:
                self.event_banner = event.description
                self.event_banner_timer = 5.0

            return event
        return None

    def initialize_states(self) -> None:
        """Register all game states."""
        from spacegame.views.main_menu_view import MainMenuView
        from spacegame.views.galaxy_map_view import GalaxyMapView
        from spacegame.views.trading_view import TradingView
        from spacegame.views.mining_view import MiningView

        # Create views
        self.main_menu_view = MainMenuView(self.ui_manager, self.save_manager)

        # Register main menu
        self.state_manager.register_state(GameState.MAIN_MENU, self.main_menu_view)
        self.state_manager.change_state(GameState.MAIN_MENU)

        logger.info("Game states initialized")

    def _start_transition(self, transition_type: TransitionType, duration: float, callback) -> None:
        """Start a visual transition then execute callback at midpoint."""
        if self.transition_manager.active:
            # Skip transition if one is already in progress, just do the swap
            callback()
            return
        old_surface = self.screen.copy()
        self.transition_manager.start(transition_type, duration, callback, old_surface)

    def _handle_state_transitions(self) -> None:
        """Check for and handle state transitions."""
        # Don't process new transitions while one is active
        if self.transition_manager.active:
            return

        # Check main menu for transitions
        if self.main_menu_view and self.main_menu_view.active:
            next_state = self.main_menu_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.main_menu_view.next_state = None

                def _do():
                    if not self.player:
                        # New game: go to name input first
                        self._ensure_name_input_view()
                        self.state_manager.change_state(GameState.NAME_INPUT)
                    else:
                        self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.5, _do)
            elif next_state == "continue":
                self.main_menu_view.next_state = None
                slot = self.save_manager.get_most_recent_save_slot()
                if slot is not None:
                    self._load_game(slot)
            elif next_state == "load_game":
                self.main_menu_view.next_state = None
                self._open_load_dialog()

        # Check name input view for transitions
        if self.name_input_view and self.name_input_view.active:
            next_state = self.name_input_view.get_next_state()
            if next_state:
                self.name_input_view.next_state = None
                player_name = self.name_input_view.get_player_name()
                self.initialize_new_game(player_name)
                self._create_gameplay_views()
                self._start_intro_narration()

        # Check galaxy map for transitions
        if self.galaxy_map_view and self.galaxy_map_view.active:
            # Handle save button (not a state transition)
            if self.galaxy_map_view.save_requested:
                self.galaxy_map_view.save_requested = False
                self.auto_save()
                self._mission_notifications.append("Game Saved")

            next_state = self.galaxy_map_view.get_next_state()
            if next_state == GameState.TRADING:
                self.galaxy_map_view.next_state = None

                # Auto-trigger campaign dialogue at Nexus Prime
                if (
                    self.player
                    and self.player.current_system_id == "nexus_prime"
                    and not self.player.dialogue_flags.get("talked_to_officer_larsen", False)
                ):
                    self.start_dialogue("officer_larsen")
                    return

                def _do():
                    self.auto_save()
                    self.state_manager.change_state(GameState.TRADING)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.SKILL_TREE:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_skill_tree_view()
                    self.state_manager.change_state(GameState.SKILL_TREE)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.SHIPYARD:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_shipyard_view()
                    self.state_manager.change_state(GameState.SHIPYARD)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.STATISTICS:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_statistics_view()
                    self.state_manager.change_state(GameState.STATISTICS)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.ACHIEVEMENTS:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_achievements_view()
                    self.state_manager.change_state(GameState.ACHIEVEMENTS)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.MAIN_MENU:
                self.galaxy_map_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.MAIN_MENU)

                self._start_transition(TransitionType.FADE, 0.5, _do)
            elif next_state == GameState.MISSION_LOG:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_mission_log_view()
                    self.state_manager.change_state(GameState.MISSION_LOG)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.CREW_ROSTER:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_crew_roster_view()
                    self.state_manager.change_state(GameState.CREW_ROSTER)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check crew roster view for transitions
        if self.crew_roster_view and self.crew_roster_view.active:
            next_state = self.crew_roster_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.crew_roster_view.next_state = None

                # Handle pending dismiss
                dismiss_id = getattr(self.crew_roster_view, "pending_dismiss_id", None)
                if dismiss_id and self.crew_roster:
                    self.crew_roster_view.pending_dismiss_id = None
                    success, msg = self.crew_roster.dismiss(dismiss_id)
                    if success:
                        self._mission_notifications.append(f"Crew Dismissed: {msg}")

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check mission log view for transitions
        if self.mission_log_view and self.mission_log_view.active:
            next_state = self.mission_log_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.mission_log_view.next_state = None

                # Handle pending mission accept
                accept_id = getattr(self.mission_log_view, "pending_accept_id", None)
                if accept_id and self.mission_manager:
                    self.mission_log_view.pending_accept_id = None
                    success, msg = self.mission_manager.accept_mission(accept_id)
                    if success:
                        mission = self.mission_manager.get_mission(accept_id)
                        name = mission.name if mission else accept_id
                        # Grant on-accept cargo
                        if mission and self.player:
                            for cargo in mission.on_accept_cargo:
                                self.player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
                                self._mission_notifications.append(
                                    f"Cargo Loaded: {cargo.quantity} {cargo.commodity_id}"
                                )
                        self._mission_notifications.append(f"Mission Accepted: {name}")

                def _do():
                    # Update galaxy map mission markers
                    if self.galaxy_map_view and self.mission_manager:
                        self.galaxy_map_view.mission_target_systems = (
                            self.mission_manager.get_active_target_systems()
                        )
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check trading view for transitions
        if self.trading_view and self.trading_view.active:
            next_state = self.trading_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.trading_view.next_state = None

                def _do():
                    self.market = None
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.MINING:
                self.trading_view.next_state = None

                def _do():
                    self._ensure_mining_view()
                    self.state_manager.change_state(GameState.MINING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)
            elif next_state == GameState.SALVAGING:
                self.trading_view.next_state = None

                def _do():
                    self._ensure_salvage_view()
                    self.state_manager.change_state(GameState.SALVAGING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)
            elif next_state == GameState.REFINING:
                self.trading_view.next_state = None

                def _do():
                    self._ensure_refining_view()
                    self.state_manager.change_state(GameState.REFINING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)
            elif next_state == GameState.DIALOGUE:
                self.trading_view.next_state = None
                npc_id = getattr(self.trading_view, "pending_npc_id", None)
                if npc_id:
                    self.trading_view.pending_npc_id = None
                    self.start_dialogue(npc_id)

        # Check dialogue view for transitions (generic — supports any return state)
        if self.dialogue_view and self.dialogue_view.active:
            next_state = self.dialogue_view.get_next_state()
            if next_state is not None:
                self.dialogue_view.next_state = None

                # Sync dialogue flags back to player for save persistence
                if self.player:
                    self.player.dialogue_flags = self.dialogue_manager.get_flags()

                    # Set talked_to flag for mission objectives
                    if self._last_dialogue_npc_id:
                        flag_key = f"talked_to_{self._last_dialogue_npc_id}"
                        self.player.dialogue_flags[flag_key] = True
                        self.dialogue_manager.set_flag(flag_key)
                        self._last_dialogue_npc_id = None

                target = next_state

                def _do():
                    self.state_manager.change_state(target)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check mining view for transitions
        if self.mining_view and self.mining_view.active:
            next_state = self.mining_view.get_next_state()
            if next_state == GameState.TRADING:
                self.mining_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.TRADING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check salvage view for transitions
        if self.salvage_view and self.salvage_view.active:
            next_state = self.salvage_view.get_next_state()
            if next_state == GameState.TRADING:
                self.salvage_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.TRADING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check refining view for transitions
        if self.refining_view and self.refining_view.active:
            next_state = self.refining_view.get_next_state()
            if next_state == GameState.TRADING:
                self.refining_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.TRADING)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check skill tree for transitions
        if self.skill_tree_view and self.skill_tree_view.active:
            next_state = self.skill_tree_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.skill_tree_view.next_state = None

                def _do():
                    # Sync drone fleet after skill tree changes
                    from spacegame.models.drone import apply_drone_skill_effects

                    apply_drone_skill_effects(self.player)
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check statistics view for transitions
        if self.statistics_view and self.statistics_view.active:
            next_state = self.statistics_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.statistics_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check achievements view for transitions
        if self.achievements_view and self.achievements_view.active:
            next_state = self.achievements_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.achievements_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check shipyard for transitions
        if self.shipyard_view and self.shipyard_view.active:
            next_state = self.shipyard_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.shipyard_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

    def _create_gameplay_views(self) -> None:
        """Create all gameplay views after new game or load."""
        from spacegame.views.galaxy_map_view import GalaxyMapView
        from spacegame.views.trading_view import TradingView

        systems = self.data_loader.systems
        commodities = self.data_loader.commodities

        self.galaxy_map_view = GalaxyMapView(
            self.ui_manager,
            self.player,
            systems,
            active_events=self.active_events,
        )
        self.trading_view = TradingView(
            self.ui_manager,
            self.player,
            systems,
            commodities,
            activity_registry=self.activity_registry,
            active_events=self.active_events,
        )

        self.state_manager.register_state(GameState.GALAXY_MAP, self.galaxy_map_view)
        self.state_manager.register_state(GameState.TRADING, self.trading_view)

        # Reset views that need per-session recreation
        self.mining_view = None
        self.salvage_view = None
        self.dialogue_view = None
        self.mission_log_view = None
        self.crew_roster_view = None
        self.refining_view = None
        self.skill_tree_view = None
        self.shipyard_view = None
        self.statistics_view = None
        self.achievements_view = None

    def _ensure_mining_view(self) -> None:
        """Create or recreate mining view for current system."""
        from spacegame.views.mining_view import MiningView

        mining_config = self.data_loader.get_mining_config(self.player.current_system_id)
        self.mining_view = MiningView(
            self.ui_manager,
            self.player,
            self.data_loader.commodities,
            mining_config=mining_config,
            progression=self.player.progression,
            drone_fleet=self.player.drone_fleet,
        )
        self.state_manager.register_state(GameState.MINING, self.mining_view)

    def _ensure_salvage_view(self) -> None:
        """Create or recreate salvage view for current system."""
        from spacegame.views.salvage_view import SalvageView

        salvage_config = self.data_loader.get_salvage_config(self.player.current_system_id)
        self.salvage_view = SalvageView(
            self.ui_manager,
            self.player,
            self.data_loader.commodities,
            salvage_config=salvage_config,
            progression=self.player.progression,
        )
        self.state_manager.register_state(GameState.SALVAGING, self.salvage_view)

    def _ensure_refining_view(self) -> None:
        """Create or recreate refining view for current system."""
        from spacegame.views.refining_view import RefiningView

        self.refining_view = RefiningView(
            self.ui_manager,
            self.player,
            self.data_loader.commodities,
            recipes=self.data_loader.recipes,
            system_id=self.player.current_system_id,
            progression=self.player.progression,
        )
        self.state_manager.register_state(GameState.REFINING, self.refining_view)

    def _ensure_skill_tree_view(self) -> None:
        """Create or recreate skill tree view."""
        from spacegame.views.skill_tree_view import SkillTreeView

        self.skill_tree_view = SkillTreeView(
            self.ui_manager,
            self.player.progression,
        )
        self.state_manager.register_state(GameState.SKILL_TREE, self.skill_tree_view)

    def _ensure_statistics_view(self) -> None:
        """Create or recreate statistics view."""
        from spacegame.views.statistics_view import StatisticsView

        self.statistics_view = StatisticsView(self.ui_manager, self.player)
        self.state_manager.register_state(GameState.STATISTICS, self.statistics_view)

    def _ensure_achievements_view(self) -> None:
        """Create or recreate achievements view."""
        from spacegame.views.achievements_view import AchievementsView

        self.achievements_view = AchievementsView(
            self.ui_manager,
            self.player,
            self.achievement_manager,
        )
        self.state_manager.register_state(GameState.ACHIEVEMENTS, self.achievements_view)

    def _ensure_dialogue_view(self) -> None:
        """Create or recreate dialogue view."""
        from spacegame.views.dialogue_view import DialogueView

        self.dialogue_view = DialogueView(self.ui_manager, self.dialogue_manager, self.data_loader)
        self.state_manager.register_state(GameState.DIALOGUE, self.dialogue_view)

    def _ensure_mission_log_view(self) -> None:
        """Create or recreate mission log view."""
        from spacegame.views.mission_log_view import MissionLogView

        self.mission_log_view = MissionLogView(self.ui_manager, self.mission_manager)
        self.state_manager.register_state(GameState.MISSION_LOG, self.mission_log_view)

    def _ensure_crew_roster_view(self) -> None:
        """Create or recreate crew roster view."""
        from spacegame.views.crew_roster_view import CrewRosterView

        crew_slots = (
            self.player.ship.ship_type.crew_slots
            + int(self.player.progression.get_bonus("crew_slot_bonus"))
            if self.player
            else 1
        )
        self.crew_roster_view = CrewRosterView(self.ui_manager, self.crew_roster, crew_slots)
        self.state_manager.register_state(GameState.CREW_ROSTER, self.crew_roster_view)

    def start_dialogue(self, npc_id: str, return_state: GameState = GameState.TRADING) -> None:
        """Start a dialogue with an NPC.

        Args:
            npc_id: ID of the NPC to talk to.
            return_state: GameState to transition to when dialogue ends.
        """
        npc = self.data_loader.get_npc(npc_id)
        if not npc:
            logger.warning(f"NPC not found: {npc_id}")
            return

        tree = self.data_loader.get_dialogue(npc.dialogue_id)
        if not tree:
            logger.warning(f"Dialogue tree not found: {npc.dialogue_id}")
            return

        # Track NPC for mission talk_to_npc objectives
        self._last_dialogue_npc_id = npc_id

        # Sync flags from player before starting
        self.dialogue_manager.load_flags(self.player.dialogue_flags)
        self.dialogue_manager.start_dialogue(tree)
        self._ensure_dialogue_view()
        self.dialogue_view._return_state = return_state

        def _do() -> None:
            self.state_manager.change_state(GameState.DIALOGUE)

        self._start_transition(TransitionType.FADE, 0.3, _do)
        logger.info(f"Starting dialogue with {npc.name}")

    def _start_intro_narration(self) -> None:
        """Start the intro backstory narration sequence after new game creation."""
        tree = self.data_loader.get_dialogue("intro_narration")
        if not tree:
            # Fallback: skip narration, go straight to galaxy map
            def _do() -> None:
                self.state_manager.change_state(GameState.GALAXY_MAP)

            self._start_transition(TransitionType.FADE, 0.5, _do)
            return

        self._last_dialogue_npc_id = None  # No NPC for narration
        self.dialogue_manager.start_dialogue(tree)
        self._ensure_dialogue_view()
        self.dialogue_view._return_state = GameState.GALAXY_MAP

        def _do() -> None:
            self.state_manager.change_state(GameState.DIALOGUE)

        self._start_transition(TransitionType.FADE, 0.5, _do)
        logger.info("Starting intro narration")

    def _ensure_name_input_view(self) -> None:
        """Create or recreate name input view."""
        from spacegame.views.name_input_view import NameInputView

        self.name_input_view = NameInputView(self.ui_manager)
        self.state_manager.register_state(GameState.NAME_INPUT, self.name_input_view)

    def _ensure_shipyard_view(self) -> None:
        """Create or recreate shipyard view."""
        from spacegame.views.shipyard_view import ShipyardView

        self.shipyard_view = ShipyardView(
            self.ui_manager,
            self.player,
            self.data_loader.upgrades,
            self.player.upgrade_manager,
        )
        self.state_manager.register_state(GameState.SHIPYARD, self.shipyard_view)

    def _open_pause_menu(self) -> None:
        """Open the pause menu."""
        from spacegame.views.pause_menu_view import PauseMenuView

        self.paused = True
        if not self.pause_menu_view:
            self.pause_menu_view = PauseMenuView(self.ui_manager)
            self.pause_menu_view.on_enter()
        logger.info("Game paused")

    def _close_pause_menu(self) -> None:
        """Close the pause menu and resume game."""
        self.paused = False
        if self.pause_menu_view:
            self.pause_menu_view.on_exit()
        logger.info("Game resumed")

    def _handle_pause_menu(self) -> None:
        """Handle pause menu actions."""
        if not self.pause_menu_view or not self.paused:
            return

        # Check if resume requested
        next_state = self.pause_menu_view.get_next_state()
        if next_state == "resume":
            self._close_pause_menu()
        elif next_state == GameState.MAIN_MENU:
            self._close_pause_menu()
            self.state_manager.change_state(GameState.MAIN_MENU)
        elif next_state == GameState.STATISTICS:
            self._close_pause_menu()
            self._ensure_statistics_view()
            self.state_manager.change_state(GameState.STATISTICS)
        elif next_state == GameState.ACHIEVEMENTS:
            self._close_pause_menu()
            self._ensure_achievements_view()
            self.state_manager.change_state(GameState.ACHIEVEMENTS)

        # Check if save dialog requested
        if self.pause_menu_view.should_show_save_dialog():
            self._open_save_dialog()

        # Check if load dialog requested
        if self.pause_menu_view.should_show_load_dialog():
            self._open_load_dialog()

        # Check if settings dialog requested
        if self.pause_menu_view.should_show_settings_dialog():
            self._open_settings_dialog()

    def _open_save_dialog(self) -> None:
        """Open save slot selection dialog."""
        from spacegame.views.save_load_view import SaveLoadView

        self.save_load_view = SaveLoadView(self.ui_manager, self.save_manager, mode="save")
        self.save_load_view.on_enter()
        logger.info("Opened save dialog")

    def _open_load_dialog(self) -> None:
        """Open load slot selection dialog."""
        from spacegame.views.save_load_view import SaveLoadView

        self.save_load_view = SaveLoadView(self.ui_manager, self.save_manager, mode="load")
        self.save_load_view.on_enter()
        logger.info("Opened load dialog")

    def _open_settings_dialog(self) -> None:
        """Open settings dialog."""
        from spacegame.views.settings_view import SettingsView

        self.settings_view = SettingsView(
            self.ui_manager,
            self.save_manager.save_dir,
            tutorial_manager=self.tutorial_manager,
        )
        self.settings_view.on_enter()
        logger.info("Opened settings dialog")

    def _handle_save_load_dialog(self) -> None:
        """Handle save/load dialog."""
        if not self.save_load_view:
            return

        # Route events to save/load view
        # (already handled in main loop event routing)

        # Check if dialog should close
        if self.save_load_view.should_close_dialog():
            # Check if save/load should execute
            if self.save_load_view.should_execute_action():
                selected_slot = self.save_load_view.get_selected_slot()
                if selected_slot is not None:
                    if self.save_load_view.mode == "save":
                        self._save_game(selected_slot)
                    else:  # load
                        self._load_game(selected_slot)

            # Close dialog
            self.save_load_view.on_exit()
            self.save_load_view = None

    def _handle_settings_dialog(self) -> None:
        """Handle settings dialog."""
        if not self.settings_view:
            return

        # Check if dialog should close
        if self.settings_view.should_close_dialog():
            # Check if settings were changed
            if self.settings_view.has_changes():
                new_save_dir = self.settings_view.get_new_save_directory()
                if new_save_dir:
                    self.save_manager = SaveManager(new_save_dir)
                    logger.info(f"Save directory changed to: {new_save_dir}")

            # Close dialog
            self.settings_view.on_exit()
            self.settings_view = None

    def _save_game(self, slot: int) -> None:
        """
        Save the current game to a slot.

        Args:
            slot: Save slot number (0-11)
        """
        if not self.player:
            logger.warning("No active game to save")
            return

        # Sync dialogue flags to player before saving
        self.player.dialogue_flags = self.dialogue_manager.get_flags()

        # Sync mission state to player before saving
        if self.mission_manager:
            self.player.mission_state = self.mission_manager.get_state()

        # Sync crew state to player before saving
        if self.crew_roster:
            self.player.crew_state = self.crew_roster.get_state()

        # Calculate total playtime
        current_playtime = time.time() - self.playtime_start
        total_playtime = self.total_playtime_seconds + int(current_playtime)

        success = self.save_manager.save_game(
            slot=slot,
            player=self.player,
            markets=self.markets,
            active_events=self.active_events,
            playtime_seconds=total_playtime,
            event_log=self.event_log,
            tutorial_state=self.tutorial_manager.to_dict(),
        )

        if success:
            logger.info(f"Game saved successfully to slot {slot}")
        else:
            logger.error(f"Failed to save game to slot {slot}")

    def _load_game(self, slot: int) -> None:
        """
        Load a game from a slot.

        Args:
            slot: Save slot number (0-11)
        """
        save_data = self.save_manager.load_game(slot)

        if not save_data:
            logger.error(f"Failed to load game from slot {slot}")
            return

        # Restore player
        self.player = save_data["player"]

        # Restore playtime
        self.total_playtime_seconds = save_data.get("playtime_seconds", 0)
        self.playtime_start = time.time()

        # Restore events, event log, and tutorial
        self.active_events = save_data.get("active_events", {})
        self.event_log = save_data.get("event_log", [])
        tutorial_data = save_data.get("tutorial", {})
        if tutorial_data:
            self.tutorial_manager = TutorialManager.from_dict(tutorial_data)

        # Recreate markets (they need to be reconstructed with current game state)
        self.markets = {}
        market_data = save_data.get("markets", {})
        for system_id, data in market_data.items():
            # Markets will be recreated when entering trading view
            # For now, just store the serialized data
            pass

        # Apply faction assignments (generate if missing from old save)
        if not self.player.faction_assignments:
            faction_ids = [f.id for f in self.data_loader.get_all_factions()]
            system_ids = [s.id for s in self.data_loader.get_all_systems()]
            if faction_ids:
                self.player.faction_assignments = generate_faction_assignments(
                    system_ids, faction_ids
                )
                self.player.faction_reputation = {fid: 0 for fid in faction_ids}
        self._apply_faction_assignments()

        # Sync dialogue flags from player
        self.dialogue_manager.load_flags(self.player.dialogue_flags)

        # Restore mission manager
        from spacegame.models.mission import MissionManager

        self.mission_manager = MissionManager(self.data_loader.missions)
        if self.player.mission_state:
            self.mission_manager.load_state(self.player.mission_state)
        else:
            self.mission_manager.update_availability()

        # Restore crew roster
        from spacegame.models.crew import CrewRoster

        self.crew_roster = CrewRoster(self.data_loader.crew_templates)
        if self.player.crew_state:
            self.crew_roster.load_state(self.player.crew_state)
        self.player.ship.set_crew_roster(self.crew_roster)
        self._crew_last_trades = self.player.trades_completed
        self._crew_last_jumps = self.player.jumps_traveled

        # Recreate gameplay views with loaded player
        self._create_gameplay_views()

        # Change to galaxy map
        self.state_manager.change_state(GameState.GALAXY_MAP)

        # Close pause menu if open
        self._close_pause_menu()

        logger.info(f"Game loaded successfully from slot {slot}")

    def auto_save(self) -> None:
        """Auto-save to slot 0."""
        if self.player:
            self._save_game(slot=0)
            logger.info("Auto-save completed")

    def _check_tutorial_triggers(self) -> None:
        """Check if a tutorial step should trigger based on current game state."""
        if not self.tutorial_manager.active or self.tutorial_manager.completed:
            return
        if self.tutorial_manager.is_showing():
            return
        if self._tutorial_overlay and self._tutorial_overlay.active:
            return

        # Determine current trigger context
        current_state = self.state_manager.current_state
        trigger = None

        if current_state == GameState.GALAXY_MAP:
            trigger = "galaxy_map"
        elif current_state == GameState.TRADING:
            trigger = "trading"
            # Check if player has completed a trade (for "after_first_trade" step)
            if self.player and self.player.trades_completed > 0:
                trigger = "after_first_trade"
        elif current_state in (GameState.MINING, GameState.SALVAGING, GameState.REFINING):
            trigger = "activity"

        # Check travel-based trigger
        if self.player and self.player.jumps_traveled > 0:
            if self.tutorial_manager.should_show_step("after_first_travel"):
                trigger = "after_first_travel"

        if trigger and self.tutorial_manager.should_show_step(trigger):
            self.tutorial_manager.start_step()
            from spacegame.views.tutorial_overlay import TutorialOverlay

            if not self._tutorial_overlay:
                self._tutorial_overlay = TutorialOverlay(self.tutorial_manager)
            self._tutorial_overlay.show()

    def check_achievements(self) -> None:
        """Check for newly unlocked achievements and queue notifications."""
        if not self.player:
            return
        newly_unlocked = self.achievement_manager.check_achievements(self.player)
        for achievement in newly_unlocked:
            reward_msg = self.achievement_manager.apply_reward(self.player, achievement)
            self._achievement_notifications.append(
                f"Achievement Unlocked: {achievement.name}! {reward_msg}"
            )

    def check_crew_xp(self) -> None:
        """Award crew XP when trades or jumps occur."""
        if not self.player or not self.crew_roster:
            return

        # Leadership skill bonuses for crew progression
        xp_bonus = int(self.player.progression.get_bonus("crew_xp_bonus"))
        loyalty_bonus = int(self.player.progression.get_bonus("crew_loyalty_bonus"))

        # Check for new trades
        current_trades = self.player.trades_completed
        if current_trades > self._crew_last_trades:
            new_trades = current_trades - self._crew_last_trades
            self._crew_last_trades = current_trades
            levelup_msgs = self.crew_roster.add_xp_to_all((5 + xp_bonus) * new_trades)
            self.crew_roster.adjust_loyalty_all((1 + loyalty_bonus) * new_trades)
            for msg in levelup_msgs:
                self._mission_notifications.append(msg)

        # Check for new jumps
        current_jumps = self.player.jumps_traveled
        if current_jumps > self._crew_last_jumps:
            new_jumps = current_jumps - self._crew_last_jumps
            self._crew_last_jumps = current_jumps
            levelup_msgs = self.crew_roster.add_xp_to_all((3 + xp_bonus) * new_jumps)
            for msg in levelup_msgs:
                self._mission_notifications.append(msg)

    def check_missions(self) -> None:
        """Check mission objectives and handle completions."""
        if not self.player or not self.mission_manager:
            return

        completed_ids = self.mission_manager.check_objectives(self.player)
        for mission_id in completed_ids:
            reward_msgs = self.mission_manager.apply_rewards(mission_id, self.player)
            mission = self.mission_manager.get_mission(mission_id)
            name = mission.name if mission else mission_id
            reward_text = ", ".join(reward_msgs) if reward_msgs else ""
            self._mission_notifications.append(f"Mission Complete: {name}! {reward_text}")
            logger.info(f"Mission completed: {name}")

            # Handle special reward types (not processed in apply_rewards)
            if mission:
                for reward in mission.rewards:
                    # Crew recruitment
                    if reward.reward_type == "crew" and reward.target_id and self.crew_roster:
                        crew_slots = self.player.ship.ship_type.crew_slots + int(
                            self.player.progression.get_bonus("crew_slot_bonus")
                        )
                        success, crew_msg = self.crew_roster.recruit(reward.target_id, crew_slots)
                        if success:
                            self._mission_notifications.append(f"Crew Joined: {crew_msg}")

                    # Trade permit
                    if reward.reward_type == "trade_permit" and reward.target_id:
                        if reward.target_id == "current_system":
                            faction_id = self.player.get_faction_for_system(
                                self.player.current_system_id
                            )
                        else:
                            faction_id = reward.target_id
                        if faction_id:
                            self.player.grant_trade_permit(faction_id)
                            dl = get_data_loader()
                            faction = dl.get_faction(faction_id)
                            fname = faction.name if faction else faction_id
                            self._mission_notifications.append(f"Trade Permit Acquired: {fname}")

            # Grant crew XP and loyalty on mission completion
            if self.crew_roster:
                levelup_msgs = self.crew_roster.add_xp_to_all(20)
                self.crew_roster.adjust_loyalty_all(5)
                for msg in levelup_msgs:
                    self._mission_notifications.append(msg)

        # Update availability (new missions may unlock from completed prereqs)
        if completed_ids:
            newly_available = self.mission_manager.update_availability()
            for mid in newly_available:
                mission = self.mission_manager.get_mission(mid)
                if mission:
                    self._mission_notifications.append(f"New Mission Available: {mission.name}")
            # Update galaxy map markers
            if self.galaxy_map_view:
                self.galaxy_map_view.mission_target_systems = (
                    self.mission_manager.get_active_target_systems()
                )

    def _handle_event_notifications(self, dt: float) -> None:
        """Handle pending event notifications and banner timer."""
        # Check if notification view was dismissed
        if self._event_notification_view and self._event_notification_view.active:
            self._event_notification_view.update(dt)
            if self._event_notification_view.is_dismissed():
                self._event_notification_view.on_exit()
                self._event_notification_view = None
            return  # Block other processing while modal is shown

        # Show pending DISASTER notification as modal
        if self.pending_event_notification:
            from spacegame.views.event_notification_view import EventNotificationView

            self._event_notification_view = EventNotificationView(
                self.ui_manager, self.pending_event_notification
            )
            self._event_notification_view.on_enter()
            self.pending_event_notification = None
            return

        # Update banner timer
        if self.event_banner_timer > 0:
            self.event_banner_timer = max(0.0, self.event_banner_timer - dt)

    def _render_event_banner(self, screen: pygame.Surface) -> None:
        """Render non-blocking event banner at top-center of screen."""
        if self.event_banner_timer <= 0 or not self.event_banner:
            return

        if self._banner_font is None:
            self._banner_font = pygame.font.Font(None, 24)

        # Fade out in last second
        alpha = 255
        if self.event_banner_timer < 1.0:
            alpha = int(255 * self.event_banner_timer)

        # Background bar
        banner_height = 32
        banner_surf = pygame.Surface((WINDOW_WIDTH, banner_height), pygame.SRCALPHA)
        banner_surf.fill((40, 20, 10, min(200, alpha)))
        screen.blit(banner_surf, (0, 0))

        # Border line
        border_surf = pygame.Surface((WINDOW_WIDTH, 2), pygame.SRCALPHA)
        border_surf.fill((*Colors.YELLOW, alpha))
        screen.blit(border_surf, (0, banner_height - 2))

        # Text
        text_surf = self._banner_font.render(f"EVENT: {self.event_banner}", True, Colors.YELLOW)
        text_surf.set_alpha(alpha)
        text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, banner_height // 2))
        screen.blit(text_surf, text_rect)

    def _render_achievement_notification(self, screen: pygame.Surface) -> None:
        """Render achievement unlock notification at top of screen."""
        if not self._achievement_notifications:
            return

        if self._achievement_notify_timer <= 0:
            if self._achievement_notifications:
                self._current_achievement_msg = self._achievement_notifications.pop(0)
                self._achievement_notify_timer = 4.0

        if self._achievement_notify_timer <= 0:
            return

        if self._banner_font is None:
            self._banner_font = pygame.font.Font(None, 24)

        msg = getattr(self, "_current_achievement_msg", "")
        if not msg:
            return

        alpha = 255
        if self._achievement_notify_timer < 1.0:
            alpha = int(255 * self._achievement_notify_timer)

        banner_y = 34 if self.event_banner_timer > 0 else 0
        banner_height = 32
        banner_surf = pygame.Surface((WINDOW_WIDTH, banner_height), pygame.SRCALPHA)
        banner_surf.fill((10, 30, 10, min(200, alpha)))
        screen.blit(banner_surf, (0, banner_y))

        border_surf = pygame.Surface((WINDOW_WIDTH, 2), pygame.SRCALPHA)
        border_surf.fill((*Colors.GREEN, alpha))
        screen.blit(border_surf, (0, banner_y + banner_height - 2))

        text_surf = self._banner_font.render(msg, True, Colors.GREEN)
        text_surf.set_alpha(alpha)
        text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, banner_y + banner_height // 2))
        screen.blit(text_surf, text_rect)

    def _render_mission_notification(self, screen: pygame.Surface) -> None:
        """Render mission notification banner at top of screen."""
        if not self._mission_notifications and self._mission_notify_timer <= 0:
            return

        if self._mission_notify_timer <= 0:
            if self._mission_notifications:
                self._current_mission_msg = self._mission_notifications.pop(0)
                self._mission_notify_timer = 4.0

        if self._mission_notify_timer <= 0:
            return

        if self._banner_font is None:
            self._banner_font = pygame.font.Font(None, 24)

        msg = self._current_mission_msg
        if not msg:
            return

        alpha = 255
        if self._mission_notify_timer < 1.0:
            alpha = int(255 * self._mission_notify_timer)

        # Position below event banner and achievement banner
        banner_y = 0
        if self.event_banner_timer > 0:
            banner_y += 34
        if self._achievement_notify_timer > 0:
            banner_y += 34
        banner_height = 32
        banner_surf = pygame.Surface((WINDOW_WIDTH, banner_height), pygame.SRCALPHA)
        banner_surf.fill((10, 15, 35, min(200, alpha)))
        screen.blit(banner_surf, (0, banner_y))

        border_surf = pygame.Surface((WINDOW_WIDTH, 2), pygame.SRCALPHA)
        border_surf.fill((*Colors.BLUE, alpha))
        screen.blit(border_surf, (0, banner_y + banner_height - 2))

        text_surf = self._banner_font.render(msg, True, Colors.BLUE)
        text_surf.set_alpha(alpha)
        text_rect = text_surf.get_rect(center=(WINDOW_WIDTH // 2, banner_y + banner_height // 2))
        screen.blit(text_surf, text_rect)

    def run(self) -> None:
        """
        Main game loop.

        Handles:
        - Input processing
        - Game state updates
        - Rendering
        - Frame timing
        """
        logger.info("Starting main game loop...")
        self.running = True

        while self.running:
            # Calculate delta time (in seconds)
            dt = self.clock.tick(FPS_TARGET) / 1000.0

            # Process input
            events = pygame.event.get()
            self.input_handler.handle_events(events)

            # Check for quit
            if self.input_handler.quit_requested:
                self.running = False
                break

            # Pass events to UI manager and current state
            for event in events:
                # Check for ESC key to toggle pause (only during gameplay)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.player and not self.paused:
                        self._open_pause_menu()
                    elif self.paused:
                        self._close_pause_menu()

                # Tutorial overlay uses raw mouse events (not pygame_gui) so
                # it can render on top of everything.  Intercept events here
                # before they reach the UI manager to prevent click-through.
                if self._tutorial_overlay and self._tutorial_overlay.active:
                    consumed = self._tutorial_overlay.handle_event(event)
                    if consumed:
                        continue
                    # Still let non-consumed events (e.g. KEYDOWN) through
                    self.ui_manager.process_events(event)
                    continue

                self.ui_manager.process_events(event)

                # Route events to event notification, save/load, pause menu, or game state
                if self._event_notification_view and self._event_notification_view.active:
                    self._event_notification_view.handle_event(event)
                elif self.save_load_view:
                    self.save_load_view.handle_event(event)
                elif self.paused and self.pause_menu_view:
                    self.pause_menu_view.handle_event(event)
                else:
                    self.state_manager.handle_event(event)

            # Update UI manager
            self.ui_manager.update(dt)

            # Handle state transitions
            self._handle_state_transitions()
            self._check_tutorial_triggers()

            # Handle pause menu and dialogs
            if self.paused:
                self._handle_pause_menu()

            if self.save_load_view:
                self.save_load_view.update(dt)
                self._handle_save_load_dialog()

            if self.settings_view:
                self._handle_settings_dialog()

            # Handle event notifications
            self._handle_event_notifications(dt)

            # Update game state (only if not paused)
            if not self.paused:
                self.state_manager.update(dt)
                self.check_achievements()
                self.check_missions()
                self.check_crew_xp()

            # Update achievement notification timer
            if self._achievement_notify_timer > 0:
                self._achievement_notify_timer = max(0.0, self._achievement_notify_timer - dt)

            # Update mission notification timer
            if self._mission_notify_timer > 0:
                self._mission_notify_timer = max(0.0, self._mission_notify_timer - dt)

            # Update visual effects
            self.transition_manager.update(dt)
            self.screen_shake.update(dt)

            # Render to intermediate surface for screen shake
            render_surface = self.screen
            self.screen.fill(Colors.BACKGROUND)
            self.state_manager.render(render_surface)

            # Render pause menu overlay if paused
            if self.paused and self.pause_menu_view:
                self.pause_menu_view.render(render_surface)

            # Render save/load dialog on top of pause menu
            if self.save_load_view:
                self.save_load_view.render(render_surface)

            # Transition overlay (on top of game, under UI)
            if self.transition_manager.active:
                self.transition_manager.render(render_surface)

            # Render event notification overlay if active
            if self._event_notification_view and self._event_notification_view.active:
                self._event_notification_view.render(render_surface)

            # Vignette overlay
            self.vignette.render(render_surface)

            # Event banner (above vignette, below UI)
            self._render_event_banner(render_surface)

            # Achievement notification banner
            self._render_achievement_notification(render_surface)

            # Mission notification banner
            self._render_mission_notification(render_surface)

            self.ui_manager.draw_ui(render_surface)

            # Tutorial overlay renders AFTER ui_manager.draw_ui() so it
            # covers all pygame_gui elements from the underlying view.
            if self._tutorial_overlay and self._tutorial_overlay.active:
                self._tutorial_overlay.render(render_surface)

            # Apply screen shake offset
            shake_x, shake_y = self.screen_shake.offset
            if shake_x != 0 or shake_y != 0:
                temp = render_surface.copy()
                self.screen.fill((0, 0, 0))
                self.screen.blit(temp, (shake_x, shake_y))

            pygame.display.flip()

            # Optional: Display FPS in window title (debug)
            if pygame.time.get_ticks() % 60 == 0:  # Update every 60 frames
                fps = self.clock.get_fps()
                pygame.display.set_caption(f"{WINDOW_TITLE} - FPS: {fps:.1f}")

        logger.info("Game loop ended")
        self.quit()

    def quit(self) -> None:
        """Clean shutdown of the game."""
        logger.info("Shutting down game...")
        pygame.quit()
        sys.exit()


def main() -> None:
    """Entry point for the game."""
    game = Game()
    game.initialize_states()
    game.run()


if __name__ == "__main__":
    main()
