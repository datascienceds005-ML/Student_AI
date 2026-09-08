"""
app.py
------
Universal E-Commerce Automated Analytics Dashboard

Upload ANY raw e-commerce sales export (Myntra, Flipkart, Amazon India,
Meesho, Shopsy, etc.) and this app will:
    1. Auto-detect which columns map to standard fields (with manual
       fallback if detection isn't confident enough).
    2. Clean messy currency/number formatting and inconsistent dates.
    3. Compute top-level KPIs.
    4. Let you build charts on demand from whatever columns exist.
    5. Export the cleaned, standardized dataset.

Run with:
    streamlit run app.py
"""

import io
import re
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# =====================================================================
# 1. SCHEMA MAPPING ENGINE
# =====================================================================
# Every platform names its columns differently. Instead of hardcoding
# per-platform logic, we define ONE set of "standard" internal fields,
# and a dictionary of keywords/aliases that are likely to appear in a
# raw column header for each standard field. Detection is keyword +
# similarity based (no external ML dependency needed -- keeps this
# deployable on Hugging Face Spaces free tier without heavy libraries).

STANDARD_FIELDS = [
    "Order_Date",
    "Order_ID",
    "Product_Title",
    "Category",
    "Price",
    "Quantity",
    "City_State",
    "Status",
]

# Keywords are matched against a LOWERCASED, UNDERSCORE-NORMALIZED
# version of each raw column header. Order matters only within a field
# (first match wins during scoring), not across fields.
FIELD_KEYWORDS = {
    "Order_Date": [
        "order_date", "order_created_at", "orderdate", "date", "created_at",
        "purchase_date", "order_time", "invoice_date", "transaction_date",
    ],
    "Order_ID": [
        "order_id", "orderid", "order_no", "order_number", "invoice_id",
        "invoice_no", "transaction_id", "sub_order_no",
    ],
    "Product_Title": [
        "product_title", "product_name", "item_name", "title", "sku_name",
        "product", "item_desc", "description", "style",
    ],
    "Category": [
        "category", "sub_category", "product_category", "segment", "type",
        "department",
    ],
    "Price": [
        "selling_price", "item_total", "discounted_price", "price", "amount",
        "sales", "sale_price", "total_amount", "revenue", "final_price",
        "unit_price", "mrp",
    ],
    "Quantity": [
        "quantity", "qty", "units", "unit_sold", "order_qty", "no_of_items",
    ],
    "City_State": [
        "city", "state", "ship_state", "ship_city", "delivery_city",
        "location", "region", "address",
    ],
    "Status": [
        "status", "order_status", "delivery_status", "fulfillment_status",
        "courier_status",
    ],
}


def _normalize(col_name: str) -> str:
    """Lowercase and replace spaces/dashes with underscores for matching."""
    return re.sub(r"[\s\-]+", "_", str(col_name).strip().lower())


def _similarity(a: str, b: str) -> float:
    """Simple fuzzy similarity score between two strings (0-1)."""
    return SequenceMatcher(None, a, b).ratio()


def auto_detect_schema(columns: list) -> dict:
    """
    Attempt to map each raw column to a standard field.

    Returns:
        dict of {standard_field: (best_raw_column_or_None, confidence_score)}

    Strategy: score every (field, raw_column) pair using substring
    matches (high confidence) or fuzzy string similarity (fallback for
    near-misses like 'discountedprice' vs 'discounted_price'). Then
    assign greedily by descending score, so each raw column is used for
    AT MOST ONE standard field -- otherwise a single ambiguous column
    (e.g. "Order No" fuzzy-matching both Order_ID and Status) could get
    assigned to multiple fields at once.
    """
    normalized = {col: _normalize(col) for col in columns}
    candidates = []  # (field, raw_col, score)

    for field, keywords in FIELD_KEYWORDS.items():
        for raw_col, norm_col in normalized.items():
            best_score = 0.0
            for kw in keywords:
                if kw in norm_col or norm_col in kw:
                    score = 1.0  # substring match = high confidence
                else:
                    score = _similarity(kw, norm_col)
                if score > best_score:
                    best_score = score
            candidates.append((field, raw_col, best_score))

    # Highest-confidence matches get first pick of both field and column.
    candidates.sort(key=lambda x: x[2], reverse=True)

    mapping = {field: (None, 0.0) for field in FIELD_KEYWORDS}
    used_columns = set()
    assigned_fields = set()

    for field, raw_col, score in candidates:
        if field in assigned_fields or raw_col in used_columns:
            continue
        mapping[field] = (raw_col, round(score, 2))
        used_columns.add(raw_col)
        assigned_fields.add(field)

    return mapping


