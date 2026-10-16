from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_wtf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
login_attempts = {}

RECOVERY_KEY = os.environ.get("RECOVERY_KEY")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
csrf = CSRFProtect(app)

UPLOAD_FOLDER = "static/uploads"
SELL_UPLOAD_FOLDER = "static/sell-uploads"

DEALER_WHATSAPP_NUMBER = "2347066108664"
DEALER_PHONE_NUMBER = "+2347066108664"
DEALER_ADDRESS = "Owerri, Imo State, Nigeria"
DEALER_INSTAGRAM = "https://instagram.com/yourhandle"
DEALER_FACEBOOK = "https://facebook.com/yourhandle"
DEALER_TWITTER = "https://twitter.com/yourhandle"

def migrate_cars_table():
    connection = sqlite3.connect("database.db")

    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(cars)").fetchall()
    }

    new_columns = {
        "condition": "TEXT",
        "transmission": "TEXT",
        "mileage": "TEXT",
        "fuel_type": "TEXT",
        "body_type": "TEXT",
        "drive_type": "TEXT",
        "engine": "TEXT",
        "exterior_color": "TEXT",
        "interior_color": "TEXT",
        "doors": "TEXT",
        "seats": "TEXT",
        "vin": "TEXT",
        "location": "TEXT",
        "features": "TEXT"
    }

    for column_name, column_type in new_columns.items():

        if column_name not in existing_columns:

            connection.execute(
                f"ALTER TABLE cars ADD COLUMN {column_name} {column_type}"
            )

    connection.commit()
    connection.close()


migrate_cars_table()

def get_distinct_makes():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    makes = connection.execute(
        "SELECT DISTINCT make FROM cars WHERE sold = 0 ORDER BY make"
    ).fetchall()
    connection.close()
    return [m["make"] for m in makes]

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_new_leads_count():
    connection = sqlite3.connect("database.db")
    counts = {}
    for table in ["inquiries", "bookings", "swap_requests", "sell_requests"]:
        counts[table] = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE status = 'new' OR status IS NULL"
        ).fetchone()[0]
    connection.close()
    return counts

def get_dashboard_stats():
    connection = sqlite3.connect("database.db")
    stats = {}
    stats["total_cars"] = connection.execute("SELECT COUNT(*) FROM cars").fetchone()[0]
    stats["available_cars"] = connection.execute("SELECT COUNT(*) FROM cars WHERE sold = 0").fetchone()[0]
    stats["sold_cars"] = connection.execute("SELECT COUNT(*) FROM cars WHERE sold = 1").fetchone()[0]
    stats["pending_bookings"] = connection.execute(
        "SELECT COUNT(*) FROM bookings WHERE status = 'new' OR status IS NULL"
    ).fetchone()[0]
    stats["pending_inquiries"] = connection.execute(
        "SELECT COUNT(*) FROM inquiries WHERE status = 'new' OR status IS NULL"
    ).fetchone()[0]
    connection.close()
    return stats

def get_available_cars(listing_type=None, search=None, min_price=None, max_price=None, sort="newest"):
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    query = "SELECT * FROM cars WHERE 1=1"
    params = []

    if listing_type:
        query += " AND listing_type = ?"
        params.append(listing_type)
    if search:
        query += " AND (make LIKE ? OR model LIKE ? OR CAST(year AS TEXT) LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if min_price:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price:
        query += " AND price <= ?"
        params.append(max_price)

    query += " ORDER BY sold ASC, "
    if sort == "price_low":
        query += "price ASC"
    elif sort == "price_high":
        query += "price DESC"
    else:
        query += "id DESC"

    cars = connection.execute(query, params).fetchall()
    connection.close()
    return cars

def get_all_cars():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    cars = connection.execute("SELECT * FROM cars").fetchall()
    connection.close()
    return cars


def get_photos_for_car(car_id):
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    photos = connection.execute(
        "SELECT filename FROM car_photos WHERE car_id = ?", (car_id,)
    ).fetchall()
    connection.close()
    return [photo["filename"] for photo in photos]

