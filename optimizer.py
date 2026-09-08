#!/usr/bin/env python3
"""
Optimizer — discrete shortlist + continuous convergence.

Two-phase pipeline for matching a reference image to a Koikatsu character
card + camera preset:

  Phase A — Discrete shortlist
    Tag the reference image with the WD tagger, then score every card in
    the asset index by tag similarity (Jaccard or weighted overlap).
    Return the top-K candidates.

  Phase B — Continuous convergence
    For each shortlist candidate (or a single --character), render at
    each requested camera preset, re-tag each render, score against the
    reference, and pick the best (card, preset) pair.

Usage:
    python optimizer.py \
        --reference renders/reference.png \
        --index asset_index.json \
        --wd-model models/wd-tagger/model.onnx \
        --wd-tags models/wd-tagger/selected_tags.csv \
        --top-k 5 \
        --presets front 3quarter

    # Single-card camera tuning (skip shortlist):
    python optimizer.py \
        --reference renders/reference.png \
        --character "C:/Games/Koikatsu/UserData/chara/female/[Community]/KK_398582.png" \
        --wd-model models/wd-tagger/model.onnx \
        --wd-tags models/wd-tagger/selected_tags.csv \
        --presets front 3quarter
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

# ---------------------------------------------------------------------------
# WD tagger (local import from workspace)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from wd_tagger import WDTagger, CATEGORY_GENERAL, CATEGORY_RATING

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Tag similarity functions
# ---------------------------------------------------------------------------

def tag_jaccard(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
) -> float:
    """Binary Jaccard of above-threshold tag sets."""
    set_a = set(tags_a.keys())
    set_b = set(tags_b.keys())
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def tag_weighted_score(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
    weight_exponent: float = 2.0,
) -> float:
    """Weighted overlap: sum of min(conf_a,conf_b)^exp over shared tags,
    normalized by sqrt of per-side conf mass."""
    shared = set(tags_a.keys()) & set(tags_b.keys())
    if not shared:
        return 0.0
    shared_sum = sum(
        min(tags_a[t], tags_b[t]) ** weight_exponent for t in shared
    )
    mass_a = sum(v ** weight_exponent for v in tags_a.values()) + 1e-9
    mass_b = sum(v ** weight_exponent for v in tags_b.values()) + 1e-9
    return shared_sum / np.sqrt(mass_a * mass_b)


def tag_similarity(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
    method: str = "weighted",
    **kwargs,
) -> float:
    if method == "jaccard":
        return tag_jaccard(tags_a, tags_b)
    return tag_weighted_score(tags_a, tags_b, **kwargs)


# ---------------------------------------------------------------------------
# Phase A — discrete shortlist
# ---------------------------------------------------------------------------

def load_index(path: Path) -> List[Dict]:
    """Load an asset index or tag cache JSON.

    Handles two shapes:
      - asset index: list of {path, wd_tags, ...}
      - tag cache:  dict {filename: {tag: conf}}
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Tag cache shape: {basename: {tag: conf}}
        return [{"path": k, "wd_tags": v} for k, v in data.items()]
    return []


