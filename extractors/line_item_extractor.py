"""
line_item_extractor.py

Uses coordinate-based word grouping (pdfplumber) for robust RTL extraction.

Each item value line ends with: HS_CODE(10-12 digits) + ITEM_NO(1-2 digits)
Package rows:  GROSS  NET  UNIT(any non-space token)  QTY  ITEM_NO

Key fixes:
  1. Arabic range covers U+0600-06FF AND U+FE70-FEFF (Presentation Forms-B)
  2. Package rows only merged into existing value-row items — never create ghost items
  3. Unit token matched with \\S+ (not Arabic-only) to handle mixed unicode
  4. Description looked up from line ABOVE value line when not found inline
"""
import re
from app.logger import get_logger
from utils.arabic_utils import clean, clean_number
from extractors.pdf_to_text import extract_words_with_coords

logger = get_logger("line_item_extractor")

_AR        = r'[\u0600-\u06FF\uFE70-\uFEFF]'
_AR_BLOCK  = re.compile(_AR)

_NOISE = {
    "ESU", "TNEGA", "S'REIRRAC", "REKORB", "RO", "RETROPMI",
    "ﻹﺳﺘﻌﻤﺎﻻت", "وﻛﯿﻞ", "اﻟﻨﺎﻗﻠﺔ", "اﻟﻤﺴﺘﻮرد",
    "او اﻟﻤﺨﻠﺺ", "اﻟﻤﺨﻠﺺ", "او", "اﻟﺠﻤﺎرك", "QR Code",
}

# Single uppercase English letters/pairs that are vertical border noise fragments
_BORDER_NOISE_RE = re.compile(r'^[A-Z]{1,3}$')

# Item value line: ends with HS_CODE + ITEM_NO
_ITEM_END_RE = re.compile(r'^(.+?)\s+(\d{10,12})\s+(\d{1,2})\s*$')

# Package row: GROSS  NET  UNIT  QTY  ITEM_NO
# Unit is any non-space token (handles mixed unicode Arabic)
_PKG_RE = re.compile(
    r'^([\d.]+)\s+([\d.]+)\s+(\S+)\s+([\d.]+)\s+(\d{1,2})\s*$'
)

# Package row without item number (item 4 edge case — border noise ate the item no)
_PKG_NO_ITEMNO_RE = re.compile(
    r'^([\d.]+)\s+([\d.]+)\s+(\S+)\s+([\d.]+)\s*$'
)

# Pure Arabic description lines (no numbers, no HS codes, no English keywords)
_DESC_ONLY_RE = re.compile(r'^[\u0600-\u06FF\uFE70-\uFEFF\s\-–]+$')

# Income type tokens to strip from description
_INCOME_NOISE_RE = re.compile(
    r'\s*(ﻲﻔﻌﻣ|معفي|ت\s*$|ﻲﻌﻄﻗ|قطعي|%|ﺍﻟﻤﺴ\S*|ﺍﻭ\S*|ﻠﺺ\S*)\s*',
    re.UNICODE
)


def _clean_row(row_str: str) -> str:
    """
    Strip leading/trailing single-letter or short uppercase border noise tokens.
    e.g. 'B 1.00 1.00 ةﺪﺣو 1.00 1' → '1.00 1.00 ةﺪﺣو 1.00 1'
         'R E 5.00 5.00 ةﺪﺣو 1.00 2' → '5.00 5.00 ةﺪﺣو 1.00 2'
    """
    tokens = row_str.split()
    # Strip leading tokens that are short uppercase English (border fragments)
    while tokens and _BORDER_NOISE_RE.match(tokens[0]):
        tokens.pop(0)
    # Strip trailing tokens that are short uppercase English
    while tokens and _BORDER_NOISE_RE.match(tokens[-1]):
        tokens.pop()
    return ' '.join(tokens)


