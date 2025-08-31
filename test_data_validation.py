#!/usr/bin/env python3
"""
Test data validation against the data dictionary
Ensures all data is stored correctly according to specifications
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

# Configuration
SPREADSHEET_ID = os.environ.get("GOOGLE_SPREADSHEET_ID")
SHEET_TAB_NAME = os.environ.get("GOOGLE_SHEET_TAB", "Cleaned_Data_20250831")

def validate_data_collection():
    """Validate that data matches the data dictionary specifications"""
    
    print("="*60)
    print("DATA VALIDATION TEST")
    print("="*60)
    
    # 1. Collect data from all sensors
    print("\n1. COLLECTING SENSOR DATA...")
    
    # Get Airthings data
    airthings_data = get_airthings_raw()
    print("\n📱 Airthings API Response:")
    if airthings_data:
        result = airthings_data["results"][0]
        print(f"   Serial: {result['serialNumber']}")
        for sensor in result["sensors"]:
            print(f"   {sensor['sensorType']}: {sensor['value']} {sensor['unit']}")
    
    # Get AirGradient Outdoor
    print("\n🌡️ AirGradient Outdoor Response:")
    outdoor_serial = os.environ.get("AIRGRADIENT_SERIAL", "")
    outdoor_url = f'http://airgradient_{outdoor_serial}.local/measures/current' if outdoor_serial else 'http://airgradient_outdoor.local/measures/current'
    outdoor_response = requests.get(outdoor_url, timeout=5)
    outdoor_data = outdoor_response.json()
    print(f"   pm02: {outdoor_data.get('pm02')} (raw)")
    print(f"   pm02Compensated: {outdoor_data.get('pm02Compensated')} ← USING THIS")
    print(f"   atmp: {outdoor_data.get('atmp')}°C (raw)")
    print(f"   atmpCompensated: {outdoor_data.get('atmpCompensated')}°C ← USING THIS")
    print(f"   tvocIndex: {outdoor_data.get('tvocIndex')}")
    print(f"   noxIndex: {outdoor_data.get('noxIndex')}")
    
    # Get AirGradient Indoor
    print("\n🏠 AirGradient Indoor Response:")
    indoor_serial = os.environ.get("AIRGRADIENT_INDOOR_SERIAL", "")
    indoor_url = f'http://airgradient_{indoor_serial}.local/measures/current' if indoor_serial else 'http://airgradient_indoor.local/measures/current'
    indoor_response = requests.get(indoor_url, timeout=5)
    indoor_data = indoor_response.json()
    print(f"   pm02Compensated: {indoor_data.get('pm02Compensated')}")
    print(f"   tvocIndex: {indoor_data.get('tvocIndex')}")
    print(f"   noxIndex: {indoor_data.get('noxIndex')}")
    
    # 2. Build the row as it should be stored
    print("\n2. BUILDING DATA ROW...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Parse Airthings sensors
    airthings_values = {}
    if airthings_data:
        for sensor in airthings_data["results"][0]["sensors"]:
            airthings_values[sensor["sensorType"]] = sensor["value"]
    
    # Build master bedroom row
    master_row = [
        timestamp,                                          # A: Timestamp
        f"airthings_{result.get('serialNumber', 'XXXXXX')[-6:] if airthings_data else 'XXXXXX'}",  # B: Sensor_ID
        "master_bedroom",                                   # C: Room
        "airthings",                                       # D: Sensor_Type
        airthings_values.get("pm25", 0),                  # E: Indoor_PM25 (μg/m³)
        outdoor_data.get("pm02Compensated", 0),           # F: Outdoor_PM25 (μg/m³)
        calculate_efficiency(                              # G: Filter_Efficiency (%)
            airthings_values.get("pm25", 0),
            outdoor_data.get("pm02Compensated", 0)
        ),
        airthings_values.get("co2", 0),                   # H: Indoor_CO2 (ppm)
        airthings_values.get("voc", 0),                   # I: Indoor_VOC (ppb)
        "",                                                # J: Indoor_NOX (Airthings doesn't have)
        airthings_values.get("temp", 0),                  # K: Indoor_Temp (°C)
        airthings_values.get("humidity", 0),              # L: Indoor_Humidity (%)
        airthings_values.get("radonShortTermAvg", 0),     # M: Indoor_Radon (Bq/m³)
        outdoor_data.get("rco2", 0),                      # N: Outdoor_CO2 (ppm)
        outdoor_data.get("atmpCompensated", 0),           # O: Outdoor_Temp (°C)
        outdoor_data.get("rhumCompensated", 0),           # P: Outdoor_Humidity (%)
        outdoor_data.get("tvocIndex", 0),                 # Q: Outdoor_VOC (index)
        outdoor_data.get("noxIndex", 0),                  # R: Outdoor_NOX (index)
    ]
    
    # Display the row
    print("\n📊 Master Bedroom Row:")
    columns = ["Timestamp", "Sensor_ID", "Room", "Sensor_Type", "Indoor_PM25", 
               "Outdoor_PM25", "Filter_Efficiency", "Indoor_CO2", "Indoor_VOC", 
               "Indoor_NOX", "Indoor_Temp", "Indoor_Humidity", "Indoor_Radon",
               "Outdoor_CO2", "Outdoor_Temp", "Outdoor_Humidity", "Outdoor_VOC", "Outdoor_NOX"]
    
    for i, (col, val) in enumerate(zip(columns, master_row)):
        print(f"   {chr(65+i)}: {col:20} = {val}")
    
    # 3. Validate data types
    print("\n3. VALIDATING DATA TYPES...")
    validations = []
    
    # Check numeric fields
    numeric_fields = [4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17]  # E through R except J
    for idx in numeric_fields:
        if idx < len(master_row):
            val = master_row[idx]
            if val != "" and not isinstance(val, (int, float)):
                validations.append(f"   ❌ Column {chr(65+idx)} should be numeric, got {type(val)}")
            else:
                validations.append(f"   ✓ Column {chr(65+idx)} is correctly numeric/empty")
    
    # Check string fields
    string_fields = [0, 1, 2, 3]  # A through D
    for idx in string_fields:
        val = master_row[idx]
        if not isinstance(val, str):
            validations.append(f"   ❌ Column {chr(65+idx)} should be string, got {type(val)}")
        else:
            validations.append(f"   ✓ Column {chr(65+idx)} is correctly string")
    
    # Check empty fields for missing sensors
    if master_row[9] != "":  # Indoor_NOX should be empty for Airthings
        validations.append("   ❌ Indoor_NOX should be empty for Airthings")
    else:
        validations.append("   ✓ Indoor_NOX correctly empty for Airthings")
    
    for v in validations:
        print(v)
    
    # 4. Check key data points
    print("\n4. KEY DATA VALIDATION:")
    print(f"   Radon: {airthings_values.get('radonShortTermAvg', 0)} Bq/m³")
    print(f"          ({airthings_values.get('radonShortTermAvg', 0)/37:.2f} pCi/L in app)")
    print(f"   PM2.5: Using compensated value {outdoor_data.get('pm02Compensated')} not raw {outdoor_data.get('pm02')}")
    print(f"   VOC: Airthings={airthings_values.get('voc', 0)} ppb, AirGradient={outdoor_data.get('tvocIndex')} index")
    print(f"   Efficiency: {master_row[6]:.1f}% (should match Apps Script)")
    
    # 5. Test writing to sheet
    print("\n5. TEST WRITE TO GOOGLE SHEETS...")
    user_input = input("   Write test row to sheet? (y/n): ")
    
    if user_input.lower() == 'y':
        credentials = service_account.Credentials.from_service_account_file(
            "google-credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=credentials)
        
        body = {"values": [master_row]}
        range_name = f"{SHEET_TAB_NAME}!A:R"
        
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        
        if result.get("updates", {}).get("updatedRows", 0) > 0:
            print(f"   ✅ Test row written to {result.get('updates', {}).get('updatedRange', '')}")
        else:
            print("   ❌ Failed to write row")
    
    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)

def get_airthings_raw():
    """Get raw Airthings API response"""
    try:
        client_id = os.getenv('AIRTHINGS_CLIENT_ID')
        client_secret = os.getenv('AIRTHINGS_CLIENT_SECRET')
        
        # Get token
        response = requests.post(
            'https://accounts-api.airthings.com/v1/token',
            json={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': ['read:device:current_values'],
            },
            timeout=10,
        )
        token = response.json()['access_token']
        
        # Get sensor data
        headers = {'Authorization': f'Bearer {token}'}
        accounts = requests.get(
            'https://consumer-api.airthings.com/v1/accounts', 
            headers=headers, 
            timeout=10
        ).json()
        
        account_id = accounts['accounts'][0]['id']
        
        sensors = requests.get(
            f'https://consumer-api.airthings.com/v1/accounts/{account_id}/sensors',
            headers=headers,
            timeout=10,
        ).json()
        
        return sensors
    except Exception as e:
        print(f"Error getting Airthings data: {e}")
        return None

def calculate_efficiency(indoor, outdoor):
    """Calculate filter efficiency"""
    if outdoor <= 0:
        return 100.0 if indoor <= 0 else 0.0
    efficiency = ((outdoor - indoor) / outdoor) * 100
    return round(max(0, min(100, efficiency)), 2)

if __name__ == "__main__":
    validate_data_collection()