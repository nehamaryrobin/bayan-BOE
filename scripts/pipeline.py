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
import os
from app.logger import get_logger
from extractors.pdf_to_text import extract_pages
from extractors.header_extractor import extract_header
from extractors.line_item_extractor import extract_tabular_groups
from db.connection import get_connection
from db.inserter import insert_boe, is_duplicate
from utils.file_utils import move_to_processed, move_to_failed

logger = get_logger("pipeline")


def process_file(pdf_path: str) -> bool:
    """
    Process a single BOE PDF file end-to-end.
    Returns True on success, False on failure.
    """
    filename = os.path.basename(pdf_path)
    logger.info(f"START | file='{filename}'")

    conn = None
    try:
        # ── Step 1: Extract raw text ──────────────────────────────────────────
        pages = extract_pages(pdf_path)
        if not any(pages):
            raise ValueError(f"No text could be extracted from '{filename}'")

        # ── Step 2: Parse header ──────────────────────────────────────────────
        header = extract_header(pages, filename)
        dec_no = header["DEC_NO"]

        # ── Step 3: Parse line items ──────────────────────────────────────────
        line_items = extract_tabular_groups(pdf_path, filename, dec_no)

        # ── Step 4: Duplicate check ───────────────────────────────────────────
        conn = get_connection()
        if is_duplicate(conn, dec_no, filename):
            logger.warning(
                f"SKIP_DUPLICATE | file='{filename}' | dec_no='{dec_no}'"
            )
            conn.close()
            # Move to processed so it doesn't get reprocessed on restart
            move_to_processed(pdf_path)
            return False

        # ── Step 5: Insert into DB (single transaction) ───────────────────────
        insert_boe(conn, header, line_items)

        # ── Step 6: Move to processed ─────────────────────────────────────────
        move_to_processed(pdf_path)
        logger.info(f"SUCCESS | file='{filename}' | dec_no='{dec_no}'")
        return True

    except Exception as e:
        logger.error(f"FAILED | file='{filename}' | error={e}")
        move_to_failed(pdf_path)
        return False

    finally:
        if conn and conn.is_connected():
            conn.close()
