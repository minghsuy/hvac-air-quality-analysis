# Project Structure

## Core Files

### Data Collection
```
├── collect_with_sheets_api_v2.py  # Main collector with multi-room support
├── collect_with_sheets_api.py     # Legacy single-room collector
├── sensors.json                   # Sensor configuration (IPs, rooms)
└── google-credentials.json        # Service account credentials (gitignored)
```

### Analysis & Visualization
```
├── analyze_historical.py          # Historical data analyzer
├── analysis.ipynb                 # Jupyter notebook for interactive analysis
└── data/                          # Data storage (gitignored)
    ├── *.csv                      # Airthings exports
    └── figures/                   # Generated visualizations
```

### Google Apps Script
```
└── apps_script_code.gs           # Smart alerting system with confidence levels
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
│   └── indoor_airqualitys_hidden_impact_on_family_health.md
├── RELEASE_CHECKLIST.md         # Release process documentation
├── VISUALIZATION_WORKFLOW.md    # Chart generation best practices
├── NEXT_PHASE.md               # Future enhancements
└── wiki_structure.md           # Wiki organization guide
```

## Utility Scripts

```
└── scripts/
    ├── update_airgradient_ips.py # Dynamic IP discovery
    ├── check_status.sh           # System health check
    └── archive/                  # Old versions for reference
```

## Testing
```
└── tests/
    ├── test_collector.py         # Unit tests for collector
    └── test_integration.py       # Integration tests
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
| `apps_script_code.gs` | Google Sheets alerting | Rarely |
| `DATA_DICTIONARY.md` | Data schema documentation | When fields change |

## Data Flow

```
1. Sensors (Airthings, AirGradient)
   ↓
2. Collector Script (every 5 minutes via cron)
   ↓
3. Google Sheets (data storage)
   ↓
4. Apps Script (smart alerting)
   ↓
5. Email Notifications (when thresholds exceeded)
```

## Quick Commands

```bash
# Test collection locally
python collect_with_sheets_api_v2.py

# Update sensor IPs
python scripts/update_airgradient_ips.py

# Check system status
./scripts/check_status.sh
```

## Storage Locations

| Data Type | Location | Persistence |
|-----------|----------|-------------|
| Collected data | Google Sheets | Permanent |
| Local backup | `/data/logs/air_quality_data.jsonl` | Until cleared |
| Application logs | `/data/logs/air_quality.log` | Rotated weekly |
| Cron logs | `/data/logs/cron.log` | Rotated daily |

## Important Notes

1. **Never commit**: `.env`, `google-credentials.json`, `sensors.json` (with real IPs)
2. **Always use**: uv for dependency management (not pip)
3. **Test locally**: Before deploying
4. **Check logs**: When troubleshooting issues
5. **Backup config**: Before making major changes