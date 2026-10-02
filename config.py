"""
Central configuration for AI Hand Gesture Controller.
All default values and configuration management.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional


import platform

# --- Paths ---
APP_NAME = "AI-Gesture-Controller"

if platform.system() == "Windows":
    APP_DATA_DIR = os.environ.get("APPDATA", os.path.expanduser("~"))
    BASE_DIR = os.path.join(APP_DATA_DIR, APP_NAME)
elif platform.system() == "Darwin":
    BASE_DIR = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
else:
    BASE_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist
os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


@dataclass
class CameraConfig:
    device_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    mirror: bool = True


@dataclass
class TrackingConfig:
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.5
    max_num_hands: int = 1
    model_complexity: int = 1
    smoothing_factor: float = 0.3
    gesture_stability_frames: int = 5


@dataclass
class SteeringConfig:
    left_limit: float = 0.0
    left_boundary: float = 0.40
    center_left: float = 0.40
    center_right: float = 0.60
    right_boundary: float = 0.60
    right_limit: float = 1.0
    sensitivity: float = 1.0
    dead_zone: float = 0.05
    hysteresis: float = 0.03
    smoothing_alpha: float = 0.25
    min_movement_threshold: float = 0.01


@dataclass
class ControlsConfig:
    left_key: str = "left"
    right_key: str = "right"
    brake_key: str = "down"
    nitro_key: str = "space"
    emergency_key: str = "f12"


@dataclass
class SafetyConfig:
    only_control_when_game_active: bool = False
    game_window_title: str = "Asphalt 8"
    game_process_name: str = ""
    hand_lost_timeout: float = 0.5
    nitro_cooldown: float = 0.5


@dataclass
class GestureConfig:
    fist_threshold: float = 0.25
    two_finger_min_distance: float = 0.06
    open_palm_threshold: float = 0.15
    pinch_threshold: float = 0.05
    confidence_threshold: float = 0.7


@dataclass
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    steering: SteeringConfig = field(default_factory=SteeringConfig)
    controls: ControlsConfig = field(default_factory=ControlsConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    gesture: GestureConfig = field(default_factory=GestureConfig)
    test_mode: bool = True  # Default to test mode for safety
    debug_mode: bool = False
    ui_update_interval: int = 50  # ms between UI updates
    current_profile: str = "default"
    first_run: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        config = cls()
        if "camera" in data:
            config.camera = CameraConfig(**data["camera"])
        if "tracking" in data:
            config.tracking = TrackingConfig(**data["tracking"])
        if "steering" in data:
            config.steering = SteeringConfig(**data["steering"])
        if "controls" in data:
            config.controls = ControlsConfig(**data["controls"])
        if "safety" in data:
            config.safety = SafetyConfig(**data["safety"])
        if "gesture" in data:
            config.gesture = GestureConfig(**data["gesture"])
        for key in ["test_mode", "debug_mode", "ui_update_interval", "current_profile", "first_run"]:
            if key in data:
                setattr(config, key, data[key])
        return config

    def save(self, path: Optional[str] = None):
        path = path or CONFIG_FILE
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        path = path or CONFIG_FILE
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                return cls.from_dict(data)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return cls()


# Global config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def save_config():
    global _config
    if _config is not None:
        _config.save()


def reset_config():
    global _config
    _config = AppConfig()
