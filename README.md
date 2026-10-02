# 🎮 AI Hand Gesture Controller for Asphalt 8

A real-time webcam-based hand gesture controller that allows you to control **Asphalt 8: Airborne** on your Windows laptop without using the physical keyboard.

The system detects your hand through the laptop webcam, interprets hand position and gestures, and generates **real OS-level keyboard inputs** that the game can receive.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange)

---

## 📋 Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Control Mappings](#control-mappings)
- [Calibration](#calibration)
- [Settings](#settings)
- [Architecture](#architecture)
- [Packaging as EXE](#packaging-as-exe)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

- **Real-time hand tracking** using MediaPipe (21 landmarks)
- **Gesture recognition**: Steering, Brake (fist), Nitro (two fingers), Neutral (open palm)
- **Smooth steering** with EMA smoothing, dead zone, and hysteresis
- **DirectInput keyboard output** (Windows) for game compatibility
- **Safety systems**: Emergency stop, hand-lost auto-release, game window detection
- **Dark futuristic UI** with live camera preview and debug panel
- **Calibration wizard** for personalized hand position mapping
- **Test mode** for safe testing without sending keyboard input
- **Configurable** settings saved to `config.json`

---

## 💻 Requirements

### Hardware
- Laptop/PC with webcam (built-in or USB)
- Windows 10/11 (for DirectInput game control)
- Asphalt 8: Airborne installed (Microsoft Store or Steam)

### Software
- **Python 3.11+** — [Download](https://www.python.org/downloads/)
- pip (included with Python)

---

## 🚀 Installation

### 1. Install Python

Download Python 3.11+ from [python.org](https://www.python.org/downloads/).

**Important**: Check "Add Python to PATH" during installation.

### 2. Create a Virtual Environment

```bash
# Navigate to the project folder
cd ai_gesture_controller

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Webcam Permissions

On Windows, go to **Settings → Privacy → Camera** and ensure camera access is enabled for Python.

---

## 🎬 Quick Start

### Test Mode (Recommended First)

```bash
python main.py --test
```

This runs the full application but does **not** send real keyboard input. Use this to verify hand tracking and gesture detection work correctly.

### Live Mode

```bash
python main.py --live
```

This sends **real keyboard input** to the active window. Make sure Asphalt 8 is running.

### With Debug Panel

```bash
python main.py --test --debug
```

### Game Workflow

1. Launch the controller: `python main.py`
2. Verify your hand is detected in the camera preview
3. Run **Calibration** (click the Calibration button)
4. Open **Asphalt 8** and start a race
5. Place your hand in front of the camera
6. Switch to **LIVE MODE** in the controller
7. Click **START CONTROLLER**
8. Drive with your hand! ✋

---

## 🕹 Control Mappings

| Gesture | Action | Default Key |
|---------|--------|-------------|
| Hand moves **LEFT** | Steer Left | ← (Left Arrow) |
| Hand moves **RIGHT** | Steer Right | → (Right Arrow) |
| Hand in **CENTER** | Go Straight | Release L/R |
| **Closed Fist** ✊ | Brake | ↓ (Down Arrow) |
| **Two Fingers** ✌ | Nitro Boost | Space |
| **Open Palm** 🖐 | Release All | Release all keys |

### Key Behavior

- Keys are properly **held** (not repeatedly pressed)
- Switching from LEFT → RIGHT properly releases LEFT first
- Nitro is **edge-triggered** (one press per gesture)
- Brake is **held** while fist is maintained

---

## 🎯 Calibration

The calibration wizard maps your hand's natural movement range to the steering zones.

1. Click **CALIBRATION** in the main window
2. **Step 1**: Hold your hand in the neutral/center position → Click "CALIBRATE CENTER"
3. **Step 2**: Move your hand to your comfortable left limit → Click "CALIBRATE LEFT"
4. **Step 3**: Move your hand to your comfortable right limit → Click "CALIBRATE RIGHT"
5. Click **SAVE & CLOSE**

Calibration values are saved to `config.json` and persist between sessions.

---

## ⚙ Settings

Accessible via the **SETTINGS** button. All settings are saved to `config.json`.

### Camera
| Setting | Default | Description |
|---------|---------|-------------|
| Camera Device | 0 | Webcam index (0 = default) |
| Resolution | 640×480 | Camera resolution |
| FPS | 30 | Target frame rate |

### Tracking
| Setting | Default | Description |
|---------|---------|-------------|
| Detection Confidence | 0.70 | Min confidence for initial detection |
| Tracking Confidence | 0.50 | Min confidence for frame-to-frame tracking |
| Smoothing Factor | 0.30 | EMA alpha (lower = smoother, more lag) |
| Gesture Stability Frames | 5 | Frames a gesture must be stable before triggering |

### Steering
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 1.0 | Steering sensitivity multiplier |
| Dead Zone | 0.05 | Minimum position change to register |
| Hysteresis | 0.03 | Extra margin to prevent zone flickering |
| Left Boundary | 0.40 | Normalized X where center→left transition occurs |
| Right Boundary | 0.60 | Normalized X where center→right transition occurs |

### Safety
| Setting | Default | Description |
|---------|---------|-------------|
| Only send when game active | OFF | Only send keys when Asphalt 8 is foreground |
| Game Window Title | "Asphalt 8" | Window title to match |
| Hand Lost Timeout | 0.5s | Release keys after hand lost for this long |
| Nitro Cooldown | 0.5s | Minimum time between nitro activations |

---

## 🏗 Architecture

```
ai_gesture_controller/
├── main.py                      # Entry point
├── config.py                    # Configuration management
├── config.json                  # Saved settings (auto-generated)
│
├── camera/
│   └── camera_manager.py        # Threaded webcam capture
│
├── vision/
│   ├── hand_tracker.py          # MediaPipe hand detection
│   └── landmark_processor.py    # Landmark smoothing & metrics
│
├── gestures/
│   ├── gesture_detector.py      # Gesture classification
│   ├── gesture_state.py         # State tracking & edge detection
│   └── steering_controller.py   # Steering zone mapping
│
├── input/
│   └── keyboard_controller.py   # OS-level key press/release
│
├── ui/
│   └── main_window.py           # Tkinter UI (main, calibration, settings)
│
├── utils/
│   ├── logger.py                # Logging
│   └── smoothing.py             # EMA, position, steering smoothers
│
├── logs/                        # Log files
├── profiles/                    # Saved profiles
├── requirements.txt
└── README.md
```

### Processing Pipeline

```
WEBCAM FRAME
    ↓
MEDIAPIPE HAND LANDMARKS (21 points)
    ↓
LANDMARK PROCESSOR (smoothing, metrics)
    ↓
GESTURE DETECTOR (fist, two-fingers, open palm)
    ↓
GESTURE STATE MANAGER (stability, edge detection)
    ↓
STEERING CONTROLLER (zone mapping, hysteresis)
    ↓
KEYBOARD CONTROLLER (key_down / key_up)
    ↓
ASPHALT 8 (receives DirectInput events)
```

---

## 📦 Windows Production Build

Development is done on macOS/Linux, but the final game control requires Windows. The build process is automated via GitHub Actions to ensure a clean, reliable Windows `.exe`.

### 🏭 Build Workflow

1. **MAC DEVELOPMENT** - Edit code and test using `--test` mode.
2. **GIT PUSH** - Push your changes to the `main` branch.
3. **GITHUB ACTIONS** - The `Windows Production Build` workflow triggers automatically.
4. **WINDOWS BUILD** - A clean Windows Server runner compiles the app with PyInstaller.
5. **DOWNLOAD ARTIFACT** - Download `AI-Gesture-Controller-Windows` from the GitHub Actions run.
6. **WINDOWS LAPTOP** - Extract the downloaded `.zip` on your Windows 10/11 gaming laptop.
7. **RUN EXE** - Double-click `AI-Gesture-Controller.exe`. No Python installation needed!
8. **CAMERA TEST** - Complete the First-Run Setup Wizard.
9. **CALIBRATION** - Run the Steering Calibration.
10. **ASPHALT 8** - Launch the game and bring it to the foreground.
11. **LIVE CONTROL** - Click "SWITCH TO LIVE MODE", confirm the warning, and drive!

### 🔧 Manual Build (Optional)

If you prefer building locally on a Windows machine:
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller AI-Gesture-Controller.spec --clean
```
The executable and required files will be placed in `dist/AI-Gesture-Controller/`.

---

## 🔧 Troubleshooting

### Camera not detected
- Check webcam permissions in Windows Settings
- Try a different camera index in Settings (0, 1, 2...)
- Close other applications using the camera

### Hand not detected
- Ensure good lighting
- Keep your hand 30-60cm from the camera
- Try lowering Detection Confidence in Settings
- Avoid complex backgrounds

### Steering is jittery
- Increase **Smoothing Factor** (0.3 → 0.5)
- Increase **Dead Zone** (0.05 → 0.10)
- Increase **Hysteresis** (0.03 → 0.06)
- Increase **Gesture Stability Frames** (5 → 8)

### Keys get stuck
- Press **F12** or **Escape** for Emergency Stop
- Click the **EMERGENCY STOP** button
- The app auto-releases all keys on:
  - Hand lost for >0.5s
  - Controller stop
  - Application close
  - Emergency stop

### Asphalt 8 doesn't respond to controls
- Make sure you're in **LIVE MODE** (not test mode)
- Make sure the **Controller is ACTIVE** (started)
- If "Only send when game active" is on, ensure Asphalt 8 is the foreground window
- Try running the controller as **Administrator** (right-click → Run as administrator)
- The game may need DirectInput: the controller uses scancodes for compatibility

### High CPU usage
- Lower camera FPS to 15-20
- Lower camera resolution to 320×240
- Increase UI update interval in config

---

## ⌨ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F5 | Start Controller |
| F6 | Stop Controller |
| F12 | Emergency Stop |
| Escape | Emergency Stop |

---

## ⚠ Safety Notes

- The controller starts in **TEST MODE** by default — no real keyboard input is sent
- Always verify hand tracking works in test mode before switching to live mode
- The **EMERGENCY STOP** (F12 / Escape / button) instantly releases all keys
- If the hand disappears for more than 0.5 seconds, all keys are automatically released
- Closing the application releases all held keys

---

## 📝 License

This project is for educational and personal use.

---

*Built with ❤️ using Python, OpenCV, MediaPipe, and Tkinter*