def shortlist(
    reference_tags: Dict[str, float],
    index: List[Dict],
    top_k: int = 10,
    method: str = "weighted",
) -> List[Dict]:
    """Score every tagged entry in the index against the reference.

    Returns top-K by similarity, each with path, score, shared tag count.
    """
    results = []
    for entry in index:
        path = entry.get("path") or entry.get("card_path") or entry.get("file")
        if not path:
            continue
        tags = entry.get("wd_tags")
        if not tags or not isinstance(tags, dict):
            continue
        score = tag_similarity(reference_tags, tags, method=method)
        results.append({
            "path": path,
            "score": round(float(score), 4),
            "tags": tags,
            "n_shared": len(set(reference_tags) & set(tags)),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Phase B — continuous convergence (render + tag + score)
# ---------------------------------------------------------------------------

def submit_and_wait(
    character_path: str,
    preset: str,
    output_path: Path,
    request_dir: Path,
    timeout: float = 180.0,
) -> bool:
    """Submit a render request JSON and poll for the response.

    Writes {character_path, camera_preset, output_path} to
    request_dir/<job_id>.json and watches for <job_id>.response.json.
    """
    request_dir = Path(request_dir)
    request_dir.mkdir(parents=True, exist_ok=True)

    job_id = Path(output_path).stem
    request_path = request_dir / f"{job_id}.json"
    response_path = request_path.with_name(f"{job_id}.response.json")

    if response_path.exists():
        response_path.unlink()

    req = {
        "character_path": str(Path(character_path).resolve()),
        "camera_preset": preset,
        "output_path": str(output_path.resolve()),
    }
    request_path.write_text(json.dumps(req, indent=2))

    deadline = time.time() + timeout
    while time.time() < deadline:
        if response_path.exists():
            try:
                resp = json.loads(response_path.read_text())
                if resp.get("success"):
                    if output_path.exists():
                        print(f"      render OK: {output_path.name} "
                              f"({output_path.stat().st_size} bytes)")
                        return True
                    else:
                        print(f"      response ok but no PNG at {output_path}")
                        return False
                else:
                    err = resp.get("error", "unknown")
                    print(f"      render failed: {err}")
                    return False
            except Exception as e:
                print(f"      bad response: {e}")
                return False
        time.sleep(1.0)

    print(f"      TIMEOUT after {timeout:.0f}s")
    return False


def phase_b(
    tagger: WDTagger,
    reference_tags: Dict[str, float],
    candidates: List[Dict],
    presets: Sequence[str],
    render_dir: Path,
    request_dir: Path,
    tag_cache: Optional[Path] = None,
    similarity: str = "weighted",
    render_timeout: float = 180.0,
) -> Optional[Dict]:
    """Render each candidate at each preset, re-tag, score, pick best.

    Returns the best (card, preset, score, render_tags) across all
    candidates, or None if nothing succeeded.
    """
    # Load tag cache (pre-tagged renders)
    cache: Dict[str, Dict[str, float]] = {}
    if tag_cache and tag_cache.exists():
        try:
            raw = json.loads(tag_cache.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cache = raw
        except Exception:
            pass

    all_results: List[Dict] = []

    for ci, cand in enumerate(candidates, 1):
        card_path = cand["path"]
        card_name = Path(card_path).stem

        print(f"\n[optimizer] Phase B [{ci}/{len(candidates)}]: {card_name}")

        best_for_card: Optional[Dict] = None

        for preset in presets:
            render_name = f"{card_name}_{preset}.png"
            render_path = render_dir / render_name
            render_path.parent.mkdir(parents=True, exist_ok=True)

            # Resolve tags: cache → existing render → new render
            tags: Optional[Dict[str, float]] = None

            if render_name in cache:
                tags = cache[render_name]
                print(f"  [{preset}] cached tags ({len(tags)} tags)")
            elif render_path.exists():
                tags = tagger.tag_image(str(render_path))
                print(f"  [{preset}] tagged existing render ({len(tags)} tags)")
            else:
                print(f"  [{preset}] submitting render...")
                sys.stdout.flush()
                ok = submit_and_wait(
                    character_path=card_path,
                    preset=preset,
                    output_path=render_path,
                    request_dir=request_dir,
                    timeout=render_timeout,
                )
                if not ok:
                    print(f"  [{preset}] SKIP (render failed)")
                    continue
                tags = tagger.tag_image(str(render_path))
                print(f"  [{preset}] tagged new render ({len(tags)} tags)")

            score = tag_similarity(reference_tags, tags, method=similarity)
            entry = {
                "card_path": card_path,
                "card_name": card_name,
                "preset": preset,
                "render": render_name,
                "score": round(float(score), 4),
                "render_tags": tags,
                "n_tags": len(tags),
            }
            all_results.append(entry)

            if best_for_card is None or score > best_for_card["score"]:
                best_for_card = entry

            print(f"      score={score:.4f}  tags={len(tags)}")

        if best_for_card:
            print(f"  → best for {card_name}: {best_for_card['preset']} "
                  f"score={best_for_card['score']:.4f}")

    if not all_results:
        return None

    all_results.sort(key=lambda r: r["score"], reverse=True)
    best = all_results[0]
    print(f"\n[optimizer] Phase B overall best: "
          f"{best['card_name']} / {best['preset']} "
          f"score={best['score']:.4f}")
    return best


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--reference", required=True,
                        help="Reference image to match against")
    parser.add_argument("--index", default="asset_index.json",
                        help="Asset index JSON (pre-tagged cards) — or a "
                             "tag cache JSON ({name: {tag: conf}})")
    parser.add_argument("--render-dir", default="renders/",
                        help="Directory for render output PNGs")
    parser.add_argument("--request-dir", default="render_requests/",
                        help="Directory for render request/response JSON")
    parser.add_argument("--wd-model", required=True,
                        help="WD tagger .onnx model path")
    parser.add_argument("--wd-tags", required=True,
                        help="WD tagger selected_tags.csv path")
    parser.add_argument("--top-k", type=int, default=5,
                        help="Shortlist size for Phase A")
    parser.add_argument("--presets", nargs="+",
                        default=["front", "3quarter"],
                        help="Camera presets to try in Phase B")
    parser.add_argument("--similarity", default="weighted",
                        choices=["jaccard", "weighted"],
                        help="Tag similarity metric")
    parser.add_argument("--tag-cache", default=None,
                        help="Optional pre-tagged renders JSON to avoid "
                             "re-tagging existing renders")
    parser.add_argument("--no-render", action="store_true",
                        help="Phase A only — skip Phase B rendering")
    parser.add_argument("--character", default=None,
                        help="Skip shortlist; optimize this character card "
                             "directly (Phase B only)")
    parser.add_argument("--output", default="optimizer_result.json",
                        help="Where to write the final result JSON")
    parser.add_argument("--render-timeout", type=float, default=180.0,
                        help="Max seconds to wait per render job")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # --- Load tagger ---
    tagger = WDTagger(args.wd_model, args.wd_tags)
    print(f"[optimizer] WD tagger ready ({Path(args.wd_model).name})")

    # --- Phase A: tag reference ---
    ref_path = Path(args.reference)
    if not ref_path.exists():
        print(f"ERROR: reference not found: {args.reference}", file=sys.stderr)
        return 1

    print(f"\n[optimizer] Phase A: tagging reference {ref_path.name}")
    ref_tags = tagger.tag_image(str(ref_path))
    print(f"[optimizer] Reference tags ({len(ref_tags)}):")
    for tag, conf in list(ref_tags.items())[:12]:
        print(f"    {tag:28s} {conf:.3f}")
    if len(ref_tags) > 12:
        print(f"    ... ({len(ref_tags) - 12} more)")
    print()

    # --- Load index ---
    index_path = Path(args.index)
    index: List[Dict] = []
    if index_path.exists():
        index = load_index(index_path)
        print(f"[optimizer] Loaded {len(index)} entries from {index_path.name}")
    else:
        print(f"[optimizer] No index at {index_path} — "
              f"skipping Phase A shortlist")

    # --- Phase A: shortlist or direct character ---
    if args.character:
        card_path = args.character
        if not Path(card_path).exists():
            print(f"ERROR: character card not found: {card_path}", file=sys.stderr)
            return 1
        candidates = [{
            "path": card_path,
            "score": 1.0,
            "tags": {},
            "n_shared": 0,
        }]
        print(f"\n[optimizer] Phase A: using specified character "
              f"{Path(card_path).name} (bypassing shortlist)")
    elif index:
        candidates = shortlist(ref_tags, index, top_k=args.top_k,
                               method=args.similarity)
        print(f"\n[optimizer] Phase A: shortlist ({len(candidates)} candidates):")
        if not candidates:
            print("  (no candidates with tags in index)")
        for i, c in enumerate(candidates, 1):
            print(f"    {i}. {Path(c['path']).name:40s} "
                  f"score={c['score']:.4f}  shared={c['n_shared']}")
        print()
    else:
        print("[optimizer] No index and no --character — nothing to optimize")
        return 1

    # --- Phase B: continuous convergence ---
    result: Dict = {
        "reference": str(ref_path),
        "reference_tags": ref_tags,
        "shortlist": candidates,
        "similarity_method": args.similarity,
    }

    if args.no_render:
        print("[optimizer] --no-render: Phase A only")
        best = candidates[0] if candidates else None
        result["best"] = best
    else:
        best = phase_b(
            tagger=tagger,
            reference_tags=ref_tags,
            candidates=candidates,
            presets=args.presets,
            render_dir=Path(args.render_dir),
            request_dir=Path(args.request_dir),
            tag_cache=Path(args.tag_cache) if args.tag_cache else None,
            similarity=args.similarity,
            render_timeout=args.render_timeout,
        )
        result["best"] = best

    # --- Write result ---
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\n[optimizer] Result → {out_path}")

    if best:
        cn = best.get("card_name") or Path(best.get("path", "?")).name
        pr = best.get("preset") or "n/a"
        print(f"[optimizer] BEST: {cn} / {pr} "
              f"score={best['score']:.4f}")
        rname = best.get("render") or best.get("path", "?")
        print(f"[optimizer] Render: {rname}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
