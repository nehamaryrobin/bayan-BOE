import re
from extractors.pdf_to_text import extract_words_with_coords

pages_words = extract_words_with_coords('data/input/BOE_MAIR.pdf')
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

merged_rows = []
for row_str in all_rows:
    if re.match(r'^\d{1,2}$', row_str) and merged_rows:
        merged_rows[-1] += f" {row_str}"
    else:
        merged_rows.append(row_str)
all_rows = merged_rows

print("Looking for rows with '8':")
for i, r in enumerate(all_rows):
    if '8' in r:
        print(f"{i}: {r}")

_LINE_ITEM_PT2_RE = re.compile(r"""
    ^.*?                                             
    (?:(?P<exemption_code>\d{6,12})\s+)?                              
    (?:(?P<aip_duty>[\d,]+\.\d+)\s+(?P<aip_no>\d+)\s+)?               
    (?P<gross_weight>[\d,]+\.\d+)\s+                                  
    (?P<net_weight>[\d,]+\.\d+)\s+                                    
    (?P<unit>[^\s\d]+)\s+      
    (?P<item_qty>[\d,]+\.00)\s+                                     
    (?:(?P<package_type>[^\s\d]+)\s+(?P<package_qty>[\d,]+\.00)\s+)?  
    (?:(?P<release_ref>\d{4,12})\s+(?P<agency>.+?)\s+)?               
    (?P<item_no>\d{1,2})                                              
    (?:\s+.*)?$   
""", re.VERBOSE | re.DOTALL)

print("\nTesting PT2 Regex on rows:")
for r in all_rows:
    if _LINE_ITEM_PT2_RE.match(r):
        print(f"MATCHED: {r}")

