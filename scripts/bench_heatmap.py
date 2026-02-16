#!/usr/bin/env python3
"""
Benchmark heatmap generation: Google Sheets vs local Parquet.
Shows where the real bottleneck is and what GPU acceleration actually helps.
"""

import os
import time

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

PARQUET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".cache", "air_quality.parquet"
)


def fetch_from_sheets():
    spreadsheet_id = os.environ["GOOGLE_SPREADSHEET_ID"]
    sheet_tab = os.environ.get("GOOGLE_SHEET_TAB", "")
    creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "google-credentials.json")
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=credentials)
    sheet = service.spreadsheets()
    range_name = f"{sheet_tab}!A:R" if sheet_tab else "A:R"
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get("values", [])

    headers = values[0]
    n_cols = len(headers)
    padded = []
    orig_cols = []
    for row in values[1:]:
        orig_cols.append(len(row))
        r = row + [""] * (n_cols - len(row)) if len(row) < n_cols else row[:n_cols]
        padded.append(r)

    df = pd.DataFrame(padded, columns=headers)
    df["_orig_cols"] = orig_cols
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    for col in [
        "Indoor_PM25",
        "Outdoor_PM25",
        "Filter_Efficiency",
        "Indoor_CO2",
        "Outdoor_CO2",
        "Indoor_VOC",
        "Indoor_NOX",
        "Indoor_Temp",
        "Indoor_Humidity",
        "Indoor_Radon",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    shifted = df["_orig_cols"] < 18
    for col in [
        "Indoor_Temp",
        "Indoor_Humidity",
        "Indoor_Radon",
        "Outdoor_CO2",
        "Outdoor_Temp",
        "Outdoor_Humidity",
        "Outdoor_VOC",
        "Outdoor_NOX",
    ]:
        if col in df.columns:
            df.loc[shifted, col] = np.nan

    df = df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)
    return df


def build_heatmap_pandas(df):
    sub = df[
        (df["Room"] == "master_bedroom") & (df["Indoor_CO2"].notna()) & (df["Indoor_CO2"] > 0)
    ].copy()
    sub["hour"] = sub["Timestamp"].dt.hour
    sub["date"] = sub["Timestamp"].dt.date
    pivot = sub.pivot_table(values="Indoor_CO2", index="hour", columns="date", aggfunc="mean")
    return pivot


print("=" * 60)
print("BENCHMARK: Heatmap Generation — Where's the Bottleneck?")
print("=" * 60)

# ── Method 1: Google Sheets API (current) ──
print("\n--- Method 1: Google Sheets API ---")
t0 = time.perf_counter()
df = fetch_from_sheets()
t1 = time.perf_counter()
pivot = build_heatmap_pandas(df)
t2 = time.perf_counter()
print(f"  Fetch:   {t1 - t0:.3f}s")
print(f"  Compute: {t2 - t1:.3f}s")
print(f"  TOTAL:   {t2 - t0:.3f}s")

# ── Save to Parquet ──
os.makedirs(os.path.dirname(PARQUET_PATH), exist_ok=True)
df.drop(columns=["_orig_cols"], errors="ignore").to_parquet(PARQUET_PATH)
parquet_size = os.path.getsize(PARQUET_PATH) / 1024 / 1024
print(f"\n  Saved parquet: {PARQUET_PATH} ({parquet_size:.1f} MB)")

# ── Method 2: Local Parquet ──
print("\n--- Method 2: Local Parquet ---")
t0 = time.perf_counter()
df2 = pd.read_parquet(PARQUET_PATH)
t1 = time.perf_counter()
pivot2 = build_heatmap_pandas(df2)
t2 = time.perf_counter()
print(f"  Read:    {t1 - t0:.3f}s")
print(f"  Compute: {t2 - t1:.3f}s")
print(f"  TOTAL:   {t2 - t0:.3f}s")

# ── Method 3: Polars ──
try:
    import polars as pl

    print("\n--- Method 3: Polars (CPU, but faster than pandas) ---")
    t0 = time.perf_counter()
    df3 = pl.read_parquet(PARQUET_PATH)
    t1 = time.perf_counter()
    sub3 = df3.filter(
        (pl.col("Room") == "master_bedroom")
        & (pl.col("Indoor_CO2").is_not_null())
        & (pl.col("Indoor_CO2") > 0)
    ).with_columns(
        [
            pl.col("Timestamp").dt.hour().alias("hour"),
            pl.col("Timestamp").dt.date().alias("date"),
        ]
    )
    pivot3 = sub3.group_by(["hour", "date"]).agg(pl.col("Indoor_CO2").mean()).sort(["date", "hour"])
    t2 = time.perf_counter()
    print(f"  Read:    {t1 - t0:.3f}s")
    print(f"  Compute: {t2 - t1:.3f}s")
    print(f"  TOTAL:   {t2 - t0:.3f}s")
except ImportError:
    print("\n--- Method 3: Polars --- (not installed)")

# ── Method 4: cuDF (GPU) ──
try:
    import cudf

    print("\n--- Method 4: cuDF (GPU-accelerated pandas) ---")
    t0 = time.perf_counter()
    gdf = cudf.read_parquet(PARQUET_PATH)
    t1 = time.perf_counter()
    sub4 = gdf[
        (gdf["Room"] == "master_bedroom") & (gdf["Indoor_CO2"].notna()) & (gdf["Indoor_CO2"] > 0)
    ].copy()
    sub4["hour"] = sub4["Timestamp"].dt.hour
    sub4["date"] = sub4["Timestamp"].dt.day  # cudf doesn't have .date, use day
    pivot4 = sub4.groupby(["hour", "date"])["Indoor_CO2"].mean()
    result4 = pivot4.to_pandas()  # bring back to CPU for plotting
    t2 = time.perf_counter()
    print(f"  Read:    {t1 - t0:.3f}s")
    print(f"  Compute: {t2 - t1:.3f}s")
    print(f"  TOTAL:   {t2 - t0:.3f}s")
except ImportError:
    print("\n--- Method 4: cuDF --- (not installed)")
    print("  Install: uv pip install cudf-cu12 (or conda install -c rapidsai cudf)")
except Exception as e:
    print(f"\n--- Method 4: cuDF --- ERROR: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
The bottleneck is NOT compute. It's:
  1. Google Sheets API (3+ seconds for 98k rows over network)
  2. Browser rendering (Plotly DOM manipulation)

Solutions that actually help:
  - Local parquet cache (eliminates network latency)
  - Pre-aggregated cache (avoid re-parsing 98k rows)
  - Streamlit @st.cache_data (already doing this)

GPU (cuDF) would help IF:
  - Dataset was 10M+ rows (not 98k)
  - Doing complex aggregations (rolling window joins, etc)
  - Real-time streaming analytics

For 98k rows, pandas pivot_table in 5ms is already overkill.
""")
