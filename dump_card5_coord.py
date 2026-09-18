import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

card5_path = Path('C:/Games/Koikatsu/UserData/chara/female/Koikatu_F_20190414221041439_The Cardboard Koi!.png')
c5 = KoikatuCharaData.load(str(card5_path))
print('=== Card5 Coordinate ===')
print(json.dumps(c5.coordinate_json(), indent=2, ensure_ascii=False)[:8000])
