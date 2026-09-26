"""Rig Test for Neverness to Everness characters."""
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from tests.common.runner import run_tests_main

if __name__ == "__main__":
    run_tests_main(suite="rig", game="nte")
