"""Main game engine — orchestrates the entire game.

Manages the core loop, state transitions, view lifecycle, save/load,
audio, tutorials, and all system managers. This is intentionally a
large file (~4,600 lines) because it owns all cross-cutting concerns.

File structure:
  Lines ~1-80:     Imports (eager for engine/models, lazy for views)
  Lines ~80-350:   Game.__init__() — pygame init, manager creation, data loading
  Lines ~350-500:  Game.run() — main loop, event handling, render
  Lines ~500-810:  Game loop helpers — update, render, HUD, save/load
  Lines ~810-1690: _handle_state_transitions() — 30-case router for all state changes
  Lines ~1690-1745: Transition helpers — _start_transition, _do closures
  Lines ~1745-2100: View factories — 23 _ensure_*_view() methods (lazy view creation)
  Lines ~2100-2270: Combat setup — start_combat(), build encounters
  Lines ~2270-2500: Encounter processing — resolve encounters, post-combat rewards
  Lines ~2500-2810: Travel & exploration — jump logic, travel encounters, day advance
  Lines ~2810-2900: Ground mission setup
  Lines ~2900-3100: Shipyard/builder setup
  Lines ~3100-3500: Tutorial, achievements, notifications
  Lines ~3500-3700: Trophy drops, builder discovery, event processing
  Lines ~3700-4000: Audio, settings, resolution management
  Lines ~4000-4611: Utility methods, main() entry point

View factories (_ensure_*_view methods) use lazy imports to keep startup fast.
State transitions are a flat switch for readability — each case maps directly
to the game state diagram. Both are kept in this file because they access
15+ shared managers that don't cleanly extract without passing the world state.
"""

import sys
import time
from pathlib import Path
from typing import Optional

import pygame
import pygame_gui

