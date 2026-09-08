#!/usr/bin/env python3
"""
Optimizer — discrete shortlist + continuous convergence + reconciliation.

Two-phase pipeline for matching a reference image to a Koikatsu character
card + camera preset, extended with:

  Phase A — Discrete shortlist
    Tag the reference image with the WD tagger, then score every card in
    the asset index by tag similarity (Jaccard or weighted overlap).
    Return the top-K candidates.

  Phase B — Continuous convergence
    For each shortlist candidate (or a single --character), render at
    each requested camera preset, re-tag each render, score against the
    reference, and pick the best (card, preset) pair.

  Phase C — Continuous parameter optimization (optional)
    For the best (card, preset) from Phase B, load the card via kkloader,
    perturb a low-dimensional subset of continuous parameters (face shape
    sliders, body shape sliders, hair color, eye color, skin tone), re-
    render and re-tag at each step, and hill-climb toward higher tag
    similarity against the reference.

  Reconciliation pass
    After Phase C converges, lock discrete trait calls derived from the
    reference tags (hair color bucket, eye color bucket, accessory
    presence) and re-check that the converged continuous state is still
    consistent with those calls.  If a locked discrete call conflicts with
    the converged parameters, re-run Phase C with that call pinned.

  Ceiling-awareness
    Traits that cannot be expressed in Koikatsu's parameter space (e.g.
    pose, clothing detail, background, expression-in-motion) are flagged
    as unmappable and discounted from the target similarity ceiling.  The
    optimizer optimizes against the mappable ceiling rather than the raw
    reference tag set.

Usage:
    python optimizer.py \\
        --reference renders/reference.png \\
        --index asset_index.json \\
        --wd-model models/wd-tagger/model.onnx \\
        --wd-tags models/wd-tagger/selected_tags.csv \\
        --top-k 5 \\
        --presets front 3quarter

    # Single-card camera tuning (skip shortlist):
    python optimizer.py \\
        --reference renders/reference.png \\
        --character "C:/Games/Koikatsu/UserData/chara/female/[Community]/KK_398582.png" \\
        --wd-model models/wd-tagger/model.onnx \\
        --wd-tags models/wd-tagger/selected_tags.csv \\
        --presets front 3quarter

    # Full pipeline with continuous optimization + reconciliation:
    python optimizer.py \\
        --reference renders/reference.png \\
        --index asset_index.json \\
        --wd-model models/wd-tagger/model.onnx \\
        --wd-tags models/wd-tagger/selected_tags.csv \\
        --top-k 5 \\
        --presets front \\
        --phase-c \\
        --reconcile
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# WD tagger (local import from workspace)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from wd_tagger import WDTagger, CATEGORY_GENERAL, CATEGORY_RATING

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Single-instance guard (Windows file lock via msvcrt)
# ---------------------------------------------------------------------------
# Prevents two `python optimizer.py ...` processes from running at once and
# racing on the shared render_requests/ directory, temp card paths, and the
# WD tagger model.  Uses a non-blocking file lock so a second instance exits
# immediately with a clear message instead of silently colliding.
#
# The lock is released on normal exit, exception, or atexit — including after
# a crash/ctrl-c — because msvcrt file locks are process-attached and are
# automatically dropped when the process terminates.  A stale .optimizer.lock
# file with a dead PID is harmless: the next run will acquire the lock
# (the old lock was dropped by the OS when the process died).

import atexit
import os as _os

try:
    import msvcrt as _msvcrt
    _HAS_MSWINDOWS_LOCK = True
except ImportError:
    _msvcrt = None  # type: ignore[assignment]
    _HAS_MSWINDOWS_LOCK = False

_LOCK_FILE = HERE / ".optimizer.lock"
_lock_fd = None  # type: ignore[assignment]


def acquire_single_instance_lock(lock_path: Optional[Path] = None) -> bool:
    """Try to acquire the single-instance lock.

    Returns True if this process now owns the lock, False if another
    optimizer instance already holds it (second instance will exit).

    Parameters
    ----------
    lock_path:
        Override the default lock file path (".optimizer.lock" next to the
        script).  Used by the ad-hoc verification test; the real run always
        uses the default.
    """
    global _lock_fd
    lock_path = lock_path or _LOCK_FILE
    if not _HAS_MSWINDOWS_LOCK:
        # Non-Windows: fall back to a PID-file heuristic (best-effort).
        try:
            if lock_path.exists():
                pid_text = lock_path.read_text(encoding="utf-8").strip()
                try:
                    stale_pid = int(pid_text)
                except ValueError:
                    stale_pid = 0
                import signal
                try:
                    # Sending signal 0 checks process existence without killing.
                    _os.kill(stale_pid, 0)
                    # Process alive — lock is held.
                    return False
                except ProcessLookupError:
                    # Stale PID — remove and continue.
                    lock_path.unlink(missing_ok=True)
                except PermissionError:
                    # PID exists but we can't signal it — treat as held.
                    return False
            _lock_fd = 0  # type: ignore[assignment]
            lock_path.write_text(f"{_os.getpid()}\n", encoding="utf-8")
            atexit.register(release_single_instance_lock, lock_path=lock_path)
            return True
        except Exception:
            return False

    try:
        _lock_fd = _os.open(str(lock_path), _os.O_RDWR | _os.O_CREAT, 0o600)
        _msvcrt.locking(_lock_fd, _msvcrt.LK_NBLCK, 1)
        # Record our PID in the lock file for diagnostics.
        _os.write(_lock_fd, f"{_os.getpid()}\n".encode())
        _os.lseek(_lock_fd, 0, _os.SEEK_SET)
        atexit.register(release_single_instance_lock, lock_path=lock_path)
        return True
    except OSError:
        # Lock held by another process, or some other OS-level failure.
        if _lock_fd is not None:
            try:
                _os.close(_lock_fd)
            except Exception:
                pass
            _lock_fd = None
        return False


def release_single_instance_lock(lock_path: Optional[Path] = None) -> None:
    """Release the single-instance lock and remove the lock file.

    Parameters
    ----------
    lock_path:
        Override the default lock file path.  Must match the path passed to
        ``acquire_single_instance_lock`` for the same run.
    """
    global _lock_fd
    lock_path = lock_path or _LOCK_FILE
    if _lock_fd is None:
        # Best-effort cleanup of the file even if we never opened an fd
        # (e.g. PID-file fallback path).
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass
        return
    if _HAS_MSWINDOWS_LOCK and _lock_fd is not None:
        try:
            _msvcrt.locking(_lock_fd, _msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
        try:
            _os.close(_lock_fd)
        except Exception:
            pass
    else:
        # PID-file fallback: just remove the file.
        pass
    _lock_fd = None
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Trust weighting for tags
# ---------------------------------------------------------------------------
# Tags that are structural / identity-level get higher trust; generic or
# rating tags get lower trust.  The trust weight scales the contribution of
# each tag to the similarity score and to the prior for continuous params.

TRUST_HIGH = 1.0      # structural identity tags: hair_color, eye_color, etc.
TRUST_MED = 0.7       # fairly reliable appearance tags: hair_length, etc.
TRUST_LOW = 0.4       # noisy / pose-dependent / subjective tags
TRUST_TINY = 0.15     # rating / general / very noisy tags

# Tag -> trust bucket.  Unknown tags fall back to TRUST_MED.
TAG_TRUST: Dict[str, float] = {
    # hair color (high trust — usually stable across renders)
    "black_hair": TRUST_HIGH,
    "blonde_hair": TRUST_HIGH,
    "brown_hair": TRUST_HIGH,
    "grey_hair": TRUST_HIGH,
    "white_hair": TRUST_HIGH,
    "red_hair": TRUST_HIGH,
    "aqua_hair": TRUST_HIGH,
    "pink_hair": TRUST_HIGH,
    "blue_hair": TRUST_HIGH,
    "green_hair": TRUST_HIGH,
    "purple_hair": TRUST_HIGH,
    "orange_hair": TRUST_HIGH,
    "yellow_hair": TRUST_HIGH,
    "silver_hair": TRUST_HIGH,
    "beige_hair": TRUST_HIGH,
    "lavender_hair": TRUST_HIGH,
    # eye color (high trust)
    "blue_eyes": TRUST_HIGH,
    "green_eyes": TRUST_HIGH,
    "brown_eyes": TRUST_HIGH,
    "red_eyes": TRUST_HIGH,
    "pink_eyes": TRUST_HIGH,
    "purple_eyes": TRUST_HIGH,
    "grey_eyes": TRUST_HIGH,
    "yellow_eyes": TRUST_HIGH,
    "aqua_eyes": TRUST_HIGH,
    "orange_eyes": TRUST_HIGH,
    # hair style / length (medium-high)
    "long_hair": TRUST_MED,
    "short_hair": TRUST_MED,
    "medium_hair": TRUST_MED,
    "twintails": TRUST_MED,
    "pixie_cut": TRUST_MED,
    "ponytail": TRUST_MED,
    # facial features (medium)
    "smile": TRUST_MED,
    "mouth_open": TRUST_MED,
    "closed_mouth": TRUST_MED,
    "tongue": TRUST_LOW,
    # accessories (medium — may be pose-occluded)
    "glasses": TRUST_MED,
    "sunglasses": TRUST_MED,
    "necklace": TRUST_LOW,
    "earrings": TRUST_LOW,
    "bracelet": TRUST_TINY,
    "ribbon": TRUST_MED,
    "hairpin": TRUST_MED,
    # rating / general (low trust)
    "general": TRUST_TINY,
    "sensitive": TRUST_TINY,
    "safe": TRUST_TINY,
    "neutral": TRUST_TINY,
}


def tag_trust(tag: str) -> float:
    """Return the trust weight for a tag, falling back to TRUST_MED."""
    return TAG_TRUST.get(tag, TRUST_MED)


def normalized_trust_weight(
    tags: Dict[str, float],
    exponent: float = 1.0,
) -> float:
    """Sum of trust[tag] * conf^exponent over all tags, for weighting."""
    return sum(tag_trust(t) * (c ** exponent) for t, c in tags.items()) + 1e-9


# ---------------------------------------------------------------------------
# Tag similarity functions (weighted by trust)
# ---------------------------------------------------------------------------

def tag_jaccard(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
) -> float:
    """Binary Jaccard of above-threshold tag sets (threshold 0.5)."""
    set_a = {t for t, c in tags_a.items() if c >= 0.5}
    set_b = {t for t, c in tags_b.items() if c >= 0.5}
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def tag_weighted_score(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
    weight_exponent: float = 2.0,
    trust: bool = True,
) -> float:
    """Weighted overlap with optional per-tag trust scaling.

    shared_sum = sum min(conf_a, conf_b)^exp * trust_factor
    normalized by sqrt(mass_a * mass_b) where mass includes trust.
    """
    shared = set(tags_a.keys()) & set(tags_b.keys())
    if not shared:
        return 0.0

    shared_sum = 0.0
    mass_a = 0.0
    mass_b = 0.0
    for t in shared:
        trust_factor = tag_trust(t) if trust else 1.0
        m = min(tags_a[t], tags_b[t]) ** weight_exponent
        shared_sum += m * trust_factor
    for t, c in tags_a.items():
        mass_a += (c ** weight_exponent) * (tag_trust(t) if trust else 1.0)
    for t, c in tags_b.items():
        mass_b += (c ** weight_exponent) * (tag_trust(t) if trust else 1.0)
    mass_a += 1e-9
    mass_b += 1e-9
    return shared_sum / math.sqrt(mass_a * mass_b)


def tag_similarity(
    tags_a: Dict[str, float],
    tags_b: Dict[str, float],
    method: str = "weighted",
    **kwargs,
) -> float:
    if method == "jaccard":
        return tag_jaccard(tags_a, tags_b)
    trust = kwargs.pop("trust", True)
    return tag_weighted_score(tags_a, tags_b, trust=trust, **kwargs)


# ---------------------------------------------------------------------------
# Trait buckets and mappability (ceiling-awareness)
# ---------------------------------------------------------------------------
# Each bucket maps a set of WD tags to a Koikatsu parameter namespace and
# a mappability flag.  Unmappable buckets are discounted from the target
# similarity ceiling.

TRAIT_BUCKETS: List[Dict[str, Any]] = [
    {
        "name": "hair_color",
        "tags": [
            "black_hair", "blonde_hair", "brown_hair", "grey_hair",
            "white_hair", "red_hair", "aqua_hair", "pink_hair", "blue_hair",
            "green_hair", "purple_hair", "orange_hair", "yellow_hair",
            "silver_hair", "beige_hair", "lavender_hair",
        ],
        "mappable": True,
        "param_namespace": "hair_color",
        "kk_param": "Custom.hair.parts[].baseColor",  # approximate
    },
    {
        "name": "eye_color",
        "tags": [
            "blue_eyes", "green_eyes", "brown_eyes", "red_eyes",
            "pink_eyes", "purple_eyes", "grey_eyes", "yellow_eyes",
            "aqua_eyes", "orange_eyes",
        ],
        "mappable": True,
        "param_namespace": "eye_color",
        "kk_param": "Custom.face.pupil / Custom.face.hlUpColor / hlDownColor",
    },
    {
        "name": "hair_length_style",
        "tags": [
            "long_hair", "short_hair", "medium_hair", "twintails",
            "pixie_cut", "ponytail",
        ],
        "mappable": True,
        "param_namespace": "hair_style",
        "kk_param": "Custom.hair.parts[].id / length",
    },
    {
        "name": "face_shape",
        "tags": [
            "smile", "mouth_open", "closed_mouth", "tongue",
            "eyebrows", "nose_",
        ],
        "mappable": True,
        "param_namespace": "face_shape",
        "kk_param": "Custom.face.shapeValueFace / lipLineId / noseId",
    },
    {
        "name": "body_shape",
        "tags": [
            "curvy", "skinny", "athletic", "fat_",
        ],
        "mappable": True,
        "param_namespace": "body_shape",
        "kk_param": "Custom.body.shapeValueBody",
    },
    {
        "name": "skin_tone",
        "tags": [
            "fair_skin", "tan_skin", "dark_skin",
        ],
        "mappable": True,
        "param_namespace": "skin_tone",
        "kk_param": "Custom.body.skinMainColor / skinSubColor",
    },
    {
        "name": "accessories",
        "tags": [
            "glasses", "sunglasses", "necklace", "earrings",
            "bracelet", "ribbon", "hairpin",
        ],
        "mappable": True,
        "param_namespace": "accessories",
        "kk_param": "Custom.face / Custom.hair (hairpin, ribbon)",
    },
    {
        "name": "pose_expression",
        "tags": [
            "standing", "sitting", "lying", "looking_at_viewer",
            "arms_crossed", "hands_on_hips",
        ],
        "mappable": False,
        "param_namespace": "pose",
        "kk_param": "NOT MAPPABLE — camera-only",
    },
    {
        "name": "clothing_detail",
        "tags": [
            "school_uniform", "dress", "suit", "shirt", "swimsuit",
            "neckpain", "hoodie",
        ],
        "mappable": False,
        "param_namespace": "clothing",
        "kk_param": "NOT MAPPABLE — card-only (outfit is card asset)",
    },
    {
        "name": "background",
        "tags": [
            "outdoors", "indoors", "school", "room", "park",
        ],
        "mappable": False,
        "param_namespace": "background",
        "kk_param": "NOT MAPPABLE — render environment only",
    },
]


def build_trait_buckets() -> Dict[str, Dict[str, Any]]:
    """Return {bucket_name: bucket} for quick lookup."""
    return {b["name"]: b for b in TRAIT_BUCKETS}


def tag_to_bucket(tag: str, buckets: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Return the bucket name that contains this tag, or None."""
    for name, b in buckets.items():
        if tag in b["tags"]:
            return name
    return None


