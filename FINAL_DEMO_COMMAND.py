#!/usr/bin/env python3
"""Run the complete professor demo (end-to-end, data-driven)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _run(script: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT}{os.pathsep}{env.get('PYTHONPATH', '')}"
    subprocess.run([sys.executable, script], cwd=str(ROOT), env=env, check=True)


def main() -> int:
    print("\n" + "╔" + "=" * 88 + "╗")
    print("║" + " " * 88 + "║")
    print("║" + " " * 18 + "🎯 PROFESSOR DEMONSTRATION - COMPLETE SYSTEM 🎯" + " " * 20 + "║")
    print("║" + " " * 88 + "║")
    print("╚" + "=" * 88 + "╝")
    print(f"Using Python: {sys.executable}\n")

    print("STEP 1: Generating diverse test images...")
    _run("generate_test_images.py")

    print("\nSTEP 2: Running comprehensive experiments...")
    _run("generate_comprehensive_results.py")

    print("\nSTEP 3: Showing results summary + best examples...")
    _run("show_comprehensive_results.py")

    print("\n" + "╔" + "=" * 88 + "╗")
    print("║" + "  DONE. Open the folders below to show your professor.".ljust(88) + "║")
    print("╚" + "=" * 88 + "╝")

    print("\nFolders:")
    print(f"  - images/test")
    print(f"  - images/results_comprehensive")
    print("\nMetrics JSON:")
    print("  - results/experiment_results_comprehensive.json\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
