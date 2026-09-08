#!/usr/bin/env python3
"""
kk_determinism_check.py

Render the same character card twice through the KkRenderBridge plugin
and diff the two screenshots pixel-by-pixel.

This validates the "deterministic render" assumption: if rendering the same
card twice under the same preset produces meaningfully different images,
the downstream similarity scoring and optimizer will be corrupted by noise.

Usage:
    python kk_determinism_check.py KK_398582.png --preset front --output renders/det_test

This writes:
    renders/det_test_run1.png
    renders/det_test_run2.png
    renders/det_test_diff.png       (visual diff, red = different pixels)
    renders/det_test_report.json    (numeric metrics)

Requirements:
    - Koikatsu running with BepInEx + KKAPI + KkRenderBridge plugin
    - render_requests/ and renders/ directories exist
"""
import argparse
import json
import sys
import time
from pathlib import Path

try:
    from PIL import Image, ImageChops
except ImportError:
    print("ERROR: Pillow required. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# Local imports
sys.path.insert(0, str(Path(__file__).parent))
# Import submit_job from kk-submit-render.py (hyphenated filename)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "kk_submit_render",
    Path(__file__).parent / "kk-submit-render.py",
)
kk_submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kk_submit)
submit_job = kk_submit.submit_job


def render_twice(card_path: Path, preset: str, output_stem: Path) -> tuple[Path, Path]:
    """Submit two render jobs for the same card and wait for both to complete."""
    out1 = output_stem.parent / f"{output_stem.name}_run1.png"
    out2 = output_stem.parent / f"{output_stem.name}_run2.png"
    # The plugin watches the GAME directory, not the workspace
    req_dir = Path(r"C:\Games\Koikatsu\render_requests")
    req1 = req_dir / f"{out1.stem}.json"
    req2 = req_dir / f"{out2.stem}.json"
    resp1 = req_dir / f"{out1.stem}.response.json"
    resp2 = req_dir / f"{out2.stem}.response.json"

    print(f"[det] Submitting run 1 → {out1}")
    submit_job(card_path, preset, out1, req_dir)

    print(f"[det] Submitting run 2 → {out2}")
    submit_job(card_path, preset, out2, req_dir)

    # Wait for both to complete by polling for response files
    timeout = 120  # seconds
    start = time.time()
    done = 0

    print(f"[det] Waiting for both renders to complete (timeout: {timeout}s)...")
    while done < 2 and (time.time() - start) < timeout:
        if resp1.exists() and not hasattr(render_twice, '_seen1'):
            render_twice._seen1 = True
            done += 1
            print(f"  ✓ Run 1 complete")
        if resp2.exists() and not hasattr(render_twice, '_seen2'):
            render_twice._seen2 = True
            done += 1
            print(f"  ✓ Run 2 complete")
        if done < 2:
            time.sleep(1)

    # Clean up sentinel attrs
    render_twice._seen1 = False
    render_twice._seen2 = False

    if done < 2:
        print(f"[det] ERROR: timeout waiting for renders (got {done}/2)", file=sys.stderr)
        return None, None

    if not out1.exists():
        print(f"[det] ERROR: run 1 output not found: {out1}", file=sys.stderr)
        return None, None
    if not out2.exists():
        print(f"[det] ERROR: run 2 output not found: {out2}", file=sys.stderr)
        return None, None

    return out1, out2


