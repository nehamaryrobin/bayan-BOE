#!/usr/bin/env python3
"""Standalone CLI to print the header regex debug view for a PDF path."""

import argparse
import os
import re
from extractors.pdf_to_text import extract_pages
from extractors.header_extractor import extract_header

def debug_header_regex_view(pdf_or_pages: str | list[str], filename: str) -> None:
    """
    Print the exact raw text and the lines most relevant to the header regex.
    Useful for seeing what the header extractor is actually reading.
    """
    pages = extract_pages(pdf_or_pages) if isinstance(pdf_or_pages, str) else list(pdf_or_pages)
    raw_text = '\n'.join(pages)

    print('\n=== HEADER REGEX DEBUG VIEW ===')
    print(f'FILE: {filename}')
    print(f'PAGES: {len(pages)}')
    print('\n--- RAW TEXT SEEN BY HEADER EXTRACTOR ---')
    print(raw_text)

    print('\n--- LINES THAT MATCH THE HEADER REGEX CLUES ---')
    for i, line in enumerate(raw_text.splitlines(), start=1):
        if re.search(r'Custom\s+Declaration|Dec No|Dec Date|Dec Type|Port Type|بيان|داﺮﯿﺘﺳإ|استيراد|جمركي', line, re.IGNORECASE):
            print(f'[{i:03d}] {line}')

    print('\n--- FIRST HEADER-STYLE REGEX MATCH (if any) ---')
    match = re.search(
        r'Custom\s+Declaration\s*.*?(?P<dec_type>داﺮﯿﺘﺳإ نﺎﯿﺑ|بيان إستيراد|يﻮﺟ|بري|بحري).*?'
        r'(?P<gregorian>\d{2}-\d{2}-\d{4})\s+(?P<hijri>\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})\s+(?P<dec_no>\d{6,8})',
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        print(match.group(0))
        print('\nGROUPS:')
        for name, value in match.groupdict().items():
            print(f'  {name} = {value!r}')
    else:
        print('No header-style regex match found.')

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Display the raw text and regex clues used by the header extractor."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file to inspect.")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        raise FileNotFoundError(f"PDF file not found: {args.pdf_path}")

    debug_header_regex_view(args.pdf_path, os.path.basename(args.pdf_path))


if __name__ == "__main__":
    main()
