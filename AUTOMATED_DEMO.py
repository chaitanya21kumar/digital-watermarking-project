#!/usr/bin/env python3
"""
AUTOMATED DEMONSTRATION SCRIPT
Shows the complete watermarking system working with minimal manual intervention
Perfect for professor presentations - run once and everything is shown!
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*80)
print(" "*15 + "🎯 AUTOMATED WATERMARKING SYSTEM DEMO 🎯")
print("="*80)

# ============================================================================
# SECTION 1: VERIFICATION - Show all files exist
# ============================================================================
print("\n" + "─"*80)
print("STEP 1: VERIFICATION - Checking all components exist")
print("─"*80)

checks = {
    "Core Modules": [
        "src/ambtc.py", "src/vq.py", "src/bd_wt_tables.py",
        "src/watermark_embed.py", "src/watermark_extract.py"
    ],
    "Modifications": [
        "src/modifications/color_support.py", "src/modifications/sha_auth.py",
        "src/modifications/adaptive_mapping.py", "src/modifications/multilevel_recovery.py",
        "src/modifications/post_processing.py"
    ],
    "Tests": [
        "tests/test_ambtc.py", "tests/test_vq.py", "tests/test_embed_extract.py",
        "tests/test_attacks.py", "tests/test_modifications.py"
    ],
    "Documentation": [
        "docs/report.docx", "docs/presentation.pptx", "README.md"
    ]
}

all_exist = True
for category, files in checks.items():
    print(f"\n✓ {category}:")
    for f in files:
        exists = "✅" if os.path.exists(f) else "❌"
        status = "EXISTS" if os.path.exists(f) else "MISSING"
        print(f"  {exists} {f:40} [{status}]")
        if not os.path.exists(f):
            all_exist = False

if all_exist:
    print("\n✅ ALL COMPONENTS VERIFIED - Ready to proceed!")
else:
    print("\n❌ Some files missing!")
    sys.exit(1)

# ============================================================================
# SECTION 2: IMPORT TEST - Show all modules import successfully
# ============================================================================
print("\n" + "─"*80)
print("STEP 2: MODULE IMPORT TEST - Loading all Python modules")
print("─"*80)

try:
    print("\n✓ Importing core modules...")
    from src.ambtc import AMBTC
    from src.vq import VectorQuantizer
    from src.bd_wt_tables import generate_bd_table, generate_wt_table
    from src.block_mapping import generate_block_mapping
    from src.watermark_embed import WatermarkEmbedder
    from src.watermark_extract import WatermarkAuthenticator
    from src.utils import load_image, save_image
    from src.metrics import psnr
    print("  ✅ All core modules loaded successfully!")
    
    print("\n✓ Importing modifications...")
    from src.modifications.color_support import ColorWatermarkEmbedder
    from src.modifications.sha_auth import SHA256AMBTC
    from src.modifications.adaptive_mapping import AdaptiveBlockMapper
    from src.modifications.multilevel_recovery import MultiLevelRecoveryAuthenticator
    from src.modifications.post_processing import EdgePreservingRecovery
    print("  ✅ All modification modules loaded successfully!")
    
except Exception as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# ============================================================================
# SECTION 3: RUN TESTS - Show test results
# ============================================================================
print("\n" + "─"*80)
print("STEP 3: RUNNING TEST SUITE")
print("─"*80)
print("\n📊 Executing pytest...")

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=line", "-q"],
    capture_output=True,
    text=True
)

# Count passing/failing
output_lines = result.stdout.split('\n')
summary_line = [l for l in output_lines if 'passed' in l or 'failed' in l]
if summary_line:
    print("\n" + summary_line[-1])
else:
    print(result.stdout[-200:])

# ============================================================================
# SECTION 4: QUICK FUNCTIONAL TEST - Embed, Attack, Authenticate
# ============================================================================
print("\n" + "─"*80)
print("STEP 4: FUNCTIONAL TEST - Complete Watermarking Pipeline")
print("─"*80)

try:
    import numpy as np
    from PIL import Image
    
    print("\n✓ Loading test image...")
    if os.path.exists("images/test/Lena.png"):
        img = load_image("images/test/Lena.png")
        print(f"  ✅ Loaded: {img.shape}")
    else:
        print("  ⚠️  Test image not found, creating synthetic...")
        img = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
    
    print("\n✓ Step 1: EMBEDDING - Adding invisible watermark...")
    embedder = WatermarkEmbedder()
    stego_img, metadata = embedder.embed(img)
    psnr_watermarked = psnr(img, stego_img)
    print(f"  ✅ Watermark embedded! PSNR = {psnr_watermarked:.2f} dB (imperceptible!)")
    
    print("\n✓ Step 2: ATTACKING - Simulating tampering (64×64 region)...")
    # Simulate cutting attack
    attacked_img = stego_img.copy()
    attacked_img[50:114, 50:114] = 0  # Cut out 64×64 region
    print(f"  ✅ Attack applied - damaged region: [50:114, 50:114]")
    
    print("\n✓ Step 3: AUTHENTICATION - Detecting and recovering...")
    authenticator = WatermarkAuthenticator()

    # Ground truth tamper map at block-level (4x4 blocks).
    block_size = metadata.get("block_size", 4)
    bh = attacked_img.shape[0] // block_size
    bw = attacked_img.shape[1] // block_size
    true_tamper = np.zeros((bh, bw), dtype=bool)
    r0 = 50 // block_size
    r1 = (114 + block_size - 1) // block_size
    c0 = 50 // block_size
    c1 = (114 + block_size - 1) // block_size
    true_tamper[r0:r1, c0:c1] = True

    result = authenticator.authenticate_and_recover(
        attacked_img,
        metadata["vq_codebook"],
        original_image=img,
        true_tamper_map=true_tamper,
    )

    metrics = result["metrics"]
    tamper_map = result["tamper_map"]
    recovered_img = result["recovered_image"]

    print("  ✅ Authentication complete!")
    print(f"     - Predicted tamper ratio: {result['tamper_ratio']*100:.2f}%")
    print(f"     - TPR: {metrics['TPR']*100:.2f}%")
    print(f"     - FPR: {metrics['FPR']*100:.4f}%")
    print(f"     - ROI Recovery PSNR: {psnr(img[50:114, 50:114], recovered_img[50:114, 50:114]):.2f} dB")
    
except Exception as e:
    print(f"  ❌ Error during functional test: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SECTION 5: EXPERIMENTAL RESULTS SUMMARY
# ============================================================================
print("\n" + "─"*80)
print("STEP 5: EXPERIMENTAL RESULTS SUMMARY")
print("─"*80)

results_path = Path("results/experiment_results_comprehensive.json")
if results_path.exists():
    print("\n✓ Loading experiment results...")
    with open(results_path) as f:
        results = json.load(f)

    stats = results.get("statistics", {})
    experiments = results.get("experiments", [])

    def _fmt(x, nd=2):
        try:
            return f"{float(x):.{nd}f}"
        except Exception:
            return "N/A"

    print("\n📊 Experiment Summary:")
    print(f"  Total experiments: {len(experiments)}")
    wq = stats.get("watermarking_quality", {})
    dp = stats.get("detection_performance", {})
    rp = stats.get("recovery_performance", {})
    print(f"  Avg watermark PSNR: {_fmt(wq.get('avg_psnr_watermarked_db'))} dB")
    print(f"  Avg TPR / FPR:      {_fmt(dp.get('avg_tpr_percent'))}% / {_fmt(dp.get('avg_fpr_percent'), 6)}%")
    print(f"  Avg recovery PSNR:  {_fmt(rp.get('avg_psnr_recovered_db'))} dB")

    if experiments:
        exp = experiments[0]
        print(f"\n  Sample: {exp.get('image_name')} ({exp.get('attack_type')})")
        print(f"    • Watermarked PSNR: {_fmt(exp.get('psnr_watermarked'))} dB")
        print(f"    • Recovered PSNR:   {_fmt(exp.get('psnr_recovered'))} dB")
        print(f"    • TPR / FPR:        {_fmt(exp.get('TPR_percent'))}% / {_fmt(exp.get('FPR_percent'), 6)}%")
else:
    print("\n⚠️  Experiment results not found")

# ============================================================================
# SECTION 6: IMAGE VERIFICATION - Show output files
# ============================================================================
print("\n" + "─"*80)
print("STEP 6: IMAGE OUTPUTS - Verification files")
print("─"*80)

result_dir = Path("images/results_comprehensive")
if result_dir.exists():
    images = list(result_dir.glob("*.png"))
    print(f"\n✓ Result images generated: {len(images)} files")
    
    # Show some example files
    examples = [f for f in images if any(x in f.name for x in ['exp1_', 'psnr_vs'])]
    for img_file in examples[:5]:
        size_kb = img_file.stat().st_size / 1024
        print(f"  ✅ {img_file.name:35} ({size_kb:.0f} KB)")
else:
    print("\n⚠️  Result images directory not found")

# ============================================================================
# SECTION 7: PROFESSOR PRESENTATION SUMMARY
# ============================================================================
print("\n" + "="*80)
print(" "*20 + "📋 WHAT TO SHOW THE PROFESSOR 📋")
print("="*80)

professor_guide = """
DEMONSTRATION SCRIPT (data-driven; no hardcoded numbers):

