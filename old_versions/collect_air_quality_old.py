#!/usr/bin/env python3
"""
Simple air quality collector for Unifi Gateway
Compares indoor (Airthings) vs outdoor (AirGradient) to track filter efficiency
"""

import os
import json
import requests
from datetime import datetime
import time

# Configuration
AIRTHINGS_CLIENT_ID = os.getenv('AIRTHINGS_CLIENT_ID', 'your_client_id')
AIRTHINGS_CLIENT_SECRET = os.getenv('AIRTHINGS_CLIENT_SECRET', 'your_secret')
AIRTHINGS_DEVICE_SERIAL = os.getenv('AIRTHINGS_DEVICE_SERIAL', 'your_serial')

# AirGradient local API (no auth needed)
AIRGRADIENT_SERIAL = os.getenv('AIRGRADIENT_SERIAL', 'your_serial')
AIRGRADIENT_URL = f"http://airgradient_{AIRGRADIENT_SERIAL}.local/measures/current"

# Google Sheets webhook (we'll use Google Forms for simplicity)
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/[FORM_ID]/formResponse"
FORM_FIELD_MAPPING = {
    'timestamp': 'entry.123456',  # Update with your field IDs
    'indoor_pm25': 'entry.234567',
    'outdoor_pm25': 'entry.345678',
    'filter_efficiency': 'entry.456789',
    'indoor_co2': 'entry.567890',
    'indoor_voc': 'entry.678901',
    'days_since_install': 'entry.789012'
}

# Filter installation dates
HVAC_INSTALL_DATE = "2025-02-25"  # Update with your actual date
ERV_INSTALL_DATE = "2025-03-15"   # Update with your actual date
FILTER_UPGRADE_DATE = "2025-06-01" # MERV 8 to MERV 13

def get_airthings_token():
    """Get Airthings access token"""
    payload = {
        "grant_type": "client_credentials",
        "client_id": AIRTHINGS_CLIENT_ID,
        "client_secret": AIRTHINGS_CLIENT_SECRET,
        "scope": ["read:device:current_values"]
    }
    
    response = requests.post(
        "https://accounts-api.airthings.com/v1/token",
        json=payload
    )
    response.raise_for_status()
    return response.json()['access_token']

def get_airthings_data():
    """Get current indoor air quality from Airthings"""
    token = get_airthings_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get account ID
    accounts = requests.get(
        "https://consumer-api.airthings.com/v1/accounts",
        headers=headers
    ).json()
    
    account_id = accounts['accounts'][0]['id']
    
    # Get sensor data
    params = {'sn': [AIRTHINGS_DEVICE_SERIAL]} if AIRTHINGS_DEVICE_SERIAL else {}
    sensors = requests.get(
        f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
        headers=headers,
        params=params
    ).json()
    
    # Extract key metrics
    if sensors['results']:
        result = sensors['results'][0]
        data = {
            'battery': result.get('batteryPercentage'),
            'timestamp': result.get('recorded')
        }
        
        for sensor in result['sensors']:
            data[sensor['sensorType']] = sensor['value']
            
        return data
    return None

def get_airgradient_data():
    """Get current outdoor air quality from AirGradient"""
    try:
        response = requests.get(AIRGRADIENT_URL, timeout=5)
        response.raise_for_status()
        return response.json()
    except:
        print("Failed to get AirGradient data")
        return None

def calculate_filter_efficiency(indoor_pm25, outdoor_pm25):
    """Calculate filter efficiency percentage"""
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        return max(0, min(100, efficiency))  # Clamp between 0-100%
    return 0

def days_since_install():
    """Calculate days since last filter change"""
    # Using MERV 13 upgrade date as last change
    install_date = datetime.strptime(FILTER_UPGRADE_DATE, "%Y-%m-%d")
    return (datetime.now() - install_date).days

def send_to_google_sheets(data):
    """Send data to Google Sheets via Forms"""
    form_data = {}
    for key, field_id in FORM_FIELD_MAPPING.items():
        if key in data:
            form_data[field_id] = data[key]
    
    response = requests.post(GOOGLE_FORM_URL, data=form_data)
    return response.status_code == 200

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
    indoor_pm25 = indoor_data.get('pm25', 0)
    outdoor_pm25 = outdoor_data.get('pm02', 0)  # AirGradient uses 'pm02' for PM2.5
    
    # Calculate efficiency
    efficiency = calculate_filter_efficiency(indoor_pm25, outdoor_pm25)
    
    # Prepare data for logging
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'indoor_pm25': indoor_pm25,
        'outdoor_pm25': outdoor_pm25,
        'filter_efficiency': efficiency,
        'indoor_co2': indoor_data.get('co2', 0),
        'indoor_voc': indoor_data.get('voc', 0),
        'days_since_install': days_since_install()
    }
    
    # Log locally
    print(f"Indoor PM2.5: {indoor_pm25} μg/m³")
    print(f"Outdoor PM2.5: {outdoor_pm25} μg/m³")
    print(f"Filter Efficiency: {efficiency:.1f}%")
    print(f"Days Since Install: {log_data['days_since_install']}")
    
    # Check if replacement needed (efficiency < 85% is concerning)
    if efficiency < 85 and outdoor_pm25 > 10:
        print("⚠️  WARNING: Filter efficiency is low! Consider replacement soon.")
    
    # Send to Google Sheets
    if send_to_google_sheets(log_data):
        print("✓ Data sent to Google Sheets")
    else:
        print("✗ Failed to send to Google Sheets")
    
    # Save locally as backup
    with open('/tmp/air_quality_latest.json', 'w') as f:
        json.dump(log_data, f)

if __name__ == "__main__":
    main()
