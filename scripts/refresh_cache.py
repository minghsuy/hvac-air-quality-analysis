#!/usr/bin/env python3
# Headless refresh of .cache/air_quality.parquet from Google Sheets.
# Invoke manually when you want fresh data:  uv run python scripts/refresh_cache.py

import os
import socket
import sys
import time
from datetime import datetime

socket.setdefaulttimeout(45)

from dotenv import load_dotenv  # noqa: E402

from _sheets_loader import load_sheet_as_df  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET_CACHE = os.path.join(REPO_ROOT, ".cache", "air_quality.parquet")
CREDS_PATH = os.path.join(REPO_ROOT, "google-credentials.json")


def fetch_from_sheets():
    load_dotenv(os.path.join(REPO_ROOT, ".env"))
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    sheet_tab = os.getenv("GOOGLE_SHEET_TAB", "")
    if not spreadsheet_id:
        raise RuntimeError("GOOGLE_SPREADSHEET_ID missing from .env")
    return load_sheet_as_df(spreadsheet_id, sheet_tab, CREDS_PATH)


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
