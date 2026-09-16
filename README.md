# MYAIR CRM

A Streamlit CRM case study for **MYAIR**, a fictional airline. Built for travel
agents to look up existing flights and manage customer registrations and
bookings. All data is fake (SQLite, seeded with [Faker](https://faker.readthedocs.io/)) —
this is a case study, not a production system.

## Features

- **Flights** — search/filter the existing flight schedule by origin, destination, status and departure date.
- **Customers** — register new customers, search, edit, and delete existing registrations.
- **Bookings** — book a customer onto a flight with available seats, cancel bookings (releases the seat).
- **Dashboard** — KPIs and charts: bookings by status, revenue by seat class, top routes, 30-day booking trend.

## Getting started

```bash
pip install -r requirements.txt
python db/seed.py       # builds the fake database at db/myair.db
streamlit run app.py
```

Re-run `python db/seed.py` any time to reset to a fresh fake dataset (40 flights, 60 customers, 90 bookings).

## Project structure

```
app.py                 Home page (KPIs, agent selector)
pages/
  1_Flights.py          Search existing flights
  2_Customers.py         Register / search / edit / delete customers
  3_Bookings.py          Create / cancel bookings
  4_Dashboard.py          Charts & KPIs
db/
  database.py            All SQL lives here; pages call these functions
  seed.py                 Generates the fake dataset
requirements.txt
.streamlit/config.toml   Theme
```

## Data model

- **flights**: flight_number, origin, destination, departure/arrival time, aircraft, seats, price, status
- **customers**: name, email (unique), phone, passport number, nationality, date of birth, notes
- **bookings**: links a customer to a flight, seat class, status (Confirmed/Cancelled), price paid, booking agent

## Development notes

Phase-by-phase build notes and manual test steps live in the Obsidian vault
under `MYAIR-CRM/` (Phase 1 through Phase 6), including a bug that was caught
and fixed in Phase 5 (mixed timestamp formats breaking the dashboard's date
parsing).
