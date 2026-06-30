import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.line_item_extraction import _LINE_ITEM_PT1_RE, _LINE_ITEM_PT2_RE, _is_stray_text
from extractors.pdf_to_text import extract_words_with_coords

def test(pdf_path: str):
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

    pt1_indices = [idx for idx, row in enumerate(all_rows) if _LINE_ITEM_PT1_RE.match(row)]
    
    print("--- PT1 ROWS ---")
    for idx in pt1_indices:
        print(f"Row {idx}: {all_rows[idx]}")
        
    print("\n--- ALL ROWS around Item 6 and 7 ---")
    for i in range(min(pt1_indices), max(pt1_indices) + 2):
        flag = "PT1" if i in pt1_indices else "   "
        print(f"{i:03d} [{flag}] {all_rows[i]}")

if __name__ == "__main__":
    test("/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/processed/2670362146.PDF")