@app.route("/")
def home():
    search = request.args.get("q")
    make = request.args.get("make")
    sort = request.args.get("sort", "newest")

    cars = get_available_cars(search=search, min_price=None, max_price=None, sort=sort)

    if make:
        cars = [c for c in cars if c["make"] == make]

    cars_with_photos = []
    for car in cars:
        photos = get_photos_for_car(car["id"])
        cars_with_photos.append({"car": car, "photos": photos})

    return render_template(
        "index.html",
        cars=cars_with_photos,
        makes=get_distinct_makes(),
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
        gallery_photos=get_gallery_photos()
    )

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    existing_admin = connection.execute("SELECT * FROM admins LIMIT 1").fetchone()
    connection.close()

    if not existing_admin:
        return redirect(url_for("admin_setup"))
    
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        record = login_attempts.get(username, {"count": 0, "locked_until": None})

        if record["locked_until"] and datetime.now() < record["locked_until"]:
            flash("Too many failed attempts. Please try again later.")
            return redirect(url_for("admin_login"))

        connection = sqlite3.connect("database.db")
        connection.row_factory = sqlite3.Row
        admin = connection.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
        connection.close()

        if admin and check_password_hash(admin["password"], password):
            login_attempts.pop(username, None)
            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]
            session["is_super_admin"] = bool(admin["is_super_admin"])
            return redirect(url_for("admin_dashboard"))
        else:
            record["count"] += 1
            if record["count"] >= MAX_LOGIN_ATTEMPTS:
                record["locked_until"] = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
                flash(f"Too many failed attempts. Locked for {LOCKOUT_MINUTES} minutes.")
            else:
                flash("Invalid username or password")
            login_attempts[username] = record
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")

