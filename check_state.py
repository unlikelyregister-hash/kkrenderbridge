#!/usr/bin/env python3
"""Check game state cleanly."""
import os, subprocess

GAME_DIR = "C:/Games/Koikatsu"
LOG = os.path.join(GAME_DIR, "BepInEx", "LogOutput.log")

# Game status
r = subprocess.run(["wmic", "process", "where", "Name='Koikatu.exe'",
    "get", "ProcessId,WorkingSetSize", "/format:list"],
    capture_output=True, text=True, timeout=10)
print("GAME:", "RUNNING" if "ProcessId=" in r.stdout else "NOT RUNNING")
if "ProcessId=" in r.stdout:
    print(r.stdout.strip()[:300])

# Log
if os.path.exists(LOG):
    lines = open(LOG).readlines()
    print(f"\nLOG LINES: {len(lines)}")
    kkr = [l.strip() for l in lines if "KkRenderBridge" in l]
    print(f"KkRenderBridge entries: {len(kkr)}")
    for l in kkr[-3:]:
        print(f"  {l}")
    errs = [l.strip() for l in lines if "op_Inequality" in l or "method not found" in l.lower()]
    if errs:
        print(f"\nERRORS ({len(errs)}):")
        for l in errs:
            print(f"  {l}")

# Renders
print("\nRENDERS:")
for f in sorted(os.listdir("C:/Users/Administrator/kk-workspace/renders")):
    if "marta" in f.lower():
        path = os.path.join("C:/Users/Administrator/kk-workspace/renders", f)
        print(f"  {f} ({os.path.getsize(path)} bytes)")
