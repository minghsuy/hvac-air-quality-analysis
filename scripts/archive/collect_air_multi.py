#!/usr/bin/env python3
"""
Multi-sensor air quality collector for Unifi Gateway
Supports Airthings (master bedroom) + AirGradient Indoor (second bedroom)
Lean design for embedded system - just collect and push data
"""

import os
import json
import requests
from datetime import datetime


# Simple env loading for Unifi (no python-dotenv)
def load_env():
    """Load environment variables from .env file"""
    env_path = "/data/scripts/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


# Load configuration
load_env()

# API credentials
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL")

# AirGradient sensors
AIRGRADIENT_OUTDOOR_SERIAL = os.environ.get("AIRGRADIENT_SERIAL")
AIRGRADIENT_INDOOR_SERIAL = os.environ.get("AIRGRADIENT_INDOOR_SERIAL")  # Configure in .env

# Google Forms
GOOGLE_FORM_ID = os.environ.get("GOOGLE_FORM_ID")


def get_airthings_token():
    """Get Airthings access token"""
    response = requests.post(
        "https://accounts-api.airthings.com/v1/token",
        json={
            "grant_type": "client_credentials",
            "client_id": AIRTHINGS_CLIENT_ID,
            "client_secret": AIRTHINGS_CLIENT_SECRET,
            "scope": ["read:device:current_values"],
        },
    )
    return response.json()["access_token"]


def get_airthings_data():
    """Get master bedroom data from Airthings"""
    try:
        token = get_airthings_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Get accounts
        accounts = requests.get(
            "https://consumer-api.airthings.com/v1/accounts", headers=headers
        ).json()

        account_id = accounts["accounts"][0]["id"]

        # Get sensor data
        params = {"sn": [AIRTHINGS_DEVICE_SERIAL]} if AIRTHINGS_DEVICE_SERIAL else {}
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params,
        ).json()

        # Extract key metrics
        if sensors["results"]:
            result = sensors["results"][0]
            data = {}
            for sensor in result["sensors"]:
                data[sensor["sensorType"]] = sensor["value"]
            return {
                "room": "master_bedroom",
                "pm25": data.get("pm25", 0),
                "co2": data.get("co2", 0),
                "voc": data.get("voc", 0),
                "temp": data.get("temp", 0),
                "humidity": data.get("humidity", 0),
                "radon": data.get("radon", 0),
            }
    except Exception as e:
        print(f"Failed to get Airthings data: {e}")
        return None


def get_airgradient_data(serial, location):
    """Get data from AirGradient sensor"""
    try:
        url = f"http://airgradient_{serial}.local/measures/current"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Use compensated values
        return {
            "room": location,
            "pm25": data.get("pm02Compensated", 0),
            "co2": data.get("rco2", 0),
            "voc": data.get("tvocIndex", 0),
            "nox": data.get("noxIndex", 0),
            "temp": data.get("atmpCompensated", 0),
            "humidity": data.get("rhumCompensated", 0),
        }
    except Exception as e:
        print(f"Failed to get AirGradient data from {location}: {e}")
        return None


def calculate_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency"""
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return max(0, min(100, efficiency))
    return 0


def send_to_google_forms(data):
    """Send data to Google Forms (existing method)"""
    if not GOOGLE_FORM_ID:
        print("Google Form ID not configured")
        return False

    form_url = f"https://docs.google.com/forms/d/e/{GOOGLE_FORM_ID}/formResponse"

    # For now, send master bedroom data (primary) with outdoor
    # TODO: Update form to handle multiple rooms
    master = data.get("master_bedroom", {})
    outdoor = data.get("outdoor", {})

    if not master or not outdoor:
        return False

    efficiency = calculate_efficiency(master["pm25"], outdoor["pm25"])

    form_data = {
        os.environ.get("FORM_TIMESTAMP", ""): datetime.now().isoformat(),
        os.environ.get("FORM_INDOOR_PM25", ""): master["pm25"],
        os.environ.get("FORM_OUTDOOR_PM25", ""): outdoor["pm25"],
        os.environ.get("FORM_EFFICIENCY", ""): round(efficiency, 1),
        os.environ.get("FORM_INDOOR_CO2", ""): master["co2"],
        os.environ.get("FORM_INDOOR_VOC", ""): master["voc"],
        os.environ.get("FORM_INDOOR_TEMP", ""): master["temp"],
        os.environ.get("FORM_INDOOR_HUMIDITY", ""): master["humidity"],
        os.environ.get("FORM_OUTDOOR_CO2", ""): outdoor["co2"],
        os.environ.get("FORM_OUTDOOR_TEMP", ""): outdoor["temp"],
        os.environ.get("FORM_OUTDOOR_HUMIDITY", ""): outdoor["humidity"],
        os.environ.get("FORM_OUTDOOR_VOC", ""): outdoor.get("voc", 0),
        os.environ.get("FORM_OUTDOOR_NOX", ""): outdoor.get("nox", 0),
    }

    # Remove empty keys
    form_data = {k: v for k, v in form_data.items() if k}

    try:
        response = requests.post(form_url, data=form_data)
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send to Google Forms: {e}")
        return False


def main():
    """Main collection routine"""
    timestamp = datetime.now()
    all_data = {}

    # Collect from all sensors
    print(f"Collecting at {timestamp}")

    # Master bedroom (Airthings)
    master_data = get_airthings_data()
    if master_data:
        all_data["master_bedroom"] = master_data
        print(f"✓ Master bedroom: PM2.5={master_data['pm25']} μg/m³")

    # Second bedroom (AirGradient Indoor)
    if AIRGRADIENT_INDOOR_SERIAL:
        second_data = get_airgradient_data(AIRGRADIENT_INDOOR_SERIAL, "second_bedroom")
        if second_data:
            all_data["second_bedroom"] = second_data
            print(f"✓ Second bedroom: PM2.5={second_data['pm25']} μg/m³")

    # Outdoor (AirGradient)
    outdoor_data = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor")
    if outdoor_data:
        all_data["outdoor"] = outdoor_data
        print(f"✓ Outdoor: PM2.5={outdoor_data['pm25']} μg/m³")

    # Calculate and display efficiency for each room
    if "outdoor" in all_data:
        outdoor_pm25 = all_data["outdoor"]["pm25"]

        for room in ["master_bedroom", "second_bedroom"]:
            if room in all_data:
                indoor_pm25 = all_data[room]["pm25"]
                efficiency = calculate_efficiency(indoor_pm25, outdoor_pm25)
                print(f"  {room}: Efficiency={efficiency:.1f}%")

                # Alert if low efficiency
                if efficiency < 85 and outdoor_pm25 > 10:
                    print(f"⚠️  {room}: Low efficiency!")

    # Send to Google Forms (for now, just master bedroom)
    if send_to_google_forms(all_data):
        print("✓ Data sent to Google Sheets")

    # Save locally as backup
    with open("/tmp/air_quality_latest.json", "w") as f:
        json.dump(all_data, f)


if __name__ == "__main__":
    main()
