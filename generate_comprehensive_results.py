#!/usr/bin/env python3
"""Generate robust multi-image watermarking results with visible attacks/recovery."""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from src.metrics import psnr
from src.utils import crop_to_block_size, download_test_images, generate_synthetic_grayscale_image
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator


def _load_test_images(test_dir: Path) -> dict:
    """Load multiple test images; ensure at least 6 diverse images exist."""
    test_dir.mkdir(parents=True, exist_ok=True)

    # Try web download first (USC SIPI). Missing assets are synthesized in utils fallback.
    try:
        download_test_images(str(test_dir))
    except Exception:
        pass

    images = {}
    for p in sorted(test_dir.glob("*.png")):
        try:
            arr = np.array(Image.open(p).convert("L"), dtype=np.uint8)
            images[p.stem] = crop_to_block_size(arr, 4)
        except Exception:
            continue

    # Ensure minimum diversity count for demo even without network.
    if len(images) < 6:
        seeds = [11, 97, 223, 509, 1021, 2047]
        names = ["PatternA", "PatternB", "PatternC", "PatternD", "PatternE", "PatternF"]
        for name, seed in zip(names, seeds):
            if name in images:
                continue
            arr = generate_synthetic_grayscale_image(512, 512, seed=seed).astype(np.uint8)
            arr = crop_to_block_size(arr, 4)
            Image.fromarray(arr).save(test_dir / f"{name}.png")
            images[name] = arr

    return images


