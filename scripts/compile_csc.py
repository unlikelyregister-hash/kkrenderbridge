"""Compile KkRenderBridge.cs using the Windows .NET Framework csc.exe."""
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
CSC = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
LIB = WORKSPACE / "lib"
SRC = WORKSPACE / "KkRenderBridge.cs"
OUT = WORKSPACE / "build" / "KkRenderBridge.dll"

REFERENCES = [
    LIB / "BepInEx.dll",
    LIB / "UnityEngine.dll",
    LIB / "KKAPI.dll",
    LIB / "Newtonsoft.Json.dll",
    Path(r"C:\Games\Koikatsu\Koikatu_Data\Managed\Assembly-CSharp.dll"),
]

def main():
    if not CSC.exists():
        print(f"ERROR: csc.exe not found at {CSC}", file=sys.stderr)
        return 1

    for ref in REFERENCES:
        if not ref.exists():
            print(f"ERROR: reference DLL missing: {ref}", file=sys.stderr)
            return 1

    if not SRC.exists():
        print(f"ERROR: source not found: {SRC}", file=sys.stderr)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Build csc command line
    args = [
        str(CSC),
        "/target:library",
        f"/out:{OUT}",
        "/optimize+",
        "/warn:4",
    ]
    for ref in REFERENCES:
        args.append(f"/reference:{ref}")

    # With backslashes in paths on Windows, csc needs forward slashes or quoted paths
    args.append(str(SRC))

    print(f"[build] csc → {OUT}")
    print(f"[build] references: {', '.join(r.name for r in REFERENCES)}")
    print(f"[build] source: {SRC.name}")

    result = subprocess.run(args, capture_output=True, text=True, timeout=60)

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            print(f"  {line}")

    if result.returncode != 0:
        print("[build] FAILED", file=sys.stderr)
        return 1

    if OUT.exists():
        size = OUT.stat().st_size
        print(f"[build] SUCCESS: {OUT} ({size} bytes)")
        # Copy to BepInEx plugins directory
        import shutil
        DEST = Path(r"C:\Games\Koikatsu\BepInEx\plugins\KkRenderBridge.dll")
        shutil.copy2(OUT, DEST)
        print(f"[build] Copied to: {DEST} ({DEST.stat().st_size} bytes)")
        return 0
    else:
        print("[build] ERROR: output DLL not created", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