@app.route("/admin/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form["username"]
        recovery_key = request.form["recovery_key"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        connection = sqlite3.connect("database.db")
        connection.row_factory = sqlite3.Row

        settings = connection.execute("SELECT * FROM settings WHERE id = 1").fetchone()

        if not settings or not check_password_hash(settings["recovery_key"], recovery_key):
            flash("Invalid recovery key")
            connection.close()
            return redirect(url_for("forgot_password"))

        if new_password != confirm_password:
            flash("Passwords do not match")
            connection.close()
            return redirect(url_for("forgot_password"))

        admin = connection.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()

        if not admin:
            flash("No admin account found with that username")
            connection.close()
            return redirect(url_for("forgot_password"))

        hashed_password = generate_password_hash(new_password)
        connection.execute(
            "UPDATE admins SET password = ? WHERE username = ?",
            (hashed_password, username)
        )
        connection.commit()
        connection.close()

        flash("Password reset successfully. You can now log in.")
        return redirect(url_for("admin_login"))

    return render_template("forgot_password.html")

@app.route("/admin/sell-requests")
def view_sell_requests():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    requests_list = connection.execute(
        "SELECT * FROM sell_requests ORDER BY created_at DESC"
    ).fetchall()

    requests_with_photos = []
    for r in requests_list:
        photos = connection.execute(
            "SELECT filename FROM sell_request_photos WHERE sell_request_id = ?", (r["id"],)
        ).fetchall()
        requests_with_photos.append({"request": r, "photos": [p["filename"] for p in photos]})

    connection.close()
    return render_template("sell_requests.html", requests=requests_with_photos)


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for("admin_login"))


@app.route("/admin/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        connection = sqlite3.connect("database.db")
        connection.row_factory = sqlite3.Row
        admin = connection.execute(
            "SELECT * FROM admins WHERE username = ?", (session["admin_username"],)
        ).fetchone()

        if not check_password_hash(admin["password"], current_password):
            flash("Current password is incorrect")
            connection.close()
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match")
            connection.close()
            return redirect(url_for("change_password"))

        new_hashed_password = generate_password_hash(new_password)
        connection.execute(
            "UPDATE admins SET password = ? WHERE username = ?",
            (new_hashed_password, session["admin_username"])
        )
        connection.commit()
        connection.close()

        flash("Password changed successfully")
        return redirect(url_for("admin_dashboard"))

    return render_template("change_password.html")

@app.route("/admin/swap-requests")
def view_swap_requests():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    requests_list = connection.execute(
        "SELECT * FROM swap_requests ORDER BY created_at DESC"
    ).fetchall()
    connection.close()

    return render_template("swap_requests.html", requests=requests_list)


@app.route("/admin/manage-admins", methods=["GET", "POST"])
def manage_admins():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    if not session.get("is_super_admin"):
        flash("Only the super admin can manage admin accounts")
        return redirect(url_for("admin_dashboard"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    if request.method == "POST":
        new_username = request.form["username"]
        new_password = request.form["password"]

        existing = connection.execute(
            "SELECT * FROM admins WHERE username = ?", (new_username,)
        ).fetchone()

        if existing:
            flash("That username is already taken")
            connection.close()
            return redirect(url_for("manage_admins"))

        hashed_password = generate_password_hash(new_password)
        connection.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            (new_username, hashed_password)
        )
        connection.commit()
        connection.close()

        flash("New admin account created")
        return redirect(url_for("manage_admins"))

    admins = connection.execute("SELECT id, username FROM admins").fetchall()
    connection.close()
    return render_template("manage_admins.html", admins=admins)


@app.route("/admin/delete-admin/<int:admin_id>", methods=["POST"])
def delete_admin(admin_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    if not session.get("is_super_admin"):
        flash("Only the super admin can manage admin accounts")
        return redirect(url_for("admin_dashboard"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    admin_to_delete = connection.execute(
        "SELECT * FROM admins WHERE id = ?", (admin_id,)
    ).fetchone()

    if admin_to_delete["username"] == session["admin_username"]:
        flash("You cannot delete your own account while logged in")
        connection.close()
        return redirect(url_for("manage_admins"))

    connection.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
    connection.commit()
    connection.close()

    flash("Admin account deleted")
    return redirect(url_for("manage_admins"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    cars = get_all_cars()

    cars_with_photos = []
    for car in cars:
        photos = get_photos_for_car(car["id"])
        cars_with_photos.append({"car": car, "photos": photos})

    return render_template("admin_dashboard.html", cars=cars_with_photos, leads=get_new_leads_count(), stats=get_dashboard_stats())

@app.route("/admin/add-car", methods=["GET", "POST"])
def add_car():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        make = request.form["make"]
        model = request.form["model"]
        year = request.form["year"]
        price = request.form["price"]
        listing_type = request.form["listing_type"]
        description = request.form["description"]

        condition = request.form.get("condition", "")
        transmission = request.form.get("transmission", "")
        mileage = request.form.get("mileage", "")
        fuel_type = request.form.get("fuel_type", "")
        body_type = request.form.get("body_type", "")
        drive_type = request.form.get("drive_type", "")
        engine = request.form.get("engine", "")
        exterior_color = request.form.get("exterior_color", "")
        interior_color = request.form.get("interior_color", "")
        doors = request.form.get("doors", "")
        seats = request.form.get("seats", "")
        location = request.form.get("location", "")
        features = request.form.get("features", "")

        connection = sqlite3.connect("database.db")
        cursor = connection.execute("""
            INSERT INTO cars (
                make, model, year, price, listing_type, description,
                condition, transmission, mileage, fuel_type, body_type,
                drive_type, engine, exterior_color, interior_color,
                doors, seats, location, features
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            make, model, year, price, listing_type, description,
            condition, transmission, mileage, fuel_type, body_type,
            drive_type, engine, exterior_color, interior_color,
            doors, seats, location, features
        ))

        new_car_id = cursor.lastrowid

        photo_files = request.files.getlist("photos")
        for photo_file in photo_files:
            if photo_file and photo_file.filename != "" and allowed_file(photo_file.filename):
                filename = secure_filename(photo_file.filename)
                unique_filename = f"{new_car_id}_{filename}"
                photo_file.save(os.path.join(UPLOAD_FOLDER, unique_filename))

                connection.execute("""
                    INSERT INTO car_photos (car_id, filename)
                    VALUES (?, ?)
                """, (new_car_id, unique_filename))

        connection.commit()
        connection.close()

        flash("Car added successfully")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_car.html")


@app.route("/admin/edit-car/<int:car_id>", methods=["GET", "POST"])
def edit_car(car_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    if request.method == "POST":

        # ============================================================
        # BASIC VEHICLE INFORMATION
        # ============================================================

        make = request.form["make"].strip()
        model = request.form["model"].strip()
        year = request.form["year"]
        price = request.form["price"]
        listing_type = request.form["listing_type"]
        description = request.form.get("description", "").strip()

        # ============================================================
        # VEHICLE SPECIFICATIONS
        # ============================================================

        condition = request.form.get("condition", "").strip()
        transmission = request.form.get("transmission", "").strip()
        mileage = request.form.get("mileage", "").strip()
        fuel_type = request.form.get("fuel_type", "").strip()
        body_type = request.form.get("body_type", "").strip()
        drive_type = request.form.get("drive_type", "").strip()
        engine = request.form.get("engine", "").strip()

        doors = request.form.get("doors", "").strip()
        seats = request.form.get("seats", "").strip()

        # ============================================================
        # APPEARANCE
        # ============================================================

        exterior_color = request.form.get("exterior_color", "").strip()
        interior_color = request.form.get("interior_color", "").strip()

        # ============================================================
        # ADDITIONAL INFORMATION
        # ============================================================

        vin = request.form.get("vin", "").strip()
        location = request.form.get("location", "").strip()
        features = request.form.get("features", "").strip()

        # ============================================================
        # UPDATE VEHICLE
        # ============================================================

        connection.execute("""
            UPDATE cars
            SET
                make = ?,
                model = ?,
                year = ?,
                price = ?,
                listing_type = ?,
                description = ?,
                condition = ?,
                transmission = ?,
                mileage = ?,
                fuel_type = ?,
                body_type = ?,
                drive_type = ?,
                engine = ?,
                exterior_color = ?,
                interior_color = ?,
                doors = ?,
                seats = ?,
                vin = ?,
                location = ?,
                features = ?
            WHERE id = ?
        """, (
            make,
            model,
            year,
            price,
            listing_type,
            description,
            condition,
            transmission,
            mileage,
            fuel_type,
            body_type,
            drive_type,
            engine,
            exterior_color,
            interior_color,
            doors,
            seats,
            vin,
            location,
            features,
            car_id
        ))

        # ============================================================
        # ADD NEW PHOTOS
        # ============================================================

        photo_files = request.files.getlist("photos")

        for photo_file in photo_files:

            if (
                photo_file
                and photo_file.filename != ""
                and allowed_file(photo_file.filename)
            ):

                filename = secure_filename(photo_file.filename)

                unique_filename = f"{car_id}_{filename}"

                photo_file.save(
                    os.path.join(UPLOAD_FOLDER, unique_filename)
                )

                connection.execute("""
                    INSERT INTO car_photos (car_id, filename)
                    VALUES (?, ?)
                """, (
                    car_id,
                    unique_filename
                ))

        connection.commit()
        connection.close()

        flash("Car updated successfully")

        return redirect(url_for("admin_dashboard"))

    # ================================================================
    # LOAD EXISTING CAR
    # ================================================================

    car = connection.execute("""
        SELECT *
        FROM cars
        WHERE id = ?
    """, (car_id,)).fetchone()

    if car is None:
        connection.close()
        flash("Car not found")
        return redirect(url_for("admin_dashboard"))

    photos = get_photos_for_car(car_id)

    connection.close()

    return render_template(
        "edit_car.html",
        car=car,
        photos=photos
    )

@app.route("/admin/delete-car/<int:car_id>", methods=["POST"])
def delete_car(car_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.execute("DELETE FROM cars WHERE id = ?", (car_id,))
    connection.commit()
    connection.close()

    flash("Car deleted successfully")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/mark-sold/<int:car_id>", methods=["POST"])
def mark_sold(car_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.execute("UPDATE cars SET sold = 1 WHERE id = ?", (car_id,))
    connection.commit()
    connection.close()

    flash("Car marked as sold")
    return redirect(url_for("admin_dashboard"))


@app.route("/car/<int:car_id>")
def car_detail(car_id):
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    connection.execute("UPDATE cars SET views = views + 1 WHERE id = ?", (car_id,))
    connection.commit()
    
    car = connection.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
    connection.close()

    if car is None:
        return "Car not found", 404

    photos = get_photos_for_car(car_id)
    return render_template(
        "car_detail.html",
        car=car,
        photos=photos,
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER
    )


@app.route("/car/<int:car_id>/inquire", methods=["POST"])
def submit_inquiry(car_id):
    name = request.form["name"]
    phone = request.form["phone"]
    message = request.form["message"]

    connection = sqlite3.connect("database.db")
    connection.execute("""
        INSERT INTO inquiries (car_id, name, phone, message)
        VALUES (?, ?, ?, ?)
    """, (car_id, name, phone, message))
    connection.commit()
    connection.close()

    flash("Thanks! We've received your inquiry and will contact you soon.")
    return redirect(url_for("car_detail", car_id=car_id))

@app.route("/admin/inquiries")
def view_inquiries():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    inquiries = connection.execute("""
        SELECT inquiries.*, cars.make, cars.model, cars.year
        FROM inquiries
        JOIN cars ON inquiries.car_id = cars.id
        ORDER BY inquiries.created_at DESC
    """).fetchall()
    connection.execute("UPDATE inquiries SET status = 'viewed' WHERE status = 'new' OR status IS NULL")
    connection.commit()
    connection.close()

    return render_template("inquiries.html", inquiries=inquiries)

@app.route("/car/<int:car_id>/book", methods=["POST"])
def submit_booking(car_id):
    name = request.form["name"]
    phone = request.form["phone"]
    booking_type = request.form["booking_type"]
    preferred_date = request.form["preferred_date"]
    notes = request.form["notes"]

    connection = sqlite3.connect("database.db")
    connection.execute("""
        INSERT INTO bookings (car_id, name, phone, booking_type, preferred_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (car_id, name, phone, booking_type, preferred_date, notes))
    connection.commit()
    connection.close()

    flash("Your booking request has been received. We'll contact you to confirm.")
    return redirect(url_for("car_detail", car_id=car_id))


@app.route("/admin/bookings")
def view_bookings():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    bookings = connection.execute("""
        SELECT bookings.*, cars.make, cars.model, cars.year
        FROM bookings
        JOIN cars ON bookings.car_id = cars.id
        ORDER BY bookings.preferred_date ASC
    """).fetchall()
    connection.close()

    return render_template("bookings.html", bookings=bookings)


def get_gallery_photos():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row
    covers = connection.execute(
        "SELECT car_photos.filename, car_photos.car_id, cars.make, cars.model, cars.year "
        "FROM car_photos JOIN cars ON car_photos.car_id = cars.id "
        "WHERE cars.sold = 0 AND car_photos.id = ("
        "SELECT MIN(cp2.id) FROM car_photos cp2 WHERE cp2.car_id = car_photos.car_id) "
        "ORDER BY car_photos.car_id DESC"
    ).fetchall()
    result = []
    for row in covers:
        item = dict(row)
        rows = connection.execute(
            "SELECT filename FROM car_photos WHERE car_id = ? ORDER BY id ASC",
            (row["car_id"],)
        ).fetchall()
        item["photos"] = [r["filename"] for r in rows]
        result.append(item)
    connection.close()
    return result

@app.route("/admin/setup", methods=["GET", "POST"])
def admin_setup():
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    existing_admin = connection.execute("SELECT * FROM admins LIMIT 1").fetchone()
    if existing_admin:
        connection.close()
        flash("Setup has already been completed.")
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        recovery_key = request.form["recovery_key"]
        confirm_recovery_key = request.form["confirm_recovery_key"]

        if password != confirm_password:
            flash("Passwords do not match")
            connection.close()
            return redirect(url_for("admin_setup"))

        if recovery_key != confirm_recovery_key:
            flash("Recovery keys do not match")
            connection.close()
            return redirect(url_for("admin_setup"))

        if len(recovery_key) < 8:
            flash("Recovery key must be at least 8 characters")
            connection.close()
            return redirect(url_for("admin_setup"))

        hashed_password = generate_password_hash(password)
        connection.execute(
            "INSERT INTO admins (username, password, is_super_admin) VALUES (?, ?, 1)",
            (username, hashed_password)
        )

        hashed_recovery_key = generate_password_hash(recovery_key)
        connection.execute(
            "INSERT INTO settings (id, recovery_key) VALUES (1, ?)",
            (hashed_recovery_key,)
        )

        connection.commit()
        connection.close()

        flash("Setup complete. You can now log in.")
        return redirect(url_for("admin_login"))

    connection.close()
    return render_template("admin_setup.html")

@app.route("/swap-car", methods=["GET", "POST"])
def swap_car():
    if request.method == "POST":
        connection = sqlite3.connect("database.db")
        connection.execute("""
            INSERT INTO swap_requests (
                first_name, last_name, phone, car_year, car_make, car_model,
                condition, mileage, vin, chassis_no, plate_number,
                particulars_name, purchased_from, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.form["first_name"],
            request.form["last_name"],
            request.form["phone"],
            request.form.get("car_year", ""),
            request.form.get("car_make", ""),
            request.form.get("car_model", ""),
            request.form.get("condition", ""),
            request.form.get("mileage", ""),
            request.form.get("vin", ""),
            request.form.get("chassis_no", ""),
            request.form.get("plate_number", ""),
            request.form.get("particulars_name", ""),
            request.form.get("purchased_from", ""),
            request.form.get("notes", "")
        ))
        connection.commit()
        connection.close()

        flash("Your swap request has been received. We'll review it and get back to you shortly.")
        return redirect(url_for("swap_car"))

    return render_template(
        "swap_car.html",
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER
    )

@app.route("/sell-car", methods=["GET", "POST"])
def sell_car():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        car_year = request.form.get("car_year", "")
        car_make = request.form.get("car_make", "")
        car_model = request.form.get("car_model", "")
        condition = request.form.get("condition", "")
        mileage = request.form.get("mileage", "")
        asking_price = request.form.get("asking_price", "")
        description = request.form.get("description", "")

        connection = sqlite3.connect("database.db")
        cursor = connection.execute("""
            INSERT INTO sell_requests (
                name, phone, car_year, car_make, car_model,
                condition, mileage, asking_price, description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, phone, car_year, car_make, car_model,
            condition, mileage, asking_price, description
        ))

        new_request_id = cursor.lastrowid

        photo_files = request.files.getlist("photos")
        for photo_file in photo_files:
            if photo_file and photo_file.filename != "" and allowed_file(photo_file.filename):
                filename = secure_filename(photo_file.filename)
                unique_filename = f"sell{new_request_id}_{filename}"
                photo_file.save(os.path.join(SELL_UPLOAD_FOLDER, unique_filename))

                connection.execute("""
                    INSERT INTO sell_request_photos (sell_request_id, filename)
                    VALUES (?, ?)
                """, (new_request_id, unique_filename))

        connection.commit()
        connection.close()

        flash("Thanks! Your car details have been submitted. We'll review and contact you soon.")
        return redirect(url_for("sell_car"))

    return render_template(
        "sell_car.html",
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS
    )

if __name__ == "__main__":
    app.run(debug=False)