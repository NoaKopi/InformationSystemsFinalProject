from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
from contextlib import contextmanager
import sqlite3
import os
from decimal import Decimal
from utils.utils import *

app = Flask(__name__)
app.secret_key = "flytau_project_secret_key_2025!"
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=10),  # disconnects after 10 minutes of inactivity
    SESSION_FILE_DIR= "/home/NoaKopi/InformationSystemsFinalProject/flask_session_data",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# ======================================================
# MAIN
# ======================================================

# ======================================================
# DB CONNECTION + CONTEXT MANAGERS (SQLite)
# ======================================================

DB_PATH = os.path.join(app.instance_path, "FLYTAU15.db")


class DictCursor:
    """
    Wrap sqlite cursor so fetchone()/fetchall() return dicts.
    This keeps your existing code working (row.get(...), etc.)
    """
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=()):
        return self._cur.execute(sql, params)

    def executemany(self, sql, seq_of_params):
        return self._cur.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        return self._cur.close()


def get_db_connection():
    os.makedirs(app.instance_path, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_cursor(dictionary=True):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        raw_cursor = conn.cursor()
        cursor = DictCursor(raw_cursor) if dictionary else raw_cursor
        yield conn, cursor
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


@contextmanager
def db_transaction(dictionary=True):
    with db_cursor(dictionary=dictionary) as (conn, cursor):
        try:
            yield conn, cursor
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise


class BookingConflict(Exception):
    pass

# -----------------------------
# Errors
# -----------------------------
@app.errorhandler(404)
def invalid_route(e):
    return redirect("/")


# =============================
# HELPERS
# =============================
def is_registered_user():
    return session.get("user_type") == "registered_client" and session.get("Email_Address")


def is_admin_user():
    return session.get("user_type") == "admin" and session.get("worker_id")


def get_order_owner_email():
    """
    returns (user_is_reg, email)
    - registered client: session["Email_Address"]
    - guest: session["guest_email_address"]
    """
    if is_registered_user():
        return True, session.get("Email_Address")
    return False, session.get("guest_email_address")


def can_cancel(departure_date, departure_time):
    """Allowed only if flight departure is >= now + 36 hours."""
    if not departure_date or departure_time is None:
        return False

    d = str(departure_date).strip()
    t_raw = str(departure_time).strip()

    parts = t_raw.split(":")
    if len(parts) >= 3:
        fmt = "%Y-%m-%d %H:%M:%S"
        t = ":".join(parts[:3])
    else:
        fmt = "%Y-%m-%d %H:%M"
        t = ":".join(parts[:2])

    dep_dt = datetime.strptime(f"{d} {t}", fmt)
    return dep_dt >= (datetime.now() + timedelta(hours=36))


def normalize_time_to_hhmmss(value: str) -> str:
    """
    Normalize time string to 'HH:MM:SS'.
    Accepts 'HH:MM' or 'HH:MM:SS'.
    """
    s = (value or "").strip()
    if not s:
        return s

    parts = s.split(":")
    if len(parts) == 2:
        return f"{parts[0]}:{parts[1]}:00"
    if len(parts) >= 3:
        return f"{parts[0]}:{parts[1]}:{parts[2]}"
    return s


def plane_has_business(cursor, plane_id: int) -> bool:
    """
    Returns True iff the plane has at least one Business seat in Seats table.
    This is the ONLY definition for "large plane" / business availability.
    """
    cursor.execute(
        """
        SELECT 1
        FROM Seats
        WHERE Plane_ID = ?
          AND LOWER(Class) = 'business'
        LIMIT 1
        """,
        (int(plane_id),),
    )
    return cursor.fetchone() is not None


def next_order_id(cursor) -> int:
    cursor.execute("SELECT COALESCE(MAX(Unique_Order_ID), 9000) + 1 AS next_id FROM Orders")
    return int(cursor.fetchone()["next_id"])


def fetch_flight_prices(flight_id: int):
    with db_cursor() as (_, cursor):
        cursor.execute("""
            SELECT Economy_Price, Business_Price
            FROM Flight
            WHERE Flight_ID = ?
            LIMIT 1
        """, (flight_id,))
        row = cursor.fetchone()
        if not row:
            return {"Economy": 0.0, "Business": 0.0}
        return {
            "Economy": float(row["Economy_Price"]),
            "Business": float(row["Business_Price"]),
        }


def infer_order_ticket_class(unique_order_id: int):
    """Determines ticket class ("Economy" or "Business") based on occupied seats, default Economy."""
    with db_cursor() as (_, cursor):
        cursor.execute("""
            SELECT s.Class AS ticket_class
            FROM Selected_Seats ss
            JOIN Seats s
              ON s.Plane_ID = ss.Plane_ID
             AND s.Row_Num = ss.Row_Num
             AND s.Column_Number = ss.Column_Number
            WHERE ss.Unique_Order_ID = ?
              AND ss.Is_Occupied = 1
            LIMIT 1
        """, (unique_order_id,))
        row = cursor.fetchone()

    tc = (row["ticket_class"] if row and row.get("ticket_class") else "Economy")
    tc = str(tc).strip()
    return tc if tc in ("Economy", "Business") else "Economy"


def compute_order_original_total(unique_order_id: int, flight_id: int, qty: int):
    """Calculates original total price: qty * price of inferred class."""
    ticket_class = infer_order_ticket_class(unique_order_id)
    prices = fetch_flight_prices(flight_id)
    price = float(prices.get(ticket_class, 0.0))
    return round(int(qty) * price, 2)


def compute_display_total(order_status: str, original_total: float):
    """Full refund for system cancellations, 5% charge for customer cancellations, else original."""
    s = (order_status or "").strip().lower()
    if s == "systemcancellation":
        return 0.0
    if s == "customercancellation":
        return round(float(original_total) * 0.05, 2)
    return round(float(original_total), 2)


# =============================
# DB CHECK
# =============================
@app.before_request
def refresh_session_timeout():
    if session.get("user_type") in ("registered_client", "admin"):
        session.permanent = True


@app.route("/db-check")
def db_check():
    try:
        with db_cursor() as (_, cursor):
            # SQLite doesn't have DATABASE() / SHOW TABLES
            cursor.execute("PRAGMA database_list;")
            db_info = cursor.fetchone() or {}
            db = db_info.get("file") or "main"

            cursor.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name;
            """)
            tables = [row["name"] for row in cursor.fetchall()]

            cursor.execute("SELECT COUNT(*) AS cnt FROM Airports;")
            airports_cnt = cursor.fetchone()["cnt"]

        return {"ok": True, "database": db, "tables_count": len(tables), "airports_count": airports_cnt}

    except Exception as e:
        return {"ok": False, "error": str(e)}, 500


# =============================
# HOME
# =============================
@app.route('/')
def home_page():
    selected_origin = request.args.get("origin_id")
    selected_destination = request.args.get("destination_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    today = datetime.now().date().isoformat()

    airports = []
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Airport_ID, Airport_Name, City, Country
                FROM Airports
                ORDER BY Country, City, Airport_Name
            """)
            airports = cursor.fetchall()
    except Exception as e:
        flash(f"Database error loading airports: {e}", "error")

    return render_template(
        "home_page.html",
        airports=airports,
        selected_origin=selected_origin,
        selected_destination=selected_destination,
        start_date=start_date,
        end_date=end_date,
        today=today
    )


# =============================
# LOGIN (Client + Admin in one page)
# =============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    user_type = request.form.get("user_type", "client")  # client/admin
    password = request.form.get("Password", "")

    if not password:
        flash("Please enter password.", "error")
        return render_template("login.html")

    try:
        with db_cursor() as (_, cursor):

            # ------------------ ADMIN LOGIN ------------------
            if user_type == "admin":
                worker_id = request.form.get("Worker_ID", "").strip()

                if not worker_id:
                    flash("Please enter Worker ID.", "error")
                    return render_template("login.html", Worker_ID=worker_id, Email_Address="")

                cursor.execute("""
                    SELECT Worker_ID, Manager_Password, Manager_First_Name_In_English
                    FROM Managers
                    WHERE Worker_ID = ?
                """, (worker_id,))
                admin = cursor.fetchone()

                if not admin or admin.get("Manager_Password") != password:
                    flash("Invalid Worker ID or password.", "error")
                    return render_template("login.html", Worker_ID=worker_id, Email_Address="")

                session.clear()
                session.permanent = False
                session["user_type"] = "admin"
                session["worker_id"] = admin["Worker_ID"]
                session["admin_name"] = admin.get("Manager_First_Name_In_English", "Admin")
                return redirect(url_for("admin_dashboard"))

            # ------------------ CLIENT LOGIN ------------------
            email = request.form.get("Email_Address", "").strip()
            if not email:
                flash("Please enter Email Address.", "error")
                return render_template("login.html", Email_Address=email, Worker_ID="")

            cursor.execute("""
                SELECT Registered_Clients_Email_Address AS Email_Address,
                       Client_Password,
                       First_Name_In_English,
                       Last_Name_In_English
                FROM Registered_Clients
                WHERE Registered_Clients_Email_Address = ?
            """, (email,))
            client = cursor.fetchone()

            if not client or client.get("Client_Password") != password:
                flash("Invalid email or password.", "error")
                return render_template("login.html", Email_Address=email, Worker_ID="")

            session.clear()
            session["user_type"] = "registered_client"
            session["Email_Address"] = client["Email_Address"]
            session["First_Name_In_English"] = client.get("First_Name_In_English", "")
            session["Last_Name_In_English"] = client.get("Last_Name_In_English", "")
            session.permanent = True
            return redirect(url_for("client_home"))

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return render_template("login.html")


