"""Bookings page - link customers to flights and manage booking status."""
import streamlit as st

from db.database import (
    AGENTS,
    BOOKING_STATUSES,
    SEAT_CLASSES,
    add_booking,
    cancel_booking,
    get_bookings,
    get_customers,
    get_flights,
    init_db,
)

st.set_page_config(page_title="Bookings | MYAIR CRM", page_icon="🧾", layout="wide")
init_db()

if "agent_name" not in st.session_state:
    st.session_state.agent_name = AGENTS[0]

st.title("🧾 Bookings")
st.caption(f"Acting as agent: **{st.session_state.agent_name}** (change on the Home page).")

tab_manage, tab_new = st.tabs(["Manage bookings", "New booking"])

PRICE_MULTIPLIER = {"Economy": 1.0, "Business": 1.8, "First": 2.6}

with tab_manage:
    status_filter = st.selectbox("Status", [""] + BOOKING_STATUSES, format_func=lambda s: s or "Any")
    bookings = get_bookings(status=status_filter or None)
    st.write(f"**{len(bookings)}** booking(s) found.")
    st.dataframe(
        bookings[[
            "booking_id", "customer_name", "email", "flight_number", "origin", "destination",
            "departure_time", "seat_class", "status", "price_paid", "agent_name", "booking_date",
        ]],
        use_container_width=True,
        hide_index=True,
    )

    confirmed = bookings[bookings["status"] == "Confirmed"]
    if not confirmed.empty:
        st.divider()
        st.subheader("Cancel a booking")
        options = {
            f"#{row.booking_id} — {row.customer_name} on {row.flight_number} ({row.origin}->{row.destination})": row.booking_id
            for row in confirmed.itertuples()
        }
        choice = st.selectbox("Select a confirmed booking", list(options.keys()))
        if st.button("Cancel booking", type="primary"):
            cancel_booking(options[choice])
            st.success("Booking cancelled and the seat was released back to the flight.")
            st.rerun()

with tab_new:
    customers = get_customers()
    flights = get_flights()
    bookable_flights = flights[(flights["seats_available"] > 0) & (flights["status"].isin(["Scheduled", "Delayed"]))]

    if customers.empty or bookable_flights.empty:
        st.info("Need at least one customer and one flight with available seats to create a booking.")
    else:
        customer_options = {
            f"#{row.customer_id} — {row.first_name} {row.last_name} ({row.email})": row.customer_id
            for row in customers.itertuples()
        }
        flight_options = {
            f"{row.flight_number}: {row.origin}->{row.destination} @ {row.departure_time} "
            f"({row.seats_available} seats left, ${row.price:.0f})": row.flight_id
            for row in bookable_flights.itertuples()
        }

        with st.form("new_booking"):
            customer_choice = st.selectbox("Customer", list(customer_options.keys()))
            flight_choice = st.selectbox("Flight", list(flight_options.keys()))
            seat_class = st.selectbox("Seat class", SEAT_CLASSES)
            submitted = st.form_submit_button("Create booking")

            if submitted:
                flight_id = flight_options[flight_choice]
                base_price = float(bookable_flights.loc[bookable_flights["flight_id"] == flight_id, "price"].iloc[0])
                price_paid = round(base_price * PRICE_MULTIPLIER[seat_class], 2)
                try:
                    booking_id = add_booking(
                        customer_options[customer_choice], flight_id, seat_class,
                        price_paid, st.session_state.agent_name,
                    )
                    st.success(f"Booking #{booking_id} created — ${price_paid:,.2f} ({seat_class}).")
                except ValueError as exc:
                    st.error(str(exc))