def extract_tabular_groups(pdf_path: str, filename: str, dec_no: str) -> list[dict]:
    pages_words = extract_words_with_coords(pdf_path)

    # ── Build clean horizontal text rows per page ─────────────────────────────
    all_rows: list[tuple[str, int]] = []  # (row_text, page_no)

    for page_no, words in enumerate(pages_words, start=1):
        if not words:
            continue
        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups: list[list[dict]] = []
        current_row = [sorted_words[0]]
        for w in sorted_words[1:]:
            # Anchor to first word of row to prevent staircase merging
            if abs(w["top"] - current_row[0]["top"]) <= 6:
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row:
            row_groups.append(current_row)

        for row in row_groups:
            row_str = " ".join(
                w["text"] for w in sorted(row, key=lambda w: w["x0"])
            ).strip()
            # Strip border noise tokens from start/end of each row
            row_str = _clean_row(row_str)
            if row_str and row_str not in _NOISE:
                all_rows.append((row_str, page_no))

    # ── Pass 1: extract value rows (HS_CODE + ITEM_NO) ───────────────────────
    value_items: dict[int, dict] = {}

    for idx, (row_str, _) in enumerate(all_rows):
        m = _ITEM_END_RE.match(row_str)
        if not m:
            continue
        body    = m.group(1).strip()
        hs_code = m.group(2)
        item_no = int(m.group(3))

        # Sanity: item_no must be 1-99, hs_code must be 10+ digits
        if not (1 <= item_no <= 99 and len(hs_code) >= 10):
            continue

        row = _parse_value_body(body, hs_code, item_no, filename, dec_no)

        # Description: try inline first, then look at row ABOVE
        if not row.get("GOODS_DESCRIPTION_23"):
            for back in range(1, 4):
                prev_row, _ = all_rows[idx - back] if idx - back >= 0 else ("", 0)
                if prev_row and _DESC_ONLY_RE.match(prev_row) and len(prev_row) > 3:
                    row["GOODS_DESCRIPTION_23"] = clean(prev_row)
                    break

        value_items[item_no] = row

    if not value_items:
        raise ValueError(f"[{filename}] No line items could be extracted")

    # ── Pass 2: extract package rows and merge into existing items ONLY ───────
    # Track which item numbers we've already assigned pkg rows to
    # so we can handle the item-4 missing-item-number edge case
    pkg_assigned: set[int] = set()
    last_pkg_item_no: int = 0

    for row_str, _ in all_rows:
        # Try full match first (with item number)
        m = _PKG_RE.match(row_str)
        if m:
            gross   = clean_number(m.group(1))
            net     = clean_number(m.group(2))
            unit    = clean(m.group(3))
            qty     = clean_number(m.group(4))
            item_no = int(m.group(5))

            if item_no in value_items and item_no not in pkg_assigned:
                value_items[item_no].update({
                    "GROSS_WEIGHT_37": gross,
                    "NET_WEIGHT_36":   net,
                    "ITEM_UNIT_35":    unit,
                    "ITEM_QTY_34":     qty,
                    "PKG_QTY_32":      1.0,
                })
                pkg_assigned.add(item_no)
                last_pkg_item_no = item_no
            continue

        # Try match without item number (border noise ate it)
        m2 = _PKG_NO_ITEMNO_RE.match(row_str)
        if m2:
            # Infer item number: next sequential item after last assigned
            inferred = last_pkg_item_no + 1
            # Find the next unassigned value item
            while inferred in pkg_assigned and inferred <= 99:
                inferred += 1

            if inferred in value_items and inferred not in pkg_assigned:
                gross = clean_number(m2.group(1))
                net   = clean_number(m2.group(2))
                unit  = clean(m2.group(3))
                qty   = clean_number(m2.group(4))
                value_items[inferred].update({
                    "GROSS_WEIGHT_37": gross,
                    "NET_WEIGHT_36":   net,
                    "ITEM_UNIT_35":    unit,
                    "ITEM_QTY_34":     qty,
                    "PKG_QTY_32":      1.0,
                })
                pkg_assigned.add(inferred)
                last_pkg_item_no = inferred

    # ── Fill always-null fields and attach keys ───────────────────────────────
    items = []
    for item_no in sorted(value_items.keys()):
        row = value_items[item_no]
        row.setdefault("GROSS_WEIGHT_37", None)
        row.setdefault("NET_WEIGHT_36",   None)
        row.setdefault("ITEM_UNIT_35",    None)
        row.setdefault("ITEM_QTY_34",     None)
        row.setdefault("PKG_QTY_32",      None)
        row.update({
            "DEC_NO":                          dec_no,
            "PDF_FILENAME":                    filename,
            "PKG_TYPE_33":                     None,
            "AIP_NO_37A":                      None,
            "AIP_DUTY_37B":                    None,
            "CUSTOMS_RESTRICTIONS_AGENCY_40":  None,
            "CUSTOMS_RELEASE_REF_41":          None,
        })
        items.append(row)

    return items


