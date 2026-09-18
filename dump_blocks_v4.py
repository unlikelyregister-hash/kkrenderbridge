#!/usr/bin/env python3
"""Dump all block tuples from Scarlet Chika card and Parameter JSON."""

import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")

from pathlib import Path
from kkloader import KoikatuCharaData

scarlet = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet)

print("=== Blocks (list of tuples) ===")
print(f"len: {len(chara.blocks)}")
for i, blk in enumerate(chara.blocks):
    print(f"[{i}] {blk!r}")
print()

print("=== chara.data keys ===")
print(list(chara.data.keys()) if hasattr(chara, 'data') else 'no data attr')
print()

# Parameter
print("=== Parameter block ===")
try:
    param = chara.data['Parameter']
    print(f"type: {type(param)}")
    print(f"dir: {[x for x in dir(param) if not x.startswith('_')]}")
    if hasattr(param, 'data'):
        print(f"data type: {type(param.data)}")
        print(f"data: {param.data}")
except Exception as e:
    print(f"Error: {e}")
