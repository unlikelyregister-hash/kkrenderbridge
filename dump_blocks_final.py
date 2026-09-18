#!/usr/bin/env python3
import os, sys, json, pathlib
sys.path.insert(0, "C:/Users/Administrator/kk-workspace")
from kkloader import KoikatuCharaData

src = "C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20260221024507269_Scarlet Chika.png"
out = pathlib.Path("C:/Users/Administrator/kk-workspace/blocks")
out.mkdir(parents=True, exist_ok=True)

c = KoikatuCharaData.load(src)

(out / "header.bin").write_bytes(c.header)
(out / "face_image.png").write_bytes(c.face_image)
(out / "blockdata.txt").write_text("\n".join(c.blockdata))

for name in c.blockdata:
    blk = getattr(c, name)   # Coordinate / Parameter / Custom / Status / KKEx
    try:
        # blk is a dict-like object; serialize it to JSON bytes
        payload = json.dumps(blk if isinstance(blk, dict) else blk.data, indent=2, ensure_ascii=False).encode("utf-8")
        (out / f"block_{name}.json").write_bytes(payload)
        keys = payload.decode("utf-8")
        print(f"[json] {name}: {len(payload)} bytes")
    except Exception as e:
        raw = getattr(blk, "data", blk)
        try:
            b = bytes(raw)
            (out / f"block_{name}.bin").write_bytes(b)
            print(f"[raw] {name}: {len(b)} bytes ({b[:16].hex()})")
        except Exception as e2:
            print(f"[fail] {name}: {type(raw)} {e2}")

print("\nDONE")
