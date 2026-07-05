import socket
import sys
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("DB_HOST")
port = int(os.getenv("DB_PORT", 3306))
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database = os.getenv("DB_NAME")

print("--- DIAGNOSTICS ---")

# 1. DNS Resolution
try:
    ip = socket.gethostbyname(host)
    print(f"DNS resolution: PASS ({ip})")
except Exception as e:
    print(f"DNS resolution: FAIL ({e})")

# 2. TCP Connection
try:
    s = socket.create_connection((host, port), timeout=5)
    s.close()
    print("TCP connection: PASS")
except Exception as e:
    print(f"TCP connection: FAIL ({e})")

# 3 & 4. MySQL Handshake and Authentication
try:
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=5
    )
    print("MySQL handshake: PASS")
    print("Authentication: PASS")
    conn.close()
except pymysql.err.OperationalError as e:
    if e.args[0] == 1045:
        print("MySQL handshake: PASS")
        print("Authentication: FAIL (Access Denied)")
    else:
        print(f"MySQL handshake: FAIL ({e})")
        print("Authentication: FAIL")
except Exception as e:
    print(f"MySQL handshake: FAIL ({e})")
    print("Authentication: FAIL")
