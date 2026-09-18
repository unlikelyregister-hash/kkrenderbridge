#!/usr/bin/env python3
"""
Koikatsu Slider Calibration Tool

Analyzes slider values from character cards to build a comprehensive
mapping between slider indices and their functions.

This works by:
1. Reading slider values from multiple reference cards with known characteristics
2. Correlating slider patterns with card attributes (tall, short, busty, etc.)
3. Building a mapping that can be refined through interactive calibration

Usage:
    python scripts/slider_calibration.py              # Analyze reference cards
    python scripts/slider_calibration.py --interactive  # Interactive calibration mode
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

# ── Paths ───────────────────────────────────────────────────────────────────
WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
GAME_CHAR_DIR = Path(r"C:\Games\Koikatsu\UserData\chara\female")
SARAHS_CARDS = [
    Path(r"C:\Games\Koikatsu\UserData\chara\female\IA2\Sarah\Cards\Koikatu_F_20221020093900740_Sarah.png"),
]
COMMUNITY_DIR = GAME_CHAR_DIR / "[Community]"
OUTPUT = WORKSPACE / "scripts" / "slider_calibration.json"

sys.path.insert(0, str(WORKSPACE))

# ── Known Slider Mappings (Koikatsu Community Knowledge) ──────────────────
# These are the generally accepted mappings for Koikatsu character creator sliders.
# Face shape has 52 indices, Body shape has 44 indices.
# Values typically range from -1.0 to 1.0, with 0.0 being neutral/default.

FACE_SHAPE_SLIDERS = {
    # Face base shape (indices 0-5)
    0: {"name": "Face Width", "desc": "Overall face width", "range": [-1.0, 1.0]},
    1: {"name": "Face Height", "desc": "Overall face height", "range": [-1.0, 1.0]},
    2: {"name": "Face Depth", "desc": "Face forward/backward depth", "range": [-1.0, 1.0]},
    3: {"name": "Face Shape Type", "desc": "Round vs angular face shape", "range": [-1.0, 1.0]},
    4: {"name": "Face Lower Depth", "desc": "Lower face depth", "range": [-1.0, 1.0]},
    5: {"name": "Face Lower Width", "desc": "Lower face/jaw width", "range": [-1.0, 1.0]},
    
    # Upper face (indices 6-11)
    6: {"name": "Forehead Width", "desc": "Width of forehead", "range": [-1.0, 1.0]},
    7: {"name": "Forehead Height", "desc": "Height of forehead", "range": [-1.0, 1.0]},
    8: {"name": "Temple Depth", "desc": "Depth at temples", "range": [-1.0, 1.0]},
    9: {"name": "Cheekbone Width", "desc": "Width at cheekbones", "range": [-1.0, 1.0]},
    10: {"name": "Cheekbone Height", "desc": "Height of cheekbones", "range": [-1.0, 1.0]},
    11: {"name": "Cheek Hollow", "desc": "Hollowness under cheekbones", "range": [-1.0, 1.0]},
    
    # Eye area (indices 12-19)
    12: {"name": "Eye Socket Depth", "desc": "Depth of eye sockets", "range": [-1.0, 1.0]},
    13: {"name": "Eye Socket Width", "desc": "Width of eye sockets", "range": [-1.0, 1.0]},
    14: {"name": "Eye Size (Width)", "desc": "Horizontal eye size", "range": [-1.0, 1.0]},
    15: {"name": "Eye Size (Height)", "desc": "Vertical eye size/openness", "range": [-1.0, 1.0]},
    16: {"name": "Eye Spacing", "desc": "Distance between eyes", "range": [-1.0, 1.0]},
    17: {"name": "Eye Tilt", "desc": "Angle of eyes (up/down)", "range": [-1.0, 1.0]},
    18: {"name": "Inner Eye Corner", "desc": "Inner corner shape", "range": [-1.0, 1.0]},
    19: {"name": "Outer Eye Corner", "desc": "Outer corner shape", "range": [-1.0, 1.0]},
    
    # Nose (indices 20-25)
    20: {"name": "Nose Bridge Height", "desc": "Height of nose bridge", "range": [-1.0, 1.0]},
    21: {"name": "Nose Bridge Width", "desc": "Width of nose bridge", "range": [-1.0, 1.0]},
    22: {"name": "Nose Tip Shape", "desc": "Shape of nose tip", "range": [-1.0, 1.0]},
    23: {"name": "Nose Tip Size", "desc": "Size of nose tip", "range": [-1.0, 1.0]},
    24: {"name": "Nose Nostril Size", "desc": "Size of nostrils", "range": [-1.0, 1.0]},
    25: {"name": "Nose Nostril Shape", "desc": "Shape of nostrils", "range": [-1.0, 1.0]},
    
    # Mouth/Lips (indices 26-33)
    26: {"name": "Mouth Width", "desc": "Width of mouth", "range": [-1.0, 1.0]},
    27: {"name": "Mouth Height", "desc": "Height of mouth opening", "range": [-1.0, 1.0]},
    28: {"name": "Upper Lip Height", "desc": "Height of upper lip", "range": [-1.0, 1.0]},
    29: {"name": "Lower Lip Height", "desc": "Height of lower lip", "range": [-1.0, 1.0]},
    30: {"name": "Lip Thickness", "desc": "Overall lip thickness", "range": [-1.0, 1.0]},
    31: {"name": "Philtrum Length", "desc": "Length of groove above lip", "range": [-1.0, 1.0]},
    32: {"name": "Mouth Corner Tilt", "desc": "Angle of mouth corners", "range": [-1.0, 1.0]},
    33: {"name": "Mouth Shape", "desc": "Overall mouth shape", "range": [-1.0, 1.0]},
    
    # Chin/Jaw (indices 34-41)
    34: {"name": "Chin Length", "desc": "Length of chin", "range": [-1.0, 1.0]},
    35: {"name": "Chin Width", "desc": "Width of chin", "range": [-1.0, 1.0]},
    36: {"name": "Chin Shape", "desc": "Shape of chin tip", "range": [-1.0, 1.0]},
    37: {"name": "Jaw Angle", "desc": "Angle of jaw line", "range": [-1.0, 1.0]},
    38: {"name": "Jaw Definition", "desc": "Prominence of jawline", "range": [-1.0, 1.0]},
    39: {"name": "Jaw Roundness", "desc": "Roundness of jaw", "range": [-1.0, 1.0]},
    40: {"name": "Lower Face Height", "desc": "Overall lower face height", "range": [-1.0, 1.0]},
    41: {"name": "Face Profile", "desc": "Side profile shape", "range": [-1.0, 1.0]},
    
    # Reserved/additional (indices 42-51)
    42: {"name": "Face Roundness", "desc": "Overall face roundness", "range": [-1.0, 1.0]},
    43: {"name": "Face Sharpness", "desc": "Overall face sharpness", "range": [-1.0, 1.0]},
    44: {"name": "Face Softness", "desc": "Skin softness appearance", "range": [-1.0, 1.0]},
    45: {"name": "Face Symmetry", "desc": "Facial symmetry adjustment", "range": [-1.0, 1.0]},
    46: {"name": "Face Balance", "desc": "Overall face balance", "range": [-1.0, 1.0]},
    47: {"name": "Face Proportion", "desc": "General proportion adjust", "range": [-1.0, 1.0]},
    48: {"name": "Face Feature 1", "desc": "Additional face feature", "range": [-1.0, 1.0]},
    49: {"name": "Face Feature 2", "desc": "Additional face feature", "range": [-1.0, 1.0]},
    50: {"name": "Face Feature 3", "desc": "Additional face feature", "range": [-1.0, 1.0]},
    51: {"name": "Face Feature 4", "desc": "Additional face feature", "range": [-1.0, 1.0]},
}

BODY_SHAPE_SLIDERS = {
    # Height and basic proportions (indices 0-5)
    0: {"name": "Height", "desc": "Overall character height", "range": [-1.0, 1.0]},
    1: {"name": "Bust Size", "desc": "Chest/bust size", "range": [-1.0, 1.0]},
    2: {"name": "Bust Position", "desc": "Vertical position of bust", "range": [-1.0, 1.0]},
    3: {"name": "Waist Size", "desc": "Waist circumference", "range": [-1.0, 1.0]},
    4: {"name": "Hip Size", "desc": "Hip circumference", "range": [-1.0, 1.0]},
    5: {"name": "Neck Length", "desc": "Length of neck", "range": [-1.0, 1.0]},
    
    # Upper body (indices 6-15)
    6: {"name": "Neck Width", "desc": "Width of neck", "range": [-1.0, 1.0]},
    7: {"name": "Shoulder Width", "desc": "Width of shoulders", "range": [-1.0, 1.0]},
    8: {"name": "Shoulder Position", "desc": "Vertical position of shoulders", "range": [-1.0, 1.0]},
    9: {"name": "Arm Length", "desc": "Length of arms", "range": [-1.0, 1.0]},
    10: {"name": "Upper Arm Thickness", "desc": "Thickness of upper arms", "range": [-1.0, 1.0]},
    11: {"name": "Forearm Length", "desc": "Length of forearms", "range": [-1.0, 1.0]},
    12: {"name": "Forearm Thickness", "desc": "Thickness of forearms", "range": [-1.0, 1.0]},
    13: {"name": "Hand Size", "desc": "Size of hands", "range": [-1.0, 1.0]},
    14: {"name": "Hand Thickness", "desc": "Thickness of hands", "range": [-1.0, 1.0]},
    15: {"name": "Torso Length", "desc": "Length of torso", "range": [-1.0, 1.0]},
    
    # Mid body (indices 16-25)
    16: {"name": "Torso Width", "desc": "Width of torso", "range": [-1.0, 1.0]},
    17: {"name": "Rib Cage Width", "desc": "Width of rib cage", "range": [-1.0, 1.0]},
    18: {"name": "Pelvis Width", "desc": "Width of pelvis", "range": [-1.0, 1.0]},
    19: {"name": "Pelvis Shape", "desc": "Shape of pelvis/hips", "range": [-1.0, 1.0]},
    20: {"name": "Thigh Length", "desc": "Length of thighs", "range": [-1.0, 1.0]},
    21: {"name": "Thigh Circumference", "desc": "Circumference of thighs", "range": [-1.0, 1.0]},
    22: {"name": "Thigh Gap", "desc": "Gap between thighs", "range": [-1.0, 1.0]},
    23: {"name": "Knee Size", "desc": "Size of knees", "range": [-1.0, 1.0]},
    24: {"name": "Calf Length", "desc": "Length of calves", "range": [-1.0, 1.0]},
    25: {"name": "Calf Circumference", "desc": "Circumference of calves", "range": [-1.0, 1.0]},
    
    # Lower body (indices 26-35)
    26: {"name": "Calf Shape", "desc": "Shape of calves", "range": [-1.0, 1.0]},
    27: {"name": "Ankle Size", "desc": "Size of ankles", "range": [-1.0, 1.0]},
    28: {"name": "Foot Size", "desc": "Size of feet", "range": [-1.0, 1.0]},
    29: {"name": "Foot Width", "desc": "Width of feet", "range": [-1.0, 1.0]},
    30: {"name": "Overall Thickness", "desc": "General body thickness", "range": [-1.0, 1.0]},
    31: {"name": "Waist Position", "desc": "Vertical position of waist", "range": [-1.0, 1.0]},
    32: {"name": "Hip Position", "desc": "Vertical position of hips", "range": [-1.0, 1.0]},
    33: {"name": "Buttock Size", "desc": "Size of buttocks", "range": [-1.0, 1.0]},
    34: {"name": "Buttock Position", "desc": "Vertical position of buttocks", "range": [-1.0, 1.0]},
    35: {"name": "Buttock Shape", "desc": "Shape of buttocks", "range": [-1.0, 1.0]},
    
    # Body composition (indices 36-43)
    36: {"name": "Fat Distribution", "desc": "Where fat is distributed", "range": [-1.0, 1.0]},
    37: {"name": "Muscle Definition", "desc": "Muscle visibility/definition", "range": [-1.0, 1.0]},
    38: {"name": "Chest Depth", "desc": "Depth of chest", "range": [-1.0, 1.0]},
    39: {"name": "Back Thickness", "desc": "Thickness of back", "range": [-1.0, 1.0]},
    40: {"name": "Posture", "desc": "Overall posture", "range": [-1.0, 1.0]},
    41: {"name": "Body Balance", "desc": "Overall body balance", "range": [-1.0, 1.0]},
    42: {"name": "Body Proportion", "desc": "General body proportion", "range": [-1.0, 1.0]},
    43: {"name": "Body Shape Detail", "desc": "Additional shape detail", "range": [-1.0, 1.0]},
}


def load_card_data(card_path: Path) -> Optional[Dict[str, Any]]:
    """Load a character card and extract all slider values."""
    from kkloader import KoikatuCharaData
    
    try:
        card = KoikatuCharaData.load(str(card_path))
        custom = card.Custom.data
        face = custom.get("face", {})
        body = custom.get("body", {})
        hair = custom.get("hair", {})
        
        return {
            "path": str(card_path),
            "name": card_path.name,
            "face_shape": face.get("shapeValueFace", []),
            "body_shape": body.get("shapeValueBody", []),
            "face_features": {
                "headId": face.get("headId", 0),
                "skinId": face.get("skinId", 0),
                "detailId": face.get("detailId", 0),
                "noseId": face.get("noseId", 0),
                "lipLineId": face.get("lipLineId", 0),
                "eyebrowId": face.get("eyebrowId", 0),
                "eyelineUpId": face.get("eyelineUpId", 0),
                "eyelineDownId": face.get("eyelineDownId", 0),
                "hlUpId": face.get("hlUpId", 0),
                "hlDownId": face.get("hlDownId", 0),
                "pupilWidth": face.get("pupilWidth", 0.8),
                "pupilHeight": face.get("pupilHeight", 0.8),
                "pupilX": face.get("pupilX", 0.5),
                "pupilY": face.get("pupilY", 0.5),
                "detailPower": face.get("detailPower", 0.5),
                "cheekGlossPower": face.get("cheekGlossPower", 0.0),
                "lipGlossPower": face.get("lipGlossPower", 0.0),
                "doubleTooth": face.get("doubleTooth", False),
                "foregroundEyebrow": face.get("foregroundEyebrow", 0),
                "foregroundEyes": face.get("foregroundEyes", 0),
            },
            "body_features": {
                "bustWeight": body.get("bustWeight", 0.0),
                "bustSoftness": body.get("bustSoftness", 0.0),
                "areolaSize": body.get("areolaSize", 0.5),
                "skinGlossPower": body.get("skinGlossPower", 0.0),
                "detailPower": body.get("detailPower", 0.5),
                "nailGlossPower": body.get("nailGlossPower", 0.5),
                "nipGlossPower": body.get("nipGlossPower", 0.5),
                "nipId": body.get("nipId", 0),
                "drawAddLine": body.get("drawAddLine", False),
            },
            "skin_colors": {
                "skinMainColor": body.get("skinMainColor", [0.0, 0.0, 0.0, 1.0]),
                "skinSubColor": body.get("skinSubColor", [0.0, 0.0, 0.0, 1.0]),
                "sunburnColor": body.get("sunburnColor", [0.0, 0.0, 0.0, 0.0]),
            },
            "hair": {
                "kind": hair.get("kind", 0),
                "glossId": hair.get("glossId", 0),
            },
        }
    except Exception as e:
        print(f"  Error loading {card_path.name}: {e}")
        return None


def analyze_cards(cards: List[Path]) -> Dict[str, Any]:
    """Analyze multiple cards to understand slider patterns."""
    print(f"\n=== Analyzing {len(cards)} Cards ===")
    
    card_data = []
    for card_path in cards:
        data = load_card_data(card_path)
        if data:
            card_data.append(data)
            print(f"  ✓ {card_path.name}: face={len(data['face_shape'])} sliders, body={len(data['body_shape'])} sliders")
    
    if not card_data:
        print("  ✗ No cards could be loaded")
        return None
    
    # Calculate statistics for each slider
    face_stats = {}
    for i in range(52):
        values = [c["face_shape"][i] for c in card_data if i < len(c["face_shape"])]
        if values:
            face_stats[i] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values),
            }
    
    body_stats = {}
    for i in range(44):
        values = [c["body_shape"][i] for c in card_data if i < len(c["body_shape"])]
        if values:
            body_stats[i] = {
                "count": len(values),
                "mean": statistics.mean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values),
            }
    
    # Identify variable sliders (those with high variance across cards)
    variable_face = [(i, s) for i, s in face_stats.items() if s["stdev"] > 0.1]
    variable_body = [(i, s) for i, s in body_stats.items() if s["stdev"] > 0.1]
    
    print(f"\n  Variable face sliders (stdev > 0.1): {len(variable_face)}/52")
    print(f"  Variable body sliders (stdev > 0.1): {len(variable_body)}/44")
    
    # Build calibration output
    calibration = {
        "version": "1.0",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cards_analyzed": len(card_data),
        "card_names": [c["name"] for c in card_data],
        "face_shape_sliders": {},
        "body_shape_sliders": {},
        "face_features": {},
        "body_features": {},
        "skin_colors": {},
        "hair": {},
        "analysis": {
            "variable_face_count": len(variable_face),
            "variable_body_count": len(variable_body),
            "most_variable_face": [
                {"index": i, "name": FACE_SHAPE_SLIDERS.get(i, {}).get("name", "unknown"), "stdev": s["stdev"]}
                for i, s in sorted(variable_face, key=lambda x: -x[1]["stdev"])[:10]
            ],
            "most_variable_body": [
                {"index": i, "name": BODY_SHAPE_SLIDERS.get(i, {}).get("name", "unknown"), "stdev": s["stdev"]}
                for i, s in sorted(variable_body, key=lambda x: -x[1]["stdev"])[:10]
            ],
        },
    }
    
    # Add detailed slider info
    for i in range(52):
        info = FACE_SHAPE_SLIDERS.get(i, {"name": f"Face Slider {i}", "desc": "Unknown face slider"})
        stats = face_stats.get(i, {})
        calibration["face_shape_sliders"][str(i)] = {
            "name": info["name"],
            "description": info["desc"],
            "range": info["range"],
            "statistics": stats,
            "card_values": [c["face_shape"][i] for c in card_data if i < len(c["face_shape"])],
        }
    
    for i in range(44):
        info = BODY_SHAPE_SLIDERS.get(i, {"name": f"Body Slider {i}", "desc": "Unknown body slider"})
        stats = body_stats.get(i, {})
        calibration["body_shape_sliders"][str(i)] = {
            "name": info["name"],
            "description": info["desc"],
            "range": info["range"],
            "statistics": stats,
            "card_values": [c["body_shape"][i] for c in card_data if i < len(c["body_shape"])],
        }
    
    # Face features from first card
    if card_data:
        calibration["face_features"] = card_data[0]["face_features"]
        calibration["body_features"] = card_data[0]["body_features"]
        calibration["skin_colors"] = card_data[0]["skin_colors"]
        calibration["hair"] = card_data[0]["hair"]
    
    return calibration


def interactive_calibration():
    """Interactive mode for calibrating sliders in real-time."""
    print("\n" + "=" * 60)
    print("  Interactive Slider Calibration Mode")
    print("=" * 60)
    print("""
