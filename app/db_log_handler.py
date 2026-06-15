import logging
from datetime import datetime

class DBLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        # We optionally buffer or connect per log, but for simplicity we will connect per log
        # In a high-throughput system, you would want a queue and a worker thread here.

    def emit(self, record):
        # We must import inside the function to avoid circular imports during logger initialization!
        from db.connection import create_raw_connection
        
        try:
            # We don't want to log the DB connection debug events endlessly
            if record.name == "db.connection":
                return
            
            msg = self.format(record)
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            
            conn = create_raw_connection()
            cursor = conn.cursor()
            query = """
            INSERT INTO app_logs ([timestamp], [log_level], [logger_name], [message])
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (timestamp, record.levelname, record.name, msg))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            self.handleError(record)
