import streamlit as st
import pandas as pd

st.title("E-Presso Business Dashboard")
st.write("Upload an E-Presso CSV file to preview your data.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        data = pd.read_csv(uploaded_file, sep=None, engine="python")

        st.success("File loaded successfully!")
        st.write(f"Rows: {data.shape[0]} | Columns: {data.shape[1]}")
        st.dataframe(data.head(20))

        if "StoreType" in data.columns:
            st.subheader("Number of Records by Store Type")
            counts = data["StoreType"].value_counts()
            st.bar_chart(counts)

    except Exception as error:
        st.error(f"Could not read this file: {error}")
