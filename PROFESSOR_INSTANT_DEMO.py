#!/usr/bin/env python3
"""
🎯 ONE COMMAND PROFESSOR DEMO
Process any new image in input/ folder and show complete watermarking workflow
"""

import numpy as np
from PIL import Image
import json
import sys
from pathlib import Path
from datetime import datetime
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.metrics import psnr
from src.utils import crop_to_block_size
from generate_comprehensive_results import roi_to_true_tamper_blocks


class ProfessorDemo:
    def __init__(self):
        self.results_dir = Path("images/results_improved")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        self.input_dir = Path("input")
        
    def print_header(self, text, width=100):
        """Print fancy header"""
        print(f"\n{'='*width}")
        print(f"  {text.center(width-4)}")
        print(f"{'='*width}\n")
    
    def print_section(self, num, title):
        """Print section header"""
        print(f"\n{num}️⃣  {title}")
        print(f"{'─'*90}")
    
    def process_image(self, image_path):
        """Process one image through complete workflow"""
        
        # Setup
        img = np.array(Image.open(image_path).convert('L'), dtype=np.uint8)
        img = crop_to_block_size(img, 4)
        h, w = img.shape
        image_name = Path(image_path).stem
        
        # ==================== EMBEDDING ====================
        self.print_section("1", "EMBEDDING WATERMARK")
        print(f"Image: {image_name} ({h}×{w} pixels)")
        print("Embedding watermark into image...")
        
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        psnr_wm = psnr(img, stego)
        print(f"✓ Watermark embedded successfully")
        print(f"✓ PSNR (invisibility): {psnr_wm:.2f} dB {'✅ IMPERCEPTIBLE (>30 dB)' if psnr_wm > 30 else '❌'}")
        
        # ==================== ATTACKING ====================
        self.print_section("2", "SIMULATING TAMPERING ATTACK")
        
        attacked = stego.copy()
        y0, y1 = h//2 - 56, h//2 + 56
        x0, x1 = w//2 - 56, w//2 + 56
        roi = (y0, y1, x0, x1)
        
        attacked[y0:y1, x0:x1] = 0  # Black patch attack
        
        psnr_attacked = psnr(img, attacked)
        psnr_attacked_roi = psnr(img[y0:y1, x0:x1], attacked[y0:y1, x0:x1])
        
        print(f"Attack type: Black pixel patch (112×112 at center)")
        print(f"✓ Tampered region: {y0}:{y1}, {x0}:{x1}")
        print(f"✓ PSNR after attack (full image): {psnr_attacked:.2f} dB (very corrupted)")
        print(f"✓ PSNR after attack (tampered region): {psnr_attacked_roi:.2f} dB (severely damaged)")
        
        # ==================== AUTHENTICATION ====================
        self.print_section("3", "AUTHENTICATION & TAMPER DETECTION")
        
        authenticator = WatermarkAuthenticator()
        authenticator.seed_gamma1 = metadata['seeds'][1]
        authenticator.seed_gamma2 = metadata['seeds'][2]
        
        true_tamper = roi_to_true_tamper_blocks(roi, stego.shape)
        
        print("Detecting tampered blocks...")
        result = authenticator.authenticate_and_recover(
            attacked,
            metadata['vq_codebook'],
            original_image=img,
            true_tamper_map=true_tamper
        )
        
        tamper_map = result['tamper_map']
        metrics = result['metrics']
        
        print(f"✓ Tamper detection complete")
        print(f"  • True Positive Rate (TPR): {metrics['TPR']*100:.1f}% (Correctly identified {int(np.sum(tamper_map & true_tamper))} tampered blocks)")
        print(f"  • Overall Accuracy: {metrics['Accuracy']*100:.1f}%")
        print(f"  • Detection Confidence: {'🟢 PERFECT' if metrics['TPR'] == 1.0 else '🟡 VERY GOOD' if metrics['TPR'] > 0.9 else '🔴 NEEDS WORK'}")
        
        # ==================== RECOVERY ====================
        self.print_section("4", "RECOVERY OF TAMPERED REGIONS")
        
        recovered = result['recovered_image']
        
        psnr_recovered = psnr(img, recovered)
        psnr_recovered_roi = psnr(img[y0:y1, x0:x1], recovered[y0:y1, x0:x1])
        
        print(f"Recovering tampered regions using embedded recovery data...")
        print(f"✓ Recovery complete")
        print(f"✓ PSNR after recovery (full image): {psnr_recovered:.2f} dB", end="")
        
        if psnr_recovered >= 30:
            print(f" ✅ EXCELLENT (nearly identical to original)")
        elif psnr_recovered >= 25:
            print(f" 🟢 VERY GOOD")
        else:
            print(f" 🔴 FAIR")
            
        print(f"✓ PSNR after recovery (recovered region): {psnr_recovered_roi:.2f} dB", end="")
        
        if psnr_recovered_roi >= 25:
            print(f" ✅ EXCELLENT RECOVERY")
        elif psnr_recovered_roi >= 20:
            print(f" 🟢 GOOD")
        else:
            print(f" 🔴 FAIR")
        
        # ==================== QUALITY IMPROVEMENT ====================
        improvement_full = psnr_recovered - psnr_attacked
        improvement_roi = psnr_recovered_roi - psnr_attacked_roi
        
        self.print_section("5", "QUALITY IMPROVEMENT ANALYSIS")
        print(f"Improvement by recovery algorithm:")
        print(f"  • Full image:        {psnr_attacked:.2f} dB → {psnr_recovered:.2f} dB  [+{improvement_full:.2f} dB] 🎯")
        print(f"  • Tampered region:   {psnr_attacked_roi:.2f} dB → {psnr_recovered_roi:.2f} dB  [+{improvement_roi:.2f} dB] 🎯")
        
        # ==================== COMPARISON TABLE ====================
        self.print_section("6", "COMPLETE METRICS COMPARISON")
        
        print(f"{'Metric':<40} {'Value':<20} {'Status':<20}")
        print(f"{'-'*80}")
        print(f"{'Watermark PSNR (invisibility)':<40} {psnr_wm:>18.2f} dB {'✅ IMPERCEPTIBLE' if psnr_wm > 30 else '❌':<20}")
        print(f"{'Attacked Image PSNR':<40} {psnr_attacked:>18.2f} dB {'(baseline)':<20}")
        print(f"{'Recovered Image PSNR':<40} {psnr_recovered:>18.2f} dB {'✅ EXCELLENT' if psnr_recovered >= 30 else '🟢 GOOD' if psnr_recovered >= 25 else '🔴 FAIR':<20}")
        print(f"{'Tamper Detection TPR':<40} {metrics['TPR']*100:>18.1f}% {'🟢 PERFECT' if metrics['TPR'] == 1.0 else '🟡 VERY GOOD':<20}")
        print(f"{'Overall Accuracy':<40} {metrics['Accuracy']*100:>18.1f}% {'✅ EXCELLENT' if metrics['Accuracy'] > 0.90 else '🟢 GOOD':<20}")
        
        # ==================== SAVE IMAGES ====================
        self.print_section("7", "SAVING RESULT IMAGES")
        
        outputs = {
            f"{image_name}_01_original": img,
            f"{image_name}_02_watermarked": stego,
            f"{image_name}_03_attacked": attacked,
            f"{image_name}_04_tamper_map": (tamper_map.astype(np.uint8) * 255),
            f"{image_name}_05_recovered": recovered,
            f"{image_name}_06_diff_attacked": np.abs(img.astype(int) - attacked.astype(int)).astype(np.uint8),
            f"{image_name}_07_diff_recovered": np.abs(img.astype(int) - recovered.astype(int)).astype(np.uint8),
        }
        
        for name, img_arr in outputs.items():
            output_path = self.results_dir / f"{name}.png"
            Image.fromarray(img_arr.astype(np.uint8)).save(output_path)
            print(f"  ✓ Saved {output_path.name}")
        
        # ==================== VERDICT ====================
        self.print_section("8", "PROFESSOR PRESENTATION VERDICT")
        
        print(f"System Performance: ", end="")
        
        if psnr_recovered >= 30 and metrics['TPR'] == 1.0 and metrics['Accuracy'] > 0.90:
            print(f"🟢🟢🟢 EXCELLENT 🟢🟢🟢")
            print(f"\nAll metrics exceed research paper standards:")
            print(f"  ✅ Watermark invisible (>30 dB) - Cannot be seen by human eye")
            print(f"  ✅ Tamper detection perfect (100% TPR) - All tampering detected")
            print(f"  ✅ Image recovery excellent (>30 dB) - Nearly identical to original")
            verdict = "EXCELLENT"
        elif psnr_recovered >= 25 and metrics['TPR'] > 0.95:
            print(f"🟢🟢 VERY GOOD 🟢🟢")
            print(f"\nSystem performs very well:")
            print(f"  ✅ Watermark invisible - Imperceptible to human eye")
            print(f"  ✅ Tamper detection very reliable - Almost all tampering caught")
            print(f"  ✅ Image recovery very good - Closely resembles original")
            verdict = "VERY GOOD"
        else:
            print(f"🟡 GOOD 🟡")
            print(f"\nSystem functions correctly but has room for improvement")
            verdict = "GOOD"
        
        # ==================== FILES LOCATION ====================
        self.print_section("9", "OUTPUT FILES LOCATION")
        print(f"All result images saved to: {self.results_dir.absolute()}")
        print(f"\nResult images (7 files):")
        for name in outputs.keys():
            print(f"  • {name}.png")
        
        # ==================== SUMMARY ====================
        self.print_header(f"✅ PROCESSING COMPLETE - {verdict.upper()}")
        
        # Save JSON metrics
        metrics_data = {
            "image_name": image_name,
            "timestamp": datetime.now().isoformat(),
            "image_size": {"height": h, "width": w},
            "watermark_psnr": float(psnr_wm),
            "attacked_psnr": float(psnr_attacked),
            "attacked_psnr_roi": float(psnr_attacked_roi),
            "recovered_psnr": float(psnr_recovered),
            "recovered_psnr_roi": float(psnr_recovered_roi),
            "improvement_full": float(improvement_full),
            "improvement_roi": float(improvement_roi),
            "detection_tpr": float(metrics['TPR']),
            "detection_accuracy": float(metrics['Accuracy']),
            "verdict": verdict,
            "result_images_dir": str(self.results_dir)
        }
        
        metrics_path = self.results_dir / f"{image_name}_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        print(f"\n📊 Metrics saved to: {metrics_path.name}")
        
        return metrics_data

    def run(self):
        """Run demo on all new images in input folder"""
        
        self.print_header("🎓 PROFESSOR PRESENTATION - WATERMARKING SYSTEM DEMO")
        
        input_files = list(self.input_dir.glob("*.png")) + list(self.input_dir.glob("*.jpg")) + list(self.input_dir.glob("*.jpeg"))
        
        if not input_files:
            print("❌ No images found in input/ folder")
            print("Please upload an image file (.png, .jpg, .jpeg) to the input/ folder")
            sys.exit(1)
        
        print(f"Found {len(input_files)} image(s) in input/ folder\n")
        
        all_metrics = []
        
        for i, image_path in enumerate(sorted(input_files), 1):
            if i > 1:
                print("\n" + "="*100)
            
            try:
                metrics = self.process_image(str(image_path))
                all_metrics.append(metrics)
            except Exception as e:
                print(f"\n❌ Error processing {image_path.name}: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Final summary
        if all_metrics:
            self.print_header("📊 OVERALL SUMMARY")
            
            avg_wm = np.mean([m['watermark_psnr'] for m in all_metrics])
            avg_recovered = np.mean([m['recovered_psnr'] for m in all_metrics])
            avg_tpr = np.mean([m['detection_tpr'] for m in all_metrics])
            avg_improvement = np.mean([m['improvement_full'] for m in all_metrics])
            
            print(f"Images processed: {len(all_metrics)}")
            print(f"Average watermark PSNR: {avg_wm:.2f} dB (invisibility)")
            print(f"Average recovered PSNR: {avg_recovered:.2f} dB (recovery quality)")
            print(f"Average detection TPR: {avg_tpr*100:.1f}% (tamper detection)")
            print(f"Average improvement: +{avg_improvement:.2f} dB\n")
            
            print("🎯 READY TO SHOW PROFESSOR!")
            print(f"Check: {self.results_dir.absolute()}")


if __name__ == "__main__":
    demo = ProfessorDemo()
    demo.run()
