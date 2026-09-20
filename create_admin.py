import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect("database.db")

username = "vincent"
plain_password = "brown112"

hashed_password = generate_password_hash(plain_password)

connection.execute("""
INSERT INTO admins (username, password)
VALUES (?, ?)
""", (username, hashed_password))

connection.commit()
connection.close()
print("Admin account created successfully.")