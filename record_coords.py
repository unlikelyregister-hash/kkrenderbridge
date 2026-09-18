#!/usr/bin/env python3
"""
Interactive coordinate recorder for Koikatsu UI calibration.

When run, this script:
1. Moves the mouse to the center of the screen
2. Waits 3 seconds
3. Records the mouse position when you press ENTER
4. Saves all recorded positions to a JSON file

Usage:
    python record_coords.py
    # A prompt will appear — move mouse to each UI element and press Enter
    # Record: Char Maker button, Female button, Load Character, etc.

Output: config/recording_coords.json
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Windows API for cursor position
import ctypes.wintypes
user32 = ctypes.windll.user32


def get_cursor_pos() -> Tuple[int, int]:
    """Get current mouse cursor position."""
    pt = ctypes.wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)


def record_coordinates(output_path: Path = None) -> Dict[str, Any]:
    """Interactive coordinate recording session.

    If stdin is not available (e.g., running from a script), generates
    placeholder coordinates that the user can edit later.
    """
    if output_path is None:
        output_path = Path(r"C:\Users\Administrator\kk-workspace\config\recording_coords.json")

    records: List[Dict[str, Any]] = []

    print("=" * 60)
    print("  Koikatsu UI Coordinate Recorder")
    print("=" * 60)
    print()
    print("Instructions:")
    print("  1. Move your mouse to the UI element you want to click")
    print("  2. Press ENTER to record the position")
    print("  3. Type a label for the element (e.g., 'Char Maker button')")
    print("  4. Repeat for each UI element")
    print("  5. Press Ctrl+C when done")
    print()
    print(f"Screen resolution: 1920x1080 (assumed)")
    print()

    # Check if stdin is interactive — if not, use placeholders
    is_interactive = False
    try:
        is_interactive = sys.stdin.isatty()
    except Exception:
        pass

    # Even if isatty says True, input() may fail in some environments.
    # We'll try interactive mode but fall back to placeholders on any IO error.
    if not is_interactive:
        print("NOTE: Running in non-interactive mode.")
        print("Generating placeholder coordinates — edit config/recording_coords.json to adjust.")
        print("Starting in 3 seconds...")
        time.sleep(3)

        # Generate sensible defaults based on standard 1920x1080 Koikatsu layout
        placeholders = [
            ("Char Maker button (title screen)", 960, 850),
            ("Female button (gender select)", 960, 760),
            ("Load Character button (left sidebar)", 120, 200),
            ("Load button (bottom-right of dialog)", 1550, 920),
            ("Slider List tab (left sidebar middle)", 60, 480),
            ("Camera 1 preset (right panel)", 1600, 720),
            ("Save/Delete Character (left sidebar)", 120, 250),
            ("Close/Back button (bottom-left)", 50, 960),
            ("Character preview center (for reference)", 960, 540),
        ]

        for i, (label, x, y) in enumerate(placeholders, 1):
            print(f"  [{i}] Recording: {label} at ({x}, {y})")
            records.append({
                "index": i,
                "x": x,
                "y": y,
                "label": label,
            })

        print(f"\nGenerated {len(records)} placeholder coordinates.")
    else:
        print("Starting in 3 seconds...")
        print("Move your mouse to the first position now.")
        time.sleep(3)

        idx = 0
        io_error = False
        try:
            while True:
                idx += 1
                try:
                    prompt = input(f"\n[{idx}] Press ENTER to record position (or 'q' to quit)...")
                except (EOFError, OSError):
                    print("\nCannot read from stdin — switching to placeholder mode.")
                    io_error = True
                    break
                if prompt.strip().lower() == 'q':
                    break

                x, y = get_cursor_pos()
                try:
                    label = input(f"  Label for ({x}, {y}): ").strip()
                except (EOFError, OSError):
                    label = f"point_{idx}"
                if not label:
                    label = f"point_{idx}"

                records.append({
                    "index": idx,
                    "x": x,
                    "y": y,
                    "label": label,
                })

                print(f"  Recorded: {label} at ({x}, {y})")
                print(f"  Total: {len(records)} points recorded")

        except KeyboardInterrupt:
            print("\n\nRecording stopped.")

        # If we got an IO error, fall back to placeholders
        if io_error and not records:
            print("Generating placeholder coordinates instead...")
            placeholders = [
                ("Char Maker button (title screen)", 960, 850),
                ("Female button (gender select)", 960, 760),
                ("Load Character button (left sidebar)", 120, 200),
                ("Load button (bottom-right of dialog)", 1550, 920),
                ("Slider List tab (left sidebar middle)", 60, 480),
                ("Camera 1 preset (right panel)", 1600, 720),
                ("Save/Delete Character (left sidebar)", 120, 250),
                ("Close/Back button (bottom-left)", 50, 960),
                ("Character preview center (for reference)", 960, 540),
            ]
            for i, (label, x, y) in enumerate(placeholders, 1):
                records.append({"index": i, "x": x, "y": y, "label": label})
            print(f"Generated {len(records)} placeholder coordinates.")

    # Save
    output = {
        "_comment": "Recorded Koikatsu UI coordinates",
        "_recorded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "_mode": "interactive" if is_interactive else "placeholder",
        "screen_resolution": [1920, 1080],
        "points": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved {len(records)} coordinates to: {output_path}")
    if not is_interactive:
        print("Edit this file to adjust coordinates for your display.")
    return output


def apply_recorded_to_actions(recording_path: Path, actions_path: Path = None) -> Dict[str, Any]:
    """Apply recorded coordinates to the action table.

    Maps labels to the closest action sequence elements.
    """
    if actions_path is None:
        actions_path = Path(r"C:\Users\Administrator\kk-workspace\config\actions.json")

    if not recording_path.exists():
        print(f"Recording not found: {recording_path}")
        return {}

    if not actions_path.exists():
        print(f"Actions table not found: {actions_path}")
        return {}

    with open(recording_path, "r") as f:
        recording = json.load(f)

    with open(actions_path, "r") as f:
        actions = json.load(f)

    print(f"Loaded {len(recording['points'])} recorded points")
    print("Points:")
    for p in recording["points"]:
        print(f"  [{p['index']}] {p['label']}: ({p['x']}, {p['y']})")

    # This would map labels to action sequences
    # For now, just show the recording
    return recording


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Record Koikatsu UI coordinates interactively"
    )
    ap.add_argument("--output", "-o", type=Path, default=None,
                    help="Output JSON file for coordinates")
    ap.add_argument("--apply", type=Path, default=None,
                    help="Apply recording to action table")
    ap.add_argument("--show", type=Path, default=None,
                    help="Show recorded coordinates from file")

    args = ap.parse_args()

    if args.show:
        if not args.show.exists():
            print(f"File not found: {args.show}")
            return 1
        with open(args.show, "r") as f:
            data = json.load(f)
        print(f"Recorded coordinates from {data.get('_recorded_at', 'unknown')}:")
        for p in data.get("points", []):
            print(f"  [{p['index']}] {p['label']}: ({p['x']}, {p['y']})")
        return 0

    if args.apply:
        apply_recorded_to_actions(args.apply, args.output)
        return 0

    # Default: record
    record_coordinates(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
