import streamlit as st
import pandas as pd

st.title("E-Presso Business Dashboard")
st.write("Upload your E-Presso sales CSV to explore revenue.")

uploaded_file = st.file_uploader("Choose a sales CSV file", type="csv")

if uploaded_file is None:
    st.info("Upload epresso_sales.csv to get started.")
    st.stop()

try:
    data = pd.read_csv(uploaded_file, sep=None, engine="python")

    missing_columns = {"Revenue", "Date"} - set(data.columns)
    if missing_columns:
        st.error(
            f"Missing required columns: {', '.join(sorted(missing_columns))}"
        )
        st.stop()

    data["Revenue"] = pd.to_numeric(data["Revenue"], errors="raise")
    data["Date"] = pd.to_datetime(
        data["Date"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="raise"
    )

    if data.empty:
        st.warning("This file has no sales rows.")
        st.stop()

    if data[["Revenue", "Date"]].isna().any().any():
        st.error("Some dates or revenue values are missing.")
        st.stop()

except Exception as error:
    st.error(f"Could not process this file: {error}")
    st.stop()

st.success("File loaded successfully!")
st.write(f"Uploaded rows: {len(data):,} | Columns: {data.shape[1]}")

years = sorted(data["Date"].dt.year.unique().tolist())
selected_year = st.selectbox("Choose a year", ["All years"] + years)

if selected_year == "All years":
    filtered_data = data.copy()
else:
    filtered_data = data[data["Date"].dt.year == selected_year].copy()

st.subheader("Total Revenue")
st.metric(
    f"Revenue — {selected_year}",
    f"${filtered_data['Revenue'].sum():,.2f}"
)

st.caption(
    f"Showing {len(filtered_data):,} rows | "
    f"Period: {filtered_data['Date'].min():%b %Y} "
    f"to {filtered_data['Date'].max():%b %Y}. Revenue is not profit."
)

annual_revenue = (
    filtered_data.groupby(filtered_data["Date"].dt.year)["Revenue"]
    .sum()
    .sort_index()
)
annual_revenue.index = annual_revenue.index.astype(str)
annual_revenue.index.name = "Year"
annual_revenue.name = "Revenue ($)"

st.subheader("Revenue by Year")
st.bar_chart(annual_revenue)

st.subheader("Annual Revenue Totals")
st.dataframe(annual_revenue.to_frame().style.format("${:,.2f}"))

monthly_revenue = (
    filtered_data.groupby(filtered_data["Date"].dt.to_period("M"))["Revenue"]
    .sum()
    .sort_index()
)
monthly_revenue.index = monthly_revenue.index.astype(str)
monthly_revenue.index.name = "Month"
monthly_revenue.name = "Revenue ($)"

st.subheader("Revenue by Month")
st.caption(f"Monthly totals for: {selected_year}")
st.line_chart(monthly_revenue)

st.subheader("Data Preview — Selected Year(s)")
st.dataframe(filtered_data.head(20))
