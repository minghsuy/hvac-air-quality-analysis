# HVAC Air Quality Analysis

98,000+ sensor readings across 6+ months, analyzing indoor air quality with Spearman correlation, LOWESS anomaly detection, and efficiency-based filter monitoring.

## What This Project Does

Three sensors (Airthings View Plus, AirGradient Open Air, AirGradient ONE) collect 14 air quality metrics every 5 minutes. A Streamlit dashboard with Parquet caching makes this data explorable in real time.

**Key insight**: MERV 13 filters maintain >85% efficiency for 120+ days — not the 45 days manufacturers recommend.

## Documentation

- [Dashboard Architecture](dashboard-architecture.md) — Why Streamlit, Parquet cache benchmarks, 3-layer caching strategy
- [Methodology](methodology.md) — Why Spearman over Pearson, LOWESS anomaly detection, pre-aggregation
- [Findings](findings.md) — Correlation analysis results, filter longevity, ERV tradeoff
- [Data Quality](data-quality.md) — Column shift fix, sensor placement, data gap handling

## Quick Links

- [GitHub Repository](https://github.com/minghsuy/hvac-air-quality-analysis)
- [Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki)
- [Data Dictionary](https://github.com/minghsuy/hvac-air-quality-analysis/blob/main/DATA_DICTIONARY.md)

## Sensors

| Sensor | Location | Measures |
|--------|----------|----------|
| Airthings View Plus | Primary bedroom | PM2.5, CO2, VOC, radon, temp, humidity |
| AirGradient Open Air | Outdoor | PM2.5, CO2, VOC, NOX, temp, humidity |
| AirGradient ONE | Second bedroom | PM2.5, CO2, VOC, NOX, temp, humidity |

## Tech Stack

- **Collection**: Python + Google Sheets API (systemd timer, every 5 min)
- **Storage**: Google Sheets (primary) + Parquet cache (dashboard)
- **Dashboard**: Streamlit + Plotly (7 pages, dark theme)
- **Analysis**: pandas, scipy (Spearman), statsmodels (LOWESS)
- **Alerting**: Google Apps Script (efficiency-based filter alerts)
