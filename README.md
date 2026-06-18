# Bayan BOE Pipeline

Extracts data from Saudi Customs Bill of Entry (BOE) PDFs and inserts it into Microsoft SQL Server (MSSQL).

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
│   ├── connection.py      # MSSQL connection (pymssql)
│   ├── models.sql         # CREATE TABLE scripts for SQL Server
│   └── inserter.py        # Transactional insert
├── utils/
│   ├── arabic_utils.py    # Arabic reshaper + bidi fix
│   └── file_utils.py      # Move files between folders
├── logs/
│   └── bayan.log
├── scripts/
│   ├── pipeline.py        # Single-file processor
│   └── run_pipeline.py    # Watchdog entry point
├── requirements.txt
└── .env.example           # Example environment variables
```

## Setup Instructions

### 1. Create and Activate Virtual Environment
It is highly recommended to run this in a Python virtual environment.

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create the Database Schema
Execute the SQL script located in `db/models.sql` in your SQL Server instance using tools like SQL Server Management Studio (SSMS), Azure Data Studio, or `sqlcmd`. This will create the `bayan` database and necessary tables.

### 4. Configure Credentials
Copy `.env.example` to `.env` and fill in your SQL Server connection details:

```bash
cp .env.example .env
```
Ensure your `.env` file looks something like this:
```ini
DB_HOST=localhost
DB_PORT=1433
DB_USER=SA
DB_PASSWORD=your_password
DB_NAME=bayan
```

### 5. Run the Pipeline
Start the watchdog service which continuously monitors the input folder:
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