def client_required() -> bool:
    """True if a registered client is logged in."""
    return session.get("user_type") == "registered_client" and bool(session.get("Email_Address"))


def client_required_or_redirect():
    """Helper that flashes message and returns False if not a registered client."""
    if not client_required():
        flash("Access allowed to registered clients only.", "error")
        return False
    return True


@app.route("/client_home")
def client_home():
    if not client_required_or_redirect():
        return redirect(url_for("login"))

    return render_template(
        "client_home.html",
        first_name=session.get("First_Name_In_English", ""),
        last_name=session.get("Last_Name_In_English", ""),
        email=session.get("Email_Address", "")
    )


@app.route("/logout")
def logout():
    session.clear()
    resp = redirect(url_for("login"))
    resp.delete_cookie(app.config.get("SESSION_COOKIE_NAME", "session"))
    return resp

# =============================
# REGISTER
# =============================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", datetime=datetime)

    first_name = (request.form.get("first_name") or "").strip()
    last_name = (request.form.get("last_name") or "").strip()
    email = (request.form.get("email") or "").strip()
    passport_id = (request.form.get("passport_id") or "").strip()
    birth_date = (request.form.get("birth_date") or "").strip()
    password = (request.form.get("password") or "").strip()
    confirm_password = (request.form.get("confirm_password") or "").strip()

    if not all([first_name, last_name, email, passport_id, birth_date, password, confirm_password]):
        flash("Please fill in all fields.", "error")
        return render_template("register.html", datetime=datetime)

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("register.html", datetime=datetime)

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT 1
                FROM Registered_Clients
                WHERE Registered_Clients_Email_Address = ?
                LIMIT 1
            """, (email,))
            if cursor.fetchone():
                flash("This email is already registered. Please login.", "error")
                return render_template("register.html", datetime=datetime)

            cursor.execute("""
                SELECT 1
                FROM Registered_Clients
                WHERE Passport_ID = ?
                LIMIT 1
            """, (passport_id,))
            if cursor.fetchone():
                flash("This Passport ID is already registered.", "error")
                return render_template("register.html", datetime=datetime)

        with db_transaction() as (_, cursor):
            cursor.execute("""
                INSERT INTO Registered_Clients
                  (Passport_ID,
                   Registered_Clients_Email_Address,
                   First_Name_In_English,
                   Last_Name_In_English,
                   Date_Of_Birth,
                   Client_Password,
                   Registration_Date)
                VALUES
                  (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (passport_id, email, first_name, last_name, birth_date, password))

        flash("Account created successfully! Please login.", "success")
        return redirect(url_for("login"))

    except Exception as e:
        flash(f"Database error while creating account: {e}", "error")
        return render_template("register.html", datetime=datetime)


# =============================
# GUEST SEARCH
# =============================
@app.route("/guest/search")
def guest_search():
    return redirect(url_for("home_page"))

# =============================
# AVAILABLE FLIGHTS
# =============================
@app.route("/available-flights")
def available_flights():
    origin_id = (request.args.get("origin_id") or "").strip()
    destination_id = (request.args.get("destination_id") or "").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()

    if not origin_id and not destination_id and not start_date and not end_date:
        flash("Please search first.", "error")
        return redirect(url_for("home_page"))

    airports, flights = [], []
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Airport_ID, Airport_Name, City, Country
                FROM Airports
                ORDER BY Country, City, Airport_Name
            """)
            airports = cursor.fetchall() or []

            sql = """
                SELECT
                    f.Flight_ID,
                    f.Plane_ID,
                    f.Departure_Date,
                    f.Departure_Time,
                    f.Economy_Price,
                    f.Business_Price,
                    f.Flight_Status,

                    ao.Airport_Name AS origin_airport_name,
                    ao.City AS origin_city,
                    ao.Country AS origin_country,

                    ad.Airport_Name AS dest_airport_name,
                    ad.City AS dest_city,
                    ad.Country AS dest_country,

                    CASE WHEN EXISTS (
                        SELECT 1
                        FROM Seats s
                        WHERE s.Plane_ID = f.Plane_ID
                          AND LOWER(s.Class) = 'business'
                        LIMIT 1
                    ) THEN 1 ELSE 0 END AS has_business

                FROM Flight f
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE 1=1
            """
            params = []

            if not is_admin_user():
                sql += " AND f.Flight_Status = 'active'"

            if origin_id:
                sql += " AND f.Origin_Airport = ?"
                params.append(origin_id)

            if destination_id:
                sql += " AND f.Destination_Airport = ?"
                params.append(destination_id)

            if start_date and end_date:
                sql += " AND f.Departure_Date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                sql += " AND f.Departure_Date >= ?"
                params.append(start_date)
            elif end_date:
                sql += " AND f.Departure_Date <= ?"
                params.append(end_date)

            sql += " ORDER BY f.Departure_Date, f.Departure_Time"
            cursor.execute(sql, tuple(params))
            flights = cursor.fetchall() or []

            for f in flights:
                f["has_business"] = bool(f.get("has_business"))

    except Exception as e:
        flash(f"Database error loading flights: {e}", "error")
        flights = []

    return render_template(
        "available_flights.html",
        airports=airports,
        flights=flights,
        origin_id=origin_id,
        destination_id=destination_id,
        start_date=start_date,
        end_date=end_date
    )


# =============================
# BOOK FLIGHT
# =============================
@app.route("/book/<int:flight_id>", methods=["GET", "POST"])
def book_flight(flight_id):
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    f.Flight_ID, f.Departure_Date, f.Departure_Time,
                    f.Economy_Price, f.Business_Price,
                    f.Plane_ID, f.Flight_Status,
                    ao.Airport_Name AS origin_airport_name, ao.City AS origin_city, ao.Country AS origin_country,
                    ad.Airport_Name AS dest_airport_name, ad.City AS dest_city, ad.Country AS dest_country,
                    CASE WHEN EXISTS (
                        SELECT 1
                        FROM Seats s
                        WHERE s.Plane_ID = f.Plane_ID
                          AND LOWER(s.Class) = 'business'
                        LIMIT 1
                    ) THEN 1 ELSE 0 END AS has_business
                FROM Flight f
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE f.Flight_ID = ?
            """, (flight_id,))
            flight = cursor.fetchone()

        if not flight:
            flash("Flight not found.", "error")
            return redirect(url_for("home_page"))

        status = (flight.get("Flight_Status") or "").strip().lower()
        if status != "active":
            flash(f"Cannot book this flight (status: {status}).", "error")
            return redirect(url_for("available_flights"))

        has_business = bool(flight.get("has_business"))

        # class requested
        selected_class = (request.args.get("class") or request.form.get("class") or "Economy").strip()
        if selected_class not in ("Economy", "Business"):
            selected_class = "Economy"

        # if no business in plane -> force Economy
        if selected_class == "Business" and not has_business:
            flash("Business class is not available for this flight. Switched to Economy.", "error")
            selected_class = "Economy"

        unit_price = float(flight["Economy_Price"])
        if selected_class == "Business":
            unit_price = float(flight["Business_Price"])

        if request.method == "GET":
            return render_template(
                "book_flight.html",
                flight=flight,
                user_is_registered=is_registered_user(),
                selected_class=selected_class,
                unit_price=unit_price,
                has_business=has_business)

        quantity_str = (request.form.get("quantity") or "").strip()
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError()
        except Exception:
            flash("Please enter a valid quantity.", "error")
            return render_template(
                "book_flight.html",
                flight=flight,
                user_is_registered=is_registered_user(),
                selected_class=selected_class,
                unit_price=unit_price,
                has_business=has_business)

        draft = {
            "flight_id": int(flight_id),
            "plane_id": int(flight["Plane_ID"]),
            "quantity": int(quantity),
            "ticket_class": selected_class,
            "unit_price": unit_price,
            "created_at": datetime.now().isoformat()
        }

        if is_registered_user():
            draft["user_type"] = "registered_client"
            draft["email"] = session.get("Email_Address")
            draft["first_name"] = session.get("First_Name_In_English", "")
            draft["last_name"] = session.get("Last_Name_In_English", "")
        else:
            guest_email = (request.form.get("guest_email") or "").strip()
            guest_first = (request.form.get("guest_first_name") or "").strip()
            guest_last = (request.form.get("guest_last_name") or "").strip()

            if not guest_email or not guest_first or not guest_last:
                flash("Please fill guest details (email + first/last name).", "error")
                return render_template(
                    "book_flight.html",
                    flight=flight,
                    user_is_registered=False,
                    selected_class=selected_class,
                    unit_price=unit_price,
                    has_business=has_business)

            draft["user_type"] = "guest"
            draft["email"] = guest_email
            draft["first_name"] = guest_first
            draft["last_name"] = guest_last

        session["draft_order"] = draft
        session["draft_selected_seats"] = []
        return redirect(url_for("draft_select_seats"))

    except Exception as e:
        flash(f"Database error while loading booking page: {e}", "error")
        return redirect(url_for("available_flights"))


