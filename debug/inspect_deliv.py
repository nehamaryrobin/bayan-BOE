import os
import sys
import pdfplumber

pdf_path = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/failed/7660135521.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    # Extract raw text with layout=True
    text_layout = page.extract_text(layout=True)
    # Extract words
    words = page.extract_words()
    
    print("--- RAW TEXT WITH LAYOUT ---")
    lines_layout = text_layout.split('\n')
    for idx, l in enumerate(lines_layout):
        if 'DELIVERY ORDER' in l or 'IMPORTER' in l or 'NET WEIGHT' in l or idx in (5, 6, 7, 8):
            print(f"Row {idx}: {l}")
            if idx + 1 < len(lines_layout):
                print(f"Row {idx+1}: {lines_layout[idx+1]}")
                print(f"Row {idx+2}: {lines_layout[idx+2]}")

print("\n--- RECONSTRUCTED ROWS FROM WORDS ---")
# Let's reconstruct using coordinate grouping
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
    if 'DELIVERY' in row_str or 'IMPORTER' in row_str or 'NET' in row_str or idx in (5, 6, 7, 8, 9, 10):
        print(f"Row {idx}: {row_str}")
