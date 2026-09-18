import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData
from pathlib import Path
import json

base1_path = 'C:/Games/Koikatsu/UserData/chara/female/kkRenderBridge/base_1.png'
card = KoikatuCharaData.load(str(base1_path))

print('=== base_1.png ===')
print(f'Size: {Path(base1_path).stat().st_size} bytes')
print()
print('=== Parameter.data ===')
pd = card.Parameter.data
for k, v in pd.items():
    print(f'  {k}: {repr(v)[:120]}')
print()
print('=== Custom.face ===')
print(json.dumps(card.Custom.data['face'], indent=2, ensure_ascii=False))
print()
print('=== Custom.body ===')
print(json.dumps(card.Custom.data['body'], indent=2, ensure_ascii=False))
print()
print('=== Custom.hair ===')
print(json.dumps(card.Custom.data['hair'], indent=2, ensure_ascii=False))
