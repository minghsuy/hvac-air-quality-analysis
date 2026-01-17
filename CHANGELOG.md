# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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