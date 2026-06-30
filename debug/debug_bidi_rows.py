"""
debug_bidi_rows.py
Shows what fix_arabic() does to PT1 rows and whether the regex still matches.
Run from project root: python debug/debug_bidi_rows.py data/processed/2670362146.PDF
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.pdf_to_text import extract_words_with_coords
from extractors.line_item_extraction import _LINE_ITEM_PT1_RE
from utils.arabic_utils import fix_arabic

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/2670362146.PDF"

pages_words = extract_words_with_coords(pdf_path)
for page_no, words in enumerate(pages_words, start=1):
    if not words: continue
    filtered = [w for w in words if w["x0"] > 10.0]
    sorted_words = sorted(filtered, key=lambda w: w["top"])

    row_groups, current_row = [], [sorted_words[0]]
    for w in sorted_words[1:]:
        if abs(w["top"] - current_row[0]["top"]) <= 9:
            current_row.append(w)
        else:
            row_groups.append(current_row)
            current_row = [w]
    if current_row: row_groups.append(current_row)

    for row in row_groups:
        raw = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
        fixed = fix_arabic(raw)
        matched_raw   = bool(_LINE_ITEM_PT1_RE.match(raw))
        matched_fixed = bool(_LINE_ITEM_PT1_RE.match(fixed))
        if matched_raw or matched_fixed:
            print(f"\n=== PAGE {page_no} ===")
            print(f"  RAW   matches PT1: {matched_raw}")
            print(f"  FIXED matches PT1: {matched_fixed}")
            print(f"  RAW  : {raw[:120]}")
            print(f"  FIXED: {fixed[:120]}")
