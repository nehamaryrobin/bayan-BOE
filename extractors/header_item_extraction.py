import re
from app.logger import get_logger
from extractors.pdf_to_text import extract_pages2, extract_pages
from utils.arabic_utils import clean, clean_number

logger = get_logger("header_extractor")

_AR = r'[\u0600-\u06FF\uFE70-\uFEFF]'


# ── Fields 1-4: DEC_NO / DEC_DATE / DEC_TYPE / PORT_TYPE ───────────────

_BOE_VALUE_LINE_RE = re.compile(r"""
    Custom\s+Declaration\s*
    (?P<port_type>جوي|يﻮﺟ|بري|يرب|بحري|يرحب)?\s* # 1. Optional Port Type 
    (?P<dec_type>[\u0600-\u06FF\uFE70-\uFEFF\w\s]+?)\s* # 2. Dec Type (Lazy match Arabic text)
    (?:(?P<date1>\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\s+)? # 3. Optional First Date
    (?P<date2>\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\s+ # 4. Mandatory Second Date
    (?P<dec_no>\d{6,8})                                 # 5. Dec Number (Integers)
""", re.VERBOSE | re.IGNORECASE | re.DOTALL)

_BOE_EXPORT_VALUE_LINE_RE = re.compile(r"""
    ^\s*
    (?P<port_type>[\u0600-\u06FF\uFE70-\uFEFF\w\t /–-]+?)[ \t]{2,}
    (?P<dec_type>Export\s+[\u0600-\u06FF\uFE70-\uFEFF]+?|Export|[\u0600-\u06FF\uFE70-\uFEFF]+?)[ \t]{2,}
    (?P<gregorian_date>\d{2}-\d{2}-\d{4})[ \t]+
    (?:(?P<hijri_date>\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})[ \t]+)?
    [a-zA-Z \t]*(?P<dec_no>\d{6,15})
    \s*$
""", re.VERBOSE | re.IGNORECASE | re.MULTILINE)


# ── Fields 5-7: Delivery / Importer / Net Weight ─────────────────────────

_DELIVERY_ORDER_LINE_RE = re.compile(r"""
    ^\s*
    (?:(?P<unload_date>\d{2}-\d{2}-\d{4})\s*/\s*)?          # 1. OPTIONAL: Unload Date
    (?P<net_weight>[\d,]+(?:\.\d+)?(?:\s*kgs)?)\s{2,}       # 2. MANDATORY: Net Weight (optionally with 'kgs' unit)
    (?P<importer_name>.+?)                                  # 3. MANDATORY: Importer Name
    (?:
        \s{2,}
        (?P<delivery_order>(?:\((?:FCL|LCL)\)\s*)?.+?\s+\d{2}-\d{2}-\d{4}\s+.+)
    )?
    \s*$                                           
""", re.VERBOSE | re.IGNORECASE)


_CARRIER_ROW_RE = re.compile(r"""
    ^\s*
    (?P<gross_weight>[\d,]+(?:\.\d+)?)\s{2,}
    (?P<intercessor>[\u0600-\u06FF\uFE70-\uFEFF\w\s()./–-]+?)                  # 1. Intercessor Co (Field 9) - Matches Arabic text
    (?:
        \s{2,}
        (?P<carrier>.+)                                                         # 2. Carrier/Captain/Driver (Field 8) - Matches remaining text
    )?
    \s*$
""", re.VERBOSE | re.IGNORECASE)


_MEASUREMENT_ROW_RE = re.compile(r"""
    ^\s*
    # 1. OPTIONAL: Measurement (Field 13) - Arabic/English text ending before the big gap
    (?:(?P<measurement>[\u0600-\u06FF\uFE70-\uFEFF\w\s()./–-]+?)(?=\s{3,}))?
    # 2. MANDATORY: Commercial Registration No (Field 12) - Enforces exactly 10 
    (?P<commercial_reg>\d{10}\b)\s+
    # 3. OPTIONAL: Carrier Name (Field 11) - Captures any remaining text at the end of the row
    (?P<carrier_name>.+)?
    \s*$
""", re.VERBOSE | re.IGNORECASE)

