import os
import sys

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_words_with_coords
from extractors.line_item_extraction import _LINE_ITEM_PT1_RE, _LINE_ITEM_PT2_RE

pdf_path = "data/processed/2670362207exemp.pdf"
pages_words = extract_words_with_coords(pdf_path)

all_rows = []
for page_no, words in enumerate(pages_words, start=1):
    if not words: continue
    filtered_words = [w for w in words if w["x0"] > 10.0]
    if not filtered_words: continue
    
    sorted_words = sorted(filtered_words, key=lambda w: w["top"])
    row_groups = []
    current_row = [sorted_words[0]]
    for w in sorted_words[1:]:
        if abs(w["top"] - current_row[0]["top"]) <= 9:
            current_row.append(w)
        else:
            row_groups.append(current_row)
            current_row = [w]
    if current_row: row_groups.append(current_row)
    
    for row in row_groups:
        row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
        if row_str:
            all_rows.append(row_str)

print("Rows from 2670362207exemp.pdf:")
for i, r in enumerate(all_rows):
    m1 = _LINE_ITEM_PT1_RE.match(r)
    m2 = _LINE_ITEM_PT2_RE.match(r)
    if m1 or m2 or "نزﻮﻟا" in r or "WEIGHT" in r or "AIP" in r:
        print(f"{i:03d}: [PT1={bool(m1)}, PT2={bool(m2)}] {r}")
        if m2:
            print(f"     -> Matched PT2: {m2.groupdict()}")
