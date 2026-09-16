"""Customers page - register, search, edit and delete customer records."""
import streamlit as st

from db.database import (
    add_customer,
    delete_customer,
    email_taken,
    get_customer,
    get_customers,
    init_db,
    update_customer,
)

st.set_page_config(page_title="Customers | MYAIR CRM", page_icon="🧑‍💼", layout="wide")
init_db()

st.title("🧑‍💼 Customers")
st.caption("Register new customers and manage existing registrations.")

tab_search, tab_new = st.tabs(["Search & manage", "Register new customer"])

with tab_search:
    search = st.text_input("Search by name, email, phone or passport number")
    customers = get_customers(search)
    st.write(f"**{len(customers)}** customer(s) found.")
    st.dataframe(
        customers[["customer_id", "first_name", "last_name", "email", "phone", "nationality", "created_at"]],
        use_container_width=True,
        hide_index=True,
    )

    if not customers.empty:
        st.divider()
        st.subheader("Edit / delete a customer")
        options = {
            f"#{row.customer_id} — {row.first_name} {row.last_name} ({row.email})": row.customer_id
            for row in customers.itertuples()
        }
        choice = st.selectbox("Select a customer", list(options.keys()))
        customer = get_customer(options[choice])

        with st.form("edit_customer"):
            c1, c2 = st.columns(2)
            first_name = c1.text_input("First name", value=customer["first_name"])
            last_name = c2.text_input("Last name", value=customer["last_name"])
            email = c1.text_input("Email", value=customer["email"])
            phone = c2.text_input("Phone", value=customer["phone"] or "")
            passport_number = c1.text_input("Passport number", value=customer["passport_number"] or "")
            nationality = c2.text_input("Nationality", value=customer["nationality"] or "")
            date_of_birth = c1.text_input("Date of birth (YYYY-MM-DD)", value=customer["date_of_birth"] or "")
            notes = st.text_area("Notes", value=customer["notes"] or "")

            saved = st.form_submit_button("Save changes")
            if saved:
                if not first_name or not last_name or not email:
                    st.error("First name, last name and email are required.")
                elif email_taken(email, exclude_id=customer["customer_id"]):
                    st.error("Another customer already uses that email.")
                else:
                    update_customer(
                        customer["customer_id"], first_name, last_name, email, phone,
                        passport_number, nationality, date_of_birth, notes,
                    )
                    st.success("Customer updated.")
                    st.rerun()

        confirm_delete = st.checkbox(f"Confirm delete of #{customer['customer_id']} and their bookings")
        if st.button("Delete customer", disabled=not confirm_delete, type="primary"):
            delete_customer(customer["customer_id"])
            st.success("Customer deleted.")
            st.rerun()

with tab_new:
    with st.form("new_customer", clear_on_submit=True):
        c1, c2 = st.columns(2)
        first_name = c1.text_input("First name")
        last_name = c2.text_input("Last name")
        email = c1.text_input("Email")
        phone = c2.text_input("Phone")
        passport_number = c1.text_input("Passport number")
        nationality = c2.text_input("Nationality")
        date_of_birth = c1.text_input("Date of birth (YYYY-MM-DD)")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Register customer")
        if submitted:
            if not first_name or not last_name or not email:
                st.error("First name, last name and email are required.")
            elif email_taken(email):
                st.error("A customer with that email already exists.")
            else:
                new_id = add_customer(
                    first_name, last_name, email, phone, passport_number,
                    nationality, date_of_birth, notes,
                )
                st.success(f"Registered customer #{new_id}: {first_name} {last_name}.")
