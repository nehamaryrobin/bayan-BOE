import os
from dotenv import load_dotenv

load_dotenv()

import os

DB_CONFIG = {
    "host":     "localhost",
    "port":     1433,
    "user":     "SA",
    "password": "NehaSql@2026",
    "database": "bayan",
}

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR      = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR  = os.path.join(BASE_DIR, "data", "processed")
FAILED_DIR     = os.path.join(BASE_DIR, "data", "failed")
LOG_FILE       = os.path.join(BASE_DIR, "logs", "bayan.log")


LOG_MAX_BYTES  = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5