_PACKAGES_ROW_RE = re.compile(r"""
    ^ \s*
    (?P<no_of_packages>\d+)\s{3,}               # 1. Number of Packages (Field 16)
    (?P<tin_no>\b[A-Z0-9]{3,15}\b)\s{3,}       # 2. TIN Number (Field 12A) 
    (?P<voyage_flight_no>\w+)                   # 3. Voyage / Flight Number (Field 14)
    \s* $
""", re.VERBOSE | re.IGNORECASE)


_AWB_MANIFEST_LINE_RE = re.compile(r"""
    \b
    (?P<awb_prefix>[A-Za-z])\s*  # 1. Single letter (e.g., M or H)
    (?P<awb_no>\d{5,7})\s+  # 2. 5 to 7 digits (AWB number sequence)
    (?P<bl_indicator>B/L|B)\s+ # 3. B/L or BL indicator
    (?P<manifest_prefix>\d{2,3})\s* # 4. 2 or 3 digits (Manifest prefix)
    [-–]\s*  # 5. Hyphen or dash indicator
    (?P<manifest_no>\d{8})  # 6. Exactly 8 digits (Manifest number sequence)
    \b
""", re.VERBOSE)

_LOOSE_AWB_MANIFEST_RE = re.compile(r"""
    # Optional AWB Part (e.g., "M 2428") followed by optional "B" or "B/L"
    (?:(?P<awb>[A-Za-z]\s*\d+)\s+(?:B/L|B)?\s+)?
    
    # Manifest Part: Captures long alphanumeric sequences or digits (minimum 6 chars)
    (?P<manifest>[A-Za-z0-9]{6,25})
""", re.VERBOSE | re.IGNORECASE)

def _field_failed(field: str, filename: str, dec_no: str) -> None:
    logger.warning(f"FIELD_FAIL | file='{filename}' | dec_no='{dec_no}' | field='{field}'")


def _find_line(lines: list[str], *keywords) -> int:
    """Return index of first line containing ALL keywords.
       Normalizes spaces so layout=True doesn't break keyword matching."""
    for i, line in enumerate(lines):
        norm_line = re.sub(r'\s+', ' ', line)
        if all(k in norm_line for k in keywords):
            return i
    return -1

def _get(lines: list[str], idx: int) -> str:
    return lines[idx].strip() if 0 <= idx < len(lines) else ""


def _search(pattern: str, text: str, flags=re.MULTILINE) -> str | None:
    m = re.search(pattern, text, flags)
    if m:
        val = m.group(1).strip()
        return val if val else None
    return None