# =============================
# DRAFT: SELECT SEATS
# =============================
@app.route("/draft/select-seats", methods=["GET", "POST"])
def draft_select_seats():
    draft = session.get("draft_order")
    if not draft:
        flash("Please start a booking first.", "error")
        return redirect(url_for("home_page"))

    flight_id = int(draft["flight_id"])
    plane_id = int(draft["plane_id"])
    needed = int(draft["quantity"])

    ticket_class = (draft.get("ticket_class") or "Economy").strip()
    if ticket_class not in ("Economy", "Business"):
        ticket_class = "Economy"

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Row_Num, Column_Number, Class
                FROM Seats
                WHERE Plane_ID = ?
                  AND Class = ?
                ORDER BY Row_Num, Column_Number
            """, (plane_id, ticket_class))
            seats = cursor.fetchall()

            cursor.execute("""
                SELECT ss.Row_Num, ss.Column_Number
                FROM Selected_Seats ss
                JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
                WHERE o.Flight_ID = ?
                  AND ss.Plane_ID = ?
                  AND ss.Is_Occupied = 1
                  AND o.Order_Status = 'active'
            """, (flight_id, plane_id))
            occ_rows = cursor.fetchall()
            occupied = {f"{r['Row_Num']}{r['Column_Number']}" for r in occ_rows}

        selected_prev = set(session.get("draft_selected_seats", []))

        if request.method == "POST":
            selected = request.form.getlist("seat_choice")

            if len(selected) != needed:
                flash(f"Please select exactly {needed} seats.", "error")
                return render_template(
                    "draft_select_seats.html",
                    seats=seats,
                    occupied=occupied,
                    selected=selected_prev,
                    needed=needed)

            parsed = []
            for seat_id in selected:
                row_part = seat_id[:-1]
                col_part = seat_id[-1]
                try:
                    row_num = int(row_part)
                except Exception:
                    flash("Invalid seat selection.", "error")
                    return redirect(url_for("draft_select_seats"))
                parsed.append((row_num, col_part))

            # ---------------------------------------------------------
            # SQLite note:
            # SQLite does NOT support (Row_Num, Column_Number) IN ((?,?),(?,?)) reliably.
            # Minimal safe approach:
            # 1) fetch candidate seats by row/col sets
            # 2) validate exact set in Python + validate class
            # ---------------------------------------------------------
            rows_list = [r for (r, _) in parsed]
            cols_list = [c for (_, c) in parsed]

            if not rows_list or not cols_list:
                flash("Invalid seat selection.", "error")
                return redirect(url_for("draft_select_seats"))

            row_ph = ",".join(["?"] * len(rows_list))
            col_ph = ",".join(["?"] * len(cols_list))

            with db_cursor() as (_, cursor):
                cursor.execute(f"""
                    SELECT Row_Num, Column_Number, Class
                    FROM Seats
                    WHERE Plane_ID = ?
                      AND Row_Num IN ({row_ph})
                      AND Column_Number IN ({col_ph})
                """, (plane_id, *rows_list, *cols_list))
                rows = cursor.fetchall() or []

            # Validate exact seats exist
            db_set = {(int(r["Row_Num"]), str(r["Column_Number"])) for r in rows}
            wanted_set = {(int(r), str(c)) for (r, c) in parsed}
            if db_set != wanted_set:
                flash("One or more selected seats are invalid.", "error")
                return redirect(url_for("draft_select_seats"))

            # Validate class
            if any(r["Class"] != ticket_class for r in rows):
                flash(f"You can only select {ticket_class} seats for this ticket type.", "error")
                return redirect(url_for("draft_select_seats"))

            # Validate availability
            if any(s in occupied for s in selected):
                flash("One or more seats are no longer available. Please choose again.", "error")
                return redirect(url_for("draft_select_seats"))

            session["draft_selected_seats"] = selected
            return redirect(url_for("order_review"))

        return render_template(
            "draft_select_seats.html",
            seats=seats,
            occupied=occupied,
            selected=selected_prev,
            needed=needed)

    except Exception as e:
        flash(f"Database error while loading seats: {e}", "error")
        return redirect(url_for("home_page"))


# =============================
# DRAFT: REVIEW
# =============================
@app.route("/draft/review", methods=["GET"])
def order_review():
    draft = session.get("draft_order")
    seats = session.get("draft_selected_seats", [])

    if not draft:
        flash("Please start a booking first.", "error")
        return redirect(url_for("home_page"))

    needed = int(draft["quantity"])
    if not seats or len(seats) != needed:
        flash("Please select seats first.", "error")
        return redirect(url_for("draft_select_seats"))

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    f.Flight_ID, f.Departure_Date, f.Departure_Time,
                    f.Economy_Price, f.Business_Price AS Business_Price,
                    ao.Airport_Name AS origin_airport_name, ao.City AS origin_city, ao.Country AS origin_country,
                    ad.Airport_Name AS dest_airport_name, ad.City AS dest_city, ad.Country AS dest_country
                FROM Flight f
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE f.Flight_ID = ?
            """, (int(draft["flight_id"]),))
            flight = cursor.fetchone()
            if not flight:
                flash("Flight not found.", "error")
                return redirect(url_for("home_page"))

            total_price = 0.0
            for seat_id in seats:
                row_num = int(seat_id[:-1])
                col = seat_id[-1]
                cursor.execute("""
                    SELECT Class
                    FROM Seats
                    WHERE Plane_ID = ?
                      AND Row_Num = ?
                      AND Column_Number = ?
                """, (draft["plane_id"], row_num, col))
                srow = cursor.fetchone()
                seat_class = (srow["Class"] if srow else "Economy")

                total_price += float(flight["Business_Price"]) if seat_class == "Business" else float(flight["Economy_Price"])

        return render_template(
            "order_review.html",
            draft=draft,
            flight=flight,
            seats=seats,
            total_price=total_price)

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("home_page"))


