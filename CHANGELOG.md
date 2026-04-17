# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`checkIndoorBaseline` — NEW Apps Script alert** (#32, closes #27). Fires when master-bedroom `Indoor_PM25` sustains above 5 µg/m³ while outdoor is calm (< 10 µg/m³ gate). Option C discrimination: WARNING at 30-min sustained (with slope gate to suppress cooking's decay phase) + CRITICAL at 90-min sustained (regardless of slope). Distinct cooldowns per tier. Backtested against 9 months of data: **1.38 alerts/wk** (0.40 WARN + 0.98 CRIT), down from 6.89/wk at the original threshold=3 proposal.
- **`MONITOR_VERSION` constant + per-`runAllChecks()` logging** (#32) — deploy-drift between repo and the paste-in-Apps-Script deployment is now grep-able in the execution log, not a mystery.
- **`EXPECTED_SENSORS` per-sensor `maxGapHours`** (#32, closes #25). `checkDataCollection` now iterates expected sensors rather than the rows it happened to see in a narrow window — a sensor stopped long enough to fall out of the scan buffer still gets flagged. Temp Stick's 3h `maxGapHours` reflects its hourly cadence plus slack.
- **Shared `scripts/_sheets_loader.py`** module — single source of truth for Sheets → DataFrame conversion (#29, closes #28). Three near-identical copies in `refresh_cache.py`, `dashboard.py`, and `bench_heatmap.py` collapsed into one with clean mock boundaries (`_fetch_values` + `_values_to_df`).
- **Pre-push guardrail** (`scripts/hooks/pre-push` Section 8) — blocks new root-level `.py`/`.csv`/`.json`, debug-pattern filenames, and `*.egg-info/` from ever re-entering the repo (#23). Exempts the DGX-pinned collector and template files (both `*_template.*` and `*.template.*` naming).
- **`docs/plans/`** directory with the four-issue monitoring sprint plan (ce-plan + document-review deepened pass).
- Interactive Streamlit dashboard with 7 pages: Overview, CO2 Compare, Heatmaps, VOC & NOX, Filter & PM2.5, Environment, Correlations (`scripts/dashboard.py`)
- Parquet cache for dashboard data (18ms read vs 3.5s Sheets API — 106x faster)
- 3-layer caching: Parquet on disk (1hr TTL), session state, pre-aggregated hourly/daily dicts
- Spearman rank correlation matrix for all 14 air quality metrics
- LOWESS anomaly detection for CO2 trend analysis (frac=0.08, 1.5x std threshold)
- 4 CO2 visualization styles: rolling avg + band, heatmap, weekly box plots, LOWESS + anomalies
- Heatmaps for all 14 metrics organized by Indoor Air / Outdoor / Comfort categories
- Weekday vs weekend and monthly hourly profile charts
- ERV tradeoff visualization (CO2 vs PM2.5 dual-axis chart)
- Outdoor-to-indoor scatter plots with Spearman and Pearson correlation display
- VOC & NOX analysis page with indoor vs outdoor comparison, daily patterns, and trends
- Performance benchmark script (`scripts/bench_heatmap.py`) — Sheets vs Parquet vs Polars vs cuDF
- Static chart generator for README/LinkedIn images (`scripts/create_visualizations.py`)
- GitHub Pages documentation site with methodology, architecture, and findings
- Column shift fix for pre-September 2025 data (17-col vs 18-col rows)
- Temp Stick WiFi sensor integration for attic temperature/humidity monitoring
- `get_tempstick_data()` with graceful failure (optional sensor, silently skipped if not configured)
- `build_air_quality_row()` and `build_temp_only_row()` helpers to eliminate row construction duplication
- Project context files: `docs/CLAUDE_CODE_CONTEXT.md` (vision/architecture) and `docs/BACKLOG.md` (prioritized tasks)
- `.env.example` template for all environment variables
- 11 new tests: 6 for Temp Stick API integration, 5 for `_sheets_loader` shift-repair boundaries (33 total)
- 6 more tests for `TestTempStickDedup` covering first-write / skip / update / missing-checkin / corrupt-cache / 429 paths
- AI analysis plan for RAPIDS + Ollama GPU-accelerated pipeline (`docs/AI_ANALYSIS_PLAN.md`)
- `docs/what-my-homes-air-taught-me.md` landing page and supporting evidence report
- `scripts/analysis/verify_findings.py` reproducible HTML evidence report generator
- `scripts/analysis/screenshot_report.py` Playwright-based visual verification hook

### Changed
- **`checkDataCollection` rewritten** (#32, closes #25). Replaces the 50-row scan window (narrower than `DATA_GAP_HOURS` at mixed cadence — the bug that hid the 3-day Temp Stick outage) with a time-based scan of `2 × max(maxGapHours)` hours. Iterates `CONFIG.EXPECTED_SENSORS` rather than `lastSeen` keys so a sensor that fell out of the scan buffer still gets flagged. Per-sensor `DATA_GAP_*` script-property lifecycle preserved. `DATA_GAP_HOURS` retained as a deprecated legacy constant.
- **Temp Stick polling now dedups by `last_checkin`** (#30, closes #26). Collector skips the Sheet write when the sensor hasn't produced a fresh reading since the last successful fetch — atomic `.tmp + os.replace` write, stderr warnings on cache IO failure. Attic row volume drops from ~288/day to ~24/day (matching the sensor's actual hourly cadence).
- **Repo tidy-pass** (#23): 6 supporting docs moved into `docs/` (`BACKLOG.md`, `CLAUDE_CODE_CONTEXT.md`, `DATA_DICTIONARY.md`, `PROJECT_STRUCTURE.md`, `RELEASE_CHECKLIST.md`, `TROUBLESHOOTING.md`). Root Python scripts moved into `scripts/utils/` (non-production) and `scripts/collectors/` (template only). `collect_with_sheets_api_v2.py` stays at root per DGX systemd pin. Duplicate `setup-git-hooks.sh` removed in favor of `scripts/install-hooks.sh`.
- Fixed ERV model in docs: Panasonic FV-04VE1 → Carrier ERVXXLHB (horizontal, attic-installed)
- Deduplicated `CLAUDE.md` by removing rules inherited from global config

### Fixed
- **`_sheets_loader` shift-repair now gated by timestamp** (#29, closes #28). The legacy 17-col column-shift repair was also firing on modern Temp Stick rows that Google Sheets trimmed to 12 cols (trailing-empty truncation), silently NaN'ing `Indoor_Temp` and `Indoor_Humidity` on every parquet read. Gate is now `(orig_cols < 18) AND (Timestamp < 2025-09-01)`. Retroactive recovery: **15,775 attic rows** from Feb 8 install onward now have valid temp/humidity (range 10.1–44.8°C); previously all were NaN.
- **Temp Stick API User-Agent** (#24). The default `python-requests/2.32.5` UA started getting 429-blocked at Temp Stick's edge (likely Cloudflare WAF) on 2026-04-13, silently dropping attic data for 3+ days. Now sends a descriptive honest UA (`hvac-air-quality-analysis/…`); not browser-faked.
- **Pre-push secrets scan** now matches only added diff lines (`^\+[^+]`) — deleting a file that legitimately documented `d8:3b:da` (the Airthings MAC prefix) no longer trips the scan. Also excludes `+++ b/path` headers from matching (paths containing sensor-ID patterns no longer false-positive).
- Temp Stick API returns °C natively (not °F as initially assumed) — removed incorrect double conversion
- Data gap alert now checks per-sensor instead of last row — no more false positives when one sensor is down
- Added cooldown (one alert per gap per sensor) and recovery notification when sensor resumes
- Landing page + wiki credibility sweep: fabricated "Scully 2019" citation corrected to Rodeheffer 2018 (#17); European code claims corrected (France tech-neutral, Norway TEK17 performance-based, F7 from Arbeidstilsynet workplace guidance) (#18); unverified California Title 24 MERV-13 claim dropped (#22)

## [0.5.0] - 2026-01-17

### Added
- **HVACMonitor v3** - Simplified Google Apps Script for filter monitoring (~850 lines, down from ~1500)
- Efficiency-based filter alerts (measures actual performance, not theoretical decay)
- Seasonal minimum outdoor PM2.5 thresholds (winter: 10, summer: 5, default: 7 μg/m³)
- Zone filter time-based reminders (for filters that can't be efficiency-measured)
- Location configuration via Script Properties for open-sourcing
- Filter replacement analysis function (`analyzeFilterReplacements()`)
- Efficiency data validation function (`analyzeEfficiencyData()`)
- Seasonal calibration function (`calibrateEfficiencyThresholds()`)

### Changed
- **BREAKING**: Migrated from Unifi Gateway to Spark DGX for data collection
- Replaced cron-based collection with systemd user services and timers
- Updated documentation to reflect new deployment architecture
- Removed load-based filter life predictions (proven unreliable by data analysis)

### Removed
- Unifi Gateway deployment scripts (`setup_unifi.sh`, `deploy_to_unifi.sh`)
- Unifi-specific SSH setup guide (`ssh_into_uni_fi_cloud_gateway_ultra.md`)
- Unifi firmware persistence scripts (`SETUP_AFTER_FIRMWARE_UPDATE.sh`)
- Cron job configuration (replaced with systemd timers)
- HVACMonitor v1/v2 (superseded by v3)

### Why These Changes?

**Spark DGX Migration:**
The Unifi Gateway proved unreliable for long-term data collection:
1. Firmware updates wiped configurations requiring manual re-setup
2. Data collection stopped unexpectedly with no notification
3. Installing Python packages required workarounds

Spark DGX with systemd provides true persistence, better monitoring, and simpler maintenance.

**HVACMonitor v3 Simplification:**
Analysis of 82,791 readings revealed:
1. Load-based filter life prediction doesn't correlate with actual degradation
2. A filter at 197% of "max life" still performed at 87.3% efficiency
3. Efficiency-based alerts measure real performance, not theoretical decay
4. Seasonal thresholds enable reliable measurement year-round

## [0.4.0] - 2025-09-01

### Added
- Comprehensive data dictionary (DATA_DICTIONARY.md) defining all fields and units
- Google Sheets schema migration tools for converting 14-column to 18-column format
- Migration guide (SHEETS_MIGRATION_GUIDE.md) with step-by-step instructions
- Data validation script to ensure compliance with data dictionary
- Smart alerting system in Google Apps Script with confidence levels
- Activity spike filtering using median calculations
- Outdoor PM2.5-based reliability scoring for alerts
- Persistence scripts for system reboots/updates
- Dynamic IP discovery for AirGradient sensors using arp

### Changed
- Migrated 3,985 rows from old Google Forms schema to new Sheets API schema
- Updated collector to write to specific sheet tab (Cleaned_Data_20250831)
- Switched to using compensated values from AirGradient (pm02Compensated, atmpCompensated)
- Standardized data types: numeric values with empty strings for missing data
- Store radon in native API units (Bq/m³) instead of display units (pCi/L)
- Apps Script now uses median instead of average to reduce false positives
- Improved alerting logic with activity hour suppression

### Fixed
- Airthings API response parsing for new "results" structure (was "sensors")
- AirGradient field names to use correct camelCase (tvocIndex, noxIndex)
- Filter efficiency calculation using compensated PM2.5 values
- Data type consistency issues between string and numeric values
- Unit conversion confusion for radon measurements
- Cron job configuration with proper PATH variables
- mDNS resolution issues using IP-based discovery

### Security
- Removed hardcoded spreadsheet IDs from multiple files
- Fixed exposed IP addresses in apps_script_code.gs
- Updated form ID placeholders in sensors.template.json
- Added missing sys import to fix undefined name errors
- Removed all temporary test and migration scripts
- Applied ruff formatting to ensure code quality

## [0.3.0] - 2025-08-30

### Added
- Multi-sensor support for tracking multiple rooms independently
- Google Sheets API direct writing (replacing Forms for better scalability)
- Second bedroom monitoring with AirGradient indoor sensor
- Dynamic IP resolution for AirGradient sensors
- Wrapper script for .local domain issues
- Comprehensive data analysis scripts for filter change impact
- Google Apps Script for automated monitoring and alerts
- Room-specific efficiency calculations
- Sensor discovery and configuration system (sensors.json)

### Changed
- Switched from Google Forms to Sheets API for multi-sensor data structure
- Data now includes room identification for each sensor reading
- Updated collection to handle both Airthings and AirGradient indoor sensors
- Improved error handling for network connectivity issues
- Enhanced documentation with multi-sensor setup instructions

### Fixed
- Data collection outage caused by firmware update removing cron job
- mDNS resolution issues with .local domains
- Timestamp handling for proper timezone support
- Filter efficiency calculation accuracy at low PM2.5 levels

### Discovered
- Firmware updates can wipe custom cron jobs and scripts
- Need monitoring to detect when collection stops (implemented in Apps Script)
- Low outdoor PM2.5 (<5 μg/m³) makes efficiency percentage unreliable

## [0.2.0] - 2025-07-27

### Added
- Secure Google Sheets API integration for reading data privately
- Comprehensive test suite with 17 tests covering all API integrations
- GitHub Actions workflows for automated testing and releases
- Pre-commit hooks for code quality
- Release documentation and changelog management
- Test scripts for verifying Airthings PM2.5 data collection
- Setup guide and verification scripts for Google Cloud authentication
- Support for reading both public (CSV export) and private (API) Google Sheets data

### Changed
- Updated pyproject.toml with Google API dependencies
- Reorganized project structure with tests/ and scripts/ directories
- Configured project as non-packaged for edge device compatibility

### Fixed
- Linting and formatting issues across all Python files
- GitHub Actions workflow configuration

### Security
- Added google-credentials.json to .gitignore for credential protection
- Implemented secure authentication for Google Sheets access

## [0.1.0] - 2025-07-27

### Added
- Initial release with core air quality monitoring functionality
- Airthings API integration for indoor air quality data
- AirGradient local API integration for outdoor air quality data
- Filter efficiency calculation and monitoring
- Google Forms integration for data logging
- Automated data collection script
- Historical data analysis tools
- Jupyter notebook for interactive analysis
- Wiki documentation for project setup and results

### Features
- Real-time PM2.5 monitoring (indoor vs outdoor)
- Filter efficiency tracking with alerts
- Cost analysis for filter replacements
- Health correlation tracking capabilities
- 5-minute automated data collection via cron

[Unreleased]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/minghsuy/hvac-air-quality-analysis/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/minghsuy/hvac-air-quality-analysis/releases/tag/v0.1.0