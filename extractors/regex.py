import re

_LINE_ITEM_PT1_RE = re.compile(r"""
    ^\s* (?P<total_duty>[\d,]+(?:\.\d+)?)\s+          # 1. Total Duty (Matches 196.38 or 0.00)
    (?P<income_type>[^\d%]+?)\s+                 # 2. Text (Excludes digits/% to prevent bleeding into the next numbers)
    (?:%\s*(?P<duty_rate>\d{1,2}(?:\.\d+)?)\s+)? # 3. OPTIONAL % and duty rate (e.g., % 15)
    (?P<cif_local>[\d,]+(?:\.\d+)?)\s+           # 4. CIF Local Value (e.g., 1,309.23, 14,531.12)
    (?P<currency_rate>\d+(?:\.\d+)?)\s+          # 5. Currency Rate (e.g., 3.75)
    (?P<currency_type>[A-Z]{3})\s+               # 6. Currency Code (e.g., USD)
    (?P<foreign_value>[\d,]+(?:\.\d+)?)\s+       # 7. Foreign Value (e.g., 341.67)
    (?P<origin_country>[A-Z]{2})\s+              # 8. Origin Country (e.g., MX)
    (?P<description>.+?)\s+                      # 9. Goods description (Arabic/English/dashes)
    (?P<hs_code>\d{12})\s+                       # 10. 12 digit int (e.g., 853180300000)
    (?P<item_no>\d{1,2})                         # 11. Item number (e.g., 16)
    \s*$
""", re.VERBOSE)

_LINE_ITEM_PT2_RE = re.compile(r"""
    ^\s*
    # 1. Optional Exemption Code (Field 42)
    (?:(?P<exemption_code>\d{6,12})\s+)?                              
    
    # 2. Optional AIP Block: Duty & No (Fields 37B & 37A)
    # They are paired: if one exists, the other must exist.
    (?:(?P<aip_duty>[\d,]+\.\d+)\s+(?P<aip_no>\d+)\s+)?               
    
    # 3. Mandatory Weights & Unit (Fields 37, 36, 35)
    (?P<gross_weight>[\d,]+\.\d+)\s+                                  
    (?P<net_weight>[\d,]+\.\d+)\s+                                    
    (?P<unit>[^\s\d]+)\s+      # Matches non-digits/non-spaces (handles both وحدة and ةﺪﺣو.)
    
    # 4. Mandatory Item QTY (Field 34)
    (?P<item_qty>[\d,]+\.00)\s+ # Enforces the exact 2 post-decimal zeros                                     
    
    # 5. Optional Package Block: Type & Qty (Fields 33 & 32)
    # Paired: Arabic word without spaces followed by .00 float
    (?:(?P<package_type>[^\s\d]+)\s+(?P<package_qty>[\d,]+\.00)\s+)?  
    
    # 6. Optional Customs Restrictions: Release Ref & Agency (Fields 41 & 40)
    # Paired: 4-12 digit integer followed by text
    (?:(?P<release_ref>\d{4,12})\s+(?P<agency>.+?)\s+)?               
    
    # 7. Mandatory Line Item Number
    (?P<item_no>\d{1,2})                                              
    \s*$
""", re.VERBOSE | re.DOTALL)

import re

AWB_MANIFEST_RE = re.compile(r"""
    ^\s*
    (?P<start_letter>M)\s* # 1. Letter M 
    (?P<manifest_id>\d+)\s* # 2. Integer of any length (e.g., 81487)
    (?P<mid_letter>[BL])\s* # 3. Letter B or L
    (?P<airline_prefix>\d{2,3})\s* # 4. Exactly 2 to 3 digits (e.g., 35 or 235)
    -\s* # 5. Literal hyphen
    (?P<awb_serial>\d{8})           # 6. Exactly 8 digits (e.g., 78282945)
    \s*$
""", re.VERBOSE | re.IGNORECASE)

_DELIVERY_ORDER_RE = re.compile(
    r'DELIVERY\s+ORDER\s+NO[^\n]*?5\s*'
    r'(?P<delivery_order>\(.*?\).*?(?:\d{2}-\d{2}-\d{4})?\s*\d+)',
    re.IGNORECASE | re.DOTALL
)