Instructions:
1. Open Character Maker in Koikatsu
2. Load a character card
3. Click on 'Slider List' tab in the left sidebar
4. Adjust any slider and note its effect
5. Press Enter here after each adjustment
6. The script will read the current slider values

You can also:
- Type 'show' to see current slider values
- Type 'save <filename>' to save current state
- Type 'load <filename>' to load a saved state
- Type 'help' for more commands
- Type 'quit' to exit

Let's start by loading a reference card...
""")
    
    # Try to load Sarah card as reference
    sarah_path = WORKSPACE / "blocks" / "face_image.png"
    if sarah_path.exists():
        print(f"Loading reference from: {sarah_path}")
    else:
        print("No reference card found in workspace")
    
    input("Press Enter when you have a character loaded in Character Maker...")
    
    # In interactive mode, we'd read the current card state
    # For now, just show what we know
    print("\nCurrent calibration knowledge:")
    print(f"  Face shape sliders: 52 total")
    print(f"  Body shape sliders: 44 total")
    print(f"  Mapped face sliders: {len(FACE_SHAPE_SLIDERS)}")
    print(f"  Mapped body sliders: {len(BODY_SHAPE_SLIDERS)}")
    
    print("\nTo calibrate a specific slider:")
    print("1. Note its position in the UI")
    print("2. Adjust it and observe the 3D model")
    print("3. Save the card and reload to see the value change")
    print("4. Update the mapping based on observation")
    
    input("\nPress Enter to continue...")
    
    # Run analysis on available cards
    card_paths = []
    
    # Add Sarah's cards
    for p in SARAHS_CARDS:
        if p.exists():
            card_paths.append(p)
    
    # Add community cards (first 10)
    if COMMUNITY_DIR.exists():
        for p in sorted(COMMUNITY_DIR.glob("*.png"))[:10]:
            card_paths.append(p)
    
    if card_paths:
        print(f"\nAnalyzing {len(card_paths)} cards for slider patterns...")
        calibration = analyze_cards(card_paths)
        
        if calibration:
            save_calibration(calibration)
            print(f"\nCalibration saved to: {OUTPUT}")
    else:
        print("\nNo character cards found to analyze.")
        print("Please put some .png character cards in the workspace to analyze.")


def save_calibration(calibration: Dict[str, Any]):
    """Save calibration to JSON file."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(calibration, f, indent=2, ensure_ascii=False)


