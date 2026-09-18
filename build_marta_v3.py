#!/usr/bin/env python3
"""Build Marta Lorente Inspired .kkpe — v3: use actual block names from MODULES."""
import os, struct
from pathlib import Path

from kkloader import KoikatuCharaData

WORKSPACE = Path(r"C:\Users\Administrator\kk-workspace")
GAME = Path(r"C:\Games\Koikatsu")
OUTPUT = WORKSPACE / "MartaLorente_Inspired.kkpe"

scarlet_path = GAME / "UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
print(f"Loading base: {scarlet_path.name}")
print(f"File size: {scarlet_path.stat().st_size:,} bytes")
base = KoikatuCharaData.load(str(scarlet_path))

print(f"\nMODULES: {base.__class__.MODULES}")
print(f"\nAvailable blocks:")
for name in base.__class__.MODULES:
    try:
        block = base[name]
        d = block.data if hasattr(block, 'data') else None
        print(f"  {name}: {type(block).__name__}" +
              (f"  data_keys={list(d.keys())[:15]}" if d else "  (no data)"))
    except Exception as e:
        print(f"  {name}: ERROR: {e}")

# Get Parameter
param = base["Parameter"]
pdata = param.data if hasattr(param, 'data') else dict(param)
print(f"\n=== Setting metadata ===")
for k, v in [
    ("lastname", "Lorente"),
    ("firstname", "Marta"),
    ("nickname", "Marta"),
    ("birthMonth", 8),
    ("birthDay", 5),
    ("bloodType", 0),   # O = 0?
    ("personality", 12),
    ("diligence", 5),
    ("kindness", 5),
    ("aggressive", 0),
]:
    try:
        pdata[k] = v
        print(f"  {k} = {v} OK")
    except Exception as e:
        print(f"  {k} FAILED: {e}")

# Check what block holds custom face/body/hair data
print(f"\n=== Check Custom block ===")
try:
    custom = base["Custom"]
    cdata = custom.data if hasattr(custom, 'data') else {}
    print(f"  Custom type: {type(custom).__name__}")
    print(f"  Custom data: {cdata}")
except Exception as e:
    print(f"  Custom ERROR: {e}")

print(f"\n=== Saving ===")
base.save(str(OUTPUT))
sz = OUTPUT.stat().st_size
print(f"  Saved: {sz:,} bytes ({sz/1024:.1f} KB)")
print(f"  >300KB: {'OK' if sz > 300000 else 'TOO SMALL'}")

print(f"\n=== Verifying ===")
v = KoikatuCharaData.load(str(OUTPUT))
vp = v["Parameter"]
vpd = vp.data if hasattr(vp, 'data') else {}
print(f"  name: {vpd.get('lastname', '?')} {vpd.get('firstname', '?')}")
print(f"  nick: {vpd.get('nickname', '?')}")
print(f"  bd: {vpd.get('birthMonth', '?')}/{vpd.get('birthDay', '?')}")
print(f"  bt: {vpd.get('bloodType', '?')}")
print(f"  per: {vpd.get('personality', '?')}")
