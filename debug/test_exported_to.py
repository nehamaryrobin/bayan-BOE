import os
import sys
import re

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages
from extractors.header_item_extraction import _find_line, _get, _AWB_MANIFEST_LINE_RE, _LOOSE_AWB_MANIFEST_RE
from utils.arabic_utils import clean

def extract_exported_to_new(lines: list[str]) -> str | None:
    idx = _find_line(lines, 'EXPORTED TO')
    if idx < 0:
        return None

    val_line = _get(lines, idx + 1)
    if not val_line:
        return None

    # 1. Find AWB/Manifest match
    match = _AWB_MANIFEST_LINE_RE.search(val_line)
    if not match:
        match = _LOOSE_AWB_MANIFEST_RE.search(val_line)

    if match:
        # 2. Extract everything in the line until that match
        left_text = val_line[:match.start()]
        cleaned_val = clean(left_text)
        
        # Filter out common packages indicator "دﺮﻃ" (Dal Reh Tah) to ensure correct data
        if cleaned_val and not re.search(r'\u062f\u0631\u0637', cleaned_val):
            return cleaned_val
            
    return None

archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
pdf_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".pdf")]

print(f"Found {len(pdf_files)} PDF files in archive.")

for pdf_file in sorted(pdf_files):
    pdf_path = os.path.join(archive_dir, pdf_file)
    try:
        pages = extract_pages(pdf_path)
        lines = [l for l in pages[0].split('\n') if l.strip()]
        res = extract_exported_to_new(lines)
        if res:
            print(f"  {pdf_file}: EXPORTED_TO = {repr(res)}")
    except Exception as e:
        print(f"  Error for {pdf_file}: {e}")
