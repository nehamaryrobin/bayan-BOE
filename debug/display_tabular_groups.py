import sys
import os

# Add root directory to path to allow importing from extractors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractors.line_item_extraction import extract_tabular_groups
from extractors.header_item_extraction import extract_header

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/display_tabular_groups.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    filename = os.path.basename(file_path)
    print(f"Extracting lines from: {file_path}...\n")
    
    try:
        header_data = extract_header(file_path, filename)
        dec_no = header_data.get("DEC_NO", "UNKNOWN")
        
        rows = extract_tabular_groups(file_path, filename, dec_no)
        
        print("--- Extracted Items ---")
        for i, row in enumerate(rows, 1):
            print(f"{i:03d}: {row}")
            
    except Exception as e:
        print(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
