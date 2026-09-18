import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

# Load base_2 (user's base) and Card5 (best blonde+hazel+tanned reference)
base_path = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\base_2.png')
card5_path = Path(r'C:\Games\Koikatsu\UserData\chara\female\[Community]\The Mighty Ape\extra girls\Koikatu_F_20190414221041439.png')

base = KoikatuCharaData.load(str(base_path))
card5 = KoikatuCharaData.load(str(card5_path))

print('=== base_2 hair ===')
print(f'  kind={base.Custom.data["hair"]["kind"]}')
for p in base.Custom.data['hair']['parts']:
    print(f'  part id={p["id"]} baseColor={p["baseColor"]}')

print()
print('=== Card5 hair (blonde reference) ===')
print(f'  kind={card5.Custom.data["hair"]["kind"]}')
for p in card5.Custom.data['hair']['parts']:
    if p['id'] != 0:
        print(f'  part id={p["id"]} baseColor={p["baseColor"]}')

print()
print('=== base_2 eyes ===')
for p in base.Custom.data['face']['pupil']:
    print(f'  pupil id={p["id"]} baseColor={p["baseColor"]}')

print()
print('=== Card5 eyes (hazel reference) ===')
for p in card5.Custom.data['face']['pupil']:
    if p['id'] != 0:
        print(f'  pupil id={p["id"]} baseColor={p["baseColor"]}')

print()
print('=== base_2 skin ===')
print(f'  skinMainColor={base.Custom.data["body"]["skinMainColor"]}')
print(f'  skinSubColor={base.Custom.data["body"]["skinSubColor"]}')

print()
print('=== Card5 skin (tanned reference) ===')
print(f'  skinMainColor={card5.Custom.data["body"]["skinMainColor"]}')
print(f'  skinSubColor={card5.Custom.data["body"]["skinSubColor"]}')

print()
print('=== Card5 Parameter ===')
for k,v in sorted(card5.Parameter.data.items()):
    print(f'  {k}: {repr(v)[:80]}')
