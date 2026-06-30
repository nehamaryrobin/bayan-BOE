import re
import unicodedata
import arabic_reshaper
from bidi.algorithm import get_display


# Covers standard Arabic, Presentation Forms-B, and Presentation Forms-A
_AR_RE = re.compile(r'([\u0600-\u06FF\uFE70-\uFEFF\uFB50-\uFDFF]+(?:\s+[\u0600-\u06FF\uFE70-\uFEFF\uFB50-\uFDFF]+)*)')


def fix_arabic(text: str) -> str:
    """
    Three-stage Arabic text correction applied only to Arabic chunks of a string,
    preserving non-Arabic segments (English, numbers, etc.) in their original positions:
      1. arabic_reshaper  — fixes character shapes (isolated → connected)
      2. python-bidi      — restores correct RTL word order
      3. NFKC normalize   — converts Presentation Forms back to standard Arabic characters
    """
    if not text:
        return text

    parts = []
    last_end = 0
    for match in _AR_RE.finditer(text):
        start, end = match.span()
        if start > last_end:
            parts.append(text[last_end:start])
        arabic_chunk = match.group(1)

        reshaped  = str(arabic_reshaper.reshape(arabic_chunk))
        reordered = get_display(reshaped)
        normalized = unicodedata.normalize('NFKC', str(reordered))

        # Append Left-To-Right Mark (LRM) \u200E to force subsequent numbers/weak characters
        # to flow Left-To-Right, matching the expected reading order in English text fields.
        parts.append(normalized + '\u200E')
        last_end = end

    if last_end < len(text):
        parts.append(text[last_end:])

    return "".join(parts) if parts else text


def clean(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return fix_arabic(text)


def clean_number(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(',', '')
    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if match:
        return match.group(0)
    return None