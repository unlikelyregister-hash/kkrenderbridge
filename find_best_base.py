import sys
sys.path.insert(0, 'C:/Users/Administrator/kk-workspace')
from pathlib import Path
from kkloader import KoikatuCharaData
import json

gdir = Path('C:/Games/Koikatsu/UserData/chara/female')

print('=== Cards with blonde hair + hazel eyes + tanned skin ===')
results = []

for f in sorted(gdir.glob('**/*.png')):
    if f.stat().st_size < 200000:
        continue
    try:
        card = KoikatuCharaData.load(str(f))
        cd = card.Custom.data
        
        # Hair blonde?
        hair_blonde = False
        hair_id = None
        hair_kind = cd['hair'].get('kind', -1)
        for hp in cd['hair']['parts']:
            if hp['id'] != 0:
                c = hp['baseColor']
                if isinstance(c, list) and len(c) >= 3:
                    if c[0] > 0.75 and c[1] > 0.55 and c[2] < c[1] and c[2] < 0.7:
                        hair_blonde = True
                        hair_id = hp['id']
                break
        
        if not hair_blonde:
            continue
        
        # Eyes hazel?
        eye_hazel = False
        eye_id = None
        for p in cd['face']['pupil']:
            bc = p['baseColor']
            if isinstance(bc, list) and len(bc) >= 3:
                if bc[1] > bc[2] and bc[0] > bc[2] and bc[1] > 0.3 and bc[1] < 0.7:
                    eye_hazel = True
                    eye_id = p['id']
                break
        
        if not eye_hazel:
            continue
        
        # Skin tanned?
        sc = cd['body']['skinMainColor']
        skin_tanned = False
        if isinstance(sc, list) and len(sc) >= 3:
            if sc[0] > 0.80 and sc[1] < 0.80 and sc[2] < 0.65:
                skin_tanned = True
        
        if not skin_tanned:
            continue
        
        pd = card.Parameter.data
        results.append((f.name, hair_id, hair_kind, eye_id, sc, pd.get('firstname', '')))
        
    except Exception as e:
        pass

if results:
    print(f'Found {len(results)} cards:')
    for name, hid, hkind, eid, sc, fn in sorted(results, key=lambda x: x[0]):
        print(f'  {name}: hair_id={hid} kind={hkind}, eye_id={eid}, skin={sc}, name="{fn}"')
else:
    print('None found with all 3 traits. Showing cards with 2/3...')
    
    # Show cards with 2 of 3
    for f in sorted(gdir.glob('**/*.png')):
        if f.stat().st_size < 200000:
            continue
        try:
            card = KoikatuCharaData.load(str(f))
            cd = card.Custom.data
            
            hair_blonde = False
            hair_id = None
            hair_kind = cd['hair'].get('kind', -1)
            for hp in cd['hair']['parts']:
                if hp['id'] != 0:
                    c = hp['baseColor']
                    if isinstance(c, list) and len(c) >= 3:
                        if c[0] > 0.75 and c[1] > 0.55 and c[2] < c[1] and c[2] < 0.7:
                            hair_blonde = True
                            hair_id = hp['id']
                    break
            
            eye_hazel = False
            eye_id = None
            for p in cd['face']['pupil']:
                bc = p['baseColor']
                if isinstance(bc, list) and len(bc) >= 3:
                    if bc[1] > bc[2] and bc[0] > bc[2] and bc[1] > 0.3 and bc[1] < 0.7:
                        eye_hazel = True
                        eye_id = p['id']
                    break
            
            sc = cd['body']['skinMainColor']
            skin_tanned = False
            if isinstance(sc, list) and len(sc) >= 3:
                if sc[0] > 0.80 and sc[1] < 0.80 and sc[2] < 0.65:
                    skin_tanned = True
            
            score = sum([hair_blonde, eye_hazel, skin_tanned])
            if score >= 2:
                pd = card.Parameter.data
                print(f'  {f.name}: hair={"B" if hair_blonde else "-"} (id={hair_id}, k={hair_kind}) eye={"H" if eye_hazel else "-"} (id={eye_id}) skin={"T" if skin_tanned else "-"} (skin={sc}) name="{pd.get("firstname","")}"')
        except:
            pass