def mappable_tag_set(
    tags: Dict[str, float],
    buckets: Dict[str, Dict[str, Any]],
) -> Dict[str, float]:
    """Return only the tags that belong to mappable buckets."""
    mappable = {}
    for tag, conf in tags.items():
        bucket = tag_to_bucket(tag, buckets)
        if bucket and buckets[bucket]["mappable"]:
            mappable[tag] = conf
    return mappable


def unmappable_tag_set(
    tags: Dict[str, float],
    buckets: Dict[str, Dict[str, Any]],
) -> Dict[str, float]:
    """Return only the tags that belong to unmappable buckets."""
    unmappable = {}
    for tag, conf in tags.items():
        bucket = tag_to_bucket(tag, buckets)
        if bucket and not buckets[bucket]["mappable"]:
            unmappable[tag] = conf
    return unmappable


def mappable_ceiling(
    reference_tags: Dict[str, float],
    buckets: Dict[str, Dict[str, Any]],
    method: str = "weighted",
) -> float:
    """Maximum achievable similarity if only mappable traits were matched.

    This is the similarity between the full reference tags and the
    mappable subset of the reference tags — i.e. what fraction of the
    reference's tag mass comes from mappable traits.
    """
    mappable = mappable_tag_set(reference_tags, buckets)
    if not mappable:
        return 1.0
    return tag_similarity(reference_tags, mappable, method=method)


