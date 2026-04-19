#!/usr/bin/env python3
"""
DISPLAY COMPREHENSIVE RESULTS WITH BEAUTIFUL FORMATTING
Shows all metrics, percentages, and statistics formatted for professor
"""

import json
import os
from pathlib import Path
import sys

print("\n" + "="*90)
print(" "*15 + "📊 DIGITAL WATERMARKING - COMPREHENSIVE RESULTS SUMMARY 📊")
print("="*90)

results_file = Path("results/experiment_results_comprehensive.json")

if not results_file.exists():
    print("\n❌ Results file not found. Run this first:")
    print("   bash run_comprehensive_demo.sh")
    print("   OR")
    print("   python generate_test_images.py && python generate_comprehensive_results.py")
    sys.exit(1)

try:
    with open(results_file) as f:
        data = json.load(f)
    
    stats = data.get("statistics", {})
    experiments = data.get("experiments", [])
    
    # ============================================================================
    # SECTION 1: WATERMARK QUALITY METRICS
    # ============================================================================
    print("\n" + "─"*90)
    print("🎯 SECTION 1: WATERMARK INVISIBILITY METRICS")
    print("─"*90)
    
    wq = stats.get("watermarking_quality", {})
    print(f"\n  Average Watermark PSNR: {wq.get('avg_psnr_watermarked_db', 0):.2f} dB")
    print(f"  Range: {wq.get('min_psnr_watermarked_db', 0)} dB to {wq.get('max_psnr_watermarked_db', 0)} dB")
    print(f"\n  📌 ITU-R Standard: >30 dB for imperceptible watermarking")
    
    psnr_val = wq.get('avg_psnr_watermarked_db', 0)
    if psnr_val >= 35:
        rating = "🟢 EXCELLENT - Imperceptible watermark"
    elif psnr_val >= 30:
        rating = "🟡 GOOD - Mostly imperceptible"
    else:
        #!/usr/bin/env python3
        """Display comprehensive results (data-driven, no hardcoded claims)."""

        from __future__ import annotations

        import json
        import sys
        from pathlib import Path


        RESULTS_FILE = Path("results/experiment_results_comprehensive.json")
        RESULTS_DIR = Path("images/results_comprehensive")


        def _fmt(val, ndigits: int = 2) -> str:
            try:
                return f"{float(val):.{ndigits}f}"
            except Exception:
                return "N/A"


        def main() -> int:
            print("\n" + "=" * 90)
            print(" " * 10 + "📊 DIGITAL WATERMARKING - COMPREHENSIVE RESULTS SUMMARY")
            print("=" * 90)

            if not RESULTS_FILE.exists():
                print(f"\n❌ Missing {RESULTS_FILE}")
                print("Run:")
                print(f"  {sys.executable} generate_test_images.py")
                print(f"  {sys.executable} generate_comprehensive_results.py")
                return 1

            data = json.loads(RESULTS_FILE.read_text())
            stats = data.get("statistics", {})
            experiments: list[dict] = data.get("experiments", [])

            images_tested = stats.get("images_tested", [])
            total_exp = int(stats.get("total_experiments", len(experiments)))

            wq = stats.get("watermarking_quality", {})
            dp = stats.get("detection_performance", {})
            rp = stats.get("recovery_performance", {})
            av = stats.get("attack_visibility", {})

            print(f"\nExperiments: {total_exp}")
            if images_tested:
                print("Images:")
                for n in images_tested:
                    print(f"  - {n}")

            print("\n" + "─" * 90)
            print("1) Invisibility (Original vs Watermarked)")
            print("─" * 90)
            print(f"Avg PSNR: {_fmt(wq.get('avg_psnr_watermarked_db'))} dB")
            print(f"Min/Max:  {_fmt(wq.get('min_psnr_watermarked_db'))} / {_fmt(wq.get('max_psnr_watermarked_db'))} dB")

            print("\n" + "─" * 90)
            print("2) Tamper Detection (Block-level)")
            print("─" * 90)
            print(f"Avg TPR:      {_fmt(dp.get('avg_tpr_percent'))}%")
            print(f"Avg FPR:      {_fmt(dp.get('avg_fpr_percent'), 6)}%")
            print(f"Avg Accuracy: {_fmt(dp.get('avg_accuracy_percent'))}%")

            print("\n" + "─" * 90)
            print("3) Recovery Quality")
            print("─" * 90)
            print(f"Avg PSNR (full image): {_fmt(rp.get('avg_psnr_recovered_db'))} dB")
            if "avg_psnr_recovered_roi_db" in rp:
                print(f"Avg PSNR (tampered ROI): {_fmt(rp.get('avg_psnr_recovered_roi_db'))} dB")

            print("\n" + "─" * 90)
            print("4) Attack Visibility")
            print("─" * 90)
            print(f"Avg PSNR attacked (full image): {_fmt(av.get('avg_psnr_attacked_db'))} dB")
            if "avg_psnr_attacked_roi_db" in av:
                print(f"Avg PSNR attacked (ROI):       {_fmt(av.get('avg_psnr_attacked_roi_db'))} dB")

            # Per-image breakdown
            print("\n" + "─" * 90)
            print("5) Per-Experiment Breakdown")
            print("─" * 90)

            for exp in experiments:
                name = exp.get("image_name", "Unknown")
                attack = exp.get("attack_type", "Unknown")
                tpr = exp.get("TPR_percent", None)
                fpr = exp.get("FPR_percent", None)
                psnr_w = exp.get("psnr_watermarked", None)
                psnr_a_roi = exp.get("psnr_attacked_roi", None)
                psnr_r_roi = exp.get("psnr_recovered_roi", None)

                roi_gain = "N/A"
                try:
                    if psnr_a_roi is not None and psnr_r_roi is not None:
                        roi_gain = f"{float(psnr_r_roi) - float(psnr_a_roi):.2f}"
                except Exception:
                    pass

                print(
                    f"- {name:10} | attack={attack:10} | "
                    f"TPR={_fmt(tpr)}% FPR={_fmt(fpr, 6)}% | "
                    f"PSNR(w)={_fmt(psnr_w)} dB | ROI gain={roi_gain} dB"
                )

            # Pick 3 showcase experiments (largest ROI improvement)
            def _roi_improvement(e: dict) -> float:
                try:
                    return float(e.get("psnr_recovered_roi", 0.0)) - float(e.get("psnr_attacked_roi", 0.0))
                except Exception:
                    return float("-inf")

            showcase = sorted(experiments, key=_roi_improvement, reverse=True)[:3]
            if showcase:
                print("\n" + "─" * 90)
                print("6) 2–3 Professor-Ready Examples (open these)")
                print("─" * 90)
                print(f"Folder: {RESULTS_DIR}")

                for e in showcase:
                    files = e.get("files", {})
                    name = e.get("image_name", "Unknown")
                    attack = e.get("attack_type", "Unknown")
                    roi_gain = _roi_improvement(e)
                    print(f"\n{name} ({attack}) | ROI PSNR gain: {_fmt(roi_gain)} dB")
                    for k in ["original", "watermarked", "attacked", "tamper_map", "recovered", "diff_attack", "diff_recovery"]:
                        if k in files:
                            print(f"  - {k:12}: {RESULTS_DIR / files[k]}")

            print("\n" + "=" * 90)
            print("Done.")
            print("=" * 90 + "\n")
            return 0


        if __name__ == "__main__":
            raise SystemExit(main())
     Metrics:
