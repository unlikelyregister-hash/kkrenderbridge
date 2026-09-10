#!/usr/bin/env python3
"""
Card builder — combine a look reference + style reference(s) into a character card.

Look folder (one or more images):
  - Drives surface traits: hair color, eye color, skin tone, hair style
  - WD-tagged to extract color/attribute buckets

Style folder (one subfolder = one style, containing multiple cards):
  - Drives structural traits: face shape, body shape, face features
  - The multiple cards in a style folder are compared to find shared slider
    ranges (similarities) — the style "signature"

Output:
  - A .kkpe/.png card with:
    - Look traits applied (hair color, eye color, skin tone, hair parts)
    - Style traits applied (shapeValueFace, shapeValueBody, face feature IDs)
    - Default clothes (id=0, nude/skin-tone) — clothing is NOT inherited
    - Metadata from the look reference (name, personality, etc.)

Usage:
    python card_builder.py \\
        --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\IA2\\Sarah\\Cards\\*.png" \\
        --style "C:\\Games\\Koikatsu\\UserData\\chara\\female\\[Community]\\style_group_1" \\
        --output my_character.kkpe

    python card_builder.py \\
        --look "look1.png" \\
        --style "styles/style_A/" \\
        --output out/kcharacter.kkpe
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure kkloader is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kkloader import KoikatuCharaData

# Local imports
from clothing.decouple import (
    set_defaults_nude,
    strip_clothes,
    inject_clothes,
)

# ── paths ───────────────────────────────────────────────────────────────────

# Example source cards for testing
SARAH_CARD = Path(
    r"C:\Games\Koikatsu\UserData\chara\female\IA2\Sarah\Cards"
    r"\Koikatu_F_20221020093900740_Sarah.png"
)
COMMUNITY_398582 = Path(
    r"C:\Games\Koikatsu\UserData\chara\female\[Community]\KK_398582.png"
)
COMMUNITY_319725 = Path(
    r"C:\Games\Koikatsu\UserData\chara\female\[Community]\KK_319725.png"
)


# ── trait extraction ─────────────────────────────────────────────────────────

def extract_look_traits(card: KoikatuCharaData) -> Dict[str, Any]:
    """Extract surface-level look traits from a card for reuse.

    Returns a dict with hashable trait values that describe the 'look':
    - hair_color: average RGB of all hair parts
    - eye_color: pupil baseColor
    - skin_main_color: skinMainColor
    - skin_sub_color: skinSubColor
    - hair_kind: hair style kind index
    - hair_part_ids: list of hair part asset IDs
    - face_skin_id: face skin texture id
    - body_skin_id: body skin texture id
    - meta: additional metadata for reference
    """
    custom = card.Custom.data
    hair = custom["hair"]
    face = custom["face"]
    body = custom["body"]

    # Hair color — average over non-zero parts
    hair_colors = []
    for part in hair.get("parts", []):
        bc = part.get("baseColor")
        if bc and part.get("id", 0) != 0:
            hair_colors.append(bc[:3])  # RGB only
    hair_color = (
        [sum(c) / len(c) for c in zip(*hair_colors)] if hair_colors else [1.0, 1.0, 1.0]
    )

    # Eye color + eye ID
    pupil = face.get("pupil", [])
    eye_color = [1.0, 1.0, 1.0]
    eye_id = 0
    if pupil:
        bc = pupil[0].get("baseColor")
        if bc:
            eye_color = list(bc[:3])
        eye_id = pupil[0].get("id", 0)

    # Skin colors
    skin_main = list(face.get("skinMainColor", body.get("skinMainColor", [1.0, 1.0, 1.0, 1.0]))[:3])
    skin_sub = list(face.get("skinSubColor", body.get("skinSubColor", [1.0, 1.0, 1.0, 1.0]))[:3])

    # Hair kind and full part data
    hair_kind = hair.get("kind", 0)

    hair_parts = []
    for part in hair.get("parts", []):
        if part and part.get("id", 0) != 0:
            hair_parts.append({
                "id": part["id"],
                "baseColor": list(part.get("baseColor", [1.0, 1.0, 1.0, 1.0])),
                "startColor": list(part.get("startColor", [1.0, 1.0, 1.0, 1.0])),
                "endColor": list(part.get("endColor", [1.0, 1.0, 1.0, 1.0])),
            })

    return {
        "hair_color": hair_color,
        "eye_color": eye_color,
        "eye_id": eye_id,
        "skin_main_color": skin_main,
        "skin_sub_color": skin_sub,
        "hair_kind": hair_kind,
        "hair_parts": hair_parts,
        "hair_part_ids": [p.get("id", 0) for p in hair.get("parts", [])],
        "face_skin_id": face.get("skinId", 0),
        "body_skin_id": body.get("skinId", 0),
        "meta": {},  # placeholder for additional per-card metadata
    }


def merge_look_traits(traits_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple look trait sets into one averaged set.

    When multiple look images are provided, this averages their traits
    (hair color, eye color, skin tone) to create a representative look.
    Hair kind and part IDs are taken from the first card.

    Returns a single merged look trait dict.
    """
    if not traits_list:
        return {}

    if len(traits_list) == 1:
        return traits_list[0]

    import numpy as np

    # Average RGB values across all cards
    n = len(traits_list)

    def avg_rgb(key: str) -> List[float]:
        vals = [t[key] for t in traits_list if key in t and len(t[key]) >= 3]
        if not vals:
            return [1.0, 1.0, 1.0]
        arr = np.array(vals, dtype=np.float64)
        return arr.mean(axis=0).tolist()[:3]

    merged = {
        "hair_color": avg_rgb("hair_color"),
        "eye_color": avg_rgb("eye_color"),
        "skin_main_color": avg_rgb("skin_main_color"),
        "skin_sub_color": avg_rgb("skin_sub_color"),
        # Take from first card (hair kind/parts should be consistent within a look)
        "hair_kind": traits_list[0].get("hair_kind", 0),
        "hair_parts": traits_list[0].get("hair_parts", []),
        "hair_part_ids": traits_list[0].get("hair_part_ids", []),
        "face_skin_id": traits_list[0].get("face_skin_id", 0),
        "body_skin_id": traits_list[0].get("body_skin_id", 0),
        "meta": {
            "source_count": n,
            "sources": [t.get("meta", {}).get("source", "?") for t in traits_list],
        },
    }
    return merged


