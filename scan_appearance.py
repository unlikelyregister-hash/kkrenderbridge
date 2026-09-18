import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

# Check what hair IDs are used by actual blonde-haired cards
# and what eye IDs are used by hazel-eyed cards
import os

gdir = Path('C:/Games/Koikatsu/UserData/chara/female')

blonde_cards = []
hazel_cards = []
tanned_cards = []

for f in sorted(gdir.glob('**/*.png')):
    if f.stat().st_size < 200000:
        continue  # skip showcase PNGs
    try:
        card = KoikatuCharaData.load(str(f))
        cd = card.Custom.data
        
        # Hair
        hair_parts = cd['hair']['parts']
        for hp in hair_parts:
            if hp['id'] != 0:
                c = hp['baseColor']
                if isinstance(c, list) and len(c) >= 3:
                    # R > G > B and relatively bright = likely blonde
                    if c[0] > 0.7 and c[1] > 0.5 and c[2] < c[1] and c[2] < 0.7:
                        blonde_cards.append((f.name, hp['id'], cd['hair'].get('kind', '?'), c))
                break
        
        # Eyes
        for p in cd['face']['pupil']:
            bc = p['baseColor']
            if isinstance(bc, list) and len(bc) >= 3:
                # Hazel: green-brown mix
                if bc[1] > bc[2] and bc[0] > bc[2] and bc[1] > 0.3 and bc[1] < 0.7 and bc[0] > 0.3 and bc[0] < 0.65:
                    hazel_cards.append((f.name, p['id'], bc))
                # Tanned skin check  
                sc = cd['body']['skinMainColor']
                if isinstance(sc, list) and len(sc) >= 3:
                    if sc[0] > 0.85 and sc[1] < 0.85 and sc[2] < 0.65:
                        tanned_cards.append((f.name, sc))
                break
    except Exception as e:
        pass

print(f'=== Blonde hair cards ({len(blonde_cards)}) ===')
for name, hid, hkind, col in sorted(blonde_cards, key=lambda x: x[0])[:15]:
    print(f'  {name}: hair part id={hid}, kind={hkind}, baseColor={col}')

print(f'\n=== Hazel eye cards ({len(hazel_cards)}) ===')
for name, pid, col in sorted(hazel_cards, key=lambda x: x[0])[:15]:
    print(f'  {name}: pupil id={pid}, baseColor={col}')

print(f'\n=== Tanned skin cards ({len(tanned_cards)}) ===')
for name, sc in sorted(tanned_cards, key=lambda x: x[0])[:15]:
    print(f'  {name}: skinMainColor={sc}')
