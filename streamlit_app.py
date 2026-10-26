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
st.subheader("Revenue by Sales Channel")
st.caption(f"Revenue for: {selected_year}")

# Store types from the E-Presso Stores table you copied.
store_types = {"SH00": "Website"}
store_types.update({
    f"SH{i:02d}": "Brick & Mortar"
    for i in range(1, 21)
})

if "Store ID" not in filtered_data.columns:
    st.error("Sales channel analysis requires a Store ID column.")
else:
    channel_data = filtered_data.copy()
    channel_data["Sales Channel"] = (
        channel_data["Store ID"]
        .map(store_types)
        .fillna("Unknown store")
    )

    if (channel_data["Sales Channel"] == "Unknown store").any():
        st.warning("Some store IDs are unknown. Check the store information.")

    channel_revenue = (
        channel_data.groupby("Sales Channel")["Revenue"]
        .sum()
        .sort_index()
    )
    channel_revenue.name = "Revenue ($)"

    st.bar_chart(channel_revenue)
    st.dataframe(
        channel_revenue.to_frame().style.format("${:,.2f}")
    )
st.subheader("Data Quality Checks")
st.caption("These checks cover the entire uploaded file.")

missing_cells = int(
    data.replace(r"^\s*$", pd.NA, regex=True)
    .isna()
    .sum()
    .sum()
)
duplicate_rows = int(data.duplicated().sum())
negative_revenue = int((data["Revenue"] < 0).sum())

st.write(f"Missing values: {missing_cells:,}")
st.write(f"Duplicate rows: {duplicate_rows:,}")
st.write(f"Negative revenue records: {negative_revenue:,}")

if "Sales ID" in data.columns:
    duplicate_ids = int(
        data["Sales ID"].dropna().duplicated().sum()
    )
    st.write(f"Repeated Sales IDs: {duplicate_ids:,}")
else:
    duplicate_ids = 0
    st.warning("Sales ID column is missing.")

if (
    missing_cells == 0
    and duplicate_rows == 0
    and negative_revenue == 0
    and duplicate_ids == 0
):
    st.success("No issues found in these checks.")
else:
    st.warning("Review the flagged records before using the results.")
st.subheader("Revenue by Product Category")

category_names = {
    "C1": "Beans",
    "C2": "Syrups",
    "C3": "Espresso Machines",
    "C4": "Accessories",
    "C5": "Frothers"
}

if "Category ID" in filtered_data.columns:
    category_data = filtered_data.copy()
    category_data["Category"] = (
        category_data["Category ID"]
        .map(category_names)
        .fillna("Unknown category")
    )

    category_revenue = (
        category_data.groupby("Category")["Revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    st.caption(f"Revenue for: {selected_year}")
    st.bar_chart(category_revenue)
    st.dataframe(
        category_revenue.to_frame()
        .style.format({"Revenue": "${:,.2f}"})
    )
else:
    st.warning("Category analysis requires a Category ID column.")
