# System Architecture

## Data Collection Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Airthings API  │────▶│  Unifi Gateway  │────▶│  Google Sheets  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               ▲
┌─────────────────┐            │
│ AirGradient     │────────────┘
│ (Local mDNS)    │
└─────────────────┘
```

## Components

### Sensors

1. **Airthings View Plus** (Master Bedroom)
   - OAuth2 API authentication
   - Measures: PM2.5, CO2, VOC, radon, temp, humidity
   - Serial: [configured in .env]

2. **AirGradient Open Air** (Outdoor)
   - Local mDNS API (no auth)
   - URL: `http://airgradient_XXXXXX.local/measures/current`
   - Measures: PM2.5, CO2, VOC, NOX, temp, humidity

3. **AirGradient ONE** (Second Bedroom)
   - Local mDNS API (no auth)
   - URL: `http://airgradient_XXXXXX.local/measures/current`
   - Measures: PM2.5, CO2, VOC, NOX, temp, humidity

### Data Collection Scripts

- **`collect_with_sheets_api.py`**: Main multi-sensor collector using Sheets API
- **`collect_multi_fixed.py`**: Wrapper for Unifi (hardcoded IPs)
- **`collect_air_quality.py`**: Legacy single-sensor with Forms API

### Unifi Gateway Deployment

```bash
# Cron job (runs every 5 minutes)
*/5 * * * * /usr/bin/python3 /data/scripts/collect_multi_fixed.py >> /data/logs/air_quality.log 2>&1
```

**Limitations:**
- No mDNS resolution (.local doesn't work)
- Firmware updates wipe customizations
- Limited Python packages available

### Google Sheets Structure

| Column | Description |
|--------|-------------|
| Timestamp | Collection time |
| Sensor_ID | Unique identifier |
| Room | Location name |
| Sensor_Type | airthings/airgradient |
| Indoor_PM25 | Indoor PM2.5 reading |
| Outdoor_PM25 | Outdoor PM2.5 reading |
| Filter_Efficiency | Calculated efficiency |
| Indoor_CO2 | CO2 levels |
| Indoor_VOC | VOC index |
| Indoor_NOX | NOX index |
| Indoor_Temp | Temperature |
| Indoor_Humidity | Humidity % |
| Indoor_Radon | Radon (Airthings only) |
| Outdoor_* | Outdoor equivalents |

### API Authentication

- **Airthings**: OAuth2 client credentials in `.env`
- **AirGradient**: No auth (local network only)
- **Google Sheets**: Service account JSON credentials

## Network Configuration

### mDNS Resolution Issues

On Unifi Gateway, .local domains don't resolve. Solution:

```python
# collect_multi_fixed.py monkey-patches requests
if 'airgradient_XXXXXX.local' in url:
    url = url.replace('airgradient_XXXXXX.local', '192.168.X.XX')
```

### DHCP Reservations Recommended

Configure static DHCP leases for AirGradient devices to maintain fixed IPs.

## Data Analysis

- **Real-time**: Google Sheets formulas
- **Historical**: Python scripts in `scripts/analysis/`
- **Visualization**: Plotly charts exported to PNG
- **ML Predictions**: Planned for Google Apps Script