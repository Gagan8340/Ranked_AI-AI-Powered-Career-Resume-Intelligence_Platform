import threading
from config import get_db_connection

def increment_metric(key, amount=1):
    """Safely increments a system metric without blocking the main thread."""
    def _run():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO system_metrics (metric_key, metric_value) 
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE 
                    metric_value = metric_value + %s
                """, (key, amount, amount))
            conn.commit()
        except Exception as e:
            print(f"Telemetry Error ({key}): {e}")
        finally:
            conn.close()
            
    threading.Thread(target=_run).start()

def record_latency(key, milliseconds):
    """Records execution time by incrementing total time and call count."""
    def _run():
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # Add to total time
                cursor.execute("""
                    INSERT INTO system_metrics (metric_key, metric_value) 
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE 
                    metric_value = metric_value + %s
                """, (f"{key}_time_ms", milliseconds, milliseconds))
                
                # Increment count
                cursor.execute("""
                    INSERT INTO system_metrics (metric_key, metric_value) 
                    VALUES (%s, 1)
                    ON DUPLICATE KEY UPDATE 
                    metric_value = metric_value + 1
                """, (f"{key}_calls",))
            conn.commit()
        except Exception as e:
            print(f"Telemetry Latency Error ({key}): {e}")
        finally:
            conn.close()
            
    threading.Thread(target=_run).start()
