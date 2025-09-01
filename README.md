# HVAC Air Quality Monitoring System

**Real-time filter efficiency tracking to prevent asthma triggers before they happen.**

[![Release](https://img.shields.io/github/v/release/minghsuy/hvac-air-quality-analysis)](https://github.com/minghsuy/hvac-air-quality-analysis/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 🎯 Why This Matters

After experiencing recurring asthma symptoms correlated with degraded HVAC filter performance, I built this system to:
- **Predict filter replacement timing** based on actual efficiency, not arbitrary schedules
- **Prevent health issues** by replacing filters before efficiency drops below safe thresholds
- **Save money** by extending filter life when efficiency remains high
- **Track multiple rooms** independently for targeted air quality management

## 📊 Current Status (v0.4.0 - September 2025)

- ✅ **Smart alerting deployed** with confidence-based notifications
- ✅ **Schema migration complete** - 3,985 historical rows preserved
- ✅ **Multi-room monitoring active** - Master & second bedrooms tracked
- ✅ **Filter efficiency stable** at 85-100% after 70+ days on MERV 13

## 🚀 Quick Start

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

## 📡 System Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Airthings   │     │ AirGradient  │     │ AirGradient  │
│   (Indoor)   │     │  (Outdoor)   │     │  (Indoor #2) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                     │
       └────────────────────┴─────────────────────┘
                           │
                    ┌──────▼───────┐
                    │ Unifi Gateway │
                    │   (Collector) │
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

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Airthings API
AIRTHINGS_CLIENT_ID=your_client_id
AIRTHINGS_CLIENT_SECRET=your_secret
AIRTHINGS_DEVICE_SERIAL=your_device_serial

# AirGradient Sensors (optional)
AIRGRADIENT_SERIAL=outdoor_sensor_serial
AIRGRADIENT_INDOOR_SERIAL=indoor_sensor_serial

# Google Sheets
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_SHEET_TAB=Cleaned_Data_20250831
```

### Google Service Account
1. Create service account in Google Cloud Console
2. Download credentials as `google-credentials.json`
3. Share your Google Sheet with the service account email

## 📈 Data Collection

The system collects data every 5 minutes, tracking:

- **Indoor Metrics**: PM2.5, CO2, VOC, temperature, humidity, radon
- **Outdoor Metrics**: PM2.5, CO2, VOC, NOX, temperature, humidity
- **Calculated**: Real-time filter efficiency percentage
- **Smart Alerts**: Confidence-based notifications avoiding false positives

### Running the Collector

```bash
# Test run
python collect_with_sheets_api_v2.py

# Deploy to Unifi Gateway (see deployment guide)
./scripts/deploy_to_unifi.sh
```

## 🔔 Smart Alerting System

The Google Apps Script provides intelligent notifications:

- **High Confidence** alerts when outdoor PM2.5 > 10 μg/m³
- **Medium Confidence** when outdoor PM2.5 is 5-10 μg/m³
- **Activity suppression** during known high-activity hours
- **Median-based** calculations to filter temporary spikes

## 📚 Documentation

- [Data Dictionary](DATA_DICTIONARY.md) - Field definitions and units
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Project Wiki](https://github.com/minghsuy/hvac-air-quality-analysis/wiki) - Detailed analysis and results

## 🛠️ Development

```bash
# Run tests
pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type checking
uv run mypy .
```

## 📊 Key Findings

After 6 months of monitoring:
- MERV 13 filters maintain >85% efficiency for 70+ days
- Indoor PM2.5 stays below 12 μg/m³ (WHO guideline)
- Filter replacement can be extended from 45 to 120+ days
- Estimated savings: $130-910/year on filter costs

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- [Airthings](https://www.airthings.com/) for excellent indoor air quality sensors
- [AirGradient](https://www.airgradient.com/) for open-source outdoor monitoring
- Unifi Gateway Ultra for reliable edge computing platform

---

**Note**: This system is designed for personal health monitoring. Always consult HVAC professionals for system maintenance and medical professionals for health concerns.