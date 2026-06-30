"""
pdf_to_text.py
Extracts raw text from each page of a BOE PDF using pdfplumber.
Returns a list of page strings (one per page).
"""

import pdfplumber
import fitz
from app.logger import get_logger

logger = get_logger("pdf_to_text")


class NonNativePdfError(Exception):
    """Raised when a PDF appears to be image/scanned instead of native text-based."""

def extract_pages(pdf_path: str) -> list[str]:
    """
    Open the PDF and return a list of raw text strings, one per page.

    Raises:
        NonNativePdfError: if the file appears to be a scanned/image PDF
                           instead of a native text PDF.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF contains no pages")

        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
            has_images = bool(getattr(page, "images", None))

            if text and text.strip():
                pages.append(text)
                logger.debug(f"Page {i}: extracted {len(text)} characters")
                continue

            if has_images:
                raise NonNativePdfError(
                    f"PDF appears to be image/scanned (non-native) on page {i}: "
                    "no selectable text could be extracted"
                )

            logger.debug(f"Page {i}: no text extracted")
            pages.append("")
    return pages


def extract_pages2(pdf_path: str) -> list[str]:
    """
    Open the PDF and return a list of raw text strings, one per page,
    reconstructed by sorting words by visual layout coordinates.
    Wide visual gaps (greater than 15 points) are padded with multiple spaces.
    """
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError("PDF contains no pages")

        for i, page in enumerate(pdf.pages, start=1):
            words = page.extract_words()
            has_images = bool(getattr(page, "images", None))
            
            if not words:
                if has_images:
                    raise NonNativePdfError(
                        f"PDF appears to be image/scanned (non-native) on page {i}: "
                        "no selectable text could be extracted"
                    )
                pages.append("")
                continue

            # Group words vertically by line (using top coordinate tolerance of 9 points)
            sorted_words = sorted(words, key=lambda w: w["top"])
            row_groups = []
            current_row = [sorted_words[0]]
            for w in sorted_words[1:]:
                if abs(w["top"] - current_row[0]["top"]) <= 9:
                    current_row.append(w)
                else:
                    row_groups.append(current_row)
                    current_row = [w]
            if current_row:
                row_groups.append(current_row)

            # Reconstruct horizontal text lines
            lines = []
            for row in row_groups:
                sorted_row = sorted(row, key=lambda w: w["x0"])
                line_parts = []
                for idx, w in enumerate(sorted_row):
                    if idx > 0:
                        gap = w["x0"] - sorted_row[idx - 1]["x1"]
                        # Insert a column spacer for wide visual gaps
                        spacing = "    " if gap > 15 else " "
                        line_parts.append(spacing)
                    line_parts.append(w["text"])
                lines.append("".join(line_parts).strip())

            pages.append("\n".join(lines))
            logger.debug(f"Page {i}: reconstructed text using coordinates")

    return pages


def extract_pages3(pdf_path: str) -> list[str]:
    """
    Open the PDF using PyMuPDF (fitz) and return a list of raw text strings, one per page.
    This preserves the correct logical reading order for bidirectional text.

    Raises:
        NonNativePdfError: if the file appears to be a scanned/image PDF
                           instead of a native text PDF.
    """
    pages = []
    with fitz.open(pdf_path) as doc:
        if len(doc) == 0:
            raise ValueError("PDF contains no pages")

        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            has_images = bool(page.get_images())

            if text and text.strip():
                pages.append(text)
                logger.debug(f"Page {i}: extracted {len(text)} characters using PyMuPDF")
                continue

            if has_images:
                raise NonNativePdfError(
                    f"PDF appears to be image/scanned (non-native) on page {i}: "
                    "no selectable text could be extracted"
                )

            logger.debug(f"Page {i}: no text extracted using PyMuPDF")
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

