import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

try:
    cursor.execute(
        """
        ALTER TABLE users
        ADD COLUMN role TEXT DEFAULT 'user'
        """
    )

    print("Role column added successfully")

except Exception as e:
    print(e)

conn.commit()
conn.close()