import sqlite3

connection = sqlite3.connect('database.db')

sample_cars = [
    ('Toyota', 'Camry', 2020, 8400000, 'For Sale', 'Great condition, low mileage, first owner.'),
    ('Honda', 'Civic', 2019, 7500000, 'For Sale', 'Well-maintained, fuel-efficient, reliable.'),
    ('Ford', 'Mustang', 2021, 12000000, 'For Sale', 'Powerful engine, sleek design, excellent performance.'),
    ('Chevrolet', 'Impala', 2018, 6800000, 'For Sale', 'Spacious interior, smooth ride, great value.'),
    ('Nissan', 'Altima', 2020, 8000000, 'For Sale', 'Comfortable, stylish, advanced safety features.'),
    ('BMW', '3 Series', 2021, 15000000, 'For Sale', 'Luxury sedan, sporty handling, premium features.'),
    ('Mercedes-Benz', 'C-Class', 2019, 14000000, 'For Sale', 'Elegant design, high-quality interior, smooth performance.'),
    ('Audi', 'A4', 2020, 13000000, 'For Sale', 'Refined styling, advanced technology, excellent driving experience.'),
    ('Volkswagen', 'Passat', 2018, 7000000, 'For Sale', 'Reliable and practical sedan with a comfortable ride.'),
    ('Hyundai', 'Elantra', 2021, 7500000, 'For Sale', 'Affordable and efficient compact car with modern features.')
]

connection.executemany("""
INSERT INTO cars (make, model, year, price, listing_type, description)
VALUES (?, ?, ?, ?, ?, ?)
""", sample_cars)

connection.commit()
connection.close()

print("Sample data added successfully.")