def _parse_value_body(body: str, hs_code: str, item_no: int,
                      filename: str, dec_no: str) -> dict:
    row: dict = {"ITEM_NO": item_no, "HS_CODE_22": hs_code}

    # ── ORIGIN: 2-letter ISO country code ────────────────────────────────────
    _EXCLUDE = {"SAR", "USD", "EUR", "AED"}
    origin = None
    for m in re.finditer(r'\b([A-Z]{2})\b', body):
        if m.group(1) not in _EXCLUDE:
            origin = m.group(1)
            break
    row["ORIGIN_24"] = origin
    if not origin:
        _field_failed("ORIGIN_24", filename, dec_no, item_no)

    # ── GOODS DESCRIPTION: Arabic text AFTER the origin code ─────────────────
    # Everything before the origin code is financial data + noise.
    # Everything after the origin code is the description.
    if origin:
        after_origin = body[body.index(origin) + len(origin):].strip()
    else:
        after_origin = body

    arabic_parts = re.findall(r'[\u0600-\u06FF\uFE70-\uFEFF][^\d\n]{2,}', after_origin)
    if arabic_parts:
        raw_desc = ' '.join(arabic_parts)
        # Strip any stray income type tokens (ﻲﻔﻌﻣ, ت, ﻲﻌﻄﻗ) and % sign
        raw_desc = re.sub(r'\b(ﻲﻔﻌﻣ|معفي|ﻲﻌﻄﻗ|قطعي)\b', '', raw_desc)
        raw_desc = re.sub(r'\bت\b', '', raw_desc)
        raw_desc = re.sub(r'%', '', raw_desc)
        raw_desc = re.sub(r'\s{2,}', ' ', raw_desc).strip()
        desc = clean(raw_desc) if raw_desc.strip() else None
    else:
        desc = None
    row["GOODS_DESCRIPTION_23"] = desc

    # ── CURRENCY TYPE ─────────────────────────────────────────────────────────
    curr_m = re.search(r'\b(SAR|USD|EUR|AED)\b', body)
    row["CURRENCY_TYPE_26"] = curr_m.group(1) if curr_m else None

    # ── DUTY RATE: "% 5" → 0.05 ──────────────────────────────────────────────
    rate_m = re.search(r'%\s*(\d+)', body)
    row["D_RATE_29"] = float(rate_m.group(1)) / 100 if rate_m else None

    # ── INCOME TYPE ───────────────────────────────────────────────────────────
    # ﻲﻔﻌﻣ / معفي = exempt   |   ﻲﻌﻄﻗ / قطعي = definite
    if re.search(r'ﻲﻔﻌﻣ|معفي', body):
        row["INCOME_TYPE_30"] = clean('معفي ت')
    elif re.search(r'ﻲﻌﻄﻗ|قطعي', body):
        row["INCOME_TYPE_30"] = clean('قطعي')
    else:
        row["INCOME_TYPE_30"] = None
        _field_failed("INCOME_TYPE_30", filename, dec_no, item_no)

    # ── NUMERIC VALUES ────────────────────────────────────────────────────────
    # Left-to-right order in extracted text (RTL reversed from document):
    #   TOTAL_DUTY | CIF_LOCAL | 1.00(rate) | FOREIGN_VALUE
    nums = [
        clean_number(n)
        for n in re.findall(r'[\d,]+\.?\d*', body)
        if clean_number(n) is not None
    ]

    # Currency rate is always 1.00 — use as positional anchor
    rate_idx = next((i for i, n in enumerate(nums) if n == 1.0), None)

    if rate_idx is not None and rate_idx >= 1:
        row["TOTAL_DUTY_31"]      = nums[0]
        row["CIF_LOCAL_VALUE_28"] = nums[rate_idx - 1]
        row["CURRENCY_VALUE_27"]  = 1.0
        row["FOREIGN_VALUE_25"]   = nums[rate_idx + 1] if rate_idx + 1 < len(nums) else None
    else:
        row["TOTAL_DUTY_31"]      = nums[0] if len(nums) > 0 else None
        row["CIF_LOCAL_VALUE_28"] = nums[1] if len(nums) > 1 else None
        row["CURRENCY_VALUE_27"]  = None
        row["FOREIGN_VALUE_25"]   = nums[2] if len(nums) > 2 else None

    for f in ["TOTAL_DUTY_31", "CIF_LOCAL_VALUE_28", "FOREIGN_VALUE_25"]:
        if row.get(f) is None:
            _field_failed(f, filename, dec_no, item_no)

    return row


def _field_failed(field: str, filename: str, dec_no: str, item_no: int) -> None:
    logger.warning(
        f"FIELD_FAIL | file='{filename}' | dec_no='{dec_no}' | "
        f"item={item_no} | field='{field}'"
    )
