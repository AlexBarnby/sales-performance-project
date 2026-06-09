# Company sales dashboard. Run with: streamlit run app.py
# Six tabs (overview, catalogue P&L, world map, regions, year-on-year, forecast),
# all driven by the sidebar filters.

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

from connection import connection_string
import queries as q

engine = create_engine(connection_string)

st.set_page_config(page_title="Sales Dashboard", page_icon="📊", layout="wide")

# Bump the base fonts up a bit - the defaults are hard to read.
st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown, p, label { font-size: 16px; }
[data-testid="stMetricValue"] { font-size: 30px; }
[data-testid="stMetricLabel"] { font-size: 16px; }
.stTabs [data-baseweb="tab"] { font-size: 16px; }
h1 { font-size: 30px; } h2 { font-size: 23px; } h3 { font-size: 19px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Company Sales Dashboard")

# A varied palette so bars and lines are easy to tell apart.
PALETTE = ["#2ec4b6", "#ff9f1c", "#e63946", "#4895ef", "#8338ec",
           "#06d6a0", "#ffd166", "#ef476f", "#118ab2", "#9bc53d"]


def style(fig, height=380):
    # Shared look for every Plotly chart: transparent, dark, readable fonts.
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=14), height=height, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


# Sidebar filters. Country and sub-region options narrow as you pick continents;
# leaving a filter blank includes everything.
ref = pd.read_sql("SELECT * FROM countries", engine)
opts = q.filter_options(engine)

st.sidebar.header("Filters")
years = st.sidebar.multiselect("Year", opts["years"])
continents = st.sidebar.multiselect("Continent", opts["continents"])

sub_pool = ref[ref["continent"].isin(continents)] if continents else ref
sub_regions = st.sidebar.multiselect("Sub-region", sorted(sub_pool["sub_region"].unique()))

country_pool = sub_pool[sub_pool["sub_region"].isin(sub_regions)] if sub_regions else sub_pool
countries = st.sidebar.multiselect("Country", sorted(country_pool["country"].unique()))

filters = {"years": years, "continents": continents, "sub_regions": sub_regions, "countries": countries}
st.sidebar.caption("Leave a filter blank to include everything.")

tabs = st.tabs(["Overview", "Catalogue (P&L)", "World Map", "Regions", "Year-on-Year", "Forecast"])

