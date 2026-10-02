"""
AI Hand Gesture Controller for Asphalt 8
========================================

Main entry point. Initializes the application and starts the UI.

Usage:
    python main.py
    python main.py --test     (test mode - no keyboard output)
    python main.py --live     (live mode - sends real keyboard input)
    python main.py --debug    (enable debug panel)
"""

import sys
import os

# Ensure the package root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, save_config
from utils.logger import logger


def main():
    """Main entry point."""
    config = get_config()

    # Always default to test mode for safety
    config.test_mode = True
    start_live = False

    # Parse CLI args
    if "--live" in sys.argv:
        start_live = True
        logger.info("Requested LIVE MODE via CLI, awaiting confirmation...")
    elif "--test" in sys.argv:
        logger.info("Starting in TEST MODE (no keyboard output)")

    if "--debug" in sys.argv:
        config.debug_mode = True

    save_config()

    # Import UI after config is set
    from ui.main_window import MainWindow

    logger.info("=" * 50)
    logger.info("AI Hand Gesture Controller for Asphalt 8")
    logger.info("=" * 50)
    logger.info(f"Mode: TEST (Safe Default)")
    logger.info(f"Debug: {'ON' if config.debug_mode else 'OFF'}")
    logger.info(f"Camera device: {config.camera.device_index}")
    logger.info(f"Steering zones: L<{config.steering.center_left:.2f} "
                f"C[{config.steering.center_left:.2f}-{config.steering.center_right:.2f}] "
                f"R>{config.steering.center_right:.2f}")
    logger.info("=" * 50)

    app = MainWindow()
    
    # If live mode requested via CLI, prompt immediately after UI init
    if start_live:
        # Schedule the toggle prompt after the mainloop starts
        app.root.after(500, app._on_toggle_mode)

    app.run()


if __name__ == "__main__":
    main()
