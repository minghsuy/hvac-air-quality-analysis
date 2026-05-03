"""Shared Google Sheets → pandas DataFrame loader.

Previously duplicated across refresh_cache.py, dashboard.py, and bench_heatmap.py
(three near-identical copies). Extracted here so the column-shift repair logic
lives in one place with a correct timestamp gate.

The 18-column schema stabilized on 2025-09-01. Pre-stabilization rows
(Jul-Aug 2025) had 17 columns and the legacy shift-repair still applies.
Post-stabilization rows under 18 columns are Google Sheets API truncation
of trailing empty strings (most visible on Temp Stick attic rows, which
have 6 trailing empties and land as 12 cols). Those rows must NOT be
shifted — their values are correctly positioned, just padded.

Callers invoke as: `from _sheets_loader import load_sheet_as_df`.
When a script is run via `python scripts/foo.py` or `streamlit run scripts/foo.py`,
`scripts/` is `sys.path[0]`, so _sheets_loader is importable as a sibling
module (no `scripts.` prefix, no package `__init__.py` needed).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

EXPECTED_COLS = 19
SHEET_RANGE = "A:S"
SCHEMA_STABILIZED = pd.Timestamp("2025-09-01")

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
    "Indoor_Pressure",
]

# Columns whose values shifted when the schema grew from 17 to 18 cols.
# Only applied to pre-SCHEMA_STABILIZED rows.
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


def _fetch_values(spreadsheet_id: str, sheet_tab: str, creds_path: str) -> list[list[str]]:
    """Google Sheets API call. Returns raw 2-D list (headers + data rows)."""
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
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
    return values


def _values_to_df(values: list[list[str]]) -> pd.DataFrame:
    """Pure transform: 2-D list → DataFrame with correct shift-repair gating.

    Factored out so tests can mock this without mocking the whole API chain.
    """
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

    # Shift-repair: only for pre-stabilization rows. Modern rows under
    # EXPECTED_COLS are Sheets API trailing-empty truncation, not schema shift.
    shifted = (orig_cols < EXPECTED_COLS) & (df["Timestamp"] < SCHEMA_STABILIZED)
    for col in set(SHIFTED_COLS) & set(df.columns):
        df.loc[shifted, col] = np.nan

    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)


def load_sheet_as_df(spreadsheet_id: str, sheet_tab: str, creds_path: str) -> pd.DataFrame:
    """Load a Google Sheet tab into a DataFrame.

    Raises RuntimeError if the sheet is empty. Callers own .env loading.
    """
    values = _fetch_values(spreadsheet_id, sheet_tab, creds_path)
    return _values_to_df(values)
