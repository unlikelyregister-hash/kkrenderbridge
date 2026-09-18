#!/usr/bin/env python3
"""
Game manager — single-instance lifecycle for Koikatsu.

Ensures only one Koikatu.exe runs at a time.  If the game is already running
and we need it in Character Maker, we save (if needed) and restart.

Uses wmic/process listing for process detection and taskkill for shutdown.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ── configurable paths ──────────────────────────────────────────────────────
GAME_DIR = Path(r"C:\Games\Koikatsu")
GAME_EXE = GAME_DIR / "Koikatu.exe"
LOG_OUTPUT = GAME_DIR / "Koikatu_Data" / "output_log.txt"
BEPINEX_LOG = GAME_DIR / "BepInEx" / "LogOutput.log"

# How long to wait after launch before checking for scene load
LAUNCH_WAIT = 8  # seconds

# How long to wait for the scene to load after the game process appears
SCENE_TIMEOUT = 120  # seconds

# How long to wait for BepInEx plugin to load
PLUGIN_TIMEOUT = 60  # seconds


# ── process detection ───────────────────────────────────────────────────────

def _run_wmic(query: str) -> str:
    """Run a wmic command and return stdout.  Empty string on failure."""
    try:
        r = subprocess.run(
            ["wmic", "process", "where", query, "get", "ProcessId,Commandline",
             "/format:list"],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout
    except Exception:
        return ""


def is_game_running() -> bool:
    """True if any Koikatu.exe process exists."""
    out = _run_wmic("Name='Koikatu.exe'")
    return "ProcessId=" in out


def get_game_pids() -> list[int]:
    """Return PIDs of all running Koikatu.exe processes."""
    pids = []
    out = _run_wmic("Name='Koikatu.exe'")
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("ProcessId="):
            try:
                pids.append(int(line.split("=", 1)[1]))
            except ValueError:
                pass
    return pids


def get_game_pid() -> Optional[int]:
    """Return the first Koikatu.exe PID, or None."""
    pids = get_game_pids()
    return pids[0] if pids else None


# ── shutdown ────────────────────────────────────────────────────────────────

def save_and_close(timeout: float = 30.0) -> bool:
    """Ask the game to save and close, then kill if it doesn't exit.

    Returns True if the game exited cleanly, False if we had to kill it.
    """
    pid = get_game_pid()
    if pid is None:
        return True  # nothing to do

    print(f"[game] Game running (PID {pid}) — requesting close...")
    # Try graceful close via taskkill WITHOUT force first
    try:
        subprocess.run(
            ["taskkill", "/IM", "Koikatu.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass

    # Wait for it to exit
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not is_game_running():
            print("[game] Game exited cleanly")
            return True
        time.sleep(1)

    # Force kill
    print("[game] Graceful close timed out — force killing")
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "Koikatu.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass
    time.sleep(2)
    return not is_game_running()


def kill_game() -> bool:
    """Force-kill any running Koikatu.exe.  Returns True if none remain."""
    if not is_game_running():
        return True
    print("[game] Force-killing Koikatu.exe")
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "Koikatu.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass
    time.sleep(2)
    return not is_game_running()


# ── launch ──────────────────────────────────────────────────────────────────

def launch() -> Optional[int]:
    """Launch Koikatsu.  Returns the PID, or None on failure."""
    if not GAME_EXE.exists():
        print(f"[game] ERROR: game executable not found: {GAME_EXE}")
        return None

    # Ensure no stale instance
    if is_game_running():
        print("[game] Game already running — not launching a second instance")
        return get_game_pid()

    print(f"[game] Launching {GAME_EXE} ...")
    try:
        proc = subprocess.Popen(
            [str(GAME_EXE)],
            cwd=str(GAME_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        print(f"[game] PID: {proc.pid}")
        return proc.pid
    except Exception as e:
        print(f"[game] Launch failed: {e}")
        return None


# ── scene detection ─────────────────────────────────────────────────────────

def _tail_log(n: int = 10) -> list[str]:
    """Return the last n lines of the game's output_log.txt."""
    if not LOG_OUTPUT.exists():
        return []
    try:
        lines = LOG_OUTPUT.read_text(errors="replace").splitlines()
        return lines[-n:]
    except Exception:
        return []


