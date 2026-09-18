#!/usr/bin/env python3
import os, sys
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

scarlet_path = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
chara = KoikatuCharaData.load(scarlet_path)

print("=== attributes ===")
print([x for x in dir(chara) if not x.startswith('_')])
print()

print("=== blockdata type:", type(chara.blockdata))
if isinstance(chara.blockdata, dict):
    for k, v in chara.blockdata.items():
        print(f"  {k}: type={type(v).__name__} id={getattr(v, 'id', '?')} name={getattr(v, 'name', '?')} data_len={len(v.data) if hasattr(v, 'data') else '?'}")
print()

print("=== face_image ===")
fi = chara.face_image
print(f"  type={type(fi)} len={len(fi) if hasattr(fi, '__len__') else '?'}")
if isinstance(fi, bytes):
    print(f"  first 32: {fi[:32].hex()}")
print()

print("=== header ===")
h = chara.header
print(f"  type={type(h)} dir={[x for x in dir(h) if not x.startswith('_')]}")
print(f"  {h}")
print()

print("=== modules (instance attr, not MODULES dict) ===")
mods = chara.modules
print(f"  type={type(mods)} dir={[x for x in dir(mods) if not x.startswith('_')]}")
if hasattr(mods, '__iter__'):
    print(f"  len={len(mods)}")
    for i, m in enumerate(mods):
        print(f"    [{i}] {m}")
print()

print("=== serialized_lstinfo_order ===")
so = chara.serialized_lstinfo_order
print(f"  type={type(so)} value={so!r}")
print()

print("=== version ===")
print(f"  {chara.version}")
