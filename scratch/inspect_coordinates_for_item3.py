import sys
import pdfplumber

pdf_path = "data/processed/2670362207exemp.pdf"
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[0]
    words = page.extract_words()
    
    # Let's filter words that have a top coordinate near item 3
    # Row 32 (Item 1) gross/net weight top is around... let's find the word '822.00' top
    item1_qty_word = [w for w in words if w["text"] == "822.00"][0]
    item3_qty_word = [w for w in words if w["text"] == "37.00"][0]
    
    print("Item 1 Row words (near top =", item1_qty_word["top"], "):")
    row1_words = [w for w in words if abs(w["top"] - item1_qty_word["top"]) <= 5]
    for w in sorted(row1_words, key=lambda w: w["x0"]):
        print(f"  {w['text']} (x0={w['x0']:.1f}, x1={w['x1']:.1f})")
        
    print("\nItem 3 Row words (near top =", item3_qty_word["top"], "):")
    row3_words = [w for w in words if abs(w["top"] - item3_qty_word["top"]) <= 5]
    for w in sorted(row3_words, key=lambda w: w["x0"]):
        print(f"  {w['text']} (x0={w['x0']:.1f}, x1={w['x1']:.1f})")
