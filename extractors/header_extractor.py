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
    """Return index of first line containing ALL keywords."""
    for i, line in enumerate(lines):
        if all(k in line for k in keywords):
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
    # Work on page 1 — all header fields are here
    lines = [l for l in pages[0].split('\n') if l.strip()]
    text  = '\n'.join(lines)
    data  = {}

    # ── Field 1: DEC_NO — 7-digit number on line 5 ───────────────────────────
    # Line 5: "Custom Declaration يﻮﺟ داﺮﯿﺘﺳإ نﺎﯿﺑ 21-04-2026 1447-11-04 1247350 ..."
    info_idx = _find_line(lines, 'Dec No', 'Dec Date', 'Dec Type')
    val_line = _get(lines, info_idx + 1)

    dec_no = _search(r'\b(\d{6,7})\b', val_line)
    if not dec_no:
        raise ValueError(f"[{filename}] Could not extract DEC_NO")
    data["DEC_NO"] = dec_no

    # ── Field 2: DEC_DATE — two date formats on same line ────────────────────
    # "21-04-2026 1447-11-04" → store as "1447-11-04 / 21-04-2026"
    dates = re.findall(r'\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2}', val_line)
    if len(dates) >= 2:
        data["DEC_DATE_HIJRI_2"]     = dates[1]   # 1447-11-04
        data["DEC_DATE_GREGORIAN_2"] = dates[0]   # 21-04-2026
    else:
        data["DEC_DATE_HIJRI_2"]     = None
        data["DEC_DATE_GREGORIAN_2"] = None
        _field_failed("DEC_DATE_HIJRI_2", filename, dec_no)
        _field_failed("DEC_DATE_GREGORIAN_2", filename, dec_no)

    # ── Field 3: DEC_TYPE — Arabic declaration type on same line ─────────────
    # Contains "داﺮﯿﺘﺳإ نﺎﯿﺑ" (import declaration) in mixed unicode
    dec_type_tokens = _arabic_tokens(val_line)
    # Remove short noise tokens (بيان جمركي fragments), keep meaningful ones
    dec_type = ' '.join([t for t in dec_type_tokens if len(t) > 2])
    if not dec_type:
        _field_failed("DEC_TYPE_3", filename, dec_no)
    data["DEC_TYPE_3"] = clean(dec_type) if dec_type else None

    # ── Field 4: PORT_TYPE — يﻮﺟ (air) on same line ─────────────────────────
    port_type = _search(r'\b(يﻮﺟ|جوي|يرﺑ|بري|يرحب|بحري)\b', val_line)
    if not port_type:
        _field_failed("PORT_TYPE_4", filename, dec_no)
    data["PORT_TYPE_4"] = clean(port_type) if port_type else None

    # ── Fields 5-7: Delivery / Importer / Net Weight ─────────────────────────
    # Label line 6: "NET WEIGHT/UNLOAD DATE 7  IMPORTER/EXPORTER 6  DELIVERY ORDER NO. 5"
    # Value line 7: "03-11-1447 / 33.5  شركة سيسكو ...  (FCL) حاوية  03-11-1447  96185253"
    deliv_lbl = _find_line(lines, 'DELIVERY ORDER NO', '5')
    deliv_val = _get(lines, deliv_lbl + 1)

    # Field 5: 8-digit delivery order number
    delivery = _search(r'(\(FCL\).+)$', deliv_val)
    if not delivery:
        _field_failed("DELIVERY_ORDER_NO_5", filename, dec_no)
    data["DELIVERY_ORDER_NO_5"] = clean(delivery)

    # Field 6: Arabic company name — longest Arabic token sequence after stripping
    before_fcl = deliv_val.split('(FCL)')[0] if '(FCL)' in deliv_val else deliv_val
    imp_tokens = _arabic_tokens(before_fcl)
    imp_tokens = [t for t in imp_tokens if len(t) > 2]
    importer = ' '.join(imp_tokens) if imp_tokens else None
    if not importer:
        _field_failed("IMPORTER_EXPORTER_6", filename, dec_no)
    data["IMPORTER_EXPORTER_6"] = clean(importer)

    # Field 7: "03-11-1447 / 33.5"
    unload_date = _search(r'(\d{2}-\d{2}-\d{4})\s*/', deliv_val)
    net_weight  = _search(r'/\s*([\d.]+)', deliv_val)
    if not unload_date:
        _field_failed("UNLOAD_DATE_7A", filename, dec_no)
    if not net_weight:
        _field_failed("NET_WEIGHT_7B", filename, dec_no)
    data["UNLOAD_DATE_7A"] = clean(unload_date)
    data["NET_WEIGHT_7B"]  = clean_number(net_weight)

    # ── Fields 8-10: Carrier / Intercessor / Gross Weight ────────────────────
    # Label line 8: "GROSS WEIGHT 10  INTERCESSOR CO. 9  CARRIER'S/CAPTAIN/DRIVER 8"
    # Value line 9: "33.5  شركة سيسكو العربية السعودية المحدودة"
    carrier_lbl = _find_line(lines, 'GROSS WEIGHT', 'INTERCESSOR')
    carrier_val = _get(lines, carrier_lbl + 1)

    # Field 10: first number on value line
    gross = _search(r'^([\d.]+)', carrier_val)
    data["GROSS_WEIGHT_10"] = clean_number(gross)
    if not gross:
        _field_failed("GROSS_WEIGHT_10", filename, dec_no)

    # Fields 8 & 9: Arabic company name (same value for both in this BOE)
    car_tokens = [t for t in _arabic_tokens(carrier_val) if len(t) > 2]
    company = ' '.join(car_tokens) if car_tokens else None
    data["CARRIER_CAPTAIN_DRIVER_8"] = clean(company) if company else None
    data["INTERCESSOR_CO_9"]         = clean(company) if company else None
    

    # ── Fields 11-13: Carrier Name / Commercial Reg / Measurement ────────────
    # Label line 10: "MEASUREMENT 13  COMMERCIAL REG. NO. 12  CARRIER'S NAME 11"
    # Value line 11: "دﺮﻃ  7001786842  ﺔﯾﺮﻄﻘﻟا ﮫﯾﻮﺠﻟا طﻮﻄﺨﻟا"
    meas_lbl = _find_line(lines, 'MEASUREMENT', 'COMMERCIAL REG')
    meas_val = _get(lines, meas_lbl + 1)

    # Field 12: 10-digit CRN starting with 7
    crn = _search(r'\b(7\d{9})\b', meas_val)
    data["COMMERCIAL_REG_NO_12"] = clean(crn)
    if not crn:
        _field_failed("COMMERCIAL_REG_NO_12", filename, dec_no)

    all_ar = _arabic_tokens(meas_val)
    # Field 13: short word (دﺮﻃ = parcel/package, ≤ 3 chars typically)
    short = [t for t in all_ar if len(t) <= 3]
    data["MEASUREMENT_13"] = clean(short[0]) if short else None
    if not short:
        _field_failed("MEASUREMENT_13", filename, dec_no)

    # Field 11: longer Arabic words = carrier name
    long_ar = [t for t in all_ar if len(t) > 3]
    carrier_name = ' '.join(long_ar) if long_ar else None
    data["CARRIER_NAME_11"] = clean(carrier_name)
    if not carrier_name:
        _field_failed("CARRIER_NAME_11", filename, dec_no)

    # ── Fields 14-16: Flight / TIN / Packages ────────────────────────────────
    # Label line 12: "NO.OF PACKAGES 16  TIN NO. 12A  VOYAGE/FLIGHT NO. 14"
    # Value line 13: "11  3009167245  1164"
    pkg_lbl = _find_line(lines, 'NO.OF PACKAGES', 'TIN NO')
    pkg_val = _get(lines, pkg_lbl + 1)
    pkg_nums = pkg_val.split()


    # positional: [packages, TIN, flight]
    data["PACKAGES_16"]         = clean_number(pkg_nums[0]) if len(pkg_nums) > 0 else None
    data["TIN_NO_12A"]          = pkg_nums[1]               if len(pkg_nums) > 1 else None
    data["VOYAGE_FLIGHT_NO_14"] = pkg_nums[2]               if len(pkg_nums) > 2 else None
    for f in ["PACKAGES_16", "TIN_NO_12A", "VOYAGE_FLIGHT_NO_14"]:
        if data[f] is None:
            _field_failed(f, filename, dec_no)


    # ── Fields 15 & 17 ───────────────────────────────────────────────────────
    # Label line 14: "EXPORTED TO 15  B\L-AWB NO. / MANIF. 17"
    # Value line 15: "M 70557 B 157 - 69961172"
    awb_lbl = _find_line(lines, 'EXPORTED TO', 'AWB')
    awb_val = _get(lines, awb_lbl + 1)
    data["EXPORTED_TO_15"]    = None  # blank in this BOE
    awb_no   = _search(r'(M\s+\d+)', awb_val)
    manifest = _search(r'[-–]\s*(\d+)\s*$', awb_val)
    if not awb_no:
        _field_failed("AWB_NO_17A", filename, dec_no)
    if not manifest:
        _field_failed("MANIFEST_NO_17B", filename, dec_no)
    data["AWB_NO_17A"]      = clean(awb_no)
    data["MANIFEST_NO_17B"] = clean(manifest)

    # ── Field 18: PORT_OF_LOADING ─────────────────────────────────────────────
    # Label line 16: "PORT OF LOADING 18"
    # Value line 17: "QA DOH"
    pol_lbl = _find_line(lines, 'PORT OF LOADING', '18')
    pol_val = _get(lines, pol_lbl + 1)
    data["PORT_OF_LOADING_18"] = clean(pol_val) if pol_val else None
    if not data["PORT_OF_LOADING_18"]:
        _field_failed("PORT_OF_LOADING_18", filename, dec_no)

    # ── Field 19: MARKS & NUMBERS ─────────────────────────────────────────────
    # Label line 36: "MARKS & NUMBERS 19"
    # Value line 37: "دﺮﻃ"
    marks_lbl = _find_line(lines, 'MARKS & NUMBERS', '19')
    marks_val = _get(lines, marks_lbl + 1)
    data["MARKS_NUMBERS_19"] = clean(marks_val) if marks_val else None

    # ── Field 20: PORT_OF_DISCHARGE ──────────────────────────────────────────
    # Label line 18: "PORT OF DISCHARGE 20"
    # Value line 19: Arabic port name
    pod_lbl = _find_line(lines, 'PORT OF DISCHARGE', '20')
    pod_val = _get(lines, pod_lbl + 1)
    data["PORT_OF_DISCHARGE_20"] = clean(pod_val) if pod_val else None
    if not data["PORT_OF_DISCHARGE_20"]:
        _field_failed("PORT_OF_DISCHARGE_20", filename, dec_no)

    # ── Field 21: DESTINATION ─────────────────────────────────────────────────
    # Label line 20: "DESTINATION 21"
    # Value line 21: "ﺔﯾدﻮﻌﺴﻟا"
    dest_lbl = _find_line(lines, 'DESTINATION', '21')
    dest_val = _get(lines, dest_lbl + 1)
    data["DESTINATION_21"] = clean(dest_val) if dest_val else None
    if not data["DESTINATION_21"]:
        _field_failed("DESTINATION_21", filename, dec_no)

    # ── Field 38: CLEARING_AGENT ─────────────────────────────────────────────
    # Label line 22: "CLEARING AGENT 38  Unified Customs Code 43"
    # Value line 23: Arabic company name
    agent_lbl = _find_line(lines, 'CLEARING AGENT', '38')
    agent_val = _get(lines, agent_lbl + 1)
    data["CLEARING_AGENT_38"] = clean(agent_val) if agent_val else None
    if not data["CLEARING_AGENT_38"]:
        _field_failed("CLEARING_AGENT_38", filename, dec_no)

    # ── Field 43: UNIFIED_CUSTOMS_CODE ───────────────────────────────────────
    # 12-digit number starting with 249 in the page header
    data["UNIFIED_CUSTOMS_CODE_43"] = _search(r'\b(249\d{9,})\b', text)

    # ── Field 44: GCC_AEO_CODE ────────────────────────────────────────────────
    # Label line 24: "GCC AEO Code 44"
    # Value: 7-digit number a few lines below (line 26: "3168281")
    aeo_lbl = _find_line(lines, 'GCC AEO Code', '44')
    aeo_val = None
    for offset in range(1, 6):
        candidate = _get(lines, aeo_lbl + offset)
        if re.match(r'^\d{7}$', candidate):
            aeo_val = candidate
            break
    data["GCC_AEO_CODE_44"] = clean(aeo_val)
    if not aeo_val:
        _field_failed("GCC_AEO_CODE_44", filename, dec_no)
        

    # ── Field 39: LICENCE_NO ──────────────────────────────────────────────────
    # Label line 25: "LICENCE NO. 39"
    # Value: 4-digit number a few lines below (line 28: "4182")
    lic_lbl = _find_line(lines, 'LICENCE NO', '39')
    licence_num = None
    licence_arabic = None
    for offset in range(1, 6):
        candidate = _get(lines, lic_lbl + offset)
        if re.match(r'^\d{4}$', candidate):
            licence_num = candidate
        if re.search(_AR, candidate) and not re.match(r'^\d', candidate):
            licence_arabic = candidate
        if licence_num and licence_arabic:
            break
    licence = f"{clean(licence_arabic)} {licence_num}" if licence_arabic and licence_num else licence_num
    data["LICENCE_NO_39"] = clean(licence) if licence else None
    if not licence:
        _field_failed("LICENCE_NO_39", filename, dec_no)

    # ── Fields 45-46: blank in this BOE ──────────────────────────────────────
    data["OTHER_REMARKS_45"] = None
    data["EXIT_PORT_46"]     = None

    # ── Fields 48-52: Duties & Fees ──────────────────────────────────────────
    # Each on its own line: "14.07 TOTAL DUTY ... 48"
    # Value is the FIRST token on the line (number comes before the label)
    def _fee(keyword: str, field_no: str) -> float | None:
        idx = _find_line(lines, keyword, field_no)
        if idx < 0:
            return None
        return clean_number(_search(r'^([\d.]+)', _get(lines, idx)))

    data["TOTAL_DUTY_48"]    = _fee('TOTAL DUTY',    '48')
    data["VAT_48A"]          = _fee('VAT',           '48A')
    data["EXCISE_TAX_48B"]   = _fee('EXCISE TAX',    '48B')
    data["ANTI_DUMPING_48C"] = _fee('ANTI DUMPING',  '48C')
    data["HANDLING_49"]      = _fee('HANDLING',      '49')
    data["OTHER_CHARGES_50"] = _fee('OTHER CHARGES', '50')

    for f in ["TOTAL_DUTY_48","VAT_48A","EXCISE_TAX_48B",
              "ANTI_DUMPING_48C","HANDLING_49","OTHER_CHARGES_50"]:
        if data[f] is None:
            _field_failed(f, filename, dec_no)

    # Field 51: "DEFINITE 49.38 ... 51" — value follows DEFINITE keyword
    def_idx = _find_line(lines, 'DEFINITE', '51')
    data["DEFINITE_51"] = clean_number(
        _search(r'DEFINITE\s+([\d.]+)', _get(lines, def_idx))
    ) if def_idx >= 0 else None

    # Field 52: "INSURED 0.00 ... 52"
    ins_idx = _find_line(lines, 'INSURED', '52')
    data["INSURED_52"] = clean_number(
        _search(r'INSURED\s+([\d.]+)', _get(lines, ins_idx))
    ) if ins_idx >= 0 else None

    # ── Field 53: PAYMENT_METHOD ──────────────────────────────────────────────
    # Line 83: "PAYMENT METHOD ﻲﻜﻨﺑ ﻞﯿﺼﺤﺗ ﻊﻓﺪﻟا ﺔﻘﯾﺮﻃ 53"
    # Arabic is Presentation Forms-B — use _arabic_str
    pay_idx = _find_line(lines, 'PAYMENT METHOD', '53')
    pay_line = _get(lines, pay_idx)
    # Remove everything from "طریقة الدفع" onward (it's the Arabic label, not the value)
    # Both reversed (ﺔﻘﯾﺮﻃ ﻊﻓﺪﻟا) and normal (طریقة الدفع) forms
    pay_line = re.split(r'ﺔﻘﯾﺮﻃ|طریقة', pay_line)[0]
    # Also remove "PAYMENT METHOD" English label and field number
    pay_line = re.sub(r'PAYMENT\s+METHOD|53', '', pay_line)
    pay_arabic = _arabic_str(pay_line)
    data["PAYMENT_METHOD_53"] = clean(pay_arabic) if pay_arabic else None

    # ── Fields 54-55: blank in this BOE ──────────────────────────────────────
    data["PAYMENT_NO_54"]   = None
    data["PAYMENT_DATE_55"] = None

    # ── Field 56: PAYMENT_BANK ───────────────────────────────────────────────
    # Line 86: "BANK يدﻮﻌﺴﻟا ﻰﻠھﻻا ﻚﻨﺒﻟا ﻚﻨﺑ 56"
    bank_idx = _find_line(lines, 'BANK', '56')
    bank_line = _get(lines, bank_idx)
    bank_arabic = _arabic_str(bank_line)
    # Remove standalone ﻚﻨﺑ / بنك (the Arabic word for "bank" — it's the label not the value)
    bank_arabic = re.sub(r'\bﻚﻨﺑ\b|\bبنك\b', '', bank_arabic).strip()
    data["PAYMENT_BANK_56"] = clean(bank_arabic) if bank_arabic else None
    if not data["PAYMENT_BANK_56"]:
        _field_failed("PAYMENT_BANK_56", filename, dec_no)

    # ── Field 57: RECEIPT_NO ──────────────────────────────────────────────────
    # Line 87: "RECEIPT NO. 1171294 ... 57"
    rcpt_idx = _find_line(lines, 'RECEIPT NO', '57')
    rcpt_line = _get(lines, rcpt_idx)
    data["RECEIPT_NO_57"] = _search(r'RECEIPT NO\.\s+(\d+)', rcpt_line)
    if not data["RECEIPT_NO_57"]:
        _field_failed("RECEIPT_NO_57", filename, dec_no)

    # ── Field 58: RECEIPT_DATE ────────────────────────────────────────────────
    # Line 88: "DATE 04-11-1447 ... 58"
    rdate_idx = _find_line(lines, 'DATE', '58')
    rdate_line = _get(lines, rdate_idx)
    data["RECEIPT_DATE_58"] = _search(r'DATE\s+(\d{2}-\d{2}-\d{4})', rdate_line)
    if not data["RECEIPT_DATE_58"]:
        _field_failed("RECEIPT_DATE_58", filename, dec_no)

    # ── Field 59: RECEIPT_BANK ────────────────────────────────────────────────
    # Line 89: "BANK ءﺎﺤﻄﺒﻟا عﺮﻓ ﻚﻨﺑ 59"
    rbank_idx = _find_line(lines, 'BANK', '59')
    rbank_line = _get(lines, rbank_idx)
    rbank_arabic = _arabic_str(rbank_line)
    data["RECEIPT_BANK_59"] = clean(rbank_arabic) if rbank_arabic else None
    if not data["RECEIPT_BANK_59"]:
        _field_failed("RECEIPT_BANK_59", filename, dec_no)

    data["PDF_FILENAME"] = filename
    return data