"""Full experiment suite reproducing paper results with modifications."""

import numpy as np
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt
from src.utils import load_image, save_image, crop_to_block_size
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.modifications.sha_auth import SHA256WatermarkEmbedder
from src.modifications.adaptive_mapping import AdaptiveWatermarkEmbedder
from src.modifications.multilevel_recovery import MultiLevelRecoveryAuthenticator
from src.modifications.post_processing import EdgePreservingRecovery
from src.metrics import psnr
from tests.test_attacks import cutting_attack, copy_paste_attack


def run_experiments():
    """Run comprehensive experiments."""
    
    results_dir = Path("images/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    summary_results = []
    
    print("\n" + "="*80)
    print("STARTING COMPREHENSIVE EXPERIMENTS")
    print("="*80)
    
    # Test images
    test_images = [
        ("Lena", "images/test/Lena.png"),
        ("Baboon", "images/test/Baboon.png"),
        ("Elaine", "images/test/Elaine.png"),
        ("Airplane", "images/test/Airplane.png"),
    ]
    
    # =========================================
    # EXPERIMENT 1: Cutting Attack 1 (64x64)
    # =========================================
    print("\n[EXP-1] Cutting Attack 1 (64x64, ~2% tamper)")
    print("-" * 80)
    
    for img_name, img_path in test_images[:2]:  # Use first 2 images for speed
        try:
            print(f"\n  Processing {img_name}...")
            original = load_image(img_path, grayscale=True)
            original = crop_to_block_size(original, 4)
            h, w = original.shape
            
            # Embed
            embedder = WatermarkEmbedder(seed_gamma=42, seed_gamma1=123, seed_gamma2=456)
            stego, metadata = embedder.embed(original)
            psnr_watermarked = psnr(original, stego)
            
            # Attack
            attacked, true_tamper = cutting_attack(stego, h//2-32, w//2-32, 64, 64)
            
            # Authenticate
            authenticator = WatermarkAuthenticator(42, 123, 456)
            result = authenticator.authenticate_and_recover(
                attacked, metadata['vq_codebook'], original
            )
            
            psnr_recovered = result['psnr_recovered'] or 0
            metrics = result['metrics']
            
            # Save images
            save_image(f"{results_dir}/exp1_{img_name}_original.png", original)
            save_image(f"{results_dir}/exp1_{img_name}_watermarked.png", stego)
            save_image(f"{results_dir}/exp1_{img_name}_attacked.png", attacked)
            save_image(f"{results_dir}/exp1_{img_name}_tamper_map.png", 
                      result['tamper_map_visual'])
            save_image(f"{results_dir}/exp1_{img_name}_recovered.png", 
                      result['recovered_image'])
            
            summary_results.append({
                'experiment': 'Cutting_Attack_64x64',
                'image': img_name,
                'psnr_watermarked': float(psnr_watermarked),
                'psnr_recovered': float(psnr_recovered),
                'tamper_ratio': result['tamper_ratio'],
                'TP': metrics['TP'],
                'TN': metrics['TN'],
                'FP': metrics['FP'],
                'FN': metrics['FN'],
                'TPR': metrics['TPR'],
                'FPR': metrics['FPR'],
                'FNR': metrics['FNR']
            })
            
            print(f"    ✓ PSNR watermarked: {psnr_watermarked:.2f} dB")
            print(f"    ✓ PSNR recovered: {psnr_recovered:.2f} dB")
            print(f"    ✓ TPR: {metrics['TPR']:.4f}, FPR: {metrics['FPR']:.4f}")
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # =========================================
    # EXPERIMENT 2: Cutting Attack 2 (32x32)
    # =========================================
    print("\n[EXP-2] Cutting Attack 2 (32x32, ~0.74% tamper)")
    print("-" * 80)
    
    for img_name, img_path in test_images[:2]:
        try:
            print(f"\n  Processing {img_name}...")
            original = load_image(img_path, grayscale=True)
            original = crop_to_block_size(original, 4)
            h, w = original.shape
            
            embedder = WatermarkEmbedder()
            stego, metadata = embedder.embed(original)
            
            attacked, true_tamper = cutting_attack(stego, h//2-16, w//2-16, 32, 32)
            
            authenticator = WatermarkAuthenticator()
            result = authenticator.authenticate_and_recover(
                attacked, metadata['vq_codebook'], original
            )
            
            psnr_recovered = result['psnr_recovered'] or 0
            metrics = result['metrics']
            
            save_image(f"{results_dir}/exp2_{img_name}_attacked.png", attacked)
            save_image(f"{results_dir}/exp2_{img_name}_recovered.png", 
                      result['recovered_image'])
            
            summary_results.append({
                'experiment': 'Cutting_Attack_32x32',
                'image': img_name,
                'psnr_recovered': float(psnr_recovered),
                'tamper_ratio': result['tamper_ratio'],
                'TPR': metrics['TPR'],
                'FPR': metrics['FPR']
            })
            
            print(f"    ✓ PSNR recovered: {psnr_recovered:.2f} dB")
            print(f"    ✓ TPR: {metrics['TPR']:.4f}")
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
    
    # =========================================
    # EXPERIMENT 5: Modification Comparison
    # =========================================
    print("\n[EXP-5] Modification Comparison")
    print("-" * 80)
    
    try:
        img_name = "Lena"
        img_path = "images/test/Lena.png"
        original = load_image(img_path, grayscale=True)
        original = crop_to_block_size(original, 4)
        
        print(f"\n  Testing all 5 modifications on {img_name}...")
        
        # Baseline
        print("\n  [MOD-Base] Baseline Algorithm")
        embedder_base = WatermarkEmbedder()
        stego_base, metadata_base = embedder_base.embed(original)
        attacked, _ = cutting_attack(stego_base, 48, 48, 64, 64)
        auth_base = WatermarkAuthenticator()
        result_base = auth_base.authenticate_and_recover(
            attacked, metadata_base['vq_codebook'], original
        )
        print(f"    ✓ PSNR recovered: {result_base['psnr_recovered'] or 0:.2f} dB")
        
        # MOD-2: SHA-256
        print("\n  [MOD-2] SHA-256 Enhanced Auth")
        embedder_sha = SHA256WatermarkEmbedder()
        stego_sha, metadata_sha = embedder_sha.embed(original)
        attacked_sha, _ = cutting_attack(stego_sha, 48, 48, 64, 64)
        auth_sha = WatermarkAuthenticator()
        result_sha = auth_sha.authenticate_and_recover(
            attacked_sha, metadata_sha['vq_codebook'], original
        )
        print(f"    ✓ PSNR recovered: {result_sha['psnr_recovered'] or 0:.2f} dB")
        
        # MOD-3: Adaptive Mapping
        print("\n  [MOD-3] Entropy-Adaptive Mapping")
        embedder_adap = AdaptiveWatermarkEmbedder()
        stego_adap, metadata_adap = embedder_adap.embed(original)
        attacked_adap, _ = cutting_attack(stego_adap, 48, 48, 64, 64)
        auth_adap = WatermarkAuthenticator()
        result_adap = auth_adap.authenticate_and_recover(
            attacked_adap, metadata_adap['vq_codebook'], original
        )
        print(f"    ✓ PSNR recovered: {result_adap['psnr_recovered'] or 0:.2f} dB")
        
        # MOD-4: Multi-Level Recovery
        print("\n  [MOD-4] Three-Tier Hierarchical Recovery")
        embedder_ml = WatermarkEmbedder()
        stego_ml, metadata_ml = embedder_ml.embed(original)
        attacked_ml, _ = cutting_attack(stego_ml, 48, 48, 64, 64)
        auth_ml = MultiLevelRecoveryAuthenticator()
        result_ml = auth_ml.authenticate_and_recover(
            attacked_ml, metadata_ml['vq_codebook'], original
        )
        tier_dist = result_ml['tier_distribution']
        print(f"    ✓ PSNR recovered: {result_ml['psnr_recovered'] or 0:.2f} dB")
        print(f"    ✓ Tier-1: {tier_dist['tier1_count']}, Tier-2: {tier_dist['tier2_count']}, Tier-3: {tier_dist['tier3_count']}")
        
        # MOD-5: Post-Processing
        print("\n  [MOD-5] Edge-Preserving Post-Processing")
        embedder_pp = WatermarkEmbedder()
        stego_pp, metadata_pp = embedder_pp.embed(original)
        attacked_pp, _ = cutting_attack(stego_pp, 48, 48, 64, 64)
        auth_pp = WatermarkAuthenticator()
        result_pp = auth_pp.authenticate_and_recover(
            attacked_pp, metadata_pp['vq_codebook'], original
        )
        recovered_pp = result_pp['recovered_image']
        tamper_map_pp = result_pp['tamper_map']
        
        postprocessed_pp = EdgePreservingRecovery.apply_postprocessing(
            recovered_pp, tamper_map_pp, attacked_pp
        )
        improvement = EdgePreservingRecovery.compute_psnr_improvement(
            recovered_pp, postprocessed_pp, original, tamper_map_pp
        )
        print(f"    ✓ PSNR before post-processing: {improvement['psnr_before_full']:.2f} dB")
        print(f"    ✓ PSNR after post-processing: {improvement['psnr_after_full']:.2f} dB")
        print(f"    ✓ Improvement: {improvement['psnr_improvement_full']:.2f} dB")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # =========================================
    # EXPERIMENT 6: PSNR vs Tamper Rate
    # =========================================
    print("\n[EXP-6] PSNR vs Tamper Rate Curve")
    print("-" * 80)
    
    try:
        original = load_image("images/test/Lena.png", grayscale=True)
        original = crop_to_block_size(original, 4)
        
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(original)
        
        attack_sizes = [32, 48, 64, 96, 128, 160, 192]
        psnr_values = []
        tamper_ratios = []
        
        h, w = original.shape
        for size in attack_sizes:
            if size > min(h, w) - 16:
                continue
            
            attacked, _ = cutting_attack(stego, h//2 - size//2, w//2 - size//2, size, size)
            
            authenticator = WatermarkAuthenticator()
            result = authenticator.authenticate_and_recover(
                attacked, metadata['vq_codebook'], original
            )
            
            psnr_val = result['psnr_recovered'] or 0
            psnr_values.append(psnr_val)
            tamper_ratios.append(result['tamper_ratio'] * 100)
            
            print(f"  Attack size {size}x{size}: PSNR={psnr_val:.2f} dB, Tamper={result['tamper_ratio']*100:.2f}%")
        
        # Plot
        if psnr_values:
            plt.figure(figsize=(10, 6))
            plt.plot(tamper_ratios, psnr_values, 'bo-', linewidth=2, markersize=8)
            plt.xlabel('Tamper Ratio (%)', fontsize=12)
            plt.ylabel('PSNR (dB)', fontsize=12)
            plt.title('PSNR of Recovered Image vs Tamper Rate', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{results_dir}/psnr_vs_tamper_rate.png", dpi=100)
            plt.close()
            print(f"  ✓ Graph saved to {results_dir}/psnr_vs_tamper_rate.png")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # =========================================
    # Save Results
    # =========================================
    print("\n"+ "="*80)
    print("SAVING RESULTS")
    print("="*80)
    
    with open(f"results/experiment_summary.json", "w") as f:
        json.dump(summary_results, f, indent=2)
    print(f"\n✓ Results saved to results/experiment_summary.json")
    
    # Create CSV
    if summary_results:
        import csv
        with open(f"results/experiment_summary.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=summary_results[0].keys())
            writer.writeheader()
            writer.writerows(summary_results)
        print(f"✓ Results saved to results/experiment_summary.csv")
    
    print("\n" + "="*80)
    print("EXPERIMENTS COMPLETE")
    print("="*80)
    
    return summary_results


if __name__ == "__main__":
    results = run_experiments()
