from extractors.pdf_to_text import extract_words_with_coords
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number

logger = get_logger("line_item_extraction")

_BORDER_NOISE_RE = re.compile(r'^[A-Z]{1,3}$')

_LINE_ITEM_PT1_RE = re.compile(r"""
    ^.*? (?P<total_duty>[\d,]+(?:\.\d+)?)\s+          
    (?P<income_type>[^\d%]+?)\s* (?:%\s*(?P<duty_rate>\d{1,2}(?:\.\d+)?)\s+)? 
    (?P<cif_local>[\d,]+(?:\.\d+)?)\s+           
    (?P<currency_rate>[\d,]+(?:\.\d+)?)\s+          
    (?P<currency_type>[A-Z]{3})\s+               
    (?:(?P<foreign_value>[\d,]+(?:\.\d+)?)\s+)?   
    (?P<origin_country>[A-Z]{2})\s+              
    (?P<description>.+?)\s+                      
    (?P<hs_code>\d{10,12})\s+                     
    (?P<item_no>\d{1,2})                         
    (?:\s+.*)?$   
""", re.VERBOSE)

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

def _is_stray_text(line: str) -> bool:
    """Returns True if the line is orphaned text (not a main row or header)."""
    if _LINE_ITEM_PT1_RE.match(line) or _LINE_ITEM_PT2_RE.match(line): return False
    if re.search(r'(TYPE|VALUE TYPE|ORIGIN|DESCRIPTION|H\.S\.CODE|MARKS & NUMBERS)', line, re.IGNORECASE): return False
    if re.match(r'^[\d\s.,\-]+$', line): return False
    return True

def _is_stray_text(line: str) -> bool:
    """Returns True if the line is orphaned text (not a main row or header)."""
    if _LINE_ITEM_PT1_RE.match(line) or _LINE_ITEM_PT2_RE.match(line): 
        return False
    walls_re = r'(TYPE|VALUE TYPE|ORIGIN|DESCRIPTION|H\.S\.CODE|MARKS & NUMBERS|WEIGHT|ITEM|PACKAGES|CUSTOMS RESTRICTIONS|AIP|تاءﺎﻔﻋﻹا ﺰﻣر 42|ةرﺎﺿ\.م\.م|نزﻮﻟا|ﻒﻨﺼﻟا|دوﺮﻄﻟا|ﺔﯿﻛﺮﻤﺠﻟا دﻮﯿﻘﻟا)'
    if re.search(walls_re, line, re.IGNORECASE): 
        return False
    if re.match(r'^[\d\s.,\-]+$', line): 
        return False
    return True
    
def _clean_desc_fragment(t: str) -> str:
    """Removes the sliced vertical margin artifacts from the text."""
    t = re.sub(r'^(?:درﻮﺘ|وا|ﺨﻤﻟا|ﺺﻠ|ﺴﻤﻟا|ت)\s*', '', t)
    t = re.sub(r'^[\u0600-\u06FF\uFE70-\uFEFF]{1,4}\s+(?=[A-Za-z])', '', t)
    if re.match(r'^[\u0600-\u06FF\uFE70-\uFEFF]{1,4}$', t): return ""
    return t.strip()

