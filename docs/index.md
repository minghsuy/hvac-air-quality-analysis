# HVAC Air Quality Analysis

142,000+ sensor readings across 9 months (July 2025 – April 2026). Continuous indoor + outdoor measurement of PM2.5, CO2, VOCs, radon, temperature, and humidity in one house.

> **Start here if you're new: [What my home's air taught me](what-my-homes-air-taught-me.md)** — four findings in ~1,500 words, parent-audience first.

## What This Project Does

Three sensors (Airthings View Plus, AirGradient Open Air, AirGradient ONE) collect 14 air quality metrics every 5 minutes. A Streamlit dashboard with Parquet caching makes this data explorable in real time.

**Headline finding** (Sept–Oct 2025 natural experiment): two filters carrying the same "MERV 13" label differed by ~24 percentage points in measured PM2.5 filtration in the same installation. OEM ~95%, generic substitute 69%. MERV rating is a minimum threshold, not a performance guarantee. Full analysis in the [verification report](reports/findings.html).

## Documentation

- [What my home's air taught me](what-my-homes-air-taught-me.md) — narrative summary, four findings
- [Findings](findings.md) — numeric summary and per-cycle filter data
- [Verification report](reports/findings.html) — interactive charts, reproducible from `scripts/analysis/verify_findings.py`
- [Methodology](methodology.md) — Spearman vs. Pearson, LOWESS anomaly detection, seasonal thresholds
- [Dashboard Architecture](dashboard-architecture.md) — Streamlit + Parquet caching benchmarks
- [Data Quality](data-quality.md) — column-shift fix, sensor placement, data gap handling
- [Lessons Learned](LESSONS_LEARNED.md) — measurement surprises and course corrections

## Interactive Charts

- [CO₂ Bedroom Levels](charts/co2_bedroom_levels.html) — ERV keeps bedrooms below the cognitive-impairment threshold
- [Filter Efficiency Over Time](charts/filter_efficiency.html) — full-history efficiency series
- [Indoor vs Outdoor PM2.5](charts/indoor_vs_outdoor_pm25.html) — filtration protection during bad air days

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