def _apply_attack(
    stego: np.ndarray,
    attack: str,
    donor: np.ndarray | None = None,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Apply visible tampering attack and return (attacked, roi)."""
    attacked = stego.copy()
    h, w = attacked.shape

    y0 = h // 2 - 56
    x0 = w // 2 - 56
    y1 = y0 + 112
    x1 = x0 + 112

    if attack == "cut_black":
        attacked[y0:y1, x0:x1] = 0
    elif attack == "noise_patch":
        rng = np.random.default_rng(12345)
        attacked[y0:y1, x0:x1] = rng.integers(0, 256, size=(y1 - y0, x1 - x0), dtype=np.uint8)
    elif attack == "copy_paste":
        sy0, sx0 = 32, 32
        if donor is not None:
            donor = donor.astype(np.uint8)
            attacked[y0:y1, x0:x1] = donor[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
        else:
            attacked[y0:y1, x0:x1] = attacked[sy0:sy0 + (y1 - y0), sx0:sx0 + (x1 - x0)]
    else:
        attacked[y0:y1, x0:x1] = 0

    return attacked, (y0, y1, x0, x1)


def _save_diff_map(a: np.ndarray, b: np.ndarray, out_path: Path):
    """Save amplified absolute-difference map for visual inspection."""
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).astype(np.uint8)
    diff_amp = np.clip(diff.astype(np.uint16) * 6, 0, 255).astype(np.uint8)
    Image.fromarray(diff_amp).save(out_path)


def roi_to_true_tamper_blocks(roi: tuple[int, int, int, int], shape: tuple[int, int], block_size: int = 4) -> np.ndarray:
    """Build block-level ground truth map from attack ROI."""
    y0, y1, x0, x1 = roi
    h, w = shape
    bh = h // block_size
    bw = w // block_size
    gt = np.zeros((bh, bw), dtype=bool)

    r0 = max(0, y0 // block_size)
    r1 = min(bh, (y1 + block_size - 1) // block_size)
    c0 = max(0, x0 // block_size)
    c1 = min(bw, (x1 + block_size - 1) // block_size)
    gt[r0:r1, c0:c1] = True
    return gt


def main():
    print("\n" + "=" * 90)
    print(" " * 18 + "COMPREHENSIVE MULTI-IMAGE WATERMARKING BENCHMARK")
    print("=" * 90)

    test_dir = Path("images/test")
    results_dir = Path("images/results_comprehensive")
    out_json = Path("results/experiment_results_comprehensive.json")

    results_dir.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    images = _load_test_images(test_dir)
    image_items = list(images.items())[:6]

    if not image_items:
        raise RuntimeError("No test images available.")

    print(f"Loaded {len(image_items)} images: {', '.join([n for n, _ in image_items])}")

    attacks = ["cut_black", "noise_patch", "copy_paste"]
    experiments = []

    for idx, (name, original) in enumerate(image_items, 1):
        print(f"\n[{idx}/{len(image_items)}] {name}")

        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(original)

        # Rotate attack types across images so final folder shows different tampering styles.
        attack_type = attacks[(idx - 1) % len(attacks)]

        donor = None
        if attack_type == "copy_paste" and len(image_items) > 1:
            donor_name, donor_img = image_items[idx % len(image_items)]
            donor = donor_img
            print(f"  using donor for copy_paste: {donor_name}")

        attacked, roi = _apply_attack(stego, attack_type, donor=donor)

        # True tamper blocks are known from ROI.
        true_tamper_blocks = roi_to_true_tamper_blocks(roi, stego.shape, block_size=4)

        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked,
            metadata["vq_codebook"],
            original_image=original,
            true_tamper_map=true_tamper_blocks,
        )

        recovered = result["recovered_image"]
        tamper_visual = result["tamper_map_visual"]
        metrics = result["metrics"]

        psnr_w = float(psnr(original, stego))
        psnr_a = float(psnr(original, attacked))
        psnr_r = float(psnr(original, recovered))

        y0, y1, x0, x1 = roi
        psnr_a_roi = float(psnr(original[y0:y1, x0:x1], attacked[y0:y1, x0:x1]))
        psnr_r_roi = float(psnr(original[y0:y1, x0:x1], recovered[y0:y1, x0:x1]))

        prefix = f"exp{idx}_{name}"
        p_original = results_dir / f"{prefix}_original.png"
        p_watermarked = results_dir / f"{prefix}_watermarked.png"
        p_attacked = results_dir / f"{prefix}_attacked.png"
        p_tamper = results_dir / f"{prefix}_tamper_map.png"
        p_recovered = results_dir / f"{prefix}_recovered.png"
        p_diff_attack = results_dir / f"{prefix}_diff_attack.png"
        p_diff_recovery = results_dir / f"{prefix}_diff_recovery.png"

        Image.fromarray(original).save(p_original)
        Image.fromarray(stego).save(p_watermarked)
        Image.fromarray(attacked).save(p_attacked)
        Image.fromarray(tamper_visual).save(p_tamper)
        Image.fromarray(recovered).save(p_recovered)
        # Diff maps should compare to the *watermarked reference* so only tampering/recovery shows.
        _save_diff_map(stego, attacked, p_diff_attack)
        _save_diff_map(stego, recovered, p_diff_recovery)

        print(
            f"  attack={attack_type} roi={roi} | "
            f"PSNR(w,a,r)=({psnr_w:.2f},{psnr_a:.2f},{psnr_r:.2f}) dB | "
            f"ROI-PSNR(a,r)=({psnr_a_roi:.2f},{psnr_r_roi:.2f}) dB | "
            f"TPR={metrics['TPR']*100:.2f}% FPR={metrics['FPR']*100:.4f}%"
        )

        experiments.append(
            {
                "exp_id": idx,
                "image_name": name,
                "image_size": f"{original.shape[0]}x{original.shape[1]}",
                "attack_type": attack_type,
                "attack_region": f"[{roi[0]}:{roi[1]}, {roi[2]}:{roi[3]}]",
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
                "files": {
                    "original": p_original.name,
                    "watermarked": p_watermarked.name,
                    "attacked": p_attacked.name,
                    "tamper_map": p_tamper.name,
                    "recovered": p_recovered.name,
                    "diff_attack": p_diff_attack.name,
                    "diff_recovery": p_diff_recovery.name,
                },
            }
        )

    avg = lambda k: float(np.mean([e[k] for e in experiments]))

    stats = {
        "total_experiments": len(experiments),
        "images_tested": [n for n, _ in image_items],
        "watermarking_quality": {
            "avg_psnr_watermarked_db": round(avg("psnr_watermarked"), 3),
            "min_psnr_watermarked_db": round(float(np.min([e["psnr_watermarked"] for e in experiments])), 3),
            "max_psnr_watermarked_db": round(float(np.max([e["psnr_watermarked"] for e in experiments])), 3),
            "quality_assessment": "Imperceptible (ITU-R >30dB)" if avg("psnr_watermarked") >= 30 else "Perceptible",
        },
        "attack_visibility": {
            "avg_psnr_attacked_db": round(avg("psnr_attacked"), 3),
            "avg_psnr_attacked_roi_db": round(avg("psnr_attacked_roi"), 3),
            "assessment": "Clearly visible attacks" if avg("psnr_attacked_roi") < 20 else "Moderate visibility",
        },
        "detection_performance": {
            "avg_tpr_percent": round(avg("TPR_percent"), 3),
            "avg_fpr_percent": round(avg("FPR_percent"), 6),
            "avg_accuracy_percent": round(avg("accuracy_percent"), 3),
        },
        "recovery_performance": {
            "avg_psnr_recovered_db": round(avg("psnr_recovered"), 3),
            "min_psnr_recovered_db": round(float(np.min([e["psnr_recovered"] for e in experiments])), 3),
            "max_psnr_recovered_db": round(float(np.max([e["psnr_recovered"] for e in experiments])), 3),
            "avg_psnr_recovered_roi_db": round(avg("psnr_recovered_roi"), 3),
        },
        "timestamp": datetime.now().isoformat(),
    }

    payload = {"statistics": stats, "experiments": experiments}
    out_json.write_text(json.dumps(payload, indent=2))

    print("\n" + "-" * 90)
    print("SUMMARY")
    print("-" * 90)
    print(f"Images tested: {stats['total_experiments']}")
    print(f"Avg watermarked PSNR: {stats['watermarking_quality']['avg_psnr_watermarked_db']:.2f} dB")
    print(f"Avg attacked PSNR:    {stats['attack_visibility']['avg_psnr_attacked_db']:.2f} dB")
    print(f"Avg recovered PSNR:   {stats['recovery_performance']['avg_psnr_recovered_db']:.2f} dB")
    print(f"Avg TPR / FPR:        {stats['detection_performance']['avg_tpr_percent']:.2f}% / {stats['detection_performance']['avg_fpr_percent']:.4f}%")
    print(f"Saved JSON:           {out_json}")
    print(f"Saved images:         {results_dir}")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    main()
