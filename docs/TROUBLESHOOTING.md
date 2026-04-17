# Troubleshooting Guide

## Common Issues and Solutions

### 🔴 Data Not Appearing in Google Sheets

#### Symptom
Collector runs without errors but no new rows appear in Google Sheets.

#### Solutions

1. **Check Sheet Tab Name**
   ```bash
   # Verify GOOGLE_SHEET_TAB matches your actual sheet
   grep GOOGLE_SHEET_TAB .env
   # Should be: Cleaned_Data_20250831 or your specific tab
   ```

2. **Verify Service Account Permissions**
   - Open Google Sheets
   - Click Share button
   - Ensure service account email has Editor access
   - Service account email format: `name@project-id.iam.gserviceaccount.com`

3. **Test Sheets API Connection**
   ```python
   python -c "
   from google.oauth2 import service_account
   from googleapiclient.discovery import build
   creds = service_account.Credentials.from_service_account_file('google-credentials.json')
   service = build('sheets', 'v4', credentials=creds)
   print('Connection successful!')
   "
   ```

### 🔴 AirGradient Sensors Unreachable

#### Symptom
```
Error: HTTPConnectionPool(host='airgradient_XXXXX.local', port=80): Max retries exceeded
```

#### Solutions

1. **Use IP Discovery Script (Recommended)**
   ```bash
   # Run the IP discovery script
   python scripts/update_airgradient_ips.py
   
   # This will update sensors.json with current IPs
   cat sensors.json | jq .
   ```

2. **Manual IP Configuration**
   ```bash
   # Find sensor IPs using arp
   arp -a | grep -i airgradient
   # or by MAC prefix
   arp -a | grep -i 'd8:3b:da'
   
   # Update sensors.json with the IPs
   vi sensors.json
   ```

### 🔴 Airthings API Returns Empty Data

#### Symptom
```
No sensors found in Airthings response
```

#### Solutions

1. **Check API Response Structure**
   ```python
   # The API changed from 'sensors' to 'results'
   # Make sure you're using the updated collector
   grep "results" collect_with_sheets_api_v2.py
   ```

2. **Verify Credentials**
   ```bash
   # Test Airthings connection
   python -c "
   import os, requests
   from dotenv import load_dotenv
   load_dotenv()
   response = requests.post(
       'https://accounts-api.airthings.com/v1/token',
       json={
           'grant_type': 'client_credentials',
           'client_id': os.getenv('AIRTHINGS_CLIENT_ID'),
           'client_secret': os.getenv('AIRTHINGS_CLIENT_SECRET'),
           'scope': ['read:device:current_values']
       }
   )
   print('Token obtained!' if 'access_token' in response.json() else 'Failed')
   "
   ```

### 🔴 Data Collection Stops After Reboot/Logout

#### Symptom
Manual execution works but collection stops after logging out or rebooting.

#### Solutions

1. **Enable Linger for Systemd User Services**
   ```bash
   # Check if linger is enabled
   loginctl show-user $USER | grep Linger

   # Enable linger (required for services to survive logout/reboot)
   loginctl enable-linger $USER
   ```

2. **Verify Timer is Running**
   ```bash
   systemctl --user status air-quality-collector.timer
   ```

3. **Check Journal Logs**
   ```bash
   journalctl --user -u air-quality-collector.timer --since "1 hour ago"
   ```

### 🔴 Google Apps Script Not Sending Alerts

#### Symptom
Data is being collected but no email alerts are received.

#### Solutions

1. **Check Script Properties**
   - Open Google Sheets
   - Extensions → Apps Script
   - Project Settings → Script Properties
   - Ensure `ALERT_EMAIL` and `ALERT_EMAIL_2` are set correctly

2. **Review Execution Logs**
   - In Apps Script editor
   - View → Executions
   - Check for errors in recent runs

3. **Test Alert Function**
   ```javascript
   // In Apps Script editor, run the built-in test function
   test();
   ```

4. **Verify Efficiency Thresholds**
   - HVACMonitor v3 uses efficiency-based alerting with seasonal calibration
   - Change filter alert at < 75% efficiency (or calibrated value)
   - Critical alert at < 65% efficiency (or calibrated value)
   - Only reliable when outdoor PM2.5 exceeds seasonal minimum (winter: 10, summer: 5)

### 🔴 Schema Mismatch Errors

#### Symptom
```
Error: Row has 14 values but sheet expects 18
```

#### Solution
You're likely still using old Google Forms data format. The system now uses the 18-column schema:

1. **Migrate Existing Data**
   - v0.4.0 already migrated 3,985 rows
   - Check you're writing to correct tab: `Cleaned_Data_20250831`

2. **Use Updated Collector**
   ```bash
   # Ensure you're using v2
   python collect_with_sheets_api_v2.py
   ```

### 🔴 Missing Python Dependencies

#### Symptom
```
ModuleNotFoundError: No module named 'dotenv'
```

