import sys
import os

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages, extract_pages2

pdf_path = "data/failed/25P0003464.pdf"

print("--- Pages 1 (extract_pages) ---")
pages1 = extract_pages(pdf_path)
if pages1:
    lines1 = [l for l in pages1[0].split('\n') if l.strip()]
    for i, line in enumerate(lines1[:20]):
        print(f"Line {i:02d}: {line}")

print("\n--- Pages 2 (extract_pages2) ---")
pages2 = extract_pages2(pdf_path)
if pages2:
    lines2 = [l for l in pages2[0].split('\n') if l.strip()]
    for i, line in enumerate(lines2[:20]):
        print(f"Line {i:02d}: {line}")
