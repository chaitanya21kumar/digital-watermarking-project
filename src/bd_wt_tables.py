"""BD (Binary Digital) and WT (Waves Type) tables with pixel-pair embedding."""

import numpy as np


def generate_bd_table() -> np.ndarray:
    """
    Generate Binary Digital Table BD of size 16x16.
    BD[x][y] = (x + y) mod 2
    """
    x_coords = np.arange(16)
    y_coords = np.arange(16)
    X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
    BD = (X + Y) % 2
    return BD.astype(np.uint8)


def generate_wt_table() -> np.ndarray:
    """
    Generate Waves Type Table WT of size 16x16.
    WT[x][y] = (x + floor(y/2)) mod 4
    """
    x_coords = np.arange(16)
    y_coords = np.arange(16)
    X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
    WT = (X + np.floor(Y / 2).astype(int)) % 4
    return WT.astype(np.uint8)


def embed_3bit_watermark(P1: int, P2: int, AC_bit: int, RI1_bit: int, RI2_bit: int,
                         BD: np.ndarray, WT: np.ndarray) -> tuple:
    """
    Embed 3-bit watermark into pixel pair (P1, P2).
    
    Args:
        P1, P2: Original pixel values (0-255)
        AC_bit, RI1_bit, RI2_bit: 3 bits of watermark to embed
        BD, WT: BD and WT tables (16x16)
    
    Returns:
        (P1_new, P2_new): Modified pixel pair carrying the watermark
    """
    # Compute coordinate in 16x16 table
    x = P1 % 16
    y = P2 % 16
    
    # Target values
    target_bd = AC_bit  # 0 or 1
    target_wt = 2 * RI1_bit + RI2_bit  # 0, 1, 2, or 3
    
    # Search for (x', y') satisfying BD[x'][y'] == target_bd AND WT[x'][y'] == target_wt
    # Clockwise search: start from (x, y) and search in raster order
    search_order = _get_clockwise_search_order(x, y)
    
    x_new, y_new = None, None
    for x_idx, y_idx in search_order:
        if BD[x_idx, y_idx] == target_bd and WT[x_idx, y_idx] == target_wt:
            x_new, y_new = x_idx, y_idx
            break
    
    if x_new is None:
        # Fallback (should not happen with proper tables)
        x_new, y_new = x, y
    
    # Reconstruct pixel values
    P1_new = 16 * (P1 // 16) + x_new
    P2_new = 16 * (P2 // 16) + y_new
    
    # Clip to [0, 255]
    P1_new = int(np.clip(P1_new, 0, 255))
    P2_new = int(np.clip(P2_new, 0, 255))
    
    return (P1_new, P2_new)


def _get_clockwise_search_order(start_x: int, start_y: int) -> list:
    """
    Generate search order for (x', y') in 16x16 grid starting from (start_x, start_y).
    Raster order: (x, y+1), (x, y+2), ..., then next row.
    """
    order = []
    for step in range(256):
        # Raster order: row-major, starting from (start_x, start_y+1)
        offset = step
        x_offset = offset // 16
        y_offset = offset % 16
        x = (start_x + x_offset) % 16
        y = (start_y + y_offset) % 16
        order.append((x, y))
    return order


def extract_3bit_watermark(P1: int, P2: int,
                           BD: np.ndarray, WT: np.ndarray) -> tuple:
    """
    Extract 3-bit watermark from pixel pair.
    
    Args:
        P1, P2: Pixel values (0-255)
        BD, WT: BD and WT tables
    
    Returns:
        (AC_bit, RI1_bit, RI2_bit): 3 extracted bits
    """
    x = P1 % 16
    y = P2 % 16
    
    # Extract bits from tables
    AC_bit = int(BD[x, y])
    wt_val = int(WT[x, y])
    RI1_bit = wt_val // 2
    RI2_bit = wt_val % 2
    
    return (AC_bit, RI1_bit, RI2_bit)


if __name__ == "__main__":
    # Test BD and WT tables
    BD = generate_bd_table()
    WT = generate_wt_table()
    
    print("BD table sample (first 5x5):")
    print(BD[:5, :5])
    print("\nWT table sample (first 5x5):")
    print(WT[:5, :5])
    
    # Test embedding and extraction
    P1, P2 = 100, 150
    AC_bit, RI1_bit, RI2_bit = 1, 0, 1
    
    P1_new, P2_new = embed_3bit_watermark(P1, P2, AC_bit, RI1_bit, RI2_bit, BD, WT)
    print(f"\nOriginal pixels: P1={P1}, P2={P2}")
    print(f"Watermark: AC_bit={AC_bit}, RI1_bit={RI1_bit}, RI2_bit={RI2_bit}")
    print(f"Modified pixels: P1'={P1_new}, P2'={P2_new}")
    
    # Extract back
    AC_ext, RI1_ext, RI2_ext = extract_3bit_watermark(P1_new, P2_new, BD, WT)
    print(f"Extracted: AC_bit={AC_ext}, RI1_bit={RI1_ext}, RI2_bit={RI2_ext}")
    print(f"Match: {(AC_ext, RI1_ext, RI2_ext) == (AC_bit, RI1_bit, RI2_bit)}")
