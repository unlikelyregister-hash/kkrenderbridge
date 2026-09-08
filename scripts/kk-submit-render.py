#!/usr/bin/env python3
"""
kk-submit-render.py

Submit a render job to the KkRenderBridge plugin via the file-based protocol.

The plugin polls render_requests/ for *.json files; this script writes one
and the plugin picks it up and renders it in-game.

Usage:
    python kk-submit-render.py <character_card.png> --preset front --output renders/job1.png
    python kk-submit-render.py modified_eye_color.png --preset 3quarter --output renders/eye_test.png

The job ID is derived from the output filename. The request file will be:
    render_requests/<job_id>.json
and the response will appear at:
    render_requests/<job_id>.response.json
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def submit_job(
    character_path: Path,
    camera_preset: str,
    output_path: Path,
    request_dir: Path,
) -> Path:
    """Write a render request JSON file and return its path."""
    # Normalize MSYS/Cygwin/batch path forms into a real Windows path.
    # MSYS python turns "/c/foo" into "\\c\\foo" (str(Path)) or "C:\\c\\foo"
    # (post-resolve).  Both are wrong — we need "C:\\foo".
    def _win(path: Path) -> Path:
        s = str(path)
        # Form A: X:\c\foo  (post-resolve MSYS drive-letter doubling)
        #   s[1] == ':'  →  real drive is s[0]
        # Form B: \c\foo or /c/foo  (pre-resolve, from bash Path constructor)
        #   s[1] != ':'  →  real drive is s[1] (or s[0] for /c/)
        if len(s) >= 2 and s[1] == ':':
            # Form A: "C:\c\Games\..."  →  real drive is s[0]
            real_drive = s[0].upper()
            rest = s[3:].lstrip('/').replace('/', '\\')
        else:
            # Form B: "\\c\Games\..." or "/c/Games/..."
            # real drive letter is at index 1 (backslash) or index 0 (slash)
            real_drive = s[1].upper() if s[0] == '\\' else s[0].upper()
            rest = s[2:].lstrip('/').replace('/', '\\')
        return Path(f"{real_drive}:\\{rest}")

    cpath = _win(character_path.resolve())
    opath = _win(Path(output_path).resolve())
    rdir  = _win(request_dir.resolve())

    request_dir.mkdir(parents=True, exist_ok=True)

    # Job ID from output filename stem
    job_id = Path(output_path).stem
    request_path = rdir / f"{job_id}.json"
    response_path = rdir / f"{job_id}.response.json"

    # Don't overwrite an existing request unless the response already exists
    if request_path.exists() and not response_path.exists():
        print(f"[submit] WARNING: {request_path} already exists and has no response yet — skipping", file=sys.stderr)
        sys.exit(1)

    # If there's a stale response, clean it up
    if response_path.exists():
        response_path.unlink()
        print(f"[submit] removed stale response: {response_path}")

    req = {
        "character_path": str(cpath),
        "camera_preset": camera_preset,
        "output_path": str(opath),
    }

    request_path.write_text(json.dumps(req, indent=2))
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Submitted render job '{job_id}'")
    print(f"  request: {request_path}")
    print(f"  character: {cpath}")
    print(f"  preset:   {camera_preset}")
    print(f"  output:   {opath}")
    print(f"  (plugin will render this in-game — check logs for response)")

    return request_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "character_card",
        type=Path,
        help="Path to a .png Koikatsu character card (modified by kk_param_roundtrip_test.py)",
    )
    parser.add_argument(
        "--preset",
        choices=["front", "3quarter"],
        default="front",
        help="Camera preset to use (default: front)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("renders/render_out.png"),
        help="Where the plugin should write the screenshot (default: renders/render_out.png)",
    )
    parser.add_argument(
        "--request-dir",
        type=Path,
        default=Path("render_requests"),
        help="Directory the plugin watches (default: ./render_requests)",
    )
    args = parser.parse_args()

    # Normalize MSYS/batch paths before existence check.
    # (Same logic as submit_job's _win below.)
    def _win(path: Path) -> Path:
        s = str(path)
        # Form A: X:\c\foo  (post-resolve MSYS drive-letter doubling)
        if len(s) >= 2 and s[1] == ':':
            real_drive = s[0].upper()
            rest = s[3:].lstrip('/').replace('/', '\\')
        else:
            # Form B: \c\foo or /c/foo
            real_drive = s[1].upper() if s[0] == '\\' else s[0].upper()
            rest = s[2:].lstrip('/').replace('/', '\\')
        return Path(f"{real_drive}:\\{rest}")

    cc = _win(args.character_card)
    if not cc.exists():
        print(f"ERROR: character card not found: {args.character_card}", file=sys.stderr)
        sys.exit(1)

    submit_job(
        character_path=cc,
        camera_preset=args.preset,
        output_path=args.output,
        request_dir=args.request_dir,
    )


if __name__ == "__main__":
    main()
