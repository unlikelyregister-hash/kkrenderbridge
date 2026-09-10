#!/usr/bin/env python3
"""
run_build.py — Master orchestrator for the Koikatsu character building pipeline.

Ties together all 6 improvements:
  1. Clothing as separate optional component (default nude, --keep-clothes, --clothes-from)
  2. Two-folder input (look images + style directory)
  3. Slider support (face/body shape values from style signature)
  4. Game launch + navigate + load card (via game_manager + ui_automation)
  5. Single instance enforcement (game_manager singleton lock)
  6. Orchestration of the full pipeline

Usage:
    # Full pipeline with game automation
    python run_build.py \\
        --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\IA2\\Sarah\\Cards\\*.png" \\
        --style "styles/slender/" \\
        --output out/my_character.kkpe \\
        --launch-game --load-in-game

    # Build only (no game)
    python run_build.py \\
        --look "looks/hair_blue_eyes_green/" \\
        --style "styles/athletic/" \\
        --output out/blue_athletic.kkpe

    # Keep original clothes from look card
    python run_build.py \\
        --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\[Community]\\KK_398582.png" \\
        --style "styles/round_face/" \\
        --output out/round_char.kkpe \\
        --keep-clothes

    # Inject clothes from specific card
    python run_build.py \\
        --look "looks/hair_blonde/" \\
        --style "styles/curvy/" \\
        --output out/blonde_curvy.kkpe \\
        --clothes-from "C:\\Games\\Koikatsu\\UserData\\chara\\female\\IA2\\Sarah\\Cards\\*.png"
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Paths ────────────────────────────────────────────────────────────────────
WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
sys.path.insert(0, str(WORKSPACE))

from kkloader import KoikatuCharaData

# ── CLI Arguments ────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Koikatsu character builder — full pipeline orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Build from look folder + style folder (no game)
  python run_build.py \\
      --look "looks/hair_blonde_eyes_blue/" \\
      --style "styles/slender/" \\
      --output out/blonde_slender.kkpe

  # Build from single look card + style, keep original clothes
  python run_build.py \\
      --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\[Community]\\KK_398582.png" \\
      --style "styles/athletic/" \\
      --output out/athletic_kk.kkpe \\
      --keep-clothes

  # Full pipeline: build + launch game + load card in Character Maker
  python run_build.py \\
      --look "looks/hair_pink/" \\
      --style "styles/curvy/" \\
      --output out/pink_curvy.kkpe \\
      --launch-game --load-in-game

  # Just launch and prepare game (no build)
  python run_build.py --launch-game --ensure-cm
""",
    )

    # Look input (one or both of these)
    ap.add_argument(
        "--look", "-l",
        type=Path,
        default=None,
        help="Look reference: a .png card, glob pattern, or directory (e.g. 'sarah.png', '*.png', 'looks/hair_blonde/')",
    )
    ap.add_argument(
        "--look-dir", "-ld",
        type=Path,
        default=None,
        help="Directory of additional look cards to merge with --look (optional)",
    )

    # Style input
    ap.add_argument(
        "--style", "-s",
        type=Path,
        required=True,
        help="Style directory containing multiple .png cards that share a body/face style",
    )

    # Output
    ap.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output card path (.kkpe or .png)",
    )

    # Clothing options
    ap.add_argument(
        "--keep-clothes",
        action="store_true",
        default=False,
        help="Keep the look card's original clothes (default: replace with nude)",
    )
    ap.add_argument(
        "--clothes-from", "-c",
        type=Path,
        default=None,
        help="Inject clothes from this card instead of default nude",
    )

    # Style blending
    ap.add_argument(
        "--style-blend",
        type=float,
        default=1.0,
        help="How much to blend toward style average (0.0=keep original, 1.0=full style, default 1.0)",
    )

    # Metadata overrides
    ap.add_argument("--name", type=str, default=None, help="Override firstname")
    ap.add_argument("--nickname", type=str, default=None, help="Override nickname")
    ap.add_argument("--lastname", type=str, default=None, help="Override lastname/familyname")

    # Game automation
    ap.add_argument(
        "--launch-game",
        action="store_true",
        default=False,
        help="Launch Koikatsu if not running (uses game_manager)",
    )
    ap.add_argument(
        "--close-game",
        action="store_true",
        default=False,
        help="Close the game after building (save and exit)",
    )
    ap.add_argument(
        "--ensure-cm",
        action="store_true",
        default=False,
        help="Navigate to Character Maker (requires --launch-game or game already running)",
    )
    ap.add_argument(
        "--load-in-game",
        action="store_true",
        default=False,
        help="Load the built card in Character Maker via UI automation (implies --launch-game --ensure-cm)",
    )
    ap.add_argument(
        "--load-folder",
        type=str,
        default="IA2",
        help="Character folder to load from in-game (default: IA2)",
    )
    ap.add_argument(
        "--load-options",
        type=str,
        default="face,body,hair,info",
        help="Comma-separated load options: face, body, hair, info, clothes, overlays. "
             "Use 'none' for default clothes. Default: face,body,hair,info",
    )

    # Card source hints
    ap.add_argument(
        "--source-card",
        type=Path,
        default=None,
        help="Optional: use this card as the base template (for blockdata/structure). "
             "If not set, uses the look card.",
    )

    args = ap.parse_args()

    # Validation
    if args.look is None:
        print("[run_build] ERROR: --look is required (or --look-dir alone is not enough)")
        ap.print_help()
        sys.exit(1)

    if args.load_in_game:
        args.launch_game = True
        args.ensure_cm = True

    return args


