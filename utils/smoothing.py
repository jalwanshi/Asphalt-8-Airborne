"""Smoothing utilities for hand position data."""

from collections import deque
from typing import Tuple, Optional


class ExponentialMovingAverage:
    """Exponential moving average filter for smoothing position data."""

    def __init__(self, alpha: float = 0.3):
        """
        Args:
            alpha: Smoothing factor (0-1). Lower = smoother but more lag.
        """
        self.alpha = alpha
        self._value: Optional[float] = None

    def update(self, new_value: float) -> float:
        if self._value is None:
            self._value = new_value
        else:
            self._value = self.alpha * new_value + (1 - self.alpha) * self._value
        return self._value

    def reset(self):
        self._value = None

    @property
    def value(self) -> Optional[float]:
        return self._value


class PositionSmoother:
    """Full smoothing pipeline for 2D position data."""

    def __init__(
        self,
        alpha: float = 0.3,
        min_movement: float = 0.01,
        buffer_size: int = 5,
    ):
        self.ema_x = ExponentialMovingAverage(alpha)
        self.ema_y = ExponentialMovingAverage(alpha)
        self.min_movement = min_movement
        self._last_output_x: Optional[float] = None
        self._last_output_y: Optional[float] = None
        self._history_x = deque(maxlen=buffer_size)
        self._history_y = deque(maxlen=buffer_size)

    def update(self, x: float, y: float) -> Tuple[float, float]:
        # Apply EMA
        smoothed_x = self.ema_x.update(x)
        smoothed_y = self.ema_y.update(y)

        # Store history for velocity
        self._history_x.append(smoothed_x)
        self._history_y.append(smoothed_y)

        # Apply minimum movement threshold
        if self._last_output_x is not None:
            dx = abs(smoothed_x - self._last_output_x)
            dy = abs(smoothed_y - self._last_output_y)
            if dx < self.min_movement:
                smoothed_x = self._last_output_x
            if dy < self.min_movement:
                smoothed_y = self._last_output_y

        self._last_output_x = smoothed_x
        self._last_output_y = smoothed_y

        return smoothed_x, smoothed_y

    def get_velocity(self) -> Tuple[float, float]:
        """Get the velocity of the position (change rate)."""
        if len(self._history_x) < 2:
            return 0.0, 0.0
        vx = self._history_x[-1] - self._history_x[-2]
        vy = self._history_y[-1] - self._history_y[-2]
        return vx, vy

    def reset(self):
        self.ema_x.reset()
        self.ema_y.reset()
        self._last_output_x = None
        self._last_output_y = None
        self._history_x.clear()
        self._history_y.clear()


class SteeringSmoother:
    """Specialized smoother for steering with dead zone and hysteresis."""

    def __init__(
        self,
        alpha: float = 0.25,
        dead_zone: float = 0.05,
        hysteresis: float = 0.03,
        min_movement: float = 0.01,
    ):
        self.ema = ExponentialMovingAverage(alpha)
        self.dead_zone = dead_zone
        self.hysteresis = hysteresis
        self.min_movement = min_movement
        self._last_zone: Optional[str] = None  # "left", "center", "right"
        self._last_output: Optional[float] = None

    def update(
        self,
        raw_x: float,
        center_left: float,
        center_right: float,
    ) -> Tuple[float, str]:
        """
        Process raw X position through smoothing pipeline.

        Returns:
            (smoothed_x, zone) where zone is "left", "center", or "right"
        """
        # Step 1: EMA smoothing
        smoothed = self.ema.update(raw_x)

        # Step 2: Minimum movement threshold
        if self._last_output is not None:
            if abs(smoothed - self._last_output) < self.min_movement:
                smoothed = self._last_output
        self._last_output = smoothed

        # Step 3: Determine zone with hysteresis
        zone = self._determine_zone(smoothed, center_left, center_right)

        return smoothed, zone

    def _determine_zone(
        self, x: float, center_left: float, center_right: float
    ) -> str:
        """Determine steering zone with hysteresis to prevent flickering."""
        hyst = self.hysteresis

        if self._last_zone == "left":
            # Need to move past center_left + hysteresis to switch to center
            if x > center_left + hyst:
                if x > center_right + hyst:
                    zone = "right"
                else:
                    zone = "center"
            else:
                zone = "left"
        elif self._last_zone == "right":
            # Need to move past center_right - hysteresis to switch to center
            if x < center_right - hyst:
                if x < center_left - hyst:
                    zone = "left"
                else:
                    zone = "center"
            else:
                zone = "right"
        else:
            # Currently center or first time
            if x < center_left - hyst:
                zone = "left"
            elif x > center_right + hyst:
                zone = "right"
            else:
                zone = "center"

        self._last_zone = zone
        return zone

    def reset(self):
        self.ema.reset()
        self._last_zone = None
        self._last_output = None

    @property
    def current_zone(self) -> Optional[str]:
        return self._last_zone
