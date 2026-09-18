#!/usr/bin/env python3
"""Scan ALL .png files in chara/female for visual parameters and find nearest match to Marta."""
import os, sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

chara_dir = Path(r'C:\Games\Koikatsu\UserData\chara\female')
results = []

for f in chara_dir.glob('*.png'):
    try:
        sz = f.stat().st_size
        if sz < 300000:
            continue
        chara = KoikatuCharaData.load(str(f))
        data = chara.data
        if data is None:
            continue
        pdata = data.get('Parameter', {})
        custom = data.get('Custom', {})
        cdata = custom.data if hasattr(custom, 'data') else {}
        
        hair = cdata.get('hair', {}).get('parts', [])
        face = cdata.get('face', {})
        body = cdata.get('body', {})
        param = data.get('Parameter', {}) if hasattr(data, 'data') else {}
        
        hair_base = None
        hair_kind = None
        for part in hair:
            pid = part.get('id', 0)
            if pid != 0:
                bc = part.get('baseColor', [0,0,0,1])
                if hair_base is None or (bc[0] > 0.5):  # prefer colored over black
                    hair_base = bc
                    hair_kind = part.get('kind', None)
                    hair_id = pid
        
        pupil = None
        if face.get('pupil'):
            pupil = face['pupil'][0].get('baseColor', None) if isinstance(face['pupil'], list) else face['pupil'].get('baseColor', None)
        
        skin = body.get('skinMainColor', None)
        skin2 = face.get('skinMainColor', None)
        
        # param data
        name = None
        if isinstance(param, dict):
            name = param.get('name') or param.get('firstname') or ''
        
        results.append({
            'file': f.name,
            'size': sz,
            'name': name,
            'hair_base': hair_base,
            'hair_kind': hair_kind,
            'hair_id': hair_id if 'hair_id' in dir() else None,
            'pupil': pupil,
            'skin_body': skin,
            'skin_face': skin2,
            'param_type': type(param).__name__,
            'custom_type': type(custom).__name__,
            'data_type': type(data).__name__,
        })
    except Exception as e:
        results.append({'file': f.name, 'error': str(e)[:100], 'size': f.stat().st_size})

print(f'Total large cards: {len(results)}')
print()
print('=== SAMPLE (first 15) ===')
for r in results[:15]:
    if 'error' not in r:
        print(f"{r['file'][:50]:50s} sz={r['size']:>8d} name={r['name']}")
        print(f"  hair_base={r['hair_base']} kind={r['hair_kind']} id={r.get('hair_id')}")
        print(f"  pupil={r['pupil']} skin_body={r['skin_body']} skin_face={r['skin_face']}")
        print(f"  param={r['param_type']} custom={r['custom_type']} data={r['data_type']}")
    else:
        print(f"{r['file'][:50]:50s} sz={r['size']:>8d} ERROR={r['error']}")
    print()
