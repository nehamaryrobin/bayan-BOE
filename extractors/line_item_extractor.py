"""
line_item_extractor.py
Extracts BOE line items as a coherent tabular group using coordinate boundary mapping.
Uses horizontal visual row grouping, then cleanly processes row text via regex anchors
to bypass column bleeding and handle dynamic page distributions.
"""
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number
from extractors.pdf_to_text import extract_words_with_coords
import re

logger = get_logger("line_item_extractor")

# Map of column field numbers to their corresponding data dictionary keys
FIELD_MAPPING = {
    22: "HS_CODE_22",
    23: "GOODS_DESCRIPTION_23",
    24: "ORIGIN_24",
    25: "FOREIGN_VALUE_25",
    26: "CURRENCY_TYPE_26",
    27: "CURRENCY_VALUE_27",
    28: "CIF_LOCAL_VALUE_28",
    29: "D_RATE_29",
    30: "INCOME_TYPE_30",
    31: "TOTAL_DUTY_31",
}


def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    pages_words = extract_words_with_coords(pdf_path)
    all_final_items = {}

    for page_no, words in enumerate(pages_words, start=1):
        if not words:
            continue

        # 1. Cluster words into clean visual horizontal rows based on vertical 'top' coordinates
        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups = []
        if sorted_words:
            current_row = [sorted_words[0]]
            for w in sorted_words[1:]:
                if abs(w["top"] - current_row[-1]["top"]) <= 6:
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row:
                row_groups.append(current_row)

        # 2. Parse the lines cleanly via anchor segmentations
        for row in row_groups:
            row_str = " ".join([w["text"] for w in sorted(row, key=lambda w: w["x0"])])
            tokens = row_str.strip().split()

            # ── A. Parse Package Grid Rows ──
            # Look at the sequence of the last 4 to 5 tokens, ignoring any header garbage at the front.
            # Sequence: ... [Gross] [Net] [Unit] [Qty] [ItemNo]
            if len(tokens) >= 4:
                item_no_str = tokens[-1]
                qty_str = tokens[-2]
                net_str = tokens[-4]

                # Verify it fits the strict package signature: ends in an item number (<40 to block phantom row 48)
                if item_no_str.isdigit() and int(item_no_str) < 40:
                    # Verify the weight/qty positions are actually numbers
                    if re.match(r'^[\d.,]+$', qty_str) and re.match(r'^[\d.,]+$', net_str):
                        item_no = int(item_no_str)
                        unit_str = tokens[-3]
                        gross_str = tokens[-5] if len(tokens) >= 5 else net_str

                        if item_no not in all_final_items:
                            all_final_items[item_no] = _create_empty_item(item_no, dec_no, filename)

                        all_final_items[item_no].update({
                            "GROSS_WEIGHT_37": clean_number(gross_str),
                            "NET_WEIGHT_36":   clean_number(net_str),
                            "ITEM_UNIT_35":    clean(unit_str),
                            "ITEM_QTY_34":     clean_number(qty_str),
                            "PKG_QTY_32":      1.0,
                        })
                        continue

            # ── B. Parse Main Value Rows ──
            # Drop the '$' anchor so trailing margin junk doesn't break the regex
            value_match = re.search(r'\b(\d{10,12})\s+(\d{1,2})\b', row_str)
            if value_match:
                item_no = int(value_match.group(2))
                hs_code = value_match.group(1)
                
                # Block phantom items captured by rogue numbers
                if item_no >= 40:
                    continue

                # Slice the string BEFORE the HS code. This entirely cuts off any margin garbage.
                body_str = row_str[:value_match.start()].strip()
                
                parsed_values = _parse_value_row_string(body_str, hs_code)

                if item_no not in all_final_items:
                    all_final_items[item_no] = _create_empty_item(item_no, dec_no, filename)

                all_final_items[item_no].update(parsed_values)

    return sorted(all_final_items.values(), key=lambda x: x["ITEM_NO"])


def _parse_value_row_string(body: str, hs_code: str) -> dict:
    """Parses isolated row body strings using exact token sequence matching."""
    item_data = {}

    # 1. Currency Type
    curr_m = re.search(r'\b(SAR|USD|EUR|AED)\b', body)
    currency_type = curr_m.group(1) if curr_m else None
    item_data["CURRENCY_TYPE_26"] = currency_type

    # 2. Origin Country
    origin_m = re.search(r'\b([A-Z]{2})\b', body)
    item_data["ORIGIN_24"] = origin_m.group(1) if (origin_m and origin_m.group(1) not in {"SAR", "USD", "EUR", "AED"}) else None

    # 3. Income Classification Type
    if "معفي" in body or "ﻲﻔﻌﻣ" in body:
        item_data["INCOME_TYPE_30"] = "معفي ت"
    else:
        item_data["INCOME_TYPE_30"] = "قطعي"

    # 4. Duty Tax Rate Percentage
    rate_m = re.search(r'%\s*(\d+)', body)
    item_data["D_RATE_29"] = float(rate_m.group(1)) / 100 if rate_m else 0.0

    # 5. Financial Matrices
    num_segment = body.split(currency_type)[0] if currency_type else body
    nums = [clean_number(n) for n in re.findall(r'[\d,]+\.?\d*', num_segment) if clean_number(n) is not None]

    if len(nums) >= 3:
        item_data["TOTAL_DUTY_31"]      = nums[0]
        item_data["CIF_LOCAL_VALUE_28"] = nums[1]
        item_data["CURRENCY_VALUE_27"]  = nums[2]
        item_data["FOREIGN_VALUE_25"]   = nums[1] if len(nums) == 3 else nums[3]
    else:
        item_data["TOTAL_DUTY_31"]      = nums[0] if len(nums) > 0 else 0.0
        item_data["CIF_LOCAL_VALUE_28"] = nums[1] if len(nums) > 1 else None
        item_data["CURRENCY_VALUE_27"]  = 1.0
        item_data["FOREIGN_VALUE_25"]   = nums[1] if len(nums) > 1 else None

    # 6. Goods Description
    arabic_blocks = re.findall(r'[\u0600-\u06FF][^\d\n]{2,}', body)
    item_data["GOODS_DESCRIPTION_23"] = clean(" ".join(arabic_blocks)) if arabic_blocks else None
    
    item_data["HS_CODE_22"] = hs_code

    return item_data


def _create_empty_item(item_no: int, dec_no: str, filename: str) -> dict:
    """Initializes schema item dictionary with strict key continuity."""
    return {
        "ITEM_NO": item_no,
        "DEC_NO": dec_no,
        "PDF_FILENAME": filename,
        "HS_CODE_22": None,
        "GOODS_DESCRIPTION_23": None,
        "ORIGIN_24": None,
        "FOREIGN_VALUE_25": None,
        "CURRENCY_TYPE_26": None,
        "CURRENCY_VALUE_27": None,
        "CIF_LOCAL_VALUE_28": None,
        "D_RATE_29": None,
        "INCOME_TYPE_30": None,
        "TOTAL_DUTY_31": None,
        "GROSS_WEIGHT_37": None,
        "NET_WEIGHT_36": None,
        "ITEM_UNIT_35": None,
        "ITEM_QTY_34": None,
        "PKG_QTY_32": None,
    }