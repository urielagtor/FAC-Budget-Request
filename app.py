import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Budget Builder", layout="centered")
st.title("Budget Builder")

# --- Category definitions (Main -> Sub) ---
CATEGORY_TREE = {
    "Capital Expenses": [
        "Computers",
        "Equipment reusable parts",
        "Storage totes",
        "Items that cost more than organizational supplies and will last more than one year",
    ],
    "Organizational Supplies": [
        "National membership dues",
        "Office supplies",
        "Gloves/masks",
        "Items needed for general club operations that aren’t for an event and won’t last more than one year",
    ],
    "Marketing Expenses": [
        "Printing costs",
        "Banners/trifolds",
        "Decorations for a campus display",
        "Promotional materials that aren’t club gear",
    ],
    "Club Gear": [
        "T-shirts",
        "Sweatshirts",
        "Jackets",
        "Wearable items featuring your club’s logo",
    ],
    "Event Supplies": [
        "Food/snacks",
        "Decorations",
        "Items needed to host and run events",
    ],
}

MAIN_CATEGORIES = list(CATEGORY_TREE.keys())

# --- Top-of-page guide ---
st.subheader("What goes where?")
st.caption("Use this guide when selecting an expense category:")

for main, subs in CATEGORY_TREE.items():
    st.markdown(f"**{main}**")
    st.markdown("\n".join([f"  - {s}" for s in subs]))

st.divider()

# --- Initialize state ---
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(
        columns=["Expense Category", "Description", "Qty.", "Amount", "Total Amount", "Date"]
    )

st.subheader("Add an expense line item")

with st.form("add_expense", clear_on_submit=True):
    expense_date = st.date_input("Date (optional)", value=date.today())

    c1, c2 = st.columns(2)
    with c1:
        main_cat = st.selectbox("Main Category", MAIN_CATEGORIES)
    with c2:
        sub_cat = st.selectbox("Sub Category", CATEGORY_TREE[main_cat])

    description = st.text_input("Description", placeholder="Required (e.g., Pizza for volunteer meeting)")

    c3, c4 = st.columns(2)
    with c3:
        qty = st.number_input("Qty.", min_value=0, step=1, value=1)
    with c4:
        amount = st.number_input("Amount (per unit)", min_value=0.0, step=1.0, value=0.0)

    total_amount = float(qty) * float(amount)
    st.write(f"**Total Amount (auto):** ${total_amount:,.2f}")

    submitted = st.form_submit_button("Add Line Item")

    if submitted:
        if not description.strip():
            st.error("Description is required.")
        else:
            new_row = {
                "Expense Category": f"{main_cat}/{sub_cat}",
                "Description": description.strip(),
                "Qty.": int(qty),
                "Amount": float(amount),
                "Total Amount": float(total_amount),
                "Date": str(expense_date),
            }
            st.session_state.expenses_df = pd.concat(
                [st.session_state.expenses_df, pd.DataFrame([new_row])],
                ignore_index=True
            )

st.subheader("Budget Line Items")

df = st.session_state.expenses_df.copy()

if df.empty:
    st.info("No line items yet. Add one above.")
else:
    # Make sure numeric columns are treated as numbers (helps editor + recalculation)
    for col in ["Qty.", "Amount", "Total Amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Editable table, but Total Amount is read-only
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        disabled=["Total Amount"],  # <-- read-only column
        key="budget_editor",
    )

    # Recalculate Total Amount from edited Qty/Amount (always authoritative)
    for col in ["Qty.", "Amount"]:
        edited_df[col] = pd.to_numeric(edited_df[col], errors="coerce").fillna(0)

    edited_df["Total Amount"] = edited_df["Qty."] * edited_df["Amount"]

    # Optional: enforce Description non-blank for edited rows too
    # (keeps blanks, but warns you; or you can auto-drop them if preferred)
    blank_desc = edited_df["Description"].fillna("").str.strip() == ""
    if blank_desc.any():
        st.warning("One or more rows have a blank Description. Please fill them in.")

    # Save back to session
    st.session_state.expenses_df = edited_df

    grand_total = float(edited_df["Total Amount"].sum())
    st.metric("Grand Total", f"${grand_total:,.2f}")

    csv_bytes = edited_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="budget_line_items.csv",
        mime="text/csv",
    )

    if st.button("Clear all line items"):
        st.session_state.expenses_df = st.session_state.expenses_df.iloc[0:0]
        st.rerun()
