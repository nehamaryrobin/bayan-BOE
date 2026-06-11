"""
text_extraction2.py

Diagnostic script to show the exact text/lines that the header extractor
works with after its step-3 cleaning stage, and then to continue into the
line-item step-4 diagnostic path.

Usage:
    /Users/nehamaryrobin/Documents/expeditors/bayan_boe/venv/bin/python text_extraction2.py data/processed/2670362146.PDF
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.pdf_to_text import extract_pages
from extractors.header_extractor import _strip_noise, _find_line, _get, _arabic_tokens, _arabic_str
from extractors.line_item_extractor import _clean_row, _NOISE
from extractors.pdf_to_text import extract_words_with_coords


def print_section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def show_header_lines(pages):
    print_section("STEP 3: HEADER LINES AFTER NOISE STRIPPING")
    cleaned_pages = _strip_noise(pages)
    lines = [l for l in cleaned_pages[0].split('\n') if l.strip()]

    print(f"  Raw page count      : {len(pages)}")
    print(f"  Cleaned page count  : {len(cleaned_pages)}")
    print(f"  Header lines seen   : {len(lines)}")
    print("\n  --- EXACT LINES PASSED TO HEADER EXTRACTOR ---")
    for i, line in enumerate(lines, 1):
        print(f"  [{i:02d}] {line!r}")

    print("\n  --- FIRST 20 LINES (readable view) ---")
    for i, line in enumerate(lines[:20], 1):
        print(f"  [{i:02d}] {line}")


def show_step4_row_debug(pdf_path: str) -> None:
    print_section("STEP 4: ROWS THE REGEX ENGINE ACTUALLY SEES")
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python text_extraction2.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"\nProcessing: {os.path.basename(pdf_path)}")

    try:
        pages = extract_pages(pdf_path)
        show_header_lines(pages)
        show_step4_row_debug(pdf_path)
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
