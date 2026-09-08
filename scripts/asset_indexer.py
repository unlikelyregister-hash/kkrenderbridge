#!/usr/bin/env python3
"""
Asset indexer for Koikatsu character cards + hair/clothing library renders.

Scans character card directories, coordinate/library asset directories, loads
each .png with kkloader (when it's a character card), extracts metadata, and
writes a JSON index.  Non-character PNGs (coordinate sheets, etc.) are indexed
with file-only metadata when kkloader parsing fails.

Usage:
    python scripts/asset_indexer.py                  # index chars + assets
    python scripts/asset_indexer.py --render-thumbs  # also render thumbs (needs game)
    python scripts/asset_indexer.py --output my_index.json
    python scripts/asset_indexer.py --category chara   # chara cards only
    python scripts/asset_indexer.py --category asset    # library assets only

Output JSON index entries:
    Character cards:
      { "path", "product_no", "header", "version", "blockdata",
        "has_image", "face_image_len", "block_sizes", "source_dir",
        "category", "digest", "thumbnail"? }
    Library assets (parse failure):
      { "path", "size", "category", "digest", "source_dir", "parse_error" }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("asset_indexer")

# ---------------------------------------------------------------------------
# WD tagger support (optional — only used when --tag-with is given)
# ---------------------------------------------------------------------------
try:
    from wd_tagger import WDTagger
    _HAS_WD_TAGGER = True
except ImportError:
    _HAS_WD_TAGGER = False
    WDTagger = None  # type: ignore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GAME_DIR = Path(r"C:\Games\Koikatsu")

# Character card directories (kkloader-parseable .png with binary payload)
CHAR_DIRS = [
    GAME_DIR / "UserData" / "chara" / "female",
    GAME_DIR / "UserData" / "chara" / "male",
]

# Asset/library directories (hair, clothing, coordinates, backgrounds, scenes).
# These may or may not be parseable by kkloader — we index with file metadata
# when parsing fails.
ASSET_DIRS = [
    GAME_DIR / "UserData" / "coordinate",
    GAME_DIR / "UserData" / "bg",
    GAME_DIR / "UserData" / "Studio" / "scene",
    GAME_DIR / "UserData" / "Studio" / "screenshot",
]

# Known subdirectories inside char dirs that contain cards
CHAR_SUBS = [
    "",
    "[Community]",
    "IA2",
    "ModPack",
    "Big Sisterly",
    "Bookish",
    "Delinquent",
    "Emotionless",
    "Friendly",
    "Glamorous",
    "Gyaru",
    "Honest",
    "Humble",
    "Jinxed",
    "Kouhai",
    "Lazy",
    "Motherly",
    "Mysterious",
    "Ojousama",
    "Old-Fashioned",
    "Otaku",
    "Perfectionist",
    "Pure",
    "Quiet",
    "Reluctant",
    "Sadistic",
    "Sexy",
    "Simple",
    "Slangy",
    "Snobby",
    "Stubborn",
    "Timid",
    "Tomboy",
    "Trendy",
    "Typical Schoolgirl",
    "Wannabe",
    "Weirdo",
    "Wild",
    "Willful",
    "Yandere",
    "Returnee",
    "Delusional",
    "Gyaru 2",
    "Humble 2",
    "Motherly 2",
    "Pure 2",
    "Quiet 2",
    "Simple 2",
    "Wannabe 2",
    "Bookish",
    "Delinquent",
    "Emotionless",
    "Friendly",
    "Glamorous",
    "Gyaru",
    "Honest",
    "Humble",
    "Jinxed",
    "Kouhai",
    "Lazy",
    "Motherly",
    "Mysterious",
    "Ojousama",
    "Old-Fashioned",
    "Otaku",
    "Perfectionist",
    "Pure",
    "Quiet",
    "Reluctant",
    "Sadistic",
    "Sexy",
    "Simple",
    "Slangy",
    "Snobby",
    "Stubborn",
    "Timid",
    "Tomboy",
    "Trendy",
    "Typical Schoolgirl",
    "Wannabe",
    "Weirdo",
    "Wild",
    "Willful",
    "Yandere",
]

# Deduplicate dirs (CHAR_SUBS has duplicates from the above list being appended)
CHAR_SUBS = list(dict.fromkeys(CHAR_SUBS))

# Where to write thumbnail renders (via KkRenderBridge)
THUMB_DIR = Path(r"C:\Users\Administrator\kk-workspace\renders\thumbs")
REQUEST_DIR = GAME_DIR / "render_requests"  # plugin watches this

# ---------------------------------------------------------------------------
# kkloader
# ---------------------------------------------------------------------------
try:
    import kkloader
    _HAS_KLOADER = True
except ImportError:
    _HAS_KLOADER = False
    kkloader = None  # type: ignore[assignment]


def _win(path: Path) -> Path:
    """Normalize MSYS /c/ paths to real Windows paths."""
    s = str(path)
    if len(s) >= 2 and s[1] == ":":
        real_drive = s[0].upper()
        rest = s[3:].lstrip("/").replace("/", "\\")
    else:
        real_drive = s[1].upper() if s[0] == "\\" else s[0].upper()
        rest = s[2:].lstrip("/").replace("/", "\\")
    return Path(f"{real_drive}:\\{rest}")


def file_digest(path: Path) -> str:
    """SHA-256 digest of a file's first 64KB (fast dedup fingerprint)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_card(card_path: Path, thumb_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load a single card and extract metadata."""
    cp = _win(card_path)
    if not cp.exists():
        return {"path": str(card_path), "error": "file not found", "category": "chara"}

    if not _HAS_KLOADER:
        return {"path": str(card_path), "error": "kkloader not available", "category": "chara"}

    try:
        kd = kkloader.KoikatuCharaData.load(str(cp), contains_png=True)
    except Exception as e:
        return {"path": str(card_path), "error": f"load failed: {e}", "category": "chara"}

    # Compute block sizes from the in-memory objects
    block_sizes: Dict[str, int] = {}
    for name in kd.blockdata:
        obj = getattr(kd, name, None)
        if obj is not None:
            try:
                block_sizes[name] = len(bytes(obj))
            except Exception:
                block_sizes[name] = -1

    entry: Dict[str, Any] = {
        "path": str(cp),
        "category": "chara",
        "product_no": kd.product_no,
        "header": kd.header.decode("utf-8", errors="replace"),
        "version": kd.version.decode("utf-8", errors="replace"),
        "blockdata": kd.blockdata,
        "has_image": kd.image is not None,
        "face_image_len": len(kd.face_image) if kd.face_image else 0,
        "block_sizes": block_sizes,
        "source_dir": str(card_path.relative_to(card_path.anchor).parent),
        "category": "chara",
    }

    # Thumbnail render path (filled in by caller if --render-thumbs)
    if thumb_dir is not None:
        entry["thumbnail"] = str(thumb_dir / cp.name)

    return entry


