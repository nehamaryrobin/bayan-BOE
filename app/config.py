import os

# ── Database ──────────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":      os.getenv("DB_HOST", "localhost"),
    "port":      int(os.getenv("DB_PORT", 3306)),
    "user":      os.getenv("DB_USER", "root"),
    "password":  os.getenv("DB_PASSWORD", ""),
    "database":  os.getenv("DB_NAME", "bayan"),
    "charset":   "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "use_unicode": True,
}

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR      = os.path.join(BASE_DIR, "data", "input")
PROCESSED_DIR  = os.path.join(BASE_DIR, "data", "processed")
FAILED_DIR     = os.path.join(BASE_DIR, "data", "failed")
LOG_FILE       = os.path.join(BASE_DIR, "logs", "bayan.log")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_MAX_BYTES  = 5 * 1024 * 1024   # 5 MB per log file
LOG_BACKUP_COUNT = 5
