"""
generate_samples.py
--------------------
Generates realistic, MESSY sample CSVs for 10 Indian e-commerce
platforms, so you can test the dashboard's auto-mapping and cleaning
logic without needing to find/download real datasets for every one.

Each platform's generator uses different column names, date formats,
and price formatting -- on purpose -- to stress-test the schema
mapping engine in app.py.

Run with:
    python generate_samples.py

Output: sample_data/<platform>_sample.csv (10 files)
"""

import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = "sample_data"
N_ROWS = 200

CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune",
          "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Surat", "Indore"]
STATES = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Tamil Nadu",
          "Maharashtra", "West Bengal", "Gujarat", "Rajasthan", "Uttar Pradesh"]


def random_dates(n, start, end, fmt):
    """Generate n random dates between start and end, formatted as strings."""
    delta = (end - start).days
    dates = [start + timedelta(days=random.randint(0, delta)) for _ in range(n)]
    return [d.strftime(fmt) for d in dates]


def messy_price(value):
    """Randomly format a numeric price as messy text (currency symbols, commas, refunds)."""
    style = random.choice(["inr_symbol", "rs_prefix", "plain_comma", "refund"])
    if style == "inr_symbol":
        return f"\u20b9{value:,.2f}"
    elif style == "rs_prefix":
        return f"Rs. {value:,.0f}"
    elif style == "refund" and random.random() < 0.05:
        return f"({value:,.0f})"  # occasional refund/negative
    else:
        return f"{value:,.0f}"


def save(df: pd.DataFrame, name: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"{name}_sample.csv")
    df.to_csv(path, index=False)
    print(f"Saved {path}  ({len(df)} rows, {len(df.columns)} cols)")


# ---------------------------------------------------------------
# 1. Myntra -- Fashion & Apparel
# ---------------------------------------------------------------
def generate_myntra():
    prices = np.random.normal(1200, 500, N_ROWS).clip(199, 5000)
    df = pd.DataFrame({
        "order_created_at": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%d/%m/%Y"),
        "Order No": [f"MYN{1000+i}" for i in range(N_ROWS)],
        "Product Name": [random.choice(["Cotton Shirt", "Denim Jeans", "Running Shoes", "Casual Kurta", "Formal Blazer"]) for _ in range(N_ROWS)],
        "Category": [random.choice(["Men Fashion", "Women Fashion", "Footwear", "Ethnic Wear"]) for _ in range(N_ROWS)],
        "Item_Total": [messy_price(p) for p in prices],
        "Qty": np.random.randint(1, 4, N_ROWS),
        "Ship City": [random.choice(CITIES) for _ in range(N_ROWS)],
        "order_status": [random.choice(["Delivered", "Shipped", "Cancelled", "Returned"]) for _ in range(N_ROWS)],
    })
    save(df, "myntra")


# ---------------------------------------------------------------
# 2. Flipkart -- Electronics & Mobiles
# ---------------------------------------------------------------
def generate_flipkart():
    prices = np.random.normal(15000, 8000, N_ROWS).clip(999, 80000)
    df = pd.DataFrame({
        "Order Date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%Y-%m-%d"),
        "order_id": [f"OD{200000+i}" for i in range(N_ROWS)],
        "product_title": [random.choice(["Smartphone 128GB", "Bluetooth Earbuds", "Laptop 15.6in", "Smartwatch", "Power Bank 20000mAh"]) for _ in range(N_ROWS)],
        "sub_category": [random.choice(["Mobiles", "Audio", "Computers", "Wearables"]) for _ in range(N_ROWS)],
        "selling_price": [messy_price(p) for p in prices],
        "units": np.random.randint(1, 3, N_ROWS),
        "delivery_city": [random.choice(CITIES) for _ in range(N_ROWS)],
        "delivery_status": [random.choice(["Delivered", "In Transit", "Cancelled"]) for _ in range(N_ROWS)],
    })
    save(df, "flipkart")


