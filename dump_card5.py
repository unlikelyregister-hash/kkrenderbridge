import sys, json
sys.path.insert(0, '.')
from kkloader import KoikatuCharaData
from pathlib import Path

src = Path('C:/Games/Koikatsu/UserData/chara/female/[Community]/The Mighty Ape/extra girls/Koikatu_F_20190414221041439.png')
c = KoikatuCharaData.load(str(src))

bd = c.blockdata
print('blockdata keys:', list(bd.keys()))
print()
print('=== Custom block ===')
custom = bd.get('Custom')
if custom is not None:
    print(json.dumps(custom, indent=2, ensure_ascii=False)[:6000])