def scan_char_dirs(
    char_dirs: List[Path],
    subs: List[str] = CHAR_SUBS,
    ext: str = ".png",
) -> List[Path]:
    """Walk char directories and yield every .png card found."""
    cards: List[Path] = []
    for base in char_dirs:
        if not base.exists():
            log.warning("char dir not found: %s", base)
            continue
        for sub in subs:
            subdir = base / sub if sub else base
            if not subdir.exists():
                continue
            for p in sorted(subdir.glob(f"*{ext}")):
                cards.append(p)
    return cards


def scan_asset_dirs(
    asset_dirs: List[Path],
    ext: str = ".png",
) -> List[Path]:
    """Walk asset directories and yield every .png found (coordinates, bg, scenes)."""
    files: List[Path] = []
    for base in asset_dirs:
        if not base.exists():
            log.warning("asset dir not found: %s", base)
            continue
        for p in sorted(base.rglob(f"*{ext}")):
            files.append(p)
    return files


def index_asset(asset_path: Path) -> Dict[str, Any]:
    """Index a library asset (.png that may or may not be a char card)."""
    ap = _win(asset_path)
    if not ap.exists():
        return {"path": str(asset_path), "error": "file not found"}

    size = ap.stat().st_size
    digest = file_digest(ap)

    entry: Dict[str, Any] = {
        "path": str(ap),
        "size": size,
        "digest": digest,
        "source_dir": str(asset_path.relative_to(asset_path.anchor).parent),
        "category": classify_asset(asset_path),
    }

    # Try kkloader parse — if it's a character card, enrich with char metadata
    if _HAS_KLOADER:
        try:
            kd = kkloader.KoikatuCharaData.load(str(ap), contains_png=True)
            block_sizes: Dict[str, int] = {}
            for name in kd.blockdata:
                obj = getattr(kd, name, None)
                if obj is not None:
                    try:
                        block_sizes[name] = len(bytes(obj))
                    except Exception:
                        block_sizes[name] = -1
            entry.update({
                "product_no": kd.product_no,
                "header": kd.header.decode("utf-8", errors="replace"),
                "version": kd.version.decode("utf-8", errors="replace"),
                "blockdata": kd.blockdata,
                "has_image": kd.image is not None,
                "face_image_len": len(kd.face_image) if kd.face_image else 0,
                "block_sizes": block_sizes,
                "parse_error": None,
            })
        except Exception as e:
            entry["parse_error"] = str(e)
            entry["blockdata"] = []
    else:
        entry["parse_error"] = "kkloader disabled"

    return entry


