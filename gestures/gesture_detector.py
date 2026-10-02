"""
Gesture Detector - Detects specific hand gestures from landmark data.
"""

from typing import Dict, List, Tuple

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import GestureConfig


class GestureDetector:
    """Detects gestures from processed hand landmark metrics."""

    def __init__(self, config: GestureConfig = None):
        self.config = config or GestureConfig()

    def detect_fist(self, finger_states: List[bool], hand_openness: float) -> bool:
        """
        Detect closed fist.
        Fist = no fingers raised AND hand openness below threshold.
        """
        raised = sum(finger_states)
        return raised <= 1 and hand_openness < self.config.fist_threshold

    def detect_two_fingers(self, finger_states: List[bool],
                           raised_count: int) -> bool:
        """
        Detect two-finger gesture (index + middle raised).
        """
        if raised_count < 2 or raised_count > 3:
            return False

        # Index and middle must be raised
        # finger_states = [thumb, index, middle, ring, pinky]
        index_up = finger_states[1] if len(finger_states) > 1 else False
        middle_up = finger_states[2] if len(finger_states) > 2 else False
        ring_down = not finger_states[3] if len(finger_states) > 3 else True
        pinky_down = not finger_states[4] if len(finger_states) > 4 else True

        return index_up and middle_up and ring_down and pinky_down

    def detect_open_palm(self, finger_states: List[bool],
                         hand_openness: float) -> bool:
        """
        Detect open palm (all fingers raised).
        """
        raised = sum(finger_states)
        return raised >= 4 and hand_openness > self.config.open_palm_threshold

    def detect_pinch(self, pinch_distance: float) -> bool:
        """Detect pinch gesture (thumb + index close together)."""
        return pinch_distance < self.config.pinch_threshold

    def detect_all(self, metrics: dict) -> Dict[str, bool]:
        """
        Run all gesture detections on the processed metrics.
        
        Returns dict of gesture_name -> bool.
        """
        finger_states = metrics.get("finger_states", [False] * 5)
        raised_count = metrics.get("raised_count", 0)
        hand_openness = metrics.get("hand_openness", 0.0)
        pinch_distance = metrics.get("pinch_distance", 0.0)

        return {
            "fist": self.detect_fist(finger_states, hand_openness),
            "two_fingers": self.detect_two_fingers(finger_states, raised_count),
            "open_palm": self.detect_open_palm(finger_states, hand_openness),
            "pinch": self.detect_pinch(pinch_distance),
        }

    def update_config(self, config: GestureConfig):
        self.config = config
