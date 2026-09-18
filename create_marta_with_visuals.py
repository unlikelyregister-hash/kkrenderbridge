"""Create MartaCard.png by combining Scarlet Chika's visual data with Marta's metadata.

Strategy:
  1. Load Scarlet Chika (the only full card with visual params in the library)
  2. Replace the Parameter block with Marta's metadata
  3. Keep Custom (face/body/hair) and Coordinate (clothes) intact
  4. Save as MartaCard.png — now has REAL visual data to render
"""
import shutil
from pathlib import Path
from kkloader import KoikatuCharaData

# Source: Scarlet Chika (full card with visual data)
SRC = Path(r"C:\Games\Koikatsu\UserData\chara\female\Koikatu_F_20260221024507269_Scarlet Chika.png")
DEST = Path.cwd() / "MartaCard.png"

print(f"Loading source card: {SRC}")
chara = KoikatuCharaData.load(str(SRC))
print(f"  blockdata: {chara.blockdata}")
print(f"  image: {len(chara.image)} bytes")
print(f"  face_image: {len(chara.face_image)} bytes")

# Replace Parameter block with Marta's metadata
print("\nReplacing Parameter block with Marta Lorente metadata...")

marta_param = {
    'nickname': 'MartaLorente_Inspired',
    'name': 'Marta',
    'familyname': 'Marta',
    'firstname': 'Lorente',
    'school': 0,
    'ptype': 1,
    'personality': 12,        # Cheerful / Free-Spirited
    'confidant': 0,
    'birth': [8, 5],          # August 5
    'bloodtype': 3,           # O
    'hobby': 0,
    'hand': 0,
    'age': 0,
    'answer1': -1,
    'answer2': -1,
    'answer3': -1,
    'voiceRate': 1.0,
    'voicePitch': 1.0,
    'voiceTone': 1.0,
    'voiceVolume': 1.0,
    'isMusic': 0,
    'isClerical': 0,
    'isFashionable': 1,
    'isDomestic': 0,
    'isIntellectual': 0,
    'isAthletic': 1,
    'isPlayful': 1,
    'isPouty': 0,
    'isGentle': 0,
    'isCautious': 0,
    'isActress': 0,
    'isShy': 0,
    'isVivacious': 1,
    'isLeader': 0,
    'isSensitive': 0,
}

# The Parameter module uses its own key format — set via .data
param_block = chara['Parameter']
param_block.data = marta_param

# Keep Custom (face/body/hair) and Coordinate (clothes) from Scarlet Chika
print(f"  Keeping Custom block: {list(chara['Custom'].data.keys())}")
print(f"  Keeping Coordinate block: {type(chara['Coordinate'].data).__name__}")

# Save
DEST.parent.mkdir(parents=True, exist_ok=True)
chara.save(str(DEST))
print(f"\nSaved: {DEST}")
print(f"  Size: {DEST.stat().st_size} bytes")

# Verify
print("\n=== Verification ===")
verify = KoikatuCharaData.load(str(DEST))
p = verify['Parameter']
print(f"  nickname: {p['nickname']}")
print(f"  name: {p['name']} {p['firstname']}")
print(f"  birthday: {p['birth']}")
print(f"  bloodtype: {p['bloodtype']}")
print(f"  personality: {p['personality']}")
print(f"  blockdata: {verify.blockdata}")
print(f"  Custom.face keys: {len(verify['Custom']['face'])} fields")
print(f"  Custom.body keys: {len(verify['Custom']['body'])} fields")
print(f"  Custom.hair keys: {len(verify['Custom']['hair'])} fields")
print(f"  Coordinate present: {verify.blockdata.count('Coordinate') > 0}")
print("\n[DONE] MartaCard.png now has Marta's metadata + Scarlet Chika's visuals")
print("  Copy to game: cp MartaCard.png \"C:/Games/Koikatsu/UserData/chara/female/kkrenderbridge/\"")
