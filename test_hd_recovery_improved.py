#!/usr/bin/env python3
"""Test improved recovery on HD Lena image with enhanced watermarking."""

import numpy as np
from PIL import Image
import json
from pathlib import Path
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.metrics import psnr
from src.utils import crop_to_block_size
from generate_comprehensive_results import roi_to_true_tamper_blocks

def test_hd_image(image_path, image_name, attack_type="cut_black"):
    """Test HD image with improved recovery."""
    print(f"\n{'='*80}")
    print(f"Testing: {image_name} ({image_path})")
    print(f"Attack: {attack_type}")
    print(f"{'='*80}")
    
    # Load and prepare image
    try:
        img = np.array(Image.open(image_path).convert('L'), dtype=np.uint8)
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return None
    
    original_h, original_w = img.shape
    print(f"Original size: {original_h}x{original_w}")
    
    # Crop to block size (4x4)
    img = crop_to_block_size(img, 4)
    h, w = img.shape
    print(f"After cropping: {h}x{w}")
    
    # Embed
    print(f"\n[1] Embedding watermark...")
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(img)
    print(f"✓ Embedding complete")
    print(f"  Watermark PSNR: {psnr(img, stego):.2f} dB (imperceptible if >30)")
    
    # Apply attack
    print(f"\n[2] Applying {attack_type} attack...")
    attacked = stego.copy()
    
    # Define attack region at center
    y0, y1 = h//2 - 56, h//2 + 56
    x0, x1 = w//2 - 56, w//2 + 56
    roi = (y0, y1, x0, x1)
    
    if attack_type == "cut_black":
        attacked[y0:y1, x0:x1] = 0
        print(f"✓ Black region applied at {roi}")
    elif attack_type == "noise_patch":
        rng = np.random.default_rng(12345)
        attacked[y0:y1, x0:x1] = rng.integers(0, 256, size=(y1-y0, x1-x0), dtype=np.uint8)
        print(f"✓ Random noise applied at {roi}")
    else:
        print(f"❌ Unknown attack type: {attack_type}")
        return None
    
    # Metrics before recovery
    psnr_attacked = psnr(img, attacked)
    print(f"Attack PSNR: {psnr_attacked:.2f} dB")
    
    # Authentication with NEW reverse mapping recovery
    print(f"\n[3] Authenticating and recovering (WITH REVERSE MAPPING FIX)...")
    authenticator = WatermarkAuthenticator()
    
    # Pass metadata maps to authenticator
    authenticator.seed_gamma1 = metadata['seeds'][1]
    authenticator.seed_gamma2 = metadata['seeds'][2]
    
    # Pass true tamper map if known
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
    psnr_recovered = psnr(img, recovered)
    psnr_recovered_roi = psnr(img[y0:y1, x0:x1], recovered[y0:y1, x0:x1])
    psnr_attacked_roi = psnr(img[y0:y1, x0:x1], attacked[y0:y1, x0:x1])
    
    print(f"✓ Recovery complete")
    print(f"\n[4] RESULTS:")
    print(f"   Recovered PSNR (full): {psnr_recovered:.2f} dB")
    print(f"   Recovered PSNR (ROI):  {psnr_recovered_roi:.2f} dB")
    print(f"   Attacked PSNR (ROI):   {psnr_attacked_roi:.2f} dB")
    print(f"\n   Detection Performance:")
    print(f"   - TPR: {metrics['TPR']*100:.1f}%")
    print(f"   - FPR: {metrics['FPR']*100:.4f}%")
    print(f"   - Accuracy: {metrics['Accuracy']*100:.1f}%")
    
    # Visual quality assessment
    print(f"\n[5] Visual Quality Assessment:")
    if psnr_recovered >= 30:
        print(f"   ✅ EXCELLENT - Recovered image is nearly indistinguishable from original")
    elif psnr_recovered >= 25:
        print(f"   ✅ GOOD - Recovered image is visually similar to original")
    elif psnr_recovered >= 20:
        print(f"   ⚠️  FAIR - Recovered image has noticeable artifacts")
    else:
        print(f"   ❌ POOR - Recovered image is heavily degraded")
    
    # Save outputs
    output_dir = Path("images/results_improved")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    prefix = f"improved_{image_name}_{attack_type}"
    Image.fromarray(img).save(output_dir / f"{prefix}_01_original.png")
    Image.fromarray(stego).save(output_dir / f"{prefix}_02_watermarked.png")
    Image.fromarray(attacked).save(output_dir / f"{prefix}_03_attacked.png")
    Image.fromarray((result['tamper_map_visual']).astype(np.uint8)).save(output_dir / f"{prefix}_04_tamper_map.png")
    Image.fromarray(recovered).save(output_dir / f"{prefix}_05_recovered.png")
    
    # Visualization: show differences
    diff_attacked = np.abs(img.astype(np.int16) - attacked.astype(np.int16)).astype(np.uint8)
    diff_recovered = np.abs(img.astype(np.int16) - recovered.astype(np.int16)).astype(np.uint8)
    
    # Amplify for visibility
    diff_attacked_vis = np.clip(diff_attacked.astype(np.uint16) * 4, 0, 255).astype(np.uint8)
    diff_recovered_vis = np.clip(diff_recovered.astype(np.uint16) * 4, 0, 255).astype(np.uint8)
    
    Image.fromarray(diff_attacked_vis).save(output_dir / f"{prefix}_06_diff_attacked.png")
    Image.fromarray(diff_recovered_vis).save(output_dir / f"{prefix}_07_diff_recovered.png")
    
    print(f"   ✓ Results saved to {output_dir}/")
    
    return {
        "image_name": image_name,
        "attack_type": attack_type,
        "psnr_watermarked": round(psnr(img, stego), 2),
        "psnr_attacked": round(psnr_attacked, 2),
        "psnr_attacked_roi": round(psnr_attacked_roi, 2),
        "psnr_recovered": round(psnr_recovered, 2),
        "psnr_recovered_roi": round(psnr_recovered_roi, 2),
        "tpr_percent": round(metrics['TPR'] * 100, 2),
        "fpr_percent": round(metrics['FPR'] * 100, 4),
        "accuracy_percent": round(metrics['Accuracy'] * 100, 2),
        "improvement_vs_attacked": round(psnr_recovered - psnr_attacked, 2),
        "quality_assessment": "EXCELLENT" if psnr_recovered >= 30 else ("GOOD" if psnr_recovered >= 25 else ("FAIR" if psnr_recovered >= 20 else "POOR"))
    }

