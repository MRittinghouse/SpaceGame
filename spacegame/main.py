"""
Main entry point for Space Trader game.

Run this module to start the game.
"""

import json
import os
import sys
from pathlib import Path

import logging


def _load_display_settings() -> None:
    """Load resolution and fullscreen from settings.json before game imports.

    Reads the settings file directly (no SaveManager import) to avoid pulling
    in heavy model imports that would snapshot WINDOW_WIDTH/HEIGHT too early.
    """
    import spacegame.config as config

    # Mirror SaveManager's settings path logic
    if os.name == "nt":
        appdata = os.getenv("APPDATA", "")
        settings_path = Path(appdata) / "SpaceGame" / "saves" / "settings.json"
    else:
        settings_path = Path.home() / ".spacegame" / "saves" / "settings.json"

    settings: dict = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # Apply resolution
    res = settings.get("resolution", list(config.DEFAULT_RESOLUTION))
    if isinstance(res, (list, tuple)) and len(res) == 2:
        w, h = int(res[0]), int(res[1])
        if (w, h) in config.SUPPORTED_RESOLUTIONS:
            config.set_resolution(w, h)

    # Apply fullscreen
    if settings.get("fullscreen", False):
        config.FULLSCREEN = True


def main() -> None:
    """Application entry point."""
    from spacegame.utils.logger import logger, setup_logger

    # Set up logging (use DEBUG for development, INFO for release)
    setup_logger(level=logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Space Trader - Starting...")
    logger.info("=" * 60)

    # Load display settings BEFORE importing game (which imports views)
    _load_display_settings()

    try:
        from spacegame.engine.game import main as game_main

        game_main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
