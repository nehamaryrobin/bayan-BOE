import sys
import os
import re

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.pdf_to_text import extract_pages
from extractors.header_item_extraction import _find_line, _get
from utils.arabic_utils import clean

def test_extract_licence(pdf_path):
    pages = extract_pages(pdf_path)
    if not pages:
        return None
    lines1 = [l for l in pages[0].split('\n') if l.strip()]
    
    lic_lbl = _find_line(lines1, 'LICENCE NO', '39')
    if lic_lbl < 0:
        return None
        
    limit = _find_line(lines1, 'Other Remarks', '45')
    if limit < 0:
        limit = len(lines1)
        
    licence_num = None
    licence_idx = -1
    for i in range(1, 6):
        idx = lic_lbl + i
        if idx < limit:
            val = _get(lines1, idx)
            if re.match(r'^\d{4}$', val):
                licence_num = val
                licence_idx = idx
                break
                
    licence_text = None
    if licence_idx > lic_lbl:
        above_val = _get(lines1, licence_idx - 1)
        if "LICENCE NO" not in above_val and not re.match(r'^\d{7}$', above_val):
            licence_text = clean(above_val)
            
    if licence_text and licence_num:
        return f"{licence_text} {licence_num}"
    return licence_num

processed_dir = "data/processed"
pdf_files = [f for f in os.listdir(processed_dir) if f.lower().endswith('.pdf')]
for f in sorted(pdf_files)[:10]:
    path = os.path.join(processed_dir, f)
    res = test_extract_licence(path)
    print(f"{f}: {repr(res)}")
