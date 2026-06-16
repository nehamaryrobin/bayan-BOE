import os
import sys
import re

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.header_item_extraction import extract_header

archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
pdf_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".pdf")]

print(f"Found {len(pdf_files)} PDF files in archive.")

for pdf_file in sorted(pdf_files):
    pdf_path = os.path.join(archive_dir, pdf_file)
    try:
        header = extract_header(pdf_path, pdf_file)
        exported_to = header.get("EXPORTED_TO_15")
        if exported_to:
            print(f"  {pdf_file}: EXPORTED_TO_15 = {repr(exported_to)}")
    except Exception as e:
        print(f"  Error for {pdf_file}: {e}")
