# All the dashboard's SQL. Each function takes the engine and a filters dict and
# returns a DataFrame.
#
# Profit is shown two ways:
#   gross_profit = (sell_price - cost_price) * quantity   (simple, price minus cost)
#   net_profit   = revenue - cogs - shipping              (after discount and shipping)
# revenue is always net of discount.

import pandas as pd

# One row per line item, joined out to product, country and date, with revenue,
# cost and both profit measures calculated once here.
FACTS = """
WITH facts AS (
    SELECT
        o.order_id,
        o.order_date,
        CAST(strftime('%Y', o.order_date) AS INTEGER) AS year,
        strftime('%Y-%m', o.order_date) AS month,
        c.country, c.iso3, c.sub_region, c.continent,
        p.product_id, p.article_no, p.product_name, p.category,
        p.cost_price, p.sell_price,
        od.quantity, od.discount,
        od.quantity * od.sell_price                          AS gross_revenue,
        od.quantity * od.sell_price * (1 - od.discount)      AS revenue,
        od.quantity * od.cost_price                          AS cogs,
        (od.sell_price - od.cost_price) * od.quantity        AS gross_profit,
        od.quantity * od.sell_price * (1 - od.discount)
            - od.quantity * od.cost_price - od.shipping_alloc AS net_profit
    FROM order_details od
    JOIN orders o     ON od.order_id = o.order_id
    JOIN products p   ON od.product_id = p.product_id
    JOIN countries c  ON o.country = c.country
)
"""


def _where(filters):
    # Build the WHERE clause from whichever filters are set. Values come from the
    # dropdowns, not free text; quotes are escaped just in case.
    clauses = []
    for column, key in [("year", "years"), ("continent", "continents"),
                        ("sub_region", "sub_regions"), ("country", "countries")]:
        values = filters.get(key)
        if values:
            if column == "year":
                joined = ", ".join(str(int(v)) for v in values)
            else:
                joined = ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
            clauses.append(f"{column} IN ({joined})")
    return ("WHERE " + " AND ".join(clauses)) if clauses else ""


def filter_options(engine):
    # Distinct values that populate the sidebar filters.
    return {
        "years": pd.read_sql("SELECT DISTINCT CAST(strftime('%Y', order_date) AS INTEGER) AS y FROM orders ORDER BY y", engine)["y"].tolist(),
        "continents": pd.read_sql("SELECT DISTINCT continent FROM countries ORDER BY continent", engine)["continent"].tolist(),
        "sub_regions": pd.read_sql("SELECT DISTINCT sub_region FROM countries ORDER BY sub_region", engine)["sub_region"].tolist(),
        "countries": pd.read_sql("SELECT DISTINCT country FROM countries ORDER BY country", engine)["country"].tolist(),
    }


def kpis(engine, filters):
    # Headline totals for the overview cards.
    query = FACTS + f"""
    SELECT
        ROUND(SUM(revenue), 0)              AS revenue,
        ROUND(SUM(net_profit), 0)           AS net_profit,
        ROUND(SUM(gross_profit), 0)         AS gross_profit,
        SUM(quantity)                       AS units,
        COUNT(DISTINCT order_id)            AS orders
    FROM facts
    {_where(filters)}
    """
    return pd.read_sql(query, engine).iloc[0]


def catalogue(engine, filters):
    # One row per article: cost, sell, units, revenue, both profit measures, margin.
    query = FACTS + f"""
    SELECT
        article_no, product_name, category,
        ROUND(cost_price, 2) AS cost_price,
        ROUND(sell_price, 2) AS sell_price,
        ROUND(sell_price - cost_price, 2) AS unit_profit,
        ROUND((sell_price - cost_price) / sell_price * 100, 1) AS unit_margin_pct,
        SUM(quantity) AS units_sold,
        ROUND(SUM(revenue), 0) AS revenue,
        ROUND(SUM(gross_profit), 0) AS gross_profit,
        ROUND(SUM(net_profit), 0) AS net_profit,
        ROUND(SUM(net_profit) / SUM(revenue) * 100, 1) AS net_margin_pct
    FROM facts
    {_where(filters)}
    GROUP BY article_no, product_name, category, cost_price, sell_price
    ORDER BY net_profit DESC
    """
    return pd.read_sql(query, engine)


def by_country(engine, filters):
    # Revenue and profit per country, keyed by ISO-3 code for the map.
    query = FACTS + f"""
    SELECT
        country, iso3, continent, sub_region,
        ROUND(SUM(revenue), 0) AS revenue,
        ROUND(SUM(net_profit), 0) AS net_profit,
        SUM(quantity) AS units
    FROM facts
    {_where(filters)}
    GROUP BY country, iso3, continent, sub_region
    ORDER BY revenue DESC
    """
    return pd.read_sql(query, engine)


def by_region(engine, filters, level):
    # Totals by continent or sub_region (level picks which).
    query = FACTS + f"""
    SELECT
        {level} AS region,
        ROUND(SUM(revenue), 0) AS revenue,
        ROUND(SUM(net_profit), 0) AS net_profit,
        ROUND(SUM(net_profit) / SUM(revenue) * 100, 1) AS net_margin_pct,
        COUNT(DISTINCT order_id) AS orders
    FROM facts
    {_where(filters)}
    GROUP BY {level}
    ORDER BY revenue DESC
    """
    return pd.read_sql(query, engine)


def products_by_region(engine, filters, level):
    # Revenue per product within each region - what is selling where.
    query = FACTS + f"""
    SELECT
        {level} AS region, category, product_name,
        ROUND(SUM(revenue), 0) AS revenue,
        SUM(quantity) AS units
    FROM facts
    {_where(filters)}
    GROUP BY {level}, category, product_name
    ORDER BY region, revenue DESC
    """
    return pd.read_sql(query, engine)


def yoy_monthly(engine, filters):
    # Revenue and profit by month within each year, for the year-on-year view.
    query = FACTS + f"""
    SELECT
        year,
        CAST(strftime('%m', order_date) AS INTEGER) AS month_no,
        ROUND(SUM(revenue), 0) AS revenue,
        ROUND(SUM(net_profit), 0) AS net_profit
    FROM facts
    {_where(filters)}
    GROUP BY year, month_no
    ORDER BY year, month_no
    """
    return pd.read_sql(query, engine)


def monthly_series(engine, filters):
    # Single monthly revenue series for the forecast.
    query = FACTS + f"""
    SELECT month, ROUND(SUM(revenue), 0) AS revenue
    FROM facts
    {_where(filters)}
    GROUP BY month
    ORDER BY month
    """
    return pd.read_sql(query, engine)
