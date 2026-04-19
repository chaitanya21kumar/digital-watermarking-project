"""Vector Quantization (VQ) implementation for watermarking recovery."""

import numpy as np
from sklearn.cluster import KMeans


class VectorQuantizer:
    """Vector Quantization using LBG algorithm (via KMeans)."""
    
    def __init__(self, codebook_size=256, block_size=4):
        self.codebook_size = codebook_size  # 256 codewords
        self.block_size = block_size        # 4x4 blocks → 16-dim vectors
        self.codebook = None                # shape: (256, 16)
    
    def train(self, image: np.ndarray):
        """
        Train VQ codebook using KMeans clustering.
        
        Args:
            image: uint8 grayscale image
        """
        image = image.astype(np.uint8)
        h, w = image.shape
        
        # Extract all non-overlapping 4x4 blocks as 16-dim vectors
        vectors = []
        for i in range(0, h, self.block_size):
            for j in range(0, w, self.block_size):
                if i + self.block_size <= h and j + self.block_size <= w:
                    block = image[i:i+self.block_size, j:j+self.block_size]
                    vector = block.flatten().astype(np.float32)
                    vectors.append(vector)
        
        if len(vectors) == 0:
            raise ValueError("No blocks extracted for VQ training")
        
        vectors = np.array(vectors, dtype=np.float32)
        
        # Train KMeans to find 256 cluster centers
        kmeans = KMeans(n_clusters=min(self.codebook_size, len(vectors)),
                       n_init=3, max_iter=100, random_state=42)
        kmeans.fit(vectors)
        
        # Store codebook, clip values to [0, 255]
        self.codebook = np.clip(kmeans.cluster_centers_, 0, 255).astype(np.uint8)
        
        # If we got fewer clusters than requested, pad with zeros
        if self.codebook.shape[0] < self.codebook_size:
            padding = np.zeros((self.codebook_size - self.codebook.shape[0], 16), dtype=np.uint8)
            self.codebook = np.vstack([self.codebook, padding])
    
    def encode(self, image: np.ndarray) -> np.ndarray:
        """
        Encode image using VQ.
        
        Args:
            image: uint8 grayscale image
        
        Returns:
            Index map: shape (num_blocks_h, num_blocks_w), uint8 values 0-255
        """
        if self.codebook is None:
            raise ValueError("Codebook not trained. Call train() first.")
        
        image = image.astype(np.uint8)
        h, w = image.shape
        
        num_blocks_h = h // self.block_size
        num_blocks_w = w // self.block_size
        
        indices = np.zeros((num_blocks_h, num_blocks_w), dtype=np.uint8)
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                block = image[i*self.block_size:(i+1)*self.block_size,
                            j*self.block_size:(j+1)*self.block_size]
                vector = block.flatten().astype(np.float32)
                
                # Find nearest codebook entry (L2 distance)
                distances = np.linalg.norm(self.codebook - vector, axis=1)
                nearest_idx = np.argmin(distances)
                indices[i, j] = nearest_idx
        
        return indices
    
    def decode_block(self, index: int) -> np.ndarray:
        """Decode single block from index."""
        if self.codebook is None:
            raise ValueError("Codebook not loaded")
        return self.codebook[index].reshape(self.block_size, self.block_size).astype(np.uint8)
    
    def decode_image(self, indices: np.ndarray, image_shape: tuple = None) -> np.ndarray:
        """
        Decode full image from index map.
        
        Args:
            indices: shape (num_blocks_h, num_blocks_w)
            image_shape: optional (height, width) for consistency check
        
        Returns:
            Decoded uint8 image
        """
        if self.codebook is None:
            raise ValueError("Codebook not loaded")
        
        num_blocks_h, num_blocks_w = indices.shape
        height = num_blocks_h * self.block_size
        width = num_blocks_w * self.block_size
        
        image = np.zeros((height, width), dtype=np.uint8)
        
        for i in range(num_blocks_h):
            for j in range(num_blocks_w):
                idx = indices[i, j]
                block = self.decode_block(idx)
                image[i*self.block_size:(i+1)*self.block_size,
                     j*self.block_size:(j+1)*self.block_size] = block
        
        return image
    
    def save_codebook(self, path: str):
        """Save codebook to file."""
        np.save(path, self.codebook)
    
    def load_codebook(self, path: str):
        """Load codebook from file."""
        self.codebook = np.load(path)


if __name__ == "__main__":
    # Test VQ
    vq = VectorQuantizer(codebook_size=256, block_size=4)
    
    # Create test image
    test_img = np.random.randint(0, 256, (16, 16), dtype=np.uint8)
    
    # Train
    vq.train(test_img)
    print(f"Codebook trained: {vq.codebook.shape}")
    
    # Encode
    indices = vq.encode(test_img)
    print(f"Encoded indices shape: {indices.shape}")
    
    # Decode
    decoded = vq.decode_image(indices)
    print(f"Decoded image shape: {decoded.shape}")
