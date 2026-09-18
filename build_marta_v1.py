#!/usr/bin/env python3
"""Build MartaLorente_v1.kkpe from base_2.png with Marta's appearance.

Uses base_2.png as the base (preserves clothing), modifies hair/eye/skin to
match Marta Lorente's look (blonde hair, hazel eyes, tanned skin), and sets
Marta's metadata.

Hair style: kind=1 (same as base_2, keeps the hair mesh), recolored to blonde
Eyes: hazel (id=6 per Card5 reference, color set to warm hazel)
Skin: tanned (id=0 kept, color overridden to tanned)
Clothing: left unchanged from base_2 (per user request)
"""

import sys, json
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

BASE_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
OUT_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente_v1.kkpe')

print(f'Loading base card: {BASE_CARD}')
c = KoikatuCharaData.load(str(BASE_CARD))
print(f'Loaded OK. Blocks: {c.blockdata}')
print()

# Get the actual dict data
custom = c.Custom.data
param = c.Parameter.data

# ============================================================
# 1. HAIR — recolor to blonde, keep kind=1
# ============================================================
hair = custom['hair']
print(f'Hair: kind={hair["kind"]}, {len(hair["parts"])} parts')

# Card5 blonde reference: baseColor=[0.887, 0.605, 0.354]
# We want a brighter blonde (Marta's is light blonde/sandy)
blonde_base = [0.92, 0.78, 0.50, 1.0]    # Sandy blonde base
blonde_start = [0.82, 0.62, 0.38, 1.0]   # Slightly darker root
blonde_end = [0.97, 0.87, 0.62, 1.0]     # Bright blonde tips
blonde_accent = [1.0, 0.80, 0.70, 1.0]   # Highlight accent
blonde_outline = [0.18, 0.15, 0.10, 1.0] # Dark outline

for p in hair['parts']:
    if p['id'] == 0:
        continue  # skip empty slots
    old = p['baseColor']
    p['baseColor'] = list(blonde_base)
    p['startColor'] = list(blonde_start)
    p['endColor'] = list(blonde_end)
    # Update accent colors
    if 'acsColor' in p:
        acs = p['acsColor']
        if isinstance(acs, list) and len(acs) > 0 and isinstance(acs[0], list):
            acs[0] = list(blonde_accent)
    if 'outlineColor' in p:
        p['outlineColor'] = list(blonde_outline)
    print(f'  Part id={p["id"]}: {old[:3]} → blonde {p["baseColor"][:3]}')

# ============================================================
# 2. EYES — change to hazel
# ============================================================
face = custom['face']
print(f'\nEyes:')
for p in face['pupil']:
    if p['id'] == 0:
        continue
    old = p['baseColor']
    # Hazel: warm green-brown (#08 type reference from Card5)
    p['baseColor'] = [0.54, 0.46, 0.25, 1.0]   # Hazel green-brown
    p['subColor'] = [0.42, 0.32, 0.15, 1.0]    # Darker inner ring
    # Keep the gradMask but adjust for hazel look
    # Card5 uses id=6, baseColor=[0.536, 0.453, 0.246]
    print(f'  Pupil id={p["id"]}: {old[:3]} → hazel {p["baseColor"][:3]}')

# ============================================================
# 3. SKIN — change to tanned
# ============================================================
body = custom['body']
old_skin = body['skinMainColor']
body['skinMainColor'] = [0.94, 0.74, 0.52, 1.0]   # Tanned (Marta's tan)
body['skinSubColor'] = [0.88, 0.56, 0.38, 1.0]    # Warm undertone
print(f'\nSkin: {old_skin[:3]} → tanned {body["skinMainColor"][:3]}')

# Face skin color (via makeup cheek/lip)
bm = face.get('baseMakeup', {})
if isinstance(bm, dict):
    if 'cheekColor' in bm:
        bm['cheekColor'] = [1.0, 0.74, 0.62, 0.5]  # Warm rosy tan
    if 'lipColor' in bm:
        bm['lipColor'] = [1.0, 0.68, 0.55, 0.6]    # Natural lip
    print(f'Face makeup adjusted for tan')

# ============================================================
# 4. PARAMETER — Marta's metadata
# ============================================================
print(f'\nParameter metadata:')
param['firstname'] = 'Marta'
param['lastname'] = 'Lorente'
param['nickname'] = 'Marta'
param['birthMonth'] = 8
param['birthDay'] = 5
param['bloodType'] = 3      # O type
param['personality'] = 12   # cheerful (12=cheerful in KK)

# Set ExtendedSaveData fields
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
    for k, v in ext.items():
        print(f'  ext.{k} = {v}')

# ============================================================
# 5. SAVE
# ============================================================
OUT_CARD.parent.mkdir(parents=True, exist_ok=True)
c.save(str(OUT_CARD))
sz = OUT_CARD.stat().st_size
print(f'\nSaved: {OUT_CARD} ({sz} bytes, {sz/1024:.1f} KB)')

# ============================================================
# 6. VERIFY
# ============================================================
c2 = KoikatuCharaData.load(str(OUT_CARD))
h2 = c2.Custom.data['hair']
print(f'\n=== VERIFY ===')
print(f'Blocks: {c2.blockdata}')

for p in h2['parts']:
    if p['id'] != 0:
        print(f'Hair part id={p["id"]}: baseColor={p["baseColor"][:3]}')

for p in c2.Custom.data['face']['pupil']:
    if p['id'] != 0:
        print(f'Eye pupil id={p["id"]}: baseColor={p["baseColor"][:3]}')

print(f'Skin: main={c2.Custom.data["body"]["skinMainColor"][:3]}')
print(f'Name: {c2.Parameter.data["firstname"]} {c2.Parameter.data["lastname"]}')
print(f'Nickname: {c2.Parameter.data["nickname"]}')
print(f'Birthday: {c2.Parameter.data["birthMonth"]}/{c2.Parameter.data["birthDay"]}')
print(f'Blood: {c2.Parameter.data["bloodType"]}')
print(f'Personality: {c2.Parameter.data["personality"]}')
ext2 = c2.Parameter.data.get('ExtendedSaveData', {})
for k, v in ext2.items():
    print(f'  {k}: {v}')

print('\nDone!')
