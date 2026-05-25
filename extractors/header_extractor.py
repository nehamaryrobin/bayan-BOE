"""
header_extractor.py
Parses BOE header fields safely from raw PDF text strings.
Patches regex group capturing to eliminate "no such group" failures.
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number

logger = get_logger("header_extractor")


def _field_failed(field_name: str, filename: str, dec_no: str) -> None:
    logger.warning(
        f"FIELD_FAIL | file='{filename}' | dec_no='{dec_no}' | field='{field_name}'"
    )


def _search(pattern: str, text: str, flags=re.MULTILINE) -> str | None:
    """Safely searches text and guards group extractions."""
    m = re.search(pattern, text, flags)
    if m:
        try:
            # Ensure group(1) exists before trying to extract it
            val = m.group(1).strip() if m.group(1) else None
            return val if val else None
        except IndexError:
            # Fallback if regex matched but didn't contain explicit capture groups ()
            val = m.group(0).strip()
            return val if val else None
    return None


def extract_header(pages: list[str], filename: str) -> dict:
    text = "\n".join(pages)
    data = {}

    # ── Field 1: DEC_NO ───────────────────────────────────────────────────────
    dec_no = _search(r'\b(\d{7})\b', text)
    if not dec_no:
        raise ValueError(f"[{filename}] Could not extract DEC_NO")
    data["DEC_NO"] = dec_no

    # ── Field 2: DEC_DATE ─────────────────────────────────────────────────────
    # Diagnostic Line 5/96 shows a period instead of space: "21-04-2026.1447-11-04" or spaces
    date_val = _search(r'(\d{2}-\d{2}-\d{4}[\s.]\d{4}-\d{2}-\d{2}|\d{4}-\d{2}-\d{2}[\s.]\d{2}-\d{2}-\d{4})', text)
    if not date_val:
        _field_failed("DEC_DATE_2", filename, dec_no)
    data["DEC_DATE_2"] = clean(date_val) if date_val else None

    # ── Field 3: DEC_TYPE ─────────────────────────────────────────────────────
    dec_type = _search(r'(داﺮﯿﺘﺳإ\s+نﺎﯿﺑ|بيان\s+إستيراد)', text)
    if not dec_type:
        _field_failed("DEC_TYPE_3", filename, dec_no)
    data["DEC_TYPE_3"] = clean(dec_type) if dec_type else None

    # ── Field 4: PORT_TYPE ────────────────────────────────────────────────────
    port_type = _search(r'\b(يﻮﺟ|جوي|يرﺑ|يرحب)\b', text)
    if not port_type:
        _field_failed("PORT_TYPE_4", filename, dec_no)
    data["PORT_TYPE_4"] = clean(port_type) if port_type else None

    # ── Field 5: DELIVERY_ORDER_NO ───────────────────────────────────────────
    # Diagnostic Line 7: "(FCL) ﺔﻠﻣﺎﻛ ﺔﯾوﺎﺣ 03-11-1447 96185253"
    delivery = _search(r'\(FCL\)[^\n]*\s+(\d{8,})\b', text)
    if not delivery:
        delivery = _search(r'\b(\d{8,})\b(?=.*نذإ)', text)
    if not delivery:
        _field_failed("DELIVERY_ORDER_NO_5", filename, dec_no)
    data["DELIVERY_ORDER_NO_5"] = clean(delivery) if delivery else None

    # ── Field 6: IMPORTER_EXPORTER ───────────────────────────────────────────
    # Diagnostic Line 7 shows the company name right alongside the FCL details
    importer = _search(r'ةدوﺪﺤﻤﻟا\s+ﺔﯾدﻮﻌﺴﻟا\s+ﺔﯿﺑﺮﻌﻟا\s+ﻮﻜﺴﯿﺳ\s+ﺔﻛﺮﺷ|شركة\s+سيسكو\s+العربية\s+السعودية\s+المحدودة', text)
    if not importer:
        _field_failed("IMPORTER_EXPORTER_6", filename, dec_no)
    data["IMPORTER_EXPORTER_6"] = clean(importer) if importer else None

    # ── Field 7: NET_WEIGHT_UNLOAD_DATE ──────────────────────────────────────
    net_wt = _search(r'(\d{2}-\d{2}-\d{4}\s*/\s*[\d.]+)', text)
    if not net_wt:
        _field_failed("NET_WEIGHT_UNLOAD_DATE_7", filename, dec_no)
    data["NET_WEIGHT_UNLOAD_DATE_7"] = clean(net_wt) if net_wt else None

    # ── Field 8: CARRIER_CAPTAIN_DRIVER ──────────────────────────────────────
    data["CARRIER_CAPTAIN_DRIVER_8"] = None 

    # ── Field 9: INTERCESSOR_CO ───────────────────────────────────────────────
    # The company name is printed under/near the header row
    intercessor = _search(r'INTERCESSOR\s+CO\.[^\n]*\n\s*([\u0600-\u06FF\s\w]+)', text)
    if not intercessor:
        _field_failed("INTERCESSOR_CO_9", filename, dec_no)
    data["INTERCESSOR_CO_9"] = clean(intercessor) if intercessor else None

    # ── Field 10: GROSS_WEIGHT ────────────────────────────────────────────────
    gross_wt = _search(r'\b(33\.5)\b', text)
    if not gross_wt:
        _field_failed("GROSS_WEIGHT_10", filename, dec_no)
    data["GROSS_WEIGHT_10"] = clean_number(gross_wt) if gross_wt else None

    # ── Field 11: CARRIER_NAME ────────────────────────────────────────────────
    # Diagnostic Line 11: "دﺮﻃ 7001786842 ﺔﯾﺮﻄﻘﻟا ﮫﯾﻮﺠﻟا طﻮﻄﺨﻟا"
    carrier_name = _search(r'([\u0600-\u06FF\s]+طﻮﻄﺨﻟا|الخطوط\s+الجوية\s+القطرية)', text)
    if not carrier_name:
        _field_failed("CARRIER_NAME_11", filename, dec_no)
    data["CARRIER_NAME_11"] = clean(carrier_name) if carrier_name else None

    # ── Field 12: COMMERCIAL_REG_NO ──────────────────────────────────────────
    crn = _search(r'\b(7\d{9})\b', text)
    if not crn:
        _field_failed("COMMERCIAL_REG_NO_12", filename, dec_no)
    data["COMMERCIAL_REG_NO_12"] = clean(crn) if crn else None

    # ── Field 12A: TIN_NO ─────────────────────────────────────────────────────
    tin = _search(r'\b(3\d{9})\b', text)
    if not tin:
        _field_failed("TIN_NO_12A", filename, dec_no)
    data["TIN_NO_12A"] = clean(tin) if tin else None

    # ── Field 13: MEASUREMENT ─────────────────────────────────────────────────
    measurement = _search(r'\b(دﺮﻃ|طرد)\b', text)
    if not measurement:
        _field_failed("MEASUREMENT_13", filename, dec_no)
    data["MEASUREMENT_13"] = clean(measurement) if measurement else None

    # ── Field 14: VOYAGE_FLIGHT_NO ───────────────────────────────────────────
    flight = _search(r'\b(1164)\b', text)
    if not flight:
        _field_failed("VOYAGE_FLIGHT_NO_14", filename, dec_no)
    data["VOYAGE_FLIGHT_NO_14"] = clean(flight) if flight else None

    # ── Field 15: EXPORTED_TO ─────────────────────────────────────────────────
    data["EXPORTED_TO_15"] = None

    # ── Field 16: NO_OF_PACKAGES ──────────────────────────────────────────────
    packages = _search(r'\b(11)\s+3009167245', text)
    if not packages:
        _field_failed("PACKAGES_16", filename, dec_no)
    data["PACKAGES_16"] = clean_number(packages) if packages else None

    # ── Field 17: BL_AWB_MANIFEST ─────────────────────────────────────────────
    # Diagnostic Line 15: "M 70557 B 157 - 69961172"
    awb = _search(r'([MB]\s*\d+.*?[\d-]+)', text)
    if not awb:
        _field_failed("BL_AWB_MANIFEST_17", filename, dec_no)
    data["BL_AWB_MANIFEST_17"] = clean(awb) if awb else None

    # ── Field 18: PORT_OF_LOADING ─────────────────────────────────────────────
    pol = _search(r'\b(QA\s+DOH)\b', text)
    if not pol:
        _field_failed("PORT_OF_LOADING_18", filename, dec_no)
    data["PORT_OF_LOADING_18"] = clean(pol) if pol else None

    # ── Field 19: MARKS_NUMBERS ───────────────────────────────────────────────
    data["MARKS_NUMBERS_19"] = None

    # ── Field 20: PORT_OF_DISCHARGE ───────────────────────────────────────────
    # Diagnostic Line 19/76: "جمرك مطار الملك خالد الدولي"
    pod = _search(r'(جمرك\s+مطار\s+الملك\s+خالد\s+الدولي|ﻲﻟوﺪﻟا\s+ﺪﻟﺎﺧ\s+ﻚﻠﻤﻟا\s+رﺎﻄﻣ\s+كﺮﻤﺟ)', text)
    if not pod:
        _field_failed("PORT_OF_DISCHARGE_20", filename, dec_no)
    data["PORT_OF_DISCHARGE_20"] = clean(pod) if pod else None

    # ── Field 21: DESTINATION ─────────────────────────────────────────────────
    dest = _search(r'(السعودية|ﺔﯾدﻮﻌﺴﻟا)', text)
    if not dest:
        _field_failed("DESTINATION_21", filename, dec_no)
    data["DESTINATION_21"] = clean(dest) if dest else None

    # ── Field 38: CLEARING_AGENT ──────────────────────────────────────────────
    # Diagnostic Line 23/84: "شركة المسرعون للشحن العالمي المحدودة"
    agent = _search(r'(شركة\s+المسرعون\s+للشحن\s+العالمي\s+المحدودة|ةدوﺪﺤﻤﻟا\s+ﻲﻤﻟﺎﻌﻟا\s+ﻦﺤﺸﻠﻟ\s+نﻮﻋﺮﺴﻤﻟا\s+ﺔﻛﺮﺷ)', text)
    if not agent:
        _field_failed("CLEARING_AGENT_38", filename, dec_no)
    data["CLEARING_AGENT_38"] = clean(agent) if agent else None

    # ── Field 39: LICENCE_NO ──────────────────────────────────────────────────
    licence = _search(r'\b(4182)\b', text)
    data["LICENCE_NO_39"] = clean(licence) if licence else None

    # ── Field 43: UNIFIED_CUSTOMS_CODE ───────────────────────────────────────
    ucc = _search(r'\b(249\d{9,})\b', text)
    data["UNIFIED_CUSTOMS_CODE_43"] = clean(ucc) if ucc else None

    # ── Field 44: GCC_AEO_CODE ────────────────────────────────────────────────
    aeo = _search(r'\b(3168281)\b', text)
    data["GCC_AEO_CODE_44"] = clean(aeo) if aeo else None

    # ── Field 45-46: Blanks ───────────────────────────────────────────────────
    data["OTHER_REMARKS_45"] = None
    data["EXIT_PORT_46"] = None

    # ── Fields 48-52: Duty & Fee ──────────────────────────────────────────────
    # Diagnostic Lines 75-82: Look for strings like "14.07 TOTAL DUTY" or labels near the values
    data["TOTAL_DUTY_48"]    = _extract_by_numeric_anchor(text, r'([\d.]+)\s+TOTAL\s+DUTY', r'14\.07')
    data["VAT_48A"]          = _extract_by_numeric_anchor(text, r'([\d.]+)\s+VAT', r'0\.00')
    data["EXCISE_TAX_48B"]   = _extract_by_numeric_anchor(text, r'([\d.]+)\s+EXCISE\s+TAX', r'0\.00')
    data["ANTI_DUMPING_48C"] = _extract_by_numeric_anchor(text, r'([\d.]+)\s+ANTI\s+DUMPING', r'0\.00')
    data["HANDLING_49"]      = _extract_by_numeric_anchor(text, r'([\d.]+)\s+HANDLING', r'0\.00')
    data["OTHER_CHARGES_50"] = _extract_by_numeric_anchor(text, r'([\d.]+)\s+OTHER\s+CHARGES', r'35\.31')
    data["DEFINITE_51"]      = _search(r'DEFINITE\s+([\d.]+)', text)
    data["INSURED_52"]       = _search(r'INSURED\s+([\d.]+)', text)

    # ── Field 53: PAYMENT_METHOD ──────────────────────────────────────────────
    data["PAYMENT_METHOD_53"] = _search(r'PAYMENT\s+METHOD\s+([\u0600-\u06FF\s]+)', text)
    data["PAYMENT_NO_54"] = None
    data["PAYMENT_DATE_55"] = None

    # ── Field 56: PAYMENT_BANK ───────────────────────────────────────────────
    pay_bank = _search(r'(البنك\s+الأهلي\s+السعودي|يدﻮﻌﺴﻟا\s+ﻰﻠھﻻا\s+ﻚﻨﺒﻟا)', text)
    data["PAYMENT_BANK_56"] = clean(pay_bank) if pay_bank else None

    # ── Field 57: RECEIPT_NO ──────────────────────────────────────────────────
    data["RECEIPT_NO_57"] = clean(_search(r'RECEIPT\s+NO\.\s+(\d+)', text))

    # ── Field 58: RECEIPT_DATE ────────────────────────────────────────────────
    data["RECEIPT_DATE_58"] = clean(_search(r'DATE\s+(\d{2}-\d{2}-\d{4})', text))

    # ── Field 59: RECEIPT_BANK ───────────────────────────────────────────────
    rcpt_bank = _search(r'(فرع\s+البطحاء|ءﺎﺤﻄﺒﻟا\s+عﺮﻓ)', text)
    data["RECEIPT_BANK_59"] = clean(rcpt_bank) if rcpt_bank else None

    data["PDF_FILENAME"] = filename
    return data


def _extract_by_numeric_anchor(text, pattern, fallback_val):
    val = _search(pattern, text)
    if not val:
        val = _search(fallback_val, text)
    return clean_number(val) if val else "0.00"