"""
Game configuration constants.

This module contains all configurable constants for the game, including
display settings, colors, timing, and game rules.
"""

from enum import Enum
import pathlib

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

WINDOW_TITLE = "Space Trader"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS_TARGET = 60

# Fullscreen mode
FULLSCREEN = False  # Toggle for fullscreen mode
VSYNC = True  # Vertical sync

# ============================================================================
# COLORS (RGB)
# ============================================================================


class Colors:
    """Standard color palette for the game."""

    # Base colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)

    # UI colors (dark theme)
    BACKGROUND = (10, 10, 20)  # Dark blue-black
    UI_PANEL = (20, 25, 40)  # Slightly lighter panel
    UI_BORDER = (60, 70, 100)  # Border color

    # Text colors
    TEXT_PRIMARY = (220, 220, 230)  # Off-white
    TEXT_SECONDARY = (150, 160, 180)  # Muted gray
    TEXT_HIGHLIGHT = (100, 200, 255)  # Bright blue
    TEXT = TEXT_PRIMARY  # Alias for convenience

    # Status colors
    GREEN = (50, 200, 100)  # Positive/gain
    RED = (220, 50, 50)  # Negative/loss
    YELLOW = (255, 200, 50)  # Warning/neutral
    BLUE = (80, 150, 255)  # Info

    # Panel
    PANEL = (20, 25, 40)  # Same as UI_PANEL

    # Convenience aliases
    SUCCESS = GREEN
    ERROR = RED

    # Particle / effect colors
    PARTICLE_SPARK = (255, 200, 80)
    PARTICLE_CYAN = (100, 200, 255)
    GLOW_BLUE = (40, 100, 255)
    GLOW_GREEN = (40, 200, 100)
    GLOW_ORANGE = (255, 150, 40)

    # Faction colors
    FACTION_COMMERCE = (100, 150, 255)  # Blue - Commerce Guild
    FACTION_MINERS = (200, 150, 50)  # Orange/gold - Miners Union
    FACTION_SCIENCE = (150, 100, 200)  # Purple - Science Collective
    FACTION_FRONTIER = (100, 200, 100)  # Green - Frontier Alliance


# ============================================================================
# GAME STATES
# ============================================================================


class GameState(Enum):
    """Enumeration of all possible game states."""

    # Meta states
    STARTUP = "startup"
    MAIN_MENU = "main_menu"
    LOADING = "loading"
    PAUSED = "paused"
    OPTIONS = "options"

    # Gameplay states
    GALAXY_MAP = "galaxy_map"
    TRADING = "trading"
    MINING = "mining"
    SALVAGING = "salvaging"
    REFINING = "refining"
    SKILL_TREE = "skill_tree"
    SHIPYARD = "shipyard"
    SHIP_MANAGEMENT = "ship_management"

    # Info screens
    STATISTICS = "statistics"
    ACHIEVEMENTS = "achievements"

    # Story states
    DIALOGUE = "dialogue"
    MISSION_LOG = "mission_log"
    MISSION_BRIEFING = "mission_briefing"
    CREW_ROSTER = "crew_roster"
    NAME_INPUT = "name_input"


# ============================================================================
# PATHS
# ============================================================================

# Base paths
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "spacegame" / "data"
ASSETS_DIR = DATA_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"
SAVES_DIR = DATA_DIR / "saves"

# Image subdirectories
SYSTEMS_IMAGE_DIR = IMAGES_DIR / "systems"
BACKGROUNDS_IMAGE_DIR = IMAGES_DIR / "backgrounds"

# Ensure directories exist
SAVES_DIR.mkdir(parents=True, exist_ok=True)
SYSTEMS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
BACKGROUNDS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# GAME RULES (Placeholder - will expand)
# ============================================================================

# Starting conditions
STARTING_CREDITS = 5000
STARTING_FUEL = 100

# Game timing (if using turn-based or timed mechanics)
AUTOSAVE_INTERVAL = 300  # seconds (5 minutes)

# ============================================================================
# MINING CONSTANTS
# ============================================================================

MINING_DEFAULT_ENERGY = 20
MINING_ENERGY_REGEN_SECONDS = 3.0
MINING_GRID_WIDTH = 6
MINING_GRID_HEIGHT = 4

# ============================================================================
# SALVAGING CONSTANTS
# ============================================================================

SALVAGE_GRID_SIZE = 5  # 5x5 grid
SALVAGE_DEFAULT_CHARGES = 10
SALVAGE_CHARGE_REGEN_SECONDS = 5.0

# ============================================================================
# PROGRESSION CONSTANTS
# ============================================================================

XP_PER_TRADE = 15
XP_PER_MINING = 5
XP_PER_SALVAGE = 5
XP_PER_REFINE = 10
XP_PER_TRAVEL = 10
MAX_LEVEL = 10

# ============================================================================
# FACTION REPUTATION CONSTANTS
# ============================================================================

REP_PER_TRADE = 2
REP_RIVAL_PENALTY_RATIO = 0.5  # Rival loses half what you gain
REP_MIN = -100
REP_MAX = 100

# ============================================================================
# DIALOGUE CONSTANTS
# ============================================================================

DIALOGUE_TEXT_SPEED = 40  # Characters per second for typewriter effect (0 = instant)
DIALOGUE_PORTRAIT_SIZE = (100, 120)

# ============================================================================
# IMAGE ASSET NAMES
# ============================================================================

# Background image names (without .png extension)
BACKGROUND_IMAGES = ["starfield", "deep_space", "nebula", "trade_routes", "frontier"]

# System image names match system IDs from systems.json
SYSTEM_IMAGES = [
    "nexus_prime",
    "verdant",
    "forgeworks",
    "breakstone",
    "axiom_labs",
    "havens_rest",
    "crimson_reach",
    "stellaris_port",
    "iron_depths",
    "nova_research",
]