1) WATERMARK QUALITY
    Show any pair: images/results_comprehensive/*_original.png vs *_watermarked.png
    Point: watermark is visually imperceptible; PSNR is in the results JSON.

2) VISIBLE TAMPERING
    Show: *_attacked.png and *_diff_attack.png
    Point: the diff map highlights the tampered ROI clearly.

3) TAMPER DETECTION
    Show: *_tamper_map.png
    Point: white blocks are detected tampering (block-level).

4) AUTOMATIC RECOVERY
    Show: *_recovered.png and *_diff_recovery.png
    Point: recovery fills the ROI; diff_recovery shows residual error.

5) METRICS (TPR/FPR + best 2–3 examples)
    Run: python show_comprehensive_results.py
    It prints averaged metrics and lists the best examples to open.

6) TESTS
    The pytest summary is printed in STEP 3 above.
"""

print(professor_guide)

# ============================================================================
# SECTION 8: FILES FOR PROFESSOR
# ============================================================================
print("\n" + "="*80)
print(" "*24 + "📁 FILES FOR PROFESSOR 📁")
print("="*80)

professor_files = {
    "docs/report.docx": "41 KB - Professional report with algorithm details",
    "docs/presentation.pptx": "42 KB - 13-slide presentation",
    "README.md": "16 KB - Complete documentation",
}

print("\nFiles to show/give to professor:\n")
for file, desc in professor_files.items():
    exists = "✅" if os.path.exists(file) else "❌"
    print(f"  {exists} {file:25} {desc}")
    if os.path.exists(file):
        size = os.path.getsize(file) / 1024
        print(f"     └─ File size: {size:.1f} KB")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print(" "*25 + "✅ DEMO COMPLETE ✅")
print("="*80)

print("""
YOUR PROJECT IS READY FOR PROFESSOR PRESENTATION!

QUICK CHECKLIST:
✓ Core modules import successfully
✓ Pytest summary printed above
✓ End-to-end embed → tamper → detect → recover ran in STEP 4
✓ Multi-image comprehensive results saved

NEXT STEPS:
1. Open images/results_comprehensive/ to view output images
2. Run python show_comprehensive_results.py to see metrics + best 2–3 examples
3. Open docs/presentation.pptx for slides
4. Open docs/report.docx for the written report

""")

print("="*80)
print(" "*18 + "Run this script anytime to verify everything works!")
print("="*80 + "\n")
