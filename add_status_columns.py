import sqlite3

connection = sqlite3.connect("database.db")

for table in ["inquiries", "bookings", "swap_requests", "sell_requests"]:
    try:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN status TEXT DEFAULT 'new'")
        print(f"Added status to {table}")
    except sqlite3.OperationalError as e:
        print(f"{table}:", e)

connection.commit()
connection.close()