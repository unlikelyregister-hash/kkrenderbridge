#!/usr/bin/env python3
"""Modify base_2.png → Marta Lorente appearance.
Use base_2.png as the base, modify hair/eye/skin colors, set Marta metadata.
Save as MartaLorente_v1.kkpe in kkRenderBridge folder. Clothing unchanged.

Goal appearance:
  Hair: blonde, wavy, side-part → baseColor [0.95, 0.82, 0.55]
  Eyes: hazel type #08 → baseColor [0.55, 0.42, 0.25]
  Skin: tanned type #04 → skinMainColor [0.92, 0.70, 0.48]
"""

import sys, json
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

BASE_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
OUT_CARD = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente_v1.kkpe')

print(f'Loading base card: {BASE_CARD}')
c = KoikatuCharaData.load(str(BASE_CARD))
print(f'Loaded OK. blocks: {c.blockdata}')
print()

orig_data = c.Custom.data

# --- Hair: recolor to blonde ---
hair = orig_data['hair']
print(f'Hair kind={hair["kind"]}, {len(hair["parts"])} parts')
for p in hair['parts']:
    if p['id'] == 0:
        continue
    p['baseColor'] = [0.93, 0.80, 0.50, 1.0]    # blonde base
    p['startColor'] = [0.80, 0.60, 0.35, 1.0]   # root dark blonde
    p['endColor'] = [0.98, 0.88, 0.65, 1.0]      # bright blonde tips
    p['outlineColor'] = [0.15, 0.12, 0.08, 1.0]  # dark outline
    print(f'  Part id={p["id"]} → blonde')

# --- Eyes: recolor to hazel ---
face = orig_data['face']
for p in face['pupil']:
    p['baseColor'] = [0.55, 0.42, 0.25, 1.0]    # hazel green-brown
    p['subColor'] = [0.42, 0.30, 0.15, 1.0]     # darker hazel ring
    print(f'  Pupil id={p["id"]} → hazel')

# --- Skin: recolor to tanned ---
body = orig_data['body']
body['skinMainColor'] = [0.92, 0.70, 0.48, 1.0]  # tanned
body['skinSubColor'] = [0.85, 0.50, 0.32, 1.0]   # warm undertone
print(f'Skin → tanned {body["skinMainColor"]}')

# Warm face makeup
bm = face.get('baseMakeup', {})
if isinstance(bm, dict):
    if 'cheekColor' in bm:
        bm['cheekColor'] = [1.0, 0.72, 0.58, 0.5]
    if 'lipColor' in bm:
        bm['lipColor'] = [1.0, 0.65, 0.50, 0.6]
    print('Face makeup → warm tones')

print()

# --- Parameter: Marta metadata ---
p = c.Parameter.data
p['firstname'] = 'Marta'
p['lastname'] = ''
p['nickname'] = 'Marta'
p['birthMonth'] = 8
p['birthDay'] = 5
p['bloodType'] = 3      # O type
p['personality'] = 12   # cheerful

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
    print(f'Parameter: {p["firstname"]} {p["lastname"]} / nick={p["nickname"]}')
    print(f'  Birthday: {p["birthMonth"]}/{p["birthDay"]}, Blood: {p["bloodType"]}, Personality: {p["personality"]}')
    print(f'  Extended ({len(ext)} fields): birthdayJP, sign, hobby, favoriteFood, favoriteColor, simply, traits')

# --- Save ---
OUT_CARD.parent.mkdir(parents=True, exist_ok=True)
c.save(str(OUT_CARD))
sz = OUT_CARD.stat().st_size
print(f'\nSaved: {OUT_CARD} ({sz} bytes, {sz/1024:.1f} KB)')

# Verify
c2 = KoikatuCharaData.load(str(OUT_CARD))
h = c2.Custom.data['hair']
print(f'\nVerify hair part0 baseColor: {h["parts"][0]["baseColor"]}')
f = c2.Custom.data['face']
print(f'Verify pupil0 baseColor: {f["pupil"][0]["baseColor"]}')
b = c2.Custom.data['body']
print(f'Verify skinMainColor: {b["skinMainColor"]}')
p2 = c2.Parameter.data
print(f'Verify name: {p2["firstname"]} {p2["lastname"]} / nick={p2["nickname"]}')

print('\nDone!')
