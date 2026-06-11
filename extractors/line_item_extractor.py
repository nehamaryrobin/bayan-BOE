import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number
from extractors.pdf_to_text import extract_words_with_coords

logger = get_logger("line_item_extractor")

# Single uppercase English letters/pairs that are vertical border noise fragments
_BORDER_NOISE_RE = re.compile(r'^[A-Z]{1,3}$')
_NOISE = {"ESU", "TNEGA", "S'REIRRAC", "REKORB", "RO", "RETROPMI", "ﻹﺳﺘﻌﻤﺎﻻت", "وﻛﯿﻞ", "اﻟﻨﺎﻗﻠﺔ", "اﻟﻤﺴﺘﻮرد", "او اﻟﻤﺨﻠﺺ", "اﻟﻤﺨﻠﺺ", "او", "اﻟﺠﻤﺎرك", "QR Code"}

_LINE_ITEM_PT1_RE = re.compile(r"""
    ^.*? (?P<total_duty>[\d,]+(?:\.\d+)?)\s+          # <-- UPDATE: ^.*? ignores leading garbage text
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
    ^.*?                                              # <-- UPDATE: ^.*? ignores leading garbage text here too
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



def _clean_row(row_str: str) -> str:
    tokens = row_str.split()
    while tokens and _BORDER_NOISE_RE.match(tokens[0]):
        tokens.pop(0)
    while tokens and _BORDER_NOISE_RE.match(tokens[-1]):
        tokens.pop()
    # Collapse all internal whitespace to single spaces
    return ' '.join(tokens)


def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    pages_words = extract_words_with_coords(pdf_path)
    all_rows = []

    # ── 1. Build clean horizontal text rows ──────────────────────────────────
    for page_no, words in enumerate(pages_words, start=1):
        if not words: continue
        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups = []
        current_row = [sorted_words[0]]
        
        for w in sorted_words[1:]:
            if abs(w["top"] - current_row[0]["top"]) <= 8:
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row: row_groups.append(current_row)

        for row in row_groups:
            row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
            row_str = _clean_row(row_str)
            if row_str and row_str not in _NOISE:
                all_rows.append(row_str)

    # ── 2. Regex Matching & Merging ──────────────────────────────────────────
    value_items: dict[int, dict] = {}

    for row_str in all_rows:
        # Check if row matches Part 1 (Financials & Description)
        match_pt1 = _LINE_ITEM_PT1_RE.match(row_str)
        if match_pt1:
            data = match_pt1.groupdict()
            item_no = int(data['item_no'])
            
            if item_no not in value_items:
                value_items[item_no] = {"ITEM_NO": item_no}
                
            duty_rate = float(data['duty_rate']) / 100 if data['duty_rate'] else None

            value_items[item_no].update({
                "TOTAL_DUTY_31": clean_number(data['total_duty']),
                "INCOME_TYPE_30": clean(data['income_type']),
                "D_RATE_29": duty_rate,
                "CIF_LOCAL_VALUE_28": clean_number(data['cif_local']),
                "CURRENCY_VALUE_27": clean_number(data['currency_rate']),
                "CURRENCY_TYPE_26": clean(data['currency_type']),
                "FOREIGN_VALUE_25": clean_number(data['foreign_value']) if data['foreign_value'] else None,
                "ORIGIN_24": clean(data['origin_country']),
                "GOODS_DESCRIPTION_23": clean(data['description']),
                "HS_CODE_22": data['hs_code']
            })
            continue 

        # Check if row matches Part 2 (Packages & Weights)
        match_pt2 = _LINE_ITEM_PT2_RE.match(row_str)
        if match_pt2:
            data = match_pt2.groupdict()
            item_no = int(data['item_no'])
            
            if item_no not in value_items:
                value_items[item_no] = {"ITEM_NO": item_no}

            value_items[item_no].update({
                "GROSS_WEIGHT_37": clean_number(data['gross_weight']),
                "NET_WEIGHT_36": clean_number(data['net_weight']),
                "ITEM_UNIT_35": clean(data['unit']),
                "ITEM_QTY_34": clean_number(data['item_qty']),
                "PKG_QTY_32": clean_number(data['package_qty']) if data['package_qty'] else None,
                "PKG_TYPE_33": clean(data['package_type']) if data['package_type'] else None,
                "AIP_DUTY_37B": clean_number(data['aip_duty']) if data['aip_duty'] else None,
                "AIP_NO_37A": data['aip_no'],
                "CUSTOMS_RESTRICTIONS_AGENCY_40": clean(data['agency']) if data['agency'] else None,
                "CUSTOMS_RELEASE_REF_41": data['release_ref']
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
            "CUSTOMS_RESTRICTIONS_AGENCY_40": None, "CUSTOMS_RELEASE_REF_41": None,
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