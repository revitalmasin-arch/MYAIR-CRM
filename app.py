"""MYAIR CRM - Home page.

Travel-agent facing CRM to browse existing flights and manage customer
registrations. Backed by a local fake SQLite database (case study data,
see db/seed.py).
"""
import streamlit as st

from db.database import AGENTS, db_exists, get_kpis, init_db

st.set_page_config(page_title="MYAIR CRM", page_icon="✈️", layout="wide")

init_db()

if get_kpis()["flights"] == 0:
    from db.seed import seed
    seed()

if "agent_name" not in st.session_state:
    st.session_state.agent_name = AGENTS[0]

with st.sidebar:
    st.selectbox("Signed in as", AGENTS, key="agent_name")

st.title("✈️ MYAIR CRM")
st.caption("Travel-agent workspace for flights, customers and bookings.")

st.markdown(
    """
    <style>
    @keyframes fly-across {
        0%   { left: -8%;  top: 55%; transform: rotate(0deg); }
        50%  { left: 50%;  top: 15%; transform: rotate(8deg); }
        100% { left: 108%; top: 55%; transform: rotate(0deg); }
    }
    .plane-strip {
        position: relative;
        height: 60px;
        margin-bottom: 0.5rem;
        overflow: hidden;
    }
    .plane-strip span {
        position: absolute;
        font-size: 2rem;
        animation: fly-across 7s ease-in-out infinite;
    }
    </style>
    <div class="plane-strip"><span>✈️</span></div>
    """,
    unsafe_allow_html=True,
)

if not db_exists():
    st.warning("No data yet. Run `python db/seed.py` from the project root, then refresh this page.")
else:
    kpis = get_kpis()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Flights", kpis["flights"])
    col2.metric("Customers", kpis["customers"])
    col3.metric("Active bookings", kpis["active_bookings"])
    col4.metric("Revenue (confirmed)", f"${kpis['revenue']:,.0f}")

    st.divider()
    st.markdown(
        "Use the pages in the sidebar to **search flights**, **manage customer "
        "registrations**, and **create or cancel bookings**."
    )
