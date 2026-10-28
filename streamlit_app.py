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


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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


# ============================================================
# ANALYTICAL FUNCTIONS FOR ASSISTANT
# ============================================================

def get_revenue_by_channel(sales, stores):
    required_store_columns = {"ID", "StoreType"}

    if not required_store_columns.issubset(stores.columns):
        return {
            "error": "Stores data is missing ID or StoreType."
        }

    if "Store ID" not in sales.columns:
        return {
            "error": "Sales data is missing Store ID."
        }

    store_lookup = stores[
        ["ID", "StoreType"]
    ].rename(
        columns={
            "ID": "Store ID",
            "StoreType": "Sales Channel"
        }
    )

    lookup = store_lookup.copy()

    lookup["Store ID"] = clean_text(lookup["Store ID"])
    lookup["Sales Channel"] = clean_text(
        lookup["Sales Channel"]
    )

    if lookup["Store ID"].isna().any():
        return {
            "error": "Stores data contains missing IDs."
        }

    if lookup["Store ID"].duplicated().any():
        return {
            "error": "Stores data contains repeated IDs."
        }

    working_sales = sales.copy()
    working_sales["Store ID"] = clean_text(
        working_sales["Store ID"]
    )

    connected = working_sales.merge(
        lookup,
        on="Store ID",
        how="left",
        validate="many_to_one"
    )

    totals = (
        connected.groupby(
            "Sales Channel",
            dropna=False
        )["Revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    result = {}

    for channel, revenue in totals.items():
        label = (
            "Unknown"
            if pd.isna(channel)
            else str(channel)
        )
        result[label] = round(float(revenue), 2)

    return result


def get_category_performance(sales, categories):
    required = {"Category ID", "Category"}

    if not required.issubset(categories.columns):
        return {
            "error": (
                "Categories data is missing "
                "Category ID or Category."
            )
        }

    if "Category ID" not in sales.columns:
        return {
            "error": "Sales data is missing Category ID."
        }

    lookup = categories[
        ["Category ID", "Category"]
    ].copy()

    lookup["Category ID"] = clean_text(
        lookup["Category ID"]
    )
    lookup["Category"] = clean_text(
        lookup["Category"]
    )

    if lookup["Category ID"].isna().any():
        return {
            "error": "Categories data contains missing IDs."
        }

    if lookup["Category ID"].duplicated().any():
        return {
            "error": "Categories data contains repeated IDs."
        }

    working_sales = sales.copy()
    working_sales["Category ID"] = clean_text(
        working_sales["Category ID"]
    )

    connected = working_sales.merge(
        lookup,
        on="Category ID",
        how="left",
        validate="many_to_one"
    )

    totals = (
        connected.groupby(
            "Category",
            dropna=False
        )["Revenue"]
        .sum()
        .sort_values(ascending=False)
    )

    result = {}

    for category, revenue in totals.items():
        label = (
            "Unknown"
            if pd.isna(category)
            else str(category)
        )
        result[label] = round(float(revenue), 2)

    return result


def get_data_quality_report(sales):
    missing_cells = int(
        sales.replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )
        .isna()
        .sum()
        .sum()
    )

    duplicate_rows = int(
        sales.duplicated().sum()
    )

    negative_revenue = int(
        (sales["Revenue"] < 0).sum()
    )

    repeated_sales_ids = None

    if "Sales ID" in sales.columns:
        sales_ids = clean_text(
            sales["Sales ID"]
        )

        repeated_sales_ids = int(
            sales_ids.dropna()
            .duplicated()
            .sum()
        )

    return {
        "missing_values": missing_cells,
        "duplicate_rows": duplicate_rows,
        "negative_revenue_records": negative_revenue,
        "repeated_sales_ids": repeated_sales_ids
    }


def get_total_revenue(sales):
    return {
        "total_revenue": round(
            float(sales["Revenue"].sum()),
            2
        )
    }



def tool_contract(tool, value, definition, scope, rows_used, caveats):
    return {
        "tool": tool,
        "value": value,
        "definition": definition,
        "scope": scope,
        "rows_used": int(rows_used),
        "caveats": caveats
    }


# ============================================================
# ASSISTANT DISPATCHER
# ============================================================

def analytical_dispatcher(
    question,
    sales,
    supporting_tables
):
    question_lower = question.lower().strip()

    # Profit questions should not be answered
    # using revenue alone.
    if (
        "profit" in question_lower
        or "profitable" in question_lower
        or "profitability" in question_lower
    ):
        return {
            "supported": False,
            "function": None,
            "arguments": {},
            "raw_result": None,
            "answer": (
                "The available data cannot reliably determine "
                "profitability. The dashboard contains revenue, "
                "but profitability would also require information "
                "such as expenses, product costs, labor costs, "
                "rent, and other operating costs."
            )
        }

    # Causation questions
    if (
        "cause" in question_lower
        or "causes" in question_lower
        or "caused" in question_lower
    ):
        return {
            "supported": False,
            "function": None,
            "arguments": {},
            "raw_result": None,
            "answer": (
                "The available observational data cannot establish "
                "causation. It may be possible to examine an "
                "association between variables, but an association "
                "does not prove that one variable caused another."
            )
        }

    # Sales channel
    if (
        "channel" in question_lower
        or "website" in question_lower
        or "brick" in question_lower
    ):
        if "Stores" not in supporting_tables:
            return {
                "supported": False,
                "function": "get_revenue_by_channel",
                "arguments": {},
                "raw_result": None,
                "answer": (
                    "I cannot calculate revenue by sales channel "
                    "until the Stores CSV is uploaded."
                )
            }

        result = get_revenue_by_channel(
            sales,
            supporting_tables["Stores"]
        )

        if "error" in result:
            return {
                "supported": False,
                "function": "get_revenue_by_channel",
                "arguments": {},
                "raw_result": result,
                "answer": result["error"]
            }

        if not result:
            answer = (
                "No sales-channel revenue could be calculated "
                "from the current data."
            )
        else:
            ordered = sorted(
                result.items(),
                key=lambda item: item[1],
                reverse=True
            )

            details = ", ".join(
                f"{name}: ${value:,.2f}"
                for name, value in ordered
            )

            top_name, top_value = ordered[0]

            answer = (
                f"{details}. "
                f"{top_name} generated the most revenue at "
                f"${top_value:,.2f}. "
                "These figures describe revenue, not profit."
            )

        return {
            "supported": True,
            "function": "get_revenue_by_channel",
            "arguments": {
                "data_scope": "current dashboard selection"
            },
            "raw_result": result,
            "answer": answer
        }

    # Product categories
    if (
        "category" in question_lower
        or "categories" in question_lower
    ):
        if "Categories" not in supporting_tables:
            return {
                "supported": False,
                "function": "get_category_performance",
                "arguments": {},
                "raw_result": None,
                "answer": (
                    "I cannot calculate category performance "
                    "until the Categories CSV is uploaded."
                )
            }

        result = get_category_performance(
            sales,
            supporting_tables["Categories"]
        )

        if "error" in result:
            return {
                "supported": False,
                "function": "get_category_performance",
                "arguments": {},
                "raw_result": result,
                "answer": result["error"]
            }

        if not result:
            answer = (
                "No product-category revenue could be calculated "
                "from the current data."
            )
        else:
            ordered = sorted(
                result.items(),
                key=lambda item: item[1],
                reverse=True
            )

            details = ", ".join(
                f"{name}: ${value:,.2f}"
                for name, value in ordered
            )

            top_name, top_value = ordered[0]

            answer = (
                f"{details}. "
                f"The highest-revenue category is {top_name} "
                f"at ${top_value:,.2f}. "
                "Revenue does not establish category profitability."
            )

        return {
            "supported": True,
            "function": "get_category_performance",
            "arguments": {
                "data_scope": "current dashboard selection"
            },
            "raw_result": result,
            "answer": answer
        }

    # Data quality
    if (
        "quality" in question_lower
        or "missing" in question_lower
        or "duplicate" in question_lower
        or "negative" in question_lower
    ):
        result = get_data_quality_report(sales)

        repeated = result["repeated_sales_ids"]

        repeated_text = (
            "not checked"
            if repeated is None
            else f"{repeated:,}"
        )

        answer = (
            f"The current sales data contains "
            f"{result['missing_values']:,} missing values, "
            f"{result['duplicate_rows']:,} duplicate rows, "
            f"{result['negative_revenue_records']:,} negative "
            f"revenue records, and {repeated_text} repeated "
            f"Sales IDs."
        )

        return {
            "supported": True,
            "function": "get_data_quality_report",
            "arguments": {
                "data_scope": "current dashboard selection"
            },
            "raw_result": result,
            "answer": answer
        }

    # Total revenue
    if (
        "total revenue" in question_lower
        or (
            "revenue" in question_lower
            and "total" in question_lower
        )
    ):
        result = get_total_revenue(sales)

        total = result["total_revenue"]

        answer = (
            f"Total revenue for the current dashboard selection "
            f"is ${total:,.2f}. "
            "Revenue is not the same as profit."
        )

        return {
            "supported": True,
            "function": "get_total_revenue",
            "arguments": {
                "data_scope": "current dashboard selection"
            },
            "raw_result": result,
            "answer": answer
        }

    return {
        "supported": False,
        "function": None,
        "arguments": {},
        "raw_result": None,
        "answer": (
            "I cannot reliably answer that question with the "
            "approved analytical functions currently available. "
            "Try asking about total revenue, sales channels, "
            "product categories, or data quality."
        )
    }


# ============================================================
# SALES UPLOAD
# ============================================================

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
            f"Sales file is missing: "
            f"{', '.join(sorted(missing))}"
        )
        st.stop()

    if data.empty:
        st.warning("This file has no sales rows.")
        st.stop()

    data["Revenue"] = pd.to_numeric(
        data["Revenue"],
        errors="raise"
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


# ============================================================
# SUPPORTING UPLOADS
# ============================================================

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
            table = read_csv(
                file,
                text_only=True
            )

            supporting_tables[table_name] = table

            st.success(
                f"{table_name}: "
                f"{len(table):,} rows loaded"
            )

            with st.expander(
                f"Preview {table_name}"
            ):
                st.dataframe(
                    table.head(10)
                )

        except Exception as error:
            st.error(
                f"Could not load {table_name}: "
                f"{error}"
            )


# ============================================================
# YEAR FILTER
# ============================================================

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


# ============================================================
# SALES METRICS
# ============================================================

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
    f"Period: "
    f"{filtered_data['Date'].min():%b %Y} "
    f"to {filtered_data['Date'].max():%b %Y}. "
    "Revenue is not profit. "
    "Sales rows are not necessarily orders."
)


