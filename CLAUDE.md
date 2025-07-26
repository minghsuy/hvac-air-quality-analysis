# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an HVAC air quality monitoring system designed to track filter efficiency and predict replacement timing to prevent asthma symptoms. The system compares indoor air quality (Airthings) vs outdoor air quality (AirGradient) to calculate real-time filter efficiency.

## Key Commands

### Development Environment Setup
```bash
# Install uv and create environment
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

### Running Tests
```bash
# Run tests with pytest
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality
```bash
# Format code with black
black .

# Lint with ruff
ruff check .

# Fix linting issues
ruff check --fix .
```

### Running the Collector
```bash
# Run locally (test mode)
python collect_air_quality.py

# Run analysis on historical data
python analyze_historical.py
```

## Architecture Overview

### Data Collection Flow
1. **Unifi Gateway** (every 5 minutes):
   - Runs `collect_air.py` via cron
   - Fetches indoor data from Airthings API
   - Fetches outdoor data from AirGradient local API
   - Calculates filter efficiency
   - Logs to Google Sheets and local JSONL

2. **Local Analysis** (on-demand):
   - `analyze_historical.py`: Analyzes CSV exports from Airthings
   - `analysis.ipynb`: Interactive Jupyter notebook for Claude-assisted analysis

### Key Thresholds
- **Filter Efficiency < 85%**: Alert threshold
- **Filter Efficiency < 80%**: Plan replacement
- **Indoor PM2.5 > 12 μg/m³**: Replace immediately (WHO guideline)

### API Integrations
- **Airthings**: OAuth2 client credentials flow for indoor air quality
- **AirGradient**: Local mDNS API (no auth) for outdoor air quality
- **Google Sheets**: Form submission API for data logging

## Project Structure

```
hvac-air-quality-analysis/
├── collect_air_quality.py    # Main data collector (runs on Unifi)
├── analyze_historical.py     # Historical data analyzer
├── analysis.ipynb           # Interactive analysis notebook
├── setup_unifi.sh          # Unifi Gateway setup script
├── pyproject.toml          # uv package management
├── .env.example            # Environment variable template
└── data/                   # Data directory (gitignored)
```

## Environment Variables

All secrets are stored in `.env` (never commit!):
- `AIRTHINGS_CLIENT_ID/SECRET`: OAuth credentials
- `AIRTHINGS_DEVICE_SERIAL`: Device to monitor
- `AIRGRADIENT_SERIAL`: Local sensor serial
- `GOOGLE_FORM_ID`: Form for data logging
- `FORM_*`: Field IDs for form submission

## Unifi Gateway Setup

The system runs on a Unifi Cloud Gateway Ultra:
1. SSH access enabled (see `ssh_into_uni_fi_cloud_gateway_ultra.md`)
2. Python3 and minimal dependencies installed
3. Cron job runs collector every 5 minutes
4. Data persists in `/data/scripts/` and `/data/logs/`

## Cost Tracking

Current filter costs:
- HVAC filter (MERV 15): $130
- ERV filter (MERV 13): $50
- Goal: Extend filter life from 45 days to 120+ days
- Target daily cost: < $1.50/day

## Health Correlation

The system aims to prevent asthma symptoms by replacing filters before efficiency drops too low. Key events tracked:
- Filter installation dates
- Efficiency degradation rates
- Indoor air quality exceedances
- Health symptoms (optional manual tracking)

## Important Security Reminders

**NEVER commit or expose:**
- Device MAC addresses (e.g., `d8:3b:da:XX:XX:XX`)
- Local IP addresses (e.g., `192.168.X.XX`)
- Device serial numbers in logs or examples
- Any network-specific identifiers

Always use generic placeholders (XX, X.XX) in documentation and examples. Check all commits for accidentally exposed network information before pushing to public repositories.