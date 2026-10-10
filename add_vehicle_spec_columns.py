import sqlite3

connection = sqlite3.connect("database.db")

new_columns = [
    "condition TEXT",
    "transmission TEXT",
    "mileage TEXT",
    "fuel_type TEXT",
    "body_type TEXT",
    "drive_type TEXT",
    "engine TEXT",
    "exterior_color TEXT",
    "interior_color TEXT",
    "doors TEXT",
    "seats TEXT",
    "location TEXT",
    "features TEXT"
]

for column in new_columns:
    try:
        connection.execute(f"ALTER TABLE cars ADD COLUMN {column}")
    except sqlite3.OperationalError:
        pass  # column already exists, skip it

connection.commit()
connection.close()

print("Vehicle spec columns added successfully.")