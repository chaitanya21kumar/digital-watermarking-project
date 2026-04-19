#!/usr/bin/env python3
"""Quick multi-image benchmark with corrected metrics (optimized for speed)."""

import json
from datetime import datetime
from pathlib import Path
import sys
import numpy as np
from PIL import Image

from src.metrics import psnr
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.utils import crop_to_block_size
from generate_comprehensive_results import roi_to_true_tamper_blocks

def run_single_test(image_path, image_name, results_dir, attack_type="cut_black"):
    """Test a single image with specified attack and return results."""
    print(f"\n  Testing {image_name} with {attack_type}...", flush=True)
    
    # Load image
    img = np.array(Image.open(image_path).convert('L'), dtype=np.uint8)
    img = crop_to_block_size(img, 4)
    
    # Embed
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(img)
    
    # Attack
    attacked = stego.copy()
    h, w = attacked.shape
    y0, y1, x0, x1 = h//2 - 56, h//2 + 56, w//2 - 56, w//2 + 56
    roi = (y0, y1, x0, x1)
    
    if attack_type == "cut_black":
        attacked[y0:y1, x0:x1] = 0
    elif attack_type == "noise_patch":
        rng = np.random.default_rng(12345)
        attacked[y0:y1, x0:x1] = rng.integers(0, 256, size=(y1-y0, x1-x0), dtype=np.uint8)
    
    # Metrics
    psnr_w = float(psnr(img, stego))
    psnr_a = float(psnr(img, attacked))
    psnr_a_roi = float(psnr(img[y0:y1, x0:x1], attacked[y0:y1, x0:x1]))
    
    # Extract with CORRECTED ground-truth
    authenticator = WatermarkAuthenticator()
    true_tamper = roi_to_true_tamper_blocks(roi, stego.shape)
    result = authenticator.authenticate_and_recover(
        attacked, 
        metadata['vq_codebook'],
        original_image=img,
        true_tamper_map=true_tamper
    )
    
    recovered = result['recovered_image']
    metrics = result['metrics']
    
    psnr_r = float(psnr(img, recovered))
    psnr_r_roi = float(psnr(img[y0:y1, x0:x1], recovered[y0:y1, x0:x1]))
    
    # Save images
    prefix = f"exp_{image_name}_{attack_type}"
    Image.fromarray(img).save(results_dir / f"{prefix}_original.png")
    Image.fromarray(stego).save(results_dir / f"{prefix}_watermarked.png")  
    Image.fromarray(attacked).save(results_dir / f"{prefix}_attacked.png")
    Image.fromarray((result['tamper_map'] * 255).astype(np.uint8)).save(results_dir / f"{prefix}_tamper_map.png")
    Image.fromarray(recovered).save(results_dir / f"{prefix}_recovered.png")
    
    print(f"    ✅ {image_name}: TPR={metrics['TPR']*100:.1f}% PSNR(w,r)={psnr_w:.1f},{psnr_r:.1f}dB")
    
    return {
        "image_name": image_name,
        "attack_type": attack_type,
        "psnr_watermarked": round(psnr_w, 3),
        "psnr_attacked": round(psnr_a, 3),
        "psnr_recovered": round(psnr_r, 3),
        "psnr_attacked_roi": round(psnr_a_roi, 3),
        "psnr_recovered_roi": round(psnr_r_roi, 3),
        "TP": int(metrics["TP"]),
        "TN": int(metrics["TN"]),
        "FP": int(metrics["FP"]),
        "FN": int(metrics["FN"]),
        "TPR_percent": round(float(metrics["TPR"] * 100), 3),
        "FPR_percent": round(float(metrics["FPR"] * 100), 6),
        "accuracy_percent": round(float(metrics["Accuracy"] * 100), 3),
    }

def main():
    # Use subset of images for faster testing
    test_images = ["Lena", "Baboon", "Cameraman", "Peppers"]
    
    print("\n" + "=" * 80)
    print("LIGHTWEIGHT MULTI-IMAGE BENCHMARK (Corrected Metrics)")
    print("=" * 80)
    
    results_dir = Path("images/results_comprehensive")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    experiments = []
    for idx, img_name in enumerate(test_images, 1):
        img_path = f"images/test/{img_name}.png"
        if not Path(img_path).exists():
            print(f"⚠️  Skipping {img_name} (not found)")
            continue
        
        # Alternate attack types
        attack = ["cut_black", "noise_patch", "cut_black"][idx % 3]
        
        try:
            result = run_single_test(img_path, img_name, results_dir, attack)
            experiments.append(result)
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Compute statistics
    if experiments:
        avg = lambda k: float(np.mean([e[k] for e in experiments]))
        
        stats = {
            "total_experiments": len(experiments),
            "watermarking_quality": {
                "avg_psnr_watermarked_db": round(avg("psnr_watermarked"), 3),
            },
            "detection_performance": {
                "avg_tpr_percent": round(avg("TPR_percent"), 3),
                "avg_fpr_percent": round(avg("FPR_percent"), 6),
                "avg_accuracy_percent": round(avg("accuracy_percent"), 3),
            },
            "recovery_performance": {
                "avg_psnr_recovered_db": round(avg("psnr_recovered"), 3),
                "avg_psnr_recovered_roi_db": round(avg("psnr_recovered_roi"), 3),
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        payload = {"statistics": stats, "experiments": experiments}
        out_file = Path("results/experiment_results_corrected.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(payload, indent=2))
        
        print("\n" + "-" * 80)
        print("CORRECTED METRICS SUMMARY")
        print("-" * 80)
        print(f"Images tested: {stats['total_experiments']}")
        print(f"Avg Watermarked PSNR: {stats['watermarking_quality']['avg_psnr_watermarked_db']:.2f} dB")
        print(f"Avg TPR: {stats['detection_performance']['avg_tpr_percent']:.2f}%  (was: 9.5% - WRONG)")
        print(f"Avg FPR: {stats['detection_performance']['avg_fpr_percent']:.6f}%")
        print(f"Avg Accuracy: {stats['detection_performance']['avg_accuracy_percent']:.2f}%  (was: 9.5% - WRONG)")
        print(f"Avg Recovered PSNR: {stats['recovery_performance']['avg_psnr_recovered_db']:.2f} dB")
        print(f"Results saved to: {out_file}")
        print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
