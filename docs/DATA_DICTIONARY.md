# Data Dictionary - HVAC Air Quality Monitoring

## Google Sheets Schema (18 columns)

| Column | Field Name | Data Type | Unit | Source | Example | Notes |
|--------|------------|-----------|------|--------|---------|-------|
| A | Timestamp | String | ISO 8601 | System | 2025-08-31 10:15:03 | Local time |
| B | Sensor_ID | String | - | Derived | airthings_129430 | Last 6 chars of serial |
| C | Room | String | - | Config | master_bedroom | Location identifier |
| D | Sensor_Type | String | - | Config | airthings | Brand/model |
| E | Indoor_PM25 | Number | μg/m³ | Sensor | 2.0 | Airthings: direct, AirGradient: pm02Compensated |
| F | Outdoor_PM25 | Number | μg/m³ | Sensor | 8.79 | AirGradient: pm02Compensated |
| G | Filter_Efficiency | Number | % | Calculated | 77.25 | ((outdoor-indoor)/outdoor)*100 |
| H | Indoor_CO2 | Number | ppm | Sensor | 637 | Direct from API |
| I | Indoor_VOC | Number | ppb | Sensor | 189 | Airthings: ppb, AirGradient: tvocIndex |
| J | Indoor_NOX | Number/Empty | index | Sensor | 1 or "" | AirGradient: noxIndex, Airthings: empty |
| K | Indoor_Temp | Number | °C | Sensor | 25.4 | Airthings: direct, AirGradient: atmpCompensated |
| L | Indoor_Humidity | Number | % | Sensor | 42.0 | Airthings: direct, AirGradient: rhumCompensated |
| M | Indoor_Radon | Number/Empty | Bq/m³ | Sensor | 9.0 or "" | Airthings only, short-term average |
| N | Outdoor_CO2 | Number | ppm | Sensor | 425 | AirGradient outdoor |
| O | Outdoor_Temp | Number | °C | Sensor | 42.6 | AirGradient: atmpCompensated |
| P | Outdoor_Humidity | Number | % | Sensor | 34.07 | AirGradient: rhumCompensated |
| Q | Outdoor_VOC | Number | index | Sensor | 393 | AirGradient: tvocIndex |
| R | Outdoor_NOX | Number | index | Sensor | 1 | AirGradient: noxIndex |

## API Field Mappings

### Airthings API Response
```json
{
  "results": [{
    "sensors": [
      {"sensorType": "pm25", "value": 1.0, "unit": "mgpc"},        // → Indoor_PM25
      {"sensorType": "co2", "value": 637.0, "unit": "ppm"},        // → Indoor_CO2
      {"sensorType": "voc", "value": 189.0, "unit": "ppb"},        // → Indoor_VOC
      {"sensorType": "temp", "value": 25.4, "unit": "c"},          // → Indoor_Temp
      {"sensorType": "humidity", "value": 42.0, "unit": "pct"},    // → Indoor_Humidity
      {"sensorType": "radonShortTermAvg", "value": 9.0, "unit": "bq"}, // → Indoor_Radon
    ]
  }]
}
```

### AirGradient API Response
```json
{
  "pm02": 1.17,              // Raw PM2.5 (not used)
  "pm02Compensated": 8.79,   // → Indoor/Outdoor_PM25 (preferred)
  "rco2": 425,                // → Indoor/Outdoor_CO2
  "tvocIndex": 393,           // → Indoor/Outdoor_VOC
  "noxIndex": 1,              // → Indoor/Outdoor_NOX
  "atmp": 40.4,               // Raw temp (not used)
  "atmpCompensated": 42.6,   // → Indoor/Outdoor_Temp (preferred)
  "rhum": 21.23,              // Raw humidity (not used)
  "rhumCompensated": 34.07   // → Indoor/Outdoor_Humidity (preferred)
}
```

