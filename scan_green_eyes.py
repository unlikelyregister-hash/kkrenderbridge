import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

gdir = Path('C:/Games/Koikatsu/UserData/chara/female')

print('=== Scanning for eye IDs that render GREEN/HAZEL ===')
green_eyes = []
hazel_eyes = []

for f in sorted(gdir.glob('**/*.png')):
    if f.stat().st_size < 200000:
        continue
    try:
        card = KoikatuCharaData.load(str(f))
        cd = card.Custom.data
        for p in cd['face']['pupil']:
            bc = p['baseColor']
            if isinstance(bc, list) and len(bc) >= 3 and p['id'] != 0:
                r, g, b = bc[0], bc[1], bc[2]
                # Green-dominant: G > R and G > B
                if g > r + 0.05 and g > b + 0.05:
                    green_eyes.append((f.name, p['id'], [r,g,b]))
                # Hazel: G > B and G > R-0.1 (green-brown, G dominant but R significant)
                elif g > b + 0.03 and g > r - 0.15 and r > 0.35:
                    hazel_eyes.append((f.name, p['id'], [r,g,b]))
    except:
        pass

print(f'\n=== GREEN eyes ({len(green_eyes)}) ===')
for name, eid, col in sorted(green_eyes, key=lambda x: x[1])[:20]:
    print(f'  {name}: eye id={eid} base=[{col[0]:.3f},{col[1]:.3f},{col[2]:.3f}]')

print(f'\n=== HAZEL eyes ({len(hazel_eyes)}) ===')
for name, eid, col in sorted(hazel_eyes, key=lambda x: x[0])[:20]:
    print(f'  {name}: eye id={eid} base=[{col[0]:.3f},{col[1]:.3f},{col[2]:.3f}]')

# Also find unique eye IDs with their most common colors
print(f'\n=== Eye ID → most common color (for IDs appearing 5+ times) ===')
from collections import Counter, defaultdict
id_colors = defaultdict(list)
for f in sorted(gdir.glob('**/*.png')):
    if f.stat().st_size < 200000:
        continue
    try:
        card = KoikatuCharaData.load(str(f))
        cd = card.Custom.data
        for p in cd['face']['pupil']:
            bc = p['baseColor']
            if isinstance(bc, list) and len(bc) >= 3 and p['id'] != 0:
                id_colors[p['id']].append((f.name, bc))
    except:
        pass

print(f'\nUnique eye IDs found: {sorted(id_colors.keys())}')
print()
for eid in sorted(id_colors.keys()):
    entries = id_colors[eid]
    if len(entries) < 3:
        continue
    avg_r = sum(e[1][0] for e in entries) / len(entries)
    avg_g = sum(e[1][1] for e in entries) / len(entries)
    avg_b = sum(e[1][2] for e in entries) / len(entries)
    sample = entries[0][0]
    dominant = 'GREEN' if avg_g > avg_r + 0.05 and avg_g > avg_b + 0.05 else \
               'HAZEL' if avg_g > avg_b + 0.02 and avg_g > avg_r - 0.12 else \
               'BROWN' if avg_r > avg_g and avg_r > avg_b else \
               'BLUE' if avg_b > avg_r and avg_b > avg_g else 'MIXED'
    print(f'  id={eid:5d}: avg=[{avg_r:.3f},{avg_g:.3f},{avg_b:.3f}] n={len(entries):3d} {dominant:6s} e.g. {sample}')
