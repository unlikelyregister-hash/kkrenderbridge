#!/usr/bin/env python3
"""
ui_automation.py — Game UI automation for Koikatsu Character Maker.

Provides mouse/keyboard control via Windows API (ctypes) to automate
the Character Maker UI: clicking buttons, navigating menus, loading cards,
adjusting sliders, and taking screenshots.

Uses the action table from config/actions.json for predefined workflows.

Coordinate system: screen-relative pixels (0,0 = top-left of primary monitor).
All coordinates assume the game window is positioned at a known location.
For windowed mode, coordinates should be relative to the game window.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
import subprocess
import sys
import time
import win32gui
import win32con
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── Windows API constants ────────────────────────────────────────────────────
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_ABSOLUTE = 0x8000

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

SM_CXSCREEN = 0
SM_CYSCREEN = 1

VK_LBUTTON = 0x01
VK_RBUTTON = 0x02
VK_CANCEL = 0x03
VK_MBUTTON = 0x04
VK_XBUTTON1 = 0x05
VK_XBUTTON2 = 0x06

# Keyboard keys
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_DELETE = 0x2E
VK_INSERT = 0x2D

# Letters
VK_A = 0x41
VK_B = 0x42
VK_C = 0x43
VK_D = 0x44
VK_E = 0x45
VK_F = 0x46
VK_G = 0x47
VK_H = 0x48
VK_I = 0x49
VK_J = 0x4A
VK_K = 0x4B
VK_L = 0x4C
VK_M = 0x4D
VK_N = 0x4E
VK_O = 0x4F
VK_P = 0x50
VK_Q = 0x51
VK_R = 0x52
VK_S = 0x53
VK_T = 0x54
VK_U = 0x55
VK_V = 0x56
VK_W = 0x57
VK_X = 0x58
VK_Y = 0x59
VK_Z = 0x5A

# Number pad
VK_NUMPAD0 = 0x60
VK_NUMPAD1 = 0x61
VK_NUMPAD2 = 0x62
VK_NUMPAD3 = 0x63
VK_NUMPAD4 = 0x64
VK_NUMPAD5 = 0x65
VK_NUMPAD6 = 0x66
VK_NUMPAD7 = 0x67
VK_NUMPAD8 = 0x68
VK_NUMPAD9 = 0x69

# Function keys
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73
VK_F5 = 0x74
VK_F6 = 0x75
VK_F7 = 0x76
VK_F8 = 0x77
VK_F9 = 0x78
VK_F10 = 0x79
VK_F11 = 0x7A
VK_F12 = 0x7B

# ── Module-level state ───────────────────────────────────────────────────────

# Loaded action table
_ACTION_TABLE: Dict[str, Any] = {}
_WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
_CONFIG_PATH = _WORKSPACE / "config" / "actions.json"


# ── Windows API helpers ──────────────────────────────────────────────────────

def _get_screen_size() -> Tuple[int, int]:
    """Get primary monitor dimensions."""
    return (
        ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN),
        ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN),
    )


def _screen_scale() -> Tuple[float, float]:
    """Return (sx, sy) scaling factors from 1920x1080 reference to actual screen."""
    sw, sh = _get_screen_size()
    return (sw / 1920.0, sh / 1080.0)


def _map_to_screen(x1080: int, y1080: int) -> Tuple[int, int]:
    """Convert 1920x1080 reference coordinates to actual screen pixels."""
    sx, sy = _screen_scale()
    return (int(x1080 * sx), int(y1080 * sy))


def _set_foreground_hwnd(hwnd: int) -> bool:
    """Bring a window to the foreground, working around Windows foreground lock.

    Uses the ALT-key simulation trick when SetForegroundWindow alone fails.
    """
    # Try direct first
    result = win32gui.SetForegroundWindow(hwnd)
    if result:
        time.sleep(0.3)
        fg = win32gui.GetForegroundWindow()
        if fg == hwnd:
            return True

    # Fallback: ALT-key toggle to bypass foreground lock
    VK_MENU = 0x12
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(VK_MENU, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.1)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = win32gui.GetForegroundWindow()
    return fg == hwnd


def bring_window_to_front() -> bool:
    """Find the Koikatsu window and bring it to the foreground.

    Returns True if the game window is now the foreground window.
    """
    hwnd = find_game_window()
    if not hwnd:
        return False
    return _set_foreground_hwnd(hwnd)


def mouse_move(x: int, y: int) -> None:
    """Move mouse cursor to absolute screen position.

    Uses SetCursorPos (reliable) instead of MOUSEEVENTF_ABSOLUTE
    which doesn't work reliably on all systems.
    """
    ctypes.windll.user32.SetCursorPos(x, y)


def mouse_click(x: int, y: int, button: str = "left") -> None:
    """Move to position and click.

    x, y are in 1920x1080 reference coordinates — they are scaled to the
    actual screen resolution automatically.
    """
    screen_x, screen_y = _map_to_screen(x, y)
    mouse_move(screen_x, screen_y)
    time.sleep(0.05)

    if button == "left":
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    elif button == "right":
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    elif button == "middle":
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)


def mouse_drag(
    x1: int, y1: int, x2: int, y2: int, button: str = "left"
) -> None:
    """Click at (x1,y1) and drag to (x2,y2).

    x1,y1,x2,y2 are in 1920x1080 reference coordinates — they are scaled
    to the actual screen resolution automatically.
    """
    s_x1, s_y1 = _map_to_screen(x1, y1)
    s_x2, s_y2 = _map_to_screen(x2, y2)
    mouse_move(s_x1, s_y1)
    time.sleep(0.05)

    if button == "left":
        down = MOUSEEVENTF_LEFTDOWN
        up = MOUSEEVENTF_LEFTUP
    elif button == "right":
        down = MOUSEEVENTF_RIGHTDOWN
        up = MOUSEEVENTF_RIGHTUP
    else:
        down = MOUSEEVENTF_MIDDLEDOWN
        up = MOUSEEVENTF_MIDDLEUP

    ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(0.05)

    # Move in steps for smoother drag (using screen coords)
    steps = max(abs(s_x2 - s_x1), abs(s_y2 - s_y1)) // 10 + 1
    for i in range(steps):
        t = (i + 1) / steps
        mx = int(s_x1 + (s_x2 - s_x1) * t)
        my = int(s_y1 + (s_y2 - s_y1) * t)
        mouse_move(mx, my)
        time.sleep(0.01)

    ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)
    time.sleep(0.05)
    
    time.sleep(0.05)
    ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)


def mouse_wheel(delta: int) -> None:
    """Scroll wheel. Positive = up, negative = down."""
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)


def key_down(key_code: int) -> None:
    """Press a key down."""
    ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_EXTENDEDKEY, 0)


def key_up(key_code: int) -> None:
    """Release a key."""
    ctypes.windll.user32.keybd_event(key_code, 0, KEYEVENTF_KEYUP | KEYEVENTF_EXTENDEDKEY, 0)


def key_press(key_code: int) -> None:
    """Press and release a key."""
    key_down(key_code)
    time.sleep(0.03)
    key_up(key_code)


def key_type(char: str) -> None:
    """Type a single character (handles shift for uppercase)."""
    char_upper = char.upper()
    if char == char_upper and 'A' <= char <= 'Z':
        key_press(ord(char))
    elif 'a' <= char <= 'z':
        key_press(ord(char_upper))
    elif char.isdigit():
        key_press(ord(char))
    elif char in "!@#$%^&*()_+{}|:\"<>?~":
        # Handle shifted characters
        shift_map = {
            "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
            "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
            "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
            ":": ";", "\"": "'", "<": ",", ">": ".", "?": "/", "~": "`",
        }
        if char in shift_map:
            key_down(VK_SHIFT)
            key_press(ord(shift_map[char]))
            key_up(VK_SHIFT)
        else:
            key_press(ord(char))
    else:
        key_press(ord(char))


def type_text(text: str, delay: float = 0.02) -> None:
    """Type a string character by character."""
    for char in text:
        key_type(char)
        time.sleep(delay)


def key_combination(keys: List[str]) -> None:
    """Press a combination of keys (e.g. ['Ctrl', 'S'])."""
    # Map names to VK codes
    vk_map = {
        "Ctrl": VK_CONTROL,
        "Control": VK_CONTROL,
        "Alt": VK_MENU,
        "Shift": VK_SHIFT,
        "Esc": VK_ESCAPE,
        "Escape": VK_ESCAPE,
        "Enter": VK_RETURN,
        "Return": VK_RETURN,
        "Space": VK_SPACE,
        "Tab": VK_TAB,
        "Delete": VK_DELETE,
        "Insert": VK_INSERT,
        **{chr(i): i for i in range(ord('A'), ord('Z') + 1)},
        **{chr(i): i for i in range(ord('0'), ord('9') + 1)},
    }
    
    # Press all modifiers down
    for key_name in keys:
        if key_name in vk_map:
            key_down(vk_map[key_name])
    
    time.sleep(0.05)
    
    # Release all
    for key_name in reversed(keys):
        if key_name in vk_map:
            key_up(vk_map[key_name])
    
    time.sleep(0.05)


# ── Window management ────────────────────────────────────────────────────────

def find_game_window() -> Optional[int]:
    """Find Koikatsu game window handle."""
    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Koikatsu" in title or "Koikatsu" in title:
                result.append(hwnd)
    
    result = []
    win32gui.EnumWindows(enum_callback, None)
    return result[0] if result else None


def get_game_window_rect() -> Optional[Tuple[int, int, int, int]]:
    """Get game window position and size (left, top, right, bottom)."""
    hwnd = find_game_window()
    if hwnd:
        return win32gui.GetWindowRect(hwnd)
    return None


def get_cursor_pos() -> Tuple[int, int]:
    """Get current mouse cursor position."""
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


# ── Action execution ────────────────────────────────────────────────────────

def _execute_action(action: Dict[str, Any], context: Dict[str, Any] = None) -> bool:
    """Execute a single action from the action table.

    Args:
        action: Action dict with 'type' field
        context: Optional context dict for variable substitution

    Returns:
        True on success, False on failure
    """
    action_type = action.get("type", "")
    desc = action.get("description", action_type)

    try:
        if action_type == "click":
            x = action.get("x")
            y = action.get("y")
            button = action.get("button", "left")
            if x is not None and y is not None:
                mouse_click(x, y, button)
                print(f"  Click {button} at ({x},{y}): {desc}")
            else:
                print(f"  [skip] click without coordinates: {desc}")

        elif action_type == "drag":
            x1 = action.get("x")
            y1 = action.get("y1", action.get("y"))
            y2 = action.get("y2", action.get("y"))
            button = action.get("button", "left")
            if x1 is not None and y1 is not None and y2 is not None:
                mouse_drag(x1, y1, x1, y2, button)
                print(f"  Drag {button} from y={y1} to y={y2}: {desc}")
            else:
                print(f"  [skip] drag without full coordinates: {desc}")
        
        elif action_type == "delay":
            ms = action.get("ms", 1000)
            seconds = ms / 1000.0
            print(f"  Delay {ms}ms: {desc}")
            time.sleep(seconds)
        
        elif action_type == "keypress":
            key = action.get("key", "")
            if key:
                # Handle special keys
                vk_map = {
                    "enter": VK_RETURN, "return": VK_RETURN,
                    "escape": VK_ESCAPE, "esc": VK_ESCAPE,
                    "tab": VK_TAB, "space": VK_SPACE,
                    "delete": VK_DELETE, "insert": VK_INSERT,
                    "backspace": VK_BACK,
                    "up": VK_UP, "down": VK_DOWN,
                    "left": VK_LEFT, "right": VK_RIGHT,
                    "f1": VK_F1, "f2": VK_F2, "f3": VK_F3, "f4": VK_F4,
                    "f5": VK_F5, "f6": VK_F6, "f7": VK_F7, "f8": VK_F8,
                    "f9": VK_F9, "f10": VK_F10, "f11": VK_F11, "f12": VK_F12,
                }
                vk = vk_map.get(key.lower())
                if vk:
                    key_press(vk)
                    print(f"  Keypress {key}: {desc}")
                elif len(key) == 1:
                    key_type(key)
                    print(f"  Keypress '{key}': {desc}")
                else:
                    print(f"  [skip] unknown key '{key}': {desc}")
            else:
                print(f"  [skip] keypress without key: {desc}")
        
        elif action_type == "hotkey":
            keys = action.get("keys", [])
            if isinstance(keys, list) and keys:
                key_combination(keys)
                print(f"  Hotkey {'+'.join(keys)}: {desc}")
            else:
                print(f"  [skip] hotkey without keys: {desc}")
        
        elif action_type == "typetext":
            text = action.get("text", "")
            if text:
                type_text(text)
                print(f"  Typing '{text}': {desc}")
            else:
                print(f"  [skip] typetext without text: {desc}")
        
        elif action_type == "command":
            cmd = action.get("command", "")
            args = action.get("args", [])
            if cmd:
                print(f"  Running command: {cmd} {' '.join(args)}: {desc}")
                full_cmd = [cmd] + args
                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    print(f"    [warn] command returned {result.returncode}")
                if result.stdout:
                    print(f"    stdout: {result.stdout[:200]}")
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}")
            else:
                print(f"  [skip] command without cmd: {desc}")
        
        elif action_type == "wait_for_window":
            title_fragment = action.get("title", "")
            timeout = action.get("timeout", 30)
            print(f"  Waiting for window containing '{title_fragment}' ({timeout}s): {desc}")
            start = time.time()
            found = False
            while time.time() - start < timeout:
                hwnd = find_game_window()
                if hwnd:
                    title = win32gui.GetWindowText(hwnd)
                    if title_fragment.lower() in title.lower():
                        found = True
                        break
                time.sleep(0.5)
            print(f"    {'Found' if found else 'NOT found'}")
        
        elif action_type == "screenshot":
            output_path = action.get("output", "")
            if output_path:
                # Get cursor position as reference
                cx, cy = get_cursor_pos()
                print(f"  Screenshot to {output_path} (cursor at {cx},{cy}): {desc}")
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(output_path)
                print(f"    Saved {img.size}")
            else:
                print(f"  [skip] screenshot without output path: {desc}")
        
        elif action_type == "select_folder":
            folder = action.get("folder", "")
            print(f"  Select folder '{folder}': {desc}")
            # This requires UI navigation — click folder in list
            # Implementation depends on actual UI layout
        
        elif action_type == "search":
            text = action.get("text", "")
            print(f"  Search for '{text}': {desc}")
            if text:
                type_text(text)
        
        elif action_type == "select_card":
            index = action.get("index", 0)
            print(f"  Select card #{index}: {desc}")
            # Navigate to card in grid
        
        elif action_type == "set_load_options":
            options = action
            print(f"  Set load options: {desc}")
            # Click checkboxes for face/body/hair/etc
        
        else:
            print(f"  [unknown] action type '{action_type}': {desc}")
    
    except Exception as e:
        print(f"  [error] {desc}: {e}")
        return False
    
    return True


def run_action_sequence(
    sequence_name: str,
    action_table: Dict[str, Any] = None,
    context: Dict[str, Any] = None,
    verbose: bool = True,
) -> bool:
    """Run a named sequence of actions from the action table.
    
    Args:
        sequence_name: Name of the action sequence (key in action_table)
        action_table: Action table dict (loaded from config if None)
        context: Optional context for variable substitution
        verbose: Print progress messages
    
    Returns:
        True if all actions succeeded, False if any failed
    """
    if action_table is None:
        action_table = load_action_table()
    
    if sequence_name not in action_table:
        print(f"[error] Unknown action sequence: {sequence_name}")
        print(f"  Available: {list(action_table.keys())}")
        return False
    
    sequence = action_table[sequence_name]
    actions = sequence.get("actions", [])
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Running: {sequence_name}")
        print(f"  Description: {sequence.get('description', '')}")
        print(f"  Actions: {len(actions)}")
        print(f"{'='*60}")
    
    succeeded = 0
    failed = 0
    
    for i, action in enumerate(actions, 1):
        if verbose:
            print(f"\n  [{i}/{len(actions)}] ", end="")
        
        if _execute_action(action, context):
            succeeded += 1
        else:
            failed += 1
            # Continue executing remaining actions
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"  Done: {succeeded} succeeded, {failed} failed")
        print(f"{'='*60}")
    
    return failed == 0


# ── Loading the action table ─────────────────────────────────────────────────

def load_action_table(path: Path = None) -> Dict[str, Any]:
    """Load the action table from JSON config."""
    if path is None:
        path = _CONFIG_PATH
    
    if not path.exists():
        print(f"[warn] Action table not found: {path}")
        return {}
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_action_table(table: Dict[str, Any], path: Path = None) -> None:
    """Save the action table to JSON config."""
    if path is None:
        path = _CONFIG_PATH
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, ensure_ascii=False)


# ── Coordinate calibration helper ────────────────────────────────────────────

def calibrate_coordinates(screenshot_dir: Path = None) -> Dict[str, Dict[str, Any]]:
    """Open an interactive coordinate picker.
    
    This is a helper for calibrating click coordinates.
    It would open screenshots and let the user click to record positions.
    
    For now, returns a template showing what needs calibration.
    """
    if screenshot_dir is None:
        screenshot_dir = Path(r"C:\Games\Koikatsu\UserData\cap")
    
    template = {
        "_comment": "Calibrated coordinates for 1920x1080 screen. Update for your setup.",
        "_calibration_note": "Coordinates are absolute screen pixels. For windowed mode, subtract window offset.",
        "title_to_char_maker": {
            "description": "From title screen → Char Maker",
            "actions": [
                {"type": "click", "x": 960, "y": 850, "button": "left", "description": "Click 'Char Maker' on title screen (CENTER BOTTOM)"},
                {"type": "delay", "ms": 2000, "description": "Wait for sub-menu"},
                {"type": "click", "x": 960, "y": 750, "button": "left", "description": "Click 'Female' on gender select (CENTER)"},
                {"type": "delay", "ms": 8000, "description": "Wait for Character Maker to load"},
            ]
        },
        "load_character": {
            "description": "Open character list, load a card with default clothes",
            "actions": [
                {"type": "click", "x": 100, "y": 200, "button": "left", "description": "Click 'Load Character' (left sidebar)"},
                {"type": "delay", "ms": 1000, "description": "Wait for character list"},
                {"type": "select_folder", "folder": "IA2", "description": "Select folder"},
                {"type": "search", "text": "", "description": "Optional search"},
                {"type": "select_card", "index": 0, "description": "Select first card"},
                {"type": "set_load_options", "face": True, "body": True, "hair": True, "character_info": True, "clothing_sets": False, "description": "Load face/body/hair but NOT clothes"},
                {"type": "click", "x": 1500, "y": 850, "button": "left", "description": "Click 'Load' button (bottom right of dialog)"},
                {"type": "delay", "ms": 3000, "description": "Wait for card to load"},
            ]
        },
        "slider_list_tab": {
            "description": "Open Slider List tab",
            "actions": [
                {"type": "click", "x": 80, "y": 500, "button": "left", "description": "Click 'Slider List' tab (left sidebar, middle)"},
                {"type": "delay", "ms": 500, "description": "Wait for slider panel"},
            ]
        },
        "save_character": {
            "description": "Save current character",
            "actions": [
                {"type": "click", "x": 100, "y": 250, "button": "left", "description": "Click 'Save/Delete Character' (left sidebar)"},
                {"type": "delay", "ms": 1000, "description": "Wait for save dialog"},
                {"type": "type_text", "text": "my_calibrated_char", "description": "Enter character name"},
                {"type": "click", "x": 1500, "y": 850, "button": "left", "description": "Click Save (bottom right)"},
                {"type": "delay", "ms": 2000, "description": "Wait for save"},
            ]
        },
    }
    
    return template


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    
    ap = argparse.ArgumentParser(description="Koikatsu UI automation")
    ap.add_argument(
        "action",
        nargs="?",
        default="list",
        help="Action: list, run <sequence>, calibrate, load-table, save-table",
    )
    ap.add_argument("sequence", nargs="?", help="Sequence name to run")
    ap.add_argument("--calibrate", action="store_true", help="Open coordinate calibration")
    ap.add_argument("--load-table", type=Path, help="Load action table from file")
    ap.add_argument("--save-table", type=Path, help="Save action table to file")
    ap.add_argument("--list", action="store_true", help="List available sequences")
    
    args = ap.parse_args()
    
    # Load action table
    table = load_action_table()
    
    if args.list or args.action == "list":
        print("Available action sequences:")
        for name, seq in table.items():
            if isinstance(seq, dict):
                desc = seq.get("description", seq.get("_comment", ""))
                actions = seq.get("actions", [])
                print(f"  {name}: {desc} ({len(actions)} actions)")
            else:
                print(f"  {name}: (metadata)")
        return 0
    
    if args.calibrate or args.action == "calibrate":
        print("=" * 60)
        print("  Coordinate Calibration Helper")
        print("=" * 60)
        print("\nThis would open screenshots and let you click to set coordinates.")
        print("For now, here are the template coordinates (1920x1080 screen):")
        print()
        template = calibrate_coordinates()
        for name, seq in template.items():
            print(f"\n  [{name}]")
            for a in seq.get("actions", []):
                x = a.get("x", "?")
                y = a.get("y", "?")
                desc = a.get("description", "")
                print(f"    click ({x}, {y}) — {desc}")
        return 0
    
    if args.action == "run" and args.sequence:
        success = run_action_sequence(args.sequence, table)
        return 0 if success else 1
    
    if args.load_table:
        table = load_action_table(args.load_table)
        print(f"Loaded action table from {args.load_table}")
        print(f"Sequences: {list(table.keys())}")
    
    if args.save_table:
        save_action_table(table, args.save_table)
        print(f"Saved action table to {args.save_table}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
