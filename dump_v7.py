#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet_path = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet_path)

print("=== chara.MODULES type:", type(chara.MODULES))
if isinstance(chara.MODULES, dict):
    for k, v in chara.MODULES.items():
        print(f"  key={k!r} value type={type(v)} value={v}")
print()

print("=== chara.data keys ===")
for k in chara.data:
    blk = chara.data[k]
    print(f"  {k}: type={type(blk)} id={getattr(blk, 'id', '?')} name={getattr(blk, 'name', '?')} data_len={len(blk.data) if hasattr(blk, 'data') else '?'}")
print()

print("=== Parameter ===")
p = chara.data['Parameter']
print(f"  type={type(p)}")
print(f"  id={getattr(p, 'id', '?')} name={getattr(p, 'name', '?')}")
print(f"  data keys={list(p.data.keys()) if hasattr(p, 'data') and isinstance(p.data, dict) else 'N/A'}")
if hasattr(p, 'data') and isinstance(p.data, dict):
    for k in p.data:
        v = p.data[k]
        if isinstance(v, list):
            print(f"    {k}: list[{len(v)}] = {v}")
        else:
            print(f"    {k}: {v}")
print()

print("=== Custom ===")
c = chara.data['Custom']
print(f"  type={type(c)}")
print(f"  id={getattr(c, 'id', '?')}")
print(f"  data len={len(c.data)}")
print(f"  first 64: {c.data[:64].hex()}")
print(f"  last 64: {c.data[-64:].hex()}")
