import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData

gdir = Path('C:/Games/Koikatsu/UserData/chara/female')

kind1_hairs = {}

for f in sorted(gdir.glob('**/*.png')):
    if f.stat().st_size < 200000:
        continue
    try:
        card = KoikatuCharaData.load(str(f))
        cd = card.Custom.data
        hair = cd['hair']
        if hair.get('kind') != 1:
            continue
        parts = hair['parts']
        for p in parts:
            if p['id'] != 0:
                c = p['baseColor']
                if isinstance(c, list) and len(c) >= 3:
                    key = p['id']
                    if key not in kind1_hairs:
                        kind1_hairs[key] = []
                    kind1_hairs[key].append((f.name, c))
                break
    except:
        pass

print(f'Hair part IDs for kind=1 ({len(kind1_hairs)} unique IDs)')
for hid in sorted(kind1_hairs.keys()):
    entries = kind1_hairs[hid]
    avg_r = sum(e[1][0] for e in entries) / len(entries)
    avg_g = sum(e[1][1] for e in entries) / len(entries)
    avg_b = sum(e[1][2] for e in entries) / len(entries)
    sample = entries[0][0]
    tag = 'BLONDE' if avg_r > 0.7 and avg_g > 0.5 and avg_b < avg_g else ''
    print(f'  id={hid:5d}: avg=[{avg_r:.3f},{avg_g:.3f},{avg_b:.3f}] n={len(entries)} {tag} e.g. {sample}')
