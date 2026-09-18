#!/usr/bin/env python3
"""Check game state and submit render if ready."""
import os, subprocess, json, time

GAME_DIR = r"C:\Games\Koikatsu"
RENDER_DIR = r"C:\Users\Administrator\kk-workspace\renders"
LOG = os.path.join(GAME_DIR, "BepInEx", "LogOutput.log")

# 1. Check game is running
result = subprocess.run(["wmic", "process", "where", "Name='Koikatu.exe'",
    "get", "ProcessId,WorkingSetSize", "/format:list"],
    capture_output=True, text=True, timeout=10)
running = "ProcessId=" in result.stdout
print(f"Game running: {running}")
if running:
    print(result.stdout.strip()[:200])

# 2. Check log for plugin status
if os.path.exists(LOG):
    lines = open(LOG).readlines()
    print(f"Log lines: {len(lines)}")
    kkr_lines = [l.strip() for l in lines if "KkRenderBridge" in l]
    print(f"KkRenderBridge log lines: {len(kkr_lines)}")
    for l in kkr_lines[-3:]:
        print(f"  {l}")
    
    err_lines = [l.strip() for l in lines if "op_Inequality" in l or "method not found" in l.lower()]
    if err_lines:
        print(f"ERRORS FOUND: {len(err_lines)}")
        for l in err_lines:
            print(f"  {l}")

# 3. Check for existing v3 response
v3_resp = os.path.join(GAME_DIR, "render_requests", "marta_kkpe_v3.json.response.json")
if os.path.exists(v3_resp):
    print(f"\nV3 response exists:")
    print(open(v3_resp).read().strip())

# 4. Check if Character Maker is open by looking for Maker state file
maker_state = os.path.join(GAME_DIR, "UserData", "MakerState.json")
if os.path.exists(maker_state):
    print("\nMakerState.json exists - Character Maker is open")
    data = json.loads(open(maker_state).read())
    loaded = data.get("loadedChara", "unknown")
    print(f"  Loaded character: {loaded}")
else:
    print("\nNo MakerState.json - Character Maker not confirmed open")

# 5. Check current request file
v3_req = os.path.join(GAME_DIR, "render_requests", "marta_kkpe_v3.json")
if os.path.exists(v3_req):
    print(f"\nV3 request file:")
    print(open(v3_req).read().strip())
