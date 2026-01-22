import re
import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="ASOIT Budget Builder", layout="centered")
st.title("ASOIT Budget Builder")

# -----------------------------
# Category definitions
# -----------------------------
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

INDENT = "   "  # visual indent like your screenshot
HEADER_SUFFIX = ":"


def build_category_dropdown_items(tree: dict[str, list[str]]) -> tuple[list[str], dict[str, str]]:
    """
    Returns:
      - display_items: list of strings shown in the dropdown (includes headers + indented subs)
      - display_to_value: mapping from display string to stored value "Main/Sub" (subs only)
    """
    display_items = []
    display_to_value = {}
    for main, subs in tree.items():
        header = f"{main}{HEADER_SUFFIX}"
        display_items.append(header)
        for sub in subs:
            display = f"{INDENT}{sub}"
            display_items.append(display)
            display_to_value[display] = f"{main}/{sub}"
        display_items.append("")  # blank spacer line like the screenshot
    # remove trailing blank spacer if present
    while display_items and display_items[-1] == "":
        display_items.pop()
    return display_items, display_to_value


DISPLAY_ITEMS, DISPLAY_TO_VALUE = build_category_dropdown_items(CATEGORY_TREE)

# -----------------------------
# Validation helpers
# -----------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(s: str) -> bool:
    s = (s or "").strip()
    return bool(EMAIL_RE.match(s))


# -----------------------------
# Club Info (required)
# -----------------------------
st.subheader("Club Info")

club_col1, club_col2 = st.columns(2)
with club_col1:
    official_club_name = st.text_input("Official Club Name *", placeholder="e.g., ASOIT Robotics Club")
    president_email = st.text_input("President Email *", placeholder="name@oit.edu")
with club_col2:
    treasurer_email = st.text_input("Treasurer Email *", placeholder="name@oit.edu")
    advisor_email = st.text_input("Advisor Email *", placeholder="name@oit.edu")

club_errors = []
if official_club_name.strip() == "":
    club_errors.append("Official Club Name is required.")
if not is_valid_email(president_email):
    club_errors.append("President Email must be a valid email address.")
if not is_valid_email(treasurer_email):
    club_errors.append("Treasurer Email must be a valid email address.")
if not is_valid_email(advisor_email):
    club_errors.append("Advisor Email must be a valid email address.")

if club_errors:
    st.warning("Please complete the required Club Info fields before exporting or adding items.")
    for e in club_errors:
        st.caption(f"• {e}")

st.divider()

# -----------------------------
# What goes where? guide
# -----------------------------
st.subheader("What goes where?")
st.caption("Use this guide when selecting an expense category:")

for main, subs in CATEGORY_TREE.items():
    st.markdown(f"**{main}{HEADER_SUFFIX}**")
    st.markdown("\n".join([f"{INDENT}- {s}" for s in subs]))

st.divider()

# -----------------------------
# Initialize state for expenses
# -----------------------------
if "expenses_df" not in st.session_state:
    st.session_state.expenses_df = pd.DataFrame(
        columns=[
            "Expense Category",
            "Description",
            "Qty.",
            "Amount",
            "Total Amount",
            "Date",
        ]
    )

if "last_valid_category_display" not in st.session_state:
    # default to first sub-item
    first_valid = next((x for x in DISPLAY_ITEMS if x in DISPLAY_TO_VALUE), None)
    st.session_state.last_valid_category_display = first_valid

# -----------------------------
# Add line item form
# -----------------------------
st.subheader("Add an expense line item")

with st.form("add_expense", clear_on_submit=True):
    expense_date = st.date_input("Date (optional)", value=date.today())

    # One dropdown with header + indented subs
    selected_display = st.selectbox(
        "Expense Category *",
        DISPLAY_ITEMS,
        index=DISPLAY_ITEMS.index(st.session_state.last_valid_category_display)
        if st.session_state.last_valid_category_display in DISPLAY_ITEMS
        else 0,
    )

    description = st.text_input("Description *", placeholder="Required (e.g., Pizza for volunteer meeting)")

    c1, c2 = st.columns(2)
    with c1:
        qty = st.number_input("Qty.", min_value=0, step=1, value=1)
    with c2:
        amount = st.number_input("Amount (per unit)", min_value=0.0, step=1.0, value=0.0)

    total_amount = float(qty) * float(amount)
    st.write(f"**Total Amount (auto):** ${total_amount:,.2f}")

    submitted = st.form_submit_button("Add Line Item")

    if submitted:
        # Validate club info first
        if club_errors:
            st.error("Fix Club Info fields above before adding line items.")
        else:
            # Validate category selection (must be a sub-item, not a header/spacer)
            if selected_display not in DISPLAY_TO_VALUE:
                st.error("Please select a sub-category (the indented items), not a header.")
            elif not description.strip():
                st.error("Description is required.")
            else:
                st.session_state.last_valid_category_display = selected_display

                new_row = {
                    "Expense Category": DISPLAY_TO_VALUE[selected_display],  # Main/Sub
                    "Description": description.strip(),
                    "Qty.": int(qty),
                    "Amount": float(amount),
                    "Total Amount": float(total_amount),
                    "Date": str(expense_date),
                }

                st.session_state.expenses_df = pd.concat(
                    [st.session_state.expenses_df, pd.DataFrame([new_row])],
                    ignore_index=True,
                )

# -----------------------------
# Table + editing
# -----------------------------
st.subheader("Budget Line Items")

df = st.session_state.expenses_df.copy()

if df.empty:
    st.info("No line items yet. Add one above.")
else:
    # Ensure numeric types
    for col in ["Qty.", "Amount", "Total Amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        disabled=["Total Amount"],  # read-only
        key="budget_editor",
    )

    # Recalc totals from any edits to qty/amount
    for col in ["Qty.", "Amount"]:
        edited_df[col] = pd.to_numeric(edited_df[col], errors="coerce").fillna(0)

    edited_df["Total Amount"] = edited_df["Qty."] * edited_df["Amount"]

    # Enforce description (warn if any blank)
    blank_desc = edited_df["Description"].fillna("").str.strip() == ""
    if blank_desc.any():
        st.warning("One or more rows have a blank Description. Please fill them in before exporting.")

    st.session_state.expenses_df = edited_df

    grand_total = float(edited_df["Total Amount"].sum())
    st.metric("Grand Total", f"${grand_total:,.2f}")

    # -----------------------------
    # CSV Export (includes Club Info columns on each row)
    # -----------------------------
    export_df = edited_df.copy()
    export_df.insert(0, "Official Club Name", official_club_name.strip())
    export_df.insert(1, "President Email", president_email.strip())
    export_df.insert(2, "Treasurer Email", treasurer_email.strip())
    export_df.insert(3, "Advisor Email", advisor_email.strip())

    # Block export if required fields missing
    can_export = (not club_errors) and (not blank_desc.any())

    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv_bytes,
        file_name="budget_line_items.csv",
        mime="text/csv",
        disabled=not can_export,
        help=None if can_export else "Fill Club Info and ensure every row has a Description before exporting.",
    )

    if st.button("Clear all line items"):
        st.session_state.expenses_df = st.session_state.expenses_df.iloc[0:0]
        st.rerun()
