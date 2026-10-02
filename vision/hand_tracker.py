"""
Hand Tracker - MediaPipe hand landmark detection.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass, field

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.logger import logger


@dataclass
class HandData:
    """Processed hand landmark data."""
    landmarks: List[Tuple[float, float, float]] = field(default_factory=list)
    # Normalized 0-1 coordinates
    index_tip: Tuple[float, float] = (0.0, 0.0)
    thumb_tip: Tuple[float, float] = (0.0, 0.0)
    palm_center: Tuple[float, float] = (0.0, 0.0)
    wrist: Tuple[float, float] = (0.0, 0.0)

    # Finger states (True = raised)
    finger_states: List[bool] = field(default_factory=lambda: [False] * 5)
    raised_count: int = 0

    # Metrics
    pinch_distance: float = 0.0
    hand_openness: float = 0.0
    is_detected: bool = False
    handedness: str = "Unknown"

    # Pixel coordinates for drawing
    landmarks_px: List[Tuple[int, int]] = field(default_factory=list)


class HandTracker:
    """MediaPipe-based hand tracking."""

    # MediaPipe hand connections for drawing
    CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),     # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),     # Index
        (0, 9), (9, 10), (10, 11), (11, 12), # Middle
        (0, 13), (13, 14), (14, 15), (15, 16), # Ring
        (0, 17), (17, 18), (18, 19), (19, 20), # Pinky
        (5, 9), (9, 13), (13, 17),           # Palm
    ]

    def __init__(
        self,
        max_hands: int = 1,
        detection_confidence: float = 0.7,
        tracking_confidence: float = 0.5,
        model_complexity: int = 1,
    ):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils

        logger.info(f"Initializing MediaPipe Hands (max_hands={max_hands}, "
                    f"detection_conf={detection_confidence}, "
                    f"tracking_conf={tracking_confidence})")

        # Try with model_complexity first (MediaPipe >= 0.8.9),
        # fall back without it for older versions
        try:
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                min_detection_confidence=detection_confidence,
                min_tracking_confidence=tracking_confidence,
                model_complexity=model_complexity,
            )
        except TypeError:
            logger.warning("model_complexity not supported, using default")
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=max_hands,
                min_detection_confidence=detection_confidence,
                min_tracking_confidence=tracking_confidence,
            )
        self._last_hand_data = HandData()
        logger.info("MediaPipe Hands initialized successfully")

    def process_frame(self, frame: np.ndarray) -> HandData:
        """Process a BGR frame and return hand data."""
        h, w, _ = frame.shape

        # Convert BGR -> RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        hand_data = HandData()

        if results.multi_hand_landmarks and len(results.multi_hand_landmarks) > 0:
            hand_landmarks = results.multi_hand_landmarks[0]
            hand_data.is_detected = True

            # Get handedness
            if results.multi_handedness:
                hand_data.handedness = results.multi_handedness[0].classification[0].label

            # Extract all 21 landmarks (normalized 0-1)
            for lm in hand_landmarks.landmark:
                hand_data.landmarks.append((lm.x, lm.y, lm.z))
                hand_data.landmarks_px.append((int(lm.x * w), int(lm.y * h)))

            # Key points
            hand_data.index_tip = (hand_landmarks.landmark[8].x, hand_landmarks.landmark[8].y)
            hand_data.thumb_tip = (hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y)
            hand_data.wrist = (hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y)

            # Palm center = average of wrist(0), index_mcp(5), middle_mcp(9), ring_mcp(13), pinky_mcp(17)
            palm_indices = [0, 5, 9, 13, 17]
            px = sum(hand_landmarks.landmark[i].x for i in palm_indices) / 5
            py = sum(hand_landmarks.landmark[i].y for i in palm_indices) / 5
            hand_data.palm_center = (px, py)

            # Finger states
            hand_data.finger_states = self._get_finger_states(hand_landmarks)
            hand_data.raised_count = sum(hand_data.finger_states)

            # Pinch distance (thumb tip to index tip)
            hand_data.pinch_distance = self._distance_2d(
                hand_landmarks.landmark[4], hand_landmarks.landmark[8]
            )

            # Hand openness (average distance of fingertips from palm center)
            tip_indices = [4, 8, 12, 16, 20]
            total_dist = 0
            for ti in tip_indices:
                dx = hand_landmarks.landmark[ti].x - px
                dy = hand_landmarks.landmark[ti].y - py
                total_dist += (dx**2 + dy**2) ** 0.5
            hand_data.hand_openness = total_dist / 5

        self._last_hand_data = hand_data
        return hand_data

    def _get_finger_states(self, hand_landmarks) -> List[bool]:
        """
        Determine which fingers are raised.
        Returns [thumb, index, middle, ring, pinky].
        """
        lm = hand_landmarks.landmark
        states = []

        # Thumb: compare tip.x to IP.x
        # For right hand: tip.x < ip.x means raised
        # For left hand: tip.x > ip.x means raised
        # Since we mirror, we use a simpler heuristic:
        # Compare thumb tip to thumb MCP in x-direction
        thumb_raised = self._distance_2d(lm[4], lm[2]) > self._distance_2d(lm[3], lm[2]) * 1.2
        states.append(thumb_raised)

        # Other fingers: tip.y < pip.y means raised (in image coords, lower y = higher)
        for tip_idx, pip_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            states.append(lm[tip_idx].y < lm[pip_idx].y)

        return states

    @staticmethod
    def _distance_2d(lm1, lm2) -> float:
        """Euclidean distance between two landmarks (2D)."""
        return ((lm1.x - lm2.x)**2 + (lm1.y - lm2.y)**2) ** 0.5

    def draw_landmarks(self, frame: np.ndarray, hand_data: HandData) -> np.ndarray:
        """Draw hand landmarks and connections on the frame."""
        if not hand_data.is_detected or not hand_data.landmarks_px:
            return frame

        overlay = frame.copy()
        h, w = frame.shape[:2]

        # Draw connections
        for start_idx, end_idx in self.CONNECTIONS:
            if start_idx < len(hand_data.landmarks_px) and end_idx < len(hand_data.landmarks_px):
                pt1 = hand_data.landmarks_px[start_idx]
                pt2 = hand_data.landmarks_px[end_idx]
                cv2.line(overlay, pt1, pt2, (0, 255, 200), 2, cv2.LINE_AA)

        # Draw landmarks
        for i, pt in enumerate(hand_data.landmarks_px):
            color = (0, 200, 255)  # Yellow-orange for normal
            radius = 4

            if i == 8:  # Index tip - larger, different color
                color = (0, 100, 255)  # Orange-red
                radius = 8
            elif i == 0:  # Wrist
                color = (255, 200, 0)  # Cyan
                radius = 6
            elif i in [4, 12, 16, 20]:  # Other tips
                color = (100, 255, 100)  # Green
                radius = 5

            cv2.circle(overlay, pt, radius, color, -1, cv2.LINE_AA)
            cv2.circle(overlay, pt, radius + 1, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw palm center
        if hand_data.palm_center:
            pcx = int(hand_data.palm_center[0] * w)
            pcy = int(hand_data.palm_center[1] * h)
            cv2.circle(overlay, (pcx, pcy), 10, (255, 0, 255), 2, cv2.LINE_AA)
            cv2.drawMarker(overlay, (pcx, pcy), (255, 0, 255),
                          cv2.MARKER_CROSS, 20, 2, cv2.LINE_AA)

        # Blend overlay
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        return frame

    def release(self):
        """Release MediaPipe resources."""
        if self.hands:
            self.hands.close()
            logger.info("MediaPipe Hands released")
