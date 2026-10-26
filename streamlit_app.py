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
st.subheader("Monthly Revenue Details")
st.caption(f"Monthly totals for: {selected_year}")

st.dataframe(
    monthly_revenue.to_frame()
    .style.format("${:,.2f}")
)
st.subheader("Supporting Data Tables")
st.write("Upload the supporting CSV files for your analysis.")

supporting_files = {
    "Stores": st.file_uploader(
        "Stores CSV", type="csv", key="stores_upload"
    ),
    "Products": st.file_uploader(
        "Products CSV", type="csv", key="products_upload"
    ),
    "Categories": st.file_uploader(
        "Categories CSV", type="csv", key="categories_upload"
    ),
    "Surveys": st.file_uploader(
        "Survey results CSV", type="csv", key="surveys_upload"
    ),
}

supporting_tables = {}

for table_name, file in supporting_files.items():
    if file is not None:
        try:
            table = pd.read_csv(
                file, dtype=str, sep=None, engine="python"
            )
            supporting_tables[table_name] = table

            st.success(
                f"{table_name}: {len(table):,} rows loaded"
            )

            with st.expander(f"Preview {table_name}"):
                st.dataframe(table.head(10))

        except Exception as error:
            st.error(f"Could not load {table_name}: {error}")
st.subheader("Customer Survey Results")

if "Surveys" not in supporting_tables:
    st.info("Upload the survey results CSV above to see this section.")
else:
    surveys = supporting_tables["Surveys"].copy()
    surveys.columns = surveys.columns.str.strip()

    required = {"Year", "Satisfaction", "Interest"}
    missing = required - set(surveys.columns)

    if missing:
        st.error(
            f"Survey file is missing: {', '.join(sorted(missing))}"
        )
    else:
        surveys["Year"] = pd.to_numeric(
            surveys["Year"].str.strip().str.replace(
                r"^[Yy]", "", regex=True
            ),
            errors="coerce"
        )

        for column in ["Satisfaction", "Interest"]:
            surveys[column] = pd.to_numeric(
                surveys[column], errors="coerce"
            )

        if selected_year != "All years":
            surveys = surveys[
                surveys["Year"] == selected_year
            ].copy()

        st.caption(
            f"Survey results for: {selected_year}. "
            "Missing ratings are excluded from averages."
        )

        if surveys[["Satisfaction", "Interest"]].notna().any().any():
            average_satisfaction = surveys["Satisfaction"].mean()
            average_interest = surveys["Interest"].mean()

            col1, col2 = st.columns(2)

            col1.metric(
                "Average Satisfaction",
                f"{average_satisfaction:.2f}"
                if pd.notna(average_satisfaction)
                else "No data"
            )

            col2.metric(
                "Average Interest",
                f"{average_interest:.2f}"
                if pd.notna(average_interest)
                else "No data"
            )

            yearly_surveys = (
                surveys.dropna(subset=["Year"])
                .groupby("Year")[["Satisfaction", "Interest"]]
                .mean()
                .sort_index()
            )

            yearly_surveys.index = (
                yearly_surveys.index.astype(int).astype(str)
            )

            st.write("**Average Satisfaction by Year**")
            st.bar_chart(yearly_surveys["Satisfaction"])

            st.write("**Average Interest by Year**")
            st.bar_chart(yearly_surveys["Interest"])

            st.write("**Annual Survey Averages**")
            st.dataframe(
                yearly_surveys.style.format(
                    "{:.2f}", na_rep="No data"
                )
            )
        else:
            st.info("No numeric survey ratings for this selection.")
