# E-Presso Business Intelligence Dashboard

Interactive E-Presso business intelligence dashboard and analytical assistant built with Python and Streamlit.

## Project Overview

This project analyzes E-Presso sales, store, product, category, and customer survey data through an interactive Streamlit dashboard. The application was designed to reproduce and validate business intelligence results originally developed in Power BI while allowing users to upload updated data and automatically recalculate results.

The application also includes a rules-based analytical assistant that uses approved analytical functions to answer business questions using the currently loaded data.

## Data Sources

The dashboard uses five E-Presso datasets:

- Sales
- Stores
- Products
- Categories
- Customer Surveys

The sales dataset contains 25,200 sales records covering January 2025 through December 2029.

## Data Grain

The grain of each dataset was reviewed before combining the tables to help prevent duplicated or incorrectly aggregated revenue.

| Table | One Row Represents | Key Column(s) | Row Count | Contains Revenue? |
| --- | --- | --- | ---: | --- |
| Sales | One sales record for a specific date, store, product, and category | Sales ID | 25,200 | Yes |
| Stores | One E-Presso store or sales location | ID | 21 | No |
| Products | One E-Presso product | Product ID | 20 | No |
| Categories | One product category | Category ID | 5 | No |
| Customer Surveys | One survey record for a store and year | Store ID + Year / Store-Year | 105 | No |

Because these tables have different levels of detail, they are not combined simply because columns have similar names. Sales is the primary revenue table. Stores, Products, and Categories are used as lookup tables, while customer survey data remains separate at the store-year level.

Before and after the lookup tables are joined to Sales, the application checks that the number of sales records and total revenue remain consistent. This helps identify joins that could accidentally duplicate or remove revenue.

## Dashboard Features

The Streamlit dashboard includes:

- Total revenue KPI
- Sales row count
- Year filter
- Revenue by year
- Revenue by month
- Revenue by sales channel
- Revenue by product category
- Revenue by product
- Customer satisfaction analysis
- Customer interest analysis
- Data-quality checks
- Supporting-table validation
- Data relationship and assumption documentation
- Interactive data previews

All calculations respond to the currently uploaded data rather than relying on hard-coded totals.

## Data Relationships

The application uses the following relationships:

- Sales.Store ID → Stores.ID
- Sales.Product ID → Products.Product ID
- Sales.Category ID → Categories.Category ID

Lookup keys are checked for uniqueness before joining. Left joins are used to preserve sales records, and revenue totals are checked after joins to detect accidental duplication.

Customer survey data is analyzed separately at the store-year level to avoid repeating survey ratings across individual sales records.

## Data Quality

The application checks the uploaded sales data for:

- Missing values
- Duplicate rows
- Negative revenue records
- Repeated Sales IDs

Supporting tables are also checked for missing values and duplicate rows.

Missing values are reported rather than automatically removed. This avoids silently changing the meaning of the source data.

## Power BI Validation

Streamlit results were compared against the Power BI baseline.

Validated results included:

| Metric | Power BI | Streamlit |
| --- | ---: | ---: |
| Total Revenue | $42,174,440 | $42,174,440 |
| 2025 Revenue | $7,181,750 | $7,181,750 |
| 2026 Revenue | $8,016,950 | $8,016,950 |
| 2027 Revenue | $8,824,720 | $8,824,720 |
| 2028 Revenue | $8,969,470 | $8,969,470 |
| 2029 Revenue | $9,181,550 | $9,181,550 |
| Website Revenue | $27,218,880 | $27,218,880 |
| Brick & Mortar Revenue | $14,955,560 | $14,955,560 |

Product-category revenue and monthly revenue patterns were also compared between Power BI and Streamlit and matched.

An independent Excel calculation was performed using the Revenue column. Excel returned total revenue of $42,174,440, matching both Power BI and Streamlit.

## Updated-Data Validation

To verify that the application responds dynamically to uploaded data, one revenue value was increased by exactly $1,000.

