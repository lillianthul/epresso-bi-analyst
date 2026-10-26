import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="E-Presso Business Dashboard",
    page_icon="☕",
    layout="wide"
)

st.title("E-Presso Business Dashboard")
st.write("Upload your E-Presso CSV files to explore business performance.")


# ---------- SALES DATA ----------

uploaded_file = st.file_uploader(
    "Sales CSV",
    type="csv",
    key="sales_upload"
)

if uploaded_file is None:
    st.info("Upload epresso_sales.csv to get started.")
    st.stop()

try:
    data = pd.read_csv(uploaded_file, sep=None, engine="python")
    data.columns = data.columns.str.strip()

    if data.columns.duplicated().any():
        st.error("The sales file contains duplicate column names.")
        st.stop()

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
    st.error(f"Could not process the sales file: {error}")
    st.stop()

st.success(
    f"Sales loaded: {len(data):,} rows | {data.shape[1]} columns"
)


# ---------- SUPPORTING FILES ----------

st.subheader("Supporting Data Tables")
st.write("Upload your Stores, Products, Categories, and Surveys CSV files.")

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
            table.columns = table.columns.str.strip()

            if table.columns.duplicated().any():
                st.error(
                    f"{table_name} contains duplicate column names."
                )
                continue

            supporting_tables[table_name] = table

            st.success(f"{table_name}: {len(table):,} rows loaded")

            with st.expander(f"Preview {table_name}"):
                st.dataframe(table.head(10))

        except Exception as error:
            st.error(f"Could not load {table_name}: {error}")


# ---------- FILTER ----------

st.divider()
st.subheader("Dashboard Filters")

years = sorted(data["Date"].dt.year.unique().tolist())
selected_year = st.selectbox("Choose a year", ["All years"] + years)

if selected_year == "All years":
    filtered_data = data.copy()
else:
    filtered_data = data[
        data["Date"].dt.year == selected_year
    ].copy()


# ---------- METRICS ----------

st.subheader("Sales Overview")

col1, col2 = st.columns(2)

col1.metric(
    f"Total Revenue — {selected_year}",
    f"${filtered_data['Revenue'].sum():,.2f}"
)

col2.metric("Sales Rows", f"{len(filtered_data):,}")

st.caption(
    f"Period: {filtered_data['Date'].min():%b %Y} "
    f"to {filtered_data['Date'].max():%b %Y}. "
    "Revenue is not profit. Sales rows are not necessarily orders."
)


# ---------- YEARLY REVENUE ----------

annual_revenue = (
    filtered_data.groupby(filtered_data["Date"].dt.year)["Revenue"]
    .sum()
    .sort_index()
)

annual_revenue.index = annual_revenue.index.astype(str)
annual_revenue.index.name = "Year"

st.subheader("Revenue by Year")
st.caption(f"Revenue for: {selected_year}")
st.bar_chart(annual_revenue)

with st.expander("Annual Revenue Totals"):
    st.dataframe(
        annual_revenue.to_frame().style.format(
            {"Revenue": "${:,.2f}"}
        )
    )


# ---------- MONTHLY REVENUE ----------

monthly_revenue = (
    filtered_data.groupby(
        filtered_data["Date"].dt.to_period("M")
    )["Revenue"]
    .sum()
    .sort_index()
)

monthly_revenue.index = monthly_revenue.index.astype(str)
monthly_revenue.index.name = "Month"

st.subheader("Revenue by Month")
st.caption(f"Monthly totals for: {selected_year}")
st.line_chart(monthly_revenue)

with st.expander("Monthly Revenue Details"):
    st.dataframe(
        monthly_revenue.to_frame().style.format(
            {"Revenue": "${:,.2f}"}
        )
    )


# ---------- SALES CHANNELS FROM STORES FILE ----------

st.subheader("Revenue by Sales Channel")
st.caption(f"Revenue for: {selected_year}")

if "Stores" not in supporting_tables:
    st.info("Upload the Stores CSV to calculate sales channels.")

elif "Store ID" not in filtered_data.columns:
    st.error("Sales data is missing Store ID.")

else:
    stores = supporting_tables["Stores"].copy()

    if not {"ID", "StoreType"}.issubset(stores.columns):
        st.error("Stores CSV needs ID and StoreType columns.")

    else:
        stores["ID"] = stores["ID"].str.strip()
        stores["StoreType"] = (
            stores["StoreType"].str.strip().replace("", pd.NA)
        )

        if stores["ID"].isna().any() or stores["ID"].eq("").any():
            st.error("Stores contains missing IDs. Fix these first.")

        elif stores["ID"].duplicated().any():
            st.error(
                "Stores contains repeated IDs. "
                "Fix these before combining tables."
            )

        else:
            channel_data = filtered_data.copy()
            channel_data["Store ID"] = (
                channel_data["Store ID"]
                .astype("string")
                .str.strip()
            )

            store_lookup = stores[["ID", "StoreType"]].rename(
                columns={
                    "ID": "Store ID",
                    "StoreType": "Sales Channel"
                }
            )

            channel_data = channel_data.merge(
                store_lookup,
                on="Store ID",
                how="left",
                validate="many_to_one"
            )

            unmatched = channel_data["Sales Channel"].isna()

            if unmatched.any():
                st.warning(
                    f"{int(unmatched.sum()):,} sales rows have no "
                    "matching store type. Included as Unknown."
                )

            channel_data["Sales Channel"] = (
                channel_data["Sales Channel"].fillna("Unknown")
            )

            channel_revenue = (
                channel_data.groupby("Sales Channel")["Revenue"]
                .sum()
                .sort_index()
            )

            st.bar_chart(channel_revenue)

            st.dataframe(
                channel_revenue.to_frame().style.format(
                    {"Revenue": "${:,.2f}"}
                )
            )

            st.caption(
                "Relationship: many sales rows to one store, "
                "using Sales.Store ID = Stores.ID. "
                "The left join preserves all selected sales rows."
            )


