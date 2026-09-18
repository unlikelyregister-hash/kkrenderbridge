import os, re
from collections import Counter

path = 'C:/Games/Koikatsu/abdata/h/list/00_00.unity3d'
size = os.path.getsize(path)
print(f'Size: {size} bytes ({size/1024/1024:.1f} MB)')

with open(path, 'rb') as f:
    data = f.read()

strings = []
for m in re.finditer(b'[A-Za-z_][A-Za-z0-9_]{2,30}', data):
    s = m.group().decode('ascii', errors='ignore')
    if len(s) >= 4 and not s.startswith('UnityEngine') and not s.startswith('Mono'):
        strings.append(s)

counts = Counter(strings)
print(f"\nFound {len(strings)} potential strings")
print("\nMost common strings (top 80):")
for s, c in counts.most_common(80):
    print(f"  '{s}' x{c}")
