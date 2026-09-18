#!/usr/bin/env python3
"""Extract Card5 (Koikatu_F_20190414221041439) full visual blocks as JSON for reference."""
import sys, json
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

card5_path = Path('C:/Games/Koikatsu/UserData/chara/female/[Community]/The Mighty Ape/extra girls/Koikatu_F_20190414221041439.png')
c5 = KoikatuCharaData.load(str(card5_path))

for key in sorted(c5.blockdata.keys()):
    block = c5.blockdata[key]
    print(f'=== Block: {key} ({type(block).__name__}) ===')
    try:
        print(json.dumps(block, indent=2, ensure_ascii=False)[:6000])
    except TypeError:
        print(repr(block)[:6000])
    print()