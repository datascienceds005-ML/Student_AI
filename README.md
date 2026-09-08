---
title: Universal E-Commerce Analytics Dashboard
emoji: 🛒
colorFrom: blue
colorTo: pink
sdk: streamlit
sdk_version: "1.38.0"
app_file: app.py
pinned: false
---

# Universal E-Commerce Automated Analytics Dashboard

Upload **any** raw e-commerce sales export (Myntra, Flipkart, Amazon India,
Meesho, Shopsy, Snapdeal, Nykaa, Ajio, Blinkit/Zepto, Tata CLiQ, or any other
platform) and get automatic schema detection, data cleaning, KPIs, and
interactive charts — no manual column renaming required.

## How it works (architecture)

1. **Schema Mapping Engine** (`auto_detect_schema` in `app.py`)
   A dictionary of keyword aliases (e.g. `Price` matches `selling_price`,
   `item_total`, `discounted_price`, `amount`, `mrp`, etc.) is compared
   against every raw column header using substring + fuzzy-string matching.
   Matches are assigned **greedily by confidence** so no single raw column
   gets mapped to two different standard fields. Anything below a 0.6
   confidence score is left unmapped and shown to the user for manual
   selection via dropdowns — this is the fallback UI requirement.

2. **Cleaning Engine** (`clean_numeric_column`, `clean_date_column`)
   - Numeric columns: currency symbols (₹, $), "Rs."/"INR" prefixes, comma
     thousand-separators (including Indian lakh-style grouping like
     `1,20,000`), and accounting-style negative numbers `(250)` are all
     normalized to clean floats.
   - Date columns: parsed with a two-pass strategy — first without forcing
     day-first (handles unambiguous ISO `YYYY-MM-DD`), then a second pass
     with `dayfirst=True` for whatever failed (handles Indian-style
     `DD/MM/YYYY`). Anything unparseable becomes `NaT` via `errors='coerce'`
     rather than crashing the pipeline.

3. **Graceful degradation**: every KPI and chart function checks whether
   its required column(s) exist before rendering. A dataset missing
   `Category` simply won't offer category-based charts — it won't crash.

4. **Export**: the standardized (not raw) dataframe is offered as a CSV
   download, so downstream tools always see the same consistent schema
   regardless of which platform the data came from.

## Project structure
```
universal-ecommerce-dashboard/
├── app.py                 # main Streamlit application (all logic)
├── generate_samples.py    # generates 10 realistic messy test CSVs
├── requirements.txt
├── README.md
└── sample_data/           # created by generate_samples.py
```

## Run locally
```bash
pip install -r requirements.txt
python generate_samples.py      # optional: creates 10 test CSVs
streamlit run app.py
```
Open the URL Streamlit prints (usually `http://localhost:8501`), upload
a CSV/XLSX (or one of the generated sample files), review/adjust the
column mapping, and explore the KPIs and charts.

## Deployment: GitHub → Hugging Face Spaces

See `DEPLOYMENT.md` for full step-by-step instructions.
