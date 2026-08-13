import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.getcwd(), "app.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        action TEXT,
        details TEXT
    )
    ''')
    conn.commit()
    conn.close()

async def log_activity(action: str, details: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO activity (timestamp, action, details) VALUES (?, ?, ?)",
                (datetime.utcnow().isoformat(), action, details))
    conn.commit()
    conn.close()
