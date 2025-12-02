# 5-Minute Interval Data Collection

## Why 5 Minutes?

With 5-minute intervals, you can capture:
- **Cooking events**: See PM2.5 spikes when making breakfast/dinner
- **Shower humidity**: Track bathroom humidity and VOC changes
- **HVAC cycles**: Monitor filter efficiency during on/off cycles
- **Cleaning activities**: Detect vacuum-induced particle spikes
- **Dryer/washer**: Catch lint and humidity from laundry

## API Usage

- **Airthings limit**: 120 requests/hour
- **5-minute intervals**: 12 requests/hour (10% of limit)
- **Very safe margin** for manual checks and testing

## Data Volume

- **Per day**: 288 rows (12 × 24)
- **Per month**: ~8,640 rows
- **Per year**: ~105,120 rows

Google Sheets can handle up to 10 million cells, so even with 13 columns, you have room for years of data.

## Adjusting the Interval

If you want to change the frequency, modify the systemd timer:

```bash
# Edit the timer configuration
systemctl --user edit air-quality-collector.timer

# Common intervals:
# OnCalendar=*:0/5    # Every 5 minutes (default)
# OnCalendar=*:0/10   # Every 10 minutes
# OnCalendar=*:0/15   # Every 15 minutes
# OnCalendar=*:0/3    # Every 3 minutes (more detailed)

# Reload after changes
systemctl --user daemon-reload
```

## Monitoring Specific Events

During your first month, you might want to temporarily increase frequency during:
- Morning routines (showers, breakfast)
- Evening cooking
- Cleaning days
- High outdoor pollution events

This helps you understand your home's air quality patterns and how quickly your filters respond.