# ---------------------------------------------------------------
# 3. Amazon India -- Order/Sales Report
# ---------------------------------------------------------------
def generate_amazon():
    prices = np.random.normal(800, 400, N_ROWS).clip(99, 4000)
    df = pd.DataFrame({
        "Date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%m-%d-%y"),
        "Order ID": [f"402-{random.randint(1000000,9999999)}-{random.randint(1000000,9999999)}" for _ in range(N_ROWS)],
        "Style": [random.choice(["JNE3797", "SET268", "J0230", "JNE3405"]) for _ in range(N_ROWS)],
        "Category": [random.choice(["Kurta", "Set", "Western Dress", "Top"]) for _ in range(N_ROWS)],
        "Amount": [messy_price(p) for p in prices],
        "Qty": np.random.randint(1, 3, N_ROWS),
        "ship-state": [random.choice(STATES) for _ in range(N_ROWS)],
        "Status": [random.choice(["Shipped", "Shipped - Delivered to Buyer", "Cancelled", "Pending"]) for _ in range(N_ROWS)],
    })
    save(df, "amazon_india")


# ---------------------------------------------------------------
# 4. Meesho -- Reseller Orders
# ---------------------------------------------------------------
def generate_meesho():
    prices = np.random.normal(400, 150, N_ROWS).clip(99, 1500)
    df = pd.DataFrame({
        "sub_order_no": [f"MSH{300000+i}" for i in range(N_ROWS)],
        "order_date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%d-%m-%Y"),
        "product_name": [random.choice(["Printed Saree", "Kids Frock", "Men T-Shirt", "Artificial Jewellery Set"]) for _ in range(N_ROWS)],
        "category": [random.choice(["Saree", "Kids Wear", "Men Wear", "Jewellery"]) for _ in range(N_ROWS)],
        "discounted_price": [messy_price(p) for p in prices],
        "quantity": np.random.randint(1, 5, N_ROWS),
        "customer_state": [random.choice(STATES) for _ in range(N_ROWS)],
        "reason_for_credit_entry": [random.choice(["Delivered", "RTO Complete", "Cancelled"]) for _ in range(N_ROWS)],
    })
    save(df, "meesho")


# ---------------------------------------------------------------
# 5. Shopsy -- Daily Orders
# ---------------------------------------------------------------
def generate_shopsy():
    prices = np.random.normal(350, 120, N_ROWS).clip(79, 1200)
    df = pd.DataFrame({
        "transaction_date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%Y-%m-%dT%H:%M:%SZ"),
        "invoice_no": [f"SHP{500000+i}" for i in range(N_ROWS)],
        "item_desc": [random.choice(["Phone Case", "Home Decor Item", "Kitchen Gadget", "Stationery Set"]) for _ in range(N_ROWS)],
        "final_price": [messy_price(p) for p in prices],
        "no_of_items": np.random.randint(1, 4, N_ROWS),
        "region": [random.choice(CITIES) for _ in range(N_ROWS)],
    })
    save(df, "shopsy")


# ---------------------------------------------------------------
# 6. Snapdeal -- Product Sales & Discount
# ---------------------------------------------------------------
def generate_snapdeal():
    prices = np.random.normal(900, 400, N_ROWS).clip(149, 3500)
    df = pd.DataFrame({
        "Invoice Date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%d/%m/%Y"),
        "Transaction Id": [f"SD{600000+i}" for i in range(N_ROWS)],
        "Item Name": [random.choice(["Wall Clock", "Backpack", "Sunglasses", "Wireless Mouse"]) for _ in range(N_ROWS)],
        "Type": [random.choice(["Home Decor", "Bags", "Accessories", "Computer Peripherals"]) for _ in range(N_ROWS)],
        "MRP": [messy_price(p) for p in prices],
        "Order Qty": np.random.randint(1, 3, N_ROWS),
        "Courier Status": [random.choice(["Delivered", "Undelivered", "RTO"]) for _ in range(N_ROWS)],
    })
    save(df, "snapdeal")


# ---------------------------------------------------------------
# 7. Nykaa -- Beauty & Cosmetics
# ---------------------------------------------------------------
def generate_nykaa():
    prices = np.random.normal(650, 300, N_ROWS).clip(99, 3000)
    df = pd.DataFrame({
        "purchase_date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%Y/%m/%d"),
        "order_number": [f"NYK{700000+i}" for i in range(N_ROWS)],
        "sku_name": [random.choice(["Matte Lipstick", "Face Serum", "Sunscreen SPF50", "Eyeliner", "Perfume 50ml"]) for _ in range(N_ROWS)],
        "department": [random.choice(["Makeup", "Skincare", "Fragrance"]) for _ in range(N_ROWS)],
        "sale_price": [messy_price(p) for p in prices],
        "unit_sold": np.random.randint(1, 3, N_ROWS),
        "ship_state": [random.choice(STATES) for _ in range(N_ROWS)],
    })
    save(df, "nykaa")


