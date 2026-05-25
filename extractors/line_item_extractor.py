"""
line_item_extractor.py

Extracts BOE line items from raw PDF text.
Strategy:
  1. Combine all page text.
  2. Locate each item block by its item number (1, 2, 3 ...) using the
     HS code pattern that always follows on the same logical row.
  3. Use the ORIGIN country code (field 24 — 2-letter ISO code like CN, TW, US)
     as a secondary anchor to validate each row and split fields.
  4. Parse remaining fields from each block.
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number

logger = get_logger("line_item_extractor")

# 10-digit HS code always present on each item row
_HS_PATTERN      = re.compile(r'\b(\d{10,12})\b')
# 2-letter ISO origin country code (field 24 anchor)
_ORIGIN_PATTERN  = re.compile(r'\b([A-Z]{2})\b')
# Numeric value (foreign/local value, duty)
_NUMBER_PATTERN  = re.compile(r'([\d,]+\.?\d*)')
# Item number at start of a line (RTL: appears as trailing digit in extracted text)
_ITEM_NO_PATTERN = re.compile(r'(?:^|\s)(\d{1,2})\s+(\d{10,12})', re.MULTILINE)


def extract_line_items(pages: list[str], filename: str, dec_no: str) -> list[dict]:
    """
    Parse all line items from page text.
    Returns a list of dicts keyed to DB column names.
    Raises ValueError if no items found at all.
    """
    text = "\n".join(pages)
    items = _parse_items(text, filename, dec_no)
    if not items:
        raise ValueError(f"[{filename}] No line items could be extracted")
    return items


def _parse_items(text: str, filename: str, dec_no: str) -> list[dict]:
    """
    Find all item blocks by locating (item_number, hs_code) pairs,
    then parse each block.
    """
    # Find all (item_no, hs_code, position) anchors
    anchors = []
    for m in _ITEM_NO_PATTERN.finditer(text):
        item_no = int(m.group(1))
        hs_code = m.group(2)
        anchors.append((item_no, hs_code, m.start()))

    if not anchors:
        logger.warning(f"[{filename}] No item anchors found via primary pattern")
        return []

    items = []
    for idx, (item_no, hs_code, start) in enumerate(anchors):
        # Slice text for this item: from current anchor to next anchor (or end)
        end = anchors[idx + 1][2] if idx + 1 < len(anchors) else len(text)
        block = text[start:end]

        row = _parse_block(block, item_no, hs_code, filename, dec_no)
        items.append(row)

    return items


def _parse_block(block: str, item_no: int, hs_code: str, filename: str, dec_no: str) -> dict:
    """Parse a single line item block into a dict."""
    row = {
        "DEC_NO":      dec_no,
        "PDF_FILENAME": filename,
        "ITEM_NO":     item_no,
    }

    # ── Field 22: HS_CODE ─────────────────────────────────────────────────────
    row["HS_CODE_22"] = hs_code

    # ── Field 24: ORIGIN (anchor — 2-letter country code) ─────────────────────
    origin = _find_origin(block)
    if not origin:
        _field_failed("ORIGIN_24", filename, dec_no, item_no)
    row["ORIGIN_24"] = origin

    # ── Field 23: GOODS_DESCRIPTION (Arabic text between HS code and ORIGIN) ──
    desc = _extract_description(block, hs_code, origin)
    if not desc:
        _field_failed("GOODS_DESCRIPTION_23", filename, dec_no, item_no)
    row["GOODS_DESCRIPTION_23"] = clean(desc)

    # ── Fields 25-31: Numeric values ──────────────────────────────────────────
    numbers = _extract_numbers(block, origin)

    row["FOREIGN_VALUE_25"]  = _safe_num(numbers, 0, "FOREIGN_VALUE_25",  filename, dec_no, item_no)
    row["CURRENCY_TYPE_26"]  = _extract_currency_type(block)
    row["CURRENCY_VALUE_27"] = _safe_num(numbers, 1, "CURRENCY_VALUE_27", filename, dec_no, item_no)
    row["CIF_LOCAL_VALUE_28"]= _safe_num(numbers, 2, "CIF_LOCAL_VALUE_28",filename, dec_no, item_no)
    row["D_RATE_29"]         = _extract_d_rate(block, filename, dec_no, item_no)
    row["INCOME_TYPE_30"]    = _extract_income_type(block, filename, dec_no, item_no)
    row["TOTAL_DUTY_31"]     = _safe_num(numbers, 3, "TOTAL_DUTY_31",     filename, dec_no, item_no)

    # ── Fields 32-37: Package / weight ────────────────────────────────────────
    pkg_numbers = _extract_pkg_numbers(block)
    row["PKG_QTY_32"]      = _safe_num(pkg_numbers, 0, "PKG_QTY_32",      filename, dec_no, item_no)
    row["PKG_TYPE_33"]     = None   # typically blank in this BOE format
    row["ITEM_QTY_34"]     = _safe_num(pkg_numbers, 1, "ITEM_QTY_34",     filename, dec_no, item_no)
    row["ITEM_UNIT_35"]    = _extract_unit(block, filename, dec_no, item_no)
    row["NET_WEIGHT_36"]   = _safe_num(pkg_numbers, 2, "NET_WEIGHT_36",   filename, dec_no, item_no)
    row["GROSS_WEIGHT_37"] = _safe_num(pkg_numbers, 3, "GROSS_WEIGHT_37", filename, dec_no, item_no)
    row["AIP_NO_37A"]      = None
    row["AIP_DUTY_37B"]    = None

    # ── Fields 40-41: Customs restrictions ────────────────────────────────────
    row["CUSTOMS_RESTRICTIONS_AGENCY_40"] = None
    row["CUSTOMS_RELEASE_REF_41"]         = None

    return row


# ── Field-level helpers ───────────────────────────────────────────────────────

def _find_origin(block: str) -> str | None:
    """
    Find the 2-letter ISO origin country code in the block.
    Must be preceded/followed by whitespace and be all-caps.
    Skips known non-origin uppercase pairs like SAR, CN is included.
    """
    # Exclude tokens that are not country codes
    _EXCLUDE = {"SAR", "CIF", "NO", "HS", "QA", "FCL", "AWB", "AIP", "DOH"}
    for m in _ORIGIN_PATTERN.finditer(block):
        candidate = m.group(1)
        if candidate not in _EXCLUDE and len(candidate) == 2:
            return candidate
    return None


def _extract_description(block: str, hs_code: str, origin: str | None) -> str | None:
    """
    Description sits between the HS code and the origin code.
    In RTL-extracted text the order may be reversed, so try both directions.
    """
    # Try: hs_code ... description ... origin
    if origin:
        m = re.search(
            re.escape(hs_code) + r'\s+([\s\S]+?)\s+' + re.escape(origin),
            block
        )
        if m:
            return m.group(1).strip()
    # Fallback: take any Arabic text in the block
    arabic = re.findall(r'[\u0600-\u06FF][^\n\d]{5,}', block)
    if arabic:
        return " ".join(arabic).strip()
    return None


def _extract_numbers(block: str, origin: str | None) -> list[float]:
    """
    Extract the sequence of numeric values that follow the ORIGIN code.
    Expected order: FOREIGN_VALUE, CURRENCY_RATE, CIF_LOCAL_VALUE, TOTAL_DUTY
    """
    # Find position of origin code and grab numbers after it
    start = 0
    if origin:
        m = re.search(r'\b' + re.escape(origin) + r'\b', block)
        if m:
            start = m.end()

    numbers = []
    for m in _NUMBER_PATTERN.finditer(block[start:]):
        val = clean_number(m.group(1))
        if val is not None:
            numbers.append(val)
    return numbers


def _extract_pkg_numbers(block: str) -> list[float]:
    """
    Extract the package/weight numbers from the lower section of the block.
    These appear as a small group: pkg_qty, item_qty, net_weight, gross_weight.
    """
    # Look for the repeated number pattern at end of block (after duty values)
    tail = block[-300:] if len(block) > 300 else block
    numbers = []
    for m in _NUMBER_PATTERN.finditer(tail):
        val = clean_number(m.group(1))
        if val is not None and val < 10000:   # weights/qty are small numbers
            numbers.append(val)
    return numbers


def _extract_currency_type(block: str) -> str | None:
    """Extract currency code e.g. SAR, USD."""
    m = re.search(r'\b(SAR|USD|EUR|GBP|AED|QAR)\b', block)
    return m.group(1) if m else None


def _extract_d_rate(block: str, filename: str, dec_no: str, item_no: int) -> float | None:
    """Extract duty rate (e.g. 0.05 from '5 %'). Returns None if exempt."""
    m = re.search(r'(\d+)\s*%', block)
    if m:
        return float(m.group(1)) / 100
    # Exempt items have no rate — NULL is correct, not a failure
    return None


def _extract_income_type(block: str, filename: str, dec_no: str, item_no: int) -> str | None:
    """Extract income type: قطعي (definite) or معفي ت (exempt)."""
    if re.search(r'قطعي', block):
        return clean('قطعي')
    if re.search(r'معفي', block):
        return clean('معفي ت')
    _field_failed("INCOME_TYPE_30", filename, dec_no, item_no)
    return None


def _extract_unit(block: str, filename: str, dec_no: str, item_no: int) -> str | None:
    """Extract unit label e.g. وحدة."""
    m = re.search(r'(وحدة|كجم|لتر|متر)', block)
    if m:
        return clean(m.group(1))
    _field_failed("ITEM_UNIT_35", filename, dec_no, item_no)
    return None


def _safe_num(numbers: list, index: int, field: str, filename: str, dec_no: str, item_no: int) -> float | None:
    if index < len(numbers):
        return numbers[index]
    _field_failed(field, filename, dec_no, item_no)
    return None


def _field_failed(field: str, filename: str, dec_no: str, item_no: int) -> None:
    logger.warning(
        f"FIELD_FAIL | file='{filename}' | dec_no='{dec_no}' | item={item_no} | field='{field}'"
    )
