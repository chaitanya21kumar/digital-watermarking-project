"""AMBTC (Absolute Moment Block Truncation Coding) implementation."""

import numpy as np
import hashlib


class AMBTC:
    """Absolute Moment Block Truncation Coding for compression and authentication."""
    
    def __init__(self, block_size=4):
        self.block_size = block_size
    
    def compress(self, image: np.ndarray) -> list:
        """
        Compress grayscale image using AMBTC.
        
        Args:
            image: uint8 grayscale image
        
        Returns:
            List of dicts: [{'xL': int, 'xH': int, 'BM': np.array(bool, shape (4,4))}]
        """
        image = image.astype(np.uint8)
        h, w = image.shape
        
        compressed_blocks = []
        
        for i in range(0, h, self.block_size):
            for j in range(0, w, self.block_size):
                if i + self.block_size <= h and j + self.block_size <= w:
                    block = image[i:i+self.block_size, j:j+self.block_size]
                    xl, xh, bm = self._compress_block(block)
                    compressed_blocks.append({'xL': xl, 'xH': xh, 'BM': bm})
        
        return compressed_blocks
    
    def _compress_block(self, block: np.ndarray) -> tuple:
        """Compress a single 4x4 block."""
        block = block.astype(np.float32)
        mean_val = np.mean(block)
        
        # Generate bitmap: 1 if pixel >= mean, 0 otherwise
        bm = (block >= mean_val).astype(np.uint8)
        
        # Count pixels >= mean
        q = np.sum(bm)
        
        # Compute xL: mean of pixels < mean
        if q < 16:  # Some pixels are below mean
            xl = np.mean(block[bm == 0])
        else:
            xl = 0
        
        # Compute xH: mean of pixels >= mean
        if q > 0:  # Some pixels are >= mean
            xh = np.mean(block[bm == 1])
        else:
            xh = 255
        
        # Clip and round to [0, 255]
        xl = int(np.clip(np.round(xl), 0, 255))
        xh = int(np.clip(np.round(xh), 0, 255))
        
        return xl, xh, bm
    
    def decompress(self, compressed_blocks: list, image_shape: tuple) -> np.ndarray:
        """
        Reconstruct image from AMBTC compressed blocks.
        
        Args:
            compressed_blocks: List of block dicts
            image_shape: (height, width) of original image
        
        Returns:
            Reconstructed uint8 image
        """
        h, w = image_shape
        image = np.zeros((h, w), dtype=np.uint8)
        
        bd_idx = 0
        for i in range(0, h, self.block_size):
            for j in range(0, w, self.block_size):
                if i + self.block_size <= h and j + self.block_size <= w:
                    if bd_idx < len(compressed_blocks):
                        block_data = compressed_blocks[bd_idx]
                        xl, xh = block_data['xL'], block_data['xH']
                        bm = block_data['BM']
                        
                        # Reconstruct block
                        reconstructed = np.where(bm, xh, xl).astype(np.uint8)
                        image[i:i+self.block_size, j:j+self.block_size] = reconstructed
                        bd_idx += 1
        
        return image
    
    def generate_auth_code(self, xL: int, xH: int, BM: np.ndarray) -> int:
        """
        Generate 8-bit authentication code.
        AC = H(BM) || H(xH || xL) where || is concatenation as bits.
        """
        # Hash of bitmap
        bm_bytes = BM.astype(np.uint8).tobytes()
        h_bm = self._hash_4bit(bm_bytes)
        
        # Hash of xH||xL
        xh_xl_bytes = bytes([xH, xL])
        h_xh_xl = self._hash_4bit(xh_xl_bytes)
        
        # Combine: 4 bits || 4 bits = 8 bits
        ac = (h_bm << 4) | h_xh_xl
        return int(np.clip(ac, 0, 255))
    
    def _hash_4bit(self, data: bytes) -> int:
        """Hash data to 4-bit value using MD5."""
        md5_hash = hashlib.md5(data).digest()
        # XOR all bytes
        result = 0
        for byte in md5_hash:
            result ^= byte
        # Keep lower 4 bits
        return result & 0x0F


if __name__ == "__main__":
    # Test AMBTC
    ambtc = AMBTC(block_size=4)
    
    # Create a simple test image
    test_img = np.random.randint(0, 256, (16, 16), dtype=np.uint8)
    
    # Compress
    compressed = ambtc.compress(test_img)
    print(f"Compressed {len(compressed)} blocks")
    
    # Decompress
    reconstructed = ambtc.decompress(compressed, test_img.shape)
    print(f"Original shape: {test_img.shape}, Reconstructed shape: {reconstructed.shape}")
    
    # Generate auth code
    if compressed:
        block = compressed[0]
        ac = ambtc.generate_auth_code(block['xL'], block['xH'], block['BM'])
        print(f"Auth code example: {ac} (0-255)")
