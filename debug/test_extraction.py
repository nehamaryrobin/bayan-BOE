import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.logger import get_logger

logger = get_logger("test_extraction")

from extractors.pdf_to_text import extract_pages
from extractors.header_item_extraction import extract_header
from extractors.line_item_extraction import extract_tabular_groups

def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_field(key: str, value) -> None:
    status = "✓" if value is not None else "✗ NULL"
    print(f"  {status}  {key:<45} {value if value is not None else ''}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_extraction.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    filename = os.path.basename(pdf_path)

    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"\nProcessing: {filename}")

    # ── Step 1: Raw text extraction ───────────────────────────────────────────
    print_section("STEP 1: RAW TEXT EXTRACTION")
    try:
        pages = extract_pages(pdf_path)
        print(f"  Pages found : {len(pages)}")
        for i, page in enumerate(pages, 1):
            print(f"  Page {i}      : {len(page)} characters extracted")

        for i, page in enumerate(pages, 1):
            print(f"\n--- RAW TEXT: PAGE {i} ---")
            print(page)
            print(f"--- END PAGE {i} ---")

    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    full_text = "\n".join(pages)


    # ── Step 2: Header extraction ─────────────────────────────────────────────
    print_section("STEP 2: HEADER FIELDS")
    try:
        header = extract_header(pdf_path, filename)
        for key, value in header.items():
            print_field(key, value)

        null_fields = [k for k, v in header.items() if v is None]
        print(f"\n  Total fields : {len(header)}")
        print(f"  Extracted    : {len(header) - len(null_fields)}")
        print(f"  NULL         : {len(null_fields)}")
        if null_fields:
            print(f"  NULL fields  : {', '.join(null_fields)}")

    except ValueError as e:
        print(f"  CRITICAL FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # ── Step 3: Line Item extraction ──────────────────────────────────────────
    print_section("STEP 3: LINE ITEM FIELDS")
    try:
        dec_no = header.get("DEC_NO", "UNKNOWN")
        line_items = extract_tabular_groups(pdf_path, filename, dec_no)
        
        if not line_items:
            print("  No line items extracted.")
        else:
            print(f"  Found {len(line_items)} line items.\n")
            for item in line_items:
                item_no = item.get("ITEM_NO", "?")
                print(f"  --- ITEM {item_no} ---")
                
                # Count stats for this item
                item_nulls = [k for k, v in item.items() if v is None]
                
                for key, value in item.items():
                    print_field(key, value)
                    
                print(f"\n  Total fields : {len(item)}")
                print(f"  Extracted    : {len(item) - len(item_nulls)}")
                print(f"  NULL         : {len(item_nulls)}")
                if item_nulls:
                    print(f"  NULL fields  : {', '.join(item_nulls)}")
                print()

    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()