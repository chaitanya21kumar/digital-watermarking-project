"""Tests for Vector Quantization."""

import pytest
import numpy as np
from src.vq import VectorQuantizer
from src.utils import generate_synthetic_grayscale_image


class TestVectorQuantizer:
    
    def test_training(self):
        """Test VQ codebook training."""
        img = generate_synthetic_grayscale_image(64, 64)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        
        assert vq.codebook is not None
        assert vq.codebook.shape == (256, 16)
        assert vq.codebook.dtype == np.uint8
        assert np.all((vq.codebook >= 0) & (vq.codebook <= 255))
    
    def test_encoding(self):
        """Test VQ encoding."""
        img = generate_synthetic_grayscale_image(64, 64)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        indices = vq.encode(img)
        
        assert indices.shape == (64 // 4, 64 // 4)  # (16, 16)
        assert indices.dtype == np.uint8
        assert np.all((indices >= 0) & (indices < 256))
    
    def test_decoding(self):
        """Test VQ decoding."""
        img = generate_synthetic_grayscale_image(64, 64)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        indices = vq.encode(img)
        decoded = vq.decode_image(indices)
        
        assert decoded.shape == img.shape
        assert decoded.dtype == np.uint8
        assert np.all((decoded >= 0) & (decoded <= 255))
    
    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding roundtrip."""
        img = generate_synthetic_grayscale_image(64, 64)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        indices = vq.encode(img)
        decoded = vq.decode_image(indices)
        
        # Should have some distortion due to quantization
        mse = np.mean((img.astype(float) - decoded.astype(float))**2)
        assert mse < 10000  # Should be reasonably close
    
    def test_codebook_size(self):
        """Test that codebook has exactly 256 entries."""
        img = generate_synthetic_grayscale_image(32, 32)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        
        # Even with small image, codebook should be padded to 256
        assert vq.codebook.shape[0] == 256
        assert vq.codebook.shape[1] == 16
    
    def test_decode_single_block(self):
        """Test decoding single block from index."""
        img = generate_synthetic_grayscale_image(64, 64)
        vq = VectorQuantizer(codebook_size=256, block_size=4)
        
        vq.train(img)
        
        # Decode index 0, 127, 255
        for idx in [0, 127, 255]:
            block = vq.decode_block(idx)
            assert block.shape == (4, 4)
            assert block.dtype == np.uint8
            assert np.all((block >= 0) & (block <= 255))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
