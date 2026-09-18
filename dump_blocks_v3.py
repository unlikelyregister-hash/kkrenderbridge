#!/usr/bin/env python3
"""Dump all block names + ids from Scarlet Chika card, and the Parameter JSON."""

import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")

from pathlib import Path
from kkloader import KoikatuCharaData

scarlet = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet)

print("=== Blocks (list) ===")
for blk in chara.blocks:
    print(f"{blk}")
    print(f"  name: {getattr(blk, 'name', 'N/A')}")
    print(f"  id: {getattr(blk, 'id', 'N/A')}")
    print(f"  data first 32 bytes: {getattr(blk, 'data', b'')[:32].hex() if getattr(blk, 'data', None) else 'N/A'}")
print()

print("=== dir(chara) ===")
print([x for x in dir(chara) if not x.startswith('_')])
print()

print("=== chara.blocks list content ===")
print(f"len: {len(chara.blocks)}")
for i, blk in enumerate(chara.blocks):
    print(f"[{i}] {blk!r}")
    # Try to see if it's a namedtuple
    print(f"  _fields: {getattr(blk, '_fields', 'N/A')}")
    print(f"  _asdict: {getattr(blk, '_asdict', lambda: {})() if hasattr(blk, '_asdict') else 'N/A'}")
print()

print("=== chara.data keys ===")
print(list(chara.data.keys()) if hasattr(chara, 'data') else 'no data attr')
