#!/usr/bin/env python3
import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

c = KoikatuCharaData.load('C:/Users/Administrator/kk-workspace/MartaLorente_Inspired.kkpe')

print('=== KoikatuCharaData attributes ===')
for a in dir(c):
    if not a.startswith('_'):
        v = getattr(c, a)
        if not callable(v):
            t = type(v).__name__
            if t == 'dict':
                print(f'  {a}: dict({len(v)} keys) -> {list(v.keys())}')
            elif t == 'list':
                print(f'  {a}: list({len(v)}) -> {v[:5]}')
            elif t == 'bytes':
                print(f'  {a}: bytes({len(v)}) -> {v[:32].hex()}')
            else:
                print(f'  {a}: {t} = {v!r}')
print()

# Blockdata
print('=== blockdata ===')
for name in c.blockdata:
    print(f'  blockdata entry: {name!r}')

print()
# modules
print('=== modules ===')
for k, v in c.modules.items():
    print(f'  {k}: {type(v).__name__}')
    if isinstance(v, dict):
        print(f'    keys: {list(v.keys())[:20]}')
        if k in ('Custom', 'Coordinate'):
            if 'parts' in v:
                print(f'    parts: {len(v["parts"])} items')
            if 'data' in v:
                print(f'    data: {type(v["data"]).__name__} len={len(v["data"])}')
