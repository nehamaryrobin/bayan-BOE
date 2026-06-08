"""
header_extractor.py
Parses BOE header fields from raw PDF text.
Arabic text covers both U+0600-06FF (standard) and U+FE70-FEFF (Presentation Forms-B).
Uses field numbers and known line positions as anchors.
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number

logger = get_logger("header_extractor")

# Both standard Arabic and Presentation Forms-B
_AR = r'[\u0600-\u06FF\uFE70-\uFEFF]'

_NOISE = {
    "ESU", "TNEGA", "S'REIRRAC", "REKORB", "RO", "RETROPMI",
    "ﻹﺳﺘﻌﻤﺎﻻت", "وﻛﯿﻞ", "اﻟﻨﺎﻗﻠﺔ", "اﻟﻤﺴﺘﻮرد",
    "او اﻟﻤﺨﻠﺺ", "اﻟﻤﺨﻠﺺ", "او", "اﻟﺠﻤﺎرك", "QR Code",
}


def _strip_noise(pages: list[str]) -> list[str]:
    out = []
    for page in pages:
        lines = [l for l in page.split('\n') if l.strip() not in _NOISE]
        out.append('\n'.join(lines))
    return out


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


def _arabic_tokens(line: str) -> list[str]:
    """
    Strip dates, numbers, English, punctuation from a line
    and return remaining Arabic tokens (covers both unicode blocks).
    """
    s = re.sub(r'\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}', ' ', line)
    s = re.sub(r'[\d.,/()\\%]+', ' ', s)
    s = re.sub(r'[A-Za-z]+', ' ', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return [t for t in s.split() if re.search(_AR, t)]


def _arabic_str(line: str) -> str:
    return ' '.join(_arabic_tokens(line))


def extract_header(pages: list[str], filename: str) -> dict:
    pages = _strip_noise(pages)
    lines = [l for l in pages[0].split('\n') if l.strip()]
    text  = '\n'.join(lines)
    data  = {}

    # ── Field 1: DEC_NO ───────────────────────────────────────────────────────
    info_idx = _find_line(lines, 'Dec No', 'Dec Date', 'Dec Type')
    val_line = _get(lines, info_idx + 1)

    dec_no = _search(r'\b(\d{6,7})\b', val_line)
    if not dec_no:
        raise ValueError(f"[{filename}] Could not extract DEC_NO")
    data["DEC_NO"] = dec_no

    # ── Field 2: DEC_DATE ─────────────────────────────────────────────────────
    dates = re.findall(r'\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}', val_line)
    if len(dates) >= 2:
        data["DEC_DATE_HIJRI_2"]     = dates[1]   
        data["DEC_DATE_GREGORIAN_2"] = dates[0]   
    else:
        data["DEC_DATE_HIJRI_2"]     = None
        data["DEC_DATE_GREGORIAN_2"] = None

    # ── Field 4: PORT_TYPE ────────────────────────────────────────────────────
    port_type = _search(r'\b(يﻮﺟ|جوي|يرﺑ|بري|يرحب|بحري)\b', val_line)
    data["PORT_TYPE_4"] = clean(port_type) if port_type else None

    # ── Field 3: DEC_TYPE (Cleaned overlap) ───────────────────────────────────
    dec_type_str = re.sub(r'\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}|[A-Za-z]+', ' ', val_line)
    dec_type_str = re.sub(r'يﻮﺟ|جوي|يرﺑ|بري|يرحب|بحري|ﻲــﻛﺮــــــــــﻤﺟ نﺎــــــــﯿـﺑ|بيان جمركي', '', dec_type_str)
    dec_type_tokens = [t for t in dec_type_str.split() if re.search(_AR, t) and len(t) > 2]
    data["DEC_TYPE_3"] = clean(' '.join(dec_type_tokens)) if dec_type_tokens else None


    # ── Fields 5-7: Delivery / Importer / Net Weight ─────────────────────────
    deliv_lbl = _find_line(lines, 'DELIVERY ORDER NO', '5')
    deliv_val = _get(lines, deliv_lbl + 1)

    delivery = _search(r'(\(FCL\).+)$', deliv_val)
    data["DELIVERY_ORDER_NO_5"] = clean(delivery) if delivery else None

    before_fcl = deliv_val.split('(FCL)')[0] if '(FCL)' in deliv_val else deliv_val
    imp_tokens = [t for t in _arabic_tokens(before_fcl) if len(t) > 2]
    data["IMPORTER_EXPORTER_6"] = clean(' '.join(imp_tokens)) if imp_tokens else None

    data["UNLOAD_DATE_7A"] = clean(_search(r'(\d{2}-\d{2}-\d{4})\s*/', deliv_val))
    data["NET_WEIGHT_7B"]  = clean_number(_search(r'/\s*([\d.]+)', deliv_val))


    # ── Fields 8-10: Carrier / Intercessor / Gross Weight ────────────────────
    carrier_lbl = _find_line(lines, 'GROSS WEIGHT', 'INTERCESSOR')
    carrier_val = _get(lines, carrier_lbl + 1)

    # Use layout=True gaps to handle empty Field 8 cleanly
    cols_8_10 = re.split(r'\s{3,}', carrier_val.strip())
    
    data["GROSS_WEIGHT_10"]          = None
    data["INTERCESSOR_CO_9"]         = None
    data["CARRIER_CAPTAIN_DRIVER_8"] = None

    if len(cols_8_10) > 0:
        data["GROSS_WEIGHT_10"] = clean_number(_search(r'^([\d.]+)', cols_8_10[0]))
    if len(cols_8_10) > 1:
        data["INTERCESSOR_CO_9"] = clean(_arabic_str(cols_8_10[1]))
    if len(cols_8_10) > 2:
        data["CARRIER_CAPTAIN_DRIVER_8"] = clean(_arabic_str(cols_8_10[2]))


    # ── Fields 11-13: Carrier Name / Commercial Reg / Measurement ────────────
    meas_lbl = _find_line(lines, 'MEASUREMENT', 'COMMERCIAL REG')
    meas_val = _get(lines, meas_lbl + 1)
    
    cols_11_13 = re.split(r'\s{3,}', meas_val.strip())
    
    data["MEASUREMENT_13"]       = None
    data["COMMERCIAL_REG_NO_12"] = None
    data["CARRIER_NAME_11"]      = None

    if len(cols_11_13) > 0:
        data["MEASUREMENT_13"] = clean(_arabic_str(cols_11_13[0]))
    if len(cols_11_13) > 1:
        data["COMMERCIAL_REG_NO_12"] = clean(_search(r'\b(7\d{9})\b', cols_11_13[1]))
    if len(cols_11_13) > 2:
        data["CARRIER_NAME_11"] = clean(_arabic_str(cols_11_13[2]))


    # ── Fields 14-16: Flight / TIN / Packages ────────────────────────────────
    pkg_lbl = _find_line(lines, 'NO.OF PACKAGES', 'TIN NO')
    pkg_val = _get(lines, pkg_lbl + 1)
    
    cols_14_16 = re.split(r'\s{3,}', pkg_val.strip())
    
    data["PACKAGES_16"]         = None
    data["TIN_NO_12A"]          = None
    data["VOYAGE_FLIGHT_NO_14"] = None

    if len(cols_14_16) > 0:
        data["PACKAGES_16"] = clean_number(cols_14_16[0])
    if len(cols_14_16) > 1:
        data["TIN_NO_12A"] = cols_14_16[1]
    if len(cols_14_16) > 2:
        data["VOYAGE_FLIGHT_NO_14"] = cols_14_16[2]


    # ── Fields 15 & 17 ───────────────────────────────────────────────────────
    awb_lbl = _find_line(lines, 'EXPORTED TO', 'AWB')
    awb_val = _get(lines, awb_lbl + 1)
    
    data["EXPORTED_TO_15"]  = None 
    data["AWB_NO_17A"]      = clean(_search(r'(M\s+\d+)', awb_val))
    
    # Updated regex to capture the full prefix (optional letter + digits), dash, and suffix
    data["MANIFEST_NO_17B"] = clean(_search(r'(\b\d{3}\s*[-–]\s*\d+)', awb_val))


    # ── Single Value Headers ──────────────────────────────────────────────────
    def _simple_extract(key_1, key_2, clean_fn=clean):
        lbl = _find_line(lines, key_1, key_2)
        return clean_fn(_get(lines, lbl + 1)) if lbl >= 0 else None

    data["PORT_OF_LOADING_18"]   = _simple_extract('PORT OF LOADING', '18')
    data["MARKS_NUMBERS_19"]     = _simple_extract('MARKS & NUMBERS', '19')
    data["PORT_OF_DISCHARGE_20"] = _simple_extract('PORT OF DISCHARGE', '20')
    data["DESTINATION_21"]       = _simple_extract('DESTINATION', '21')
    data["CLEARING_AGENT_38"]    = _simple_extract('CLEARING AGENT', '38')

    data["UNIFIED_CUSTOMS_CODE_43"] = _search(r'\b(249\d{9,}|951\d{8,})\b', text)

    aeo_lbl = _find_line(lines, 'GCC AEO Code', '44')
    aeo_val = next((_get(lines, aeo_lbl + i) for i in range(1, 6) if re.match(r'^\d{7}$', _get(lines, aeo_lbl + i))), None)
    data["GCC_AEO_CODE_44"] = clean(aeo_val)
        
    lic_lbl = _find_line(lines, 'LICENCE NO', '39')
    licence_num = next((_get(lines, lic_lbl + i) for i in range(1, 6) if re.match(r'^\d{4}$', _get(lines, lic_lbl + i))), None)
    licence_arabic = next((_get(lines, lic_lbl + i) for i in range(1, 6) if re.search(_AR, _get(lines, lic_lbl + i)) and not re.match(r'^\d', _get(lines, lic_lbl + i))), None)
    
    data["LICENCE_NO_39"] = clean(f"{clean(licence_arabic)} {licence_num}") if licence_arabic and licence_num else licence_num
    data["OTHER_REMARKS_45"] = None
    data["EXIT_PORT_46"]     = None


    # ── Fields 48-52: Duties & Fees ──────────────────────────────────────────
    def _fee(keyword: str, field_no: str) -> float | None:
        idx = _find_line(lines, keyword, field_no)
        if idx < 0: return None
        return clean_number(_search(r'^([\d.]+)', _get(lines, idx)))

    data["TOTAL_DUTY_48"]    = _fee('TOTAL DUTY',    '48')
    data["VAT_48A"]          = _fee('VAT',           '48A')
    data["EXCISE_TAX_48B"]   = _fee('EXCISE TAX',    '48B')
    data["ANTI_DUMPING_48C"] = _fee('ANTI DUMPING',  '48C')
    data["HANDLING_49"]      = _fee('HANDLING',      '49')
    data["OTHER_CHARGES_50"] = _fee('OTHER CHARGES', '50')

    def_idx = _find_line(lines, 'DEFINITE', '51')
    data["DEFINITE_51"] = clean_number(_search(r'DEFINITE\s+([\d.]+)', _get(lines, def_idx))) if def_idx >= 0 else None

    ins_idx = _find_line(lines, 'INSURED', '52')
    data["INSURED_52"] = clean_number(_search(r'INSURED\s+([\d.]+)', _get(lines, ins_idx))) if ins_idx >= 0 else None


    # ── Field 53: PAYMENT_METHOD (Fixed Leak) ─────────────────────────────────
    pay_idx = _find_line(lines, 'PAYMENT METHOD', '53')
    pay_line = _get(lines, pay_idx)
    pay_line = re.sub(r'PAYMENT\s+METHOD|53', '', pay_line, flags=re.IGNORECASE)
    pay_line = re.sub(r'طريقة\s*الدفع|طریقة\s*الدفع|طريقه\s*الدفع|ﻊﻓﺪﻟا\s*ﺔﻘﯾﺮﻃ|ﺔﻘﯾﺮﻃ\s*ﻊﻓﺪﻟا', '', pay_line) 
    data["PAYMENT_METHOD_53"] = clean(_arabic_str(pay_line))

    data["PAYMENT_NO_54"]   = None
    data["PAYMENT_DATE_55"] = None

    # ── Field 56 & 59: Bank Names (Fixed Leak) ────────────────────────────────
    bank_idx = _find_line(lines, 'BANK', '56')
    bank_arabic = _arabic_str(_get(lines, bank_idx))
    bank_arabic = re.sub(r'ﻚﻨﺑ|بنك', '', bank_arabic).strip() # Removed \b boundaries
    data["PAYMENT_BANK_56"] = clean(bank_arabic)

    rbank_idx = _find_line(lines, 'BANK', '59')
    rbank_arabic = _arabic_str(_get(lines, rbank_idx))
    rbank_arabic = re.sub(r'ﻚﻨﺑ|بنك', '', rbank_arabic).strip() # Removed \b boundaries
    data["RECEIPT_BANK_59"] = clean(rbank_arabic)

    # ── Fields 57 & 58: Receipt No / Date ─────────────────────────────────────
    rcpt_idx = _find_line(lines, 'RECEIPT NO', '57')
    data["RECEIPT_NO_57"] = _search(r'RECEIPT NO\.\s+(\d+)', _get(lines, rcpt_idx))

    rdate_idx = _find_line(lines, 'DATE', '58')
    data["RECEIPT_DATE_58"] = _search(r'DATE\s+(\d{2}-\d{2}-\d{4})', _get(lines, rdate_idx))

    # Error logging
    for k, v in data.items():
        if v is None and k not in ("EXPORTED_TO_15", "OTHER_REMARKS_45", "EXIT_PORT_46", "PAYMENT_NO_54", "PAYMENT_DATE_55"):
            _field_failed(k, filename, dec_no)

    data["PDF_FILENAME"] = filename
    return data