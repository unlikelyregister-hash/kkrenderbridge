#!/usr/bin/env python3
"""Quick check: game state, log, renders."""
import os, subprocess

GAME_DIR = "C:/Games/Koikatsu"

# Game
r = subprocess.run(["wmic", "process", "where", "Name='Koikatu.exe'",
    "get", "ProcessId,WorkingSetSize", "/format:list"],
    capture_output=True, text=True, timeout=10)
running = "ProcessId=" in r.stdout
print("GAME:", "RUNNING" if running else "NOT RUNNING")
if running:
    pid = r.stdout.strip().split("ProcessId=")[1].split("\n")[0].strip()
    wss = r.stdout.strip().split("WorkingSetSize=")[1].split("\n")[0].strip()
    print(f"  PID={pid}  WSS={int(wss):,} bytes")

# Log
log = os.path.join(GAME_DIR, "BepInEx", "LogOutput.log")
if os.path.exists(log):
    lines = open(log).readlines()
    print(f"\nLOG: {len(lines)} lines")
    for l in lines:
        if any(k in l for k in ["KkRenderBridge", "Intro", "Chainloader", "error", "Error"]):
            print(f"  {l.rstrip()}")

# Renders
print("\nRENDERS (marta*):")
for f in sorted(os.listdir("C:/Users/Administrator/kk-workspace/renders")):
    if "marta" in f.lower():
        path = os.path.join("C:/Users/Administrator/kk-workspace/renders", f)
        print(f"  {f:30s} {os.path.getsize(path):>10,d} bytes")
