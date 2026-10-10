import sqlite3

connection = sqlite3.connect("database.db")

# ============================================================
# CARS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    price INTEGER NOT NULL,
    listing_type TEXT NOT NULL,
    description TEXT,
    sold INTEGER NOT NULL DEFAULT 0,
    views INTEGER NOT NULL DEFAULT 0,
    condition TEXT,
    transmission TEXT,
    mileage TEXT,
    fuel_type TEXT,
    body_type TEXT,
    drive_type TEXT,
    engine TEXT,
    exterior_color TEXT,
    interior_color TEXT,
    doors TEXT,
    seats TEXT,
    vin TEXT,
    location TEXT,
    features TEXT
)
""")

# ============================================================
# CAR PHOTOS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS car_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    FOREIGN KEY (car_id) REFERENCES cars (id)
)
""")

# ============================================================
# ADMINS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_super_admin INTEGER NOT NULL DEFAULT 0
)
""")

# ============================================================
# SETTINGS (recovery key, set during one-time admin setup)
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    recovery_key TEXT NOT NULL
)
""")

# ============================================================
# INQUIRIES
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (car_id) REFERENCES cars (id)
)
""")

# ============================================================
# BOOKINGS (test drive / inspection)
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    booking_type TEXT NOT NULL,
    preferred_date TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (car_id) REFERENCES cars (id)
)
""")

# ============================================================
# SWAP REQUESTS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS swap_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    car_year TEXT,
    car_make TEXT,
    car_model TEXT,
    condition TEXT,
    mileage TEXT,
    vin TEXT,
    chassis_no TEXT,
    plate_number TEXT,
    particulars_name TEXT,
    purchased_from TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# ============================================================
# SELL REQUESTS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS sell_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    car_year TEXT,
    car_make TEXT,
    car_model TEXT,
    condition TEXT,
    mileage TEXT,
    asking_price TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# ============================================================
# SELL REQUEST PHOTOS
# ============================================================
connection.execute("""
CREATE TABLE IF NOT EXISTS sell_request_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sell_request_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    FOREIGN KEY (sell_request_id) REFERENCES sell_requests (id)
)
""")

connection.commit()
connection.close()

print("Database and all tables created successfully.")