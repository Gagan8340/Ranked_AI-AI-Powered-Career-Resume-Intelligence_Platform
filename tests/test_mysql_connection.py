import socket
import sys
import pymysql
import os
import requests
from dotenv import load_dotenv

# Step 1 & 2: Load variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
DB_PORT = os.getenv("DB_PORT") or os.getenv("MYSQLPORT")
DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")
DB_USER = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
DB_PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")

print("--- Step 1 & 2: Variable Check ---")
print(f"DB_HOST loaded: {'YES' if DB_HOST else 'NO'} ({DB_HOST})")
print(f"DB_PORT loaded: {'YES' if DB_PORT else 'NO'} ({DB_PORT})")
print(f"DB_NAME loaded: {'YES' if DB_NAME else 'NO'}")
print(f"DB_USER loaded: {'YES' if DB_USER else 'NO'}")
print(f"DB_PASSWORD loaded: {'YES' if DB_PASSWORD else 'NO'}")

# Clean up port
try:
    DB_PORT = int(DB_PORT)
except (ValueError, TypeError):
    DB_PORT = 3306

print("\n--- Step 4 & 5: Connectivity Diagnostics ---")

# DNS Resolution
try:
    ip = socket.gethostbyname(DB_HOST)
    print(f"DNS Resolution: PASS ({ip})")
except Exception as e:
    print(f"DNS Resolution: FAIL ({e})")
    sys.exit(1)

# TCP Socket Test
try:
    s = socket.create_connection((DB_HOST, DB_PORT), timeout=10)
    s.close()
    print("TCP Connectivity: PASS")
except Exception as e:
    print(f"TCP Connectivity: FAIL ({e})")
    sys.exit(1)

# MySQL Authentication and Handshake
try:
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10
    )
    print("MySQL Authentication: PASS")
except pymysql.err.OperationalError as e:
    print(f"MySQL Authentication: FAIL ({e.args[0]} {e.args[1] if len(e.args) > 1 else ''})")
    sys.exit(1)
except Exception as e:
    print(f"MySQL Authentication: FAIL ({e})")
    sys.exit(1)

# SELECT 1
try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("SELECT 1: PASS")
except Exception as e:
    print(f"SELECT 1: FAIL ({e})")
    sys.exit(1)

# SHOW TABLES
try:
    with conn.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"SHOW TABLES: PASS. Tables found: {tables}")
except Exception as e:
    print(f"SHOW TABLES: FAIL ({e})")
finally:
    conn.close()

print("\n--- DONE ---")
