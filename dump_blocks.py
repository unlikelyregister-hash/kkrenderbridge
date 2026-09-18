#!/usr/bin/env python3
"""Dump required visual blocks from Scarlet Chika and rebuild Marta's .kkpe with byte-exact visuals."""
import os, struct, zlib, sys
from pathlib import Path

from kkloader import KoikatuCharaData

GAME = Path("C:/Games/Koikatsu")
scarlet = GAME / "UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
outdir = Path("C:/Users/Administrator/kk-workspace/blocks")
outdir.mkdir(parents=True, exist_ok=True)

print(f"Loading Scarlet Chika from: {scarlet}")
print(f"File size: {scarlet.stat().st_size} bytes")

try:
    chara = KoikatuCharaData.load(str(scarlet))
except Exception as e:
    print(f"ERROR loading card: {e}")
    sys.exit(1)

print(f"Header: {chara.header}")
print(f"Loaded {len(chara)} blocks:")
for blk in chara.blocks:
    print(f"  {blk.name} id={blk.id:04X} ({len(blk.data)} bytes)")
    if hasattr(blk, 'data') and blk.data:
        print(f"    First 32 bytes: {blk.data[:32].hex()}")

print("\n=== Dumping all blocks as raw .bin files ===")
for blk in chara.blocks:
    out = outdir / f"block_{blk.id:04X}_{blk.name}.bin"
    out.write_bytes(blk.data)
    print(f"  Wrote {out.name} ({len(blk.data)} bytes)")

print("\nDone.")
