#!/usr/bin/env python3
"""Build MartaLorente_v2.kkpe from base_2.png with Marta's appearance.

Fixed hair/eye/skin asset IDs:
  Hair: kind=1, part id=22 (blonde from Card5 reference), recolored to bright blonde
  Eyes: id=6 (hazel from Card5), color set to warm hazel
  Skin: color overridden to tanned
  Clothing: unchanged from base_2 (per user)
"""

import sys, json
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

BASE_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
OUT_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente_v2.kkpe')

print(f'Loading base card: {BASE_CARD}')
c = KoikatuCharaData.load(str(BASE_CARD))
print(f'Blocks: {c.blockdata}')

custom = c.Custom.data
param = c.Parameter.data

# ============================================================
# HAIR — change part ids to blonde mesh + recolor
# ============================================================
hair = custom['hair']
hair['kind'] = 1  # keep long wavy

# Map old part ids to new blonde ids from Card5 reference
# base_2 uses: part[0]=id45, part[1]=id40, part[2]=id0, part[3]=id0
# Card5 uses: part[0]=id22, part[1]=id5, part[2]=id0, part[3]=id0
# We want: part[0]=id22 (main hair), part[1]=id5 (back hair/strands), rest=0
new_part_map = {45: 22, 40: 5, 0: 0}  # map old id -> new id

for p in hair['parts']:
    old_id = p['id']
    if old_id in new_part_map:
        new_id = new_part_map[old_id]
        p['id'] = new_id
        if new_id != 0:
            # Set blonde colors (Marta has light blonde/sandy)
            p['baseColor'] = [0.94, 0.80, 0.52, 1.0]     # Sandy blonde
            p['startColor'] = [0.84, 0.64, 0.40, 1.0]    # Root shading
            p['endColor'] = [0.99, 0.90, 0.68, 1.0]      # Bright tips
            p['outlineColor'] = [0.20, 0.16, 0.10, 1.0]  # Slightly darker outline
            if 'acsColor' in p and isinstance(p['acsColor'], list) and len(p['acsColor']) > 0:
                p['acsColor'][0] = [1.0, 0.82, 0.72, 1.0]  # Hair highlight accent
            print(f'  Part {old_id}→{new_id}: blonde {p["baseColor"][:3]}')
        else:
            print(f'  Part {old_id}→0: cleared')

# ============================================================
# EYES — change to hazel (id=6 from Card5)
# ============================================================
face = custom['face']
for p in face['pupil']:
    if p['id'] == 0:
        continue
    old_id = p['id']
    p['id'] = 6  # Hazel eye model (same as Card5)
    # Hazel color: warm green-brown
    p['baseColor'] = [0.54, 0.46, 0.24, 1.0]
    p['subColor'] = [0.42, 0.32, 0.14, 1.0]
    print(f'  Pupil {old_id}→6: hazel {p["baseColor"][:3]}')

# ============================================================
# SKIN — tanned
# ============================================================
body = custom['body']
body['skinMainColor'] = [0.94, 0.74, 0.52, 1.0]   # Tanned
body['skinSubColor'] = [0.88, 0.56, 0.38, 1.0]    # Warm undertone
print(f'Skin: → tanned {body["skinMainColor"][:3]}')

# Face warmth
bm = face.get('baseMakeup', {})
if isinstance(bm, dict):
    if 'cheekColor' in bm:
        bm['cheekColor'] = [1.0, 0.74, 0.62, 0.5]
    if 'lipColor' in bm:
        bm['lipColor'] = [1.0, 0.68, 0.55, 0.6]

# ============================================================
# PARAMETER — Marta metadata
# ============================================================
param['firstname'] = 'Marta'
param['lastname'] = 'Lorente'
param['nickname'] = 'Marta'
param['birthMonth'] = 8
param['birthDay'] = 5
param['bloodType'] = 3      # O type
param['personality'] = 12   # cheerful

ext = param.get('ExtendedSaveData')
if ext is None:
    param['ExtendedSaveData'] = {}
    ext = param['ExtendedSaveData']
if isinstance(ext, dict):
    ext['birthdayJP'] = '8月5日'
    ext['sign'] = '獅子座 (Leo)'
    ext['hobby'] = 'surfing, photography'
    ext['favoriteFood'] = 'tropical fruits and seafood'
    ext['favoriteColor'] = 'white, gold'
    ext['simply'] = 'just being herself'
    ext['traits'] = 'bright, slightly clumsy but earnest'

# ============================================================
# SAVE
# ============================================================
OUT_CARD.parent.mkdir(parents=True, exist_ok=True)
c.save(str(OUT_CARD))
sz = OUT_CARD.stat().st_size
print(f'\nSaved: {OUT_CARD} ({sz} bytes, {sz/1024:.1f} KB)')

# VERIFY
c2 = KoikatuCharaData.load(str(OUT_CARD))
h2 = c2.Custom.data['hair']
print(f'\n=== VERIFY ===')
for p in h2['parts']:
    if p['id'] != 0:
        print(f'Hair: id={p["id"]} baseColor={p["baseColor"][:3]}')
for p in c2.Custom.data['face']['pupil']:
    if p['id'] != 0:
        print(f'Eye: id={p["id"]} baseColor={p["baseColor"][:3]}')
print(f'Skin: {c2.Custom.data["body"]["skinMainColor"][:3]}')
print(f'Name: {c2.Parameter.data["firstname"]} {c2.Parameter.data["lastname"]}')
print(f'Nick: {c2.Parameter.data["nickname"]}')
print(f'Bday: {c2.Parameter.data["birthMonth"]}/{c2.Parameter.data["birthDay"]}')
print(f'Blood: {c2.Parameter.data["bloodType"]} (3=O)')
print(f'Personality: {c2.Parameter.data["personality"]} (12=cheerful)')

print('\nDone!')
