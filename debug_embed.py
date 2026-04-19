#!/usr/bin/env python3
"""Debug embedding performance."""

import sys
import numpy as np
from PIL import Image

print("[A] Loading modules...", flush=True)
from src.watermark_embed import WatermarkEmbedder

print("[B] Importing Lena image...", flush=True)
img = np.array(Image.open('images/test/Lena.png').convert('L'), dtype=np.uint8)
print(f"[C] Image shape: {img.shape}", flush=True)

print("[D] Creating embedder...", flush=True)
embedder = WatermarkEmbedder()

print("[E] Testing preprocessing...", flush=True)
preprocessed = embedder._preprocess_image(img)
print(f"[F] Preprocessed shape: {preprocessed.shape}", flush=True)

print("[G] Testing AMBTC...", flush=True)
from src.ambtc import AMBTC
ambtc = AMBTC(4)
compressed = ambtc.compress(preprocessed)
print(f"[H] Compressed {len(compressed)} blocks", flush=True)

print("[I] Testing VQ training...", flush=True)
from src.vq import VectorQuantizer
vq = VectorQuantizer(256, 4)
vq.train(img)
print(f"[J] VQ codebook size: {vq.codebook.shape}", flush=True)

vq_indices = vq.encode(img)
print(f"[K] VQ indices shape: {vq_indices.shape}", flush=True)

print("[L] Done!", flush=True)
