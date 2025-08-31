#!/usr/bin/env python3
"""
Simple test to verify we can append data to the cleaned sheet
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID")
SHEET_TAB_NAME = os.environ.get("GOOGLE_SHEET_TAB", "Cleaned_Data_20250831")

print(f"Testing append to: {SHEET_TAB_NAME}")

# Connect to Google Sheets
credentials = service_account.Credentials.from_service_account_file(
    "google-credentials.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
service = build("sheets", "v4", credentials=credentials)

# Create test row with dummy data
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
test_row = [
    timestamp,                # Timestamp
    "test_sensor",           # Sensor_ID
    "test_room",             # Room
    "test",                  # Sensor_Type
    "3",                     # Indoor_PM25
    "10",                    # Outdoor_PM25
    "70",                    # Filter_Efficiency
    "450",                   # Indoor_CO2
    "50",                    # Indoor_VOC
    "0",                     # Indoor_NOX
    "22.5",                  # Indoor_Temp
    "45",                    # Indoor_Humidity
    "0",                     # Indoor_Radon
    "420",                   # Outdoor_CO2
    "25",                    # Outdoor_Temp
    "60",                    # Outdoor_Humidity
    "100",                   # Outdoor_VOC
    "1",                     # Outdoor_NOX
]

# Append the test row
body = {"values": [test_row]}
range_name = f"{SHEET_TAB_NAME}!A:R"

try:
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    
    updated = result.get("updates", {})
    if updated.get("updatedRows", 0) > 0:
        print(f"✅ SUCCESS! Test row added to {updated.get('updatedRange', '')}")
        print(f"   Timestamp: {timestamp}")
        print("   Go check your Google Sheet!")
    else:
        print("❌ No rows were updated")
        
except Exception as e:
    print(f"❌ Error: {e}")