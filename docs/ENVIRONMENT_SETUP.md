# Environment Setup

## Local Development

### Prerequisites
- Python 3.12+
- uv package manager

### Setup
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Install dependencies
uv sync --dev
```

## Environment Variables (.env)

```bash
# Airthings API credentials
AIRTHINGS_CLIENT_ID=your_client_id
AIRTHINGS_CLIENT_SECRET=your_client_secret
AIRTHINGS_DEVICE_SERIAL=your_serial_here

# AirGradient serials
AIRGRADIENT_SERIAL=your_outdoor_serial      # Outdoor
AIRGRADIENT_INDOOR_SERIAL=your_indoor_serial # Second bedroom

# Google Sheets
GOOGLE_SPREADSHEET_ID=your_sheet_id
```

## Google Service Account Setup

1. Create service account in Google Cloud Console
2. Download JSON credentials as `google-credentials.json`
3. Share Google Sheet with service account email
4. Grant Editor permissions

## Unifi Gateway Setup

### SSH Access
```bash
ssh root@192.168.X.X
```

### Install Dependencies
```bash
apt update
apt install python3-pip
pip3 install requests google-api-python-client google-auth
```

### Deploy Files
```bash
# From local machine
scp collect_multi_fixed.py root@192.168.X.X:/data/scripts/
scp collect_with_sheets_api.py root@192.168.X.X:/data/scripts/
scp google-credentials.json root@192.168.X.X:/data/scripts/
scp .env root@192.168.X.X:/data/scripts/
```

### Configure Cron
```bash
# On Unifi Gateway
crontab -e

# Add this line:
*/5 * * * * /usr/bin/python3 /data/scripts/collect_multi_fixed.py >> /data/logs/air_quality.log 2>&1
```

### Verify
```bash
# Test manually
python3 /data/scripts/collect_multi_fixed.py

# Check logs
tail -f /data/logs/air_quality.log
```

## AirGradient Device Configuration

### Find Device IPs
```bash
# On local network
ping airgradient_XXXXXX.local
```

### Configure DHCP Reservations
In Unifi Console:
1. Network → Client Devices
2. Find AirGradient devices
3. Settings → Fixed IP
4. Assign static IPs

### Update collect_multi_fixed.py
```python
if 'airgradient_XXXXXX.local' in url:
    url = url.replace('airgradient_XXXXXX.local', 'YOUR_IP_HERE')
```

## Troubleshooting

### No data collection
- Check cron job: `crontab -l`
- Check logs: `/data/logs/air_quality.log`
- Test manually: `python3 /data/scripts/collect_multi_fixed.py`

### .local domains not resolving
- Use collect_multi_fixed.py with hardcoded IPs
- Configure DHCP reservations

### Firmware update removed cron
- Re-add cron job
- Consider backup script on different machine

### Permission denied on Google Sheets
- Share sheet with service account email
- Grant Editor permissions