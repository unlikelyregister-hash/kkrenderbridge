#!/usr/bin/env python3
import os, subprocess, pathlib

game_log = pathlib.Path(r"C:\Games\Koikatsu\BepInEx\LogOutput.log")
print("=== Game log tail ===")
if game_log.exists():
    lines = game_log.read_text(encoding='utf-8', errors='replace').splitlines()
    for l in lines[-15:]:
        print(l)
else:
    print("Log not found")

print("\n=== Game process ===")
r = subprocess.run(["wmic", "process", "where", "Name='Koikatu.exe'", "get", "ProcessId,WorkingSetSize", "/format:list"],
                   capture_output=True, text=True)
print(r.stdout or "Not running")

print("\n=== Renders dir ===")
rd = pathlib.Path("C:/Users/Administrator/kk-workspace/renders")
if rd.exists():
    for f in sorted(rd.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        print(f"  {f.name}  {f.stat().st_size:>10d} bytes  mtime={f.stat().st_mtime}")

print("\n=== .kkpe files ===")
for p in pathlib.Path("C:/Users/Administrator/kk-workspace").glob("*.kkpe"):
    print(f"  {p.name}  {p.stat().st_size} bytes")

print("\n=== Deploy check ===")
deploy_share = pathlib.Path(r"C:\Games\Koikatsu\UserData\Share\MartaLorente_Inspired.kkpe")
deploy_chara = pathlib.Path(r"C:\Games\Koikatsu\UserData\chara\female\kkrenderbridge\MartaLorente_Inspired.kkpe")
for p, label in [(deploy_share, "Share"), (deploy_chara, "kkrenderbridge")]:
    if p.exists():
        print(f"  {label}: {p.stat().st_size} bytes  OK")
    else:
        print(f"  {label}: MISSING")
