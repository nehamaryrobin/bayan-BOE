import re
import arabic_reshaper
from bidi.algorithm import get_display


def fix_arabic(text: str) -> str:
    """
    Reshape and reorder Arabic text extracted from PDF (which is often
    stored in visual/RTL order) into proper logical Unicode order for DB storage.
    Returns the original text unchanged if it contains no Arabic characters.
    """
    if not text or not _has_arabic(text):
        return text
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _has_arabic(text: str) -> bool:
    """Return True if text contains any Arabic Unicode characters."""
    return bool(re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+', text))


def clean(value) -> str | None:
    """
    Strip whitespace from a value. Return None if empty after stripping.
    Applies Arabic fix if Arabic characters are detected.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return fix_arabic(text)


def clean_number(value) -> float | None:
    """
    Parse a numeric string (may contain commas) to float.
    Returns None if empty or unparseable.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None
