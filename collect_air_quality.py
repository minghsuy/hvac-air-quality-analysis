#!/usr/bin/env python3
"""
Simple air quality collector
Compares indoor (Airthings) vs outdoor (AirGradient) to track filter efficiency
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
AIRTHINGS_CLIENT_ID = os.getenv("AIRTHINGS_CLIENT_ID", "your_client_id")
AIRTHINGS_CLIENT_SECRET = os.getenv("AIRTHINGS_CLIENT_SECRET", "your_secret")
AIRTHINGS_DEVICE_SERIAL = os.getenv("AIRTHINGS_DEVICE_SERIAL", "your_serial")

# AirGradient local API (no auth needed)
AIRGRADIENT_SERIAL = os.getenv("AIRGRADIENT_SERIAL", "your_serial")
AIRGRADIENT_URL = f"http://airgradient_{AIRGRADIENT_SERIAL}.local/measures/current"


def get_airthings_token():
    """Get Airthings access token"""
    payload = {
        "grant_type": "client_credentials",
        "client_id": AIRTHINGS_CLIENT_ID,
        "client_secret": AIRTHINGS_CLIENT_SECRET,
        "scope": ["read:device:current_values"],
    }

    response = requests.post(
        "https://accounts-api.airthings.com/v1/token", json=payload, timeout=10
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_airthings_data():
    """Get current indoor air quality from Airthings"""
    token = get_airthings_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Get account ID
    accounts = requests.get(
        "https://consumer-api.airthings.com/v1/accounts", headers=headers, timeout=10
    ).json()

    account_id = accounts["accounts"][0]["id"]

    # Get sensor data
    params = {"sn": [AIRTHINGS_DEVICE_SERIAL]} if AIRTHINGS_DEVICE_SERIAL else {}
    sensors = requests.get(
        f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
        headers=headers,
        params=params,
        timeout=10,
    ).json()

    # Extract key metrics
    if sensors["results"]:
        result = sensors["results"][0]
        data = {"battery": result.get("batteryPercentage"), "timestamp": result.get("recorded")}

        for sensor in result["sensors"]:
            data[sensor["sensorType"]] = sensor["value"]

        return data
    return None


def get_airgradient_data():
    """Get current outdoor air quality from AirGradient"""
    try:
        response = requests.get(AIRGRADIENT_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        # Use compensated values as recommended
        return {
            "pm25": data.get("pm02Compensated", 0),  # Use compensated PM2.5
            "temp": data.get("atmpCompensated", 0),  # Use compensated temp
            "humidity": data.get("rhumCompensated", 0),  # Use compensated humidity
            "co2": data.get("rco2", 0),
            "voc": data.get("tvocIndex", 0),
            "nox": data.get("noxIndex", 0),
            "raw_data": data,  # Keep full data for debugging
        }
    except Exception:
        # Sanitize error message to avoid information disclosure
        print("Failed to get AirGradient data: Connection error")
        # Log full error for debugging if needed
        # print(f"Debug: {e}")
        return None


def calculate_filter_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency percentage"""
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return max(0, min(100, efficiency))  # Clamp between 0-100%
    return 0


def send_to_google_sheets(data):
    """Send data to Google Sheets via Forms"""
    # Get form configuration from environment
    form_id = os.getenv("GOOGLE_FORM_ID")
    if not form_id:
        print("Google Form ID not configured")
        return False

    form_url = f"https://docs.google.com/forms/d/e/{form_id}/formResponse"

    # Map data to form fields
    form_data = {
        os.getenv("FORM_TIMESTAMP", ""): data.get("timestamp", ""),
        os.getenv("FORM_INDOOR_PM25", ""): data.get("indoor_pm25", ""),
        os.getenv("FORM_OUTDOOR_PM25", ""): data.get("outdoor_pm25", ""),
        os.getenv("FORM_EFFICIENCY", ""): data.get("filter_efficiency", ""),
        os.getenv("FORM_INDOOR_CO2", ""): data.get("indoor_co2", ""),
        os.getenv("FORM_INDOOR_VOC", ""): data.get("indoor_voc", ""),
        os.getenv("FORM_INDOOR_TEMP", ""): data.get("indoor_temp", ""),
        os.getenv("FORM_INDOOR_HUMIDITY", ""): data.get("indoor_humidity", ""),
        os.getenv("FORM_OUTDOOR_CO2", ""): data.get("outdoor_co2", ""),
        os.getenv("FORM_OUTDOOR_TEMP", ""): data.get("outdoor_temp", ""),
        os.getenv("FORM_OUTDOOR_HUMIDITY", ""): data.get("outdoor_humidity", ""),
        os.getenv("FORM_OUTDOOR_VOC", ""): data.get("outdoor_voc", ""),
        os.getenv("FORM_OUTDOOR_NOX", ""): data.get("outdoor_nox", ""),
    }

    # Remove empty keys
    form_data = {k: v for k, v in form_data.items() if k}

    try:
        response = requests.post(form_url, data=form_data, timeout=10)
        return response.status_code == 200
    except Exception:
        # Sanitize error message to avoid information disclosure
        print("Failed to send to Google Sheets: Submission error")
        # Log full error for debugging if needed
        # print(f"Debug: {e}")
        return False


def main():
    """Main collection routine"""
    print(f"Starting air quality collection at {datetime.now()}")

    # Get indoor data from Airthings
    indoor_data = get_airthings_data()
    if not indoor_data:
        print("Failed to get Airthings data")
        return

    # Get outdoor data from AirGradient
    outdoor_data = get_airgradient_data()
    if not outdoor_data:
        print("Failed to get AirGradient data")
        return

    # Extract key metrics
    indoor_pm25 = indoor_data.get("pm25", 0)
    outdoor_pm25 = outdoor_data.get("pm25", 0)  # Now using compensated value

    # Calculate efficiency
    efficiency = calculate_filter_efficiency(indoor_pm25, outdoor_pm25)

    # Prepare data for logging
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "indoor_pm25": indoor_pm25,
        "outdoor_pm25": outdoor_pm25,
        "filter_efficiency": round(efficiency, 1),
        "indoor_co2": indoor_data.get("co2", 0),
        "indoor_voc": indoor_data.get("voc", 0),
        "indoor_temp": indoor_data.get("temp", 0),
        "indoor_humidity": indoor_data.get("humidity", 0),
        "outdoor_co2": outdoor_data.get("co2", 0),
        "outdoor_temp": outdoor_data.get("temp", 0),
        "outdoor_humidity": outdoor_data.get("humidity", 0),
        "outdoor_voc": outdoor_data.get("voc", 0),
        "outdoor_nox": outdoor_data.get("nox", 0),
    }

    # Log locally
    print(f"Indoor PM2.5: {indoor_pm25} μg/m³")
    print(f"Outdoor PM2.5: {outdoor_pm25} μg/m³ (compensated)")
    print(f"Filter Efficiency: {efficiency:.1f}%")

    # Check if replacement needed (efficiency < 85% is concerning)
    if efficiency < 85 and outdoor_pm25 > 10:
        print("⚠️  WARNING: Filter efficiency is low! Consider replacement soon.")

    # Send to Google Sheets
    if send_to_google_sheets(log_data):
        print("✓ Data sent to Google Sheets")
    else:
        print("✗ Failed to send to Google Sheets")

    # Save locally as backup with secure permissions
    import stat

    temp_file = "/tmp/air_quality_latest.json"
    with open(temp_file, "w") as f:
        json.dump(log_data, f)
    # Set file permissions to 600 (read/write for owner only)
    os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)


if __name__ == "__main__":
    main()
