import sqlite3
from datetime import datetime
import os


DB_NAME = os.path.join(
    "database",
    "memory.db"
)

def connect():
    os.makedirs(
        "database",
        exist_ok=True
    )

    return sqlite3.connect(DB_NAME)



# membuat database
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


    conn.commit()
    conn.close()



# simpan percakapan
def save_chat(user, ai):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO conversations(user, ai, waktu)
    VALUES(?,?,?)
    """,
    (
        user,
        ai,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()



# ambil percakapan terakhir
def get_history(limit=5):

    conn = connect()
    cursor = conn.cursor()


    cursor.execute("""
    SELECT user, ai
    FROM conversations
    ORDER BY id DESC
    LIMIT ?
    """,(limit,))


    data = cursor.fetchall()

    conn.close()

    return data[::-1]



# simpan preferensi
def remember(key,value):

    conn = connect()
    cursor = conn.cursor()


    cursor.execute("""
    INSERT INTO preferences(key,value)
    VALUES(?,?)
    ON CONFLICT(key)
    DO UPDATE SET value=excluded.value
    """,
    (key,value))


    conn.commit()
    conn.close()



# baca preferensi
def recall(key):

    conn = connect()
    cursor = conn.cursor()


    cursor.execute("""
    SELECT value
    FROM preferences
    WHERE key=?
    """,
    (key,))


    result = cursor.fetchone()

    conn.close()


    if result:
        return result[0]

    return None