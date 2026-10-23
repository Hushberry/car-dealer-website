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
    all_cars = get_available_cars(search=None, min_price=None, max_price=None, sort="newest")
    total = len(all_cars)
    featured = []
    for car in all_cars[:8]:
        featured.append({"car": car, "photos": get_photos_for_car(car["id"])})
    return render_template(
        "index.html",
        cars=featured,
        total_cars=total,
        makes=get_distinct_makes(),
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
        gallery_photos=_gallery_excl(locals().get("cars"))
    )


@app.route("/cars")
def cars_page():
    search = request.args.get("q")
    make = request.args.get("make")
    sort = request.args.get("sort", "newest")
    lt = (request.args.get("listing_type") or "").strip().lower()

    cars = get_available_cars(search=search, min_price=None, max_price=None, sort=sort)

    if make:
        cars = [c for c in cars if c["make"] == make]

    if lt and cars:
        try:
            if "listing_type" in cars[0].keys():
                chosen = [c for c in cars if str(c["listing_type"] or "").lower() == lt]
                if chosen:
                    cars = chosen
        except Exception:
            pass

    cars_with_photos = []
    for car in cars:
        cars_with_photos.append({"car": car, "photos": get_photos_for_car(car["id"])})

    return render_template(
        "cars.html",
        cars=cars_with_photos,
        total_cars=len(cars_with_photos),
        makes=get_distinct_makes(),
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
        gallery_photos=_gallery_excl(locals().get("cars"))
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


# ======================== AUCTIONS ========================
from flask import jsonify
AUCTION_MIN_INCREMENT = 50000


def _now_lagos():
    return datetime.utcnow() + timedelta(hours=1)


def _lagos_str(ts):
    try:
        return (datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") + timedelta(hours=1)).strftime("%d %b %Y, %H:%M")
    except Exception:
        return ts or ""


def ensure_auction_schema():
    conn = sqlite3.connect("database.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(cars)")]
    for name, ddl in (("auction_enabled", "INTEGER DEFAULT 0"), ("auction_start", "INTEGER"),
                      ("auction_end", "TEXT"), ("auction_closed", "INTEGER DEFAULT 0")):
        if name not in cols:
            conn.execute("ALTER TABLE cars ADD COLUMN %s %s" % (name, ddl))
    conn.execute("CREATE TABLE IF NOT EXISTS bids (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "car_id INTEGER NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL, "
                 "amount INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()


ensure_auction_schema()


def _auction_state(conn, car):
    if not car["auction_enabled"]:
        return {"enabled": False}
    top = conn.execute("SELECT MAX(amount) AS m, COUNT(*) AS c FROM bids WHERE car_id = ?", (car["id"],)).fetchone()
    start = car["auction_start"] or 0
    current = top["m"] or 0
    count = top["c"] or 0
    min_next = start if count == 0 else current + AUCTION_MIN_INCREMENT
    ended = bool(car["auction_closed"]) or bool(car["sold"])
    seconds_left = None
    if car["auction_end"]:
        try:
            end = datetime.strptime(car["auction_end"], "%Y-%m-%dT%H:%M")
            seconds_left = int((end - _now_lagos()).total_seconds())
            if seconds_left <= 0:
                seconds_left = 0
                ended = True
        except ValueError:
            pass
    return {"enabled": True, "ended": ended, "start": start, "current": current, "count": count,
            "min_next": min_next, "seconds_left": seconds_left, "increment": AUCTION_MIN_INCREMENT}


@app.route("/car/<int:car_id>/auction.json")
def auction_json(car_id):
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    car = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
    data = {"enabled": False} if car is None else _auction_state(conn, car)
    conn.close()
    return jsonify(data)


@app.route("/auctions.json")
def auctions_json():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    out = {}
    for car in conn.execute("SELECT * FROM cars WHERE auction_enabled = 1").fetchall():
        out[str(car["id"])] = _auction_state(conn, car)
    conn.close()
    return jsonify(out)


@app.route("/car/<int:car_id>/bid", methods=["POST"])
def place_bid(car_id):
    name = request.form.get("name", "").strip()[:60]
    phone = request.form.get("phone", "").strip()[:20]
    raw = request.form.get("amount", "").replace(",", "").replace("\u20a6", "").strip()
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    car = conn.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
    if car is None:
        conn.close()
        return "Car not found", 404
    back = redirect(url_for("car_detail", car_id=car_id) + "#auction")
    st = _auction_state(conn, car)
    if not st["enabled"] or st["ended"]:
        conn.close()
        flash("This auction is not open for bidding.")
        return back
    if len(name) < 2 or len(phone.replace(" ", "")) < 7:
        conn.close()
        flash("Please enter your name and a valid phone number.")
        return back
    try:
        amount = int(raw)
    except ValueError:
        conn.close()
        flash("Please enter your bid as a number.")
        return back
    if amount < st["min_next"] or amount > 10 ** 12:
        conn.close()
        flash("Your bid must be at least \u20a6{:,}.".format(st["min_next"]))
        return back
    conn.execute("INSERT INTO bids (car_id, name, phone, amount) VALUES (?, ?, ?, ?)", (car_id, name, phone, amount))
    conn.commit()
    conn.close()
    flash("Bid of \u20a6{:,} placed! The dealer will contact the highest bidder when the auction ends.".format(amount))
    return back


@app.route("/admin/auctions")
def admin_auctions():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    items = []
    for car in conn.execute("SELECT * FROM cars ORDER BY id DESC").fetchall():
        rows = conn.execute("SELECT * FROM bids WHERE car_id = ? ORDER BY amount DESC, id ASC", (car["id"],)).fetchall()
        bids = [{"name": b["name"], "phone": b["phone"], "amount": b["amount"], "when": _lagos_str(b["created_at"])} for b in rows]
        items.append({"car": car, "bids": bids, "state": _auction_state(conn, car)})
    conn.close()
    return render_template("admin_auctions.html", items=items, min_inc=AUCTION_MIN_INCREMENT)


@app.route("/admin/auction/<int:car_id>/save", methods=["POST"])
def admin_auction_save(car_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    enabled = 1 if request.form.get("enabled") else 0
    try:
        start = int(request.form.get("start", "0").replace(",", "").strip() or 0)
    except ValueError:
        start = 0
    end = request.form.get("end", "").strip()
    if end:
        try:
            datetime.strptime(end, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("That end date and time was not valid.")
            return redirect(url_for("admin_auctions"))
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE cars SET auction_enabled = ?, auction_start = ?, auction_end = ?, auction_closed = 0 WHERE id = ?",
                 (enabled, start, end or None, car_id))
    conn.commit()
    conn.close()
    flash("Auction settings saved.")
    return redirect(url_for("admin_auctions"))


@app.route("/admin/auction/<int:car_id>/close", methods=["POST"])
def admin_auction_close(car_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE cars SET auction_closed = 1 WHERE id = ?", (car_id,))
    conn.commit()
    conn.close()
    flash("Auction closed.")
    return redirect(url_for("admin_auctions"))
# ====================== END AUCTIONS ======================


# ======================== BRAND + ALERTS ========================
import re
import smtplib
import threading
from email.message import EmailMessage
from markupsafe import Markup

BRAND_NAME = os.getenv("BRAND_NAME", "PrimeDrive Motors").strip() or "PrimeDrive Motors"


@app.context_processor
def inject_brand():
    parts = BRAND_NAME.split(" ", 1)
    if len(parts) == 2:
        html = Markup("%s <em>%s</em>") % (parts[0], parts[1])
    else:
        html = Markup("%s") % parts[0]
    return {"brand_name": BRAND_NAME, "brand_html": html}


def _send_email(subject, body):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    pwd = os.getenv("SMTP_PASS", "")
    to = os.getenv("ALERT_EMAIL_TO", user)
    if not (user and pwd and to):
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.set_content(body)
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
    except Exception as e:
        print("alert email failed:", e)


_ALERT_LABELS = (("bid", "New bid"), ("inquir", "New inquiry"), ("book", "New booking"),
                 ("swap", "New swap request"), ("sell", "New sell request"))


@app.after_request
def lead_alerts(response):
    try:
        p = request.path.lower()
        if (request.method == "POST" and 300 <= response.status_code < 400
                and not p.startswith("/admin") and "login" not in p and "password" not in p):
            label = next((l for k, l in _ALERT_LABELS if k in p), "New form submission")
            lines = []
            for k, v in request.form.items():
                if k.lower() == "csrf_token" or "pass" in k.lower():
                    continue
                lines.append("%s: %s" % (k.replace("_", " ").title(), v))
            m = re.search(r"/car/(\d+)", p)
            if m:
                lines.append("Car page: " + request.url_root.rstrip("/") + "/car/" + m.group(1))
            body = "\n".join(lines) or "A visitor submitted a form."
            threading.Thread(target=_send_email, args=("%s - %s" % (label, BRAND_NAME), body), daemon=True).start()
    except Exception as e:
        print("lead alert error:", e)
    return response
# ====================== END BRAND + ALERTS ======================


# ======================== TESTIMONIALS ========================
from flask import jsonify


def ensure_testimonial_schema():
    conn = sqlite3.connect("database.db")
    conn.execute("CREATE TABLE IF NOT EXISTS testimonials (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "name TEXT NOT NULL, detail TEXT, rating INTEGER DEFAULT 5, quote TEXT NOT NULL, "
                 "visible INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()


ensure_testimonial_schema()


@app.route("/testimonials.json")
def testimonials_json():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT name, detail, rating, quote, photo, created_at AS date FROM testimonials WHERE visible = 1 ORDER BY id DESC LIMIT 12").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/admin/testimonials")
def admin_testimonials():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM testimonials ORDER BY COALESCE(pending, 0) DESC, id DESC").fetchall()
    conn.close()
    return render_template("admin_testimonials.html", rows=rows)


@app.route("/admin/testimonials/add", methods=["POST"])
def admin_testimonial_add():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    name = request.form.get("name", "").strip()[:60]
    detail = request.form.get("detail", "").strip()[:80]
    quote = request.form.get("quote", "").strip()[:600]
    try:
        rating = max(1, min(5, int(request.form.get("rating", "5"))))
    except ValueError:
        rating = 5
    visible = 1 if request.form.get("visible") else 0
    if len(name) < 2 or len(quote) < 10:
        flash("Please enter a name and a review of at least 10 characters.")
        return redirect(url_for("admin_testimonials"))
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO testimonials (name, detail, rating, quote, visible) VALUES (?, ?, ?, ?, ?)",
                 (name, detail, rating, quote, visible))
    conn.commit()
    conn.close()
    flash("Testimonial added.")
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/<int:tid>/toggle", methods=["POST"])
def admin_testimonial_toggle(tid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE testimonials SET visible = 1 - COALESCE(visible, 0), pending = 0 WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_testimonials"))


@app.route("/admin/testimonials/<int:tid>/delete", methods=["POST"])
def admin_testimonial_delete(tid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    _row = conn.execute("SELECT photo FROM testimonials WHERE id = ?", (tid,)).fetchone()
    if _row and _row[0]:
        try:
            import os as _os
            _os.remove(_os.path.join(app.root_path, "static", _row[0]))
        except Exception:
            pass
    conn.execute("DELETE FROM testimonials WHERE id = ?", (tid,))
    conn.commit()
    conn.close()
    flash("Testimonial deleted.")
    return redirect(url_for("admin_testimonials"))
# ====================== END TESTIMONIALS ======================


# ======================== PUBLIC TESTIMONIAL FORM ========================
def ensure_testimonial_pending():
    conn = sqlite3.connect("database.db")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(testimonials)")]
    if "pending" not in cols:
        conn.execute("ALTER TABLE testimonials ADD COLUMN pending INTEGER DEFAULT 0")
    if "photo" not in cols:
        conn.execute("ALTER TABLE testimonials ADD COLUMN photo TEXT")
    conn.commit()
    conn.close()


ensure_testimonial_pending()
_testi_hits = {}


@app.context_processor
def inject_pending_reviews():
    n = 0
    try:
        if request.path.startswith("/admin"):
            conn = sqlite3.connect("database.db")
            n = conn.execute("SELECT COUNT(*) FROM testimonials WHERE COALESCE(pending,0) = 1").fetchone()[0]
            conn.close()
    except Exception:
        n = 0
    return {"pending_reviews": n}


@app.route("/testimonials/submit", methods=["POST"])
def submit_testimonial():
    import os, uuid, io
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()
    now = datetime.utcnow()
    hits = [t for t in _testi_hits.get(ip, []) if (now - t).total_seconds() < 3600]
    if len(hits) >= 3:
        return jsonify(ok=False, msg="Too many submissions. Please try again later."), 429
    if request.form.get("website"):
        return jsonify(ok=True, msg="Thank you!")
    name = request.form.get("name", "").strip()[:60]
    detail = request.form.get("detail", "").strip()[:80]
    quote = request.form.get("quote", "").strip()[:600]
    try:
        rating = max(1, min(5, int(request.form.get("rating", "5"))))
    except ValueError:
        rating = 5
    if len(name) < 2 or len(quote) < 10:
        return jsonify(ok=False, msg="Please enter your name and a review of at least 10 characters."), 400

    photo_rel = None
    f = request.files.get("photo")
    if f and f.filename:
        raw = f.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            return jsonify(ok=False, msg="Photo is too large (max 5 MB)."), 400
        head = raw[:12]
        is_jpg = head[:3] == b"\xff\xd8\xff"
        is_png = head[:8] == b"\x89PNG\r\n\x1a\n"
        is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        if not (is_jpg or is_png or is_webp):
            return jsonify(ok=False, msg="Please upload a JPG, PNG or WEBP photo."), 400
        folder = os.path.join(app.root_path, "static", "uploads", "testimonials")
        os.makedirs(folder, exist_ok=True)
        fname = uuid.uuid4().hex + ".jpg"
        try:
            from PIL import Image, ImageOps
            im = Image.open(io.BytesIO(raw))
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((480, 480))
            im.save(os.path.join(folder, fname), "JPEG", quality=85)
        except ImportError:
            ext = ".png" if is_png else (".webp" if is_webp else ".jpg")
            fname = uuid.uuid4().hex + ext
            with open(os.path.join(folder, fname), "wb") as out:
                out.write(raw)
        except Exception:
            return jsonify(ok=False, msg="That photo could not be read. Please try another one."), 400
        photo_rel = "uploads/testimonials/" + fname

    auto = os.getenv("REVIEWS_AUTO_APPROVE", "0") == "1"
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO testimonials (name, detail, rating, quote, visible, pending, photo) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (name, detail, rating, quote, 1 if auto else 0, 0 if auto else 1, photo_rel))
    conn.commit()
    conn.close()
    hits.append(now)
    _testi_hits[ip] = hits
    body = "Name: %s\nCar: %s\nRating: %s/5\nPhoto: %s\n\n%s\n\nApprove it in Admin > Testimonials." % (name, detail or "-", rating, "yes" if photo_rel else "no", quote)
    threading.Thread(target=_send_email, args=("New testimonial to approve - %s" % BRAND_NAME, body), daemon=True).start()
    if auto:
        return jsonify(ok=True, live=True, msg="Thank you! Your review is now live.")
    return jsonify(ok=True, live=False, msg="Thank you! Your review will appear once the dealer approves it.")
# ====================== END PUBLIC TESTIMONIAL FORM ======================


# ======================== CONTACT PAGE ========================
def ensure_contact_schema():
    conn = sqlite3.connect("database.db")
    conn.execute("CREATE TABLE IF NOT EXISTS contact_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 "name TEXT NOT NULL, phone TEXT, email TEXT, interest TEXT, message TEXT NOT NULL, "
                 "handled INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()


ensure_contact_schema()
_contact_hits = {}


@app.context_processor
def inject_new_messages():
    n = 0
    try:
        if request.path.startswith("/admin"):
            conn = sqlite3.connect("database.db")
            n = conn.execute("SELECT COUNT(*) FROM contact_messages WHERE COALESCE(handled,0) = 0").fetchone()[0]
            conn.close()
    except Exception:
        n = 0
    return {"new_messages": n}


@app.route("/contact")
def contact_page():
    import os
    return render_template(
        "contact.html",
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
        contact_email=os.getenv("CONTACT_EMAIL", ""),
        showroom_hours=os.getenv("SHOWROOM_HOURS", "Mon \u2013 Sat: 9:00 AM \u2013 6:00 PM|Sunday: By appointment"),
    )


@app.route("/contact/send", methods=["POST"])
def contact_send():
    ip = (request.headers.get("X-Forwarded-For", request.remote_addr or "") or "").split(",")[0].strip()
    now = datetime.utcnow()
    hits = [t for t in _contact_hits.get(ip, []) if (now - t).total_seconds() < 3600]
    if len(hits) >= 5:
        return jsonify(ok=False, msg="Too many messages. Please try again later or reach us on WhatsApp."), 429
    if request.form.get("website"):
        return jsonify(ok=True, msg="Thank you!")
    name = request.form.get("name", "").strip()[:80]
    phone = request.form.get("phone", "").strip()[:40]
    email = request.form.get("email", "").strip()[:120]
    interest = request.form.get("interest", "").strip()[:40]
    message = request.form.get("message", "").strip()[:1500]
    if len(name) < 2 or len(message) < 5 or (len(phone) < 6 and "@" not in email):
        return jsonify(ok=False, msg="Please enter your name, a phone number or email, and your message."), 400
    conn = sqlite3.connect("database.db")
    conn.execute("INSERT INTO contact_messages (name, phone, email, interest, message) VALUES (?, ?, ?, ?, ?)",
                 (name, phone, email, interest, message))
    conn.commit()
    conn.close()
    hits.append(now)
    _contact_hits[ip] = hits
    body = "Name: %s\nPhone: %s\nEmail: %s\nInterested in: %s\n\n%s\n\nSee it in Admin > Messages." % (
        name, phone or "-", email or "-", interest or "-", message)
    threading.Thread(target=_send_email, args=("New website message - %s" % BRAND_NAME, body), daemon=True).start()
    return jsonify(ok=True, msg="Thank you. Your message has been sent and our team will be in touch shortly.")


@app.route("/admin/messages")
def admin_messages():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM contact_messages ORDER BY COALESCE(handled,0) ASC, id DESC").fetchall()
    conn.close()
    return render_template("admin_messages.html", rows=rows)


@app.route("/admin/messages/<int:mid>/done", methods=["POST"])
def admin_message_done(mid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.execute("UPDATE contact_messages SET handled = 1 - COALESCE(handled, 0) WHERE id = ?", (mid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_messages"))


@app.route("/admin/messages/<int:mid>/delete", methods=["POST"])
def admin_message_delete(mid):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect("database.db")
    conn.execute("DELETE FROM contact_messages WHERE id = ?", (mid,))
    conn.commit()
    conn.close()
    flash("Message deleted.")
    return redirect(url_for("admin_messages"))
# ====================== END CONTACT PAGE ======================


# ======================== SERVICES PAGE ========================
@app.route("/services")
def services_page():
    return render_template(
        "services.html",
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
    )
# ====================== END SERVICES PAGE ======================


# ======================== ABOUT PAGE ========================
@app.route("/about")
def about_page():
    return render_template(
        "about.html",
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
    )
# ====================== END ABOUT PAGE ======================


# ======================== TESTIMONIALS PAGE ========================
@app.route("/testimonials")
@app.route("/testimonials.html")
def testimonials_page():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, name, detail, rating, quote, photo, created_at FROM testimonials "
                        "WHERE visible = 1 AND COALESCE(pending, 0) = 0 ORDER BY id DESC").fetchall()
    conn.close()
    reviews = []
    for r in rows:
        d = dict(r)
        try:
            dt = datetime.strptime((d.get("created_at") or "")[:10], "%Y-%m-%d")
            d["date"] = "%d %s" % (dt.day, dt.strftime("%b %Y"))
        except Exception:
            d["date"] = ""
        try:
            d["rating"] = max(1, min(5, int(d.get("rating") or 5)))
        except Exception:
            d["rating"] = 5
        reviews.append(d)
    count = len(reviews)
    avg = round(sum(x["rating"] for x in reviews) / float(count), 1) if count else 0
    return render_template(
        "testimonials.html",
        reviews=reviews,
        review_count=count,
        review_avg=avg,
        whatsapp_number=DEALER_WHATSAPP_NUMBER,
        phone_number=DEALER_PHONE_NUMBER,
        dealer_address=DEALER_ADDRESS,
        instagram=DEALER_INSTAGRAM,
        facebook=DEALER_FACEBOOK,
        twitter=DEALER_TWITTER,
    )
# ====================== END TESTIMONIALS PAGE ======================


# ======================== SITE DETAILS (footer) ========================
@app.context_processor
def inject_site():
    import os
    from datetime import datetime as _dt

    def _u(env, fallback):
        v = os.getenv(env, "").strip()
        return v or (fallback or "")

    return {
        "site_whatsapp": DEALER_WHATSAPP_NUMBER or "",
        "site_phone": DEALER_PHONE_NUMBER or "",
        "site_address": DEALER_ADDRESS or "",
        "site_instagram": _u("INSTAGRAM_URL", DEALER_INSTAGRAM),
        "site_facebook": _u("FACEBOOK_URL", DEALER_FACEBOOK),
        "site_twitter": _u("TWITTER_URL", DEALER_TWITTER),
        "site_tiktok": os.getenv("TIKTOK_URL", "").strip(),
        "site_youtube": os.getenv("YOUTUBE_URL", "").strip(),
        "site_email": os.getenv("CONTACT_EMAIL", "").strip(),
        "site_hours": os.getenv("SHOWROOM_HOURS", "Mon \u2013 Sat: 9:00 AM \u2013 6:00 PM|Sunday: By appointment"),
        "current_year": _dt.utcnow().year,
    }
# ====================== END SITE DETAILS ======================


def _gallery_excl(featured):
    """gallery photos: cars NOT already featured in Latest Arrivals come first"""
    photos = get_gallery_photos()
    try:
        ids = set()
        for c in (featured or []):
            try:
                ids.add(c["id"])
            except Exception:
                ids.add(c[0])
        rest = [x for x in photos if x["car_id"] not in ids]
        shown = [x for x in photos if x["car_id"] in ids]
        return rest + shown
    except Exception:
        return photos


# ===== ADMIN LOGIN PROTECTION =====
import time as _lp_time

def _lp_db():
    return sqlite3.connect("database.db")

try:
    _c = _lp_db()
    _c.execute("CREATE TABLE IF NOT EXISTS login_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, ts INTEGER)")
    _c.commit(); _c.close()
except Exception:
    pass

def _lp_ip():
    xf = request.headers.get("X-Forwarded-For", "")
    return (xf.split(",")[0].strip() if xf else request.remote_addr) or "?"

def _lp_is_login():
    p = request.path.lower()
    return request.method == "POST" and "admin" in p and "login" in p

@app.before_request
def _lp_check():
    if not _lp_is_login():
        return None
    since = int(_lp_time.time()) - 15 * 60
    con = _lp_db()
    n = con.execute("SELECT COUNT(*) FROM login_attempts WHERE ip=? AND ts>?", (_lp_ip(), since)).fetchone()[0]
    con.close()
    if n >= 5:
        return ("Too many failed login attempts. Please wait 15 minutes and try again.", 429)
    return None

@app.after_request
def _lp_record(resp):
    try:
        if _lp_is_login():
            con = _lp_db()
            loc = (resp.headers.get("Location") or "").lower()
            redirected = resp.status_code in (301, 302, 303, 307, 308)
            failed = (resp.status_code == 200) or (redirected and "login" in loc)
            if failed:
                con.execute("INSERT INTO login_attempts (ip, ts) VALUES (?,?)", (_lp_ip(), int(_lp_time.time())))
            elif redirected:
                con.execute("DELETE FROM login_attempts WHERE ip=?", (_lp_ip(),))
            con.execute("DELETE FROM login_attempts WHERE ts<?", (int(_lp_time.time()) - 86400,))
            con.commit(); con.close()
    except Exception:
        pass
    return resp

if __name__ == "__main__":
    app.run(debug=False)