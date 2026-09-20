import sqlite3

connection = sqlite3.connect("database.db")
connection.execute(
    "UPDATE admins SET is_super_admin = 1 WHERE username = ?", ("vincent",)
)
connection.commit()
connection.close()

print("Super admin set successfully.")