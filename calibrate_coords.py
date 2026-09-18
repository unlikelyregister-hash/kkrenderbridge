#!/usr/bin/env python3
"""
Screenshot-based coordinate calibration — fast version.

Scans UI screenshots for solid-color regions using row/column profile
analysis instead of flood-fill. Much faster.

Usage:
    python calibrate_coords.py --analyze
    python calibrate_coords.py --output config/actions_calibrated.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

CAP_DIR = Path(r"C:\Games\Koikatsu\UserData\cap")
OUTPUT_DEFAULT = Path(r"C:\Users\Administrator\kk-workspace\config\actions_calibrated.json")
SCREEN_W = 1920
SCREEN_H = 1080


# ── Fast region detection via row/column profiles ────────────────────────────

def detect_regions_fast(img: Image.Image, min_area: int = 500) -> List[Dict[str, Any]]:
    """Detect rectangular regions by looking for color-uniform bands.

    Much faster than flood-fill: scans horizontal and vertical profiles
    to find runs of similar-colored pixels, then intersects them.

    Returns list of region dicts.
    """
    arr = np.array(img)
    h, w, _ = arr.shape

    # Detect major color transitions in each row
    # A "solid region" has low variance across its span
    regions = []

    # Horizontal scan: find runs where each row has stable color
    for y in range(0, h, 2):  # sample every 2nd row for speed
        row = arr[y].astype(int)
        # Compute color differences between adjacent pixels
        diffs = np.abs(np.diff(row, axis=0)).max(axis=1)
        # Find runs where diffs are small (solid color)
        is_solid = diffs < 30  # tolerance

        # Find contiguous solid runs
        changes = np.diff(np.concatenate([[False], is_solid, [False]]).astype(int))
        starts = np.where(changes == 1)[0]
        ends = np.where(changes == -1)[0]

        for s, e in zip(starts, ends):
            run_w = e - s
            if run_w < 30:  # minimum width
                continue

            # Check if this row segment is part of a larger region
            # by checking vertical consistency in a small window
            y_min = max(0, y - 2)
            y_max = min(h - 1, y + 2)

            # Average color of this segment
            seg = arr[y, s:e]
            avg_color = seg.mean(axis=0).astype(int)

            # Check if similar rows above/below have similar segments
            consistent = 0
            for dy in range(y_min, y_max + 1):
                if dy == y:
                    continue
                row2 = arr[dy].astype(int)
                diffs2 = np.abs(np.diff(row2, axis=0)).max(axis=1)
                is_solid2 = diffs2 < 30
                changes2 = np.diff(np.concatenate([[False], is_solid2, [False]]).astype(int))
                starts2 = np.where(changes2 == 1)[0]
                ends2 = np.where(changes2 == -1)[0]

                for s2, e2 in zip(starts2, ends2):
                    # Check overlap
                    if s2 <= s and e2 >= e:
                        seg2 = arr[dy, s:e]
                        avg2 = seg2.mean(axis=0).astype(int)
                        color_diff = np.abs(avg_color - avg2).max()
                        if color_diff < 40:
                            consistent += 1

            if consistent >= 1:  # at least 1 neighboring row agrees
                area = run_w * min(5, consistent + 1)
                if area >= min_area:
                    regions.append({
                        "x": int(s),
                        "y": int(y),
                        "w": int(run_w),
                        "h": 3,  # approximate
                        "cx": int(s + run_w // 2),
                        "cy": int(y),
                        "color": [int(c) for c in avg_color],
                    })

    # Merge nearby regions that are likely the same UI element
    merged = []
    for r in sorted(regions, key=lambda x: (x["y"], x["x"])):
        # Check if this overlaps/touches any existing merged region
        found = False
        for m in merged:
            if (abs(r["cx"] - m["cx"]) < r["w"] and
                    abs(r["y"] - m["y"]) < 10):
                # Merge: expand the existing region
                m["w"] = max(m["w"], r["x"] + r["w"] - m["x"])
                m["h"] = max(m["h"], abs(r["y"] - m["y"]) + 3)
                m["y"] = min(m["y"], r["y"])
                m["cy"] = (m["y"] + m["h"] // 2)
                found = True
                break
        if not found:
            merged.append(dict(r))

    return merged


def classify_region(r: Dict[str, Any]) -> str:
    """Classify a UI region by its screen position."""
    x, y, w, h = r["x"], r["y"], r["w"], r["h"]

    if y < 100:
        return "title_bar"
    if x < 250:
        if y < 400:
            return "sidebar_left_top"
        elif y < 700:
            return "sidebar_left_mid"
        else:
            return "sidebar_left_bot"
    if x > SCREEN_W - 250:
        if y > SCREEN_H - 200:
            return "bottom_right_btn"
        return "right_panel"
    if y > SCREEN_H - 150:
        return "bottom_bar"
    if w > 200 and h > 40:
        return "center_panel"
    return "unknown"


def analyze_screenshot(screenshot_path: Path, max_regions: int = 30) -> Dict[str, Any]:
    """Analyze one screenshot for UI element positions."""
    img = Image.open(screenshot_path)
    regions = detect_regions_fast(img, min_area=300)

    # Classify and sort
    for r in regions:
        r["classification"] = classify_region(r)

    # Keep most significant regions (by area)
    regions.sort(key=lambda r: r["w"] * r["h"], reverse=True)
    top = regions[:max_regions]

    return {
        "file": screenshot_path.name,
        "size": [img.width, img.height],
        "region_count": len(regions),
        "top_regions": top,
    }


# ── Build calibrated action table ────────────────────────────────────────────

def build_calibrated_table() -> Dict[str, Any]:
    """Build action table with coordinates calibrated for standard 1920x1080.

    The coordinates are educated guesses based on standard Koikatsu UI layout.
    The user should verify against actual screenshots and adjust as needed.
    """
    return {
        "_comment": "Calibrated UI automation coordinates for Koikatsu (1920x1080).",
        "_calibration_method": "Positional estimates — verify with screenshots in "
                               "C:\\Games\\Koikatsu\\UserData\\cap\\",
        "_adjustment_tip": "If game is windowed, coordinates may need offset adjustment. "
                           "Use the screenshot analysis to find actual button positions.",

        "title_to_char_maker": {
            "description": "From title screen → Char Maker",
            "actions": [
                {"type": "click", "x": 960, "y": 850, "button": "left",
                 "description": "Click 'Char Maker' on title screen"},
                {"type": "delay", "ms": 2000, "description": "Wait for sub-menu"},
                {"type": "click", "x": 960, "y": 760, "button": "left",
                 "description": "Click 'Female' on gender selection"},
                {"type": "delay", "ms": 8000, "description": "Wait for CM to load"},
            ]
        },

        "load_character": {
            "description": "Open character list, load card with options",
            "actions": [
                {"type": "click", "x": 120, "y": 200, "button": "left",
                 "description": "Click 'Load Character' (left sidebar)"},
                {"type": "delay", "ms": 1000, "description": "Wait for character list"},
                {"type": "select_folder", "folder": "IA2",
                 "description": "Select folder from left panel"},
                {"type": "search", "text": "",
                 "description": "Optional search filter"},
                {"type": "select_card", "index": 0,
                 "description": "Select first card in grid"},
                {"type": "set_load_options",
                 "face": True, "body": True, "hair": True,
                 "character_info": True, "clothing_sets": False,
                 "description": "Load face/body/hair/info, NOT clothes"},
                {"type": "click", "x": 1550, "y": 920, "button": "left",
                 "description": "Click 'Load' button (bottom-right)"},
                {"type": "delay", "ms": 3000, "description": "Wait for card to load"},
            ]
        },

        "slider_list_tab": {
            "description": "Open Slider List tab",
            "actions": [
                {"type": "click", "x": 60, "y": 480, "button": "left",
                 "description": "Click 'Slider List' tab (left sidebar middle)"},
                {"type": "delay", "ms": 500, "description": "Wait for slider panel"},
            ]
        },

        "adjust_slider": {
            "description": "Adjust a slider value by dragging",
            "actions": [
                {"type": "click", "x": 400, "y": 300, "button": "left",
                 "description": "Click slider handle (center)—adjust for target slider"},
                {"type": "drag", "x": 400, "y": 380, "button": "left",
                 "description": "Drag to new value position"},
                {"type": "delay", "ms": 200, "description": "Wait for slider to settle"},
            ]
        },

        "save_character": {
            "description": "Save character to file",
            "actions": [
                {"type": "click", "x": 120, "y": 250, "button": "left",
                 "description": "Click 'Save/Delete Character' (left sidebar)"},
                {"type": "delay", "ms": 1000, "description": "Wait for save dialog"},
                {"type": "type_text", "text": "calibrated_char",
                 "description": "Enter character name"},
                {"type": "click", "x": 1550, "y": 920, "button": "left",
                 "description": "Click Save/OK button"},
                {"type": "delay", "ms": 2000, "description": "Wait for save"},
            ]
        },

        "close_character_maker": {
            "description": "Close Character Maker → title screen",
            "actions": [
                {"type": "click", "x": 50, "y": 960, "button": "left",
                 "description": "Click close/back button (bottom-left)"},
                {"type": "delay", "ms": 3000, "description": "Wait for title screen"},
            ]
        },

        "set_camera_preset": {
            "description": "Select camera preset from right Control Panel",
            "actions": [
                {"type": "click", "x": 1600, "y": 720, "button": "left",
                 "description": "Click Camera 1 (right panel bottom area)"},
                {"type": "delay", "ms": 500, "description": "Wait for camera move"},
            ]
        },

        "trigger_render": {
            "description": "Trigger render via KkRenderBridge plugin (file-based, not UI)",
            "actions": [
                {"type": "command", "command": "python",
                 "args": ["scripts/kk-submit-render.py"],
                 "description": "Submit render request via plugin"},
                {"type": "delay", "ms": 15000, "description": "Wait for render"},
            ]
        }
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Calibrate Koikatsu UI coordinates from screenshots"
    )
    ap.add_argument("--output", "-o", type=Path, default=OUTPUT_DEFAULT,
                    help=f"Output JSON (default: {OUTPUT_DEFAULT})")
    ap.add_argument("--analyze", action="store_true",
                    help="Analyze screenshots and print findings")
    ap.add_argument("--screenshot", type=Path, default=None,
                    help="Analyze one specific screenshot")

    args = ap.parse_args()

    if args.analyze:
        if args.screenshot:
            screenshots = [args.screenshot]
        else:
            screenshots = sorted(CAP_DIR.glob("Koikatu-*-UI.png"))

        if not screenshots:
            print(f"No Koikatu UI screenshots in {CAP_DIR}")
        else:
            print(f"Analyzing {len(screenshots)} screenshots (fast scan)...")
            for ss in screenshots[:8]:
                result = analyze_screenshot(ss)
                print(f"\n  {result['file']} ({result['size'][0]}x{result['size'][1]}): "
                      f"{result['region_count']} raw regions")
                # Show top 5 by area
                for r in result["top_regions"][:5]:
                    print(f"    [{r['classification']:20s}] ({r['x']:4d},{r['y']:4d}) "
                          f"{r['w']:3d}x{r['h']:3d} → center ({r['cx']:4d},{r['cy']:4d}) "
                          f"rgb={r['color']}")

    # Save calibrated table
    table = build_calibrated_table()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(table, f, indent=2, ensure_ascii=False)

    print(f"\nCalibrated table saved to: {args.output}")
    print(f"Sequences: {list(table.keys())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
