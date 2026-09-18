#!/usr/bin/env python3
import os, sys, json
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet_path = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet_path)

print("=== blockdata ===")
for name in chara.blockdata:
    blk = chara.modules[name]
    print(f"  {name}: id=0x{blk.id:04X} data_len={len(blk.data)} first32={blk.data[:32].hex()}")
print()

print("=== Parameter ===")
p = chara.modules['Parameter']
print(f"  id=0x{p.id:04X} name={p.name} data_len={len(p.data)}")
try:
    pj = json.loads(p.data.decode('utf-8-sig'))
    print(f"  JSON keys ({len(pj)}): {list(pj.keys())}")
    for k, v in pj.items():
        if isinstance(v, (list, dict)):
            print(f"    {k}: {type(v).__name__}")
            if isinstance(v, list):
                for i, item in enumerate(v[:5]):
                    print(f"      [{i}]: {item}")
                if len(v) > 5:
                    print(f"      ... ({len(v)-5} more)")
            else:
                for i, (ik, iv) in enumerate(v.items()):
                    if isinstance(iv, list):
                        print(f"      {ik}: list[{len(iv)}] {iv[:3]}{'...' if len(iv)>3 else ''}")
                    else:
                        print(f"      {ik}: {iv}")
        else:
            print(f"    {k}: {v}")
except Exception as e:
    print(f"  Not JSON: {e}")
    print(f"  first 300: {p.data[:300]}")
print()

print("=== Custom ===")
c = chara.modules['Custom']
print(f"  id=0x{c.id:04X} name={c.name} data_len={len(c.data)}")
try:
    cj = json.loads(c.data.decode('utf-8-sig'))
    print(f"  JSON keys ({len(cj)}): {list(cj.keys())}")
    for k, v in cj.items():
        if isinstance(v, (list, dict)):
            print(f"    {k}: {type(v).__name__} len={len(v)}")
            if isinstance(v, list) and len(v) < 20:
                for i, item in enumerate(v):
                    print(f"      [{i}]: {item}")
            elif isinstance(v, dict):
                for ik, iv in list(v.items())[:30]:
                    if isinstance(iv, list):
                        print(f"      {ik}: list[{len(iv)}] {iv[:3]}{'...' if len(iv)>3 else ''}")
                    else:
                        print(f"      {ik}: {iv}")
        else:
            print(f"    {k}: {v}")
except Exception as e:
    print(f"  Not JSON: {e}")
    print(f"  first 500: {c.data[:500]}")
