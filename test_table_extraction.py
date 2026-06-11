"""
test_table_extraction.py
Tests pdfplumber's extract_table() on a BOE PDF and prints results.

Usage:
    python test_table_extraction.py <path_to_pdf>

Example:
    python test_table_extraction.py data/input/BOE_MAIR.pdf
"""
import sys
import os
import pdfplumber

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_table_extraction.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"\nProcessing: {os.path.basename(pdf_path)}")

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):

            print(f"\n{'='*60}")
            print(f"  PAGE {page_no}")
            print(f"{'='*60}")

            # ── Method 1: extract_table (default settings) ────────────────
            print("\n--- METHOD 1: extract_table (default) ---")
            table = page.extract_table()
            if table:
                for row_idx, row in enumerate(table):
                    print(f"  Row {row_idx:2}: {row}")
            else:
                print("  No table found")

            # ── Method 2: extract_tables (finds ALL tables on page) ───────
            print("\n--- METHOD 2: extract_tables (all tables) ---")
            tables = page.extract_tables()
            print(f"  Tables found: {len(tables)}")
            for t_idx, table in enumerate(tables):
                print(f"\n  Table {t_idx + 1} ({len(table)} rows):")
                for row_idx, row in enumerate(table):
                    print(f"    Row {row_idx:2}: {row}")

            # ── Method 3: extract_table with custom settings ───────────────
            print("\n--- METHOD 3: extract_table (explicit lines strategy) ---")
            table_settings = {
                "vertical_strategy":   "lines",
                "horizontal_strategy": "lines",
            }
            table = page.extract_table(table_settings)
            if table:
                for row_idx, row in enumerate(table):
                    print(f"  Row {row_idx:2}: {row}")
            else:
                print("  No table found with lines strategy")

            # ── Method 4: extract_table with text strategy ─────────────────
            print("\n--- METHOD 4: extract_table (text strategy) ---")
            table_settings = {
                "vertical_strategy":   "text",
                "horizontal_strategy": "text",
            }
            table = page.extract_table(table_settings)
            if table:
                for row_idx, row in enumerate(table):
                    print(f"  Row {row_idx:2}: {row}")
            else:
                print("  No table found with text strategy")

if __name__ == "__main__":
    main()