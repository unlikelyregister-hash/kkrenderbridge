#!/usr/bin/env python3
"""Build MartaLorente.png from base_2.png — modify appearance + metadata.

base_2.png has: dark brown hair (id=45/40), blue-green eyes (id=10),
fair skin, named Chika Scarlet.

Goal: blonde hair, hazel eyes, tanned skin, named Marta Lorente.
Clothing stays as-is from base_2 (per user).

Uses Card5 reference values:
  Hair kind=1, part ids 22+5, blonde baseColor=[0.887,0.605,0.354]
  Eyes id=6, hazel baseColor=[0.536,0.453,0.246]
  Skin: tanned base=[0.994,0.837,0.787] sub=[0.970,0.632,0.508]
"""

import sys
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

BASE = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
OUT = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')

print(f'Loading base: {BASE}')
c = KoikatuCharaData.load(str(BASE))
print(f'Loaded OK. File: {BASE.name} ({BASE.stat().st_size} bytes)')

h = c.Custom.data['hair']
f = c.Custom.data['face']
b = c.Custom.data['body']
p = c.Parameter.data

# ============================================================
# HAIR — change to blonde (id=22+5, kind=1)
# ============================================================
print(f'\nOriginal hair: kind={h["kind"]}')
for part in h['parts']:
    if part['id'] == 0:
        continue
    old_id = part['id']
    # Use the blonde hair part ids from Card5
    if old_id == 45:
        part['id'] = 22  # main hair strand (blonde)
    elif old_id == 40:
        part['id'] = 5   # secondary hair strand (blonde)
    # Set blonde color
    part['baseColor'] = [0.92, 0.80, 0.52, 1.0]
    part['startColor'] = [0.82, 0.64, 0.40, 1.0]
    part['endColor'] = [0.98, 0.88, 0.65, 1.0]
    part['outlineColor'] = [0.20, 0.16, 0.10, 1.0]
    if 'acsColor' in part and isinstance(part['acsColor'], list) and len(part['acsColor']) > 0:
        part['acsColor'][0] = [1.0, 0.82, 0.72, 1.0]
    print(f'  Part id {old_id} → {part["id"]}: blonde {part["baseColor"][:3]}')

# ============================================================
# EYES — change to hazel (id=6)
# ============================================================
for eye in f['pupil']:
    if eye['id'] == 0:
        continue
    old_id = eye['id']
    eye['id'] = 6  # Hazel eye (same as Card5)
    eye['baseColor'] = [0.54, 0.46, 0.25, 1.0]   # Hazel green-brown
    eye['subColor'] = [0.42, 0.32, 0.15, 1.0]    # Darker inner ring
    print(f'  Eye id {old_id} → {eye["id"]}: hazel {eye["baseColor"][:3]}')

# ============================================================
# SKIN — tanned
# ============================================================
old_skin = b['skinMainColor'][:3]
b['skinMainColor'] = [0.94, 0.74, 0.52, 1.0]    # Tanned
b['skinSubColor'] = [0.88, 0.56, 0.38, 1.0]     # Warm undertone
print(f'  Skin: {old_skin} → {b["skinMainColor"][:3]} (tanned)')

# Face makeup warmth
bm = f.get('baseMakeup', {})
if isinstance(bm, dict):
    if 'cheekColor' in bm:
        bm['cheekColor'] = [1.0, 0.72, 0.58, 0.5]  # Warm rosy tan
    if 'lipColor' in bm:
        bm['lipColor'] = [1.0, 0.65, 0.50, 0.6]

# ============================================================
# PARAMETER — Marta metadata
# ============================================================
p['firstname'] = 'Marta'
p['lastname'] = 'Lorente'
p['nickname'] = 'Marta'
p['birthMonth'] = 8
p['birthDay'] = 5
p['bloodType'] = 3         # O type
p['personality'] = 12      # Cheerful

# Extended fields
ext = p.get('ExtendedSaveData')
if ext is None:
    p['ExtendedSaveData'] = {}
    ext = p['ExtendedSaveData']
if isinstance(ext, dict):
    ext['birthdayJP'] = '8月5日'
    ext['sign'] = '獅子座 (Leo)'
    ext['hobby'] = 'surfing, photography'
    ext['favoriteFood'] = 'tropical fruits and seafood'
    ext['favoriteColor'] = 'white, gold'
    ext['simply'] = 'just being herself'
    ext['traits'] = 'bright, slightly clumsy but earnest'
    for k, v in ext.items():
        print(f'  {k}: {v}')

# ============================================================
# SAVE as .png (game-loadable format)
# ============================================================
OUT.parent.mkdir(parents=True, exist_ok=True)
c.save(str(OUT))
sz = OUT.stat().st_size
print(f'\nSaved: {OUT.name} ({sz} bytes, {sz/1024:.1f} KB)')

# ============================================================
# VERIFY
# ============================================================
c2 = KoikatuCharaData.load(str(OUT))
h2 = c2.Custom.data['hair']
f2 = c2.Custom.data['face']
b2 = c2.Custom.data['body']
p2 = c2.Parameter.data

print(f'\n=== VERIFY ===')
print(f'Name: {p2["firstname"]} {p2["lastname"]} / nick={p2["nickname"]}')
print(f'Bday: {p2["birthMonth"]}/{p2["birthDay"]} Blood: {p2["bloodType"]} Personality: {p2["personality"]}')
for part in h2['parts']:
    if part['id'] != 0:
        print(f'Hair: id={part["id"]} base=[{part["baseColor"][0]:.3f},{part["baseColor"][1]:.3f},{part["baseColor"][2]:.3f}]')
for eye in f2['pupil']:
    if eye['id'] != 0:
        print(f'Eye: id={eye["id"]} base=[{eye["baseColor"][0]:.3f},{eye["baseColor"][1]:.3f},{eye["baseColor"][2]:.3f}]')
print(f'Skin: [{b2["skinMainColor"][0]:.3f},{b2["skinMainColor"][1]:.3f},{b2["skinMainColor"][2]:.3f}]')

# Verify blocks match
assert c2.blockdata == c.blockdata, "Block list changed!"
print(f'Blocks: {c2.blockdata} (unchanged)')
print(f'File size: {OUT.stat().st_size} bytes (same as base: {BASE.stat().st_size} bytes)')

print('\nDone — MartaLorente.png ready for render!')
