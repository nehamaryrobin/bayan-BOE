import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.pdf_to_text import extract_words_with_coords

def view_line_items(pdf_path: str):
    print(f"Extracting words with coords from {pdf_path}...")
    pages_words = extract_words_with_coords(pdf_path)
    
    for page_no, words in enumerate(pages_words, start=1):
        if not words: continue
        
        print(f"\n--- PAGE {page_no} ---")
        # Filter out vertical sidebar letters/words on the left margin (typically x0 <= 10.0)
        filtered_words = [w for w in words if w["x0"] > 10.0]
        if not filtered_words: continue
        
        sorted_words = sorted(filtered_words, key=lambda w: w["top"])
        row_groups = []
        current_row = [sorted_words[0]]
        
        for w in sorted_words[1:]:
            if abs(w["top"] - current_row[0]["top"]) <= 5: # Y-Tolerance
                current_row.append(w)
            else:
                row_groups.append(current_row)
                current_row = [w]
        if current_row: row_groups.append(current_row)

        for row in row_groups:
            row_str = " ".join(w["text"] for w in sorted(row, key=lambda w: w["x0"])).strip()
            if row_str:
                print(row_str)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python view_line_items.py <pdf_path>")
        sys.exit(1)
        
    pdf_path = sys.argv[1]
    
    # Try resolving if it's just a filename
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
            
    view_line_items(pdf_path)
