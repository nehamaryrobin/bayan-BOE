"""
test_extraction.py
Runs extraction on a single BOE PDF and prints results to terminal.
No database connection required.

Usage:
    python test_extraction.py <path_to_pdf>

Example:
    python test_extraction.py data/input/BOE_MAIR.pdf
"""
import sys
import os
import json

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.pdf_to_text import extract_pages
from extractors.header_extractor import extract_header
from extractors.line_item_extractor import extract_line_items


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

        # Print raw text of each page for inspection
        for i, page in enumerate(pages, 1):
            print(f"\n--- RAW TEXT: PAGE {i} ---")
            print(page)
            print(f"--- END PAGE {i} ---")

    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # ── Step 2: Header extraction ─────────────────────────────────────────────
    print_section("STEP 2: HEADER FIELDS")
    try:
        header = extract_header(pages, filename)
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

    # ── Step 3: Line item extraction ──────────────────────────────────────────
    print_section("STEP 3: LINE ITEMS")
    try:
        dec_no = header["DEC_NO"]
        line_items = extract_line_items(pages, filename, dec_no)
        print(f"  Items found: {len(line_items)}\n")

        for item in line_items:
            print(f"  --- Item {item.get('ITEM_NO')} ---")
            for key, value in item.items():
                if key not in ("DEC_NO", "PDF_FILENAME"):
                    print_field(key, value)
            print()

    except ValueError as e:
        print(f"  CRITICAL FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    # ── Summary ───────────────────────────────────────────────────────────────
    print_section("SUMMARY")
    print(f"  File      : {filename}")
    print(f"  DEC_NO    : {header.get('DEC_NO')}")
    print(f"  Items     : {len(line_items)}")
    print(f"  Status    : Ready for DB insert\n")


if __name__ == "__main__":
    main()