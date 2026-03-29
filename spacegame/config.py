"""
Game configuration constants.

This module contains all configurable constants for the game, including
display settings, colors, timing, and game rules.
"""

import pathlib
import sys
from enum import Enum

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

WINDOW_TITLE = "Aurelia: A Ledger of Stars"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS_TARGET = 60

# Supported resolutions (width, height) — player selects in settings
SUPPORTED_RESOLUTIONS: list[tuple[int, int]] = [
    (1280, 720),
    (1600, 900),
    (1920, 1080),
]
DEFAULT_RESOLUTION: tuple[int, int] = (1280, 720)

# Fullscreen mode
FULLSCREEN = False  # Toggle for fullscreen mode
VSYNC = True  # Vertical sync


def set_resolution(width: int, height: int) -> None:
    """Update the active resolution globals.

    Must be called BEFORE views are imported so that
    ``from spacegame.config import WINDOW_WIDTH`` picks up the new value.
    """
    global WINDOW_WIDTH, WINDOW_HEIGHT
    WINDOW_WIDTH = width
    WINDOW_HEIGHT = height


# Base resolution used by scale_x / scale_y helpers
_BASE_WIDTH = 1280
_BASE_HEIGHT = 720


def scale_x(base_px: int) -> int:
    """Scale a horizontal pixel value from 1280-base to the current resolution.

    Args:
        base_px: Pixel value designed for 1280px width.

    Returns:
        Proportionally scaled value for the active WINDOW_WIDTH.
    """
    return round(base_px * WINDOW_WIDTH / _BASE_WIDTH)


def scale_y(base_px: int) -> int:
    """Scale a vertical pixel value from 720-base to the current resolution.

    Args:
        base_px: Pixel value designed for 720px height.

    Returns:
        Proportionally scaled value for the active WINDOW_HEIGHT.
    """
    return round(base_px * WINDOW_HEIGHT / _BASE_HEIGHT)


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

    # Panel & card backgrounds
    PANEL = (20, 25, 40)  # Same as UI_PANEL
    PANEL_BG = (15, 20, 35)  # Content panel background (darker)
    CARD_BG = (20, 28, 45)  # Card / inactive tab background

    # Bar rendering
    BAR_BG = (30, 30, 40)  # Progress bar track background
    BAR_BG_LIGHT = (40, 40, 50)  # Lighter bar track variant
    BAR_EDGE = (200, 240, 255)  # Leading edge highlight on filled bars

    # List row backgrounds
    ROW_BG = (30, 40, 65)  # Normal list/table row background
    ROW_HIGHLIGHT = (40, 55, 90)  # Selected/hovered row background
    ROW_DETAIL = (22, 30, 50)  # Detail panel inside list row

    # Accent colors
    GOLD = (255, 215, 0)  # Gold highlight / achievement color

    # Scrollbar
    SCROLLBAR_TRACK = (30, 35, 55)  # Scrollbar track background
    SCROLLBAR_THUMB = (80, 90, 120)  # Scrollbar thumb

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

    # Skill check colors
    CHECK_PASS = (80, 220, 120)  # Green - will pass
    CHECK_MARGINAL = (220, 200, 60)  # Yellow - borderline
    CHECK_FAIL = (200, 80, 80)  # Red - will fail

    # Attribute colors
    ATTR_HIGHLIGHT = (180, 160, 255)  # Soft purple for attribute display

    # Salvage view colors
    SALVAGE_THEME = (100, 200, 255)  # Salvage hold / intel accent
    CELL_HIDDEN_BG = (40, 42, 55)  # Unrevealed cell background
    CELL_HIDDEN_BORDER = (65, 68, 85)  # Unrevealed cell border
    CELL_EMPTY_BG = (25, 25, 30)  # Scanned empty cell
    CORRUPTION_BG = (50, 20, 20)  # Corrupted cell background
    CORRUPTION_BORDER = (90, 35, 35)  # Corrupted cell border
    CORRUPTION_TEXT = (150, 50, 50)  # Corrupted label text
    CELL_TRANSITION_BG = (12, 14, 22)  # Deck transition dark cell
    CELL_TRANSITION_BORDER = (25, 28, 38)  # Deck transition border

    # Quality tier colors
    QUALITY_POOR = (80, 80, 80)
    QUALITY_NORMAL = (140, 140, 140)
    QUALITY_GOOD = (100, 200, 100)
    QUALITY_EXCELLENT = (255, 220, 80)

    # Ground exploration tile colors (placeholder)
    GROUND_FLOOR = (60, 65, 75)
    GROUND_WALL = (35, 35, 45)
    GROUND_DOOR_CLOSED = (100, 80, 50)
    GROUND_DOOR_OPEN = (80, 70, 55)
    GROUND_EXIT = (50, 200, 100)
    GROUND_ENTRANCE = (80, 150, 255)
    GROUND_PLAYER = (255, 220, 80)
    GROUND_ENEMY = (220, 60, 60)
    GROUND_ENEMY_SUSPICIOUS = (220, 160, 40)
    GROUND_ENEMY_ALERT = (255, 40, 40)
    GROUND_NOISY_FLOOR = (70, 65, 60)
    GROUND_TERMINAL = (60, 180, 200)  # Cyan — interactive data terminal
    GROUND_HAZARD = (200, 80, 40)  # Orange-red — environmental hazard
    GROUND_VENT = (120, 130, 140)  # Grey-blue — steam vent (blocks vision)
    GROUND_FOG_EXPLORED_ALPHA = 140  # Semi-transparent overlay for explored tiles


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
    SHIP_BUILDER = "ship_builder"
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
    CHARACTER_CREATION = "character_creation"
    CHARACTER = "character"
    JOURNAL = "journal"

    # Station states
    STATION_HUB = "station_hub"
    REPAIR_BAY = "repair_bay"
    CANTINA = "cantina"
    INVESTMENT = "investment"

    # Combat states
    COMBAT = "combat"
    ENCOUNTER = "encounter"

    # Ground exploration states
    GROUND_BRIEFING = "ground_briefing"
    GROUND_EXPLORATION = "ground_exploration"
    GROUND_RESULT = "ground_result"


