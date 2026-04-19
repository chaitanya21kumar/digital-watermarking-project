#!/usr/bin/env python3
"""Run the end-to-end demo from Python (no bash)."""

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
    print("\n" + "=" * 90)
    print(" " * 14 + "🎯 DIGITAL WATERMARKING SYSTEM - COMPLETE DEMO")
    print("=" * 90)
    print(f"Using Python: {sys.executable}")

    if sys.prefix == sys.base_prefix:
        print("\n⚠️  Warning: not running inside a virtual environment.")
        print("   (This is OK if dependencies are installed globally.)")

    print("\nSTEP 1: Generating diverse test images...")
    _run("generate_test_images.py")

    print("\nSTEP 2: Running comprehensive experiments...")
    _run("generate_comprehensive_results.py")

    print("\nSTEP 3: Displaying results summary...")
    _run("show_comprehensive_results.py")

    print("\n" + "=" * 90)
    print("✅ DEMO COMPLETE")
    print("=" * 90 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
