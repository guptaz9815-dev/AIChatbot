import os
from getpass import getpass
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_chatbot"),
)
name = input("Admin name: ").strip()
email = input("Admin email: ").strip().lower()
password = getpass("Admin password (minimum 8 characters): ")
if len(password) < 8:
    raise SystemExit("Password must be at least 8 characters.")
cur = conn.cursor()
cur.execute("INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,'admin')",
            (name, email, generate_password_hash(password)))
conn.commit()
cur.close()
conn.close()
print("Admin account created.")
