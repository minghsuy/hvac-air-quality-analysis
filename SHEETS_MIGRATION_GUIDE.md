# Google Sheets Migration Guide

## Current Situation
- **Old data (rows 2-3630)**: Google Forms submissions with 14 columns (stopped Aug 8, 2025)
- **New data (rows 3631+)**: Sheets API with 18 columns (started Aug 30, 2025)
- **Problem**: Mixed schemas in same sheet causing Apps Script to fail

## Step-by-Step Fix

### Step 1: Backup Your Data ✅ COMPLETED
```bash
# Already done - backup saved to:
data/backup_sheets_20250831_101046.json
data/cleaned_data_20250831_101046.csv
```

### Step 2: Choose Your Migration Path

#### Option A: Create New Clean Sheet Tab (RECOMMENDED)
1. Run the fixer script again:
   ```bash
   uv run python fix_sheets_schema.py
   ```
2. Choose option 1 to create a new tab with cleaned data
3. This keeps your original data safe

#### Option B: Use the CSV File
1. Open Google Sheets
2. File → Import → Upload `data/cleaned_data_20250831_101046.csv`
3. Create as new sheet or new tab

### Step 3: Update Apps Script

1. **Open your Google Sheet**
2. **Extensions → Apps Script**
3. **Delete all existing code**
4. **Copy and paste the code from `apps_script_code.gs`**
5. **Save (Ctrl+S or Cmd+S)**

### Step 4: Configure Apps Script

1. In Apps Script editor, click **Project Settings** (gear icon)
2. Scroll down to **Script Properties**
3. Add property:
   - Property: `ALERT_EMAIL`
   - Value: `your-email@example.com`

### Step 5: Set Up Triggers

1. In Apps Script editor, run the `setupTriggers()` function once:
   - Select `setupTriggers` from dropdown
   - Click ▶️ Run
   - Authorize when prompted

This sets up:
- Hourly filter efficiency checks
- Daily summary at 8 AM

### Step 6: Test Everything

1. In Apps Script, run the `test()` function
2. Check the Execution Log for results
3. Verify you see data for all sensors

### Step 7: Update Data Collection

The current collector (`collect_with_sheets_api.py`) is already using the correct schema.
Just ensure it's running on your Unifi Gateway:

```bash
# On Unifi Gateway
crontab -l | grep collect
# Should see: */5 * * * * /data/scripts/collect_with_sheets_api.py
```

## New Data Schema (18 columns)

| Column | Field | Description | Example |
|--------|-------|-------------|---------|
| A | Timestamp | ISO format datetime | 2025-08-30 18:29:06 |
| B | Sensor_ID | Unique sensor identifier | airthings_129430 |
| C | Room | Location name | master_bedroom |
| D | Sensor_Type | Sensor brand/type | airthings |
| E | Indoor_PM25 | Indoor PM2.5 (μg/m³) | 2 |
| F | Outdoor_PM25 | Outdoor PM2.5 (μg/m³) | 5 |
| G | Filter_Efficiency | Calculated efficiency (%) | 60.0 |
| H | Indoor_CO2 | Indoor CO2 (ppm) | 450 |
| I | Indoor_VOC | Indoor VOC (ppb) | 75 |
| J | Indoor_NOX | Indoor NOX | 0 |
| K | Indoor_Temp | Indoor temperature (°C) | 22.5 |
| L | Indoor_Humidity | Indoor humidity (%) | 45 |
| M | Indoor_Radon | Indoor radon (Bq/m³) | 15 |
| N | Outdoor_CO2 | Outdoor CO2 (ppm) | 420 |
| O | Outdoor_Temp | Outdoor temperature (°C) | 25.0 |
| P | Outdoor_Humidity | Outdoor humidity (%) | 60 |
| Q | Outdoor_VOC | Outdoor VOC (ppb) | 100 |
| R | Outdoor_NOX | Outdoor NOX | 1 |

## Apps Script Functions

### Available Functions
- `getLatestReadings()` - Get latest reading for each sensor
- `getFilterStats()` - Calculate 24-hour statistics
- `checkFilterAlert()` - Check if efficiency below threshold
- `createDailySummary()` - Generate daily summary
- `test()` - Test all functions

### Alert Thresholds
- **Warning**: Efficiency < 85%
- **Critical**: Efficiency < 80%

## Troubleshooting

### If Apps Script shows errors:
1. Check that you're using the cleaned data (18 columns)
2. Verify headers match exactly
3. Check Execution Log for details

### If data collection stops:
1. SSH to Unifi Gateway
2. Check logs: `tail -100 /data/logs/air_quality.log`
3. Test manually: `python3 /data/scripts/collect_with_sheets_api.py`

### If you see authentication errors:
1. Verify `google-credentials.json` exists
2. Check service account has Editor access to sheet
3. Re-run `setup_google_sheets_api.py` if needed

## Next Steps

1. ✅ Clean and migrate data
2. ✅ Update Apps Script
3. ⏳ Monitor for 24 hours
4. ⏳ Verify alerts working
5. ⏳ Check daily summaries

## Support Files

- `fix_sheets_schema.py` - Fixes mixed schema issues
- `apps_script_code.gs` - Updated Apps Script code
- `analyze_sheets_mess.py` - Analyzes current data state
- `collect_with_sheets_api.py` - Current data collector (already correct)

## Important Notes

- Old Google Forms method is deprecated - don't use it
- All new data uses Sheets API with 18-column schema
- Keep backups before making any changes
- Test in a new sheet tab first before replacing main data