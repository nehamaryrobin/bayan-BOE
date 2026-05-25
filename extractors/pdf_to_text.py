"""
pdf_to_text.py
Extracts raw text from each page of a BOE PDF using pdfplumber.
Returns a list of page strings (one per page).
"""
import pdfplumber
from app.logger import get_logger

logger = get_logger("pdf_to_text")


def extract_pages(pdf_path: str) -> list[str]:
    """
    Open the PDF and return a list of raw text strings, one per page.
    Raises on any read error so the pipeline can catch and roll back.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(x_tolerance=3, y_tolerance=3)
            if text:
                pages.append(text)
                logger.debug(f"Page {i}: extracted {len(text)} characters")
            else:
                logger.debug(f"Page {i}: no text extracted")
                pages.append("")
    return pages


def extract_words_with_coords(pdf_path: str) -> list[list[dict]]:
    """
    Return words with their bounding-box coordinates for each page.
    Used by extractors that need positional parsing (e.g. line items).
    Each word dict has: text, x0, top, x1, bottom, page_no
    """
    all_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True,
            )
            for w in words:
                w["page_no"] = i
            all_pages.append(words)
    return all_pages
