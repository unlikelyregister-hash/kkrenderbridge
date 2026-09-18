#!/usr/bin/env python3
"""Fix eye color using BR-Chan's known hazel values: base=[0.580,0.537,0.420].
BR-Chan cards use eye id=6 with these values and render as hazel (green-brown),
not orange. Our previous values were too red-dominant.
Also try a green-dominant hazel: [0.42,0.55,0.22].
"""

import sys
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

SRC = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')
OUT = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')

c = KoikatuCharaData.load(str(SRC))
face = c.Custom.data['face']

# BR-Chan hazel: [0.580, 0.537, 0.420] — warm but balanced green-brown
# This should render as actual hazel, not orange
for eye in face['pupil']:
    eye['baseColor'] = [0.580, 0.537, 0.420, 1.0]
    eye['subColor'] = [0.450, 0.400, 0.280, 1.0]

print(f'BR-Chan hazel: base=[{eye["baseColor"][0]:.3f},{eye["baseColor"][1]:.3f},{eye["baseColor"][2]:.3f}]')
print(f'                sub=[{eye["subColor"][0]:.3f},{eye["subColor"][1]:.3f},{eye["subColor"][2]:.3f}]')

c.save(str(OUT))
print(f'Saved: {OUT.name} ({OUT.stat().st_size} bytes)')

# Verify
c2 = KoikatuCharaData.load(str(OUT))
for e in c2.Custom.data['face']['pupil']:
    if e['id'] != 0:
        print(f'Verify: id={e["id"]} base=[{e["baseColor"][0]:.3f},{e["baseColor"][1]:.3f},{e["baseColor"][2]:.3f}]')
print('Done!')
