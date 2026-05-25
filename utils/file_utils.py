import os
import shutil
from app.config import PROCESSED_DIR, FAILED_DIR
from app.logger import get_logger

logger = get_logger("file_utils")


def move_to_processed(filepath: str) -> None:
    _move(filepath, PROCESSED_DIR)


def move_to_failed(filepath: str) -> None:
    _move(filepath, FAILED_DIR)


def _move(filepath: str, destination_dir: str) -> None:
    filename = os.path.basename(filepath)
    dest = os.path.join(destination_dir, filename)

    # If a file with the same name already exists in dest, suffix it
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        import time
        dest = os.path.join(destination_dir, f"{base}_{int(time.time())}{ext}")

    try:
        shutil.move(filepath, dest)
        logger.debug(f"Moved '{filename}' → '{destination_dir}'")
    except Exception as e:
        logger.error(f"Failed to move '{filename}' to '{destination_dir}': {e}")