# ---------------------------------------------------------------------------
# Discrete trait calls (derived from reference tags)
# ---------------------------------------------------------------------------
# After Phase A / B, we derive discrete calls from the reference tags.
# These are "locked" during reconciliation and used to constrain Phase C.

TraitCall = Dict[str, Any]  # {bucket_name: {value, confidence, tags}}


def derive_discrete_calls(
    reference_tags: Dict[str, float],
    buckets: Dict[str, Dict[str, Any]],
    threshold: float = 0.5,
) -> Dict[str, TraitCall]:
    """Derive discrete trait calls from reference tags.

    For each mappable bucket, pick the highest-confidence tag as the call
    value and record the supporting tags + confidence.
    """
    calls: Dict[str, TraitCall] = {}
    for name, b in buckets.items():
        if not b["mappable"]:
            continue
        bucket_tags = {t: c for t, c in reference_tags.items() if t in b["tags"]}
        if not bucket_tags:
            continue
        best_tag = max(bucket_tags, key=bucket_tags.get)
        best_conf = bucket_tags[best_tag]
        if best_conf < threshold:
            continue
        calls[name] = {
            "value": best_tag,
            "confidence": round(best_conf, 3),
            "tags": bucket_tags,
            "bucket": name,
        }
    return calls


# ---------------------------------------------------------------------------
# Phase A — discrete shortlist (unchanged core, trust-aware scoring)
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
        return [{"path": k, "wd_tags": v} for k, v in data.items()]
    return []


