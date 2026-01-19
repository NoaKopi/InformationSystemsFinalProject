from datetime import datetime, timedelta, date, time
from abc import ABC, abstractmethod

# =============================
# Statuses (SYNC with DB)
# =============================
FLIGHT_STATUSES = {"active", "cancelled", "done", "full"}
ORDER_STATUSES = {"active", "done", "systemcancellation", "customercancellation"}


# =============================
# Users
# =============================
class Unidentified_Guests:
    """Represents an unidentified (non-registered) guest user in the system."""
    def __init__(self, email_address, first_name_in_english, last_name_in_english, phone_numbers=None):
        self.email_address = email_address
        self.first_name_in_english = first_name_in_english
        self.last_name_in_english = last_name_in_english
        self.phone_numbers = phone_numbers if phone_numbers is not None else []


class RegisteredClient(Unidentified_Guests):
    def __init__(
        self,
        email_address,
        first_name_in_english,
        last_name_in_english,
        passport_id,
        birth_date,
        password,
        phone_numbers=None,
    ):
        super().__init__(email_address, first_name_in_english, last_name_in_english, phone_numbers)
        self.passport_id = passport_id
        self.birth_date = birth_date
        self.password = password
        self.registration_date = datetime.now()


# =============================
# Workers
# =============================
class Workers(ABC):
    def __init__(
        self,
        worker_id,
        first_name_in_hebrew,
        last_name_in_hebrew,
        phone_number,
        address_city,
        address_street,
        address_number,
        start_date,
    ):
        self.worker_id = worker_id
        self.first_name_in_hebrew = first_name_in_hebrew
        self.last_name_in_hebrew = last_name_in_hebrew
        self.phone_number = phone_number
        self.address_city = address_city
        self.address_street = address_street
        self.address_number = address_number
        self.start_date = start_date

    def __str__(self):
        return f"{self.first_name_in_hebrew} {self.last_name_in_hebrew} ({self.worker_id})"


class Managers(Workers):
    def __init__(
        self,
        worker_id,
        first_name_in_hebrew,
        last_name_in_hebrew,
        phone_number,
        address_city,
        address_street,
        address_number,
        start_date,
        first_name_in_english,
        last_name_in_english,
        password,
    ):
        super().__init__(
            worker_id,
            first_name_in_hebrew,
            last_name_in_hebrew,
            phone_number,
            address_city,
            address_street,
            address_number,
            start_date,
        )
        self.first_name_in_english = first_name_in_english
        self.last_name_in_english = last_name_in_english
        self.password = password

    def __str__(self):
        return f"Manager: {self.first_name_in_english} {self.last_name_in_english} (ID: {self.worker_id})"


class Pilots(Workers):
    def __init__(
        self,
        worker_id,
        first_name_in_hebrew,
        last_name_in_hebrew,
        phone_number,
        address_city,
        address_street,
        address_number,
        start_date,
        is_long_flight_qualified,
    ):
        super().__init__(
            worker_id,
            first_name_in_hebrew,
            last_name_in_hebrew,
            phone_number,
            address_city,
            address_street,
            address_number,
            start_date,
        )
        self.is_long_flight_qualified = bool(is_long_flight_qualified)


class FlightAttendants(Workers):
    def __init__(
        self,
        worker_id,
        first_name_in_hebrew,
        last_name_in_hebrew,
        phone_number,
        address_city,
        address_street,
        address_number,
        start_date,
        is_long_flight_qualified,
    ):
        super().__init__(
            worker_id,
            first_name_in_hebrew,
            last_name_in_hebrew,
            phone_number,
            address_city,
            address_street,
            address_number,
            start_date,
        )
        self.is_long_flight_qualified = bool(is_long_flight_qualified)



# =============================
# Seats
# =============================
class Seat(ABC):
    def __init__(self, row_number, column_number):
        self.row_number = int(row_number)
        self.column_number = str(column_number)

    @abstractmethod
    def get_price(self, flight):
        raise NotImplementedError

    @property
    @abstractmethod
    def seat_type(self):
        raise NotImplementedError

    def __str__(self):
        return f"Row {self.row_number}, Col {self.column_number} ({self.seat_type})"

    def __repr__(self):
        return f"{self.seat_type}Seat({self.row_number}, {self.column_number})"

    def __eq__(self, other):
        return (
            isinstance(other, Seat)
            and self.row_number == other.row_number
            and self.column_number == other.column_number
            and self.seat_type == other.seat_type
        )

    def __hash__(self):
        return hash((self.row_number, self.column_number, self.seat_type))