# =============================
# DRAFT: CONFIRM
# =============================
@app.route("/draft/confirm", methods=["POST"])
def confirm_order():
    draft = session.get("draft_order")
    seats = session.get("draft_selected_seats", [])

    if not draft or not seats:
        flash("Missing booking data. Please start again.", "error")
        return redirect(url_for("home_page"))

    needed = int(draft["quantity"])
    if len(seats) != needed:
        flash("Seat selection is incomplete.", "error")
        return redirect(url_for("draft_select_seats"))

    flight_id = int(draft["flight_id"])
    plane_id = int(draft["plane_id"])
    email = (draft.get("email") or "").strip()
    user_type = (draft.get("user_type") or "").strip()

    if not email or user_type not in ("guest", "registered_client"):
        flash("Missing user data. Please start again.", "error")
        return redirect(url_for("home_page"))

    try:
        with db_transaction() as (_, cursor):

            # Re-check seats taken (transaction safety)
            for seat_id in seats:
                row_num = int(seat_id[:-1])
                col = seat_id[-1]

                cursor.execute("""
                    SELECT 1
                    FROM Selected_Seats ss
                    JOIN Orders o ON o.Unique_Order_ID = ss.Unique_Order_ID
                    WHERE o.Flight_ID = ?
                      AND ss.Plane_ID = ?
                      AND ss.Row_Num = ?
                      AND ss.Column_Number = ?
                      AND ss.Is_Occupied = 1
                      AND o.Order_Status = 'active'
                    LIMIT 1
                """, (flight_id, plane_id, row_num, col))

                if cursor.fetchone():
                    raise BookingConflict("One or more seats were taken while you were booking.")

            # Ensure guest exists
            if user_type == "guest":
                cursor.execute(
                    "SELECT Email_Address FROM Unidentified_Guests WHERE Email_Address = ?",
                    (email,))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO Unidentified_Guests (Email_Address, First_Name_In_English, Last_Name_In_English)
                        VALUES (?, ?, ?)
                    """, (email, draft.get("first_name", ""), draft.get("last_name", "")))

            # Fetch flight prices once
            cursor.execute("""
                SELECT Economy_Price, Business_Price
                FROM Flight
                WHERE Flight_ID = ?
                LIMIT 1
            """, (flight_id,))
            pr = cursor.fetchone()
            if not pr:
                raise Exception("Flight not found.")

            eco_price = float(pr["Economy_Price"])
            bus_price = float(pr["Business_Price"])

            # Compute Final_Total based on seat classes
            final_total = 0.0
            for seat_id in seats:
                row_num = int(seat_id[:-1])
                col = seat_id[-1]

                cursor.execute("""
                    SELECT Class
                    FROM Seats
                    WHERE Plane_ID = ?
                      AND Row_Num = ?
                      AND Column_Number = ?
                    LIMIT 1
                """, (plane_id, row_num, col))
                srow = cursor.fetchone()
                if not srow:
                    raise Exception(f"Seat {seat_id} does not exist in Seats table.")

                seat_class = (srow["Class"] or "Economy")
                if seat_class == "Business":
                    final_total += bus_price
                else:
                    final_total += eco_price

            final_total = round(final_total, 2)

            # Create new order id
            new_order_id = next_order_id(cursor)

            # Insert order WITH Final_Total
            if user_type == "registered_client":
                cursor.execute("""
                    INSERT INTO Orders
                      (Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address,
                       Order_Status, Final_Total)
                    VALUES
                      (?, ?, ?, NULL, 'active', ?)
                """, (new_order_id, flight_id, email, final_total))
            else:
                cursor.execute("""
                    INSERT INTO Orders
                      (Unique_Order_ID, Flight_ID, Registered_Clients_Email_Address, Unidentified_Guest_Email_Address,
                       Order_Status, Final_Total)
                    VALUES
                      (?, ?, NULL, ?, 'active', ?)
                """, (new_order_id, flight_id, email, final_total))

            # Insert Has_an_order
            cursor.execute("""
                INSERT INTO Has_an_order (Email_Address, Unique_Order_ID, Quantity_of_tickets)
                VALUES (?, ?, ?)
            """, (email, new_order_id, needed))

            # Insert Selected_Seats
            for seat_id in seats:
                row_num = int(seat_id[:-1])
                col = seat_id[-1]
                cursor.execute("""
                    INSERT INTO Selected_Seats (Plane_ID, Unique_Order_ID, Column_Number, Row_Num, Is_Occupied)
                    VALUES (?, ?, ?, ?, 1)
                """, (plane_id, new_order_id, col, row_num))

        if user_type == "guest":
            session["guest_unique_order_id"] = str(new_order_id)
            session["guest_email_address"] = email

        session.pop("draft_order", None)
        session.pop("draft_selected_seats", None)

        return redirect(url_for("order_confirmed", unique_order_id=new_order_id))

    except BookingConflict:
        flash("One or more seats were taken while you were booking. Please choose again.", "error")
        return redirect(url_for("draft_select_seats"))

    except Exception as e:
        flash(f"Database error while confirming order: {e}", "error")
        return redirect(url_for("order_review"))


# =============================
# ORDER DETAILS FETCHERS
# =============================
def fetch_order_details(unique_order_id: int, user_is_reg: bool, email: str):
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                  o.Unique_Order_ID,
                  o.Order_Status,
                  o.Flight_ID,
                  o.Registered_Clients_Email_Address,
                  o.Unidentified_Guest_Email_Address
                FROM Orders o
                WHERE o.Unique_Order_ID = ?
                LIMIT 1
            """, (unique_order_id,))
            o = cursor.fetchone()
            if not o:
                return None

            owner_email = o["Registered_Clients_Email_Address"] or o["Unidentified_Guest_Email_Address"]
            if not owner_email or owner_email.strip().lower() != (email or "").strip().lower():
                return None

            cursor.execute("""
                SELECT
                    f.Flight_ID,
                    f.Departure_Date,
                    f.Departure_Time,
                    ao.Airport_Name AS origin_airport_name,
                    ao.City AS origin_city,
                    ao.Country AS origin_country,
                    ad.Airport_Name AS dest_airport_name,
                    ad.City AS dest_city,
                    ad.Country AS dest_country
                FROM Flight f
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE f.Flight_ID = ?
                LIMIT 1
            """, (o["Flight_ID"],))
            f = cursor.fetchone()
            if not f:
                return None

            cursor.execute("""
                SELECT Quantity_of_tickets
                FROM Has_an_order
                WHERE Unique_Order_ID = ?
                  AND Email_Address = ?
                LIMIT 1
            """, (unique_order_id, email))
            q = cursor.fetchone()
            qty = int(q["Quantity_of_tickets"]) if q and q.get("Quantity_of_tickets") is not None else 0

            cursor.execute("""
                SELECT Row_Num, Column_Number
                FROM Selected_Seats
                WHERE Unique_Order_ID = ?
                  AND Is_Occupied = 1
                ORDER BY Row_Num, Column_Number
            """, (unique_order_id,))
            seats_rows = cursor.fetchall() or []
            seats = [f"{r['Row_Num']}{r['Column_Number']}" for r in seats_rows]

            return {
                "unique_order_id": int(o["Unique_Order_ID"]),
                "order_status": o["Order_Status"],
                "email_address": email,
                "flight_id": int(f["Flight_ID"]),
                "origin_airport_name": f["origin_airport_name"],
                "origin_city": f["origin_city"],
                "origin_country": f["origin_country"],
                "dest_airport_name": f["dest_airport_name"],
                "dest_city": f["dest_city"],
                "dest_country": f["dest_country"],
                "departure_date": f["Departure_Date"],
                "departure_time": f["Departure_Time"],
                "quantity_of_tickets": qty,
                "seats": seats
            }
    except Exception:
        return None

@app.route("/order/<int:unique_order_id>/confirmed")
def order_confirmed(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Order confirmed. Please use Order Management to look it up.", "info")
        return redirect(url_for("order_management", tab="future"))

    order = fetch_order_details(unique_order_id, user_is_reg=user_is_reg, email=email)
    if not order:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("order_management", tab="future"))

    return render_template("order_confirmed.html", order=order)


def _fetch_order_seats(cursor, unique_order_id: int):
    cursor.execute("""
        SELECT Row_Num, Column_Number
        FROM Selected_Seats
        WHERE Unique_Order_ID = ?
          AND Is_Occupied = 1
        ORDER BY Row_Num, Column_Number
    """, (unique_order_id,))
    rows = cursor.fetchall() or []
    return [f"{r['Row_Num']}{r['Column_Number']}" for r in rows]


def fetch_future_orders_registered(email: str):
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    o.Unique_Order_ID AS unique_order_id,
                    o.Order_Status    AS order_status,
                    o.Flight_ID       AS flight_id,

                    ao.Airport_Name AS origin_airport,
                    ad.Airport_Name AS destination_airport,

                    f.Departure_Date AS departure_date,
                    f.Departure_Time AS departure_time,

                    hao.Quantity_of_tickets AS quantity_of_tickets
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                LEFT JOIN Has_an_order hao
                  ON hao.Unique_Order_ID = o.Unique_Order_ID
                 AND hao.Email_Address = o.Registered_Clients_Email_Address
                WHERE o.Registered_Clients_Email_Address = ?
                  AND o.Order_Status = 'active'
                  AND f.Departure_Date >= DATE('now')
                ORDER BY f.Departure_Date, f.Departure_Time
            """, (email,))

            orders = cursor.fetchall() or []
            for o in orders:
                o["seats"] = _fetch_order_seats(cursor, int(o["unique_order_id"]))
                o["cancellable"] = can_cancel(o["departure_date"], o["departure_time"])
            return orders
    except Exception:
        return []


def fetch_future_orders_guest(unique_order_id: str, email: str):
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    o.Unique_Order_ID AS unique_order_id,
                    o.Order_Status    AS order_status,
                    o.Flight_ID       AS flight_id,

                    ao.Airport_Name AS origin_airport,
                    ad.Airport_Name AS destination_airport,

                    f.Departure_Date AS departure_date,
                    f.Departure_Time AS departure_time,

                    hao.Quantity_of_tickets AS quantity_of_tickets
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                LEFT JOIN Has_an_order hao
                  ON hao.Unique_Order_ID = o.Unique_Order_ID
                 AND hao.Email_Address = o.Unidentified_Guest_Email_Address
                WHERE o.Unique_Order_ID = ?
                  AND o.Unidentified_Guest_Email_Address = ?
                  AND o.Order_Status = 'active'
                  AND f.Departure_Date >= DATE('now')
                LIMIT 1
            """, (unique_order_id, email))

            row = cursor.fetchone()
            if not row:
                return []

            row["seats"] = _fetch_order_seats(cursor, int(row["unique_order_id"]))
            row["cancellable"] = can_cancel(row["departure_date"], row["departure_time"])
            return [row]
    except Exception:
        return []


