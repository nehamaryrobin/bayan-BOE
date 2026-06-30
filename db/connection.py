"""
connection.py
SQL Server connection using pymssql.
Unicode/NVARCHAR handled natively by SQL Server.
"""
import pymssql
from contextlib import contextmanager
from app.config import DB_CONFIG
from app.logger import get_logger

logger = get_logger("db.connection")


def create_raw_connection():
    return pymssql.connect(
        server=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset="UTF-8",
    )

def get_connection():
    try:
        conn = create_raw_connection()
        logger.debug("DB connection established")
        return conn
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        raise

@contextmanager
def transaction_context():
    """
    Context manager for database connections.
    Automatically commits on success or rolls back on exception,
    ensuring that the connection is always closed.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed and rolled back: {e}")
        raise
    finally:
        conn.close()