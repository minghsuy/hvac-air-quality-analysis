#!/usr/bin/env python3
"""
Multi-sensor collector using Google Sheets API - Version 2
Updated to write to a specific sheet tab (for cleaned data)
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Configuration
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL", "")

# AirGradient sensors
AIRGRADIENT_OUTDOOR_SERIAL = os.environ.get("AIRGRADIENT_SERIAL", "")
AIRGRADIENT_INDOOR_SERIAL = os.environ.get("AIRGRADIENT_INDOOR_SERIAL", "")

# Temp Stick WiFi sensor (attic)
TEMP_STICK_API_KEY = os.environ.get("TEMP_STICK_API_KEY", "")
TEMP_STICK_SENSOR_ID = os.environ.get("TEMP_STICK_SENSOR_ID", "")

# Local network - use actual IPs from environment or config
OUTDOOR_IP = os.environ.get("AIRGRADIENT_OUTDOOR_IP", "192.168.X.XX")
INDOOR_IP = os.environ.get("AIRGRADIENT_INDOOR_IP", "192.168.X.XX")

# Google Sheets configuration - ALL FROM ENVIRONMENT VARIABLES
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID", "")

# Sheet tab name - use environment variable or default to main sheet
SHEET_TAB_NAME = os.environ.get("GOOGLE_SHEET_TAB", "")  # Empty string means use main sheet

# Local paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_CREDS = os.path.join(SCRIPT_DIR, "google-credentials.json")

# For testing locally, use the credentials from the main directory
if not os.path.exists(GOOGLE_CREDS):
    GOOGLE_CREDS = "google-credentials.json"

if SHEET_TAB_NAME:
    print(f"🔧 Using sheet tab: {SHEET_TAB_NAME}")
else:
    print("🔧 Using main sheet (no tab specified)")


def get_sheets_service():
    """Create Google Sheets API service using service account"""
    try:
        if not os.path.exists(GOOGLE_CREDS):
            print(f"❌ Credentials file not found: {GOOGLE_CREDS}")
            return None

        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDS, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        service = build("sheets", "v4", credentials=credentials)
        print("✓ Connected to Google Sheets API")
        return service
    except Exception as e:
        print(f"Failed to create Sheets service: {e}")
        return None


def ensure_headers(service, spreadsheet_id):
    """Ensure the sheet has proper headers for multi-sensor data"""
    try:
        sheet = service.spreadsheets()

        # Build range based on whether we're using a specific tab
        if SHEET_TAB_NAME:
            range_name = f"{SHEET_TAB_NAME}!A1:R1"
        else:
            range_name = "A1:R1"

        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()

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
                spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="RAW", body=body
            ).execute()
            location = SHEET_TAB_NAME if SHEET_TAB_NAME else "main sheet"
            print(f"✓ Headers updated in {location}")
            return True
        else:
            location = SHEET_TAB_NAME if SHEET_TAB_NAME else "main sheet"
            print(f"✓ Headers already correct in {location}")
            return True
    except HttpError as e:
        if "Unable to parse range" in str(e) and SHEET_TAB_NAME:
            print(f"❌ Sheet tab '{SHEET_TAB_NAME}' not found!")
            print("   Please check the tab name or create it first")
            print("   Or remove GOOGLE_SHEET_TAB from .env to use main sheet")
        else:
            print(f"❌ Error checking headers: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    return False


def append_to_sheet(service, spreadsheet_id, values):
    """Append a row to the spreadsheet"""
    try:
        body = {"values": [values]}

        # Build range based on whether we're using a specific tab
        if SHEET_TAB_NAME:
            range_name = f"{SHEET_TAB_NAME}!A:R"
        else:
            range_name = "A:R"

        result = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )

        updated_rows = result.get("updates", {}).get("updatedRows", 0)
        if updated_rows > 0:
            updated_range = result.get("updates", {}).get("updatedRange", "")
            print(f"  ✓ Added row to {updated_range}")
        return updated_rows > 0
    except HttpError as e:
        if "Unable to parse range" in str(e) and SHEET_TAB_NAME:
            print(f"❌ Sheet tab '{SHEET_TAB_NAME}' not found!")
        else:
            print(f"❌ Failed to append: {e}")
    except Exception as e:
        print(f"❌ Failed to append to sheet: {e}")
    return False


def get_airthings_data():
    """Get data from Airthings sensor"""
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

        if not accounts.get("accounts"):
            return None

        account_id = accounts["accounts"][0]["id"]

        # Get sensor data
        params = {"sn": [AIRTHINGS_DEVICE_SERIAL]} if AIRTHINGS_DEVICE_SERIAL else {}
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params,
            timeout=10,
        ).json()

        # Use last 6 chars of serial for sensor ID
        serial_suffix = AIRTHINGS_DEVICE_SERIAL[-6:] if AIRTHINGS_DEVICE_SERIAL else "unknown"

        # Check both old and new API response formats
        if sensors.get("results"):
            # New format (as of Aug 2025)
            result = sensors["results"][0]
            sensor_data = {}
            for s in result.get("sensors", []):
                sensor_data[s["sensorType"]] = s["value"]

            return {
                "sensor_id": f"airthings_{serial_suffix}",
                "room": "master_bedroom",
                "sensor_type": "airthings",
                "pm25": sensor_data.get("pm25", 0),
                "co2": sensor_data.get("co2", 0),
                "voc": sensor_data.get("voc", 0),
                "nox": "",  # Airthings doesn't have NOX
                "temp": sensor_data.get("temp", 0),
                "humidity": sensor_data.get("humidity", 0),
                "radon": sensor_data.get("radonShortTermAvg", 0),
            }
        elif sensors.get("sensors"):
            # Old format (legacy)
            sensor = sensors["sensors"][0]
            return {
                "sensor_id": f"airthings_{serial_suffix}",
                "room": "master_bedroom",
                "sensor_type": "airthings",
                "pm25": sensor.get("pm25", 0),
                "co2": sensor.get("co2", 0),
                "voc": sensor.get("voc", 0),
                "nox": "",  # Airthings doesn't have NOX
                "temp": sensor.get("temp", 0),
                "humidity": sensor.get("humidity", 0),
                "radon": sensor.get("radonShortTermAvg", 0),
            }
    except Exception as e:
        print(f"Airthings API error: {e}")
        return None


def get_airgradient_data(serial, room, ip=None):
    """Get data from AirGradient sensor"""
    try:
        # Try mDNS first, then fall back to IP
        urls = []
        if serial and serial != "XXXXXX":
            urls.append(f"http://airgradient_{serial}.local/measures/current")
        if ip and ip != "192.168.X.XX":
            urls.append(f"http://{ip}/measures/current")

        if not urls:
            print(f"  ⚠️ No valid URL for {room} sensor")
            return None

        for url in urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Extract last 6 chars of serial for sensor ID
                    sensor_id = (
                        f"airgradient_{serial[-6:]}"
                        if serial and serial != "XXXXXX"
                        else f"airgradient_{room[:3]}"
                    )

                    return {
                        "sensor_id": sensor_id,
                        "room": room,
                        "sensor_type": "airgradient",
                        "pm25": data.get(
                            "pm02Compensated", data.get("pm02", 0)
                        ),  # Use compensated value if available
                        "co2": data.get("rco2", 0),
                        "voc": data.get("tvocIndex", 0),  # Fixed: camelCase field name
                        "nox": data.get("noxIndex", 0),  # Fixed: camelCase field name
                        "temp": data.get(
                            "atmpCompensated", data.get("atmp", 0)
                        ),  # Use compensated temp too
                        "humidity": data.get(
                            "rhumCompensated", data.get("rhum", 0)
                        ),  # And humidity
                        "radon": "",  # Empty string for missing data
                        "raw_data": data,
                    }
            except (requests.RequestException, KeyError, ValueError):
                continue

        print(f"  ⚠️ Could not reach {room} sensor")
        return None

    except Exception as e:
        print(f"AirGradient {room} connection error: {e}")
        return None


def get_tempstick_data():
    """Get temperature/humidity data from Temp Stick WiFi sensor in attic"""
    if not TEMP_STICK_API_KEY or not TEMP_STICK_SENSOR_ID:
        return None

    try:
        response = requests.get(
            f"https://tempstickapi.com/api/v1/sensor/{TEMP_STICK_SENSOR_ID}",
            headers={"X-API-KEY": TEMP_STICK_API_KEY},
            timeout=10,
        )

        if response.status_code != 200:
            print(f"  ⚠️ Temp Stick API returned status {response.status_code}")
            return None

        data = response.json().get("data", {})

        # Temp Stick API returns °C (dashboard displays °F but API is metric)
        temp_c = data.get("last_temp")
        if temp_c is not None:
            temp_c = round(temp_c, 2)
        else:
            temp_c = ""

        humidity = data.get("last_humidity", "")

        return {
            "sensor_id": f"tempstick_{TEMP_STICK_SENSOR_ID[-4:]}",
            "room": "attic",
            "sensor_type": "tempstick",
            "temp": temp_c,
            "humidity": humidity,
        }
    except Exception as e:
        print(f"Temp Stick API error: {e}")
        return None


def calculate_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency percentage"""
    if outdoor_pm25 <= 0:
        return 100.0 if indoor_pm25 <= 0 else 0.0
    efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
    return round(max(0, min(100, efficiency)), 2)


