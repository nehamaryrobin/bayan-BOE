import sys
import os

sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.header_item_extraction import extract_header

pdf_path = "data/archive/2660199588.pdf"
res = extract_header(pdf_path, os.path.basename(pdf_path))
print("COMMERCIAL_REG_NO_12:", repr(res.get("COMMERCIAL_REG_NO_12")))
print("MEASUREMENT_13:", repr(res.get("MEASUREMENT_13")))
print("CARRIER_NAME_11:", repr(res.get("CARRIER_NAME_11")))
