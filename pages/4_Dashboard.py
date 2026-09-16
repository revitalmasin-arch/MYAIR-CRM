"""Dashboard page - KPIs and quick reports for travel agents."""
import pandas as pd
import plotly.express as px
import streamlit as st

from db.database import get_bookings, get_kpis, init_db

st.set_page_config(page_title="Dashboard | MYAIR CRM", page_icon="📊", layout="wide")
init_db()

# Palette roles (see MYAIR-CRM Obsidian notes / dataviz reference palette).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
STATUS_GOOD, STATUS_CRITICAL = "#0ca30c", "#d03b3b"
SEQ_BLUE_400 = "#3987e5"

st.title("📊 Dashboard")
st.caption("Snapshot of bookings and revenue across the network.")

kpis = get_kpis()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Flights", kpis["flights"])
c2.metric("Customers", kpis["customers"])
c3.metric("Active bookings", kpis["active_bookings"])
c4.metric("Revenue (confirmed)", f"${kpis['revenue']:,.0f}")

st.divider()

bookings = get_bookings()

if bookings.empty:
    st.info("No bookings yet — create some on the Bookings page first.")
else:
    row1_left, row1_right = st.columns(2)

    with row1_left:
        st.subheader("Bookings by status")
        by_status = bookings["status"].value_counts().reindex(["Confirmed", "Cancelled"]).fillna(0).reset_index()
        by_status.columns = ["status", "count"]
        fig = px.bar(
            by_status, x="status", y="count", text="count",
            color="status", color_discrete_map={"Confirmed": STATUS_GOOD, "Cancelled": STATUS_CRITICAL},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, yaxis_title="Bookings", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with row1_right:
        st.subheader("Confirmed revenue by seat class")
        confirmed = bookings[bookings["status"] == "Confirmed"]
        by_class = confirmed.groupby("seat_class")["price_paid"].sum().reindex(
            ["Economy", "Business", "First"]
        ).fillna(0).reset_index()
        fig = px.bar(
            by_class, x="seat_class", y="price_paid", text="price_paid",
            color="seat_class",
            color_discrete_map={"Economy": BLUE, "Business": ORANGE, "First": AQUA},
        )
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(showlegend=False, yaxis_title="Revenue ($)", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    row2_left, row2_right = st.columns(2)

    with row2_left:
        st.subheader("Top 5 routes by bookings")
        bookings["route"] = bookings["origin"] + " → " + bookings["destination"]
        top_routes = bookings["route"].value_counts().head(5).sort_values().reset_index()
        top_routes.columns = ["route", "count"]
        fig = px.bar(top_routes, x="count", y="route", orientation="h", text="count")
        fig.update_traces(marker_color=SEQ_BLUE_400, textposition="outside")
        fig.update_layout(yaxis_title=None, xaxis_title="Bookings")
        st.plotly_chart(fig, use_container_width=True)

    with row2_right:
        st.subheader("Bookings over the last 30 days")
        bookings["booking_day"] = pd.to_datetime(bookings["booking_date"], format="ISO8601", utc=True).dt.date
        cutoff = pd.Timestamp.now().date() - pd.Timedelta(days=30)
        recent = bookings[bookings["booking_day"] >= cutoff]
        by_day = recent.groupby("booking_day").size().reset_index(name="count")
        fig = px.line(by_day, x="booking_day", y="count", markers=True)
        fig.update_traces(line_color=SEQ_BLUE_400, marker_color=SEQ_BLUE_400)
        fig.update_layout(yaxis_title="Bookings", xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