def fetch_past_orders_registered(email: str):
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    o.Unique_Order_ID AS unique_order_id,
                    o.Order_Status    AS order_status,
                    o.Flight_ID       AS flight_id,

                    ao.Airport_Name AS origin_airport,
                    ad.Airport_Name AS destination_airport,

                    f.Departure_Date AS departure_date,
                    f.Departure_Time AS departure_time,

                    hao.Quantity_of_tickets AS quantity_of_tickets
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                LEFT JOIN Has_an_order hao
                  ON hao.Unique_Order_ID = o.Unique_Order_ID
                 AND hao.Email_Address = o.Registered_Clients_Email_Address
                WHERE o.Registered_Clients_Email_Address = ?
                  AND f.Departure_Date < DATE('now')
                ORDER BY f.Departure_Date DESC, f.Departure_Time DESC
            """, (email,))

            orders = cursor.fetchall() or []
            for o in orders:
                o["seats"] = _fetch_order_seats(cursor, int(o["unique_order_id"]))
                o["cancellable"] = False
            return orders
    except Exception:
        return []

# =============================
# ORDER MANAGEMENT
# =============================
@app.route("/order-management")
def order_management():
    tab = request.args.get("tab", "future")
    if tab not in ("future", "history"):
        tab = "future"

    user_is_reg = bool(is_registered_user())
    future_orders, past_orders = [], []

    # bring orders
    if tab == "future":
        if user_is_reg:
            email = session.get("Email_Address")
            future_orders = fetch_future_orders_registered(email)
        else:
            unique = session.get("guest_unique_order_id")
            gemail = session.get("guest_email_address")
            if unique and gemail:
                future_orders = fetch_future_orders_guest(unique, gemail)
    else:
        if user_is_reg:
            email = session.get("Email_Address")
            past_orders = fetch_past_orders_registered(email)

    # -----------------------------
    # Add final_total to each order
    # -----------------------------
    flight_prices_cache = {}   # flight_id -> {"Economy": x, "Business": y}
    order_class_cache = {}     # unique_order_id -> "Economy"/"Business"
    cancelled_orig_totals = session.get("cancelled_order_original_totals") or {}

    def _get_prices(flight_id: int):
        if flight_id not in flight_prices_cache:
            flight_prices_cache[flight_id] = fetch_flight_prices(flight_id)
        return flight_prices_cache[flight_id]

    def _get_class(unique_order_id: int):
        if unique_order_id not in order_class_cache:
            order_class_cache[unique_order_id] = infer_order_ticket_class(unique_order_id)
        return order_class_cache[unique_order_id]

    def _calc_original_total(order: dict) -> float:
        qty = order.get("quantity_of_tickets") or 0
        try:
            qty = int(qty)
        except Exception:
            qty = 0

        flight_id = int(order.get("flight_id"))
        unique_order_id = int(order.get("unique_order_id"))

        tc = _get_class(unique_order_id)
        prices = _get_prices(flight_id)
        price = float(prices.get(tc, 0.0))
        return round(qty * price, 2)

    def _attach_final_total(orders: list[dict]):
        for o in orders:
            status = (o.get("order_status") or "").strip().lower()
            if status == "systemcancellation":
                o["final_total"] = 0.0
                continue
            if status == "customercancellation":
                orig = cancelled_orig_totals.get(str(o.get("unique_order_id")))
                if orig is None:
                    try:
                        orig = _calc_original_total(o)
                    except Exception:
                        orig = 0.0
                o["final_total"] = round(float(orig) * 0.05, 2)
                continue
            try:
                o["final_total"] = _calc_original_total(o)
            except Exception:
                o["final_total"] = 0.0

    if tab == "future":
        _attach_final_total(future_orders)
    else:
        _attach_final_total(past_orders)

    return render_template(
        "order_management.html",
        active_tab=tab,
        user_is_registered=user_is_reg,
        future_orders=future_orders,
        past_orders=past_orders
    )

# =============================
# ORDER LOOKUP (GUEST)
# =============================
@app.route("/order-management/lookup", methods=["POST"])
def lookup_order():
    unique_order_id = (request.form.get("unique_order_id") or "").strip()
    email = (request.form.get("email_address") or "").strip()

    if not unique_order_id.isdigit() or not email:
        flash("Please enter a valid Order ID and Email Address.", "error")
        return redirect(url_for("order_management", tab="future"))

    session["guest_unique_order_id"] = unique_order_id
    session["guest_email_address"] = email
    return redirect(url_for("order_details", unique_order_id=int(unique_order_id)))

# =============================
# ORDER DETAILS (VIEW)
# =============================
@app.route("/order/<int:unique_order_id>", methods=["GET"])
def order_details(unique_order_id):
    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Please enter your Order ID and Email in Order Management.", "error")
        return redirect(url_for("order_management", tab="future"))
    order = fetch_order_details(unique_order_id, user_is_reg=user_is_reg, email=email)
    if not order:
        flash("Order not found or access denied.", "error")
        return redirect(url_for("order_management", tab="future"))
    return render_template("order_confirmed.html", order=order)

# =============================
# CANCEL ORDER
# =============================
@app.route("/order/cancel", methods=["POST"])
def cancel_order():
    unique_order_id = (request.form.get("unique_order_id") or "").strip()
    if not unique_order_id.isdigit():
        flash("Invalid Order ID.", "error")
        return redirect(url_for("order_management", tab="future"))

    unique_order_id = int(unique_order_id)

    user_is_reg, email = get_order_owner_email()
    if not email:
        flash("Please identify your order first (Order ID + Email).", "error")
        return redirect(url_for("order_management", tab="future"))

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT
                    o.Unique_Order_ID,
                    o.Order_Status,
                    o.Flight_ID,
                    o.Registered_Clients_Email_Address,
                    o.Unidentified_Guest_Email_Address,
                    o.Final_Total,
                    f.Departure_Date,
                    f.Departure_Time
                FROM Orders o
                JOIN Flight f ON f.Flight_ID = o.Flight_ID
                WHERE o.Unique_Order_ID = ?
                LIMIT 1
            """, (unique_order_id,))
            o = cursor.fetchone()

        if not o:
            flash("Order not found.", "error")
            return redirect(url_for("order_management", tab="future"))

        owner_email = o["Registered_Clients_Email_Address"] or o["Unidentified_Guest_Email_Address"]
        if (owner_email or "").strip().lower() != (email or "").strip().lower():
            flash("Access denied.", "error")
            return redirect(url_for("order_management", tab="future"))

        if (o["Order_Status"] or "").strip().lower() != "active":
            flash("Only active orders can be cancelled.", "error")
            return redirect(url_for("order_management", tab="future"))

        if not can_cancel(o["Departure_Date"], o["Departure_Time"]):
            flash("Cancellation not available (less than 36 hours before departure).", "error")
            return redirect(url_for("order_management", tab="future"))

        try:
            current_total = float(o["Final_Total"] or 0.0)
        except Exception:
            current_total = 0.0

        fee_total = round(current_total * 0.05, 2)

        with db_transaction() as (_, cursor):
            # SQLite: no FOR UPDATE. Transaction itself provides the needed safety in your single-app context.
            cursor.execute("""
                SELECT Unique_Order_ID, Order_Status, Final_Total
                FROM Orders
                WHERE Unique_Order_ID = ?
            """, (unique_order_id,))
            locked = cursor.fetchone()

            if not locked:
                flash("Order not found.", "error")
                return redirect(url_for("order_management", tab="future"))

            if (locked["Order_Status"] or "").strip().lower() != "active":
                flash("Only active orders can be cancelled.", "error")
                return redirect(url_for("order_management", tab="future"))

            cursor.execute("""
                UPDATE Orders
                SET Order_Status = 'customercancellation',
                    Final_Total = ?
                WHERE Unique_Order_ID = ?
            """, (fee_total, unique_order_id))

            cursor.execute("""
                UPDATE Selected_Seats
                SET Is_Occupied = 0
                WHERE Unique_Order_ID = ?
            """, (unique_order_id,))

        flash(
            f"Order {unique_order_id} cancelled. Cancellation fee charged: ${fee_total:.2f}",
            "success"
        )
        return redirect(url_for("order_management", tab="future"))

    except Exception as e:
        flash(f"Database error while cancelling order: {e}", "error")
        return redirect(url_for("order_management", tab="future"))

# ======================================================
# ===================== ADMIN PART ======================
# ======================================================

def admin_required() -> bool:
    return session.get("user_type") == "admin" and session.get("worker_id")


