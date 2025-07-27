#!/usr/bin/env python3
"""
Secure Google Sheets reader using service account authentication
Keeps your air quality data private
"""

import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

# Load environment variables
load_dotenv()


class SecureGoogleSheetsReader:
    def __init__(self):
        self.credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")
        self.spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
        self.service = None

    def authenticate(self):
        """Authenticate using service account credentials"""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                "Please follow setup_google_sheets_api.md to create service account"
            )

        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            self.service = build("sheets", "v4", credentials=credentials)
            print("✓ Successfully authenticated with Google Sheets API")
            return True
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            return False

    def read_sheet(self, range_name="Form Responses 1!A:Z"):
        """Read data from Google Sheet"""
        if not self.spreadsheet_id:
            raise ValueError(
                "GOOGLE_SPREADSHEET_ID not found in .env\nAdd: GOOGLE_SPREADSHEET_ID=your_sheet_id"
            )

        if not self.service:
            if not self.authenticate():
                return None

        try:
            sheet = self.service.spreadsheets()
            result = (
                sheet.values().get(spreadsheetId=self.spreadsheet_id, range=range_name).execute()
            )

            values = result.get("values", [])

            if not values:
                print("No data found in sheet")
                return None

            # Handle duplicate column names
            headers = values[0]
            # Make column names unique by adding suffix to duplicates
            seen = {}
            unique_headers = []
            for header in headers:
                if header in seen:
                    seen[header] += 1
                    unique_headers.append(f"{header}_{seen[header]}")
                else:
                    seen[header] = 0
                    unique_headers.append(header)

            # Convert to DataFrame
            df = pd.DataFrame(values[1:], columns=unique_headers)
            print(f"✓ Successfully read {len(df)} rows from Google Sheets")
            return df

        except HttpError as error:
            if error.resp.status == 403:
                print(
                    "✗ Access denied. Make sure you've shared the sheet with the service account email"
                )
                print(f"  Check {self.credentials_path} for the 'client_email' field")
            elif error.resp.status == 404:
                print("✗ Spreadsheet not found. Check your GOOGLE_SPREADSHEET_ID")
            else:
                print(f"✗ An error occurred: {error}")
            return None

    def get_service_account_email(self):
        """Get the service account email to share the sheet with"""
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path, "r") as f:
                creds = json.load(f)
                return creds.get("client_email")
        return None


def analyze_air_quality_data(df):
    """Analyze the air quality data"""
    if df is None or df.empty:
        return

    print("\n=== Air Quality Data Analysis ===")

    # Try to identify columns (adjust based on your actual form fields)
    # Common variations of column names
    timestamp_variations = ["Timestamp", "timestamp", "Time", "Date"]
    pm25_indoor_variations = ["Indoor PM2.5", "indoor_pm25", "Indoor PM2.5 (μg/m³)"]
    pm25_outdoor_variations = ["Outdoor PM2.5", "outdoor_pm25", "Outdoor PM2.5 (μg/m³)"]
    efficiency_variations = ["Filter Efficiency", "filter_efficiency", "Filter Efficiency (%)"]

    # Find actual columns
    timestamp_col = next((col for col in timestamp_variations if col in df.columns), None)
    indoor_col = next((col for col in pm25_indoor_variations if col in df.columns), None)
    outdoor_col = next((col for col in pm25_outdoor_variations if col in df.columns), None)
    efficiency_col = next((col for col in efficiency_variations if col in df.columns), None)

    # Convert timestamp
    if timestamp_col:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors="coerce")
        df = df.sort_values(timestamp_col)
        df = df.set_index(timestamp_col)

    # Convert numeric columns
    for col in [indoor_col, outdoor_col, efficiency_col]:
        if col and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Show recent data
    print("\n📊 Last 10 readings:")
    display_cols = [col for col in [indoor_col, outdoor_col, efficiency_col] if col]
    if display_cols:
        print(df[display_cols].tail(10))

    # Calculate statistics
    if indoor_col and outdoor_col and efficiency_col:
        print("\n📈 Summary Statistics:")
        print("\nIndoor PM2.5 (μg/m³):")
        print(f"  Current: {df[indoor_col].iloc[-1]:.1f}")
        print(f"  24h Average: {df[indoor_col].last('24H').mean():.1f}")
        print(f"  7d Average: {df[indoor_col].last('7D').mean():.1f}")

        print("\nOutdoor PM2.5 (μg/m³):")
        print(f"  Current: {df[outdoor_col].iloc[-1]:.1f}")
        print(f"  24h Average: {df[outdoor_col].last('24H').mean():.1f}")
        print(f"  7d Average: {df[outdoor_col].last('7D').mean():.1f}")

        print("\nFilter Efficiency (%):")
        print(f"  Current: {df[efficiency_col].iloc[-1]:.1f}")
        print(f"  24h Average: {df[efficiency_col].last('24H').mean():.1f}")
        print(f"  7d Average: {df[efficiency_col].last('7D').mean():.1f}")

        # Alerts
        recent_efficiency = df[efficiency_col].last("24H")
        low_efficiency_count = (recent_efficiency < 85).sum()

        if low_efficiency_count > 0:
            print(f"\n⚠️  ALERT: {low_efficiency_count} readings below 85% efficiency in last 24h")
            print("Consider replacing filters soon!")

        # WHO guideline check
        recent_indoor = df[indoor_col].last("24H")
        high_pm25_count = (recent_indoor > 15).sum()

        if high_pm25_count > 0:
            print(
                f"\n⚠️  HEALTH ALERT: {high_pm25_count} readings above WHO guideline (15 μg/m³) in last 24h"
            )

    return df


def main():
    """Main function"""
    print("=== Secure Google Sheets Reader ===\n")

    reader = SecureGoogleSheetsReader()

    # Show service account email for setup help
    service_email = reader.get_service_account_email()
    if service_email:
        print(f"📧 Service account email: {service_email}")
        print("Make sure this email has 'Viewer' access to your Google Sheet\n")

    try:
        # Read the data
        df = reader.read_sheet()

        if df is not None:
            # Analyze
            df = analyze_air_quality_data(df)

            # Save locally
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"air_quality_secure_{timestamp}.csv"
            df.to_csv(output_file)
            print(f"\n✓ Data saved to {output_file}")

            # Show data freshness
            if df.index.name and pd.api.types.is_datetime64_any_dtype(df.index):
                latest = df.index[-1]
                age = datetime.now() - latest
                print(f"\n🕐 Latest data: {latest.strftime('%Y-%m-%d %H:%M')}")
                print(f"   Age: {age.total_seconds() / 3600:.1f} hours")

                if age.total_seconds() > 3600:  # More than 1 hour old
                    print(
                        "\n⚠️  Data might be stale. Check if collector is running on Unifi Gateway"
                    )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check that google-credentials.json exists")
        print("2. Verify GOOGLE_SPREADSHEET_ID in .env")
        print("3. Ensure sheet is shared with service account email")


if __name__ == "__main__":
    main()
