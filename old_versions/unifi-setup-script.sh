#!/bin/bash
# Setup script for Unifi Cloud Gateway Ultra
# Run this after SSHing into your gateway

echo "Setting up air quality monitoring on Unifi Gateway..."

# Create directories
mkdir -p /data/scripts
mkdir -p /data/logs

# Install Python packages (minimal for embedded system)
echo "Installing Python packages..."
pip3 install requests

# Create environment file
cat > /data/scripts/.env << 'EOF'
# Airthings API Credentials
AIRTHINGS_CLIENT_ID=your_client_id
AIRTHINGS_CLIENT_SECRET=your_secret
AIRTHINGS_DEVICE_SERIAL=your_serial

# AirGradient Configuration
# Find your AirGradient serial in the device or via mDNS
AIRGRADIENT_SERIAL=your_airgradient_serial

# Google Form Configuration  
GOOGLE_FORM_ID=your_form_id
# Get these entry IDs from inspecting your Google Form
FORM_TIMESTAMP=entry.123456
FORM_INDOOR_PM25=entry.234567
FORM_OUTDOOR_PM25=entry.345678
FORM_EFFICIENCY=entry.456789
FORM_INDOOR_CO2=entry.567890
FORM_INDOOR_VOC=entry.678901
FORM_DAYS_SINCE=entry.789012
EOF

# Create simplified collector script
cat > /data/scripts/collect_air.py << 'EOF'
#!/usr/bin/env python3
import os
import json
import requests
from datetime import datetime

# Load config
with open('/data/scripts/.env', 'r') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

# Configuration
AIRTHINGS_CLIENT_ID = os.environ.get('AIRTHINGS_CLIENT_ID')
AIRTHINGS_CLIENT_SECRET = os.environ.get('AIRTHINGS_CLIENT_SECRET')
AIRTHINGS_DEVICE_SERIAL = os.environ.get('AIRTHINGS_DEVICE_SERIAL')
AIRGRADIENT_SERIAL = os.environ.get('AIRGRADIENT_SERIAL')
GOOGLE_FORM_ID = os.environ.get('GOOGLE_FORM_ID')

# Filter install date (update this!)
LAST_FILTER_CHANGE = "2025-06-01"

def get_airthings_token():
    """Get Airthings token"""
    response = requests.post(
        "https://accounts-api.airthings.com/v1/token",
        json={
            "grant_type": "client_credentials",
            "client_id": AIRTHINGS_CLIENT_ID,
            "client_secret": AIRTHINGS_CLIENT_SECRET,
            "scope": ["read:device:current_values"]
        }
    )
    return response.json()['access_token']

def get_indoor_data():
    """Get indoor air quality from Airthings"""
    token = get_airthings_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get accounts
    accounts = requests.get(
        "https://consumer-api.airthings.com/v1/accounts",
        headers=headers
    ).json()
    
    account_id = accounts['accounts'][0]['id']
    
    # Get sensor data
    params = {'sn': [AIRTHINGS_DEVICE_SERIAL]} if AIRTHINGS_DEVICE_SERIAL else {}
    response = requests.get(
        f"https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors",
        headers=headers,
        params=params
    )
    
    sensors = response.json()
    if sensors['results']:
        result = sensors['results'][0]
        data = {}
        for sensor in result['sensors']:
            data[sensor['sensorType']] = sensor['value']
        return data
    return {}

def get_outdoor_data():
    """Get outdoor air quality from AirGradient"""
    try:
        url = f"http://airgradient_{AIRGRADIENT_SERIAL}.local/measures/current"
        response = requests.get(url, timeout=5)
        return response.json()
    except:
        return {}

def main():
    """Collect and log data"""
    timestamp = datetime.now()
    
    # Get data
    indoor = get_indoor_data()
    outdoor = get_outdoor_data()
    
    # Calculate metrics
    indoor_pm25 = indoor.get('pm25', 0)
    outdoor_pm25 = outdoor.get('pm02', 0)
    
    if outdoor_pm25 > 0:
        efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
        efficiency = max(0, min(100, efficiency))
    else:
        efficiency = 0
    
    # Days since filter change
    install_date = datetime.strptime(LAST_FILTER_CHANGE, "%Y-%m-%d")
    days_since = (timestamp - install_date).days
    
    # Log data
    log_entry = {
        'timestamp': timestamp.isoformat(),
        'indoor_pm25': indoor_pm25,
        'outdoor_pm25': outdoor_pm25,
        'efficiency': round(efficiency, 1),
        'indoor_co2': indoor.get('co2', 0),
        'indoor_voc': indoor.get('voc', 0),
        'days_since_install': days_since
    }
    
    # Save to log file
    with open('/data/logs/air_quality.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    # Send to Google Sheets
    if GOOGLE_FORM_ID:
        form_url = f"https://docs.google.com/forms/d/e/{GOOGLE_FORM_ID}/formResponse"
        form_data = {
            os.environ.get('FORM_TIMESTAMP'): timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            os.environ.get('FORM_INDOOR_PM25'): indoor_pm25,
            os.environ.get('FORM_OUTDOOR_PM25'): outdoor_pm25,
            os.environ.get('FORM_EFFICIENCY'): efficiency,
            os.environ.get('FORM_INDOOR_CO2'): indoor.get('co2', 0),
            os.environ.get('FORM_INDOOR_VOC'): indoor.get('voc', 0),
            os.environ.get('FORM_DAYS_SINCE'): days_since
        }
        
        try:
            requests.post(form_url, data=form_data)
            print(f"✓ Data sent to Google Sheets at {timestamp}")
        except:
            print(f"✗ Failed to send to Google Sheets at {timestamp}")
    
    # Alert if efficiency is low
    if efficiency < 85 and outdoor_pm25 > 10:
        print(f"⚠️  ALERT: Filter efficiency at {efficiency:.1f}% - consider replacement!")
    
    print(f"Indoor: {indoor_pm25} μg/m³, Outdoor: {outdoor_pm25} μg/m³, Efficiency: {efficiency:.1f}%")

if __name__ == "__main__":
    main()
EOF

chmod +x /data/scripts/collect_air.py

# Create cron job
echo "Setting up hourly collection..."
(crontab -l 2>/dev/null; echo "0 * * * * /usr/bin/python3 /data/scripts/collect_air.py >> /data/logs/collection.log 2>&1") | crontab -

echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit /data/scripts/.env with your actual credentials"
echo "2. Find your AirGradient serial: avahi-browse -t _http._tcp"
echo "3. Test the script: python3 /data/scripts/collect_air.py"
echo "4. Check logs: tail -f /data/logs/collection.log"
