"""
Main entry point for Space Trader game.

Run this module to start the game.
"""

import sys
from spacegame.engine.game import main as game_main
from spacegame.utils.logger import logger, setup_logger
import logging


def main() -> None:
    """Application entry point."""
    # Set up logging (use DEBUG for development, INFO for release)
    setup_logger(level=logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Space Trader - Starting...")
    logger.info("=" * 60)

    try:
        game_main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
