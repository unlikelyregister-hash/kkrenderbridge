#!/usr/bin/env python3
"""Build Marta Lorente Inspired .kkpe with overridden visual parameters.
Uses Scarlet Chika as base, overrides hair color → blonde,
skin color → tan, eye color → hazel, lip color → coral.
Keeps all asset IDs (hair kind, eye kind, face shape) unchanged."""
import os, struct, json
from pathlib import Path
from copy import deepcopy

from kkloader import KoikatuCharaData

WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
GAME = Path(r"C:\Games\Koikatsu")
OUTPUT = WORKSPACE / "MartaLorente_Inspired.kkpe"
BASE_CARD = GAME / "UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"

print(f"=== Loading base card: {BASE_CARD.name} ===")
print(f"  Size: {BASE_CARD.stat().st_size:,} bytes")
base = KoikatuCharaData.load(str(BASE_CARD))

# ---- 1. Parameter block: metadata ----
param = base["Parameter"]
pdata = param.data if hasattr(param, 'data') else dict(param)

marta_meta = {
    "lastname": "Lorente",
    "firstname": "Marta",
    "nickname": "Marta",
    "birthMonth": 8,
    "birthDay": 5,
    "bloodType": 0,
    "personality": 12,
    "diligence": 5,
    "kindness": 5,
    "aggressive": 0,
    "attribute": {"hinnyo": False, "harapeko": False, "donkan": False, "choroi": False,
                  "bitch": True, "mutturi": False, "dokusyo": True, "ongaku": True,
                  "kappatu": False, "ukemi": False, "friendly": True, "kireizuki": True,
                  "taida": False, "sinsyutu": False, "hitori": True, "undo": False,
                  "majime": False, "likeGirls": False, "ExtendedSaveData": None},
    "awnser": {"animal": True, "eat": True, "cook": False, "exercise": False,
               "study": False, "fashionable": True, "blackCoffee": True,
               "spicy": True, "sweet": False, "ExtendedSaveData": None},
    "denial": {"kiss": True, "aibu": True, "anal": True, "massage": True,
               "notCondom": True, "ExtendedSaveData": None},
    "weakPoint": 2,
    "clubActivities": 0,
    "callType": -1,
    "sex": 1,
    "exType": 0,
    "voiceRate": 0.5,
    "version": 0.0.5,
}
for k, v in marta_meta.items():
    pdata[k] = v
print(f"  Metadata set: {pdata.get('lastname')} {pdata.get('firstname')}, "
      f"BD: {pdata.get('birthMonth')}/{pdata.get('birthDay')}, "
      f"BT: {pdata.get('bloodType')}, "
      f"Per: {pdata.get('personality')}")

# ---- 2. Custom block: visual parameters ----
custom = base["Custom"]
cdata = custom.data if hasattr(custom, 'data') else {}
print(f"\n=== Modifying visual parameters ===")

# Helper to convert RGB (0-255) → Koikatsu float (0-1)
def rgb(r, g, b, a=1.0):
    return [r/255.0, g/255.0, b/255.0, a]

# --- Hair colors: blonde (base #FFE0B0, highlight #FFF5E0) ---
hair = cdata.get("hair", {})
print(f"  Hair parts: {len(hair.get('parts', []))}")
for i, part in enumerate(hair.get("parts", [])):
    pid = part.get("id", 0)
    if pid == 0:
        continue  # skip empty parts
    bc = part.get("baseColor", [0,0,0,1])
    sc = part.get("startColor", [0,0,0,1])
    ec = part.get("endColor", [0,0,0,1])
    print(f"    Part {i} (id={pid}): base={bc[:3]}, start={sc[:3]}, end={ec[:3]}")
    # Override to blonde
    part["baseColor"] = rgb(255, 224, 176)   # #FFE0B0 - blonde base
    part["startColor"] = rgb(255, 245, 224)  # #FFF5E0 - light blonde highlight
    part["endColor"] = rgb(255, 232, 192)    # #FFE8C0 - blonde gradient end
    part["outlineColor"] = rgb(180, 160, 120)  # slightly darker outline

# Override hair kind to a wavy style if possible
# Scarlet Chika uses kind=1. Marta wants style #27 (wavy side-part)
# kind is the hair asset ID; 1 is likely the default
# We keep kind=1 since we don't have asset ID for #27
hair["kind"] = 1  # keep current; can't change without correct asset ID
hair["glossId"] = 5

cdata["hair"] = hair
print(f"  Hair → blonde (base=#FFE0B0, highlight=#FFF5E0)")

# --- Body/skin colors: tanned ---
body = cdata.get("body", {})
print(f"\n  Body keys: {list(body.keys())[:10]}")
bc = body.get("skinMainColor", [1,1,1,1])
sc = body.get("skinSubColor", [1,1,1,1])
print(f"    Skin main: {bc[:3]}, sub: {sc[:3]}")
# Tan skin: main=#E0B090, sub=#C09070
body["skinMainColor"] = rgb(224, 176, 144)   # #E0B090 - tanned skin main
body["skinSubColor"] = rgb(192, 144, 112)    # #C09070 - tanned skin sub
body["skinGlossPower"] = 0.15  # less glossy for natural look
cdata["body"] = body
print(f"  Skin → tanned (main=#E0B090, sub=#C09070)")