def admin_required_or_redirect():
    if not admin_required():
        flash("Admin access only.", "error")
        return False
    return True


@app.route("/admin/dashboard")
def admin_dashboard():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))
    return render_template("admin_dashboard.html")


@app.route("/admin/reports", methods=["GET"])
def admin_reports():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    avg_occupancy_percent = None
    revenue_rows = []
    worker_hours_rows = []
    cancel_rate_rows = []
    plane_month_rows = []

    try:
        with db_cursor() as (_, cursor):

            # Average occupancy of completed flights
            cursor.execute("""
                SELECT
                    ROUND(AVG(per_flight.occupied_seats * 1.0 / per_flight.total_seats) * 100, 2) AS avg_occupancy_percent
                FROM (
                    SELECT
                        f.Flight_ID,
                        COUNT(*) AS occupied_seats,
                        (
                            SELECT COUNT(*)
                            FROM Seats s
                            WHERE s.Plane_ID = f.Plane_ID
                        ) AS total_seats
                    FROM Flight f
                    JOIN Orders o
                        ON o.Flight_ID = f.Flight_ID
                    JOIN Selected_Seats ss
                        ON ss.Unique_Order_ID = o.Unique_Order_ID
                       AND ss.Is_Occupied = 1
                    WHERE f.Flight_Status = 'done'
                    GROUP BY f.Flight_ID, f.Plane_ID
                ) AS per_flight;
            """)
            row = cursor.fetchone()
            avg_occupancy_percent = row["avg_occupancy_percent"] if row else None

            # Revenue by manufacturer/size/class
            cursor.execute("""
                SELECT
                    pl.Plane_Size,
                    pl.Manufacturer,
                    s.Class,
                    SUM(
                        CASE
                            WHEN o.Order_Status IN ('active','done') THEN
                                CASE
                                    WHEN s.Class = 'Economy'  THEN f.Economy_Price
                                    WHEN s.Class = 'Business' THEN f.Business_Price
                                END
                            WHEN o.Order_Status = 'customercancellation' THEN
                                0.05 * CASE
                                    WHEN s.Class = 'Economy'  THEN f.Economy_Price
                                    WHEN s.Class = 'Business' THEN f.Business_Price
                                END
                            WHEN o.Order_Status = 'systemcancellation' THEN
                                0
                            ELSE 0
                        END
                    ) AS Revenue
                FROM Orders o
                JOIN Flight f
                  ON f.Flight_ID = o.Flight_ID
                JOIN Planes pl
                  ON pl.Plane_ID = f.Plane_ID
                JOIN Selected_Seats ss
                  ON ss.Unique_Order_ID = o.Unique_Order_ID
                JOIN Seats s
                  ON s.Plane_ID = ss.Plane_ID
                 AND s.Row_Num = ss.Row_Num
                 AND s.Column_Number = ss.Column_Number
                GROUP BY
                    pl.Plane_Size,
                    pl.Manufacturer,
                    s.Class
                ORDER BY
                    pl.Manufacturer, pl.Plane_Size, s.Class;
            """)
            revenue_rows = cursor.fetchall() or []

            # Workers accumulated flight hours (short vs long)
            # SQLite: TIME_TO_SEC replacement via strftime seconds delta
            cursor.execute("""
                SELECT
                    w.Worker_ID,
                    w.Employee_Type,
                    ROUND(SUM(
                        CASE
                            WHEN (strftime('%s','1970-01-01 ' || r.Duration) - strftime('%s','1970-01-01 00:00:00'))
                                 <= (6 * 3600)
                            THEN (strftime('%s','1970-01-01 ' || r.Duration) - strftime('%s','1970-01-01 00:00:00'))
                            ELSE 0
                        END
                    ) / 3600.0, 2) AS Short_Flight_Hours,
                    ROUND(SUM(
                        CASE
                            WHEN (strftime('%s','1970-01-01 ' || r.Duration) - strftime('%s','1970-01-01 00:00:00'))
                                 > (6 * 3600)
                            THEN (strftime('%s','1970-01-01 ' || r.Duration) - strftime('%s','1970-01-01 00:00:00'))
                            ELSE 0
                        END
                    ) / 3600.0, 2) AS Long_Flight_Hours
                FROM (
                    SELECT Worker_ID, 'Pilot' AS Employee_Type
                    FROM Pilots
                    UNION ALL
                    SELECT Worker_ID, 'Flight_Attendant' AS Employee_Type
                    FROM Flight_Attendants
                ) AS w

                LEFT JOIN Pilots_Scheduled_to_Flights psf
                  ON w.Employee_Type = 'Pilot'
                 AND psf.Worker_ID = w.Worker_ID

                LEFT JOIN Flight_Attendants_Assigned_To_Flights fa
                  ON w.Employee_Type = 'Flight_Attendant'
                 AND fa.Worker_ID = w.Worker_ID

                LEFT JOIN Flight f
                  ON f.Flight_ID = COALESCE(psf.Flight_ID, fa.Flight_ID)
                 AND f.Flight_Status = 'done'

                LEFT JOIN Routes r
                  ON r.Origin_Airport = f.Origin_Airport
                 AND r.Destination_Airport = f.Destination_Airport

                GROUP BY
                    w.Worker_ID,
                    w.Employee_Type
                ORDER BY
                    w.Worker_ID,
                    w.Employee_Type;
            """)
            worker_hours_rows = cursor.fetchall() or []

            # Customer cancellation rate by month
            cursor.execute("""
                SELECT
                    strftime('%m-%Y', Date_Of_Order) AS month_year,
                    ROUND(
                        100.0 * SUM(CASE WHEN Order_Status = 'customercancellation' THEN 1 ELSE 0 END) / COUNT(*),
                        2
                    ) AS customer_cancellation_rate_percent
                FROM Orders
                GROUP BY strftime('%Y-%m', Date_Of_Order)
                ORDER BY MIN(Date_Of_Order);
            """)
            cancel_rate_rows = cursor.fetchall() or []

            # Monthly activity per plane
            cursor.execute("""
                SELECT
                    f.Plane_ID,
                    strftime('%m-%Y', MIN(f.Departure_Date)) AS month_year,

                    SUM(CASE WHEN f.Flight_Status = 'done' THEN 1 ELSE 0 END) AS flights_performed,
                    SUM(CASE WHEN f.Flight_Status = 'cancelled' THEN 1 ELSE 0 END) AS flights_cancelled,

                    ROUND(100.0 * SUM(CASE WHEN f.Flight_Status = 'done' THEN 1 ELSE 0 END) / 30.0, 2) AS utilization_percent,

                    (
                        SELECT printf('%s-%s', f2.Origin_Airport, f2.Destination_Airport)
                        FROM Flight f2
                        WHERE f2.Plane_ID = f.Plane_ID
                          AND strftime('%Y-%m', f2.Departure_Date) = strftime('%Y-%m', MIN(f.Departure_Date))
                        GROUP BY f2.Origin_Airport, f2.Destination_Airport
                        ORDER BY COUNT(*) DESC, f2.Origin_Airport, f2.Destination_Airport
                        LIMIT 1
                    ) AS dominant_origin_destination

                FROM Flight f
                GROUP BY
                    f.Plane_ID,
                    strftime('%Y', f.Departure_Date),
                    strftime('%m', f.Departure_Date)
                ORDER BY
                    f.Plane_ID,
                    strftime('%Y', f.Departure_Date),
                    strftime('%m', f.Departure_Date);
            """)
            plane_month_rows = cursor.fetchall() or []

        return render_template(
            "admin_reports.html",
            avg_occupancy_percent=avg_occupancy_percent,
            revenue_rows=revenue_rows,
            worker_hours_rows=worker_hours_rows,
            cancel_rate_rows=cancel_rate_rows,
            plane_month_rows=plane_month_rows
        )

    except Exception as e:
        flash(f"Database error loading reports: {e}", "error")
        return redirect(url_for("admin_dashboard"))


