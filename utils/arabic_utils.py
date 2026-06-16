import re
import unicodedata
import arabic_reshaper
from bidi.algorithm import get_display


# Covers standard Arabic (U+0600-06FF) AND Presentation Forms-B (U+FE70-FEFF)
_AR_RE = re.compile(r'[\u0600-\u06FF\uFE70-\uFEFF]')


def fix_arabic(text: str) -> str:
    """
    Three-stage Arabic text correction:
      1. arabic_reshaper  — fixes character shapes (isolated → connected)
      2. python-bidi      — restores correct RTL word order
      3. NFKC normalize   — converts Presentation Forms-B (U+FE70-FEFF)
                            to standard Arabic (U+0600-06FF) for clean DB storage
    """
    if not text or not _AR_RE.search(text):
        return text
    reshaped  = str(arabic_reshaper.reshape(text))
    reordered = get_display(reshaped)
    return unicodedata.normalize('NFKC', str(reordered))


def clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return fix_arabic(text)


def clean_number(value) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    text = re.sub(r'[^\d.-]', '', text)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None