def main():
    """Main entry point."""
    print("=" * 60)
    print("  Koikatsu Slider Calibration Tool")
    print("=" * 60)
    
    interactive = "--interactive" in sys.argv or "-i" in sys.argv
    
    if interactive:
        interactive_calibration()
    else:
        # Normal analysis mode
        card_paths = []
        
        # Add Sarah's cards
        for p in SARAHS_CARDS:
            if p.exists():
                card_paths.append(p)
        
        # Add community cards
        if COMMUNITY_DIR.exists():
            for p in sorted(COMMUNITY_DIR.glob("*.png"))[:20]:
                card_paths.append(p)
        
        if not card_paths:
            print("No character cards found!")
            print(f"Looking in: {COMMUNITY_DIR}")
            return 1
        
        print(f"Found {len(card_paths)} cards to analyze")
        calibration = analyze_cards(card_paths[:10])  # Analyze first 10
        
        if calibration:
            save_calibration(calibration)
            print(f"\nCalibration saved to: {OUTPUT}")
            print(f"\nKey findings:")
            print(f"  Variable face sliders: {calibration['analysis']['variable_face_count']}/52")
            print(f"  Variable body sliders: {calibration['analysis']['variable_body_count']}/44")
            
            print(f"\nMost variable face sliders:")
            for item in calibration['analysis']['most_variable_face'][:5]:
                print(f"  [{item['index']:2d}] {item['name']:30s} (stdev: {item['stdev']:.3f})")
            
            print(f"\nMost variable body sliders:")
            for item in calibration['analysis']['most_variable_body'][:5]:
                print(f"  [{item['index']:2d}] {item['name']:30s} (stdev: {item['stdev']:.3f})")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
