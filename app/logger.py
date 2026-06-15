import logging
import os
from logging.handlers import RotatingFileHandler
from app.config import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT

def get_logger(name: str) -> logging.Logger:

    logger = logging.getLogger(name)
    
    # If logger already configured, return it
    if logger.handlers:
        return logger

    # Configure default handler and level
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # ── Rotating file handler ─────────────────────────────────────────────────
    fh = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # ── Console handler ───────────────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    # ── Database handler ──────────────────────────────────────────────────────
    try:
        from app.db_log_handler import DBLogHandler
        db_handler = DBLogHandler()
        db_handler.setLevel(logging.INFO)
        # We don't use the formatter for DB because we insert the raw message
        # but you can format the message string if desired
        logger.addHandler(db_handler)
    except ImportError:
        pass

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger