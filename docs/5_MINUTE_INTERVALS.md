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

If you want to change the frequency later:

```bash
# On Unifi Gateway
crontab -e

# Change */5 to:
# */10 for every 10 minutes (6/hour)
# */15 for every 15 minutes (4/hour)
# */3 for every 3 minutes (20/hour) - more detailed
```

## Monitoring Specific Events

During your first month, you might want to temporarily increase frequency during:
- Morning routines (showers, breakfast)
- Evening cooking
- Cleaning days
- High outdoor pollution events

This helps you understand your home's air quality patterns and how quickly your filters respond.