### Temp Stick API Response
```json
{
  "data": {
    "sensor_id": "TS00XXXXXX",
    "sensor_name": "Attic",
    "last_temp": 20.52,           // °C (API returns metric; dashboard shows °F)
    "last_humidity": 35.0,        // → Indoor_Humidity
    "battery_pct": 98.5,
    "offline": false
  }
}
```

**Attic sensor notes:**
- Room: `attic` (near ERV/air handler)
- Only populates Indoor_Temp (col K) and Indoor_Humidity (col L)
- All other data fields = empty string `""`
- No filter efficiency calculation (no PM2.5 data)
- Battery-powered, reports every ~15-30 minutes (vs 5 min for other sensors)
- Some 5-minute collection polls may return the same reading (acceptable, not duplicated)
- API returns °C natively (dashboard displays °F but API is metric)

## Data Type Rules

1. **Numeric fields**: Store as numbers (not strings) for calculations
2. **Missing data**: Use empty string `""` (not 0 or null)
3. **Units**: Store in API native units (Bq/m³ not pCi/L)
4. **Compensated values**: Use when available (more accurate)

## Unit Conversions (for reference only)

- **Radon**: 1 pCi/L = 37 Bq/m³ (store Bq/m³, display can convert)
- **Temperature**: Store °C (convert to °F for display if needed: °F = °C × 9/5 + 32)
- **PM2.5**: μg/m³ is standard globally

## Missing Data Handling

| Sensor | Missing Fields | Reason |
|--------|---------------|--------|
| Airthings | Indoor_NOX | Sensor not present |
| AirGradient | Indoor_Radon | Sensor not present |
| Temp Stick | All except Indoor_Temp, Indoor_Humidity | Temp/humidity only sensor |
| All | Any field | Sensor offline/error → empty string |

## Filter Efficiency Calculation

```python
if outdoor_pm25 <= 0:
    efficiency = 100.0 if indoor_pm25 <= 0 else 0.0
else:
    efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
    efficiency = max(0, min(100, efficiency))  # Clamp 0-100%
```

## Alert Thresholds (HVACMonitor v3)

### Filter Efficiency
- **< 75%**: Change filter - efficiency declining (default; auto-calibrated monthly)
- **< 65%**: Critical - filter is failing, replace immediately (default; auto-calibrated monthly)

### Indoor Air Quality
- **PM2.5 > 12 μg/m³**: WHO annual guideline exceeded
- **PM2.5 > 25 μg/m³**: WHO 24-hour guideline exceeded
- **CO2 > 1000 ppm**: Ventilation recommended
- **CO2 > 2000 ppm**: Poor ventilation - immediate action needed

### Seasonal Outdoor PM2.5 Minimums (for reliable efficiency)
- **Winter (Dec-Feb)**: >= 10 μg/m³ required
- **Summer (Jun-Aug)**: >= 5 μg/m³ required
- **Spring/Fall**: >= 7 μg/m³ required

Readings below these thresholds are excluded from efficiency calculations.

## Data Quality Notes

1. **AirGradient Compensated Values**: Temperature and humidity compensation algorithms improve PM2.5 accuracy
2. **VOC/NOX Indices**: Not directly comparable between brands (different scales)
3. **Radon**: Short-term average can fluctuate; long-term average more meaningful
4. **Negative Efficiency**: Can occur when indoor sources present (cooking, cleaning)

## Schema Version

- **Version**: 2.2
- **Date**: 2026-02-08
- **Changes in v2.2**: Added Temp Stick sensor type (`tempstick`, room `attic`), updated alert thresholds for HVACMonitor v3
- **Changes in v2.1**: Added smart alerting thresholds, clarified WHO guidelines
- **Breaking Change from v1.0**: Added Sensor_ID, Room, Sensor_Type, Indoor_NOX columns (v2.0)

## Implementation Status

- ✅ Data collection to 18-column schema (v0.4.0+)
- ✅ Multi-room support with sensor identification
- ✅ Temp Stick attic sensor integration (v0.5.0+)
- ✅ HVACMonitor v3 efficiency-based alerting with seasonal calibration
- ✅ Median-based efficiency calculation with high-confidence filtering