# ============================================================================
# PATHS
# ============================================================================


def _resolve_root() -> pathlib.Path:
    """Resolve project root, handling both dev and frozen (PyInstaller) modes."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return pathlib.Path(__file__).parent.parent


# Base paths
PROJECT_ROOT = _resolve_root()
DATA_DIR = PROJECT_ROOT / "spacegame" / "data"
ASSETS_DIR = DATA_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
IMAGES_DIR = ASSETS_DIR / "images"

# Audio directories
AUDIO_DIR = ASSETS_DIR / "audio"
MUSIC_DIR = AUDIO_DIR / "music"
SFX_DIR = AUDIO_DIR / "sfx"
AMBIENT_DIR = AUDIO_DIR / "ambient"

# Image subdirectories
SYSTEMS_IMAGE_DIR = IMAGES_DIR / "systems"
BACKGROUNDS_IMAGE_DIR = IMAGES_DIR / "backgrounds"

# Ensure directories exist (skip in frozen builds — bundled assets are read-only)
if not getattr(sys, "frozen", False):
    SYSTEMS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    BACKGROUNDS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# GAME RULES (Placeholder - will expand)
# ============================================================================

# Starting conditions
STARTING_CREDITS = 4000
STARTING_FUEL = 100

# Game timing (if using turn-based or timed mechanics)
AUTOSAVE_INTERVAL = 300  # seconds (5 minutes)

# ============================================================================
# COMBAT CONSTANTS
# ============================================================================

COMBAT_FLEE_BASE_CHANCE = 30
COMBAT_FLEE_SPEED_FACTOR = 3
COMBAT_FLEE_MIN_CHANCE = 10
COMBAT_FLEE_MAX_CHANCE = 90
COMBAT_FLEE_ACCURACY_PENALTY = 20
COMBAT_HIT_CHANCE_MIN = 5
COMBAT_HIT_CHANCE_MAX = 95
COMBAT_DEFEAT_CARGO_LOSS_PERCENT = 30
COMBAT_DEFEAT_HULL_REMAINING_PERCENT = 25
COMBAT_DEFEAT_CREDIT_LOSS_PERCENT = 10  # Lose 10% of credits (repair/salvage costs)
COMBAT_DEFEAT_REPUTATION_PENALTY = 5  # Lose 5 rep with local faction (needed rescuing)
COMBAT_DEFEAT_FUEL_REMAINING = 5  # Minimum fuel after defeat (enough for 1 jump)

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

XP_PER_TRADE = 5
XP_PER_MINING = 3
XP_PER_SALVAGE = 6
XP_PER_REFINE = 10
XP_PER_TRAVEL = 10
MAX_LEVEL = 999  # Effectively uncapped — formula-based XP scaling
SKILL_POINT_CAP_LEVEL = 40  # Stop granting skill points after this level
ATTRIBUTE_CAP_LEVEL = 25  # Last level that awards attribute points

# ============================================================================
# FACTION REPUTATION CONSTANTS
# ============================================================================

REP_PER_TRADE = 1
REP_MIN = -100
REP_MAX = 100

# === POLITICAL SYSTEM ===
REP_SPILLOVER_RATIO = 0.30  # Rival loses 30% of rep you gain (centralized)
POLITICAL_EVENT_DAILY_CHANCE = 0.08  # 8% per game day
POLITICAL_EVENT_MIN_DURATION = 3
POLITICAL_EVENT_MAX_DURATION = 7
FACTION_RELATIONSHIP_MIN = -100
FACTION_RELATIONSHIP_MAX = 100
INTEL_BASE_VALUE = 50
INTEL_RIVAL_BONUS_MULTIPLIER = 2.0
REP_HOSTILE_ATTACK_CHANCE = 40
REP_FRIENDLY_DISPOSITION_BONUS = 10
REP_UNFRIENDLY_DISPOSITION_PENALTY = -10

# === GALAXY EVENTS ===
GALAXY_EVENT_DAILY_CHANCE = 0.04  # 4% per day (~1 event per 25 days)
GALAXY_EVENT_MAX_ACTIVE = 2
GALAXY_EVENT_MIN_DURATION = 3
GALAXY_EVENT_MAX_DURATION = 8
EMBARGO_INSPECTION_MULTIPLIER = 2.0  # Double inspection chance during embargo
MAJOR_TRADE_PROFIT_THRESHOLD = 500  # CR profit to trigger travel log entry
NEWS_TICKER_BUFFER_SIZE = 8

# ============================================================================
# CREW RE-RECRUITMENT COSTS
# ============================================================================

CREW_RERECRUIT_NEUTRAL = 500  # Re-signing bonus for neutral loyalty
CREW_RERECRUIT_WARY = 1500  # Higher cost for wary crew
CREW_RERECRUIT_DISCONTENTED = 3000  # Harsh penalty for discontented crew
CREW_DEPARTED_SURCHARGE = 50000  # Harsh penalty if crew left due to loyalty 0

# ============================================================================
# DIALOGUE CONSTANTS
# ============================================================================

DIALOGUE_TEXT_SPEED = 40  # Characters per second for typewriter effect (0 = instant)
DIALOGUE_PORTRAIT_SIZE = (scale_x(100), scale_y(120))
SOCIAL_CHECK_FEEDBACK_DURATION = 1.5  # Seconds to show check result overlay

# ============================================================================
# GROUND EXPLORATION CONSTANTS
# ============================================================================

GROUND_TILE_SIZE = 48  # Pixels per tile (model-level, do not scale)
GROUND_VIEWPORT_TILES_X = WINDOW_WIDTH // GROUND_TILE_SIZE  # Visible tiles horizontally
GROUND_VIEWPORT_TILES_Y = WINDOW_HEIGHT // GROUND_TILE_SIZE  # Visible tiles vertically
GROUND_CAMERA_LERP_SPEED = 8.0  # Camera smoothing factor
GROUND_BASE_VISION_RADIUS = 5  # Player base vision in tiles
GROUND_DEFAULT_MAP_WIDTH = 20
GROUND_DEFAULT_MAP_HEIGHT = 25

# Stealth & detection
GROUND_SUSPICIOUS_DECAY_TURNS = 5  # Turns for SUSPICIOUS → UNDETECTED
GROUND_ALERT_DECAY_TURNS = 8  # Turns of broken LOS for ALERT → SUSPICIOUS
GROUND_DEFAULT_ENEMY_VISION = 5  # Default enemy vision range
GROUND_ENEMY_VISION_CONE_ANGLE = 90  # Degrees, centered on facing direction
GROUND_NOISE_DOOR_OPEN = 2  # Noise radius for opening a door
GROUND_NOISE_NOISY_FLOOR = 3  # Noise radius for stepping on noisy tile
GROUND_NOISE_SPRINT = 4  # Noise radius for sprinting

# Ground combat — "Dice & Grit"
GROUND_COMBAT_BASE_HP = 10  # Player base HP on ground
GROUND_COMBAT_ENGAGE_RANGE = 2  # Tiles from player to pull enemies into combat
GROUND_COMBAT_RETREAT_BASE_DIFFICULTY = 4  # Base retreat roll target
GROUND_COMBAT_AMBUSH_BONUS = 3  # Attack bonus on ambush first exchange
GROUND_COMBAT_DISADVANTAGED_PENALTY = 2  # Penalty when caught in the open
GROUND_COMBAT_OUTNUMBERED_PENALTY = 1  # Per enemy beyond the first
GROUND_COMBAT_MOMENTUM_THRESHOLD = 2  # Consecutive wins needed for bonus
GROUND_COMBAT_MOMENTUM_BONUS = 2  # Attack bonus from momentum
GROUND_COMBAT_LAST_STAND_BONUS = 3  # Bonus when below 25% HP
GROUND_COMBAT_INTIMIDATION_KILL_BONUS = 2  # Talk bonus after defeating an enemy
GROUND_COMBAT_CRIT_MULTIPLIER = 2  # Damage multiplier on natural 6
GROUND_COMBAT_INTIMIDATING_PRESENCE_DEBUFF = 2  # Enemy debuff on first exchange
GROUND_COMBAT_PANEL_HEIGHT = 220  # Pixel height of combat overlay panel
GROUND_COMBAT_DICE_ANIM_DURATION = 0.6  # Seconds for dice roll animation
GROUND_COMBAT_RESULT_DISPLAY_DURATION = 1.5  # Seconds to show exchange result

# ============================================================================
# CRIMINAL HEAT DISPLAY
# ============================================================================


def get_heat_display_color(heat: int) -> tuple[int, int, int] | None:
    """Get the display color for a criminal heat value.

    Args:
        heat: Criminal heat (0-100).

    Returns:
        RGB tuple for the heat indicator, or None if heat is 0.
    """
    if heat <= 0:
        return None
    if heat <= 10:
        return (255, 255, 255)  # White — low
    if heat <= 25:
        return (255, 255, 0)  # Yellow — moderate
    if heat <= 50:
        return (255, 165, 0)  # Orange — high
    return (255, 50, 50)  # Red — critical


# ============================================================================
# AUDIO SETTINGS
# ============================================================================

MIXER_FREQUENCY = 44100
MIXER_SIZE = -16  # 16-bit signed
MIXER_CHANNELS = 2  # Stereo
MIXER_BUFFER = 1024

DEFAULT_MASTER_VOLUME = 1.0
DEFAULT_MUSIC_VOLUME = 0.7
DEFAULT_SFX_VOLUME = 0.9
DEFAULT_AMBIENT_VOLUME = 0.6

MUSIC_FADE_MS = 1000  # Default music cross-fade in milliseconds

# ============================================================================
# IMAGE ASSET NAMES
# ============================================================================

# === DANGER YIELD SCALING ===
# Multiplier applied to mining/salvage yields based on system danger level
DANGER_YIELD_MULTIPLIERS: dict[str, float] = {
    "safe": 1.0,
    "moderate": 1.15,
    "dangerous": 1.3,
}

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
