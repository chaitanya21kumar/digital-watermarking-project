#!/usr/bin/env python3
"""Download high-quality diverse images from web sources."""

import urllib.request
import urllib.error
from pathlib import Path
import time

def download_images():
    """Download diverse high-quality images for testing."""
    
    images_dir = Path("images/test_quality")
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # High-quality image sources (direct URLs to PNG/JPEG)
    # These are from public datasets and research sources
    image_sources = {
        # Kodak PhotoCD (professional photography) - 24 bit depth, high quality
        "Kodak_Portrait.jpg": "https://www.cs.technion.ac.il/~elad/various/KodakImages/photo_13.png",
        "Kodak_Landscape.jpg": "https://www.cs.technion.ac.il/~elad/various/KodakImages/photo_04.png",
        "Kodak_Nature.jpg": "https://www.cs.technion.ac.il/~elad/various/KodakImages/photo_06.png",
        
        # BSD500 natural images (Berkeley Segmentation Dataset)
        "BSD_Street.jpg": "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS500/data/images/train/100075.jpg",
        "BSD_Flowers.jpg": "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS500/data/images/train/101087.jpg",
        
        # Standard Lena (better quality version)
        "Lena_HD.jpg": "https://upload.wikimedia.org/wikipedia/en/7/7d/Lenna_%28test_image%29.png",
        
        # High-quality test images
        "Building.jpg": "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS500/data/images/train/12003.jpg",
        "Architecture.jpg": "https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/bsds/BSDS500/data/images/train/100039.jpg",
    }
    
    print("\n" + "=" * 80)
    print("DOWNLOADING HIGH-QUALITY IMAGES FROM WEB")
    print("=" * 80)
    
    downloaded = []
    failed = []
    
    for name, url in image_sources.items():
        filepath = images_dir / name
        
        # Skip if already exists
        if filepath.exists():
            print(f"✅ {name:25} (already exists)")
            downloaded.append(name)
            continue
        
        try:
            print(f"⬇️  {name:25} downloading... ", end="", flush=True)
            
            # Add timeout and user agent
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                size_kb = len(content) / 1024
                print(f"✅ ({size_kb:.0f} KB)")
                downloaded.append(name)
                time.sleep(0.5)  # Be nice to servers
                
        except urllib.error.URLError as e:
            print(f"⚠️  (timeout/unreachable)")
            failed.append((name, str(e)))
        except Exception as e:
            print(f"❌ ({type(e).__name__})")
            failed.append((name, str(e)))
    
    print("\n" + "=" * 80)
    print(f"DOWNLOADED: {len(downloaded)} images")
    print(f"FAILED: {len(failed)} images")
    
    if failed:
        print("\nFailed downloads (will use generated alternatives):")
        for name, error in failed:
            print(f"  - {name}: {error[:60]}")
    
    print(f"\nImages saved to: {images_dir}")
    print("=" * 80 + "\n")
    
    return downloaded

if __name__ == "__main__":
    download_images()
