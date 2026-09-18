#!/usr/bin/env python3
"""Build Marta Lorente Inspired v5: use correct asset IDs from the game's item database."""
import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

SRC = Path('C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png')
OUT = Path('C:/Users/Administrator/kk-workspace/MartaLorente_Inspired.kkpe')

print(f"Loading template: {SRC}")
c = KoikatuCharaData.load(str(SRC))
print(f"Template size: {SRC.stat().st_size} bytes")

# ── 1. Parameter: Marta's metadata (same as before) ─────────────────────────
print("\n=== Setting Marta's metadata ===")
c.Parameter.data = {
    "name": "Marta Lorente Inspired",
    "familyname": "Lorente",
    "firstname": "Marta",
    "nickname": "Marta",
    "birth": [8, 5],
    "bloodtype": 4,
    "personality": 12,
    "isAthletic": 1,
    "isVivacious": 1,
    "isGentle": 1,
    "isSensitive": 1,
    "isPlayful": 1,
    "isFashionable": 1,
    "voiceRate": 1.0, "voicePitch": 1.0, "voiceTone": 1.0, "voiceVolume": 1.0,
    "school": 0, "ptype": 1, "confidant": 0, "hobby": 0, "hand": 0, "age": 0,
    "answer1": -1, "answer2": -1, "answer3": -1,
    "isMusic": 0, "isClerical": 0, "isIntellectual": 0,
    "isDomestic": 0, "isPouty": 0, "isCautious": 0,
    "isActress": 0, "isShy": 0, "isLeader": 0,
}

# ── 2. Custom: Hair + Face + Body (visual parameters) ──────────────────────
print("\n=== Setting Custom (hair/face/body) ===")
custom = c.Custom.data
hair = custom["hair"]
face = custom["face"]
body = custom["body"]

# --- Hair: KEEP kind=1 (long wavy) — closest vanilla match to style #27 ---
# Parts id=45/40 are Scarlet Chika's hair parts. Color IS set to blonde.
# We cannot change the hair kind to 27 because that's a specific display index
# that requires the correct asset bundle to be loaded.
print(f"Hair kind: {hair['kind']} (keeping long wavy — close to style #27)")
print(f"Hair parts: {[(p['id'], p['baseColor']) for p in hair['parts']]}")

# --- Eyes: change pupil id from 10 → 6 (vanilla hazel eye, used by 20+ cards) ---
print(f"\nBefore: pupil id={face['pupil'][0]['id']} baseColor={face['pupil'][0]['baseColor']}")
face["pupil"][0]["id"] = 6  # vanilla hazel eye
face["pupil"][1]["id"] = 6
face["pupil"][0]["baseColor"] = [0.5357142686843872, 0.45280611515045166, 0.2455357015132904, 1.0]
face["pupil"][1]["baseColor"] = [0.5357142686843872, 0.45280611515045166, 0.2455357015132904, 1.0]
print(f"After:  pupil id={face['pupil'][0]['id']} baseColor={face['pupil'][0]['baseColor']}")

