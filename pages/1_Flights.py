"""Flights page - browse and search existing MYAIR flights."""
import streamlit as st

from db.database import FLIGHT_STATUSES, get_airports, get_flights, init_db

st.set_page_config(page_title="Flights | MYAIR CRM", page_icon="✈️", layout="wide")
init_db()

st.title("✈️ Flights")
st.caption("Search the existing flight schedule.")

airports = [""] + get_airports()

col1, col2, col3 = st.columns(3)
origin = col1.selectbox("Origin", airports, format_func=lambda a: a or "Any")
destination = col2.selectbox("Destination", airports, format_func=lambda a: a or "Any")
status = col3.selectbox("Status", [""] + FLIGHT_STATUSES, format_func=lambda s: s or "Any")

col4, col5 = st.columns(2)
date_from = col4.date_input("Departs on/after", value=None)
date_to = col5.date_input("Departs on/before", value=None)

flights = get_flights(
    origin=origin or None,
    destination=destination or None,
    status=status or None,
    date_from=str(date_from) if date_from else None,
    date_to=str(date_to) if date_to else None,
)

st.write(f"**{len(flights)}** flight(s) found.")
st.dataframe(
    flights[[
        "flight_id", "flight_number", "origin", "destination", "departure_time",
        "arrival_time", "aircraft", "seats_available", "seats_total", "price", "status",
    ]],
    use_container_width=True,
    hide_index=True,
)