def classify_asset(path: Path) -> str:
    """Classify a .png asset by its parent directory."""
    p = str(path)
    if "/chara/" in p or "\\chara\\" in p:
        return "chara"
    if "/coordinate/" in p or "\\coordinate\\" in p:
        return "coordinate"
    if "/bg/" in p or "\\bg\\" in p:
        return "background"
    if "/scene/" in p or "\\scene\\" in p:
        return "scene"
    return "other"


def _merge_wd_tags(
    entry: Dict[str, Any],
    tags_json: Path,
    basename: str,
) -> None:
    """Merge WD tag data from a tags JSON file into an index entry.

    The tags JSON maps image basenames to tag dicts (as written by
    wd_tagger.py --image-dir --out).  We look up *basename* (the file
    name only, not the full path) so that index entries for assets found
    under any directory tree can pick up tags from a single batch run.
    """
    try:
        data = json.loads(tags_json.read_text(encoding="utf-8"))
    except Exception as e:
        log.debug("cannot read tags json %s: %s", tags_json, e)
        return
    tags = data.get(basename)
    if isinstance(tags, dict) and tags:
        # Drop the 4 rating-category labels (general/sensitive/
        # questionable/explicit) — they're constant boilerplate scores
        # across all renders, not useful for matching.
        rating_noise = frozenset({"general", "sensitive", "questionable", "explicit"})
        filtered = {k: v for k, v in tags.items() if k not in rating_noise}
        if filtered:
            entry["wd_tags"] = filtered


# ---------------------------------------------------------------------------
# Thumbnail rendering (via KkRenderBridge)
# ---------------------------------------------------------------------------