class EconomySeat(Seat):
    def get_price(self, flight):
        return flight.economy_price

    @property
    def seat_type(self):
        return "Economy"


class BusinessSeat(Seat):
    def get_price(self, flight):
        return flight.business_price

    @property
    def seat_type(self):
        return "Business"


# =============================
# Plane
# =============================
class Plane:
    def __init__(self, plane_id, manufacturer, plane_size, purchase_date, seats):
        self.plane_id = plane_id
        self.manufacturer = manufacturer
        self.plane_size = plane_size
        self.purchase_date = purchase_date

        if not seats or len(seats) == 0:
            raise ValueError("A plane cannot be created without seats.")
        self.seats = seats

    def can_fly_long(self):
        return str(self.plane_size).lower() == "large"

    def __str__(self):
        return f"Plane {self.plane_id}: {self.manufacturer} ({len(self.seats)} seats)"


# =============================
# Flight
# =============================
class Flight:
    """Represents a flight in the system."""

    def __init__(
        self,
        flight_id,
        plane_id,
        origin,
        destination,
        departure_time,
        departure_date,
        duration_minutes,
        economy_price,
        business_price,
        status="active",
    ):
        status = (status or "").strip().lower()
        if status not in FLIGHT_STATUSES:
            raise ValueError(f"Invalid flight status: {status}")

        self.status = status
        self.flight_id = flight_id
        self.plane_id = plane_id
        self.origin = origin
        self.destination = destination
        self.departure_time = departure_time
        self.departure_date = departure_date
        self.duration_minutes = int(duration_minutes)
        self.economy_price = economy_price
        self.business_price = business_price

        self._occupied_seats = set()

    def is_seat_available(self, seat):
        return seat not in self._occupied_seats

    def book_seats(self, seats_to_book):
        if self.status in {"cancelled", "done"}:
            raise ValueError(f"Cannot book seats: flight {self.flight_id} status is '{self.status}'.")

        for seat in seats_to_book:
            if seat in self._occupied_seats:
                raise ValueError(f"Error: Seat {seat} is already occupied on flight {self.flight_id}.")

        for seat in seats_to_book:
            self._occupied_seats.add(seat)

    def release_seats(self, seats_to_release):
        for seat in seats_to_release:
            if seat in self._occupied_seats:
                self._occupied_seats.remove(seat)

    def get_departure_datetime(self):
        return datetime.combine(self.departure_date, self.departure_time)

    def get_arrival_datetime(self):
        duration = timedelta(minutes=self.duration_minutes)
        return self.get_departure_datetime() + duration

    def is_short_flight(self):
        return self.duration_minutes <= 360

    def set_full_if_needed(self, is_full: bool):
        if self.status in {"cancelled", "done"}:
            return
        self.status = "full" if is_full else "active"


# =============================
# Order
# =============================
class Order:
    def __init__(self, order_code, flight, customer, seats, status="active"):
        self.order_code = order_code
        self.flight = flight
        self.customer = customer
        self.seats = seats

        status = (status or "").strip().lower()
        if status not in ORDER_STATUSES:
            raise ValueError(f"Invalid order status: {status}")
        self.status = status

        self.created_at = datetime.now()
        self.total_price = self.calculate_total_price()

        try:
            self.flight.book_seats(self.seats)
        except Exception:
            pass

    def calculate_total_price(self):
        total = 0
        for seat in self.seats:
            total += seat.get_price(self.flight)
        return total

    def mark_done(self):
        self.status = "done"

    def cancel_order(self, cancel_reason="customercancellation"):
        cancel_reason = (cancel_reason or "").strip().lower()

        if cancel_reason not in {"customercancellation", "systemcancellation"}:
            raise ValueError("Invalid cancellation type")

        if self.status in {"done", "customercancellation", "systemcancellation"}:
            return

        self.status = cancel_reason

        try:
            self.flight.release_seats(self.seats)
        except Exception:
            pass

        if cancel_reason == "customercancellation":
            self.total_price *= 0.95
        else:
            self.total_price = 0


