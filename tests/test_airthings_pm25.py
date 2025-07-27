#!/usr/bin/env python3
"""
Test script to verify Airthings PM2.5 data collection
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
AIRTHINGS_CLIENT_ID = os.getenv('AIRTHINGS_CLIENT_ID')
AIRTHINGS_CLIENT_SECRET = os.getenv('AIRTHINGS_CLIENT_SECRET')
AIRTHINGS_DEVICE_SERIAL = os.getenv('AIRTHINGS_DEVICE_SERIAL')

def get_airthings_token():
    """Get Airthings access token"""
    print("1. Getting Airthings access token...")
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": AIRTHINGS_CLIENT_ID,
        "client_secret": AIRTHINGS_CLIENT_SECRET,
        "scope": ["read:device:current_values"]
    }
    
    try:
        response = requests.post(
            "https://accounts-api.airthings.com/v1/token",
            json=payload
        )
        response.raise_for_status()
        token = response.json()['access_token']
        print("✓ Successfully got access token")
        return token
    except Exception as e:
        print(f"✗ Failed to get token: {e}")
        return None

def test_airthings_connection():
    """Test connection and data retrieval from Airthings"""
    print("\n=== Testing Airthings PM2.5 Data Collection ===\n")
    
    # Check environment variables
    print("Checking configuration...")
    if not all([AIRTHINGS_CLIENT_ID, AIRTHINGS_CLIENT_SECRET, AIRTHINGS_DEVICE_SERIAL]):
        print("✗ Missing environment variables!")
        print(f"  AIRTHINGS_CLIENT_ID: {'✓' if AIRTHINGS_CLIENT_ID else '✗'}")
        print(f"  AIRTHINGS_CLIENT_SECRET: {'✓' if AIRTHINGS_CLIENT_SECRET else '✗'}")
        print(f"  AIRTHINGS_DEVICE_SERIAL: {'✓' if AIRTHINGS_DEVICE_SERIAL else '✗'}")
        return
    
    print("✓ All environment variables present")
    print(f"  Device Serial: {AIRTHINGS_DEVICE_SERIAL}")
    
    # Get token
    token = get_airthings_token()
    if not token:
        return
    
    # Get account info
    print("\n2. Getting account information...")
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        accounts = requests.get(
            "https://consumer-api.airthings.com/v1/accounts",
            headers=headers
        ).json()
        
        if 'accounts' in accounts and accounts['accounts']:
            account_id = accounts['accounts'][0]['id']
            print(f"✓ Found account ID: {account_id}")
        else:
            print("✗ No accounts found")
            return
    except Exception as e:
        print(f"✗ Failed to get accounts: {e}")
        return
    
    # Get sensor data
    print(f"\n3. Getting sensor data for device {AIRTHINGS_DEVICE_SERIAL}...")
    
    try:
        params = {'sn': [AIRTHINGS_DEVICE_SERIAL]}
        response = requests.get(
            f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
            headers=headers,
            params=params
        )
        sensors = response.json()
        
        if 'results' not in sensors or not sensors['results']:
            print("✗ No sensor data found")
            print(f"Response: {json.dumps(sensors, indent=2)}")
            return
        
        result = sensors['results'][0]
        print(f"✓ Got sensor data from device")
        print(f"  Battery: {result.get('batteryPercentage')}%")
        print(f"  Last update: {result.get('recorded')}")
        
        # Look for PM2.5 sensor
        print("\n4. Checking for PM2.5 sensor...")
        pm25_found = False
        
        for sensor in result.get('sensors', []):
            sensor_type = sensor.get('sensorType')
            value = sensor.get('value')
            unit = sensor.get('unit', '')
            
            print(f"  - {sensor_type}: {value} {unit}")
            
            if sensor_type == 'pm25':
                pm25_found = True
                print(f"\n✓ PM2.5 sensor found!")
                print(f"  Current PM2.5: {value} {unit}")
                
                # Check if value is reasonable
                if value is not None and 0 <= value <= 500:
                    print(f"  Status: Valid reading")
                else:
                    print(f"  Status: Unusual value - please check sensor")
        
        if not pm25_found:
            print("\n✗ PM2.5 sensor NOT found in device data")
            print("  Available sensors:")
            for sensor in result.get('sensors', []):
                print(f"    - {sensor.get('sensorType')}")
            
            print("\n  Possible issues:")
            print("  1. Device doesn't have PM2.5 sensor")
            print("  2. PM2.5 sensor is disabled or not calibrated")
            print("  3. Wrong device serial number")
        
        # Save full response for debugging
        debug_file = 'airthings_debug.json'
        with open(debug_file, 'w') as f:
            json.dump(sensors, f, indent=2)
        print(f"\n✓ Full response saved to {debug_file} for debugging")
        
    except Exception as e:
        print(f"✗ Failed to get sensor data: {e}")
        return

if __name__ == "__main__":
    test_airthings_connection()