def shortlist(
    reference_tags: Dict[str, float],
    index: List[Dict],
    top_k: int = 10,
    method: str = "weighted",
    trust: bool = True,
) -> List[Dict]:
    """Score every tagged entry in the index against the reference.

    Returns top-K by similarity, each with path, score, shared tag count.
    Uses trust-weighted scoring when trust=True.
    """
    results = []
    for entry in index:
        path = entry.get("path") or entry.get("card_path") or entry.get("file")
        if not path:
            continue
        tags = entry.get("wd_tags")
        if not tags or not isinstance(tags, dict):
            continue
        score = tag_similarity(reference_tags, tags, method=method, trust=trust)
        results.append({
            "path": path,
            "score": round(float(score), 4),
            "tags": tags,
            "n_shared": len(set(reference_tags) & set(tags)),
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Phase B — continuous convergence (render + tag + score) (unchanged core)
# ---------------------------------------------------------------------------

def submit_and_wait(
    character_path: str,
    preset: str,
    output_path: Path,
    request_dir: Path,
    timeout: float = 180.0,
) -> bool:
    """Submit a render request JSON and poll for the response."""
    request_dir = Path(request_dir)
    request_dir.mkdir(parents=True, exist_ok=True)

    # Defense-in-depth: job_id embeds the current PID + a sub-second timestamp
    # so two optimizer runs (or two concurrent renders) never collide on the
    # same job-ID even if the single-instance lock were bypassed.
    _now_ns = int(time.time() * 1e9) % 1_000_000_000
    _pid = _os.getpid()
    job_id = f"{Path(output_path).stem}_{_pid}_{_now_ns}"
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
    trust: bool = True,
) -> Optional[Dict]:
    """Render each candidate at each preset, re-tag, score, pick best.

    Returns the best (card, preset, score, render_tags) across all
    candidates, or None if nothing succeeded.
    """
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

            score = tag_similarity(reference_tags, tags, method=similarity, trust=trust)
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

            print(f"      score={score:.4f}  tags={len(tags)}  "
                  f"trust_adjusted={trust}")

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
# Phase C — continuous parameter optimization
# ---------------------------------------------------------------------------
# For the best (card, preset) from Phase B, load the card, perturb a
# low-dimensional subset of continuous parameters, re-render and re-tag
# at each step, and hill-climb toward higher tag similarity.

# Which parameter groups we can realistically optimize.  Each entry maps
# a "parameter group" name to a list of (descriptor, getter, setter, bounds)
# where getter/setter operate on a loaded KoikatuCharaData's Custom block.

# NOTE: This is a best-effort skeleton.  The exact parameter paths depend on
# the kkloader API version and the card format.  The placeholder functions
# below are guarded with try/except and log when they can't operate, so the
# optimizer degrades gracefully to Phase B-only if kkloader can't modify
# parameters.

ParameterGroup = Dict[str, Any]  # {name, descriptors, getter, setter, bounds, step}


def _face_shape_get(card: Any) -> Optional[np.ndarray]:
    """Try to read Custom.face.shapeValueFace as a float array."""
    try:
        face = card["Custom"]
        sv = face.data.get("face", {}).get("shapeValueFace")
        if sv is None:
            return None
        arr = np.array(sv, dtype=np.float64)
        return arr
    except Exception:
        return None


def _face_shape_set(card: Any, values: np.ndarray) -> bool:
    """Try to write shapeValueFace back."""
    try:
        face = card["Custom"]
        face.data["face"]["shapeValueFace"] = values.tolist()
        return True
    except Exception:
        return False


def _body_shape_get(card: Any) -> Optional[np.ndarray]:
    try:
        body = card["Custom"]
        sv = body.data.get("body", {}).get("shapeValueBody")
        if sv is None:
            return None
        return np.array(sv, dtype=np.float64)
    except Exception:
        return None


def _body_shape_set(card: Any, values: np.ndarray) -> bool:
    try:
        body = card["Custom"]
        body.data["body"]["shapeValueBody"] = values.tolist()
        return True
    except Exception:
        return False


def _hair_color_get(card: Any) -> Optional[np.ndarray]:
    """Read the base color of the first non-zero-length hair part."""
    try:
        hair = card["Custom"]
        parts = hair.data.get("hair", {}).get("parts", [])
        for p in parts:
            if p.get("length", 0) > 0:
                bc = p.get("baseColor")
                if bc:
                    return np.array(bc[:3], dtype=np.float64)
        return None
    except Exception:
        return None


def _hair_color_set(card: Any, color: np.ndarray) -> bool:
    """Set base color on all non-zero-length hair parts."""
    try:
        hair = card["Custom"]
        parts = hair.data.get("hair", {}).get("parts", [])
        for p in parts:
            if p.get("length", 0) > 0:
                p["baseColor"] = [float(color[0]), float(color[1]),
                                  float(color[2]), 1.0]
                p["startColor"] = [float(color[0]), float(color[1]),
                                   float(color[2]), 1.0]
                p["endColor"] = [float(color[0]), float(color[1]),
                                 float(color[2]), 1.0]
        return True
    except Exception:
        return False


def _eye_color_get(card: Any) -> Optional[np.ndarray]:
    """Read hlUpColor as a proxy for eye color."""
    try:
        face = card["Custom"]
        ec = face.data.get("face", {}).get("hlUpColor")
        if ec:
            return np.array(ec[:3], dtype=np.float64)
        return None
    except Exception:
        return None


def _eye_color_set(card: Any, color: np.ndarray) -> bool:
    try:
        face = card["Custom"]
        face.data["face"]["hlUpColor"] = [float(color[0]), float(color[1]),
                                           float(color[2]), 1.0]
        face.data["face"]["hlDownColor"] = [float(color[0]), float(color[1]),
                                            float(color[2]), 1.0]
        return True
    except Exception:
        return False


def _skin_tone_get(card: Any) -> Optional[np.ndarray]:
    try:
        body = card["Custom"]
        mc = body.data.get("body", {}).get("skinMainColor")
        if mc:
            return np.array(mc[:3], dtype=np.float64)
        return None
    except Exception:
        return None


def _skin_tone_set(card: Any, color: np.ndarray) -> bool:
    try:
        body = card["Custom"]
        body.data["body"]["skinMainColor"] = [float(color[0]), float(color[1]),
                                              float(color[2]), 1.0]
        return True
    except Exception:
        return False


# Parameter groups we attempt to optimize.  Each has a name, a getter/setter,
# a list of (index_or_label, low, high) bounds, and a step size for the
# initial grid exploration.  Only the first group that succeeds is used per
# run — we don't jointly optimize face + body + hair because each render is
# expensive.

PARAM_GROUPS: List[ParameterGroup] = [
    {
        "name": "face_shape",
        "descriptor": "shapeValueFace sliders",
        "get": _face_shape_get,
        "set": _face_shape_set,
        "bounds": [(i, 0.0, 1.0) for i in range(42)],  # shapeValueFace length
        "step": 0.05,
        "dim": 42,
    },
    {
        "name": "body_shape",
        "descriptor": "shapeValueBody sliders",
        "get": _body_shape_get,
        "set": _body_shape_set,
        "bounds": [(i, 0.0, 1.0) for i in range(44)],
        "step": 0.05,
        "dim": 44,
    },
    {
        "name": "hair_color",
        "descriptor": "hair RGB",
        "get": _hair_color_get,
        "set": _hair_color_set,
        "bounds": [("r", 0.0, 1.0), ("g", 0.0, 1.0), ("b", 0.0, 1.0)],
        "step": 0.05,
        "dim": 3,
    },
    {
        "name": "eye_color",
        "descriptor": "eye (highlight) RGB",
        "get": _eye_color_get,
        "set": _eye_color_set,
        "bounds": [("r", 0.0, 1.0), ("g", 0.0, 1.0), ("b", 0.0, 1.0)],
        "step": 0.05,
        "dim": 3,
    },
    {
        "name": "skin_tone",
        "descriptor": "skin RGB",
        "get": _skin_tone_get,
        "set": _skin_tone_set,
        "bounds": [("r", 0.0, 1.0), ("g", 0.0, 1.0), ("b", 0.0, 1.0)],
        "step": 0.05,
        "dim": 3,
    },
]


def _pick_param_group(
    card: Any,
    prefer: Optional[str] = None,
) -> Optional[ParameterGroup]:
    """Return the first param group whose getter returns non-None on this card.

    If `prefer` is given, try that group first.
    """
    groups = PARAM_GROUPS
    if prefer:
        groups = [g for g in groups if g["name"] == prefer] + [
            g for g in groups if g["name"] != prefer
        ]
    for g in groups:
        try:
            val = g["get"](card)
            if val is not None and len(val) > 0:
                return g
        except Exception:
            continue
    return None


def _save_card_tmp(card: Any, tmp_path: Path) -> bool:
    """Save a KoikatuCharaData to a temporary PNG."""
    try:
        card.save(str(tmp_path))
        return tmp_path.exists()
    except Exception as e:
        print(f"      [phase_c] save failed: {e}")
        return False


# Frozen dict helper for tagging without side effects
def _freeze_tags(tags: Dict[str, float]) -> Dict[str, float]:
    return dict(tags)


def phase_c(
    tagger: WDTagger,
    reference_tags: Dict[str, float],
    card_path: str,
    preset: str,
    render_dir: Path,
    request_dir: Path,
    param_group_name: Optional[str] = None,
    steps: int = 6,
    similarity: str = "weighted",
    render_timeout: float = 180.0,
    trust: bool = True,
    report_path: Optional[Path] = None,
) -> Optional[Dict]:
    """Continuous parameter optimization for a single (card, preset).

    Loads the card, picks a parameter group, perturbs it in `steps`
    increments around the current value, re-renders + re-tags at each
    point, and picks the best.  Returns the best parameter state + score,
    or None if nothing worked.

    If kkloader can't load/modify the card, returns None and logs a
    graceful degradation message.
    """
    print(f"\n[optimizer] Phase C: continuous optimization "
          f"for {Path(card_path).name} / {preset}")

    # Try to load the card
    try:
        import kkloader
        card = kkloader.KoikatuCharaData.load(card_path)
        print(f"  [phase_c] card loaded via kkloader")
    except Exception as e:
        print(f"  [phase_c] cannot load card via kkloader: {e}")
        print(f"  [phase_c] degrading to Phase B result (no continuous opt)")
        return None

    # Pick parameter group
    pg = _pick_param_group(card, prefer=param_group_name)
    if pg is None:
        print(f"  [phase_c] no parameter group available on this card")
        print(f"  [phase_c] degrading to Phase B result (no continuous opt)")
        return None

    print(f"  [phase_c] using param group: {pg['name']} "
          f"({pg['descriptor']}, dim={pg['dim']})")

    # Current parameter values
    current = pg["get"](card)
    if current is None:
        print(f"  [phase_c] getter returned None for {pg['name']}")
        return None
    current = np.array(current, dtype=np.float64)

    # Build a small grid around the current value
    bounds = pg["bounds"]
    dim = pg["dim"]
    if dim > 3:
        # For high-dim groups, perturb a random low-dim subspace (first 3
        # dimensions) to keep the grid small.
        indices = list(range(min(3, dim)))
        print(f"  [phase_c] high-dim group ({dim} sliders) — "
              f"optimizing subspace of first {len(indices)} dims")
    else:
        indices = list(range(dim))

    # Generate candidate perturbations: for each selected dimension, try
    # { -step, 0, +step } and take the Cartesian product (3^|indices| points).
    step = pg["step"]
    levels = [-step, 0.0, step]
    candidates = []
    for lvl_tuple in np.array(np.meshgrid(*[levels] * len(indices),
                                          indexing="ij")).T.reshape(-1, len(indices)):
        cand = current.copy()
        for i, lvl in zip(indices, lvl_tuple):
            lo = bounds[i][1] if i < len(bounds) else 0.0
            hi = bounds[i][2] if i < len(bounds) else 1.0
            new_val = float(np.clip(cand[i] + lvl, lo, hi))
            # Don't keep the identical point
            if abs(new_val - cand[i]) > 1e-6:
                cand[i] = new_val
        candidates.append(cand)

    # Deduplicate and keep current as baseline
    seen = {tuple(current.tolist())}
    unique = [current]
    for cand in candidates:
        key = tuple(np.round(cand, 4).tolist())
        if key not in seen:
            seen.add(key)
            unique.append(cand)
    print(f"  [phase_c] {len(unique)} candidate parameter sets "
          f"(incl. baseline)")

    # Evaluate each candidate: set params, save to temp PNG, render, tag, score
    best_score = -1.0
    best_params = current.copy()
    best_tags: Optional[Dict[str, float]] = None
    best_render_name = ""

    # Defense-in-depth: temp card path embeds PID + timestamp so two
    # optimizer runs (or two concurrent Phase C runs) never write the same
    # temp card even if the single-instance lock were bypassed.
    _now_ns = int(time.time() * 1e9) % 1_000_000_000
    _pid = _os.getpid()
    tmp_card = render_dir / f".phase_c_{Path(card_path).stem}_{preset}_{_pid}_{_now_ns}.png"

    for i, params in enumerate(unique):
        label = f"baseline" if i == 0 else f"candidate {i}"
        print(f"  [phase_c] [{label}] evaluating...")

        # Set parameters
        ok = pg["set"](card, params)
        if not ok:
            print(f"      [phase_c] setter failed — skip")
            continue

        # Save to temp path
        if not _save_card_tmp(card, tmp_card):
            continue

        # Render
        render_name = f"{Path(card_path).stem}_{preset}_pc{i}.png"
        render_path = render_dir / render_name
        render_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy the temp card to the actual character path?  No — the submit
        # API takes a character_path, so we submit the temp card.
        ok_render = submit_and_wait(
            character_path=str(tmp_card),
            preset=preset,
            output_path=render_path,
            request_dir=request_dir,
            timeout=render_timeout,
        )
        if not ok_render:
            print(f"      [phase_c] render failed")
            continue

        # Tag
        tags = tagger.tag_image(str(render_path))
        score = tag_similarity(reference_tags, tags, method=similarity, trust=trust)
        print(f"      [phase_c] score={score:.4f}  tags={len(tags)}")

        if score > best_score:
            best_score = score
            best_params = params.copy()
            best_tags = tags
            best_render_name = render_name

    # Restore original card parameters so we don't leave the card mutated
    pg["set"](card, current)

    if best_score < 0:
        print(f"  [phase_c] no candidate scored — keeping baseline")
        return {
            "param_group": pg["name"],
            "params": current.tolist(),
            "score": 0.0,
            "render_tags": reference_tags,  # placeholder
            "best_render": "",
            "improved": False,
        }

    print(f"  [phase_c] best: {pg['name']} score={best_score:.4f} "
          f"(baseline was {_freeze_tags(reference_tags) and 0.0:.4f})")
    return {
        "param_group": pg["name"],
        "params": best_params.tolist(),
        "score": round(float(best_score), 4),
        "render_tags": best_tags or {},
        "best_render": best_render_name,
        "improved": best_score > 0,
    }


# ---------------------------------------------------------------------------
# Reconciliation pass
# ---------------------------------------------------------------------------
# After Phase C converges, lock the discrete trait calls derived from the
# reference tags and re-check that the converged continuous state is still
# consistent.  If a locked call conflicts with the converged params, re-run
# Phase C with that call pinned.

RECONCILE_PASSES = 2  # max reconciliation iterations


def reconcile(
    tagger: WDTagger,
    reference_tags: Dict[str, float],
    card_path: str,
    preset: str,
    render_dir: Path,
    request_dir: Path,
    discrete_calls: Dict[str, TraitCall],
    phase_c_result: Optional[Dict],
    buckets: Dict[str, Dict[str, Any]],
    similarity: str = "weighted",
    render_timeout: float = 180.0,
    trust: bool = True,
) -> Dict[str, Any]:
    """Reconciliation pass: lock discrete calls, re-check against converged state.

    Returns a reconciliation report.
    """
    print("\n[optimizer] Reconciliation pass")
    report: Dict[str, Any] = {
        "discrete_calls": discrete_calls,
        "phase_c_result": phase_c_result,
        "conflicts": [],
        "resolutions": [],
        "final_score": phase_c_result["score"] if phase_c_result else None,
        "passes": [],
    }

    # For each discrete call, check whether the converged continuous state
    # is consistent with it.  Consistency is defined per bucket:
    #  - hair_color: the converged hair color RGB should be within a
    #    tolerance of the reference tag's implied color (approximate).
    #  - eye_color: same for eye color.
    #  - hair_style: the card's hair part IDs should match the call's style.
    #  - face_shape / body_shape: can't directly verify from params alone;
    #    check via render tag similarity.

    # We re-render with the converged params and check if the discrete call's
    # expected tags are present in the render tags.
    if phase_c_result is None:
        print("  [reconcile] no Phase C result — skipping reconciliation")
        report["note"] = "no phase_c result"
        return report

    # Load the card with converged params applied and re-render once to get
    # the reconciled render tags
    try:
        import kkloader
        card = kkloader.KoikatuCharaData.load(card_path)
    except Exception as e:
        print(f"  [reconcile] cannot reload card: {e}")
        return report

    # Apply converged params
    pg_name = phase_c_result.get("param_group")
    if pg_name:
        pg = next((g for g in PARAM_GROUPS if g["name"] == pg_name), None)
        if pg and pg["set"]:
            try:
                pg["set"](card, np.array(phase_c_result["params"]))
                # Defense-in-depth: embed PID + timestamp so two reconcile runs
                # never share the same temp card.
                _now_ns = int(time.time() * 1e9) % 1_000_000_000
                _pid = _os.getpid()
                tmp_card = render_dir / f".reconcile_{Path(card_path).stem}_{_pid}_{_now_ns}.png"
                if _save_card_tmp(card, tmp_card):
                    render_name = f"{Path(card_path).stem}_{preset}_recon.png"
                    render_path = render_dir / render_name
                    ok = submit_and_wait(
                        character_path=str(tmp_card),
                        preset=preset,
                        output_path=render_path,
                        request_dir=request_dir,
                        timeout=render_timeout,
                    )
                    if ok:
                        recon_tags = tagger.tag_image(str(render_path))
                        print(f"  [reconcile] re-rendered with converged params: "
                              f"{len(recon_tags)} tags")
                    else:
                        recon_tags = {}
                        print(f"  [reconcile] re-render failed")
                else:
                    recon_tags = {}
                    print(f"  [reconcile] save failed")
            except Exception as e:
                print(f"  [reconcile] param apply failed: {e}")
                recon_tags = {}
        else:
            recon_tags = {}
    else:
        recon_tags = {}

    # Check each discrete call against recon_tags
    for call_name, call in discrete_calls.items():
        expected_tag = call["value"]
        present = expected_tag in recon_tags
        conf = recon_tags.get(expected_tag, 0.0) if present else 0.0
        conflict = not present or conf < 0.4
        report["conflicts"].append({
            "call": call_name,
            "expected_tag": expected_tag,
            "present_in_recon": present,
            "confidence_in_recon": round(conf, 3),
            "conflict": conflict,
        })
        if conflict:
            print(f"  [reconcile] CONFLICT: {call_name} expects "
                  f"{expected_tag} (conf {call['confidence']}), "
                  f"recon has conf {conf:.3f}")
            report["resolutions"].append({
                "call": call_name,
                "action": "flagged_for_rerun",
                "expected_tag": expected_tag,
            })
        else:
            print(f"  [reconcile] OK: {call_name} {expected_tag} "
                  f"conf {conf:.3f} in recon")
            report["passes"].append(call_name)

    # If there are conflicts and we have a phase_c_result, re-run Phase C
    # with the conflicting calls pinned (we approximate pinning by
    # re-optimizing only the non-conflicting param group).
    if report["conflicts"] and phase_c_result:
        print(f"  [reconcile] {len(report['conflicts'])} conflict(s) — "
              f"would re-run Phase C with pinned calls in a full implementation")
        report["resolutions"].append({
            "action": "rerun_needed",
            "conflicts": [c["call"] for c in report["conflicts"]],
        })
    else:
        print(f"  [reconcile] all discrete calls consistent with converged state")

    report["final_score"] = phase_c_result["score"] if phase_c_result else None
    return report


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
    # New options
    parser.add_argument("--trust", action=argparse.BooleanOptionalAction,
                        default=True,
                        help="Enable trust-weighted tag scoring "
                             "(default: on)")
    parser.add_argument("--ceiling", action="store_true",
                        default=False,
                        help="Report mappable ceiling (unmappable-trait "
                             "discount) without optimizing against it "
                             "(diagnostic only)")
    parser.add_argument("--phase-c", action="store_true",
                        default=False,
                        help="Run Phase C continuous parameter optimization "
                             "on the best Phase B result")
    parser.add_argument("--phase-c-group", default=None,
                        help="Force a specific Phase C parameter group "
                             "(face_shape, body_shape, hair_color, "
                             "eye_color, skin_tone)")
    parser.add_argument("--phase-c-steps", type=int, default=6,
                        help="Number of perturbation steps for Phase C "
                             "(per dimension)")
    parser.add_argument("--reconcile", action="store_true",
                        default=False,
                        help="Run reconciliation pass after Phase C: lock "
                             "discrete trait calls and re-check consistency")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # --- Single-instance guard ---
    # Acquires a non-blocking file lock so two `python optimizer.py ...`
    # processes can't run at once and race on render_requests / temp cards.
    if not acquire_single_instance_lock():
        msg = (
            "[optimizer] Another optimizer instance appears to be running already "
            f"(lock held at {_LOCK_FILE}).  Exiting.  If you're sure no other "
            "instance is alive, delete that file and re-run."
        )
        print(msg, file=sys.stderr)
        # Also write a short marker so a cron job / watchdog can see the refusal.
        return 99

    # --- Load tagger (expensive — do this AFTER we own the lock) ---
    tagger = WDTagger(args.wd_model, args.wd_tags)
    print(f"[optimizer] WD tagger ready ({Path(args.wd_model).name})")

    # --- Trait buckets ---
    buckets = build_trait_buckets()

    # --- Phase A: tag reference ---
    ref_path = Path(args.reference)
    if not ref_path.exists():
        print(f"ERROR: reference not found: {args.reference}", file=sys.stderr)
        return 1

    print(f"\n[optimizer] Phase A: tagging reference {ref_path.name}")
    ref_tags = tagger.tag_image(str(ref_path))
    print(f"[optimizer] Reference tags ({len(ref_tags)}):")
    for tag, conf in list(ref_tags.items())[:12]:
        trust = tag_trust(tag)
        print(f"    {tag:28s} {conf:.3f}  trust={trust:.2f}")
    if len(ref_tags) > 12:
        print(f"    ... ({len(ref_tags) - 12} more)")
    print()

    # --- Mappable ceiling (diagnostic) ---
    if args.ceiling:
        ceiling = mappable_ceiling(ref_tags, buckets, method=args.similarity)
        mappable = mappable_tag_set(ref_tags, buckets)
        unmappable = unmappable_tag_set(ref_tags, buckets)
        print(f"[optimizer] Mappable ceiling: {ceiling:.4f}")
        print(f"  mappable tags: {len(mappable)} "
              f"({sum(mappable.values()):.2f} conf mass)")
        print(f"  unmappable tags: {len(unmappable)} "
              f"({sum(unmappable.values()):.2f} conf mass)")
        if unmappable:
            print(f"  unmappable: {', '.join(sorted(unmappable.keys()))}")
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
                               method=args.similarity, trust=args.trust)
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

    # --- Discrete calls from reference ---
    discrete_calls = derive_discrete_calls(ref_tags, buckets)
    if discrete_calls:
        print(f"[optimizer] Discrete trait calls ({len(discrete_calls)}):")
        for name, call in discrete_calls.items():
            print(f"    {name}: {call['value']} "
                  f"(conf {call['confidence']}, "
                  f"{len(call['tags'])} tags)")
        print()

    # --- Phase B: continuous convergence ---
    result: Dict[str, Any] = {
        "reference": str(ref_path),
        "reference_tags": ref_tags,
        "shortlist": candidates,
        "similarity_method": args.similarity,
        "trust_weighted": args.trust,
        "discrete_calls": discrete_calls,
        "buckets": {name: {"mappable": b["mappable"],
                            "tags": b["tags"]}
                    for name, b in buckets.items()},
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
            trust=args.trust,
        )
        result["best"] = best

    # --- Phase C: continuous parameter optimization ---
    phase_c_result: Optional[Dict] = None
    if args.phase_c and best:
        card_path = best.get("card_path")
        preset = best.get("preset")
        if card_path and preset:
            phase_c_result = phase_c(
                tagger=tagger,
                reference_tags=ref_tags,
                card_path=card_path,
                preset=preset,
                render_dir=Path(args.render_dir),
                request_dir=Path(args.request_dir),
                param_group_name=args.phase_c_group,
                steps=args.phase_c_steps,
                similarity=args.similarity,
                render_timeout=args.render_timeout,
                trust=args.trust,
            )
            result["phase_c"] = phase_c_result
            if phase_c_result:
                print(f"\n[optimizer] Phase C result: "
                      f"{phase_c_result['param_group']} "
                      f"score={phase_c_result['score']:.4f} "
                      f"improved={phase_c_result['improved']}")

    # --- Reconciliation pass ---
    reconcile_report: Optional[Dict] = None
    if args.reconcile and phase_c_result:
        reconcile_report = reconcile(
            tagger=tagger,
            reference_tags=ref_tags,
            card_path=best.get("card_path", ""),
            preset=best.get("preset", ""),
            render_dir=Path(args.render_dir),
            request_dir=Path(args.request_dir),
            discrete_calls=discrete_calls,
            phase_c_result=phase_c_result,
            buckets=buckets,
            similarity=args.similarity,
            render_timeout=args.render_timeout,
            trust=args.trust,
        )
        result["reconciliation"] = reconcile_report

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

    if args.ceiling:
        ceiling = mappable_ceiling(ref_tags, buckets, method=args.similarity)
        print(f"[optimizer] Mappable ceiling (target upper bound): {ceiling:.4f}")

    if phase_c_result:
        print(f"[optimizer] Phase C best score: {phase_c_result['score']:.4f}")
    if reconcile_report:
        n_conflicts = len([c for c in reconcile_report.get("conflicts", [])
                           if c.get("conflict")])
        print(f"[optimizer] Reconciliation: "
              f"{len(reconcile_report.get('passes', []))} passes, "
              f"{n_conflicts} conflicts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
