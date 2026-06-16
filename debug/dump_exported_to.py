import os
import sys
import re

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages
from extractors.header_item_extraction import _find_line, _get

archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
pdf_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".pdf")]

for pdf_file in sorted(pdf_files):
    pdf_path = os.path.join(archive_dir, pdf_file)
    try:
        pages = extract_pages(pdf_path)
        lines = [l for l in pages[0].split('\n') if l.strip()]
        idx = _find_line(lines, 'EXPORTED TO')
        if idx >= 0:
            val_line = _get(lines, idx + 1)
            groups = [g.strip() for g in re.split(r'\s{3,}', val_line) if g.strip()]
            print(f"{pdf_file}: {groups}")
    except Exception as e:
        print(f"Error for {pdf_file}: {e}")
