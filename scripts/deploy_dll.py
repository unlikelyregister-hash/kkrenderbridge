#!/usr/bin/env python
"""Deploy KkRenderBridge.dll to the game's BepInEx/plugins directory.

Uses Win32 CreateFile/WriteFile to overwrite the DLL even when Koikatsu
has the old file open (shutil.copy2 fails with OSError 22 in that case).
"""
import ctypes
import sys
from pathlib import Path

src = Path(__file__).parent.parent / "build" / "KkRenderBridge.dll"
dst = Path(r"C:\Games\Koikatsu\BepInEx\plugins\KkRenderBridge.dll")

if not src.exists():
    print(f"ERROR: source not found: {src}")
    sys.exit(1)

# Backup old DLL (shutil works for reading a file we don't have open)
backup = dst.with_suffix(".dll.bak")
if dst.exists() and dst.stat().st_size != src.stat().st_size:
    print(f"Backing up old DLL → {backup}")
    import shutil
    shutil.copy2(dst, backup)

print(f"Deploying {src.stat().st_size} bytes → {dst}")

# Win32 overwrite — works even when the target is open by another process
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_WRITE = 0x00000002
CREATE_ALWAYS = 2

h = kernel32.CreateFileW(
    str(dst), GENERIC_WRITE, FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
)
if h == ctypes.c_void_p(-1).value or h == 0:
    # Fall back to CREATE_ALWAYS if OPEN_EXISTING fails (e.g. file was deleted)
    h = kernel32.CreateFileW(
        str(dst), GENERIC_WRITE, 0, None, CREATE_ALWAYS, 0, None
    )
    if h == ctypes.c_void_p(-1).value or h == 0:
        import os
        print(f"ERROR: cannot open {dst}: {os.strerror(ctypes.get_last_error())}")
        sys.exit(1)

with open(src, "rb") as f:
    data = f.read()

written = ctypes.c_ulong(0)
ok = kernel32.WriteFile(h, data, len(data), ctypes.byref(written), None)
kernel32.CloseHandle(h)
if not ok:
    import os
    print(f"ERROR: write failed: {os.strerror(ctypes.get_last_error())}")
    sys.exit(1)

print(f"Wrote {written.value} bytes → {dst}")
print("Done.")