def extract_style_traits(card: KoikatuCharaData) -> Dict[str, Any]:
    """Extract structural style traits from a card.

    These define the face/body shape and feature choices that make a character
    belong to a particular 'style' or body type.

    Returns:
    - shapeValueFace: list of face shape sliders
    - shapeValueBody: list of body shape sliders
    - noseId, lipLineId, eyebrowId: face feature IDs
    - headId: head mesh ID
    - bustWeight, bustSoftness: body features
    - pupilWidth, pupilHeight: eye openness
    """
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


def style_similarity(traits_a: Dict[str, Any], traits_b: Dict[str, Any]) -> float:
    """Compute similarity between two style trait sets.

    Compares shapeValueFace and shapeValueBody vectors (cosine similarity)
    plus discrete feature IDs (exact match bonus).

    Returns 0.0–1.0.
    """
    import numpy as np

    # Face shape similarity
    face_a = np.array(traits_a.get("shapeValueFace", []), dtype=np.float64)
    face_b = np.array(traits_b.get("shapeValueFace", []), dtype=np.float64)
    if len(face_a) == 0 or len(face_b) == 0:
        face_sim = 0.0
    else:
        # Pad to same length
        max_len = max(len(face_a), len(face_b))
        fa = np.pad(face_a, (0, max_len - len(face_a)))
        fb = np.pad(face_b, (0, max_len - len(face_b)))
        dot = np.dot(fa, fb)
        norm = np.linalg.norm(fa) * np.linalg.norm(fb)
        face_sim = float(dot / norm) if norm > 1e-9 else 0.0

    # Body shape similarity
    body_a = np.array(traits_a.get("shapeValueBody", []), dtype=np.float64)
    body_b = np.array(traits_b.get("shapeValueBody", []), dtype=np.float64)
    if len(body_a) == 0 or len(body_b) == 0:
        body_sim = 0.0
    else:
        max_len = max(len(body_a), len(body_b))
        ba = np.pad(body_a, (0, max_len - len(body_a)))
        bb = np.pad(body_b, (0, max_len - len(body_b)))
        dot = np.dot(ba, bb)
        norm = np.linalg.norm(ba) * np.linalg.norm(bb)
        body_sim = float(dot / norm) if norm > 1e-9 else 0.0

    # Discrete feature match bonus
    feature_match = 0.0
    for key in ("noseId", "lipLineId", "eyebrowId", "headId"):
        if traits_a.get(key) == traits_b.get(key):
            feature_match += 0.05

    # Weight: face shape is more important than body for 'style'
    return 0.6 * face_sim + 0.3 * body_sim + min(feature_match, 0.2)


