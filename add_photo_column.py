import sqlite3

connection = sqlite3.connect("database.db")
connection.execute("ALTER TABLE cars ADD COLUMN photo TEXT")
connection.commit()
connection.close()

print("Photo clumn added successfully.")