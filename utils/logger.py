"""Logger utility for the AI Gesture Controller."""

import logging
import os
import sys
from datetime import datetime

# Ensure project root is on path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import LOGS_DIR


def setup_logger(name: str = "gesture_controller") -> logging.Logger:
    """Setup and return a configured logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler
    log_file = os.path.join(LOGS_DIR, "controller.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("=" * 60)
    logger.info("AI Hand Gesture Controller - Session Started")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    return logger


# Module-level logger
logger = setup_logger()
