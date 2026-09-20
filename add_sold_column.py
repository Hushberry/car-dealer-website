import sqlite3

connection = sqlite3.connect("database.db")
connection.execute("ALTER TABLE cars ADD COLUMN sold INTEGER NOT NULL DEFAULT 0")
connection.commit()
connection.close()

print("Sold column added successfully.")