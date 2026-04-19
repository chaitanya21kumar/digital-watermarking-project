"""Tests for attack simulations."""

import numpy as np
from src.utils import generate_synthetic_grayscale_image, crop_to_block_size
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator


def cutting_attack(stego_image: np.ndarray,
                  start_row: int, start_col: int,
                  height: int, width: int,
                  fill_value: int = 128) -> tuple:
    """
    Simulate cutting/cropping attack by replacing a rectangular region.
    
    Args:
        stego_image: Watermarked image
        start_row, start_col: Top-left corner of attack region
        height, width: Size of attack region (should be multiples of 4)
        fill_value: Value to fill the region with
    
    Returns:
        (attacked_image, true_tamper_map) where true_tamper_map is block-level
    """
    block_size = 4
    attacked = stego_image.copy()
    
    # Replace the region
    attacked[start_row:start_row+height, start_col:start_col+width] = fill_value
    
    # Create true tamper map at block level
    h, w = stego_image.shape
    num_blocks_h = h // block_size
    num_blocks_w = w // block_size
    true_tamper_map = np.zeros((num_blocks_h, num_blocks_w), dtype=bool)
    
    # Mark blocks that overlap with the attacked region
    start_block_row = start_row // block_size
    start_block_col = start_col // block_size
    end_block_row = (start_row + height + block_size - 1) // block_size
    end_block_col = (start_col + width + block_size - 1) // block_size
    
    true_tamper_map[start_block_row:end_block_row,
                    start_block_col:end_block_col] = True
    
    return attacked, true_tamper_map


def copy_paste_attack(stego_image: np.ndarray,
                     src_row: int, src_col: int,
                     dst_row: int, dst_col: int,
                     height: int, width: int,
                     source_image: np.ndarray = None) -> tuple:
    """
    Simulate copy-paste attack by copying from another authenticated image.
    
    Args:
        stego_image: Target watermarked image (to paste into)
        src_row, src_col: Top-left corner of source region in source image
        dst_row, dst_col: Top-left corner of destination in stego_image
        height, width: Size of region
        source_image: Optional source authenticated image (default: generate fresh)
    
    Returns:
        (attacked_image, true_tamper_map)
    """
    block_size = 4
    attacked = stego_image.copy()
    
    # If no source provided, generate fresh authenticated image
    if source_image is None:
        h, w = stego_image.shape
        source_original = generate_synthetic_grayscale_image(h, w, seed=999)
        source_original = crop_to_block_size(source_original, block_size)
        
        embedder = WatermarkEmbedder(seed_gamma=99, seed_gamma1=199, seed_gamma2=299)
        source_image, _ = embedder.embed(source_original)
    
    # Copy region from source to destination
    attacked[dst_row:dst_row+height, dst_col:dst_col+width] = \
        source_image[src_row:src_row+height, src_col:src_col+width]
    
    # Create true tamper map
    h, w = stego_image.shape
    num_blocks_h = h // block_size
    num_blocks_w = w // block_size
    true_tamper_map = np.zeros((num_blocks_h, num_blocks_w), dtype=bool)
    
    # Mark blocks in destination region
    start_block_row = dst_row // block_size
    start_block_col = dst_col // block_size
    end_block_row = (dst_row + height + block_size - 1) // block_size
    end_block_col = (dst_col + width + block_size - 1) // block_size
    
    true_tamper_map[start_block_row:end_block_row,
                    start_block_col:end_block_col] = True
    
    return attacked, true_tamper_map


class TestCuttingAttack:
    
    def test_cutting_attack_small(self):
        """Test small cutting attack (32x32)."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # 32x32 attack at center
        attacked, true_tamper = cutting_attack(stego, 48, 48, 32, 32, fill_value=100)
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        pred_tamper = result['tamper_map']
        
        # Check detection
        assert result['tamper_ratio'] > 0.05
        assert np.any(pred_tamper)
        
        # Check metrics
        metrics = result['metrics']
        assert metrics['TPR'] > 0.8  # Should detect most tampered blocks
    
    def test_cutting_attack_large(self):
        """Test large cutting attack (64x64)."""
        img = generate_synthetic_grayscale_image(256, 256)
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # 64x64 attack
        attacked, true_tamper = cutting_attack(stego, 96, 96, 64, 64)
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        assert result['tamper_ratio'] > 0.05


class TestCopyPasteAttack:
    
    def test_copy_paste_attack(self):
        """Test copy-paste attack."""
        img1 = generate_synthetic_grayscale_image(128, 128, seed=1)
        img2 = generate_synthetic_grayscale_image(128, 128, seed=2)
        
        embedder = WatermarkEmbedder()
        stego1, metadata1 = embedder.embed(img1)
        stego2, metadata2 = embedder.embed(img2)
        
        # Copy-paste from stego2 to stego1
        attacked, true_tamper = copy_paste_attack(
            stego1, 32, 32, 32, 32, 32, 32,
            source_image=stego2
        )
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata1['vq_codebook'], img1
        )
        
        # Should detect tampering
        assert result['tamper_ratio'] > 0.01


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
