"""Watermark embedding algorithm (paper-faithful implementation)."""

import numpy as np
from src.ambtc import AMBTC
from src.vq import VectorQuantizer
from src.bd_wt_tables import generate_bd_table, generate_wt_table, embed_3bit_watermark
from src.block_mapping import generate_block_mapping, linear_to_2d_block_index
from src.utils import crop_to_block_size


class WatermarkEmbedder:
    """Fragile watermarking embedder based on AMBTC + VQ."""
    
    def __init__(self, seed_gamma=42, seed_gamma1=123, seed_gamma2=456,
                 block_size=4, vq_codebook_size=256):
        self.seed_gamma = seed_gamma
        self.seed_gamma1 = seed_gamma1
        self.seed_gamma2 = seed_gamma2
        self.block_size = block_size
        self.vq_codebook_size = vq_codebook_size
    
    def embed(self, image: np.ndarray) -> tuple:
        """
        Full embedding pipeline.
        
        Args:
            image: uint8 grayscale image
        
        Returns:
            (stego_image, metadata) where metadata contains seeds, shapes, codebook, etc.
        """
        image = image.astype(np.uint8)
        
        # Crop to block size
        image = crop_to_block_size(image, self.block_size)
        h, w = image.shape
        
        print(f"[Embed] Image size: {h}x{w}")
        
        # PHASE 1: Preprocessing
        print("[Embed] Phase 1: Preprocessing...")
        preprocessed_image = self._preprocess_image(image)
        
        # PHASE 2: AMBTC on preprocessed image
        print("[Embed] Phase 2: AMBTC compression...")
        ambtc = AMBTC(self.block_size)
        compressed_blocks = ambtc.compress(preprocessed_image)
        
        # Generate auth codes for all blocks
        auth_codes = np.zeros(len(compressed_blocks), dtype=np.uint8)
        for i, block_data in enumerate(compressed_blocks):
            auth_codes[i] = ambtc.generate_auth_code(
                block_data['xL'], block_data['xH'], block_data['BM']
            )
        
        # PHASE 3: VQ on original image
        print("[Embed] Phase 3: VQ training and encoding...")
        vq = VectorQuantizer(self.vq_codebook_size, self.block_size)
        vq.train(image)
        vq_indices = vq.encode(image)
        
        num_blocks_h, num_blocks_w = vq_indices.shape
        num_blocks = num_blocks_h * num_blocks_w
        
        # PHASE 4: Generate block mappings
        print("[Embed] Phase 4: Block mapping generation...")
        map1 = generate_block_mapping(num_blocks, self.seed_gamma1)
        map2 = generate_block_mapping(num_blocks, self.seed_gamma2)
        
        # PHASE 5: Watermark embedding
        print("[Embed] Phase 5: Watermark embedding...")
        stego_image = image.copy()
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        linear_idx = 0
        for block_row in range(num_blocks_h):
            for block_col in range(num_blocks_w):
                # Get source blocks from mappings
                src1_idx = map1[linear_idx]
                src2_idx = map2[linear_idx]
                
                # Get watermark bits
                ac = auth_codes[src1_idx]
                ri1 = vq_indices.flat[src1_idx]
                ri2 = vq_indices.flat[src2_idx]
                
                # Embed 24 bits into 8 pixel pairs
                self._embed_block_watermark(
                    stego_image, block_row, block_col,
                    ac, ri1, ri2, BD, WT, self.block_size
                )
                
                linear_idx += 1
        
        print("[Embed] ✓ Embedding complete")
        
        # Prepare metadata
        metadata = {
            'seeds': (self.seed_gamma, self.seed_gamma1, self.seed_gamma2),
            'image_shape': (h, w),
            'vq_codebook': vq.codebook,
            'block_size': self.block_size,
            'auth_codes': auth_codes,
            'vq_indices': vq_indices,
            'map1': map1,
            'map2': map2
        }
        
        return stego_image, metadata
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Replace 4 LSBs of each pixel with random bits."""
        h, w = image.shape
        rng = np.random.default_rng(self.seed_gamma)
        
        # Generate random bit stream
        bit_stream = rng.integers(0, 2, size=4 * h * w, dtype=np.uint8)
        
        preprocessed = image.copy().astype(np.uint32)
        
        for i in range(h * w):
            # Extract 4 random bits to form nibble
            nibble = 0
            for k in range(4):
                nibble = (nibble << 1) | bit_stream[4*i + k]
            
            # Replace 4 LSBs: keep upper 4 bits, replace lower 4
            preprocessed.flat[i] = (preprocessed.flat[i] & 0xF0) | nibble
        
        return preprocessed.astype(np.uint8)
    
    def _embed_block_watermark(self, stego_image: np.ndarray,
                                block_row: int, block_col: int,
                                ac: int, ri1: int, ri2: int,
                                BD: np.ndarray, WT: np.ndarray,
                                block_size: int):
        """Embed 24-bit watermark into one 4x4 block using 8 pixel pairs."""
        
        # Extract bit representation of watermark values
        ac_bits = [(ac >> (7-k)) & 1 for k in range(8)]      # bits 7..0
        ri1_bits = [(ri1 >> (7-k)) & 1 for k in range(8)]    # bits 7..0
        ri2_bits = [(ri2 >> (7-k)) & 1 for k in range(8)]    # bits 7..0
        
        # 8 pixel pairs in block
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
        
        for pair_idx, (coord1, coord2) in enumerate(pixel_pairs):
            r1, c1 = coord1
            r2, c2 = coord2
            
            # Global pixel indices
            p1_row = block_row * block_size + r1
            p1_col = block_col * block_size + c1
            p2_row = block_row * block_size + r2
            p2_col = block_col * block_size + c2
            
            # Get original pixels
            P1 = int(stego_image[p1_row, p1_col])
            P2 = int(stego_image[p2_row, p2_col])
            
            # Extract 3 watermark bits for this pair
            ac_bit = ac_bits[pair_idx]
            ri1_bit = ri1_bits[pair_idx]
            ri2_bit = ri2_bits[pair_idx]
            
            # Embed 3-bit watermark
            P1_new, P2_new = embed_3bit_watermark(
                P1, P2, ac_bit, ri1_bit, ri2_bit, BD, WT
            )
            
            # Write back modified pixels
            stego_image[p1_row, p1_col] = P1_new
            stego_image[p2_row, p2_col] = P2_new


if __name__ == "__main__":
    # Test embedding
    from src.utils import generate_synthetic_grayscale_image
    
    test_img = generate_synthetic_grayscale_image(128, 128)
    
    embedder = WatermarkEmbedder(seed_gamma=42, seed_gamma1=123, seed_gamma2=456)
    stego, metadata = embedder.embed(test_img)
    
    print(f"Stego image shape: {stego.shape}")
    print(f"Metadata keys: {list(metadata.keys())}")
