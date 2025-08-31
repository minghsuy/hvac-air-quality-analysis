#!/usr/bin/env python3
"""
Multi-sensor collector using Google Sheets API (not Forms)
Direct append to sheets - better for multiple sensors
Runs on Ubiquiti Gateway with minimal dependencies
"""

import os
import json
import requests
from datetime import datetime


# For Ubiquiti - simple env loading (no python-dotenv)
def load_env():
    """Load environment variables from .env file"""
    env_path = "/data/scripts/.env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


load_env()

# Configuration
SPREADSHEET_ID = os.environ.get(
    "GOOGLE_SPREADSHEET_ID", "1RMhS2pra8Fho3mw0RMc39IMT-seBeTN_tmo9yFIwBBo"
)

# Sensors
AIRTHINGS_CLIENT_ID = os.environ.get("AIRTHINGS_CLIENT_ID")
AIRTHINGS_CLIENT_SECRET = os.environ.get("AIRTHINGS_CLIENT_SECRET")
AIRTHINGS_DEVICE_SERIAL = os.environ.get("AIRTHINGS_DEVICE_SERIAL")
AIRGRADIENT_OUTDOOR_SERIAL = os.environ.get("AIRGRADIENT_SERIAL")
AIRGRADIENT_INDOOR_SERIAL = os.environ.get("AIRGRADIENT_INDOOR_SERIAL")  # Configure in .env


