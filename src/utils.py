"""Utility functions for image I/O and helper operations."""

import os
import numpy as np
from PIL import Image
import requests
from pathlib import Path


def download_test_images(output_dir="images/test"):
    """Download standard grayscale test images for watermarking experiments."""
    os.makedirs(output_dir, exist_ok=True)
    
    images = {
        "Lena": "https://sipi.usc.edu/database/preview/misc/4.2.04.jpg",
        "Baboon": "https://sipi.usc.edu/database/preview/misc/4.2.03.jpg",
        "Elaine": "https://sipi.usc.edu/database/preview/misc/4.2.06.jpg",
        "Airplane": "https://sipi.usc.edu/database/preview/misc/4.2.05.jpg",
    }
    
    for name, url in images.items():
        filepath = os.path.join(output_dir, f"{name}.png")
        if os.path.exists(filepath):
            print(f"  {name} already exists at {filepath}")
            continue
        
        try:
            print(f"  Downloading {name}...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            img = Image.open(__import__('io').BytesIO(response.content))
            # Convert to grayscale and resize to 512x512
            img = img.convert('L').resize((512, 512), Image.Resampling.LANCZOS)
            img.save(filepath)
            print(f"    ✓ Saved {name} to {filepath}")
        except Exception as e:
            print(f"    ✗ Failed to download {name}: {e}")
            print(f"    Generating synthetic {name}...")
            img_array = generate_synthetic_grayscale_image(512, 512, seed=hash(name) % 10000)
            img = Image.fromarray(img_array.astype(np.uint8))
            img.save(filepath)
            print(f"    ✓ Saved synthetic {name} to {filepath}")
    
    # Create a small color test image
    color_test_path = os.path.join(output_dir, "test_color.png")
    if not os.path.exists(color_test_path):
        print("  Creating small color test image (64x64)...")
        color_img = generate_synthetic_color_image(64, 64)
        img = Image.fromarray(color_img.astype(np.uint8))
        img.save(color_test_path)
        print(f"    ✓ Saved to {color_test_path}")


def generate_synthetic_grayscale_image(height, width, seed=42):
    """Generate a realistic-looking synthetic grayscale test image using numpy."""
    rng = np.random.RandomState(seed)
    
    img = np.zeros((height, width), dtype=np.float32)
    
    # Add gradient background
    for i in range(height):
        img[i, :] = (i / height) * 200
    
    # Add some circles of varying intensity
    centers = [(height//4, width//4, 80), (height*3//4, width*3//4, 100), 
               (height//2, width//2, 60)]
    for cy, cx, r in centers:
        for y in range(max(0, cy-r), min(height, cy+r)):
            for x in range(max(0, cx-r), min(width, cx+r)):
                dist = np.sqrt((y-cy)**2 + (x-cx)**2)
                if dist <= r:
                    img[y, x] = 200 - (dist/r)*100
    
    # Add texture/noise
    noise = rng.normal(0, 10, (height, width))
    img = img + noise
    
    # Create some edges with local patterns
    for i in range(min(100, height), min(300, height)):
        for j in range(min(100, width), min(300, width)):
            if ((i + j) // 10) % 2 == 0:
                img[i, j] = np.clip(img[i, j] + 30, 0, 255)
    
    return np.clip(img, 0, 255)


def generate_synthetic_color_image(height, width, seed=42):
    """Generate a synthetic RGB color test image."""
    rng = np.random.RandomState(seed)
    
    img = np.zeros((height, width, 3), dtype=np.float32)
    
    # RGB gradient
    for i in range(height):
        img[i, :, 0] = (i / height) * 255  # Red channel
    for j in range(width):
        img[:, j, 1] = (j / width) * 255   # Green channel
    img[:, :, 2] = 128  # Blue channel constant
    
    # Add some texture
    noise = rng.normal(0, 10, (height, width, 3))
    img = img + noise
    
    return np.clip(img, 0, 255)


def load_image(filepath, grayscale=True):
    """Load image as numpy array. Returns grayscale uint8 array."""
    img = Image.open(filepath)
    if grayscale:
        img = img.convert('L')
    img_array = np.array(img, dtype=np.uint8)
    return img_array


def save_image(filepath, img_array):
    """Save numpy array as image file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    if img_array.dtype != np.uint8:
        img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_array)
    img.save(filepath)


def crop_to_block_size(image, block_size=4):
    """Crop image to nearest multiple of block_size."""
    h, w = image.shape[:2]
    h_crop = (h // block_size) * block_size
    w_crop = (w // block_size) * block_size
    return image[:h_crop, :w_crop]


def get_block_indices(image_shape, block_size=4):
    """Return list of (row, col) top-left corner indices for all blocks in raster order."""
    h, w = image_shape[:2]
    num_blocks_h = h // block_size
    num_blocks_w = w // block_size
    
    indices = []
    for i in range(num_blocks_h):
        for j in range(num_blocks_w):
            indices.append((i * block_size, j * block_size))
    
    return indices


def extract_blocks(image, block_size=4):
    """Extract all non-overlapping blocks from image. Returns list of (h, w, block_size, block_size) arrays."""
    h, w = image.shape[:2]
    blocks = []
    for i in range(0, h, block_size):
        for j in range(0, w, block_size):
            if i + block_size <= h and j + block_size <= w:
                blocks.append(image[i:i+block_size, j:j+block_size].copy())
    return blocks


def reconstruct_image_from_blocks(blocks, num_blocks_h, num_blocks_w, block_size=4):
    """Reconstruct image from list of blocks."""
    height = num_blocks_h * block_size
    width = num_blocks_w * block_size
    image = np.zeros((height, width), dtype=np.uint8)
    
    idx = 0
    for i in range(num_blocks_h):
        for j in range(num_blocks_w):
            image[i*block_size:(i+1)*block_size, j*block_size:(j+1)*block_size] = blocks[idx]
            idx += 1
    
    return image


if __name__ == "__main__":
    print("Downloading test images...")
    download_test_images()
    print("✓ Test images ready!")
