# Data Quality

[Back to index](index.md)

## Column Shift Problem

### The Bug

Before September 2025, the data collector wrote 17 columns per row. After adding Airthings radon support and outdoor sensor fields, it writes 18 columns. Both row formats exist in the same Google Sheet.

When pandas reads a 17-column row against an 18-column header, every column after the missing field shifts left by one position. Temperature data appears in the humidity column, humidity in the radon column, and so on.

### The Fix

Track the original column count per row during data loading:

```python
for row in raw_rows:
    orig_cols.append(len(row))
    # Pad short rows with empty strings
    padded_row = row + [""] * (n_cols - len(row))

df["_orig_cols"] = orig_cols
```

Then NaN the columns that would be misaligned in short rows:

```python
shifted = df["_orig_cols"] < 18
for col in ["Indoor_Temp", "Indoor_Humidity", "Indoor_Radon",
            "Outdoor_CO2", "Outdoor_Temp", "Outdoor_Humidity",
            "Outdoor_VOC", "Outdoor_NOX"]:
    df.loc[shifted, col] = np.nan
```

### What's Preserved

The first 10 columns (Timestamp through Indoor_NOX) are correctly positioned in both 17-column and 18-column rows. Only the later columns need NaN treatment.

This means PM2.5, CO2, VOC, and NOX data from the full date range is usable. Temperature, humidity, radon, and outdoor metrics are only available from September 2025 onward.

## Sensor Placement Context

### Primary Bedroom Sensor (Airthings View Plus)
- Wall-mounted, away from windows and vents
- Measures: PM2.5, CO2, VOC, radon, temp, humidity
- Cleanest indoor air data — minimal interference from cooking or activities

### Second Bedroom Sensor (AirGradient ONE)
- Located near the kitchen area
- **Cooking spikes**: PM2.5 can jump from 3 to 80+ ug/m3 during cooking, with a 30-60 minute decay. This is a sensor placement artifact, not an air quality problem.
- Measures: PM2.5, CO2, VOC, NOX, temp, humidity
- Best sensor for detecting indoor activity patterns

### Outdoor Sensor (AirGradient Open Air)
- Provides the outdoor PM2.5 baseline for filter efficiency calculation
- Measures: PM2.5, CO2, VOC, NOX, temp, humidity
- Weather-exposed — data reflects actual outdoor conditions

### Scale Differences

Airthings and AirGradient use different VOC/NOX index scales:

- **Airthings VOC**: Proprietary index (higher = worse)
- **AirGradient VOC/NOX**: Sensirion SGP41 index (1-500 scale)

Cross-sensor VOC/NOX comparisons require awareness of these different scales. The correlation matrix uses single-room data to avoid mixing scales.

## October 2025 Data Gap

A 2-week data gap exists in October 2025. This corresponds to the migration from the Unifi Cloud Gateway to the DGX Spark for data collection.

### Impact
- No readings for approximately 14 days
- Before the gap: Unifi-based collection (less reliable, firmware wipes)
- After the gap: DGX Spark with systemd timers (persistent, reliable)
- The gap is visible in heatmaps and time-series charts as a blank band

### Handling
- The gap is left as-is (no interpolation or imputation)
- Rolling averages and LOWESS smoothing handle the gap gracefully
- Daily aggregations for the gap period simply have no entries
- The date range picker allows users to select around the gap if needed

## Data Volume

| Metric | Value |
|--------|-------|
| Total readings | 98,000+ |
| Collection interval | Every 5 minutes |
| Sensors | 3 (2 indoor, 1 outdoor) |
| Metrics per reading | Up to 14 numeric fields |
| Date range | 6+ months |
| Storage | Google Sheets (primary), Parquet cache (dashboard) |
| Parquet file size | ~4 MB |
