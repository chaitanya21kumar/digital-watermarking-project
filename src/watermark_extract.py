"""Watermark extraction and authentication algorithm."""

import numpy as np
from src.ambtc import AMBTC
from src.vq import VectorQuantizer
from src.bd_wt_tables import generate_bd_table, generate_wt_table, extract_3bit_watermark
from src.block_mapping import generate_block_mapping
from src.metrics import psnr, compute_detection_metrics
from src.utils import crop_to_block_size


class WatermarkAuthenticator:
    """Fragile watermarking authenticator and recovery."""
    
    def __init__(self, seed_gamma=42, seed_gamma1=123, seed_gamma2=456, block_size=4):
        self.seed_gamma = seed_gamma
        self.seed_gamma1 = seed_gamma1
        self.seed_gamma2 = seed_gamma2
        self.block_size = block_size
    
    def authenticate_and_recover(
        self,
        stego_image: np.ndarray,
        vq_codebook: np.ndarray,
        original_image: np.ndarray | None = None,
        true_tamper_map: np.ndarray | None = None,
    ) -> dict:
        """
        Full authentication and recovery pipeline.
        
        Args:
            stego_image: uint8 watermarked/attacked image
            vq_codebook: VQ codebook for recovery
            original_image: Optional reference (typically the *original host* image).
                If provided, PSNR metrics are computed against it.
                For detection ground truth, we *ignore watermark-only LSB changes* by
                thresholding absolute pixel differences > 15.
            true_tamper_map: Optional *block-level* boolean tamper map (2D or 1D).
                If provided, it is used as the ground truth for detection metrics.
        
        Returns:
            Dictionary with tamper_map, recovered_image, metrics, etc.
        """
        stego_image = stego_image.astype(np.uint8)
        stego_image = crop_to_block_size(stego_image, self.block_size)
        h, w = stego_image.shape

        if original_image is not None:
            original_image = crop_to_block_size(original_image.astype(np.uint8), self.block_size)
            if original_image.shape != stego_image.shape:
                raise ValueError(
                    "original_image must match stego_image shape after cropping "
                    f"(got {original_image.shape} vs {stego_image.shape})."
                )
        
        print(f"[Auth] Image size: {h}x{w}")
        
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        # PHASE 1: Extract watermarks
        print("[Auth] Phase 1: Extracting watermarks...")
        num_blocks_h = h // self.block_size
        num_blocks_w = w // self.block_size
        num_blocks = num_blocks_h * num_blocks_w
        
        ac_ext = np.zeros(num_blocks, dtype=np.uint8)
        ri1_ext = np.zeros(num_blocks, dtype=np.uint8)
        ri2_ext = np.zeros(num_blocks, dtype=np.uint8)
        
        linear_idx = 0
        for block_row in range(num_blocks_h):
            for block_col in range(num_blocks_w):
                ac, ri1, ri2 = self._extract_block_watermark(
                    stego_image, block_row, block_col, BD, WT, self.block_size
                )
                ac_ext[linear_idx] = ac
                ri1_ext[linear_idx] = ri1
                ri2_ext[linear_idx] = ri2
                linear_idx += 1
        
        # PHASE 2: Preprocess stego for auth code recomputation
        print("[Auth] Phase 2: Recomputing auth codes...")
        preprocessed = self._preprocess_image(stego_image)
        ambtc = AMBTC(self.block_size)
        compressed_blocks = ambtc.compress(preprocessed)
        
        ac_recomp = np.zeros(num_blocks, dtype=np.uint8)
        for i, block_data in enumerate(compressed_blocks):
            ac_recomp[i] = ambtc.generate_auth_code(
                block_data['xL'], block_data['xH'], block_data['BM']
            )
        
        # PHASE 3: Tamper detection (first round)
        print("[Auth] Phase 3: Identifying tampered blocks...")
        map1 = generate_block_mapping(num_blocks, self.seed_gamma1)
        map2 = generate_block_mapping(num_blocks, self.seed_gamma2)
        
        tamper_map_1d = np.zeros(num_blocks, dtype=bool)
        for block_idx in range(num_blocks):
            src1_idx = map1[block_idx]
            # Compare extracted AC with recomputed AC
            if ac_ext[block_idx] != ac_recomp[src1_idx]:
                tamper_map_1d[block_idx] = True
        
        # PHASE 4: Refined tamper detection (3x3 neighborhood)
        print("[Auth] Phase 4: Refining tamper detection...")
        tamper_map = tamper_map_1d.reshape(num_blocks_h, num_blocks_w)
        tamper_map = self._refine_tamper_map(tamper_map)
        tamper_map_1d = tamper_map.flatten()
        
        # PHASE 5: Recovery
        print("[Auth] Phase 5: Recovering tampered regions...")
        vq = VectorQuantizer(codebook_size=256, block_size=self.block_size)
        vq.codebook = vq_codebook
        
        recovered_image = stego_image.copy()
        
        for block_idx in range(num_blocks):
            if not tamper_map_1d[block_idx]:
                continue  # Block is valid, no recovery needed
            
            src1_idx = map1[block_idx]
            src2_idx = map2[block_idx]
            
            block_row = block_idx // num_blocks_w
            block_col = block_idx % num_blocks_w
            
            # Try tier 1: RI1 from Map1
            if not tamper_map_1d[src1_idx]:
                vq_idx = ri1_ext[block_idx]
                recovery_block = vq.decode_block(vq_idx)
            # Try tier 2: RI2 from Map2
            elif not tamper_map_1d[src2_idx]:
                vq_idx = ri2_ext[block_idx]
                recovery_block = vq.decode_block(vq_idx)
            # Fallback: interpolation from neighbors
            else:
                recovery_block = self._interpolate_recovery(
                    recovered_image, block_row, block_col,
                    tamper_map, self.block_size
                )
            
            # Write recovered block
            r_start = block_row * self.block_size
            c_start = block_col * self.block_size
            recovered_image[r_start:r_start+self.block_size,
                          c_start:c_start+self.block_size] = recovery_block
        
        # Create visual tamper map (grayscale)
        tamper_visual = np.zeros((h, w), dtype=np.uint8)
        for block_idx in range(num_blocks):
            block_row = block_idx // num_blocks_w
            block_col = block_idx % num_blocks_w
            r_start = block_row * self.block_size
            c_start = block_col * self.block_size
            
            if tamper_map_1d[block_idx]:
                tamper_visual[r_start:r_start+self.block_size,
                            c_start:c_start+self.block_size] = 255
        
        # Compute metrics
        print("[Auth] Computing metrics...")
        psnr_stego = psnr(stego_image, original_image) if original_image is not None else None
        psnr_recovered = psnr(recovered_image, original_image) if original_image is not None else None
        
        tamper_ratio = np.sum(tamper_map_1d) / num_blocks
        
        metrics = {
            'TP': 0, 'TN': 0, 'FP': 0, 'FN': 0,
            'TPR': 0, 'FPR': 0, 'FNR': 0, 'Accuracy': 0
        }

        true_tamper_1d: np.ndarray | None = None

        # Prefer explicit ground truth tamper map if provided.
        if true_tamper_map is not None:
            true_tm = np.asarray(true_tamper_map).astype(bool)
            if true_tm.ndim == 2:
                if true_tm.shape != (num_blocks_h, num_blocks_w):
                    raise ValueError(
                        "true_tamper_map 2D shape must match block grid "
                        f"({num_blocks_h}, {num_blocks_w}), got {true_tm.shape}."
                    )
                true_tamper_1d = true_tm.flatten()
            elif true_tm.ndim == 1:
                if true_tm.shape[0] != num_blocks:
                    raise ValueError(
                        f"true_tamper_map 1D length must be {num_blocks}, got {true_tm.shape[0]}."
                    )
                true_tamper_1d = true_tm
            else:
                raise ValueError("true_tamper_map must be a 1D or 2D boolean array.")

        # Backward-compatible heuristic: derive ground truth from a reference image.
        # We intentionally ignore watermark-only changes (<= 15 per pixel) since embedding
        # only alters the lower 4 bits of pixels.
        elif original_image is not None:
            diff = np.abs(stego_image.astype(np.int16) - original_image.astype(np.int16))
            true_tamper_pixels = diff > 15

            # Convert pixel-level tamper mask to block-level.
            # Shape: (Bh, bs, Bw, bs) -> (Bh, Bw)
            bh = num_blocks_h
            bw = num_blocks_w
            bs = self.block_size
            true_blocks = true_tamper_pixels.reshape(bh, bs, bw, bs).any(axis=(1, 3))
            true_tamper_1d = true_blocks.flatten()

        if true_tamper_1d is not None:
            metrics = compute_detection_metrics(tamper_map_1d, true_tamper_1d)
        
        print("[Auth] ✓ Authentication complete")
        
        return {
            'tamper_map': tamper_map,
            'tamper_map_visual': tamper_visual,
            'tamper_1d': tamper_map_1d,
            'recovered_image': recovered_image,
            'psnr_stego': psnr_stego,
            'psnr_recovered': psnr_recovered,
            'tamper_ratio': float(tamper_ratio),
            'metrics': metrics
        }
    
    def _extract_block_watermark(self, stego_image: np.ndarray,
                                 block_row: int, block_col: int,
                                 BD: np.ndarray, WT: np.ndarray,
                                 block_size: int) -> tuple:
        """Extract 24-bit watermark from one block."""
        
        pixel_pairs = [
            [(0, 0), (0, 1)],
            [(0, 2), (0, 3)],
            [(1, 0), (1, 1)],
            [(1, 2), (1, 3)],
            [(2, 0), (2, 1)],
            [(2, 2), (2, 3)],
            [(3, 0), (3, 1)],
            [(3, 2), (3, 3)]
        ]
        
        ac_bits = []
        ri1_bits = []
        ri2_bits = []
        
        for coord1, coord2 in pixel_pairs:
            r1, c1 = coord1
            r2, c2 = coord2
            
            p1_row = block_row * block_size + r1
            p1_col = block_col * block_size + c1
            p2_row = block_row * block_size + r2
            p2_col = block_col * block_size + c2
            
            P1 = int(stego_image[p1_row, p1_col])
            P2 = int(stego_image[p2_row, p2_col])
            
            ac_bit, ri1_bit, ri2_bit = extract_3bit_watermark(P1, P2, BD, WT)
            ac_bits.append(ac_bit)
            ri1_bits.append(ri1_bit)
            ri2_bits.append(ri2_bit)
        
        # Reconstruct 8-bit values from bits
        ac = int(np.packbits(np.array(ac_bits, dtype=bool))[0])
        ri1 = int(np.packbits(np.array(ri1_bits, dtype=bool))[0])
        ri2 = int(np.packbits(np.array(ri2_bits, dtype=bool))[0])
        
        return ac, ri1, ri2
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Same preprocessing as embedding."""
        h, w = image.shape
        rng = np.random.default_rng(self.seed_gamma)
        bit_stream = rng.integers(0, 2, size=4 * h * w, dtype=np.uint8)
        
        preprocessed = image.copy().astype(np.uint32)
        for i in range(h * w):
            nibble = 0
            for k in range(4):
                nibble = (nibble << 1) | bit_stream[4*i + k]
            preprocessed.flat[i] = (preprocessed.flat[i] & 0xF0) | nibble
        
        return preprocessed.astype(np.uint8)
    
    def _refine_tamper_map(self, tamper_map: np.ndarray) -> np.ndarray:
        """Apply 3x3 neighborhood-based refinement."""
        h, w = tamper_map.shape
        refined = tamper_map.copy()
        
        for i in range(h):
            for j in range(w):
                if refined[i, j]:
                    continue  # Already marked as tampered
                
                # Check 3x3 neighborhood (with boundary handling)
                # Mark as tampered if 2+ neighboring blocks in same row/column are tampered
                
                # Horizontal neighbors
                left = refined[i, j-1] if j > 0 else False
                right = refined[i, j+1] if j < w-1 else False
                if left and right:
                    refined[i, j] = True
                
                # Vertical neighbors
                top = refined[i-1, j] if i > 0 else False
                bottom = refined[i+1, j] if i < h-1 else False
                if top and bottom:
                    refined[i, j] = True
                
                # Diagonal neighbors
                tl = refined[i-1, j-1] if i > 0 and j > 0 else False
                br = refined[i+1, j+1] if i < h-1 and j < w-1 else False
                if tl and br:
                    refined[i, j] = True
                
                tr = refined[i-1, j+1] if i > 0 and j < w-1 else False
                bl = refined[i+1, j-1] if i < h-1 and j > 0 else False
                if tr and bl:
                    refined[i, j] = True
        
        return refined
    
    def _interpolate_recovery(self, recovered_image: np.ndarray,
                             block_row: int, block_col: int,
                             tamper_map: np.ndarray,
                             block_size: int) -> np.ndarray:
        """Interpolate recovery from neighbor blocks when both sources are tampered."""
        h, w = tamper_map.shape
        neighbor_blocks = []
        
        # 8-connected neighbors
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                if di == 0 and dj == 0:
                    continue
                ni, nj = block_row + di, block_col + dj
                if 0 <= ni < h and 0 <= nj < w and not tamper_map[ni, nj]:
                    r_start = ni * block_size
                    c_start = nj * block_size
                    neighbor_blocks.append(
                        recovered_image[r_start:r_start+block_size,
                                      c_start:c_start+block_size].copy()
                    )
        
        if neighbor_blocks:
            # Average valid neighbors
            neighbor_array = np.array(neighbor_blocks, dtype=np.float32)
            recovery_block = np.mean(neighbor_array, axis=0).astype(np.uint8)
        else:
            # No valid neighbors, use neutral gray
            recovery_block = np.ones((block_size, block_size), dtype=np.uint8) * 128
        
        return recovery_block


if __name__ == "__main__":
    from src.utils import generate_synthetic_grayscale_image
    from src.watermark_embed import WatermarkEmbedder
    
    # Test authentication
    test_img = generate_synthetic_grayscale_image(128, 128)
    
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(test_img)
    
    authenticator = WatermarkAuthenticator()
    result = authenticator.authenticate_and_recover(
        stego, metadata['vq_codebook'], test_img
    )
    
    print(f"Tamper ratio: {result['tamper_ratio']}")
    print(f"Metrics: {result['metrics']}")