# =====================================================================
# 2. DATA CLEANING ENGINE
# =====================================================================

def clean_numeric_column(series: pd.Series) -> pd.Series:
    """
    Coerce a messy numeric column (currency symbols, commas, stray text,
    negative refunds in parentheses) into clean floats.

    Handles formats like:
        "Rs. 1,299.00"  ->  1299.00
        "$45.99"        ->  45.99
        "(250)"         ->  -250.0   (accounting-style negative)
        "1,20,000"      ->  120000.0 (Indian lakh-style comma grouping)
    """
    def _clean_value(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        if s == "" or s.lower() in ("nan", "none", "null", "-"):
            return np.nan

        is_negative = s.startswith("(") and s.endswith(")")

        # Remove common currency words/abbreviations FIRST (with their
        # trailing period, e.g. "Rs." or "INR") -- doing this before
        # stripping symbols avoids leaving a stray "." that would be
        # misread as a decimal point (e.g. "Rs. 599" must not become ".599").
        s = re.sub(r"(?i)\b(rs|inr|usd|rupees|dollars?)\b\.?", "", s)
        s = re.sub(r"[₹$,()\s]", "", s)

        if s in ("", "-", "."):
            return np.nan

        try:
            value = float(s)
        except ValueError:
            return np.nan

        return -abs(value) if is_negative else value

    return series.apply(_clean_value)


def clean_date_column(series: pd.Series) -> pd.Series:
    """
    Parse a messy date column that may mix DD/MM/YYYY, YYYY-MM-DD, and
    ISO timestamps. errors='coerce' turns anything unparseable into NaT
    rather than crashing the whole pipeline.

    Two-pass strategy:
      1. Try WITHOUT forcing dayfirst. This correctly handles unambiguous
         formats like YYYY-MM-DD (forcing dayfirst=True on these can
         mis-parse e.g. "2023-10-28" by trying to treat 28 as a month).
      2. For whatever failed, retry WITH dayfirst=True, which correctly
         handles ambiguous Indian-style DD/MM/YYYY dates.
    """
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)
    still_missing = parsed.isna() & series.notna()

    if still_missing.any():
        retry = pd.to_datetime(series[still_missing], errors="coerce", dayfirst=True)
        parsed.loc[still_missing] = retry

    return parsed


@st.cache_data(show_spinner=False)
def load_raw_file(uploaded_file) -> pd.DataFrame:
    """Load an uploaded CSV or Excel file into a DataFrame."""
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        # Try a couple of common encodings used by Indian e-commerce exports.
        for encoding in ("utf-8", "latin1", "cp1252"):
            try:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding=encoding)
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file, encoding="utf-8", errors="ignore")
    elif name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Please upload .csv or .xlsx")


