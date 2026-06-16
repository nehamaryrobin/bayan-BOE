import os
import sys

# Add project root to path
sys.path.insert(0, "/Users/nehamaryrobin/Documents/expeditors/bayan_boe")

from extractors.header_item_extraction import extract_header

failed_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/failed"
pdf_files = [f for f in os.listdir(failed_dir) if f.lower().endswith(".pdf")]

print(f"Found {len(pdf_files)} failed PDFs.")
for pdf_file in sorted(pdf_files):
    pdf_path = os.path.join(failed_dir, pdf_file)
    try:
        header = extract_header(pdf_path, pdf_file)
        print(f"\n=== {pdf_file} ===")
        print(f"  DEC_NO: {header.get('DEC_NO')}")
        print(f"  NET_WEIGHT_7B: {header.get('NET_WEIGHT_7B')}")
        print(f"  UNLOAD_DATE_7A: {header.get('UNLOAD_DATE_7A')}")
        print(f"  IMPORTER_EXPORTER_6: {header.get('IMPORTER_EXPORTER_6')}")
        print(f"  DELIVERY_ORDER_NO_5: {header.get('DELIVERY_ORDER_NO_5')}")
    except Exception as e:
        print(f"  Error for {pdf_file}: {e}")
