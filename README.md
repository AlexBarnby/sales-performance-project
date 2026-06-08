# Company Sales Dashboard

A web dashboard for reviewing a company's worldwide sales: where the money and the profit
come from, what is selling in each market, how the catalogue performs line by line, and how
this year compares to the last. Built to be filtered, so the same view answers a question
about one country or the whole business.

## What it shows

- **Overview**: revenue, net profit, margin, units, and orders for the current filter, with revenue over time and the top products and continents.
- **Catalogue (P&L)**: every article with its cost price, sell price, units sold, revenue, and profit. Profit is shown two ways - a simple sell-minus-cost figure and a net figure that also takes off discounts and shipping - alongside the margin.
- **World Map**: sales shaded by country, switchable between revenue, profit, and units.
- **Regions**: revenue, profit, and margin grouped by continent or by business sub-region (DACH, Benelux, Balkans, and so on), plus what is selling in each.
- **Year-on-Year**: monthly revenue for each year side by side, with yearly totals and growth.
- **Forecast**: a three-month revenue projection.

## Filtering

Every tab responds to the sidebar filters: year, continent, sub-region, and country. They
work top-down - choosing a continent narrows the sub-regions and countries on offer - or on
their own. Leaving a filter blank includes everything, so the dashboard moves from a
company-wide view down to a single market without changing tab.

## How it works

The data sits in a relational database: a product catalogue with cost and sell prices, a
country table that maps each country to a sub-region and continent, and the orders and line
items themselves. Profit is derived at query time rather than stored, with each line carrying
its own discount and a share of its order's shipping so margins add up correctly at every
level - product, country, region, or year.

The analysis is done in SQL. A single view joins the line items out to product, country, and
date, and works out revenue, cost, and both profit measures once; the rest of the queries
aggregate that view for each tab. The interface is built in Streamlit, the world map with
Plotly, and the connection to the database runs through SQLAlchemy.

## Setup

```bash
pip install -r requirements.txt   # one time
python build_database.py          # one time, creates sales.db with sample data
streamlit run app.py              # starts the dashboard in the browser
```

It runs out of the box on a local SQLite database, so there is nothing to configure to see
it working. The sample data spans several years across more than forty countries.

## Running it on MySQL

The database is set by a single line in `connection.py`, so moving from SQLite to MySQL is a
small change:

1. In `connection.py`, comment out the SQLite line and uncomment the MySQL block, adding the password.
2. In `queries.py`, swap the SQLite date functions (`strftime`) for the MySQL equivalents (`YEAR()` and `DATE_FORMAT()`).
3. Run `python build_database.py`, then `streamlit run app.py`.

## Files

- `connection.py` - the database connection string, kept in one place
- `reference_data.py` - the country-to-region mapping and the product catalogue
- `build_database.py` - creates the database and sample data (run once)
- `queries.py` - all the SQL, including the profit logic and filtering
- `app.py` - the Streamlit dashboard
- `requirements.txt` - the libraries to install
