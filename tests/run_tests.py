"""Master Test Runner CLI.

Run all or filtered test suites across all or specific games.

Usage Examples:
    # Run all suites on default character for Genshin
    python tests/run_tests.py --game genshin

    # Run Rig suite on multiple characters
    python tests/run_tests.py --suite rig --game genshin --characters collei-a-new-leaf columbina-moonweave-gossamer

    # Run all suites with a specific Blender executable
    python tests/run_tests.py --blender "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe"

    # Run textures suite on ZZZ character
    python tests/run_tests.py --suite textures --game zzz --characters roxy-default
"""
import sys
import argparse
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tests.common.runner import (
    find_default_blender,
    run_suite_on_character,
    format_results_table,
)
from tests.common.character_resolver import (
    resolve_character_dir,
    list_characters,
    GAME_FOLDERS,
)

ALL_SUITES = ["rig", "textures", "facerig", "charactersettings"]


def main():
    parser = argparse.ArgumentParser(description="Master Test Runner for Gacha Setup Addon")
    parser.add_argument(
        "--suite",
        "-s",
        default="all",
        choices=ALL_SUITES + ["all"],
        help="Test suite to run (rig, textures, facerig, charactersettings, or all).",
    )
    parser.add_argument(
        "--game",
        "-g",
        default="all",
        choices=list(GAME_FOLDERS.keys()) + ["all"],
        help="Target game (genshin, zzz, hsr, wuwa, nte, ake, or all).",
    )
    parser.add_argument(
        "--character",
        "--characters",
        "-c",
        nargs="+",
        default=None,
        help="Specific character name(s) or folder(s) to test.",
    )
    parser.add_argument(
        "--blender",
        "-b",
        default=None,
        help="Path to blender.exe. Defaults to auto-detecting Blender 5.2 or Goo Engine.",
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

    args = parser.parse_args()

    blender_exe = args.blender or find_default_blender()
    if not blender_exe or not Path(blender_exe).is_file():
        print(f"[FATAL] Blender executable not found: {blender_exe}")
        print("Please specify a valid path using --blender <path/to/blender.exe>")
        sys.exit(1)

    suites_to_run = ALL_SUITES if args.suite == "all" else [args.suite]
    games_to_run = list(GAME_FOLDERS.keys()) if args.game == "all" else [args.game]

    print("\n" + "=" * 78)
    print("GACHA SETUP AUTOMATED TEST SUITE")
    print(f"Blender: {blender_exe}")
    print(f"Suites: {', '.join(suites_to_run)}")
    print(f"Games: {', '.join(games_to_run)}")
    print("=" * 78)

    all_results = []

    for game in games_to_run:
        # Resolve characters for this game
        if args.character:
            char_dirs = []
            for c in args.character:
                cdir = resolve_character_dir(c, game=game)
                if cdir and cdir not in char_dirs:
                    char_dirs.append(cdir)
            if not char_dirs and args.game != "all":
                print(f"[WARN] None of the specified characters belong to game '{game}'")
                continue
        else:
            chars = list_characters(game)
            char_dirs = [chars[0]["path"]] if chars else []

        if not char_dirs:
            print(f"\n[SKIP] No characters found for game: {game}")
            continue

        for suite in suites_to_run:
            print(f"\n>>> Running Suite: [{suite.upper()}] for Game: [{game.upper()}] on {len(char_dirs)} character(s)...")
            suite_results = []
            for cdir in char_dirs:
                print(f"    Testing {Path(cdir).name}...")
                res = run_suite_on_character(
                    blender_exe=blender_exe,
                    suite=suite,
                    game=game,
                    char_dir=cdir,
                    save_blend=args.save_blend,
                    verbose=args.verbose,
                )
                suite_results.append(res)
                all_results.append(res)

            format_results_table(suite_results, suite=suite, game=game, blender_exe=blender_exe)

    # Final summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("status") == "PASS")
    failed = total - passed

    print("\n" + "#" * 78)
    print(f"OVERALL RESULTS: Total: {total} | Passed: {passed} | Failed: {failed}")
    print("#" * 78 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
