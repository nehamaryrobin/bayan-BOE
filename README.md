# Bayan BOE Pipeline

Extracts data from Saudi Customs Bill of Entry (BOE) PDFs and inserts it into MySQL.

## Folder Structure

```
bayan_boe/
├── app/
│   ├── config.py          # DB credentials, paths
│   └── logger.py          # Rotating file + console logger
├── data/
│   ├── input/             # Drop PDFs here
│   ├── processed/         # Successfully processed PDFs
│   └── failed/            # PDFs that failed extraction or insert
├── extractors/
│   ├── pdf_to_text.py     # Raw text extraction via pdfplumber
│   ├── header_extractor.py
│   └── line_item_extractor.py
├── db/
│   ├── connection.py      # MySQL connection (utf8mb4)
│   ├── models.sql         # CREATE TABLE scripts
│   └── inserter.py        # Transactional insert
├── utils/
│   ├── arabic_utils.py    # Arabic reshaper + bidi fix
│   └── file_utils.py      # Move files between folders
├── logs/
│   └── bayan.log
├── scripts/
│   ├── pipeline.py        # Single-file processor
│   └── run_pipeline.py    # Watchdog entry point
└── requirements.txt
```

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create the database
```bash
mysql -u root -p < db/models.sql
```

### 3. Configure credentials
Edit `app/config.py` or set environment variables:
```bash
export DB_HOST=your_host
export DB_PORT=3306
export DB_USER=your_user
export DB_PASSWORD=your_password
export DB_NAME=bayan
```

### 4. MySQL server config
Add to `my.cnf` / `my.ini`:
```ini
[mysqld]
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
```

### 5. Run
```bash
python scripts/run_pipeline.py
```

Drop any BOE PDF into `data/input/` — it will be picked up automatically.

## Behaviour

| Event | Result |
|---|---|
| New PDF arrives | Extracted → inserted → moved to `processed/` |
| Duplicate (same dec_no + filename) | Skipped + logged → moved to `processed/` |
| Extraction or DB error | Full rollback → moved to `failed/` |
| Field missing | NULL stored, warning logged with field name |

## Logs

`logs/bayan.log` (rotating, max 5 MB × 5 files)

- File level: `SUCCESS` or `FAILED` with filename + dec_no
- Field level: `FIELD_FAIL` with field name, only when extraction fails
