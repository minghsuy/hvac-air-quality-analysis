#!/usr/bin/env python3
"""
Test Airthings API connection and data append to Google Sheets
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

# Airthings config
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL", "")

# Google Sheets config
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID")
SHEET_TAB_NAME = os.environ.get("GOOGLE_SHEET_TAB", "Cleaned_Data_20250831")

print("=" * 60)
print("TESTING AIRTHINGS + GOOGLE SHEETS")
print("=" * 60)

# Test Airthings API
print("\n1. Testing Airthings API...")
try:
    # Get token
    response = requests.post(
        "https://accounts-api.airthings.com/v1/token",
        json={
            "grant_type": "client_credentials",
            "client_id": AIRTHINGS_CLIENT_ID,
            "client_secret": AIRTHINGS_CLIENT_SECRET,
            "scope": ["read:device:current_values"],
        },
        timeout=10,
    )
    token = response.json()["access_token"]
    print("   ✓ Got access token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get accounts
    accounts = requests.get(
        "https://consumer-api.airthings.com/v1/accounts", 
        headers=headers, 
        timeout=10
    ).json()
    
    if accounts.get("accounts"):
        account_id = accounts["accounts"][0]["id"]
        print(f"   ✓ Account ID: {account_id}")
        
        # Get sensor data - try without serial filter first
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            timeout=10,
        ).json()
        
        # API returns 'results' not 'sensors'
        
        if sensors.get("results"):
            result = sensors["results"][0]
            print(f"   ✓ Found sensor: {result.get('serialNumber', 'unknown')}")
            
            # Extract data from the sensor values
            data = {"pm25": 0, "co2": 0, "voc": 0, "temp": 0, "humidity": 0, "radon": 0}
            
            for sensor in result.get("sensors", []):
                sensor_type = sensor.get("sensorType")
                value = sensor.get("value", 0)
                
                if sensor_type == "pm25":
                    data["pm25"] = value
                elif sensor_type == "co2":
                    data["co2"] = value
                elif sensor_type == "voc":
                    data["voc"] = value
                elif sensor_type == "temp":
                    data["temp"] = value
                elif sensor_type == "humidity":
                    data["humidity"] = value
                elif sensor_type == "radonShortTermAvg":
                    data["radon"] = value
            
            print(f"   PM2.5: {data['pm25']} μg/m³")
            print(f"   CO2: {data['co2']} ppm")
            print(f"   Temp: {data['temp']}°C")
            print(f"   Humidity: {data['humidity']}%")
            
            # Now append to Google Sheets
            print("\n2. Appending to Google Sheets...")
            
            credentials = service_account.Credentials.from_service_account_file(
                "google-credentials.json",
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
            service = build("sheets", "v4", credentials=credentials)
            
            # Create row with real Airthings data
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Use dummy outdoor data since we can't reach AirGradient
            outdoor_pm25 = 10  # Dummy value
            efficiency = ((outdoor_pm25 - data['pm25']) / outdoor_pm25 * 100) if outdoor_pm25 > 0 else 0
            
            row = [
                timestamp,
                f"airthings_{AIRTHINGS_DEVICE_SERIAL[-6:] if AIRTHINGS_DEVICE_SERIAL else 'XXXXXX'}",
                "master_bedroom",
                "airthings",
                str(data['pm25']),
                str(outdoor_pm25),
                str(round(efficiency, 2)),
                str(data['co2']),
                str(data['voc']),
                "0",  # NOX
                str(data['temp']),
                str(data['humidity']),
                str(data['radon']),
                "420",  # Dummy outdoor CO2
                "25",   # Dummy outdoor temp
                "60",   # Dummy outdoor humidity
                "100",  # Dummy outdoor VOC
                "1",    # Dummy outdoor NOX
            ]
            
            # Append
            body = {"values": [row]}
            range_name = f"{SHEET_TAB_NAME}!A:R"
            
            result = service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()
            
            updated = result.get("updates", {})
            if updated.get("updatedRows", 0) > 0:
                print("   ✅ SUCCESS! Real Airthings data added")
                print(f"   Range: {updated.get('updatedRange', '')}")
                print(f"   Timestamp: {timestamp}")
                print("\n3. Check your Google Sheet for the new row!")
                print("   Then run the Apps Script test() function to verify")
            else:
                print("   ❌ No rows were updated")
                
        else:
            print("   ❌ No sensors found")
    else:
        print("   ❌ No accounts found")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()