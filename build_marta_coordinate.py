#!/usr/bin/env python3
"""Rebuild Marta Lorente Inspired .kkpe with correct Coordinate clothes/accessories.

Clothes: white halter top (part[0]=top), white sarong (part[1]=bottom),
  nude underwear (parts[2-3]=bras, part[6]=panty), skin-colored socks/legs (parts[4,5,7,8])
Accessories: gold hoop earrings (acc[0]), gold pendant necklace (acc[1]),
  gold ring (acc[2]), no other accessories

Hair: keep existing blonde/tanned values (already set by build_marta_kkpe.py).
Face/body: keep existing tanned skin values.
"""
import json, copy, pathlib, os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

SRC = pathlib.Path(r"C:\Games\Koikatsu\UserData\chara\female\Koikatu_F_20260221024507269_Scarlet Chika.png")
OUT = pathlib.Path.cwd() / "MartaLorente_Inspired.kkpe"

print(f"Loading template: {SRC}")
chara = KoikatuCharaData.load(str(SRC))
print(f"Template size: {SRC.stat().st_size} bytes")

# ── 1. Coordinate block (clothes + accessories) ──────────────────────────────
coord = chara.Coordinate
coord_data = coord.data  # list of 7 slot dicts
print(f"\nCoordinate has {len(coord_data)} slots")

# Work on slot 0 only (the main outfit)
slot = coord_data[0]
clothes = slot["clothes"]
parts = clothes["parts"]  # 9 parts
acc = slot["accessory"]["parts"]  # 20 accessory slots
mkup = slot["makeup"]

# Helper: set a part's all 4 colorInfo entries to the same color
def set_part_color(part, r, g, b, a=1.0, pattern=0):
    for ci in part["colorInfo"]:
        ci["baseColor"] = [r, g, b, a]
        ci["pattern"] = pattern
        ci["patternColor"] = [r, g, b, a]
        ci["tiling"] = [0.0, 0.0]

WHITE = (1.0, 1.0, 1.0)
GOLD = (1.0, 0.83, 0.39)
NUDE = (0.95, 0.85, 0.78)

# part[0] = top: white halter top (scarlet chika top id=321527, keep id, change color to white)
# Keep same part id so the top model loads; just recolor to white
top = parts[0]
set_part_color(top, *WHITE, pattern=0)
print(f"Top (part 0, id={top['id']}): whitened")

# part[1] = bottom: white sarong wrap (scarlet chika skirt id=4, keep id, recolor white)
# This is the school skirt — recolor to white for sarong effect
bottom = parts[1]
set_part_color(bottom, *WHITE, pattern=0)
print(f"Bottom (part 1, id={bottom['id']}): whitened (sarong)")

# parts[2-3] = bras/underwear: nude/skin tone (keep ids 1, change color to nude)
for idx in [2, 3]:
    if parts[idx]["id"] != 0:
        set_part_color(parts[idx], *NUDE, pattern=0)
print(f"Underwear (parts 2-3): nudified")

# parts[4-5] = legs/socks: skin tone
for idx in [4, 5]:
    if parts[idx]["id"] != 0:
        set_part_color(parts[idx], *NUDE, pattern=0)
print(f"Legs/socks (parts 4-5): nudified")

# part[6] = panty: nude
if parts[6]["id"] != 0:
    set_part_color(parts[6], *NUDE, pattern=0)
print(f"Panty (part 6): nudified")

# parts[7-8] = socks/legs: skin tone
for idx in [7, 8]:
    if parts[idx]["id"] != 0:
        set_part_color(parts[idx], *NUDE, pattern=0)
print(f"Legs/socks (parts 7-8): nudified")

# ── Accessories ───────────────────────────────────────────────────────────────
# acc[0] = gold hoop earrings
acc[0]["type"] = 120  # earring type
acc[0]["id"] = 0       # will use default earring model (or find actual earring id)
acc[0]["color"] = [
    [1.0, 0.83, 0.39, 1.0],  # gold
    [1.0, 0.70, 0.20, 1.0],  # dark gold shadow
    [1.0, 1.0, 1.0, 1.0],    # highlight
    [1.0, 0.83, 0.39, 1.0],  # main gold
]
acc[0]["hideCategory"] = 0
acc[0]["noShake"] = False

# acc[1] = gold pendant necklace
acc[1]["type"] = 120
acc[1]["id"] = 0
acc[1]["color"] = [
    [1.0, 0.83, 0.39, 1.0],
    [1.0, 0.70, 0.20, 1.0],
    [1.0, 1.0, 1.0, 1.0],
    [1.0, 0.83, 0.39, 1.0],
]
acc[1]["hideCategory"] = 0
acc[1]["noShake"] = False

# acc[2] = gold ring on finger
acc[2]["type"] = 120
acc[2]["id"] = 0
acc[2]["color"] = [
    [1.0, 0.83, 0.39, 1.0],
    [1.0, 0.70, 0.20, 1.0],
    [1.0, 1.0, 1.0, 1.0],
    [1.0, 0.83, 0.39, 1.0],
]
acc[2]["hideCategory"] = 0
acc[2]["noShake"] = False

# Clear remaining accessory slots (hide them)
for i in range(3, 20):
    acc[i]["type"] = 120
    acc[i]["id"] = 0
    acc[i]["color"] = [[1.0, 1.0, 1.0, 1.0]] * 4
    acc[i]["hideCategory"] = 0
    acc[i]["noShake"] = False

print(f"Accessories: gold earring, necklace, ring")

# ── Makeup ────────────────────────────────────────────────────────────────────
mkup["eyeshadowId"] = 0
mkup["eyeshadowColor"] = [0.8, 0.7, 0.55, 1.0]  # warm champagne
mkup["cheekId"] = 0
mkup["cheekColor"] = [1.0, 0.6, 0.55, 1.0]      # warm coral blush
mkup["lipId"] = 0
mkup["lipColor"] = [0.95, 0.55, 0.50, 1.0]      # warm coral lip
mkup["paintId"] = [0, 0]
mkup["paintColor"] = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
mkup["paintLayout"] = [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]

print(f"Makeup: champagne eyeshadow, coral blush, warm lip")

# ── 2. Save ───────────────────────────────────────────────────────────────────
print(f"\nSaving to: {OUT}")
chara.save(str(OUT))
sz = OUT.stat().st_size
print(f"Saved: {OUT} ({sz} bytes)")

# ── 3. Verify ─────────────────────────────────────────────────────────────────
print("\n=== Verification ===")
chara2 = KoikatuCharaData.load(str(OUT))
p = chara2.Parameter
print(f"Name: {p.data.get('name', 'N/A')}")
print(f"Birthday: {p.data.get('birth', 'N/A')}")
print(f"Personality: {p.data.get('personality', 'N/A')}")

coord2 = chara2.Coordinate
slot2 = coord2.data[0]
clothes2 = slot2["clothes"]
top2 = clothes2["parts"][0]
print(f"\nTop colorInfo[0] baseColor: {top2['colorInfo'][0]['baseColor']}")
print(f"Bottom colorInfo[0] baseColor: {clothes2['parts'][1]['colorInfo'][0]['baseColor']}")
print(f"Accessory[0] color[0]: {slot2['accessory']['parts'][0]['color'][0]}")
print(f"Accessory[1] color[0]: {slot2['accessory']['parts'][1]['color'][0]}")

print(f"\nDone. File: {OUT} ({sz} bytes)")