# ============================================================
# ANNUAL REVENUE
# ============================================================

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
st.caption(
    f"Revenue for: {selected_year}"
)

st.bar_chart(
    annual_revenue
)

with st.expander(
    "Annual Revenue Totals"
):
    st.dataframe(
        annual_revenue
        .to_frame()
        .style
        .format(
            {"Revenue": "${:,.2f}"}
        )
    )


# ============================================================
# MONTHLY REVENUE
# ============================================================

monthly_revenue = (
    filtered_data.groupby(
        filtered_data["Date"]
        .dt.to_period("M")
    )["Revenue"]
    .sum()
    .sort_index()
)

monthly_revenue.index = (
    monthly_revenue.index.astype(str)
)

monthly_revenue.index.name = "Month"

st.subheader("Revenue by Month")
st.caption(
    f"Monthly totals for: {selected_year}"
)

st.line_chart(
    monthly_revenue
)

with st.expander(
    "Monthly Revenue Details"
):
    st.dataframe(
        monthly_revenue
        .to_frame()
        .style
        .format(
            {"Revenue": "${:,.2f}"}
        )
    )


# ============================================================
# SALES CHANNEL REVENUE
# ============================================================

st.subheader("Revenue by Sales Channel")
st.caption(
    f"Revenue for: {selected_year}"
)

