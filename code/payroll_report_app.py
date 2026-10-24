"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                           (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.

import streamlit as st

from payroll import (
    build_history,
    hours_grid,
    load_employees,
    load_export,
    missed_weeks,
    pay_by_month,
    summarize_employees,
)

st.title("Salt City Coffee — Quarterly Payroll Report")
st.write("Upload weekly payroll exports to review hours, pay, and missed weeks.")

employees = load_employees()
uploads = st.file_uploader(
    "Payroll exports",
    type=["csv"],
    accept_multiple_files=True,
    key="exports",
)

if uploads:
    history = build_history([load_export(upload) for upload in uploads], employees)
    unmatched = (
        history.loc[history["department"].isna(), "employeeid"].dropna().unique()
    )
    if len(unmatched):
        names = ", ".join(str(employee_id) for employee_id in unmatched)
        st.warning(
            f"These employee IDs are not on the roster and are excluded: {names}"
        )

    matched = history[history["department"].notna()].copy()
    departments = ["All", *sorted(matched["department"].unique())]
    department = st.selectbox("Department", departments, key="department")

    first_date = history["pay_date"].dt.date.min()
    last_date = history["pay_date"].dt.date.max()
    dates = st.date_input("Pay date range", value=(first_date, last_date), key="dates")
    start_date, end_date = dates

    selected = matched[matched["pay_date"].dt.date.between(start_date, end_date)]
    if department != "All":
        selected = selected[selected["department"] == department]

    st.subheader(f"{department}: {start_date} to {end_date}")
    weeks = selected["week_ending"].nunique()
    employee_count = selected["employee_id"].nunique()
    total_hours = selected["hours_worked"].sum()
    total_pay = selected["gross_pay"].sum()

    metric_columns = st.columns(4)
    metric_columns[0].metric("Weeks", f"{weeks:,}")
    metric_columns[1].metric("Employees", f"{employee_count:,}")
    metric_columns[2].metric("Total hours", f"{total_hours:,.2f}")
    metric_columns[3].metric("Total gross pay", f"${total_pay:,.2f}")

    monthly_pay = pay_by_month(selected)
    st.bar_chart(monthly_pay, x="month")
    st.dataframe(summarize_employees(selected))

    grid = hours_grid(selected)
    st.dataframe(grid)
    st.dataframe(missed_weeks(grid))

    st.download_button(
        "Download monthly payroll CSV",
        data=monthly_pay.to_csv(index=False),
        file_name="payroll_by_month.csv",
        mime="text/csv",
        key="download",
    )
