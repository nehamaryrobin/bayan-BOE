"""
connection.py
SQL Server connection using pymssql.
Unicode/NVARCHAR handled natively by SQL Server.
"""
import pymssql
from app.config import DB_CONFIG
from app.logger import get_logger

logger = get_logger("db.connection")


def get_connection():
    try:
        conn = pymssql.connect(
            server=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            charset="UTF-8",
        )
        logger.debug("DB connection established")
        return conn
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        raise