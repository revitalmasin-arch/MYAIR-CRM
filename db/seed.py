"""Generates fake data for the MYAIR CRM case study.

Run directly to (re)build db/myair.db from scratch:
    python db/seed.py
"""
import random
import sqlite3
from datetime import datetime, timedelta

from faker import Faker

try:
    from database import DB_PATH, SCHEMA, AGENTS, SEAT_CLASSES  # running as script
except ImportError:
    from db.database import DB_PATH, SCHEMA, AGENTS, SEAT_CLASSES  # running as module

fake = Faker()
random.seed(42)
Faker.seed(42)

AIRPORTS = ["TLV", "JFK", "LHR", "CDG", "FRA", "FCO", "BCN", "AMS", "IST", "DXB", "ATH", "LIS"]
AIRCRAFT = {
    "Boeing 737-800": 189,
    "Airbus A320": 180,
    "Airbus A321neo": 220,
    "Boeing 787-9": 296,
}
FLIGHT_STATUS_WEIGHTS = [("Scheduled", 70), ("Delayed", 10), ("Cancelled", 5), ("Completed", 15)]
NUM_FLIGHTS = 40
NUM_CUSTOMERS = 60
NUM_BOOKINGS = 90


def weighted_choice(pairs):
    options, weights = zip(*pairs)
    return random.choices(options, weights=weights, k=1)[0]


def build_flights():
    flights = []
    for i in range(NUM_FLIGHTS):
        origin, destination = random.sample(AIRPORTS, 2)
        aircraft, seats_total = random.choice(list(AIRCRAFT.items()))
        departure = datetime.now() + timedelta(
            days=random.randint(-10, 30), hours=random.randint(0, 23), minutes=random.choice([0, 15, 30, 45])
        )
        arrival = departure + timedelta(hours=random.randint(1, 9), minutes=random.choice([0, 15, 30, 45]))
        status = weighted_choice(FLIGHT_STATUS_WEIGHTS)
        booked_seats = random.randint(0, int(seats_total * 0.85))
        flights.append((
            f"MY{100 + i}",
            origin,
            destination,
            departure.isoformat(timespec="minutes"),
            arrival.isoformat(timespec="minutes"),
            aircraft,
            seats_total,
            seats_total - booked_seats,
            round(random.uniform(80, 650), 2),
            status,
        ))
    return flights


def build_customers():
    customers = []
    for _ in range(NUM_CUSTOMERS):
        first, last = fake.first_name(), fake.last_name()
        created = fake.date_time_between(start_date="-2y", end_date="now").isoformat(timespec="seconds")
        customers.append((
            first,
            last,
            f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@example.com",
            fake.phone_number(),
            fake.bothify("??######").upper(),
            fake.country(),
            fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
            created,
            fake.sentence() if random.random() < 0.3 else None,
        ))
    return customers


def build_bookings(conn):
    flight_ids = [r[0] for r in conn.execute("SELECT flight_id FROM flights").fetchall()]
    customer_rows = conn.execute("SELECT customer_id FROM customers").fetchall()
    customer_ids = [r[0] for r in customer_rows]

    bookings = []
    seats_taken = {fid: 0 for fid in flight_ids}
    for _ in range(NUM_BOOKINGS):
        flight_id = random.choice(flight_ids)
        seats_total, seats_available = conn.execute(
            "SELECT seats_total, seats_available FROM flights WHERE flight_id = ?", (flight_id,)
        ).fetchone()
        if seats_taken[flight_id] >= seats_total - seats_available:
            continue  # no more "already booked" seats to represent for this flight

        seat_class = weighted_choice([("Economy", 75), ("Business", 20), ("First", 5)])
        base_price = conn.execute("SELECT price FROM flights WHERE flight_id = ?", (flight_id,)).fetchone()[0]
        multiplier = {"Economy": 1.0, "Business": 1.8, "First": 2.6}[seat_class]
        status = weighted_choice([("Confirmed", 85), ("Cancelled", 15)])
        booking_date = fake.date_time_between(start_date="-60d", end_date="now").isoformat(timespec="seconds")

        bookings.append((
            random.choice(customer_ids),
            flight_id,
            booking_date,
            seat_class,
            status,
            round(base_price * multiplier, 2),
            random.choice(AGENTS),
        ))
        seats_taken[flight_id] += 1
    return bookings


def seed():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("DROP TABLE IF EXISTS bookings; DROP TABLE IF EXISTS flights; DROP TABLE IF EXISTS customers;")
    conn.executescript(SCHEMA)

    conn.executemany(
        """INSERT INTO flights
           (flight_number, origin, destination, departure_time, arrival_time, aircraft,
            seats_total, seats_available, price, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        build_flights(),
    )
    conn.executemany(
        """INSERT INTO customers
           (first_name, last_name, email, phone, passport_number, nationality, date_of_birth, created_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        build_customers(),
    )
    conn.commit()

    conn.executemany(
        """INSERT INTO bookings (customer_id, flight_id, booking_date, seat_class, status, price_paid, agent_name)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        build_bookings(conn),
    )
    conn.commit()

    flights_n = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
    customers_n = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    bookings_n = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    conn.close()
    print(f"Seeded {DB_PATH}: {flights_n} flights, {customers_n} customers, {bookings_n} bookings.")


if __name__ == "__main__":
    seed()
