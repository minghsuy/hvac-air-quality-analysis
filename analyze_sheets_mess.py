#!/usr/bin/env python3
"""
Analyze the Google Sheets data to understand the schema mess
"""

import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

def analyze_sheets_data():
    """Read and analyze the current state of Google Sheets data"""
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        "google-credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)
    
    SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
    if not SPREADSHEET_ID:
        print("Error: GOOGLE_SPREADSHEET_ID not set in .env")
        return
    
    print(f"Analyzing spreadsheet: {SPREADSHEET_ID}")
    print("=" * 60)
    
    try:
        # Get all data from the sheet
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="A:Z"  # Get all columns
        ).execute()
        
        values = result.get("values", [])
        
        if not values:
            print("No data found in sheet")
            return
        
        print(f"Total rows: {len(values)}")
        print(f"Headers row: {values[0] if values else 'No headers'}")
        print("\n" + "=" * 60)
        
        # Analyze different data schemas
        if len(values) > 1:
            # Check for old schema (before 2025-08-08)
            old_schema_count = 0
            new_schema_count = 0
            
            for i, row in enumerate(values[1:], start=2):  # Skip header
                if len(row) == 0:
                    continue
                    
                # Try to parse timestamp
                try:
                    timestamp_str = row[0]
                    # Check format
                    if "/" in timestamp_str:  # Old format like "8/7/2025 22:00:00"
                        old_schema_count += 1
                        if old_schema_count == 1:
                            print(f"\nOld schema example (row {i}):")
                            print(f"  Columns: {len(row)}")
                            print(f"  First 5 values: {row[:5]}")
                    else:  # New format like "2025-08-27T10:00:00"
                        new_schema_count += 1
                        if new_schema_count == 1:
                            print(f"\nNew schema example (row {i}):")
                            print(f"  Columns: {len(row)}")
                            print(f"  First 5 values: {row[:5]}")
                except (IndexError, ValueError, KeyError):
                    pass
            
            print("\n" + "=" * 60)
            print("Data Summary:")
            print(f"  Old schema rows (before Aug 8): {old_schema_count}")
            print(f"  New schema rows (after Aug 8): {new_schema_count}")
            
            # Find the transition point
            for i, row in enumerate(values[1:], start=2):
                if len(row) > 0:
                    try:
                        if "/" not in row[0] and i > 2:  # Found first new format
                            print(f"  Schema change at row {i}")
                            print(f"  Last old format: {values[i-2][0] if i > 2 else 'N/A'}")
                            print(f"  First new format: {row[0]}")
                            break
                    except (IndexError, ValueError, KeyError):
                        pass
        
        # Check column count variations
        print("\n" + "=" * 60)
        print("Column count analysis:")
        col_counts = {}
        for i, row in enumerate(values):
            col_count = len(row)
            if col_count not in col_counts:
                col_counts[col_count] = []
            col_counts[col_count].append(i + 1)
        
        for count, rows in sorted(col_counts.items()):
            if len(rows) > 10:
                print(f"  {count} columns: {len(rows)} rows (rows {rows[0]}-{rows[-1]})")
            else:
                print(f"  {count} columns: {len(rows)} rows (rows {rows})")
        
        # Show current headers vs expected headers
        print("\n" + "=" * 60)
        print("Header Analysis:")
        current_headers = values[0] if values else []
        
        expected_headers = [
            "Timestamp",
            "Sensor_ID",
            "Room",
            "Sensor_Type",
            "Indoor_PM25",
            "Outdoor_PM25",
            "Filter_Efficiency",
            "Indoor_CO2",
            "Indoor_VOC",
            "Indoor_NOX",
            "Indoor_Temp",
            "Indoor_Humidity",
            "Indoor_Radon",
            "Outdoor_CO2",
            "Outdoor_Temp",
            "Outdoor_Humidity",
            "Outdoor_VOC",
            "Outdoor_NOX",
        ]
        
        print(f"Current headers ({len(current_headers)} columns):")
        for i, header in enumerate(current_headers):
            print(f"  {i+1}. {header}")
        
        print(f"\nExpected headers ({len(expected_headers)} columns):")
        for i, header in enumerate(expected_headers):
            match = "✓" if i < len(current_headers) and current_headers[i] == header else "✗"
            print(f"  {i+1}. {header} {match}")
            
    except Exception as e:
        print(f"Error reading sheet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_sheets_data()