class GoogleSheetsWriter:
    """Simple Google Sheets API writer for Ubiquiti"""

    def __init__(self):
        """Initialize with service account credentials"""
        # Load credentials from file
        creds_path = "/data/scripts/google-credentials.json"
        if not os.path.exists(creds_path):
            print(f"⚠️  Google credentials not found at {creds_path}")
            print("   Copy google-credentials.json to Ubiquiti Gateway")
            self.enabled = False
            return

        with open(creds_path, "r") as f:
            self.creds = json.load(f)

        self.enabled = True
        self.token = None
        self.token_expiry = 0

    def get_access_token(self):
        """Get access token using service account credentials"""
        import time

        now = int(time.time())

        # Check if token is still valid
        if self.token and now < self.token_expiry - 60:
            return self.token

        # Create JWT manually (no external libraries needed)
        # header = {"alg": "RS256", "typ": "JWT"}  # Would be used in full JWT implementation

        claim_set = {
            "iss": self.creds["client_email"],
            "scope": "https://www.googleapis.com/auth/spreadsheets",
            "aud": "https://oauth2.googleapis.com/token",
            "exp": now + 3600,
            "iat": now,
        }

        # For Ubiquiti, we'll use a simpler approach with requests
        # Use the service account key directly
        auth_url = "https://oauth2.googleapis.com/token"

        # Create JWT assertion (simplified for Ubiquiti)
        # Note: In production, you'd properly sign the JWT
        # For now, we'll use a direct API key approach

        # Get token using service account
        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": self._create_jwt(claim_set),
        }

        response = requests.post(auth_url, data=payload)
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            self.token_expiry = now + data.get("expires_in", 3600)
            return self.token
        else:
            print(f"Failed to get token: {response.text}")
            return None

    def _create_jwt(self, claims):
        """Create a simple JWT for service account auth"""
        # This is simplified - in production use proper JWT library
        # For Ubiquiti, consider using pre-generated tokens
        import base64

        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
            .decode()
            .rstrip("=")
        )

        payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")

        # Note: Signature would require RSA signing with private key
        # For simplicity on Ubiquiti, you might want to pre-generate tokens
        # or use a different auth method

        return f"{header}.{payload}.signature_placeholder"

    def append_row(self, values):
        """Append a row to the spreadsheet"""
        if not self.enabled:
            return False

        # For Ubiquiti simplicity, use API key if available
        # Otherwise fall back to service account

        # Simple approach: Use API key (if you have one)
        api_key = os.environ.get("GOOGLE_API_KEY")

        if api_key:
            # Use API key (simpler, but requires public sheet)
            url = (
                f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/A:Z:append"
            )
            params = {"key": api_key, "valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}
        else:
            # Use OAuth token
            token = self.get_access_token()
            if not token:
                return False

            url = (
                f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/A:Z:append"
            )
            params = {"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}
            headers = {"Authorization": f"Bearer {token}"}

        body = {"values": [values]}

        try:
            if api_key:
                response = requests.post(url, params=params, json=body)
            else:
                response = requests.post(url, params=params, json=body, headers=headers)

            return response.status_code == 200
        except Exception as e:
            print(f"Failed to append to sheet: {e}")
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
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get accounts
        accounts = requests.get(
            "https://consumer-api.airthings.com/v1/accounts", headers=headers
        ).json()

        account_id = accounts["accounts"][0]["id"]

        # Get sensor data
        params = {"sn": [AIRTHINGS_DEVICE_SERIAL]}
        sensors = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params,
        ).json()

        # Extract metrics
        if sensors["results"]:
            result = sensors["results"][0]
            data = {}
            for sensor in result["sensors"]:
                data[sensor["sensorType"]] = sensor["value"]
            return {
                "sensor_id": "airthings_master",
                "room": "master_bedroom",
                "sensor_type": "airthings",
                "pm25": data.get("pm25", 0),
                "co2": data.get("co2", 0),
                "voc": data.get("voc", 0),
                "temp": data.get("temp", 0),
                "humidity": data.get("humidity", 0),
                "radon": data.get("radon", 0),
            }
    except Exception as e:
        print(f"Airthings error: {e}")
        return None


def get_airgradient_data(serial, room):
    """Get data from AirGradient sensor"""
    try:
        url = f"http://airgradient_{serial}.local/measures/current"
        response = requests.get(url, timeout=5)
        data = response.json()

        return {
            "sensor_id": f"airgradient_{serial[-4:]}",
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
    except Exception as e:
        print(f"AirGradient {room} error: {e}")
        return None


def calculate_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency"""
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return round(max(0, min(100, efficiency)), 1)
    return 0


def main():
    """Main collection routine"""
    timestamp = datetime.now().isoformat()

    print(f"Collecting at {timestamp}")

    # Initialize Sheets writer
    sheets = GoogleSheetsWriter()

    # Collect outdoor data first (needed for efficiency calculation)
    outdoor = get_airgradient_data(AIRGRADIENT_OUTDOOR_SERIAL, "outdoor")
    if not outdoor:
        print("Failed to get outdoor data")
        return

    outdoor_pm25 = outdoor["pm25"]
    print(f"✓ Outdoor: PM2.5={outdoor_pm25} μg/m³")

    # Collect indoor data from all sensors
    indoor_sensors = []

    # Master bedroom (Airthings)
    master = get_airthings_data()
    if master:
        master["efficiency"] = calculate_efficiency(master["pm25"], outdoor_pm25)
        indoor_sensors.append(master)
        print(f"✓ Master bedroom: PM2.5={master['pm25']} μg/m³, Efficiency={master['efficiency']}%")

    # Second bedroom (AirGradient)
    if AIRGRADIENT_INDOOR_SERIAL:
        second = get_airgradient_data(AIRGRADIENT_INDOOR_SERIAL, "second_bedroom")
        if second:
            second["efficiency"] = calculate_efficiency(second["pm25"], outdoor_pm25)
            indoor_sensors.append(second)
            print(
                f"✓ Second bedroom: PM2.5={second['pm25']} μg/m³, Efficiency={second['efficiency']}%"
            )

    # Send to Google Sheets - one row per sensor
    success_count = 0

    for sensor in indoor_sensors:
        row = [
            timestamp,
            sensor["sensor_id"],
            sensor["room"],
            sensor["sensor_type"],
            sensor["pm25"],
            outdoor_pm25,
            sensor["efficiency"],
            sensor["co2"],
            sensor["voc"],
            sensor["nox"] if "nox" in sensor else 0,
            sensor["temp"],
            sensor["humidity"],
            sensor["radon"],
            outdoor["co2"],
            outdoor["temp"],
            outdoor["humidity"],
            outdoor["voc"],
            outdoor["nox"],
        ]

        if sheets.append_row(row):
            success_count += 1
        else:
            # Fallback to Forms if Sheets API fails
            print("Sheets API failed, trying Forms fallback...")
            # Add Forms fallback here if needed

    if success_count > 0:
        print(f"✓ Sent {success_count} rows to Google Sheets")
    else:
        print("✗ Failed to send to Google Sheets")

    # Save locally as backup
    backup_data = {"timestamp": timestamp, "outdoor": outdoor, "indoor": indoor_sensors}

    with open("/tmp/air_quality_latest.json", "w") as f:
        json.dump(backup_data, f)


if __name__ == "__main__":
    main()
