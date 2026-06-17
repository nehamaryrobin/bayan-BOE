import sys
import os

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages

pdf_path = sys.argv[1]
pages = extract_pages(pdf_path)
if pages:
    lines = pages[0].split('\n')
    for i, line in enumerate(lines):
        if any(kw in line.upper() for kw in ['MEASUREMENT']):
            print(f"File: {os.path.basename(pdf_path)}")
            print(f"Line {i-1:03d}: {lines[i-1] if i-1 >= 0 else ''}")
            print(f"Line {i:03d} (Label): {line}")
            print(f"Line {i+1:03d} (Value): {lines[i+1] if i+1 < len(lines) else ''}")
            print(f"Line {i+2:03d}: {lines[i+2] if i+2 < len(lines) else ''}")
            print("-" * 50)
