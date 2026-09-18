import os

game = "C:/Games/Koikatsu"

print("=== Searching for hair/eye/skin/clothes asset bundles ===")
count = 0
keywords = ['hair', 'head', 'face', 'eye', 'skin', 'type', 'cloth', 'costume', 'outfit', 'top', 'bottom', 'accessor', 'item', 'catalog', 'list', 'enum', 'palette']
for root, dirs, files in os.walk(game):
    for f in files:
        fl = f.lower()
        if any(x in fl for x in keywords):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            print(f"  {path} ({size} bytes)")
            count += 1
            if count >= 50:
                break
    if count >= 50:
        break

print(f"\nTotal found: {count}")
