#!/usr/bin/env python3
"""
Multi-sensor collector that dynamically finds AirGradient IPs
Works on Ubiquiti where .local doesn't resolve
"""

import os
import requests
import subprocess
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build


# Simple env loading
def load_env():
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
SPREADSHEET_ID = os.environ.get(
    "GOOGLE_SPREADSHEET_ID", "1RMhS2pra8Fho3mw0RMc39IMT-seBeTN_tmo9yFIwBBo"
)
CREDENTIALS_FILE = (
    "/data/scripts/google-credentials.json"
    if os.path.exists("/data/scripts/google-credentials.json")
    else "google-credentials.json"
)

# Sensors
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL")
AIRGRADIENT_OUTDOOR_SERIAL = os.environ.get("AIRGRADIENT_SERIAL")
AIRGRADIENT_INDOOR_SERIAL = os.environ.get("AIRGRADIENT_INDOOR_SERIAL")  # Configure in .env


def find_airgradient_ip(mac_suffix):
    """
    Find AirGradient IP by MAC address suffix
    MAC addresses are d8:3b:da:XX:XX:XX
    """
    try:
        # Method 1: Check ARP cache
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        lines = result.stdout.split("\n")

        for line in lines:
            if mac_suffix.lower() in line.lower():
                # Extract IP from line like: ? (192.168.X.XX) at d8:3b:da:XX:XX:XX
                parts = line.split()
                for part in parts:
                    if part.startswith("(") and part.endswith(")"):
                        return part[1:-1]  # Remove parentheses
                    # Sometimes IP is without parentheses
                    if "." in part and part.replace(".", "").isdigit():
                        return part

        # Method 2: Try to ping the network and refresh ARP
        # This is a bit aggressive but works on small networks
        print(f"Scanning network for {mac_suffix}...")
        subnet = os.environ.get("NETWORK_SUBNET", "192.168.X")  # Customize in .env if needed

        for i in range(1, 255):
            ip = f"{subnet}.{i}"
            # Quick ping with timeout
            subprocess.run(
                ["ping", "-c", "1", "-W", "1", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        # Check ARP again
        result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        lines = result.stdout.split("\n")

        for line in lines:
            if mac_suffix.lower() in line.lower():
                parts = line.split()
                for part in parts:
                    if part.startswith("(") and part.endswith(")"):
                        return part[1:-1]
                    if "." in part and part.count(".") == 3:
                        return part

    except Exception as e:
        print(f"Error finding IP for {mac_suffix}: {e}")

    return None


def test_airgradient_ip(ip):
    """Test if an IP responds like an AirGradient sensor"""
    try:
        response = requests.get(f"http://{ip}/measures/current", timeout=2)
        data = response.json()
        # Check if it has expected fields
        if "pm02Compensated" in data or "rco2" in data:
            return True
    except Exception:
        pass
    return False


def get_sheets_service():
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)
        return service
    except Exception as e:
        print(f"Failed to create Sheets service: {e}")
        return None


def ensure_headers(service, spreadsheet_id):
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range="A1:R1").execute()

        values = result.get("values", [])
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

        if not values or values[0] != headers:
            body = {"values": [headers]}
            sheet.values().update(
                spreadsheetId=spreadsheet_id, range="A1:R1", valueInputOption="RAW", body=body
            ).execute()
            print("✓ Headers updated")
    except Exception:
        pass


def append_to_sheet(service, spreadsheet_id, values):
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
    except Exception as e:
        print(f"Failed to append: {e}")
        return False


def get_airthings_data():
    try:
        response = requests.post(
            "https://accounts-api.airthings.com/v1/token",
            json={
                "grant_type": "client_credentials",
                "client_id": AIRTHINGS_CLIENT_ID,
                "client_secret": AIRTHINGS_CLIENT_SECRET,
                "scope": ["read:device:current_values"],
            },
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        accounts = requests.get(
            "https://consumer-api.airthings.com/v1/accounts", headers=headers
        ).json()

        account_id = accounts["accounts"][0]["id"]

        params = {"sn": [AIRTHINGS_DEVICE_SERIAL]}
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params,
        ).json()

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
                "nox": 0,
                "temp": data.get("temp", 0),
                "humidity": data.get("humidity", 0),
                "radon": data.get("radon", 0),
            }
    except Exception as e:
        print(f"Airthings error: {e}")
        return None


def get_airgradient_data(serial, room):
    """Get data from AirGradient sensor using dynamic IP lookup"""
    try:
        # First try .local (works on some systems)
        url = f"http://airgradient_{serial}.local/measures/current"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
        except Exception:
            # Fall back to finding IP by MAC
            print(f"Looking up IP for {serial}...")

            # Convert serial to MAC suffix (last 6 chars)
            mac_suffix = serial[-6:]  # e.g., "1c5f38" or "1cf228"

            # Try to find in ARP cache
            ip = find_airgradient_ip(mac_suffix)

            if not ip:
                # Try cached IPs from environment
                cached_ip = os.environ.get(f"AIRGRADIENT_{serial.upper()}_IP")
                if cached_ip and test_airgradient_ip(cached_ip):
                    ip = cached_ip
                else:
                    print(f"Could not find IP for {serial}")
                    return None

            print(f"Found {serial} at {ip}")

            # Cache the IP for next run (optional - write to .env)
            # This would require file writing logic

            url = f"http://{ip}/measures/current"
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
            "radon": 0,
        }
    except Exception as e:
        print(f"AirGradient {room} error: {e}")
        return None


def calculate_efficiency(indoor_pm25, outdoor_pm25):
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return round(max(0, min(100, efficiency)), 1)
    return 0


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'=' * 50}")
    print(f"Air Quality Collection - {timestamp}")
    print("=" * 50)

    service = get_sheets_service()
    if not service:
        print("❌ Failed to connect to Google Sheets API")
        return

    ensure_headers(service, SPREADSHEET_ID)

    # Get outdoor data
    outdoor = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor")
    if not outdoor:
        print("❌ Failed to get outdoor data")
        return

    outdoor_pm25 = outdoor["pm25"]
    print(f"✓ Outdoor: PM2.5={outdoor_pm25} μg/m³")

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

    # Send to Google Sheets
    success_count = 0
    for row in rows_to_append:
        if append_to_sheet(service, SPREADSHEET_ID, row):
            success_count += 1

    if success_count > 0:
        print(f"\n✅ Successfully sent {success_count}/{len(rows_to_append)} rows to Google Sheets")
    else:
        print("\n❌ Failed to send data to Google Sheets")

    print("=" * 50)


if __name__ == "__main__":
    main()
