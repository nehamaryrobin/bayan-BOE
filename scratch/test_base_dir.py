import sys
import os
import unicodedata
import arabic_reshaper
from bidi.algorithm import get_display

def fix_arabic_rtl(text: str) -> str:
    reshaped  = str(arabic_reshaper.reshape(text))
    reordered = get_display(reshaped, base_dir="R")
    return unicodedata.normalize('NFKC', str(reordered))

def fix_arabic_ltr(text: str) -> str:
    reshaped  = str(arabic_reshaper.reshape(text))
    reordered = get_display(reshaped, base_dir="L")
    return unicodedata.normalize('NFKC', str(reordered))

def main():
    test_cases = [
        "ةﺮﺧﺎﺒﻟا لﻮﺻو كﺮﻤﺠﺑ ﻦﺤﺸﻟا ﺔﻘﻄﻨﻣ 29-10-1447 200017 314",
        "(FCL) ﺔﻠﻣﺎﻛ ﺔﯾوﺎﺣ 27-11-1447 96149571"
    ]
    
    for t in test_cases:
        print(f"Original: {t}")
        print(f"  Base LTR: {fix_arabic_ltr(t)}")
        print(f"  Base RTL: {fix_arabic_rtl(t)}")
        print("-" * 50)

if __name__ == "__main__":
    main()