# Overview.
with tabs[0]:
    k = q.kpis(engine, filters)
    margin = k["net_profit"] / k["revenue"] * 100 if k["revenue"] else 0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Revenue", f"€{k['revenue']:,.0f}")
    c2.metric("Net Profit", f"€{k['net_profit']:,.0f}")
    c3.metric("Net Margin", f"{margin:.1f}%")
    c4.metric("Units Sold", f"{k['units']:,.0f}")
    c5.metric("Orders", f"{k['orders']:,.0f}")

    st.divider()
    st.subheader("Revenue over time")
    series = q.monthly_series(engine, filters)
    fig = px.line(series, x="month", y="revenue", markers=True, color_discrete_sequence=["#2ec4b6"])
    fig.update_traces(line=dict(width=2))
    st.plotly_chart(style(fig), use_container_width=True, key="ov_revenue_time")

    left, right = st.columns(2)
    with left:
        st.subheader("Top products by revenue")
        cat = q.catalogue(engine, filters).sort_values("revenue").tail(10)
        fig = px.bar(cat, x="revenue", y="product_name", orientation="h",
                     color="product_name", color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Revenue (€)")
        st.plotly_chart(style(fig), use_container_width=True, key="ov_top_products")
    with right:
        st.subheader("Revenue by continent")
        reg = q.by_region(engine, filters, "continent").sort_values("revenue")
        fig = px.bar(reg, x="revenue", y="region", orientation="h",
                     color="region", color_discrete_sequence=PALETTE)
        fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Revenue (€)")
        st.plotly_chart(style(fig), use_container_width=True, key="ov_revenue_continent")

# Catalogue (P&L).
with tabs[1]:
    st.subheader("Product catalogue and profitability")
    cat = q.catalogue(engine, filters)

    categories = st.multiselect("Category", sorted(cat["category"].unique()))
    if categories:
        cat = cat[cat["category"].isin(categories)]

    show = cat.rename(columns={
        "article_no": "Article", "product_name": "Product", "category": "Category",
        "cost_price": "Cost €", "sell_price": "Sell €", "unit_profit": "Unit Profit €",
        "unit_margin_pct": "Unit Margin %", "units_sold": "Units Sold", "revenue": "Revenue €",
        "gross_profit": "Gross Profit €", "net_profit": "Net Profit €", "net_margin_pct": "Net Margin %",
    })
    st.dataframe(show, hide_index=True, use_container_width=True)
    st.caption(
        "Gross Profit is the simple measure: (sell price − cost price) × units. "
        "Net Profit also takes off the discounts given and each line's share of shipping."
    )

    totals = cat[["revenue", "gross_profit", "net_profit"]].sum()
    t1, t2, t3 = st.columns(3)
    t1.metric("Revenue (shown)", f"€{totals['revenue']:,.0f}")
    t2.metric("Gross Profit (shown)", f"€{totals['gross_profit']:,.0f}")
    t3.metric("Net Profit (shown)", f"€{totals['net_profit']:,.0f}")

# World map.
with tabs[2]:
    st.subheader("Sales by country")
    metric = st.radio("Colour by", ["revenue", "net_profit", "units"], horizontal=True,
                      format_func=lambda m: {"revenue": "Revenue", "net_profit": "Net Profit", "units": "Units"}[m])
    cdf = q.by_country(engine, filters)
    fig = px.choropleth(
        cdf, locations="iso3", color=metric, hover_name="country",
        hover_data={"iso3": False, "revenue": ":,.0f", "net_profit": ":,.0f", "units": ":,.0f"},
        color_continuous_scale="Turbo",
    )
    fig.update_traces(marker_line_width=0.4, marker_line_color="rgba(255,255,255,0.4)")
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        geo=dict(showframe=False, bgcolor="rgba(0,0,0,0)", landcolor="#2a2a2a", showcountries=True,
                 countrycolor="rgba(255,255,255,0.15)"),
    )
    st.plotly_chart(fig, use_container_width=True, key="map_choropleth")

    st.subheader("Top countries")
    st.dataframe(
        cdf.head(15).rename(columns={
            "country": "Country", "continent": "Continent", "sub_region": "Sub-region",
            "revenue": "Revenue €", "net_profit": "Net Profit €", "units": "Units"}).drop(columns="iso3"),
        hide_index=True, use_container_width=True,
    )

# Regions.
with tabs[3]:
    level_label = st.radio("Group by", ["Continent", "Sub-region"], horizontal=True)
    level = "continent" if level_label == "Continent" else "sub_region"

    reg = q.by_region(engine, filters, level).sort_values("revenue")
    st.subheader(f"Revenue and profit by {level_label.lower()}")
    # Horizontal grouped bars so the region names read left-to-right, never vertical.
    long = reg.melt(id_vars="region", value_vars=["revenue", "net_profit"],
                    var_name="measure", value_name="value")
    long["measure"] = long["measure"].map({"revenue": "Revenue", "net_profit": "Net Profit"})
    fig = px.bar(long, x="value", y="region", color="measure", orientation="h", barmode="group",
                 color_discrete_sequence=["#4895ef", "#06d6a0"])
    fig.update_layout(yaxis_title="", xaxis_title="€", legend_title="")
    st.plotly_chart(style(fig, height=max(380, 40 * len(reg))), use_container_width=True, key="reg_revenue_profit")

    st.dataframe(
        reg.sort_values("revenue", ascending=False).rename(columns={
            "region": level_label, "revenue": "Revenue €", "net_profit": "Net Profit €",
            "net_margin_pct": "Net Margin %", "orders": "Orders"}),
        hide_index=True, use_container_width=True,
    )

    st.subheader(f"What is selling, by {level_label.lower()}")
    pbr = q.products_by_region(engine, filters, level)
    pick = st.selectbox(level_label, sorted(pbr["region"].unique()))
    top = pbr[pbr["region"] == pick].sort_values("revenue").tail(10)
    fig = px.bar(top, x="revenue", y="product_name", orientation="h",
                 color="product_name", color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False, yaxis_title="", xaxis_title="Revenue (€)")
    st.plotly_chart(style(fig), use_container_width=True, key="reg_products")

