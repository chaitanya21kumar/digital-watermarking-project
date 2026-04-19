"""MOD-3: Entropy-Adaptive Block Mapping - Content-aware mapping."""

import numpy as np
from scipy.stats import entropy
from src.watermark_embed import WatermarkEmbedder
from src.block_mapping import generate_block_mapping


class AdaptiveBlockMapper:
    """
    Content-aware block mapping based on local entropy.
    
    Novelty: Random mapping ignores image content. High-entropy blocks may have
    recovery info in low-entropy blocks. This ensures high-entropy blocks map to
    similar-entropy blocks for better recovery quality.
    """
    
    @staticmethod
    def compute_block_entropies(image: np.ndarray, block_size: int = 4) -> np.ndarray:
        """
        Compute Shannon entropy for each 4x4 block.
        
        Args:
            image: uint8 grayscale image
            block_size: Block size (default 4)
        
        Returns:
            Array of entropy values, shape (num_blocks_h, num_blocks_w)
        """
        h, w = image.shape
        num_blocks_h = h // block_size
        num_blocks_w = w // block_size
        entropies = np.zeros((num_blocks_h, num_blocks_w))
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                block = image[i*block_size:(i+1)*block_size,
                            j*block_size:(j+1)*block_size]
                
                # Compute histogram (256 bins for pixel values)
                hist, _ = np.histogram(block.flatten(), bins=256, range=(0, 256))
                hist = hist / hist.sum()  # Normalize
                
                # Compute entropy (exclude zero bins)
                hist = hist[hist > 0]
                block_entropy = -np.sum(hist * np.log2(hist + 1e-10))
                entropies[i, j] = block_entropy
        
        return entropies
    
    @staticmethod
    def generate_adaptive_mapping(image: np.ndarray, seed: int, 
                                  block_size: int = 4) -> np.ndarray:
        """
        Generate entropy-grouped permutation mapping.
        
        Algorithm:
        1. Compute entropy for all blocks
        2. Sort blocks into entropy quartiles
        3. Within each quartile, apply random permutation
        
        Args:
            image: uint8 grayscale image
            seed: Random seed
            block_size: Block size
        
        Returns:
            Mapping array of length num_blocks
        """
        entropies_2d = AdaptiveBlockMapper.compute_block_entropies(image, block_size)
        h, w = entropies_2d.shape
        num_blocks = h * w
        
        # Flatten entropies
        entropies_flat = entropies_2d.flatten()
        
        # Get entropy quartile bins
        q1 = np.percentile(entropies_flat, 25)
        q2 = np.percentile(entropies_flat, 50)
        q3 = np.percentile(entropies_flat, 75)
        
        # Assign blocks to quartiles
        quartiles = np.zeros(num_blocks, dtype=int)
        for i in range(num_blocks):
            if entropies_flat[i] <= q1:
                quartiles[i] = 0
            elif entropies_flat[i] <= q2:
                quartiles[i] = 1
            elif entropies_flat[i] <= q3:
                quartiles[i] = 2
            else:
                quartiles[i] = 3
        
        # Create adaptive mapping
        rng = np.random.default_rng(seed)
        mapping = np.zeros(num_blocks, dtype=np.uint32)
        
        for q in range(4):
            q_indices = np.where(quartiles == q)[0]
            q_permutation = rng.permutation(q_indices)
            mapping[q_indices] = q_permutation
        
        return mapping


class AdaptiveWatermarkEmbedder(WatermarkEmbedder):
    """
    Watermark embedder with entropy-adaptive block mapping.
    """
    
    def embed(self, image: np.ndarray) -> tuple:
        """
        Full embedding pipeline with adaptive block mapping.
        """
        image = image.astype(np.uint8)
        
        from src.utils import crop_to_block_size
        image = crop_to_block_size(image, self.block_size)
        h, w = image.shape
        
        print(f"[Embed-Adaptive] Image size: {h}x{w}")
        
        # PHASE 1: Preprocessing
        print("[Embed-Adaptive] Phase 1: Preprocessing...")
        preprocessed_image = self._preprocess_image(image)
        
        # PHASE 2: AMBTC
        print("[Embed-Adaptive] Phase 2: AMBTC compression...")
        from src.ambtc import AMBTC
        ambtc = AMBTC(self.block_size)
        compressed_blocks = ambtc.compress(preprocessed_image)
        
        auth_codes = np.zeros(len(compressed_blocks), dtype=np.uint8)
        for i, block_data in enumerate(compressed_blocks):
            auth_codes[i] = ambtc.generate_auth_code(
                block_data['xL'], block_data['xH'], block_data['BM']
            )
        
        # PHASE 3: VQ
        print("[Embed-Adaptive] Phase 3: VQ training and encoding...")
        from src.vq import VectorQuantizer
        vq = VectorQuantizer(self.vq_codebook_size, self.block_size)
        vq.train(image)
        vq_indices = vq.encode(image)
        
        num_blocks_h, num_blocks_w = vq_indices.shape
        num_blocks = num_blocks_h * num_blocks_w
        
        # PHASE 4: Adaptive mapping
        print("[Embed-Adaptive] Phase 4: Entropy-adaptive mapping generation...")
        map1 = AdaptiveBlockMapper.generate_adaptive_mapping(image, self.seed_gamma1, self.block_size)
        map2 = AdaptiveBlockMapper.generate_adaptive_mapping(image, self.seed_gamma2, self.block_size)
        
        # PHASE 5: Watermark embedding
        print("[Embed-Adaptive] Phase 5: Watermark embedding...")
        stego_image = image.copy()
        from src.bd_wt_tables import generate_bd_table, generate_wt_table
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        linear_idx = 0
        for block_row in range(num_blocks_h):
            for block_col in range(num_blocks_w):
                src1_idx = map1[linear_idx]
                src2_idx = map2[linear_idx]
                
                ac = auth_codes[src1_idx]
                ri1 = vq_indices.flat[src1_idx]
                ri2 = vq_indices.flat[src2_idx]
                
                self._embed_block_watermark(
                    stego_image, block_row, block_col,
                    ac, ri1, ri2, BD, WT, self.block_size
                )
                
                linear_idx += 1
        
        print("[Embed-Adaptive] ✓ Embedding complete")
        
        metadata = {
            'seeds': (self.seed_gamma, self.seed_gamma1, self.seed_gamma2),
            'image_shape': (h, w),
            'vq_codebook': vq.codebook,
            'block_size': self.block_size,
            'auth_codes': auth_codes,
            'vq_indices': vq_indices,
            'map1': map1,
            'map2': map2,
            'mapping_type': 'adaptive'
        }
        
        return stego_image, metadata


if __name__ == "__main__":
    from src.utils import generate_synthetic_grayscale_image
    
    test_img = generate_synthetic_grayscale_image(256, 256)
    
    # Compute entropies
    entropies = AdaptiveBlockMapper.compute_block_entropies(test_img)
    print(f"Entropy map shape: {entropies.shape}")
    print(f"Min entropy: {entropies.min():.2f}, Max entropy: {entropies.max():.2f}")
    
    # Test adaptive mapping
    map_adaptive = AdaptiveBlockMapper.generate_adaptive_mapping(test_img, seed=42)
    print(f"Adaptive mapping shape: {map_adaptive.shape}")
    print(f"All unique: {len(np.unique(map_adaptive)) == len(map_adaptive)}")
    
    # Compare with random mapping
    map_random = np.random.default_rng(42).permutation(len(map_adaptive))
    print(f"Random mapping shape: {map_random.shape}")
