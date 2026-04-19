"""Metrics for watermarking evaluation: PSNR, TPR, FPR, FNR."""

import numpy as np


def psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute Peak Signal-to-Noise Ratio (PSNR) between two uint8 images.
    Returns infinity if images are identical.
    """
    mse = np.mean((img1.astype(np.float64) - img2.astype(np.float64))**2)
    if mse == 0:
        return float('inf')
    max_val = 255.0
    return 10 * np.log10(max_val**2 / mse)


def compute_detection_metrics(pred_tamper: np.ndarray, 
                              true_tamper: np.ndarray) -> dict:
    """
    Compute detection metrics: TP, TN, FP, FN, TPR, FPR, FNR, Accuracy.
    
    Args:
        pred_tamper: bool array, True = predicted as tampered
        true_tamper: bool array, True = actually tampered
    
    Returns:
        dict with TP, TN, FP, FN, TPR, FPR, FNR, Accuracy
    """
    pred_tamper = pred_tamper.astype(bool).flatten()
    true_tamper = true_tamper.astype(bool).flatten()
    
    tp = np.sum(pred_tamper & true_tamper)
    tn = np.sum(~pred_tamper & ~true_tamper)
    fp = np.sum(pred_tamper & ~true_tamper)
    fn = np.sum(~pred_tamper & true_tamper)
    
    # True Positive Rate (Sensitivity/Recall)
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    
    # False Positive Rate
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    # False Negative Rate
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    # Accuracy
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    
    return {
        'TP': int(tp),
        'TN': int(tn),
        'FP': int(fp),
        'FN': int(fn),
        'TPR': float(tpr),
        'FPR': float(fpr),
        'FNR': float(fnr),
        'Accuracy': float(accuracy)
    }


if __name__ == "__main__":
    # Test metrics
    pred = np.array([True, True, False, False, True])
    true = np.array([True, False, False, True, True])
    
    metrics = compute_detection_metrics(pred, true)
    print("Test Metrics:", metrics)
    
    # Test PSNR
    img1 = np.ones((10, 10), dtype=np.uint8) * 100
    img2 = img1.copy()
    print(f"PSNR (identical): {psnr(img1, img2)}")
    
    img2[0, 0] = 110
    print(f"PSNR (1 pixel diff): {psnr(img1, img2):.2f} dB")
