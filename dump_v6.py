#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet)

print("=== KoikatuCharaData.MODULES (namedtuple fields) ===")
for name in chara.MODULES._fields:
    blk = getattr(chara, name, None)
    print(f"  {name}: id=0x{blk.id:04X} len={len(blk.data)}  first32={blk.data[:32].hex() if blk.data else 'None'}")
print()

print("=== chara.data keys ===")
print(list(chara.data.keys()))
print()

print("=== Parameter block ===")
p = chara.data['Parameter']
print(f"type: {type(p)}")
print(f"dir: {[x for x in dir(p) if not x.startswith('_')]}")
if hasattr(p, 'data'):
    print(f"data type: {type(p.data)}")
    print(f"data: {p.data}")
print()

print("=== Custom block ===")
c = chara.data['Custom']
print(f"type: {type(c)}")
print(f"dir: {[x for x in dir(c) if not x.startswith('_')]}")
if hasattr(c, 'data'):
    print(f"data type: {type(c.data)}")
    print(f"data len: {len(c.data)}")
    print(f"data first 64 bytes hex: {c.data[:64].hex()}")
