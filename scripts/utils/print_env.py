import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
name = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
pw = os.getenv("DB_PASSWORD")

print("--- RUNTIME VALUES ---")
print(f"DB_HOST='{host}' (type: {type(host)})")
print(f"DB_PORT='{port}' (type: {type(port)})")
print(f"DB_NAME='{name}' (type: {type(name)})")
print(f"DB_USER='{user}' (type: {type(user)})")
print(f"DB_PASSWORD=***MASKED*** (length: {len(pw) if pw else 0})")