# -----------------------------
# Admin - Flight Search Board
# -----------------------------
@app.route("/admin/flights", methods=["GET"])
def admin_flights():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    origin_id = (request.args.get("origin_id") or "").strip()
    destination_id = (request.args.get("destination_id") or "").strip()
    start_date = (request.args.get("start_date") or "").strip()
    end_date = (request.args.get("end_date") or "").strip()
    status = (request.args.get("status") or "").strip().lower()

    if status and status not in FLIGHT_STATUSES:
        status = ""

    airports, flights = [], []

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Airport_ID, Airport_Name, City, Country
                FROM Airports
                ORDER BY Country, City, Airport_Name
            """)
            airports = cursor.fetchall()

            sql = """
                SELECT
                    f.Flight_ID,
                    f.Plane_ID,
                    f.Departure_Date,
                    f.Departure_Time,
                    f.Economy_Price,
                    f.Business_Price,
                    f.Flight_Status,
                    ao.Airport_Name AS origin_airport_name,
                    ao.City AS origin_city,
                    ad.Airport_Name AS dest_airport_name,
                    ad.City AS dest_city
                FROM Flight f
                JOIN Airports ao ON ao.Airport_ID = f.Origin_Airport
                JOIN Airports ad ON ad.Airport_ID = f.Destination_Airport
                WHERE 1=1
            """
            params = []

            if origin_id:
                sql += " AND f.Origin_Airport = ?"
                params.append(origin_id)

            if destination_id:
                sql += " AND f.Destination_Airport = ?"
                params.append(destination_id)

            if start_date and end_date:
                sql += " AND f.Departure_Date BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                sql += " AND f.Departure_Date >= ?"
                params.append(start_date)
            elif end_date:
                sql += " AND f.Departure_Date <= ?"
                params.append(end_date)

            if status:
                sql += " AND LOWER(f.Flight_Status) = ?"
                params.append(status)

            sql += " ORDER BY f.Departure_Date DESC, f.Departure_Time DESC"

            cursor.execute(sql, tuple(params))
            flights = cursor.fetchall()

    except Exception as e:
        flash(f"Database error loading flights: {e}", "error")

    return render_template(
        "admin_flights.html",
        airports=airports,
        flights=flights,
        origin_id=origin_id,
        destination_id=destination_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )

# ======================================================
# Admin - Add Flight
# ======================================================
@app.route("/admin/flights/new", methods=["GET", "POST"])
def admin_new_flight_step1():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    airports = []

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Airport_ID, Airport_Name, City, Country
                FROM Airports
                ORDER BY Country, City, Airport_Name
            """)
            airports = cursor.fetchall()

            if request.method == "POST":
                origin_id = (request.form.get("origin_id") or "").strip()
                dest_id = (request.form.get("destination_id") or "").strip()
                dep_date = (request.form.get("departure_date") or "").strip()
                dep_time = (request.form.get("departure_time") or "").strip()

                if not all([origin_id, dest_id, dep_date, dep_time]):
                    flash("All fields are required.", "error")
                    return render_template("admin_new_flight_step1.html", airports=airports)

                if origin_id == dest_id:
                    flash("Origin and destination must be different.", "error")
                    return render_template("admin_new_flight_step1.html", airports=airports)

                duration = get_route_duration_minutes(cursor, origin_id, dest_id)
                if duration is None:
                    flash("Route duration not found for this origin/destination.", "error")
                    return render_template("admin_new_flight_step1.html", airports=airports)

                dep_dt = dt_from_date_time(dep_date, dep_time)
                end_dt = dep_dt + timedelta(minutes=int(duration))

                session["admin_new_flight"] = {
                    "origin_id": int(origin_id),
                    "dest_id": int(dest_id),
                    "dep_date": dep_date,
                    "dep_time": dep_time,
                    "duration": int(duration),
                    "is_long": is_long_flight(int(duration)),
                    "window_start": dep_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "window_end": end_dt.strftime("%Y-%m-%d %H:%M:%S")
                }
                return redirect(url_for("admin_new_flight_step2"))

        return render_template("admin_new_flight_step1.html", airports=airports)

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_dashboard"))