def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    pages_words = extract_words_with_coords(pdf_path)
    all_rows = []

    # ── 1. Build clean horizontal text rows ──────────────────────────────────
    for page_no, words in enumerate(pages_words, start=1):
        if not words: continue
        
        # Filter out vertical sidebar letters/words on the left margin (typically x0 <= 10.0)
        filtered_words = [w for w in words if w["x0"] > 10.0]
        if not filtered_words: continue
        
        sorted_words = sorted(filtered_words, key=lambda w: w["top"])
        row_groups = []
        current_row = [sorted_words[0]]
        
        for w in sorted_words[1:]:
            if abs(w["top"] - current_row[0]["top"]) <= 9: # Y-Tolerance
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row: row_groups.append(current_row)

        for row in row_groups:
            row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
            if row_str:
                all_rows.append(row_str)

    # ── 1.5. Orphan Number Merger & Noise Removal ────────────────────────────
    # Remove noise rows before checking for line items
    all_rows = [r for r in all_rows if not _BORDER_NOISE_RE.match(r)]

    merged_rows = []
    for row_str in all_rows:
        if re.match(r'^\d{1,2}$', row_str) and merged_rows:
            merged_rows[-1] += f" {row_str}"
        else:
            merged_rows.append(row_str)
    all_rows = merged_rows


    # ── Pre-calculate PT1 indices to establish safe boundaries ───────────────
    pt1_indices = [idx for idx, r in enumerate(all_rows) if _LINE_ITEM_PT1_RE.match(r)]

    # ── 2. Regex Matching (Simple Approach) ──────────────────────────────────
    value_items: dict[int, dict] = {}

    for i, row_str in enumerate(all_rows):
        
        # --- Check Part 1 (Financials & Description) ---
        match_pt1 = _LINE_ITEM_PT1_RE.match(row_str)
        if match_pt1:
            data = match_pt1.groupdict()
            item_no = int(data['item_no'])
            row = value_items.setdefault(item_no, {"ITEM_NO": item_no})

            # --- MULTI-LINE DESCRIPTION SCANNER ---
            # Find our boundaries so we don't accidentally steal text from other items
            my_pos = pt1_indices.index(i)
            prev_i = pt1_indices[my_pos - 1] if my_pos > 0 else -1
            next_i = pt1_indices[my_pos + 1] if my_pos < len(pt1_indices) - 1 else len(all_rows)

            # Establish halfway midpoints
            up_limit = (i + prev_i) // 2
            down_limit = (i + next_i) // 2

            # 1. Scan UP to the midpoint
            up_texts = []
            for j in range(i - 1, up_limit, -1):
                if not _is_stray_text(all_rows[j]): break
                up_texts.insert(0, all_rows[j])

            # 2. Scan DOWN to the midpoint
            down_texts = []
            for j in range(i + 1, down_limit + 1):
                if not _is_stray_text(all_rows[j]): break
                down_texts.append(all_rows[j])

            # 3. Merge and Clean the strings together
            raw_frags = up_texts + [data['description']] + down_texts
            final_desc = " ".join(filter(None, (_clean_desc_fragment(f) for f in raw_frags)))
            # --------------------------------------

            row.update({
                "TOTAL_DUTY_31": clean_number(data.get('total_duty')),
                "INCOME_TYPE_30": clean(data.get('income_type')),
                "D_RATE_29": clean(f"% {data['duty_rate']}") if data.get('duty_rate') else None,
                "CIF_LOCAL_VALUE_28": clean_number(data.get('cif_local')),
                "CURRENCY_VALUE_27": clean_number(data.get('currency_rate')),
                "CURRENCY_TYPE_26": clean(data.get('currency_type')),
                "FOREIGN_VALUE_25": clean_number(data.get('foreign_value')),
                "ORIGIN_24": clean(data.get('origin_country')),
                "GOODS_DESCRIPTION_23": clean(final_desc),
                "HS_CODE_22": clean(data.get('hs_code'))
            })
            continue

        # --- Check Part 2 (Packages & Weights) ---
        match_pt2 = _LINE_ITEM_PT2_RE.match(row_str)
        if match_pt2:
            data = match_pt2.groupdict()
            item_no = int(data['item_no'])
            
            # Initialize dict for this item_no if Part 2 appeared before Part 1
            row = value_items.setdefault(item_no, {"ITEM_NO": item_no})

            row.update({
                "GROSS_WEIGHT_37": clean_number(data.get('gross_weight')),
                "NET_WEIGHT_36": clean_number(data.get('net_weight')),
                "ITEM_UNIT_35": clean(data.get('unit')),
                "ITEM_QTY_34": clean_number(data.get('item_qty')),
                "PKG_QTY_32": clean_number(data.get('package_qty')),
                "PKG_TYPE_33": clean(data.get('package_type')),
                "AIP_DUTY_37B": clean_number(data.get('aip_duty')),
                "AIP_NO_37A": clean(data.get('aip_no')),
                "CUSTOMS_RESTRICTIONS_AGENCY_40": clean(data.get('agency')),
                "CUSTOMS_RELEASE_REF_41": clean(data.get('release_ref')),
                "EXEMPTION_CODE_42": clean(data.get('exemption_code'))
            })

    if not value_items:
        logger.warning(f"[{filename}] No line items matched the regex patterns.")
        return []

    # ── 3. Fill Defaults & Attach Metadata ───────────────────────────────────
    items = []
    for item_no in sorted(value_items.keys()):
        row = value_items[item_no]
        
        defaults = {
            "GROSS_WEIGHT_37": None, "NET_WEIGHT_36": None, "ITEM_UNIT_35": None,
            "ITEM_QTY_34": None, "PKG_QTY_32": None, "PKG_TYPE_33": None,
            "AIP_NO_37A": None, "AIP_DUTY_37B": None, 
            "CUSTOMS_RESTRICTIONS_AGENCY_40": None, "CUSTOMS_RELEASE_REF_41": None, "EXEMPTION_CODE_42": None,
            "TOTAL_DUTY_31": None, "INCOME_TYPE_30": None, "D_RATE_29": None,
            "CIF_LOCAL_VALUE_28": None, "CURRENCY_VALUE_27": None,
            "CURRENCY_TYPE_26": None, "FOREIGN_VALUE_25": None,
            "ORIGIN_24": None, "GOODS_DESCRIPTION_23": None, "HS_CODE_22": None
        }
        
        for k, v in defaults.items():
            row.setdefault(k, v)
            
        row.update({
            "DEC_NO": dec_no,
            "PDF_FILENAME": filename
        })
        items.append(row)

    return items