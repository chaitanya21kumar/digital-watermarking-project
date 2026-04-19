#!/usr/bin/env python3
"""Quick improved recovery demo - shows before/after comparison."""

import numpy as np
from PIL import Image
import json
from pathlib import Path
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.metrics import psnr
from src.utils import crop_to_block_size
from generate_comprehensive_results import roi_to_true_tamper_blocks

def demo_recovery_improvement(image_path, image_name):
    """Show recovery improvement with one test."""
    print(f"\n{'='*80}")
    print(f"QUICK DEMO: {image_name}")
    print(f"{'='*80}\n")
    
    # Load image
    img = np.array(Image.open(image_path).convert('L'), dtype=np.uint8)
    img = crop_to_block_size(img, 4)
    h, w = img.shape
    
    print(f"Image: {h}x{w}")
    
    # Embed
    print("1️⃣  Embedding watermark...")
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(img)
    print(f"   ✓ Watermark PSNR: {psnr(img, stego):.2f} dB")
    
    # Attack
    print("\n2️⃣  Attacking image (black 112×112 patch at center)...")
    attacked = stego.copy()
    y0, y1 = h//2 - 56, h//2 + 56
    x0, x1 = w//2 - 56, w//2 + 56
    roi = (y0, y1, x0, x1)
    attacked[y0:y1, x0:x1] = 0
    psnr_attacked = psnr(img, attacked)
    psnr_attacked_roi = psnr(img[y0:y1, x0:x1], attacked[y0:y1, x0:x1])
    print(f"   ✓ Attacked PSNR (full): {psnr_attacked:.2f} dB")
    print(f"   ✓ Attacked PSNR (ROI):  {psnr_attacked_roi:.2f} dB")
    
    # Recovery with IMPROVED algorithm
    print("\n3️⃣  Authenticating with IMPROVED REVERSE MAPPING recovery...")
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
    
    # Results
    psnr_recovered = psnr(img, recovered)
    psnr_recovered_roi = psnr(img[y0:y1, x0:x1], recovered[y0:y1, x0:x1])
    
    print(f"   ✓ Recovered PSNR (full): {psnr_recovered:.2f} dB ✅")
    print(f"   ✓ Recovered PSNR (ROI):  {psnr_recovered_roi:.2f} dB ✅")
    
    # Analysis
    print(f"\n4️⃣  IMPROVEMENT ANALYSIS:")
    print(f"   Recovery Quality: {psnr_recovered:.2f} dB (vs attacked {psnr_attacked:.2f} dB)")
    improvement = psnr_recovered - psnr_attacked
    print(f"   Improvement: +{improvement:.2f} dB 🎯")
    
    print(f"\n5️⃣  DETECTION PERFORMANCE:")
    print(f"   TPR (True Positive Rate): {metrics['TPR']*100:.1f}%")
    print(f"   Accuracy: {metrics['Accuracy']*100:.1f}%")
    
    if psnr_recovered >= 30:
        quality = "✅ EXCELLENT - nearly identical to original"
    elif psnr_recovered >= 25:
        quality = "✅ GOOD - visually similar to original"
    else:
        quality = "⚠️  FAIR - noticeable differences"
    
    print(f"\n6️⃣  QUALITY VERDICT: {quality}")
    
    return {
        "image": image_name,
        "psnr_watermark": round(psnr(img, stego), 2),
        "psnr_attacked": round(psnr_attacked, 2),
        "psnr_recovered": round(psnr_recovered, 2),
        "improvement": round(improvement, 2),
        "tpr": round(metrics['TPR'] * 100, 1),
        "accuracy": round(metrics['Accuracy'] * 100, 1),
    }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("IMPROVED RECOVERY DEMONSTRATION")
    print("Fix: Using reverse mapping to extract recovery data from authentic blocks")
    print("="*80)
    
    # Quick test on available images
    test_cases = [
        ("images/test_quality/Lena_HD.jpg", "Lena HD (512×512)"),
        ("images/test/Lena.png", "Lena Standard (512×512)"),
    ]
    
    results = []
    for path, name in test_cases:
        if Path(path).exists():
            result = demo_recovery_improvement(path, name)
            results.append(result)
    
    # Summary
    if results:
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        for r in results:
            print(f"\n{r['image']}:")
            print(f"  Watermark: {r['psnr_watermark']} dB (imperceptible: ✓)")
            print(f"  Recovered: {r['psnr_recovered']} dB (improvement: +{r['improvement']} dB)")
            print(f"  Detection: TPR {r['tpr']}% | Accuracy {r['accuracy']}%")
        
        avg_improvement = np.mean([r['improvement'] for r in results])
        print(f"\n🎯 Average improvement: +{avg_improvement:.2f} dB")
        print("="*80 + "\n")
