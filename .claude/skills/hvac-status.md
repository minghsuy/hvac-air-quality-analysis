# HVAC Air Quality System Status Check

Check the health and status of both air quality monitoring systems (Unifi Cloud Gateway and Spark DGX).

## What this skill does

1. **Unifi Cloud Gateway ($GATEWAY_IP or 192.168.X.1)**
   - Check if cron job exists and is running
   - Show last collection timestamp from logs
   - Verify data is being written to Google Sheets

2. **Spark DGX ($DGX_IP or 192.168.X.XXX)**
   - Check systemd timer status
   - Show last collection timestamp
   - Show next scheduled collection time
   - Verify data collection is working

3. **Data Validation**
   - Compare timestamps from both systems
   - Check for data gaps (collections should be ~5 minutes apart)
   - Alert if either system hasn't collected in >10 minutes

4. **Sensor Status**
   - Show latest sensor readings from both systems
   - Compare indoor/outdoor PM2.5 levels
   - Show filter efficiency calculations

## Commands to run

```bash
# Check Unifi Gateway (set GATEWAY_IP in environment)
ssh root@${GATEWAY_IP:-192.168.X.1} "crontab -l | grep collect && tail -30 /data/logs/air_quality.log"

# Check Spark DGX (set DGX_IP and DGX_USER in environment)
ssh ${DGX_USER:-user}@${DGX_IP:-192.168.X.XXX} "systemctl --user status air-quality-collector.timer && systemctl --user list-timers air-quality-collector.timer && tail -30 ~/hvac-air-quality-analysis/logs/air_quality.log"
```

## Expected output

Provide a summary showing:
- ✅/❌ Status of each system
- ⏰ Last collection time for each
- 📊 Latest sensor readings
- ⚠️ Any alerts or issues detected
- 📈 Trend: Both systems collecting normally / Issues detected

## Success criteria

- Both systems should show collections within last 10 minutes
- No error messages in logs
- Data being written to Google Sheets successfully
- Sensor readings are reasonable (PM2.5 < 100, CO2 < 5000, etc.)
