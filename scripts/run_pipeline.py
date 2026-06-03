"""
run_pipeline.py
Watches data/input/ continuously using watchdog.
Processes each new PDF as it arrives.

Usage:
    python scripts/run_pipeline.py
"""
import sys
import os
import time

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from app.config import INPUT_DIR  # Path to watch for new PDFs
from app.logger import get_logger
from scripts.pipeline import process_file  

logger = get_logger("watcher")


class BOEHandler(FileSystemEventHandler):
    """Handles new file creation events in the input directory."""

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return

        path = event.src_path
        if not str(path).lower().endswith(".pdf"):
            logger.debug(f"Ignoring non-PDF file: {path}")
            return

        # Brief pause to ensure the file is fully written before reading
        time.sleep(1)

        logger.info(f"New file detected: '{os.path.basename(str(path))}'")
        process_file(str(path))


def main() -> None:
    logger.info(f"Watching folder: {INPUT_DIR}")
    logger.info("Press Ctrl+C to stop.")

    # Process any PDFs already sitting in input/ on startup
    _process_existing()

    event_handler = BOEHandler()
    observer = Observer()
    observer.schedule(event_handler, INPUT_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        logger.info("Shutdown requested — stopping watcher.")
        observer.stop()

    observer.join()
    logger.info("Watcher stopped.")


def _process_existing() -> None:
    """Process any PDF files already in input/ at startup."""
    existing = [
        f for f in os.listdir(INPUT_DIR)
        if f.lower().endswith(".pdf")
    ]
    if existing:
        logger.info(f"Found {len(existing)} existing PDF(s) in input/ — processing now.")
        for fname in existing:
            process_file(os.path.join(INPUT_DIR, fname))
    else:
        logger.info("No existing PDFs in input/ — waiting for new files.")


if __name__ == "__main__":
    main()