Original revenue value:

$6,780

Modified revenue value:

$7,780

Original total revenue:

$42,174,440

Expected modified total revenue:

$42,175,440

Actual modified total revenue:

$42,175,440

The affected 2025 annual revenue and Website sales-channel revenue also increased by $1,000. Brick & Mortar revenue remained unchanged as expected.

The modified dataset was uploaded without changing the Python code or restarting the application. The original dataset was restored after testing.

## Analytical Assistant

The application includes an E-Presso Analytical Assistant that answers business questions using approved analytical functions and the currently loaded dashboard data.

The assistant is implemented as a rules-based analytical assistant (Option B). It routes supported questions to approved analytical functions rather than generating and executing arbitrary analytical code.

The assistant can analyze:

- Total revenue
- Revenue by sales channel
- Product category performance
- Data quality

The assistant uses the same year selection as the dashboard so users can analyze either all years or a selected year.

Assistant responses identify the current analysis scope and are organized into:

- Findings
- Interpretation
- Next Steps

For supported questions, the assistant displays a Tool-Call Log showing the analytical function, arguments, and raw result.

The assistant has a 15-question session limit and identifies unsupported questions rather than generating unsupported calculations or conclusions.

## Analytical Functions

The assistant uses approved functions including:

- `get_total_revenue()`
- `get_revenue_by_channel()`
- `get_category_performance()`
- `get_data_quality_report()`

The assistant does not generate or execute arbitrary Python code.

## Tool-Call Transparency

For supported analytical questions, the application provides a visible Tool-Call Log showing:

- Function used
- Arguments
- Raw function result
- Definition
- Analysis scope
- Rows used
- Relevant caveats

This makes the calculation process visible and helps demonstrate that numerical answers come from the currently loaded application data.

## Analytical Limitations

The application distinguishes between findings supported by the data and conclusions that cannot be reliably made.

Revenue cannot establish profitability because the available data does not include all necessary cost and expense information. When asked which store is most profitable, the assistant identifies this limitation rather than treating revenue as profit.

The assistant also does not claim that an observed relationship proves causation. Observational data may show associations, but those associations do not by themselves establish causal relationships.

Questions that cannot be answered using the available data or approved analytical functions are identified as unsupported rather than answered using invented calculations.

## Assistant Testing

The analytical assistant was evaluated using the required test categories:

1. Numerical calculation — total revenue
2. Numerical comparison — sales-channel revenue
3. Missing information — store profitability
4. Analytical judgment — whether customer satisfaction causes higher revenue
5. Updated-data test — total revenue after a $1,000 revenue modification

All five required tests passed.

An additional edge-case question asked which store generated the most revenue. Because store-level revenue was not included in the assistant's approved analytical functions, the assistant correctly identified the request as unsupported rather than inventing a result. This confirmed the robustness of the unsupported-question handling.

During development, the assistant interface was also improved to more closely match the required analytical structure. Responses were updated to clearly display Scope, Findings, Interpretation, and Next Steps, the Tool-Call Log was expanded, and the session question limit was increased to 15. Numerical questions were retested after these changes and continued to return the validated results.

The updated-data test confirmed that the assistant uses the currently uploaded data rather than hard-coded results.

## Technologies

- Python
- Streamlit
- pandas
- GitHub
- Power BI

## Usage

1. Open the Streamlit application.
2. Upload the E-Presso Sales CSV.
3. Upload the Stores, Products, Categories, and Surveys CSV files.
4. Select a year or choose All years.
5. Review dashboard metrics and visualizations.
6. Use the E-Presso Analytical Assistant to ask supported business questions.
7. Expand the Tool-Call Log to inspect the analytical function, arguments, and raw result.

## Important Interpretation Notes

Revenue is not the same as profit.

Sales rows are not necessarily equivalent to customer orders.

Missing survey responses may limit conclusions.

Survey averages give equal weight to available store-year ratings.

Analytical conclusions should remain within the limits of the available data.
