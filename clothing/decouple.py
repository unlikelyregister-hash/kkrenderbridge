#!/usr/bin/env python3
"""
Clothing decoupling — strip clothes to defaults or inject from another card.

The Coordinate block's slot[0].clothes.parts[] holds 9 clothing part dicts.
Each part has an ``id`` (asset ID) and ``colorInfo[]`` (4 color entries).

Two operations:
  1. strip_clothes(card)  → set all part IDs to 0 (no mesh), clear colors
  2. inject_clothes(target, source) → copy slot[0].clothes from source into target

These are used by card_builder.py to make clothing an optional component.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, List, Optional

# Directory where this module lives — scripts may import from here
HERE = Path(__file__).resolve().parent.parent


# ── helpers ─────────────────────────────────────────────────────────────────

def _slot0_clothes(card: Any) -> Dict[str, Any]:
    """Return the clothes dict from slot 0 of the card's Coordinate block."""
    coord = card.Coordinate.data  # list of 7 slot dicts
    return coord[0]["clothes"]


def _slot0_clothes_parts(card: Any) -> List[Dict[str, Any]]:
    """Return the parts list from slot 0 clothes."""
    return _slot0_clothes(card)["parts"]


# ── strip ───────────────────────────────────────────────────────────────────

def strip_clothes(card: Any) -> List[Dict[str, Any]]:
    """Remove all clothing from slot 0 by zeroing part IDs and colors.

    Keeps the parts list structure (9 entries) so the card remains valid.
    Each part gets id=0 and all colorInfo entries set to transparent white.

    Returns the modified parts list for inspection.
    """
    parts = _slot0_clothes_parts(card)
    for part in parts:
        part["id"] = 0
        for ci in part.get("colorInfo", []):
            ci["baseColor"] = [1.0, 1.0, 1.0, 0.0]  # transparent
            ci["pattern"] = 0
            ci["patternColor"] = [1.0, 1.0, 1.0, 0.0]
            ci["tiling"] = [0.0, 0.0]
    return parts


# ── inject ──────────────────────────────────────────────────────────────────

def inject_clothes(target_card: Any, source_card: Any) -> Dict[str, Any]:
    """Copy slot[0].clothes from source_card into target_card.

    Deep-copies the clothes dict (parts, colors, emblems, sleeves, hideOpt)
    so the target gets the source's exact outfit.

    Returns the injected clothes dict.
    """
    src_clothes = _slot0_clothes(source_card)
    tgt_clothes = _slot0_clothes(target_card)

    # Deep copy each part
    tgt_parts = tgt_clothes["parts"]
    src_parts = src_clothes["parts"]

    # Ensure the same number of parts (should always be 9)
    assert len(tgt_parts) == len(src_parts), (
        f"part count mismatch: target={len(tgt_parts)} source={len(src_parts)}"
    )

    for i, src_part in enumerate(src_parts):
        # Preserve the target's part structure but overwrite all fields
        tgt_part = tgt_parts[i]
        tgt_part.clear()
        tgt_part.update(copy.deepcopy(src_part))

    # Copy top-level clothes fields too
    tgt_clothes.clear()
    tgt_clothes.update(copy.deepcopy(src_clothes))

    return tgt_clothes


# ── default-nude ────────────────────────────────────────────────────────────

def set_defaults_nude(card: Any) -> List[Dict[str, Any]]:
    """Set all clothing parts to id=0 with nude/skin-tone colors.

    Unlike strip_clothes (which makes everything transparent), this gives
    the character a 'default undressed' look with skin-colored parts.

    Returns the modified parts list.
    """
    parts = _slot0_clothes_parts(card)
    NUDE = [0.95, 0.85, 0.78, 1.0]

    for part in parts:
        part["id"] = 0
        part["emblemeId"] = 0
        part["emblemeId2"] = 0
        part["hideOpt"] = [False, False]
        part["sleevesType"] = 0
        for ci in part.get("colorInfo", []):
            ci["baseColor"] = list(NUDE)
            ci["pattern"] = 0
            ci["patternColor"] = list(NUDE)
            ci["tiling"] = [0.0, 0.0]

    return parts


# ── standalone test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from kkloader import KoikatuCharaData

    SRC_SARAH = Path(
        r"C:\Games\Koikatsu\UserData\chara\female\IA2\Sarah\Cards"
        r"\Koikatu_F_20221020093900740_Sarah.png"
    )
    SRC_COMMUNITY_1 = Path(
        r"C:\Games\Koikatsu\UserData\chara\female\[Community]\KK_398582.png"
    )
    SRC_COMMUNITY_2 = Path(
        r"C:\Games\Koikatsu\UserData\chara\female\[Community]\KK_319725.png"
    )

    print("=" * 60)
    print("Clothing Decouple — Standalone Test")
    print("=" * 60)

    # Test 1: strip clothes from Sarah
    print("\n--- Test 1: strip_clothes(Sarah) ---")
    card = KoikatuCharaData.load(str(SRC_SARAH))
    parts_before = _slot0_clothes_parts(card)
    print(f"Before: {len(parts_before)} parts, ids={[p['id'] for p in parts_before]}")
    strip_clothes(card)
    parts_after = _slot0_clothes_parts(card)
    print(f"After:  {len(parts_after)} parts, ids={[p['id'] for p in parts_after]}")
    print(f"  colorInfo[0].baseColor = {parts_after[0]['colorInfo'][0]['baseColor']}")

    out_stripped = Path.cwd() / "test_stripped_clothes.kkpe"
    card.save(str(out_stripped))
    print(f"Saved: {out_stripped} ({out_stripped.stat().st_size} bytes)")

    # Test 2: set_defaults_nude
    print("\n--- Test 2: set_defaults_nude(Sarah) ---")
    card2 = KoikatuCharaData.load(str(SRC_SARAH))
    parts_nude = set_defaults_nude(card2)
    print(f"IDs: {[p['id'] for p in parts_nude]}")
    print(f"  colorInfo[0].baseColor = {parts_nude[0]['colorInfo'][0]['baseColor']}")

    out_nude = Path.cwd() / "test_nude.kkpe"
    card2.save(str(out_nude))
    print(f"Saved: {out_nude} ({out_nude.stat().st_size} bytes)")

    # Test 3: inject clothes from community card into stripped Sarah
    if SRC_COMMUNITY_1.exists():
        print("\n--- Test 3: inject_clothes(stripped_Sarah, KK_398582) ---")
        src_card = KoikatuCharaData.load(str(SRC_COMMUNITY_1))
        tgt_card = KoikatuCharaData.load(str(SRC_SARAH))
        strip_clothes(tgt_card)

        src_parts = _slot0_clothes_parts(src_card)
        print(f"Source parts: {len(src_parts)} ids={[p['id'] for p in src_parts]}")

        inject_clothes(tgt_card, src_card)
        tgt_parts = _slot0_clothes_parts(tgt_card)
        print(f"Target parts after inject: {len(tgt_parts)} ids={[p['id'] for p in tgt_parts]}")
        print(f"  part[0] colorInfo[0].baseColor = {tgt_parts[0]['colorInfo'][0]['baseColor']}")

        out_injected = Path.cwd() / "test_injected_clothes.kkpe"
        tgt_card.save(str(out_injected))
        print(f"Saved: {out_injected} ({out_injected.stat().st_size} bytes)")

    print("\n[DONE]")
