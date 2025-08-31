# 📅 Next Phase: Google Apps Script Automation (August 31, 2025)

## Current Status
- ✅ Multi-sensor data collection working (every 5 minutes)
- ✅ Both bedrooms tracked separately in Google Sheets
- ✅ 24 hours of data will be available by tomorrow
- ✅ New filter showing excellent performance

## Tomorrow's Goals: Apps Script Automation

### 1. Deploy the Apps Script (Morning)
The script is ready in `apps_script.gs`. You need to:

1. **Open your Google Sheet**
2. **Extensions → Apps Script**
3. **Copy the entire `apps_script.gs` content**
4. **Update configuration**:
   ```javascript
   const EMAIL_ADDRESS = 'your-email@gmail.com';  // Your actual email
   const SHEET_NAME = 'Sheet1';  // Your data sheet name
   ```
5. **Run `setupTriggers()`** once to enable:
   - Data gap alerts (every 30 minutes)
   - Daily summary (9 AM)
   - Low efficiency alerts

### 2. Verify Monitoring Works
After setup, test:
- Run `testAlerts()` to verify email works
- Check for daily summary tomorrow at 9 AM
- Monitor for any data gaps

### 3. Analyze First Day's Data
With 24 hours of multi-sensor data:
- Compare room efficiencies
- Check if second bedroom always shows 100%
- Identify any sensor issues
- Calculate daily averages per room

### 4. Set Up ML Predictions
In Google Sheets, add formulas:
```
=FORECAST(TODAY()+30, 
  FILTER(G:G, C:C="master_bedroom"), 
  FILTER(A:A, C:C="master_bedroom"))
```

### 5. Create Dashboard Tab
Design a summary sheet with:
- Current readings per room
- 24-hour averages
- Efficiency trends
- Days until predicted replacement
- Cost tracking

## Data to Analyze Tomorrow

### Key Questions:
1. **Room Comparison**: Why is second bedroom always 0 PM2.5?
   - Sensor issue?
   - Better sealed room?
   - Less activity?

2. **Efficiency Patterns**:
   - Does efficiency vary by time of day?
   - Impact of outdoor PM2.5 levels?
   - Correlation with HVAC cycling?

3. **Filter Performance**:
   - How does new filter (Aug 29) compare to old?
   - Projected lifespan based on degradation rate?
   - Cost per day calculation?

## Files You'll Need

### On Your Mac:
- `apps_script.gs` - Apps Script code
- `analyze_historical.py` - For deeper analysis
- Your Google Sheet URL

### On Ubiquiti (already running):
- `collect_multi_fixed.py` - Running every 5 minutes
- Logs at `/data/logs/air_quality.log`

## Success Metrics for Tomorrow

✅ **Automation Working**:
- [ ] Daily summary email received
- [ ] No data gap alerts (collection stable)
- [ ] Both rooms showing in data

✅ **Analysis Complete**:
- [ ] 24-hour averages calculated
- [ ] Room comparison documented
- [ ] Filter lifespan projection created

✅ **Dashboard Created**:
- [ ] Real-time status view
- [ ] Historical trends
- [ ] Predictive metrics

## Troubleshooting Reminders

### If No Data Appears:
```bash
ssh root@192.168.X.X
tail -f /data/logs/air_quality.log
```

### If Apps Script Fails:
- Check View → Executions in Apps Script
- Verify email address is correct
- Make sure sheet name matches

### If Predictions Don't Work:
- Need at least 7 days of data for reliable FORECAST
- Check data has no gaps
- Ensure timestamp format is consistent

## Long-term Vision

Once this phase is complete, you'll have:
1. **Fully automated monitoring** with alerts
2. **Per-room air quality tracking**
3. **Predictive filter replacement**
4. **Cost optimization data**
5. **Health correlation capability**

This positions you to:
- Never miss a filter replacement
- Optimize for cost vs health
- Share learnings with others
- Build on the platform for more sensors

---

**Remember**: The system is now collecting data 24/7. Focus tomorrow on making it smart with automation and analysis!