#!/usr/bin/env python3
"""Build Marta Lorente Inspired card from base_2.png (appearance modification).

Uses base_2.png as the base, modifies hair/eye/skin colors toward Marta's look,
sets Marta's metadata, saves as new card in kkRenderBridge folder.

Clothing is left unchanged per user request (handled separately).

Goal appearance:
  Hair: blonde, wavy, side-part → baseColor [0.95, 0.82, 0.55]
  Eyes: hazel type #08 → baseColor [0.58, 0.48, 0.28]
  Skin: tanned type #04 → skinMainColor [0.98, 0.76, 0.55]
"""

import sys, json
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

BASE_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
OUT_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente_v1.kkpe')

print(f'Loading base card: {BASE_CARD}')
c = KoikatuCharaData.load(str(BASE_CARD))
print(f'Loaded OK. blockdata: {c.blockdata}')
print()

# ============================================================
# 1. Modify Custom block: hair, eyes, skin
# ============================================================

# --- Hair: recolor to blonde ---
hair = c.Custom.data['hair']
print(f'Original hair: kind={hair["kind"]}, parts={len(hair["parts"])}')
for i, part in enumerate(hair['parts']):
    if part['id'] == 0:
        continue
    orig = part['baseColor'][:3]
    part['baseColor'] = [0.95, 0.82, 0.55, 1.0]
    part['startColor'] = [0.75, 0.55, 0.30, 1.0]
    part['endColor'] = [1.0, 0.90, 0.70, 1.0]
    print(f'  Part {i}: id={part["id"]} → blonde {part["baseColor"]}')

# --- Eyes: recolor to hazel ---
face = c.Custom.data['face']
for p in face['pupil']:
    orig = p['baseColor'][:3]
    p['baseColor'] = [0.58, 0.48, 0.28, 1.0]
    p['subColor'] = [0.45, 0.32, 0.18, 1.0]
    print(f'  Pupil id={p["id"]} → hazel {p["baseColor"]}')

# --- Skin: recolor to tanned ---
body = c.Custom.data['body']
body['skinMainColor'] = [0.98, 0.76, 0.55, 1.0]  # tanned
body['skinSubColor'] = [0.92, 0.58, 0.40, 1.0]   # warm undertone
print(f'  Body skin → tanned {body["skinMainColor"]}')

# Warm tan tones for face makeup
bm = face.get('baseMakeup', {})
if 'cheekColor' in bm:
    bm['cheekColor'] = [1.0, 0.75, 0.60, 0.6]
if 'lipColor' in bm:
    bm['lipColor'] = [1.0, 0.70, 0.55, 0.7]
print(f'  Face makeup → warm tan tones')

print()

# ============================================================
# 2. Set Parameter metadata for Marta
# ============================================================

param = c.Parameter.data  # .data is the dict

# Map Marta fields to Parameter fields
param['lastname'] = ''        # empty (Marta is first name only)
param['firstname'] = 'Marta Lorente'  # or just 'Marta'
param['nickname'] = 'Marta'
param['birthMonth'] = 8
param['birthDay'] = 5
param['bloodType'] = 4        # O type (check enum: A=0? B=1? AB=2? O=3? or 4?)
# Koikatsu blood types: A=0, B=1, AB=2, O=3 — so O = 3
# Let me use 3 for O
param['bloodType'] = 3
param['personality'] = 12     # cheerful

# Check existing keys for traits/hobby/etc.
print(f'\nParameter data keys: {list(param.keys())}')
print(f'Existing traits/hobby/favorite fields: ', end='')
for k in param.keys():
    if any(x in k.lower() for x in ['trait', 'hobby', 'fav', 'color', 'food', 'sign', 'birth', 'sim']):
        print(f'{k}={repr(param[k])[:60]} ', end='')
print()

# Try to set additional fields that may exist in ExtendedSaveData or unknown fields
# The Parameter block has .data dict which we can extend
ext = param.get('ExtendedSaveData')
if ext is None:
    param['ExtendedSaveData'] = {}

print('\nSetting custom fields in ExtendedSaveData...')
ext = param['ExtendedSaveData']
if isinstance(ext, dict):
    ext['birthdayJP'] = '8月5日'
    ext['sign'] = '獅子座 (Leo)'
    ext['hobby'] = 'surfing, photography'
    ext['favoriteFood'] = 'tropical fruits and seafood'
    ext['favoriteColor'] = 'white, gold'
    ext['simply'] = 'just being herself'
    ext['traits'] = 'bright, slightly clumsy but earnest'
    print(f'  Set {len(ext)} custom fields')
else:
    print(f'  ExtendedSaveData is not a dict: {type(ext)}')

print()

# ============================================================
# 3. Save
# ============================================================

OUT_CARD.parent.mkdir(parents=True, exist_ok=True)
c.save(str(OUT_CARD))
sz = OUT_CARD.stat().st_size
print(f'Saved: {OUT_CARD} ({sz} bytes / {sz/1024:.1f} KB)')

# Verify
c2 = KoikatuCharaData.load(str(OUT_CARD))
print(f'\nRe-load OK')

hair2 = c2.Custom.data['hair']
print(f'Hair part 0 baseColor: {hair2["parts"][0]["baseColor"]}')
face2 = c2.Custom.data['face']
print(f'Pupil 0 baseColor: {face2["pupil"][0]["baseColor"]}')
body2 = c2.Custom.data['body']
print(f'SkinMainColor: {body2["skinMainColor"]}')

p2 = c2.Parameter.data
print(f'\nParam firstname: {p2["firstname"]}')
print(f'Param nickname: {p2["nickname"]}')
print(f'Param birthMonth/Day: {p2["birthMonth"]}/{p2["birthDay"]}')
print(f'Param bloodType: {p2["bloodType"]}')
print(f'Param personality: {p2["personality"]}')

ext2 = p2.get('ExtendedSaveData', {})
print(f'ExtendedSaveData keys: {list(ext2.keys())}')
for k, v in ext2.items():
    print(f'  {k}: {v}')

print('\nDone!')
