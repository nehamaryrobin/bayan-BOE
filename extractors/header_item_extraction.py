import re
from app.logger import get_logger
from extractors.pdf_to_text import extract_pages_layout, extract_pages
from utils.arabic_utils import clean, clean_number
from db.models import BoeHeader

logger = get_logger("header_extractor")

_AR = r'[\u0600-\u06FF\uFE70-\uFEFF]'

# Regex patterns kept as module constants for efficiency
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
    ^\s*
    (?P<no_of_packages>\d+)\s{3,}      # 1. MANDATORY: Number of Packages (Field 16)
    (?P<tin_no>\b\d{10,15}\b)\s{3,}    # 2. MANDATORY: TIN Number (Field 12A) - Matches either standard 10-digit or 15-digit IDs
    (?P<voyage_flight_no>\w+).         # 3. MANDATORY: Voyage / Flight Number (Field 14)
    \s*$
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


class HeaderExtractor:
    """Object-oriented parser class to isolate related BOE header fields and logic."""

    def __init__(self, pdf_path: str, filename: str):
        self.pdf_path = pdf_path
        self.filename = filename.rsplit('.', 1)[0]
        self._lines1 = []
        self._text1 = ""
        self._lines2 = []
        self._text2 = ""
        self.data = {"PDF_FILENAME": self.filename}

    def _find_line(self, lines: list[str], *keywords) -> int:
        for i, line in enumerate(lines):
            norm_line = re.sub(r'\s+', ' ', line)
            if all(k in norm_line for k in keywords):
                return i
        return -1

    def _get(self, lines: list[str], idx: int) -> str:
        return lines[idx].strip() if 0 <= idx < len(lines) else ""

    def _search(self, pattern: str, text: str, flags=re.MULTILINE) -> str | None:
        m = re.search(pattern, text, flags)
        if m:
            val = m.group(1).strip()
            return val if val else None
        return None

    def _field_failed(self, field: str) -> None:
        logger.warning(f"FIELD_FAIL | file='{self.filename}' | dec_no='{self.data.get('DEC_NO')}' | field='{field}'")

    def extract(self) -> BoeHeader:
        # Load PDF layout texts
        pages1 = extract_pages(self.pdf_path)
        self._lines1 = [l for l in pages1[0].split('\n') if l.strip()]
        self._text1  = '\n'.join(self._lines1) 

        pages2 = extract_pages_layout(self.pdf_path)
        self._lines2 = [l for l in pages2[0].split('\n') if l.strip()]
        self._text2  = '\n'.join(self._lines2) 

        # Parsing stages
        self._parse_identifiers()
        self._parse_delivery_and_importer()
        self._parse_carrier_details()
        self._parse_measurement_and_reg()
        self._parse_packages_and_flight()
        self._parse_exported_to()
        self._parse_awb_and_manifest()
        self._parse_marks_and_numbers()
        self._parse_single_value_headers()
        self._parse_duties_and_fees()
        self._parse_payment_info()

        return BoeHeader(**self.data)

    def _parse_identifiers(self):
        match = _BOE_VALUE_LINE_RE.search(self._text2)
        if not match:
            match = _BOE_EXPORT_VALUE_LINE_RE.search(self._text2)
        if not match:
            raise ValueError(f"[{self.filename}] Could not extract DEC_NO and header info")
        
        header = match.groupdict()
        self.data["DEC_NO"]               = clean(header.get("dec_no"))
        self.data["DEC_TYPE_3"]           = clean(header.get("dec_type"))
        self.data["PORT_TYPE_4"]          = clean(header.get("port_type"))

        # Parse dates flexibly
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
        
        self.data["DEC_DATE_GREGORIAN_2"] = gregorian
        self.data["DEC_DATE_HIJRI_2"]     = hijri

    def _parse_delivery_and_importer(self):
        deliv_lbl = self._find_line(self._lines2, 'DELIVERY ORDER NO', '5')
        deliv_val = self._get(self._lines2, deliv_lbl + 1)
        line_match = _DELIVERY_ORDER_LINE_RE.match(deliv_val)

        if line_match:
            res = line_match.groupdict()
            self.data["DELIVERY_ORDER_NO_5"] = clean(res.get("delivery_order"))
            self.data["IMPORTER_EXPORTER_6"] = clean(res.get("importer_name"))
            self.data["UNLOAD_DATE_7A"]       = clean(res.get("unload_date"))
            self.data["NET_WEIGHT_7B"]        = clean_number(res.get("net_weight"))
        else:
            self.data["DELIVERY_ORDER_NO_5"] = None
            self.data["IMPORTER_EXPORTER_6"] = None
            self.data["UNLOAD_DATE_7A"]       = None
            self.data["NET_WEIGHT_7B"]        = None

    def _parse_carrier_details(self):
        carrier_lbl = self._find_line(self._lines2, 'GROSS WEIGHT', 'INTERCESSOR')
        carrier_val = self._get(self._lines2, carrier_lbl + 1)
        carrier_match = _CARRIER_ROW_RE.match(carrier_val)

        if carrier_match:
            res = carrier_match.groupdict()    
            self.data["GROSS_WEIGHT_10"]          = clean_number(res.get("gross_weight"))
            self.data["INTERCESSOR_CO_9"]         = clean(res.get("intercessor"))
            self.data["CARRIER_CAPTAIN_DRIVER_8"] = clean(res.get("carrier"))
        else:
            self.data["GROSS_WEIGHT_10"]          = None
            self.data["INTERCESSOR_CO_9"]         = None
            self.data["CARRIER_CAPTAIN_DRIVER_8"] = None

    def _parse_measurement_and_reg(self):
        meas_lbl = self._find_line(self._lines1, 'MEASUREMENT', 'COMMERCIAL', 'NAME')
        meas_val = self._get(self._lines1, meas_lbl + 1)
        
        reg_match = re.search(r'\b\d{10}(?:\s*[\/\\\-]+\s*\d{10})*\b', meas_val)
        if reg_match:
            self.data["COMMERCIAL_REG_NO_12"] = reg_match.group(0).replace(" ", "")
            
            # Extract Measurement (left of the 10 digits)
            left_part = meas_val[:reg_match.start()].strip()
            cleaned_meas = clean(left_part)
            if cleaned_meas and "الناقلة" not in cleaned_meas and "اﻟﻨﺎﻗﻠﺔ" not in cleaned_meas:
                self.data["MEASUREMENT_13"] = cleaned_meas
            else:
                self.data["MEASUREMENT_13"] = None
                
            # Extract Carrier Name (right of the 10 digits)
            right_part = meas_val[reg_match.end():].strip()
            self.data["CARRIER_NAME_11"] = clean(right_part)
        else:
            self.data["MEASUREMENT_13"]       = None
            self.data["COMMERCIAL_REG_NO_12"] = None
            self.data["CARRIER_NAME_11"]      = None

    def _parse_packages_and_flight(self):
        pkg_lbl = self._find_line(self._lines1, 'NO.OF PACKAGES', 'TIN NO')
        if pkg_lbl < 0:
            pkg_lbl = self._find_line(self._lines1, 'NO.OF PACKAGES')
        pkg_val = self._get(self._lines1, pkg_lbl + 1)
        
        cols_14_16 = re.split(r'\s{3,}', pkg_val.strip())
        
        self.data["PACKAGES_16"] = clean_number(cols_14_16[0]) if len(cols_14_16) > 0 else None
        
        tin_val = clean(cols_14_16[1]) if len(cols_14_16) > 1 else None
        if tin_val and not re.match(r'^\d+$', tin_val.replace(" ", "")):
            self.data["TIN_NO_12A"] = None
        else:
            self.data["TIN_NO_12A"] = tin_val
            
        self.data["VOYAGE_FLIGHT_NO_14"] = clean(cols_14_16[2]) if len(cols_14_16) > 2 else None

    def _parse_awb_manifest_block(self, text_block: str) -> tuple[str | None, str | None, int | None]:
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

    def _parse_exported_to(self):
        idx = self._find_line(self._lines1, 'EXPORTED TO')
        if idx < 0:
            self.data["EXPORTED_TO_15"] = None
            return

        val_line = self._get(self._lines1, idx + 1)
        if not val_line:
            self.data["EXPORTED_TO_15"] = None
            return

        cols = re.split(r'\s{3,}', val_line.strip())
        if not cols:
            self.data["EXPORTED_TO_15"] = None
            return

        target_col = cols[-1]
        target_start = val_line.find(target_col)
        _, _, match_idx = self._parse_awb_manifest_block(target_col)
        
        if match_idx is not None:
            left_text = val_line[:target_start + match_idx]
            cleaned_val = clean(left_text)
            if cleaned_val and not re.search(r'\u062f\u0631\u0637', cleaned_val):
                self.data["EXPORTED_TO_15"] = cleaned_val
                return

        self.data["EXPORTED_TO_15"] = None

    def _parse_awb_and_manifest(self):
        awb_manifest_matches = _AWB_MANIFEST_LINE_RE.findall(self._text1)
        
        if awb_manifest_matches:
            awb_list, manifest_list = [], []
            for match in awb_manifest_matches:
                prefix = match[0] if match[0] else "M"
                awb_list.append(f"{prefix} {match[1]}")
                manifest_list.append(f"{match[3]} - {match[4]}")
                
            self.data["AWB_NO_17A"]      = clean(', '.join(awb_list))
            self.data["MANIFEST_NO_17B"] = clean(', '.join(manifest_list))
        else:
            awb_lbl = self._find_line(self._lines1, 'EXPORTED TO', 'MANIF', '17')
            if awb_lbl != -1:
                awb_val = self._get(self._lines1, awb_lbl + 1)
                cols = re.split(r'\s{3,}', awb_val.strip())
                if cols:
                    target_col = cols[-1] 
                    awb_val_extracted, manifest_val_extracted, _ = self._parse_awb_manifest_block(target_col)
                    self.data["AWB_NO_17A"] = awb_val_extracted
                    self.data["MANIFEST_NO_17B"] = manifest_val_extracted
            else:
                self.data["AWB_NO_17A"]      = None
                self.data["MANIFEST_NO_17B"] = None

    def _parse_marks_and_numbers(self):
        marks_idx = self._find_line(self._lines1, 'MARKS', '&', 'NUMBERS')
        if marks_idx != -1:
            marks_lines = []
            for line in self._lines1[marks_idx + 1:]:
                if 'ESU' in line or 'TNEGA' in line:
                    break
                if line.strip():
                    marks_lines.append(line.strip())
            self.data["MARKS_NUMBERS_19"] = clean(" ".join(marks_lines))
        else:
            self.data["MARKS_NUMBERS_19"] = None

    def _parse_single_value_headers(self):
        def _simple_extract(key_1, key_2):
            lbl = self._find_line(self._lines1, key_1, key_2)
            return (self._get(self._lines1, lbl + 1)) if lbl >= 0 else None

        self.data["PORT_OF_LOADING_18"]   = clean(_simple_extract('PORT OF LOADING', '18'))
        self.data["PORT_OF_DISCHARGE_20"] = clean(_simple_extract('PORT OF DISCHARGE', '20'))
        self.data["DESTINATION_21"]       = clean(_simple_extract('DESTINATION', '21'))
        self.data["CLEARING_AGENT_38"]    = clean(_simple_extract('CLEARING AGENT', '38'))
        self.data["UNIFIED_CUSTOMS_CODE_43"] = self._search(r'\b(249\d{9,}|951\d{8,})\b', self._text2)

        aeo_lbl = self._find_line(self._lines1, 'GCC AEO Code', '44')
        limit = self._find_line(self._lines1, 'Other Remarks', '45')
        if limit < 0:
            limit = len(self._lines1)

        aeo_val = next((self._get(self._lines1, aeo_lbl + i) for i in range(1, 6) if aeo_lbl + i < limit and re.match(r'^\d{7}$', self._get(self._lines1, aeo_lbl + i))), None)
        self.data["GCC_AEO_CODE_44"] = aeo_val
            
        lic_lbl = self._find_line(self._lines1, 'LICENCE NO', '39')
        licence_num = None
        licence_idx = -1
        for i in range(1, 6):
            idx = lic_lbl + i
            if idx < limit:
                val = self._get(self._lines1, idx)
                if re.match(r'^\d{4}$', val):
                    licence_num = val
                    licence_idx = idx
                    break

        licence_text = None
        if licence_idx > lic_lbl:
            above_val = self._get(self._lines1, licence_idx - 1)
            if "LICENCE NO" not in above_val and not re.match(r'^\d{7}$', above_val):
                licence_text = clean(above_val)

        if licence_text and licence_num:
            self.data["LICENCE_NO_39"] = f"{licence_text} {licence_num}"
        else:
            self.data["LICENCE_NO_39"] = licence_num

        # Other remarks (Field 45)
        rem_idx = self._find_line(self._lines2, 'Other Remarks', '45')
        if rem_idx >= 0:
            rem_val = self._get(self._lines2, rem_idx + 1)
            if 'EXIT PORT' in rem_val or '46' in rem_val:
                self.data["OTHER_REMARKS_45"] = None
            else:
                self.data["OTHER_REMARKS_45"] = clean(rem_val)
        else:
            self.data["OTHER_REMARKS_45"] = None

        # Exit Port (Field 46)
        exit_idx = self._find_line(self._lines1, 'EXIT PORT', '46')
        if exit_idx >= 0:
            exit_val = self._get(self._lines1, exit_idx + 1)
            if 'QR Code' in exit_val or '47' in exit_val or 'ﺔﻌﯾﺮﺴﻟا' in exit_val:
                self.data["EXIT_PORT_46"] = None
            else:
                self.data["EXIT_PORT_46"] = clean(exit_val)
        else:
            self.data["EXIT_PORT_46"] = None

    def _parse_duties_and_fees(self):
        def _fee(keyword: str, field_no: str) -> float | None:
            idx = self._find_line(self._lines1, keyword, field_no)
            if idx < 0:
                return None
            return clean_number(self._search(r'^([\d.]+)', self._get(self._lines1, idx)))

        self.data["TOTAL_DUTY_48"]    = _fee('TOTAL DUTY',    '48')
        self.data["VAT_48A"]          = _fee('VAT',           '48A')
        self.data["EXCISE_TAX_48B"]   = _fee('EXCISE TAX',    '48B')
        self.data["ANTI_DUMPING_48C"] = _fee('ANTI DUMPING',  '48C')
        self.data["HANDLING_49"]      = _fee('HANDLING',      '49')
        self.data["OTHER_CHARGES_50"] = _fee('OTHER CHARGES', '50')

        def_idx = self._find_line(self._lines1, 'DEFINITE', '51')
        self.data["DEFINITE_51"] = clean_number(self._search(r'DEFINITE\s+([\d.]+)', self._get(self._lines1, def_idx))) if def_idx >= 0 else None

        ins_idx = self._find_line(self._lines1, 'INSURED', '52')
        self.data["INSURED_52"] = clean_number(self._search(r'INSURED\s+([\d.]+)', self._get(self._lines1, ins_idx))) if ins_idx >= 0 else None

    def _parse_payment_info(self):
        # 1. Payment Method (Field 53)
        pm_match = re.search(r"PAYMENT\s+METHOD\s*(?P<val>.{0,50}?)\s*ﻊﻓﺪﻟا\s*ﺔﻘﯾﺮﻃ", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["PAYMENT_METHOD_53"] = clean(pm_match.group("val")) if pm_match else None

        # 2. Payment No (Field 54)
        pn_match = re.search(r"\bNO\.?\s*(?P<val>.{0,50}?)\s*ﻢﻗر\s*54", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["PAYMENT_NO_54"]     = clean(pn_match.group("val")) if pn_match else None

        # 3. Payment Date (Field 55)
        pd_match = re.search(r"\bDATE\s*(?P<val>.{0,50}?)\s*ﺦﯾرﺎﺗ\s*55", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["PAYMENT_DATE_55"]   = clean(pd_match.group("val")) if pd_match else None

        # 4. Payment Bank (Field 56)
        pb_match = re.search(r"\bBANK\s*(?P<val>.{0,50}?)\s*(?:بنك|ﻚﻨﺒﻟا|ﻚﻨﺑ)\s*56", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["PAYMENT_BANK_56"] = clean(pb_match.group("val")) if pb_match else None

        # 5. Receipt No (Field 57) 
        rn_match = re.search(r"RECEIPT\s+NO\.?\s*(?P<val>\d+).*?ﻢﻗر\s*57", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["RECEIPT_NO_57"] = clean(rn_match.group("val")) if rn_match else None

        # 6. Receipt Date (Field 58)
        rd_match = re.search(r"\bDATE\s*(?P<val>.{0,50}?)\s*ﺦﯾرﺎﺗ\s*58", self._text1, re.IGNORECASE | re.DOTALL)
        self.data["RECEIPT_DATE_58"]   = clean(rd_match.group("val")) if rd_match else None

        # 7. Receipt Bank (Field 59)
        rb_match = re.search(r"\bBANK\s*(?P<val>.{0,50}?)\s*(?:بنك|ﻚﻨﺒﻟا|ﻚﻨﺑ)\s*59", self._text2, re.IGNORECASE | re.DOTALL)
        self.data["RECEIPT_BANK_59"] = clean(rb_match.group("val")) if rb_match else None


def extract_header(pdf_or_pages: str | list[str], filename: str) -> dict:
    """Wrapper function to preserve backwards compatibility with procedural calls."""
    if isinstance(pdf_or_pages, str):
        extractor = HeaderExtractor(pdf_or_pages, filename)
        header_obj = extractor.extract()
        return header_obj.to_dict()
    else:
        # Fallback if list of pre-extracted pages is passed
        pages1 = list(pdf_or_pages)
        lines1 = [l for l in pages1[0].split('\n') if l.strip()]
        text1  = '\n'.join(lines1) 
        pages2 = extract_pages_layout(pdf_or_pages) if isinstance(pdf_or_pages, str) else list(pdf_or_pages)
        lines2 = [l for l in pages2[0].split('\n') if l.strip()]
        text2  = '\n'.join(lines2) 

        extractor = HeaderExtractor("", filename)
        extractor._lines1 = lines1
        extractor._text1 = text1
        extractor._lines2 = lines2
        extractor._text2 = text2

        extractor._parse_identifiers()
        extractor._parse_delivery_and_importer()
        extractor._parse_carrier_details()
        extractor._parse_measurement_and_reg()
        extractor._parse_packages_and_flight()
        extractor._parse_exported_to()
        extractor._parse_awb_and_manifest()
        extractor._parse_marks_and_numbers()
        extractor._parse_single_value_headers()
        extractor._parse_duties_and_fees()
        extractor._parse_payment_info()
        return BoeHeader(**extractor.data).to_dict()