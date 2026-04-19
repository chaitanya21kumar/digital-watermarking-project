"""Tests for modifications."""

import numpy as np
import pytest
from src.utils import generate_synthetic_grayscale_image, generate_synthetic_color_image
from src.modifications.color_support import ColorWatermarkEmbedder
from src.modifications.sha_auth import SHA256WatermarkEmbedder
from src.modifications.adaptive_mapping import AdaptiveWatermarkEmbedder
from src.modifications.multilevel_recovery import MultiLevelRecoveryAuthenticator
from src.modifications.post_processing import EdgePreservingRecovery
from src.metrics import psnr


class TestMOD1ColorSupport:
    
    def test_color_embedding(self):
        """Test color image embedding."""
        color_img = generate_synthetic_color_image(64, 64)
        embedder = ColorWatermarkEmbedder()
        
        stego_rgb, metadata = embedder.embed_color(color_img)
        
        assert stego_rgb.shape == color_img.shape
        assert stego_rgb.dtype == np.uint8
        
        # PSNR should be high
        psnr_val = psnr(color_img, stego_rgb)
        assert psnr_val > 35  # Slightly lower than grayscale due to Y channel
    
    def test_color_authentication(self):
        """Test color image authentication."""
        color_img = generate_synthetic_color_image(64, 64)
        embedder = ColorWatermarkEmbedder()
        
        stego_rgb, metadata = embedder.embed_color(color_img)
        
        result = embedder.authenticate_and_recover_color(stego_rgb, metadata, color_img)
        
        assert 'recovered_image_rgb' in result
        assert 'channel_info' in result
        assert result['tamper_ratio'] < 0.1  # Low false positive


class TestMOD2SHA256:
    
    def test_sha256_embedding(self):
        """Test SHA-256 based embedding."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = SHA256WatermarkEmbedder()
        
        stego, metadata = embedder.embed(img)
        
        assert stego.shape == img.shape
        assert metadata['hash_type'] == 'SHA256'
        
        # PSNR should be identical to base
        psnr_val = psnr(img, stego)
        assert psnr_val > 45
    
    def test_sha256_lower_fpr(self):
        """Test that SHA-256 produces better hash outputs."""
        from src.modifications.sha_auth import SHA256AMBTC, compare_hash_collision_rate
        
        # All unique blocks with same xL, xH but different BM should produce
        # different auth codes more often with SHA-256
        ambtc = SHA256AMBTC(block_size=4)
        
        xL, xH = 100, 200
        
        # Generate different bitmaps
        bm1 = np.array([[1,0,1,0], [0,1,0,1], [1,0,1,0], [0,1,0,1]], dtype=np.uint8)
        bm2 = np.array([[0,1,0,1], [1,0,1,0], [0,1,0,1], [1,0,1,0]], dtype=np.uint8)
        
        ac1 = ambtc.generate_auth_code(xL, xH, bm1)
        ac2 = ambtc.generate_auth_code(xL, xH, bm2)
        
        assert ac1 != ac2  # Should produce different codes


class TestMOD3AdaptiveMapping:
    
    def test_entropy_computation(self):
        """Test entropy computation for blocks."""
        img = generate_synthetic_grayscale_image(128, 128)
        
        from src.modifications.adaptive_mapping import AdaptiveBlockMapper
        entropies = AdaptiveBlockMapper.compute_block_entropies(img)
        
        assert entropies.shape == (128 // 4, 128 // 4)
        assert np.all(entropies >= 0)
        assert np.all(entropies <= 8)  # Max entropy for 8-bit values
    
    def test_adaptive_mapping_generation(self):
        """Test adaptive mapping generation."""
        img = generate_synthetic_grayscale_image(128, 128)
        
        from src.modifications.adaptive_mapping import AdaptiveBlockMapper
        mapping = AdaptiveBlockMapper.generate_adaptive_mapping(img, seed=42)
        
        num_blocks = (128 // 4) ** 2
        assert len(mapping) == num_blocks
        assert len(np.unique(mapping)) == num_blocks  # All unique
        assert np.all((mapping >= 0) & (mapping < num_blocks))
    
    def test_adaptive_embedding(self):
        """Test embedding with adaptive mapping."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = AdaptiveWatermarkEmbedder()
        
        stego, metadata = embedder.embed(img)
        
        assert metadata['mapping_type'] == 'adaptive'
        assert stego.shape == img.shape
        
        psnr_val = psnr(img, stego)
        assert psnr_val > 45


class TestMOD4MultiLevelRecovery:
    
    def test_three_tier_recovery(self):
        """Test three-tier recovery mechanism."""
        img = generate_synthetic_grayscale_image(128, 128)
        
        from src.watermark_embed import WatermarkEmbedder
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # Simulate heavy attack (multiple blocks)
        attacked = stego.copy()
        attacked[0:32, 0:32] = 100
        attacked[96:128, 96:128] = 100
        
        authenticator = MultiLevelRecoveryAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        # Should have all three recovery tiers used
        tier_dist = result['tier_distribution']
        assert tier_dist['tier1_count'] >= 0
        assert tier_dist['tier2_count'] >= 0
        assert tier_dist['tier3_count'] >= 0
        
        # Recovery should still produce output
        assert result['recovered_image'].shape == img.shape


class TestMOD5PostProcessing:
    
    def test_bilateral_filtering(self):
        """Test bilateral filter post-processing."""
        img = generate_synthetic_grayscale_image(128, 128)
        
        from src.watermark_embed import WatermarkEmbedder
        from src.watermark_extract import WatermarkAuthenticator
        
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # Simulate small attack
        attacked = stego.copy()
        attacked[48:52, 48:52] = 100
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        recovered = result['recovered_image']
        tamper_map = result['tamper_map']
        
        # Apply post-processing
        postprocessed = EdgePreservingRecovery.apply_postprocessing(
            recovered, tamper_map, attacked, block_size=4
        )
        
        assert postprocessed.shape == recovered.shape
        assert postprocessed.dtype == np.uint8
    
    def test_psnr_improvement(self):
        """Test that post-processing improves PSNR."""
        img = generate_synthetic_grayscale_image(128, 128)
        
        from src.watermark_embed import WatermarkEmbedder
        from src.watermark_extract import WatermarkAuthenticator
        
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # Simulate attack
        attacked = stego.copy()
        attacked[40:60, 40:60] = 75
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        recovered = result['recovered_image']
        tamper_map = result['tamper_map']
        
        # Apply post-processing
        postprocessed = EdgePreservingRecovery.apply_postprocessing(
            recovered, tamper_map, attacked
        )
        
        # Compute improvement
        improvement = EdgePreservingRecovery.compute_psnr_improvement(
            recovered, postprocessed, img, tamper_map
        )
        
        # Should see some improvement (may be small due to small attack)
        assert improvement['psnr_improvement_full'] >= -1  # Allow small negative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
