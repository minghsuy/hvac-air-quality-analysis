#!/usr/bin/env python3
"""
Analyze current Google Sheets data to understand patterns before implementing multi-sensor support
"""

import os
import pandas as pd
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()


def fetch_sheets_data():
    """Fetch data from Google Sheets using API"""

    CREDENTIALS_FILE = "google-credentials.json"
    SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")

    # Authenticate
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )

    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    # Get all data
    result = (
        sheet.values()
        .get(
            spreadsheetId=SPREADSHEET_ID,
            range="A:Z",  # Get all columns
        )
        .execute()
    )

    values = result.get("values", [])

    if not values:
        print("No data found in spreadsheet")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(values[1:], columns=values[0])

    return df


def analyze_data(df):
    """Analyze the current data structure and patterns"""

    print("=" * 60)
    print("GOOGLE SHEETS DATA ANALYSIS")
    print("=" * 60)

    # Basic info
    print("\n📊 Data Overview:")
    print(f"  - Total rows: {len(df)}")
    print(f"  - Date range: {df.iloc[0, 0]} to {df.iloc[-1, 0]}")
    print(f"  - Columns: {df.shape[1]}")

    # Column analysis
    print("\n📋 Columns Found:")
    for i, col in enumerate(df.columns):
        # Get sample values (non-empty)
        non_empty = df[col].dropna().head(3)
        if len(non_empty) > 0:
            sample = ", ".join([str(v)[:20] for v in non_empty])
            print(f"  {i + 1}. {col}: {sample}...")

    # Check for numeric columns
    print("\n📈 Numeric Columns Analysis:")
    numeric_cols = []
    for col in df.columns:
        try:
            # Try to convert to float
            test_vals = pd.to_numeric(df[col].dropna().head(10), errors="coerce")
            if test_vals.notna().sum() > 5:  # At least 5 valid numbers
                numeric_cols.append(col)
                values = pd.to_numeric(df[col], errors="coerce")
                print(f"  - {col}:")
                print(f"      Range: {values.min():.2f} to {values.max():.2f}")
                print(f"      Mean: {values.mean():.2f}")
                print(f"      Latest: {values.dropna().iloc[-1]:.2f}")
        except Exception:
            pass

    # Check for efficiency calculations
    print("\n⚡ Filter Efficiency Analysis:")
    if "Filter Efficiency (%)" in df.columns:
        eff_col = "Filter Efficiency (%)"
    elif "Efficiency" in df.columns:
        eff_col = "Efficiency"
    else:
        eff_col = None

    if eff_col:
        try:
            efficiency = pd.to_numeric(df[eff_col], errors="coerce")
            print(f"  - Current efficiency: {efficiency.dropna().iloc[-1]:.1f}%")
            print(f"  - Average efficiency: {efficiency.mean():.1f}%")
            print(f"  - Minimum efficiency: {efficiency.min():.1f}%")

            # Check recent trend
            recent = efficiency.dropna().tail(10)
            if len(recent) > 1:
                trend = "declining" if recent.iloc[-1] < recent.iloc[0] else "improving"
                print(f"  - Recent trend: {trend}")
        except Exception:
            pass

    # Check for PM2.5 data
    print("\n💨 PM2.5 Analysis:")
    indoor_pm_col = None
    outdoor_pm_col = None

    for col in df.columns:
        if "indoor" in col.lower() and "pm" in col.lower():
            indoor_pm_col = col
        elif "outdoor" in col.lower() and "pm" in col.lower():
            outdoor_pm_col = col

    if indoor_pm_col:
        indoor_pm = pd.to_numeric(df[indoor_pm_col], errors="coerce")
        print(f"  - Indoor PM2.5 latest: {indoor_pm.dropna().iloc[-1]:.1f} μg/m³")
        print(f"  - Indoor PM2.5 average: {indoor_pm.mean():.1f} μg/m³")

    if outdoor_pm_col:
        outdoor_pm = pd.to_numeric(df[outdoor_pm_col], errors="coerce")
        print(f"  - Outdoor PM2.5 latest: {outdoor_pm.dropna().iloc[-1]:.1f} μg/m³")
        print(f"  - Outdoor PM2.5 average: {outdoor_pm.mean():.1f} μg/m³")

    # Data collection frequency
    print("\n⏰ Collection Frequency:")
    if "Timestamp" in df.columns:
        try:
            # Parse timestamps
            timestamps = pd.to_datetime(df["Timestamp"], errors="coerce")
            valid_timestamps = timestamps.dropna()
            if len(valid_timestamps) > 1:
                time_diffs = valid_timestamps.diff().dropna()
                avg_interval = time_diffs.mean()
                print(f"  - Average interval: {avg_interval.total_seconds() / 60:.1f} minutes")
                print(f"  - Data points per day: {1440 / (avg_interval.total_seconds() / 60):.0f}")
        except Exception:
            pass

    # Check for room-specific data
    print("\n🏠 Room Detection:")
    room_found = False
    for col in df.columns:
        if "room" in col.lower() or "location" in col.lower():
            room_found = True
            unique_rooms = df[col].dropna().unique()
            print(f"  - Rooms/locations found: {', '.join(unique_rooms)}")

    if not room_found:
        print("  - No room-specific columns found (single sensor setup)")

    return df


def main():
    """Main analysis function"""
    print("Fetching data from Google Sheets...")

    try:
        df = fetch_sheets_data()
        if df is not None:
            analyze_data(df)

            # Save a sample for inspection
            sample_file = "/tmp/sheets_sample.csv"
            df.tail(100).to_csv(sample_file, index=False)
            print(f"\n💾 Sample data (last 100 rows) saved to: {sample_file}")

            print("\n" + "=" * 60)
            print("RECOMMENDATIONS FOR MULTI-SENSOR SETUP:")
            print("=" * 60)
            print("1. Current data appears to be single-sensor")
            print("2. Need to add 'room' or 'sensor_id' column")
            print("3. Consider separate rows per sensor reading")
            print("4. Keep efficiency calculation in Sheets formulas")
            print("5. Add sensor type column (airthings/airgradient)")

    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. The service account has access to your sheet")
        print("2. The GOOGLE_SPREADSHEET_ID is correct in .env")


if __name__ == "__main__":
    main()
