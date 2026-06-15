from extractors.line_item_extraction import extract_tabular_groups
from extractors.pdf_to_text import extract_words_with_coords

pages_words = extract_words_with_coords('data/input/BOE_MAIR.pdf')
all_rows = []
for page_no, words in enumerate(pages_words, start=1):
    if not words: continue
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
    for row in row_groups:
        row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
        if row_str:
            all_rows.append(row_str)

for i, r in enumerate(all_rows):
    if '5.50' in r or 'MP' in r:
        print(f"[{i}] {repr(r)}")
