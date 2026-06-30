import re
from app.logger import get_logger
from extractors.pdf_to_text import extract_words_with_coords
from utils.arabic_utils import clean, clean_number, fix_arabic
from db.models import BoeLineItem

logger = get_logger("line_item_extraction")

# Module constants for efficiency
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
    (?:(?P<exemption_code>\d{1,12})\s+)?                              
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


class LineItemExtractor:
    """Object-oriented parser class to isolate line items table row parsing and clustering."""

    def __init__(self, pdf_path: str, filename: str, dec_no: str):
        self.pdf_path = pdf_path
        self.filename = filename.rsplit('.', 1)[0]
        self.dec_no = dec_no
        self.all_rows = []
        self.all_tops = []
        self.all_pages = []

    def _is_stray_text(self, line: str) -> bool:
        """Returns True if the line is orphaned text (not a main row or header)."""
        if _LINE_ITEM_PT1_RE.match(line) or _LINE_ITEM_PT2_RE.match(line): 
            return False
            
        walls_re = r'(VALUE TYPE|ORIGIN|DESCRIPTION|H\.S\.CODE|MARKS & NUMBERS|WEIGHT|ITEM|PACKAGES|CUSTOMS RESTRICTIONS|AIP|تاءﺎﻔﻋﻹا ﺰﻣر 42|ةرﺎﺿ\.م\.م|نزﻮﻟا|ﻒﻨﺼﻟا|دوﺮﻄﻟا|ﺔﯿﻛﺮﻤﺠﻟا دﻮﯿﻘﻟا)'
        if re.search(walls_re, line, re.IGNORECASE): 
            return False
            
        if re.search(r'\bTYPE\b', line, re.IGNORECASE):
            header_words = r'\b(?:Port|Dec|Value|Income|Type|Qty|Unit|Gross|Net|Rate|Duty|No|Code|Description|Origin|H\.S\.Code)\b'
            arabic_header_words = r'(عﻮﻨﻟا|عﻮﻧ|ﺬﻔﻨﻤﻟا|نﺎﯿﺒﻟا|ﺦﯾرﺎﺗ|ﻢﻗر|ﺔﻠﻤﻌﻟا|ﺮﻌﺴﻟا|ﺔﻤﯿﻘﻟا|ﺔﯿﻠﺤﻤﻟا|مﻮﺳﺮﻟا|ﻒﻨﺼﻟا|نزﻮﻟا|دوﺮﻄﻟا|ﺔﯿﻛﺮﻤﺠﻟا|دﻮﯿﻘﻟا|تاءﺎﻔﻋﻹا|ﺰﻣر|ةرﺎﺿ|م|م)'
            cleaned = re.sub(header_words, '', line, flags=re.IGNORECASE)
            cleaned = re.sub(arabic_header_words, '', cleaned)
            cleaned = re.sub(r'[\d\s.,\-()\[\]"\'%&/]+', '', cleaned).strip()
            if not cleaned:
                return False

        if re.match(r'^[\d\s.,\-]+$', line): 
            return False
            
        return True

    def _clean_desc_fragment(self, t: str) -> str:
        """Removes the sliced vertical margin artifacts from the text."""
        t = re.sub(r'^\s*\bTYPE\b\s*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s*\bTYPE\b\s*$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'^(?:درﻮﺘ|وا|ﺨﻤﻟا|ﺺﻠ|ﺴﻤﻟا|ت)\s*', '', t)
        t = re.sub(r'^[\u0600-\u06FF\uFE70-\uFEFF]{1,4}\s+(?=[A-Za-z])', '', t)
        if re.match(r'^[\u0600-\u06FF\uFE70-\uFEFF]{1,4}$', t): 
            return ""
        return t.strip()

    def extract(self) -> list[BoeLineItem]:
        pages_words = extract_words_with_coords(self.pdf_path)

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
                if abs(w["top"] - current_row[0]["top"]) <= 5: # Y-Tolerance
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row: 
                row_groups.append(current_row)

            for row in row_groups:
                row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
                if row_str:
                    self.all_rows.append(row_str)
                    self.all_tops.append(sum(w["top"] for w in row) / len(row))
                    self.all_pages.append(page_no)

        # ── 1.5. Noise Removal ────────────────────────────
        valid_indices = [i for i, r in enumerate(self.all_rows) if not _BORDER_NOISE_RE.match(r)]
        self.all_rows  = [self.all_rows[i] for i in valid_indices]
        self.all_tops  = [self.all_tops[i] for i in valid_indices]
        self.all_pages = [self.all_pages[i] for i in valid_indices]

        # Pre-calculate PT1 indices to establish safe boundaries
        pt1_indices = [idx for idx, r in enumerate(self.all_rows) if _LINE_ITEM_PT1_RE.match(r)]

        # ── 2. Regex Matching ──────────────────────────────────
        value_items: dict[int, dict] = {}

        for i, row_str in enumerate(self.all_rows):
            
            # --- Check Part 1 (Financials & Description) ---
            match_pt1 = _LINE_ITEM_PT1_RE.match(row_str)
            if match_pt1:
                data = match_pt1.groupdict()
                item_no = int(data['item_no'])
                row = value_items.setdefault(item_no, {"ITEM_NO": item_no})

                # --- MULTI-LINE DESCRIPTION SCANNER ---
                my_pos = pt1_indices.index(i)
                prev_i = pt1_indices[my_pos - 1] if my_pos > 0 else -1
                next_i = pt1_indices[my_pos + 1] if my_pos < len(pt1_indices) - 1 else len(self.all_rows)

                # 1. Scan UP (assign if closer to this PT1 row than to prev PT1 row)
                up_texts = []
                for j in range(i - 1, prev_i, -1):
                    if self._is_stray_text(self.all_rows[j]):
                        dist_to_me = abs(self.all_tops[j] - self.all_tops[i])
                        dist_to_prev = abs(self.all_tops[j] - self.all_tops[prev_i]) if (prev_i != -1 and self.all_pages[j] == self.all_pages[prev_i]) else float('inf')
                        
                        if dist_to_me <= dist_to_prev:
                            up_texts.insert(0, self.all_rows[j])
                        else:
                            break
                    else:
                        break

                # 2. Scan DOWN (assign if closer to this PT1 row than to next PT1 row)
                down_texts = []
                for j in range(i + 1, next_i):
                    if self._is_stray_text(self.all_rows[j]):
                        dist_to_me = abs(self.all_tops[j] - self.all_tops[i])
                        dist_to_next = abs(self.all_tops[j] - self.all_tops[next_i]) if (next_i != len(self.all_rows) and self.all_pages[j] == self.all_pages[next_i]) else float('inf')
                        
                        if dist_to_me <= dist_to_next:
                            down_texts.append(self.all_rows[j])
                        else:
                            break
                    else:
                        break

                raw_frags = up_texts + [data['description']] + down_texts
                final_desc = " ".join(filter(None, (self._clean_desc_fragment(fix_arabic(f)) for f in raw_frags)))

                row.update({
                    "TOTAL_DUTY_31": clean_number(data.get('total_duty')),
                    "INCOME_TYPE_30": clean(data.get('income_type')),
                    "D_RATE_29": clean(f"% {data['duty_rate']}") if data.get('duty_rate') else None,
                    "CIF_LOCAL_VALUE_28": clean_number(data.get('cif_local')),
                    "CURRENCY_VALUE_27": clean_number(data.get('currency_rate')),
                    "CURRENCY_TYPE_26": clean(data.get('currency_type')),
                    "FOREIGN_VALUE_25": clean_number(data.get('foreign_value')),
                    "ORIGIN_24": clean(data.get('origin_country')),
                    "GOODS_DESCRIPTION_23": final_desc.strip() if final_desc else None,
                    "HS_CODE_22": clean(data.get('hs_code'))
                })
                continue

            # --- Check Part 2 (Packages & Weights) ---
            match_pt2 = _LINE_ITEM_PT2_RE.match(row_str)
            if match_pt2:
                data = match_pt2.groupdict()
                item_no = int(data['item_no'])
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
            logger.warning(f"[{self.filename}] No line items matched the regex patterns.")
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
                "DEC_NO": self.dec_no,
                "PDF_FILENAME": self.filename
            })
            items.append(BoeLineItem(**row))

        return items


def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    """Wrapper function to preserve backwards compatibility with procedural calls."""
    extractor = LineItemExtractor(pdf_path, filename, dec_no)
    line_items = extractor.extract()
    return [item.to_dict() for item in line_items]