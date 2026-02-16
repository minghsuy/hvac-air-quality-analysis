# HVAC Air Quality Monitoring System

**Manufacturer says replace filters every 45 days. My data says 120+ days. Here's why.**

[![Release](https://img.shields.io/github/v/release/minghsuy/hvac-air-quality-analysis)](https://github.com/minghsuy/hvac-air-quality-analysis/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## The Problem

My family has asthma. After noticing symptoms correlating with degraded HVAC filter performance, I needed answers:

- **When should I actually replace filters?** (Not when the manufacturer says, but when efficiency drops)
- **How do I measure "efficiency" objectively?** (Indoor PM2.5 alone is meaningless without outdoor context)
- **Can I predict problems before they affect health?**

## The Solution

6+ months of continuous monitoring with **98,000+ sensor readings** revealed:

| What Manufacturer Says | What Data Shows |
|------------------------|-----------------|
| Replace every 45 days | MERV 13 maintains >85% efficiency for **120+ days** |
| Indoor air quality sensors are enough | You need **outdoor baseline** to calculate true efficiency |
| Replace on schedule | Replace when **efficiency drops below threshold** |

**Result**: Better air quality, fewer asthma triggers, $130-910/year saved on unnecessary filter replacements.

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

## Key Findings

After analyzing 98,000+ readings over 6 months:

1. **MERV 13 filters maintain >85% efficiency for 120+ days** (not 45 days as marketed)
2. **Load-based predictions don't work** - a filter at 197% of "max life" still performed at 87.3% efficiency
3. **Seasonal calibration matters** - winter pollution requires different thresholds than summer
4. **Indoor PM2.5 stays below 12 μg/m³** (WHO guideline) with proper monitoring

See the [Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki) for detailed analysis and visualizations.

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
- [Data Dictionary](DATA_DICTIONARY.md) - Field definitions and units
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
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