from spacegame.achievement_manager import AchievementManager
from spacegame.config import (
    FPS_TARGET,
    FULLSCREEN,
    MIXER_BUFFER,
    MIXER_CHANNELS,
    MIXER_FREQUENCY,
    MIXER_SIZE,
    STARTING_CREDITS,
    VSYNC,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    Colors,
    GameState,
)
from spacegame.data_loader import get_data_loader
from spacegame.engine.activity_registry import create_default_registry
from spacegame.engine.audio_manager import get_audio_manager
from spacegame.engine.fonts import get_font
from spacegame.engine.input_handler import InputHandler
from spacegame.engine.screen_effects import ScreenShake, Vignette
from spacegame.engine.startup_timer import StartupTimer
from spacegame.engine.state_manager import StateManager
from spacegame.engine.transitions import TransitionManager, TransitionType
from spacegame.models.event import EventGenerator
from spacegame.models.faction import generate_faction_assignments
from spacegame.models.market import Market
from spacegame.models.player import Player
from spacegame.models.ship import Ship
from spacegame.save_manager import SaveManager
from spacegame.tutorial_manager import TutorialManager
from spacegame.utils.logger import logger


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
        logger.info("Initializing Aurelia: A Ledger of Stars...")
        timer = StartupTimer()

        # Initialize audio mixer before pygame.init() for correct format
        timer.begin("mixer_preinit")
        pygame.mixer.pre_init(
            frequency=MIXER_FREQUENCY,
            size=MIXER_SIZE,
            channels=MIXER_CHANNELS,
            buffer=MIXER_BUFFER,
        )
        timer.end("mixer_preinit")

        # Initialize PyGame
        timer.begin("pygame_init")
        pygame.init()
        timer.end("pygame_init")

        # Create window
        timer.begin("display_setup")
        flags = pygame.SCALED
        if FULLSCREEN:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(
            (WINDOW_WIDTH, WINDOW_HEIGHT), flags=flags, vsync=1 if VSYNC else 0
        )
        pygame.display.set_caption(WINDOW_TITLE)

        # Custom pixel art cursor
        self._set_pixel_cursor()
        timer.end("display_setup")

        # Audio system
        timer.begin("audio_init")
        self.audio_manager = get_audio_manager()
        self._last_audio_state: Optional[GameState] = None
        self._dialogue_music: str = "dialogue_neutral"
        timer.end("audio_init")

        # Core systems
        self.clock = pygame.time.Clock()
        self.running = False
        self.state_manager = StateManager()
        self.input_handler = InputHandler()

        # pygame_gui UI manager with resolution-scaled theme
        timer.begin("ui_manager")
        from spacegame.config import DATA_DIR

        theme_path = DATA_DIR / "theme.json"
        scaled_theme_path = self._build_scaled_theme(theme_path)
        if scaled_theme_path:
            self.ui_manager = pygame_gui.UIManager(
                (WINDOW_WIDTH, WINDOW_HEIGHT), theme_path=str(scaled_theme_path)
            )
            logger.info(f"Loaded UI theme (scaled for {WINDOW_WIDTH}x{WINDOW_HEIGHT})")
        else:
            self.ui_manager = pygame_gui.UIManager((WINDOW_WIDTH, WINDOW_HEIGHT))
            logger.info("No theme.json found, using default pygame_gui theme")
        timer.end("ui_manager")

        # Game data
        timer.begin("data_loading")
        self.data_loader = get_data_loader()
        timer.end("data_loading")
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

        # Restore persisted audio settings
        saved_settings = self.save_manager.load_settings()
        if "audio" in saved_settings:
            from spacegame.engine.audio_manager import AudioConfig

            self.audio_manager.set_config(AudioConfig.from_dict(saved_settings["audio"]))

        # Markets (system_id -> Market)
        self.markets: dict[str, Market] = {}

        # Price history and trade route tracking
        from spacegame.models.market import PriceHistory

        self.price_history: PriceHistory = PriceHistory()

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
        self._cockpit_hud = None
        self._tutorial_cooldown: int = 0  # frames to wait before next overlay

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
        self.character_creation_view = None
        self.character_view = None
        self.combat_view = None
        self.encounter_view = None
        self.ground_briefing_view = None
        self.ground_exploration_view = None
        self.ground_result_view = None
        self.investment_view = None
        self.cantina_view = None

        # Investment system
        from spacegame.models.investment import InvestmentManager

        self.investment_manager: Optional[InvestmentManager] = None

        # Dialogue system
        from spacegame.models.attributes import AttributeSheet
        from spacegame.models.dialogue import DialogueManager
        from spacegame.models.social import SocialManager

        self.dialogue_manager = DialogueManager()
        self.social_manager = SocialManager()
        self.dialogue_manager.set_social_manager(self.social_manager)
        self._last_dialogue_npc_id: Optional[str] = None
        self.attribute_sheet = AttributeSheet()

        # Mission system
        from spacegame.models.mission import MissionManager

        self.mission_manager: Optional[MissionManager] = None
        self.mission_log_view = None

        # Mission notification queue
        self._mission_notifications: list[str] = []
        self._mission_notify_timer: float = 0.0
        self._current_mission_msg: str = ""

        # Bounty hunter system
        self._bounty_immunity_until: int = 0
        self._pending_bounty_combat_ids: list[str] = []

        # Crew system
        from spacegame.models.crew import CrewRoster

        self.crew_roster: Optional[CrewRoster] = None
        self.crew_roster_view = None
        self._crew_last_trades: int = 0
        self._crew_last_jumps: int = 0

        # Ambient dialogue system
        from spacegame.models.ambient_dialogue import AmbientDialogueManager

        self.ambient_dialogue: Optional[AmbientDialogueManager] = None
        self._ambient_idle_day_counter: int = 0

        # Journal system
        from spacegame.models.journal import Journal

        self.journal: Optional[Journal] = None
        self.journal_view = None
        self._last_visited_count: int = 1  # Starting system is already visited

        # Ground contract system
        from spacegame.models.ground_contracts import GroundContractManager

        self.ground_contract_manager: Optional[GroundContractManager] = None

        # Smuggling contract system
        from spacegame.models.smuggling import SmugglingContractManager

        self.smuggling_contract_manager: Optional[SmugglingContractManager] = None

        # Political system
        from spacegame.models.politics import PoliticsManager

        self.politics_manager: Optional[PoliticsManager] = None

        # Galaxy event system
        from spacegame.models.galaxy_event import GalaxyEventGenerator

        self.galaxy_event_generator: Optional[GalaxyEventGenerator] = None
        self.active_galaxy_events: dict[str, list] = {}  # system_id -> [GalaxyEvent]

        # Station chatter system
        from spacegame.models.station_chatter import StationChatterManager

        self.station_chatter: Optional[StationChatterManager] = None

        # News ticker system
        from spacegame.models.news_ticker import NewsTicker

        self.news_ticker: Optional[NewsTicker] = None
        self._pending_player_news: list[dict] = []

        # Milestone celebration overlay
        self._celebration_text: str = ""
        self._celebration_subtitle: str = ""
        self._celebration_timer: float = 0.0

        # Travel log system
        from spacegame.models.travel_log import TravelLogGenerator

        self.travel_log: Optional[TravelLogGenerator] = None

        # Day-advance tracking for market event generation
        self._last_known_day: int = 0

        logger.info(f"Window created: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        logger.info(f"Target FPS: {FPS_TARGET}")
        timer.log_summary()

    def _make_crew_commentary_fn(self):
        """Create a callable that returns crew commentary for mini-game events.

        Returns:
            A function(action_type: str) -> Optional[tuple[str, str]] returning
            (crew_name, text) or None.
        """
        ambient = self.ambient_dialogue
        roster = self.crew_roster

        if not ambient or not roster:
            return lambda action_type: None

        def _get_line(action_type: str):
            recruited = [t.id for t, _s in roster.get_recruited_members()]
            if not recruited:
                return None
            loyalty_map = {}
            for tid in recruited:
                state = roster.get_member_state(tid)
                if state:
                    loyalty_map[tid] = state.get("loyalty", 50)
            result = ambient.get_player_action_line(action_type, recruited, loyalty_map)
            if result:
                crew_id, text = result
                template = roster.get_template(crew_id)
                name = template.name if template else crew_id
                return (name, text)
            return None

        return _get_line

    def queue_player_news(self, detail: str = "", commodity: str = "", amount: str = "") -> None:
        """Queue a player action for the next news ticker generation.

        Args:
            detail: Action-specific detail.
            commodity: Commodity involved.
            amount: Amount or value string.
        """
        if self.player:
            self._pending_player_news.append(
                self.player.make_news_context(detail, commodity, amount)
            )

    def initialize_new_game(self, player_name: str = "Captain", ship_name: str = "") -> None:
        """Initialize a new game with starting conditions.

        Args:
            player_name: Name chosen by the player.
            ship_name: Player-chosen ship name (empty = use ship type name).
        """
        logger.info("Initializing new game...")

        # Create player with starting ship
        shuttle_type = self.data_loader.get_ship_type("shuttle")
        starting_ship = Ship(ship_type=shuttle_type, current_fuel=shuttle_type.fuel_capacity)

        # Generate a preset build so the player has a composite from the start
        from spacegame.models.ship_presets import generate_preset_from_ship_type

        try:
            preset = generate_preset_from_ship_type(shuttle_type)
            starting_ship.set_build(preset)
        except Exception:
            pass  # Composite will be generated on first drydock visit

        # Debug mode: 1M credits when player name is "Debug"
        credits = 1_000_000 if player_name == "Debug" else STARTING_CREDITS

        self.player = Player(
            name=player_name,
            credits=credits,
            current_system_id="nexus_prime",
            ship=starting_ship,
            ship_name=ship_name,
        )

        # Sync upgrade manager slots from ship type (default_factory doesn't know ship type)
        self.player.upgrade_manager._weapon_slots = shuttle_type.weapon_slots
        self.player.upgrade_manager._defense_slots = shuttle_type.defense_slots
        self.player.upgrade_manager._utility_slots = shuttle_type.utility_slots

        logger.info(f"Player created: {self.player.name} at {self.player.current_system_id}")
        logger.info(f"Starting credits: {self.player.credits} CR")

        # Generate random faction assignments
        faction_ids = [f.id for f in self.data_loader.get_all_factions()]
        system_ids = [s.id for s in self.data_loader.get_all_systems()]
        if faction_ids:
            self.player.faction_assignments = generate_faction_assignments(system_ids, faction_ids)
            self.player.faction_reputation = dict.fromkeys(faction_ids, 0)
            self._apply_faction_assignments()

        # Initialize event generator
        commodity_ids = [c.id for c in self.data_loader.get_all_commodities()]
        system_ids = [s.id for s in self.data_loader.get_all_systems()]
        self.event_generator = EventGenerator(commodity_ids, system_ids)

        # Initialize recipe discovery (all non-discoverable recipes start discovered)
        self.player.initialize_discovered_recipes(self.data_loader.recipes)

        # Start tutorial for new game
        self.tutorial_manager.reset_tutorial()

        # Initialize mission system
        from spacegame.models.mission import MissionManager

        self.mission_manager = MissionManager(self.data_loader.missions)
        self.mission_manager.update_availability(self.player.dialogue_flags)

        # Auto-start campaign mission: bill of landing
        self.mission_manager.accept_mission("bill_of_landing")

        # Initialize procedural mission generator
        from spacegame.models.procedural_missions import ProceduralMissionGenerator

        self.procedural_mission_gen = ProceduralMissionGenerator(
            systems=self.data_loader.systems,
            commodities=self.data_loader.commodities,
            enemy_templates=self.data_loader.enemy_templates,
            seed=hash(self.player.name) & 0xFFFFFFFF,
        )
        self._proc_missions_day: int = -1

        # Initialize crew system
        from spacegame.models.crew import CrewRoster

        self.crew_roster = CrewRoster(self.data_loader.crew_templates)
        self.player.ship.set_crew_roster(self.crew_roster)
        self.dialogue_manager.set_crew_roster(self.crew_roster)
        self._crew_last_trades = 0

        # Initialize ambient dialogue
        if self.data_loader.ambient_lines:
            from spacegame.models.ambient_dialogue import AmbientDialogueManager

            self.ambient_dialogue = AmbientDialogueManager(self.data_loader.ambient_lines)
        self._crew_last_jumps = 0

        # Initialize attribute system
        from spacegame.models.attributes import AttributeSheet

        self.attribute_sheet = AttributeSheet(unspent_points=5)
        self.social_manager.set_progression(self.player.progression)
        self.social_manager.set_attribute_sheet(self.attribute_sheet)

        # Initialize journal system
        from spacegame.models.journal import Journal

        self.journal = Journal(auto_templates=self.data_loader.journal_entries)

        # Initialize ground contract system
        from spacegame.models.ground_contracts import GroundContractManager

        self.ground_contract_manager = GroundContractManager()

        # Initialize investment system
        from spacegame.models.investment import InvestmentManager

        self.investment_manager = InvestmentManager(
            templates=dict(self.data_loader.investment_templates)
        )

        # Initialize smuggling contract system
        from spacegame.models.smuggling import SmugglingContractManager

        self.smuggling_contract_manager = SmugglingContractManager()

        # Initialize political system
        self._initialize_politics_manager()

        # Initialize galaxy event system
        self._initialize_galaxy_event_generator()

        # Initialize station chatter
        self._initialize_station_chatter()

        # Initialize news ticker
        self._initialize_news_ticker()

        # Initialize travel log
        self._initialize_travel_log()

        # Initialize cockpit HUD
        self._init_cockpit_hud()

        # Track starting day for event generation
        self._last_known_day = self.player.game_day

    @staticmethod
    def _build_scaled_theme(base_path: Path) -> Optional[Path]:
        """Build a resolution-scaled theme JSON for pygame_gui.

        Reads the base theme file, scales any font sizes proportionally
        to the active resolution, and writes a temp file.

        Args:
            base_path: Path to the base theme.json.

        Returns:
            Path to the scaled theme file, or None if base doesn't exist.
        """
        if not base_path.exists():
            return None
        try:
            import json

            from spacegame.engine.fonts import scaled_font_size

            with open(base_path, "r") as f:
                theme_data = json.load(f)

            # Walk the theme tree and scale any font size values
            def _scale_fonts(obj: dict) -> None:
                for key, value in obj.items():
                    if isinstance(value, dict):
                        if key == "font" and "size" in value:
                            base_size = int(value["size"])
                            value["size"] = str(scaled_font_size(base_size))
                        else:
                            _scale_fonts(value)

            _scale_fonts(theme_data)

            # Write scaled theme to temp file (same dir for relative paths)
            scaled_path = base_path.parent / "_theme_scaled.json"
            with open(scaled_path, "w") as f:
                json.dump(theme_data, f, indent=4)
            return scaled_path
        except Exception as e:
            logger.warning(f"Failed to build scaled theme: {e}")
            return base_path

    def _init_cockpit_hud(self) -> None:
        """Create or reinitialize the cockpit HUD overlay."""
        from spacegame.views.cockpit_hud import CockpitHUD

        self._cockpit_hud = CockpitHUD(
            player=self.player,
            mission_manager=self.mission_manager,
            crew_roster=self.crew_roster,
        )

    def _ensure_view_for_state(self, state: GameState) -> None:
        """Ensure the view for a target state is initialized.

        Args:
            state: Target GameState to prepare.
        """
        ensure_map = {
            GameState.CHARACTER: self._ensure_character_view,
            GameState.SKILL_TREE: self._ensure_skill_tree_view,
            GameState.CREW_ROSTER: self._ensure_crew_roster_view,
            GameState.MISSION_LOG: self._ensure_mission_log_view,
            GameState.JOURNAL: self._ensure_journal_view,
            GameState.STATISTICS: self._ensure_statistics_view,
            GameState.ACHIEVEMENTS: self._ensure_achievements_view,
        }
        ensure_fn = ensure_map.get(state)
        if ensure_fn:
            ensure_fn()

    def _set_pixel_cursor(self) -> None:
        """Set a custom 16x16 pixel art cursor matching the game aesthetic."""
        # 16x16 arrow cursor in blue accent colors
        # . = transparent, X = outline (dark), B = bright accent, A = mid accent
        cursor_art = [
            "X...............",
            "XBX.............",
            "XBBX............",
            "XBBBX...........",
            "XBBBBX..........",
            "XBBBBBX.........",
            "XBBBBBBX........",
            "XBBBBBBBX.......",
            "XBBBBBBBBX......",
            "XBBBBBXXX.......",
            "XBBXBBX.........",
            "XBX.XBX.........",
            "XX..XBBX........",
            "X....XBX........",
            ".....XBX........",
            "......X.........",
        ]
        colors = {
            ".": (0, 0, 0, 0),
            "X": (10, 10, 15, 255),
            "B": (100, 180, 255, 255),
            "A": (60, 120, 200, 255),
        }
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        for y, row in enumerate(cursor_art):
            for x, ch in enumerate(row):
                c = colors.get(ch)
                if c and c[3] > 0:
                    surf.set_at((x, y), c)
        cursor = pygame.cursors.Cursor((0, 0), surf)
        pygame.mouse.set_cursor(cursor)

    def _initialize_politics_manager(self, political_state: Optional[dict] = None) -> None:
        """Initialize or restore the PoliticsManager.

        Args:
            political_state: Saved political state dict, or None for fresh defaults.
        """
        from spacegame.models.politics import PoliticsManager

        factions = {f.id: f for f in self.data_loader.get_all_factions()}
        if political_state:
            self.politics_manager = PoliticsManager.from_dict(political_state, factions)
        else:
            relationships = list(self.data_loader.faction_relationships)
            self.politics_manager = PoliticsManager(relationships=relationships, factions=factions)

        # Load faction perks into politics manager
        if self.politics_manager and self.data_loader.faction_perks:
            self.politics_manager.set_faction_perks(self.data_loader.faction_perks)

        # Wire politics into dialogue system for faction_reputation_changes
        if self.politics_manager and self.player:
            self.dialogue_manager.set_politics_manager(self.politics_manager, self.player)

    def _initialize_galaxy_event_generator(self) -> None:
        """Initialize the galaxy event generator from data-driven templates."""
        from spacegame.models.galaxy_event import GalaxyEventGenerator

        templates = self.data_loader.galaxy_event_templates
        chains = self.data_loader.galaxy_event_chains
        self.galaxy_event_generator = GalaxyEventGenerator(templates or [], chains=chains or [])

    def _initialize_station_chatter(self) -> None:
        """Initialize station chatter from loaded data."""
        from spacegame.models.station_chatter import StationChatterManager

        lines = self.data_loader.station_chatter_lines
        self.station_chatter = StationChatterManager(lines)

    def _initialize_news_ticker(self) -> None:
        """Initialize news ticker from loaded templates."""
        from spacegame.config import NEWS_TICKER_BUFFER_SIZE
        from spacegame.models.news_ticker import NewsTicker

        self.news_ticker = NewsTicker(
            self.data_loader.news_templates, buffer_size=NEWS_TICKER_BUFFER_SIZE
        )

    def _initialize_travel_log(self) -> None:
        """Initialize travel log from loaded templates."""
        from spacegame.models.travel_log import TravelLogGenerator

        self.travel_log = TravelLogGenerator(self.data_loader.travel_log_templates)

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

        # Create views
        self.main_menu_view = MainMenuView(self.ui_manager, self.save_manager)

        # Register main menu
        self.state_manager.register_state(GameState.MAIN_MENU, self.main_menu_view)
        self.state_manager.change_state(GameState.MAIN_MENU)

        logger.info("Game states initialized")

    # === State → Music/Ambient mapping ===

    _STATE_MUSIC: dict[GameState, str] = {
        GameState.MAIN_MENU: "main_theme",
        GameState.GALAXY_MAP: "galaxy_exploration",
        GameState.TRADING: "station_hub",
        GameState.STATION_HUB: "station_hub",
        GameState.CANTINA: "station_hub",
        GameState.REPAIR_BAY: "station_hub",
        GameState.SHIPYARD: "station_hub",
        GameState.INVESTMENT: "station_hub",
        GameState.SALVAGING: "station_hub",
        GameState.REFINING: "station_hub",
        GameState.COMBAT: "combat_intense",
        GameState.ENCOUNTER: "combat_intense",
        GameState.MINING: "mining_rhythm",
        GameState.GROUND_BRIEFING: "ground_stealth",
        GameState.GROUND_EXPLORATION: "ground_stealth",
        GameState.GROUND_RESULT: "ground_stealth",
        GameState.DIALOGUE: "dialogue_intimate",
    }

    _STATE_AMBIENT: dict[GameState, str] = {
        GameState.GALAXY_MAP: "ambient_space",
        GameState.TRADING: "ambient_station",
        GameState.STATION_HUB: "ambient_station",
        GameState.CANTINA: "ambient_station",
        GameState.REPAIR_BAY: "ambient_station",
        GameState.SHIPYARD: "ambient_station",
        GameState.INVESTMENT: "ambient_station",
        GameState.SALVAGING: "ambient_station",
        GameState.REFINING: "ambient_station",
        GameState.COMBAT: "ambient_combat",
        GameState.ENCOUNTER: "ambient_combat",
        GameState.GROUND_BRIEFING: "ambient_ground",
        GameState.GROUND_EXPLORATION: "ambient_ground",
        GameState.GROUND_RESULT: "ambient_ground",
    }

    def _update_audio_for_state(self) -> None:
        """Update music and ambient sounds when game state changes."""
        current = self.state_manager.current_state
        if current == self._last_audio_state:
            return
        self._last_audio_state = current

        if current is None:
            return

        # Music (dialogue state uses dynamic track based on NPC)
        if current == GameState.DIALOGUE:
            music_id = self._dialogue_music
        else:
            music_id = self._STATE_MUSIC.get(current)
        if music_id:
            self.audio_manager.play_music(music_id)
        # Don't stop music for unmapped states (skill tree, stats, etc.)
        # — they inherit the parent state's music

        # Ambient
        ambient_id = self._STATE_AMBIENT.get(current)
        if ambient_id:
            self.audio_manager.play_ambient(ambient_id)

    def _start_transition(self, transition_type: TransitionType, duration: float, callback) -> None:
        """Start a visual transition then execute callback at midpoint."""
        if self.transition_manager.active:
            # Skip transition if one is already in progress, just do the swap
            callback()
            return
        old_surface = self.screen.copy()
        self.transition_manager.start(transition_type, duration, callback, old_surface)

    # ==================================================================
    # STATE TRANSITIONS (lines ~836-1710)
    # Each active view is checked for a pending next_state. When found,
    # the transition handler creates the target view (via _ensure_*),
    # wraps the state change in a visual transition, and clears the
    # pending state. Cases are ordered by frequency of use.
    # ==================================================================

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
                    # Always start fresh — clear existing player if loaded
                    self.player = None
                    self._start_intro_narration(return_state=GameState.NAME_INPUT)

                self._start_transition(TransitionType.FADE, 0.5, _do)
            elif next_state == "continue":
                self.main_menu_view.next_state = None
                slot = self.save_manager.get_most_recent_save_slot()
                if slot is not None:
                    self._load_game(slot)
            elif next_state == "load_game":
                self.main_menu_view.next_state = None
                self._open_load_dialog()
            elif next_state == "settings":
                self.main_menu_view.next_state = None
                self._open_settings_from_menu()

        # Check name input view for transitions
        if self.name_input_view and self.name_input_view.active:
            next_state = self.name_input_view.get_next_state()
            if next_state:
                self.name_input_view.next_state = None
                player_name = self.name_input_view.get_player_name()
                ship_name = self.name_input_view.get_ship_name()
                self.initialize_new_game(player_name, ship_name=ship_name)
                self._create_gameplay_views()

                # Go to character creation for attribute allocation
                def _do():
                    self._ensure_character_creation_view()
                    self.state_manager.change_state(GameState.CHARACTER_CREATION)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check character creation view for transitions
        if hasattr(self, "character_creation_view") and self.character_creation_view:
            if self.character_creation_view.active:
                next_state = self.character_creation_view.get_next_state()
                if next_state == GameState.GALAXY_MAP:
                    self.character_creation_view.next_state = None

                    def _do():
                        self.state_manager.change_state(GameState.GALAXY_MAP)

                    self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check galaxy map for transitions
        if self.galaxy_map_view and self.galaxy_map_view.active:
            # Handle save button (not a state transition)
            if self.galaxy_map_view.save_requested:
                self.galaxy_map_view.save_requested = False
                self.auto_save()
                self._mission_notifications.append("Game Saved")

            # Handle arrival notification
            if getattr(self.galaxy_map_view, "arrival_message", None):
                self._mission_notifications.append(self.galaxy_map_view.arrival_message)
                self.galaxy_map_view.arrival_message = None

                # Travel log: first visit entry
                if self.travel_log and self.journal and self.player:
                    system_id = self.player.current_system_id
                    if len(self.player.systems_visited) > self._last_visited_count:
                        entry = self.travel_log.on_first_visit(system_id, self.player.game_day)
                        if entry:
                            self.journal.add_entry(entry)
                    self._last_visited_count = len(self.player.systems_visited)

                # Trigger ambient crew dialogue on system arrival
                if self.ambient_dialogue and self.crew_roster and self.player:
                    system_id = self.player.current_system_id
                    system = self.data_loader.get_system(system_id)
                    faction_id = system.faction if system else ""
                    recruited = [t.id for t, _ in self.crew_roster.get_recruited_members()]
                    loyalty_map = {}
                    for tid in recruited:
                        state = self.crew_roster.get_member_state(tid)
                        loyalty_map[tid] = state["loyalty"] if state else 0
                        template = self.crew_roster.get_template(tid)
                        if not template:
                            continue
                        # Check home system
                        if template.home_system_id == system_id:
                            line = self.ambient_dialogue.get_line(
                                "home_system",
                                tid,
                                system_id=system_id,
                                loyalty=loyalty_map[tid],
                            )
                            if line:
                                self._mission_notifications.append(f'{template.name}: "{line}"')
                        # Check faction territory
                        elif template.faction_id and template.faction_id == faction_id:
                            line = self.ambient_dialogue.get_line(
                                "faction_territory",
                                tid,
                                faction_id=faction_id,
                                loyalty=loyalty_map[tid],
                            )
                            if line:
                                self._mission_notifications.append(f'{template.name}: "{line}"')

            # Check for NPC auto-trigger dialogues at current system
            self._check_auto_triggers()
            if self.dialogue_view and self.dialogue_view.active:
                return  # Auto-trigger fired, skip galaxy map processing

            next_state = self.galaxy_map_view.get_next_state()
            if next_state == GameState.TRADING:
                self.galaxy_map_view.next_state = None

                # Auto-trigger campaign dialogue at Nexus Prime (one-time only)
                if (
                    self.player
                    and self.player.current_system_id == "nexus_prime"
                    and not self.player.dialogue_flags.get("talked_to_officer_larsen", False)
                ):
                    # Set flag immediately so the trigger can never re-fire,
                    # even if the dialogue is interrupted or game exits early.
                    self.player.dialogue_flags["talked_to_officer_larsen"] = True
                    self.dialogue_manager.set_flag("talked_to_officer_larsen")
                    self.start_dialogue("officer_larsen", return_state=GameState.STATION_HUB)
                    return

                # Check for bounty hunter encounter on arrival
                if self._check_bounty_hunter_encounter():
                    return

                # Check for customs inspection on arrival
                if self._check_customs_inspection():
                    return

                # Check for campaign ground mission trigger on arrival
                if self._check_ground_mission_trigger():
                    return

                def _do():
                    self.auto_save()
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.COMBAT:
                self.galaxy_map_view.next_state = None
                pending = getattr(self.galaxy_map_view, "_pending_encounter", None)
                if pending:
                    self.galaxy_map_view._pending_encounter = None
                    self.screen_shake.trigger(intensity=5.0, duration=0.3)
                    encounter = self._resolve_encounter_ref(pending)
                    if encounter:
                        self.start_combat(
                            encounter,
                            return_state=GameState.STATION_HUB,
                            transition_type=TransitionType.WARP,
                        )
                        return

                # Fallback: safe landing
                def _do():
                    self.auto_save()
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.ENCOUNTER:
                self.galaxy_map_view.next_state = None
                enc_ref = getattr(self.galaxy_map_view, "_pending_encounter_ref", None)
                if enc_ref:
                    self.galaxy_map_view._pending_encounter_ref = None
                    defn = self._resolve_encounter_definition(enc_ref)
                    if defn:
                        self._ensure_encounter_view(defn, enc_ref)

                        def _do():
                            self.state_manager.change_state(GameState.ENCOUNTER)

                        self._start_transition(TransitionType.FADE, 0.4, _do)
                        return

                # Fallback: no definition found → go to station hub
                def _do():
                    self.auto_save()
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.CHARACTER:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_character_view()
                    self.state_manager.change_state(GameState.CHARACTER)

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
            elif next_state == GameState.JOURNAL:
                self.galaxy_map_view.next_state = None

                def _do():
                    self._ensure_journal_view()
                    self.state_manager.change_state(GameState.JOURNAL)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check journal view for transitions
        if self.journal_view and self.journal_view.active:
            next_state = self.journal_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.journal_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

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
                    # Check dismiss blocking (e.g. Priya during lab_rat)
                    from spacegame.models.mission import MissionStatus as _MS

                    active_ids = (
                        [m.id for m in self.mission_manager.get_missions_by_status(_MS.ACTIVE)]
                        if self.mission_manager
                        else []
                    )
                    can, reason = self.crew_roster.can_dismiss(dismiss_id, active_ids)
                    if not can:
                        self._mission_notifications.append(reason)
                    else:
                        success, msg = self.crew_roster.dismiss(dismiss_id)
                        if success:
                            self._mission_notifications.append(f"Crew Dismissed: {msg}")

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check character view for transitions
        if hasattr(self, "character_view") and self.character_view:
            if self.character_view.active:
                next_state = self.character_view.get_next_state()
                if next_state == GameState.GALAXY_MAP:
                    self.character_view.next_state = None

                    def _do():
                        self.state_manager.change_state(GameState.GALAXY_MAP)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.SKILL_TREE:
                    self.character_view.next_state = None

                    def _do():
                        self._ensure_skill_tree_view()
                        self.state_manager.change_state(GameState.SKILL_TREE)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.CREW_ROSTER:
                    self.character_view.next_state = None

                    def _do():
                        self._ensure_crew_roster_view()
                        self.state_manager.change_state(GameState.CREW_ROSTER)

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
                    # Update galaxy map mission markers and forced encounters
                    if self.galaxy_map_view and self.mission_manager:
                        self.galaxy_map_view.mission_target_systems = (
                            self.mission_manager.get_active_target_systems()
                        )
                        self.galaxy_map_view.forced_encounters = (
                            self.mission_manager.get_active_forced_encounters()
                        )
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check trading view for transitions
        if self.trading_view and self.trading_view.active:
            next_state = self.trading_view.get_next_state()
            if next_state == GameState.STATION_HUB:
                self.trading_view.next_state = None

                def _do():
                    self.market = None
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check dialogue view for transitions (generic — supports any return state)
        if self.dialogue_view and self.dialogue_view.active:
            next_state = self.dialogue_view.get_next_state()
            if next_state is not None:
                self.dialogue_view.next_state = None

                # Sync dialogue flags and social state back to player
                if self.player:
                    self.player.dialogue_flags = self.dialogue_manager.get_flags()
                    self.player.social_state = self.social_manager.get_state()

                    # Set talked_to flag for mission objectives
                    if self._last_dialogue_npc_id:
                        flag_key = f"talked_to_{self._last_dialogue_npc_id}"
                        self.player.dialogue_flags[flag_key] = True
                        self.dialogue_manager.set_flag(flag_key)
                        self._last_dialogue_npc_id = None

                    # Check for journal auto-entries triggered by new flags
                    self._check_journal_triggers()

                    # Handle mission failures triggered by dialogue
                    if (
                        self.player.dialogue_flags.get("iron_delivery_failed")
                        and self.mission_manager
                    ):
                        from spacegame.models.mission import MissionStatus

                        if self.mission_manager.get_status("iron_delivery") == MissionStatus.ACTIVE:
                            self.mission_manager.fail_mission("iron_delivery")
                            self._mission_notifications.append("Mission Failed: Iron Ore Delivery")
                            logger.info(
                                "Iron delivery mission failed — player sold consigned cargo"
                            )

                target = next_state

                def _do():
                    if target == GameState.NAME_INPUT:
                        self._ensure_name_input_view()
                    elif target == GameState.STATION_HUB:
                        self._ensure_station_hub_view()
                    elif target == GameState.CANTINA:
                        self._ensure_cantina_view()
                    self.state_manager.change_state(target)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check mining view for transitions
        if self.mining_view and self.mining_view.active:
            next_state = self.mining_view.get_next_state()
            if next_state == GameState.TRADING:
                self.mining_view.next_state = None
                # Discovery: check for shape/material from deep mining (Phase D2)
                self._check_mining_discovery()

                def _do():
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check salvage view for transitions
        if self.salvage_view and self.salvage_view.active:
            next_state = self.salvage_view.get_next_state()
            if next_state == GameState.TRADING:
                self.salvage_view.next_state = None
                # Discovery: check for shape blueprint from salvage (Phase D2)
                self._check_salvage_discovery()

                def _do():
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check refining view for transitions
        if self.refining_view and self.refining_view.active:
            next_state = self.refining_view.get_next_state()
            if next_state == GameState.TRADING:
                self.refining_view.next_state = None

                def _do():
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.SLIDE, 0.3, _do)

        # Check skill tree for transitions
        if self.skill_tree_view and self.skill_tree_view.active:
            next_state = self.skill_tree_view.get_next_state()
            if next_state == GameState.CHARACTER:
                self.skill_tree_view.next_state = None

                def _do():
                    # Sync drone fleet after skill tree changes
                    from spacegame.models.drone import apply_drone_skill_effects

                    apply_drone_skill_effects(self.player)
                    self._ensure_character_view()
                    self.state_manager.change_state(GameState.CHARACTER)

                self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.GALAXY_MAP:
                self.skill_tree_view.next_state = None

                def _do():
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

        # Check combat view for transitions
        if self.combat_view and self.combat_view.active:
            next_state = self.combat_view.get_next_state()
            if next_state:
                self.combat_view.next_state = None
                self._apply_combat_result()
                target = next_state

                def _do():
                    # Ensure target view exists before switching
                    if target == GameState.TRADING:
                        self._ensure_station_hub_view()
                        self.state_manager.change_state(GameState.STATION_HUB)
                    elif target == GameState.GALAXY_MAP:
                        self.state_manager.change_state(GameState.GALAXY_MAP)
                    elif target == GameState.STATION_HUB:
                        self._ensure_station_hub_view()
                        self.state_manager.change_state(GameState.STATION_HUB)
                    else:
                        self._ensure_view_for_state(target)
                        self.state_manager.change_state(target)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check encounter view for transitions
        if self.encounter_view and self.encounter_view.active:
            next_state = self.encounter_view.get_next_state()
            if next_state:
                self.encounter_view.next_state = None
                if self.encounter_view.pending_combat:
                    # Combat from encounter choice: resolve and start combat
                    enc_ref = self.encounter_view.encounter_ref
                    combat_encounter = self._resolve_encounter_ref(enc_ref)
                    if combat_encounter:
                        self._apply_encounter_result()
                        self.start_combat(
                            combat_encounter,
                            return_state=GameState.TRADING,
                            transition_type=TransitionType.WARP,
                        )
                        return
                # Non-combat: apply rewards and go to trading
                self._apply_encounter_result()

                # Check if encounter result triggered bounty combat
                if self._pending_bounty_combat_ids:
                    enemy_ids = self._pending_bounty_combat_ids
                    self._pending_bounty_combat_ids = []
                    bounty_combat = self._resolve_bounty_combat(enemy_ids)
                    if bounty_combat:
                        self.start_combat(
                            bounty_combat,
                            return_state=GameState.TRADING,
                            transition_type=TransitionType.WARP,
                        )
                        return

                def _do():
                    self.auto_save()
                    self.state_manager.change_state(GameState.TRADING)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check ground briefing for transitions
        if self.ground_briefing_view and self.ground_briefing_view.active:
            next_state = self.ground_briefing_view.get_next_state()
            if next_state == GameState.GROUND_EXPLORATION:
                self.ground_briefing_view.next_state = None
                crew_ids = list(self.ground_briefing_view.selected_crew)
                config = self.ground_briefing_view.mission_config

                def _do():
                    from spacegame.models.ground_crew import GroundCrewBonuses

                    crew_bonuses = GroundCrewBonuses.compute(
                        crew_ids,
                        self.attribute_sheet if self.player else None,
                    )

                    gen_result = self._build_ground_map(config)
                    mission_state = gen_result.build_mission_state(
                        crew_bonuses,
                        self.attribute_sheet if self.player else None,
                        self.player.progression if self.player else None,
                    )
                    from spacegame.views.ground_exploration_view import (
                        GroundExplorationView,
                    )

                    self.ground_exploration_view = GroundExplorationView(
                        self.ui_manager,
                        mission_state.ground_map,
                        mission_state.player,
                        mission_state,
                        mission_config=config,
                    )
                    self.ground_exploration_view._crew_ids = crew_ids
                    self.state_manager.register_state(
                        GameState.GROUND_EXPLORATION,
                        self.ground_exploration_view,
                    )
                    self.state_manager.change_state(GameState.GROUND_EXPLORATION)

                self._start_transition(TransitionType.PIXELATE, 0.5, _do)
            elif next_state is not None:
                # Cancel — return to previous state
                self.ground_briefing_view.next_state = None
                target = next_state

                def _do():
                    self.state_manager.change_state(target)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check ground exploration for transitions
        if self.ground_exploration_view and self.ground_exploration_view.active:
            next_state = self.ground_exploration_view.get_next_state()
            if next_state == GameState.GROUND_RESULT:
                self.ground_exploration_view.next_state = None
                outcome = self.ground_exploration_view._mission_outcome
                if outcome:
                    result = self.ground_exploration_view.get_mission_result(outcome)
                    if result:
                        self._apply_ground_result(result)
                        self._ensure_ground_result_view(result)

                        def _do():
                            self.state_manager.change_state(GameState.GROUND_RESULT)

                        self._start_transition(TransitionType.FADE, 0.3, _do)
            elif next_state == GameState.GALAXY_MAP:
                # No-config exit (backward compatibility)
                self.ground_exploration_view.next_state = None

                def _do():
                    self.state_manager.change_state(GameState.GALAXY_MAP)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check ground result for transitions
        if self.ground_result_view and self.ground_result_view.active:
            next_state = self.ground_result_view.get_next_state()
            if next_state is not None:
                self.ground_result_view.next_state = None
                target = next_state

                def _do():
                    self.auto_save()
                    self.state_manager.change_state(target)

                self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check shipyard for transitions
        if self.shipyard_view and self.shipyard_view.active:
            next_state = self.shipyard_view.get_next_state()
            if next_state == GameState.GALAXY_MAP:
                self.shipyard_view.next_state = None

                def _do():
                    self._ensure_station_hub_view()
                    self.state_manager.change_state(GameState.STATION_HUB)

                self._start_transition(TransitionType.FADE, 0.3, _do)

            elif next_state == GameState.SHIP_BUILDER:
                self.shipyard_view.next_state = None

                def _do_builder():
                    self._ensure_ship_builder_view()
                    self.state_manager.change_state(GameState.SHIP_BUILDER)

                self._start_transition(TransitionType.FADE, 0.3, _do_builder)

        # Check ship builder for transitions
        if hasattr(self, "ship_builder_view") and self.ship_builder_view:
            if self.ship_builder_view.active:
                next_state = self.ship_builder_view.get_next_state()
                if next_state == GameState.SHIPYARD:
                    self.ship_builder_view.next_state = None

                    def _do_builder_back():
                        self._ensure_shipyard_view()
                        self.state_manager.change_state(GameState.SHIPYARD)

                    self._start_transition(TransitionType.FADE, 0.3, _do_builder_back)

        # Check station hub view for transitions
        if hasattr(self, "station_hub_view") and self.station_hub_view:
            if self.station_hub_view.active:
                # Handle re-recruitment notification (no state change needed)
                rerecruit_id = getattr(self.station_hub_view, "pending_rerecruit_id", None)
                if rerecruit_id and self.crew_roster:
                    self.station_hub_view.pending_rerecruit_id = None
                    template = self.crew_roster.get_template(rerecruit_id)
                    name = template.name if template else rerecruit_id
                    self._mission_notifications.append(f"Crew Re-recruited: {name}")

                # Handle crew hire notification (no state change needed)
                hire_id = getattr(self.station_hub_view, "pending_hire_id", None)
                if hire_id and self.crew_roster:
                    self.station_hub_view.pending_hire_id = None
                    template = self.crew_roster.get_template(hire_id)
                    name = template.name if template else hire_id
                    self._mission_notifications.append(f"Crew Hired: {name}")

                # Handle station board contract acceptance
                contract_id = getattr(self.station_hub_view, "pending_contract_id", None)
                if contract_id and self.mission_manager:
                    self.station_hub_view.pending_contract_id = None
                    mission = self.mission_manager.get_mission(contract_id)
                    name = mission.name if mission else contract_id
                    self._mission_notifications.append(f"Contract Accepted: {name}")

                next_state = self.station_hub_view.get_next_state()
                if next_state == GameState.GALAXY_MAP:
                    self.station_hub_view.next_state = None

                    def _do():
                        self.state_manager.change_state(GameState.GALAXY_MAP)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.TRADING:
                    self.station_hub_view.next_state = None

                    def _do():
                        self.state_manager.change_state(GameState.TRADING)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.REPAIR_BAY:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_repair_bay_view()
                        self.state_manager.change_state(GameState.REPAIR_BAY)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.CANTINA:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_cantina_view()
                        self.state_manager.change_state(GameState.CANTINA)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.INVESTMENT:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_investment_view()
                        self.state_manager.change_state(GameState.INVESTMENT)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.MINING:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_mining_view()
                        self.state_manager.change_state(GameState.MINING)

                    self._start_transition(TransitionType.SLIDE, 0.3, _do)
                elif next_state == GameState.SALVAGING:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_salvage_view()
                        self.state_manager.change_state(GameState.SALVAGING)

                    self._start_transition(TransitionType.SLIDE, 0.3, _do)
                elif next_state == GameState.REFINING:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_refining_view()
                        self.state_manager.change_state(GameState.REFINING)

                    self._start_transition(TransitionType.SLIDE, 0.3, _do)
                elif next_state == GameState.SHIPYARD:
                    self.station_hub_view.next_state = None

                    def _do():
                        self._ensure_shipyard_view()
                        self.state_manager.change_state(GameState.SHIPYARD)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.DIALOGUE:
                    self.station_hub_view.next_state = None
                    npc_id = getattr(self.station_hub_view, "pending_npc_id", None)
                    if npc_id:
                        self.station_hub_view.pending_npc_id = None
                        self.start_dialogue(npc_id, return_state=GameState.STATION_HUB)

        # Check repair bay view for transitions
        if hasattr(self, "repair_bay_view") and self.repair_bay_view:
            if self.repair_bay_view.active:
                next_state = self.repair_bay_view.get_next_state()
                if next_state == GameState.STATION_HUB:
                    self.repair_bay_view.next_state = None

                    def _do():
                        self._ensure_station_hub_view()
                        self.state_manager.change_state(GameState.STATION_HUB)

                    self._start_transition(TransitionType.FADE, 0.3, _do)

        # Check cantina view for transitions
        if hasattr(self, "cantina_view") and self.cantina_view:
            if self.cantina_view.active:
                # Handle re-recruitment notification
                rerecruit_id = getattr(self.cantina_view, "pending_rerecruit_id", None)
                if rerecruit_id and self.crew_roster:
                    self.cantina_view.pending_rerecruit_id = None
                    template = self.crew_roster.get_template(rerecruit_id)
                    name = template.name if template else rerecruit_id
                    self._mission_notifications.append(f"Crew Re-recruited: {name}")

                # Handle crew hire notification
                hire_id = getattr(self.cantina_view, "pending_hire_id", None)
                if hire_id and self.crew_roster:
                    self.cantina_view.pending_hire_id = None
                    template = self.crew_roster.get_template(hire_id)
                    name = template.name if template else hire_id
                    self._mission_notifications.append(f"Crew Hired: {name}")

                # Handle station board contract acceptance
                contract_id = getattr(self.cantina_view, "pending_contract_id", None)
                if contract_id and self.mission_manager:
                    self.cantina_view.pending_contract_id = None
                    mission = self.mission_manager.get_mission(contract_id)
                    name = mission.name if mission else contract_id
                    self._mission_notifications.append(f"Contract Accepted: {name}")

                next_state = self.cantina_view.get_next_state()
                if next_state == GameState.STATION_HUB:
                    self.cantina_view.next_state = None

                    def _do():
                        self._ensure_station_hub_view()
                        self.state_manager.change_state(GameState.STATION_HUB)

                    self._start_transition(TransitionType.FADE, 0.3, _do)
                elif next_state == GameState.DIALOGUE:
                    self.cantina_view.next_state = None
                    npc_id = getattr(self.cantina_view, "pending_npc_id", None)
                    if npc_id:
                        self.cantina_view.pending_npc_id = None
                        self.start_dialogue(npc_id, return_state=GameState.CANTINA)

        # Check investment view for transitions
        if self.investment_view:
            if self.investment_view.active:
                next_state = self.investment_view.get_next_state()
                if next_state == GameState.STATION_HUB:
                    self.investment_view.next_state = None

                    def _do():
                        self._ensure_station_hub_view()
                        self.state_manager.change_state(GameState.STATION_HUB)

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
            politics_manager=self.politics_manager,
            news_ticker=self.news_ticker,
        )
        # Wire journal for quick-add overlay
        if self.journal:
            self.galaxy_map_view.journal = self.journal
        self.trading_view = TradingView(
            self.ui_manager,
            self.player,
            systems,
            commodities,
            activity_registry=self.activity_registry,
            active_events=self.active_events,
            price_history=self.price_history,
            smuggling_contract_manager=self.smuggling_contract_manager,
            politics_manager=self.politics_manager,
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
        self.combat_view = None
        self.encounter_view = None
        self.journal_view = None
        self.ground_briefing_view = None
        self.ground_exploration_view = None
        self.ground_result_view = None
        self.station_hub_view = None
        self.repair_bay_view = None

    # ==================================================================
    # VIEW FACTORIES (lines ~1777-2130)
    # 23 _ensure_*_view() methods. Each lazily imports its view class,
    # creates an instance with current game state, and registers it
    # with the state manager. Views are recreated on each visit to
    # ensure fresh data (locations, configs, mission state, etc.).
    # ==================================================================

    def _ensure_station_hub_view(self) -> None:
        """Create or recreate station hub view for current system."""
        from spacegame.views.station_hub_view import StationHubView

        system = self.data_loader.get_system(self.player.current_system_id)
        locations = self.data_loader.get_locations_for_system(self.player.current_system_id)

        # Generate procedural station board contracts (refresh each day)
        self._refresh_procedural_missions()

        self.station_hub_view = StationHubView(
            self.ui_manager,
            self.player,
            system,
            locations,
            activity_registry=self.activity_registry,
            data_loader=self.data_loader,
            politics_manager=self.politics_manager,
            crew_roster=self.crew_roster,
            station_chatter=self.station_chatter,
            mission_manager=self.mission_manager,
        )
        self.state_manager.register_state(GameState.STATION_HUB, self.station_hub_view)

    def _ensure_repair_bay_view(self) -> None:
        """Create or recreate repair bay view for current system."""
        from spacegame.views.repair_bay_view import RepairBayView

        locations = self.data_loader.get_locations_for_system(self.player.current_system_id)
        cost_per_hp = 10  # default
        location_name = "Repair Bay"
        location_flavor = ""
        for loc in locations:
            if loc.location_type == "repair_bay":
                if loc.repair_cost_per_hp > 0:
                    cost_per_hp = loc.repair_cost_per_hp
                location_name = loc.name
                location_flavor = loc.flavor_text
                break
        # Free repairs faction perk
        if self.politics_manager and self.politics_manager.has_perk(
            self.player, self.player.current_system_id, "free_repairs"
        ):
            cost_per_hp = 0
        self.repair_bay_view = RepairBayView(
            self.ui_manager,
            self.player,
            cost_per_hp=cost_per_hp,
            location_name=location_name,
            location_flavor=location_flavor,
        )
        self.state_manager.register_state(GameState.REPAIR_BAY, self.repair_bay_view)

    def _ensure_cantina_view(self) -> None:
        """Create or recreate cantina view for current system."""
        from spacegame.views.cantina_view import CantinaView

        locations = self.data_loader.get_locations_for_system(self.player.current_system_id)
        cantina_loc = None
        for loc in locations:
            if loc.location_type == "cantina":
                cantina_loc = loc
                break
        if not cantina_loc:
            return
        system = self.data_loader.get_system(self.player.current_system_id)
        self.cantina_view = CantinaView(
            self.ui_manager,
            self.player,
            system,
            cantina_loc,
            self.data_loader,
            crew_roster=self.crew_roster,
            mission_manager=self.mission_manager,
        )
        self.state_manager.register_state(GameState.CANTINA, self.cantina_view)

    def _ensure_investment_view(self) -> None:
        """Create or recreate investment view for current system."""
        from spacegame.views.investment_view import InvestmentView

        if not self.investment_manager:
            return
        self.investment_view = InvestmentView(
            ui_manager=self.ui_manager,
            player=self.player,
            investment_manager=self.investment_manager,
            system_id=self.player.current_system_id,
        )
        self.state_manager.register_state(GameState.INVESTMENT, self.investment_view)

    def _ensure_mining_view(self) -> None:
        """Create or recreate mining view for current system."""
        from spacegame.views.mining_view import MiningView

        mining_config = self.data_loader.get_mining_config(self.player.current_system_id)
        system = self.data_loader.systems.get(self.player.current_system_id)
        if system:
            mining_config.danger_level = system.danger_level
        if self.politics_manager:
            mining_config.perk_yield_bonus = self.politics_manager.get_perk_bonus(
                self.player, self.player.current_system_id, "mining_yield_bonus"
            )
            mining_config.perk_wholesale_bonus = self.politics_manager.get_perk_bonus(
                self.player, self.player.current_system_id, "wholesale_ore_bonus"
            )
        self.mining_view = MiningView(
            self.ui_manager,
            self.player,
            self.data_loader.commodities,
            mining_config=mining_config,
            progression=self.player.progression,
            drone_fleet=self.player.drone_fleet,
        )
        self.mining_view._get_crew_line = self._make_crew_commentary_fn()
        self.state_manager.register_state(GameState.MINING, self.mining_view)

    def _ensure_salvage_view(self) -> None:
        """Create or recreate salvage view for current system."""
        from spacegame.views.salvage_view import SalvageView

        salvage_config = self.data_loader.get_salvage_config(self.player.current_system_id)
        system = self.data_loader.systems.get(self.player.current_system_id)
        if system:
            salvage_config.danger_level = system.danger_level
        if self.politics_manager:
            salvage_config.perk_yield_bonus = self.politics_manager.get_perk_bonus(
                self.player, self.player.current_system_id, "salvage_yield_bonus"
            )
        self.salvage_view = SalvageView(
            self.ui_manager,
            self.player,
            self.data_loader.commodities,
            salvage_config=salvage_config,
            progression=self.player.progression,
        )
        self.salvage_view._get_crew_line = self._make_crew_commentary_fn()
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
        self.refining_view._get_crew_line = self._make_crew_commentary_fn()
        self.state_manager.register_state(GameState.REFINING, self.refining_view)

    def _ensure_skill_tree_view(self) -> None:
        """Create or recreate skill tree view."""
        from spacegame.views.skill_tree_view import SkillTreeView

        self.skill_tree_view = SkillTreeView(
            self.ui_manager,
            self.player.progression,
            player=self.player,
        )
        self.state_manager.register_state(GameState.SKILL_TREE, self.skill_tree_view)

    def _ensure_character_creation_view(self) -> None:
        """Create character creation view for attribute allocation."""
        from spacegame.views.character_creation_view import CharacterCreationView

        self.character_creation_view = CharacterCreationView(
            self.ui_manager,
            self.attribute_sheet,
        )
        self.state_manager.register_state(
            GameState.CHARACTER_CREATION, self.character_creation_view
        )

    def _ensure_character_view(self) -> None:
        """Create or recreate character screen view."""
        from spacegame.views.character_view import CharacterView

        self.character_view = CharacterView(
            self.ui_manager,
            self.player,
            self.attribute_sheet,
            self.social_manager,
            politics_manager=self.politics_manager,
        )
        self.state_manager.register_state(GameState.CHARACTER, self.character_view)

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

        self.dialogue_view = DialogueView(
            self.ui_manager, self.dialogue_manager, self.data_loader, self.social_manager
        )
        self.state_manager.register_state(GameState.DIALOGUE, self.dialogue_view)

    def _ensure_mission_log_view(self) -> None:
        """Create or recreate mission log view."""
        from spacegame.views.mission_log_view import MissionLogView

        self.mission_log_view = MissionLogView(self.ui_manager, self.mission_manager)
        self.state_manager.register_state(GameState.MISSION_LOG, self.mission_log_view)

    def _ensure_journal_view(self) -> None:
        """Create or recreate journal view."""
        from spacegame.views.journal_view import JournalView

        self.journal_view = JournalView(
            self.ui_manager,
            self.journal,
            self.player.game_day if self.player else 1,
            self.player.current_system_id if self.player else "",
            mission_manager=self.mission_manager,
        )
        self.state_manager.register_state(GameState.JOURNAL, self.journal_view)

    def _ensure_crew_roster_view(self) -> None:
        """Create or recreate crew roster view."""
        from spacegame.views.crew_roster_view import CrewRosterView

        crew_slots = (
            self.player.ship.ship_type.crew_slots
            + int(self.player.progression.get_bonus("crew_slot_bonus"))
            if self.player
            else 1
        )
        from spacegame.models.mission import MissionStatus as _MS

        active_ids = (
            [m.id for m in self.mission_manager.get_missions_by_status(_MS.ACTIVE)]
            if self.mission_manager
            else []
        )
        self.crew_roster_view = CrewRosterView(
            self.ui_manager,
            self.crew_roster,
            crew_slots,
            active_mission_ids=active_ids,
        )
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

        # Select dialogue music based on NPC (default neutral, emotional NPCs get intimate)
        self._dialogue_music = (
            getattr(npc, "dialogue_music", "dialogue_neutral") or "dialogue_neutral"
        )

        # Sync flags and social state from player before starting
        self.dialogue_manager.load_flags(self.player.dialogue_flags)
        self.social_manager.load_state(self.player.social_state)

        # Detect if player sold the cargo broker's iron ore
        if npc_id == "delivery_merchant" and self.mission_manager:
            from spacegame.models.mission import MissionStatus

            iron_status = self.mission_manager.get_status("iron_delivery")
            has_ore = self.player.ship.get_cargo_quantity("iron_ore") >= 10
            if (
                iron_status == MissionStatus.ACTIVE
                and not has_ore
                and not self.player.dialogue_flags.get("iron_ore_delivered", False)
            ):
                self.player.dialogue_flags["broker_ore_sold"] = True
                self.dialogue_manager.set_flag("broker_ore_sold")

        # Apply faction-based disposition modifier to NPC
        if self.politics_manager and npc.faction_id:
            disp_mod = self.politics_manager.get_npc_disposition_modifier(
                self.player, npc.faction_id
            )
            if disp_mod != 0:
                self.social_manager.modify_disposition(npc_id, disp_mod)
                logger.info(f"Applied faction disposition modifier to {npc_id}: {disp_mod:+d}")

        self.dialogue_manager.start_dialogue(tree, npc_id=npc_id)
        self._ensure_dialogue_view()
        self.dialogue_view._return_state = return_state

        def _do() -> None:
            self.state_manager.change_state(GameState.DIALOGUE)

        self._start_transition(TransitionType.FADE, 0.3, _do)
        logger.info(f"Starting dialogue with {npc.name}")

    def _start_intro_narration(self, return_state: GameState = GameState.GALAXY_MAP) -> None:
        """Start the intro backstory narration sequence.

        Args:
            return_state: State to transition to when narration ends.
        """
        tree = self.data_loader.get_dialogue("intro_narration")
        if not tree:
            # Fallback: skip narration, go to return state directly
            def _do() -> None:
                if return_state == GameState.NAME_INPUT:
                    self._ensure_name_input_view()
                self.state_manager.change_state(return_state)

            self._start_transition(TransitionType.FADE, 0.5, _do)
            return

        self._last_dialogue_npc_id = None  # No NPC for narration
        self._dialogue_music = "dialogue_intimate"  # Narration is emotional
        self.dialogue_manager.start_dialogue(tree)
        self._ensure_dialogue_view()
        self.dialogue_view._return_state = return_state

        def _do() -> None:
            self.state_manager.change_state(GameState.DIALOGUE)

        self._start_transition(TransitionType.FADE, 0.5, _do)
        logger.info("Starting intro narration")

    def _ensure_name_input_view(self) -> None:
        """Create or recreate name input view."""
        from spacegame.views.name_input_view import NameInputView

        self.name_input_view = NameInputView(self.ui_manager)
        self.state_manager.register_state(GameState.NAME_INPUT, self.name_input_view)

    def _ensure_combat_view(
        self, engine: "CombatEngine", return_state: GameState = GameState.TRADING
    ) -> None:
        """Create combat view with a prepared engine.

        Args:
            engine: CombatEngine instance with initialized state.
            return_state: State to return to when combat ends.
        """
        from spacegame.views.combat_view import CombatView

        self.combat_view = CombatView(self.ui_manager, engine, self.player, self.social_manager)
        self.combat_view._return_state = return_state
        if self.player:
            self.combat_view._bribe_credits_available = self.player.credits
        self.state_manager.register_state(GameState.COMBAT, self.combat_view)

    def start_combat(
        self,
        encounter: "CombatEncounter",
        return_state: GameState = GameState.TRADING,
        transition_type: TransitionType = TransitionType.FADE,
    ) -> None:
        """Initialize and enter a combat encounter.

        Args:
            encounter: CombatEncounter defining enemies and seed.
            return_state: State to return to when combat ends.
            transition_type: Visual transition to use (FADE or WARP).
        """
        from spacegame.models.combat import (
            CombatState,
            EnemyShip,
            build_player_combat_state,
        )
        from spacegame.models.combat_engine import CombatEngine

        crew_moves = self._get_crew_combat_moves()
        player_state = build_player_combat_state(
            self.player.ship,
            self.player.upgrade_manager,
            self.crew_roster,
            crew_moves,
            player_level=self.player.progression.level,
            progression=self.player.progression,
        )
        enemies = [EnemyShip.from_template(t) for t in encounter.enemy_templates]
        combat_state = CombatState(
            player=player_state,
            enemies=enemies,
            encounter=encounter,
            combat_log=[],
        )
        engine = CombatEngine(combat_state, seed=encounter.encounter_seed)
        self._ensure_combat_view(engine, return_state)

        def _do() -> None:
            self.state_manager.change_state(GameState.COMBAT)

        duration = 0.6 if transition_type == TransitionType.WARP else 0.4
        self._start_transition(transition_type, duration, _do)
        logger.info("Starting combat encounter")

    def _resolve_encounter_ref(self, ref: "EncounterRef") -> Optional["CombatEncounter"]:
        """Resolve an EncounterRef (template IDs) into a full CombatEncounter.

        Args:
            ref: EncounterRef with enemy template IDs and seed.

        Returns:
            CombatEncounter with resolved templates, or None if templates missing.
        """
        from spacegame.models.combat import CombatEncounter

        templates = []
        for tid in ref.enemy_template_ids:
            template = self.data_loader.enemy_templates.get(tid)
            if template:
                templates.append(template)

        if not templates:
            return None

        return CombatEncounter(
            enemy_templates=templates,
            encounter_seed=ref.encounter_seed,
        )

    def _resolve_bounty_combat(self, enemy_ids: list[str]) -> Optional["CombatEncounter"]:
        """Resolve bounty hunter enemy IDs into a CombatEncounter.

        Args:
            enemy_ids: List of bounty hunter enemy template IDs.

        Returns:
            CombatEncounter or None if templates missing.
        """
        from spacegame.models.combat import CombatEncounter

        templates = []
        for tid in enemy_ids:
            template = self.data_loader.enemy_templates.get(tid)
            if template:
                templates.append(template)

        if not templates:
            return None

        seed = hash(f"{self.player.game_day}_bounty_combat") & 0xFFFFFFFF
        return CombatEncounter(
            enemy_templates=templates,
            encounter_seed=seed,
        )

    def _resolve_encounter_definition(self, ref: "EncounterRef") -> Optional["EncounterDefinition"]:
        """Select an encounter definition for a non-hostile encounter.

        Args:
            ref: EncounterRef with type and seed.

        Returns:
            EncounterDefinition or None if no definitions match.
        """
        from spacegame.models.encounter import (
            EncounterContext,
            lookup_encounter_definition,
            select_encounter_definition,
        )

        # Direct lookup by ID (scripted/forced encounters)
        if ref.encounter_def_id:
            defn = lookup_encounter_definition(
                self.data_loader.encounter_definitions,
                ref.encounter_def_id,
            )
            if defn:
                return defn

        # Random weighted selection (procedural encounters)
        danger = "moderate"
        system_id = ""
        faction_id = ""
        if self.player:
            system_id = self.player.current_system_id
            system = self.data_loader.systems.get(system_id)
            if system:
                danger = getattr(system, "danger_level", "moderate")
                faction_id = getattr(system, "faction_id", "")

        context = EncounterContext(
            encounter_type=ref.encounter_type,
            danger_level=danger,
            seed=ref.encounter_seed,
            system_id=system_id,
            faction_id=faction_id,
            player_level=self.player.progression.level if self.player else 1,
            dialogue_flags=self.player.dialogue_flags if self.player else {},
        )

        defn = select_encounter_definition(
            self.data_loader.encounter_definitions,
            context,
        )
        if defn:
            ref.encounter_def_id = defn.id
        return defn

    def _ensure_encounter_view(
        self,
        encounter_def: "EncounterDefinition",
        encounter_ref: "EncounterRef",
    ) -> None:
        """Create encounter view for a non-hostile encounter.

        Args:
            encounter_def: The selected encounter definition.
            encounter_ref: The encounter reference from travel.
        """
        from spacegame.views.encounter_view import EncounterView

        self.encounter_view = EncounterView(self.ui_manager, encounter_def, encounter_ref)
        self.state_manager.register_state(GameState.ENCOUNTER, self.encounter_view)

    def _check_bounty_hunter_encounter(self) -> bool:
        """Check for and trigger a bounty hunter encounter on arrival.

        Evaluates criminal heat against bounty hunter thresholds. If triggered,
        builds a pre-combat encounter with surrender/fight/negotiate/bribe choices.

        Returns:
            True if bounty hunter encounter was triggered.
        """
        if not self.player:
            return False

        # Check bounty immunity
        if self.player.game_day < self._bounty_immunity_until:
            return False

        system_id = self.player.current_system_id

        has_signal_jammer = self.player.upgrade_manager.has_upgrade("signal_jammer")
        has_false_transponder = self.player.upgrade_manager.has_upgrade("false_transponder")

        from spacegame.models.smuggling import (
            build_bounty_hunter_encounter,
            get_bounty_hunter_tier,
            should_trigger_bounty_hunter,
        )

        triggered = should_trigger_bounty_hunter(
            criminal_heat=self.player.criminal_heat,
            game_day=self.player.game_day,
            system_id=system_id,
            has_signal_jammer=has_signal_jammer,
            has_false_transponder=has_false_transponder,
        )

        if not triggered:
            return False

        tier = get_bounty_hunter_tier(self.player.criminal_heat)
        if tier is None:
            return False

        # Get persuasion level
        persuasion_level = 0
        if self.social_manager:
            p_skill = self.social_manager.get_skill("persuasion")
            if p_skill:
                persuasion_level = p_skill.level

        seed = hash(f"{self.player.game_day}_{system_id}_bounty") & 0xFFFFFFFF

        encounter_def = build_bounty_hunter_encounter(
            tier=tier,
            criminal_heat=self.player.criminal_heat,
            player_credits=self.player.credits,
            persuasion_level=persuasion_level,
            seed=seed,
        )

        from spacegame.models.encounter import EncounterRef

        encounter_ref = EncounterRef(
            enemy_template_ids=[],
            encounter_seed=seed,
            encounter_type="bounty_hunter",
        )

        self._ensure_encounter_view(encounter_def, encounter_ref)

        def _do() -> None:
            self.state_manager.change_state(GameState.ENCOUNTER)

        self._start_transition(TransitionType.FADE, 0.4, _do)
        logger.info(
            f"Bounty hunter encounter triggered at {system_id} "
            f"(heat={self.player.criminal_heat}, tier={tier.value})"
        )
        return True

    def _check_customs_inspection(self) -> bool:
        """Check for and trigger a customs inspection on arrival.

        Evaluates the local faction's law enforcement rules against the
        player's cargo, criminal heat, upgrades, and skills. If an inspection
        triggers, builds a dynamic encounter and routes to ENCOUNTER state.

        Returns:
            True if inspection was triggered (caller should return early).
        """
        if not self.player or not self.data_loader:
            return False

        system_id = self.player.current_system_id
        faction_id = self.player.get_faction_for_system(system_id)
        if not faction_id:
            return False

        faction_law = self.data_loader.faction_laws.get(faction_id)
        if not faction_law or faction_law.inspection_chance <= 0:
            return False

        # Determine cargo legality
        cargo = dict(self.player.ship.current_cargo)
        if not cargo:
            return False  # Nothing to inspect

        legality_map: dict[str, "Legality"] = {}
        has_restricted = False
        has_illegal = False
        for commodity_id in cargo:
            commodity = self.data_loader.commodities.get(commodity_id)
            if commodity:
                from spacegame.models.commodity import Legality

                legality_map[commodity_id] = commodity.legality
                if commodity.legality == Legality.RESTRICTED:
                    has_restricted = True
                elif commodity.legality == Legality.ILLEGAL:
                    has_illegal = True
            else:
                legality_map[commodity_id] = Legality.LEGAL

        # Check upgrade modifiers
        has_hidden_compartment = self.player.upgrade_manager.has_upgrade("hidden_compartment")
        has_signal_jammer = self.player.upgrade_manager.has_upgrade("signal_jammer")
        has_false_transponder = self.player.upgrade_manager.has_upgrade("false_transponder")

        # Get observation skill level
        observation_level = 0
        if self.social_manager:
            obs_skill = self.social_manager.get_skill("observation")
            if obs_skill:
                observation_level = obs_skill.level

        faction_reputation = self.player.get_reputation(faction_id)

        from spacegame.models.smuggling import should_trigger_inspection

        triggered = should_trigger_inspection(
            faction_law=faction_law,
            criminal_heat=self.player.criminal_heat,
            has_restricted=has_restricted,
            has_illegal=has_illegal,
            has_hidden_compartment=has_hidden_compartment,
            has_signal_jammer=has_signal_jammer,
            has_false_transponder=has_false_transponder,
            observation_level=observation_level,
            faction_reputation=faction_reputation,
            game_day=self.player.game_day,
            system_id=system_id,
        )

        if not triggered:
            return False

        # Build price map for fine calculation
        price_map: dict[str, int] = {}
        for commodity_id in cargo:
            commodity = self.data_loader.commodities.get(commodity_id)
            if commodity:
                price_map[commodity_id] = commodity.base_price

        # Get social skill levels
        persuasion_level = 0
        intimidation_level = 0
        if self.social_manager:
            p_skill = self.social_manager.get_skill("persuasion")
            if p_skill:
                persuasion_level = p_skill.level
            i_skill = self.social_manager.get_skill("intimidation")
            if i_skill:
                intimidation_level = i_skill.level

        # Get faction display name
        faction = self.data_loader.factions.get(faction_id)
        faction_name = faction.name if faction else faction_id

        from spacegame.models.smuggling import build_inspection_encounter

        encounter_def = build_inspection_encounter(
            faction_law=faction_law,
            faction_name=faction_name,
            cargo=cargo,
            legality_map=legality_map,
            price_map=price_map,
            player_credits=self.player.credits,
            persuasion_level=persuasion_level,
            intimidation_level=intimidation_level,
        )

        from spacegame.models.encounter import EncounterRef

        encounter_ref = EncounterRef(
            enemy_template_ids=[],
            encounter_seed=hash(f"{self.player.game_day}_{system_id}_customs") & 0xFFFFFFFF,
            encounter_type="customs_inspection",
        )

        self._ensure_encounter_view(encounter_def, encounter_ref)

        def _do() -> None:
            self.state_manager.change_state(GameState.ENCOUNTER)

        self._start_transition(TransitionType.FADE, 0.4, _do)
        logger.info(f"Customs inspection triggered at {system_id}")
        return True

    def _check_ground_mission_trigger(self) -> bool:
        """Check if an active campaign mission has a ground mission at the current system.

        Queries MissionManager for ground mission triggers matching the
        current system. If found, builds a GroundMissionConfig and launches
        the briefing screen.

        Returns:
            True if a ground mission was triggered, False otherwise.
        """
        if not self.player or not self.mission_manager:
            return False

        trigger = self.mission_manager.get_ground_mission_trigger(
            self.player.current_system_id,
            self.player.dialogue_flags,
        )
        if not trigger:
            return False

        ground_mission_id, complete_flag = trigger

        # Build config from campaign data
        from spacegame.models.ground_mission import (
            DifficultyTier,
            GroundMissionConfig,
            GroundMissionRewards,
            MissionType,
        )

        # Look up the parent mission for metadata
        from spacegame.models.mission import MissionStatus

        parent_mission = None
        for m in self.mission_manager.get_missions_by_status(MissionStatus.ACTIVE):
            if m.ground_mission_id == ground_mission_id:
                parent_mission = m
                break

        name = parent_mission.name if parent_mission else ground_mission_id
        description = parent_mission.description if parent_mission else "Campaign ground mission."

        # Determine faction from system
        system = self.data_loader.systems.get(self.player.current_system_id)
        faction_id = getattr(system, "faction_id", "") if system else ""

        config = GroundMissionConfig(
            id=ground_mission_id,
            name=name,
            description=description,
            mission_type=MissionType.INFILTRATION,
            difficulty=DifficultyTier.MODERATE,
            faction_id=faction_id,
            objectives=[f"Complete {name}"],
            intel_hints=[],
            rewards=GroundMissionRewards(credits=0, xp=0),
            campaign_mission_id=parent_mission.id if parent_mission else None,
            complete_flag=complete_flag,
        )

        self.start_ground_mission(config)
        logger.info(
            "Ground mission triggered: %s at %s",
            ground_mission_id,
            self.player.current_system_id,
        )
        return True

    def _apply_encounter_result(self) -> None:
        """Apply rewards from a completed encounter to player state."""
        if not self.encounter_view or not self.player:
            return

        outcome = self.encounter_view.chosen_outcome
        if not outcome:
            return

        self.player.encounters_survived += 1

        for reward in outcome.rewards:
            if reward.reward_type == "credits":
                self.player.credits += reward.amount
                logger.info(f"Encounter reward: +{reward.amount} credits")
            elif reward.reward_type == "deduct_credits":
                amount = reward.amount
                if self.player.credits >= amount:
                    self.player.credits -= amount
                    logger.info(f"Encounter cost: -{amount} credits")
                else:
                    logger.info("Encounter: insufficient credits — waived")
            elif reward.reward_type == "xp":
                xp_msgs = self.player.progression.add_xp(reward.amount)
                for msg in xp_msgs:
                    self._mission_notifications.append(msg)
                logger.info(f"Encounter reward: +{reward.amount} XP")
            elif reward.reward_type == "set_flag":
                if reward.target_id:
                    self.player.dialogue_flags[reward.target_id] = True
                    if self.dialogue_manager:
                        self.dialogue_manager.set_flag(reward.target_id)
                    logger.info(f"Encounter flag set: {reward.target_id}")
            elif reward.reward_type == "add_criminal_heat":
                self.player.add_criminal_heat(reward.amount)
                self.player.times_caught_smuggling += 1
                logger.info(f"Encounter: +{reward.amount} criminal heat")
                self._trigger_crew_reaction("smuggling_caught")
            elif reward.reward_type == "modify_reputation":
                if reward.target_id:
                    if self.politics_manager:
                        self.politics_manager.apply_reputation_with_spillover(
                            self.player, reward.target_id, reward.amount
                        )
                    else:
                        self.player.modify_reputation(reward.target_id, reward.amount)
                    logger.info(f"Encounter: {reward.amount} reputation with {reward.target_id}")
            elif reward.reward_type == "confiscate_cargo":
                if reward.target_id:
                    qty = self.player.ship.get_cargo_quantity(reward.target_id)
                    remove_qty = min(qty, reward.amount)
                    if remove_qty > 0:
                        self.player.ship.remove_cargo(reward.target_id, remove_qty)
                        logger.info(f"Encounter: confiscated {remove_qty} {reward.target_id}")
            elif reward.reward_type == "reduce_criminal_heat":
                self.player.decay_criminal_heat(reward.amount)
                logger.info(f"Encounter: -{reward.amount} criminal heat")
            elif reward.reward_type == "bounty_immunity":
                self._bounty_immunity_until = self.player.game_day + reward.amount
                logger.info(f"Encounter: bounty immunity for {reward.amount} days")
            elif reward.reward_type == "start_bounty_combat":
                # Transition to combat with bounty hunter enemies
                self._pending_bounty_combat_ids = (
                    reward.target_id.split(",") if reward.target_id else []
                )
                logger.info("Encounter: starting bounty hunter combat")

        # Mark unique encounters as seen so they don't repeat
        enc_def = getattr(self.encounter_view, "encounter_def", None)
        if enc_def and getattr(enc_def, "unique", False):
            flag = f"encounter_seen_{enc_def.id}"
            self.player.dialogue_flags[flag] = True
            if self.dialogue_manager:
                self.dialogue_manager.set_flag(flag)
            logger.info(f"Unique encounter seen: {flag}")

    def _get_crew_combat_moves(self) -> dict:
        """Build crew_template_id -> list[CombatMove] mapping from active crew.

        Uses combat_moves (plural, 4 abilities) if available, falls back
        to the legacy single combat_move field.
        """
        from spacegame.models.combat import CombatMove

        moves: dict[str, list[CombatMove]] = {}
        if self.crew_roster:
            for template, _state in self.crew_roster.get_recruited_members():
                crew_moves: list[CombatMove] = []
                # New: multiple combat moves per crew member
                if template.combat_moves:
                    for move_data in template.combat_moves:
                        crew_moves.append(self.data_loader._parse_combat_move(move_data))
                # Legacy fallback: single combat_move
                elif template.combat_move:
                    crew_moves.append(self.data_loader._parse_combat_move(template.combat_move))
                if crew_moves:
                    moves[template.id] = crew_moves
        return moves

    def _apply_combat_result(self) -> None:
        """Apply combat outcome to persistent player state.

        Syncs hull/shields, awards XP, generates and distributes loot,
        handles bribe costs, negotiation outcomes, or applies defeat penalties.
        """
        if not self.combat_view or not self.player:
            return

        from spacegame.models.combat import CombatResult
        from spacegame.views.combat_view import _roll_loot

        state = self.combat_view.engine.get_state()
        result = state.result

        # Sync hull/shields back to player's ship
        self.player.ship.current_hull = state.player.hull
        self.player.ship.current_shields = state.player.shields

        if result == CombatResult.VICTORY:
            self.player.combats_won += 1
            total_xp = sum(e.template.xp_reward for e in state.enemies)
            xp_msgs = self.player.progression.add_xp(total_xp)
            for msg in xp_msgs:
                self._mission_notifications.append(msg)

            # Distribute loot to player cargo
            for enemy in state.enemies:
                if not enemy.is_alive and enemy.template.loot_table:
                    loot = _roll_loot(
                        enemy.template.loot_table,
                        seed=state.encounter.encounter_seed + hash(enemy.template.id),
                    )
                    for commodity_id, qty in loot.items():
                        self.player.ship.add_cargo(commodity_id, qty)
                        logger.info(f"Combat loot: +{qty} {commodity_id}")
                # Distribute rare loot
                if not enemy.is_alive and enemy.template.rare_loot:
                    rare_loot = _roll_loot(
                        enemy.template.rare_loot,
                        seed=state.encounter.encounter_seed + hash(enemy.template.id) + 7919,
                    )
                    for commodity_id, qty in rare_loot.items():
                        self.player.ship.add_cargo(commodity_id, qty)
                        logger.info(f"Combat rare loot: +{qty} {commodity_id}")

            # Award credit rewards from defeated enemies
            total_credits = sum(e.template.credit_reward for e in state.enemies if not e.is_alive)
            if total_credits > 0:
                self.player.add_credits(total_credits)
                logger.info(f"Combat loot: +{total_credits} credits")

            logger.info(f"Combat victory: +{total_xp} XP")
            self._trigger_crew_reaction("combat_victory")

        elif result == CombatResult.DEFEAT:
            safe_system = self.player.current_system_id
            self.player.apply_combat_defeat(safe_system)
            logger.info("Combat defeat: cargo lost, retreated")

        elif result == CombatResult.FLED:
            self.player.combats_fled += 1
            logger.info("Combat: player fled")
            self._trigger_crew_reaction("combat_retreat")

        elif result == CombatResult.NEGOTIATED:
            self.player.combats_won += 1
            self.player.combats_negotiated += 1

            # Enhanced negotiate: partial loot (50% of normal loot)
            if state.negotiate_partial_loot:
                for enemy in state.enemies:
                    if enemy.template.loot_table:
                        loot = _roll_loot(
                            enemy.template.loot_table,
                            seed=state.encounter.encounter_seed + hash(enemy.template.id),
                        )
                        for commodity_id, qty in loot.items():
                            half_qty = max(1, qty // 2)
                            self.player.ship.add_cargo(commodity_id, half_qty)
                            logger.info(f"Negotiated partial loot: +{half_qty} {commodity_id}")

            # Enhanced negotiate: rival faction rep from intimidation
            if state.negotiate_rival_rep and self.politics_manager:
                # Intimidation success earns +2 rep with the enemy's faction
                enemy_faction = state.enemies[0].template.faction_id if state.enemies else None
                if enemy_faction:
                    self.politics_manager.apply_reputation_with_spillover(
                        self.player, enemy_faction, 2
                    )
                    logger.info(f"Combat: intimidation success — +2 rep with {enemy_faction}")
                else:
                    logger.info("Combat: intimidation success — no faction to reward")

            logger.info("Combat: negotiated resolution")

        elif result == CombatResult.BRIBED:
            self.player.combats_bribed += 1
            # Deduct bribe cost from player credits
            bribe_cost = getattr(self.combat_view, "_bribe_cost", 0)
            if bribe_cost > 0:
                self.player.credits -= bribe_cost
                logger.info(f"Combat: bribed enemies for {bribe_cost} CR")
            else:
                logger.info("Combat: bribed (no cost)")

            # Bribing an enemy faction earns -1 rep (you're funding them)
            if self.politics_manager:
                enemy_faction = state.enemies[0].template.faction_id if state.enemies else None
                if enemy_faction:
                    self.politics_manager.apply_reputation_with_spillover(
                        self.player, enemy_faction, -1
                    )
                    logger.info(f"Combat: bribe — -1 rep with {enemy_faction}")

    def _trigger_crew_reaction(self, action_type: str) -> None:
        """Trigger a crew ambient reaction to a player action.

        Picks a random matching line from any recruited crew member and
        queues it as a mission notification.

        Args:
            action_type: The player action (e.g. "sold_cargo", "combat_victory").
        """
        if not self.ambient_dialogue or not self.crew_roster:
            return
        recruited = [t.id for t, _ in self.crew_roster.get_recruited_members()]
        if not recruited:
            return
        loyalty_map = {}
        for tid in recruited:
            state = self.crew_roster.get_member_state(tid)
            loyalty_map[tid] = state["loyalty"] if state else 0
        result = self.ambient_dialogue.get_player_action_line(
            action_type=action_type,
            recruited_ids=recruited,
            loyalty_map=loyalty_map,
        )
        if result:
            crew_id, text = result
            template = self.crew_roster.get_template(crew_id)
            name = template.name if template else crew_id
            self._mission_notifications.append(f'{name}: "{text}"')

    # === Ground Mission Methods ===

    def _ensure_ground_briefing_view(self, config: "GroundMissionConfig") -> None:
        """Create and register the ground briefing view.

        Args:
            config: Ground mission configuration for briefing display.
        """
        from spacegame.views.ground_briefing_view import GroundBriefingView

        skill_levels: dict[str, int] = {}
        if self.social_manager:
            for sid in ("observation", "persuasion", "intimidation"):
                skill_levels[sid] = self.social_manager.get_skill_level(sid)
        self.ground_briefing_view = GroundBriefingView(
            self.ui_manager,
            config,
            self.crew_roster if self.crew_roster else self._make_empty_crew_roster(),
            skill_levels,
        )
        self.state_manager.register_state(GameState.GROUND_BRIEFING, self.ground_briefing_view)

    def _ensure_ground_result_view(self, result: "GroundMissionResult") -> None:
        """Create and register the ground result view.

        Args:
            result: Ground mission result to display.
        """
        from spacegame.views.ground_result_view import GroundResultView

        self.ground_result_view = GroundResultView(self.ui_manager, result)
        self.state_manager.register_state(GameState.GROUND_RESULT, self.ground_result_view)

    def get_ground_contracts(self) -> list:
        """Get available ground contracts at the current system.

        Generates contracts if none exist for this system/day combo,
        then returns non-expired, non-completed contracts.

        Returns:
            List of available GroundContract instances.
        """
        if not self.player or not self.ground_contract_manager:
            return []

        system_id = self.player.current_system_id
        game_day = self.player.game_day
        faction_id = self.player.faction_assignments.get(system_id, "independent")
        level = self.player.progression.level

        # Check if we already have contracts for this system+day
        available = self.ground_contract_manager.get_available(system_id, game_day)
        if not available:
            # Generate new contracts for this visit
            self.ground_contract_manager.generate_contracts(system_id, faction_id, game_day, level)
            available = self.ground_contract_manager.get_available(system_id, game_day)

        return available

    def accept_ground_contract(self, contract_id: str) -> None:
        """Accept a ground contract and launch the mission.

        Args:
            contract_id: ID of the contract to accept.
        """
        if not self.ground_contract_manager:
            return

        for c in self.ground_contract_manager.active_contracts:
            if c.id == contract_id and not c.completed:
                self.start_ground_mission(c.config)
                return

    def start_ground_mission(self, config: "GroundMissionConfig") -> None:
        """Launch a ground mission by opening the briefing screen.

        Args:
            config: Ground mission configuration.
        """
        self._ensure_ground_briefing_view(config)
        self.state_manager.change_state(GameState.GROUND_BRIEFING)
        logger.info("Starting ground mission: %s", config.name)

    def _apply_ground_result(self, result: "GroundMissionResult") -> None:
        """Apply ground mission outcome to persistent player state.

        Awards credits, XP, crew XP on success. Applies consequence
        curve penalties on failure. Extraction keeps loot only.

        Args:
            result: The completed mission result.
        """
        if not self.player:
            return

        from spacegame.models.ground_mission import (
            GHOST_RUN_BONUS_PERCENT,
            MissionOutcome,
        )

        outcome = result.outcome

        # Apply ground loot bonus from skills and crew
        loot_bonus = self.player.progression.get_bonus("ground_loot_bonus")
        if self.crew_roster:
            loot_bonus += self.crew_roster.get_bonus("ground_loot_bonus")
        boosted_loot = round(result.loot_credits * (1.0 + loot_bonus))

        if outcome == MissionOutcome.SUCCESS:
            # Mission reward + loot (with bonus)
            total = result.config.rewards.credits + boosted_loot
            # Ghost bonus
            if result.is_ghost_run:
                total += int(result.config.rewards.credits * GHOST_RUN_BONUS_PERCENT / 100)
            self.player.credits += total

            # XP
            if result.config.rewards.xp > 0:
                xp_msgs = self.player.progression.add_xp(result.config.rewards.xp)
                for msg in xp_msgs:
                    self._mission_notifications.append(msg)

            # Crew XP — award to participating crew members
            if result.crew_ids and result.config.rewards.crew_xp > 0 and self.crew_roster:
                for crew_id in result.crew_ids:
                    state = self.crew_roster._state.get(crew_id)
                    if state is not None:
                        state["xp"] = state.get("xp", 0) + result.config.rewards.crew_xp

            # Reputation
            for faction_id, rep in result.config.rewards.reputation.items():
                if hasattr(self.player, "faction_reputation"):
                    self.player.faction_reputation.modify(faction_id, rep)

            # Complete associated contract (awards bonus credits)
            if self.ground_contract_manager:
                ok, msg = self.ground_contract_manager.complete_contract(result.config.id)
                if ok:
                    # Find the contract to get bonus amount
                    for gc in self.ground_contract_manager.active_contracts:
                        if gc.id == result.config.id:
                            self.player.credits += gc.bonus_credits
                            total += gc.bonus_credits
                            break

            logger.info(
                "Ground mission success: +%d CR, +%d XP",
                total,
                result.config.rewards.xp,
            )

        elif outcome == MissionOutcome.EXTRACTED:
            # Keep loot (with bonus), no mission reward
            self.player.credits += boosted_loot
            logger.info("Ground mission extracted: +%d CR loot", boosted_loot)

        elif outcome.is_failure:
            # Apply consequence curve penalties
            penalties = result.calculate_penalties()
            credit_loss = int(self.player.credits * penalties["credit_loss_percent"] / 100)
            self.player.credits -= credit_loss

            # Partial loot (with bonus applied to kept portion)
            kept_loot = int(boosted_loot * penalties["loot_kept_percent"] / 100)
            self.player.credits += kept_loot

            # XP penalty
            if penalties["xp_penalty"] > 0:
                self.player.progression.add_xp(-penalties["xp_penalty"])

            logger.info(
                "Ground mission %s: -%d CR penalty, +%d CR loot kept",
                outcome.value,
                credit_loss,
                kept_loot,
            )

        # Add commodity drops to ship cargo
        if result.loot_commodities:
            for cid, qty in result.loot_commodities.items():
                self.player.ship.add_cargo(cid, qty, price_per_unit=0)
            logger.info("Ground commodity loot: %s", result.loot_commodities)

        # Track ground mission statistics
        self.player.ground_enemies_defeated += result.enemies_defeated
        self.player.ground_enemies_talked += result.enemies_talked

        if outcome == MissionOutcome.SUCCESS:
            self.player.ground_missions_completed += 1
            if result.is_ghost_run:
                self.player.ground_undetected_completions += 1
            if result.config.is_campaign:
                self.player.ground_campaign_missions_completed += 1
            # Set the completion flag so the parent mission objective resolves
            if result.config.complete_flag:
                self.player.dialogue_flags[result.config.complete_flag] = True
                if getattr(self, "dialogue_manager", None):
                    self.dialogue_manager.set_flag(result.config.complete_flag)
                logger.info("Ground mission flag set: %s", result.config.complete_flag)
            self._trigger_crew_reaction("ground_mission_success")
        elif outcome.is_failure:
            self.player.ground_missions_failed += 1
            self._trigger_crew_reaction("ground_mission_fail")

    def _build_ground_map(self, config: "GroundMissionConfig") -> "MapGenResult":
        """Build a ground map, using campaign map if available.

        Checks DataLoader for a hand-authored campaign map matching
        the config ID. Falls back to procedural generation.

        Args:
            config: Ground mission configuration.

        Returns:
            MapGenResult ready for play.
        """
        # Check for campaign map
        campaign_data = self.data_loader.campaign_ground_maps.get(config.id)
        if campaign_data:
            from spacegame.models.campaign_map import (
                CampaignMapBuilder,
                CampaignMapData,
            )

            parsed = CampaignMapData.from_dict(campaign_data)
            return CampaignMapBuilder.build(parsed)

        # Procedural fallback
        from spacegame.models.ground_mapgen import GroundMapGenerator, MapGenConfig

        gen_config = MapGenConfig(
            mission_type=config.mission_type,
            difficulty=config.difficulty,
            seed=config.seed or hash(config.id),
            faction_id=config.faction_id,
        )
        return GroundMapGenerator().generate(gen_config)

    def _make_empty_crew_roster(self) -> "CrewRoster":
        """Create an empty crew roster for ground briefing fallback."""
        from spacegame.models.crew import CrewRoster

        return CrewRoster(self.data_loader.crew_templates)

    def _ensure_ship_builder_view(self) -> None:
        """Create or recreate ship builder view."""
        from spacegame.views.ship_builder_view import ShipBuilderView

        # Clean up previous builder view's UI elements to avoid zombie buttons
        old_view = self.state_manager.states.get(GameState.SHIP_BUILDER)
        if old_view and hasattr(old_view, "_destroy_ui"):
            old_view._destroy_ui()

        self.ship_builder_view = ShipBuilderView(
            self.ui_manager,
            self.player,
            self.data_loader,
        )
        self.state_manager.register_state(GameState.SHIP_BUILDER, self.ship_builder_view)

    def _ensure_shipyard_view(self) -> None:
        """Create or recreate shipyard view."""
        from spacegame.views.shipyard_view import ShipyardView

        # Clean up previous view's UI elements to avoid zombie buttons
        old_view = self.state_manager.states.get(GameState.SHIPYARD)
        if old_view and hasattr(old_view, "_destroy_ui"):
            old_view._destroy_ui()

        self.shipyard_view = ShipyardView(
            self.ui_manager,
            self.player,
            self.data_loader.upgrades,
            self.player.upgrade_manager,
            all_ship_types=self.data_loader.ship_types,
        )
        self.state_manager.register_state(GameState.SHIPYARD, self.shipyard_view)

    def _open_pause_menu(self) -> None:
        """Open the pause menu."""
        from spacegame.views.pause_menu_view import PauseMenuView

        self.paused = True
        if not self.pause_menu_view:
            self.pause_menu_view = PauseMenuView(self.ui_manager)
            self.pause_menu_view.on_enter()
        self.audio_manager.pause_music()
        logger.info("Game paused")

    def _close_pause_menu(self) -> None:
        """Close the pause menu and resume game."""
        self.paused = False
        if self.pause_menu_view:
            self.pause_menu_view.on_exit()
        self.audio_manager.resume_music()
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

    def _open_settings_from_menu(self) -> None:
        """Open settings dialog from the main menu."""
        # Hide main menu buttons so they don't show through settings
        if self.main_menu_view:
            self.main_menu_view._set_menu_buttons_visible(False)
        self._open_settings_dialog()

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

                # Persist audio and display config
                settings = self.save_manager.load_settings()
                audio_cfg = self.settings_view.get_audio_config()
                if audio_cfg:
                    settings["audio"] = audio_cfg.to_dict()
                display = self.settings_view.get_display_settings()
                settings["resolution"] = display["resolution"]
                settings["fullscreen"] = display["fullscreen"]
                self.save_manager.save_settings(settings)

            # Close dialog
            self.settings_view.on_exit()
            self.settings_view = None
            # Restore main menu buttons if we came from the main menu
            if self.main_menu_view and self.main_menu_view.active:
                self.main_menu_view._set_menu_buttons_visible(True)

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

        # Sync social state to player before saving
        self.player.social_state = self.social_manager.get_state()

        # Sync attribute state to player before saving
        if hasattr(self, "attribute_sheet"):
            self.player.attribute_state = self.attribute_sheet.to_dict()

        # Sync journal state to player before saving
        if self.journal:
            self.player.journal_state = self.journal.get_state()

        # Sync ground contract state to player before saving
        if self.ground_contract_manager:
            self.player.ground_contract_state = self.ground_contract_manager.to_dict()

        # Sync smuggling contract state to player before saving
        if self.smuggling_contract_manager:
            self.player.smuggling_contract_state = self.smuggling_contract_manager.to_dict()

        # Sync political state to player before saving
        if self.politics_manager:
            self.player.political_state = self.politics_manager.to_dict()

        # Calculate total playtime
        current_playtime = time.time() - self.playtime_start
        total_playtime = self.total_playtime_seconds + int(current_playtime)

        # Serialize galaxy events for save
        galaxy_events_data: dict = {}
        for sid, evts in self.active_galaxy_events.items():
            galaxy_events_data[sid] = [e.to_dict() for e in evts]

        success = self.save_manager.save_game(
            slot=slot,
            player=self.player,
            markets=self.markets,
            active_events=self.active_events,
            playtime_seconds=total_playtime,
            event_log=self.event_log,
            tutorial_state=self.tutorial_manager.to_dict(),
            price_history=self.price_history,
            trade_routes=self.player.trade_route_tracker,
            investment_manager=self.investment_manager,
            ambient_dialogue=self.ambient_dialogue,
            galaxy_events=galaxy_events_data,
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
        # Keep overlay's reference in sync after replacing the manager
        if self._tutorial_overlay:
            self._tutorial_overlay.tutorial_manager = self.tutorial_manager

        # Recreate markets (they need to be reconstructed with current game state)
        self.markets = {}
        market_data = save_data.get("markets", {})
        for _system_id, _data in market_data.items():
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
                self.player.faction_reputation = dict.fromkeys(faction_ids, 0)
        self._apply_faction_assignments()

        # Backward compat: initialize discovered recipes if empty (old saves)
        if not self.player.discovered_recipes:
            self.player.initialize_discovered_recipes(self.data_loader.recipes)

        # Sync dialogue flags and social state from player
        self.dialogue_manager.load_flags(self.player.dialogue_flags)
        self.social_manager.load_state(self.player.social_state)

        # Restore mission manager
        from spacegame.models.mission import MissionManager

        self.mission_manager = MissionManager(self.data_loader.missions)
        if self.player.mission_state:
            self.mission_manager.load_state(self.player.mission_state)
        else:
            self.mission_manager.update_availability(self.player.dialogue_flags)

        # Initialize procedural mission generator
        from spacegame.models.procedural_missions import ProceduralMissionGenerator

        self.procedural_mission_gen = ProceduralMissionGenerator(
            systems=self.data_loader.systems,
            commodities=self.data_loader.commodities,
            enemy_templates=self.data_loader.enemy_templates,
            seed=hash(self.player.name) & 0xFFFFFFFF,
        )
        self._proc_missions_day = -1

        # Restore crew roster
        from spacegame.models.crew import CrewRoster

        self.crew_roster = CrewRoster(self.data_loader.crew_templates)
        if self.player.crew_state:
            self.crew_roster.load_state(self.player.crew_state)
        self.player.ship.set_crew_roster(self.crew_roster)
        self._crew_last_trades = self.player.trades_completed
        self._crew_last_jumps = self.player.jumps_traveled

        # Restore attribute system
        from spacegame.models.attributes import AttributeSheet

        self.attribute_sheet = AttributeSheet.from_dict(self.player.attribute_state)
        self.social_manager.set_progression(self.player.progression)
        self.social_manager.set_attribute_sheet(self.attribute_sheet)

        # Restore journal system
        from spacegame.models.journal import Journal

        self.journal = Journal(auto_templates=self.data_loader.journal_entries)
        if self.player.journal_state:
            self.journal.load_state(self.player.journal_state)

        # Restore ground contract system
        from spacegame.models.ground_contracts import GroundContractManager

        if self.player.ground_contract_state:
            self.ground_contract_manager = GroundContractManager.from_dict(
                self.player.ground_contract_state
            )
        else:
            self.ground_contract_manager = GroundContractManager()

        # Restore smuggling contract system
        from spacegame.models.smuggling import SmugglingContractManager as _SCM

        if self.player.smuggling_contract_state:
            self.smuggling_contract_manager = _SCM.from_dict(self.player.smuggling_contract_state)
        else:
            self.smuggling_contract_manager = _SCM()

        # Restore investment system
        from spacegame.models.investment import InvestmentManager

        investment_state = save_data.get("investment_state", None)
        if investment_state:
            self.investment_manager = InvestmentManager.from_dict(
                investment_state, self.data_loader.investment_templates
            )
        else:
            self.investment_manager = InvestmentManager(
                templates=dict(self.data_loader.investment_templates)
            )

        # Restore political system
        self._initialize_politics_manager(self.player.political_state or None)

        # Restore galaxy event system
        self._initialize_galaxy_event_generator()
        galaxy_events_data = save_data.get("galaxy_events", {})
        if galaxy_events_data:
            from spacegame.models.galaxy_event import GalaxyEvent as _GE

            self.active_galaxy_events = {}
            for sid, evt_list in galaxy_events_data.items():
                self.active_galaxy_events[sid] = [_GE.from_dict(d) for d in evt_list]
        else:
            self.active_galaxy_events = {}

        # Restore station chatter, news ticker, and travel log
        self._initialize_station_chatter()
        self._initialize_news_ticker()
        self._initialize_travel_log()
        self._last_visited_count = len(self.player.systems_visited)

        # Restore price history
        if save_data.get("price_history"):
            self.price_history = save_data["price_history"]
        else:
            from spacegame.models.market import PriceHistory

            self.price_history = PriceHistory()

        # Restore trade route tracker
        if save_data.get("trade_routes"):
            self.player.trade_route_tracker = save_data["trade_routes"]

        # Restore ambient dialogue state
        if self.ambient_dialogue and save_data.get("ambient_dialogue"):
            self.ambient_dialogue.load_state(save_data["ambient_dialogue"])

        # Wire crew_roster to dialogue manager
        if self.crew_roster:
            self.dialogue_manager.set_crew_roster(self.crew_roster)

        # Initialize cockpit HUD
        self._init_cockpit_hud()

        # Track day for event generation
        self._last_known_day = self.player.game_day

        # Recreate event generator if needed
        if not self.event_generator:
            commodity_ids = [c.id for c in self.data_loader.get_all_commodities()]
            system_ids = [s.id for s in self.data_loader.get_all_systems()]
            self.event_generator = EventGenerator(commodity_ids, system_ids)

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
        """Check if a tutorial step or mini-game hint should trigger."""
        # Don't show anything if overlay is already active
        if self._tutorial_overlay and self._tutorial_overlay.active:
            return

        # Brief cooldown after dismissing an overlay to avoid jarring back-to-back dialogs
        if self._tutorial_cooldown > 0:
            self._tutorial_cooldown -= 1
            return

        from spacegame.views.tutorial_overlay import TutorialOverlay

        if not self._tutorial_overlay:
            self._tutorial_overlay = TutorialOverlay(self.tutorial_manager)
        # Ensure overlay always references the current manager (may change on load)
        elif self._tutorial_overlay.tutorial_manager is not self.tutorial_manager:
            self._tutorial_overlay.tutorial_manager = self.tutorial_manager

        # --- Mini-game contextual hints (shown once per game, independent of tutorial) ---
        current_state = self.state_manager.current_state
        hint_map = {
            GameState.MINING: "mining",
            GameState.SALVAGING: "salvage",
            GameState.REFINING: "refining",
            GameState.SHIP_BUILDER: "builder_welcome",
        }

        # Builder-specific sequential hints (QA Fix #7)
        if current_state == GameState.SHIP_BUILDER:
            builder_view = self.state_manager.states.get(GameState.SHIP_BUILDER)
            if builder_view and hasattr(builder_view, "_pending_hint"):
                pending = builder_view._pending_hint
                if pending and self.tutorial_manager.should_show_hint(pending):
                    self._tutorial_overlay.show_hint(pending)
                    builder_view._pending_hint = None
                    return
        hint_id = hint_map.get(current_state)
        if hint_id and self.tutorial_manager.should_show_hint(hint_id):
            self._tutorial_overlay.show_hint(hint_id)
            return

        # Process boss trophy drops after combat (Phase D2)
        if current_state != GameState.COMBAT and hasattr(self, "_combat_trophies_checked"):
            if not self._combat_trophies_checked:
                self._check_combat_trophy_drops()
                self._combat_trophies_checked = True
        elif current_state == GameState.COMBAT:
            self._combat_trophies_checked = False

        # Combat-specific contextual hints (Phase 11)
        if current_state == GameState.COMBAT:
            combat_hint = self._get_combat_tutorial_hint()
            if combat_hint and self.tutorial_manager.should_show_hint(combat_hint):
                self._tutorial_overlay.show_hint(combat_hint)
                return

        # --- 5-step tutorial (only when tutorial is active) ---
        if not self.tutorial_manager.active or self.tutorial_manager.completed:
            return
        if self.tutorial_manager.is_showing():
            return

        # Determine current trigger context
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
            self._tutorial_overlay.show()

    def _get_combat_tutorial_hint(self) -> Optional[str]:
        """Determine which combat tutorial hint to show, if any.

        Checks combat state for first-time triggers: boss encounter,
        momentum threshold, elemental status, defensive identity.

        Returns:
            Hint ID string or None.
        """
        combat_view = self.state_manager.states.get(GameState.COMBAT)
        if combat_view is None or not hasattr(combat_view, "engine"):
            return None

        try:
            state = combat_view.engine.get_state()
        except Exception:
            return None

        # Boss encounter (first time)
        if any(e.template.is_boss for e in state.enemies if e.is_alive):
            return "combat_boss"

        player = state.player

        # Defensive identity (first time a player has one)
        if player.defensive_identity:
            return "combat_defensive_identity"

        # Momentum gauge (first time momentum > 0)
        if player.momentum and player.momentum.current > 0:
            if player.momentum.ultimate_available:
                return "combat_ultimate"
            if player.momentum.current >= 0.25:
                return "combat_crew_combo"
            return "combat_momentum"

        # Elemental effects (first time an enemy has burn/chill/suppressed)
        for enemy in state.enemies:
            for eff, _ in enemy.active_effects:
                if eff.type.value in ("burn", "chill", "suppressed"):
                    return "combat_elemental"

        return None

    # ------------------------------------------------------------------
    # Builder discovery hooks (Phase D2 wiring)
    # ------------------------------------------------------------------

    def _check_salvage_discovery(self) -> None:
        """Check for shape discovery after completing a salvage run."""
        if not self.player:
            return
        from spacegame.models.builder_discovery import check_salvage_discovery

        deck_type = "cargo"  # Default; salvage views track deck type
        if hasattr(self, "salvage_view") and self.salvage_view:
            deck_type = getattr(self.salvage_view, "_deck_type", "cargo")
        skill_level = (
            int(self.player.progression.get_bonus("salvage_expert") * 10)
            if hasattr(self.player, "progression")
            else 0
        )
        result = check_salvage_discovery(
            deck_type,
            skill_level,
            self.player.unlocked_shapes,
        )
        if result:
            self.player.unlocked_shapes.add(result)
            self._show_builder_discovery("shape", result)

    def _check_mining_discovery(self) -> None:
        """Check for shape/material discovery after mining."""
        if not self.player:
            return
        from spacegame.models.builder_discovery import check_mining_discovery

        system_id = self.player.current_system_id
        depth = 3  # Default; mining views track depth
        if hasattr(self, "mining_view") and self.mining_view:
            depth = getattr(self.mining_view, "_current_depth", 3)
        skill_level = (
            int(self.player.progression.get_bonus("deep_mining") * 10)
            if hasattr(self.player, "progression")
            else 0
        )
        result = check_mining_discovery(
            system_id,
            depth,
            skill_level,
            self.player.unlocked_shapes,
            self.player.unlocked_materials,
        )
        if result:
            if result["type"] == "shape":
                self.player.unlocked_shapes.add(result["id"])
            else:
                self.player.unlocked_materials.add(result["id"])
            self._show_builder_discovery(result["type"], result["id"])

    def _check_combat_trophy_drops(self) -> None:
        """Process boss trophy drops after combat victory."""
        if not self.player or not hasattr(self, "combat_view"):
            return
        combat_view = self.state_manager.states.get(GameState.COMBAT)
        if not combat_view or not hasattr(combat_view, "engine"):
            return
        state = combat_view.engine.get_state()
        trophies = getattr(state, "_pending_trophy_drops", [])
        for trophy in trophies:
            shape_id = trophy["shape_id"]
            if shape_id not in self.player.unlocked_shapes:
                self.player.unlocked_shapes.add(shape_id)
                self._show_builder_discovery("shape", shape_id, boss_name=trophy.get("boss_name"))
        if hasattr(state, "_pending_trophy_drops"):
            state._pending_trophy_drops.clear()

        # Legendary module trophy drops
        module_trophies = getattr(state, "_pending_module_trophy_drops", [])
        for trophy in module_trophies:
            module_id = trophy["module_id"]
            if module_id not in self.player.unlocked_modules:
                self.player.unlocked_modules.add(module_id)
                self._show_builder_discovery("module", module_id, boss_name=trophy.get("boss_name"))
                logger.info(
                    f"Legendary module unlocked: {module_id} from {trophy.get('boss_name')}"
                )
        if hasattr(state, "_pending_module_trophy_drops"):
            state._pending_module_trophy_drops.clear()

    def _show_builder_discovery(
        self, discovery_type: str, item_id: str, boss_name: str = ""
    ) -> None:
        """Show a discovery notification for a builder unlock."""
        label = item_id.replace("_", " ").title()
        if boss_name:
            msg = f"Trophy: {label} (from {boss_name})"
        elif discovery_type == "shape":
            msg = f"Shape Discovered: {label}"
        else:
            msg = f"Material Discovered: {label}"
        # Use the existing mission notification system for display
        if hasattr(self, "_mission_notifications"):
            self._mission_notifications.append(msg)
        logger.info(f"Builder discovery: {discovery_type} '{item_id}'")

    def _check_day_advance(self) -> None:
        """Check if game day advanced and trigger market event generation.

        Compares current game day against _last_known_day. When a day
        advance is detected, tries to generate a market event and cleans
        up expired events from active_events.
        """
        if not self.player:
            return
        current_day = self.player.game_day
        if current_day == self._last_known_day:
            return

        self._last_known_day = current_day

        # Record current prices for price history (all systems)
        if self.price_history:
            for system in self.data_loader.get_all_systems():
                market = Market(system, self.data_loader.get_all_commodities(), current_day)
                for commodity in self.data_loader.get_all_commodities():
                    price = market.get_price(commodity.id)
                    if price > 0:
                        self.price_history.record(system.id, commodity.id, current_day, price)

        # Try to generate a new market event
        self.try_generate_market_event()

        # Clean up expired events
        expired = [sid for sid, ev in self.active_events.items() if not ev.is_active(current_day)]
        for sid in expired:
            del self.active_events[sid]

        # Clean up expired ground contracts
        if self.ground_contract_manager:
            self.ground_contract_manager.advance_day(current_day)

        # Decay criminal heat (1 point per day)
        self.player.decay_criminal_heat(1)

        # Check expired smuggling contracts
        if self.smuggling_contract_manager:
            expired = self.smuggling_contract_manager.get_expired_contracts(current_day)
            for contract in expired:
                self.player.deduct_credits(contract.penalty_on_failure)
                self._mission_notifications.append(
                    f"Smuggling contract expired: {contract.client_name} — "
                    f"Penalty: {contract.penalty_on_failure} CR"
                )

        # Advance political events — relationship drift and event generation
        if self.politics_manager:
            new_event = self.politics_manager.try_generate_event(current_day)
            if new_event:
                self._mission_notifications.append(f"Political: {new_event.description}")
            self.politics_manager.advance_day(current_day)

        # Galaxy events — generate new, clean up expired
        if self.galaxy_event_generator:
            new_galaxy_event = self.galaxy_event_generator.try_generate_event(
                current_day, self.active_galaxy_events
            )
            if new_galaxy_event:
                sid = new_galaxy_event.system_id
                if sid not in self.active_galaxy_events:
                    self.active_galaxy_events[sid] = []
                self.active_galaxy_events[sid].append(new_galaxy_event)
                self._mission_notifications.append(f"Galaxy Event: {new_galaxy_event.description}")
                logger.info(
                    f"Galaxy event: {new_galaxy_event.id} at {sid} "
                    f"(type={new_galaxy_event.event_type.value})"
                )

            # Clean up expired galaxy events and trigger chains
            for sid in list(self.active_galaxy_events.keys()):
                still_active = []
                for e in self.active_galaxy_events[sid]:
                    if e.is_active(current_day):
                        still_active.append(e)
                    else:
                        # Check for chain follow-up
                        self.galaxy_event_generator.check_chain_triggers(e, current_day)
                self.active_galaxy_events[sid] = still_active
                if not self.active_galaxy_events[sid]:
                    del self.active_galaxy_events[sid]

        # Generate news ticker headlines from current state
        if self.news_ticker:
            galaxy_evt_ctx = []
            for evts in self.active_galaxy_events.values():
                for e in evts:
                    galaxy_evt_ctx.append(
                        {
                            "event_type": e.event_type.value,
                            "description": e.description,
                            "system_id": e.system_id,
                            "faction_id": e.faction_id,
                        }
                    )
            market_evt_ctx = []
            for evt in self.active_events.values():
                if evt.is_active(current_day):
                    market_evt_ctx.append(
                        {
                            "event_type": evt.event_type.value,
                            "commodity": evt.commodity_id,
                            "system_id": evt.system_id,
                            "description": evt.description,
                        }
                    )
            # Include any queued player action news
            player_actions = list(self._pending_player_news)
            self._pending_player_news = []

            # Auto-generate player news for notable stats
            if self.player and self.player.trades_completed > 0:
                # Chance to mention the player when they've been active
                import random as _rng

                if _rng.random() < 0.15:  # 15% chance per day
                    player_actions.append(
                        self.player.make_news_context(
                            commodity=self.player.current_system_id,
                        )
                    )

            context = {
                "galaxy_events": galaxy_evt_ctx,
                "market_events": market_evt_ctx,
                "player_actions": player_actions,
            }
            self.news_ticker.generate_headlines(context)

        # Advance investments — accumulate returns, apply disaster/pirate effects
        if self.investment_manager:
            systems = self.data_loader.get_all_systems()
            danger_levels = {s.id: s.danger_level for s in systems}
            notifications = self.investment_manager.advance_day(
                current_day, self.active_events, danger_levels
            )
            for msg in notifications:
                self._mission_notifications.append(msg)

        # Crew departure checks
        if self.crew_roster:
            for warning in self.crew_roster.check_departure_warnings():
                self._mission_notifications.append(f"Warning: {warning}")
            for departure in self.crew_roster.process_departures():
                self._mission_notifications.append(departure)

        # Ambient idle dialogue (every 3 days)
        # (Crew reactions to player actions are triggered via _trigger_crew_reaction)
        self._ambient_idle_day_counter += 1
        if self._ambient_idle_day_counter >= 3 and self.ambient_dialogue and self.crew_roster:
            self._ambient_idle_day_counter = 0
            recruited = [t.id for t, _ in self.crew_roster.get_recruited_members()]
            loyalty_map = {}
            for tid in recruited:
                state = self.crew_roster.get_member_state(tid)
                loyalty_map[tid] = state["loyalty"] if state else 0
            result = self.ambient_dialogue.get_random_idle(recruited, loyalty_map)
            if result:
                crew_id, text = result
                template = self.crew_roster.get_template(crew_id)
                name = template.name if template else crew_id
                self._mission_notifications.append(f'{name}: "{text}"')

    # Achievement IDs that trigger full-screen celebration
    CELEBRATION_ACHIEVEMENTS: set[str] = {
        "first_trade",
        "first_100_credits",
        "first_1000_credits",
        "first_ship_upgrade",
        "first_s_rank",
        "first_crew_member",
        "mine_depth_10",
        "mine_depth_20",
        "trades_100",
        "level_5",
        "level_10",
        "level_20",
        "explore_all_systems",
        "first_combat_win",
    }

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
            # Trigger celebration for notable achievements
            if achievement.id in self.CELEBRATION_ACHIEVEMENTS:
                self._celebration_text = achievement.name
                self._celebration_subtitle = f"{achievement.description} {reward_msg}"
                self._celebration_timer = 3.0

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
            loyalty_flags = self.crew_roster.adjust_loyalty_all((1 + loyalty_bonus) * new_trades)
            for flag in loyalty_flags:
                self.dialogue_manager.set_flag(flag)
            for msg in levelup_msgs:
                self._mission_notifications.append(msg)
            # Crew reaction to trading (alternate sold/bought based on parity)
            action = "sold_cargo" if current_trades % 2 == 0 else "bought_cargo"
            self._trigger_crew_reaction(action)

        # Check for new jumps
        current_jumps = self.player.jumps_traveled
        if current_jumps > self._crew_last_jumps:
            new_jumps = current_jumps - self._crew_last_jumps
            self._crew_last_jumps = current_jumps
            levelup_msgs = self.crew_roster.add_xp_to_all((3 + xp_bonus) * new_jumps)
            for msg in levelup_msgs:
                self._mission_notifications.append(msg)

    def _refresh_procedural_missions(self) -> None:
        """Generate procedural station board missions for the current system.

        Generates new contracts each game day, removing old unclaimed ones.
        """
        if not self.player or not hasattr(self, "procedural_mission_gen"):
            return

        current_day = self.player.game_day
        system_id = self.player.current_system_id
        if current_day == self._proc_missions_day:
            return  # Already generated for today

        self._proc_missions_day = current_day

        # Remove old procedural missions that were never accepted
        old_proc = [
            mid for mid in list(self.mission_manager._missions.keys()) if mid.startswith("proc_")
        ]
        for mid in old_proc:
            self.mission_manager.remove_mission(mid)

        # Generate fresh contracts for this system
        missions = self.procedural_mission_gen.generate_for_system(system_id, current_day)
        for mission in missions:
            self.mission_manager.add_mission(mission)

    def check_missions(self) -> None:
        """Check mission objectives and handle completions."""
        if not self.player or not self.mission_manager:
            return

        recruited_crew_ids = self.crew_roster.recruited_ids if self.crew_roster else None
        completed_ids = self.mission_manager.check_objectives(
            self.player, recruited_crew_ids=recruited_crew_ids
        )
        for mission_id in completed_ids:
            reward_msgs = self.mission_manager.apply_rewards(mission_id, self.player)
            mission = self.mission_manager.get_mission(mission_id)
            name = mission.name if mission else mission_id
            reward_text = ", ".join(reward_msgs) if reward_msgs else ""
            self._mission_notifications.append(f"Mission Complete: {name}! {reward_text}")
            logger.info(f"Mission completed: {name}")

            # Track mission completion stats
            if mission and mission.mission_type == "side":
                self.player.side_missions_completed += 1
            if mission and mission.crew_member_id:
                self.player.crew_quests_completed += 1

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
                        else:
                            # Crew full — mark companion as pending for cantina recruitment
                            template = self.crew_roster.get_template(reward.target_id)
                            if template and template.is_companion:
                                self.crew_roster.add_pending_companion(reward.target_id)
                                system = self.data_loader.get_system(template.home_system_id)
                                system_name = system.name if system else template.home_system_id
                                self._mission_notifications.append(
                                    f"Crew Full: {template.name} is waiting at "
                                    f"{system_name}. Dismiss a crew member and "
                                    f"visit the cantina to recruit them."
                                )
                                logger.info(
                                    f"Crew full — {template.name} marked as pending "
                                    f"at {template.home_system_id}"
                                )

                    # Trade permit
                    if reward.reward_type == "trade_permit" and reward.target_id:
                        dl = get_data_loader()
                        if reward.target_id == "all":
                            # Universal permit — grant for all factions
                            for fid in dl.factions:
                                self.player.grant_trade_permit(fid)
                            self._mission_notifications.append(
                                "Trade Permit Acquired: Universal Bill of Landing"
                            )
                        else:
                            faction_id = reward.target_id
                            self.player.grant_trade_permit(faction_id)
                            faction = dl.get_faction(faction_id)
                            fname = faction.name if faction else faction_id
                            self._mission_notifications.append(f"Trade Permit Acquired: {fname}")

                    # Reputation reward (routed through centralized spillover)
                    if (
                        reward.reward_type in ("reputation", "modify_reputation")
                        and reward.target_id
                    ):
                        if self.politics_manager:
                            changes = self.politics_manager.apply_reputation_with_spillover(
                                self.player, reward.target_id, reward.amount
                            )
                            dl = get_data_loader()
                            for fid, amt in changes:
                                faction = dl.get_faction(fid)
                                fname = faction.name if faction else fid
                                sign = "+" if amt >= 0 else ""
                                self._mission_notifications.append(f"{sign}{amt} Rep: {fname}")
                        else:
                            self.player.modify_reputation(reward.target_id, reward.amount)
                            dl = get_data_loader()
                            faction = dl.get_faction(reward.target_id)
                            fname = faction.name if faction else reward.target_id
                            sign = "+" if reward.amount >= 0 else ""
                            self._mission_notifications.append(
                                f"{sign}{reward.amount} Rep: {fname}"
                            )

            # Grant crew XP and loyalty on mission completion
            if self.crew_roster:
                levelup_msgs = self.crew_roster.add_xp_to_all(20)
                loyalty_flags = self.crew_roster.adjust_loyalty_all(5)
                for flag in loyalty_flags:
                    self.dialogue_manager.set_flag(flag)
                for msg in levelup_msgs:
                    self._mission_notifications.append(msg)

        # Crew reaction to mission completion
        if completed_ids:
            self._trigger_crew_reaction("mission_completed")

        # Check for journal auto-entries triggered by mission rewards
        if completed_ids:
            self._check_journal_triggers()

        # Expire side missions whose window has closed
        if completed_ids:
            expired = self.mission_manager.expire_missions()
            for mid in expired:
                exp_mission = self.mission_manager.get_mission(mid)
                if exp_mission:
                    logger.info(f"Side mission expired: {exp_mission.name}")
            if expired:
                self._trigger_crew_reaction("mission_expired")

        # Update availability (missions may unlock from completed prereqs or new flags)
        newly_available = self.mission_manager.update_availability(self.player.dialogue_flags)
        if newly_available:
            discoverable_count = 0
            for mid in newly_available:
                mission = self.mission_manager.get_mission(mid)
                if mission:
                    # Auto-accepted missions grant on_accept_cargo immediately
                    if mission.auto_accept and mission.on_accept_cargo:
                        for cargo in mission.on_accept_cargo:
                            self.player.ship.add_cargo(cargo.commodity_id, cargo.quantity, 0)
                            self._mission_notifications.append(
                                f"Cargo Loaded: {cargo.quantity} {cargo.commodity_id}"
                            )
                    if mission.auto_accept:
                        self._mission_notifications.append(f"Mission Accepted: {mission.name}")
                    else:
                        discoverable_count += 1
                        # Add narrative journal entry for mission discovery
                        if self.journal:
                            discovery = (
                                mission.discovery_text or f"Heard word of new work: {mission.name}."
                            )
                            self.journal.add_auto_entry(
                                entry_id=f"mission_discover_{mid}",
                                text=discovery,
                                game_day=self.player.game_day,
                                system_id=self.player.current_system_id,
                                tag="goals",
                                mission_id=mid,
                            )
            # Single consolidated notification instead of one per mission
            if discoverable_count == 1:
                self._mission_notifications.append("New Mission Available — check your journal")
            elif discoverable_count > 1:
                self._mission_notifications.append("New Missions Available — check your journal")
            # Update galaxy map markers and forced encounters
            if self.galaxy_map_view:
                self.galaxy_map_view.mission_target_systems = (
                    self.mission_manager.get_active_target_systems()
                )
                self.galaxy_map_view.forced_encounters = (
                    self.mission_manager.get_active_forced_encounters()
                )

    def _check_journal_triggers(self) -> None:
        """Scan dialogue flags for new journal auto-entries to trigger."""
        if not self.journal or not self.player:
            return
        for flag, value in self.player.dialogue_flags.items():
            if value:
                entry = self.journal.trigger_auto_entry(
                    flag, self.player.game_day, self.player.current_system_id
                )
                if entry:
                    self._mission_notifications.append("Journal updated")

    def _check_auto_triggers(self) -> None:
        """Check all NPCs for auto-trigger dialogues at current system."""
        if not self.player:
            return
        for npc in self.data_loader.npcs.values():
            if not npc.auto_trigger_gate_flag:
                continue
            if self.player.dialogue_flags.get(npc.auto_trigger_gate_flag, False):
                continue
            if self.player.current_system_id != npc.home_system_id:
                continue
            if not all(
                self.player.dialogue_flags.get(f, False) for f in npc.auto_trigger_prerequisites
            ):
                continue
            # Pre-set gate flag to prevent re-fire
            self.player.dialogue_flags[npc.auto_trigger_gate_flag] = True
            self.dialogue_manager.set_flag(npc.auto_trigger_gate_flag)
            self.start_dialogue(npc.id, return_state=GameState.GALAXY_MAP)
            return  # One trigger per frame

    def check_attribute_milestones(self) -> None:
        """Check and award attribute milestones and level-up points."""
        if not self.player or not hasattr(self, "attribute_sheet"):
            return

        # Level-up attribute points: award at odd levels 3-25
        level = self.player.progression.level
        level_milestones = {
            lvl: f"level_{lvl}" for lvl in range(3, 26, 2)
        }  # {3: "level_3", 5: "level_5", ..., 25: "level_25"}
        for lvl, milestone_id in level_milestones.items():
            if level >= lvl and not self.attribute_sheet.has_milestone(milestone_id):
                self.attribute_sheet._awarded_milestones.add(milestone_id)
                self.attribute_sheet.add_points(1)
                self._mission_notifications.append(f"Level {lvl} reached — +1 attribute point!")

        # Gameplay milestones
        if self.player.trades_completed >= 1:
            success, msg = self.attribute_sheet.award_milestone("first_trade")
            if success:
                self._mission_notifications.append(msg)

        if len(self.player.systems_visited) >= 5:
            success, msg = self.attribute_sheet.award_milestone("explorer_5")
            if success:
                self._mission_notifications.append(msg)

        if self.player.ore_mined >= 50:
            success, msg = self.attribute_sheet.award_milestone("miner_50")
            if success:
                self._mission_notifications.append(msg)

        if self.mission_manager:
            completed = self.mission_manager.get_completed_ids()
            if completed:
                success, msg = self.attribute_sheet.award_milestone("first_mission")
                if success:
                    self._mission_notifications.append(msg)

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
            self._banner_font = get_font("machine", 24)

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
                self.audio_manager.play_sfx("achievement")

        if self._achievement_notify_timer <= 0:
            return

        if self._banner_font is None:
            self._banner_font = get_font("machine", 24)

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

    def _render_celebration(self, screen: pygame.Surface) -> None:
        """Render full-screen milestone celebration overlay."""
        if self._celebration_timer <= 0:
            return

        # Fade: full for first 2s, fade out in last 1s
        if self._celebration_timer > 1.0:
            alpha = 255
        else:
            alpha = int(255 * self._celebration_timer)

        # Dimmed background
        dim = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, min(alpha, 100)))
        screen.blit(dim, (0, 0))

        # Title
        title_font = get_font("header", 44)
        title = title_font.render("MILESTONE ACHIEVED", True, Colors.GOLD)
        title.set_alpha(alpha)
        screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))

        # Achievement name
        name_font = get_font("dialogue", 32)
        name = name_font.render(self._celebration_text, True, Colors.TEXT)
        name.set_alpha(alpha)
        screen.blit(name, name.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))

        # Subtitle (description + reward)
        if self._celebration_subtitle:
            sub_font = get_font("dialogue", 20)
            sub = sub_font.render(self._celebration_subtitle, True, Colors.TEXT_SECONDARY)
            sub.set_alpha(alpha)
            screen.blit(sub, sub.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 30)))

        # Decorative lines
        line_w = 300
        line_x = WINDOW_WIDTH // 2 - line_w // 2
        line_surf = pygame.Surface((line_w, 2), pygame.SRCALPHA)
        line_surf.fill((Colors.GOLD[0], Colors.GOLD[1], Colors.GOLD[2], alpha))
        screen.blit(line_surf, (line_x, WINDOW_HEIGHT // 2 - 18))

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
            self._banner_font = get_font("machine", 24)

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
                # Tutorial overlay uses raw mouse events (not pygame_gui) so
                # it can render on top of everything.  Intercept events here
                # before they reach the UI manager to prevent click-through.
                if self._tutorial_overlay and self._tutorial_overlay.active:
                    consumed = self._tutorial_overlay.handle_event(event)
                    if consumed:
                        # If the overlay just closed, add cooldown to prevent
                        # immediate back-to-back dialogs (e.g. hint then tutorial)
                        if not self._tutorial_overlay.active:
                            self._tutorial_cooldown = 30  # ~0.5s at 60fps
                        continue
                    # Still let non-consumed events (e.g. KEYDOWN) through
                    self.ui_manager.process_events(event)
                    continue

                # Cockpit HUD event handling (before pygame_gui)
                if self._cockpit_hud and self._cockpit_hud.visible:
                    hud_result = self._cockpit_hud.handle_event(event)
                    if hud_result is not None:
                        # Navigate to requested state
                        self._ensure_view_for_state(hud_result)
                        self.state_manager.change_state(hud_result)
                        continue
                    # Consume mouse clicks on the HUD bar to prevent click-through
                    if event.type == pygame.MOUSEBUTTONDOWN and event.pos[1] >= self._cockpit_hud.y:
                        continue

                # F11 — toggle fullscreen
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    continue

                # Check for ESC key to toggle pause (only during gameplay)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.player and not self.paused:
                        self._open_pause_menu()
                    elif self.paused:
                        self._close_pause_menu()

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

            # Update cockpit HUD visibility based on current state
            if self._cockpit_hud and self.player:
                # Pass current system's faction to HUD for station skin accent
                faction_id = ""
                if self.player.current_system_id:
                    sys_data = self.data_loader.get_system(self.player.current_system_id)
                    if sys_data:
                        faction_id = sys_data.faction
                self._cockpit_hud.update(
                    dt, self.state_manager.current_state, faction_id=faction_id
                )

            # Handle state transitions
            self._handle_state_transitions()
            self._check_tutorial_triggers()
            self._update_audio_for_state()

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
                self._check_day_advance()
                # Defer mission/achievement checks while dialogue is active
                # to avoid notification banners overlapping the conversation
                if (
                    not (self.dialogue_view and self.dialogue_view.active)
                    and not self.transition_manager.active
                ):
                    self.check_achievements()
                    self.check_missions()
                self.check_crew_xp()
                self.check_attribute_milestones()

            # Update achievement notification timer
            if self._achievement_notify_timer > 0:
                self._achievement_notify_timer = max(0.0, self._achievement_notify_timer - dt)

            # Update mission notification timer
            if self._mission_notify_timer > 0:
                self._mission_notify_timer = max(0.0, self._mission_notify_timer - dt)

            # Update celebration timer
            if self._celebration_timer > 0:
                self._celebration_timer = max(0.0, self._celebration_timer - dt)

            # Update visual effects
            self.transition_manager.update(dt)
            self.screen_shake.update(dt)

            # Update audio
            self.audio_manager.update(dt)

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

            # Milestone celebration overlay
            if self._celebration_timer > 0:
                self._render_celebration(render_surface)

            # Mission notification banner
            self._render_mission_notification(render_surface)

            self.ui_manager.draw_ui(render_surface)

            # Cockpit HUD renders AFTER pygame_gui so it sits on top of view UI
            if self._cockpit_hud and self.player:
                self._cockpit_hud.render(render_surface)

            # Tutorial overlay renders AFTER HUD and ui_manager.draw_ui() so it
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
        self.audio_manager.shutdown()
        pygame.quit()
        sys.exit()


def main() -> None:
    """Entry point for the game."""
    game = Game()
    game.initialize_states()
    game.run()


if __name__ == "__main__":
    main()
