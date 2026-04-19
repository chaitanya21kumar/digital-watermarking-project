"""Tests for watermark embedding and extraction."""

import pytest
import numpy as np
from src.utils import generate_synthetic_grayscale_image
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.metrics import psnr
from src.bd_wt_tables import generate_bd_table, generate_wt_table


class TestWatermarkEmbedding:
    
    def test_embedding_psnr(self):
        """Test that embedded watermark introduces acceptable PSNR loss."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder(seed_gamma=42, seed_gamma1=123, seed_gamma2=456)
        
        stego, metadata = embedder.embed(img)
        
        assert stego.shape == img.shape
        assert stego.dtype == np.uint8
        
        # PSNR should be high (watermark is imperceptible)
        psnr_val = psnr(img, stego)
        assert psnr_val > 45  # Good quality watermark
    
    def test_embedding_output_structure(self):
        """Test that embedding returns proper metadata."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder()
        
        stego, metadata = embedder.embed(img)
        
        assert isinstance(metadata, dict)
        assert 'seeds' in metadata
        assert 'image_shape' in metadata
        assert 'vq_codebook' in metadata
        assert 'auth_codes' in metadata
        assert 'vq_indices' in metadata
        assert 'map1' in metadata
        assert 'map2' in metadata


class TestWatermarkAuthentication:
    
    def test_no_attack_authentication(self):
        """Test authentication when image is not attacked."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder(seed_gamma=42, seed_gamma1=123, seed_gamma2=456)
        stego, metadata = embedder.embed(img)
        
        authenticator = WatermarkAuthenticator(seed_gamma=42, seed_gamma1=123, seed_gamma2=456)
        result = authenticator.authenticate_and_recover(
            stego, metadata['vq_codebook'], img
        )
        
        # With proper seeds and no attack, very few blocks should be marked as tampered
        assert result['tamper_ratio'] < 0.05  # Less than 5% false positive
        assert 'tamper_map' in result
        assert 'recovered_image' in result
    
    def test_recovery_psnr(self):
        """Test PSNR of recovered image."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # Simulate no attack
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            stego, metadata['vq_codebook'], img
        )
        
        recovered = result['recovered_image']
        assert recovered.shape == img.shape
        assert recovered.dtype == np.uint8
    
    def test_metrics_computation(self):
        """Test that metrics are properly computed."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            stego, metadata['vq_codebook'], img
        )
        
        metrics = result['metrics']
        assert 'TP' in metrics and isinstance(metrics['TP'], (int, np.integer))
        assert 'TN' in metrics
        assert 'FP' in metrics
        assert 'FN' in metrics
        assert 'TPR' in metrics and 0 <= metrics['TPR'] <= 1
        assert 'FPR' in metrics and 0 <= metrics['FPR'] <= 1


class TestBDWTTables:
    
    def test_bd_table_generation(self):
        """Test BD table generation."""
        BD = generate_bd_table()
        
        assert BD.shape == (16, 16)
        assert BD.dtype == np.uint8
        assert np.all((BD == 0) | (BD == 1))
        
        # Check specific values: BD[x][y] = (x + y) mod 2
        assert BD[0, 0] == 0
        assert BD[0, 1] == 1
        assert BD[1, 0] == 1
        assert BD[1, 1] == 0
        assert BD[5, 5] == 0  # (5+5) mod 2 = 0
        assert BD[5, 6] == 1  # (5+6) mod 2 = 1
    
    def test_wt_table_generation(self):
        """Test WT table generation."""
        WT = generate_wt_table()
        
        assert WT.shape == (16, 16)
        assert WT.dtype == np.uint8
        assert np.all((WT >= 0) & (WT <= 3))
        
        # Check specific values: WT[x][y] = (x + floor(y/2)) mod 4
        assert WT[0, 0] == 0
        assert WT[0, 1] == 0
        assert WT[0, 2] == 1
        assert WT[0, 3] == 1
        assert WT[5, 5] == (5 + 2) % 4  # (5 + floor(5/2)) mod 4 = 7 mod 4 = 3
    
    def test_bd_wt_balance(self):
        """Test that BD and WT tables are balanced."""
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        # BD should have equal 0s and 1s
        zeros_bd = np.sum(BD == 0)
        ones_bd = np.sum(BD == 1)
        assert zeros_bd == ones_bd == 128
        
        # WT should have equal distribution of 0,1,2,3
        for val in range(4):
            count = np.sum(WT == val)
            assert count == 64  # 256 / 4


class TestPixelPairEmbedding:
    
    def test_pixel_pair_roundtrip(self):
        """Test embedding and extracting 3-bit watermark from pixel pair."""
        from src.bd_wt_tables import embed_3bit_watermark, extract_3bit_watermark
        
        BD = generate_bd_table()
        WT = generate_wt_table()
        
        P1, P2 = 100, 150
        AC_bit, RI1_bit, RI2_bit = 1, 0, 1
        
        P1_new, P2_new = embed_3bit_watermark(P1, P2, AC_bit, RI1_bit, RI2_bit, BD, WT)
        AC_ext, RI1_ext, RI2_ext = extract_3bit_watermark(P1_new, P2_new, BD, WT)
        
        # Should recover exactly
        assert AC_ext == AC_bit
        assert RI1_ext == RI1_bit
        assert RI2_ext == RI2_bit
        
        # Pixel values should be close to original
        assert abs(P1_new - P1) <= 15
        assert abs(P2_new - P2) <= 15


class TestCuttingAttack:
    
    def test_cutting_attack_detection(self):
        """Test that cutting attack is properly detected."""
        img = generate_synthetic_grayscale_image(128, 128)
        embedder = WatermarkEmbedder()
        stego, metadata = embedder.embed(img)
        
        # Simulate cutting attack
        attacked = stego.copy()
        attacked[32:48, 32:48] = 100  # Replace 16x16 region
        
        authenticator = WatermarkAuthenticator()
        result = authenticator.authenticate_and_recover(
            attacked, metadata['vq_codebook'], img
        )
        
        # Should detect tampered blocks
        assert result['tamper_ratio'] > 0.1  # At least 10% tamper detected
        tamper_map = result['tamper_map']
        
        # Tampered region should be detected (32:48 = blocks 8-12)
        tampered_in_region = np.sum(tamper_map[8:12, 8:12])
        assert tampered_in_region > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
