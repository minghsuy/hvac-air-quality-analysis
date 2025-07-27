# Hardware Setup Guide

This guide covers the complete hardware setup for indoor and outdoor air quality monitoring.

## Indoor Monitoring: Airthings View Plus

### Device Specifications
- **Model**: Airthings View Plus
- **Measurements**: PM2.5, PM1, CO2, VOC, Temperature, Humidity, Radon, Pressure
- **Connectivity**: WiFi (2.4GHz only)
- **Power**: USB-C or batteries

### Placement Guidelines
1. **Height**: 3-6 feet from floor (breathing zone)
2. **Location**: Central living area, away from:
   - Direct airflow from vents
   - Kitchen (cooking interference)
   - Windows and doors
   - Direct sunlight
3. **Wall mounting**: Use included bracket for stable readings

### Initial Setup
1. Download Airthings app
2. Create account and add device
3. Connect to 2.4GHz WiFi network
4. Let sensor stabilize for 7 days (especially Radon)

### API Configuration
1. Log into [Airthings Dashboard](https://dashboard.airthings.com)
2. Navigate to API settings
3. Generate client credentials
4. Note your device serial number
5. Test API access:
```bash
curl -X POST https://accounts-api.airthings.com/v1/token \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### Known Limitations
- **PM2.5 Precision**: Rounds to whole numbers (0, 1, 2...)
- **Update Frequency**: 5-minute intervals
- **API Rate Limits**: 120 requests per hour

## Outdoor Monitoring: AirGradient ONE

### Why AirGradient?
- **Precision**: 0.01 μg/m³ resolution
- **Open Source**: Full control over data
- **Weatherproof**: Designed for outdoor use
- **Local API**: No cloud dependency

### Kit Contents
- AirGradient ONE board
- Plantower PMS5003 sensor
- SenseAir S8 CO2 sensor
- SHT40 temp/humidity sensor
- Weatherproof enclosure
- Power adapter

### Assembly Steps
1. Follow [official build guide](https://www.airgradient.com/outdoor/)
2. Flash firmware with outdoor configuration
3. Configure WiFi through web interface
4. Enable local API in settings

### Installation Location
1. **Height**: 6-10 feet above ground
2. **Clearance**: 3+ feet from walls/obstacles
3. **Protection**: Under eave or weathershield
4. **Orientation**: Inlet facing away from house
5. **Power**: Weatherproof outlet or extension

### Network Configuration
```json
{
  "wifi_ssid": "YourNetwork",
  "wifi_password": "YourPassword",
  "api_enabled": true,
  "api_port": 80,
  "mqtt_enabled": false,
  "send_to_cloud": false
}
```

## Integration: Unifi Gateway

### Why Use Unifi Gateway?
- Always-on data collection
- No dependency on personal computers
- Centralized logging
- Network isolation for IoT devices

### Prerequisites
- SSH access enabled
- Python 3.8+ installed
- Persistent storage path identified

### Setup Process
See [Data Collection](Data-Collection) guide for detailed steps

## Maintenance

### Monthly Tasks
- Clean sensor inlets with compressed air
- Check WiFi connectivity
- Verify data collection continuity

### Annual Tasks
- Calibrate CO2 sensors (outdoor fresh air)
- Replace Plantower sensor if degraded
- Update firmware for security patches

## Troubleshooting

### Airthings Issues
- **No data**: Check WiFi connection (2.4GHz only)
- **Erratic readings**: Ensure stable power supply
- **API errors**: Regenerate credentials

### AirGradient Issues
- **Network drops**: Set static IP reservation
- **Sensor errors**: Check cable connections
- **Wrong readings**: Verify outdoor placement

## Cost Breakdown
- Airthings View Plus: ~$300
- AirGradient ONE kit: ~$200
- Total investment: ~$500
- ROI: 6-12 months from optimized filter replacement

---
*Next: [Data Collection](Data-Collection) →*