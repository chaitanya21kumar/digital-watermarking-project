"""MOD-4: Multi-Level Hierarchical Recovery - Three-tier recovery cascade."""

import numpy as np
from src.watermark_extract import WatermarkAuthenticator


class MultiLevelRecoveryAuthenticator(WatermarkAuthenticator):
    """
    Enhanced authenticator with three-tier recovery cascade.
    
    Novelty: Paper's two-tier recovery fails when both Map1 and Map2 sources are tampered.
    This adds interpolation-based tier-3 recovery for robustness at high tamper rates.
    """
    
    def authenticate_and_recover(self, stego_image: np.ndarray,
                                 vq_codebook: np.ndarray,
                                 original_image: np.ndarray = None) -> dict:
        """
        Full authentication and recovery with three-tier cascade.
        """
        stego_image = stego_image.astype(np.uint8)
        
        from src.utils import crop_to_block_size
        stego_image = crop_to_block_size(stego_image, self.block_size)
        h, w = stego_image.shape
        
        print(f"[Auth-3Tier] Image size: {h}x{w}")
        
        from src.bd_wt_tables import generate_bd_table, generate_wt_table
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        # PHASE 1: Extract watermarks
        print("[Auth-3Tier] Phase 1: Extracting watermarks...")
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
        
        # PHASE 2: Preprocess and recompute auth codes
        print("[Auth-3Tier] Phase 2: Recomputing auth codes...")
        preprocessed = self._preprocess_image(stego_image)
        from src.ambtc import AMBTC
        ambtc = AMBTC(self.block_size)
        compressed_blocks = ambtc.compress(preprocessed)
        
        ac_recomp = np.zeros(num_blocks, dtype=np.uint8)
        for i, block_data in enumerate(compressed_blocks):
            ac_recomp[i] = ambtc.generate_auth_code(
                block_data['xL'], block_data['xH'], block_data['BM']
            )
        
        # PHASE 3: Tamper detection
        print("[Auth-3Tier] Phase 3: Identifying tampered blocks...")
        from src.block_mapping import generate_block_mapping
        map1 = generate_block_mapping(num_blocks, self.seed_gamma1)
        map2 = generate_block_mapping(num_blocks, self.seed_gamma2)
        
        tamper_map_1d = np.zeros(num_blocks, dtype=bool)
        for block_idx in range(num_blocks):
            src1_idx = map1[block_idx]
            if ac_ext[block_idx] != ac_recomp[src1_idx]:
                tamper_map_1d[block_idx] = True
        
        # PHASE 4: Refined tamper detection
        print("[Auth-3Tier] Phase 4: Refining tamper detection...")
        tamper_map = tamper_map_1d.reshape(num_blocks_h, num_blocks_w)
        tamper_map = self._refine_tamper_map(tamper_map)
        tamper_map_1d = tamper_map.flatten()
        
        # PHASE 5: Three-tier recovery
        print("[Auth-3Tier] Phase 5: Three-tier hierarchical recovery...")
        from src.vq import VectorQuantizer
        vq = VectorQuantizer(codebook_size=256, block_size=self.block_size)
        vq.codebook = vq_codebook
        
        recovered_image = stego_image.copy()
        tier_map = np.zeros(num_blocks, dtype=np.uint8)  # 1, 2, or 3
        
        for block_idx in range(num_blocks):
            if not tamper_map_1d[block_idx]:
                tier_map[block_idx] = 0  # Not tampered
                continue
            
            block_row = block_idx // num_blocks_w
            block_col = block_idx % num_blocks_w
            
            src1_idx = map1[block_idx]
            src2_idx = map2[block_idx]
            
            # TIER 1: Use RI1 from Map1 source
            if not tamper_map_1d[src1_idx]:
                vq_idx = ri1_ext[block_idx]
                recovery_block = vq.decode_block(vq_idx)
                tier_map[block_idx] = 1
            # TIER 2: Use RI2 from Map2 source
            elif not tamper_map_1d[src2_idx]:
                vq_idx = ri2_ext[block_idx]
                recovery_block = vq.decode_block(vq_idx)
                tier_map[block_idx] = 2
            # TIER 3: Interpolation from neighbors + VQ refinement
            else:
                recovery_block = self._tier3_interpolation(
                    recovered_image, block_row, block_col,
                    tamper_map, vq, self.block_size
                )
                tier_map[block_idx] = 3
            
            # Write recovered block
            r_start = block_row * self.block_size
            c_start = block_col * self.block_size
            recovered_image[r_start:r_start+self.block_size,
                          c_start:c_start+self.block_size] = recovery_block
        
        # Create visual tamper map
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
        print("[Auth-3Tier] Computing metrics...")
        from src.metrics import psnr, compute_detection_metrics
        
        psnr_stego = psnr(stego_image, original_image) if original_image is not None else None
        psnr_recovered = psnr(recovered_image, original_image) if original_image is not None else None
        
        tamper_ratio = np.sum(tamper_map_1d) / num_blocks
        
        metrics = {
            'TP': 0, 'TN': 0, 'FP': 0, 'FN': 0,
            'TPR': 0, 'FPR': 0, 'FNR': 0, 'Accuracy': 0
        }
        
        if original_image is not None:
            true_tamper = (stego_image != original_image)
            true_tamper = crop_to_block_size(true_tamper, self.block_size)
            
            true_tamper_1d = np.zeros(num_blocks, dtype=bool)
            for block_idx in range(num_blocks):
                block_row = block_idx // num_blocks_w
                block_col = block_idx % num_blocks_w
                r_start = block_row * self.block_size
                c_start = block_col * self.block_size
                block = true_tamper[r_start:r_start+self.block_size,
                                   c_start:c_start+self.block_size]
                if np.any(block):
                    true_tamper_1d[block_idx] = True
            
            metrics = compute_detection_metrics(tamper_map_1d, true_tamper_1d)
        
        print("[Auth-3Tier] ✓ Three-tier authentication complete")
        
        # Tier distribution
        tier_dist = {
            'tier1_count': np.sum(tier_map == 1),
            'tier2_count': np.sum(tier_map == 2),
            'tier3_count': np.sum(tier_map == 3)
        }
        
        return {
            'tamper_map': tamper_map,
            'tamper_map_visual': tamper_visual,
            'tamper_1d': tamper_map_1d,
            'recovered_image': recovered_image,
            'tier_map': tier_map,
            'tier_distribution': tier_dist,
            'psnr_stego': psnr_stego,
            'psnr_recovered': psnr_recovered,
            'tamper_ratio': float(tamper_ratio),
            'metrics': metrics
        }
    
    def _tier3_interpolation(self, recovered_image: np.ndarray,
                            block_row: int, block_col: int,
                            tamper_map: np.ndarray,
                            vq,
                            block_size: int) -> np.ndarray:
        """
        Tier-3 recovery using weighted interpolation from valid neighbors
        + VQ nearest-neighbor refinement.
        """
        h, w = tamper_map.shape
        neighbor_blocks = []
        neighbor_distances = []
        
        # 8-connected neighbors
        for di in [-1, 0, 1]:
            for dj in [-1, 0, 1]:
                if di == 0 and dj == 0:
                    continue
                ni, nj = block_row + di, block_col + dj
                if 0 <= ni < h and 0 <= nj < w and not tamper_map[ni, nj]:
                    r_start = ni * block_size
                    c_start = nj * block_size
                    block = recovered_image[r_start:r_start+block_size,
                                          c_start:c_start+block_size].copy()
                    neighbor_blocks.append(block)
                    # Distance weight (diagonal neighbors have larger distance)
                    dist = np.sqrt(di**2 + dj**2)
                    neighbor_distances.append(dist)
        
        if neighbor_blocks:
            # Weighted average by inverse distance
            distances = np.array(neighbor_distances)
            weights = 1.0 / (distances + 0.1)  # Avoid division by zero
            weights = weights / weights.sum()
            
            # Weighted mean of neighbors
            neighbor_array = np.array(neighbor_blocks, dtype=np.float32)
            tier3_block = np.average(neighbor_array, axis=0, weights=weights)
            
            # Refinement: blend with VQ nearest neighbor
            # Find VQ codeword closest to tier3_block
            tier3_vector = tier3_block.flatten().astype(np.float32)
            distances_vq = np.linalg.norm(vq.codebook - tier3_vector, axis=1)
            nearest_idx = np.argmin(distances_vq)
            vq_block = vq.decode_block(nearest_idx).astype(np.float32)
            
            # Blend: 70% interpolated + 30% VQ
            refined_block = (0.7 * tier3_block + 0.3 * vq_block).astype(np.uint8)
            return refined_block
        else:
            # No valid neighbors, use global mean of valid blocks
            valid_blocks = []
            for i in range(h * block_size):
                for j in range(w * block_size):
                    block_idx = (i // block_size) * w + (j // block_size)
                    if block_idx < len(tamper_map.flatten()) and not tamper_map.flatten()[block_idx]:
                        bi = i // block_size
                        bj = j // block_size
                        r_start = bi * block_size
                        c_start = bj * block_size
                        if r_start + block_size <= recovered_image.shape[0] and \
                           c_start + block_size <= recovered_image.shape[1]:
                            block = recovered_image[r_start:r_start+block_size,
                                                  c_start:c_start+block_size]
                            valid_blocks.append(block)
            
            if valid_blocks:
                avg_block = np.mean(valid_blocks, axis=0).astype(np.uint8)
                return np.ones((block_size, block_size), dtype=np.uint8) * avg_block.mean()
            else:
                return np.ones((block_size, block_size), dtype=np.uint8) * 128


if __name__ == "__main__":
    from src.utils import generate_synthetic_grayscale_image
    from src.watermark_embed import WatermarkEmbedder
    
    test_img = generate_synthetic_grayscale_image(128, 128)
    
    embedder = WatermarkEmbedder()
    stego, metadata = embedder.embed(test_img)
    
    authenticator = MultiLevelRecoveryAuthenticator()
    result = authenticator.authenticate_and_recover(
        stego, metadata['vq_codebook'], test_img
    )
    
    print(f"Tier distribution: {result['tier_distribution']}")
    print(f"Tamper ratio: {result['tamper_ratio']}")
