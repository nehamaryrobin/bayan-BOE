import os
import sys
import pdfplumber

pdf_path = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/failed/8660015771.pdf"
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    
    # Reconstruct rows
    sorted_words = sorted(words, key=lambda w: w["top"])
    row_groups = []
    current_row = [sorted_words[0]]
    for w in sorted_words[1:]:
        if abs(w["top"] - current_row[0]["top"]) <= 9:
            current_row.append(w)
        else:
            row_groups.append(current_row)
            current_row = [w]
    if current_row: row_groups.append(current_row)
    
    for idx, row in enumerate(row_groups):
        row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
        if idx < 20:
            print(f"Row {idx}: {row_str}")
