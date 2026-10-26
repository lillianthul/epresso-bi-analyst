import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="E-Presso Business Dashboard",
    page_icon="☕",
    layout="wide"
)

st.title("E-Presso Business Dashboard")
st.write(
    "Upload your E-Presso CSV files to explore business performance."
)


# ---------- HELPER FUNCTIONS ----------

def read_csv(file, text_only=False):
    file.seek(0)

    table = pd.read_csv(
        file,
        dtype=str if text_only else None,
        sep=None,
        engine="python"
    )

    table.columns = table.columns.str.strip()

    if table.columns.duplicated().any():
        raise ValueError("The file contains duplicate column names.")

    return table


def clean_text(series):
    return (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


def connect_lookup(sales, lookup, key, label, table_name):
    required = {key, label}
    missing = required - set(lookup.columns)

    if missing:
        st.error(
            f"{table_name} is missing: "
            f"{', '.join(sorted(missing))}"
        )
        return None

    if key not in sales.columns:
        st.error(f"Sales data is missing {key}.")
        return None

    lookup = lookup[[key, label]].copy()

    lookup[key] = clean_text(lookup[key])
    lookup[label] = clean_text(lookup[label])

    if lookup[key].isna().any():
        st.error(f"{table_name} contains missing {key} values.")
        return None

    if lookup[key].duplicated().any():
        st.error(
            f"{table_name} contains repeated {key} values. "
            "Fix these before joining to prevent duplicated revenue."
        )
        return None

    result = sales.drop(columns=[label], errors="ignore").copy()
    result[key] = clean_text(result[key])

    result = result.merge(
        lookup,
        on=key,
        how="left",
        validate="many_to_one"
    )

    missing_labels = result[label].isna()

    if missing_labels.any():
        st.warning(
            f"{int(missing_labels.sum()):,} selected sales rows "
            f"have no matching {label} name. "
            "Their IDs are shown where available."
        )

    result[label] = (
        result[label]
        .fillna(result[key])
        .fillna(f"Missing {label}")
    )

    return result


def show_revenue_breakdown(
    sales, lookup, key, label, table_name
):
    connected = connect_lookup(
        sales, lookup, key, label, table_name
    )

    if connected is None:
        return

    totals = (
        connected.groupby(label)["Revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(totals)

    st.dataframe(
        totals.to_frame().style.format(
            {"Revenue": "${:,.2f}"}
        )
    )

    st.caption(
        f"Relationship: many sales rows to one "
        f"{table_name} row using {key}. "
        "A left join preserves sales rows; "
        "unique lookup IDs prevent revenue duplication."
    )

    difference = (
        connected["Revenue"].sum() - sales["Revenue"].sum()
    )

    if abs(difference) < 0.005:
        st.caption(
            "Join check passed: revenue is unchanged after joining."
        )
    else:
        st.error(
            f"Join check failed: revenue changed by "
            f"${difference:,.2f}."
        )


# ---------- SALES UPLOAD ----------

uploaded_file = st.file_uploader(
    "Sales CSV",
    type="csv",
    key="sales_upload"
)

if uploaded_file is None:
    st.info("Upload epresso_sales.csv to get started.")
    st.stop()

try:
    data = read_csv(uploaded_file)

    missing = {"Revenue", "Date"} - set(data.columns)

    if missing:
        st.error(
            f"Sales file is missing: {', '.join(sorted(missing))}"
        )
        st.stop()

    if data.empty:
        st.warning("This file has no sales rows.")
        st.stop()

    data["Revenue"] = pd.to_numeric(
        data["Revenue"], errors="raise"
    )

    data["Date"] = pd.to_datetime(
        data["Date"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="raise"
    )

    if data[["Revenue", "Date"]].isna().any().any():
        st.error("Some dates or revenue values are missing.")
        st.stop()

    if not data["Revenue"].map(
        lambda value: float("-inf") < value < float("inf")
    ).all():
        st.error("Revenue contains infinite values.")
        st.stop()

except Exception as error:
    st.error(f"Could not process the sales file: {error}")
    st.stop()

st.success(
    f"Sales loaded: {len(data):,} rows | "
    f"{data.shape[1]} columns"
)


# ---------- SUPPORTING UPLOADS ----------

st.subheader("Supporting Data Tables")
st.write(
    "Upload your Stores, Products, Categories, "
    "and Surveys CSV files."
)

supporting_files = {
    "Stores": st.file_uploader(
        "Stores CSV",
        type="csv",
        key="stores_upload"
    ),
    "Products": st.file_uploader(
        "Products CSV",
        type="csv",
        key="products_upload"
    ),
    "Categories": st.file_uploader(
        "Categories CSV",
        type="csv",
        key="categories_upload"
    ),
    "Surveys": st.file_uploader(
        "Survey results CSV",
        type="csv",
        key="surveys_upload"
    ),
}

supporting_tables = {}

for table_name, file in supporting_files.items():
    if file is not None:
        try:
            table = read_csv(file, text_only=True)
            supporting_tables[table_name] = table

            st.success(
                f"{table_name}: {len(table):,} rows loaded"
            )

            with st.expander(f"Preview {table_name}"):
                st.dataframe(table.head(10))

        except Exception as error:
            st.error(
                f"Could not load {table_name}: {error}"
            )


# ---------- YEAR FILTER ----------

st.divider()
st.subheader("Dashboard Filters")

years = sorted(
    data["Date"].dt.year.unique().tolist()
)

selected_year = st.selectbox(
    "Choose a year",
    ["All years"] + years
)

if selected_year == "All years":
    filtered_data = data.copy()
else:
    filtered_data = data[
        data["Date"].dt.year == selected_year
    ].copy()


# ---------- SALES METRICS ----------

st.subheader("Sales Overview")

col1, col2 = st.columns(2)

col1.metric(
    f"Total Revenue — {selected_year}",
    f"${filtered_data['Revenue'].sum():,.2f}"
)

col2.metric(
    "Sales Rows",
    f"{len(filtered_data):,}"
)

st.caption(
    f"Period: {filtered_data['Date'].min():%b %Y} "
    f"to {filtered_data['Date'].max():%b %Y}. "
    "Revenue is not profit. "
    "Sales rows are not necessarily orders."
)


# ---------- ANNUAL REVENUE ----------

annual_revenue = (
    filtered_data.groupby(
        filtered_data["Date"].dt.year
    )["Revenue"]
    .sum()
    .sort_index()
)

annual_revenue.index = (
    annual_revenue.index.astype(str)
)
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

monthly_revenue.index = (
    monthly_revenue.index.astype(str)
)
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


# ---------- SALES CHANNEL REVENUE ----------

st.subheader("Revenue by Sales Channel")
st.caption(f"Revenue for: {selected_year}")

if "Stores" not in supporting_tables:
    st.info(
        "Upload the Stores CSV to calculate sales channels."
    )

else:
    stores = supporting_tables["Stores"].copy()

    if not {"ID", "StoreType"}.issubset(stores.columns):
        st.error(
            "Stores CSV needs ID and StoreType columns."
        )

    else:
        store_lookup = stores[
            ["ID", "StoreType"]
        ].rename(
            columns={
                "ID": "Store ID",
                "StoreType": "Sales Channel"
            }
        )

        show_revenue_breakdown(
            filtered_data,
            store_lookup,
            "Store ID",
            "Sales Channel",
            "Stores"
        )

        st.caption(
            "Source key: Sales.Store ID = Stores.ID."
        )


# ---------- CATEGORY REVENUE ----------

st.subheader("Revenue by Product Category")
st.caption(f"Revenue for: {selected_year}")

if "Categories" not in supporting_tables:
    st.info(
        "Upload the Categories CSV to see category revenue."
    )

else:
    show_revenue_breakdown(
        filtered_data,
        supporting_tables["Categories"],
        "Category ID",
        "Category",
        "Categories"
    )


# ---------- PRODUCT REVENUE ----------

st.subheader("Revenue by Product")
st.caption(f"Revenue for: {selected_year}")

if "Products" not in supporting_tables:
    st.info(
        "Upload the Products CSV to see product revenue."
    )

else:
    show_revenue_breakdown(
        filtered_data,
        supporting_tables["Products"],
        "Product ID",
        "Product",
        "Products"
    )


# ---------- CUSTOMER SURVEYS ----------

st.subheader("Customer Survey Results")

if "Surveys" not in supporting_tables:
    st.info(
        "Upload the survey results CSV to see this section."
    )

else:
    surveys = supporting_tables["Surveys"].copy()

    required = {
        "Year",
        "Satisfaction",
        "Interest"
    }

    missing = required - set(surveys.columns)

    if missing:
        st.error(
            f"Survey file is missing: "
            f"{', '.join(sorted(missing))}"
        )

    else:
        surveys["Year"] = pd.to_numeric(
            clean_text(surveys["Year"]).str.replace(
                r"^[Yy]", "", regex=True
            ),
            errors="coerce"
        )

        valid_year = (
            surveys["Year"].notna()
            & surveys["Year"].between(1, 9999)
            & surveys["Year"].mod(1).eq(0)
        )

        invalid_years = int((~valid_year).sum())

        if invalid_years:
            st.warning(
                f"{invalid_years:,} survey rows have "
                "missing or invalid years and are excluded."
            )

        surveys = surveys[valid_year].copy()

        for column in ["Satisfaction", "Interest"]:
            original = clean_text(surveys[column])

            numeric = pd.to_numeric(
                original, errors="coerce"
            )

            finite = numeric.map(
                lambda value: (
                    pd.notna(value)
                    and float("-inf") < value < float("inf")
                )
            )

            invalid_count = int(
                (original.notna() & ~finite).sum()
            )

            surveys[column] = numeric.where(finite)

            if invalid_count:
                st.warning(
                    f"{invalid_count:,} invalid {column} "
                    "values were excluded from averages."
                )

        if selected_year != "All years":
            surveys = surveys[
                surveys["Year"] == selected_year
            ].copy()

        st.caption(
            f"Survey results for: {selected_year}. "
            "Missing or invalid ratings are excluded. "
            "Each available store-year rating receives "
            "equal weight."
        )

        has_ratings = (
            surveys[["Satisfaction", "Interest"]]
            .notna()
            .any()
            .any()
        )

        if has_ratings:
            average_satisfaction = (
                surveys["Satisfaction"].mean()
            )

            average_interest = (
                surveys["Interest"].mean()
            )

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
                "Available satisfaction ratings: "
                f"{surveys['Satisfaction'].count():,} | "
                "Available interest ratings: "
                f"{surveys['Interest'].count():,}. "
                "Missing responses may limit conclusions."
            )

            yearly_surveys = (
                surveys.groupby("Year")[
                    ["Satisfaction", "Interest"]
                ]
                .mean()
                .sort_index()
            )

            yearly_surveys.index = (
                yearly_surveys.index
                .astype(int)
                .astype(str)
            )

            st.write(
                "**Average Satisfaction by Year**"
            )
            st.bar_chart(
                yearly_surveys["Satisfaction"]
            )

            st.write(
                "**Average Interest by Year**"
            )
            st.bar_chart(
                yearly_surveys["Interest"]
            )

            st.write(
                "**Annual Survey Averages**"
            )
            st.dataframe(
                yearly_surveys.style.format(
                    "{:.2f}",
                    na_rep="No data"
                )
            )

            st.caption(
                "Survey ratings are analyzed separately "
                "from sales to avoid repeating store-year "
                "ratings across sales rows."
            )

        else:
            st.info(
                "No numeric survey ratings "
                "for this selection."
            )


# ---------- SALES DATA QUALITY ----------

st.subheader("Data Quality Checks")
st.caption(
    "These sales checks cover the entire uploaded file, "
    "regardless of the year filter."
)

missing_cells = int(
    data.replace(
        r"^\s*$", pd.NA, regex=True
    )
    .isna()
    .sum()
    .sum()
)

duplicate_rows = int(
    data.duplicated().sum()
)

negative_revenue = int(
    (data["Revenue"] < 0).sum()
)

st.write(
    f"Missing values: {missing_cells:,}"
)
st.write(
    f"Duplicate rows: {duplicate_rows:,}"
)
st.write(
    f"Negative revenue records: {negative_revenue:,}"
)

duplicate_ids = None

if "Sales ID" in data.columns:
    sales_ids = clean_text(data["Sales ID"])

    duplicate_ids = int(
        sales_ids.dropna().duplicated().sum()
    )

    st.write(
        f"Repeated Sales IDs: {duplicate_ids:,}"
    )

else:
    st.warning(
        "Sales ID is missing, so ID uniqueness "
        "was not checked."
    )

if (
    missing_cells == 0
    and duplicate_rows == 0
    and negative_revenue == 0
    and duplicate_ids == 0
):
    st.success(
        "No issues found in these sales checks."
    )

else:
    st.warning(
        "Review flagged records or unavailable checks. "
        "Negative revenue may represent returns; "
        "verify its meaning."
    )


# ---------- SUPPORTING DATA QUALITY ----------

st.write(
    "**Supporting Table Missing Values and Duplicates**"
)

if supporting_tables:
    quality_rows = []

    for name, table in supporting_tables.items():
        cleaned = table.replace(
            r"^\s*$", pd.NA, regex=True
        )

        quality_rows.append({
            "Table": name,
            "Rows": len(table),
            "Missing Cells": int(
                cleaned.isna().sum().sum()
            ),
            "Duplicate Rows": int(
                table.duplicated().sum()
            )
        })

    st.dataframe(
        pd.DataFrame(quality_rows),
        hide_index=True
    )

    st.caption(
        "Missing values are reported, "
        "not automatically removed. "
        "Website location fields and survey ratings "
        "may be unavailable."
    )

    survey_source = supporting_tables.get("Surveys")

    if survey_source is not None:
        if {"Store ID", "Year"}.issubset(
            survey_source.columns
        ):
            survey_keys = pd.DataFrame({
                "Store ID": clean_text(
                    survey_source["Store ID"]
                ),
                "Year": clean_text(
                    survey_source["Year"]
                ).str.replace(
                    r"^[Yy]", "", regex=True
                )
            })

            complete_keys = (
                survey_keys.notna().all(axis=1)
            )

            repeated_survey_keys = int(
                survey_keys.loc[complete_keys]
                .duplicated()
                .sum()
            )

            st.write(
                "Repeated survey store-year combinations: "
                f"{repeated_survey_keys:,}"
            )

            if repeated_survey_keys:
                st.warning(
                    "Review repeated survey store-year "
                    "combinations before interpreting averages."
                )


# ---------- RELATIONSHIP NOTES ----------

with st.expander("Data Relationships and Assumptions"):
    st.markdown(
        """
- Sales revenue is summed from the uploaded Revenue column.
- Sales connects to Stores using Sales.Store ID = Stores.ID.
- Sales connects to Products using Product ID.
- Sales connects to Categories using Category ID.
- Each lookup key must be unique before joining.
- Left joins retain sales rows with unmatched lookup values.
- Products and Categories connect separately to Sales.
- Surveys are analyzed separately at the store-year level.
- Survey averages give equal weight to available ratings.
- Revenue alone cannot establish profit.
        """
    )


# ---------- SALES PREVIEW ----------

with st.expander(
    "Sales Data Preview — Selected Year(s)"
):
    st.dataframe(filtered_data.head(20))
