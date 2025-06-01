import sqlite3

DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            url TEXT,
            code TEXT,
            type TEXT,
            extra TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_file(file_id, url, code, ftype, extra=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?)", (file_id, url, code, ftype, extra))
    conn.commit()
    conn.close()

def get_files_by_type(ftype):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url, code FROM files WHERE type = ?", (ftype,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "url": r[1], "code": r[2]} for r in rows]

def get_file_by_code(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url, code FROM files WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    return {"id": row[0], "url": row[1], "code": row[2]} if row else None

def get_file_by_id(file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, url, code FROM files WHERE id = ?", (file_id,))
    row = c.fetchone()
    conn.close()
    return {"id": row[0], "url": row[1], "code": row[2]} if row else None

def delete_file(file_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM files WHERE id = ?", (file_id,))
    conn.commit()
    conn.close()
