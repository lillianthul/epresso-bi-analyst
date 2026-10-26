import streamlit as st
import pandas as pd

st.title("E-Presso Business Dashboard")
st.write("Upload your E-Presso sales CSV to preview data and calculate revenue.")

uploaded_file = st.file_uploader("Choose a sales CSV file", type="csv")

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file, sep=None, engine="python")

        if "Revenue" not in data.columns:
            st.error("Please upload the sales file containing a Revenue column.")
        else:
            data["Revenue"] = pd.to_numeric(data["Revenue"], errors="raise")

            if data["Revenue"].isna().any():
                st.error("Some revenue values are missing. Check your file.")
            else:
                st.success("File loaded successfully!")
                st.write(f"Rows: {data.shape[0]} | Columns: {data.shape[1]}")

                st.subheader("Total Revenue")
                st.metric(
                    "Revenue — all uploaded sales",
                    f"${data['Revenue'].sum():,.2f}"
                )

                st.subheader("Data Preview")
                st.dataframe(data.head(20))

    except Exception as error:
        st.error(f"Could not process this file: {error}")
else:
    st.info("Upload epresso_sales.csv to get started.")
