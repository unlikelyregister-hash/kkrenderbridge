#!/usr/bin/env python3
"""Rebuild Marta Lorente Inspired .kkpe: copy Scarlet Chika's Coordinate,
then replace clothes + accessories to match Marta's outfit.

Marta's outfit:
  - White crochet halter/fringe top
  - White sarong wrap with gold ring belt
  - Gold hoop earrings
  - Gold pendant necklace
  - Gold rings
  - Athletic body, tanned skin

Visual approach:
  - Keep hair/eye/skin/tone color values from build_marta_kkpe.py (already in the .kkpe)
  - Replace Coordinate clothes to be white-based (top + sarong)
  - Add gold accessories
"""
import json, copy, pathlib, os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

SRC = pathlib.Path("C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png")
OUT = pathlib.Path("C:/Users/Administrator/kk-workspace/MartaLorente_Inspired.kkpe")

print(f"Loading template: {SRC}")
chara = KoikatuCharaData.load(str(SRC))
print(f"Template blocks: {list(chara.blockdata)}")

# ── Parameter block: Marta's metadata ────────────────────────────────────────
print("\n=== Setting Marta's metadata ===")
param = chara.Parameter
param.data = {
    "name": "Marta Lorente Inspired",
    "familyname": "Lorente",
    "firstname": "Marta",
    "nickname": "Marta",
    "school": 0,
    "ptype": 1,
    "personality": 12,
    "confidant": 0,
    "birth": [8, 5],
    "bloodtype": 4,
    "hobby": 0,
    "hand": 0,
    "age": 0,
    "answer1": -1,
    "answer2": -1,
    "answer3": -1,
    "voiceRate": 1.0,
    "voicePitch": 1.0,
    "voiceTone": 1.0,
    "voiceVolume": 1.0,
    "isMusic": 0,
    "isClerical": 0,
    "isFashionable": 1,
    "isDomestic": 0,
    "isIntellectual": 0,
    "isAthletic": 1,
    "isPlayful": 1,
    "isPouty": 0,
    "isGentle": 1,
    "isCautious": 0,
    "isActress": 0,
    "isShy": 0,
    "isVivacious": 1,
    "isLeader": 0,
    "isSensitive": 1,
}
print("Parameter set.")

# ── Custom block: hair/face/body colors (Marta's appearance) ─────────────────
print("\n=== Setting Marta's visual colors ===")
custom = chara.Custom
face = custom.data["face"]
body = custom.data["body"]
hair = custom.data["hair"]

# Hair: blonde
for part in hair["parts"]:
    if part["id"] != 0:
        part["baseColor"] = [1.0, 0.784, 0.549, 1.0]   # blonde base
        part["startColor"] = [1.0, 0.902, 0.745, 1.0]  # light blonde highlight
        part["endColor"] = [1.0, 0.941, 0.824, 1.0]
        part["acsColor"][0] = [1.0, 0.85, 0.7, 1.0]

# Face: hazel eyes + tanned skin
pupil = face["pupil"][0] if face.get("pupil") else {}
if pupil:
    pupil["baseColor"] = [0.627, 0.510, 0.314, 1.0]   # hazel
    pupil["subColor"] = [0.5, 0.4, 0.25, 1.0]

