import re
import arabic_reshaper
from bidi.algorithm import get_display

# Covers standard Arabic (U+0600-06FF) AND Presentation Forms-B (U+FE70-FEFF)
_AR_RE = re.compile(r'[\u0600-\u06FF\uFE70-\uFEFF]')


def fix_arabic(text: str) -> str:
    if not text or not _AR_RE.search(text):
        return text
    reshaped = arabic_reshaper.reshape(text)
    return str(get_display(reshaped)) #explicit converted to str for type consistency


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
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None