if __name__ == "__main__":
    print("\n" + "="*80)
    print("HD IMAGE RECOVERY TEST WITH IMPROVED ALGORITHM (REVERSE MAPPING)")
    print("="*80)
    
    # Test on available HD/high-quality images
    test_images = [
        ("images/test_quality/Lena_HD.jpg", "Lena_HD"),
        ("images/test/Lena.png", "Lena_512"),
    ]
    
    results = []
    for img_path, img_name in test_images:
        if Path(img_path).exists():
            result = test_hd_image(img_path, img_name, attack_type="cut_black")
            if result:
                results.append(result)
                result_copy = test_hd_image(img_path, img_name, attack_type="noise_patch")
                if result_copy:
                    results.append(result_copy)
        else:
            print(f"\n⚠️  Image not found: {img_path}")
    
    # Summary
    if results:
        print("\n" + "="*80)
        print("SUMMARY OF IMPROVED RECOVERY RESULTS")
        print("="*80)
        
        summary_data = {
            "test_results": results,
            "average_psnr_recovered": round(np.mean([r["psnr_recovered"] for r in results]), 2),
            "average_improvement": round(np.mean([r["improvement_vs_attacked"] for r in results]), 2),
        }
        
        output_file = Path("results/improved_recovery_results.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(summary_data, indent=2))
        
        print(f"\nAverage Recovered PSNR: {summary_data['average_psnr_recovered']} dB")
        print(f"Average Improvement over Attacked: {summary_data['average_improvement']} dB")
        print(f"\nDetailed results saved to: {output_file}")
        print("="*80 + "\n")
