"""
Steering Controller - Maps hand position to steering zones with smoothing.
"""

from typing import Tuple, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import SteeringConfig
from utils.smoothing import SteeringSmoother
from utils.logger import logger


class SteeringController:
    """Controls steering based on hand X position."""

    def __init__(self, config: SteeringConfig = None):
        self.config = config or SteeringConfig()
        self._smoother = SteeringSmoother(
            alpha=self.config.smoothing_alpha,
            dead_zone=self.config.dead_zone,
            hysteresis=self.config.hysteresis,
            min_movement=self.config.min_movement_threshold,
        )
        self._current_zone = "center"
        self._smoothed_x = 0.5

    def update(self, raw_x: float) -> Tuple[str, float]:
        """
        Process raw hand X position through the steering pipeline.
        
        Returns:
            (zone, smoothed_x) where zone is "left", "center", or "right"
        """
        self._smoothed_x, self._current_zone = self._smoother.update(
            raw_x,
            self.config.center_left,
            self.config.center_right,
        )
        return self._current_zone, self._smoothed_x

    @property
    def zone(self) -> str:
        return self._current_zone

    @property
    def smoothed_x(self) -> float:
        return self._smoothed_x

    def get_zone_position(self) -> float:
        """
        Get normalized position within zones.
        Returns value from -1.0 (full left) to 1.0 (full right),
        0.0 = center.
        """
        x = self._smoothed_x
        cl = self.config.center_left
        cr = self.config.center_right
        ll = self.config.left_limit
        rl = self.config.right_limit

        if x < cl:
            # In left zone: map [left_limit, center_left] -> [-1, 0]
            if cl - ll > 0:
                return -1.0 + (x - ll) / (cl - ll)
            return -1.0
        elif x > cr:
            # In right zone: map [center_right, right_limit] -> [0, 1]
            if rl - cr > 0:
                return (x - cr) / (rl - cr)
            return 1.0
        else:
            return 0.0

    def calibrate_center(self, x: float):
        """Set center zone from calibration."""
        margin = self.config.dead_zone
        self.config.center_left = max(0.0, x - 0.10)
        self.config.center_right = min(1.0, x + 0.10)
        logger.info(f"Calibrated center: [{self.config.center_left:.3f}, {self.config.center_right:.3f}]")

    def calibrate_left(self, x: float):
        """Set left boundary from calibration."""
        self.config.left_limit = max(0.0, x - 0.05)
        self.config.center_left = x + 0.05
        logger.info(f"Calibrated left: limit={self.config.left_limit:.3f}, boundary={self.config.center_left:.3f}")

    def calibrate_right(self, x: float):
        """Set right boundary from calibration."""
        self.config.right_limit = min(1.0, x + 0.05)
        self.config.center_right = x - 0.05
        logger.info(f"Calibrated right: boundary={self.config.center_right:.3f}, limit={self.config.right_limit:.3f}")

    def reset(self):
        """Reset smoother state."""
        self._smoother.reset()
        self._current_zone = "center"
        self._smoothed_x = 0.5

    def update_config(self, config: SteeringConfig):
        """Update steering config and recreate smoother."""
        self.config = config
        self._smoother = SteeringSmoother(
            alpha=config.smoothing_alpha,
            dead_zone=config.dead_zone,
            hysteresis=config.hysteresis,
            min_movement=config.min_movement_threshold,
        )
