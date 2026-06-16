import os
import sys

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages2
from extractors.header_item_extraction import _find_line, _get

pdf_path = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/failed/7660135521.pdf"
pages = extract_pages2(pdf_path)
lines = [l for l in pages[0].split('\n') if l.strip()]

print("--- LINES DUMP ---")
for idx, l in enumerate(lines):
    print(f"Line {idx}: {l}")

deliv_lbl = _find_line(lines, 'DELIVERY ORDER NO', '5')
print(f"\nDELIVERY ORDER NO Index: {deliv_lbl}")
if deliv_lbl >= 0:
    print(f"Line deliv_lbl + 1: {_get(lines, deliv_lbl + 1)}")
