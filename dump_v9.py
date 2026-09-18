#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet_path = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet_path)

print("=== chara.blockdata (list) ===")
print(f"  len={len(chara.blockdata)}")
for i, blk in enumerate(chara.blockdata):
    print(f"  [{i}] id=0x{blk.id:04X} name={blk.name} data_len={len(blk.data)} first32={blk.data[:32].hex()}")
print()

print("=== chara.modules (dict) ===")
for k, blk in chara.modules.items():
    print(f"  {k}: id=0x{blk.id:04X} name={blk.name} data_len={len(blk.data)} first32={blk.data[:32].hex()}")
print()

print("=== Parameter.detail ===")
p = chara.modules['Parameter']
print(f"  type={type(p)} dir={[x for x in dir(p) if not x.startswith('_')]}")
print(f"  id={p.id} name={p.name}")
print(f"  data len={len(p.data)}")
# Try to parse as JSON
import json
try:
    pj = json.loads(p.data.decode('utf-8-sig'))
    print(f"  JSON keys: {list(pj.keys())}")
    for k, v in pj.items():
        if isinstance(v, (list, dict)):
            print(f"    {k}: {type(v).__name__} len={len(v)}")
        else:
            print(f"    {k}: {v}")
except Exception as e:
    print(f"  Not JSON: {e}")
    print(f"  first 200 bytes: {p.data[:200]}")
print()

print("=== Custom.detail ===")
c = chara.modules['Custom']
print(f"  type={type(c)} dir={[x for x in dir(c) if not x.startswith('_')]}")
print(f"  id={c.id} name={c.name}")
print(f"  data len={len(c.data)}")
try:
    cj = json.loads(c.data.decode('utf-8-sig'))
    print(f"  JSON keys: {list(cj.keys())}")
    for k, v in cj.items():
        if isinstance(v, (list, dict)):
            print(f"    {k}: {type(v).__name__} len={len(v)}")
        else:
            print(f"    {k}: {v}")
except Exception as e:
    print(f"  Not JSON: {e}")
    print(f"  first 200: {c.data[:200]}")
