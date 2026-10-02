"""
Keyboard Controller - Generates OS-level keyboard inputs with safe state management.

Uses platform-appropriate methods:
- Windows: ctypes SendInput (DirectInput compatible) with pyautogui fallback
- macOS: pyautogui (for development/testing)
"""

import platform
import time
from typing import Dict, Set, Optional

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from utils.logger import logger

SYSTEM = platform.system()

# --- Windows DirectInput Scancodes ---
# These are needed for games that use DirectInput instead of regular key events
SCAN_CODES = {
    "left": 0x4B,
    "right": 0x4D,
    "up": 0x48,
    "down": 0x50,
    "space": 0x39,
    "escape": 0x01,
    "f12": 0x58,
    "a": 0x1E,
    "d": 0x20,
    "w": 0x11,
    "s": 0x1F,
}

if SYSTEM == "Windows":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    # Input event constants
    INPUT_KEYBOARD = 1
    KEYEVENTF_SCANCODE = 0x0008
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_EXTENDEDKEY = 0x0001

    # Extended key scancodes (arrow keys, etc.)
    EXTENDED_KEYS = {0x48, 0x4B, 0x4D, 0x50}

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT),
        ]

    def _send_key_event(scan_code: int, key_up: bool = False):
        """Send a DirectInput key event on Windows."""
        flags = KEYEVENTF_SCANCODE
        if scan_code in EXTENDED_KEYS:
            flags |= KEYEVENTF_EXTENDEDKEY
        if key_up:
            flags |= KEYEVENTF_KEYUP

        ki = KEYBDINPUT(
            wVk=0,
            wScan=scan_code,
            dwFlags=flags,
            time=0,
            dwExtraInfo=ctypes.pointer(ctypes.c_ulong(0)),
        )
        inp = INPUT(type=INPUT_KEYBOARD)
        inp._input.ki = ki
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

else:
    # macOS/Linux fallback using pyautogui
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

        # Key name mapping for pyautogui
        _PYAUTOGUI_KEYS = {
            "left": "left",
            "right": "right",
            "up": "up",
            "down": "down",
            "space": "space",
            "escape": "escape",
            "f12": "f12",
            "a": "a",
            "d": "d",
            "w": "w",
            "s": "s",
        }
    except ImportError:
        logger.warning("pyautogui not available - keyboard control disabled on this platform")
        pyautogui = None

    def _send_key_event(scan_code: int, key_up: bool = False):
        """Fallback key event using pyautogui."""
        if pyautogui is None:
            return
        # Find key name from scan code
        key_name = None
        for name, code in SCAN_CODES.items():
            if code == scan_code:
                key_name = _PYAUTOGUI_KEYS.get(name, name)
                break
        if key_name:
            if key_up:
                pyautogui.keyUp(key_name)
            else:
                pyautogui.keyDown(key_name)


class KeyboardController:
    """
    Manages keyboard key states. Ensures:
    - Keys are not re-pressed when already held
    - Keys are properly released on transitions
    - All keys are released on stop/error/cleanup
    """

    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self._pressed_keys: Set[str] = set()
        self._enabled = False
        self._key_event_log = []  # For debugging

    def enable(self):
        """Enable keyboard output."""
        self._enabled = True
        logger.info("Keyboard controller ENABLED")

    def disable(self):
        """Disable keyboard output and release all keys."""
        self.release_all()
        self._enabled = False
        logger.info("Keyboard controller DISABLED")

    def key_down(self, key_name: str):
        """
        Press a key if not already pressed.
        key_name: e.g. 'left', 'right', 'down', 'space'
        """
        if key_name in self._pressed_keys:
            return  # Already pressed, do nothing

        scan_code = SCAN_CODES.get(key_name)
        if scan_code is None:
            logger.warning(f"Unknown key: {key_name}")
            return

        self._pressed_keys.add(key_name)
        self._key_event_log.append(("DOWN", key_name, time.time()))

        if self._enabled and not self.test_mode:
            _send_key_event(scan_code, key_up=False)
            logger.debug(f"KEY DOWN: {key_name}")
        else:
            logger.debug(f"KEY DOWN (simulated): {key_name}")

    def key_up(self, key_name: str):
        """Release a key if currently pressed."""
        if key_name not in self._pressed_keys:
            return  # Not pressed, do nothing

        scan_code = SCAN_CODES.get(key_name)
        if scan_code is None:
            return

        self._pressed_keys.discard(key_name)
        self._key_event_log.append(("UP", key_name, time.time()))

        if self._enabled and not self.test_mode:
            _send_key_event(scan_code, key_up=True)
            logger.debug(f"KEY UP: {key_name}")
        else:
            logger.debug(f"KEY UP (simulated): {key_name}")

    def release_all(self):
        """Release all currently pressed keys. Critical safety method."""
        keys_to_release = list(self._pressed_keys)
        for key in keys_to_release:
            scan_code = SCAN_CODES.get(key)
            if scan_code is not None and not self.test_mode:
                _send_key_event(scan_code, key_up=True)
            self._pressed_keys.discard(key)

        if keys_to_release:
            logger.info(f"Released all keys: {keys_to_release}")

    def is_pressed(self, key_name: str) -> bool:
        """Check if a key is currently held."""
        return key_name in self._pressed_keys

    @property
    def pressed_keys(self) -> Set[str]:
        return self._pressed_keys.copy()

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_state_dict(self) -> Dict[str, str]:
        """Get a dict of key states for debug display."""
        all_keys = ["left", "right", "down", "space"]
        return {k: "PRESSED" if k in self._pressed_keys else "RELEASED" for k in all_keys}

    def __del__(self):
        """Ensure keys are released on garbage collection."""
        try:
            self.release_all()
        except Exception:
            pass


def get_active_window_info() -> tuple[str, str]:
    """Get the (title, process_name) of the currently active/foreground window."""
    if SYSTEM == "Windows":
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            
            # Get Title
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            
            # Get Process Name
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_VM_READ (0x0010)
            process_handle = ctypes.windll.kernel32.OpenProcess(0x0410, False, pid)
            process_name = ""
            if process_handle:
                try:
                    buf2 = ctypes.create_unicode_buffer(260)
                    ctypes.windll.psapi.GetModuleBaseNameW(process_handle, 0, buf2, 260)
                    process_name = buf2.value
                except Exception:
                    pass
                finally:
                    ctypes.windll.kernel32.CloseHandle(process_handle)
                    
            return title, process_name
        except Exception as e:
            logger.debug(f"Error getting window info: {e}")
            return "", ""
    elif SYSTEM == "Darwin":
        try:
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            name = active_app.get("NSApplicationName", "")
            return name, name
        except Exception:
            return "", ""
    return "", ""


def is_game_window_active(game_title: str = "Asphalt 8", game_process: str = "") -> bool:
    """Check if the game window is the active foreground window."""
    title, process = get_active_window_info()
    
    if game_process and game_process.lower() in process.lower():
        return True
    if game_title and game_title.lower() in title.lower():
        return True
        
    return False