# --- Face skin colors (tanned) ---
# Note: face.skinId=0 loads default face texture; the face doesn't have
# skinMainColor/skinSubColor in its data dict. Body skin color affects neck/limbs.
face["skinMainColor"] = [1.0, 0.82, 0.65, 1.0]  # warm tan
face["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]   # warm undertone
print(f"Face skin colors set to tanned")

# --- Body skin: already tanned in our data, ensure it stays ---
body["skinMainColor"] = [1.0, 0.8199999928474426, 0.6499999761581421, 1.0]
body["skinSubColor"] = [1.0, 0.550000011920929, 0.4000000059604645, 1.0]
body["skinGlossPower"] = 0.35
body["sunburnColor"] = [1.0, 0.949999988079071, 0.699999988079071, 0.4000000059604645]
print(f"Body skin: {body['skinMainColor']}")

# --- Face features ---
face["detailPower"] = 0.5
face["cheekGlossPower"] = 0.15
face["pupilWidth"] = 0.87
face["pupilHeight"] = 0.83

# ── 3. Coordinate: Clothes + Accessories ────────────────────────────────────
print("\n=== Setting Coordinate (clothes + accessories) ===")
cdata = c.Coordinate.data
slot0 = cdata[0]
clothes = slot0["clothes"]
parts = clothes["parts"]
acc = slot0["accessory"]["parts"]
mkup = slot0["makeup"]

WHITE = [1.0, 1.0, 1.0, 1.0]
GOLD = [1.0, 0.83, 0.39, 1.0]
GOLD_DARK = [1.0, 0.65, 0.15, 1.0]
NUDE = [0.95, 0.85, 0.78, 1.0]

# Helper: recolor a part
def recolor(part, color, pattern=0):
    for ci in part["colorInfo"]:
        ci["baseColor"] = list(color)
        ci["pattern"] = pattern
        ci["patternColor"] = list(color)
        ci["tiling"] = [0.0, 0.0]
    part["emblemeId"] = 0  # remove any emblem/logo

# part[0] = TOP: keep id=321527, recolor white, remove emblemeId
recolor(parts[0], WHITE, pattern=0)
parts[0]["emblemeId"] = 0
print(f"Top: id={parts[0]['id']} white, emblemeId=0")

# part[1] = BOTTOM: change id=4 (plaid skirt) → id=524 (white skirt, vanilla)
# Also recolor parts[2-8] to nude
parts[1]["id"] = 524  # vanilla white skirt
recolor(parts[1], WHITE, pattern=0)
for idx in [2, 3, 6, 7, 8]:
    recolor(parts[idx], NUDE, pattern=0)
for idx in [4, 5]:
    recolor(parts[idx], NUDE, pattern=0)
print(f"Bottom: id={parts[1]['id']} (white skirt)")
print(f"Underwear/legs: nude")

# --- Accessories: try to set gold earrings, necklace, rings ---
# type=120 is the accessory render type. id=0 means "no accessory".
# We'll set gold tint on slots 0-2 and leave others empty.
for i in range(3):
    acc[i]["type"] = 120
    acc[i]["id"] = 0  # no specific accessory mesh — just gold tint on default
    acc[i]["color"] = [GOLD, GOLD_DARK, WHITE, GOLD]
    acc[i]["hideCategory"] = 0
    acc[i]["noShake"] = False

# Clear rest
for i in range(3, 20):
    acc[i]["type"] = 120
    acc[i]["id"] = 0
    acc[i]["color"] = [WHITE] * 4
    acc[i]["hideCategory"] = 0

print(f"Accessories: gold tint on slots 0-2 (default mesh)")

# --- Makeup ---
mkup["eyeshadowId"] = 0
mkup["eyeshadowColor"] = [0.8, 0.7, 0.55, 1.0]
mkup["cheekId"] = 0
mkup["cheekColor"] = [1.0, 0.6, 0.55, 1.0]
mkup["lipId"] = 0
mkup["lipColor"] = [0.95, 0.55, 0.50, 1.0]

# ── 4. Save ──────────────────────────────────────────────────────────────────
print(f"\nSaving to: {OUT}")
c.save(str(OUT))
sz = OUT.stat().st_size
print(f"Saved: {OUT} ({sz} bytes)")

# ── 5. Verify ─────────────────────────────────────────────────────────────────
print("\n=== Verification ===")
c2 = KoikatuCharaData.load(str(OUT))
print(f"Name: {c2.Parameter.data.get('name')}")
print(f"Birth: {c2.Parameter.data.get('birth')}")
print(f"Personality: {c2.Parameter.data.get('personality')}")

cd2 = c2.Custom.data
hair2 = cd2["hair"]
face2 = cd2["face"]
body2 = cd2["body"]
coord2 = c2.Coordinate.data[0]
clothes2 = coord2["clothes"]
acc2 = coord2["accessory"]["parts"]

print(f"\nHair kind: {hair2['kind']}")
for i, p in enumerate(hair2["parts"]):
    print(f"  part[{i}] id={p['id']} baseColor={p['baseColor']}")

print(f"\nEye pupil[0]: id={face2['pupil'][0]['id']} baseColor={face2['pupil'][0]['baseColor']}")

print(f"\nFace skinId: {face2['skinId']} skinMainColor={face2.get('skinMainColor','N/A')}")
print(f"Body skinId: {body2['skinId']} skinMainColor={body2['skinMainColor']}")

print(f"\nClothes:")
for i, p in enumerate(clothes2["parts"]):
    bc = p["colorInfo"][0]["baseColor"] if p["colorInfo"] else "N/A"
    print(f"  part[{i}] id={p['id']} baseColor={bc} emblemeId={p.get('emblemeId',0)}")

print(f"\nAccessories (first 3):")
for i in range(3):
    a = acc2[i]
    print(f"  acc[{i}] type={a['type']} id={a['id']} color[0]={a['color'][0]}")

print(f"\nDone. File: {OUT} ({sz} bytes)")
