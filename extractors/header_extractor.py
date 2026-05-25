"""
header_extractor.py
Parses BOE header fields from raw PDF text.
All field numbers match the official BOE field numbering.
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number

logger = get_logger("header_extractor")

# ── Regex helpers ─────────────────────────────────────────────────────────────

def _search(pattern: str, text: str, flags=re.MULTILINE) -> str | None:
    m = re.search(pattern, text, flags)
    if m:
        return m.group(1).strip() or None
    return None


def _field_failed(field_name: str, filename: str, dec_no: str) -> None:
    logger.warning(
        f"FIELD_FAIL | file='{filename}' | dec_no='{dec_no}' | field='{field_name}'"
    )


# ── Main extractor ────────────────────────────────────────────────────────────

def extract_header(pages: list[str], filename: str) -> dict:
    """
    Parse header fields from all page text combined.
    Returns a dict keyed by column names matching the DB schema.
    Raises ValueError if critical fields (DEC_NO, DEC_DATE) cannot be found.
    """
    text = "\n".join(pages)
    dec_no = None
    data = {}

    # ── Field 1: DEC_NO ───────────────────────────────────────────────────────
    dec_no = _search(r'(?:Dec No|رقم البیان)[^\d]*(\d{6,})', text)
    if not dec_no:
        # fallback: first standalone 7-digit number
        dec_no = _search(r'\b(\d{7,})\b', text)
    if not dec_no:
        raise ValueError(f"[{filename}] Could not extract DEC_NO")
    data["DEC_NO"] = dec_no

    # ── Field 2: DEC_DATE (stored as-is: Hijri / Gregorian) ──────────────────
    date_val = _search(
        r'(\d{4}-\d{2}-\d{2}\s*/\s*\d{2}-\d{2}-\d{4})', text
    )
    if not date_val:
        _field_failed("DEC_DATE_2", filename, dec_no)
    data["DEC_DATE_2"] = clean(date_val)

    # ── Field 3: DEC_TYPE ─────────────────────────────────────────────────────
    dec_type = _search(r'(?:Type Dec|نوع البیان)\s*\n([^\n]+)', text)
    if not dec_type:
        dec_type = _search(r'(بیان\s+\S+)', text)
    if not dec_type:
        _field_failed("DEC_TYPE_3", filename, dec_no)
    data["DEC_TYPE_3"] = clean(dec_type)

    # ── Field 4: PORT_TYPE ────────────────────────────────────────────────────
    port_type = _search(r'(?:Type Port|نوع المنفذ)\s*\n([^\n]+)', text)
    if not port_type:
        port_type = _search(r'\b(جوي|بري|بحري)\b', text)
    if not port_type:
        _field_failed("PORT_TYPE_4", filename, dec_no)
    data["PORT_TYPE_4"] = clean(port_type)

    # ── Field 5: DELIVERY_ORDER_NO ───────────────────────────────────────────
    delivery = _search(r'(?:DELIVERY ORDER NO|رقم إذن التسلیم)[^\d]*(\d+)', text)
    if not delivery:
        _field_failed("DELIVERY_ORDER_NO_5", filename, dec_no)
    data["DELIVERY_ORDER_NO_5"] = clean(delivery)

    # ── Field 6: IMPORTER_EXPORTER ───────────────────────────────────────────
    importer = _search(
        r'(?:IMPORTER\s*/\s*EXPORTER|المستورد\s*/\s*المصدر)\s*\n([^\n]+)', text
    )
    if not importer:
        _field_failed("IMPORTER_EXPORTER_6", filename, dec_no)
    data["IMPORTER_EXPORTER_6"] = clean(importer)

    # ── Field 7: NET_WEIGHT_UNLOAD_DATE ──────────────────────────────────────
    net_wt = _search(
        r'(?:NET WEIGHT|الوزن الصافى)[^\d]*(\d[\d\-/\s.]+)', text
    )
    if not net_wt:
        _field_failed("NET_WEIGHT_UNLOAD_DATE_7", filename, dec_no)
    data["NET_WEIGHT_UNLOAD_DATE_7"] = clean(net_wt)

    # ── Field 8: CARRIER_CAPTAIN_DRIVER ──────────────────────────────────────
    carrier_drv = _search(
        r"(?:CARRIER'S/CAPTAIN/DRIVER|السائق/القبطان/الناقلة)\s*\n([^\n]+)", text
    )
    if not carrier_drv:
        _field_failed("CARRIER_CAPTAIN_DRIVER_8", filename, dec_no)
    data["CARRIER_CAPTAIN_DRIVER_8"] = clean(carrier_drv)

    # ── Field 9: INTERCESSOR_CO ───────────────────────────────────────────────
    intercessor = _search(
        r'(?:INTERCESSOR CO\.|الشركة الوسیطة)\s*\n([^\n]+)', text
    )
    if not intercessor:
        _field_failed("INTERCESSOR_CO_9", filename, dec_no)
    data["INTERCESSOR_CO_9"] = clean(intercessor)

    # ── Field 10: GROSS_WEIGHT ────────────────────────────────────────────────
    gross_wt = _search(r'(?:GROSS WEIGHT|الوزن القائم)\s*\n\s*([\d.]+)', text)
    if not gross_wt:
        _field_failed("GROSS_WEIGHT_10", filename, dec_no)
    data["GROSS_WEIGHT_10"] = clean_number(gross_wt)

    # ── Field 11: CARRIER_NAME ────────────────────────────────────────────────
    carrier_name = _search(
        r"(?:CARRIER'S NAME|اسم الناقلة)\s*\n([^\n]+)", text
    )
    if not carrier_name:
        _field_failed("CARRIER_NAME_11", filename, dec_no)
    data["CARRIER_NAME_11"] = clean(carrier_name)

    # ── Field 12: COMMERCIAL_REG_NO ──────────────────────────────────────────
    crn = _search(r'(?:COMMERCIAL REG\. NO\.|رقم السجل التجاري)\s*\n(\d+)', text)
    if not crn:
        _field_failed("COMMERCIAL_REG_NO_12", filename, dec_no)
    data["COMMERCIAL_REG_NO_12"] = clean(crn)

    # ── Field 12A: TIN_NO ─────────────────────────────────────────────────────
    tin = _search(r'(?:TIN NO\.|الرقم الضریبى)\s*\n(\d+)', text)
    if not tin:
        _field_failed("TIN_NO_12A", filename, dec_no)
    data["TIN_NO_12A"] = clean(tin)

    # ── Field 13: MEASUREMENT ─────────────────────────────────────────────────
    measurement = _search(r'(?:MEASUREMENT|القیاس)\s*\n([^\n]+)', text)
    if not measurement:
        _field_failed("MEASUREMENT_13", filename, dec_no)
    data["MEASUREMENT_13"] = clean(measurement)

    # ── Field 14: VOYAGE_FLIGHT_NO ───────────────────────────────────────────
    flight = _search(r'(?:VOYAGE / FLIGHT NO\.|رقم الرحلة)\s*\n(\S+)', text)
    if not flight:
        _field_failed("VOYAGE_FLIGHT_NO_14", filename, dec_no)
    data["VOYAGE_FLIGHT_NO_14"] = clean(flight)

    # ── Field 15: EXPORTED_TO ─────────────────────────────────────────────────
    exported_to = _search(r'(?:EXPORTED TO|المصدر إلیھ)\s*\n([^\n]+)', text)
    if not exported_to:
        _field_failed("EXPORTED_TO_15", filename, dec_no)
    data["EXPORTED_TO_15"] = clean(exported_to)

    # ── Field 16: NO_OF_PACKAGES ──────────────────────────────────────────────
    packages = _search(r'(?:NO\.OF PACKAGES|عدد الطرود)\s*\n(\d+)', text)
    if not packages:
        _field_failed("PACKAGES_16", filename, dec_no)
    data["PACKAGES_16"] = clean_number(packages)

    # ── Field 17: BL_AWB_MANIFEST ─────────────────────────────────────────────
    awb = _search(
        r'(?:B\\L-AWB NO\.|رقم البولیصة/المنافست)\s*\n([^\n]+)', text
    )
    if not awb:
        awb = _search(r'(M\s+\d+\s+B\s+\d+\s*[-–]\s*\d+)', text)
    if not awb:
        _field_failed("BL_AWB_MANIFEST_17", filename, dec_no)
    data["BL_AWB_MANIFEST_17"] = clean(awb)

    # ── Field 18: PORT_OF_LOADING ─────────────────────────────────────────────
    pol = _search(r'(?:PORT OF LOADING|میناء الشحن)\s*\n([^\n]+)', text)
    if not pol:
        _field_failed("PORT_OF_LOADING_18", filename, dec_no)
    data["PORT_OF_LOADING_18"] = clean(pol)

    # ── Field 19: MARKS_NUMBERS ───────────────────────────────────────────────
    marks = _search(r'(?:MARKS & NUMBERS|العلامات و الأرقام)\s*\n([^\n]+)', text)
    if not marks:
        _field_failed("MARKS_NUMBERS_19", filename, dec_no)
    data["MARKS_NUMBERS_19"] = clean(marks)

    # ── Field 20: PORT_OF_DISCHARGE ───────────────────────────────────────────
    pod = _search(r'(?:PORT OF DISCHARGE|میناء التفریغ)\s*\n([^\n]+)', text)
    if not pod:
        _field_failed("PORT_OF_DISCHARGE_20", filename, dec_no)
    data["PORT_OF_DISCHARGE_20"] = clean(pod)

    # ── Field 21: DESTINATION ─────────────────────────────────────────────────
    dest = _search(r'(?:DESTINATION|جھة المقصد)\s*\n([^\n]+)', text)
    if not dest:
        _field_failed("DESTINATION_21", filename, dec_no)
    data["DESTINATION_21"] = clean(dest)

    # ── Field 38: CLEARING_AGENT ──────────────────────────────────────────────
    agent = _search(r'(?:CLEARING AGENT|المخلص الجمركى)\s*\n([^\n]+)', text)
    if not agent:
        _field_failed("CLEARING_AGENT_38", filename, dec_no)
    data["CLEARING_AGENT_38"] = clean(agent)

    # ── Field 39: LICENCE_NO ──────────────────────────────────────────────────
    licence = _search(r'(?:LICENCE NO\.|رقم الرخصة)\s*\n([^\n]+)', text)
    if not licence:
        _field_failed("LICENCE_NO_39", filename, dec_no)
    data["LICENCE_NO_39"] = clean(licence)

    # ── Field 43: UNIFIED_CUSTOMS_CODE ───────────────────────────────────────
    ucc = _search(r'(?:Unified Customs Code|الرقم المرجعي الموحد)[^\d]*(\d+)', text)
    if not ucc:
        _field_failed("UNIFIED_CUSTOMS_CODE_43", filename, dec_no)
    data["UNIFIED_CUSTOMS_CODE_43"] = clean(ucc)

    # ── Field 44: GCC_AEO_CODE ────────────────────────────────────────────────
    aeo = _search(r'(?:GCC AEO Code|رمز المشغل الاقتصادى)[^\d]*(\d+)', text)
    if not aeo:
        _field_failed("GCC_AEO_CODE_44", filename, dec_no)
    data["GCC_AEO_CODE_44"] = clean(aeo)

    # ── Field 45: OTHER_REMARKS ───────────────────────────────────────────────
    remarks = _search(r'(?:Other Remarks|ملاحظات أخرى)\s*\n([^\n]+)', text)
    if not remarks:
        _field_failed("OTHER_REMARKS_45", filename, dec_no)
    data["OTHER_REMARKS_45"] = clean(remarks)

    # ── Field 46: EXIT_PORT ───────────────────────────────────────────────────
    exit_port = _search(r'(?:EXIT PORT|جمرك الخروج)\s*\n([^\n]+)', text)
    if not exit_port:
        _field_failed("EXIT_PORT_46", filename, dec_no)
    data["EXIT_PORT_46"] = clean(exit_port)

    # ── Fields 48-52: Duty & Fee Summary ──────────────────────────────────────
    data["TOTAL_DUTY_48"]    = _extract_fee(text, r'(?:TOTAL DUTY|الرسوم الجمركیة)\s*([\d.]+)', "TOTAL_DUTY_48", filename, dec_no)
    data["VAT_48A"]          = _extract_fee(text, r'(?:VAT|ضریبة القیمة المضافة)\s*([\d.]+)', "VAT_48A", filename, dec_no)
    data["EXCISE_TAX_48B"]   = _extract_fee(text, r'(?:EXCISE TAX|ضریبة انتقائیة)\s*([\d.]+)', "EXCISE_TAX_48B", filename, dec_no)
    data["ANTI_DUMPING_48C"] = _extract_fee(text, r'(?:ANTI DUMPING|رسم ممارسات ضارة)\s*([\d.]+)', "ANTI_DUMPING_48C", filename, dec_no)
    data["HANDLING_49"]      = _extract_fee(text, r'(?:HANDLING|رسوم المناولة)\s*([\d.]+)', "HANDLING_49", filename, dec_no)
    data["OTHER_CHARGES_50"] = _extract_fee(text, r'(?:OTHER CHARGES|رسوم أخرى)\s*([\d.]+)', "OTHER_CHARGES_50", filename, dec_no)
    data["DEFINITE_51"]      = _extract_fee(text, r'(?:DEFINITE|قطعى)\s*([\d.]+)', "DEFINITE_51", filename, dec_no)
    data["INSURED_52"]       = _extract_fee(text, r'(?:INSURED|تأمین)\s*([\d.]+)', "INSURED_52", filename, dec_no)

    # ── Field 53: PAYMENT_METHOD ──────────────────────────────────────────────
    pay_method = _search(r'(?:PAYMENT METHOD|طریقة الدفع)\s*([^\n\d]+)', text)
    if not pay_method:
        _field_failed("PAYMENT_METHOD_53", filename, dec_no)
    data["PAYMENT_METHOD_53"] = clean(pay_method)

    # ── Field 54: PAYMENT_NO ──────────────────────────────────────────────────
    pay_no = _search(r'(?:NO\.\s*54|رقم\s*54)[^\d]*(\d+)', text)
    if not pay_no:
        _field_failed("PAYMENT_NO_54", filename, dec_no)
    data["PAYMENT_NO_54"] = clean(pay_no)

    # ── Field 55: PAYMENT_DATE ────────────────────────────────────────────────
    pay_date = _search(r'(?:DATE\s*55|تاریخ\s*55)[^\d]*(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})', text)
    if not pay_date:
        _field_failed("PAYMENT_DATE_55", filename, dec_no)
    data["PAYMENT_DATE_55"] = clean(pay_date)

    # ── Field 56: PAYMENT_BANK ───────────────────────────────────────────────
    pay_bank = _search(r'(?:BANK\s*56|بنك\s*56)\s*([^\n]+)', text)
    if not pay_bank:
        _field_failed("PAYMENT_BANK_56", filename, dec_no)
    data["PAYMENT_BANK_56"] = clean(pay_bank)

    # ── Field 57: RECEIPT_NO ──────────────────────────────────────────────────
    receipt_no = _search(r'(?:RECEIPT NO\.|رقم ایصال الدفع)\s*(\d+)', text)
    if not receipt_no:
        _field_failed("RECEIPT_NO_57", filename, dec_no)
    data["RECEIPT_NO_57"] = clean(receipt_no)

    # ── Field 58: RECEIPT_DATE ────────────────────────────────────────────────
    receipt_date = _search(
        r'(?:DATE\s*58|تاریخ\s*58)[^\d]*(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})', text
    )
    if not receipt_date:
        # fallback: Hijri date near receipt section
        receipt_date = _search(r'(\d{2}-\d{2}-\d{4})\s*(?:DATE|تاریخ)', text)
    if not receipt_date:
        _field_failed("RECEIPT_DATE_58", filename, dec_no)
    data["RECEIPT_DATE_58"] = clean(receipt_date)

    # ── Field 59: RECEIPT_BANK ───────────────────────────────────────────────
    receipt_bank = _search(r'(?:BANK\s*59|بنك\s*59)\s*([^\n]+)', text)
    if not receipt_bank:
        _field_failed("RECEIPT_BANK_59", filename, dec_no)
    data["RECEIPT_BANK_59"] = clean(receipt_bank)

    # ── PDF Filename (primary key component) ──────────────────────────────────
    data["PDF_FILENAME"] = filename

    return data


def _extract_fee(text: str, pattern: str, field: str, filename: str, dec_no: str) -> float | None:
    val = _search(pattern, text)
    if val is None:
        _field_failed(field, filename, dec_no)
    return clean_number(val)
