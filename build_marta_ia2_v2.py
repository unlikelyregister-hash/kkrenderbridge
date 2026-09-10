#!/usr/bin/env python
"""
build_marta_ia2_v2.py — Build Marta with correct looks + IA2_flat style.

Approach (per user instruction):
  1. Look at ALL cards in styles/IA2_flat, find similarities → define baseline.
  2. Use base_1.png as the template.
  3. Edit base_1 to make it look like Marta (hair, skin, eyes from Marta_Y.png).
  4. Apply IA2_flat style (body/facial shape sliders from baseline).
  5. Output: .kkpe + .png, both in out/ and copied to kkRenderBridge.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kkloader import KoikatuCharaData

WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
OUT_DIR = WORKSPACE / "out"
KKRB = Path(r"C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge")

BASE1_PATH = KKRB / "base_1.png"
MARTA_Y_PATH = KKRB / "Marta_Y.png"
STYLE_DIR = WORKSPACE / "styles" / "IA2_flat"

OUT_KKPE = OUT_DIR / "marta_ia2_v2.kkpe"
OUT_PNG = OUT_DIR / "marta_ia2_v2.png"


# ── IA2_flat style baseline (pre-computed by analyze_ia2_flat.py) ──────────
BASELINE_PATH = WORKSPACE / "out" / "ia2_flat_baseline.json"


def load_baseline():
    """Load pre-computed IA2_flat baseline from JSON."""
    with open(BASELINE_PATH) as f:
        return json.load(f)


def build():
    print("=" * 70)
    print("BUILD: Marta IA2_flat v2")
    print("=" * 70)

    # ── 1. Load template (base_1) ──────────────────────────────────────────
    print(f"\n[1] Loading template: {BASE1_PATH}")
    card = KoikatuCharaData.load(str(BASE1_PATH))
    cd = card.Custom.data
    print(f"    Template hair kind: {cd['hair']['kind']}")
    print(f"    Template eye id:    {cd['face']['pupil'][0]['id']}")
    print(f"    Template skin:      {cd['body']['skinMainColor'][:3]}")

    # ── 2. Load Marta_Y as LOOK source ─────────────────────────────────────
    print(f"\n[2] Loading look source: {MARTA_Y_PATH}")
    marta = KoikatuCharaData.load(str(MARTA_Y_PATH))
    md = marta.Custom.data

    # Extract Marta's EXACT game values
    marta_look = {
        "hair_kind": md["hair"]["kind"],
        "hair_parts": [],
        "eye_id": md["face"]["pupil"][0]["id"],
        "eye_color": list(md["face"]["pupil"][0]["baseColor"][:3]),
        "skin_main_color": list(md["body"]["skinMainColor"][:3]),
        "skin_sub_color": list(md["body"]["skinSubColor"][:3]),
        "face_skin_id": md["face"].get("skinId", 0),
        "body_skin_id": md["body"].get("skinId", 0),
    }
    for p in md["hair"]["parts"]:
        if p.get("id", 0) != 0:
            marta_look["hair_parts"].append({
                "id": p["id"],
                "baseColor": list(p.get("baseColor", [1.0, 1.0, 1.0, 1.0])),
                "startColor": list(p.get("startColor", [1.0, 1.0, 1.0, 1.0])),
                "endColor": list(p.get("endColor", [1.0, 1.0, 1.0, 1.0])),
            })

    print(f"    Marta hair kind:  {marta_look['hair_kind']}")
    print(f"    Marta hair parts: {[p['id'] for p in marta_look['hair_parts']]}")
    print(f"    Marta hair color: {[round(c, 3) for c in marta_look['hair_parts'][0]['baseColor'][:3]]}")
    print(f"    Marta eye id:     {marta_look['eye_id']}")
    print(f"    Marta eye color:  {[round(c, 3) for c in marta_look['eye_color']]}")
    print(f"    Marta skin main:  {[round(c, 3) for c in marta_look['skin_main_color']]}")
    print(f"    Marta skin sub:   {[round(c, 3) for c in marta_look['skin_sub_color']]}")

    # ── 3. Load IA2_flat style baseline ─────────────────────────────────────
    print(f"\n[3] Loading IA2_flat style baseline")
    bl = load_baseline()
    print(f"    Baseline from {bl['member_count']} IA2_flat cards")
    print(f"    Internal similarity: {bl['internal_sim']:.4f}")
    print(f"    noseId=     {bl['noseId']}")
    print(f"    lipLineId=  {bl['lipLineId']}")
    print(f"    headId=     {bl['headId']}")
    print(f"    eyebrowId=  {bl['eyebrowId']}")
    print(f"    pupilW=     {bl['pupilWidth']:.2f}")
    print(f"    pupilH=     {bl['pupilHeight']:.2f}")
    print(f"    pupilX=     {bl['pupilX']:.2f}")
    print(f"    pupilY=     {bl['pupilY']:.2f}")
    print(f"    bustWeight= {bl['bustWeight']:.2f}")
    print(f"    bustSoftness={bl['bustSoftness']:.2f}")
    print(f"    areolaSize= {bl['areolaSize']:.2f}")
    print(f"    face shapeValueFace: {len(bl['dominant_face'])} dims (first 8: {[round(v,3) for v in bl['dominant_face'][:8]]})")
    print(f"    body shapeValueBody: {len(bl['dominant_body'])} dims (first 6: {[round(v,3) for v in bl['dominant_body'][:6]]})")

    # ── 4. Apply LOOK to template (hair, eyes, skin from Marta_Y) ─────────
    print(f"\n[4] Applying LOOK (Marta_Y values) to template")

    # Hair kind
    cd["hair"]["kind"] = marta_look["hair_kind"]

    # Hair parts — replace entirely with Marta's parts
    # First, zero out all existing parts
    for p in cd["hair"]["parts"]:
        p["id"] = 0
        p["baseColor"] = [1.0, 1.0, 1.0, 1.0]
        p["startColor"] = [1.0, 1.0, 1.0, 1.0]
        p["endColor"] = [1.0, 1.0, 1.0, 1.0]

    # Then fill in Marta's parts
    for i, hp in enumerate(marta_look["hair_parts"]):
        if i < len(cd["hair"]["parts"]):
            cd["hair"]["parts"][i]["id"] = hp["id"]
            cd["hair"]["parts"][i]["baseColor"] = hp["baseColor"]
            cd["hair"]["parts"][i]["startColor"] = hp["startColor"]
            cd["hair"]["parts"][i]["endColor"] = hp["endColor"]

    # Eye ID + color
    for p in cd["face"]["pupil"]:
        p["id"] = marta_look["eye_id"]
        p["baseColor"] = [
            float(marta_look["eye_color"][0]),
            float(marta_look["eye_color"][1]),
            float(marta_look["eye_color"][2]),
            1.0,
        ]

    # Skin colors (face + body)
    smc = marta_look["skin_main_color"]
    ssc = marta_look["skin_sub_color"]
    cd["face"]["skinMainColor"] = [float(smc[0]), float(smc[1]), float(smc[2]), 1.0]
    cd["face"]["skinSubColor"] = [float(ssc[0]), float(ssc[1]), float(ssc[2]), 1.0]
    cd["body"]["skinMainColor"] = [float(smc[0]), float(smc[1]), float(smc[2]), 1.0]
    cd["body"]["skinSubColor"] = [float(ssc[0]), float(ssc[1]), float(ssc[2]), 1.0]

    # Skin IDs
    if marta_look["face_skin_id"] != 0:
        cd["face"]["skinId"] = marta_look["face_skin_id"]
    if marta_look["body_skin_id"] != 0:
        cd["body"]["skinId"] = marta_look["body_skin_id"]

    print(f"    Hair kind → {cd['hair']['kind']}")
    print(f"    Hair parts → {[p['id'] for p in cd['hair']['parts'] if p.get('id',0) != 0]}")
    print(f"    Eye id → {cd['face']['pupil'][0]['id']}")
    print(f"    Eye color → {[round(c,3) for c in cd['face']['pupil'][0]['baseColor'][:3]]}")
    print(f"    Skin main → {[round(c,3) for c in cd['body']['skinMainColor'][:3]]}")

    # ── 5. Apply STYLE (IA2_flat body/facial shapes) ───────────────────────
    print(f"\n[5] Applying STYLE (IA2_flat baseline)")

    # Replace shapeValueFace with IA2_flat baseline
    cd["face"]["shapeValueFace"] = bl["dominant_face"]

    # Replace shapeValueBody with IA2_flat baseline
    cd["body"]["shapeValueBody"] = bl["dominant_body"]

    # Set discrete face features
    cd["face"]["noseId"] = bl["noseId"]
    cd["face"]["lipLineId"] = bl["lipLineId"]
    cd["face"]["headId"] = bl["headId"]
    cd["face"]["eyebrowId"] = bl["eyebrowId"]
    cd["face"]["pupilWidth"] = bl["pupilWidth"]
    cd["face"]["pupilHeight"] = bl["pupilHeight"]
    cd["face"]["pupilX"] = bl["pupilX"]
    cd["face"]["pupilY"] = bl["pupilY"]

    # Set discrete body features
    cd["body"]["bustWeight"] = bl["bustWeight"]
    cd["body"]["bustSoftness"] = bl["bustSoftness"]
    cd["body"]["areolaSize"] = bl["areolaSize"]

    print(f"    shapeValueFace → {len(cd['face']['shapeValueFace'])} dims (IA2_flat baseline)")
    print(f"    shapeValueBody → {len(cd['body']['shapeValueBody'])} dims (IA2_flat baseline)")
    print(f"    noseId → {cd['face']['noseId']}")
    print(f"    lipLineId → {cd['face']['lipLineId']}")
    print(f"    eyebrowId → {cd['face']['eyebrowId']}")

    # ── 6. Clothes: nude (all id=0) ─────────────────────────────────────────
    print(f"\n[6] Setting clothes to default nude")
    for cloth_block in ["clothes", "over Wear", "accent"]:
        if cloth_block in cd:
            for item in cd[cloth_block]:
                item["id"] = 0
    # Also handle clothesArms if present
    if "clothesArms" in cd:
        for item in cd["clothesArms"]:
            item["id"] = 0
    print(f"    Clothes set to id=0 (nude)")

    # ── 7. Metadata ─────────────────────────────────────────────────────────
    print(f"\n[7] Setting metadata")
    pd = card.Parameter.data
    pd["name"] = "Marta"
    pd["familyname"] = "Lorente"
    pd["nickname"] = "Marta"
    pd["personality"] = 12
    print(f"    name={pd['name']} familyname={pd['familyname']} nickname={pd['nickname']} personality={pd['personality']}")

    # ── 8. Save .kkpe ───────────────────────────────────────────────────────
    print(f"\n[8] Saving .kkpe → {OUT_KKPE}")
    card.save(str(OUT_KKPE))
    print(f"    Saved: {OUT_KKPE.stat().st_size} bytes")

    # ── 9. Save .png ────────────────────────────────────────────────────────
    print(f"\n[9] Saving .png → {OUT_PNG}")
    card.save(str(OUT_PNG))
    print(f"    Saved: {OUT_PNG.stat().st_size} bytes")

    # ── 10. Copy to kkRenderBridge ──────────────────────────────────────────
    print(f"\n[10] Copying to kkRenderBridge")
    shutil.copy2(str(OUT_KKPE), str(KKRB / "marta_ia2_v2.kkpe"))
    shutil.copy2(str(OUT_PNG), str(KKRB / "marta_ia2_v2.png"))
    print(f"    Copied .kkpe → {KKRB / 'marta_ia2_v2.kkpe'}")
    print(f"    Copied .png  → {KKRB / 'marta_ia2_v2.png'}")

    print(f"\n{'=' * 70}")
    print("BUILD COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    build()
