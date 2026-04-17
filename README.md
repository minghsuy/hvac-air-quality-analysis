# HVAC Air Quality Monitoring System

**Continuous residential HVAC monitoring. 142,000+ sensor readings across 9 months. Three installer / filter / system incidents caught that a human trusting the install wouldn't have.**

[![Release](https://img.shields.io/github/v/release/minghsuy/hvac-air-quality-analysis)](https://github.com/minghsuy/hvac-air-quality-analysis/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

👉 **New here?** Start at the landing page: [What my home's air taught me](https://minghsuy.github.io/hvac-air-quality-analysis/what-my-homes-air-taught-me.html). The full verification report with interactive charts: [findings.html](https://minghsuy.github.io/hvac-air-quality-analysis/reports/findings.html).

## Why this exists

My gas furnace kept tripping its overheat-safety cutoff. My CO2 sensor was reading unusually high at the same time. An HVAC company traced both to a previous installer having clamped the air duct to my room. I scrapped the furnace, put in a heat pump + ERV, and started measuring the air continuously. The monitoring system grew out of wanting a signal I could trust the next time a human told me "it's fine."

Nine months and 142,000+ readings later, the system has caught two more incidents of the same pattern:

- **Sept 6 – Oct 15, 2025** — installer substituted a generic MERV-13-labeled filter for my OEM ERV filter during a service visit. Measured efficiency dropped from ~95% to 69% median. Detected within the first day of data; confirmed across the full 40-day period.
- **Feb 7–8, 2026** — in-service filter degradation. Hourly efficiency dropped from ~95% baseline to 49% by 9 AM. HVACMonitor v3 (Google Apps Script) escalated WARNING → CRITICAL over 8 hours. Replacement restored efficiency to 100% within the hour. Family reported smelling the air before the numbers made it human-obvious.

The measurement system is still running. Google Apps Script on a trigger, seasonal threshold calibration, email alerts on drift. Full methodology in the [docs](docs/) directory and the [verification report](https://minghsuy.github.io/hvac-air-quality-analysis/reports/findings.html).

## Findings (verified against 142k-row parquet cache)

1. **OEM MERV 13 filter cycles** run 116–151 days in this installation vs. a 90-day manufacturer schedule. ~$130/year back on the ERV alone at current prices; savings scale with filter cost.
2. **Two filters with the same "MERV 13" rating differ by ~24 percentage points** in real-world PM2.5 efficiency in the same installation (Sept–Oct 2025 natural experiment). MERV is a minimum spec, not a performance guarantee. This is consistent with peer-reviewed filtration research (Fazli et al., *Indoor Air* 2019, PMID 31077624).
3. **Efficiency-based alerts catch real failures** that calendar-based replacement schedules miss. Load-based filter-life prediction does not predict efficiency degradation in this system.
4. **CO2–VOC correlate at ρ=0.65** in this house, making an inexpensive CO2 monitor a reasonable under-ventilation proxy (for homes where VOCs are occupant-sourced rather than material-off-gassed).
5. **Outdoor PM2.5–Indoor Radon correlate at ρ=0.53** as an atmospheric-stagnation co-signal — rare for homes to measure both continuously.

## How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Airthings   │     │ AirGradient  │     │ AirGradient  │
│   (Indoor)   │     │  (Outdoor)   │     │  (Indoor #2) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       └────────────────────┴─────────────────────┘
                           │
                    ┌──────▼───────┐
                    │   Collector   │
                    │  (Spark DGX)  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Google Sheets │
                    │   (Storage)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  Apps Script  │
                    │   (Alerting)  │
                    └──────────────┘
```

**Filter Efficiency Formula**:
```
Efficiency = ((Outdoor PM2.5 - Indoor PM2.5) / Outdoor PM2.5) × 100%
```

This is why indoor-only monitoring fails: if outdoor air is clean, even a failing filter looks effective.

## Dashboard

An interactive Streamlit dashboard makes the data explorable:

```bash
# Run the dashboard
streamlit run scripts/dashboard.py --server.port 8501
```

> **Prerequisites**: The dashboard requires a configured `.env` file (with `GOOGLE_SPREADSHEET_ID` and `GOOGLE_SHEET_TAB`), a valid `google-credentials.json` service account file, and an active Google Sheet with sensor data. See [Configuration](#configuration) for setup.

**7 pages**: Overview, CO2 Compare, Heatmaps, VOC & NOX, Filter & PM2.5, Environment, Correlations

- Spearman rank correlation matrix for all 14 metrics
- LOWESS anomaly detection for CO2 trend analysis
- Heatmaps for every metric (hour x date, weekday vs weekend, monthly profiles)
- Parquet cache: 18ms load vs 3.5s Google Sheets API (106x faster)

See the [methodology docs](https://minghsuy.github.io/hvac-air-quality-analysis/methodology) for why Spearman over Pearson.

**Interactive charts**: [CO₂ Levels](https://minghsuy.github.io/hvac-air-quality-analysis/charts/co2_bedroom_levels.html) | [Filter Efficiency](https://minghsuy.github.io/hvac-air-quality-analysis/charts/filter_efficiency.html) | [Indoor vs Outdoor PM2.5](https://minghsuy.github.io/hvac-air-quality-analysis/charts/indoor_vs_outdoor_pm25.html)

## Duplicate-content note

This section previously held an older version of the findings summary. It's been consolidated into the `## Findings` section at the top of this README (aligned with the landing page and verification report) to avoid drift.

See [docs/findings.md](docs/findings.md) for the current numeric summary and [docs/reports/findings.html](https://minghsuy.github.io/hvac-air-quality-analysis/reports/findings.html) for the interactive verification report. [Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki) has the deeper research and policy essay.

## Quick Start

### Prerequisites
- Python 3.12+
- [uv package manager](https://github.com/astral-sh/uv)
- Airthings API credentials
- Google Service Account (for Sheets API)
- (Optional) AirGradient sensors for outdoor monitoring

### Installation

```bash
# Clone repository
git clone https://github.com/minghsuy/hvac-air-quality-analysis.git
cd hvac-air-quality-analysis

# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv --python 3.12
source .venv/bin/activate
uv sync --dev

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

```bash
# .env file
AIRTHINGS_CLIENT_ID=your_client_id
AIRTHINGS_CLIENT_SECRET=your_secret
AIRTHINGS_DEVICE_SERIAL=your_device_serial

# AirGradient Sensors (optional but recommended)
AIRGRADIENT_SERIAL=outdoor_sensor_serial
AIRGRADIENT_INDOOR_SERIAL=indoor_sensor_serial

# Google Sheets
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SHEET_TAB=Cleaned_Data_20250831
```

### Running the Collector

```bash
# Test run
python collect_with_sheets_api_v2.py --test

# For persistent collection, use systemd user service
# See CLAUDE.md for systemd setup instructions
```

## Smart Alerting

The Google Apps Script (`HVACMonitor_v3.gs`) provides:

- **Efficiency-based filter alerts** - measures actual performance, not theoretical decay
- **Seasonal thresholds** - auto-calibrates for winter vs. summer air quality
- **Time-based reminders** - for filters that can't be efficiency-measured (zone filters)
- **Barometric pressure alerts** - weather-triggered health notifications

## Documentation

- [GitHub Pages — Methodology & Findings](https://minghsuy.github.io/hvac-air-quality-analysis/) - Dashboard architecture, statistical methodology, correlation findings
- [Data Dictionary](docs/DATA_DICTIONARY.md) - Field definitions and units
- [Troubleshooting Guide](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki) - Detailed analysis and results
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Lessons Learned](docs/LESSONS_LEARNED.md) - What worked and what didn't

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- [Airthings](https://www.airthings.com/) for indoor air quality sensors
- [AirGradient](https://www.airgradient.com/) for open-source outdoor monitoring

---

**Note**: This system is designed for personal health monitoring. Always consult HVAC professionals for system maintenance and medical professionals for health concerns.
