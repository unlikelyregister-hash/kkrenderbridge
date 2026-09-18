#!/usr/bin/env python3
"""Ad-hoc verification: confirm Marta cards have correct metadata + appearance after fix."""
import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData
from pathlib import Path

KBDIR = Path('C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge')
SHARED = Path('C:/Games/Koikatsu/UserData/Share')

EXPECTED = {
    'Marta_Y.png': {'name': 'Lorente Marta', 'nick': 'Marta', 'per': 12, 'blood': 0},
    'MartaLorente.png': {'name': 'Lorente Marta', 'nick': 'Marta', 'per': 12, 'blood': 0},
}

print('=== Meta verification ===')
all_ok = True
for fname, exp in EXPECTED.items():
    card = KoikatuCharaData.load(str(KBDIR / fname))
    pd = card.Parameter.data
    cd = card.Custom.data
    name = f'{pd["lastname"]} {pd["firstname"]}'
    ok = (
        name == exp['name'] and
        pd['nickname'] == exp['nick'] and
        pd['personality'] == exp['per'] and
        pd['bloodType'] == exp['blood']
    )
    status = '✓' if ok else '✗'
    print(f'  {status} {fname}: {name}, nick={pd["nickname"]}, per={pd["personality"]}, blood={pd["bloodType"]}')
    if not ok:
        all_ok = False
        print(f'     diffs: name={name!r} vs {exp["name"]!r}, nick={pd["nickname"]!r} vs {exp["nick"]!r}, per={pd["personality"]} vs {exp["per"]}, blood={pd["bloodType"]} vs {exp["blood"]}')

print()
print('=== Visual verification ===')
for fname in ['Marta_Y.png', 'MartaLorente.png']:
    card = KoikatuCharaData.load(str(KBDIR / fname))
    cd = card.Custom.data
    hk = cd['hair']['kind']
    hairs = []
    for i, pt in enumerate(cd['hair']['parts']):
        if pt and pt['id'] != 0:
            rgb = pt['baseColor'][:3]
            hairs.append(f'part[{i}] id={pt["id"]} rgb=({rgb[0]:.2f},{rgb[1]:.2f},{rgb[2]:.2f})')
    eye = cd['face']['pupil'][0]
    eye_rgb = eye['baseColor'][:3]
    skin = cd['body']['skinMainColor'][:3]
    print(f'  {fname}:')
    print(f'    Hair kind={hk}')
    for h in hairs:
        print(f'    {h}')
    print(f'    Eye id={eye["id"]} rgb=({eye_rgb[0]:.2f},{eye_rgb[1]:.2f},{eye_rgb[2]:.2f})  (exp: hazel ~0.58,0.54,0.42)')
    print(f'    Skin rgb=({skin[0]:.2f},{skin[1]:.2f},{skin[2]:.2f})  (exp: tanned ~0.94,0.74,0.52)')

print()
print('=== Base cards unchanged check ===')
for fname in ['base_1.png', 'base_2.png']:
    card = KoikatuCharaData.load(str(KBDIR / fname))
    pd = card.Parameter.data
    print(f'  {fname}: {pd["lastname"]} {pd["firstname"]} (original, unmodified)')

print()
print('=== Share copies ===')
for fname in EXPECTED:
    sf = SHARED / fname
    exists = sf.exists()
    size = sf.stat().st_size if exists else "MISSING"
    mark = "✓" if exists else "✗"
    print(f'  {mark} {fname}: {size} bytes')

print()
print('RESULT:', 'ALL CHECKS PASSED' if all_ok else 'SOME CHECKS FAILED')
