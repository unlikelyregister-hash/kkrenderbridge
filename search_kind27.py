#!/usr/bin/env python3
import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

gdir = Path('C:/Games/Koikatsu/UserData/chara')

results = []
for f in sorted(gdir.rglob('*.png')):
    try:
        sz = f.stat().st_size
        if sz < 300000:
            continue
        c = KoikatuCharaData.load(str(f))
        cd = c.Custom.data
        hair = cd.get('hair', {})
        face = cd.get('face', {})
        body = cd.get('body', {})
        
        kind = hair.get('kind', -1)
        eb, epup = False, None
        for p in face.get('pupil', []):
            bc = p.get('baseColor', [0,0,0,1])
            if 0.50 <= bc[0] <= 0.75 and 0.30 <= bc[1] <= 0.65 and 0.20 <= bc[2] <= 0.50:
                eb = True
                epup = p
                break
        
        if kind == 27 or eb:
            results.append({
                'file': str(f.relative_to(gdir)),
                'kind': kind,
                'eye_hazel': eb,
                'eye_id': epup.get('id') if epup else None,
                'eye_bc': epup.get('baseColor') if epup else None,
                'name': c.Parameter.data.get('name', ''),
            })
    except:
        pass

print(f"Results (kind=27 or hazel eyes): {len(results)}")
for r in results:
    print(f"  {r['file']}: kind={r['kind']} hazel={r['eye_hazel']} eye_id={r['eye_id']} eye_bc={r['eye_bc']} name={r['name']}")

print()
print("=== ALL distinct hair kind values (blonde cards) ===")
kinds = set()
for f in sorted(gdir.rglob('*.png')):
    try:
        sz = f.stat().st_size
        if sz < 300000:
            continue
        c = KoikatuCharaData.load(str(f))
        hair = c.Custom.data.get('hair', {})
        for part in hair.get('parts', []):
            bc = part.get('baseColor', [0,0,0,1])
            if bc[0] > 0.85 and bc[1] > 0.6 and bc[2] < 0.7:
                kinds.add(hair.get('kind'))
                break
    except:
        pass

print(f"Blonde hair kinds found: {sorted(kinds)}")
print(f"Count: {len(kinds)}")