# Year-on-year.
with tabs[4]:
    st.subheader("Year-on-year revenue")
    yoy = q.yoy_monthly(engine, filters)
    if not yoy.empty:
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        yoy = yoy.copy()
        yoy["month_name"] = yoy["month_no"].map(lambda i: months[i - 1])
        fig = px.line(yoy.sort_values("month_no"), x="month_name", y="revenue",
                      color="year", markers=True, color_discrete_sequence=PALETTE)
        fig.update_layout(xaxis_title="", yaxis_title="Revenue (€)", legend_title="Year")
        fig.update_xaxes(categoryorder="array", categoryarray=months)
        st.plotly_chart(style(fig), use_container_width=True, key="yoy_lines")

        st.subheader("Yearly totals and growth")
        yearly = yoy.groupby("year")[["revenue", "net_profit"]].sum().reset_index()
        yearly["revenue_growth_%"] = (yearly["revenue"].pct_change() * 100).round(1)
        yearly["profit_growth_%"] = (yearly["net_profit"].pct_change() * 100).round(1)
        st.dataframe(
            yearly.rename(columns={"year": "Year", "revenue": "Revenue €", "net_profit": "Net Profit €",
                                   "revenue_growth_%": "Revenue Growth %", "profit_growth_%": "Profit Growth %"}),
            hide_index=True, use_container_width=True,
        )
        st.caption("The current year is still in progress, so its totals are partial.")
    else:
        st.info("No data for the current filters.")

# Forecast.
with tabs[5]:
    st.subheader("Three-month revenue forecast")
    series = q.monthly_series(engine, filters).set_index("month")["revenue"].astype(float)

    if len(series) >= 6:
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            if len(series) >= 24:
                model = ExponentialSmoothing(series, trend="add", seasonal="add", seasonal_periods=12)
            else:
                model = ExponentialSmoothing(series, trend="add")
            forecast = model.fit().forecast(3).clip(lower=0)
        except Exception:
            avg = series.tail(3).mean()
            forecast = pd.Series([avg, avg, avg])

        hist_x = list(range(len(series)))
        fc_x = list(range(len(series), len(series) + 3))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist_x, y=series.values, mode="lines+markers",
                                 name="Actual", line=dict(color="#2ec4b6", width=2)))
        fig.add_trace(go.Scatter(x=fc_x, y=forecast.values, mode="lines+markers",
                                 name="Forecast", line=dict(color="#ff9f1c", width=2, dash="dash")))
        fig.update_layout(xaxis_title="Month index", yaxis_title="Revenue (€)")
        st.plotly_chart(style(fig), use_container_width=True, key="forecast_chart")

        st.caption("Projected three months ahead from the monthly revenue trend and its seasonal pattern.")
        with st.expander("How this forecast works"):
            st.markdown(
                "I used exponential smoothing (the Holt-Winters method) to project the next three "
                "months. It works by giving recent months more weight than older ones, while also "
                "picking up the overall trend and the repeating seasonal pattern in the data, such "
                "as the regular autumn and Q4 lift. I chose it because it stays stable on a fairly "
                "short monthly series like this one.\n\n"
                "With more years of history, an AR or ARIMA model would be a natural next step. "
                "That would mean checking the series is stationary first (using the ACF and PACF "
                "plots) and then modelling the month-to-month autocorrelation directly, which can "
                "give a tighter forecast once there is enough data to support it."
            )
    else:
        st.info("Not enough months in the current filter to forecast. Widen the filters.")
