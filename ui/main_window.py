"""
Main Window - Dark futuristic Tkinter UI for AI Hand Gesture Controller.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import time
from typing import Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_config, save_config, AppConfig
from camera.camera_manager import CameraManager
from vision.hand_tracker import HandTracker, HandData
from vision.landmark_processor import LandmarkProcessor
from gestures.gesture_detector import GestureDetector
from gestures.steering_controller import SteeringController
from gestures.gesture_state import GestureStateManager, GestureType
from input.keyboard_controller import KeyboardController, is_game_window_active
from utils.logger import logger


# ─── Color Palette (Dark Futuristic) ───
BG_DARK = "#0a0e17"
BG_PANEL = "#111827"
BG_CARD = "#1a2332"
BG_CARD_HOVER = "#1f2b3d"
ACCENT_CYAN = "#00d4ff"
ACCENT_BLUE = "#3b82f6"
ACCENT_GREEN = "#10b981"
ACCENT_RED = "#ef4444"
ACCENT_ORANGE = "#f59e0b"
ACCENT_PURPLE = "#8b5cf6"
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
BORDER_COLOR = "#1e293b"
BORDER_ACTIVE = "#334155"

STATUS_ON = "#10b981"
STATUS_OFF = "#ef4444"
STATUS_WARN = "#f59e0b"


class MainWindow:
    """Main application window with camera preview, controls, and debug panel."""

    def __init__(self):
        self.config = get_config()
        self.root = tk.Tk()
        self.root.title("AI Hand Gesture Controller for Asphalt 8")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("1280x820")
        self.root.minsize(1100, 750)

        # Try to set icon
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # ─── Core components ───
        self.camera = CameraManager(
            device_index=self.config.camera.device_index,
            width=self.config.camera.width,
            height=self.config.camera.height,
            fps=self.config.camera.fps,
            mirror=self.config.camera.mirror,
        )
        self.hand_tracker = HandTracker(
            max_hands=self.config.tracking.max_num_hands,
            detection_confidence=self.config.tracking.min_detection_confidence,
            tracking_confidence=self.config.tracking.min_tracking_confidence,
            model_complexity=self.config.tracking.model_complexity,
        )
        self.landmark_processor = LandmarkProcessor(
            smoothing_factor=self.config.tracking.smoothing_factor,
            min_movement=self.config.steering.min_movement_threshold,
        )
        self.gesture_detector = GestureDetector(self.config.gesture)
        self.steering = SteeringController(self.config.steering)
        self.gesture_states = GestureStateManager(
            stability_frames=self.config.tracking.gesture_stability_frames,
            nitro_cooldown=self.config.safety.nitro_cooldown,
        )
        self.keyboard = KeyboardController(test_mode=self.config.test_mode)

        # ─── State ───
        self._controller_active = False
        self._hand_lost_time: Optional[float] = None
        self._last_hand_data = HandData()
        self._last_metrics = {}
        self._last_gestures = {}
        self._current_zone = "center"
        self._processing = False
        self._nitro_ready = True
        self._debug_vars = {}  # Initialized here so it always exists

        # ─── Build UI ───
        self._build_styles()
        self._build_ui()
        self._bind_events()

        # Start camera
        self.camera.start()

        # Start processing loop
        self._schedule_update()

        # Show first run experience if needed
        if getattr(self.config, 'first_run', False):
            self.root.after(1000, self._show_first_run_wizard)

        logger.info("Main window initialized")

    def _show_first_run_wizard(self):
        """Display the Windows first run experience wizard."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Setup Wizard")
        dlg.geometry("500x380")
        dlg.configure(bg=BG_DARK)
        dlg.transient(self.root)
        dlg.grab_set()

        # Center the dialog
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 380) // 2
        dlg.geometry(f"+{x}+{y}")

        tk.Label(dlg, text="AI GESTURE CONTROLLER", font=("Segoe UI", 16, "bold"), 
                 fg=ACCENT_CYAN, bg=BG_DARK).pack(pady=(20, 10))
        
        steps = [
            "1. Camera Setup",
            "2. Hand Tracking Test",
            "3. Steering Calibration",
            "4. Gesture Calibration",
            "5. Keyboard Test",
            "6. Game Configuration",
            "7. Save Configuration"
        ]
        
        for step in steps:
            tk.Label(dlg, text=step, font=("Segoe UI", 11), fg=TEXT_PRIMARY, bg=BG_DARK).pack(anchor="w", padx=100, pady=2)
            
        btn_frame = tk.Frame(dlg, bg=BG_DARK)
        btn_frame.pack(fill="x", pady=20)
        
        def complete_setup():
            self.config.first_run = False
            save_config()
            dlg.destroy()
            self._on_settings() # Open settings for them to configure
            
        tk.Button(btn_frame, text="BEGIN SETUP", font=("Segoe UI", 11, "bold"),
                  bg=ACCENT_GREEN, fg="white", command=complete_setup, relief="flat", width=20).pack(pady=10)

    def _build_styles(self):
        """Configure ttk styles for dark theme."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background=BG_DARK)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("Panel.TFrame", background=BG_PANEL)

        style.configure("Title.TLabel",
                        background=BG_DARK, foreground=ACCENT_CYAN,
                        font=("Segoe UI", 18, "bold"))
        style.configure("Header.TLabel",
                        background=BG_CARD, foreground=TEXT_PRIMARY,
                        font=("Segoe UI", 11, "bold"))
        style.configure("Status.TLabel",
                        background=BG_CARD, foreground=TEXT_SECONDARY,
                        font=("Segoe UI", 10))
        style.configure("Value.TLabel",
                        background=BG_CARD, foreground=ACCENT_CYAN,
                        font=("Consolas", 11, "bold"))
        style.configure("Debug.TLabel",
                        background=BG_PANEL, foreground=TEXT_SECONDARY,
                        font=("Consolas", 9))
        style.configure("DebugVal.TLabel",
                        background=BG_PANEL, foreground=ACCENT_GREEN,
                        font=("Consolas", 9, "bold"))

    def _build_ui(self):
        """Build the main UI layout."""
        # ─── Title Bar ───
        title_frame = tk.Frame(self.root, bg=BG_DARK, height=60)
        title_frame.pack(fill="x", padx=15, pady=(10, 5))
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="⚡ AI HAND GESTURE CONTROLLER",
                 font=("Segoe UI", 20, "bold"), fg=ACCENT_CYAN,
                 bg=BG_DARK).pack(side="left", padx=5)

        tk.Label(title_frame, text="for Asphalt 8",
                 font=("Segoe UI", 14), fg=TEXT_MUTED,
                 bg=BG_DARK).pack(side="left", padx=(0, 20))

        # Mode indicator
        self._mode_label = tk.Label(title_frame,
                                    text="● TEST MODE" if self.config.test_mode else "● LIVE MODE",
                                    font=("Segoe UI", 11, "bold"),
                                    fg=STATUS_WARN if self.config.test_mode else STATUS_ON,
                                    bg=BG_DARK)
        self._mode_label.pack(side="right", padx=10)

        # macOS Development warning
        import platform
        if platform.system() != "Windows":
            warning_frame = tk.Frame(self.root, bg=BG_CARD)
            warning_frame.pack(fill="x", padx=15, pady=(0, 10))
            tk.Label(warning_frame, text="DEVELOPMENT MODE: Windows live game control is available only in the Windows build.",
                     font=("Segoe UI", 10), fg=ACCENT_ORANGE, bg=BG_CARD).pack(pady=5)

        # ─── Main Content ───
        content = tk.Frame(self.root, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=15, pady=5)

        # Left: Camera + Steering indicator
        left_panel = tk.Frame(content, bg=BG_DARK)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Camera preview
        cam_frame = tk.Frame(left_panel, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                            highlightthickness=1)
        cam_frame.pack(fill="both", expand=True)

        self._camera_canvas = tk.Canvas(cam_frame, bg="#000000",
                                        highlightthickness=0)
        self._camera_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # Steering indicator bar
        steer_frame = tk.Frame(left_panel, bg=BG_CARD, height=50,
                              highlightbackground=BORDER_COLOR, highlightthickness=1)
        steer_frame.pack(fill="x", pady=(5, 0))
        steer_frame.pack_propagate(False)

        self._steering_canvas = tk.Canvas(steer_frame, bg=BG_CARD, height=45,
                                          highlightthickness=0)
        self._steering_canvas.pack(fill="x", padx=5, pady=2)

        # Right panel: Status + Controls
        right_panel = tk.Frame(content, bg=BG_DARK, width=320)
        right_panel.pack(side="right", fill="y", padx=(8, 0))
        right_panel.pack_propagate(False)

        # Status card
        self._build_status_card(right_panel)

        # Control buttons
        self._build_control_buttons(right_panel)

        # ─── Bottom: Debug Panel ───
        self._debug_frame = tk.Frame(self.root, bg=BG_PANEL, height=140)
        self._debug_frame.pack(fill="x", padx=15, pady=(5, 10))

        if self.config.debug_mode:
            self._build_debug_panel()
            self._debug_frame.pack_propagate(False)
        else:
            self._debug_frame.pack_forget()

    def _build_status_card(self, parent):
        """Build the status information card."""
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                       highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="STATUS", font=("Segoe UI", 11, "bold"),
                 fg=TEXT_PRIMARY, bg=BG_CARD).pack(anchor="w", padx=12, pady=(10, 5))

        # Status rows
        self._status_vars = {}
        status_items = [
            ("Camera", "INITIALIZING", STATUS_WARN),
            ("Hand", "NOT DETECTED", STATUS_OFF),
            ("FPS", "0", TEXT_SECONDARY),
            ("Gesture", "NONE", TEXT_SECONDARY),
            ("Steering", "CENTER", ACCENT_CYAN),
            ("Brake", "OFF", TEXT_SECONDARY),
            ("Nitro", "READY", TEXT_SECONDARY),
            ("Controller", "OFF", STATUS_OFF),
        ]

        for label, default, color in status_items:
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", padx=12, pady=2)

            tk.Label(row, text=f"{label}:", font=("Segoe UI", 10),
                     fg=TEXT_MUTED, bg=BG_CARD, width=12, anchor="w").pack(side="left")

            var = tk.StringVar(value=default)
            lbl = tk.Label(row, textvariable=var, font=("Consolas", 10, "bold"),
                          fg=color, bg=BG_CARD, anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self._status_vars[label] = (var, lbl)

        tk.Frame(card, bg=BORDER_COLOR, height=1).pack(fill="x", padx=12, pady=8)

    def _build_control_buttons(self, parent):
        """Build control buttons."""
        btn_frame = tk.Frame(parent, bg=BG_DARK)
        btn_frame.pack(fill="x", pady=5)

        # Start/Stop Controller
        self._start_btn = self._make_button(
            btn_frame, "▶  START CONTROLLER", ACCENT_GREEN, self._on_start)
        self._start_btn.pack(fill="x", pady=3)

        self._stop_btn = self._make_button(
            btn_frame, "⏹  STOP CONTROLLER", ACCENT_ORANGE, self._on_stop)
        self._stop_btn.pack(fill="x", pady=3)

        # Calibration
        self._cal_btn = self._make_button(
            btn_frame, "🎯  CALIBRATION", ACCENT_BLUE, self._on_calibration)
        self._cal_btn.pack(fill="x", pady=3)

        # Settings
        self._settings_btn = self._make_button(
            btn_frame, "⚙  SETTINGS", ACCENT_PURPLE, self._on_settings)
        self._settings_btn.pack(fill="x", pady=3)

        # Test/Live mode toggle
        self._mode_btn = self._make_button(
            btn_frame,
            "🧪  SWITCH TO LIVE MODE" if self.config.test_mode else "🧪  SWITCH TO TEST MODE",
            STATUS_WARN, self._on_toggle_mode)
        self._mode_btn.pack(fill="x", pady=3)

        # Debug toggle
        self._debug_btn = self._make_button(
            btn_frame, "🐛  TOGGLE DEBUG", TEXT_MUTED, self._on_toggle_debug)
        self._debug_btn.pack(fill="x", pady=3)

        # Spacer
        tk.Frame(btn_frame, bg=BG_DARK, height=10).pack(fill="x")

        # Emergency Stop
        self._emergency_btn = tk.Button(
            btn_frame, text="🛑  EMERGENCY STOP", font=("Segoe UI", 12, "bold"),
            fg="white", bg="#dc2626", activebackground="#b91c1c",
            activeforeground="white", relief="flat", cursor="hand2",
            height=2, command=self._on_emergency_stop)
        self._emergency_btn.pack(fill="x", pady=3)

    def _make_button(self, parent, text, color, command):
        """Create a styled dark button."""
        btn = tk.Button(
            parent, text=text, font=("Segoe UI", 10, "bold"),
            fg=color, bg=BG_CARD, activebackground=BG_CARD_HOVER,
            activeforeground=color, relief="flat", cursor="hand2",
            height=1, command=command,
            highlightbackground=BORDER_COLOR, highlightthickness=1)
        return btn

    def _build_debug_panel(self):
        """Build the debug information panel."""
        # Clear existing
        for w in self._debug_frame.winfo_children():
            w.destroy()

        tk.Label(self._debug_frame, text="DEBUG PANEL",
                 font=("Segoe UI", 10, "bold"), fg=ACCENT_PURPLE,
                 bg=BG_PANEL).pack(anchor="w", padx=10, pady=(5, 3))

        cols_frame = tk.Frame(self._debug_frame, bg=BG_PANEL)
        cols_frame.pack(fill="both", expand=True, padx=10)

        self._debug_vars = {}

        debug_items = [
            # Column 1
            [("Hand Detected", "NO"), ("Index X", "0.000"), ("Index Y", "0.000"),
             ("Raised Fingers", "0"), ("Pinch", "FALSE")],
            # Column 2
            [("Current Gesture", "NONE"), ("Steering Zone", "CENTER"),
             ("Smoothed X", "0.500"), ("Velocity", "0.000"), ("Hand Open", "0.000")],
            # Column 3
            [("LEFT Key", "RELEASED"), ("RIGHT Key", "RELEASED"),
             ("DOWN Key", "RELEASED"), ("SPACE", "READY"), ("FPS", "0.0")],
        ]

        for col_idx, col_items in enumerate(debug_items):
            col = tk.Frame(cols_frame, bg=BG_PANEL)
            col.pack(side="left", fill="both", expand=True, padx=5)

            for label, default in col_items:
                row = tk.Frame(col, bg=BG_PANEL)
                row.pack(fill="x", pady=1)

                tk.Label(row, text=f"{label}:", font=("Consolas", 9),
                         fg=TEXT_MUTED, bg=BG_PANEL, anchor="w",
                         width=16).pack(side="left")

                var = tk.StringVar(value=default)
                tk.Label(row, textvariable=var, font=("Consolas", 9, "bold"),
                         fg=ACCENT_GREEN, bg=BG_PANEL, anchor="w").pack(side="left")
                self._debug_vars[label] = var

    def _bind_events(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<Escape>", lambda e: self._on_emergency_stop())
        self.root.bind("<F12>", lambda e: self._on_emergency_stop())
        self.root.bind("<F5>", lambda e: self._on_start())
        self.root.bind("<F6>", lambda e: self._on_stop())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════════════════════════════════
    # Processing Loop
    # ═══════════════════════════════════════════

    def _schedule_update(self):
        """Schedule the next processing update."""
        try:
            self._process_frame()
        except Exception as e:
            logger.error(f"Error in processing frame: {e}", exc_info=True)
        self.root.after(self.config.ui_update_interval, self._schedule_update)

    def _process_frame(self):
        """Main processing pipeline: Camera → Hand → Gesture → Steering → Keyboard."""
        frame = self.camera.get_frame()
        if frame is None:
            self._update_status("Camera", "NO SIGNAL", STATUS_OFF)
            return

        self._update_status("Camera", "ACTIVE", STATUS_ON)
        self._update_status("FPS", str(self.camera.fps), TEXT_SECONDARY)

        # Hand tracking
        hand_data = self.hand_tracker.process_frame(frame)
        self._last_hand_data = hand_data

        if hand_data.is_detected:
            self._hand_lost_time = None
            self._update_status("Hand", "● DETECTED", STATUS_ON)

            # Process landmarks
            metrics = self.landmark_processor.process(hand_data)
            self._last_metrics = metrics

            # Detect gestures
            gestures = self.gesture_detector.detect_all(metrics)
            self._last_gestures = gestures

            # Update gesture states (stability/edge detection)
            self.gesture_states.update(
                fist_detected=gestures["fist"],
                two_fingers_detected=gestures["two_fingers"],
                open_palm_detected=gestures["open_palm"],
            )

            current_gesture = self.gesture_states.current_gesture

            # Steering
            if current_gesture == GestureType.STEERING:
                zone, smoothed_x = self.steering.update(metrics["smoothed_x"])
                self._current_zone = zone
            else:
                self._current_zone = "center"

            # Apply game controls
            if self._controller_active:
                self._apply_controls(current_gesture)

            # Update status display
            gesture_name = current_gesture.name
            self._update_status("Gesture", gesture_name, ACCENT_CYAN)
            self._update_status("Steering", self._current_zone.upper(), ACCENT_CYAN)

            brake_on = self.gesture_states.fist.is_active
            self._update_status("Brake", "ON" if brake_on else "OFF",
                              ACCENT_RED if brake_on else TEXT_SECONDARY)

            nitro_ready = not self.gesture_states.two_fingers.is_active
            self._update_status("Nitro", "ACTIVE" if not nitro_ready else "READY",
                              ACCENT_ORANGE if not nitro_ready else TEXT_SECONDARY)

            # Draw landmarks on frame
            frame = self.hand_tracker.draw_landmarks(frame, hand_data)

        else:
            # Hand lost
            self._update_status("Hand", "NOT DETECTED", STATUS_OFF)
            self._update_status("Gesture", "NONE", TEXT_MUTED)
            self._update_status("Steering", "---", TEXT_MUTED)

            if self._hand_lost_time is None:
                self._hand_lost_time = time.time()
            elif time.time() - self._hand_lost_time > self.config.safety.hand_lost_timeout:
                if self._controller_active:
                    self.keyboard.release_all()
                    self._current_zone = "center"

        # Draw HUD on frame
        frame = self._draw_hud(frame)

        # Display frame
        self._display_frame(frame)

        # Draw steering indicator
        self._draw_steering_bar()

        # Update debug panel
        if self.config.debug_mode and self._debug_vars:
            self._update_debug()

    def _apply_controls(self, gesture: GestureType):
        """Apply the current gesture as keyboard controls."""
        cfg = self.config.controls

        # Safety: check game window if enabled
        if self.config.safety.only_control_when_game_active:
            if not is_game_window_active(self.config.safety.game_window_title, self.config.safety.game_process_name):
                self.keyboard.release_all()
                self._update_status("Controller", "GAME NOT ACTIVE", STATUS_WARN)
                return
            else:
                self._update_status("Controller", "● ACTIVE", STATUS_ON)

        # Steering
        if gesture == GestureType.STEERING:
            if self._current_zone == "left":
                self.keyboard.key_up(cfg.right_key)
                self.keyboard.key_down(cfg.left_key)
            elif self._current_zone == "right":
                self.keyboard.key_up(cfg.left_key)
                self.keyboard.key_down(cfg.right_key)
            else:  # center
                self.keyboard.key_up(cfg.left_key)
                self.keyboard.key_up(cfg.right_key)

            # Release brake when steering
            self.keyboard.key_up(cfg.brake_key)

        # Brake (fist)
        elif gesture == GestureType.FIST:
            self.keyboard.key_up(cfg.left_key)
            self.keyboard.key_up(cfg.right_key)
            self.keyboard.key_down(cfg.brake_key)

        # Nitro (two fingers) - edge triggered
        elif gesture == GestureType.TWO_FINGERS:
            if self.gesture_states.two_fingers.just_activated:
                self.keyboard.key_down(cfg.nitro_key)
                self.keyboard.key_up(cfg.nitro_key)
                logger.info("NITRO activated")

        # Open palm - release everything
        elif gesture == GestureType.OPEN_PALM:
            self.keyboard.key_up(cfg.left_key)
            self.keyboard.key_up(cfg.right_key)
            self.keyboard.key_up(cfg.brake_key)

    def _draw_hud(self, frame: np.ndarray) -> np.ndarray:
        """Draw HUD overlay on the camera frame."""
        h, w = frame.shape[:2]

        # Semi-transparent overlay for text background
        overlay = frame.copy()

        # Status bar at top
        cv2.rectangle(overlay, (0, 0), (w, 35), (10, 14, 23), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # FPS
        cv2.putText(frame, f"FPS: {self.camera.fps}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 255), 1, cv2.LINE_AA)

        # Hand status
        if self._last_hand_data.is_detected:
            cv2.putText(frame, "HAND: DETECTED", (w - 220, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (16, 185, 129), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, "HAND: NOT DETECTED", (w - 250, 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (239, 68, 68), 1, cv2.LINE_AA)

        # Controller status
        status = "ACTIVE" if self._controller_active else "OFF"
        color = (16, 185, 129) if self._controller_active else (239, 68, 68)
        cv2.putText(frame, f"CTRL: {status}", (w // 2 - 50, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1, cv2.LINE_AA)

        # Steering zone visualization
        if self._last_hand_data.is_detected and self._last_metrics:
            sx = self._last_metrics.get("smoothed_x", 0.5)

            # Draw zone regions
            cl = int(self.config.steering.center_left * w)
            cr = int(self.config.steering.center_right * w)

            cv2.line(frame, (cl, 40), (cl, h - 10), (100, 100, 100), 1, cv2.LINE_AA)
            cv2.line(frame, (cr, 40), (cr, h - 10), (100, 100, 100), 1, cv2.LINE_AA)

            # Current zone label
            zone_text = self._current_zone.upper()
            zone_color = (0, 212, 255) if self._current_zone == "center" else \
                         (59, 130, 246) if self._current_zone == "left" else (245, 158, 11)
            cv2.putText(frame, zone_text, (w // 2 - 40, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, zone_color, 2, cv2.LINE_AA)

        # Mode indicator
        mode = "TEST" if self.config.test_mode else "LIVE"
        mode_color = (245, 158, 11) if self.config.test_mode else (16, 185, 129)
        cv2.putText(frame, mode, (10, h - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, mode_color, 1, cv2.LINE_AA)

        return frame

    def _display_frame(self, frame: np.ndarray):
        """Convert OpenCV frame to Tkinter image and display."""
        canvas = self._camera_canvas
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        # Resize to fit canvas
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        fh, fw = frame_rgb.shape[:2]
        scale = min(cw / fw, ch / fh)
        new_w = int(fw * scale)
        new_h = int(fh * scale)
        if new_w > 0 and new_h > 0:
            resized = cv2.resize(frame_rgb, (new_w, new_h))
            img = Image.fromarray(resized)
            self._photo = ImageTk.PhotoImage(img)
            canvas.delete("all")
            x_offset = (cw - new_w) // 2
            y_offset = (ch - new_h) // 2
            canvas.create_image(x_offset, y_offset, anchor="nw", image=self._photo)

    def _draw_steering_bar(self):
        """Draw the horizontal steering indicator bar."""
        canvas = self._steering_canvas
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1:
            return

        canvas.delete("all")

        y_mid = h // 2
        bar_h = 14
        margin = 30

        # Zone boundaries
        cl = self.config.steering.center_left
        cr = self.config.steering.center_right

        cl_px = int(margin + cl * (w - 2 * margin))
        cr_px = int(margin + cr * (w - 2 * margin))

        # Left zone
        canvas.create_rectangle(margin, y_mid - bar_h // 2,
                               cl_px, y_mid + bar_h // 2,
                               fill="#1e3a5f", outline="")
        # Center zone
        canvas.create_rectangle(cl_px, y_mid - bar_h // 2,
                               cr_px, y_mid + bar_h // 2,
                               fill="#1a3d2e", outline="")
        # Right zone
        canvas.create_rectangle(cr_px, y_mid - bar_h // 2,
                               w - margin, y_mid + bar_h // 2,
                               fill="#3d2e1a", outline="")

        # Labels
        canvas.create_text(margin + (cl_px - margin) // 2, y_mid - bar_h,
                          text="LEFT", fill=ACCENT_BLUE, font=("Consolas", 8, "bold"))
        canvas.create_text((cl_px + cr_px) // 2, y_mid - bar_h,
                          text="CENTER", fill=ACCENT_GREEN, font=("Consolas", 8, "bold"))
        canvas.create_text(cr_px + (w - margin - cr_px) // 2, y_mid - bar_h,
                          text="RIGHT", fill=ACCENT_ORANGE, font=("Consolas", 8, "bold"))

        # Current position dot
        if self._last_metrics and self._last_metrics.get("is_detected"):
            sx = self._last_metrics.get("smoothed_x", 0.5)
            dot_x = int(margin + sx * (w - 2 * margin))
            dot_color = ACCENT_CYAN
            if self._current_zone == "left":
                dot_color = ACCENT_BLUE
            elif self._current_zone == "right":
                dot_color = ACCENT_ORANGE

            canvas.create_oval(dot_x - 8, y_mid - 8, dot_x + 8, y_mid + 8,
                             fill=dot_color, outline="white", width=2)

        # Zone boundary markers
        canvas.create_line(cl_px, y_mid - bar_h, cl_px, y_mid + bar_h,
                          fill=TEXT_MUTED, width=1, dash=(3, 3))
        canvas.create_line(cr_px, y_mid - bar_h, cr_px, y_mid + bar_h,
                          fill=TEXT_MUTED, width=1, dash=(3, 3))

    def _update_status(self, key: str, value: str, color: str):
        """Update a status variable and its color."""
        if key in self._status_vars:
            var, lbl = self._status_vars[key]
            var.set(value)
            lbl.configure(fg=color)

    def _update_debug(self):
        """Update debug panel variables."""
        m = self._last_metrics
        ks = self.keyboard.get_state_dict()

        updates = {
            "Hand Detected": "YES" if m.get("is_detected") else "NO",
            "Index X": f"{m.get('raw_x', 0):.3f}",
            "Index Y": f"{m.get('raw_y', 0):.3f}",
            "Raised Fingers": str(m.get("raised_count", 0)),
            "Pinch": "TRUE" if self._last_gestures.get("pinch") else "FALSE",
            "Current Gesture": self.gesture_states.current_gesture.name,
            "Steering Zone": self._current_zone.upper(),
            "Smoothed X": f"{m.get('smoothed_x', 0.5):.3f}",
            "Velocity": f"{m.get('speed', 0):.3f}",
            "Hand Open": f"{m.get('hand_openness', 0):.3f}",
            "LEFT Key": ks.get("left", "RELEASED"),
            "RIGHT Key": ks.get("right", "RELEASED"),
            "DOWN Key": ks.get("down", "RELEASED"),
            "SPACE": ks.get("space", "RELEASED"),
            "FPS": str(self.camera.fps),
        }

        for key, val in updates.items():
            if key in self._debug_vars:
                self._debug_vars[key].set(val)

    # ═══════════════════════════════════════════
    # Button Handlers
    # ═══════════════════════════════════════════

    def _on_start(self):
        """Start the controller."""
        self._controller_active = True
        self.keyboard.enable()
        self._update_status("Controller", "● ACTIVE", STATUS_ON)
        logger.info("Controller STARTED")

    def _on_stop(self):
        """Stop the controller."""
        self._controller_active = False
        self.keyboard.disable()
        self.steering.reset()
        self.gesture_states.reset()
        self._current_zone = "center"
        self._update_status("Controller", "OFF", STATUS_OFF)
        logger.info("Controller STOPPED")

    def _on_emergency_stop(self):
        """Emergency stop - release everything immediately."""
        self._controller_active = False
        self.keyboard.release_all()
        self.keyboard.disable()
        self.steering.reset()
        self.gesture_states.reset()
        self._current_zone = "center"
        self._update_status("Controller", "⚠ EMERGENCY STOP", ACCENT_RED)
        logger.warning("EMERGENCY STOP activated")

    def _on_calibration(self):
        """Open calibration window."""
        CalibrationWindow(self.root, self)

    def _on_settings(self):
        """Open settings window."""
        SettingsWindow(self.root, self)

    def _on_toggle_mode(self):
        """Toggle between test and live mode with custom confirmation."""
        if self.config.test_mode:
            # Custom confirmation dialog
            dlg = tk.Toplevel(self.root)
            dlg.title("WARNING")
            dlg.geometry("400x200")
            dlg.configure(bg=BG_DARK)
            dlg.transient(self.root)
            dlg.grab_set()
            
            # Center the dialog
            dlg.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() - 400) // 2
            y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
            dlg.geometry(f"+{x}+{y}")
            
            tk.Label(dlg, text="WARNING", font=("Segoe UI", 16, "bold"), 
                     fg=ACCENT_RED, bg=BG_DARK).pack(pady=(20, 10))
            tk.Label(dlg, text="Live Control will send keyboard input\nto the active Windows application.",
                     font=("Segoe UI", 11), fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=5)
            
            btn_frame = tk.Frame(dlg, bg=BG_DARK)
            btn_frame.pack(fill="x", pady=20)
            
            def enable():
                self._enable_live_mode()
                dlg.destroy()
                
            tk.Button(btn_frame, text="CANCEL", font=("Segoe UI", 10, "bold"),
                      bg=BG_CARD, fg=TEXT_MUTED, command=dlg.destroy, relief="flat", width=12).pack(side="left", padx=20, expand=True)
            tk.Button(btn_frame, text="ENABLE LIVE CONTROL", font=("Segoe UI", 10, "bold"),
                      bg=ACCENT_RED, fg="white", command=enable, relief="flat", width=22).pack(side="right", padx=20, expand=True)
        else:
            # Switch back to test mode immediately
            self.config.test_mode = True
            self._update_mode_ui()
            logger.info("Mode switched to TEST")

    def _enable_live_mode(self):
        self.config.test_mode = False
        self._update_mode_ui()
        logger.info("Mode switched to LIVE")

    def _update_mode_ui(self):
        self.keyboard.test_mode = self.config.test_mode
        save_config()
        if self.config.test_mode:
            self._mode_label.config(text="● TEST MODE", fg=STATUS_WARN)
            self._mode_btn.config(text="🧪  SWITCH TO LIVE MODE")
        else:
            self._mode_label.config(text="● LIVE MODE", fg=STATUS_ON)
            self._mode_btn.config(text="🧪  SWITCH TO TEST MODE")

    def _on_toggle_debug(self):
        """Toggle debug panel visibility."""
        self.config.debug_mode = not self.config.debug_mode

        if self.config.debug_mode:
            self._debug_frame.pack(fill="x", padx=15, pady=(5, 10))
            self._debug_frame.pack_propagate(False)
            self._build_debug_panel()
        else:
            self._debug_frame.pack_forget()

    def _on_close(self):
        """Clean shutdown."""
        logger.info("Application closing...")
        self._on_emergency_stop()
        self.camera.stop()
        self.hand_tracker.release()
        save_config()
        self.root.destroy()
        logger.info("Application closed")

    def run(self):
        """Start the main event loop."""
        logger.info("Starting main event loop")
        self.root.mainloop()


class CalibrationWindow:
    """Calibration wizard window."""

    def __init__(self, parent, main_window: MainWindow):
        self.main = main_window
        self.win = tk.Toplevel(parent)
        self.win.title("Calibration")
        self.win.configure(bg=BG_DARK)
        self.win.geometry("500x600")
        self.win.transient(parent)
        self.win.grab_set()

        self._step = 0
        self._samples = []
        self._sampling = False

        self._build_ui()

    def _build_ui(self):
        tk.Label(self.win, text="🎯 CALIBRATION",
                 font=("Segoe UI", 18, "bold"), fg=ACCENT_CYAN,
                 bg=BG_DARK).pack(pady=(20, 10))

        tk.Label(self.win,
                 text="Follow the steps below to calibrate\nyour hand position for steering.",
                 font=("Segoe UI", 11), fg=TEXT_SECONDARY,
                 bg=BG_DARK, justify="center").pack(pady=(0, 20))

        # Steps
        steps = [
            ("STEP 1", "Place your hand in the CENTER position", "CALIBRATE CENTER"),
            ("STEP 2", "Move your hand to the LEFT position", "CALIBRATE LEFT"),
            ("STEP 3", "Move your hand to the RIGHT position", "CALIBRATE RIGHT"),
        ]

        self._step_frames = []
        self._step_labels = []

        for i, (title, desc, btn_text) in enumerate(steps):
            frame = tk.Frame(self.win, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                           highlightthickness=1)
            frame.pack(fill="x", padx=30, pady=5)

            tk.Label(frame, text=title, font=("Segoe UI", 11, "bold"),
                     fg=ACCENT_CYAN, bg=BG_CARD).pack(anchor="w", padx=15, pady=(10, 2))

            tk.Label(frame, text=desc, font=("Segoe UI", 10),
                     fg=TEXT_SECONDARY, bg=BG_CARD).pack(anchor="w", padx=15, pady=(0, 5))

            status_var = tk.StringVar(value="Not calibrated")
            status_lbl = tk.Label(frame, textvariable=status_var,
                                  font=("Consolas", 9, "bold"),
                                  fg=TEXT_MUTED, bg=BG_CARD)
            status_lbl.pack(anchor="w", padx=15)

            btn = tk.Button(frame, text=btn_text, font=("Segoe UI", 10, "bold"),
                           fg=ACCENT_CYAN, bg=BG_PANEL, relief="flat",
                           cursor="hand2",
                           command=lambda idx=i: self._calibrate_step(idx))
            btn.pack(fill="x", padx=15, pady=(5, 10))

            self._step_frames.append(frame)
            self._step_labels.append((status_var, status_lbl))

        # Save/Close
        btn_row = tk.Frame(self.win, bg=BG_DARK)
        btn_row.pack(fill="x", padx=30, pady=20)

        tk.Button(btn_row, text="SAVE & CLOSE", font=("Segoe UI", 11, "bold"),
                  fg=ACCENT_GREEN, bg=BG_CARD, relief="flat", cursor="hand2",
                  command=self._save_and_close).pack(side="right", padx=5)

        tk.Button(btn_row, text="CANCEL", font=("Segoe UI", 11),
                  fg=TEXT_MUTED, bg=BG_CARD, relief="flat", cursor="hand2",
                  command=self.win.destroy).pack(side="right", padx=5)

    def _calibrate_step(self, step_idx: int):
        """Capture current hand position for calibration step."""
        metrics = self.main._last_metrics
        if not metrics or not metrics.get("is_detected"):
            messagebox.showwarning("No Hand Detected",
                                   "Please place your hand in view of the camera.",
                                   parent=self.win)
            return

        x = metrics["smoothed_x"]
        var, lbl = self._step_labels[step_idx]

        if step_idx == 0:  # Center
            self.main.steering.calibrate_center(x)
            var.set(f"✓ Calibrated: {x:.3f}")
        elif step_idx == 1:  # Left
            self.main.steering.calibrate_left(x)
            var.set(f"✓ Calibrated: {x:.3f}")
        elif step_idx == 2:  # Right
            self.main.steering.calibrate_right(x)
            var.set(f"✓ Calibrated: {x:.3f}")

        lbl.configure(fg=ACCENT_GREEN)
        logger.info(f"Calibration step {step_idx + 1} completed: x={x:.3f}")

    def _save_and_close(self):
        """Save calibration and close."""
        # Update config
        self.main.config.steering = self.main.steering.config
        save_config()
        logger.info("Calibration saved")
        self.win.destroy()


class SettingsWindow:
    """Settings window for all configuration options."""

    def __init__(self, parent, main_window: MainWindow):
        self.main = main_window
        self.config = main_window.config
        self.win = tk.Toplevel(parent)
        self.win.title("Settings")
        self.win.configure(bg=BG_DARK)
        self.win.geometry("600x700")
        self.win.transient(parent)
        self.win.grab_set()

        self._vars = {}
        self._build_ui()

    def _build_ui(self):
        tk.Label(self.win, text="⚙ SETTINGS",
                 font=("Segoe UI", 18, "bold"), fg=ACCENT_PURPLE,
                 bg=BG_DARK).pack(pady=(15, 10))

        # Scrollable frame
        canvas = tk.Canvas(self.win, bg=BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.win, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_DARK)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=15)
        scrollbar.pack(side="right", fill="y")

        # ─── Camera Settings ───
        self._add_section(scroll_frame, "📷 Camera")
        self._add_entry(scroll_frame, "Camera Device", "camera.device_index",
                        str(self.config.camera.device_index))
        self._add_entry(scroll_frame, "Resolution Width", "camera.width",
                        str(self.config.camera.width))
        self._add_entry(scroll_frame, "Resolution Height", "camera.height",
                        str(self.config.camera.height))
        self._add_entry(scroll_frame, "FPS", "camera.fps",
                        str(self.config.camera.fps))

        # ─── Tracking ───
        self._add_section(scroll_frame, "🖐 Tracking")
        self._add_slider(scroll_frame, "Detection Confidence", "tracking.det_conf",
                         0.1, 1.0, self.config.tracking.min_detection_confidence)
        self._add_slider(scroll_frame, "Tracking Confidence", "tracking.track_conf",
                         0.1, 1.0, self.config.tracking.min_tracking_confidence)
        self._add_slider(scroll_frame, "Smoothing Factor", "tracking.smoothing",
                         0.05, 1.0, self.config.tracking.smoothing_factor)
        self._add_entry(scroll_frame, "Gesture Stability Frames", "tracking.stability",
                        str(self.config.tracking.gesture_stability_frames))

        # ─── Steering ───
        self._add_section(scroll_frame, "🎮 Steering")
        self._add_slider(scroll_frame, "Sensitivity", "steering.sensitivity",
                         0.1, 3.0, self.config.steering.sensitivity)
        self._add_slider(scroll_frame, "Dead Zone", "steering.dead_zone",
                         0.0, 0.2, self.config.steering.dead_zone)
        self._add_slider(scroll_frame, "Hysteresis", "steering.hysteresis",
                         0.0, 0.1, self.config.steering.hysteresis)
        self._add_slider(scroll_frame, "Left Boundary", "steering.center_left",
                         0.1, 0.5, self.config.steering.center_left)
        self._add_slider(scroll_frame, "Right Boundary", "steering.center_right",
                         0.5, 0.9, self.config.steering.center_right)

        # ─── Controls ───
        self._add_section(scroll_frame, "⌨ Controls")
        self._add_entry(scroll_frame, "Left Key", "controls.left",
                        self.config.controls.left_key)
        self._add_entry(scroll_frame, "Right Key", "controls.right",
                        self.config.controls.right_key)
        self._add_entry(scroll_frame, "Brake Key", "controls.brake",
                        self.config.controls.brake_key)
        self._add_entry(scroll_frame, "Nitro Key", "controls.nitro",
                        self.config.controls.nitro_key)

        # ─── Safety ───
        self._add_section(scroll_frame, "🛡 Safety")
        self._add_checkbox(scroll_frame, "Only send input when game is active",
                          "safety.game_only", self.config.safety.only_control_when_game_active)
        self._add_entry(scroll_frame, "Game Window Title", "safety.game_title",
                        self.config.safety.game_window_title)
        self._add_slider(scroll_frame, "Hand Lost Timeout (s)", "safety.hand_timeout",
                         0.1, 3.0, self.config.safety.hand_lost_timeout)
        self._add_slider(scroll_frame, "Nitro Cooldown (s)", "safety.nitro_cd",
                         0.0, 3.0, self.config.safety.nitro_cooldown)

        # Save/Cancel buttons
        btn_frame = tk.Frame(self.win, bg=BG_DARK)
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="SAVE", font=("Segoe UI", 11, "bold"),
                  fg=ACCENT_GREEN, bg=BG_CARD, relief="flat", cursor="hand2",
                  command=self._save).pack(side="right", padx=5)

        tk.Button(btn_frame, text="CANCEL", font=("Segoe UI", 11),
                  fg=TEXT_MUTED, bg=BG_CARD, relief="flat", cursor="hand2",
                  command=self.win.destroy).pack(side="right", padx=5)

    def _add_section(self, parent, title):
        tk.Label(parent, text=title, font=("Segoe UI", 12, "bold"),
                 fg=ACCENT_CYAN, bg=BG_DARK).pack(anchor="w", padx=10, pady=(15, 5))
        tk.Frame(parent, bg=BORDER_COLOR, height=1).pack(fill="x", padx=10)

    def _add_entry(self, parent, label, key, default):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill="x", padx=15, pady=3)
        tk.Label(row, text=label, font=("Segoe UI", 10),
                 fg=TEXT_SECONDARY, bg=BG_DARK, width=24, anchor="w").pack(side="left")
        var = tk.StringVar(value=default)
        entry = tk.Entry(row, textvariable=var, font=("Consolas", 10),
                        fg=TEXT_PRIMARY, bg=BG_CARD, insertbackground=TEXT_PRIMARY,
                        relief="flat", width=20)
        entry.pack(side="left", padx=5)
        self._vars[key] = var

    def _add_slider(self, parent, label, key, min_val, max_val, default):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill="x", padx=15, pady=3)
        tk.Label(row, text=label, font=("Segoe UI", 10),
                 fg=TEXT_SECONDARY, bg=BG_DARK, width=24, anchor="w").pack(side="left")

        var = tk.DoubleVar(value=default)
        val_label = tk.Label(row, text=f"{default:.2f}", font=("Consolas", 9),
                            fg=ACCENT_CYAN, bg=BG_DARK, width=6)
        val_label.pack(side="right")

        scale = tk.Scale(row, from_=min_val, to=max_val, resolution=0.01,
                        orient="horizontal", variable=var,
                        bg=BG_DARK, fg=TEXT_PRIMARY, troughcolor=BG_CARD,
                        highlightthickness=0, showvalue=False, length=180,
                        command=lambda v, l=val_label: l.config(text=f"{float(v):.2f}"))
        scale.pack(side="left", padx=5)
        self._vars[key] = var

    def _add_checkbox(self, parent, label, key, default):
        var = tk.BooleanVar(value=default)
        cb = tk.Checkbutton(parent, text=label, variable=var,
                           font=("Segoe UI", 10), fg=TEXT_SECONDARY,
                           bg=BG_DARK, selectcolor=BG_CARD,
                           activebackground=BG_DARK, activeforeground=TEXT_PRIMARY)
        cb.pack(anchor="w", padx=15, pady=3)
        self._vars[key] = var

    def _save(self):
        """Save settings to config."""
        try:
            cfg = self.config

            # Camera
            if "camera.device_index" in self._vars:
                cfg.camera.device_index = int(self._vars["camera.device_index"].get())
            if "camera.width" in self._vars:
                cfg.camera.width = int(self._vars["camera.width"].get())
            if "camera.height" in self._vars:
                cfg.camera.height = int(self._vars["camera.height"].get())
            if "camera.fps" in self._vars:
                cfg.camera.fps = int(self._vars["camera.fps"].get())

            # Tracking
            if "tracking.det_conf" in self._vars:
                cfg.tracking.min_detection_confidence = float(self._vars["tracking.det_conf"].get())
            if "tracking.track_conf" in self._vars:
                cfg.tracking.min_tracking_confidence = float(self._vars["tracking.track_conf"].get())
            if "tracking.smoothing" in self._vars:
                cfg.tracking.smoothing_factor = float(self._vars["tracking.smoothing"].get())
            if "tracking.stability" in self._vars:
                cfg.tracking.gesture_stability_frames = int(self._vars["tracking.stability"].get())

            # Steering
            if "steering.sensitivity" in self._vars:
                cfg.steering.sensitivity = float(self._vars["steering.sensitivity"].get())
            if "steering.dead_zone" in self._vars:
                cfg.steering.dead_zone = float(self._vars["steering.dead_zone"].get())
            if "steering.hysteresis" in self._vars:
                cfg.steering.hysteresis = float(self._vars["steering.hysteresis"].get())
            if "steering.center_left" in self._vars:
                cfg.steering.center_left = float(self._vars["steering.center_left"].get())
            if "steering.center_right" in self._vars:
                cfg.steering.center_right = float(self._vars["steering.center_right"].get())

            # Controls
            if "controls.left" in self._vars:
                cfg.controls.left_key = self._vars["controls.left"].get()
            if "controls.right" in self._vars:
                cfg.controls.right_key = self._vars["controls.right"].get()
            if "controls.brake" in self._vars:
                cfg.controls.brake_key = self._vars["controls.brake"].get()
            if "controls.nitro" in self._vars:
                cfg.controls.nitro_key = self._vars["controls.nitro"].get()

            # Safety
            if "safety.game_only" in self._vars:
                cfg.safety.only_control_when_game_active = bool(self._vars["safety.game_only"].get())
            if "safety.game_title" in self._vars:
                cfg.safety.game_window_title = self._vars["safety.game_title"].get()
            if "safety.hand_timeout" in self._vars:
                cfg.safety.hand_lost_timeout = float(self._vars["safety.hand_timeout"].get())
            if "safety.nitro_cd" in self._vars:
                cfg.safety.nitro_cooldown = float(self._vars["safety.nitro_cd"].get())

            # Apply to components
            self.main.steering.update_config(cfg.steering)
            self.main.gesture_detector.update_config(cfg.gesture)
            self.main.gesture_states = GestureStateManager(
                stability_frames=cfg.tracking.gesture_stability_frames,
                nitro_cooldown=cfg.safety.nitro_cooldown,
            )

            save_config()
            logger.info("Settings saved")
            messagebox.showinfo("Settings", "Settings saved successfully!", parent=self.win)
            self.win.destroy()

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings:\n{e}", parent=self.win)