def wait_for_scene(timeout: float = SCENE_TIMEOUT) -> bool:
    """Wait until the game's output_log.txt mentions scene loading.

    Returns True when a scene-loaded line appears, False on timeout.
    """
    print(f"[game] Waiting for scene load (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        lines = _tail_log(20)
        for line in lines:
            low = line.lower()
            if "sceneloaded" in low or "scene loaded" in low:
                print(f"[game] Scene loaded detected")
                return True
            if "character maker" in low or "charactermaker" in low:
                print(f"[game] Character Maker detected in log")
                return True
        time.sleep(2)

    # Final check — maybe it loaded in between polls
    lines = _tail_log(50)
    for line in lines:
        low = line.lower()
        if "sceneloaded" in low or "character maker" in low:
            print(f"[game] Scene loaded (detected late)")
            return True

    print(f"[game] TIMEOUT waiting for scene")
    return False


def wait_for_plugin(timeout: float = PLUGIN_TIMEOUT) -> bool:
    """Wait until KkRenderBridge logs its 'watching' message."""
    if not BEPINEX_LOG.exists():
        print("[game] BepInEx log not found — plugin may not be installed")
        return False

    print(f"[game] Waiting for KkRenderBridge plugin (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        lines = _tail_log(20)
        for line in lines:
            if "KkRenderBridge" in line and "watching" in line.lower():
                print(f"[game] Plugin ready")
                return True
        time.sleep(1)

    print("[game] Plugin may not have loaded yet")
    return False


# ── full lifecycle ──────────────────────────────────────────────────────────

class GameSession:
    """Manage a single Koikatsu session.

    Usage::

        sess = GameSession()
        sess.ensure_character_maker()   # launches / restarts as needed
        # ... do UI automation ...
        sess.close()                     # save and close
    """

    def __init__(
        self,
        game_dir: Path = GAME_DIR,
        auto_close_existing: bool = True,
    ):
        self.game_dir = game_dir
        self.game_exe = game_dir / "Koikatu.exe"
        self.log_output = game_dir / "Koikatu_Data" / "output_log.txt"
        self.bepinex_log = game_dir / "BepInEx" / "LogOutput.log"
        self.auto_close_existing = auto_close_existing
        self.launched = False

    # ── properties ────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return is_game_running()

    @property
    def pid(self) -> Optional[int]:
        return get_game_pid()

    # ── lifecycle ─────────────────────────────────────────────────────────

    def close(self, timeout: float = 30.0) -> bool:
        """Save-and-close the game if running."""
        if not self.is_running:
            return True
        return save_and_close(timeout)

    def kill(self) -> bool:
        """Force-kill the game if running."""
        if not self.is_running:
            return True
        return kill_game()

    def launch(self) -> Optional[int]:
        """Launch the game.  Returns PID or None."""
        if self.is_running:
            print("[game] Already running, PID", self.pid)
            return self.pid
        self.kill()  # ensure clean slate
        time.sleep(1)
        pid = launch()
        if pid:
            self.launched = True
        return pid

    def ensure_character_maker(
        self,
        launch_timeout: float = SCENE_TIMEOUT,
        plugin_timeout: float = PLUGIN_TIMEOUT,
    ) -> bool:
        """Ensure the game is running and in (or loading into) Character Maker.

        If the game is already running, leave it alone.  If not, launch it
        and wait for scene load.

        Returns True if the game is running and we detected scene load,
        False on timeout.
        """
        if self.is_running:
            print(f"[game] Game already running (PID {self.pid})")
            # If the game is in any scene other than Character Maker,
            # we need to save-and-restart to get there.
            # The current scene name appears in the log as e.g.
            #   "Loading scene: clubxxx"  or  "Scene was loaded: charactermaker"
            log = self.log_output
            if log.exists():
                try:
                    tail = log.read_text(errors="replace").splitlines()[-30:]
                    joined = "\n".join(tail).lower()
                    if "charactermaker" not in joined and "character maker" not in joined:
                        print("[game] Game running but NOT in Character Maker — saving and restarting")
                        self.close(timeout=15.0)
                        time.sleep(2)
                        pid = self.launch()
                        if pid is None:
                            return False
                        time.sleep(LAUNCH_WAIT)
                        return wait_for_scene(launch_timeout)
                except Exception:
                    pass
            # If we can't read the log, just wait — maybe it's still loading
            return wait_for_scene(launch_timeout)

        # Close any stragglers
        if self.auto_close_existing:
            self.kill()

        pid = self.launch()
        if pid is None:
            return False

        time.sleep(LAUNCH_WAIT)
        return wait_for_scene(launch_timeout)


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Koikatsu game manager")
    ap.add_argument("--close", action="store_true", help="Save-and-close the game")
    ap.add_argument("--kill", action="store_true", help="Force-kill the game")
    ap.add_argument("--launch", action="store_true", help="Launch the game")
    ap.add_argument("--status", action="store_true", help="Print running state")
    ap.add_argument("--ensure-cm", action="store_true",
                    help="Launch + wait for Character Maker scene")
    args = ap.parse_args()

    sess = GameSession()

    if args.status:
        print(f"Running: {sess.is_running}")
        print(f"PID:     {sess.pid}")
        if sess.is_running:
            print(f"Exe:     {sess.game_exe}")
        sys.exit(0)

    if args.close:
        ok = sess.close()
        print(f"Closed: {ok}")
        sys.exit(0 if ok else 1)

    if args.kill:
        ok = sess.kill()
        print(f"Killed: {ok}")
        sys.exit(0 if ok else 1)

    if args.launch:
        pid = sess.launch()
        print(f"Launched PID: {pid}")
        sys.exit(0 if pid else 1)

    if args.ensure_cm:
        ok = sess.ensure_character_maker()
        print(f"CM ready: {ok}")
        sys.exit(0 if ok else 1)

    print("Nothing to do — use --status, --close, --kill, --launch, or --ensure-cm")
    sys.exit(0)