def render_thumbnail(
    card_path: Path,
    thumb_path: Path,
    preset: str = "front",
    timeout_sec: float = 60.0,
) -> bool:
    """Submit a render job for a thumbnail and wait for the response.

    Returns True if the screenshot was captured successfully.
    """
    from datetime import datetime

    job_id = "thumb_" + card_path.stem
    request_path = REQUEST_DIR / f"{job_id}.json"
    response_path = request_path.with_name(f"{job_id}.response.json")

    # Clean any stale response
    if response_path.exists():
        response_path.unlink()

    req = {
        "character_path": str(_win(card_path.resolve())),
        "camera_preset": preset,
        "output_path": str(thumb_path.resolve()),
    }
    REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(req, indent=2))

    log.info("  submitted thumb %s → %s", job_id, thumb_path.name)

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if response_path.exists():
            resp = json.loads(response_path.read_text())
            if resp.get("success"):
                if thumb_path.exists():
                    log.info("  OK: %s (%d bytes)", thumb_path.name, thumb_path.stat().st_size)
                    return True
                else:
                    log.warning("  response says success but no PNG at %s", thumb_path)
                    return False
            else:
                log.warning("  render failed: %s", resp.get("error", "unknown"))
                return False
        time.sleep(1.0)

    log.warning("  TIMEOUT waiting for %s", job_id)
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("asset_index.json"),
        help="Output JSON index path (default: asset_index.json)",
    )
    parser.add_argument(
        "--render-thumbs", "-t",
        action="store_true",
        help="Render thumbnails for chara cards via KkRenderBridge (needs game running)",
    )
    parser.add_argument(
        "--thumb-preset",
        default="front",
        choices=["front", "3quarter"],
        help="Camera preset for thumbnails",
    )
    parser.add_argument(
        "--thumb-timeout",
        type=float,
        default=60.0,
        help="Max seconds to wait per thumbnail render",
    )
    parser.add_argument(
        "--category",
        choices=["chara", "asset", "all"],
        default="all",
        help="Which asset category to index (default: all)",
    )
    parser.add_argument(
        "--no-kkloader",
        action="store_true",
        help="Skip kkloader parsing (file-only index)",
    )
    parser.add_argument(
        "--tag-with",
        type=Path,
        default=None,
        help="Path to a .json file mapping image basenames → WD tags "
             "(e.g. tags/render_tags.json from wd_tagger.py --image-dir). "
             "When set, each index entry gets a \"wd_tags\" field from the "
             "matching basename.",
    )
    args = parser.parse_args()

    global _HAS_KLOADER
    if args.no_kkloader:
        _HAS_KLOADER = False

    index: List[Dict[str, Any]] = []
    seen_digests: set = set()

    def add_entry(entry: Dict[str, Any]) -> bool:
        """Add entry to index, skipping duplicates by digest. Returns True if added."""
        d = entry.get("digest")
        if d and d in seen_digests:
            return False  # duplicate
        if d:
            seen_digests.add(d)
        index.append(entry)
        return True

    # --- Character cards ---
    if args.category in ("chara", "all"):
        log.info("Scanning %d char dirs...", len(CHAR_DIRS))
        cards = scan_char_dirs(CHAR_DIRS)
        log.info("Found %d char card .png files", len(cards))

        if args.render_thumbs:
            THUMB_DIR.mkdir(parents=True, exist_ok=True)
            log.info("Thumbnails → %s", THUMB_DIR)

        t0 = time.time()
        for i, card in enumerate(cards, 1):
            if i % 50 == 0 or i == len(cards):
                elapsed = time.time() - t0
                log.info("[%d/%d] %s  (%.1f cards/min)", i, len(cards), card.name, i / elapsed * 60)

            thumb_path = THUMB_DIR / card.name if args.render_thumbs else None
            digest = file_digest(_win(card))

            if args.render_thumbs and thumb_path.exists():
                entry = index_card(card)
                entry["thumbnail"] = str(thumb_path)
                entry["digest"] = digest
                add_entry(entry)
                continue

            entry = index_card(card)
            entry["digest"] = digest

            if args.render_thumbs and entry.get("has_image") and not thumb_path.exists():
                log.info("Rendering thumb for %s...", card.name)
                if render_thumbnail(card, thumb_path, args.thumb_preset, args.thumb_timeout):
                    entry["thumbnail"] = str(thumb_path)

            # Merge WD tags from the provided JSON if available
            if args.tag_with and args.tag_with.exists():
                _merge_wd_tags(entry, args.tag_with, card.name)

            add_entry(entry)

    # --- Asset/library files ---
    if args.category in ("asset", "all"):
        log.info("Scanning %d asset dirs...", len(ASSET_DIRS))
        assets = scan_asset_dirs(ASSET_DIRS)
        log.info("Found %d asset .png files", len(assets))

        t0 = time.time()
        for i, asset in enumerate(assets, 1):
            if i % 100 == 0 or i == len(assets):
                elapsed = time.time() - t0
                log.info("[%d/%d] %s  (%.1f files/min)", i, len(assets), asset.name, i / elapsed * 60)

            entry = index_asset(asset)
            if args.tag_with and args.tag_with.exists():
                _merge_wd_tags(entry, args.tag_with, asset.name)
            add_entry(entry)

    # --- Summary ---
    # cards/assets may be undefined if only one category was selected
    n_cards = len(cards) if 'cards' in dir() else 0
    n_assets = len(assets) if 'assets' in dir() else 0
    dupes = (n_cards + n_assets) - len(index) if args.category == "all" else 0
    ok = sum(1 for e in index if "error" not in e and not e.get("parse_error"))
    failed = sum(1 for e in index if e.get("error") or e.get("parse_error"))
    thumbed = sum(1 for e in index if e.get("thumbnail"))

    log.info("Done: %d entries in index (%d dupes skipped), %d OK, %d failed, %d thumbnails",
             len(index), dupes, ok, failed, thumbed)
    log.info("Index written to %s", args.output)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    # Category breakdown
    cats: Dict[str, int] = {}
    for e in index:
        c = e.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    log.info("Category breakdown: %s", json.dumps(cats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
