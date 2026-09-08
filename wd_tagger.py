#!/usr/bin/env python3
"""
WD (Waifu Diffusion) tagger wrapper -- runs a Danbooru-trained ONNX
tagging model on an image and returns {tag: confidence} scores.

Used two ways in the pipeline:
  1. Batch mode from asset_indexer.py -- tag every rendered asset once,
     store results in the asset index.
  2. Single-image mode as an MCP tool / CLI -- tag an incoming reference
     image at the start of an optimizer run.

Model files (not included -- download once):
    huggingface-cli download SmilingWolf/wd-swinv2-tagger-v3 \
        model.onnx selected_tags.csv --local-dir ./models/wd-tagger

Usage:
    python wd_tagger.py --model models/wd-tagger/model.onnx \
                         --tags models/wd-tagger/selected_tags.csv \
                         --image some_render.png

    python wd_tagger.py --model ... --tags ... --image-dir renders/ \
                         --out tags_output.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image
import onnxruntime as ort

# ---------------------------------------------------------------------------
# Where to cache the model locally (workspace-relative)
# ---------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "models" / "wd-tagger"

# Category codes used in the WD tagger label CSVs (selected_tags.csv).
# 0 = general, 4 = character, 9 = rating -- keeping this explicit rather
# than hardcoding indices makes it easy to filter by category later
# (e.g. drop character-name tags, keep only general + rating).
CATEGORY_GENERAL = 0
CATEGORY_CHARACTER = 4
CATEGORY_RATING = 9

# Default thresholds per category (matched to SmilingWolf v3 model).
THRESHOLD_GENERAL = 0.35
THRESHOLD_CHARACTER = 0.85

# Tags to always exclude regardless of score (booru noise, not useful for
# reference matching).
EXCLUDE_TAGS = frozenset({
    "rating_explicit", "rating_safe", "rating_questionable", "rating_ambiguous",
    "score_9", "score_8", "score_7", "score_6", "score_5", "score_4",
    "score_3", "score_2", "score_1",
})


# ---------------------------------------------------------------------------
# WDTagger
# ---------------------------------------------------------------------------

class WDTagger:
    """Loads a WD tagger ONNX model + selected_tags.csv and produces
    {tag_name: confidence} dicts for images."""

    def __init__(
        self,
        model_path: str,
        tags_csv_path: str,
        providers: Optional[List[str]] = None,
        exclude_tags: Optional[set] = None,
    ):
        self._providers = providers or ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(
            str(model_path),
            providers=self._providers,
        )
        input_info = self.session.get_inputs()[0]
        self.input_name = input_info.name
        self.input_size = self._infer_input_size(input_info.shape)
        self.input_type = input_info.type

        self.tag_names, self.tag_categories = self._load_tags(tags_csv_path)
        self._exclude = frozenset(exclude_tags) if exclude_tags else EXCLUDE_TAGS
        self._n_tags = len(self.tag_names)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_input_size(shape) -> int:
        """Read (or guess) the square input size from the model's input shape."""
        dims = [int(d) for d in shape if isinstance(d, int) and d > 1]
        if dims:
            return dims[0]
        return 448  # WD tagger v3 default

    @staticmethod
    def _load_tags(csv_path: str) -> Tuple[List[str], List[int]]:
        names, categories = [], []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                names.append(row["name"])
                categories.append(int(row["category"]))
        return names, categories

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def preprocess(self, image_path: str) -> np.ndarray:
        """Convert an image file to the model's expected input tensor.

        Strategy: pad to square (preserving aspect ratio), resize to the
        model's input size, then convert to BGR no-normalized uint8 batch.
        This matches the SmilingWolf v3 export conventions; if you swap to a
        different tagger variant, verify against its model card.
        """
        img = Image.open(image_path).convert("RGB")

        w, h = img.size
        side = max(w, h)
        padded = Image.new("RGB", (side, side), (255, 255, 255))
        padded.paste(img, ((side - w) // 2, (side - h) // 2))

        resized = padded.resize(
            (self.input_size, self.input_size),
            Image.LANCZOS,
        )

        arr = np.asarray(resized, dtype=np.float32)
        arr = arr[:, :, ::-1]            # RGB → BGR
        arr = np.expand_dims(arr, axis=0)  # [1, H, W, 3]
        return arr

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def tag_image(
        self,
        image_path: str,
        general_threshold: float = THRESHOLD_GENERAL,
        character_threshold: float = THRESHOLD_CHARACTER,
        include_categories: Tuple[int, ...] = (CATEGORY_GENERAL, CATEGORY_RATING),
        exclude_tags: Optional[set] = None,
    ) -> Dict[str, float]:
        """Tag a single image and return {tag: confidence} for tags above
        the category-specific thresholds."""
        inputs = self.preprocess(image_path)
        t0 = time.perf_counter()
        outputs = self.session.run(None, {self.input_name: inputs})
        dt = time.perf_counter() - t0

        probs = outputs[0][0]  # [n_tags]
        exclude = frozenset(exclude_tags) if exclude_tags else self._exclude

        results: Dict[str, float] = {}
        for i in range(self._n_tags):
            prob = float(probs[i])
            name = self.tag_names[i]
            cat = self.tag_categories[i]

            if name in exclude:
                continue
            if cat == CATEGORY_GENERAL:
                if cat not in include_categories or prob < general_threshold:
                    continue
            elif cat == CATEGORY_CHARACTER:
                if cat not in include_categories or prob < character_threshold:
                    continue
            elif cat == CATEGORY_RATING:
                if cat not in include_categories:
                    continue
            else:
                continue

            results[name] = round(prob, 4)

        return dict(
            sorted(results.items(), key=lambda kv: kv[1], reverse=True)
        )

    # ------------------------------------------------------------------
    # Batch convenience
    # ------------------------------------------------------------------

    def tag_directory(
        self,
        image_dir: str,
        out_path: Optional[str] = None,
        general_threshold: float = THRESHOLD_GENERAL,
        character_threshold: float = THRESHOLD_CHARACTER,
        include_categories: Tuple[int, ...] = (CATEGORY_GENERAL, CATEGORY_RATING),
        exts: Optional[set] = None,
        progress_every: int = 20,
    ) -> Dict[str, Dict[str, float]]:
        """Tag every image in a directory and return {filename: tags}."""
        exts = frozenset(exts) if exts else {".png", ".jpg", ".jpeg", ".webp"}
        images = sorted(
            p for p in Path(image_dir).iterdir()
            if p.suffix.lower() in exts
        )
        results: Dict[str, Dict[str, float]] = {}
        t0 = time.perf_counter()
        for i, img_path in enumerate(images, 1):
            try:
                tags = self.tag_image(
                    str(img_path),
                    general_threshold=general_threshold,
                    character_threshold=character_threshold,
                    include_categories=include_categories,
                )
                results[img_path.name] = tags
            except Exception as e:
                results[img_path.name] = {"__error__": str(e)}
            if i % progress_every == 0 or i == len(images):
                elapsed = time.perf_counter() - t0
                per_img = elapsed / i if i else 0
                eta = per_img * (len(images) - i)
                print(
                    f"  [wd_tag] {i}/{len(images)}  "
                    f"{img_path.name}  {per_img:.3f}s/img  eta {eta:.0f}s",
                    flush=True,
                )
        if out_path:
            Path(out_path).write_text(
                json.dumps(results, indent=2, ensure_ascii=False)
            )
            print(f"[wd_tag] wrote {out_path}")
        return results


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
    parser.add_argument("--image", help="Single image to tag")
    parser.add_argument("--image-dir", help="Directory of images to tag in batch")
    parser.add_argument("--out", help="Write JSON results here (batch mode) "
                                       "or print to stdout if omitted")
    parser.add_argument("--general-threshold", type=float, default=THRESHOLD_GENERAL)
    parser.add_argument("--character-threshold", type=float, default=THRESHOLD_CHARACTER)
    parser.add_argument("--include-character-tags", action="store_true",
                        help="Also include character-name tags "
                             "(off by default -- not useful for the "
                             "reference-matching pipeline)")
    parser.add_argument("--exclude", nargs="*", default=None,
                        help="Extra tag names to exclude")
    args = parser.parse_args()

    if not args.image and not args.image_dir:
        print("ERROR: provide --image or --image-dir", file=sys.stderr)
        return 1

    tagger = WDTagger(
        args.model,
        args.tags,
        exclude_tags=set(args.exclude) if args.exclude else None,
    )

    include = [CATEGORY_GENERAL, CATEGORY_RATING]
    if args.include_character_tags:
        include.append(CATEGORY_CHARACTER)

    if args.image:
        tags = tagger.tag_image(
            args.image,
            general_threshold=args.general_threshold,
            character_threshold=args.character_threshold,
            include_categories=tuple(include),
        )
        out = {"image": args.image, "tags": tags}
        text = json.dumps(out, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(text)
            print(f"[wd_tagger] wrote {args.out}")
        else:
            print(text)
    else:
        tagger.tag_directory(
            args.image_dir,
            out_path=args.out,
            general_threshold=args.general_threshold,
            character_threshold=args.character_threshold,
            include_categories=tuple(include),
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
