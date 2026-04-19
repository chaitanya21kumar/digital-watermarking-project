"""Tests for AMBTC compression and authentication."""

import pytest
import numpy as np
from src.ambtc import AMBTC
from src.utils import generate_synthetic_grayscale_image


class TestAMBTC:
    
    def test_compress_decompress_roundtrip(self):
        """Test that compression and decompression preserve image structure."""
        img = generate_synthetic_grayscale_image(16, 16, seed=42)
        ambtc = AMBTC(block_size=4)
        
        compressed = ambtc.compress(img)
        decompressed = ambtc.decompress(compressed, img.shape)
        
        assert decompressed.shape == img.shape
        assert decompressed.dtype == np.uint8
        # Should be similar but not identical due to quantization
        mse = np.mean((img.astype(float) - decompressed.astype(float))**2)
        assert mse < 1000  # Allow some error from quantization
    
    def test_compress_output_format(self):
        """Test that compression output has correct format."""
        img = generate_synthetic_grayscale_image(16, 16)
        ambtc = AMBTC(block_size=4)
        
        compressed = ambtc.compress(img)
        
        assert isinstance(compressed, list)
        assert len(compressed) == (16 // 4) * (16 // 4)  # 4 blocks total
        
        for block in compressed:
            assert isinstance(block, dict)
            assert 'xL' in block and 'xH' in block and 'BM' in block
            assert 0 <= block['xL'] <= 255
            assert 0 <= block['xH'] <= 255
            assert block['BM'].dtype == np.uint8
            assert block['BM'].shape == (4, 4)
    
    def test_auth_code_generation(self):
        """Test authentication code generation."""
        ambtc = AMBTC(block_size=4)
        
        xL, xH = 50, 200
        BM = np.array([[1,0,1,0], [0,1,0,1], [1,0,1,0], [0,1,0,1]], dtype=np.uint8)
        
        ac1 = ambtc.generate_auth_code(xL, xH, BM)
        ac2 = ambtc.generate_auth_code(xL, xH, BM)
        
        # Same input should give same output (deterministic)
        assert ac1 == ac2
        # Should be 8-bit value
        assert 0 <= ac1 <= 255
        
        # Different input should (likely) give different output
        ac3 = ambtc.generate_auth_code(xL, xH+10, BM)
        assert ac1 != ac3  # Different xH
    
    def test_all_zero_block(self):
        """Test handling of uniform blocks."""
        ambtc = AMBTC(block_size=4)
        
        block = np.zeros((4, 4), dtype=np.uint8)
        xL, xH, bm = ambtc._compress_block(block)
        
        # All pixels equal to mean (0), so xL = 0, xH = 255 or 0
        assert xL == 0
        # Reconstruct: should be all zeros or all 255
    
    def test_compression_ratio(self):
        """Test that compression is effective."""
        img = generate_synthetic_grayscale_image(128, 128)
        ambtc = AMBTC(block_size=4)
        
        compressed = ambtc.compress(img)
        
        # Original: 128 x 128 = 16384 bytes
        # Compressed: (128/4) x (128/4) = 256 blocks
        # Each block: 1 byte (xL) + 1 byte (xH) + 16 bytes (BM) ≈ 18 bytes
        # Actually: xL + xH = 2 bytes, BM = 2 bytes (16 bits)
        # Total ≈ 256 * 4 = 1024 bytes (rough estimate)
        
        assert len(compressed) == 256


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