# =============================
# Admin - Add Flight (STEP 2)
# =============================
@app.route("/admin/flights/new/step2", methods=["GET", "POST"])
def admin_new_flight_step2():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    draft = session.get("admin_new_flight")
    if not draft:
        flash("Please start flight creation first.", "error")
        return redirect(url_for("admin_new_flight_step1"))

    try:
        with db_cursor() as (_, cursor):
            is_long = bool(draft["is_long"])
            window_start = draft["window_start"]
            window_end = draft["window_end"]

            # Planes + Staff availability
            planes = available_planes(cursor, window_start, window_end, is_long=is_long)
            pilots = available_pilots(cursor, window_start, window_end, require_long_qualified=is_long)
            attendants = available_attendants(cursor, window_start, window_end, require_long_qualified=is_long)

            if request.method == "POST":
                plane_id = (request.form.get("plane_id") or "").strip()
                economy_price = (request.form.get("economy_price") or "").strip()
                business_price = (request.form.get("business_price") or "").strip()
                selected_pilots = request.form.getlist("pilots")
                selected_att = request.form.getlist("attendants")

                if not plane_id or not economy_price:
                    flash("Plane and economy price are required.", "error")
                    return render_template(
                        "admin_new_flight_step2.html",
                        draft=draft, planes=planes, pilots=pilots, attendants=attendants
                    )

                # validate plane exists  (SQLite: ?)
                cursor.execute("SELECT Plane_ID FROM Planes WHERE Plane_ID = ?", (plane_id,))
                if not cursor.fetchone():
                    flash("Selected plane not found.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

                plane_id_int = int(plane_id)
                is_plane_large = plane_is_large(cursor, plane_id_int)  # by Seats table
                size_label = "large" if is_plane_large else "small"

                if is_long and not is_plane_large:
                    flash("Long flight requires a LARGE plane (Economy + Business seats).", "error")
                    return redirect(url_for("admin_new_flight_step2"))

                req_pilots = 3 if is_plane_large else 2
                req_att = 6 if is_plane_large else 3

                if len(selected_pilots) != req_pilots:
                    flash(f"Please select exactly {req_pilots} pilots.", "error")
                    return render_template(
                        "admin_new_flight_step2.html",
                        draft=draft, planes=planes, pilots=pilots, attendants=attendants
                    )

                if len(selected_att) != req_att:
                    flash(f"Please select exactly {req_att} attendants.", "error")
                    return render_template(
                        "admin_new_flight_step2.html",
                        draft=draft, planes=planes, pilots=pilots, attendants=attendants
                    )

                bp = None
                if is_plane_large:
                    if not business_price:
                        flash("Business price is required for LARGE planes (Business class exists).", "error")
                        return render_template(
                            "admin_new_flight_step2.html",
                            draft=draft, planes=planes, pilots=pilots, attendants=attendants
                        )
                    bp = float(business_price)

                # HARD re-check availability now (no SQL changes needed here, only placeholders inside utils if any)
                current_planes = available_planes(cursor, window_start, window_end, is_long=is_long)
                current_plane_ids = {int(p["Plane_ID"]) for p in current_planes}
                if plane_id_int not in current_plane_ids:
                    flash("Selected plane is no longer available in this time window.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

                current_pilots = {str(p["Worker_ID"]) for p in available_pilots(cursor, window_start, window_end, require_long_qualified=is_long)}
                if any(str(w) not in current_pilots for w in selected_pilots):
                    flash("One or more pilots are no longer available.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

                current_att = {str(a["Worker_ID"]) for a in available_attendants(cursor, window_start, window_end, require_long_qualified=is_long)}
                if any(str(w) not in current_att for w in selected_att):
                    flash("One or more attendants are no longer available.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

                draft.update({
                    "plane_id": plane_id_int,
                    "plane_size": size_label,
                    "economy_price": float(economy_price),
                    "business_price": bp,
                    "selected_pilots": [str(x) for x in selected_pilots],
                    "selected_attendants": [str(x) for x in selected_att],
                })
                session["admin_new_flight"] = draft
                return redirect(url_for("admin_new_flight_review"))

        return render_template(
            "admin_new_flight_step2.html",
            draft=draft, planes=planes, pilots=pilots, attendants=attendants
        )

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_new_flight_step1"))


# =============================
# Admin - Add Flight (REVIEW)
# =============================
@app.route("/admin/flights/new/review", methods=["GET", "POST"])
def admin_new_flight_review():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    draft = session.get("admin_new_flight")
    if not draft or "plane_id" not in draft:
        flash("Missing flight draft. Please start again.", "error")
        return redirect(url_for("admin_new_flight_step1"))

    try:
        # Keep the original datetimes for our own use if needed
        new_start = datetime.strptime(draft["window_start"], "%Y-%m-%d %H:%M:%S")
        new_end = datetime.strptime(draft["window_end"], "%Y-%m-%d %H:%M:%S")

        # pass WITHOUT seconds to overlap_* helpers
        window_start_nosec = draft["window_start"][:16]  # 'YYYY-MM-DD HH:MM'
        window_end_nosec = draft["window_end"][:16]      # 'YYYY-MM-DD HH:MM'

        if request.method == "GET":
            return render_template("admin_new_flight_review.html", draft=draft)

        # Normalize time for TIME column
        dep_time_sql = normalize_time_to_hhmmss(draft.get("dep_time"))

        # writes -> transaction
        with db_transaction() as (_, cursor):

            if overlap_exists_for_plane(cursor, int(draft["plane_id"]), window_start_nosec, window_end_nosec):
                flash("Selected plane is no longer available.", "error")
                return redirect(url_for("admin_new_flight_step2"))

            for wid in draft["selected_pilots"]:
                if overlap_exists_for_pilot(cursor, int(wid), window_start_nosec, window_end_nosec):
                    flash("One or more pilots are no longer available.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

            for wid in draft["selected_attendants"]:
                if overlap_exists_for_attendant(cursor, int(wid), window_start_nosec, window_end_nosec):
                    flash("One or more attendants are no longer available.", "error")
                    return redirect(url_for("admin_new_flight_step2"))

            flight_id = next_flight_id(cursor)

            business_price = draft.get("business_price")
            if business_price is None:
                business_price = 0.00

            # SQLite: ? placeholders
            cursor.execute("""
                INSERT INTO Flight
                  (Flight_ID, Plane_ID, Origin_Airport, Destination_Airport,
                   Departure_Time, Departure_Date,
                   Economy_Price, Business_Price, Flight_Status)
                VALUES
                  (?,?,?,?,?,?,?,?, 'active')
            """, (
                int(flight_id),
                int(draft["plane_id"]),
                int(draft["origin_id"]),
                int(draft["dest_id"]),
                dep_time_sql,          # always HH:MM:SS
                draft["dep_date"],
                float(draft["economy_price"]),
                float(business_price)
            ))

            for wid in draft["selected_pilots"]:
                cursor.execute("""
                    INSERT INTO Pilots_Scheduled_to_Flights (Worker_ID, Flight_ID)
                    VALUES (?,?)
                """, (int(wid), int(flight_id)))

            for wid in draft["selected_attendants"]:
                cursor.execute("""
                    INSERT INTO Flight_Attendants_Assigned_To_Flights (Worker_ID, Flight_ID)
                    VALUES (?,?)
                """, (int(wid), int(flight_id)))

        session.pop("admin_new_flight", None)
        flash("Flight created successfully.", "success")
        return redirect(url_for("admin_flights"))

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_new_flight_step1"))


# =============================
# Admin - Cancel Flight (pick)
# =============================
@app.route("/admin/flights/cancel", methods=["GET"], endpoint="admin_cancel_flight_pick")
def admin_cancel_flight_pick_view():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    flights = []
    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Flight_ID, Departure_Date, Departure_Time, Flight_Status
                FROM Flight
                WHERE Flight_Status IN ('active','full')
                ORDER BY Departure_Date, Departure_Time
            """)
            flights = cursor.fetchall() or []

        now_dt = datetime.now()
        for f in flights:
            f["can_cancel"] = can_cancel_flight_by_72h_rule(
                f["Departure_Date"], f["Departure_Time"], now_dt=now_dt
            )
        return render_template("admin_cancel_pick.html", flights=flights)

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_dashboard"))


# =============================
# Admin - Cancel Flight (confirm)
# =============================
@app.route("/admin/flights/<int:flight_id>/cancel", methods=["GET", "POST"], endpoint="admin_cancel_flight_confirm")
def admin_cancel_flight_confirm(flight_id):
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    try:
        with db_cursor() as (_, cursor):
            cursor.execute("""
                SELECT Flight_ID, Departure_Date, Departure_Time, Flight_Status
                FROM Flight
                WHERE Flight_ID = ?
            """, (flight_id,))
            flight = cursor.fetchone()

        if not flight:
            flash("Flight not found.", "error")
            return redirect(url_for("admin_cancel_flight_pick"))

        if not can_cancel_flight_by_72h_rule(flight["Departure_Date"], flight["Departure_Time"]):
            flash("Cancellation is not allowed פחות מ-72 שעות לפני הטיסה.", "error")
            return redirect(url_for("admin_cancel_flight_pick"))

        if request.method == "GET":
            return render_template("admin_cancel_confirm.html", flight=flight)

        # POST -> transaction
        with db_transaction() as (_, cursor):
            # SQLite: no FOR UPDATE
            cursor.execute("""
                SELECT Flight_ID, Departure_Date, Departure_Time, Flight_Status
                FROM Flight
                WHERE Flight_ID = ?
            """, (flight_id,))
            locked = cursor.fetchone()

            if not locked:
                flash("Flight not found.", "error")
                return redirect(url_for("admin_cancel_flight_pick"))

            if locked["Flight_Status"] not in ("active", "full"):
                flash("This flight cannot be cancelled (status is not active/full).", "error")
                return redirect(url_for("admin_cancel_flight_pick"))

            if not can_cancel_flight_by_72h_rule(locked["Departure_Date"], locked["Departure_Time"]):
                flash("Cancellation is not allowed less than 72 hours before the flight.", "error")
                return redirect(url_for("admin_cancel_flight_pick"))

            cursor.execute("""
                UPDATE Flight
                SET Flight_Status = 'cancelled'
                WHERE Flight_ID = ?
            """, (flight_id,))

            # SQLite: no FOR UPDATE
            cursor.execute("""
                SELECT Unique_Order_ID
                FROM Orders
                WHERE Flight_ID = ?
                  AND Order_Status = 'active'
            """, (flight_id,))
            rows = cursor.fetchall() or []
            active_order_ids = [int(r["Unique_Order_ID"]) for r in rows]

            cursor.execute("""
                UPDATE Orders
                SET Order_Status = 'systemcancellation',
                    Final_Total  = 0.00
                WHERE Flight_ID = ?
                  AND Order_Status = 'active'
            """, (flight_id,))

            if active_order_ids:
                placeholders = ",".join(["?"] * len(active_order_ids))
                cursor.execute(f"""
                    UPDATE Selected_Seats
                    SET Is_Occupied = 0
                    WHERE Unique_Order_ID IN ({placeholders})
                """, tuple(active_order_ids))

        flash("Flight cancelled successfully. Active orders were fully refunded (Final_Total set to 0).", "success")
        return redirect(url_for("admin_flights"))

    except Exception as e:
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin_cancel_flight_pick"))


# =============================
# Admin - Add Staff
# =============================
@app.route("/admin/staff/add", methods=["GET", "POST"], endpoint="admin_add_staff")
def admin_add_staff():
    if not admin_required_or_redirect():
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("admin_add_staff.html")

    staff_type = (request.form.get("staff_type") or "").strip().lower()
    if staff_type not in ("pilot", "attendant"):
        flash("Invalid staff type.", "error")
        return redirect(url_for("admin_add_staff"))

    try:
        worker_id = int(request.form.get("worker_id"))
        house_number = int(request.form.get("house_number"))
    except ValueError:
        flash("Worker ID and House Number must be numbers.", "error")
        return redirect(url_for("admin_add_staff"))

    city = request.form.get("city", "").strip()
    street = request.form.get("street", "").strip()
    first_he = request.form.get("first_he", "").strip()
    last_he = request.form.get("last_he", "").strip()
    phone = request.form.get("phone", "").strip()
    start_date = request.form.get("start_date")
    is_qualified = 1 if request.form.get("is_qualified") else 0

    if not all([city, street, first_he, last_he, phone, start_date]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("admin_add_staff"))

    try:
        with db_transaction() as (_, cursor):
            # SQLite: ? placeholders
            cursor.execute("SELECT 1 FROM Pilots WHERE Worker_ID = ? LIMIT 1", (worker_id,))
            if cursor.fetchone():
                flash("Worker ID already exists as Pilot.", "error")
                return redirect(url_for("admin_add_staff"))

            cursor.execute("SELECT 1 FROM Flight_Attendants WHERE Worker_ID = ? LIMIT 1", (worker_id,))
            if cursor.fetchone():
                flash("Worker ID already exists as Flight Attendant.", "error")
                return redirect(url_for("admin_add_staff"))

            cursor.execute("SELECT 1 FROM Managers WHERE Worker_ID = ? LIMIT 1", (worker_id,))
            if cursor.fetchone():
                flash("Worker ID already exists as Manager.", "error")
                return redirect(url_for("admin_add_staff"))

            if staff_type == "pilot":
                cursor.execute("""
                    INSERT INTO Pilots
                    (Worker_ID, City, Street, House_Number,
                     First_Name_In_Hebrew, Last_Name_In_Hebrew,
                     Worker_Phone_Number, Start_Date, Is_Qualified)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    worker_id, city, street, house_number,
                    first_he, last_he, phone, start_date, is_qualified
                ))
            else:
                cursor.execute("""
                    INSERT INTO Flight_Attendants
                    (Worker_ID, City, Street, House_Number,
                     First_Name_In_Hebrew, Last_Name_In_Hebrew,
                     Worker_Phone_Number, Start_Date, Is_Qualified)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    worker_id, city, street, house_number,
                    first_he, last_he, phone, start_date, is_qualified
                ))

        flash("Staff member added successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    except Exception as e:
        flash(f"Database error while adding staff: {e}", "error")
        return redirect(url_for("admin_add_staff"))

# ======================================================
# Entry point
# ======================================================