def build_air_quality_row(timestamp, sensor, outdoor, efficiency):
    """Build a sheet row for an air quality sensor with PM2.5 and outdoor data"""
    return [
        timestamp,
        sensor["sensor_id"],
        sensor["room"],
        sensor["sensor_type"],
        sensor["pm25"],
        outdoor["pm25"],
        efficiency,
        sensor["co2"],
        sensor["voc"],
        sensor["nox"],
        sensor["temp"],
        sensor["humidity"],
        sensor["radon"],
        outdoor["co2"],
        outdoor["temp"],
        outdoor["humidity"],
        outdoor["voc"],
        outdoor["nox"],
    ]


def build_temp_only_row(timestamp, sensor):
    """Build a sheet row for a temp/humidity-only sensor (empty air quality fields)"""
    return [
        timestamp,
        sensor["sensor_id"],
        sensor["room"],
        sensor["sensor_type"],
        "",  # Indoor_PM25
        "",  # Outdoor_PM25
        "",  # Filter_Efficiency
        "",  # Indoor_CO2
        "",  # Indoor_VOC
        "",  # Indoor_NOX
        sensor["temp"],
        sensor["humidity"],
        "",  # Indoor_Radon
        "",  # Outdoor_CO2
        "",  # Outdoor_Temp
        "",  # Outdoor_Humidity
        "",  # Outdoor_VOC
        "",  # Outdoor_NOX
    ]


