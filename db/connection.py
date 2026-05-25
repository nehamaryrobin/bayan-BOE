"""
connection.py
MySQL connection using utf8mb4 for full Arabic/Unicode support.
"""
import mysql.connector
from mysql.connector import MySQLConnection
from app.config import DB_CONFIG
from app.logger import get_logger

logger = get_logger("db.connection")

def get_connection() -> MySQLConnection:
    """Return a new MySQL connection configured for utf8mb4."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        # Enforce utf8mb4 at session level as a belt-and-suspenders measure
        cursor = conn.cursor()
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("SET CHARACTER SET utf8mb4")
        cursor.close()
        return conn
    except mysql.connector.Error as e:
        logger.error(f"DB connection failed: {e}")
        raise