# ---------- CATEGORY REVENUE ----------

st.subheader("Revenue by Product Category")

# These labels are from the original course category mapping.
# Uploaded category and product relationships still need verification.
category_names = {
    "C1": "Beans",
    "C2": "Syrups",
    "C3": "Espresso Machines",
    "C4": "Accessories",
    "C5": "Frothers"
}

if "Category ID" in filtered_data.columns:
    category_data = filtered_data.copy()
    category_data["Category ID"] = (
        category_data["Category ID"].astype("string").str.strip()
    )

    category_data["Category"] = (
        category_data["Category ID"].map(category_names)
    )

    unknown_categories = category_data["Category"].isna()

    if unknown_categories.any():
        st.warning(
            f"{int(unknown_categories.sum()):,} sales rows have "
            "unmapped categories. Their IDs are shown where available."
        )

    category_data["Category"] = (
        category_data["Category"]
        .fillna(category_data["Category ID"])
        .fillna("Missing category")
    )

    category_revenue = (
        category_data.groupby("Category")["Revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    st.caption(f"Revenue for: {selected_year}")
    st.bar_chart(category_revenue)

    st.dataframe(
        category_revenue.to_frame().style.format(
            {"Revenue": "${:,.2f}"}
        )
    )

    st.caption(
        "Category labels currently use the original course mapping. "
        "Uploaded Products and Categories are previewed above; "
        "their relationships have not yet been connected."
    )

else:
    st.info(
        "Category analysis requires a Category ID column in sales. "
        "The Products relationship must be verified before deriving it."
    )


# ---------- SURVEY RESULTS ----------

st.subheader("Customer Survey Results")

if "Surveys" not in supporting_tables:
    st.info("Upload the survey results CSV to see this section.")

else:
    surveys = supporting_tables["Surveys"].copy()

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

        invalid_years = int(surveys["Year"].isna().sum())

        if invalid_years:
            st.warning(
                f"{invalid_years:,} survey rows have missing or "
                "invalid years and are excluded from this analysis."
            )

        surveys = surveys.dropna(subset=["Year"]).copy()

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
            "Missing or nonnumeric ratings are excluded from averages. "
            "Each available store-year rating receives equal weight."
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

            st.caption(
                f"Available satisfaction ratings: "
                f"{surveys['Satisfaction'].count():,} | "
                f"Available interest ratings: "
                f"{surveys['Interest'].count():,}. "
                "Missing responses may limit conclusions."
            )

            yearly_surveys = (
                surveys.groupby("Year")[["Satisfaction", "Interest"]]
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


# ---------- DATA QUALITY ----------

st.subheader("Data Quality Checks")
st.caption(
    "Counts cover the entire uploaded sales file, regardless of year filter."
)

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

duplicate_ids = None

if "Sales ID" in data.columns:
    sales_ids = (
        data["Sales ID"].astype("string").str.strip().replace("", pd.NA)
    )
    duplicate_ids = int(sales_ids.dropna().duplicated().sum())
    st.write(f"Repeated Sales IDs: {duplicate_ids:,}")
else:
    st.warning("Sales ID is missing, so ID uniqueness was not checked.")

if (
    missing_cells == 0
    and duplicate_rows == 0
    and negative_revenue == 0
    and duplicate_ids == 0
):
    st.success("No issues found in these sales checks.")
else:
    st.warning(
        "Review flagged records or unavailable checks. "
        "Negative revenue may represent returns; verify its meaning."
    )

st.write("**Supporting Table Missing Values and Duplicates**")

if supporting_tables:
    quality_rows = []

    for name, table in supporting_tables.items():
        cleaned = table.replace(r"^\s*$", pd.NA, regex=True)

        quality_rows.append({
            "Table": name,
            "Rows": len(table),
            "Missing Cells": int(cleaned.isna().sum().sum()),
            "Duplicate Rows": int(table.duplicated().sum())
        })

    st.dataframe(pd.DataFrame(quality_rows), hide_index=True)

    st.caption(
        "Missing values are reported, not automatically removed. "
        "For example, website location fields and survey ratings "
        "may be unavailable."
    )


# ---------- SALES PREVIEW ----------

with st.expander("Sales Data Preview — Selected Year(s)"):
    st.dataframe(filtered_data.head(20))
