import os
import sys
import pdfplumber

pdf_path = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/failed/7660135521.pdf"

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    for tol in [1.0, 1.5, 2.0, 3.0]:
        print(f"\n--- x_tolerance={tol} ---")
        text = page.extract_text(layout=True, x_tolerance=tol, y_tolerance=3)
        for l in text.split('\n'):
            if 'DELIVERY ORDER' in l or 'IMPORTER' in l or 'NET' in l or '08-12-1447' in l:
                print(l)
