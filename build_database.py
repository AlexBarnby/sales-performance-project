# Builds the sales database with sample data. Run once before launching the app.
# Tables: products, customers, countries, orders, order_details.
# Each line item stores its sell price, cost price, discount and shipping share,
# so profit can be worked out at any level later.

import random
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine

from connection import connection_string
from reference_data import COUNTRIES, PRODUCTS

engine = create_engine(connection_string)
random.seed(42)

# Reference tables.
countries_df = pd.DataFrame(COUNTRIES, columns=["country", "iso3", "sub_region", "continent", "weight"])
products_df = pd.DataFrame(PRODUCTS, columns=["article_no", "product_name", "category", "cost_price", "sell_price"])
products_df.insert(0, "product_id", range(1, len(products_df) + 1))

# Customers, spread across countries by each country's weight.
country_pool = []
for c in COUNTRIES:
    country_pool += [c[0]] * c[4]
customers = [{"customer_id": i, "customer_name": f"Customer {i:04d}", "country": random.choice(country_pool)}
             for i in range(1, 401)]
customers_df = pd.DataFrame(customers)

# Orders across roughly 3.5 years so year-on-year has something to compare.
# Monthly multiplier adds seasonality; yearly factor grows the later years.
season = {1: 0.9, 2: 0.9, 3: 1.0, 4: 1.05, 5: 1.05, 6: 0.9,
          7: 0.8, 8: 0.8, 9: 1.1, 10: 1.2, 11: 1.3, 12: 1.45}
yearly_growth = {2023: 0.85, 2024: 1.0, 2025: 1.18, 2026: 1.30}

orders, order_details = [], []
order_id, detail_id = 1, 1
day = date(2023, 1, 1)
end = date.today()

while day <= end:
    base = random.choices([1, 2, 3, 4, 5], weights=[15, 30, 30, 18, 7])[0]
    n_orders = int(round(base * season[day.month] * yearly_growth.get(day.year, 1.0)))

    for _ in range(n_orders):
        customer = random.choice(customers)
        shipping_cost = round(random.uniform(8, 45), 2)

        # Build the lines first so shipping can be split across them by value.
        lines = []
        for _ in range(random.choices([1, 2, 3, 4], weights=[45, 30, 17, 8])[0]):
            product = products_df.sample(1).iloc[0]
            quantity = random.randint(1, 8)
            discount = random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2])
            line_revenue = quantity * product["sell_price"] * (1 - discount)
            lines.append({
                "product_id": int(product["product_id"]), "quantity": quantity,
                "sell_price": float(product["sell_price"]), "cost_price": float(product["cost_price"]),
                "discount": discount, "line_revenue": line_revenue,
            })

        total_rev = sum(l["line_revenue"] for l in lines) or 1
        orders.append({"order_id": order_id, "order_date": day.isoformat(),
                       "customer_id": customer["customer_id"], "country": customer["country"],
                       "shipping_cost": shipping_cost})

        for l in lines:
            order_details.append({
                "detail_id": detail_id, "order_id": order_id, "product_id": l["product_id"],
                "quantity": l["quantity"], "sell_price": l["sell_price"], "cost_price": l["cost_price"],
                "discount": l["discount"],
                # Shipping split by this line's share of the order's revenue.
                "shipping_alloc": round(shipping_cost * l["line_revenue"] / total_rev, 2),
            })
            detail_id += 1
        order_id += 1
    day += timedelta(days=1)

orders_df = pd.DataFrame(orders)
order_details_df = pd.DataFrame(order_details)

# Write every table.
countries_df.to_sql("countries", engine, if_exists="replace", index=False)
products_df.to_sql("products", engine, if_exists="replace", index=False)
customers_df.to_sql("customers", engine, if_exists="replace", index=False)
orders_df.to_sql("orders", engine, if_exists="replace", index=False)
order_details_df.to_sql("order_details", engine, if_exists="replace", index=False)

print(f"Database built: {len(orders_df)} orders, {len(order_details_df)} line items, "
      f"{len(countries_df)} countries, {len(products_df)} products.")
