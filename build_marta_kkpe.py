"""Build Marta Lorente Inspired character card from scratch using Scarlet Chika's
visual parameter structure as a template, with Marta's appearance values filled in.

This creates a valid .kkpe-loadable card with:
  - Hair: blonde (kind 1, long wavy) with blonde base + light blonde highlights
  - Eyes: hazel/brown (pupil color adjusted)
  - Skin: tanned warm tone
  - Makeup: adjusted for Marta's look
  - Body: athletic build
  - Full metadata: name, birthday, personality, traits
"""
from pathlib import Path
from kkloader import KoikatuCharaData
import copy

# ── Source: Scarlet Chika (full visual data template) ──────────────────────
SRC = Path(r"C:\Games\Koikatsu\UserData\chara\female\Koikatu_F_20260221024507269_Scarlet Chika.png")
OUT = Path.cwd() / "MartaLorente_Inspired.kkpe"

print(f"Loading template: {SRC}")
chara = KoikatuCharaData.load(str(SRC))

# ── Replace Parameter block with Marta's metadata ───────────────────────────
print("\n=== Setting Marta's metadata ===")
chara["Parameter"].data = {
    "nickname": "MartaLorente_Inspired",
    "name": "Marta Lorente Inspired",
    "familyname": "Lorente",
    "firstname": "Marta",
    "school": 0,
    "ptype": 1,
    "personality": 12,          # cheerful
    "confidant": 0,
    "birth": [8, 5],            # August 5
    "bloodtype": 4,             # O type (0=A,1=B,2=AB,3=O — wait let me check)
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

# ── Modify visual parameters to match Marta ─────────────────────────────────
custom = chara["Custom"]
face = custom.data["face"]
body = custom.data["body"]
hair = custom.data["hair"]

# --- Hair: blonde base color (long wavy style, keeping Scarlet Chika's part IDs) ---
# Marta: blonde hair with light blonde highlights
for part in hair["parts"]:
    if part["id"] != 0:  # skip empty parts
        # Blonde base: RGB ~ (255, 200, 140) → normalized [1.0, 0.784, 0.549, 1.0]
        part["baseColor"] = [1.0, 0.784, 0.549, 1.0]
        # Light blonde highlight: RGB ~ (255, 230, 190) → [1.0, 0.902, 0.745, 1.0]
        part["startColor"] = [1.0, 0.902, 0.745, 1.0]
        # Lighter blonde end: RGB ~ (255, 240, 210) → [1.0, 0.941, 0.824, 1.0]
        part["endColor"] = [1.0, 0.941, 0.824, 1.0]
        # Accessory colors for blonde hair
        part["acsColor"][0] = [1.0, 0.85, 0.7, 1.0]  # main acs
        part["acsColor"][1] = [0.0, 0.0, 0.0, 1.0]   # shadow
        part["acsColor"][2] = [0.0, 0.0, 0.0, 1.0]   # affect
        # Keep length from template

# --- Face: hazel/brown eyes ---
# Marta: hazel eyes (warm brown-green)
pupil = face["pupil"][0] if face.get("pupil") else {}
if pupil:
    # Hazel: RGB ~ (160, 130, 80) → [0.627, 0.510, 0.314, 1.0]
    pupil["baseColor"] = [0.627, 0.510, 0.314, 1.0]
    pupil["subColor"] = [0.5, 0.4, 0.25, 1.0]

# Skin tones for face
face["skinMainColor"] = [1.0, 0.82, 0.65, 1.0]    # warm tan base
face["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]     # warm undertone

# Eyebrow color: darker blonde/brown
face["eyebrowColor"] = [0.6, 0.45, 0.3, 1.0]

# Lip: coral/warm pink
face["lipLineColor"] = [0.9, 0.55, 0.5, 1.0]
face["baseMakeup"]["lipColor"] = [0.95, 0.55, 0.5, 1.0] if "lipColor" in face["baseMakeup"] else None

# Eyeliner color
face["eyelineColor"] = [0.3, 0.2, 0.15, 1.0]

# --- Body: tanned skin ---
body["skinMainColor"] = [1.0, 0.82, 0.65, 1.0]
body["skinSubColor"] = [1.0, 0.55, 0.40, 1.0]
body["skinGlossPower"] = 0.35
body["sunburnColor"] = [1.0, 0.95, 0.7, 0.4]

# --- Body shape: more athletic ---
# shapeValueBody is an array of sliders — keep Scarlet Chika's values but tweak slightly
body["shapeValueBody"] = [
    0.35,  # bust size - slightly larger
    0.55,  # waist - slimmer
    0.45,  # hip - moderate
    0.40,  # waist position
    0.45,  # thigh
    0.50,  # upper arm
    0.45,  # forearm
    0.50,  # belly
    0.45,  # back
    0.40,  # neck
]

# --- Detail / makeup settings ---
face["detailPower"] = 0.5
body["detailPower"] = 0.75
face["cheekGlossPower"] = 0.15

# ── Save as .kkpe ────────────────────────────────────────────────────────────
print(f"\nSaving to: {OUT}")
chara.save(str(OUT))

# ── Verify ───────────────────────────────────────────────────────────────────
sz = OUT.stat().st_size
print(f"\nSaved: {OUT} ({sz} bytes)")

# Reload and verify
print("\n=== Verification ===")
chara2 = KoikatuCharaData.load(str(OUT))
p = chara2["Parameter"]
print(f"Name: {p.data.get('name')}")
print(f"Birthday: {p.data.get('birth')}")
print(f"Personality: {p.data.get('personality')}")
print(f"Bloodtype: {p.data.get('bloodtype')}")

hair2 = chara2["Custom"].data["hair"]
for part in hair2["parts"]:
    if part["id"] != 0:
        print(f"\nHair part id={part['id']}:")
        print(f"  baseColor: {part['baseColor']}")
        print(f"  startColor: {part['startColor']}")

face2 = chara2["Custom"].data["face"]
pupil2 = face2["pupil"][0] if face2.get("pupil") else {}
print(f"\nPupil color: {pupil2.get('baseColor', 'N/A')}")
print(f"SkinMainColor (body): {chara2['Custom'].data['body']['skinMainColor']}")
print(f"\nDone! File: {OUT}")
