import sys
import os
import json

# Add root directory to path to allow importing from extractors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractors.line_item_extraction import extract_tabular_groups
from extractors.header_item_extraction import extract_header

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/display_line_items.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    filename = os.path.basename(file_path)
    
    print(f"Extracting line items from: {file_path}...\n")
    
    try:
        # 1. Run header extraction to get the DEC_NO dynamically
        header_data = extract_header(file_path, filename)
        dec_no = header_data.get("DEC_NO", "UNKNOWN")
        
        print(f"Found DEC_NO from header: {dec_no}")
        
        # 2. Run line item extraction passing the dynamic DEC_NO
        items = extract_tabular_groups(file_path, filename, dec_no)
        
        print("\n--- Extracted Line Items ---")
        print(json.dumps(items, indent=4, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
