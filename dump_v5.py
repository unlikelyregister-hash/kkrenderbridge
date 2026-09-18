#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet)

print("dir(chara):", [x for x in dir(chara) if not x.startswith('_')])
print("len blocks:", len(chara.blocks))
for i, blk in enumerate(chara.blocks):
    print(f"[{i}] name={blk.name} id=0x{blk.id:04X} data_len={len(blk.data)}")
    print(f"    data first 32: {blk.data[:32].hex()}")
print()
print("=== Parameter data ===")
p = chara.data['Parameter']
print("type:", type(p))
print("dir:", [x for x in dir(p) if not x.startswith('_')])
print("data keys:", list(p.data.keys()) if isinstance(p.data, dict) else type(p.data))