def test_local():
    """Test the collection locally before deploying"""
    print("\n" + "=" * 60)
    print("🧪 TESTING GOOGLE SHEETS DATA COLLECTION")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n📅 Timestamp: {timestamp}")

    # Show configuration
    print("\n⚙️ Configuration:")
    print(
        f"  Spreadsheet ID: {SPREADSHEET_ID[:10]}..."
        if SPREADSHEET_ID
        else "  Spreadsheet ID: NOT SET"
    )
    if SHEET_TAB_NAME:
        print(f"  Sheet Tab: {SHEET_TAB_NAME}")
    else:
        print("  Sheet Tab: Using main sheet")

    # Connect to Google Sheets
    print("\n🔌 Connecting to Google Sheets...")
    service = get_sheets_service()
    if not service:
        print("❌ Failed to connect to Google Sheets API")
        return False

    # Check headers
    location = f"'{SHEET_TAB_NAME}'" if SHEET_TAB_NAME else "main sheet"
    print(f"\n📋 Checking headers in {location}...")
    if not ensure_headers(service, SPREADSHEET_ID):
        print("❌ Could not verify headers")
        return False

    # Collect outdoor data
    print("\n🌡️ Collecting outdoor data...")
    outdoor = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor", OUTDOOR_IP)
    if not outdoor:
        print("❌ Failed to get outdoor data")
        # Use dummy data for testing
        print("  Using dummy outdoor data for testing...")
        outdoor = {
            "pm25": 10,
            "co2": 420,
            "voc": 100,
            "nox": 1,
            "temp": 25,
            "humidity": 50,
            "radon": 0,
        }
    else:
        print(f"  ✓ Outdoor PM2.5: {outdoor['pm25']} μg/m³")

    outdoor_pm25 = outdoor["pm25"]

    # Test data rows
    test_rows = []

    # Collect master bedroom (Airthings)
    print("\n🛏️ Collecting master bedroom data...")
    master = get_airthings_data()
    if master:
        efficiency = calculate_efficiency(master["pm25"], outdoor_pm25)
        print(f"  ✓ Master PM2.5: {master['pm25']} μg/m³")
        print(f"  ✓ Filter Efficiency: {efficiency}%")
        test_rows.append(build_air_quality_row(timestamp, master, outdoor, efficiency))
    else:
        print("  ⚠️ No Airthings data available")

    # Collect second bedroom (AirGradient)
    if AIRGRADIENT_INDOOR_SERIAL:
        print("\n🛏️ Collecting second bedroom data...")
        second = get_airgradient_data(AIRGRADIENT_INDOOR_SERIAL, "second_bedroom", INDOOR_IP)
        if second:
            efficiency = calculate_efficiency(second["pm25"], outdoor_pm25)
            print(f"  ✓ Second bedroom PM2.5: {second['pm25']} μg/m³")
            print(f"  ✓ Filter Efficiency: {efficiency}%")
            test_rows.append(build_air_quality_row(timestamp, second, outdoor, efficiency))
        else:
            print("  ⚠️ No second bedroom data available")

    # Collect attic data (Temp Stick)
    print("\n🌡️ Collecting attic data...")
    attic = get_tempstick_data()
    if attic:
        print(f"  ✓ Attic Temp: {attic['temp']}°C")
        print(f"  ✓ Attic Humidity: {attic['humidity']}%")
        test_rows.append(build_temp_only_row(timestamp, attic))
    else:
        print("  ⚠️ No attic data available (Temp Stick not configured or unreachable)")

    # Send test data to Google Sheets
    if test_rows:
        print(f"\n📤 Sending {len(test_rows)} row(s) to Google Sheets...")
        success_count = 0
        for row in test_rows:
            if append_to_sheet(service, SPREADSHEET_ID, row):
                success_count += 1

        if success_count > 0:
            print(f"\n✅ Successfully sent {success_count}/{len(test_rows)} rows to {location}")
            print("   Check your Google Sheet to verify the data!")
            return True
        else:
            print("\n❌ Failed to send data to Google Sheets")
            return False
    else:
        print("\n⚠️ No data collected to send")
        return False


