import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from extractors.pdf_to_text import extract_pages


def display_text(pdf_path: str) -> None:
    """Extract text from a PDF and print each page to the terminal."""
    pages = extract_pages(pdf_path)

    if not pages:
        print("No pages were extracted from the PDF.")
        return

    for index, text in enumerate(pages, start=1):
        print(f"\n===== Page {index} =====")
        print(text if text else "(No text extracted from this page)")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: python debug/raw_text.py /path/to/file.pdf"""
    args = sys.argv[1:] if argv is None else argv

    if not args:
        print("Usage: python debug/raw_text.py /path/to/file.pdf")
        return 1

    try:
        display_text(args[0])
    except Exception as exc:
        print(f"Error extracting text: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
