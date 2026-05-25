"""
line_item_extractor.py
Semantic Anchor & Sequence Parser for Saudi BOE Layouts.
Uses strict baseline anchoring to prevent header-chaining, then plucks
explicitly typed data from the cleanly isolated row strings.
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number
from extractors.pdf_to_text import extract_words_with_coords

logger = get_logger("line_item_extractor")

def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    pages_words = extract_words_with_coords(pdf_path)
    all_final_items = {}

    for page_no, words in enumerate(pages_words, start=1):
        if not words:
            continue

        # ── 1. Create Clean Horizontal Text Strings (STRICT BASELINE) ──
        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups = []
        if sorted_words:
            current_row = [sorted_words[0]]
            for w in sorted_words[1:]:
                # BUG FIX: Compare against current_row[0] to prevent "staircase" merging
                if abs(w["top"] - current_row[0]["top"]) <= 6:
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row:
                row_groups.append(current_row)

        # ── 2. Classify and Extract ──
        for row in row_groups:
            row_str = " ".join([w["text"] for w in sorted(row, key=lambda w: w["x0"])]).strip()
            
            # --- PATH A: MAIN ITEM ROW ---
            hs_match = re.search(r'\b(\d{10,12})\b', row_str)
            
            if hs_match:
                hs_code = hs_match.group(1)
                item_match = re.search(r'\b(\d{1,2})\s*$', row_str)
                if not item_match:
                    continue 
                    
                item_no = int(item_match.group(1))
                
                if item_no not in all_final_items:
                    all_final_items[item_no] = _create_empty_item(item_no, dec_no, filename)
                
                parsed_main = _parse_main_sequence(row_str, hs_code, item_no)
                all_final_items[item_no].update(parsed_main)
                continue

            # --- PATH B: PACKAGE ITEM ROW ---
            # Trigger: Ends in 1-2 digits, contains decimals, and is not a main line
            if not hs_match and re.search(r'\b\d{1,2}\s*$', row_str):
                # Ensure it has the visual signature of a package line (multiple float numbers)
                float_count = len(re.findall(r'\b\d+\.\d+\b', row_str))
                if float_count >= 2:
                    item_match = re.search(r'\b(\d{1,2})\s*$', row_str)
                    if item_match:
                        item_no = int(item_match.group(1))
                        
                        if item_no not in all_final_items:
                            all_final_items[item_no] = _create_empty_item(item_no, dec_no, filename)
                            
                        parsed_pkg = _parse_package_sequence(row_str, item_no)
                        all_final_items[item_no].update(parsed_pkg)

    return sorted(all_final_items.values(), key=lambda x: x["ITEM_NO"])


def _parse_main_sequence(row_str: str, hs_code: str, item_no: int) -> dict:
    data: dict = {"HS_CODE_22": hs_code}
    
    # 1. Clean the string
    body = re.sub(r'\b' + re.escape(hs_code) + r'\b', ' ', row_str)
    body = re.sub(r'\b' + str(item_no) + r'\s*$', ' ', body)
    
    # 2. Pluck Tax Rate
    rate_m = re.search(r'%\s*(\d+)', body)
    data["D_RATE_29"] = float(rate_m.group(1)) / 100 if rate_m else 0.0
    if rate_m:
        body = body.replace(rate_m.group(0), ' ')

    # 3. Pluck Currency
    curr_m = re.search(r'\b(SAR|USD|EUR|AED)\b', body)
    data["CURRENCY_TYPE_26"] = curr_m.group(1) if curr_m else None
    if curr_m:
        body = body.replace(curr_m.group(0), ' ')

    # 4. Pluck Origin (2 Letters)
    origin_m = re.search(r'\b([A-Z]{2})\b', body)
    data["ORIGIN_24"] = origin_m.group(1) if origin_m else None
    if origin_m:
        body = body.replace(origin_m.group(0), ' ')

    # 5. Pluck Income Type
    if "معفي" in body or "ﻲﻔﻌﻣ" in body:
        data["INCOME_TYPE_30"] = "معفي ت"
        body = re.sub(r'(معفي|ت|ﻲﻔﻌﻣ)', ' ', body)
    else:
        data["INCOME_TYPE_30"] = "قطعي"
        body = re.sub(r'(قطعي|ﻲﻌﻄﻗ)', ' ', body)

    # 6. Extract Arabic Description
    arabic_blocks = re.findall(r'[\u0600-\u06FF][^\d\n]{2,}', body)
    data["GOODS_DESCRIPTION_23"] = clean(" ".join(arabic_blocks)) if arabic_blocks else None

    # 7. Extract Financial Sequences
    nums = [clean_number(n) for n in re.findall(r'[\d,]+\.?\d*', body) if clean_number(n) is not None]
    
    if len(nums) >= 4:
        data["TOTAL_DUTY_31"]      = nums[0]
        data["CIF_LOCAL_VALUE_28"] = nums[1]
        data["CURRENCY_VALUE_27"]  = nums[2]
        data["FOREIGN_VALUE_25"]   = nums[3]
    elif len(nums) == 3:
        data["TOTAL_DUTY_31"]      = 0.0
        data["CIF_LOCAL_VALUE_28"] = nums[0]
        data["CURRENCY_VALUE_27"]  = nums[1]
        data["FOREIGN_VALUE_25"]   = nums[2]
    else:
        data["TOTAL_DUTY_31"]      = nums[0] if len(nums) > 0 else 0.0
        data["CIF_LOCAL_VALUE_28"] = nums[1] if len(nums) > 1 else None
        data["CURRENCY_VALUE_27"]  = 1.0
        data["FOREIGN_VALUE_25"]   = nums[1] if len(nums) > 1 else None

    return data


def _parse_package_sequence(row_str: str, item_no: int) -> dict:
    data: dict = {"PKG_QTY_32": 1.0}
    
    # Remove the trailing item number 
    body = re.sub(r'\b' + str(item_no) + r'\s*$', ' ', row_str)
    
    # 1. Extract Unit Name (Greedy match to fix fractured Arabic spacing like ﻭﺣﺪ ﺓ)
    # Replaces spacing inside Arabic words to heal the token
    arabic_only = "".join(re.findall(r'[\u0600-\u06FF]+', body))
    data["ITEM_UNIT_35"] = clean(arabic_only) if arabic_only else "وحدة"
    
    # 2. Extract Numbers
    nums = [clean_number(n) for n in re.findall(r'[\d,]+\.?\d*', body) if clean_number(n) is not None]
    
    if len(nums) >= 3:
        data["GROSS_WEIGHT_37"] = nums[0]
        data["NET_WEIGHT_36"]   = nums[1]
        data["ITEM_QTY_34"]     = nums[2]
    elif len(nums) == 2:
        data["GROSS_WEIGHT_37"] = nums[0]
        data["NET_WEIGHT_36"]   = nums[0]
        data["ITEM_QTY_34"]     = nums[1]
    else:
        data["GROSS_WEIGHT_37"] = nums[0] if len(nums) > 0 else None
        data["NET_WEIGHT_36"]   = nums[0] if len(nums) > 0 else None
        data["ITEM_QTY_34"]     = 1.0
        
    return data


def _create_empty_item(item_no: int, dec_no: str, filename: str) -> dict:
    return {
        "ITEM_NO": item_no, "DEC_NO": dec_no, "PDF_FILENAME": filename,
        "HS_CODE_22": None, "GOODS_DESCRIPTION_23": None, "ORIGIN_24": None,
        "FOREIGN_VALUE_25": None, "CURRENCY_TYPE_26": None, "CURRENCY_VALUE_27": None,
        "CIF_LOCAL_VALUE_28": None, "D_RATE_29": None, "INCOME_TYPE_30": None, "TOTAL_DUTY_31": None,
        "GROSS_WEIGHT_37": None, "NET_WEIGHT_36": None, "ITEM_UNIT_35": None, "ITEM_QTY_34": None, "PKG_QTY_32": None,
        "PKG_TYPE_33": None, "AIP_NO_37A": None, "AIP_DUTY_37B": None, "CUSTOMS_RESTRICTIONS_AGENCY_40": None,
        "CUSTOMS_RELEASE_REF_41": None, "EXEMPTION_OF_DUTY_CODE": None
    }