if "Stores" not in supporting_tables:
    st.info(
        "Upload the Stores CSV "
        "to calculate sales channels."
    )

else:
    stores = (
        supporting_tables["Stores"]
        .copy()
    )

    if not {
        "ID",
        "StoreType"
    }.issubset(stores.columns):

        st.error(
            "Stores CSV needs ID "
            "and StoreType columns."
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
            "Source key: "
            "Sales.Store ID = Stores.ID."
        )


# ============================================================
# CATEGORY REVENUE
# ============================================================

st.subheader(
    "Revenue by Product Category"
)

st.caption(
    f"Revenue for: {selected_year}"
)

if "Categories" not in supporting_tables:
    st.info(
        "Upload the Categories CSV "
        "to see category revenue."
    )

else:
    show_revenue_breakdown(
        filtered_data,
        supporting_tables["Categories"],
        "Category ID",
        "Category",
        "Categories"
    )


# ============================================================
# PRODUCT REVENUE
# ============================================================

st.subheader(
    "Revenue by Product"
)

st.caption(
    f"Revenue for: {selected_year}"
)

if "Products" not in supporting_tables:
    st.info(
        "Upload the Products CSV "
        "to see product revenue."
    )

else:
    show_revenue_breakdown(
        filtered_data,
        supporting_tables["Products"],
        "Product ID",
        "Product",
        "Products"
    )


