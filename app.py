from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
import os

load_dotenv()

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
login_attempts = {}

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = os.environ.get("SECRET_KEY")

UPLOAD_FOLDER = "static/uploads"
DEALER_WHATSAPP_NUMBER = "2347066108664"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_available_cars(listing_type=None, make=None, min_price=None, max_price=None):
    connection = sqlite3.connect("database.db")
    connection.row_factory = sqlite3.Row

    query = "SELECT * FROM cars WHERE sold = 0"
    params = []

    if listing_type:
        query += " AND listing_type = ?"
        params.append(listing_type)
    if make:
        query += " AND make LIKE ?"
        params.append(f"%{make}%")
    if min_price:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price:
        query += " AND price <= ?"
        params.append(max_price)

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
    listing_type = request.args.get("listing_type")
    make = request.args.get("make")
    min_price = request.args.get("min_price")
    max_price = request.args.get("max_price")

    cars = get_available_cars(listing_type, make, min_price, max_price)

    cars_with_photos = []
    for car in cars:
        photos = get_photos_for_car(car["id"])
        cars_with_photos.append({"car": car, "photos": photos})

    return render_template("index.html", cars=cars_with_photos)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
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

    return render_template("admin_dashboard.html", cars=cars_with_photos)


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

        connection = sqlite3.connect("database.db")
        cursor = connection.execute("""
            INSERT INTO cars (make, model, year, price, listing_type, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (make, model, year, price, listing_type, description))

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
        make = request.form["make"]
        model = request.form["model"]
        year = request.form["year"]
        price = request.form["price"]
        listing_type = request.form["listing_type"]
        description = request.form["description"]

        connection.execute("""
            UPDATE cars
            SET make = ?, model = ?, year = ?, price = ?, listing_type = ?, description = ?
            WHERE id = ?
        """, (make, model, year, price, listing_type, description, car_id))

        photo_files = request.files.getlist("photos")
        for photo_file in photo_files:
            if photo_file and photo_file.filename != "" and allowed_file(photo_file.filename):
                filename = secure_filename(photo_file.filename)
                unique_filename = f"{car_id}_{filename}"
                photo_file.save(os.path.join(UPLOAD_FOLDER, unique_filename))

                connection.execute("""
                    INSERT INTO car_photos (car_id, filename)
                    VALUES (?, ?)
                """, (car_id, unique_filename))

        connection.commit()
        connection.close()

        flash("Car updated successfully")
        return redirect(url_for("admin_dashboard"))

    car = connection.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
    photos = get_photos_for_car(car_id)
    connection.close()
    return render_template("edit_car.html", car=car, photos=photos)


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
    car = connection.execute("SELECT * FROM cars WHERE id = ?", (car_id,)).fetchone()
    connection.close()

    if car is None:
        return "Car not found", 404

    photos = get_photos_for_car(car_id)
    return render_template("car_detail.html", car=car, photos=photos, whatsapp_number=DEALER_WHATSAPP_NUMBER)


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
    

if __name__ == "__main__":
    app.run(debug=True)