def build_clean_dataframe(raw_df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Build a standardized DataFrame using only the fields the user has
    confirmed a mapping for. Missing/unmapped fields are simply skipped
    (this is the "fail gracefully" requirement) -- downstream chart code
    checks column existence before rendering anything.
    """
    clean = pd.DataFrame(index=raw_df.index)

    for field, raw_col in mapping.items():
        if not raw_col or raw_col not in raw_df.columns:
            continue  # field not available in this dataset -- skip gracefully

        if field == "Price":
            clean[field] = clean_numeric_column(raw_df[raw_col])
        elif field == "Quantity":
            clean[field] = clean_numeric_column(raw_df[raw_col]).fillna(1)
        elif field == "Order_Date":
            clean[field] = clean_date_column(raw_df[raw_col])
        else:
            clean[field] = raw_df[raw_col].astype(str).str.strip()

    return clean


# =====================================================================
# 3. KPI CALCULATIONS
# =====================================================================

def compute_kpis(df: pd.DataFrame) -> dict:
    """
    Compute top-level KPIs, using only whatever columns are actually
    present. Returns None for any KPI that can't be computed, so the UI
    can skip rendering that card instead of crashing.
    """
    kpis = {"total_revenue": None, "total_orders": None, "units_sold": None, "aov": None}

    if "Price" in df.columns:
        kpis["total_revenue"] = df["Price"].sum(skipna=True)

    if "Order_ID" in df.columns:
        kpis["total_orders"] = df["Order_ID"].nunique()
    else:
        kpis["total_orders"] = len(df)  # fallback: 1 row = 1 order

    if "Quantity" in df.columns:
        kpis["units_sold"] = df["Quantity"].sum(skipna=True)

    if kpis["total_revenue"] is not None and kpis["total_orders"]:
        kpis["aov"] = kpis["total_revenue"] / kpis["total_orders"]

    return kpis


# =====================================================================
# 4. STREAMLIT UI
# =====================================================================

st.set_page_config(
    page_title="Universal E-Commerce Analytics Dashboard",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Universal E-Commerce Automated Analytics Dashboard")
st.caption(
    "Upload a raw sales export from Myntra, Flipkart, Amazon India, Meesho, "
    "Shopsy, or any other e-commerce platform. The dashboard auto-detects "
    "the schema, cleans the data, and builds KPIs and charts automatically."
)

# ---------------------------------------------------------------
# Step 1: File Upload
# ---------------------------------------------------------------
uploaded_file = st.file_uploader(
    "Upload your sales file (.csv or .xlsx, up to 200MB)",
    type=["csv", "xlsx", "xls"],
)

if uploaded_file is None:
    st.info("👆 Upload a file to get started. No file? Use `generate_samples.py` "
            "to create realistic test datasets for 10 Indian e-commerce platforms.")
    st.stop()

try:
    raw_df = load_raw_file(uploaded_file)
except Exception as e:
    st.error(f"Couldn't read this file: {e}")
    st.stop()

if raw_df.empty:
    st.error("The uploaded file appears to be empty.")
    st.stop()

st.success(f"Loaded **{len(raw_df):,} rows** and **{len(raw_df.columns)} columns**.")
with st.expander("Preview raw data"):
    st.dataframe(raw_df.head(20), use_container_width=True)

# ---------------------------------------------------------------
# Step 2: Schema Detection + Manual Fallback
# ---------------------------------------------------------------
st.subheader("Step 1: Column Mapping")

auto_mapping = auto_detect_schema(list(raw_df.columns))

CONFIDENCE_THRESHOLD = 0.6  # below this, we ask the user to confirm manually

st.write(
    "The app tries to auto-detect which of your columns correspond to "
    "standard fields. Review and correct the mapping below if needed "
    "(select **'-- None --'** for fields your dataset doesn't have)."
)

final_mapping = {}
col_options = ["-- None --"] + list(raw_df.columns)

mapping_cols = st.columns(2)
for i, field in enumerate(STANDARD_FIELDS):
    detected_col, confidence = auto_mapping.get(field, (None, 0.0))
    default_value = detected_col if (detected_col and confidence >= CONFIDENCE_THRESHOLD) else "-- None --"

    with mapping_cols[i % 2]:
        label = f"{field.replace('_', ' ')}"
        if detected_col and confidence < CONFIDENCE_THRESHOLD:
            label += f"  ⚠️ low-confidence guess: '{detected_col}'"
        selected = st.selectbox(
            label,
            options=col_options,
            index=col_options.index(default_value) if default_value in col_options else 0,
            key=f"map_{field}",
        )
        final_mapping[field] = None if selected == "-- None --" else selected

mapped_count = sum(1 for v in final_mapping.values() if v)
if mapped_count == 0:
    st.warning("No fields mapped yet -- select at least Price or Order_Date above to see KPIs and charts.")
    st.stop()

# ---------------------------------------------------------------
# Step 3: Clean the Data
# ---------------------------------------------------------------
clean_df = build_clean_dataframe(raw_df, final_mapping)

# Drop rows where every mapped value is missing (fully unusable rows)
clean_df = clean_df.dropna(how="all")

st.subheader("Step 2: Cleaned & Standardized Data")
with st.expander("Preview cleaned data"):
    st.dataframe(clean_df.head(20), use_container_width=True)

# ---------------------------------------------------------------
# Step 4: KPI Cards
# ---------------------------------------------------------------
st.subheader("Step 3: Key Metrics")

kpis = compute_kpis(clean_df)
kpi_cols = st.columns(4)

with kpi_cols[0]:
    if kpis["total_revenue"] is not None:
        st.metric("Total Revenue", f"₹{kpis['total_revenue']:,.0f}")
    else:
        st.metric("Total Revenue", "N/A", help="No Price column mapped")

with kpi_cols[1]:
    st.metric("Total Orders", f"{kpis['total_orders']:,}")

with kpi_cols[2]:
    if kpis["units_sold"] is not None:
        st.metric("Units Sold", f"{kpis['units_sold']:,.0f}")
    else:
        st.metric("Units Sold", "N/A", help="No Quantity column mapped")

with kpi_cols[3]:
    if kpis["aov"] is not None:
        st.metric("Avg Order Value", f"₹{kpis['aov']:,.2f}")
    else:
        st.metric("Avg Order Value", "N/A", help="Needs both Price and Order_ID/rows")

# ---------------------------------------------------------------
# Step 5: Universal Chart Builder
# ---------------------------------------------------------------
st.subheader("Step 4: Chart Builder")

chart_type = st.radio(
    "Choose a chart type",
    ["Bar Chart", "Line Trend", "Donut / Pie", "Scatter Plot", "Correlation Heatmap"],
    horizontal=True,
)

numeric_cols = clean_df.select_dtypes(include="number").columns.tolist()
categorical_cols = [c for c in clean_df.columns if c not in numeric_cols and c != "Order_Date"]
has_date = "Order_Date" in clean_df.columns and clean_df["Order_Date"].notna().any()

if chart_type == "Bar Chart":
    if categorical_cols and numeric_cols:
        c1, c2 = st.columns(2)
        group_col = c1.selectbox("Group by (category)", categorical_cols)
        value_col = c2.selectbox("Value (numeric)", numeric_cols)
        agg_df = clean_df.groupby(group_col)[value_col].sum().sort_values(ascending=False).head(15).reset_index()
        fig = px.bar(agg_df, x=group_col, y=value_col, title=f"{value_col} by {group_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Bar chart needs at least one categorical column (e.g. Category) and one numeric column (e.g. Price).")

elif chart_type == "Line Trend":
    if has_date and numeric_cols:
        value_col = st.selectbox("Metric to trend over time", numeric_cols)
        trend_df = clean_df.dropna(subset=["Order_Date"]).copy()
        trend_df["Order_Date"] = trend_df["Order_Date"].dt.date
        agg_df = trend_df.groupby("Order_Date")[value_col].sum().reset_index()
        fig = px.line(agg_df, x="Order_Date", y=value_col, title=f"{value_col} Over Time")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Line trend needs a mapped Order_Date column with valid dates.")

elif chart_type == "Donut / Pie":
    if categorical_cols and numeric_cols:
        c1, c2 = st.columns(2)
        group_col = c1.selectbox("Break down by", categorical_cols, key="pie_group")
        value_col = c2.selectbox("Value", numeric_cols, key="pie_value")
        agg_df = clean_df.groupby(group_col)[value_col].sum().sort_values(ascending=False).head(10).reset_index()
        fig = px.pie(agg_df, names=group_col, values=value_col, hole=0.45, title=f"{value_col} Share by {group_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Donut chart needs at least one categorical column and one numeric column.")

elif chart_type == "Scatter Plot":
    if len(numeric_cols) >= 2:
        c1, c2 = st.columns(2)
        x_col = c1.selectbox("X axis", numeric_cols, key="scatter_x")
        y_col = c2.selectbox("Y axis", numeric_cols, index=min(1, len(numeric_cols) - 1), key="scatter_y")
        fig = px.scatter(clean_df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Scatter plot needs at least two numeric columns (e.g. Price and Quantity).")

elif chart_type == "Correlation Heatmap":
    if len(numeric_cols) >= 2:
        corr = clean_df[numeric_cols].corr(numeric_only=True)
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", title="Correlation Heatmap")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Correlation heatmap needs at least two numeric columns.")

# ---------------------------------------------------------------
# Step 6: Export Cleaned Data
# ---------------------------------------------------------------
st.subheader("Step 5: Export Cleaned Dataset")

csv_buffer = io.StringIO()
clean_df.to_csv(csv_buffer, index=False)
st.download_button(
    label="⬇️ Download Cleaned CSV",
    data=csv_buffer.getvalue(),
    file_name="cleaned_ecommerce_data.csv",
    mime="text/csv",
)