def style_group_signature(style_dir: Path) -> Dict[str, Any]:
    """Analyze all cards in a style directory to find the shared style signature.

    Loads each .png card, extracts style traits, computes pairwise similarity,
    and returns:
    - average_traits: element-wise average of shapeValueFace and shapeValueBody
    - consensus_features: most common noseId, lipLineId, etc.
    - internal_similarity: average pairwise similarity (how cohesive the group is)
    - member_count: number of cards analyzed
    - member_paths: list of card paths
    """
    import numpy as np

    cards = list(style_dir.glob("*.png"))
    if not cards:
        print(f"[style] WARNING: no .png cards in {style_dir}")
        return {
            "average_traits": {},
            "consensus_features": {},
            "internal_similarity": 0.0,
            "member_count": 0,
            "member_paths": [],
        }

    print(f"[style] Analyzing {len(cards)} cards in {style_dir.name}...")

    all_traits = []
    for card_path in cards:
        try:
            raw = card_path.read_bytes()
            try:
                card = KoikatuCharaData.load(raw)
            except TypeError:
                # Some cards need str path instead of bytes
                card = KoikatuCharaData.load(str(card_path))
            t = extract_style_traits(card)
            t["_path"] = str(card_path)
            all_traits.append(t)
        except Exception as e:
            print(f"  [style] skipped {card_path.name}: {e}")

    if not all_traits:
        print(f"[style] No cards could be loaded from {style_dir}")
        return {
            "average_traits": {},
            "consensus_features": {},
            "internal_similarity": 0.0,
            "member_count": 0,
            "member_paths": [],
        }

    # Pairwise similarity
    n = len(all_traits)
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            sim = style_similarity(all_traits[i], all_traits[j])
            sims.append(sim)

    internal_sim = sum(sims) / len(sims) if sims else 0.0
    print(f"  Internal similarity: {internal_sim:.4f} ({len(sims)} pairs)")

    # Average shapeValueFace and shapeValueBody
    face_arrays = [np.array(t["shapeValueFace"], dtype=np.float64) for t in all_traits]
    body_arrays = [np.array(t["shapeValueBody"], dtype=np.float64) for t in all_traits]

    max_face_len = max(len(a) for a in face_arrays)
    max_body_len = max(len(a) for a in body_arrays)

    avg_face = np.zeros(max_face_len)
    avg_body = np.zeros(max_body_len)
    for a in face_arrays:
        avg_face[:len(a)] += a
    for a in body_arrays:
        avg_body[:len(a)] += a
    avg_face /= n
    avg_body /= n

    # Consensus discrete features (most common value)
    from collections import Counter
    consensus = {}
    for key in ("noseId", "lipLineId", "eyebrowId", "headId", "bustWeight", "bustSoftness"):
        vals = [t.get(key) for t in all_traits if t.get(key) is not None]
        if vals:
            counter = Counter(vals)
            consensus[key] = counter.most_common(1)[0][0]

    return {
        "average_traits": {
            "shapeValueFace": avg_face.tolist(),
            "shapeValueBody": avg_body.tolist(),
        },
        "consensus_features": consensus,
        "internal_similarity": internal_sim,
        "member_count": n,
        "member_paths": [t["_path"] for t in all_traits],
    }