def compute_diff(img1_path: Path, img2_path: Path, diff_path: Path) -> dict:
    """Pixel-diff two images and return metrics."""
    img1 = Image.open(img1_path).convert("RGBA")
    img2 = Image.open(img2_path).convert("RGBA")

    if img1.size != img2.size:
        return {
            "error": f"size mismatch: {img1.size} vs {img2.size}",
        }

    # Compute pixel difference
    diff = ImageChops.difference(img1, img2)

    # Save visual diff (amplified for visibility)
    # Multiply differences by 4 for visibility in the diff image
    diff_data = diff.load()
    w, h = diff.size
    amp = Image.new("RGBA", (w, h))
    amp_data = amp.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = diff_data[x, y]
            # Scale up differences; clamp at 255
            amp_data[x, y] = (
                min(r * 4, 255),
                min(g * 4, 255),
                min(b * 4, 255),
                255 if (r + g + b) > 0 else 0,
            )
    amp.save(diff_path)

    # Compute metrics
    total_pixels = w * h
    diff_pixels = 0
    max_diff = 0
    sum_diff = 0

    for y in range(h):
        for x in range(w):
            r, g, b, a = diff_data[x, y]
            d = r + g + b  # 0-765
            if d > 0:
                diff_pixels += 1
            if d > max_diff:
                max_diff = d
            sum_diff += d

    avg_diff = sum_diff / total_pixels if total_pixels > 0 else 0
    pct_diff = (diff_pixels / total_pixels) * 100 if total_pixels > 0 else 0

    return {
        "image1": str(img1_path),
        "image2": str(img2_path),
        "diff_image": str(diff_path),
        "size": [w, h],
        "total_pixels": total_pixels,
        "different_pixels": diff_pixels,
        "pct_different": round(pct_diff, 4),
        "max_channel_diff": max_diff,        # 0-765
        "avg_channel_diff": round(avg_diff, 4),  # 0-765
        "mean_squared_error": round(sum_diff / (total_pixels * 3), 4),  # per-channel MSE
    }


def interpret_results(metrics: dict) -> str:
    """Give a human-readable verdict on the diff results."""
    if "error" in metrics:
        return f"ERROR: {metrics['error']}"

    pct = metrics["pct_different"]
    avg = metrics["avg_channel_diff"]

    # Thresholds (tune based on empirical results):
    #   < 0.01% different pixels, avg diff < 1.0 → essentially deterministic
    #   < 0.1% different, avg < 3.0 → likely OK (minor AA/dithering)
    #   > 0.1% different or avg > 3.0 → POTENTIAL NON-DETERMINISM

    if pct < 0.001 and avg < 0.5:
        return (
            f"✓ DETERMINISTIC: {pct}% pixels differ (avg diff {avg}/765). "
            f"Near-perfect match — any differences are sub-pixel noise."
        )
    elif pct < 0.1 and avg < 3.0:
        return (
            f"~ MINOR VARIATION: {pct}% pixels differ (avg diff {avg}/765). "
            f"Likely anti-aliasing or dithering noise. Acceptable for most uses, "
            f"but monitor if it grows."
        )
    else:
        return (
            f"✗ NON-DETERMINISTIC: {pct}% pixels differ (avg diff {avg}/765). "
            f"This level of variation will corrupt similarity scoring and optimizer "
            f"convergence. Investigate camera/lighting stability before proceeding."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card", type=Path, help="Path to a .png character card")
    parser.add_argument("--preset", choices=["front", "3quarter"], default="front")
    parser.add_argument("--output", type=Path, default=Path("renders/det_test"),
                        help="Output stem (two runs + diff + report will be derived from this)")
    parser.add_argument("--wait", type=int, default=120,
                        help="Max seconds to wait for both renders (default: 120)")
    args = parser.parse_args()

    if not args.card.exists():
        print(f"ERROR: card not found: {args.card}", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[det] Card: {args.card}")
    print(f"[det] Preset: {args.preset}")
    print(f"[det] Output stem: {args.output}")
    print()

    # Step 1: Render twice
    run1, run2 = render_twice(args.card, args.preset, args.output)
    if run1 is None or run2 is None:
        sys.exit(1)

    print()
    print(f"  Run 1: {run1} ({run1.stat().st_size} bytes)")
    print(f"  Run 2: {run2} ({run2.stat().st_size} bytes)")
    print()

    # Step 2: Diff
    diff_path = args.output.parent / f"{args.output.stem}_diff.png"
    report_path = args.output.parent / f"{args.output.stem}_report.json"

    print("[det] Computing pixel diff...")
    metrics = compute_diff(run1, run2, diff_path)
    print()

    # Save report
    report_path.write_text(json.dumps(metrics, indent=2, default=str))
    print(f"[det] Report: {report_path}")
    print(f"[det] Diff image: {diff_path}")
    print()

    # Step 3: Interpret
    verdict = interpret_results(metrics)
    print("=" * 60)
    print(f"  {verdict}")
    print("=" * 60)

    # Exit code: 0 if deterministic enough, 1 if not
    if metrics.get("pct_different", 999) > 0.1 or metrics.get("avg_channel_diff", 999) > 3.0:
        sys.exit(1)


if __name__ == "__main__":
    main()
