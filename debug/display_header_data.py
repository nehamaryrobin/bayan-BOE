import sys
import os
import json

# Add the root directory to the Python path to allow imports from extractors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractors.header_item_extraction import extract_header

def main():
    if len(sys.argv) < 2:
        print("Usage: python display_header_data.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)
        
    filename = os.path.basename(file_path)
    
    try:
        print(f"Extracting header data from: {file_path}...\n")
        data = extract_header(file_path, filename)
        
        print("--- Extracted Header Data ---")
        print(json.dumps(data, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error extracting data: {e}")

if __name__ == "__main__":
    main()