# ── Card Building (reuse card_builder.py logic) ──────────────────────────────

def extract_look_traits(card: KoikatuCharaData) -> Dict[str, Any]:
    """Extract look traits from a card.

    Extracts both surface traits (colors) AND structural traits (hair kind,
    hair part IDs, eye pupil ID, skin IDs) so the look can be fully reproduced.
    """
    custom = card.Custom.data
    hair = custom["hair"]
    face = custom["face"]
    body = custom["body"]

    # --- Hair parts with full data ---
    hair_parts = []
    for part in hair.get("parts", []):
        if part and part.get("id", 0) != 0:
            hair_parts.append({
                "id": part["id"],
                "baseColor": list(part.get("baseColor", [1.0, 1.0, 1.0, 1.0])),
                "startColor": list(part.get("startColor", [1.0, 1.0, 1.0, 1.0])),
                "endColor": list(part.get("endColor", [1.0, 1.0, 1.0, 1.0])),
            })

    # Average hair color across parts (for backward compat)
    hair_colors = [p["baseColor"][:3] for p in hair_parts]
    hair_color = (
        [sum(c) / len(c) for c in zip(*hair_colors)] if hair_colors else [1.0, 1.0, 1.0]
    )

    # Eye pupil
    pupil = face.get("pupil", [])
    eye_color = [1.0, 1.0, 1.0]
    eye_id = 0
    if pupil:
        bc = pupil[0].get("baseColor")
        if bc:
            eye_color = list(bc[:3])
        eye_id = pupil[0].get("id", 0)

    skin_main = list(face.get("skinMainColor", body.get("skinMainColor", [1.0, 1.0, 1.0, 1.0]))[:3])
    skin_sub = list(face.get("skinSubColor", body.get("skinSubColor", [1.0, 1.0, 1.0, 1.0]))[:3])

    return {
        "hair_color": hair_color,
        "hair_kind": hair.get("kind", 0),
        "hair_parts": hair_parts,
        "eye_color": eye_color,
        "eye_id": eye_id,
        "skin_main_color": skin_main,
        "skin_sub_color": skin_sub,
        "hair_part_ids": [p.get("id", 0) for p in hair.get("parts", [])],
        "face_skin_id": face.get("skinId", 0),
        "body_skin_id": body.get("skinId", 0),
    }