# --- Eye colors: hazel ---
face = cdata.get("face", {})
pupils = face.get("pupil", [])
print(f"\n  Eyes: {len(pupils)} pupils")
for i, pupil in enumerate(pupils):
    bc = pupil.get("baseColor", [0,0,0,1])
    sc = pupil.get("subColor", [0,0,0,1])
    print(f"    Pupil {i}: base={bc[:3]}, sub={sc[:3]}")
    # Hazel eyes: base=#A08040 (brown-green hazel)
    pupil["baseColor"] = rgb(160, 128, 64)   # #A08040 - hazel
    pupil["subColor"] = rgb(140, 100, 50)    # darker hazel inner

# Lip color: coral
bm = face.get("baseMakeup", {})
lip_c = bm.get("lipColor", [1,1,1,1])
print(f"\n  Lip color: {lip_c[:3]}")
bm["lipColor"] = rgb(230, 160, 140)  # coral pink
bm["lipGlossPower"] = 0.5  # some gloss
face["baseMakeup"] = bm
print(f"  Lips → coral (#E6A08C)")

# Cheek color: light peach
cheek_c = bm.get("cheekColor", [1,1,1,1])
bm["cheekColor"] = rgb(255, 200, 180)  # light peach blush
face["baseMakeup"] = bm

cdata["face"] = face

# --- Eye shape: keep current but note target is type #08 ---
# The eye shape is controlled by the 'pupil' id and various eye-related IDs
# Scarlet Chika's eyes use id=10 (blue-ish). We keep the shape, just change color.
print(f"\n  Eye shape: keeping current (pupil id={pupils[0].get('id') if pupils else 'N/A'})")
print(f"    Target: eye type #08 (hazel) — can't change without asset ID")

custom.data = cdata

# ---- 3. Save ----
print(f"\n=== Saving {OUTPUT.name} ===")
base.save(str(OUTPUT))
sz = OUTPUT.stat().st_size
print(f"  Size: {sz:,} bytes ({sz/1024:.1f} KB)")
print(f"  >300KB: {'YES' if sz > 300000 else 'NO — INVALID CARD'}")

# ---- 4. Verify round-trip ----
print(f"\n=== Verifying round-trip ===")
v = KoikatuCharaData.load(str(OUTPUT))
vp = v["Parameter"]
vpd = vp.data if hasattr(vp, 'data') else {}
vc = v["Custom"]
vcd = vc.data if hasattr(vc, 'data') else {}

print(f"  Name: {vpd.get('lastname')} {vpd.get('firstname')}")
print(f"  Nick: {vpd.get('nickname')}")
print(f"  BD: {vpd.get('birthMonth')}/{vpd.get('birthDay')}")
print(f"  BT: {vpd.get('bloodType')}")
print(f"  Per: {vpd.get('personality')}")

# Check hair color
vh = vcd.get("hair", {})
for i, part in enumerate(vh.get("parts", [])):
    if part.get("id", 0) != 0:
        bc = part.get("baseColor", [0,0,0,1])
        print(f"  Hair part {i} base color (float): {bc}")
        print(f"    → RGB: ({int(bc[0]*255)}, {int(bc[1]*255)}, {int(bc[2]*255)})")
        if abs(bc[0] - 255/255) < 0.01 and abs(bc[1] - 224/255) < 0.01 and abs(bc[2] - 176/255) < 0.01:
            print(f"    → ✓ Blonde verified")
        else:
            print(f"    → ✗ NOT blonde!")

# Check skin color
vb = vcd.get("body", {})
bmain = vb.get("skinMainColor", [0,0,0,1])
print(f"  Skin main (float): {bmain}")
print(f"    → RGB: ({int(bmain[0]*255)}, {int(bmain[1]*255)}, {int(bmain[2]*255)})")
if abs(bmain[0] - 224/255) < 0.01 and abs(bmain[1] - 176/255) < 0.01:
    print(f"    → ✓ Tan verified")
else:
    print(f"    → ✗ NOT tan!")

# Check eye color
vf = vcd.get("face", {})
vpupils = vf.get("pupil", [])
if vpupils:
    vbcol = vpupils[0].get("baseColor", [0,0,0,1])
    print(f"  Eye base (float): {vbcol}")
    print(f"    → RGB: ({int(vbcol[0]*255)}, {int(vbcol[1]*255)}, {int(vbcol[2]*255)})")
    if abs(vbcol[0] - 160/255) < 0.01 and abs(vbcol[1] - 128/255) < 0.01:
        print(f"    → ✓ Hazel verified")
    else:
        print(f"    → ✗ NOT hazel!")

print(f"\n=== DONE ===")
print(f"File: {OUTPUT}")
print(f"Ready for render submission")