# ======================================================
# ================= Admin / DB Helpers ==================
# ======================================================

def dt_from_date_time(d, t):
    """
    Robust conversion of date+time into datetime.
    Supports:
    - d: date OR 'YYYY-MM-DD'
    - t: time OR timedelta OR 'HH:MM' OR 'HH:MM:SS' OR 'HH:MM:SS.ffffff'
    """
    # ---- date ----
    if isinstance(d, date) and not isinstance(d, datetime):
        d_str = d.strftime("%Y-%m-%d")
    else:
        d_str = str(d).strip()

    # ---- time ----
    if isinstance(t, timedelta):
        total_seconds = int(t.total_seconds())
        hh = total_seconds // 3600
        mm = (total_seconds % 3600) // 60
        ss = total_seconds % 60
        t_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
    elif isinstance(t, time):
        t_str = t.strftime("%H:%M:%S")
    else:
        t_str = str(t).strip()

    # normalize time string:
    # - cut microseconds if exist
    if "." in t_str:
        t_str = t_str.split(".")[0]

    # - if it's HH:MM -> make it HH:MM:SS
    if len(t_str) == 5 and t_str.count(":") == 1:
        t_str = t_str + ":00"

    # - if it's longer than HH:MM:SS (rare) trim to 8
    if len(t_str) > 8:
        t_str = t_str[:8]

    # now ALWAYS parse with seconds
    return datetime.strptime(f"{d_str} {t_str}", "%Y-%m-%d %H:%M:%S")

def hours_until_departure(departure_date, departure_time, now_dt=None) -> float:
    """
    Returns hours until departure.
    departure_date: date or 'YYYY-MM-DD'
    departure_time: time or 'HH:MM'/'HH:MM:SS'
    """
    if now_dt is None:
        now_dt = datetime.now()

    dep_dt = dt_from_date_time(departure_date, departure_time)
    delta = dep_dt - now_dt
    return delta.total_seconds() / 3600.0


def can_cancel_flight_by_72h_rule(departure_date, departure_time, now_dt=None) -> bool:
    """
    Business rule:
    Admin cannot cancel if less than 72 hours remain before departure.
    Allowed only if departure is at least 72h away.
    """
    return hours_until_departure(departure_date, departure_time, now_dt=now_dt) >= 72.0


def get_route_duration_minutes(cursor, origin_id, dest_id):
    cursor.execute(
        """
        SELECT Duration
        FROM Routes
        WHERE Origin_Airport = %s AND Destination_Airport = %s
        """,
        (origin_id, dest_id),
    )
    row = cursor.fetchone()
    if not row:
        return None

    dur = row["Duration"]

    # MySQL TIME can come as timedelta, or string "HH:MM:SS"
    if isinstance(dur, timedelta):
        return int(dur.total_seconds() // 60)

    dur_str = str(dur)
    parts = dur_str.split(":")
    if len(parts) >= 2:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) >= 3 else 0
        return h * 60 + m + (1 if s >= 30 else 0)

    return None


def is_long_flight(duration_minutes: int) -> bool:
    # לפי הדרישה שלך נשאר כמו שהיה (אפשר לשנות אם יש כלל אחר)
    return int(duration_minutes) > 360


def next_flight_id(cursor, base=1000) -> int:
    cursor.execute("SELECT COALESCE(MAX(Flight_ID), %s) + 1 AS next_id FROM Flight", (base,))
    return int(cursor.fetchone()["next_id"])


# -----------------------------
# Plane size by YOUR definition:
# Large = has Business seats
# Small = Economy only
# -----------------------------

