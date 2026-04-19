"""Block mapping generation for watermark embedding."""

import numpy as np


def generate_block_mapping(num_blocks: int, seed: int) -> np.ndarray:
    """
    Generate non-repeating random permutation mapping for blocks.
    
    Args:
        num_blocks: Total number of blocks
        seed: Random seed for reproducibility
    
    Returns:
        Array of length num_blocks where mapping[i] = j means
        block i's watermark is sourced from block j.
    """
    rng = np.random.default_rng(seed)
    mapping = rng.permutation(num_blocks)
    return mapping.astype(np.uint32)


def get_block_indices(image_shape: tuple, block_size: int = 4) -> list:
    """
    Return list of (row, col) top-left corner indices of all blocks in raster order.
    
    Args:
        image_shape: (height, width) of image
        block_size: Size of each block
    
    Returns:
        List of tuples: [(row0, col0), (row0, col1), ..., (rowN, colN)]
    """
    h, w = image_shape[:2]
    num_blocks_h = h // block_size
    num_blocks_w = w // block_size
    
    indices = []
    for i in range(num_blocks_h):
        for j in range(num_blocks_w):
            indices.append((i * block_size, j * block_size))
    
    return indices


def linear_to_2d_block_index(linear_idx: int, num_blocks_w: int) -> tuple:
    """Convert linear block index to 2D grid position."""
    block_row = linear_idx // num_blocks_w
    block_col = linear_idx % num_blocks_w
    return (block_row, block_col)


def block_2d_to_linear_index(block_row: int, block_col: int, num_blocks_w: int) -> int:
    """Convert 2D block grid position to linear index."""
    return block_row * num_blocks_w + block_col


if __name__ == "__main__":
    # Test block mapping
    num_blocks = 64
    mapping = generate_block_mapping(num_blocks, seed=42)
    
    print(f"Generated mapping for {num_blocks} blocks")
    print(f"Mapping shape: {mapping.shape}")
    print(f"First 10 mappings: {mapping[:10]}")
    print(f"All unique: {len(np.unique(mapping)) == num_blocks}")
    
    # Test indices
    indices = get_block_indices((256, 256), block_size=4)
    print(f"\nGenerated {len(indices)} block indices for 256x256 image")
    print(f"First 5 indices: {indices[:5]}")