# ============================================================
# CUSTOMER SURVEYS
# ============================================================

st.subheader(
    "Customer Survey Results"
)

if "Surveys" not in supporting_tables:
    st.info(
        "Upload the survey results CSV "
        "to see this section."
    )

else:
    surveys = (
        supporting_tables["Surveys"]
        .copy()
    )

    required = {
        "Year",
        "Satisfaction",
        "Interest"
    }

    missing = (
        required - set(surveys.columns)
    )

    if missing:
        st.error(
            f"Survey file is missing: "
            f"{', '.join(sorted(missing))}"
        )

    else:
        surveys["Year"] = pd.to_numeric(
            clean_text(
                surveys["Year"]
            ).str.replace(
                r"^[Yy]",
                "",
                regex=True
            ),
            errors="coerce"
        )

        valid_year = (
            surveys["Year"].notna()
            & surveys["Year"].between(
                1,
                9999
            )
            & surveys["Year"].mod(1).eq(0)
        )

        invalid_years = int(
            (~valid_year).sum()
        )

        if invalid_years:
            st.warning(
                f"{invalid_years:,} survey rows "
                "have missing or invalid years "
                "and are excluded."
            )

        surveys = surveys[
            valid_year
        ].copy()

        for column in [
            "Satisfaction",
            "Interest"
        ]:
            original = clean_text(
                surveys[column]
            )

            numeric = pd.to_numeric(
                original,
                errors="coerce"
            )

            finite = numeric.map(
                lambda value: (
                    pd.notna(value)
                    and float("-inf")
                    < value
                    < float("inf")
                )
            )

            invalid_count = int(
                (
                    original.notna()
                    & ~finite
                ).sum()
            )

            surveys[column] = (
                numeric.where(finite)
            )

            if invalid_count:
                st.warning(
                    f"{invalid_count:,} invalid "
                    f"{column} values were "
                    "excluded from averages."
                )

        if selected_year != "All years":
            surveys = surveys[
                surveys["Year"]
                == selected_year
            ].copy()

        st.caption(
            f"Survey results for: "
            f"{selected_year}. "
            "Missing or invalid ratings "
            "are excluded. "
            "Each available store-year rating "
            "receives equal weight."
        )

        has_ratings = (
            surveys[
                [
                    "Satisfaction",
                    "Interest"
                ]
            ]
            .notna()
            .any()
            .any()
        )

        if has_ratings:
            average_satisfaction = (
                surveys[
                    "Satisfaction"
                ].mean()
            )

            average_interest = (
                surveys[
                    "Interest"
                ].mean()
            )

            col1, col2 = st.columns(2)

            col1.metric(
                "Average Satisfaction",
                (
                    f"{average_satisfaction:.2f}"
                    if pd.notna(
                        average_satisfaction
                    )
                    else "No data"
                )
            )

            col2.metric(
                "Average Interest",
                (
                    f"{average_interest:.2f}"
                    if pd.notna(
                        average_interest
                    )
                    else "No data"
                )
            )

            st.caption(
                "Available satisfaction ratings: "
                f"{surveys['Satisfaction'].count():,} | "
                "Available interest ratings: "
                f"{surveys['Interest'].count():,}. "
                "Missing responses may limit "
                "conclusions."
            )

            yearly_surveys = (
                surveys.groupby(
                    "Year"
                )[
                    [
                        "Satisfaction",
                        "Interest"
                    ]
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
                "**Average Satisfaction "
                "by Year**"
            )

            st.bar_chart(
                yearly_surveys[
                    "Satisfaction"
                ]
            )

            st.write(
                "**Average Interest "
                "by Year**"
            )

            st.bar_chart(
                yearly_surveys[
                    "Interest"
                ]
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
                "Survey ratings are analyzed "
                "separately from sales to avoid "
                "repeating store-year ratings "
                "across sales rows."
            )

        else:
            st.info(
                "No numeric survey ratings "
                "for this selection."
            )


# ============================================================
# SALES DATA QUALITY
# ============================================================

st.subheader(
    "Data Quality Checks"
)

st.caption(
    "These sales checks cover the entire "
    "uploaded file, regardless of the "
    "year filter."
)

missing_cells = int(
    data.replace(
        r"^\s*$",
        pd.NA,
        regex=True
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
    f"Missing values: "
    f"{missing_cells:,}"
)

st.write(
    f"Duplicate rows: "
    f"{duplicate_rows:,}"
)

st.write(
    f"Negative revenue records: "
    f"{negative_revenue:,}"
)

duplicate_ids = None

if "Sales ID" in data.columns:
    sales_ids = clean_text(
        data["Sales ID"]
    )

    duplicate_ids = int(
        sales_ids
        .dropna()
        .duplicated()
        .sum()
    )

    st.write(
        f"Repeated Sales IDs: "
        f"{duplicate_ids:,}"
    )

else:
    st.warning(
        "Sales ID is missing, "
        "so ID uniqueness was not checked."
    )

if (
    missing_cells == 0
    and duplicate_rows == 0
    and negative_revenue == 0
    and duplicate_ids == 0
):
    st.success(
        "No issues found in "
        "these sales checks."
    )

else:
    st.warning(
        "Review flagged records or "
        "unavailable checks. "
        "Negative revenue may represent "
        "returns; verify its meaning."
    )


# ============================================================
# SUPPORTING DATA QUALITY
# ============================================================

st.write(
    "**Supporting Table Missing Values "
    "and Duplicates**"
)

if supporting_tables:
    quality_rows = []

    for name, table in (
        supporting_tables.items()
    ):
        cleaned = table.replace(
            r"^\s*$",
            pd.NA,
            regex=True
        )

        quality_rows.append({
            "Table": name,
            "Rows": len(table),
            "Missing Cells": int(
                cleaned
                .isna()
                .sum()
                .sum()
            ),
            "Duplicate Rows": int(
                table
                .duplicated()
                .sum()
            )
        })

    st.dataframe(
        pd.DataFrame(
            quality_rows
        ),
        hide_index=True
    )

    st.caption(
        "Missing values are reported, "
        "not automatically removed. "
        "Website location fields and "
        "survey ratings may be unavailable."
    )

    survey_source = (
        supporting_tables.get(
            "Surveys"
        )
    )

    if survey_source is not None:
        if {
            "Store ID",
            "Year"
        }.issubset(
            survey_source.columns
        ):
            survey_keys = pd.DataFrame({
                "Store ID": clean_text(
                    survey_source[
                        "Store ID"
                    ]
                ),
                "Year": clean_text(
                    survey_source[
                        "Year"
                    ]
                ).str.replace(
                    r"^[Yy]",
                    "",
                    regex=True
                )
            })

            complete_keys = (
                survey_keys
                .notna()
                .all(axis=1)
            )

            repeated_survey_keys = int(
                survey_keys.loc[
                    complete_keys
                ]
                .duplicated()
                .sum()
            )

            st.write(
                "Repeated survey store-year "
                "combinations: "
                f"{repeated_survey_keys:,}"
            )

            if repeated_survey_keys:
                st.warning(
                    "Review repeated survey "
                    "store-year combinations "
                    "before interpreting averages."
                )


# ============================================================
# RELATIONSHIP NOTES
# ============================================================

with st.expander(
    "Data Relationships and Assumptions"
):
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


# ============================================================
# ANALYTICAL ASSISTANT
# ============================================================

st.divider()

st.header(
    "E-Presso Analytical Assistant"
)

st.write(
    "Ask a business question about the currently "
    "loaded data. The assistant uses approved "
    "analytical functions rather than generating "
    "or executing arbitrary code."
)

st.caption(
    f"Current analysis scope: {selected_year}. "
    "The assistant uses the same year selection "
    "as the dashboard."
)

if "assistant_question_count" not in st.session_state:
    st.session_state[
        "assistant_question_count"
    ] = 0

question_limit = 15

questions_remaining = (
    question_limit
    - st.session_state[
        "assistant_question_count"
    ]
)

st.caption(
    f"Questions remaining this session: "
    f"{questions_remaining}"
)

question = st.text_input(
    "Ask the analytical assistant",
    placeholder=(
        "Example: Which sales channel "
        "generated the most revenue?"
    )
)

ask_button = st.button(
    "Analyze Question"
)

if ask_button:
    if not question.strip():
        st.warning(
            "Enter a business question first."
        )

    elif (
        st.session_state[
            "assistant_question_count"
        ]
        >= question_limit
    ):
        st.error(
            "The session question limit has "
            "been reached. This limit helps "
            "control assistant usage."
        )

    else:
        st.session_state[
            "assistant_question_count"
        ] += 1

        response = analytical_dispatcher(
            question,
            filtered_data,
            supporting_tables
        )

        scope_info = {
            "year": str(selected_year),
            "data_source": "currently uploaded E-Presso files"
        }

        if response["supported"] and response["function"]:
            raw_value = response["raw_result"]
            definitions = {
                "get_total_revenue": "Sum of Revenue for the current dashboard selection.",
                "get_revenue_by_channel": "Sum of sales revenue grouped by sales channel.",
                "get_category_performance": "Sum of sales revenue grouped by product category.",
                "get_data_quality_report": "Counts missing values, duplicate rows, negative revenue records, and repeated Sales IDs."
            }
            caveats = {
                "get_total_revenue": ["Revenue is not profit.", "Results reflect the currently uploaded data."],
                "get_revenue_by_channel": ["Revenue is not profit.", "Results reflect the currently uploaded data."],
                "get_category_performance": ["Revenue does not establish category profitability.", "Results reflect the currently uploaded data."],
                "get_data_quality_report": ["Negative revenue may represent returns and should be interpreted in context."]
            }
            response["raw_result"] = tool_contract(
                response["function"],
                raw_value,
                definitions.get(response["function"], "Approved analytical calculation."),
                scope_info,
                len(filtered_data),
                caveats.get(response["function"], [])
            )

        st.subheader(
            "Assistant Response"
        )

        st.markdown(
            f"**Scope:** {selected_year} — currently uploaded data"
        )

        st.markdown("### Findings")
        st.write(response["answer"])

        st.markdown("### Interpretation")
        if response["supported"]:
            if response["function"] == "get_total_revenue":
                st.write(
                    "This total is calculated directly from the Revenue "
                    "column for the current dashboard selection."
                )
            elif response["function"] == "get_revenue_by_channel":
                st.write(
                    "The channel comparison identifies which sales channel "
                    "generated the most revenue in the current scope."
                )
            elif response["function"] == "get_category_performance":
                st.write(
                    "The category comparison identifies which product "
                    "categories contributed the most revenue in the current scope."
                )
            elif response["function"] == "get_data_quality_report":
                st.write(
                    "These checks help identify records that may affect "
                    "the reliability or interpretation of the analysis."
                )
            else:
                st.write(
                    "The finding is based on an approved calculation using "
                    "the currently loaded data."
                )
        else:
            st.write(
                "The requested conclusion is not supported by the available "
                "data or approved analytical functions, so the assistant "
                "does not guess."
            )

        st.markdown("### Next Steps")
        if response["supported"]:
            if response["function"] in {
                "get_total_revenue",
                "get_revenue_by_channel",
                "get_category_performance"
            }:
                st.write(
                    "Use this result as a revenue finding only. Revenue is "
                    "not profit, so cost and expense information would be "
                    "needed for profitability recommendations."
                )
            else:
                st.write(
                    "Review any flagged records and confirm their business "
                    "meaning before changing or removing data."
                )
        else:
            st.write(
                "Try asking about total revenue, sales channels, product "
                "categories, or data quality. No recommendation is supported "
                "when the required information is unavailable."
            )

        if response["supported"]:
            st.caption(
                "Finding: calculated from the currently loaded data "
                "using an approved analytical function."
            )
        else:
            st.caption(
                "Limitation: the requested conclusion is not supported "
                "by the available approved analytical functions or data."
            )

        with st.expander(
            "Tool-Call Log"
        ):
            st.write(
                "**Function used:**"
            )

            if response["function"]:
                st.code(
                    response["function"]
                )
            else:
                st.write(
                    "No analytical function "
                    "was executed."
                )

            st.write(
                "**Arguments:**"
            )

            st.json(
                response["arguments"]
            )

            st.write(
                "**Raw result:**"
            )

            if (
                response["raw_result"]
                is not None
            ):
                st.json(
                    response[
                        "raw_result"
                    ]
                )
            else:
                st.write(
                    "No numerical result "
                    "was produced."
                )


# ============================================================
# SALES PREVIEW
# ============================================================

with st.expander(
    "Sales Data Preview — Selected Year(s)"
):
    st.dataframe(
        filtered_data.head(20)
    )
