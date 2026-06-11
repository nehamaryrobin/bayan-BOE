"""
test_extraction.py
Runs extraction on a single BOE PDF and prints results to terminal.
No database connection required.

Usage:
    python test_extraction.py <path_to_pdf>
"""
import sys
import os
import json

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.pdf_to_text import extract_pages, extract_words_with_coords
from extractors.header_extractor import extract_header
# CHANGE 1: Import the new coordinate-based tabular group extractor
from extractors.line_item_extractor import extract_tabular_groups, _clean_row, _NOISE


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
    diagnose(full_text)

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

    # ── Step 3: Debug row strings after grouping/cleaning ─────────────────────
    print_step4_rows(pdf_path)

    # ── Step 4: Line item extraction ──────────────────────────────────────────
    print_section("STEP 4: LINE ITEMS (TABULAR GROUPING)")
    try:
        dec_no = header["DEC_NO"]
        
        # CHANGE 2: Call the geometric extractor using pdf_path instead of parsed text pages
        line_items = extract_tabular_groups(pdf_path, filename, dec_no)
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


def diagnose(text: str) -> None:
    print("\n=== DIAGNOSTIC: LINE BY LINE ===")
    for i, line in enumerate(text.split('\n'), 1):
        if line.strip():
            print(f"{i:3}: {repr(line)}")


def print_step4_rows(pdf_path: str) -> None:
    """
    Print the cleaned row strings that are fed into the regex engine
    after the row-grouping and noise-cleaning step.
    """
    print_section("STEP 4: DEBUG ROWS SENT TO REGEX")

    pages_words = extract_words_with_coords(pdf_path)
    row_count = 0

    for page_no, words in enumerate(pages_words, start=1):
        if not words:
            continue

        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups = []
        current_row = [sorted_words[0]]

        for w in sorted_words[1:]:
            if abs(w["top"] - current_row[0]["top"]) <= 6:
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row:
            row_groups.append(current_row)

        for row in row_groups:
            row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
            row_str = _clean_row(row_str)
            if row_str and row_str not in _NOISE:
                row_count += 1
                print(f"  Page {page_no:>2} | row {row_count:>2}: {row_str}")

    print(f"\n  Total cleaned rows printed: {row_count}")


if __name__ == "__main__":
    main()