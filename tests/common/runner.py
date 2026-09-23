"""Host Test Runner CLI & Subprocess Manager.

Runs Blender in background mode to execute tests, parse results,
and display structured summaries.
"""
import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import tempfile
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
EXECUTOR_SCRIPT = WORKSPACE / "tests" / "common" / "blender_executor.py"

from tests.common.character_resolver import (
    resolve_character_dir,
    list_characters,
    GAME_FOLDERS,
)

DEFAULT_BLENDER_CANDIDATES = [
    r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
    r"D:\GOOENGINE\goo-engine-4.4.3-windows+8ab20b9\blender.exe",
    r"D:\goo-engine-4.4.3-windows+8ab20b9\blender.exe",
]


def find_default_blender():
    """Find a default blender executable if not specified by the user."""
    env_blender = os.environ.get("BLENDER_EXE")
    if env_blender and Path(env_blender).is_file():
        return env_blender

    for cand in DEFAULT_BLENDER_CANDIDATES:
        if Path(cand).is_file():
            return cand

    which_blender = shutil.which("blender")
    if which_blender:
        return which_blender

    return None


def run_suite_on_character(blender_exe, suite, game, char_dir, save_blend=False, verbose=False):
    """Run a single suite test on a character using Blender subprocess."""
    char_name = Path(char_dir).name
    temp_dir = Path(tempfile.mkdtemp(prefix=f"test_{suite}_{game}_{char_name}_"))
    output_json = temp_dir / "result.json"
    save_blend_path = str(temp_dir / f"{char_name}_{suite}.blend") if save_blend else ""

    extra_args = {
        "save_blend_path": save_blend_path,
        "verbose": verbose,
    }

    cmd = [
        str(blender_exe),
        "--background",
        "--python",
        str(EXECUTOR_SCRIPT),
        "--",
        suite,
        game,
        str(char_dir),
        str(output_json),
        json.dumps(extra_args),
    ]

    start_time = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(WORKSPACE),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.time() - start_time

    if verbose or proc.returncode != 0 and not output_json.is_file():
        print(f"\n--- [BLENDER LOG for {char_name}] ---")
        print(proc.stdout)
        print("--- [END BLENDER LOG] ---\n")

    if output_json.is_file():
        try:
            result = json.loads(output_json.read_text(encoding="utf-8"))
            result["elapsed_seconds"] = elapsed
            result["blender_returncode"] = proc.returncode
            if save_blend:
                result["saved_blend"] = save_blend_path
            return result
        except Exception as e:
            return {
                "status": "FAIL",
                "character_name": char_name,
                "character_dir": str(char_dir),
                "suite": suite,
                "game": game,
                "error": f"Failed to parse result JSON: {e}",
                "elapsed_seconds": elapsed,
                "blender_returncode": proc.returncode,
                "checks": [],
            }
    else:
        return {
            "status": "FAIL",
            "character_name": char_name,
            "character_dir": str(char_dir),
            "suite": suite,
            "game": game,
            "error": f"Blender process exited with code {proc.returncode} without writing result.json",
            "elapsed_seconds": elapsed,
            "blender_returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-30:]),
            "checks": [],
        }


def format_results_table(results, suite, game, blender_exe):
    """Format and print a human-readable results table."""
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = total - passed

    print("\n" + "=" * 78)
    print(f"TEST SUITE: {suite.upper()} | GAME: {game.upper()}")
    print(f"Blender: {blender_exe}")
    print("-" * 78)

    for r in results:
        status = r.get("status", "FAIL")
        name = r.get("character_name", "Unknown")
        elapsed = r.get("elapsed_seconds", 0.0)
        status_tag = "[PASS]" if status == "PASS" else "[FAIL]"

        print(f"{status_tag} {name} ({elapsed:.1f}s)")
        for c in r.get("checks", []):
            c_pass = c.get("passed", False)
            c_tag = "  [OK]  " if c_pass else "  [FAIL]"
            c_name = c.get("name", "Check")
            c_msg = c.get("message", "")
            print(f"   {c_tag} {c_name}: {c_msg}")

        if r.get("error"):
            print(f"      ERROR: {r['error']}")
        if r.get("saved_blend"):
            print(f"      Blend saved: {r['saved_blend']}")

    print("-" * 78)
    print(f"SUMMARY: Total: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 78 + "\n")


def create_cli_parser(suite_name, game_name=None):
    """Create a standard CLI parser for test scripts."""
    parser = argparse.ArgumentParser(
        description=f"Run {suite_name.capitalize()} Tests" + (f" for {game_name.capitalize()}" if game_name else "")
    )
    parser.add_argument(
        "--blender",
        "-b",
        default=None,
        help="Path to blender.exe. Defaults to auto-detecting Blender 5.2 or Goo Engine.",
    )
    parser.add_argument(
        "--character",
        "--characters",
        "-c",
        nargs="+",
        default=None,
        help="One or more character folder names or paths to test (e.g. collei-a-new-leaf).",
    )
    parser.add_argument(
        "--game",
        "-g",
        default=game_name,
        choices=list(GAME_FOLDERS.keys()),
        help="Target game (genshin, zzz, hsr, wuwa, nte, ake).",
    )
    parser.add_argument(
        "--save-blend",
        action="store_true",
        help="Save resulting .blend file for visual inspection.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose Blender output.",
    )
    return parser


def run_tests_main(suite, game):
    """Entrypoint function for suite/game test files."""
    parser = create_cli_parser(suite, game)
    args = parser.parse_args()

    blender_exe = args.blender or find_default_blender()
    if not blender_exe or not Path(blender_exe).is_file():
        print(f"[FATAL] Blender executable not found: {blender_exe}")
        print("Please specify a valid path using --blender <path/to/blender.exe>")
        sys.exit(1)

    target_game = args.game or game
    if not target_game:
        print("[FATAL] Game must be specified.")
        sys.exit(1)

    char_dirs = []
    if args.character:
        for c in args.character:
            cdir = resolve_character_dir(c, game=target_game)
            if not cdir:
                print(f"[ERROR] Character '{c}' could not be resolved for game '{target_game}'")
            else:
                char_dirs.append(cdir)
    else:
        # Default: Pick the first available character for this game
        all_chars = list_characters(target_game)
        if all_chars:
            char_dirs = [all_chars[0]["path"]]
        else:
            print(f"[FATAL] No characters found for game '{target_game}'")
            sys.exit(1)

    if not char_dirs:
        print(f"[FATAL] No valid character directories found.")
        sys.exit(1)

    print(f"\nRunning {suite.upper()} tests for {target_game.upper()} on {len(char_dirs)} character(s)...")
    print(f"Blender executable: {blender_exe}")

    results = []
    for cdir in char_dirs:
        print(f"\n>>> Testing {Path(cdir).name}...")
        res = run_suite_on_character(
            blender_exe=blender_exe,
            suite=suite,
            game=target_game,
            char_dir=cdir,
            save_blend=args.save_blend,
            verbose=args.verbose,
        )
        results.append(res)

    format_results_table(results, suite=suite, game=target_game, blender_exe=blender_exe)

    all_passed = all(r.get("status") == "PASS" for r in results)
    sys.exit(0 if all_passed else 1)
