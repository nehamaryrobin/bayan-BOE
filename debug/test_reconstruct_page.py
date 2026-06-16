import os
import sys
import pdfplumber
import re

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.header_item_extraction import extract_header

def extract_pages_reconstructed(pdf_path: str) -> list[str]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            if not words:
                pages.append("")
                continue
            
            # Sort words by top coordinate
            sorted_words = sorted(words, key=lambda w: w["top"])
            row_groups = []
            current_row = [sorted_words[0]]
            for w in sorted_words[1:]:
                # group words on the same line (tolerance of 9 points)
                if abs(w["top"] - current_row[0]["top"]) <= 9:
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row:
                row_groups.append(current_row)
            
            # Reconstruct lines
            lines = []
            for row in row_groups:
                # Sort words in row from left to right
                line_str = "  ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
                if line_str:
                    lines.append(line_str)
            
            pages.append("\n".join(lines))
    return pages

# Let's test this on a failed PDF to see if header extraction succeeds
archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
pdf_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".pdf")]

print(f"Found {len(pdf_files)} PDFs.")
for pdf_file in sorted(pdf_files)[:5]:
    pdf_path = os.path.join(archive_dir, pdf_file)
    try:
        # Reconstruct pages
        pages = extract_pages_reconstructed(pdf_path)
        # Try header extraction
        header = extract_header(pages, pdf_file)
        print(f"  {pdf_file}: DEC_NO={header['DEC_NO']}, NET_WEIGHT={header['NET_WEIGHT_7B']}, DELIVERY_ORDER={header['DELIVERY_ORDER_NO_5']}")
    except Exception as e:
        print(f"  Error for {pdf_file}: {e}")
