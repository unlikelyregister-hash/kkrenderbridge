#!/usr/bin/env python3
"""
Sanity check for wd_tagger.py before trusting it for the full asset
indexing pass. Preprocessing bugs (wrong channel order, no padding,
wrong normalization, wrong input size) tend to produce tag output that
LOOKS plausible -- real Danbooru vocabulary, reasonable-sounding
confidences -- but is actually wrong. A silent bug here would corrupt
every downstream shortlist search, so this is a "look at it yourself"
check, not a script that passes/fails on its own.

What this does:
  1. Picks a handful of your already-indexed chara renders
  2. Tags each with wd_tagger.py
  3. Prints top-N tags per image next to a thumbnail-sized ASCII summary
     (color/size stats) so you can eyeball obvious mismatches without
     needing to separately open every image file

  4. Runs two structural checks that WOULD catch known preprocessing
     bugs even without a human looking:
       a) Same image tagged twice -> results must be identical
          (catches non-determinism in preprocessing/inference)
       b) A horizontally-flipped copy of the same image -> tag SET
          should be nearly identical, confidences may shift slightly
          but symmetric tags (e.g. hair color, general style tags)
          should not collapse to near-zero. A big drop across the
          board on the flipped copy is a strong signal of a
          preprocessing orientation/channel bug.

Usage:
    python wd_tagger_smoke_test.py \
        --model models/wd-tagger/model.onnx \
        --tags models/wd-tagger/selected_tags.csv \
        --image-dir renders/chara_samples \
        --sample-count 5
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict

import numpy as np
from PIL import Image

from wd_tagger import WDTagger, CATEGORY_GENERAL, CATEGORY_RATING

# ---------------------------------------------------------------------------
# Image summary -- cheap non-tagger signal
# ---------------------------------------------------------------------------


def summarize_image(path: str) -> str:
    """Return a compact string describing the image's size and average color
    so you can spot-obvious mismatches against tag output (e.g. tagger says
    blonde_hair but avg RGB is clearly not yellow/gold-leaning)."""
    img = Image.open(path).convert("RGB")
    small = img.resize((16, 16))
    arr = np.asarray(small, dtype=np.float32)
    avg = arr.mean(axis=(0, 1))
    return f"size={img.size} avg_rgb=({avg[0]:.0f},{avg[1]:.0f},{avg[2]:.0f})"


def print_top_tags(tags: Dict[str, float], n: int = 12):
    """Print top-N tags with a confidence bar for manual eyeballing."""
    for i, (name, conf) in enumerate(tags.items()):
        if i >= n:
            break
        bar = "#" * max(0, int(conf * 20))
        print(f"    {name:30s} {conf:.3f} {bar}")


# ---------------------------------------------------------------------------
# Structural checks
# ---------------------------------------------------------------------------


def determinism_check(tagger: WDTagger, image_path: str) -> bool:
    """Tag the same image twice -- results must be byte-identical.

    Catches non-determinism in preprocessing or inference (rare but
    possible with certain ONNX execution providers and multi-threaded
    kernels).
    """
    t1 = tagger.tag_image(image_path)
    t2 = tagger.tag_image(image_path)
    if t1 != t2:
        print(f"  [FAIL] non-deterministic output for {image_path}")
        diff_keys = set(t1.keys()) ^ set(t2.keys())
        print(f"         differing tag sets: {diff_keys}")
        common = set(t1.keys()) & set(t2.keys())
        for k in sorted(common):
            if t1[k] != t2[k]:
                print(f"         {k}: {t1[k]} vs {t2[k]}")
        return False
    print(f"  [PASS] deterministic output ({len(t1)} tags)")
    return True


def flip_consistency_check(
    tagger: WDTagger,
    image_path: str,
    tmp_dir: Path,
    jaccard_threshold: float = 0.6,
) -> bool:
    """Flip the image horizontally and re-tag; the tag SET should stay
    largely overlapping.

    Some tags legitimately change on a flip (e.g. hair_over_one_eye,
    asymmetrical_hair), so this is a soft check: a low Jaccard similarity
    is worth a manual look but doesn't necessarily mean a bug. A collapse
    across the board on the flipped copy is a strong signal of a
    preprocessing orientation or channel-order bug.
    """
    img = Image.open(image_path).convert("RGB")
    flipped = img.transpose(Image.FLIP_LEFT_RIGHT)

    with tempfile.NamedTemporaryFile(
        suffix=".png", dir=str(tmp_dir), delete=False
    ) as fh:
        flipped_path = Path(fh.name)
        flipped.save(flipped_path)

    try:
        original_tags = tagger.tag_image(image_path)
        flipped_tags = tagger.tag_image(str(flipped_path))

        orig_set = set(original_tags.keys())
        flip_set = set(flipped_tags.keys())
        overlap = orig_set & flip_set
        union = orig_set | flip_set

        jaccard = len(overlap) / len(union) if union else 1.0
        print(
            f"  flip-consistency Jaccard: {jaccard:.3f} "
            f"({len(overlap)}/{len(union)} tags shared)"
        )

        # Show which tags dropped out on flip -- useful for diagnosis
        dropped = orig_set - flip_set
        gained = flip_set - orig_set
        if dropped:
            print(f"    dropped on flip: {sorted(dropped)[:8]}")
        if gained:
            print(f"    gained on flip:  {sorted(gained)[:8]}")

        if jaccard < jaccard_threshold:
            print(
                f"  [WARN] low overlap after flip (<{jaccard_threshold}) -- "
                "inspect manually; could be legit orientation-sensitive tags "
                "OR a preprocessing bug"
            )
            return False
        print(f"  [PASS] flip consistency reasonable (Jaccard >= {jaccard_threshold})")
        return True
    finally:
        flipped_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--model", required=True, help="Path to WD tagger .onnx file")
    parser.add_argument("--tags", required=True, help="Path to selected_tags.csv")
    parser.add_argument("--image-dir", required=True,
                        help="Directory of known chara renders to sample from")
    parser.add_argument("--sample-count", type=int, default=5,
                        help="How many images to sample (picks first N)")
    parser.add_argument("--top-n", type=int, default=12,
                        help="How many top tags to print per image for manual review")
    parser.add_argument("--jaccard-threshold", type=float, default=0.6,
                        help="Below this Jaccard on the flip test = warning")
    args = parser.parse_args()

    image_dir = Path(args.image_dir)
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    all_images = sorted(
        p for p in image_dir.iterdir() if p.suffix.lower() in exts
    )

    if not all_images:
        print(f"ERROR: no images found in {image_dir}", file=sys.stderr)
        return 1

    sample = all_images[: args.sample_count]
    print(
        f"[smoke_test] sampling {len(sample)} of {len(all_images)} images "
        f"from {image_dir}\n"
    )

    tagger = WDTagger(args.model, args.tags)
    tmp_dir = Path(tempfile.mkdtemp(prefix="wd_smoke_"))

    all_pass = True
    report: Dict[str, Dict] = {}

    for img_path in sample:
        print(f"=== {img_path.name} ===")
        print(f"  {summarize_image(str(img_path))}")

        tags = tagger.tag_image(
            str(img_path),
            include_categories=(CATEGORY_GENERAL, CATEGORY_RATING),
        )
        print(f"  top {args.top_n} tags (general + rating):")
        print_top_tags(tags, n=args.top_n)

        det_ok = determinism_check(tagger, str(img_path))
        flip_ok = flip_consistency_check(
            tagger, str(img_path), tmp_dir, args.jaccard_threshold
        )

        report[img_path.name] = {
            "tags": tags,
            "determinism": "PASS" if det_ok else "FAIL",
            "flip_jaccard": flip_ok,  # bool + message printed above
        }

        all_pass = all_pass and det_ok and flip_ok
        print()

    # Summary
    print("=" * 60)
    if all_pass:
        print("[smoke_test] structural checks PASSED for all sampled images.")
    else:
        print(
            "[smoke_test] some checks FAILED or WARNED -- "
            "investigate before trusting this for the full indexing pass."
        )
    print()
    print(
        "MANUAL STEP (required, not automated): look at the top tags "
        "printed above for each image and confirm they match what you "
        "can see in the actual render (hair color/style, eye color, "
        "clothing, etc). This is the check that actually catches a "
        "subtly-wrong-but-plausible-looking preprocessing bug -- the "
        "structural checks above only catch gross failures."
    )

    # Write a short JSON report for record-keeping
    report_path = tmp_dir / "smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n[smoke_test] report written to {report_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
