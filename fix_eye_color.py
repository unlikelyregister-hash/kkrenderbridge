#!/usr/bin/env python3
"""Fix eye color on MartaLorente.png from orange/amber to proper hazel.

Current values:
  eye id=6, baseColor=[0.54, 0.46, 0.25] — too orange-red (R high, G medium, B low)
  subColor=[0.42, 0.32, 0.15]

Target hazel (from Card5 reference + typical hazel):
  Hazel = green-brown mix. Green channel dominant, brown/orange tint in center.
  baseColor should be: R=0.54, G=0.52, B=0.28 (more green, less red dominance)
  subColor: R=0.42, G=0.38, B=0.22 (darker ring with green tint)
  
  Actually let me pick a proper hazel:
  - Outer: greenish-brown: R=0.52, G=0.50, B=0.30 (balanced green-brown)
  - Inner ring: warmer brown: R=0.48, G=0.38, B=0.20
  
  Or try a classic hazel from well-known KK cards:
  Card5 (Botan): base=[0.536, 0.453, 0.246] — this IS hazel but looked orange
  Let me try: base=[0.50, 0.52, 0.30] — more green-dominant hazel
  subColor=[0.38, 0.36, 0.18] — darker greenish ring
"""

import sys
from pathlib import Path

sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from kkloader import KoikatuCharaData

SRC = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')
OUT = Path(r'C:\Games\Koikatsu\UserData\chara\female\kkRenderBridge\MartaLorente.png')

print(f'Loading: {SRC}')
c = KoikatuCharaData.load(str(SRC))

face = c.Custom.data['face']

# Show current eye values
for i, eye in enumerate(face['pupil']):
    bc = eye['baseColor']
    sc = eye['subColor']
    print(f'Eye {i}: id={eye["id"]} base=[{bc[0]:.3f},{bc[1]:.3f},{bc[2]:.3f}] sub=[{sc[0]:.3f},{sc[1]:.3f},{sc[2]:.3f}]')

# Fix: proper hazel — green-dominant with brown ring
# baseColor: green > red > blue (green-brown mix, hazel)
# The previous [0.54,0.46,0.25] gave orange. Let's try greener:
for eye in face['pupil']:
    eye['baseColor'] = [0.52, 0.52, 0.30, 1.0]   # Green-brown hazel (balanced)
    eye['subColor'] = [0.40, 0.40, 0.22, 1.0]    # Slightly darker ring, green tint

print(f'\nNew eye values:')
for eye in face['pupil']:
    bc = eye['baseColor']
    sc = eye['subColor']
    print(f'  id={eye["id"]} base=[{bc[0]:.3f},{bc[1]:.3f},{bc[2]:.3f}] sub=[{sc[0]:.3f},{sc[1]:.3f},{sc[2]:.3f}]')

# Save
c.save(str(OUT))
sz = OUT.stat().st_size
print(f'\nSaved: {OUT.name} ({sz} bytes, {sz/1024:.1f} KB)')

# Verify roundtrip
c2 = KoikatuCharaData.load(str(OUT))
for eye in c2.Custom.data['face']['pupil']:
    if eye['id'] != 0:
        print(f'Verify eye id={eye["id"]} base=[{eye["baseColor"][0]:.3f},{eye["baseColor"][1]:.3f},{eye["baseColor"][2]:.3f}]')
print('Done!')