def apply_look_traits(
    card: KoikatuCharaData,
    look: Dict[str, Any],
) -> None:
    """Apply look traits to a card's Custom block (in-place).

    Copies BOTH surface colors AND structural features (hair kind, hair part
    IDs, eye pupil ID, skin IDs) from the look source.  Previously this only
    changed RGB colors, which meant the character kept the template's hair
    style/eye type — the root cause of "style overpowers looks".
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

        while len(existing_parts) < len(look_parts):
            existing_parts.append({})

        for i, lp in enumerate(look_parts):
            if i < len(existing_parts):
                existing_parts[i].clear()
                existing_parts[i].update(copy.deepcopy(lp))

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
    face["skinMainColor"] = [float(smc[0]), float(smc[1]), float(smc[2]), 1.0]
    face["skinSubColor"] = [float(ssc[0]), float(ssc[1]), float(ssc[2]), 1.0]
    body["skinMainColor"] = [float(smc[0]), float(smc[1]), float(smc[2]), 1.0]
    body["skinSubColor"] = [float(ssc[0]), float(ssc[1]), float(ssc[2]), 1.0]

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
    """Apply style signature to a card's Custom block (in-place).

    blend=1.0 → replace current sliders with the style average
    blend=0.5 → move halfway from current toward style average
    """
    import numpy as np

    custom = card.Custom.data
    face = custom["face"]
    body = custom["body"]

    avg = signature.get("average_traits", {})
    cons = signature.get("consensus_features", {})

    # Face shape
    cur_face = np.array(face.get("shapeValueFace", []), dtype=np.float64)
    tgt_face = np.array(avg.get("shapeValueFace", []), dtype=np.float64)
    if len(tgt_face) > 0:
        max_len = max(len(cur_face), len(tgt_face))
        cf = np.pad(cur_face, (0, max_len - len(cur_face)))
        tf = np.pad(tgt_face, (0, max_len - len(tgt_face)))
        new_face = cf + blend * (tf - cf)
        face["shapeValueFace"] = new_face[:max_len].tolist()

    # Body shape
    cur_body = np.array(body.get("shapeValueBody", []), dtype=np.float64)
    tgt_body = np.array(avg.get("shapeValueBody", []), dtype=np.float64)
    if len(tgt_body) > 0:
        max_len = max(len(cur_body), len(tgt_body))
        cb = np.pad(cur_body, (0, max_len - len(cur_body)))
        tb = np.pad(tgt_body, (0, max_len - len(tgt_body)))
        new_body = cb + blend * (tb - cb)
        body["shapeValueBody"] = new_body[:max_len].tolist()

    # Discrete features
    for key in ("noseId", "lipLineId", "eyebrowId", "headId"):
        if key in cons:
            if key in ("noseId", "lipLineId", "eyebrowId", "headId"):
                face[key] = cons[key]

    # Body features
    for key in ("bustWeight", "bustSoftness"):
        if key in cons:
            body[key] = cons[key]

    # Eye openness
    for key in ("pupilWidth", "pupilHeight", "pupilX", "pupilY"):
        if key in cons:
            face[key] = cons[key]


# ── main build ──────────────────────────────────────────────────────────────

def build_card(
    look_card_path: Path,
    style_dir: Path,
    output_path: Path,
    use_default_clothes: bool = True,
    clothes_source: Optional[Path] = None,
    style_blend: float = 1.0,
    metadata_override: Optional[Dict[str, Any]] = None,
    look_dir: Optional[Path] = None,   # NEW: optional directory of look cards
) -> Dict[str, Any]:
    """Build a character card from a look reference + style directory.

    Args:
        look_card_path:   A .png card that defines the look (hair, eyes, skin).
        style_dir:        A directory containing multiple .png cards that share
                          a body/face style.  The average of their sliders becomes
                          the target style.
        output_path:      Where to write the resulting card.
        use_default_clothes: If True, replace clothes with default/nude (id=0).
        clothes_source:   If set, inject clothes from this card instead of defaults.
        style_blend:      0.0–1.0 how much to blend toward the style average.
        metadata_override: Optional dict to replace Parameter block fields.
        look_dir:         Optional directory of additional look cards to merge.
                          When provided, traits from all cards in this directory
                          are averaged with the primary look card.

    Returns a report dict with build details.
    """
    print(f"[build] Look card:   {look_card_path}")
    print(f"[build] Look dir:    {look_dir or '(none)'}")
    print(f"[build] Style dir:   {style_dir}")
    print(f"[build] Output:      {output_path}")
    print(f"[build] Clothes:     {'default nude' if use_default_clothes else 'keep original'}"
          f"{' + injected from ' + str(clothes_source) if clothes_source else ''}")
    print(f"[build] Style blend: {style_blend}")

    # ── Load primary look card ─────────────────────────────────────────────
    look_card = KoikatuCharaData.load(str(look_card_path))
    look_traits = extract_look_traits(look_card)
    look_traits["meta"]["source"] = look_card_path.name
    print(f"[build] Primary look traits: hair={look_traits['hair_color']}, "
          f"eyes={look_traits['eye_color']}, skin={look_traits['skin_main_color']}")

    # ── Optionally merge with additional look cards ────────────────────────
    if look_dir and look_dir.is_dir():
        extra_cards = list(look_dir.glob("*.png"))
        if extra_cards:
            print(f"[build] Merging {len(extra_cards)} additional look cards from {look_dir}")
            extra_traits = []
            for ec in extra_cards:
                try:
                    ec_card = KoikatuCharaData.load(str(ec))
                    et = extract_look_traits(ec_card)
                    et["meta"]["source"] = ec.name
                    extra_traits.append(et)
                    print(f"  + {ec.name}")
                except Exception as e:
                    print(f"  - skipped {ec.name}: {e}")
            
            if extra_traits:
                all_traits = [look_traits] + extra_traits
                look_traits = merge_look_traits(all_traits)
                print(f"[build] Merged look traits: hair={look_traits['hair_color']}, "
                      f"eyes={look_traits['eye_color']}, skin={look_traits['skin_main_color']}")
        else:
            print(f"[build] No .png cards found in look dir {look_dir}")

    # ── Analyze style directory ────────────────────────────────────────────
    style_sig = style_group_signature(style_dir)
    if style_sig["member_count"] == 0:
        print("[build] WARNING: no style cards loaded — proceeding without style")
    else:
        print(f"[build] Style signature: {style_sig['member_count']} members, "
              f"internal sim={style_sig['internal_similarity']:.3f}")

    # ── Work on a copy of the look card ─────────────────────────────────────
    # We use the look card as the base (it has the image data + blockdata),
    # then overlay style traits and handle clothes.
    card = KoikatuCharaData.load(str(look_card_path))

    # ── Apply look traits (hair, eyes, skin) ──────────────────────────────
    apply_look_traits(card, look_traits)
    print("[build] Look traits applied")

    # ── Apply style traits (face/body shape) ──────────────────────────────
    if style_sig["member_count"] > 0:
        apply_style_traits(card, style_sig, blend=style_blend)
        print("[build] Style traits applied")
    else:
        print("[build] No style traits to apply")

    # ── Handle clothes ──────────────────────────────────────────────────────
    if use_default_clothes:
        if clothes_source and clothes_source.exists():
            # Load source, inject
            src = KoikatuCharaData.load(str(clothes_source))
            inject_clothes(card, src)
            print(f"[build] Clothes injected from {clothes_source.name}")
        else:
            # Default nude
            set_defaults_nude(card)
            print("[build] Clothes set to default nude (id=0)")
    # else: keep original clothes from look card

    # ── Optional: clear accessories if we want clean slate ─────────────────
    # (Leave makeup as-is for now)

    # ── Parameter block ─────────────────────────────────────────────────────
    param = card.Parameter.data
    if metadata_override:
        param.update(metadata_override)
        print(f"[build] Metadata overridden with {len(metadata_override)} fields")
    else:
        # Use look card's own metadata as-is
        print("[build] Using look card's metadata as-is")

    # ── Save ────────────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card.save(str(output_path))
    sz = output_path.stat().st_size
    print(f"[build] Saved: {output_path} ({sz} bytes)")

    # ── Verify ──────────────────────────────────────────────────────────────
    print("[build] Verifying...")
    v = KoikatuCharaData.load(str(output_path))
    vt = extract_look_traits(v)
    print(f"  Hair color: {vt['hair_color']}")
    print(f"  Eye color:  {vt['eye_color']}")
    print(f"  Skin:       {vt['skin_main_color']}")
    print(f"  Hair kind:  {vt['hair_kind']}")

    if style_sig["member_count"] > 0:
        st = extract_style_traits(v)
        print(f"  Face shape (first 5): {st['shapeValueFace'][:5]}")
        print(f"  Body shape (first 5): {st['shapeValueBody'][:5]}")

    clothes = v.Coordinate.data[0]["clothes"]["parts"]
    print(f"  Clothes: {len(clothes)} parts, ids={[p['id'] for p in clothes]}")

    return {
        "output": str(output_path),
        "size": sz,
        "look_traits": look_traits,
        "style_signature": style_sig,
        "clothes_ids": [p["id"] for p in clothes],
        "metadata": card.Parameter.data,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a Koikatsu character card from look + style references",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build from Sarah (look) + a style group folder
  python card_builder.py \\
      --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\IA2\\Sarah\\Cards\\*.png" \\
      --style "C:\\Games\\Koikatsu\\UserData\\chara\\female\\[Community]\\my_style_group" \\
      --output out/test_card.kkpe

  # Build from a single look card with default clothes
  python card_builder.py \\
      --look "C:\\Games\\Koikatsu\\UserData\\chara\\female\\[Community]\\KK_398582.png" \\
      --style "styles/slender/" \\
      --output out/slender_character.kkpe

  # Build with clothes injected from another card
  python card_builder.py \\
      --look "look_card.png" \\
      --style "styles/athletic/" \\
      --clothes-from "C:\\Games\\Koikatsu\\UserData\\chara\\female\\IA2\\Sarah\\Cards\\*.png" \\
      --output out/full_outfit_card.kkpe

  # Keep original clothes (don't strip)
  python card_builder.py \\
      --look "look_card.png" \\
      --style "styles/round_face/" \\
      --keep-clothes \\
      --output out/look_with_style.kkpe
""",
    )

    ap.add_argument(
        "--look", "-l",
        type=Path,
        required=False,
        default=None,
        help="Look reference: a .png card, glob pattern, or directory of cards (e.g. 'sarah.png', '*.png', or 'looks/')",
    )
    ap.add_argument(
        "--look-dir", "-ld",
        type=Path,
        default=None,
        help="Directory containing multiple look reference cards (alternative to --look)",
    )
    ap.add_argument(
        "--style", "-s",
        type=Path,
        required=True,
        help="Style directory containing multiple .png cards that share a body/face style",
    )
    ap.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output card path (.kkpe or .png)",
    )
    ap.add_argument(
        "--clothes-from", "-c",
        type=Path,
        default=None,
        help="Inject clothes from this card instead of default nude",
    )
    ap.add_argument(
        "--keep-clothes",
        action="store_true",
        default=False,
        help="Keep the look card's original clothes (don't strip or replace)",
    )
    ap.add_argument(
        "--style-blend",
        type=float,
        default=1.0,
        help="How much to blend toward style average (0.0–1.0, default 1.0)",
    )
    ap.add_argument(
        "--name",
        type=str,
        default=None,
        help="Override character name (Parameter.firstname)",
    )
    ap.add_argument(
        "--nickname",
        type=str,
        default=None,
        help="Override nickname (Parameter.nickname)",
    )

    args = ap.parse_args()

    # Resolve look path (handle glob)
    look_path = args.look
    look_dir = args.look_dir
    
    if look_path is None and look_dir is None:
        print("[build] ERROR: need either --look or --look-dir")
        return 1
    
    if look_path is not None:
        if look_path.exists():
            # Single file
            pass
        else:
            # Try as glob
            matches = list(Path(".").glob(str(look_path)))
            if matches:
                look_path = matches[0]
                print(f"[build] Look glob matched: {look_path}")
            else:
                # Try absolute glob
                abs_matches = list(Path("/").glob(str(look_path)))
                if abs_matches:
                    look_path = abs_matches[0]
                else:
                    print(f"[build] ERROR: cannot find look card: {args.look}")
                    return 1
    
    # Validate style dir
    if not args.style.is_dir():
        print(f"[build] ERROR: style directory not found: {args.style}")
        return 1
    
    # Metadata override
    meta = {}
    if args.name:
        meta["firstname"] = args.name
    if args.nickname:
        meta["nickname"] = args.nickname
    
    # Clothes handling
    use_defaults = not args.keep_clothes
    clothes_src = args.clothes_from if args.clothes_from and args.clothes_from.exists() else None
    if args.clothes_from and not args.clothes_from.exists():
        print(f"[build] WARNING: clothes-from path not found: {args.clothes_from}")
    
    report = build_card(
        look_card_path=look_path,
        style_dir=args.style,
        output_path=args.output,
        use_default_clothes=use_defaults,
        clothes_source=clothes_src,
        style_blend=args.style_blend,
        metadata_override=meta if meta else None,
        look_dir=look_dir,
    )

    print(f"\n[build] Done. Report saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
