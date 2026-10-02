"""
Landmark Processor - Processes raw landmarks into actionable metrics.
"""

from typing import Tuple, Optional, List
from collections import deque
import time

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vision.hand_tracker import HandData
from utils.smoothing import PositionSmoother


class LandmarkProcessor:
    """Processes hand landmarks into smoothed, normalized metrics."""

    def __init__(self, smoothing_factor: float = 0.3, min_movement: float = 0.01):
        self._smoother = PositionSmoother(
            alpha=smoothing_factor,
            min_movement=min_movement,
            buffer_size=10,
        )
        self._velocity_history = deque(maxlen=10)
        self._last_time = time.time()

    def process(self, hand_data: HandData) -> dict:
        """
        Process hand data into smoothed metrics.
        
        Returns dict with:
            - smoothed_x, smoothed_y: smoothed index fingertip position
            - velocity_x, velocity_y: hand velocity
            - speed: absolute speed
            - raw_x, raw_y: unsmoothed position
            - palm_x, palm_y: palm center
            - finger_states: list of bool
            - raised_count: int
            - pinch_distance: float
            - hand_openness: float
            - is_detected: bool
        """
        if not hand_data.is_detected:
            return {
                "is_detected": False,
                "smoothed_x": 0.5,
                "smoothed_y": 0.5,
                "velocity_x": 0.0,
                "velocity_y": 0.0,
                "speed": 0.0,
                "raw_x": 0.5,
                "raw_y": 0.5,
                "palm_x": 0.5,
                "palm_y": 0.5,
                "finger_states": [False] * 5,
                "raised_count": 0,
                "pinch_distance": 0.0,
                "hand_openness": 0.0,
            }

        raw_x, raw_y = hand_data.index_tip
        smoothed_x, smoothed_y = self._smoother.update(raw_x, raw_y)
        vx, vy = self._smoother.get_velocity()

        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        speed = (vx**2 + vy**2) ** 0.5
        if dt > 0:
            speed /= dt  # Normalize by time

        return {
            "is_detected": True,
            "smoothed_x": smoothed_x,
            "smoothed_y": smoothed_y,
            "velocity_x": vx,
            "velocity_y": vy,
            "speed": speed,
            "raw_x": raw_x,
            "raw_y": raw_y,
            "palm_x": hand_data.palm_center[0],
            "palm_y": hand_data.palm_center[1],
            "finger_states": hand_data.finger_states,
            "raised_count": hand_data.raised_count,
            "pinch_distance": hand_data.pinch_distance,
            "hand_openness": hand_data.hand_openness,
        }

    def reset(self):
        """Reset smoother state."""
        self._smoother.reset()
        self._velocity_history.clear()
