#!/usr/bin/env python3
"""Fix the double-backslash issue in KkRenderBridge.cs and rebuild."""
from pathlib import Path

src_path = Path("KkRenderBridge.cs")
with open(src_path, "r", encoding="utf-8") as f:
    src = f.read()

# Fix the problematic escaped backslash in comment
before = src
src = src.replace("---\\\n", "----\n")
src = src.replace("---\\\\", "----")

with open(src_path, "w", encoding="utf-8") as f:
    f.write(src)

if before != src:
    print("Fixed double-backslash in comment")
else:
    print("No changes needed")

# Rebuild
import subprocess, sys
result = subprocess.run(
    [sys.executable, "scripts/compile_csc.py"],
    capture_output=True, text=True, timeout=60
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])
print(f"Exit code: {result.returncode}")