# ---------------------------------------------------------------
# 8. Ajio -- Fashion & Lifestyle
# ---------------------------------------------------------------
def generate_ajio():
    prices = np.random.normal(1500, 700, N_ROWS).clip(299, 6000)
    df = pd.DataFrame({
        "invoice_date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%d-%b-%Y"),
        "order_id": [f"AJO{800000+i}" for i in range(N_ROWS)],
        "title": [random.choice(["Slim Fit Trousers", "Graphic Tee", "Leather Jacket", "Ethnic Kurti"]) for _ in range(N_ROWS)],
        "segment": [random.choice(["Men", "Women", "Kids"]) for _ in range(N_ROWS)],
        "total_amount": [messy_price(p) for p in prices],
        "order_qty": np.random.randint(1, 3, N_ROWS),
        "city": [random.choice(CITIES) for _ in range(N_ROWS)],
        "fulfillment_status": [random.choice(["Delivered", "Processing", "Cancelled"]) for _ in range(N_ROWS)],
    })
    save(df, "ajio")


# ---------------------------------------------------------------
# 9. Blinkit / Zepto -- Quick Commerce Grocery
# ---------------------------------------------------------------
def generate_blinkit():
    prices = np.random.normal(250, 150, N_ROWS).clip(20, 1200)
    df = pd.DataFrame({
        "order_time": random_dates(N_ROWS, datetime(2023, 6, 1), datetime(2023, 12, 31), "%Y-%m-%d %H:%M:%S"),
        "order_id": [f"BLK{900000+i}" for i in range(N_ROWS)],
        "item_name": [random.choice(["Milk 1L", "Bread Loaf", "Onions 1kg", "Instant Noodles Pack", "Cold Drink 750ml"]) for _ in range(N_ROWS)],
        "product_category": [random.choice(["Dairy", "Bakery", "Vegetables", "Packaged Food", "Beverages"]) for _ in range(N_ROWS)],
        "price": [messy_price(p) for p in prices],
        "quantity": np.random.randint(1, 6, N_ROWS),
        "delivery_city": [random.choice(CITIES) for _ in range(N_ROWS)],
    })
    save(df, "blinkit_zepto")


# ---------------------------------------------------------------
# 10. Tata CLiQ -- Multi-Category Transactions
# ---------------------------------------------------------------
def generate_tata_cliq():
    prices = np.random.normal(2200, 1200, N_ROWS).clip(299, 15000)
    df = pd.DataFrame({
        "Order_Date": random_dates(N_ROWS, datetime(2023, 1, 1), datetime(2023, 12, 31), "%d.%m.%Y"),
        "OrderNumber": [f"TC{100000+i}" for i in range(N_ROWS)],
        "ItemDescription": [random.choice(["Home Theatre System", "Designer Watch", "Air Fryer", "Formal Shoes", "Handbag"]) for _ in range(N_ROWS)],
        "ProductCategory": [random.choice(["Electronics", "Fashion", "Home Appliances", "Accessories"]) for _ in range(N_ROWS)],
        "MRP": [messy_price(p) for p in prices],
        "Units": np.random.randint(1, 3, N_ROWS),
        "Address": [f"{random.choice(CITIES)}, {random.choice(STATES)}" for _ in range(N_ROWS)],
        "OrderStatus": [random.choice(["Delivered", "Shipped", "Returned", "Cancelled"]) for _ in range(N_ROWS)],
    })
    save(df, "tata_cliq")


if __name__ == "__main__":
    generate_myntra()
    generate_flipkart()
    generate_amazon()
    generate_meesho()
    generate_shopsy()
    generate_snapdeal()
    generate_nykaa()
    generate_ajio()
    generate_blinkit()
    generate_tata_cliq()
    print("\nAll 10 sample files generated in sample_data/")
