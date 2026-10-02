"""
Camera Manager - Handles webcam capture, frame retrieval, and camera lifecycle.
"""

import cv2
import threading
import time
from typing import Optional, Tuple, List
import numpy as np

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.logger import logger


class CameraManager:
    """Manages webcam capture with thread-safe frame access."""

    def __init__(self, device_index: int = 0, width: int = 640, height: int = 480,
                 fps: int = 30, mirror: bool = True):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.target_fps = fps
        self.mirror = mirror

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._paused = False

        # FPS tracking
        self._fps = 0.0
        self._frame_count = 0
        self._fps_timer = time.time()

    @staticmethod
    def list_cameras(max_check: int = 5) -> List[int]:
        """Detect available camera devices."""
        available = []
        for i in range(max_check):
            cap = cv2.VideoCapture(i)
            if cap is not None and cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def start(self) -> bool:
        """Start the camera capture."""
        if self._running:
            logger.warning("Camera already running")
            return True

        logger.info(f"Starting camera (device={self.device_index}, "
                    f"{self.width}x{self.height} @ {self.target_fps}fps)")

        self._cap = cv2.VideoCapture(self.device_index)
        if not self._cap.isOpened():
            logger.error(f"Failed to open camera device {self.device_index}")
            return False

        # Configure camera
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        # Read actual settings
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Camera opened: actual resolution {actual_w}x{actual_h}")

        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

        logger.info("Camera capture thread started")
        return True

    def stop(self):
        """Stop the camera capture."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._frame = None
        logger.info("Camera stopped")

    def pause(self):
        """Pause frame processing."""
        self._paused = True
        logger.info("Camera paused")

    def resume(self):
        """Resume frame processing."""
        self._paused = False
        logger.info("Camera resumed")

    def _capture_loop(self):
        """Background capture loop."""
        while self._running:
            if self._paused:
                time.sleep(0.05)
                continue

            if self._cap is None or not self._cap.isOpened():
                logger.error("Camera disconnected")
                self._running = False
                break

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame")
                time.sleep(0.01)
                continue

            if self.mirror:
                frame = cv2.flip(frame, 1)

            with self._lock:
                self._frame = frame

            # FPS calculation
            self._frame_count += 1
            elapsed = time.time() - self._fps_timer
            if elapsed >= 1.0:
                self._fps = self._frame_count / elapsed
                self._frame_count = 0
                self._fps_timer = time.time()

            # Throttle to target FPS
            time.sleep(max(0, 1.0 / self.target_fps - 0.001))

    def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame (thread-safe copy)."""
        with self._lock:
            if self._frame is not None:
                return self._frame.copy()
        return None

    @property
    def fps(self) -> float:
        return round(self._fps, 1)

    @property
    def is_active(self) -> bool:
        return self._running and self._cap is not None and self._cap.isOpened()

    @property
    def is_paused(self) -> bool:
        return self._paused

    def change_device(self, device_index: int):
        """Switch to a different camera device."""
        was_running = self._running
        if was_running:
            self.stop()
        self.device_index = device_index
        if was_running:
            self.start()
