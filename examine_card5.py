import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

card5_path = Path(r'C:\Games\Koikatsu\UserData\chara\female\[Community]\The Mighty Ape\extra girls\Koikatu_F_20190414221041439.png')
card = KoikatuCharaData.load(str(card5_path))

print('=== Card5 blocks ===')
print(f'blockdata: {card.blockdata}')
print()

print('=== Parameter ===')
pd = card.Parameter.data
for k, v in sorted(pd.items()):
    print(f'  {k}: {repr(v)[:100]}')
print()

print('=== Coordinate ===')
coord = card.Coordinate.data
print(f'Type: {type(coord).__name__}')
if isinstance(coord, list):
    for i, slot in enumerate(coord):
        print(f'Slot {i}: {list(slot.keys())}')
        c = slot.get('clothes', {})
        parts = c.get('parts', [])
        print(f'  clothes: {len(parts)} parts')
        for j, p in enumerate(parts[:3]):
            print(f'    [{j}] id={p["id"]} emblemeId={p.get("emblemeId",0)}')
        print(f'  subPartsId: {c.get("subPartsId")}')
        a = slot.get('accessory', {})
        acc = a.get('parts', [])
        print(f'  accessory: {len(acc)} parts')
        for j, ap in enumerate(acc[:5]):
            print(f'    [{j}] type={ap["type"]} id={ap["id"]}')
        m = slot.get('makeup', {})
        print(f'  makeup: es={m.get("eyeshadowId")} ch={m.get("cheekId")} li={m.get("lipId")}')
        print()
else:
    print(f'Not a list')

print('=== Custom ===')
custom = card.Custom.data
print(f'face pupil[0]: id={custom["face"]["pupil"][0]["id"]} baseColor={custom["face"]["pupil"][0]["baseColor"]}')
print(f'face skinId={custom["face"]["skinId"]} headId={custom["face"]["headId"]}')
print(f'body skinId={custom["body"]["skinId"]} skinMainColor={custom["body"]["skinMainColor"]} skinSubColor={custom["body"]["skinSubColor"]}')
print(f'hair kind={custom["hair"]["kind"]}')
for i, p in enumerate(custom['hair']['parts'][:4]):
    print(f'  part[{i}]: id={p["id"]} baseColor={p["baseColor"]}')
