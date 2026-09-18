import os, re

path = 'C:/Games/Koikatsu/abdata/h/list/00_00.unity3d'
with open(path, 'rb') as f:
    data = f.read()

strings = []
i = 0
while i < len(data):
    if 32 <= data[i] < 127:
        j = i
        while j < len(data) and 32 <= data[j] < 127 and j - i < 100:
            j += 1
        s = data[i:j].decode('ascii', errors='ignore')
        if len(s) >= 3:
            strings.append(s)
        i = j
    else:
        i += 1

# Look for item name patterns
patterns = []
for s in strings:
    if re.match(r'^[A-Z_]{2,}[0-9]{2,}$', s) or re.match(r'^Co_[A-Z]+', s) or re.match(r'^[A-Z]+_[0-9]+', s):
        patterns.append(s)

print('Potential item name patterns:')
for p in sorted(set(patterns))[:80]:
    print(f'  {p}')

# Also look for keyword matches
print('\nKeyword matches:')
for s in strings:
    sl = s.lower()
    if any(k in sl for k in ['hair', 'eye', 'skin', 'cloth', 'top', 'bot', 'bra', 'pants', 'shoes', 'sock', 'glove', 'jacket', 'shirt']):
        if len(s) > 3:
            print(f'  {s}')
