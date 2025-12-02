#!/usr/bin/env python3
"""
Multi-sensor collector using Google Sheets API instead of Forms
Handles multiple sensors properly with fallback path handling
"""

import os
import sys
import json
import requests
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build


# Simple env loading with fallback paths
def load_env():
    """Load environment variables from .env file"""
    # Try local .env first, then fallback paths
    env_paths = [".env", "/data/scripts/.env"]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ[key] = value
            break


load_env()

# Configuration
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID")
if not SPREADSHEET_ID:
    print("❌ Error: GOOGLE_SPREADSHEET_ID not set in environment")
    sys.exit(1)

# Try local credentials first, then fallback path
if os.path.exists("google-credentials.json"):
    CREDENTIALS_FILE = "google-credentials.json"
else:
    CREDENTIALS_FILE = "/data/scripts/google-credentials.json"

# Sensors
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL")
AIRGRADIENT_OUTDOOR_SERIAL = os.environ.get("AIRGRADIENT_SERIAL")
AIRGRADIENT_INDOOR_SERIAL = os.environ.get("AIRGRADIENT_INDOOR_SERIAL")  # Configure in .env


def get_sheets_service():
    """Get Google Sheets service using service account"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception:
        print("Failed to create Sheets service")
        return None


def ensure_headers(service, spreadsheet_id):
    """Ensure the sheet has proper headers for multi-sensor data"""
    try:
        sheet = service.spreadsheets()

        # Check if headers exist
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range="A1:R1").execute()

        values = result.get("values", [])

        # Expected headers for multi-sensor setup
        headers = [
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

        # If no headers or different headers, update them
        if not values or values[0] != headers:
            body = {"values": [headers]}
            sheet.values().update(
                spreadsheetId=spreadsheet_id, range="A1:R1", valueInputOption="RAW", body=body
            ).execute()
            print("✓ Headers updated for multi-sensor data")
            return True
    except Exception:
        pass
    return False


def append_to_sheet(service, spreadsheet_id, values):
    """Append a row to the spreadsheet"""
    try:
        body = {"values": [values]}

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range="A:R",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )

        return result.get("updates", {}).get("updatedRows", 0) > 0
    except Exception:
        print("Failed to append to sheet")
        return False


def get_airthings_data():
    """Get master bedroom data from Airthings"""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Get accounts
        accounts = requests.get(
            "https://consumer-api.airthings.com/v1/accounts", headers=headers, timeout=10
        ).json()

        account_id = accounts["accounts"][0]["id"]

        # Get sensor data
        params = {"sn": [AIRTHINGS_DEVICE_SERIAL]}
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params,
            timeout=10,
        ).json()

        # Extract metrics
        if sensors["results"]:
            result = sensors["results"][0]
            data = {}
            for sensor in result["sensors"]:
                data[sensor["sensorType"]] = sensor["value"]
            return {
                "sensor_id": f"airthings_{AIRTHINGS_DEVICE_SERIAL[-6:]}",
                "room": "master_bedroom",
                "sensor_type": "airthings",
                "pm25": data.get("pm25", 0),
                "co2": data.get("co2", 0),
                "voc": data.get("voc", 0),
                "nox": 0,  # Airthings doesn't have NOX
                "temp": data.get("temp", 0),
                "humidity": data.get("humidity", 0),
                "radon": data.get("radon", 0),
            }
    except Exception:
        print("Airthings API error")
        return None


def get_airgradient_data(serial, room):
    """Get data from AirGradient sensor"""
    try:
        url = f"http://airgradient_{serial}.local/measures/current"
        response = requests.get(url, timeout=5)
        data = response.json()

        return {
            "sensor_id": f"airgradient_{serial[-6:]}",
            "room": room,
            "sensor_type": "airgradient",
            "pm25": data.get("pm02Compensated", 0),
            "co2": data.get("rco2", 0),
            "voc": data.get("tvocIndex", 0),
            "nox": data.get("noxIndex", 0),
            "temp": data.get("atmpCompensated", 0),
            "humidity": data.get("rhumCompensated", 0),
            "radon": 0,  # AirGradient doesn't have radon
        }
    except Exception:
        print(f"AirGradient {room} connection error")
        return None


def calculate_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency"""
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return round(max(0, min(100, efficiency)), 1)
    return 0


def main():
    """Main collection routine"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'=' * 50}")
    print(f"Air Quality Collection - {timestamp}")
    print("=" * 50)

    # Get Sheets service
    service = get_sheets_service()
    if not service:
        print("❌ Failed to connect to Google Sheets API")
        print("Falling back to Forms method...")
        # Could fall back to Forms here
        return

    # Ensure headers are set
    ensure_headers(service, SPREADSHEET_ID)

    # Collect outdoor data first
    outdoor = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor")
    if not outdoor:
        print("❌ Failed to get outdoor data")
        return

    outdoor_pm25 = outdoor["pm25"]
    print(f"✓ Outdoor: PM2.5={outdoor_pm25} μg/m³")

    # Collect indoor data from all sensors
    rows_to_append = []

    # Master bedroom (Airthings)
    master = get_airthings_data()
    if master:
        efficiency = calculate_efficiency(master["pm25"], outdoor_pm25)
        print(f"✓ Master bedroom: PM2.5={master['pm25']} μg/m³, Efficiency={efficiency}%")

        row = [
            timestamp,
            master["sensor_id"],
            master["room"],
            master["sensor_type"],
            master["pm25"],
            outdoor_pm25,
            efficiency,
            master["co2"],
            master["voc"],
            master["nox"],
            master["temp"],
            master["humidity"],
            master["radon"],
            outdoor["co2"],
            outdoor["temp"],
            outdoor["humidity"],
            outdoor["voc"],
            outdoor["nox"],
        ]
        rows_to_append.append(row)

    # Second bedroom (AirGradient)
    if AIRGRADIENT_INDOOR_SERIAL:
        second = get_airgradient_data(AIRGRADIENT_INDOOR_SERIAL, "second_bedroom")
        if second:
            efficiency = calculate_efficiency(second["pm25"], outdoor_pm25)
            print(f"✓ Second bedroom: PM2.5={second['pm25']} μg/m³, Efficiency={efficiency}%")

            row = [
                timestamp,
                second["sensor_id"],
                second["room"],
                second["sensor_type"],
                second["pm25"],
                outdoor_pm25,
                efficiency,
                second["co2"],
                second["voc"],
                second["nox"],
                second["temp"],
                second["humidity"],
                second["radon"],
                outdoor["co2"],
                outdoor["temp"],
                outdoor["humidity"],
                outdoor["voc"],
                outdoor["nox"],
            ]
            rows_to_append.append(row)

    # Send all rows to Google Sheets
    success_count = 0
    for row in rows_to_append:
        if append_to_sheet(service, SPREADSHEET_ID, row):
            success_count += 1

    if success_count > 0:
        print(f"\n✅ Successfully sent {success_count}/{len(rows_to_append)} rows to Google Sheets")
    else:
        print("\n❌ Failed to send data to Google Sheets")

    # Save backup
    backup = {
        "timestamp": timestamp,
        "outdoor": outdoor,
        "indoor": [master, second] if second else [master],
    }

    with open("/tmp/air_quality_latest.json", "w") as f:
        json.dump(backup, f, indent=2)

    print("💾 Backup saved to /tmp/air_quality_latest.json")
    print("=" * 50)


if __name__ == "__main__":
    main()
