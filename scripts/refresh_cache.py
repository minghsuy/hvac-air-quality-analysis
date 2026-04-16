#!/usr/bin/env python3
# Headless refresh of .cache/air_quality.parquet from Google Sheets.
# Mirrors scripts/dashboard.py::_fetch_from_sheets + _save_parquet — inlined
# rather than imported because dashboard.py imports streamlit at module scope.
# TODO: extract scripts/_sheets_loader.py to dedupe this, dashboard.py, and
#   bench_heatmap.py (three near-identical copies of the same fetch pipeline).
# Invoke manually when you want fresh data:  uv run python scripts/refresh_cache.py

import os
import socket
import sys
import time
from datetime import datetime

socket.setdefaulttimeout(45)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google.oauth2 import service_account  # noqa: E402
from googleapiclient.discovery import build  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_CACHE = os.path.join(REPO_ROOT, ".cache", "air_quality.parquet")
CREDS_PATH = os.path.join(REPO_ROOT, "google-credentials.json")

# Sheet schema: 18 columns (A:R). Pre-Sep 2025 rows had 17 and need the
# column-shift repair applied via SHIFTED_COLS below.
EXPECTED_COLS = 18
SHEET_RANGE = "A:R"

NUMERIC_COLS = [
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
]
# Columns whose positions shifted when the schema went from 17 to 18 cols.
# For rows with len(row) < EXPECTED_COLS, these values are unreliable.
SHIFTED_COLS = [
    "Indoor_Temp",
    "Indoor_Humidity",
    "Indoor_Radon",
    "Outdoor_CO2",
    "Outdoor_Temp",
    "Outdoor_Humidity",
    "Outdoor_VOC",
    "Outdoor_NOX",
]


def fetch_from_sheets() -> pd.DataFrame:
    load_dotenv(os.path.join(REPO_ROOT, ".env"))
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    sheet_tab = os.getenv("GOOGLE_SHEET_TAB", "")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SPREADSHEET_ID missing from .env")

    credentials = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    range_name = f"{sheet_tab}!{SHEET_RANGE}" if sheet_tab else SHEET_RANGE
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )
    values = result.get("values", [])
    if not values:
        raise RuntimeError("Sheet returned no rows")

    headers = values[0]
    n_cols = len(headers)
    data_rows = values[1:]
    orig_cols = np.fromiter((len(r) for r in data_rows), dtype=np.int16, count=len(data_rows))
    padded = [
        row + [""] * (n_cols - len(row)) if len(row) < n_cols else row[:n_cols] for row in data_rows
    ]

    df = pd.DataFrame(padded, columns=headers)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")

    for col in set(NUMERIC_COLS) & set(df.columns):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    shifted = orig_cols < EXPECTED_COLS
    for col in set(SHIFTED_COLS) & set(df.columns):
        df.loc[shifted, col] = np.nan

    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)


def main() -> int:
    stamp = datetime.now().isoformat(timespec="seconds")
    t0 = time.perf_counter()
    try:
        df = fetch_from_sheets()
        os.makedirs(os.path.dirname(PARQUET_CACHE), exist_ok=True)
        df.to_parquet(PARQUET_CACHE)
        dt = time.perf_counter() - t0
        print(
            f"[{stamp}] ok rows={len(df)} "
            f"range={df['Timestamp'].min()}..{df['Timestamp'].max()} elapsed={dt:.1f}s"
        )
        return 0
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"[{stamp}] FAIL elapsed={dt:.1f}s error={type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
