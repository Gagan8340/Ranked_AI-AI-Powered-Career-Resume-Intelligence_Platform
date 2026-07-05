import os
import time
from dotenv import load_dotenv

import pymysql

load_dotenv()

print("--- ENV LOADING REPORT ---")
print(f"DB_HOST loaded: {'YES' if os.getenv('DB_HOST') else 'NO'}")
print(f"DB_PORT loaded: {'YES' if os.getenv('DB_PORT') else 'NO'}")
print(f"DB_NAME loaded: {'YES' if os.getenv('DB_NAME') else 'NO'}")
print(f"DB_USER loaded: {'YES' if os.getenv('DB_USER') else 'NO'}")
print(f"DB_PASSWORD loaded: {'YES' if os.getenv('DB_PASSWORD') else 'NO'}")
print("--------------------------\n")

print("--- RAILWAY CONNECTIVITY ---")
start = time.time()
try:
    conn = pymysql.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        connect_timeout=10
    )
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
    conn.close()
    elapsed = time.time() - start
    print("Status: PASS")
    print(f"Timing: {elapsed:.2f}s")
except Exception as e:
    elapsed = time.time() - start
    print("Status: FAIL")
    print(f"Timing: {elapsed:.2f}s")
    print(f"Error: {e}")
print("----------------------------")
