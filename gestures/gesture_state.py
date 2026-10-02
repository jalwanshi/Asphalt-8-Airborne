"""
Gesture State - Tracks gesture states with confidence and edge detection.
"""

import time
from enum import Enum, auto
from typing import Optional


class GestureType(Enum):
    NONE = auto()
    STEERING = auto()
    FIST = auto()          # Brake
    TWO_FINGERS = auto()   # Nitro
    OPEN_PALM = auto()     # Neutral


class GestureState:
    """Tracks a single gesture's state with stability and edge detection."""

    def __init__(self, stability_frames: int = 5, cooldown: float = 0.0):
        self.stability_frames = stability_frames
        self.cooldown = cooldown

        self._active = False
        self._candidate_active = False
        self._candidate_count = 0
        self._last_activation_time = 0.0
        self._last_deactivation_time = 0.0

        # Edge detection
        self._just_activated = False
        self._just_deactivated = False

    def update(self, detected: bool):
        """Update gesture state. Call once per frame."""
        self._just_activated = False
        self._just_deactivated = False

        if detected == self._candidate_active:
            self._candidate_count += 1
        else:
            self._candidate_active = detected
            self._candidate_count = 1

        # Check stability
        if self._candidate_count >= self.stability_frames:
            if self._candidate_active and not self._active:
                # Check cooldown
                if time.time() - self._last_deactivation_time >= self.cooldown:
                    self._active = True
                    self._just_activated = True
                    self._last_activation_time = time.time()
            elif not self._candidate_active and self._active:
                self._active = False
                self._just_deactivated = True
                self._last_deactivation_time = time.time()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def just_activated(self) -> bool:
        """True only on the frame the gesture becomes active."""
        return self._just_activated

    @property
    def just_deactivated(self) -> bool:
        """True only on the frame the gesture becomes inactive."""
        return self._just_deactivated

    def reset(self):
        self._active = False
        self._candidate_active = False
        self._candidate_count = 0
        self._just_activated = False
        self._just_deactivated = False


class GestureStateManager:
    """Manages all gesture states together."""

    def __init__(self, stability_frames: int = 5, nitro_cooldown: float = 0.5):
        self.fist = GestureState(stability_frames=stability_frames)
        self.two_fingers = GestureState(
            stability_frames=stability_frames,
            cooldown=nitro_cooldown,
        )
        self.open_palm = GestureState(stability_frames=stability_frames)
        self._current_gesture = GestureType.NONE

    def update(self, fist_detected: bool, two_fingers_detected: bool,
               open_palm_detected: bool):
        """Update all gesture states."""
        self.fist.update(fist_detected)
        self.two_fingers.update(two_fingers_detected)
        self.open_palm.update(open_palm_detected)

        # Determine current primary gesture (priority: fist > two_fingers > open_palm > steering)
        if self.fist.is_active:
            self._current_gesture = GestureType.FIST
        elif self.two_fingers.is_active:
            self._current_gesture = GestureType.TWO_FINGERS
        elif self.open_palm.is_active:
            self._current_gesture = GestureType.OPEN_PALM
        else:
            self._current_gesture = GestureType.STEERING

    @property
    def current_gesture(self) -> GestureType:
        return self._current_gesture

    def reset(self):
        self.fist.reset()
        self.two_fingers.reset()
        self.open_palm.reset()
        self._current_gesture = GestureType.NONE
