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

3. **For Unifi Gateway**
   ```bash
   # .local domains don't resolve on Unifi
   # Always use the wrapper script
   ./scripts/run_collector.sh
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

### 🔴 Cron Job Not Running on Unifi

#### Symptom
Manual execution works but automated collection doesn't happen.

#### Solutions

1. **Check Crontab**
   ```bash
   crontab -l
   # Should show:
   # */5 * * * * /data/scripts/run_collector.sh >> /data/logs/cron.log 2>&1
   ```

2. **Add Missing Cron Entry**
   ```bash
   crontab -e
   # Add these lines:
   PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
   */5 * * * * /data/scripts/run_collector.sh >> /data/logs/cron.log 2>&1
   ```

3. **Check Cron Service**
   ```bash
   ps aux | grep cron
   # If not running:
   /etc/init.d/cron start
   ```

4. **Setup Persistence After Updates**
   ```bash
   # Run the persistence setup script
   /data/scripts/SETUP_AFTER_FIRMWARE_UPDATE.sh
   
   # This ensures cron jobs survive reboots
   ```

### 🔴 Google Apps Script Not Sending Alerts

#### Symptom
Data is being collected but no email alerts are received.

#### Solutions

1. **Check Script Properties**
   - Open Google Sheets
   - Extensions → Apps Script
   - Project Settings → Script Properties
   - Ensure `EMAIL_RECIPIENT` is set correctly

2. **Review Execution Logs**
   - In Apps Script editor
   - View → Executions
   - Check for errors in recent runs

3. **Test Alert Function**
   ```javascript
   // In Apps Script editor, run this test
   function testAlert() {
     analyzeEfficiency();
   }
   ```

4. **Verify Confidence Thresholds**
   - v0.4.0 uses smart alerting
   - Alerts suppressed during activity hours (5-11 PM) for low confidence
   - Check outdoor PM2.5 is >10 for high confidence alerts

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

1. **Local Development**
   ```bash
   # Use uv to install dependencies
   uv sync --dev
   ```

2. **On Unifi Gateway**
   ```bash
   # Unifi uses pip3
   pip3 install python-dotenv requests
   # or use apt:
   apt-get install -y python3-requests
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
The v0.4.0 smart alerting system should handle this:
- Uses median instead of average
- Suppresses low-confidence alerts during activity hours (5-11 PM)
- Requires high outdoor PM2.5 for confident readings

Update to latest Apps Script code if still experiencing issues.

## Diagnostic Commands

### Check System Status
```bash
# On Unifi Gateway
cd /data/scripts
./check_status.sh

# View recent logs
tail -100 /data/logs/air_quality.log

# Check last collection
tail -1 /data/logs/air_quality_data.jsonl | jq .
```

### Test Individual Components
```bash
# Test Airthings only
python -c "from collect_with_sheets_api_v2 import get_airthings_data; print(get_airthings_data())"

# Test AirGradient outdoor
curl -s http://192.168.X.XX/measures/current | jq .

# Test Google Sheets write
python collect_with_sheets_api_v2.py --dry-run
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
# Clear logs and restart
rm /data/logs/air_quality.log
rm /data/logs/air_quality_data.jsonl
./run_collector.sh

# Rebuild from scratch
rm -rf .venv
uv venv --python 3.12
uv sync --dev
```

## Log Files Location

| Log File | Purpose | Location |
|----------|---------|----------|
| Application Log | Main collector output | `/data/logs/air_quality.log` |
| Data Log | JSON records of all readings | `/data/logs/air_quality_data.jsonl` |
| Cron Log | Cron execution history | `/data/logs/cron.log` |
| Collection Log | Legacy collection output | `/data/logs/collection.log` |

## Getting Help

1. **Check Logs First**
   ```bash
   # Most recent errors
   grep ERROR /data/logs/air_quality.log | tail -20
   
   # Check data format
   tail -1 /data/logs/air_quality_data.jsonl | python -m json.tool
   ```

2. **Enable Debug Mode**
   ```python
   # Add to your .env
   DEBUG=true
   ```

3. **Report Issues**
   - [GitHub Issues](https://github.com/minghsuy/hvac-air-quality-analysis/issues)
   - Include error messages and logs
   - Mention your setup (sensors, Unifi model, etc.)

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
   - Monitor Unifi Gateway storage space

## Working Example Output

A successful collection run should look like:

```bash
root@Cloud-Gateway-Ultra:/data/scripts# python3 collect_with_sheets_api_v2.py
2025-09-01 10:00:00 - Starting collection...
2025-09-01 10:00:01 - Airthings data: PM2.5=0.0, CO2=427, Temp=20.6°C
2025-09-01 10:00:02 - AirGradient outdoor: PM2.5=8.73, CO2=420, Temp=25.2°C
2025-09-01 10:00:02 - AirGradient indoor: PM2.5=1.2, CO2=445, Temp=21.3°C
2025-09-01 10:00:03 - Filter efficiency: Master=100.0%, Second=86.2%
2025-09-01 10:00:04 - Data written to Google Sheets (2 rows)
2025-09-01 10:00:04 - Collection complete
```

If you see this, everything is working correctly!