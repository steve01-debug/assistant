import sqlite3
from datetime import datetime
import os

DB_NAME = os.path.join("database", "memory.db")


def connect():
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_NAME)


def init_memory():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        ai TEXT,
        waktu TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS preferences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )
    """)

    # FTS5 table for fast semantic/text research & thesis notes
    try:
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS thesis_notes USING fts5(
            title,
            content,
            category,
            created_at UNINDEXED
        )
        """)
    except sqlite3.OperationalError:
        # Fallback if FTS5 is not compiled into sqlite (standard table with LIKE search)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS thesis_notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            category TEXT,
            created_at TEXT
        )
        """)

    conn.commit()
    conn.close()


def save_chat(user, ai):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO conversations(user, ai, waktu)
    VALUES(?,?,?)
    """, (user, ai, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_history(limit=5):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT user, ai
    FROM conversations
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    data = cursor.fetchall()
    conn.close()
    return data[::-1]


def remember(key, value):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO preferences(key,value)
    VALUES(?,?)
    ON CONFLICT(key)
    DO UPDATE SET value=excluded.value
    """, (key, value))
    conn.commit()
    conn.close()


def recall(key):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT value
    FROM preferences
    WHERE key=?
    """, (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def save_thesis_note(title, content, category="skripsi"):
    """Simpan catatan, kutipan jurnal, atau poin skripsi."""
    conn = connect()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO thesis_notes(title, content, category, created_at)
    VALUES(?,?,?,?)
    """, (title, content, category, now))
    conn.commit()
    conn.close()
    return f"Catatan skripsi '{title}' berhasil disimpan dalam kategori '{category}'."


def search_thesis_notes(query, limit=5):
    """Cari catatan skripsi secara cepat menggunakan full-text search."""
    conn = connect()
    cursor = conn.cursor()
    try:
        # Coba FTS5 match
        # Bersihkan karakter spesial yang bisa merusak query FTS5
        clean_query = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_query:
            clean_query = query.strip()
            
        cursor.execute("""
        SELECT title, content, category, created_at
        FROM thesis_notes
        WHERE thesis_notes MATCH ?
        ORDER BY rank
        LIMIT ?
        """, (f'"{clean_query}"*', limit))
        results = cursor.fetchall()
    except Exception:
        # Fallback LIKE query
        search_pattern = f"%{query}%"
        cursor.execute("""
        SELECT title, content, category, created_at
        FROM thesis_notes
        WHERE title LIKE ? OR content LIKE ? OR category LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, limit))
        results = cursor.fetchall()

    conn.close()
    return results
