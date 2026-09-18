#!/usr/bin/env python3
"""Dump all block names + ids from Scarlet Chika card, and the Parameter JSON."""

import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")

from kkloader import KoikatuCharaData

scarlet = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet)

print("=== Blocks (list) ===")
for blk in chara.blocks:
    print(f"{blk}")
print()

print("=== dir(chara.blocks[0]) ===")
if chara.blocks:
    b0 = chara.blocks[0]
    print([x for x in dir(b0) if not x.startswith('_')])
print()

print("=== Block attributes for all blocks ===")
for blk in chara.blocks:
    print(f"--- {blk} ---")
    print(f"  name attr: {getattr(blk, 'name', 'N/A')}")
    print(f"  id attr: {getattr(blk, 'id', 'N/A')}")
    print(f"  data attr: {getattr(blk, 'data', 'N/A')}")
    print(f"  has block attr: {hasattr(blk, 'block')}")
    if hasattr(blk, 'block'):
        print(f"  block attr: {blk.block}")
    print(f"  has raw attr: {hasattr(blk, 'raw')}")
    if hasattr(blk, 'raw'):
        print(f"  raw attr: {blk.raw}")
    print()

print("=== Parameter block ===")
try:
    param_block = chara.data['Parameter']
    print(f"param_block type: {type(param_block)}")
    print(f"dir: {[x for x in dir(param_block) if not x.startswith('_')]}")
    if hasattr(param_block, 'data'):
        print(f"data keys: {list(param_block.data.keys()) if isinstance(param_block.data, dict) else type(param_block.data)}")
except Exception as e:
    print(f"Error: {e}")
