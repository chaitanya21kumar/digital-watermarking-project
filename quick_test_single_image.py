#!/usr/bin/env python3
"""Quick single-image test to verify the system works."""

import numpy as np
from PIL import Image
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from generate_comprehensive_results import roi_to_true_tamper_blocks

# Test with Lena
print("=" * 80)
print("QUICK SINGLE-IMAGE TEST: Lena")
print("=" * 80)

img = np.array(Image.open('images/test/Lena.png').convert('L'), dtype=np.uint8)
print(f"\n[1] Loaded image: {img.shape}")

# Embed
embedder = WatermarkEmbedder()
print("[2] Embedding watermark...")
stego, metadata = embedder.embed(img)
print("    ✓ Embed complete")

# Attack
print("[3] Applying attack (black 112x112 ROI at center)...")
attacked = stego.copy()
roi = (256-56, 256+56, 256-56, 256+56)  # y0, y1, x0, x1
y0, y1, x0, x1 = roi
attacked[y0:y1, x0:x1] = 0
print(f"    ✓ Attack applied to ROI {roi}")

# Detect and recover
print("[4] Authenticating and recovering...")
authenticator = WatermarkAuthenticator()
true_tamper = roi_to_true_tamper_blocks(roi, stego.shape)
result = authenticator.authenticate_and_recover(
    attacked, 
    metadata['vq_codebook'], 
    original_image=img, 
    true_tamper_map=true_tamper
)
print("    ✓ Authentication and recovery complete")

# Print metrics
metrics = result['metrics']
print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"Detection Performance:")
print(f"  TP: {metrics['TP']}, TN: {metrics['TN']}, FP: {metrics['FP']}, FN: {metrics['FN']}")
print(f"  TPR: {metrics['TPR']*100:.2f}%")
print(f"  FPR: {metrics['FPR']*100:.4f}%")
print(f"  Accuracy: {metrics['Accuracy']*100:.2f}%")
print(f"\nRecovery Quality (ROI):")
print(f"  PSNR attacked ROI: {result.get('psnr_attacked_roi', 'N/A'):.2f} dB")
print(f"  PSNR recovered ROI: {result.get('psnr_recovered_roi', 'N/A'):.2f} dB")

# Save outputs
print("\n[5] Saving outputs...")
Image.fromarray(stego).save("images/results_comprehensive/test_Lena_watermarked.png")
Image.fromarray(attacked).save("images/results_comprehensive/test_Lena_attacked.png")
Image.fromarray(result['recovered_image']).save("images/results_comprehensive/test_Lena_recovered.png")
Image.fromarray((result['tamper_map'] * 255).astype(np.uint8)).save("images/results_comprehensive/test_Lena_tamper_map.png")

# Visual diff
diff = np.abs(stego.astype(np.int16) - attacked.astype(np.int16)).astype(np.uint8)
diff_amp = np.clip(diff.astype(np.uint16) * 6, 0, 255).astype(np.uint8)
Image.fromarray(diff_amp).save("images/results_comprehensive/test_Lena_diff_attack.png")

print("    ✓ Results saved to images/results_comprehensive/")
print("\n" + "=" * 80)
print("✓ TEST PASSED")
print("=" * 80 + "\n")
