import sys
import os
import fitz

def view_fitz_lines(pdf_path: str):
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        print(f"\n=========================================")
        print(f"               PAGE {i}                  ")
        print(f"=========================================")
        text = page.get_text("text")
        lines = text.split("\n")
        for line_no, line in enumerate(lines, start=1):
            # Print with line number representation
            print(f"{line_no:03d} | {line}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_fitz_lines.py <pdf_path_or_name>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    
    # Resolve if it is just a filename/basename
    if not os.path.exists(pdf_path):
        processed_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/processed"
        input_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/input"
        archive_dir = "/Users/nehamaryrobin/Documents/expeditors/bayan_boe/data/archive"
        
        found = False
        for d in [processed_dir, input_dir, archive_dir]:
            files = [f for f in os.listdir(d) if f.startswith(pdf_path) and f.lower().endswith(".pdf")]
            if files:
                pdf_path = os.path.join(d, files[0])
                found = True
                break
                
        if not found:
            print(f"Could not find PDF matching {pdf_path}")
            sys.exit(1)
            
    view_fitz_lines(pdf_path)
