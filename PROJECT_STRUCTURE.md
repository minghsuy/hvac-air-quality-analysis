# Project Structure

## Core Files

### Data Collection
```
├── collect_with_sheets_api_v2.py  # Main collector with multi-room support
├── sensors.json                   # Sensor configuration (IPs, rooms) - gitignored
└── google-credentials.json        # Service account credentials (gitignored)
```

### Dashboard & Analysis
```
├── scripts/
│   ├── dashboard.py               # Multi-page Streamlit dashboard (7 pages)
│   ├── bench_heatmap.py           # Performance benchmark (Sheets vs Parquet vs Polars)
│   └── create_visualizations.py   # Interactive Plotly HTML chart generator
├── .cache/                         # Parquet data cache (gitignored)
├── analyze_historical.py          # Historical data analyzer
├── analysis.ipynb                 # Jupyter notebook for interactive analysis
└── data/                          # Data storage (gitignored)
    ├── *.csv                      # Airthings exports
    └── figures/                   # Generated visualizations
```

### Google Apps Script
```
└── HVACMonitor_v3.gs             # Filter monitoring with efficiency-based alerts
```

## Configuration

### Environment
```
├── .env                           # Your credentials (gitignored)
├── .env.example                   # Template for environment variables
└── pyproject.toml                 # Dependencies and project metadata
```

### Version Control
```
├── .gitignore                     # Files to exclude from git
├── .pre-commit-config.yaml        # Pre-commit hooks configuration
└── CHANGELOG.md                   # Version history and changes
```

## Documentation

### Main Docs
```
├── README.md                      # Project overview and quick start
├── TROUBLESHOOTING.md            # Common issues and solutions
├── DATA_DICTIONARY.md            # Field definitions and units
└── CLAUDE.md                     # AI assistant instructions
```

### Specialized Guides
```
├── docs/
│   ├── ARCHITECTURE.md          # System design and data flow
│   ├── LESSONS_LEARNED.md       # Key insights from deployment
│   ├── 5_MINUTE_INTERVALS.md    # Why we use 5-minute collection
│   ├── _config.yml              # GitHub Pages Jekyll config
│   ├── charts/                  # Interactive Plotly HTML charts (generated)
│   ├── index.md                 # GitHub Pages landing page
│   ├── dashboard-architecture.md # Dashboard design and caching
│   ├── methodology.md           # Statistical methodology (Spearman, LOWESS)
│   ├── findings.md              # Correlation analysis results
│   └── data-quality.md          # Data engineering fixes
└── RELEASE_CHECKLIST.md         # Release process documentation
```

## Utility Scripts

```
└── scripts/
    ├── read_sheets_simple.py      # Simple Google Sheets reader
    ├── setup_google_sheets_api.py # API setup helper
    ├── analysis/                  # Analysis scripts
    └── collection/                # Collection utilities
```

## Testing
```
└── tests/
    ├── conftest.py                # Pytest configuration
    └── test_collect_air_quality.py # Unit tests for collector
```

## CI/CD
```
└── .github/
    └── workflows/
        ├── test.yml              # Automated testing
        └── release.yml           # Release automation
```

## File Purposes

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `collect_with_sheets_api_v2.py` | Main data collector | As needed |
| `sensors.json` | Sensor IP addresses | When IPs change |
| `google-credentials.json` | Auth for Sheets API | Never (gitignored) |
| `.env` | API credentials | As needed (gitignored) |
| `HVACMonitor_v3.gs` | Google Sheets filter monitoring | Rarely |
| `DATA_DICTIONARY.md` | Data schema documentation | When fields change |

## Data Flow

```
1. Sensors (Airthings, AirGradient)
   ↓
2. Collector Script (every 5 minutes via systemd timer)
   ↓
3. Google Sheets (data storage)
   ↓
4. Apps Script (filter efficiency monitoring)
   ↓
5. Email Notifications (when thresholds exceeded)
```

## Quick Commands

```bash
# Test collection locally
python collect_with_sheets_api_v2.py

# Run with verbose test output
python collect_with_sheets_api_v2.py --test

# Check systemd timer status (on deployment server)
systemctl --user status air-quality-collector.timer
```

## Storage Locations

| Data Type | Location | Persistence |
|-----------|----------|-------------|
| Collected data | Google Sheets | Permanent |
| Application logs | `journalctl --user -u air-quality-collector` | System managed |

## Important Notes

1. **Never commit**: `.env`, `google-credentials.json`, `sensors.json` (with real IPs)
2. **Always use**: uv for dependency management (not pip)
3. **Test locally**: Before deploying
4. **Check logs**: When troubleshooting issues
5. **Backup config**: Before making major changes
