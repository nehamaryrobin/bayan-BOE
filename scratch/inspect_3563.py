import sys
import os

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages, extract_pages2
from extractors.header_item_extraction import _find_line, _get

pdf_path = "data/processed/25P0003563.pdf"

print("--- Pages 1 (extract_pages) ---")
pages1 = extract_pages(pdf_path)
if pages1:
    lines1 = [l for l in pages1[0].split('\n') if l.strip()]
    
    # Let's find GCC AEO Code and LICENCE NO labels and print surrounding lines
    aeo = _find_line(lines1, 'GCC AEO Code', '44')
    lic = _find_line(lines1, 'LICENCE NO', '39')
    
    print("GCC AEO Label index:", aeo)
    if aeo >= 0:
        for i in range(-1, 8):
            if 0 <= aeo + i < len(lines1):
                print(f"  aeo+{i:02d}: {repr(lines1[aeo + i])}")
                
    print("\nLICENCE NO Label index:", lic)
    if lic >= 0:
        for i in range(-1, 8):
            if 0 <= lic + i < len(lines1):
                print(f"  lic+{i:02d}: {repr(lines1[lic + i])}")
