import sqlite3

connection = sqlite3.connect("database.db")
connection.execute("ALTER TABLE admins ADD COLUMN is_super_admin INTEGER NOT NULL DEFAULT 0")
connection.commit()
connection.close()

print("is_super_admin column added successfully.")