face["skinMainColor"] = [1.0, 0.82, 0.65, 1.0]        # warm tan
face["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]         # warm undertone
face["eyebrowColor"] = [0.6, 0.45, 0.3, 1.0]
face["lipLineColor"] = [0.9, 0.55, 0.5, 1.0]
if "baseMakeup" in face and "lipColor" in face["baseMakeup"]:
    face["baseMakeup"]["lipColor"] = [0.95, 0.55, 0.5, 1.0]
face["eyelineColor"] = [0.3, 0.2, 0.15, 1.0]
face["detailPower"] = 0.5
face["cheekGlossPower"] = 0.15

# Body: tanned skin + athletic build
body["skinMainColor"] = [1.0, 0.82, 0.65, 1.0]
body["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]
body["skinGlossPower"] = 0.35
body["sunburnColor"] = [1.0, 0.95, 0.7, 0.4]
body["shapeValueBody"] = [0.35, 0.55, 0.45, 0.40, 0.45, 0.50, 0.45, 0.50, 0.45, 0.40]
body["detailPower"] = 0.75
print("Custom (hair/skin/eyes) set.")

# ── Coordinate block: Marta's clothes + accessories ──────────────────────────
print("\n=== Setting Coordinate (clothes + accessories) ===")
coord = chara.Coordinate
coord_data = coord.data  # list of 7 outfit slots
slot0 = coord_data[0]    # main outfit
clothes = slot0["clothes"]
parts = clothes["parts"]  # 9 parts
acc = slot0["accessory"]["parts"]  # 20 accessory slots
mkup = slot0["makeup"]

WHITE = [1.0, 1.0, 1.0, 1.0]
GOLD  = [1.0, 0.83, 0.39, 1.0]
GOLD_DARK = [1.0, 0.65, 0.15, 1.0]
NUDE = [0.95, 0.85, 0.78, 1.0]

# Helper: set all 4 colorInfo entries of a part to the same color
def recolor_part(part, color, pattern=0):
    for ci in part["colorInfo"]:
        ci["baseColor"] = list(color)
        ci["pattern"] = pattern
        ci["patternColor"] = list(color)
        ci["tiling"] = [0.0, 0.0]

# part[0] = top: white halter/fringe top
# Keep Scarlet Chika's top id (321527) so the mesh loads, recolor to white
recolor_part(parts[0], WHITE, pattern=0)
print(f"part[0] top (id={parts[0]['id']}): white")

# part[1] = bottom: white sarong wrap
# Keep Scarlet Chika's skirt id (4), recolor to white
recolor_part(parts[1], WHITE, pattern=0)
print(f"part[1] bottom (id={parts[1]['id']}): white")

# parts[2-3] = bras/underwear: nude
for idx in [2, 3]:
    recolor_part(parts[idx], NUDE, pattern=0)
print(f"parts[2-3] underwear: nude")

# parts[4-5] = legs/socks: nude
for idx in [4, 5]:
    recolor_part(parts[idx], NUDE, pattern=0)
print(f"parts[4-5] legs: nude")

# part[6] = panty: nude
recolor_part(parts[6], NUDE, pattern=0)
print(f"part[6] panty: nude")

# parts[7-8] = socks/legs: nude
for idx in [7, 8]:
    recolor_part(parts[idx], NUDE, pattern=0)
print(f"parts[7-8] legs: nude")

# ── Accessories ───────────────────────────────────────────────────────────────
# acc[0] = gold hoop earrings
acc[0]["type"] = 120
acc[0]["id"] = 0
acc[0]["color"] = [GOLD, GOLD_DARK, WHITE, GOLD]
acc[0]["hideCategory"] = 0
acc[0]["noShake"] = False

# acc[1] = gold pendant necklace
acc[1]["type"] = 120
acc[1]["id"] = 0
acc[1]["color"] = [GOLD, GOLD_DARK, WHITE, GOLD]
acc[1]["hideCategory"] = 0
acc[1]["noShake"] = False

# acc[2] = gold ring
acc[2]["type"] = 120
acc[2]["id"] = 0
acc[2]["color"] = [GOLD, GOLD_DARK, WHITE, GOLD]
acc[2]["hideCategory"] = 0
acc[2]["noShake"] = False

# Clear remaining accessory slots
for i in range(3, 20):
    acc[i]["type"] = 120
    acc[i]["id"] = 0
    acc[i]["color"] = [WHITE] * 4
    acc[i]["hideCategory"] = 0
    acc[i]["noShake"] = False

print(f"Accessories: gold earring, necklace, ring")

# ── Makeup ────────────────────────────────────────────────────────────────────
mkup["eyeshadowId"] = 0
mkup["eyeshadowColor"] = [0.8, 0.7, 0.55, 1.0]
mkup["cheekId"] = 0
mkup["cheekColor"] = [1.0, 0.6, 0.55, 1.0]
mkup["lipId"] = 0
mkup["lipColor"] = [0.95, 0.55, 0.50, 1.0]
mkup["paintId"] = [0, 0]
mkup["paintColor"] = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
mkup["paintLayout"] = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]

# ── Save ──────────────────────────────────────────────────────────────────────
print(f"\nSaving to: {OUT}")
chara.save(str(OUT))
sz = OUT.stat().st_size
print(f"Saved: {OUT} ({sz} bytes)")

# ── Verify ────────────────────────────────────────────────────────────────────
print("\n=== Verification ===")
chara2 = KoikatuCharaData.load(str(OUT))
p = chara2.Parameter
print(f"Name: {p.data.get('name')}")
print(f"Birthday: {p.data.get('birth')}")
print(f"Personality: {p.data.get('personality')}")

coord2 = chara2.Coordinate
slot2 = coord2.data[0]
clothes2 = slot2["clothes"]
print(f"\nClothes parts count: {len(clothes2['parts'])}")
for i, pt in enumerate(clothes2["parts"]):
    ci0 = pt["colorInfo"][0] if pt["colorInfo"] else {}
    bc = ci0.get("baseColor", "N/A")
    print(f"  part[{i}] id={pt['id']:>7d} baseColor={bc}")

print(f"\nAccessories (first 3):")
for i in range(3):
    a = slot2["accessory"]["parts"][i]
    print(f"  acc[{i}] type={a['type']} id={a['id']} color[0]={a['color'][0]}")

print(f"\nCoordinate slot 0 clothes parts: {len(clothes2['parts'])}")
print(f"Coordinate slot 0 accessory parts: {len(slot2['accessory']['parts'])}")

print(f"\nDone. File: {OUT} ({sz} bytes)")
