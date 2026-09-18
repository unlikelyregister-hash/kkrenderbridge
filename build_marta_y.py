import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

SRC = 'C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge/base_1.png'
DST = 'C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge/Marta_Y.png'
SHARE = 'C:/Games/Koikatsu/UserData/Share/Marta_Y.png'

card = KoikatuCharaData.load(str(SRC))
c = card.Custom.data

# --- Hair: switch from kind=0 (short) to kind=1 (long wavy) ---
c['hair']['kind'] = 1
for i, part in enumerate(c['hair']['parts']):
    if part is None:
        continue
    id_override = 22 if i == 0 else (5 if i == 1 else 0)
    if id_override != 0 or part['id'] != 0:
        part['id'] = id_override
    bc = part['baseColor']
    part['baseColor'] = [0.94, 0.80, 0.52, bc[3] if len(bc) > 3 else 1.0]
    sc = part['startColor']
    part['startColor'] = [0.75, 0.62, 0.40, sc[3] if len(sc) > 3 else 1.0]
    ec = part['endColor']
    part['endColor'] = [1.0, 0.88, 0.60, ec[3] if len(ec) > 3 else 1.0]
    oc = part.get('outlineColor', None)
    if oc:
        part['outlineColor'] = [0.45, 0.35, 0.20, oc[3] if len(oc) > 3 else 1.0]
    ac = part.get('acsColor', [])
    if ac and len(ac) > 1:
        ac[0] = [0.95, 0.82, 0.55, 1.0]

# --- Eyes: id=2 -> id=6, pink -> hazel (BR-Chan proven values) ---
for p in c['face']['pupil']:
    p['id'] = 6
    p['baseColor'] = [0.580, 0.537, 0.420, 1.0]
    p['subColor'] = [0.667, 0.824, 0.471, 1.0]

# --- Eyebrow: black ---
c['face']['eyebrowColor'] = [0.0, 0.0, 0.0, 1.0]

# --- Skin: warm-pink -> tanned ---
c['body']['skinMainColor'] = [0.94, 0.74, 0.52, 1.0]
c['body']['skinSubColor'] = [1.0, 0.78, 0.59, 1.0]
c['face']['skinMainColor'] = [0.94, 0.74, 0.52, 1.0]
c['face']['skinSubColor'] = [1.0, 0.78, 0.59, 1.0]

# --- Lips: more pink ---
c['face']['lipColor'] = [0.882, 0.498, 0.498, 1.0]

# --- Metadata ---
p = card.Parameter.data
p['lastname'] = 'Lorente'
p['firstname'] = 'Marta'
p['nickname'] = 'Marta'
p['callType'] = 0
p['personality'] = 12
p['bloodType'] = 0
p['birthMonth'] = 8
p['birthDay'] = 5
p['clubActivities'] = 3
p['voiceRate'] = 1.0
p['weakPoint'] = 15

card.save(str(DST))
print(f'Saved: {DST}')

import shutil
shutil.copy(str(DST), SHARE)
print(f'Copied: {SHARE}')
print(f'Size: {Path(DST).stat().st_size} bytes')

# Verify
verify = KoikatuCharaData.load(str(DST))
vc = verify.Custom.data
print()
print('=== Verification ===')
print(f'Hair kind: {vc["hair"]["kind"]}')
for i, pt in enumerate(vc['hair']['parts']):
    if pt and pt['id'] != 0:
        print(f'  part[{i}] id={pt["id"]} base={pt["baseColor"][:3]}')
print(f'Eye id: {vc["face"]["pupil"][0]["id"]} base={vc["face"]["pupil"][0]["baseColor"][:3]}')
print(f'Skin main: {vc["body"]["skinMainColor"][:3]}')
print(f'Name: {verify.Parameter.data["lastname"]} {verify.Parameter.data["firstname"]}')
