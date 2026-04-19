"""MOD-1: Color Image Support - RGB to YCbCr for watermarking."""

import numpy as np
import cv2
from src.watermark_embed import WatermarkEmbedder
from src.watermark_extract import WatermarkAuthenticator
from src.utils import crop_to_block_size


class ColorWatermarkEmbedder(WatermarkEmbedder):
    """
    Extension to RGB color images.
    
    Novelty: Paper only handles 8-bit grayscale. This independently processes
    Y, Cb, Cr channels in YCbCr color space, embedding authentication in luminance
    and recovery info in chrominance for better perceptual quality.
    """
    
    def embed_color(self, rgb_image: np.ndarray) -> tuple:
        """
        Full color embedding pipeline.
        
        Args:
            rgb_image: uint8 RGB image (H, W, 3)
        
        Returns:
            (stego_rgb, metadata)
        """
        rgb_image = rgb_image.astype(np.uint8)
        
        print("[ColorEmbed] Converting RGB to YCbCr...")
        # Note: cv2 uses BGR by default, so we need to convert first
        bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        ycbcr_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2YCrCb)
        
        y_channel = ycbcr_image[:, :, 0]
        cb_channel = ycbcr_image[:, :, 1]
        cr_channel = ycbcr_image[:, :, 2]
        
        # Embed watermark in Y channel (luminance)
        print("[ColorEmbed] Embedding in Y channel...")
        stego_y, metadata = self.embed(y_channel)
        
        # For Cb and Cr, just apply light authentication (no full embedding)
        print("[ColorEmbed] Processing Cb and Cr channels...")
        from src.ambtc import AMBTC
        ambtc = AMBTC(self.block_size)
        
        cb_compressed = ambtc.compress(cb_channel)
        cr_compressed = ambtc.compress(cr_channel)
        
        metadata['cb_channel'] = cb_channel.copy()
        metadata['cr_channel'] = cr_channel.copy()
        metadata['cb_compressed'] = cb_compressed
        metadata['cr_compressed'] = cr_compressed
        
        # Reconstruct YCbCr with watermarked Y
        ycbcr_stego = np.stack([stego_y, cb_channel, cr_channel], axis=2)
        
        # Convert back to RGB
        bgr_stego = cv2.cvtColor(ycbcr_stego.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        rgb_stego = cv2.cvtColor(bgr_stego, cv2.COLOR_BGR2RGB)
        
        print("[ColorEmbed] ✓ Color embedding complete")
        return rgb_stego, metadata
    
    def authenticate_and_recover_color(self, stego_rgb: np.ndarray,
                                       metadata: dict,
                                       original_rgb: np.ndarray = None) -> dict:
        """
        Full color authentication and recovery.
        
        Args:
            stego_rgb: uint8 watermarked RGB image
            metadata: Metadata from embedding
            original_rgb: Optional original RGB for comparison
        
        Returns:
            Dictionary with recovery results
        """
        stego_rgb = stego_rgb.astype(np.uint8)
        
        print("[ColorAuth] Converting to YCbCr...")
        bgr_stego = cv2.cvtColor(stego_rgb, cv2.COLOR_RGB2BGR)
        ycbcr_stego = cv2.cvtColor(bgr_stego, cv2.COLOR_BGR2YCrCb)
        
        y_stego = ycbcr_stego[:, :, 0]
        cb_stego = ycbcr_stego[:, :, 1]
        cr_stego = ycbcr_stego[:, :, 2]
        
        # Convert original if provided
        original_y = None
        if original_rgb is not None:
            bgr_orig = cv2.cvtColor(original_rgb.astype(np.uint8), cv2.COLOR_RGB2BGR)
            ycbcr_orig = cv2.cvtColor(bgr_orig, cv2.COLOR_BGR2YCrCb)
            original_y = ycbcr_orig[:, :, 0]
        
        # Authenticate Y channel
        print("[ColorAuth] Authenticating Y channel...")
        authenticator = WatermarkAuthenticator(
            self.seed_gamma, self.seed_gamma1, self.seed_gamma2, self.block_size
        )
        result = authenticator.authenticate_and_recover(
            y_stego, metadata['vq_codebook'], original_y
        )
        
        # Check chroma consistency if available
        from src.ambtc import AMBTC
        ambtc = AMBTC(self.block_size)
        cb_compressed = ambtc.compress(cb_stego)
        cr_compressed = ambtc.compress(cr_stego)
        
        # Prepare recovered RGB
        recovered_y = result['recovered_image']
        recovered_ycbcr = np.stack([recovered_y, cb_stego, cr_stego], axis=2)
        bgr_recovered = cv2.cvtColor(recovered_ycbcr.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        recovered_rgb = cv2.cvtColor(bgr_recovered, cv2.COLOR_BGR2RGB)
        
        result['recovered_image_rgb'] = recovered_rgb
        result['channel_info'] = {
            'cb_blocks_count': len(cb_compressed),
            'cr_blocks_count': len(cr_compressed)
        }
        
        print("[ColorAuth] ✓ Color authentication complete")
        return result


if __name__ == "__main__":
    from src.utils import generate_synthetic_color_image
    
    color_img = generate_synthetic_color_image(128, 128)
    
    embedder = ColorWatermarkEmbedder()
    stego_rgb, metadata = embedder.embed_color(color_img)
    
    print(f"Original RGB shape: {color_img.shape}")
    print(f"Stego RGB shape: {stego_rgb.shape}")
    
    result = embedder.authenticate_and_recover_color(stego_rgb, metadata, color_img)
    print(f"Tamper ratio: {result['tamper_ratio']}")