#### Solutions

```bash
# Use uv to install dependencies
uv sync --dev
```

### 🔴 Unit Conversion Confusion

#### Symptom
Radon shows as 9 in sheets but 0.24 in Airthings app.

#### Explanation
- API returns **Bq/m³** (native unit)
- App displays **pCi/L** (US unit)
- Conversion: `pCi/L = Bq/m³ ÷ 37`
- We store native units (Bq/m³) in sheets per DATA_DICTIONARY.md

### 🔴 Filter Efficiency Shows Negative Values

#### Symptom
Efficiency calculation shows -50% or other negative values.

#### Solutions

1. **Check PM2.5 Values**
   ```python
   # Efficiency formula:
   # ((outdoor - indoor) / outdoor) * 100
   # 
   # Negative means indoor > outdoor
   ```

2. **Verify Using Compensated Values**
   ```bash
   # Check you're using compensated PM2.5
   grep "pm02Compensated" collect_with_sheets_api_v2.py
   ```

3. **Verify Sensor Placement**
   - Outdoor sensor should be outside
   - Indoor sensor away from cooking/smoking areas
   - Allow 5-10 minutes after activities for readings to stabilize

### 🔴 High False Positive Alerts

#### Symptom
Getting alerts during cooking or cleaning activities.

#### Solution
HVACMonitor v3 handles this with multiple mechanisms:
- Uses **median** (not average) of efficiency readings — resists outliers
- **Indoor PM spike detection** identifies cooking/cleaning events (indoor exceeds outdoor by >= 5 ug/m3)
- Efficiency calculation **filters out** readings where indoor > outdoor
- Requires outdoor PM2.5 above **seasonal minimum** (winter: 10, summer: 5) for reliable readings

Update to latest `HVACMonitor_v3.gs` if still experiencing issues.

## Diagnostic Commands

### Check System Status
```bash
# Check systemd service status
systemctl --user status air-quality-collector.timer
systemctl --user status air-quality-collector.service

# Check recent journal logs
journalctl --user -u air-quality-collector.service --since "1 hour ago"
```

### Test Individual Components
```bash
# Test Airthings only
python -c "from collect_with_sheets_api_v2 import get_airthings_data; print(get_airthings_data())"

# Test AirGradient outdoor
curl -s http://192.168.X.XX/measures/current | jq .

# Test full collection (verbose output)
python collect_with_sheets_api_v2.py --test
```

### Finding Device IPs
```bash
# Find AirGradient devices by MAC prefix
arp -a | grep -i 'd8:3b:da'

# Check DHCP leases
cat /var/lib/dhcp/dhcpd.leases | grep -A5 -B5 airgradient

# Scan network (if nmap available)
nmap -sn 192.168.X.0/24 | grep -B2 -i "d8:3b:da"
```

### Reset and Restart
```bash
# Restart the systemd timer
systemctl --user restart air-quality-collector.timer

# Rebuild from scratch
rm -rf .venv
uv venv --python 3.12
uv sync --dev
```

## Log Files Location

The collector runs as a systemd user service. Logs are in the systemd journal:

```bash
# View recent collector logs
journalctl --user -u air-quality-collector.service --since "1 hour ago"

# View all errors
journalctl --user -u air-quality-collector.service --priority=err

# Follow logs in real time
journalctl --user -u air-quality-collector.service -f
```

## Getting Help

1. **Check Logs First**
   ```bash
   # Most recent errors
   journalctl --user -u air-quality-collector.service --since "1 hour ago" --no-pager
   ```

2. **Enable Debug Mode**
   ```python
   # Add to your .env
   DEBUG=true
   ```

3. **Report Issues**
   - [GitHub Issues](https://github.com/minghsuy/hvac-air-quality-analysis/issues)
   - Include error messages and logs
   - Mention your setup (sensors, system specs, etc.)

## Prevention Tips

1. **Regular Maintenance**
   - Check data collection weekly
   - Review logs monthly
   - Update credentials before expiry

2. **Backup Configuration**
   ```bash
   # Backup your working config
   cp .env .env.backup
   cp sensors.json sensors.json.backup
   cp google-credentials.json google-credentials.json.backup
   ```

3. **Monitor System Health**
   - Set up a separate alert if no data for 1 hour
   - Check Google Sheets for regular updates
   - Monitor disk space periodically

## Working Example Output

A successful collection run should look like:

```bash
$ python collect_with_sheets_api_v2.py
✓ Connected to Google Sheets API
✓ Outdoor: PM2.5=10 μg/m³
✓ Master bedroom: PM2.5=2 μg/m³, Efficiency=80%
✓ Second bedroom: PM2.5=1 μg/m³, Efficiency=90%
✓ Attic: Temp=22.3°C, Humidity=35%
✅ Successfully sent 3 rows to Cleaned_Data_20250831
```

If you see this, everything is working correctly!