def main():
    """Main collection function for production use"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Connect to Google Sheets
    service = get_sheets_service()
    if not service:
        print("❌ Failed to connect to Google Sheets API")
        return

    # Ensure headers are set
    ensure_headers(service, SPREADSHEET_ID)

    # Collect outdoor data first
    outdoor = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor", OUTDOOR_IP)
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
        rows_to_append.append(build_air_quality_row(timestamp, master, outdoor, efficiency))

    # Second bedroom (AirGradient)
    if AIRGRADIENT_INDOOR_SERIAL:
        second = get_airgradient_data(AIRGRADIENT_INDOOR_SERIAL, "second_bedroom", INDOOR_IP)
        if second:
            efficiency = calculate_efficiency(second["pm25"], outdoor_pm25)
            print(f"✓ Second bedroom: PM2.5={second['pm25']} μg/m³, Efficiency={efficiency}%")
            rows_to_append.append(build_air_quality_row(timestamp, second, outdoor, efficiency))

    # Attic (Temp Stick) - temp/humidity only
    attic = get_tempstick_data()
    if attic:
        print(f"✓ Attic: Temp={attic['temp']}°C, Humidity={attic['humidity']}%")
        rows_to_append.append(build_temp_only_row(timestamp, attic))

    # Send all rows to Google Sheets
    success_count = 0
    for row in rows_to_append:
        if append_to_sheet(service, SPREADSHEET_ID, row):
            success_count += 1

    if success_count > 0:
        location = SHEET_TAB_NAME if SHEET_TAB_NAME else "main sheet"
        print(f"\n✅ Successfully sent {success_count}/{len(rows_to_append)} rows to {location}")
    else:
        print("\n❌ Failed to send data to Google Sheets")


if __name__ == "__main__":
    import sys

    # Validate required configuration
    if not SPREADSHEET_ID:
        print("❌ Error: GOOGLE_SPREADSHEET_ID not set in .env file")
        sys.exit(1)

    # Add instructions
    if len(sys.argv) == 1:
        print("\nUsage:")
        print("  python collect_with_sheets_api_v2.py        # Run normal collection")
        print("  python collect_with_sheets_api_v2.py --test # Test mode with verbose output")
        print("\nMake sure your .env file contains:")
        print("  GOOGLE_SPREADSHEET_ID=your_sheet_id")
        print("  GOOGLE_SHEET_TAB=Cleaned_Data_20250831  # Optional, for specific tab")
        print("")

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running in TEST mode...")
        test_local()
    else:
        main()
