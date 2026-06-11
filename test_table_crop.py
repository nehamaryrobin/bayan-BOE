"""
test_table_crop.py
Tests pdfplumber's extract_table() on a specific coordinate region of a BOE PDF.

pdfplumber coordinate system:
  (x0, top, x1, bottom)
  Origin (0,0) is TOP-LEFT of the page
  x increases rightward
  top increases downward

Usage:
    python test_table_crop.py <path_to_pdf>
"""
import sys
import os
import pdfplumber

# ── Define your crop regions here ────────────────────────────────────────────
# Format: (x0, top, x1, bottom)
# Adjust these values to target specific sections of the BOE

REGIONS = {
    "header_fields_5_to_21": (0, 100, 600, 330),   # fields 5-21 table area
    "line_items_table":      (0, 330, 600, 480),   # line items rows
    "package_weight_table":  (0, 450, 600, 560),   # package/weight rows
    "duty_summary":          (0, 560, 300, 680),   # duty totals section
}


def extract_region(page, region_name, bbox, strategy="lines"):
    print(f"\n--- REGION: {region_name} ---")
    print(f"    bbox: {bbox}  strategy: {strategy}")

    # Crop the page to the bounding box
    cropped = page.crop(bbox)

    # Show raw text from this region
    raw_text = cropped.extract_text()
    print(f"\n  Raw text:")
    if raw_text:
        for line in raw_text.split('\n'):
            if line.strip():
                print(f"    {repr(line)}")
    else:
        print("    (empty)")

    # Try table extraction on the cropped region
    print(f"\n  Table (strategy={strategy}):")
    table = cropped.extract_table({
        "vertical_strategy":   strategy,
        "horizontal_strategy": strategy,
    })
    if table:
        for row_idx, row in enumerate(table):
            # Filter out completely empty rows
            if any(cell for cell in row if cell):
                print(f"    Row {row_idx:2}: {row}")
    else:
        print("    No table found")

    # Also try words with coordinates in this region
    print(f"\n  Words with coordinates:")
    words = cropped.extract_words(x_tolerance=3, y_tolerance=3)
    for w in words:
        print(f"    x0={w['x0']:6.1f} top={w['top']:6.1f} | {repr(w['text'])}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_table_crop.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    print(f"\nProcessing: {os.path.basename(pdf_path)}")

    with pdfplumber.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            print(f"\n{'='*60}")
            print(f"  PAGE {page_no} — size: {page.width:.1f} x {page.height:.1f}")
            print(f"{'='*60}")

            for region_name, bbox in REGIONS.items():
                # Try both strategies
                extract_region(page, region_name, bbox, strategy="lines")
                extract_region(page, region_name, bbox, strategy="text")


if __name__ == "__main__":
    main()