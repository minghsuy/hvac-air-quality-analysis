# 🔄 Switch from Google Forms to Sheets API

## Why Switch to Sheets API?

### Current Problems with Forms:
- ❌ Can only submit one sensor at a time
- ❌ Fixed fields - can't add rooms dynamically
- ❌ No room identification in data
- ❌ Duplicate timestamp columns
- ❌ Can't handle multiple indoor sensors properly

### Benefits of Sheets API:
- ✅ One row per sensor with room labels
- ✅ Dynamic columns based on sensor availability
- ✅ Proper multi-room support
- ✅ Cleaner data structure
- ✅ Better for analysis and ML predictions
- ✅ Can update existing rows if needed

## 📋 Prerequisites

1. **Google Cloud Service Account** ✓ (You already have this!)
   - File: `google-credentials.json`
   - Already configured with Sheets API access

2. **Copy credentials to Ubiquiti:**
   ```bash
   scp google-credentials.json root@[gateway-ip]:/data/scripts/
   ```

3. **Install Google API library on Ubiquiti:**
   ```bash
   ssh root@[gateway-ip]
   pip3 install google-api-python-client google-auth
   ```

## 🚀 Step-by-Step Migration

### Step 1: Test Sheets API Locally

Test the new collector on your local machine first:
```bash
# Copy credentials to project root
cp google-credentials.json .

# Test the Sheets API collector
uv run python collect_with_sheets_api.py
```

You should see:
```
✓ Outdoor: PM2.5=X μg/m³
✓ Master bedroom: PM2.5=Y μg/m³, Efficiency=Z%
✓ Second bedroom: PM2.5=W μg/m³, Efficiency=V%
✅ Successfully sent 2/2 rows to Google Sheets
```

### Step 2: Create New Sheet Tab (Recommended)

1. Open your Google Sheet
2. Add a new tab called "Multi-Sensor Data"
3. The script will automatically add headers:
   - Timestamp, Sensor_ID, Room, Sensor_Type, Indoor_PM25, etc.

### Step 3: Deploy to Ubiquiti

```bash
# Copy the new collector
scp collect_with_sheets_api.py root@[gateway-ip]:/data/scripts/

# Copy credentials if not already there
scp google-credentials.json root@[gateway-ip]:/data/scripts/

# SSH to gateway
ssh root@[gateway-ip]

# Install dependencies (if needed)
pip3 install google-api-python-client google-auth

# Test it
cd /data/scripts
python3 collect_with_sheets_api.py
```

### Step 4: Update Cron Job

```bash
# Update cron to use the new Sheets API collector
crontab -e

# Change from:
*/5 * * * * /usr/bin/python3 /data/scripts/collect_air.py >> /data/logs/air_quality.log 2>&1

# To:
*/5 * * * * /usr/bin/python3 /data/scripts/collect_with_sheets_api.py >> /data/logs/air_quality.log 2>&1
```

### Step 5: Verify It's Working

1. **Check the logs:**
   ```bash
   tail -f /data/logs/air_quality.log
   ```

2. **Check Google Sheets:**
   - New rows should appear every 5 minutes
   - Each row shows which room/sensor
   - Both bedrooms tracked separately

3. **Monitor for 1 hour** to ensure stability

## 📊 New Data Structure

### Old (Forms):
```
Timestamp | Indoor PM2.5 | Outdoor PM2.5 | Efficiency | ...
```
Single row, no room identification

### New (Sheets API):
```
Timestamp | Sensor_ID | Room | Sensor_Type | Indoor_PM25 | Outdoor_PM25 | Efficiency | ...
2025-08-30 18:00:00 | airthings_129430 | master_bedroom | airthings | 1.0 | 6.5 | 84.6 | ...
2025-08-30 18:00:00 | airgradient_cf228 | second_bedroom | airgradient | 0.5 | 6.5 | 92.3 | ...
```
Multiple rows per timestamp, clear room identification

## 🔧 Troubleshooting

### "Failed to connect to Google Sheets API"
- Check `google-credentials.json` exists at `/data/scripts/`
- Verify service account has access to your sheet
- Share sheet with service account email (found in credentials file)

### "No module named 'google'"
```bash
pip3 install google-api-python-client google-auth
```

### "Permission denied"
- Share your Google Sheet with the service account email:
  - Find email in `google-credentials.json` (client_email field)
  - Share sheet with that email as "Editor"

### Want to keep Forms as backup?
The script can fall back to Forms if Sheets API fails. Just keep your Forms configuration in `.env`.

## 📈 Analysis Benefits

With the new structure, you can:

1. **Compare rooms directly:**
   ```sql
   SELECT Room, AVG(Indoor_PM25) as Avg_PM25
   FROM data
   GROUP BY Room
   ```

2. **Track sensor-specific trends:**
   ```sql
   SELECT Sensor_ID, MIN(Filter_Efficiency), MAX(Filter_Efficiency)
   FROM data
   WHERE Timestamp > DATE_SUB(NOW(), INTERVAL 7 DAY)
   GROUP BY Sensor_ID
   ```

3. **Use Google Sheets formulas:**
   ```
   =QUERY(A:R, "SELECT B, AVG(E) WHERE C = 'master_bedroom' GROUP BY B")
   ```

4. **ML predictions per room:**
   ```
   =FORECAST(TODAY()+30, 
     FILTER(G:G, C:C="master_bedroom"), 
     FILTER(A:A, C:C="master_bedroom"))
   ```

## ✅ Success Checklist

- [ ] Tested locally with `collect_with_sheets_api.py`
- [ ] Copied `google-credentials.json` to Ubiquiti
- [ ] Installed Google API libraries on Ubiquiti
- [ ] Updated cron job to use new script
- [ ] Verified data flowing to new sheet structure
- [ ] Both rooms showing separate data
- [ ] Monitoring working for 1+ hours

## 🎯 Next Steps

Once running with Sheets API:

1. **Update Apps Script** to work with new structure
2. **Create room-specific dashboards** in Google Sheets
3. **Set up per-room alerts** (e.g., "Second bedroom efficiency < 80%")
4. **Build ML models** for each room's filter performance

---

**Note**: Keep the old Forms collector as backup (`collect_air.py`). You can always switch back if needed by updating the cron job.