def extract_header(pdf_or_pages: str | list[str], filename: str) -> dict:

    pages1 = extract_pages(pdf_or_pages) if isinstance(pdf_or_pages, str) else list(pdf_or_pages)
    lines1 = [l for l in pages1[0].split('\n') if l.strip()]
    text1  = '\n'.join(lines1) 

    pages2 = extract_pages2(pdf_or_pages) if isinstance(pdf_or_pages, str) else list(pdf_or_pages)
    lines2 = [l for l in pages2[0].split('\n') if l.strip()]
    text2  = '\n'.join(lines2) 

    data = {}
    data["PDF_FILENAME"] = filename.rsplit('.', 1)[0]


    # ── Fields 1-4: DEC_NO / DEC_DATE / DEC_TYPE / PORT_TYPE ───────────────
    match = _BOE_VALUE_LINE_RE.search(text2)
    if not match:
        match = _BOE_EXPORT_VALUE_LINE_RE.search(text2)
    if not match:
        raise ValueError(f"[{filename}] Could not extract DEC_NO and header info")
    
    header = match.groupdict()
    data["DEC_NO"]               = clean(header.get("dec_no"))
    data["DEC_TYPE_3"]           = clean(header.get("dec_type"))
    data["PORT_TYPE_4"]          = clean(header.get("port_type"))

    # Parse dates flexibly (supporting either 1 or 2 dates)
    gregorian = clean(header.get("gregorian_date"))
    hijri = clean(header.get("hijri_date"))
    if "date1" in header or "date2" in header:
        d1 = header.get("date1")
        d2 = header.get("date2")
        for d in [d1, d2]:
            if not d:
                continue
            year_match = re.search(r'\b\d{4}\b', d)
            if year_match:
                year = int(year_match.group(0))
                if year >= 2000:
                    gregorian = clean(d)
                else:
                    hijri = clean(d)
    
    data["DEC_DATE_GREGORIAN_2"] = gregorian
    data["DEC_DATE_HIJRI_2"]     = hijri



    # ── Fields 5-7: Delivery / Importer / Net Weight ─────────────────────────
    deliv_lbl = _find_line(lines2, 'DELIVERY ORDER NO', '5')
    deliv_val = _get(lines2, deliv_lbl + 1)

    line_match = _DELIVERY_ORDER_LINE_RE.match(deliv_val)

    if line_match:
        res = line_match.groupdict()
        
        data["DELIVERY_ORDER_NO_5"] = clean(res.get("delivery_order"))
        data["IMPORTER_EXPORTER_6"] = clean(res.get("importer_name"))
        data["UNLOAD_DATE_7A"]       = clean(res.get("unload_date"))
        data["NET_WEIGHT_7B"]        = clean_number(res.get("net_weight"))
    else:
        # Fallback handling in case of layout corruption
        data["DELIVERY_ORDER_NO_5"] = None
        data["IMPORTER_EXPORTER_6"] = None
        data["UNLOAD_DATE_7A"]       = None
        data["NET_WEIGHT_7B"]        = None


    # ── Fields 8-10: Carrier / Intercessor / Gross Weight ────────────────────
    carrier_lbl = _find_line(lines2, 'GROSS WEIGHT', 'INTERCESSOR')
    carrier_val = _get(lines2, carrier_lbl + 1)

    carrier_match = _CARRIER_ROW_RE.match(carrier_val)

    if carrier_match:
        res = carrier_match.groupdict()    
   
        data["GROSS_WEIGHT_10"]          = clean_number(res.get("gross_weight"))
        data["INTERCESSOR_CO_9"]         = clean(res.get("intercessor"))
        data["CARRIER_CAPTAIN_DRIVER_8"] = clean(res.get("carrier"))
    else:
        data["GROSS_WEIGHT_10"]          = None
        data["INTERCESSOR_CO_9"]         = None
        data["CARRIER_CAPTAIN_DRIVER_8"] = None


    # ── Fields 11-13: Carrier Name / Commercial Reg / Measurement ────────────
    meas_lbl = _find_line(lines1, 'MEASUREMENT', 'COMMERCIAL', 'NAME')
    meas_val = _get(lines1, meas_lbl + 1)
    
    reg_match = re.search(r'\b\d{10}(?:\s*[\/\\\-]+\s*\d{10})*\b', meas_val)
    if reg_match:
        data["COMMERCIAL_REG_NO_12"] = reg_match.group(0).replace(" ", "")
        
        # Extract Measurement (left of the 10 digits)
        left_part = meas_val[:reg_match.start()].strip()
        cleaned_meas = clean(left_part)
        if cleaned_meas and "الناقلة" not in cleaned_meas and "اﻟﻨﺎﻗﻠﺔ" not in cleaned_meas:
            data["MEASUREMENT_13"] = cleaned_meas
        else:
            data["MEASUREMENT_13"] = None
            
        # Extract Carrier Name (right of the 10 digits)
        right_part = meas_val[reg_match.end():].strip()
        data["CARRIER_NAME_11"] = clean(right_part)
    else:
        data["MEASUREMENT_13"]       = None
        data["COMMERCIAL_REG_NO_12"] = None
        data["CARRIER_NAME_11"]      = None

    # ── Fields 14-16: Flight / TIN / Packages ────────────────────────────────
    pkg_lbl = _find_line(lines1, 'NO.OF PACKAGES', 'TIN NO')
    if pkg_lbl < 0:
        pkg_lbl = _find_line(lines1, 'NO.OF PACKAGES')
    pkg_val = _get(lines1, pkg_lbl + 1)
    
    cols_14_16 = re.split(r'\s{3,}', pkg_val.strip())
    
    data["PACKAGES_16"]         = clean_number(cols_14_16[0]) if len(cols_14_16) > 0 else None
    
    tin_val = clean(cols_14_16[1]) if len(cols_14_16) > 1 else None
    if tin_val and not re.match(r'^[A-Za-z0-9]{3,15}$', tin_val.replace(" ", "")):
        data["TIN_NO_12A"] = None
    else:
        data["TIN_NO_12A"] = tin_val
        
    data["VOYAGE_FLIGHT_NO_14"] = clean(cols_14_16[2]) if len(cols_14_16) > 2 else None



    # ── Fields 15 & 17: Exported To / AWB & Manifest ─────────────────────────
    def _parse_awb_manifest(text_block: str) -> tuple[str | None, str | None, int | None]:
        """
        Parses AWB number and Manifest number from a given text block.
        Returns a tuple: (awb_no, manifest_no, match_start_index)
        """
        if not text_block:
            return None, None, None

        # 1. Try strict regex first
        strict_match = _AWB_MANIFEST_LINE_RE.search(text_block)
        if strict_match:
            res = strict_match.groupdict()
            prefix = res.get("awb_prefix") if res.get("awb_prefix") else "M"
            awb = f"{prefix} {res.get('awb_no')}"
            manifest = f"{res.get('manifest_prefix')} - {res.get('manifest_no')}"
            return clean(awb), clean(manifest), strict_match.start()

        # 2. Try positional groups (2 or 4 groups)
        parts = text_block.split()
        if len(parts) == 2:
            start_idx = text_block.find(parts[0])
            return clean(parts[0]), clean(parts[1]), start_idx
        elif len(parts) == 4:
            start_idx = text_block.find(parts[0])
            prefix = parts[0] if len(parts[0]) == 1 and parts[0].isalpha() else ""
            awb_val = f"{prefix} {parts[1]}".strip() if prefix else parts[1]
            return clean(awb_val), clean(parts[3]), start_idx

        # 3. Try loose regex match
        loose_match = _LOOSE_AWB_MANIFEST_RE.search(text_block)
        if loose_match:
            res = loose_match.groupdict()
            awb = res.get("awb")
            manifest = res.get("manifest")
            return clean(awb) if awb else None, clean(manifest) if manifest else None, loose_match.start()

        return None, None, None

    def _extract_exported_to(lines: list[str]) -> str | None:
        idx = _find_line(lines, 'EXPORTED TO')
        if idx < 0:
            return None

        val_line = _get(lines, idx + 1)
        if not val_line:
            return None

        # Split the row by wide gaps to isolate the columns
        cols = re.split(r'\s{3,}', val_line.strip())
        if not cols:
            return None

        # Target the absolute right-most block of text (which contains the AWB/Manifest)
        target_col = cols[-1]
        target_start = val_line.find(target_col)
        
        # Parse AWB/Manifest in target_col
        _, _, match_idx = _parse_awb_manifest(target_col)
        
        if match_idx is not None:
            # Slices everything before the start of the AWB/Manifest portion
            left_text = val_line[:target_start + match_idx]
            cleaned_val = clean(left_text)
            
            # Filter out common packages indicator "دﺮﻃ" (Dal Reh Tah) to ensure correct data
            if cleaned_val and not re.search(r'\u062f\u0631\u0637', cleaned_val):
                return cleaned_val

        return None

    data["EXPORTED_TO_15"] = _extract_exported_to(lines1)

    # STEP 1: Try the Strict Multi-Line Global Search
    awb_manifest_matches = _AWB_MANIFEST_LINE_RE.findall(text1)
    
    if awb_manifest_matches:
        awb_list, manifest_list = [], []
        for match in awb_manifest_matches:
            prefix = match[0] if match[0] else "M"
            awb_list.append(f"{prefix} {match[1]}")
            manifest_list.append(f"{match[3]} - {match[4]}")
            
        data["AWB_NO_17A"]      = clean(', '.join(awb_list))
        data["MANIFEST_NO_17B"] = clean(', '.join(manifest_list))

    else:
        # STEP 2: FALLBACK - Positional extraction for Corrupted/Misgenerated Formats
        awb_lbl = _find_line(lines1, 'EXPORTED TO', 'MANIF', '17')
        
        if awb_lbl != -1:
            awb_val = _get(lines1, awb_lbl + 1)
            
            # Split the row by wide gaps to isolate the columns
            cols = re.split(r'\s{3,}', awb_val.strip())
            
            if cols:
                # Target the absolute right-most block of text
                target_col = cols[-1] 
                awb_val_extracted, manifest_val_extracted, _ = _parse_awb_manifest(target_col)
                data["AWB_NO_17A"] = awb_val_extracted
                data["MANIFEST_NO_17B"] = manifest_val_extracted
        else:
            data["AWB_NO_17A"]      = None
            data["MANIFEST_NO_17B"] = None

     # ── Field 19: Marks & Numbers ────────────────────
    marks_idx = _find_line(lines1, 'MARKS', '&', 'NUMBERS')
    
    if marks_idx != -1:
        marks_lines = []
        # Iterate through all lines below the header
        for line in lines1[marks_idx + 1:]:
            # Stop extracting if we hit the boundary noise words
            if 'ESU' in line or 'TNEGA' in line:
                break
            
            # Only append non-empty lines
            if line.strip():
                marks_lines.append(line.strip())
                
        # Join the collected lines into a single string and clean it
        data["MARKS_NUMBERS_19"] = clean(" ".join(marks_lines))
    else:
        data["MARKS_NUMBERS_19"] = None

    # ── Single Value Headers ──────────────────────────────────────────────────
    def _simple_extract(key_1, key_2):
        lbl = _find_line(lines1, key_1, key_2)
        return (_get(lines1, lbl + 1)) if lbl >= 0 else None

    data["PORT_OF_LOADING_18"]   = clean(_simple_extract('PORT OF LOADING', '18'))
    data["PORT_OF_DISCHARGE_20"] = clean(_simple_extract('PORT OF DISCHARGE', '20'))
    data["DESTINATION_21"]       = clean(_simple_extract('DESTINATION', '21'))
    data["CLEARING_AGENT_38"]    = clean(_simple_extract('CLEARING AGENT', '38'))    #>>>>>>

    data["UNIFIED_CUSTOMS_CODE_43"] = _search(r'\b(249\d{9,}|951\d{8,})\b', text2)   #>>>>>>

    #scan upto 5 lines, retrive a 7 digit integer
    aeo_lbl = _find_line(lines1, 'GCC AEO Code', '44')
    limit = _find_line(lines1, 'Other Remarks', '45')
    if limit < 0:
        limit = len(lines1)

    aeo_val = next((_get(lines1, aeo_lbl + i) for i in range(1, 6) if aeo_lbl + i < limit and re.match(r'^\d{7}$', _get(lines1, aeo_lbl + i))), None)
    data["GCC_AEO_CODE_44"] = (aeo_val)
        
    lic_lbl = _find_line(lines1, 'LICENCE NO', '39')
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
        data["LICENCE_NO_39"] = f"{licence_text} {licence_num}"
    else:
        data["LICENCE_NO_39"] = licence_num
   

    # ── Field 45: OTHER_REMARKS ───────────────────────────────────────────────
    rem_idx = _find_line(lines2, 'Other Remarks', '45')
    if rem_idx >= 0:
        rem_val = _get(lines2, rem_idx + 1)
        # Guard: If the next line is the EXIT PORT label, the remarks are empty
        if 'EXIT PORT' in rem_val or '46' in rem_val:
            data["OTHER_REMARKS_45"] = None
        else:
            data["OTHER_REMARKS_45"] = clean(rem_val)
    else:
        data["OTHER_REMARKS_45"] = None

    # ── Field 46: EXIT_PORT ───────────────────────────────────────────────────
    exit_idx = _find_line(lines1, 'EXIT PORT', '46')
    if exit_idx >= 0:
        exit_val = _get(lines1, exit_idx + 1)
        # Guard: If the next line is the QR Code label, the exit port is empty
        if 'QR Code' in exit_val or '47' in exit_val or 'ﺔﻌﯾﺮﺴﻟا' in exit_val:
            data["EXIT_PORT_46"] = None
        else:
            data["EXIT_PORT_46"] = clean(exit_val)
    else:
        data["EXIT_PORT_46"] = None




    # ── Fields 48-52: Duties & Fees ──────────────────────────────────────────
    def _fee(keyword: str, field_no: str) -> float | None:
        idx = _find_line(lines1, keyword, field_no)
        if idx < 0:
            return None
        return clean_number(_search(r'^([\d.]+)', _get(lines1, idx)))

    data["TOTAL_DUTY_48"]    = _fee('TOTAL DUTY',    '48')
    data["VAT_48A"]          = _fee('VAT',           '48A')
    data["EXCISE_TAX_48B"]   = _fee('EXCISE TAX',    '48B')
    data["ANTI_DUMPING_48C"] = _fee('ANTI DUMPING',  '48C')
    data["HANDLING_49"]      = _fee('HANDLING',      '49')
    data["OTHER_CHARGES_50"] = _fee('OTHER CHARGES', '50')

    def_idx = _find_line(lines1, 'DEFINITE', '51')
    data["DEFINITE_51"] = clean_number(_search(r'DEFINITE\s+([\d.]+)', _get(lines1, def_idx))) if def_idx >= 0 else None

    ins_idx = _find_line(lines1, 'INSURED', '52')
    data["INSURED_52"] = clean_number(_search(r'INSURED\s+([\d.]+)', _get(lines1, ins_idx))) if ins_idx >= 0 else None


   
    # ── Fields 53-59: Payment & Receipt Information ──────────────────────────

    # 1. Payment Method (Field 53)
    pm_match = re.search(r"PAYMENT\s+METHOD\s*(?P<val>.{0,50}?)\s*ﻊﻓﺪﻟا\s*ﺔﻘﯾﺮﻃ", text1, re.IGNORECASE | re.DOTALL)
    data["PAYMENT_METHOD_53"] = clean(pm_match.group("val")) if pm_match else None

    # 2. Payment No (Field 54)
    pn_match = re.search(r"\bNO\.?\s*(?P<val>.{0,50}?)\s*ﻢﻗر\s*54", text1, re.IGNORECASE | re.DOTALL)
    data["PAYMENT_NO_54"]     = clean(pn_match.group("val")) if pn_match else None

    # (Optional) Payment Date (Field 55) - Added for completeness
    pd_match = re.search(r"\bDATE\s*(?P<val>.{0,50}?)\s*ﺦﯾرﺎﺗ\s*55", text1, re.IGNORECASE | re.DOTALL)
    data["PAYMENT_DATE_55"]   = clean(pd_match.group("val")) if pd_match else None

    # 3. Payment Bank (Field 56)
    pb_match = re.search(r"\bBANK\s*(?P<val>.{0,50}?)\s*(?:بنك|ﻚﻨﺒﻟا|ﻚﻨﺑ)\s*56", text1, re.IGNORECASE | re.DOTALL)
    data["PAYMENT_BANK_56"] = clean(pb_match.group("val")) if pb_match else None

    # 4. Receipt No (Field 57) 
    rn_match = re.search(r"RECEIPT\s+NO\.?\s*(?P<val>\d+).*?ﻢﻗر\s*57", text1, re.IGNORECASE | re.DOTALL)
    data["RECEIPT_NO_57"] = clean(rn_match.group("val")) if rn_match else None

    # 5. Receipt Date (Field 58)
    rd_match = re.search(r"\bDATE\s*(?P<val>.{0,50}?)\s*ﺦﯾرﺎﺗ\s*58", text1, re.IGNORECASE | re.DOTALL)
    data["RECEIPT_DATE_58"]   = clean(rd_match.group("val")) if rd_match else None

    # 6. Receipt Bank (Field 59)
    rb_match = re.search(r"\bBANK\s*(?P<val>.{0,50}?)\s*(?:بنك|ﻚﻨﺒﻟا|ﻚﻨﺑ)\s*59", text2, re.IGNORECASE | re.DOTALL)
    data["RECEIPT_BANK_59"] = clean(rb_match.group("val")) if rb_match else None



    return data