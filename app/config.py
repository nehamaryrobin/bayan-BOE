import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "port":     int(os.environ.get("DB_PORT", 1433)),
    "user":     os.environ.get("DB_USER", "SA"),
    "password": os.environ.get("DB_PASSWORD", "NehaSql@2026"),
    "database": os.environ.get("DB_NAME", "bayan"),
}

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE       = os.path.join(BASE_DIR, "logs", "bayan.log")

LOG_MAX_BYTES  = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5

INPUT_DIR      = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR  = os.path.join(BASE_DIR, "data", "processed")
FAILED_DIR     = os.path.join(BASE_DIR, "data", "failed")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(FAILED_DIR, exist_ok=True)