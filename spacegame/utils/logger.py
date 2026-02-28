"""
Logging configuration for the game.

Sets up structured logging for debugging and monitoring game behavior.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(name: str = "spacegame", level: int = logging.INFO) -> logging.Logger:
    """
    Set up and configure the game logger.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format: [TIMESTAMP] LEVEL - Message
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)

    # Optional: File handler for persistent logs
    # Uncomment when you want file logging
    # log_dir = Path("logs")
    # log_dir.mkdir(exist_ok=True)
    # file_handler = logging.FileHandler(log_dir / "spacegame.log")
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    return logger


# Create default logger
logger = setup_logger()
