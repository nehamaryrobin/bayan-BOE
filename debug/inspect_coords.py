import os
import sys
import pdfplumber

archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
pdf_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".pdf")]

for pdf_file in sorted(pdf_files)[:5]:
    pdf_path = os.path.join(archive_dir, pdf_file)
    print(f"\n=== {pdf_file} ===")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # Reconstruct rows
        sorted_words = sorted(words, key=lambda w: w["top"])
        row_groups = []
        current_row = [sorted_words[0]]
        for w in sorted_words[1:]:
            if abs(w["top"] - current_row[0]["top"]) <= 9:
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row: row_groups.append(current_row)
        
        for idx, row in enumerate(row_groups):
            row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
            if 'DELIVERY' in row_str or 'IMPORTER' in row_str or 'NET' in row_str or idx in (5, 6, 7, 8, 9, 10):
                # Print each word in the row with its coordinates
                sorted_row = sorted(row, key=lambda w: w["x0"])
                print(f"Row {idx} reconstructed: {row_str}")
                for w in sorted_row:
                    print(f"  Word: {w['text']} (x0={w['x0']:.1f}, x1={w['x1']:.1f}, top={w['top']:.1f})")