def plane_is_large(cursor, plane_id: int) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM Seats
        WHERE Plane_ID = %s
          AND LOWER(Class) = 'business'
        LIMIT 1
        """,
        (plane_id,),
    )
    return cursor.fetchone() is not None


def plane_size_label(cursor, plane_id: int) -> str:
    return "large" if plane_is_large(cursor, plane_id) else "small"


# -----------------------------
# Availability (NO overlaps)
# Uses NOT EXISTS in SQL (stable)
# window_start_str/window_end_str are "YYYY-mm-dd HH:MM:SS"
# -----------------------------

def available_planes(cursor, window_start_str: str, window_end_str: str, is_long: bool):
    """
    Returns planes that are free in the time window.
    If is_long=True -> only LARGE planes (has Business seats)
    If is_long=False -> small + large allowed
    """
    cursor.execute(
        """
        SELECT p.Plane_ID, p.Plane_Size
        FROM Planes p
        WHERE
          (%s = 0 OR EXISTS (
              SELECT 1
              FROM Seats s
              WHERE s.Plane_ID = p.Plane_ID
                AND LOWER(s.Class) = 'business'
              LIMIT 1
          ))
          AND NOT EXISTS (
            SELECT 1
            FROM Flight f
            JOIN Routes r
              ON r.Origin_Airport = f.Origin_Airport
             AND r.Destination_Airport = f.Destination_Airport
            WHERE f.Plane_ID = p.Plane_ID
              AND f.Flight_Status <> 'cancelled'
              AND TIMESTAMP(%s) < ADDTIME(TIMESTAMP(f.Departure_Date, f.Departure_Time), r.Duration)
              AND TIMESTAMP(f.Departure_Date, f.Departure_Time) < TIMESTAMP(%s)
          )
        ORDER BY p.Plane_ID
        """,
        (1 if is_long else 0, window_start_str, window_end_str),
    )
    rows = cursor.fetchall() or []
    # add computed label for UI
    for r in rows:
        # safe even if Plane_Size is numeric
        r["SizeLabel"] = "large" if _plane_has_business_from_cached(cursor, r["Plane_ID"]) else "small"
    return rows


def _plane_has_business_from_cached(cursor, plane_id):
    # small helper; avoids writing twice
    cursor.execute(
        """
        SELECT 1
        FROM Seats
        WHERE Plane_ID = %s
          AND LOWER(Class) = 'business'
        LIMIT 1
        """,
        (plane_id,),
    )
    return cursor.fetchone() is not None


def available_pilots(cursor, window_start_str: str, window_end_str: str, require_long_qualified: bool):
    cursor.execute(
        """
        SELECT p.Worker_ID, p.Is_Qualified
        FROM Pilots p
        WHERE (%s = 0 OR p.Is_Qualified = 1)
          AND NOT EXISTS (
            SELECT 1
            FROM Pilots_Scheduled_to_Flights ps
            JOIN Flight f ON f.Flight_ID = ps.Flight_ID
            JOIN Routes r
              ON r.Origin_Airport = f.Origin_Airport
             AND r.Destination_Airport = f.Destination_Airport
            WHERE ps.Worker_ID = p.Worker_ID
              AND f.Flight_Status <> 'cancelled'
              AND TIMESTAMP(%s) < ADDTIME(TIMESTAMP(f.Departure_Date, f.Departure_Time), r.Duration)
              AND TIMESTAMP(f.Departure_Date, f.Departure_Time) < TIMESTAMP(%s)
          )
        ORDER BY p.Worker_ID
        """,
        (1 if require_long_qualified else 0, window_start_str, window_end_str),
    )
    return cursor.fetchall() or []


def available_attendants(cursor, window_start_str: str, window_end_str: str, require_long_qualified: bool):
    cursor.execute(
        """
        SELECT a.Worker_ID, a.Is_Qualified
        FROM Flight_Attendants a
        WHERE (%s = 0 OR a.Is_Qualified = 1)
          AND NOT EXISTS (
            SELECT 1
            FROM Flight_Attendants_Assigned_To_Flights fa
            JOIN Flight f ON f.Flight_ID = fa.Flight_ID
            JOIN Routes r
              ON r.Origin_Airport = f.Origin_Airport
             AND r.Destination_Airport = f.Destination_Airport
            WHERE fa.Worker_ID = a.Worker_ID
              AND f.Flight_Status <> 'cancelled'
              AND TIMESTAMP(%s) < ADDTIME(TIMESTAMP(f.Departure_Date, f.Departure_Time), r.Duration)
              AND TIMESTAMP(f.Departure_Date, f.Departure_Time) < TIMESTAMP(%s)
          )
        ORDER BY a.Worker_ID
        """,
        (1 if require_long_qualified else 0, window_start_str, window_end_str),
    )
    return cursor.fetchall() or []

def parse_dt_flexible(value):
    """
    Accepts:
    - datetime
    - 'YYYY-MM-DD HH:MM'
    - 'YYYY-MM-DD HH:MM:SS'
    Returns datetime.
    """
    if isinstance(value, datetime):
        return value

    s = (value or "").strip()
    if not s:
        raise ValueError("Empty datetime string")

    # Try with seconds first, then without seconds
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    # If there are extra parts, trim to seconds length
    if len(s) >= 19:
        try:
            return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    raise ValueError(f"Invalid datetime format: {s}")

def overlap_exists_for_plane(cursor, plane_id, window_start, window_end) -> bool:
    start_dt = parse_dt_flexible(window_start)
    end_dt = parse_dt_flexible(window_end)

    cursor.execute("""
        SELECT 1
        FROM Flight f
        JOIN Routes r
          ON r.Origin_Airport = f.Origin_Airport
         AND r.Destination_Airport = f.Destination_Airport
        WHERE f.Plane_ID = %s
          AND f.Flight_Status IN ('active','full','done')  -- אם אצלך אחרת תשאירי כמו שהיה
          AND (
                TIMESTAMP(f.Departure_Date, f.Departure_Time) < %s
            AND TIMESTAMP(f.Departure_Date, f.Departure_Time) + INTERVAL TIME_TO_SEC(r.Duration) SECOND > %s
          )
        LIMIT 1
    """, (int(plane_id), end_dt, start_dt))

    return cursor.fetchone() is not None



def overlap_exists_for_pilot(cursor, worker_id, window_start, window_end) -> bool:
    start_dt = parse_dt_flexible(window_start)
    end_dt = parse_dt_flexible(window_end)

    cursor.execute("""
        SELECT 1
        FROM Pilots_Scheduled_to_Flights psf
        JOIN Flight f ON f.Flight_ID = psf.Flight_ID
        JOIN Routes r
          ON r.Origin_Airport = f.Origin_Airport
         AND r.Destination_Airport = f.Destination_Airport
        WHERE psf.Worker_ID = %s
          AND f.Flight_Status IN ('active','full','done')
          AND (
                TIMESTAMP(f.Departure_Date, f.Departure_Time) < %s
            AND TIMESTAMP(f.Departure_Date, f.Departure_Time) + INTERVAL TIME_TO_SEC(r.Duration) SECOND > %s
          )
        LIMIT 1
    """, (int(worker_id), end_dt, start_dt))

    return cursor.fetchone() is not None



def overlap_exists_for_attendant(cursor, worker_id, window_start, window_end) -> bool:
    start_dt = parse_dt_flexible(window_start)
    end_dt = parse_dt_flexible(window_end)

    cursor.execute("""
        SELECT 1
        FROM Flight_Attendants_Assigned_To_Flights fa
        JOIN Flight f ON f.Flight_ID = fa.Flight_ID
        JOIN Routes r
          ON r.Origin_Airport = f.Origin_Airport
         AND r.Destination_Airport = f.Destination_Airport
        WHERE fa.Worker_ID = %s
          AND f.Flight_Status IN ('active','full','done')
          AND (
                TIMESTAMP(f.Departure_Date, f.Departure_Time) < %s
            AND TIMESTAMP(f.Departure_Date, f.Departure_Time) + INTERVAL TIME_TO_SEC(r.Duration) SECOND > %s
          )
        LIMIT 1
    """, (int(worker_id), end_dt, start_dt))

    return cursor.fetchone() is not None


def _intervals_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    # True if intervals [a_start, a_end) and [b_start, b_end) overlap
    return a_start < b_end and b_start < a_end


def _flight_start_end_from_row(row):
    """
    row must include:
      - Departure_Date
      - Departure_Time
      - Duration  (either timedelta or 'HH:MM:SS' string)
    Returns: (start_dt, end_dt)
    """
    start = dt_from_date_time(row["Departure_Date"], row["Departure_Time"])

    dur = row["Duration"]
    if isinstance(dur, timedelta):
        minutes = int(dur.total_seconds() // 60)
    else:
        # expected 'HH:MM:SS' or 'HH:MM'
        parts = str(dur).split(":")
        h = int(parts[0]) if len(parts) > 0 else 0
        m = int(parts[1]) if len(parts) > 1 else 0
        minutes = h * 60 + m

    end = start + timedelta(minutes=minutes)
    return start, end
