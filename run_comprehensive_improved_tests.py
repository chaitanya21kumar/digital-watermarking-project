#!/usr/bin/env python3
"""Comprehensive test suite with improved recovery on diverse images."""

import numpy as np
from PIL import Image
import json
from pathlib import Path
from datetime import datetime
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.metrics import psnr
from src.utils import crop_to_block_size
from generate_comprehensive_results import roi_to_true_tamper_blocks

def test_image_comprehensive(image_path, image_name):
    """Test image with both attack types."""
    print(f"\n{'='*80}")
    print(f"Testing: {image_name}")
    print(f"{'='*80}")
    
    # Load image
    try:
        img = np.array(Image.open(image_path).convert('L'), dtype=np.uint8)
    except Exception as e:
        print(f"❌ Failed to load: {e}")
        return None
    
    original_h, original_w = img.shape
    img = crop_to_block_size(img, 4)
    h, w = img.shape
    
    print(f"Image size: {original_h}x{original_w} → {h}x{w} (cropped)")
    
    # Embed
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(img)
    psnr_watermark = psnr(img, stego)
    
    print(f"\n✓ Watermark embedded: {psnr_watermark:.2f} dB (target: >30)")
    
    results = []
    
    for attack_type in ["cut_black", "noise_patch"]:
        print(f"\n  Attack: {attack_type}")
        
        # Apply attack
        attacked = stego.copy()
        y0, y1 = h//2 - 56, h//2 + 56
        x0, x1 = w//2 - 56, w//2 + 56
        roi = (y0, y1, x0, x1)
        
        if attack_type == "cut_black":
            attacked[y0:y1, x0:x1] = 0
        else:
            rng = np.random.default_rng(12345)
            attacked[y0:y1, x0:x1] = rng.integers(0, 256, size=(y1-y0, x1-x0), dtype=np.uint8)
        
        # Authentication with reverse mapping fix
        authenticator = WatermarkAuthenticator()
        authenticator.seed_gamma1 = metadata['seeds'][1]
        authenticator.seed_gamma2 = metadata['seeds'][2]
        
        true_tamper = roi_to_true_tamper_blocks(roi, stego.shape)
        result = authenticator.authenticate_and_recover(
            attacked,
            metadata['vq_codebook'],
            original_image=img,
            true_tamper_map=true_tamper
        )
        
        recovered = result['recovered_image']
        metrics = result['metrics']
        
        # Compute metrics
        psnr_attacked_full = psnr(img, attacked)
        psnr_recovered_full = psnr(img, recovered)
        psnr_attacked_roi = psnr(img[y0:y1, x0:x1], attacked[y0:y1, x0:x1])
        psnr_recovered_roi = psnr(img[y0:y1, x0:x1], recovered[y0:y1, x0:x1])
        
        improvement = psnr_recovered_full - psnr_attacked_full
        
        result_data = {
            "image_name": image_name,
            "attack_type": attack_type,
            "psnr_watermark": round(psnr_watermark, 2),
            "psnr_attacked_full": round(psnr_attacked_full, 2),
            "psnr_recovered_full": round(psnr_recovered_full, 2),
            "psnr_attacked_roi": round(psnr_attacked_roi, 2),
            "psnr_recovered_roi": round(psnr_recovered_roi, 2),
            "improvement_full": round(improvement, 2),
            "tpr_percent": round(metrics['TPR'] * 100, 1),
            "accuracy_percent": round(metrics['Accuracy'] * 100, 1),
        }
        
        quality = "EXCELLENT" if psnr_recovered_full >= 30 else ("GOOD" if psnr_recovered_full >= 25 else "FAIR")
        print(f"    ✓ Full PSNR: {psnr_recovered_full:.2f} dB [{quality}]")
        print(f"    ✓ ROI PSNR: {psnr_recovered_roi:.2f} dB (vs attacked {psnr_attacked_roi:.2f})")
        print(f"    ✓ Detection: TPR={metrics['TPR']*100:.0f}% Accuracy={metrics['Accuracy']*100:.0f}%")
        
        results.append(result_data)
    
    return results

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE RECOVERY TEST SUITE - IMPROVED ALGORITHM")
    print("="*80)
    
    # Available test images
    test_images = [
        ("images/test_quality/Lena_HD.jpg", "Lena_HD"),
        ("images/test/Lena.png", "Lena_512"),
        ("images/test/Baboon.png", "Baboon"),
        ("images/test/Cameraman.png", "Cameraman"),
        ("images/test/Peppers.png", "Peppers"),
        ("images/test/Airplane.png", "Airplane"),
    ]
    
    all_results = []
    available_count = 0
    
    for img_path, img_name in test_images:
        if Path(img_path).exists():
            results = test_image_comprehensive(img_path, img_name)
            if results:
                all_results.extend(results)
                available_count += 1
        else:
            print(f"\n⚠️  Skipped (not found): {img_path}")
    
    # Summary statistics
    if all_results:
        print("\n" + "="*80)
        print("SUMMARY - IMPROVED RECOVERY PERFORMANCE")
        print("="*80)
        
        psnr_vals = [r["psnr_recovered_full"] for r in all_results]
        roi_psnr_vals = [r["psnr_recovered_roi"] for r in all_results]
        tpr_vals = [r["tpr_percent"] for r in all_results]
        accuracy_vals = [r["accuracy_percent"] for r in all_results]
        
        print(f"\nTested images: {available_count}")
        print(f"Total experiments: {len(all_results)}")
        
        print(f"\n✓ Recovery Quality (Full Image):")
        print(f"    Average PSNR: {np.mean(psnr_vals):.2f} dB")
        print(f"    Min PSNR: {np.min(psnr_vals):.2f} dB")
        print(f"    Max PSNR: {np.max(psnr_vals):.2f} dB")
        
        print(f"\n✓ Recovery Quality (Attack ROI):")
        print(f"    Average PSNR: {np.mean(roi_psnr_vals):.2f} dB")
        print(f"    Range: {np.min(roi_psnr_vals):.2f} - {np.max(roi_psnr_vals):.2f} dB")
        
        print(f"\n✓ Detection Performance:")
        print(f"    Average TPR: {np.mean(tpr_vals):.1f}%")
        print(f"    Average Accuracy: {np.mean(accuracy_vals):.1f}%")
        
        # Classification
        excellent = sum(1 for r in all_results if r["psnr_recovered_full"] >= 30)
        good = sum(1 for r in all_results if 25 <= r["psnr_recovered_full"] < 30)
        fair = sum(1 for r in all_results if 20 <= r["psnr_recovered_full"] < 25)
        poor = sum(1 for r in all_results if r["psnr_recovered_full"] < 20)
        
        print(f"\n✓ Quality Classification:")
        print(f"    EXCELLENT (≥30dB): {excellent}/{len(all_results)}")
        print(f"    GOOD (25-30dB):    {good}/{len(all_results)}")
        print(f"    FAIR (20-25dB):    {fair}/{len(all_results)}")
        print(f"    POOR (<20dB):      {poor}/{len(all_results)}")
        
        # Save comprehensive results
        summary = {
            "timestamp": datetime.now().isoformat(),
            "images_tested": available_count,
            "experiments": len(all_results),
            "statistics": {
                "recovery_psnr": {
                    "average": round(np.mean(psnr_vals), 2),
                    "min": round(np.min(psnr_vals), 2),
                    "max": round(np.max(psnr_vals), 2),
                    "std": round(np.std(psnr_vals), 2),
                },
                "roi_psnr": {
                    "average": round(np.mean(roi_psnr_vals), 2),
                    "min": round(np.min(roi_psnr_vals), 2),
                    "max": round(np.max(roi_psnr_vals), 2),
                },
                "detection": {
                    "avg_tpr_percent": round(np.mean(tpr_vals), 1),
                    "avg_accuracy_percent": round(np.mean(accuracy_vals), 1),
                }
            },
            "quality_distribution": {
                "excellent": excellent,
                "good": good,
                "fair": fair,
                "poor": poor,
            },
            "results": all_results
        }
        
        out_file = Path("results/comprehensive_improved_recovery.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(summary, indent=2))
        
        print(f"\n✓ Detailed results saved to: {out_file}")
        print("="*80 + "\n")

if __name__ == "__main__":
    main()
