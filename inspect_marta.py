#!/usr/bin/env python3
import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData
import json

c = KoikatuCharaData.load('C:/Users/Administrator/kk-workspace/MartaLorente_Inspired.kkpe')

# Use the same attribute access pattern as dump_v8.py showed
hair = c.hair
face = c.face
body = c.body

print('=== Hair ===')
print('kind:', hair.get('kind') if isinstance(hair, dict) else 'N/A')
if isinstance(hair, dict):
    for i, part in enumerate(hair.get('parts', [])):
        print(f'  part[{i}]: id={part.get("id")} baseColor={part.get("baseColor")}')

print()
print('=== Face ===')
print('type:', type(face).__name__)
if isinstance(face, dict):
    for k in ['headId','skinId','detailId','pupil','skinMainColor','skinSubColor','eyebrowColor','lipLineColor']:
        v = face.get(k)
        if k == 'pupil' and isinstance(v, list):
            print(f'  pupil[0]: {json.dumps(v[0]) if v else "N/A"}')
        else:
            print(f'  {k}: {v}')
    bm = face.get('baseMakeup', {})
    if isinstance(bm, dict):
        print('  baseMakeup:')
        for bk, bv in bm.items():
            print(f'    {bk}: {bv}')
else:
    print('  face is not a dict:', type(face))
    print('  dir:', [x for x in dir(face) if not x.startswith('_')])

print()
print('=== Body ===')
print('type:', type(body).__name__)
if isinstance(body, dict):
    for k in ['skinId','skinMainColor','skinSubColor','sunburnColor','shapeValueBody']:
        v = body.get(k)
        print(f'  {k}: {v}')
else:
    print('  body is not a dict:', type(body))

print()
print('=== Coordinate ===')
coord = c.coordinate
print('type:', type(coord).__name__)
if isinstance(coord, dict):
    print('  keys:', list(coord.keys()))
