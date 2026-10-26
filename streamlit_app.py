st.subheader("Revenue by Month")
st.caption(f"Monthly totals for: {selected_year}")

monthly_revenue = (
    filtered_data.groupby(
        filtered_data["Date"].dt.to_period("M")
    )["Revenue"]
    .sum()
    .sort_index()
)

monthly_revenue.index = monthly_revenue.index.astype(str)
monthly_revenue.index.name = "Month"
monthly_revenue.name = "Revenue ($)"

st.line_chart(monthly_revenue)
