#!/usr/bin/env python3
"""Parse Koikatsu asset catalogs to find item-to-ID mappings for each category.
Checks abdata/h/list/00_00.unity3d against checkitem.xml to recover the mapping."""
import os, re, xml.etree.ElementTree as ET

GAME = "C:/Games/Koikatsu"

# --- 1. Item blacklist/favorites from save data ---
blacklist = set()
favorites = set()
for xml_path in [f"{GAME}/UserData/save/itemblacklist.xml",
                 f"{GAME}/UserData/save/itemfavorites.xml"]:
    if os.path.exists(xml_path):
        tree = ET.parse(xml_path)
        for item in tree.getroot().findall("item"):
            blacklist.add(item.get("id")) if "blacklist" in xml_path else favorites.add(item.get("id"))

# --- 2. Checkitem.xml: item IDs per mod+category ---
cat_items = {}  # (mod_guid, category) -> [item_id, ...]
if os.path.exists(f"{GAME}/UserData/save/checkitem.dat"):
    # Binary format - skip for now
    pass
elif os.path.exists(f"{GAME}/UserData/save/checkitem.xml"):
    tree = ET.parse(f"{GAME}/UserData/save/checkitem.xml")
    for mod in tree.getroot():
        guid = mod.get("guid", "")
        for cat in mod:
            cat_num = int(cat.get("number", 0))
            items = [int(i.get("id")) for i in cat.findall("item")]
            cat_items[(guid, cat_num)] = sorted(items)

print(f"=== Parsed checkitem.xml: {len(cat_items)} mod+category entries ===")
for (guid, cat), items in sorted(cat_items.items()):
    if cat in [100, 105, 106, 109, 112, 122, 124, 126, 128, 129, 210, 211]:
        print(f"  Category {cat} ({guid[:30]}): {len(items)} items, first={items[0] if items else '?'}" +
              (f", last={items[-1]}" if len(items) > 1 else ""))

print()

# --- 3. Parse the h/list/00_00.unity3d catalog ---
catalog = f"{GAME}/abdata/h/list/00_00.unity3d"
print(f"=== Catalog: {catalog} ({os.path.getsize(catalog)} bytes) ===")

with open(catalog, "rb") as f:
    data = f.read()

# Find all mod GUID-like patterns: [something]text
mod_pattern = re.compile(rb'\[[^\]]{1,20}\][A-Za-z0-9_]{2,40}')
mod_matches = list(mod_pattern.finditer(data))
print(f"Found {len(mod_matches)} potential mod entries")

# Build (mod_text, near_item_ids) mapping
mod_to_items = {}
for mm in mod_matches:
    mod_text = mm.group().decode("utf-8", errors="replace")
    mod_start = mm.start()
    # Look for item IDs within 100 bytes after the mod
    nearby_ids = set()
    for m in re.finditer(rb"(?<![0-9])([0-9]{5,6})(?![0-9])", data[mm.start():mm.start()+200]):
        val = int(m.group(1))
        if 100 < val < 9999999:
            nearby_ids.add(val)
    if nearby_ids:
        mod_to_items[mod_text] = nearby_ids

print(f"Mod entries with nearby IDs: {len(mod_to_items)}")

# Match against checkitem.xml categories
# For each category in checkitem.xml, find which mod entries contain those items
cat_mod_map = {}  # category -> list of (mod_text, matching_items)
for (guid, cat_num), expected_items in cat_items.items():
    if cat_num not in [100, 105, 106, 109, 112, 122, 124, 126, 128, 129, 210, 211]:
        continue
    for mod_text, mod_items in mod_to_items.items():
        overlap = expected_items & mod_items
        if overlap:
            if cat_num not in cat_mod_map:
                cat_mod_map[cat_num] = []
            cat_mod_map[cat_num].append((mod_text, sorted(overlap)))

print(f"\n=== Category → Mod mapping ===")
for cat_num in sorted(cat_mod_map):
    entries = cat_mod_map[cat_num]
    print(f"Category {cat_num}: {len(entries)} mod matches")
    for mod_text, items in entries[:5]:
        print(f"  {mod_text[:50]:50s} overlap: {items[:10]}")

print()

# --- 4. Find which mod owns which category for tops, bottoms, etc ---
# From checkitem.xml:
# Category 210 = tops (Clothing - Top)
# Category 211 = bottoms (Clothing - Bottom)
# Category 100 = hair accessories (Category 100 - Hair Access)
# Category 105 = eye accessories
# Category 106 = face accessories
# etc.

# Try to find the "vanilla" mods (the ones shipped with the game)
# Look for mod GUIDs that appear in multiple categories
vanilla_mods = set()
for (guid, cat_num), items in cat_items.items():
    if cat_num in [100, 105, 106, 109, 112, 210, 211]:
        vanilla_mods.add(guid)

print(f"=== Vanilla mods (appearing in vanilla categories) ===")
for guid in sorted(vanilla_mods):
    cats = [c for (g, c), _ in cat_items.items() if g == guid]
    total_items = sum(len(items) for (_, _), items in cat_items.items() if _ == guid)
    print(f"  {guid[:50]:50s} categories: {cats} total items: {total_items}")

print()

# --- 5. Look for the actual item names in the catalog ---
# Items in h/list catalog have names encoded as part of the data
# Search for text that might be item names near category 210 (tops)
print("=== Looking for item names near category 210 (tops) ===")
cat210_str = b"210"
for cm in re.finditer(cat210_str, data):
    pos = cm.start()
    window = data[max(0,pos-100):pos+300]
    # Find readable strings in this window
    strs = []
    for m in re.finditer(rb'[A-Za-z_][A-Za-z0-9_]{2,30}', window):
        s = m.group().decode("ascii", errors="ignore")
        strs.append((m.start() + max(0,pos-100), s))
    if strs:
        print(f"  Offset {pos}: strings nearby: {[s for _,s in strs[:10]]}")
