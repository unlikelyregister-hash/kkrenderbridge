#!/usr/bin/env python3
"""Fix eye color: try green-dominant hazel that renders as hazel not orange.

The previous [0.52,0.52,0.30] rendered orange/amber.
Let me try more green-dominant values:
  Option A: [0.45, 0.55, 0.30] — green dominant hazel
  Option B: [0.50, 0.54, 0.25] — green-brown 
  Option C: from actual known hazel KK cards

Let me check what eye IDs exist and what colors they render as.
First, let me just try a greener hazel.
"""

import sys
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

SRC = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')
OUT = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')

c = KoikatuCharaData.load(str(SRC))
face = c.Custom.data['face']

# Try greener hazel — more green, less red
# baseColor: R=0.48, G=0.56, B=0.28 (green-dominant hazel)
# subColor: R=0.38, G=0.44, B=0.20 (darker greenish ring)
for eye in face['pupil']:
    eye['baseColor'] = [0.48, 0.56, 0.28, 1.0]
    eye['subColor'] = [0.38, 0.44, 0.20, 1.0]

print(f'New eye: base=[{eye["baseColor"][0]:.3f},{eye["baseColor"][1]:.3f},{eye["baseColor"][2]:.3f}]')
print(f'        sub=[{eye["subColor"][0]:.3f},{eye["subColor"][1]:.3f},{eye["subColor"][2]:.3f}]')

c.save(str(OUT))
print(f'Saved: {OUT.name} ({OUT.stat().st_size} bytes)')

# Verify
c2 = KoikatuCharaData.load(str(OUT))
for e in c2.Custom.data['face']['pupil']:
    if e['id'] != 0:
        print(f'Verify: id={e["id"]} base=[{e["baseColor"][0]:.3f},{e["baseColor"][1]:.3f},{e["baseColor"][2]:.3f}]')
print('Done!')
