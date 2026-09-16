"""Data access layer for the MYAIR CRM fake database (SQLite).

Every page in the Streamlit app talks to the database through the
functions in this module instead of writing raw SQL inline.
"""
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
import sqlite3

import pandas as pd

DB_DIR = Path(__file__).resolve().parent
DB_PATH = DB_DIR / "myair.db"

AGENTS = ["Dana Cohen", "Omer Levi", "Noa Peretz", "Yossi Mizrahi", "Shira Avraham"]
SEAT_CLASSES = ["Economy", "Business", "First"]
FLIGHT_STATUSES = ["Scheduled", "Delayed", "Cancelled", "Completed"]
BOOKING_STATUSES = ["Confirmed", "Cancelled"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS flights (
    flight_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    flight_number   TEXT NOT NULL,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    departure_time  TEXT NOT NULL,
    arrival_time    TEXT NOT NULL,
    aircraft        TEXT NOT NULL,
    seats_total     INTEGER NOT NULL,
    seats_available INTEGER NOT NULL,
    price           REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Scheduled'
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name       TEXT NOT NULL,
    last_name        TEXT NOT NULL,
    email            TEXT NOT NULL UNIQUE,
    phone            TEXT,
    passport_number  TEXT,
    nationality      TEXT,
    date_of_birth    TEXT,
    created_at       TEXT NOT NULL,
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    flight_id    INTEGER NOT NULL REFERENCES flights(flight_id),
    booking_date TEXT NOT NULL,
    seat_class   TEXT NOT NULL DEFAULT 'Economy',
    status       TEXT NOT NULL DEFAULT 'Confirmed',
    price_paid   REAL NOT NULL,
    agent_name   TEXT
);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)


def db_exists() -> bool:
    return DB_PATH.exists()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---------------------------------------------------------------- flights --
def get_flights(origin=None, destination=None, status=None, date_from=None, date_to=None) -> pd.DataFrame:
    query = "SELECT * FROM flights WHERE 1=1"
    params = []
    if origin:
        query += " AND origin = ?"
        params.append(origin)
    if destination:
        query += " AND destination = ?"
        params.append(destination)
    if status:
        query += " AND status = ?"
        params.append(status)
    if date_from:
        query += " AND date(departure_time) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(departure_time) <= date(?)"
        params.append(date_to)
    query += " ORDER BY departure_time ASC"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_flight(flight_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM flights WHERE flight_id = ?", (flight_id,)).fetchone()
        return dict(row) if row else None


def get_airports() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT origin AS a FROM flights UNION SELECT DISTINCT destination AS a FROM flights"
        ).fetchall()
        return sorted({r["a"] for r in rows})


def update_flight_status(flight_id: int, status: str):
    with get_connection() as conn:
        conn.execute("UPDATE flights SET status = ? WHERE flight_id = ?", (status, flight_id))


# --------------------------------------------------------------- customers --
def get_customers(search: str = "") -> pd.DataFrame:
    query = "SELECT * FROM customers"
    params = []
    if search:
        query += """ WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?
                     OR phone LIKE ? OR passport_number LIKE ?"""
        like = f"%{search}%"
        params = [like, like, like, like, like]
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_customer(customer_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()
        return dict(row) if row else None


def email_taken(email: str, exclude_id: int | None = None) -> bool:
    with get_connection() as conn:
        if exclude_id:
            row = conn.execute(
                "SELECT 1 FROM customers WHERE email = ? AND customer_id != ?", (email, exclude_id)
            ).fetchone()
        else:
            row = conn.execute("SELECT 1 FROM customers WHERE email = ?", (email,)).fetchone()
        return row is not None


def add_customer(first_name, last_name, email, phone, passport_number, nationality, date_of_birth, notes) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO customers
               (first_name, last_name, email, phone, passport_number, nationality, date_of_birth, created_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, email, phone, passport_number, nationality, date_of_birth, now_iso(), notes),
        )
        return cur.lastrowid


def update_customer(customer_id, first_name, last_name, email, phone, passport_number, nationality,
                     date_of_birth, notes):
    with get_connection() as conn:
        conn.execute(
            """UPDATE customers SET first_name=?, last_name=?, email=?, phone=?, passport_number=?,
               nationality=?, date_of_birth=?, notes=? WHERE customer_id=?""",
            (first_name, last_name, email, phone, passport_number, nationality, date_of_birth, notes, customer_id),
        )


def delete_customer(customer_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM bookings WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))


# ---------------------------------------------------------------- bookings --
def get_bookings(customer_id=None, flight_id=None, status=None) -> pd.DataFrame:
    query = """
        SELECT b.booking_id, b.booking_date, b.seat_class, b.status, b.price_paid, b.agent_name,
               c.customer_id, c.first_name || ' ' || c.last_name AS customer_name, c.email,
               f.flight_id, f.flight_number, f.origin, f.destination, f.departure_time
        FROM bookings b
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN flights f ON f.flight_id = b.flight_id
        WHERE 1=1
    """
    params = []
    if customer_id:
        query += " AND b.customer_id = ?"
        params.append(customer_id)
    if flight_id:
        query += " AND b.flight_id = ?"
        params.append(flight_id)
    if status:
        query += " AND b.status = ?"
        params.append(status)
    query += " ORDER BY b.booking_date DESC"
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


def add_booking(customer_id: int, flight_id: int, seat_class: str, price_paid: float, agent_name: str) -> int:
    with get_connection() as conn:
        flight = conn.execute("SELECT seats_available FROM flights WHERE flight_id = ?", (flight_id,)).fetchone()
        if flight is None or flight["seats_available"] <= 0:
            raise ValueError("No seats available on this flight.")
        cur = conn.execute(
            """INSERT INTO bookings (customer_id, flight_id, booking_date, seat_class, status, price_paid, agent_name)
               VALUES (?, ?, ?, ?, 'Confirmed', ?, ?)""",
            (customer_id, flight_id, now_iso(), seat_class, price_paid, agent_name),
        )
        conn.execute(
            "UPDATE flights SET seats_available = seats_available - 1 WHERE flight_id = ?", (flight_id,)
        )
        return cur.lastrowid


def cancel_booking(booking_id: int):
    with get_connection() as conn:
        booking = conn.execute("SELECT flight_id, status FROM bookings WHERE booking_id = ?", (booking_id,)).fetchone()
        if booking is None or booking["status"] == "Cancelled":
            return
        conn.execute("UPDATE bookings SET status = 'Cancelled' WHERE booking_id = ?", (booking_id,))
        conn.execute(
            "UPDATE flights SET seats_available = seats_available + 1 WHERE flight_id = ?", (booking["flight_id"],)
        )


# --------------------------------------------------------------- dashboard --
def get_kpis() -> dict:
    with get_connection() as conn:
        flights = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        active_bookings = conn.execute("SELECT COUNT(*) FROM bookings WHERE status = 'Confirmed'").fetchone()[0]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(price_paid), 0) FROM bookings WHERE status = 'Confirmed'"
        ).fetchone()[0]
        return {
            "flights": flights,
            "customers": customers,
            "active_bookings": active_bookings,
            "revenue": revenue,
        }