def merge_look_traits(traits_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple look trait sets by averaging RGB values."""
    if not traits_list:
        return {}
    if len(traits_list) == 1:
        return traits_list[0]

    import numpy as np

    def avg_rgb(key: str) -> List[float]:
        vals = [t[key] for t in traits_list if key in t and len(t[key]) >= 3]
        if not vals:
            return [1.0, 1.0, 1.0]
        arr = np.array(vals, dtype=np.float64)
        return arr.mean(axis=0).tolist()[:3]

    return {
        "hair_color": avg_rgb("hair_color"),
        "eye_color": avg_rgb("eye_color"),
        "skin_main_color": avg_rgb("skin_main_color"),
        "skin_sub_color": avg_rgb("skin_sub_color"),
        "hair_kind": traits_list[0].get("hair_kind", 0),
        "hair_parts": traits_list[0].get("hair_parts", []),
        "hair_part_ids": traits_list[0].get("hair_part_ids", []),
        "eye_id": traits_list[0].get("eye_id", 0),
        "face_skin_id": traits_list[0].get("face_skin_id", 0),
        "body_skin_id": traits_list[0].get("body_skin_id", 0),
    }


def extract_style_traits(card: KoikatuCharaData) -> Dict[str, Any]:
    """Extract style (structural) traits."""
    custom = card.Custom.data
    face = custom["face"]
    body = custom["body"]
    return {
        "shapeValueFace": list(face.get("shapeValueFace", [])),
        "shapeValueBody": list(body.get("shapeValueBody", [])),
        "noseId": face.get("noseId", 0),
        "lipLineId": face.get("lipLineId", 0),
        "eyebrowId": face.get("eyebrowId", 0),
        "headId": face.get("headId", 0),
        "bustWeight": body.get("bustWeight", 0.0),
        "bustSoftness": body.get("bustSoftness", 0.0),
        "pupilWidth": face.get("pupilWidth", 0.8),
        "pupilHeight": face.get("pupilHeight", 0.8),
        "pupilX": face.get("pupilX", 0.5),
        "pupilY": face.get("pupilY", 0.5),
    }


def style_group_signature(style_dir: Path) -> Dict[str, Any]:
    """Compute style signature from a directory of style cards."""
    import numpy as np
    from collections import Counter

    cards = list(style_dir.glob("*.png"))
    if not cards:
        return {
            "average_traits": {}, "consensus_features": {},
            "internal_similarity": 0.0, "member_count": 0, "member_paths": [],
        }

    print(f"[style] Analyzing {len(cards)} cards in {style_dir.name}...")
    all_traits = []
    for cp in cards:
        try:
            raw = cp.read_bytes()
            try:
                card = KoikatuCharaData.load(raw)
            except TypeError:
                card = KoikatuCharaData.load(str(cp))
            t = extract_style_traits(card)
            t["_path"] = str(cp)
            all_traits.append(t)
        except Exception as e:
            print(f"  [style] skipped {cp.name}: {e}")

    if not all_traits:
        return {"average_traits": {}, "consensus_features": {},
                "internal_similarity": 0.0, "member_count": 0, "member_paths": []}

    # Pairwise similarity
    n = len(all_traits)
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            a = all_traits[i]
            b = all_traits[j]
            fa = np.array(a.get("shapeValueFace", []), dtype=np.float64)
            fb = np.array(b.get("shapeValueFace", []), dtype=np.float64)
            if len(fa) and len(fb):
                ml = max(len(fa), len(fb))
                fsim = float(np.dot(np.pad(fa, (0, ml-len(fa))), np.pad(fb, (0, ml-len(fb)))) /
                             (np.linalg.norm(fa)*np.linalg.norm(fb)+1e-9))
            else:
                fsim = 0.0
            sims.append(fsim)

    internal_sim = sum(sims) / len(sims) if sims else 0.0

    # Averages
    face_arrays = [np.array(t["shapeValueFace"], dtype=np.float64) for t in all_traits]
    body_arrays = [np.array(t["shapeValueBody"], dtype=np.float64) for t in all_traits]
    mfl = max(len(a) for a in face_arrays)
    mbl = max(len(a) for a in body_arrays)
    avg_face = np.zeros(mfl)
    avg_body = np.zeros(mbl)
    for a in face_arrays:
        avg_face[:len(a)] += a
    for a in body_arrays:
        avg_body[:len(a)] += a
    avg_face /= n
    avg_body /= n

    # Consensus
    consensus = {}
    for key in ("noseId", "lipLineId", "eyebrowId", "headId", "bustWeight", "bustSoftness"):
        vals = [t.get(key) for t in all_traits if t.get(key) is not None]
        if vals:
            consensus[key] = Counter(vals).most_common(1)[0][0]

    return {
        "average_traits": {"shapeValueFace": avg_face.tolist(), "shapeValueBody": avg_body.tolist()},
        "consensus_features": consensus,
        "internal_similarity": internal_sim,
        "member_count": n,
        "member_paths": [t["_path"] for t in all_traits],
    }


def apply_look_traits(
    card: KoikatuCharaData,
    look: Dict[str, Any],
) -> None:
    """Apply look traits to card in-place.

    Copies BOTH surface colors AND structural features (hair kind, hair part
    IDs, eye pupil ID, skin IDs) from the look source.  Previously this only
    changed RGB colors, which meant the character kept the template's hair
    style/body shape/eye type — the root cause of "style overpowers looks".
    """
    import copy

    custom = card.Custom.data
    hair = custom["hair"]
    face = custom["face"]
    body = custom["body"]

    # ── Hair: kind + full part data ──
    if "hair_kind" in look:
        hair["kind"] = look["hair_kind"]

    if "hair_parts" in look and look["hair_parts"]:
        existing_parts = hair.get("parts", [])
        look_parts = look["hair_parts"]

        # Ensure enough slots exist
        while len(existing_parts) < len(look_parts):
            existing_parts.append({})

        for i, lp in enumerate(look_parts):
            if i < len(existing_parts):
                existing_parts[i].clear()
                existing_parts[i].update(copy.deepcopy(lp))

        # Zero out extras
        for i in range(len(look_parts), len(existing_parts)):
            existing_parts[i].clear()
            existing_parts[i]["id"] = 0

    # ── Eyes: pupil ID + colors ──
    if "eye_id" in look:
        for p in face.get("pupil", []):
            p["id"] = look["eye_id"]

    if "eye_color" in look:
        ec = look["eye_color"]
        for p in face.get("pupil", []):
            p["baseColor"] = [float(ec[0]), float(ec[1]), float(ec[2]), 1.0]

    # ── Skin colors ──
    smc = look.get("skin_main_color", [1.0, 1.0, 1.0])
    ssc = look.get("skin_sub_color", [1.0, 1.0, 1.0])
    for target in (face, body):
        target["skinMainColor"] = [float(smc[0]), float(smc[1]), float(smc[2]), 1.0]
        target["skinSubColor"] = [float(ssc[0]), float(ssc[1]), float(ssc[2]), 1.0]

    # ── Skin IDs ──
    if "face_skin_id" in look:
        face["skinId"] = look["face_skin_id"]
    if "body_skin_id" in look:
        body["skinId"] = look["body_skin_id"]


def apply_style_traits(
    card: KoikatuCharaData,
    signature: Dict[str, Any],
    blend: float = 1.0,
) -> None:
    """Apply style traits to card in-place."""
    import numpy as np

    custom = card.Custom.data
    face = custom["face"]
    body = custom["body"]
    avg = signature.get("average_traits", {})
    cons = signature.get("consensus_features", {})

    # Face shape
    cur = np.array(face.get("shapeValueFace", []), dtype=np.float64)
    tgt = np.array(avg.get("shapeValueFace", []), dtype=np.float64)
    if len(tgt) > 0:
        ml = max(len(cur), len(tgt))
        cf = np.pad(cur, (0, ml - len(cur)))
        tf = np.pad(tgt, (0, ml - len(tgt)))
        face["shapeValueFace"] = (cf + blend * (tf - cf))[:ml].tolist()

    # Body shape
    cur = np.array(body.get("shapeValueBody", []), dtype=np.float64)
    tgt = np.array(avg.get("shapeValueBody", []), dtype=np.float64)
    if len(tgt) > 0:
        ml = max(len(cur), len(tgt))
        cb = np.pad(cur, (0, ml - len(cur)))
        tb = np.pad(tgt, (0, ml - len(tgt)))
        body["shapeValueBody"] = (cb + blend * (tb - cb))[:ml].tolist()

    # Discrete features
    for key in ("noseId", "lipLineId", "eyebrowId", "headId"):
        if key in cons:
            face[key] = cons[key]
    for key in ("bustWeight", "bustSoftness"):
        if key in cons:
            body[key] = cons[key]
    for key in ("pupilWidth", "pupilHeight", "pupilX", "pupilY"):
        if key in cons:
            face[key] = cons[key]


def set_defaults_nude(card: KoikatuCharaData) -> None:
    """Set all clothes to nude/skin-tone (id=0)."""
    coord = card.Coordinate.data
    slot = coord[0]
    clothes = slot["clothes"]
    parts = clothes["parts"]
    NUDE = [0.95, 0.85, 0.78, 1.0]

    for part in parts:
        part["id"] = 0
        part["emblemeId"] = 0
        part["emblemeId2"] = 0
        part["hideOpt"] = [False, False]
        part["sleevesType"] = 0
        for ci in part.get("colorInfo", []):
            ci["baseColor"] = list(NUDE)
            ci["pattern"] = 0
            ci["patternColor"] = list(NUDE)
            ci["tiling"] = [0.0, 0.0]


def inject_clothes(target: KoikatuCharaData, source: KoikatuCharaData) -> None:
    """Copy clothes from source card into target."""
    import copy
    src_clothes = source.Coordinate.data[0]["clothes"]
    tgt_clothes = target.Coordinate.data[0]["clothes"]
    tgt_parts = tgt_clothes["parts"]
    src_parts = src_clothes["parts"]

    for i, sp in enumerate(src_parts):
        if i < len(tgt_parts):
            tgt_parts[i].clear()
            tgt_parts[i].update(copy.deepcopy(sp))

    tgt_clothes.clear()
    tgt_clothes.update(copy.deepcopy(src_clothes))


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> int:
    """Execute the full build pipeline."""
    print("=" * 60)
    print("  Koikatsu Character Builder — Pipeline")
    print("=" * 60)

    # ── Step 1: Resolve look card(s) ──────────────────────────────────────
    print("\n[1/6] Resolving look card(s)...")
    look_path = args.look
    look_dir = args.look_dir

    # Handle glob
    if look_path and not look_path.exists():
        matches = list(Path(".").glob(str(look_path)))
        if matches:
            look_path = matches[0]
            print(f"  Glob matched: {look_path}")
        else:
            abs_matches = list(Path("/").glob(str(look_path)))
            if abs_matches:
                look_path = abs_matches[0]
            else:
                print(f"[run_build] ERROR: look card not found: {args.look}")
                return 1

    if not look_path or not look_path.exists():
        print(f"[run_build] ERROR: look card does not exist: {look_path}")
        return 1

    print(f"  Primary look: {look_path}")

    # Load primary look card — may be a KK character card or a regular image
    primary_look = None
    primary_card = None
    try:
        primary_card = KoikatuCharaData.load(str(look_path))
        primary_look = extract_look_traits(primary_card)
        print(f"  Loaded as KK character card: {look_path.name}")
    except Exception as e:
        print(f"  Not a KK character card ({look_path.name}), analyzing as image...")
        from PIL import Image
        import numpy as np
        from collections import Counter

        img = Image.open(look_path).convert('RGB')
        arr = np.array(img)
        h, w, _ = arr.shape

        # Skin tone: center region
        center = arr[h//4:3*h//4, w//4:3*w//4]
        skin_pixels = center.reshape(-1, 3)
        skin_mask = (
            (skin_pixels[:, 0] > 95) & (skin_pixels[:, 1] > 40) & (skin_pixels[:, 2] > 20) &
            (skin_pixels[:, 0] > skin_pixels[:, 1]) & (skin_pixels[:, 1] > skin_pixels[:, 2])
        )
        if skin_mask.sum() > 100:
            skin_color = skin_pixels[skin_mask].mean(axis=0)
        else:
            skin_color = center.reshape(-1, 3).mean(axis=0)

        # Hair: dark regions in top third
        top = arr[:h//3, :]
        dark_mask = (top.reshape(-1, 3)[:, 0] < 80) & (top.reshape(-1, 3)[:, 1] < 80) & (top.reshape(-1, 3)[:, 2] < 80)
        if dark_mask.sum() > 50:
            hair_color = top.reshape(-1, 3)[dark_mask].mean(axis=0)
        else:
            all_top = top.reshape(-1, 3)
            brightness = all_top.mean(axis=1)
            darkest_idx = np.argpartition(brightness, len(brightness)//5)[:len(brightness)//5]
            hair_color = all_top[darkest_idx].mean(axis=0)

        # Eye color: non-skin colored pixels in center band
        center_band = arr[h//3:2*h//3, w//3:2*w//3]
        pixels = center_band.reshape(-1, 3)
        non_skin = ~(
            (pixels[:, 0] > 95) & (pixels[:, 1] > 40) & (pixels[:, 2] > 20) &
            (pixels[:, 0] > pixels[:, 1]) & (pixels[:, 1] > pixels[:, 2])
        )
        colored = pixels[non_skin]
        if len(colored) > 100:
            quantized = (colored // 32).astype(np.uint8)
            tuples = [tuple(p) for p in quantized]
            common = Counter(tuples).most_common(5)
            eye_color = [0.3, 0.2, 0.1]  # fallback brown
            for q, count in common:
                r, g, b = q[0]*32+16, q[1]*32+16, q[2]*32+16
                saturation = max(r, g, b) - min(r, g, b)
                if saturation > 30 and not (r < 60 and g < 60 and b < 60):
                    eye_color = [r/255, g/255, b/255]
                    break
        else:
            eye_color = [0.3, 0.2, 0.1]

        primary_look = {
            "hair_color": [float(hair_color[0])/255, float(hair_color[1])/255, float(hair_color[2])/255],
            "eye_color": eye_color,
            "skin_main_color": [float(skin_color[0])/255, float(skin_color[1])/255, float(skin_color[2])/255],
            "skin_sub_color": [float(skin_color[0])/255, float(skin_color[1])/255, float(skin_color[2])/255],
            "hair_kind": 0,
            "hair_part_ids": [],
            "face_skin_id": 0,
            "body_skin_id": 0,
            "meta": {"source": look_path.name, "note": "extracted from image (not KK card)"},
        }
        print(f"  Extracted: hair={primary_look['hair_color']}, "
              f"eyes={primary_look['eye_color']}, skin={primary_look['skin_main_color']}")

    primary_look["meta"] = primary_look.get("meta", {})
    primary_look["meta"]["source"] = look_path.name

    # Merge with look-dir if provided
    if look_dir and look_dir.is_dir():
        extra_cards = list(look_dir.glob("*.png"))
        if extra_cards:
            print(f"  Merging {len(extra_cards)} additional look cards from {look_dir}")
            extra_traits = []
            for ec in extra_cards:
                try:
                    ec_card = KoikatuCharaData.load(str(ec))
                    et = extract_look_traits(ec_card)
                    et["meta"] = {"source": ec.name}
                    extra_traits.append(et)
                    print(f"    + {ec.name}")
                except Exception as e:
                    # Could be a regular image — extract traits via image analysis
                    try:
                        from PIL import Image as PILImage
                        import numpy as np
                        from collections import Counter

                        img = PILImage.open(ec).convert('RGB')
                        arr = np.array(img)
                        h, w, _ = arr.shape

                        center = arr[h//4:3*h//4, w//4:3*w//4]
                        skin_pixels = center.reshape(-1, 3)
                        skin_mask = (
                            (skin_pixels[:, 0] > 95) & (skin_pixels[:, 1] > 40) & (skin_pixels[:, 2] > 20) &
                            (skin_pixels[:, 0] > skin_pixels[:, 1]) & (skin_pixels[:, 1] > skin_pixels[:, 2])
                        )
                        if skin_mask.sum() > 100:
                            sc = skin_pixels[skin_mask].mean(axis=0)
                        else:
                            sc = center.reshape(-1, 3).mean(axis=0)

                        top = arr[:h//3, :]
                        dark_mask = (top.reshape(-1, 3)[:, 0] < 80) & (top.reshape(-1, 3)[:, 1] < 80) & (top.reshape(-1, 3)[:, 2] < 80)
                        if dark_mask.sum() > 50:
                            hc = top.reshape(-1, 3)[dark_mask].mean(axis=0)
                        else:
                            at = top.reshape(-1, 3)
                            b = at.mean(axis=1)
                            di = np.argpartition(b, len(b)//5)[:len(b)//5]
                            hc = at[di].mean(axis=0)

                        cb = arr[h//3:2*h//3, w//3:2*w//3]
                        px = cb.reshape(-1, 3)
                        ns = ~( (px[:, 0] > 95) & (px[:, 1] > 40) & (px[:, 2] > 20) &
                                (px[:, 0] > px[:, 1]) & (px[:, 1] > px[:, 2]) )
                        col = px[ns]
                        ec_eye = [0.3, 0.2, 0.1]
                        if len(col) > 100:
                            q = (col // 32).astype(np.uint8)
                            ts = [tuple(p) for p in q]
                            cm = Counter(ts).most_common(5)
                            for qq, cnt in cm:
                                rr, gg, bb = qq[0]*32+16, qq[1]*32+16, qq[2]*32+16
                                sat = max(rr, gg, bb) - min(rr, gg, bb)
                                if sat > 30 and not (rr < 60 and gg < 60 and bb < 60):
                                    ec_eye = [rr/255, gg/255, bb/255]
                                    break

                        et = {
                            "hair_color": [float(hc[0])/255, float(hc[1])/255, float(hc[2])/255],
                            "eye_color": ec_eye,
                            "skin_main_color": [float(sc[0])/255, float(sc[1])/255, float(sc[2])/255],
                            "skin_sub_color": [float(sc[0])/255, float(sc[1])/255, float(sc[2])/255],
                            "hair_kind": 0, "hair_part_ids": [],
                            "face_skin_id": 0, "body_skin_id": 0,
                            "meta": {"source": ec.name, "note": "image-extracted"},
                        }
                        extra_traits.append(et)
                        print(f"    + {ec.name} (image-extracted)")
                    except Exception as e2:
                        print(f"    - {ec.name}: {e} / {e2}")
            if extra_traits:
                all_traits = [primary_look] + extra_traits
                primary_look = merge_look_traits(all_traits)
                print(f"  Merged look: hair={primary_look['hair_color']}, "
                      f"eyes={primary_look['eye_color']}, skin={primary_look['skin_main_color']}")
        else:
            print(f"  No .png cards in look dir {look_dir}")

    # ── Step 2: Analyze style directory ────────────────────────────────────
    print("\n[2/6] Analyzing style directory...")
    style_dir = args.style
    if not style_dir.is_dir():
        print(f"[run_build] ERROR: style dir not found: {style_dir}")
        return 1

    style_sig = style_group_signature(style_dir)
    print(f"  Style: {style_sig['member_count']} members, "
          f"internal sim={style_sig['internal_similarity']:.3f}")

    # ── Step 3: Build the card ────────────────────────────────────────────
    print("\n[3/6] Building character card...")

    # Choose base card: source-card if given, else look card
    base_path = args.source_card if args.source_card and args.source_card.exists() else look_path
    print(f"  Base template: {base_path}")

    card = KoikatuCharaData.load(str(base_path))

    # Apply look
    apply_look_traits(card, primary_look)
    print("  Look traits applied")

    # Apply style
    if style_sig["member_count"] > 0:
        apply_style_traits(card, style_sig, blend=args.style_blend)
        print(f"  Style traits applied (blend={args.style_blend})")
    else:
        print("  No style traits (empty style dir)")

    # Handle clothes
    if args.keep_clothes:
        print("  Clothes: keeping original from look card")
    elif args.clothes_from and args.clothes_from.exists():
        src = KoikatuCharaData.load(str(args.clothes_from))
        inject_clothes(card, src)
        print(f"  Clothes: injected from {args.clothes_from.name}")
    else:
        set_defaults_nude(card)
        print("  Clothes: set to default nude (id=0)")

    # Metadata override
    if args.name or args.nickname or args.lastname:
        param = card.Parameter.data
        if args.name:
            param["firstname"] = args.name
        if args.nickname:
            param["nickname"] = args.nickname
        if args.lastname:
            param["lastname"] = args.lastname
        print(f"  Metadata overridden: name={args.name or '?'}, nick={args.nickname or '?'}")

    # Save
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(str(output_path))
    sz = output_path.stat().st_size
    print(f"\n  Saved: {output_path} ({sz} bytes)")

    # Verify
    print("\n  Verification:")
    v = KoikatuCharaData.load(str(output_path))
    vlook = extract_look_traits(v)
    print(f"    Hair:  {vlook['hair_color']}")
    print(f"    Eyes:  {vlook['eye_color']}")
    print(f"    Skin:  {vlook['skin_main_color']}")
    clothes = v.Coordinate.data[0]["clothes"]["parts"]
    print(f"    Clothes: {len(clothes)} parts, ids={[p['id'] for p in clothes]}")

    # ── Step 4: Game automation (if requested) ────────────────────────────
    if args.launch_game or args.ensure_cm or args.load_in_game:
        print("\n[4/6] Game automation...")
        try:
            from game_manager import GameSession
            sess = GameSession()

            if args.launch_game:
                print("  Ensuring game is running...")
                ok = sess.ensure_character_maker()
                if not ok:
                    print("[run_build] WARNING: game may not be ready")

            if args.ensure_cm:
                print("  Ensuring Character Maker is open...")
                # Already handled by ensure_character_maker above

            if args.load_in_game:
                print("  Loading card in Character Maker via UI automation...")
                try:
                    from ui_automation import run_action_sequence, load_action_table
                    table = load_action_table()
                    
                    # Build a custom load sequence
                    load_seq = {
                        "actions": [
                            {"type": "click", "x": 100, "y": 200,
                             "description": "Click 'Load Character' button"},
                            {"type": "delay", "ms": 1000,
                             "description": "Wait for character list"},
                            {"type": "select_folder", "folder": args.load_folder,
                             "description": f"Select folder '{args.load_folder}'"},
                            {"type": "search", "text": "",
                             "description": "No search filter"},
                            {"type": "select_card", "index": 0,
                             "description": "Select first card (our newly built one)"},
                            {"type": "set_load_options",
                             "face": True, "body": True, "hair": True,
                             "character_info": True,
                             "clothing_sets": args.keep_clothes,
                             "description": "Load options"},
                            {"type": "click", "x": 1500, "y": 850,
                             "description": "Click 'Load' button"},
                            {"type": "delay", "ms": 3000,
                             "description": "Wait for card to load"},
                        ]
                    }
                    
                    print("  Executing load sequence...")
                    success = run_action_sequence("load_character", table)
                    if not success:
                        print("[run_build] WARNING: UI automation had issues")
                except ImportError:
                    print("[run_build] WARNING: ui_automation.py not available — skipping in-game load")
        except ImportError as e:
            print(f"[run_build] WARNING: {e} — skipping game automation")

    # ── Step 5: Close game if requested ───────────────────────────────────
    if args.close_game:
        print("\n[5/6] Closing game...")
        try:
            from game_manager import GameSession
            sess = GameSession()
            sess.close()
            print("  Game closed")
        except Exception as e:
            print(f"  [warn] Could not close game: {e}")

    # ── Step 6: Summary ────────────────────────────────────────────────────
    print("\n[6/6] Summary")
    print(f"  Output: {output_path} ({sz} bytes)")
    print(f"  Look:   hair={primary_look['hair_color']}, eyes={primary_look['eye_color']}")
    print(f"  Style:  {style_sig['member_count']} members, sim={style_sig['internal_similarity']:.3f}")
    print(f"  Clothes: {'original' if args.keep_clothes else 'nude' if not args.clothes_from else 'injected'}")

    print("\n" + "=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)

    return 0


def main() -> int:
    args = parse_args()
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
