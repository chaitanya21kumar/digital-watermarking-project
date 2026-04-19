"""Vector Quantization (VQ) implementation for watermarking recovery."""

import os
import numpy as np


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
        
        # Subsample training vectors for speed on large images.
        rng = np.random.default_rng(42)
        if len(vectors) > 4096:
            sample_idx = rng.choice(len(vectors), size=4096, replace=False)
            train_vectors = vectors[sample_idx]
        else:
            train_vectors = vectors

        # Train KMeans codebook. Default to numpy implementation for portability.
        n_clusters = min(self.codebook_size, len(train_vectors))
        centers = None

        use_sklearn = os.environ.get("VQ_USE_SKLEARN", "0") == "1"
        if use_sklearn:
            try:
                from sklearn.cluster import KMeans  # type: ignore

                kmeans = KMeans(
                    n_clusters=n_clusters,
                    n_init=3,
                    max_iter=100,
                    random_state=42,
                )
                kmeans.fit(train_vectors)
                centers = kmeans.cluster_centers_
            except Exception:
                centers = self._kmeans_numpy(train_vectors, n_clusters, max_iter=20, seed=42)
        else:
            centers = self._kmeans_numpy(train_vectors, n_clusters, max_iter=20, seed=42)

        # Store codebook, clip values to [0, 255]
        self.codebook = np.clip(centers, 0, 255).astype(np.uint8)
        
        # If we got fewer clusters than requested, pad with zeros
        if self.codebook.shape[0] < self.codebook_size:
            padding = np.zeros((self.codebook_size - self.codebook.shape[0], 16), dtype=np.uint8)
            self.codebook = np.vstack([self.codebook, padding])

    def _kmeans_numpy(self, vectors: np.ndarray, n_clusters: int,
                      max_iter: int = 30, seed: int = 42) -> np.ndarray:
        """Lightweight numpy k-means fallback for environments without sklearn."""
        rng = np.random.default_rng(seed)
        n_samples = vectors.shape[0]

        # Initialize centers with unique samples.
        init_idx = rng.choice(n_samples, size=n_clusters, replace=False)
        centers = vectors[init_idx].astype(np.float32).copy()

        for _ in range(max_iter):
            # Assign each sample to nearest center (squared Euclidean distance).
            d2 = np.sum((vectors[:, None, :] - centers[None, :, :]) ** 2, axis=2)
            labels = np.argmin(d2, axis=1)

            new_centers = centers.copy()
            for k in range(n_clusters):
                members = vectors[labels == k]
                if len(members) > 0:
                    new_centers[k] = np.mean(members, axis=0)
                else:
                    # Re-seed empty cluster to a random sample.
                    new_centers[k] = vectors[rng.integers(0, n_samples)]

            if np.allclose(new_centers, centers, atol=1e-3):
                centers = new_centers
                break
            centers = new_centers

        return centers
    
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
