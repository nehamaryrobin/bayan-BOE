import sys
import os
import re

# Add project root to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.pdf_to_text import extract_pages2, extract_words_with_coords

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug/inspect_pdf_read.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print("=" * 80)
    print(f" INSPECTING PDF READING FOR: {os.path.basename(pdf_path)}")
    print("=" * 80)

    # 1. Header Extraction View
    print("\n" + "#" * 80)
    print(" 1. TEXT SEEN BY header_item_extraction.py (Page 1 via extract_pages2)")
    print("#" * 80 + "\n")
    
    try:
        header_pages = extract_pages2(pdf_path)
        if not header_pages:
            print("No text extracted for headers.")
        else:
            lines = [l for l in header_pages[0].split('\n') if l.strip()]
            for idx, line in enumerate(lines):
                print(f"Line {idx:2d}: {line}")
    except Exception as e:
        print(f"Failed to extract header text: {e}")

    # 2. Line Item Extraction View
    print("\n" + "#" * 80)
    print(" 2. ROWS SEEN BY line_item_extraction.py (All Pages, x0 > 10.0, 1-space join)")
    print("#" * 80 + "\n")
    
    try:
        pages_words = extract_words_with_coords(pdf_path)
        for page_no, words in enumerate(pages_words, start=1):
            print(f"--- PAGE {page_no} ---")
            if not words:
                print("  (No words on this page)")
                continue

            # Filter out vertical sidebar letters/words on the left margin (typically x0 <= 10.0)
            filtered_words = [w for w in words if w["x0"] > 10.0]
            if not filtered_words:
                print("  (All words filtered out by x0 > 10.0 margin)")
                continue

            # Group vertically by line (tolerance of 9 points)
            sorted_words = sorted(filtered_words, key=lambda w: w["top"])
            row_groups = []
            current_row = [sorted_words[0]]
            for w in sorted_words[1:]:
                if abs(w["top"] - current_row[0]["top"]) <= 9:
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row:
                row_groups.append(current_row)

            # Print single-space joined lines
            for row_idx, row in enumerate(row_groups):
                row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
                if row_str:
                    print(f"Row {row_idx:2d}: {row_str}")
            print()

    except Exception as e:
        print(f"Failed to extract line item text: {e}")

if __name__ == "__main__":
    main()
