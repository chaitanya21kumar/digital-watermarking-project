"""MOD-5: Edge-Preserving Post-Processing - Bilateral filtering for artifact reduction."""

import numpy as np
import cv2
from src.metrics import psnr


class EdgePreservingRecovery:
    """
    Post-processing with edge-preserving bilateral filter.
    
    Novelty: VQ-based recovery introduces blocking artifacts. Paper acknowledges
    "room to improve image quality of restored images" - this addresses exactly that.
    """
    
    @staticmethod
    def apply_postprocessing(recovered_image: np.ndarray,
                            tamper_map: np.ndarray,
                            stego_image: np.ndarray,
                            block_size: int = 4,
                            bilateral_d: int = 5,
                            bilateral_sigma_color: float = 30,
                            bilateral_sigma_space: float = 10) -> np.ndarray:
        """
        Apply edge-preserving filtering to recovered regions only.
        
        Args:
            recovered_image: Recovered uint8 image (possibly with artifacts)
            tamper_map: Block-level tamper map (2D bool array)
            stego_image: Original stego image for guided filtering
            block_size: Block size (for mapping block indices to pixels)
            bilateral_d: Diameter of pixel neighborhood for bilateral filter
            bilateral_sigma_color: Color space sigma for bilateral filter
            bilateral_sigma_space: Coordinate space sigma for bilateral filter
        
        Returns:
            Post-processed uint8 image
        """
        h, w = recovered_image.shape
        recovered = recovered_image.astype(np.float32)
        
        # Create mask: 1 where blocks are recovered (tampered), 0 otherwise
        num_blocks_h, num_blocks_w = tamper_map.shape
        mask = np.zeros((h, w), dtype=np.float32)
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                if tamper_map[i, j]:
                    r_start = i * block_size
                    c_start = j * block_size
                    r_end = min(r_start + block_size, h)
                    c_end = min(c_start + block_size, w)
                    mask[r_start:r_end, c_start:c_end] = 1.0
        
        # Dilate mask slightly to include block boundaries
        if np.sum(mask) > 0:
            mask_uint8 = (mask * 255).astype(np.uint8)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask_dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
            mask = (mask_dilated.astype(np.float32)) / 255.0
        
        # Apply bilateral filter for smoothing
        bilateral_filtered = cv2.bilateralFilter(
            recovered_image.astype(np.uint8),
            d=bilateral_d,
            sigmaColor=bilateral_sigma_color,
            sigmaSpace=bilateral_sigma_space
        ).astype(np.float32)
        
        # Blend: apply bilateral filter only to recovered regions
        result = recovered * (1.0 - mask) + bilateral_filtered * mask
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def apply_postprocessing_with_guided_filter(recovered_image: np.ndarray,
                                                 tamper_map: np.ndarray,
                                                 stego_image: np.ndarray,
                                                 block_size: int = 4,
                                                 radius: int = 4) -> np.ndarray:
        """
        Advanced post-processing with guided filter at block boundaries.
        
        Uses stego image as guide for better edge preservation.
        
        Args:
            recovered_image: Recovered uint8 image
            tamper_map: Block-level tamper map
            stego_image: Original stego image (as guide)
            block_size: Block size
            radius: Radius for guided filter
        
        Returns:
            Post-processed uint8 image
        """
        h, w = recovered_image.shape
        result = recovered_image.copy().astype(np.float32)
        
        # Apply at block boundaries
        eps = 1.0
        
        for i in range(tamper_map.shape[0]):
            for j in range(tamper_map.shape[1]):
                if not tamper_map[i, j]:
                    continue
                
                # Block coordinates
                r_start = i * block_size
                c_start = j * block_size
                r_end = min(r_start + block_size, h)
                c_end = min(c_start + block_size, w)
                
                # Boundary region (2 pixels around block)
                r_start_ext = max(0, r_start - 2)
                c_start_ext = max(0, c_start - 2)
                r_end_ext = min(h, r_end + 2)
                c_end_ext = min(w, c_end + 2)
                
                # Extract patches
                recovered_patch = result[r_start_ext:r_end_ext, c_start_ext:c_end_ext]
                guide_patch = stego_image[r_start_ext:r_end_ext, c_start_ext:c_end_ext].astype(np.float32)
                
                # Apply guided filter concept (simplified)
                # Use weighted average where weights are based on guide image similarity
                weights = np.exp(-((guide_patch - guide_patch.mean())**2) / (eps + 50))
                if weights.sum() > 0:
                    weights = weights / weights.sum()
                
                # Blend recovered with weighted guide
                filtered_patch = 0.8 * recovered_patch + 0.2 * guide_patch * weights.mean()
                result[r_start_ext:r_end_ext, c_start_ext:c_end_ext] = filtered_patch
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    def compute_psnr_improvement(before: np.ndarray,
                                 after: np.ndarray,
                                 original: np.ndarray,
                                 tamper_map: np.ndarray,
                                 block_size: int = 4) -> dict:
        """
        Compute PSNR improvement from post-processing.
        
        Returns:
            Dictionary with PSNR improvements for whole image and tampered regions
        """
        psnr_before_full = psnr(before, original)
        psnr_after_full = psnr(after, original)
        
        # Compute for tampered regions only
        h, w = tamper_map.shape
        mask = np.zeros((before.shape[0], before.shape[1]), dtype=bool)
        
        for i in range(h):
            for j in range(w):
                if tamper_map[i, j]:
                    r_start = i * block_size
                    c_start = j * block_size
                    r_end = min(r_start + block_size, before.shape[0])
                    c_end = min(c_start + block_size, before.shape[1])
                    mask[r_start:r_end, c_start:c_end] = True
        
        if np.sum(mask) > 0:
            before_tampered = before[mask]
            after_tampered = after[mask]
            original_tampered = original[mask]
            
            mse_before = np.mean((before_tampered.astype(float) - original_tampered.astype(float))**2)
            mse_after = np.mean((after_tampered.astype(float) - original_tampered.astype(float))**2)
            
            psnr_before_tampered = 10 * np.log10(255**2 / (mse_before + 1e-10))
            psnr_after_tampered = 10 * np.log10(255**2 / (mse_after + 1e-10))
        else:
            psnr_before_tampered = float('inf')
            psnr_after_tampered = float('inf')
        
        return {
            'psnr_before_full': float(psnr_before_full),
            'psnr_after_full': float(psnr_after_full),
            'psnr_improvement_full': float(psnr_after_full - psnr_before_full),
            'psnr_before_tampered': float(psnr_before_tampered),
            'psnr_after_tampered': float(psnr_after_tampered),
            'psnr_improvement_tampered': float(psnr_after_tampered - psnr_before_tampered) if psnr_before_tampered != float('inf') else 0.0
        }


if __name__ == "__main__":
    from src.utils import generate_synthetic_grayscale_image
    from src.watermark_embed import WatermarkEmbedder
    from src.watermark_extract import WatermarkAuthenticator
    
    test_img = generate_synthetic_grayscale_image(128, 128)
    
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(test_img)
    
    # Simulate attack by corrupting one block
    stego_attacked = stego.copy()
    stego_attacked[20:24, 20:24] = 100
    
    authenticator = WatermarkAuthenticator()
    result = authenticator.authenticate_and_recover(
        stego_attacked, metadata['vq_codebook'], test_img
    )
    
    recovered = result['recovered_image']
    tamper_map = result['tamper_map']
    
    # Apply post-processing
    postprocessed = EdgePreservingRecovery.apply_postprocessing(
        recovered, tamper_map, stego_attacked, block_size=4
    )
    
    # Compute improvement
    improvement = EdgePreservingRecovery.compute_psnr_improvement(
        recovered, postprocessed, test_img, tamper_map
    )
    
    print(f"PSNR improvement: {improvement['psnr_improvement_full']:.2f} dB (full image)")
    print(f"PSNR improvement: {improvement['psnr_improvement_tampered']:.2f} dB (tampered regions)")
