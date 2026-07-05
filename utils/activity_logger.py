import json
from datetime import datetime

from config import get_db_connection


def log_activity(user_id, action, metadata=None):
    if not user_id or not action:
        return
    payload = json.dumps(metadata or {}) if metadata is not None else None
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO activity_logs (user_id, action, details, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, action, payload, datetime.utcnow()),
            )
        connection.commit()
    finally:
        connection.close()
