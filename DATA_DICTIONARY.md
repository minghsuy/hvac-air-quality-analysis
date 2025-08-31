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
| All | Any field | Sensor offline/error → empty string |

## Filter Efficiency Calculation

```python
if outdoor_pm25 <= 0:
    efficiency = 100.0 if indoor_pm25 <= 0 else 0.0
else:
    efficiency = ((outdoor_pm25 - indoor_pm25) / outdoor_pm25) * 100
    efficiency = max(0, min(100, efficiency))  # Clamp 0-100%
```

## Alert Thresholds

- **Filter Efficiency < 85%**: Warning
- **Filter Efficiency < 80%**: Critical - Replace filter
- **Indoor PM2.5 > 12 μg/m³**: WHO guideline exceeded

## Data Quality Notes

1. **AirGradient Compensated Values**: Temperature and humidity compensation algorithms improve PM2.5 accuracy
2. **VOC/NOX Indices**: Not directly comparable between brands (different scales)
3. **Radon**: Short-term average can fluctuate; long-term average more meaningful
4. **Negative Efficiency**: Can occur when indoor sources present (cooking, cleaning)

## Schema Version

- **Version**: 2.0
- **Date**: 2025-08-31
- **Breaking Change from v1**: Added Sensor_ID, Room, Sensor_Type, Indoor_NOX columns