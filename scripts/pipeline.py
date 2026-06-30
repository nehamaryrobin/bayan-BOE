"""
pipeline.py
Orchestrates the full BOE processing pipeline for a single PDF file:
  1. Extract raw text from PDF
  2. Parse header fields
  3. Parse line items
  4. Check for duplicates
  5. Insert into MySQL (single transaction)
  6. Move file to processed/ or failed/
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.logger import get_logger
from extractors.pdf_to_text import NonNativePdfError, extract_pages
from extractors.header_item_extraction import extract_header
from extractors.line_item_extraction import extract_tabular_groups
from db.connection import transaction_context
from db.inserter import insert_boe, is_duplicate
from utils.file_utils import move_to_processed, move_to_failed
import watchdog

logger = get_logger("pipeline")


def process_file(pdf_path: str) -> bool:
    """
    Process a single BOE PDF file end-to-end.
    Returns True on success, False on failure.
    """
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    logger.info(f"START | file='{filename}'")

    try:
        # ── Step 1: Extract raw text ──────────────────────────────────────────
        pages = extract_pages(pdf_path)
        if not any(pages):
            raise ValueError(f"No text could be extracted from '{filename}'")

        # ── Step 2: Parse header ──────────────────────────────────────────────
        header = extract_header(pdf_path, filename)
        dec_no = header["DEC_NO"]

        # ── Step 3: Parse line items ──────────────────────────────────────────
        line_items = extract_tabular_groups(pdf_path, filename, dec_no)

        # ── Step 4: Database Transaction (Duplicate Check & Insertion) ────────
        with transaction_context() as conn:
            if is_duplicate(conn, dec_no, filename):
                logger.warning(
                    f"SKIP_DUPLICATE | file='{filename}' | dec_no='{dec_no}'"
                )
                move_to_processed(pdf_path)
                return False

            # ── Step 5: Insert into DB ─────────────────────────────────────────
            insert_boe(conn, header, line_items)

        # ── Step 6: Move to processed ─────────────────────────────────────────
        move_to_processed(pdf_path)
        logger.info(f"SUCCESS | file='{filename}' | dec_no='{dec_no}'")
        return True

    except NonNativePdfError as e:
        logger.error(f"FAILED_NON_NATIVE_PDF | file='{filename}' | error={e}")
        move_to_failed(pdf_path)
        return False
    except Exception as e:
        logger.error(f"FAILED | file='{filename}' | error={e}")
        move_to_failed(pdf_path)
        return False


def main() -> int:
    """Entry point for running the pipeline directly from the command line."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process a single BOE PDF file end-to-end."
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the BOE PDF file to process",
    )
    args = parser.parse_args()

    pdf_path = args.pdf_path
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return 1

    success = process_file(pdf_path)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())