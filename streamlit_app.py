import streamlit as st
import pandas as pd

st.title("E-Presso Business Dashboard")
st.write("Upload your E-Presso sales CSV to explore revenue.")

uploaded_file = st.file_uploader("Choose a sales CSV file", type="csv")

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file, sep=None, engine="python")

        required_columns = {"Revenue", "Date"}
        missing_columns = required_columns - set(data.columns)

        if missing_columns:
            st.error(f"Missing required columns: {', '.join(sorted(missing_columns))}")
            st.stop()

        data["Revenue"] = pd.to_numeric(data["Revenue"], errors="raise")
        data["Date"] = pd.to_datetime(
            data["Date"],
            format="%m/%d/%Y %I:%M:%S %p",
            errors="raise"
        )

        if data[["Revenue", "Date"]].isna().any().any():
            st.error("Some dates or revenue values are missing. Check your file.")
            st.stop()

        if data.empty:
            st.warning("This file has no sales rows.")
            st.stop()

        st.success("File loaded successfully!")
        st.write(f"Rows: {data.shape[0]} | Columns: {data.shape[1]}")

        st.subheader("Total Revenue")
        st.metric(
            "Revenue — all uploaded sales",
            f"${data['Revenue'].sum():,.2f}"
        )

        st.caption(
            f"Period: {data['Date'].min():%b %Y} "
            f"to {data['Date'].max():%b %Y}. Revenue is not profit."
        )

        annual_revenue = (
            data.groupby(data["Date"].dt.year)["Revenue"]
            .sum()
            .sort_index()
        )
        annual_revenue.index = annual_revenue.index.astype(str)
        annual_revenue.index.name = "Year"
        annual_revenue.name = "Revenue ($)"

        st.subheader("Revenue by Year")
        st.bar_chart(annual_revenue)

        st.subheader("Annual Revenue Totals")
        st.dataframe(
            annual_revenue.to_frame().style.format("${:,.2f}")
        )

        st.subheader("Data Preview")
        st.dataframe(data.head(20))

    except Exception as error:
        st.error(f"Could not process this file: {error}")
else:
    st.info("Upload epresso_sales.csv to get started.")
