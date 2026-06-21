import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS images(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    filename TEXT,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS image_access(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id TEXT,
    otp TEXT,
    filename TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS history(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    filename TEXT,

    action TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS activity_logs(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    action TEXT,

    filename TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

)
""")

conn.commit()
conn.close()

print("Database Created Successfully")